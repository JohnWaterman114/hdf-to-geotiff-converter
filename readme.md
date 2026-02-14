# MODIS HDF to GeoTIFF Converter

An Agent skill for converting MODIS HDF files to GeoTIFF format with correct Sinusoidal projection, guiding users to select which datasets to convert.

## Overview

This skill converts MODIS HDF-EOS files to GeoTIFF format while preserving the original Sinusoidal projection. It automatically detects the product type, resolution, and geographic bounds from the HDF file metadata, ensuring accurate georeferencing.

## Processing Workflow 

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

## Data Source & Calculation

| Data | Source | Method |
|------|--------|--------|
| UpperLeft | StructMetadata.0 | Extracted directly |
| LowerRight | StructMetadata.0 | Extracted directly |
| XDim, YDim | StructMetadata.0 | Extracted directly |
| **Resolution** | Calculated | `(LR_X - UL_X) / XDim` |
| **Geotransform** | Calculated | `(UL_X, resolution, 0, UL_Y, 0, -resolution)` |
| Projection WKT | Fixed | Sinusoidal (MODIS standard) |

**All coordinate and resolution values are dynamically calculated from metadata, no hardcoded values!**

## Features

- **Automatic metadata extraction**: Reads projection information directly from HDF file metadata

## Supported Products

MODIS HDF-EOS files with similar structure

## Installation

### Prerequisites

- Python 3.8+
- Conda (recommended)
- Required packages:
  - `pyhdf` - For reading HDF4 files
  - `gdal` - For creating GeoTIFF files
  - `numpy` - For array operations
  - `tqdm` - For progress bar display (optional)

### Setup

This skill requires a Python environment with the following packages:
- `pyhdf` - For reading HDF4 files
- `gdal` - For creating GeoTIFF files
- `numpy` - For array operations
- `tqdm` - For progress bar display (optional)

Install in your existing environment:
```bash
# Using conda
conda install -c conda-forge gdal numpy
pip install pyhdf tqdm

# Or using pip only
pip install gdal numpy pyhdf tqdm
```

## Usage
When you call the skill, it will:
1. Display file information (product type, resolution, date, tile)
2. List all available datasets
3. Wait for you to select which datasets to convert

```python
import sys
sys.path.insert(0, 'path/to/hdf-to-geotiff-converter/scripts')

from skill import run_skill

result = run_skill({
    'input_file': 'path/to/MOD13Q1.A2023161.h29v09.061.hdf',
    'output_dir': 'output/directory'
})

print(result)
```

### Command Line

```bash
# Run conversion in your Python environment
python -c "
import sys
sys.path.insert(0, 'path/to/hdf-to-geotiff-converter/scripts')
from skill import run_skill

result = run_skill({
    'input_file': 'D:/data/MOD13Q1.A2023161.h29v09.061.hdf',
    'output_dir': 'D:/data/output'
})
"
```

## API Reference

### analyze_hdf_file(hdf_file)

Analyzes an HDF file and returns information about its contents.

**Parameters:**
- `hdf_file` (str): Path to the HDF file

**Returns:**
- `dict`: File information containing:
  - `product_type`: MODIS product type (e.g., 'MOD13Q1')
  - `resolution`: Spatial resolution (e.g., '250m')
  - `date`: Acquisition date in YYYYMMDD format
  - `tile`: Tile identifier (e.g., 'h29v09')
  - `data_fields`: List of available datasets

### hdf_to_geotiff_sinusoidal(hdf_file, output_dir=None, datasets=None)

Converts HDF file to GeoTIFF with Sinusoidal projection.

**Parameters:**
- `hdf_file` (str): Path to the HDF file
- `output_dir` (str, optional): Output directory for GeoTIFF files
- `datasets` (list, optional): List of dataset names to convert

**Returns:**
- `list`: List of created GeoTIFF file paths

### convert_with_user_selection(hdf_file, output_dir=None, interactive=True)

Converts HDF file with user-interactive dataset selection.

**Parameters:**
- `hdf_file` (str): Path to the HDF file
- `output_dir` (str, optional): Output directory for GeoTIFF files
- `interactive` (bool): Enable interactive mode (default: True)

**Returns:**
- `dict`: Conversion result with status and output files

### run_skill(input_data)

Main entry point for skill execution.

**Parameters:**
- `input_data` (dict or str): Input parameters
  - `input_file`: Path to HDF file
  - `output_dir`: Output directory (optional)

**Returns:**
- `dict`: Conversion result


## Acknowledgments

This project is for research and educational purposes.


