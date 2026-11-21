use super::{tr, App, Post, SOURCES};
use eframe::egui::{self, Button, Color32, Context, Frame, Margin, RichText, Stroke, TextEdit, Ui};

const CANVAS: Color32 = Color32::from_rgb(17, 17, 23);
const SIDEBAR: Color32 = Color32::from_rgb(23, 22, 31);
const PANEL: Color32 = Color32::from_rgb(30, 29, 41);
const TILE: Color32 = Color32::from_rgb(24, 23, 32);
const LINE: Color32 = Color32::from_rgb(53, 51, 67);
const INK: Color32 = Color32::from_rgb(244, 241, 250);
const MUTED: Color32 = Color32::from_rgb(171, 166, 190);
const ACCENT: Color32 = Color32::from_rgb(177, 155, 252);
const ACTIVE: Color32 = Color32::from_rgb(55, 43, 85);

pub(super) fn install(ctx: &Context) {
    let mut fonts = egui::FontDefinitions::default();
    for (name, data) in [
        (
            "Manrope",
            include_bytes!("../assets/Manrope-Regular.ttf").as_slice(),
        ),
        (
            "Manrope Bold",
            include_bytes!("../assets/Manrope-Bold.ttf").as_slice(),
        ),
    ] {
        fonts
            .font_data
            .insert(name.into(), egui::FontData::from_static(data).into());
    }
    fonts.families.insert(
        title_font(),
        vec!["Manrope Bold".into(), "Ubuntu-Light".into()],
    );
    fonts
        .families
        .entry(egui::FontFamily::Proportional)
        .or_default()
        .insert(0, "Manrope".into());
    ctx.set_fonts(fonts);
    let mut style = (*ctx.style()).clone();
    for (role, size) in [
        (egui::TextStyle::Small, 12.),
        (egui::TextStyle::Body, 14.),
        (egui::TextStyle::Button, 14.),
        (egui::TextStyle::Heading, 21.),
    ] {
        style
            .text_styles
            .insert(role, egui::FontId::proportional(size));
    }
    style.spacing.item_spacing = egui::vec2(10., 10.);
    style.spacing.button_padding = egui::vec2(12., 7.);
    style.spacing.interact_size.y = 30.;
    style.visuals = egui::Visuals::dark();
    let v = &mut style.visuals;
    v.override_text_color = Some(INK);
    v.panel_fill = CANVAS;
    v.window_fill = SIDEBAR;
    v.window_stroke = Stroke::new(1.0_f32, LINE);
    v.extreme_bg_color = CANVAS;
    v.faint_bg_color = TILE;
    v.hyperlink_color = ACCENT;
    v.selection.bg_fill = ACTIVE;
    v.selection.stroke = Stroke::new(1.0_f32, ACCENT);
    for widget in [
        &mut v.widgets.inactive,
        &mut v.widgets.hovered,
        &mut v.widgets.active,
        &mut v.widgets.open,
    ] {
        widget.corner_radius = 7.into();
        widget.weak_bg_fill = PANEL;
        widget.bg_fill = PANEL;
        widget.bg_stroke = Stroke::new(1.0_f32, LINE);
        widget.fg_stroke.color = INK;
    }
    v.widgets.hovered.weak_bg_fill = ACTIVE;
    v.widgets.hovered.bg_stroke = Stroke::new(1.0_f32, ACCENT);
    v.widgets.active.weak_bg_fill = ACTIVE;
    v.widgets.active.bg_stroke = Stroke::new(1.0_f32, ACCENT);
    ctx.set_style(style);
}

fn title_font() -> egui::FontFamily {
    egui::FontFamily::Name("ArtFinder title".into())
}

fn primary(label: &str) -> Button<'_> {
    Button::new(RichText::new(tr(label)).strong().color(CANVAS))
        .fill(ACCENT)
        .corner_radius(7)
}

fn surface(fill: Color32, padding: i8) -> Frame {
    Frame::new().fill(fill).inner_margin(Margin::same(padding))
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) enum GridSize {
    Compact,
    Large,
    Single,
}

impl GridSize {
    fn label(self) -> &'static str {
        match self {
            Self::Compact => "Compacta",
            Self::Large => "Grande",
            Self::Single => "Uma por linha",
        }
    }

    fn layout(self, available: f32) -> (usize, f32, f32) {
        let minimum = match self {
            Self::Compact => 220.,
            Self::Large => 290.,
            Self::Single => available,
        };
        let gap = 14.;
        let columns = ((available + gap) / (minimum + gap)).floor().max(1.) as usize;
        let width = ((available + gap) / columns as f32 - gap - 2.).min(690.);
        let height = match self {
            Self::Compact => (width * 0.84).clamp(155., 290.),
            Self::Large | Self::Single => (width * 1.02).clamp(210., 540.),
        };
        (columns, width, height)
    }
}

