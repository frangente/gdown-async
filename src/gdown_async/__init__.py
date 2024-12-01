# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

"""Asynchronous Google Drive file downloader."""

from ._file import (
    File,
    FileDownloadCallback,
    download_file,
    extract_file_id,
    retrieve_file,
)
from ._folder import (
    Folder,
    FolderDownloadCallback,
    download_folder,
    extract_folder_id,
    find_subfolder_id,
    retrieve_folder,
)

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
    "find_subfolder_id",
    "retrieve_file",
    "retrieve_folder",
]
