"""Small cross-platform helpers shared by desktop builds.

This module intentionally depends only on the Python standard library so it
can be imported before the rest of the application is bootstrapped.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


APP_NAME = "ArtFinder"


def user_data_dir() -> Path:
    """Return the conventional writable data directory for this platform."""
    override = os.getenv("ARTFINDER_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA")
        return Path(base) / APP_NAME if base else Path.home() / ".artfinder"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME

    # Linux and other freedesktop-style systems.
    base = os.getenv("XDG_DATA_HOME")
    return Path(base) / "artfinder" if base else Path.home() / ".local" / "share" / "artfinder"


def open_folder(path: str | Path) -> bool:
    """Open *path* with the platform file manager."""
    folder = Path(path).resolve()
    folder.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        os.startfile(folder)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])
    return True


def window_icon(resource_dir: str | Path) -> Path:
    """Choose an icon format understood by the active desktop backend."""
    filename = "artfinder.ico" if sys.platform == "win32" else "artfinder-icon.png"
    return Path(resource_dir) / "assets" / filename
