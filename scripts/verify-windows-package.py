"""Check the local candidate without launching it or reading user credentials."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from PyInstaller.archive.readers import CArchiveReader


def verify(executable: Path, root: Path) -> dict:
    archive = CArchiveReader(str(executable))
    entries = {name.replace("\\", "/"): name for name in archive.toc}
    forbidden = []
    for name in entries:
        path = PurePosixPath(name)
        if (
            path.name == ".env"
            or path.name.startswith(".env.")
            or path.name.startswith("user_categories")
            or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".jks", ".keystore"}
            or any(part in {"downloads", ".git", "cookies"} for part in path.parts)
        ):
            forbidden.append(name)
    if forbidden:
        raise ValueError("Unexpected personal-data paths in package: " + ", ".join(forbidden))

    if any("qtwebengine" in name.lower() or "webview2" in name.lower() for name in entries):
        raise ValueError("Native desktop package unexpectedly contains a browser engine")
    if any(PurePosixPath(name).name.lower() in {"icu.dll", "icuuc.dll", "icuin.dll"} for name in entries):
        raise ValueError("Package shadows the Windows ICU runtime required by Qt")
    pyz_name = next((name for name in archive.toc if name.endswith(".pyz")), None)
    if not pyz_name:
        raise ValueError("Missing Python module archive")
    modules = archive.open_embedded_archive(pyz_name).toc
    for module in ["artfinder.native.window", "artfinder.native.widgets", "artfinder.native.client",
                   "artfinder.native.themes", "artfinder.native.studio", "artfinder.native.appearance", "artfinder.native.inspector"]:
        if module not in modules:
            raise ValueError(f"Missing native desktop module: {module}")
    if not any(name.endswith("Qt6Widgets.dll") for name in entries):
        raise ValueError("Missing native Qt Widgets runtime")

    if "assets/discovery-welcome.png" in entries:
        raise ValueError("Package contains the rejected AI-generated welcome illustration")

    resources = [
        "templates/index.html", "templates/viewer.css", "templates/viewer.js",
        "templates/i18n.js", "defaults/categories.json",
        "assets/fonts/Archivo.ttf", "assets/fonts/SourceSans3.ttf",
        "assets/fonts/Archivo-OFL.txt", "assets/fonts/SourceSans3-OFL.txt",
    ]
    for name in resources:
        if name not in entries:
            raise ValueError(f"Missing packaged resource: {name}")
        if archive.extract(entries[name]) != (root / name).read_bytes():
            raise ValueError(f"Stale packaged resource: {name}")
    defaults = json.loads(archive.extract(entries["defaults/categories.json"]))
    if defaults != {"categories": {}}:
        raise ValueError("New installations must start with empty categories")
    with executable.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "executable": str(executable.resolve()),
        "sha256": digest,
        "size_bytes": executable.stat().st_size,
        "checked_resources": resources,
        "empty_categories": True,
        "forbidden_paths": 0,
        "native_qt": True,
        "embedded_browser": False,
        "limitations": "Path checks do not replace secret scanning or device testing.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, Path(__file__).resolve().parents[1]), indent=2))
