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
    @property
    def project(self):
        return Path(__file__).parents[1]

    def test_android_is_native_compose_without_embedded_python(self):
        build = (self.project / "android-native" / "app" / "build.gradle.kts").read_text(
            encoding="utf-8"
        )
        workflow = (self.project / ".github" / "workflows" / "build-android.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('id("org.jetbrains.kotlin.plugin.compose")', build)
        self.assertIn('implementation("androidx.compose.material3:material3")', build)
        self.assertIn("android-native", workflow)
        self.assertNotIn("buildozer", workflow.lower())
        self.assertNotIn("python-for-android", workflow.lower())

    def test_android_supports_api_29_through_36_without_broad_storage(self):
        build = (self.project / "android-native" / "app" / "build.gradle.kts").read_text(
            encoding="utf-8"
        )
        manifest = (
            self.project / "android-native" / "app" / "src" / "main" / "AndroidManifest.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("compileSdk = 36", build)
        self.assertIn("minSdk = 29", build)
        self.assertIn("targetSdk = 36", build)
        self.assertNotIn("READ_EXTERNAL_STORAGE", manifest)
        self.assertNotIn("WRITE_EXTERNAL_STORAGE", manifest)
        self.assertNotIn("MANAGE_EXTERNAL_STORAGE", manifest)
        self.assertIn('android:allowBackup="false"', manifest)

    def test_android_uses_pairing_code_only_and_mediastore(self):
        build = (self.project / "android-native" / "app" / "build.gradle.kts").read_text(
            encoding="utf-8"
        )
        scanner = (
            self.project / "android-native" / "app" / "src" / "main" / "java"
            / "io" / "github" / "gabizips" / "artfinder" / "ui" / "screen" / "QrScanner.kt"
        )
        manifest = (self.project / "android-native" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(
            encoding="utf-8"
        )
        gallery = (
            self.project / "android-native" / "app" / "src" / "main" / "java"
            / "io" / "github" / "gabizips" / "artfinder" / "data" / "GalleryRepository.kt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("com.google.mlkit:barcode-scanning", build)
        self.assertNotIn("androidx.camera", build)
        self.assertFalse(scanner.exists())
        self.assertNotIn("android.permission.CAMERA", manifest)
        self.assertIn("MediaStore.Images.Media.RELATIVE_PATH", gallery)
        self.assertIn('Environment.DIRECTORY_PICTURES + "/ArtFinder"', gallery)

    def test_android_workflow_requires_stable_signing_certificate(self):
        workflow = (self.project / ".github" / "workflows" / "build-android.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("ARTFINDER_ANDROID_KEYSTORE_BASE64", workflow)
        self.assertIn("ARTFINDER_ANDROID_KEYSTORE_PASSWORD", workflow)
        self.assertIn("apksigner verify --verbose --print-certs", workflow)
        self.assertIn(
            "e8d6011c9c44b130be635ec8973184d39681d711b7b5aee1ab15e7354b408567",
            workflow,
        )

    def test_windows_package_check_matches_code_only_pairing(self):
        workflow = (self.project / ".github" / "workflows" / "build-windows.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("utils[\\\\.]pairing", workflow)
        self.assertIn("cryptography", workflow)
        self.assertNotIn("qrcode", workflow.lower())

    def test_tagged_release_publishes_the_android_apk(self):
        workflow = (self.project / ".github" / "workflows" / "release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("uses: ./.github/workflows/build-android.yml", workflow)
        self.assertIn("secrets: inherit", workflow)
        self.assertIn("ArtFinder-Android-native", workflow)
        self.assertIn("ArtFinder-Android-10-16.apk", workflow)
