import asyncio
import socket
import unittest
from unittest.mock import patch

import app
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
