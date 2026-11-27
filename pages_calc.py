# -*- coding: utf-8 -*-
"""pages_calc.py - Máy tính khoa học kiểu Casio fx-580VN X: bàn phím + lịch sử + ~40 công cụ giải toán có lời giải từng bước."""
import math
import re
from fractions import Fraction

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QStackedWidget, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QScrollArea, QSizePolicy, QSplitter, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

import calc_engine as ce
import i18n
import natural_display as nd
from ui_common import copy_text, esc, fix_combo, mk_btn, mk_card, mk_label, shrink_x

# ------------------------------------------------------------------------------
# Hiển thị kết quả dạng HTML đẹp
# ------------------------------------------------------------------------------


def html_result(title, steps=(), results=(), notes=(), mono=None, dark=False):
    en = i18n.is_en()
    acc = "#818CF8" if dark else "#4F46E5"
    soft = "#1E293B" if dark else "#EEF2FF"
    muted = "#94A3B8" if dark else "#64748B"
    h = [f"<div style='font-family:\"Segoe UI\",sans-serif; font-size:13.5px; line-height:1.55;'>"
         f"<div style='font-size:15.5px; font-weight:700; margin-bottom:6px'>{i18n.tr_calc_text(title)}</div>"]
    if steps:
        h.append(f"<div style='color:{muted}; font-weight:600'>{'Steps' if en else 'Các bước'}</div><table cellspacing='0' cellpadding='3'>")
        for i, s in enumerate(steps, 1):
            h.append(f"<tr><td valign='top' style='color:{acc}'><b>{i}.</b></td><td>{i18n.tr_calc_text(s)}</td></tr>")
        h.append("</table>")
    if mono:
        h.append(f"<pre style='font-family:\"Cascadia Code\",Consolas,monospace; font-size:13px; background:{soft}; padding:9px; border-radius:8px'>{i18n.tr_calc_text(mono)}</pre>")
    if results:
        h.append(f"<br><table width='100%' cellpadding='10' cellspacing='0'><tr><td bgcolor='{soft}'>"
                 f"<span style='color:{acc}; font-weight:700; font-size:11.5px'>{'RESULT' if en else 'KẾT QUẢ'}</span><br>")
        for r in results:
            h.append(f"<span style='font-size:15.5px; font-weight:600'>{i18n.tr_calc_text(r)}</span><br>")
        h.append("</td></tr></table>")
    for n in notes:
        h.append(f"<div style='color:#D97706; margin-top:6px'>{i18n.tr_calc_text(n)}</div>")
    h.append("</div>")
    return "".join(h)


def err_html(msg):
    return f"<div style='color:#E5484D; font-size:14px'>{msg}</div>"


def num(c, text):
    v = c.evaluate(text)
    if isinstance(v, complex):
        raise ce.CalcError("Giá trị phải là số thực.")
    return v


# ------------------------------------------------------------------------------
# Khai báo các công cụ: (nhóm, tên, [(nhãn, mặc định, gợi ý)], hàm)
# hàm nhận (calc, [chuỗi nhập]) -> dict(title, steps, results, notes, mono)
# ------------------------------------------------------------------------------


def t_linear(c, v):
    a, b = num(c, v[0]), num(c, v[1])
    st, rs = ce.solve_linear(a, b)
    return dict(title="Phương trình bậc nhất ax + b = 0", steps=st, results=rs)


def t_quad(c, v):
    a, b, cc = (num(c, x) for x in v[:3])
    st, rs = ce.solve_quadratic(a, b, cc)
    return dict(title="Phương trình bậc hai ax² + bx + c = 0", steps=st, results=rs)


def t_poly(c, v):
    co = ce.parse_numbers(v[0])
    if len(co) < 2 or len(co) > 11:
        raise ce.CalcError("Nhập 2–11 hệ số từ bậc cao xuống thấp (VD: 1 -6 11 -6 cho x³ − 6x² + 11x − 6).")
    st, rs = ce.solve_poly(co)
    return dict(title=f"Phương trình bậc {len(co) - 1}", steps=st, results=rs, notes=["Nghiệm tính số (độ chính xác ~10⁻¹⁰); nghiệm phức hiển thị dạng a + bi."])


def _sys(c, v, n):
    nums = [num(c, x) for x in re.split(r"[\s,;]+", v[0].strip()) if x]
    if len(nums) != n * (n + 1):
        raise ce.CalcError(f"Cần {n * (n + 1)} số: mỗi hàng gồm {n} hệ số rồi vế phải. VD hệ 2 ẩn: 2 1 5; 1 -1 1")
    A = [nums[i * (n + 1):i * (n + 1) + n] for i in range(n)]
    b = [nums[i * (n + 1) + n] for i in range(n)]
    sol, msg = ce.solve_system(A, b)
    names = "xyzt"[:n]
    eqs = [" + ".join(f"{ce.fmt_num(A[i][j])}{names[j]}" for j in range(n)).replace("+ -", "− ") + f" = {ce.fmt_num(b[i])}" for i in range(n)]
    det = ce.mat_det([[Fraction(x).limit_denominator(10 ** 6) for x in r] for r in A])
    if sol is None:
        return dict(title=f"Hệ {n} phương trình {n} ẩn", steps=["Hệ: " + " ; ".join(eqs), f"Định thức D = {ce.fmt_num(float(det))}"], results=[msg])
    return dict(title=f"Hệ {n} phương trình {n} ẩn", steps=["Hệ: " + " ; ".join(eqs), f"Định thức D = {ce.fmt_num(float(det))} ≠ 0 ⇒ hệ có nghiệm duy nhất", "Khử Gauss–Jordan trên phân số"],
                results=[f"{names[i]} = {ce.frac_str(sol[i])}" + (f" ≈ {ce.fmt_num(float(sol[i]))}" if sol[i].denominator != 1 else "") for i in range(n)])


def t_ineq(c, v):
    co = ce.parse_numbers(v[0])
    op = v[1].strip() or ">"
    op = {"≥": ">=", "≤": "<=", "=>": ">=", "=<": "<="}.get(op, op)
    if op not in (">", "<", ">=", "<="):
        raise ce.CalcError("Dấu so sánh: >  <  >=  <=")
    S, roots = ce.solve_ineq_poly(co, op)
    return dict(title=f"Bất phương trình bậc {len(co) - 1}: {ce.poly_str(co)} {op.replace('>=', '≥').replace('<=', '≤')} 0",
                steps=["Tìm nghiệm thực của đa thức: " + (", ".join(ce.fmt_num(r) for r in roots) or "không có"), "Xét dấu đa thức trên từng khoảng"], results=[S])


def t_stat1(c, v):
    xs = ce.parse_numbers(v[0])
    fr = ce.parse_numbers(v[1]) if v[1].strip() else None
    st = ce.stats_1var(xs, fr)
    rows = "".join(f"{k:<34s} {ce.fmt_num(x) if not isinstance(x, str) else x}\n" for k, x in st.items())
    return dict(title="Thống kê 1 biến", mono=rows.rstrip(), results=[f"x̄ = {ce.fmt_num(st['x̄ (trung bình)'])}", f"σx = {ce.fmt_num(st['σx (độ lệch chuẩn tổng thể)'])}   ·   sx = {ce.fmt_num(st['sx (độ lệch chuẩn mẫu)'])}"])


KINDS = {"Tuyến tính (y = a + bx)": "lin", "Bậc 2 (y = ax² + bx + c)": "quad", "Mũ (y = a·bˣ)": "exp", "Lôgarit (y = a + b·ln x)": "log", "Lũy thừa (y = a·xᵇ)": "pow", "Nghịch đảo (y = a + b/x)": "inv"}


def t_reg(c, v):
    xs, ys = ce.parse_numbers(v[0]), ce.parse_numbers(v[1])
    kind = KINDS.get(v[2], "lin")
    r = ce.regression(xs, ys, kind)
    res = [r["eq"]]
    if "r" in r:
        res.append(f"Hệ số tương quan r = {ce.fmt_num(r['r'])}")
    if "R²" in r:
        res.append(f"R² = {ce.fmt_num(r['R²'])}")
    steps = [f"Dữ liệu: n = {len(xs)} cặp (x; y)", "Phương pháp bình phương tối thiểu"]
    if v[3].strip():
        x0 = num(c, v[3])
        res.append(f"Dự đoán ŷ({ce.fmt_num(x0)}) = {ce.fmt_num(r['pred'](x0))}")
    return dict(title="Hồi quy", steps=steps, results=res)


def t_norm(c, v):
    mu, sg = num(c, v[0]), num(c, v[1])
    a, b = num(c, v[2]), num(c, v[3])
    if sg <= 0:
        raise ce.CalcError("σ phải dương.")
    p = ce.norm_cdf(b, mu, sg) - ce.norm_cdf(a, mu, sg)
    za, zb = (a - mu) / sg, (b - mu) / sg
    return dict(title="Phân phối chuẩn N(μ, σ²)", steps=[f"z₁ = (a − μ)/σ = {ce.fmt_num(za)};  z₂ = (b − μ)/σ = {ce.fmt_num(zb)}", "P(a < X < b) = Φ(z₂) − Φ(z₁)"],
                results=[f"P({ce.fmt_num(a)} < X < {ce.fmt_num(b)}) = {ce.fmt_num(p, 8)}", f"P(X < {ce.fmt_num(b)}) = {ce.fmt_num(ce.norm_cdf(b, mu, sg), 8)}"],
                notes=["Nhập a = -1e9 để tính P(X < b); b = 1e9 để tính P(X > a)."])


def t_norminv(c, v):
    mu, sg, p = num(c, v[0]), num(c, v[1]), num(c, v[2])
    x = ce.norm_inv(p, mu, sg)
    return dict(title="Giá trị tới hạn (InvN)", steps=[f"Tìm x sao cho P(X < x) = {ce.fmt_num(p)}"], results=[f"x = {ce.fmt_num(x, 9)}"])


def t_binom(c, v):
    n, p, k = int(num(c, v[0])), num(c, v[1]), int(num(c, v[2]))
    if not (0 <= p <= 1 and 0 <= k <= n):
        raise ce.CalcError("Cần 0 ≤ p ≤ 1 và 0 ≤ k ≤ n.")
    pm = math.comb(n, k) * p ** k * (1 - p) ** (n - k)
    cdf = sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    return dict(title="Phân phối nhị thức B(n, p)", steps=[f"P(X = k) = C({n},{k})·{ce.fmt_num(p)}^{k}·(1 − {ce.fmt_num(p)})^{n - k}"],
                results=[f"P(X = {k}) = {ce.fmt_num(pm, 8)}", f"P(X ≤ {k}) = {ce.fmt_num(cdf, 8)}", f"E(X) = np = {ce.fmt_num(n * p)};  V(X) = np(1 − p) = {ce.fmt_num(n * p * (1 - p))}"])


