# -*- coding: utf-8 -*-
"""pages_chem.py - Phần HÓA HỌC: phương trình, cấu trúc SMILES, trình vẽ phân tử kiểu ChemDraw 3 cột, bảng tuần hoàn, tra cứu chất."""
import re
from urllib.parse import unquote

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QScrollArea, QSizePolicy, QSpinBox, QSplitter,
                               QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

import canvas_widgets as cw
import data_chem as dc
import data_chem_wiki as dcw
import data_store as ds
import formula_engine as fe
import i18n
import i18n_data
import icons
import molecule as mo
from ocr_ui import ask_ocr
from sketcher_canvas import ELEMENT_CHOICES, GROUPS, QUICK_ELEMENTS, QUICK_GROUPS, TEMPLATES, MoleculeSketcher
from ui_common import ACCENTS, ImageView, PALETTES, copy_image, copy_text, esc, fix_combo, mk_btn, mk_card, mk_label, mk_sep, no_wheel, save_bytes_dialog, shrink_x
from word_ui import word_button

BG_CHOICES = [("Trong suốt", "transparent"), ("Trắng", "white"), ("Tối", "dark")]
COLOR_CHOICES = [("Đen", "#111827"), ("Trắng", "#FFFFFF"), ("Xanh dương", "#1D4ED8"), ("Đỏ", "#DC2626"), ("Lục", "#15803D")]


def scroll_wrap(inner: QWidget) -> QScrollArea:
    sc = QScrollArea()
    sc.setWidgetResizable(True)
    sc.setFrameShape(QFrame.NoFrame)
    sc.setWidget(inner)
    return sc


def _sync_icon_btns(btns, dark):
    c = PALETTES["dark" if dark else "light"]
    for b in btns:
        ic = b.property("_ic")
        if not ic:
            continue
        col = "#FFFFFF" if b.property("primary") else (c["danger"] if b.property("danger") else c["muted"])
        b.setIcon(icons.make_icon(ic, col, col, size=16))


# ==============================================================================
# HÓA TRỊ & TÍNH TAN
# ==============================================================================
class ValenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bảng hóa trị · Tính tan · Dãy hoạt động")
        self.resize(780, 640)
        lay = QVBoxLayout(self)
        tb = QTextBrowser()
        html = ["<h3>Hóa trị thường gặp</h3><table cellpadding='5' border='0' width='100%'>"]
        for els, val, note in ds.VALENCE_TABLE:
            html.append(f"<tr><td><b>{els}</b></td><td align='center'>{val}</td><td>{note}</td></tr>")
        html.append("</table><h3>Quy tắc tính tan trong nước</h3><ul>")
        for a, b in ds.SOLUBILITY_RULES:
            html.append(f"<li><b>{a}</b>: {b}</li>")
        html.append(
            "</ul><h3>Dãy hoạt động hóa học của kim loại</h3>"
            "<p style='font-size:15px'><b>K, Na, Ba, Ca, Mg, Al, Zn, Fe, Ni, Sn, Pb, H, Cu, Hg, Ag, Pt, Au</b></p>"
            "<p>Kim loại đứng trước H đẩy được H₂ khỏi axit loãng; kim loại đứng trước đẩy kim loại đứng sau ra khỏi dung dịch muối "
            "(trừ K, Na, Ba, Ca tác dụng với nước trước).</p>"
            "<h3>Một số kết tủa và màu sắc đặc trưng</h3><ul>"
            "<li>AgCl trắng · AgBr vàng nhạt · AgI vàng đậm · Ag₃PO₄ vàng · Ag₂S, CuS, PbS, FeS đen</li>"
            "<li>BaSO₄, CaCO₃, BaCO₃ trắng · Cu(OH)₂ xanh lam · Fe(OH)₂ trắng xanh · Fe(OH)₃ nâu đỏ · Al(OH)₃ keo trắng · Mg(OH)₂ trắng</li>"
            "<li>Dung dịch: Cu²⁺ xanh lam · Fe³⁺ vàng nâu · Fe²⁺ lục nhạt · MnO₄⁻ tím · Cr₂O₇²⁻ da cam · CrO₄²⁻ vàng · [Fe(SCN)]²⁺ đỏ máu</li></ul>"
        )
        tb.setHtml("".join(html))
        lay.addWidget(tb)
        b = mk_btn("Đóng", primary=True)
        b.clicked.connect(self.accept)
        lay.addWidget(b)


