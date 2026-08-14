# sources/tumblr.py
"""
Módulo de busca no Tumblr via API pública (v2).
Requer TUMBLR_API_KEY em config.py.
Para busca por POPULARIDADE, configure também as chaves OAuth
rodando: python setup_tumblr_oauth.py
"""

import re
import hmac
import time
import random
import string
import hashlib
import base64
import requests
from sources.errors import SourceUnavailableError, source_unavailable
import urllib.parse
from config import (
    TUMBLR_API_KEY, TUMBLR_DELAY, MIN_WIDTH, MIN_HEIGHT, MIN_SCORE, REQUEST_TIMEOUT,
    TUMBLR_CONSUMER_SECRET, TUMBLR_OAUTH_TOKEN, TUMBLR_OAUTH_TOKEN_SECRET,
)

AI_TAGS = {
    "ai_generated", "ai-generated", "ai_art", "stable_diffusion",
    "novelai", "nai_diffusion", "midjourney", "dall-e", "dall_e",
    "image_generation", "automated_art", "diffusion_model",
    "generated_by_ai", "aigc", "aiart", "ai art", "stablediffusion",
    "artificialintelligence", "aiillustration"
}

BASE_URL = "https://api.tumblr.com/v2/tagged"

# Tags especiais por categoria (aliases e ships que o Tumblr usa diferente dos boorus).
# Se a categoria não está aqui, o sistema usa as tags do user_categories.json diretamente.
# IMPORTANTE: o app.py passa as tags do booru (ex: "yamato_(one_piece)") como category_key.
CATEGORY_TAGS: dict[str, list[str]] = {

    # ── Sonic ──────────────────────────────────────────────────────────────
    "shadow_the_hedgehog":                          ["shadow the hedgehog"],
    "rouge_the_bat":                                ["rouge the bat"],
    "shadow_the_hedgehog rouge_the_bat":            ["shadouge"],
    "shadow_the_hedgehog sonic_the_hedgehog":       ["sonadow"],
    "sonic_the_hedgehog":                           ["sonic the hedgehog"],

    # ── Helluva Boss ───────────────────────────────────────────────────────
    "loona_(helluva_boss)":                         ["loona helluva boss", "loona"],
    "blitz_(helluva_boss)":                         ["blitzo", "blitz helluva boss", "blitzo helluva boss"],
    "millie_(helluva_boss)":                        ["millie helluva boss"],
    "moxxie_(helluva_boss)":                        ["moxxie helluva boss"],
    "fizzarolli_(helluva_boss)":                    ["fizzarolli", "fizzarolli helluva boss"],
    "stolas_(helluva_boss)":                        ["stolas", "stolas helluva boss"],
    "millie_(helluva_boss) moxxie_(helluva_boss)":  ["moxxie x millie", "millie x moxxie", "m&m helluva boss", "moxlie"],

    # ── Hazbin Hotel ───────────────────────────────────────────────────────
    "alastor_(hazbin_hotel)":                       ["alastor", "alastor hazbin hotel"],
    "angel_dust":                                   ["angel dust", "angel dust hazbin hotel"],
    "husk_(hazbin_hotel)":                          ["husk hazbin hotel", "husk"],
    "lucifer_morningstar_(hazbin_hotel)":           ["lucifer morningstar", "lucifer hazbin hotel"],
    "husk_(hazbin_hotel) angel_dust":               ["huskerdust", "husk x angel dust", "angel dust x husk"],

    # ── Ships ──────────────────────────────────────────────────────────────
    "catnap_(poppy_playtime) dogday_(poppy_playtime)": ["catnap x dogday", "dogday x catnap", "catnap dogday", "poppy playtime ship"],

    # "yamato" sozinho é genérico, prefira com contexto
    "yamato_(one_piece)":                           ["yamato one piece", "yamato"],
    "perona_(one_piece)":                           ["perona one piece", "perona"],
    # "nami" sozinho é muito genérico — usa com contexto
    "nami_(one_piece)":                             ["nami one piece", "nami"],

    # "jax" sozinho é extremamente genérico
    "jax_(the_amazing_digital_circus)":             ["jax the amazing digital circus", "jax tadc", "tadc jax"],

    # ── League of Legends ──────────────────────────────────────────────────
    "evelynn_(league_of_legends)":                  ["evelynn", "evelynn league of legends", "evelynn lol"],
    "miss_fortune_(league_of_legends)":             ["miss fortune", "miss fortune lol"],

    # High School DxD
    "rias_gremory":                                 ["rias gremory", "rias"],
    # Cowboy Bebop
    "faye_valentine":                               ["faye valentine", "faye bebop"],
    # Re:Zero
    "echidna_(re:zero)":                            ["echidna re zero", "echidna rezero", "echidna witch of greed"],

    # ── Jogos ──────────────────────────────────────────────────────────────
    "chun-li":                                      ["chun li", "chun-li", "chun li street fighter"],
    "ada_wong":                                     ["ada wong", "ada resident evil"],
    "jill_valentine":                               ["jill valentine", "jill resident evil"],
}

