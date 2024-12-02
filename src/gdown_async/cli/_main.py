# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import argparse
import functools
import sys

import anyio
import rich

from gdown_async import (
    __version__,
    download_file,
    download_folder,
    extract_file_id,
    extract_folder_id,
)

from ._callbacks import ProgressFileDownloadCallback, TreeFolderDownloadCallback


def get_parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the CLI."""
    parser = argparse.ArgumentParser(description="Download files from Google Drive.")
    version = f"%(prog)s {__version__}"
    parser.add_argument("-v", "--version", action="version", version=version)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file-id", help="The ID of a Google Drive file.")
    group.add_argument("--folder-id", help="The ID of a Google Drive folder.")
    group.add_argument("--url", help="The URL of a Google Drive file/folder.")

    # optional arguments
    parser.add_argument("--output-dir", help="The output directory.", default=".")
    parser.add_argument("-q", "--quiet", help="Suppress output.", action="store_true")
    parser.add_argument("-f", "--force", help="Force download.", action="store_true")
    parser.add_argument(
        "--max-concurrency",
        help="The maximum number of concurrent downloads. "
        "This is only used for folder downloads.",
        type=int,
        default=None,
    )

    return parser


def main() -> None:
    """Main entry point for the CLI."""
    parser = get_parser()
    args = parser.parse_args()

    if args.file_id:
        id_, fn = args.file_id, download_file
        callback = ProgressFileDownloadCallback() if not args.quiet else None
    elif args.folder_id:
        id_ = args.folder_id
        fn = functools.partial(download_folder, max_concurrency=args.max_concurrency)
        callback = TreeFolderDownloadCallback() if not args.quiet else None
    else:
        try:
            id_, fn = extract_file_id(args.url), download_file
            callback = ProgressFileDownloadCallback() if not args.quiet else None
        except ValueError:
            try:
                id_ = extract_folder_id(args.url)
                fn = functools.partial(
                    download_folder, max_concurrency=args.max_concurrency
                )
                callback = TreeFolderDownloadCallback() if not args.quiet else None
            except ValueError:
                rich.print("[red]Invalid URL.[/red]")
                sys.exit(1)

    fn = functools.partial(
        fn,
        id_,
        output_dir=args.output_dir,
        force=args.force,
        callback=callback,
    )
    anyio.run(fn)
