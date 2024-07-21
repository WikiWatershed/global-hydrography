from pathlib import Path
import re
import pyogrio
import geopandas as gpd
import pandas as pd

from global_hydrography.preprocess import TDXPreprocessor



def select_tdx_files(
    directory_path: Path,
    tdxhydroregion: int,
    file_extension: str,
)-> list[Path]:
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
                streamnet_file = item
            if 'basins' in item.name:
                basins_file = item

    return (streamnet_file, basins_file)

