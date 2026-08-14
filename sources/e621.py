# sources/e621.py
"""
Módulo de busca no e621 (e621.net).
API publica REST compativel com Danbooru — sem autenticacao para acesso basico.
Exige User-Agent com email conforme politica do site.

e621 e especialmente bom para arte Sonic/Shadow/Rouge pois a comunidade
furyy/sonic tem tagging muito precisa e ampla.

Rating:
    s = safe (SFW)
    q = questionable (sensivel)
    e = explicit (NSFW)
"""

import time
import requests
from config import MIN_WIDTH, MIN_HEIGHT, DANBOORU_DELAY, MIN_SCORE, REQUEST_TIMEOUT
from sources.errors import source_unavailable

BASE_URL = "https://e621.net/posts.json"

HEADERS = {
    # e621 exige User-Agent identificavel conforme: https://e621.net/wiki_pages/api
    "User-Agent": "artFinder/2.0 (personal archiver; contact via github)",
}

AI_TAGS = {
    "ai_generated", "ai-generated", "stable_diffusion", "novelai",
    "nai_diffusion", "midjourney", "dall-e", "dall_e", "image_generation",
    "automated_art", "diffusion_model", "generated_by_ai", "aigc",
    "conditionally_nsfw",  # tag especifica do e621
}

CATEGORIES: dict[str, str] = {
    "shadow_solo":  "shadow_the_hedgehog -rouge_the_bat -sonic_the_hedgehog",
    "rouge_solo":   "rouge_the_bat -shadow_the_hedgehog -sonic_the_hedgehog",
    "shadow_rouge": "shadow_the_hedgehog rouge_the_bat",
    "shadow_sonic": "shadow_the_hedgehog sonic_the_hedgehog -rouge_the_bat",
    "blitz_(helluva_boss)": "blitzo_(helluva_boss)",
    "lucifer_morningstar_(hazbin_hotel)": "lucifer_(hazbin_hotel)"
}

def _normalize_rating(r: str) -> str:
    return {"s": "sfw", "q": "sensitive", "e": "nsfw"}.get(r, "sfw")


def fetch_posts(category_key: str, max_pages: int = 5, tags: str | None = None,
                direct: str | None = None) -> list[dict]:
    """
    Busca posts no e621 para a categoria informada.

    Args:
        category_key: chave de CATEGORIES
        max_pages: paginas a percorrer (max 320 por pagina no e621)
        tags: query booru explícita (passada pelo app.py)
        direct: query final desta fonte (source_tags da categoria)

    Returns:
        Lista de dicts padronizados
    """
    tags = direct or tags or CATEGORIES.get(category_key, category_key)  # fallback: usa a key como tags diretamente
    results: list[dict] = []

    for page in range(1, max_pages + 1):
        params = {
            "tags":  tags,
            "limit": 100,
            "page":  page,
        }

        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            error = source_unavailable("e621", e)
            print(f"  [e621] Erro na pagina {page}: {error}")
            raise error from e

        posts = data.get("posts", [])
        if not posts:
            print(f"  [e621] Pagina {page}: sem mais resultados.")
            break

        print(f"  [e621] Pagina {page}: {len(posts)} resultados encontrados na API.")
        kept = 0

        for post in posts:
            # e621 tem estrutura diferente: file.url, sample.url, preview.url
            file_info    = post.get("file", {})
            sample_info  = post.get("sample", {})
            preview_info = post.get("preview", {})

            url = file_info.get("url")
            if not url:
                continue

            w = file_info.get("width") or 0
            h = file_info.get("height") or 0
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                continue

            score = (post.get("score") or {}).get("total") or 0
            if score < MIN_SCORE:
                continue

            # Tags no e621 sao separadas por categoria em dicts
            tag_dict = post.get("tags", {})
            all_tags: list[str] = []
            for tag_list in tag_dict.values():
                all_tags.extend(tag_list)
            tag_str = " ".join(all_tags)
            tag_set = set(t.lower() for t in all_tags)

            # Filtro anti-IA
            if tag_set & AI_TAGS:
                continue

            raw_rating = post.get("rating", "s")
            post_id    = str(post.get("id", ""))
            created_raw = post.get("created_at", "")
            post_date = 0
            if isinstance(created_raw, str) and created_raw:
                try:
                    from datetime import datetime
                    # Formato e621: '2022-09-02T01:54:33.407-04:00' ou similar
                    # Vamos ignorar os decimais e timezone pra simplificar o parse caso python < 3.11
                    clean_date = created_raw.split('.')[0][:19]
                    post_date = int(datetime.fromisoformat(clean_date).timestamp())
                except:
                    pass

            # Artistas
            artists = tag_dict.get("artist", [])
            artist  = ", ".join(a for a in artists if a not in ("conditional_dnp", "avoid_posting"))

            results.append({
                "url":         url,
                "preview_url": sample_info.get("url") or preview_info.get("url") or url,
                "page_url":    f"https://e621.net/posts/{post_id}",
                "width":       w,
                "height":      h,
                "score":       score,
                "source":      "e621",
                "id":          post_id,
                "tags":        tag_str,
                "artist":      artist,
                "rating":      _normalize_rating(raw_rating),
                "is_ai":       False,
                "post_date":   int(post_date),
                "category":    category_key,
            })
            kept += 1

        print(f"  [e621] Pagina {page}: {kept}/{len(posts)} artes mantidas apos filtros locais.")
        time.sleep(DANBOORU_DELAY)

    return results
