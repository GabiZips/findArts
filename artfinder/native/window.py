"""ArtFinder native desktop workspace built entirely with Qt Widgets."""
import json
from urllib.parse import quote, urlsplit

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
    QHBoxLayout, QLabel, QLineEdit, QListView, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QSlider, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from .studio import nav_icon
from .inspector import Inspector
from .themes import THEMES, apply_theme, load_fonts, stylesheet
from .client import ApiClient
from .dialogs import CategoryDialog, CollectionsDialog, FiltersDialog, SearchDialog, SettingsDialog
from .models import ArtworkModel, canonical, filter_posts, rating, source_name, uid
from .widgets import ArtworkDelegate, ArtworkGrid, Thumbnails, Viewer, button, label


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
        self.search_attempted = False
        self.search_generation = 0
        self.library_generation = 0
        self.setWindowTitle("ArtFinder")
        self.setWindowIcon(nav_icon("brand"))
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
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        masthead = QWidget()
        masthead.setObjectName("masthead")
        mast = QHBoxLayout(masthead)
        mast.setContentsMargins(22, 10, 22, 10)
        mast.setSpacing(10)
        mark = QLabel()
        mark.setPixmap(nav_icon("brand").pixmap(46, 46))
        mast.addWidget(mark)
        mast.addWidget(label("ArtFinder", "brand"))
        mast.addSpacing(22)
        self.nav = {}
        self.navigation = QButtonGroup(self)
        self.navigation.setExclusive(True)
        for key, title in [("search", "Explorar"), ("gallery", "Minha galeria"), ("stats", "Estatísticas")]:
            item = button(title, lambda checked=False, key=key: self.switch_section(key), icon=key)
            item.setObjectName("navTab")
            item.setCheckable(True)
            self.navigation.addButton(item)
            item.setChecked(key == "search")
            self.nav[key] = item
            mast.addWidget(item)
        mast.addStretch(1)
        mast.addWidget(button("Categorias", self.open_categories, icon="categories"))
        mast.addWidget(button("Configurações", lambda: self.open_dialog(SettingsDialog), icon="settings"))
        outer.addWidget(masthead)

        workspace = QWidget()
        content = QVBoxLayout(workspace)
        content.setContentsMargins(22, 14, 22, 10)
        content.setSpacing(10)
        self.command_bar = QWidget()
        self.command_bar.setObjectName("commandBar")
        command = QHBoxLayout(self.command_bar)
        command.setContentsMargins(10, 8, 8, 8)
        command.setSpacing(8)
        self.quick_search = QLineEdit(self.search_options.get("tags", ""))
        self.quick_search.setPlaceholderText("Digite tags, personagens ou artistas…")
        self.quick_search.setAccessibleName("Tags da busca")
        self.quick_search.setClearButtonEnabled(True)
        self.quick_search.returnPressed.connect(self.search_tags)
        command.addWidget(self.quick_search, 1)
        self.empty_search = button("Buscar", self.search_tags, True)
        self.empty_search.setEnabled(False)
        command.addWidget(self.empty_search)
        self.new_search = button("Busca avançada", self.open_search, icon="filter")
        self.new_search.setToolTip("Escolher categorias, fontes e páginas (Ctrl+N)")
        self.new_search.setEnabled(False)
        command.addWidget(self.new_search)
        content.addWidget(self.command_bar)
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
        header = QHBoxLayout()
        self.title = label("Explorar", "title")
        header.addWidget(self.title)
        self.count = label("", "resultCount")
        header.addWidget(self.count)
        header.addStretch(1)
        self.library_toolbar = QWidget()
        library_layout = QHBoxLayout(self.library_toolbar)
        library_layout.setContentsMargins(0, 0, 0, 0)
        self.collection_filter = QComboBox()
        self.collection_filter.setProperty("userDataLabels", True)
        self.collection_filter.setMinimumContentsLength(15)
        self.collection_filter.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.collection_filter.addItem("Todas as coleções", None)
        self.collection_filter.currentIndexChanged.connect(self.apply_filters)
        library_layout.addWidget(self.collection_filter)
        library_layout.addWidget(button("Coleções", lambda: self.open_dialog(CollectionsDialog), icon="collections"))
        self.duplicates_button = button("Duplicatas", self.show_duplicates)
        library_layout.addWidget(self.duplicates_button)
        library_layout.addWidget(button("Atualizar", self.refresh_library))
        header.addWidget(self.library_toolbar)
        self.filter_button = button("Filtros", self.open_filters)
        header.addWidget(self.filter_button)
        content.addLayout(header)
        self.toolbar = QWidget()
        toolbar = QHBoxLayout(self.toolbar)
        toolbar.setContentsMargins(0, 0, 0, 0)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Filtrar por artista, categoria ou tag…")
        self.query.setAccessibleName("Filtrar resultados")
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
        self.hide_saved = QCheckBox("Ocultar artes já guardadas")
        self.hide_saved.setChecked(True)
        self.hide_saved.toggled.connect(self.apply_filters)
        toolbar.addWidget(self.hide_saved)
        content.addWidget(self.toolbar)
        self.pages = QStackedWidget()
        self.grid = ArtworkGrid()
        self.grid.setObjectName("artGrid")
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setLayoutMode(QListView.LayoutMode.Batched)
        self.grid.setBatchSize(80)
        self.grid.setUniformItemSizes(True)
        self.grid.setGridSize(QSize(410, 485))
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
        empty_layout.setContentsMargins(0, 8, 0, 0)
        empty_layout.setSpacing(16)
        self.search_cover = QWidget()
        self.search_cover.setObjectName("searchCover")
        cover = QHBoxLayout(self.search_cover)
        cover.setContentsMargins(38, 22, 38, 22)
        cover.setSpacing(24)
        introduction = QVBoxLayout()
        introduction.setSpacing(10)
        introduction.addStretch()
        introduction.addWidget(label("Encontre sua próxima referência.", "coverTitle"))
        introduction.addWidget(label("Busque por tags ou combine categorias e fontes em Busca avançada.", "coverCopy"))
        introduction.addStretch()
        cover.addLayout(introduction, 1)
        cover_mark = QLabel()
        cover_mark.setPixmap(nav_icon("brand").pixmap(200, 200))
        cover.addWidget(cover_mark)
        empty_layout.addWidget(self.search_cover)
        self.empty_title = label("", "emptyTitle")
        self.empty_message = label("", "muted")
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_message)
        self.reset_button = button("Limpar filtros", self.reset_filters, icon="close")
        empty_layout.addWidget(self.reset_button, 0, Qt.AlignmentFlag.AlignLeft)
        empty_layout.addStretch(1)
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
        self.actions = QWidget()
        self.actions.setObjectName("actions")
        actions = QHBoxLayout(self.actions)
        actions.setContentsMargins(10, 7, 8, 7)
        actions.setSpacing(7)
        actions.addWidget(label("Tamanho", "muted"))
        self.thumbnail_size = QSlider(Qt.Orientation.Horizontal)
        self.thumbnail_size.setRange(180, 720)
        self.thumbnail_size.setValue(self.preferences.value("artwork_width", 410, type=int))
        self.thumbnail_size.setFixedWidth(80)
        self.thumbnail_size.setToolTip("Tamanho das artes")
        self.thumbnail_size.setAccessibleName("Tamanho das artes")
        self.thumbnail_size.setSingleStep(40)
        self.thumbnail_size.setPageStep(90)
        self.thumbnail_size.valueChanged.connect(self.resize_thumbnails)
        actions.addWidget(self.thumbnail_size)
        self.grid.set_thumbnail_width(self.thumbnail_size.value())
        self.inspector_toggle = button("Detalhes", self.toggle_inspector, icon="panel")
        self.inspector_toggle.setCheckable(True)
        self.inspector_toggle.setChecked(self.preferences.value("artwork_details", False, type=bool))
        actions.addWidget(self.inspector_toggle)
        actions.addSpacing(8)
        self.selection_label = label("Selecione uma arte", "muted")
        actions.addWidget(self.selection_label, 1)
        self.save_collection = QComboBox()
        self.save_collection.setProperty("userDataLabels", True)
        self.save_collection.setToolTip("Coleção usada ao guardar")
        self.save_collection.setMinimumContentsLength(10)
        self.save_collection.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.save_collection.addItem("Sem coleção", None)
        actions.addWidget(self.save_collection)
        self.open_button = button("Abrir arte", self.open_selected, icon="open")
        self.save_button = button("Guardar", self.save_selected, True)
        self.download_button = button("Baixar", lambda: self.download(self.selected()))
        for widget in [self.open_button, self.save_button, self.download_button]:
            actions.addWidget(widget)
        content.addWidget(self.actions)
        outer.addWidget(workspace, 1)
        self.language = self.translations.language
        self.disk_status = label("", "muted")
        self.statusBar().addPermanentWidget(self.disk_status)
        self.statusBar().showMessage("Conectando à biblioteca local…")
        for key, callback in [("Ctrl+N", self.open_search), ("Ctrl+F", self.focus_search), ("Ctrl+,", lambda: self.open_dialog(SettingsDialog))]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
        self.apply_filters()
        apply_theme(QApplication.instance(), self.theme)
        self.refresh_configuration()
        self.refresh_library()

    def resize_thumbnails(self, size):
        self.preferences.setValue("artwork_width", size)
        self.grid.set_thumbnail_width(size)

    def toggle_inspector(self, *_):
        self.preferences.setValue("artwork_details", self.inspector_toggle.isChecked())
        self.update_inspector()

    def update_inspector(self):
        self.inspector.setVisible(self.inspector_toggle.isChecked() and self.pages.currentWidget() == self.grid)

    def focus_search(self):
        if self.quick_search.isVisible():
            self.quick_search.setFocus()
            self.quick_search.selectAll()
        elif self.query.isVisible():
            self.query.setFocus()

    def reset_filters(self):
        self.filters = {}
        self.preferences.setValue("filters", "{}")
        for control in (self.query, self.source_filter, self.collection_filter, self.hide_saved):
            control.blockSignals(True)
        self.query.clear()
        self.source_filter.setCurrentIndex(0)
        self.collection_filter.setCurrentIndex(0)
        self.hide_saved.setChecked(False)
        for control in (self.query, self.source_filter, self.collection_filter, self.hide_saved):
            control.blockSignals(False)
        self.apply_filters()

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

    def change_language(self, language):
        self.language = language
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
        previous_filter = self.collection_filter.currentData()
        self.collections = data.get("collections", [])
        for box, title in [(self.save_collection, "Sem coleção"), (self.collection_filter, "Todas as coleções")]:
            selected = box.currentData()
            box.blockSignals(True)
            box.clear()
            box.addItem(title, None)
            for item in self.collections:
                box.addItem(item["name"], item["id"])
            box.setCurrentIndex(max(0, box.findData(selected)))
            box.blockSignals(False)
        if self.collection_filter.currentData() != previous_filter:
            self.apply_filters()

    def set_stats(self, data):
        total, disk = data.get("total", 0), data.get("disk_mb", 0)
        self.disk_status.setText(f"{total} artes  ·  {disk} MB")
        rows = [("Artes no banco", total), ("Downloads (MB)", disk)]
        for name, key in [("Fonte", "by_source"), ("Categoria", "by_category"), ("Avaliação", "by_rating")]:
            rows.extend((f"{name} / {title}", value) for title, value in (data.get(key) or {}).items())
        self.stats.setRowCount(len(rows))
        for row, (title, value) in enumerate(rows):
            self.stats.setItem(row, 0, QTableWidgetItem(str(title)))
            self.stats.setItem(row, 1, QTableWidgetItem(str(value)))

    def clear_result_query(self):
        self.query.blockSignals(True)
        self.query.clear()
        self.query.blockSignals(False)
        self.source_filter.blockSignals(True)
        self.source_filter.setCurrentIndex(0)
        self.source_filter.blockSignals(False)

    def switch_section(self, section):
        if self.section != section:
            self.clear_result_query()
            self.grid.clearSelection()
        self.section = section
        self.nav[section].setChecked(True)
        self.title.setText({"search": "Explorar", "gallery": "Minha galeria", "stats": "Estatísticas"}[section])
        if section != "search":
            self.refresh_library()
        self.apply_filters()

    def apply_filters(self, *_):
        in_search = self.section == "search"
        in_gallery = self.section == "gallery"
        self.command_bar.setVisible(in_search)
        self.progress_panel.setVisible(in_search and self.search_reply is not None)
        self.library_toolbar.setVisible(in_gallery)
        self.hide_saved.setVisible(in_search)
        if self.section == "stats":
            self.pages.setCurrentWidget(self.stats)
            self.count.hide()
            self.toolbar.hide()
            self.filter_button.hide()
            self.actions.hide()
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
        if visible != self.model.posts:
            selected = {uid(post) for post in self.selected()}
            current = self.grid.currentIndex().data(Qt.ItemDataRole.UserRole)
            current_id = uid(current) if current else None
            selection_model = self.grid.selectionModel()
            selection_model.blockSignals(True)
            self.model.replace(visible)
            selection = QItemSelection()
            for row, post in enumerate(visible):
                if uid(post) in selected:
                    index = self.model.index(row, 0)
                    selection.select(index, index)
                    if uid(post) == current_id:
                        selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
            selection_model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            selection_model.blockSignals(False)

        self.count.setText(f"{len(visible)} / {len(posts)}")
        self.count.setVisible(bool(posts))
        self.pages.setCurrentWidget(self.grid if visible else self.empty)
        self.toolbar.setVisible(bool(posts))
        self.filter_button.setVisible(bool(posts))
        if not visible:
            introductory = in_search and not posts and not self.search_attempted
            self.search_cover.setVisible(introductory)
            self.empty_title.setVisible(not introductory)
            self.empty_message.setVisible(not introductory)
            self.reset_button.setVisible(bool(posts))
            if self.search_reply:
                title, message = "Buscando artes…", "Os resultados aparecem conforme chegam."
            elif posts:
                title, message = "Nenhuma arte com esses filtros", "Limpe os filtros para ver os resultados carregados."
            elif in_search:
                title, message = "Sem resultados", "Experimente outras tags ou fontes."
            else:
                title, message = "Sua galeria está vazia", "Use Guardar em uma arte de Explorar para trazê-la para cá."
            self.empty_title.setText(title)
            self.empty_message.setText(message)
        self.update_inspector()
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
        dialog.tags.setText(self.quick_search.text())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.search_options = dialog.values()
            self.quick_search.setText(self.search_options["tags"])
            self.preferences.setValue("search", json.dumps(self.search_options))
            self.start_search()

    def start_search(self):
        self.search_generation += 1
        if self.search_reply:
            self.search_reply.abort()
        generation = self.search_generation
        self.switch_section("search")
        self.search_attempted = True
        self.search_posts = []
        self.clear_result_query()
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
            self.apply_filters()
            self.new_search.setEnabled(True)
            self.empty_search.setEnabled(True)
            if error:
                self.error(error)
            elif cancelled:
                self.notify("Busca cancelada. Os resultados recebidos foram mantidos.")
        self.search_reply = self.api.search(body, event, finished)
        self.apply_filters()

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
        self.actions.setVisible(self.pages.currentWidget() == self.grid)
        self.selection_label.setText(f"{count} selecionada(s)" if count else "")
        self.open_button.setEnabled(count == 1)
        self.save_button.setEnabled(count > 0)
        self.download_button.setEnabled(count > 0)
        self.save_collection.setEnabled(count > 0)

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
