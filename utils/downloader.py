# utils/downloader.py
"""
Downloader assíncrono com:
- Verificação de qualidade (resolução, tamanho)
- Deduplicação por source:id (SQLite)
- Deduplicação por perceptual hash (imagehash)
- Filtro de cor opcional
- Salvamento de metadados JSON ao lado de cada imagem
- Suporte a callback de progresso (para SSE streaming)
"""

import json
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Callable, Awaitable

from config import (
    DOWNLOAD_DIR, ORGANIZE_BY,
    REQUEST_TIMEOUT, MAX_DOWNLOAD_WORKERS, USE_COLOR_FILTER,
)
from filters.quality import passes_file_size
from filters.color_filter import passes_color_filter
from utils.database import is_downloaded, is_duplicate_hash, register_download


def get_extension(url: str) -> str:
    """Extrai a extensão do arquivo a partir da URL."""
    ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
    allowed = {"jpg", "jpeg", "png", "gif", "webp"}
    return ext if ext in allowed else "jpg"


def compute_phash(image_data: bytes) -> Optional[str]:
    """Calcula o perceptual hash de uma imagem. Retorna hex string ou None."""
    try:
        import imagehash
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(image_data))
        h = imagehash.phash(img)
        return str(h)
    except Exception:
        return None


async def download_single(
    session: aiohttp.ClientSession,
    post: dict,
    category: str,
    semaphore: asyncio.Semaphore,
    on_done: Optional[Callable[[bool, str], Awaitable[None]]] = None,
) -> bool:
    """
    Baixa uma única imagem de forma assíncrona.

    Args:
        session: sessão aiohttp compartilhada
        post: dict com url, source, id, score, artist, tags, width, height
        category: nome da pasta de destino (ex: "shadow_solo")
        semaphore: limita concorrência
        on_done: callback assíncrono chamado ao terminar cada imagem.
                 Recebe (success: bool, message: str)

    Returns:
        True se a imagem foi baixada com sucesso.
    """
    source  = post.get("source", "unknown")
    post_id = post.get("id", "")
    url     = post.get("url", "")

    async def _report(ok: bool, msg: str):
        if on_done:
            await on_done(ok, msg)

    if not url or not post_id:
        await _report(False, "URL ou ID ausente")
        return False

    # --- Verificação de duplicata por source:id ---
    # (em thread: SQLite é bloqueante e congelaria o event loop/SSE)
    if await asyncio.to_thread(is_downloaded, source, post_id):
        await _report(False, f"{source}:{post_id} já baixado")
        return False

    async with semaphore:
        try:
            import urllib.parse
            netloc = urllib.parse.urlparse(url).netloc
            # Pixiv (i.pximg.net) exige Referer da pixiv.net, senão retorna 403
            referer = ("https://www.pixiv.net/" if "pximg.net" in netloc
                       else f"https://{netloc}/")
            req_headers = {
                "Referer": referer,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with session.get(url, headers=req_headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as resp:
                if "text/html" in resp.headers.get("Content-Type", ""):
                    await _report(False, "Bloqueado pelo servidor (HTML recebido)")
                    return False
                if resp.status != 200:
                    await _report(False, f"HTTP {resp.status}")
                    return False

                content_length = int(resp.headers.get("Content-Length", 0))
                if content_length > 0 and not passes_file_size(content_length):
                    await _report(False, "Arquivo muito pequeno/grande")
                    return False

                image_data = await resp.read()

        except Exception as e:
            # sem emoji: em consola cp1252 (Windows) o print de "⚠️" levanta
            # UnicodeEncodeError dentro do handler e derruba o lote inteiro
            print(f"  [!] Erro ao baixar [{source}:{post_id}]: {e}")
            await _report(False, str(e))
            return False

    if not passes_file_size(len(image_data)):
        await _report(False, "Arquivo muito pequeno/grande")
        return False

    # pHash é CPU-bound e a checagem lê o banco inteiro — ambos em thread
    phash = await asyncio.to_thread(compute_phash, image_data)
    if phash and await asyncio.to_thread(is_duplicate_hash, phash):
        await _report(False, "Duplicata detectada")
        return False

    if USE_COLOR_FILTER and not await asyncio.to_thread(passes_color_filter, None, image_data):
        await _report(False, "Filtro de cor")
        return False

    # --- Salvar arquivo ---
    import re as _re
    def _safe(name: str) -> str:
        # remove caracteres inválidos em nomes de pasta (Windows não aceita : \ / etc.)
        return _re.sub(r'[^a-zA-Z0-9_\- ]', '', name or '').strip()

    raw_artist = post.get("artist", "").strip()
    raw_cat    = (post.get("category") or "").strip()

    if ORGANIZE_BY == "artist" and raw_artist:
        # por artista (com fallback pra categoria, depois misc)
        save_category = _safe(raw_artist.split(",")[0]) or _safe(raw_cat) or "misc"
    else:
        # por tag/categoria (padrão; fallback pra artista, depois misc)
        save_category = _safe(raw_cat) or _safe(raw_artist.split(",")[0]) or "misc"

    folder = Path(DOWNLOAD_DIR) / save_category
    folder.mkdir(parents=True, exist_ok=True)

    ext      = get_extension(url)
    filename = folder / f"{source}_{post_id}.{ext}"

    try:
        async with aiofiles.open(filename, "wb") as f:
            await f.write(image_data)
    except Exception as e:
        print(f"  [!] Erro ao salvar [{filename.name}]: {e}")
        await _report(False, str(e))
        return False

    # --- Salvar metadados JSON ---
    meta = {
        "source":   source,
        "id":       post_id,
        "url":      url,
        "artist":   post.get("artist", ""),
        "score":    post.get("score", 0),
        "tags":     post.get("tags", ""),
        "width":    post.get("width", 0),
        "height":   post.get("height", 0),
        "rating":   post.get("rating", "sfw"),
        "category": post.get("category", category),
        "page_url": post.get("page_url", ""),
        "phash":    phash or "",
    }
    meta_folder = Path(DOWNLOAD_DIR) / "metadata" / save_category
    meta_folder.mkdir(parents=True, exist_ok=True)
    meta_path = meta_folder / f"{source}_{post_id}.json"
    try:
        async with aiofiles.open(meta_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))
    except Exception:
        pass

    # --- Registrar no banco (em thread, SQLite bloqueante) ---
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

    await _report(True, filename.name)
    return True


async def download_batch(
    posts: list[dict],
    category: str,
    on_progress: Optional[Callable[[int, int, int, str], Awaitable[None]]] = None,
) -> int:
    """
    Baixa um lote de imagens de forma assíncrona e concorrente.

    Args:
        posts: lista de dicts de posts
        category: categoria (pasta de destino)
        on_progress: callback assíncrono(done, total, ok_count, filename)

    Returns:
        Número de imagens baixadas com sucesso
    """
    semaphore  = asyncio.Semaphore(MAX_DOWNLOAD_WORKERS)
    downloaded = 0
    done_count = 0
    total      = len(posts)

    connector = aiohttp.TCPConnector(limit=MAX_DOWNLOAD_WORKERS)
    headers   = {"User-Agent": "artFinder/2.0 (personal archiver)"}

    async def _cb(ok: bool, msg: str):
        nonlocal downloaded, done_count
        done_count += 1
        if ok:
            downloaded += 1
        print(f"\r    [{done_count}/{total}] ok: {downloaded} | MSG: {msg}", flush=True)
        if on_progress:
            await on_progress(done_count, total, downloaded, msg)

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [
            download_single(session, post, category, semaphore, on_done=_cb)
            for post in posts
        ]
        # return_exceptions: um erro inesperado em um download não pode
        # abortar o lote inteiro (os outros continuam)
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        for out in outcomes:
            if isinstance(out, BaseException):
                print(f"  [!] Erro inesperado no lote: {out!r}")

    print()
    return downloaded


def run_download_batch(posts: list[dict], category: str) -> int:
    """Wrapper síncrono para asyncio.run (sem callback de progresso)."""
    return asyncio.run(download_batch(posts, category))
