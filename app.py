"""
app.py — Shadow & Rouge Art Finder  (interface visual local)
Servidor FastAPI que serve a GUI no navegador.

Uso:
    python app.py
    # Abre automaticamente: http://localhost:7860
"""

import asyncio
import json
import sys
import webbrowser
from pathlib import Path
from threading import Timer

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
try:
    from sse_starlette.sse import EventSourceResponse
    HAS_SSE = True
except ImportError:
    HAS_SSE = False
import requests as _requests

# ── garante que o projeto está no path ─────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

# Evita UnicodeEncodeError nos prints em consoles Windows cp1252
# (queries japonesas do Pixiv, emojis etc. viram '?' em vez de crashar)
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="replace")
        except Exception:
            pass

from config import DOWNLOAD_DIR
from utils.database import get_stats, known_uids, add_to_blacklist, add_blocked_artist, get_blocked_artists
from utils.downloader import download_batch, run_download_batch
from utils.normalize import normalize_posts

USER_CATS_FILE = Path(__file__).parent / "user_categories.json"


def _split_tags(tags_str: str) -> list[str]:
    """Divide tags por ';' ou nova linha em queries independentes (OR).
    'shadow_the_hedgehog; rouge_the_bat' → duas buscas separadas.
    'shadow_the_hedgehog rouge_the_bat'  → uma busca com AND (comportamento padrão do booru).
    """
    import re
    parts = re.split(r'[;\n]+', tags_str or "")
    return [p.strip() for p in parts if p.strip()]


