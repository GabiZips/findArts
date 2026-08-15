import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import desktop
from desktop import _migrate_env_if_needed
from utils.platform import user_data_dir, window_icon


class DesktopBootstrapTests(unittest.TestCase):
    def test_packaging_uses_empty_defaults_not_personal_categories(self):
        project = Path(__file__).resolve().parents[1]
        spec = (project / "artfinder.spec").read_text(encoding="utf-8")
        defaults = (project / "defaults" / "categories.json").read_text(encoding="utf-8")
        self.assertIn('("defaults/categories.json", "defaults")', spec)
        self.assertNotIn('("user_categories.json", ".")', spec)
        self.assertEqual(__import__("json").loads(defaults), {"categories": {}})

    def test_windows_workflow_smoke_tests_packaged_pairing(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "build-windows.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("ARTFINDER_SMOKE_TEST", workflow)
        self.assertIn("ARTFINDER_DATA_DIR", workflow)

    def test_windows_window_icon_is_an_ico_resource(self):
        with patch("utils.platform.sys.platform", "win32"):
            self.assertEqual(window_icon("root").suffix, ".ico")

    def test_linux_window_icon_is_a_png_resource(self):
        with patch("utils.platform.sys.platform", "linux"):
            self.assertEqual(window_icon("root").suffix, ".png")

    def test_linux_uses_xdg_data_home(self):
        with (
            patch("utils.platform.sys.platform", "linux"),
            patch.dict("utils.platform.os.environ", {"XDG_DATA_HOME": "/tmp/xdg"}, clear=True),
        ):
            self.assertEqual(user_data_dir(), Path("/tmp/xdg/artfinder"))

    def test_migrates_project_env_on_first_desktop_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable_dir = root / "project" / "dist"
            data_dir = root / "local" / "ArtFinder"
            executable_dir.mkdir(parents=True)
            legacy = executable_dir.parent / ".env"
            legacy.write_text("PIXIV_REFRESH_TOKEN=test-token\n", encoding="utf-8")

            migrated_from = _migrate_env_if_needed(data_dir, executable_dir)

            self.assertEqual(migrated_from, legacy)
            self.assertEqual(
                (data_dir / ".env").read_text(encoding="utf-8"),
                "PIXIV_REFRESH_TOKEN=test-token\n",
            )

    def test_does_not_overwrite_existing_desktop_env(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable_dir = root / "project" / "dist"
            data_dir = root / "local" / "ArtFinder"
            executable_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)
            (executable_dir.parent / ".env").write_text(
                "PIXIV_REFRESH_TOKEN=legacy\n",
                encoding="utf-8",
            )
            target = data_dir / ".env"
            target.write_text("PIXIV_REFRESH_TOKEN=current\n", encoding="utf-8")

            migrated_from = _migrate_env_if_needed(data_dir, executable_dir)

            self.assertIsNone(migrated_from)
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "PIXIV_REFRESH_TOKEN=current\n",
            )
