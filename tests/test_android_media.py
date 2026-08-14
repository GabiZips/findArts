import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import android_media


class _Values(dict):
    def put(self, key, value):
        self[key] = value


class _Columns:
    DISPLAY_NAME = "display_name"
    MIME_TYPE = "mime_type"
    RELATIVE_PATH = "relative_path"
    IS_PENDING = "is_pending"


class _Uri:
    def __init__(self, value):
        self.value = value

    def toString(self):
        return self.value


class _UriClass:
    @staticmethod
    def parse(value):
        return _Uri(value)


class _ImagesMedia:
    @staticmethod
    def getContentUri(volume):
        return f"content://images/{volume}"


class _MediaStore:
    VOLUME_EXTERNAL_PRIMARY = "external_primary"


class _Output:
    def __init__(self, *, fail=False):
        self.data = bytearray()
        self.fail = fail
        self.closed = False

    def write(self, payload, **_kwargs):
        if self.fail:
            raise OSError("write failed")
        self.data.extend(payload)

    def flush(self):
        pass

    def close(self):
        self.closed = True


class _Resolver:
    def __init__(self, *, fail_write=False):
        self.output = _Output(fail=fail_write)
        self.insert_values = None
        self.updates = []
        self.deleted = []

    def insert(self, _collection, values):
        self.insert_values = dict(values)
        return _Uri("content://media/external/images/media/42")

    def openOutputStream(self, _uri):
        return self.output

    def update(self, uri, values, _where, _args):
        self.updates.append((uri.toString(), dict(values)))
        return 1

    def delete(self, uri, _where, _args):
        self.deleted.append(uri.toString())
        return 1


def _runtime(resolver):
    return android_media._AndroidRuntime(
        resolver=resolver,
        content_values=_Values,
        media_columns=_Columns,
        images_media=_ImagesMedia,
        media_store=_MediaStore,
        uri=_UriClass,
        integer=int,
    )


class AndroidMediaStoreTests(unittest.TestCase):
    def test_publish_copies_and_releases_pending_row(self):
        resolver = _Resolver()
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "art.png"
            image.write_bytes(b"image-data")
            with patch.object(android_media, "_android_runtime", return_value=_runtime(resolver)):
                uri = android_media.publish_image(image)

        self.assertEqual(uri, "content://media/external/images/media/42")
        self.assertEqual(resolver.output.data, b"image-data")
        self.assertEqual(resolver.insert_values["relative_path"], "Pictures/ArtFinder")
        self.assertEqual(resolver.insert_values["is_pending"], 1)
        self.assertEqual(resolver.updates[0][1]["is_pending"], 0)
        self.assertEqual(resolver.deleted, [])

    def test_failed_publish_removes_pending_row(self):
        resolver = _Resolver(fail_write=True)
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "art.jpg"
            image.write_bytes(b"broken")
            with patch.object(android_media, "_android_runtime", return_value=_runtime(resolver)):
                with self.assertRaises(android_media.AndroidMediaError):
                    android_media.publish_image(image)
        self.assertEqual(
            resolver.deleted,
            ["content://media/external/images/media/42"],
        )

    def test_delete_uses_recorded_content_uri(self):
        resolver = _Resolver()
        with patch.object(android_media, "_android_runtime", return_value=_runtime(resolver)):
            removed = android_media.delete_image("content://media/external/images/media/7")
        self.assertTrue(removed)
        self.assertEqual(resolver.deleted, ["content://media/external/images/media/7"])

    def test_desktop_process_does_not_load_android_bridge(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(android_media.android_media_available())
            with self.assertRaises(android_media.AndroidMediaError):
                android_media._android_runtime()


if __name__ == "__main__":
    unittest.main()
