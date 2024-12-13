# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import aiohttp
import anyio
import bs4

from ._records import File, Folder
from ._utils import extract_file_id, extract_folder_id, init_session, is_url


async def fetch_file(id_or_url: str) -> File:
    """Retrieves the name of a Google Drive file.

    Args:
        id_or_url: The ID or URL of the Google Drive file.

    Returns:
        The [File][gdown_async.File] instance.

    Raises:
        FileNotFoundError: If no file is found with the given ID or URL.
        RuntimeError: If an unexpected error occurs while fetching the file.
    """
    id_ = extract_file_id(id_or_url) if is_url(id_or_url) else id_or_url
    async with aiohttp.ClientSession() as session:
        init_session(session)
        url = f"https://drive.google.com/file/d/{id_}/view?usp=drive_link"
        async with session.get(url) as response:
            if response.status != 200:
                msg = f"No file found with ID '{id_}'."
                raise FileNotFoundError(msg)

            content = await response.text()

    soup = bs4.BeautifulSoup(content, "html.parser")
    if soup.title is None:
        msg = f"An unexpected error occurred while fetching the file with ID '{id_}'."
        raise RuntimeError(msg)

    return File(id_, soup.title.text.removesuffix(" - Google Drive"))


async def fetch_folder(id_or_url: str, *, max_depth: int | None = None) -> Folder:
    """Retrieves the structure of a Google Drive folder.

    Args:
        id_or_url: The ID or URL of the Google Drive folder.
        max_depth: The maximum depth of the folder structure to retrieve. If `None`, the
            entire folder structure is fetched.

    Returns:
        The folder structure.

    Raises:
        ValueError: If the maximum depth is not a positive integer.
        ValueError: If the folder URL is invalid.
        FileNotFoundError: If the folder does not exist.
    """
    if max_depth is not None:
        if max_depth < 1:
            msg = f"Maximum depth must be a positive integer, got {max_depth}."
            raise ValueError(msg)
    elif max_depth is None:
        max_depth = -1

    id_ = extract_folder_id(id_or_url) if is_url(id_or_url) else id_or_url
    async with aiohttp.ClientSession() as session:
        init_session(session)
        folder = await _fetch_folder_rec(id_, depth=max_depth, session=session)
        if folder is None:
            msg = f"No folder found with ID '{id_}'."
            raise FileNotFoundError(msg)

        return folder


# --------------------------------------------------------------------------- #
# Private functions
# --------------------------------------------------------------------------- #


async def _fetch_folder(id_: str, *, session: aiohttp.ClientSession) -> Folder | None:
    """Fetches the name and contents of a Google Drive folder."""
    url = f"https://drive.google.com/drive/folders/{id_}"
    async with session.get(url) as response:
        if response.status != 200:
            return None

        content = await response.text()

    soup = bs4.BeautifulSoup(content, "html.parser")
    if soup.title is None:
        return None
    name = soup.title.text.removesuffix(" - Google Drive")

    files = [
        File(div["data-id"], div.find("div", class_="KL4NAf").text)
        for div in soup.find_all("div", class_="WYuW0e Ss7qXc")
    ]

    folders = [
        Folder(div["data-id"], div.find("div", class_="KL4NAf").text, [])
        for div in soup.find_all("div", class_="WYuW0e RDfNAe Ss7qXc")
    ]

    return Folder(id_, name, files + folders)


async def _fetch_folder_rec(
    id_: str,
    *,
    depth: int,
    session: aiohttp.ClientSession,
) -> Folder | None:
    """Builds the structure of a Google Drive folder recursively."""
    folder = await _fetch_folder(id_, session=session)
    if folder is None or depth == 1:
        return folder

    async def _fetch_child(idx: int) -> None:
        f = folder.children[idx]
        f = await _fetch_folder_rec(f.id, depth=depth - 1, session=session)
        if f is None:
            # Here we raise so that all the other tasks are cancelled
            # and the main task can catch the exception and return None.
            raise RuntimeError

        folder.children[idx] = f

    try:
        async with anyio.create_task_group() as tg:
            for idx, item in enumerate(folder.children):
                if isinstance(item, Folder):
                    tg.start_soon(_fetch_child, idx)
    except Exception:  # noqa: BLE001
        return None

    return folder
