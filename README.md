<div align="center">

# gdown-async

<h4>Google Drive downloader with async support for Python</h4>


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![basedpyright - checked](https://img.shields.io/badge/basedpyright-checked-42b983)](https://docs.basedpyright.com)

[![Python](https://img.shields.io/badge/python-3.10_%7C_3.11_%7C_3.12_%7C_3.13-blue?logo=python&logoColor=white)](https://www.python.org/)

</div>

## Installation

If you only need to use `gdown-async` as a library, you can install it via pip:

```bash
pip install gdown-async
```

If you also want to use the CLI, you can simply install the optional `cli` extra:

```bash
pip install gdown-async[cli]
```

## Usage

### As a library

To download a file from Google Drive, you can use the `download_file` function:

```python
import anyio
from gdown_async import download_file

async def main():
    await download_file("file_id_or_url", output_dir="path/to/output/dir")

anyio.run(main)
```

If passed a `FILE_ID` or `FILE_URL`, the function will download the corresponding file into the specified `output_dir` with the name of the file stored on Google Drive. If you want to specify a different filename, you can pass a `File` object instead:

```python
import anyio
from gdown_async import download_file, File, fetch_file

async def main():
    file = File("file_id", name="filename")
    # NOTE: to create a File object you need to use the file_id, not the file URL
    # if you only have the URL, you can use the fetch_file function to get the file_id
    # file = await fetch_file("file_id_or_url")
    # file.name = "filename"

    await download_file(file, output_dir="path/to/output/dir")
```

Similarly, you can use the `download_folder` function to download a folder:

```python
import anyio
from gdown_async import download_folder

async def main():
    await download_folder("folder_id_or_url", output_dir="path/to/output/dir")

anyio.run(main)
```

The `download_folder` function will download the entire folder structure into the specified `output_dir` with the same names as on Google Drive. If you want to specify a different folder/subfolder/file name or only download specific files, you can use the `Folder` object:

```python
import anyio
from gdown_async import download_folder, Folder, fetch_folder

async def main():
    folder = await fetch_folder("folder_id_or_url")
    # modify the folder object as needed

    await download_folder(folder, output_dir="path/to/output/dir")

anyio.run(main)
```

### From the CLI

To download a file from Google Drive, you can use the `gdown-async` command:

```bash
gdown-async --file FILE_ID_OR_URL
```

Similarly, you can use the `gdown-async` command to download a folder:

```bash
gdown-async --folder FOLDER_ID_OR_URL
```

The following optional flags are available for both file and folder downloads:

- `--output-dir` or `-o`: Directory where the file/folder will be downloaded (default: `.`). When downloading a file, the file will be saved inside this directory with the name of the file stored on Google Drive. When downloading a folder, the root folder will be saved inside this directory with the same name as on Google Drive.
- `--quiet` or `-q`: Suppress all output except for errors (default: `False`).
- `--force` or `-f`: Overwrite existing files (default: `False`). If this flag is not set, the program will skip downloading files that already exist in the output directory (no check is made to verify that the existing file is the same as the one being downloaded, only the filename is checked).

When downloading a folder, you can also use the following optional flags:

- `--max-concurrency` or `-c`: Maximum number of concurrent downloads (default: `None`). If not specified, no limit is set.
- `--max-depth` or `-d`: Maximum depth of the folder structure to download (default: `None`). If not specified, the entire folder structure will be downloaded.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.