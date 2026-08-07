"""Android entry point for the local ArtFinder web application.

python-for-android's WebView bootstrap opens ``http://127.0.0.1:5000`` while
this module runs the same FastAPI application used on desktop. No remote
ArtFinder server is required and credentials remain on the device.
"""

from __future__ import annotations

import os
from pathlib import Path


MOBILE_PORT = 5000


def prepare_mobile_environment(home: str | Path | None = None) -> Path:
    """Configure a writable private data directory before importing the app."""
    base = Path(home or os.getenv("HOME") or Path.cwd()).expanduser().resolve()
    data_dir = base / "artfinder"
    os.environ.setdefault("ARTFINDER_DATA_DIR", str(data_dir))
    os.environ.setdefault("ARTFINDER_MOBILE", "1")
    return Path(os.environ["ARTFINDER_DATA_DIR"])


def main() -> None:
    prepare_mobile_environment()

    import uvicorn

    # Import only after ARTFINDER_DATA_DIR is set: config.py creates its data
    # directories during import and Android's packaged source is read-only.
    from app import app

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=MOBILE_PORT,
        log_level="warning",
        access_log=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
