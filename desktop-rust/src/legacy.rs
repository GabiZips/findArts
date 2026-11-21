use crate::{
    library::Library,
    sources::{Post, R, SOURCES},
};
use rusqlite::{Connection, OpenFlags};
use std::{collections::HashMap, path::Path};

fn source_name(s: &str) -> String {
    SOURCES
        .iter()
        .find(|n| n.eq_ignore_ascii_case(s))
        .copied()
        .unwrap_or(s)
        .to_owned()
}
impl Library {
    pub fn import_library(&mut self, dir: &Path) -> R<String> {
        let downloads = dir
            .join("downloads")
            .canonicalize()
            .map_err(|e| e.to_string())?;
        let conn = Connection::open_with_flags(
            downloads.join("artfinder.db"),
            OpenFlags::SQLITE_OPEN_READ_ONLY,
        )
        .map_err(|e| e.to_string())?;
        let schema = |table: &str| {
            conn.query_row(
                "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name=?)",
                [table],
                |r| r.get::<_, bool>(0),
            )
            .unwrap_or(false)
        };
        let mut metadata = HashMap::new();
        let mut favorites = HashMap::new();
        let mut files = 0;
        let mut skipped = 0;
        let db_err = |e: rusqlite::Error| e.to_string();
        if schema("posts") {
            let mut stmt=conn.prepare("SELECT source,post_id,url,preview_url,page_url,artist,tags,rating,width,height,score FROM posts WHERE COALESCE(is_ai,0)=0").map_err(db_err)?;
            for p in stmt
                .query_map([], |r| {
                    let text = |i| r.get::<_, Option<String>>(i).map(Option::unwrap_or_default);
                    Ok(Post {
                        source: source_name(&text(0)?),
                        id: text(1)?,
                        image: text(2)?,
                        thumb: text(3)?,
                        page: text(4)?,
                        artist: text(5)?,
                        tags: text(6)?,
                        rating: text(7)?,
                        width: r.get(8).unwrap_or(0),
                        height: r.get(9).unwrap_or(0),
                        score: r.get(10).unwrap_or(0),
                        ..Default::default()
                    })
                })
                .map_err(db_err)?
            {
                let mut p = p.map_err(db_err)?;
                if crate::sources::ai(&p.tags) {
                    continue;
                }
                if p.rating == "sfw" {
                    p.rating = "general".into()
                }
                metadata.insert(p.key(), p);
            }
        }
        if schema("favorites") {
            let mut stmt = conn
                .prepare("SELECT source,post_id,url,preview_url,page_url,artist FROM favorites")
                .map_err(db_err)?;
            for row in stmt
                .query_map([], |r| {
                    Ok(Post {
                        source: source_name(&r.get::<_, String>(0)?),
                        id: r.get(1)?,
                        image: r.get(2)?,
                        thumb: r.get(3)?,
                        page: r.get(4)?,
                        artist: r.get(5)?,
                        ..Default::default()
                    })
                })
                .map_err(db_err)?
            {
                let fallback = row.map_err(db_err)?;
                let p = metadata.get(&fallback.key()).cloned().unwrap_or(fallback);
                self.save_favorite(&p, true)?;
                favorites.insert(p.key(), p);
            }
        }
        for (table, kind, col) in [
            ("collections", "collection", "name"),
            ("blocked_artists", "artist", "artist"),
            ("blacklist", "post", "uid"),
        ] {
            if schema(table) {
                let mut stmt = conn
                    .prepare(&format!("SELECT {col} FROM {table}"))
                    .map_err(db_err)?;
                for row in stmt
                    .query_map([], |r| r.get::<_, String>(0))
                    .map_err(db_err)?
                {
                    let mut n = row.map_err(db_err)?;
                    if kind == "post" {
                        if let Some((s, id)) = n.split_once(':') {
                            n = format!("{}:{id}", source_name(s))
                        }
                    }
                    self.set(kind, &n, "")?
                }
            }
        }
        if schema("favorite_collections") && schema("collections") {
            let mut stmt=conn.prepare("SELECT f.source,f.post_id,c.name FROM favorite_collections f JOIN collections c ON c.id=f.collection_id").map_err(db_err)?;
            for row in stmt
                .query_map([], |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, String>(1)?,
                        r.get::<_, String>(2)?,
                    ))
                })
                .map_err(db_err)?
            {
                let (s, id, n) = row.map_err(db_err)?;
                let key = format!("{}:{id}", source_name(&s));
                if let Some(post) = favorites.get(&key) {
                    self.assign(post, &n, true)?;
                }
            }
        }
        if schema("downloads") {
            let mut stmt=conn.prepare("SELECT source_id,source,file_path,artist,tags,width,height,score FROM downloads").map_err(db_err)?;
            for row in stmt
                .query_map([], |r| {
                    let uid: String = r.get(0)?;
                    let p = Post {
                        id: uid
                            .split_once(':')
                            .map(|(_, id)| id)
                            .unwrap_or(&uid)
                            .to_owned(),
                        source: source_name(&r.get::<_, String>(1)?),
                        artist: r.get(3).unwrap_or_default(),
                        tags: r.get(4).unwrap_or_default(),
                        width: r.get(5).unwrap_or(0),
                        height: r.get(6).unwrap_or(0),
                        score: r.get(7).unwrap_or(0),
                        ..Default::default()
                    };
                    Ok((r.get::<_, String>(2)?, p))
                })
                .map_err(db_err)?
            {
                let (path, p) = row.map_err(db_err)?;
                if self.details(&p.key())?.1.is_some() {
                    continue;
                }
                let path = downloads.join(path).canonicalize();
                let Ok(path) = path else {
                    skipped += 1;
                    continue;
                };
                if !path.starts_with(&downloads)
                    || !path
                        .metadata()
                        .is_ok_and(|m| m.is_file() && m.len() <= 64 << 20)
                {
                    skipped += 1;
                    continue;
                }
                let post = metadata.get(&p.key()).unwrap_or(&p);
                let b = std::fs::read(path).map_err(|e| e.to_string())?;
                if self.save(post, &b).is_ok() {
                    files += 1
                } else {
                    skipped += 1
                }
            }
        }
        Ok(format!(
            "{} favoritos, {files} arquivos copiados, {skipped} arquivos indisponíveis",
            favorites.len()
        ))
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    #[ignore = "requer perfil Windows instalado"]
    fn installed_library_import() {
        let dir = tempfile::tempdir().unwrap();
        let mut db = Library::open(dir.path()).unwrap();
        let legacy =
            std::path::PathBuf::from(std::env::var_os("LOCALAPPDATA").unwrap()).join("ArtFinder");
        let result = db.import_library(&legacy).unwrap();
        println!("{result}");
        let (favorites, downloaded) = db.counts().unwrap();
        assert!(favorites + downloaded > 0);
    }
}
