"""Native dialogs for search, categories, collections and local settings."""
import re
import unicodedata
from urllib.parse import quote

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QGridLayout, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QScrollArea, QSpinBox, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)
from .widgets import button, label


def scroll(content):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(content)
    area.setFrameShape(QScrollArea.Shape.NoFrame)
    return area


def check_list(values, selected):
    widget = QListWidget()
    widget.setMinimumHeight(160)
    for key, title in values:
        item = QListWidgetItem(title, widget)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if key in selected else Qt.CheckState.Unchecked)
    return widget


def checked(widget):
    return [widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(widget.count()) if widget.item(i).checkState() == Qt.CheckState.Checked]


class SearchDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle("Nova busca")
        self.resize(640, 700)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Nova busca", "dialogTitle"))
        layout.addWidget(label("Escolha categorias e fontes ou informe tags para uma busca avulsa.", "muted"))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtrar categorias…")
        layout.addWidget(self.filter)
        self.categories = check_list([(key, f"{cat.get('group', 'Geral')} / {cat.get('label', key)}") for key, cat in window.categories.items()], window.search_options.get("categories", []))
        self.filter.textChanged.connect(lambda text: [self.categories.item(i).setHidden(text.casefold() not in self.categories.item(i).text().casefold()) for i in range(self.categories.count())])
        layout.addWidget(self.categories, 1)
        form = QFormLayout()
        self.tags = QLineEdit(window.search_options.get("tags", ""))
        self.tags.setPlaceholderText("Tags avulsas; separe consultas com ponto e vírgula")
        form.addRow("Tags", self.tags)
        self.pages = QSpinBox()
        self.pages.setRange(1, 50)
        self.pages.setValue(window.search_options.get("pages", 1))
        form.addRow("Páginas por fonte", self.pages)
        layout.addLayout(form)
        layout.addWidget(label("Fontes", "sectionTitle"))
        self.sources = check_list([(s, s) for s in window.sources], window.search_options.get("sources", window.sources))
        layout.addWidget(self.sources)
        if window.unavailable_sources:
            layout.addWidget(label("Configure outras fontes em Configurações → Fontes e credenciais.", "muted"))
        self.error = label("")
        self.error.setObjectName("error")
        layout.addWidget(self.error)
        actions = QHBoxLayout()
        actions.addWidget(button("Gerenciar categorias", lambda: (self.reject(), window.open_categories())))
        actions.addStretch()
        actions.addWidget(button("Cancelar", self.reject))
        actions.addWidget(button("Buscar", self.submit, True))
        layout.addLayout(actions)

    def submit(self):
        if not checked(self.categories) and not self.tags.text().strip():
            self.error.setText("Selecione uma categoria ou informe tags.")
            return
        if not checked(self.sources):
            self.error.setText("Selecione ao menos uma fonte.")
            return
        if self.pages.value() > 20 and QMessageBox.question(self, "Busca extensa", "Esta busca pode demorar e atingir os limites das fontes. Continuar?") != QMessageBox.StandardButton.Yes:
            return
        self.accept()

    def values(self):
        return {"categories": checked(self.categories), "sources": checked(self.sources), "tags": self.tags.text().strip(), "pages": self.pages.value()}


class FiltersDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle("Filtros")
        self.resize(600, 620)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Refinar resultados", "dialogTitle"))
        layout.addWidget(label("Os filtros são aplicados às artes carregadas, sem uma nova busca.", "muted"))
        self.groups = {}
        for key, title, values in [
            ("ratings", "Classificação", [("sfw", "SFW"), ("sensitive", "Sensível"), ("nsfw", "NSFW")]),
            ("media", "Mídia", [("image", "Imagem"), ("gif", "GIF"), ("webp", "WebP"), ("video", "Vídeo")]),
            ("assessments", "Avaliação", [("none", "Não avaliadas"), ("usar", "Usar"), ("talvez", "Talvez"), ("depois", "Rever depois"), ("nao", "Não gostei")]),
        ]:
            layout.addWidget(label(title, "sectionTitle"))
            row = QHBoxLayout()
            self.groups[key] = []
            for value, text in values:
                box = QCheckBox(text)
                box.setChecked(value in window.filters.get(key, [v[0] for v in values]))
                row.addWidget(box)
                self.groups[key].append((value, box))
            layout.addLayout(row)
        form = QFormLayout()
        self.score = QSpinBox()
        self.score.setRange(0, 10000000)
        self.score.setValue(window.filters.get("score", 0))
        form.addRow("Score mínimo", self.score)
        self.period = QComboBox()
        for title, days in [("Qualquer período", 0), ("7 dias", 7), ("30 dias", 30), ("3 meses", 90), ("1 ano", 365)]:
            self.period.addItem(title, days)
        self.period.setCurrentIndex(max(0, self.period.findData(window.filters.get("days", 0))))
        form.addRow("Período", self.period)
        self.blacklist = QPlainTextEdit(window.filters.get("blacklist", ""))
        self.blacklist.setPlaceholderText("Tags separadas por vírgula")
        self.blacklist.setMaximumHeight(90)
        form.addRow("Excluir tags", self.blacklist)
        layout.addLayout(form)
        layout.addWidget(label("Artes sem data informada continuam visíveis no filtro de período.", "muted"))
        layout.addStretch()
        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        actions.accepted.connect(self.accept)
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)

    def values(self):
        values = {key: [value for value, box in boxes if box.isChecked()] for key, boxes in self.groups.items()}
        return {**values, "score": self.score.value(), "days": self.period.currentData(), "blacklist": self.blacklist.toPlainText()}


class CategoryDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.current = None
        self.setWindowTitle("Categorias")
        self.resize(940, 720)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Suas categorias", "dialogTitle"))
        split = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filtrar categorias…")
        left_layout.addWidget(self.search)
        self.list = QListWidget()
        left_layout.addWidget(self.list)
        left_layout.addWidget(button("Nova categoria", self.clear))
        split.addWidget(left)
        editor = QWidget()
        form = QFormLayout(editor)
        self.name, self.key, self.group = QLineEdit(), QLineEdit(), QLineEdit()
        self.tags = QPlainTextEdit()
        self.tags.setMaximumHeight(90)
        self.tags.setPlaceholderText("Consultas separadas por ponto e vírgula")
        self.favorite = QCheckBox("Favoritar categoria")
        for caption, widget in [("Nome", self.name), ("Chave", self.key), ("Grupo", self.group), ("Tags principais", self.tags), ("", self.favorite)]:
            form.addRow(caption, widget)
        self.overrides = {}
        for source in ["danbooru", "gelbooru", "safebooru", "e621", "pixiv", "tumblr", "bluesky", "deviantart"]:
            field = QLineEdit()
            field.setPlaceholderText("Opcional: consultas específicas desta fonte")
            self.overrides[source] = field
            form.addRow(source, field)
        self.error = label("")
        form.addRow(self.error)
        actions = QHBoxLayout()
        self.save_button = button("Salvar categoria", self.save, True)
        actions.addWidget(self.save_button)
        actions.addWidget(button("Excluir", self.remove))
        form.addRow(actions)
        split.addWidget(scroll(editor))
        split.setSizes([280, 600])
        layout.addWidget(split)
        layout.addWidget(button("Fechar", self.accept))
        self.list.currentItemChanged.connect(self.select)
        self.search.textChanged.connect(self.populate)
        self.populate()

    def populate(self, *_):
        self.list.clear()
        query = self.search.text().casefold()
        for key, cat in self.window.categories.items():
            if query not in f"{key} {cat.get('label')} {cat.get('group')} {cat.get('tags')}".casefold():
                continue
            item = QListWidgetItem(f"{cat.get('label', key)}\n{cat.get('group', 'Geral')}", self.list)
            item.setData(Qt.ItemDataRole.UserRole, key)

    def clear(self):
        self.list.clearSelection()
        self.current = None
        self.key.setEnabled(True)
        for field in [self.name, self.key, self.group, *self.overrides.values()]:
            field.clear()
        self.tags.clear()
        self.favorite.setChecked(False)
        self.error.clear()

    def select(self, item, *_):
        if not item:
            return
        self.current = item.data(Qt.ItemDataRole.UserRole)
        cat = self.window.categories[self.current]
        self.key.setText(self.current)
        self.key.setEnabled(False)
        self.name.setText(cat.get("label", self.current))
        self.group.setText(cat.get("group", "Geral"))
        self.tags.setPlainText(cat.get("tags", ""))
        self.favorite.setChecked(cat.get("favorite", False))
        for source, field in self.overrides.items():
            raw = cat.get("source_tags", {}).get(source, [])
            field.setText("; ".join(raw) if isinstance(raw, list) else str(raw))
        self.error.clear()

    def save(self):
        key = self.key.text().strip()
        if not key:
            key = re.sub(r"[^a-z0-9_-]+", "_", unicodedata.normalize("NFKD", self.name.text()).encode("ascii", "ignore").decode().lower()).strip("_")
        if not key or not self.name.text().strip() or not self.tags.toPlainText().strip():
            self.error.setText("Preencha nome, chave e tags principais.")
            return
        if not self.current and key in self.window.categories:
            self.error.setText("Esta chave já existe. Selecione a categoria para editá-la.")
            return
        old = self.window.categories.get(self.current, {})
        data = {"key": key, "label": self.name.text().strip(), "group": self.group.text().strip() or "Geral", "tags": self.tags.toPlainText(),
                "favorite": self.favorite.isChecked(), "color": old.get("color", "#a594ee"), "emoji": old.get("emoji", "🎨"),
                "source_tags": {source: [q.strip() for q in field.text().split(";") if q.strip()] for source, field in self.overrides.items()},
                "replace_source_tags": True, "auto_map": False}
        self.save_button.setEnabled(False)
        def saved(result):
            self.save_button.setEnabled(True)
            self.window.categories[result["key"]] = result["category"]
            self.populate()
            self.clear()
            self.window.notify("Categoria salva.")
        def failed(message):
            self.save_button.setEnabled(True)
            self.error.setText(message)
        self.window.api.request("/api/categories", saved, method="POST", data=data, error=failed)

    def remove(self):
        key = self.current
        if not key or QMessageBox.question(self, "Excluir categoria", "Excluir esta categoria? As artes guardadas serão mantidas.") != QMessageBox.StandardButton.Yes:
            return
        def removed(_):
            self.window.categories.pop(key, None)
            self.populate()
            self.clear()
        self.window.api.request("/api/categories/" + quote(key, safe=""), removed, method="DELETE", error=self.error.setText)


class CollectionsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Coleções")
        self.resize(480, 440)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Organize sua galeria", "dialogTitle"))
        self.list = QListWidget()
        layout.addWidget(self.list)
        row = QHBoxLayout()
        row.addWidget(button("Nova", self.create))
        row.addWidget(button("Renomear", self.rename))
        row.addWidget(button("Excluir", self.remove))
        layout.addLayout(row)
        self.error = label("")
        layout.addWidget(self.error)
        layout.addWidget(button("Fechar", self.accept))
        self.refresh()

    def refresh(self, *_):
        def loaded(data):
            self.window.set_collections(data)
            self.list.clear()
            for collection in data.get("collections", []):
                item = QListWidgetItem(collection["name"], self.list)
                item.setData(Qt.ItemDataRole.UserRole, collection["id"])
        self.window.api.request("/api/collections", loaded, error=self.error.setText)

    def create(self):
        name, ok = QInputDialog.getText(self, "Nova coleção", "Nome")
        if ok and name.strip():
            self.window.api.request("/api/collections", self.refresh, method="POST", data={"name": name}, error=self.error.setText)

    def rename(self):
        item = self.list.currentItem()
        if not item:
            return
        name, ok = QInputDialog.getText(self, "Renomear coleção", "Nome", text=item.text())
        if ok and name.strip():
            self.window.api.request(f"/api/collections/{item.data(Qt.ItemDataRole.UserRole)}", self.refresh, method="PATCH", data={"name": name}, error=self.error.setText)

    def remove(self):
        item = self.list.currentItem()
        if item and QMessageBox.question(self, "Excluir coleção", "Excluir a coleção? As artes serão mantidas na galeria.") == QMessageBox.StandardButton.Yes:
            self.window.api.request(f"/api/collections/{item.data(Qt.ItemDataRole.UserRole)}", self.refresh, method="DELETE", error=self.error.setText)


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.fields = {}
        self.setWindowTitle("Configurações")
        self.resize(720, 670)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Configurações", "dialogTitle"))
        tabs = QTabWidget()
        layout.addWidget(tabs)
        from .themes import THEMES
        appearance = QWidget()
        appearance_layout = QVBoxLayout(appearance)
        appearance_layout.addWidget(label("Tema do aplicativo", "sectionTitle"))
        appearance_layout.addWidget(label("Escolha as cores da interface. A mudança é aplicada na hora e salva automaticamente.", "muted"))
        self.theme_selector = QComboBox()
        self.theme_selector.setProperty("userDataLabels", True)
        for key, theme in THEMES.items():
            self.theme_selector.addItem(window.translations.text(theme["name"]), key)
        self.theme_selector.setCurrentIndex(self.theme_selector.findData(window.theme))
        self.theme_selector.currentIndexChanged.connect(lambda _: window.set_theme(self.theme_selector.currentData()))
        # Keep a single selection model for preference changes and preview buttons.
        self.theme_selector.hide()
        self.theme_selector.setParent(appearance)
        from .appearance import ThemePreview
        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_cards = {}
        previews = QGridLayout()
        previews.setSpacing(16)
        for index, (key, theme) in enumerate(THEMES.items()):
            card = ThemePreview(key, window.translations.text(theme["name"]))
            card.setChecked(key == window.theme)
            self.theme_group.addButton(card)
            self.theme_cards[key] = card
            card.clicked.connect(lambda checked=False, key=key: self.theme_selector.setCurrentIndex(self.theme_selector.findData(key)))
            previews.addWidget(card, index // 2, index % 2)
        self.theme_selector.currentIndexChanged.connect(
            lambda _: self.theme_cards[self.theme_selector.currentData()].setChecked(True))
        appearance_layout.addLayout(previews)
        appearance_layout.addStretch()
        tabs.addTab(scroll(appearance), "Aparência")
        general = QWidget()
        general_layout = QFormLayout(general)
        self.language = QComboBox()
        self.language.setProperty("userDataLabels", True)
        self.language.addItem("Português", "pt-BR")
        self.language.addItem("English", "en")
        self.language.setCurrentIndex(max(0, self.language.findData(window.language)))
        self.language.currentIndexChanged.connect(lambda _: window.change_language(self.language.currentData()))
        general_layout.addRow(label("Idioma"), self.language)
        self.blur_box = QCheckBox("Ocultar prévias NSFW")
        self.blur_box.setChecked(window.blur)
        self.blur_box.toggled.connect(window.set_blur)
        general_layout.addRow(self.blur_box)
        tabs.addTab(general, "Geral")
        sources = QWidget()
        self.form = QFormLayout(sources)
        self.form.addRow(label("Os valores salvos ficam no cofre do sistema e não são exibidos. Deixe em branco para manter.", "muted"))
        tabs.addTab(scroll(sources), "Fontes e credenciais")
        self.error = label("Carregando fontes…")
        self.form.addRow(self.error)
        self.save_button = button("Salvar credenciais", self.save_credentials, True)
        self.save_button.setEnabled(False)
        self.form.addRow(self.save_button)
        window.api.request("/api/settings/credentials", self.credentials_loaded, error=self.error.setText)
        pairing = QWidget()
        pairing_layout = QVBoxLayout(pairing)
        pairing_layout.addWidget(label("Parear PC e celular", "sectionTitle"))
        pairing_layout.addWidget(label("Use a mesma rede Wi-Fi. O código é temporário e inclui somente os itens selecionados.", "muted"))
        self.pair_categories = QCheckBox("Categorias e tags")
        self.pair_categories.setChecked(True)
        self.pair_credentials = QCheckBox("Credenciais das fontes")
        pairing_layout.addWidget(self.pair_categories)
        pairing_layout.addWidget(self.pair_credentials)
        pairing_layout.addWidget(button("Gerar código de pareamento", self.pair))
        self.pair_options = QComboBox()
        pairing_layout.addWidget(self.pair_options)
        self.code = QPlainTextEdit()
        self.code.setReadOnly(True)
        pairing_layout.addWidget(self.code)
        pairing_layout.addWidget(button("Copiar código", lambda: QApplication.clipboard().setText(self.code.toPlainText())))
        self.pair_status = label("")
        pairing_layout.addWidget(self.pair_status)
        self.pair_options.currentIndexChanged.connect(lambda _: self.code.setPlainText(self.pair_options.currentData() or ""))
        tabs.addTab(pairing, "Celular")
        files = QWidget()
        files_layout = QVBoxLayout(files)
        files_layout.addWidget(label("Arquivos e manutenção", "sectionTitle"))
        files_layout.addWidget(button("Abrir pasta de downloads", window.open_downloads))
        files_layout.addWidget(button("Abrir pasta de dados", window.open_data))
        files_layout.addWidget(button("Sincronizar banco com o disco", self.sync))
        files_layout.addWidget(label("A sincronização remove registros de arquivos que já foram apagados fora do aplicativo.", "muted"))
        files_layout.addStretch()
        tabs.addTab(files, "Arquivos")
        layout.addWidget(button("Fechar", self.accept))

    def credentials_loaded(self, data):
        self.error.setText(data.get("storage_error") or "")
        for group in data.get("groups", []):
            self.form.insertRow(self.form.rowCount() - 2, label(group["source"], "sectionTitle"))
            for field in group["fields"]:
                edit = QLineEdit()
                edit.setEchoMode(QLineEdit.EchoMode.Password)
                edit.setPlaceholderText("Configurado — em branco para manter" if field["configured"] else "Não configurado")
                clear = QCheckBox("Remover")
                clear.setEnabled(field["configured"])
                row = QHBoxLayout()
                row.addWidget(edit)
                row.addWidget(clear)
                self.fields[field["key"]] = (edit, clear)
                self.form.insertRow(self.form.rowCount() - 2, field["key"], row)
        self.save_button.setEnabled(True)

    def save_credentials(self):
        values = {key: edit.text().strip() for key, (edit, clear) in self.fields.items() if edit.text().strip() and not clear.isChecked()}
        removals = [key for key, (_, clear) in self.fields.items() if clear.isChecked()]
        if removals and QMessageBox.question(self, "Remover credenciais", "Remover as credenciais marcadas do cofre?") != QMessageBox.StandardButton.Yes:
            return
        self.save_button.setEnabled(False)
        def saved(_):
            for edit, clear in self.fields.values():
                edit.clear()
            self.window.refresh_configuration()
            self.window.notify("Credenciais salvas no cofre do sistema.")
            self.accept()
        def failed(message):
            self.error.setText(message)
            self.save_button.setEnabled(True)
        self.window.api.request("/api/settings/credentials", saved, method="POST", data={"values": values, "clear": removals}, error=failed)

    def pair(self):
        def created(data):
            self.pair_options.clear()
            for option in data.get("options", []):
                self.pair_options.addItem(option.get("address") or option.get("host") or "Rede local", option["code"])
            self.pair_status.setText("Código válido por cinco minutos. Abra Parear no celular.")
        self.window.api.request("/api/pairing/create", created, method="POST", data={"categories": self.pair_categories.isChecked(), "credentials": self.pair_credentials.isChecked()}, error=self.pair_status.setText)

    def sync(self):
        if QMessageBox.question(self, "Sincronizar banco", "Remover do banco os registros de arquivos que não existem mais?") == QMessageBox.StandardButton.Yes:
            self.window.api.request("/api/sync-db", lambda result: (self.window.notify(result.get("message", "Sincronizado.")), self.window.refresh_library()), method="POST")
