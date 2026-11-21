#![cfg_attr(all(windows, not(test)), windows_subsystem = "windows")]
mod i18n;
mod interface;
mod legacy;
mod library;
mod pairing;
use i18n::tr;
mod sources;
use eframe::egui::{self, ColorImage, TextureHandle};
use library::Library;
use sources::{Post, R, SOURCES};
use std::{
    collections::{HashMap, HashSet},
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc::{channel, Receiver, Sender},
    },
    thread,
};
enum Event {
    Tags(String, String, R<String>),
    Imported(R<String>),
    Transfer(R<serde_json::Value>),
    Saved(String, R<String>),
    Page {
        epoch: u64,
        query: String,
        result: R<sources::Page>,
        finished: bool,
    },
    Thumb(String, R<ColorImage>),
    Open(u64, Post, R<(Option<ColorImage>, Vec<u8>)>),
}
fn stream_pages(
    mut cursor: Option<String>,
    mut remaining: Option<u32>,
    cancelled: &AtomicBool,
    mut fetch: impl FnMut(Option<&str>) -> R<sources::Page>,
    mut publish: impl FnMut(R<sources::Page>, bool) -> bool,
) -> bool {
    let mut cursors: HashSet<_> = cursor.iter().cloned().collect();
    while !cancelled.load(Ordering::Relaxed) {
        let result = fetch(cursor.as_deref()).map(|mut page| {
            page.next = page
                .next
                .filter(|next| !next.is_empty() && cursors.insert(next.clone()));
            page
        });
        if cancelled.load(Ordering::Relaxed) {
            return false;
        }
        cursor = result.as_ref().ok().and_then(|page| page.next.clone());
        remaining = remaining.map(|count| count.saturating_sub(1));
        let finished = cursor.is_none() || remaining == Some(0);
        if !publish(result, finished) {
            return false;
        }
        if finished {
            return true;
        }
    }
    false
}

