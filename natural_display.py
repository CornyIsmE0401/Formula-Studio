# -*- coding: utf-8 -*-
"""natural_display.py - Ô nhập/hiển thị biểu thức dạng "natural display" (như Casio fx-580VN X, Casio online).

Biểu thức là một cây: mỗi hàng (Row) là danh sách nút; nút có thể là ký tự hoặc mẫu (phân số, căn, mũ, trị tuyệt đối,
hàm có ngoặc). Bấm phím chức năng sẽ chèn đúng mẫu công thức, con trỏ nhảy vào ô trống đầu tiên.
Biểu thức được chuyển thành chuỗi cho calc_engine bằng to_text().
"""
import re

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

FUNCS = ["sinh", "cosh", "tanh", "asin", "acos", "atan", "sin", "cos", "tan", "log10", "log2", "ln", "log", "exp", "cbrt", "nCr", "nPr", "Pol", "Rec",
         "gcd", "lcm", "floor", "ceil", "round", "sign", "re", "im", "conj", "arg", "max", "min", "sec", "csc", "cot", "fact"]
DISPLAY_NAME = {"asin": "sin⁻¹", "acos": "cos⁻¹", "atan": "tan⁻¹", "cbrt": "∛"}


class Incomplete(Exception):
    """Biểu thức còn ô trống."""


class Row(list):
    def __init__(self, *a):
        super().__init__(*a)
        self.node = None          # nút chứa hàng này (None = hàng gốc)


class Node:
    def __init__(self, kind, disp="", ins=None, nslots=0, name=""):
        self.kind = kind          # ch | frac | sqrt | root | sup | sub | abs | func
        self.disp = disp
        self.ins = disp if ins is None else ins
        self.name = name
        self.slots = []
        for _ in range(nslots):
            r = Row()
            r.node = self
            self.slots.append(r)

    def to_data(self):
        if self.kind == "ch":
            return ["ch", self.disp, self.ins]
        return [self.kind, self.name, [[n.to_data() for n in s] for s in self.slots]]

    @staticmethod
    def from_data(d):
        if d[0] == "ch":
            return Node("ch", d[1], d[2])
        if d[0] == "grid":
            n = Node("grid", name=d[1], nslots=len(d[2]))
        else:
            nslots = {"frac": 2, "sqrt": 1, "root": 2, "sup": 1, "sub": 1, "abs": 1, "func": 1, "accent": 1, "binom": 2, "rm": 1}[d[0]]
            n = Node(d[0], name=d[1], nslots=nslots)
        for slot, items in zip(n.slots, d[2]):
            for it in items:
                slot.append(Node.from_data(it))
        return n


def _ch(c):
    m = {"-": ("−", "-"), "*": ("×", "*"), "/": ("÷", "/")}
    if c in m:
        return Node("ch", *m[c])
    return Node("ch", c)


# ----------------------------------------------------------------------------- chuyển sang chuỗi cho engine
def ser_row(row):
    parts = []
    for i, n in enumerate(row):
        s = ser_node(n)
        if parts and _needs_mul(parts[-1], row[i - 1], s, n):
            parts.append("*")
        parts.append(s)
    return "".join(parts)


_TPL = ("frac", "sqrt", "root", "abs", "func")


def _needs_mul(prev_s, prev_n, s, n):
    """Chèn dấu nhân tường minh khi một mẫu (căn, phân số, hàm…) đứng sát một toán hạng."""
    if not prev_s or not s:
        return False
    if prev_n.kind in _TPL or prev_n.kind == "sup":
        return n.kind == "ch" and (s[0].isdigit() or s[0] in "(π" or s[0].isalpha())
    if n.kind in _TPL:
        return prev_n.kind == "ch" and (prev_s[-1] in "0123456789)!%π" or prev_s[-1].isalpha())
    return False


def ser_node(n):
    if n.kind == "ch":
        return n.ins
    for s in n.slots:
        if not s:
            raise Incomplete()
    if n.kind == "frac":
        return f"(({ser_row(n.slots[0])})/({ser_row(n.slots[1])}))"
    if n.kind == "sqrt":
        return f"sqrt({ser_row(n.slots[0])})"
    if n.kind == "root":
        return f"root({ser_row(n.slots[0])},{ser_row(n.slots[1])})"
    if n.kind == "sup":
        return f"^({ser_row(n.slots[0])})"
    if n.kind == "sub":
        return f"_({ser_row(n.slots[0])})"
    if n.kind == "abs":
        return f"abs({ser_row(n.slots[0])})"
    if n.kind == "func":
        return f"{n.name}({ser_row(n.slots[0])})"
    return ""


_SUP = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
_SUB = str.maketrans("0123456789-+", "₀₁₂₃₄₅₆₇₈₉₋₊")


def disp_row(row):
    out = []
    for n in row:
        k = n.kind
        if k == "ch":
            out.append(n.disp)
        elif k == "frac":
            out.append(f"({disp_row(n.slots[0])})/({disp_row(n.slots[1])})")
        elif k == "sqrt":
            out.append(f"√({disp_row(n.slots[0])})")
        elif k == "root":
            out.append(f"{disp_row(n.slots[0]).translate(_SUP)}√({disp_row(n.slots[1])})")
        elif k == "sup":
            t = disp_row(n.slots[0])
            out.append(t.translate(_SUP) if re.fullmatch(r"[0-9−\-+]+", t) else f"^({t})")
        elif k == "sub":
            t = disp_row(n.slots[0])
            out.append(t.translate(_SUB) if re.fullmatch(r"[0-9−\-+]+", t) else f"_({t})")
        elif k == "abs":
            out.append(f"|{disp_row(n.slots[0])}|")
        elif k == "func":
            out.append(f"{DISPLAY_NAME.get(n.name, n.name)}({disp_row(n.slots[0])})")
    return "".join(out)


# ----------------------------------------------------------------------------- chuyển đổi 2 chiều WYSIWYG <-> LaTeX
_LATEX_TO_UNI = {
    "pm": "±", "mp": "∓", "times": "×", "cdot": "·", "div": "÷",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠",
    "approx": "≈", "equiv": "≡", "propto": "∝", "sim": "∼", "cong": "≅",
    "perp": "⊥", "parallel": "∥", "angle": "∠", "triangle": "△",
    "infty": "∞", "circ": "°", "dots": "…", "ldots": "…", "cdots": "…",
    "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆",
    "cup": "∪", "cap": "∩", "emptyset": "∅", "forall": "∀", "exists": "∃",
    "Rightarrow": "⇒", "Leftrightarrow": "⇔", "to": "→", "rightarrow": "→", "leftarrow": "←",
    "partial": "∂", "nabla": "∇", "hbar": "ℏ", "ell": "ℓ",
    "langle": "⟨", "rangle": "⟩", "mid": "∣",
    "sum": "∑", "int": "∫", "iint": "∬", "iiint": "∭", "oint": "∮", "prod": "∏",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "Delta": "Δ",
    "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "Theta": "Θ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "Lambda": "Λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "pi": "π", "Pi": "Π", "rho": "ρ", "sigma": "σ", "Sigma": "Σ",
    "tau": "τ", "phi": "φ", "varphi": "φ", "Phi": "Φ", "chi": "χ", "psi": "ψ", "Psi": "Ψ",
    "omega": "ω", "Omega": "Ω", "Gamma": "Γ",
}

_BIG_OPS = {"∑", "∫", "∬", "∭", "∮", "∏"}
_MATHBB_MAP = {"R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ"}