def t_poisson(c, v):
    lam, k = num(c, v[0]), int(num(c, v[1]))
    pm = math.exp(-lam) * lam ** k / math.factorial(k)
    cdf = sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k + 1))
    return dict(title="Phân phối Poisson", steps=[f"P(X = k) = e^(−λ)·λᵏ / k!"], results=[f"P(X = {k}) = {ce.fmt_num(pm, 8)}", f"P(X ≤ {k}) = {ce.fmt_num(cdf, 8)}"])


def t_matop(c, v):
    A = ce.parse_matrix(v[0])
    op = v[2]
    B = ce.parse_matrix(v[1]) if v[1].strip() else None
    res, notes, mono = [], [], ""
    if op == "Định thức det(A)":
        res = [f"det(A) = {ce.frac_str(ce.mat_det(A))}"]
    elif op == "Nghịch đảo A⁻¹":
        mono = ce.mat_str(ce.mat_inv(A))
        res = ["A⁻¹ ="]
    elif op == "Chuyển vị Aᵀ":
        mono = ce.mat_str(ce.mat_T(A))
        res = ["Aᵀ ="]
    elif op == "Hạng rank(A)":
        res = [f"rank(A) = {ce.mat_rank(A)}"]
    elif op == "Vết tr(A)":
        res = [f"tr(A) = {ce.frac_str(sum(A[i][i] for i in range(min(len(A), len(A[0])))))}"]
    elif op == "A + B":
        if not B:
            raise ce.CalcError("Cần nhập ma trận B.")
        mono = ce.mat_str([[x + y for x, y in zip(r1, r2)] for r1, r2 in zip(A, B)])
        res = ["A + B ="]
    elif op == "A − B":
        if not B:
            raise ce.CalcError("Cần nhập ma trận B.")
        mono = ce.mat_str([[x - y for x, y in zip(r1, r2)] for r1, r2 in zip(A, B)])
        res = ["A − B ="]
    elif op == "A × B":
        if not B:
            raise ce.CalcError("Cần nhập ma trận B.")
        mono = ce.mat_str(ce.mat_mul(A, B))
        res = ["A × B ="]
    elif op == "Aⁿ (n nhập ở ô B)":
        n = int(ce.Calc().evaluate(v[1] or "2"))
        mono = ce.mat_str(ce.mat_pow(A, n))
        res = [f"A^{n} ="]
    elif op == "Trị riêng của A":
        co, roots = ce.mat_eigen(A)
        mono = "Đa thức đặc trưng: " + ce.poly_str(co) + " = 0"
        res = [f"λ{ce._sub(i + 1)} = {ce.fmt_complex(z)}" for i, z in enumerate(roots)]
    return dict(title=f"Ma trận — {op}", mono=mono or None, results=res, notes=notes)


def t_vec(c, v):
    a, b = ce.parse_vec(v[0]), ce.parse_vec(v[1])
    if len(a) != len(b):
        raise ce.CalcError("Hai vectơ phải cùng số chiều (2 hoặc 3).")
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    res = [f"a·b = {ce.fmt_num(dot)}", f"|a| = {ce.fmt_num(na)};  |b| = {ce.fmt_num(nb)}"]
    if na * nb:
        res.append(f"Góc (a, b) = {ce.fmt_num(math.degrees(math.acos(max(-1, min(1, dot / (na * nb))))))}°")
    res.append("a + b = (" + "; ".join(ce.fmt_num(x + y) for x, y in zip(a, b)) + ")")
    res.append("a − b = (" + "; ".join(ce.fmt_num(x - y) for x, y in zip(a, b)) + ")")
    steps = []
    if len(a) == 3:
        cr = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        res.append("[a, b] = (" + "; ".join(ce.fmt_num(x) for x in cr) + ")")
        res.append(f"Diện tích hình bình hành = |[a, b]| = {ce.fmt_num(math.sqrt(sum(x * x for x in cr)))}")
        res.append(f"Diện tích tam giác = {ce.fmt_num(math.sqrt(sum(x * x for x in cr)) / 2)}")
        steps = ["Tích có hướng: [a,b] = (y₁z₂ − z₁y₂ ; z₁x₂ − x₁z₂ ; x₁y₂ − y₁x₂)"]
    else:
        res.append(f"Diện tích hình bình hành = |x₁y₂ − x₂y₁| = {ce.fmt_num(abs(a[0] * b[1] - a[1] * b[0]))}")
    if nb:
        k = dot / (nb * nb)
        res.append("Hình chiếu của a lên b = (" + "; ".join(ce.fmt_num(k * x) for x in b) + ")")
    return dict(title="Vectơ", steps=steps, results=res)


def t_complex(c, v):
    cc = ce.Calc()
    cc.complex_mode = True
    z = cc.evaluate(v[0])
    z = complex(z)
    r = abs(z)
    ph = math.degrees(math.atan2(z.imag, z.real))
    res = [f"z = {ce.fmt_complex(z)}", f"|z| = {ce.fmt_num(r)}", f"arg(z) = {ce.fmt_num(ph)}° = {ce.fmt_num(math.radians(ph))} rad", f"z̄ = {ce.fmt_complex(z.conjugate())}",
           f"Dạng lượng giác: z = {ce.fmt_num(r)}(cos {ce.fmt_num(ph)}° + i·sin {ce.fmt_num(ph)}°)", f"Dạng mũ: z = {ce.fmt_num(r)}·e^(i·{ce.fmt_num(math.radians(ph))})"]
    if z != 0:
        res.append(f"1/z = {ce.fmt_complex(1 / z)}")
    n = int(num(ce.Calc(), v[1])) if v[1].strip() else 0
    if n > 1:
        rts = [complex(r ** (1 / n) * math.cos((math.radians(ph) + 2 * math.pi * k) / n), r ** (1 / n) * math.sin((math.radians(ph) + 2 * math.pi * k) / n)) for k in range(n)]
        res += [f"Căn bậc {n} thứ {k + 1}: {ce.fmt_complex(w)}" for k, w in enumerate(rts)]
    return dict(title="Số phức", steps=["Có thể nhập biểu thức: (3+4i)*(1-2i), (1+i)^8, sqrt(-4)…"], results=res)


def t_base(c, v):
    txt, base = v[0].strip().upper().replace(" ", ""), {"Thập phân (DEC)": 10, "Nhị phân (BIN)": 2, "Bát phân (OCT)": 8, "Thập lục phân (HEX)": 16}[v[1]]
    try:
        n = int(txt, base)
    except ValueError:
        raise ce.CalcError(f"'{v[0]}' không phải số hợp lệ trong hệ cơ số {base}.")
    return dict(title="Đổi hệ cơ số", results=[f"DEC: {n}", f"BIN: {ce.to_base(n, 2)}", f"OCT: {ce.to_base(n, 8)}", f"HEX: {ce.to_base(n, 16)}"],
                steps=[f"Chuyển {txt} (cơ số {base}) sang thập phân: {n}"], notes=[])


def t_logic(c, v):
    a, b = int(v[0], 0), int(v[1], 0)
    return dict(title="Phép toán logic bit", results=[f"{a} AND {b} = {a & b} (BIN {ce.to_base(a & b, 2)})", f"{a} OR {b} = {a | b} (BIN {ce.to_base(a | b, 2)})",
                                                      f"{a} XOR {b} = {a ^ b} (BIN {ce.to_base(a ^ b, 2)})", f"NOT {a} = {~a}", f"{a} << 1 = {a << 1};  {a} >> 1 = {a >> 1}"],
                steps=["Nhập số thập phân hoặc tiền tố 0b (nhị phân), 0x (hex), 0o (bát phân)"])


def t_table(c, v):
    f, a, b, st = v[0], num(c, v[1]), num(c, v[2]), num(c, v[3])
    if st <= 0 or (b - a) / st > 400:
        raise ce.CalcError("Bước phải dương và tối đa 400 dòng.")
    rows, x = [], a
    while x <= b + 1e-12:
        try:
            y = ce.fmt_num(c.evaluate(f, {"x": x}))
        except ce.CalcError:
            y = "—"
        rows.append(f"{ce.fmt_num(x):>12s}   │ {y}")
        x += st
    return dict(title=f"Bảng giá trị f(x) = {f}", mono="         x     │ f(x)\n" + "─" * 14 + "┼" + "─" * 20 + "\n" + "\n".join(rows))


def t_deriv(c, v):
    x0 = num(c, v[1])
    f = lambda x: c.evaluate(v[0], {"x": x})  # noqa: E731
    d1 = ce.numeric_derivative(f, x0)
    h = 1e-3
    d2 = (f(x0 + h) - 2 * f(x0) + f(x0 - h)) / (h * h)
    ex = ce.exact_form(d1)
    return dict(title=f"Đạo hàm của f(x) = {v[0]} tại x = {v[1]}", steps=["Đạo hàm số (sai phân trung tâm, ngoại suy Richardson)"],
                results=[f"f(x₀) = {ce.fmt_num(f(x0))}", f"f ′(x₀) ≈ {ce.fmt_num(d1, 9)}" + (f" = {ex}" if ex else ""), f"f ″(x₀) ≈ {ce.fmt_num(d2, 6)}",
                         f"Tiếp tuyến: y = {ce.fmt_num(d1)}(x − {ce.fmt_num(x0)}) + {ce.fmt_num(f(x0))}"])


def t_integral(c, v):
    a, b = num(c, v[1]), num(c, v[2])
    f = lambda x: c.evaluate(v[0], {"x": x})  # noqa: E731
    val = ce.numeric_integral(f, a, b, 4000)
    ex = ce.exact_form(val)
    return dict(title=f"Tích phân xác định ∫ {v[0]} dx từ {v[1]} đến {v[2]}", steps=["Quy tắc Simpson với 4000 khoảng chia"], results=[f"I ≈ {ce.fmt_num(val, 10)}" + (f" = {ex}" if ex else "")])


def t_limit(c, v):
    x0 = v[1].strip()
    f = lambda x: c.evaluate(v[0], {"x": x})  # noqa: E731
    res = []
    if x0.lower() in ("inf", "+inf", "∞", "+∞"):
        res = [f"x → +∞: f(10⁶) = {ce.fmt_num(f(1e6))}, f(10⁹) = {ce.fmt_num(f(1e9))}"]
    elif x0.lower() in ("-inf", "-∞"):
        res = [f"x → −∞: f(−10⁶) = {ce.fmt_num(f(-1e6))}"]
    else:
        a = num(c, x0)
        for h in (1e-3, 1e-6, 1e-9):
            try:
                res.append(f"h = {h:g}:  f(x₀ − h) = {ce.fmt_num(f(a - h))},  f(x₀ + h) = {ce.fmt_num(f(a + h))}")
            except ce.CalcError:
                res.append(f"h = {h:g}: không xác định")
    return dict(title=f"Giới hạn của f(x) = {v[0]}", steps=["Tính giá trị tiến gần về điểm cần tìm giới hạn từ hai phía"], results=res)


