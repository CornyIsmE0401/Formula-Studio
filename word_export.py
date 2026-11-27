# -*- coding: utf-8 -*-
"""word_export.py - Đưa công thức / phương trình hóa học / hình vẽ sang Microsoft Word.

* latex_to_omml(): chuyển LaTeX -> OMML (công thức GỐC của Word, sửa được bằng Equation Editor của Word).
* build_docx(): tạo file .docx (công thức là equation thật; hình vẽ là ảnh PNG).
* insert_into_word(): chèn thẳng vào Word đang mở tại vị trí con trỏ (Windows + pywin32, qua COM, dùng Flat OPC).
"""
import base64
import io
import re
import struct
import zipfile
from xml.sax.saxutils import escape

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

SYM = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι",
    "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "varpi": "ϖ", "rho": "ρ", "varrho": "ϱ", "sigma": "σ", "varsigma": "ς", "tau": "τ",
    "upsilon": "υ", "phi": "φ", "varphi": "ϕ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π",
    "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω", "cdot": "⋅", "times": "×", "div": "÷", "pm": "±", "mp": "∓", "leq": "≤", "le": "≤", "geq": "≥",
    "ge": "≥", "neq": "≠", "ne": "≠", "approx": "≈", "equiv": "≡", "sim": "∼", "simeq": "≃", "propto": "∝", "infty": "∞", "to": "→", "rightarrow": "→", "leftarrow": "←",
    "leftrightarrow": "↔", "Rightarrow": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔", "Longrightarrow": "⟹", "longrightarrow": "⟶", "mapsto": "↦", "in": "∈", "notin": "∉",
    "ni": "∋", "subset": "⊂", "supset": "⊃", "subseteq": "⊆", "supseteq": "⊇", "cup": "∪", "cap": "∩", "emptyset": "∅", "varnothing": "∅", "forall": "∀", "exists": "∃",
    "partial": "∂", "nabla": "∇", "angle": "∠", "perp": "⊥", "parallel": "∥", "triangle": "△", "circ": "∘", "ldots": "…", "cdots": "⋯", "dots": "…", "vdots": "⋮",
    "ddots": "⋱", "hbar": "ℏ", "ell": "ℓ", "Re": "ℜ", "Im": "ℑ", "aleph": "ℵ", "prime": "′", "degree": "°", "star": "⋆", "ast": "∗", "oplus": "⊕", "otimes": "⊗",
    "land": "∧", "lor": "∨", "neg": "¬", "therefore": "∴", "because": "∵", "mid": "∣", "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉",
    "uparrow": "↑", "downarrow": "↓", "rightleftharpoons": "⇌", "sqrt": "√", "ll": "≪", "gg": "≫", "setminus": "∖", "bullet": "∙", "square": "□", "checkmark": "✓",
}
FUNCS = {"sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "log", "ln", "lg", "exp", "max", "min", "det", "gcd", "deg", "dim", "ker", "sup", "inf", "arg", "mod"}
NARY = {"sum": "∑", "prod": "∏", "int": "∫", "iint": "∬", "iiint": "∭", "oint": "∮", "bigcup": "⋃", "bigcap": "⋂", "coprod": "∐"}
ACCENT = {"vec": "→", "hat": "̂", "widehat": "̂", "tilde": "̃", "widetilde": "̃", "dot": "̇", "ddot": "̈", "check": "̌", "acute": "́", "grave": "̀"}
SPACE = {",": " ", ";": " ", ":": " ", "!": "", "quad": "  ", "qquad": "    ", " ": " "}
DELIM = {"(": "(", ")": ")", "[": "[", "]": "]", "{": "{", "}": "}", "|": "|", "\\{": "{", "\\}": "}", "\\|": "‖", ".": "", "\\langle": "⟨", "\\rangle": "⟩",
         "\\lfloor": "⌊", "\\rfloor": "⌋", "\\lceil": "⌈", "\\rceil": "⌉", "/": "/", "\\vert": "|", "\\Vert": "‖"}


# ==============================================================================
# 1. PHÂN TÍCH LATEX
# ==============================================================================
def _tokenize(s):
    toks, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+)", s[i:])
            if m:
                toks.append(("cmd", m.group(1)))
                i += m.end()
            else:
                toks.append(("cmd", s[i + 1] if i + 1 < len(s) else ""))
                i += 2
        elif c in "{}^_&":
            toks.append((c, c))
            i += 1
        elif c.isspace():
            i += 1
        else:
            toks.append(("ch", c))
            i += 1
    return toks


