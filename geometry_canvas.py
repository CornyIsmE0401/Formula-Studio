# -*- coding: utf-8 -*-
"""geometry_canvas.py - Hình học động & Đồ thị chuyên nghiệp kiểu GeoGebra-lite:
điểm tự do/phụ thuộc, đoạn/đường/tia/vectơ, đường tròn, đa giác, góc (ký hiệu góc vuông chuẩn),
trung điểm, vuông góc/song song/phân giác/trung trực, đối xứng trục/tâm, tiếp tuyến đường tròn,
giao điểm, tâm đặc biệt tam giác, đồ thị hàm số (có cache AST & dò tọa độ trực tiếp trên đường cong),
24 hình mẫu 2D/3D, đo đạc, hoàn tác, lưu/mở .geo, xuất PNG/SVG."""
import json
import math

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QColorDialog, QInputDialog, QMenu, QWidget

import calc_engine as ce

TOOLS = {
    "select": ("Chọn / Di chuyển (V)", ()),
    "point": ("Điểm (P)", ("P",)),
    "seg": ("Đoạn thẳng (S)", ("P", "P")),
    "line": ("Đường thẳng (L)", ("P", "P")),
    "ray": ("Tia", ("P", "P")),
    "vec": ("Vectơ", ("P", "P")),
    "circle": ("Đường tròn (tâm + điểm) (C)", ("P", "P")),
    "circ3": ("Đường tròn qua 3 điểm", ("P", "P", "P")),
    "poly": ("Đa giác (G)", ("*",)),
    "angle": ("Góc (A, đỉnh B, C) (A)", ("P", "P", "P")),
    "mid": ("Trung điểm", ("P", "P")),
    "perp": ("Đường vuông góc", ("P", "O")),
    "para": ("Đường song song", ("P", "O")),
    "bis": ("Phân giác góc (A, đỉnh B, C)", ("P", "P", "P")),
    "perpbis": ("Đường trung trực", ("P", "P")),
    "foot": ("Chân đường vuông góc", ("P", "O")),
    "inter": ("Giao điểm", ("O", "O")),
    "reflect": ("Đối xứng qua đường thẳng", ("P", "O")),
    "sym_pt": ("Đối xứng qua tâm", ("P", "P")),
    "tangent": ("Tiếp tuyến từ điểm đến đường tròn", ("P", "O")),
    "centroid": ("Trọng tâm tam giác", ("P", "P", "P")),
    "circum": ("Tâm đường tròn ngoại tiếp", ("P", "P", "P")),
    "incenter": ("Tâm đường tròn nội tiếp", ("P", "P", "P")),
    "ortho": ("Trực tâm tam giác", ("P", "P", "P")),
    "text": ("Chú thích", ()),
    "erase": ("Xóa (E)", ()),
}

TOOLS_EN = {
    "select": "Select / Move (V)",
    "point": "Point (P)",
    "seg": "Segment (S)",
    "line": "Line (L)",
    "ray": "Ray",
    "vec": "Vector",
    "circle": "Circle (Center + Point) (C)",
    "circ3": "Circle Through 3 Points",
    "poly": "Polygon (G)",
    "angle": "Angle (A, Vertex B, C) (A)",
    "mid": "Midpoint",
    "perp": "Perpendicular Line",
    "para": "Parallel Line",
    "bis": "Angle Bisector (A, Vertex B, C)",
    "perpbis": "Perpendicular Bisector",
    "foot": "Foot of Perpendicular",
    "inter": "Intersection Point",
    "reflect": "Reflect Across Line",
    "sym_pt": "Central Symmetry",
    "tangent": "Tangent to Circle",
    "centroid": "Triangle Centroid",
    "circum": "Circumcenter",
    "incenter": "Incenter",
    "ortho": "Orthocenter",
    "text": "Text Annotation",
    "erase": "Erase (E)",
}


def _tool_label(k):
    import i18n
    return TOOLS_EN.get(k, TOOLS.get(k, ("",))[0]) if i18n.is_en() else TOOLS.get(k, ("",))[0]


LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FUNC_COLORS = ["#2563EB", "#E11D48", "#059669", "#D97706", "#7C3AED", "#0891B2", "#DB2777"]

FIGURES = [
    "Tam giác thường", "Tam giác vuông", "Tam giác cân", "Tam giác đều",
    "Tam giác + Đường tròn ngoại tiếp", "Tam giác + Đường tròn nội tiếp", "Tam giác + 3 đường cao (Trực tâm)",
    "Hình chữ nhật", "Hình vuông", "Hình bình hành", "Hình bình hành + Hai đường chéo",
    "Hình thang", "Hình thang cân", "Hình thang vuông",
    "Hình thoi", "Hình thoi + Hai đường chéo", "Ngũ giác đều", "Lục giác đều",
    "Tứ diện đều S.ABC", "Hình chóp tam giác S.ABC", "Hình chóp tứ giác S.ABCD", "Hình chóp cụt tứ giác",
    "Hình lăng trụ tam giác ABC.A'B'C'", "Lăng trụ đứng tứ giác ABCD.A'B'C'D'",
    "Hình hộp chữ nhật ABCD.A'B'C'D'", "Hình lập phương ABCD.A'B'C'D'",
    "Hình trụ (mô phỏng 3D)", "Hình nón (mô phỏng 3D)",
]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


