import asyncio
import socket
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

import requests
import app
import config
from utils.http_transport import PublicHTTPAdapter, PublicResolver
from utils.network import RemoteURLRejected, validate_remote_url


def address(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 443))]


class PinnedTransportTests(unittest.TestCase):
    def test_sync_transport_pins_address_and_keeps_tls_hostname(self):
        adapter = PublicHTTPAdapter()
        self.addCleanup(adapter.close)
        request = requests.Request("GET", "https://images.example/art.png").prepare()
        with patch("utils.network.socket.getaddrinfo", return_value=address("8.8.8.8")):
            pool = adapter.get_connection_with_tls_context(request, True)
        self.assertEqual(pool.host, "8.8.8.8")
        self.assertEqual(pool.assert_hostname, "images.example")
        self.assertEqual(pool.conn_kw["server_hostname"], "images.example")
        self.assertEqual(pool.cert_reqs, "CERT_REQUIRED")
        self.assertEqual(request.headers["Host"], "images.example")

    def test_dns_change_between_initial_validation_and_connection_is_rejected(self):
        adapter = PublicHTTPAdapter()
        self.addCleanup(adapter.close)
        request = requests.Request("GET", "https://images.example/art.png").prepare()
        with patch("utils.network.socket.getaddrinfo", side_effect=[address("8.8.8.8"), address("127.0.0.1")]):
            validate_remote_url(request.url)
            with self.assertRaises(RemoteURLRejected):
                adapter.get_connection_with_tls_context(request, True)

    def test_async_resolver_checks_actual_connection_addresses(self):
        async def run():
            resolver = PublicResolver()
            with patch("utils.network.socket.getaddrinfo", return_value=address("8.8.8.8")):
                values = await resolver.resolve("images.example", 443)
            self.assertEqual(values[0]["host"], "8.8.8.8")
            self.assertEqual(values[0]["hostname"], "images.example")
            with patch("utils.network.socket.getaddrinfo", return_value=address("192.168.1.1")):
                with self.assertRaises(RemoteURLRejected):
                    await resolver.resolve("images.example", 443)
            await resolver.close()
        asyncio.run(run())

    def test_private_literal_mixed_answers_proxy_and_disabled_tls_rejected(self):
        adapter = PublicHTTPAdapter()
        self.addCleanup(adapter.close)
        request = requests.Request("GET", "https://images.example/a").prepare()
        with patch("utils.network.socket.getaddrinfo", return_value=address("8.8.8.8") + address("10.0.0.1")):
            with self.assertRaises(RemoteURLRejected):
                adapter.get_connection_with_tls_context(request, True)
        for verify, proxies in ((False, None), (True, {"https": "http://proxy.example"})):
            with self.assertRaises(RemoteURLRejected):
                adapter.get_connection_with_tls_context(request, verify, proxies)
        for ip in ("127.0.0.1", "10.0.0.1", "169.254.169.254"):
            with patch("utils.network.socket.getaddrinfo", return_value=address(ip)):
                with self.assertRaises(RemoteURLRejected):
                    adapter.get_connection_with_tls_context(requests.Request("GET", f"http://{ip}/a").prepare(), True)

    def test_danbooru_credentials_only_on_exact_https_host(self):
        for url, expected in (("http://danbooru.donmai.us/a", None),
                              ("https://cdn.donmai.us/a", None),
                              ("https://danbooru.donmai.us/a", ("dummy", "dummy"))):
            response = MagicMock(status_code=200)
            response.__enter__.return_value = response
            response.headers = {"content-type": "image/png"}
            response.iter_content.return_value = [b"test"]
            with patch.object(config, "DANBOORU_LOGIN", "dummy"), \
                 patch.object(config, "DANBOORU_API_KEY", "dummy"), \
                 patch.object(app, "_proxy_cache", {}), \
                 patch("utils.network.validate_remote_url", side_effect=urlsplit), \
                 patch.object(app, "public_image_get", return_value=response) as get:
                app._fetch_image_sync(url)
            self.assertEqual(get.call_args.kwargs["auth"], expected)
