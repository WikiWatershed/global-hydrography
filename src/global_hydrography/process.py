from pathlib import Path
import re
import pyogrio
import geopandas as gpd
import pandas as pd

from global_hydrography.preprocess import TDXPreprocessor
from global_hydrography.delineation.mnsi import MNSI_FIELDS, DISCOVER, FINISH, ROOT
from global_hydrography.delineation import subset_network


DISSOLVE_ROOT_ID = "DISSOLVE_ROOT_ID"
ELEMENT_COUNT = "ELEMENT_COUNT"


def select_tdx_files(
    directory_path: Path,
    tdxhydroregion: int,
    file_extension: str,
) -> tuple[Path]:
    """Select pairs of TDX 'streamnet' and 'streamreach_basins'
    files for processing together.

    Parameters:
        directory_path: Local directory path to where files are located.
        tdxhydroregion: 10-digit region code used to organize TDXHydro files
            and taken from HydroBASINS Level 2 IDs.
    """
    for item in directory_path.iterdir():
        if (
            item.is_file()
            and item.suffix == file_extension
            and str(tdxhydroregion) in item.name
        ):
            if "streamnet" in item.name:
                streamnet_filepath = item
            if "basins" in item.name:
                basins_filepath = item

    return (streamnet_filepath, basins_filepath)


def create_basins_mnsi(
    basins_gdf: gpd.GeoDataFrame,
    streams_mnsi_gdf: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame]:
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
        how="right",
        on="LINKNO",
    )
    # Save streamnet rows that don't have a basin geometry
    streams_no_basin_gdf = streams_mnsi_gdf[basins_mnsi_gdf.geometry == None].copy(
        deep=True
    )

    # Drop no-geometry rows from basins gdf
    basins_mnsi_gdf.drop(
        streams_no_basin_gdf.index.to_list(),
        inplace=True,
    )

    return (basins_mnsi_gdf, streams_no_basin_gdf)


def compute_dissolve_groups(
    gdf: gpd.GeoDataFrame,
    max_elements: int = 200,
    min_elements: int = 150,
) -> gpd.GeoDataFrame:
    """Adds additional field to indicating downstream most linkid of dissolve group

    Args:
        gdf (gpd.GeoDataFrame): GeoDataFrame object for the basins layer
        max_elements (int, optional): Maximum number of upstream elements to pre-dissolve.
            Defaults to 200.
        min_elements (int, optional): Minimum number of upstream elements to pre-dissolve.
            Note that min_elements is aspirational, depending on the basins, it may be necessary
            to temporary reduce.
            Defaults to 150. Cannot be less than 2.

    Raises:
        ValueError: If minimum_elements<2

    Returns:
        gpd.GeoDataFrame: Modified basins GeoDataFrame with dissolve group id
    """
    if min_elements < 2:
        raise ValueError("min_elements needs to be greater than two.")
    _min_elements = min_elements

    # we are going to be mutating the dataframe, so let's make a copy
    gdf = gdf.copy(deep=True)

    # we'll use the upstream element count for aggregation, initial this can be
    # determined using nested set indices. Later we'll need a new method.
    gdf[ELEMENT_COUNT] = gdf[FINISH] - gdf[DISCOVER]
    gdf[DISSOLVE_ROOT_ID] = None

    previous = gdf[ROOT].count()
    while gdf.loc[gdf[DISSOLVE_ROOT_ID].isnull(), ROOT].count() > max_elements:
        gdf = __identify_dissolve_groups(gdf, max_elements, _min_elements)
        remaining = gdf.loc[gdf[DISSOLVE_ROOT_ID].isnull(), ROOT].count()
        print(f"Previous elements {previous}, new elements {remaining}")
        # if we failed to make any dissolve progress, lower the threshold.
        if previous == remaining:
            _min_elements -= 25
            print(f"No progress was made. New min threshold is {_min_elements}")
            continue
        elif _min_elements != min_elements:
            _min_elements = min_elements
            print(f"Min threshold reset to {min_elements}")

        previous = remaining

        gdf = __update_element_counts(gdf)

    gdf = gdf.drop(columns=[ELEMENT_COUNT])
    return gdf


def __update_element_counts(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Update element count to exclude elements already in dissolve group"""
    sub = gdf.loc[gdf[DISSOLVE_ROOT_ID].isnull()]

    # define help function with knowledge of sub
    def __count(x) -> int:
        return subset_network(sub, x)[ROOT].count()

    # loop elements in the subset, updating the corresponding element in
    # parent data frame
    for i in sub.index:
        gdf.loc[i, ELEMENT_COUNT] = __count(i)
    return gdf


def __identify_dissolve_groups(
    gdf: gpd.GeoDataFrame,
    max_elements: int,
    min_elements: int,
) -> gpd.GeoDataFrame:
    # the stop condition is when all upstream not already in a dissolve group and within
    # the grouping have been exhausted
    while (
        gdf.loc[
            (gdf[DISSOLVE_ROOT_ID].isnull()) & (gdf[ELEMENT_COUNT] <= max_elements),
            ELEMENT_COUNT,
        ].max()
        > min_elements
    ):
        # find the element with the largest element count still above the processing threshold
        # we want to process largest first because otherwise we'd pre-dissolve the upstream
        # elements and then pre-dissolve them again with the downstream element (inefficient).
        df = gdf.loc[
            (gdf[DISSOLVE_ROOT_ID].isnull()) & (gdf[ELEMENT_COUNT] <= max_elements)
        ]
        element = df.sort_values([ELEMENT_COUNT], ascending=False).iloc[0]
        # dissolve the polygon using helper function
        gdf = __tag_dissolve_group(gdf, element.name)

    return gdf


def __tag_dissolve_group(gdf: gpd.GeoDataFrame, linkid: int) -> gpd.GeoDataFrame:
    """Dissolves polygons upstream of linkid and places them in gdf"""

    # subset network to only elements upstream of the linkid
    sub = subset_network(gdf, linkid)
    # further subset to only elements not already in dissolve group
    sub = sub.loc[sub[DISSOLVE_ROOT_ID].isnull()]

    # get id's for the rows that are now represented by a dissolved polygon
    elements = sub.index

    # update elements to indicate they are part of this dissolve group
    gdf.loc[elements, DISSOLVE_ROOT_ID] = linkid

    return gdf
