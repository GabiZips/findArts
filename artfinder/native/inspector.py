"""Artwork details panel for the native library workspace."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget
from .models import media_type, rating, uid
from .widgets import button, label


class Inspector(QScrollArea):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.post = None
        self.setObjectName("inspector")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(230)
        self.setMaximumWidth(330)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("inspectorBody")
        self.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        layout.addWidget(label("Detalhes", "sectionTitle"))
        self.preview = QLabel()
        self.preview.setObjectName("inspectorPreview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedHeight(190)
        self.preview.setMinimumWidth(0)
        self.preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.preview)
        self.artist = label("Selecione uma arte", "sectionTitle")
        self.artist.setProperty("userDataLabels", True)
        layout.addWidget(self.artist)
        self.open = button("Abrir", window.open_selected)
        layout.addWidget(self.open)
        self.metadata = QWidget()
        form = QFormLayout(self.metadata)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(12)
        self.values = {}
        for key, title in [("source", "Fonte"), ("format", "Formato"), ("size", "Dimensões"), ("score", "Score"), ("rating", "Conteúdo")]:
            value = label("")
            value.setProperty("userDataLabels", True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.values[key] = value
            form.addRow(label(title, "muted"), value)
        layout.addWidget(self.metadata)
        self.tags = label("", "muted")
        self.tags.setMaximumHeight(120)
        self.tags.setProperty("userDataLabels", True)
        self.tags.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.tags)
        layout.addStretch()
        window.thumbnails.changed.connect(self.refresh_preview)
        self.set_posts([])

    def set_posts(self, posts):
        self.post = posts[0] if len(posts) == 1 else None
        self.open.setEnabled(self.post is not None)
        self.metadata.setVisible(self.post is not None)
        self.tags.clear()
        if self.post is None:
            self.artist.setText("Selecione uma arte" if not posts else f"{len(posts)} selecionada(s)")
            self.preview.clear()
            self.preview.setText("Prévia")
            return
        post = self.post
        self.artist.setText(post.get("artist") or "Artista desconhecido")
        width, height = post.get("width"), post.get("height")
        values = {"source": post.get("source", ""), "format": media_type(post).upper(),
                  "size": f"{width} × {height}" if width and height else "—",
                  "score": str(post.get("score") or 0), "rating": rating(post).upper()}
        for key, value in values.items():
            self.values[key].setText(value)
        tags = post.get("tags") or ""
        self.tags.setText(" ".join(tags)[:600] if isinstance(tags, list) else str(tags)[:600])
        self.refresh_preview()

    def refresh_preview(self):
        if self.post is None:
            return
        self.preview.clear()
        protected = self.window.blur and rating(self.post) == "nsfw" and uid(self.post) not in self.window.revealed
        if protected:
            self.preview.setText("NSFW\nAbrir para revelar")
            return
        image = self.window.thumbnails.get(self.post)
        if image and not image.isNull():
            self.preview.setPixmap(image.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation))
        else:
            self.preview.setText("Carregando…" if image is None else "Prévia indisponível")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "preview"):
            self.preview.setFixedHeight(120 if self.height() < 500 else 190)
        self.refresh_preview()
