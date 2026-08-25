import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import database


class DownloadDatabaseTests(unittest.TestCase):
    def setUp(self):
        self._schema_ready = database._schema_ready

    def tearDown(self):
        database._schema_ready = self._schema_ready
        database._invalidate_phash_cache()

    def test_old_download_database_gets_public_uri_column(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "old.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """CREATE TABLE downloads (
                    id INTEGER PRIMARY KEY,
                    source_id TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    file_path TEXT,
                    phash TEXT,
                    downloaded_at INTEGER
                )"""
            )
            conn.commit()
            conn.close()

            with patch.object(database, "DB_PATH", db_path):
                database._schema_ready = False
                migrated = database._connect()
                columns = {
                    row[1]
                    for row in migrated.execute("PRAGMA table_info(downloads)").fetchall()
                }
                migrated.close()

        self.assertIn("public_uri", columns)

    def test_public_uri_can_be_registered_and_updated(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "downloads.db"
            private_file = str(Path(temp) / "downloads" / "art.jpg")
            with patch.object(database, "DB_PATH", db_path):
                database._schema_ready = False
                database.register_download(
                    "Danbooru",
                    "42",
                    private_file,
                    public_uri="content://media/42",
                )
                row = database.get_download_by_file_path(private_file)
                self.assertEqual(row["public_uri"], "content://media/42")
                self.assertTrue(database.set_download_public_uri(private_file, ""))
                row = database.get_download_by_file_path(private_file)
                self.assertEqual(row["public_uri"], "")

    def test_favorites_can_be_organized_without_duplicating_artwork(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "library.db"
            with patch.object(database, "DB_PATH", db_path):
                database._schema_ready = False
                self.assertTrue(database.add_favorite("Pixiv", "42", url="https://example.com/42.jpg"))
                references = database.create_collection("Referências")
                colors = database.create_collection("Cores")
                assigned = database.set_favorite_collections(
                    "Pixiv", "42", [references["id"], colors["id"], 999999]
                )

                self.assertEqual(assigned, [references["id"], colors["id"]])
                favorite = database.get_favorites()[0]
                self.assertEqual(favorite["collection_ids"], assigned)
                self.assertEqual(sum(item["item_count"] for item in database.get_collections()), 2)

                self.assertTrue(database.delete_collection(references["id"]))
                favorite = database.get_favorites()[0]
                self.assertEqual(favorite["collection_ids"], [colors["id"]])

    def test_collection_names_are_unique_ignoring_case(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "library.db"
            with patch.object(database, "DB_PATH", db_path):
                database._schema_ready = False
                database.create_collection("Inspiração")
                with self.assertRaises(sqlite3.IntegrityError):
                    database.create_collection("inspiração")


if __name__ == "__main__":
    unittest.main()