class _P:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def eat(self):
        tk = self.peek()
        self.i += 1
        return tk

    def seq(self, stop=()):
        out = []
        while self.i < len(self.t):
            k, v = self.peek()
            if (k == "}" and "}" in stop) or (k == "&" and "&" in stop) or (k == "cmd" and v in stop):
                break
            if k == "cmd" and v == "\\" and "\\" in stop:
                break
            if k == "}" and "}" not in stop:
                self.eat()
                continue
            out.append(self.script(self.atom()))
        return out

    def group(self):
        if self.peek()[0] == "{":
            self.eat()
            s = self.seq(("}",))
            if self.peek()[0] == "}":
                self.eat()
            return s
        a = self.atom()
        return [a] if a else []

    def script(self, base):
        sub = sup = None
        while self.peek()[0] in ("^", "_"):
            k = self.eat()[0]
            g = self.group()
            if k == "^":
                sup = g
            else:
                sub = g
        if sub is None and sup is None:
            return base
        return ("script", base, sub, sup)

    def raw_text(self):
        """Đọc {...} thành chuỗi chữ thô (cho \\mathrm, \\text, tên cột...)."""
        if self.peek()[0] != "{":
            return self.eat()[1] or ""
        self.eat()
        depth, out = 1, ""
        while self.i < len(self.t) and depth:
            k, v = self.eat()
            if k == "{":
                depth += 1
            elif k == "}":
                depth -= 1
                if not depth:
                    break
            elif k == "cmd":
                out += SYM.get(v, " " if v in SPACE else "")
            else:
                out += v
        return out

    def atom(self):
        k, v = self.eat()
        if k is None:
            return ("text", "")
        if k == "{":
            s = self.seq(("}",))
            if self.peek()[0] == "}":
                self.eat()
            return ("row", s)
        if k in ("^", "_"):
            self.i -= 1
            return ("text", "")
        if k == "ch":
            return ("text", v)
        if k == "&":
            return ("text", "")
        name = v
        if name in ("frac", "dfrac", "tfrac"):
            return ("frac", self.group(), self.group())
        if name == "binom":
            return ("binom", self.group(), self.group())
        if name == "sqrt":
            deg = None
            if self.peek() == ("ch", "["):
                self.eat()
                deg = []
                while self.peek() != ("ch", "]") and self.peek()[0]:
                    deg.append(self.script(self.atom()))
                self.eat()
            return ("sqrt", deg, self.group())
        if name in ("mathrm", "text", "mathbf", "textbf", "operatorname", "mathit", "textit", "mbox", "mathsf", "mathtt"):
            if name in ("mathbf", "textbf"):
                return ("styled", "b", self.raw_text())
            return ("upgroup", self.group())
        if name in ("mathbb", "mathcal"):
            t = self.raw_text()
            bb = {"R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ", "P": "ℙ"}
            return ("up", "".join(bb.get(ch, ch) for ch in t)) if name == "mathbb" else ("text", t)
        if name in ("overline", "bar"):
            return ("bar", self.group())
        if name == "underline":
            return ("bar", self.group(), "bot")
        if name in ACCENT:
            return ("acc", ACCENT[name], self.group())
        if name in ("xrightarrow", "xleftrightarrow", "xleftarrow"):
            return ("xarrow", {"xrightarrow": "⟶", "xleftrightarrow": "⇌", "xleftarrow": "⟵"}[name], self.group())
        if name in NARY:
            return ("nary", NARY[name])
        if name == "lim":
            return ("lim",)
        if name == "left":
            kk, vv = self.eat()
            beg = DELIM.get(("\\" + vv) if kk == "cmd" else vv, vv if kk == "ch" else "")
            body = self.seq(("right",))
            end = ""
            if self.peek() == ("cmd", "right"):
                self.eat()
                kk, vv = self.eat()
                end = DELIM.get(("\\" + vv) if kk == "cmd" else vv, vv if kk == "ch" else "")
            return ("delim", beg, end, body)
        if name == "begin":
            env = self.raw_text()
            if env in ("array", "tabular", "alignedat") and self.peek()[0] == "{":
                self.raw_text()
            rows, cur, cell = [], [], []
            while self.i < len(self.t):
                kk, vv = self.peek()
                if kk == "cmd" and vv == "end":
                    self.eat()
                    self.raw_text()
                    break
                if kk == "&":
                    self.eat()
                    cur.append(cell)
                    cell = []
                    continue
                if kk == "cmd" and vv == "\\":
                    self.eat()
                    cur.append(cell)
                    rows.append(cur)
                    cur, cell = [], []
                    continue
                cell.append(self.script(self.atom()))
            if cell or cur:
                cur.append(cell)
                rows.append(cur)
            return ("env", env, rows)
        if name in SPACE:
            return ("text", SPACE[name])
        if name in FUNCS:
            return ("up", name)
        if name in SYM:
            return ("text", SYM[name])
        if name in ("{", "}", "%", "$", "#", "_", "&"):
            return ("text", name)
        if name == "\\":
            return ("text", " ")
        if name in ("right", "end"):
            return ("text", "")
        return ("up", name)


