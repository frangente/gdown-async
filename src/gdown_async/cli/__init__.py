# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

"""Command line interface for gdown-async."""

from ._main import get_parser, main
from ._callbacks import ProgressFileDownloadCallback, TreeFolderDownloadCallback

__all__ = ['ProgressFileDownloadCallback', 'TreeFolderDownloadCallback', 'get_parser', 'main']
