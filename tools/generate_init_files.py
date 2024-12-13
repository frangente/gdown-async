# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import importlib.metadata
import subprocess
from pathlib import Path
from typing import cast

import griffe

PACKAGE = "gdown_async"
PRIVATE_MODULES = {f"{PACKAGE}._utils"}


def should_export(member: griffe.Object | griffe.Alias, module: griffe.Module) -> bool:
    """Determines if a member should be exported in the __init__.py file."""
    if not member.is_public:
        return False

    # verify that the member has been defined in the module or in a sub-module
    return member.canonical_path.startswith(module.canonical_path)


def create_exports(module: griffe.Module) -> None:
    """Creates the __init__.py file for the given module."""
    for submodule in module.modules.values():
        create_exports(submodule)

    if not module.is_public:
        return

    exports: dict[str, list[str]] = {}
    __all__: set[str] = set()
    for subname, submodule in module.modules.items():
        if submodule.canonical_path in PRIVATE_MODULES or submodule.is_public:
            continue

        exports[subname] = [
            n for n, m in submodule.members.items() if should_export(m, submodule)
        ]
        __all__.update(exports[subname])

    file = cast(Path, module.filepath)
    lines: list[str] = []
    with file.open("r") as f:
        for line in f:
            if line.startswith(("from", "import", "__all__")):
                break

            lines.append(line)

    with file.open("w") as f:
        # write the original content of the file
        f.writelines(lines)

        # write from ._sub import *
        for name, members in exports.items():
            if not members:
                continue
            f.write(f"from .{name} import {', '.join(members)}\n")

        # write __all__ at the end of the file
        f.write(f"\n__all__ = {sorted(__all__)}\n")


def write_version(module: griffe.Module) -> None:
    """Writes the version in the _version.py file."""
    version = importlib.metadata.version(PACKAGE)
    file = module.filepath
    if isinstance(file, list):
        msg = "Multiple files found for the module."
        raise RuntimeError(msg)  # noqa: TRY004

    # find a __version__ line and replace it
    lines: list[str] = []
    found = False
    with file.open("r") as f:
        for line in f:
            if line.startswith("__version__"):
                line = f'__version__ = "{version}"\n'  # noqa: PLW2901
                found = True
            lines.append(line)

    if not found:
        lines.append("\n")
        lines.append(f"__version__ = '{version}'\n")

    with file.open("w") as f:
        f.writelines(lines)


def main() -> None:
    """Main entry point of the script."""
    module = cast(griffe.Module, griffe.load(PACKAGE))
    write_version(module.modules["_version"])
    create_exports(module)

    subprocess.run(["ruff", "format", "src", "-q"], check=True)  # noqa: S603, S607
    subprocess.run(["ruff", "check", "src", "-e", "-s"], check=True)  # noqa: S603, S607


if __name__ == "__main__":
    main()
