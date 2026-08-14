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


if __name__ == "__main__":
    unittest.main()
