import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from utils.credential_store import CredentialStore, CredentialStoreError, native_backend
from utils.credentials import CREDENTIAL_KEYS, resolve_credentials, save_credentials, clean_legacy_credentials


class FakeBackend:
    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[service, username] = password

    def delete_password(self, service, username):
        self.values.pop((service, username), None)


class CredentialStoreTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.store = CredentialStore(self.backend, frozenset({"TOKEN"}), "test-only")

    def test_roundtrip_and_idempotent_delete(self):
        self.assertIsNone(self.store.read("TOKEN"))
        self.store.write("TOKEN", "synthetic-value")
        self.assertEqual(self.store.read("TOKEN"), "synthetic-value")
        self.store.delete("TOKEN")
        self.store.delete("TOKEN")
        self.assertIsNone(self.store.read("TOKEN"))

    def test_unknown_fields_rejected_before_backend(self):
        for operation in [lambda: self.store.read("OTHER"),
                          lambda: self.store.write("OTHER", "test"),
                          lambda: self.store.delete("OTHER")]:
            with self.assertRaises(CredentialStoreError):
                operation()
        self.assertEqual(self.backend.values, {})

    def test_invalid_values_rejected(self):
        for value in [None, 42, "", "invalid\x00value"]:
            with self.assertRaises(CredentialStoreError):
                self.store.write("TOKEN", value)

    def test_backend_error_does_not_expose_secret(self):
        with patch.object(self.backend, "get_password", side_effect=RuntimeError("secret-probe")):
            with self.assertRaises(CredentialStoreError) as error:
                self.store.read("TOKEN")
        self.assertNotIn("secret-probe", str(error.exception))
        self.assertTrue(error.exception.__suppress_context__)

    def test_readback_mismatch_is_failure(self):
        with patch.object(self.backend, "set_password"):
            with self.assertRaises(CredentialStoreError):
                self.store.write("TOKEN", "synthetic-value")

    def test_delete_must_be_verified(self):
        self.store.write("TOKEN", "synthetic-value")
        with patch.object(self.backend, "delete_password"):
            with self.assertRaises(CredentialStoreError):
                self.store.delete("TOKEN")

    def test_unsupported_platform_has_no_fallback(self):
        with patch("utils.credential_store.sys.platform", "unsupported"):
            with self.assertRaises(CredentialStoreError):
                native_backend()

    def test_service_namespaces_are_isolated(self):
        self.store.write("TOKEN", "synthetic-value")
        other = CredentialStore(self.backend, frozenset({"TOKEN"}), "other-test")
        self.assertIsNone(other.read("TOKEN"))


class CredentialPolicyTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.store = CredentialStore(self.backend, CREDENTIAL_KEYS, "policy-test")
        self.key = "PIXIV_REFRESH_TOKEN"

    def test_legacy_is_read_only_when_native_entry_absent(self):
        self.assertEqual(resolve_credentials(self.store, {self.key: "legacy"})[self.key], "legacy")
        save_credentials(self.store, {self.key: "native"}, set())
        self.assertEqual(resolve_credentials(self.store, {self.key: "legacy"})[self.key], "native")

    def test_removal_survives_restart_with_legacy_secret(self):
        save_credentials(self.store, {}, {self.key})
        restarted = CredentialStore(self.backend, CREDENTIAL_KEYS, "policy-test")
        self.assertEqual(resolve_credentials(restarted, {self.key: "legacy"})[self.key], "")

    def test_locked_store_never_falls_back(self):
        with patch.object(self.backend, "get_password", side_effect=RuntimeError("locked")):
            with self.assertRaises(CredentialStoreError):
                resolve_credentials(self.store, {self.key: "legacy"})

    def test_invalid_record_never_falls_back(self):
        self.store.write(self.key, "malformed")
        with self.assertRaises(CredentialStoreError):
            resolve_credentials(self.store, {self.key: "legacy"})

    def test_partial_failure_restores_previous_records(self):
        save_credentials(self.store, {self.key: "old"}, set())
        original = self.store.write
        def fail_one(key, value):
            if key == self.key and 'new' in value:
                raise CredentialStoreError("synthetic failure")
            return original(key, value)
        with patch.object(self.store, "write", side_effect=fail_one):
            with self.assertRaises(CredentialStoreError):
                save_credentials(self.store, {self.key: "new", "BSKY_HANDLE": "test"}, set())
        self.assertEqual(resolve_credentials(self.store, {})[self.key], "old")
        self.assertIsNone(self.store.read("BSKY_HANDLE"))

    def test_cleanup_keeps_unmigrated_and_unrelated_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_bytes(b'# comment\r\nPIXIV_REFRESH_TOKEN="test"\r\nBSKY_PASSWORD=unmigrated\r\nOTHER=keep\r\n')
            save_credentials(self.store, {self.key: "test"}, set())
            result = clean_legacy_credentials(self.store, path)
            self.assertEqual(result, {"removed": 1, "remaining": 1})
            self.assertEqual(path.read_bytes(), b'# comment\r\nBSKY_PASSWORD=unmigrated\r\nOTHER=keep\r\n')
            self.assertEqual(clean_legacy_credentials(self.store, path)["removed"], 0)

    def test_cleanup_preserves_conflicting_legacy_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('PIXIV_REFRESH_TOKEN=legacy\n', encoding='utf-8')
            save_credentials(self.store, {self.key: "different"}, set())
            self.assertEqual(clean_legacy_credentials(self.store, path)["remaining"], 1)
            self.assertIn('legacy', path.read_text())

    def test_cleanup_locked_vault_preserves_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            content = 'PIXIV_REFRESH_TOKEN=test\n'
            path.write_text(content, encoding='utf-8')
            with patch.object(self.store, "read", side_effect=CredentialStoreError("locked")):
                with self.assertRaises(CredentialStoreError):
                    clean_legacy_credentials(self.store, path)
            self.assertEqual(path.read_text(), content)
