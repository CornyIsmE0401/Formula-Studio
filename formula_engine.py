# -*- coding: utf-8 -*-
"""formula_engine.py - Công thức hóa học: đọc công thức, tính M, cân bằng (kể cả ion/oxi hóa khử), vẽ phương trình,
xuất LaTeX/mhchem; vẽ công thức Toán (LaTeX); cấu hình electron; quét ảnh OCR; phát âm."""
import base64
import io
import json
import math
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from math import gcd

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap

from data_store import ATOMIC_MASSES, ELEMENTS_BY_Z

try:
    from rapid_latex_ocr import LatexOCR as _RapidLatexOCR
    HAS_RAPID_OCR = True
except Exception:
    _RapidLatexOCR = None
    HAS_RAPID_OCR = False
try:
    from pix2tex.cli import LatexOCR as _Pix2Tex
    HAS_PIX2TEX = True
except Exception:
    _Pix2Tex = None
    HAS_PIX2TEX = False

_SUBS = str.maketrans("0123456789n+-", "₀₁₂₃₄₅₆₇₈₉ₙ₊₋")
_SUPS = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")
_UNSUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻₊₋", "0123456789" "0123456789" "+-+-")


# ==============================================================================
# 1. ĐỌC CÔNG THỨC, ION, KHỐI LƯỢNG MOL
# ==============================================================================
def normalize_chem_text(t: str) -> str:
    """Chuẩn hóa ký tự Unicode: H₂O, Fe³⁺, →, ⇌ ... về dạng ASCII dễ xử lý."""
    t = t.replace("→", "->").replace("⇌", "<=>").replace("⇄", "<=>").replace("↔", "<=>").replace("⟶", "->")
    t = t.replace("−", "-").replace("–", "-").replace("·", ".").replace("•", ".").replace("↑", " ^ ").replace("↓", " v ")
    out = []
    for ch in t:
        if ch in "₀₁₂₃₄₅₆₇₈₉":
            out.append(str("₀₁₂₃₄₅₆₇₈₉".index(ch)))
        elif ch in "⁰¹²³⁴⁵⁶⁷⁸⁹":
            out.append("^" + str("⁰¹²³⁴⁵⁶⁷⁸⁹".index(ch)) if (not out or out[-1] != "^") else str("⁰¹²³⁴⁵⁶⁷⁸⁹".index(ch)))
        elif ch == "⁺":
            out.append("^+" if not (out and out[-1].startswith("^")) else "+")
        elif ch == "⁻":
            out.append("^-" if not (out and out[-1].startswith("^")) else "-")
        else:
            out.append(ch)
    return "".join(out)


_CHARGE_RE = re.compile(r"\^\{?(\d*)([+-])\}?$|\^\{?([+-])(\d*)\}?$")


def split_charge(sp: str):
    """'SO4^{2-}' -> ('SO4', -2).  'Fe^3+' -> ('Fe', 3)."""
    s = sp.strip()
    m = _CHARGE_RE.search(s)
    if not m:
        return s, 0
    if m.group(2):
        n, sign = (int(m.group(1)) if m.group(1) else 1), m.group(2)
    else:
        n, sign = (int(m.group(4)) if m.group(4) else 1), m.group(3)
    return s[:m.start()], (n if sign == "+" else -n)


def strip_state(sp: str):
    m = re.search(r"\((s|l|g|aq)\)\s*$", sp.strip(), flags=re.IGNORECASE)
    if m:
        return sp.strip()[:m.start()].strip(), m.group(0).strip()
    return sp.strip(), ""


def parse_formula_counts(formula: str) -> dict:
    clean = normalize_chem_text(formula).strip()
    clean, _ = strip_state(clean)
    clean, _ = split_charge(clean)
    clean = clean.replace("*", ".")
    if not clean or clean == "e":
        return {}
    total = defaultdict(int)
    for part in clean.split("."):
        part = part.strip()
        if not part:
            continue
        m_lead = re.match(r"^(\d+)(.*)$", part)
        mult = int(m_lead.group(1)) if m_lead else 1
        body = m_lead.group(2) if m_lead else part
        for el, cnt in _parse_single_formula(body).items():
            total[el] += cnt * mult
    return dict(total)


def _parse_single_formula(s: str) -> dict:
    tokens = re.findall(r"([A-Z][a-z]?|\d+|[\(\)\[\]])", s)
    stack = [defaultdict(int)]
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("(", "["):
            stack.append(defaultdict(int))
            i += 1
        elif tok in (")", "]"):
            if len(stack) == 1:
                raise ValueError("Ngoặc không khớp trong công thức.")
            group = stack.pop()
            mult = 1
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                mult = int(tokens[i + 1])
                i += 2
            else:
                i += 1
            for el, cnt in group.items():
                stack[-1][el] += cnt * mult
        elif re.match(r"^[A-Z][a-z]?$", tok):
            if tok not in ATOMIC_MASSES:
                raise ValueError(f"Không nhận diện được nguyên tố: '{tok}'")
            mult = 1
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                mult = int(tokens[i + 1])
                i += 2
            else:
                i += 1
            stack[-1][tok] += mult
        else:
            i += 1
    if len(stack) != 1:
        raise ValueError("Thiếu dấu đóng ngoặc trong công thức.")
    return dict(stack[0])


