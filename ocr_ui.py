# -*- coding: utf-8 -*-
"""ocr_ui.py - Hộp thoại quét ảnh → công thức (Toán LaTeX / PT hóa học / SMILES).
Mặc định dùng Gemini AI (online, API key miễn phí) vì rapid-latex-ocr KHÔNG có bản cho Python ≥ 3.13."""
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout)

import formula_engine as fe
import i18n
from ui_common import ImageView, copy_text, mk_btn, mk_label

KIND_TITLE = {"math": "Quét ảnh → LaTeX", "chem": "Quét ảnh → phương trình hóa học", "smiles": "Quét ảnh → SMILES (cấu trúc)"}
KIND_TITLE_EN = {"math": "Scan Image → LaTeX", "chem": "Scan Image → Chemical Equation", "smiles": "Scan Image → SMILES (Structure)"}


def qimage_to_png(img: QImage) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


class OcrDialog(QDialog):
    def __init__(self, parent, ctx, kind="math"):
        super().__init__(parent)
        self.ctx, self.kind, self.png, self.result_text, self._th = ctx, kind, None, "", None
        if getattr(ctx, "qss", ""):
            self.setStyleSheet(ctx.qss)
        en = i18n.is_en()
        title_str = (KIND_TITLE_EN if en else KIND_TITLE).get(kind, "Scan Image" if en else "Quét ảnh")
        self.setWindowTitle(title_str)
        self.resize(680, 640)
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.addWidget(mk_label(title_str, "h1"))
        self.view = ImageView(200)
        self.view.set_bg("#FFFFFF" if not ctx.dark else "#0B1120")
        self.view.set_text(
            "No image loaded.\nClick 'Paste Image' (from screenshot/clipboard) or 'Choose Image File…'."
            if en else
            "Chưa có ảnh.\nBấm «Dán ảnh» (đã chụp/copy ảnh) hoặc «Chọn tệp ảnh…»."
        )
        lay.addWidget(self.view, 1)
        row = QHBoxLayout()
        b1 = mk_btn("Paste Image from Clipboard" if en else "Dán ảnh từ clipboard", primary=True)
        b1.clicked.connect(self.paste_img)
        b2 = mk_btn("Choose Image File…" if en else "Chọn tệp ảnh…")
        b2.clicked.connect(self.pick_file)
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch()
        lay.addLayout(row)
        er = QHBoxLayout()
        er.addWidget(QLabel("OCR Engine:" if en else "Bộ nhận diện:"))
        self.cmb = QComboBox()
        for k, label in fe.available_ocr_engines():
            self.cmb.addItem(label, k)
        er.addWidget(self.cmb, 1)
        lay.addLayout(er)
        kr = QHBoxLayout()
        kr.addWidget(QLabel("Gemini API Key:"))
        self.key = QLineEdit(ctx.prefs.get("gemini_key", ""))
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("Paste a free API key from aistudio.google.com/apikey" if en else "Dán API key miễn phí từ aistudio.google.com/apikey")
        kr.addWidget(self.key, 1)
        lay.addLayout(kr)
        why = mk_label(
            (
                f"Python {sys.version_info.major}.{sys.version_info.minor} detected. Offline rapid-latex-ocr supports Python 3.6–3.12 only, "
                "so Gemini AI (free API key, high accuracy) is used automatically."
                if en else
                f"Python của bạn là {sys.version_info.major}.{sys.version_info.minor}. Gói offline «rapid-latex-ocr» chỉ có cho Python 3.6–3.12 nên "
                "không cài được trên Python mới hơn — vì vậy app dùng Gemini (online, miễn phí, chính xác)."
            ), "muted", True)
        lay.addWidget(why)
        self.btn_go = mk_btn("Recognize" if en else "Nhận diện", primary=True)
        self.btn_go.clicked.connect(self.run_ocr)
        lay.addWidget(self.btn_go)
        self.out = QPlainTextEdit()
        self.out.setPlaceholderText("Recognized output will appear here (editable before inserting)." if en else "Kết quả nhận diện sẽ hiện ở đây (có thể sửa trước khi dùng).")
        self.out.setMaximumHeight(110)
        lay.addWidget(self.out)
        br = QHBoxLayout()
        self.btn_use = mk_btn("Use Result" if en else "Dùng kết quả", primary=True)
        self.btn_use.clicked.connect(self.accept_use)
        bc = mk_btn("Copy" if en else "Sao chép")
        bc.clicked.connect(lambda: copy_text(self.out.toPlainText()))
        bx = mk_btn("Close" if en else "Đóng")
        bx.clicked.connect(self.reject)
        br.addStretch()
        br.addWidget(bc)
        br.addWidget(self.btn_use)
        br.addWidget(bx)
        lay.addLayout(br)

    def _set_png(self, data):
        self.png = data
        self.view.set_png(data, dpr=1.0)

    def paste_img(self):
        img = QGuiApplication.clipboard().image()
        if img.isNull():
            self.view.set_text(
                "No image in clipboard. Take a screenshot (Win+Shift+S) or copy an image first."
                if i18n.is_en() else
                "Clipboard không có ảnh. Hãy chụp màn hình (Win+Shift+S) hoặc copy ảnh trước."
            )
            return
        self._set_png(qimage_to_png(img))

    def pick_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Image" if i18n.is_en() else "Chọn ảnh", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            img = QImage(path)
            if not img.isNull():
                self._set_png(qimage_to_png(img))

    def run_ocr(self):
        en = i18n.is_en()
        if not self.png:
            self.out.setPlainText("No image loaded — paste or choose an image first." if en else "Chưa có ảnh — hãy dán hoặc chọn ảnh trước.")
            return
        mode = self.cmb.currentData()
        if mode == "gemini":
            self.ctx.prefs["gemini_key"] = self.key.text().strip()
            self.ctx.save_prefs()
        self.btn_go.setEnabled(False)
        self.btn_go.setText("Recognizing…" if en else "Đang nhận diện…")
        self._th = fe.OcrThread(self.png, mode, self.key.text(), self.kind, self)
        self._th.result_ready.connect(self._ok)
        self._th.error_occurred.connect(self._err)
        self._th.start()

    def _done(self):
        self.btn_go.setEnabled(True)
        self.btn_go.setText("Recognize" if i18n.is_en() else "Nhận diện")

    def _ok(self, text):
        self._done()
        self.out.setPlainText(text)

    def _err(self, msg):
        self._done()
        self.out.setPlainText("Lỗi: " + msg)

    def accept_use(self):
        t = self.out.toPlainText().strip()
        if t and not t.startswith("Lỗi:"):
            self.result_text = t
            self.accept()


def ask_ocr(parent, ctx, kind):
    d = OcrDialog(parent, ctx, kind)
    return d.result_text if d.exec() == QDialog.Accepted else ""
