# -*- coding: utf-8 -*-
"""
Created on Mon Jul  3 18:20:48 2023

@author: YUNDAM
"""

import os
from shapely.geometry import Polygon, box
import numpy as np
from geopandas import GeoDataFrame, GeoSeries, overlay
from copy import deepcopy
from tripy import earclip
from tkinter import Tk
from tkinter.filedialog import askdirectory


#%%

def move2Wstation(my_gpd, bx, by): 
    """
    Calibrate existing XY coordinates 
    based on the location of the weather station 

    Parameters
    ----------
    my_gpd : geopandas.geodataframe.GeoDataFrame
        GIS data transformed to geopandas DataFrame.
    bx, by : float
        centroid of target building (XY).

    Returns
    -------
    my_gpd2 : geopandas.geodataframe.GeoDataFrame
        calibrated GIS data ( XY coords of weather station -> (0,0) ).

    """
    
    my_gpd2 = deepcopy(my_gpd)
    fixed_gpd = my_gpd.translate(xoff = -bx, yoff = -by)
    my_gpd2['geometry'] = fixed_gpd
    return my_gpd2


def ext_bbox(poly, offset = 60, crs = {'proj': 'tmerc', 'lat_0': 38, 'lon_0': 127.5, 'k': 0.9996, 'x_0': 1000000, 'y_0': 2000000, 'ellps': 'GRS80', 'units': 'm', 'no_defs': True}):
    """
    Generate extended bbox   

    Args:
        poly (shapely.geometry.polygon.Polygon): Polygon data of target building.
        offset (float, optional): bbox extension length (m). Defaults to 20.
        crs (str, optional): coordinate reference system (CRS). Defaults to '+proj=tmerc +lat_0=38 +lon_0=127.0028902777778 ++=1 +x_0=200000 +y_0=500000 +ellps=bessel +towgs84=-115.8,474.99,674.11,1.16,-2.31,-1.63,6.43 +units=m +no_defs'.

    Returns:
        new_bbox_gpd (geopandas.geodataframe.GeoDataFrame): building's extended bbox.

    """
    
    bbox = poly.bounds
    ll_x, ll_y, ur_x, ur_y = bbox[0]-offset, bbox[1]-offset, bbox[2]+offset, bbox[3]+offset
    new_bbox = box(ll_x, ll_y, ur_x, ur_y)
    new_bbox_gpd = GeoDataFrame(GeoSeries(new_bbox), columns = ['geometry'])
    new_bbox_gpd.crs = crs
    return new_bbox_gpd

#%%
def findSurrBldgs(polygons, poly, boundaryBuffer = 60, crs = {'proj': 'tmerc', 'lat_0': 38, 'lon_0': 127.5, 'k': 0.9996, 'x_0': 1000000, 'y_0': 2000000, 'ellps': 'GRS80', 'units': 'm', 'no_defs': True}):
    """
    Find Surrounding buildings  

    Parameters
    ----------
    polygons : geopandas.geodataframe.GeoDataFrame
        GIS data transformed to geopandas DataFrame (target building exception).
    poly : shapely.geometry.polygon.Polygon
        Polygon data of target building.

    crs : TYPE, optional
        DESCRIPTION. The default is '+proj=tmerc +lat_0=38 +lon_0=127.0028902777778 ++=1 +x_0=200000 +y_0=500000 +ellps=bessel +towgs84=-115.8,474.99,674.11,1.16,-2.31,-1.63,6.43 +units=m +no_defs'.

    Returns
    -------
    surrBldgs : geopandas.geodataframe.GeoDataFrame
        surrounding building data.
    new_bbox: geopandas.geodataframe.GeoDataFrame
        building's extended bbox..

    """

    bufferPolygon = poly.buffer(boundaryBuffer, join_style = 2)
    bufferPolygon_ = GeoDataFrame(GeoSeries(bufferPolygon), columns = ['geometry'])
    bufferPolygon_.crs = crs
    surrBldgs = overlay(bufferPolygon_, polygons, how='intersection')
    return surrBldgs, bufferPolygon 
    

        
#%% 