def t_sigma(c, v):
    a, b = int(num(c, v[1])), int(num(c, v[2]))
    s = c.evaluate(f"sigma({v[0]}, {a}, {b})")
    p = c.evaluate(f"prod({v[0]}, {a}, {b})") if b - a < 60 else "(quá lớn)"
    return dict(title=f"Tổng Σ và tích Π của {v[0]} với x từ {a} đến {b}", results=[f"Σ = {ce.fmt_num(s)}", f"Π = {ce.fmt_num(p) if not isinstance(p, str) else p}"])


def t_solve(c, v):
    f = lambda x: c.evaluate(v[0], {"x": x})  # noqa: E731
    sols = []
    for x0 in [num(c, v[1])] + [-10, -3, -1, 0.5, 2, 5, 10]:
        try:
            r = ce.solve_newton(f, x0)
            if abs(f(r)) < 1e-7 and not any(abs(r - s) < 1e-6 for s in sols):
                sols.append(r)
        except (ce.CalcError, ZeroDivisionError, OverflowError, ValueError):
            pass
    if not sols:
        raise ce.CalcError("Không tìm được nghiệm. Hãy thử giá trị khởi đầu khác.")
    return dict(title=f"SOLVE: {v[0]} = 0", steps=["Phương pháp Newton–Raphson từ nhiều điểm xuất phát"], results=[f"x = {ce.fmt_num(s, 10)}" + (f" = {ce.exact_form(s)}" if ce.exact_form(s) else "") for s in sorted(sols)])


def t_calc(c, v):
    vals = {}
    for pair in re.split(r"[;,]", v[1]):
        if "=" in pair:
            k, e = pair.split("=", 1)
            vals[k.strip()] = c.evaluate(e)
    r = c.evaluate(v[0], vals)
    ex = ce.exact_form(r) if not isinstance(r, (int, complex)) else None
    return dict(title="CALC: thay giá trị biến", steps=[f"Thay {', '.join(f'{k} = {ce.fmt_num(x)}' for k, x in vals.items())}"], results=[f"{v[0]} = {ce.fmt_num(r, 10)}" + (f" = {ex}" if ex else "")])


def t_gcd(c, v):
    ns = [int(num(c, x)) for x in re.split(r"[\s,;]+", v[0].strip()) if x]
    g = ns[0]
    l = ns[0]
    for x in ns[1:]:
        g = math.gcd(g, x)
        l = l * x // math.gcd(l, x)
    return dict(title="ƯCLN và BCNN", results=[f"ƯCLN = {g}", f"BCNN = {l}"], steps=["Thuật toán Euclid"])


def t_factor(c, v):
    n = int(num(c, v[0]))
    f = ce.prime_factors(n)
    s = " × ".join(f"{p}{str(e).translate(ce.SUP)}" if e > 1 else str(p) for p, e in f.items())
    ds = ce.divisors(n)
    res = [f"{n} = {s}", "Số nguyên tố" if (len(f) == 1 and list(f.values())[0] == 1) else f"Có {len(ds)} ước"]
    if len(ds) <= 80:
        res.append("Các ước: " + ", ".join(map(str, ds)))
    return dict(title="Phân tích ra thừa số nguyên tố", results=res, steps=["Chia thử cho các số nguyên tố"])


def t_divide(c, v):
    a, b = int(num(c, v[0])), int(num(c, v[1]))
    if b == 0:
        raise ce.CalcError("Số chia phải khác 0.")
    q, r = divmod(a, b)
    return dict(title="Phép chia có dư", results=[f"{a} = {b} × {q} + {r}", f"Thương = {q}; Dư = {r}"])


def t_frac(c, v):
    x = Fraction(v[0].strip()) if re.match(r"^-?\d+/\d+$|^-?\d+$", v[0].strip()) else Fraction(c.evaluate(v[0])).limit_denominator(10 ** 6)
    return dict(title="Phân số ⇄ số thập phân", results=[f"Phân số tối giản: {ce.frac_str(x)}", f"Hỗn số: {ce.mixed_str(x)}", f"Thập phân: {ce.fmt_num(float(x), 12)}", f"Phần trăm: {ce.fmt_num(float(x) * 100)}%"])


def t_modpow(c, v):
    a, b, m = (int(num(c, x)) for x in v[:3])
    return dict(title="Lũy thừa modulo", results=[f"{a}^{b} mod {m} = {pow(a, b, m)}"], steps=["Bình phương liên tiếp (square-and-multiply)"])


def t_comb(c, v):
    n, k = int(num(c, v[0])), int(num(c, v[1]))
    return dict(title="Tổ hợp – Chỉnh hợp – Hoán vị", results=[f"n! = {math.factorial(n) if n < 200 else '(quá lớn)'}", f"C({n},{k}) = {math.comb(n, k)}", f"A({n},{k}) = {math.perm(n, k)}", f"Hoán vị lặp: {n}!/{k}! = {math.factorial(n) // math.factorial(k)}"])


def t_unit(c, v):
    cat, val, u1, u2 = v[0], num(c, v[1]), v[2].strip(), v[3].strip()
    if cat == "Nhiệt độ":
        r = ce.convert_unit(cat, val, u1 or "°C", u2 or "°F")
    else:
        if u1 not in ce.UNITS[cat] or u2 not in ce.UNITS[cat]:
            raise ce.CalcError("Đơn vị chưa có. Đơn vị hợp lệ: " + ", ".join(ce.UNITS[cat]))
        r = ce.convert_unit(cat, val, u1, u2)
    return dict(title=f"Đổi đơn vị — {cat}", results=[f"{ce.fmt_num(val)} {u1} = {ce.fmt_num(r, 10)} {u2}"], notes=[] if cat == "Nhiệt độ" else [f"Đơn vị có sẵn: {', '.join(ce.UNITS[cat])}"] if True else [])


def t_ratio(c, v):
    a, b, cc = num(c, v[0]), num(c, v[1]), num(c, v[2])
    if cc == 0:
        raise ce.CalcError("Giá trị c phải khác 0.")
    return dict(title="Tỉ lệ a : b = c : x", steps=["x = b·c / a"], results=[f"x = {ce.fmt_num(b * cc / a)}"]) if a != 0 else dict(title="Tỉ lệ", results=["a phải khác 0"])


def t_percent(c, v):
    a, b = num(c, v[0]), num(c, v[1])
    res = [f"{ce.fmt_num(b)}% của {ce.fmt_num(a)} = {ce.fmt_num(a * b / 100)}", f"{ce.fmt_num(a)} tăng {ce.fmt_num(b)}% = {ce.fmt_num(a * (1 + b / 100))}", f"{ce.fmt_num(a)} giảm {ce.fmt_num(b)}% = {ce.fmt_num(a * (1 - b / 100))}"]
    if b:
        res.append(f"{ce.fmt_num(a)} là bao nhiêu % của {ce.fmt_num(b)}: {ce.fmt_num(a / b * 100)}%")
    return dict(title="Phần trăm", results=res)


def t_interest(c, v):
    P, r, n = num(c, v[0]), num(c, v[1]) / 100, num(c, v[2])
    simple = P * (1 + r * n)
    comp = P * (1 + r) ** n
    pay = P * r / (1 - (1 + r) ** -n) if r else P / n
    return dict(title="Tài chính cơ bản", steps=["Lãi đơn: A = P(1 + rn)", "Lãi kép: A = P(1 + r)ⁿ", "Trả góp đều: M = P·r / (1 − (1 + r)⁻ⁿ)"],
                results=[f"Lãi đơn: {ce.fmt_num(simple, 12)}", f"Lãi kép: {ce.fmt_num(comp, 12)}", f"Số tiền trả đều mỗi kỳ: {ce.fmt_num(pay, 12)}"])


def t_triangle(c, v):
    vals = {k: (num(c, x) if x.strip() else None) for k, x in zip("abcABC", v[:6])}
    a, b, cc, A, B, C = (vals[k] for k in "abcABC")
    rad = math.radians
    steps = []
    try:
        sides = [x for x in (a, b, cc) if x is not None]
        angs = [x for x in (A, B, C) if x is not None]
        if len(sides) == 3:
            A = math.degrees(math.acos((b * b + cc * cc - a * a) / (2 * b * cc)))
            B = math.degrees(math.acos((a * a + cc * cc - b * b) / (2 * a * cc)))
            C = 180 - A - B
            steps.append("Định lí hàm số cos: cos A = (b² + c² − a²)/(2bc), …")
        elif len(sides) == 2 and len(angs) == 1:
            if a is not None and b is not None and C is not None:
                cc = math.sqrt(a * a + b * b - 2 * a * b * math.cos(rad(C)))
                A = math.degrees(math.acos((b * b + cc * cc - a * a) / (2 * b * cc)))
                B = 180 - A - C
                steps.append("Hai cạnh và góc xen giữa: c² = a² + b² − 2ab·cos C")
            elif a is not None and cc is not None and B is not None:
                b = math.sqrt(a * a + cc * cc - 2 * a * cc * math.cos(rad(B)))
                A = math.degrees(math.acos((b * b + cc * cc - a * a) / (2 * b * cc)))
                C = 180 - A - B
                steps.append("b² = a² + c² − 2ac·cos B")
            elif b is not None and cc is not None and A is not None:
                a = math.sqrt(b * b + cc * cc - 2 * b * cc * math.cos(rad(A)))
                B = math.degrees(math.acos((a * a + cc * cc - b * b) / (2 * a * cc)))
                C = 180 - A - B
                steps.append("a² = b² + c² − 2bc·cos A")
            else:
                raise ce.CalcError("Trường hợp cạnh–cạnh–góc đối: hãy nhập thêm dữ kiện (có thể có 2 nghiệm).")
        elif len(angs) >= 2 and len(sides) >= 1:
            if A is None:
                A = 180 - B - C
            elif B is None:
                B = 180 - A - C
            elif C is None:
                C = 180 - A - B
            k = (a / math.sin(rad(A))) if a is not None else (b / math.sin(rad(B)) if b is not None else cc / math.sin(rad(C)))
            a, b, cc = k * math.sin(rad(A)), k * math.sin(rad(B)), k * math.sin(rad(C))
            steps.append("Định lí hàm số sin: a/sin A = b/sin B = c/sin C = 2R")
        else:
            raise ce.CalcError("Cần ít nhất 3 dữ kiện (3 cạnh; 2 cạnh + 1 góc; hoặc 1 cạnh + 2 góc).")
        if min(a, b, cc, A, B, C) <= 0 or abs(A + B + C - 180) > 1e-6:
            raise ce.CalcError("Dữ kiện không tạo thành tam giác.")
    except (ValueError, ZeroDivisionError):
        raise ce.CalcError("Dữ kiện không tạo thành tam giác hợp lệ.")
    p = (a + b + cc) / 2
    S = math.sqrt(max(p * (p - a) * (p - b) * (p - cc), 0))
    R = a * b * cc / (4 * S) if S else float("inf")
    return dict(title="Giải tam giác ABC", steps=steps, results=[f"a = {ce.fmt_num(a)};  b = {ce.fmt_num(b)};  c = {ce.fmt_num(cc)}", f"A = {ce.fmt_num(A)}°;  B = {ce.fmt_num(B)}°;  C = {ce.fmt_num(C)}°",
                                                                f"Chu vi = {ce.fmt_num(2 * p)};  Diện tích S = {ce.fmt_num(S)}", f"R (ngoại tiếp) = {ce.fmt_num(R)};  r (nội tiếp) = {ce.fmt_num(S / p)}",
                                                                f"Đường cao: hₐ = {ce.fmt_num(2 * S / a)}, h_b = {ce.fmt_num(2 * S / b)}, h_c = {ce.fmt_num(2 * S / cc)}"])


