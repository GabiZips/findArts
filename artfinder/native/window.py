"""ArtFinder native desktop workspace built entirely with Qt Widgets."""
import json
from urllib.parse import quote, urlsplit

from PySide6.QtCore import QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QGridLayout,
    QHBoxLayout, QLabel, QListView, QMainWindow, QMenu, QMessageBox, QProgressBar,
    QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QLineEdit, QListWidget, QListWidgetItem, QSlider, QSplitter,
)

from .studio import nav_icon
from .inspector import Inspector
from .themes import THEMES, apply_theme, load_fonts, refresh_icons, stylesheet
from .client import ApiClient
from .dialogs import CategoryDialog, CollectionsDialog, FiltersDialog, SearchDialog, SettingsDialog
from .models import ArtworkModel, canonical, filter_posts, rating, source_name, uid
from .widgets import ArtworkDelegate, ArtworkGrid, ImageView, Thumbnails, Viewer, button, label, pixmap_from_bytes


STYLE = stylesheet("night")


class NativeWindow(QMainWindow):
    def __init__(self, base_url, data_dir, download_dir, resource_dir):
        super().__init__()
        from pathlib import Path
        self.data_dir, self.download_dir = Path(data_dir), Path(download_dir)
        self.preferences = QSettings(str(self.data_dir / "native-ui.ini"), QSettings.Format.IniFormat)
        self.theme = self.preferences.value("theme", "night")
        if self.theme not in THEMES:
            self.theme = "night"
        load_fonts(resource_dir)
        apply_theme(QApplication.instance(), self.theme)
        from .translations import NativeTranslations
        self.translations = NativeTranslations(Path(resource_dir), self.preferences.value("language", "pt-BR"), self)
        QApplication.instance().installEventFilter(self.translations)
        self.categories, self.sources, self.unavailable_sources, self.collections = {}, [], [], []
        self.search_posts, self.library_posts, self.ratings, self.saved = [], [], {}, set()
        self.filters = self.read_preference("filters", {})
        self.search_options = self.read_preference("search", {})
        self.blur = self.preferences.value("blur_nsfw", True, type=bool)
        self.revealed = set()
        self.section = "search"
        self.search_reply = None
        self.search_generation = 0
        self.library_generation = 0
        self.setWindowTitle("ArtFinder")
        self.setWindowIcon(QIcon(str(Path(resource_dir) / "assets" / "artfinder.ico")))
        self.resize(1440, 900)
        self.setMinimumSize(1000, 680)
        geometry = self.preferences.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.api = ApiClient(base_url, self)
        self.api.failed.connect(self.error)
        self.thumbnails = Thumbnails(self.api, self)
        self.model = ArtworkModel(self)
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        rail = QWidget()
        rail.setObjectName("rail")
        rail.setFixedWidth(200)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(12, 18, 12, 14)
        rail_layout.setSpacing(8)
        brand = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(nav_icon("brand").pixmap(38, 38))
        brand.addWidget(mark)
        brand.addWidget(label("ArtFinder", "brand"), 1)
        rail_layout.addLayout(brand)
        rail_layout.addSpacing(18)
        self.nav = {}
        for key, title in [("search", "Explorar"), ("gallery", "Minha galeria"), ("stats", "Estatísticas")]:
            item = button(title, lambda checked=False, key=key: self.switch_section(key))
            item.setProperty("iconName", key)
            item.setProperty("navigation", True)
            item.setIcon(nav_icon(key))
            item.setIconSize(QSize(21, 21))
            item.setCheckable(True)
            item.setChecked(key == "search")
            self.nav[key] = item
            item.toggled.connect(lambda: refresh_icons(QApplication.instance(), self.theme))
            rail_layout.addWidget(item)
        rail_layout.addWidget(label("Coleções", "navHeading"))
        self.collection_list = QListWidget()
        self.collection_list.setObjectName("collectionList")
        self.collection_list.setProperty("userDataLabels", True)
        self.collection_list.itemClicked.connect(self.select_collection)
        rail_layout.addWidget(self.collection_list, 1)
        for key, title, callback in [
            ("categories", "Categorias", self.open_categories),
            ("collections", "Coleções", lambda: self.open_dialog(CollectionsDialog)),
            ("settings", "Configurações", lambda: self.open_dialog(SettingsDialog)),
        ]:
            item = button(title, callback)
            item.setProperty("iconName", key)
            item.setProperty("navigation", True)
            item.setIcon(nav_icon(key))
            item.setIconSize(QSize(21, 21))
            rail_layout.addWidget(item)
        self.language = QComboBox()
        self.language.setProperty("userDataLabels", True)
        self.language.addItem("Português", "pt-BR")
        self.language.addItem("English", "en")
        self.language.setCurrentIndex(max(0, self.language.findData(self.translations.language)))
        self.language.currentIndexChanged.connect(self.change_language)
        rail_layout.addWidget(self.language)
        self.blur_box = QCheckBox("Ocultar prévias NSFW")
        self.blur_box.setChecked(self.blur)
        self.blur_box.toggled.connect(self.set_blur)
        rail_layout.addWidget(self.blur_box)
        self.disk_status = label("Biblioteca local", "muted")
        rail_layout.addWidget(self.disk_status)
        outer.addWidget(rail)
        workspace = QWidget()
        content = QVBoxLayout(workspace)
        content.setContentsMargins(18, 16, 18, 8)
        content.setSpacing(10)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        self.title = label("Explorar artes", "title")
        self.subtitle = label("Busque nas suas fontes e organize suas descobertas.", "muted")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)
        self.filter_button = button("Filtros", self.open_filters)
        self.new_search = button("Nova busca", self.open_search, True)
        self.new_search.setEnabled(False)
        header.addWidget(self.filter_button)
        header.addWidget(self.new_search)
        content.addLayout(header)
        self.progress_panel = QWidget()
        progress_layout = QHBoxLayout(self.progress_panel)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress_text = label("Buscando…", "muted")
        progress_layout.addWidget(self.progress, 1)
        progress_layout.addWidget(self.progress_text)
        progress_layout.addWidget(button("Cancelar", self.cancel_search))
        self.progress_panel.hide()
        content.addWidget(self.progress_panel)
        self.toolbar = QWidget()
        self.toolbar.setObjectName("searchTools")
        toolbar = QHBoxLayout(self.toolbar)
        toolbar.setContentsMargins(0, 0, 0, 0)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Filtrar por artista, categoria ou tag…")
        self.query.setClearButtonEnabled(True)
        self.query.textChanged.connect(self.apply_filters)
        toolbar.addWidget(self.query, 1)
        self.source_filter = QComboBox()
        self.source_filter.addItem("Todos os sites", "")
        self.source_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.source_filter)
        self.sort = QComboBox()
        for name, value in [("Maior score", "score"), ("Mais recentes", "recent"), ("Artista", "artist"), ("Fonte", "source"), ("Categoria", "category")]:
            self.sort.addItem(name, value)
        self.sort.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.sort)
        toolbar.addWidget(button("Atualizar", self.refresh_library))
        content.addWidget(self.toolbar)
        self.library_toolbar = QWidget()
        library_layout = QHBoxLayout(self.library_toolbar)
        library_layout.setContentsMargins(0, 0, 0, 0)
        self.collection_filter = QComboBox()
        self.collection_filter.setProperty("userDataLabels", True)
        self.collection_filter.addItem("Todas as coleções", None)
        self.collection_filter.currentIndexChanged.connect(self.apply_filters)
        library_layout.addWidget(self.collection_filter)
        self.duplicates_button = button("Duplicatas", self.show_duplicates)
        library_layout.addWidget(self.duplicates_button)
        self.hide_saved = QCheckBox("Ocultar artes já guardadas")
        self.hide_saved.setChecked(True)
        self.hide_saved.toggled.connect(self.apply_filters)
        library_layout.addWidget(self.hide_saved)
        library_layout.addStretch()
        self.count = label("0 artes", "muted")
        library_layout.addWidget(self.count)
        content.addWidget(self.library_toolbar)
        self.pages = QStackedWidget()
        self.grid = ArtworkGrid()
        self.grid.setObjectName("artGrid")
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setLayoutMode(QListView.LayoutMode.Batched)
        self.grid.setBatchSize(80)
        self.grid.setUniformItemSizes(True)
        self.grid.setGridSize(QSize(260, 328))
        self.grid.setMouseTracking(True)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.grid.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.grid.setModel(self.model)
        self.grid.setItemDelegate(ArtworkDelegate(self, self.grid))
        self.grid.activated.connect(lambda index: self.open_viewer(index.row()))
        self.grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self.context_menu)
        self.grid.selectionModel().selectionChanged.connect(self.selection_changed)
        self.thumbnails.changed.connect(self.grid.viewport().update)
        self.empty = QWidget()
        empty_layout = QVBoxLayout(self.empty)
        empty_layout.setContentsMargins(32, 32, 32, 32)
        empty_layout.addStretch()
        self.empty_title = label("Sua próxima descoberta começa aqui", "emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title)
        self.empty_message = label("Busque por tags ou abra uma busca para escolher categorias e fontes.", "muted")
        self.empty_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_message)
        empty_layout.addSpacing(18)
        self.quick_search = QLineEdit()
        self.quick_search.setPlaceholderText("Digite tags, personagens ou artistas…")
        self.quick_search.setClearButtonEnabled(True)
        self.quick_search.setMinimumWidth(420)
        self.quick_search.setMaximumWidth(520)
        self.quick_search.setMinimumHeight(34)
        self.quick_search.returnPressed.connect(self.search_tags)
        empty_layout.addWidget(self.quick_search, 0, Qt.AlignmentFlag.AlignHCenter)
        self.empty_search = button("Buscar", self.search_tags, True)
        self.empty_search.setEnabled(False)
        empty_layout.addWidget(self.empty_search, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addSpacing(12)
        self.search_hint = label("Ctrl + N  Nova busca     ·     Ctrl + F  Filtrar resultados", "muted")
        self.search_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.search_hint)
        empty_layout.addStretch(2)
        self.stats = QTableWidget(0, 2)
        self.stats.setHorizontalHeaderLabels(["Biblioteca", "Quantidade"])
        self.stats.horizontalHeader().setStretchLastSection(True)
        self.stats.setColumnWidth(0, 420)
        self.stats.verticalHeader().hide()
        self.stats.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for widget in [self.empty, self.grid, self.stats]:
            self.pages.addWidget(widget)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.pages)
        self.inspector = Inspector(self)
        self.splitter.addWidget(self.inspector)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setSizes([850, 250])
        content.addWidget(self.splitter, 1)
        status_tools = QHBoxLayout()
        self.grid_hint = label("Duplo clique para abrir · Ctrl + clique para selecionar", "muted")
        status_tools.addWidget(self.grid_hint, 1)
        status_tools.addWidget(label("Miniaturas", "muted"))
        self.thumbnail_size = QSlider(Qt.Orientation.Horizontal)
        self.thumbnail_size.setRange(160, 320)
        self.thumbnail_size.setValue(self.preferences.value("thumbnail_size", 220, type=int))
        self.thumbnail_size.setFixedWidth(100)
        self.thumbnail_size.setToolTip("Tamanho das miniaturas")
        self.thumbnail_size.setAccessibleName("Tamanho das miniaturas")
        self.thumbnail_size.valueChanged.connect(self.resize_thumbnails)
        status_tools.addWidget(self.thumbnail_size)
        self.inspector_toggle = button("Detalhes", self.toggle_inspector)
        self.inspector_toggle.setCheckable(True)
        self.inspector_toggle.setChecked(self.preferences.value("show_inspector", True, type=bool))
        status_tools.addWidget(self.inspector_toggle)
        content.addLayout(status_tools)
        self.grid.set_thumbnail_width(self.thumbnail_size.value())
        self.actions = QWidget()
        self.actions.setObjectName("actions")
        actions = QHBoxLayout(self.actions)
        actions.setContentsMargins(14, 12, 14, 12)
        self.selection_label = label("Selecione uma arte para abrir ou guardar.", "muted")
        actions.addWidget(self.selection_label, 1)
        self.save_collection = QComboBox()
        self.save_collection.setProperty("userDataLabels", True)
        self.save_collection.setToolTip("Coleção usada ao guardar")
        self.save_collection.addItem("Sem coleção", None)
        actions.addWidget(self.save_collection)
        self.open_button = button("Abrir", self.open_selected)
        self.save_button = button("Guardar", self.save_selected)
        self.download_button = button("Baixar", lambda: self.download(self.selected()), True)
        for widget in [self.open_button, self.save_button, self.download_button]:
            actions.addWidget(widget)
        content.addWidget(self.actions)
        outer.addWidget(workspace, 1)
        self.statusBar().showMessage("Conectando à biblioteca local…")
        for key, callback in [("Ctrl+N", self.open_search), ("Ctrl+F", self.query.setFocus), ("Ctrl+,", lambda: self.open_dialog(SettingsDialog))]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
        self.collection_filter.hide()
        self.apply_filters()
        apply_theme(QApplication.instance(), self.theme)
        self.refresh_configuration()
        self.refresh_library()

    def resize_thumbnails(self, size):
        self.preferences.setValue("thumbnail_size", size)
        self.grid.set_thumbnail_width(size)

    def toggle_inspector(self, *_):
        enabled = self.inspector_toggle.isChecked()
        self.preferences.setValue("show_inspector", enabled)
        self.inspector.setVisible(enabled and self.pages.currentWidget() == self.grid)

    def select_collection(self, item):
        self.collection_filter.setCurrentIndex(max(0, self.collection_filter.findData(item.data(Qt.ItemDataRole.UserRole))))
        self.switch_section("gallery")

    def search_tags(self):
        if not self.new_search.isEnabled() or not self.api.authenticated:
            return
        tags = self.quick_search.text().strip()
        if not tags or not self.sources:
            self.open_search()
            return
        self.search_options = {"categories": [], "sources": self.sources, "pages": 1, "tags": tags}
        self.preferences.setValue("search", json.dumps(self.search_options))
        self.start_search()

    def set_theme(self, key):
        self.theme = key if key in THEMES else "night"
        self.preferences.setValue("theme", self.theme)
        self.preferences.sync()
        apply_theme(QApplication.instance(), self.theme)
        self.grid.viewport().update()

    def read_preference(self, key, fallback):
        try:
            result = json.loads(self.preferences.value(key, "null"))
            return result if isinstance(result, type(fallback)) else fallback
        except (ValueError, TypeError):
            return fallback

    def notify(self, message):
        self.statusBar().showMessage(self.translations.text(message), 12000)

    def change_language(self):
        language = self.language.currentData()
        self.preferences.setValue("language", language)
        self.translations.set_language(language)

    def error(self, message):
        self.notify("Erro: " + message)
        QMessageBox.warning(self, "ArtFinder", message)

    def refresh_configuration(self):
        self.api.request("/api/categories", lambda data: setattr(self, "categories", data.get("categories", {})))
        def sources(data):
            self.sources = data.get("sources", [])
            self.unavailable_sources = data.get("unavailable_sources", [])
            self.new_search.setEnabled(True)
            self.empty_search.setEnabled(True)
        self.api.request("/api/sources", sources)

    def refresh_library(self):
        self.library_generation += 1
        generation = self.library_generation
        results = {}
        def received(key, data):
            if generation != self.library_generation:
                return
            results[key] = data
            if len(results) != 4:
                return
            self.ratings = results["ratings"].get("ratings", {})
            combined = {}
            for item in results["downloaded"].get("items", []):
                post = canonical(item)
                combined[uid(post)] = post
            favorites = results["favorites"].get("favorites", [])
            self.saved = set(combined) | {uid(p) for p in favorites}
            for item in favorites:
                post = canonical(item)
                key = uid(post)
                combined[key] = {**post, **combined.get(key, {}), "collection_ids": item.get("collection_ids", []), "favorite": True}
            for item in results["rated"].get("items", []):
                post = canonical(item)
                combined.setdefault(uid(post), post)
            self.library_posts = list(combined.values())
            self.apply_filters()
            self.notify("Biblioteca atualizada.")
        for key, path in [("downloaded", "/api/gallery-items"), ("favorites", "/api/favorites"), ("ratings", "/api/ratings"), ("rated", "/api/rated-posts")]:
            self.api.request(path, lambda data, key=key: received(key, data))
        self.api.request("/api/collections", self.set_collections)
        self.api.request("/api/stats", self.set_stats)

    def set_collections(self, data):
        self.collections = data.get("collections", [])
        self.collection_list.clear()
        for collection in self.collections:
            item = QListWidgetItem(collection["name"], self.collection_list)
            item.setData(Qt.ItemDataRole.UserRole, collection["id"])
        if not self.collections:
            item = QListWidgetItem("Nenhuma coleção", self.collection_list)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
        for box, title in [(self.save_collection, "Sem coleção"), (self.collection_filter, "Todas as coleções")]:
            selected = box.currentData()
            box.blockSignals(True)
            box.clear()
            box.addItem(title, None)
            for item in self.collections:
                box.addItem(item["name"], item["id"])
            box.setCurrentIndex(max(0, box.findData(selected)))
            box.blockSignals(False)

    def set_stats(self, data):
        total, disk = data.get("total", 0), data.get("disk_mb", 0)
        self.disk_status.setText(f"{total} artes no banco\n{disk} MB em downloads")
        rows = [("Artes no banco", total), ("Downloads (MB)", disk)]
        for name, key in [("Fonte", "by_source"), ("Categoria", "by_category"), ("Avaliação", "by_rating")]:
            rows.extend((f"{name} / {title}", value) for title, value in (data.get(key) or {}).items())
        self.stats.setRowCount(len(rows))
        for row, (title, value) in enumerate(rows):
            self.stats.setItem(row, 0, QTableWidgetItem(str(title)))
            self.stats.setItem(row, 1, QTableWidgetItem(str(value)))

    def switch_section(self, section):
        self.section = section
        for key, widget in self.nav.items():
            widget.setChecked(key == section)
        self.title.setText({"search": "Explorar artes", "gallery": "Sua galeria", "stats": "Sua biblioteca em números"}[section])
        self.subtitle.setText({"search": "Busque nas suas fontes e organize suas descobertas.", "gallery": "As artes que você escolheu guardar.", "stats": "Acompanhe suas artes e organize seus arquivos."}[section])
        self.toolbar.setVisible(section != "stats")
        self.library_toolbar.setVisible(section != "stats")
        self.actions.setVisible(section != "stats")
        self.filter_button.setVisible(section != "stats")
        self.new_search.setVisible(True)
        self.hide_saved.setVisible(section == "search")
        self.collection_filter.setVisible(section == "gallery")
        if section != "search":
            self.refresh_library()
        self.apply_filters()

    def apply_filters(self, *_):
        if self.section == "stats":
            self.pages.setCurrentWidget(self.stats)
            self.inspector.hide()
            return
        posts = self.search_posts if self.section == "search" else self.library_posts
        selected_source = self.source_filter.currentData()
        self.source_filter.blockSignals(True)
        self.source_filter.clear()
        self.source_filter.addItem("Todos os sites", "")
        sources = {source_name(p.get("source")) for p in posts if p.get("source")}
        if selected_source:
            sources.add(selected_source)
        for source in sorted(sources):
            self.source_filter.addItem(source, source)
        self.source_filter.setCurrentIndex(max(0, self.source_filter.findData(selected_source)))
        self.source_filter.blockSignals(False)
        options = {**self.filters, "query": self.query.text(), "source": self.source_filter.currentData(), "sort": self.sort.currentData(),
                   "hide_saved": self.section == "search" and self.hide_saved.isChecked(), "collection": self.collection_filter.currentData() if self.section == "gallery" else None}
        visible = filter_posts(posts, options, self.ratings, self.saved)
        self.model.replace(visible)
        self.count.setText(f"{len(visible)} de {len(posts)} artes")
        self.pages.setCurrentWidget(self.grid if visible else self.empty)
        self.toolbar.setVisible(bool(posts))
        self.library_toolbar.setVisible(bool(posts))
        self.duplicates_button.setVisible(self.section == "gallery")
        self.actions.setVisible(bool(visible))
        self.filter_button.setVisible(bool(posts))
        self.new_search.setVisible(True)
        if not visible:
            initial = not posts and self.section == "search"
            self.empty_title.setText("Sua próxima descoberta começa aqui" if initial else "Nenhuma arte para mostrar")
            self.empty_message.setText("Busque por tags ou escolha categorias e fontes em Nova busca." if initial else "Ajuste os filtros. As artes que você guardar aparecem nesta galeria.")
            self.quick_search.setVisible(initial)
            self.search_hint.setVisible(initial)
            self.empty_search.setVisible(initial)
        self.toggle_inspector()
        self.selection_changed()

    def open_dialog(self, dialog_type):
        dialog = dialog_type(self)
        dialog.exec()
        # Keep QObject alive for outstanding asynchronous callbacks until shutdown.
        return dialog

    def open_categories(self):
        self.open_dialog(CategoryDialog)

    def open_search(self):
        if not self.api.authenticated or not self.new_search.isEnabled():
            return
        dialog = SearchDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.search_options = dialog.values()
            self.preferences.setValue("search", json.dumps(self.search_options))
            self.start_search()

    def start_search(self):
        if self.search_reply:
            self.search_reply.abort()
        self.search_generation += 1
        generation = self.search_generation
        self.switch_section("search")
        self.search_posts = []
        self.apply_filters()
        self.progress_panel.show()
        self.progress.setValue(0)
        self.progress_text.setText("Iniciando busca…")
        self.new_search.setEnabled(False)
        self.empty_search.setEnabled(False)
        body = {key: self.search_options[key] for key in ("categories", "sources", "pages")}
        tags = self.search_options.get("tags", "")
        body["custom_categories"] = [{"label": "Busca avulsa", "tags": tags}] if tags else []
        body["min_score"] = self.filters.get("score", 0)
        seen = set()
        def event(name, data):
            if generation != self.search_generation:
                return
            if name == "posts":
                for item in data.get("posts", []):
                    post = canonical(item)
                    if uid(post) not in seen:
                        seen.add(uid(post))
                        self.search_posts.append(post)
                self.apply_filters()
            if name in {"progress", "posts"}:
                self.progress.setValue(int(100 * data.get("done", 0) / max(1, data.get("total", 1))))
                self.progress_text.setText(f"{data.get('source', '')}  •  {len(self.search_posts)} artes")
            if name == "done":
                errors = data.get("errors", [])
                self.notify(f"Busca concluída: {len(self.search_posts)} artes." + (f" {len(errors)} fonte(s) tiveram erros." if errors else ""))
                if errors:
                    QMessageBox.warning(self, "Algumas fontes falharam", "\n".join(f"{e.get('source', '')}: {e.get('error', '')}" for e in errors))
        def finished(error, cancelled):
            if generation != self.search_generation:
                return
            self.search_reply = None
            self.progress_panel.hide()
            self.new_search.setEnabled(True)
            self.empty_search.setEnabled(True)
            if error:
                self.error(error)
            elif cancelled:
                self.notify("Busca cancelada. Os resultados recebidos foram mantidos.")
        self.search_reply = self.api.search(body, event, finished)

    def cancel_search(self):
        if self.search_reply:
            self.search_reply.abort()

    def open_filters(self):
        dialog = FiltersDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.filters = dialog.values()
            self.preferences.setValue("filters", json.dumps(self.filters))
            self.apply_filters()

    def set_blur(self, enabled):
        self.blur = enabled
        self.preferences.setValue("blur_nsfw", enabled)
        self.revealed.clear()
        self.grid.viewport().update()
        self.inspector.refresh_preview()

    def selected(self):
        return [self.model.posts[index.row()] for index in self.grid.selectionModel().selectedIndexes()]

    def selection_changed(self, *_):
        selected = self.selected()
        self.inspector.set_posts(selected)
        count = len(selected)
        self.actions.setVisible(count > 0 and self.section != "stats")
        self.selection_label.setText(f"{count} selecionada(s)" if count else "Duplo clique para abrir • Ctrl + clique para selecionar")
        self.open_button.setEnabled(count == 1)
        self.save_button.setEnabled(count > 0)
        self.download_button.setEnabled(count > 0)

    def open_selected(self):
        selected = self.grid.selectionModel().selectedIndexes()
        if selected:
            self.open_viewer(selected[0].row())

    def open_viewer(self, index):
        if 0 <= index < len(self.model.posts):
            viewer = Viewer(self, self.model.posts, index)
            viewer.exec()
            self.inspector.refresh_preview()

    def save_selected(self):
        posts = self.selected()
        self.save_many(posts)

    def save(self, post):
        self.save_many([post])

    def save_many(self, posts):
        collection = self.save_collection.currentData()
        remaining = list(posts)
        def next_post(_=None):
            if not remaining:
                self.notify("Artes guardadas na galeria.")
                self.refresh_library()
                return
            post = canonical(remaining.pop(0))
            # Preserve existing memberships when adding an already-saved artwork.
            existing = next((p for p in self.library_posts if uid(p) == uid(post)), {})
            collections = list(existing.get("collection_ids") or [])
            if collection is not None and collection not in collections:
                collections.append(collection)
            self.api.request("/api/favorites", next_post, method="POST", data={**post, "skip_download": True, "collection_ids": collections})
        if remaining:
            next_post()

    def download(self, posts):
        if not posts:
            return
        self.notify(f"Baixando {len(posts)} arte(s)…")
        self.api.request("/api/download", lambda data: (self.refresh_library(), self.notify(data.get("message", "Download concluído."))), method="POST", data={"posts": [canonical(p) for p in posts]})

    def rate(self, post, value):
        value = "" if self.ratings.get(uid(post)) == value else value
        def rated(_):
            if value:
                self.ratings[uid(post)] = value
            else:
                self.ratings.pop(uid(post), None)
            self.notify("Avaliação salva." if value else "Avaliação removida.")
            self.apply_filters()
        self.api.request("/api/ratings", rated, method="POST", data={**canonical(post), "aval": value})

    def open_source(self, post):
        url = post.get("page_url") or ""
        if urlsplit(url).scheme.lower() in {"http", "https"}:
            QDesktopServices.openUrl(QUrl(url))
        else:
            self.notify("Esta arte não informa um link de origem válido.")

    def open_downloads(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.download_dir)))

    def open_data(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.data_dir)))

    def context_menu(self, position):
        index = self.grid.indexAt(position)
        if not index.isValid():
            return
        post = self.model.posts[index.row()]
        menu = QMenu(self)
        for title, callback in [("Abrir", lambda: self.open_viewer(index.row())), ("Guardar", lambda: self.save(post)), ("Baixar", lambda: self.download([post])), ("Ver na fonte", lambda: self.open_source(post))]:
            menu.addAction(title, callback)
        menu.addSeparator()
        for value, title in [("usar", "Usar"), ("talvez", "Talvez"), ("depois", "Rever depois"), ("nao", "Não gostei")]:
            menu.addAction(title, lambda value=value: self.rate(post, value))
        menu.addSeparator()
        if post.get("favorite"):
            menu.addAction("Remover dos guardados", lambda: self.remove_favorite(post))
        if post.get("rel_path"):
            menu.addAction("Excluir arquivo do dispositivo…", lambda: self.delete_file(post))
        menu.addAction("Ocultar permanentemente…", lambda: self.hide_post(post))
        menu.exec(self.grid.viewport().mapToGlobal(position))

    def remove_favorite(self, post):
        if QMessageBox.question(self, "Remover dos guardados", "Remover esta arte dos guardados? O arquivo baixado será mantido.") == QMessageBox.StandardButton.Yes:
            p = canonical(post)
            self.api.request(f"/api/favorites/{quote(p['source'], safe='')}/{quote(p['id'], safe='')}", lambda _: self.refresh_library(), method="DELETE")

    def delete_file(self, post):
        if QMessageBox.question(self, "Excluir arquivo", "Excluir definitivamente o arquivo desta arte do dispositivo?") == QMessageBox.StandardButton.Yes:
            self.api.request("/api/delete-image", lambda _: self.refresh_library(), method="POST", data={"rel_path": post["rel_path"]})

    def hide_post(self, post):
        if QMessageBox.question(self, "Ocultar arte", "Ocultar esta arte permanentemente das buscas e da galeria?") == QMessageBox.StandardButton.Yes:
            def hidden(_):
                self.search_posts = [p for p in self.search_posts if uid(p) != uid(post)]
                self.refresh_library()
            self.api.request("/api/blacklist", hidden, method="POST", data={"uids": [uid(post)]})

    def show_duplicates(self):
        def loaded(data):
            dialog = QDialog(self)
            dialog.setWindowTitle("Duplicatas")
            dialog.resize(660, 500)
            layout = QVBoxLayout(dialog)
            from PySide6.QtWidgets import QListWidget, QListWidgetItem
            details = QListWidget()
            for number, group in enumerate(data.get("groups", []), 1):
                files = group.get("files", []) if isinstance(group, dict) else group
                for item in files:
                    if isinstance(item, dict):
                        name = item.get("rel_path") or item.get("file_path") or item.get("path") or "Arquivo"
                        QListWidgetItem(f"Grupo {number}  •  {name}\n{item.get('width', 0)} × {item.get('height', 0)}", details)
            if details.count() == 0:
                QListWidgetItem("Nenhuma duplicata encontrada.", details)
            layout.addWidget(label("Arquivos semelhantes encontrados", "dialogTitle"))
            layout.addWidget(details)
            layout.addWidget(button("Fechar", dialog.accept))
            dialog.exec()
        self.api.request("/api/duplicates", loaded)

    def closeEvent(self, event):
        if self.search_reply and QMessageBox.question(self, "Sair do ArtFinder", "Há uma busca em andamento. Cancelar e fechar?") != QMessageBox.StandardButton.Yes:
            event.ignore()
            return
        self.search_generation += 1
        self.cancel_search()
        self.preferences.setValue("geometry", self.saveGeometry())
        self.preferences.sync()
        event.accept()


def run_native(base_url, data_dir, download_dir, resource_dir):
    application = QApplication.instance() or QApplication([])
    application.setApplicationName("ArtFinder")
    application.setOrganizationName("ArtFinder")
    application.setStyle("Fusion")
    application.setStyleSheet(STYLE)
    window = NativeWindow(base_url, data_dir, download_dir, resource_dir)
    window.show()
    return application.exec()
