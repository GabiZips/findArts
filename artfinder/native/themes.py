"""Shared native colors for controls, dialogs, and painted artwork cards."""
from PySide6.QtGui import QColor, QPalette

# Keep stable keys so existing user preferences continue to work.
THEMES = {
    "night": {"name": "Noturno", "bg": "#101014", "surface": "#19191f", "rail": "#151519",
              "text": "#e6e8f0", "muted": "#a7a7b7", "border": "#373743", "accent": "#bd9aff",
              "ink": "#211232", "hover": "#30293c", "selected": "#30243f", "error": "#ffb5ad"},
    "graphite": {"name": "Grafite", "bg": "#222222", "surface": "#303030", "rail": "#282828",
                 "text": "#f6f1e9", "muted": "#bdbdbd", "border": "#4e4e4e", "accent": "#e9c48c",
                 "ink": "#302211", "hover": "#4e463b", "selected": "#584a33", "error": "#ffb5ad"},
    "forest": {"name": "Floresta", "bg": "#222c24", "surface": "#303e32", "rail": "#19231c",
               "text": "#f1f3e7", "muted": "#bcc9b4", "border": "#5c745d", "accent": "#c8dc93",
               "ink": "#263018", "hover": "#44563c", "selected": "#4b603e", "error": "#ffb5ad"},
    "light": {"name": "Claro", "bg": "#e8eef0", "surface": "#f6f9fa", "rail": "#213741",
              "text": "#203640", "muted": "#4f6872", "border": "#8aa1aa", "accent": "#256274",
              "ink": "#ffffff", "hover": "#d7e5e8", "selected": "#c6dce3", "error": "#a22c3b"},
}

CONTROLS = {
    "night": {"control": "#212129", "controlEdge": "#505060"},
    "graphite": {"control": "#48423b", "controlEdge": "#a09380"},
    "forest": {"control": "#43553f", "controlEdge": "#8fa284"},
    "light": {"control": "#dce7eb", "controlEdge": "#73909c"},
}