fn bitmap(bytes: &[u8], size: u32) -> R<ColorImage> {
    let img = library::decode(bytes)?.thumbnail(size, size).to_rgba8();
    Ok(ColorImage::from_rgba_unmultiplied(
        [img.width() as usize, img.height() as usize],
        img.as_raw(),
    ))
}
fn animate(bytes: &[u8], ctx: egui::Context) -> Option<Receiver<ColorImage>> {
    use image::AnimationDecoder;
    if !bytes.starts_with(b"GIF87a") && !bytes.starts_with(b"GIF89a") {
        return None;
    }
    let bytes = bytes.to_vec();
    let (tx, rx) = std::sync::mpsc::sync_channel(1);
    thread::spawn(move || loop {
        let Ok(decoder) = image::codecs::gif::GifDecoder::new(std::io::Cursor::new(&bytes)) else {
            return;
        };
        let mut count = 0;
        for frame in decoder.into_frames() {
            let Ok(frame) = frame else { return };
            let (num, den) = frame.delay().numer_denom_ms();
            let im = image::DynamicImage::ImageRgba8(frame.into_buffer())
                .thumbnail(1200, 1200)
                .to_rgba8();
            let bitmap = ColorImage::from_rgba_unmultiplied(
                [im.width() as usize, im.height() as usize],
                im.as_raw(),
            );
            if tx.send(bitmap).is_err() {
                return;
            }
            ctx.request_repaint();
            count += 1;
            std::thread::sleep(std::time::Duration::from_millis(u64::from(
                (num / den.max(1)).clamp(20, 60000),
            )));
        }
        if count < 2 {
            return;
        }
    });
    Some(rx)
}
struct Viewer {
    frames: Option<Receiver<ColorImage>>,
    post: Post,
    texture: Option<TextureHandle>,
    bytes: Vec<u8>,
    zoom: f32,
}
struct App {
    db: Library,
    view: String,
    source: String,
    query: String,
    results: Vec<Post>,
    status: Vec<String>,
    pending: usize,
    search_epoch: u64,
    cancelled: std::sync::Arc<std::sync::atomic::AtomicBool>,
    searched: bool,
    search_cache: Vec<Post>,
    search_cursors: HashMap<String, String>,
    search_categories: HashMap<String, String>,
    next: HashMap<String, String>,
    selection: HashSet<String>,
    pages: u32,
    all_pages: bool,
    search_pages_loaded: usize,
    search_result_keys: HashSet<String>,
    grid_size: interface::GridSize,
    rx: Receiver<Event>,
    tx: Sender<Event>,
    textures: HashMap<String, (TextureHandle, u64)>,
    queued_thumbs: HashSet<String>,
    failed_thumbs: HashSet<String>,
    downloading: HashSet<String>,
    background_tx: Sender<Event>,
    background_rx: Receiver<Event>,
    viewer_order: Vec<Post>,
    opening: Option<u64>,
    viewer_epoch: u64,
    viewer: Option<Viewer>,
    collection: String,
    collection_edit: String,
    category_filter: String,
    category_label: String,
    category_group: String,
    category_icon: String,
    category_color: String,
    kind: String,
    name: String,
    value: String,
    cred: String,
    secret: String,
    safe: bool,
    protect: bool,
    gallery_modes: [bool; 2],
    remove_file: Option<String>,
    revealed: HashSet<String>,
    classes: [bool; 3],
    formats: [bool; 4],
    days: i64,
    min_score: i64,
    min_width: u64,
    min_height: u64,
    filter: String,
    sort: String,
    hide_downloaded: bool,
    confirm_clear: bool,
    query_categories: HashMap<String, String>,
    pair_code: String,
    pair_keys: bool,
    transfer: Option<serde_json::Value>,
    export_path: String,
    orientation: String,
    english: bool,
    palette: HashMap<String, Vec<[u8; 3]>>,
    color: [u8; 3],
    color_filter: bool,
    tolerance: u32,
}
impl App {
    fn new(db: Library) -> Self {
        let english = db
            .names("preferences")
            .unwrap_or_default()
            .into_iter()
            .any(|(k, v)| k == "language" && v == "en");
        let (tx, rx) = channel();
        let (background_tx, background_rx) = channel();
        Self {
            db,
            view: "Busca".into(),
            source: "Todas".into(),
            query: String::new(),
            results: vec![],
            status: vec![],
            pending: 0,
            search_epoch: 0,
            cancelled: Default::default(),
            searched: false,
            search_cache: Vec::new(),
            search_cursors: HashMap::new(),
            search_categories: HashMap::new(),
            next: HashMap::new(),
            selection: SOURCES.iter().map(|v| v.to_string()).collect(),
            pages: 1,
            all_pages: false,
            search_pages_loaded: 0,
            search_result_keys: HashSet::new(),
            grid_size: interface::GridSize::Large,
            rx,
            tx,
            textures: HashMap::new(),
            queued_thumbs: HashSet::new(),
            failed_thumbs: HashSet::new(),
            downloading: HashSet::new(),
            background_tx,
            background_rx,
            viewer_order: Vec::new(),
            opening: None,
            viewer_epoch: 0,
            viewer: None,
            collection: String::new(),
            collection_edit: String::new(),
            category_filter: String::new(),
            category_label: String::new(),
            category_group: String::new(),
            category_icon: String::new(),
            category_color: String::new(),
            kind: "category".into(),
            name: String::new(),
            value: String::new(),
            cred: sources::KEYS[0].into(),
            secret: String::new(),
            safe: true,
            protect: true,
            gallery_modes: [true, true],
            remove_file: None,
            revealed: HashSet::new(),
            classes: [true; 3],
            formats: [true; 4],
            days: 0,
            min_score: 0,
            min_width: 0,
            min_height: 0,
            filter: String::new(),
            sort: "Maior pontuação".into(),
            hide_downloaded: true,
            confirm_clear: false,
            query_categories: HashMap::new(),
            pair_code: String::new(),
            pair_keys: false,
            transfer: None,
            export_path: String::new(),
            orientation: "Todas".into(),
            english,
            palette: HashMap::new(),
            color: [100, 130, 190],
            color_filter: false,
            tolerance: 90,
        }
    }
    fn reset(&mut self) {
        (self.tx, self.rx) = channel();
        self.cancel_search();
        self.opening = None;
        self.remove_file = None;
        self.queued_thumbs.clear();
        self.failed_thumbs.clear();
        self.results.clear();
        self.search_result_keys.clear();
        self.textures.clear();
        self.palette.clear();
        self.query_categories.clear();
        self.status.clear();
        self.next.clear();
        self.viewer = None
    }
    fn message<T>(&mut self, r: R<T>) {
        if let Err(e) = r {
            self.status.push(e)
        }
    }
    fn cancel_search(&mut self) {
        self.cancelled
            .store(true, std::sync::atomic::Ordering::Relaxed);
        self.search_epoch = self.search_epoch.wrapping_add(1);
        self.pending = 0;
    }
    fn hidden(&self, p: &Post) -> bool {
        self.protect && interface::classification(p) > 0 && !self.revealed.contains(&p.key())
    }
    fn start(&mut self, ctx: &egui::Context, more: bool) {
        if !more && self.query.trim().is_empty() {
            self.status = vec!["Informe uma tag ou categoria.".into()];
            return;
        }
        let cursors = self.next.clone();
        if !more {
            self.reset();
            self.search_pages_loaded = 0;
        }
        self.searched = true;
        self.cancelled = Default::default();
        let categories = self.db.names("category").unwrap_or_default();
        for s in SOURCES {
            let mut work = Vec::new();
            if more {
                for (key, cursor) in &cursors {
                    if let Some((src, query)) = key.split_once('|') {
                        if src == s {
                            work.push((query.to_owned(), Some(cursor.clone())))
                        }
                    }
                }
            } else {
                if self.source != "Todas"
                    && self.source != s
                    && !(self.source == "Selecionadas" && self.selection.contains(s))
                {
                    continue;
                }
                let mapped = self.db.names(&format!("tags/{s}")).unwrap_or_default();
                let mut unique = HashSet::new();
                for term in self
                    .query
                    .split([';', '\n'])
                    .map(str::trim)
                    .filter(|q| !q.is_empty())
                {
                    let resolved = mapped
                        .iter()
                        .chain(categories.iter())
                        .find(|(name, _)| name == term)
                        .map(|(_, q)| q.as_str())
                        .unwrap_or(term);
                    for q in resolved
                        .split([';', '\n'])
                        .map(str::trim)
                        .filter(|q| !q.is_empty())
                    {
                        if unique.insert(q.to_owned()) {
                            self.query_categories
                                .insert(format!("{s}|{q}"), term.to_owned());
                            work.push((q.to_owned(), None))
                        }
                    }
                }
            }
            if work.is_empty() {
                continue;
            }
            self.pending += work.len();
            let tx = self.tx.clone();
            let ui = ctx.clone();
            let limit = (!self.all_pages).then_some(self.pages.max(1));
            let cancelled = self.cancelled.clone();
            let epoch = self.search_epoch;
            thread::spawn(move || {
                for (query, cursor) in work {
                    let key = format!("{s}|{query}");
                    let completed = stream_pages(
                        cursor,
                        limit,
                        &cancelled,
                        |cursor| sources::search(s, &query, cursor),
                        |result, finished| {
                            let delivered = tx
                                .send(Event::Page {
                                    epoch,
                                    query: key.clone(),
                                    result,
                                    finished,
                                })
                                .is_ok();
                            if delivered {
                                ui.request_repaint();
                            }
                            delivered
                        },
                    );
                    if !completed {
                        return;
                    }
                }
            });
        }
    }
    fn thumbs(&mut self, ctx: &egui::Context, posts: &[Post]) {
        for post in posts {
            if let Some((_, last_used)) = self.textures.get_mut(&post.key()) {
                *last_used = ctx.cumulative_pass_nr();
            }
        }
        self.queue_thumbs(ctx, posts, false);
    }
    fn analyze_colors(&mut self, ctx: &egui::Context, posts: &[Post]) {
        self.queue_thumbs(ctx, posts, true);
    }
    fn queue_thumbs(&mut self, ctx: &egui::Context, posts: &[Post], colors_only: bool) {
        let available = 8usize.saturating_sub(self.queued_thumbs.len());
        if available == 0 {
            return;
        }
        for p in posts
            .iter()
            .filter(|p| !self.hidden(p))
            .filter(|p| {
                let id = p.key();
                !self.textures.contains_key(&id)
                    && (!colors_only || !self.palette.contains_key(&id))
                    && !self.queued_thumbs.contains(&id)
                    && !self.failed_thumbs.contains(&id)
            })
            .take(available)
            .cloned()
            .collect::<Vec<_>>()
        {
            let key = p.key();
            self.queued_thumbs.insert(key.clone());
            let path = self.local(&p);
            let tx = self.tx.clone();
            let ui = ctx.clone();
            thread::spawn(move || {
                let data = thumbnail(&p, path);
                let _ = tx.send(Event::Thumb(key, data));
                ui.request_repaint();
            });
        }
    }
    fn save_favorite(&mut self, p: &Post, on: bool) {
        let result = self.db.save_favorite(p, on);
        if result.is_ok() && !on && self.view == "Favoritos" {
            self.results.retain(|item| item.key() != p.key());
        }
        self.message(result);
    }
    fn download(&mut self, ctx: &egui::Context, p: Post) {
        if self.hidden(&p) || !self.downloading.insert(p.key()) {
            return;
        }
        let tx = self.background_tx.clone();
        let ctx = ctx.clone();
        let root = self.db.root.clone();
        thread::spawn(move || {
            let r = Library::open(&root)
                .and_then(|mut db| sources::media(&p, false).and_then(|bytes| db.save(&p, &bytes)));
            let _ = tx.send(Event::Saved(p.key(), r));
            ctx.request_repaint();
        });
    }
    fn local(&self, p: &Post) -> Option<PathBuf> {
        self.db
            .details(&p.key())
            .ok()?
            .1
            .map(|f| self.db.root.join("downloads").join(f))
    }
    fn open(&mut self, ctx: &egui::Context, p: Post) {
        if self.hidden(&p) {
            return;
        }
        self.viewer_epoch = self.viewer_epoch.wrapping_add(1);
        let request = self.viewer_epoch;
        self.opening = Some(request);
        let path = self.local(&p);
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        thread::spawn(move || {
            let result = read_media(&p, path).and_then(|b| {
                Ok((
                    if library::video_ext(&b).is_some() {
                        None
                    } else {
                        Some(bitmap(&b, 2400)?)
                    },
                    b,
                ))
            });
            let _ = tx.send(Event::Open(request, p, result));
            ctx.request_repaint();
        });
    }
    fn load(&mut self, _ctx: &egui::Context) {
        self.reset();
        if matches!(
            self.view.as_str(),
            "Busca" | "Configurações" | "Estatísticas"
        ) {
            return;
        }
        let res = if self.view == "Duplicatas" {
            self.db.duplicates()
        } else {
            self.db.posts(&self.view, &self.collection)
        };
        match res {
            Ok(ps) => self.results = ps,
            Err(e) => self.status.push(e),
        }
    }
    fn visible(&self) -> Vec<Post> {
        let downloaded = if self.hide_downloaded && self.view == "Busca" {
            self.db.downloaded_keys().unwrap_or_default()
        } else {
            HashSet::new()
        };
        let blocked = self.db.names("post").unwrap_or_default();
        let tags = self.db.names("blacklist").unwrap_or_default();
        let artists = self.db.names("artist").unwrap_or_default();
        let cutoff = chrono::Utc::now().timestamp() - self.days * 86400;
        let filter = self.filter.to_lowercase();
        let mut posts = self
            .results
            .iter()
            .filter(|p| {
                let class = interface::classification(p);
                (!self.safe || class == 0)
                    && self.classes[class]
                    && (self.days == 0 || p.date >= cutoff)
                    && (self.view != "Galeria" && self.formats.iter().all(|on| *on) || {
                        let (favorite, file) = self.db.details(&p.key()).unwrap_or_default();
                        let gallery_match = self.view != "Galeria"
                            || if file.is_some() {
                                self.gallery_modes[0]
                            } else {
                                favorite && self.gallery_modes[1]
                            };
                        gallery_match && self.formats[interface::format_index(p, file.as_deref())]
                    })
                    && !downloaded.contains(&p.key())
                    && !blocked.iter().any(|(k, _)| k == &p.key())
                    && match self.orientation.as_str() {
                        "Paisagem" => p.width > p.height,
                        "Retrato" => p.height > p.width,
                        "Quadrada" => p.width > 0 && p.width == p.height,
                        _ => true,
                    }
                    && p.score >= self.min_score
                    && p.width >= self.min_width
                    && p.height >= self.min_height
                    && (self.filter.is_empty()
                        || format!("{} {} {}", p.tags, p.artist, p.source)
                            .to_lowercase()
                            .contains(&filter))
                    && !tags
                        .iter()
                        .any(|(t, _)| p.tags.split_whitespace().any(|w| w.eq_ignore_ascii_case(t)))
                    && !artists
                        .iter()
                        .any(|(a, _)| a.eq_ignore_ascii_case(&p.artist))
            })
            .cloned()
            .collect::<Vec<_>>();
        match self.sort.as_str() {
            "Maior pontuação" => posts.sort_by_key(|p| std::cmp::Reverse(p.score)),
            "Menor pontuação" => posts.sort_by_key(|p| p.score),
            "Em alta" => posts.sort_by_key(|p| {
                std::cmp::Reverse((p.score, p.date, p.id.parse::<i64>().unwrap_or(0)))
            }),
            "Fonte" => posts.sort_by(|a, b| a.source.cmp(&b.source)),
            "Categoria" => posts.sort_by(|a, b| a.category.cmp(&b.category)),
            _ => {}
        }
        posts
    }
    fn events(&mut self, ctx: &egui::Context) {
        while let Ok(event) = self
            .background_rx
            .try_recv()
            .or_else(|_| self.rx.try_recv())
        {
            match event {
                Event::Imported(r) => self.status = vec![r.unwrap_or_else(|e| e)],
                Event::Tags(name, s, r) => match r {
                    Ok(q) => {
                        let result = self.db.set(&format!("tags/{s}"), &name, &q);
                        self.message(result);
                        self.status.push(format!("{name} · {s} · {q}"));
                    }
                    Err(e) => self.status.push(format!("{s} · {e}")),
                },
                Event::Transfer(r) => match r {
                    Ok(payload) => self.transfer = Some(payload),
                    Err(e) => self.status.push(e),
                },
                Event::Saved(id, r) => {
                    self.downloading.remove(&id);
                    match r {
                        Ok(_) => self.status.push(tr("Original baixado").into()),
                        Err(e) => self.status.push(format!("{id} · {e}")),
                    }
                }
                Event::Page {
                    epoch,
                    query,
                    result,
                    finished,
                } => {
                    if epoch != self.search_epoch {
                        continue;
                    }
                    if finished {
                        self.pending = self.pending.saturating_sub(1);
                    }
                    let source = query
                        .split_once('|')
                        .map_or(query.as_str(), |(source, _)| source);
                    match result {
                        Ok(page) => {
                            self.search_pages_loaded += 1;
                            if let Some(next) = page.next {
                                self.next.insert(query.clone(), next);
                            } else {
                                self.next.remove(&query);
                            }
                            let category = self.query_categories.get(&query);
                            for mut post in page.posts {
                                if self.search_result_keys.insert(post.key()) {
                                    post.category = category.cloned().unwrap_or_default();
                                    self.results.push(post);
                                }
                            }
                        }
                        Err(error) => self.status.push(format!("{source} · {error}")),
                    }
                }
                Event::Thumb(id, Ok(img)) => {
                    self.queued_thumbs.remove(&id);
                    let mut bins = HashMap::new();
                    for pix in img.pixels.iter().step_by(8).filter(|p| p.a() > 128) {
                        *bins
                            .entry([pix.r() / 32, pix.g() / 32, pix.b() / 32])
                            .or_insert(0usize) += 1
                    }
                    let mut ranked = bins.into_iter().collect::<Vec<_>>();
                    ranked.sort_by_key(|p| std::cmp::Reverse(p.1));
                    self.palette.insert(
                        id.clone(),
                        ranked
                            .into_iter()
                            .take(5)
                            .map(|(c, _)| c.map(|v| v * 32 + 16))
                            .collect(),
                    );
                    if self.textures.len() >= 96 {
                        let oldest = self
                            .textures
                            .iter()
                            .min_by_key(|(_, (_, last_used))| *last_used)
                            .map(|(key, _)| key.clone());
                        if let Some(oldest) = oldest {
                            self.textures.remove(&oldest);
                        }
                    }
                    let texture = ctx.load_texture(id.clone(), img, Default::default());
                    self.textures
                        .insert(id, (texture, ctx.cumulative_pass_nr()));
                }
                Event::Thumb(id, Err(_)) => {
                    self.queued_thumbs.remove(&id);
                    self.failed_thumbs.insert(id);
                }
                Event::Open(request, post, Ok((img, bytes))) => {
                    if self.opening != Some(request) {
                        continue;
                    }
                    self.opening = None;
                    if self.hidden(&post) {
                        continue;
                    }
                    self.viewer = Some(Viewer {
                        frames: animate(&bytes, ctx.clone()),
                        texture: img
                            .map(|img| ctx.load_texture("Original", img, Default::default())),
                        post,
                        bytes,
                        zoom: 1.0,
                    })
                }
                Event::Open(request, _, Err(e)) => {
                    if self.opening == Some(request) {
                        self.opening = None;
                        self.status.push(e);
                    }
                }
            }
        }
    }
    fn settings(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.label(tr("Idioma"));
            if ui
                .selectable_value(&mut self.english, false, "Português")
                .changed()
                || ui
                    .selectable_value(&mut self.english, true, "English")
                    .changed()
            {
                self.message(self.db.set(
                    "preferences",
                    "language",
                    if self.english { "en" } else { "pt" },
                ));
                ui.ctx().request_repaint();
            }
        });
        if let Ok((fav, files)) = self.db.counts() {
            ui.label(format!(
                "{fav} {} · {files} downloads",
                tr("Favoritos").to_lowercase()
            ));
        }
        ui.collapsing(tr("Importar categorias do ArtFinder instalado"), |ui| {
            if ui
                .button("Importar biblioteca, favoritos e downloads do Windows")
                .clicked()
            {
                let root = self.db.root.clone();
                let tx = self.tx.clone();
                let ctx = ui.ctx().clone();
                thread::spawn(move || {
                    let r = (|| {
                        let dir = PathBuf::from(
                            std::env::var_os("LOCALAPPDATA").ok_or("Perfil indisponível")?,
                        )
                        .join("ArtFinder");
                        Library::open(&root)?.import_library(&dir)
                    })();
                    let _ = tx.send(Event::Imported(r));
                    ctx.request_repaint()
                });
            }
            if ui.button(tr("Importar categorias do Windows")).clicked() {
                let r = (|| {
                    let p = PathBuf::from(
                        std::env::var_os("LOCALAPPDATA").ok_or("Perfil indisponível")?,
                    )
                    .join("ArtFinder/user_categories.json");
                    let data: serde_json::Value =
                        serde_json::from_reader(std::fs::File::open(p).map_err(|e| e.to_string())?)
                            .map_err(|_| "JSON inválido")?;
                    self.db.import_categories(&data["categories"])
                })();
                match r {
                    Ok(n) => self.status = vec![format!("{n} categorias importadas")],
                    Err(e) => self.status.push(e),
                }
            }
        });
        ui.collapsing(tr("Parear com outro dispositivo"), |ui| {
            ui.checkbox(
                &mut self.pair_keys,
                tr("Incluir credenciais na transferência"),
            );
            if ui.button(tr("Gerar código (5 minutos)")).clicked() {
                match pairing::export(&self.db, self.pair_keys) {
                    Ok(c) => self.pair_code = c,
                    Err(e) => self.status.push(e),
                }
            }
            ui.add(
                egui::TextEdit::multiline(&mut self.pair_code)
                    .hint_text(tr("Código de pareamento")),
            );
            if !self.pair_code.is_empty() && ui.button(tr("Copiar código")).clicked() {
                ui.ctx().copy_text(self.pair_code.clone());
            }
            if ui.button(tr("Receber configuração")).clicked() {
                let c = self.pair_code.clone();
                let tx = self.tx.clone();
                let ctx = ui.ctx().clone();
                thread::spawn(move || {
                    let _ = tx.send(Event::Transfer(pairing::fetch(&c)));
                    ctx.request_repaint()
                });
            }
            if let Some(payload) = &self.transfer {
                let nc = payload["categories"].as_object().map_or(0, |v| v.len());
                let nk = payload["credentials"].as_object().map_or(0, |v| v.len());
                ui.label(format!("{nc} categorias e {nk} credenciais disponíveis"));
                if ui.button(tr("Aplicar configuração recebida")).clicked() {
                    let r = (|| {
                        if nc > 0 {
                            self.db.import_categories(&payload["categories"])?;
                        }
                        if self.pair_keys {
                            for k in sources::KEYS {
                                if let Some(v) = payload["credentials"][k].as_str() {
                                    sources::vault(k)?
                                        .set_password(v)
                                        .map_err(|_| "Falha ao gravar credencial")?
                                }
                            }
                        }
                        Ok(())
                    })();
                    if r.is_ok() {
                        self.transfer = None;
                        self.pair_code.clear();
                        self.status = vec!["Configuração importada".into()]
                    }
                    self.message(r)
                }
            }
        });
        ui.heading(tr("Categorias e biblioteca"));
        egui::ComboBox::from_id_salt("kind")
            .selected_text(tr(kind_label(&self.kind)))
            .show_ui(ui, |ui| {
                for k in ["category", "collection", "blacklist", "artist", "post"] {
                    ui.selectable_value(&mut self.kind, k.into(), tr(kind_label(k)));
                }
                for s in SOURCES {
                    ui.selectable_value(
                        &mut self.kind,
                        format!("tags/{s}"),
                        format!("Tags por categoria · {s}"),
                    );
                }
            });
        ui.horizontal(|ui| {
            ui.label(tr("Nome"));
            ui.text_edit_singleline(&mut self.name);
        });
        if self.kind == "category" || self.kind.starts_with("tags/") {
            ui.horizontal(|ui| {
                ui.label(tr("Tags da busca"));
                ui.text_edit_singleline(&mut self.value);
            });
        }
        if self.kind == "category" {
            ui.horizontal_wrapped(|ui| {
                for (label, value) in [
                    ("Nome exibido", &mut self.category_label),
                    ("Grupo", &mut self.category_group),
                    ("Ícone", &mut self.category_icon),
                    ("Cor", &mut self.category_color),
                ] {
                    ui.add(
                        egui::TextEdit::singleline(value)
                            .hint_text(tr(label))
                            .desired_width(125.),
                    );
                }
            });
        }
        if ui.button(tr("Salvar")).clicked() {
            let result = if self.kind == "category" {
                let key = self.name.trim();
                let label = if self.category_label.trim().is_empty() {
                    key
                } else {
                    self.category_label.trim()
                };
                let meta = serde_json::json!({"label":label,"group":self.category_group.trim(),"emoji":self.category_icon.trim(),"color":self.category_color.trim()});
                self.db.set_category(key, &self.value, &meta)
            } else {
                self.db.set(&self.kind, &self.name, &self.value)
            };
            self.message(result);
        }
        for (n, v) in self.db.names(&self.kind).unwrap_or_default() {
            ui.horizontal(|ui| {
                ui.label(&n);
                ui.label(&v);
                if self.kind == "category"
                    && ui
                        .small_button("★")
                        .on_hover_text(tr("Favoritar categoria"))
                        .clicked()
                {
                    if self
                        .db
                        .names("favorite_category")
                        .unwrap_or_default()
                        .iter()
                        .any(|(a, _)| a == &n)
                    {
                        let r = self.db.remove("favorite_category", &n);
                        self.message(r)
                    } else {
                        self.message(self.db.set("favorite_category", &n, "1"));
                    }
                }
                if self.kind == "category" && ui.small_button("Mapear tags").clicked() {
                    for s in ["Pixiv", "e621"] {
                        let ctx = ui.ctx().clone();
                        let tx = self.tx.clone();
                        let k = n.clone();
                        let q = v.clone();
                        thread::spawn(move || {
                            let _ = tx.send(Event::Tags(k, s.into(), sources::map_tags(s, &q)));
                            ctx.request_repaint()
                        });
                    }
                }
                if self.kind == "category" {
                    let mut position = self
                        .db
                        .names("order")
                        .unwrap_or_default()
                        .iter()
                        .find(|(k, _)| k == &n)
                        .and_then(|(_, v)| v.parse::<usize>().ok())
                        .unwrap_or(100);
                    if ui
                        .add(egui::DragValue::new(&mut position).prefix("Ordem "))
                        .changed()
                    {
                        self.message(self.db.set("order", &n, &position.to_string()))
                    }
                }
                if ui.small_button(tr("Editar")).clicked() {
                    self.name = n.clone();
                    self.value = v;
                    if self.kind == "category" {
                        let meta = self
                            .db
                            .names("category_meta")
                            .ok()
                            .and_then(|items| items.into_iter().find(|(k, _)| k == &n))
                            .and_then(|(_, v)| serde_json::from_str::<serde_json::Value>(&v).ok())
                            .unwrap_or_default();
                        self.category_label = meta["label"].as_str().unwrap_or(&n).into();
                        self.category_group = meta["group"].as_str().unwrap_or("").into();
                        self.category_icon = meta["emoji"].as_str().unwrap_or("").into();
                        self.category_color = meta["color"].as_str().unwrap_or("").into();
                    }
                }
                if ui.small_button(tr("Remover")).clicked() {
                    let r = self.db.remove(&self.kind, &n);
                    self.message(r)
                }
            });
        }
        ui.separator();
        ui.horizontal(|ui| {
            for (label, path) in [
                ("Abrir downloads", self.db.root.join("downloads")),
                ("Abrir pasta de dados", self.db.root.clone()),
            ] {
                if ui.button(label).clicked() {
                    self.message(
                        std::process::Command::new(if cfg!(windows) {
                            "explorer.exe"
                        } else {
                            "xdg-open"
                        })
                        .arg(path)
                        .spawn()
                        .map_err(|e| e.to_string()),
                    );
                }
            }
        });
        if ui.button("Limpar registros de downloads").clicked() {
            self.confirm_clear = true
        }
        if self.confirm_clear {
            ui.label("Limpar o índice de downloads? Os arquivos continuam no disco.");
            ui.horizontal(|ui| {
                if ui.button("Confirmar limpeza").clicked() {
                    self.message(self.db.clear_downloads());
                    self.confirm_clear = false
                }
                if ui.button("Cancelar").clicked() {
                    self.confirm_clear = false
                }
            });
        }
        if ui.button(tr("Restaurar índice da galeria")).clicked() {
            match self.db.reconcile() {
                Ok(n) => self.status = vec![format!("{n} registros atualizados")],
                Err(e) => self.status.push(e),
            }
        }
        ui.heading(tr("Credenciais"));
        if ui
            .button(tr(
                "Usar credenciais do arquivo .env do ArtFinder nesta sessão",
            ))
            .clicked()
        {
            let path = std::env::var_os("LOCALAPPDATA")
                .map(PathBuf::from)
                .unwrap_or_default()
                .join("ArtFinder/.env");
            match std::fs::read_to_string(path) {
                Ok(raw) => {
                    let mut n = 0;
                    for line in raw.lines() {
                        if let Some((k, v)) = line.split_once('=') {
                            let k = k.trim();
                            let v = v.trim().trim_matches('"').trim_matches('\'');
                            if sources::KEYS.contains(&k)
                                && !v.is_empty()
                                && sources::credential(k).is_none()
                            {
                                sources::session_set(k, v);
                                n += 1
                            }
                        }
                    }
                    self.status = vec![format!("{n} campos carregados para esta sessão")]
                }
                Err(_) => self.status = vec!["Arquivo de configuração indisponível".into()],
            }
        }
        egui::ComboBox::from_id_salt("key")
            .selected_text(&self.cred)
            .show_ui(ui, |ui| {
                for k in sources::KEYS {
                    if ui.selectable_value(&mut self.cred, k.into(), k).changed() {
                        self.secret.clear()
                    }
                }
            });
        ui.add(egui::TextEdit::singleline(&mut self.secret).password(true));
        if ui.button(tr("Remover do cofre")).clicked() {
            let r = sources::vault(&self.cred).and_then(|v| match v.delete_credential() {
                Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
                Err(_) => Err("Falha ao remover do cofre".into()),
            });
            self.message(r)
        }
        if ui
            .add_enabled(
                !self.secret.is_empty(),
                egui::Button::new(tr("Salvar no cofre do sistema")),
            )
            .clicked()
        {
            let r = sources::vault(&self.cred).and_then(|v| {
                v.set_password(&self.secret)
                    .map_err(|_| "Falha ao salvar credencial".into())
            });
            if r.is_ok() {
                self.secret.clear();
                self.status = vec!["Credencial salva".into()]
            }
            self.message(r)
        }
    }
}
fn kind_label(k: &str) -> &str {
    match k {
        "category" => "Categorias",
        "collection" => "Coleções",
        "blacklist" => "Tags bloqueadas",
        "post" => "Publicações bloqueadas",
        "artist" => "Artistas bloqueados",
        _ => k,
    }
}
fn thumbnail(post: &Post, path: Option<PathBuf>) -> R<ColorImage> {
    if let Some(image) = path
        .and_then(|file| std::fs::read(file).ok())
        .and_then(|bytes| bitmap(&bytes, 640).ok())
    {
        return Ok(image);
    }
    if let Ok(image) = sources::sample(post).and_then(|bytes| bitmap(&bytes, 640)) {
        return Ok(image);
    }
    sources::media(post, true).and_then(|bytes| bitmap(&bytes, 640))
}

