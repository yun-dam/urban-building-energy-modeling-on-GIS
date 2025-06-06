# 🏢 Auto-generating Urban Building Energy Models in EnergyPlus

This Python tool automates the generation of EnergyPlus models from GIS-based building footprint shapefiles. It extracts building geometry, assigns archetype data (e.g., insulation levels, usage types), and generates `.idf` simulation files for each building. The tool also supports optional simulation runs using EnergyPlus.

## 🚀 Features

- Converts GIS shapefiles to EnergyPlus-ready IDF files
- Auto-assigns envelope U-values based on construction year and location
- Handles WGS84 to UTM coordinate transformation
- Generates detailed wall, window, roof, and floor elements
- Models surrounding buildings as shading objects
- Runs EnergyPlus simulations (optional)

## 📝 Initialization

To initialize the class:

```python
from genEnergyPlus import genEnergyPlus

gEP = genEnergyPlus(
    shpPath='sample_data/buildings.shp',
    epwPath='sample_data/weather.epw',
    savePath='output',
    idColumn='PNU',
    floorNumberColumn='GRND_FLR',
    useTypeColumn='USABILITY',
    builtDateColumn='USEAPR_DAY',
    wsg84=True
)
```

## ⚙️ Usage

To generate an `.idf` file and optionally run simulation:

```python
# Export processed data
df = gEP.processedDataExport()

# Generate EnergyPlus model and run simulation for a building ID
gEP.main(
    bldgID='1168010100100120000',  # Replace with your actual building ID
    wwr=0.4,                       # Wall-to-window ratio
    Z_height=3.0,                  # Floor height (meters)
    boundaryBuffer=30,            # Range to include surrounding buildings
    run_simluation=True           # Run EnergyPlus simulation
)
```

## 📍 Notes
This tool currently supports only Polygon geometries. MultiPolygons are filtered out.

Insulation and usage metadata are based on Korean standards but can be adapted globally.

Weather data is extracted from the specified .epw file and appended to each record.

🧪 This tool is currently a demo implementation based on Korean Open GIS data.

🌐 Generalization for global GIS data and archetypes is in progress.