STYLE_TEMPLATE = """
QWidget { background: @bg; color: @text; font-family: 'Source Sans 3', 'Segoe UI'; font-size: 15px; }
QMainWindow, QDialog { background: @bg; }
QLabel, QCheckBox { background: transparent; }
QLabel#brand { font-family: 'Archivo'; font-size: 21px; font-weight: 750; }
QLabel#title { font-family: 'Archivo'; font-size: 24px; font-weight: 750; }
QLabel#dialogTitle, QLabel#emptyTitle { font-size: 25px; font-weight: 600; padding: 8px 0; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; padding: 12px 0 6px; }
QLabel#muted, QStatusBar { color: @muted; }
QLabel#error { color: @error; }
QPushButton {
    color: @text; background: @control;
    border: 1px solid @controlEdge; border-radius: 7px;
    padding: 6px 11px; min-height: 20px; font-weight: 600;
}
QPushButton:hover { background: @hover; border-color: @accent; }
QPushButton:pressed, QPushButton:checked { background: @selected; border: 1px solid @accent; }
QPushButton[primary=true] { background: @accent; color: @ink; border: 1px solid @accent; font-weight: 700; }
QPushButton[primary=true]:hover { background: @accent; color: @ink; border-color: @text; }
QPushButton[primary=true]:pressed { background: @accent; color: @ink; border: 1px solid @text; }
QPushButton:disabled, QPushButton[primary=true]:disabled { color: @muted; background: @surface; border: 1px solid @border; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus { border: 1px solid @accent; background: @selected; }
QPushButton[primary=true]:focus { background: @accent; color: @ink; border: 1px solid @text; }
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox { background: @surface; border: 1px solid @border; border-radius: 6px; padding: 7px; selection-background-color: @selected; selection-color: @text; }
QComboBox { min-width: 90px; }
QComboBox QAbstractItemView { background: @surface; color: @text; selection-background-color: @selected; selection-color: @text; }
QListView, QTableWidget { background: @bg; border: 1px solid @border; border-radius: 8px; outline: none; }
QListWidget::item { padding: 10px; border-radius: 5px; }
QListWidget::item:selected { background: @selected; }
QCheckBox { spacing: 8px; padding: 6px 2px; }
QCheckBox::indicator { width: 16px; height: 16px; }
QTabWidget::pane { border: 1px solid @border; border-radius: 6px; }
QTabBar::tab { padding: 12px 18px; background: @surface; }
QTabBar::tab:selected { background: @selected; color: @text; }
QScrollBar:vertical { background: @bg; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: @border; min-height: 30px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QProgressBar { border: 0; background: @surface; border-radius: 4px; height: 7px; }
QProgressBar::chunk { background: @accent; border-radius: 4px; }
QMenu, QToolTip { background: @surface; color: @text; border: 1px solid @border; padding: 6px; }
QMenu::item { padding: 9px 22px; }
QMenu::item:selected { background: @selected; }
QStatusBar { border-top: 1px solid @border; }
QHeaderView::section { background: @surface; color: @muted; padding: 8px; border: none; }
QWidget#masthead { background: @rail; border-bottom: 1px solid @border; }
QPushButton#navTab { background: transparent; border-color: transparent; padding: 8px 12px; }
QPushButton#navTab:hover { background: @hover; border-color: @controlEdge; }
QPushButton#navTab:checked { background: @surface; border: 1px solid @border; border-bottom: 3px solid @accent; }
QPushButton#navTab:focus { border-color: @accent; }
QLabel#resultCount { color: @muted; padding: 2px 10px; background: @surface; border-radius: 6px; }
QWidget#searchCover { background: @surface; border: 1px solid @border; border-radius: 9px; }
QLabel#coverTitle { color: @text; font-size: 20px; font-weight: 700; }
QDialog#artworkFilters QLabel#dialogTitle { padding: 0; font-size: 23px; }
QDialog#artworkFilters QLabel#sectionTitle { padding: 7px 0 0; }
QPushButton#filterChip {
    border-radius: 14px; padding: 4px 13px; min-height: 20px;
    background: @bg; border: 1px solid @controlEdge; color: @muted;
}
QPushButton#filterChip:hover { color: @text; border-color: @accent; }
QPushButton#filterChip:checked { background: @selected; border-color: @accent; color: @text; }
QPushButton#filterChip[filterValue=sfw]:checked { background: #20332b; color: #a7efbc; border-color: #79c294; }
QPushButton#filterChip[filterValue=sensitive]:checked { background: #352e20; color: #f8db8f; border-color: #d9b56b; }
QPushButton#filterChip[filterValue=nsfw]:checked { background: #38242b; color: #ffc3cd; border-color: #db8b9d; }
QPushButton#filterChip:focus { border-color: @text; }
QLabel#emptyTitle { font-family: 'Archivo'; font-size: 26px; font-weight: 700; }
QWidget#inspector { background: @surface; border-left: 1px solid @border; }
QWidget#inspector QLabel { border: none; }
QWidget#inspectorBody, QWidget#inspectorBody QWidget { background: @surface; }
QWidget#inspectorBody QLabel#inspectorPreview { background: @bg; }
QLabel#inspectorPreview { background: @bg; border-radius: 5px; }
QWidget#commandBar, QWidget#actions { background: @surface; border: 1px solid @border; border-radius: 10px; }
QWidget#commandBar QLineEdit { background: @bg; }
QWidget#actions QSlider { min-height: 29px; }
QSplitter::handle { background: @border; width: 1px; }
QSlider::groove:horizontal { height: 4px; background: @border; border-radius: 2px; }
QSlider::handle:horizontal { width: 16px; margin: -6px 0; background: @accent; border-radius: 8px; }
QListView#artGrid { border: none; }
QGraphicsView { background: #121318; border: none; }
"""


def stylesheet(key):
    result = STYLE_TEMPLATE
    colors = {**THEMES[key], **CONTROLS[key]}
    for role in sorted(colors, key=len, reverse=True):
        color = colors[role]
        result = result.replace("@" + role, color)
    return result


def apply_theme(application, key):
    colors = THEMES[key]
    application.setProperty("theme", key)
    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, "bg"), (QPalette.ColorRole.WindowText, "text"),
        (QPalette.ColorRole.Base, "surface"), (QPalette.ColorRole.AlternateBase, "bg"),
        (QPalette.ColorRole.Text, "text"), (QPalette.ColorRole.Button, "surface"),
        (QPalette.ColorRole.ButtonText, "text"), (QPalette.ColorRole.Highlight, "accent"),
        (QPalette.ColorRole.HighlightedText, "ink"), (QPalette.ColorRole.PlaceholderText, "muted"),
        (QPalette.ColorRole.ToolTipBase, "surface"), (QPalette.ColorRole.ToolTipText, "text"),
    ]:
        palette.setColor(role, QColor(colors[color]))
    application.setPalette(palette)
    application.setStyleSheet(stylesheet(key))
    refresh_icons(application, key)


def refresh_icons(application, key):
    from PySide6.QtWidgets import QPushButton
    from .studio import nav_icon
    colors = THEMES[key]
    for widget in application.allWidgets():
        if isinstance(widget, QPushButton) and widget.property("iconName"):
            color = colors["ink"] if widget.property("primary") else colors["text"]
            widget.setIcon(nav_icon(widget.property("iconName"), color))


def load_fonts(resource_dir):
    from PySide6.QtGui import QFontDatabase
    from pathlib import Path
    root = Path(resource_dir) / "assets" / "fonts"
    if "Archivo" not in QFontDatabase.families():
        for filename in ("Archivo.ttf", "SourceSans3.ttf"):
            QFontDatabase.addApplicationFont(str(root / filename))