def t_line(c, v):
    x1, y1, x2, y2 = (num(c, x) for x in v[:4])
    if (x1, y1) == (x2, y2):
        raise ce.CalcError("Hai điểm phải khác nhau.")
    a, b = y2 - y1, x1 - x2
    cc = -(a * x1 + b * y1)
    d = math.hypot(x2 - x1, y2 - y1)
    res = [f"Đường thẳng AB: {ce.fmt_num(a)}x + {ce.fmt_num(b)}y + {ce.fmt_num(cc)} = 0", f"AB = {ce.fmt_num(d)}", f"Trung điểm M({ce.fmt_num((x1 + x2) / 2)}; {ce.fmt_num((y1 + y2) / 2)})"]
    if x1 != x2:
        res.append(f"Hệ số góc k = {ce.fmt_num((y2 - y1) / (x2 - x1))}")
    res.append(f"Đường trung trực: {ce.fmt_num(x2 - x1)}x + {ce.fmt_num(y2 - y1)}y + {ce.fmt_num(-((x2 ** 2 - x1 ** 2) + (y2 ** 2 - y1 ** 2)) / 2)} = 0")
    if v[4].strip():
        px, py = (num(c, x) for x in v[4].replace(";", " ").replace(",", " ").split()[:2])
        res.append(f"Khoảng cách từ P({ce.fmt_num(px)}; {ce.fmt_num(py)}) đến AB = {ce.fmt_num(abs(a * px + b * py + cc) / math.hypot(a, b))}")
    return dict(title="Đường thẳng qua 2 điểm", steps=["VTCP u = (x₂ − x₁; y₂ − y₁), VTPT n = (y₂ − y₁; x₁ − x₂)"], results=res)


def t_circle3(c, v):
    pts = [num(c, x) for x in v[:6]]
    cc = ce.Calc()
    from geometry_canvas import GeometryCanvas
    r = GeometryCanvas._circumcircle((pts[0], pts[1]), (pts[2], pts[3]), (pts[4], pts[5]))
    if not r:
        raise ce.CalcError("Ba điểm thẳng hàng — không có đường tròn qua cả ba.")
    (ox, oy), R = r
    return dict(title="Đường tròn qua 3 điểm", results=[f"Tâm I({ce.fmt_num(ox)}; {ce.fmt_num(oy)}),  R = {ce.fmt_num(R)}", f"(x − {ce.fmt_num(ox)})² + (y − {ce.fmt_num(oy)})² = {ce.fmt_num(R * R)}"])


def t_area3d(c, v):
    kind = v[0]
    a, b, h = num(c, v[1]), num(c, v[2]), num(c, v[3])
    pi = math.pi
    if kind == "Hình cầu (R)":
        res = [f"S = 4πR² = {ce.fmt_num(4 * pi * a * a)}", f"V = 4/3·πR³ = {ce.fmt_num(4 / 3 * pi * a ** 3)}"]
    elif kind == "Hình trụ (R, h)":
        res = [f"Sxq = 2πRh = {ce.fmt_num(2 * pi * a * b)}", f"Stp = 2πR(R + h) = {ce.fmt_num(2 * pi * a * (a + b))}", f"V = πR²h = {ce.fmt_num(pi * a * a * b)}"]
    elif kind == "Hình nón (R, h)":
        l = math.hypot(a, b)
        res = [f"l = √(R² + h²) = {ce.fmt_num(l)}", f"Sxq = πRl = {ce.fmt_num(pi * a * l)}", f"Stp = πR(R + l) = {ce.fmt_num(pi * a * (a + l))}", f"V = 1/3·πR²h = {ce.fmt_num(pi * a * a * b / 3)}"]
    elif kind == "Hình hộp chữ nhật (a, b, c)":
        res = [f"V = abc = {ce.fmt_num(a * b * h)}", f"Stp = 2(ab + bc + ca) = {ce.fmt_num(2 * (a * b + b * h + h * a))}", f"Đường chéo d = {ce.fmt_num(math.sqrt(a * a + b * b + h * h))}"]
    elif kind == "Hình lập phương (a)":
        res = [f"V = a³ = {ce.fmt_num(a ** 3)}", f"Stp = 6a² = {ce.fmt_num(6 * a * a)}", f"Đường chéo = a√3 = {ce.fmt_num(a * math.sqrt(3))}"]
    elif kind == "Hình chóp (S đáy, h)":
        res = [f"V = 1/3·S·h = {ce.fmt_num(a * b / 3)}"]
    elif kind == "Hình nón cụt (R, r, h)":
        res = [f"V = π·h/3·(R² + Rr + r²) = {ce.fmt_num(pi * h / 3 * (a * a + a * b + b * b))}", f"l = {ce.fmt_num(math.sqrt((a - b) ** 2 + h * h))}"]
    else:
        res = [f"V = S·h = {ce.fmt_num(a * b)}"]
    return dict(title=kind, results=res, notes=["Ô 1, 2, 3 lần lượt là các đại lượng theo thứ tự trong ngoặc."])


def t_phys(c, v):
    return dict(title="Hằng số vật lí", results=[f"{n} = {ce.fmt_num(val, 10)} {u}" for n, val, u in ce.PHYS_CONSTS if not v[0].strip() or v[0].lower() in n.lower()], notes=[])


def t_rand(c, v):
    import random
    lo, hi, k = int(num(c, v[0])), int(num(c, v[1])), int(num(c, v[2]))
    return dict(title="Số ngẫu nhiên", results=[", ".join(str(random.randint(lo, hi)) for _ in range(min(k, 100)))])


def t_ph(c, v):
    kind = v[0]
    C = num(c, v[1])
    if C <= 0:
        raise ce.CalcError("Nồng độ C phải dương.")
    steps = []
    if kind == "Acid mạnh (H⁺)":
        h = C
        ph = -math.log10(h)
        steps = [f"[H⁺] = C = {ce.fmt_num(h)} M", "pH = −lg[H⁺]"]
    elif kind == "Base mạnh (OH⁻)":
        oh = C
        poh = -math.log10(oh)
        ph = 14.0 - poh
        steps = [f"[OH⁻] = C = {ce.fmt_num(oh)} M", f"pOH = −lg[OH⁻] = {ce.fmt_num(poh)}", "pH = 14 − pOH"]
    elif kind == "Acid yếu (C, Ka)":
        ka = num(c, v[2])
        if ka <= 0:
            raise ce.CalcError("Hằng số Ka phải dương.")
        h = (-ka + math.sqrt(ka * ka + 4 * ka * C)) / 2.0
        ph = -math.log10(h)
        steps = ["Giải phương trình bậc 2: x² + Ka·x − Ka·C = 0", f"[H⁺] = {ce.fmt_num(h, 8)} M"]
    else:
        kb = num(c, v[2])
        if kb <= 0:
            raise ce.CalcError("Hằng số Kb phải dương.")
        oh = (-kb + math.sqrt(kb * kb + 4 * kb * C)) / 2.0
        poh = -math.log10(oh)
        ph = 14.0 - poh
        steps = ["Giải phương trình bậc 2: x² + Kb·x − Kb·C = 0", f"[OH⁻] = {ce.fmt_num(oh, 8)} M", f"pOH = {ce.fmt_num(poh)}"]
    env = "Acid (pH < 7)" if ph < 6.999 else ("Trung tính (pH ≈ 7)" if ph <= 7.001 else "Base (pH > 7)")
    return dict(title=f"Tính pH dung dịch — {kind}", steps=steps,
                results=[f"pH = {ce.fmt_num(ph, 6)}", f"pOH = {ce.fmt_num(14.0 - ph, 6)}", f"Môi trường: {env}"])


def t_dilution(c, v):
    c1, v1, c2 = num(c, v[0]), num(c, v[1]), num(c, v[2])
    if c2 <= 0 or c1 <= 0 or v1 <= 0:
        raise ce.CalcError("Các giá trị C₁, V₁, C₂ phải dương.")
    v2 = c1 * v1 / c2
    add_h2o = v2 - v1
    res = [f"Thể tích sau pha loãng: V₂ = {ce.fmt_num(v2, 8)} mL"]
    if add_h2o >= 0:
        res.append(f"Lượng nước cần thêm: ΔV = V₂ − V₁ = {ce.fmt_num(add_h2o, 8)} mL")
    else:
        res.append(f"Cần cô đặc bớt: {ce.fmt_num(-add_h2o, 8)} mL dung môi")
    return dict(title="Pha loãng dung dịch (C₁V₁ = C₂V₂)", steps=["Áp dụng định luật bảo toàn số mol chất tan: C₁·V₁ = C₂·V₂", "V₂ = C₁·V₁ / C₂"], results=res)