fn read_media(p: &Post, path: Option<PathBuf>) -> R<Vec<u8>> {
    if let Some(f) = path {
        if f.is_file() {
            return std::fs::read(f).map_err(|e| e.to_string());
        }
    }
    sources::media(p, false)
}
impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _: &mut eframe::Frame) {
        i18n::set(self.english);
        self.events(ctx);
        self.shell(ctx);
        self.screen(ctx);
        if let Some(mut v) = self.viewer.take() {
            if let Some(frame) = v.frames.as_ref().and_then(|rx| rx.try_recv().ok()) {
                if let Some(t) = v.texture.as_mut() {
                    t.set(frame, Default::default())
                }
            }
            let mut open = !ctx.input(|i| i.key_pressed(egui::Key::Escape));
            let mut next = 0isize;
            let mut hide = false;
            if !ctx.wants_keyboard_input() {
                if ctx.input(|i| i.key_pressed(egui::Key::ArrowLeft)) {
                    next = -1;
                }
                if ctx.input(|i| i.key_pressed(egui::Key::ArrowRight)) {
                    next = 1;
                }
            }
            egui::Window::new(tr("Visualizador"))
                .open(&mut open)
                .resizable(true)
                .default_width(720.)
                .show(ctx, |ui| {
                    ui.horizontal_wrapped(|ui| {
                        if ui.button(tr("← Anterior")).clicked() {
                            next = -1;
                        }
                        if ui.button(tr("Próxima →")).clicked() {
                            next = 1;
                        }
                        if self.protect
                            && interface::classification(&v.post) > 0
                            && ui.button(tr("Ocultar imagem")).clicked()
                        {
                            hide = true;
                        }
                    });
                    ui.label(format!(
                        "{} · {} · {} × {}",
                        v.post.source, v.post.artist, v.post.width, v.post.height
                    ));
                    ui.horizontal(|ui| {
                        ui.add(egui::Slider::new(&mut v.zoom, 0.2..=4.).text(tr("Zoom")));
                        if ui.button("100%").clicked() {
                            v.zoom = 1.;
                        }
                    });
                    egui::ScrollArea::both()
                        .max_height(ctx.screen_rect().height() * 0.50)
                        .show(ui, |ui| {
                            let Some(texture) = &v.texture else {
                                ui.label(tr("Vídeo · salve o original para reproduzir"));
                                return;
                            };
                            let size = texture.size_vec2();
                            let scale = (650. / size.x).min(400. / size.y).min(1.) * v.zoom;
                            ui.image((texture.id(), size * scale));
                        });
                    if url::Url::parse(&v.post.page).is_ok_and(|u| u.scheme() == "https") {
                        ui.hyperlink_to(tr("Publicação original"), &v.post.page);
                    }
                    let id = v.post.key();
                    if let Ok((mut fav, file)) = self.db.details(&id) {
                        ui.horizontal_wrapped(|ui| {
                            if ui.checkbox(&mut fav, tr("Favorito")).changed() {
                                self.save_favorite(&v.post, fav);
                            }
                            if file.is_none() && ui.button(tr("Baixar original")).clicked() {
                                let r = self.db.save(&v.post, &v.bytes);
                                self.message(r)
                            } else if let Some(f) = file {
                                ui.label(format!("Salvo · {f}"));
                                if v.texture.is_none()
                                    && ui.button(tr("Reproduzir vídeo")).clicked()
                                {
                                    let path = self.db.root.join("downloads").join(&f);
                                    let result = std::process::Command::new(if cfg!(windows) {
                                        "explorer.exe"
                                    } else {
                                        "xdg-open"
                                    })
                                    .arg(path)
                                    .spawn()
                                    .map_err(|e| e.to_string());
                                    self.message(result);
                                }
                            }
                        });
                    }
                    ui.collapsing(tr("Organizar e exportar"), |ui| {
                        if ui.button(tr("Bloquear publicação")).clicked() {
                            self.message(self.db.set("post", &id, ""))
                        }
                        if !v.post.artist.is_empty() && ui.button(tr("Bloquear artista")).clicked()
                        {
                            self.message(self.db.set("artist", &v.post.artist, ""))
                        }
                        if self.local(&v.post).is_some()
                            && ui.button(tr("Remover download da galeria")).clicked()
                        {
                            self.remove_file = Some(id.clone());
                        }
                        if self.remove_file.as_ref() == Some(&id) {
                            ui.label(tr("Apagar este arquivo da galeria?"));
                            ui.horizontal(|ui| {
                                if ui.button(tr("Confirmar remoção")).clicked() {
                                    let result = self.db.forget_file(&id);
                                    self.message(result);
                                    self.remove_file = None;
                                }
                                if ui.button(tr("Cancelar")).clicked() {
                                    self.remove_file = None;
                                }
                            });
                        }
                        ui.add(
                            egui::TextEdit::singleline(&mut self.export_path)
                                .hint_text(tr("Caminho completo para exportar")),
                        );
                        if ui.button(tr("Exportar original")).clicked() {
                            use std::io::Write;
                            let result = std::fs::OpenOptions::new()
                                .write(true)
                                .create_new(true)
                                .open(&self.export_path)
                                .and_then(|mut f| f.write_all(&v.bytes))
                                .map_err(|e| e.to_string());
                            self.message(result)
                        }
                    });
                    ui.collapsing(tr("Coleções"), |ui| {
                        for (n, _) in self.db.names("collection").unwrap_or_default() {
                            let mut on = self.db.collection(&id, &n).unwrap_or(false);
                            if ui.checkbox(&mut on, &n).changed() {
                                let result = self.db.assign(&v.post, &n, on);
                                self.message(result);
                            }
                        }
                    });
                    ui.collapsing(tr("Tags"), |ui| {
                        ui.label(&v.post.tags);
                    });
                });
            if hide {
                self.revealed.remove(&v.post.key());
                self.opening = None;
            }
            if !open {
                self.opening = None;
            }
            if open && !hide {
                if next != 0 {
                    let target = self
                        .viewer_order
                        .iter()
                        .position(|p| p.key() == v.post.key())
                        .and_then(|i| i.checked_add_signed(next))
                        .and_then(|i| self.viewer_order.get(i))
                        .cloned();
                    if let Some(p) = target {
                        if self.hidden(&p) {
                            self.status.push(
                                tr("Revele a próxima arte protegida na grade para abrir.").into(),
                            );
                        } else {
                            self.open(ctx, p);
                        }
                    }
                }
                self.viewer = Some(v);
            } else if self.view != "Busca" && !hide {
                self.load(ctx);
            }
        }
    }
}
fn main() -> eframe::Result {
    if std::env::args_os().nth(1).as_deref() == Some(std::ffi::OsStr::new("--smoke-test")) {
        let check_profile = || -> std::io::Result<()> {
            let profile = tempfile::tempdir()?;
            let library = Library::open(profile.path()).map_err(std::io::Error::other)?;
            if !library
                .names("category")
                .map_err(std::io::Error::other)?
                .is_empty()
                || library.counts().map_err(std::io::Error::other)? != (0, 0)
            {
                return Err(std::io::Error::other("Expected an empty ArtFinder profile"));
            }
            Ok(())
        };
        return check_profile().map_err(|error| eframe::Error::AppCreation(Box::new(error)));
    }

    let root = std::env::var_os("ARTFINDER_RUST_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            std::env::var_os("LOCALAPPDATA")
                .map(PathBuf::from)
                .or_else(|| std::env::var_os("HOME").map(|p| PathBuf::from(p).join(".local/share")))
                .unwrap_or_else(std::env::temp_dir)
                .join("ArtFinder-Rust")
        });
    let icon = eframe::icon_data::from_png_bytes(include_bytes!("../../assets/artfinder-icon.png"))
        .expect("ícone");
    let viewport = egui::ViewportBuilder::default()
        .with_icon(icon)
        .with_min_inner_size([610., 515.])
        .with_inner_size([1160., 780.]);
    eframe::run_native(
        "ArtFinder · Rust",
        eframe::NativeOptions {
            viewport,
            ..Default::default()
        },
        Box::new(move |cc| {
            interface::install(&cc.egui_ctx);
            let db = Library::open(&root).map_err(std::io::Error::other)?;
            Ok(Box::new(App::new(db)))
        }),
    )
}

