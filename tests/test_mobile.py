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
