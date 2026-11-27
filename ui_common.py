# -*- coding: utf-8 -*-
"""ui_common.py - Hệ thống thiết kế chuyên nghiệp: Design Tokens Sáng/Tối, đồng bộ thanh tiêu đề Windows,
QSS chuẩn hóa từng lớp component, widget tái sử dụng mượt mà không lag."""
import os
import sys
import unicodedata
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (QComboBox, QCompleter, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

ACCENTS = {  # tên: (chính, đậm hơn/hover, sáng nhẹ cho gradient)
    "Chàm": ("#5B5BD6", "#4646B9", "#7474E8"),
    "Lam": ("#2563EB", "#1D4ED8", "#3B82F6"),
    "Xanh biển": ("#0284C7", "#0369A1", "#0EA5E9"),
    "Ngọc": ("#0D9488", "#0F766E", "#14B8A6"),
    "Lục": ("#10B981", "#059669", "#34D399"),
    "Cam": ("#EA580C", "#C2410C", "#F97316"),
    "Hồng": ("#E11D48", "#BE123C", "#F43F5E"),
    "Tím": ("#7C3AED", "#6D28D9", "#8B5CF6"),
}

THEME_META = [
    ("light", "Studio Sáng", "Nền trắng thanh lịch, sắc nét", False, "#F5F7FC", "#FFFFFF", "#4F46E5"),
    ("dark", "Midnight Pro", "Nền tối sâu, dịu mắt ban đêm", True, "#090D16", "#121A2B", "#6366F1"),
    ("nord", "Nordic Frost", "Xám lam dịu nhẹ cho học tập lâu", True, "#161B26", "#1F2736", "#38BDF8"),
    ("warm", "Warm Paper", "Giấy kem ấm bảo vệ mắt", False, "#F7F3EB", "#FFFDF9", "#D97706"),
]

PALETTES = {
    "light": dict(
        is_dark=False,
        bg="#F4F6FB",
        surface="#FFFFFF",
        surface2="#EEF2F8",
        border="#DFE6F1",
        border_strong="#C3CFE0",
        text="#0F172A",
        muted="#475569",
        subtle="#64748B",
        side="#F9FAFE",
        input="#FFFFFF",
        hover="#E8EEF8",
        scroll="#C8D3E4",
        scroll_hover="#94A3B8",
        preview="#FFFFFF",
        canvas="#FFFFFF",
        grid="#EAEFF7",
        danger="#DC2626",
        danger_soft="rgba(220,38,38,0.10)",
    ),
    "dark": dict(
        is_dark=True,
        bg="#090D16",
        surface="#111827",
        surface2="#1A2438",
        border="#23304A",
        border_strong="#364A70",
        text="#F1F5F9",
        muted="#9BA9BF",
        subtle="#6B7B95",
        side="#0C1220",
        input="#0A0F1C",
        hover="#1E2B44",
        scroll="#314364",
        scroll_hover="#4B6491",
        preview="#0A0F1C",
        canvas="#0A0F1C",
        grid="#192338",
        danger="#F87171",
        danger_soft="rgba(248,113,113,0.16)",
    ),
    "nord": dict(
        is_dark=True,
        bg="#161B26",
        surface="#1F2636",
        surface2="#273144",
        border="#313E55",
        border_strong="#445573",
        text="#ECEFF4",
        muted="#A7B5CB",
        subtle="#7B8BA6",
        side="#1A202D",
        input="#141923",
        hover="#2D3950",
        scroll="#3F4F6B",
        scroll_hover="#596E94",
        preview="#141923",
        canvas="#141923",
        grid="#253045",
        danger="#F87171",
        danger_soft="rgba(248,113,113,0.16)",
    ),
    "warm": dict(
        is_dark=False,
        bg="#F5F0E6",
        surface="#FFFDF8",
        surface2="#EFE9DC",
        border="#E2D8C7",
        border_strong="#CBBFA9",
        text="#231D16",
        muted="#5E5244",
        subtle="#817362",
        side="#FAF6EE",
        input="#FFFFFF",
        hover="#EAE2D2",
        scroll="#CFC3AE",
        scroll_hover="#A89A82",
        preview="#FFFDF8",
        canvas="#FFFDF9",
        grid="#EFE9DD",
        danger="#C81E1E",
        danger_soft="rgba(200,30,30,0.10)",
    ),
}


def is_dark_mode(mode: str) -> bool:
    return bool(PALETTES.get(mode, PALETTES["light"]).get("is_dark", False))


def esc(text: str) -> str:
    """Thoát '&' để Qt không biến nó thành phím tắt."""
    return text.replace("&", "&&")


def apply_win_titlebar(win, dark: bool):
    """Đồng bộ màu thanh tiêu đề Windows 10/11 với chế độ Sáng/Tối của ứng dụng."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(win.winId())
        val = ctypes.c_int(1 if dark else 0)
        dwm = ctypes.windll.dwmapi
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (Win11 / Win10)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


def build_palette(mode="light", accent="Chàm") -> QPalette:
    """QPalette nhẹ (<2ms) cho nền cửa sổ chính, hội thoại hệ thống, tooltip và menu."""
    c = PALETTES.get(mode, PALETTES["light"])
    a = ACCENTS.get(accent, ACCENTS["Chàm"])[0]
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(c["bg"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Base, QColor(c["input"]))
    pal.setColor(QPalette.AlternateBase, QColor(c["surface2"]))
    pal.setColor(QPalette.ToolTipBase, QColor(c["surface"]))
    pal.setColor(QPalette.ToolTipText, QColor(c["text"]))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.Button, QColor(c["surface"]))
    pal.setColor(QPalette.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.BrightText, QColor("#FFFFFF"))
    pal.setColor(QPalette.Highlight, QColor(a))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.PlaceholderText, QColor(c["subtle"]))
    return pal


def _chevron_qss(dark: bool, fallback_col: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    p = base / "assets" / ("chevron_light.png" if dark else "chevron_dark.png")
    if p.exists():
        return f'image: url("{p.as_posix()}"); width: 12px; height: 12px;'
    return f"width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {fallback_col};"


def build_qss(mode="light", accent="Chàm") -> str:
    c = PALETTES.get(mode, PALETTES["light"])
    dark = bool(c.get("is_dark", False))
    chev = _chevron_qss(dark, c["muted"])
    acc_tuple = ACCENTS.get(accent, ACCENTS["Chàm"])
    a, ad, al = acc_tuple[0], acc_tuple[1], acc_tuple[2]
    rr, gg, bb = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    soft = f"rgba({rr},{gg},{bb},{0.22 if dark else 0.11})"
    soft2 = f"rgba({rr},{gg},{bb},{0.34 if dark else 0.20})"
    ring = f"rgba({rr},{gg},{bb},0.55)"
    btn_grad = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {al}, stop:1 {a})"
    btn_grad_hov = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {a}, stop:1 {ad})"
    hero_bg = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {soft2}, stop:0.6 {c['surface']}, stop:1 {c['surface']})"
    side_bg = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {c['side']}, stop:1 {c['bg']})"
    return f"""
QMainWindow, QWidget {{
    background: {c['bg']}; color: {c['text']};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}
QToolTip {{
    background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border_strong']}; border-radius: 8px;
    padding: 6px 10px; font-size: 12.5px;
}}

/* Typography */
QLabel {{ background: transparent; }}
QLabel[muted="true"] {{ color: {c['muted']}; font-size: 12.5px; }}
QLabel[caption="true"] {{ color: {c['subtle']}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; }}
QLabel[sidecap="true"] {{ color: {c['subtle']}; font-size: 10.5px; font-weight: 700; letter-spacing: 0.9px; padding-left: 12px; }}
QLabel[h1="true"] {{ font-size: 19px; font-weight: 700; color: {c['text']}; }}
QLabel[h2="true"] {{ font-size: 14px; font-weight: 600; color: {c['text']}; }}
QLabel[brand="true"] {{ font-size: 16px; font-weight: 700; color: {c['text']}; }}
QLabel[brandsub="true"] {{ font-size: 11.5px; color: {c['muted']}; }}
QLabel[kpi_num="true"] {{ font-size: 25px; font-weight: 800; color: {a}; }}
QLabel[kpi_lbl="true"] {{ font-size: 12.5px; font-weight: 600; color: {c['muted']}; }}
QLabel[result="true"] {{ font-size: 26px; font-weight: 700; color: {a}; }}
QLabel[badge="true"] {{
    background: {soft}; color: {al if dark else a}; border: 1px solid {soft2}; border-radius: 10px;
    padding: 3px 10px; font-size: 11.5px; font-weight: 600;
}}
QLabel[badge_ok="true"] {{
    background: rgba(16,185,129,0.16); color: #10B981; border-radius: 10px;
    padding: 3px 10px; font-size: 11.5px; font-weight: 600;
}}
QLabel[badge_muted="true"] {{
    background: {c['surface2']}; color: {c['muted']}; border-radius: 10px;
    padding: 3px 10px; font-size: 11.5px; font-weight: 600;
}}

/* Containers & Cards */
QFrame[sep="true"] {{ background: {c['border']}; border: none; }}
QFrame[card="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {c['surface']}, stop:1 {c['surface2'] if not dark else c['surface']});
    border: 1px solid {c['border']};
    border-top-color: {c['border_strong'] if dark else c['border']};
    border-radius: 13px;
}}
QFrame[hero="true"] {{
    background: {hero_bg};
    border: 1.5px solid {soft2};
    border-radius: 16px;
}}
QFrame[kpi="true"] {{
    background: {c['surface']};
    border: 1px solid {c['border']};
    border-top: 2px solid {a};
    border-radius: 13px;
}}
QFrame[panel="true"] {{
    background: {c['surface2']};
    border: 1px solid {c['border']};
    border-radius: 10px;
}}
QFrame[calcdisplay="true"] {{
    background: {c['input']};
    border: 1.5px solid {c['border_strong']};
    border-radius: 13px;
}}
QFrame#sidebar {{
    background: {side_bg};
    border-right: 1px solid {c['border']};
}}

