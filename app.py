"""
ArtFinder local application composition.

Servidor FastAPI privado usado pela janela desktop e pelos testes locais.

Uso:
    python app.py
    # Abre automaticamente: http://localhost:7860
"""

import asyncio
import hashlib
import ipaddress
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import unicodedata
import webbrowser
from pathlib import Path
from threading import Timer
from urllib.parse import urlencode, urlsplit

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
try:
    from sse_starlette.sse import EventSourceResponse
    HAS_SSE = True
except ImportError:
    HAS_SSE = False
import requests as _requests

# ── garante que o projeto está no path ─────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

# Evita UnicodeEncodeError nos prints em consoles Windows cp1252
# (queries japonesas do Pixiv, emojis etc. viram '?' em vez de crashar)
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="replace")
        except Exception:
            pass

from config import DATA_DIR, DOWNLOAD_DIR, RESOURCE_DIR, USER_CATEGORIES_PATH
from artfinder.domain.content_policy import is_ai_generated, matched_ai_indicators
from artfinder.api.library import router as library_router
from utils.database import get_stats, known_uids, add_to_blacklist, add_blocked_artist, get_blocked_artists
from utils.downloader import download_batch
from utils.lan_security import (
    LAN_COOKIE_NAME,
    LAN_QUERY_NAME,
    ensure_lan_token,
    is_loopback_client,
    lan_mode_enabled,
    token_matches,
)
from utils.normalize import normalize_posts
from utils.pairing import PairingError, pairing_manager, parse_pairing_code

USER_CATS_FILE = Path(USER_CATEGORIES_PATH)
DEFAULT_USER_CATS_FILE = Path(RESOURCE_DIR) / "defaults" / "categories.json"
_USER_CATS_LOCK = threading.RLock()
_CREDENTIALS_LOCK = threading.RLock()

# The first public Windows artifact accidentally bundled this exact personal
# category file. Only this byte-for-byte file is migrated; user-created or
# edited categories are never touched.
_LEGACY_BUNDLED_CATEGORY_HASHES = {
    "09dbf971205e5a66094e97ebb478019c8ae9b30c2411610a72c9b3049d47e3c5",
}

CREDENTIAL_FIELDS = {
    "Danbooru": ("DANBOORU_LOGIN", "DANBOORU_API_KEY"),
    "Gelbooru": ("GELBOORU_USER_ID", "GELBOORU_API_KEY"),
    "Pixiv": ("PIXIV_REFRESH_TOKEN",),
    "Tumblr": (
        "TUMBLR_API_KEY",
        "TUMBLR_CONSUMER_SECRET",
        "TUMBLR_OAUTH_TOKEN",
        "TUMBLR_OAUTH_TOKEN_SECRET",
    ),
    "DeviantArt": ("DEVIANTART_CLIENT_ID", "DEVIANTART_CLIENT_SECRET"),
    "Bluesky": ("BSKY_HANDLE", "BSKY_PASSWORD"),
}
_CREDENTIAL_KEYS = frozenset(key for keys in CREDENTIAL_FIELDS.values() for key in keys)


def _write_credentials(updates: dict[str, str], removals: set[str]) -> None:
    """Atomically update only credential keys in the private .env file."""
    env_path = Path(DATA_DIR) / ".env"
    with _CREDENTIALS_LOCK:
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        changed = set(updates) | removals
        kept = []
        for line in lines:
            stripped = line.strip()
            key = stripped.partition("=")[0].strip() if "=" in stripped else ""
            if key not in changed:
                kept.append(line)
        kept.extend(f"{key}={value}" for key, value in updates.items())

        env_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=str(env_path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
                file.write("\n".join(kept).rstrip() + ("\n" if kept else ""))
                file.flush()
                os.fsync(file.fileno())
            os.replace(tmp_name, env_path)
            if os.name != "nt":
                os.chmod(env_path, 0o600)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


def _apply_credentials(updates: dict[str, str], removals: set[str]) -> None:
    """Refresh already-imported source modules without exposing saved values."""
    import config as current_config

    values = {key: "" for key in removals}
    values.update(updates)
    source_modules = (
        "sources.bsky",
        "sources.danbooru",
        "sources.deviantart",
        "sources.gelbooru",
        "sources.pixiv",
        "sources.tumblr",
    )
    for key, value in values.items():
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)
        setattr(current_config, key, value)
        for module_name in source_modules:
            module = sys.modules.get(module_name)
            if module is not None and hasattr(module, key):
                setattr(module, key, value)

    # Authentication sessions must not survive a credential change.
    bsky = sys.modules.get("sources.bsky")
    if bsky is not None:
        bsky._BSKY_TOKEN = None
        bsky._BSKY_TOKEN_EXPIRES = 0
    deviantart = sys.modules.get("sources.deviantart")
    if deviantart is not None:
        deviantart._token_cache = {"token": None, "expires_at": 0}
    pixiv = sys.modules.get("sources.pixiv")
    if pixiv is not None:
        pixiv._api = None
        pixiv._auth_at = 0


def _credential_status_payload() -> dict:
    """Return configuration state only; credential values never leave Python."""
    import config as current_config

    return {
        "groups": [
            {
                "source": source,
                "fields": [
                    {"key": key, "configured": bool(getattr(current_config, key, ""))}
                    for key in keys
                ],
            }
            for source, keys in CREDENTIAL_FIELDS.items()
        ]
    }


def _validate_credential_changes(
    raw_values: object,
    raw_removals: object,
) -> tuple[dict[str, str], set[str]]:
    """Validate credential mutations shared by settings and pairing imports."""
    if not isinstance(raw_values, dict) or not isinstance(raw_removals, list):
        raise ValueError("Formato de credenciais invalido")
    if any(not isinstance(key, str) for key in raw_values) or any(
        not isinstance(key, str) for key in raw_removals
    ):
        raise ValueError("Campo de credencial invalido")

    unknown = (set(raw_values) | set(raw_removals)) - _CREDENTIAL_KEYS
    if unknown:
        raise ValueError("Campo de credencial desconhecido")

    updates: dict[str, str] = {}
    for key, raw_value in raw_values.items():
        if not isinstance(raw_value, str):
            raise ValueError(f"Valor invalido para {key}")
        value = raw_value.strip()
        if not value:
            continue
        if len(value) > 4096 or "\n" in value or "\r" in value or "\0" in value:
            raise ValueError(f"Valor invalido para {key}")
        updates[key] = value

    removals = {str(key) for key in raw_removals}
    updates = {key: value for key, value in updates.items() if key not in removals}
    return updates, removals


def _configured_credential_values() -> dict[str, str]:
    """Read only whitelisted values for in-process encryption."""
    import config as current_config

    return {
        key: value
        for key in _CREDENTIAL_KEYS
        if isinstance((value := getattr(current_config, key, "")), str) and value
    }


def _sanitize_pairing_categories(raw_categories: object) -> dict:
    """Bound and normalize categories received from a decrypted pairing blob."""
    if not isinstance(raw_categories, dict) or len(raw_categories) > 500:
        raise ValueError("Categorias de pareamento invalidas")

    clean: dict[str, dict] = {}
    field_limits = {
        "label": 200,
        "emoji": 32,
        "tags": 20_000,
        "group": 200,
        "color": 32,
    }
    for raw_key, raw_category in raw_categories.items():
        if (
            not isinstance(raw_key, str)
            or not raw_key.strip()
            or len(raw_key) > 200
            or any(char in raw_key for char in "\r\n\0")
            or not isinstance(raw_category, dict)
        ):
            raise ValueError("Categoria de pareamento invalida")

        category: dict[str, object] = {}
        for field, limit in field_limits.items():
            value = raw_category.get(field)
            if value is None:
                continue
            if not isinstance(value, str) or len(value) > limit or "\0" in value:
                raise ValueError(f"Campo de categoria invalido: {field}")
            category[field] = value
        favorite = raw_category.get("favorite", False)
        if not isinstance(favorite, bool):
            raise ValueError("Campo de categoria invalido: favorite")
        category["favorite"] = favorite

        raw_source_tags = raw_category.get("source_tags")
        if raw_source_tags is not None:
            if not isinstance(raw_source_tags, dict) or len(raw_source_tags) > 30:
                raise ValueError("Tags por fonte invalidas")
            source_tags: dict[str, list[str]] = {}
            for raw_source, raw_queries in raw_source_tags.items():
                if (
                    not isinstance(raw_source, str)
                    or not raw_source.strip()
                    or len(raw_source) > 50
                    or not isinstance(raw_queries, list)
                    or len(raw_queries) > 50
                ):
                    raise ValueError("Tags por fonte invalidas")
                queries = []
                for raw_query in raw_queries:
                    if (
                        not isinstance(raw_query, str)
                        or not raw_query.strip()
                        or len(raw_query) > 2_000
                        or "\0" in raw_query
                    ):
                        raise ValueError("Consulta por fonte invalida")
                    queries.append(raw_query.strip())
                if queries:
                    source_tags[raw_source.strip()] = queries
            if source_tags:
                category["source_tags"] = source_tags

        category.setdefault("label", raw_key.replace("_", " ").title())
        category.setdefault("emoji", "🎨")
        category.setdefault("tags", raw_key)
        category.setdefault("group", "Geral")
        category.setdefault("color", "#6366f1")
        clean[raw_key.strip()] = category
    return clean


def _split_tags(tags_str: str) -> list[str]:
    """Divide tags por ';' ou nova linha em queries independentes (OR).
    'shadow_the_hedgehog; rouge_the_bat' → duas buscas separadas.
    'shadow_the_hedgehog rouge_the_bat'  → uma busca com AND (comportamento padrão do booru).
    """
    import re
    parts = re.split(r'[;\n]+', tags_str or "")
    return [p.strip() for p in parts if p.strip()]


