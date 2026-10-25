import asyncio
import unittest
from unittest.mock import MagicMock, patch

from fastapi import Request

import app
from utils.media import video_byte_range


class VideoPlaybackTests(unittest.TestCase):
    def test_ranges_support_initial_load_seeking_and_suffix(self):
        for value, expected in [("bytes=0-", (0, 9)), ("bytes=4-6", (4, 6)),
                                ("bytes=-3", (7, 9)), ("bytes=8-99", (8, 9))]:
            self.assertEqual(video_byte_range(value, 10), expected)
        for value in ["bytes=10-", "bytes=5-2", "bytes=-0", "bytes=-", "bytes=0-1,3-4", "items=0-1"]:
            with self.assertRaises(ValueError):
                video_byte_range(value, 10)

    def test_response_exposes_partial_content_and_unsatisfiable_size(self):
        response = app._video_response(b"0123456789", "video/mp4", "bytes=4-6")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.body, b"456")
        self.assertEqual(response.headers["content-range"], "bytes 4-6/10")
        invalid = app._video_response(b"0123456789", "video/mp4", "bytes=10-")
        self.assertEqual(invalid.status_code, 416)
        self.assertEqual(invalid.headers["content-range"], "bytes */10")

    def test_video_transport_uses_safe_referer_and_size_limit(self):
        response = MagicMock(status_code=200)
        response.__enter__.return_value = response
        response.headers = {"content-type": "video/mp4", "content-length": "4"}
        response.iter_content.return_value = [b"test"]
        url = "https://static1.e621.net/data/test-video.mp4?test=1"
        with patch.object(app, "_proxy_cache", {}), \
             patch("utils.network.validate_remote_url", return_value=app.urlsplit(url)), \
             patch.object(app, "public_image_get", return_value=response) as get:
            result = app._fetch_image_sync(url, True)
        self.assertEqual(result, (b"test", "video/mp4"))
        self.assertEqual(get.call_args.kwargs["headers"]["Referer"], "https://e621.net/")
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertTrue(get.call_args.kwargs["stream"])

    def test_proxy_errors_do_not_echo_signed_url(self):
        request = Request({"type": "http", "headers": []})
        with patch.object(app, "_fetch_image_sync", side_effect=RuntimeError("secret-url-token")):
            response = asyncio.run(app.proxy_video(request, "https://example.com/file.mp4"))
        self.assertEqual(response.status_code, 502)
        self.assertNotIn(b"secret-url-token", response.body)

    def test_image_endpoint_cannot_serve_video_from_shared_cache(self):
        with patch.object(app, "_proxy_cache", {"video": (b"data", "video/mp4")}):
            with self.assertRaises(ValueError):
                app._fetch_image_sync("video")