def calculate_molar_mass(formula: str):
    counts = parse_formula_counts(formula)
    if not counts:
        raise ValueError("Công thức trống hoặc không hợp lệ.")
    total_m = sum(ATOMIC_MASSES[el] * cnt for el, cnt in counts.items())
    breakdown = [(el, cnt, ATOMIC_MASSES[el] * cnt, ATOMIC_MASSES[el] * cnt / total_m * 100.0) for el, cnt in counts.items()]
    return total_m, breakdown


# ==============================================================================
# 2. CÂN BẰNG PHƯƠNG TRÌNH (BẢO TOÀN NGUYÊN TỐ + ĐIỆN TÍCH)
# ==============================================================================
_ARROW_RE = re.compile(r"(<=>|<->|⇌|-->|->|=>|==|→|(?<=\s)=(?=\s))((?:\[[^\]]*\]){0,2})")
LAST_NOTE = ""


def _split_species(side: str):
    """Tách theo dấu '+' nhưng không cắt điện tích (Fe^{2+}, H^+, Fe^3+)."""
    items, cur, depth = [], "", 0
    for i, ch in enumerate(side):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "+" and depth == 0 and not re.search(r"\^\d*$", cur) and not re.search(r"\^\{?$", cur):
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    return [x.strip() for x in items if x.strip()]


def _read_species(raw: str):
    item = raw.strip()
    suffix = ""
    m = re.search(r"(\s*(?:\^|v|↑|↓)\s*)+$", item) if re.search(r"\s(\^|v)$", item) or item.endswith(("↑", "↓")) else None
    if m:
        suffix = " " + m.group(0).strip()
        item = item[:m.start()].strip()
    item = re.sub(r"^\d+\s*", "", item)
    return item, suffix


def is_balanced(eq_text: str) -> bool:
    """Kiểm tra phương trình (đã có hệ số) đã cân bằng về nguyên tố và điện tích chưa."""
    text = normalize_chem_text(eq_text).strip()
    am = _ARROW_RE.search(text)
    if not am:
        return False
    tot = []
    for side in (text[:am.start()], text[am.end():]):
        cnt, chg = defaultdict(int), 0
        for raw in _split_species(side):
            sp, _ = _read_species(raw)
            m = re.match(r"^\s*(\d+)", raw)
            k = int(m.group(1)) if m else 1
            base, _st = strip_state(sp)
            core, c = split_charge(base)
            for el, n in (parse_formula_counts(core) if core != "e" else {}).items():
                cnt[el] += n * k
            chg += c * k
        tot.append((dict(cnt), chg))
    return tot[0] == tot[1]