fn hint(ui: &mut Ui, text: &str) {
    ui.label(RichText::new(tr(text)).color(MUTED));
}

fn emblem(ui: &mut Ui, search: bool, size: f32) {
    let (rect, _) = ui.allocate_exact_size(egui::Vec2::splat(size), egui::Sense::hover());
    let painter = ui.painter();
    painter.rect_filled(rect, 10, ACTIVE);
    let center = rect.center();
    let point = |x, y| center + egui::vec2(x, y) * size;
    let stroke = Stroke::new(1.8_f32, ACCENT);
    if search {
        painter.circle_stroke(point(-0.05, -0.05), size * 0.15, stroke);
        painter.line_segment([point(0.06, 0.06), point(0.18, 0.18)], stroke);
    } else {
        painter.rect_stroke(
            egui::Rect::from_center_size(center, egui::vec2(size * 0.58, size * 0.48)),
            4,
            stroke,
            egui::StrokeKind::Inside,
        );
        painter.circle_filled(point(-0.13, -0.083), size * 0.037, ACCENT);
        painter.add(egui::Shape::line(
            vec![
                point(-0.22, 0.15),
                point(-0.05, 0.),
                point(0.061, 0.102),
                point(0.18, -0.014),
                point(0.23, 0.044),
            ],
            stroke,
        ));
    }
}

pub(super) fn classification(p: &Post) -> usize {
    match (p.source.as_str(), p.rating.as_str()) {
        (_, "g" | "general" | "safe" | "sfw") | ("Safebooru", _) => 0,
        ("Danbooru", "s") | (_, "sensitive" | "q" | "questionable" | "m") => 1,
        (_, "s") => 0,
        _ => 2,
    }
}

pub(super) fn format_index(p: &Post, file: Option<&str>) -> usize {
    let path = file
        .or_else(|| p.image.split('?').next())
        .unwrap_or("")
        .to_ascii_lowercase();
    if path.ends_with(".gif") {
        1
    } else if path.ends_with(".webp") {
        2
    } else if path.ends_with(".webm") || path.ends_with(".mp4") {
        3
    } else {
        0
    }
}

impl App {
    fn navigate(&mut self, ctx: &Context, view: &str) {
        if self.view == view {
            return;
        }
        if self.view == "Busca" {
            self.search_cache = std::mem::take(&mut self.results);
            self.search_cursors = std::mem::take(&mut self.next);
            self.search_categories = std::mem::take(&mut self.query_categories);
        }
        self.view = view.into();
        self.load(ctx);
        if view == "Busca" {
            self.results = std::mem::take(&mut self.search_cache);
            self.next = std::mem::take(&mut self.search_cursors);
            self.search_result_keys = self.results.iter().map(Post::key).collect();
            self.query_categories = std::mem::take(&mut self.search_categories);
        }
    }