TOOLS = [
    ("Phương trình", "Bậc 1", [("a", "2", ""), ("b", "-6", "")], t_linear),
    ("Phương trình", "Bậc 2", [("a", "1", ""), ("b", "-3", ""), ("c", "2", "")], t_quad),
    ("Phương trình", "Bậc 3–10", [("Hệ số (cao → thấp)", "1 -6 11 -6", "VD: 1 -6 11 -6 ⇒ x³ − 6x² + 11x − 6 = 0")], t_poly),
    ("Phương trình", "Hệ 2 ẩn", [("Hệ 2 phương trình", "2 1 5; 1 -1 1", "#sys2")], lambda c, v: _sys(c, v, 2)),
    ("Phương trình", "Hệ 3 ẩn", [("Hệ 3 phương trình", "1 1 1 6; 2 -1 1 3; 1 2 -1 2", "#sys3")], lambda c, v: _sys(c, v, 3)),
    ("Phương trình", "Hệ 4 ẩn", [("Hệ 4 phương trình", "1 1 1 1 10; 1 -1 1 -1 2; 2 1 -1 1 3; 1 2 3 -1 4", "#sys4")], lambda c, v: _sys(c, v, 4)),
    ("Phương trình", "SOLVE f(x) = 0", [("f(x)", "x^3 - 2x - 5", "#expr"), ("Giá trị đầu", "2", "")], t_solve),
    ("Phương trình", "Bất phương trình", [("Hệ số đa thức (cao → thấp)", "1 -3 2", ""), ("Dấu", ">", "@>|<|>=|<=")], t_ineq),
    ("Giải tích", "Đạo hàm tại điểm", [("f(x)", "x^3 + sin(x)", "#expr"), ("x₀", "1", "")], t_deriv),
    ("Giải tích", "Tích phân xác định", [("f(x)", "x^2", "#expr"), ("Cận dưới a", "0", ""), ("Cận trên b", "3", "")], t_integral),
    ("Giải tích", "Giới hạn", [("f(x)", "sin(x)/x", "#expr"), ("x → (số hoặc inf)", "0", "")], t_limit),
    ("Giải tích", "Σ và Π", [("f(x) (biến x)", "x^2", "#expr"), ("Từ", "1", ""), ("Đến", "10", "")], t_sigma),
    ("Giải tích", "Bảng giá trị f(x)", [("f(x)", "x^2 - 3x + 2", "#expr"), ("Từ", "-3", ""), ("Đến", "5", ""), ("Bước", "1", "")], t_table),
    ("Giải tích", "CALC (thay biến)", [("Biểu thức", "x^2 + y", "#expr"), ("Gán (x=2; y=3)", "x=2; y=3", "")], t_calc),
    ("Thống kê", "Thống kê 1 biến", [("Giá trị", "2 4 4 5 7 9 10", "cách nhau bằng dấu cách / ; /,"), ("Tần số (tùy chọn)", "", "để trống = mỗi giá trị 1 lần")], t_stat1),
    ("Thống kê", "Hồi quy", [("Dãy x", "1 2 3 4 5", ""), ("Dãy y", "2.1 3.9 6.2 7.8 10.1", ""), ("Dạng hồi quy", "Tuyến tính (y = a + bx)", "@" + "|".join(KINDS)), ("Dự đoán tại x =", "6", "")], t_reg),
    ("Xác suất", "Phân phối chuẩn", [("μ", "0", ""), ("σ", "1", ""), ("a", "-1.96", ""), ("b", "1.96", "")], t_norm),
    ("Xác suất", "Phân vị chuẩn (InvN)", [("μ", "0", ""), ("σ", "1", ""), ("P(X < x)", "0.975", "")], t_norminv),
    ("Xác suất", "Nhị thức", [("n", "10", ""), ("p", "0.3", ""), ("k", "4", "")], t_binom),
    ("Xác suất", "Poisson", [("λ", "3", ""), ("k", "2", "")], t_poisson),
    ("Xác suất", "Tổ hợp – Chỉnh hợp", [("n", "10", ""), ("k", "3", "")], t_comb),
    ("Ma trận", "Ma trận", [("Ma trận A", "1 2; 3 4", "#mat"), ("Ma trận B / mũ n", "5 6; 7 8", "#matB"), ("Phép toán", "Định thức det(A)", "@Định thức det(A)|Nghịch đảo A⁻¹|Chuyển vị Aᵀ|Hạng rank(A)|Vết tr(A)|Trị riêng của A|A + B|A − B|A × B|Aⁿ (n nhập ở ô B)")], t_matop),
    ("Ma trận", "Vectơ", [("Vectơ a (2–3 thành phần)", "1 2 3", ""), ("Vectơ b", "4 5 6", "")], t_vec),
    ("Số", "Số phức", [("z / biểu thức", "(3+4i)*(1-2i)", "#expr"), ("Căn bậc n (tùy chọn)", "", "")], t_complex),
    ("Số", "Hệ cơ số", [("Số", "255", ""), ("Cơ số của số nhập", "Thập phân (DEC)", "@Thập phân (DEC)|Nhị phân (BIN)|Bát phân (OCT)|Thập lục phân (HEX)")], t_base),
    ("Số", "Logic bit", [("A", "12", ""), ("B", "10", "")], t_logic),
    ("Số", "ƯCLN · BCNN", [("Các số", "24 36 60", "")], t_gcd),
    ("Số", "Phân tích thừa số nguyên tố", [("Số nguyên", "360", "")], t_factor),
    ("Số", "Chia có dư", [("Số bị chia", "100", ""), ("Số chia", "7", "")], t_divide),
    ("Số", "Phân số ⇄ thập phân", [("Số", "0.375", "#expr")], t_frac),
    ("Số", "Lũy thừa modulo", [("a", "7", ""), ("b", "128", ""), ("m", "13", "")], t_modpow),
    ("Số", "Số ngẫu nhiên", [("Từ", "1", ""), ("Đến", "100", ""), ("Số lượng", "5", "")], t_rand),
    ("Hình học", "Giải tam giác", [("a", "5", "bỏ trống nếu chưa biết"), ("b", "6", ""), ("c", "7", ""), ("A (độ)", "", ""), ("B (độ)", "", ""), ("C (độ)", "", "")], t_triangle),
    ("Hình học", "Đường thẳng qua 2 điểm", [("x₁", "1", ""), ("y₁", "2", ""), ("x₂", "4", ""), ("y₂", "6", ""), ("Điểm P (tùy chọn: x y)", "", "")], t_line),
    ("Hình học", "Đường tròn qua 3 điểm", [("x₁", "0", ""), ("y₁", "0", ""), ("x₂", "4", ""), ("y₂", "0", ""), ("x₃", "0", ""), ("y₃", "3", "")], t_circle3),
    ("Hình học", "Diện tích – Thể tích", [("Hình", "Hình cầu (R)", "@Hình cầu (R)|Hình trụ (R, h)|Hình nón (R, h)|Hình nón cụt (R, r, h)|Hình hộp chữ nhật (a, b, c)|Hình lập phương (a)|Hình chóp (S đáy, h)|Lăng trụ (S đáy, h)"), ("Ô 1", "3", ""), ("Ô 2", "4", ""), ("Ô 3", "5", "")], t_area3d),
    ("Tiện ích", "Đổi đơn vị", [("Loại", "Độ dài", "@" + "|".join(list(ce.UNITS) + ["Nhiệt độ"])), ("Giá trị", "100", ""), ("Từ đơn vị", "km", ""), ("Sang đơn vị", "m", "")], t_unit),
    ("Tiện ích", "Tỉ lệ a:b = c:x", [("a", "2", ""), ("b", "5", ""), ("c", "8", "")], t_ratio),
    ("Tiện ích", "Phần trăm", [("Giá trị a", "250", ""), ("Phần trăm b", "15", "")], t_percent),
    ("Tiện ích", "Lãi suất – Trả góp", [("Vốn P", "100000000", ""), ("Lãi suất mỗi kỳ (%)", "1", ""), ("Số kỳ n", "12", "")], t_interest),
    ("Tiện ích", "Hóa học: Tính pH dung dịch", [("Loại dung dịch", "Acid yếu (C, Ka)", "@Acid mạnh (H⁺)|Base mạnh (OH⁻)|Acid yếu (C, Ka)|Base yếu (C, Kb)"), ("Nồng độ C (M)", "0.1", ""), ("Ka hoặc Kb (nếu yếu)", "1.8e-5", "VD: 1.8e-5 cho CH3COOH")], t_ph),
    ("Tiện ích", "Hóa học: Pha loãng C₁V₁ = C₂V₂", [("Nồng độ ban đầu C₁", "2", ""), ("Thể tích ban đầu V₁ (mL)", "50", ""), ("Nồng độ cần pha C₂", "0.5", "")], t_dilution),
    ("Tiện ích", "Hằng số vật lí", [("Lọc theo tên (để trống = tất cả)", "", "")], t_phys),
]


# ------------------------------------------------------------------------------
# Ô nhập trực quan cho biểu thức, hệ phương trình và ma trận trong ToolForm
# ------------------------------------------------------------------------------
class VisualExprInput(QWidget):
    """Ô nhập biểu thức toán học trực quan (phân số, căn, mũ, hàm…) kèm dải phím chèn nhanh."""
    submitted = Signal()
    changed = Signal()

    def __init__(self, default="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.nd = nd.NaturalDisplay(18, min_h=44, max_h=88)
        self.nd.placeholder = "Gõ trực tiếp (/ phân số · ^ mũ · sqrt( căn)"
        self.nd.from_calc(default)
        self.nd.submitted.connect(self.submitted.emit)
        self.nd.changed.connect(self.changed.emit)
        lay.addWidget(self.nd)

        bar = QHBoxLayout()
        bar.setSpacing(3)
        for lab, act in (
            ("a/b", "frac"), ("√", "sqrt"), ("x²", "sup2"), ("xⁿ", "sup"),
            ("|x|", "abs"), ("sin", "fn:sin"), ("cos", "fn:cos"),
            ("ln", "fn:ln"), ("π", "ch:π"), ("eˣ", "expe"),
        ):
            b = shrink_x(mk_btn(lab, pill=True))
            b.setFixedHeight(23)
            b.clicked.connect(lambda _, a=act: self._ins(a))
            bar.addWidget(b, 1)
        lay.addLayout(bar)

    def _ins(self, act):
        d = self.nd
        if act == "frac":
            d.put_frac()
        elif act == "sqrt":
            d.put_sqrt()
        elif act == "sup2":
            d.put_sup("2")
        elif act == "sup":
            d.put_sup()
        elif act == "abs":
            d.put_abs()
        elif act == "expe":
            d.put_char("e", "e")
            d.put_sup()
        elif act.startswith("fn:"):
            d.put_func(act[3:])
        elif act.startswith("ch:"):
            d.put_char(act[3:], act[3:])
        d.setFocus()

    def text(self):
        return self.nd.to_text()

    def latex_text(self):
        return self.nd.to_latex()

    def set_theme_colors(self, c, acc):
        self.nd.set_colors(c["text"], c["muted"], c["input"], c["border"], acc)


class VisualSystemGrid(QWidget):
    """Bảng nhập hệ phương trình n ẩn trực quan dạng { a·x + b·y = c."""
    submitted = Signal()
    changed = Signal()

    def __init__(self, n, default_str="", parent=None):
        super().__init__(parent)
        self.n = n
        self.cells = []
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 2, 0, 2)
        root.setSpacing(6)
        brace = QFrame()
        brace.setFixedWidth(4)
        brace.setStyleSheet("background:#6366F1; border-radius:2px;")
        root.addWidget(brace)

        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        rows_def = [r.strip().split() for r in default_str.split(";") if r.strip()]
        vars_ = "xyzt"[:n]
        for r in range(n):
            row_cells = []
            def_r = rows_def[r] if r < len(rows_def) else []
            col_ui = 0
            for c in range(n + 1):
                ed = shrink_x(QLineEdit(def_r[c] if c < len(def_r) else "0"))
                ed.setAlignment(Qt.AlignCenter)
                ed.setMinimumWidth(34)
                ed.returnPressed.connect(self.submitted.emit)
                ed.textChanged.connect(self.changed.emit)
                grid.addWidget(ed, r, col_ui)
                row_cells.append(ed)
                col_ui += 1
                if c < n:
                    suffix = f"{vars_[c]} +" if c < n - 1 else f"{vars_[c]} ="
                    lb = mk_label(suffix, "muted")
                    lb.setAlignment(Qt.AlignCenter)
                    grid.addWidget(lb, r, col_ui)
                    col_ui += 1
            self.cells.append(row_cells)
        root.addLayout(grid, 1)

    def text(self):
        return "; ".join(" ".join((ed.text().strip() or "0") for ed in r) for r in self.cells)


