# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import dataclasses
from collections.abc import Iterator

from typing_extensions import Self


@dataclasses.dataclass
class File:
    """A Google Drive file."""

    id: str
    name: str


@dataclasses.dataclass
class Folder:
    """A Google Drive folder."""

    id: str
    name: str
    children: list[File | Self]

    def __iter__(self) -> Iterator[File | Self]:
        yield from self.children
