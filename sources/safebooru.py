# sources/safebooru.py
"""
Módulo de busca no Safebooru (safebooru.org).
API identica ao Danbooru — gratuita, sem autenticacao, 100% SFW.
"""
import time
import requests
from config import MIN_WIDTH, MIN_HEIGHT, GELBOORU_DELAY, MIN_SCORE, REQUEST_TIMEOUT

BASE_URL = "https://safebooru.org/index.php"
HEADERS  = {
    "User-Agent": "artFinder/2.0 (personal archiver)",
    "Accept": "application/json",
}

AI_TAGS = {
    "ai_generated", "ai-generated", "stable_diffusion", "novelai",
    "nai_diffusion", "midjourney", "dall-e", "dall_e", "image_generation",
    "automated_art", "diffusion_model", "generated_by_ai", "aigc",
}

CATEGORIES: dict[str, str] = {
    "shadow_solo":  "shadow_the_hedgehog -rouge_the_bat -sonic_the_hedgehog",
    "rouge_solo":   "rouge_the_bat -shadow_the_hedgehog -sonic_the_hedgehog",
    "shadow_rouge": "shadow_the_hedgehog rouge_the_bat",
    "shadow_sonic": "shadow_the_hedgehog sonic_the_hedgehog -rouge_the_bat",
}


def fetch_posts(category_key: str, max_pages: int = 5, tags: str | None = None,
                direct: str | None = None) -> list[dict]:
    # Aceita query final da fonte (direct), tags explícitas do app.py,
    # chave conhecida OU qualquer string como query de tags diretamente
    tags = direct or tags or CATEGORIES.get(category_key, category_key)
    results: list[dict] = []

    for pid in range(max_pages):
        params = {
            "page": "dapi", "s": "post", "q": "index",
            "json": 1, "tags": tags, "limit": 100, "pid": pid,
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            # Safebooru às vezes retorna XML/HTML quando não há resultados
            text = resp.text.strip()
            if not text or text.startswith("<") or text in ("null", "[]", "{}"):
                break  # sem mais resultados

            data = resp.json()
            if isinstance(data, list):
                posts = data
            else:
                posts = data.get("post", [])

            if not posts:
                print(f"  [Safebooru] Pagina {pid}: sem mais resultados.")
                break

            print(f"  [Safebooru] Pagina {pid}: {len(posts)} resultados encontrados na API.")
            kept = 0

        except Exception as e:
            print(f"  [Safebooru] Erro na pagina {pid}: {e}")
            break

        for post in posts:
            w = post.get("width", 0)
            h = post.get("height", 0)
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                continue
            if (post.get("score") or 0) < MIN_SCORE:
                continue

            tag_str = post.get("tags", "")
            if set(tag_str.lower().split()) & AI_TAGS:
                continue

            post_id  = str(post.get("id", ""))
            file_url = post.get("file_url", "")
            if not file_url:
                dir_ = post.get("directory", "")
                img  = post.get("image", "")
                file_url = f"https://safebooru.org/images/{dir_}/{img}" if dir_ and img else ""
            if not file_url:
                continue

            preview = (
                post.get("preview_url")
                or f"https://safebooru.org/thumbnails/{post.get('directory','')}/thumbnail_{post.get('image','')}"
            )

            results.append({
                "url":         file_url,
                "preview_url": preview,
                "page_url":    f"https://safebooru.org/index.php?page=post&s=view&id={post_id}",
                "width":       w, "height": h,
                "score":       post.get("score", 0),
                "source":      "safebooru",
                "id":          post_id,
                "tags":        tag_str,
                "artist":      "",
                "rating":      "sfw",
                "is_ai":       False,
                "category":    category_key,
            })
            kept += 1

        print(f"  [Safebooru] Pagina {pid}: {kept}/{len(posts)} artes mantidas apos filtros locais.")
        time.sleep(GELBOORU_DELAY)

    return results