/* Buttons */
QPushButton {{
    background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 8px;
    padding: 6px 12px; font-weight: 500;
}}
QPushButton:hover {{ background: {c['hover']}; border-color: {c['border_strong']}; }}
QPushButton:pressed {{ background: {soft}; border-color: {a}; }}
QPushButton:focus {{ border: 1.5px solid {ring}; }}
QPushButton:checked {{ background: {btn_grad}; color: #FFFFFF; border-color: {ad}; font-weight: 600; }}
QPushButton:disabled {{ color: {c['subtle']}; background: {c['surface2']}; border-color: {c['border']}; }}

QPushButton[primary="true"] {{
    background: {btn_grad}; color: #FFFFFF; border: 1px solid {ad}; font-weight: 600;
}}
QPushButton[primary="true"]:hover {{ background: {btn_grad_hov}; border-color: {ad}; }}

QPushButton[subtle="true"] {{
    background: {c['surface2']}; color: {c['text']}; border: 1px solid {c['border']}; min-width: 0px;
}}
QPushButton[subtle="true"]:hover {{ background: {c['hover']}; border-color: {c['border_strong']}; }}
QPushButton[subtle="true"]:checked {{ background: {soft2}; color: {al if dark else a}; border-color: {a}; font-weight: 600; }}

QPushButton[sidetoggle="true"] {{
    background: {c['surface2']}; color: {c['text']};
    border: 1px solid {c['border_strong']}; border-radius: 7px;
    padding: 0px; font-weight: 800; font-size: 13px; min-width: 0px;
}}
QPushButton[sidetoggle="true"]:hover {{ background: {soft}; color: {al if dark else a}; border-color: {a}; }}

QPushButton[danger="true"] {{
    background: transparent; color: {c['danger']}; border: 1px solid {c['border']};
}}
QPushButton[danger="true"]:hover {{ background: {c['danger_soft']}; border-color: {c['danger']}; }}

QPushButton[star="true"] {{
    background: {c['surface2']}; color: {c['muted']}; border: 1px solid {c['border']};
    border-radius: 8px; padding: 5px 11px; font-weight: 600;
}}
QPushButton[star="true"]:hover {{ border-color: #F59E0B; color: #F59E0B; background: rgba(245,158,11,0.10); }}
QPushButton[star="true"]:checked {{
    background: rgba(245,158,11,0.18); color: {"#FBBF24" if dark else "#B45309"};
    border: 1.5px solid #F59E0B; font-weight: 700;
}}

QPushButton[tool="true"] {{
    background: transparent; color: {c['text']};
    border: 1px solid transparent; border-radius: 8px;
    padding: 4px 4px; font-weight: 600; font-size: 11.5px; min-width: 0px;
}}
QPushButton[tool="true"]:hover {{ background: {c['hover']}; border-color: {c['border']}; }}
QPushButton[tool="true"]:checked {{ background: {btn_grad}; color: #FFFFFF; border-color: {ad}; }}

QPushButton[elem="true"] {{
    background: {c['surface2']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 7px;
    padding: 3px 2px; font-weight: 700; font-size: 12px; min-width: 0px;
}}
QPushButton[elem="true"]:hover {{ background: {c['hover']}; border-color: {a}; }}
QPushButton[elem="true"]:checked {{ background: {btn_grad}; color: #FFFFFF; border-color: {ad}; }}

QPushButton[seg="true"] {{
    background: {c['surface2']}; color: {c['muted']};
    border: 1px solid {c['border']}; border-radius: 8px;
    padding: 4px 10px; font-weight: 600; font-size: 11.5px; min-width: 0px;
}}
QPushButton[seg="true"]:hover {{ color: {c['text']}; border-color: {c['border_strong']}; }}
QPushButton[seg="true"]:checked {{ background: {btn_grad}; color: #FFFFFF; border-color: {ad}; }}

/* Sidebar Navigation */
QPushButton[nav="true"] {{
    text-align: left;
    padding: 10px 12px 10px 12px;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 10px;
    background: transparent;
    color: {c['muted']};
    font-weight: 600;
    font-size: 13px;
}}
QPushButton[nav="true"]:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton[nav="true"]:checked {{
    background: {soft};
    color: {al if dark else a};
    border-color: {soft2};
    border-left: 3px solid {a};
    font-weight: 700;
}}

QPushButton[navutil="true"] {{
    text-align: left;
    padding: 9px 12px 9px 15px;
    border: 1px solid {c['border']};
    border-radius: 10px;
    background: {c['surface']};
    color: {c['text']};
    font-weight: 600;
    font-size: 12.5px;
}}
QPushButton[navutil="true"]:hover {{ background: {c['hover']}; border-color: {a}; color: {al if dark else a}; }}

QPushButton[guideitem="true"] {{
    text-align: left;
    padding: 9px 11px;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 9px;
    background: transparent;
    color: {c['muted']};
    font-weight: 600;
    font-size: 12.5px;
}}
QPushButton[guideitem="true"]:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton[guideitem="true"]:checked {{
    background: {soft}; color: {al if dark else a};
    border-color: {soft2}; border-left: 3px solid {a}; font-weight: 700;
}}

QPushButton[themecard="true"] {{
    text-align: left;
    padding: 10px 12px;
    border: 1.5px solid {c['border']};
    border-radius: 12px;
    background: {c['surface2']};
    color: {c['text']};
    font-weight: 700;
}}
QPushButton[themecard="true"]:hover {{ border-color: {a}; background: {c['hover']}; }}
QPushButton[themecard="true"]:checked {{
    background: {soft}; color: {al if dark else a}; border: 2px solid {a};
}}

QPushButton[pill="true"] {{
    border-radius: 11px; padding: 3px 7px; font-size: 11.5px; min-width: 0px;
    background: {c['surface2']}; border: 1px solid {c['border']};
}}
QPushButton[pill="true"]:hover {{ background: {soft}; border-color: {a}; color: {al if dark else a}; }}
QPushButton[pill="true"]:checked {{ background: {btn_grad}; color: #FFFFFF; border-color: {ad}; }}

QPushButton[nav_mini="true"] {{
    text-align: center;
    padding: 9px 0px;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 10px;
    background: transparent;
    color: {c['muted']};
    min-width: 0px;
}}
QPushButton[nav_mini="true"]:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton[nav_mini="true"]:checked {{ background: {soft}; color: {al if dark else a}; border-left: 3px solid {a}; }}

/* Calculator Keys */
QPushButton[key="true"] {{ background: {c['surface2']}; border: 1px solid {c['border']}; border-radius: 9px; font-size: 14px; font-weight: 600; padding: 0; }}
QPushButton[key="true"]:hover {{ background: {c['hover']}; border-color: {a}; }}
QPushButton[key="num"] {{ background: {c['surface']}; border: 1px solid {c['border']}; font-size: 16px; font-weight: 700; border-radius: 9px; padding: 0; }}
QPushButton[key="num"]:hover {{ background: {c['hover']}; border-color: {a}; }}
QPushButton[key="fn"] {{ background: {soft}; color: {al if dark else a}; font-size: 13px; font-weight: 700; border: 1px solid transparent; border-radius: 9px; padding: 0; }}
QPushButton[key="fn"]:hover {{ background: {soft2}; border-color: {a}; }}
QPushButton[key="op"] {{ background: {c['surface2']}; border: 1px solid {c['border']}; font-size: 17px; font-weight: 700; border-radius: 9px; padding: 0; }}
QPushButton[key="op"]:hover {{ background: {c['hover']}; border-color: {a}; }}
QPushButton[key="eq"] {{ background: {btn_grad}; color: #FFFFFF; font-size: 18.5px; font-weight: 800; border: 1px solid {ad}; border-radius: 9px; padding: 0; }}
QPushButton[key="eq"]:hover {{ background: {btn_grad_hov}; }}
QPushButton[key="ac"] {{ background: {c['danger']}; color: #FFFFFF; font-weight: 700; border: none; border-radius: 9px; padding: 0; }}
QPushButton[key="ac"]:hover {{ background: #B91C1C; }}

/* Inputs & Controls */
QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {c['input']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 8px;
    padding: 5px 9px; font-size: 13px;
    selection-background-color: {a}; selection-color: #FFFFFF;
}}
QPlainTextEdit {{
    font-family: "Cascadia Code", "Cascadia Mono", "Consolas", monospace;
    font-size: 13px;
}}
QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border-color: {c['border_strong']};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1.5px solid {a};
}}
QComboBox {{
    padding: 5px 22px 5px 8px;
}}
QComboBox QLineEdit {{
    border: none; background: transparent; padding: 0px; margin: 0px;
}}
QComboBox QLineEdit:focus {{
    border: none;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 22px; border: none; border-left: 1px solid {c['border']};
    border-top-right-radius: 7px; border-bottom-right-radius: 7px;
    background: {c['surface2']};
}}
QComboBox::drop-down:hover {{
    background: {soft};
}}
QComboBox::down-arrow {{
    {chev}
}}
QComboBox QAbstractItemView {{
    background: {c['surface']}; color: {c['text']};
    border: 1.5px solid {c['border_strong']}; border-radius: 9px;
    selection-background-color: {a}; selection-color: #FFFFFF;
    outline: none; padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 5px 8px; border-radius: 5px;
    color: {c['text']}; background: transparent;
    min-height: 22px;
}}
QComboBox QAbstractItemView::item:hover {{
    background: {soft}; color: {c['text']};
}}
QComboBox QAbstractItemView::item:selected,
QComboBox QAbstractItemView::item:selected:hover {{
    background: {a}; color: #FFFFFF;
}}

/* Checkboxes & Radios */
QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QRadioButton::indicator {{
    width: 16px; height: 16px; border-radius: 9px;
    border: 1.5px solid {c['border_strong']}; background: {c['input']};
}}
QRadioButton::indicator:hover {{ border-color: {a}; }}
QRadioButton::indicator:checked {{
    border: 1.5px solid {a};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {a}, stop:0.48 {a}, stop:0.55 {c['input']}, stop:1 {c['input']});
}}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 5px;
    border: 1.5px solid {c['border_strong']}; background: {c['input']};
}}
QCheckBox::indicator:hover {{ border-color: {a}; }}
QCheckBox::indicator:checked {{
    border: 1.5px solid {a};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {a}, stop:0.52 {a}, stop:0.58 {c['input']}, stop:1 {c['input']});
}}

/* Tabs */
QTabWidget::pane {{ border: none; top: 6px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: {c['surface']}; color: {c['muted']};
    border: 1px solid {c['border']}; border-radius: 9px;
    padding: 7px 15px; margin: 2px 5px 2px 0; font-weight: 600;
}}
QTabBar::tab:hover {{ color: {c['text']}; background: {c['hover']}; border-color: {c['border_strong']}; }}
QTabBar::tab:selected {{ background: {btn_grad}; color: #FFFFFF; border-color: {ad}; }}

/* Lists & Tables */
QListWidget, QTableWidget, QTreeWidget {{
    background: {c['input']}; border: 1px solid {c['border']};
    border-radius: 9px; outline: none; font-size: 13px;
    alternate-background-color: {c['surface2']};
    padding: 4px;
}}
QListWidget::item {{ padding: 7px 10px; border-radius: 6px; margin: 1px 0; }}
QListWidget::item:selected, QTableWidget::item:selected {{ background: {a}; color: #FFFFFF; }}
QListWidget::item:hover:!selected {{ background: {c['hover']}; }}
QHeaderView::section {{
    background: {c['surface2']}; color: {c['text']};
    border: none; border-bottom: 1px solid {c['border']};
    padding: 6px 8px; font-weight: 700;
}}

/* Scrollbars */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['scroll']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['scroll_hover']}; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['scroll']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* Misc */
QStatusBar {{
    background: {c['side']}; color: {c['muted']};
    border-top: 1px solid {c['border']}; font-size: 12px;
    padding: 2px 10px;
}}
QGroupBox {{
    border: 1px solid {c['border']}; border-radius: 10px;
    margin-top: 12px; padding: 10px 8px 8px 8px; font-weight: 700;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {a}; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 6px; }}
QSplitter::handle:vertical {{ height: 6px; }}
QSplitter::handle:hover {{ background: {soft}; border-radius: 3px; }}
QMenu {{
    background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border_strong']}; border-radius: 9px; padding: 4px;
}}
QMenu::item {{ padding: 6px 20px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {a}; color: #FFFFFF; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 8px; }}
QFrame[combopopup="true"] {{
    background: {c['surface']}; color: {c['text']};
    border: 1.5px solid {c['border_strong']}; border-radius: 11px;
}}
QFrame[combopopup="true"] QLineEdit {{
    background: {c['input']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 7px;
    padding: 5px 9px; font-size: 13px;
}}
QFrame[combopopup="true"] QLineEdit:focus {{
    border: 1.5px solid {a};
}}
QFrame[combopopup="true"] QListWidget {{
    background: transparent; border: none; padding: 2px 0; outline: none; font-size: 13px;
}}
QFrame[combopopup="true"] QListWidget::item {{
    padding: 6px 10px; border-radius: 6px; margin: 1px 0;
    color: {c['text']};
}}
QFrame[combopopup="true"] QListWidget::item:hover:!selected {{
    background: {soft}; color: {c['text']};
}}
QFrame[combopopup="true"] QListWidget::item:selected {{
    background: {a}; color: #FFFFFF; font-weight: 600;
}}
"""


def mk_btn(text, primary=False, tip="", pill=False, checkable=False, prop=None):
    b = QPushButton(esc(text))
    if primary:
        b.setProperty("primary", True)
    if pill:
        b.setProperty("pill", True)
    if prop:
        b.setProperty(*prop)
    if tip:
        b.setToolTip(tip)
    b.setCheckable(checkable)
    b.setCursor(Qt.PointingHandCursor)
    return b


class _NoWheelFilter(QObject):
    """Chặn cuộn chuột vô tình làm đổi giá trị QComboBox / QSpinBox khi chưa mở danh sách."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel:
            if isinstance(obj, QComboBox):
                if not obj.view().isVisible():
                    ev.ignore()
                    return True
            else:
                if not obj.hasFocus():
                    ev.ignore()
                    return True
        return False


_NO_WHEEL = None


def no_wheel(w: QWidget) -> QWidget:
    """Chặn cuộn chuột nhầm trên widget (QComboBox / QSpinBox / QDoubleSpinBox)."""
    global _NO_WHEEL
    if _NO_WHEEL is None:
        _NO_WHEEL = _NoWheelFilter()
    w.setFocusPolicy(Qt.StrongFocus)
    w.installEventFilter(_NO_WHEEL)
    return w


def _norm_search(t: str) -> str:
    t = (t or "").strip().lower().replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn")


class _ComboPopup(QFrame):
    """Popup thả xuống hiện đại tích hợp sẵn thanh tìm kiếm ngay bên trong danh sách."""

    def __init__(self, combo: "SearchableComboBox"):
        super().__init__(combo, Qt.Popup | Qt.FramelessWindowHint)
        self.combo = combo
        self.setProperty("combopopup", True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(7, 7, 7, 7)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refilter)
        self.search.installEventFilter(self)
        top.addWidget(self.search, 1)

        self.lbl_cnt = QLabel("")
        self.lbl_cnt.setProperty("badge", True)
        top.addWidget(self.lbl_cnt)
        lay.addLayout(top)

        self.lst = QListWidget()
        self.lst.setUniformItemSizes(True)
        self.lst.setMouseTracking(True)
        self.lst.itemClicked.connect(self._choose)
        lay.addWidget(self.lst, 1)

    def eventFilter(self, obj, ev):
        if obj is self.search and ev.type() == QEvent.KeyPress:
            k = ev.key()
            if k == Qt.Key_Down:
                if self.lst.count() > 0:
                    self.lst.setCurrentRow(min(self.lst.count() - 1, max(0, self.lst.currentRow() + 1)))
                return True
            if k == Qt.Key_Up:
                if self.lst.count() > 0:
                    self.lst.setCurrentRow(max(0, self.lst.currentRow() - 1))
                return True
            if k in (Qt.Key_Return, Qt.Key_Enter):
                it = self.lst.currentItem() or (self.lst.item(0) if self.lst.count() > 0 else None)
                if it is not None:
                    self._choose(it)
                return True
            if k == Qt.Key_Escape:
                self.hide()
                return True
        return super().eventFilter(obj, ev)

    def open_for(self):
        import i18n
        # Đồng bộ stylesheet từ cửa sổ hiện tại
        qss = ""
        w = self.combo
        while w is not None and not qss:
            qss = w.styleSheet()
            w = w.parentWidget()
        if not qss and self.combo.window() is not None:
            ctx = getattr(self.combo.window(), "ctx", None)
            if ctx is not None:
                qss = getattr(ctx, "qss", "")
        if qss:
            self.setStyleSheet(qss)

        self.search.blockSignals(True)
        self.search.clear()
        self.search.setPlaceholderText("Search…" if i18n.is_en() else "Tìm nhanh…")
        self.search.blockSignals(False)
        self._refilter("")

        # Tính kích thước thoáng hiển thị nhiều mục (tới ~12–14 mục cùng lúc)
        n = self.combo.count()
        pop_w = max(self.combo.width(), 260)
        fm = self.lst.fontMetrics()
        max_tw = max((fm.horizontalAdvance(self.combo.itemText(i)) for i in range(min(n, 80))), default=180)
        pop_w = min(420, max(pop_w, max_tw + 48))
        rows_h = min(380, max(96, min(n, 13) * 31 + 12))
        pop_h = rows_h + 50
        self.resize(pop_w, pop_h)

        # Định vị ngay dưới (hoặc lật lên trên nếu gần mép đáy màn hình)
        gp = self.combo.mapToGlobal(QPoint(0, self.combo.height() + 3))
        scr = QGuiApplication.screenAt(gp) or QGuiApplication.primaryScreen()
        if scr is not None:
            ag = scr.availableGeometry()
            if gp.y() + pop_h > ag.bottom() - 6:
                gp.setY(max(ag.top() + 6, self.combo.mapToGlobal(QPoint(0, 0)).y() - pop_h - 3))
            if gp.x() + pop_w > ag.right() - 6:
                gp.setX(max(ag.left() + 6, ag.right() - pop_w - 6))
        self.move(gp)
        self.show()
        self.search.setFocus()

    def _refilter(self, query: str):
        q = _norm_search(query)
        vi_items = self.combo.property("_vi_items")
        cur_idx = self.combo.currentIndex()
        self.lst.setUpdatesEnabled(False)
        self.lst.clear()
        sel_row = -1
        for i in range(self.combo.count()):
            txt = self.combo.itemText(i)
            vi_txt = vi_items[i] if isinstance(vi_items, list) and i < len(vi_items) else ""
            if not q or q in _norm_search(txt) or (vi_txt and q in _norm_search(vi_txt)):
                it = QListWidgetItem(txt)
                it.setData(Qt.UserRole, i)
                self.lst.addItem(it)
                if i == cur_idx:
                    sel_row = self.lst.count() - 1
        self.lst.setUpdatesEnabled(True)
        shown = self.lst.count()
        total = self.combo.count()
        self.lbl_cnt.setText(f"{shown}" if shown == total else f"{shown}/{total}")
        if sel_row >= 0:
            self.lst.setCurrentRow(sel_row)
            self.lst.scrollToItem(self.lst.item(sel_row))
        elif shown > 0:
            self.lst.setCurrentRow(0)

    def _choose(self, it: QListWidgetItem):
        idx = it.data(Qt.UserRole)
        self.hide()
        if isinstance(idx, int) and 0 <= idx < self.combo.count():
            self.combo.setCurrentIndex(idx)
            self.combo.activated.emit(idx)


class SearchableComboBox(QComboBox):
    """QComboBox có ô tìm kiếm tích hợp ngay trong danh sách thả xuống, chống cuộn chuột nhầm."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup = None

    def showPopup(self):
        if self._popup is None:
            self._popup = _ComboPopup(self)
        self._popup.open_for()

    def hidePopup(self):
        if self._popup is not None:
            self._popup.hide()
        super().hidePopup()


def fix_combo(cmb: QComboBox, min_chars: int = 8, fixed_w: int = None, searchable: bool = False) -> QComboBox:
    """Ngăn QComboBox tự phình ngang theo mục dài nhất, chặn cuộn chuột nhầm và hỗ trợ tìm kiếm tích hợp trong danh sách."""
    if searchable and not isinstance(cmb, SearchableComboBox):
        cmb.deleteLater()
        cmb = SearchableComboBox()
    cmb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    cmb.setMinimumContentsLength(min_chars)
    if fixed_w is not None:
        cmb.setFixedWidth(fixed_w)
        cmb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    else:
        cmb.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    no_wheel(cmb)
    return cmb


def shrink_x(w: QWidget) -> QWidget:
    """Cho phép widget co ngang linh hoạt trong khung hẹp thay vì đẩy tràn bố cục."""
    sp = w.sizePolicy()
    sp.setHorizontalPolicy(QSizePolicy.Ignored)
    w.setSizePolicy(sp)
    return w


def mk_label(text, kind=None, wrap=False):
    lb = QLabel(text)
    if kind:
        lb.setProperty(kind, True)
    lb.setWordWrap(wrap)
    return lb


def mk_sep(vertical=False):
    f = QFrame()
    f.setProperty("sep", True)
    if vertical:
        f.setFixedWidth(1)
    else:
        f.setFixedHeight(1)
    return f


def mk_card(layout=None, margins=(14, 12, 14, 12), spacing=8):
    f = QFrame()
    f.setProperty("card", True)
    if layout is None:
        layout = QVBoxLayout()
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    f.setLayout(layout)
    return f


def copy_image(img) -> bool:
    if isinstance(img, QPixmap):
        QGuiApplication.clipboard().setPixmap(img)
    else:
        QGuiApplication.clipboard().setImage(img)
    return True


def copy_text(t: str):
    QGuiApplication.clipboard().setText(t)


def save_bytes_dialog(parent, data: bytes, title: str, flt: str, default: str) -> bool:
    path, _ = QFileDialog.getSaveFileName(parent, title, default, flt)
    if not path:
        return False
    with open(path, "wb") as f:
        f.write(data)
    return True


class ImageView(QWidget):
    """Hiển thị ảnh PNG (đã render ở 2× độ phân giải) vừa khung, nền tùy chọn có viền mịn."""
    clicked = Signal()

    def __init__(self, min_h=140, parent=None):
        super().__init__(parent)
        self.pix = None
        self.bg = None
        self.text = ""
        self.setMinimumHeight(min_h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_png(self, data: bytes, dpr=2.0):
        pm = QPixmap()
        pm.loadFromData(data)
        pm.setDevicePixelRatio(1.0)
        self.pix, self.dpr, self.text = pm, dpr, ""
        self.update()

    def set_pixmap(self, pm, dpr=1.0):
        self.pix, self.dpr, self.text = pm, dpr, ""
        self.update()

    def set_text(self, t):
        self.pix, self.text = None, t
        self.update()

    def set_bg(self, color):
        self.bg = QColor(color) if color else None
        self.update()

    def current_pixmap(self):
        return self.pix

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.bg:
            border_c = QColor("#28354D") if self.bg.lightness() < 120 else QColor("#E2E8F0")
            p.setPen(QPen(border_c, 1))
            p.setBrush(self.bg)
            p.drawRoundedRect(r, 10, 10)
        if self.pix:
            pw, ph = self.pix.width() / self.dpr, self.pix.height() / self.dpr
            if pw > 0 and ph > 0:
                s = min(1.3, (r.width() - 20) / pw, (r.height() - 20) / ph)
                w, h = pw * s, ph * s
                p.drawPixmap(QRectF(r.center().x() - w / 2, r.center().y() - h / 2, w, h), self.pix, QRectF(self.pix.rect()))
        elif self.text:
            p.setPen(QColor("#94A3B8"))
            p.drawText(r.adjusted(16, 12, -16, -12), Qt.AlignCenter | Qt.TextWordWrap, self.text)

    def mousePressEvent(self, e):
        self.clicked.emit()
