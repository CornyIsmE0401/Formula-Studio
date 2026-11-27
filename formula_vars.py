# -*- coding: utf-8 -*-
"""formula_vars.py - Tìm biến trong mã LaTeX và thay giá trị vào (không cần sửa mã công thức)."""
import re

_SKIP_ARG = {"mathrm", "text", "textbf", "mathbf", "operatorname", "begin", "end", "mathbb", "mathcal", "ce", "pu", "color", "tag"}
_NUM = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _read_group(s, i):
    """s[i] == '{' -> (nội dung, chỉ số sau '}')"""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def _tokens(s):
    """Sinh (loại, văn bản, tên_biến). loại: 'var' hoặc 'raw'."""
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            j = i + 1
            if j < n and s[j].isalpha():
                while j < n and s[j].isalpha():
                    j += 1
                cmd = s[i + 1:j]
                if cmd in _SKIP_ARG:
                    k = j
                    while k < n and s[k] == " ":
                        k += 1
                    if k < n and s[k] == "{":
                        _, e = _read_group(s, k)
                        yield "raw", s[i:e], None
                        i = e
                        continue
                yield "raw", s[i:j], None
                i = j
            else:
                yield "raw", s[i:i + 2], None
                i += 2
            continue
        if c.isalpha() and c.isascii():
            j = i + 1
            name = c
            if j < n and s[j] == "_":
                if j + 1 < n and s[j + 1] == "{":
                    sub, e = _read_group(s, j + 1)
                    name, j = f"{c}_{sub}", e
                elif j + 1 < n:
                    name, j = f"{c}_{s[j + 1]}", j + 2
            yield "var", s[i:j], name
            i = j
            continue
        yield "raw", c, None
        i += 1


def detect_vars(latex, limit=12):
    seen = []
    for kind, _, name in _tokens(latex):
        if kind == "var" and name not in seen:
            seen.append(name)
    return seen[:limit]


def _fmt_value(v):
    v = v.strip()
    if _NUM.match(v):
        v = v.replace(",", "{,}")
        return f"({v})" if v.startswith("-") else v
    if re.search(r"[+\-*/]", v) and not v.startswith("\\"):
        return f"({v})"
    return v


def substitute(latex, values):
    """values: {tên_biến: chuỗi}. Biến không có giá trị giữ nguyên."""
    vals = {k: v for k, v in values.items() if v and v.strip()}
    if not vals:
        return latex
    out = []
    for kind, text, name in _tokens(latex):
        if kind == "var" and name in vals:
            rep = _fmt_value(vals[name])
            prev = "".join(out)[-1:] if out else ""
            if prev.isdigit() and rep[:1].isdigit():
                out.append("\\cdot ")
            out.append(rep)
        else:
            out.append(text)
    return "".join(out)
