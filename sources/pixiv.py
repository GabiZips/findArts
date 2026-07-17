# sources/pixiv.py
"""
Módulo de busca no Pixiv via pixivpy3 (API oficial do app móvel).

Autenticação: o Pixiv não permite mais login por senha na API. Você precisa
de um REFRESH TOKEN (obtido uma vez, dura bastante). Gere com:

    python get_pixiv_token.py

e cole o valor em PIXIV_REFRESH_TOKEN no .env.

Notas:
- Ordenar por popularidade ('popular_desc') exige conta Premium. Sem Premium,
  usamos 'date_desc' e ordenamos localmente por total_bookmarks.
- Imagens do Pixiv (i.pximg.net) exigem Referer https://www.pixiv.net/ para
  baixar — isso é tratado no proxy (app.py) e no downloader (utils/downloader.py).
"""

import time
from datetime import datetime

from config import (
    MIN_WIDTH, MIN_HEIGHT, MIN_SCORE, PIXIV_REFRESH_TOKEN,
)

# Rating do Pixiv: x_restrict 0 = seguro, 1 = R-18, 2 = R-18G
def _normalize_rating(x_restrict: int) -> str:
    return {0: "sfw", 1: "nsfw", 2: "nsfw"}.get(int(x_restrict or 0), "sfw")

# Fallback legado para uso standalone — o app.py passa as tags da categoria
# diretamente via parâmetro tags= de fetch_posts().
CATEGORIES: dict[str, str] = {}

# Queries prontas para categorias padrão (Pixiv indexa muito por japonês/romaji).
# IMPORTANTE: usar sempre a tag canônica COMPLETA — termos curtos como
# "シャドウ" (só "Shadow") apanham Shadowverse, Persona, FF6 etc., e
# "シャドルー" sozinho é a Shadaloo do Street Fighter, não o ship Shadow×Rouge.
# Cada categoria pode ter várias queries (japonesa + inglesa); os resultados
# são deduplicados. Query com espaço = AND de tags ("HelluvaBoss Loona" exige
# as duas tags no post — usado quando o nome sozinho é ambíguo demais).
# Todas as entradas abaixo foram validadas contra a API real (2026-07).
QUERY_MAP: dict[str, list[str]] = {
    # ── Sonic ────────────────────────────────────────────────────────
    "shadow_solo":  ["シャドウ・ザ・ヘッジホッグ", "shadow_the_hedgehog"],
    "rouge_solo":   ["ルージュ・ザ・バット", "rouge_the_bat"],
    "shadow_rouge": ["シャドルー(ソニック)", "shadouge"],   # ship Shadow×Rouge
    "shadow_sonic": ["ソニシャド", "sonadow"],              # ship Sonic×Shadow
    "sonadow":      ["ソニシャド", "sonadow"],
    "sonic_solo":   ["ソニック・ザ・ヘッジホッグ", "sonic_the_hedgehog"],

    # ── Helluva Boss ─────────────────────────────────────────────────
    # "Loona"/"Millie" sozinhas são ambíguas (LOONA kpop etc.) → AND com a série
    "loona":          ["HelluvaBoss Loona"],
    "blitzo":         ["Blitzo"],                            # nome único da série
    "millie_helluva": ["HelluvaBoss Millie"],
    "moxxie_helluva": ["Moxxie"],                            # nome único da série
    "fizz_helluva":   ["Fizzarolli"],
    "stolas_helluva": ["Stolas", "ストラス"],

    # ── Hazbin Hotel ─────────────────────────────────────────────────
    "alastor_hazbin": ["Alastor", "アラスター"],
    "angel_dust":     ["AngelDust", "エンジェルダスト"],
    "husk_hazbin":    ["HazbinHotel Husk"],                  # "Husk" sozinho é genérico
    "lucifer_hazbin": ["HazbinHotel Lucifer", "ルシファー(ハズビンホテル)"],

    # ── Ships ────────────────────────────────────────────────────────
    "huskerdust":     ["Huskerdust", "ハスエン"],
    "mm_ship":        ["HelluvaBoss Moxxie Millie"],
    "catnap_dogday":  ["CatNap DogDay", "ドッグデイ キャットナップ"],

    # ── One Piece ────────────────────────────────────────────────────
    "yamato_op": ["ヤマト(ONEPIECE)", "ヤマト(ワンピース)"],
    "perona_op": ["ペローナ"],
    "nami_op":   ["ONEPIECE ナミ", "ナミ"],

    # ── Outros ───────────────────────────────────────────────────────
    "jax_circus":    ["TADC Jax", "TheAmazingDigitalCircus Jax"],
    "evelynn_lol":   ["Evelynn"],        # "イヴリン" hoje é dominada por Wuthering Waves
    "vex_lol":       ["ヴェックス"],
    "rias_gremory":  ["リアス・グレモリー"],
    "dazai_osamu":   ["太宰治(文豪ストレイドッグス)"],
    "death_endless": ["サンドマン Death"],   # fandom pequeno no Pixiv, mas preciso
}

_api = None
_auth_at = 0


def _get_api():
    """Autentica (ou reusa) o cliente pixivpy. Reautentica a cada ~50 min."""
    global _api, _auth_at
    if not PIXIV_REFRESH_TOKEN:
        return None
    if _api is not None and (time.time() - _auth_at) < 3000:
        return _api
    try:
        from pixivpy3 import AppPixivAPI
        api = AppPixivAPI()
        api.auth(refresh_token=PIXIV_REFRESH_TOKEN)
        _api = api
        _auth_at = time.time()
        return _api
    except Exception as e:
        print(f"  [Pixiv] Falha ao autenticar (token inválido/expirado?): {e}")
        _api = None
        return None