def balance_chemical_equation(eq_text: str) -> str:
    global LAST_NOTE
    LAST_NOTE = ""
    text = normalize_chem_text(eq_text).strip()
    if re.search(r"(^|\s|\+)n[A-Z(\[]|\)n(\s|$)|\]n(\s|$)", text):
        raise ValueError("Phản ứng trùng hợp/trùng ngưng có hệ số n - không thể cân bằng tự động, hãy viết tay.")
    if not text:
        raise ValueError("Vui lòng nhập phương trình hóa học.")
    am = _ARROW_RE.search(text)
    if not am:
        raise ValueError("Phương trình cần có mũi tên (->, <=>, → hoặc =).")
    arrow_str = am.group(0)
    lhs_raw, rhs_raw = text[:am.start()].strip(), text[am.end():].strip()
    if not lhs_raw or not rhs_raw:
        raise ValueError("Thiếu chất tham gia hoặc sản phẩm.")
    lhs = [_read_species(x) for x in _split_species(lhs_raw)]
    rhs = [_read_species(x) for x in _split_species(rhs_raw)]
    allsp = lhs + rhs
    n_l, n = len(lhs), len(allsp)
    infos = []
    for sp, _ in allsp:
        base, _st = strip_state(sp)
        core, ch = split_charge(base)
        infos.append((parse_formula_counts(core) if core != "e" else {}, ch))
    elements = sorted({el for d, _ in infos for el in d})
    if not elements:
        raise ValueError("Không tìm thấy nguyên tố hợp lệ.")
    rows = []
    for el in elements:
        rows.append([Fraction(d.get(el, 0) if i < n_l else -d.get(el, 0)) for i, (d, _) in enumerate(infos)])
    if any(c for _, c in infos):
        rows.append([Fraction(c if i < n_l else -c) for i, (_, c) in enumerate(infos)])
    R, pivots, r = rows, [], 0
    for c in range(n):
        if r >= len(R):
            break
        p = next((i for i in range(r, len(R)) if R[i][c] != 0), None)
        if p is None:
            continue
        R[r], R[p] = R[p], R[r]
        pv = R[r][c]
        R[r] = [x / pv for x in R[r]]
        for i in range(len(R)):
            if i != r and R[i][c] != 0:
                f = R[i][c]
                R[i] = [R[i][j] - f * R[r][j] for j in range(n)]
        pivots.append(c)
        r += 1
    free = [c for c in range(n) if c not in pivots]
    if not free:
        raise ValueError("Không cân bằng được: kiểm tra lại công thức hai vế (có thể thiếu chất hoặc sai chỉ số).")
    note = ""
    vec = [Fraction(0)] * n
    chosen = None
    if len(free) > 1:
        # thử tìm nghiệm dương nhỏ nhất trong tổ hợp các biến tự do
        import itertools
        best = None
        for combo in itertools.product(range(0, 4), repeat=len(free)):
            if not any(combo):
                continue
            v = [Fraction(0)] * n
            for fc, k in zip(free, combo):
                v[fc] = Fraction(k)
            for ri, pc in enumerate(pivots):
                v[pc] = -sum(R[ri][fc] * v[fc] for fc in free)
            if all(x > 0 for x in v):
                tot = sum(v)
                if best is None or tot < best[0]:
                    best = (tot, v)
        if best is None:
            raise ValueError("Phương trình có vô số cách cân bằng hoặc thiếu chất (hệ số không duy nhất).")
        vec = best[1]
        note = "Phương trình có nhiều cách cân bằng về nguyên tố (thường là phản ứng oxi hóa - khử phức tạp); đã chọn nghiệm nhỏ nhất, hãy kiểm tra bằng bảo toàn electron."
        LAST_NOTE = note
    else:
        vec[free[0]] = Fraction(1)
        for ri, pc in enumerate(pivots):
            vec[pc] = -R[ri][free[0]]
    dl = 1
    for v in vec:
        dl = abs(dl * v.denominator) // gcd(dl, v.denominator)
    iv = [int(v * dl) for v in vec]
    if all(x < 0 for x in iv):
        iv = [-x for x in iv]
    if any(x <= 0 for x in iv):
        raise ValueError("Không tìm được hệ số nguyên dương (chất có thể không tham gia, hoặc cần thêm H2O, H+, e-).")
    g = 0
    for x in iv:
        g = gcd(g, x)
    iv = [x // g for x in iv]

    def fmt(items, coefs):
        return " + ".join(f"{'' if cf == 1 else cf}{sp}{suf}" for (sp, suf), cf in zip(items, coefs))
    return f"{fmt(lhs, iv[:n_l])} {arrow_str} {fmt(rhs, iv[n_l:])}"


# ==============================================================================
# 3. CHUYỂN PHƯƠNG TRÌNH -> UNICODE / LATEX / mhchem
# ==============================================================================
_COND_MAP = {"t^o": "t°", "to": "t°", "t°": "t°", "dpdd": "đpdd", "dpnc": "đpnc", "dp": "đp", "dac": "đặc", "loang": "loãng",
             "diep luc": "diệp lục", "xt": "xt", "as": "as", "men": "men", "mn": "màng ngăn", "p": "P", "criolit": "criolit",
             "nong": "nóng", "du": "dư", "kt": "kết tủa"}


def cond_to_unicode(cond: str) -> str:
    parts = []
    for tok in [c.strip() for c in cond.split(",") if c.strip()]:
        low = tok.lower()
        if low in _COND_MAP:
            parts.append(_COND_MAP[low])
            continue
        tok = re.sub(r"(\d+)\^o\s*C", r"\1°C", tok)
        tok = tok.replace("t^o", "t°").replace("^o", "°")
        tok = re.sub(r"\bdac\b", "đặc", tok)
        tok = re.sub(r"\bloang\b", "loãng", tok)
        tok = species_to_unicode(tok) if re.search(r"[A-Z]\d|[A-Z][a-z]?\d?$", tok) and " " not in tok.replace(" đặc", "").replace(" loãng", "") else \
            re.sub(r"([A-Za-z\)])(\d+)", lambda m: m.group(1) + m.group(2).translate(_SUBS), tok)
        parts.append(tok)
    return ", ".join(parts)


def species_to_unicode(sp: str) -> str:
    s = sp.strip()
    state = ""
    m = re.search(r"\((s|l|g|aq)\)$", s)
    if m:
        state, s = m.group(0), s[:m.start()]
    core, ch = split_charge(s)
    lead = re.match(r"^(\d+|n)(?=[A-Z\(\[])", core)
    lead_t = ""
    if lead:
        lead_t, core = lead.group(1), core[lead.end():]
    out, i = "", 0
    while i < len(core):
        c = core[i]
        if c == ".":
            out += "·"
            i += 1
            m2 = re.match(r"\d+", core[i:])
            if m2:
                out += m2.group(0)
                i += m2.end()
            continue
        if c.isdigit():
            m2 = re.match(r"\d+", core[i:])
            out += m2.group(0).translate(_SUBS) if out and (out[-1].isalpha() or out[-1] in ")]₀₁₂₃₄₅₆₇₈₉") else m2.group(0)
            i += m2.end()
            continue
        if c == "n" and out and out[-1] in ")]":
            out += "ₙ"
        elif c == "-" and i + 1 < len(core) and core[i + 1] in "C(N":
            out += "–"
        else:
            out += c
        i += 1
    chg = ""
    if ch:
        chg = (str(abs(ch)).translate(_SUPS) if abs(ch) > 1 else "") + ("⁺" if ch > 0 else "⁻")
    return f"{lead_t}{out}{chg}{state}"


def parse_equation_pieces(text: str):
    """-> list: ('sp', unicode) | ('plus',) | ('arrow', kind, top, bottom)"""
    t = normalize_chem_text(text).strip()
    pieces, pos = [], 0
    for am in _ARROW_RE.finditer(t):
        pieces += _side_pieces(t[pos:am.start()])
        kind = "eq" if am.group(1) in ("<=>", "<->", "⇌") else "fwd"
        conds = re.findall(r"\[([^\]]*)\]", am.group(2) or "")
        pieces.append(("arrow", kind, cond_to_unicode(conds[0]) if conds else "", cond_to_unicode(conds[1]) if len(conds) > 1 else ""))
        pos = am.end()
    pieces += _side_pieces(t[pos:])
    return pieces


def _side_pieces(side: str):
    out = []
    for i, raw in enumerate(_split_species(side)):
        if i:
            out.append(("plus",))
        item, mark = raw.strip(), ""
        mm = re.search(r"\s+(\^|v)$", item)
        if mm:
            item, mark = item[:mm.start()].strip(), "↑" if mm.group(1) == "^" else "↓"
        out.append(("sp", species_to_unicode(item) + mark))
    return out


def chem_to_latex(chem_text: str) -> str:
    """Xuất LaTeX thuần (dùng \\xrightarrow) — dán được vào Word/LaTeX/MathType."""
    pieces = parse_equation_pieces(chem_text)
    out = []
    for p in pieces:
        if p[0] == "plus":
            out.append("+")
        elif p[0] == "arrow":
            top = r"\mathrm{" + p[2].replace("°", r"^\circ ") + "}" if p[2] else ""
            cmd = r"\xrightarrow" if p[1] == "fwd" else r"\xleftrightarrow"
            out.append(f"{cmd}{{{top}}}" if top else (r"\longrightarrow" if p[1] == "fwd" else r"\rightleftharpoons"))
        else:
            u = p[1]
            tex = ""
            for ch in u:
                if ch in "₀₁₂₃₄₅₆₇₈₉ₙ":
                    tex += "_{" + (str("₀₁₂₃₄₅₆₇₈₉".index(ch)) if ch != "ₙ" else "n") + "}"
                elif ch in "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻":
                    tex += "^{" + "0123456789+-"["⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻".index(ch)] + "}"
                elif ch == "·":
                    tex += r"\cdot "
                elif ch == "↑":
                    tex += r"\uparrow "
                elif ch == "↓":
                    tex += r"\downarrow "
                else:
                    tex += ch
            tex = re.sub(r"\^\{(\d)\}\^\{([+-])\}", r"^{\1\2}", tex)
            out.append(r"\mathrm{" + tex + "}")
    return " ".join(out)


def chem_to_mhchem(chem_text: str) -> str:
    t = normalize_chem_text(chem_text).strip()
    t = t.replace("^o", r"^\circ").replace(" v", r" \downarrow").replace(" ^", r" \uparrow")
    return r"\ce{" + t + "}"


# ==============================================================================
# 4. VẼ PHƯƠNG TRÌNH HÓA HỌC (BỐ CỤC NGANG, NHIỀU MŨI TÊN, ĐIỀU KIỆN TRÊN/DƯỚI)
# ==============================================================================
@lru_cache(maxsize=128)
def render_chem_equation_bytes(text, font_size=26, color="#111827", bg_mode="transparent", fmt="png", dpi=220, max_px=1500):
    pieces = parse_equation_pieces(text)
    if not pieces:
        raise ValueError("Chưa có công thức.")
    fp_sp = FontProperties(family=["DejaVu Serif"], size=font_size)
    fp_cd = FontProperties(family=["DejaVu Sans"], size=max(9, font_size * 0.56))
    fig = Figure(figsize=(8, 2), dpi=100)
    FigureCanvasAgg(fig)
    rend = fig.canvas.get_renderer()
    gap = font_size * 0.55

    def tw(s, fp):
        if not s:
            return 0.0
        return rend.get_text_width_height_descent(s, fp, False)[0]
    items = []
    for p in pieces:
        if p[0] == "sp":
            items.append({"k": "sp", "t": p[1], "w": tw(p[1], fp_sp)})
        elif p[0] == "plus":
            items.append({"k": "plus", "t": "+", "w": tw("+", fp_sp)})
        else:
            cw_ = max(tw(p[2], fp_cd), tw(p[3], fp_cd))
            items.append({"k": "arrow", "kind": p[1], "top": p[2], "bot": p[3], "w": max(font_size * 2.4, cw_ + font_size * 0.8)})
    # chia dòng
    lines, cur, cur_w = [], [], 0.0
    for it in items:
        need = it["w"] + gap
        if cur and cur_w + need > max_px and it["k"] in ("plus", "arrow"):
            lines.append(cur)
            cur, cur_w = [], 0.0
        cur.append(it)
        cur_w += need
    if cur:
        lines.append(cur)
    line_w = [sum(i["w"] + gap for i in ln) - gap for ln in lines]
    W = max(line_w) + font_size * 1.2
    row_h = font_size * 3.4
    H = row_h * len(lines) + font_size * 0.4
    fig = Figure(figsize=(W / 100.0, H / 100.0), dpi=100)
    FigureCanvasAgg(fig)
    if bg_mode == "transparent":
        fig.patch.set_alpha(0.0)
        face = "none"
    else:
        face = "#0B1120" if bg_mode == "dark" else "#FFFFFF"
        fig.patch.set_facecolor(face)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    for li, ln in enumerate(lines):
        y = row_h * (li + 0.5) + font_size * 0.2
        x = (W - line_w[li]) / 2
        for it in ln:
            if it["k"] in ("sp", "plus"):
                ax.text(x, y, it["t"], fontproperties=fp_sp, color=color, ha="left", va="center_baseline")
            else:
                x1, x2 = x + 4, x + it["w"] - 4
                lw = max(1.3, font_size / 17.0)
                ys = [y - font_size * 0.06] if it["kind"] == "fwd" else [y - font_size * 0.20, y + font_size * 0.08]
                if it["kind"] == "fwd":
                    ax.annotate("", xy=(x2, ys[0]), xytext=(x1, ys[0]), arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=font_size * 0.6, shrinkA=0, shrinkB=0))
                else:
                    ax.annotate("", xy=(x2, ys[0]), xytext=(x1, ys[0]), arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=font_size * 0.55, shrinkA=0, shrinkB=0))
                    ax.annotate("", xy=(x1, ys[1]), xytext=(x2, ys[1]), arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=font_size * 0.55, shrinkA=0, shrinkB=0))
                top_y = ys[0] - font_size * 0.28
                if it["top"]:
                    ax.text((x1 + x2) / 2, top_y, it["top"], fontproperties=fp_cd, color=color, ha="center", va="bottom")
                if it["bot"]:
                    ax.text((x1 + x2) / 2, ys[-1] + font_size * 0.30, it["bot"], fontproperties=fp_cd, color=color, ha="center", va="top")
            x += it["w"] + gap
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi if fmt != "svg" else 100, bbox_inches="tight", pad_inches=0.12,
                transparent=(bg_mode == "transparent"), facecolor=face)
    return buf.getvalue()




