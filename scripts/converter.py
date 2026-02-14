#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MODIS HDF to GeoTIFF converter with Sinusoidal projection support
"""

import os
import sys
import numpy as np
from datetime import datetime, timedelta

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from pyhdf.SD import SD, SDC
from osgeo import gdal, osr


def parse_modis_date(filename):
    """
    Parse date from MODIS filename and convert to YYYYMMDD format
    """
    try:
        # Split filename by dots
        parts = filename.split('.')
        if len(parts) < 2:
            return None
        
        # Get date part (e.g., A2015209)
        date_part = parts[1]
        if len(date_part) != 8 or not date_part[0] == 'A':
            return None
        
        # Extract year and day of year
        year = int(date_part[1:5])
        doy = int(date_part[5:8])
        
        # Convert to datetime
        date = datetime(year, 1, 1) + timedelta(days=doy-1)
        
        # Return YYYYMMDD format
        return date.strftime('%Y%m%d')
    except Exception as e:
        print(f"Error parsing date: {str(e)}")
        return None


def analyze_hdf_file(hdf_file):
    """
    Analyze HDF file information
    
    Args:
        hdf_file (str): Path to MODIS HDF file
        
    Returns:
        dict: File information including resolution, data info, and data fields
    """
    file_info = {
        'path': hdf_file,
        'basename': os.path.basename(hdf_file),
        'resolution': None,
        'data_info': {},
        'data_fields': [],
        'date': parse_modis_date(os.path.basename(hdf_file)),
        'product_type': os.path.basename(hdf_file).split('.')[0],
        'tile': None
    }
    
    try:
        # Open HDF file
        hdf_ds = SD(hdf_file, SDC.READ)
        
        # Get global attributes
        global_attrs = hdf_ds.attributes()
        
        # Get tile information from filename
        import re
        tile_match = re.search(r'h\d+v\d+', file_info['basename'])
        if tile_match:
            file_info['tile'] = tile_match.group(0)
        
        # Calculate resolution from StructMetadata.0
        struct_metadata = global_attrs.get('StructMetadata.0', '')
        upper_left_match = re.search(r'UpperLeftPointMtrs=\(([^,]+),([^)]+)\)', struct_metadata)
        lower_right_match = re.search(r'LowerRightMtrs=\(([^,]+),([^)]+)\)', struct_metadata)
        xdim_match = re.search(r'XDim=(\d+)', struct_metadata)
        
        if upper_left_match and lower_right_match and xdim_match:
            ul_x = float(upper_left_match.group(1))
            lr_x = float(lower_right_match.group(1))
            xdim = int(xdim_match.group(1))
            
            resolution_meters = abs((lr_x - ul_x) / xdim)
            file_info['resolution'] = f'{resolution_meters:.2f}m'
            file_info['resolution_meters'] = resolution_meters
        else:
            file_info['resolution'] = 'unknown'
        
        # Get data fields
        datasets = hdf_ds.datasets().keys()
        for dataset_name in datasets:
            try:
                dataset = hdf_ds.select(dataset_name)
                data = dataset.get()
                attrs = dataset.attributes()
                
                field_info = {
                    'name': dataset_name,
                    'shape': data.shape,
                    'dtype': str(data.dtype),
                    'size': data.size,
                    'min': np.min(data) if data.size > 0 else None,
                    'max': np.max(data) if data.size > 0 else None
                }
                
                file_info['data_fields'].append(field_info)
                dataset = None
            except Exception as e:
                print(f"Error analyzing dataset {dataset_name}: {e}")
                continue
        
        file_info['data_info']['total_datasets'] = len(datasets)
        file_info['data_info']['file_size'] = os.path.getsize(hdf_file) / (1024 * 1024)  # MB
        
        # Clean up
        hdf_ds.end()
        
    except Exception as e:
        print(f"Error analyzing HDF file: {e}")
        import traceback
        traceback.print_exc()
    
    return file_info


def compare_hdf_files(hdf_files):
    """
    Compare multiple HDF files
    
    Args:
        hdf_files (list): List of HDF file paths
        
    Returns:
        dict: Comparison results
    """
    if len(hdf_files) == 0:
        return {}
    
    # Analyze all files
    file_infos = []
    for hdf_file in hdf_files:
        print(f"Analyzing file: {os.path.basename(hdf_file)}")
        file_info = analyze_hdf_file(hdf_file)
        file_infos.append(file_info)
    
    # Compare resolutions
    resolutions = set(info['resolution'] for info in file_infos)
    
    # Compare product types
    product_types = set(info['product_type'] for info in file_infos)
    
    # Compare data fields
    data_field_sets = []
    for info in file_infos:
        fields = set(field['name'] for field in info['data_fields'])
        data_field_sets.append(fields)
    
    # Check if all data field sets are the same
    all_fields_same = all(fields == data_field_sets[0] for fields in data_field_sets)
    
    comparison = {
        'file_infos': file_infos,
        'resolutions': list(resolutions),
        'product_types': list(product_types),
        'all_fields_same': all_fields_same,
        'total_files': len(hdf_files)
    }
    
    return comparison


def get_user_selection(file_infos, all_same=True):
    """
    Get user selection of data fields to convert
    
    Args:
        file_infos (list): List of file information dictionaries
        all_same (bool): Whether all files have the same data fields
        
    Returns:
        dict: User selection
    """
    if all_same and len(file_infos) > 0:
        # All files have the same data fields, ask once
        print("\nFile Analysis Report:")
        print(f"Total files: {len(file_infos)}")
        print(f"Resolution: {file_infos[0]['resolution']}")
        print(f"Product type: {file_infos[0]['product_type']}")
        print(f"Data fields found: {len(file_infos[0]['data_fields'])}")
        print("\nAvailable data fields:")
        
        for i, field in enumerate(file_infos[0]['data_fields'], 1):
            print(f"{i}. {field['name']} (shape: {field['shape']}, type: {field['dtype']})")
        
        # Get user selection
        while True:
            user_input = input("\nEnter the numbers of data fields to convert (comma-separated, e.g., 1,3), or 'ndvi' for only NDVI: ")
            
            if user_input.lower() == 'ndvi':
                # Select only NDVI fields
                selected_fields = [field['name'] for field in file_infos[0]['data_fields'] if 'NDVI' in field['name']]
                if selected_fields:
                    print(f"Selected fields: {selected_fields}")
                    return {'all_same': True, 'selected_fields': selected_fields}
                else:
                    print("No NDVI fields found. Please select manually.")
                    continue
            
            try:
                indices = [int(idx.strip()) - 1 for idx in user_input.split(',')]
                selected_fields = [file_infos[0]['data_fields'][i]['name'] for i in indices if 0 <= i < len(file_infos[0]['data_fields'])]
                if selected_fields:
                    print(f"Selected fields: {selected_fields}")
                    return {'all_same': True, 'selected_fields': selected_fields}
                else:
                    print("Invalid selection. Please try again.")
            except:
                print("Invalid input. Please try again.")
    else:
        # Files have different data fields, ask for each file
        selections = {}
        for i, info in enumerate(file_infos):
            print(f"\nFile {i+1}: {info['basename']}")
            print(f"Resolution: {info['resolution']}")
            print(f"Product type: {info['product_type']}")
            print(f"Data fields found: {len(info['data_fields'])}")
            print("Available data fields:")
            
            for j, field in enumerate(info['data_fields'], 1):
                print(f"{j}. {field['name']} (shape: {field['shape']}, type: {field['dtype']})")
            
            # Get user selection
            while True:
                user_input = input(f"\nEnter the numbers of data fields to convert for this file (comma-separated, e.g., 1,3), or 'ndvi' for only NDVI: ")
                
                if user_input.lower() == 'ndvi':
                    # Select only NDVI fields
                    selected_fields = [field['name'] for field in info['data_fields'] if 'NDVI' in field['name']]
                    if selected_fields:
                        print(f"Selected fields: {selected_fields}")
                        selections[info['path']] = selected_fields
                        break
                    else:
                        print("No NDVI fields found. Please select manually.")
                        continue
                
                try:
                    indices = [int(idx.strip()) - 1 for idx in user_input.split(',')]
                    selected_fields = [info['data_fields'][j]['name'] for j in indices if 0 <= j < len(info['data_fields'])]
                    if selected_fields:
                        print(f"Selected fields: {selected_fields}")
                        selections[info['path']] = selected_fields
                        break
                    else:
                        print("Invalid selection. Please try again.")
                except:
                    print("Invalid input. Please try again.")
        
        return {'all_same': False, 'selections': selections}


def get_modis_projection_info(hdf_file):
    """
    Get projection information from MODIS HDF file
    
    Args:
        hdf_file (str): Path to MODIS HDF file
        
    Returns:
        dict: Projection information including geotransform and WKT
    """
    import re
    
    try:
        from pyhdf.SD import SD, SDC
        from pyhdf.HDF import HDF
        from pyhdf.VS import VS
        
        projection_info = {
            'geotransform': None,
            'projection_wkt': None,
            'resolution': None
        }
        
        # Open HDF file
        hdf_ds = SD(hdf_file, SDC.READ)
        
        # Get projection info from global attributes
        global_attrs = hdf_ds.attributes()
        print("Global attributes:", list(global_attrs.keys()))
        
        # Parse StructMetadata.0 to extract projection info
        struct_metadata = global_attrs.get('StructMetadata.0', '')
        
        # Extract coordinates and dimensions from metadata
        upper_left_match = re.search(r'UpperLeftPointMtrs=\(([^,]+),([^)]+)\)', struct_metadata)
        lower_right_match = re.search(r'LowerRightMtrs=\(([^,]+),([^)]+)\)', struct_metadata)
        xdim_match = re.search(r'XDim=(\d+)', struct_metadata)
        ydim_match = re.search(r'YDim=(\d+)', struct_metadata)
        
        if upper_left_match and lower_right_match and xdim_match and ydim_match:
            ul_x = float(upper_left_match.group(1))
            ul_y = float(upper_left_match.group(2))
            lr_x = float(lower_right_match.group(1))
            lr_y = float(lower_right_match.group(2))
            xdim = int(xdim_match.group(1))
            ydim = int(ydim_match.group(1))
            
            # Calculate resolution from actual geographic bounds
            resolution_x = (lr_x - ul_x) / xdim
            resolution_y = (lr_y - ul_y) / ydim
            resolution = abs(resolution_x)
            
            print(f"Extracted from StructMetadata.0:")
            print(f"  UpperLeft: ({ul_x}, {ul_y})")
            print(f"  LowerRight: ({lr_x}, {lr_y})")
            print(f"  Dimensions: {xdim} x {ydim}")
            print(f"  Resolution: {resolution} meters")
            
            projection_info['resolution'] = resolution
            
            # Create geotransform directly from metadata
            geotransform = (ul_x, resolution, 0.0, ul_y, 0.0, -resolution)
            projection_info['geotransform'] = geotransform
            print(f"Calculated geotransform: {geotransform}")
        else:
            # StructMetadata.0 is required for correct projection
            print("Error: Could not extract projection info from StructMetadata.0")
            print("  Missing required metadata for georeferencing")
            hdf_ds.end()
            return None
        
        # Set standard Sinusoidal projection WKT
        srs = osr.SpatialReference()
        srs.ImportFromWkt('PROJCS["unnamed",GEOGCS["Unknown datum based upon the custom spheroid",DATUM["Not specified (based on custom spheroid)",SPHEROID["Custom spheroid",6371007.181,0]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]]],PROJECTION["Sinusoidal"],PARAMETER["longitude_of_center",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]')
        projection_info['projection_wkt'] = srs.ExportToWkt()
        
        hdf_ds.end()
        return projection_info
        
    except Exception as e:
        print(f"Error reading projection info: {e}")
        import traceback
        traceback.print_exc()
        
        return None


def hdf_to_geotiff_sinusoidal(hdf_file, output_dir=None, datasets=None):
    """
    Convert MODIS HDF file to GeoTIFF format with Sinusoidal projection
    
    Args:
        hdf_file (str): Path to MODIS HDF file
        output_dir (str, optional): Output directory for GeoTIFF files
        datasets (list, optional): List of datasets to process. If None, process all NDVI-related datasets
        
    Returns:
        list: List of created GeoTIFF files
    """
    if not os.path.exists(hdf_file):
        print(f"Error: HDF file not found: {hdf_file}")
        return []
    
    # Set output directory
    if output_dir is None:
        output_dir = os.path.dirname(hdf_file)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get HDF file basename
    hdf_basename = os.path.basename(hdf_file)
    output_files = []
    
    # Parse date from filename
    date_str = parse_modis_date(hdf_basename)
    if date_str:
        print(f"Parsed date: {date_str}")
    else:
        print("Warning: Could not parse date from filename")
    
    try:
        # Get projection information from HDF file
        print(f"Reading projection info from {hdf_basename}")
        projection_info = get_modis_projection_info(hdf_file)
        
        # Open HDF file with pyhdf
        print(f"Using pyhdf to read {hdf_basename}")
        hdf_ds = SD(hdf_file, SDC.READ)
        
        # Get list of datasets
        all_datasets = hdf_ds.datasets().keys()
        print(f"Found {len(all_datasets)} datasets in {hdf_basename}")
        
        # Determine which datasets to process
        if datasets is None:
            # Default: process only NDVI datasets
            process_datasets = [ds for ds in all_datasets if 'NDVI' in ds]
        else:
            # Process user-selected datasets
            process_datasets = [ds for ds in all_datasets if ds in datasets]
        
        print(f"Processing {len(process_datasets)} datasets: {process_datasets}")
        
        # Process selected datasets
        dataset_iter = process_datasets
        if tqdm is not None:
            dataset_iter = tqdm(process_datasets, desc="Converting datasets", unit="dataset")
        
        for dataset_name in dataset_iter:
            if tqdm is None:
                print(f"Processing dataset: {dataset_name}")
            
            # Create output filename with parsed date and dataset name
            if date_str:
                # Extract product type from filename (MOD13Q1, MOD13A1, etc.)
                product_type = hdf_basename.split('.')[0]
                # Create safe filename from dataset name
                safe_dataset_name = dataset_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                output_filename = f"{product_type}_{date_str}_{safe_dataset_name}.tif"
            else:
                safe_dataset_name = dataset_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                output_filename = f"{hdf_basename.split('.')[0]}_{hdf_basename.split('.')[1]}_{safe_dataset_name}.tif"
            output_path = os.path.join(output_dir, output_filename)
            
            # Force overwrite existing file
            if os.path.exists(output_path):
                print(f"Overwriting existing file: {output_path}")
                os.remove(output_path)
            
            try:
                # Read dataset
                dataset = hdf_ds.select(dataset_name)
                data = dataset.get()
                
                # Get attributes
                attrs = dataset.attributes()
                
                # Print dataset info
                print(f"Dataset shape: {data.shape}")
                print(f"Dataset type: {data.dtype}")
                
                # Create GeoTIFF using GDAL
                driver = gdal.GetDriverByName('GTiff')
                if not driver:
                    print("Error: GTiff driver not available")
                    continue
                
                # Get image size
                if len(data.shape) == 2:
                    y_size, x_size = data.shape
                    num_bands = 1
                else:
                    print(f"Error: Unexpected data shape: {data.shape}")
                    continue
                
                # Create output dataset
                out_ds = driver.Create(output_path, x_size, y_size, num_bands, gdal.GDT_Float32)
                if not out_ds:
                    print(f"Error: Cannot create output file: {output_path}")
                    continue
                
                # Set geotransform and projection from HDF file
                if projection_info and projection_info['geotransform']:
                    geotransform = projection_info['geotransform']
                    print(f"Using extracted geotransform: {geotransform}")
                else:
                    print("Error: Could not extract geotransform from HDF file, skipping dataset")
                    continue
                
                out_ds.SetGeoTransform(geotransform)
                
                # Set projection
                if projection_info['projection_wkt']:
                    print("Using extracted projection WKT")
                    out_ds.SetProjection(projection_info['projection_wkt'])
                else:
                    # Set Sinusoidal projection as fallback
                    srs = osr.SpatialReference()
                    srs.ImportFromWkt('PROJCS["unnamed",GEOGCS["Unknown datum based upon the custom spheroid",DATUM["Not specified (based on custom spheroid)",SPHEROID["Custom spheroid",6371007.181,0]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]]],PROJECTION["Sinusoidal"],PARAMETER["longitude_of_center",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]')
                    out_ds.SetProjection(srs.ExportToWkt())
                    print("Using default Sinusoidal projection")
                
                # Write data
                out_band = out_ds.GetRasterBand(1)
                out_band.WriteArray(data)
                
                # Set no data value based on dataset type
                if 'NDVI' in dataset_name or 'EVI' in dataset_name:
                    out_band.SetNoDataValue(-3000)  # MODIS vegetation indices no data value
                else:
                    # For other datasets, try to get no data value from attributes
                    no_data_value = None
                    for key, value in attrs.items():
                        if 'no data' in key.lower() or 'nodata' in key.lower():
                            no_data_value = value
                            break
                    if no_data_value is not None:
                        out_band.SetNoDataValue(no_data_value)
                
                # Copy attributes as metadata
                metadata = {}
                for key, value in attrs.items():
                    metadata[key] = str(value)
                out_band.SetMetadata(metadata)
                
                # Clean up
                out_ds = None
                dataset = None
                
                print(f"Successfully created GeoTIFF: {output_path}")
                output_files.append(output_path)
                
            except Exception as e:
                print(f"Error processing dataset {dataset_name}: {str(e)}")
                continue
        
        # Clean up
        hdf_ds.end()
        
    except Exception as e:
        print(f"Error processing HDF file: {str(e)}")
        return []
    
    return output_files





def batch_convert_hdf_files(hdf_files, output_dir=None):
    """
    Batch convert multiple MODIS HDF files to GeoTIFF format
    
    Args:
        hdf_files (list): List of HDF file paths
        output_dir (str, optional): Output directory for GeoTIFF files
        
    Returns:
        dict: Conversion results
    """
    results = {
        'total': len(hdf_files),
        'success': 0,
        'failed': 0,
        'created_files': []
    }
    
    if not hdf_files:
        print("Error: No HDF files provided")
        return results
    
    # Step 1: Analyze and compare files
    print("\n=== Step 1: File Analysis ===")
    comparison = compare_hdf_files(hdf_files)
    
    if not comparison:
        print("Error: Failed to analyze files")
        return results
    
    # Step 2: Get user selection
    print("\n=== Step 2: User Selection ===")
    user_selection = get_user_selection(comparison['file_infos'], comparison['all_fields_same'])
    
    # Step 3: Perform conversion based on user selection
    print("\n=== Step 3: Conversion ===")
    if user_selection['all_same']:
        # All files have the same data fields, convert all with same selection
        selected_fields = user_selection['selected_fields']
        for hdf_file in hdf_files:
            print(f"\nProcessing file: {os.path.basename(hdf_file)}")
            output_files = hdf_to_geotiff_sinusoidal(hdf_file, output_dir, selected_fields)
            
            if output_files:
                results['success'] += 1
                results['created_files'].extend(output_files)
                print(f"Created {len(output_files)} GeoTIFF files")
            else:
                results['failed'] += 1
                print("Conversion failed")
    else:
        # Files have different data fields, convert each with its own selection
        selections = user_selection['selections']
        for hdf_file in hdf_files:
            if hdf_file in selections:
                selected_fields = selections[hdf_file]
                print(f"\nProcessing file: {os.path.basename(hdf_file)}")
                output_files = hdf_to_geotiff_sinusoidal(hdf_file, output_dir, selected_fields)
                
                if output_files:
                    results['success'] += 1
                    results['created_files'].extend(output_files)
                    print(f"Created {len(output_files)} GeoTIFF files")
                else:
                    results['failed'] += 1
                    print("Conversion failed")
            else:
                print(f"Skipping file: {os.path.basename(hdf_file)} (no selection)")
                results['failed'] += 1
    
    return results


def convert_with_user_selection(hdf_file, output_dir=None, interactive=True):
    """
    Convert HDF file to GeoTIFF with user selection of data fields
    
    Args:
        hdf_file (str): Path to MODIS HDF file
        output_dir (str, optional): Output directory for GeoTIFF files
        interactive (bool): Whether to use interactive mode (default: True)
        
    Returns:
        dict: Conversion result
    """
    if not os.path.exists(hdf_file):
        return {
            'status': 'error',
            'message': f"HDF file not found: {hdf_file}"
        }
    
    # Step 1: Analyze the file
    print("\n=== Step 1: File Analysis ===")
    file_info = analyze_hdf_file(hdf_file)
    
    if not file_info:
        return {
            'status': 'error',
            'message': "Failed to analyze HDF file"
        }
    
    # Step 2: Display file information
    print(f"\nFile Information:")
    print(f"File: {file_info['basename']}")
    print(f"Product type: {file_info['product_type']}")
    print(f"Resolution: {file_info['resolution']}")
    print(f"Date: {file_info['date']}")
    print(f"Tile: {file_info['tile']}")
    print(f"Data fields found: {len(file_info['data_fields'])}")
    
    print("\nAvailable data fields:")
    for i, field in enumerate(file_info['data_fields'], 1):
        print(f"{i}. {field['name']} (shape: {field['shape']}, type: {field['dtype']})")
    
    # Step 3: Get user selection
    print("\n=== Step 2: User Selection ===")
    selected_fields = []
    
    if interactive:
        # Interactive mode: get user input
        while True:
            user_input = input("Enter the numbers of data fields to convert (comma-separated, e.g., 1,3), or 'all' for all fields: ")
            
            if user_input.lower() == 'all':
                # Select all fields
                selected_fields = [field['name'] for field in file_info['data_fields']]
                print(f"Selected all fields: {selected_fields}")
                break
            
            try:
                indices = [int(idx.strip()) - 1 for idx in user_input.split(',')]
                selected_fields = [file_info['data_fields'][i]['name'] for i in indices if 0 <= i < len(file_info['data_fields'])]
                if selected_fields:
                    print(f"Selected fields: {selected_fields}")
                    break
                else:
                    print("Invalid selection. Please try again.")
            except:
                print("Invalid input. Please try again.")
    else:
        # Non-interactive mode: select first field by default
        if file_info['data_fields']:
            selected_fields = [file_info['data_fields'][0]['name']]
            print(f"Non-interactive mode: selected first field: {selected_fields}")
        else:
            return {
                'status': 'error',
                'message': "No data fields found in HDF file"
            }
    
    # Step 4: Perform conversion
    print("\n=== Step 3: Conversion ===")
    output_files = hdf_to_geotiff_sinusoidal(hdf_file, output_dir, selected_fields)
    
    if output_files:
        return {
            'status': 'success',
            'message': f"Successfully converted {len(output_files)} data fields",
            'output_files': output_files
        }
    else:
        return {
            'status': 'error',
            'message': "Conversion failed"
        }
