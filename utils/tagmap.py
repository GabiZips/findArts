# utils/tagmap.py
"""
Descoberta automática de tags equivalentes por fonte.

Dada a query booru de uma categoria (ex. "yamato_(one_piece)"), descobre
as tags certas em fontes que usam vocabulário próprio:

- Pixiv: usa os "other names" da wiki do Danbooru (nomes japoneses curados
  pela comunidade — é como as próprias boorus mapeiam tags vindas do Pixiv)
  e valida cada candidato com uma busca real no Pixiv antes de aceitar.
- e621: confere se cada tag existe por lá via autocomplete; se não existe
  mas há um alias óbvio (ex. blitz_(helluva_boss) → blitzo_(helluva_boss)),
  sugere a query corrigida — também validada com uma busca real.

Tudo determinístico (sem LLM): as próprias APIs são a fonte da verdade.
Só tags que retornam resultados de verdade entram na sugestão.
"""

import time

import requests

UA = {"User-Agent": "ArtFinder/2.0 (personal archiver)"}
E621_UA = {"User-Agent": "artFinder/2.0 (personal archiver; contact via github)"}


def _wiki_other_names(tag: str) -> list[str]:
    try:
        r = requests.get(
            "https://danbooru.donmai.us/wiki_pages.json",
            params={"search[title]": tag.strip().lower()},
            headers=UA, timeout=10,
        )
        r.raise_for_status()
        pages = r.json()
        if isinstance(pages, list) and pages:
            return [n for n in (pages[0].get("other_names") or []) if n]
    except Exception as e:
        print(f"  [AutoTag] wiki danbooru '{tag}': {e}")
    return []


def _danbooru_canonical(tag: str) -> str:
    """Resolve alias do Danbooru: vex_(league_of_legends) → vex_(league).
    A wiki (e os other_names) fica registrada só na tag canônica."""
    try:
        r = requests.get(
            "https://danbooru.donmai.us/tag_aliases.json",
            params={"search[antecedent_name]": tag.strip().lower()},
            headers=UA, timeout=10,
        )
        r.raise_for_status()
        rows = r.json()
        if isinstance(rows, list):
            for row in rows:
                if row.get("status") == "active" and row.get("consequent_name"):
                    return row["consequent_name"]
    except Exception:
        pass
    return tag


def danbooru_other_names(tag: str) -> list[str]:
    """Nomes alternativos (japonês/romaji) da wiki do Danbooru para uma tag.
    Se a tag for um alias, segue para a canônica antes de desistir."""
    names = _wiki_other_names(tag)
    if not names:
        canonical = _danbooru_canonical(tag)
        if canonical != tag:
            names = _wiki_other_names(canonical)
    return names


def _pixiv_count(api, query: str) -> int:
    """Nº aproximado de resultados de uma busca exata no Pixiv (0–60)."""
    try:
        r = api.search_illust(query, search_target="exact_match_for_tags",
                              sort="date_desc", search_ai_type=1)
        il = (r or {}).get("illusts") or []
        extra = 30 if (r or {}).get("next_url") else 0
        return len(il) + extra
    except Exception:
        return 0


def suggest_pixiv(booru_query: str) -> list[str]:
    """Sugere queries validadas do Pixiv para uma query booru.

    Personagem único → até 2 tags (japonesa e/ou inglesa, as com mais posts).
    Ship (2+ personagens) → uma query AND com a melhor tag de cada um.
    """
    try:
        from sources.pixiv import _get_api
    except Exception:
        return []
    api = _get_api()
    if api is None:
        return []

    tokens = [t for t in booru_query.split() if not t.startswith("-")]
    if not tokens or len(tokens) > 3:
        return []

    per_token: list[list[tuple[str, int]]] = []
    for t in tokens:
        cands = danbooru_other_names(t)[:4]
        cands.append(t)          # a própria tag booru às vezes é usada no Pixiv
        validated = []
        for c in cands:
            n = _pixiv_count(api, c)
            if n >= 3:
                validated.append((c, n))
            time.sleep(1.0)      # rate limit do Pixiv
        if not validated:
            return []            # personagem sem tag no Pixiv → sem sugestão
        validated.sort(key=lambda x: x[1], reverse=True)
        per_token.append(validated)

    if len(per_token) == 1:
        return [c for c, _ in per_token[0][:2]]

    # Ship/combinação: exige as melhores tags de cada personagem juntas (AND)
    combined = " ".join(v[0][0] for v in per_token)
    time.sleep(1.0)
    return [combined] if _pixiv_count(api, combined) >= 1 else []


def _e621_autocomplete(prefix: str) -> list[dict]:
    try:
        r = requests.get(
            "https://e621.net/tags/autocomplete.json",
            params={"search[name_matches]": prefix},
            headers=E621_UA, timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def suggest_e621(booru_query: str) -> list[str]:
    """Corrige a query booru para o vocabulário do e621, quando necessário.

    Retorna [] se a query original já funciona lá (não precisa de override)
    ou se não há correspondência confiável.
    """
    tokens = booru_query.split()
    if not tokens or len(tokens) > 4:
        return []
    out: list[str] = []
    changed = False
    for t in tokens:
        neg = t.startswith("-")
        name = (t[1:] if neg else t).lower()
        base = name.split("_(")[0]
        context = name.split("_(")[1].rstrip(")").split("_")[0] if "_(" in name else ""
        if len(base) < 3:
            return []
        cands = _e621_autocomplete(base[:12])
        names = {d.get("name") for d in cands}
        if name in names:
            out.append(t)        # a tag existe igual no e621
        else:
            # alias: candidato mais popular com mesmo prefixo (e contexto, se houver)
            best = None
            for d in cands:
                nm, pc = d.get("name", ""), d.get("post_count") or 0
                if pc <= 0 or not nm.startswith(base[:4]):
                    continue
                if context and context not in nm:
                    continue
                if best is None or pc > best[1]:
                    best = (nm, pc)
            if best is None:
                return []        # sem correspondência confiável → não arrisca
            out.append(("-" if neg else "") + best[0])
            changed = True
        time.sleep(0.5)
    if not changed:
        return []
    final = " ".join(out)
    # Validação final: a query corrigida retorna posts de verdade?
    try:
        r = requests.get("https://e621.net/posts.json",
                         params={"tags": final, "limit": 1},
                         headers=E621_UA, timeout=10)
        r.raise_for_status()
        if r.json().get("posts"):
            return [final]
    except Exception:
        pass
    return []


def suggest_source_tags(booru_query: str) -> dict[str, list[str]]:
    """Mapa {fonte: [queries validadas]} para uma query booru."""
    booru_query = (booru_query or "").strip()
    if not booru_query:
        return {}
    out: dict[str, list[str]] = {}
    px = suggest_pixiv(booru_query)
    if px:
        out["pixiv"] = px
    e6 = suggest_e621(booru_query)
    if e6:
        out["e621"] = e6
    return out
