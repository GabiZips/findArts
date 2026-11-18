"""Original artwork finder mark and line icons for the native workspace."""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer


PATHS = {
    "search": "M20 4l-5 12-11 4 5-12z M9 8l6 8",
    "magnifier": "M21 21l-5-5 M18 11a7 7 0 1 1-14 0 7 7 0 0 1 14 0z",
    "panel": "M3 4h18v16H3z M14 4v16 M17 8h1 M17 12h1",
    "gallery": "M3 5h18v15H3z M4 18l5-6 4 4 3-3 5 6 M16 9h.1",
    "stats": "M4 20h16 M6 16v-5 M12 16V4 M18 16V8",
    "categories": "M3 4h9l9 9-8 8-10-10z M8 8h.1",
    "collections": "M3 7h7l2 2h9v11H3z M5 4h6l2 2h6",
    "plus": "M12 4v16 M4 12h16",
    "filter": "M3 6h18 M6 12h12 M9 18h6 M7 4v4 M16 10v4 M12 16v4",
    "refresh": "M20 10a8 8 0 1 0-2 8 M20 4v6h-6",
    "open": "M13 4h7v7 M20 4l-11 11 M9 5H4v15h15v-5",
    "save": "M6 3h12v18l-6-4-6 4z",
    "download": "M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5",
    "close": "M6 6l12 12 M6 18L18 6",
    "check": "M4 12l5 5L20 6",
    "settings": "M4 7h6m5 0h5 M4 17h10m4 0h2 M10 4v6h4V4z M14 14v6h4v-6z",
}


def brand_pixmap(size):
    """Draw a pair of prints with a chunky finder lens over the front print."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 100, size / 100)
    painter.setPen(Qt.PenStyle.NoPen)

    painter.save()
    painter.translate(42, 44)
    painter.rotate(-14)
    painter.setBrush(QColor("#18203b"))
    painter.drawRoundedRect(QRectF(-32, -33, 64, 68), 10, 10)
    painter.setBrush(QColor("#afc1ff"))
    painter.drawRoundedRect(QRectF(-30, -35, 61, 65), 9, 9)
    painter.restore()

    painter.save()
    painter.translate(54, 50)
    painter.rotate(9)
    painter.setBrush(QColor("#18203b"))
    painter.drawRoundedRect(QRectF(-29, -29, 66, 69), 10, 10)
    painter.setBrush(QColor("#ff9d50"))
    painter.drawRoundedRect(QRectF(-31, -33, 66, 69), 9, 9)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#20264b"), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(10, 11, 20, 21)
    painter.drawEllipse(QRectF(-17, -18, 32, 32))
    painter.restore()
    painter.end()
    return pixmap


def nav_icon(name, color="#eef1fb"):
    if name == "brand":
        icon = QIcon()
        for size in (24, 48, 96, 192):
            icon.addPixmap(brand_pixmap(size))
        return icon
    path = PATHS[name]
    artwork = f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{artwork}</svg>'
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    return QIcon(pixmap)
