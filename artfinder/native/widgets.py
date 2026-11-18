"""Virtualized artwork grid and native image/animation/video viewer."""
from collections import OrderedDict

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImageReader, QKeySequence, QMovie, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QListView, QDialog, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QPushButton,
    QSlider, QStackedWidget, QStyledItemDelegate, QStyle, QVBoxLayout, QWidget,
)

from .themes import THEMES
from .studio import nav_icon
from .models import media_type, rating, uid


def button(text, callback=None, primary=False, *, icon=None):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.setProperty("primary", primary)
    icons = {
        "Nova busca": "plus", "Criar uma busca": "search", "Buscar": "magnifier", "Filtros": "filter",
        "Atualizar": "refresh", "Abrir": "open", "Guardar": "save", "Baixar": "download",
        "Fechar": "close", "Cancelar": "close", "Salvar categoria": "check",
        "Salvar credenciais": "check", "Duplicatas": "gallery",
    }
    icon = icon or icons.get(text)
    if icon:
        theme = QApplication.instance().property("theme") or "night"
        color = THEMES[theme]["ink" if primary else "text"]
        widget.setProperty("iconName", icon)
        widget.setIcon(nav_icon(icon, color))
        widget.setIconSize(QSize(19, 19))
    if callback is not None:
        widget.clicked.connect(callback)
    return widget