def _migrate_legacy_bundled_categories() -> bool:
    """Quarantine the category list leaked by the obsolete Windows build."""
    if not getattr(sys, "frozen", False) or not USER_CATS_FILE.is_file():
        return False
    try:
        digest = hashlib.sha256(USER_CATS_FILE.read_bytes()).hexdigest()
        if digest not in _LEGACY_BUNDLED_CATEGORY_HASHES:
            return False
        backup = USER_CATS_FILE.with_name("user_categories.legacy-backup.json")
        if backup.exists():
            USER_CATS_FILE.unlink()
        else:
            USER_CATS_FILE.replace(backup)
        print("  [Migracao] Categorias do build antigo foram removidas da lista ativa.")
        return True
    except OSError as exc:
        print(f"  [Migracao] Nao foi possivel limpar categorias antigas: {exc}")
        return False


def _load_user_cats() -> dict:
    """Carrega categorias do usuario de user_categories.json."""
    with _USER_CATS_LOCK:
        try:
            _migrate_legacy_bundled_categories()
            if not USER_CATS_FILE.exists() and DEFAULT_USER_CATS_FILE.exists():
                USER_CATS_FILE.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(DEFAULT_USER_CATS_FILE, USER_CATS_FILE)
            with open(USER_CATS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("categories", {})
        except Exception:
            # fallback para categorias antigas do config
            from config import CATEGORIES as CK
            return {k: {"label": k.replace("_"," ").title(), "tags": k, "group": "Geral", "favorite": False, "emoji": "🎨", "color": "#6366f1"} for k in CK}


def _save_user_cats(cats: dict) -> None:
    """Salva categorias de forma atômica para evitar JSON truncado."""
    with _USER_CATS_LOCK:
        USER_CATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix="user_categories.",
            suffix=".tmp",
            dir=str(USER_CATS_FILE.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"categories": cats}, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, USER_CATS_FILE)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

app = FastAPI(title="artFinder")
app.include_router(library_router)

# A pasta inteira de downloads não é montada como StaticFiles: isso publicava
# artfinder.db, WAL e metadados JSON para qualquer pessoa na rede.
downloads_path = Path(DOWNLOAD_DIR)
downloads_path.mkdir(parents=True, exist_ok=True)


@app.middleware("http")
async def local_security_headers(request: Request, call_next):
    """Bloqueia mutações cross-site e adiciona headers seguros.

    Requisições sem Origin continuam aceitas para scripts/CLI locais. Browsers
    enviando formulários/fetch de outro site são rejeitados.
    """
    client_host = request.client.host if request.client else ""
    remote_lan_client = lan_mode_enabled() and not is_loopback_client(client_host)
    if remote_lan_client:
        query_token = request.query_params.get(LAN_QUERY_NAME)
        supplied_token = (
            request.headers.get("x-artfinder-token")
            or request.cookies.get(LAN_COOKIE_NAME)
            or query_token
        )
        if not token_matches(supplied_token):
            message = "Acesso LAN nao autorizado. Use o endereco completo mostrado no computador."
            if request.url.path.startswith("/api/"):
                return JSONResponse({"error": message}, status_code=401)
            return HTMLResponse(
                f"<h1>ArtFinder</h1><p>{message}</p>",
                status_code=401,
                headers={"Cache-Control": "no-store"},
            )

        # Exchange the one-time URL parameter for an HttpOnly session cookie,
        # then remove the secret from browser history and future Referer values.
        if query_token:
            remaining = [
                (key, value)
                for key, value in request.query_params.multi_items()
                if key != LAN_QUERY_NAME
            ]
            target = request.url.path
            if remaining:
                target += "?" + urlencode(remaining)
            response = RedirectResponse(target, status_code=303)
            response.set_cookie(
                LAN_COOKIE_NAME,
                query_token,
                httponly=True,
                samesite="strict",
                secure=False,  # LAN mode is HTTP; never expose it to the internet.
            )
            response.headers["Cache-Control"] = "no-store"
            return response

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin", "")
        sec_fetch_site = request.headers.get("sec-fetch-site", "")
        if sec_fetch_site == "cross-site":
            return JSONResponse({"error": "Requisicao cross-site bloqueada"}, status_code=403)
        if origin:
            try:
                if urlsplit(origin).netloc.lower() != request.headers.get("host", "").lower():
                    return JSONResponse({"error": "Origem nao autorizada"}, status_code=403)
            except Exception:
                return JSONResponse({"error": "Origem invalida"}, status_code=403)

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=()",
    )
    return response

# ── helpers ─────────────────────────────────────────────────────────

