# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import aiohttp
import anyio
import bs4

from ._records import File, Folder
from ._url import extract_file_id, extract_folder_id, is_url
from ._utils import init_session


async def retrieve_file(id_or_url: str) -> File:
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


async def retrieve_folder(id_or_url: str) -> Folder:
    """Retrieves the structure of a Google Drive folder.

    Args:
        id_or_url: The ID or URL of the Google Drive folder.

    Returns:
        The folder structure.

    Raises:
        ValueError: If the folder URL is invalid.
        FileNotFoundError: If the folder does not exist.
    """
    id_ = extract_folder_id(id_or_url) if is_url(id_or_url) else id_or_url
    async with aiohttp.ClientSession() as session:
        init_session(session)
        folder = await _build_folder(id_, session=session)
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


async def _build_folder(id_: str, *, session: aiohttp.ClientSession) -> Folder | None:
    """Builds the structure of a Google Drive folder recursively."""
    folder = await _fetch_folder(id_, session=session)
    if folder is None:
        return None

    async def _build_child(idx: int) -> None:
        item = folder.children[idx]
        if isinstance(item, File):
            return

        tmp = await _fetch_folder(item.id, session=session)
        if tmp is None:
            # Here we raise so that all the other tasks are cancelled
            # and the main task can catch the exception and return None.
            raise RuntimeError

        folder.children[idx] = tmp

    try:
        async with anyio.create_task_group() as tg:
            for idx in range(len(folder.children)):
                tg.start_soon(_build_child, idx)
    except Exception:  # noqa: BLE001
        return None

    return folder