def polygon2pts(polygon, ccw=True):
    """
    Vertices from 2D polygon

    Args:
        polygon (shapely.geometry.polygon.Polygon): shapely polygon.
        ccw (bool, optional): whether counter-clockwise. Defaults to True.

    Returns:
        points (list of tuples): 2D vertices of polygon.
        n_points (integer): number of vertices.
        
    """
    
    is_ccw = polygon.exterior.is_ccw
    
    points = list(zip(*polygon.exterior.coords.xy))
    
    if is_ccw != ccw:
        points.reverse()
    
    n_points = len(points) - 1
    return points, n_points


#%%

def calc_NormVec2D(pt1, pt2):
    """
    Detect 2D edge's outward-facing normal vector (angle for x-axis) 
    using 2 XY points
    
    assumption: counter-clockwise polygon (footprint)

    Args:
        pt1 (tuple): edge's 1st XY point.
        pt2 (tuple): edge's 2nd XY point.

    Returns:
        deg (float): angle of edge's outward-facing normal vector.
        unit_norm (tuple): edge's outward-facing normal vector (XY).

    """
    
    vector_edge = np.array(pt2) - np.array(pt1)
        
    dx, dy = vector_edge
    norm = (dy, -dx) # outward-facing 2D normal vector (counter-clowise polygon)
    
    norm_np = np.array(norm) # convert nsormal vector as np.array
    unit_norm = norm_np / np.linalg.norm(norm_np) # make unit-vector
    unit_norm = tuple(unit_norm)

    rad = np.math.atan2(np.linalg.det([np.array([1,0]),unit_norm]),np.dot(np.array([1,0]),unit_norm))


    deg = np.rad2deg(rad) # convert radian to degree
    return deg, unit_norm


def roof2wallNormVec(roof):
    """
    Detect wall's outward-facing normal vector (angle for x-axis) 
    using roof's edge
    
    assumption. 1: counter-clockwise polygon (roof)    

    Args:
        roof (list of tuples): roof's XYZ coordinates

    Returns:
        wallAng (list): angle of walls' outward-facing normal vector for x-axis.
        wallNormVec (list of tuples): awalls' outward-facing normal unit vector for x-axis.

    """
    n_roof = len(roof)
    wallNormVec, wallAng = [0]*n_roof, [0]*n_roof

    for idx in range(len(roof)):
        pt1, pt2 = roof[idx:idx+2] if idx != len(roof)-1 else [roof[idx], roof[0]]
        angle, NormVec = calc_NormVec2D(pt1[:-1], pt2[:-1])

        wallAng[idx] = angle
        wallNormVec[idx] = NormVec
        
    return wallAng, wallNormVec    
        

def edge2wall(pt1, pt2):
    """
    Make wall's XYZ coordinates from roof's edge
    
    assumption. 1: counter-clockwise polygon (roof)
    assumption. 2: rectangular wall (conter-clockwise)    

    Args:
        pt1 (tuple): edge's 1st XY point.
        pt2 (tuple): edge's 2nd XY point.

    Returns:
        wall_coords (list): walls' XYZ coordinates. 
        corresponded to polygon's individual edge.

    """
    ll, lr = list(pt1), list(pt2)
    ll[-1], lr[-1] = 0, 0 # wall's lower-left vertex
    wall_coords = [pt1, tuple(ll), tuple(lr), pt2]
    return wall_coords


def check_Depth(width, height, offsets):
    """
    Validate calculated offset of wall's coordinates for making window's coordinates

    Args:
        width (float): wall width (m).
        height (float): wall height (m).
        offsets (list): calculated offset length (m).

    Returns:
        valid_offset (float): valid offset length (m).

    """
    valid_offset = 0
    
    for offset in offsets:
        is_valid = True if (width - 2*offset) > 0 else False
        is_valid = True if (height - 2*offset) > 0 else False 
        if is_valid:
            valid_offset = offset
        
    return valid_offset


def windowCoords(wall_np, offset):
    """
    Pad wall's coordinates for making window coordinates.

    assumption. 1: Rectangular wall (conter-clockwise, left-upper corner)

    Args:
        wall (np.array): wall's 3D coordinates.
        offset (float): offset length (m).

    Returns:
        window (list of tuples): window's 3D coordinates.

    """

    window_np = np.zeros_like(wall_np)
    

    # padding direction    
    unit_horz = np.array(wall_np[2]) - np.array(wall_np[1])
    unit_vert = np.array(wall_np[3]) - np.array(wall_np[2])
 
    
    unit_horz = unit_horz/np.linalg.norm(unit_horz)
    unit_vert = unit_vert/np.linalg.norm(unit_vert)
    

    
    move_horz = unit_horz*offset
    move_vert = unit_vert*offset
    
    window_np[0] = wall_np[0] + move_horz - move_vert
    window_np[1] = wall_np[1] + move_horz + move_vert
    window_np[2] = wall_np[2] - move_horz + move_vert  
    window_np[3] = wall_np[3] - move_horz - move_vert 

    window = window_np.tolist() # list of list
    window = [tuple(XYZ) for XYZ in window]
    
    return window

          
