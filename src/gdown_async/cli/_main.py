# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import argparse

import anyio

from gdown_async import __version__, download_file, download_folder, fetch_folder

from ._callbacks import ProgressFileDownloadCallback, TreeFolderDownloadCallback


def get_parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the CLI."""
    parser = argparse.ArgumentParser(description="Download files from Google Drive.")
    version = f"%(prog)s {__version__}"
    parser.add_argument("-v", "--version", action="version", version=version)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="The ID or URL of the file to download.")
    group.add_argument("--folder", help="The ID or URL of the folder to download.")

    # optional arguments
    parser.add_argument(
        "-o",
        "--output-dir",
        help="The directory where to save the file or folder.",
        default=".",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help="Suppress output.",
        action="store_true",
    )
    parser.add_argument(
        "-f",
        "--force",
        help="Overwrite existing files.",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--max-concurrency",
        help="The maximum number of concurrent downloads. "
        "This is only used for folder downloads.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-d",
        "--depth",
        help="Up to how many levels to download.",
        type=int,
        default=None,
    )

    return parser


def main() -> None:
    """Main entry point for the CLI."""
    parser = get_parser()
    args = parser.parse_args()
    anyio.run(_download, args)


# --------------------------------------------------------------------------- #
# Private functions
# --------------------------------------------------------------------------- #


async def _download(args: argparse.Namespace) -> None:
    if args.file:
        await download_file(
            args.file,
            output_dir=args.output_dir,
            force=args.force,
            callback=ProgressFileDownloadCallback() if not args.quiet else None,
        )
    else:
        if args.depth is not None:
            folder = await fetch_folder(args.folder, depth=args.depth)
        else:
            folder = await fetch_folder(args.folder)

        await download_folder(
            folder,
            output_dir=args.output_dir,
            force=args.force,
            max_concurrency=args.max_concurrency,
            callback=TreeFolderDownloadCallback() if not args.quiet else None,
        )
