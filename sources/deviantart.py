# sources/deviantart.py
"""
Módulo de busca no DeviantArt via API OAuth2.
Registro gratuito em: https://www.deviantart.com/developers/
Requer DEVIANTART_CLIENT_ID e DEVIANTART_CLIENT_SECRET em config.py.

Nota: O app pode ficar como "Unpublished" — funciona normalmente para uso pessoal
com o fluxo client_credentials (não requer login de usuário).

Estratégia de busca:
- A API não tem endpoint de busca por texto livre.
- Usamos /browse/tags (busca por tag) e /browse/newest para cada tag relevante.
"""

import time
import requests
from config import (
    DEVIANTART_CLIENT_ID, DEVIANTART_CLIENT_SECRET,
    DEVIANTART_DELAY, MIN_SCORE, MIN_WIDTH, MIN_HEIGHT, REQUEST_TIMEOUT
)

AI_TAGS = {
    "ai_generated", "ai-generated", "ai_art", "stable_diffusion",
    "novelai", "nai_diffusion", "midjourney", "dall-e", "dall_e",
    "image_generation", "automated_art", "diffusion_model",
    "generated_by_ai", "aigc", "aiart", "stablediffusion",
    "ai generated", "artificial intelligence art"
}

TOKEN_URL = "https://www.deviantart.com/oauth2/token"
BASE_URL  = "https://www.deviantart.com/api/v1/oauth2"

_token_cache: dict = {"token": None, "expires_at": 0}

# Tags relevantes por categoria
CATEGORY_TAGS: dict[str, list[str]] = {
    "shadow_solo":  ["shadowthehedgehog", "shadow_the_hedgehog", "shadow hedgehog"],
    "rouge_solo":   ["rougethehat", "rouge_the_bat", "rouge bat sonic"],
    "shadow_rouge": ["shadouge", "shadow rouge", "shadowandrouge"],
    "shadow_sonic": ["sonadow", "shadow sonic", "shadowandsonic"],
}


def _get_token() -> str | None:
    """Obtém (ou reutiliza) o access token via client_credentials."""
    import time as t

    if _token_cache["token"] and t.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    if not DEVIANTART_CLIENT_ID or not DEVIANTART_CLIENT_SECRET:
        return None

    try:
        resp = requests.post(TOKEN_URL, data={
            "grant_type":    "client_credentials",
            "client_id":     DEVIANTART_CLIENT_ID,
            "client_secret": DEVIANTART_CLIENT_SECRET,
        }, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            print(f"  [DeviantArt] Erro OAuth: {data.get('error_description', data['error'])}")
            return None

        _token_cache["token"] = data.get("access_token")
        _token_cache["expires_at"] = t.time() + data.get("expires_in", 3600)
        return _token_cache["token"]
    except Exception as e:
        print(f"  [DeviantArt] Falha ao obter token: {e}")
        return None


def _fetch_by_tag(tag: str, token: str, offset: int = 0, limit: int = 24) -> list[dict]:
    """Busca deviations por tag via /browse/tags."""
    headers = {"Authorization": f"Bearer {token}"}
    results = []

    params = {
        "tag":    tag,
        "offset": offset,
        "limit":  limit,
        # A API retorna 403 em tags que têm conteúdo sensível (ex: rouge_the_bat)
        # se passarmos mature_content=false ou omitirmos.
        # Passamos true para a requisição passar, e filtramos os +18 no Python.
        "mature_content": "true",
    }

    try:
        resp = requests.get(
            f"{BASE_URL}/browse/tags",
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [DeviantArt] Erro ao buscar tag '{tag}': {e}")
        return []

    for dev in data.get("results", []):
        if dev.get("is_deleted") or dev.get("is_mature"):
            continue

        # A resposta de /browse/tags tem estrutura diferente de /browse/search
        content = dev.get("content") or dev.get("preview") or {}
        url = content.get("src")
        w   = content.get("width", 0)
        h   = content.get("height", 0)

        # Fallback: thumbs
        if not url:
            thumbs = dev.get("thumbs", [])
            if thumbs:
                best_thumb = sorted(thumbs, key=lambda x: x.get("width") or 0, reverse=True)[0]
                url = best_thumb.get("src")
                w   = best_thumb.get("width", 0)
                h   = best_thumb.get("height", 0)

        if not url:
            continue

        if w and h and (w < MIN_WIDTH or h < MIN_HEIGHT):
            continue

        stats = dev.get("stats", {})
        favourites = stats.get("favourites") or 0

        if favourites < MIN_SCORE:
            continue

        # Filtro de IA: verifica tags e título/descrição
        dev_tags = set(t.lower() for t in dev.get("tags", []))
        dev_title = dev.get("title", "").lower()
        ai_in_title = any(kw in dev_title for kw in ("ai", "stable diffusion", "midjourney", "novelai", "dall-e"))
        if dev_tags & AI_TAGS or ai_in_title:
            continue

        author = dev.get("author", {}).get("username", "")
        results.append({
            "url":      url,
            "page_url": dev.get("url", ""),
            "width":    w,
            "height":   h,
            "score":    favourites,
            "source":   "deviantart",
            "id":       str(dev.get("deviationid", dev.get("deviation_id", ""))),
            "tags":     tag,
            "artist":   author,
            "rating":   "sfw",  # is_mature já foi filtrado acima
            "post_date": int(dev.get("published_time") or 0),
        })

    return results


def fetch_posts(category_key: str, max_pages: int = 5, tags: str | None = None,
                direct: str | None = None) -> list[dict]:
    """
    Busca deviations no DeviantArt para a categoria via tags.

    Args:
        category_key: chave de CATEGORY_TAGS
        max_pages: páginas por tag (24 itens cada)
        tags: query booru explícita (passada pelo app.py) — antes este módulo
              derivava só da category_key e ignorava as tags reais da categoria
        direct: tag final do DeviantArt (source_tags da categoria)

    Returns:
        Lista de dicts padronizados
    """
    token = _get_token()
    if not token:
        print("  [DeviantArt] Token indisponivel — verifique as credenciais. Pulando.")
        return []

    if direct:
        # Tag final do DeviantArt (source_tags da categoria)
        search_tags = [direct]
    elif category_key in CATEGORY_TAGS:
        search_tags = CATEGORY_TAGS[category_key]
    else:
        # Fallback para categorias personalizadas (igual às outras fontes):
        # deriva tags DeviantArt da query booru — remove exclusões ("-tag"),
        # parênteses de desambiguação e underscores.
        import re as _re
        base = tags or category_key
        derived = []
        for raw in base.split():
            if raw.startswith("-"):
                continue
            clean = _re.sub(r"[()_]", " ", raw)
            clean = _re.sub(r"\s+", " ", clean).strip()
            if clean and clean not in derived:
                derived.append(clean)
        search_tags = derived or [base]
    results: list[dict] = []

    for tag in search_tags:
        kept = 0
        total_retrieved = 0
        for page in range(max_pages):
            offset = page * 24
            posts = _fetch_by_tag(tag, token, offset=offset)
            total_retrieved += 24
            results.extend(posts)
            kept += len(posts)

            if len(posts) < 24:
                break   # sem mais resultados para esta tag

        print(f"  [DeviantArt] {tag}: {kept} artes mantidas de {total_retrieved} buscadas.")
        time.sleep(DEVIANTART_DELAY)

    # Remover duplicatas por ID
    seen: set[str] = set()
    unique = []
    for p in results:
        if p["id"] and p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)

    return unique
