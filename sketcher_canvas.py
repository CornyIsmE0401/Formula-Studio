# -*- coding: utf-8 -*-
"""sketcher_canvas.py - Trình vẽ cấu trúc phân tử chuyên nghiệp:
liên kết đơn/đôi/ba/nêm đặc/nêm đứt (stereo), phím tắt kiểu ChemDraw, xem trước bóng mờ (ghost preview),
chọn vùng kéo nhiều nguyên tử, xoay/lật phân tử, lưới chấm, menu chuột phải, chuẩn hóa bố cục, hoàn tác/làm lại."""
import copy
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QGuiApplication, QPainter, QPen, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QInputDialog, QMenu, QWidget

import data_store as ds
import molecule as mo

GROUPS = {
    # Alkyl / Hydrocarbon
    "CH₃ (Methyl)": "C", "C₂H₅ (Ethyl)": "CC", "C₃H₇ (n-Propyl)": "CCC", "CH(CH₃)₂ (Isopropyl)": "C(C)C", "C₄H₉ (n-Butyl)": "CCCC",
    "C(CH₃)₃ (tert-Butyl)": "C(C)(C)C", "CH₂CH(CH₃)₂ (Isobutyl)": "CC(C)C", "CH=CH₂ (Vinyl)": "C=C", "CH₂CH=CH₂ (Allyl)": "CC=C",
    "C≡CH (Ethynyl)": "C#C", "C₆H₅ (Phenyl)": "c1ccccc1", "CH₂C₆H₅ (Benzyl)": "Cc1ccccc1", "Cyclohexyl": "C1CCCCC1", "Cyclopropyl": "C1CC1",
    "Naphthyl": "c1ccc2ccccc2c1", "Pyridyl": "c1ccncc1", "Furyl": "c1ccco1", "Thienyl": "c1cccs1",
    # Oxygen-containing
    "OH (Hydroxyl)": "O", "OCH₃ (Methoxy)": "OC", "OC₂H₅ (Ethoxy)": "OCC", "OC₆H₅ (Phenoxy)": "Oc1ccccc1", "CH₂OH (Hydroxymethyl)": "CO", "CH₂OCH₃": "COC",
    "CHO (Aldehyde)": "C=O", "COCH₃ (Acetyl)": "C(C)=O", "COOH (Carboxyl)": "C(=O)O", "COOCH₃ (Methoxycarbonyl)": "C(=O)OC", "COOC₂H₅ (Ethoxycarbonyl)": "C(=O)OCC",
    "OCOCH₃ (Acetoxy)": "OC(C)=O", "COCl (Acyl chloride)": "C(Cl)=O", "C=O (Carbonyl)": "C=O", "OOH (Hydroperoxy)": "OO",
    # Nitrogen-containing
    "NH₂ (Amino)": "N", "NHCH₃": "NC", "N(CH₃)₂": "N(C)C", "N(C₂H₅)₂": "N(CC)CC", "NHCOCH₃ (Acetamido)": "NC(C)=O", "CONH₂ (Carbamoyl)": "C(=O)N",
    "CN (Cyano / Nitrile)": "C#N", "NO₂ (Nitro)": "[N+](=O)[O-]", "NO (Nitroso)": "N=O", "N₃ (Azide)": "N=[N+]=[N-]", "NH-NH₂ (Hydrazino)": "NN",
    # Halogen
    "F (Fluoro)": "F", "Cl (Chloro)": "Cl", "Br (Bromo)": "Br", "I (Iodo)": "I", "CF₃ (Trifluoromethyl)": "C(F)(F)F", "CCl₃": "C(Cl)(Cl)Cl", "CH₂Cl": "CCl", "CH₂Br": "CBr",
    # Sulfur, Phosphorus, Boron, Silicon & Protecting groups
    "SH (Thiol)": "S", "SCH₃ (Methylthio)": "SC", "SO₃H (Sulfo)": "S(=O)(=O)O", "SO₂NH₂ (Sulfamoyl)": "S(N)(=O)=O", "SO₂CH₃ (Mesyl)": "S(C)(=O)=O", "S=O (Sulfinyl)": "S=O",
    "PO₃H₂ (Phosphono)": "P(=O)(O)O", "OPO₃H₂ (Phosphate)": "OP(=O)(O)O", "B(OH)₂ (Boronic)": "B(O)O", "Si(CH₃)₃ (TMS)": "[Si](C)(C)C",
    "Boc (-COOtBu)": "C(=O)OC(C)(C)C", "Tosyl (Ts)": "S(=O)(=O)c1ccc(C)cc1",
}

QUICK_GROUPS = [
    ("OH", "OH (Hydroxyl)"), ("NH₂", "NH₂ (Amino)"), ("COOH", "COOH (Carboxyl)"), ("CHO", "CHO (Aldehyde)"),
    ("NO₂", "NO₂ (Nitro)"), ("CN", "CN (Cyano / Nitrile)"), ("CH₃", "CH₃ (Methyl)"), ("C₂H₅", "C₂H₅ (Ethyl)"),
    ("OCH₃", "OCH₃ (Methoxy)"), ("COCH₃", "COCH₃ (Acetyl)"), ("SO₃H", "SO₃H (Sulfo)"), ("Ph", "C₆H₅ (Phenyl)"),
]

ELEMENT_CHOICES = [
    "C", "H", "N", "O", "S", "P", "F", "Cl", "Br", "I", "B", "Si", "Se", "As",
    "Li", "Na", "K", "Rb", "Cs", "Be", "Mg", "Ca", "Sr", "Ba", "Al", "Ga",
    "Sn", "Pb", "Bi", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ag", "Au", "Pt", "Pd", "Hg", "Cd", "W", "Mo", "Zr", "He", "Ne", "Ar", "Xe",
]

QUICK_ELEMENTS = ["C", "H", "N", "O", "S", "P", "F", "Cl", "Br", "I", "B", "Si"]

