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
        shpPath: .shp 파일 디렉토리
        epwPath: .epw 파일 디렉토리
        savePath: 생성되는 IDF 및 시뮬레이션 결과 파일 저장 디렉토리
        idColumn: Building ID Column 명
        floorNumberColumn: 지상층수 Column 명
        useTypeColumn: 용도코드 Column 명 (예: 03000)
        builtDateColumn: 승인일자 Column 명                
        wsg84: 데이터 Polygon 좌표가 위경도 좌표일 경우 True
            
        '''
        
        # path
        cpath = os.getcwd() # 작업폴더 (current path)    
        self.MinimalIDFpath = os.path.join(cpath, 'IDF') # Minimal IDF 디렉토리
        self.iddpath = genIDD() # IDD 파일 생성

        # eppy
        IDF.setiddname(self.iddpath) # IDD 위치 지정
                                       
        self.data_ = read_file(shpPath, encoding = 'cp949')
        
        Uvalues = insMeta # 단열기준
        UseType = load_useMeta() # 건물용도
        
        self.epwPath = epwPath
        self.savePath = savePath
        
        self.epwFileName = self.epwPath.split(sep='\\')[-1]
        region, lat, lon, tzone, elev = get_epwinfo(self.epwPath)

        Projection = Proj(self.data_.crs)
        
        self.floorNumberColumn = floorNumberColumn
        self.idColumn = idColumn
        self.useTypeColumn = useTypeColumn
        self.builtDateColumn = builtDateColumn
        
        # GIS데이터 - 메타데이터 병합
        self.data_ = self.data_.join(UseType.set_index('BDTYP_CD')[['IDF_type', '주거여부']], on = self.useTypeColumn) 
        self.data_[self.builtDateColumn].fillna('-1', inplace=True) # 누락데이터 처리 (-1)
        n_data = self.data_.shape[0]
            
        # 승인일자 발췌
        # UseAprDay = self.data_[builtDateColumn].copy() # 원본 수정 배제 ### 컬럼명 받기
        
        # 추가 데이터 초기화
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
           
            EPWFname[idx] = self.epwFileName # EPW 파일명
            EPWRegion[idx] = region # EPW 지역명
            EPWLat[idx] = lat # 위도
            EPWLon[idx] = lon # 경도   
            EPWTzone[idx] = tzone # 시간대
            EPWElev[idx] = elev # 해발고도
            
            new_date = row[self.builtDateColumn]
            date_apply[idx] = new_date 
            
            # 승인일자와 가장 가까운 단열기준 시점 탐색
            chk = 0
            for key in Uvalues.keys():
                if int(new_date) >= int(key):
                    sht_name = key
                    chk = 1
                    break        
            
            sht_name = '19790916' if chk == 0 else sht_name # 79.9.16 이전 승인
            
            # 외피 열관류율 탐색
            UvalueTable = Uvalues[sht_name]
            SI_GUN_GU = '11' # 시군구 코드 서울로 적용
            
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
            
            # date_apply = parallel_work(UseAprDay, 4) # 병렬연산
        
        # 신규 데이터 추가
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
        
        self.data_.projection = Projection # 투영체 저장
        
        # 누락 정보 채움 
        self.data_['IDF_type'].fillna('off', inplace = True) # 용도 (업무시설 가정)
        self.data_[self.floorNumberColumn].fillna(0, inplace = True) # 지상층수 (0)    
        
        self.data_[self.idColumn].fillna('dummy', inplace = True) # 건물일련번호
        self.data_[self.useTypeColumn].fillna('dummy', inplace = True) # 용도
        
        # MultiPolygon 여부 -> 추후 MultiPolygon 처리 추가 개발 예정
        self.data_['is_MultiPolygon'] = (self.data_.geometry.type == 'MultiPolygon').tolist()
        
        target_crs = {'proj': 'tmerc', 'lat_0': 38, 'lon_0': 127.5, 'k': 0.9996, 'x_0': 1000000, 'y_0': 2000000, 'ellps': 'GRS80', 'units': 'm', 'no_defs': True} 
                    
        self.data_.crs = target_crs
        self.my_proj = Proj(self.data_.crs)
        self.data_.reset_index(inplace = True)       
        

        if wsg84: # 좌표가 위경도인 데이터셋은 UTM으로 변환 필요


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
        
    def processedDataExport(self): # 전처리된 데이터프레임 출력
        
        return self.data_ 
    
    def main(self, bldgID,  wwr = 0.4, Z_height = 3.0, boundaryBuffer = 30, run_simluation = True):
        
        '''
        bldgID: Building ID
        wwr: Wall-to-Window Ratio (창면적비)
        Z_height: 층고 높이 (m)
        boundaryBuffer: 입력된 건물로부터 몇 m 건물까지 주변 건물로 모델링하는지
        run_simluation: 시뮬레이션까지 돌릴지말지
            
        '''
        
        
        cpath = os.getcwd() # 작업폴더 (current path)    
        MinimalIDFpath = os.path.join(cpath, 'IDF') # Minimal IDF 디렉토리
        
        # 벽체 정보 저장공간 (dictionary)
        Target_bldg = self.data_[self.data_[self.idColumn] == bldgID].iloc[0]
        bldg_idx = self.data_.index[self.data_[self.idColumn] == bldgID][0]

        # IDF 파일명
        newIDF = 'Bldg_ID_' + str(bldgID) + '.idf'
        print('Generating... ' + newIDF)
        
        # 기타 건물정보
        n_floor = int(Target_bldg[self.floorNumberColumn]) # 지상층수
        
        if n_floor == 0:          
            raise Exception('지상층수가 0층입니다.')
            # print('지상층수가 0층입니다.')
            # continue

        built_year = int(Target_bldg['Date_apply'][:4]) # 승인일자에서 준공연도 추출
        use_type = Target_bldg['IDF_type'] # 용도 (IDF) 
        
        # 열관류율
        Uwall = float(Target_bldg['U_wall'])
        Uroof = float(Target_bldg['U_roof'])
        Ufloor = float(Target_bldg['U_floor'])
        Uwindow = float(Target_bldg['U_window'])
        
        
        # 준공연도에 따른 Minimal IDF 파일 선정
        if built_year < 1981:
            minimalIDF = use_type+'1.idf'
        elif built_year < 1988:
            minimalIDF = use_type+'2.idf'
        elif built_year < 2002:
            minimalIDF = use_type+'3.idf'
        else:
            minimalIDF = use_type+'4.idf'
        
        otherIdx = self.data_[self.data_[self.idColumn] != bldgID].index
        
        
        # Polygon 좌표 보정 (원점: 건물 중심)
        cent = Target_bldg['geometry'].centroid # 중심좌표
        bx, by = cent.x, cent.y # 건물중심 XY 좌표
        blon, blat = self.my_proj(bx, by, inverse = True) # 건물중심 위도 & 경도

        
        # 대상건물 좌표 보정 후 Polygon
        convertedData = move2Wstation(self.data_, blon, blat)
        poly = convertedData.loc[bldg_idx].geometry
        poly.simplify(30)
        
        # 좌표 보정 후 다른건물 Polygon 리스트 생성 (전체 Polygon 데이터 중, 대상건물 제외)
        convertedData = convertedData.loc[otherIdx]
           
        
        # 대상건물 Polygon 삼각분할 (Ear-Clipping 알고리즘) -> EnergyPlus 형상 정보 관련 에러 방지
        # 오목평면 (concave plane) -> 볼록평면화 (convex planes)
        poly_triangulated = triangulateEarclip(poly)
        
        # 대상건물 Zone 정보 생성 (zone 이름, zone 층고) -> zone XYZ 원점은 (0,0,0)
        zone_name, zone_height = gen_zones(n_floor, height = Z_height)
        
        # 인접건물 선별
        inter, new_bbox = findSurrBldgs(convertedData, poly, boundaryBuffer = boundaryBuffer) # extension: 바닥 최외곽에서 확장 거리 (m)    
        inter = inter[inter.geometry.type != 'MultiPolygon'] # MultiPolygon 제외 -> 추후 Multi Polygon 쪼개는 방법 추가
        inter = inter[inter[self.floorNumberColumn] > 0] # 지상층수 1층이상만
        
        # 대상건물 외피 Polygon 생성 (XYZ)
        
        # 1층 지붕 외곽 Polygon (0. 삼각분할 이전, 1. 위에서 바닥을 바라보았을 때 반시계방향 회전, 2. 윗방향으로 층고만큼 offset)        
        RoofPolygon = poly2roof(poly, Z_height) # 외벽 좌표 생성하는데 활용 -> 1층의 천장 높이의 좌표 점 List    
        # 바닥, 지붕 Polygon
        floors, roofs = gen_horizontal_vertex(poly_triangulated, n_floor, Z_height) # 각 층의 바닥 및 천장 좌표 생성
        
        # # 아래 위 층의 천장 좌표 활용해서 외벽 Polygon 좌표 생성
        walls = [edge2wall(RoofPolygon[idx], RoofPolygon[idx+1])
                 if idx != len(RoofPolygon)-1 else edge2wall(RoofPolygon[idx], RoofPolygon[0]) 
                 for idx in range(len(RoofPolygon)) ]
        
        
        # 외벽 방위 (XY 좌표계에서 반시계방향 회전 기준, 법선각도 (degree), 법선벡터 (XY), 외벽 중심좌표 (3D))
        wallAng, wallNormVec = roof2wallNormVec(RoofPolygon) # 법선각도, 법선벡터
        
        # 창호 Polygon (외벽 Polygon & 창면적비 조합)   
        windows = [wall2window(wall, wwr = wwr) for wall in walls] #WWR 고정
        
        
        ## 외피 IDF 속성정보 생성 (EnergyPlus)
        # Name: 외피이름
        # ZoneName: 매칭되는 zone 이름
        # BoundCond: 인접면 조건 (e.g. outdoors, surface)
        # SunExposure, WindExposure: 태양 및 바람 노출여부
        
        WallName, WallZoneName, WallBoundCond, WallBoundCondObj, WallSunExposure, WallWindExposure = gen_WallProp(walls, n_floor) # wall property name 입력
        WindowName, WindowSurType, WindowWallName, WindowBoundCondObj = gen_WindowProp(windows, n_floor) # window property name 입력
        FloorName, FloorZoneName, FloorBoundCond, FloorBoundCondObj, FloorSunExposure, FloorWindExposure = gen_FloorName(floors, n_floor) # floor property name 입력
        RoofName, RoofZoneName, RoofBoundCond, RoofBoundCondObj, RoofSunExposure, RoofWindExposure = gen_RoofName(roofs, n_floor) # roof property name 입력
        
        ## 벽 방위 저장
        # wall_info = {}
        # wall_info[bldg_idx] = (WallName, wallAng*n_floor) # 각도로 방위 판단하기 위함
        
        ## 인접건물 모델링 (음영 객체)     
        # 인접건물은 외벽 (불투명)만 배치
        shadingWalls = []     
        # 인접건물 외벽정보 생성
        for idx, shadingObj in inter.iterrows():
        
            shadingGeometry = shadingObj['geometry'] # 인접건물 Polygon
            shadingFloorNumber = shadingObj[self.floorNumberColumn] # 인접건물 지상층수
            shadingRoofPolygon = poly2roof(shadingGeometry, Z_height*shadingFloorNumber) # 인접건물 지붕외곽 Polygon (외벽생성에 활용)
            shadingWall = [edge2wall(shadingRoofPolygon[idx], shadingRoofPolygon[idx+1]) 
                           if idx != len(shadingRoofPolygon)-1 else edge2wall(shadingRoofPolygon[idx], shadingRoofPolygon[0]) 
                           for idx in range(len(shadingRoofPolygon)) ]
        
            shadingWalls.append(shadingWall)        
        
        
        # epw 파일 찾기      
        # all_items = os.listdir('.')
        # epwFile = [item for item in all_items if os.path.isfile(os.path.join('.', item)) and item.endswith('.epw')][0]
    
        
        # 대상건물의 IDF 생성
        idf = IDF(os.path.join(MinimalIDFpath, minimalIDF), epw = self.epwFileName) # 할당된 idf 파일 불러오기
        
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
            idf2run.run(output_prefix = 'Bldg_ID_' + str(bldgID), output_suffix = 'L', readvars=True, output_directory = self.savePath, ep_version="9-0-1")        
        
        else:
            
            pass
        
        
        print('!!! Done !!!')

        # copy2(os.path.join(epwpath, EPWFname), os.path.join(this_savepath, EPWFname))

        

