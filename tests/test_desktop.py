import tempfile
import unittest
from pathlib import Path

import desktop
from desktop import _migrate_env_if_needed


class DesktopBootstrapTests(unittest.TestCase):
    def test_windows_window_icon_is_an_ico_resource(self):
        source = Path(desktop.__file__).read_text(encoding="utf-8")
        self.assertIn('"assets" / "artfinder.ico"', source)

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
