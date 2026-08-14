import unittest
from unittest.mock import Mock, patch

import requests

from sources import danbooru, gelbooru
from sources.errors import SourceUnavailableError, public_source_error


class SourceErrorTests(unittest.TestCase):
    def test_connection_error_is_safe_and_actionable(self):
        raw = requests.ConnectionError(
            "failed https://example.test/api?api_key=super-secret"
        )
        message = public_source_error("Example", raw)
        self.assertIn("DNS", message)
        self.assertNotIn("super-secret", message)
        self.assertNotIn("example.test", message)

    def test_http_status_is_reported_without_request_url(self):
        response = Mock(status_code=403)
        raw = requests.HTTPError(
            "403 for https://example.test/?token=super-secret",
            response=response,
        )
        message = public_source_error("Example", raw)
        self.assertIn("HTTP 403", message)
        self.assertNotIn("super-secret", message)

    def test_danbooru_propagates_network_failure_to_search_ui(self):
        raw = requests.ConnectionError("blocked by campus network")
        with patch.object(danbooru.requests, "get", side_effect=raw):
            with self.assertRaises(SourceUnavailableError) as raised:
                danbooru.fetch_posts("test", max_pages=1, tags="test")
        self.assertIn("Danbooru", str(raised.exception))
        self.assertIn("bloqueio da rede", str(raised.exception))

    def test_connector_log_does_not_echo_api_key_from_request_error(self):
        raw = requests.ConnectionError(
            "failed https://gelbooru.example/?api_key=super-secret"
        )
        with (
            patch.object(gelbooru, "GELBOORU_API_KEY", "super-secret"),
            patch.object(gelbooru, "GELBOORU_USER_ID", "123"),
            patch.object(gelbooru.requests, "get", side_effect=raw),
            patch("builtins.print") as output,
        ):
            with self.assertRaises(SourceUnavailableError):
                gelbooru.fetch_posts("test", max_pages=1, tags="test")
        logged = " ".join(str(call) for call in output.call_args_list)
        self.assertNotIn("super-secret", logged)


if __name__ == "__main__":
    unittest.main()
