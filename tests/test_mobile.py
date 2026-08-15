import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mobile import (
    MOBILE_LOG_NAME,
    MOBILE_PORT,
    _startup_error_html,
    main,
    prepare_mobile_environment,
)


class MobileBootstrapTests(unittest.TestCase):
    def test_mobile_server_uses_webview_port(self):
        self.assertEqual(MOBILE_PORT, 5000)

    def test_mobile_data_is_written_below_app_home(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {}, clear=True):
                data_dir = prepare_mobile_environment(temp)
                self.assertEqual(data_dir, Path(temp).resolve() / "artfinder")
                self.assertEqual(os.environ["ARTFINDER_MOBILE"], "1")

    def test_android_private_directory_takes_priority_over_home(self):
        with tempfile.TemporaryDirectory() as private, tempfile.TemporaryDirectory() as home:
            with patch.dict(
                os.environ,
                {"ANDROID_PRIVATE": private, "HOME": home},
                clear=True,
            ):
                data_dir = prepare_mobile_environment()
                self.assertEqual(data_dir, Path(private).resolve() / "artfinder")

    def test_startup_failure_is_logged_and_shown_instead_of_closing(self):
        with tempfile.TemporaryDirectory() as temp:
            captured = []

            def broken_loader():
                raise RuntimeError("missing android dependency")

            def capture_error(exc, log_path):
                captured.append((exc, log_path))

            with patch.dict(os.environ, {"ANDROID_PRIVATE": temp}, clear=True), patch(
                "mobile.sys.stderr", io.StringIO()
            ):
                main(
                    app_loader=broken_loader,
                    server_runner=lambda *_args, **_kwargs: None,
                    error_server=capture_error,
                )

            self.assertEqual(len(captured), 1)
            self.assertIsInstance(captured[0][0], RuntimeError)
            log_path = Path(temp).resolve() / "artfinder" / MOBILE_LOG_NAME
            actual_log = captured[0][1]
            self.assertEqual(actual_log, log_path)
            self.assertTrue(actual_log.exists())
            self.assertIn("missing android dependency", actual_log.read_text(encoding="utf-8"))

    def test_startup_error_page_exposes_private_log_safely(self):
        log_path = Path("/private/android/artfinder") / MOBILE_LOG_NAME
        page = _startup_error_html(
            ModuleNotFoundError("No module named urllib3"),
            log_path,
            "Traceback: No module named urllib3",
        )
        self.assertIn(f'href="/{MOBILE_LOG_NAME}"', page)
        self.assertIn("No module named urllib3", page)
        self.assertNotIn("/private/android/artfinder", page)
        self.assertIn("viewport-fit=cover", page)
        self.assertIn("safe-area-inset-top", page)


class MobilePackagingTests(unittest.TestCase):
    def test_android_packages_empty_category_defaults(self):
        spec = (Path(__file__).parents[1] / "buildozer.spec").read_text(encoding="utf-8")
        self.assertIn("defaults/*", spec)
        self.assertNotIn("user_categories.json", spec)

    def test_android_python_matches_pinned_aiohttp_recipe(self):
        spec = (Path(__file__).parents[1] / "buildozer.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn("python3==3.11.9", spec)
        self.assertIn("hostpython3==3.11.9", spec)
        self.assertIn("aiohttp==3.8.3", spec)
        self.assertIn("urllib3==2.7.0", spec)
        self.assertIn("certifi==2026.7.22", spec)
        self.assertIn("oauthlib==3.3.1", spec)
        self.assertIn("pyjnius", spec)
        self.assertIn("android.ndk = 28c", spec)
        self.assertIn("p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831", spec)

    def test_android_disables_backup_and_uses_explicit_webview_port(self):
        spec = (Path(__file__).parents[1] / "buildozer.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn("android.allow_backup = False", spec)
        self.assertIn("p4a.port = 5000", spec)

    def test_android_supports_api_29_through_36_without_broad_storage(self):
        spec = (Path(__file__).parents[1] / "buildozer.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn("android.api = 36", spec)
        self.assertIn("android.minapi = 29", spec)
        self.assertIn("android.ndk_api = 29", spec)
        self.assertNotIn("READ_EXTERNAL_STORAGE", spec)
        self.assertNotIn("WRITE_EXTERNAL_STORAGE", spec)
        self.assertNotIn("MANAGE_EXTERNAL_STORAGE", spec)

        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "build-android.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('android:minSdkVersion="29"', workflow)
        self.assertIn('android:targetSdkVersion="36"', workflow)
        self.assertIn('android:usesCleartextTraffic="true"', workflow)

    def test_android_workflow_verifies_freetype_fallback(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "build-android.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("sourceforge.net/projects/freetype", workflow)
        self.assertIn(
            "174d9e53402e1bf9ec7277e22ec199ba3e55a6be2c0740cb18c0ee9850fc8c34",
            workflow,
        )

    def test_android_workflow_recreates_disposable_p4a_venv(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "build-android.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "rm -rf .buildozer/android/platform/build-arm64-v8a/build/venv",
            workflow,
        )

    def test_android_workflow_requires_stable_signing_certificate(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "build-android.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("ARTFINDER_ANDROID_KEYSTORE_BASE64", workflow)
        self.assertIn("ARTFINDER_ANDROID_KEYSTORE_PASSWORD", workflow)
        self.assertIn("apksigner verify --verbose --print-certs", workflow)
        self.assertIn(
            "e8d6011c9c44b130be635ec8973184d39681d711b7b5aee1ab15e7354b408567",
            workflow,
        )

    def test_tagged_release_publishes_the_android_apk(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "release.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("uses: ./.github/workflows/build-android.yml", workflow)
        self.assertIn("secrets: inherit", workflow)
        self.assertIn("ArtFinder-Android-10-16.apk", workflow)