#[cfg(test)]
mod interface_tests {
    use super::*;

    #[test]
    fn pagination_streams_past_fifty_and_stops_on_repeated_cursor() {
        let mut fetched = 0;
        let mut published = 0;
        let mut more = None;
        let cancelled = AtomicBool::new(false);
        let completed = stream_pages(
            None,
            Some(60),
            &cancelled,
            |cursor| {
                assert_eq!(
                    cursor
                        .and_then(|value| value.parse::<usize>().ok())
                        .unwrap_or(0),
                    fetched
                );
                fetched += 1;
                Ok(sources::Page {
                    posts: Vec::new(),
                    next: Some(fetched.to_string()),
                })
            },
            |page, finished| {
                published += 1;
                assert_eq!(finished, published == 60);
                more = page.unwrap().next;
                true
            },
        );
        assert!(completed);
        assert_eq!((fetched, published), (60, 60));
        assert_eq!(more.as_deref(), Some("60"));
        let completed = stream_pages(
            more,
            None,
            &cancelled,
            |cursor| {
                let value = cursor.unwrap();
                let next = if value == "60" { "61" } else { "60" };
                Ok(sources::Page {
                    posts: Vec::new(),
                    next: Some(next.into()),
                })
            },
            |page, finished| {
                published += 1;
                assert_eq!(finished, published == 62);
                assert_eq!(page.unwrap().next.is_none(), finished);
                true
            },
        );
        assert!(completed);
        assert_eq!(published, 62);
    }

