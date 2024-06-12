import os
from pathlib import Path
import geopandas as gpd
import fsspec

# Writes the file information to output.txt
def check_files():
    output_file_path = 'J:\\MMW\\TDX_Hydro\\output.txt'
    with open(output_file_path, 'w') as output_file:
        for file in os.listdir('J:\\MMW\\TDX_Hydro'):
            file_path = os.path.join('J:\\MMW\\TDX_Hydro', file)
            try:
                df = gpd.read_file(file_path)
                output_file.write(f"-----------------------------------------------\n")
                output_file.write(f"File: {file}\n")
                df.info(buf=output_file)
                output_file.write(f"Size: {df.size}\n")
                output_file.write(f"-----------------------------------------------\n\n\n")
                print(f"{file} done!")
            except Exception as e:
                print(f"ERROR for {file}: ", e)

# Compares the local vs remote file size
def check_size():
    tdx_fs = fsspec.filesystem(protocol='http')
    ROOT_URL = "https://earth-info.nga.mil/php/download.php"
    
    for file in os.listdir('J:\\MMW\\TDX_Hydro'):
        if(file == 'output.txt' or file == 'hydrobasins_level2.geojson'):
            continue

        url_file = file.replace('.', '-')
        url = f"{ROOT_URL}?file={url_file}"
        try:
            remote_size = tdx_fs.info(url)['size']
        except FileNotFoundError:
            print(f"File not found: {url}")
            continue
        
        file_path = os.path.join('J:\\MMW\\TDX_Hydro', file)
        try:
            local_size = os.path.getsize(file_path)
        except FileNotFoundError:
            print(f"File not found: {file_path}")

        if (remote_size == local_size):
            print(f"{file}: EQUAL, {remote_size}")
        else:
            print(f"{file}: NOT EQUAL, r: {remote_size}, l: {local_size}")
        

if __name__ == "__main__":
    check_files()