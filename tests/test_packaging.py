import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.inspect_android_apk import inspect_apk


def _apk(
    path: Path,
    *,
    personal_categories: bool = False,
    compiled_modules: bool = False,
) -> None:
    private_buffer = io.BytesIO()
    with tarfile.open(fileobj=private_buffer, mode="w") as archive:
        extension = "pyc" if compiled_modules else "py"
        files = {
            f"app.{extension}": b"",
            f"main.{extension}": b"",
            f"mobile.{extension}": b"",
            "defaults/categories.json": json.dumps({"categories": {}}).encode(),
        }
        if personal_categories:
            files["user_categories.json"] = b'{"categories":{"private":{}}}'
        for name, payload in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr("assets/private.tar", private_buffer.getvalue())
        archive.writestr("lib/arm64-v8a/libpython.so", b"ELF")


class AndroidPackageInspectionTests(unittest.TestCase):
    def test_clean_apk_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "clean.apk"
            _apk(path)
            self.assertEqual(inspect_apk(path), [])

    def test_compiled_android_modules_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "compiled.apk"
            _apk(path, compiled_modules=True)
            self.assertEqual(inspect_apk(path), [])

    def test_personal_categories_fail_the_build(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "leaked.apk"
            _apk(path, personal_categories=True)
            errors = inspect_apk(path)
            self.assertTrue(any("user_categories.json" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
