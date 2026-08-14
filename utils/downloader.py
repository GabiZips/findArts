"""Asynchronous, bounded and deduplicated artwork downloader."""

from __future__ import annotations

import asyncio
import json
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Awaitable, Callable, Optional
from urllib.parse import urlsplit

import aiofiles
import aiohttp

from config import (
    DOWNLOAD_DIR,
    MAX_DOWNLOAD_WORKERS,
    MAX_FILE_MB,
    ORGANIZE_BY,
    REQUEST_TIMEOUT,
    USE_COLOR_FILTER,
)
from filters.color_filter import passes_color_filter
from filters.quality import passes_file_size
from utils.android_media import (
    AndroidMediaError,
    android_media_available,
    delete_image as delete_public_image,
    publish_image,
)
from utils.database import (
    is_downloaded,
    is_duplicate_hash,
    register_download,
    set_download_public_uri,
)
from utils.network import is_domain, validate_redirect, validate_remote_url


_MAX_DOWNLOAD_BYTES = MAX_FILE_MB * 1024 * 1024
_MAX_REDIRECTS = 5


def get_extension(url: str) -> str:
    """Extract a supported image extension from a URL."""
    ext = url.split("?", 1)[0].rsplit(".", 1)[-1].lower()
    allowed = {"jpg", "jpeg", "png", "gif", "webp"}
    return ext if ext in allowed else "jpg"


def compute_phash(image_data: bytes) -> Optional[str]:
    """Calculate a perceptual image hash."""
    try:
        import imagehash
        from PIL import Image

        with Image.open(BytesIO(image_data)) as image:
            return str(imagehash.phash(image))
    except Exception:
        return None


def _safe_component(value: object, fallback: str = "unknown") -> str:
    """Create a short Windows-safe filename component with no path semantics."""
    clean = re.sub(r"[^a-zA-Z0-9_\- ]", "", str(value or "")).strip(" .")
    return clean[:100] or fallback


def _validate_image(image_data: bytes) -> bool:
    """Reject mislabeled HTML/error pages and malformed image payloads."""
    try:
        from PIL import Image

        with Image.open(BytesIO(image_data)) as image:
            image.verify()
        return True
    except Exception:
        return False


def _request_headers(url: str) -> dict[str, str]:
    parsed = urlsplit(url)
    if is_domain(parsed.hostname, "pximg.net") or is_domain(parsed.hostname, "pixiv.net"):
        referer = "https://www.pixiv.net/"
    else:
        referer = f"{parsed.scheme}://{parsed.netloc}/"
    return {
        "Referer": referer,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }


async def _fetch_image(
    session: aiohttp.ClientSession,
    url: str,
) -> tuple[bytes, str]:
    """Fetch an image with bounded streaming and validated redirects."""
    current_url = url
    for redirect_count in range(_MAX_REDIRECTS + 1):
        validate_remote_url(current_url)
        async with session.get(
            current_url,
            headers=_request_headers(current_url),
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            allow_redirects=False,
        ) as response:
            if response.status in {301, 302, 303, 307, 308}:
                if redirect_count >= _MAX_REDIRECTS:
                    raise ValueError("Redirecionamentos demais")
                location = response.headers.get("Location", "")
                if not location:
                    raise ValueError("Redirecionamento sem destino")
                current_url = validate_redirect(current_url, location)
                continue

            if response.status != 200:
                raise ValueError(f"HTTP {response.status}")

            content_type = (
                response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            )
            if content_type not in {
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/webp",
                "image/avif",
                "image/bmp",
            }:
                raise ValueError("O servidor nao retornou uma imagem")

            try:
                content_length = int(response.headers.get("Content-Length", "0"))
            except ValueError:
                content_length = 0
            if content_length > _MAX_DOWNLOAD_BYTES:
                raise ValueError("Arquivo maior que o limite configurado")
            if content_length > 0 and not passes_file_size(content_length):
                raise ValueError("Arquivo muito pequeno/grande")

            chunks = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                chunks.extend(chunk)
                if len(chunks) > _MAX_DOWNLOAD_BYTES:
                    raise ValueError("Arquivo maior que o limite configurado")
            return bytes(chunks), current_url

    raise ValueError("Falha ao seguir redirecionamento")


