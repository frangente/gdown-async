# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import functools
import os
from typing import cast

import aiohttp
import anyio
import bs4

from ._callbacks import FileDownloadCallback, FolderDownloadCallback
from ._fetch import retrieve_file, retrieve_folder
from ._records import File, Folder
from ._url import extract_file_id, extract_folder_id, is_url
from ._utils import check_file_path, check_folder_path, init_session


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
        init_session(session)
        await _download_file(file, path, session=session, callback=callback)


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
        ValueError: If the maximum concurrency is less than 1.
        ValueError: If the folder URL is invalid.
        FileNotFoundError: If the folder does not exist.
        NotADirectoryError: If the location where the folder or any of its subfolders
            should be saved is not a directory.
        IsADirectoryError: If the location where a file should be saved is a directory.
    """
    if max_concurrency is not None and max_concurrency < 1:
        msg = f"Max concurrency must be greater than 0, got {max_concurrency}."
        raise ValueError(msg)

    if isinstance(x, str):
        id_ = extract_folder_id(x) if is_url(x) else x
        folder = await retrieve_folder(id_)
    else:
        folder = x

    success = False
    path = anyio.Path(output_dir) / folder.name
    await check_folder_path(folder, path)

    try:
        if callback is not None:
            await callback.on_folder_setup(folder, path)

        limiter = anyio.CapacityLimiter(max_concurrency) if max_concurrency else None
        async with aiohttp.ClientSession() as session:
            init_session(session)
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


async def _download_file(  # noqa: C901, PLR0912, PLR0915
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
            headers = session.headers.copy()
            if downloaded > 0:
                # set the `Range` header to resume the download
                headers["Range"] = f"bytes={downloaded}-"

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


async def _download_folder_file(  # noqa: PLR0913
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
            await _download_file(file, path, session=session, callback=callback)
    else:
        await _download_file(file, path, session=session, callback=callback)


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
                        _download_folder_file,
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