def _build_query(category_key: str, booru_override: str | None = None) -> tuple[list[str], str]:
    """Retorna (lista de queries, search_target) para a categoria.

    Tags do QUERY_MAP são canônicas → match exato (elimina o ruído do
    partial: "シャドウ" parcial apanha Shadowverse, Persona, FF6...).
    Queries derivadas automaticamente continuam com match parcial.
    """
    if category_key in QUERY_MAP:
        return QUERY_MAP[category_key], "exact_match_for_tags"
    booru = booru_override or CATEGORIES.get(category_key, category_key)
    if booru in QUERY_MAP:
        return QUERY_MAP[booru], "exact_match_for_tags"
    words = []
    for raw in booru.split():
        if raw.startswith("-"):
            continue   # Pixiv não tem sintaxe de exclusão simples; ignora
        clean = raw.replace("(", " ").replace(")", " ").replace("_", " ").strip()
        clean = " ".join(clean.split())
        if clean and clean not in words:
            words.append(clean)
    return [" ".join(words) or category_key], "partial_match_for_tags"


def _best_urls(illust) -> tuple[str, str]:
    """Retorna (url_original_hd, url_preview) da primeira página do illust."""
    # meta_single_page: ilustração de página única
    single = (illust.get("meta_single_page") or {}).get("original_image_url")
    if single:
        preview = (illust.get("image_urls") or {}).get("large") or single
        return single, preview
    # meta_pages: ilustração com várias páginas — pega a primeira
    pages = illust.get("meta_pages") or []
    if pages:
        urls = pages[0].get("image_urls") or {}
        orig = urls.get("original") or urls.get("large") or ""
        preview = urls.get("large") or urls.get("medium") or orig
        return orig, preview
    # fallback
    iu = illust.get("image_urls") or {}
    orig = iu.get("large") or iu.get("medium") or ""
    return orig, (iu.get("medium") or orig)


def fetch_posts(category_key: str, max_pages: int = 5, tags: str | None = None,
                direct: str | None = None) -> list[dict]:
    """
    Busca ilustrações no Pixiv para a categoria.
    Ordena por popularidade (bookmarks) — via API se Premium, senão localmente.
    """
    if not PIXIV_REFRESH_TOKEN:
        print("  [Pixiv] PIXIV_REFRESH_TOKEN não configurado. Pulando.")
        return []

    api = _get_api()
    if api is None:
        return []

    if direct:
        # Query final do Pixiv (source_tags da categoria) → match exato
        queries, search_target = [direct], "exact_match_for_tags"
    else:
        queries, search_target = _build_query(category_key, tags)
    results: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        _search_one(api, query, search_target, category_key, max_pages, results, seen)

    # Sem Premium a API não ordena por popularidade — ordenamos aqui
    results.sort(key=lambda p: p.get("score") or 0, reverse=True)
    return results


def _search_one(api, query: str, search_target: str, category_key: str,
                max_pages: int, results: list[dict], seen: set[str]) -> None:
    """Executa uma query no Pixiv, acumulando em `results` (dedupe via `seen`)."""
    offset = 0

    for page in range(1, max_pages + 1):
        try:
            # search_ai_type=1 pede ao próprio Pixiv para ocultar arte de IA
            r = api.search_illust(
                query,
                search_target=search_target,
                sort="date_desc",           # popular_desc exige Premium
                search_ai_type=1,
                offset=offset or None,
            )
        except Exception as e:
            print(f"  [Pixiv] Erro na busca '{query}' (offset {offset}): {e}")
            break

        illusts = (r or {}).get("illusts") or []
        if not illusts:
            print(f"  [Pixiv] '{query}' pagina {page}: sem mais resultados.")
            break

        print(f"  [Pixiv] '{query}' pagina {page}: {len(illusts)} ilustrações da API.")
        kept = 0

        for il in illusts:
            pid = str(il.get("id", ""))
            if not pid or pid in seen:
                continue

            # Filtro anti-IA (2ª camada): illust_ai_type == 2 significa IA
            if int(il.get("illust_ai_type") or 0) == 2:
                continue

            w = il.get("width") or 0
            h = il.get("height") or 0
            if w and h and (w < MIN_WIDTH or h < MIN_HEIGHT):
                continue

            score = int(il.get("total_bookmarks") or 0)
            if score < MIN_SCORE:
                continue

            url, preview = _best_urls(il)
            if not url:
                continue

            seen.add(pid)

            tags = " ".join(
                (t.get("name") or "") for t in (il.get("tags") or [])
            ).strip()

            post_date = 0
            cd = il.get("create_date") or ""
            if cd:
                try:
                    post_date = int(datetime.fromisoformat(cd).timestamp())
                except Exception:
                    pass

            results.append({
                "url":         url,
                "preview_url": preview,
                "page_url":    f"https://www.pixiv.net/artworks/{pid}",
                "width":       w,
                "height":      h,
                "score":       score,
                "source":      "pixiv",
                "id":          pid,
                "tags":        tags,
                "artist":      (il.get("user") or {}).get("name", ""),
                "rating":      _normalize_rating(il.get("x_restrict")),
                "is_ai":       False,
                "post_date":   post_date,
                "category":    category_key,
            })
            kept += 1

        print(f"  [Pixiv] '{query}' pagina {page}: {kept}/{len(illusts)} mantidas.")

        # paginação: a API devolve a próxima offset em next_url
        next_url = (r or {}).get("next_url")
        if not next_url:
            break
        try:
            offset = int(api.parse_qs(next_url).get("offset", 0))
        except Exception:
            offset += 30
        time.sleep(1.0)   # respeita rate limit do Pixiv