class VisualMatrixGrid(QWidget):
    """Bảng nhập ma trận trực quan kèm chọn nhanh cỡ (2×2, 3×3, 4×4, 2×3, 3×2)."""
    submitted = Signal()
    changed = Signal()

    SIZES = [("2×2", 2, 2), ("3×3", 3, 3), ("4×4", 4, 4), ("2×3", 2, 3), ("3×2", 3, 2)]

    def __init__(self, default_str="", allow_scalar=False, parent=None):
        super().__init__(parent)
        self.allow_scalar = allow_scalar
        self.cells = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(6)
        top.addWidget(mk_label("Cỡ:", "muted"))
        self.cmb_sz = fix_combo(QComboBox(), 6, fixed_w=96)
        for lab, r, c in self.SIZES:
            self.cmb_sz.addItem(lab, (r, c))
        if allow_scalar:
            self.cmb_sz.addItem("Số mũ n", (1, 1))
        top.addWidget(self.cmb_sz)
        top.addStretch()
        lay.addLayout(top)

        self.box = QFrame()
        self.box.setProperty("panel", True)
        self.grid = QGridLayout(self.box)
        self.grid.setContentsMargins(8, 6, 8, 6)
        self.grid.setSpacing(4)
        lay.addWidget(self.box)

        rows_def = [r.strip().split() for r in default_str.split(";") if r.strip()]
        r0 = max(1, len(rows_def)) if rows_def else 2
        c0 = max(1, len(rows_def[0])) if rows_def else 2
        idx = next((i for i, (_, rr, cc) in enumerate(self.SIZES) if (rr, cc) == (r0, c0)), 0)
        self.cmb_sz.setCurrentIndex(idx)
        self._rebuild(r0, c0, rows_def)
        self.cmb_sz.currentIndexChanged.connect(self._on_size_changed)

    def _on_size_changed(self):
        r, c = self.cmb_sz.currentData()
        old = [[ed.text().strip() for ed in row] for row in self.cells]
        self._rebuild(r, c, old)
        self.changed.emit()

    def _rebuild(self, rows, cols, init_vals=()):
        while self.grid.count():
            it = self.grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.cells = []
        for r in range(rows):
            rc = []
            for c in range(cols):
                v = init_vals[r][c] if (r < len(init_vals) and c < len(init_vals[r])) else ("2" if (rows == 1 and cols == 1) else ("1" if r == c else "0"))
                ed = shrink_x(QLineEdit(v))
                ed.setAlignment(Qt.AlignCenter)
                ed.setMinimumWidth(36)
                ed.returnPressed.connect(self.submitted.emit)
                ed.textChanged.connect(self.changed.emit)
                self.grid.addWidget(ed, r, c)
                rc.append(ed)
            self.cells.append(rc)

    def text(self):
        if len(self.cells) == 1 and len(self.cells[0]) == 1:
            return self.cells[0][0].text().strip() or "2"
        return "; ".join(" ".join((ed.text().strip() or "0") for ed in r) for r in self.cells)


def _poly_to_latex(coeffs):
    """Chuyển danh sách hệ số đa thức sang chuỗi LaTeX đẹp (VD: x^3 - 6x^2 + 11x - 6)."""
    deg = len(coeffs) - 1
    parts = []
    for idx, c in enumerate(coeffs):
        s = c.strip()
        if not s or s in ("0", "+0", "-0"):
            continue
        p = deg - idx
        neg = s.startswith("-")
        mag = s.lstrip("+-")
        if p > 0 and mag == "1":
            mag = ""
        term = mag + ("" if p == 0 else ("x" if p == 1 else f"x^{{{p}}}"))
        if not parts:
            parts.append(("-" if neg else "") + term)
        else:
            parts.append((" - " if neg else " + ") + term)
    return "".join(parts) or "0"


_PREVIEW_TOOLS = {
    "Bậc 1", "Bậc 2", "Bậc 3–10", "Bất phương trình", "SOLVE f(x) = 0",
    "Đạo hàm tại điểm", "Tích phân xác định", "Giới hạn", "Σ và Π",
    "Bảng giá trị f(x)", "Tỉ lệ a:b = c:x", "Lũy thừa modulo",
}


