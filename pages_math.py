# -*- coding: utf-8 -*-
"""pages_math.py - Phần TOÁN HỌC: soạn/vẽ công thức LaTeX (400+ mẫu) và Hình học động · Đồ thị hiện đại."""
import re

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QScrollArea, QSizePolicy, QSpinBox,
                               QSplitter, QStackedWidget, QTabWidget, QVBoxLayout, QWidget)

import calc_engine as ce
import data_math as dm
import data_store as ds
import formula_engine as fe
import formula_vars as fv
import i18n
import i18n_data
import icons
import natural_display as nd
from geometry_canvas import FIGURES, TOOLS as GEO_TOOLS, GeometryCanvas
from ocr_ui import ask_ocr
from pages_chem import BG_CHOICES, COLOR_CHOICES, scroll_wrap
from ui_common import ACCENTS, ImageView, PALETTES, copy_image, copy_text, esc, fix_combo, mk_btn, mk_card, mk_label, mk_sep, no_wheel, save_bytes_dialog, shrink_x
from word_ui import qimage_png, word_button


class MathFormulaPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.last_png = None
        self._syncing = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.render)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.fill)
        self._icon_btns = []
        self._theme_dirty = False
        self._build()
        self._load_formula(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}", prefer_visual=True)
        self.render()

    def showEvent(self, e):
        super().showEvent(e)
        if self._theme_dirty:
            self._theme_dirty = False
            self.render()

    def _ibtn(self, text, icon_name, primary=False, tip="", prop=None):
        b = mk_btn(text, primary=primary, tip=tip, prop=prop)
        b.setProperty("_ic", icon_name)
        b.setIconSize(QSize(16, 16))
        self._icon_btns.append(b)
        return b

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(8)

        # ---- Thanh công cụ trên cùng
        top_card = mk_card(QVBoxLayout(), margins=(10, 8, 10, 8), spacing=8)
        tb = QHBoxLayout()
        tb.setSpacing(5)
        b1 = self._ibtn("Sao chép", "copy", primary=True, tip="Sao chép ảnh công thức độ nét cao vào clipboard")
        b1.clicked.connect(self.copy_img)
        b2 = self._ibtn("Quét ảnh", "camera", tip="Nhận diện công thức từ ảnh sang LaTeX (Gemini AI)")
        b2.clicked.connect(self.do_ocr)
        self.b_fav = self._ibtn("Lưu mẫu", "star", tip="Lưu công thức hiện tại vào danh sách Yêu thích")
        self.b_fav.clicked.connect(self.add_fav)
        b_clr = self._ibtn("Xóa", "trash", prop=("danger", True))
        b_clr.clicked.connect(self._clear_all)
        for b in (b1, b2, self.b_fav):
            tb.addWidget(b)
        tb.addWidget(word_button(self.ctx, self, lambda: {"kind": "math", "latex": self.effective()} if self.effective() else None))
        tb.addWidget(b_clr)
        tb.addStretch()
        b_lat = mk_btn("LaTeX", prop=("subtle", True), tip="Sao chép mã LaTeX vào clipboard")
        b_lat.clicked.connect(lambda: (copy_text(self.effective()), self.ctx.say("Đã sao chép mã LaTeX.")))
        b_svg = self._ibtn("SVG", "save", tip="Xuất tệp vector SVG")
        b_svg.clicked.connect(lambda: self.save("svg"))
        b_png = self._ibtn("PNG", "save", tip="Xuất ảnh PNG 300 DPI")
        b_png.clicked.connect(lambda: self.save("png"))
        for b in (b_lat, b_svg, b_png):
            tb.addWidget(b)
        top_card.layout().addLayout(tb)

        # ---- Khu vực soạn thảo (trái: Trực quan WYSIWYG <-> Mã LaTeX) + xem trước trực tiếp (phải)
        sp = QSplitter(Qt.Horizontal)
        left = QWidget()
        left.setMinimumWidth(290)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)
        ll.setSpacing(6)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self.b_mode_vis = mk_btn("Trực quan", checkable=True, prop=("seg", True),
                                 tip="Sửa trực tiếp trên công thức (WYSIWYG): bấm vào ô để sửa, gõ / phân số, ^ mũ, _ chỉ số, Tab nhảy ô")
        self.b_mode_tex = mk_btn("Mã LaTeX", checkable=True, prop=("seg", True),
                                 tip="Chỉnh sửa trực tiếp mã nguồn LaTeX (hỗ trợ đầy đủ ma trận, tích phân, tổng, hệ phương trình)")
        self.b_mode_vis.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.b_mode_tex.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.b_mode_vis.clicked.connect(lambda: self._set_edit_mode(0))
        self.b_mode_tex.clicked.connect(lambda: self._set_edit_mode(1))
        mode_row.addWidget(self.b_mode_vis)
        mode_row.addWidget(self.b_mode_tex)
        mode_row.addStretch(1)
        ll.addLayout(mode_row)

        self.mode_hint_box = QFrame()
        self.mode_hint_box.setProperty("panel", True)
        self.mode_hint_lay = QHBoxLayout(self.mode_hint_box)
        self.mode_hint_lay.setContentsMargins(8, 4, 8, 4)
        self.mode_hint_lay.setSpacing(5)
        self.lbl_mode_hint = shrink_x(mk_label("", "muted"))
        self.lbl_mode_hint.setProperty("_i18n_skip", True)
        self._hint_kind = "visual"

        self.edit_stack = QStackedWidget()
        self.edit_stack.setMinimumHeight(96)
        self.edit_stack.setMaximumHeight(186)

        self.visual = nd.NaturalDisplay(24, formula_mode=True, min_h=96, max_h=182)
        self.visual.placeholder = "Nhấp để gõ trực tiếp (/ phân số · ^ mũ · _ chỉ số · Tab chuyển ô)"
        self.visual.changed.connect(self._visual_changed)
        self.edit_stack.addWidget(self.visual)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Cascadia Code", 10.5))
        self.editor.setMinimumHeight(92)
        self.editor.setMaximumHeight(182)
        self.editor.setPlaceholderText(r"Nhập mã LaTeX, VD: \int_0^1 x^2\,dx = \frac{1}{3}")
        self.editor.textChanged.connect(self._text_changed)
        self.edit_stack.addWidget(self.editor)
        ll.addWidget(self.edit_stack)
        ll.addWidget(self.mode_hint_box)

        # ---- Thay số nhanh + tính giá trị
        self.var_edits = {}
        self.var_box = QFrame()
        self.var_box.setProperty("panel", True)
        vb = QVBoxLayout(self.var_box)
        vb.setContentsMargins(10, 7, 10, 7)
        vb.setSpacing(5)
        vh = QHBoxLayout()
        vh.setSpacing(4)
        vh.addWidget(shrink_x(mk_label("Thay số nhanh", "h2")), 1)
        b_eval = mk_btn("Tính", pill=True, tip="Tính giá trị số của công thức sau khi thay số")
        b_eval.clicked.connect(self.eval_substituted)
        b_clr_v = mk_btn("Đặt lại", pill=True)
        b_clr_v.clicked.connect(self.clear_vars)
        b_apply = mk_btn("Ghi mã", pill=True, tip="Ghi công thức đã thay số vào khung soạn thảo")
        b_apply.clicked.connect(self.apply_vars)
        for bw in (b_eval, b_clr_v, b_apply):
            vh.addWidget(bw)
        vb.addLayout(vh)
        self.var_grid = QGridLayout()
        self.var_grid.setHorizontalSpacing(8)
        self.var_grid.setVerticalSpacing(4)
        vb.addLayout(self.var_grid)
        self.lbl_eval = mk_label("", "badge")
        self.lbl_eval.hide()
        vb.addWidget(self.lbl_eval)
        ll.addWidget(self.var_box)

        opt = QHBoxLayout()
        opt.setSpacing(5)
        opt.addWidget(mk_label("Cỡ:", "muted"))
        self.spin = no_wheel(QSpinBox())
        self.spin.setRange(12, 80)
        self.spin.setValue(30)
        self.spin.setSuffix(" pt")
        self.spin.setFixedWidth(64)
        self.spin.valueChanged.connect(lambda: self.timer.start(140))
        opt.addWidget(self.spin)
        self.cmb_col = fix_combo(QComboBox(), 5, fixed_w=86)
        for n, v in COLOR_CHOICES:
            self.cmb_col.addItem(n, v)
        self.cmb_col.currentIndexChanged.connect(lambda: self.timer.start(80))
        opt.addWidget(self.cmb_col)
        self.cmb_bg = fix_combo(QComboBox(), 7, fixed_w=134)
        for n, v in BG_CHOICES:
            self.cmb_bg.addItem("Nền " + n, v)
        self.cmb_bg.currentIndexChanged.connect(lambda: self.timer.start(80))
        opt.addWidget(self.cmb_bg)
        self.chk_inline = QCheckBox("Cỡ nhỏ")
        self.chk_inline.stateChanged.connect(lambda: self.timer.start(80))
        opt.addWidget(self.chk_inline)
        opt.addStretch()
        ll.addLayout(opt)
        sp.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 0, 0, 0)
        rl.setSpacing(4)
        rl.addWidget(mk_label("XEM TRƯỚC TRỰC TIẾP", "caption"))
        self.view = ImageView(150)
        rl.addWidget(self.view, 1)
        self.lbl_err = QLabel("")
        self.lbl_err.setWordWrap(True)
        self.lbl_err.setStyleSheet("color:#EF4444; font-size:12px;")
        rl.addWidget(self.lbl_err)
        sp.addWidget(right)
        sp.setSizes([470, 560])
        top_card.layout().addWidget(sp)

        # ---- Bảng ký hiệu chèn thông minh (hỗ trợ cả Trực quan lẫn LaTeX)
        pal_card = mk_card(QVBoxLayout(), margins=(10, 6, 10, 6), spacing=2)
        self.pal = QTabWidget()
        self.pal.setFixedHeight(114)
        for name, items in ds.MATH_PALETTES.items():
            w = QWidget()
            g = QGridLayout(w)
            g.setContentsMargins(4, 4, 4, 2)
            g.setSpacing(4)
            for i, (lab, ins) in enumerate(items):
                b = mk_btn(lab, prop=("subtle", True))
                b.setMinimumWidth(44)
                b.setFixedHeight(29)
                b.setToolTip(ins)
                b.clicked.connect(lambda _, t=ins: self._smart_insert(t))
                g.addWidget(b, i // 10, i % 10)
            sc_p = scroll_wrap(w)
            sc_p.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.pal.addTab(sc_p, esc(name))
        pal_card.layout().addWidget(self.pal)

        # ---- Thư viện công thức mẫu
        lib_card = mk_card(QVBoxLayout(), margins=(12, 10, 12, 10), spacing=6)
        self.tabs = QTabWidget()
        w1 = QWidget()
        v1 = QVBoxLayout(w1)
        v1.setContentsMargins(0, 6, 0, 0)
        v1.setSpacing(6)
        fr = QHBoxLayout()
        fr.setSpacing(8)
        self.cmb_cat = fix_combo(QComboBox(), 10, fixed_w=176, searchable=True)
        self.cmb_cat.addItems(dm.MATH_CATEGORIES)
        self.cmb_cat.currentIndexChanged.connect(self.fill)
        fr.addWidget(self.cmb_cat)
        self.q = QLineEdit()
        self.q.setClearButtonEnabled(True)
        self.q.setPlaceholderText("Tìm công thức: tên, chuyên đề, LaTeX… (VD: tích phân, đạo hàm, hình cầu, Fourier, pH)")
        self.q.textChanged.connect(lambda: self.search_timer.start(100))
        fr.addWidget(self.q, 1)
        self.lbl_n = mk_label("", "badge")
        fr.addWidget(self.lbl_n)
        v1.addLayout(fr)
        self.lst = QListWidget()
        self.lst.setAlternatingRowColors(True)
        self.lst.itemClicked.connect(self.pick)
        v1.addWidget(self.lst, 1)
        self.tabs.addTab(w1, esc(f"Công thức mẫu ({len(dm.MATH_SAMPLES)})"))
        self.lst_recent = QListWidget()
        self.lst_recent.itemClicked.connect(self.pick)
        self.tabs.addTab(self.lst_recent, "Gần đây")
        self.lst_fav = QListWidget()
        self.lst_fav.itemClicked.connect(self.pick)
        self.tabs.addTab(self.lst_fav, "Yêu thích")
        lib_card.layout().addWidget(self.tabs)

        # Dùng QSplitter dọc để cả editor lẫn thư viện đều thoải mái không bị mất màn hình
        vsplit = QSplitter(Qt.Vertical)
        upper = QWidget()
        ul = QVBoxLayout(upper)
        ul.setContentsMargins(0, 0, 0, 0)
        ul.setSpacing(8)
        ul.addWidget(top_card)
        ul.addWidget(pal_card)
        vsplit.addWidget(upper)
        vsplit.addWidget(lib_card)
        vsplit.setSizes([430, 310])
        root.addWidget(vsplit, 1)

        self.fill()
        self.fill_prefs()

    def _clear_all(self):
        self._syncing = True
        self.visual.clear()
        self.editor.clear()
        self._syncing = False
        self._text_changed()

    def _update_mode_hint(self, kind: str = None):
        if kind is not None:
            self._hint_kind = kind
        k = getattr(self, "_hint_kind", "visual")
        en = i18n.is_en()
        pal = self.ctx.palette
        dark = self.ctx.dark
        acc = ACCENTS.get(self.ctx.prefs.get("accent", "Chàm"), ACCENTS["Chàm"])[1 if dark else 0]
        kbd_bg = "#1E293B" if dark else "#F1F5F9"
        kbd_bd = "#3B4C6B" if dark else "#CBD5E1"
        kbd_qss = (
            f"background:{kbd_bg}; color:{acc}; border:1px solid {kbd_bd}; "
            f"border-bottom:2px solid {kbd_bd}; border-radius:5px; "
            f"padding:1px 6px; font-family:'Cascadia Code',Consolas,monospace; "
            f"font-size:11px; font-weight:700;"
        )
        lbl_qss = f"color:{pal['muted']}; font-size:11.5px; background:transparent; border:none; padding:0px;"

        # Xóa chip cũ tức thì
        while self.mode_hint_lay.count():
            it = self.mode_hint_lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        def add_chip(key_txt: str, label_txt: str):
            kb = QLabel(key_txt)
            kb.setProperty("_i18n_skip", True)
            kb.setStyleSheet(kbd_qss)
            lb = QLabel(label_txt)
            lb.setProperty("_i18n_skip", True)
            lb.setStyleSheet(lbl_qss)
            self.mode_hint_lay.addWidget(kb)
            self.mode_hint_lay.addWidget(lb)

        if k == "visual":
            pairs = (
                [("/", "Fraction"), ("^", "Power"), ("_", "Subscript"), ("Tab", "Next")]
                if en else
                [("/", "Phân số"), ("^", "Mũ"), ("_", "Chỉ số"), ("Tab", "Ô tiếp")]
            )
            for idx, (ky, lb) in enumerate(pairs):
                if idx > 0:
                    self.mode_hint_lay.addSpacing(4)
                add_chip(ky, lb)
            self.lbl_mode_hint.setText(" · ".join(f"{ky} {lb}" for ky, lb in pairs))
        else:
            if k == "matrix":
                msg = "Matrix / multiline → LaTeX Code" if en else "Ma trận/hệ nhiều dòng → Mã LaTeX"
            elif k == "advanced":
                msg = "Advanced formula → LaTeX Code" if en else "Công thức nâng cao → Mã LaTeX"
            else:
                msg = "Supports full LaTeX syntax" if en else "Hỗ trợ mọi cú pháp LaTeX"
            add_chip("TeX", msg)
            self.lbl_mode_hint.setText(msg)
        self.mode_hint_lay.addStretch(1)

    def _set_edit_mode(self, idx: int):
        if idx == 0:
            raw = self.editor.toPlainText().strip()
            self._syncing = True
            ok = self.visual.from_latex(raw)
            self._syncing = False
            if not ok:
                self.b_mode_vis.setChecked(False)
                self.b_mode_tex.setChecked(True)
                self.edit_stack.setCurrentIndex(1)
                self._update_mode_hint("matrix")
                self.ctx.say(
                    "Multiline formula (matrix / system) — edit in LaTeX Code mode."
                    if i18n.is_en() else
                    "Công thức nhiều dòng (ma trận / hệ phương trình) — hãy chỉnh ở chế độ Mã LaTeX."
                )
                return
            self.edit_stack.setCurrentIndex(0)
            self.b_mode_vis.setChecked(True)
            self.b_mode_tex.setChecked(False)
            self._update_mode_hint("visual")
            self.visual.setFocus()
        else:
            self.edit_stack.setCurrentIndex(1)
            self.b_mode_vis.setChecked(False)
            self.b_mode_tex.setChecked(True)
            self._update_mode_hint("latex")
            self.editor.setFocus()

    def _load_formula(self, latex: str, prefer_visual=None):
        want_vis = (self.edit_stack.currentIndex() == 0) if prefer_visual is None else prefer_visual
        self._syncing = True
        self.editor.setPlainText(latex)
        if want_vis and self.visual.from_latex(latex):
            self.edit_stack.setCurrentIndex(0)
            self.b_mode_vis.setChecked(True)
            self.b_mode_tex.setChecked(False)
            self._update_mode_hint("visual")
        else:
            self.edit_stack.setCurrentIndex(1)
            self.b_mode_vis.setChecked(False)
            self.b_mode_tex.setChecked(True)
            self._update_mode_hint("advanced" if want_vis else "latex")
        self._syncing = False
        self._text_changed()

    def _visual_changed(self):
        if self._syncing:
            return
        self._syncing = True
        self.editor.setPlainText(self.visual.to_latex())
        self._syncing = False
        self._text_changed()

    def _smart_insert(self, tpl):
        if self.edit_stack.currentIndex() == 0:
            v = self.visual
            if tpl == r"\frac{a}{b}":
                v.put_frac()
                v.setFocus()
                return
            if tpl == r"\sqrt{x}":
                v.put_sqrt()
                v.setFocus()
                return
            if tpl == r"\sqrt[n]{x}":
                v.put_root()
                v.setFocus()
                return
            if tpl == r"x^{n}":
                v.put_sup()
                v.setFocus()
                return
            if tpl == r"x_{n}":
                v.put_sub()
                v.setFocus()
                return
            if tpl == r"x_{n}^{m}":
                v.put_sub()
                v.setFocus()
                return
            if tpl == r"\left| x \right|":
                v.put_abs()
                v.setFocus()
                return
            if tpl == r"\left( x \right)":
                v.put_char("(", "(")
                v.put_char(")", ")")
                v.move(-1)
                v.setFocus()
                return
            if tpl == r"\left[ x \right]":
                v.put_char("[", "[")
                v.put_char("]", "]")
                v.move(-1)
                v.setFocus()
                return
            if tpl == r"\left\{ x \right\}":
                v.put_char("{", r"\left\{")
                v.put_char("}", r"\right\}")
                v.move(-1)
                v.setFocus()
                return
            if tpl == r"\begin{cases} x + y = 1 \\ x - y = 0 \end{cases}":
                v.put_grid("cases", 2, 1)
                v.setFocus()
                return
            if tpl == r"\begin{bmatrix} a & b \\ c & d \end{bmatrix}":
                v.put_grid("bmatrix", 2, 2)
                v.setFocus()
                return
            if tpl == r"\vec{AB}":
                v.put_accent("vec")
                v.setFocus()
                return
            if tpl == r"\bar{x}":
                v.put_accent("bar")
                v.setFocus()
                return
            if tpl == r"\int_{a}^{b} f(x)\,dx":
                v.put_char("∫", r"\int")
                v.put_sub()
                v.setFocus()
                return
            if tpl == r"\sum_{i=1}^{n} x_i":
                v.put_char("∑", r"\sum")
                v.put_sub()
                v.setFocus()
                return
            if tpl == r"\lim_{x \to 0} f(x)":
                v.put_char("lim", r"\lim")
                v.put_sub()
                v.setFocus()
                return
            if tpl == r"\log_{a}(b)":
                v.put_char("log", r"\log")
                v.put_sub()
                v.setFocus()
                return
            if tpl == r"|\vec{u}|":
                v.put_abs()
                v.put_accent("vec")
                v.setFocus()
                return
            if tpl == r"\frac{\partial f}{\partial x}":
                r = nd.parse_latex_to_row(tpl)
                if r:
                    for item in r:
                        v._ins(item)
                    v._touch()
                    v.setFocus()
                    return
            m_bb = re.fullmatch(r"\\mathbb\{([A-Z])\}", tpl.strip())
            if m_bb and m_bb.group(1) in nd._MATHBB_MAP:
                ch_ = m_bb.group(1)
                v.put_char(nd._MATHBB_MAP[ch_], f"\\mathbb{{{ch_}}}")
                v.setFocus()
                return
            if tpl == "x^2":
                v.put_sup("2")
                v.setFocus()
                return
            if tpl == "x^3":
                v.put_sup("3")
                v.setFocus()
                return
            if tpl == r"e^{x}":
                v.put_char("e", "e")
                v.put_sup()
                v.setFocus()
                return
            if tpl.strip() == r"^\circ":
                v.put_char("°", r"^\circ ")
                v.setFocus()
                return
            if tpl == r"\%":
                v.put_char("%", r"\%")
                v.setFocus()
                return
            m_fn = re.fullmatch(r"\\([a-zA-Z]+)\([^)]*\)", tpl.strip())
            if m_fn and m_fn.group(1) in nd._LATEX_FUNCS:
                v.put_func(m_fn.group(1))
                v.setFocus()
                return
            m_sym = re.fullmatch(r"\\([a-zA-Z]+)\s*", tpl.strip())
            if m_sym and m_sym.group(1) in nd._LATEX_TO_UNI:
                v.put_char(nd._LATEX_TO_UNI[m_sym.group(1)], f"\\{m_sym.group(1)} ")
                v.setFocus()
                return
            if tpl in ("'", "''"):
                for ch in tpl:
                    v.put_char(ch, ch)
                v.setFocus()
                return
            # Mẫu nhiều dòng (ma trận, hệ phương trình): chuyển mượt sang Mã LaTeX
            self._set_edit_mode(1)
            self.ctx.say("Ma trận / hệ phương trình nhiều dòng dùng chế độ Mã LaTeX.")

        cur = self.editor.textCursor()
        sel = cur.selectedText()
        if sel:
            if tpl == r"\frac{a}{b}":
                cur.insertText(f"\\frac{{{sel}}}{{b}}")
                return
            if tpl == r"\sqrt{x}":
                cur.insertText(f"\\sqrt{{{sel}}}")
                return
            if tpl == r"\left( x \right)":
                cur.insertText(f"\\left( {sel} \\right)")
                return
            if tpl == r"\left| x \right|":
                cur.insertText(f"\\left| {sel} \\right|")
                return
        cur.insertText(tpl)
        self.editor.setFocus()

    def _text_changed(self):
        if self._syncing:
            return
        self._rebuild_vars()
        self.lbl_eval.hide()
        self.timer.start(200)

    def _rebuild_vars(self):
        names = fv.detect_vars(self.editor.toPlainText())
        if names == list(self.var_edits):
            return
        old = {k: e.text() for k, e in self.var_edits.items()}
        while self.var_grid.count():
            it = self.var_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.var_edits = {}
        for i, n in enumerate(names[:12]):
            r, c = i // 4, (i % 4) * 2
            lab_t = n.replace("{", "").replace("}", "").replace("_", "").translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")) if "_" in n else n
            lab = mk_label(f"{lab_t} =", "muted")
            lab.setMinimumWidth(26)
            ed = QLineEdit(old.get(n, ""))
            ed.setPlaceholderText("num…" if i18n.is_en() else "số…")
            ed.setMaximumWidth(86)
            ed.textChanged.connect(lambda _: (self.lbl_eval.hide(), self.timer.start(180)))
            self.var_grid.addWidget(lab, r, c)
            self.var_grid.addWidget(ed, r, c + 1)
            self.var_edits[n] = ed
        self.var_box.setVisible(bool(names))

    def effective(self):
        t = self.editor.toPlainText().strip()
        return fv.substitute(t, {k: e.text() for k, e in self.var_edits.items()}) if t else ""

    def clear_vars(self):
        for e in self.var_edits.values():
            e.clear()
        self.lbl_eval.hide()

    def apply_vars(self):
        t = self.effective()
        if t:
            self.clear_vars()
            self._load_formula(t)

    def eval_substituted(self):
        """Thử tính giá trị số cho vế phải (hoặc toàn bộ biểu thức) sau khi đã thay số."""
        raw = self.effective()
        if not raw:
            return
        rhs = raw.split("=")[-1].strip() if "=" in raw else raw
        expr = rhs
        # Chuyển một số lệnh LaTeX phổ biến sang cú pháp Calc
        for _ in range(4):
            expr = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", expr)
            expr = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", expr)
        expr = (expr.replace(r"\cdot", "*").replace(r"\times", "*").replace(r"\pi", "pi")
                    .replace(r"\sin", "sin").replace(r"\cos", "cos").replace(r"\tan", "tan")
                    .replace(r"\ln", "ln").replace(r"\lg", "log").replace(r"\left", "").replace(r"\right", "")
                    .replace("{", "(").replace("}", ")").replace(",", "."))
        try:
            calc = ce.Calc()
            val = calc.evaluate(expr)
            ex = ce.exact_form(val) if not isinstance(val, (int, complex)) else None
            lbl_res = "Result ≈" if i18n.is_en() else "Kết quả ≈"
            txt = f"{lbl_res} {ce.fmt_num(val, 10)}" + (f"  (= {ex})" if ex else "")
            self.lbl_eval.setProperty("_i18n_skip", True)
            self.lbl_eval.setText(txt)
            self.lbl_eval.show()
        except Exception:
            self.lbl_eval.setProperty("_i18n_skip", True)
            self.lbl_eval.setText(
                "Please enter numeric values for all variables (basic algebraic/trig expressions only)."
                if i18n.is_en() else
                "Hãy nhập đủ giá trị số cho các biến (chỉ hỗ trợ biểu thức đại số/lượng giác cơ bản)."
            )
            self.lbl_eval.show()

    def fill(self):
        cat, q = i18n.combo_key(self.cmb_cat), self.q.text().strip().lower()
        en = i18n.is_en()
        self.lst.setUpdatesEnabled(False)
        self.lst.clear()
        n = 0
        for t, c, l in dm.MATH_SAMPLES:
            t_en = i18n_data.math_title_en(t)
            c_en = i18n.tr(c)
            if (cat == "Tất cả" or c == cat) and (not q or q in t.lower() or q in t_en.lower() or q in l.lower() or q in c.lower() or q in c_en.lower()):
                disp_t = i18n.smart_title(t_en if en else t)
                disp_c = i18n.smart_title(c_en if en else c)
                disp_l = i18n.tr_math_latex(l)
                it = QListWidgetItem(f"{disp_t}   [{disp_c}]\n{disp_l}")
                it.setData(Qt.UserRole, disp_l)
                self.lst.addItem(it)
                n += 1
        self.lst.setUpdatesEnabled(True)
        self.lbl_n.setProperty("_i18n_skip", True)
        self.lbl_n.setText(f"{n} formulas" if en else f"{n} mẫu")

    def fill_prefs(self):
        for lst, key in ((self.lst_recent, "math_recents"), (self.lst_fav, "math_favorites")):
            lst.clear()
            for e in self.ctx.prefs.get(key, []):
                it = QListWidgetItem(e)
                it.setData(Qt.UserRole, e)
                lst.addItem(it)

    def pick(self, it):
        e = it.data(Qt.UserRole)
        self._load_formula(e, prefer_visual=(self.edit_stack.currentIndex() == 0))
        rec = [x for x in self.ctx.prefs.get("math_recents", []) if x != e]
        rec.insert(0, e)
        self.ctx.prefs["math_recents"] = rec[:40]
        self.ctx.save_prefs()
        self.fill_prefs()

    def add_fav(self):
        e = self.editor.toPlainText().strip()
        if e:
            fav = self.ctx.prefs.setdefault("math_favorites", [])
            if e not in fav:
                fav.insert(0, e)
            self.ctx.save_prefs()
            self.fill_prefs()
            self.ctx.say("Đã thêm công thức vào Yêu thích.")

    def render(self):
        t = self.effective()
        if not t:
            self.view.set_text(
                "Type directly in Visual mode, enter LaTeX code, or choose a sample below…"
                if i18n.is_en() else
                "Gõ trực tiếp ở khung Trực quan hoặc nhập mã LaTeX, chọn mẫu bên dưới…"
            )
            self.last_png = None
            self.lbl_err.setText("")
            return
        bg, col = self.cmb_bg.currentData(), self.cmb_col.currentData()
        try:
            self.last_png = fe.render_formula_to_bytes(t, self.spin.value(), col, bg, not self.chk_inline.isChecked(), "png", 200)
            self.view.set_png(self.last_png, 2.0)
            self.view.set_bg({"transparent": ("#0B1120" if QColor(col).lightness() > 140 else "#FFFFFF"), "white": "#FFFFFF", "dark": "#0B1120"}[bg])
            self.lbl_err.setText("")
        except Exception as exc:
            self.lbl_err.setText(f"{'Check LaTeX syntax' if i18n.is_en() else 'Kiểm tra cú pháp LaTeX'}: {str(exc)[:160]}")

    def copy_img(self):
        if self.last_png:
            pm = QPixmap()
            pm.loadFromData(self.last_png)
            copy_image(pm)
            self.ctx.say("Đã sao chép ảnh công thức.")

    def save(self, fmt):
        try:
            data = fe.render_formula_to_bytes(self.effective(), self.spin.value(), self.cmb_col.currentData(), self.cmb_bg.currentData(), not self.chk_inline.isChecked(), fmt, 300)
            save_bytes_dialog(self, data, "Lưu", f"{fmt.upper()} (*.{fmt})", f"cong_thuc.{fmt}")
        except Exception as exc:
            self.lbl_err.setText(str(exc))

    def do_ocr(self):
        t = ask_ocr(self, self.ctx, "math")
        if t:
            self._load_formula(t)

    def refresh_theme(self):
        c = self.ctx.palette
        acc = ACCENTS.get(self.ctx.prefs.get("accent", "Chàm"), ACCENTS["Chàm"])[0]
        self.visual.set_colors(c["text"], c["muted"], c["input"], c["border"], acc)
        self._update_mode_hint()
        for b in self._icon_btns:
            ic = b.property("_ic")
            col = "#FFFFFF" if b.property("primary") else (c["danger"] if b.property("danger") else c["muted"])
            b.setIcon(icons.make_icon(ic, col, col, size=16))
        if self.isVisible():
            self.render()
        else:
            self._theme_dirty = True


# ==============================================================================
# HÌNH HỌC ĐỘNG · ĐỒ THỊ (Bố cục Studio hiện đại)
# ==============================================================================
GEO_DOCK = [
    ("CƠ BẢN", [
        ("select", "Chọn"), ("point", "• Điểm"),
        ("seg", "╱ Đoạn"), ("line", "↔ Đường"),
        ("ray", "↗ Tia"), ("vec", "→ Vectơ"),
        ("circle", "◯ Tròn"), ("circ3", "◎ 3 điểm"),
        ("poly", "⬠ Đa giác"), ("angle", "∠ Góc"),
    ]),
    ("DỰNG HÌNH", [
        ("mid", "M Tr.điểm"), ("perpbis", "⟂M Tr.trực"),
        ("perp", "⊥ Vuông"), ("para", "∥ S.song"),
        ("bis", "∠/ P.giác"), ("foot", "H Chân vg"),
        ("inter", "× Giao"), ("tangent", "⊘ Tiếp t."),
        ("reflect", "⇄ ĐX trục"), ("sym_pt", "◎ ĐX tâm"),
    ]),
    ("TÂM TAM GIÁC", [
        ("centroid", "G Trọng t."), ("circum", "O Ngoại t."),
        ("incenter", "I Nội tiếp"), ("ortho", "H₀ Trực t."),
    ]),
    ("KHÁC", [
        ("text", "T Chú thích"), ("erase", "✕ Xóa"),
    ]),
]

QUICK_FUNCS = [
    ("Parabol", "x^2 - 2x - 3"),
    ("Bậc 3", "x^3 - 3x"),
    ("sin(x)", "sin(x)"),
    ("cos(x)", "cos(x)"),
    ("1/x", "1/x"),
    ("ln(x)", "ln(x)"),
    ("eˣ", "exp(x)"),
    ("√x", "sqrt(x)"),
]

SWATCHES = ["#2563EB", "#E11D48", "#059669", "#D97706", "#7C3AED", "#0891B2"]


class GeometryPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.btns = {}
        self._icon_btns = []
        self._build()
        self.choose("select")

    def _ibtn(self, text, icon_name, primary=False, tip="", prop=None):
        b = mk_btn(text, primary=primary, tip=tip, prop=prop)
        b.setProperty("_ic", icon_name)
        b.setIconSize(QSize(16, 16))
        self._icon_btns.append(b)
        return b

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(8)

        # ---- 1. Thanh hành động gọn phía trên
        top = mk_card(QHBoxLayout(), margins=(8, 6, 8, 6), spacing=4)
        tl = top.layout()
        for txt, ic, fn, tip in (
            ("", "undo", lambda: self.cv.undo(), "Hoàn tác (Ctrl+Z)"),
            ("", "redo", lambda: self.cv.redo(), "Làm lại (Ctrl+Y)"),
            ("", "zoom_out", lambda: self.cv.zoom_by(1 / 1.22), "Thu nhỏ (1% – 1250%, phím -)"),
            ("", "zoom_in", lambda: self.cv.zoom_by(1.22), "Phóng to (1% – 1250%, phím +)"),
            ("Vừa hình", "fit", lambda: self.cv.fit_view(), "Thu phóng vừa khít hình (F)"),
            ("Gốc O", "grid", lambda: self.cv.center_origin(), "Đưa gốc tọa độ O về giữa (0)"),
        ):
            b = self._ibtn(txt, ic, tip=tip, prop=("subtle", True))
            if not txt:
                b.setFixedSize(28, 28)
            b.clicked.connect(fn)
            tl.addWidget(b)
        tl.addWidget(mk_sep(vertical=True))
        b_clr = self._ibtn("Xóa", "trash", tip="Xóa toàn bộ vùng vẽ", prop=("danger", True))
        b_clr.clicked.connect(lambda: self.cv.clear_all())
        tl.addWidget(b_clr)
        tl.addStretch()

        b_sum = mk_btn("Đo", tip="Tóm tắt số đo các đối tượng", prop=("subtle", True))
        b_sum.clicked.connect(self.summary)
        b_open = mk_btn("Mở", tip="Mở tệp .geo", prop=("subtle", True))
        b_open.clicked.connect(self.open_geo)
        b_save = mk_btn("Lưu", tip="Lưu tệp .geo", prop=("subtle", True))
        b_save.clicked.connect(self.save_geo)
        b_cp = self._ibtn("Sao chép", "copy", primary=True, tip="Sao chép ảnh hình vẽ")
        b_cp.clicked.connect(self.copy_img)
        b_png = self._ibtn("PNG", "save", tip="Xuất ảnh PNG")
        b_png.clicked.connect(lambda: self.save("png"))
        b_svg = self._ibtn("SVG", "save", tip="Xuất tệp vector SVG")
        b_svg.clicked.connect(lambda: self.save("svg"))
        for w in (b_sum, b_open, b_save, b_cp,
                  word_button(self.ctx, self, lambda: {"kind": "image", "png": qimage_png(self.cv.export_pixmap()), "dpi": 192, "title": "Hình học"} if self.cv.order or self.cv.objs else None),
                  b_png, b_svg):
            tl.addWidget(w)
        root.addWidget(top)

        # ---- 2. Khu vực làm việc 3 cột: Dock trái | Canvas giữa | Inspector phải
        main_row = QHBoxLayout()
        main_row.setSpacing(8)

        # --- Dock công cụ trái (2 cột gọn)
        dock_inner = QWidget()
        dl = QVBoxLayout(dock_inner)
        dl.setContentsMargins(6, 8, 10, 8)
        dl.setSpacing(8)
        for gname, items in GEO_DOCK:
            dl.addWidget(mk_label(gname, "caption"))
            grid = QGridLayout()
            grid.setSpacing(4)
            for idx, (k, lab) in enumerate(items):
                b = mk_btn(lab, tip=GEO_TOOLS[k][0], checkable=True, prop=("tool", True))
                b.setFixedHeight(29)
                b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
                b.clicked.connect(lambda _, kk=k: self.choose(kk))
                self.btns[k] = b
                grid.addWidget(b, idx // 2, idx % 2)
            dl.addLayout(grid)
        dl.addStretch()
        dock_card = mk_card(QVBoxLayout(), margins=(0, 0, 0, 0), spacing=0)
        dock_sc = scroll_wrap(dock_inner)
        dock_sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        dock_card.layout().addWidget(dock_sc)
        dock_card.setFixedWidth(220)
        main_row.addWidget(dock_card)

        # --- Canvas trung tâm
        center_col = QVBoxLayout()
        center_col.setSpacing(6)
        fr = mk_card(QVBoxLayout(), margins=(4, 4, 4, 4), spacing=0)
        self.cv = GeometryCanvas()
        self.cv.status.connect(self._on_cv_status)
        self.cv.info_changed.connect(lambda t: self.lbl_sel.setText(
            t or (
                "Tip: drag points, labels, or notes freely · scroll to zoom 1%–1250%"
                if i18n.is_en() else
                "Mẹo: kéo điểm/nhãn/chú thích để bố trí đẹp · cuộn chuột thu phóng 1%–1250%"
            )
        ))
        self.cv.tool_changed.connect(self.sync_tool)
        self.cv.objs_changed.connect(self._sync_func_list)
        fr.layout().addWidget(self.cv)
        center_col.addWidget(fr, 1)

        info_bar = mk_card(QHBoxLayout(), margins=(12, 6, 12, 6), spacing=8)
        self.lbl_sel = mk_label("Mẹo: ở chế độ Chọn có thể kéo điểm, kéo tên điểm (A, B…), số đo góc/cạnh và chú thích · nhấp đúp để đổi tên/nội dung", "muted", True)
        info_bar.layout().addWidget(self.lbl_sel, 1)
        center_col.addWidget(info_bar)
        main_row.addLayout(center_col, 1)

        # --- Inspector bên phải
        side = QWidget()
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 10, 0)
        sv.setSpacing(8)

        # Đồ thị hàm số
        g2 = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=6)
        g2.layout().addWidget(shrink_x(mk_label("ĐỒ THỊ  y = f(x)", "caption")))
        frow = QHBoxLayout()
        frow.setSpacing(5)
        self.fx = shrink_x(QLineEdit())
        self.fx.setPlaceholderText("VD: x^2 - 2x - 3 | sin(x)")
        self.fx.returnPressed.connect(self.add_func)
        frow.addWidget(self.fx, 1)
        bf = mk_btn("Vẽ", primary=True)
        bf.clicked.connect(self.add_func)
        frow.addWidget(bf)
        g2.layout().addLayout(frow)

        # Chip hàm mẫu nhanh (3 cột đều nhau)
        qgrid = QGridLayout()
        qgrid.setSpacing(4)
        for idx, (lab, ex) in enumerate(QUICK_FUNCS):
            b = mk_btn(lab, pill=True, tip=f"Vẽ y = {ex}")
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, e_=ex: self._plot_preset(e_))
            qgrid.addWidget(b, idx // 3, idx % 3)
        g2.layout().addLayout(qgrid)

        # Danh sách đồ thị đang vẽ (ẩn/hiện, xóa nhanh)
        self.lst_funcs = shrink_x(QListWidget())
        self.lst_funcs.setMaximumHeight(92)
        self.lst_funcs.setToolTip("Nhấp đúp để ẩn/hiện đồ thị; bấm nút Xóa bên dưới để bỏ")
        self.lst_funcs.itemDoubleClicked.connect(self._toggle_func_vis)
        g2.layout().addWidget(self.lst_funcs)
        fbtns = QHBoxLayout()
        fbtns.setSpacing(5)
        b_ftog = shrink_x(mk_btn("Ẩn / Hiện", pill=True))
        b_ftog.clicked.connect(lambda: self._toggle_func_vis(self.lst_funcs.currentItem()))
        b_fdel = shrink_x(mk_btn("Xóa đồ thị", pill=True))
        b_fdel.clicked.connect(self._del_selected_func)
        fbtns.addWidget(b_ftog, 1)
        fbtns.addWidget(b_fdel, 1)
        g2.layout().addLayout(fbtns)
        sv.addWidget(g2)

        # Hình mẫu 2D & 3D
        g1 = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=6)
        g1.layout().addWidget(shrink_x(mk_label(f"HÌNH MẪU 2D · 3D ({len(FIGURES)})", "caption")))
        self.cmb_fig = fix_combo(QComboBox(), 6, searchable=True)
        self.cmb_fig.setMaxVisibleItems(20)
        self.cmb_fig.addItems(["— chọn hình để chèn —"] + FIGURES)
        self.cmb_fig.activated.connect(lambda i: i and (self.cv.add_figure(FIGURES[i - 1]), self.cmb_fig.setCurrentIndex(0)))
        g1.layout().addWidget(self.cmb_fig)
        sv.addWidget(g1)

        # Kiểu nét & màu nhanh
        g4 = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=6)
        g4.layout().addWidget(shrink_x(mk_label("KIỂU NÉT & MÀU", "caption")))
        sw_row = QHBoxLayout()
        sw_row.setSpacing(4)
        for hx in SWATCHES:
            sb = mk_btn("", tip=f"Chọn màu {hx}")
            sb.setFixedSize(22, 22)
            sb.setStyleSheet(f"background:{hx}; border-radius:11px; border:1.5px solid rgba(148,163,184,0.65); padding:0;")
            sb.clicked.connect(lambda _, col=hx: self._set_color(col))
            sw_row.addWidget(sb)
        self.b_col = shrink_x(mk_btn("Khác…", pill=True))
        self.b_col.clicked.connect(self.pick_color)
        sw_row.addWidget(self.b_col, 1)
        g4.layout().addLayout(sw_row)

        rw = QHBoxLayout()
        rw.setSpacing(6)
        self.ck_dash = shrink_x(QCheckBox("Nét đứt"))
        self.ck_dash.stateChanged.connect(lambda s: setattr(self.cv, "cur_dashed", bool(s)))
        rw.addWidget(self.ck_dash, 1)
        rw.addWidget(mk_label("Dày:", "muted"))
        self.sp_w = no_wheel(QDoubleSpinBox())
        self.sp_w.setRange(0.5, 8)
        self.sp_w.setValue(2.0)
        self.sp_w.setSingleStep(0.5)
        self.sp_w.setFixedWidth(70)
        self.sp_w.valueChanged.connect(lambda v: setattr(self.cv, "cur_width", v))
        rw.addWidget(self.sp_w)
        g4.layout().addLayout(rw)
        sv.addWidget(g4)

        # Hiển thị
        g3 = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=4)
        g3.layout().addWidget(shrink_x(mk_label("HIỂN THỊ", "caption")))
        for text, attr, init in (
            ("Lưới tọa độ", "show_grid", True),
            ("Trục Ox, Oy", "show_axes", True),
            ("Tên điểm", "show_labels", True),
            ("Hiện số đo (dài, góc, S)", "show_measure", True),
            ("Tô màu đa giác", "fill_polys", True),
            ("Bắt điểm vào lưới", "snap", True),
        ):
            ck = shrink_x(QCheckBox(text))
            ck.setChecked(init)
            ck.stateChanged.connect(lambda s, a=attr: (setattr(self.cv, a, bool(s)), self.cv.update()))
            g3.layout().addWidget(ck)
        sv.addWidget(g3)
        sv.addStretch()

        sc = scroll_wrap(side)
        sc.setFixedWidth(292)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_row.addWidget(sc)
        root.addLayout(main_row, 1)

    def choose(self, k):
        self.cv.set_tool(k)

    def _on_cv_status(self, msg):
        self.ctx.say(msg)
        if msg:
            self.lbl_sel.setText(msg)

    def sync_tool(self, k):
        for kk, b in self.btns.items():
            b.setChecked(kk == k)

    def _set_color(self, hex_col):
        self.cv.cur_color = hex_col
        self.ctx.say(f"Đã chọn màu nét {hex_col}")

    def pick_color(self):
        c = QColorDialog.getColor(QColor(self.cv.cur_color), self)
        if c.isValid():
            self._set_color(c.name())

    def _plot_preset(self, expr):
        try:
            self.cv.add_function(expr)
            self.ctx.say(f"Đã vẽ đồ thị y = {expr}")
        except ce.CalcError as exc:
            self.ctx.say(f"Lỗi vẽ đồ thị: {exc}")

    def add_func(self):
        t = self.fx.text().strip()
        if not t:
            return
        try:
            self.cv.add_function(t)
            self.fx.clear()
        except ce.CalcError as exc:
            self.ctx.say(f"Hàm không hợp lệ: {exc}")

    def _sync_func_list(self):
        self.lst_funcs.clear()
        for i, o in enumerate(self.cv.objs):
            if o["type"] == "func":
                mark = "○ [ẩn] " if o["hidden"] else "● "
                it = QListWidgetItem(f"{mark}y = {o['expr']}")
                it.setData(Qt.UserRole, i)
                it.setForeground(QColor(o["color"]))
                self.lst_funcs.addItem(it)

    def _toggle_func_vis(self, it):
        if not it:
            return
        idx = it.data(Qt.UserRole)
        if 0 <= idx < len(self.cv.objs):
            self.cv.objs[idx]["hidden"] = not self.cv.objs[idx]["hidden"]
            self._sync_func_list()
            self.cv.update()

    def _del_selected_func(self):
        it = self.lst_funcs.currentItem()
        if not it:
            return
        idx = it.data(Qt.UserRole)
        if 0 <= idx < len(self.cv.objs):
            self.cv.push_undo()
            self.cv.delete_obj(idx)
            self.cv.update()

    def copy_img(self):
        copy_image(QPixmap.fromImage(self.cv.export_pixmap()))
        self.ctx.say("Đã sao chép ảnh hình vẽ.")

    def save(self, fmt):
        if fmt == "png":
            path, _ = QFileDialog.getSaveFileName(self, "Lưu PNG", "hinh_hoc.png", "PNG (*.png)")
            if path:
                self.cv.export_pixmap().save(path, "PNG")
        else:
            save_bytes_dialog(self, self.cv.export_svg_bytes(), "Lưu SVG", "SVG (*.svg)", "hinh_hoc.svg")

    def save_geo(self):
        save_bytes_dialog(self, self.cv.to_json().encode("utf-8"), "Lưu hình", "Hình học (*.geo)", "hinh.geo")

    def open_geo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Mở hình", "", "Hình học (*.geo)")
        if path:
            try:
                self.cv.from_json(open(path, encoding="utf-8").read())
            except Exception as exc:
                self.ctx.say(f"Không mở được tệp: {exc}")

    def summary(self):
        t = self.cv.summary_text()
        self.lbl_sel.setText(
            t.replace("\n", "  |  ") if t else ("No objects to measure yet." if i18n.is_en() else "Chưa có đối tượng nào để đo.")
        )

    def refresh_theme(self):
        c = self.ctx.palette
        self.cv.set_dark(self.ctx.dark, c["canvas"], c["grid"])
        for b in self._icon_btns:
            ic = b.property("_ic")
            col = "#FFFFFF" if b.property("primary") else (c["danger"] if b.property("danger") else c["muted"])
            b.setIcon(icons.make_icon(ic, col, col, size=16))


