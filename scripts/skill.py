#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HDF to GeoTIFF converter skill
"""

import os
import sys
from converter import analyze_hdf_file, hdf_to_geotiff_sinusoidal


def analyze(input_file):
    """
    Analyze HDF file and return available datasets
    
    Args:
        input_file (str): Path to HDF file
    
    Returns:
        dict: Analysis result with file info and available datasets
    """
    try:
        if not os.path.exists(input_file):
            return {
                "status": "error",
                "message": f"File not found: {input_file}"
            }
        
        file_info = analyze_hdf_file(input_file)
        
        return {
            "status": "success",
            "file_info": file_info,
            "message": f"Found {len(file_info.get('data_fields', []))} datasets"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Analysis failed: {str(e)}"
        }


def convert(input_file, output_dir, datasets=None):
    """
    Convert HDF file to GeoTIFF
    
    Args:
        input_file (str): Path to HDF file
        output_dir (str): Output directory
        datasets (list, optional): List of dataset names to convert
    
    Returns:
        dict: Conversion result
    """
    try:
        if not os.path.exists(input_file):
            return {
                "status": "error",
                "message": f"File not found: {input_file}"
            }
        
        os.makedirs(output_dir, exist_ok=True)
        
        output_files = hdf_to_geotiff_sinusoidal(input_file, output_dir, datasets)
        
        if output_files:
            return {
                "status": "success",
                "message": f"Successfully converted {len(output_files)} dataset(s)",
                "output_files": output_files
            }
        else:
            return {
                "status": "error",
                "message": "No files were converted"
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Conversion failed: {str(e)}"
        }


def handle_hdf_to_geotiff_conversion(request):
    """
    Handle HDF to GeoTIFF conversion request
    
    Args:
        request (dict): Request dictionary containing conversion parameters
            - input_file: Input HDF file path
            - output_dir: Output directory for GeoTIFF files
            - datasets: (optional) List of dataset names to convert
            - analyze_only: (optional) If True, only analyze without converting
    
    Returns:
        dict: Conversion result
    """
    try:
        input_file = request.get('input_file')
        output_dir = request.get('output_dir')
        datasets = request.get('datasets')
        analyze_only = request.get('analyze_only', False)
        
        if not input_file:
            return {
                "status": "error",
                "message": "Missing required parameter: input_file"
            }
        
        if analyze_only:
            return analyze(input_file)
        
        if not output_dir:
            output_dir = os.path.dirname(input_file)
        
        return convert(input_file, output_dir, datasets)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Conversion failed: {str(e)}"
        }


def run_skill(input_data):
    """
    Skill main entry function
    
    Args:
        input_data (dict): Input data
    
    Returns:
        dict: Processing result
    """
    print("=====================================")
    print("     HDF to GeoTIFF Converter Skill")
    print("=====================================")
    
    # Handle different input formats
    if isinstance(input_data, dict):
        # Directly handle dictionary input
        print("Processing dictionary input...")
        result = handle_hdf_to_geotiff_conversion(input_data)
    elif isinstance(input_data, str):
        # Handle string input
        print("Processing string input...")
        # Try to parse parameters from string
        import re
        input_file_match = re.search(r'input_file\s*[:=]\s*("[^"]+"|\'[^\']+\'|[^,\n]+)', input_data)
        output_dir_match = re.search(r'output_dir\s*[:=]\s*("[^"]+"|\'[^\']+\'|[^,\n]+)', input_data)
        
        input_file = None
        output_dir = None
        
        if input_file_match:
            input_file = input_file_match.group(1).strip('"\'')
        else:
            # Try to extract file path from string
            import glob
            hdf_files = glob.glob(os.path.join(input_data, '*.hdf'))
            if hdf_files:
                input_file = hdf_files[0]
        
        if output_dir_match:
            output_dir = output_dir_match.group(1).strip('"\'')
        
        result = handle_hdf_to_geotiff_conversion({
            'input_file': input_file,
            'output_dir': output_dir
        })
    else:
        result = {
            "status": "error",
            "message": "Invalid input format, should be dictionary or string"
        }
    
    print(f"\nResult: {result['status']}")
    print(f"Message: {result['message']}")
    if 'output_files' in result and result['output_files']:
        print("\nCreated files:")
        for file in result['output_files']:
            print(f"- {os.path.basename(file)}")
    print("=====================================")
    
    return result


if __name__ == "__main__":
    """
    Main function - accepts command line arguments
    
    Usage:
        python skill.py analyze <input_file>
        python skill.py convert <input_file> <output_dir> <datasets>
    
    Example:
        python skill.py analyze D:/ndvi/hdf/MOD13Q1.A2023161.h29v09.061.hdf
        python skill.py convert D:/ndvi/hdf/MOD13Q1.A2023161.h29v09.061.hdf D:/ndvi/tif "NDVI,EVI"
    """
    import json
    import sys
    import numpy as np
    from osgeo import gdal
    
    def convert_to_serializable(obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(v) for v in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python skill.py analyze <input_file>")
        print("  python skill.py convert <input_file> <output_dir> [datasets]")
        sys.exit(1)
    
    command = sys.argv[1]
    input_file = sys.argv[2]
    
    if command == "analyze":
        analysis = analyze(input_file)
        
        if analysis['status'] == 'success':
            file_info = analysis['file_info']
            print("=== File Analysis Report ===")
            print(f"Product: {file_info['product_type']}")
            print(f"Date: {file_info['date']}")
            print(f"Tile: {file_info['tile']}")
            print(f"Resolution: {file_info['resolution']}")
            print()
            print("Available Datasets:")
            for i, field in enumerate(file_info['data_fields'], 1):
                print(f"  {i}. {field['name']} - Shape: {field['shape']}")
        else:
            print(f"Error: {analysis['message']}")
    
    elif command == "convert":
        if len(sys.argv) < 4:
            print("Error: output_dir required for convert command")
            sys.exit(1)
        
        output_dir = sys.argv[3]
        datasets = sys.argv[4].split(",") if len(sys.argv) > 4 else None
        
        result = run_skill({
            'input_file': input_file,
            'output_dir': output_dir,
            'datasets': datasets
        })
        result = convert_to_serializable(result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: analyze, convert")
        sys.exit(1)