class GeometryCanvas(QWidget):
    status = Signal(str)
    info_changed = Signal(str)
    tool_changed = Signal(str)
    objs_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 320)
        self.setFocusPolicy(Qt.StrongFocus)
        self.points, self.order, self.objs = {}, [], []
        self.counter = 1
        self.tool, self.pending = "select", []
        self.scale, self.origin = 48.0, QPointF(260, 260)
        self.show_grid, self.show_axes, self.show_labels, self.show_measure = True, True, True, True
        self.snap, self.dark = True, False
        self.bg_hex, self.grid_hex = "#FFFFFF", "#EAEFF7"
        self.sel = None            # ("p", id) | ("o", idx)
        self.hover = None          # ("p", id) | ("o", idx) | ("edge", u, v)
        self.snap_target = None    # dict(wx, wy, kind, ...) — vị trí đặt điểm chính xác + vòng tròn xem trước
        self.trace_pt = None       # (wx, wy, expr, color) khi rê chuột gần đồ thị
        self._warn_msg = ""        # cảnh báo ngắn trên canvas khi nhấp sai loại đối tượng
        self.drag = None
        self.drag_lbl = None       # (target, start_pos, orig_x, orig_y) — kéo chỉnh vị trí nhãn điểm / góc / số đo / chú thích
        self._label_rects = []     # [(QRectF, target)]
        self.hover_lbl = None      # target đang rê chuột lên nhãn
        self.pan_from = None
        self.mouse_pos = QPointF(-1000, -1000)
        self.undo_stack, self.redo_stack = [], []
        self.cur_color = "#2563EB"
        self.cur_dashed = False
        self.cur_width = 2.0
        self.fill_polys = True
        self._init_origin = False
        self._func_cache = {}      # expr -> (Calc, parsed_node)
        self._func_color_idx = 0

    # ------------------------------------------------------------------ tiện ích
    def set_dark(self, d, bg_hex=None, grid_hex=None):
        self.dark = bool(d)
        self.bg_hex = bg_hex or ("#0A0F1C" if self.dark else "#FFFFFF")
        self.grid_hex = grid_hex or ("#192338" if self.dark else "#EAEFF7")
        self.update()

    @property
    def bg(self):
        return QColor(self.bg_hex)

    @property
    def fg(self):
        return QColor("#F1F5F9" if self.dark else "#0F172A")

    def w2s(self, x, y):
        return QPointF(self.origin.x() + x * self.scale, self.origin.y() - y * self.scale)

    def s2w(self, p):
        return ((p.x() - self.origin.x()) / self.scale, (self.origin.y() - p.y()) / self.scale)

    def next_label(self):
        used = {p["label"] for p in self.points.values()}
        for k in range(1, 20):
            for ch in LABELS:
                name = ch if k == 1 else f"{ch}{k - 1}"
                if name not in used:
                    return name
        return "P"

    def set_tool(self, t):
        self.tool, self.pending, self._warn_msg = t, [], ""
        self.tool_changed.emit(t)
        self.status.emit(_tool_label(t) + " — " + self._hint())
        self.update()

    def _grid_step(self):
        raw_step = 48.0 / max(self.scale, 1e-6)
        exp = math.floor(math.log10(raw_step))
        base = 10.0 ** exp
        mant = raw_step / base
        if mant < 1.5:
            return base
        if mant < 3.5:
            return 2.0 * base
        if mant < 7.5:
            return 5.0 * base
        return 10.0 * base

    def _next_need(self):
        """Trả về loại đối tượng cần nhấp tiếp theo: 'P', 'O', 'PO' (linh hoạt điểm hoặc đường), hoặc None."""
        spec = TOOLS[self.tool][1]
        if not spec:
            return None
        if spec[0] == "*":
            return "P"
        if spec == ("P", "O"):
            if not self.pending:
                return "PO"
            return "O" if self.pending[0][0] == "p" else "P"
        if len(self.pending) < len(spec):
            return spec[len(self.pending)]
        return None

    def _step_prompt(self):
        """Chuỗi hướng dẫn ngắn gọn ngay trên canvas cho bước dựng hình hiện tại."""
        if self.tool == "select":
            return ""
        import i18n
        en = i18n.is_en()
        name = _tool_label(self.tool)
        if self._warn_msg:
            return f"{name}  ·  {self._warn_msg}"
        if self.tool == "poly":
            k = len(self.pending)
            if k == 0:
                return f"{name}  ·  " + ("Click polygon vertices (click first vertex or Enter to close)" if en else "Nhấp các đỉnh đa giác (nhấp lại đỉnh đầu hoặc Enter để khép)")
            if k < 3:
                return f"{name}  ·  " + (f"{k} vertices picked — click vertex {k + 1}" if en else f"Đã chọn {k} đỉnh — nhấp tiếp đỉnh thứ {k + 1}")
            return f"{name}  ·  " + (f"{k} vertices picked — click more, or click first vertex / Enter to close" if en else f"Đã chọn {k} đỉnh — nhấp tiếp, hoặc nhấp lại đỉnh đầu / Enter để đóng")
        if self.tool == "point":
            return f"{name}  ·  " + ("Click anywhere to place a point" if en else "Nhấp vị trí bất kỳ để tạo điểm")
        if self.tool == "text":
            return f"{name}  ·  " + ("Click where to place text annotation" if en else "Nhấp vị trí cần đặt chú thích")
        if self.tool == "erase":
            return f"{name}  ·  " + ("Click a point or object to delete" if en else "Nhấp điểm hoặc đối tượng cần xóa")
        spec = TOOLS[self.tool][1]
        total = len(spec)
        step = len(self.pending) + 1
        need = self._next_need()
        if self.tool == "tangent":
            if need == "PO":
                return f"{name}  ·  " + ("Step 1/2: Click a point or an existing circle" if en else "Bước 1/2: Nhấp 1 điểm hoặc 1 đường tròn đã vẽ")
            return f"{name}  ·  " + (("Step 2/2: Click an existing CIRCLE" if need == "O" else "Step 2/2: Click / place a POINT") if en else ("Bước 2/2: Nhấp vào ĐƯỜNG TRÒN đã vẽ" if need == "O" else "Bước 2/2: Nhấp chọn / tạo ĐIỂM"))
        if spec == ("P", "O"):
            if need == "PO":
                return f"{name}  ·  " + ("Step 1/2: Click a point (or a segment/line/polygon edge)" if en else "Bước 1/2: Nhấp 1 điểm (hoặc 1 đoạn/đường thẳng/cạnh đa giác)")
            return f"{name}  ·  " + (("Step 2/2: Click an existing SEGMENT / LINE / EDGE" if need == "O" else "Step 2/2: Click / place a POINT") if en else ("Bước 2/2: Nhấp vào ĐOẠN / ĐƯỜNG THẲNG / CẠNH ĐA GIÁC đã vẽ" if need == "O" else "Bước 2/2: Nhấp chọn / tạo ĐIỂM"))
        if spec == ("O", "O"):
            return f"{name}  ·  " + (f"Step {step}/2: Click line, segment, polygon edge, or circle #{step}" if en else f"Bước {step}/2: Nhấp chọn đường thẳng, đoạn, cạnh đa giác hoặc đường tròn thứ {step}")
        return f"{name}  ·  " + (f"Step {step}/{total}: Click or place point #{step}" if en else f"Bước {step}/{total}: Nhấp chọn hoặc tạo điểm thứ {step}")

    def _hint(self):
        import i18n
        en = i18n.is_en()
        spec = TOOLS[self.tool][1]
        if self.tool == "select":
            return ("drag points, labels, or notes · drag empty space to pan · scroll to zoom · hover curves for coordinates"
                    if en else "kéo điểm để di chuyển · kéo vùng trống để cuộn · cuộn chuột để thu phóng · rê lên đồ thị để xem tọa độ")
        if self.tool == "text":
            return "click where to place text annotation" if en else "nhấp vào vị trí cần đặt chú thích"
        if self.tool == "erase":
            return "click a point or object to delete" if en else "nhấp vào điểm hoặc đối tượng cần xóa"
        if self.tool == "poly":
            return "click vertices; click first vertex or press Enter to close" if en else "nhấp các đỉnh; nhấp lại đỉnh đầu hoặc nhấn Enter để đóng"
        if self.tool == "reflect":
            return "pick a point to reflect, then pick the axis line" if en else "chọn điểm cần lấy đối xứng, sau đó chọn đường thẳng trục"
        if self.tool == "sym_pt":
            return "pick a point to reflect, then pick the symmetry center" if en else "chọn điểm cần lấy đối xứng, sau đó chọn tâm đối xứng"
        if self.tool == "tangent":
            return "pick a point, then pick a circle" if en else "chọn điểm ngoài/trên đường tròn, sau đó chọn đường tròn"
        names = ({"P": "point", "O": "line/segment/circle"} if en else {"P": "điểm", "O": "đường/đoạn/đường tròn"})
        if not spec:
            return ""
        return (f"select {len(spec)} objects: " if en else f"chọn {len(spec)} đối tượng: ") + ", ".join(names[x] for x in spec)

    def center_origin(self):
        self.origin = QPointF(self.width() * 0.5, self.height() * 0.5)
        self.scale = 48.0
        self.update()

    def zoom_by(self, factor):
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        wx, wy = self.s2w(center)
        self.scale = max(0.5, min(600.0, self.scale * factor))
        self.origin = QPointF(center.x() - wx * self.scale, center.y() + wy * self.scale)
        self.update()

    def fit_view(self):
        pts = [(p["x"], p["y"]) for p in self.points.values() if not p.get("hidden")]
        if not pts:
            self.center_origin()
            return
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        w = max(max(xs) - min(xs), 2.0) * 1.2 + 2.0
        h = max(max(ys) - min(ys), 2.0) * 1.2 + 2.0
        self.scale = max(0.5, min(200.0, min(self.width() / w, self.height() / h)))
        cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
        self.origin = QPointF(self.width() / 2.0 - cx * self.scale, self.height() / 2.0 + cy * self.scale)
        self.update()

    # ------------------------------------------------------------------ lịch sử
    def _state(self):
        return json.dumps({"points": self.points, "order": self.order, "objs": self.objs, "counter": self.counter}, ensure_ascii=False)

    def _load_state(self, s):
        d = json.loads(s)
        self.points = {int(k): v for k, v in d["points"].items()}
        self.order, self.objs, self.counter = d["order"], d["objs"], d["counter"]
        self.sel = None
        self.recompute()
        self.objs_changed.emit()

    def push_undo(self):
        self.undo_stack.append(self._state())
        if len(self.undo_stack) > 80:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self._state())
            self._load_state(self.undo_stack.pop())
            self.update()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self._state())
            self._load_state(self.redo_stack.pop())
            self.update()

    def clear_all(self):
        if not self.points and not self.objs:
            return
        self.push_undo()
        self.points, self.order, self.objs, self.counter, self.sel, self.pending = {}, [], [], 1, None, []
        self.objs_changed.emit()
        self.info_changed.emit("")
        self.update()

    def to_json(self):
        return self._state()

    def from_json(self, s):
        self.push_undo()
        self._load_state(s)
        self.fit_view()
        self.update()

    # ------------------------------------------------------------------ tạo đối tượng
    def add_point(self, x, y, kind="free", parents=(), label=None, **kw):
        pid = self.counter
        self.counter += 1
        self.points[pid] = {
            "id": pid, "label": label or self.next_label(), "kind": kind, "x": x, "y": y,
            "parents": list(parents), "color": kw.get("color"), "hidden": kw.get("hidden", False), "idx": kw.get("idx", 0),
        }
        self.order.append(pid)
        return pid

    def add_obj(self, typ, pts=(), **kw):
        o = {
            "type": typ, "pts": list(pts), "color": kw.get("color", self.cur_color),
            "dashed": kw.get("dashed", self.cur_dashed), "width": kw.get("width", self.cur_width),
            "label": kw.get("label", ""), "ref": kw.get("ref"), "expr": kw.get("expr", ""),
            "x": kw.get("x", 0), "y": kw.get("y", 0), "text": kw.get("text", ""), "hidden": False,
            "idx": kw.get("idx", 0), "edge_ref": kw.get("edge_ref", False),
        }
        self.objs.append(o)
        self.objs_changed.emit()
        return len(self.objs) - 1

    # ------------------------------------------------------------------ hình học
    def P(self, pid):
        p = self.points[pid]
        return (p["x"], p["y"])

    def line_of(self, o):
        t = o["type"]
        try:
            if t in ("seg", "line", "ray", "vec"):
                a, b = self.P(o["pts"][0]), self.P(o["pts"][1])
                return a, _sub(b, a)
            if t in ("perp", "para"):
                base = self.line_of(self.objs[o["ref"]])
                if base is None:
                    return None
                p = self.P(o["pts"][0])
                d = base[1]
                return p, ((-d[1], d[0]) if t == "perp" else d)
            if t == "perpbis":
                a, b = self.P(o["pts"][0]), self.P(o["pts"][1])
                d = _sub(b, a)
                return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), (-d[1], d[0])
            if t == "bis":
                a, b, c = (self.P(i) for i in o["pts"])
                u, v = _sub(a, b), _sub(c, b)
                lu, lv = math.hypot(*u) or 1, math.hypot(*v) or 1
                d = (u[0] / lu + v[0] / lv, u[1] / lu + v[1] / lv)
                if abs(d[0]) + abs(d[1]) < 1e-9:
                    d = (-u[1], u[0])
                return b, d
            if t == "tangent":
                p = self.P(o["pts"][0])
                ci = self.circle_of(self.objs[o["ref"]])
                if not ci:
                    return None
                c, r = ci
                dx, dy = p[0] - c[0], p[1] - c[1]
                dist = math.hypot(dx, dy)
                if dist < r - 1e-6 or r < 1e-9:
                    return None
                if abs(dist - r) <= 1e-3:
                    return p, (-dy, dx)
                ang = math.atan2(dy, dx)
                alpha = math.acos(max(-1.0, min(1.0, r / dist)))
                sg = 1 if o.get("idx", 0) == 0 else -1
                ta = ang + sg * alpha
                tx, ty = c[0] + r * math.cos(ta), c[1] + r * math.sin(ta)
                return p, (tx - p[0], ty - p[1])
        except (KeyError, IndexError, TypeError):
            return None
        return None

    def circle_of(self, o):
        t = o["type"]
        try:
            if t == "circle":
                c, p = self.P(o["pts"][0]), self.P(o["pts"][1])
                return c, math.hypot(p[0] - c[0], p[1] - c[1])
            if t == "circ3":
                return self._circumcircle(*[self.P(i) for i in o["pts"]])
        except KeyError:
            return None
        return None

    @staticmethod
    def _circumcircle(a, b, c):
        d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
        if abs(d) < 1e-12:
            return None
        ux = ((a[0] ** 2 + a[1] ** 2) * (b[1] - c[1]) + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1]) + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])) / d
        uy = ((a[0] ** 2 + a[1] ** 2) * (c[0] - b[0]) + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0]) + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])) / d
        return (ux, uy), math.hypot(a[0] - ux, a[1] - uy)

    def _intersections(self, o1, o2):
        l1, l2 = self.line_of(o1), self.line_of(o2)
        c1, c2 = self.circle_of(o1), self.circle_of(o2)
        res = []
        if l1 and l2:
            (p, d), (q, e) = l1, l2
            den = d[0] * e[1] - d[1] * e[0]
            if abs(den) > 1e-12:
                t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
                res = [(p[0] + t * d[0], p[1] + t * d[1])]
        elif (l1 and c2) or (c1 and l2):
            (p, d), (c, r) = (l1, c2) if l1 else (l2, c1)
            fx, fy = p[0] - c[0], p[1] - c[1]
            a = d[0] ** 2 + d[1] ** 2
            b = 2 * (fx * d[0] + fy * d[1])
            cc = fx * fx + fy * fy - r * r
            disc = b * b - 4 * a * cc
            if a > 0 and disc >= 0:
                for sg in (1, -1):
                    t = (-b + sg * math.sqrt(disc)) / (2 * a)
                    res.append((p[0] + t * d[0], p[1] + t * d[1]))
        elif c1 and c2:
            (a_, r1), (b_, r2) = c1, c2
            dx, dy = b_[0] - a_[0], b_[1] - a_[1]
            d = math.hypot(dx, dy)
            if d > 1e-12 and abs(r1 - r2) <= d <= r1 + r2:
                x = (d * d + r1 * r1 - r2 * r2) / (2 * d)
                h = math.sqrt(max(r1 * r1 - x * x, 0))
                mx, my = a_[0] + x * dx / d, a_[1] + x * dy / d
                res = [(mx - h * dy / d, my + h * dx / d), (mx + h * dy / d, my - h * dx / d)]
        return res

    def recompute(self):
        for pid in self.order:
            p = self.points.get(pid)
            if not p or p["kind"] == "free":
                continue
            try:
                k, par = p["kind"], p["parents"]
                if k == "mid":
                    a, b = self.P(par[0]), self.P(par[1])
                    p["x"], p["y"] = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                elif k == "sym_pt":
                    a, o = self.P(par[0]), self.P(par[1])
                    p["x"], p["y"] = 2 * o[0] - a[0], 2 * o[1] - a[1]
                elif k == "foot":
                    a, (q, d) = self.P(par[0]), self.line_of(self.objs[par[1]])
                    t = ((a[0] - q[0]) * d[0] + (a[1] - q[1]) * d[1]) / (d[0] ** 2 + d[1] ** 2)
                    p["x"], p["y"] = q[0] + t * d[0], q[1] + t * d[1]
                elif k == "reflect":
                    a, (q, d) = self.P(par[0]), self.line_of(self.objs[par[1]])
                    t = ((a[0] - q[0]) * d[0] + (a[1] - q[1]) * d[1]) / (d[0] ** 2 + d[1] ** 2)
                    fx, fy = q[0] + t * d[0], q[1] + t * d[1]
                    p["x"], p["y"] = 2 * fx - a[0], 2 * fy - a[1]
                elif k == "inter":
                    pts = self._intersections(self.objs[par[0]], self.objs[par[1]])
                    if pts:
                        i = min(p["idx"], len(pts) - 1) if p["idx"] >= 0 else 0
                        p["x"], p["y"] = pts[i]
                        p["hidden"] = False
                    else:
                        p["hidden"] = True
                elif k in ("centroid", "circum", "incenter", "ortho"):
                    a, b, c = (self.P(i) for i in par)
                    if k == "centroid":
                        p["x"], p["y"] = (a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3
                    elif k == "circum":
                        cc = self._circumcircle(a, b, c)
                        if cc:
                            p["x"], p["y"] = cc[0]
                    elif k == "incenter":
                        la, lb, lc = math.hypot(*_sub(b, c)), math.hypot(*_sub(a, c)), math.hypot(*_sub(a, b))
                        s = la + lb + lc or 1
                        p["x"], p["y"] = (la * a[0] + lb * b[0] + lc * c[0]) / s, (la * a[1] + lb * b[1] + lc * c[1]) / s
                    else:
                        g = ((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3)
                        cc = self._circumcircle(a, b, c)
                        if cc:
                            p["x"], p["y"] = (3 * g[0] - 2 * cc[0][0], 3 * g[1] - 2 * cc[0][1])
            except (KeyError, IndexError, TypeError, ZeroDivisionError):
                p["hidden"] = True

    # ------------------------------------------------------------------ tìm đối tượng
    def hit_point(self, pos, r=14):
        best, bd = None, r
        for pid in reversed(self.order):
            p = self.points[pid]
            if p.get("hidden"):
                continue
            sp = self.w2s(p["x"], p["y"])
            d = math.hypot(sp.x() - pos.x(), sp.y() - pos.y())
            if d < bd:
                best, bd = pid, d
        return best

    def hit_obj(self, pos, tol=13):
        wx, wy = self.s2w(pos)
        tw = tol / self.scale
        for i in range(len(self.objs) - 1, -1, -1):
            o = self.objs[i]
            if o["hidden"] or o.get("edge_ref"):
                continue
            t = o["type"]
            ln = self.line_of(o)
            if ln:
                (px, py), (dx, dy) = ln
                dd = dx * dx + dy * dy
                if dd == 0:
                    continue
                s = ((wx - px) * dx + (wy - py) * dy) / dd
                if t in ("seg", "vec"):
                    s = max(0, min(1, s))
                elif t == "ray":
                    s = max(0, s)
                if math.hypot(wx - (px + s * dx), wy - (py + s * dy)) <= tw:
                    return i
            ci = self.circle_of(o)
            if ci and abs(math.hypot(wx - ci[0][0], wy - ci[0][1]) - ci[1]) <= tw:
                return i
            if t == "poly":
                pts = [self.P(k) for k in o["pts"] if k in self.points]
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    dd = dx * dx + dy * dy or 1
                    s = max(0, min(1, ((wx - a[0]) * dx + (wy - a[1]) * dy) / dd))
                    if math.hypot(wx - (a[0] + s * dx), wy - (a[1] + s * dy)) <= tw:
                        return i
            if t == "text" and math.hypot(self.w2s(o["x"], o["y"]).x() - pos.x(), self.w2s(o["x"], o["y"]).y() - pos.y()) < 30:
                return i
            if t == "func":
                y = self._eval_func(o["expr"], wx)
                if y is not None and abs(self.w2s(wx, y).y() - pos.y()) <= tol + 2:
                    return i
        return None

    def hit_construct_target(self, pos, need_circle=False, allow_circle=True, tol=14):
        """Tìm đường thẳng, đoạn thẳng, cạnh đa giác hoặc đường tròn hợp lệ cho công cụ dựng hình.
        Trả về ('o', oi) hoặc ('edge', pid_u, pid_v) hoặc None."""
        wx, wy = self.s2w(pos)
        tw = tol / self.scale
        best, bd = None, tw
        for i in range(len(self.objs) - 1, -1, -1):
            o = self.objs[i]
            if o["hidden"] or o.get("edge_ref"):
                continue
            t = o["type"]
            ci = self.circle_of(o)
            if ci and (need_circle or allow_circle):
                d = abs(math.hypot(wx - ci[0][0], wy - ci[0][1]) - ci[1])
                if d <= bd:
                    best, bd = ("o", i), d
                continue
            if need_circle:
                continue
            ln = self.line_of(o)
            if ln:
                (px, py), (dx, dy) = ln
                dd = dx * dx + dy * dy
                if dd == 0:
                    continue
                s = ((wx - px) * dx + (wy - py) * dy) / dd
                if t in ("seg", "vec"):
                    s = max(0, min(1, s))
                elif t == "ray":
                    s = max(0, s)
                d = math.hypot(wx - (px + s * dx), wy - (py + s * dy))
                if d <= bd:
                    best, bd = ("o", i), d
            elif t == "poly":
                pids = [k for k in o["pts"] if k in self.points]
                for u, v in zip(pids, pids[1:] + pids[:1]):
                    a, b = self.P(u), self.P(v)
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    dd = dx * dx + dy * dy or 1
                    s = max(0, min(1, ((wx - a[0]) * dx + (wy - a[1]) * dy) / dd))
                    d = math.hypot(wx - (a[0] + s * dx), wy - (a[1] + s * dy))
                    if d <= bd:
                        best, bd = ("edge", u, v), d
        return best

    def _ensure_edge_seg(self, u, v):
        """Tái sử dụng hoặc tạo đoạn thẳng tham chiếu cạnh đa giác (u, v) để dựng hình động."""
        for i, o in enumerate(self.objs):
            if not o["hidden"] and o["type"] == "seg" and set(o["pts"]) == {u, v}:
                return i
        return self.add_obj("seg", [u, v], edge_ref=True)

    def _get_func(self, expr):
        if expr not in self._func_cache:
            c = ce.Calc()
            try:
                node = c.parse(expr)
                self._func_cache[expr] = (c, node)
            except ce.CalcError:
                self._func_cache[expr] = None
        return self._func_cache[expr]

    def _eval_func(self, expr, x):
        item = self._get_func(expr)
        if not item:
            return None
        c, node = item
        try:
            y = c.ev(node, {"x": x})
            if isinstance(y, complex) or not math.isfinite(float(y)):
                return None
            return float(y)
        except Exception:
            return None

    def _update_trace(self, pos):
        if self.tool != "select" or self.drag is not None or self.pan_from is not None:
            self.trace_pt = None
            return
        wx, _ = self.s2w(pos)
        best, bd = None, 16.0
        for o in self.objs:
            if o["hidden"] or o["type"] != "func":
                continue
            y = self._eval_func(o["expr"], wx)
            if y is None:
                continue
            sp = self.w2s(wx, y)
            d = abs(sp.y() - pos.y())
            if d < bd:
                best, bd = (wx, y, o["expr"], o["color"]), d
        self.trace_pt = best

    # ------------------------------------------------------------------ chuột & bắt điểm thông minh
    def _snap(self, wx, wy, screen_pos=None):
        """Bắt điểm từ tính mềm vào giao lưới: chỉ hút khi con trỏ ở gần nút lưới (<= 9px),
        còn lại đặt CHÍNH XÁC tại vị trí con trỏ để không bao giờ bị giật lệch."""
        if not self.snap:
            return wx, wy
        half = self._grid_step() / 2.0
        gx, gy = round(wx / half) * half, round(wy / half) * half
        if screen_pos is None:
            screen_pos = self.w2s(wx, wy)
        gs = self.w2s(gx, gy)
        if math.hypot(gs.x() - screen_pos.x(), gs.y() - screen_pos.y()) <= 9.0:
            return gx, gy
        return wx, wy

    def _nearby_geom_items(self, pos, tol=22):
        """Thu thập các đường/đoạn/cạnh đa giác/đường tròn gần con trỏ để tìm giao điểm & bắt điểm trên đường."""
        wx, wy = self.s2w(pos)
        tw = tol / max(self.scale, 1e-6)
        items = []  # (dist, src, obj_dict, proj_pt)
        seen_edges = set()
        for i, o in enumerate(self.objs):
            if o["hidden"] or o.get("edge_ref"):
                continue
            t = o["type"]
            ci = self.circle_of(o)
            if ci:
                (cx, cy), r = ci
                d_c = math.hypot(wx - cx, wy - cy)
                d = abs(d_c - r)
                if d <= tw and d_c > 1e-9:
                    px, py = cx + r * (wx - cx) / d_c, cy + r * (wy - cy) / d_c
                    items.append((d, ("o", i), o, (px, py)))
                continue
            ln = self.line_of(o)
            if ln:
                (qx, qy), (dx, dy) = ln
                dd = dx * dx + dy * dy
                if dd < 1e-12:
                    continue
                s = ((wx - qx) * dx + (wy - qy) * dy) / dd
                if t in ("seg", "vec"):
                    s = max(0.0, min(1.0, s))
                    seen_edges.add(tuple(sorted(o["pts"][:2])))
                elif t == "ray":
                    s = max(0.0, s)
                px, py = qx + s * dx, qy + s * dy
                d = math.hypot(wx - px, wy - py)
                if d <= tw:
                    items.append((d, ("o", i), o, (px, py)))
            elif t == "poly":
                pids = [k for k in o["pts"] if k in self.points]
                for u, v in zip(pids, pids[1:] + pids[:1]):
                    key = (min(u, v), max(u, v))
                    if key in seen_edges:
                        continue
                    seen_edges.add(key)
                    a, b = self.P(u), self.P(v)
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    dd = dx * dx + dy * dy
                    if dd < 1e-12:
                        continue
                    s = max(0.0, min(1.0, ((wx - a[0]) * dx + (wy - a[1]) * dy) / dd))
                    px, py = a[0] + s * dx, a[1] + s * dy
                    d = math.hypot(wx - px, wy - py)
                    if d <= tw:
                        syn = {"type": "seg", "pts": [u, v], "hidden": False}
                        items.append((d, ("edge", u, v), syn, (px, py)))
        items.sort(key=lambda x: x[0])
        return items

    def _resolve_point_target(self, pos, disable_snap=False):
        """Xác định chính xác vị trí đặt điểm (dùng chung cho cả vòng tròn xem trước lẫn lúc nhấp):
        1) Điểm có sẵn -> 2) Giao điểm 2 đường/hình -> 3) Điểm nằm trên đường/cạnh/đường tròn
        -> 4) Bắt từ tính mềm vào nút lưới (<= 9px) -> 5) Đúng vị trí con trỏ."""
        pid = self.hit_point(pos, r=14)
        if pid is not None:
            p = self.points[pid]
            return {"kind": "point", "pid": pid, "wx": p["x"], "wy": p["y"], "label": p["label"]}

        wx, wy = self.s2w(pos)
        if not disable_snap:
            near = self._nearby_geom_items(pos, tol=22)
            # Ưu tiên 2: Tự động phát hiện giao điểm của 2 đường/cạnh/đường tròn gần con trỏ
            if len(near) >= 2:
                best_inter, best_d = None, 15.0
                lim = min(len(near), 8)
                for a_i in range(lim):
                    for b_i in range(a_i + 1, lim):
                        _, src1, o1, _ = near[a_i]
                        _, src2, o2, _ = near[b_i]
                        pts = self._intersections(o1, o2)
                        for idx_k, (ix, iy) in enumerate(pts):
                            sp = self.w2s(ix, iy)
                            d_px = math.hypot(sp.x() - pos.x(), sp.y() - pos.y())
                            if d_px < best_d:
                                best_d = d_px
                                best_inter = {
                                    "kind": "inter", "wx": ix, "wy": iy,
                                    "src1": src1, "src2": src2, "idx": idx_k, "label": "Giao điểm",
                                }
                if best_inter is not None:
                    return best_inter

            # Ưu tiên 3: Bắt chính xác lên đường thẳng / đoạn / cạnh đa giác / đường tròn (trong 10px)
            if near:
                d_w, _, _, (px, py) = near[0]
                if d_w * self.scale <= 10.0:
                    return {"kind": "on_obj", "wx": px, "wy": py, "label": ""}

            # Ưu tiên 4: Bắt từ tính mềm vào nút lưới (chỉ khi thực sự gần nút lưới <= 9px)
            if self.snap:
                half = self._grid_step() / 2.0
                gx, gy = round(wx / half) * half, round(wy / half) * half
                gs = self.w2s(gx, gy)
                if math.hypot(gs.x() - pos.x(), gs.y() - pos.y()) <= 9.0:
                    return {"kind": "grid", "wx": gx, "wy": gy, "label": ""}

        return {"kind": "free", "wx": wx, "wy": wy, "label": ""}

    def hit_label(self, pos):
        """Kiểm tra chuột có đang trúng nhãn điểm / nhãn góc / số đo / chú thích để kéo di chuyển không."""
        for r, tgt in reversed(self._label_rects):
            if r.adjusted(-3, -2, 3, 2).contains(pos):
                return tgt
        return None

    def mousePressEvent(self, e):
        self.setFocus()
        pos = e.position()
        self.mouse_pos = pos
        if e.button() == Qt.MiddleButton:
            self.pan_from = (pos, QPointF(self.origin))
            return
        if e.button() == Qt.RightButton:
            return
        t = self.tool
        if t == "select":
            pid = self.hit_point(pos)
            if pid is not None:
                self.sel = ("p", pid)
                self.push_undo()
                self.drag = pid if self.points[pid]["kind"] == "free" else None
                self.info_changed.emit(self._describe())
            else:
                ltgt = self.hit_label(pos)
                if ltgt is not None:
                    self.push_undo()
                    kind, idx_ = ltgt
                    if kind == "pt_lbl":
                        p_ = self.points[idx_]
                        self.sel = ("p", idx_)
                        self.drag_lbl = (ltgt, pos, p_.get("lx", 8.0), p_.get("ly", -7.0))
                    elif kind == "obj_lbl":
                        o_ = self.objs[idx_]
                        self.sel = ("o", idx_)
                        self.drag_lbl = (ltgt, pos, o_.get("lx", 0.0), o_.get("ly", 0.0))
                    elif kind == "text_obj":
                        o_ = self.objs[idx_]
                        self.sel = ("o", idx_)
                        self.drag_lbl = (ltgt, pos, o_["x"], o_["y"])
                    self.setCursor(Qt.ClosedHandCursor)
                    self.info_changed.emit("Đang kéo vị trí nhãn / chú thích — thả chuột để cố định")
                else:
                    oi = self.hit_obj(pos)
                    self.sel = ("o", oi) if oi is not None else None
                    self.info_changed.emit(self._describe())
                    if oi is None:
                        self.pan_from = (pos, QPointF(self.origin))
            self.update()
            return
        if t == "erase":
            pid = self.hit_point(pos)
            if pid is not None:
                self.push_undo()
                self.delete_point(pid)
            else:
                oi = self.hit_obj(pos)
                if oi is not None:
                    self.push_undo()
                    self.delete_obj(oi)
            self.update()
            return
        if t == "text":
            txt, ok = QInputDialog.getText(self, "Chú thích", "Nội dung:")
            if ok and txt:
                self.push_undo()
                wx, wy = self.s2w(pos)
                self.add_obj("text", x=wx, y=wy, text=txt, color=self.cur_color)
            self.update()
            return
        self._construct_click(pos, disable_snap=bool(e.modifiers() & Qt.ControlModifier))

    def _pick_point(self, pos, disable_snap=False):
        st = self._resolve_point_target(pos, disable_snap=disable_snap)
        if st["kind"] == "point":
            return st["pid"]
        if st["kind"] == "inter":
            s1, s2 = st["src1"], st["src2"]
            oi1 = s1[1] if s1[0] == "o" else self._ensure_edge_seg(s1[1], s1[2])
            oi2 = s2[1] if s2[0] == "o" else self._ensure_edge_seg(s2[1], s2[2])
            return self.add_point(st["wx"], st["wy"], "inter", [oi1, oi2], idx=st["idx"])
        return self.add_point(st["wx"], st["wy"])

    def _construct_click(self, pos, disable_snap=False):
        spec = TOOLS[self.tool][1]
        need = self._next_need()
        if need is None:
            self.pending = []
            return
        self._warn_msg = ""
        need_circle = (self.tool == "tangent")
        allow_circle = (self.tool in ("tangent", "inter"))

        if need == "PO":
            # Cho phép nhấp Điểm trước HOẶC Đường/Đoạn/Cạnh/Đường tròn trước đều được!
            pid = self.hit_point(pos)
            if pid is not None:
                self.push_undo()
                self.pending.append(("p", pid))
            else:
                tgt = self.hit_construct_target(pos, need_circle=need_circle, allow_circle=allow_circle)
                if tgt is not None:
                    self.push_undo()
                    oi = tgt[1] if tgt[0] == "o" else self._ensure_edge_seg(tgt[1], tgt[2])
                    self.pending.append(("o", oi))
                else:
                    self.push_undo()
                    pid = self._pick_point(pos, disable_snap=disable_snap)
                    self.pending.append(("p", pid))
        elif need == "P":
            if self.tool == "poly" and len(self.pending) >= 3:
                pid = self.hit_point(pos)
                if pid == self.pending[0][1]:
                    self._finish_poly()
                    return
            self.push_undo()
            pid = self._pick_point(pos, disable_snap=disable_snap)
            self.pending.append(("p", pid))
        else:  # need == "O"
            tgt = self.hit_construct_target(pos, need_circle=need_circle, allow_circle=allow_circle)
            if tgt is None:
                if need_circle:
                    msg = "Chưa trúng đường tròn — hãy nhấp lên viền đường tròn đã vẽ."
                elif self.tool == "inter":
                    msg = "Hãy nhấp lên đoạn, đường thẳng, cạnh đa giác hoặc đường tròn."
                else:
                    msg = "Chưa trúng đường — hãy nhấp lên đoạn/đường thẳng hoặc cạnh đa giác đã vẽ."
                self._warn_msg = msg
                self.status.emit(msg)
                self.update()
                return
            self.push_undo()
            oi = tgt[1] if tgt[0] == "o" else self._ensure_edge_seg(tgt[1], tgt[2])
            self.pending.append(("o", oi))

        if spec[0] != "*" and len(self.pending) == len(spec):
            self._finish_construct()
        else:
            self.status.emit(self._step_prompt())
        self.snap_target = None
        self.update()

    def _finish_poly(self):
        pts = [i for k, i in self.pending]
        self.add_obj("poly", pts)
        self.pending = []
        self._warn_msg = ""
        self.status.emit("Đã tạo đa giác.")
        self.update()

    def _finish_construct(self):
        t = self.tool
        raw_pend = list(self.pending)
        self.pending = []
        self._warn_msg = ""
        # Chuẩn hóa thứ tự (P, O) nếu người dùng nhấp Đường trước Điểm sau
        if TOOLS[t][1] == ("P", "O") and len(raw_pend) == 2 and raw_pend[0][0] == "o":
            raw_pend = [raw_pend[1], raw_pend[0]]
        pend = [i for _, i in raw_pend]
        if t in ("seg", "line", "ray", "vec", "circle", "circ3", "angle", "perpbis", "bis"):
            if len(set(pend)) == len(pend) or t == "angle":
                self.add_obj(t, pend)
        elif t in ("mid", "sym_pt"):
            self.add_point(0, 0, t, pend)
        elif t in ("centroid", "circum", "incenter", "ortho"):
            self.add_point(0, 0, t, pend)
        elif t in ("perp", "para"):
            self.add_obj(t, [pend[0]], ref=pend[1])
        elif t in ("foot", "reflect"):
            self.add_point(0, 0, t, pend)
        elif t == "tangent":
            self.add_obj("tangent", [pend[0]], ref=pend[1], idx=0)
            self.add_obj("tangent", [pend[0]], ref=pend[1], idx=1)
        elif t == "inter":
            n = len(self._intersections(self.objs[pend[0]], self.objs[pend[1]]))
            for k in range(max(1, min(n, 2))):
                self.add_point(0, 0, "inter", pend, idx=k)
        self.recompute()
        self.status.emit(f"Đã dựng: {TOOLS[t][0]}")
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        self.mouse_pos = pos
        if self.pan_from:
            d = pos - self.pan_from[0]
            self.origin = self.pan_from[1] + d
            self.snap_target = None
        elif self.drag_lbl is not None and (e.buttons() & Qt.LeftButton):
            ltgt, start_pos, ox, oy = self.drag_lbl
            kind, idx_ = ltgt
            dx, dy = pos.x() - start_pos.x(), pos.y() - start_pos.y()
            if kind == "pt_lbl" and idx_ in self.points:
                self.points[idx_]["lx"] = ox + dx
                self.points[idx_]["ly"] = oy + dy
            elif kind == "obj_lbl" and 0 <= idx_ < len(self.objs):
                self.objs[idx_]["lx"] = ox + dx
                self.objs[idx_]["ly"] = oy + dy
            elif kind == "text_obj" and 0 <= idx_ < len(self.objs):
                self.objs[idx_]["x"] = ox + dx / self.scale
                self.objs[idx_]["y"] = oy - dy / self.scale
            self.snap_target = None
        elif self.drag is not None and (e.buttons() & Qt.LeftButton):
            wx, wy = self._snap(*self.s2w(pos), pos) if (e.modifiers() & Qt.ControlModifier) == 0 and self.snap else self.s2w(pos)
            self.points[self.drag]["x"], self.points[self.drag]["y"] = wx, wy
            self.snap_target = None
            self.recompute()
            self.info_changed.emit(self._describe())
        else:
            need = self._next_need() if self.tool != "select" else None
            pid = self.hit_point(pos)
            self.hover_lbl = None
            if pid is not None and need != "O":
                self.hover = ("p", pid)
            elif self.tool == "select":
                ltgt = self.hit_label(pos)
                if ltgt is not None:
                    self.hover_lbl = ltgt
                    self.hover = None
                    self.setCursor(Qt.OpenHandCursor)
                else:
                    oi = self.hit_obj(pos)
                    self.hover = ("o", oi) if oi is not None else None
                    self.setCursor(Qt.ArrowCursor)
            elif need in ("O", "PO"):
                tgt = self.hit_construct_target(pos, need_circle=(self.tool == "tangent"), allow_circle=(self.tool in ("tangent", "inter")))
                self.hover = tgt
            else:
                oi = self.hit_obj(pos)
                self.hover = ("o", oi) if oi is not None else None
            if need == "P" or (need == "PO" and self.hover is None):
                self.snap_target = self._resolve_point_target(pos, disable_snap=bool(e.modifiers() & Qt.ControlModifier))
            else:
                self.snap_target = None
            self._update_trace(pos)
        self.update()

    def leaveEvent(self, e):
        self.snap_target = None
        self.hover = None
        self.hover_lbl = None
        self.update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        was_lbl = self.drag_lbl is not None
        self.drag = None
        self.drag_lbl = None
        self.pan_from = None
        if was_lbl:
            self.setCursor(Qt.OpenHandCursor if self.hit_label(e.position()) else Qt.ArrowCursor)
            self.info_changed.emit(self._describe())

    def mouseDoubleClickEvent(self, e):
        if self.tool == "poly" and len(self.pending) >= 3:
            self._finish_poly()
            return
        pos = e.position()
        pid = self.hit_point(pos)
        if pid is not None:
            self.rename_point(pid)
            return
        ltgt = self.hit_label(pos)
        if ltgt is not None:
            kind, idx_ = ltgt
            if kind == "pt_lbl" and idx_ in self.points:
                self.rename_point(idx_)
            elif kind == "text_obj" and 0 <= idx_ < len(self.objs):
                o = self.objs[idx_]
                txt, ok = QInputDialog.getText(self, "Sửa chú thích", "Nội dung:", text=o.get("text", ""))
                if ok and txt:
                    self.push_undo()
                    o["text"] = txt
                    self.update()
            elif kind == "obj_lbl" and 0 <= idx_ < len(self.objs):
                o = self.objs[idx_]
                txt, ok = QInputDialog.getText(self, "Nhãn đối tượng", "Nhãn (để trống để hiện số đo mặc định):", text=o.get("label", ""))
                if ok:
                    self.push_undo()
                    o["label"] = txt
                    self.update()

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        pos = e.position()
        wx, wy = self.s2w(pos)
        self.scale = max(0.5, min(600.0, self.scale * f))
        self.origin = QPointF(pos.x() - wx * self.scale, pos.y() + wy * self.scale)
        self.update()

    def keyPressEvent(self, e):
        k, mod = e.key(), e.modifiers()
        if k in (Qt.Key_Return, Qt.Key_Enter) and self.tool == "poly" and len(self.pending) >= 3:
            self._finish_poly()
        elif k == Qt.Key_Escape:
            self.pending = []
            self.set_tool("select")
        elif k in (Qt.Key_Delete, Qt.Key_Backspace) and self.sel:
            self.push_undo()
            if self.sel[0] == "p":
                self.delete_point(self.sel[1])
            else:
                self.delete_obj(self.sel[1])
            self.sel = None
            self.update()
        elif k == Qt.Key_Z and (mod & Qt.ControlModifier):
            if mod & Qt.ShiftModifier:
                self.redo()
            else:
                self.undo()
        elif k == Qt.Key_Y and (mod & Qt.ControlModifier):
            self.redo()
        elif not (mod & (Qt.ControlModifier | Qt.AltModifier)):
            sc = {
                Qt.Key_V: "select", Qt.Key_P: "point", Qt.Key_S: "seg", Qt.Key_L: "line",
                Qt.Key_C: "circle", Qt.Key_G: "poly", Qt.Key_A: "angle", Qt.Key_E: "erase",
            }
            if k in sc:
                self.set_tool(sc[k])
            elif k == Qt.Key_F:
                self.fit_view()
            elif k == Qt.Key_0:
                self.center_origin()
            elif k in (Qt.Key_Plus, Qt.Key_Equal):
                self.zoom_by(1.18)
            elif k == Qt.Key_Minus:
                self.zoom_by(1 / 1.18)

    def contextMenuEvent(self, e):
        pos = QPointF(e.pos())
        pid = self.hit_point(pos)
        oi = None
        if pid is None:
            ltgt = self.hit_label(pos)
            if ltgt is not None:
                if ltgt[0] == "pt_lbl":
                    pid = ltgt[1]
                else:
                    oi = ltgt[1]
        if pid is None and oi is None:
            oi = self.hit_obj(pos)
        m = QMenu(self)
        if pid is not None:
            a1 = m.addAction("Đổi tên điểm…")
            a2 = m.addAction("Đổi màu…")
            a3 = m.addAction("Ẩn/hiện điểm")
            a_rst = m.addAction("Đặt lại vị trí nhãn")
            m.addSeparator()
            a4 = m.addAction("Xóa điểm")
            act = m.exec(e.globalPos())
            if act == a1:
                self.rename_point(pid)
            elif act == a2:
                c = QColorDialog.getColor(QColor(self.points[pid]["color"] or self.fg), self)
                if c.isValid():
                    self.push_undo()
                    self.points[pid]["color"] = c.name()
            elif act == a3:
                self.push_undo()
                self.points[pid]["hidden"] = not self.points[pid]["hidden"]
            elif act == a_rst:
                self.push_undo()
                self.points[pid].pop("lx", None)
                self.points[pid].pop("ly", None)
            elif act == a4:
                self.push_undo()
                self.delete_point(pid)
        elif oi is not None:
            o = self.objs[oi]
            a_txt = m.addAction("Sửa nội dung chú thích…") if o["type"] == "text" else None
            a1 = m.addAction("Đổi màu…")
            a2 = m.addAction("Nét đứt / nét liền") if o["type"] != "text" else None
            a3 = m.addAction("Đặt tên / nhãn…") if o["type"] != "text" else None
            a4 = m.addAction("Độ dày nét…") if o["type"] != "text" else None
            a_rst = m.addAction("Đặt lại vị trí nhãn") if o["type"] != "text" else None
            m.addSeparator()
            a5 = m.addAction("Xóa")
            act = m.exec(e.globalPos())
            if a_txt and act == a_txt:
                txt, ok = QInputDialog.getText(self, "Sửa chú thích", "Nội dung:", text=o.get("text", ""))
                if ok and txt:
                    self.push_undo()
                    o["text"] = txt
            elif act == a1:
                c = QColorDialog.getColor(QColor(o["color"]), self)
                if c.isValid():
                    self.push_undo()
                    o["color"] = c.name()
                    self.objs_changed.emit()
            elif a2 and act == a2:
                self.push_undo()
                o["dashed"] = not o["dashed"]
            elif a3 and act == a3:
                txt, ok = QInputDialog.getText(self, "Nhãn", "Nhãn hiển thị:", text=o["label"])
                if ok:
                    self.push_undo()
                    o["label"] = txt
            elif a4 and act == a4:
                w, ok = QInputDialog.getDouble(self, "Độ dày", "Độ dày nét (px):", o["width"], 0.5, 10, 1)
                if ok:
                    self.push_undo()
                    o["width"] = w
            elif a_rst and act == a_rst:
                self.push_undo()
                o.pop("lx", None)
                o.pop("ly", None)
            elif act == a5:
                self.push_undo()
                self.delete_obj(oi)
        else:
            m.addAction("Vừa khít hình (F)").triggered.connect(self.fit_view)
            m.addAction("Về gốc tọa độ O (0)").triggered.connect(self.center_origin)
            m.addSeparator()
            m.addAction("Bật/tắt lưới").triggered.connect(lambda: (setattr(self, "show_grid", not self.show_grid), self.update()))
            m.addAction("Bật/tắt trục tọa độ").triggered.connect(lambda: (setattr(self, "show_axes", not self.show_axes), self.update()))
            m.exec(e.globalPos())
        self.update()

    def rename_point(self, pid):
        txt, ok = QInputDialog.getText(self, "Đổi tên điểm", "Tên mới:", text=self.points[pid]["label"])
        if ok and txt.strip():
            self.push_undo()
            self.points[pid]["label"] = txt.strip()
            self.update()

    def delete_point(self, pid):
        dead = {pid}
        changed = True
        while changed:
            changed = False
            for q in self.points.values():
                if q["id"] not in dead and q["kind"] != "free" and any(x in dead for x in q["parents"] if isinstance(x, int) and q["kind"] not in ("foot", "reflect", "inter")):
                    dead.add(q["id"])
                    changed = True
        kill = {i for i, o in enumerate(self.objs) if any(p in dead for p in o["pts"])}
        self._remove_objs(kill)
        for d in dead:
            self.points.pop(d, None)
            if d in self.order:
                self.order.remove(d)
        self.recompute()
        self.objs_changed.emit()

    def delete_obj(self, oi):
        self._remove_objs({oi})
        self.recompute()
        self.objs_changed.emit()

    def _remove_objs(self, idxs):
        if not idxs:
            return
        more = True
        while more:
            more = False
            for i, o in enumerate(self.objs):
                if i not in idxs and o.get("ref") in idxs:
                    idxs.add(i)
                    more = True
        for pid, p in list(self.points.items()):
            if (p["kind"] in ("foot", "reflect") and p["parents"][1] in idxs) or (p["kind"] == "inter" and any(x in idxs for x in p["parents"])):
                self.points.pop(pid)
                self.order.remove(pid)
        remap, new = {}, []
        for i, o in enumerate(self.objs):
            if i not in idxs:
                remap[i] = len(new)
                new.append(o)
        for o in new:
            if o.get("ref") is not None:
                o["ref"] = remap.get(o["ref"])
        for p in self.points.values():
            if p["kind"] in ("foot", "reflect"):
                p["parents"][1] = remap.get(p["parents"][1], 0)
            elif p["kind"] == "inter":
                p["parents"] = [remap.get(x, 0) for x in p["parents"]]
        self.objs = new

    # ------------------------------------------------------------------ mô tả
    def _describe_item(self, target):
        if not target:
            return ""
        if target[0] == "p":
            p = self.points.get(target[1])
            return f"Điểm {p['label']} ({p['x']:.3f}; {p['y']:.3f})" if p else ""
        if target[1] >= len(self.objs):
            return ""
        o = self.objs[target[1]]
        t = o["type"]
        try:
            if t == "func":
                return f"Đồ thị: y = {o['expr']}"
            if t == "seg":
                a, b = self.P(o["pts"][0]), self.P(o["pts"][1])
                return f"Đoạn {self.points[o['pts'][0]]['label']}{self.points[o['pts'][1]]['label']} = {math.hypot(*_sub(a, b)):.4f}"
            if t == "poly":
                pts = [self.P(k) for k in o["pts"]]
                return f"Đa giác {''.join(self.points[k]['label'] for k in o['pts'])}: S = {self._area(pts):.4f}, P = {self._perimeter(pts):.4f}"
            if t == "angle":
                return f"Góc = {self._angle_deg(*[self.P(k) for k in o['pts']]):.3f}°"
            ci = self.circle_of(o)
            if ci:
                return f"Đường tròn tâm ({ci[0][0]:.3f}; {ci[0][1]:.3f}), R = {ci[1]:.4f}, S = {math.pi * ci[1] ** 2:.4f}, C = {2 * math.pi * ci[1]:.4f}"
            ln = self.line_of(o)
            if ln:
                (px, py), (dx, dy) = ln
                a_, b_, c_ = dy, -dx, dx * py - dy * px
                parts = []
                for coef, var in ((a_, "x"), (b_, "y"), (c_, "")):
                    if abs(coef) < 1e-12:
                        continue
                    tt = f"{abs(coef):.4g}" + var if not (var and abs(abs(coef) - 1) < 1e-12) else var
                    parts.append(("− " if coef < 0 else ("+ " if parts else "")) + tt)
                return "Đường thẳng: " + " ".join(parts) + " = 0"
        except KeyError:
            return ""
        return ""

    def _describe(self):
        return self._describe_item(self.sel)

    @staticmethod
    def _area(pts):
        return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2

    @staticmethod
    def _perimeter(pts):
        return sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pts, pts[1:] + pts[:1]))

    @staticmethod
    def _angle_deg(a, b, c):
        u, v = _sub(a, b), _sub(c, b)
        lu, lv = math.hypot(*u), math.hypot(*v)
        if lu * lv == 0:
            return 0.0
        return math.degrees(math.acos(max(-1, min(1, (u[0] * v[0] + u[1] * v[1]) / (lu * lv)))))

    def summary_text(self):
        out = []
        for i in range(len(self.objs)):
            d = self._describe_item(("o", i))
            if d:
                out.append(d)
        return "\n".join(out)

    # ------------------------------------------------------------------ hình mẫu 2D & 3D
    def add_figure(self, name):
        self.push_undo()
        # Đặt hình vào giữa khung nhìn hiện tại
        cx, cy = self.s2w(QPointF(self.width() * 0.5, self.height() * 0.5))
        figs = {
            "Tam giác thường": ([("A", -3, -2), ("B", 3, -2), ("C", -1, 2.5)], [("poly", "ABC")]),
            "Tam giác vuông": ([("A", -3, -2), ("B", 3, -2), ("C", -3, 2)], [("poly", "ABC"), ("angle", "CAB")]),
            "Tam giác cân": ([("A", -2.5, -2), ("B", 2.5, -2), ("C", 0, 2.8)], [("poly", "ABC")]),
            "Tam giác đều": ([("A", -2.5, -1.8), ("B", 2.5, -1.8), ("C", 0, 2.53)], [("poly", "ABC")]),
            "Tam giác + Đường tròn ngoại tiếp": ([("A", -3, -1.8), ("B", 3, -1.8), ("C", -0.5, 2.6)], [("poly", "ABC"), ("circ3", "ABC")]),
            "Tam giác + Đường tròn nội tiếp": ([("A", -3, -2), ("B", 3, -2), ("C", -0.4, 2.6)], [("poly", "ABC"), ("incirc", "ABC")]),
            "Tam giác + 3 đường cao (Trực tâm)": ([("A", -3, -2), ("B", 3, -2), ("C", -0.8, 2.6)], [("poly", "ABC"), ("ortho_demo", "ABC")]),
            "Hình chữ nhật": ([("A", -3, -1.8), ("B", 3, -1.8), ("C", 3, 1.8), ("D", -3, 1.8)], [("poly", "ABCD")]),
            "Hình vuông": ([("A", -2, -2), ("B", 2, -2), ("C", 2, 2), ("D", -2, 2)], [("poly", "ABCD")]),
            "Hình bình hành": ([("A", -3.5, -1.8), ("B", 2.5, -1.8), ("C", 4.5, 1.8), ("D", -1.5, 1.8)], [("poly", "ABCD")]),
            "Hình bình hành + Hai đường chéo": ([("A", -3.5, -1.8), ("B", 2.5, -1.8), ("C", 4.5, 1.8), ("D", -1.5, 1.8)], [("poly", "ABCD"), ("dseg", "AC"), ("dseg", "BD")]),
            "Hình thang": ([("A", -3.5, -1.8), ("B", 3.5, -1.8), ("C", 1.5, 1.8), ("D", -1.5, 1.8)], [("poly", "ABCD")]),
            "Hình thang cân": ([("A", -3.5, -1.8), ("B", 3.5, -1.8), ("C", 2, 1.8), ("D", -2, 1.8)], [("poly", "ABCD")]),
            "Hình thang vuông": ([("A", -3, -1.8), ("B", 3.5, -1.8), ("C", 1.2, 1.8), ("D", -3, 1.8)], [("poly", "ABCD"), ("angle", "DAB")]),
            "Hình thoi": ([("A", -3, 0), ("B", 0, -2), ("C", 3, 0), ("D", 0, 2)], [("poly", "ABCD")]),
            "Hình thoi + Hai đường chéo": ([("A", -3, 0), ("B", 0, -2), ("C", 3, 0), ("D", 0, 2)], [("poly", "ABCD"), ("dseg", "AC"), ("dseg", "BD")]),
            "Ngũ giác đều": ([(chr(65 + k), 2.8 * math.cos(math.pi / 2 + 2 * math.pi * k / 5), 2.8 * math.sin(math.pi / 2 + 2 * math.pi * k / 5)) for k in range(5)], [("poly", "ABCDE")]),
            "Lục giác đều": ([(chr(65 + k), 2.8 * math.cos(2 * math.pi * k / 6), 2.8 * math.sin(2 * math.pi * k / 6)) for k in range(6)], [("poly", "ABCDEF")]),
            "Tứ diện đều S.ABC": ([("A", -2.6, -2.0), ("B", 2.4, -2.0), ("C", 0.2, -0.3), ("S", 0.0, 2.8)],
                                  [("seg", "AB"), ("seg", "BC"), ("seg", "SA"), ("seg", "SB"), ("seg", "SC"), ("dseg", "AC")]),
            "Hình chóp tam giác S.ABC": ([("A", -2.5, -2.2), ("B", 2.5, -2.2), ("C", -0.3, -0.3), ("S", 0.1, 2.8)],
                                          [("seg", "AB"), ("seg", "BC"), ("seg", "SA"), ("seg", "SB"), ("seg", "SC"), ("dseg", "AC")]),
            "Hình chóp tứ giác S.ABCD": ([("A", -3.2, -2.2), ("B", 1.8, -2.2), ("C", 4.0, -0.3), ("D", -1.0, -0.3), ("S", 0.4, 3.2)],
                                          [("seg", "AB"), ("seg", "BC"), ("seg", "SA"), ("seg", "SB"), ("seg", "SC"), ("dseg", "CD"), ("dseg", "DA"), ("dseg", "SD")]),
            "Hình chóp cụt tứ giác": ([("A", -3.2, -2.2), ("B", 2.2, -2.2), ("C", 4.0, -0.5), ("D", -1.4, -0.5),
                                       ("A'", -1.8, 1.8), ("B'", 1.4, 1.8), ("C'", 2.5, 2.8), ("D'", -0.7, 2.8)],
                                      [("seg", "AB"), ("seg", "BC"), ("dseg", "CD"), ("dseg", "DA"),
                                       ("seg", "A'B'"), ("seg", "B'C'"), ("seg", "C'D'"), ("seg", "D'A'"),
                                       ("seg", "AA'"), ("seg", "BB'"), ("seg", "CC'"), ("dseg", "DD'")]),
            "Hình lăng trụ tam giác ABC.A'B'C'": ([("A", -2.5, -2.6), ("B", 2.5, -2.6), ("C", -0.3, -0.7), ("A'", -1.9, 1.6), ("B'", 3.1, 1.6), ("C'", 0.3, 3.5)],
                                                  [("seg", "AB"), ("seg", "BC"), ("dseg", "AC"), ("seg", "AA'"), ("seg", "BB'"), ("seg", "CC'"), ("seg", "A'B'"), ("seg", "B'C'"), ("seg", "A'C'")]),
            "Lăng trụ đứng tứ giác ABCD.A'B'C'D'": ([("A", -3.0, -2.4), ("B", 1.6, -2.4), ("C", 3.6, -0.6), ("D", -1.4, -0.4),
                                                      ("A'", -3.0, 1.6), ("B'", 1.6, 1.6), ("C'", 3.6, 3.4), ("D'", -1.4, 3.6)],
                                                     [("seg", "AB"), ("seg", "BC"), ("dseg", "CD"), ("dseg", "DA"), ("seg", "A'B'"), ("seg", "B'C'"), ("seg", "C'D'"), ("seg", "D'A'"),
                                                      ("seg", "AA'"), ("seg", "BB'"), ("seg", "CC'"), ("dseg", "DD'")]),
            "Hình hộp chữ nhật ABCD.A'B'C'D'": ([("A", -3.2, -2.4), ("B", 1.8, -2.4), ("C", 4.0, -0.5), ("D", -1.0, -0.5),
                                                  ("A'", -3.2, 1.1), ("B'", 1.8, 1.1), ("C'", 4.0, 3.0), ("D'", -1.0, 3.0)],
                                                 [("seg", "AB"), ("seg", "BC"), ("dseg", "CD"), ("dseg", "DA"), ("seg", "A'B'"), ("seg", "B'C'"), ("seg", "C'D'"), ("seg", "D'A'"),
                                                  ("seg", "AA'"), ("seg", "BB'"), ("seg", "CC'"), ("dseg", "DD'")]),
            "Hình lập phương ABCD.A'B'C'D'": ([("A", -2.8, -2.4), ("B", 1.2, -2.4), ("C", 3.2, -0.8), ("D", -0.8, -0.8),
                                               ("A'", -2.8, 1.6), ("B'", 1.2, 1.6), ("C'", 3.2, 3.2), ("D'", -0.8, 3.2)],
                                              [("seg", "AB"), ("seg", "BC"), ("dseg", "CD"), ("dseg", "DA"), ("seg", "A'B'"), ("seg", "B'C'"), ("seg", "C'D'"), ("seg", "D'A'"),
                                               ("seg", "AA'"), ("seg", "BB'"), ("seg", "CC'"), ("dseg", "DD'")]),
            "Hình trụ (mô phỏng 3D)": ([("O", 0, -2.2), ("O'", 0, 2.2), ("A", -2.2, -2.2), ("B", 2.2, -2.2), ("A'", -2.2, 2.2), ("B'", 2.2, 2.2)],
                                        [("seg", "AA'"), ("seg", "BB'"), ("dseg", "OO'"), ("dseg", "AB"), ("seg", "A'B'")]),
            "Hình nón (mô phỏng 3D)": ([("O", 0, -2.2), ("S", 0, 2.6), ("A", -2.4, -2.2), ("B", 2.4, -2.2)],
                                        [("seg", "SA"), ("seg", "SB"), ("dseg", "SO"), ("dseg", "AB")]),
        }
        if name not in figs:
            return
        pts, segs = figs[name]
        ids = {}
        for lab, x, y in pts:
            ids[lab] = self.add_point(round((x + cx) * 2) / 2, round((y + cy) * 2) / 2, label=self._unique(lab))

        def split(s):
            out, i = [], 0
            while i < len(s):
                out.append(s[i:i + 2] if i + 1 < len(s) and s[i + 1] == "'" else s[i])
                i += 2 if i + 1 < len(s) and s[i + 1] == "'" else 1
            return out

        for kind, lab in segs:
            names = split(lab)
            if kind == "poly":
                self.add_obj("poly", [ids[n] for n in names])
            elif kind == "circ3":
                self.add_obj("circ3", [ids[n] for n in names], color="#0D9488")
                self.add_point(0, 0, "circum", [ids[n] for n in names], label=self._unique("O"))
            elif kind == "incirc":
                a, b, c = [ids[n] for n in names]
                i_id = self.add_point(0, 0, "incenter", [a, b, c], label=self._unique("I"))
                s_ab = self.add_obj("seg", [a, b], hidden=False)
                f_ab = self.add_point(0, 0, "foot", [i_id, s_ab], label=self._unique("H"))
                self.add_obj("circle", [i_id, f_ab], color="#0D9488")
            elif kind == "angle":
                self.add_obj("angle", [ids[n] for n in names], color="#D97706")
            elif kind == "ortho_demo":
                a, b, c = [ids[n] for n in names]
                h_id = self.add_point(0, 0, "ortho", [a, b, c], label=self._unique("H"))
                s_bc = self.add_obj("seg", [b, c], hidden=False)
                s_ac = self.add_obj("seg", [a, c], hidden=False)
                s_ab = self.add_obj("seg", [a, b], hidden=False)
                f1 = self.add_point(0, 0, "foot", [a, s_bc], label=self._unique("D"))
                f2 = self.add_point(0, 0, "foot", [b, s_ac], label=self._unique("E"))
                f3 = self.add_point(0, 0, "foot", [c, s_ab], label=self._unique("F"))
                for u, v in ((a, f1), (b, f2), (c, f3)):
                    self.add_obj("seg", [u, v], dashed=True, color="#E11D48")
            else:
                a, b = names
                self.add_obj("seg", [ids[a], ids[b]], dashed=(kind == "dseg"))
        self.recompute()
        self.update()

    def _unique(self, lab):
        used = {p["label"] for p in self.points.values()}
        if lab not in used:
            return lab
        k = 1
        while f"{lab}{k}" in used:
            k += 1
        return f"{lab}{k}"

    def add_function(self, expr, color=None):
        c = ce.Calc()
        try:
            node = c.parse(expr)
            c.ev(node, {"x": 1.0})
        except ce.CalcError as exc:
            if "chưa có giá trị" not in str(exc):
                raise
        self.push_undo()
        if not color:
            color = FUNC_COLORS[self._func_color_idx % len(FUNC_COLORS)]
            self._func_color_idx += 1
        self.add_obj("func", expr=expr, color=color, width=2.3)
        self.update()

    # ------------------------------------------------------------------ vẽ
    def resizeEvent(self, e):
        if not self._init_origin:
            self.origin = QPointF(self.width() * 0.5, self.height() * 0.5)
            self._init_origin = True
        super().resizeEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        self._draw(p, QRectF(self.rect()), True)

    def _draw(self, p, rect, interactive):
        if interactive:
            self._label_rects = []
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.fillRect(rect, self.bg)
        W, H = rect.width(), rect.height()
        grid_c = QColor(self.grid_hex)
        axis_c = QColor("#64748B")

        # Thuật toán bước lưới 1-2-5 ổn định từ thu phóng 1% (±1000) đến 1250% (±0.05)
        step = self._grid_step()

        x0, x1 = self.s2w(QPointF(0, 0))[0], self.s2w(QPointF(W, 0))[0]
        y1, y0 = self.s2w(QPointF(0, 0))[1], self.s2w(QPointF(0, H))[1]

        if self.show_grid:
            p.setPen(QPen(grid_c, 1))
            k_min = math.floor(x0 / step)
            k_max = min(math.ceil(x1 / step), k_min + 260)
            for k in range(k_min, k_max + 1):
                sx = self.w2s(k * step, 0).x()
                p.drawLine(QPointF(sx, 0), QPointF(sx, H))
            k_min = math.floor(y0 / step)
            k_max = min(math.ceil(y1 / step), k_min + 260)
            for k in range(k_min, k_max + 1):
                sy = self.w2s(0, k * step).y()
                p.drawLine(QPointF(0, sy), QPointF(W, sy))

        if self.show_axes:
            p.setPen(QPen(axis_c, 1.5))
            o = self.w2s(0, 0)
            if -20 <= o.y() <= H + 20:
                p.drawLine(QPointF(0, o.y()), QPointF(W, o.y()))
            if -20 <= o.x() <= W + 20:
                p.drawLine(QPointF(o.x(), 0), QPointF(o.x(), H))
            # Mũi tên 2 đầu trục Ox, Oy
            p.setBrush(QBrush(axis_c))
            if 0 <= o.y() <= H:
                p.drawPolygon(QPolygonF([QPointF(W - 2, o.y()), QPointF(W - 10, o.y() - 3.5), QPointF(W - 10, o.y() + 3.5)]))
            if 0 <= o.x() <= W:
                p.drawPolygon(QPolygonF([QPointF(o.x(), 2), QPointF(o.x() - 3.5, 10), QPointF(o.x() + 3.5, 10)]))
            p.setBrush(Qt.NoBrush)

            f = QFont("Segoe UI", 8)
            p.setFont(f)
            fm_t = QFontMetricsF(f)
            p.setPen(QColor("#94A3B8" if self.dark else "#64748B"))
            ox_y = max(14.0, min(H - 22.0, o.y()))
            oy_x = max(8.0, min(W - 44.0, o.x()))

            def _fmt_tick(v):
                if abs(v) < 1e-12:
                    return "0"
                return f"{round(v, 9):g}"

            last_tx = -1e9
            k_min = math.floor(x0 / step)
            k_max = min(math.ceil(x1 / step), k_min + 260)
            for k in range(k_min, k_max + 1):
                if k == 0:
                    continue
                val = k * step
                sp = self.w2s(val, 0)
                if 0 <= o.y() <= H:
                    p.drawLine(QPointF(sp.x(), o.y() - 3), QPointF(sp.x(), o.y() + 3))
                lbl = _fmt_tick(val)
                tw = fm_t.horizontalAdvance(lbl)
                tx = sp.x() - tw / 2.0
                if tx > last_tx + 6 and 4 <= sp.x() <= W - 18:
                    p.drawText(QPointF(tx, ox_y + 15), lbl)
                    last_tx = tx + tw

            k_min = math.floor(y0 / step)
            k_max = min(math.ceil(y1 / step), k_min + 260)
            for k in range(k_min, k_max + 1):
                if k == 0:
                    continue
                val = k * step
                sp = self.w2s(0, val)
                if 0 <= o.x() <= W:
                    p.drawLine(QPointF(o.x() - 3, sp.y()), QPointF(o.x() + 3, sp.y()))
                if 16 <= sp.y() <= H - 12:
                    p.drawText(QPointF(oy_x + 7, sp.y() + 4), _fmt_tick(val))

            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            if 0 <= o.x() <= W and 0 <= o.y() <= H:
                p.drawText(QPointF(o.x() - 13, o.y() + 15), "O")
            if 0 <= o.y() <= H:
                p.drawText(QPointF(W - 16, o.y() - 8), "x")
            if 0 <= o.x() <= W:
                p.drawText(QPointF(o.x() + 9, 14), "y")

        font = QFont("Segoe UI", 10)
        p.setFont(font)
        func_idx = 0
        for i, o in enumerate(self.objs):
            if o["hidden"]:
                continue
            is_sel = (self.sel == ("o", i)) or any(k == "o" and idx_ == i for k, idx_ in self.pending)
            is_hov = interactive and (self.hover == ("o", i))
            if o.get("edge_ref") and not (is_sel or is_hov):
                continue
            self._draw_obj(p, o, is_sel, is_hov, W, H, func_idx, i, interactive)
            if o["type"] == "func":
                func_idx += 1

        # Tô sáng cạnh đa giác đang rê chuột khi chọn mục tiêu dựng hình
        if interactive and self.hover and self.hover[0] == "edge":
            _, eu, ev = self.hover
            if eu in self.points and ev in self.points:
                sa, sb = self.w2s(*self.P(eu)), self.w2s(*self.P(ev))
                p.setPen(QPen(QColor(245, 158, 11, 90), 9.0, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(sa, sb)
                p.setPen(QPen(QColor("#F59E0B"), 2.8, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(sa, sb)

        # Xem trước động đối tượng đang dựng
        if interactive and self.pending and self.tool != "select":
            self._draw_live_preview(p, W, H)

        # Vẽ điểm
        for pid in self.order:
            pt = self.points[pid]
            if pt.get("hidden"):
                continue
            sp = self.w2s(pt["x"], pt["y"])
            col = QColor(pt["color"] or ("#F8FAFC" if self.dark else "#0F172A"))
            selected = self.sel == ("p", pid)
            hovered = interactive and (self.hover == ("p", pid))
            pend = any(k == "p" and i == pid for k, i in self.pending)
            if hovered or selected or pend:
                glow_c = QColor("#EF4444" if self.tool == "erase" else "#F59E0B")
                glow_c.setAlpha(65)
                p.setPen(Qt.NoPen)
                p.setBrush(glow_c)
                p.drawEllipse(sp, 11, 11)
            r = 5.4 if (selected or pend or hovered) else 4.3
            p.setPen(QPen(QColor("#F59E0B") if (selected or pend) else self.bg, 1.7))
            p.setBrush(QBrush(col if pt["kind"] == "free" else QColor("#EF4444")))
            p.drawEllipse(sp, r, r)
            if self.show_labels:
                lpos = QPointF(sp.x() + pt.get("lx", 8.0), sp.y() + pt.get("ly", -7.0))
                self._draw_drag_label(p, lpos, pt["label"], self.fg, QFont("Segoe UI", 10.5, QFont.Bold), ("pt_lbl", pid), interactive)

        # Vòng tròn xem trước vị trí đặt điểm / giao điểm tự động (đặt đâu trúng đúng đó)
        if interactive and self.snap_target and self.tool != "select":
            self._draw_snap_preview(p, self.snap_target)

        # Dò tọa độ trực tiếp trên đồ thị hàm số
        if interactive and self.trace_pt:
            tx, ty, expr, col = self.trace_pt
            sp = self.w2s(tx, ty)
            c = QColor(col)
            p.setPen(QPen(self.bg, 2))
            p.setBrush(c)
            p.drawEllipse(sp, 5.2, 5.2)
            lbl = f"({tx:.2f}; {ty:.2f})"
            p.setFont(QFont("Segoe UI", 8.5, QFont.Bold))
            fm = QFontMetricsF(p.font())
            tw = fm.horizontalAdvance(lbl) + 12
            box = QRectF(sp.x() + 10, sp.y() - 26, tw, 20)
            p.setPen(QPen(c, 1.2))
            p.setBrush(QColor(15, 23, 42, 220) if self.dark else QColor(255, 255, 255, 235))
            p.drawRoundedRect(box, 6, 6)
            p.setPen(self.fg)
            p.drawText(box, Qt.AlignCenter, lbl)

        # HUD góc dưới trái + thanh hướng dẫn từng bước phía trên khi dựng hình
        if interactive:
            self._draw_hud(p, W, H)
            self._draw_step_banner(p, W)

    def _draw_step_banner(self, p, W):
        txt = self._step_prompt()
        if not txt:
            return
        font = QFont("Segoe UI", 8.5, QFont.DemiBold)
        p.setFont(font)
        fm = QFontMetricsF(font)
        max_w = max(140.0, W - 24.0)
        br = fm.boundingRect(QRectF(0, 0, max_w - 20.0, 180.0), Qt.AlignCenter | Qt.TextWordWrap, txt)
        tw = min(max_w, max(110.0, br.width() + 26.0))
        th = max(25.0, br.height() + 12.0)
        rect = QRectF((W - tw) / 2.0, 10.0, tw, th)
        warn = bool(self._warn_msg)
        if warn:
            bg = QColor(120, 53, 15, 232) if self.dark else QColor(254, 243, 199, 244)
            bd = QColor("#F59E0B")
            fg = QColor("#FDE68A" if self.dark else "#92400E")
        else:
            bg = QColor(15, 23, 42, 218) if self.dark else QColor(248, 250, 252, 240)
            bd = QColor("#4F46E5" if not self.dark else "#6366F1")
            fg = QColor("#E2E8F0" if self.dark else "#1E293B")
        p.setPen(QPen(bd, 1.2))
        p.setBrush(bg)
        p.drawRoundedRect(rect, 8, 8)
        p.setPen(fg)
        p.drawText(rect.adjusted(10, 4, -10, -4), Qt.AlignCenter | Qt.TextWordWrap, txt)

    def _draw_snap_preview(self, p, st):
        sp = self.w2s(st["wx"], st["wy"])
        kind = st["kind"]
        if kind == "point":
            return  # Điểm có sẵn đã có vòng sáng hover riêng
        if kind == "inter":
            # Giao điểm 2 đường/hình: vòng tròn phát sáng xanh ngọc + chữ thập + nhãn "Giao điểm"
            col = QColor("#10B981")
            glow = QColor(16, 185, 129, 72)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(sp, 13.5, 13.5)
            p.setPen(QPen(col, 2.2))
            p.setBrush(self.bg)
            p.drawEllipse(sp, 6.2, 6.2)
            p.setPen(QPen(col, 1.8))
            p.drawLine(QPointF(sp.x() - 3.2, sp.y() - 3.2), QPointF(sp.x() + 3.2, sp.y() + 3.2))
            p.drawLine(QPointF(sp.x() + 3.2, sp.y() - 3.2), QPointF(sp.x() - 3.2, sp.y() + 3.2))
            import i18n
            lbl = f"{'Intersection' if i18n.is_en() else 'Giao điểm'} ({st['wx']:.2f}; {st['wy']:.2f})"
            font = QFont("Segoe UI", 8.5, QFont.Bold)
            p.setFont(font)
            fm = QFontMetricsF(font)
            tw = fm.horizontalAdvance(lbl) + 14
            box = QRectF(sp.x() + 12, sp.y() - 26, tw, 20)
            p.setPen(QPen(col, 1.2))
            p.setBrush(QColor(6, 78, 59, 230) if self.dark else QColor(236, 253, 245, 242))
            p.drawRoundedRect(box, 6, 6)
            p.setPen(QColor("#A7F3D0" if self.dark else "#065F46"))
            p.drawText(box, Qt.AlignCenter, lbl)
            return
        if kind == "on_obj":
            col = QColor("#0EA5E9")
            glow = QColor(14, 165, 233, 55)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(sp, 11.0, 11.0)
            p.setPen(QPen(col, 2.0))
            p.setBrush(self.bg)
            p.drawEllipse(sp, 5.2, 5.2)
            return
        if kind == "grid":
            col = QColor("#F59E0B")
            glow = QColor(245, 158, 11, 52)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(sp, 10.5, 10.5)
            p.setPen(QPen(col, 1.9))
            p.setBrush(self.bg)
            p.drawEllipse(sp, 4.8, 4.8)
            return
        # kind == "free": vòng tròn báo vị trí điểm ngay đúng con trỏ
        col = QColor("#6366F1" if self.dark else "#4F46E5")
        p.setPen(QPen(col, 1.7, Qt.DashLine))
        p.setBrush(QColor(99, 102, 241, 45))
        p.drawEllipse(sp, 7.0, 7.0)
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawEllipse(sp, 2.8, 2.8)

    def _draw_live_preview(self, p, W, H):
        t = self.tool
        if self.snap_target:
            mx, my = self.snap_target["wx"], self.snap_target["wy"]
        else:
            mx, my = self._snap(*self.s2w(self.mouse_pos), self.mouse_pos)
        ms = self.w2s(mx, my)
        p_ids = [i for k, i in self.pending if k == "p"]
        o_ids = [i for k, i in self.pending if k == "o"]
        pts_w = [self.P(i) for i in p_ids if i in self.points]
        pts_s = [self.w2s(*q) for q in pts_w]
        pen = QPen(QColor("#F59E0B"), 1.8, Qt.DashLine)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        if t in ("perp", "para", "foot", "reflect"):
            # Lấy đường đang chọn hoặc đang rê chuột (kể cả cạnh đa giác)
            ln = None
            if o_ids:
                ln = self.line_of(self.objs[o_ids[0]])
            elif self.hover:
                if self.hover[0] == "o":
                    ln = self.line_of(self.objs[self.hover[1]])
                elif self.hover[0] == "edge":
                    a_, b_ = self.P(self.hover[1]), self.P(self.hover[2])
                    ln = (a_, _sub(b_, a_))
            pt_w = pts_w[0] if pts_w else (mx, my)
            if ln:
                (q, d) = ln
                dd = d[0] * d[0] + d[1] * d[1]
                if dd > 1e-12:
                    if t in ("perp", "para"):
                        dir_ = (-d[1], d[0]) if t == "perp" else d
                        seg = self._clip_line(pt_w, dir_, W, H, "line")
                        if seg:
                            p.drawLine(*seg)
                    else:
                        u_ = ((pt_w[0] - q[0]) * d[0] + (pt_w[1] - q[1]) * d[1]) / dd
                        fx, fy = q[0] + u_ * d[0], q[1] + u_ * d[1]
                        tx, ty = (fx, fy) if t == "foot" else (2 * fx - pt_w[0], 2 * fy - pt_w[1])
                        p.drawLine(self.w2s(*pt_w), self.w2s(tx, ty))
                        p.setBrush(QColor("#F59E0B"))
                        p.drawEllipse(self.w2s(tx, ty), 4.5, 4.5)
                        p.setBrush(Qt.NoBrush)
            return
        if t == "mid" and len(pts_w) == 1:
            p.drawLine(pts_s[0], ms)
            mp = self.w2s((pts_w[0][0] + mx) / 2, (pts_w[0][1] + my) / 2)
            p.setBrush(QColor("#F59E0B"))
            p.drawEllipse(mp, 4.5, 4.5)
            p.setBrush(Qt.NoBrush)
            return
        if t == "sym_pt" and len(pts_w) == 1:
            rx, ry = 2 * mx - pts_w[0][0], 2 * my - pts_w[0][1]
            rs = self.w2s(rx, ry)
            p.drawLine(pts_s[0], rs)
            p.setBrush(QColor("#F59E0B"))
            p.drawEllipse(rs, 4.5, 4.5)
            p.setBrush(Qt.NoBrush)
            return

        if t == "circle" and len(pts_w) == 1:
            r = math.hypot(mx - pts_w[0][0], my - pts_w[0][1])
            p.drawEllipse(pts_s[0], r * self.scale, r * self.scale)
            p.drawLine(pts_s[0], ms)
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(QPointF((pts_s[0].x() + ms.x()) / 2 + 6, (pts_s[0].y() + ms.y()) / 2 - 6), f"R = {r:.2f}")
        elif t == "circ3" and len(pts_w) == 2:
            cc = self._circumcircle(pts_w[0], pts_w[1], (mx, my))
            if cc:
                sc = self.w2s(*cc[0])
                p.drawEllipse(sc, cc[1] * self.scale, cc[1] * self.scale)
            p.drawLine(pts_s[0], pts_s[1])
        elif t in ("line", "ray") and len(pts_w) == 1:
            seg = self._clip_line(pts_w[0], (mx - pts_w[0][0], my - pts_w[0][1]), W, H, t)
            if seg:
                p.drawLine(*seg)
        elif t == "perpbis" and len(pts_w) == 1:
            p.drawLine(pts_s[0], ms)
            dx, dy = mx - pts_w[0][0], my - pts_w[0][1]
            mid = ((pts_w[0][0] + mx) / 2, (pts_w[0][1] + my) / 2)
            seg = self._clip_line(mid, (-dy, dx), W, H, "line")
            if seg:
                p.drawLine(*seg)
        elif t == "poly" and pts_s:
            poly_s = pts_s + [ms]
            fill = QColor("#F59E0B")
            fill.setAlpha(24)
            p.setBrush(fill)
            p.drawPolygon(QPolygonF(poly_s))
        elif t == "angle" and len(pts_w) == 2:
            p.drawLine(pts_s[0], pts_s[1])
            p.drawLine(pts_s[1], ms)
            deg = self._angle_deg(pts_w[0], pts_w[1], (mx, my))
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(pts_s[1] + QPointF(10, -10), f"{deg:.1f}°")
        elif pts_s:
            for a, b in zip(pts_s, pts_s[1:]):
                p.drawLine(a, b)
            p.drawLine(pts_s[-1], ms)
            if t == "seg" and len(pts_w) == 1:
                L = math.hypot(mx - pts_w[0][0], my - pts_w[0][1])
                p.setFont(QFont("Segoe UI", 9, QFont.Bold))
                p.drawText(QPointF((pts_s[0].x() + ms.x()) / 2 + 6, (pts_s[0].y() + ms.y()) / 2 - 6), f"{L:.2f}")

    def _draw_hud(self, p, W, H):
        wx, wy = self.s2w(self.mouse_pos)
        zoom_pct = int(round(self.scale / 48.0 * 100))
        coord = f"({wx:.2f}; {wy:.2f})" if self.rect().contains(self.mouse_pos.toPoint()) else ""
        parts = [f"{zoom_pct}%"]
        if coord:
            parts.append(coord)
        if self.tool != "select":
            parts.append(_tool_label(self.tool))
        txt = "  ·  ".join(parts)
        font = QFont("Segoe UI", 8.5, QFont.DemiBold)
        p.setFont(font)
        fm = QFontMetricsF(font)
        tw = fm.horizontalAdvance(txt) + 18
        rect = QRectF(10, H - 30, tw, 22)
        bg = QColor(15, 23, 42, 190) if self.dark else QColor(248, 250, 252, 230)
        bd = QColor("#334155") if self.dark else QColor("#CBD5E1")
        p.setPen(QPen(bd, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, 7, 7)
        p.setPen(QColor("#CBD5E1" if self.dark else "#475569"))
        p.drawText(rect, Qt.AlignCenter, txt)

    def _pen(self, o, selected, hovered=False):
        c = QColor(o["color"] if o["color"] else self.fg)
        if self.dark and c.name().lower() in ("#0f172a", "#111827", "#000000"):
            c = QColor("#E2E8F0")
        w = o["width"] + (1.4 if selected else (0.9 if hovered else 0.0))
        pen = QPen(c, w)
        if o["dashed"]:
            pen.setStyle(Qt.DashLine)
        pen.setCapStyle(Qt.RoundCap)
        return pen

    def _clip_line(self, p0, d, W, H, mode):
        a = self.w2s(*p0)
        dx, dy = d[0] * self.scale, -d[1] * self.scale
        n = math.hypot(dx, dy)
        if n == 0:
            return None
        dx, dy = dx / n, dy / n
        L = (W + H) * 3
        s = a if mode == "ray" else QPointF(a.x() - dx * L, a.y() - dy * L)
        return s, QPointF(a.x() + dx * L, a.y() + dy * L)

    def _draw_drag_label(self, p, pos, text, color, font, target, interactive=True):
        """Vẽ nhãn / chú thích có thể kéo di chuyển bằng chuột trong chế độ Chọn, tự ghi vùng hit-test."""
        if not text:
            return
        p.setFont(font)
        fm = QFontMetricsF(font)
        tw = fm.horizontalAdvance(text)
        ascent = fm.ascent()
        descent = fm.descent()
        rect = QRectF(pos.x() - 3.0, pos.y() - ascent - 2.0, tw + 6.0, ascent + descent + 4.0)
        if interactive and target is not None:
            self._label_rects.append((rect, target))
            is_hov = (self.tool == "select" and self.hover_lbl == target)
            is_drag = (self.drag_lbl is not None and self.drag_lbl[0] == target)
            if is_hov or is_drag:
                bg = QColor(99, 102, 241, 48) if self.dark else QColor(79, 70, 229, 32)
                bd = QColor("#818CF8" if self.dark else "#4F46E5")
                p.save()
                p.setPen(QPen(bd, 1.1, Qt.DashLine))
                p.setBrush(bg)
                p.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 4, 4)
                p.restore()
        p.setPen(color)
        p.drawText(pos, text)

    def _draw_obj(self, p, o, selected, hovered, W, H, func_idx=0, oi=-1, interactive=True):
        t = o["type"]
        pen = self._pen(o, selected, hovered)
        p.setBrush(Qt.NoBrush)
        lx, ly = o.get("lx", 0.0), o.get("ly", 0.0)
        lbl_tgt = ("obj_lbl", oi) if oi >= 0 else None
        try:
            if t == "func":
                self._draw_func(p, o, pen, W, H, func_idx)
                return
            if t == "text":
                sp = self.w2s(o["x"], o["y"])
                col = QColor(o["color"])
                if self.dark and col.name().lower() in ("#0f172a", "#111827", "#000000"):
                    col = QColor("#E2E8F0")
                self._draw_drag_label(p, sp, o["text"], col, QFont("Segoe UI", 12), ("text_obj", oi) if oi >= 0 else None, interactive)
                return
            if t == "poly":
                pts = [self.w2s(*self.P(k)) for k in o["pts"]]
                if self.fill_polys:
                    c = QColor(o["color"])
                    c.setAlpha(44 if hovered else 30)
                    p.setBrush(QBrush(c))
                p.setPen(pen)
                p.drawPolygon(QPolygonF(pts))
                p.setBrush(Qt.NoBrush)
                if self.show_measure:
                    P = [self.P(k) for k in o["pts"]]
                    p.setPen(QColor("#94A3B8" if self.dark else "#64748B"))
                    p.setFont(QFont("Segoe UI", 9))
                    for a, b, sa, sb in zip(P, P[1:] + P[:1], pts, pts[1:] + pts[:1]):
                        p.drawText(QPointF((sa.x() + sb.x()) / 2 + 4, (sa.y() + sb.y()) / 2 - 4), f"{math.hypot(*_sub(a, b)):.2f}")
                    cx = sum(q.x() for q in pts) / len(pts)
                    cy = sum(q.y() for q in pts) / len(pts)
                    self._draw_drag_label(p, QPointF(cx - 20 + lx, cy + ly), o.get("label") or f"S = {self._area(P):.2f}", QColor(o["color"]), QFont("Segoe UI", 9.5, QFont.Bold), lbl_tgt, interactive)
                return
            if t == "angle":
                a, b, c = (self.P(k) for k in o["pts"])
                sb = self.w2s(*b)
                ang1 = math.atan2(a[1] - b[1], a[0] - b[0])
                ang2 = math.atan2(c[1] - b[1], c[0] - b[0])
                diff = (ang2 - ang1 + math.pi) % (2 * math.pi) - math.pi
                deg = self._angle_deg(a, b, c)
                p.setPen(pen)
                if abs(deg - 90.0) < 0.25:
                    sz = 14.0
                    u1 = QPointF(math.cos(ang1) * sz, -math.sin(ang1) * sz)
                    u2 = QPointF(math.cos(ang2) * sz, -math.sin(ang2) * sz)
                    p1, p2, p3 = sb + u1, sb + u1 + u2, sb + u2
                    p.drawLine(p1, p2)
                    p.drawLine(p2, p3)
                    self._draw_drag_label(p, p2 + QPointF(4 + lx, -3 + ly), o.get("label") or "90°", pen.color(), QFont("Segoe UI", 8.5, QFont.Bold), lbl_tgt, interactive)
                else:
                    rad = 26
                    p.drawArc(QRectF(sb.x() - rad, sb.y() - rad, 2 * rad, 2 * rad), int(math.degrees(ang1) * 16), int(math.degrees(diff) * 16))
                    mid = ang1 + diff / 2
                    apos = QPointF(sb.x() + (rad + 10) * math.cos(mid) - 12 + lx, sb.y() - (rad + 10) * math.sin(mid) + 4 + ly)
                    self._draw_drag_label(p, apos, o.get("label") or f"{deg:.1f}°", pen.color(), QFont("Segoe UI", 9, QFont.Bold), lbl_tgt, interactive)
                return
            ci = self.circle_of(o)
            if ci:
                c, r = ci
                sc = self.w2s(*c)
                if hovered:
                    hc = QColor(pen.color())
                    hc.setAlpha(60)
                    p.setPen(QPen(hc, pen.widthF() + 5))
                    p.drawEllipse(sc, r * self.scale, r * self.scale)
                p.setPen(pen)
                p.drawEllipse(sc, r * self.scale, r * self.scale)
                if self.show_measure and t == "circle":
                    self._draw_drag_label(p, QPointF(sc.x() + 6 + lx, sc.y() + 15 + ly), o.get("label") or f"R = {r:.2f}", QColor("#94A3B8" if self.dark else "#64748B"), QFont("Segoe UI", 9), lbl_tgt, interactive)
                return
            ln = self.line_of(o)
            if ln:
                (px, py), (dx, dy) = ln
                if t in ("seg", "vec"):
                    a, b = self.w2s(*self.P(o["pts"][0])), self.w2s(*self.P(o["pts"][1]))
                    if hovered:
                        hc = QColor(pen.color())
                        hc.setAlpha(60)
                        p.setPen(QPen(hc, pen.widthF() + 5, Qt.SolidLine, Qt.RoundCap))
                        p.drawLine(a, b)
                    p.setPen(pen)
                    p.drawLine(a, b)
                    if t == "vec":
                        ang = math.atan2(b.y() - a.y(), b.x() - a.x())
                        h = QPolygonF([
                            b,
                            QPointF(b.x() - 12 * math.cos(ang - 0.38), b.y() - 12 * math.sin(ang - 0.38)),
                            QPointF(b.x() - 12 * math.cos(ang + 0.38), b.y() - 12 * math.sin(ang + 0.38)),
                        ])
                        p.setBrush(QBrush(pen.color()))
                        p.drawPolygon(h)
                        p.setBrush(Qt.NoBrush)
                    mpos = QPointF((a.x() + b.x()) / 2 + 5 + lx, (a.y() + b.y()) / 2 - 5 + ly)
                    if self.show_measure and t == "seg":
                        P1, P2 = self.P(o["pts"][0]), self.P(o["pts"][1])
                        self._draw_drag_label(p, mpos, o["label"] or f"{math.hypot(*_sub(P1, P2)):.2f}", QColor("#94A3B8" if self.dark else "#64748B"), QFont("Segoe UI", 9), lbl_tgt, interactive)
                    elif o["label"]:
                        self._draw_drag_label(p, mpos, o["label"], self.fg, QFont("Segoe UI", 9.5), lbl_tgt, interactive)
                else:
                    seg = self._clip_line((px, py), (dx, dy), W, H, "ray" if t == "ray" else "line")
                    if seg:
                        if hovered:
                            hc = QColor(pen.color())
                            hc.setAlpha(60)
                            p.setPen(QPen(hc, pen.widthF() + 5))
                            p.drawLine(*seg)
                        p.setPen(pen)
                        p.drawLine(*seg)
                    if o["label"]:
                        self._draw_drag_label(p, self.w2s(px, py) + QPointF(8 + lx, -8 + ly), o["label"], self.fg, QFont("Segoe UI", 9.5), lbl_tgt, interactive)
        except (KeyError, IndexError, ZeroDivisionError):
            return

    def _draw_func(self, p, o, pen, W, H=600, func_idx=0):
        item = self._get_func(o["expr"])
        if not item:
            return
        c, node = item
        path, pen_down, last = QPainterPath(), False, None
        n = max(240, int(W * 1.25))
        x0, x1 = self.s2w(QPointF(0, 0))[0], self.s2w(QPointF(W, 0))[0]
        jump_lim = max(2000.0, H * 3.0)
        for i in range(n):
            x = x0 + (x1 - x0) * i / (n - 1)
            try:
                y = c.ev(node, {"x": x})
                if isinstance(y, complex) or not math.isfinite(float(y)):
                    raise ValueError
                sp = self.w2s(x, float(y))
                if abs(sp.y()) > 1e5 or (last is not None and abs(sp.y() - last) > jump_lim):
                    pen_down = False
                    last = None
                    continue
                if not pen_down:
                    path.moveTo(sp)
                    pen_down = True
                else:
                    path.lineTo(sp)
                last = sp.y()
            except (ce.CalcError, ValueError, ZeroDivisionError, OverflowError):
                pen_down = False
                last = None
        p.setPen(pen)
        p.drawPath(path)
        # Nhãn chú giải dạng pill góc trên trái
        lbl = f"y = {o['expr']}"
        p.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        fm = QFontMetricsF(p.font())
        tw = fm.horizontalAdvance(lbl) + 18
        box = QRectF(12, 10 + 26 * func_idx, tw, 22)
        bg = QColor(15, 23, 42, 195) if self.dark else QColor(255, 255, 255, 225)
        p.setPen(QPen(QColor(o["color"]), 1.2))
        p.setBrush(bg)
        p.drawRoundedRect(box, 6, 6)
        p.setPen(QColor(o["color"]))
        p.drawText(box, Qt.AlignCenter, lbl)
        p.setBrush(Qt.NoBrush)

    # ------------------------------------------------------------------ xuất
    def export_pixmap(self, scale=2):
        img = QImage(self.width() * scale, self.height() * scale, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.scale(scale, scale)
        sel, self.sel = self.sel, None
        self._draw(p, QRectF(0, 0, self.width(), self.height()), False)
        self.sel = sel
        p.end()
        return img

    def export_svg_bytes(self):
        from PySide6.QtSvg import QSvgGenerator
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        gen = QSvgGenerator()
        gen.setOutputDevice(buf)
        gen.setSize(QSize(self.width(), self.height()))
        gen.setViewBox(QRectF(0, 0, self.width(), self.height()))
        gen.setTitle("Formula Studio - Hình học")
        p = QPainter(gen)
        sel, self.sel = self.sel, None
        self._draw(p, QRectF(0, 0, self.width(), self.height()), False)
        self.sel = sel
        p.end()
        buf.close()
        return bytes(ba)
