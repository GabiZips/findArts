# utils/normalize.py
"""
Camada de normalização de posts.

Cada fonte (danbooru, gelbooru, tumblr, ...) monta o dicionário do post do seu
próprio jeito, e às vezes uma API devolve `null` num campo numérico. Isso já
causou crash em ordenações/comparações (ex.: `None < 0`).

`normalize_post()` recebe o dicionário cru de qualquer fonte e devolve um dict
com o MESMO esquema e tipos garantidos. Passar todo post por aqui elimina essa
classe inteira de bug e torna seguro adicionar fontes novas.
"""

from typing import Any

# Ratings aceitos (em minúsculo). Qualquer outro vira "sfw".
_RATINGS = {
    "sfw", "safe", "general", "g",
    "sensitive", "s",
    "questionable", "q",
    "nsfw", "explicit", "e",
}


def _to_int(value: Any, default: int = 0) -> int:
    """Converte para int de forma tolerante. None/''/lixo viram `default`."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _to_str(value: Any, default: str = "") -> str:
    """Converte para str. None vira `default`."""
    if value is None:
        return default
    return str(value)


def normalize_post(raw: dict, source: str = "") -> dict:
    """Padroniza um post cru de qualquer fonte para o esquema canônico.

    Esquema garantido (com tipos):
        source       str   (minúsculo)
        id           str
        url          str
        preview_url  str
        page_url     str
        artist       str
        score        int
        width        int
        height       int
        rating       str   (um de _RATINGS, default "sfw")
        tags         str
        is_ai        bool
        category     str
        post_date    int

    Campos extras presentes no `raw` são preservados.
    """
    if not isinstance(raw, dict):
        return raw

    p = dict(raw)  # preserva campos extras

    src = (source or p.get("source") or "").strip().lower()

    rating = (_to_str(p.get("rating"), "sfw")).strip().lower()
    if rating not in _RATINGS:
        rating = "sfw"

    url = _to_str(p.get("url"))

    p["source"]      = src
    p["id"]          = _to_str(p.get("id") or p.get("post_id"))
    p["url"]         = url
    p["preview_url"] = _to_str(p.get("preview_url")) or url
    p["page_url"]    = _to_str(p.get("page_url"))
    p["artist"]      = _to_str(p.get("artist"))
    p["score"]       = _to_int(p.get("score"))
    p["width"]       = _to_int(p.get("width"))
    p["height"]      = _to_int(p.get("height"))
    p["rating"]      = rating
    p["tags"]        = _to_str(p.get("tags"))
    p["is_ai"]       = bool(p.get("is_ai", False))
    p["category"]    = _to_str(p.get("category"))
    p["post_date"]   = _to_int(p.get("post_date"))

    return p


def normalize_posts(posts: list, source: str = "") -> list:
    """Normaliza uma lista de posts. Itens não-dict são ignorados."""
    out = []
    for raw in posts or []:
        if isinstance(raw, dict):
            out.append(normalize_post(raw, source))
    return out
