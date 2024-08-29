"""
This file is to batch process the TDX Hydro files on LimnoTech 
servers and convert them to geoparquet files containing nested
set index information.
"""

from pathlib import Path

import pyogrio
import geopandas as gpd
from collections import Counter
import re

import global_hydrography as gh
from global_hydrography.delineation.mnsi import MNSI_FIELDS
from global_hydrography.preprocess import TDXPreprocessor
from global_hydrography.process import compute_dissolve_groups, DISSOLVE_ROOT_ID, ELEMENT_COUNT


INPUT_DIR = Path("J:\MMW\TDX_HydroRaw")
OUTPUT_DIR = Path("J:\MMW\TDX_MNSI_Output")

#function pulled from example 4.
def process_tdx_streams_basins(
    input_dir: Path,
    output_dir: Path,
    tdx_hydro_region: int, 
    preprocessor:TDXPreprocessor
) -> list[Path]:
    """Process a pair of TDXHydro streamnet and streamreach_basins files for 
    a given TDX Hydro Region, creating a set of GeoParquet files ready for use 
    by Model My Watershed. This processing includes:
    - Reads the 'TDX_streamnet*.gpkg' file provided by NGA, converts LINKNO fields to 
    globally unique values, calculates and adds three new Modified Nested Set Index (MNSI) 
    fields, drops useless fields, and sets LINKNO as the index.
    - Reads the 'TDX_streareach_basins*.gpkg' file provided by NGA, renames 'streamID' 
    to LINKNO, converts LINKNO to globally unique values, and sets LINKNO as the index.
    - Moves MNSI fields from streament to basins datasets, saving a dataset of streams
    that don't have a matching basin geometry.
    - Saves three output datasets to GeoParquet files in the output directory.

    Parameters:
        input_dir: Directory with raw TDX Hydro GeoPackage ('.gpkg') files.
        output_dir: Directory for saving processed GeoParquet ('.parquet') files.
        tdx_hydro_region: The 10-digit TDX Hydro Region
        preprocessor: An instance of the TDXPreprocessor class.

    Returns: a list of output file paths
        TDX_streamnet_*.parquet  
        TDX_streamreach_basins_mnsi_*.parquet  
        TDX_streams_no_basin_*.parquet  
    """
    # Get file paths
    print (f"Processing TDXHydroRegion = {tdx_hydro_region}")
    streamnet_file, basins_file = gh.process.select_tdx_files(
        input_dir, tdx_hydro_region,'.gpkg')
    

    ## Process streamnet file ##
    # get streamnet file metadata
    streamnet_info = pyogrio.read_info(streamnet_file, layer=0)
    print(f"  Reading: layer = {streamnet_info['layer_name']} " 
        f"last updated {streamnet_info['layer_metadata']['DBF_DATE_LAST_UPDATE']}"
    )
    
    # open streamnet file as GeoDataFrame
    streamnet_gdf = gpd.read_file(streamnet_file, engine='pyogrio', layer=0, use_arrow=True)

    # apply preprocessing to make linkno globally unique
    preprocessor.tdx_to_global_linkno(streamnet_gdf, tdx_hydro_region)

    # apply preprocessing to make drop columns with no value
    preprocessor.tdx_drop_useless_columns(streamnet_gdf)

    # compute the modified nested set index
    print('  Computing: modified nested set index')
    streamnet_gdf = gh.mnsi.modified_nest_set_index(streamnet_gdf)

    # Set 'LINKNO' as index, to facilitate selection
    streamnet_gdf.set_index('LINKNO', inplace=True)


    ## Process basins file ##
    # get basins file metadata
    basins_info = pyogrio.read_info(basins_file, layer=0)
    print(f"  Reading: layer = {basins_info['layer_name']}")

    # open basins file as GeoDataFrame
    basins_gdf = gpd.read_file(basins_file, engine='pyogrio', layer=0, use_arrow=True)

    # Rename 'streamID' to 'LINKNO' to facilitate interoperability 
    # with streamnet files
    basins_gdf.rename(columns={'streamID':'LINKNO'}, inplace=True)
    
    # apply preprocessing to make linkno globally unique
    preprocessor.tdx_to_global_linkno(basins_gdf, tdx_hydro_region)

    # Set 'LINKNO' as index, to facilitate selection
    basins_gdf.set_index('LINKNO', inplace=True)

    #compute predissolve group
    basins_mnsi_gdf = compute_dissolve_groups(basins_mnsi_gdf, max_elements=200, min_elements=125,)

    
    ## Move MNSI fields from streamnet to basins ##
    fields_to_copy = [*MNSI_FIELDS, DISSOLVE_ROOT_ID, ELEMENT_COUNT]
    print(f"  Moving MNSI files from streamnet to basins datasets.")
    basins_mnsi_gdf, streams_no_basin_gdf = gh.process.create_basins_mnsi(
        basins_gdf,
        streamnet_gdf,
        fields_to_copy=fields_to_copy
    )
    # Drop MNSI fields from streamnet_gdf
    #we now wish to retain this information
    #streamnet_gdf.drop(columns=gh.mnsi.MNSI_FIELDS, inplace=True)

    ## Write GeoParquet files ##
    gdf_dict = {
        'streamnet': streamnet_gdf,
        'streamreach_basins_mnsi': basins_mnsi_gdf,
        'streams_no_basin': streams_no_basin_gdf,
    }
    parquet_paths = []
    for dataset, gdf in gdf_dict.items():
        path = output_dir / f"TDX_{dataset}_{tdx_hydro_region}_01.parquet"
        parquet_paths.append(path)
        gdf.to_parquet(path, compression='zstd')
        print(f'  File saved: {path.name}')

    return parquet_paths

#help function to get all TDX regions from input file
def get_tdx_regions(input_dir:Path) -> list[int]:
    tdx_regions = Counter()

    for file_path in input_dir.iterdir():
        file_name = file_path.name
        match = re.search("\d{10}",file_name)
        if match:
            tdx_region = int(match.group(0))
            tdx_regions[tdx_region] = True

    return tdx_regions.keys()

def main() -> None:
    #regions = get_tdx_regions(INPUT_DIR)
    regions = [4020024190]
    preprocessor = TDXPreprocessor()
    for region in regions:
        print(f'start {region}')
        process_tdx_streams_basins(
            input_dir=INPUT_DIR,
            output_dir=OUTPUT_DIR,
            tdx_hydro_region=region,
            preprocessor=preprocessor,
        )
        print(f'finish {region}')

if __name__ == '__main__':
    main()