"""Public-only image transports: validate the IP actually used by the socket."""

import asyncio
from contextlib import contextmanager
import socket
from urllib.parse import urlsplit

from aiohttp.abc import AbstractResolver
import requests
from requests.adapters import HTTPAdapter

from utils.network import RemoteURLRejected, public_addresses


class PublicResolver(AbstractResolver):
    async def resolve(self, host, port=0, family=socket.AF_INET):
        addresses = await asyncio.to_thread(public_addresses, host, port, family)
        return [dict(hostname=host, host=info[4][0], port=port, family=info[0],
                     proto=info[2], flags=socket.AI_NUMERICHOST) for info in addresses]

    async def close(self):
        pass


class PublicHTTPAdapter(HTTPAdapter):
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        if proxies or verify is False:
            raise RemoteURLRejected("Proxy ou TLS sem verificacao nao permitido")
        parsed = urlsplit(request.url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password):
            raise RemoteURLRejected("URL invalida")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in {80, 443}:
            raise RemoteURLRejected("Porta nao permitida")
        addresses = public_addresses(parsed.hostname, port)
        # Prefer IPv4 when both families exist, avoiding IPv6-only route failures.
        selected = next((info for info in addresses if info[0] == socket.AF_INET), addresses[0])
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(request, verify, cert)
        host_params["host"] = selected[4][0]
        if parsed.scheme == "https":
            pool_kwargs.update(server_hostname=parsed.hostname, assert_hostname=parsed.hostname)
        request.headers["Host"] = parsed.netloc
        return self.poolmanager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)


@contextmanager
def public_image_get(url, **kwargs):
    """A one-request session; redirects must be validated by the caller."""
    kwargs["allow_redirects"] = False
    kwargs["stream"] = True
    with requests.Session() as session:
        session.trust_env = False
        session.mount("http://", PublicHTTPAdapter())
        session.mount("https://", PublicHTTPAdapter())
        with session.get(url, **kwargs) as response:
            yield response