# ==============================================================================
# 2. PHÁT OMML
# ==============================================================================
def _run(text, upright=False, bold=False):
    if text == "":
        return ""
    props = ""
    if upright or bold:
        props = "<m:rPr>" + ("<m:sty m:val=\"b\"/>" if bold and not upright else ("<m:sty m:val=\"p\"/>" if upright and not bold else "<m:sty m:val=\"bi\"/>" if False else "<m:sty m:val=\"p\"/>")) + "</m:rPr>"
    return f"<m:r>{props}<m:t xml:space=\"preserve\">{escape(text)}</m:r>".replace("</m:r>", "</m:t></m:r>", 1) if False else f"<m:r>{props}<m:t xml:space=\"preserve\">{escape(text)}</m:t></m:r>"


def _emit_list(nodes, up=False):
    out, i = [], 0
    while i < len(nodes):
        n = nodes[i]
        if n[0] in ("text", "up") and not (n[0] == "text" and n[1] == ""):
            j, buf, upr = i, "", up or n[0] == "up"
            while j < len(nodes) and nodes[j][0] in ("text", "up") and (up or nodes[j][0] == "up") == upr:
                buf += nodes[j][1]
                j += 1
            out.append(_run(buf, upr))
            i = j
            continue
        base = n[1] if n[0] == "script" else n
        kind = base[0]
        if kind == "nary":
            sub = sup = None
            if n[0] == "script":
                sub, sup = n[2], n[3]
            operand = ""
            if i + 1 < len(nodes):
                operand = _emit_node(nodes[i + 1], up)
                i += 1
            chr_ = base[1]
            loc = "subSup" if chr_ in "∫∬∭∮" else "undOvr"
            out.append(f"<m:nary><m:naryPr><m:chr m:val=\"{chr_}\"/><m:limLoc m:val=\"{loc}\"/>"
                       f"{'' if sub else '<m:subHide m:val=\"1\"/>'}{'' if sup else '<m:supHide m:val=\"1\"/>'}</m:naryPr>"
                       f"<m:sub>{_emit_list(sub or [], up)}</m:sub><m:sup>{_emit_list(sup or [], up)}</m:sup><m:e>{operand}</m:e></m:nary>")
        elif kind == "lim":
            sub = n[2] if n[0] == "script" else None
            if sub:
                out.append(f"<m:limLow><m:e>{_run('lim', True)}</m:e><m:lim>{_emit_list(sub, up)}</m:lim></m:limLow>")
            else:
                out.append(_run("lim", True))
        else:
            out.append(_emit_node(n, up))
        i += 1
    return "".join(out)


