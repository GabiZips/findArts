import asyncio
import json
import unittest
from http.cookies import SimpleCookie
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Request
import app
from utils import pairing
from utils.local_security import SESSION_COOKIE, trusted_host
from utils.lan_security import token_matches
from artfinder.domain.search import build_search_plan


def request(path="/api/categories", method="GET", host="127.0.0.1:7860", headers=()):
    return Request({"type": "http", "http_version": "1.1", "method": method,
                    "scheme": "http", "path": path, "raw_path": path.encode(),
                    "query_string": b"", "headers": [(b"host", host.encode()), *headers],
                    "client": ("127.0.0.1", 50000), "server": ("127.0.0.1", 7860)})


class LocalSecurityTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(app.os.environ, {"ARTFINDER_LAN": "0"})
        self.env.start()
        self.addCleanup(self.env.stop)

    @staticmethod
    async def next_route(_request):
        return app.Response("ok")

    def test_foreign_host_rejected_even_with_matching_origin(self):
        response = asyncio.run(app.local_security_headers(request(
            method="POST", host="untrusted.example:7860",
            headers=[(b"origin", b"http://untrusted.example:7860"), (b"sec-fetch-site", b"same-origin")],
        ), self.next_route))
        self.assertEqual(response.status_code, 400)

    def test_host_validation(self):
        for host in ("evil.example", "localhost@evil.example", "localhost/path", "127.0.0.1:99999", "localhost\n", ""):
            self.assertFalse(trusted_host(host), host)
        for host in ("localhost:7860", "127.0.0.1:7860", "[::1]:7860"):
            self.assertTrue(trusted_host(host), host)
        self.assertFalse(trusted_host("192.168.1.5:7860"))
        self.assertTrue(trusted_host("192.168.1.5:7860", lan=True))

    def test_local_api_needs_session_but_health_stays_available(self):
        for path, expected in (("/api/categories", 401), ("/api/health", 200)):
            response = asyncio.run(app.local_security_headers(request(path), self.next_route))
            self.assertEqual(response.status_code, expected)

    def test_interface_bootstrap_issues_httponly_session(self):
        response = asyncio.run(app.local_security_headers(request("/"), self.next_route))
        cookies = SimpleCookie(response.headers["set-cookie"])
        self.assertTrue(cookies[SESSION_COOKIE]["httponly"])
        self.assertEqual(cookies[SESSION_COOKIE]["samesite"], "strict")
        response = asyncio.run(app.local_security_headers(request(headers=[
            (b"cookie", f"{SESSION_COOKIE}={cookies[SESSION_COOKIE].value}".encode()),
        ]), self.next_route))
        self.assertEqual(response.status_code, 200)

    def test_cross_site_request_blocked_even_with_session(self):
        response = asyncio.run(app.local_security_headers(request(
            method="POST", headers=[(b"sec-fetch-site", b"cross-site")],
        ), self.next_route))
        self.assertEqual(response.status_code, 403)

    def test_non_ascii_token_is_rejected_without_server_error(self):
        with patch.dict(app.os.environ, {"ARTFINDER_LAN_TOKEN": "expected"}):
            self.assertFalse(token_matches("não-autorizado"))


class SearchParityTests(unittest.TestCase):
    def test_json_and_stream_share_override_ai_score_and_deduplication(self):
        categories = {"vex": {"tags": "vex_league_of_legends", "source_tags": {"bsky": ["Vex League of Legends"]}}}
        source = MagicMock(return_value=[
            {"id": "ai", "tags": "ai_generated", "score": 200},
            {"id": "low", "score": 1},
            {"id": "ok", "score": 200}, {"id": "ok", "score": 200},
        ])
        body = {"categories": ["vex"], "sources": ["bsky"], "pages": 1, "min_score": 100}
        async def run():
            result = await app.search(body)
            stream_request = request()
            stream_request.is_disconnected = AsyncMock(return_value=False)
            streamed = await app.search_stream(body, stream_request)
            posts = []
            async for event in streamed.body_iterator:
                if event["event"] == "posts":
                    posts.extend(json.loads(event["data"])["posts"])
            return result, posts
        with patch.object(app, "_load_user_cats", return_value=categories), \
             patch.object(app, "_get_sources", return_value={"bsky": source}), \
             patch.object(app, "get_blocked_artists", return_value=set()), \
             patch("utils.database.get_blacklisted_uids", return_value=set()), \
             patch.object(app, "known_uids", return_value=set()):
            result, posts = asyncio.run(run())
        self.assertEqual([p["id"] for p in result["posts"]], ["ok"])
        self.assertEqual(result["posts"], posts)
        for call in source.call_args_list:
            self.assertEqual(call.kwargs, {"max_pages": 1, "direct": "Vex League of Legends"})

    def test_invalid_plan_is_rejected(self):
        for body in ({"pages": "x"}, {"categories": "vex"}, {"custom_categories": ["x"]},
                     {"custom_categories": [{"tags": "vex", "source_tags": ["x"]}]}):
            with self.assertRaises(ValueError):
                build_search_plan(body, {}, {"bsky": object()})


class PairingNetworkTests(unittest.TestCase):
    def test_redirect_and_oversized_body_rejected(self):
        code = pairing._pairing_code("http://192.168.1.20:54321/v1/pair/token", b"k" * 32)
        for status, chunks in ((302, []), (200, [b"x" * 400_000, b"x" * 400_000])):
            response = MagicMock(status_code=status)
            response.__enter__.return_value = response
            response.iter_content.return_value = chunks
            session = MagicMock()
            session.__enter__.return_value = session
            session.get.return_value = response
            with patch.object(app._requests, "Session", return_value=session):
                result = asyncio.run(app.fetch_pairing_envelope(request(), {"code": code}))
            self.assertEqual(result.status_code, 502)
            self.assertFalse(session.get.call_args.kwargs["allow_redirects"])
            self.assertTrue(session.get.call_args.kwargs["stream"])
            response.__exit__.assert_called_once()

    def test_pairing_rejects_query_fragment_and_non_private_networks(self):
        for url in ("http://192.168.1.20:5/v1/pair/t?q=1", "http://192.168.1.20:5/v1/pair/t#f",
                    "http://127.0.0.1:5/v1/pair/t", "http://0.0.0.0:5/v1/pair/t"):
            with self.assertRaises(pairing.PairingError):
                app._validated_pairing_endpoint(pairing._pairing_code(url, b"k" * 32))
