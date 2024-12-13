# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import urllib.parse

import aiohttp
import anyio

from ._records import Folder

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
)


def init_session(session: aiohttp.ClientSession) -> None:
    """Initializes the session with the default headers."""
    session.headers["User-Agent"] = _USER_AGENT


async def check_file_path(path: anyio.Path) -> None:
    """Checks that the provided path can be used as an output file.

    Args:
        path: The path to check.

    Raises:
        IsADirectoryError: If the path is a directory.
    """
    if await path.exists():
        if not await path.is_file():
            msg = f"Output path '{path}' is not a file."
            raise IsADirectoryError(msg)

        return

    # to verify that the provided path is valid, we try to create it and then delete it
    await path.parent.mkdir(parents=True, exist_ok=True)
    await path.touch()
    await path.unlink()


async def check_folder_path(folder: Folder, path: anyio.Path) -> None:
    """Checks that the provided path can be used as an output directory.

    Args:
        folder: The folder structure to check.
        path: The path to check.

    Raises:
        NotADirectoryError: If any path in the folder associated to the folder or
            any of its subfolders is not a directory.
        IsADirectoryError: If any path in the folder associated to a file within the
            folder (or any of its subfolders) is a directory.
    """
    if await path.exists():
        if not await path.is_dir():
            msg = f"Output directory '{path}' is not a directory."
            raise NotADirectoryError(msg)

        for item in folder:
            if isinstance(item, Folder):
                await check_folder_path(item, path / item.name)
            else:
                await check_file_path(path / item.name)

        return

    # to verify that the path is valid, we try to create it
    await path.mkdir(parents=True, exist_ok=True)


def is_url(url: str) -> bool:
    """Checks if the string is a URL."""
    return url.startswith(("http://", "https://"))


def extract_file_id(url: str) -> str:
    """Extracts the file ID from a Google Drive URL.

    The Google Drive URL must have one of the following formats:
    - `https://drive.google.com/file/d/<file_id>/...`
    - `https://drive.google.com/uc?id=<file_id>`

    Args:
        url: The Google Drive URL.

    Returns:
        The file ID extracted from the URL.

    Raises:
        ValueError: If the URL is invalid.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "drive.google.com":
        msg = f"Invalid Google Drive file URL '{url}'."
        raise ValueError(msg)

    parts = parsed.path.split("/")
    if len(parts) >= 4 and parts[1] == "file" and parts[2] == "d":
        return parts[3]

    query = urllib.parse.parse_qs(parsed.query)
    if "id" in query and len(query["id"]) == 1:
        return query["id"][0]

    msg = f"Invalid Google Drive file URL '{url}'."
    raise ValueError(msg)


def extract_folder_id(url: str) -> str:
    """Extracts the folder ID from a Google Drive URL.

    The Google Drive URL must have the following format:
    `https://drive.google.com/drive/folders/<folder_id>`

    Args:
        url: The Google Drive URL.

    Returns:
        The folder ID extracted from the URL.

    Raises:
        ValueError: If the URL is invalid.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "drive.google.com":
        msg = f"Invalid Google Drive folder URL '{url}'."
        raise ValueError(msg)

    parts = parsed.path.split("/")
    if len(parts) != 4 or parts[1] != "drive" or parts[2] != "folders":
        msg = f"Invalid Google Drive folder URL '{url}'."
        raise ValueError(msg)

    if not parts[3]:
        msg = f"Invalid Google Drive folder URL '{url}'."
        raise ValueError(msg)

    return parts[3]
