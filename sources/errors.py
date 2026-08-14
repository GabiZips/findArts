"""Public, credential-safe errors shared by artwork source connectors."""

from __future__ import annotations

import json

import requests


class SourceUnavailableError(RuntimeError):
    """A source could not be queried; its message is safe for the UI."""


def public_source_error(source: str, exc: BaseException) -> str:
    """Classify a request failure without leaking URLs, query strings or keys."""
    if isinstance(exc, requests.Timeout):
        reason = "tempo limite; a rede pode estar bloqueando ou atrasando a fonte"
    elif isinstance(exc, requests.ConnectionError):
        reason = "nao foi possivel conectar; verifique DNS, firewall ou bloqueio da rede"
    elif isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        if status in {401, 403}:
            reason = f"acesso recusado (HTTP {status}); confira as credenciais ou a rede"
        elif status == 429:
            reason = "limite temporario de requisicoes atingido (HTTP 429)"
        elif status:
            reason = f"a fonte respondeu com erro HTTP {status}"
        else:
            reason = "a fonte recusou a solicitacao"
    elif isinstance(exc, (json.JSONDecodeError, ValueError, KeyError)):
        reason = "a fonte retornou uma resposta invalida ou a autenticacao expirou"
    else:
        reason = "falha inesperada no conector"
    return f"{source}: {reason}."


def source_unavailable(source: str, exc: BaseException) -> SourceUnavailableError:
    return SourceUnavailableError(public_source_error(source, exc))
