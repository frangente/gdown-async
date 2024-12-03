# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import dataclasses
import os
import urllib.parse
from typing import Protocol, cast

import aiohttp
import anyio
import bs4

from ._utils import USER_AGENT, is_url

# --------------------------------------------------------------------------- #
# Public classes
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class File:
    """A Google Drive file."""

    id: str
    name: str


class FileDownloadCallback(Protocol):
    """A callback protocol for the download of a Google Drive file.

    This callback protocol provides hooks for various stages of the download of a
    Google Drive file. By default, all methods are no-op, but you can override them
    to provide custom behavior, e.g. for logging or displaying progress.
    """

    async def on_file_setup(self, file: File, path: anyio.Path) -> None:
        """Called when all the setup is done before starting the download.

        Note:
            This method is not called if the file already exists and the download is
            skipped. In that case, [on_skip][gdown_async.FileDownloadCallback.on_skip]
            is called instead.

        Args:
            file: The Google Drive file.
            path: The path where the file will be saved.
        """

    async def on_file_start(self, file: File, total: int) -> None:
        """Called immediately before starting the download of the file.

        This is called after [on_setup][gdown_async.FileDownloadCallback.on_setup] and
        before the download of the file starts from scratch. If the download is resumed,
        [on_resume][gdown_async.FileDownloadCallback.on_resume] is called instead.

        Args:
            file: The Google Drive file.
            total: The total number of bytes to download.
        """

    async def on_file_resume(self, file: File, downloaded: int, total: int) -> None:
        """Called immediately before resuming the download of the file.

        This is called after [on_setup][gdown_async.FileDownloadCallback.on_setup] and
        before the download of the file resumes from a previous download. If the
        download is started from scratch,
        [on_start][gdown_async.FileDownloadCallback.on_start] is called instead.

        Args:
            file: The Google Drive file.
            downloaded: The number of bytes already downloaded.
            total: The total number of bytes to download.
        """

    async def on_file_progress(self, file: File, downloaded: int, total: int) -> None:
        """Called during the download of the file.

        This method is called after each chunk of data is downloaded. If the file is
        small, this method may be called only once (so `downloaded` will be equal to
        `total`), otherwise it will be called multiple times.

        Args:
            file: The Google Drive file.
            downloaded: The number of bytes already downloaded.
            total: The total number of bytes to download.
        """

    async def on_file_complete(self, file: File, total: int) -> None:
        """Called when the download of the file completes.

        This is called after the download of the file completes successfully.

        Args:
            file: The Google Drive file.
            total: The total number of bytes downloaded. This is equal to the total
                number of bytes to download.
        """

    async def on_file_cleanup(self, file: File, *, success: bool) -> None:
        """Called after the download of the file completes or fails.

        This method is called after the download of the file completes successfully or
        fails. This is the last method called in the lifecycle of the download.

        Note:
            This method is not called if the download is skipped.

        Args:
            file: The Google Drive file.
            success: If `True`, the download completed successfully,
                otherwise it failed.
        """

    async def on_file_fail(self, file: File, exc: BaseException) -> None:
        """Called when the download of the file fails.

        Args:
            file: The Google Drive file.
            exc: The exception that caused the download to fail.
        """

    async def on_file_skip(self, file: File, path: anyio.Path) -> None:
        """Called when the download of the file is skipped.

        Args:
            file: The Google Drive file.
            path: The path where the file would have been saved.
        """


# --------------------------------------------------------------------------- #
# Public functions
# --------------------------------------------------------------------------- #


