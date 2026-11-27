import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

import data_store as ds
import formula_engine as eng


def _dist_pt_seg(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    if l2 < 1e-6:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


# ==============================================================================
# 1. MÔ HÌNH BOHR & SƠ ĐỒ Ô ORBITAL (hỗ trợ Sáng & Tối)
# ==============================================================================
class BohrWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 270)
        self.element = ds.ELEMENTS_BY_Z[26]
        self.struct = eng.compute_electron_structure(26)
        self.dark = False

    def set_dark(self, dark: bool):
        self.dark = bool(dark)
        self.update()

    def set_element(self, z: int):
        self.element = ds.ELEMENTS_BY_Z[z]
        self.struct = eng.compute_electron_structure(z)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_on(p, QRectF(self.rect()), self.dark)
        p.end()

    def _draw_on(self, p: QPainter, rect: QRectF, dark=False):
        bg = QColor("#0B1120" if dark else "#FFFFFF")
        fg = QColor("#F1F5F9" if dark else "#0F172A")
        ring_c = QColor("#334155" if dark else "#CBD5E1")
        e_fill = QColor("#818CF8" if dark else "#4F46E5")
        e_edge = QColor("#0B1120" if dark else "#FFFFFF")
        nuc_fill = QColor("#1E1B4B" if dark else "#EEF2FF")
        nuc_edge = QColor("#818CF8" if dark else "#4338CA")
        nuc_txt = QColor("#E0E7FF" if dark else "#312E81")
        sub_txt = QColor("#94A3B8" if dark else "#475569")

        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, 10, 10)
        w, h = rect.width(), rect.height()
        cx, cy = w / 2.0, h / 2.0 + 4
        z, sym, en_name = self.element[0], self.element[1], self.element[2]
        shells = self.struct["shells"]

        p.setPen(fg)
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(QRectF(0, 6, w, 22), Qt.AlignmentFlag.AlignCenter, f"{sym} · {en_name} · Z = {z}")

        max_r = min(w, h - 64) * 0.44
        nuc_r = 21
        step = (max_r - nuc_r - 8) / max(1, len(shells))
        for idx, count in enumerate(shells):
            r = nuc_r + (idx + 1) * step
            p.setPen(QPen(ring_c, 1.3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.setPen(QPen(e_edge, 1.0))
            p.setBrush(QBrush(e_fill))
            for k in range(count):
                ang = -math.pi / 2 + 2 * math.pi * k / count
                p.drawEllipse(QPointF(cx + r * math.cos(ang), cy + r * math.sin(ang)), 4.0, 4.0)

        p.setPen(QPen(nuc_edge, 1.8))
        p.setBrush(QBrush(nuc_fill))
        p.drawEllipse(QPointF(cx, cy), nuc_r, nuc_r)
        p.setPen(nuc_txt)
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(QRectF(cx - nuc_r, cy - 13, nuc_r * 2, 16), Qt.AlignmentFlag.AlignCenter, sym)
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(QRectF(cx - nuc_r, cy + 1, nuc_r * 2, 14), Qt.AlignmentFlag.AlignCenter, f"{z}+")

        shell_txt = " · ".join(f"{eng.SHELL_NAMES[i]}: {cnt}" for i, cnt in enumerate(shells))
        p.setPen(sub_txt)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.drawText(QRectF(8, h - 26, w - 16, 20), Qt.AlignmentFlag.AlignCenter, shell_txt)

    def render_to_pixmap(self, size=(520, 500)) -> QPixmap:
        pix = QPixmap(size[0], size[1])
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_on(p, QRectF(0, 0, size[0], size[1]), dark=False)
        p.end()
        return pix

    def to_svg_bytes(self) -> bytes:
        w, h = 440, 420
        cx, cy = w / 2, h / 2 + 6
        z, sym, en_name = self.element[0], self.element[1], self.element[2]
        shells = self.struct["shells"]
        step = (152 - 34) / max(1, len(shells))
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            '<rect width="100%" height="100%" fill="#FFFFFF"/>',
            f'<text x="{cx}" y="24" text-anchor="middle" font-family="Segoe UI" font-size="15" font-weight="bold" fill="#0F172A">{sym} · {en_name} · Z = {z}</text>',
        ]
        for idx, count in enumerate(shells):
            r = 26 + (idx + 1) * step
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" stroke="#94A3B8" stroke-width="1.3"/>')
            for k in range(count):
                ang = -math.pi / 2 + 2 * math.pi * k / count
                parts.append(f'<circle cx="{cx + r * math.cos(ang):.1f}" cy="{cy + r * math.sin(ang):.1f}" r="4.3" fill="#4F46E5" stroke="#FFFFFF" stroke-width="1"/>')
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="26" fill="#EEF2FF" stroke="#4338CA" stroke-width="2"/>')
        parts.append(f'<text x="{cx}" y="{cy - 1}" text-anchor="middle" font-family="Segoe UI" font-size="13" font-weight="bold" fill="#312E81">{sym}</text>')
        parts.append(f'<text x="{cx}" y="{cy + 13}" text-anchor="middle" font-family="Segoe UI" font-size="10" fill="#312E81">{z}+</text>')
        shell_txt = " · ".join(f"{eng.SHELL_NAMES[i]}: {cnt}" for i, cnt in enumerate(shells))
        parts.append(f'<text x="{cx}" y="{h - 14}" text-anchor="middle" font-family="Segoe UI" font-size="12" fill="#475569">{shell_txt}</text>')
        parts.append("</svg>")
        return "\n".join(parts).encode("utf-8")


class OrbitalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(430, 270)
        self.element = ds.ELEMENTS_BY_Z[26]
        self.struct = eng.compute_electron_structure(26)
        self.dark = False

    def set_dark(self, dark: bool):
        self.dark = bool(dark)
        self.update()

    def set_element(self, z: int):
        self.element = ds.ELEMENTS_BY_Z[z]
        self.struct = eng.compute_electron_structure(z)
        self.setMinimumHeight(max(270, 92 + len(self.struct["orbitals_by_shell"]) * 50))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_on(p, QRectF(self.rect()), self.dark)
        p.end()

    def _draw_on(self, p: QPainter, rect: QRectF, dark=False):
        bg = QColor("#0B1120" if dark else "#FFFFFF")
        fg = QColor("#F1F5F9" if dark else "#0F172A")
        acc = QColor("#818CF8" if dark else "#4F46E5")
        lbl_c = QColor("#94A3B8" if dark else "#475569")
        sub_c = QColor("#CBD5E1" if dark else "#334155")
        box_bg = QColor("#1E293B" if dark else "#F8FAFC")
        box_bd = QColor("#475569" if dark else "#94A3B8")

        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, 10, 10)
        z, sym, en_name = self.element[0], self.element[1], self.element[2]
        p.setPen(fg)
        p.setFont(QFont("Segoe UI", 10.5, QFont.Weight.Bold))
        p.drawText(16, 24, f"{sym} · {en_name} · Z = {z}")
        p.setPen(acc)
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.drawText(16, 44, self.struct["condensed_config"])

        y = 70
        box_sz = 25
        for n in sorted(self.struct["orbitals_by_shell"].keys()):
            p.setPen(lbl_c)
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.drawText(16, y + 17, f"{eng.SHELL_NAMES[n - 1]} (n={n})")
            x = 88
            for sub_label, boxes in self.struct["orbitals_by_shell"][n]:
                p.setPen(sub_c)
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
                p.drawText(x, y - 4, sub_label)
                for occ in boxes:
                    p.setPen(QPen(box_bd, 1.2))
                    p.setBrush(QBrush(box_bg))
                    p.drawRoundedRect(QRectF(x, y, box_sz, box_sz), 4, 4)
                    arrow = "↑↓" if occ == 2 else ("↑" if occ == 1 else "")
                    if arrow:
                        p.setPen(fg)
                        p.setFont(QFont("Segoe UI", 10.5, QFont.Weight.Bold))
                        p.drawText(QRectF(x, y, box_sz, box_sz), Qt.AlignmentFlag.AlignCenter, arrow)
                    x += box_sz + 3
                x += 11
            y += 48
        p.setPen(fg)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.drawText(16, y + 8, f"Electron độc thân: {self.struct['unpaired']}  ·  Hund & Pauli  ·  Khối {self.struct['block']}")

    def render_to_pixmap(self) -> QPixmap:
        w, h = max(620, self.width()), max(300, self.minimumHeight())
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_on(p, QRectF(0, 0, w, h), dark=False)
        p.end()
        return pix

    def to_svg_bytes(self) -> bytes:
        n_shells = len(self.struct["orbitals_by_shell"])
        w, h = 680, max(300, 105 + n_shells * 50)
        z, sym, en_name = self.element[0], self.element[1], self.element[2]
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            '<rect width="100%" height="100%" fill="#FFFFFF"/>',
            f'<text x="16" y="26" font-family="Segoe UI" font-size="14" font-weight="bold" fill="#0F172A">{sym} · {en_name} · Z = {z}</text>',
            f'<text x="16" y="46" font-family="Segoe UI" font-size="12" fill="#4F46E5">{self.struct["condensed_config"]}</text>',
        ]
        y = 72
        for n in sorted(self.struct["orbitals_by_shell"].keys()):
            parts.append(f'<text x="16" y="{y + 17}" font-family="Segoe UI" font-size="11" font-weight="bold" fill="#475569">{eng.SHELL_NAMES[n - 1]} (n={n})</text>')
            x = 92
            for sub_label, boxes in self.struct["orbitals_by_shell"][n]:
                parts.append(f'<text x="{x}" y="{y - 4}" font-family="Segoe UI" font-size="10" fill="#334155">{sub_label}</text>')
                for occ in boxes:
                    parts.append(f'<rect x="{x}" y="{y}" width="25" height="25" rx="4" fill="#F8FAFC" stroke="#64748B" stroke-width="1.2"/>')
                    arrow = "↑↓" if occ == 2 else ("↑" if occ == 1 else "")
                    if arrow:
                        parts.append(f'<text x="{x + 12.5}" y="{y + 17}" text-anchor="middle" font-family="Segoe UI" font-size="12" font-weight="bold" fill="#0F172A">{arrow}</text>')
                    x += 28
                x += 11
            y += 48
        parts.append("</svg>")
        return "\n".join(parts).encode("utf-8")


