import unittest
from pathlib import Path


class AndroidPackagingTests(unittest.TestCase):
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

    def test_android_results_prioritize_artwork_and_support_swipe_viewing(self):
        ui_root = (
            self.project / "android-native" / "app" / "src" / "main" / "java"
            / "io" / "github" / "gabizips" / "artfinder" / "ui"
        )
        search = (ui_root / "screen" / "SearchScreen.kt").read_text(encoding="utf-8")
        gallery = (ui_root / "screen" / "GalleryScreen.kt").read_text(encoding="utf-8")
        viewer = (ui_root / "component" / "ZoomableImageViewer.kt").read_text(encoding="utf-8")

        self.assertIn("controlsExpanded = false", search)
        self.assertIn("CompactSearchBar", search)
        self.assertIn("HorizontalPager", viewer)
        self.assertIn("userScrollEnabled = images.size > 1", viewer)
        self.assertIn("images = viewerImages", search)
        self.assertIn("images = viewerImages", gallery)

    def test_android_has_a_shared_branded_visual_system(self):
        android = self.project / "android-native"
        ui_root = (
            android / "app" / "src" / "main" / "java"
            / "io" / "github" / "gabizips" / "artfinder" / "ui"
        )
        design = (ui_root / "component" / "ArtFinderDesign.kt").read_text(encoding="utf-8")
        typography = (ui_root / "theme" / "Type.kt").read_text(encoding="utf-8")

        for component in (
            "ArtFinderBackdrop",
            "ArtFinderPanel",
            "ArtFinderPrimaryButton",
            "ArtFinderSecondaryButton",
            "ArtFinderPill",
        ):
            self.assertIn(f"fun {component}", design)

        self.assertIn("R.font.manrope_variable", typography)
        build = (android / "app" / "build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn('assets.directories.add("../licenses")', build)
        self.assertTrue((android / "app" / "src" / "main" / "res" / "font" / "manrope_variable.ttf").is_file())
        self.assertTrue((android / "licenses" / "MANROPE-OFL.txt").is_file())

        for screen in ("SearchScreen.kt", "TagsScreen.kt", "GalleryScreen.kt", "SettingsScreen.kt"):
            source = (ui_root / "screen" / screen).read_text(encoding="utf-8")
            self.assertIn("ArtFinderBackdrop", source)
