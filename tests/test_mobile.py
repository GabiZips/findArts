import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mobile import MOBILE_PORT, prepare_mobile_environment


class MobileBootstrapTests(unittest.TestCase):
    def test_mobile_server_uses_webview_port(self):
        self.assertEqual(MOBILE_PORT, 5000)

    def test_mobile_data_is_written_below_app_home(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {}, clear=True):
                data_dir = prepare_mobile_environment(temp)
                self.assertEqual(data_dir, Path(temp).resolve() / "artfinder")
                self.assertEqual(os.environ["ARTFINDER_MOBILE"], "1")


class MobilePackagingTests(unittest.TestCase):
    def test_android_python_matches_pinned_aiohttp_recipe(self):
        spec = (Path(__file__).parents[1] / "buildozer.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn("python3==3.11.9", spec)
        self.assertIn("aiohttp==3.8.3", spec)