def wall2window(wall_coords, wwr = 0.3):
    """
    Make window's XYZ coordinates in existng wall (rectangular & count-clockwise).
    
    offset_length formula (quadratic):
        width*height*wwr = (width - 2*offset)*(height - 2*offset)
        -> solve "offset"
    
    assumption. 1: rectangular wall (counter-clockwise, upper-left corner)
    
    Args:
        wall_coords (list of tuples): wall's XYZ coordinates. 
        wwr (float, optional): window-wall ratio (0-1). Defaults to 0.3.

    Returns:
        window_coords (list of tuples): window's XYZ coordinates.

    """

    wall_np = np.array(wall_coords)
    
    # wall dimension
    width = np.linalg.norm((wall_np[2]-wall_np[1])) 
    height = np.linalg.norm((wall_np[1]-wall_np[0]))    
    
    p_polynomial = [4, -2*(width+height), width*height -(wwr)*width*height]
    offsets = np.roots(p_polynomial) # find offset corresonded to window-wall ratio
    valid_offset = check_Depth(width, height, offsets)
    
    
    window_coords = windowCoords(wall_np, valid_offset)
    
    return window_coords


def poly2floor(polygon, Zoffset = 0):
    """
    Make floor coordinates using footprint's polygon.
    (rotation: clockwise)

    Args:
        polygon (shapely.geometry.polygon.Polygon): shapely polygon.

    Returns:
        floor3D (list of tuples): floor coordinates.

    """
    floor2D, __ = polygon2pts(polygon, ccw=False)
    if floor2D[0] == floor2D[-1]:
        floor2D = floor2D[:-1]
    floor3D = [(*vertex, Zoffset) for vertex in floor2D]    
    return floor3D    


def poly2roof(polygon, Zoffset = 3.0):
    """
    Make roof coordinates using footprint's polygon.
    (rotation: counter-clockwise)

    Args:
        polygon (TYPE): DESCRIPTION.
        height (TYPE, optional): DESCRIPTION. Defaults to 3.0.

    Returns:
        roof3D (TYPE): DESCRIPTION.

    """
    roof2D, __ = polygon2pts(polygon, ccw=True)
    if roof2D[0] == roof2D[-1]:
        roof2D = roof2D[:-1]
    roof3D = [(*vertex, Zoffset) for vertex in roof2D]    
    return roof3D        

#%%

def gen_WallProp(walls, n_floor):
    n_eachwall = len(walls)
    n_wall = n_eachwall*n_floor
    
    WallBoundCond = ['Outdoors']*n_wall
    WallBoundCondObj = ['']*n_wall
    WallSunExposure = ['SunExposed']*n_wall
    WallWindExposure = ['WindExposed']*n_wall

    WallName, WallZoneName = [], []

    for idx1 in range(n_floor):
        WallName += ['wall_%d_%d' %(idx2+1, idx1+1) for idx2 in range(n_eachwall)]
        WallZoneName += ['zone_%d' %(idx1+1) for idx2 in range(n_eachwall)]
        
    return WallName, WallZoneName, WallBoundCond, WallBoundCondObj, WallSunExposure, WallWindExposure 


def gen_WindowProp(windows, n_floor, surtype = 'Window'):
    n_eachwindow = len(windows)
    n_window = n_eachwindow*n_floor
    
    WindowSurType = [surtype]*n_window
    WindowBoundCondObj = ['']*n_window

    WindowName, WindowWallName = [], []
    for idx1 in range(n_floor):
        WindowWallName += ['wall_%d_%d' %(idx2+1, idx1+1) for idx2 in range(n_eachwindow)]        
        WindowName += ['window_%d_%d' %(idx2+1, idx1+1) for idx2 in range(n_eachwindow)]
        
    return WindowName, WindowSurType, WindowWallName, WindowBoundCondObj


