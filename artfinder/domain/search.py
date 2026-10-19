"""One query plan and content policy for JSON and streaming searches."""

from dataclasses import dataclass
import re

from artfinder.domain.content_policy import is_ai_generated
from utils.normalize import normalize_posts


def split_queries(value: str) -> list[str]:
    return list(dict.fromkeys(part.strip() for part in re.split(r"[;\n]+", value or "") if part.strip()))


@dataclass(frozen=True)
class SearchPlan:
    combos: list[tuple[str, str, str | None, str | None]]
    pages: int
    min_score: int


def build_search_plan(body: dict, categories: dict, sources: dict) -> SearchPlan:
    try:
        pages = max(1, min(int(body.get("pages", 2)), 50))
        min_score = max(0, int(body.get("min_score", 0)))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Paginas ou score invalidos") from exc
    keys = body.get("categories", list(categories))
    selected = body.get("sources", [])
    extra = body.get("custom_categories", [])
    if (not isinstance(keys, list) or not all(isinstance(key, str) for key in keys)
            or not isinstance(selected, list) or not all(isinstance(s, str) for s in selected)
            or not isinstance(extra, list) or not all(isinstance(c, dict) for c in extra)):
        raise ValueError("Categorias ou fontes invalidas")
    selected = list(dict.fromkeys(s for s in (selected or list(sources)) if s in sources))
    combos = []
    records = [(key, categories[key]) for key in keys if key in categories]
    records += [(str(c.get("label", "custom")), c) for c in extra]
    for key, category in records:
        raw_overrides = category.get("source_tags") or {}
        if not isinstance(raw_overrides, dict) or not all(isinstance(s, str) for s in raw_overrides):
            raise ValueError("Consultas da fonte invalidas")
        overrides = {s.lower(): value for s, value in raw_overrides.items()}
        for source in selected:
            direct = overrides.get(source.lower())
            if direct:
                queries = direct if isinstance(direct, list) else [direct]
                if not all(isinstance(query, str) for query in queries):
                    raise ValueError("Consultas da fonte invalidas")
                combos.extend((key, source, None, q.strip()) for q in queries if q.strip())
            else:
                tags = category.get("tags", "")
                if not isinstance(tags, str):
                    raise ValueError("Tags invalidas")
                combos.extend((key, source, q, None) for q in split_queries(tags))
    combos = list(dict.fromkeys(combos))
    if len(combos) > 2000:
        raise ValueError("Muitas consultas. Selecione menos categorias ou fontes.")
    return SearchPlan(combos, pages, min_score)


def fetch_query(fn, combo, pages):
    category, _source, tags, direct = combo
    if direct:
        return fn(category, max_pages=pages, direct=direct)
    if tags:
        return fn(category, max_pages=pages, tags=tags)
    return fn(category, max_pages=pages)


def accepted_posts(raw, *, source, category, seen, blacklist, blocked_artists, min_score=0):
    result = []
    for post in normalize_posts(raw, source):
        uid = f"{post['source']}:{post['id']}"
        if (uid in seen or uid in blacklist or post['score'] < min_score
                or is_ai_generated(post)
                or post['artist'].strip().lower() in blocked_artists):
            continue
        seen.add(uid)
        if not post.get("category"):
            post['category'] = category
        result.append(post)
    return result
