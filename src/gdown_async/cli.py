# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

"""Command line interface for gdown-async."""

import argparse
import functools
import sys

import anyio

from gdown_async import __version__

from ._file import download_file, extract_file_id
from ._folder import download_folder, extract_folder_id


def main() -> None:
    """Main entry point for the CLI."""
    parser = get_parser()
    args = parser.parse_args()

    if args.file_id:
        id_, fn = args.file_id, download_file
    elif args.folder_id:
        id_, fn = args.folder_id, download_folder
    elif args.url:
        try:
            id_, fn = extract_file_id(args.url), download_file
        except ValueError:
            try:
                id_, fn = extract_folder_id(args.url), download_folder
            except ValueError:
                sys.exit("Invalid URL.")
    else:
        # this will never happen, it is just to make basedpyright happy
        sys.exit("Invalid arguments.")

    fn = functools.partial(
        fn, id_, output_dir=args.output, force=args.force, quiet=args.quiet
    )
    anyio.run(fn)


def get_parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the CLI."""
    parser = argparse.ArgumentParser(description="Download files from Google Drive.")
    version = f"%(prog)s {__version__}"
    parser.add_argument("-v", "--version", action="version", version=version)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file-id", help="The ID of a Google Drive file.")
    group.add_argument("--folder-id", help="The ID of a Google Drive folder.")
    group.add_argument("--url", help="The URL of a Google Drive file/folder.")

    parser.add_argument("--output", help="The output directory.", default=".")
    parser.add_argument("--quiet", help="Suppress output.", action="store_true")
    parser.add_argument("--force", help="Force download.", action="store_true")

    return parser
