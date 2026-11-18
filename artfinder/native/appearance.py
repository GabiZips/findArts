"""Native, keyboard-accessible previews for the appearance settings."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton
from .themes import THEMES
from .studio import nav_icon


class ThemePreview(QPushButton):
    def __init__(self, key, title, parent=None):
        super().__init__(title, parent)
        self.key = key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(220, 150)
        self.setAccessibleName(title)

    def sizeHint(self):
        return QSize(270, 158)

    def paintEvent(self, event):
        colors = THEMES[self.key]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        outline = colors["accent"] if self.isChecked() or self.hasFocus() else colors["border"]
        painter.setPen(QPen(QColor(outline), 2 if self.isChecked() or self.hasFocus() else 1))
        painter.setBrush(QColor(colors["surface"]))
        painter.drawRoundedRect(bounds, 12, 12)
        preview = bounds.adjusted(10, 10, -10, -43)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colors["bg"]))
        painter.drawRoundedRect(preview, 6, 6)
        painter.fillRect(QRectF(preview.left(), preview.top(), preview.width(), 22), QColor(colors["rail"]))
        painter.setBrush(QColor(colors["accent"]))
        painter.drawRoundedRect(QRectF(preview.left() + 7, preview.top() + 7, 10, 9), 3, 3)
        painter.setBrush(QColor(colors["border"]))
        for col in range(3):
            painter.drawRoundedRect(QRectF(preview.left() + 25 + col * 28, preview.top() + 9, 22, 5), 2, 2)
        tile_width = (preview.width() - 22) / 3
        for col, color in enumerate((colors["selected"], colors["hover"], colors["surface"])):
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(preview.left() + 7 + col * (tile_width + 4),
                                           preview.top() + 29, tile_width, preview.height() - 36), 4, 4)
        painter.setPen(QColor(colors["text"]))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(bounds.adjusted(14, bounds.height() - 38, -40, -8),
                         Qt.AlignmentFlag.AlignVCenter, self.text())
        if self.isChecked():
            icon_rect = self.rect().adjusted(self.width() - 36, self.height() - 35, -12, -11)
            nav_icon("check", colors["accent"]).paint(painter, icon_rect)
        painter.end()