class MathSection(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.formula = MathFormulaPage(ctx)
        self.geo = GeometryPage(ctx)
        self.tabs.addTab(self.formula, esc("Công thức Toán (LaTeX)"))
        self.tabs.addTab(self.geo, esc("Hình học động · Đồ thị"))
        lay.addWidget(self.tabs)

    def refresh_theme(self):
        self.geo.refresh_theme()
        self.formula.refresh_theme()

    def refresh_lang(self):
        self.formula.fill()
        en = i18n.is_en()
        for ed in self.formula.var_edits.values():
            ed.setPlaceholderText("num…" if en else "số…")
        self.formula.visual.placeholder = (
            "Click to type visually (/ fraction · ^ power · _ subscript · Tab)"
            if en else "Nhấp để gõ trực tiếp (/ phân số · ^ mũ · _ chỉ số · Tab chuyển ô)"
        )
        self.formula._update_mode_hint()
        if not self.formula.effective():
            self.formula.render()
        self.geo.lbl_sel.setText(
            "Tip: In Select mode, drag points, point labels (A, B…), measurements & notes · double-click to edit"
            if en else
            "Mẹo: ở chế độ Chọn có thể kéo điểm, kéo tên điểm (A, B…), số đo góc/cạnh và chú thích · nhấp đúp để đổi tên/nội dung"
        )
        self.geo.cv.update()
