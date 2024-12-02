# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import dataclasses
import functools
import os
import urllib.parse
from collections.abc import Iterator, Sequence
from typing import Protocol

import aiohttp
import anyio
import bs4

from ._file import File, FileDownloadCallback, check_file_path, download
from ._utils import USER_AGENT, is_url

# --------------------------------------------------------------------------- #
# Public classes
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class Folder:
    """A Google Drive folder."""

    id: str
    name: str
    children: list["File | Folder"]

    def __iter__(self) -> Iterator["File | Folder"]:
        yield from self.children


class FolderDownloadCallback(FileDownloadCallback, Protocol):
    """A callback protocol for the download of a Google Drive folder."""

    async def on_folder_setup(self, folder: Folder, path: anyio.Path) -> None:
        """Called when all the necessary setup has been completed.

        Note:
            This method is called only once at the beginning of the download
            for the root folder (i.e., it is not called for its subfolders).

        Args:
            folder: The root folder.
            path: The directory where the items of the folder will be saved (and
                not the directory where the root folder will be saved).
        """

    async def on_folder_start(self, folder: Folder) -> None:
        """Called when the download of a folder starts.

        This method is called for each folder in the hierarchy, starting from
        the root folder and then for each subfolder.

        Args:
            folder: The folder that is being downloaded.
        """

    async def on_folder_complete(self, folder: Folder) -> None:
        """Called when the download of a folder completes.

        The download of a folder is considered complete when all its items have
        been downloaded (i.e., files and subfolders). This method is called for
        each folder in the hierarchy, starting from the leaf folders and then
        moving up to the root folder.

        Args:
            folder: The folder that has been downloaded.
        """

    async def on_folder_fail(self, folder: Folder, exc: BaseException) -> None:
        """Called when the download of a folder fails.

        This method is called when an exception is raised during the download
        of a folder (i.e., during the download of its items). The exception is
        passed as an argument to this method. This method is called for each
        folder in the hierarchy, starting from the leaf folders (where the
        exception occurred) and then moving up to the root folder.

        Args:
            folder: The folder that failed to download.
            exc: The exception that caused the failure.
        """

    async def on_folder_cleanup(self, folder: Folder, *, success: bool) -> None:
        """Called after the download of the root folder completes or fails.

        Note:
            This method is called only once at the end of the download for the
            root folder (i.e., it is not called for its subfolders).

        Args:
            folder: The root folder.
            success: Whether the download of the root folder completed successfully.
        """


# --------------------------------------------------------------------------- #
# Public functions
# --------------------------------------------------------------------------- #