# ==============================================================================
# 5. VẼ CÔNG THỨC TOÁN (LATEX -> ẢNH)
# ==============================================================================
_MATHTEXT_INIT = False


def _ensure_mathtext_rc():
    global _MATHTEXT_INIT
    if not _MATHTEXT_INIT:
        matplotlib.rcParams.update({
            "mathtext.fontset": "custom", "mathtext.rm": "DejaVu Serif",
            "mathtext.it": "DejaVu Serif:italic", "mathtext.bf": "DejaVu Serif:bold",
            "mathtext.fallback": "stix", "font.family": "DejaVu Serif",
        })
        _MATHTEXT_INIT = True


def _sanitize_mathtext(latex: str) -> str:
    s = latex.strip()
    s = s.replace(r"\text{", r"\mathrm{")
    s = re.sub(r"\\pmod\{([^{}]+)\}", r"\\ (\\mathrm{mod}\\ \1)", s)
    s = s.replace(r"\le ", r"\leq ").replace(r"\ge ", r"\geq ").replace(r"\ne ", r"\neq ")
    s = s.replace(r"\iff", r"\Leftrightarrow").replace(r"\implies", r"\Rightarrow")
    s = s.replace(r"\to ", r"\rightarrow ").replace(r"\to}", r"\rightarrow}")
    s = s.replace(r"\dots", r"\ldots")
    return s