    pub(super) fn shell(&mut self, ctx: &Context) {
        let groups = [
            ("Explorar", &["Busca"][..]),
            (
                "Biblioteca",
                &["Galeria", "Favoritos", "Coleções", "Duplicatas"][..],
            ),
            ("Aplicativo", &["Estatísticas", "Configurações"][..]),
        ];
        if ctx.screen_rect().width() < 790. {
            egui::TopBottomPanel::top("navigation")
                .frame(surface(SIDEBAR, 12))
                .show(ctx, |ui| {
                    ui.horizontal_wrapped(|ui| {
                        ui.label(RichText::new("ArtFinder").size(19.).strong());
                        for (_, tabs) in groups {
                            for tab in tabs {
                                if ui.selectable_label(self.view == *tab, tr(tab)).clicked() {
                                    self.navigate(ctx, tab);
                                }
                            }
                        }
                    });
                });
            return;
        }
        egui::SidePanel::left("navigation")
            .exact_width(204.)
            .resizable(false)
            .frame(surface(SIDEBAR, 16).stroke(Stroke::new(1.0_f32, LINE)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    emblem(ui, false, 36.);
                    ui.label(RichText::new("ArtFinder").font(egui::FontId::new(21., title_font())));
                });
                ui.add_space(23.);
                for (group, tabs) in groups {
                    ui.label(RichText::new(tr(group)).size(12.).strong().color(MUTED));
                    ui.spacing_mut().item_spacing.y = 3.;
                    for tab in tabs {
                        let active = self.view == *tab;
                        let response = ui.add(
                            Button::new(RichText::new(tr(tab)).color(if active {
                                INK
                            } else {
                                MUTED
                            }))
                            .min_size(egui::vec2(ui.available_width(), 37.))
                            .fill(if active { ACTIVE } else { Color32::TRANSPARENT })
                            .stroke(Stroke::NONE)
                            .corner_radius(7),
                        );
                        if active {
                            let left = response.rect.left() + 2.;
                            ui.painter().line_segment(
                                [
                                    egui::pos2(left, response.rect.top() + 10.),
                                    egui::pos2(left, response.rect.bottom() - 10.),
                                ],
                                Stroke::new(2.0_f32, ACCENT),
                            );
                        }
                        if response.clicked() {
                            self.navigate(ctx, tab);
                        }
                    }
                    ui.spacing_mut().item_spacing.y = 10.;
                    ui.add_space(15.);
                }
            });
    }

    fn search_controls(&mut self, ui: &mut Ui, ctx: &Context) {
        surface(PANEL, 15)
            .stroke(Stroke::new(1.0_f32, LINE))
            .corner_radius(11)
            .show(ui, |ui| {
                ui.horizontal(|ui| {
                    let entry = ui.add_sized(
                        [(ui.available_width() - 108.).max(95.), 43.],
                        TextEdit::singleline(&mut self.query)
                            .id_salt("main-query")
                            .hint_text(tr("Digite uma tag ou categoria")),
                    );
                    if ctx.input(|i| i.key_pressed(egui::Key::K) && i.modifiers.command) {
                        entry.request_focus();
                    }
                    let enter = entry.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter));
                    if ui.add_sized([98., 43.], primary("Buscar")).clicked() || enter {
                        self.start(ctx, false);
                    }
                });
                ui.horizontal_wrapped(|ui| {
                    egui::ComboBox::from_id_salt("search-source")
                        .selected_text(if self.source == "Todas" {
                            tr("Todas as fontes")
                        } else {
                            tr(&self.source)
                        })
                        .show_ui(ui, |ui| {
                            for s in ["Todas", "Selecionadas"].into_iter().chain(SOURCES) {
                                ui.selectable_value(
                                    &mut self.source,
                                    s.into(),
                                    tr(if s == "Todas" { "Todas as fontes" } else { s }),
                                );
                            }
                        });
                    if self.source == "Selecionadas" {
                        ui.menu_button(
                            format!("{} ({})", tr("Fontes"), self.selection.len()),
                            |ui| {
                                for s in SOURCES {
                                    let mut selected = self.selection.contains(s);
                                    if ui.checkbox(&mut selected, s).changed() {
                                        if selected {
                                            self.selection.insert(s.into());
                                        } else {
                                            self.selection.remove(s);
                                        }
                                    }
                                }
                            },
                        );
                    }
                    ui.add_enabled(
                        !self.all_pages,
                        egui::DragValue::new(&mut self.pages)
                            .range(1..=u32::MAX)
                            .prefix(tr("Páginas ")),
                    )
                    .on_hover_text(tr("Páginas por consulta"));
                    ui.checkbox(&mut self.all_pages, tr("Até o fim"))
                        .on_hover_text(tr(
                            "Continua até a fonte ficar sem páginas ou você cancelar.",
                        ));
                    self.category_menu(ui, ctx);
                    if self.pending > 0 && ui.button(tr("Cancelar busca")).clicked() {
                        self.cancel_search();
                    }
                });
            });
        let prefix = self
            .query
            .split([' ', ';'])
            .next_back()
            .unwrap_or("")
            .to_lowercase();
        if (2..=80).contains(&prefix.chars().count()) {
            let suggestions = self.db.suggest(&prefix).unwrap_or_default();
            if !suggestions.is_empty() {
                ui.horizontal_wrapped(|ui| {
                    hint(ui, "Sugestões");
                    for tag in suggestions.iter().take(4) {
                        if ui.small_button(tag).clicked() {
                            let pos = self.query.rfind([' ', ';']).map_or(0, |pos| pos + 1);
                            self.query.replace_range(pos.., tag);
                        }
                    }
                });
            }
        }
    }

    fn category_menu(&mut self, ui: &mut Ui, ctx: &Context) {
        ui.menu_button(tr("Categorias"), |ui| {
            let rank = self
                .db
                .names("order")
                .unwrap_or_default()
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>();
            let favorites = self
                .db
                .names("favorite_category")
                .unwrap_or_default()
                .into_iter()
                .map(|(key, _)| key)
                .collect::<std::collections::HashSet<_>>();
            let meta = self
                .db
                .names("category_meta")
                .unwrap_or_default()
                .into_iter()
                .filter_map(|(key, value)| {
                    Some((key, serde_json::from_str::<serde_json::Value>(&value).ok()?))
                })
                .collect::<std::collections::HashMap<_, _>>();
            let mut categories = self.db.names("category").unwrap_or_default();
            categories.sort_by_key(|(key, _)| {
                (
                    !favorites.contains(key),
                    rank.get(key)
                        .and_then(|v| v.parse::<usize>().ok())
                        .unwrap_or(usize::MAX),
                )
            });
            ui.add(
                TextEdit::singleline(&mut self.category_filter).hint_text(tr("Filtrar categorias")),
            );
            let needle = self.category_filter.to_lowercase();
            egui::ScrollArea::vertical()
                .max_height(300.)
                .show(ui, |ui| {
                    for (key, tags) in categories {
                        let label = meta
                            .get(&key)
                            .and_then(|m| m["label"].as_str())
                            .unwrap_or(&key);
                        let group = meta
                            .get(&key)
                            .and_then(|m| m["group"].as_str())
                            .unwrap_or("");
                        if !format!("{label} {group} {tags}")
                            .to_lowercase()
                            .contains(&needle)
                        {
                            continue;
                        }
                        let mut selected = self.query.split(';').any(|s| s.trim() == key);
                        if ui
                            .checkbox(&mut selected, label)
                            .on_hover_text(tags)
                            .changed()
                        {
                            let mut terms = self
                                .query
                                .split(';')
                                .map(str::trim)
                                .filter(|s| !s.is_empty() && *s != key)
                                .map(str::to_owned)
                                .collect::<Vec<_>>();
                            if selected {
                                terms.push(key);
                            }
                            self.query = terms.join("; ");
                        }
                    }
                });
            if ui.button(tr("Gerenciar categorias")).clicked() {
                self.kind = "category".into();
                self.navigate(ctx, "Configurações");
                ui.close_menu();
            }
        });
    }

    fn filters(&mut self, ui: &mut Ui) {
        ui.menu_button(tr("Filtros"), |ui| {
            ui.set_min_width(248.);
            ui.checkbox(&mut self.safe, tr("Somente seguro"));
            let old = self.protect;
            ui.checkbox(&mut self.protect, tr("Proteger conteúdo sensível"));
            if old != self.protect && self.protect {
                self.revealed.clear();
                self.viewer = None;
                self.opening = None;
            }
            if self.view == "Busca" {
                ui.checkbox(&mut self.hide_downloaded, tr("Ocultar da galeria"));
            }
            ui.separator();
            hint(ui, "Classificação");
            ui.horizontal_wrapped(|ui| {
                for (i, label) in ["Seguro", "Sensível", "Adulto"].into_iter().enumerate() {
                    ui.add_enabled_ui(!self.safe || i == 0, |ui| {
                        ui.checkbox(&mut self.classes[i], tr(label));
                    });
                }
            });
            ui.horizontal_wrapped(|ui| {
                for (i, label) in ["Imagem", "GIF", "WebP", "Vídeo"].into_iter().enumerate() {
                    ui.checkbox(&mut self.formats[i], tr(label));
                }
            });
            let period = |days| {
                if days == 0 {
                    tr("Qualquer data").to_owned()
                } else {
                    format!("{days} {}", tr("dias"))
                }
            };
            egui::ComboBox::from_id_salt("period")
                .selected_text(period(self.days))
                .show_ui(ui, |ui| {
                    for days in [0, 7, 30, 90, 180, 365] {
                        ui.selectable_value(&mut self.days, days, period(days));
                    }
                });
            egui::ComboBox::from_id_salt("orientation")
                .selected_text(if self.orientation == "Todas" {
                    tr("Qualquer orientação")
                } else {
                    tr(&self.orientation)
                })
                .show_ui(ui, |ui| {
                    for o in ["Todas", "Paisagem", "Retrato", "Quadrada"] {
                        ui.selectable_value(&mut self.orientation, o.into(), tr(o));
                    }
                });
            ui.horizontal(|ui| {
                ui.add(egui::DragValue::new(&mut self.min_width).prefix(tr("Largura ≥ ")));
                ui.add(egui::DragValue::new(&mut self.min_height).prefix(tr("Altura ≥ ")));
            });
            ui.add(
                egui::DragValue::new(&mut self.min_score)
                    .range(0..=i64::MAX)
                    .prefix(tr("Pontuação ≥ ")),
            );
            ui.horizontal(|ui| {
                ui.checkbox(&mut self.color_filter, tr("Filtrar por cor"));
                ui.color_edit_button_srgb(&mut self.color);
            });
            if self.color_filter {
                ui.add(egui::Slider::new(&mut self.tolerance, 10..=230).text(tr("Tolerância")));
            }
            if ui.button(tr("Restaurar filtros")).clicked() {
                self.safe = true;
                self.classes = [true; 3];
                self.formats = [true; 4];
                self.days = 0;
                self.orientation = "Todas".into();
                self.min_width = 0;
                self.min_height = 0;
                self.min_score = 0;
                self.color_filter = false;
                self.filter.clear();
                self.hide_downloaded = true;
            }
        });
    }

    fn empty(&mut self, ui: &mut Ui, ctx: &Context) {
        let (title, body) = if self.pending > 0 {
            (
                "Buscando artes",
                "Os resultados aparecem conforme cada fonte responde.",
            )
        } else if self.view == "Busca" && !self.searched {
            (
                "O que você quer encontrar?",
                "Digite uma tag ou selecione suas categorias para começar.",
            )
        } else if !self.results.is_empty() {
            (
                "Nenhuma arte com esses filtros",
                "Altere os filtros ou limpe o campo de busca nesta página.",
            )
        } else {
            match self.view.as_str() {
                "Favoritos" => (
                    "Nenhuma arte guardada",
                    "Use Guardar em uma arte para encontrá-la aqui.",
                ),
                "Galeria" => (
                    "Sua galeria está vazia",
                    "Baixe uma arte para acessá-la neste dispositivo.",
                ),
                "Coleções" => (
                    "Nenhuma arte nesta coleção",
                    "Adicione artes a uma coleção pelo menu da publicação.",
                ),
                "Duplicatas" => (
                    "Nenhuma duplicata encontrada",
                    "Imagens baixadas com conteúdo semelhante aparecem aqui.",
                ),
                _ => (
                    "Nenhum resultado",
                    "Confira as tags e abra Atividade para ver a resposta de cada fonte.",
                ),
            }
        };
        ui.add_space(12.);
        surface(TILE, 24)
            .corner_radius(11)
            .stroke(Stroke::new(1.0_f32, LINE))
            .show(ui, |ui| {
                ui.vertical_centered(|ui| {
                    ui.add_space(20.);
                    emblem(ui, self.view == "Busca", 56.);
                    ui.label(RichText::new(tr(title)).font(egui::FontId::new(22., title_font())));
                    hint(ui, body);
                    ui.add_space(6.);
                    if self.view != "Busca"
                        && self.results.is_empty()
                        && ui.button(tr("Ir para a busca")).clicked()
                    {
                        self.navigate(ctx, "Busca");
                    }
                    ui.add_space(16.);
                });
            });
    }

    fn card(&mut self, ui: &mut Ui, ctx: &Context, p: &Post, width: f32, image_height: f32) {
        let id = p.key();
        let hidden = self.hidden(p);
        let (favorite, file) = self.db.details(&id).unwrap_or_default();
        surface(TILE, 0)
            .corner_radius(9)
            .stroke(Stroke::new(1.0_f32, LINE))
            .show(ui, |ui| {
                ui.set_width(width);
                let size = egui::vec2(width, image_height);
                let image_action = if hidden {
                    ui.add_sized(size, Button::new(tr("Mostrar imagem")).fill(PANEL))
                } else if let Some((texture, _)) = self.textures.get(&id) {
                    let ratio =
                        (size.x / texture.size_vec2().x).min(size.y / texture.size_vec2().y);
                    ui.add_sized(
                        size,
                        egui::ImageButton::new(
                            egui::Image::new(texture)
                                .fit_to_exact_size(texture.size_vec2() * ratio)
                                .alt_text(tr("Abrir arte")),
                        )
                        .frame(false),
                    )
                    .on_hover_text(tr("Abrir original"))
                } else {
                    ui.add_sized(
                        size,
                        Button::new(tr(if self.failed_thumbs.contains(&id) {
                            "Abrir original"
                        } else {
                            "Abrir arte"
                        }))
                        .fill(PANEL),
                    )
                };
                if image_action.clicked() {
                    if hidden {
                        self.revealed.insert(id.clone());
                    } else {
                        self.open(ctx, p.clone());
                    }
                }
                surface(TILE, 9).show(ui, |ui| {
                    let artist = if p.artist.is_empty() {
                        tr("Artista desconhecido")
                    } else {
                        &p.artist
                    };
                    ui.add(egui::Label::new(RichText::new(artist).strong()).truncate())
                        .on_hover_text(artist);
                    let rating = tr(["Seguro", "Sensível", "Adulto"][classification(p)]);
                    let details = if p.width > 0 && p.height > 0 {
                        format!("{}  ·  {rating}  ·  {}×{}", p.source, p.width, p.height)
                    } else {
                        format!("{}  ·  {rating}", p.source)
                    };
                    ui.add(
                        egui::Label::new(RichText::new(&details).size(11.).color(MUTED)).truncate(),
                    )
                    .on_hover_text(details);
                    ui.horizontal(|ui| {
                        ui.spacing_mut().button_padding.x = 7.;
                        ui.spacing_mut().item_spacing.x = 5.;
                        if ui
                            .button(tr(if favorite { "Guardado" } else { "Guardar" }))
                            .clicked()
                        {
                            self.save_favorite(p, !favorite);
                        }
                        let busy = self.downloading.contains(&id);
                        if ui
                            .add_enabled(
                                !hidden && file.is_none() && !busy,
                                Button::new(tr(if file.is_some() {
                                    "Baixado"
                                } else if busy {
                                    "Baixando…"
                                } else {
                                    "Baixar"
                                })),
                            )
                            .clicked()
                        {
                            self.download(ctx, p.clone());
                        }
                        ui.menu_button("⋯", |ui| {
                            if self.protect
                                && classification(p) > 0
                                && self.revealed.contains(&id)
                                && ui.button(tr("Ocultar imagem")).clicked()
                            {
                                self.revealed.remove(&id);
                                ui.close_menu();
                            }
                            if url::Url::parse(&p.page).is_ok_and(|u| u.scheme() == "https") {
                                ui.hyperlink_to(tr("Publicação original"), &p.page);
                            }
                            if !hidden && !p.image.is_empty() {
                                if let Ok(mut reverse) =
                                    url::Url::parse("https://saucenao.com/search.php")
                                {
                                    reverse.query_pairs_mut().append_pair("url", &p.image);
                                    ui.hyperlink_to("SauceNAO", reverse.as_str());
                                }
                            }
                            if !p.artist.trim().is_empty() {
                                let display = p.artist.trim();
                                let tag = display
                                    .to_lowercase()
                                    .split_whitespace()
                                    .collect::<Vec<_>>()
                                    .join("_");
                                if !tag.contains(';') {
                                    if ui.button(tr("Buscar artista")).clicked() {
                                        self.navigate(ctx, "Busca");
                                        self.query = tag.clone();
                                        self.start(ctx, false);
                                        ui.close_menu();
                                    }
                                    if ui.button(tr("Favoritar artista")).clicked() {
                                        let meta =
                                            serde_json::json!({"label":display,"group":"Artistas"});
                                        let result =
                                            self.db.set_category(&tag, &tag, &meta).and_then(
                                                |()| self.db.set("favorite_category", &tag, "1"),
                                            );
                                        self.message(result);
                                        ui.close_menu();
                                    }
                                }
                            }
                            let names = self.db.names("collection").unwrap_or_default();
                            if !names.is_empty() {
                                ui.separator();
                                hint(ui, "Coleções");
                                for (n, _) in names {
                                    let mut on = self.db.collection(&id, &n).unwrap_or(false);
                                    if ui.checkbox(&mut on, &n).changed() {
                                        let result = self.db.assign(p, &n, on);
                                        self.message(result);
                                    }
                                }
                            }
                            ui.separator();
                            if ui.button(tr("Bloquear publicação")).clicked() {
                                self.message(self.db.set("post", &id, ""));
                                ui.close_menu();
                            }
                            if !p.artist.is_empty() && ui.button(tr("Bloquear artista")).clicked() {
                                self.message(self.db.set("artist", &p.artist, ""));
                                ui.close_menu();
                            }
                        });
                    });
                });
            });
    }

    pub(super) fn screen(&mut self, ctx: &Context) {
        egui::CentralPanel::default()
            .frame(surface(CANVAS, 24))
            .show(ctx, |ui| {
                let title = if self.view == "Busca" {
                    "Buscar artes"
                } else {
                    &self.view
                };
                ui.label(RichText::new(tr(title)).font(egui::FontId::new(32., title_font())));
                ui.add_space(3.);
                if self.view == "Configurações" {
                    self.activity(ui);
                    egui::ScrollArea::vertical().show(ui, |ui| self.settings(ui));
                    return;
                }
                if self.view == "Estatísticas" {
                    self.stats(ui);
                    return;
                }
                if self.view == "Busca" {
                    self.search_controls(ui, ctx);
                }
                if self.view == "Coleções" {
                    self.collection_controls(ui, ctx);
                }
                if self.view == "Galeria" {
                    ui.horizontal_wrapped(|ui| {
                        for (i, label) in ["Baixadas", "Guardadas"].into_iter().enumerate() {
                            ui.checkbox(&mut self.gallery_modes[i], tr(label));
                        }
                    });
                }
                ui.horizontal_wrapped(|ui| {
                    ui.add_sized(
                        [215., 32.],
                        TextEdit::singleline(&mut self.filter).hint_text(tr("Filtrar resultados")),
                    );
                    self.filters(ui);
                    egui::ComboBox::from_id_salt("sort")
                        .selected_text(tr(&self.sort))
                        .show_ui(ui, |ui| {
                            for s in [
                                "Maior pontuação",
                                "Menor pontuação",
                                "Em alta",
                                "Fonte",
                                "Categoria",
                                "Ordem de chegada",
                            ] {
                                ui.selectable_value(&mut self.sort, s.into(), tr(s));
                            }
                        });
                    if self.view != "Busca" && ui.button(tr("Atualizar")).clicked() {
                        self.load(ctx);
                    }
                    if self.view == "Busca" {
                        egui::ComboBox::from_id_salt("search-grid-size")
                            .selected_text(tr(self.grid_size.label()))
                            .show_ui(ui, |ui| {
                                for size in [GridSize::Compact, GridSize::Large, GridSize::Single] {
                                    ui.selectable_value(
                                        &mut self.grid_size,
                                        size,
                                        tr(size.label()),
                                    );
                                }
                            })
                            .response
                            .on_hover_text(tr("Tamanho das imagens"));
                    }
                });
                let candidates = self.visible();
                if self.color_filter {
                    self.analyze_colors(ctx, &candidates);
                }
                let posts = candidates
                    .into_iter()
                    .filter(|p| self.color_matches(p))
                    .collect::<Vec<_>>();
                self.viewer_order = posts.clone();
                ui.horizontal_wrapped(|ui| {
                    if !posts.is_empty() {
                        ui.label(
                            RichText::new(format!(
                                "{} {}",
                                posts.len(),
                                tr(if posts.len() == 1 { "arte" } else { "artes" })
                            ))
                            .strong(),
                        );
                    }
                    if self.pending > 0 {
                        ui.spinner();
                        hint(ui, "Buscando nas fontes");
                    }
                    if self.view == "Busca" && self.search_pages_loaded > 0 {
                        ui.small(format!(
                            "{} {}",
                            self.search_pages_loaded,
                            tr(if self.search_pages_loaded == 1 {
                                "página consultada"
                            } else {
                                "páginas consultadas"
                            })
                        ));
                    }
                    if self.opening.is_some() {
                        ui.spinner();
                        hint(ui, "Abrindo original");
                    }
                    if self.pending == 0
                        && !self.next.is_empty()
                        && self.view == "Busca"
                        && ui.button(tr("Carregar mais")).clicked()
                    {
                        self.start(ctx, true);
                    }
                    self.activity(ui);
                });
                if posts.is_empty() {
                    if self.color_filter && !self.queued_thumbs.is_empty() {
                        ui.spinner();
                        hint(ui, "Analisando cores");
                    } else {
                        self.empty(ui, ctx);
                    }
                    return;
                }
                let gap = 14.;
                let grid = if self.view == "Busca" {
                    self.grid_size
                } else {
                    GridSize::Compact
                };
                let available = ui.available_width() - 12.;
                let (cols, width, height) = grid.layout(available);
                let row_width = (width + 2.) * cols as f32 + gap * (cols - 1) as f32;
                let inset = ((available - row_width) * 0.5).max(0.);
                ui.spacing_mut().item_spacing.y = gap;
                egui::ScrollArea::vertical()
                    .auto_shrink([false, false])
                    .id_salt(&self.view)
                    .show_rows(ui, height + 103., posts.len().div_ceil(cols), |ui, rows| {
                        let first = rows.start * cols;
                        let end = (rows.end * cols).min(posts.len());
                        self.thumbs(ctx, &posts[first..end]);
                        for row in posts[first..end].chunks(cols) {
                            ui.allocate_ui(egui::vec2(ui.available_width(), height + 103.), |ui| {
                                ui.horizontal_top(|ui| {
                                    ui.spacing_mut().item_spacing.x = gap;
                                    if inset > 1. {
                                        ui.add_space(inset);
                                    }
                                    for p in row {
                                        ui.push_id(p.key(), |ui| {
                                            self.card(ui, ctx, p, width, height)
                                        });
                                    }
                                });
                            });
                        }
                    });
            });
    }

    fn activity(&self, ui: &mut Ui) {
        if let Some(latest) = self.status.last() {
            ui.menu_button(tr("Atividade"), |ui| {
                egui::ScrollArea::vertical()
                    .max_height(270.)
                    .show(ui, |ui| {
                        for line in self.status.iter().rev().take(30) {
                            ui.label(line);
                        }
                    });
            })
            .response
            .on_hover_text(latest);
            ui.add(egui::Label::new(RichText::new(latest).color(MUTED).size(12.)).truncate());
        }
    }

    fn collection_controls(&mut self, ui: &mut Ui, ctx: &Context) {
        let names = self.db.names("collection").unwrap_or_default();
        ui.horizontal_wrapped(|ui| {
            egui::ComboBox::from_id_salt("collection")
                .selected_text(if self.collection.is_empty() {
                    tr("Escolher coleção")
                } else {
                    &self.collection
                })
                .show_ui(ui, |ui| {
                    for (name, _) in &names {
                        if ui
                            .selectable_label(self.collection == *name, name)
                            .clicked()
                        {
                            self.collection = name.clone();
                            self.load(ctx);
                        }
                    }
                });
            ui.menu_button(tr("Nova coleção"), |ui| {
                ui.add(TextEdit::singleline(&mut self.collection_edit).hint_text(tr("Nome")));
                if ui.button(tr("Criar coleção")).clicked()
                    && !self.collection_edit.trim().is_empty()
                {
                    let name = self.collection_edit.trim().to_owned();
                    match self.db.set("collection", &name, "") {
                        Ok(()) => {
                            self.collection = name;
                            self.collection_edit.clear();
                            ui.close_menu();
                            self.load(ctx);
                        }
                        Err(e) => self.status.push(e),
                    }
                }
            });
            if !self.collection.is_empty() {
                ui.menu_button(tr("Excluir coleção"), |ui| {
                    hint(
                        ui,
                        "Confirme a exclusão da coleção. As artes continuam na biblioteca.",
                    );
                    if ui.button(tr("Confirmar remoção")).clicked() {
                        let name = self.collection.clone();
                        match self.db.remove("collection", &name) {
                            Ok(()) => {
                                self.collection.clear();
                                self.load(ctx);
                                ui.close_menu();
                            }
                            Err(e) => self.status.push(e),
                        }
                    }
                });
                ui.menu_button(tr("Renomear coleção"), |ui| {
                    ui.add(
                        TextEdit::singleline(&mut self.collection_edit).hint_text(tr("Novo nome")),
                    );
                    if ui.button(tr("Renomear")).clicked() {
                        let name = self.collection_edit.trim().to_owned();
                        match self.db.rename_collection(&self.collection, &name) {
                            Ok(()) => {
                                self.collection = name;
                                self.collection_edit.clear();
                                ui.close_menu();
                                self.load(ctx);
                            }
                            Err(e) => self.status.push(e),
                        }
                    }
                });
            }
        });
    }

    fn stats(&mut self, ui: &mut Ui) {
        let Ok(stats) = self.db.stats() else {
            hint(ui, "Estatísticas indisponíveis");
            return;
        };
        egui::ScrollArea::vertical().show(ui, |ui| {
            ui.horizontal_wrapped(|ui| {
                for (label, value) in [
                    ("Guardadas", stats.favorites.to_string()),
                    ("Baixadas", stats.downloads.to_string()),
                    (
                        "No disco",
                        format!("{:.1} MiB", stats.bytes as f64 / 1048576.),
                    ),
                ] {
                    surface(PANEL, 16).corner_radius(9).show(ui, |ui| {
                        ui.set_min_width(128.);
                        ui.label(RichText::new(value).size(28.).strong());
                        hint(ui, label);
                    });
                }
            });
            for (heading, rows) in [
                ("Por fonte", stats.sources),
                ("Por categoria", stats.categories),
            ] {
                ui.add_space(12.);
                ui.heading(tr(heading));
                let max = rows.iter().map(|(_, n)| *n).max().unwrap_or(1).max(1) as f32;
                for (key, n) in rows {
                    ui.horizontal(|ui| {
                        ui.add_sized([145., 26.], egui::Label::new(tr(&key)).truncate())
                            .on_hover_text(&key);
                        ui.add(
                            egui::ProgressBar::new(n as f32 / max)
                                .desired_width((ui.available_width() - 45.).clamp(20., 350.))
                                .fill(ACCENT),
                        );
                        ui.label(n.to_string());
                    });
                }
            }
        });
    }

    fn color_matches(&self, p: &Post) -> bool {
        !self.color_filter
            || self.hidden(p)
            || self.palette.get(&p.key()).is_some_and(|colors| {
                colors.iter().any(|c| {
                    c.iter()
                        .zip(self.color)
                        .map(|(a, b)| (i32::from(*a) - i32::from(b)).pow(2) as u32)
                        .sum::<u32>()
                        <= self.tolerance.pow(2)
                })
            })
    }
}