def gen_FloorName(floors, n_floor):
    n_eachfloor = len(floors)//n_floor # number of roofs per each floor
    
    FloorBoundCond = ['Ground']*n_eachfloor + ['Surface']*( (n_floor-1)*n_eachfloor)
    FloorSunExposure = ['NoSun']*n_eachfloor*n_floor
    FloorWindExposure = ['NoWind']*n_eachfloor*n_floor


    FloorBoundCondObj = ['']*n_eachfloor
    FloorZoneName = ['zone_1']*n_eachfloor
    FloorName = ['floor_{}_1'.format(idx2+1) for idx2 in range(n_eachfloor)]
    
    for idx in range(1, n_floor):

        FloorBoundCondObj += ['roof_%d_%d' %(idx2+1, idx) for idx2 in range(n_eachfloor)]
        FloorName += ['floor_%d_%d' %(idx2+1, idx+1) for idx2 in range(n_eachfloor)]
        FloorZoneName += ['zone_{}'.format(idx+1)]*n_eachfloor

    return FloorName, FloorZoneName, FloorBoundCond, FloorBoundCondObj, FloorSunExposure, FloorWindExposure 


def gen_RoofName(roofs, n_floor):
    n_eachroof = len(roofs)//n_floor # number of roofs per each floor
    
    RoofBoundCond = ['Surface']*( (n_floor-1) * n_eachroof) + ['Outdoors']*n_eachroof
    RoofSunExposure = ['NoSun']* ( (n_floor-1) * n_eachroof) + ['SunExposed']*n_eachroof
    RoofWindExposure = ['NoWind']*( (n_floor-1) * n_eachroof) + ['WindExposed']*n_eachroof 

    RoofZoneName, RoofName, RoofBoundCondObj = [], [], []

    for idx in range(n_floor):

        RoofBoundCondObj += ['floor_{}_{}'.format(idx2+1, idx+2) for idx2 in range(n_eachroof)] # adjacent floor of each floor
        RoofName += ['roof_{}_{}'.format(idx2+1, idx+1) for idx2 in range(n_eachroof)] 
        RoofZoneName += ['zone_{}'.format(idx+1)]*n_eachroof # zone name w.r.t each roof

    RoofBoundCondObj[-n_eachroof:] = ['']*n_eachroof   
        
    return RoofName, RoofZoneName, RoofBoundCond, RoofBoundCondObj, RoofSunExposure, RoofWindExposure


#%%

def gen_zones(n_floor, height = 3.5):
    Zone_Name = ['zone_%d' %(idx+1) for idx in range(n_floor)]
    Zone_height = [height for idx in range(n_floor)]    

    return Zone_Name, Zone_height


def idf_zones(idf, Zname, Zheight):
    for zname, height in zip(Zname, Zheight):        
        idf.newidfobject('ZONE')
        target_obj = idf.idfobjects['ZONE'][-1]
        
        setattr(target_obj, 'Name', zname)
        setattr(target_obj, 'X_Origin', 0)
        setattr(target_obj, 'Y_Origin', 0)        
        setattr(target_obj, 'Z_Origin', 0)                
        setattr(target_obj, 'Ceiling_Height', height)
    return idf        


def gen_zonelist(idf, Zone_Name):
    idf.newidfobject('ZONELIST')
    zlist = idf.idfobjects['ZONELIST'][0]
    people = idf.idfobjects['PEOPLE'][0]
    lights = idf.idfobjects['LIGHTS'][0]
    equip = idf.idfobjects['ELECTRICEQUIPMENT'][0]
    infil = idf.idfobjects['ZONEINFILTRATION:DESIGNFLOWRATE'][0]

    IdealHVAC = idf.idfobjects['HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM']
    
    setattr(zlist, 'Name', 'zonelist')
    setattr(people, 'Zone_or_ZoneList_Name', 'zonelist')
    setattr(lights, 'Zone_or_ZoneList_Name', 'zonelist')
    setattr(equip, 'Zone_or_ZoneList_Name', 'zonelist')
    setattr(infil, 'Zone_or_ZoneList_Name', 'zonelist')
    for idx, zone in enumerate(Zone_Name):
        setattr(zlist, 'Zone_{}_Name'.format(idx+1), zone)
        if idx != 0:
            idf.newidfobject('HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM')
        setattr(IdealHVAC[idx], 'Zone_Name', zone)
        setattr(IdealHVAC[idx], 'Template_Thermostat_Name', 'thermostat')
        setattr(IdealHVAC[idx], 'Design_Specification_Outdoor_Air_Object_Name', 'OA_design')        
    return idf            

