# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import urllib.parse


def is_url(url: str) -> bool:
    """Checks if the string is a URL."""
    return url.startswith(("http://", "https://"))


def extract_file_id(url: str) -> str:
    """Extracts the file ID from a Google Drive URL.

    The Google Drive URL must have one of the following formats:
    - `https://drive.google.com/file/d/<file_id>/...`
    - `https://drive.google.com/uc?id=<file_id>`

    Args:
        url: The Google Drive URL.

    Returns:
        The file ID extracted from the URL.

    Raises:
        ValueError: If the URL is invalid.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "drive.google.com":
        msg = f"Invalid Google Drive file URL '{url}'."
        raise ValueError(msg)

    parts = parsed.path.split("/")
    if len(parts) >= 4 and parts[1] == "file" and parts[2] == "d":
        return parts[3]

    query = urllib.parse.parse_qs(parsed.query)
    if "id" in query and len(query["id"]) == 1:
        return query["id"][0]

    msg = f"Invalid Google Drive file URL '{url}'."
    raise ValueError(msg)


def extract_folder_id(url: str) -> str:
    """Extracts the folder ID from a Google Drive URL.

    The Google Drive URL must have the following format:
    `https://drive.google.com/drive/folders/<folder_id>`

    Args:
        url: The Google Drive URL.

    Returns:
        The folder ID extracted from the URL.

    Raises:
        ValueError: If the URL is invalid.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "drive.google.com":
        msg = f"Invalid Google Drive folder URL '{url}'."
        raise ValueError(msg)

    parts = parsed.path.split("/")
    if len(parts) != 4 or parts[1] != "drive" or parts[2] != "folders":
        msg = f"Invalid Google Drive folder URL '{url}'."
        raise ValueError(msg)

    if not parts[3]:
        msg = f"Invalid Google Drive folder URL '{url}'."
        raise ValueError(msg)

    return parts[3]
