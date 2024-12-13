# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

"""Asynchronous Google Drive file downloader."""

from ._callbacks import FileDownloadCallback, FolderDownloadCallback
from ._download import download_file, download_folder
from ._fetch import fetch_file, fetch_folder
from ._records import File, Folder
from ._url import extract_file_id, extract_folder_id, is_url
from ._version import __version__

__all__ = [
    "File",
    "FileDownloadCallback",
    "Folder",
    "FolderDownloadCallback",
    "__version__",
    "download_file",
    "download_folder",
    "extract_file_id",
    "extract_folder_id",
    "fetch_file",
    "fetch_folder",
    "is_url",
]