async def download_single(
    session: aiohttp.ClientSession,
    post: dict,
    category: str,
    semaphore: asyncio.Semaphore,
    on_done: Optional[Callable[[bool, str], Awaitable[None]]] = None,
) -> bool:
    """Download one artwork and register it when all checks pass."""
    source = str(post.get("source", "unknown"))
    post_id = str(post.get("id", ""))
    url = str(post.get("url", ""))

    async def report(ok: bool, message: str) -> None:
        if on_done:
            await on_done(ok, message)

    if not url or not post_id:
        await report(False, "URL ou ID ausente")
        return False
    if await asyncio.to_thread(is_downloaded, source, post_id):
        await report(False, f"{source}:{post_id} ja baixado")
        return False

    async with semaphore:
        try:
            image_data, final_url = await _fetch_image(session, url)
        except Exception as exc:
            print(f"  [!] Erro ao baixar [{source}:{post_id}]: {exc}")
            await report(False, str(exc))
            return False

    if not passes_file_size(len(image_data)):
        await report(False, "Arquivo muito pequeno/grande")
        return False
    if not await asyncio.to_thread(_validate_image, image_data):
        await report(False, "Conteudo de imagem invalido")
        return False

    phash = await asyncio.to_thread(compute_phash, image_data)
    if phash and await asyncio.to_thread(is_duplicate_hash, phash):
        await report(False, "Duplicata detectada")
        return False
    if USE_COLOR_FILTER and not await asyncio.to_thread(
        passes_color_filter, None, image_data
    ):
        await report(False, "Filtro de cor")
        return False

    raw_artist = str(post.get("artist", "")).strip()
    raw_category = str(post.get("category") or category or "").strip()
    if ORGANIZE_BY == "artist" and raw_artist:
        save_category = (
            _safe_component(raw_artist.split(",")[0], "")
            or _safe_component(raw_category, "misc")
        )
    else:
        save_category = (
            _safe_component(raw_category, "")
            or _safe_component(raw_artist.split(",")[0], "misc")
        )

    folder = Path(DOWNLOAD_DIR) / save_category
    folder.mkdir(parents=True, exist_ok=True)
    safe_source = _safe_component(source)
    safe_post_id = _safe_component(post_id)
    filename = folder / f"{safe_source}_{safe_post_id}.{get_extension(final_url)}"
    partial = filename.with_suffix(filename.suffix + ".part")

    try:
        async with aiofiles.open(partial, "wb") as file:
            await file.write(image_data)
            await file.flush()
        await asyncio.to_thread(os.replace, partial, filename)
    except Exception as exc:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            pass
        print(f"  [!] Erro ao salvar [{filename.name}]: {exc}")
        await report(False, str(exc))
        return False

    metadata = {
        "source": source,
        "id": post_id,
        "url": url,
        "artist": post.get("artist", ""),
        "score": post.get("score", 0),
        "tags": post.get("tags", ""),
        "width": post.get("width", 0),
        "height": post.get("height", 0),
        "rating": post.get("rating", "sfw"),
        "category": post.get("category", category),
        "page_url": post.get("page_url", ""),
        "phash": phash or "",
    }
    metadata_folder = Path(DOWNLOAD_DIR) / "metadata" / save_category
    metadata_folder.mkdir(parents=True, exist_ok=True)
    metadata_path = metadata_folder / f"{safe_source}_{safe_post_id}.json"
    try:
        async with aiofiles.open(metadata_path, "w", encoding="utf-8") as file:
            await file.write(json.dumps(metadata, ensure_ascii=False, indent=2))
    except Exception:
        pass

    await asyncio.to_thread(
        register_download,
        source=source,
        post_id=post_id,
        file_path=str(filename),
        artist=post.get("artist", ""),
        score=post.get("score", 0),
        tags=post.get("tags", ""),
        width=post.get("width", 0),
        height=post.get("height", 0),
        phash=phash or "",
    )

    public_status = ""
    if android_media_available():
        try:
            public_uri = await asyncio.to_thread(publish_image, filename)
            updated = await asyncio.to_thread(
                set_download_public_uri,
                str(filename),
                public_uri,
            )
            if not updated:
                try:
                    await asyncio.to_thread(delete_public_image, public_uri)
                except AndroidMediaError:
                    pass
                raise AndroidMediaError("Download removido do banco durante a exportação")
            public_status = " · Galeria do celular"
        except Exception as exc:
            # The private copy remains valid and visible inside ArtFinder. A
            # per-item export button lets the user retry without downloading.
            public_status = " · Galeria pendente"
            print(f"  [!] {source}:{post_id} salvo no app, mas não na Galeria: {exc}")

    await report(True, filename.name + public_status)
    return True


async def download_batch(
    posts: list[dict],
    category: str,
    on_progress: Optional[
        Callable[[int, int, int, str], Awaitable[None]]
    ] = None,
) -> int:
    """Download a batch concurrently and report aggregate batch progress."""
    semaphore = asyncio.Semaphore(MAX_DOWNLOAD_WORKERS)
    downloaded = 0
    done_count = 0
    total = len(posts)
    connector = aiohttp.TCPConnector(limit=MAX_DOWNLOAD_WORKERS)
    headers = {"User-Agent": "artFinder/2.0 (personal archiver)"}

    async def callback(ok: bool, message: str) -> None:
        nonlocal downloaded, done_count
        done_count += 1
        if ok:
            downloaded += 1
        print(
            f"\r    [{done_count}/{total}] ok: {downloaded} | MSG: {message}",
            flush=True,
        )
        if on_progress:
            await on_progress(done_count, total, downloaded, message)

    async with aiohttp.ClientSession(
        connector=connector,
        headers=headers,
    ) as session:
        outcomes = await asyncio.gather(
            *[
                download_single(session, post, category, semaphore, callback)
                for post in posts
            ],
            return_exceptions=True,
        )
        for outcome in outcomes:
            if isinstance(outcome, BaseException):
                print(f"  [!] Erro inesperado no lote: {outcome!r}")

    print()
    return downloaded


def run_download_batch(posts: list[dict], category: str) -> int:
    """Synchronous wrapper kept for CLI compatibility."""
    return asyncio.run(download_batch(posts, category))
