"""Shared validation helpers for URLs fetched by the application."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import SplitResult, urljoin, urlsplit


class RemoteURLRejected(ValueError):
    """Raised when a remote URL is unsafe or malformed."""


def is_domain(hostname: str | None, domain: str) -> bool:
    """Return True only for the exact domain or one of its subdomains."""
    host = (hostname or "").rstrip(".").lower()
    root = domain.rstrip(".").lower()
    return host == root or host.endswith("." + root)


def validate_remote_url(url: str) -> SplitResult:
    """Validate a public HTTP(S) URL and return its parsed representation."""
    if not isinstance(url, str) or not url.strip():
        raise RemoteURLRejected("URL ausente")

    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise RemoteURLRejected("Apenas URLs http/https sao permitidas")
    if parsed.username or parsed.password:
        raise RemoteURLRejected("Credenciais na URL nao sao permitidas")
    if not parsed.hostname:
        raise RemoteURLRejected("Host ausente na URL")

    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise RemoteURLRejected("Porta invalida na URL") from exc
    if port not in {80, 443}:
        raise RemoteURLRejected("Apenas portas web padrao sao permitidas")

    public_addresses(parsed.hostname, port)
    return parsed


def public_addresses(host: str, port: int, family: int = socket.AF_UNSPEC) -> list:
    """Resolve once and return only addresses that may be connected to."""
    try:
        addresses = socket.getaddrinfo(
            host,
            port,
            family=family,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise RemoteURLRejected(
            f"Nao foi possivel resolver o host: {host}"
        ) from exc
    if not addresses:
        raise RemoteURLRejected("O host nao possui endereco de rede")

    for info in addresses:
        address = info[4][0].split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise RemoteURLRejected("Endereco IP invalido") from exc
        if not ip.is_global:
            raise RemoteURLRejected("Destino de rede interno ou reservado bloqueado")

    return addresses


def validate_redirect(base_url: str, location: str) -> str:
    """Resolve and validate a redirect target."""
    target = urljoin(base_url, location)
    validate_remote_url(target)
    return target
