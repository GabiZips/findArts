use crate::sources::{Post, R};
use rusqlite::{params, Connection, OptionalExtension};
use std::{
    io::{Cursor, Write},
    path::{Path, PathBuf},
};
pub struct Library {
    db: Connection,
    pub root: PathBuf,
}
fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}
pub fn video_ext(b: &[u8]) -> Option<&'static str> {
    if b.len() > 16
        && b.get(4..8) == Some(b"ftyp")
        && u32::from_be_bytes(b[..4].try_into().ok()?) >= 16
    {
        Some("mp4")
    } else if b.starts_with(&[0x1a, 0x45, 0xdf, 0xa3])
        && b.iter()
            .take(512)
            .copied()
            .collect::<Vec<_>>()
            .windows(4)
            .any(|s| s == b"webm")
    {
        Some("webm")
    } else {
        None
    }
}
pub fn decode(bytes: &[u8]) -> R<image::DynamicImage> {
    let mut reader = image::ImageReader::new(Cursor::new(bytes))
        .with_guessed_format()
        .map_err(err)?;
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(16000);
    limits.max_image_height = Some(16000);
    limits.max_alloc = Some(256 << 20);
    reader.limits(limits);
    reader.decode().map_err(err)
}
impl Library {
    pub fn open(root: &Path) -> R<Self> {
        std::fs::create_dir_all(root.join("downloads")).map_err(err)?;
        let db = Connection::open(root.join("library.sqlite3")).map_err(err)?;
        db.execute_batch("PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;
 CREATE TABLE IF NOT EXISTS posts(id TEXT PRIMARY KEY,data TEXT NOT NULL,favorite INTEGER DEFAULT 0,file TEXT,hash TEXT,seen INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS names(kind TEXT,name TEXT,value TEXT DEFAULT '',PRIMARY KEY(kind,name));
 CREATE TABLE IF NOT EXISTS members(collection TEXT,id TEXT REFERENCES posts(id),PRIMARY KEY(collection,id));").map_err(err)?;
        Ok(Self {
            db,
            root: root.into(),
        })
    }
    pub fn names(&self, kind: &str) -> R<Vec<(String, String)>> {
        let mut stmt = self
            .db
            .prepare("SELECT name,value FROM names WHERE kind=? ORDER BY name")
            .map_err(err)?;
        let rows = stmt
            .query_map([kind], |r| Ok((r.get(0)?, r.get(1)?)))
            .map_err(err)?;
        rows.collect::<Result<_, _>>().map_err(err)
    }
    pub fn set(&self, k: &str, n: &str, v: &str) -> R<()> {
        if n.trim().is_empty() {
            return Err("Informe o nome".into());
        }
        self.db.execute("INSERT INTO names VALUES(?,?,?) ON CONFLICT(kind,name) DO UPDATE SET value=excluded.value",params![k,n.trim(),v.trim()]).map_err(err)?;
        Ok(())
    }
    pub fn remove(&mut self, k: &str, n: &str) -> R<()> {
        let tx = self.db.transaction().map_err(err)?;
        if k == "category" {
            tx.execute("DELETE FROM names WHERE name=? AND (kind LIKE 'tags/%' OR kind IN ('favorite_category','category_meta','order'))",[n]).map_err(err)?;
        }
        if k == "collection" {
            tx.execute("DELETE FROM members WHERE collection=?", [n])
                .map_err(err)?;
        }
        tx.execute("DELETE FROM names WHERE kind=? AND name=?", params![k, n])
            .map_err(err)?;
        tx.commit().map_err(err)
    }
    pub fn details(&self, id: &str) -> R<(bool, Option<String>)> {
        self.db
            .query_row("SELECT favorite,file FROM posts WHERE id=?", [id], |r| {
                Ok((r.get(0)?, r.get(1)?))
            })
            .optional()
            .map(|row| row.unwrap_or_default())
            .map_err(err)
    }
    pub fn save_favorite(&self, post: &Post, favorite: bool) -> R<()> {
        if favorite {
            self.db
                .execute(
                    "INSERT INTO posts(id,data,seen,favorite) VALUES(?,?,unixepoch(),1)
                 ON CONFLICT(id) DO UPDATE SET favorite=1",
                    params![post.key(), serde_json::to_string(post).map_err(err)?],
                )
                .map_err(err)?;
        } else {
            self.db
                .execute("UPDATE posts SET favorite=0 WHERE id=?", [post.key()])
                .map_err(err)?;
        }
        Ok(())
    }
    pub fn collection(&self, id: &str, n: &str) -> R<bool> {
        self.db
            .query_row(
                "SELECT EXISTS(SELECT 1 FROM members WHERE id=? AND collection=?)",
                params![id, n],
                |r| r.get(0),
            )
            .map_err(err)
    }
    pub fn assign(&mut self, post: &Post, name: &str, on: bool) -> R<()> {
        if !on {
            self.db
                .execute(
                    "DELETE FROM members WHERE id=? AND collection=?",
                    params![post.key(), name],
                )
                .map_err(err)?;
            return Ok(());
        }

        let tx = self.db.transaction().map_err(err)?;
        tx.execute(
            "INSERT OR IGNORE INTO posts(id,data,seen) VALUES(?,?,unixepoch())",
            params![post.key(), serde_json::to_string(post).map_err(err)?],
        )
        .map_err(err)?;
        tx.execute(
            "INSERT OR IGNORE INTO members(id,collection) VALUES(?,?)",
            params![post.key(), name],
        )
        .map_err(err)?;
        tx.commit().map_err(err)
    }
    pub fn posts(&self, view: &str, n: &str) -> R<Vec<Post>> {
        let mut stmt=self.db.prepare("SELECT data FROM posts WHERE CASE ?1 WHEN 'Favoritos' THEN favorite WHEN 'Galeria' THEN file IS NOT NULL OR favorite WHEN 'Coleções' THEN EXISTS(SELECT 1 FROM members m WHERE m.id=posts.id AND m.collection=?2) ELSE 0 END ORDER BY seen DESC,id").map_err(err)?;
        let rows = stmt
            .query_map(params![view, n], |r| r.get::<_, String>(0))
            .map_err(err)?;
        rows.map(|x| serde_json::from_str(&x.map_err(err)?).map_err(err))
            .collect()
    }
    pub fn save(&mut self, p: &Post, bytes: &[u8]) -> R<String> {
        let (ext, hash) = if let Some(video) = video_ext(bytes) {
            (video, None)
        } else {
            let img = decode(bytes)?;
            let format = image::guess_format(bytes).map_err(err)?;
            let ext = format
                .extensions_str()
                .first()
                .ok_or("Formato desconhecido")?;
            let small = img
                .resize_exact(9, 8, image::imageops::FilterType::Triangle)
                .to_luma8();
            let mut hash = 0u64;
            for y in 0..8 {
                for x in 0..8 {
                    hash = (hash << 1)
                        | u64::from(small.get_pixel(x, y)[0] > small.get_pixel(x + 1, y)[0]);
                }
            }
            (*ext, Some(format!("{hash:016x}")))
        };
        let digest = ring::digest::digest(&ring::digest::SHA256, bytes)
            .as_ref()
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>();
        let filename = format!("{digest}.{ext}");
        let data = serde_json::to_string(p).map_err(err)?;
        let dir = self.root.join("downloads");
        let path = dir.join(&filename);
        let tx = self
            .db
            .transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)
            .map_err(err)?;
        if !path.exists() {
            let mut tmp = tempfile::NamedTempFile::new_in(&dir).map_err(err)?;
            tmp.write_all(bytes).map_err(err)?;
            tmp.as_file().sync_all().map_err(err)?;
            tmp.persist_noclobber(path).map_err(err)?;
        }
        tx.execute(
            "INSERT INTO posts(id,data,seen,file,hash) VALUES(?,?,unixepoch(),?,?)
             ON CONFLICT(id) DO UPDATE SET file=excluded.file,hash=excluded.hash",
            params![p.key(), data, filename, hash],
        )
        .map_err(err)?;
        tx.commit().map_err(err)?;
        Ok(filename)
    }
    pub fn duplicates(&self) -> R<Vec<Post>> {
        let mut stmt = self
            .db
            .prepare("SELECT data,hash FROM posts WHERE file IS NOT NULL AND hash IS NOT NULL")
            .map_err(err)?;
        let rows = stmt
            .query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?)))
            .map_err(err)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(err)?;
        let hashes: Vec<_> = rows
            .iter()
            .map(|(_, h)| u64::from_str_radix(h, 16).map_err(err))
            .collect::<R<_>>()?;
        rows.iter()
            .enumerate()
            .filter(|(i, _)| {
                hashes
                    .iter()
                    .enumerate()
                    .any(|(j, h)| *i != j && (hashes[*i] ^ h).count_ones() <= 5)
            })
            .map(|(_, r)| serde_json::from_str(&r.0).map_err(err))
            .collect()
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn library_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let mut db = Library::open(dir.path()).unwrap();
        let p = Post {
            source: "Safebooru".into(),
            id: "77".into(),
            ..Default::default()
        };
        db.save_favorite(&p, true).unwrap();
        db.set("collection", "C", "").unwrap();
        db.assign(&p, "C", true).unwrap();
        for tab in ["Favoritos", "Coleções"] {
            assert_eq!(db.posts(tab, "C").unwrap().len(), 1);
        }
        let bytes = include_bytes!("../../assets/artfinder-icon.png");
        let f = db.save(&p, bytes).unwrap();
        assert_eq!(db.save(&p, bytes).unwrap(), f);
        assert!(db.save(&p, b"not an image").is_err());
        drop(db);
        let mut db = Library::open(dir.path()).unwrap();
        assert_eq!(db.posts("Galeria", "").unwrap().len(), 1);
        assert_eq!(db.details(&p.key()).unwrap(), (true, Some(f)));
        db.rename_collection("C", "Coleção nova").unwrap();
        assert!(db.collection(&p.key(), "Coleção nova").unwrap());
        assert_eq!(db.stats().unwrap().downloads, 1);
        db.rename_collection("Coleção nova", "C").unwrap();
        db.remove("collection", "C").unwrap();
        assert!(!db.collection(&p.key(), "C").unwrap());
    }
}
impl Library {
    pub fn import_categories(&mut self, cats: &serde_json::Value) -> R<usize> {
        let entries = cats.as_object().ok_or("Categorias inválidas")?;
        let tx = self.db.transaction().map_err(err)?;
        for (key, cat) in entries {
            let tags = cat["tags"].as_str().ok_or("Tags inválidas")?;
            tx.execute(
                "INSERT OR REPLACE INTO names VALUES('category_meta',?,?)",
                params![key, cat.to_string()],
            )
            .map_err(err)?;
            if cat["favorite"] == true {
                tx.execute(
                    "INSERT OR REPLACE INTO names VALUES('favorite_category',?,'1')",
                    [key],
                )
                .map_err(err)?;
            }
            tx.execute("INSERT INTO names(kind,name,value) VALUES('category',?,?) ON CONFLICT(kind,name) DO UPDATE SET value=excluded.value",params![key,tags]).map_err(err)?;
            for s in crate::sources::SOURCES {
                let kind = format!("tags/{s}");
                let q = &cat["source_tags"][s.to_lowercase()];
                let terms = if let Some(a) = q.as_array() {
                    a.iter()
                        .filter_map(|v| v.as_str())
                        .collect::<Vec<_>>()
                        .join(" ; ")
                } else {
                    q.as_str().unwrap_or("").into()
                };
                if !terms.is_empty() {
                    tx.execute("INSERT INTO names VALUES(?,?,?) ON CONFLICT(kind,name) DO UPDATE SET value=excluded.value",params![kind,key,terms]).map_err(err)?;
                }
            }
        }
        tx.commit().map_err(err)?;
        Ok(entries.len())
    }
    pub fn forget_file(&mut self, id: &str) -> R<()> {
        let tx = self
            .db
            .transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)
            .map_err(err)?;
        let file: Option<String> = tx
            .query_row("SELECT file FROM posts WHERE id=?", [id], |r| r.get(0))
            .map_err(err)?;
        tx.execute("UPDATE posts SET file=NULL,hash=NULL WHERE id=?", [id])
            .map_err(err)?;
        if let Some(f) = file {
            let used: bool = tx
                .query_row(
                    "SELECT EXISTS(SELECT 1 FROM posts WHERE file=?)",
                    [&f],
                    |r| r.get(0),
                )
                .map_err(err)?;
            if !used {
                let path = self.root.join("downloads").join(f);
                if path.is_file() {
                    std::fs::remove_file(path).map_err(err)?;
                }
            }
        }
        tx.commit().map_err(err)
    }
    pub fn counts(&self) -> R<(i64, i64)> {
        self.db
            .query_row(
                "SELECT coalesce(sum(favorite),0),count(file) FROM posts",
                [],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .map_err(err)
    }
}
impl Library {
    pub fn suggest(&self, prefix: &str) -> R<Vec<String>> {
        let mut stmt = self
            .db
            .prepare("SELECT json_extract(data,'$.tags') FROM posts WHERE favorite OR file IS NOT NULL OR EXISTS(SELECT 1 FROM members WHERE members.id=posts.id) ORDER BY seen DESC LIMIT 800")
            .map_err(err)?;
        let mut counts = std::collections::BTreeMap::new();
        for tags in stmt.query_map([], |r| r.get::<_, String>(0)).map_err(err)? {
            for t in tags.map_err(err)?.split_whitespace() {
                if t.len() < 100 && t.to_lowercase().starts_with(prefix) {
                    *counts.entry(t.to_owned()).or_insert(0) += 1
                }
            }
        }
        let mut ranked = counts.into_iter().collect::<Vec<_>>();
        ranked.sort_by_key(|(_, n)| std::cmp::Reverse(*n));
        Ok(ranked.into_iter().take(12).map(|(t, _)| t).collect())
    }
    pub fn reconcile(&mut self) -> R<usize> {
        let tx = self.db.transaction().map_err(err)?;
        let entries = {
            let mut stmt = tx
                .prepare("SELECT id,file FROM posts WHERE file IS NOT NULL")
                .map_err(err)?;
            let rows = stmt
                .query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?)))
                .map_err(err)?;
            rows.collect::<Result<Vec<_>, _>>().map_err(err)?
        };
        let mut count = 0;
        for (id, file) in entries {
            if !self.root.join("downloads").join(file).is_file() {
                count += tx
                    .execute("UPDATE posts SET file=NULL,hash=NULL WHERE id=?", [id])
                    .map_err(err)?;
            }
        }
        tx.commit().map_err(err)?;
        Ok(count)
    }
}
impl Library {
    pub fn downloaded_keys(&self) -> R<std::collections::HashSet<String>> {
        let mut stmt = self
            .db
            .prepare("SELECT id FROM posts WHERE file IS NOT NULL")
            .map_err(err)?;
        let rows = stmt.query_map([], |r| r.get(0)).map_err(err)?;
        rows.collect::<Result<_, _>>().map_err(err)
    }
    pub fn clear_downloads(&self) -> R<usize> {
        self.db
            .execute(
                "UPDATE posts SET file=NULL,hash=NULL WHERE file IS NOT NULL",
                [],
            )
            .map_err(err)
    }
}

