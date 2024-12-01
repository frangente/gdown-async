# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
)


def is_url(url: str) -> bool:
    """Check if the string is a URL."""
    return url.startswith(("http://", "https://"))
