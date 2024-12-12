# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

from typing import Protocol

import anyio

from ._records import File, Folder

# --------------------------------------------------------------------------- #
# FileDownloadCallback
# --------------------------------------------------------------------------- #


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
# FolderDownloadCallback
# --------------------------------------------------------------------------- #


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