def _load_user_cats() -> dict:
    """Carrega categorias do usuario de user_categories.json."""
    try:
        with open(USER_CATS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("categories", {})
    except Exception:
        # fallback para categorias antigas do config
        from config import CATEGORIES as CK
        return {k: {"label": k.replace("_"," ").title(), "tags": k, "group": "Geral", "favorite": False, "emoji": "🎨", "color": "#6366f1"} for k in CK}


def _save_user_cats(cats: dict) -> None:
    with open(USER_CATS_FILE, "w", encoding="utf-8") as f:
        json.dump({"categories": cats}, f, ensure_ascii=False, indent=2)

app = FastAPI(title="artFinder")

import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles

# 1. Força o diretório para a pasta temporária do Vercel
DOWNLOAD_DIR = "/tmp/downloads"
downloads_path = Path(DOWNLOAD_DIR)

# 2. Cria a pasta no diretório /tmp (o único com permissão de escrita)
downloads_path.mkdir(parents=True, exist_ok=True)

# 3. Monta a rota estática para a galeria
app.mount("/downloads", StaticFiles(directory=str(downloads_path)), name="downloads")

# ── helpers ─────────────────────────────────────────────────────────

def _get_sources() -> dict:
    sources = {}
    try:
        from sources.bsky import fetch_posts
        from config import BSKY_HANDLE, BSKY_PASSWORD
        if BSKY_HANDLE and BSKY_PASSWORD:
            sources["Bluesky"] = fetch_posts
    except Exception as e:
        print(f"Error loading Bluesky: {e}")
        pass
    try:
        from sources.danbooru import fetch_posts
        sources["Danbooru"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.gelbooru import fetch_posts
        sources["Gelbooru"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.safebooru import fetch_posts
        sources["Safebooru"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.e621 import fetch_posts
        sources["e621"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.deviantart import fetch_posts
        from config import DEVIANTART_CLIENT_ID
        if DEVIANTART_CLIENT_ID:
            sources["DeviantArt"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.tumblr import fetch_posts
        from config import TUMBLR_API_KEY
        if TUMBLR_API_KEY:
            sources["Tumblr"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.pixiv import fetch_posts
        from config import PIXIV_REFRESH_TOKEN
        if PIXIV_REFRESH_TOKEN:
            sources["Pixiv"] = fetch_posts
    except Exception as e:
        print(f"Error loading Pixiv: {e}")
    return sources


# ── rotas ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve a interface principal."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/sources")
async def list_sources():
    """Lista fontes disponíveis."""
    return {"sources": list(_get_sources().keys())}


@app.get("/api/categories")
async def get_categories():
    """Retorna todas as categorias do usuario."""
    cats = _load_user_cats()
    return {"categories": cats}


_SOURCE_PREFIX_RE = None  # compilado sob demanda em create_category


def _parse_source_prefixes(tags_field: str) -> tuple[str, dict[str, list[str]]]:
    """Separa entradas "fonte: query" do campo de tags.

    "yamato_(one_piece); pixiv: ヤマト(ONEPIECE); tumblr: yamato one piece"
    → ("yamato_(one_piece)", {"pixiv": ["ヤマト(ONEPIECE)"], "tumblr": [...]})
    """
    import re
    global _SOURCE_PREFIX_RE
    if _SOURCE_PREFIX_RE is None:
        _SOURCE_PREFIX_RE = re.compile(
            r"(?i)^(danbooru|gelbooru|safebooru|e621|pixiv|tumblr|bsky|bluesky|deviantart)\s*:\s*(.+)$"
        )
    src_tags: dict[str, list[str]] = {}
    booru_parts: list[str] = []
    for part in _split_tags(tags_field):
        m = _SOURCE_PREFIX_RE.match(part)
        if m:
            src = m.group(1).lower()
            if src == "bsky":
                src = "bluesky"   # nome usado em _get_sources()
            src_tags.setdefault(src, []).append(m.group(2).strip())
        else:
            booru_parts.append(part)
    return "; ".join(booru_parts), src_tags


def _auto_map_category(key: str) -> dict:
    """Descobre tags específicas por fonte (Pixiv/e621) e salva na categoria.
    Roda em thread. Não sobrescreve overrides já existentes (manuais)."""
    try:
        from utils.tagmap import suggest_source_tags
        cats = _load_user_cats()
        if key not in cats:
            return {}
        found: dict[str, list[str]] = {}
        for tg in _split_tags(cats[key].get("tags", "")):
            for src, qs in suggest_source_tags(tg).items():
                dst = found.setdefault(src, [])
                dst.extend(q for q in qs if q not in dst)
        if not found:
            print(f"  [AutoTag] '{key}': nenhuma tag específica encontrada.")
            return {}
        # Re-lê antes de salvar (minimiza conflito com edições concorrentes)
        cats = _load_user_cats()
        if key not in cats:
            return {}
        st = cats[key].setdefault("source_tags", {})
        added = {src: qs for src, qs in found.items() if src not in st}
        if added:
            st.update(added)
            _save_user_cats(cats)
        print(f"  [AutoTag] '{key}': {added or 'nada novo (overrides manuais mantidos)'}")
        return added
    except Exception as e:
        print(f"  [AutoTag] '{key}': erro: {e}")
        return {}


@app.post("/api/categories")
async def create_category(body: dict):
    """Cria ou atualiza uma categoria.
    Body: {key, label, tags, group, emoji, color, favorite,
           source_tags?: {fonte: [queries]}, auto_map?: bool}

    No campo tags, entradas com prefixo de fonte viram a query exata
    daquela fonte:  "yamato_(one_piece); pixiv: ヤマト(ONEPIECE)".
    Sem override manual, o app descobre tags do Pixiv/e621 sozinho em
    segundo plano (wiki do Danbooru + validação nas APIs reais).
    """
    key = body.get("key", "").strip().replace(" ", "_").lower()
    if not key or not body.get("tags"):
        return JSONResponse({"error": "key e tags sao obrigatorios"}, status_code=400)

    booru_tags, src_tags = _parse_source_prefixes(body.get("tags", ""))

    # source_tags passado direto no body (via API) complementa os prefixos
    for src, qs in (body.get("source_tags") or {}).items():
        qs = qs if isinstance(qs, list) else [qs]
        dst = src_tags.setdefault(str(src).lower(), [])
        dst.extend(q for q in qs if q and q not in dst)

    cats = _load_user_cats()
    old = cats.get(key) or {}
    # Se as tags booru não mudaram, preserva os overrides antigos;
    # se mudaram, descarta (estariam mapeando o personagem errado).
    if _split_tags(old.get("tags", "")) == _split_tags(booru_tags):
        merged = dict(old.get("source_tags") or {})
        merged.update(src_tags)
        src_tags = merged

    cats[key] = {
        "label":    body.get("label", key),
        "emoji":    body.get("emoji", "🎨"),
        "tags":     booru_tags,
        "group":    body.get("group", "Geral"),
        "favorite": bool(body.get("favorite", False)),
        "color":    body.get("color", "#6366f1"),
    }
    if src_tags:
        cats[key]["source_tags"] = src_tags
    _save_user_cats(cats)

    # Descoberta automática (Pixiv/e621) em segundo plano — não bloqueia a UI
    if booru_tags and body.get("auto_map", True):
        asyncio.get_running_loop().run_in_executor(None, _auto_map_category, key)

    return {"ok": True, "key": key, "category": cats[key]}


@app.post("/api/categories/{key}/auto-map")
async def auto_map_category(key: str):
    """(Re)executa a descoberta automática de tags por fonte da categoria."""
    cats = _load_user_cats()
    if key not in cats:
        return JSONResponse({"error": "Categoria nao encontrada"}, status_code=404)
    loop = asyncio.get_running_loop()
    added = await loop.run_in_executor(None, _auto_map_category, key)
    return {"ok": True, "added": added,
            "source_tags": _load_user_cats().get(key, {}).get("source_tags", {})}


@app.get("/api/suggest-source-tags")
async def suggest_source_tags_api(tags: str = ""):
    """Sugere queries por fonte para uma query booru (não salva nada)."""
    tags = (tags or "").strip()
    if not tags:
        return {"suggestions": {}}
    from utils.tagmap import suggest_source_tags
    loop = asyncio.get_running_loop()
    out = await loop.run_in_executor(None, suggest_source_tags, tags)
    return {"suggestions": out}


@app.post("/api/categories/{key}/favorite")
async def toggle_favorite(key: str):
    """Alterna o status de favorito de uma categoria."""
    cats = _load_user_cats()
    if key not in cats:
        return JSONResponse({"error": "Categoria nao encontrada"}, status_code=404)
    cats[key]["favorite"] = not cats[key].get("favorite", False)
    _save_user_cats(cats)
    return {"ok": True, "favorite": cats[key]["favorite"]}


@app.delete("/api/categories/{key}")
async def delete_category(key: str):
    """Remove uma categoria."""
    cats = _load_user_cats()
    if key not in cats:
        return JSONResponse({"error": "Categoria nao encontrada"}, status_code=404)
    del cats[key]
    _save_user_cats(cats)
    return {"ok": True}

@app.post("/api/categories/reorder")
async def reorder_categories(body: dict):
    """Salva a nova ordem das categorias após drag-and-drop."""
    order = body.get("order", [])
    if not order:
        return JSONResponse({"error": "order is required"}, status_code=400)
    cats = _load_user_cats()
    new_cats = {}
    for key in order:
        if key in cats:
            new_cats[key] = cats[key]
    # append any keys not in order (safety)
    for key in cats:
        if key not in new_cats:
            new_cats[key] = cats[key]
    _save_user_cats(new_cats)
    return {"ok": True}

@app.post("/api/block-artist")
async def block_artist(body: dict):
    artist = body.get("artist")
    if not artist:
        return JSONResponse({"error": "Nenhum artista fornecido"}, status_code=400)
    success = add_blocked_artist(artist)
    if not success:
        return JSONResponse({"error": "Erro ao bloquear artista"}, status_code=500)
    return {"ok": True, "artist": artist.strip().lower()}


@app.get("/api/stats")
async def stats():
    """Estatisticas detalhadas do banco + disco."""
    base = get_stats()
    dl_path = Path(DOWNLOAD_DIR).resolve()
    by_cat: dict[str, int] = {}
    total_bytes = 0
    if dl_path.exists():
        for cat_dir in dl_path.iterdir():
            if cat_dir.is_dir() and cat_dir.name != "metadata" and not cat_dir.name.startswith("."):
                files = [f for f in cat_dir.glob("*") if f.is_file()]
                if files:
                    by_cat[cat_dir.name] = len(files)
                    total_bytes += sum(f.stat().st_size for f in files)
    base["by_category"] = by_cat
    base["disk_mb"] = round(total_bytes / 1_048_576, 1)
    # Contadores de triagem (Usar / Talvez / Rever depois / Não gostei)
    try:
        from utils.database import get_all_ratings
        by_rating: dict[str, int] = {}
        for v in get_all_ratings().values():
            by_rating[v] = by_rating.get(v, 0) + 1
        base["by_rating"] = by_rating
    except Exception:
        base["by_rating"] = {}
    return base


# ── RATINGS (triagem) ─────────────────────────────────────────────────────

@app.get("/api/ratings")
async def list_ratings():
    """Retorna {uid: rating} de todas as artes avaliadas."""
    from utils.database import get_all_ratings
    return {"ratings": get_all_ratings()}


@app.get("/api/rated-posts")
async def rated_posts():
    """Retorna todas as artes avaliadas com metadados (para o painel de triagem)."""
    from utils.database import _connect
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT r.uid, r.rating AS aval, r.rated_at,
                   p.source, p.post_id, p.url, p.preview_url, p.page_url,
                   p.artist, p.score, p.width, p.height, p.tags,
                   p.rating, p.category
            FROM ratings r
            LEFT JOIN posts p ON p.uid = r.uid
            ORDER BY r.rated_at DESC
        """).fetchall()
        items = []
        for row in rows:
            uid = row["uid"]
            src = row["source"] or (uid.split(":", 1)[0] if ":" in uid else "")
            pid = row["post_id"] or (uid.split(":", 1)[1] if ":" in uid else uid)
            items.append({
                "uid": uid, "aval": row["aval"], "rated_at": row["rated_at"] or 0,
                "source": src, "post_id": pid,
                "url": row["url"] or "", "preview_url": row["preview_url"] or "",
                "page_url": row["page_url"] or "", "artist": row["artist"] or "",
                "score": row["score"] or 0, "width": row["width"] or 0,
                "height": row["height"] or 0, "tags": row["tags"] or "",
                "rating": row["rating"] or "sfw", "category": row["category"] or "",
            })
        return {"items": items}
    finally:
        conn.close()


@app.post("/api/ratings")
async def rate_post(body: dict):
    """Avalia uma arte. Body: {source, id, aval: usar|talvez|depois|nao}.
    aval vazio/null remove a avaliação.
    (O campo se chama 'aval' porque 'rating' já é usado para SFW/NSFW no post.)"""
    source  = body.get("source", "")
    post_id = str(body.get("id") or body.get("post_id") or "")
    rating  = (body.get("aval") or "").strip().lower()
    if not source or not post_id:
        return JSONResponse({"error": "source e id são obrigatórios"}, status_code=400)

    from utils.database import set_rating, remove_rating, VALID_RATINGS
    if not rating:
        removed = remove_rating(source, post_id)
        return {"ok": True, "removed": removed}
    if rating not in VALID_RATINGS:
        return JSONResponse({"error": f"rating inválido (use: {', '.join(sorted(VALID_RATINGS))})"},
                            status_code=400)
    set_rating(source, post_id, rating)

    # Guarda os metadados no cache de posts para não perder a imagem de vista
    try:
        from utils.database import upsert_posts_batch
        upsert_posts_batch([body])
    except Exception:
        pass
    return {"ok": True, "rating": rating}


# ── FAVORITES ─────────────────────────────────────────────────────────────

@app.get("/api/favorites")
async def list_favorites():
    """Retorna todas as artes favoritadas."""
    from utils.database import get_favorites
    return {"favorites": get_favorites()}


@app.post("/api/favorites")
async def add_to_favorites(body: dict):
    """Salva arte nos favoritos E dispara download para o disco."""
    source  = body.get("source", "")
    post_id = str(body.get("id") or body.get("post_id") or "")
    if not source or not post_id:
        return JSONResponse({"error": "source e id são obrigatórios"}, status_code=400)
    from utils.database import add_favorite
    inserted = add_favorite(
        source=source, post_id=post_id,
        artist=body.get("artist", ""),
        url=body.get("url", ""),
        preview_url=body.get("preview_url", ""),
        page_url=body.get("page_url", ""),
    )
    # Auto-download: salva o arquivo no disco também, a menos que skip_download seja True
    skip_download = body.get("skip_download", False)
    dl_url   = body.get("url") or body.get("preview_url", "")
    category = body.get("category") or "favoritos"

    if dl_url and not skip_download:
        from utils.database import is_downloaded
        if not is_downloaded(source, post_id):
            try:
                dl_posts = [{
                    "url":         dl_url,
                    "preview_url": body.get("preview_url", dl_url),
                    "source":      source,
                    "id":          post_id,
                    "artist":      body.get("artist", ""),
                    "score":       body.get("score", 0),
                    "width":       body.get("width", 0),
                    "height":      body.get("height", 0),
                    "tags":        body.get("tags", ""),
                    "rating":      body.get("rating", "sfw"),
                    "page_url":    body.get("page_url", ""),
                    # sem esta chave o downloader ignora a categoria do lote e
                    # salva na pasta do artista/misc em vez de "favoritos"
                    "category":    category,
                }]
                await download_batch(dl_posts, category)
            except Exception as e:
                print(f"  [DEBUG - Baixar] Falha ao baixar arte {post_id} automaticamente: {e}")
    
    # Salva os metadados dessa arte no cache (tabela posts) para a Galeria usar depois
    try:
        from utils.database import upsert_posts_batch
        upsert_posts_batch([{
            "source": source, "id": post_id, "url": body.get("url", ""),
            "preview_url": body.get("preview_url", ""), "page_url": body.get("page_url", ""),
            "artist": body.get("artist", ""), "score": body.get("score", 0),
            "width": body.get("width", 0), "height": body.get("height", 0),
            "tags": body.get("tags", ""), "rating": body.get("rating", "sfw"),
            "category": body.get("category", "")
        }])
    except Exception as e:
        print(f"  [DEBUG - Metadados] Erro ao salvar cache da arte favoritada: {e}")

    print(f"  [DEBUG - Guardar/Baixar] ID {post_id} salvo. Auto-download={not skip_download}")
    return {"ok": True, "inserted": inserted, "already_existed": not inserted}


@app.delete("/api/favorites/{source}/{post_id}")
async def remove_from_favorites(source: str, post_id: str):
    """Remove uma arte dos favoritos."""
    from utils.database import remove_favorite
    removed = remove_favorite(source, post_id)
    return {"ok": True, "removed": removed}



@app.get("/api/downloaded-ids")
async def downloaded_ids():
    """Retorna lista de source_ids ja baixados para filtro hide-downloaded."""
    from utils.database import _connect
    conn = _connect()
    try:
        rows = conn.execute("SELECT source_id FROM downloads").fetchall()
        return {"ids": [r[0] for r in rows]}
    finally:
        conn.close()


@app.get("/api/gallery-items")
async def gallery_items():
    """Retorna metadados das imagens baixadas para a galeria interna."""
    from utils.database import _connect, get_blacklisted_uids
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT d.source, d.source_id, d.file_path, d.artist, d.score,
                   d.downloaded_at, d.tags, d.width, d.height,
                   p.rating, p.page_url, p.category, p.preview_url, p.url as orig_url
            FROM downloads d
            LEFT JOIN posts p ON p.uid = d.source_id
            ORDER BY d.downloaded_at DESC
        """).fetchall()
        # Respeita ocultar-pra-sempre (blacklist) e artistas bloqueados
        blacklist = get_blacklisted_uids()
        blocked   = set(get_blocked_artists())
        items = []
        dl_dir = Path(DOWNLOAD_DIR).resolve()
        for row in rows:
            source, source_id, file_path, artist, score, dl_at, tags, w, h, rating, page_url, category, prev_url, orig_url = row
            if not file_path:
                continue
            if f"{source}:{source_id}" in blacklist:
                continue
            if (artist or "").strip().lower() in blocked:
                continue
            fp = Path(file_path)
            if not fp.is_absolute():
                fp = (Path(__file__).parent / fp).resolve()
            if not fp.exists():
                continue
            try:
                rel = fp.relative_to(dl_dir).as_posix()
            except ValueError:
                rel = "/".join(fp.parts[-2:])
            items.append({
                "source":        source,
                "uid":           source_id or f"{source}:?",
                "rel_path":      rel,
                "artist":        artist or "",
                "score":         score or 0,
                "downloaded_at": dl_at or 0,
                "tags":          tags or "",
                "width":         w or 0,
                "height":        h or 0,
                "rating":        rating or "sfw",
                "page_url":      page_url or "",
                "category":      category or "",
                "preview_url":   prev_url or "",
                "orig_url":      orig_url or "",
            })
        return {"items": items}
    finally:
        conn.close()


@app.get("/api/tag-suggest")
async def tag_suggest(q: str = ""):
    """Sugere tags reais (autocomplete do Danbooru) para o termo digitado."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"tags": []}
    import requests
    from config import DANBOORU_LOGIN, DANBOORU_API_KEY

    def _fetch():
        params = {"search[query]": q, "search[type]": "tag_query", "limit": 10}
        auth = (DANBOORU_LOGIN, DANBOORU_API_KEY) if (DANBOORU_LOGIN and DANBOORU_API_KEY) else None
        r = requests.get(
            "https://danbooru.donmai.us/autocomplete.json",
            params=params, auth=auth,
            headers={"User-Agent": "ArtFinder/2.0 (personal archiver)"},
            timeout=6,
        )
        r.raise_for_status()
        return r.json()

    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, _fetch)
    except Exception as e:
        return {"tags": [], "error": str(e)}

    out = []
    for d in data if isinstance(data, list) else []:
        val = d.get("value") or d.get("label") or ""
        if not val:
            continue
        out.append({
            "value":      val,
            "post_count": d.get("post_count") or 0,
            "category":   d.get("category", 0),
        })
    return {"tags": out}


@app.get("/api/duplicates")
async def duplicates(threshold: int = 8):
    """Agrupa imagens baixadas que são quase idênticas (distância de Hamming
    do pHash <= threshold). Retorna só os grupos com 2+ imagens."""
    from utils.database import _connect
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT source, source_id, file_path, phash, artist, score, width, height "
            "FROM downloads WHERE phash IS NOT NULL AND phash != ''"
        ).fetchall()
    finally:
        conn.close()

    dl_dir = Path(DOWNLOAD_DIR).resolve()
    items = []
    for source, sid, file_path, phash, artist, score, w, h in rows:
        if not file_path:
            continue
        fp = Path(file_path)
        if not fp.is_absolute():
            fp = (Path(__file__).parent / fp).resolve()
        if not fp.exists():
            continue
        try:
            rel = fp.relative_to(dl_dir).as_posix()
        except ValueError:
            rel = "/".join(fp.parts[-2:])
        try:
            bits = int(phash, 16)
        except (TypeError, ValueError):
            continue
        items.append({
            "uid": sid, "source": source, "rel_path": rel,
            "artist": artist or "", "score": score or 0,
            "width": w or 0, "height": h or 0, "_bits": bits,
        })

    # União por distância de Hamming (union-find simples)
    n = len(items)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for i in range(n):
        for j in range(i + 1, n):
            if bin(items[i]["_bits"] ^ items[j]["_bits"]).count("1") <= threshold:
                union(i, j)

    clusters: dict[int, list] = {}
    for idx in range(n):
        clusters.setdefault(find(idx), []).append(items[idx])

    groups = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        for m in members:
            m.pop("_bits", None)
        # maior resolução primeiro (a "melhor" pra manter)
        members.sort(key=lambda m: (m["width"] * m["height"], m["score"]), reverse=True)
        groups.append(members)

    return {"groups": groups, "count": len(groups)}


@app.post("/api/blacklist")
async def blacklist_posts(body: dict):
    """Adiciona UIDs à blacklist permanente (nunca mais aparecem na busca)."""
    uids = body.get("uids", [])
    if not uids:
        return {"added": 0}
    count = add_to_blacklist(uids)
    # Remove do banco de posts também (para liberar espaço)
    from utils.database import delete_posts
    delete_posts(uids)
    print(f"  [DEBUG - Blacklist] {count} artes ocultadas para sempre. (UIDs: {uids})")
    return {"added": count}


@app.get("/api/blacklist")
async def get_blacklist_count():
    """Retorna quantos itens estão na blacklist."""
    from utils.database import get_blacklisted_uids
    uids = get_blacklisted_uids()
    return {"count": len(uids)}


@app.post("/api/sync-db")
async def sync_database():
    """
    Sincroniza o banco com o disco:
    remove registros cujos arquivos foram apagados manualmente.
    """
    from utils.database import sync_db
    removed = sync_db()
    stats = get_stats()
    return {"removed": removed, "remaining": stats["total"],
            "message": f"{removed} registro(s) removido(s) do banco."}


@app.post("/api/clear-db")
async def clear_database():
    """Apaga TODOS os registros do banco (nao apaga arquivos do disco)."""
    from utils.database import clear_db
    removed = clear_db()
    return {"removed": removed,
            "message": f"Banco limpo: {removed} registro(s) removido(s)."}


def _run_search_sync(categories, source_names, pages, custom_cats, all_sources):
    """Executa busca sincrona – chamada em thread do executor."""
    all_posts: list[dict] = []
    seen_ids: set[str] = set()
    blocked_artists: set[str] = get_blocked_artists()
    try:
        from utils.database import get_blacklisted_uids
        blacklist_ids = get_blacklisted_uids()
    except Exception:
        blacklist_ids = set()

    def add_posts(posts, cat):
        for p in normalize_posts(posts):
            uid = f"{p.get('source','?')}:{p.get('id','?')}"
            if uid in seen_ids or uid in blacklist_ids:
                continue   # 'return' abortava o lote inteiro na 1ª duplicata
            artist_lower = (p.get("artist") or "").strip().lower()
            if artist_lower and artist_lower in blocked_artists:
                continue
            seen_ids.add(uid)
            if not p.get("category"):
                p["category"] = cat
            all_posts.append(p)

    for cat in categories:
        for sn in source_names:
            fn = all_sources.get(sn)
            if not fn: continue
            try:
                res = fn(cat, max_pages=pages)
                add_posts(res, cat)
                print(f"  [Busca] {sn} -> '{cat}': retornou {len(res)} artes")
            except Exception as e:
                print(f"  [search] {sn}/{cat}: {e}")

    for ccat in custom_cats:
        label = ccat.get("label","custom"); ctags = ccat.get("tags","")
        if not ctags: continue
        for sn in source_names:
            fn = all_sources.get(sn)
            if not fn: continue
            try:
                # tags= explícito: o antigo hack de injetar em m.CATEGORIES
                # era race condition com buscas simultâneas (duas abas/celular)
                res = fn(label, max_pages=pages, tags=ctags)
                add_posts(res, label)
                print(f"  [Busca] {sn} -> '{label}': retornou {len(res)} artes")
            except Exception as e:
                print(f"  [search-custom] {sn}/{label}: {e}")

    all_posts.sort(key=lambda x: x.get("score") or 0, reverse=True)
    return all_posts


@app.post("/api/search")
async def search(body: dict):
    """Busca sincrona (fallback)."""
    # Resolve tags das categorias selecionadas
    user_cats  = _load_user_cats()
    cat_keys   = body.get("categories", list(user_cats.keys()))
    extra_cats = body.get("custom_categories", [])
    resolved   = []
    for k in cat_keys:
        if k not in user_cats:
            continue
        for tg in _split_tags(user_cats[k]["tags"]):
            resolved.append({"label": k, "tags": tg})
    resolved  += extra_cats
    source_names = body.get("sources", [])
    pages        = max(1, min(int(body.get("pages", 2)), 50))
    all_sources  = _get_sources()
    if not source_names: source_names = list(all_sources.keys())
    else: source_names = [s for s in source_names if s in all_sources]
    loop = asyncio.get_running_loop()
    posts = await loop.run_in_executor(None, lambda: _run_search_sync([], source_names, pages, resolved, all_sources))
    return {"posts": posts, "total": len(posts)}












@app.post("/api/search-stream")




async def search_stream(body: dict, request: Request):
    """Busca com SSE: envia posts fonte por fonte com progresso em tempo real."""
    if not HAS_SSE:
        return JSONResponse(await search(body))

    # Resolve categorias do usuario
    user_cats    = _load_user_cats()
    cat_keys     = body.get("categories", list(user_cats.keys()))
    extra_cats   = body.get("custom_categories", [])  # categorias ad-hoc do frontend
    source_names = body.get("sources", [])
    pages        = max(1, min(int(body.get("pages", 2)), 50))
    min_score    = int(body.get("min_score", 0))
    all_sources  = _get_sources()
    if not source_names: source_names = list(all_sources.keys())
    else: source_names = [s for s in source_names if s in all_sources]

    # Monta os combos (categoria × fonte). Cada combo é
    # (label, fonte, tags_booru | None, query_direta | None):
    #  - se a categoria tem source_tags para a fonte, usa essas queries
    #    como estão (query_direta) — uma busca por query;
    #  - senão, usa as tags booru (divididas por ';'), que cada fonte
    #    converte do seu jeito.
    combos: list[tuple[str, str, str | None, str | None]] = []
    for k in cat_keys:
        if k not in user_cats:
            continue
        ucat = user_cats[k]
        stags = {s.lower(): v for s, v in (ucat.get("source_tags") or {}).items()}
        for sn in source_names:
            ov = stags.get(sn.lower())
            if ov:
                for q in (ov if isinstance(ov, list) else [ov]):
                    if q:
                        combos.append((k, sn, None, q))
            else:
                for tg in _split_tags(ucat.get("tags", "")):
                    combos.append((k, sn, tg, None))
    for c in extra_cats:
        for sn in source_names:
            for tg in _split_tags(c.get("tags", "")):
                combos.append((c.get("label", "custom"), sn, tg, None))

    # blacklist_ids: UIDs permanentemente bloqueados (persiste em TODOS os combos)
    blacklist_ids: set[str] = set()
    try:
        from utils.database import get_blacklisted_uids
        blacklist_ids = get_blacklisted_uids()
        if blacklist_ids:
            print(f"  [Blacklist] {len(blacklist_ids)} UIDs bloqueados carregados.")
    except Exception:
        blacklist_ids = set()
    blocked_artists = get_blocked_artists()

    async def generator():
        loop = asyncio.get_running_loop()
        total_unique_count = 0
        
        # Deduplicação na requisição inteira para não aparecer repetido na mesma tela
        request_seen: set[str] = set()

        for i,(cat,src_name,custom_tags,direct) in enumerate(combos):
            if await request.is_disconnected(): break
            fn = all_sources.get(src_name)
            if not fn: continue

            yield {"event":"progress","data":json.dumps({"source":src_name,"cat":cat,"done":i,"total":len(combos)})}

            def _fetch(fn=fn, cat=cat, custom_tags=custom_tags, direct=direct):
                # tags= explícito: o antigo hack de injetar em m.CATEGORIES
                # era race condition com buscas simultâneas (duas abas/celular)
                if direct:
                    return fn(cat, max_pages=pages, direct=direct)
                if custom_tags:
                    return fn(cat, max_pages=pages, tags=custom_tags)
                return fn(cat, max_pages=pages)

            try:
                posts = await loop.run_in_executor(None, _fetch)
                posts = normalize_posts(posts, src_name)
                print(f"  [Busca] {src_name} -> '{cat}': retornou {len(posts)} artes")
            except Exception as e:
                yield {"event":"progress","data":json.dumps({"source":src_name,"cat":cat,"done":i+1,"total":len(combos),"error":str(e)})}
                continue

            new_posts = []
            for p in posts:
                # 0a) Filtra por score mínimo
                if int(p.get("score") or 0) < min_score:
                    continue
                
                # 0b) Filtra por artista bloqueado
                artist_lower = (p.get("artist") or "").strip().lower()
                if artist_lower and artist_lower in blocked_artists:
                    continue

                # 0c) Filtro central de IA (segunda camada de defesa)
                _AI_KW = {
                    "ai_generated","ai-generated","ai_art","stable_diffusion",
                    "novelai","nai_diffusion","midjourney","dall-e","dall_e",
                    "image_generation","automated_art","diffusion_model",
                    "generated_by_ai","aigc","aiart","stablediffusion",
                    "artificialintelligence","ai generated"
                }
                post_tags = set((p.get("tags") or "").lower().split())
                if post_tags & _AI_KW or p.get("is_ai"):
                    print(f"  [AI-filter] Bloqueado: {p.get('source')}:{p.get('id')} (tags: {post_tags & _AI_KW or 'is_ai=True'})")
                    continue

                uid = f"{p.get('source','?')}:{p.get('id','?')}"
                # Bloqueia se estiver na blacklist permanente
                if uid in blacklist_ids:
                    continue
                # Bloqueia duplicatas DENTRO da mesma busca inteira
                if uid in request_seen:
                    continue
                request_seen.add(uid)
                # normalize_posts() já garante todos os campos com tipos corretos,
                # mas deixa category "" para fontes que não a preenchem (bsky,
                # deviantart) — setdefault não corrige valor vazio, então
                # atribuímos explicitamente para o download ir pra pasta certa.
                if not p.get("category"):
                    p["category"] = cat
                new_posts.append(p)


            novos_db = 0
            known_in_db = 0
            send_posts = new_posts  # fallback: envia todos
            total_unique_count += len(new_posts)

            if new_posts:
                # Agora NÃO salvamos mais no banco (sem histórico inútil)
                # Salvaremos só quando a pessoa Baixar ou Guardar de fato.
                uids_batch = [f"{p.get('source')}:{p.get('id')}" for p in new_posts]
                already_set = await loop.run_in_executor(None, known_uids, uids_batch)
                known_in_db = len(already_set)
                novos_db = len(new_posts) - known_in_db
                send_posts = new_posts

            print(f"  [DEBUG - Busca] Fonte '{src_name}' (Tag '{cat}'):")
            print(f"    - Retornou da internet: {len(new_posts)} artes")
            print(f"    - Já estavam em cache no banco: {known_in_db} artes")
            print(f"    - Mostrando na sua tela agora: {len(send_posts)} artes\n")

            yield {"event": "posts", "data": json.dumps({
                "source":     src_name,
                "cat":        cat,
                "done":       i + 1,
                "total":      len(combos),
                "posts":      send_posts,
                "new_in_db":  novos_db,
                "known_in_db": known_in_db,
            })}
            await asyncio.sleep(0)

        yield {"event": "done", "data": json.dumps({"total_unique": total_unique_count})}


    return EventSourceResponse(generator())


@app.post("/api/download")
async def download(body: dict):
    """
    Baixa as imagens selecionadas (resposta simples, sem streaming).
    Para progresso em tempo real use /api/download-stream.
    """
    posts = body.get("posts", [])
    if not posts:
        return {"downloaded": 0, "message": "Nenhum post recebido."}

    from collections import defaultdict
    by_cat: dict[str, list] = defaultdict(list)
    for p in posts:
        by_cat[p.get("category", "misc")].append(p)

    # Salva os metadados das artes para a Galeria
    try:
        from utils.database import upsert_posts_batch
        upsert_posts_batch(posts)
    except:
        pass

    # await direto: run_download_batch usa asyncio.run(), que crasha
    # dentro de um event loop já em execução (RuntimeError).
    total = 0
    for cat, cat_posts in by_cat.items():
        n = await download_batch(cat_posts, cat)
        total += n

    return {"downloaded": total, "message": f"{total} imagem(ns) baixada(s)."}


@app.post("/api/download-stream")
async def download_stream(body: dict, request: Request):
    """
    Download com SSE: envia progresso por imagem em tempo real.
    Eventos: 'progress' {done, total, ok, filename} | 'done' {downloaded, failed}
    """
    if not HAS_SSE:
        r = await download(body)
        return JSONResponse(r)

    posts = body.get("posts", [])
    if not posts:
        async def _empty():
            yield {"event": "done", "data": json.dumps({"downloaded": 0, "failed": 0})}
        return EventSourceResponse(_empty())

    from collections import defaultdict
    by_cat: dict[str, list] = defaultdict(list)
    for p in posts:
        by_cat[p.get("category", "misc")].append(p)

    # Salva os metadados das artes para a Galeria
    try:
        from utils.database import upsert_posts_batch
        upsert_posts_batch(posts)
    except Exception as e:
        print(f"Erro ao salvar posts no banco: {e}")

    progress_q: asyncio.Queue = asyncio.Queue()

    async def _progress_cb(done, _total, ok_count, msg):
        await progress_q.put({"done": done, "total": _total, "ok": ok_count, "msg": msg})

    async def _run_downloads():
        from utils.downloader import download_batch
        try:
            for cat, cat_posts in by_cat.items():
                await download_batch(cat_posts, cat, on_progress=_progress_cb)
        except Exception as e:
            print(f"  [download-stream] Erro no lote: {e}")
        finally:
            # Sentinel SEMPRE enviado — sem isso o generator ficava travado
            # 30s no timeout quando o download falhava com exceção.
            await progress_q.put(None)

    async def generator():
        loop = asyncio.get_running_loop()
        task = loop.create_task(_run_downloads())
        ok_total = 0
        done_total = 0
        while True:
            if await request.is_disconnected():
                task.cancel(); break
            try:
                item = await asyncio.wait_for(progress_q.get(), timeout=30)
            except asyncio.TimeoutError:
                break
            if item is None:
                break
            ok_total   = item["ok"]
            done_total = item["done"]
            yield {"event": "progress", "data": json.dumps(item)}
        try:
            await asyncio.shield(task)
        except (asyncio.CancelledError, Exception):
            pass  # task cancelada pelo disconnect ou erro já logado
        failed = done_total - ok_total
        yield {"event": "done", "data": json.dumps({"downloaded": ok_total, "failed": failed})}

    return EventSourceResponse(generator())



# Cache simples em memória: url -> (bytes, content_type) (FIFO,
# limitado por nº de entradas E por memória total — imagens HD do
# Pixiv/Danbooru chegam a dezenas de MB cada)
_proxy_cache: dict[str, tuple[bytes, str]] = {}
_PROXY_CACHE_MAX = 200
_PROXY_CACHE_MAX_BYTES = 200 * 1024 * 1024   # 200 MB
_proxy_cache_bytes = 0

def _get_referer(url: str) -> str:
    """Retorna o Referer correto para cada domínio — evita bloqueio de hotlink."""
    if "gelbooru.com" in url:
        return "https://gelbooru.com/"
    if "danbooru.donmai.us" in url or "donmai.us" in url:
        return "https://danbooru.donmai.us/"
    if "safebooru.org" in url:
        return "https://safebooru.org/"
    if "e621.net" in url:
        return "https://e621.net/"
    if "rule34.xxx" in url:
        return "https://rule34.xxx/"
    # Pixiv (i.pximg.net) bloqueia hotlink sem este Referer específico
    if "pximg.net" in url or "pixiv.net" in url:
        return "https://www.pixiv.net/"
    # fallback genérico
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"
    except Exception:
        return "https://danbooru.donmai.us/"


def _fetch_image_sync(url: str) -> tuple[bytes, str]:
    """Busca a imagem de forma síncrona (chamada em thread pool)."""
    # Segurança: só proxia http/https (evita file://, ftp://, etc.)
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL inválida: apenas http/https são permitidos")

    # Segurança (SSRF): bloqueia endereços internos — sem isso, alguém na
    # mesma rede poderia usar o proxy para sondar o roteador/outros hosts.
    import ipaddress, socket
    host = parsed.hostname or ""
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError("URL aponta para endereço interno — bloqueado")
    except socket.gaierror:
        raise ValueError(f"Não foi possível resolver o host: {host}")

    # Cache hit (bytes + content-type corretos)
    if url in _proxy_cache:
        return _proxy_cache[url]

    from config import DANBOORU_LOGIN, DANBOORU_API_KEY

    # Danbooru CDN exige Basic Auth para acesso server-side e aceita Discordbot
    # Gelbooru barra Discordbot, então usamos Mozilla
    ua = "Discordbot/2.0" if "donmai.us" in url else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    headers = {
        "User-Agent":      ua,
        "Referer":         _get_referer(url),
        "Accept":          "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest":  "image",
        "Sec-Fetch-Mode":  "no-cors",
        "Sec-Fetch-Site":  "cross-site",
    }

    # Danbooru CDN exige autenticação Basic Auth para acesso server-side
    auth = None
    if "donmai.us" in url and DANBOORU_LOGIN and DANBOORU_API_KEY:
        auth = (DANBOORU_LOGIN, DANBOORU_API_KEY)

    r = _requests.get(url, headers=headers, auth=auth, timeout=20, stream=True)
    r.raise_for_status()
    content_type = r.headers.get("content-type", "image/jpeg")

    # Lê em chunks de 64KB
    chunks = []
    for chunk in r.iter_content(65536):
        if chunk:
            chunks.append(chunk)
    data = b"".join(chunks)

    # Armazena no cache (remove os mais antigos se estourar itens ou memória)
    global _proxy_cache_bytes
    _proxy_cache[url] = (data, content_type)
    _proxy_cache_bytes += len(data)
    while len(_proxy_cache) > 1 and (
        len(_proxy_cache) > _PROXY_CACHE_MAX
        or _proxy_cache_bytes > _PROXY_CACHE_MAX_BYTES
    ):
        oldest = next(iter(_proxy_cache))
        _proxy_cache_bytes -= len(_proxy_cache.pop(oldest)[0])

    return data, content_type


@app.get("/api/proxy-image")
async def proxy_image(url: str):
    """
    Proxy para imagens: carrega do servidor externo com o Referer correto
    e repassa ao browser. Não bloqueia o event loop e tem cache em memória.
    """
    loop = asyncio.get_running_loop()
    try:
        data, content_type = await loop.run_in_executor(None, _fetch_image_sync, url)
        from fastapi.responses import Response
        return Response(content=data, media_type=content_type,
                        headers={"Cache-Control": "public, max-age=3600"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)



@app.get("/api/thumb")
async def thumb(rel_path: str):
    """
    Serve uma miniatura JPEG (~480px) da imagem baixada, gerando e cacheando
    em downloads/.thumbs/ na primeira vez. Deixa a galeria muito mais leve.
    GIFs são servidos no original (a miniatura perderia a animação).
    """
    from fastapi.responses import FileResponse
    dl_dir = Path(DOWNLOAD_DIR).resolve()
    src = (dl_dir / rel_path).resolve()
    try:
        src.relative_to(dl_dir)
    except ValueError:
        return JSONResponse({"error": "Caminho inválido"}, status_code=400)
    if not src.is_file():
        return JSONResponse({"error": "Arquivo não encontrado"}, status_code=404)
    if src.suffix.lower() == ".gif":
        return FileResponse(src)

    tpath = dl_dir / ".thumbs" / Path(rel_path).parent / (src.stem + ".jpg")
    if not tpath.exists() or tpath.stat().st_mtime < src.stat().st_mtime:
        def _gen():
            from PIL import Image
            tpath.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((480, 8000))
                im.save(tpath, "JPEG", quality=82)
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _gen)
        except Exception:
            return FileResponse(src)   # fallback: serve o original
    return FileResponse(tpath, headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/delete-image")
async def delete_image(body: dict):
    """
    Apaga uma imagem do disco e remove o registro do banco.
    Body: {rel_path: str}  (caminho relativo dentro de downloads/)
    """
    rel_path = body.get("rel_path", "")
    if not rel_path:
        return JSONResponse({"error": "rel_path ausente"}, status_code=400)

    dl_dir   = Path(DOWNLOAD_DIR).resolve()
    file_path = (dl_dir / rel_path).resolve()

    # Segurança: impede path traversal (comparação por componentes de caminho,
    # não por prefixo de string — "downloads_evil" passaria no startswith)
    try:
        file_path.relative_to(dl_dir)
    except ValueError:
        return JSONResponse({"error": "Caminho inválido"}, status_code=400)

    deleted_file = False
    if file_path.exists():
        try:
            file_path.unlink()
            deleted_file = True
            # remove JSON de metadados e thumbnail se existirem
            cat     = file_path.parent.name
            meta_p  = dl_dir / "metadata" / cat / (file_path.stem + ".json")
            if meta_p.exists():
                meta_p.unlink()
            thumb_p = dl_dir / ".thumbs" / cat / (file_path.stem + ".jpg")
            if thumb_p.exists():
                thumb_p.unlink()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # Remove do banco pelo caminho
    from utils.database import _connect
    conn = _connect()
    try:
        conn.execute("DELETE FROM downloads WHERE file_path = ?", (str(file_path),))
        conn.commit()
    finally:
        conn.close()

    return {"deleted": deleted_file, "path": rel_path}


# ── entry point ─────────────────────────────────────────────────────────

def open_browser():
    webbrowser.open("http://localhost:7860")

def _lan_ip() -> str:
    """Descobre o IP local da máquina na rede (pra acessar do celular)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Não envia nada de fato; só força o SO a escolher a interface de saída.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return ""
    finally:
        s.close()

if __name__ == "__main__":
    import logging
    # Suprime o ConnectionResetError do Windows (WinError 10054) — inofensivo,
    # aparece quando o browser fecha conexoes SSE antes do servidor.
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)

    lan = _lan_ip()
    print("=" * 52)
    print("  ArtFinder  —  Interface Visual")
    print("=" * 52)
    print("  Neste PC:    http://localhost:7860")
    if lan:
        print(f"  No celular:  http://{lan}:7860")
        print("  (mesmo Wi-Fi; se nao abrir, libere a porta 7860 no firewall)")
    print("  Pressione Ctrl+C para encerrar.")
    print("=" * 52)
    Timer(1.2, open_browser).start()
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

