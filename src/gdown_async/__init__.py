# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

"""Asynchronous Google Drive file downloader."""

from ._callbacks import FileDownloadCallback, FolderDownloadCallback
from ._download import download_file, download_folder
from ._fetch import fetch_file, fetch_folder
from ._records import File, Folder
from ._version import __version__

__all__ = [
    "File",
    "FileDownloadCallback",
    "Folder",
    "FolderDownloadCallback",
    "__version__",
    "download_file",
    "download_folder",
    "fetch_file",
    "fetch_folder",
]
