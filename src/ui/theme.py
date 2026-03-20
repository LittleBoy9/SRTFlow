"""
Design tokens — colors, fonts, spacing, animations.
Single source of truth for SRTFlow's visual identity.
"""

# ── Colors ─────────────────────────────────────────────────────────────────
BG          = "#0c0c0e"
SURFACE     = "#151518"
SURFACE_2   = "#1c1c21"
SURFACE_3   = "#232329"
BORDER      = "#2a2a32"
BORDER_FOCUS= "#4f9cf9"

TEXT_1      = "#f2f2f7"   # primary
TEXT_2      = "#8e8e9e"   # secondary
TEXT_3      = "#4a4a5a"   # muted / placeholder

ACCENT      = "#4f9cf9"
ACCENT_DARK = "#1a4a8a"
ACCENT_GLOW = "rgba(79,156,249,0.18)"

SUCCESS     = "#30d158"
SUCCESS_BG  = "rgba(48,209,88,0.12)"
WARNING     = "#ffd60a"
WARNING_BG  = "rgba(255,214,10,0.12)"
ERROR       = "#ff453a"
ERROR_BG    = "rgba(255,69,58,0.12)"
INFO        = "#4f9cf9"
INFO_BG     = "rgba(79,156,249,0.12)"

# ── Typography ──────────────────────────────────────────────────────────────
FONT_FAMILY = '"SF Pro Display", "Segoe UI Variable", "Inter", system-ui, sans-serif'
FONT_MONO   = '"SF Mono", "Cascadia Code", "Fira Code", monospace'

# ── Spacing ─────────────────────────────────────────────────────────────────
RADIUS_SM   = "6px"
RADIUS_MD   = "10px"
RADIUS_LG   = "14px"
RADIUS_XL   = "18px"

# ── Master stylesheet ────────────────────────────────────────────────────────
STYLESHEET = f"""
/* ── Base ── */
QMainWindow, QDialog {{
    background-color: {BG};
}}

QWidget {{
    background-color: transparent;
    color: {TEXT_1};
    font-family: {FONT_FAMILY};
    font-size: 13px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
}}

QWidget:disabled {{
    color: {TEXT_3};
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_3};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    height: 6px;
    background: transparent;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 3px;
}}

/* ── Labels ── */
QLabel {{
    background: transparent;
    color: {TEXT_1};
}}
QLabel[role="heading"] {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    color: {TEXT_2};
    text-transform: uppercase;
}}
QLabel[role="muted"] {{
    color: {TEXT_3};
    font-size: 12px;
}}
QLabel[role="accent"] {{
    color: {ACCENT};
    font-size: 12px;
    font-weight: 600;
}}

/* ── Line Edits ── */
QLineEdit {{
    background-color: {SURFACE_2};
    border: 1.5px solid {BORDER};
    border-radius: {RADIUS_MD};
    padding: 10px 14px;
    color: {TEXT_1};
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {BORDER_FOCUS};
    background-color: {SURFACE_3};
}}
QLineEdit:hover:!focus {{
    border-color: #3a3a46;
}}
QLineEdit::placeholder {{
    color: {TEXT_3};
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {SURFACE_2};
    border: 1.5px solid {BORDER};
    border-radius: {RADIUS_MD};
    padding: 10px 14px;
    color: {TEXT_1};
    font-size: 13px;
    min-width: 140px;
}}
QComboBox:focus {{
    border-color: {BORDER_FOCUS};
}}
QComboBox:hover {{
    border-color: #3a3a46;
    background-color: {SURFACE_3};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_2};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE_3};
    border: 1.5px solid {BORDER};
    border-radius: {RADIUS_MD};
    padding: 4px;
    outline: none;
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    border-radius: {RADIUS_SM};
    min-height: 32px;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {SURFACE_3};
}}

/* ── Push Buttons ── */
QPushButton {{
    background-color: {SURFACE_2};
    color: {TEXT_1};
    border: 1.5px solid {BORDER};
    border-radius: {RADIUS_MD};
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {SURFACE_3};
    border-color: #3a3a46;
}}
QPushButton:pressed {{
    background-color: {SURFACE};
}}
QPushButton:disabled {{
    color: {TEXT_3};
    border-color: {BORDER};
}}

QPushButton[role="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5ba4ff, stop:1 #3d86e8);
    color: #ffffff;
    border: none;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.3px;
    border-radius: {RADIUS_LG};
    padding: 14px 24px;
}}
QPushButton[role="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #6cb0ff, stop:1 #4f96f0);
}}
QPushButton[role="primary"]:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3d86e8, stop:1 #2a6dcf);
}}
QPushButton[role="primary"]:disabled {{
    background: {SURFACE_3};
    color: {TEXT_3};
}}

QPushButton[role="ghost"] {{
    background: transparent;
    border: none;
    color: {TEXT_2};
    padding: 6px 10px;
    font-size: 12px;
    border-radius: {RADIUS_SM};
}}
QPushButton[role="ghost"]:hover {{
    background: {SURFACE_2};
    color: {TEXT_1};
}}

QPushButton[role="danger"] {{
    background: transparent;
    border: 1.5px solid {ERROR};
    color: {ERROR};
    border-radius: {RADIUS_MD};
}}
QPushButton[role="danger"]:hover {{
    background-color: {ERROR_BG};
}}

/* ── Checkboxes ── */
QCheckBox {{
    spacing: 8px;
    color: {TEXT_1};
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {BORDER};
    border-radius: 4px;
    background: {SURFACE_2};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url(none);
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}

/* ── Progress Bar ── */
QProgressBar {{
    background-color: {SURFACE_2};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3d86e8, stop:1 #5ba4ff);
    border-radius: 4px;
}}

/* ── Text Edit (log) ── */
QTextEdit, QPlainTextEdit {{
    background-color: {SURFACE};
    border: 1.5px solid {BORDER};
    border-radius: {RADIUS_MD};
    padding: 10px;
    color: {TEXT_1};
    font-family: {FONT_MONO};
    font-size: 12px;
    line-height: 1.6;
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {SURFACE_3};
    color: {TEXT_1};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {BORDER};
    background: {BORDER};
    border: none;
    max-height: 1px;
}}
"""