@lru_cache(maxsize=128)
def render_formula_to_bytes(
    latex: str,
    font_size: int = 24,
    color: str = "#111827",
    bg_mode: str = "transparent",
    display_mode: bool = True,
    fmt: str = "png",
    dpi: int = 220,
) -> bytes:
    expr = _sanitize_mathtext(latex)
    if not expr:
        raise ValueError("Chưa có công thức.")

    _ensure_mathtext_rc()
    fig = Figure(figsize=(8, 1.8), dpi=dpi)
    FigureCanvasAgg(fig)
    if bg_mode == "transparent":
        fig.patch.set_alpha(0.0)
        facecolor = "none"
    elif bg_mode == "dark":
        fig.patch.set_facecolor("#0B1120")
        facecolor = "#0B1120"
    else:
        fig.patch.set_facecolor("#FFFFFF")
        facecolor = "#FFFFFF"

    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)

    fs = font_size if display_mode else max(12, int(font_size * 0.78))

    if r"\begin{cases}" in expr:
        _draw_cases_expr(ax, expr, fs, color)
    elif r"\begin{bmatrix}" in expr or r"\begin{pmatrix}" in expr:
        _draw_matrix_expr(ax, expr, fs, color)
    else:
        ax.text(0.5, 0.5, f"${expr}$", fontsize=fs, color=color, ha="center", va="center", transform=ax.transAxes)

    buf = io.BytesIO()
    fig.savefig(
        buf, format=fmt, dpi=dpi, bbox_inches="tight", pad_inches=0.18,
        transparent=(bg_mode == "transparent"), facecolor=facecolor,
    )
    return buf.getvalue()