def label(text, name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


def pixmap_from_bytes(raw, size=QSize(800, 800)):
    buffer = QBuffer()
    buffer.setData(QByteArray(raw))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    reader.setAutoTransform(True)
    original = reader.size()
    if original.isValid() and size.isValid() and (original.width() > size.width() or original.height() > size.height()):
        reader.setScaledSize(original.scaled(size, Qt.AspectRatioMode.KeepAspectRatio))
    return QPixmap.fromImage(reader.read())


class Thumbnails(QObject):
    changed = Signal()

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api, self.cache, self.pending, self.queue = api, OrderedDict(), set(), []
        self.active = 0

    def get(self, post):
        key = self.api.media_path(post)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        if key not in self.pending:
            self.pending.add(key)
            self.queue.append(key)
            self.pump()
        return None

    def pump(self):
        while self.queue and self.active < 6:
            key = self.queue.pop(0)
            self.active += 1
            self.api.request(key, lambda raw, key=key: self.complete(key, pixmap_from_bytes(raw)),
                             binary=True, error=lambda _message, key=key: self.complete(key, QPixmap()))

    def complete(self, key, image):
        self.active -= 1
        self.pending.discard(key)
        self.cache[key] = image
        while len(self.cache) > 160:
            self.cache.popitem(last=False)
        self.changed.emit()
        self.pump()


class ArtworkGrid(QListView):
    """Fit complete columns to the viewport while retaining virtualized items."""
    thumbnail_width = 410

    def set_thumbnail_width(self, width):
        self.thumbnail_width = width
        self.reflow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()

    def reflow(self):
        available = max(1, self.viewport().width() - 18)
        columns = max(1, round(available / self.thumbnail_width))
        width = available // columns
        size = QSize(width, min(690, round(width * 1.05)) + 55)
        if size != self.gridSize():
            self.setGridSize(size)
            self.doItemsLayout()


class ArtworkDelegate(QStyledItemDelegate):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window

    def sizeHint(self, option, index):
        return self.parent().gridSize()

    def paint(self, painter, option, index):
        post = index.data(Qt.ItemDataRole.UserRole)
        if not post:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = option.rect.adjusted(6, 5, -6, -5)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        colors = THEMES[self.window.theme]
        painter.setPen(QPen(QColor(colors["accent" if selected else "border"]), 2 if selected else 1))
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.setBrush(QColor(colors["selected" if selected else "hover" if hovered else "surface"]))
        painter.drawRoundedRect(bounds, 11, 11)
        image_rect = bounds.adjusted(3, 3, -3, -53)
        painter.setBrush(QColor(colors["bg"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(image_rect, 8, 8)
        protected = self.window.blur and rating(post) == "nsfw" and uid(post) not in self.window.revealed
        image = None if protected else self.window.thumbnails.get(post)
        if image and not image.isNull():
            scaled = image.scaled(image_rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.save()
            clip = QPainterPath()
            clip.addRoundedRect(image_rect, 8, 8)
            painter.setClipPath(clip)
            painter.drawPixmap(image_rect.center().x() - scaled.width() // 2, image_rect.center().y() - scaled.height() // 2, scaled)
            painter.restore()
        else:
            painter.setPen(QColor(colors["muted"]))
            message = "NSFW\nAbrir para revelar" if protected else "Carregando…" if image is None else "Prévia indisponível"
            painter.drawText(image_rect, Qt.AlignmentFlag.AlignCenter, self.window.translations.text(message))
        title_font = painter.font()
        title_font.setBold(True)
        title_font.setPixelSize(16)
        painter.setFont(title_font)
        painter.setPen(QColor(colors["text"]))
        title = painter.fontMetrics().elidedText(post.get("artist") or "Artista desconhecido", Qt.TextElideMode.ElideRight, bounds.width() - 20)
        painter.drawText(bounds.adjusted(10, bounds.height() - 48, -10, -25), Qt.AlignmentFlag.AlignVCenter, title)
        title_font.setBold(False)
        title_font.setPixelSize(13)
        painter.setFont(title_font)
        painter.setPen(QColor(colors["muted"]))
        source = post.get("source", "")
        kind = media_type(post)
        media = f"  ·  {kind.upper()}" if kind != "image" else ""
        score = post.get("score") or 0
        metadata = painter.fontMetrics().elidedText(f"{source}{media}  ·  {score}", Qt.TextElideMode.ElideRight, bounds.width() - 20)
        painter.drawText(bounds.adjusted(10, bounds.height() - 24, -10, -4), Qt.AlignmentFlag.AlignVCenter, metadata)
        if selected:
            badge = QRect(bounds.left() + 12, bounds.top() + 12, 26, 26)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors["accent"]))
            painter.drawEllipse(badge)
            nav_icon("check", colors["ink"]).paint(painter, badge.adjusted(4, 4, -4, -4))
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QColor(colors["accent"]))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(bounds.adjusted(2, 2, -2, -2), 8, 8)
        painter.restore()


class ImageView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.item = None

    def set_pixmap(self, pixmap, fit=True):
        if self.item is None:
            self.item = self.scene().addPixmap(pixmap)
        else:
            self.item.setPixmap(pixmap)
        self.scene().setSceneRect(self.item.boundingRect())
        if fit:
            self.fit()

    def fit(self):
        if self.item:
            self.fitInView(self.item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        self.zoom(1.2 if event.angleDelta().y() > 0 else 1 / 1.2)
        event.accept()

    def zoom(self, factor):
        scale = self.transform().m11() * factor
        if 0.015 <= scale <= 20:
            self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit()


class Viewer(QDialog):
    def __init__(self, window, posts, index):
        super().__init__(window)
        self.window, self.posts, self.index = window, list(posts), index
        self.generation = 0
        self.reply = self.movie = self.player = self.media_buffer = None
        self.setWindowTitle("Visualizador • ArtFinder")
        self.resize(1120, 800)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(button("‹ Anterior", lambda: self.step(-1)))
        self.caption = label("")
        header.addWidget(self.caption, 1)
        header.addWidget(button("Próxima ›", lambda: self.step(1)))
        header.addWidget(button("Fechar", self.close))
        layout.addLayout(header)
        self.stack = QStackedWidget()
        self.image = ImageView()
        self.message = label("Carregando…")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.message)
        self.stack.addWidget(self.image)
        layout.addWidget(self.stack, 1)
        self.reveal = button("Mostrar imagem", self.show_protected, True)
        layout.addWidget(self.reveal)
        self.video_controls = QWidget()
        controls = QHBoxLayout(self.video_controls)
        self.play_button = button("Reproduzir / pausar", self.toggle_video)
        controls.addWidget(self.play_button)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderMoved.connect(lambda pos: self.player.setPosition(pos) if self.player else None)
        controls.addWidget(self.seek, 1)
        layout.addWidget(self.video_controls)
        tools = QHBoxLayout()
        self.zoom_buttons = []
        for title, callback in [("−", lambda: self.image.zoom(1 / 1.2)), ("Ajustar", self.image.fit), ("+", lambda: self.image.zoom(1.2))]:
            control = button(title, callback)
            self.zoom_buttons.append(control)
            tools.addWidget(control)
        tools.addStretch(1)
        tools.addWidget(button("Ver na fonte", lambda: window.open_source(self.current), icon="open"))
        tools.addWidget(button("Baixar", lambda: window.download([self.current])))
        tools.addWidget(button("Guardar", lambda: window.save(self.current), True))
        self.hide_preview = button("Ocultar imagem", self.hide_protected)
        tools.addWidget(self.hide_preview)
        layout.addLayout(tools)
        for key, offset in [("Left", -1), ("Right", 1)]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda offset=offset: self.step(offset))
        self.finished.connect(self.cleanup)
        self.load()

    @property
    def current(self):
        return self.posts[self.index]

    def cleanup(self, *_):
        self.generation += 1
        if self.reply:
            self.reply.abort()
            self.reply = None
        if self.movie:
            self.movie.stop()
            self.movie.deleteLater()
            self.movie = None
        if self.player:
            self.player.stop()
            self.player.setSourceDevice(None)
        if self.media_buffer:
            self.media_buffer.close()
            self.media_buffer.deleteLater()
            self.media_buffer = None

    def step(self, offset):
        self.index = (self.index + offset) % len(self.posts)
        self.load()

    def load(self):
        self.cleanup()
        post = self.current
        self.caption.setText(f"{self.index + 1} / {len(self.posts)}   {post.get('artist') or 'Artista desconhecido'}   •   {post.get('source', '')}")
        self.stack.setCurrentWidget(self.message)
        protected = self.window.blur and rating(post) == "nsfw" and uid(post) not in self.window.revealed
        self.reveal.setVisible(protected)
        self.hide_preview.setVisible(self.window.blur and rating(post) == "nsfw" and not protected)
        for control in self.zoom_buttons:
            control.setEnabled(False)
        self.video_controls.hide()
        self.message.setText("Conteúdo NSFW oculto. Revele somente se desejar visualizar." if protected else "Carregando…")
        if protected:
            return
        generation = self.generation
        def loaded(raw):
            if generation != self.generation:
                return
            self.reply = None
            if media_type(post) == "video":
                self.load_video(raw)
            else:
                self.load_image(raw)
        def failed(message):
            if generation == self.generation:
                self.reply = None
                self.message.setText("Não foi possível abrir a mídia. " + message)
        self.reply = self.window.api.request(self.window.api.media_path(post, preview=False), loaded, binary=True, error=failed)

    def show_protected(self):
        self.window.revealed.add(uid(self.current))
        self.window.grid.viewport().update()
        self.load()

    def hide_protected(self):
        self.window.revealed.discard(uid(self.current))
        self.window.grid.viewport().update()
        self.load()

    def load_image(self, raw):
        image = pixmap_from_bytes(raw, QSize(4096, 4096))
        if image.isNull():
            self.message.setText("Formato de imagem indisponível. Use ‘Ver na fonte’.")
            return
        self.image.set_pixmap(image)
        self.stack.setCurrentWidget(self.image)
        for control in self.zoom_buttons:
            control.setEnabled(True)
        self.media_buffer = QBuffer(self)
        self.media_buffer.setData(QByteArray(raw))
        self.media_buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.movie = QMovie(self.media_buffer, QByteArray(), self)
        if self.movie.isValid() and self.movie.frameCount() != 1:
            self.movie.setScaledSize(image.size())
            self.movie.frameChanged.connect(lambda _: self.image.set_pixmap(self.movie.currentPixmap(), fit=False) if self.movie else None)
            self.movie.start()

    def load_video(self, raw):
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget
        if self.player is None:
            self.video = QVideoWidget()
            self.stack.addWidget(self.video)
            self.player = QMediaPlayer(self)
            self.audio = QAudioOutput(self)
            self.audio.setVolume(0.6)
            self.player.setAudioOutput(self.audio)
            self.player.setVideoOutput(self.video)
            self.player.durationChanged.connect(lambda duration: self.seek.setRange(0, duration))
            self.player.positionChanged.connect(lambda position: self.seek.setValue(position) if not self.seek.isSliderDown() else None)
            self.player.errorOccurred.connect(lambda *_: self.message.setText("Não foi possível reproduzir: " + self.player.errorString()))
        self.media_buffer = QBuffer(self)
        self.media_buffer.setData(QByteArray(raw))
        self.media_buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.player.setSourceDevice(self.media_buffer)
        self.stack.setCurrentWidget(self.video)
        self.video_controls.show()
        # Playback always requires a deliberate action, including after reveal.

    def toggle_video(self):
        if self.player:
            from PySide6.QtMultimedia import QMediaPlayer
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()
