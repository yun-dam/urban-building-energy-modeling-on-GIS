# -*- coding: utf-8 -*-
"""
Created on Mon Jul  3 18:20:48 2023

@author: YUNDAM
"""

import os

from eppy.modeleditor import IDF
from IDD.genIDD90 import genIDD

from util import (move2Wstation, triangulateEarclip, gen_zones, findSurrBldgs, 
poly2roof, gen_horizontal_vertex, edge2wall, roof2wallNormVec, 
gen_WallProp, gen_WindowProp, gen_FloorName, gen_RoofName,
idf_zones, gen_zonelist, idf_walls, idf_windows, idf_roofs,
idf_floors, idf_shadingObjs, wall2window, set_Ins_thickness, set_glazing, get_epwinfo)

from pyproj import Proj

from geopandas import read_file
from metaData.insMeta import insMeta
from metaData.useMeta import load_useMeta

from shapely import Polygon 

class genEnergyPlus():
    
    def __init__(self, shpPath, epwPath, savePath = '.', idColumn = 'PNU', floorNumberColumn = 'GRND_FLR', useTypeColumn = 'USABILITY', builtDateColumn = 'USEAPR_DAY', wsg84 = True):
        
        '''
        shpPath: .shp directory
        epwPath: .epw directory
        savePath: directory to save EnergyPlus input (.idf) and output files
        idColumn: Building ID column name
        floorNumberColumn: # of ground floors column name
        useTypeColumn: use type column name
        builtDateColumn: date built column name (in 'yyyymmdd' format)
        wsg84: if geometry coordinates are lat and lot, then True
            
        '''
        
        # path
        cpath = os.getcwd() 
        self.MinimalIDFpath = os.path.join(cpath, 'IDF') # Minimal IDF directroy (=Archetypes)
        self.iddpath = genIDD() # generate IDD

        # eppy
        IDF.setiddname(self.iddpath) # IDD path
                                       
        self.data_ = read_file(shpPath, encoding = 'cp949') # read shapefiles
        
        Uvalues = insMeta # insulation data according to year built
        UseType = load_useMeta() # use type data
        
        self.epwPath = epwPath 
        self.savePath = savePath
        
        self.epwFileName = self.epwPath.split(sep='\\')[-1]
        region, lat, lon, tzone, elev = get_epwinfo(self.epwPath)

        Projection = Proj(self.data_.crs)
        
        self.floorNumberColumn = floorNumberColumn
        self.idColumn = idColumn
        self.useTypeColumn = useTypeColumn
        self.builtDateColumn = builtDateColumn
        
        # Merge GIS data with Archetype data
        self.data_ = self.data_.join(UseType.set_index('BDTYP_CD')[['IDF_type', '주거여부']], on = self.useTypeColumn) 
        self.data_[self.builtDateColumn].fillna('-1', inplace=True) # 누락데이터 처리 (-1)
        n_data = self.data_.shape[0]
            
        # Initialize
        date_apply = ['a']*n_data
        U_wall = ['a']*n_data
        U_roof = ['a']*n_data
        U_floor = ['a']*n_data
        U_window = ['a']*n_data
        EPWFname = ['a']*n_data
        EPWRegion = ['a']*n_data
        EPWLat = ['a']*n_data
        EPWLon = ['a']*n_data
        EPWTzone = ['a']*n_data
        EPWElev = ['a']*n_data
            
        for idx, row in self.data_.iterrows():
            
            if (idx+1)%int(n_data/10) == 0: # 10%*n -> print
                print('Data concatenation -> %.1f%%' %( (idx+1)/n_data*100))
           
            # epw information
            EPWFname[idx] = self.epwFileName 
            EPWRegion[idx] = region 
            EPWLat[idx] = lat 
            EPWLon[idx] = lon 
            EPWTzone[idx] = tzone 
            EPWElev[idx] = elev 
            
            new_date = row[self.builtDateColumn]
            date_apply[idx] = new_date 
            
            # map insulation information according to year built
            chk = 0
            for key in Uvalues.keys():
                if int(new_date) >= int(key):
                    sht_name = key
                    chk = 1
                    break        
            
            sht_name = '19790916' if chk == 0 else sht_name # for buildings before 1979.9.16
            
            # Map envelopes -> not only Korean metadata is applicable
            UvalueTable = Uvalues[sht_name]
            SI_GUN_GU = '11' # Region code for Seoul -> will be modified to general applications over the globe
            
            for idx2, TableRow in UvalueTable.iterrows():
                if SI_GUN_GU.startswith(str(TableRow['시군구코드'])):
                    if row['주거여부'] == 1: # 주거
                        U_wall[idx] = TableRow['외벽_주거']
                        U_window[idx] = TableRow['창호_주거']               
                    else:
                        U_wall[idx] = TableRow['외벽_주거외']
                        U_window[idx] = TableRow['창호_주거외']
                    U_roof[idx] = TableRow['지붕']
                    U_floor[idx] = TableRow['바닥']
            
            # date_apply = parallel_work(UseAprDay, 4) # Parallel processing
        
        # map insulation data
        self.data_['Date_apply'] = date_apply
        self.data_['U_wall'] = U_wall
        self.data_['U_roof'] = U_roof
        self.data_['U_floor'] = U_floor
        self.data_['U_window'] = U_window
        
        self.data_['EPWFname'] = EPWFname
        self.data_['EPWRegion'] = EPWRegion
        self.data_['EPWLat'] = EPWLat
        self.data_['EPWLon'] = EPWLon
        self.data_['EPWTzone'] = EPWTzone
        self.data_['EPWElev'] = EPWElev
        
        self.data_.projection = Projection 
        
        # fill missing data
        self.data_['IDF_type'].fillna('off', inplace = True) # NaN -> office 
        self.data_[self.floorNumberColumn].fillna(0, inplace = True) # NaN -> 0
        
        self.data_[self.idColumn].fillna('dummy', inplace = True) 
        self.data_[self.useTypeColumn].fillna('dummy', inplace = True) 
        
        # Remove MultiPolygon for analysis --> MultiPolygon will also be covered in the near future
        self.data_['is_MultiPolygon'] = (self.data_.geometry.type == 'MultiPolygon').tolist()
        
        target_crs = {'proj': 'tmerc', 'lat_0': 38, 'lon_0': 127.5, 'k': 0.9996, 'x_0': 1000000, 'y_0': 2000000, 'ellps': 'GRS80', 'units': 'm', 'no_defs': True} 
                    
        self.data_.crs = target_crs
        self.my_proj = Proj(self.data_.crs)
        self.data_.reset_index(inplace = True)       
        

        if wsg84: # conversion: wsg84 -> UTM


            for b in range(len(self.data_)):
                targetBldgCoords = self.data_.iloc[b]['geometry'].boundary.coords._coords
                
                xs = []
                ys = []
                    
                for k in range(len(targetBldgCoords)):
             
                    x, y = self.my_proj(targetBldgCoords[k][0], targetBldgCoords[k][1], inverse=False) # x, y
                    
                    xs.append(x)
                    ys.append(y)
                    
                self.data_['geometry'].iloc[b] = Polygon([(xx, yy) for xx, yy in zip(xs, ys)])
                    
                
        # self.data_ = self.data_.dropna(subset = ['BLD_NM'])
        
    def processedDataExport(self): # export merged data
        
        return self.data_ 
    
    def main(self, bldgID,  wwr = 0.4, Z_height = 3.0, boundaryBuffer = 30, run_simluation = True):
        
        '''
        bldgID: Building ID
        wwr: Wall-to-Window Ratio
        Z_height: Floor-to-Floor Height
        boundaryBuffer: How far from the building should surrounding buildings be modelled
        run_simluation: run simulation (True) or just generate idf (False)
            
        '''
        
        
        cpath = os.getcwd() 
        MinimalIDFpath = os.path.join(cpath, 'IDF') 
        
        Target_bldg = self.data_[self.data_[self.idColumn] == bldgID].iloc[0]
        bldg_idx = self.data_.index[self.data_[self.idColumn] == bldgID][0]

        
        newIDF = 'Bldg_ID_' + str(bldgID) + '.idf' # idf file name
        print('Generating... ' + newIDF)
        
        n_floor = int(Target_bldg[self.floorNumberColumn])
        
        if n_floor == 0:          
            raise Exception('# of Floors is 0!')

        built_year = int(Target_bldg['Date_apply'][:4]) # year built
        use_type = Target_bldg['IDF_type'] # use type
        
        # U-values
        Uwall = float(Target_bldg['U_wall'])
        Uroof = float(Target_bldg['U_roof'])
        Ufloor = float(Target_bldg['U_floor'])
        Uwindow = float(Target_bldg['U_window'])
        
        
        # Select a vintage according to year built
        if built_year < 1981:
            minimalIDF = use_type+'1.idf'
        elif built_year < 1988:
            minimalIDF = use_type+'2.idf'
        elif built_year < 2002:
            minimalIDF = use_type+'3.idf'
        else:
            minimalIDF = use_type+'4.idf'
        
        otherIdx = self.data_[self.data_[self.idColumn] != bldgID].index
        
        
        # Polygon coordinate conversion (origin: center of the footprint polygon)
        cent = Target_bldg['geometry'].centroid 
        bx, by = cent.x, cent.y 
        blon, blat = self.my_proj(bx, by, inverse = True) # center in lon, lat

        
        
        # list polygons of other buildings
        convertedData = move2Wstation(self.data_, blon, blat)
        poly = convertedData.loc[bldg_idx].geometry
        poly.simplify(30)
        
        convertedData = convertedData.loc[otherIdx]
           
        
        # Ear-Clipping to triangulate the footprint to generate EnergyPlus geometry 
        # i.e., concave -> convex
        poly_triangulated = triangulateEarclip(poly)
        
        # Zone information -> origin is (0,0,0)
        zone_name, zone_height = gen_zones(n_floor, height = Z_height)
        
        # map surrounding buildings within the boundary buffer (m)
        inter, new_bbox = findSurrBldgs(convertedData, poly, boundaryBuffer = boundaryBuffer) 
        inter = inter[inter.geometry.type != 'MultiPolygon'] # remove MultiPolygon
        inter = inter[inter[self.floorNumberColumn] > 0] # remove 0 floor
        
        ## Generate polygon of envelopes
        # Genrate Roofs and Floors 
        RoofPolygon = poly2roof(poly, Z_height) 
        floors, roofs = gen_horizontal_vertex(poly_triangulated, n_floor, Z_height) # generate coordinates of floors ans ceilings of each floor
        
        # Generate walls 
        walls = [edge2wall(RoofPolygon[idx], RoofPolygon[idx+1])
                 if idx != len(RoofPolygon)-1 else edge2wall(RoofPolygon[idx], RoofPolygon[0]) 
                 for idx in range(len(RoofPolygon)) ]
        
        
        # Save orientation information of walls (CCW in the x, y coordinate sys. based on the center of a wall polygon)
        wallAng, wallNormVec = roof2wallNormVec(RoofPolygon)
        
        # Generate windows (Wall with WWR)
        windows = [wall2window(wall, wwr = wwr) for wall in walls] 
        
        
        ## 외피 IDF 속성정보 생성 (EnergyPlus)
        # Name: 외피이름
        # ZoneName: 매칭되는 zone 이름
        # BoundCond: 인접면 조건 (e.g. outdoors, surface)
        # SunExposure, WindExposure: 태양 및 바람 노출여부
        
        WallName, WallZoneName, WallBoundCond, WallBoundCondObj, WallSunExposure, WallWindExposure = gen_WallProp(walls, n_floor) # wall property name 
        WindowName, WindowSurType, WindowWallName, WindowBoundCondObj = gen_WindowProp(windows, n_floor) # window property name 
        FloorName, FloorZoneName, FloorBoundCond, FloorBoundCondObj, FloorSunExposure, FloorWindExposure = gen_FloorName(floors, n_floor) # floor property name 
        RoofName, RoofZoneName, RoofBoundCond, RoofBoundCondObj, RoofSunExposure, RoofWindExposure = gen_RoofName(roofs, n_floor) # roof property name
        
        ## To save wall orientations info
        # wall_info = {}
        # wall_info[bldg_idx] = (WallName, wallAng*n_floor) 
        
        ## modeling surrounding buildings (Shading objects)     
        # modeling only opaque walls of surrounding buildings 
        
        shadingWalls = []     
        for idx, shadingObj in inter.iterrows():
        
            shadingGeometry = shadingObj['geometry'] 
            shadingFloorNumber = shadingObj[self.floorNumberColumn] 
            shadingRoofPolygon = poly2roof(shadingGeometry, Z_height*shadingFloorNumber) 
            shadingWall = [edge2wall(shadingRoofPolygon[idx], shadingRoofPolygon[idx+1]) 
                           if idx != len(shadingRoofPolygon)-1 else edge2wall(shadingRoofPolygon[idx], shadingRoofPolygon[0]) 
                           for idx in range(len(shadingRoofPolygon)) ]
        
            shadingWalls.append(shadingWall)        
        
        
        # find epw files
        # all_items = os.listdir('.')
        # epwFile = [item for item in all_items if os.path.isfile(os.path.join('.', item)) and item.endswith('.epw')][0]
    
        
        # generate a idf
        idf = IDF(os.path.join(MinimalIDFpath, minimalIDF), epw = self.epwFileName)
        
        setattr(idf.idfobjects['BUILDING'][0], 'Solar_Distribution', 'FullExterior')
        
        idf = idf_zones(idf, zone_name, zone_height)
        idf = gen_zonelist(idf, zone_name)
        idf = idf_walls(idf, walls, WallName, WallBoundCond, WallBoundCondObj, WallSunExposure, WallWindExposure, WallZoneName, Z_height)        
        idf = idf_windows(idf, windows, WindowName, WindowSurType, WindowWallName, WindowBoundCondObj, Z_height)
        idf = idf_roofs(idf, roofs, RoofName, RoofBoundCond, RoofBoundCondObj, RoofSunExposure, RoofWindExposure, RoofZoneName)    
        idf = idf_floors(idf, floors, FloorName, FloorBoundCond, FloorBoundCondObj, FloorSunExposure, FloorWindExposure, FloorZoneName)    
        idf = idf_shadingObjs(idf, shadingWalls)
        
        idf = set_Ins_thickness(idf, Uwall, Uroof, Ufloor)
        idf = set_glazing(idf, Uwindow)
        
        # this_savepath = os.path.join(savepath, EPWRegion)
        idfSavePath = os.path.join(self.savePath, newIDF)
        idf.saveas(idfSavePath)
        
        
        if run_simluation: #### in progress ####
            print('Running... ' + newIDF)
            idf2run= IDF(idfSavePath, self.epwPath)
            idf2run.run(output_prefix = 'Bldg_ID_' + str(bldgID), output_suffix = 'L', 
                        readvars=True, output_directory = self.savePath, ep_version="9-0-1")        
        
        else:
            
            pass
        
        
        print('!!! Done !!!')

        # copy2(os.path.join(epwpath, EPWFname), os.path.join(this_savepath, EPWFname))

        