def _draw_cases_expr(ax, expr: str, fs: int, color: str):
    m = re.search(r"\\begin\{cases\}(.*?)\\end\{cases\}", expr, flags=re.DOTALL)
    prefix = expr[:m.start()].strip()
    lines = [ln.strip() for ln in m.group(1).strip().split(r"\\") if ln.strip()]
    x_cursor = 1.0
    if prefix:
        ax.text(x_cursor, 1.5, f"${prefix}$", fontsize=fs, color=color, ha="left", va="center")
        x_cursor += max(0.8, len(prefix) * 0.12)
    ax.text(x_cursor, 1.5, "{", fontsize=fs * (1.2 + 0.55 * len(lines)), color=color, ha="center", va="center")
    step = 0.52
    start_y = 1.5 + (len(lines) - 1) * step / 2.0
    for i, ln in enumerate(lines):
        ax.text(x_cursor + 0.38, start_y - i * step, f"${ln}$", fontsize=fs * 0.92, color=color, ha="left", va="center")


def _draw_matrix_expr(ax, expr: str, fs: int, color: str):
    is_p = r"\begin{pmatrix}" in expr
    env = "pmatrix" if is_p else "bmatrix"
    m = re.search(rf"\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}", expr, flags=re.DOTALL)
    prefix = expr[:m.start()].strip()
    suffix = expr[m.end():].strip()
    rows = [[c.strip() for c in r.split("&")] for r in m.group(1).strip().split(r"\\") if r.strip()]
    n_rows, n_cols = len(rows), max(len(r) for r in rows)
    x_cursor = 1.4
    if prefix:
        ax.text(x_cursor, 1.5, f"${prefix}$", fontsize=fs, color=color, ha="right", va="center")
        x_cursor += 0.35

    col_w, row_h = 0.92, 0.54
    x_left = x_cursor
    x_right = x_left + n_cols * col_w + 0.2
    half_h = (n_rows * row_h) / 2.0 + 0.12
    lw = max(1.6, fs / 14.0)
    if is_p:
        ax.text(x_left - 0.05, 1.5, "(", fontsize=fs * (1.1 + 0.5 * n_rows), color=color, ha="center", va="center")
        ax.text(x_right + 0.05, 1.5, ")", fontsize=fs * (1.1 + 0.5 * n_rows), color=color, ha="center", va="center")
    else:
        tick = 0.14
        ax.plot([x_left + tick, x_left, x_left, x_left + tick], [1.5 + half_h, 1.5 + half_h, 1.5 - half_h, 1.5 - half_h], color=color, lw=lw)
        ax.plot([x_right - tick, x_right, x_right, x_right - tick], [1.5 + half_h, 1.5 + half_h, 1.5 - half_h, 1.5 - half_h], color=color, lw=lw)

    start_y = 1.5 + (n_rows - 1) * row_h / 2.0
    for i, r_cells in enumerate(rows):
        for j, cell in enumerate(r_cells):
            ax.text(x_left + 0.1 + (j + 0.5) * col_w, start_y - i * row_h, f"${cell}$", fontsize=fs * 0.9, color=color, ha="center", va="center")
    if suffix:
        ax.text(x_right + 0.32, 1.5, f"${suffix}$", fontsize=fs, color=color, ha="left", va="center")



def bytes_to_qpixmap(png_bytes: bytes) -> QPixmap:
    pix = QPixmap()
    pix.loadFromData(png_bytes, "PNG")
    return pix



# ==============================================================================
# 4. CẤU HÌNH ELECTRON, LỚP BOHR & SƠ ĐỒ Ô ORBITAL
# ==============================================================================
MADELUNG_ORDER = [
    (1, "s", 2), (2, "s", 2), (2, "p", 6), (3, "s", 2), (3, "p", 6),
    (4, "s", 2), (3, "d", 10), (4, "p", 6), (5, "s", 2), (4, "d", 10),
    (5, "p", 6), (6, "s", 2), (4, "f", 14), (5, "d", 10), (6, "p", 6),
    (7, "s", 2), (5, "f", 14), (6, "d", 10), (7, "p", 6),
]

