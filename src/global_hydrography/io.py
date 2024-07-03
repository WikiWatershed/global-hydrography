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


class TDXHydroDownloader:

    ROOT_URL = "https://earth-info.nga.mil/php/download.php"

    def __init__(
        self, 
        filesystem: fsspec.filesystem = None, 
        download_dir: Path = None,
    ) -> None:
        self.__filesystem: fsspec.filesystem = (
            filesystem if filesystem else self.init_fsspec_filesystem()
        )
        self.__download_dir: Path = self.create_data_directory(download_dir)

    @staticmethod
    def init_fsspec_filesystem(
        connection_limit: int = 2, timeout: int = 0
    ) -> fsspec.filesystem:
        """Initializes a HTTP Filesystem object for download of TDXHydroData"""

        # originally we were running into connection timeout issues
        # fspec's implementation of HTTPFileSystem provides user ability to set parameters
        # for the underlying aiohttp.ClientSession. Though it turned out the connection was
        # being closed on the hosts end
        client_timeout = aiohttp.ClientTimeout(
            total=timeout
        )  # total of 0 should indicate no timeouts

        # to reduce likelihood of host closing connections, we want to decrease the number of
        # simultaneous connections we have. Testing found that <2 connections was reasonably stable
        # but I will still provide user ability to set this limit if desired.
        connector = aiohttp.TCPConnector(limit=connection_limit)

        client_kwargs = {
            "connector": connector,
            "timeout": client_timeout,
        }
        return fsspec.filesystem("http", asynchronous=True, client_kwargs=client_kwargs)

    @staticmethod
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
            os.mkdir(data_dir)  # TODO: replace with pathlib: `data_dir.mkdir()`
        return data_dir

    def get_hybas_ids(
        self, 
        hydrobasins_filename: str = "hydrobasins_level2",
    ) -> list[str]:
        """Downloads the large hydrobasins file and extracts the HYBAS ids from the file"""
        hydrobasins_url = f"{self.ROOT_URL}?file={hydrobasins_filename}"
        logger.debug(f"Downloading from {hydrobasins_url}")
        fs = fsspec.filesystem("http", asynchronous=False)  # use synchronous filesystem

        try:
            fs.exists(hydrobasins_url)
            # download the file
            file_name = hydrobasins_filename + ".geojson"
            local_filepath = self.__download_dir / file_name
            fs.get_file(hydrobasins_url, str(local_filepath))
            # parse file to extract HYDAS ids
            hydro_gdf = gpd.read_file(local_filepath)
            hybas_ids = hydro_gdf["HYBAS_ID"].tolist()
            return hybas_ids
        except Exception as e:
            logger.error(
                f"Unable to locate or parse file at {hydrobasins_url}. Provide override to default with `hydrobasins_url` argument, or check Basin GeoJSON File with ID Numbers"
            )
            raise e

    async def __download_file(
        self,
        file_name: str,
        extension: str = "gpkg",
    ) -> None:
        url = f"{self.ROOT_URL}?file={file_name}-{extension}"
        save_path = self.__download_dir.joinpath(f"{file_name}.{extension}") #TODO: remove file_name to preserve original filename
        try:

            logger.info(f"Attempting download of {url}")
            await self.__filesystem._get_file(url, str(save_path))
            logger.info(f"Downloaded file and save to {save_path}")
        except Exception as e:
            logger.error(f"Failed to download {url}, with exception `{e}`")

    async def download_files(
        self,
        hybas_ids: Iterable[str | int],
        dataset_names: Iterable[str],
    ) -> None:
        """Coroutine to download corresponding files"""
        session = await self.__filesystem.set_session()

        tasks = []
        for hybas_id in hybas_ids:
            for dataset in dataset_names:
                file_name = f"{hybas_id}-{dataset}"
                tasks.append(self.__download_file(file_name))

        # Run all tasks concurrently
        await asyncio.gather(*tasks)
        await session.close()  # Explicitly close the session


async def main(hybas_ids: Iterable[int | str] = None, datasets: Iterable[str] = None):
    downloader = TDXHydroDownloader()
    if not datasets:
        datasets = ("basins", "streamnet")
    if not hybas_ids:
        hybas_ids = downloader.get_hybas_ids()
    await downloader.download_files(hybas_ids, datasets)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    start_time = time.time()
    asyncio.run(main())
    end_time = time.time()
    print(end_time - start_time)
