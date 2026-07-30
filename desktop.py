"""Native desktop launcher for ArtFinder.

FastAPI remains the application core, but it is bound to a random loopback
port and displayed inside a native pywebview window.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import socket
import sys
import threading
import time
from pathlib import Path


def _migrate_env_if_needed(data_dir: Path, executable_dir: Path) -> Path | None:
    """Copy a nearby legacy .env into the desktop data directory once."""
    target = data_dir / ".env"
    if target.exists():
        return None

    candidates = (
        executable_dir / ".env",
        executable_dir.parent / ".env",
    )
    for candidate in candidates:
        if candidate.is_file() and candidate.resolve() != target.resolve():
            data_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, target)
            return candidate
    return None


def _bootstrap_desktop_data() -> None:
    """Prepare writable desktop configuration before config.py is imported."""
    if not getattr(sys, "frozen", False):
        return
    local_app_data = os.getenv("LOCALAPPDATA")
    data_dir = (
        Path(local_app_data) / "ArtFinder"
        if local_app_data
        else Path.home() / ".artfinder"
    )
    _migrate_env_if_needed(data_dir, Path(sys.executable).resolve().parent)


_bootstrap_desktop_data()

import uvicorn

from app import app
from config import DATA_DIR, DOWNLOAD_DIR, RESOURCE_DIR


def _show_fatal_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, message, "ArtFinder", 0x10)
    except Exception:
        print(message)


class DesktopApi:
    """Small set of safe native actions callable by the web interface."""

    def open_downloads_folder(self) -> bool:
        folder = Path(DOWNLOAD_DIR)
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)  # type: ignore[attr-defined]
        return True

    def open_data_folder(self) -> bool:
        folder = Path(DATA_DIR)
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)  # type: ignore[attr-defined]
        return True


def _create_server() -> tuple[uvicorn.Server, socket.socket, str]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        server_header=False,
    )
    return uvicorn.Server(config), listener, f"http://127.0.0.1:{port}"


def main() -> int:
    try:
        import webview
    except ImportError:
        _show_fatal_error(
            "A interface desktop nao esta instalada.\n\n"
            "Execute: python -m pip install -r requirements-desktop.txt"
        )
        return 1

    server, listener, url = _create_server()
    server_error: list[BaseException] = []

    def run_server() -> None:
        try:
            server.run(sockets=[listener])
        except BaseException as exc:
            server_error.append(exc)

    server_thread = threading.Thread(
        target=run_server,
        name="artfinder-server",
        daemon=True,
    )
    server_thread.start()

    deadline = time.monotonic() + 15
    while not server.started and server_thread.is_alive():
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    if not server.started:
        server.should_exit = True
        listener.close()
        detail = f"\n\nDetalhes: {server_error[0]}" if server_error else ""
        _show_fatal_error("Nao foi possivel iniciar o ArtFinder." + detail)
        return 1

    webview.create_window(
        "ArtFinder",
        url=url,
        js_api=DesktopApi(),
        width=1440,
        height=900,
        min_size=(1024, 700),
        confirm_close=True,
    )
    exit_code = 0
    try:
        webview.start(
            debug=os.getenv("ARTFINDER_DEBUG", "").strip() == "1",
            private_mode=False,
            storage_path=str(Path(DATA_DIR) / "webview"),
            icon=str(Path(RESOURCE_DIR) / "assets" / "artfinder.ico"),
        )
    except Exception as exc:
        exit_code = 1
        _show_fatal_error(f"A janela do ArtFinder encontrou um erro.\n\n{exc}")
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)
        try:
            listener.close()
        except OSError:
            pass

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