SUBSHELL_EXCEPTIONS = {
    24: {(4, "s"): 1, (3, "d"): 5}, 29: {(4, "s"): 1, (3, "d"): 10},
    41: {(5, "s"): 1, (4, "d"): 4}, 42: {(5, "s"): 1, (4, "d"): 5},
    44: {(5, "s"): 1, (4, "d"): 7}, 45: {(5, "s"): 1, (4, "d"): 8},
    46: {(5, "s"): 0, (4, "d"): 10}, 47: {(5, "s"): 1, (4, "d"): 10},
    57: {(4, "f"): 0, (5, "d"): 1}, 58: {(4, "f"): 1, (5, "d"): 1},
    64: {(4, "f"): 7, (5, "d"): 1}, 78: {(6, "s"): 1, (5, "d"): 9},
    79: {(6, "s"): 1, (5, "d"): 10}, 89: {(5, "f"): 0, (6, "d"): 1},
    90: {(5, "f"): 0, (6, "d"): 2}, 91: {(5, "f"): 2, (6, "d"): 1},
    92: {(5, "f"): 3, (6, "d"): 1}, 93: {(5, "f"): 4, (6, "d"): 1},
    96: {(5, "f"): 7, (6, "d"): 1}, 103: {(5, "f"): 14, (6, "d"): 0, (7, "p"): 1},
}

NOBLE_CORES = [(86, "[Rn]"), (54, "[Xe]"), (36, "[Kr]"), (18, "[Ar]"), (10, "[Ne]"), (2, "[He]")]
SHELL_NAMES = ["K", "L", "M", "N", "O", "P", "Q"]
ORBITAL_BOX_COUNT = {"s": 1, "p": 3, "d": 5, "f": 7}
SUPERSCRIPT_MAP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def compute_electron_structure(z: int) -> dict:
    occ = {}
    rem = z
    for n, orb, cap in MADELUNG_ORDER:
        if rem <= 0:
            break
        take = min(rem, cap)
        occ[(n, orb)] = take
        rem -= take
    if z in SUBSHELL_EXCEPTIONS:
        for k, v in SUBSHELL_EXCEPTIONS[z].items():
            if v == 0:
                occ.pop(k, None)
            else:
                occ[k] = v

    orb_order = {"s": 0, "p": 1, "d": 2, "f": 3}
    sorted_subs = sorted(occ.items(), key=lambda kv: (kv[0][0], orb_order[kv[0][1]]))
    shells_dict = defaultdict(int)
    for (n, _), cnt in sorted_subs:
        shells_dict[n] += cnt
    shells = [shells_dict[i] for i in range(1, max(shells_dict.keys()) + 1)]
    full_str = " ".join(f"{n}{o}{str(c).translate(SUPERSCRIPT_MAP)}" for (n, o), c in sorted_subs)

    core_str, core_z = "", 0
    for nz, label in NOBLE_CORES:
        if z > nz:
            core_z, core_str = nz, label
            break

    if core_z:
        core_occ = compute_electron_structure(core_z)["subshells_dict"]
        val_parts = [f"{n}{o}{str(c).translate(SUPERSCRIPT_MAP)}" for (n, o), c in sorted_subs if core_occ.get((n, o), 0) != c]
        condensed_str = f"{core_str} " + " ".join(val_parts)
    else:
        condensed_str = full_str

    orbitals_by_shell = defaultdict(list)
    unpaired = 0
    for (n, o), c in sorted_subs:
        n_boxes = ORBITAL_BOX_COUNT[o]
        boxes = [0] * n_boxes
        for idx in range(min(c, n_boxes)):
            boxes[idx] = 1
        for idx in range(max(0, c - n_boxes)):
            boxes[idx] = 2
        unpaired += sum(1 for b in boxes if b == 1)
        orbitals_by_shell[n].append((f"{n}{o}{c}", boxes))

    last_orb = "s"
    for n, o, _ in MADELUNG_ORDER:
        if (n, o) in occ and occ[(n, o)] > 0:
            last_orb = o

    return {
        "z": z, "subshells_dict": occ, "sorted_subshells": sorted_subs,
        "shells": shells, "full_config": full_str, "condensed_config": condensed_str,
        "orbitals_by_shell": dict(orbitals_by_shell), "unpaired": unpaired, "block": last_orb,
    }





# ==============================================================================
# 7. QUÉT ẢNH CÔNG THỨC (OCR): Gemini online (cần API key miễn phí) hoặc offline nếu máy có thư viện
# ==============================================================================
_RAPID_OCR_INSTANCE = None
_P2T_INSTANCE = None
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash", "gemini-1.5-flash"]