    #[test]
    fn pagination_cancels_after_publishing_current_page() {
        let cancelled = AtomicBool::new(false);
        let mut fetched = 0;
        let completed = stream_pages(
            None,
            None,
            &cancelled,
            |_| {
                fetched += 1;
                Ok(sources::Page {
                    posts: Vec::new(),
                    next: Some("next".into()),
                })
            },
            |page, finished| {
                assert_eq!(page.unwrap().next.as_deref(), Some("next"));
                assert!(!finished);
                cancelled.store(true, Ordering::Relaxed);
                true
            },
        );
        assert!(!completed);
        assert_eq!(fetched, 1);
    }

    #[test]
    fn library_filters_and_protected_artwork() {
        let dir = tempfile::tempdir().unwrap();
        let mut app = App::new(Library::open(dir.path()).unwrap());
        let safe = Post {
            source: "Danbooru".into(),
            id: "1".into(),
            artist: "Ari".into(),
            rating: "g".into(),
            ..Default::default()
        };
        let sensitive = Post {
            source: "Danbooru".into(),
            id: "2".into(),
            artist: "Ari".into(),
            rating: "s".into(),
            image: "https://example.invalid/art.gif".into(),
            ..Default::default()
        };
        let ctx = egui::Context::default();
        app.tx
            .send(Event::Page {
                epoch: app.search_epoch,
                query: "Danbooru|test".into(),
                result: Ok(sources::Page {
                    posts: vec![safe.clone(), sensitive.clone()],
                    next: None,
                }),
                finished: true,
            })
            .unwrap();
        app.events(&ctx);
        assert_eq!(app.visible().len(), 1);
        let db = rusqlite::Connection::open(dir.path().join("library.sqlite3")).unwrap();
        let recorded: i64 = db
            .query_row("SELECT count(*) FROM posts", [], |row| row.get(0))
            .unwrap();
        assert_eq!(recorded, 0);
        app.safe = false;
        assert!(app.hidden(&sensitive));
        app.thumbs(&ctx, std::slice::from_ref(&sensitive));
        app.open(&ctx, sensitive.clone());
        assert!(app.queued_thumbs.is_empty());
        assert!(app.opening.is_none());
        app.revealed.insert(sensitive.key());
        assert!(!app.hidden(&sensitive));
        app.revealed.remove(&sensitive.key());
        assert!(app.hidden(&sensitive));
        app.formats[1] = false;
        assert_eq!(app.visible().len(), 1);
        app.formats = [true; 4];
        app.db.save_favorite(&safe, true).unwrap();
        app.load(&ctx);
        assert!(app.results.is_empty());
        app.view = "Galeria".into();
        app.load(&ctx);
        assert_eq!(app.visible().len(), 1);
        app.gallery_modes[1] = false;
        assert!(app.visible().is_empty());
    }

    #[test]
    fn interface_renders_search_and_grid_at_desktop_and_compact_sizes() {
        let dir = tempfile::tempdir().unwrap();
        let mut app = App::new(Library::open(dir.path()).unwrap());
        let ctx = egui::Context::default();
        interface::install(&ctx);
        let p = Post {
            source: "Safebooru".into(),
            id: "test".into(),
            artist: "Sample".into(),
            rating: "safe".into(),
            ..Default::default()
        };
        let file = app
            .db
            .save(&p, include_bytes!("../../assets/artfinder-icon.png"))
            .unwrap();
        assert!(app.db.root.join("downloads").join(file).is_file());
        for (width, view) in [
            (1160., "Busca"),
            (1160., "Galeria"),
            (610., "Galeria"),
            (610., "Configurações"),
            (1160., "Estatísticas"),
        ] {
            app.view = view.into();
            app.load(&ctx);
            let viewport = egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(width, 650.),
                )),
                ..Default::default()
            };
            let output = ctx.run(viewport, |ctx| {
                app.events(ctx);
                app.shell(ctx);
                app.screen(ctx);
            });
            assert!(!output.shapes.is_empty());
        }
    }
}