TEMPLATES = {
    "Mạch thẳng (Chains)": {
        "Pentane (C₅)": "CCCCC", "Hexane (C₆)": "CCCCCC", "Heptane (C₇)": "CCCCCCC", "Octane (C₈)": "CCCCCCCC",
        "Nonane (C₉)": "CCCCCCCCC", "Decane (C₁₀)": "CCCCCCCCCC", "Isobutane": "CC(C)C", "Neopentane": "CC(C)(C)C",
        "Isopentane": "CCC(C)C", "But-2-ene": "CC=CC", "Buta-1,3-diene": "C=CC=C", "Isoprene": "C=CC(C)=C",
    },
    "Vòng thơm (Aromatics)": {
        "Naphthalene": "c1ccc2ccccc2c1", "Anthracene": "c1ccc2cc3ccccc3cc2c1", "Phenanthrene": "c1ccc2c(c1)ccc1ccccc12",
        "Pyrene": "c1cc2ccc3cccc4ccc(c1)c2c34", "Biphenyl": "c1ccc(cc1)-c1ccccc1", "Toluene": "Cc1ccccc1",
        "Styrene": "C=Cc1ccccc1", "Phenol": "Oc1ccccc1", "Aniline": "Nc1ccccc1", "Benzoic acid": "OC(=O)c1ccccc1",
        "Salicylic acid": "OC(=O)c1ccccc1O",
    },
    "Dị vòng (Heterocycles)": {
        "Pyridine": "c1ccncc1", "Pyrimidine": "c1cncnc1", "Pyrazine": "c1cnccn1", "Furan": "c1ccoc1",
        "Thiophene": "c1ccsc1", "Pyrrole": "c1cc[nH]c1", "Imidazole": "c1c[nH]cn1", "Thiazole": "c1cscn1",
        "Indole": "c1ccc2[nH]ccc2c1", "Quinoline": "c1ccc2ncccc2c1", "Purine": "c1ncc2[nH]cnc2n1",
        "Oxirane": "C1CO1", "THF": "C1CCOC1", "1,4-Dioxane": "C1COCCO1", "Piperidine": "C1CCNCC1", "Morpholine": "C1COCCN1",
    },
    "Vòng no & Khung (Alicyclic)": {
        "Decalin": "C1CCC2CCCCC2C1", "Norbornane": "C1CC2CCC1C2", "Adamantane": "C1C2CC3CC1CC(C2)C3",
        "Steroid core": "C1CCC2C(C1)CCC1C2CCC2CCCC12", "Cyclohexene": "C1=CCCCC1", "Cyclohexa-1,4-diene": "C1=CCC=CC1",
        "Spiro[4.5]decane": "C1CCCC12CCCCC2",
    },
    "Carbohydrate & Amino acid": {
        "Glucose (pyranose)": "OCC1OC(O)C(O)C(O)C1O", "Fructose (furanose)": "OCC1OC(O)(CO)C(O)C1O",
        "Ribose": "OCC1OC(O)C(O)C1O", "Glycine": "NCC(=O)O", "Alanine": "CC(N)C(=O)O",
        "Valine": "CC(C)C(N)C(=O)O", "Phenylalanine": "NC(Cc1ccccc1)C(=O)O", "Tryptophan": "NC(Cc1c[nH]c2ccccc12)C(=O)O",
        "Proline": "OC(=O)C1CCCN1", "Lactic acid": "CC(O)C(=O)O", "Citric acid": "OC(=O)CC(O)(CC(=O)O)C(=O)O", "Urea": "NC(N)=O",
    },
    "Dược phẩm & Sinh học": {
        "Aspirin": "CC(=O)Oc1ccccc1C(=O)O", "Paracetamol": "CC(=O)Nc1ccc(O)cc1",
        "Ibuprofen": "CC(C)Cc1ccc(C(C)C(=O)O)cc1", "Caffeine": "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
        "Dopamine": "NCCc1ccc(O)c(O)c1", "Adrenaline": "CNC(O)c1ccc(O)c(O)c1",
        "Vanillin": "COc1cc(C=O)ccc1O", "Ascorbic acid (Vitamin C)": "OCC(O)C1OC(=O)C(O)=C1O",
        "Adenine": "Nc1ncnc2[nH]cnc12", "Uracil": "O=c1cc[nH]c(=O)[nH]1",
        "Nicotine": "CN1CCCC1c2cccnc2", "Menthol": "CC1CCC(C(C)C)C(O)C1",
    },
}

_FORMULA_INDEX = None


def identify_formula(counts: dict):
    """Tìm các chất trong kho có cùng công thức phân tử (trả về tên chuẩn IUPAC)."""
    global _FORMULA_INDEX
    import data_chem as dc
    import formula_engine as fe
    if _FORMULA_INDEX is None:
        _FORMULA_INDEX = {}
        for f, en, vi, cat, desc, smi in dc.COMPOUNDS:
            try:
                key = frozenset(fe.parse_formula_counts(f).items())
            except Exception:
                continue
            _FORMULA_INDEX.setdefault(key, []).append(en)
    return _FORMULA_INDEX.get(frozenset(counts.items()), [])


