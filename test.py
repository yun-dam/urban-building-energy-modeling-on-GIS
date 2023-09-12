# -*- coding: utf-8 -*-
"""
Created on Mon Aug 21 13:08:27 2023

@author: YUNDAM
"""


from genEnergyPlus import genEnergyPlus

# %%

shpF = r'.\sampleGIS\Seoul_Gangnam_Yeoksam_One_Block.shp'
epwF = r'.\EPW\KOR_SO_Seoul.WS.471080_TMYx.2007-2021.epw'
idfsaveF = r'.'

epClass = genEnergyPlus(shpF,epwF, savePath = idfsaveF, idColumn='SGG_OID')
data = epClass.processedDataExport()

ubemBldg = data['SGG_OID']

# %% modeling all buildings in data

for b in ubemBldg:
    
    try:
        
        bldgID = b 
        epClass.main(bldgID, run_simluation=False, boundaryBuffer = 200)

    except:
        
        continue
    
