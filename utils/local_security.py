"""Host validation and process-local browser sessions (including loopback)."""

import hmac
import ipaddress
import secrets
from urllib.parse import urlsplit

SESSION_COOKIE = "artfinder_local_session"
_SESSION_TOKEN = secrets.token_urlsafe(32)


def trusted_host(host: str, *, lan: bool = False) -> bool:
    """Never trust arbitrary DNS names, even if Origin matches Host."""
    try:
        if any(char.isspace() or ord(char) < 32 for char in host):
            return False
        parsed = urlsplit("http://" + host)
        if (not host or parsed.username or parsed.password or parsed.path
                or parsed.query or parsed.fragment or parsed.port == 0):
            return False
        name = parsed.hostname or ""
        if name == "localhost":
            return True
        address = ipaddress.ip_address(name)
        return address.is_loopback or (lan and address.is_private
                                       and not address.is_unspecified
                                       and not address.is_link_local)
    except ValueError:
        return False


def valid_session(candidate: str | None) -> bool:
    return bool(candidate and hmac.compare_digest(candidate.encode("utf-8"), _SESSION_TOKEN.encode("ascii")))


def set_session_cookie(response) -> None:
    response.set_cookie(SESSION_COOKIE, _SESSION_TOKEN, httponly=True,
                        samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
