"""Original compass mark and line icons for the native workspace."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


PATHS = {
    "search": "M20 4l-5 12-11 4 5-12z M9 8l6 8",
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


def nav_icon(name, color="#e8e6f1"):
    if name == "brand":
        artwork = ('<rect x="1" y="1" width="22" height="22" rx="7" fill="#84b7ff"/>'
                   '<path d="M17 6l-3 8-8 4 4-9z" fill="#1c2a3d"/>'
                   '<circle cx="12" cy="12" r="2" fill="#84b7ff"/>')
    else:
        path = PATHS[name]
        artwork = f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{artwork}</svg>'
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    return QIcon(pixmap)