def extract_folder_id(url: str) -> str:
    """Extracts the folder ID from a Google Drive URL.

    The Google Drive URL must have the following format:
    `https://drive.google.com/drive/folders/<folder_id>`

    Args:
        url: The Google Drive URL.

    Returns:
        The folder ID if found, `None` otherwise.

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


async def find_subfolder_id(root: str, path: Sequence[str]) -> str:
    """Finds the ID of a subfolder in a Google Drive folder.

    Args:
        root: The ID or URL of the Google Drive folder.
        path: The path to the subfolder.

    Returns:
        The ID of the subfolder if found, `None` otherwise.

    Raises:
        ValueError: If the root folder URL is invalid.
        FileNotFoundError: If the root folder does not exist.
        FileNotFoundError: If the subfolder or any of its parents does not exist.
        RuntimeError: If an unexpected error occurs while fetching the subfolder.
    """
    id_ = extract_folder_id(root) if is_url(root) else root
    async with aiohttp.ClientSession() as session:
        session.headers["User-Agent"] = USER_AGENT

        folder = await _build_folder(id_, session=session)
        if folder is None:
            msg = f"No root folder found with ID '{id_}'."
            raise FileNotFoundError(msg)

        traversed: list[str] = []
        for name in path:
            for item in folder:
                if isinstance(item, Folder) and item.name == name:
                    folder = item
                    break
            else:
                msg = f"No subfolder found with path '.{'/'.join(traversed)}/{name}'."
                raise FileNotFoundError(msg)

            folder = await _build_folder(folder.id, session=session)
            if folder is None:
                # Here an error occurred while fetching the subfolder, because
                # we know that the subfolder exists (we just found it in the loop above)
                # but now we cannot retrieve its structure.
                msg = (
                    "An unexpected error occurred while fetching the subfolder "
                    f"'.{'/'.join(traversed)}/{name}'."
                )
                raise RuntimeError(msg)

            traversed.append(folder.name)

        return folder.id


async def retrieve_folder(id_or_url: str) -> Folder:
    """Retrieves the structure of a Google Drive folder.

    Args:
        id_or_url: The ID or URL of the Google Drive folder.

    Returns:
        The folder structure if the folder exists, `None` otherwise.

    Raises:
        ValueError: If the folder URL is invalid.
        FileNotFoundError: If the folder does not exist.
    """
    id_ = extract_folder_id(id_or_url) if is_url(id_or_url) else id_or_url
    async with aiohttp.ClientSession() as session:
        session.headers["User-Agent"] = USER_AGENT
        folder = await _build_folder(id_, session=session)
        if folder is None:
            msg = f"No folder found with ID '{id_}'."
            raise FileNotFoundError(msg)

        return folder


async def download_folder(
    x: Folder | str,
    /,
    *,
    output_dir: os.PathLike[str] | str = ".",
    force: bool = False,
    max_concurrency: int | None = None,
    callback: FolderDownloadCallback | None = None,
) -> None:
    """Downloads a folder from Google Drive.

    Args:
        x: Either the ID of the Google Drive folder, the URL of the folder or the
            folder structure. If the folder structure is provided, only the items in
            the structure will be downloaded (i.e., if you query the structure of a
            folder and then you remove some items from it, only the remaining items
            will be downloaded, not the whole original folder).
        output_dir: The directory where to save the folder. If the directory does not
            exist, it will be created. If it exists, the folder will be saved inside it.
        force: Whether to force the download of all the files even if they already
            exist. If `False` and a file already exists, the download will be skipped
            (no check is done to verify if the file is complete, corrupted or outdated).
        max_concurrency: The maximum number of concurrent downloads. If `None`, the
            number of concurrent downloads is not limited.
        callback: A callback to use for the download of the folder.

    Raises:
        NotADirectoryError: If the output path already exists but it is not a directory.
        ValueError: If the folder URL is invalid.
        FileNotFoundError: If the folder does not exist.
    """
    if isinstance(x, str):
        id_ = extract_folder_id(x) if is_url(x) else x
        folder = await retrieve_folder(id_)
    else:
        folder = x

    success = False
    path = anyio.Path(output_dir) / folder.name
    await _check_folder_path(folder, path)

    try:
        if callback is not None:
            await callback.on_folder_setup(folder, path)

        limiter = anyio.CapacityLimiter(max_concurrency) if max_concurrency else None
        async with aiohttp.ClientSession() as session:
            session.headers["User-Agent"] = USER_AGENT
            await _download_folder(
                folder,
                path=path,
                force=force,
                session=session,
                limiter=limiter,
                callback=callback,
            )

        success = True
    finally:
        if callback is not None:
            await callback.on_folder_cleanup(folder, success=success)


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


async def _check_folder_path(folder: Folder, path: anyio.Path) -> None:
    """Checks that the provided path is a valid output directory."""
    if await path.exists():
        if not await path.is_dir():
            msg = f"Output directory '{path}' is not a directory."
            raise NotADirectoryError(msg)

        for item in folder:
            if isinstance(item, Folder):
                await _check_folder_path(item, path / item.name)
            else:
                await check_file_path(path / item.name)

        return

    # to verify that the path is valid, we try to create it
    await path.mkdir(parents=True, exist_ok=True)


async def _download_folder(  # noqa: PLR0913
    folder: Folder,
    path: anyio.Path,
    *,
    force: bool = False,
    session: aiohttp.ClientSession,
    limiter: anyio.CapacityLimiter | None = None,
    callback: FolderDownloadCallback | None = None,
) -> None:
    """Downloads a Google Drive folder recursively."""
    try:
        if callback is not None:
            await callback.on_folder_start(folder)

        await path.mkdir(parents=True, exist_ok=True)
        async with anyio.create_task_group() as tg:
            for item in folder:
                if isinstance(item, Folder):
                    fn = functools.partial(
                        _download_folder,
                        item,
                        path / item.name,
                        force=force,
                        session=session,
                        callback=callback,
                    )
                else:
                    fn = functools.partial(
                        _donwload_file,
                        item,
                        path / item.name,
                        force=force,
                        session=session,
                        limiter=limiter,
                        callback=callback,
                    )

                tg.start_soon(fn)
    except BaseException as exc:
        if callback is not None:
            await callback.on_folder_fail(folder, exc)

        raise

    if callback is not None:
        await callback.on_folder_complete(folder)


async def _donwload_file(  # noqa: PLR0913
    file: File,
    path: anyio.Path,
    *,
    force: bool,
    session: aiohttp.ClientSession,
    limiter: anyio.CapacityLimiter | None,
    callback: FileDownloadCallback | None,
) -> None:
    if await path.exists() and not force:
        if callback is not None:
            await callback.on_file_skip(file, path)

        return

    await path.unlink(missing_ok=True)
    if limiter is not None:
        async with limiter:
            await download(file, path, session=session, callback=callback)
    else:
        await download(file, path, session=session, callback=callback)
