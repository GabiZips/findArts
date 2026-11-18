"""Shared native artwork identity, filtering and virtual gallery model."""
import time
from urllib.parse import urlsplit

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


def uid(post):
    return post.get("uid") or f"{post.get('source', '')}:{post.get('id') or post.get('post_id') or ''}"


def canonical(post):
    value = dict(post)
    value["id"] = str(value.get("id") or value.get("post_id") or uid(value).partition(":")[2])
    value["url"] = value.get("url") or value.get("orig_url") or ""
    value["uid"] = uid(value)
    return value


def source_name(value):
    value = (value or "").lower()
    return "bluesky" if value == "bsky" else value


def rating(post):
    raw = (post.get("rating") or "sfw").lower()
    if raw in {"nsfw", "explicit", "e", "questionable", "q"}:
        return "nsfw"
    return "sensitive" if raw in {"sensitive", "s"} else "sfw"


def media_type(post):
    path = urlsplit(post.get("url") or post.get("orig_url") or post.get("rel_path") or post.get("preview_url") or "").path.lower()
    if path.endswith((".mp4", ".webm", ".m4v", ".mov")):
        return "video"
    if path.endswith(".gif"):
        return "gif"
    if path.endswith(".webp"):
        return "webp"
    return "image"


def filter_posts(posts, options, saved=None):
    saved = saved or set()
    query = options.get("query", "").casefold().strip()
    blocked = [s.strip().replace("_", " ").casefold() for s in options.get("blacklist", "").split(",") if s.strip()]
    result = []
    for p in posts:
        if options.get("source") and source_name(p.get("source")) != source_name(options["source"]):
            continue
        if rating(p) not in options.get("ratings", ["sfw", "sensitive", "nsfw"]):
            continue
        if media_type(p) not in options.get("media", ["image", "gif", "webp", "video"]):
            continue
        if (p.get("score") or 0) < options.get("score", 0):
            continue
        if options.get("hide_saved") and uid(p) in saved:
            continue
        if options.get("collection") and options["collection"] not in (p.get("collection_ids") or []):
            continue
        if query and query not in " ".join(str(p.get(k) or "") for k in ("artist", "tags", "source", "category")).casefold():
            continue
        tags = " " + str(p.get("tags") or "").replace("_", " ").casefold() + " "
        if any(" " + tag + " " in tags for tag in blocked):
            continue
        days, date = options.get("days", 0), p.get("post_date") or 0
        if days and date and date < time.time() - days * 86400:
            continue
        result.append(p)
    mode = options.get("sort", "score")
    if mode == "score":
        result.sort(key=lambda p: p.get("score") or 0, reverse=True)
    elif mode == "recent":
        result.sort(key=lambda p: p.get("post_date") or p.get("downloaded_at") or p.get("added_at") or 0, reverse=True)
    elif mode in {"source", "artist", "category"}:
        result.sort(key=lambda p: str(p.get(mode) or "").casefold())
    return result


class ArtworkModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.posts = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.posts)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self.posts):
            return None
        post = self.posts[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return post
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.AccessibleTextRole):
            return f"{post.get('artist') or 'Artista desconhecido'} — {post.get('source', '')} — {rating(post)}"
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{post.get('artist') or 'Artista desconhecido'}\n{post.get('source', '')} • {post.get('width') or 0} × {post.get('height') or 0}\nDuplo clique ou Enter para abrir"

    def replace(self, posts):
        self.beginResetModel()
        self.posts = posts
        self.endResetModel()