class ToolForm(QWidget):
    def __init__(self, ctx, tool, parent=None):
        super().__init__(parent)
        self.ctx, self.tool = ctx, tool
        self.calc = ce.Calc()
        _, name, fields, fn = tool
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)
        lay.addWidget(mk_label(name, "h2"))

        # Thanh xem trước công thức trực quan (tự cập nhật khi gõ hệ số / hàm số)
        self.preview_nd = None
        if name in _PREVIEW_TOOLS:
            self.preview_nd = nd.NaturalDisplay(19, readonly=True, min_h=48, max_h=88)
            lay.addWidget(self.preview_nd)

        self.edits = []
        self._expr_widgets = []
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        for i, (lab, default, hint) in enumerate(fields):
            grid.addWidget(QLabel(lab), i, 0)
            if hint.startswith("@"):
                opts = hint[1:].split("|")
                w = fix_combo(QComboBox(), 10, searchable=(len(opts) >= 6))
                w.addItems(opts)
                if default in opts:
                    w.setCurrentText(default)
                w.currentIndexChanged.connect(self._update_preview)
                self.edits.append(w)
            elif hint == "#expr":
                w = VisualExprInput(default)
                w.submitted.connect(self.run)
                w.changed.connect(self._update_preview)
                self._expr_widgets.append(w)
                self.edits.append(w)
            elif hint in ("#sys2", "#sys3", "#sys4"):
                w = VisualSystemGrid(int(hint[-1]), default)
                w.submitted.connect(self.run)
                self.edits.append(w)
            elif hint in ("#mat", "#matB"):
                w = VisualMatrixGrid(default, allow_scalar=(hint == "#matB"))
                w.submitted.connect(self.run)
                self.edits.append(w)
            else:
                w = QLineEdit(default)
                if hint:
                    w.setPlaceholderText(hint)
                w.returnPressed.connect(self.run)
                w.textChanged.connect(self._update_preview)
                self.edits.append(w)
            grid.addWidget(w, i, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        r = QHBoxLayout()
        b = mk_btn("Tính", primary=True)
        b.clicked.connect(self.run)
        bc = mk_btn("Sao chép kết quả")
        bc.clicked.connect(lambda: copy_text(self.out.toPlainText()))
        r.addWidget(b)
        r.addWidget(bc)
        r.addStretch()
        lay.addLayout(r)
        self.out = QTextBrowser()
        self.out.setMinimumHeight(200)
        lay.addWidget(self.out, 1)
        self._ran = False
        self._theme_dirty = False
        self.refresh_theme()
        self._update_preview()

    def _raw_val(self, e):
        if isinstance(e, QComboBox):
            return i18n.combo_key(e)
        return e.text()

    def _latex_val(self, e):
        if isinstance(e, VisualExprInput):
            return e.latex_text() or "?"
        if isinstance(e, QComboBox):
            return i18n.combo_key(e)
        return e.text().strip() or "?"

    def _update_preview(self):
        if self.preview_nd is None:
            return
        name = self.tool[1]
        tex = ""
        try:
            if name == "Bậc 1":
                tex = _poly_to_latex([self._raw_val(self.edits[0]), self._raw_val(self.edits[1])]) + " = 0"
            elif name == "Bậc 2":
                tex = _poly_to_latex([self._raw_val(self.edits[0]), self._raw_val(self.edits[1]), self._raw_val(self.edits[2])]) + " = 0"
            elif name == "Bậc 3–10":
                cs = [x for x in re.split(r"[\s,;]+", self._raw_val(self.edits[0]).strip()) if x]
                tex = (_poly_to_latex(cs) + " = 0") if cs else "P(x) = 0"
            elif name == "Bất phương trình":
                cs = [x for x in re.split(r"[\s,;]+", self._raw_val(self.edits[0]).strip()) if x]
                op = {">=": r"\geq", "<=": r"\leq"}.get(self._raw_val(self.edits[1]).strip(), self._raw_val(self.edits[1]).strip())
                tex = f"{_poly_to_latex(cs)} {op} 0" if cs else ""
            elif name == "SOLVE f(x) = 0":
                tex = f"{self._latex_val(self.edits[0])} = 0"
            elif name == "Đạo hàm tại điểm":
                tex = f"\\frac{{d}}{{dx}}\\left({self._latex_val(self.edits[0])}\\right)\\mid_{{x={self._latex_val(self.edits[1])}}}"
            elif name == "Tích phân xác định":
                tex = f"\\int_{{{self._latex_val(self.edits[1])}}}^{{{self._latex_val(self.edits[2])}}} {self._latex_val(self.edits[0])}\\,dx"
            elif name == "Giới hạn":
                t = self._latex_val(self.edits[1]).replace("inf", r"\infty").replace("∞", r"\infty")
                tex = f"\\lim_{{x \\to {t}}} {self._latex_val(self.edits[0])}"
            elif name == "Σ và Π":
                tex = f"\\sum_{{x={self._latex_val(self.edits[1])}}}^{{{self._latex_val(self.edits[2])}}} {self._latex_val(self.edits[0])}"
            elif name == "Bảng giá trị f(x)":
                tex = f"f(x) = {self._latex_val(self.edits[0])}"
            elif name == "Tỉ lệ a:b = c:x":
                tex = f"\\frac{{{self._latex_val(self.edits[0])}}}{{{self._latex_val(self.edits[1])}}} = \\frac{{{self._latex_val(self.edits[2])}}}{{x}}"
            elif name == "Lũy thừa modulo":
                tex = f"{self._latex_val(self.edits[0])}^{{{self._latex_val(self.edits[1])}}} \\pmod{{{self._latex_val(self.edits[2])}}}"
        except Exception:
            tex = ""
        if tex:
            self.preview_nd.from_latex(tex)

    def refresh_theme(self):
        from ui_common import ACCENTS
        c = self.ctx.palette
        acc = ACCENTS.get(self.ctx.prefs.get("accent", "Chàm"), ACCENTS["Chàm"])[0]
        for w in self._expr_widgets:
            w.set_theme_colors(c, acc)
        if self.preview_nd is not None:
            self.preview_nd.set_colors(acc, c["muted"], c["surface2"], c["border"], acc)

    def showEvent(self, e):
        super().showEvent(e)
        if not self._ran or self._theme_dirty:
            self._ran = True
            self._theme_dirty = False
            self.refresh_theme()
            self.run()

    def run(self):
        self._ran = True
        self._update_preview()
        try:
            vals = [self._raw_val(e) for e in self.edits]
        except nd.Incomplete:
            self.out.setHtml(err_html("Biểu thức còn ô trống nét đứt — hãy điền đầy đủ trước khi bấm Tính."))
            return
        try:
            r = self.tool[3](self.calc, vals)
            self.out.setHtml(html_result(r["title"], r.get("steps", ()), r.get("results", ()), r.get("notes", ()), r.get("mono"), self.ctx.dark))
        except ce.CalcError as exc:
            self.out.setHtml(err_html(str(exc)))
        except (ValueError, ZeroDivisionError, OverflowError, IndexError, KeyError) as exc:
            self.out.setHtml(err_html(f"Dữ liệu nhập không hợp lệ ({exc.__class__.__name__}: {exc}). Kiểm tra lại cách nhập."))


# ------------------------------------------------------------------------------
# MÁY TÍNH CHÍNH
# ------------------------------------------------------------------------------
class CalculatorSection(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.calc = ce.Calc()
        self.shift = False
        self.fixed_mode = "auto"      # auto | dec
        self.last_val = None
        self._res_text = ""
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(12)

        # ---- Trái: máy tính khoa học cao cấp
        left = mk_card(QVBoxLayout(), margins=(10, 10, 10, 10), spacing=7)
        left.setMinimumWidth(330)
        left.setMaximumWidth(468)
        left.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        hd = QHBoxLayout()
        hd.setSpacing(6)
        hd.addWidget(shrink_x(mk_label("Máy tính khoa học", "h1")), 1)
        self.b_ang = mk_btn("DEG", pill=True, tip="Đơn vị góc: DEG → RAD → GRA")
        self.b_ang.clicked.connect(self.cycle_angle)
        self.b_cx = mk_btn("Số phức: tắt", pill=True, checkable=True, tip="Bật để tính căn số âm, ln số âm… ra số phức")
        self.b_cx.setProperty("_i18n_skip", True)
        self.b_cx.clicked.connect(lambda: (setattr(self.calc, "complex_mode", self.b_cx.isChecked()), self._sync_cx_btn()))
        hd.addWidget(self.b_ang)
        hd.addWidget(self.b_cx)
        left.layout().addLayout(hd)

        # Khung màn hình LCD 2 dòng + thanh trạng thái biến nhớ
        lcd = QFrame()
        lcd.setProperty("calcdisplay", True)
        ll = QVBoxLayout(lcd)
        ll.setContentsMargins(10, 8, 10, 8)
        ll.setSpacing(4)
        mem_row = QHBoxLayout()
        mem_row.setSpacing(6)
        self.lbl_mem = shrink_x(mk_label("EXACT · Ans = 0", "badge"))
        mem_row.addWidget(self.lbl_mem, 1)
        for var_name in ("A", "B"):
            bm = mk_btn(f"→{var_name}", pill=True, tip=f"Lưu kết quả hiện tại vào biến {var_name}")
            bm.clicked.connect(lambda _, vn=var_name: self.store_var(vn))
            mem_row.addWidget(bm)
        ll.addLayout(mem_row)

        self.inp = nd.NaturalDisplay(25)
        self.inp.placeholder = "Nhập biểu thức, bấm = hoặc Enter để tính"
        self.inp.submitted.connect(self.equals)
        ll.addWidget(self.inp)

        self.res = nd.NaturalDisplay(29, readonly=True, align_right=True)
        self.res.setMinimumHeight(60)
        ll.addWidget(self.res)

        self.lbl_alt = QLabel("")
        self.lbl_alt.setAlignment(Qt.AlignRight)
        self.lbl_alt.setProperty("muted", True)
        self.lbl_alt.setWordWrap(True)
        ll.addWidget(self.lbl_alt)
        left.layout().addWidget(lcd)

        mode = QHBoxLayout()
        mode.setSpacing(5)
        self.b_sd = shrink_x(mk_btn("S⇔D  Chính xác ⇄ Thập phân", prop=("subtle", True), tip="Chuyển đổi hiển thị phân số / căn / π ⇄ thập phân"))
        self.b_sd.clicked.connect(self.toggle_sd)
        self.b_dms = mk_btn("° ′ ″", prop=("subtle", True), tip="Đổi kết quả sang độ-phút-giây")
        self.b_dms.clicked.connect(self.to_dms)
        from word_ui import word_button
        b_word = word_button(ctx, self, lambda: {"kind": "math", "latex": f"{self.inp.to_display()} = {self._res_text}"} if self._res_text else None, label="Word")
        mode.addWidget(self.b_sd, 1)
        mode.addWidget(self.b_dms)
        mode.addWidget(b_word)
        left.layout().addLayout(mode)

        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        left.layout().addLayout(self.grid)
        self.fn_buttons = {}
        self._build_keys()
        left.layout().addStretch(1)
        root.addWidget(left)

        # ---- Phải: tìm nhanh 43 công cụ + tab công cụ + lịch sử
        right = QVBoxLayout()
        right.setSpacing(8)
        search_bar = mk_card(QHBoxLayout(), margins=(10, 7, 10, 7), spacing=8)
        search_bar.layout().addWidget(mk_label("Tìm nhanh:", "muted"))
        self.cmb_jump = fix_combo(QComboBox(), 10, searchable=True)
        self.cmb_jump.addItem("— Tìm nhanh trong 43 bộ giải —", None)
        search_bar.layout().addWidget(self.cmb_jump, 1)
        right.addWidget(search_bar)

        self.tabs = QTabWidget()
        self.tabs.tabBar().setStyleSheet("QTabBar::tab { padding: 6px 10px; margin-right: 3px; font-size: 12px; }")
        self.tabs.setUsesScrollButtons(True)
        groups = list(dict.fromkeys(t[0] for t in TOOLS))
        short = {"Phương trình": "Phương trình", "Giải tích": "Giải tích", "Thống kê": "Thống kê", "Xác suất": "Xác suất",
                 "Ma trận": "Ma trận · Vectơ", "Số": "Số · Phức", "Hình học": "Hình học", "Tiện ích": "Tiện ích · Hóa"}
        self._tool_forms = []
        self._group_widgets = {}
        for gi, g in enumerate(groups):
            page = QWidget()
            pl = QVBoxLayout(page)
            pl.setContentsMargins(0, 6, 0, 0)
            cr = QHBoxLayout()
            cr.addWidget(mk_label("Công cụ:", "muted"))
            cmb = fix_combo(QComboBox(), 10, searchable=True)
            stack = QStackedWidget()
            g_tools = [t for t in TOOLS if t[0] == g]
            built = {}
            for ti, t in enumerate(g_tools):
                cmb.addItem(t[1])
                stack.addWidget(QWidget())  # placeholder nhẹ, chỉ tạo ToolForm khi mở
                self.cmb_jump.addItem(f"[{short[g]}]  {t[1]}", (gi, ti))

            def _ensure(idx, _stack=stack, _tools=g_tools, _built=built):
                if idx < 0 or idx >= len(_tools):
                    return
                if idx not in _built:
                    tf = ToolForm(ctx, _tools[idx])
                    i18n.apply_lang_to_tree(tf)
                    old = _stack.widget(idx)
                    _stack.removeWidget(old)
                    old.deleteLater()
                    _stack.insertWidget(idx, tf)
                    _built[idx] = tf
                    self._tool_forms.append(tf)
                _stack.setCurrentIndex(idx)

            cmb.currentIndexChanged.connect(_ensure)
            self._group_widgets[gi] = (cmb, stack, _ensure)
            cr.addWidget(cmb, 1)
            pl.addLayout(cr)
            pl.addWidget(stack, 1)
            self.tabs.addTab(page, esc(short[g]))
        # Khởi tạo công cụ đầu tiên khi người dùng đổi tab
        self.tabs.currentChanged.connect(lambda gi: self._group_widgets[gi][2](self._group_widgets[gi][0].currentIndex()) if gi in self._group_widgets else None)
        self._group_widgets[0][2](0)
        self.cmb_jump.activated.connect(self._jump_to_tool)
        right.addWidget(self.tabs, 3)

        hist = mk_card(QVBoxLayout(), margins=(12, 9, 12, 9), spacing=6)
        hh = QHBoxLayout()
        hh.addWidget(shrink_x(mk_label("Lịch sử (nhấp đúp để dùng lại)", "h2")), 1)
        bcl = mk_btn("Xóa", prop=("danger", True))
        bcl.clicked.connect(lambda: self.hist.clear())
        hh.addWidget(bcl)
        hist.layout().addLayout(hh)
        self.hist = QListWidget()
        self.hist.setMaximumHeight(155)
        self.hist.itemDoubleClicked.connect(self._reuse)
        hist.layout().addWidget(self.hist)
        right.addWidget(hist, 1)
        root.addLayout(right, 1)
        self.refresh_theme()

    def _jump_to_tool(self, idx):
        data = self.cmb_jump.itemData(idx)
        if not data:
            return
        gi, ti = data
        self.tabs.setCurrentIndex(gi)
        cmb, stack, ensure = self._group_widgets[gi]
        cmb.setCurrentIndex(ti)
        ensure(ti)
        self.cmb_jump.blockSignals(True)
        self.cmb_jump.setCurrentIndex(0)
        self.cmb_jump.blockSignals(False)

    def store_var(self, name):
        if self.last_val is None:
            self.ctx.say("Chưa có kết quả để lưu.")
            return
        self.calc.vars[name] = self.last_val
        self._update_mem_badge()
        self.ctx.say(f"Đã lưu {ce.fmt_num(self.last_val)} vào biến {name}.")

    def _update_mem_badge(self):
        parts = ["DEC" if self.fixed_mode == "dec" else "EXACT"]
        if self.last_val is not None:
            parts.append(f"Ans = {ce.fmt_num(self.last_val, 6)}")
        for k in ("A", "B"):
            if k in self.calc.vars and self.calc.vars[k] != 0:
                parts.append(f"{k} = {ce.fmt_num(self.calc.vars[k], 5)}")
        self.lbl_mem.setText("  ·  ".join(parts))

    def _sync_cx_btn(self):
        on = self.b_cx.isChecked()
        self.b_cx.setText(esc(("Complex: ON" if on else "Complex: OFF") if i18n.is_en() else ("Số phức: bật" if on else "Số phức: tắt")))

    def refresh_lang(self):
        self._sync_cx_btn()
        self.inp.placeholder = "Enter expression, press = or Enter" if i18n.is_en() else "Nhập biểu thức, bấm = hoặc Enter để tính"
        self.inp.update()
        for tf in getattr(self, "_tool_forms", ()):
            i18n.apply_lang_to_tree(tf)
            if tf._ran:
                tf.run()

    def refresh_theme(self):
        from ui_common import ACCENTS
        c = self.ctx.palette
        acc = ACCENTS.get(self.ctx.prefs.get("accent", "Chàm"), ACCENTS["Chàm"])[0]
        self.inp.set_colors(c["text"], c["muted"], c["input"], c["input"], acc)
        self.res.set_colors(acc, c["muted"], c["input"], c["input"], acc)
        for tf in getattr(self, "_tool_forms", ()):
            tf.refresh_theme()
            if tf._ran:
                if tf.isVisible():
                    tf.run()
                else:
                    tf._theme_dirty = True

    def _reuse(self, it):
        self.inp.from_data(it.data(Qt.UserRole))
        self.inp.setFocus()

    # ---- bàn phím: (nhãn, nhãn SHIFT, hành động, hành động SHIFT, kiểu)
    def _build_keys(self):
        F = lambda n: "func:" + n  # noqa: E731
        rows = [
            [("SHIFT", None, "shift", None, "fn"), ("sin", "sin⁻¹", F("sin"), F("asin"), "fn"), ("cos", "cos⁻¹", F("cos"), F("acos"), "fn"), ("tan", "tan⁻¹", F("tan"), F("atan"), "fn"),
             ("π", "e", "ch:π", "ch:e", "fn"), ("Ans", "→A", "ch:Ans", "ch:→A|->A", "fn")],
            [("x²", "x³", "sup2", "sup3", "fn"), ("xʸ", "ʸ√x", "supy", "root", "fn"), ("√", "∛", "sqrt", "root3", "fn"), ("log", "10ˣ", F("log"), "pow10", "fn"),
             ("ln", "eˣ", F("ln"), "expe", "fn"), ("n!", "|x|", "ch:!", "abs", "fn")],
            [("(", "[", "open", "open", "fn"), (")", "]", "close", "close", "fn"), ("nCr", "nPr", F("nCr"), F("nPr"), "fn"), ("Pol", "Rec", F("Pol"), F("Rec"), "fn"),
             ("EXP", "i", "exp10", "ch:i", "fn"), ("%", "mod", "ch:%", "ch:mod| mod ", "fn")],
            [("7", None, "ch:7", None, "num"), ("8", None, "ch:8", None, "num"), ("9", None, "ch:9", None, "num"), ("DEL", None, "del", None, "ac"), ("AC", None, "ac", None, "ac"), ("÷", None, "div", None, "op")],
            [("4", None, "ch:4", None, "num"), ("5", None, "ch:5", None, "num"), ("6", None, "ch:6", None, "num"), ("×", None, "ch:×|*", None, "op"), ("−", None, "ch:−|-", None, "op"), ("x⁻¹", "!", "supm1", "ch:!", "fn")],
            [("1", None, "ch:1", None, "num"), ("2", None, "ch:2", None, "num"), ("3", None, "ch:3", None, "num"), ("+", None, "ch:+", None, "op"), ("A", "B", "ch:A", "ch:B", "fn"), ("a/b", None, "frac", None, "fn")],
            [("0", None, "ch:0", None, "num"), (".", None, "ch:.", None, "num"), ("abs", "i", "abs", "ch:i", "fn"), ("Copy", None, "copy", None, "fn"), ("Ans", None, "ch:Ans", None, "fn"), ("=", None, "=", None, "eq")],
            [("◀", None, "left", None, "fn"), ("▶", None, "right", None, "fn"), ("▲", None, "up", None, "fn"), ("▼", None, "down", None, "fn"), (",", None, "ch:,", None, "fn"), ("x", "y", "ch:x", "ch:y", "fn")],
        ]
        for r, row in enumerate(rows):
            for c, (lab, sh, act, sact, kind) in enumerate(row):
                b = mk_btn(lab, prop=("key", kind))
                b.setFixedHeight(40)
                b.setMinimumWidth(46)
                b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                b.clicked.connect(lambda _, a=act, s=sact: self.press(a, s))
                self.grid.addWidget(b, r, c)
                self.fn_buttons[(r, c)] = (b, lab, sh)

    def press(self, act, sact):
        if act == "shift":
            self.shift = not self.shift
            for (b, l, s) in self.fn_buttons.values():
                if s:
                    b.setText(esc(s if self.shift else l))
            self.sender().setStyleSheet("background:#F59E0B; color:white;" if self.shift else "")
            return
        if self.shift and sact:
            act = sact
            self.press_off()
        elif self.shift:
            self.press_off()
        self.run_action(act)
        self.inp.setFocus()

    def run_action(self, act):
        d = self.inp
        if act.startswith("ch:"):
            disp, _, ins = act[3:].partition("|")
            d.put_char(disp, ins or None)
        elif act.startswith("func:"):
            d.put_func(act[5:])
        elif act == "ac":
            d.clear()
            self.res.clear()
            self.lbl_alt.setText("")
            self._res_text = ""
        elif act == "del":
            d.backspace()
        elif act == "=":
            self.equals()
        elif act == "copy":
            copy_text(self._res_text)
            self.ctx.say("Đã sao chép kết quả.")
        elif act == "sqrt":
            d.put_sqrt()
        elif act == "root":
            d.put_root()
        elif act == "root3":
            d.put_root("3")
        elif act == "sup2":
            d.put_sup("2")
        elif act == "sup3":
            d.put_sup("3")
        elif act == "supy":
            d.put_sup()
        elif act == "supm1":
            d.put_sup("-1")
        elif act == "pow10":
            d.put_char("10")
            d.put_sup()
        elif act == "expe":
            d.put_char("e")
            d.put_sup()
        elif act == "exp10":
            d.put_char("×10", "*10")
            d.put_sup()
        elif act == "abs":
            d.put_abs()
        elif act == "frac":
            d.put_frac()
        elif act == "div":
            d.put_div()
        elif act == "open":
            d.type_open()
        elif act == "close":
            d.type_close()
        elif act in ("left", "right"):
            d.move(-1 if act == "left" else 1)
        elif act in ("up", "down"):
            d.move_vertical(act == "up")

    def press_off(self):
        self.shift = False
        for (b, l, s) in self.fn_buttons.values():
            if s:
                b.setText(esc(l))
            if l == "SHIFT":
                b.setStyleSheet("")

    def cycle_angle(self):
        nxt = {"DEG": "RAD", "RAD": "GRA", "GRA": "DEG"}[self.calc.angle]
        self.calc.angle = nxt
        self.b_ang.setText(nxt)

    def toggle_sd(self):
        self.fixed_mode = "dec" if self.fixed_mode != "dec" else "auto"
        self.show_value(self.last_val)
        self._update_mem_badge()

    def to_dms(self):
        if isinstance(self.last_val, (int, float)):
            self.lbl_alt.setText(("DMS: " if i18n.is_en() else "Độ–phút–giây: ") + ce.to_dms(self.last_val))

    def _error(self, title, detail=""):
        self.res.set_pretty(title)
        self.lbl_alt.setText(detail)
        self._res_text = ""

    def equals(self):
        if self.inp.is_empty():
            return
        try:
            t = self.inp.to_text()
        except nd.Incomplete:
            self._error("Lỗi cú pháp", "Biểu thức còn ô trống. Điền vào ô nét đứt hoặc xóa mẫu công thức đó.")
            return
        try:
            v = self.calc.evaluate(t)
        except ce.CalcError as exc:
            self._error("Lỗi", str(exc))
            return
        except (ValueError, OverflowError, ZeroDivisionError, RecursionError) as exc:
            self._error("Lỗi", f"Lỗi Math: {exc}")
            return
        self.last_val = v
        self.show_value(v)
        self._update_mem_badge()
        it = QListWidgetItem(f"{self.inp.to_display()}   =   {self._res_text or ce.fmt_num(v)}")
        it.setData(Qt.UserRole, self.inp.to_data())
        self.hist.insertItem(0, it)

    def show_value(self, v):
        if v is None:
            return
        txt = ce.fmt_num(v)
        ex = None if self.fixed_mode == "dec" else (ce.exact_form(v) if not isinstance(v, (int, complex)) else None)
        if ex:
            self.res.set_pretty(ex)
            self._res_text = ex
            self.lbl_alt.setText(f"{'Decimal' if i18n.is_en() else 'Thập phân'}: {txt}")
        else:
            self.res.set_pretty(txt)
            self._res_text = txt
            alts = []
            if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v).is_integer() is False and self.fixed_mode == "dec":
                f = Fraction(v).limit_denominator(100000)
                if abs(float(f) - v) < 1e-9:
                    alts.append(f"{'Fraction' if i18n.is_en() else 'Phân số'}: {ce.frac_str(f)}")
            if isinstance(v, int) and abs(v) < 10 ** 12 and v > 1:
                alts.append(f"{'Binary' if i18n.is_en() else 'Hệ nhị phân'}: " + ce.to_base(v, 2) + "   ·   Hex: " + ce.to_base(v, 16))
            self.lbl_alt.setText("   ".join(alts))
