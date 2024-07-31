import geopandas as gpd


def subset_network(gdf: gpd.GeoDataFrame, linkid: int) -> gpd.GeoDataFrame:
    """Subset a basins (gdf) to include only elements upstream of linkid

    Args:
        gdf (gpd.GeoDataFrame): and GeoDataFrame representation of the
            basins dataset where the stream reach with linkid resides.
        linkid (int): The global unique identifier for the stream
            network of interest

    Returns:
        gpd.GeoDataFrame: Subsetted GeoDataFrame containing all basins
            upstream of the basin corresponding to linkno
    """
    # ID target basins from linkno and extract critical mnsi info
    # this is assuming the gdf has already set index to streamID
    target_basin = gdf.loc[linkid]
    root_id = target_basin["ROOT_ID"]
    discover_time = target_basin["DISCOVER_TIME"]
    finish_time = target_basin["FINISH_TIME"]

    # subset using modified nest set index logic, further documented in README
    return gdf.loc[
        (gdf["ROOT_ID"] == root_id)
        & (gdf["DISCOVER_TIME"] >= discover_time)
        & (gdf["FINISH_TIME"] <= finish_time)
    ]