# ==============================================================================
# 1. PHƯƠNG TRÌNH HÓA HỌC
# ==============================================================================
class ChemEquationPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.render)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.fill_lib)
        self.last_png = None
        self._icon_btns = []
        self._theme_dirty = False
        self._build()
        self.editor.setPlainText("2H2 + O2 ->[t^o] 2H2O")
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
        body = QWidget()
        root = QVBoxLayout(body)
        root.setSpacing(10)

        # --- hàng cân bằng & tính M
        c1 = mk_card(QVBoxLayout(), margins=(14, 10, 14, 10), spacing=8)
        r = QHBoxLayout()
        r.setSpacing(6)
        r.addWidget(mk_label("Cân bằng:", "h2"))
        self.in_bal = QLineEdit()
        self.in_bal.setClearButtonEnabled(True)
        self.in_bal.setPlaceholderText("VD: Fe + O2 -> Fe3O4   |   KMnO4 + HCl -> KCl + MnCl2 + Cl2 + H2O   |   Fe^{2+} + MnO4^- + H^+ -> Fe^{3+} + Mn^{2+} + H2O")
        self.in_bal.returnPressed.connect(self.do_balance)
        r.addWidget(self.in_bal, 1)
        b = mk_btn("Cân bằng", primary=True)
        b.clicked.connect(self.do_balance)
        r.addWidget(b)
        bo = self._ibtn("Quét ảnh", "camera", tip="Nhận diện phương trình hóa học từ ảnh (Gemini AI)")
        bo.clicked.connect(self.do_ocr)
        r.addWidget(bo)
        c1.layout().addLayout(r)
        self.lbl_bal = QLabel("")
        self.lbl_bal.setWordWrap(True)
        self.lbl_bal.setTextFormat(Qt.RichText)
        c1.layout().addWidget(self.lbl_bal)

        r2 = QHBoxLayout()
        r2.setSpacing(6)
        r2.addWidget(mk_label("Tính khối lượng mol M:", "h2"))
        self.in_m = QLineEdit()
        self.in_m.setClearButtonEnabled(True)
        self.in_m.setPlaceholderText("VD: CuSO4.5H2O, Ca(OH)2, Al2(SO4)3, KAl(SO4)2.12H2O")
        self.in_m.returnPressed.connect(self.do_mass)
        r2.addWidget(self.in_m, 1)
        b2 = mk_btn("Tính g/mol", primary=True)
        b2.clicked.connect(self.do_mass)
        r2.addWidget(b2)
        c1.layout().addLayout(r2)
        self.lbl_m = QLabel("")
        self.lbl_m.setTextFormat(Qt.RichText)
        self.lbl_m.setWordWrap(True)
        c1.layout().addWidget(self.lbl_m)
        root.addWidget(c1)

        # --- soạn thảo + xem trước
        c2 = mk_card(QVBoxLayout(), margins=(14, 10, 14, 10), spacing=8)
        tb = QHBoxLayout()
        tb.setSpacing(6)
        self.b_copy = self._ibtn("Sao chép ảnh", "copy", primary=True)
        self.b_copy.clicked.connect(self.copy_img)
        self.b_fav = self._ibtn("Yêu thích", "star")
        self.b_fav.clicked.connect(self.add_fav)
        b_val = mk_btn("Hóa trị · Tính tan", prop=("subtle", True))
        b_val.clicked.connect(self._open_valence)
        b_clear = self._ibtn("Xóa", "trash", prop=("danger", True))
        b_clear.clicked.connect(lambda: self.editor.clear())
        for w in (self.b_copy, self.b_fav, b_val):
            tb.addWidget(w)
        tb.addWidget(word_button(self.ctx, self, lambda: {"kind": "chem", "text": self.editor.toPlainText().strip()} if self.editor.toPlainText().strip() else None))
        tb.addWidget(b_clear)
        tb.addStretch()
        for txt, fn in (("LaTeX", self.copy_latex), ("mhchem", self.copy_mhchem)):
            bb = mk_btn(txt, prop=("subtle", True))
            bb.clicked.connect(fn)
            tb.addWidget(bb)
        for txt, fmt in (("SVG", "svg"), ("PNG", "png")):
            bb = self._ibtn(txt, "save")
            bb.clicked.connect(lambda _, f=fmt: self.save(f))
            tb.addWidget(bb)
        c2.layout().addLayout(tb)

        sp = QSplitter(Qt.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)
        ll.setSpacing(6)
        ll.addWidget(mk_label("MÃ HÓA HỌC (MHCHEM)", "caption"))
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Cascadia Code", 10.5))
        self.editor.setMinimumHeight(100)
        self.editor.textChanged.connect(lambda: self.timer.start(220))
        ll.addWidget(self.editor, 1)
        opt = QHBoxLayout()
        opt.setSpacing(6)
        opt.addWidget(mk_label("Cỡ:", "muted"))
        self.spin = no_wheel(QSpinBox())
        self.spin.setRange(12, 72)
        self.spin.setValue(28)
        self.spin.setSuffix(" pt")
        self.spin.valueChanged.connect(lambda: self.timer.start(140))
        opt.addWidget(self.spin)
        self.cmb_col = fix_combo(QComboBox(), 6, fixed_w=104)
        for n, v in COLOR_CHOICES:
            self.cmb_col.addItem(n, v)
        self.cmb_col.currentIndexChanged.connect(lambda: self.timer.start(80))
        opt.addWidget(self.cmb_col)
        self.cmb_bg = fix_combo(QComboBox(), 8, fixed_w=124)
        for n, v in BG_CHOICES:
            self.cmb_bg.addItem("Nền " + n, v)
        self.cmb_bg.currentIndexChanged.connect(lambda: self.timer.start(80))
        opt.addWidget(self.cmb_bg)
        b_bk = mk_btn("Cân bằng khung soạn", prop=("subtle", True))
        b_bk.clicked.connect(self.balance_editor)
        opt.addWidget(b_bk)
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
        self.lbl_err.setStyleSheet("color:#EF4444;")
        rl.addWidget(self.lbl_err)
        sp.addWidget(right)
        sp.setSizes([430, 620])
        c2.layout().addWidget(sp)
        root.addWidget(c2)

        # --- bảng ký hiệu
        c3 = mk_card(QVBoxLayout(), margins=(10, 6, 10, 6), spacing=4)
        self.pal_tabs = QTabWidget()
        self.pal_tabs.setFixedHeight(96)
        for name, items in ds.CHEM_PALETTES.items():
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(4, 4, 4, 2)
            h.setSpacing(5)
            for lab, ins in items:
                bt = mk_btn(lab, prop=("subtle", True))
                bt.setMinimumWidth(42)
                bt.clicked.connect(lambda _, t=ins: self.editor.insertPlainText(t))
                h.addWidget(bt)
            h.addStretch()
            sc_p = scroll_wrap(w)
            sc_p.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.pal_tabs.addTab(sc_p, esc(name))
        c3.layout().addWidget(self.pal_tabs)
        root.addWidget(c3)

        # --- thư viện phản ứng
        c4 = mk_card(QVBoxLayout(), margins=(14, 10, 14, 10), spacing=6)
        self.tabs_lib = QTabWidget()
        self.tabs_lib.setMinimumHeight(330)
        w1 = QWidget()
        v1 = QVBoxLayout(w1)
        v1.setContentsMargins(0, 6, 0, 0)
        fr = QHBoxLayout()
        fr.setSpacing(8)
        self.cmb_cat = fix_combo(QComboBox(), 10, fixed_w=192, searchable=True)
        self.cmb_cat.addItem("Tất cả phản ứng")
        self.cmb_cat.addItems(dc.REACTION_CATEGORIES)
        self.cmb_cat.currentIndexChanged.connect(self.fill_lib)
        fr.addWidget(self.cmb_cat)
        self.in_find = QLineEdit()
        self.in_find.setClearButtonEnabled(True)
        self.in_find.setPlaceholderText("Tìm phản ứng: tên, chất, công thức… (VD: aspirin, KMnO4, điện phân, xanh Phổ)")
        self.in_find.textChanged.connect(lambda: self.search_timer.start(100))
        fr.addWidget(self.in_find, 1)
        self.lbl_count = mk_label("", "badge")
        fr.addWidget(self.lbl_count)
        v1.addLayout(fr)
        self.lst = QListWidget()
        self.lst.setAlternatingRowColors(True)
        self.lst.itemClicked.connect(self.pick_item)
        v1.addWidget(self.lst, 1)
        self.tabs_lib.addTab(w1, esc(f"Phản ứng mẫu ({len(dc.REACTIONS)})"))
        self.lst_recent = QListWidget()
        self.lst_recent.itemClicked.connect(self.pick_item)
        self.tabs_lib.addTab(self.lst_recent, "Gần đây")
        self.lst_fav = QListWidget()
        self.lst_fav.itemClicked.connect(self.pick_item)
        self.tabs_lib.addTab(self.lst_fav, "Yêu thích")
        c4.layout().addWidget(self.tabs_lib)
        root.addWidget(c4)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.addWidget(scroll_wrap(body))
        self.fill_lib()
        self.fill_prefs()

    def fill_lib(self):
        cat = i18n.combo_key(self.cmb_cat)
        en = i18n.is_en()
        q = self.in_find.text().strip().lower()
        cat_ok = "Tất cả" if cat.startswith("Tất cả") else cat
        res = []
        for t, c, e in dc.REACTIONS:
            if cat_ok != "Tất cả" and c != cat_ok:
                continue
            t_en = i18n_data.reaction_title_en(t, e)
            c_en = i18n.tr(c)
            if not q or q in t.lower() or q in t_en.lower() or q in e.lower() or q in c.lower() or q in c_en.lower():
                res.append((t_en if en else t, c_en if en else c, e))
        self.lst.setUpdatesEnabled(False)
        self.lst.clear()
        for t, c, e in res[:700]:
            it = QListWidgetItem(f"{i18n.smart_title(t)}   [{i18n.smart_title(c)}]\n{e}")
            it.setData(Qt.UserRole, e)
            self.lst.addItem(it)
        self.lst.setUpdatesEnabled(True)
        self.lbl_count.setProperty("_i18n_skip", True)
        self.lbl_count.setText(f"{len(res)} reactions" if en else f"{len(res)} phản ứng")

    def fill_prefs(self):
        for lst, key in ((self.lst_recent, "chem_recents"), (self.lst_fav, "chem_favorites")):
            lst.clear()
            for e in self.ctx.prefs.get(key, []):
                it = QListWidgetItem(e)
                it.setData(Qt.UserRole, e)
                lst.addItem(it)

    def pick_item(self, it):
        e = it.data(Qt.UserRole)
        self.editor.setPlainText(e)
        self.in_bal.setText(re.sub(r"\[[^\]]*\]", "", e))
        self.push_recent(e)

    def push_recent(self, e):
        rec = [x for x in self.ctx.prefs.get("chem_recents", []) if x != e]
        rec.insert(0, e)
        self.ctx.prefs["chem_recents"] = rec[:40]
        self.ctx.save_prefs()
        self.fill_prefs()

    def add_fav(self):
        e = self.editor.toPlainText().strip()
        if e:
            fav = self.ctx.prefs.setdefault("chem_favorites", [])
            if e not in fav:
                fav.insert(0, e)
            self.ctx.save_prefs()
            self.fill_prefs()
            self.ctx.say("Đã thêm vào Yêu thích.")

    def _open_valence(self):
        d = ValenceDialog(self)
        if getattr(self.ctx, "qss", ""):
            d.setStyleSheet(self.ctx.qss)
        d.exec()

    def do_balance(self):
        t = self.in_bal.text().strip()
        try:
            res = fe.balance_chemical_equation(t)
            bal_lbl = "Balanced:" if i18n.is_en() else "Đã cân bằng:"
            self.lbl_bal.setText(f"<span style='color:#10B981; font-weight:600;'>{bal_lbl}</span> <b>{res}</b>" + (f"<br><span style='color:#D97706;'>{fe.LAST_NOTE}</span>" if fe.LAST_NOTE else ""))
            self.editor.setPlainText(res)
            self.push_recent(res)
        except Exception as exc:
            self.lbl_bal.setText(f"<span style='color:#EF4444;'>{exc}</span>")

    def balance_editor(self):
        self.in_bal.setText(self.editor.toPlainText().strip())
        self.do_balance()

    def do_mass(self):
        t = self.in_m.text().strip()
        try:
            m, rows = fe.calculate_molar_mass(t)
            tr = "".join(f"<tr><td><b>{el}</b></td><td align='right'>&nbsp;×{n}</td><td align='right'>&nbsp;{mass:.3f}</td><td align='right'>&nbsp;{pct:.2f}%</td></tr>" for el, n, mass, pct in rows)
            self.lbl_m.setText(f"M({t}) = <b style='font-size:15px'>{m:.3f} g/mol</b><table cellspacing='2'>{tr}</table>")
        except Exception as exc:
            self.lbl_m.setText(f"<span style='color:#EF4444;'>{exc}</span>")

    def do_ocr(self):
        t = ask_ocr(self, self.ctx, "chem")
        if t:
            self.in_bal.setText(t)
            self.editor.setPlainText(t)

    def render(self):
        t = self.editor.toPlainText().strip()
        if not t:
            self.view.set_text("Enter a chemical equation on the left…" if i18n.is_en() else "Nhập phương trình ở khung bên trái…")
            self.last_png = None
            self.lbl_err.setText("")
            return
        bg = self.cmb_bg.currentData()
        col = self.cmb_col.currentData()
        try:
            self.last_png = fe.render_chem_equation_bytes(t, self.spin.value(), col, bg, "png", 200)
            self.view.set_png(self.last_png, 2.0)
            self.view.set_bg({"transparent": ("#0B1120" if QColor(col).lightness() > 140 else "#FFFFFF"), "white": "#FFFFFF", "dark": "#0B1120"}[bg])
            self.lbl_err.setText("")
        except Exception as exc:
            self.lbl_err.setText(f"{'Unable to render' if i18n.is_en() else 'Không vẽ được'}: {exc}")

    def copy_img(self):
        if self.last_png:
            pm = QPixmap()
            pm.loadFromData(self.last_png)
            copy_image(pm)
            self.ctx.say("Đã sao chép ảnh phương trình vào clipboard.")

    def copy_latex(self):
        copy_text(fe.chem_to_latex(self.editor.toPlainText()))
        self.ctx.say("Đã sao chép mã LaTeX.")

    def copy_mhchem(self):
        copy_text(fe.chem_to_mhchem(self.editor.toPlainText()))
        self.ctx.say("Đã sao chép mã mhchem \\ce{...}.")

    def save(self, fmt):
        try:
            data = fe.render_chem_equation_bytes(self.editor.toPlainText().strip(), self.spin.value(), self.cmb_col.currentData(), self.cmb_bg.currentData(), fmt, 300)
            save_bytes_dialog(self, data, "Lưu", f"{fmt.upper()} (*.{fmt})", f"phuong_trinh.{fmt}")
        except Exception as exc:
            self.lbl_err.setText(str(exc))

    def refresh_theme(self):
        _sync_icon_btns(self._icon_btns, self.ctx.dark)
        if self.isVisible():
            self.render()
        else:
            self._theme_dirty = True