def extract_file_id(url: str) -> str:
    """Extracts the file ID from a Google Drive URL.

    The Google Drive URL must have one of the following formats:
    - `https://drive.google.com/file/d/<file_id>/...`
    - `https://drive.google.com/uc?id=<file_id>`

    Args:
        url: The Google Drive URL.

    Returns:
        The file ID if found, `None` otherwise.

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
        session.headers["User-Agent"] = USER_AGENT
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


async def download_file(
    x: File | str,
    /,
    *,
    output_dir: os.PathLike[str] | str = ".",
    force: bool = False,
    callback: FileDownloadCallback | None = None,
) -> None:
    """Downloads a file from Google Drive.

    Args:
        x: Either the ID of the Google Drive file, the URL of the file or the
            [File][gdown_async.File] instance.
        output_dir: The output directory. If you passed the ID or URL of the file,
            it will be saved in this directory with the name provided by Google Drive,
            otherwise it will be saved with the name provided by the
            [File][gdown_async.File] instance.
        force: If `True`, the file will be downloaded even if it already exists. If
            `False` and a file with the same name already exists, the download will be
            skipped (no check is performed on the content of the file).
        callback: A callback to use for the download of the file.

    Raises:
        NotADirectoryError: If the output path already exists and is not a directory.
        IsADirectoryError: If the output path already exists and is a not a file.
        ValueError: If the file URL is invalid.
    """
    if isinstance(x, str):
        id_ = extract_file_id(x) if is_url(x) else x
        file = await retrieve_file(id_)
    else:
        file = x

    path = anyio.Path(output_dir) / file.name
    await check_file_path(path)

    if await path.exists() and not force:
        if callback is not None:
            await callback.on_file_skip(file, path)
        return

    await path.unlink(missing_ok=True)
    async with aiohttp.ClientSession() as session:
        session.headers["User-Agent"] = USER_AGENT
        await download(file, path, session=session, callback=callback)


# --------------------------------------------------------------------------- #
# Functions for internal use
# --------------------------------------------------------------------------- #


async def download(  # noqa: C901, PLR0912, PLR0915
    file: File,
    path: anyio.Path,
    *,
    session: aiohttp.ClientSession,
    callback: FileDownloadCallback | None = None,
) -> None:
    """Downloads a Google Drive file.

    Args:
        file: The Google Drive file.
        path: The path where the file will be saved. This must be a file path,
            not a directory path (no check is performed to ensure this).
        session: The aiohttp client session.
        callback: A callback to use for the download of the file.
    """
    response, success = None, False
    try:
        if callback is not None:
            await callback.on_file_setup(file, path)

        await path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.parent / f"{path.name}.gdown"
        await tmp_path.touch()

        params = {"id": file.id, "export": "download"}
        response = await session.get("https://drive.google.com/uc", params=params)
        if response.status != 200:
            await tmp_path.unlink()
            msg = f"Failed to download file with ID '{file.id}'."
            raise RuntimeError(msg)

        if response.headers["Content-Type"].startswith("text/html"):
            # we received the HTML page that asks the user to confirm the download
            soup = bs4.BeautifulSoup(await response.text(), "html.parser")
            response.close()

            form = soup.find("form")
            if form is None or not isinstance(form, bs4.Tag):
                await tmp_path.unlink()
                msg = f"Failed to download file with ID '{file.id}'."
                raise RuntimeError(msg)

            params = {
                input_["name"]: input_["value"]
                for input_ in form.find_all("input")
                if input_.get("name") is not None
            }

            downloaded = (await tmp_path.stat()).st_size
            if downloaded > 0:
                # set the `Range` header to resume the download
                headers = {"Range": f"bytes={downloaded}-", "User-Agent": USER_AGENT}
            else:
                headers = {"User-Agent": USER_AGENT}

            url = cast(str, form["action"])
            response = await session.get(url, params=params, headers=headers)
        else:
            downloaded = 0

        total = int(response.headers["Content-Length"]) + downloaded
        if callback is not None:
            if downloaded == 0:
                await callback.on_file_start(file, total)
            else:
                await callback.on_file_resume(file, downloaded, total)

        async with await anyio.open_file(tmp_path, "ab") as f:
            async for chunk in response.content.iter_any():
                await f.write(chunk)
                downloaded += len(chunk)

                if callback is not None:
                    await callback.on_file_progress(file, downloaded, total)

        await tmp_path.rename(path)
        if callback is not None:
            await callback.on_file_complete(file, total)
        success = True
    except BaseException as exc:
        if callback is not None:
            await callback.on_file_fail(file, exc)
        raise
    finally:
        if response is not None and not response.closed:
            response.close()

        if callback is not None:
            await callback.on_file_cleanup(file, success=success)


async def check_file_path(path: anyio.Path) -> None:
    """Checks that the provided path is valid for a file."""
    if await path.exists():
        if not await path.is_file():
            msg = f"Output path '{path}' is not a file."
            raise IsADirectoryError(msg)

        return

    # to verify that the provided path is valid, we try to create it and then delete it
    await path.parent.mkdir(parents=True, exist_ok=True)
    await path.touch()
    await path.unlink()
