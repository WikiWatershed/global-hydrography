"""
Global Hydrography functions for fetching and saving data.
"""

from typing import Iterable

import os
import sys
from pathlib import Path
import time
import logging

import fsspec
import asyncio
import geopandas as gpd
import aiohttp

logger = logging.getLogger(__name__)


def get_tdxhydro():
    root_url = "https://earth-info.nga.mil/php/download.php"
    hydrobasins_filename = "hydrobasins_level2"
    hydrobasins_url = f"{root_url}?file={hydrobasins_filename}"


def get_hybas_ids():
    root_url = "https://earth-info.nga.mil/php/download.php"
    hydrobasins_filename = "hydrobasins_level2"
    hydrobasins_url = f"{root_url}?file={hydrobasins_filename}"
    fsspec_http = fsspec.filesystem(protocol="http", timeout=None)

    try:
        fsspec_http.exists(hydrobasins_url)
    except:
        print("Check Basin GeoJSON File with ID Numbers URL")

    working_dir = Path.cwd()
    project_dir = working_dir.parent
    data_dir = project_dir / "global-hydrography/data_temp"
    data_dir.mkdir(parents=True, exist_ok=True)

    file_name = hydrobasins_filename + ".geojson"
    local_filepath = data_dir / file_name

    fsspec_http.get_file(hydrobasins_url, str(local_filepath))
    hydro_gdf = gpd.read_file("../data_temp/hydrobasins_level2.geojson")
    hybas_ids = hydro_gdf["HYBAS_ID"].tolist()

    return hybas_ids


async def download_file(
    filesystem: fsspec.filesystem,
    url: str,
    filepath: str,
) -> None:
    try:
        logger.info(f"Attempting download of {url}")
        # await filesystem._get_file(url, str(filepath))
        logger.info(f"Downloaded {filepath}")
    except Exception as e:
        logger.error(f"Failed to download {url}, with exception `{e}`")


def init_fsspec_filesystem() -> fsspec.filesystem:
    # originally running into connection timeout issues
    # fspec's implementation of HTTPFileSystem provides user ability to set parameters
    # for the underlying aiohttp.ClientSession. We'll try explicitly setting timeout limit
    connector = aiohttp.TCPConnector(limit=2)
    client_timeout = aiohttp.ClientTimeout(
        total=0
    )  # total of 0 should indicate no timeouts
    client_kwargs = {
        "connector": connector,
        "timeout": client_timeout,
    }
    return fsspec.filesystem("http", asynchronous=True, client_kwargs=client_kwargs)


def create_data_directory(data_dir: str = None) -> Path:
    if data_dir:
        data_dir = Path(data_dir)
    else:
        working_dir = Path.cwd()
        project_dir = working_dir.parent
        data_dir = (
            project_dir / "global-hydrography/data_temp"
        )  # Temporary data directory to be .gitignored
    # create the directory if necessary
    if not data_dir.exists():
        os.mkdir(data_dir)
    return data_dir


async def main(hybas_ids: Iterable[int | str]):
    filesystem = init_fsspec_filesystem()
    session = await filesystem.set_session()

    root_url = "https://earth-info.nga.mil/php/download.php"

    data_dir = create_data_directory()

    tasks = []
    for hybas_id in hybas_ids:
        # Construct the URLs
        basin_url = f"{root_url}?file={hybas_id}-basins-gpkg"
        stream_url = f"{root_url}?file={hybas_id}-streamnet-gpkg"

        # Construct the file paths
        basin_filepath = data_dir / f"TDX_streamreach_basins_{hybas_id}_01.gpkg"
        stream_filepath = data_dir / f"TDX_streamnet_basins_{hybas_id}_01.gpkg"

        # Add download tasks
        tasks.append(download_file(filesystem, basin_url, basin_filepath))
        tasks.append(download_file(filesystem, stream_url, stream_filepath))

    # Run all tasks concurrently
    await asyncio.gather(*tasks)
    await session.close()  # Explicitly close the session


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    start_time = time.time()
    hybas_ids = [1020000010, 1020011530]
    # hybas_ids = get_hybas_ids()
    asyncio.run(main(hybas_ids))
    end_time = time.time()
    print(end_time - start_time)