_UNI_TO_LATEX = {
    "±": r"\pm ", "∓": r"\mp ", "×": r"\times ", "·": r"\cdot ", "÷": r"\div ",
    "−": "-", "≤": r"\leq ", "≥": r"\geq ", "≠": r"\neq ", "≈": r"\approx ",
    "≡": r"\equiv ", "∝": r"\propto ", "∼": r"\sim ", "≅": r"\cong ",
    "⊥": r"\perp ", "∥": r"\parallel ", "∠": r"\angle ", "△": r"\triangle ",
    "∞": r"\infty ", "°": r"^\circ ", "…": r"\dots ",
    "∈": r"\in ", "∉": r"\notin ", "⊂": r"\subset ", "⊆": r"\subseteq ",
    "∪": r"\cup ", "∩": r"\cap ", "∅": r"\emptyset ", "∀": r"\forall ", "∃": r"\exists ",
    "⇒": r"\Rightarrow ", "⇔": r"\Leftrightarrow ", "→": r"\to ", "←": r"\leftarrow ",
    "∂": r"\partial ", "∇": r"\nabla ", "ℏ": r"\hbar ", "ℓ": r"\ell ",
    "⟨": r"\langle ", "⟩": r"\rangle ", "∣": r"\mid ", "%": r"\%",
    "∑": r"\sum", "∫": r"\int", "∬": r"\iint", "∭": r"\iiint", "∮": r"\oint", "∏": r"\prod",
    "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}", "ℤ": r"\mathbb{Z}", "ℚ": r"\mathbb{Q}", "ℂ": r"\mathbb{C}",
    "α": r"\alpha ", "β": r"\beta ", "γ": r"\gamma ", "δ": r"\delta ", "Δ": r"\Delta ",
    "ε": r"\varepsilon ", "ζ": r"\zeta ", "η": r"\eta ", "θ": r"\theta ", "Θ": r"\Theta ",
    "ι": r"\iota ", "κ": r"\kappa ", "λ": r"\lambda ", "Λ": r"\Lambda ", "μ": r"\mu ", "ν": r"\nu ",
    "ξ": r"\xi ", "π": r"\pi ", "Pi": r"\Pi ", "Π": r"\Pi ", "ρ": r"\rho ", "σ": r"\sigma ", "Σ": r"\Sigma ",
    "τ": r"\tau ", "φ": r"\varphi ", "Φ": r"\Phi ", "χ": r"\chi ", "ψ": r"\psi ", "Psi": r"\Psi ", "Ψ": r"\Psi ",
    "ω": r"\omega ", "Omega": r"\Omega ", "Ω": r"\Omega ", "Γ": r"\Gamma ",
}

_LATEX_FUNCS = {
    "sin", "cos", "tan", "cot", "sec", "csc",
    "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh",
    "ln", "lg", "log", "exp", "det", "max", "min", "lim", "gcd", "deg",
}

_GRID_ENVS = {"bmatrix", "pmatrix", "vmatrix", "Bmatrix", "matrix", "cases"}

_UNSUPPORTED_LATEX = re.compile(
    r"\\(?:choose|over|stackrel|xrightarrow|ce|pu|color|tag)\b"
)


def _grid_spec(name):
    parts = (name or "bmatrix:2:2").split(":")
    env = parts[0]
    rows = int(parts[1]) if len(parts) > 1 else 2
    cols = int(parts[2]) if len(parts) > 2 else 2
    return env, rows, cols


def _split_top_level(s: str, sep: str):
    """Tách chuỗi theo sep (VD '\\\\' hoặc '&') ở mức ngoặc/môi trường ngoài cùng."""
    out, buf = [], []
    i, n, depth, env_depth = 0, len(s), 0, 0
    L = len(sep)
    while i < n:
        if s.startswith(r"\begin{", i):
            env_depth += 1
            buf.append(r"\begin{")
            i += 7
            continue
        if s.startswith(r"\end{", i):
            env_depth = max(0, env_depth - 1)
            buf.append(r"\end{")
            i += 5
            continue
        if depth == 0 and env_depth == 0 and s.startswith(sep, i):
            out.append("".join(buf))
            buf = []
            i += L
            continue
        c = s[i]
        if c == "\\" and i + 1 < n:
            buf.append(s[i:i + 2])
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        buf.append(c)
        i += 1
    out.append("".join(buf))
    return out


def _node_to_latex(n):
    k = n.kind
    if k == "ch":
        if n.ins.startswith("\\"):
            return n.ins
        if n.disp in _UNI_TO_LATEX:
            return _UNI_TO_LATEX[n.disp]
        if n.disp in ("+", "=", "<", ">"):
            return f" {n.disp} "
        if n.disp == "-":
            return " - "
        return n.disp
    if k == "frac":
        return f"\\frac{{{row_to_latex(n.slots[0])}}}{{{row_to_latex(n.slots[1])}}}"
    if k == "sqrt":
        return f"\\sqrt{{{row_to_latex(n.slots[0])}}}"
    if k == "root":
        idx = row_to_latex(n.slots[0])
        body = row_to_latex(n.slots[1])
        return f"\\sqrt[{idx}]{{{body}}}" if idx else f"\\sqrt{{{body}}}"
    if k == "sup":
        inner = row_to_latex(n.slots[0])
        return f"^{inner}" if len(inner) == 1 and inner.isalnum() else f"^{{{inner}}}"
    if k == "sub":
        inner = row_to_latex(n.slots[0])
        return f"_{inner}" if len(inner) == 1 and inner.isalnum() else f"_{{{inner}}}"
    if k == "abs":
        return f"\\left| {row_to_latex(n.slots[0])} \\right|"
    if k == "accent":
        inner = row_to_latex(n.slots[0])
        if n.name == "vec":
            cmd = "overrightarrow" if len(inner) > 1 and not inner.startswith("\\") else "vec"
            return f"\\{cmd}{{{inner}}}"
        if n.name == "bar":
            cmd = "overline" if len(inner) > 1 and not inner.startswith("\\") else "bar"
            return f"\\{cmd}{{{inner}}}"
        return f"\\{n.name}{{{inner}}}"
    if k == "binom":
        return f"\\binom{{{row_to_latex(n.slots[0])}}}{{{row_to_latex(n.slots[1])}}}"
    if k == "grid":
        env, rows, cols = _grid_spec(n.name)
        r_strs = []
        for r in range(rows):
            c_strs = [row_to_latex(n.slots[r * cols + c]) for c in range(cols)]
            r_strs.append(" & ".join(c_strs))
        return f"\\begin{{{env}}} " + r" \\ ".join(r_strs) + f" \\end{{{env}}}"
    if k == "rm":
        inner = row_to_latex(n.slots[0])
        cmd = n.name or "mathrm"
        return f"\\{cmd}{{{inner}}}"
    if k == "func":
        if n.name == "pmod":
            return f" \\pmod{{{row_to_latex(n.slots[0])}}}"
        nm = {"asin": "arcsin", "acos": "arccos", "atan": "arctan"}.get(n.name, n.name)
        prefix = f"\\{nm}" if nm in _LATEX_FUNCS else nm
        return f"{prefix}({row_to_latex(n.slots[0])})"
    return ""


def row_to_latex(row):
    out = []
    for n in row:
        t = _node_to_latex(n)
        if out and out[-1].endswith(" ") and t.startswith(" "):
            t = t.lstrip(" ")
        # tránh dính lệnh LaTeX với chữ cái ngay sau (VD: \pi x, \sum a_n)
        if out and re.search(r"\\[A-Za-z]+$", out[-1]) and t and t[0].isalpha():
            out.append(" ")
        out.append(t)
    s = "".join(out).strip()
    s = re.sub(r" {2,}", " ", s)
    s = re.sub(r"([(\[{=,])\s*-\s*", r"\1-", s)
    s = re.sub(r"^-\s+", "-", s)
    return s