#%%

def bldgSurface_property(surface_obj, name, surtype, bound, boundobj, sun, wind, zone):
        setattr(surface_obj, 'Name', name)
        setattr(surface_obj, 'Surface_Type', surtype)        
        setattr(surface_obj, 'Outside_Boundary_Condition', bound)
        setattr(surface_obj, 'Outside_Boundary_Condition_Object', boundobj)  
        setattr(surface_obj, 'Sun_Exposure', sun)
        setattr(surface_obj, 'Wind_Exposure', wind)
        setattr(surface_obj, 'Zone_Name', zone)


def idf_walls(idf, walls, WallName, WallBoundCond, WallBoundCondObj, WallSunExposure, WallWindExposure, WallZoneName, height = 3.5):
    objname = 'BUILDINGSURFACE:DETAILED'

    n_floor = int(len(WallName) / len(walls))
    n_wall = len(walls)

    for name_, bound_, boundobj_, sun_, wind_, zone_ in zip(WallName, WallBoundCond, WallBoundCondObj, WallSunExposure, WallWindExposure, WallZoneName):
        idf.newidfobject(objname)
        target_obj = idf.idfobjects[objname][-1]
        bldgSurface_property(target_obj, name_, 'Wall', bound_, boundobj_, sun_, wind_, zone_)
        
    cnt = 0
    for idx1 in range(n_floor):
        for idx2 in range(n_wall):        
            target_obj = idf.idfobjects[objname][cnt]
            my_wall = walls[idx2]

            for idx3 in range(len(my_wall)):
                x, y, z = my_wall[idx3]
                
                setattr(target_obj, 'Construction_Name', 'wall')                
                setattr(target_obj, 'Vertex_%d_Xcoordinate' %(idx3+1), x)
                setattr(target_obj, 'Vertex_%d_Ycoordinate' %(idx3+1), y)
                setattr(target_obj, 'Vertex_%d_Zcoordinate' %(idx3+1), z + height*idx1)   
            cnt += 1    
    return idf                


def idf_windows(idf, windows, WindowName, WindowSurType, WindowWallName, WindowBoundCondObj, height = 3.5):
    objname = 'FENESTRATIONSURFACE:DETAILED'

    n_window = len(windows)
    n_floor = int(len(WindowName) / n_window)


    for name_, surtype_, wallname_, boundobj_ in zip(WindowName, WindowSurType, WindowWallName, WindowBoundCondObj):
        idf.newidfobject(objname)
        target_obj = idf.idfobjects[objname][-1]
        
        setattr(target_obj, 'Name', name_)
        setattr(target_obj, 'Construction_Name', 'window')                                
        setattr(target_obj, 'Surface_Type', surtype_)        
        setattr(target_obj, 'Building_Surface_Name', wallname_)                
        setattr(target_obj, 'Outside_Boundary_Condition_Object', boundobj_)

    cnt = 0
    for idx1 in range(n_floor):
        for idx2 in range(n_window):        
            target_obj = idf.idfobjects[objname][cnt]
            my_window = windows[idx2]

            for idx3, vertex in enumerate(my_window):
                x, y, z = vertex
                setattr(target_obj, 'Vertex_%d_Xcoordinate' %(idx3+1), x)
                setattr(target_obj, 'Vertex_%d_Ycoordinate' %(idx3+1), y)
                setattr(target_obj, 'Vertex_%d_Zcoordinate' %(idx3+1), z + height*idx1)   
            cnt += 1    
    return idf


