"""
Global Hydrography functions for fetching and saving data.
"""

# Imports
from typing import Iterable

import os.path
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import time
from urllib.parse import urlparse

import fsspec
import asyncio
import geopandas as gpd
import requests
import aiohttp


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
        await filesystem._get_file(url, str(filepath))
        print(f"Downloaded {filepath}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")


def init_fsspec_filesystem() -> fsspec.filesystem:
    # originally running into connection timeout issues
    # fspec's implementation of HTTPFileSystem provides user ability to set parameters
    # for the underlying aiohttp.ClientSession. We'll try explicitly setting timeout limit
    client_timeout = aiohttp.ClientTimeout(
        total=0
    )  # total of 0 should indicate no timeouts
    client_kwargs = {
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
    start_time = time.time()
    hybas_ids = [1020000010, 1020011530]
    # hybas_ids = get_hybas_ids()
    asyncio.run(main(hybas_ids))
    end_time = time.time()
    print(end_time - start_time)


# Another method, does not currently work:

# async def get_content_length(url):
#     async with aiohttp.ClientSession() as session:
#         async with session.head(url) as request:
#             return request.content_length


# def parts_generator(size, start=0, part_size=10 * 1024 ** 2):
#     while size - start > part_size:
#         yield start, start + part_size
#         start += part_size
#     yield start, size


# async def download(url, headers, save_path):
#     async with aiohttp.ClientSession(headers=headers) as session:
#         async with session.get(url) as request:
#             file = await aiofiles.open(save_path, 'wb')
#             await file.write(await request.content.read())


# async def process(url):
#     filename = os.path.basename(urlparse(url).path)
#     tmp_dir = TemporaryDirectory(prefix=filename, dir=os.path.abspath('.'))
#     print(tmp_dir)
#     size = await get_content_length(url)
#     tasks = []
#     file_parts = []
#     for number, sizes in enumerate(parts_generator(size)):
#         part_file_name = os.path.join(tmp_dir.name, f'{filename}.part{number}')
#         file_parts.append(part_file_name)
#         tasks.append(download(url, {'Range': f'bytes={sizes[0]}-{sizes[1]}'}, part_file_name))
#     await asyncio.gather(*tasks)
#     with open(filename, 'wb') as wfd:
#         for f in file_parts:
#             with open(f, 'rb') as fd:
#                 shutil.copyfileobj(fd, wfd)


# async def main():
#     urls = ['https://earth-info.nga.mil/php/download.php?file=1020000010-streamnet-gpkg',
#             'https://earth-info.nga.mil/php/download.php?file=1020011530-streamnet-gpkg',
#             'https://earth-info.nga.mil/php/download.php?file=1020000010-basins-gpkg',
#             'https://earth-info.nga.mil/php/download.php?file=1020011530-basins-gpkg']
#     await asyncio.gather(*[process(url) for url in urls])


# if __name__ == '__main__':
#     import time

#     start_code = time.monotonic()
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())
#     print(f'{time.monotonic() - start_code} seconds!')
