"""Desktop credential policy shared by startup, settings and pairing."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from utils.credential_store import CredentialStore, CredentialStoreError, native_backend

CREDENTIAL_FIELDS = {
    "Danbooru": ("DANBOORU_LOGIN", "DANBOORU_API_KEY"),
    "Gelbooru": ("GELBOORU_USER_ID", "GELBOORU_API_KEY"),
    "Pixiv": ("PIXIV_REFRESH_TOKEN",),
    "Tumblr": ("TUMBLR_API_KEY", "TUMBLR_CONSUMER_SECRET", "TUMBLR_OAUTH_TOKEN", "TUMBLR_OAUTH_TOKEN_SECRET"),
    "DeviantArt": ("DEVIANTART_CLIENT_ID", "DEVIANTART_CLIENT_SECRET"),
    "Bluesky": ("BSKY_HANDLE", "BSKY_PASSWORD"),
}
CREDENTIAL_KEYS = frozenset(key for fields in CREDENTIAL_FIELDS.values() for key in fields)
_LOCK = RLock()


def profile_store(data_dir):
    profile = hashlib.sha256(os.path.normcase(str(Path(data_dir).resolve())).encode()).hexdigest()[:32]
    return CredentialStore(native_backend(), CREDENTIAL_KEYS,
                           f"io.github.gabizips.artfinder.v1.{profile}")


def resolve_credentials(store, legacy):
    """Native entries (including removals) win; errors never use legacy secrets."""
    values = {}
    for key in CREDENTIAL_KEYS:
        raw = store.read(key)
        if raw is None:
            values[key] = legacy.get(key, "")
            continue
        try:
            item = json.loads(raw)
            if item.get("version") != 1 or not isinstance(item.get("value"), str):
                raise ValueError
            values[key] = item["value"]
        except (ValueError, TypeError, AttributeError):
            raise CredentialStoreError("Invalid credential store record.") from None
    return values


def save_credentials(store, updates, removals):
    """Verified writes with best-effort rollback; empty records suppress legacy."""
    changed = set(updates) | set(removals)
    if changed - CREDENTIAL_KEYS:
        raise CredentialStoreError("Unsupported credential field.")
    if any(not isinstance(v, str) or not v or '\x00' in v for v in updates.values()):
        raise CredentialStoreError("Invalid credential value.")
    with _LOCK:
        previous = {key: store.read(key) for key in changed}
        attempted = []
        try:
            for key in sorted(changed):
                attempted.append(key)
                value = "" if key in removals else updates[key]
                store.write(key, json.dumps({"version": 1, "value": value}, ensure_ascii=False))
        except CredentialStoreError:
            failed = False
            for key in reversed(attempted):
                try:
                    if previous[key] is None:
                        store.delete(key)
                    else:
                        store.write(key, previous[key])
                except CredentialStoreError:
                    failed = True
            if failed:
                raise CredentialStoreError("Credential update failed; restart and review stored credentials.") from None
            raise


def clean_legacy_credentials(store, path):
    """Remove only values verified in the vault, preserving all other lines."""
    path = Path(path)
    with _LOCK:
        if path.is_symlink():
            raise CredentialStoreError("Legacy configuration must be a regular file.")
        if not path.exists():
            return {"removed": 0, "remaining": 0}
        original = path.read_bytes()
        lines = original.decode("utf-8").splitlines(keepends=True)
        native = resolve_credentials(store, {})
        kept, removed, remaining = [], 0, 0
        for line in lines:
            stripped = line.strip()
            key, separator, value = stripped.partition("=")
            key = key.strip()
            if separator and key in CREDENTIAL_KEYS and not stripped.startswith("#"):
                value = value.strip().strip('"').strip("'")
                if store.read(key) is not None and (native[key] == value or native[key] == ""):
                    removed += 1
                    continue
                remaining += 1
            kept.append(line)
        if removed:
            fd, temporary = tempfile.mkstemp(prefix=".credential-cleanup-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as target:
                    target.write("".join(kept).encode("utf-8"))
                    target.flush()
                    os.fsync(target.fileno())
                if path.is_symlink() or path.read_bytes() != original:
                    raise CredentialStoreError("Legacy configuration changed; try again.")
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return {"removed": removed, "remaining": remaining}