def idf_roofs(idf, roof, RoofName, RoofBoundCond, RoofBoundCondObj, RoofSunExposure, RoofWindExposure, RoofZoneName):
    objname = 'BUILDINGSURFACE:DETAILED'
    n_roof = len(roof)
    
    cnt = 1
    for name_, bound_, boundobj_, sun_, wind_, zone_, surface_ in zip(RoofName, RoofBoundCond, RoofBoundCondObj, RoofSunExposure, RoofWindExposure, RoofZoneName, roof):

        # property assignment
        idf.newidfobject(objname)
        target_obj = idf.idfobjects[objname][-1]        
        surtype = 'Ceiling' if bound_.upper() == 'Surface' else 'Roof'        
        bldgSurface_property(target_obj, name_, surtype, bound_, boundobj_, sun_, wind_, zone_)
        
        # vertex placement
        for idx3, vertex in enumerate(surface_):
            x, y, z = vertex
            setattr(target_obj, 'Vertex_%d_Xcoordinate' %(idx3+1), x)
            setattr(target_obj, 'Vertex_%d_Ycoordinate' %(idx3+1), y)
            setattr(target_obj, 'Vertex_%d_Zcoordinate' %(idx3+1), z)

        # Construction name (cnt==n_roof -> 최상층)
        constname = 'roof_' if cnt == n_roof else 'roof'
        setattr(target_obj, 'Construction_Name', constname)
        cnt += 1
                    
    return idf               


def idf_floors(idf, floor, FloorName, FloorBoundCond, FloorBoundCondObj, FloorSunExposure, FloorWindExposure, FloorZoneName):
    objname = 'BUILDINGSURFACE:DETAILED'

    cnt = 0
    for name_, bound_, boundobj_, sun_, wind_, zone_, surface_ in zip(FloorName, FloorBoundCond, FloorBoundCondObj, FloorSunExposure, FloorWindExposure, FloorZoneName, floor):

        # property assignment
        idf.newidfobject(objname)
        target_obj = idf.idfobjects[objname][-1]
        
        bldgSurface_property(target_obj, name_, 'Floor', bound_, boundobj_, sun_, wind_, zone_)
        
        # vertex placement
        for idx3, vertex in enumerate(surface_):
            x, y, z = vertex
            setattr(target_obj, 'Vertex_%d_Xcoordinate' %(idx3+1), x)
            setattr(target_obj, 'Vertex_%d_Ycoordinate' %(idx3+1), y)
            setattr(target_obj, 'Vertex_%d_Zcoordinate' %(idx3+1), z)
            
        # Construction name (cnt==n_roof -> 최상층)
        constname = 'floor_' if cnt == 0 else 'floor'
        setattr(target_obj, 'Construction_Name', constname)
        cnt += 1

    return idf              


def idf_shadingObjs(idf, SHD_walls):
    objname = 'SHADING:BUILDING:DETAILED'

    cnt = 1
    for shd_obj in SHD_walls:
        for walls_ in shd_obj:
            idf.newidfobject(objname)
            target_obj = idf.idfobjects[objname][-1]
            setattr(target_obj, 'Name', 'shd_{}'.format(cnt))
            cnt += 1
            
            for idx, wall in enumerate(walls_):

                x, y, z = wall
                setattr(target_obj, 'Name', 'shd_{}'.format(cnt))
                setattr(target_obj, 'Vertex_%d_Xcoordinate' %(idx+1), x)
                setattr(target_obj, 'Vertex_%d_Ycoordinate' %(idx+1), y)
                setattr(target_obj, 'Vertex_%d_Zcoordinate' %(idx+1), z)   

    return idf                


#%%
def idf_default_opaqueConst(idf, wallconst = 'wall', roofconst = 'roof', floorconst = 'floor'):
    objname = 'buildingsurface:detailed'.upper()
    objs = idf.idfobjects[objname]
    for obj in objs:
        surType = getattr(obj, 'Surface_Type').upper()
        if surType == 'wall'.upper():
            setattr(obj, 'Construction_Name', wallconst)
        elif surType == 'roof'.upper():
            setattr(obj, 'Construction_Name', roofconst)            
        elif surType == 'ceiling'.upper():
            setattr(obj, 'Construction_Name', roofconst)                        
        elif surType == 'Floor'.upper():
            setattr(obj, 'Construction_Name', floorconst)                           
    return idf        

def idf_default_windowConst(idf, constname = 'window'):
    objname = 'fenestrationsurface:detailed'.upper()
    objs = idf.idfobjects[objname]
    for obj in objs:
        setattr(obj, 'Construction_Name', constname)
    return idf        


#%%

def gen_horizontal_vertex(poly_triangulated, n_floor, Z_height):
    floors, roofs = [], []
    
    for idx in range(n_floor):
        floors += [poly2floor(f, Z_height*idx) for f in poly_triangulated]
        roofs += [poly2roof(f, Z_height*(idx+1)) for f in poly_triangulated]    
    return floors,roofs    

