# -*- coding: utf-8 -*-
"""word_ui.py - Nút «Word» ở mỗi trang + hộp thoại «Tài liệu Word» (giỏ công thức)."""
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QPushButton, QVBoxLayout

import i18n
import word_export as we
from ui_common import mk_btn, mk_label

KIND_ICON = {"math": "Toán", "chem": "Hóa", "image": "Hình", "text": "Văn bản"}
KIND_ICON_EN = {"math": "Math", "chem": "Chem", "image": "Figure", "text": "Text"}


def item_label(it):
    en = i18n.is_en()
    if it["kind"] == "image":
        return f"{it.get('title') or ('Figure' if en else 'Hình vẽ')}"
    body = it.get("latex") or it.get("text") or ""
    icons_map = KIND_ICON_EN if en else KIND_ICON
    return f"[{icons_map.get(it['kind'], '')}] {it.get('title') or ''} {body[:70]}".strip()


def qimage_png(img) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


def save_docx(parent, items) -> bool:
    path, _ = QFileDialog.getSaveFileName(parent, "Lưu tài liệu Word", "cong_thuc.docx", "Word (*.docx)")
    if not path:
        return False
    with open(path, "wb") as f:
        f.write(we.build_docx_bytes(items))
    return True


def word_button(ctx, parent, get_item, label="Word"):
    """get_item() -> dict hoặc None (kèm thông báo lỗi bằng ctx.say)."""
    b = mk_btn(label, tip="Đưa vào Microsoft Word: chèn thẳng, thêm vào tài liệu, hoặc xuất .docx")
    menu = QMenu(b)

    def fetch():
        try:
            it = get_item()
        except Exception as exc:
            ctx.say(f"Chưa có nội dung hợp lệ: {exc}")
            return None
        if not it:
            ctx.say("Chưa có nội dung để đưa vào Word.")
        return it

    def insert_now():
        it = fetch()
        if it:
            ok, msg = we.insert_into_word([it])
            ctx.say(msg if ok else msg.splitlines()[0])
            if not ok:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(parent, "Chèn vào Word", msg)

    def add():
        it = fetch()
        if it:
            ctx.add_basket(it)

    def export_one():
        it = fetch()
        if it and save_docx(parent, [it]):
            ctx.say("Đã xuất file .docx.")
    act_ins = menu.addAction("Chèn ngay vào Word đang mở (tại vị trí con trỏ)")
    act_ins.triggered.connect(insert_now)
    act_add = menu.addAction("Thêm vào «Tài liệu Word» (gom nhiều công thức rồi xuất một lần)")
    act_add.triggered.connect(add)
    act_exp = menu.addAction("Xuất file .docx (chỉ mục này)")
    act_exp.triggered.connect(export_one)
    menu.addSeparator()
    act_open = menu.addAction("Mở «Tài liệu Word»…")
    act_open.triggered.connect(ctx.open_basket)

    def _sync_menu_lang():
        if i18n.is_en():
            act_ins.setText("Insert Into Open Word (at cursor)")
            act_add.setText("Add to 'Word Document' Basket (batch export)")
            act_exp.setText("Export .docx File (this item only)")
            act_open.setText("Open 'Word Document'…")
        else:
            act_ins.setText("Chèn ngay vào Word đang mở (tại vị trí con trỏ)")
            act_add.setText("Thêm vào «Tài liệu Word» (gom nhiều công thức rồi xuất một lần)")
            act_exp.setText("Xuất file .docx (chỉ mục này)")
            act_open.setText("Mở «Tài liệu Word»…")

    menu.aboutToShow.connect(_sync_menu_lang)
    b.setMenu(menu)
    return b


class WordBasketDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        if getattr(ctx, "qss", ""):
            self.setStyleSheet(ctx.qss)
        en = i18n.is_en()
        self.setWindowTitle("Word Document" if en else "Tài liệu Word")
        self.resize(640, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(mk_label("Word Document" if en else "Tài liệu Word", "h1"))
        lay.addWidget(mk_label(
            "Items below will be exported into a .docx file in order. Math formulas and chemical equations become native editable Word Equations; molecules and geometry are crisp images."
            if en else
            "Các mục dưới đây sẽ được xuất thành file .docx theo thứ tự. Công thức Toán và phương trình hóa học thành "
            "equation GỐC của Word (sửa được); cấu trúc phân tử và hình học là ảnh.", "muted", True))
        self.lst = QListWidget()
        lay.addWidget(self.lst, 1)
        r = QHBoxLayout()
        btns = (
            (("↑ Up", lambda: self.move(-1)), ("↓ Down", lambda: self.move(1)), ("Remove Item", self.remove), ("Clear All", self.clear))
            if en else
            (("↑ Lên", lambda: self.move(-1)), ("↓ Xuống", lambda: self.move(1)), ("Xóa mục", self.remove), ("Xóa hết", self.clear))
        )
        for text, fn in btns:
            b = mk_btn(text)
            b.clicked.connect(fn)
            r.addWidget(b)
        r.addStretch()
        lay.addLayout(r)
        r2 = QHBoxLayout()
        b1 = mk_btn("Export .docx" if en else "Xuất file .docx", primary=True)
        b1.clicked.connect(self.export)
        b2 = mk_btn("Insert Into Open Word" if en else "Chèn vào Word đang mở", primary=True)
        b2.clicked.connect(self.insert)
        b3 = mk_btn("Close" if en else "Đóng")
        b3.clicked.connect(self.accept)
        r2.addWidget(b1)
        r2.addWidget(b2)
        r2.addStretch()
        r2.addWidget(b3)
        lay.addLayout(r2)
        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        lay.addWidget(self.msg)
        self.refill()

    def refill(self, sel=None):
        self.lst.clear()
        for it in self.ctx.basket:
            self.lst.addItem(QListWidgetItem(item_label(it)))
        if sel is not None and 0 <= sel < self.lst.count():
            self.lst.setCurrentRow(sel)
        self.ctx.basket_changed()

    def move(self, d):
        r = self.lst.currentRow()
        n = r + d
        if 0 <= r < len(self.ctx.basket) and 0 <= n < len(self.ctx.basket):
            b = self.ctx.basket
            b[r], b[n] = b[n], b[r]
            self.refill(n)

    def remove(self):
        r = self.lst.currentRow()
        if 0 <= r < len(self.ctx.basket):
            self.ctx.basket.pop(r)
            self.refill(min(r, len(self.ctx.basket) - 1))

    def clear(self):
        self.ctx.basket.clear()
        self.refill()

    def export(self):
        en = i18n.is_en()
        if not self.ctx.basket:
            self.msg.setText("No items yet." if en else "Chưa có mục nào.")
        elif save_docx(self, self.ctx.basket):
            self.msg.setText("Exported .docx file." if en else "Đã xuất file .docx.")

    def insert(self):
        ok, msg = we.insert_into_word(self.ctx.basket)
        self.msg.setText(("" if ok else "") + msg)