pub struct LibraryStats {
    pub favorites: i64,
    pub downloads: i64,
    pub bytes: u64,
    pub sources: Vec<(String, i64)>,
    pub categories: Vec<(String, i64)>,
}

impl Library {
    pub fn rename_collection(&mut self, previous: &str, name: &str) -> R<()> {
        let name = name.trim();
        if name.is_empty() {
            return Err("Informe o nome da coleção".into());
        }
        if previous == name {
            return Ok(());
        }
        let tx = self.db.transaction().map_err(err)?;
        let count = tx
            .execute(
                "UPDATE names SET name=? WHERE kind='collection' AND name=?",
                params![name, previous],
            )
            .map_err(err)?;
        if count == 0 {
            return Err("Coleção indisponível".into());
        }
        tx.execute(
            "UPDATE members SET collection=? WHERE collection=?",
            params![name, previous],
        )
        .map_err(err)?;
        tx.commit().map_err(err)
    }

    pub fn stats(&self) -> R<LibraryStats> {
        let (favorites, downloads) = self.counts()?;
        let bytes = std::fs::read_dir(self.root.join("downloads"))
            .map_err(err)?
            .filter_map(Result::ok)
            .filter_map(|entry| entry.metadata().ok())
            .filter(|meta| meta.is_file())
            .map(|meta| meta.len())
            .sum();
        let rows = |sql: &str| -> R<Vec<(String, i64)>> {
            let mut stmt = self.db.prepare(sql).map_err(err)?;
            let rows = stmt
                .query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
                .map_err(err)?;
            rows.collect::<Result<_, _>>().map_err(err)
        };
        let sources=rows("SELECT json_extract(data,'$.source'),count(*) FROM posts WHERE file IS NOT NULL GROUP BY 1 ORDER BY 2 DESC,1")?;
        let categories=rows("SELECT coalesce(nullif(json_extract(data,'$.category'),''),'Sem categoria'),count(*) FROM posts WHERE file IS NOT NULL GROUP BY 1 ORDER BY 2 DESC,1")?;
        Ok(LibraryStats {
            favorites,
            downloads,
            bytes,
            sources,
            categories,
        })
    }
}

impl Library {
    pub fn set_category(&mut self, key: &str, tags: &str, meta: &serde_json::Value) -> R<()> {
        if key.is_empty() || key.contains([';', '\n']) || tags.trim().is_empty() {
            return Err("Informe o nome e as tags da categoria".into());
        }
        let tx = self.db.transaction().map_err(err)?;
        for (field, value) in [
            ("category", tags.trim().to_owned()),
            ("category_meta", meta.to_string()),
        ] {
            tx.execute("INSERT INTO names VALUES(?,?,?) ON CONFLICT(kind,name) DO UPDATE SET value=excluded.value",params![field,key,value]).map_err(err)?;
        }
        tx.commit().map_err(err)
    }
}
