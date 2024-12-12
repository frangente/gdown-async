# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

"""Asynchronous Google Drive file downloader."""

from ._callbacks import FileDownloadCallback, FolderDownloadCallback
from ._download import download_file, download_folder
from ._fetch import retrieve_file, retrieve_folder
from ._records import File, Folder
from ._url import extract_file_id, extract_folder_id, is_url

__version__ = "0.0.1"

__all__ = [
    "File",
    "FileDownloadCallback",
    "Folder",
    "FolderDownloadCallback",
    "download_file",
    "download_folder",
    "extract_file_id",
    "extract_folder_id",
    "is_url",
    "retrieve_file",
    "retrieve_folder",
]
