import asyncio
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import config
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
    def test_interface_loads_shared_language_runtime(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn('id="languageSelect"', html)
        self.assertIn('src="/ui/i18n.js"', html)

        script = asyncio.run(app.i18n_script())
        self.assertEqual(Path(script.path).name, "i18n.js")

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