def _get_sources() -> dict:
    sources = {}
    try:
        from sources.bsky import fetch_posts
        from config import BSKY_HANDLE, BSKY_PASSWORD
        if BSKY_HANDLE and BSKY_PASSWORD:
            sources["Bluesky"] = fetch_posts
    except Exception as e:
        print(f"Error loading Bluesky: {e}")
        pass
    try:
        from sources.danbooru import fetch_posts
        sources["Danbooru"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.gelbooru import fetch_posts
        from config import GELBOORU_USER_ID, GELBOORU_API_KEY
        if GELBOORU_USER_ID and GELBOORU_API_KEY:
            sources["Gelbooru"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.safebooru import fetch_posts
        sources["Safebooru"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.e621 import fetch_posts
        sources["e621"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.deviantart import fetch_posts
        from config import DEVIANTART_CLIENT_ID, DEVIANTART_CLIENT_SECRET
        if DEVIANTART_CLIENT_ID and DEVIANTART_CLIENT_SECRET:
            sources["DeviantArt"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.tumblr import fetch_posts
        from config import TUMBLR_API_KEY
        if TUMBLR_API_KEY:
            sources["Tumblr"] = fetch_posts
    except Exception:
        pass
    try:
        from sources.pixiv import fetch_posts
        from config import PIXIV_REFRESH_TOKEN
        if PIXIV_REFRESH_TOKEN:
            sources["Pixiv"] = fetch_posts
    except Exception as e:
        print(f"Error loading Pixiv: {e}")
    return sources


# ── rotas ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve a interface principal."""
    html_path = Path(RESOURCE_DIR) / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    """Small startup/smoke-test endpoint without personal information."""
    return {
        "ok": True,
        "app": "ArtFinder",
        "mobile": os.getenv("ARTFINDER_MOBILE", "").strip() == "1",
        "lan": lan_mode_enabled(),
    }


@app.get("/ui/i18n.js", response_class=FileResponse)
async def i18n_script():
    """Serve the shared browser/desktop/mobile translation runtime."""
    return FileResponse(
        Path(RESOURCE_DIR) / "templates" / "i18n.js",
        media_type="application/javascript",
    )


@app.get("/ui/viewer.css", response_class=FileResponse)
async def viewer_styles():
    return FileResponse(Path(RESOURCE_DIR) / "templates" / "viewer.css", media_type="text/css")


@app.get("/ui/viewer.js", response_class=FileResponse)
async def viewer_script():
    return FileResponse(
        Path(RESOURCE_DIR) / "templates" / "viewer.js",
        media_type="application/javascript",
    )


@app.get("/api/sources")
async def list_sources():
    """Lista fontes ativas e explica quais ainda precisam de configuração."""
    import config as current_config

    active = list(_get_sources().keys())
    requirements = {
        "Gelbooru": ("GELBOORU_USER_ID", "GELBOORU_API_KEY"),
        "Pixiv": ("PIXIV_REFRESH_TOKEN",),
        "Tumblr": ("TUMBLR_API_KEY",),
        "DeviantArt": ("DEVIANTART_CLIENT_ID", "DEVIANTART_CLIENT_SECRET"),
        "Bluesky": ("BSKY_HANDLE", "BSKY_PASSWORD"),
    }
    unavailable = []
    for source, keys in requirements.items():
        if source in active:
            continue
        missing = [key for key in keys if not getattr(current_config, key, "")]
        unavailable.append({
            "name": source,
            "missing": missing,
            "reason": (
                "Configuração necessária: " + ", ".join(missing)
                if missing
                else "Conector indisponível nesta instalação"
            ),
        })
    return {"sources": active, "unavailable_sources": unavailable}


@app.get("/api/settings/credentials")
async def credential_settings():
    """List editable credential names and whether each one is configured."""
    return _credential_status_payload()


@app.post("/api/settings/credentials")
async def save_credential_settings(body: dict):
    """Save source credentials locally without ever returning their values."""
    try:
        updates, removals = _validate_credential_changes(
            body.get("values") or {}, body.get("clear") or []
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    try:
        _write_credentials(updates, removals)
        _apply_credentials(updates, removals)
    except OSError as exc:
        return JSONResponse({"error": f"Nao foi possivel salvar: {exc}"}, status_code=500)
    return {"ok": True, **_credential_status_payload()}


@app.post("/api/pairing/create")
async def create_pairing(request: Request, body: dict):
    """Create a five-minute encrypted export reachable only on the LAN."""
    client_host = request.client.host if request.client else ""
    if not is_loopback_client(client_host):
        return JSONResponse({"error": "Pareamento so pode ser criado no PC local"}, status_code=403)
    if os.getenv("ARTFINDER_MOBILE", "").strip() == "1":
        return JSONResponse({"error": "Crie o codigo no ArtFinder do PC"}, status_code=400)

    raw_include_categories = body.get("categories", True)
    raw_include_credentials = body.get("credentials", True)
    if not isinstance(raw_include_categories, bool) or not isinstance(
        raw_include_credentials, bool
    ):
        return JSONResponse({"error": "Opcoes de pareamento invalidas"}, status_code=400)
    include_categories = raw_include_categories
    include_credentials = raw_include_credentials
    if not include_categories and not include_credentials:
        return JSONResponse({"error": "Selecione algo para transferir"}, status_code=400)

    categories = _load_user_cats() if include_categories else {}
    try:
        credentials, _unused = (
            _validate_credential_changes(_configured_credential_values(), [])
            if include_credentials
            else ({}, set())
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    payload = {
        "version": 1,
        "source": socket.gethostname(),
        "sections": {
            "categories": include_categories,
            "credentials": include_credentials,
        },
        "categories": categories,
        "credentials": credentials,
    }
    try:
        session = pairing_manager.create(payload)
    except (PairingError, ImportError, OSError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    return {
        "ok": True,
        "expires_at": session.expires_at,
        "options": session.options,
        "summary": {
            "categories": len(categories),
            "credentials": len(credentials),
        },
    }


def _validated_pairing_endpoint(code: object) -> str:
    if not isinstance(code, str) or len(code) > 12_000:
        raise PairingError("Codigo de pareamento invalido")
    descriptor = parse_pairing_code(code.strip())
    endpoint = urlsplit(descriptor["url"])
    try:
        address = ipaddress.ip_address(endpoint.hostname or "")
    except ValueError as exc:
        raise PairingError("Endereco de pareamento invalido") from exc
    if (
        endpoint.scheme != "http"
        or not address.is_private
        or address.is_loopback
        or address.is_link_local
        or endpoint.username
        or endpoint.password
        or not endpoint.path.startswith("/v1/pair/")
    ):
        raise PairingError("Endereco de pareamento invalido")
    return descriptor["url"]


@app.post("/api/pairing/fetch")
async def fetch_pairing_envelope(request: Request, body: dict):
    """Fetch the encrypted LAN envelope through the local Android backend.

    Keeping this request out of the WebView avoids cross-origin/private-network
    restrictions. The AES key remains only in the code and decryption still
    happens locally in the WebView.
    """
    client_host = request.client.host if request.client else ""
    if not is_loopback_client(client_host):
        return JSONResponse({"error": "Pareamento permitido apenas neste dispositivo"}, status_code=403)
    try:
        endpoint = _validated_pairing_endpoint(body.get("code"))
    except PairingError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    def download_envelope():
        with _requests.Session() as session:
            session.trust_env = False
            return session.get(
                endpoint,
                headers={"Accept": "application/json"},
                timeout=(3, 8),
            )

    try:
        response = await asyncio.get_running_loop().run_in_executor(None, download_envelope)
    except _requests.Timeout:
        return JSONResponse({"error": "O PC demorou demais para responder"}, status_code=504)
    except _requests.RequestException:
        return JSONResponse(
            {"error": "Nao foi possivel acessar o PC. Verifique o Wi-Fi e o firewall"},
            status_code=502,
        )
    if response.status_code == 410:
        return JSONResponse({"error": "Codigo expirado ou ja utilizado"}, status_code=410)
    if response.status_code != 200 or len(response.content) > 600_000:
        return JSONResponse({"error": "Resposta de pareamento invalida"}, status_code=502)
    try:
        envelope = response.json()
    except ValueError:
        return JSONResponse({"error": "Resposta de pareamento invalida"}, status_code=502)
    if (
        not isinstance(envelope, dict)
        or envelope.get("version") != 1
        or envelope.get("algorithm") != "AES-256-GCM"
        or not isinstance(envelope.get("nonce"), str)
        or not isinstance(envelope.get("ciphertext"), str)
    ):
        return JSONResponse({"error": "Pacote de pareamento incompativel"}, status_code=502)
    return {"ok": True, "envelope": envelope}


@app.post("/api/pairing/import")
async def import_pairing(body: dict):
    """Persist a locally decrypted and strictly validated pairing payload."""
    if len(json.dumps(body, ensure_ascii=False)) > 600_000:
        return JSONResponse({"error": "Pacote de pareamento grande demais"}, status_code=413)
    payload = body.get("payload")
    mode = body.get("mode", "merge")
    if not isinstance(payload, dict) or payload.get("version") != 1:
        return JSONResponse({"error": "Pacote de pareamento invalido"}, status_code=400)
    if mode not in {"merge", "replace"}:
        return JSONResponse({"error": "Modo de importacao invalido"}, status_code=400)

    sections = payload.get("sections")
    if not isinstance(sections, dict):
        return JSONResponse({"error": "Secoes de pareamento invalidas"}, status_code=400)
    has_categories = sections.get("categories") is True
    has_credentials = sections.get("credentials") is True
    if not has_categories and not has_credentials:
        return JSONResponse({"error": "Pacote de pareamento vazio"}, status_code=400)

    try:
        imported_categories = (
            _sanitize_pairing_categories(payload.get("categories"))
            if has_categories
            else {}
        )
        imported_credentials, _unused = (
            _validate_credential_changes(payload.get("credentials"), [])
            if has_credentials
            else ({}, set())
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    old_categories = _load_user_cats()
    old_credentials = _configured_credential_values()
    new_categories = (
        imported_categories
        if has_categories and mode == "replace"
        else {**old_categories, **imported_categories}
    )

    try:
        with _USER_CATS_LOCK, _CREDENTIALS_LOCK:
            if has_categories:
                _save_user_cats(new_categories)
            if has_credentials and imported_credentials:
                _write_credentials(imported_credentials, set())
                _apply_credentials(imported_credentials, set())
    except Exception as exc:
        try:
            with _USER_CATS_LOCK, _CREDENTIALS_LOCK:
                if has_categories:
                    _save_user_cats(old_categories)
                if has_credentials:
                    previous_removals = _CREDENTIAL_KEYS - set(old_credentials)
                    _write_credentials(old_credentials, previous_removals)
                    _apply_credentials(old_credentials, previous_removals)
        except Exception:
            pass
        return JSONResponse({"error": f"Nao foi possivel importar: {exc}"}, status_code=500)

    return {
        "ok": True,
        "source": str(payload.get("source") or "PC"),
        "categories": len(imported_categories),
        "credentials": len(imported_credentials),
        "mode": mode,
    }


@app.get("/api/categories")
async def get_categories():
    """Retorna todas as categorias do usuario."""
    cats = _load_user_cats()
    return {"categories": cats}


_SOURCE_PREFIX_RE = None  # compilado sob demanda em create_category
_CATEGORY_SOURCE_NAMES = {
    "danbooru",
    "gelbooru",
    "safebooru",
    "e621",
    "pixiv",
    "tumblr",
    "bluesky",
    "deviantart",
}


def _parse_source_prefixes(tags_field: str) -> tuple[str, dict[str, list[str]]]:
    """Separa entradas "fonte: query" do campo de tags.

    "yamato_(one_piece); pixiv: ヤマト(ONEPIECE); tumblr: yamato one piece"
    → ("yamato_(one_piece)", {"pixiv": ["ヤマト(ONEPIECE)"], "tumblr": [...]})
    """
    import re
    global _SOURCE_PREFIX_RE
    if _SOURCE_PREFIX_RE is None:
        _SOURCE_PREFIX_RE = re.compile(
            r"(?i)^(danbooru|gelbooru|safebooru|e621|pixiv|tumblr|bsky|bluesky|deviantart)\s*:\s*(.+)$"
        )
    src_tags: dict[str, list[str]] = {}
    booru_parts: list[str] = []
    for part in _split_tags(tags_field):
        m = _SOURCE_PREFIX_RE.match(part)
        if m:
            src = m.group(1).lower()
            if src == "bsky":
                src = "bluesky"   # nome usado em _get_sources()
            src_tags.setdefault(src, []).append(m.group(2).strip())
        else:
            booru_parts.append(part)
    return "; ".join(booru_parts), src_tags


def _normalize_category_key(raw_key: object, existing: dict) -> str:
    """Return an URL-safe key while preserving keys created by older releases."""
    if not isinstance(raw_key, str):
        return ""
    raw_key = raw_key.strip().lower()
    if raw_key in existing:
        return raw_key
    ascii_key = unicodedata.normalize("NFKD", raw_key).encode("ascii", "ignore").decode()
    import re
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9_-]+", "_", ascii_key)).strip("_-")


def _normalize_category_source_tags(raw_source_tags: object) -> dict[str, list[str]]:
    """Validate and normalize exact queries configured for each source."""
    if raw_source_tags is None:
        return {}
    if not isinstance(raw_source_tags, dict) or len(raw_source_tags) > len(_CATEGORY_SOURCE_NAMES) + 1:
        raise ValueError("Tags por fonte invalidas")

    normalized: dict[str, list[str]] = {}
    for raw_source, raw_queries in raw_source_tags.items():
        if not isinstance(raw_source, str):
            raise ValueError("Fonte invalida")
        source = raw_source.strip().lower()
        if source == "bsky":
            source = "bluesky"
        if source not in _CATEGORY_SOURCE_NAMES:
            raise ValueError(f"Fonte desconhecida: {source}")
        queries = raw_queries if isinstance(raw_queries, list) else [raw_queries]
        if len(queries) > 50:
            raise ValueError("Muitas consultas para uma fonte")
        clean: list[str] = []
        for raw_query in queries:
            if not isinstance(raw_query, str):
                raise ValueError("Consulta por fonte invalida")
            for query in _split_tags(raw_query):
                if len(query) > 2_000 or "\0" in query:
                    raise ValueError("Consulta por fonte invalida")
                if query not in clean:
                    clean.append(query)
        if clean:
            normalized[source] = clean
    return normalized


def _auto_map_category(key: str) -> dict:
    """Descobre tags específicas por fonte (Pixiv/e621) e salva na categoria.
    Roda em thread. Não sobrescreve overrides já existentes (manuais)."""
    try:
        from utils.tagmap import suggest_source_tags
        cats = _load_user_cats()
        if key not in cats:
            return {}
        found: dict[str, list[str]] = {}
        for tg in _split_tags(cats[key].get("tags", "")):
            for src, qs in suggest_source_tags(tg).items():
                dst = found.setdefault(src, [])
                dst.extend(q for q in qs if q not in dst)
        if not found:
            print(f"  [AutoTag] '{key}': nenhuma tag específica encontrada.")
            return {}
        # Re-lê antes de salvar (minimiza conflito com edições concorrentes)
        cats = _load_user_cats()
        if key not in cats:
            return {}
        st = cats[key].setdefault("source_tags", {})
        added = {src: qs for src, qs in found.items() if src not in st}
        if added:
            st.update(added)
            _save_user_cats(cats)
        print(f"  [AutoTag] '{key}': {added or 'nada novo (overrides manuais mantidos)'}")
        return added
    except Exception as e:
        print(f"  [AutoTag] '{key}': erro: {e}")
        return {}


@app.post("/api/categories")
async def create_category(body: dict):
    """Cria ou atualiza uma categoria.
    Body: {key, label, tags, group, emoji, color, favorite,
           source_tags?: {fonte: [queries]}, replace_source_tags?: bool,
           auto_map?: bool}

    No campo tags, entradas com prefixo de fonte viram a query exata
    daquela fonte:  "yamato_(one_piece); pixiv: ヤマト(ONEPIECE)".
    Sem override manual, o app descobre tags do Pixiv/e621 sozinho em
    segundo plano (wiki do Danbooru + validação nas APIs reais).
    """
    cats = _load_user_cats()
    key = _normalize_category_key(body.get("key", ""), cats)
    raw_tags = body.get("tags", "")
    if not isinstance(raw_tags, str):
        return JSONResponse({"error": "Tags invalidas"}, status_code=400)
    booru_tags, prefixed_source_tags = _parse_source_prefixes(raw_tags)
    if not key or not booru_tags:
        return JSONResponse({"error": "key e tags principais sao obrigatorios"}, status_code=400)
    if len(booru_tags) > 20_000:
        return JSONResponse({"error": "Tags excedem o limite permitido"}, status_code=400)

    try:
        explicit_source_tags = _normalize_category_source_tags(body.get("source_tags"))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    src_tags = {source: list(queries) for source, queries in prefixed_source_tags.items()}
    for source, queries in explicit_source_tags.items():
        destination = src_tags.setdefault(source, [])
        destination.extend(query for query in queries if query not in destination)

    def clean_text(field: str, default: str, limit: int) -> str:
        value = body.get(field, default)
        if not isinstance(value, str) or "\0" in value or len(value) > limit:
            raise ValueError(f"Campo invalido: {field}")
        return value.strip() or default

    try:
        label = clean_text("label", key, 200)
        emoji = clean_text("emoji", "🎨", 32)
        group = clean_text("group", "Geral", 200)
        color = clean_text("color", "#6366f1", 32)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    import re
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return JSONResponse({"error": "Campo invalido: color"}, status_code=400)
    if not isinstance(body.get("favorite", False), bool):
        return JSONResponse({"error": "Campo invalido: favorite"}, status_code=400)
    if not isinstance(body.get("replace_source_tags", False), bool):
        return JSONResponse({"error": "Campo invalido: replace_source_tags"}, status_code=400)

    old = cats.get(key) or {}
    # Se as tags booru não mudaram, preserva os overrides antigos;
    # se mudaram, descarta (estariam mapeando o personagem errado). O editor
    # visual envia replace_source_tags para também permitir apagar um override.
    if (
        not body.get("replace_source_tags", False)
        and _split_tags(old.get("tags", "")) == _split_tags(booru_tags)
    ):
        merged = dict(old.get("source_tags") or {})
        merged.update(src_tags)
        src_tags = merged

    cats[key] = {
        "label":    label,
        "emoji":    emoji,
        "tags":     booru_tags,
        "group":    group,
        "favorite": body.get("favorite", False),
        "color":    color,
    }
    if src_tags:
        cats[key]["source_tags"] = src_tags
    _save_user_cats(cats)

    # Descoberta automática (Pixiv/e621) em segundo plano — não bloqueia a UI
    if booru_tags and body.get("auto_map", True):
        asyncio.get_running_loop().run_in_executor(None, _auto_map_category, key)

    return {"ok": True, "key": key, "category": cats[key]}


@app.post("/api/categories/{key}/auto-map")
async def auto_map_category(key: str):
    """(Re)executa a descoberta automática de tags por fonte da categoria."""
    cats = _load_user_cats()
    if key not in cats:
        return JSONResponse({"error": "Categoria nao encontrada"}, status_code=404)
    loop = asyncio.get_running_loop()
    added = await loop.run_in_executor(None, _auto_map_category, key)
    return {"ok": True, "added": added,
            "source_tags": _load_user_cats().get(key, {}).get("source_tags", {})}


@app.get("/api/suggest-source-tags")
async def suggest_source_tags_api(tags: str = ""):
    """Sugere queries por fonte para uma query booru (não salva nada)."""
    tags = (tags or "").strip()
    if not tags:
        return {"suggestions": {}}
    from utils.tagmap import suggest_source_tags
    loop = asyncio.get_running_loop()
    out = await loop.run_in_executor(None, suggest_source_tags, tags)
    return {"suggestions": out}


@app.post("/api/categories/{key}/favorite")
async def toggle_favorite(key: str):
    """Alterna o status de favorito de uma categoria."""
    cats = _load_user_cats()
    if key not in cats:
        return JSONResponse({"error": "Categoria nao encontrada"}, status_code=404)
    cats[key]["favorite"] = not cats[key].get("favorite", False)
    _save_user_cats(cats)
    return {"ok": True, "favorite": cats[key]["favorite"]}


@app.delete("/api/categories/{key}")
async def delete_category(key: str):
    """Remove uma categoria."""
    cats = _load_user_cats()
    if key not in cats:
        return JSONResponse({"error": "Categoria nao encontrada"}, status_code=404)
    del cats[key]
    _save_user_cats(cats)
    return {"ok": True}

@app.post("/api/categories/reorder")
async def reorder_categories(body: dict):
    """Salva a nova ordem das categorias após drag-and-drop."""
    order = body.get("order", [])
    if not order:
        return JSONResponse({"error": "order is required"}, status_code=400)
    cats = _load_user_cats()
    new_cats = {}
    for key in order:
        if key in cats:
            new_cats[key] = cats[key]
    # append any keys not in order (safety)
    for key in cats:
        if key not in new_cats:
            new_cats[key] = cats[key]
    _save_user_cats(new_cats)
    return {"ok": True}

@app.post("/api/block-artist")
async def block_artist(body: dict):
    artist = body.get("artist")
    if not artist:
        return JSONResponse({"error": "Nenhum artista fornecido"}, status_code=400)
    success = add_blocked_artist(artist)
    if not success:
        return JSONResponse({"error": "Erro ao bloquear artista"}, status_code=500)
    return {"ok": True, "artist": artist.strip().lower()}


@app.get("/api/stats")
async def stats():
    """Estatisticas detalhadas do banco + disco."""
    base = get_stats()
    dl_path = Path(DOWNLOAD_DIR).resolve()
    by_cat: dict[str, int] = {}
    total_bytes = 0
    if dl_path.exists():
        for cat_dir in dl_path.iterdir():
            if cat_dir.is_dir() and cat_dir.name != "metadata" and not cat_dir.name.startswith("."):
                files = [f for f in cat_dir.glob("*") if f.is_file()]
                if files:
                    by_cat[cat_dir.name] = len(files)
                    total_bytes += sum(f.stat().st_size for f in files)
    base["by_category"] = by_cat
    base["disk_mb"] = round(total_bytes / 1_048_576, 1)
    # Contadores de triagem (Usar / Talvez / Rever depois / Não gostei)
    try:
        from utils.database import get_all_ratings
        by_rating: dict[str, int] = {}
        for v in get_all_ratings().values():
            by_rating[v] = by_rating.get(v, 0) + 1
        base["by_rating"] = by_rating
    except Exception:
        base["by_rating"] = {}
    return base


# ── RATINGS (triagem) ─────────────────────────────────────────────────────

@app.get("/api/ratings")
async def list_ratings():
    """Retorna {uid: rating} de todas as artes avaliadas."""
    from utils.database import get_all_ratings
    return {"ratings": get_all_ratings()}


@app.get("/api/rated-posts")
async def rated_posts():
    """Retorna todas as artes avaliadas com metadados (para o painel de triagem)."""
    from utils.database import _connect
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT r.uid, r.rating AS aval, r.rated_at,
                   p.source, p.post_id, p.url, p.preview_url, p.page_url,
                   p.artist, p.score, p.width, p.height, p.tags,
                   p.rating, p.category
            FROM ratings r
            LEFT JOIN posts p ON p.uid = r.uid
            ORDER BY r.rated_at DESC
        """).fetchall()
        items = []
        for row in rows:
            uid = row["uid"]
            src = row["source"] or (uid.split(":", 1)[0] if ":" in uid else "")
            pid = row["post_id"] or (uid.split(":", 1)[1] if ":" in uid else uid)
            items.append({
                "uid": uid, "aval": row["aval"], "rated_at": row["rated_at"] or 0,
                "source": src, "post_id": pid,
                "url": row["url"] or "", "preview_url": row["preview_url"] or "",
                "page_url": row["page_url"] or "", "artist": row["artist"] or "",
                "score": row["score"] or 0, "width": row["width"] or 0,
                "height": row["height"] or 0, "tags": row["tags"] or "",
                "rating": row["rating"] or "sfw", "category": row["category"] or "",
            })
        return {"items": items}
    finally:
        conn.close()


@app.post("/api/ratings")
async def rate_post(body: dict):
    """Avalia uma arte. Body: {source, id, aval: usar|talvez|depois|nao}.
    aval vazio/null remove a avaliação.
    (O campo se chama 'aval' porque 'rating' já é usado para SFW/NSFW no post.)"""
    source  = body.get("source", "")
    post_id = str(body.get("id") or body.get("post_id") or "")
    rating  = (body.get("aval") or "").strip().lower()
    if not source or not post_id:
        return JSONResponse({"error": "source e id são obrigatórios"}, status_code=400)

    from utils.database import set_rating, remove_rating, VALID_RATINGS
    if not rating:
        removed = remove_rating(source, post_id)
        return {"ok": True, "removed": removed}
    if rating not in VALID_RATINGS:
        return JSONResponse({"error": f"rating inválido (use: {', '.join(sorted(VALID_RATINGS))})"},
                            status_code=400)
    set_rating(source, post_id, rating)

    # Guarda os metadados no cache de posts para não perder a imagem de vista
    try:
        from utils.database import upsert_posts_batch
        upsert_posts_batch([body])
    except Exception:
        pass
    return {"ok": True, "rating": rating}


# ── FAVORITES ─────────────────────────────────────────────────────────────

@app.get("/api/favorites")
async def list_favorites():
    """Retorna todas as artes favoritadas."""
    from utils.database import get_favorites
    return {"favorites": get_favorites()}


@app.post("/api/favorites")
async def add_to_favorites(body: dict):
    """Salva arte nos favoritos E dispara download para o disco."""
    source  = body.get("source", "")
    post_id = str(body.get("id") or body.get("post_id") or "")
    if not source or not post_id:
        return JSONResponse({"error": "source e id são obrigatórios"}, status_code=400)
    raw_collection_ids = body.get("collection_ids", [])
    if not isinstance(raw_collection_ids, list) or len(raw_collection_ids) > 100:
        return JSONResponse({"error": "collection_ids inválido"}, status_code=400)
    try:
        collection_ids = [int(value) for value in raw_collection_ids]
    except (TypeError, ValueError):
        return JSONResponse({"error": "collection_ids inválido"}, status_code=400)
    from utils.database import add_favorite
    inserted = add_favorite(
        source=source, post_id=post_id,
        artist=body.get("artist", ""),
        url=body.get("url", ""),
        preview_url=body.get("preview_url", ""),
        page_url=body.get("page_url", ""),
    )
    if "collection_ids" in body:
        from utils.database import set_favorite_collections
        set_favorite_collections(source, post_id, collection_ids)
    # Auto-download: salva o arquivo no disco também, a menos que skip_download seja True
    skip_download = body.get("skip_download", False)
    dl_url   = body.get("url") or body.get("preview_url", "")
    category = body.get("category") or "favoritos"

    if dl_url and not skip_download:
        from utils.database import is_downloaded
        if not is_downloaded(source, post_id):
            try:
                dl_posts = [{
                    "url":         dl_url,
                    "preview_url": body.get("preview_url", dl_url),
                    "source":      source,
                    "id":          post_id,
                    "artist":      body.get("artist", ""),
                    "score":       body.get("score", 0),
                    "width":       body.get("width", 0),
                    "height":      body.get("height", 0),
                    "tags":        body.get("tags", ""),
                    "rating":      body.get("rating", "sfw"),
                    "page_url":    body.get("page_url", ""),
                    # sem esta chave o downloader ignora a categoria do lote e
                    # salva na pasta do artista/misc em vez de "favoritos"
                    "category":    category,
                }]
                await download_batch(dl_posts, category)
            except Exception as e:
                print(f"  [DEBUG - Baixar] Falha ao baixar arte {post_id} automaticamente: {e}")
    
    # Salva os metadados dessa arte no cache (tabela posts) para a Galeria usar depois
    try:
        from utils.database import upsert_posts_batch
        upsert_posts_batch([{
            "source": source, "id": post_id, "url": body.get("url", ""),
            "preview_url": body.get("preview_url", ""), "page_url": body.get("page_url", ""),
            "artist": body.get("artist", ""), "score": body.get("score", 0),
            "width": body.get("width", 0), "height": body.get("height", 0),
            "tags": body.get("tags", ""), "rating": body.get("rating", "sfw"),
            "category": body.get("category", "")
        }])
    except Exception as e:
        print(f"  [DEBUG - Metadados] Erro ao salvar cache da arte favoritada: {e}")

    print(f"  [DEBUG - Guardar/Baixar] ID {post_id} salvo. Auto-download={not skip_download}")
    return {"ok": True, "inserted": inserted, "already_existed": not inserted}


@app.delete("/api/favorites/{source}/{post_id}")
async def remove_from_favorites(source: str, post_id: str):
    """Remove uma arte dos favoritos."""
    from utils.database import remove_favorite
    removed = remove_favorite(source, post_id)
    return {"ok": True, "removed": removed}



@app.get("/api/downloaded-ids")
async def downloaded_ids():
    """Retorna lista de source_ids ja baixados para filtro hide-downloaded."""
    from utils.database import _connect
    conn = _connect()
    try:
        rows = conn.execute("SELECT source_id FROM downloads").fetchall()
        return {"ids": [r[0] for r in rows]}
    finally:
        conn.close()


@app.get("/api/gallery-items")
async def gallery_items():
    """Retorna metadados das imagens baixadas para a galeria interna."""
    from utils.database import _connect, get_blacklisted_uids
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT d.source, d.source_id, d.file_path, d.artist, d.score,
                   d.downloaded_at, d.tags, d.width, d.height, d.public_uri,
                   p.rating, p.page_url, p.category, p.preview_url, p.url as orig_url
            FROM downloads d
            LEFT JOIN posts p ON p.uid = d.source_id
            ORDER BY d.downloaded_at DESC
        """).fetchall()
        # Respeita ocultar-pra-sempre (blacklist) e artistas bloqueados
        blacklist = get_blacklisted_uids()
        blocked   = set(get_blocked_artists())
        items = []
        dl_dir = Path(DOWNLOAD_DIR).resolve()
        for row in rows:
            (
                source,
                source_id,
                file_path,
                artist,
                score,
                dl_at,
                tags,
                w,
                h,
                public_uri,
                rating,
                page_url,
                category,
                prev_url,
                orig_url,
            ) = row
            if not file_path:
                continue
            if source_id in blacklist:
                continue
            if (artist or "").strip().lower() in blocked:
                continue
            fp = Path(file_path)
            if not fp.is_absolute():
                fp = (Path(DOWNLOAD_DIR).parent / fp).resolve()
            if not fp.exists():
                continue
            try:
                rel = fp.relative_to(dl_dir).as_posix()
            except ValueError:
                rel = "/".join(fp.parts[-2:])
            items.append({
                "source":        source,
                "uid":           source_id or f"{source}:?",
                "rel_path":      rel,
                "artist":        artist or "",
                "score":         score or 0,
                "downloaded_at": dl_at or 0,
                "tags":          tags or "",
                "width":         w or 0,
                "height":        h or 0,
                "public_uri":    public_uri or "",
                "rating":        rating or "sfw",
                "page_url":      page_url or "",
                "category":      category or "",
                "preview_url":   prev_url or "",
                "orig_url":      orig_url or "",
            })
        return {"items": items}
    finally:
        conn.close()


@app.get("/api/tag-suggest")
async def tag_suggest(q: str = ""):
    """Sugere tags reais (autocomplete do Danbooru) para o termo digitado."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"tags": []}
    import requests
    from config import DANBOORU_LOGIN, DANBOORU_API_KEY

    def _fetch():
        params = {"search[query]": q, "search[type]": "tag_query", "limit": 10}
        auth = (DANBOORU_LOGIN, DANBOORU_API_KEY) if (DANBOORU_LOGIN and DANBOORU_API_KEY) else None
        r = requests.get(
            "https://danbooru.donmai.us/autocomplete.json",
            params=params, auth=auth,
            headers={"User-Agent": "ArtFinder/2.0 (personal archiver)"},
            timeout=6,
        )
        r.raise_for_status()
        return r.json()

    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, _fetch)
    except Exception as e:
        return {"tags": [], "error": str(e)}

    out = []
    for d in data if isinstance(data, list) else []:
        val = d.get("value") or d.get("label") or ""
        if not val:
            continue
        out.append({
            "value":      val,
            "post_count": d.get("post_count") or 0,
            "category":   d.get("category", 0),
        })
    return {"tags": out}


@app.get("/api/duplicates")
async def duplicates(threshold: int = 8):
    """Agrupa imagens baixadas que são quase idênticas (distância de Hamming
    do pHash <= threshold). Retorna só os grupos com 2+ imagens."""
    from utils.database import _connect
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT source, source_id, file_path, phash, artist, score, width, height "
            "FROM downloads WHERE phash IS NOT NULL AND phash != ''"
        ).fetchall()
    finally:
        conn.close()

    dl_dir = Path(DOWNLOAD_DIR).resolve()
    items = []
    for source, sid, file_path, phash, artist, score, w, h in rows:
        if not file_path:
            continue
        fp = Path(file_path)
        if not fp.is_absolute():
            fp = (Path(DOWNLOAD_DIR).parent / fp).resolve()
        if not fp.exists():
            continue
        try:
            rel = fp.relative_to(dl_dir).as_posix()
        except ValueError:
            rel = "/".join(fp.parts[-2:])
        try:
            bits = int(phash, 16)
        except (TypeError, ValueError):
            continue
        items.append({
            "uid": sid, "source": source, "rel_path": rel,
            "artist": artist or "", "score": score or 0,
            "width": w or 0, "height": h or 0, "_bits": bits,
        })

    # União por distância de Hamming (union-find simples)
    n = len(items)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for i in range(n):
        for j in range(i + 1, n):
            if bin(items[i]["_bits"] ^ items[j]["_bits"]).count("1") <= threshold:
                union(i, j)

    clusters: dict[int, list] = {}
    for idx in range(n):
        clusters.setdefault(find(idx), []).append(items[idx])

    groups = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        for m in members:
            m.pop("_bits", None)
        # maior resolução primeiro (a "melhor" pra manter)
        members.sort(key=lambda m: (m["width"] * m["height"], m["score"]), reverse=True)
        groups.append(members)

    return {"groups": groups, "count": len(groups)}


@app.post("/api/blacklist")
async def blacklist_posts(body: dict):
    """Adiciona UIDs à blacklist permanente (nunca mais aparecem na busca)."""
    uids = body.get("uids", [])
    if not uids:
        return {"added": 0}
    count = add_to_blacklist(uids)
    # Remove do banco de posts também (para liberar espaço)
    from utils.database import delete_posts
    delete_posts(uids)
    print(f"  [DEBUG - Blacklist] {count} artes ocultadas para sempre. (UIDs: {uids})")
    return {"added": count}


@app.get("/api/blacklist")
async def get_blacklist_count():
    """Retorna quantos itens estão na blacklist."""
    from utils.database import get_blacklisted_uids
    uids = get_blacklisted_uids()
    return {"count": len(uids)}


@app.post("/api/sync-db")
async def sync_database():
    """
    Sincroniza o banco com o disco:
    remove registros cujos arquivos foram apagados manualmente.
    """
    from utils.database import sync_db
    removed = sync_db()
    stats = get_stats()
    return {"removed": removed, "remaining": stats["total"],
            "message": f"{removed} registro(s) removido(s) do banco."}


@app.post("/api/clear-db")
async def clear_database():
    """Apaga TODOS os registros do banco (nao apaga arquivos do disco)."""
    from utils.database import clear_db
    removed = clear_db()
    return {"removed": removed,
            "message": f"Banco limpo: {removed} registro(s) removido(s)."}


def _run_search_sync(categories, source_names, pages, custom_cats, all_sources, errors=None):
    """Executa busca sincrona – chamada em thread do executor."""
    all_posts: list[dict] = []
    seen_ids: set[str] = set()
    blocked_artists: set[str] = get_blocked_artists()
    try:
        from utils.database import get_blacklisted_uids
        blacklist_ids = get_blacklisted_uids()
    except Exception:
        blacklist_ids = set()

    def add_posts(posts, cat):
        for p in normalize_posts(posts):
            uid = f"{p.get('source','?')}:{p.get('id','?')}"
            if uid in seen_ids or uid in blacklist_ids:
                continue   # 'return' abortava o lote inteiro na 1ª duplicata
            artist_lower = (p.get("artist") or "").strip().lower()
            if artist_lower and artist_lower in blocked_artists:
                continue
            seen_ids.add(uid)
            if not p.get("category"):
                p["category"] = cat
            all_posts.append(p)

    for cat in categories:
        for sn in source_names:
            fn = all_sources.get(sn)
            if not fn: continue
            try:
                res = fn(cat, max_pages=pages)
                add_posts(res, cat)
                print(f"  [Busca] {sn} -> '{cat}': retornou {len(res)} artes")
            except Exception as e:
                print(f"  [search] {sn}/{cat}: {e}")
                if errors is not None:
                    errors.append({"source": sn, "category": cat, "error": str(e)})

    for ccat in custom_cats:
        label = ccat.get("label","custom"); ctags = ccat.get("tags","")
        if not ctags: continue
        for sn in source_names:
            fn = all_sources.get(sn)
            if not fn: continue
            try:
                # tags= explícito: o antigo hack de injetar em m.CATEGORIES
                # era race condition com buscas simultâneas (duas abas/celular)
                res = fn(label, max_pages=pages, tags=ctags)
                add_posts(res, label)
                print(f"  [Busca] {sn} -> '{label}': retornou {len(res)} artes")
            except Exception as e:
                print(f"  [search-custom] {sn}/{label}: {e}")
                if errors is not None:
                    errors.append({"source": sn, "category": label, "error": str(e)})

    all_posts.sort(key=lambda x: x.get("score") or 0, reverse=True)
    return all_posts


@app.post("/api/search")
async def search(body: dict):
    """Busca sincrona (fallback)."""
    # Resolve tags das categorias selecionadas
    user_cats  = _load_user_cats()
    cat_keys   = body.get("categories", list(user_cats.keys()))
    extra_cats = body.get("custom_categories", [])
    resolved   = []
    for k in cat_keys:
        if k not in user_cats:
            continue
        for tg in _split_tags(user_cats[k]["tags"]):
            resolved.append({"label": k, "tags": tg})
    resolved  += extra_cats
    source_names = body.get("sources", [])
    pages        = max(1, min(int(body.get("pages", 2)), 50))
    all_sources  = _get_sources()
    if not source_names: source_names = list(all_sources.keys())
    else: source_names = [s for s in source_names if s in all_sources]
    loop = asyncio.get_running_loop()
    errors: list[dict] = []
    posts = await loop.run_in_executor(
        None,
        lambda: _run_search_sync([], source_names, pages, resolved, all_sources, errors),
    )
    return {"posts": posts, "total": len(posts), "errors": errors}












@app.post("/api/search-stream")




async def search_stream(body: dict, request: Request):
    """Busca com SSE: envia posts fonte por fonte com progresso em tempo real."""
    if not HAS_SSE:
        return JSONResponse(await search(body))

    # Resolve categorias do usuario
    user_cats    = _load_user_cats()
    cat_keys     = body.get("categories", list(user_cats.keys()))
    extra_cats   = body.get("custom_categories", [])  # categorias ad-hoc do frontend
    source_names = body.get("sources", [])
    pages        = max(1, min(int(body.get("pages", 2)), 50))
    min_score    = int(body.get("min_score", 0))
    all_sources  = _get_sources()
    if not source_names: source_names = list(all_sources.keys())
    else: source_names = [s for s in source_names if s in all_sources]

    # Monta os combos (categoria × fonte). Cada combo é
    # (label, fonte, tags_booru | None, query_direta | None):
    #  - se a categoria tem source_tags para a fonte, usa essas queries
    #    como estão (query_direta) — uma busca por query;
    #  - senão, usa as tags booru (divididas por ';'), que cada fonte
    #    converte do seu jeito.
    combos: list[tuple[str, str, str | None, str | None]] = []
    for k in cat_keys:
        if k not in user_cats:
            continue
        ucat = user_cats[k]
        stags = {s.lower(): v for s, v in (ucat.get("source_tags") or {}).items()}
        for sn in source_names:
            ov = stags.get(sn.lower())
            if ov:
                for q in (ov if isinstance(ov, list) else [ov]):
                    if q:
                        combos.append((k, sn, None, q))
            else:
                for tg in _split_tags(ucat.get("tags", "")):
                    combos.append((k, sn, tg, None))
    for c in extra_cats:
        for sn in source_names:
            for tg in _split_tags(c.get("tags", "")):
                combos.append((c.get("label", "custom"), sn, tg, None))

    # blacklist_ids: UIDs permanentemente bloqueados (persiste em TODOS os combos)
    blacklist_ids: set[str] = set()
    try:
        from utils.database import get_blacklisted_uids
        blacklist_ids = get_blacklisted_uids()
        if blacklist_ids:
            print(f"  [Blacklist] {len(blacklist_ids)} UIDs bloqueados carregados.")
    except Exception:
        blacklist_ids = set()
    blocked_artists = get_blocked_artists()

    async def generator():
        loop = asyncio.get_running_loop()
        total_unique_count = 0
        errors: list[dict] = []
        
        # Deduplicação na requisição inteira para não aparecer repetido na mesma tela
        request_seen: set[str] = set()

        for i,(cat,src_name,custom_tags,direct) in enumerate(combos):
            if await request.is_disconnected(): break
            fn = all_sources.get(src_name)
            if not fn: continue

            yield {"event":"progress","data":json.dumps({"source":src_name,"cat":cat,"done":i,"total":len(combos)})}

            def _fetch(fn=fn, cat=cat, custom_tags=custom_tags, direct=direct):
                # tags= explícito: o antigo hack de injetar em m.CATEGORIES
                # era race condition com buscas simultâneas (duas abas/celular)
                if direct:
                    return fn(cat, max_pages=pages, direct=direct)
                if custom_tags:
                    return fn(cat, max_pages=pages, tags=custom_tags)
                return fn(cat, max_pages=pages)

            try:
                posts = await loop.run_in_executor(None, _fetch)
                posts = normalize_posts(posts, src_name)
                print(f"  [Busca] {src_name} -> '{cat}': retornou {len(posts)} artes")
            except Exception as e:
                errors.append({"source": src_name, "category": cat, "error": str(e)})
                yield {"event":"progress","data":json.dumps({"source":src_name,"cat":cat,"done":i+1,"total":len(combos),"error":str(e)})}
                continue

            new_posts = []
            for p in posts:
                # 0a) Filtra por score mínimo
                if int(p.get("score") or 0) < min_score:
                    continue
                
                # 0b) Filtra por artista bloqueado
                artist_lower = (p.get("artist") or "").strip().lower()
                if artist_lower and artist_lower in blocked_artists:
                    continue

                # 0c) Filtro central de IA (segunda camada de defesa)
                if is_ai_generated(p):
                    indicators = matched_ai_indicators(p)
                    print(f"  [AI-filter] Bloqueado: {p.get('source')}:{p.get('id')} (indicadores: {indicators})")
                    continue

                uid = f"{p.get('source','?')}:{p.get('id','?')}"
                # Bloqueia se estiver na blacklist permanente
                if uid in blacklist_ids:
                    continue
                # Bloqueia duplicatas DENTRO da mesma busca inteira
                if uid in request_seen:
                    continue
                request_seen.add(uid)
                # normalize_posts() já garante todos os campos com tipos corretos,
                # mas deixa category "" para fontes que não a preenchem (bsky,
                # deviantart) — setdefault não corrige valor vazio, então
                # atribuímos explicitamente para o download ir pra pasta certa.
                if not p.get("category"):
                    p["category"] = cat
                new_posts.append(p)


            novos_db = 0
            known_in_db = 0
            send_posts = new_posts  # fallback: envia todos
            total_unique_count += len(new_posts)

            if new_posts:
                # Agora NÃO salvamos mais no banco (sem histórico inútil)
                # Salvaremos só quando a pessoa Baixar ou Guardar de fato.
                uids_batch = [f"{p.get('source')}:{p.get('id')}" for p in new_posts]
                already_set = await loop.run_in_executor(None, known_uids, uids_batch)
                known_in_db = len(already_set)
                novos_db = len(new_posts) - known_in_db
                send_posts = new_posts

            print(f"  [DEBUG - Busca] Fonte '{src_name}' (Tag '{cat}'):")
            print(f"    - Retornou da internet: {len(new_posts)} artes")
            print(f"    - Já estavam em cache no banco: {known_in_db} artes")
            print(f"    - Mostrando na sua tela agora: {len(send_posts)} artes\n")

            yield {"event": "posts", "data": json.dumps({
                "source":     src_name,
                "cat":        cat,
                "done":       i + 1,
                "total":      len(combos),
                "posts":      send_posts,
                "new_in_db":  novos_db,
                "known_in_db": known_in_db,
            })}
            await asyncio.sleep(0)

        yield {"event": "done", "data": json.dumps({
            "total_unique": total_unique_count,
            "errors": errors,
        })}


    return EventSourceResponse(generator())


@app.post("/api/download")
async def download(body: dict):
    """
    Baixa as imagens selecionadas (resposta simples, sem streaming).
    Para progresso em tempo real use /api/download-stream.
    """
    posts = body.get("posts", [])
    if not posts:
        return {"downloaded": 0, "message": "Nenhum post recebido."}

    from collections import defaultdict
    by_cat: dict[str, list] = defaultdict(list)
    for p in posts:
        by_cat[p.get("category", "misc")].append(p)

    # Salva os metadados das artes para a Galeria
    try:
        from utils.database import upsert_posts_batch
        upsert_posts_batch(posts)
    except:
        pass

    # await direto: run_download_batch usa asyncio.run(), que crasha
    # dentro de um event loop já em execução (RuntimeError).
    total = 0
    for cat, cat_posts in by_cat.items():
        n = await download_batch(cat_posts, cat)
        total += n

    return {"downloaded": total, "message": f"{total} imagem(ns) baixada(s)."}


@app.post("/api/download-stream")
async def download_stream(body: dict, request: Request):
    """
    Download com SSE: envia progresso por imagem em tempo real.
    Eventos: 'progress' {done, total, ok, filename} | 'done' {downloaded, failed}
    """
    if not HAS_SSE:
        r = await download(body)
        return JSONResponse(r)

    posts = body.get("posts", [])
    if not posts:
        async def _empty():
            yield {"event": "done", "data": json.dumps({"downloaded": 0, "failed": 0})}
        return EventSourceResponse(_empty())

    from collections import defaultdict
    by_cat: dict[str, list] = defaultdict(list)
    for p in posts:
        by_cat[p.get("category", "misc")].append(p)

    # Salva os metadados das artes para a Galeria
    try:
        from utils.database import upsert_posts_batch
        upsert_posts_batch(posts)
    except Exception as e:
        print(f"Erro ao salvar posts no banco: {e}")

    progress_q: asyncio.Queue = asyncio.Queue()

    async def _run_downloads():
        from utils.downloader import download_batch
        total_all = len(posts)
        done_before = 0
        ok_before = 0
        gallery_pending = 0
        try:
            for cat, cat_posts in by_cat.items():
                async def _category_progress(done, _total, ok_count, msg):
                    nonlocal gallery_pending
                    if msg.endswith(" · Galeria pendente"):
                        gallery_pending += 1
                    await progress_q.put({
                        "done": done_before + done,
                        "total": total_all,
                        "ok": ok_before + ok_count,
                        "msg": msg,
                        "gallery_pending": gallery_pending,
                    })

                downloaded = await download_batch(
                    cat_posts,
                    cat,
                    on_progress=_category_progress,
                )
                done_before += len(cat_posts)
                ok_before += downloaded
        except Exception as e:
            print(f"  [download-stream] Erro no lote: {e}")
        finally:
            # Sentinel SEMPRE enviado — sem isso o generator ficava travado
            # 30s no timeout quando o download falhava com exceção.
            await progress_q.put(None)

    async def generator():
        loop = asyncio.get_running_loop()
        task = loop.create_task(_run_downloads())
        ok_total = 0
        done_total = 0
        gallery_pending_total = 0
        while True:
            if await request.is_disconnected():
                task.cancel(); break
            try:
                item = await asyncio.wait_for(progress_q.get(), timeout=30)
            except asyncio.TimeoutError:
                break
            if item is None:
                break
            ok_total   = item["ok"]
            done_total = item["done"]
            gallery_pending_total = item.get("gallery_pending", 0)
            yield {"event": "progress", "data": json.dumps(item)}
        try:
            await asyncio.shield(task)
        except (asyncio.CancelledError, Exception):
            pass  # task cancelada pelo disconnect ou erro já logado
        failed = done_total - ok_total
        yield {"event": "done", "data": json.dumps({
            "downloaded": ok_total,
            "failed": failed,
            "gallery_pending": gallery_pending_total,
        })}

    return EventSourceResponse(generator())



# Cache simples em memória: url -> (bytes, content_type) (FIFO,
# limitado por nº de entradas E por memória total — imagens HD do
# Pixiv/Danbooru chegam a dezenas de MB cada)
_proxy_cache: dict[str, tuple[bytes, str]] = {}
_PROXY_CACHE_MAX = 200
_PROXY_CACHE_MAX_BYTES = 200 * 1024 * 1024   # 200 MB
_proxy_cache_bytes = 0
_proxy_cache_lock = threading.Lock()

def _get_referer(url: str) -> str:
    """Retorna o Referer correto para cada domínio — evita bloqueio de hotlink."""
    from utils.network import is_domain
    host = urlsplit(url).hostname
    if is_domain(host, "gelbooru.com"):
        return "https://gelbooru.com/"
    if is_domain(host, "donmai.us"):
        return "https://danbooru.donmai.us/"
    if is_domain(host, "safebooru.org"):
        return "https://safebooru.org/"
    if is_domain(host, "e621.net"):
        return "https://e621.net/"
    if is_domain(host, "rule34.xxx"):
        return "https://rule34.xxx/"
    # Pixiv (i.pximg.net) bloqueia hotlink sem este Referer específico
    if is_domain(host, "pximg.net") or is_domain(host, "pixiv.net"):
        return "https://www.pixiv.net/"
    # fallback genérico
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}/"
    except Exception:
        return "https://danbooru.donmai.us/"


def _fetch_image_sync(url: str) -> tuple[bytes, str]:
    """Fetch a bounded image while validating the URL and every redirect."""
    global _proxy_cache_bytes

    from config import DANBOORU_API_KEY, DANBOORU_LOGIN, MAX_FILE_MB
    from utils.network import is_domain, validate_redirect, validate_remote_url

    with _proxy_cache_lock:
        cached = _proxy_cache.get(url)
    if cached is not None:
        return cached

    current_url = url
    max_bytes = MAX_FILE_MB * 1024 * 1024
    for redirect_count in range(6):
        parsed = validate_remote_url(current_url)
        danbooru = is_domain(parsed.hostname, "donmai.us")
        headers = {
            "User-Agent": (
                "Discordbot/2.0" if danbooru else
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            "Referer": _get_referer(current_url),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        auth = (
            (DANBOORU_LOGIN, DANBOORU_API_KEY)
            if danbooru and DANBOORU_LOGIN and DANBOORU_API_KEY
            else None
        )
        with _requests.get(
            current_url,
            headers=headers,
            auth=auth,
            timeout=20,
            stream=True,
            allow_redirects=False,
        ) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                if redirect_count >= 5:
                    raise ValueError("Redirecionamentos demais")
                current_url = validate_redirect(
                    current_url,
                    response.headers.get("location", ""),
                )
                continue
            response.raise_for_status()
            content_type = (
                response.headers.get("content-type", "").split(";", 1)[0].lower()
            )
            if content_type not in {
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/webp",
                "image/avif",
                "image/bmp",
            }:
                raise ValueError("O servidor nao retornou uma imagem")
            try:
                declared_size = int(response.headers.get("content-length", "0"))
            except ValueError:
                declared_size = 0
            if declared_size > max_bytes:
                raise ValueError("Imagem maior que o limite configurado")

            chunks = bytearray()
            for chunk in response.iter_content(64 * 1024):
                if chunk:
                    chunks.extend(chunk)
                    if len(chunks) > max_bytes:
                        raise ValueError("Imagem maior que o limite configurado")
            data = bytes(chunks)
            break
    else:
        raise ValueError("Falha ao buscar imagem")

    if len(data) <= _PROXY_CACHE_MAX_BYTES:
        with _proxy_cache_lock:
            previous = _proxy_cache.pop(url, None)
            if previous:
                _proxy_cache_bytes -= len(previous[0])
            _proxy_cache[url] = (data, content_type)
            _proxy_cache_bytes += len(data)
            while _proxy_cache and (
                len(_proxy_cache) > _PROXY_CACHE_MAX
                or _proxy_cache_bytes > _PROXY_CACHE_MAX_BYTES
            ):
                oldest = next(iter(_proxy_cache))
                _proxy_cache_bytes -= len(_proxy_cache.pop(oldest)[0])
    return data, content_type


@app.get("/api/proxy-image")
async def proxy_image(url: str):
    """
    Proxy para imagens: carrega do servidor externo com o Referer correto
    e repassa ao browser. Não bloqueia o event loop e tem cache em memória.
    """
    loop = asyncio.get_running_loop()
    try:
        data, content_type = await loop.run_in_executor(None, _fetch_image_sync, url)
        return Response(content=data, media_type=content_type,
                        headers={"Cache-Control": "private, max-age=3600"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)



_DOWNLOADED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_PRIVATE_DOWNLOAD_ROOTS = {"metadata", ".thumbs"}


def _resolve_download_image(rel_path: str, *, must_exist: bool = True) -> Path:
    """Resolve a user-provided private image path without allowing traversal."""
    if not isinstance(rel_path, str) or not rel_path or Path(rel_path).is_absolute():
        raise ValueError("Caminho invalido")
    download_root = Path(DOWNLOAD_DIR).resolve()
    file_path = (download_root / rel_path).resolve()
    try:
        relative = file_path.relative_to(download_root)
    except ValueError as exc:
        raise ValueError("Caminho invalido") from exc
    if (
        not relative.parts
        or relative.parts[0].lower() in _PRIVATE_DOWNLOAD_ROOTS
        or file_path.suffix.lower() not in _DOWNLOADED_IMAGE_EXTENSIONS
    ):
        raise PermissionError("Arquivo nao permitido")
    if must_exist and not file_path.is_file():
        raise FileNotFoundError("Arquivo nao encontrado")
    return file_path


@app.get("/api/thumb")
async def thumb(rel_path: str):
    """
    Serve uma miniatura JPEG (~480px) da imagem baixada, gerando e cacheando
    em downloads/.thumbs/ na primeira vez. Deixa a galeria muito mais leve.
    GIFs são servidos no original (a miniatura perderia a animação).
    """
    from fastapi.responses import FileResponse
    dl_dir = Path(DOWNLOAD_DIR).resolve()
    if Path(rel_path).is_absolute():
        return JSONResponse({"error": "Caminho invalido"}, status_code=400)
    src = (dl_dir / rel_path).resolve()
    try:
        relative = src.relative_to(dl_dir)
    except ValueError:
        return JSONResponse({"error": "Caminho inválido"}, status_code=400)
    if (
        not relative.parts
        or relative.parts[0].lower() in {"metadata", ".thumbs"}
        or src.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ):
        return JSONResponse({"error": "Arquivo nao permitido"}, status_code=403)
    if not src.is_file():
        return JSONResponse({"error": "Arquivo não encontrado"}, status_code=404)
    if src.suffix.lower() == ".gif":
        return FileResponse(src)

    tpath = dl_dir / ".thumbs" / relative.parent / (src.stem + ".jpg")
    if not tpath.exists() or tpath.stat().st_mtime < src.stat().st_mtime:
        def _gen():
            from PIL import Image
            tpath.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((480, 8000))
                im.save(tpath, "JPEG", quality=82)
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _gen)
        except Exception:
            return FileResponse(src)   # fallback: serve o original
    return FileResponse(tpath, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/file")
async def downloaded_file(rel_path: str):
    """Serve only downloaded image files, never the database or metadata."""
    try:
        file_path = _resolve_download_image(rel_path)
    except ValueError:
        return JSONResponse({"error": "Caminho invalido"}, status_code=400)
    except PermissionError:
        return JSONResponse({"error": "Arquivo nao permitido"}, status_code=403)
    except FileNotFoundError:
        return JSONResponse({"error": "Arquivo nao encontrado"}, status_code=404)

    return FileResponse(
        file_path,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.post("/api/export-image")
async def export_image_to_android_gallery(body: dict):
    """Publish an existing private download to Android's public photo gallery."""
    from utils.android_media import (
        AndroidMediaError,
        android_media_available,
        publish_image,
    )

    if not android_media_available():
        return JSONResponse(
            {"error": "Disponível somente no aplicativo Android"},
            status_code=409,
        )
    rel_path = body.get("rel_path", "")
    try:
        file_path = _resolve_download_image(rel_path)
    except ValueError:
        return JSONResponse({"error": "Caminho invalido"}, status_code=400)
    except PermissionError:
        return JSONResponse({"error": "Arquivo nao permitido"}, status_code=403)
    except FileNotFoundError:
        return JSONResponse({"error": "Arquivo nao encontrado"}, status_code=404)

    from utils.database import get_download_by_file_path, set_download_public_uri

    record = await asyncio.to_thread(get_download_by_file_path, str(file_path))
    if not record:
        return JSONResponse({"error": "Download não registrado"}, status_code=404)
    if record.get("public_uri"):
        return {"ok": True, "already_exported": True, "public_uri": record["public_uri"]}

    try:
        public_uri = await asyncio.to_thread(publish_image, file_path)
    except AndroidMediaError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    updated = await asyncio.to_thread(
        set_download_public_uri,
        str(file_path),
        public_uri,
    )
    if not updated:
        # Avoid an untracked public copy if the database row disappeared while
        # the MediaStore stream was being written.
        try:
            from utils.android_media import delete_image as delete_public_image

            await asyncio.to_thread(delete_public_image, public_uri)
        except AndroidMediaError:
            pass
        return JSONResponse({"error": "Download não registrado"}, status_code=409)
    return {"ok": True, "public_uri": public_uri}


@app.post("/api/delete-image")
async def delete_image(body: dict):
    """
    Apaga uma imagem do disco e remove o registro do banco.
    Body: {rel_path: str}  (caminho relativo dentro de downloads/)
    """
    rel_path = body.get("rel_path", "")
    if not rel_path:
        return JSONResponse({"error": "rel_path ausente"}, status_code=400)
    try:
        file_path = _resolve_download_image(rel_path, must_exist=False)
    except ValueError:
        return JSONResponse({"error": "Caminho invalido"}, status_code=400)
    except PermissionError:
        return JSONResponse({"error": "Arquivo nao permitido"}, status_code=403)

    dl_dir = Path(DOWNLOAD_DIR).resolve()
    from utils.database import (
        _connect,
        _invalidate_phash_cache,
        get_download_by_file_path,
        set_download_public_uri,
    )

    record = await asyncio.to_thread(get_download_by_file_path, str(file_path))
    public_uri = (record or {}).get("public_uri", "")
    public_deleted = None
    if public_uri:
        from utils.android_media import (
            AndroidMediaError,
            android_media_available,
            delete_image as delete_public_image,
        )

        if android_media_available():
            try:
                public_deleted = await asyncio.to_thread(
                    delete_public_image,
                    public_uri,
                )
            except AndroidMediaError as exc:
                # Preserve the private copy and database URI so deletion can be
                # retried instead of silently orphaning a public image.
                return JSONResponse({"error": str(exc)}, status_code=502)
            await asyncio.to_thread(set_download_public_uri, str(file_path), "")

    deleted_file = False
    if file_path.exists():
        try:
            file_path.unlink()
            deleted_file = True
            # remove JSON de metadados e thumbnail se existirem
            cat     = file_path.parent.name
            meta_p  = dl_dir / "metadata" / cat / (file_path.stem + ".json")
            if meta_p.exists():
                meta_p.unlink()
            thumb_p = dl_dir / ".thumbs" / cat / (file_path.stem + ".jpg")
            if thumb_p.exists():
                thumb_p.unlink()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # Remove do banco pelo caminho
    conn = _connect()
    try:
        cursor = conn.execute(
            "DELETE FROM downloads WHERE file_path = ?",
            (str(file_path),),
        )
        conn.commit()
        if cursor.rowcount:
            _invalidate_phash_cache()
    finally:
        conn.close()

    return {
        "deleted": deleted_file,
        "path": rel_path,
        "public_deleted": public_deleted,
    }


# ── entry point ─────────────────────────────────────────────────────────

def open_browser():
    webbrowser.open("http://localhost:7860")

def _lan_ip() -> str:
    """Descobre o IP local da máquina na rede (pra acessar do celular)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Não envia nada de fato; só força o SO a escolher a interface de saída.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return ""
    finally:
        s.close()

if __name__ == "__main__":
    import logging
    # Suprime o ConnectionResetError do Windows (WinError 10054) — inofensivo,
    # aparece quando o browser fecha conexoes SSE antes do servidor.
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)

    allow_lan = lan_mode_enabled()
    lan = _lan_ip() if allow_lan else ""
    print("=" * 52)
    print("  ArtFinder  —  Interface Visual")
    print("=" * 52)
    print("  Neste PC:    http://localhost:7860")
    if lan:
        token = ensure_lan_token()
        print(f"  No celular:  http://{lan}:7860/?{LAN_QUERY_NAME}={token}")
        print("  Link protegido por token; use apenas em uma rede privada confiavel.")
    print("  Pressione Ctrl+C para encerrar.")
    print("=" * 52)
    Timer(1.2, open_browser).start()
    uvicorn.run(
        app,
        # LAN binding is opt-in and non-loopback requests require the session
        # token enforced by local_security_headers above.
        host="0.0.0.0" if allow_lan else "127.0.0.1",  # nosec B104
        port=7860,
        log_level="warning",
    )

