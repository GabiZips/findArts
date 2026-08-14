import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.inspect_android_apk import REQUIRED_RUNTIME_PACKAGES, inspect_apk


def _apk(
    path: Path,
    *,
    personal_categories: bool = False,
    compiled_modules: bool = False,
    missing_runtime_package: str | None = None,
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

    runtime_buffer = io.BytesIO()
    with tarfile.open(fileobj=runtime_buffer, mode="w:gz") as runtime:
        for package in REQUIRED_RUNTIME_PACKAGES - {missing_runtime_package}:
            name = f"_python_bundle/site-packages/{package}/__init__.pyc"
            info = tarfile.TarInfo(name)
            runtime.addfile(info, io.BytesIO())

    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr("assets/private.tar", private_buffer.getvalue())
        archive.writestr("lib/arm64-v8a/libpython.so", b"ELF")
        archive.writestr("lib/arm64-v8a/libpybundle.so", runtime_buffer.getvalue())


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

    def test_missing_runtime_dependency_fails_the_build(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing-urllib3.apk"
            _apk(path, missing_runtime_package="urllib3")
            errors = inspect_apk(path)
            self.assertTrue(any("urllib3" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
