# sources/gelbooru.py
"""
Módulo de busca no Gelbooru (gelbooru.com).
API REST — requer conta e API key desde 2023.

Como obter credenciais (gratuito):
1. Crie uma conta em https://gelbooru.com/index.php?page=account&s=register
2. Va em My Account > Options > API Access Credentials
3. Copie user_id e api_key
4. Adicione em config.py: GELBOORU_USER_ID e GELBOORU_API_KEY
"""

import time
import requests
from config import MIN_WIDTH, MIN_HEIGHT, GELBOORU_DELAY, MIN_SCORE, REQUEST_TIMEOUT
from sources.errors import SourceUnavailableError, source_unavailable
try:
    from config import GELBOORU_USER_ID, GELBOORU_API_KEY
except ImportError:
    GELBOORU_USER_ID = ""
    GELBOORU_API_KEY = ""

BASE_URL = "https://gelbooru.com/index.php"

HEADERS = {
    "User-Agent": "ShadowRougeArtFinder/2.0 (personal use; +https://github.com)",
}

# Fallback legado para uso standalone — o app.py passa as tags da categoria
# diretamente via parâmetro tags= de fetch_posts().
CATEGORIES: dict[str, str] = {}

# Tags que indicam arte gerada por IA
AI_TAGS = {
    "ai_generated", "ai-generated", "ai_art", "stable_diffusion",
    "novelai", "nai_diffusion", "midjourney", "dall-e", "dall_e",
    "image_generation", "automated_art", "diffusion_model",
    "generated_by_ai", "aigc"
}

def _normalize_rating(r: str) -> str:
    return {
        "general": "sfw", "sensitive": "sensitive",
        "questionable": "nsfw", "explicit": "nsfw"
    }.get(str(r).lower(), "sfw")


def fetch_posts(category_key: str, max_pages: int = 5, tags: str | None = None,
                direct: str | None = None) -> list[dict]:
    """
    Busca posts no Gelbooru para a categoria informada.

    Args:
        category_key: chave de CATEGORIES
        max_pages: paginas a percorrer (pid 0, 1, 2 ...)
        tags: query booru explícita (passada pelo app.py)
        direct: query final desta fonte (source_tags da categoria)

    Returns:
        Lista de dicts padronizados
    """
    if not GELBOORU_API_KEY:
        raise SourceUnavailableError("Gelbooru: credenciais nao configuradas.")

    tags = direct or tags or CATEGORIES.get(category_key, category_key)  # fallback: usa a key como tags diretamente
    results: list[dict] = []

    for pid in range(max_pages):
        params = {
            "page":     "dapi",
            "s":        "post",
            "q":        "index",
            "json":     1,
            "tags":     tags,
            "limit":    100,
            "pid":      pid,
            "api_key":  GELBOORU_API_KEY,
            "user_id":  GELBOORU_USER_ID,
        }

        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            error = source_unavailable("Gelbooru", e)
            print(f"  [Gelbooru] Erro na pagina {pid}: {error}")
            raise error from e

        # A resposta pode ser lista ou dict com chave "post"
        if isinstance(data, list):
            posts = data
        else:
            posts = data.get("post", [])

        if not posts:
            print(f"  [Gelbooru] Pagina {pid}: sem mais resultados.")
            break

        print(f"  [Gelbooru] Pagina {pid}: {len(posts)} resultados encontrados na API.")
        kept = 0

        for post in posts:
            w = post.get("width") or 0
            h = post.get("height") or 0
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                continue

            score = post.get("score") or 0
            if score < MIN_SCORE:
                continue

            file_url   = post.get("file_url", "")
            sample_url = post.get("sample_url", "") or file_url
            preview_url= post.get("preview_url", "") or sample_url

            if not file_url:
                continue

            tag_str    = post.get("tags", "")
            tag_set    = set(tag_str.lower().split())
            if tag_set & AI_TAGS:
                continue

            post_id    = str(post.get("id", ""))
            raw_rating = post.get("rating", "general")
            post_date  = int(post.get("created", 0) or 0)

            results.append({
                "url":         file_url,       # URL HD para lightbox/download
                "preview_url": sample_url,     # sample (~800px) para o grid — carrega rápido
                "thumb_url":   preview_url,    # thumbnail pequeno
                "page_url":    f"https://gelbooru.com/index.php?page=post&s=view&id={post_id}",
                "width":       w,
                "height":      h,
                "score":       score,
                "source":      "gelbooru",
                "id":          post_id,
                "tags":        tag_str,
                "artist":      "",
                "rating":      _normalize_rating(raw_rating),
                "is_ai":       False,
                "post_date":   post_date,
                "category":    category_key,
            })
            kept += 1

        print(f"  [Gelbooru] Pagina {pid}: {kept}/{len(posts)} artes mantidas apos filtros locais.")
        time.sleep(GELBOORU_DELAY)

    return results