# ==============================================================================
# 2. CẤU TRÚC SMILES
# ==============================================================================
class SmilesPage(QWidget):
    open_sketcher = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.mol, self.last_png = None, None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.render)
        self._icon_btns = []
        self._theme_dirty = False
        self._build()
        self.edit.setPlainText("CH3COOH")

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
        root.setSpacing(8)
        root.setContentsMargins(0, 4, 0, 0)
        c = mk_card(QVBoxLayout(), margins=(14, 10, 14, 10), spacing=8)
        tb = QHBoxLayout()
        tb.setSpacing(5)
        b1 = self._ibtn("Sao chép", "copy", primary=True, tip="Sao chép ảnh cấu trúc 2D vào clipboard")
        b1.clicked.connect(self.copy_img)
        b_edit = mk_btn("Mở Trình vẽ", prop=("subtle", True), tip="Nạp phân tử này sang Trình vẽ cấu trúc để chỉnh sửa trực tiếp")
        b_edit.clicked.connect(lambda: self.mol and self.open_sketcher.emit(mo.to_smiles(self.mol)))
        b3 = self._ibtn("Quét ảnh", "camera", tip="Nhận diện công thức cấu trúc từ ảnh sang SMILES")
        b3.clicked.connect(self.do_ocr)
        b2 = self._ibtn("Xóa", "trash", prop=("danger", True))
        b2.clicked.connect(lambda: self.edit.clear())
        for w in (b1, b_edit, b3):
            tb.addWidget(w)
        tb.addWidget(word_button(self.ctx, self, self.word_item))
        tb.addWidget(b2)
        tb.addStretch()
        b_cs = mk_btn("SMILES", prop=("subtle", True), tip="Sao chép mã SMILES")
        b_cs.clicked.connect(self.copy_smiles)
        tb.addWidget(b_cs)
        for txt, fmt in (("SVG", "svg"), ("PNG", "png")):
            bb = self._ibtn(txt, "save")
            bb.clicked.connect(lambda _, f=fmt: self.save(f))
            tb.addWidget(bb)
        c.layout().addLayout(tb)

        r = QHBoxLayout()
        r.setSpacing(6)
        r.addWidget(mk_label(f"Mẫu ({len(dc.SMILES_PRESETS)}):", "muted"))
        self.cmb_grp = fix_combo(QComboBox(), 8, fixed_w=156, searchable=True)
        self.cmb_grp.addItem("Tất cả nhóm chất")
        self.cmb_grp.addItems(list(dc.SMILES_GROUPS))
        self.cmb_grp.currentIndexChanged.connect(self.fill_mol)
        r.addWidget(self.cmb_grp)
        self.cmb_mol = fix_combo(QComboBox(), 8, searchable=True)
        self.cmb_mol.setMinimumWidth(110)
        self.cmb_mol.activated.connect(self.pick_mol)
        r.addWidget(self.cmb_mol, 1)
        self.chk_ch3 = QCheckBox("CH₃")
        self.chk_ch3.setToolTip("Hiển thị nhóm đầu mạch CH₃")
        self.chk_ch3.setChecked(True)
        self.chk_ch3.stateChanged.connect(lambda: self.timer.start(50))
        r.addWidget(self.chk_ch3)
        self.cmb_col = fix_combo(QComboBox(), 6, fixed_w=112)
        self.cmb_col.addItems(["Màu nguyên tố", "Đơn sắc"])
        self.cmb_col.currentIndexChanged.connect(lambda: self.timer.start(50))
        r.addWidget(self.cmb_col)
        self.cmb_bg = fix_combo(QComboBox(), 6, fixed_w=112)
        for n, v in BG_CHOICES:
            self.cmb_bg.addItem("Nền " + n, v)
        self.cmb_bg.currentIndexChanged.connect(lambda: self.timer.start(50))
        r.addWidget(self.cmb_bg)
        self.chk_rd = QCheckBox("RDKit")
        self.chk_rd.setChecked(mo.HAS_RDKIT)
        self.chk_rd.setEnabled(mo.HAS_RDKIT)
        self.chk_rd.setToolTip("RDKit đã cài" if mo.HAS_RDKIT else "Chưa cài RDKit - dùng bộ dựng hình tích hợp")
        self.chk_rd.stateChanged.connect(lambda: self.timer.start(50))
        r.addWidget(self.chk_rd)
        c.layout().addLayout(r)
        root.addWidget(c)

        sp = QSplitter(Qt.Horizontal)
        left = mk_card(QVBoxLayout(), margins=(12, 10, 12, 10), spacing=6)
        left.setMinimumWidth(240)
        left.layout().addWidget(shrink_x(mk_label("TÊN CHẤT · CÔNG THỨC · SMILES", "caption")))
        self.edit = QPlainTextEdit()
        self.edit.setFont(QFont("Cascadia Code", 10.5))
        self.edit.setPlaceholderText("VD: CH3COOH · CH3CH(OH)CH3 · aspirin · paracetamol · vanilin · c1ccccc1")
        self.edit.setFixedHeight(92)
        self.edit.textChanged.connect(lambda: self.timer.start(260))
        left.layout().addWidget(self.edit)
        self.lbl_note = QLabel("")
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setTextFormat(Qt.RichText)
        left.layout().addWidget(self.lbl_note)
        self.info = QTextBrowser()
        self.info.setOpenLinks(False)
        left.layout().addWidget(self.info, 1)
        sp.addWidget(left)

        right = mk_card(QVBoxLayout(), margins=(12, 10, 12, 10), spacing=6)
        right.setMinimumWidth(240)
        right.layout().addWidget(shrink_x(mk_label("CẤU TRÚC 2D CHUẨN HÓA TRỊ", "caption")))
        self.view = ImageView(300)
        right.layout().addWidget(self.view, 1)
        sp.addWidget(right)
        sp.setSizes([390, 670])
        root.addWidget(sp, 1)

        chips = mk_card(QGridLayout(), margins=(10, 6, 10, 6), spacing=4)
        quick_mols = (
            ("Benzene", "c1ccccc1"), ("Toluene", "Cc1ccccc1"), ("Phenol", "Oc1ccccc1"), ("Aniline", "Nc1ccccc1"),
            ("Ethanol", "CCO"), ("Acetic acid", "CC(=O)O"), ("Glucose", "OCC(O)C(O)C(O)C(O)C=O"),
            ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O"), ("Paracetamol", "CC(=O)Nc1ccc(O)cc1"),
            ("Caffeine", "Cn1cnc2c1c(=O)n(C)c(=O)n2C"), ("Vitamin C", "OCC(O)C1OC(=O)C(O)=C1O"),
            ("Dopamine", "NCCc1ccc(O)c(O)c1"), ("Vanillin", "COc1cc(C=O)ccc1O"), ("Ibuprofen", "CC(C)Cc1ccc(C(C)C(=O)O)cc1"),
        )
        for idx, (lab, smi) in enumerate(quick_mols):
            b = mk_btn(lab, pill=True)
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, s=smi: self.edit.setPlainText(s))
            chips.layout().addWidget(b, idx // 7, idx % 7)
        root.addWidget(chips)
        self.fill_mol()

    def fill_mol(self):
        g = i18n.combo_key(self.cmb_grp)
        self.cmb_mol.blockSignals(True)
        self.cmb_mol.clear()
        i18n.reset_combo_vi_cache(self.cmb_mol)
        self.cmb_mol.addItem(i18n.smart_title(i18n.tr("— chọn chất —")), "")
        items = dc.SMILES_PRESETS if g == "Tất cả nhóm chất" else dc.SMILES_GROUPS.get(g, [])
        for lab, smi in items:
            self.cmb_mol.addItem(i18n.smart_title(lab), smi)
        self.cmb_mol.blockSignals(False)

    def pick_mol(self, idx):
        smi = self.cmb_mol.itemData(idx)
        if smi:
            self.edit.setPlainText(smi)

    def set_text(self, t):
        self.edit.setPlainText(t)

    def render(self):
        raw = self.edit.toPlainText().strip()
        if not raw:
            self.view.set_text("Enter a compound name, condensed formula, or SMILES…" if i18n.is_en() else "Nhập tên chất, công thức thu gọn hoặc SMILES…")
            self.info.clear()
            self.lbl_note.setText("")
            return
        try:
            mol, note, smi = mo.make_mol(raw.splitlines()[0] if "\n" in raw and not raw.count(".") else raw.replace("\n", ""), self.chk_rd.isChecked() and mo.HAS_RDKIT)
            self.mol = mol
            bg = self.cmb_bg.currentData()
            mono, ch3 = self.cmb_col.currentIndex() == 1, self.chk_ch3.isChecked()
            self.last_png = mo.render_mol_bytes(mol, "png", bg, mono, ch3, 66, 200)
            dark_prev = (bg == "dark") or (bg == "transparent" and self.ctx.dark)
            prev = self.last_png if dark_prev == (bg == "dark") else mo.render_mol_bytes(mol, "png", "dark", mono, ch3, 66, 200)
            self.view.set_png(prev, 2.0)
            self.view.set_bg("#0B1120" if dark_prev else "#FFFFFF")
            self.lbl_note.setProperty("_i18n_skip", True)
            if i18n.is_en():
                en_note = (
                    note.replace("Nhận diện công thức ", "Recognized formula ")
                        .replace("Nhận diện tên ", "Recognized name ")
                        .replace("Đã nhận diện ", "Recognized ")
                ) if note else "SMILES parsed successfully."
                self.lbl_note.setText(f"<span style='color:#10B981;'>{en_note}</span>")
            else:
                self.lbl_note.setText(f"<span style='color:#10B981;'>{note}</span>" if note else "<span style='color:#10B981;'>Đọc SMILES thành công.</span>")
            self.fill_info(mol, smi)
        except Exception as exc:
            self.mol = None
            self.last_png = None
            self.lbl_note.setText(f"<span style='color:#EF4444;'>{exc}</span>")
            self.view.set_text("Could not build 2D structure.\nCheck SMILES or condensed formula." if i18n.is_en() else "Không dựng được cấu trúc.\nKiểm tra lại mã SMILES / công thức.")
            self.info.clear()

    def fill_info(self, mol, smi):
        from sketcher_canvas import identify_formula
        names = identify_formula(mol.formula_counts())
        hs = mol.hcounts()
        rings = len(mo.find_rings(len(mol.atoms), mol.bonds))
        if i18n.is_en():
            html = (
                f"<div style='font-family:\"Segoe UI\",sans-serif; font-size:13.5px; line-height:1.6;'>"
                f"<p><b>Molecular formula:</b> {mol.formula(True)}<br><b>Molar mass:</b> {mol.mass():.3f} g/mol<br>"
                f"<b>Atoms:</b> {len(mol.atoms)} (+ {sum(hs)} H) · <b>Bonds:</b> {len(mol.bonds)} · <b>Rings:</b> {rings}</p>"
                f"<p><b>SMILES:</b><br><code>{smi}</code></p>"
            )
            if names:
                html += "<p><b>Possible matches:</b> " + ", ".join(dict.fromkeys(names[:8])) + "</p>"
            html += "</div>"
        else:
            html = (
                f"<div style='font-family:\"Segoe UI\",sans-serif; font-size:13.5px; line-height:1.6;'>"
                f"<p><b>Công thức phân tử:</b> {mol.formula(True)}<br><b>Khối lượng mol:</b> {mol.mass():.3f} g/mol<br>"
                f"<b>Số nguyên tử:</b> {len(mol.atoms)} (+ {sum(hs)} H) · <b>Liên kết:</b> {len(mol.bonds)} · <b>Số vòng:</b> {rings}</p>"
                f"<p><b>SMILES:</b><br><code>{smi}</code></p>"
            )
            if names:
                html += "<p><b>Có thể là:</b> " + ", ".join(dict.fromkeys(names[:8])) + "</p>"
            html += "</div>"
        self.info.setHtml(html)

    def copy_img(self):
        if self.last_png:
            pm = QPixmap()
            pm.loadFromData(self.last_png)
            copy_image(pm)
            self.ctx.say("Đã sao chép ảnh cấu trúc.")

    def word_item(self):
        if not self.mol:
            return None
        png = mo.render_mol_bytes(self.mol, "png", "white", self.cmb_col.currentIndex() == 1, self.chk_ch3.isChecked(), 66, 200)
        return {"kind": "image", "png": png, "dpi": 200, "title": self.mol.formula()}

    def copy_smiles(self):
        if self.mol:
            copy_text(mo.to_smiles(self.mol))
            self.ctx.say("Đã sao chép SMILES.")

    def save(self, fmt):
        if not self.mol:
            return
        data = mo.render_mol_bytes(self.mol, fmt, self.cmb_bg.currentData(), self.cmb_col.currentIndex() == 1, self.chk_ch3.isChecked(), 66, 300)
        save_bytes_dialog(self, data, "Lưu", f"{fmt.upper()} (*.{fmt})", f"cau_truc.{fmt}")

    def do_ocr(self):
        t = ask_ocr(self, self.ctx, "smiles")
        if t:
            self.edit.setPlainText(t)

    def refresh_theme(self):
        _sync_icon_btns(self._icon_btns, self.ctx.dark)
        if self.isVisible():
            self.render()
        else:
            self._theme_dirty = True


# ==============================================================================
# 3. TRÌNH VẼ PHÂN TỬ (Studio 3 cột kiểu ChemDraw)
# ==============================================================================
RING_SPECS = [
    ("Benzene", 6, True, "Benzene ring (6-membered aromatic)"),
    ("C₆ no", 6, False, "Cyclohexane (6-membered)"),
    ("C₅", 5, False, "Cyclopentane (5-membered)"),
    ("C₄", 4, False, "Cyclobutane (4-membered)"),
    ("C₃", 3, False, "Cyclopropane (3-membered)"),
    ("C₇", 7, False, "Cycloheptane (7-membered)"),
    ("C₈", 8, False, "Cyclooctane (8-membered)"),
    ("C₅ đôi", 5, True, "Cyclopentadiene (5-membered, 2 double bonds)"),
]


class SketcherPage(QWidget):
    open_smiles = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.tool_btns = {}
        self.elem_btns = {}
        self.ring_btns = []
        self._icon_btns = []
        self._dock_icon_btns = []
        self._build()

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

        # ---- 1. Thanh hành động gọn 1 dòng phía trên
        top = mk_card(QHBoxLayout(), margins=(8, 6, 8, 6), spacing=4)
        tl = top.layout()
        for txt, ic, fn, tip in (
            ("", "undo", lambda: self.sk.undo(), "Hoàn tác (Ctrl+Z)"),
            ("", "redo", lambda: self.sk.redo(), "Làm lại (Ctrl+Y)"),
            ("Chuẩn hóa", "sparkles", lambda: self.sk.clean(), "Tự động sắp xếp lại bố cục 2D đẹp chuẩn góc"),
            ("", "zoom_out", lambda: self.sk.zoom_by(1 / 1.15), "Thu nhỏ (-)"),
            ("", "zoom_in", lambda: self.sk.zoom_by(1.15), "Phóng to (+)"),
            ("", "fit", lambda: self.sk.center_view(), "Căn giữa & vừa khung (Space)"),
            ("", "rotate_l", lambda: self.sk.rotate_mol(15), "Xoay trái 15°"),
            ("", "rotate_r", lambda: self.sk.rotate_mol(-15), "Xoay phải 15°"),
            ("", "flip_h", lambda: self.sk.flip_mol(True), "Lật ngang"),
            ("", "flip_v", lambda: self.sk.flip_mol(False), "Lật dọc"),
        ):
            b = self._ibtn(txt, ic, tip=tip, prop=("subtle", True))
            if not txt:
                b.setFixedSize(28, 28)
            b.clicked.connect(fn)
            tl.addWidget(b)

        tl.addWidget(mk_sep(vertical=True))
        b_clr = self._ibtn("Xóa", "trash", tip="Xóa toàn bộ khung vẽ", prop=("danger", True))
        b_clr.clicked.connect(lambda: self.sk.clear_all())
        tl.addWidget(b_clr)
        tl.addStretch()

        b_cp = self._ibtn("Sao chép", "copy", primary=True, tip="Sao chép ảnh phân tử vào clipboard")
        b_cp.clicked.connect(self.copy_img)
        b_smi = mk_btn("SMILES", prop=("subtle", True), tip="Sao chép mã SMILES")
        b_smi.clicked.connect(self.copy_smiles)
        b_tab = mk_btn("Phân tích", prop=("subtle", True), tip="Mở cấu trúc này ở tab phân tích SMILES")
        b_tab.clicked.connect(self.to_smiles)
        b_png = self._ibtn("PNG", "save", tip="Xuất PNG nền trong suốt")
        b_png.clicked.connect(lambda: self.save("png"))
        b_svg = self._ibtn("SVG", "save", tip="Xuất vector SVG")
        b_svg.clicked.connect(lambda: self.save("svg"))
        for w in (b_cp,
                  word_button(self.ctx, self, lambda: {"kind": "image", "png": self.sk.export_bytes("png", "white"), "dpi": 200, "title": self.sk.mol.formula()} if self.sk.mol.atoms else None),
                  b_smi, b_tab, b_png, b_svg):
            tl.addWidget(w)
        root.addWidget(top)

        # ---- 2. Vùng làm việc 3 cột: Dock trái | Canvas giữa | Inspector phải
        main_row = QHBoxLayout()
        main_row.setSpacing(8)

        # --- Dock công cụ trái (chọn, liên kết, nguyên tố 1-click, vòng 1-click)
        dock_inner = QWidget()
        dl = QVBoxLayout(dock_inner)
        dl.setContentsMargins(6, 8, 10, 8)
        dl.setSpacing(8)

        def add_tool_btn(key, text, tip, icon_name=None):
            b = mk_btn(text, tip=tip, checkable=True, prop=("tool", True))
            b.setFixedHeight(30)
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            if icon_name:
                b.setProperty("_dock_ic", icon_name)
                b.setIconSize(QSize(14, 14))
                self._dock_icon_btns.append(b)
            b.clicked.connect(lambda _, k=key: self.pick_tool(k))
            self.tool_btns[key] = b
            return b

        dl.addWidget(mk_label("THAO TÁC", "caption"))
        g_act = QGridLayout()
        g_act.setSpacing(4)
        g_act.addWidget(add_tool_btn("select", "Chọn", "Chọn / kéo nguyên tử / khoanh vùng nhiều nguyên tử (V)", "cursor"), 0, 0)
        g_act.addWidget(add_tool_btn("pan", "Di chuyển", "Kéo chuột trái để di chuyển/trượt vùng vẽ tự do (H)", "move"), 0, 1)
        g_act.addWidget(add_tool_btn("erase", "Xóa", "Nhấp để xóa nguyên tử/liên kết hoặc kéo chọn vùng để xóa hàng loạt (E)", "trash"), 1, 0)
        g_act.addWidget(add_tool_btn("plus", "Tích +", "Tăng điện tích (+1)", "plus_circle"), 1, 1)
        g_act.addWidget(add_tool_btn("minus", "Tích −", "Giảm điện tích (−1)", "minus_circle"), 2, 0, 1, 2)
        dl.addLayout(g_act)

        dl.addWidget(mk_label("LIÊN KẾT", "caption"))
        g_bond = QGridLayout()
        g_bond.setSpacing(4)
        for idx, (k, lab, tip) in enumerate((
            ("bond1", "─ Đơn", "Liên kết đơn (phím 1)"),
            ("bond2", "═ Đôi", "Liên kết đôi (phím 2)"),
            ("bond3", "≡ Ba", "Liên kết ba (phím 3)"),
            ("wedge", "▸ Nêm", "Liên kết nêm đặc hướng ra (phím 4)"),
            ("dash", "┄ Đứt", "Liên kết nêm đứt hướng vào (phím 5)"),
        )):
            g_bond.addWidget(add_tool_btn(k, lab, tip), idx // 2, idx % 2)
        dl.addLayout(g_bond)

        dl.addWidget(mk_label("NGUYÊN TỐ", "caption"))
        g_el = QGridLayout()
        g_el.setSpacing(4)
        for idx, el in enumerate(QUICK_ELEMENTS):
            b = mk_btn(el, tip=f"Đặt / đổi nguyên tố {el} (rê chuột lên nguyên tử rồi bấm phím tắt)", checkable=True, prop=("elem", True))
            b.setFixedHeight(27)
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, e_=el: self._select_quick_el(e_))
            self.elem_btns[el] = b
            g_el.addWidget(b, idx // 3, idx % 3)
        b_other = mk_btn("+ Nguyên tố khác…", tip="Chọn nguyên tố bất kỳ trong bảng tuần hoàn", prop=("subtle", True))
        b_other.setFixedHeight(27)
        b_other.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        b_other.clicked.connect(self._pick_other_element)
        g_el.addWidget(b_other, 4, 0, 1, 3)
        dl.addLayout(g_el)

        dl.addWidget(mk_label("VÒNG NHANH", "caption"))
        g_ring = QGridLayout()
        g_ring.setSpacing(4)
        for idx, (lab, n, arom, tip) in enumerate(RING_SPECS):
            b = mk_btn(lab, tip=tip, checkable=True, prop=("tool", True))
            b.setFixedHeight(28)
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, i=idx: self._pick_ring_btn(i))
            self.ring_btns.append(b)
            g_ring.addWidget(b, idx // 2, idx % 2)
        dl.addLayout(g_ring)
        dl.addStretch()

        dock_card = mk_card(QVBoxLayout(), margins=(0, 0, 0, 0), spacing=0)
        dock_sc = scroll_wrap(dock_inner)
        dock_sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        dock_card.layout().addWidget(dock_sc)
        dock_card.setFixedWidth(202)
        main_row.addWidget(dock_card)

        # --- Canvas trung tâm
        self.sk = MoleculeSketcher()
        self.sk.changed.connect(self.update_info)
        self.sk.status.connect(self.ctx.say)
        self.sk.tool_changed.connect(self._sync_tool_ui)
        fr = mk_card(QVBoxLayout(), margins=(4, 4, 4, 4), spacing=0)
        fr.layout().addWidget(self.sk)
        main_row.addWidget(fr, 1)

        # --- Inspector bên phải
        side = QWidget()
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 10, 0)
        sv.setSpacing(8)

        # Nạp nhanh theo tên / công thức / SMILES
        g_load = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=6)
        g_load.layout().addWidget(shrink_x(mk_label("NẠP TỪ TÊN / SMILES", "caption")))
        lrow = QHBoxLayout()
        lrow.setSpacing(5)
        self.in_name = shrink_x(QLineEdit())
        self.in_name.setClearButtonEnabled(True)
        self.in_name.setPlaceholderText("VD: aspirin, CH3COOH…")
        self.in_name.returnPressed.connect(self.load_name)
        lrow.addWidget(self.in_name, 1)
        b_go = mk_btn("Nạp", primary=True)
        b_go.clicked.connect(self.load_name)
        lrow.addWidget(b_go)
        g_load.layout().addLayout(lrow)
        self.cmb_tpl = fix_combo(QComboBox(), 6, searchable=True)
        self.cmb_tpl.setMaxVisibleItems(22)
        self.cmb_tpl.addItem("— chọn từ kho chất mẫu —", "")
        for lab, smi in dc.SMILES_PRESETS:
            self.cmb_tpl.addItem(lab, smi)
        self.cmb_tpl.activated.connect(self.load_tpl)
        g_load.layout().addWidget(self.cmb_tpl)
        sv.addWidget(g_load)

        # Nhóm chức nhanh 1-click + đầy đủ
        g_grp = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=6)
        g_grp.layout().addWidget(shrink_x(mk_label("NHÓM CHỨC & GỐC THẾ", "caption")))
        qgg = QGridLayout()
        qgg.setSpacing(4)
        for idx, (lab, key) in enumerate(QUICK_GROUPS):
            b = mk_btn(lab, pill=True, tip=f"Gắn nhóm {key}")
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, k=key: self._select_group(k))
            qgg.addWidget(b, idx // 3, idx % 3)
        g_grp.layout().addLayout(qgg)
        self.cmb_grp = fix_combo(QComboBox(), 6, searchable=True)
        self.cmb_grp.setMaxVisibleItems(24)
        self.cmb_grp.addItems(list(GROUPS))
        self.cmb_grp.setCurrentText("OH (Hydroxyl)")
        self.cmb_grp.activated.connect(lambda _: self._select_group(i18n.combo_key(self.cmb_grp)))
        g_grp.layout().addWidget(self.cmb_grp)
        sv.addWidget(g_grp)

        # Khung mẫu dựng sẵn
        g_tpl = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=6)
        g_tpl.layout().addWidget(shrink_x(mk_label("KHUNG MẪU DỰNG SẴN", "caption")))
        self.cmb_tcat = fix_combo(QComboBox(), 6, searchable=True)
        self.cmb_tcat.addItem("Tất cả khung mẫu")
        self.cmb_tcat.addItems(list(TEMPLATES))
        self.cmb_tcat.currentIndexChanged.connect(lambda _: self._fill_tpl_items())
        g_tpl.layout().addWidget(self.cmb_tcat)
        self.cmb_titem = fix_combo(QComboBox(), 6, searchable=True)
        self.cmb_titem.activated.connect(lambda _: self._pick_template(activate=True))
        g_tpl.layout().addWidget(self.cmb_titem)
        sv.addWidget(g_tpl)

        # Hiển thị
        g_disp = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=5)
        g_disp.layout().addWidget(shrink_x(mk_label("HIỂN THỊ PHÂN TỬ", "caption")))
        self.cmb_cmode = fix_combo(QComboBox(), 6)
        self.cmb_cmode.addItem("Thu gọn (CH₃, CH₂, CH, C)", "inline")
        self.cmb_cmode.addItem("Tách H trên/dưới C", "stacked")
        self.cmb_cmode.addItem("Khung xương (ẩn C)", "skeleton")
        self.cmb_cmode.currentIndexChanged.connect(lambda _: (setattr(self.sk, "cmode", self.cmb_cmode.currentData()), self.sk.update()))
        g_disp.layout().addWidget(self.cmb_cmode)
        for text, attr, init in (
            ("Hiện C trong vòng", "ring_c", False),
            ("Đơn sắc (đen trắng)", "mono", False),
            ("Lưới chấm gợi ý", "show_grid", True),
            ("Cảnh báo hóa trị", "check_valence", True),
        ):
            ck = shrink_x(QCheckBox(text))
            ck.setChecked(init)
            ck.stateChanged.connect(lambda s, a=attr: (setattr(self.sk, a, bool(s)), self.sk.update()))
            g_disp.layout().addWidget(ck)
        sv.addWidget(g_disp)

        # Thông tin phân tử trực tiếp
        g_info = mk_card(QVBoxLayout(), margins=(10, 9, 10, 9), spacing=4)
        g_info.layout().addWidget(shrink_x(mk_label("THÔNG TIN PHÂN TỬ", "caption")))
        self.lbl_info = shrink_x(QTextBrowser())
        self.lbl_info.setMaximumHeight(165)
        self.lbl_info.setMinimumHeight(115)
        g_info.layout().addWidget(self.lbl_info)
        sv.addWidget(g_info)
        sv.addStretch()

        sc = scroll_wrap(side)
        sc.setFixedWidth(288)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_row.addWidget(sc)
        root.addLayout(main_row, 1)

        self._fill_tpl_items()
        self.pick_tool("bond1")
        self.update_info()

    def _sync_dock_icons(self):
        c = self.ctx.palette
        for b in self._dock_icon_btns:
            ic = b.property("_dock_ic")
            col = "#FFFFFF" if b.isChecked() else (c["danger"] if ic == "trash" else c["text"])
            b.setIcon(icons.make_icon(ic, col, col, size=14))

    def _clear_dock_checks(self):
        for b in self.tool_btns.values():
            b.setChecked(False)
        for b in self.elem_btns.values():
            b.setChecked(False)
        for b in self.ring_btns:
            b.setChecked(False)
        self._sync_dock_icons()

    def _sync_tool_ui(self, key):
        self._clear_dock_checks()
        if key in self.tool_btns:
            self.tool_btns[key].setChecked(True)
        elif key == "atom" and self.sk.element in self.elem_btns:
            self.elem_btns[self.sk.element].setChecked(True)
        self._sync_dock_icons()

    def _select_quick_el(self, el):
        self.sk.set_tool("atom", element=el)
        self._clear_dock_checks()
        if el in self.elem_btns:
            self.elem_btns[el].setChecked(True)

    def _pick_other_element(self):
        sym, ok = QInputDialog.getText(self, "Nguyên tố bất kỳ", "Nhập kí hiệu nguyên tố (VD: Fe, Cu, Ti, Ge, Pt):")
        sym = sym.strip().capitalize()
        if ok and sym in ds.ATOMIC_MASSES:
            self.sk.set_tool("atom", element=sym)
            self._clear_dock_checks()
            self.ctx.say(f"Đã chọn nguyên tố {sym}")

    def _pick_ring_btn(self, idx):
        _, n, arom, _ = RING_SPECS[idx]
        self.sk.set_tool("ring", ring_n=n, ring_arom=arom)
        self._clear_dock_checks()
        self.ring_btns[idx].setChecked(True)

    def _select_group(self, key):
        self.cmb_grp.blockSignals(True)
        if self.cmb_grp.findText(key) >= 0:
            self.cmb_grp.setCurrentText(key)
        self.cmb_grp.blockSignals(False)
        self.sk.set_tool("group", group=key)
        self._clear_dock_checks()

    def _fill_tpl_items(self, cat=None):
        cat = cat or i18n.combo_key(self.cmb_tcat)
        self.cmb_titem.blockSignals(True)
        self.cmb_titem.clear()
        i18n.reset_combo_vi_cache(self.cmb_titem)
        if cat == "Tất cả khung mẫu":
            for grp_dict in TEMPLATES.values():
                for name, smi in grp_dict.items():
                    self.cmb_titem.addItem(i18n.smart_title(name), smi)
        else:
            for name, smi in TEMPLATES.get(cat, {}).items():
                self.cmb_titem.addItem(i18n.smart_title(name), smi)
        self.cmb_titem.blockSignals(False)
        self.sk.template = self.cmb_titem.currentData()

    def _pick_template(self, activate=False):
        self.sk.template = self.cmb_titem.currentData()
        if activate:
            self.sk.set_tool("template")
            self._clear_dock_checks()

    def pick_tool(self, key):
        self.sk.set_tool(key)
        self._sync_tool_ui(key)

    def update_info(self):
        f, m, names = self.sk.info()
        en = i18n.is_en()
        if not f:
            msg = "No molecule yet. Draw on canvas or choose a preset on the right." if en else "Chưa có phân tử. Vẽ hoặc chọn chất mẫu ở bên phải."
            self.lbl_info.setHtml(f"<span style='color:#94A3B8;'>{msg}</span>")
            return
        smi = self.sk.smiles()
        comp = " · ".join(f"{el}: {pct:.1f}%" for el, _, pct in self.sk.composition())
        rings = len(mo.find_rings(len(self.sk.mol.atoms), self.sk.mol.bonds))
        r_lbl = "Rings:" if en else "Vòng:"
        s_lbl = "Matches:" if en else "Gợi ý:"
        html = (
            f"<div style='font-size:15px; font-weight:700;'>{f}</div>"
            f"<div><b>M =</b> {m:.3f} g/mol · <b>{r_lbl}</b> {rings}</div>"
            f"<div style='color:#94A3B8; font-size:12px; margin-top:2px;'>{comp}</div>"
            f"<div style='margin-top:4px;'><b>SMILES:</b> <code>{smi}</code></div>"
        )
        if names:
            html += f"<div style='margin-top:3px;'><b>{s_lbl}</b> " + ", ".join(dict.fromkeys(names[:5])) + "</div>"
        self.lbl_info.setHtml(html)

    def load_tpl(self, idx):
        smi = self.cmb_tpl.itemData(idx)
        if smi:
            self._load_smiles(smi)
            self.cmb_tpl.setCurrentIndex(0)

    def load_name(self):
        txt = self.in_name.text().strip()
        if not txt:
            return
        try:
            mol, note, _ = mo.make_mol(txt, True)
            self.sk.load_mol(mol)
            self.ctx.say(note or "Đã nạp cấu trúc.")
        except Exception as exc:
            self.ctx.say(f"Không nạp được: {exc}")

    def _load_smiles(self, smi):
        mol = mo.parse_smiles(smi)
        mo.layout(mol, True)
        self.sk.load_mol(mol)

    def copy_img(self):
        if self.sk.mol.atoms:
            pm = QPixmap()
            pm.loadFromData(self.sk.export_bytes("png", "transparent" if not self.ctx.dark else "dark"))
            copy_image(pm)
            self.ctx.say("Đã sao chép ảnh cấu trúc.")

    def copy_smiles(self):
        if self.sk.mol.atoms:
            copy_text(self.sk.smiles())
            self.ctx.say("Đã sao chép SMILES.")

    def to_smiles(self):
        if self.sk.mol.atoms:
            self.open_smiles.emit(self.sk.smiles())

    def save(self, fmt):
        if self.sk.mol.atoms:
            save_bytes_dialog(self, self.sk.export_bytes(fmt, "transparent"), "Lưu", f"{fmt.upper()} (*.{fmt})", f"phan_tu.{fmt}")

    def refresh_theme(self):
        c = self.ctx.palette
        self.sk.set_dark(self.ctx.dark, c["canvas"], c["grid"])
        _sync_icon_btns(self._icon_btns, self.ctx.dark)
        self._sync_dock_icons()