# Fallback legado para uso standalone — o app.py passa as booru tags da
# categoria diretamente via parâmetro tags= de fetch_posts().
CATEGORIES: dict[str, str] = {}


def _tags_from_category_key(category_key: str, booru_override: str | None = None) -> list[str]:
    """
    Resolve uma category_key para lista de tags do Tumblr.
    Fluxo de resolução (prioridade decrescente):
      1. Verifica CATEGORY_TAGS usando as booru tags (explícitas ou de CATEGORIES)
      2. Verifica CATEGORY_TAGS usando a category_key diretamente
      3. Deriva automaticamente das booru tags (remove parênteses, troca _ por espaço)
    """
    # 1. Booru tags explícitas do app.py, com fallback para CATEGORIES/key
    booru_tags = booru_override or CATEGORIES.get(category_key, category_key)

    # 2. Tenta encontrar no mapa de tags do Tumblr pela booru tag
    if booru_tags in CATEGORY_TAGS:
        return CATEGORY_TAGS[booru_tags]

    # 3. Tenta pela category_key diretamente
    if category_key in CATEGORY_TAGS:
        return CATEGORY_TAGS[category_key]

    # 4. Deriva automaticamente das booru tags
    # Remove parênteses de desambiguação: "millie_(helluva_boss)" → "millie"
    # Substitui underscores por espaços
    derived = []
    for raw_tag in booru_tags.split():
        if raw_tag.startswith("-"):
            continue  # ignora tags de exclusão
        # Mantém o contexto da série em vez de descartá-lo:
        # "vex_(league)" -> "vex league" (busca mais específica, menos ruído)
        clean = re.sub(r"\s+", " ", raw_tag.replace("(", " ").replace(")", " ").replace("_", " ")).strip()
        if clean and clean not in derived:
            derived.append(clean)

    return derived if derived else [booru_tags.replace("_", " ")]


def _extract_images_from_post(post: dict, min_w: int, min_h: int) -> list[dict]:
    """
    Extrai todas as imagens de um post Tumblr, tanto de posts normais (NPF content)
    quanto de reblogs (trail) e do formato legado (photos).
    Lida com layouts em grade (photo sets) e posts sem dimensão informada.
    """
    found = []

    def _best_media(media: list) -> dict:
        """Escolhe a mídia de maior resolução da lista."""
        if not media:
            return {}
        return max(media, key=lambda m: (m.get("width") or 0) * (m.get("height") or 0))

    def _process_blocks(blocks: list):
        for block in blocks:
            if block.get("type") != "image":
                continue
            media = block.get("media", [])
            if not media:
                continue
            best = _best_media(media)
            if not best:
                continue
            w = best.get("width", 0)
            h = best.get("height", 0)
            # Se dimensões não informadas (w=0/h=0), aceita o post mas usa 0
            # Só rejeita se temos certeza que é pequeno demais
            if w > 0 and h > 0:
                if w < (min_w - 300) or h < (min_h - 300):
                    continue
            url = best.get("url", "")
            if not url:
                continue
            valid_previews = [m for m in media if m.get("width", 0) >= 400]
            preview = valid_previews[-1]["url"] if valid_previews else url
            found.append({"url": url, "preview_url": preview, "w": w, "h": h})

    # 1. Conteúdo direto do post (NPF)
    _process_blocks(post.get("content", []))

    # 2. Trail (reblogs) — cada item do trail pode ter seu próprio content
    for trail_item in post.get("trail", []):
        _process_blocks(trail_item.get("content", []))

    # 3. Formato legado (posts antigos não convertidos para NPF)
    if not found:
        for photo in post.get("photos", []):
            alt_sizes = photo.get("alt_sizes", [])
            if not alt_sizes:
                continue
            best = max(alt_sizes, key=lambda x: (x.get("width") or 0) * (x.get("height") or 0))
            w, h = best.get("width", 0), best.get("height", 0)
            if w > 0 and h > 0:
                if w < (min_w - 300) or h < (min_h - 300):
                    continue
            url = best.get("url", "")
            if not url:
                continue
            valid_previews = [m for m in alt_sizes if m.get("width", 0) >= 400]
            preview = valid_previews[-1]["url"] if valid_previews else url
            found.append({"url": url, "preview_url": preview, "w": w, "h": h})

    return found


def _has_oauth() -> bool:
    return bool(TUMBLR_API_KEY and TUMBLR_CONSUMER_SECRET and TUMBLR_OAUTH_TOKEN and TUMBLR_OAUTH_TOKEN_SECRET)


def _oauth_header(method: str, url: str, extra_params: dict | None = None) -> str:
    """Gera o header Authorization OAuth 1.0a para uma requisição."""
    params = extra_params or {}
    oauth_params = {
        "oauth_consumer_key":     TUMBLR_API_KEY,
        "oauth_token":            TUMBLR_OAUTH_TOKEN,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_nonce":            "".join(random.choices(string.ascii_letters + string.digits, k=32)),
        "oauth_version":          "1.0",
    }
    all_params = {**params, **oauth_params}
    sorted_params = sorted(all_params.items())
    param_str = "&".join(
        f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted_params
    )
    base = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(param_str, safe=""),
    ])
    key = f"{urllib.parse.quote(TUMBLR_CONSUMER_SECRET, safe='')}&{urllib.parse.quote(TUMBLR_OAUTH_TOKEN_SECRET, safe='')}"
    sig = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = sig
    return "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(str(v), safe="")}"'
        for k, v in sorted(oauth_params.items())
    )


