# sources/danbooru.py
"""
Módulo de busca no Danbooru (danbooru.donmai.us).
API pública REST — sem autenticação para uso básico (20 results/página).
Com conta gratuita o limite sobe para 200.
"""

import time
import requests
from config import (
    MIN_WIDTH, MIN_HEIGHT, DANBOORU_DELAY, MIN_SCORE, REQUEST_TIMEOUT,
    DANBOORU_LOGIN, DANBOORU_API_KEY,
)
from sources.errors import source_unavailable

HEADERS = {
    "User-Agent": "ShadowRougeArtFinder/2.0 (personal use; +https://github.com)",
}

BASE_URL = "https://danbooru.donmai.us/posts.json"

# Tags que indicam arte gerada por IA (lista oficial do Danbooru)
AI_TAGS = {
    "ai_generated", "ai-generated", "ai_art", "stable_diffusion",
    "novelai", "nai_diffusion", "midjourney", "dall-e", "dall_e",
    "image_generation", "automated_art", "diffusion_model",
    "generated_by_ai", "aigc"
}

# Mapeamento de rating do Danbooru para padrao interno
# g=geral(SFW), s=sensivel, q=questionavel, e=explicito(NSFW)
def _normalize_rating(r: str) -> str:
    return {"g": "sfw", "s": "sensitive", "q": "nsfw", "e": "nsfw"}.get(r, "sfw")

# Fallback legado para uso standalone — o app.py passa as tags da categoria
# diretamente via parâmetro tags= de fetch_posts().
CATEGORIES: dict[str, str] = {}


def fetch_posts(category_key: str, max_pages: int = 5, tags: str | None = None,
                direct: str | None = None) -> list[dict]:
    """
    Busca posts no Danbooru para a categoria informada.

    Args:
        category_key: chave de CATEGORIES (ex: "shadow_solo")
        max_pages: quantidade de páginas a percorrer
        tags: query booru explícita — passada pelo app.py; evita o antigo
              hack de injetar em CATEGORIES (era race condition com buscas
              simultâneas de duas abas/dispositivos)
        direct: query final desta fonte (source_tags da categoria) — usada
                como está, sem nenhuma conversão

    Returns:
        Lista de dicts com campos: url, width, height, score, source, id, tags
    """
    tags = direct or tags or CATEGORIES.get(category_key, category_key)  # fallback: usa a key como tags diretamente
    # rating:g,s requer autenticação no Danbooru; sem conta usa só as tags.
    # Se tiver conta, descomente a linha abaixo e configure DANBOORU_LOGIN/DANBOORU_API_KEY.
    # if SAFE_ONLY:
    #     tags += " rating:g,s"

    results: list[dict] = []

    # Com credenciais configuradas usa Basic Auth: limite sobe de 20 → 200/página
    auth = (DANBOORU_LOGIN, DANBOORU_API_KEY) if (DANBOORU_LOGIN and DANBOORU_API_KEY) else None
    limit = 200 if auth else 20

    for page in range(1, max_pages + 1):
        params = {
            "tags":  tags,
            "limit": limit,
            "page":  page,
        }
        # Nota: rating:g,s requer autenticação. Sem conta, omitimos o filtro de rating.

        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, auth=auth, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            error = source_unavailable("Danbooru", e)
            print(f"  [Danbooru] Erro na página {page}: {error}")
            raise error from e

        if not data:
            print(f"  [Danbooru] Pagina {page}: sem mais resultados.")
            break   # sem mais resultados

        print(f"  [Danbooru] Pagina {page}: {len(data)} resultados encontrados na API.")
        kept = 0

        for post in data:
            w = post.get("image_width") or 0
            h = post.get("image_height") or 0
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                continue

            score = post.get("score") or 0
            if score < MIN_SCORE:
                continue

            tag_string = post.get("tag_string", "")
            tag_set = set(tag_string.lower().split())

            if tag_set & AI_TAGS:
                continue

            raw_rating = post.get("rating", "g")
            post_id = str(post.get("id", ""))

            # Timestamp original do post
            created_raw = post.get("created_at", "")
            post_date = 0
            if created_raw:
                try:
                    from datetime import datetime, timezone
                    # Danbooru retorna ISO 8601: "2023-04-12T05:40:00.000-04:00"
                    dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    post_date = int(dt.astimezone(timezone.utc).timestamp())
                except Exception:
                    post_date = 0

            # large_file_url = sample JPG (~800px, rapido para o grid)
            # file_url       = original PNG/JPG (HD, para lightbox/download)
            file_url  = post.get("file_url") or post.get("large_file_url", "")
            large_url = post.get("large_file_url") or file_url

            if not file_url:
                continue

            results.append({
                "url":         file_url,    # HD para lightbox/download
                "preview_url": large_url,  # sample para o grid (rapido)
                "page_url":    f"https://danbooru.donmai.us/posts/{post_id}",
                "width":       w,
                "height":      h,
                "score":       score,
                "source":      "danbooru",
                "id":          post_id,
                "tags":        tag_string,
                "artist":      post.get("tag_string_artist", ""),
                "rating":      _normalize_rating(raw_rating),
                "is_ai":       False,
                "post_date":   post_date,
                "category":    category_key,
            })
            kept += 1

        print(f"  [Danbooru] Pagina {page}: {kept}/{len(data)} artes mantidas apos filtros locais.")
        time.sleep(DANBOORU_DELAY)

    return results
