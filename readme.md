# MODIS HDF to GeoTIFF Converter

A Trae AI skill for converting MODIS HDF files to GeoTIFF format with correct Sinusoidal projection.

## Overview

This skill converts MODIS HDF-EOS files to GeoTIFF format while preserving the original Sinusoidal projection. It automatically detects the product type, resolution, and geographic bounds from the HDF file metadata, ensuring accurate georeferencing.

## Features

- **Automatic metadata extraction**: Reads projection information directly from HDF file metadata
- **Dynamic resolution calculation**: Computes pixel resolution from actual geographic bounds
- **Multiple dataset support**: Can convert any dataset within the HDF file (NDVI, EVI, quality bands, etc.)
- **Batch conversion**: Supports converting multiple files at once
- **Sinusoidal projection**: Preserves the original MODIS Sinusoidal coordinate system

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

```bash
# Create and activate conda environment
conda create -n geo_env python=3.9
conda activate geo_env

# Install required packages
conda install -c conda-forge gdal numpy
pip install pyhdf tqdm
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
# Activate environment
conda activate geo_env

# Run conversion
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

## Output Files

The converted GeoTIFF files are named using the pattern:
```
{PRODUCT}_{DATE}_{RESOLUTION}_{DATASET}.tif
```

Example: `MOD13Q1_20230809_250m_16_days_NDVI.tif`

## Projection Information

The converted GeoTIFF files use the MODIS Sinusoidal projection:

- **Projection**: Sinusoidal (GCTP_SNSOID)
- **Datum**: Custom sphere (6371007.181m)
- **Units**: Meters
- **Pixel resolution**: Dynamically calculated from file metadata

### Geotransform Parameters

The geotransform is calculated dynamically from the HDF file's StructMetadata:

```
(x_min, pixel_width, 0, y_max, 0, -pixel_height)
```

Example for tile h29v09 (250m):
```
(12231455.716333, 231.65635826395825, 0.0, 0.0, 0.0, -231.65635826395825)
```

## Troubleshooting

### "Error opening file" / "SD (7): Error opening file"

The HDF file may be corrupted or incomplete. Try re-downloading the file.

### "Another program is using this file"

Close any programs that may have the output file open (QGIS, etc.) or choose a different output directory.

### Wrong projection in output

Ensure you're using the latest version of the converter. The projection is now dynamically calculated from file metadata.

### Date parsing fails

Verify the filename follows MODIS naming convention: `PRODUCT.AYYYYDDD.TILE.VERSION.hdf`

## License

This project is for research and educational purposes.

## Acknowledgments

- MODIS data provided by NASA LP DAAC
- Uses pyhdf library for HDF4 file reading
- Uses GDAL for GeoTIFF creation