def parse_latex_to_row(latex: str):
    """Phân tích công thức LaTeX sang cây Row để chỉnh trực quan (WYSIWYG).
    Hỗ trợ ~98% công thức (phân số, căn, mũ, chỉ số, tích phân, tổng, giới hạn, vectơ, gạch ngang,
    nhị thức, chữ thẳng, tập hợp…). Trả về None cho ma trận / hệ phương trình nhiều dòng (\\begin{...})."""
    s = latex.strip()
    if not s:
        return Row()
    if _UNSUPPORTED_LATEX.search(s):
        return None
    n = len(s)

    def skip_ws(i):
        while i < n and s[i].isspace():
            i += 1
        return i

    def read_group(i, open_c="{", close_c="}"):
        if i >= n or s[i] != open_c:
            return None, i
        depth, j = 0, i
        while j < n:
            if s[j] == "\\" and j + 1 < n:
                j += 2
                continue
            if s[j] == open_c:
                depth += 1
            elif s[j] == close_c:
                depth -= 1
                if depth == 0:
                    return s[i + 1:j], j + 1
            j += 1
        return None, i

    def read_arg(i):
        i = skip_ws(i)
        if i >= n:
            return None, i
        if s[i] == "{":
            return read_group(i, "{", "}")
        if s[i] == "\\":
            j = i + 1
            while j < n and s[j].isalpha():
                j += 1
            return s[i:j], j
        return s[i], i + 1

    def parse_range(src):
        r = parse_latex_to_row(src)
        if r is None:
            return None
        sub_row = Row()
        sub_row.extend(r)
        return sub_row

    row = Row()
    i = 0
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c == "\\":
            if i + 1 < n and s[i + 1] == "%":
                row.append(Node("ch", "%", r"\%"))
                i += 2
                continue
            if i + 1 < n and s[i + 1] == " ":
                row.append(Node("ch", " ", r"\ "))
                i += 2
                continue
            if i + 1 < n and s[i + 1] in ("{", "}"):
                br = s[i + 1]
                row.append(Node("ch", br, f"\\{br}"))
                i += 2
                continue
            if i + 1 < n and s[i + 1] == "|":
                row.append(Node("ch", "‖", r"\|"))
                i += 2
                continue
            if i + 1 < n and s[i + 1] in (",", ";", ":", "!"):
                i += 2
                continue
            j = i + 1
            while j < n and s[j].isalpha():
                j += 1
            cmd = s[i + 1:j]
            i = j
            if not cmd:
                return None
            if cmd == "begin":
                env_s, i = read_arg(i)
                if not env_s or env_s.strip() not in _GRID_ENVS:
                    return None
                env = env_s.strip()
                # Tìm \end{env} khớp cùng cấp
                depth_e = 1
                st = i
                k = i
                found = -1
                end_tok = f"\\end{{{env}}}"
                beg_tok = f"\\begin{{{env}}}"
                while k < n:
                    if s.startswith(beg_tok, k):
                        depth_e += 1
                        k += len(beg_tok)
                    elif s.startswith(end_tok, k):
                        depth_e -= 1
                        if depth_e == 0:
                            found = k
                            break
                        k += len(end_tok)
                    else:
                        k += 1
                if found < 0:
                    return None
                body = s[st:found].strip()
                i = found + len(end_tok)
                raw_rows = _split_top_level(body, r"\\")
                # Bỏ dòng rỗng ở cuối nếu có trailing \\
                if len(raw_rows) > 1 and not raw_rows[-1].strip():
                    raw_rows.pop()
                grid_cells = [_split_top_level(rr, "&") for rr in raw_rows]
                nrows = max(1, len(grid_cells))
                ncols = max(1, max(len(rc) for rc in grid_cells))
                nd = Node("grid", name=f"{env}:{nrows}:{ncols}", nslots=nrows * ncols)
                for r_idx, rc in enumerate(grid_cells):
                    for c_idx in range(ncols):
                        cell_src = rc[c_idx].strip() if c_idx < len(rc) else ""
                        parsed = parse_range(cell_src)
                        if parsed is None:
                            return None
                        nd.slots[r_idx * ncols + c_idx].extend(parsed)
                row.append(nd)
            elif cmd in ("quad", "qquad"):
                row.append(Node("ch", "   ", f"\\{cmd} "))
            elif cmd == "frac":
                num_s, i = read_arg(i)
                den_s, i = read_arg(i)
                if num_s is None or den_s is None:
                    return None
                rn, rd = parse_range(num_s), parse_range(den_s)
                if rn is None or rd is None:
                    return None
                nd = Node("frac", nslots=2)
                nd.slots[0].extend(rn)
                nd.slots[1].extend(rd)
                row.append(nd)
            elif cmd == "binom":
                a_s, i = read_arg(i)
                b_s, i = read_arg(i)
                if a_s is None or b_s is None:
                    return None
                ra, rb = parse_range(a_s), parse_range(b_s)
                if ra is None or rb is None:
                    return None
                nd = Node("binom", nslots=2)
                nd.slots[0].extend(ra)
                nd.slots[1].extend(rb)
                row.append(nd)
            elif cmd == "sqrt":
                i = skip_ws(i)
                idx_s = None
                if i < n and s[i] == "[":
                    idx_s, i = read_group(i, "[", "]")
                    if idx_s is None:
                        return None
                body_s, i = read_arg(i)
                if body_s is None:
                    return None
                rb = parse_range(body_s)
                if rb is None:
                    return None
                if idx_s is not None:
                    ri = parse_range(idx_s)
                    if ri is None:
                        return None
                    nd = Node("root", nslots=2)
                    nd.slots[0].extend(ri)
                    nd.slots[1].extend(rb)
                else:
                    nd = Node("sqrt", nslots=1)
                    nd.slots[0].extend(rb)
                row.append(nd)
            elif cmd in ("vec", "overrightarrow", "bar", "overline", "hat"):
                body_s, i = read_arg(i)
                if body_s is None:
                    return None
                rb = parse_range(body_s)
                if rb is None:
                    return None
                acc_kind = "vec" if cmd in ("vec", "overrightarrow") else ("bar" if cmd in ("bar", "overline") else "hat")
                nd = Node("accent", name=acc_kind, nslots=1)
                nd.slots[0].extend(rb)
                row.append(nd)
            elif cmd == "mathbb":
                body_s, i = read_arg(i)
                if body_s is None:
                    return None
                if body_s.strip() in _MATHBB_MAP:
                    bch = body_s.strip()
                    row.append(Node("ch", _MATHBB_MAP[bch], f"\\mathbb{{{bch}}}"))
                else:
                    rb = parse_range(body_s)
                    if rb is None:
                        return None
                    nd = Node("rm", name="mathbb", nslots=1)
                    nd.slots[0].extend(rb)
                    row.append(nd)
            elif cmd in ("mathrm", "text", "textbf", "mathbf", "mathcal"):
                body_s, i = read_arg(i)
                if body_s is None:
                    return None
                # Giữ khoảng trắng tự nhiên bên trong \text{...} / \mathrm{...}
                if cmd in ("text", "mathrm", "textbf", "mathbf") and "\\" not in body_s and "^" not in body_s and "_" not in body_s:
                    nd = Node("rm", name="mathrm" if cmd == "text" else cmd, nslots=1)
                    for ch_ in body_s:
                        nd.slots[0].append(Node("ch", ch_, r"\ " if ch_ == " " else ch_))
                    row.append(nd)
                else:
                    rb = parse_range(body_s)
                    if rb is None:
                        return None
                    nd = Node("rm", name="mathrm" if cmd == "text" else cmd, nslots=1)
                    nd.slots[0].extend(rb)
                    row.append(nd)
            elif cmd == "pmod":
                body_s, i = read_arg(i)
                if body_s is None:
                    return None
                rb = parse_range(body_s)
                if rb is None:
                    return None
                nd = Node("func", name="pmod", nslots=1)
                nd.slots[0].extend(rb)
                row.append(nd)
            elif cmd == "left":
                i = skip_ws(i)
                if i >= n:
                    return None
                if s[i] == "\\" and i + 1 < n and s[i + 1] in ("{", "}"):
                    br = s[i + 1]
                    row.append(Node("ch", br, f"\\{br}"))
                    i += 2
                    continue
                if s[i] == "\\" and i + 1 < n and s[i + 1] == "|":
                    row.append(Node("ch", "‖", r"\|"))
                    i += 2
                    continue
                delim = s[i]
                i += 1
                if delim == "|":
                    depth = 1
                    st = i
                    found = -1
                    k = i
                    while k < n:
                        if s.startswith(r"\left", k):
                            depth += 1
                            k += 5
                        elif s.startswith(r"\right", k):
                            depth -= 1
                            if depth == 0:
                                found = k
                                break
                            k += 6
                        else:
                            k += 1
                    if found < 0:
                        return None
                    inner = s[st:found]
                    ri = parse_range(inner)
                    if ri is None:
                        return None
                    nd = Node("abs", nslots=1)
                    nd.slots[0].extend(ri)
                    row.append(nd)
                    i = skip_ws(found + 6)
                    if i < n and s[i] == "|":
                        i += 1
                elif delim in ("(", "["):
                    row.append(Node("ch", delim, delim))
                elif delim == ".":
                    pass
                else:
                    return None
            elif cmd == "right":
                i = skip_ws(i)
                if i < n and s[i] == "\\" and i + 1 < n and s[i + 1] in ("{", "}"):
                    br = s[i + 1]
                    row.append(Node("ch", br, f"\\{br}"))
                    i += 2
                elif i < n and s[i] == "\\" and i + 1 < n and s[i + 1] == "|":
                    row.append(Node("ch", "‖", r"\|"))
                    i += 2
                elif i < n and s[i] in (")", "]"):
                    row.append(Node("ch", s[i], s[i]))
                    i += 1
                elif i < n and s[i] in ("|", "."):
                    i += 1
                else:
                    return None
            elif cmd in _LATEX_FUNCS:
                i_next = skip_ws(i)
                if cmd != "lim" and i_next < n and s[i_next] == "(":
                    inner, i2 = read_group(i_next, "(", ")")
                    if inner is not None:
                        ri = parse_range(inner)
                        if ri is None:
                            return None
                        nd = Node("func", name=cmd, nslots=1)
                        nd.slots[0].extend(ri)
                        row.append(nd)
                        i = i2
                        continue
                row.append(Node("ch", cmd, f"\\{cmd}" + ("" if cmd == "lim" else " ")))
            elif cmd in _LATEX_TO_UNI:
                uni = _LATEX_TO_UNI[cmd]
                ins = f"\\{cmd}" if uni in _BIG_OPS else f"\\{cmd} "
                row.append(Node("ch", uni, ins))
            else:
                return None
        elif c in ("^", "_"):
            arg_s, i = read_arg(i + 1)
            if arg_s is None:
                return None
            if c == "^" and arg_s.strip() == r"\circ":
                row.append(Node("ch", "°", r"^\circ "))
                continue
            ra = parse_range(arg_s)
            if ra is None:
                return None
            nd = Node("sup" if c == "^" else "sub", nslots=1)
            nd.slots[0].extend(ra)
            row.append(nd)
        elif c == "|":
            j = i + 1
            depth = 0
            found = -1
            while j < n:
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                elif s[j] == "|" and depth == 0:
                    found = j
                    break
                j += 1
            if found > i:
                ri = parse_range(s[i + 1:found])
                if ri is None:
                    return None
                nd = Node("abs", nslots=1)
                nd.slots[0].extend(ri)
                row.append(nd)
                i = found + 1
            else:
                row.append(Node("ch", "|", "|"))
                i += 1
        elif c == "{":
            inner, i2 = read_group(i, "{", "}")
            if inner is None:
                return None
            ri = parse_range(inner)
            if ri is None:
                return None
            row.extend(ri)
            i = i2
        elif c == "}":
            return None
        elif c == "-":
            row.append(Node("ch", "−", "-"))
            i += 1
        else:
            row.append(Node("ch", c, c))
            i += 1

    def _fix_parents(r, owner=None):
        r.node = owner
        for nd in r:
            for sl in getattr(nd, "slots", []):
                sl.node = nd
                _fix_parents(sl, nd)
    _fix_parents(row)
    return row


