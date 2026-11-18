"""Native UI integration against the real local API, with isolated data/sources.

Run with requirements-dev.txt installed. No real credentials or external sources
are used. Set ARTFINDER_NATIVE_SCREENSHOTS to a directory to retain UI captures.
"""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

HAS_QT = importlib.util.find_spec("PySide6") is not None
if HAS_QT:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from artfinder.native.client import EventDecoder
    from artfinder.native.models import canonical, filter_posts, uid
    from artfinder.native.window import NativeWindow, STYLE
    from artfinder.native.dialogs import CategoryDialog, SearchDialog, FiltersDialog, SettingsDialog
    from artfinder.native.widgets import Viewer


@unittest.skipUnless(HAS_QT, "Native Qt dependencies are not installed")
class NativeModelTests(unittest.TestCase):
    def test_sse_split_unicode_crlf_and_multiple_events(self):
        events = []
        decoder = EventDecoder(lambda event, payload: events.append((event, payload)))
        raw = ('event: posts\r\ndata: {"artist":"Ilustração"}\r\n\r\n'
               ': heartbeat\r\n\r\nevent: done\ndata: {"total":1}\n\n').encode()
        for byte in raw:
            decoder.feed(bytes([byte]))
        self.assertEqual(events, [("posts", {"artist": "Ilustração"}), ("done", {"total": 1})])

    def test_filters_use_real_dates_aliases_and_persistent_identities(self):
        posts = [canonical({"uid": "bsky:12", "source": "bsky", "rating": "q", "orig_url": "https://example.test/a.WEBM?x=1", "score": 8}),
                 canonical({"source": "pixiv", "post_id": "99", "score": 3, "post_date": 1})]
        self.assertEqual(posts[0]["id"], "12")
        self.assertEqual(uid(posts[1]), "pixiv:99")
        self.assertEqual(filter_posts(posts, {"source": "bluesky", "days": 7}), [posts[0]])
        self.assertEqual(filter_posts(posts, {"ratings": ["sfw"]}), [posts[1]])
        self.assertEqual(filter_posts(posts, {"media": ["video"]}), [posts[0]])
        self.assertEqual(filter_posts(posts, {"hide_saved": True}, saved={"bsky:12"}), [posts[1]])
        self.assertEqual(len(posts), 2)


