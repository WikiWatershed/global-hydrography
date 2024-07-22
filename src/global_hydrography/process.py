from pathlib import Path
import re
import pyogrio
import geopandas as gpd
import pandas as pd

from global_hydrography.preprocess import TDXPreprocessor
from global_hydrography.delineation.mnsi import MNSI_FIELDS



def select_tdx_files(
    directory_path: Path,
    tdxhydroregion: int,
    file_extension: str,
)-> tuple[Path]:
    """Select pairs of TDX 'streamnet' and 'streamreach_basins'
    files for processing together.

    Parameters:
        directory_path: Local directory path to where files are located.
        tdxhydroregion: 10-digit region code used to organize TDXHydro files
            and taken from HydroBASINS Level 2 IDs.
    """
    for item in directory_path.iterdir():
        if (item.is_file() and 
            item.suffix==file_extension and
            str(tdxhydroregion) in item.name
        ):
            if 'streamnet' in item.name:
                streamnet_filepath = item
            if 'basins' in item.name:
                basins_filepath = item

    return (streamnet_filepath, basins_filepath)


def create_basins_mnsi(
    basins_gdf: gpd.GeoDataFrame,
    streams_mnsi_gdf: gpd.GeoDataFrame,
)-> tuple[gpd.GeoDataFrame]:
    """Create Basins GeoDataFrame with MNSI fields from streamnet_mnsi_gdf.

    Parameters:
        basins_gdf: TDX Streamreach Basins dataset, with 'streamID' renamed to 'LINKNO'.
        streams_mnsi_gdf: TDX Stream Network dataset with MNSI fields added.

    Return: A tuple of GeoDataFrames
        basins_mnsi_gdf: A copy of the basins_gdf appended with three MNSI fields.
        streams_no_basin_gdf: A gdf of the streamnet LINKs that have no associated basins.
    """
    
    # Perform a right join, for all rows in streamnet,
    # potentially creating some rows with no basin geometries
    basins_mnsi_gdf = pd.merge(
        basins_gdf, 
        streams_mnsi_gdf[MNSI_FIELDS], 
        how='right', 
        on='LINKNO',
    )
    # Save streamnet rows that don't have a basin geometry
    streams_no_basin_gdf = streams_mnsi_gdf[basins_mnsi_gdf.geometry==None].copy(deep=True)

    # Drop no-geometry rows from basins gdf
    basins_mnsi_gdf.drop(
        streams_no_basin_gdf.index.to_list(), 
        inplace=True,
    )
    
    return (basins_mnsi_gdf, streams_no_basin_gdf)