#%% Polygon 삼각분할 (ear clip 삼각분할)

def triangulateEarclip(polygon): 
    poly = list(polygon.exterior.coords)
    tri = [Polygon(tr) for tr in earclip(poly) if Polygon(tr).area > 0] # 삼각면 중 면적 0 제거
    return tri


#%% 
def gen_IDFsavepath(data_):
    regionList = data_.EPWRegion.unique()
    root = Tk() # UI on
    UI_title = 'IDF를 생성할 폴더 (디렉토리)를 선택하세요'
    path = askdirectory(parent = root, title = UI_title)
    root.destroy() # UI off    

    if path == '':
        raise Exception("폴더 (디렉토리)를 선택해주세요")
    [os.mkdir(os.path.join(path, region)) for region in regionList if os.path.isdir(os.path.join(path, region)) == False]        
    data_.IDFpath = path
    return path, data_


def check_gisdata(data_):
    if 'crs' not in dir(data_):
        raise Exception("전처리 과정 필요 (preprocessing.Organize_Data 실행)")
    else:
        return data_.crs        



def get_epwinfo(filename):
    """
    Read site location info from epw's header

    Parameters
    ----------
    filename : str
        epw file name.

    Returns
    -------
    loc : str
        site name (e.g. "INCH'ON").
    lat : float
        latitude.
    lon : float
        longitude.
    tzone : float
        time zone.
    elev : float
        elevation.

    """
    
    # read header line
    f = open(filename, 'r')
    while 1:
        line = f.readline()
        sline = line.split(',')
        if sline[0].upper() == 'location'.upper():
            break # current comma-splited line corresponds to epw's header
    
    f.close() # close epw file
    
    # get site information from epw    
    loc = sline[1]
    lat, lon, tzone, elev = sline[6:10]
    
    return loc, lat, lon, tzone, elev
    

def WallIns_thickness(Uvalue):
    d1, k1 = 0.1016, 0.89 # M01 100mm brick
    k2 = 0.03 # I03 75mm insulation board
    Rair = 0.15 # F04 Wall air space resistance
    d3, k3 = 0.019, 0.16 # G01a 19mm gypsum board
    d2 = (1/Uvalue - d1/k1 - Rair - d3/k3)*k2
    return d2

def RoofIns_thickness(Uvalue):
    d1, k1 = 0.1016, 1.95 # M14a 100mm heavyweight concrete
    k2 = 0.03 # I02 50mm insulation board
    Rair = 0.18 # F05 Ceiling air space resistance
    d3, k3 = 0.0191, 0.06 # F16 Acoustic tile
    d2 = (1/Uvalue - d1/k1 - Rair - d3/k3)*k2
    return d2
    
def FloorIns_thickness(Uvalue):
    d1, k1 = 0.0191, 0.06 # F16 Acoustic tile
    Rair = 0.18 # F05 Ceiling air space resistance
    k2 = 0.03 # I02 50mm insulation board
    d3, k3 = 0.1016, 1.95 # M14a 100mm heavyweight concrete
    d2 = (1/Uvalue - d1/k1 - Rair - d3/k3)*k2
    return d2    

def set_Ins_thickness(idf, Uwall, Uroof, Ufloor):
    Material = idf.idfobjects['MATERIAL']
    dWall = WallIns_thickness(Uwall)
    dRoof = RoofIns_thickness(Uroof)
    dFloor = FloorIns_thickness(Ufloor)
    for material in Material:
        if getattr(material, 'Name') == 'I03 75mm insulation board': # 외벽 단열재
            setattr(material, 'Thickness', dWall)
        elif getattr(material, 'Name') == 'dummy': # 지붕
            setattr(material, 'Thickness', dRoof)
        elif getattr(material, 'Name') == 'dummy_': # 최하층바닥
            setattr(material, 'Thickness', dFloor)
    return idf            
            
def set_glazing(idf, WindowU, SHGC = 0.581): # SHGC 0.72: 건축물의 에너지절약설계기준 서식 1 표5의 복층 로이유리
    target_obj = idf.idfobjects['WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM'][0]
    setattr(target_obj, 'UFactor', WindowU)
    setattr(target_obj, 'Solar_Heat_Gain_Coefficient', SHGC)
    return idf            

