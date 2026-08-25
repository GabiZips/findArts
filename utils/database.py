# utils/database.py
"""
Banco de dados SQLite central do artFinder.
Tabelas:
  - posts      : toda arte já descoberta pelo app (persistência permanente)
  - downloads  : rastreia o que foi baixado para o disco (com phash)
  - favorites  : artes favoritadas pelo usuário
  - blacklist  : artes ocultadas permanentemente (nunca mais aparecem na busca)
"""

import sqlite3
import threading
import time
from pathlib import Path
from config import DB_PATH

# ── Schema ──────────────────────────────────────────────────────────────

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS posts (
    uid           TEXT    PRIMARY KEY,      -- "{source}:{post_id}"
    source        TEXT    NOT NULL,
    post_id       TEXT    NOT NULL,
    category      TEXT    DEFAULT '',
    url           TEXT    DEFAULT '',
    preview_url   TEXT    DEFAULT '',
    page_url      TEXT    DEFAULT '',
    width         INTEGER DEFAULT 0,
    height        INTEGER DEFAULT 0,
    score         INTEGER DEFAULT 0,
    rating        TEXT    DEFAULT 'sfw',
    artist        TEXT    DEFAULT '',
    tags          TEXT    DEFAULT '',
    is_ai         INTEGER DEFAULT 0,
    post_date     INTEGER DEFAULT 0,        -- timestamp original do site (quando disponivel)
    discovered_at INTEGER DEFAULT 0         -- timestamp de quando o app viu pela primeira vez
);

CREATE INDEX IF NOT EXISTS idx_posts_source      ON posts(source);
CREATE INDEX IF NOT EXISTS idx_posts_category    ON posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_score       ON posts(score DESC);
CREATE INDEX IF NOT EXISTS idx_posts_rating      ON posts(rating);
CREATE INDEX IF NOT EXISTS idx_posts_discovered  ON posts(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_post_date   ON posts(post_date DESC);
CREATE INDEX IF NOT EXISTS idx_posts_width       ON posts(width);

CREATE TABLE IF NOT EXISTS downloads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       TEXT    NOT NULL UNIQUE,
    source          TEXT    NOT NULL,
    artist          TEXT,
    score           INTEGER DEFAULT 0,
    file_path       TEXT,
    tags            TEXT,
    width           INTEGER DEFAULT 0,
    height          INTEGER DEFAULT 0,
    phash           TEXT,
    public_uri      TEXT    DEFAULT '',
    downloaded_at   INTEGER
);

CREATE TABLE IF NOT EXISTS favorites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT    NOT NULL,
    post_id     TEXT    NOT NULL,
    artist      TEXT    DEFAULT '',
    url         TEXT    DEFAULT '',
    preview_url TEXT    DEFAULT '',
    page_url    TEXT    DEFAULT '',
    added_at    INTEGER NOT NULL,
    UNIQUE(source, post_id)
);

CREATE INDEX IF NOT EXISTS idx_source_id ON downloads(source_id);
CREATE INDEX IF NOT EXISTS idx_phash     ON downloads(phash);
CREATE INDEX IF NOT EXISTS idx_fav_src   ON favorites(source, post_id);

