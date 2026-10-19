"""Session-token authentication for ArtFinder's optional LAN mode."""

from __future__ import annotations

import hmac
import ipaddress
import os
import secrets


LAN_COOKIE_NAME = "artfinder_lan_session"
LAN_QUERY_NAME = "access_token"


def lan_mode_enabled() -> bool:
    return os.getenv("ARTFINDER_LAN", "").strip() == "1"


def ensure_lan_token() -> str:
    """Return the configured LAN token or create an ephemeral session token."""
    token = os.getenv("ARTFINDER_LAN_TOKEN", "").strip()
    if not token:
        token = secrets.token_urlsafe(32)
        os.environ["ARTFINDER_LAN_TOKEN"] = token
    return token


def is_loopback_client(host: str | None) -> bool:
    value = (host or "").strip().strip("[]").split("%", 1)[0]
    if value.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def token_matches(candidate: str | None) -> bool:
    expected = os.getenv("ARTFINDER_LAN_TOKEN", "").strip()
    supplied = (candidate or "").strip()
    return bool(expected and supplied and hmac.compare_digest(expected.encode("utf-8"), supplied.encode("utf-8")))
