# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: MIT

import anyio
import rich
from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.tree import Tree
from typing_extensions import override

from gdown_async import File, FileDownloadCallback, Folder, FolderDownloadCallback

# --------------------------------------------------------------------------- #
# File
# --------------------------------------------------------------------------- #


class ProgressFileDownloadCallback(FileDownloadCallback):
    """A callback that displays the file download progress using a progress bar."""

    def __init__(
        self,
        *,
        console: Console | None = None,
        transient: bool = True,
    ) -> None:
        """Initializes the callback with a console.

        Args:
            console: The console to use for output. If `None`, a new console is created
                using [get_console()][rich.get_console].
            transient: If `True`, the progress bar is removed after the download is
                complete. If `False`, the progress bar remains visible.
        """
        self.console = console or rich.get_console()
        self.transient = transient
        self.progress = None
        self.task_id = None

    @override
    async def on_file_setup(self, file: File, path: anyio.Path) -> None:
        self.console.print(f"[cyan]Downloading[/] '{file.name}' to '{path}'")
        self.progress = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(),
            DownloadColumn(),
            TextColumn("["),
            TimeElapsedColumn(),
            TextColumn("<"),
            TimeRemainingColumn(),
            TextColumn(","),
            TransferSpeedColumn(),
            TextColumn("]"),
            console=self.console,
            transient=self.transient,
        )
        self.progress.start()
        self.task_id = self.progress.add_task("[cyan]Downloading[/]", total=None)

    @override
    async def on_file_start(self, file: File, total: int) -> None:
        if self.progress is None or self.task_id is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        self.progress.start_task(self.task_id)
        self.progress.update(self.task_id, total=total)

    @override
    async def on_file_resume(self, file: File, downloaded: int, total: int) -> None:
        if self.progress is None or self.task_id is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        self.progress.start_task(self.task_id)
        self.progress.update(self.task_id, completed=downloaded, total=total)

    @override
    async def on_file_progress(self, file: File, downloaded: int, total: int) -> None:
        if self.progress is None or self.task_id is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        self.progress.update(self.task_id, completed=downloaded)

    @override
    async def on_file_complete(self, file: File, total: int) -> None:
        if self.progress is None or self.task_id is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        self.progress.update(self.task_id, completed=total)
        self.console.print("[green]Download complete[/]")

    @override
    async def on_file_skip(self, file: File, path: anyio.Path) -> None:
        self.console.print(f"[yellow]Skipping[/] '{file.name}'")

    @override
    async def on_file_fail(self, file: File, exc: BaseException) -> None:
        self.console.print("[red]Download failed[/]")

    @override
    async def on_file_cleanup(self, file: File, *, success: bool) -> None:
        if self.progress is not None:
            self.progress.stop()


# --------------------------------------------------------------------------- #
# Folder
# --------------------------------------------------------------------------- #


class TreeFolderDownloadCallback(FolderDownloadCallback):
    """A callback that displays the folder download progress using a tree view."""

    def __init__(self, console: Console | None = None) -> None:
        """Initializes the callback with a console.

        Args:
            console: The console to use for output. If `None`, a new console is created
                using [get_console()][rich.get_console].
        """
        self.console = console or rich.get_console()
        self.nodes: dict[str, Tree] | None = None
        self.live: Live | None = None

    @override
    async def on_folder_setup(self, folder: Folder, path: anyio.Path) -> None:
        self.console.print(f"[cyan]Downloading[/] '{folder.name}' to '{path}'")
        tree, nodes = _get_tree(folder)

        self.nodes = nodes
        self.live = Live(tree, console=self.console, transient=True)
        self.live.start()

    @override
    async def on_folder_start(self, folder: Folder) -> None:
        if self.live is None or self.nodes is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        tree = self.nodes[folder.id]
        tree.label = f"📁 {folder.name} 🔄 [Downloading]"

    @override
    async def on_file_setup(self, file: File, path: anyio.Path) -> None:
        if self.live is None or self.nodes is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        tree = self.nodes[file.id]
        tree.label = f"📄 {file.name} 🔄 [Downloading]"

    @override
    async def on_file_start(self, file: File, total: int) -> None:
        if self.live is None or self.nodes is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        tree = self.nodes[file.id]
        tree.label = f"📄 {file.name} 🔄 [0%]"

    @override
    async def on_file_resume(self, file: File, downloaded: int, total: int) -> None:
        if self.live is None or self.nodes is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        tree = self.nodes[file.id]
        tree.label = f"📄 {file.name} 🔄 [{downloaded / total:.0%}]"

    @override
    async def on_file_progress(self, file: File, downloaded: int, total: int) -> None:
        if self.live is None or self.nodes is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        tree = self.nodes[file.id]
        tree.label = f"📄 {file.name} 🔄 [{downloaded / total:.0%}]"

    @override
    async def on_file_complete(self, file: File, total: int) -> None:
        if self.live is None or self.nodes is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        tree = self.nodes[file.id]
        tree.label = f"📄 {file.name} ✅ [Downloaded]"

    @override
    async def on_file_skip(self, file: File, path: anyio.Path) -> None:
        if self.live is None or self.nodes is None:
            return

        tree = self.nodes[file.id]
        tree.label = f"📄 {file.name} ⏭️ [Skipped]"

    @override
    async def on_file_fail(self, file: File, exc: BaseException) -> None:
        if self.live is None or self.nodes is None:
            return

        tree = self.nodes[file.id]
        tree.label = f"📄 {file.name} ❌"

    @override
    async def on_folder_complete(self, folder: Folder) -> None:
        if self.live is None or self.nodes is None:
            msg = "Callback not initialized."
            raise RuntimeError(msg)

        tree = self.nodes[folder.id]
        tree.label = f"📁 {folder.name} ✅ [Downloaded]"

    @override
    async def on_folder_fail(self, folder: Folder, exc: BaseException) -> None:
        if self.live is None or self.nodes is None:
            return

        tree = self.nodes[folder.id]
        tree.label = f"📁 {folder.name} ❌ [Failed]"

    @override
    async def on_folder_cleanup(self, folder: Folder, *, success: bool) -> None:
        if self.live is not None:
            self.live.stop()

        if success:
            self.console.print("[green]Download complete[/]")
        else:
            self.console.print("[red]Download failed[/]")


def _get_tree(folder: Folder) -> tuple[Tree, dict[str, Tree]]:
    """Builds a [Tree][rich.tree.Tree] from a folder structure."""
    tree = Tree(f"📁 {folder.name}")
    nodes: dict[str, Tree] = {folder.id: tree}
    for item in folder:
        if isinstance(item, File):
            node = tree.add(f"📄 {item.name}")
            nodes[item.id] = node
        else:
            sub_dir, sub_nodes = _get_tree(item)
            tree.add(sub_dir)
            nodes.update(sub_nodes)

    return tree, nodes