@unittest.skipUnless(HAS_QT, "Native Qt dependencies are not installed")
class NativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image, ImageDraw
        import app
        import desktop
        from utils import database
        cls.qt = QApplication.instance() or QApplication([])
        if os.name == "nt":
            QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"))
        cls.qt.setStyle("Fusion")
        cls.qt.setStyleSheet(STYLE)
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.downloads = cls.root / "downloads"
        cls.downloads.mkdir()
        cls.media = {}
        colors = [(64, 90, 123), (110, 77, 105), (63, 111, 106), (124, 101, 67), (76, 74, 124), (95, 108, 80)]
        for index, color in enumerate(colors):
            image = Image.new("RGB", (420, 520), color)
            draw = ImageDraw.Draw(image)
            draw.ellipse((80, 85, 335, 340), fill=tuple(min(255, c + 55) for c in color))
            draw.polygon([(0, 520), (210, 220), (420, 520)], fill=tuple(max(0, c - 25) for c in color))
            stream = io.BytesIO()
            image.save(stream, format="PNG")
            cls.media[str(index)] = stream.getvalue()
        cls.fetches = []
        def fetch_image(url, **_):
            cls.fetches.append(url)
            return cls.media[url.rsplit("/", 1)[-1].split(".")[0]], "image/png"
        cls.slow = False
        def source(*_, **__):
            if cls.slow:
                time.sleep(0.4)
            return [{"id": str(i), "url": f"https://example.test/{i}.png", "preview_url": f"https://example.test/{i}.png", "artist": f"Estudo de formas {i + 1}",
                     "score": 20 - i, "width": 420, "height": 520, "rating": "nsfw" if i == 5 else "sfw", "tags": "landscape", "page_url": f"https://example.test/art/{i}"} for i in range(6)]
        cls.schema = database._schema_ready
        cls.patches = [patch.object(database, "DB_PATH", cls.root / "test.db"), patch.object(app, "USER_CATS_FILE", cls.root / "categories.json"),
                       patch.object(app, "DOWNLOAD_DIR", str(cls.downloads)), patch.object(app, "_get_sources", lambda: {"Danbooru": source}),
                       patch.object(app, "_fetch_image_sync", fetch_image)]
        for item in cls.patches:
            item.start()
        database._schema_ready = False
        (cls.root / "categories.json").write_text(json.dumps({"categories": {"landscape": {"label": "Paisagens", "tags": "landscape", "group": "Referências"}}}), encoding="utf-8")
        cls.server, cls.listener, cls.url = desktop._create_server()
        cls.thread = threading.Thread(target=lambda: cls.server.run(sockets=[cls.listener]), daemon=True)
        cls.thread.start()
        deadline = time.time() + 5
        while not cls.server.started and time.time() < deadline:
            time.sleep(0.01)
        if not cls.server.started:
            raise RuntimeError("Native test service did not start")

    @classmethod
    def tearDownClass(cls):
        from utils import database
        cls.server.should_exit = True
        cls.thread.join(5)
        cls.listener.close()
        for item in reversed(cls.patches):
            item.stop()
        database._schema_ready = cls.schema
        database._invalidate_phash_cache()
        cls.temp.cleanup()

    def wait(self, condition, timeout=8000):
        deadline = time.monotonic() + timeout / 1000
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(20)
            # Let the in-process API thread acquire the GIL between Qt event pumps.
            time.sleep(0.001)
        self.assertTrue(condition(), "Native UI did not reach the expected state")

    def capture(self, widget, name):
        output = os.getenv("ARTFINDER_NATIVE_SCREENSHOTS")
        if output:
            path = Path(output)
            path.mkdir(parents=True, exist_ok=True)
            QTest.qWait(80)
            self.assertTrue(widget.grab().save(str(path / name)))

    def test_native_search_library_dialogs_viewer_and_cancellation(self):
        window = NativeWindow(self.url, self.root, self.downloads, Path(__file__).resolve().parents[1])
        errors = []
        window.error = errors.append
        window.api.failed.disconnect()
        window.api.failed.connect(errors.append)
        window.show()
        try:
            self.wait(lambda: window.new_search.isEnabled() and bool(window.categories))
            self.capture(window, "native-home.png")
            window.resize(1000, 680)
            self.capture(window, "native-home-compact.png")
            window.resize(1440, 900)
            search = SearchDialog(window)
            search.show()
            self.assertEqual(search.categories.count(), 1)
            search.categories.item(0).setCheckState(Qt.CheckState.Checked)
            self.capture(search, "native-search.png")
            search.submit()
            self.assertEqual(search.result(), search.DialogCode.Accepted)
            window.search_options = search.values()
            window.start_search()
            self.wait(lambda: window.search_reply is None)
            self.assertEqual(len(window.search_posts), 6)
            self.wait(lambda: window.thumbnails.active == 0)
            self.assertFalse(any("/5.png" in url for url in self.fetches))
            self.assertFalse(window.inspector.isVisible())
            self.assertGreaterEqual(window.grid.gridSize().width(), 375)
            self.capture(window, "native-results.png")
            window.grid.setCurrentIndex(window.model.index(0, 0))
            self.assertTrue(window.download_button.isEnabled())
            self.assertEqual(window.inspector.post, window.model.posts[0])
            self.assertEqual(window.inspector.values["size"].text(), "420 × 520")
            QTest.mouseClick(window.inspector_toggle, Qt.MouseButton.LeftButton)
            self.assertTrue(window.inspector.isVisible())
            QTest.mouseClick(window.inspector_toggle, Qt.MouseButton.LeftButton)
            self.assertFalse(window.inspector.isVisible())
            QTest.mouseClick(window.inspector_toggle, Qt.MouseButton.LeftButton)
            self.assertTrue(window.inspector.isVisible())
            window.thumbnail_size.setValue(180)
            self.assertEqual(window.preferences.value("artwork_width", type=int), 180)
            window.thumbnail_size.setValue(410)
            window.resize(1000, 680)
            self.capture(window, "native-results-compact.png")
            self.assertLessEqual(window.minimumSizeHint().width(), 1000)
            window.resize(1440, 900)
            self.capture(window, "native-selection.png")
            window.grid.setCurrentIndex(window.model.index(5, 0))
            self.assertIn("NSFW", window.inspector.preview.text())
            self.assertFalse(any("/5.png" in url for url in self.fetches))
            window.grid.clearSelection()
            window.source_filter.setCurrentIndex(window.source_filter.findData("danbooru"))
            self.assertEqual(window.model.rowCount(), 6)
            window.query.setText("formas 2")
            self.assertEqual(window.model.rowCount(), 1)
            window.query.setText("no-such-artwork")
            self.assertEqual(window.model.rowCount(), 0)
            QTest.mouseClick(window.reset_button, Qt.MouseButton.LeftButton)
            self.assertEqual(window.model.rowCount(), 6)
            window.hide_saved.setChecked(True)
            post = window.search_posts[0]
            window.save(post)
            self.wait(lambda: uid(post) in window.saved)
            self.assertEqual(window.model.rowCount(), 5)
            window.switch_section("gallery")
            self.wait(lambda: window.model.rowCount() == 1)
            self.capture(window, "native-gallery.png")
            window.api.request("/api/collections", lambda _: window.refresh_library(), method="POST", data={"name": "Referências"})
            self.wait(lambda: len(window.collections) == 1 or bool(errors))
            self.assertEqual(errors, [])
            self.assertEqual(window.collection_filter.itemText(1), "Referências")
            window.collection_filter.setCurrentIndex(1)
            self.assertEqual(window.model.rowCount(), 0)
            window.collection_filter.setCurrentIndex(0)
            self.assertEqual(window.model.rowCount(), 1)
            viewer = Viewer(window, window.search_posts, 5)
            viewer.show()
            self.assertTrue(viewer.reveal.isVisible())
            self.assertIsNone(viewer.reply)
            viewer.show_protected()
            self.wait(lambda: viewer.image.item is not None)
            self.assertIn(uid(viewer.current), window.revealed)
            viewer.hide_protected()
            self.assertTrue(viewer.reveal.isVisible())
            viewer.step(1)
            self.wait(lambda: viewer.stack.currentWidget() == viewer.image)
            self.capture(viewer, "native-viewer.png")
            viewer.reject()
            editor = CategoryDialog(window)
            editor.show()
            editor.name.setText("Estudos de luz")
            editor.tags.setPlainText("lighting")
            editor.overrides["pixiv"].setText("光")
            editor.save()
            self.wait(lambda: "estudos_de_luz" in window.categories)
            self.assertEqual(window.categories["estudos_de_luz"]["source_tags"]["pixiv"], ["光"])
            self.capture(editor, "native-categories.png")
            editor.reject()
            filters = FiltersDialog(window)
            filters.show()
            self.assertEqual(set(filters.groups), {"ratings", "media"})
            image_filter = filters.groups["media"][0][1]
            QTest.mouseClick(image_filter, Qt.MouseButton.LeftButton)
            self.assertNotIn("image", filters.values()["media"])
            QTest.mouseClick(image_filter, Qt.MouseButton.LeftButton)
            self.capture(filters, "native-filters.png")
            filters.reject()
            settings = SettingsDialog(window)
            settings.show()
            self.wait(lambda: settings.save_button.isEnabled())
            self.capture(settings, "native-settings.png")
            from PySide6.QtCore import QSettings
            from PySide6.QtGui import QPalette
            from artfinder.native.themes import THEMES
            self.assertEqual(window.theme, "night")
            for key in ["graphite", "forest", "light", "night"]:
                theme = THEMES[key]
                QTest.mouseClick(settings.theme_cards[key], Qt.MouseButton.LeftButton)
                self.assertEqual(window.theme, key)
                self.assertEqual(self.qt.palette().color(QPalette.ColorRole.Window).name(), theme["bg"])
                saved_preferences = QSettings(str(self.root / "native-ui.ini"), QSettings.Format.IniFormat)
                self.assertEqual(saved_preferences.value("theme"), key)
                self.capture(window, f"native-theme-{key}.png")
            settings.theme_selector.setCurrentIndex(settings.theme_selector.findData("night"))
            reopened = NativeWindow(self.url, self.root, self.downloads, Path(__file__).resolve().parents[1])
            self.assertEqual(reopened.theme, "night")
            self.wait(lambda: reopened.new_search.isEnabled())
            reopened.close()
            settings.reject()
            settings.language.setCurrentIndex(settings.language.findData("en"))
            self.assertEqual(window.nav["gallery"].text(), "My gallery")
            self.assertEqual(window.new_search.text(), "Advanced search")
            settings.language.setCurrentIndex(settings.language.findData("pt-BR"))
            self.assertEqual(window.nav["gallery"].text(), "Minha galeria")
            self.slow = True
            type(self).slow = True
            window.quick_search.setText("landscape")
            window.search_tags()
            self.assertEqual(window.search_options["tags"], "landscape")
            QTest.qWait(50)
            window.cancel_search()
            self.wait(lambda: window.search_reply is None)
            self.assertTrue(window.new_search.isEnabled())
            type(self).slow = False
            self.assertEqual(errors, [])
        finally:
            window.search_generation += 1
            window.cancel_search()
            window.close()
            self.qt.processEvents()

    @unittest.skipUnless(os.getenv("ARTFINDER_TEST_VIDEO"), "Set ARTFINDER_TEST_VIDEO to a local synthetic video fixture")
    def test_native_video_and_animated_gif(self):
        from PIL import Image
        from PySide6.QtMultimedia import QMediaPlayer
        window = NativeWindow(self.url, self.root, self.downloads, Path(__file__).resolve().parents[1])
        self.wait(lambda: window.new_search.isEnabled())
        viewer = Viewer(window, [{"source": "test", "id": "protected", "rating": "nsfw"}], 0)
        viewer.show()
        try:
            viewer.cleanup()
            viewer.load_video(Path(os.environ["ARTFINDER_TEST_VIDEO"]).read_bytes())
            self.wait(lambda: viewer.player.duration() > 0)
            self.assertEqual(viewer.player.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
            viewer.toggle_video()
            self.wait(lambda: viewer.player.position() > 200)
            self.assertEqual(viewer.player.error(), QMediaPlayer.Error.NoError)
            self.capture(viewer, "native-video.png")
            viewer.cleanup()
            stream = io.BytesIO()
            Image.new("RGB", (100, 100), "navy").save(stream, format="GIF", save_all=True, append_images=[Image.new("RGB", (100, 100), "purple")], duration=100, loop=0)
            viewer.load_image(stream.getvalue())
            self.wait(lambda: viewer.movie.currentFrameNumber() == 1)
            self.assertFalse(viewer.image.item.pixmap().isNull())
        finally:
            viewer.reject()
            window.close()
            self.qt.processEvents()