# ----------------------------------------------------------------------------- widget
class NaturalDisplay(QWidget):
    submitted = Signal()
    changed = Signal()

    def __init__(self, base_px=24, readonly=False, align_right=False, parent=None, formula_mode=False, min_h=None, max_h=None):
        super().__init__(parent)
        self.base_px = base_px
        self.readonly = readonly
        self.align_right = align_right
        self.formula_mode = formula_mode
        self.min_h = min_h
        self.max_h = max_h
        self.root = Row()
        self.cur = (self.root, 0)
        self.dark = False
        self.accent = "#5B5BD6"
        self.fg = QColor("#1B2133")
        self.muted = QColor("#9AA3BA")
        self.bg = QColor("#FFFFFF")
        self.border = QColor("#D5DBEA")
        self.placeholder = ""
        self._carets = []
        self._blink = True
        self._fm = {}
        self._scroll = 0.0
        self.setFocusPolicy(Qt.NoFocus if readonly else Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        init_h = max(min_h or 0, int(base_px * 2.3))
        self.setMinimumHeight(init_h)
        self.setFixedHeight(init_h)
        if not readonly:
            t = QTimer(self)
            t.timeout.connect(self._tick)
            t.start(530)
            self.setCursor(Qt.IBeamCursor)

    # ---------------------------------------------------------------- giao diện
    def set_colors(self, fg, muted, bg, border, accent):
        self.fg, self.muted, self.bg, self.border, self.accent = QColor(fg), QColor(muted), QColor(bg), QColor(border), accent
        self.update()

    def _tick(self):
        self._blink = not self._blink
        self.update()

    # ---------------------------------------------------------------- nội dung
    def clear(self):
        self.root = Row()
        self.cur = (self.root, 0)
        self._touch()

    def is_empty(self):
        return not self.root

    def to_text(self):
        return ser_row(self.root)

    def to_display(self):
        return disp_row(self.root)

    def to_latex(self):
        return row_to_latex(self.root)

    def from_latex(self, latex: str) -> bool:
        """Nạp công thức LaTeX vào trình soạn trực quan. Trả False nếu công thức chứa cú pháp nâng cao."""
        row = parse_latex_to_row(latex)
        if row is None:
            return False
        self.root = row
        self.cur = (self.root, len(self.root))
        self._fit()
        self._blink = True
        self.update()
        return True

    def from_calc(self, expr: str):
        """Nạp biểu thức kiểu máy tính (VD: x^3 + sin(x), sin(x)/x, sqrt(x+1)) vào trình soạn trực quan."""
        old_blk = self.blockSignals(True)
        try:
            self._from_calc_impl(expr)
        finally:
            self.blockSignals(old_blk)
        self.cur = (self.root, len(self.root))
        self._fit()
        self.update()

    def _from_calc_impl(self, expr: str):
        self.root = Row()
        self.cur = (self.root, 0)
        s = (expr or "").strip()
        i, n = 0, len(s)
        while i < n:
            c = s[i]
            if c.isspace():
                i += 1
                continue
            if c == "/":
                self.put_div()
                # đọc toán hạng mẫu số ngay sau '/'
                j = i + 1
                while j < n and s[j].isspace():
                    j += 1
                if j < n and s[j] == "(":
                    depth, k = 0, j
                    while k < n:
                        if s[k] == "(":
                            depth += 1
                        elif s[k] == ")":
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    sub_s = s[j + 1:k] if k < n else s[j + 1:]
                    sub_nd = NaturalDisplay(self.base_px, formula_mode=self.formula_mode)
                    sub_nd.from_calc(sub_s)
                    den_row = self.cur[0]
                    for it in sub_nd.root:
                        den_row.append(it)
                    for it in den_row:
                        for sl in getattr(it, "slots", []):
                            sl.node = it
                    self._move_out(den_row.node)
                    i = k + 1
                    continue
                else:
                    k = j
                    while k < n and (s[k].isalnum() or s[k] in "._"):
                        k += 1
                    for ch_ in s[j:k]:
                        self._type(ch_)
                    if self.cur[0].node is not None:
                        self._move_out(self.cur[0].node)
                    i = k
                    continue
            if c == "^":
                self.put_sup()
                j = i + 1
                if j < n and s[j] == "(":
                    depth, k = 0, j
                    while k < n:
                        if s[k] == "(":
                            depth += 1
                        elif s[k] == ")":
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    for ch_ in s[j + 1:k]:
                        self._type(ch_)
                    if self.cur[0].node is not None:
                        self._move_out(self.cur[0].node)
                    i = k + 1
                    continue
                else:
                    k = j
                    if k < n and s[k] in "+-":
                        k += 1
                    while k < n and (s[k].isalnum() or s[k] == "."):
                        k += 1
                    for ch_ in s[j:k]:
                        self._type(ch_)
                    if self.cur[0].node is not None:
                        self._move_out(self.cur[0].node)
                    i = k
                    continue
            if s.startswith("pi", i) and (i + 2 == n or not s[i + 2].isalpha()) and (i == 0 or not s[i - 1].isalpha()):
                self.put_char("π", "π")
                i += 2
                continue
            self._type(c)
            i += 1

    def to_data(self):
        return [n.to_data() for n in self.root]

    def from_data(self, d):
        self.root = Row()
        for it in d:
            self.root.append(Node.from_data(it))
        self.cur = (self.root, len(self.root))
        self._touch()

    def set_pretty(self, text):
        """Hiển thị chuỗi kết quả (phân số a/b, căn √, lũy thừa, 1.2E-5…) dưới dạng công thức."""
        self.root = parse_pretty(text)
        self.cur = (self.root, len(self.root))
        self._touch()

    def _fit(self):
        sc = 1.0
        w, a, d = self._m_row(self.root, sc)
        avail = self.width() - 20
        if self.readonly and w > avail > 0:
            sc = max(0.5, avail / w)
            w, a, d = self._m_row(self.root, sc)
        target = max(int(self.base_px * 2.3), int(a + d + 22))
        if self.min_h is not None:
            target = max(self.min_h, target)
        if self.max_h is not None:
            target = min(self.max_h, target)
        if target != self.height():
            self.setFixedHeight(target)

    def resizeEvent(self, e):
        self._fit()
        super().resizeEvent(e)

    def _touch(self):
        self._fit()
        self._blink = True
        self.changed.emit()
        self.update()

    # ---------------------------------------------------------------- chèn
    def _ins(self, node):
        row, i = self.cur
        row.insert(i, node)
        self.cur = (row, i + 1)
        return node

    def put_char(self, disp, ins=None):
        self._ins(Node("ch", disp, ins))
        self._touch()

    def _enter(self, node, slot=0):
        self.cur = (node.slots[slot], 0)

    def put_func(self, name):
        n = self._ins(Node("func", name=name, nslots=1))
        self._enter(n)
        self._touch()

    def put_sqrt(self):
        n = self._ins(Node("sqrt", nslots=1))
        self._enter(n)
        self._touch()

    def put_root(self, index=None):
        n = self._ins(Node("root", nslots=2))
        if index:
            for c in index:
                n.slots[0].append(_ch(c))
            self._enter(n, 1)
        else:
            self._enter(n, 0)
        self._touch()

    def put_abs(self):
        n = self._ins(Node("abs", nslots=1))
        self._enter(n)
        self._touch()

    def put_sup(self, text=None):
        n = self._ins(Node("sup", nslots=1))
        if text:
            for c in text:
                n.slots[0].append(_ch(c))
            row, i = self.cur
            self.cur = (row, i)          # con trỏ ở sau nút mũ
        else:
            self._enter(n)
        self._touch()

    def put_sub(self, text=None):
        n = self._ins(Node("sub", nslots=1))
        if text:
            for c in text:
                n.slots[0].append(_ch(c))
            row, i = self.cur
            self.cur = (row, i)
        else:
            self._enter(n)
        self._touch()

    def put_frac(self):
        n = self._ins(Node("frac", nslots=2))
        self._enter(n)
        self._touch()

    def put_accent(self, kind="vec"):
        n = self._ins(Node("accent", name=kind, nslots=1))
        self._enter(n)
        self._touch()

    def put_binom(self):
        n = self._ins(Node("binom", nslots=2))
        self._enter(n)
        self._touch()

    def put_grid(self, env="bmatrix", rows=2, cols=2):
        n = self._ins(Node("grid", name=f"{env}:{rows}:{cols}", nslots=rows * cols))
        self._enter(n, 0)
        self._touch()

    def put_div(self):
        """Phím ÷: lấy toán hạng đứng trước làm tử số, con trỏ xuống mẫu số."""
        row, i = self.cur
        j = i
        while j > 0 and row[j - 1].kind in ("sup", "sub"):
            j -= 1
        if j > 0:
            p = row[j - 1]
            if p.kind == "ch" and p.ins == ")":
                depth, k = 0, j - 1
                while k >= 0:
                    if row[k].kind == "ch" and row[k].ins == ")":
                        depth += 1
                    elif row[k].kind == "ch" and row[k].ins == "(":
                        depth -= 1
                        if depth == 0:
                            break
                    k -= 1
                j = k if k >= 0 else j - 1
            elif p.kind == "ch" and (p.ins.isalnum() or p.ins in ".!π"):
                k = j - 1
                digit_run = p.ins.isdigit() or p.ins == "."
                while k > 0 and row[k - 1].kind == "ch" and ((row[k - 1].ins.isdigit() or row[k - 1].ins == ".") if digit_run else row[k - 1].ins.isalpha()):
                    k -= 1
                j = k
            else:
                j = j - 1 if p.kind != "ch" else j
        taken = list(row[j:i])
        if taken and taken[0].kind == "ch" and taken[0].ins == "(" and taken[-1].kind == "ch" and taken[-1].ins == ")":
            taken = taken[1:-1]
        del row[j:i]
        n = Node("frac", nslots=2)
        for t in taken:
            n.slots[0].append(t)
            if t.kind != "ch":
                for s in t.slots:
                    s.node = t
        row.insert(j, n)
        self.cur = (n.slots[1], 0) if taken else (n.slots[0], 0)
        self._touch()

    def type_close(self):
        row, i = self.cur
        if row.node is not None and i == len(row) and row.node.kind in ("func", "abs", "sqrt", "root", "frac"):
            self._move_out(row.node)
            self._touch()
            return
        self.put_char(")")

    def _move_out(self, node):
        parent = self._row_of(node)
        if parent is not None:
            self.cur = (parent, parent.index(node) + 1)

    def _row_of(self, node):
        def walk(row):
            if node in row:
                return row
            for n in row:
                for s in getattr(n, "slots", []):
                    r = walk(s)
                    if r is not None:
                        return r
            return None
        return walk(self.root)

    def type_open(self):
        """Gõ '(' sau tên hàm (sin, sqrt, abs…) thì chuyển thành mẫu hàm."""
        row, i = self.cur
        run = []
        k = i
        while k > 0 and row[k - 1].kind == "ch" and row[k - 1].ins.isalpha() and len(row[k - 1].ins) == 1:
            run.insert(0, row[k - 1].ins)
            k -= 1
        word = "".join(run)
        for ln in range(len(word), 0, -1):
            w = word[-ln:]
            if w in FUNCS or w in ("sqrt", "abs", "root"):
                del row[i - ln:i]
                self.cur = (row, i - ln)
                if w == "sqrt":
                    self.put_sqrt()
                elif w == "abs":
                    self.put_abs()
                elif w == "root":
                    self.put_root()
                else:
                    self.put_func(w)
                return
        self.put_char("(")

    # ---------------------------------------------------------------- xóa / di chuyển
    def _positions(self):
        out = []

        def walk(row):
            out.append((row, 0))
            for i, n in enumerate(row):
                for s in getattr(n, "slots", []):
                    walk(s)
                out.append((row, i + 1))
        walk(self.root)
        return out

    def _idx(self, pos):
        for k, (r, i) in enumerate(pos):
            if r is self.cur[0] and i == self.cur[1]:
                return k
        return 0

    def move(self, d):
        pos = self._positions()
        k = max(0, min(len(pos) - 1, self._idx(pos) + d))
        # nhảy qua các vị trí trùng (cuối hàng ngay trước mẫu và đầu ô đầu tiên)
        self.cur = pos[k]
        self._touch()

    def move_vertical(self, up):
        row, i = self.cur
        node = row.node
        while node is not None:
            if node.kind in ("frac", "binom"):
                idx = node.slots.index(row)
                if up and idx == 1:
                    self.cur = (node.slots[0], min(i, len(node.slots[0])))
                    return self._touch()
                if (not up) and idx == 0:
                    self.cur = (node.slots[1], min(i, len(node.slots[1])))
                    return self._touch()
            if node.kind == "grid":
                _, rows, cols = _grid_spec(node.name)
                idx = node.slots.index(row)
                r, c = divmod(idx, cols)
                nr = r - 1 if up else r + 1
                if 0 <= nr < rows:
                    tgt = node.slots[nr * cols + c]
                    self.cur = (tgt, min(i, len(tgt)))
                    return self._touch()
            if node.kind == "root" and row is node.slots[0] and not up:
                self.cur = (node.slots[1], 0)
                return self._touch()
            if node.kind == "sup" and not up:
                self._move_out(node)
                return self._touch()
            if node.kind == "sub" and up:
                self._move_out(node)
                return self._touch()
            parent = self._row_of(node)
            if parent is None:
                break
            row, i, node = parent, parent.index(node), parent.node

    def backspace(self):
        row, i = self.cur
        if i > 0:
            p = row[i - 1]
            if p.kind != "ch":
                if all(not s for s in p.slots) or (p.kind in ("sup", "sub") and not p.slots[0]):
                    del row[i - 1]
                    self.cur = (row, i - 1)
                else:
                    last = p.slots[-1]
                    self.cur = (last, len(last))
            else:
                del row[i - 1]
                self.cur = (row, i - 1)
        elif row.node is not None:
            node = row.node
            parent = self._row_of(node)
            if parent is None:
                return
            if all(not s for s in node.slots):
                k = parent.index(node)
                del parent[k]
                self.cur = (parent, k)
            else:
                # đầu một ô của mẫu: lùi ra trước mẫu, nếu mẫu là phân số thì "tháo" tử số ra
                k = parent.index(node)
                if node.kind == "frac" and row is node.slots[1] and not node.slots[1]:
                    del parent[k]
                    for t in node.slots[0]:
                        parent.insert(k, t)
                        k += 1
                    self.cur = (parent, k)
                else:
                    self.cur = (parent, k)
        self._touch()

    def delete(self):
        row, i = self.cur
        if i < len(row):
            del row[i]
            self._touch()

    def focusNextPrevChild(self, next_child):
        if self.formula_mode:
            return False
        return super().focusNextPrevChild(next_child)

    # ---------------------------------------------------------------- bàn phím vật lý
    def keyPressEvent(self, e):
        if self.readonly:
            return
        k, t, mod = e.key(), e.text(), e.modifiers()
        if mod & Qt.ControlModifier and k == Qt.Key_V:
            from PySide6.QtGui import QGuiApplication
            for c in QGuiApplication.clipboard().text().strip():
                self._type(c)
            return
        if self.formula_mode and k == Qt.Key_Tab:
            row, _ = self.cur
            if row.node is not None:
                idx = row.node.slots.index(row)
                if idx + 1 < len(row.node.slots):
                    self.cur = (row.node.slots[idx + 1], 0)
                else:
                    self._move_out(row.node)
                self._touch()
            return
        if k in (Qt.Key_Return, Qt.Key_Enter):
            self.submitted.emit()
        elif k == Qt.Key_Backspace:
            self.backspace()
        elif k == Qt.Key_Delete:
            self.delete()
        elif k == Qt.Key_Left:
            self.move(-1)
        elif k == Qt.Key_Right:
            self.move(1)
        elif k == Qt.Key_Up:
            self.move_vertical(True)
        elif k == Qt.Key_Down:
            self.move_vertical(False)
        elif k == Qt.Key_Home:
            self.cur = (self.root, 0)
            self._touch()
        elif k == Qt.Key_End:
            self.cur = (self.root, len(self.root))
            self._touch()
        elif k == Qt.Key_Escape:
            self.clear()
        elif t and t.isprintable():
            self._type(t)

    def _type(self, c):
        if c == " ":
            if self.formula_mode:
                row, i = self.cur
                if row.node is not None and row.node.kind in ("sup", "sub") and i == len(row) and len(row) > 0:
                    self._move_out(row.node)
                    self._touch()
            return
        if c == "/":
            self.put_div()
        elif c == "^":
            self.put_sup()
        elif c == "_" and self.formula_mode:
            self.put_sub()
        elif c == "(":
            self.type_open()
        elif c == ")":
            self.type_close()
        elif c == "√":
            self.put_sqrt()
        elif c == "²":
            self.put_sup("2")
        elif c == "³":
            self.put_sup("3")
        elif c == "=":
            if self.formula_mode:
                self.put_char("=", "=")
            else:
                self.submitted.emit()
        else:
            n = _ch(c)
            self.put_char(n.disp, n.ins)

    def mousePressEvent(self, e):
        if self.readonly:
            return
        self.setFocus()
        p = e.position()
        best, bd = None, 1e18
        for (x, y0, y1, row, i) in self._carets:
            d = (x - p.x()) ** 2 + (((y0 + y1) / 2 - p.y()) * 1.6) ** 2
            if d < bd:
                best, bd = (row, i), d
        if best:
            self.cur = best
            self._touch()

    # ---------------------------------------------------------------- đo & vẽ
    def _font(self, sc):
        px = max(8, int(round(self.base_px * sc)))
        if px not in self._fm:
            f = QFont(self.font())
            f.setPixelSize(px)
            f.setWeight(QFont.Medium)
            self._fm[px] = (f, QFontMetricsF(f))
        return self._fm[px]

    def _m_row(self, row, sc):
        """(rộng, trên đường cơ sở, dưới đường cơ sở)"""
        S = self.base_px * sc
        if not row:
            return (0.62 * S, 0.78 * S, 0.25 * S)
        w, a, d = 0.0, 0.0, 0.0
        for n in row:
            nw, na, nd = self._m_node(n, sc)
            w += nw
            a, d = max(a, na), max(d, nd)
        return (w, max(a, 0.78 * S), max(d, 0.25 * S))

    def _m_node(self, n, sc):
        S = self.base_px * sc
        f, fm = self._font(sc)
        k = n.kind
        if k == "ch":
            if n.disp in _BIG_OPS:
                bf, bfm = self._font(sc * 1.32)
                return (bfm.horizontalAdvance(n.disp) + 0.10 * S, 1.02 * S, 0.36 * S)
            return (fm.horizontalAdvance(n.disp) + (0.14 * S if n.disp in "+−×÷=±<>≤≥≠≈⇒⇔" else 0.0), 0.78 * S, 0.25 * S)
        if k == "sup":
            iw, ia, idd = self._m_row(n.slots[0], sc * 0.68)
            raise_ = 0.50 * S
            return (iw + 2, max(0.0, raise_ + ia), max(0.0, idd - raise_))
        if k == "sub":
            iw, ia, idd = self._m_row(n.slots[0], sc * 0.68)
            drop = 0.28 * S
            return (iw + 2, max(0.0, ia - drop), max(0.25 * S, drop + idd))
        if k == "frac":
            nw, na, nd = self._m_row(n.slots[0], sc)
            dw, da, dd = self._m_row(n.slots[1], sc)
            axis, gap = 0.30 * S, 3.0
            return (max(nw, dw) + 10, axis + gap + nd + na, max(da + dd + gap - axis, 0.25 * S))
        if k == "binom":
            nw, na, nd = self._m_row(n.slots[0], sc * 0.92)
            dw, da, dd = self._m_row(n.slots[1], sc * 0.92)
            axis, gap = 0.30 * S, 3.0
            asc = axis + gap + nd + na
            desc = max(da + dd + gap - axis, 0.25 * S)
            pw = self._paren_w(S, asc + desc)
            return (max(nw, dw) + 2 * pw + 6, asc, desc)
        if k == "grid":
            g = self._m_grid(n, sc)
            return (g["w"], g["asc"], g["desc"])
        if k == "accent":
            iw, ia, idd = self._m_row(n.slots[0], sc)
            return (iw + 4, ia + 0.30 * S, idd)
        if k == "rm":
            iw, ia, idd = self._m_row(n.slots[0], sc * 0.95)
            return (iw + 2, ia, idd)
        if k in ("sqrt", "root"):
            iw, ia, idd = self._m_row(n.slots[-1], sc)
            rw = 0.62 * S
            asc = ia + 5
            w = rw + iw + 4
            if k == "root":
                xw, xa, xd = self._m_row(n.slots[0], sc * 0.6)
                w += max(0.0, xw - 0.25 * rw)
                asc = max(asc, 0.5 * ia + xa + xd + 2)
            return (w, asc, idd)
        if k == "abs":
            iw, ia, idd = self._m_row(n.slots[0], sc)
            return (iw + 14, ia + 2, idd + 2)
        if k == "func":
            iw, ia, idd = self._m_row(n.slots[0], sc)
            nm = " (mod " if n.name == "pmod" else DISPLAY_NAME.get(n.name, n.name)
            if n.name == "pmod":
                return (fm.horizontalAdvance(" (mod ") + iw + fm.horizontalAdvance(")"), max(ia, 0.78 * S), max(idd, 0.25 * S))
            pw = self._paren_w(S, ia + idd)
            return (fm.horizontalAdvance(nm) + 2 * pw + iw + 2, max(ia, 0.78 * S), max(idd, 0.25 * S))
        return (0, 0, 0)

    @staticmethod
    def _paren_w(S, h):
        return 0.30 * S + min(0.25 * S, max(0.0, (h - 1.03 * S)) * 0.08)

    def _m_grid(self, n, sc):
        env, rows, cols = _grid_spec(n.name)
        S = self.base_px * sc
        csc = sc * (0.76 if rows >= 3 else 0.86)
        col_w = [0.0] * cols
        row_a = [0.0] * rows
        row_d = [0.0] * rows
        cell_m = {}
        for r in range(rows):
            for c in range(cols):
                cw_, ca, cd = self._m_row(n.slots[r * cols + c], csc)
                cell_m[(r, c)] = (cw_, ca, cd)
                col_w[c] = max(col_w[c], cw_)
                row_a[r] = max(row_a[r], ca)
                row_d[r] = max(row_d[r], cd)
        hgap = max(8.0, 0.45 * S)
        vgap = max(4.0, 0.18 * S)
        body_w = sum(col_w) + max(0, cols - 1) * hgap
        body_h = sum(row_a[r] + row_d[r] for r in range(rows)) + max(0, rows - 1) * vgap
        axis = 0.30 * S
        asc = max(0.78 * S, body_h / 2.0 + axis + 2.0)
        desc = max(0.25 * S, body_h / 2.0 - axis + 2.0)
        if env == "cases":
            lw = max(10.0, 0.46 * S)
            rw = 4.0
        elif env == "matrix":
            lw, rw = 4.0, 4.0
        elif env == "pmatrix":
            pw = self._paren_w(S, body_h + 4.0)
            lw, rw = pw + 2.0, pw + 2.0
        else:
            lw = max(8.0, 0.34 * S)
            rw = lw
        return dict(env=env, rows=rows, cols=cols, csc=csc, col_w=col_w, row_a=row_a, row_d=row_d,
                    cell_m=cell_m, hgap=hgap, vgap=vgap, body_w=body_w, body_h=body_h,
                    lw=lw, rw=rw, w=lw + body_w + rw + 6.0, asc=asc, desc=desc)

    def _paint_row(self, p, row, x, base, sc, rec=True):
        S = self.base_px * sc
        f, fm = self._font(sc)
        w, a, d = self._m_row(row, sc)
        if not row:
            r = QRectF(x + 1, base - 0.62 * S, 0.5 * S, 0.8 * S)
            pen = QPen(self.muted, 1.2, Qt.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 2, 2)
            if rec:
                self._carets.append((x + 0.25 * S, base - a, base + d, row, 0))
            return w
        cx = x
        for i, n in enumerate(row):
            if rec:
                self._carets.append((cx, base - a, base + d, row, i))
            cx += self._paint_node(p, n, cx, base, sc, rec)
        if rec:
            self._carets.append((cx, base - a, base + d, row, len(row)))
        return w

    def _paint_node(self, p, n, x, base, sc, rec):
        S = self.base_px * sc
        f, fm = self._font(sc)
        k = n.kind
        w, a, d = self._m_node(n, sc)
        pen = QPen(self.fg, max(1.2, S * 0.065), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        if k == "ch":
            if n.disp in _BIG_OPS:
                bf, _ = self._font(sc * 1.32)
                p.setFont(bf)
                p.setPen(self.fg)
                p.drawText(QPointF(x + 0.04 * S, base + 0.08 * S), n.disp)
                return w
            p.setFont(f)
            p.setPen(self.fg)
            pad = 0.07 * S if n.disp in "+−×÷=±<>≤≥≠≈⇒⇔" else 0.0
            p.drawText(QPointF(x + pad, base), n.disp)
            return w
        if k == "sup":
            self._paint_row(p, n.slots[0], x + 1, base - 0.50 * S, sc * 0.68, rec)
            return w
        if k == "sub":
            self._paint_row(p, n.slots[0], x + 1, base + 0.28 * S, sc * 0.68, rec)
            return w
        if k == "frac":
            nw, na, nd = self._m_row(n.slots[0], sc)
            dw, da, dd = self._m_row(n.slots[1], sc)
            axis, gap = 0.30 * S, 3.0
            W = max(nw, dw)
            self._paint_row(p, n.slots[0], x + 5 + (W - nw) / 2, base - axis - gap - nd, sc, rec)
            self._paint_row(p, n.slots[1], x + 5 + (W - dw) / 2, base - axis + gap + da, sc, rec)
            p.setPen(pen)
            p.drawLine(QPointF(x + 1, base - axis), QPointF(x + w - 1, base - axis))
            return w
        if k == "binom":
            nw, na, nd = self._m_row(n.slots[0], sc * 0.92)
            dw, da, dd = self._m_row(n.slots[1], sc * 0.92)
            axis, gap = 0.30 * S, 3.0
            W = max(nw, dw)
            pw = self._paren_w(S, a + d)
            top, bot = base - a, base + d
            self._paren(p, x + pw * 0.85, top, bot, True, pen)
            self._paint_row(p, n.slots[0], x + pw + 3 + (W - nw) / 2, base - axis - gap - nd, sc * 0.92, rec)
            self._paint_row(p, n.slots[1], x + pw + 3 + (W - dw) / 2, base - axis + gap + da, sc * 0.92, rec)
            self._paren(p, x + w - pw * 0.85, top, bot, False, pen)
            return w
        if k == "grid":
            g = self._m_grid(n, sc)
            env, rows, cols, csc = g["env"], g["rows"], g["cols"], g["csc"]
            top, bot = base - g["asc"] + 1.0, base + g["desc"] - 1.0
            x_left = x + 3.0
            x_right = x + w - 3.0
            if env == "bmatrix":
                self._bracket(p, x_left + 1.0, top, bot, True, pen, g["lw"] * 0.55)
                self._bracket(p, x_right - 1.0, top, bot, False, pen, g["rw"] * 0.55)
            elif env == "pmatrix":
                self._paren(p, x_left + g["lw"] * 0.72, top, bot, True, pen)
                self._paren(p, x_right - g["rw"] * 0.72, top, bot, False, pen)
            elif env == "vmatrix":
                p.setPen(pen)
                p.drawLine(QPointF(x_left + g["lw"] * 0.5, top), QPointF(x_left + g["lw"] * 0.5, bot))
                p.drawLine(QPointF(x_right - g["rw"] * 0.5, top), QPointF(x_right - g["rw"] * 0.5, bot))
            elif env in ("cases", "Bmatrix"):
                self._brace(p, x_left, top, bot, True, pen, g["lw"] * 0.82)
                if env == "Bmatrix":
                    self._brace(p, x_right, top, bot, False, pen, g["rw"] * 0.82)
            cy = (top + bot - g["body_h"]) / 2.0
            for r in range(rows):
                rbase = cy + g["row_a"][r]
                cx = x_left + g["lw"]
                for c in range(cols):
                    cw_, _, _ = g["cell_m"][(r, c)]
                    ox = 0.0 if env == "cases" else (g["col_w"][c] - cw_) / 2.0
                    self._paint_row(p, n.slots[r * cols + c], cx + ox, rbase, csc, rec)
                    cx += g["col_w"][c] + g["hgap"]
                cy += g["row_a"][r] + g["row_d"][r] + g["vgap"]
            return w
        if k == "accent":
            iw, ia, idd = self._m_row(n.slots[0], sc)
            self._paint_row(p, n.slots[0], x + 2, base, sc, rec)
            y_bar = base - ia - 0.12 * S
            p.setPen(pen)
            if n.name == "vec":
                p.drawLine(QPointF(x + 2, y_bar), QPointF(x + iw + 2, y_bar))
                ah = max(3.0, 0.16 * S)
                p.drawLine(QPointF(x + iw + 2 - ah, y_bar - ah * 0.65), QPointF(x + iw + 2, y_bar))
                p.drawLine(QPointF(x + iw + 2 - ah, y_bar + ah * 0.65), QPointF(x + iw + 2, y_bar))
            elif n.name == "hat":
                mid_x = x + 2 + iw / 2.0
                hw = min(iw * 0.45, 0.32 * S)
                hh = max(3.2, 0.18 * S)
                p.drawLine(QPointF(mid_x - hw, y_bar + hh * 0.3), QPointF(mid_x, y_bar - hh * 0.7))
                p.drawLine(QPointF(mid_x, y_bar - hh * 0.7), QPointF(mid_x + hw, y_bar + hh * 0.3))
            else:
                p.drawLine(QPointF(x + 2, y_bar), QPointF(x + iw + 2, y_bar))
            return w
        if k == "rm":
            self._paint_row(p, n.slots[0], x + 1, base, sc * 0.95, rec)
            return w
        if k in ("sqrt", "root"):
            inner = n.slots[-1]
            iw, ia, idd = self._m_row(inner, sc)
            rw = 0.62 * S
            off = 0.0
            if k == "root":
                xw, xa, xd = self._m_row(n.slots[0], sc * 0.6)
                off = max(0.0, xw - 0.25 * rw)
                self._paint_row(p, n.slots[0], x, base - 0.5 * ia - xd, sc * 0.6, rec)
            top = base - ia - 3.5
            x0 = x + off
            path = QPainterPath()
            path.moveTo(x0 + 0.02 * rw, base - 0.30 * S)
            path.lineTo(x0 + 0.20 * rw, base - 0.36 * S)
            path.lineTo(x0 + 0.45 * rw, base + idd)
            path.lineTo(x0 + rw, top)
            path.lineTo(x0 + rw + iw + 3, top)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
            self._paint_row(p, inner, x0 + rw + 1, base, sc, rec)
            return w
        if k == "abs":
            iw, ia, idd = self._m_row(n.slots[0], sc)
            p.setPen(pen)
            p.drawLine(QPointF(x + 3, base - ia - 1), QPointF(x + 3, base + idd + 1))
            p.drawLine(QPointF(x + w - 3, base - ia - 1), QPointF(x + w - 3, base + idd + 1))
            self._paint_row(p, n.slots[0], x + 7, base, sc, rec)
            return w
        if k == "func":
            if n.name == "pmod":
                iw, ia, idd = self._m_row(n.slots[0], sc)
                p.setFont(f)
                p.setPen(self.fg)
                pre = " (mod "
                p.drawText(QPointF(x, base), pre)
                cx = x + fm.horizontalAdvance(pre)
                self._paint_row(p, n.slots[0], cx, base, sc, rec)
                p.setFont(f)
                p.setPen(self.fg)
                p.drawText(QPointF(cx + iw, base), ")")
                return w
            nm = DISPLAY_NAME.get(n.name, n.name)
            iw, ia, idd = self._m_row(n.slots[0], sc)
            p.setFont(f)
            p.setPen(self.fg)
            p.drawText(QPointF(x, base), nm)
            cx = x + fm.horizontalAdvance(nm)
            pw = self._paren_w(S, ia + idd)
            top, bot = base - max(ia, 0.78 * S), base + max(idd, 0.25 * S)
            self._paren(p, cx + pw * 0.8, top, bot, True, pen)
            self._paint_row(p, n.slots[0], cx + pw, base, sc, rec)
            self._paren(p, cx + pw + iw + pw * 0.2, top, bot, False, pen)
            return w
        return w

    @staticmethod
    def _paren(p, x, top, bot, left, pen):
        bulge = min(0.12 * (bot - top) + 3, 7) * (-1 if left else 1)
        path = QPainterPath()
        path.moveTo(x, top)
        path.quadTo(x + bulge, (top + bot) / 2, x, bot)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    @staticmethod
    def _bracket(p, x, top, bot, left, pen, arm=5.0):
        d = arm if left else -arm
        path = QPainterPath()
        path.moveTo(x + d, top)
        path.lineTo(x, top)
        path.lineTo(x, bot)
        path.lineTo(x + d, bot)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    @staticmethod
    def _brace(p, x, top, bot, left, pen, bw=8.0):
        mid = (top + bot) / 2.0
        s = 1.0 if left else -1.0
        x_edge = x + s * bw
        x_mid = x + s * bw * 0.45
        x_tip = x
        r = min(bw * 0.55, (bot - top) * 0.2)
        path = QPainterPath()
        path.moveTo(x_edge, top)
        path.quadTo(x_mid, top, x_mid, top + r)
        path.lineTo(x_mid, mid - r)
        path.quadTo(x_mid, mid, x_tip, mid)
        path.quadTo(x_mid, mid, x_mid, mid + r)
        path.lineTo(x_mid, bot - r)
        path.quadTo(x_mid, bot, x_edge, bot)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(self.border, 1))
        p.setBrush(self.bg)
        p.drawRoundedRect(r, 8, 8)
        sc = 1.0
        avail = self.width() - 20
        w, a, d = self._m_row(self.root, sc)
        if self.readonly and w > avail > 0:
            sc = max(0.5, avail / w)
            w, a, d = self._m_row(self.root, sc)
        elif self.max_h is not None and (a + d + 14) > self.height():
            sc = max(0.55, (self.height() - 14) / max(a + d, 1.0))
            w, a, d = self._m_row(self.root, sc)
        base = (self.height() - (a + d)) / 2 + a
        if not self.root and self.placeholder and not self.readonly:
            p.setPen(self.muted)
            pf = QFont(self.font())
            pf.setPixelSize(int(self.base_px * 0.55))
            p.setFont(pf)
            p.drawText(QRectF(12, 0, self.width() - 24, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.placeholder)
        x0 = 10.0
        if self.align_right and w <= avail:
            x0 = self.width() - 10 - w
        shift = 0.0
        if w > avail and not self.readonly:
            cx = self._caret_x_content(sc)
            if cx is not None:
                shift = min(0.0, avail - cx - 6)
        p.save()
        p.setClipRect(r.adjusted(2, 2, -2, -2))
        p.translate(x0 + shift, 0)
        self._carets = []
        self._paint_row(p, self.root, 0, base, sc, True)
        if not self.readonly and self.hasFocus() and self._blink:
            row, i = self.cur
            for (x, y0, y1, rw, ii) in self._carets:
                if rw is row and ii == i:
                    p.setPen(QPen(QColor(self.accent), 2))
                    p.drawLine(QPointF(x, y0 - 1), QPointF(x, y1 + 1))
                    break
        p.restore()
        off = x0 + shift
        self._carets = [(x + off, y0, y1, rw, i) for (x, y0, y1, rw, i) in self._carets]

    def _caret_x_content(self, sc=1.0):
        """Vị trí x của con trỏ trong hệ tọa độ nội dung (để cuộn ngang khi biểu thức dài)."""
        from PySide6.QtGui import QImage
        img = QImage(4, 4, QImage.Format_ARGB32)
        pr = QPainter(img)
        self._carets = []
        self._paint_row(pr, self.root, 0, 20, sc, True)
        pr.end()
        row, i = self.cur
        for (x, y0, y1, rw, ii) in self._carets:
            if rw is row and ii == i:
                return x
        return None


# ----------------------------------------------------------------------------- phân tích chuỗi kết quả
_PRETTY_TOK = re.compile(r"(\d+(?:[.,]\d+)?)(?:[Ee]([+-]?\d+))|(\d+(?:\.\d+)?)|(√)|(.)", re.S)


def parse_pretty(text):
    row = Row()
    s = text.strip()
    items = []
    for m in _PRETTY_TOK.finditer(s):
        if m.group(1):
            for c in m.group(1):
                items.append(_ch(c))
            items.append(Node("ch", "×10", "*10"))
            sp = Node("sup", nslots=1)
            for c in m.group(2).replace("+", ""):
                sp.slots[0].append(_ch(c))
            items.append(sp)
        elif m.group(3):
            for c in m.group(3):
                items.append(_ch(c))
        elif m.group(4):
            items.append("√")
        else:
            c = m.group(5)
            items.append(_ch(c) if c != "/" else "/")
    # √ + toán hạng
    out, i = [], 0
    while i < len(items):
        it = items[i]
        if it == "√":
            n = Node("sqrt", nslots=1)
            i += 1
            while i < len(items) and isinstance(items[i], Node) and items[i].kind == "ch" and (items[i].ins.isdigit() or items[i].ins == "."):
                n.slots[0].append(items[i])
                i += 1
            out.append(n)
            continue
        out.append(it)
        i += 1

    def operand_char(n):
        return isinstance(n, Node) and (n.kind in ("sqrt", "sup") or (n.kind == "ch" and (n.ins.isdigit() or n.ins in ".π" or n.ins.isalpha())))
    res, i = [], 0
    while i < len(out):
        it = out[i]
        if it == "/" and res and operand_char(res[-1]):
            k = len(res)
            while k > 0 and operand_char(res[k - 1]):
                k -= 1
            num = res[k:]
            del res[k:]
            j = i + 1
            den = []
            while j < len(out) and operand_char(out[j]):
                den.append(out[j])
                j += 1
            if den:
                n = Node("frac", nslots=2)
                n.slots[0].extend(num)
                n.slots[1].extend(den)
                res.append(n)
                i = j
                continue
            res.extend(num)
        res.append(_ch("/") if it == "/" else it)
        i += 1

    def fix(r, owner=None):
        r.node = owner
        for n in r:
            if isinstance(n, Node):
                for sl in n.slots:
                    sl.node = n
                    fix(sl, n)
    for n in res:
        if isinstance(n, str):
            n = _ch(n)
        row.append(n)
    fix(row)
    return row
