"""Android entry point for the local ArtFinder web application.

python-for-android's WebView bootstrap opens ``http://127.0.0.1:5000`` while
this module runs the same FastAPI application used on desktop. No remote
ArtFinder server is required and credentials remain on the device.
"""

from __future__ import annotations

import html
import os
import sys
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable


MOBILE_PORT = 5000
MOBILE_LOG_NAME = "mobile-startup.log"


def prepare_mobile_environment(home: str | Path | None = None) -> Path:
    """Configure a writable private data directory before importing the app."""
    # python-for-android explicitly exposes the app's private files directory in
    # ANDROID_PRIVATE. HOME is not guaranteed to be configured by the WebView
    # bootstrap and cwd points at unpacked application resources.
    base = Path(
        home
        or os.getenv("ANDROID_PRIVATE")
        or os.getenv("HOME")
        or Path.cwd()
    ).expanduser().resolve()
    default_data_dir = base / "artfinder"
    os.environ.setdefault("ARTFINDER_DATA_DIR", str(default_data_dir))
    os.environ.setdefault("ARTFINDER_MOBILE", "1")
    data_dir = Path(os.environ["ARTFINDER_DATA_DIR"]).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _write_startup_log(data_dir: Path, status: str, detail: str = "") -> Path:
    """Append a bounded startup record in Android's private app storage."""
    log_path = data_dir / MOBILE_LOG_NAME
    if log_path.exists() and log_path.stat().st_size > 512 * 1024:
        log_path.replace(log_path.with_suffix(".previous.log"))
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_path.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {status}\n")
        if detail:
            file.write(detail.rstrip() + "\n")
    if os.name != "nt":
        try:
            os.chmod(log_path, 0o600)
        except OSError:
            pass
    return log_path


def _startup_error_html(
    exc: BaseException,
    log_path: Path,
    detail: str = "",
) -> str:
    error_name = html.escape(type(exc).__name__)
    error_text = html.escape(str(exc) or "Erro desconhecido")
    safe_log_name = html.escape(log_path.name)
    safe_detail = html.escape(detail or f"{type(exc).__name__}: {exc}")
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ArtFinder - erro de inicializacao</title>
<style>
body{{font-family:system-ui,sans-serif;background:#111118;color:#f5f5f7;margin:0;padding:28px}}
main{{max-width:680px;margin:auto;background:#1d1d28;border:1px solid #343448;border-radius:16px;padding:24px}}
h1{{font-size:1.4rem;color:#ff7b8b}}code{{word-break:break-word;color:#d6b4ff}}
p{{line-height:1.55;color:#d4d4dd}}
a{{color:#b99cff}}details{{margin-top:18px}}pre{{white-space:pre-wrap;word-break:break-word;background:#111118;padding:14px;border-radius:10px;max-height:45vh;overflow:auto}}
</style></head><body><main>
<h1>O ArtFinder nao conseguiu iniciar</h1>
<p>O aplicativo permaneceu aberto para mostrar o diagnostico em vez de fechar.</p>
<p><strong>{error_name}:</strong> <code>{error_text}</code></p>
<p>O relatorio foi salvo no armazenamento interno privado do app. Ele nao aparece no gerenciador de arquivos comum.</p>
<p><a href="/{safe_log_name}">Abrir o relatorio completo</a></p>
<details><summary>Ver detalhes tecnicos nesta tela</summary><pre>{safe_detail}</pre></details>
</main></body></html>"""


def _serve_startup_error(exc: BaseException, log_path: Path) -> None:
    """Serve a dependency-free diagnostic page to the Android WebView."""
    try:
        detail = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        detail = ""
    page = _startup_error_html(exc, log_path, detail).encode("utf-8")

    class StartupErrorHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path.split("?", 1)[0] == f"/{MOBILE_LOG_NAME}":
                try:
                    body = log_path.read_bytes()
                except OSError:
                    body = b"Startup log is unavailable."
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return

            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, _format: str, *_args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", MOBILE_PORT), StartupErrorHandler)
    server.serve_forever()


def main(
    app_loader: Callable[[], object] | None = None,
    server_runner: Callable[..., None] | None = None,
    error_server: Callable[[BaseException, Path], None] | None = None,
) -> None:
    data_dir = prepare_mobile_environment()

    try:
        import uvicorn

        # Import only after ARTFINDER_DATA_DIR is set: config.py creates its
        # data directories during import and Android resources are read-only.
        if app_loader is None:
            from app import app
        else:
            app = app_loader()

        _write_startup_log(data_dir, "STARTING", f"Python {sys.version}")
        runner = server_runner or uvicorn.run
        runner(
            app,
            host="127.0.0.1",
            port=MOBILE_PORT,
            log_level="warning",
            access_log=False,
            server_header=False,
        )
    except KeyboardInterrupt:
        raise
    except BaseException as exc:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log_path = _write_startup_log(data_dir, "FAILED", detail)
        print(detail, file=sys.stderr, flush=True)
        (error_server or _serve_startup_error)(exc, log_path)


if __name__ == "__main__":
    main()