class MoleculeSketcher(QWidget):
    changed = Signal()
    status = Signal(str)
    tool_changed = Signal(str)

    L = 52.0  # px / độ dài liên kết

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(320, 320)
        self.mol = mo.Mol()
        self.tool = "bond1"
        self.element = "C"
        self.ring_n = 6
        self.ring_arom = True
        self.group = "OH (Hydroxyl)"
        self.dark = False
        self.bg_hex = "#FFFFFF"
        self.dot_hex = "#E2E8F0"
        self.show_ch3 = True
        self.show_grid = True
        self.check_valence = True
        self.cmode = "inline"      # skeleton | inline | stacked
        self.ring_c = False
        self.template = None
        self.mono = False
        self.hover = None          # ("a", idx) | ("b", idx)
        self.selected = set()      # set of atom indices
        self.sel_box = None        # (QPointF start, QPointF cur)
        self.erase_box = None      # (QPointF start, QPointF cur) — kéo khoanh vùng để xóa nhiều nguyên tử/liên kết
        self.drag_from = None
        self.drag_to = QPointF()
        self.drag_moved = False
        self.moving = None
        self.pan = None
        self.mouse_pos = QPointF(-1000, -1000)
        self.undo_stack, self.redo_stack = [], []
        self.origin = QPointF(320, 240)
        self._init_origin = False

    # ------------------------------------------------------------------ tiện ích
    def resizeEvent(self, e):
        if not self._init_origin and not self.mol.atoms:
            self.origin = QPointF(self.width() / 2.0, self.height() / 2.0)
            self._init_origin = True
        super().resizeEvent(e)

    def set_dark(self, d, bg_hex=None, dot_hex=None):
        self.dark = bool(d)
        self.bg_hex = bg_hex or ("#0A0F1C" if self.dark else "#FFFFFF")
        self.dot_hex = dot_hex or ("#1C273D" if self.dark else "#DCE4F0")
        self.update()

    def w2s(self, x, y):
        return QPointF(self.origin.x() + x * self.L, self.origin.y() - y * self.L)

    def s2w(self, p):
        return ((p.x() - self.origin.x()) / self.L, (self.origin.y() - p.y()) / self.L)

    def set_tool(self, t, **kw):
        self.tool = t
        for k, v in kw.items():
            setattr(self, k, v)
        if t != "select":
            self.selected.clear()
        self.setCursor(Qt.OpenHandCursor if t == "pan" else Qt.ArrowCursor)
        self.tool_changed.emit(t)
        self.status.emit(self._hint())
        self.update()

    def _hint(self):
        import i18n
        if i18n.is_en():
            return {
                "bond1": "Single bond (1): click an atom to extend at 120°, drag to choose angle/connect atoms; click bond to cycle order",
                "bond2": "Double bond (2): click an atom/bond or drag to create a double bond",
                "bond3": "Triple bond (3): click an atom/bond or drag to create a triple bond",
                "wedge": "Solid wedge (4): drag from an atom to draw an out-of-plane stereobond",
                "dash": "Dashed wedge (5): drag from an atom to draw an into-plane stereobond",
                "atom": f"Element {self.element}: click empty space to place, click atom to replace (tip: hover atom & press C/N/O/S/P/F/L/R)",
                "ring": f"{self.ring_n}-membered ring: click empty space to place, click atom to attach, or click bond to fuse",
                "group": f"Group {self.group}: click an atom to attach (or click empty space to place)",
                "template": "Template: click empty space to place, or click an atom to attach",
                "select": "Select (V): drag atoms to move, drag empty space to box-select; hold H or use Pan View to pan canvas",
                "pan": "Pan View (H): hold left mouse button and drag to pan the canvas freely",
                "plus": "Positive charge (+): click an atom",
                "minus": "Negative charge (−): click an atom",
                "erase": "Erase (E): click an atom/bond to delete, or drag a selection box to erase a region",
            }.get(self.tool, "")
        return {
            "bond1": "Liên kết đơn (1): nhấp nguyên tử để nối dài 120°, kéo để chọn góc/nối hai nguyên tử; nhấp liên kết để đổi bậc",
            "bond2": "Liên kết đôi (2): nhấp nguyên tử/liên kết hoặc kéo để tạo nối đôi",
            "bond3": "Liên kết ba (3): nhấp nguyên tử/liên kết hoặc kéo để tạo nối ba",
            "wedge": "Liên kết nêm đặc (4): kéo từ nguyên tử để vẽ liên kết hướng ra ngoài mặt phẳng (hóa lập thể)",
            "dash": "Liên kết nêm đứt (5): kéo từ nguyên tử để vẽ liên kết hướng vào trong mặt phẳng (hóa lập thể)",
            "atom": f"Nguyên tố {self.element}: nhấp chỗ trống để đặt, nhấp nguyên tử để đổi (mẹo: rê chuột lên nguyên tử rồi bấm C/N/O/S/P/F/L/R)",
            "ring": f"Vòng {self.ring_n} cạnh: nhấp chỗ trống để đặt, nhấp nguyên tử để gắn hoặc nhấp liên kết để ghép vòng",
            "group": f"Nhóm {self.group}: nhấp nguyên tử để gắn (nhấp chỗ trống để đặt riêng)",
            "template": "Khung mẫu: nhấp chỗ trống để đặt, nhấp nguyên tử để nối vào",
            "select": "Chọn (V): kéo nguyên tử di chuyển, kéo vùng trống để khoanh chọn nhiều nguyên tử; giữ phím H hoặc nút Di chuyển để kéo vùng vẽ",
            "pan": "Di chuyển vùng vẽ (H): giữ chuột trái và kéo để trượt khung nhìn tự do mọi hướng",
            "plus": "Tăng điện tích (+): nhấp nguyên tử",
            "minus": "Giảm điện tích (−): nhấp nguyên tử",
            "erase": "Xóa (E): nhấp nguyên tử/liên kết để xóa từng mục, hoặc kéo khoanh vùng để xóa cả vùng",
        }.get(self.tool, "")

    def _snap(self):
        return copy.deepcopy((self.mol.atoms, self.mol.bonds))

    def push_undo(self):
        self.undo_stack.append(self._snap())
        if len(self.undo_stack) > 120:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _restore(self, s):
        self.mol.atoms, self.mol.bonds = copy.deepcopy(s[0]), copy.deepcopy(s[1])
        self.selected.clear()
        self.hover = None
        self.changed.emit()
        self.update()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self._snap())
            self._restore(self.undo_stack.pop())
            self.status.emit("Đã hoàn tác.")

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self._snap())
            self._restore(self.redo_stack.pop())
            self.status.emit("Đã làm lại.")

    def clear_all(self):
        if not self.mol.atoms:
            return
        self.push_undo()
        self.mol = mo.Mol()
        self.selected.clear()
        self.hover = None
        self.changed.emit()
        self.update()

    def load_mol(self, mol, center=True):
        self.push_undo()
        self.mol = mol
        self.selected.clear()
        self.hover = None
        if center and mol.atoms:
            self.center_view()
        self.changed.emit()
        self.update()

    def center_view(self):
        if not self.mol.atoms:
            self.L = 52.0
            self.origin = QPointF(self.width() / 2.0, self.height() / 2.0)
            self.update()
            return
        xs = [a["x"] for a in self.mol.atoms]
        ys = [a["y"] for a in self.mol.atoms]
        w, h = max(xs) - min(xs) + 2.4, max(ys) - min(ys) + 2.4
        self.L = max(10.0, min(68.0, min(self.width() / w, self.height() / h)))
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        self.origin = QPointF(self.width() / 2.0 - cx * self.L, self.height() / 2.0 + cy * self.L)
        self.update()

    def zoom_by(self, factor):
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        wx, wy = self.s2w(center)
        self.L = max(8.0, min(160.0, self.L * factor))
        self.origin = QPointF(center.x() - wx * self.L, center.y() + wy * self.L)
        self.update()

    def rotate_mol(self, deg=15.0):
        targets = list(self.selected) if self.selected else list(range(len(self.mol.atoms)))
        if not targets:
            return
        self.push_undo()
        cx = sum(self.mol.atoms[i]["x"] for i in targets) / len(targets)
        cy = sum(self.mol.atoms[i]["y"] for i in targets) / len(targets)
        rad = math.radians(deg)
        c, s = math.cos(rad), math.sin(rad)
        for i in targets:
            a = self.mol.atoms[i]
            dx, dy = a["x"] - cx, a["y"] - cy
            a["x"], a["y"] = cx + dx * c - dy * s, cy + dx * s + dy * c
        self.changed.emit()
        self.update()

    def flip_mol(self, horizontal=True):
        targets = list(self.selected) if self.selected else list(range(len(self.mol.atoms)))
        if not targets:
            return
        self.push_undo()
        cx = sum(self.mol.atoms[i]["x"] for i in targets) / len(targets)
        cy = sum(self.mol.atoms[i]["y"] for i in targets) / len(targets)
        for i in targets:
            a = self.mol.atoms[i]
            if horizontal:
                a["x"] = 2 * cx - a["x"]
            else:
                a["y"] = 2 * cy - a["y"]
        self.changed.emit()
        self.update()

    def clean(self):
        if not self.mol.atoms:
            return
        self.push_undo()
        mo.layout(self.mol, use_rdkit=True)
        self.center_view()
        self.changed.emit()
        self.update()
        self.status.emit("Đã chuẩn hóa bố cục 2D.")

    # ------------------------------------------------------------------ thao tác đồ thị
    def atom_at(self, pos, r=16):
        best, bd = None, r
        for i, a in enumerate(self.mol.atoms):
            s = self.w2s(a["x"], a["y"])
            d = math.hypot(s.x() - pos.x(), s.y() - pos.y())
            if d < bd:
                best, bd = i, d
        return best

    def bond_at(self, pos, tol=9):
        wx, wy = self.s2w(pos)
        best, bd = None, tol / self.L
        for k, b in enumerate(self.mol.bonds):
            a1, a2 = self.mol.atoms[b["u"]], self.mol.atoms[b["v"]]
            dx, dy = a2["x"] - a1["x"], a2["y"] - a1["y"]
            dd = dx * dx + dy * dy or 1
            s = max(0, min(1, ((wx - a1["x"]) * dx + (wy - a1["y"]) * dy) / dd))
            d = math.hypot(wx - (a1["x"] + s * dx), wy - (a1["y"] + s * dy))
            if d < bd:
                best, bd = k, d
        return best

    def neighbors(self, i):
        out = []
        for b in self.mol.bonds:
            if b["u"] == i:
                out.append(b["v"])
            elif b["v"] == i:
                out.append(b["u"])
        return out

    def free_angle(self, i):
        a = self.mol.atoms[i]
        angs = [math.atan2(self.mol.atoms[n]["y"] - a["y"], self.mol.atoms[n]["x"] - a["x"]) for n in self.neighbors(i)]
        if not angs:
            return math.radians(30)
        if len(angs) == 1:
            base = angs[0] + math.pi
            n0 = self.neighbors(i)[0]
            n2 = self.neighbors(n0)
            sign = 1
            for n in n2:
                if n != i:
                    pa = math.atan2(self.mol.atoms[n]["y"] - self.mol.atoms[n0]["y"], self.mol.atoms[n]["x"] - self.mol.atoms[n0]["x"])
                    d = (angs[0] - pa + math.pi) % (2 * math.pi) - math.pi
                    sign = -1 if d > 0 else 1
            return base + sign * math.radians(60)
        best, bs = 0, -1
        for k in range(24):
            ang = k * math.pi / 12
            m = min(abs((ang - x + math.pi) % (2 * math.pi) - math.pi) for x in angs)
            if m > bs + 1e-9:
                best, bs = ang, m
        return best

    def add_atom(self, x, y, el=None):
        return self.mol.add_atom(el or self.element or "C", 0, None, False, x, y)

    def set_bond(self, u, v, order, cycle=False, stereo=0):
        for b in self.mol.bonds:
            if {b["u"], b["v"]} == {u, v}:
                if stereo:
                    if b.get("stereo", 0) == stereo and b["u"] == u:
                        b["u"], b["v"] = v, u  # lật chiều nêm nếu nhấp lại
                    else:
                        b["u"], b["v"], b["o"], b["stereo"] = u, v, 1, stereo
                else:
                    b["o"] = (b["o"] % 3) + 1 if (cycle and b["o"] == order and not b.get("stereo")) else order
                    b["stereo"] = 0
                return
        nb = {"u": u, "v": v, "o": 1 if stereo else order}
        if stereo:
            nb["stereo"] = stereo
        self.mol.bonds.append(nb)

    def _ring_geometry(self, n, center=None, atom=None, bond=None):
        """Tính danh sách đỉnh (wx, wy) của vòng n cạnh khi đặt tại chỗ trống / nguyên tử / liên kết."""
        R = 1.0 / (2 * math.sin(math.pi / n))
        if bond is not None and 0 <= bond < len(self.mol.bonds):
            b = self.mol.bonds[bond]
            a1, a2 = self.mol.atoms[b["u"]], self.mol.atoms[b["v"]]
            mx, my = (a1["x"] + a2["x"]) / 2, (a1["y"] + a2["y"]) / 2
            dx, dy = a2["x"] - a1["x"], a2["y"] - a1["y"]
            L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L, dx / L
            ap = R * math.cos(math.pi / n)
            c1 = (mx + nx * ap, my + ny * ap)
            c2 = (mx - nx * ap, my - ny * ap)
            cen = lambda c: sum(1 for q in self.mol.atoms if math.hypot(q["x"] - c[0], q["y"] - c[1]) < R * 1.1)  # noqa: E731
            center = c1 if cen(c1) <= cen(c2) else c2
            start = math.atan2(a1["y"] - center[1], a1["x"] - center[0])
        elif atom is not None and 0 <= atom < len(self.mol.atoms):
            a = self.mol.atoms[atom]
            ang = self.free_angle(atom)
            center = (a["x"] + R * math.cos(ang), a["y"] + R * math.sin(ang))
            start = math.atan2(a["y"] - center[1], a["x"] - center[0])
        elif center is not None:
            start = math.pi / 2 if n != 4 else math.pi / 4
        else:
            return []
        return [(center[0] + R * math.cos(start + 2 * math.pi * k / n),
                 center[1] + R * math.sin(start + 2 * math.pi * k / n)) for k in range(n)]

    def stamp_ring(self, n, arom, center=None, atom=None, bond=None):
        pts = self._ring_geometry(n, center=center, atom=atom, bond=bond)
        if not pts:
            return
        ids, new_flags = [], []
        for x, y in pts:
            found = next((i for i, q in enumerate(self.mol.atoms) if math.hypot(q["x"] - x, q["y"] - y) < 0.3), None)
            if found is None:
                found = self.mol.add_atom("C", 0, None, False, x, y)
                new_flags.append(True)
            else:
                new_flags.append(False)
            ids.append(found)
        for k in range(n):
            u, v = ids[k], ids[(k + 1) % n]
            exists = any({b["u"], b["v"]} == {u, v} for b in self.mol.bonds)
            if not exists:
                order = 2 if (arom and n % 2 == 0 and k % 2 == 0) or (arom and n == 5 and k in (0, 2)) else 1
                self.mol.bonds.append({"u": u, "v": v, "o": order})
        if arom and n == 6:
            self._fix_benzene(ids)

    def _fix_benzene(self, ids):
        bonds = {frozenset((b["u"], b["v"])): b for b in self.mol.bonds}
        ring_b = [bonds[frozenset((ids[k], ids[(k + 1) % 6]))] for k in range(6) if frozenset((ids[k], ids[(k + 1) % 6])) in bonds]
        if len(ring_b) != 6:
            return
        for pattern in (0, 1):
            if any(b["o"] == 3 for b in ring_b):
                continue
            for k, b in enumerate(ring_b):
                b["o"] = 2 if k % 2 == pattern else 1
            break

    def attach_group(self, i, frag_smiles):
        a = self.mol.atoms[i]
        ang = self.free_angle(i)
        frag = mo.parse_smiles(frag_smiles)
        mo._layout_own(frag)
        e = frag.atoms[0]
        cx = sum(q["x"] for q in frag.atoms) / len(frag.atoms) - e["x"]
        cy = sum(q["y"] for q in frag.atoms) / len(frag.atoms) - e["y"]
        grow = math.atan2(cy, cx) if (abs(cx) + abs(cy)) > 1e-6 else 0.0
        rot = ang - grow if len(frag.atoms) > 1 and (abs(cx) + abs(cy)) > 1e-6 else 0.0
        base = len(self.mol.atoms)
        px, py = a["x"] + math.cos(ang), a["y"] + math.sin(ang)
        for q in frag.atoms:
            dx, dy = q["x"] - e["x"], q["y"] - e["y"]
            self.mol.atoms.append({**q, "x": px + dx * math.cos(rot) - dy * math.sin(rot), "y": py + dx * math.sin(rot) + dy * math.cos(rot)})
        for b in frag.bonds:
            self.mol.bonds.append({"u": b["u"] + base, "v": b["v"] + base, "o": b["o"]})
        self.mol.bonds.append({"u": i, "v": base, "o": 1})

    def place_template(self, smi, wx, wy):
        frag = mo.parse_smiles(smi)
        mo.layout(frag, True)
        xs = [q["x"] for q in frag.atoms]
        ys = [q["y"] for q in frag.atoms]
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        base = len(self.mol.atoms)
        for q in frag.atoms:
            self.mol.atoms.append({**q, "x": q["x"] - cx + wx, "y": q["y"] - cy + wy})
        for b in frag.bonds:
            self.mol.bonds.append({"u": b["u"] + base, "v": b["v"] + base, "o": b["o"]})

    def delete_atoms(self, indices):
        rem = set(indices)
        if not rem:
            return
        remap = {}
        new_atoms = []
        for i, a in enumerate(self.mol.atoms):
            if i not in rem:
                remap[i] = len(new_atoms)
                new_atoms.append(a)
        new_bonds = []
        for b in self.mol.bonds:
            if b["u"] in rem or b["v"] in rem:
                continue
            nb = dict(b)
            nb["u"], nb["v"] = remap[b["u"]], remap[b["v"]]
            new_bonds.append(nb)
        self.mol.atoms, self.mol.bonds = new_atoms, new_bonds
        self.selected.clear()
        self.hover = None

    def delete_atom(self, i):
        self.delete_atoms({i})

    def _drag_target_point(self, i, pos):
        """Tính vị trí đích (wx, wy, target_atom_idx, angle_deg) khi đang kéo vẽ liên kết."""
        a = self.mol.atoms[i]
        s = self.w2s(a["x"], a["y"])
        target = self.atom_at(pos, 20)
        if target is not None and target != i:
            t = self.mol.atoms[target]
            ang = math.degrees(math.atan2(t["y"] - a["y"], t["x"] - a["x"]))
            return t["x"], t["y"], target, ang
        raw_ang = math.atan2(-(pos.y() - s.y()), pos.x() - s.x())
        step = math.pi / 12  # 15° snap
        ang = round(raw_ang / step) * step
        nx, ny = a["x"] + math.cos(ang), a["y"] + math.sin(ang)
        hit = next((k for k, q in enumerate(self.mol.atoms) if k != i and math.hypot(q["x"] - nx, q["y"] - ny) < 0.3), None)
        return nx, ny, hit, math.degrees(ang)

    # ------------------------------------------------------------------ chuột & menu
    def mousePressEvent(self, e):
        self.setFocus()
        pos = e.position()
        self.mouse_pos = pos
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self.tool == "pan"):
            self.pan = (pos, QPointF(self.origin))
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() != Qt.LeftButton:
            return
        t = self.tool
        ai = self.atom_at(pos)
        bi = None if ai is not None else self.bond_at(pos)
        wx, wy = self.s2w(pos)

        if t == "select":
            if ai is not None:
                if e.modifiers() & Qt.ShiftModifier:
                    if ai in self.selected:
                        self.selected.remove(ai)
                    else:
                        self.selected.add(ai)
                    self.update()
                    return
                if ai not in self.selected:
                    self.selected = {ai}
                self.push_undo()
                if e.modifiers() & Qt.ControlModifier:
                    self.moving = ("all", pos)
                else:
                    self.moving = ("sel", pos)
            else:
                if not (e.modifiers() & Qt.ShiftModifier):
                    self.selected.clear()
                self.sel_box = (pos, pos)
            self.update()
            return

        if t == "erase":
            if ai is not None or bi is not None:
                self.push_undo()
                if ai is not None:
                    self.delete_atom(ai)
                else:
                    self.mol.bonds.pop(bi)
                self.changed.emit()
                self.update()
            else:
                self.erase_box = (pos, pos)
                self.update()
            return

        if t in ("bond1", "bond2", "bond3", "wedge", "dash"):
            order = 1 if t in ("wedge", "dash") else int(t[-1])
            stereo = 1 if t == "wedge" else (-1 if t == "dash" else 0)
            if ai is None and bi is not None:
                self.push_undo()
                b = self.mol.bonds[bi]
                self.set_bond(b["u"], b["v"], order, cycle=(stereo == 0), stereo=stereo)
                self.changed.emit()
                self.update()
                return
            self.push_undo()
            if ai is None:
                ai = self.add_atom(*self._snap_xy(wx, wy), el="C")
            self.drag_from = ai
            self.drag_to = pos
            self.drag_moved = False
            self.update()
            return

        self.push_undo()
        if t == "atom":
            if ai is not None:
                self.mol.atoms[ai]["el"], self.mol.atoms[ai]["h"] = self.element, None
            elif bi is None:
                self.add_atom(*self._snap_xy(wx, wy), el=self.element)
        elif t == "ring":
            if ai is not None:
                self.stamp_ring(self.ring_n, self.ring_arom, atom=ai)
            elif bi is not None:
                self.stamp_ring(self.ring_n, self.ring_arom, bond=bi)
            else:
                self.stamp_ring(self.ring_n, self.ring_arom, center=(wx, wy))
        elif t == "group":
            frag = GROUPS.get(self.group, "O")
            if ai is not None:
                self.attach_group(ai, frag)
            elif bi is None:
                self.attach_group(self.add_atom(*self._snap_xy(wx, wy), el="C"), frag)
        elif t == "template" and self.template:
            if ai is not None:
                self.attach_group(ai, self.template)
            elif bi is None:
                self.place_template(self.template, wx, wy)
        elif t in ("plus", "minus") and ai is not None:
            self.mol.atoms[ai]["charge"] += 1 if t == "plus" else -1
            self.mol.atoms[ai]["h"] = None
        self.changed.emit()
        self.update()

    def _snap_xy(self, x, y):
        return round(x * 4) / 4, round(y * 4) / 4

    def mouseMoveEvent(self, e):
        pos = e.position()
        self.mouse_pos = pos
        if self.pan and (e.buttons() & (Qt.MiddleButton | Qt.LeftButton)):
            self.origin = self.pan[1] + (pos - self.pan[0])
            self.update()
            return
        if self.erase_box is not None and (e.buttons() & Qt.LeftButton):
            self.erase_box = (self.erase_box[0], pos)
            self.update()
            return
        if self.sel_box is not None and (e.buttons() & Qt.LeftButton):
            self.sel_box = (self.sel_box[0], pos)
            r = QRectF(self.sel_box[0], pos).normalized()
            self.selected = {i for i, a in enumerate(self.mol.atoms) if r.contains(self.w2s(a["x"], a["y"]))}
            self.update()
            return
        if self.moving and (e.buttons() & Qt.LeftButton):
            p0 = self.moving[1]
            dx, dy = (pos.x() - p0.x()) / self.L, -(pos.y() - p0.y()) / self.L
            targets = range(len(self.mol.atoms)) if self.moving[0] == "all" else self.selected
            for i in targets:
                if i < len(self.mol.atoms):
                    self.mol.atoms[i]["x"] += dx
                    self.mol.atoms[i]["y"] += dy
            self.moving = (self.moving[0], pos)
            self.changed.emit()
        elif self.drag_from is not None:
            self.drag_to = pos
            self.drag_moved = True
            t = self.atom_at(pos, 20)
            self.hover = ("a", t) if (t is not None and t != self.drag_from) else None
        else:
            ai = self.atom_at(pos)
            bi = None if ai is not None else self.bond_at(pos)
            self.hover = ("a", ai) if ai is not None else (("b", bi) if bi is not None else None)
        self.update()

    def mouseReleaseEvent(self, e):
        if self.pan is not None:
            self.pan = None
            self.setCursor(Qt.OpenHandCursor if self.tool == "pan" else Qt.ArrowCursor)
            return
        if self.erase_box is not None:
            r = QRectF(self.erase_box[0], self.erase_box[1]).normalized()
            self.erase_box = None
            if r.width() >= 6 or r.height() >= 6:
                kill_atoms = {i for i, a in enumerate(self.mol.atoms) if r.contains(self.w2s(a["x"], a["y"]))}
                kill_bonds = [
                    k for k, b in enumerate(self.mol.bonds)
                    if b["u"] not in kill_atoms and b["v"] not in kill_atoms and r.contains(
                        QPointF(
                            (self.w2s(self.mol.atoms[b["u"]]["x"], self.mol.atoms[b["u"]]["y"]).x() + self.w2s(self.mol.atoms[b["v"]]["x"], self.mol.atoms[b["v"]]["y"]).x()) / 2,
                            (self.w2s(self.mol.atoms[b["u"]]["x"], self.mol.atoms[b["u"]]["y"]).y() + self.w2s(self.mol.atoms[b["v"]]["x"], self.mol.atoms[b["v"]]["y"]).y()) / 2,
                        )
                    )
                ]
                if kill_atoms or kill_bonds:
                    self.push_undo()
                    for k in sorted(kill_bonds, reverse=True):
                        self.mol.bonds.pop(k)
                    if kill_atoms:
                        self.delete_atoms(kill_atoms)
                    self.changed.emit()
                    self.status.emit(f"Đã xóa vùng chọn ({len(kill_atoms)} nguyên tử, {len(kill_bonds)} liên kết).")
            self.update()
            return
        if self.sel_box is not None:
            self.sel_box = None
            self.update()
            return
        if self.moving:
            self.moving = None
            return
        if self.drag_from is None:
            return
        i, pos = self.drag_from, e.position()
        self.drag_from = None
        self.hover = None
        order = 1 if self.tool in ("wedge", "dash") else int(self.tool[-1])
        stereo = 1 if self.tool == "wedge" else (-1 if self.tool == "dash" else 0)
        a = self.mol.atoms[i]
        s = self.w2s(a["x"], a["y"])
        dist = math.hypot(pos.x() - s.x(), pos.y() - s.y())
        if dist < 14:
            ang = self.free_angle(i)
            nx, ny = a["x"] + math.cos(ang), a["y"] + math.sin(ang)
            hit = next((k for k, q in enumerate(self.mol.atoms) if k != i and math.hypot(q["x"] - nx, q["y"] - ny) < 0.3), None)
            if hit is None:
                hit = self.add_atom(nx, ny, el="C")
            self.set_bond(i, hit, order, stereo=stereo)
        else:
            nx, ny, hit, _ = self._drag_target_point(i, pos)
            if hit is None:
                hit = self.add_atom(nx, ny, el="C")
            self.set_bond(i, hit, order, stereo=stereo)
        self.changed.emit()
        self.update()

    def wheelEvent(self, e):
        f = 1.14 if e.angleDelta().y() > 0 else 1 / 1.14
        pos = e.position()
        wx, wy = self.s2w(pos)
        self.L = max(8.0, min(160.0, self.L * f))
        self.origin = QPointF(pos.x() - wx * self.L, pos.y() + wy * self.L)
        self.update()

    def contextMenuEvent(self, e):
        pos = QPointF(e.pos())
        ai = self.atom_at(pos)
        bi = None if ai is not None else self.bond_at(pos)
        m = QMenu(self)
        if ai is not None:
            sub_el = m.addMenu("Đổi nguyên tố")
            for el in ("C", "H", "N", "O", "S", "P", "F", "Cl", "Br", "I"):
                sub_el.addAction(el).triggered.connect(lambda _, e_=el: self._set_atom_el(ai, e_))
            sub_el.addSeparator()
            sub_el.addAction("Nguyên tố khác…").triggered.connect(lambda: self._prompt_atom_el(ai))
            sub_g = m.addMenu("Gắn nhanh nhóm chức")
            for lab, key in QUICK_GROUPS:
                sub_g.addAction(lab).triggered.connect(lambda _, k=key: self._ctx_attach(ai, GROUPS[k]))
            m.addSeparator()
            m.addAction("Điện tích +1").triggered.connect(lambda: self._set_charge(ai, 1))
            m.addAction("Điện tích −1").triggered.connect(lambda: self._set_charge(ai, -1))
            m.addAction("Đặt điện tích về 0").triggered.connect(lambda: self._set_charge(ai, 0, absolute=True))
            m.addSeparator()
            m.addAction("Xóa nguyên tử").triggered.connect(lambda: (self.push_undo(), self.delete_atom(ai), self.changed.emit(), self.update()))
        elif bi is not None:
            b = self.mol.bonds[bi]
            m.addAction("Liên kết đơn ─").triggered.connect(lambda: self._set_bond_props(bi, 1, 0))
            m.addAction("Liên kết đôi ═").triggered.connect(lambda: self._set_bond_props(bi, 2, 0))
            m.addAction("Liên kết ba ≡").triggered.connect(lambda: self._set_bond_props(bi, 3, 0))
            m.addSeparator()
            m.addAction("Nêm đặc ▸ (hướng ra)").triggered.connect(lambda: self._set_bond_props(bi, 1, 1))
            m.addAction("Nêm đứt ┄ (hướng vào)").triggered.connect(lambda: self._set_bond_props(bi, 1, -1))
            if b.get("stereo"):
                m.addAction("Đảo chiều nêm").triggered.connect(lambda: self._flip_bond_dir(bi))
            m.addSeparator()
            m.addAction("Xóa liên kết").triggered.connect(lambda: (self.push_undo(), self.mol.bonds.pop(bi), self.changed.emit(), self.update()))
        else:
            m.addAction("Chuẩn hóa bố cục 2D").triggered.connect(self.clean)
            m.addAction("Căn giữa & vừa khung").triggered.connect(self.center_view)
            m.addSeparator()
            m.addAction("Xoay phải 15°").triggered.connect(lambda: self.rotate_mol(-15))
            m.addAction("Xoay trái 15°").triggered.connect(lambda: self.rotate_mol(15))
            m.addAction("Lật ngang").triggered.connect(lambda: self.flip_mol(True))
            m.addAction("Lật dọc").triggered.connect(lambda: self.flip_mol(False))
            m.addSeparator()
            m.addAction("Dán SMILES từ clipboard").triggered.connect(self._paste_smiles)
        m.exec(e.globalPos())

    def _set_atom_el(self, ai, el):
        self.push_undo()
        self.mol.atoms[ai]["el"], self.mol.atoms[ai]["h"] = el, None
        self.changed.emit()
        self.update()

    def _prompt_atom_el(self, ai):
        sym, ok = QInputDialog.getText(self, "Nguyên tố", "Nhập kí hiệu nguyên tố (VD: Fe, Cu, Si):")
        sym = sym.strip().capitalize()
        if ok and sym in ds.ATOMIC_MASSES:
            self._set_atom_el(ai, sym)

    def _ctx_attach(self, ai, smi):
        self.push_undo()
        self.attach_group(ai, smi)
        self.changed.emit()
        self.update()

    def _set_charge(self, ai, delta, absolute=False):
        self.push_undo()
        self.mol.atoms[ai]["charge"] = delta if absolute else self.mol.atoms[ai]["charge"] + delta
        self.mol.atoms[ai]["h"] = None
        self.changed.emit()
        self.update()

    def _set_bond_props(self, bi, order, stereo):
        self.push_undo()
        self.mol.bonds[bi]["o"] = order
        self.mol.bonds[bi]["stereo"] = stereo
        self.changed.emit()
        self.update()

    def _flip_bond_dir(self, bi):
        self.push_undo()
        b = self.mol.bonds[bi]
        b["u"], b["v"] = b["v"], b["u"]
        self.changed.emit()
        self.update()

    def _paste_smiles(self):
        txt = QGuiApplication.clipboard().text().strip()
        if not txt:
            return
        try:
            mol, note, _ = mo.make_mol(txt, True)
            self.load_mol(mol)
            self.status.emit(note or "Đã dán cấu trúc từ clipboard.")
        except Exception as exc:
            self.status.emit(f"Clipboard không phải SMILES hợp lệ: {exc}")

    def keyPressEvent(self, e):
        k = e.key()
        mod = e.modifiers()
        if k == Qt.Key_Z and (mod & Qt.ControlModifier):
            if mod & Qt.ShiftModifier:
                self.redo()
            else:
                self.undo()
            return
        if k == Qt.Key_Y and (mod & Qt.ControlModifier):
            self.redo()
            return
        if k == Qt.Key_A and (mod & Qt.ControlModifier):
            self.selected = set(range(len(self.mol.atoms)))
            self.update()
            return
        if k in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.selected:
                self.push_undo()
                self.delete_atoms(self.selected)
                self.changed.emit()
                self.update()
            elif self.hover:
                self.push_undo()
                if self.hover[0] == "a":
                    self.delete_atom(self.hover[1])
                else:
                    self.mol.bonds.pop(self.hover[1])
                self.hover = None
                self.changed.emit()
                self.update()
            return
        if k == Qt.Key_Space:
            self.center_view()
            return
        if k == Qt.Key_Escape:
            self.selected.clear()
            self.set_tool("select")
            return
        if k in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_by(1.15)
            return
        if k == Qt.Key_Minus:
            self.zoom_by(1 / 1.15)
            return

        # Phím tắt kiểu ChemDraw khi đang rê chuột lên nguyên tử hoặc liên kết
        if not (mod & (Qt.ControlModifier | Qt.AltModifier)):
            el_keys = {
                Qt.Key_C: "C", Qt.Key_N: "N", Qt.Key_O: "O", Qt.Key_S: "S",
                Qt.Key_P: "P", Qt.Key_F: "F", Qt.Key_B: "B", Qt.Key_H: "H",
                Qt.Key_I: "I", Qt.Key_L: "Cl", Qt.Key_R: "Br",
            }
            if self.hover and self.hover[0] == "a" and k in el_keys:
                self._set_atom_el(self.hover[1], el_keys[k])
                self.status.emit(f"Đã đổi nguyên tử thành {el_keys[k]}")
                return
            if self.hover and self.hover[0] == "b":
                if k == Qt.Key_1:
                    self._set_bond_props(self.hover[1], 1, 0)
                    return
                if k == Qt.Key_2:
                    self._set_bond_props(self.hover[1], 2, 0)
                    return
                if k == Qt.Key_3:
                    self._set_bond_props(self.hover[1], 3, 0)
                    return
                if k == Qt.Key_4:
                    self._set_bond_props(self.hover[1], 1, 1)
                    return
                if k == Qt.Key_5:
                    self._set_bond_props(self.hover[1], 1, -1)
                    return
            # Chuyển công cụ nhanh bằng phím số / chữ
            tool_keys = {
                Qt.Key_1: "bond1", Qt.Key_2: "bond2", Qt.Key_3: "bond3",
                Qt.Key_4: "wedge", Qt.Key_5: "dash", Qt.Key_V: "select", Qt.Key_E: "erase", Qt.Key_H: "pan",
            }
            if k in tool_keys:
                self.set_tool(tool_keys[k])
                return

    # ------------------------------------------------------------------ vẽ
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        bgc = QColor(self.bg_hex)
        p.fillRect(self.rect(), bgc)

        if self.show_grid:
            self._draw_dot_grid(p)

        if not self.mol.atoms and self.tool != "ring":
            import i18n
            p.setPen(QColor("#64748B" if self.dark else "#94A3B8"))
            p.setFont(QFont("Segoe UI", 10.5))
            empty_txt = (
                "Click anywhere on the canvas to start drawing a molecule\n\n"
                "Quick tip: pick Benzene on the left dock and click • Hover an atom and press C, N, O, L (Cl), or R (Br) to switch elements"
                if i18n.is_en() else
                "Nhấp vào vùng vẽ để bắt đầu dựng cấu trúc phân tử\n\n"
                "Mẹo nhanh: chọn vòng Benzene ở thanh trái rồi nhấp • Rê chuột lên nguyên tử và bấm C, N, O, Cl (L), Br (R) để đổi nhanh"
            )
            p.drawText(self.rect().adjusted(28, 12, -28, -12), Qt.AlignCenter | Qt.TextWordWrap, empty_txt)
        if self.mol.atoms:
            self._draw_molecule(p, interactive=True)

        # Xem trước bóng mờ cho công cụ Vòng (ring)
        if self.tool == "ring" and self.rect().contains(self.mouse_pos.toPoint()):
            self._draw_ring_ghost(p)

        # Khung chọn vùng
        if self.sel_box is not None:
            r = QRectF(self.sel_box[0], self.sel_box[1]).normalized()
            p.setPen(QPen(QColor("#4F46E5"), 1.3, Qt.DashLine))
            p.setBrush(QColor(79, 70, 229, 28))
            p.drawRect(r)

        # Khung khoanh vùng xóa (màu đỏ cảnh báo + tô đỏ nguyên tử sắp xóa)
        if self.erase_box is not None:
            r = QRectF(self.erase_box[0], self.erase_box[1]).normalized()
            p.setPen(QPen(QColor("#EF4444"), 1.6, Qt.DashLine))
            p.setBrush(QColor(239, 68, 68, 30))
            p.drawRect(r)
            for i, a in enumerate(self.mol.atoms):
                s = self.w2s(a["x"], a["y"])
                if r.contains(s):
                    p.setPen(QPen(QColor("#EF4444"), 2.0))
                    p.setBrush(QColor(239, 68, 68, 70))
                    p.drawEllipse(s, 13, 13)

        # HUD góc dưới trái: mức thu phóng + phím tắt ngữ cảnh
        self._draw_hud(p)

    def _draw_dot_grid(self, p):
        step = self.L * 0.5
        while step < 18:
            step *= 2
        while step > 56:
            step /= 2
        dot_c = QColor(self.dot_hex)
        p.setPen(QPen(dot_c, 1.4))
        ox = self.origin.x() % step
        oy = self.origin.y() % step
        w, h = self.width(), self.height()
        x = ox
        while x < w:
            y = oy
            while y < h:
                p.drawPoint(QPointF(x, y))
                y += step
            x += step

    def _draw_ring_ghost(self, p):
        ai = self.atom_at(self.mouse_pos)
        bi = None if ai is not None else self.bond_at(self.mouse_pos)
        if ai is not None:
            pts = self._ring_geometry(self.ring_n, atom=ai)
        elif bi is not None:
            pts = self._ring_geometry(self.ring_n, bond=bi)
        else:
            pts = self._ring_geometry(self.ring_n, center=self.s2w(self.mouse_pos))
        if not pts:
            return
        spts = [self.w2s(x, y) for x, y in pts]
        col = QColor("#38BDF8" if self.dark else "#4F46E5")
        col_fill = QColor(col)
        col_fill.setAlpha(22)
        col.setAlpha(155)
        p.setPen(QPen(col, 1.8, Qt.DashLine))
        p.setBrush(col_fill)
        p.drawPolygon(QPolygonF(spts))

    def _draw_hud(self, p):
        import i18n
        en = i18n.is_en()
        zoom_pct = int(round(self.L / 52.0 * 100))
        txt = f"{zoom_pct}%"
        if self.tool == "pan":
            txt += "  ·  Drag canvas to pan" if en else "  ·  Kéo chuột trái để di chuyển vùng vẽ"
        elif self.selected:
            txt += f"  ·  {len(self.selected)} atoms selected" if en else f"  ·  Đang chọn {len(self.selected)} nguyên tử"
        over_n = self.valence_warnings()
        if self.check_valence and over_n:
            txt += f"  ·  ⚠ {over_n} valence warning(s)" if en else f"  ·  ⚠ {over_n} nguyên tử vượt hóa trị"
        font = QFont("Segoe UI", 8.5, QFont.DemiBold)
        p.setFont(font)
        fm = QFontMetricsF(font)
        tw = fm.horizontalAdvance(txt) + 18
        rect = QRectF(10, self.height() - 30, tw, 22)
        bg = QColor(15, 23, 42, 185) if self.dark else QColor(248, 250, 252, 225)
        bd = QColor("#334155") if self.dark else QColor("#CBD5E1")
        p.setPen(QPen(bd, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, 7, 7)
        p.setPen(QColor("#F87171" if (self.check_valence and over_n) else ("#CBD5E1" if self.dark else "#475569")))
        p.drawText(rect, Qt.AlignCenter, txt)

    def valence_warnings(self):
        if not self.mol.atoms:
            return 0
        adj = self.mol.adj()
        cnt = 0
        for i, a in enumerate(self.mol.atoms):
            bond_sum = sum(self.mol.bond_order(i, n) for n in adj[i])
            vals = mo.CHARGED_VAL.get((a["el"], a["charge"])) if a["charge"] else mo.ORGANIC_VAL.get(a["el"])
            if vals and a["h"] is None and bond_sum > max(vals):
                cnt += 1
        return cnt

    def _draw_molecule(self, p, interactive=True):
        font = QFont("Segoe UI", 1)
        font.setPixelSize(max(10, int(self.L * 0.36)))
        fm = QFontMetricsF(font)
        scene = mo.build_scene(self.mol, lambda t: fm.horizontalAdvance(t) / self.L if t else 0.0, self.show_ch3, self.mono, self.dark, self.cmode, self.ring_c)
        lw = max(1.6, self.L * 0.036)

        # Vẽ liên kết nêm đặc (wedges)
        for (p1, p2, p3, col) in scene.get("wedges", ()):
            p.setPen(QPen(QColor(col), lw * 0.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(QBrush(QColor(col)))
            p.drawPolygon(QPolygonF([self.w2s(*p1), self.w2s(*p2), self.w2s(*p3)]))
        p.setBrush(Qt.NoBrush)

        # Vẽ liên kết thường & nêm đứt
        for (x1, y1, x2, y2, col, dashed) in scene["lines"]:
            pen = QPen(QColor(col), lw)
            pen.setCapStyle(Qt.RoundCap)
            if dashed:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawLine(self.w2s(x1, y1), self.w2s(x2, y2))

        p.setFont(font)
        for t in scene["texts"]:
            s = self.w2s(t["x"], t["y"])
            p.setPen(QColor(t["color"]))
            p.drawText(QPointF(s.x(), s.y() + (fm.ascent() - fm.descent()) / 2), t["text"])

        if not interactive:
            return

        # Highlight các nguyên tử đang chọn
        for i in self.selected:
            if i < len(self.mol.atoms):
                s = self.w2s(self.mol.atoms[i]["x"], self.mol.atoms[i]["y"])
                p.setPen(QPen(QColor("#4F46E5" if not self.dark else "#818CF8"), 2))
                p.setBrush(QColor(79, 70, 229, 36))
                p.drawEllipse(s, 14, 14)

        # Cảnh báo vượt hóa trị
        if self.check_valence:
            adj = self.mol.adj()
            for i, a in enumerate(self.mol.atoms):
                bond_sum = sum(self.mol.bond_order(i, n) for n in adj[i])
                vals = mo.CHARGED_VAL.get((a["el"], a["charge"])) if a["charge"] else mo.ORGANIC_VAL.get(a["el"])
                if vals and a["h"] is None and bond_sum > max(vals):
                    s = self.w2s(a["x"], a["y"])
                    p.setPen(QPen(QColor("#EF4444"), 2, Qt.DashLine))
                    p.setBrush(QColor(239, 68, 68, 28))
                    p.drawEllipse(s, 15, 15)

        # Highlight liên kết khi rê chuột
        if self.hover and self.hover[0] == "b" and self.hover[1] < len(self.mol.bonds):
            b = self.mol.bonds[self.hover[1]]
            p1 = self.w2s(self.mol.atoms[b["u"]]["x"], self.mol.atoms[b["u"]]["y"])
            p2 = self.w2s(self.mol.atoms[b["v"]]["x"], self.mol.atoms[b["v"]]["y"])
            col_h = QColor(239, 68, 68, 95) if self.tool == "erase" else QColor(245, 158, 11, 75)
            col_c = QColor(239, 68, 68, 210) if self.tool == "erase" else QColor(245, 158, 11, 195)
            p.setPen(QPen(col_h, 12, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(p1, p2)
            p.setPen(QPen(col_c, 3.8, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(p1, p2)

        # Xem trước liên kết đang kéo (snap góc 15° + hiển thị góc)
        if self.drag_from is not None and self.drag_from < len(self.mol.atoms):
            a = self.mol.atoms[self.drag_from]
            sp1 = self.w2s(a["x"], a["y"])
            self._glow(p, sp1, QColor("#38BDF8"), strong=True)
            if math.hypot(self.drag_to.x() - sp1.x(), self.drag_to.y() - sp1.y()) >= 14:
                nx, ny, hit, ang_deg = self._drag_target_point(self.drag_from, self.drag_to)
                sp2 = self.w2s(nx, ny)
                pen = QPen(QColor("#38BDF8"), 2.4, Qt.DashLine)
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.drawLine(sp1, sp2)
                p.setBrush(QColor(56, 189, 248, 60))
                p.drawEllipse(sp2, 6, 6)
                # nhãn góc gọn
                p.setFont(QFont("Segoe UI", 8.5, QFont.Bold))
                p.setPen(QColor("#38BDF8" if self.dark else "#0284C7"))
                mid = QPointF((sp1.x() + sp2.x()) / 2 + 8, (sp1.y() + sp2.y()) / 2 - 8)
                p.drawText(mid, f"{int(round(ang_deg)) % 360}°")

        # Điểm đang rê chuột
        if self.hover and self.hover[0] == "a" and self.hover[1] is not None and self.hover[1] < len(self.mol.atoms):
            a = self.mol.atoms[self.hover[1]]
            col = QColor("#EF4444") if self.tool == "erase" else (QColor("#34D399") if self.drag_from is not None else QColor("#F59E0B"))
            self._glow(p, self.w2s(a["x"], a["y"]), col, strong=self.drag_from is not None)

    def _glow(self, p, c, color, strong=False):
        r = 28 if strong else 23
        g = QRadialGradient(c, r)
        c0, c1, c2 = QColor(color), QColor(color), QColor(color)
        c0.setAlpha(145 if strong else 105)
        c1.setAlpha(50)
        c2.setAlpha(0)
        g.setColorAt(0.0, c0)
        g.setColorAt(0.55, c1)
        g.setColorAt(1.0, c2)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(c, r, r)
        ring = QColor(color)
        ring.setAlpha(235)
        p.setPen(QPen(ring, 2.0))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, 12.5, 12.5)

    # ------------------------------------------------------------------ đầu ra
    def smiles(self):
        return mo.to_smiles(self.mol)

    def info(self):
        if not self.mol.atoms:
            return "", 0.0, []
        counts = self.mol.formula_counts()
        return self.mol.formula(True), self.mol.mass(), identify_formula(counts)

    def composition(self):
        if not self.mol.atoms:
            return []
        counts = self.mol.formula_counts()
        total = self.mol.mass() or 1.0
        return [(el, n, ds.ATOMIC_MASSES.get(el, 0.0) * n / total * 100.0) for el, n in counts.items()]

    def export_bytes(self, fmt, bg="transparent"):
        return mo.render_mol_bytes(self.mol, fmt, bg, self.mono, self.show_ch3, cmode=self.cmode, ring_c=self.ring_c)