# ==============================================================================
# 4. BẢNG TUẦN HOÀN (vẽ bằng QPainter — 0 lag khi đổi theme, chuẩn danh pháp IUPAC)
# ==============================================================================
class PeriodicPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.active_cat, self.sel = None, 26
        self._build()
        self.select(26)

    def _build(self):
        body = QWidget()
        root = QVBoxLayout(body)
        root.setSpacing(10)
        top = mk_card(QHBoxLayout(), margins=(14, 10, 14, 10), spacing=12)
        sv = QVBoxLayout()
        self.txt = QLineEdit()
        self.txt.setClearButtonEnabled(True)
        self.txt.setPlaceholderText("Tìm Z, ký hiệu, tên IUPAC…")
        self.txt.setFixedWidth(210)
        self.txt.textChanged.connect(self.refilter)
        sv.addWidget(self.txt)
        rr = QHBoxLayout()
        rr.setSpacing(6)
        self.chk_auto = QCheckBox("Tự đọc")
        self.cmb_rate = fix_combo(QComboBox(), 5, fixed_w=92)
        self.cmb_rate.addItems(["0.75×", "1.0×", "1.25×"])
        self.cmb_rate.setCurrentIndex(1)
        rr.addWidget(self.chk_auto)
        rr.addWidget(self.cmb_rate)
        rr.addStretch()
        sv.addLayout(rr)
        top.layout().addLayout(sv)
        self.badge = QLabel()
        self.badge.setFixedSize(84, 84)
        self.badge.setAlignment(Qt.AlignCenter)
        top.layout().addWidget(self.badge)
        iv = QVBoxLayout()
        self.l1, self.l2, self.l3 = mk_label("", "h2", True), mk_label("", None, True), mk_label("", "muted", True)
        for w in (self.l1, self.l2, self.l3):
            iv.addWidget(w)
        top.layout().addLayout(iv, 1)
        bv = QVBoxLayout()
        b_sp = mk_btn("Nghe phát âm IUPAC", primary=True)
        b_sp.clicked.connect(lambda: self.ctx.speak(ds.ELEMENTS_BY_Z[self.sel][2], [0.75, 1.0, 1.25][self.cmb_rate.currentIndex()]))
        b_ex = mk_btn("Xuất ảnh bảng", prop=("subtle", True))
        b_ex.clicked.connect(self.export_table)
        bv.addWidget(b_sp)
        bv.addWidget(b_ex)
        top.layout().addLayout(bv)
        root.addWidget(top)

        self.card = mk_card(QVBoxLayout(), margins=(8, 8, 8, 8), spacing=8)
        self.ptable = cw.PeriodicTableWidget()
        self.ptable.on_select = lambda zz: self.select(zz, self.chk_auto.isChecked())
        self.card.layout().addWidget(self.ptable)

        legv = QVBoxLayout()
        legv.setSpacing(4)
        leg = QHBoxLayout()
        leg2 = QHBoxLayout()
        b_all = mk_btn("Tất cả", pill=True)
        b_all.clicked.connect(lambda: (setattr(self, "active_cat", None), self.refilter()))
        leg.addWidget(b_all)
        for i, (ck, (lbl, hc)) in enumerate(ds.CATEGORY_LABELS.items()):
            b = mk_btn("● " + lbl, pill=True)
            b.setStyleSheet(f"color:{hc}; font-weight:600;")
            b.clicked.connect(lambda _, k=ck: (setattr(self, "active_cat", k), self.refilter()))
            (leg if i < 4 else leg2).addWidget(b)
        leg.addStretch()
        leg2.addStretch()
        legv.addLayout(leg)
        legv.addLayout(leg2)
        self.card.layout().addLayout(legv)
        root.addWidget(self.card)

        vr = QHBoxLayout()
        bc = mk_card(QVBoxLayout())
        bc.layout().addWidget(mk_label("Mô hình Bohr", "h2"))
        self.bohr = cw.BohrWidget()
        self.bohr.setMinimumHeight(320)
        bc.layout().addWidget(self.bohr, 1)
        bh = QHBoxLayout()
        b1 = mk_btn("Sao chép Bohr", primary=True)
        b1.clicked.connect(lambda: (copy_image(self.bohr.render_to_pixmap()), self.ctx.say("Đã sao chép hình Bohr.")))
        b2 = mk_btn("Tải SVG")
        b2.clicked.connect(lambda: save_bytes_dialog(self, self.bohr.to_svg_bytes(), "SVG", "SVG (*.svg)", f"bohr_Z{self.sel}.svg"))
        bh.addWidget(b1)
        bh.addWidget(b2)
        bh.addStretch()
        bc.layout().addLayout(bh)

        oc = mk_card(QVBoxLayout())
        oc.layout().addWidget(mk_label("Sơ đồ ô orbital ↑↓", "h2"))
        self.orb = cw.OrbitalWidget()
        self.orb.setMinimumHeight(320)
        oc.layout().addWidget(self.orb, 1)
        oh = QHBoxLayout()
        o1 = mk_btn("Sao chép orbital", primary=True)
        o1.clicked.connect(lambda: (copy_image(self.orb.render_to_pixmap()), self.ctx.say("Đã sao chép sơ đồ orbital.")))
        o2 = mk_btn("Tải SVG")
        o2.clicked.connect(lambda: save_bytes_dialog(self, self.orb.to_svg_bytes(), "SVG", "SVG (*.svg)", f"orbital_Z{self.sel}.svg"))
        oh.addWidget(o1)
        oh.addWidget(o2)
        oh.addStretch()
        oc.layout().addLayout(oh)
        vr.addWidget(bc, 1)
        vr.addWidget(oc, 1)
        root.addLayout(vr)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.addWidget(scroll_wrap(body))

    def select(self, z, speak=False):
        self.sel = z
        el = ds.ELEMENTS_BY_Z[z]
        _, sym, en, vi, lat, ipa, mass, cat, _, _, per, grp = el
        lbl, hc = ds.CATEGORY_LABELS[cat]
        st = fe.compute_electron_structure(z)
        self.badge.setProperty("_i18n_skip", True)
        self.l1.setProperty("_i18n_skip", True)
        self.l2.setProperty("_i18n_skip", True)
        self.l3.setProperty("_i18n_skip", True)
        self.badge.setText(f"{z}\n{sym}\n{mass}")
        self.badge.setStyleSheet(f"background:{hc}30; border:2px solid {hc}; border-radius:12px; font-weight:800; font-size:14px;")
        lbl_disp = i18n.VI_TO_EN.get("● " + lbl, lbl).replace("● ", "") if i18n.is_en() else lbl
        self.l1.setText(f"{en}   {ipa}   •   {lbl_disp}")
        if i18n.is_en():
            self.l2.setText(f"Aᵣ: {mass}  |  Config: {st['condensed_config']}  |  Period {per} · Group {grp} ({st['block']}-block)  |  Unpaired e⁻: {st['unpaired']}")
            self.l3.setText(f"Latin root: {lat}  •  Full configuration: {st['full_config']}")
        else:
            self.l2.setText(f"Aᵣ: {mass}  |  Cấu hình: {st['condensed_config']}  |  Chu kì {per} · Nhóm {grp} (khối {st['block']})  |  e độc thân: {st['unpaired']}")
            self.l3.setText(f"Tên gốc Latin: {lat}  •  Cấu hình đầy đủ: {st['full_config']}")
        self.ptable.set_selected(z)
        self.bohr.set_element(z)
        self.orb.set_element(z)
        if speak:
            self.ctx.speak(en, [0.75, 1.0, 1.25][self.cmb_rate.currentIndex()])

    def refilter(self):
        self.ptable.set_filter(self.txt.text(), self.active_cat)

    def export_table(self):
        pm = self.ptable.render_to_pixmap()
        path, _ = QFileDialog.getSaveFileName(self, "Lưu ảnh bảng tuần hoàn", "periodic_table.png", "PNG (*.png)")
        if path:
            pm.save(path, "PNG")

    def refresh_theme(self):
        self.ptable.set_dark(self.ctx.dark)
        self.bohr.set_dark(self.ctx.dark)
        self.orb.set_dark(self.ctx.dark)