def _emit_node(n, up=False):
    k = n[0]
    if k == "text":
        t = n[1]
        # chữ số và toán tử: giữ nguyên; chữ cái: nghiêng (mặc định Word) trừ khi up
        return _run(t, up)
    if k == "up":
        return _run(n[1], True)
    if k == "styled":
        return _run(n[2], False, True)
    if k == "row":
        return _emit_list(n[1], up)
    if k == "upgroup":
        return _emit_list(n[1], True)
    if k == "script":
        base, sub, sup = n[1], n[2], n[3]
        if base[0] in ("nary", "lim"):
            return _emit_list([n], up)
        b = _emit_node(base, up) or "<m:r><m:t></m:t></m:r>"
        if base[0] == "xarrow":
            return b
        if sub is not None and sup is not None:
            return f"<m:sSubSup><m:e>{b}</m:e><m:sub>{_emit_list(sub, up)}</m:sub><m:sup>{_emit_list(sup, up)}</m:sup></m:sSubSup>"
        if sup is not None:
            if len(sup) == 1 and sup[0] == ("text", "∘"):
                return f"<m:sSup><m:e>{b}</m:e><m:sup>{_run('°')}</m:sup></m:sSup>"
            return f"<m:sSup><m:e>{b}</m:e><m:sup>{_emit_list(sup, up)}</m:sup></m:sSup>"
        return f"<m:sSub><m:e>{b}</m:e><m:sub>{_emit_list(sub, up)}</m:sub></m:sSub>"
    if k == "frac":
        return f"<m:f><m:num>{_emit_list(n[1], up)}</m:num><m:den>{_emit_list(n[2], up)}</m:den></m:f>"
    if k == "binom":
        return (f"<m:d><m:dPr><m:begChr m:val=\"(\"/><m:endChr m:val=\")\"/></m:dPr><m:e><m:f><m:fPr><m:type m:val=\"noBar\"/></m:fPr>"
                f"<m:num>{_emit_list(n[1], up)}</m:num><m:den>{_emit_list(n[2], up)}</m:den></m:f></m:e></m:d>")
    if k == "sqrt":
        if n[1]:
            return f"<m:rad><m:radPr/><m:deg>{_emit_list(n[1], up)}</m:deg><m:e>{_emit_list(n[2], up)}</m:e></m:rad>"
        return f"<m:rad><m:radPr><m:degHide m:val=\"1\"/></m:radPr><m:deg/><m:e>{_emit_list(n[2], up)}</m:e></m:rad>"
    if k == "bar":
        pos = n[2] if len(n) > 2 else "top"
        return f"<m:bar><m:barPr><m:pos m:val=\"{pos}\"/></m:barPr><m:e>{_emit_list(n[1], up)}</m:e></m:bar>"
    if k == "acc":
        return f"<m:acc><m:accPr><m:chr m:val=\"{n[1]}\"/></m:accPr><m:e>{_emit_list(n[2], up)}</m:e></m:acc>"
    if k == "xarrow":
        lim = _emit_list(n[2], up)
        arrow = _run(n[1])
        if not n[2]:
            return arrow
        return f"<m:limUpp><m:e>{arrow}</m:e><m:lim>{lim}</m:lim></m:limUpp>"
    if k == "delim":
        return f"<m:d><m:dPr><m:begChr m:val=\"{escape(n[1])}\"/><m:endChr m:val=\"{escape(n[2])}\"/></m:dPr><m:e>{_emit_list(n[3], up)}</m:e></m:d>"
    if k == "env":
        env, rows = n[1], n[2]
        if env == "cases":
            eq = "".join(f"<m:e>{_emit_list(sum(([c, ('text', ' ')] for c in r), [])[:-1] if False else [x for c in r for x in c], up)}</m:e>" for r in rows)
            return f"<m:d><m:dPr><m:begChr m:val=\"{{\"/><m:endChr m:val=\"\"/></m:dPr><m:e><m:eqArr>{''.join(f'<m:e>{_emit_list([x for c in r for x in c], up)}</m:e>' for r in rows)}</m:eqArr></m:e></m:d>"
        mrows = "".join("<m:mr>" + "".join(f"<m:e>{_emit_list(c, up)}</m:e>" for c in r) + "</m:mr>" for r in rows)
        mat = f"<m:m><m:mPr><m:mcs><m:mc><m:mcPr><m:count m:val=\"{max(len(r) for r in rows) if rows else 1}\"/><m:mcJc m:val=\"center\"/></m:mcPr></m:mc></m:mcs></m:mPr>{mrows}</m:m>"
        br = {"pmatrix": ("(", ")"), "bmatrix": ("[", "]"), "Bmatrix": ("{", "}"), "vmatrix": ("|", "|"), "Vmatrix": ("‖", "‖")}.get(env)
        if br:
            return f"<m:d><m:dPr><m:begChr m:val=\"{br[0]}\"/><m:endChr m:val=\"{br[1]}\"/></m:dPr><m:e>{mat}</m:e></m:d>"
        return mat
    if k in ("nary", "lim"):
        return _emit_list([n], up)
    return ""


