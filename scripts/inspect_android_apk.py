"""Fail a build when an ArtFinder APK leaks local data or misses its bootstrap."""

from __future__ import annotations

import argparse
import io
import json
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


PRIVATE_TAR = "assets/private.tar"
FORBIDDEN_NAMES = {
    ".env",
    "user_categories.json",
    "artfinder.db",
    "dump.json",
}
REQUIRED_APP_MODULES = {
    "app": {"app.py", "app.pyc"},
    "main": {"main.py", "main.pyc"},
    "mobile": {"mobile.py", "mobile.pyc"},
}


def inspect_apk(apk_path: Path) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(apk_path) as apk:
        apk_names = set(apk.namelist())
        if PRIVATE_TAR not in apk_names:
            return [f"missing {PRIVATE_TAR}"]

        arches = {
            PurePosixPath(name).parts[1]
            for name in apk_names
            if name.startswith("lib/") and len(PurePosixPath(name).parts) >= 3
        }
        if arches != {"arm64-v8a"}:
            errors.append(f"unexpected native architectures: {sorted(arches)}")

        private_bytes = apk.read(PRIVATE_TAR)

    with tarfile.open(fileobj=io.BytesIO(private_bytes)) as private:
        members = {member.name.lstrip("./"): member for member in private.getmembers()}
        basenames = {PurePosixPath(name).name for name in members}
        leaked = sorted(FORBIDDEN_NAMES & basenames)
        if leaked:
            errors.append(f"private archive contains local data: {', '.join(leaked)}")

        # python-for-android compiles application modules to .pyc, while the
        # synthetic test package and some older recipes may retain .py files.
        missing = sorted(
            module
            for module, candidates in REQUIRED_APP_MODULES.items()
            if not (candidates & members.keys())
        )
        if missing:
            errors.append(f"private archive misses app modules: {', '.join(missing)}")

        defaults_name = "defaults/categories.json"
        defaults_member = members.get(defaults_name)
        if defaults_member is None:
            errors.append(f"private archive misses {defaults_name}")
        else:
            extracted = private.extractfile(defaults_member)
            try:
                payload = json.loads(extracted.read().decode("utf-8") if extracted else "")
            except (UnicodeDecodeError, json.JSONDecodeError):
                errors.append("default categories are not valid UTF-8 JSON")
            else:
                if payload != {"categories": {}}:
                    errors.append("default categories are not empty")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    args = parser.parse_args()
    errors = inspect_apk(args.apk)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"APK inspection passed: {args.apk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