# ==============================================================================
# 5. TRA CỨU CHẤT · BÁCH KHOA HÓA HỌC (CHUẨN IUPAC + ĐÁNH DẤU SAO TỰ HỌC)
# ==============================================================================
class CompoundPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.rows = []
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.fill)
        self.open_smiles = None
        self.open_sketcher = None
        self.open_equation = None
        self._theme_dirty = False
        self._build()
        self.fill()

    def showEvent(self, e):
        super().showEvent(e)
        if self._theme_dirty:
            self._theme_dirty = False
            self.show_detail()

    @staticmethod
    def _star_key(c) -> str:
        return f"{c[0]}||{c[1]}"

    def _starred_set(self) -> set:
        return set(self.ctx.prefs.get("starred_compounds", []))

    def _update_star_filter_btn(self):
        n = len(self._starred_set())
        self.b_star_filter.setProperty("_i18n_skip", True)
        self.b_star_filter.setText(esc(f"★ Bookmarked ({n})" if i18n.is_en() else f"★ Đã Lưu ({n})"))

    def _sync_star_btn(self, c):
        starred = bool(c and self._star_key(c) in self._starred_set())
        self.b_star.setProperty("_i18n_skip", True)
        self.b_star.blockSignals(True)
        self.b_star.setChecked(starred)
        self.b_star.blockSignals(False)
        self.b_star.setText(("Bookmarked" if starred else "Bookmark") if i18n.is_en() else ("Đã đánh dấu" if starred else "Đánh dấu sao"))
        col = "#F59E0B" if starred else self.ctx.palette["muted"]
        self.b_star.setIcon(icons.make_icon("star_filled" if starred else "star", col, col, size=15))

    def _toggle_star(self):
        c = self.cur()
        if not c:
            return
        key = self._star_key(c)
        lst = list(self.ctx.prefs.get("starred_compounds", []))
        if key in lst:
            lst.remove(key)
            self.ctx.say(f"Removed bookmark: {c[1]}" if i18n.is_en() else f"Đã bỏ đánh dấu sao: {c[1]}")
        else:
            lst.insert(0, key)
            self.ctx.say(f"Bookmarked: {c[1]}" if i18n.is_en() else f"Đã đánh dấu sao: {c[1]}")
        self.ctx.prefs["starred_compounds"] = lst
        self.ctx.save_prefs()
        self._update_star_filter_btn()
        self._sync_star_btn(c)
        # Cập nhật dấu ★ ngay trong danh sách (hoặc lọc lại nếu đang ở chế độ chỉ xem chất đánh dấu)
        if self.b_star_filter.isChecked():
            self.fill()
        else:
            r = self.lst.currentRow()
            if 0 <= r < self.lst.count():
                self._style_list_item(self.lst.item(r), c, key in lst)

    def _style_list_item(self, it: QListWidgetItem, c, is_starred: bool):
        f, en, vi, cat, desc, smi = c
        disp = i18n.smart_title(en if i18n.is_en() else dc.compound_display_name(en, vi))
        f_uni = fe.species_to_unicode(f) if "n" not in f.replace("Na", "").replace("Mn", "").replace("Sn", "").replace("Zn", "").replace("Ni", "").replace("In", "") else f
        prefix = "★  " if is_starred else ""
        it.setText(f"{prefix}{disp}   —   {f_uni}")
        if is_starred:
            it.setForeground(QColor("#FBBF24" if self.ctx.dark else "#B45309"))
        else:
            it.setData(Qt.ForegroundRole, None)

    def _on_wiki_link(self, url):
        s = url.toString()
        if s.startswith("rxn:") and self.open_equation:
            eq = unquote(s[4:])
            self.open_equation(eq)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(8)
        c = mk_card(QHBoxLayout(), margins=(12, 9, 12, 9), spacing=8)
        self.q = QLineEdit()
        self.q.setClearButtonEnabled(True)
        self.q.setPlaceholderText(f"Tìm trong {len(dc.COMPOUNDS)} chất chuẩn IUPAC: tên quốc tế, công thức, ứng dụng… (VD: Nitrogen dioxide, Aspirin, H2SO4)")
        self.q.textChanged.connect(lambda: self.search_timer.start(100))
        c.layout().addWidget(self.q, 1)
        self.cat = fix_combo(QComboBox(), 10, fixed_w=192, searchable=True)
        self.cat.addItems(dc.COMPOUND_CATEGORIES)
        self.cat.currentIndexChanged.connect(self.fill)
        c.layout().addWidget(self.cat)
        self.b_star_filter = mk_btn("★ Đã Lưu (0)", checkable=True, prop=("star", True), tip="Lọc các chất đã đánh dấu sao")
        self.b_star_filter.toggled.connect(lambda _: self.fill())
        c.layout().addWidget(self.b_star_filter)
        self.lbl_n = mk_label("", "badge")
        c.layout().addWidget(self.lbl_n)
        root.addWidget(c)

        sp = QSplitter(Qt.Horizontal)
        self.lst = QListWidget()
        self.lst.setMinimumWidth(205)
        self.lst.setAlternatingRowColors(True)
        self.lst.currentRowChanged.connect(self.show_detail)
        sp.addWidget(self.lst)

        right = mk_card(QVBoxLayout(), margins=(12, 10, 12, 10), spacing=8)
        right.setMinimumWidth(300)

        # Đầu bài Wiki: Tên chất + nút ★ Đánh dấu sao tự học
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        tv = QVBoxLayout()
        tv.setSpacing(2)
        self.title = shrink_x(mk_label("", "h1", True))
        self.sub = shrink_x(mk_label("", "muted", True))
        tv.addWidget(self.title)
        tv.addWidget(self.sub)
        hdr.addLayout(tv, 1)
        self.b_star = mk_btn("Đánh dấu sao", checkable=True, prop=("star", True), tip="Đánh dấu sao để lưu chất này vào danh sách đã lưu")
        self.b_star.setIconSize(QSize(15, 15))
        self.b_star.clicked.connect(self._toggle_star)
        hdr.addWidget(self.b_star, 0, Qt.AlignTop)
        right.layout().addLayout(hdr)

        # Thanh nút thao tác nhanh
        rb = QHBoxLayout()
        rb.setSpacing(5)
        b1 = shrink_x(mk_btn("Phát âm IUPAC", primary=True, tip="Nghe phát âm chuẩn quốc tế IUPAC"))
        b1.clicked.connect(self.say)
        b2 = shrink_x(mk_btn("Copy CT", prop=("subtle", True), tip="Sao chép công thức hóa học"))
        b2.clicked.connect(lambda: self.cur() and (copy_text(self.cur()[0]), self.ctx.say("Đã sao chép công thức.")))
        b3 = shrink_x(mk_btn("Mở SMILES", prop=("subtle", True), tip="Mở cấu trúc ở tab SMILES"))
        b3.clicked.connect(self.to_smiles)
        b4 = shrink_x(mk_btn("Mở Trình vẽ", prop=("subtle", True), tip="Chỉnh sửa trực tiếp ở Trình vẽ phân tử"))
        b4.clicked.connect(self.to_sketcher)
        for b in (b1, b2, b3, b4):
            rb.addWidget(b, 1)
        right.layout().addLayout(rb)

        # Vùng nội dung Wiki: mô hình 2D gọn phía trên + bài Bách khoa chi tiết có thể kéo giãn phía dưới
        vsp = QSplitter(Qt.Vertical)
        self.view = ImageView(128)
        self.view.setMaximumHeight(230)
        vsp.addWidget(self.view)
        self.det = QTextBrowser()
        self.det.setOpenLinks(False)
        self.det.anchorClicked.connect(self._on_wiki_link)
        vsp.addWidget(self.det)
        vsp.setSizes([155, 420])
        right.layout().addWidget(vsp, 1)

        sp.addWidget(right)
        sp.setSizes([380, 700])
        root.addWidget(sp, 1)
        self._update_star_filter_btn()

    def cur(self):
        r = self.lst.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def fill(self):
        starred = self._starred_set()
        rows = dc.search_compounds(self.q.text(), i18n.combo_key(self.cat))
        if self.b_star_filter.isChecked():
            rows = [c for c in rows if self._star_key(c) in starred]
        self.rows = rows
        self.lst.setUpdatesEnabled(False)
        self.lst.clear()
        for c in self.rows:
            it = QListWidgetItem()
            self._style_list_item(it, c, self._star_key(c) in starred)
            self.lst.addItem(it)
        self.lst.setUpdatesEnabled(True)
        self.lbl_n.setProperty("_i18n_skip", True)
        self.lbl_n.setText(f"{len(self.rows)} compounds" if i18n.is_en() else f"{len(self.rows)} chất")
        self._update_star_filter_btn()
        if self.rows:
            self.lst.setCurrentRow(0)
        else:
            if i18n.is_en():
                self.title.setText("No matching compounds" if not self.b_star_filter.isChecked() else "No bookmarked compounds yet")
                self.sub.setText("Click 'Bookmark' on any compound to save it to your ★ Bookmarked list." if self.b_star_filter.isChecked() else "")
            else:
                self.title.setText("Chưa có chất nào phù hợp" if not self.b_star_filter.isChecked() else "Chưa đánh dấu sao chất nào")
                self.sub.setText("Nhấn nút 'Đánh dấu sao' ở góc phải mỗi chất để lưu vào danh sách ★ Đã Lưu." if self.b_star_filter.isChecked() else "")
            self.view.set_bg(None)
            self.view.set_text("")
            self.det.setHtml("")
            self._sync_star_btn(None)

    def show_detail(self, r=0):
        c = self.cur()
        if not c:
            return
        f, en, vi, cat, desc, smi = c
        alias = dc.extract_common_vn(vi)
        self.title.setProperty("_i18n_skip", True)
        self.sub.setProperty("_i18n_skip", True)
        self.title.setText(i18n.smart_title(en))
        cat_disp = i18n.smart_title(i18n.tr(cat))
        self.sub.setText(f"{cat_disp}" + (f"   •   Tên Thường Gọi: {i18n.smart_title(alias)}" if (alias and not i18n.is_en()) else ""))
        self._sync_star_btn(c)
        try:
            m, rows = fe.calculate_molar_mass(re.sub(r"[()]?n$", "", f) if "n" in f and f.endswith("n") else f)
            mass = f"{m:.3f} g/mol"
        except Exception:
            mass, rows = "—", []
        smiles_stats = None
        if smi and ("." not in smi or "[" in smi):
            try:
                mol = mo.parse_smiles(smi)
                mo.layout(mol, True)
                png = mo.render_mol_bytes(mol, "png", "dark" if self.ctx.dark else "white", False, True, 60, 160)
                self.view.set_png(png, 1.6)
                self.view.set_bg("#0B1120" if self.ctx.dark else "#FFFFFF")
                hs = mol.hcounts()
                rings = len(mo.find_rings(len(mol.atoms), mol.bonds))
                smiles_stats = (len(mol.atoms), sum(hs), len(mol.bonds), rings)
            except Exception:
                self.view.set_bg(None)
                self.view.set_text(
                    "Unable to render 2D molecular structure for this compound."
                    if i18n.is_en() else
                    "Không dựng được cấu trúc cho chất này."
                )
        else:
            self.view.set_bg(None)
            self.view.set_text(
                (
                    "(Elemental substance, polymer, or inorganic crystal lattice — see Wiki profile below)"
                    if i18n.is_en() else
                    "(Chất dạng đơn chất, polymer hoặc mạng tinh thể vô cơ — xem hồ sơ Wiki bên dưới)"
                ) if not smi else ""
            )

        acc = ACCENTS.get(self.ctx.prefs.get("accent", "Chàm"), ACCENTS["Chàm"])[0]
        wiki_html = dcw.build_compound_wiki_html(c, alias, mass, rows, smiles_stats, dc.REACTIONS, self.ctx.dark, acc, lang=i18n.get_lang())
        self.det.setHtml(wiki_html)

    def refresh_theme(self):
        # Đồng bộ lại màu dấu sao trong danh sách
        starred = self._starred_set()
        for i, c in enumerate(self.rows):
            if i < self.lst.count() and self._star_key(c) in starred:
                self.lst.item(i).setForeground(QColor("#FBBF24" if self.ctx.dark else "#B45309"))
        if self.isVisible():
            self.show_detail()
        else:
            self._theme_dirty = True

    def say(self):
        c = self.cur()
        if c:
            self.ctx.speak(c[1], 1.0)

    def to_smiles(self):
        c = self.cur()
        if c and c[5] and self.open_smiles:
            self.open_smiles(c[5])

    def to_sketcher(self):
        c = self.cur()
        if c and c[5] and self.open_sketcher:
            self.open_sketcher(c[5])


