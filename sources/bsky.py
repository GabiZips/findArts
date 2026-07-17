"""
Módulo de busca no Bluesky (bsky.app).
Requer autenticação usando AT Protocol (com.atproto.server.createSession).
"""

import re
import time
import requests
from config import (
    MIN_WIDTH, MIN_HEIGHT, MIN_SCORE, REQUEST_TIMEOUT,
    BSKY_HANDLE, BSKY_PASSWORD, BSKY_DELAY,
)

# Bluesky API uses bsky.social for generic XRPC requests
AUTH_URL = "https://bsky.social/xrpc/com.atproto.server.createSession"
SEARCH_URL = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"

# Global session token to reuse across requests
_BSKY_TOKEN = None
_BSKY_TOKEN_EXPIRES = 0

CATEGORIES: dict[str, str] = {}

# Map the actual UI category labels to better Bluesky search queries
BSKY_QUERY_MAP: dict[str, str] = {
    "yamato_op": "yamato one piece",
    "perona_op": "perona one piece",
    "nami_op": "nami one piece",
    "jax_circus": "jax the amazing digital circus",
    "evelynn_lol": "evelynn league of legends",
    "shadow_solo": "shadow the hedgehog -rouge -sonic",
    "rouge_solo": "rouge the bat -shadow -sonic",
    "shadow_rouge": "shadow the hedgehog rouge the bat",
    "shadow_sonic": "shadow the hedgehog sonic the hedgehog -rouge",
    "blitz_helluva": "blitzo helluva boss",
    "lucifer_morningstar": "lucifer hazbin hotel",
    "millie_helluva": "millie helluva boss",
    "moxxie_helluva": "moxxie helluva boss",
    "mm_ship": "moxxie millie helluva boss",
    "loona": "loona helluva boss",
    "stolas_helluva": "stolas helluva boss",
    "husk_hazbin": "husk hazbin hotel",
    "fizzarolli_helluva": "fizzarolli helluva boss",
    "alastor_hazbin": "alastor hazbin hotel"
}

def _get_token() -> str:
    global _BSKY_TOKEN, _BSKY_TOKEN_EXPIRES
    now = time.time()
    if _BSKY_TOKEN and now < _BSKY_TOKEN_EXPIRES:
        return _BSKY_TOKEN

    if not BSKY_HANDLE or not BSKY_PASSWORD:
        raise ValueError("Credenciais do Bluesky não configuradas (BSKY_HANDLE / BSKY_PASSWORD)")

    payload = {"identifier": BSKY_HANDLE, "password": BSKY_PASSWORD}
    resp = requests.post(AUTH_URL, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    _BSKY_TOKEN = data["accessJwt"]
    # Token typically valid for a while, set an arbitrary safe refresh of 30 minutes
    _BSKY_TOKEN_EXPIRES = now + 1800 
    return _BSKY_TOKEN


def fetch_posts(category_key: str, max_pages: int = 5, tags: str | None = None,
                direct: str | None = None) -> list[dict]:
    """
    Busca posts no Bluesky que contenham imagens.
    """
    # direct (source_tags da categoria) tem prioridade máxima e é usado
    # como está; depois BSKY_QUERY_MAP; por fim deriva das booru tags
    query = direct or BSKY_QUERY_MAP.get(category_key)
    if not query:
        # Deriva das booru tags explícitas (ou CATEGORIES/key como fallback)
        query = tags or CATEGORIES.get(category_key, category_key)
        query = query.replace("_", " ").replace("(", "").replace(")", "").strip()
    # Adiciona a palavra "art" ou "#art" para maximizar achados? O usuário pode fazer isso, ou podemos deixar a query base.

    try:
        token = _get_token()
    except Exception as e:
        print(f"Erro ao autenticar no Bluesky: {e}")
        return []

    headers = {"Authorization": f"Bearer {token}"}
    results = []
    cursor = None
    kept = 0
    limit = 100

    for _ in range(max_pages):
        params = {"q": query, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        try:
            resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Erro ao buscar no Bluesky ({category_key}): {e}")
            break

        posts = data.get("posts", [])
        if not posts:
            break

        for post in posts:
            embed = post.get("embed", {})
            # Pode estar encadeado como view record etc, mas o searchPosts retorna embed na raiz do view
            if embed.get("$type") != "app.bsky.embed.images#view" or "images" not in embed:
                continue

            score = post.get("likeCount") or 0
            if score < MIN_SCORE:
                continue

            author = post.get("author", {})
            artist = author.get("displayName") or author.get("handle", "unknown")
            post_uri = post.get("uri", "")
            post_id = post_uri.split("/")[-1] if "/" in post_uri else post_uri
            
            # Tags from facets and regex
            tags_list = []
            record = post.get("record", {})
            
            # 1. From facets
            for facet in record.get("facets", []):
                for feature in facet.get("features", []):
                    if feature.get("$type") == "app.bsky.richtext.facet#tag":
                        tag = feature.get("tag", "").strip()
                        if tag and tag not in tags_list:
                            tags_list.append(tag)
                            
            # 2. From text via regex (fallback for missing facets)
            text_content = record.get("text", "")
            if text_content:
                regex_tags = re.findall(r'#(\w+)', text_content)
                for t in regex_tags:
                    if t not in tags_list:
                        tags_list.append(t)
                        
            tags = " ".join(tags_list)

            # Bluesky can have multiple images per post. We extract them all.
            for idx, img in enumerate(embed["images"]):
                url = img.get("fullsize")
                if not url:
                    continue

                aspect = img.get("aspectRatio", {})
                w = aspect.get("width", 0)
                h = aspect.get("height", 0)

                # Skip if too small (some images might not have w/h metadata, assume 0 means unknown and skip)
                if w > 0 and w < MIN_WIDTH:
                    continue
                if h > 0 and h < MIN_HEIGHT:
                    continue

                # Calculate rating based on labels and tags
                rating = "sfw"
                for label in (post.get("labels") or []):
                    val = label.get("val", "").lower()
                    if val in ["porn", "sexual", "nudity", "nsfw", "explicit", "graphic-media"]:
                        rating = "nsfw"
                        break
                
                if rating == "sfw":
                    for t in tags_list:
                        if t.lower() in ["nsfw", "r18", "18+", "rule34", "porn", "smut", "lewd", "nude", "nudity", "crotch"]:
                            rating = "nsfw"
                            break

                uid = f"{post_id}_{idx}" if len(embed["images"]) > 1 else post_id

                # Timestamp original do post (createdAt ISO 8601)
                post_date = 0
                created = record.get("createdAt", "")
                if created:
                    try:
                        from datetime import datetime
                        post_date = int(datetime.fromisoformat(
                            created.replace("Z", "+00:00")).timestamp())
                    except Exception:
                        pass

                results.append({
                    "url":         url,
                    "preview_url": img.get("thumb") or url,
                    "page_url":    f"https://bsky.app/profile/{author.get('handle') or ''}/post/{post_id}",
                    "width":       w,
                    "height":      h,
                    "score":       score,
                    "artist":      artist,
                    "tags":        tags,
                    "source":      "bsky",
                    "id":          uid,
                    "rating":      rating,
                    "is_ai":       False,
                    "post_date":   post_date,
                    "category":    category_key,
                })
                kept += 1

        cursor = data.get("cursor")
        if not cursor:
            break

        time.sleep(BSKY_DELAY)

    print(f"[Bluesky] '{category_key}': {kept} imagens aceitas.")
    return results