def latex_to_omml(latex: str, display=True) -> str:
    """LaTeX -> <m:oMathPara>/<m:oMath> (chuỗi XML, chưa có khai báo namespace)."""
    s = latex.strip()
    s = re.sub(r"^\$+|\$+$", "", s).strip()
    p = _P(_tokenize(s))
    nodes = []
    while p.i < len(p.t):
        nodes.append(p.script(p.atom()))
    body = _emit_list(nodes)
    return f"<m:oMathPara><m:oMath>{body}</m:oMath></m:oMathPara>" if display else f"<m:oMath>{body}</m:oMath>"


# ==============================================================================
# 3. TẠO .DOCX / FLAT OPC
# ==============================================================================
def _png_size(data: bytes):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    return 600, 300


def _para(inner, center=False, small=False):
    ppr = "<w:pPr>" + ("<w:jc w:val=\"center\"/>" if center else "") + "<w:spacing w:before=\"60\" w:after=\"100\"/></w:pPr>"
    return f"<w:p>{ppr}{inner}</w:p>"


def _text_run(t, small=False, bold=False, color=None):
    rpr = ("<w:rPr>" + ("<w:b/>" if bold else "") + (f"<w:color w:val=\"{color}\"/>" if color else "") + ("<w:sz w:val=\"18\"/>" if small else "") + "</w:rPr>")
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{escape(t)}</w:t></w:r>"


def _build_parts(items):
    """-> (document_xml, rels:list[(id,target)], media:dict[name->bytes])"""
    paras, rels, media = [], [], {}
    for it in items:
        kind = it["kind"]
        if it.get("title"):
            paras.append(_para(_text_run(it["title"], True, False, "6B7280")))
        if kind == "math":
            try:
                paras.append(f"<w:p><w:pPr><w:spacing w:before=\"40\" w:after=\"120\"/></w:pPr>{latex_to_omml(it['latex'])}</w:p>")
            except Exception:
                paras.append(_para(_text_run(it["latex"])))
        elif kind == "chem":
            import formula_engine as fe
            try:
                latex = fe.chem_to_latex(it["text"])
                paras.append(f"<w:p><w:pPr><w:spacing w:before=\"40\" w:after=\"120\"/></w:pPr>{latex_to_omml(latex)}</w:p>")
            except Exception:
                paras.append(_para(_text_run(it["text"])))
        elif kind == "text":
            paras.append(_para(_text_run(it["text"])))
        elif kind == "image":
            n = len(media) + 1
            name = f"image{n}.png"
            media[name] = it["png"]
            rid = f"rIdImg{n}"
            rels.append((rid, "media/" + name))
            wpx, hpx = _png_size(it["png"])
            dpi = float(it.get("dpi", 200))
            cx, cy = int(wpx / dpi * 914400), int(hpx / dpi * 914400)
            maxw = int(6.0 * 914400)
            if cx > maxw:
                cy, cx = int(cy * maxw / cx), maxw
            draw = (f"<w:r><w:drawing><wp:inline distT=\"0\" distB=\"0\" distL=\"0\" distR=\"0\" xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\">"
                    f"<wp:extent cx=\"{cx}\" cy=\"{cy}\"/><wp:docPr id=\"{n}\" name=\"Hinh {n}\"/>"
                    f"<a:graphic xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\"><a:graphicData uri=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">"
                    f"<pic:pic xmlns:pic=\"http://schemas.openxmlformats.org/drawingml/2006/picture\"><pic:nvPicPr><pic:cNvPr id=\"{n}\" name=\"{name}\"/><pic:cNvPicPr/></pic:nvPicPr>"
                    f"<pic:blipFill><a:blip r:embed=\"{rid}\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>"
                    f"<pic:spPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"{cx}\" cy=\"{cy}\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>"
                    f"</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>")
            paras.append(_para(draw, center=True))
    doc = (f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><w:document xmlns:w=\"{W}\" xmlns:m=\"{M}\" "
           f"xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><w:body>{''.join(paras)}"
           f"<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/><w:pgMar w:top=\"1134\" w:right=\"1134\" w:bottom=\"1134\" w:left=\"1134\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/></w:sectPr></w:body></w:document>")
    return doc, rels, media