# ==============================================================================
# TỔNG HỢP PHẦN HÓA HỌC
# ==============================================================================
class ChemSection(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.eq = ChemEquationPage(ctx)
        self.smi = SmilesPage(ctx)
        self.sk = SketcherPage(ctx)
        self.pt = PeriodicPage(ctx)
        self.cp = CompoundPage(ctx)
        self.sk.open_smiles.connect(self.show_smiles)
        self.smi.open_sketcher.connect(self.show_sketcher)
        self.cp.open_smiles = self.show_smiles
        self.cp.open_sketcher = self.show_sketcher
        self.cp.open_equation = self.show_equation
        for w, name in (
            (self.eq, "Phương trình · Cân bằng"),
            (self.smi, "Cấu trúc SMILES"),
            (self.sk, "Trình vẽ phân tử"),
            (self.pt, "Bảng tuần hoàn 118"),
            (self.cp, f"Tra cứu chất ({len(dc.COMPOUNDS)})"),
        ):
            self.tabs.addTab(w, esc(name))
        lay.addWidget(self.tabs)

    def show_equation(self, eq):
        self.eq.editor.setPlainText(eq)
        self.eq.in_bal.setText(re.sub(r"\[[^\]]*\]", "", eq))
        self.tabs.setCurrentWidget(self.eq)
        self.ctx.say("Loaded equation from Chemistry Wiki." if i18n.is_en() else "Đã mở phương trình từ Bách khoa chất.")

    def refresh_lang(self):
        self.eq.fill_lib()
        if not self.eq.editor.toPlainText().strip():
            self.eq.render()
        self.smi.fill_mol()
        self.smi.render()
        self.sk.update_info()
        self.sk.sk.update()
        self.pt.select(self.pt.sel)
        self.cp.fill()
        self.cp.show_detail()

    def show_smiles(self, smi):
        self.smi.set_text(smi)
        self.tabs.setCurrentWidget(self.smi)

    def show_sketcher(self, smi):
        try:
            self.sk._load_smiles(smi)
            self.tabs.setCurrentWidget(self.sk)
        except Exception as exc:
            self.ctx.say(f"Không mở được trong trình vẽ: {exc}")

    def refresh_theme(self):
        self.sk.refresh_theme()
        self.pt.refresh_theme()
        self.eq.refresh_theme()
        self.smi.refresh_theme()
        self.cp.refresh_theme()
