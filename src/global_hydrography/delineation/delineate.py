'''Global Hydrography (gh) functions to subset and delineate a watershed from
mnsi & hydro unit fields added during gh processing.
'''

import geopandas as gpd
from shapely.geometry import Point, Polygon

from global_hydrography.delineation.mnsi import (
    MNSI_FIELDS, DISCOVER, FINISH, ROOT
)


def subset_network(gdf: gpd.GeoDataFrame, linkid: int) -> gpd.GeoDataFrame:
    """Subset a basins (gdf) to include only elements upstream of linkid

    Args:
        gdf (gpd.GeoDataFrame): A GeoDataFrame representation of the
            basins dataset where the stream reach with linkid resides.
        linkid (int): The global unique identifier for the stream
            network of interest

    Returns:
        gpd.GeoDataFrame: Subsetted GeoDataFrame containing all basins
            upstream of the basin corresponding to linkno
    """
    # TODO: Rename function to `get_upstream_basins()` 
    # or `get_upstream_links()` if we also want to use it for streams.

    # ID target basins from linkno and extract critical mnsi info
    # this is assuming the gdf has already set index to streamID
    target_basin = gdf.loc[linkid]
    root_id = target_basin[ROOT]
    discover_time = target_basin[DISCOVER]
    finish_time = target_basin[FINISH]

    # subset using modified nest set index logic, further documented in README
    return gdf.loc[
        (gdf[ROOT] == root_id)
        & (gdf[DISCOVER] >= discover_time)
        & (gdf[FINISH] <= finish_time)
    ]


def get_linkno_by_latlon(
    basins_gdf: gpd.GeoDataFrame,
    lat: float,
    lon: float,
) -> int:
    """Finds the single basin record that contains the latitude and longitude
    for a single TDX Hydro Region.
    
    Args:
        gdf (GeoDataFrame): A GeoDataFrame representation of the
            basins dataset that contains the latitude and longitude.
        lat (float): The latitude of the selected point location. 
        lon (float): The longitude of the selected point location.
    Returns:
        int: The LINKNO for the record.
    """
    point = Point(lon, lat)

    return basins_gdf.loc[
        basins_gdf.geometry.contains(point)
    ].index.values[0]



def get_watershed_boundary(
    upstream_basins_gdf: gpd.GeoDataFrame,
    simplify: bool = True,
) -> Polygon:
    """
    """
    # if upstream_basins_gdf.size < 500

    boundary = upstream_basins_gdf.geometry.union_all(method='coverage') 
        # method is 18.5x Faster, but only for non-overlapping polygons

    return boundary
