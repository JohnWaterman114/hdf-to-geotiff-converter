---
name: "hdf-to-geotiff-converter"
description: "Agent skill that converts MODIS HDF files to GeoTIFF with correct Sinusoidal projection, guiding users to select which datasets to convert. Invoke when user needs to convert MODIS HDF files to GeoTIFF format."
---

# MODIS HDF to GeoTIFF Converter

This skill handles the conversion of MODIS HDF files to GeoTIFF format while preserving the correct Sinusoidal projection.

## Directory Structure

```
hdf-to-geotiff-converter/
├── SKILL.md            # Skill documentation
└── scripts/            # Python scripts
    ├── converter.py     # Core conversion script
    └── skill.py         # Skill main entry point
```

## When to Use

- User has MODIS HDF files that need to be converted to GeoTIFF format
- User needs to batch convert multiple MODIS HDF files



## Workflow
# Processing Workflow 

example:user input a file   MOD13Q1.A2024161.h29v09.061.2024181211247.hdf

```
┌────────────────────────────────────────────────────────────────┐
│  Input: MOD13Q1.A2024161.h29v09.061.2024181211247.hdf          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 1: Parse Filename                                        │
│     Product type: MOD13Q1                                      │
│     Date: A2024161 → 20240609                                  │
│     Tile: h29v09                                               │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 2: Open HDF File (pyhdf)                                 │
│     Read StructMetadata.0                                      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 3: Extract Coordinate Info from   StructMetadata.0       │
│     UpperLeft: (12231455.716, 0.0)                             │
│     LowerRight: (13343406.236, -1111950.52)                    │
│     Dimensions: 4800 × 4800                                    │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 4: Calculate Projection Parameters                       │
│     resolution = (13343406 - 12231455) / 4800 = 231.656m       │
│     geotransform = (12231455.716, 231.656, 0, 0, 0, -231.656)  │
│     projection = Sinusoidal WKT                                │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 5: Report to User                                        │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ File Analysis Report:                                │   │
│     │   Product: MOD13Q1 (MODIS Vegetation Indices)        │   │
│     │   Date: 2024-06-09 (Day 161)                         │   │
│     │   Tile: h29v09                                       │   │
│     │   Resolution: 231.656m (~250m)                       │   │
│     │   Dimensions: 4800 × 4800 pixels                     │   │
│     │   Coverage: ~1112km × ~1112km                        │   │
│     │                                                      │   │
│     │ Available Datasets:                                  │   │
│     │   1. 250m 16 days NDVI (Vegetation Index)            │   │
│     │   2. 250m 16 days EVI (Enhanced Vegetation Index)    │   │
│     │   3. 250m 16 days VI Quality (Quality Assessment)    │   │
│     │   ...                                                │   │
│     └──────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 6: User Selection                                        │
│     User selects: NDVI, pixel reliability                      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 7: Convert Each Dataset                                  │
│     - Read data array                                          │
│     - Create GeoTIFF                                           │
│     - Set geotransform + projection                            │
│     - Write data                                               │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Output:                                                       │
│  - MOD13Q1_20240609_250m_16_days_NDVI.tif                      │
│  - MOD13Q1_20240609_250m_16_days_pixel_reliability.tif         │
└────────────────────────────────────────────────────────────────┘
```

### Step 1: Analyze HDF File

When user provides an HDF file path, analyze it to see available datasets:

example:

user input: "D:\ndvi\hdf\MYD13Q1.A2017201.h29v09.061.2021282010832.hdf"

```bash
python skill.py analyze "path/to/MOD13Q1.A2023161.h29v09.061.hdf"
```

Output:
```
=== File Analysis Report ===
Product: MOD13Q1
Date: 2023161
Tile: h29v09
Resolution: 231.66m

Available Datasets:
  1. 250m 16 days NDVI - Shape: (4800, 4800)
  2. 250m 16 days EVI - Shape: (4800, 4800)
  ...
```

### Step 2: Ask User to Select Datasets

Show the analysis report to user and ask which datasets to convert:

```
Please select datasets to convert (enter numbers, e.g., 1,12):
```

Wait for user's selection (e.g., user enters "1" for NDVI).

### Step 3: Convert Selected Datasets

After user confirms selection, execute conversion:

```bash
# Convert single dataset
python skill.py convert "path/to/file.hdf" "output/dir" "250m 16 days NDVI"

# Convert multiple datasets
python skill.py convert "path/to/file.hdf" "output/dir" "250m 16 days NDVI,250m 16 days EVI"
```

### Step 4: Verify Output

Check that converted files have the correct projection:

```python
from osgeo import gdal

ds = gdal.Open("output_file.tif")
print(f"Extent: {ds.GetGeoTransform()}")
print(f"Projection: {ds.GetProjection()}")
```

**Expected results:**
- MOD13Q1: 4800x4800, Sinusoidal projection
- MOD13A1: 2400x2400, Sinusoidal projection

### Step 5: Load into QGIS

Load the converted GeoTIFF files into QGIS:

```python
from qgis.core import QgsProject

# Add raster layer
layer = iface.addRasterLayer("path/to/file.tif", "layer_name", "gdal")
```

Or use QGIS MCP tools:
```
mcp_qgis_add_raster_layer(path="D:/path/to/file.tif", name="layer_name")
```

## Alternative: Python API

You can also call the skill directly from Python:

```python
import sys
sys.path.insert(0, 'path/to/hdf-to-geotiff-converter/scripts')

from skill import analyze, convert

# Analyze
result = analyze('path/to/file.hdf')
print(result['file_info'])

# Convert
result = convert('path/to/file.hdf', 'output/dir', ['250m 16 days NDVI'])
```

## Important Notes

1. **Use pyhdf, not GDAL**: GDAL may fail to recognize HDF4 files without proper driver setup. pyhdf is more reliable for reading MODIS HDF files.

2. **Force overwrite**: When re-converting files, explicitly remove existing files to ensure the correct projection is applied.

3. **Process only NDVI dataset**: MODIS HDF files contain multiple datasets (NDVI, EVI, quality, etc.). For vegetation analysis, typically only NDVI is needed.

4. **Date format**: MODIS uses day-of-year (DOY) format (e.g., A2015209 = year 2015, day 209). Convert to YYYYMMDD for human-readable filenames.

5. **Projection consistency**: Always verify that converted files match the projection of reference files before loading into QGIS.

6. **Progress bar**: When converting multiple datasets, a progress bar will be displayed. Install `tqdm` for this feature (`pip install tqdm`). If not installed, the conversion will still work but without the progress bar.

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| GDAL cannot open HDF file | Use pyhdf library instead of GDAL for reading HDF files |
| Converted files have wrong projection | Manually set Sinusoidal projection with correct geotransform parameters |
| Files not overwriting | Explicitly remove existing files before conversion |
| Date parsing fails | Verify filename format matches MODIS naming convention (AYYYYDOY) |

## Scripts

- `scripts/converter.py` - Core conversion functions
- `scripts/skill.py` - Skill entry point (run_skill function)