CREATE TABLE IF NOT EXISTS collections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL COLLATE NOCASE UNIQUE,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS favorite_collections (
    source        TEXT    NOT NULL,
    post_id       TEXT    NOT NULL,
    collection_id INTEGER NOT NULL,
    PRIMARY KEY(source, post_id, collection_id),
    FOREIGN KEY(source, post_id) REFERENCES favorites(source, post_id) ON DELETE CASCADE,
    FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_fav_col_collection ON favorite_collections(collection_id);

CREATE TABLE IF NOT EXISTS blacklist (
    uid         TEXT    PRIMARY KEY,   -- "{source}:{post_id}"
    source      TEXT    NOT NULL,
    post_id     TEXT    NOT NULL,
    added_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bl_uid ON blacklist(uid);

CREATE TABLE IF NOT EXISTS blocked_artists (
    artist      TEXT    PRIMARY KEY,
    added_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ratings (
    uid         TEXT    PRIMARY KEY,   -- "{source}:{post_id}"
    source      TEXT    NOT NULL,
    post_id     TEXT    NOT NULL,
    rating      TEXT    NOT NULL,      -- 'usar' | 'talvez' | 'depois' | 'nao'
    rated_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ratings_rating ON ratings(rating);
"""


_schema_ready = False
_schema_lock = threading.Lock()


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    declaration: str,
) -> None:
    """Add a column to databases created by older ArtFinder versions."""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def _connect() -> sqlite3.Connection:
    """Abre conexão com o banco e garante que todas as tabelas existem."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    global _schema_ready
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    if not _schema_ready:
        with _schema_lock:
            if not _schema_ready:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript(_CREATE_SQL)
                _ensure_column(conn, "downloads", "public_uri", "TEXT DEFAULT ''")
                conn.commit()
                _schema_ready = True
    return conn


# ── POSTS ────────────────────────────────────────────────────────────────

def upsert_post(post: dict) -> bool:
    """
    Insere ou atualiza um post descoberto.
    Retorna True se era novo (foi inserido), False se já existia.
    """
    source  = post.get("source", "")
    post_id = str(post.get("id", ""))
    uid     = f"{source}:{post_id}"

    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO posts
               (uid, source, post_id, category, url, preview_url, page_url,
                width, height, score, rating, artist, tags, is_ai,
                post_date, discovered_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                uid,
                source,
                post_id,
                post.get("category", ""),
                post.get("url", ""),
                post.get("preview_url", ""),
                post.get("page_url", ""),
                post.get("width", 0),
                post.get("height", 0),
                post.get("score", 0),
                post.get("rating", "sfw"),
                post.get("artist", ""),
                post.get("tags", ""),
                1 if post.get("is_ai") else 0,
                post.get("post_date", 0),
                int(time.time()),
            )
        )
        conn.commit()
        return cur.rowcount > 0   # True = novo
    finally:
        conn.close()


def upsert_posts_batch(posts: list[dict]) -> tuple[int, int]:
    """
    Insere múltiplos posts de uma vez.
    Retorna (novos, ja_existiam).
    """
    if not posts:
        return 0, 0

    now = int(time.time())
    rows = []
    for post in posts:
        source  = post.get("source", "")
        post_id = str(post.get("id", ""))
        uid     = f"{source}:{post_id}"
        rows.append((
            uid,
            source,
            post_id,
            post.get("category", ""),
            post.get("url", ""),
            post.get("preview_url", ""),
            post.get("page_url", ""),
            post.get("width", 0),
            post.get("height", 0),
            post.get("score", 0),
            post.get("rating", "sfw"),
            post.get("artist", ""),
            post.get("tags", ""),
            1 if post.get("is_ai") else 0,
            post.get("post_date", 0),
            now,
        ))

    conn = _connect()
    try:
        before = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        # Upsert real: se o post já existe, atualiza os metadados (rating,
        # categoria, URLs, score...) em vez de ignorar — INSERT OR IGNORE
        # deixava a Galeria com dados desatualizados para sempre.
        conn.executemany(
            """INSERT INTO posts
               (uid, source, post_id, category, url, preview_url, page_url,
                width, height, score, rating, artist, tags, is_ai,
                post_date, discovered_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(uid) DO UPDATE SET
                 category    = CASE WHEN excluded.category != '' THEN excluded.category ELSE posts.category END,
                 url         = CASE WHEN excluded.url != '' THEN excluded.url ELSE posts.url END,
                 preview_url = CASE WHEN excluded.preview_url != '' THEN excluded.preview_url ELSE posts.preview_url END,
                 page_url    = CASE WHEN excluded.page_url != '' THEN excluded.page_url ELSE posts.page_url END,
                 width       = MAX(posts.width,  excluded.width),
                 height      = MAX(posts.height, excluded.height),
                 score       = MAX(posts.score,  excluded.score),
                 rating      = excluded.rating,
                 artist      = CASE WHEN excluded.artist != '' THEN excluded.artist ELSE posts.artist END,
                 tags        = CASE WHEN excluded.tags != '' THEN excluded.tags ELSE posts.tags END,
                 is_ai       = excluded.is_ai,
                 post_date   = MAX(posts.post_date, excluded.post_date)""",
            rows
        )
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        novos = after - before
        return novos, len(posts) - novos
    finally:
        conn.close()


def known_uids(uids: list[str]) -> set[str]:
    """
    Dado uma lista de UIDs, retorna os que já existem no banco.
    Útil para filtrar resultados de busca e mostrar só os novos.
    """
    if not uids:
        return set()
    conn = _connect()
    try:
        placeholders = ",".join("?" * len(uids))
        rows = conn.execute(
            # Only generated '?' placeholders are interpolated; values stay bound.
            f"SELECT uid FROM posts WHERE uid IN ({placeholders})",  # nosec B608
            uids,
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def delete_posts(uids: list[str]) -> int:
    """Remove posts do banco (oculta da biblioteca)."""
    if not uids:
        return 0
    conn = _connect()
    try:
        placeholders = ",".join("?" * len(uids))
        # Only generated '?' placeholders are interpolated; values stay bound.
        cur = conn.execute(
            f"DELETE FROM posts WHERE uid IN ({placeholders})",  # nosec B608
            uids,
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ── BLACKLIST ─────────────────────────────────────────────────────────────

def add_to_blacklist(uids: list[str]) -> int:
    """Adiciona UIDs à blacklist permanente. Retorna quantos foram adicionados."""
    if not uids:
        return 0
    conn = _connect()
    try:
        added = 0
        ts = int(time.time())
        for uid in uids:
            parts = uid.split(":", 1)
            source  = parts[0] if len(parts) == 2 else ""
            post_id = parts[1] if len(parts) == 2 else uid
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO blacklist(uid, source, post_id, added_at) VALUES(?,?,?,?)",
                    (uid, source, post_id, ts)
                )
                if conn.execute("SELECT changes()").fetchone()[0]:
                    added += 1
            except Exception:
                pass
        conn.commit()
        return added
    finally:
        conn.close()


def get_blacklisted_uids() -> set[str]:
    """Retorna todos os UIDs na blacklist."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT uid FROM blacklist").fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def is_blacklisted_batch(uids: list[str]) -> set[str]:
    """Retorna o subconjunto de UIDs que estão na blacklist."""
    if not uids:
        return set()
    conn = _connect()
    try:
        placeholders = ",".join("?" * len(uids))
        rows = conn.execute(
            # Only generated '?' placeholders are interpolated; values stay bound.
            f"SELECT uid FROM blacklist WHERE uid IN ({placeholders})",  # nosec B608
            uids,
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()

def add_blocked_artist(artist: str) -> bool:
    """Adiciona um artista à lista de bloqueados permanentemente."""
    if not artist:
        return False
    artist_norm = artist.strip().lower()
    conn = _connect()
    try:
        ts = int(time.time())
        conn.execute("INSERT OR IGNORE INTO blocked_artists(artist, added_at) VALUES(?,?)", (artist_norm, ts))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao bloquear artista {artist_norm}: {e}")
        return False
    finally:
        conn.close()

def get_blocked_artists() -> set[str]:
    """Retorna o conjunto de artistas bloqueados."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT artist FROM blocked_artists").fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()
    finally:
        conn.close()


# ── DOWNLOADS ─────────────────────────────────────────────────────────────


def is_downloaded(source: str, post_id: str) -> bool:
    """Verifica se o par (source, id) já foi registrado como download."""
    key = f"{source}:{post_id}"
    conn = _connect()
    try:
        cur = conn.execute("SELECT 1 FROM downloads WHERE source_id = ?", (key,))
        return cur.fetchone() is not None
    finally:
        conn.close()


# Cache em memória dos phashes (como ints). Evita reabrir o banco e varrer a
# tabela inteira a cada download — com a coleção grande isso era o gargalo.
_phash_cache: list[int] | None = None
_phash_lock = threading.Lock()


def _invalidate_phash_cache() -> None:
    global _phash_cache
    with _phash_lock:
        _phash_cache = None


def _get_phash_cache() -> list[int]:
    global _phash_cache
    with _phash_lock:
        if _phash_cache is None:
            conn = _connect()
            try:
                rows = conn.execute(
                    "SELECT phash FROM downloads WHERE phash IS NOT NULL AND phash != ''"
                ).fetchall()
            finally:
                conn.close()
            cache = []
            for row in rows:
                try:
                    cache.append(int(row[0], 16))
                except (TypeError, ValueError):
                    continue
            _phash_cache = cache
        return _phash_cache


def is_duplicate_hash(phash_hex: str, threshold: int = 5) -> bool:
    """Verifica se já existe uma imagem com hash perceptual próximo (Hamming distance)."""
    if not phash_hex:
        return False
    try:
        target = int(phash_hex, 16)
    except ValueError:
        return False

    for stored in _get_phash_cache():
        if bin(target ^ stored).count("1") <= threshold:
            return True
    return False


def register_download(
    source: str,
    post_id: str,
    file_path: str,
    artist: str = "",
    score: int = 0,
    tags: str = "",
    width: int = 0,
    height: int = 0,
    phash: str = "",
    public_uri: str = "",
):
    """Registra um download bem-sucedido no banco."""
    key = f"{source}:{post_id}"
    conn = _connect()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO downloads
               (source_id, source, artist, score, file_path, tags, width, height,
                phash, public_uri, downloaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                key,
                source,
                artist,
                score,
                file_path,
                tags,
                width,
                height,
                phash,
                public_uri,
                int(time.time()),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Mantém o cache de phash coerente sem recarregar do banco
    if phash:
        with _phash_lock:
            if _phash_cache is not None:
                try:
                    _phash_cache.append(int(phash, 16))
                except (TypeError, ValueError):
                    pass


def get_download_by_file_path(file_path: str) -> dict | None:
    """Return the tracked download matching an absolute private file path."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT source_id, file_path, public_uri FROM downloads WHERE file_path = ?",
            (file_path,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_download_public_uri(file_path: str, public_uri: str) -> bool:
    """Persist (or clear) the Android MediaStore URI for a download."""
    conn = _connect()
    try:
        cursor = conn.execute(
            "UPDATE downloads SET public_uri = ? WHERE file_path = ?",
            (public_uri, file_path),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_stats() -> dict:
    """Retorna estatísticas gerais do banco (downloads)."""
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        by_source = conn.execute(
            "SELECT source, COUNT(*) FROM downloads GROUP BY source ORDER BY COUNT(*) DESC"
        ).fetchall()
        return {
            "total":     total,
            "by_source": {r[0]: r[1] for r in by_source},
        }
    finally:
        conn.close()


def clear_db() -> int:
    """Apaga TODOS os registros do banco de downloads. Retorna quantos foram removidos."""
    conn = _connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        conn.execute("DELETE FROM downloads")
        conn.commit()
        _invalidate_phash_cache()
        return count
    finally:
        conn.close()


def sync_db() -> int:
    """Remove do banco de downloads os registros cujo arquivo não existe mais no disco."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT source_id, file_path FROM downloads").fetchall()
        removed = 0
        for row in rows:
            source_id = row[0] if isinstance(row, (list, tuple)) else row["source_id"]
            file_path = row[1] if isinstance(row, (list, tuple)) else row["file_path"]
            if not file_path or not Path(file_path).exists():
                conn.execute("DELETE FROM downloads WHERE source_id = ?", (source_id,))
                removed += 1
        conn.commit()
        if removed:
            _invalidate_phash_cache()
        return removed
    finally:
        conn.close()


# ── RATINGS (triagem) ─────────────────────────────────────────────────────

VALID_RATINGS = {"usar", "talvez", "depois", "nao"}


def set_rating(source: str, post_id: str, rating: str) -> bool:
    """Define/atualiza a avaliação de uma arte. Retorna True se válido."""
    if rating not in VALID_RATINGS:
        return False
    uid = f"{source}:{post_id}"
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO ratings(uid, source, post_id, rating, rated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(uid) DO UPDATE SET rating=excluded.rating, rated_at=excluded.rated_at""",
            (uid, source, str(post_id), rating, int(time.time())),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def remove_rating(source: str, post_id: str) -> bool:
    """Remove a avaliação (volta a ser 'não avaliada'). Retorna True se removida."""
    conn = _connect()
    try:
        cur = conn.execute(
            "DELETE FROM ratings WHERE uid = ?", (f"{source}:{post_id}",)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_all_ratings() -> dict[str, str]:
    """Retorna {uid: rating} de todas as artes avaliadas."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT uid, rating FROM ratings").fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


# ── FAVORITES ────────────────────────────────────────────────────────────

def add_favorite(source: str, post_id: str, artist: str = "",
                 url: str = "", preview_url: str = "", page_url: str = "") -> bool:
    """Adiciona uma arte aos favoritos. Retorna True se inserido."""
    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO favorites
               (source, post_id, artist, url, preview_url, page_url, added_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (source, str(post_id), artist or "", url or "",
             preview_url or "", page_url or "", int(time.time())),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def remove_favorite(source: str, post_id: str) -> bool:
    """Remove uma arte dos favoritos. Retorna True se removido."""
    conn = _connect()
    try:
        cur = conn.execute(
            "DELETE FROM favorites WHERE source = ? AND post_id = ?",
            (source, str(post_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_favorites() -> list[dict]:
    """Retorna todas as artes favoritadas, mais recentes primeiro."""
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT f.source, f.post_id, f.artist, f.url, f.preview_url, f.page_url, f.added_at,
                      p.rating, p.score, p.width, p.height, p.tags
               FROM favorites f
               LEFT JOIN posts p ON p.uid = f.source || ':' || f.post_id
               ORDER BY f.added_at DESC"""
        ).fetchall()
        membership: dict[tuple[str, str], list[int]] = {}
        for row in conn.execute(
            "SELECT source, post_id, collection_id FROM favorite_collections ORDER BY collection_id"
        ).fetchall():
            membership.setdefault((row["source"], row["post_id"]), []).append(row["collection_id"])
        return [
            {
                "source":      r["source"],
                "post_id":     r["post_id"],
                "artist":      r["artist"] or "",
                "url":         r["url"] or "",
                "preview_url": r["preview_url"] or "",
                "page_url":    r["page_url"] or "",
                "added_at":    r["added_at"],
                "rating":      r["rating"] or "sfw",
                "score":       r["score"] or 0,
                "width":       r["width"] or 0,
                "height":      r["height"] or 0,
                "tags":        r["tags"] or "",
                "collection_ids": membership.get((r["source"], r["post_id"]), []),
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_collections() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT c.id, c.name, c.created_at, COUNT(fc.post_id) AS item_count
               FROM collections c
               LEFT JOIN favorite_collections fc ON fc.collection_id = c.id
               GROUP BY c.id
               ORDER BY c.name COLLATE NOCASE"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_collection(name: str) -> dict:
    clean = " ".join((name or "").split())[:80]
    if not clean:
        raise ValueError("Nome da coleção é obrigatório")
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO collections(name, created_at) VALUES(?, ?)",
            (clean, int(time.time())),
        )
        conn.commit()
        return {"id": cur.lastrowid, "name": clean, "created_at": int(time.time()), "item_count": 0}
    finally:
        conn.close()


def rename_collection(collection_id: int, name: str) -> bool:
    clean = " ".join((name or "").split())[:80]
    if not clean:
        raise ValueError("Nome da coleção é obrigatório")
    conn = _connect()
    try:
        cur = conn.execute("UPDATE collections SET name = ? WHERE id = ?", (clean, collection_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_collection(collection_id: int) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def set_favorite_collections(source: str, post_id: str, collection_ids: list[int]) -> list[int]:
    clean_ids = sorted({int(value) for value in collection_ids})[:100]
    conn = _connect()
    try:
        existing = {
            row[0]
            for row in conn.execute(
                f"SELECT id FROM collections WHERE id IN ({','.join('?' for _ in clean_ids)})",
                clean_ids,
            ).fetchall()
        } if clean_ids else set()
        conn.execute(
            "DELETE FROM favorite_collections WHERE source = ? AND post_id = ?",
            (source, str(post_id)),
        )
        conn.executemany(
            "INSERT INTO favorite_collections(source, post_id, collection_id) VALUES(?, ?, ?)",
            [(source, str(post_id), collection_id) for collection_id in sorted(existing)],
        )
        conn.commit()
        return sorted(existing)
    finally:
        conn.close()


def is_favorited(source: str, post_id: str) -> bool:
    """Verifica se uma arte já está nos favoritos."""
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT 1 FROM favorites WHERE source = ? AND post_id = ?",
            (source, str(post_id)),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()