def build_docx_bytes(items) -> bytes:
    doc, rels, media = _build_parts(items)
    rel_xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
               + "".join(f"<Relationship Id=\"{rid}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image\" Target=\"{t}\"/>" for rid, t in rels) + "</Relationships>")
    ct = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
          "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/>"
          "<Default Extension=\"png\" ContentType=\"image/png\"/><Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/></Types>")
    root_rels = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                 "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/></Relationships>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", rel_xml)
        for name, data in media.items():
            z.writestr("word/media/" + name, data)
    return buf.getvalue()


def build_flat_opc(items) -> str:
    """Flat OPC (một file XML) - dùng cho Range.InsertXML của Word."""
    doc, rels, media = _build_parts(items)
    body = re.sub(r"^<\?xml[^>]*\?>", "", doc)
    rel_xml = "".join(f"<Relationship Id=\"{rid}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image\" Target=\"{t}\"/>" for rid, t in rels)
    pkg = ("<?xml version=\"1.0\" standalone=\"yes\"?><?mso-application progid=\"Word.Document\"?>"
           "<pkg:package xmlns:pkg=\"http://schemas.microsoft.com/office/2006/xmlPackage\">"
           "<pkg:part pkg:name=\"/_rels/.rels\" pkg:contentType=\"application/vnd.openxmlformats-package.relationships+xml\"><pkg:xmlData>"
           "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" "
           "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/></Relationships></pkg:xmlData></pkg:part>"
           "<pkg:part pkg:name=\"/word/_rels/document.xml.rels\" pkg:contentType=\"application/vnd.openxmlformats-package.relationships+xml\"><pkg:xmlData>"
           f"<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">{rel_xml}</Relationships></pkg:xmlData></pkg:part>"
           f"<pkg:part pkg:name=\"/word/document.xml\" pkg:contentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"><pkg:xmlData>{body}</pkg:xmlData></pkg:part>")
    for name, data in media.items():
        pkg += (f"<pkg:part pkg:name=\"/word/media/{name}\" pkg:contentType=\"image/png\" pkg:compression=\"store\"><pkg:binaryData>"
                f"{base64.b64encode(data).decode('ascii')}</pkg:binaryData></pkg:part>")
    return pkg + "</pkg:package>"


# ==============================================================================
# 4. CHÈN THẲNG VÀO WORD ĐANG MỞ (Windows)
# ==============================================================================
def insert_into_word(items):
    """Trả về (ok, thông_báo). Cần: Windows + Microsoft Word + `pip install pywin32`."""
    if not items:
        return False, "Chưa có nội dung để chèn."
    try:
        import win32com.client as wc  # type: ignore
    except Exception:
        return False, ("Chưa cài pywin32 (hoặc không phải Windows). Chạy:  python -m pip install pywin32   rồi thử lại.\n"
                       "Hoặc dùng «Xuất file .docx» và copy từ file đó sang tài liệu của bạn.")
    try:
        try:
            app = wc.GetActiveObject("Word.Application")
        except Exception:
            app = wc.Dispatch("Word.Application")
            app.Visible = True
        if app.Documents.Count == 0:
            app.Documents.Add()
        app.Selection.Range.InsertXML(build_flat_opc(items))
        return True, f"Đã chèn {len(items)} mục vào Word tại vị trí con trỏ."
    except Exception as exc:
        return False, f"Word không nhận được dữ liệu ({exc}). Hãy thử «Xuất file .docx»."
