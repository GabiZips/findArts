import asyncio
import json
import os
import socket
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import MagicMock, patch

import app
import config
from fastapi import Request
from utils.downloader import _safe_component
from utils.network import RemoteURLRejected, is_domain, validate_remote_url


class NetworkSafetyTests(unittest.TestCase):
    def test_domain_match_does_not_accept_lookalikes(self):
        self.assertTrue(is_domain("cdn.donmai.us", "donmai.us"))
        self.assertFalse(is_domain("donmai.us.evil.example", "donmai.us"))

    def test_loopback_destination_is_rejected(self):
        resolved = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 80),
            )
        ]
        with patch("utils.network.socket.getaddrinfo", return_value=resolved):
            with self.assertRaises(RemoteURLRejected):
                validate_remote_url("http://example.test/image.jpg")

    def test_non_web_scheme_is_rejected(self):
        with self.assertRaises(RemoteURLRejected):
            validate_remote_url("file:///windows/system.ini")


class AppRouteTests(unittest.TestCase):
    @staticmethod
    def _request(
        path: str = "/api/health",
        query: bytes = b"",
        client: str = "192.168.1.50",
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> Request:
        return Request({
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query,
            "headers": headers or [(b"host", b"192.168.1.10:7860")],
            "client": (client, 54321),
            "server": ("192.168.1.10", 7860),
            "root_path": "",
        })

    def test_interface_loads_shared_language_runtime(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn('id="languageSelect"', html)
        self.assertIn('src="/ui/i18n.js"', html)
        self.assertIn('src="/ui/viewer.js"', html)
        self.assertIn('href="/ui/viewer.css"', html)

        script = asyncio.run(app.i18n_script())
        self.assertEqual(Path(script.path).name, "i18n.js")
        viewer_script = asyncio.run(app.viewer_script())
        viewer_styles = asyncio.run(app.viewer_styles())
        self.assertEqual(Path(viewer_script.path).name, "viewer.js")
        self.assertEqual(Path(viewer_styles.path).name, "viewer.css")

    def test_interface_has_persistent_nsfw_blur_and_zoom_controls(self):
        html = asyncio.run(app.index()).body.decode("utf-8")
        self.assertIn('onchange="setNsfwBlur(this.checked)"', html)
        self.assertIn('id="lbNsfwReveal"', html)
        self.assertIn('id="lbZoomLabel"', html)
        script = Path("templates/viewer.js").read_text(encoding="utf-8")
        self.assertIn('artfinder.blurNsfw', script)
        self.assertIn('scale + delta', script)

    def test_interface_has_non_streaming_search_fallback(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn('contentType.includes("text/event-stream")', html)
        self.assertIn('fetch("/api/search"', html)
        self.assertIn("Adicionar personagem ou tag", html)

    def test_category_manager_exposes_group_choices_and_source_overrides(self):
        html = asyncio.run(app.index()).body.decode("utf-8")
        self.assertIn('list="cmGroupOptions"', html)
        self.assertIn('id="cmSearch"', html)
        self.assertIn('data-cm-source="pixiv"', html)
        self.assertIn('data-cm-source="bluesky"', html)
        self.assertIn('id="cmQueryPreview"', html)
        self.assertIn("replace_source_tags:true", html)
        self.assertNotIn("onclick=\"editCmCat('${k}')\"", html)

    def test_interface_respects_android_system_bar_safe_areas(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn("viewport-fit=cover", html)
        self.assertIn("env(safe-area-inset-top,0px)", html)
        self.assertIn("top:var(--safe-top)", html)
        self.assertIn("bottom:var(--safe-bottom)", html)

    def test_interface_exposes_android_gallery_export_actions(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn('fetch("/api/export-image"', html)
        self.assertIn("📱 Salvar no celular", html)
        self.assertIn("Pictures/ArtFinder", html)

    def test_interface_exposes_encrypted_device_pairing(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn('id="pairingModal"', html)
        self.assertIn('fetch("/api/pairing/create"', html)
        self.assertIn('fetch("/api/pairing/import"', html)
        self.assertIn('crypto.subtle.decrypt', html)
        self.assertIn("artfinder-pair:v1:", html)

    def test_mobile_pairing_uses_local_relay_and_code_only(self):
        html = asyncio.run(app.index()).body.decode("utf-8")
        self.assertIn('fetch("/api/pairing/fetch"', html)
        self.assertNotIn('capture="environment"', html)
        self.assertNotIn("BarcodeDetector", html)
        self.assertNotIn('confirm(t("Importar tags e credenciais deste PC?"))', html)

    def test_category_form_uses_source_mapping_examples(self):
        response = asyncio.run(app.index())
        html = response.body.decode("utf-8")
        self.assertIn("vex_(league_of_legends)", html)
        self.assertIn('data-cm-source="pixiv"', html)
        self.assertIn("ex: ヴェックス", html)
        self.assertNotIn("shadow_the_hedgehog -rouge_the_bat", html)

    def test_lan_mode_rejects_remote_requests_without_token(self):
        async def next_handler(_request):
            return app.Response("ok")

        with patch.dict(
            app.os.environ,
            {"ARTFINDER_LAN": "1", "ARTFINDER_LAN_TOKEN": "test-secret"},
            clear=False,
        ):
            response = asyncio.run(
                app.local_security_headers(self._request(), next_handler)
            )
        self.assertEqual(response.status_code, 401)

    def test_lan_token_is_exchanged_for_httponly_cookie(self):
        async def next_handler(_request):
            return app.Response("ok")

        with patch.dict(
            app.os.environ,
            {"ARTFINDER_LAN": "1", "ARTFINDER_LAN_TOKEN": "test-secret"},
            clear=False,
        ):
            response = asyncio.run(
                app.local_security_headers(
                    self._request(path="/", query=b"access_token=test-secret"),
                    next_handler,
                )
            )
        self.assertEqual(response.status_code, 303)
        cookie = SimpleCookie()
        cookie.load(response.headers["set-cookie"])
        self.assertTrue(cookie["artfinder_lan_session"]["httponly"])
        self.assertEqual(response.headers["location"], "/")

    def test_lan_mode_keeps_loopback_available_without_token(self):
        async def next_handler(_request):
            return app.Response("ok")

        with patch.dict(
            app.os.environ,
            {"ARTFINDER_LAN": "1", "ARTFINDER_LAN_TOKEN": "test-secret"},
            clear=False,
        ):
            response = asyncio.run(
                app.local_security_headers(
                    self._request(client="127.0.0.1"),
                    next_handler,
                )
            )
        self.assertEqual(response.status_code, 200)

    def test_fresh_install_starts_without_categories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            defaults = root / "defaults.json"
            defaults.write_text('{"categories": {}}\n', encoding="utf-8")
            user_file = root / "data" / "user_categories.json"
            with (
                patch.object(app, "DEFAULT_USER_CATS_FILE", defaults),
                patch.object(app, "USER_CATS_FILE", user_file),
            ):
                self.assertEqual(app._load_user_cats(), {})
                self.assertEqual(
                    json.loads(user_file.read_text(encoding="utf-8")),
                    {"categories": {}},
                )

    def test_obsolete_bundled_categories_are_migrated_but_user_edits_are_not(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            defaults = root / "defaults.json"
            defaults.write_text('{"categories": {}}\n', encoding="utf-8")
            user_file = root / "user_categories.json"
            leaked = b'{"categories":{"legacy":{}}}'
            user_file.write_bytes(leaked)
            leaked_hash = __import__("hashlib").sha256(leaked).hexdigest()
            with (
                patch.object(app, "DEFAULT_USER_CATS_FILE", defaults),
                patch.object(app, "USER_CATS_FILE", user_file),
                patch.object(app, "_LEGACY_BUNDLED_CATEGORY_HASHES", {leaked_hash}),
                patch.object(app.sys, "frozen", True, create=True),
            ):
                self.assertEqual(app._load_user_cats(), {})
                self.assertTrue((root / "user_categories.legacy-backup.json").exists())

            edited = b'{"categories":{"mine":{"tags":"mine"}}}'
            user_file.write_bytes(edited)
            with (
                patch.object(app, "USER_CATS_FILE", user_file),
                patch.object(app, "_LEGACY_BUNDLED_CATEGORY_HASHES", {leaked_hash}),
                patch.object(app.sys, "frozen", True, create=True),
            ):
                self.assertIn("mine", app._load_user_cats())

    def test_gelbooru_is_not_enabled_without_credentials(self):
        with (
            patch.object(config, "GELBOORU_USER_ID", ""),
            patch.object(config, "GELBOORU_API_KEY", ""),
        ):
            self.assertNotIn("Gelbooru", app._get_sources())

    def test_sources_distinguish_broken_connector_from_missing_credentials(self):
        with (
            patch.object(app, "_get_sources", return_value={}),
            patch.object(config, "PIXIV_REFRESH_TOKEN", ""),
        ):
            result = asyncio.run(app.list_sources())
        unavailable = {entry["name"]: entry for entry in result["unavailable_sources"]}
        self.assertEqual(unavailable["Danbooru"]["status"], "unavailable")
        self.assertEqual(unavailable["Danbooru"]["missing"], [])
        self.assertEqual(unavailable["Pixiv"]["status"], "configuration_required")

    def test_sync_search_reports_source_failures(self):
        def broken_source(*args, **kwargs):
            raise RuntimeError("network unavailable")

        errors = []
        posts = app._run_search_sync(
            [],
            ["Broken"],
            1,
            [{"label": "test", "tags": "test_tag"}],
            {"Broken": broken_source},
            errors,
        )
        self.assertEqual(posts, [])
        self.assertEqual(errors[0]["source"], "Broken")
        self.assertIn("network unavailable", errors[0]["error"])

    def test_credential_status_never_returns_secret_values(self):
        with patch.object(config, "PIXIV_REFRESH_TOKEN", "super-secret-token"):
            response = asyncio.run(app.credential_settings())
        self.assertNotIn("super-secret-token", str(response))
        pixiv = next(group for group in response["groups"] if group["source"] == "Pixiv")
        self.assertTrue(pixiv["fields"][0]["configured"])

    def test_credential_writer_preserves_unrelated_env_values(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(app, "DATA_DIR", temp), patch.object(app, "profile_store") as factory:
            factory.return_value.read.return_value = None
            env_path = Path(temp) / ".env"
            env_path.write_text("UNRELATED=keep\nPIXIV_REFRESH_TOKEN=old\n", encoding="utf-8")
            app._write_credentials({"PIXIV_REFRESH_TOKEN": "new"}, set())
            self.assertEqual(
                env_path.read_text(encoding="utf-8"),
                "UNRELATED=keep\nPIXIV_REFRESH_TOKEN=old\n",
            )
            saved = json.loads(factory.return_value.write.call_args.args[1])
            self.assertEqual(saved["value"], "new")

    def test_unknown_credential_field_is_rejected(self):
        response = asyncio.run(
            app.save_credential_settings({"values": {"UNSAFE_FIELD": "value"}})
        )
        self.assertEqual(response.status_code, 400)

    def test_migration_preserves_existing_native_entries(self):
        with patch.object(app, "profile_store") as factory, patch.object(config, "CREDENTIAL_STORAGE_ERROR", False), patch.object(app, "_configured_credential_values", return_value={"PIXIV_REFRESH_TOKEN": "legacy"}):
            factory.return_value.read.return_value = '{"version":1,"value":"native"}'
            result = asyncio.run(app.migrate_credential_settings())
            self.assertEqual(result["migrated"], 0)
            factory.return_value.write.assert_not_called()

    def test_migration_copies_missing_and_is_explicit(self):
        with patch.object(app, "profile_store") as factory, patch.object(config, "CREDENTIAL_STORAGE_ERROR", False), patch.object(app, "_configured_credential_values", return_value={"PIXIV_REFRESH_TOKEN": "legacy"}):
            factory.return_value.read.return_value = None
            result = asyncio.run(app.migrate_credential_settings())
            self.assertEqual(result["migrated"], 1)
            self.assertTrue(result["legacy_file_preserved"])
            self.assertNotIn("legacy", json.dumps(result).replace("legacy_file_preserved", ""))

    def test_save_vault_failure_is_safe_response(self):
        from utils.credential_store import CredentialStoreError
        with patch.object(app, "_write_credentials", side_effect=CredentialStoreError("secret-probe")):
            result = asyncio.run(app.save_credential_settings({"values": {"PIXIV_REFRESH_TOKEN": "test"}}))
        self.assertEqual(result.status_code, 503)
        self.assertNotIn(b"secret-probe", result.body)

    def test_malformed_credential_clear_list_is_rejected(self):
        response = asyncio.run(app.save_credential_settings({"clear": [{}]}))
        self.assertEqual(response.status_code, 400)

    def test_mobile_cannot_create_pairing_export(self):
        with patch.dict(os.environ, {"ARTFINDER_MOBILE": "1"}, clear=False):
            response = asyncio.run(
                app.create_pairing(
                    self._request(client="127.0.0.1"),
                    {"categories": True, "credentials": True},
                )
            )
        self.assertEqual(response.status_code, 400)

    def test_pairing_export_encrypts_only_whitelisted_configuration(self):
        fake_session = MagicMock(
            expires_at=123456,
            options=[{"address": "192.168.1.10", "code": "opaque"}],
        )
        with (
            patch.dict(os.environ, {"ARTFINDER_MOBILE": "0"}, clear=False),
            patch.object(app, "_load_user_cats", return_value={"vex": {"tags": "vex"}}),
            patch.object(
                app,
                "_configured_credential_values",
                return_value={"PIXIV_REFRESH_TOKEN": "secret-token"},
            ),
            patch.object(app.pairing_manager, "create", return_value=fake_session) as create,
        ):
            response = asyncio.run(
                app.create_pairing(
                    self._request(client="127.0.0.1"),
                    {"categories": True, "credentials": True},
                )
            )
        payload = create.call_args.args[0]
        self.assertEqual(payload["categories"]["vex"]["tags"], "vex")
        self.assertEqual(payload["credentials"]["PIXIV_REFRESH_TOKEN"], "secret-token")
        self.assertTrue(set(payload["credentials"]) <= app._CREDENTIAL_KEYS)
        self.assertNotIn("secret-token", str(response))

    def test_pairing_export_rejects_non_boolean_options(self):
        with patch.dict(os.environ, {"ARTFINDER_MOBILE": "0"}, clear=False):
            response = asyncio.run(
                app.create_pairing(
                    self._request(client="127.0.0.1"),
                    {"categories": "yes", "credentials": True},
                )
            )
        self.assertEqual(response.status_code, 400)

    def test_pairing_import_merges_categories_and_saves_allowed_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            user_file = root / "user_categories.json"
            user_file.write_text(
                json.dumps({"categories": {"existing": {"tags": "existing"}}}),
                encoding="utf-8",
            )
            payload = {
                "version": 1,
                "source": "My PC",
                "sections": {"categories": True, "credentials": True},
                "categories": {
                    "vex": {
                        "label": "Vex",
                        "tags": "vex_(league_of_legends)",
                        "source_tags": {"pixiv": ["ヴェックス"]},
                    }
                },
                "credentials": {"PIXIV_REFRESH_TOKEN": "paired-token"},
            }
            with (
                patch.object(app, "USER_CATS_FILE", user_file),
                patch.object(app, "DATA_DIR", root),
                patch.object(config, "PIXIV_REFRESH_TOKEN", ""),
                patch.object(app, "_apply_credentials"),
                patch.object(app, "profile_store") as factory,
            ):
                factory.return_value.read.return_value = None
                response = asyncio.run(
                    app.import_pairing({"payload": payload, "mode": "merge"})
                )
                categories = app._load_user_cats()
            self.assertTrue(response["ok"])
            self.assertEqual(set(categories), {"existing", "vex"})
            self.assertEqual(
                categories["vex"]["source_tags"]["pixiv"],
                ["ヴェックス"],
            )
            self.assertFalse((root / ".env").exists())
            self.assertEqual(json.loads(factory.return_value.write.call_args.args[1])["value"], "paired-token")

    def test_pairing_import_rejects_unknown_credential(self):
        payload = {
            "version": 1,
            "sections": {"categories": False, "credentials": True},
            "categories": {},
            "credentials": {"UNSAFE_FIELD": "secret"},
        }
        response = asyncio.run(app.import_pairing({"payload": payload}))
        self.assertEqual(response.status_code, 400)

    def test_mobile_pairing_relay_fetches_private_endpoint_without_proxy(self):
        from utils import pairing

        code = pairing._pairing_code(
            "http://192.168.1.20:54321/v1/pair/token",
            b"k" * 32,
        )
        envelope = {
            "version": 1,
            "algorithm": "AES-256-GCM",
            "nonce": "nonce",
            "ciphertext": "ciphertext",
        }
        response = MagicMock(status_code=200)
        response.__enter__.return_value = response
        response.iter_content.return_value = [json.dumps(envelope).encode()]
        session = MagicMock()
        session.__enter__.return_value = session
        session.get.return_value = response
        with patch.object(app._requests, "Session", return_value=session):
            result = asyncio.run(app.fetch_pairing_envelope(
                self._request(client="127.0.0.1"),
                {"code": code},
            ))
        self.assertTrue(result["ok"])
        self.assertEqual(result["envelope"], envelope)
        self.assertFalse(session.trust_env)
        session.get.assert_called_once_with(
            "http://192.168.1.20:54321/v1/pair/token",
            headers={"Accept": "application/json"},
            timeout=(3, 8),
            allow_redirects=False,
            stream=True,
        )

    def test_mobile_pairing_relay_rejects_public_endpoint(self):
        from utils import pairing

        code = pairing._pairing_code(
            "http://8.8.8.8:54321/v1/pair/token",
            b"k" * 32,
        )
        result = asyncio.run(app.fetch_pairing_envelope(
            self._request(client="127.0.0.1"),
            {"code": code},
        ))
        self.assertEqual(result.status_code, 400)

    def test_database_is_not_served_as_download(self):
        response = asyncio.run(app.downloaded_file("artfinder.db"))
        self.assertEqual(response.status_code, 403)

    def test_database_is_not_served_as_thumbnail(self):
        response = asyncio.run(app.thumb("artfinder.db"))
        self.assertEqual(response.status_code, 403)

    def test_database_is_not_accepted_by_delete_endpoint(self):
        response = asyncio.run(app.delete_image({"rel_path": "artfinder.db"}))
        self.assertEqual(response.status_code, 403)

    def test_android_can_export_an_existing_private_download(self):
        from utils import android_media, database

        with tempfile.TemporaryDirectory() as temp:
            download_root = Path(temp) / "downloads"
            image = download_root / "vex" / "Danbooru_42.jpg"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"image")
            with (
                patch.object(app, "DOWNLOAD_DIR", download_root),
                patch.dict(os.environ, {"ARTFINDER_MOBILE": "1"}, clear=False),
                patch.object(
                    database,
                    "get_download_by_file_path",
                    return_value={"public_uri": ""},
                ),
                patch.object(database, "set_download_public_uri", return_value=True),
                patch.object(
                    android_media,
                    "publish_image",
                    return_value="content://media/42",
                ),
            ):
                response = asyncio.run(
                    app.export_image_to_android_gallery(
                        {"rel_path": "vex/Danbooru_42.jpg"}
                    )
                )
        self.assertTrue(response["ok"])
        self.assertEqual(response["public_uri"], "content://media/42")

    def test_android_delete_failure_preserves_private_copy(self):
        from utils import android_media, database

        with tempfile.TemporaryDirectory() as temp:
            download_root = Path(temp) / "downloads"
            image = download_root / "vex" / "Danbooru_42.jpg"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"image")
            with (
                patch.object(app, "DOWNLOAD_DIR", download_root),
                patch.dict(os.environ, {"ARTFINDER_MOBILE": "1"}, clear=False),
                patch.object(
                    database,
                    "get_download_by_file_path",
                    return_value={"public_uri": "content://media/42"},
                ),
                patch.object(
                    android_media,
                    "delete_image",
                    side_effect=android_media.AndroidMediaError("provider failed"),
                ),
            ):
                response = asyncio.run(
                    app.delete_image({"rel_path": "vex/Danbooru_42.jpg"})
                )
                self.assertTrue(image.exists())
        self.assertEqual(response.status_code, 502)

    def test_android_delete_removes_public_and_private_copies(self):
        from utils import android_media, database

        connection = MagicMock()
        connection.execute.return_value.rowcount = 1
        with tempfile.TemporaryDirectory() as temp:
            download_root = Path(temp) / "downloads"
            image = download_root / "vex" / "Danbooru_42.jpg"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"image")
            with (
                patch.object(app, "DOWNLOAD_DIR", download_root),
                patch.dict(os.environ, {"ARTFINDER_MOBILE": "1"}, clear=False),
                patch.object(
                    database,
                    "get_download_by_file_path",
                    return_value={"public_uri": "content://media/42"},
                ),
                patch.object(database, "set_download_public_uri", return_value=True),
                patch.object(database, "_connect", return_value=connection),
                patch.object(database, "_invalidate_phash_cache"),
                patch.object(android_media, "delete_image", return_value=True) as public_delete,
            ):
                response = asyncio.run(
                    app.delete_image({"rel_path": "vex/Danbooru_42.jpg"})
                )
                self.assertFalse(image.exists())
        self.assertTrue(response["deleted"])
        self.assertTrue(response["public_deleted"])
        public_delete.assert_called_once_with("content://media/42")

    def test_source_prefix_parser(self):
        base, sources = app._parse_source_prefixes(
            "vex_(league_of_legends); pixiv: ヴェックス; tumblr: vex lol"
        )
        self.assertEqual(base, "vex_(league_of_legends)")
        self.assertEqual(sources["pixiv"], ["ヴェックス"])
        self.assertEqual(sources["tumblr"], ["vex lol"])

    def test_category_editor_can_remove_an_existing_source_override(self):
        existing = {
            "vex": {
                "label": "Vex",
                "tags": "vex_(league_of_legends)",
                "source_tags": {"pixiv": ["ヴェックス"]},
            }
        }
        saved = {}
        with (
            patch.object(app, "_load_user_cats", return_value=existing),
            patch.object(app, "_save_user_cats", side_effect=lambda cats: saved.update(cats)),
        ):
            response = asyncio.run(app.create_category({
                "key": "vex",
                "label": "Vex",
                "tags": "vex_(league_of_legends)",
                "source_tags": {},
                "replace_source_tags": True,
                "auto_map": False,
            }))
        self.assertTrue(response["ok"])
        self.assertNotIn("source_tags", saved["vex"])

    def test_new_category_key_is_url_safe_and_source_queries_are_split(self):
        saved = {}
        with (
            patch.object(app, "_load_user_cats", return_value={}),
            patch.object(app, "_save_user_cats", side_effect=lambda cats: saved.update(cats)),
        ):
            response = asyncio.run(app.create_category({
                "key": "V (Cyberpunk)",
                "label": "V",
                "tags": "v_(cyberpunk_2077)",
                "source_tags": {"bsky": "V Cyberpunk; V Cyberpunk 2077"},
                "replace_source_tags": True,
                "auto_map": False,
            }))
        self.assertEqual(response["key"], "v_cyberpunk")
        self.assertEqual(saved["v_cyberpunk"]["source_tags"]["bluesky"], [
            "V Cyberpunk",
            "V Cyberpunk 2077",
        ])

    def test_category_rejects_unknown_source_override(self):
        with patch.object(app, "_load_user_cats", return_value={}):
            response = asyncio.run(app.create_category({
                "key": "vex",
                "label": "Vex",
                "tags": "vex_(league_of_legends)",
                "source_tags": {"unknown": ["vex"]},
                "auto_map": False,
            }))
        self.assertEqual(response.status_code, 400)

    def test_direct_source_tags_extend_legacy_prefixed_tags(self):
        saved = {}
        with (
            patch.object(app, "_load_user_cats", return_value={}),
            patch.object(app, "_save_user_cats", side_effect=lambda cats: saved.update(cats)),
        ):
            response = asyncio.run(app.create_category({
                "key": "vex",
                "label": "Vex",
                "tags": "vex_(league_of_legends); pixiv: ヴェックス",
                "source_tags": {"pixiv": ["Vex LoL"]},
                "replace_source_tags": True,
                "auto_map": False,
            }))
        self.assertTrue(response["ok"])
        self.assertEqual(saved["vex"]["source_tags"]["pixiv"], [
            "ヴェックス",
            "Vex LoL",
        ])

    def test_filename_components_have_no_path_syntax(self):
        self.assertEqual(_safe_component("../../bad:id"), "badid")


if __name__ == "__main__":
    unittest.main()