# ── Amostragem temporal ────────────────────────────────────────────────────
# O /tagged do Tumblr só retorna ordem cronológica (não há sort por notas na
# API v2). Para achar os posts FAMOSOS de qualquer época — não só os recentes —
# buscamos várias janelas de tempo ("before" = N dias atrás) e ordenamos
# localmente por note_count.
_SAMPLE_OFFSETS_DAYS = [0, 30, 90, 180, 365, 545, 730, 1095, 1460, 1825]


def _sample_offsets(n: int) -> list[int]:
    """Escolhe n offsets espalhados pela lista (sempre inclui 0 = recente)."""
    if n >= len(_SAMPLE_OFFSETS_DAYS):
        return list(_SAMPLE_OFFSETS_DAYS)
    if n <= 1:
        return [0]
    step = (len(_SAMPLE_OFFSETS_DAYS) - 1) / (n - 1)
    idxs = sorted({round(i * step) for i in range(n)})
    return [_SAMPLE_OFFSETS_DAYS[i] for i in idxs]


def fetch_posts(category_key: str, max_pages: int = 5, tags: str | None = None,
                direct: str | None = None) -> list[dict]:
    """
    Busca posts de foto no Tumblr para a categoria.
    Cada "página" amostra uma janela de tempo diferente (agora, -1 mês,
    -6 meses, -1 ano...) e o resultado final é ordenado por popularidade
    (note_count), então os posts mais famosos de qualquer época aparecem.
    """
    if not TUMBLR_API_KEY:
        raise SourceUnavailableError("Tumblr: chave de API nao configurada.")

    # direct = uma tag final do Tumblr (não passa pela derivação booru)
    search_tags = [direct] if direct else _tags_from_category_key(category_key, tags)
    results: list[dict] = []
    seen_ids: set[str] = set()
    now = int(time.time())

    # ── Busca via /tagged com amostragem temporal ───────────────────────────
    for tag in search_tags:
        for page_idx, offset_days in enumerate(_sample_offsets(max_pages), start=1):
            params: dict = {
                "tag":     tag,
                "api_key": TUMBLR_API_KEY,
                "limit":   20,
                "npf":     "true",
            }
            if offset_days > 0:
                params["before"] = now - offset_days * 86400

            try:
                resp = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                posts = resp.json().get("response", [])
            except Exception as e:
                error = source_unavailable("Tumblr", e)
                print(f"  [Tumblr] Erro ao buscar tag '{tag}': {error}")
                raise error from e

            _win = "recente" if offset_days == 0 else f"-{offset_days}d"
            if not posts:
                print(f"  [Tumblr] Tag '{tag}' janela {_win}: sem resultados.")
                time.sleep(TUMBLR_DELAY)
                continue

            print(f"  [Tumblr] Tag '{tag}' janela {_win}: {len(posts)} resultados encontrados na API.")
            kept = 0

            for post in posts:
                note_count = post.get("note_count") or 0
                if note_count < MIN_SCORE:
                    continue

                post_id  = str(post.get("id", ""))
                blog     = post.get("blog_name", "")
                ptags    = " ".join(post.get("tags", []))

                post_tag_set = set(t.lower().replace(" ", "_") for t in post.get("tags", []))
                post_tag_set |= set(t.lower() for t in post.get("tags", []))
                if post_tag_set & AI_TAGS:
                    continue

                images = _extract_images_from_post(post, MIN_WIDTH, MIN_HEIGHT)

                for idx, img in enumerate(images):
                    uid = f"{post_id}_{idx}" if idx > 0 else post_id
                    if uid in seen_ids:
                        continue
                    seen_ids.add(uid)

                    results.append({
                        "url":         img["url"],
                        "preview_url": img["preview_url"],
                        "page_url":    post.get("post_url", f"https://www.tumblr.com/blog/{blog}/{post_id}"),
                        "width":       img["w"],
                        "height":      img["h"],
                        "score":       note_count,
                        "source":      "tumblr",
                        "id":          uid,
                        "tags":        ptags,
                        "artist":      blog,
                        "rating":      "sfw",
                        "is_ai":       False,
                        "post_date":   int(post.get("timestamp", 0) or 0),
                        "category":    category_key,
                    })
                    kept += 1

            print(f"  [Tumblr] Tag '{tag}' janela {_win}: {kept}/{len(posts)} artes mantidas apos filtros.")
            time.sleep(TUMBLR_DELAY)

    # Mais populares primeiro (note_count) — é isso que a amostragem viabiliza
    results.sort(key=lambda p: p.get("score") or 0, reverse=True)
    return results