def available_ocr_engines():
    engines = [("gemini", "Gemini AI (Online, cần API key miễn phí)")]
    if HAS_RAPID_OCR:
        engines.append(("rapid", "RapidLatexOCR (Offline)"))
    if HAS_PIX2TEX:
        engines.append(("pix2tex", "pix2tex (Offline)"))
    return engines


class OcrThread(QThread):
    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, image_bytes: bytes, engine_mode: str = "gemini", api_key: str = "", target_kind: str = "math", parent=None):
        super().__init__(parent)
        self.image_bytes = image_bytes
        self.engine_mode = engine_mode
        self.api_key = api_key.strip()
        self.target_kind = target_kind

    def run(self):
        global _RAPID_OCR_INSTANCE, _P2T_INSTANCE
        try:
            if self.engine_mode == "rapid":
                if _RAPID_OCR_INSTANCE is None:
                    _RAPID_OCR_INSTANCE = _RapidLatexOCR()
                res, _ = _RAPID_OCR_INSTANCE(self.image_bytes)
                self.result_ready.emit(str(res).strip())
            elif self.engine_mode == "pix2tex":
                from PIL import Image
                if _P2T_INSTANCE is None:
                    _P2T_INSTANCE = _Pix2Tex()
                self.result_ready.emit(str(_P2T_INSTANCE(Image.open(io.BytesIO(self.image_bytes)))).strip())
            else:
                self._run_gemini()
        except urllib.error.HTTPError as e:
            msg = {400: "Yêu cầu không hợp lệ (ảnh lỗi hoặc API key sai).", 401: "API key không đúng.", 403: "API key bị từ chối hoặc chưa bật Gemini API.",
                   429: "Đã vượt giới hạn miễn phí, hãy thử lại sau ít phút."}.get(e.code, f"HTTP {e.code}")
            self.error_occurred.emit(f"Lỗi gọi Gemini: {msg}")
        except urllib.error.URLError:
            self.error_occurred.emit("Không kết nối được Internet. Chế độ Gemini cần mạng.")
        except Exception as exc:
            self.error_occurred.emit(f"Lỗi nhận diện ảnh: {exc}")

    def _run_gemini(self):
        if not self.api_key:
            self.error_occurred.emit("Chưa nhập Gemini API Key.\nLấy key miễn phí tại https://aistudio.google.com/apikey rồi dán vào ô API Key.")
            return
        prompts = {
            "math": "Trích xuất chính xác công thức Toán học trong ảnh sang mã LaTeX thuần. Chỉ trả về mã LaTeX, không giải thích, không bọc ``` hoặc $.",
            "chem": "Trích xuất chính xác công thức/phương trình hóa học trong ảnh sang cú pháp đơn giản: chỉ số viết liền (H2SO4), điện tích dạng Fe^{3+}, mũi tên -> hoặc <=>, điều kiện dạng ->[t^o, xt]. Ví dụ: 2H2 + O2 ->[t^o] 2H2O. Chỉ trả về chuỗi công thức.",
            "smiles": "Nhận diện cấu trúc phân tử hữu cơ trong ảnh và trả về mã SMILES hợp lệ. Chỉ trả về đúng một chuỗi SMILES, không giải thích.",
            "text": "Chép lại chính xác toàn bộ chữ và công thức toán trong ảnh. Công thức viết dạng LaTeX trong dấu $...$. Không giải thích thêm.",
        }
        b64 = base64.b64encode(self.image_bytes).decode("ascii")
        payload = json.dumps({"contents": [{"parts": [{"text": prompts.get(self.target_kind, prompts["math"])},
                                                      {"inline_data": {"mime_type": "image/png", "data": b64}}]}]}).encode("utf-8")
        last_err = None
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=40) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
                if self.target_kind in ("math", "chem", "smiles"):
                    text = text.strip("$").strip()
                self.result_ready.emit(text)
                return
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code in (404, 400) and model != GEMINI_MODELS[-1]:
                    continue
                raise
        if last_err:
            raise last_err


# ==============================================================================
# 8. ĐỌC PHÁT ÂM GIỌNG NÓI OFFLINE (WINDOWS SYSTEM.SPEECH)
# ==============================================================================
class SpeechThread(QThread):
    finished_signal = Signal()

    def __init__(self, text: str, rate: float = 1.0, parent=None):
        super().__init__(parent)
        self.text = text
        self.rate = rate
        self._proc = None

    def run(self):
        try:
            safe_txt = self.text.replace("'", "''").replace('"', "")
            sapi_rate = int(max(-5, min(5, round((self.rate - 1.0) * 6))))
            if sys.platform == "win32":
                ps_cmd = (
                    "Add-Type -AssemblyName System.Speech; "
                    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    f"$s.Rate = {sapi_rate}; "
                    f"$s.Speak('{safe_txt}');"
                )
                self._proc = subprocess.Popen(
                    ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                self._proc.wait()
            elif sys.platform == "darwin":
                self._proc = subprocess.Popen(["say", safe_txt])
                self._proc.wait()
        except Exception:
            pass
        self.finished_signal.emit()

    def stop(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass