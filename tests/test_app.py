import asyncio
import json
import socket
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch

import app
import config
from fastapi import Request
from utils.downloader import _safe_component
from utils.network import RemoteURLRejected, is_domain, validate_remote_url


class NetworkSafetyTests(unittest.TestCase):
    def test_domain_match_does_not_accept_lookalikes(self):
        self.assertTrue(is_domain("cdn.donmai.us", "donmai.us"))
        self.assertFalse(is_domain("donmai.us.evil.example", "donmai.us"))

    def test_loopback_destination_is_rejected(self):
        resolved = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 80),
            )
        ]
        with patch("utils.network.socket.getaddrinfo", return_value=resolved):
            with self.assertRaises(RemoteURLRejected):
                validate_remote_url("http://example.test/image.jpg")

    def test_non_web_scheme_is_rejected(self):
        with self.assertRaises(RemoteURLRejected):
            validate_remote_url("file:///windows/system.ini")


class AppRouteTests(unittest.TestCase):
    @staticmethod
    def _request(
        path: str = "/api/health",
        query: bytes = b"",
        client: str = "192.168.1.50",
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> Request:
        return Request({
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query,
            "headers": headers or [(b"host", b"192.168.1.10:7860")],
            "client": (client, 54321),
            "server": ("192.168.1.10", 7860),
            "root_path": "",
        })

    def test_interface_loads_shared_language_runtime(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn('id="languageSelect"', html)
        self.assertIn('src="/ui/i18n.js"', html)

        script = asyncio.run(app.i18n_script())
        self.assertEqual(Path(script.path).name, "i18n.js")

    def test_interface_has_non_streaming_search_fallback(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn('contentType.includes("text/event-stream")', html)
        self.assertIn('fetch("/api/search"', html)
        self.assertIn("Adicionar personagem ou tag", html)

    def test_interface_respects_android_system_bar_safe_areas(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn("viewport-fit=cover", html)
        self.assertIn("env(safe-area-inset-top,0px)", html)
        self.assertIn("top:var(--safe-top)", html)
        self.assertIn("bottom:var(--safe-bottom)", html)

    def test_category_form_uses_source_mapping_examples(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn("vex_(league_of_legends)", html)
        self.assertIn("pixiv: ヴェックス", html)
        self.assertNotIn("shadow_the_hedgehog -rouge_the_bat", html)

    def test_lan_mode_rejects_remote_requests_without_token(self):
        async def next_handler(_request):
            return app.Response("ok")

        with patch.dict(
            app.os.environ,
            {"ARTFINDER_LAN": "1", "ARTFINDER_LAN_TOKEN": "test-secret"},
            clear=False,
        ):
            response = asyncio.run(
                app.local_security_headers(self._request(), next_handler)
            )
        self.assertEqual(response.status_code, 401)

    def test_lan_token_is_exchanged_for_httponly_cookie(self):
        async def next_handler(_request):
            return app.Response("ok")

        with patch.dict(
            app.os.environ,
            {"ARTFINDER_LAN": "1", "ARTFINDER_LAN_TOKEN": "test-secret"},
            clear=False,
        ):
            response = asyncio.run(
                app.local_security_headers(
                    self._request(path="/", query=b"access_token=test-secret"),
                    next_handler,
                )
            )
        self.assertEqual(response.status_code, 303)
        cookie = SimpleCookie()
        cookie.load(response.headers["set-cookie"])
        self.assertTrue(cookie["artfinder_lan_session"]["httponly"])
        self.assertEqual(response.headers["location"], "/")

    def test_lan_mode_keeps_loopback_available_without_token(self):
        async def next_handler(_request):
            return app.Response("ok")

        with patch.dict(
            app.os.environ,
            {"ARTFINDER_LAN": "1", "ARTFINDER_LAN_TOKEN": "test-secret"},
            clear=False,
        ):
            response = asyncio.run(
                app.local_security_headers(
                    self._request(client="127.0.0.1"),
                    next_handler,
                )
            )
        self.assertEqual(response.status_code, 200)

    def test_fresh_install_starts_without_categories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            defaults = root / "defaults.json"
            defaults.write_text('{"categories": {}}\n', encoding="utf-8")
            user_file = root / "data" / "user_categories.json"
            with (
                patch.object(app, "DEFAULT_USER_CATS_FILE", defaults),
                patch.object(app, "USER_CATS_FILE", user_file),
            ):
                self.assertEqual(app._load_user_cats(), {})
                self.assertEqual(
                    json.loads(user_file.read_text(encoding="utf-8")),
                    {"categories": {}},
                )

    def test_obsolete_bundled_categories_are_migrated_but_user_edits_are_not(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            defaults = root / "defaults.json"
            defaults.write_text('{"categories": {}}\n', encoding="utf-8")
            user_file = root / "user_categories.json"
            leaked = b'{"categories":{"legacy":{}}}'
            user_file.write_bytes(leaked)
            leaked_hash = __import__("hashlib").sha256(leaked).hexdigest()
            with (
                patch.object(app, "DEFAULT_USER_CATS_FILE", defaults),
                patch.object(app, "USER_CATS_FILE", user_file),
                patch.object(app, "_LEGACY_BUNDLED_CATEGORY_HASHES", {leaked_hash}),
                patch.object(app.sys, "frozen", True, create=True),
            ):
                self.assertEqual(app._load_user_cats(), {})
                self.assertTrue((root / "user_categories.legacy-backup.json").exists())

            edited = b'{"categories":{"mine":{"tags":"mine"}}}'
            user_file.write_bytes(edited)
            with (
                patch.object(app, "USER_CATS_FILE", user_file),
                patch.object(app, "_LEGACY_BUNDLED_CATEGORY_HASHES", {leaked_hash}),
                patch.object(app.sys, "frozen", True, create=True),
            ):
                self.assertIn("mine", app._load_user_cats())

    def test_gelbooru_is_not_enabled_without_credentials(self):
        with (
            patch.object(config, "GELBOORU_USER_ID", ""),
            patch.object(config, "GELBOORU_API_KEY", ""),
        ):
            self.assertNotIn("Gelbooru", app._get_sources())

    def test_sync_search_reports_source_failures(self):
        def broken_source(*args, **kwargs):
            raise RuntimeError("network unavailable")

        errors = []
        posts = app._run_search_sync(
            [],
            ["Broken"],
            1,
            [{"label": "test", "tags": "test_tag"}],
            {"Broken": broken_source},
            errors,
        )
        self.assertEqual(posts, [])
        self.assertEqual(errors[0]["source"], "Broken")
        self.assertIn("network unavailable", errors[0]["error"])

    def test_credential_status_never_returns_secret_values(self):
        with patch.object(config, "PIXIV_REFRESH_TOKEN", "super-secret-token"):
            response = asyncio.run(app.credential_settings())
        self.assertNotIn("super-secret-token", str(response))
        pixiv = next(group for group in response["groups"] if group["source"] == "Pixiv")
        self.assertTrue(pixiv["fields"][0]["configured"])

    def test_credential_writer_preserves_unrelated_env_values(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(app, "DATA_DIR", temp):
            env_path = Path(temp) / ".env"
            env_path.write_text("UNRELATED=keep\nPIXIV_REFRESH_TOKEN=old\n", encoding="utf-8")
            app._write_credentials({"PIXIV_REFRESH_TOKEN": "new"}, set())
            self.assertEqual(
                env_path.read_text(encoding="utf-8"),
                "UNRELATED=keep\nPIXIV_REFRESH_TOKEN=new\n",
            )

    def test_unknown_credential_field_is_rejected(self):
        response = asyncio.run(
            app.save_credential_settings({"values": {"UNSAFE_FIELD": "value"}})
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_credential_clear_list_is_rejected(self):
        response = asyncio.run(app.save_credential_settings({"clear": [{}]}))
        self.assertEqual(response.status_code, 400)

    def test_database_is_not_served_as_download(self):
        response = asyncio.run(app.downloaded_file("artfinder.db"))
        self.assertEqual(response.status_code, 403)

    def test_database_is_not_served_as_thumbnail(self):
        response = asyncio.run(app.thumb("artfinder.db"))
        self.assertEqual(response.status_code, 403)

    def test_source_prefix_parser(self):
        base, sources = app._parse_source_prefixes(
            "vex_(league_of_legends); pixiv: ヴェックス; tumblr: vex lol"
        )
        self.assertEqual(base, "vex_(league_of_legends)")
        self.assertEqual(sources["pixiv"], ["ヴェックス"])
        self.assertEqual(sources["tumblr"], ["vex lol"])

    def test_filename_components_have_no_path_syntax(self):
        self.assertEqual(_safe_component("../../bad:id"), "badid")


if __name__ == "__main__":
    unittest.main()