# ==============================================================================
# 2. BẢNG TUẦN HOÀN 118 NGUYÊN TỐ VẼ BẰNG QPAINTER (SIÊU MƯỢT, 0 LAG KHI ĐỔI THEME)
# ==============================================================================
class PeriodicTableWidget(QWidget):
    """Bảng tuần hoàn 118 nguyên tố vẽ trực tiếp bằng QPainter:
    đổi Sáng/Tối tức thì (<1ms), hover mượt, lọc nhóm/từ khóa không giật, xuất ảnh PNG sắc nét."""
    selected = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(940, 580)
        self.sel_z = 26
        self.hover_z = None
        self.dark = False
        self.query = ""
        self.active_cat = None
        self.on_select = None
        self._rects = {}  # z -> QRectF

    def set_dark(self, dark: bool):
        self.dark = bool(dark)
        self.update()

    def set_filter(self, query: str = "", active_cat=None):
        self.query = (query or "").strip().lower()
        self.active_cat = active_cat
        self.update()

    def set_selected(self, z: int):
        self.sel_z = z
        self.update()

    def _matches(self, el) -> bool:
        z, sym, en, vi, lat, ipa, mass, cat, row, col, per, grp = el
        if self.active_cat not in (None, cat):
            return False
        q = self.query
        if not q:
            return True
        return q in str(z) or q == sym.lower() or q in en.lower() or q in vi.lower() or q in lat.lower()

    def _cell_layout(self, rect: QRectF):
        pad_x, pad_y = 4.0, 4.0
        gap = 3.2
        cols = 18
        avail_w = rect.width() - pad_x * 2
        avail_h = rect.height() - pad_y * 2 - 14.0  # thêm khe ngăn họ Lanthanide/Actinide
        cw = (avail_w - gap * (cols - 1)) / cols
        ch = min(cw * 1.06, (avail_h - gap * 9) / 10.0)
        cw = min(cw, ch * 1.18)
        total_w = cols * cw + (cols - 1) * gap
        total_h = 10 * ch + 9 * gap + 12.0
        ox = rect.x() + (rect.width() - total_w) / 2.0
        oy = rect.y() + (rect.height() - total_h) / 2.0
        return ox, oy, cw, ch, gap

    def _cell_rect(self, row, col, ox, oy, cw, ch, gap) -> QRectF:
        y_extra = 12.0 if row >= 8 else 0.0
        return QRectF(ox + col * (cw + gap), oy + row * (ch + gap) + y_extra, cw, ch)

    def _hit_z(self, pos):
        for z, r in self._rects.items():
            if r.contains(pos):
                return z
        return None

    def mouseMoveEvent(self, e):
        z = self._hit_z(e.position())
        if z != self.hover_z:
            self.hover_z = z
            if z is not None:
                el = ds.ELEMENTS_BY_Z[z]
                self.setToolTip(f"{el[0]} – {el[1]} ({el[2]})  ·  Aᵣ = {el[6]}")
            else:
                self.setToolTip("")
            self.update()

    def leaveEvent(self, e):
        if self.hover_z is not None:
            self.hover_z = None
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            z = self._hit_z(e.position())
            if z is not None:
                self.sel_z = z
                self.update()
                if self.on_select:
                    self.on_select(z)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._draw_table(p, QRectF(self.rect()), self.dark)
        p.end()

    def _draw_table(self, p: QPainter, rect: QRectF, dark: bool):
        bg = QColor("#151E32" if dark else "#FFFFFF")
        p.fillRect(rect, bg)
        ox, oy, cw, ch, gap = self._cell_layout(rect)
        self._rects.clear()

        f_z = QFont("Segoe UI", max(7, int(ch * 0.175)), QFont.Weight.DemiBold)
        f_sym = QFont("Segoe UI", max(10, int(ch * 0.30)), QFont.Weight.Bold)
        f_mass = QFont("Segoe UI", max(7, int(ch * 0.165)))
        f_hint = QFont("Segoe UI", max(8, int(ch * 0.19)), QFont.Weight.DemiBold)

        # Nhãn nhóm 57–71 và 89–103
        for r_i, txt in ((5, "57–71"), (6, "89–103")):
            mr = self._cell_rect(r_i, 2, ox, oy, cw, ch, gap)
            p.setPen(QColor("#64748B" if dark else "#94A3B8"))
            p.setFont(f_hint)
            p.drawText(mr, Qt.AlignmentFlag.AlignCenter, txt)

        for el in ds.ELEMENTS_RAW:
            z, sym, en, vi, lat, ipa, mass, cat, row, col, per, grp = el
            r = self._cell_rect(row, col, ox, oy, cw, ch, gap)
            self._rects[z] = r
            hc = QColor(ds.CATEGORY_LABELS[cat][1])
            match = self._matches(el)
            is_sel = (z == self.sel_z)
            is_hov = (z == self.hover_z)

            if is_sel or match:
                fill = QColor(hc)
                if dark and not is_sel:
                    fill.setAlpha(210 if is_hov else 175)
                elif not dark and is_hov and not is_sel:
                    fill = fill.lighter(108)
                lum = fill.lightness()
                fg = QColor("#0F172A" if (lum > 145 and not dark) else "#FFFFFF")
                if is_sel:
                    bd = QColor("#FFFFFF" if dark else "#0F172A")
                    bw = 2.4
                elif is_hov:
                    bd = QColor("#F8FAFC" if dark else "#1E293B")
                    bw = 1.6
                else:
                    bd = QColor(hc)
                    bd.setAlpha(180)
                    bw = 1.0
            else:
                fill = QColor(hc)
                fill.setAlpha(28 if dark else 34)
                fg = QColor(hc)
                fg.setAlpha(110)
                bd = QColor(hc)
                bd.setAlpha(45)
                bw = 0.8

            p.setPen(QPen(bd, bw))
            p.setBrush(QBrush(fill))
            p.drawRoundedRect(r, 7, 7)

            p.setPen(fg)
            p.setFont(f_z)
            p.drawText(QRectF(r.x() + 3, r.y() + 2, r.width() - 6, ch * 0.28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, str(z))
            p.setFont(f_sym)
            p.drawText(QRectF(r.x(), r.y() + ch * 0.24, r.width(), ch * 0.46), Qt.AlignmentFlag.AlignCenter, sym)
            p.setFont(f_mass)
            m_txt = f"{mass:.2f}" if mass < 100 else f"{mass:.1f}"
            p.drawText(QRectF(r.x() + 2, r.y() + ch * 0.70, r.width() - 4, ch * 0.26), Qt.AlignmentFlag.AlignCenter, m_txt)

    def render_to_pixmap(self) -> QPixmap:
        w, h = max(1120, self.width()), max(620, self.height())
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._draw_table(p, QRectF(0, 0, w, h), False)
        p.end()
        return pix

