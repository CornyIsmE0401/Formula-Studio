# -*- coding: utf-8 -*-
"""calc_engine.py - Bộ máy tính khoa học kiểu Casio fx-580VN X: phân tích biểu thức, giải phương trình,
bất phương trình, thống kê, phân phối, ma trận, vectơ, số phức, hệ cơ số, đạo hàm/tích phân, số học, đổi đơn vị."""
import cmath
import math
import random
import re
from fractions import Fraction
from itertools import combinations_with_replacement  # noqa: F401
from math import gcd

# ==============================================================================
# 1. TRÌNH PHÂN TÍCH BIỂU THỨC
# ==============================================================================
CONSTS = {"pi": math.pi, "π": math.pi, "e": math.e, "i": 1j, "phi": (1 + 5 ** 0.5) / 2}
FUNC_NAMES = ["sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "asin", "acos", "atan", "sin", "cos", "tan", "log10", "log2", "ln", "log",
              "sqrt", "cbrt", "abs", "exp", "fact", "floor", "ceil", "round", "sign", "gcd", "lcm", "nCr", "nPr", "root", "mod", "rem",
              "Pol", "Rec", "deriv", "integral", "sigma", "prod", "re", "im", "conj", "arg", "rand", "randint", "max", "min", "sec", "csc", "cot",
              "deg", "rad", "fib", "isprime", "dms", "pow", "hypot", "atan2", "normpdf", "normcdf", "binom", "cdf"]
LAZY = {"deriv", "integral", "sigma", "prod"}


class CalcError(Exception):
    pass


def _tok(s):
    s = re.sub(r"(\d+)\s*C\s*(\d+)", r"nCr(\1,\2)", s)
    s = re.sub(r"(\d+)\s*P\s*(\d+)", r"nPr(\1,\2)", s)
    s = (s.replace("×", "*").replace("÷", "/").replace("−", "-").replace("–", "-").replace("²", "^2").replace("³", "^3")
         .replace("√", " sqrt").replace("∛", " cbrt").replace("°", "°").replace("⁻¹", "^(-1)").replace("**", "^").replace("·", "*"))
    toks, i, n = [], 0, len(s)
    names = sorted(FUNC_NAMES + list(CONSTS) + ["Ans", "ans", "x", "y", "z", "t", "A", "B", "C", "D", "E", "F", "M", "X", "Y", "n", "k", "u", "v"], key=len, reverse=True)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
        elif c.isdigit() or (c == "." and i + 1 < n and s[i + 1].isdigit()):
            m = re.match(r"\d*\.?\d*(?:[eE][+-]?\d+)?", s[i:])
            txt = m.group(0)
            # tránh nuốt chữ e là hằng số: '2e' không có số mũ -> chỉ lấy phần số
            if txt and txt[-1] in "eE":
                txt = txt[:-1]
            toks.append(("num", float(txt) if ("." in txt or "e" in txt.lower()) else int(txt)))
            i += len(txt)
        elif c in "+-*/^(),!%°=<>→":
            if c == "→":
                toks.append(("op", "->"))
            else:
                toks.append(("op", c))
            i += 1
        elif c == "-" and s[i:i + 2] == "->":
            toks.append(("op", "->"))
            i += 2
        elif c.isalpha() or c == "π":
            for nm in names:
                if s.startswith(nm, i):
                    # nCr, nPr dạng trung tố: 5C2, 5P2 xử lý ở dưới
                    toks.append(("id", nm))
                    i += len(nm)
                    break
            else:
                raise CalcError(f"Không hiểu ký hiệu '{c}'")
        else:
            raise CalcError(f"Ký tự không hợp lệ '{c}'")
    # "->" xử lý
    out = []
    j = 0
    while j < len(toks):
        if toks[j] == ("op", "-") and j + 1 < len(toks) and toks[j + 1] == ("op", ">"):
            out.append(("op", "->"))
            j += 2
        else:
            out.append(toks[j])
            j += 1
    return out


def _insert_mul(toks):
    out = []
    for k, t in enumerate(toks):
        if out:
            p = out[-1]
            p_val = p[0] in ("num",) or (p[0] == "id" and p[1] not in FUNC_NAMES) or p == ("op", ")") or p == ("op", "!") or p == ("op", "%") or p == ("op", "°")
            t_start = t[0] == "num" or t[0] == "id" or t == ("op", "(")
            if p_val and t_start:
                # 'sin 30' xử lý ở parser; 2sin(x) -> 2*sin(x)
                out.append(("op", "*"))
            elif p[0] == "id" and p[1] in FUNC_NAMES and p[1] not in LAZY and t[0] in ("num",):
                pass
        out.append(t)
    return out


class Calc:
    def __init__(self):
        self.angle = "DEG"
        self.vars = {c: 0.0 for c in "ABCDEFMXYZ"}
        self.ans = 0.0
        self.complex_mode = False

    # --- góc
    def _to_rad(self, x):
        return math.radians(x) if self.angle == "DEG" else (x * math.pi / 200 if self.angle == "GRA" else x)

    def _from_rad(self, x):
        return math.degrees(x) if self.angle == "DEG" else (x * 200 / math.pi if self.angle == "GRA" else x)

    # --- phân tích
    def parse(self, text):
        toks = _insert_mul(_tok(text))
        self._t, self._p = toks, 0
        node = self._assign()
        if self._p < len(self._t):
            raise CalcError("Cú pháp sai (thừa ký tự hoặc thiếu toán tử).")
        return node

    def _peek(self):
        return self._t[self._p] if self._p < len(self._t) else (None, None)

    def _eat(self, val=None):
        t = self._peek()
        if val is not None and t != ("op", val):
            raise CalcError(f"Thiếu '{val}'")
        self._p += 1
        return t

    def _assign(self):
        node = self._expr()
        if self._peek() == ("op", "->"):
            self._eat()
            t = self._eat()
            if t[0] != "id":
                raise CalcError("Sau → phải là tên biến (A–F, M, X, Y).")
            return ("store", node, t[1])
        return node

    def _expr(self):
        node = self._term()
        while self._peek() in (("op", "+"), ("op", "-")):
            op = self._eat()[1]
            node = ("bin", op, node, self._term())
        return node

    def _term(self):
        node = self._unary()
        while self._peek() in (("op", "*"), ("op", "/")):
            op = self._eat()[1]
            node = ("bin", op, node, self._unary())
        return node

    def _unary(self):
        if self._peek() == ("op", "-"):
            self._eat()
            return ("neg", self._unary())
        if self._peek() == ("op", "+"):
            self._eat()
            return self._unary()
        return self._power()

    def _power(self):
        base = self._postfix()
        if self._peek() == ("op", "^"):
            self._eat()
            if self._peek() == ("op", "-"):
                self._eat()
                ex = ("neg", self._pow_operand())
            else:
                ex = self._pow_operand()
            return ("bin", "^", base, ex)
        return base

    def _pow_operand(self):
        # số mũ kết hợp phải: a^b^c, cho phép -x và hàm
        node = self._postfix()
        if self._peek() == ("op", "^"):
            self._eat()
            node = ("bin", "^", node, self._pow_operand())
        return node

    def _postfix(self):
        node = self._atom()
        while True:
            t = self._peek()
            if t == ("op", "!"):
                self._eat()
                node = ("fn", "fact", [node])
            elif t == ("op", "%"):
                self._eat()
                node = ("bin", "/", node, ("num", 100))
            elif t == ("op", "°"):
                self._eat()
                node = ("deg", node)
            else:
                break
        return node

    def _atom(self):
        t = self._eat() if self._peek()[0] else None
        if t is None:
            raise CalcError("Biểu thức chưa đầy đủ.")
        if t[0] == "num":
            return ("num", t[1])
        if t == ("op", "("):
            node = self._expr()
            if self._peek() == ("op", ")"):
                self._eat()
            return node
        if t[0] == "id":
            name = t[1]
            if name in FUNC_NAMES:
                if self._peek() == ("op", "("):
                    self._eat()
                    args = []
                    if self._peek() != ("op", ")"):
                        args.append(self._expr())
                        while self._peek() == ("op", ","):
                            self._eat()
                            args.append(self._expr())
                    if self._peek() == ("op", ")"):
                        self._eat()
                    return ("fn", name, args)
                arg = self._unary_arg()
                return ("fn", name, [arg])
            return ("var", name)
        raise CalcError(f"Không mong đợi '{t[1]}'")

    def _unary_arg(self):
        """sin30, sqrt9, ln2 ... (không ngoặc)"""
        if self._peek() == ("op", "-"):
            self._eat()
            return ("neg", self._unary_arg())
        node = self._atom()
        if self._peek() == ("op", "^"):
            self._eat()
            node = ("bin", "^", node, self._pow_operand())
        return node

    # --- tính toán
    def ev(self, node, env):
        k = node[0]
        if k == "num":
            return node[1]
        if k == "var":
            n = node[1]
            if n in env:
                return env[n]
            if n in ("Ans", "ans"):
                return self.ans
            if n in self.vars:
                return self.vars[n]
            if n in CONSTS:
                return CONSTS[n]
            raise CalcError(f"Biến '{n}' chưa có giá trị.")
        if k == "neg":
            return -self.ev(node[1], env)
        if k == "deg":
            return math.radians(self.ev(node[1], env)) if self.angle == "RAD" else self.ev(node[1], env)
        if k == "store":
            v = self.ev(node[1], env)
            self.vars[node[2]] = v
            return v
        if k == "bin":
            a, b = self.ev(node[2], env), self.ev(node[3], env)
            op = node[1]
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "/":
                if b == 0:
                    raise CalcError("Lỗi Math: chia cho 0.")
                return a / b
            if op == "^":
                return self._pow(a, b)
        if k == "fn":
            return self._fn(node[1], node[2], env)
        raise CalcError("Biểu thức không hợp lệ.")

    @staticmethod
    def _pow(a, b):
        try:
            if isinstance(a, (int, float)) and a < 0 and isinstance(b, float) and not float(b).is_integer():
                # căn bậc lẻ của số âm: (-8)^(1/3) = -2
                inv = 1 / b
                if abs(inv - round(inv)) < 1e-9 and round(inv) % 2 == 1:
                    return -((-a) ** b)
                return complex(a) ** b
            if isinstance(b, int) and b >= 0 and isinstance(a, int):
                return a ** b
            return a ** b
        except OverflowError:
            raise CalcError("Lỗi Math: số quá lớn.")
        except ZeroDivisionError:
            raise CalcError("Lỗi Math: chia cho 0.")

    def _fn(self, name, args, env):
        if name in LAZY:
            return self._lazy(name, args, env)
        v = [self.ev(a, env) for a in args]
        cx = any(isinstance(x, complex) for x in v)
        m = cmath if (cx or self.complex_mode) else math
        try:
            a = v[0] if v else 0
            if name in ("sin", "cos", "tan", "sec", "csc", "cot"):
                if cx:
                    return getattr(cmath, name if name in ("sin", "cos", "tan") else "sin")(a)
                r = self._to_rad(a)
                if name == "tan" and abs(math.cos(r)) < 1e-12:
                    raise CalcError("Lỗi Math: tan không xác định.")
                res = {"sin": math.sin, "cos": math.cos, "tan": math.tan,
                       "sec": lambda x: 1 / math.cos(x), "csc": lambda x: 1 / math.sin(x), "cot": lambda x: 1 / math.tan(x)}[name](r)
                return 0.0 if abs(res) < 1e-15 else res
            if name in ("asin", "acos", "atan"):
                if name != "atan" and not cx and abs(a) > 1:
                    raise CalcError("Lỗi Math: |x| > 1.")
                r = getattr(m, name)(a)
                return r if cx else self._from_rad(r)
            if name in ("sinh", "cosh", "tanh", "asinh", "acosh", "atanh"):
                return getattr(m, name)(a)
            if name == "ln":
                if (not cx) and a <= 0:
                    if a == 0 or not self.complex_mode:
                        raise CalcError("Lỗi Math: ln của số ≤ 0.")
                return m.log(a)
            if name == "log10":
                return m.log10(a)
            if name == "log":
                if len(v) == 2:
                    return math.log(v[1]) / math.log(v[0])
                if a <= 0:
                    raise CalcError("Lỗi Math: log của số ≤ 0.")
                return m.log10(a)
            if name == "log2":
                return math.log2(a)
            if name == "sqrt":
                return m.sqrt(a) if (a >= 0 or cx) else (cmath.sqrt(a) if self.complex_mode else self._err("Lỗi Math: căn của số âm (dùng chế độ Số phức)."))
            if name == "cbrt":
                return math.copysign(abs(a) ** (1 / 3), a)
            if name == "root":
                n, x = v[0], v[1]
                if x < 0 and int(n) % 2 == 1:
                    return -((-x) ** (1 / n))
                return x ** (1 / n)
            if name == "abs":
                return abs(a)
            if name == "exp":
                return m.exp(a)
            if name == "fact":
                if a < 0 or abs(a - round(a)) > 1e-9:
                    raise CalcError("Lỗi Math: giai thừa chỉ cho số nguyên không âm.")
                if a > 400:
                    raise CalcError("Lỗi Math: số quá lớn.")
                return math.factorial(int(round(a)))
            if name == "nCr":
                return math.comb(int(v[0]), int(v[1]))
            if name == "nPr":
                return math.perm(int(v[0]), int(v[1]))
            if name == "floor":
                return math.floor(a)
            if name == "ceil":
                return math.ceil(a)
            if name == "round":
                return round(a, int(v[1])) if len(v) > 1 else round(a)
            if name == "sign":
                return (a > 0) - (a < 0)
            if name == "gcd":
                r = int(v[0])
                for x in v[1:]:
                    r = gcd(r, int(x))
                return r
            if name == "lcm":
                r = int(v[0])
                for x in v[1:]:
                    r = r * int(x) // gcd(r, int(x))
                return r
            if name in ("mod", "rem"):
                return v[0] % v[1] if v[1] else self._err("Lỗi Math: chia cho 0.")
            if name == "pow":
                return self._pow(v[0], v[1])
            if name == "hypot":
                return math.hypot(*v)
            if name == "atan2":
                return self._from_rad(math.atan2(v[0], v[1]))
            if name == "Pol":
                return complex(math.hypot(v[0], v[1]), self._from_rad(math.atan2(v[1], v[0])))
            if name == "Rec":
                r = self._to_rad(v[1])
                return complex(v[0] * math.cos(r), v[0] * math.sin(r))
            if name == "re":
                return complex(a).real
            if name == "im":
                return complex(a).imag
            if name == "conj":
                return complex(a).conjugate()
            if name == "arg":
                return self._from_rad(cmath.phase(a))
            if name == "rand":
                return random.random()
            if name == "randint":
                return random.randint(int(v[0]), int(v[1]))
            if name == "max":
                return max(v)
            if name == "min":
                return min(v)
            if name == "deg":
                return math.degrees(a)
            if name == "rad":
                return math.radians(a)
            if name == "fib":
                x, y = 0, 1
                for _ in range(int(a)):
                    x, y = y, x + y
                return x
            if name == "isprime":
                return 1 if is_prime(int(a)) else 0
            if name == "dms":
                d = int(a)
                mi = int((a - d) * 60)
                return d + mi / 100 + ((a - d) * 60 - mi) * 60 / 10000
            if name == "normpdf":
                mu, sg = (v[1], v[2]) if len(v) >= 3 else (0, 1)
                return math.exp(-((a - mu) ** 2) / (2 * sg * sg)) / (sg * math.sqrt(2 * math.pi))
            if name == "normcdf":
                mu, sg = (v[1], v[2]) if len(v) >= 3 else (0, 1)
                return 0.5 * (1 + math.erf((a - mu) / (sg * math.sqrt(2))))
            if name == "binom":
                return math.comb(int(v[0]), int(v[1])) * v[2] ** v[1] * (1 - v[2]) ** (v[0] - v[1])
        except (ValueError, OverflowError) as exc:
            raise CalcError("Lỗi Math: " + str(exc))
        except ZeroDivisionError:
            raise CalcError("Lỗi Math: chia cho 0.")
        raise CalcError(f"Hàm '{name}' chưa hỗ trợ hoặc thiếu đối số.")

    @staticmethod
    def _err(msg):
        raise CalcError(msg)

    def _lazy(self, name, args, env):
        if name == "deriv":
            if len(args) < 2:
                raise CalcError("deriv(f(x), x0)")
            x0 = self.ev(args[1], env)
            return numeric_derivative(lambda x: self.ev(args[0], {**env, "x": x}), x0)
        if name == "integral":
            if len(args) < 3:
                raise CalcError("integral(f(x), a, b)")
            a, b = self.ev(args[1], env), self.ev(args[2], env)
            return numeric_integral(lambda x: self.ev(args[0], {**env, "x": x}), a, b)
        if name in ("sigma", "prod"):
            if len(args) < 3:
                raise CalcError(f"{name}(f(x), a, b)")
            a, b = int(self.ev(args[1], env)), int(self.ev(args[2], env))
            if b - a > 100000:
                raise CalcError("Khoảng tính quá lớn.")
            tot = 0 if name == "sigma" else 1
            for kx in range(a, b + 1):
                val = self.ev(args[0], {**env, "x": kx, "k": kx, "n": kx})
                tot = tot + val if name == "sigma" else tot * val
            return tot
        raise CalcError("Hàm không hỗ trợ.")

    def evaluate(self, text, env=None):
        t = text.strip()
        if not t:
            raise CalcError("Chưa nhập biểu thức.")
        node = self.parse(t)
        val = self.ev(node, env or {})
        if isinstance(val, complex) and abs(val.imag) < 1e-12 * max(1, abs(val.real)):
            val = val.real
        if isinstance(val, float) and val.is_integer() and abs(val) < 1e15:
            val = int(val) if abs(val) < 1e15 else val
        self.ans = val
        return val


def is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def numeric_derivative(f, x0, h=1e-5):
    d1 = (f(x0 + h) - f(x0 - h)) / (2 * h)
    h2 = h * 2
    d2 = (f(x0 + h2) - f(x0 - h2)) / (2 * h2)
    return (4 * d1 - d2) / 3


def numeric_integral(f, a, b, n=2000):
    if a == b:
        return 0.0
    if n % 2:
        n += 1
    h = (b - a) / n
    s = f(a) + f(b)
    for i in range(1, n):
        s += f(a + i * h) * (4 if i % 2 else 2)
    return s * h / 3


# ==============================================================================
# 2. ĐỊNH DẠNG KẾT QUẢ (THẬP PHÂN / PHÂN SỐ / CĂN / π)
# ==============================================================================
SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def fmt_num(x, digits=10):
    if isinstance(x, complex):
        return fmt_complex(x, digits)
    if isinstance(x, int):
        return str(x) if abs(x) < 10 ** 15 else f"{x:.{digits}g}"
    if x != x or x in (float("inf"), float("-inf")):
        return "Lỗi Math"
    if x == 0:
        return "0"
    ax = abs(x)
    if ax >= 1e15 or ax < 1e-9:
        m, e = f"{x:.{digits - 1}e}".split("e")
        m = m.rstrip("0").rstrip(".")
        return f"{m}×10{str(int(e)).translate(SUP)}"
    s = f"{x:.{digits}g}"
    if "e" in s:
        s = f"{x:.12f}".rstrip("0").rstrip(".")
    return s


def fmt_complex(z, digits=10):
    re_, im_ = z.real, z.imag
    if abs(im_) < 1e-12:
        return fmt_num(re_, digits)
    ims = fmt_num(abs(im_), digits)
    ims = "" if ims == "1" else ims
    if abs(re_) < 1e-12:
        return ("-" if im_ < 0 else "") + ims + "i"
    return f"{fmt_num(re_, digits)} {'-' if im_ < 0 else '+'} {ims}i"


def simplify_radical(n):
    """√n = k√m  với m không chứa bình phương."""
    k, m, f = 1, n, 2
    while f * f <= m:
        while m % (f * f) == 0:
            m //= f * f
            k *= f
        f += 1
    return k, m


def exact_form(x):
    """Trả về chuỗi dạng chính xác (phân số, căn, bội của π) nếu nhận ra được, ngược lại None."""
    if isinstance(x, (int, complex)) or x != x or abs(x) > 1e12 or x == 0:
        return None
    fr = Fraction(x).limit_denominator(5000)
    if abs(float(fr) - x) < 1e-12 * max(1, abs(x)) and fr.denominator != 1:
        return frac_str(fr)
    # bội của π
    r = x / math.pi
    fr = Fraction(r).limit_denominator(360)
    if fr != 0 and abs(float(fr) - r) < 1e-10 and fr.denominator <= 360:
        num = "π" if abs(fr.numerator) == 1 else f"{abs(fr.numerator)}π"
        s = ("-" if fr < 0 else "") + num
        return s if fr.denominator == 1 else f"{s}/{fr.denominator}"
    # căn:  x = p/q * √m
    sq = x * x
    fr2 = Fraction(sq).limit_denominator(2000)
    if abs(float(fr2) - sq) < 1e-9 * max(1, sq) and fr2 > 0:
        num, den = fr2.numerator, fr2.denominator
        k1, m1 = simplify_radical(num)
        k2, m2 = simplify_radical(den)
        # √(num/den) = √(num*den)/den
        k, m = simplify_radical(num * den)
        if m == 1:
            return None
        coef = Fraction(k, den)
        sgn = "-" if x < 0 else ""
        c = "" if coef.numerator == 1 else str(coef.numerator)
        rad = f"{c}√{m}"
        return f"{sgn}{rad}" if coef.denominator == 1 else f"{sgn}{rad}/{coef.denominator}"
    return None


def frac_str(fr):
    fr = Fraction(fr)
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


def mixed_str(fr):
    fr = Fraction(fr)
    if abs(fr.numerator) > fr.denominator > 1:
        w = int(fr)
        rest = abs(fr) - abs(w)
        return f"{w} {rest.numerator}/{rest.denominator}"
    return frac_str(fr)


def to_dms(x):
    sgn = "-" if x < 0 else ""
    x = abs(x)
    d = int(x)
    m = int((x - d) * 60)
    s = ((x - d) * 60 - m) * 60
    return f"{sgn}{d}°{m}′{s:.2f}″"


# ==============================================================================
# 3. ĐA THỨC, PHƯƠNG TRÌNH
# ==============================================================================
def poly_roots(coefs, iters=500):
    """Nghiệm phức của đa thức (hệ số từ bậc cao xuống thấp) bằng Durand-Kerner + làm mịn Newton."""
    c = list(coefs)
    while c and abs(c[0]) < 1e-15:
        c.pop(0)
    n = len(c) - 1
    if n < 1:
        return []
    c = [x / c[0] for x in c]
    r = 1 + max(abs(x) for x in c[1:])
    roots = [complex(r * 0.7, 0.1) ** k * 0.9 + 0.01j * k for k in range(n)]
    roots = [r * 0.5 * cmath.exp(2j * math.pi * (k + 0.25) / n) for k in range(n)]

    def p(z):
        v = 0
        for a in c:
            v = v * z + a
        return v
    for _ in range(iters):
        delta = 0
        for i in range(n):
            den = 1
            for j in range(n):
                if i != j:
                    den *= (roots[i] - roots[j])
            if den == 0:
                den = 1e-12
            d = p(roots[i]) / den
            roots[i] -= d
            delta = max(delta, abs(d))
        if delta < 1e-14:
            break
    # Newton làm mịn
    dc = [c[k] * (n - k) for k in range(n)]
    for i in range(n):
        for _ in range(5):
            dv = 0
            for a in dc:
                dv = dv * roots[i] + a
            if dv == 0:
                break
            roots[i] -= p(roots[i]) / dv
    out = []
    for z in roots:
        if abs(z.imag) < 1e-9 * max(1, abs(z.real)):
            z = complex(z.real, 0)
        if abs(z.real) < 1e-12:
            z = complex(0, z.imag)
        out.append(z)
    return sorted(out, key=lambda z: (round(z.real, 9), round(z.imag, 9)))


def _fr(x):
    """Cố gắng chuyển về Fraction nếu x là số hữu tỉ 'đẹp'."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    f = Fraction(x).limit_denominator(10000)
    return f if abs(float(f) - x) < 1e-12 else None


def solve_quadratic(a, b, c):
    steps = []
    if a == 0:
        return solve_linear(b, c)
    steps.append("Phương trình: " + poly_str([a, b, c]) + " = 0")
    d = b * b - 4 * a * c
    steps.append(f"Δ = b² − 4ac = {fmt_num(b)}² − 4·{fmt_num(a)}·{fmt_num(c)} = {fmt_num(d)}")
    res = []
    fa, fb, fc = _fr(a), _fr(b), _fr(c)
    rat = fa is not None and fb is not None and fc is not None
    if d > 1e-15:
        steps.append("Δ > 0 ⇒ phương trình có 2 nghiệm thực phân biệt")
        x1, x2 = (-b + math.sqrt(d)) / (2 * a), (-b - math.sqrt(d)) / (2 * a)
        if rat:
            D = fb * fb - 4 * fa * fc
            k, m = simplify_radical_frac(D)
            if m == 1:
                e1, e2 = frac_str((-fb + k) / (2 * fa)), frac_str((-fb - k) / (2 * fa))
            else:
                e1 = rad_root_str(fb, k, m, fa, +1)
                e2 = rad_root_str(fb, k, m, fa, -1)
            res += [f"x₁ = {e1}" + ("" if m == 1 else f" ≈ {fmt_num(x1)}"), f"x₂ = {e2}" + ("" if m == 1 else f" ≈ {fmt_num(x2)}")]
        else:
            res += [f"x₁ = {fmt_num(x1)}", f"x₂ = {fmt_num(x2)}"]
    elif abs(d) <= 1e-15:
        steps.append("Δ = 0 ⇒ nghiệm kép")
        x = -b / (2 * a)
        res.append(f"x₁ = x₂ = {fmt_num(x)}" + (f" = {frac_str(_fr(x))}" if _fr(x) is not None and _fr(x).denominator != 1 else ""))
    else:
        steps.append("Δ < 0 ⇒ không có nghiệm thực; có 2 nghiệm phức liên hợp")
        z = complex(-b / (2 * a), math.sqrt(-d) / (2 * a))
        res += [f"x₁ = {fmt_complex(z)}", f"x₂ = {fmt_complex(z.conjugate())}"]
    if d >= 0:
        s1 = -b / a
        p1 = c / a
        steps.append(f"Vi-ét: x₁ + x₂ = −b/a = {fmt_num(s1)};  x₁·x₂ = c/a = {fmt_num(p1)}")
    xv = -b / (2 * a)
    yv = a * xv * xv + b * xv + c
    steps.append(f"Đỉnh parabol: I({fmt_num(xv)}; {fmt_num(yv)})")
    return steps, res


def simplify_radical_frac(D):
    """√D với D là Fraction >= 0: trả (k, m) với √D = k√m, k Fraction."""
    num, den = D.numerator, D.denominator
    k, m = simplify_radical(num * den)
    return Fraction(k, den), m


def rad_root_str(b, k, m, a, sign):
    """x = (-b ± k√m)/(2a)  ->  '(−1 + √5)/2' dạng gọn."""
    L, K, D = Fraction(-b), Fraction(k) * sign, Fraction(2 * a)
    if D < 0:
        L, K, D = -L, -K, -D
    lcm = 1
    for f in (L, K, D):
        lcm = lcm * f.denominator // gcd(lcm, f.denominator)
    Li, Ki, Di = int(L * lcm), int(K * lcm), int(D * lcm)
    g = gcd(gcd(abs(Li), abs(Ki)), abs(Di)) or 1
    Li, Ki, Di = Li // g, Ki // g, Di // g
    kt = f"{'' if abs(Ki) == 1 else abs(Ki)}√{m}"
    if Li == 0:
        num = ("−" if Ki < 0 else "") + kt
    else:
        num = f"{str(Li).replace('-', '−')} {'−' if Ki < 0 else '+'} {kt}"
    if Di == 1:
        return num if Li == 0 else f"{num}"
    return (f"{num}/{Di}" if Li == 0 else f"({num})/{Di}")


def solve_linear(a, b):
    if a == 0:
        return ["Phương trình: " + poly_str([a, b]) + " = 0"], ["Vô nghiệm" if b != 0 else "Vô số nghiệm"]
    x = -b / a
    ex = exact_form(x)
    return ["Phương trình: " + poly_str([a, b]) + " = 0", f"x = −b/a = {fmt_num(-b)}/{fmt_num(a)}"], [f"x = {fmt_num(x)}" + (f" = {ex}" if ex else "")]


def solve_poly(coefs):
    roots = poly_roots(coefs)
    deg = len(coefs) - 1
    steps = [f"Đa thức bậc {deg}: " + poly_str(coefs) + " = 0"]
    res = []
    for k, z in enumerate(roots, 1):
        res.append(f"x{_sub(k)} = {fmt_complex(z)}")
    return steps, res


def _sub(n):
    return str(n).translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉"))


def poly_str(coefs):
    n = len(coefs) - 1
    parts = []
    for i, c in enumerate(coefs):
        p = n - i
        if abs(c) < 1e-15:
            continue
        cs = fmt_num(abs(c))
        if cs == "1" and p > 0:
            cs = ""
        mon = "" if p == 0 else ("x" if p == 1 else "x" + str(p).translate(SUP))
        sgn = "−" if c < 0 else "+"
        parts.append((sgn, cs + mon if (cs + mon) else "1"))
    if not parts:
        return "0"
    s = ("−" if parts[0][0] == "−" else "") + parts[0][1]
    for sg, t in parts[1:]:
        s += f" {sg} {t}"
    return s


def solve_system(A, b):
    """Giải hệ Ax=b bằng Fraction (nếu được) — trả (nghiệm, ghi chú)."""
    n = len(A)
    try:
        M = [[Fraction(x).limit_denominator(10 ** 6) if not isinstance(x, Fraction) else x for x in row] + [Fraction(bv).limit_denominator(10 ** 6)] for row, bv in zip(A, b)]
    except Exception:
        M = [[Fraction(x) for x in row] + [Fraction(bv)] for row, bv in zip(A, b)]
    rank = 0
    piv = []
    for c in range(n):
        p = next((r for r in range(rank, n) if M[r][c] != 0), None)
        if p is None:
            continue
        M[rank], M[p] = M[p], M[rank]
        pv = M[rank][c]
        M[rank] = [x / pv for x in M[rank]]
        for r in range(n):
            if r != rank and M[r][c] != 0:
                f = M[r][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[rank])]
        piv.append(c)
        rank += 1
    for r in range(rank, n):
        if M[r][n] != 0:
            return None, "Hệ vô nghiệm"
    if rank < n:
        return None, "Hệ có vô số nghiệm"
    return [M[i][n] for i in range(n)], ""


def solve_ineq_poly(coefs, op):
    """Giải bất phương trình đa thức > < >= <= 0 → khoảng nghiệm thực."""
    roots = sorted({round(z.real, 9) for z in poly_roots(coefs) if abs(z.imag) < 1e-9})
    f = lambda x: sum(c * x ** (len(coefs) - 1 - i) for i, c in enumerate(coefs))  # noqa: E731
    pts = [-1e9] + roots + [1e9]
    strict = op in (">", "<")
    want_pos = op in (">", ">=")
    intervals = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        mid = (a + b) / 2 if i not in (0, len(pts) - 2) else (b - 1 if i == 0 else a + 1)
        if i == 0:
            mid = b - 1
        elif i == len(pts) - 2:
            mid = a + 1
        v = f(mid)
        if (v > 0) == want_pos and abs(v) > 1e-12:
            intervals.append((a, b))
    inc_roots = [] if strict else [r for r in roots if not any(abs(r - x) < 1e-9 or abs(r - y) < 1e-9 for x, y in intervals)]
    # gộp khoảng liền kề
    merged = []
    for a, b in intervals:
        if merged and abs(merged[-1][1] - a) < 1e-9 and not strict:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))

    def ends(a, b):
        l = "(−∞" if a <= -1e8 else (("(" if strict else "[") + fmt_num(a))
        r = "+∞)" if b >= 1e8 else (fmt_num(b) + (")" if strict else "]"))
        return f"{l}; {r}"
    parts = [ends(a, b) for a, b in merged] + [f"{{{fmt_num(r)}}}" for r in inc_roots]
    return ("S = " + " ∪ ".join(parts)) if parts else "S = ∅ (vô nghiệm)", roots


def solve_newton(f, x0, tol=1e-12, it=200):
    x = x0
    for _ in range(it):
        fx = f(x)
        h = 1e-7 * max(1, abs(x))
        d = (f(x + h) - f(x - h)) / (2 * h)
        if d == 0:
            x += 1e-3
            continue
        nx = x - fx / d
        if abs(nx - x) < tol:
            return nx
        x = nx
    raise CalcError("SOLVE không hội tụ — hãy thử giá trị đầu khác.")


# ==============================================================================
# 4. THỐNG KÊ, PHÂN PHỐI
# ==============================================================================
def parse_numbers(text):
    c = Calc()
    out = []
    for tok in re.split(r"[;\s,]+", text.strip()):
        if tok:
            out.append(float(c.evaluate(tok)))
    return out


def quantile(sorted_vals, q):
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = q * (n + 1) - 1  # phương pháp trung vị theo SGK Việt Nam: chia đôi
    lo = sorted_vals
    half = n // 2
    med = (lo[half] if n % 2 else (lo[half - 1] + lo[half]) / 2)
    if q == 0.5:
        return med
    lower = lo[:half]
    upper = lo[half + (n % 2):]
    part = lower if q < 0.5 else upper
    if not part:
        return med
    m = len(part)
    return part[m // 2] if m % 2 else (part[m // 2 - 1] + part[m // 2]) / 2


def stats_1var(xs, freqs=None):
    if freqs is None:
        freqs = [1] * len(xs)
    if len(freqs) != len(xs):
        raise CalcError("Số tần số phải bằng số giá trị.")
    n = sum(freqs)
    if n <= 0:
        raise CalcError("Tổng tần số phải dương.")
    sx = sum(x * f for x, f in zip(xs, freqs))
    sx2 = sum(x * x * f for x, f in zip(xs, freqs))
    mean = sx / n
    var_p = sx2 / n - mean ** 2
    var_p = max(var_p, 0)
    var_s = var_p * n / (n - 1) if n > 1 else float("nan")
    expanded = sorted(x for x, f in zip(xs, freqs) for _ in range(int(f)))
    cnt = {}
    for x, f in zip(xs, freqs):
        cnt[x] = cnt.get(x, 0) + f
    mx = max(cnt.values())
    modes = sorted(k for k, v in cnt.items() if v == mx)
    res = {"n": n, "Σx": sx, "Σx²": sx2, "x̄ (trung bình)": mean, "σx (độ lệch chuẩn tổng thể)": math.sqrt(var_p),
           "sx (độ lệch chuẩn mẫu)": math.sqrt(var_s) if n > 1 else float("nan"), "σ² (phương sai)": var_p,
           "Giá trị nhỏ nhất": min(xs), "Q₁": quantile(expanded, 0.25), "Trung vị (Med)": quantile(expanded, 0.5),
           "Q₃": quantile(expanded, 0.75), "Giá trị lớn nhất": max(xs), "Khoảng biến thiên": max(xs) - min(xs),
           "Khoảng tứ phân vị": quantile(expanded, 0.75) - quantile(expanded, 0.25),
           "Mốt (Mode)": ", ".join(fmt_num(m) for m in modes) if mx > 1 or len(modes) < len(xs) else "không có"}
    return res


def regression(xs, ys, kind="lin"):
    n = len(xs)
    if n != len(ys) or n < 2:
        raise CalcError("Cần ít nhất 2 cặp (x, y) với số lượng bằng nhau.")
    tx, ty = xs[:], ys[:]
    if kind == "exp":
        if any(y <= 0 for y in ys):
            raise CalcError("Hồi quy mũ cần y > 0.")
        ty = [math.log(y) for y in ys]
    elif kind == "log":
        if any(x <= 0 for x in xs):
            raise CalcError("Hồi quy lôgarit cần x > 0.")
        tx = [math.log(x) for x in xs]
    elif kind == "pow":
        if any(x <= 0 for x in xs) or any(y <= 0 for y in ys):
            raise CalcError("Hồi quy lũy thừa cần x, y > 0.")
        tx, ty = [math.log(x) for x in xs], [math.log(y) for y in ys]
    elif kind == "inv":
        if any(x == 0 for x in xs):
            raise CalcError("Hồi quy nghịch đảo cần x ≠ 0.")
        tx = [1 / x for x in xs]
    elif kind == "quad":
        if n < 3:
            raise CalcError("Hồi quy bậc 2 cần ít nhất 3 điểm.")
        S = lambda p: sum(x ** p for x in xs)  # noqa: E731
        T = lambda p: sum(y * x ** p for x, y in zip(xs, ys))  # noqa: E731
        sol, msg = solve_system([[S(4), S(3), S(2)], [S(3), S(2), S(1)], [S(2), S(1), n]], [T(2), T(1), T(0)])
        if sol is None:
            raise CalcError(msg)
        a, b, c = map(float, sol)
        ym = sum(ys) / n
        ssr = sum((y - (a * x * x + b * x + c)) ** 2 for x, y in zip(xs, ys))
        sst = sum((y - ym) ** 2 for y in ys)
        r2 = 1 - ssr / sst if sst else 1.0
        return {"a": a, "b": b, "c": c, "R²": r2, "eq": f"y = {fmt_num(a)}x² + {fmt_num(b)}x + {fmt_num(c)}", "pred": lambda x: a * x * x + b * x + c}
    mx, my = sum(tx) / n, sum(ty) / n
    sxx = sum((x - mx) ** 2 for x in tx)
    sxy = sum((x - mx) * (y - my) for x, y in zip(tx, ty))
    syy = sum((y - my) ** 2 for y in ty)
    if sxx == 0:
        raise CalcError("Các giá trị x đều bằng nhau - không hồi quy được.")
    B = sxy / sxx
    A = my - B * mx
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else 1.0
    if kind == "lin":
        return {"a": A, "b": B, "r": r, "eq": f"y = {fmt_num(A)} + {fmt_num(B)}x", "pred": lambda x: A + B * x, "inv": lambda y: (y - A) / B}
    if kind == "exp":
        a, b = math.exp(A), math.exp(B)
        return {"a": a, "b": b, "r": r, "eq": f"y = {fmt_num(a)}·{fmt_num(b)}ˣ", "pred": lambda x: a * b ** x}
    if kind == "log":
        return {"a": A, "b": B, "r": r, "eq": f"y = {fmt_num(A)} + {fmt_num(B)}·ln x", "pred": lambda x: A + B * math.log(x)}
    if kind == "pow":
        a = math.exp(A)
        return {"a": a, "b": B, "r": r, "eq": f"y = {fmt_num(a)}·x^{fmt_num(B)}", "pred": lambda x: a * x ** B}
    return {"a": A, "b": B, "r": r, "eq": f"y = {fmt_num(A)} + {fmt_num(B)}/x", "pred": lambda x: A + B / x}


def norm_cdf(x, mu=0.0, sg=1.0):
    return 0.5 * (1 + math.erf((x - mu) / (sg * math.sqrt(2))))


def norm_inv(p, mu=0.0, sg=1.0):
    if not 0 < p < 1:
        raise CalcError("Xác suất phải nằm trong (0; 1).")
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return mu + sg * (lo + hi) / 2


# ==============================================================================
# 5. MA TRẬN, VECTƠ
# ==============================================================================
def parse_matrix(text):
    rows = [r for r in re.split(r"[;\n]+", text.strip()) if r.strip()]
    if not rows:
        raise CalcError("Ma trận trống. Nhập mỗi hàng cách nhau bằng dấu ; (VD: 1 2; 3 4).")
    c = Calc()
    M = []
    for r in rows:
        M.append([Fraction(c.evaluate(t)).limit_denominator(10 ** 6) if not isinstance(c.evaluate(t), complex) else c.evaluate(t)
                  for t in re.split(r"[\s,]+", r.strip()) if t])
    w = len(M[0])
    if any(len(r) != w for r in M):
        raise CalcError("Các hàng của ma trận phải có cùng số phần tử.")
    return M


def mat_str(M, pad=True):
    cells = [[frac_str(x) if isinstance(x, Fraction) else fmt_num(x) for x in r] for r in M]
    w = max(len(x) for r in cells for x in r)
    return "\n".join("│ " + "  ".join(x.rjust(w) for x in r) + " │" for r in cells)


def mat_mul(A, B):
    if len(A[0]) != len(B):
        raise CalcError(f"Không nhân được: A là {len(A)}×{len(A[0])}, B là {len(B)}×{len(B[0])}.")
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]


def mat_det(M):
    n = len(M)
    if n != len(M[0]):
        raise CalcError("Định thức chỉ tính cho ma trận vuông.")
    A = [r[:] for r in M]
    det = Fraction(1) if isinstance(A[0][0], Fraction) else 1
    for c in range(n):
        p = next((r for r in range(c, n) if A[r][c] != 0), None)
        if p is None:
            return 0
        if p != c:
            A[c], A[p] = A[p], A[c]
            det = -det
        det *= A[c][c]
        for r in range(c + 1, n):
            f = A[r][c] / A[c][c]
            A[r] = [x - f * y for x, y in zip(A[r], A[c])]
    return det


def mat_inv(M):
    n = len(M)
    if n != len(M[0]):
        raise CalcError("Chỉ nghịch đảo được ma trận vuông.")
    A = [list(r) + [Fraction(int(i == j)) for j in range(n)] for i, r in enumerate(M)]
    for c in range(n):
        p = next((r for r in range(c, n) if A[r][c] != 0), None)
        if p is None:
            raise CalcError("Ma trận suy biến (det = 0) — không có ma trận nghịch đảo.")
        A[c], A[p] = A[p], A[c]
        pv = A[c][c]
        A[c] = [x / pv for x in A[c]]
        for r in range(n):
            if r != c and A[r][c] != 0:
                f = A[r][c]
                A[r] = [x - f * y for x, y in zip(A[r], A[c])]
    return [r[n:] for r in A]


def mat_rank(M):
    A = [r[:] for r in M]
    rank, rows, cols = 0, len(A), len(A[0])
    for c in range(cols):
        p = next((r for r in range(rank, rows) if A[r][c] != 0), None)
        if p is None:
            continue
        A[rank], A[p] = A[p], A[rank]
        for r in range(rank + 1, rows):
            f = A[r][c] / A[rank][c]
            A[r] = [x - f * y for x, y in zip(A[r], A[rank])]
        rank += 1
    return rank


def mat_T(M):
    return [list(r) for r in zip(*M)]


def mat_pow(M, k):
    n = len(M)
    R = [[Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    if k < 0:
        M, k = mat_inv(M), -k
    for _ in range(k):
        R = mat_mul(R, M)
    return R


def mat_eigen(M):
    n = len(M)
    if n != len(M[0]) or n > 5:
        raise CalcError("Trị riêng: ma trận vuông cỡ ≤ 5.")
    # đa thức đặc trưng bằng Faddeev-LeVerrier
    A = [[float(x) for x in r] for r in M]
    I = [[float(i == j) for j in range(n)] for i in range(n)]
    c = [1.0]
    Mk = [[0.0] * n for _ in range(n)]
    for k in range(1, n + 1):
        Mk = [[sum(A[i][t] * Mk[t][j] for t in range(n)) + c[-1] * I[i][j] for j in range(n)] for i in range(n)]
        AM = [[sum(A[i][t] * Mk[t][j] for t in range(n)) for j in range(n)] for i in range(n)]
        c.append(-sum(AM[i][i] for i in range(n)) / k)
    return c, poly_roots(c)


def parse_vec(text):
    c = Calc()
    v = [float(c.evaluate(t)) for t in re.split(r"[\s,;]+", text.strip()) if t]
    if len(v) not in (2, 3):
        raise CalcError("Vectơ cần 2 hoặc 3 thành phần.")
    return v


# ==============================================================================
# 6. HỆ CƠ SỐ, SỐ HỌC
# ==============================================================================
def to_base(n, b):
    digits = "0123456789ABCDEF"
    if n == 0:
        return "0"
    s, neg = "", n < 0
    n = abs(n)
    while n:
        s = digits[n % b] + s
        n //= b
    return ("-" if neg else "") + s


def prime_factors(n):
    n = abs(int(n))
    if n < 2:
        raise CalcError("Chỉ phân tích số nguyên ≥ 2.")
    f, d, out = {}, 2, n
    while d * d <= out:
        while out % d == 0:
            f[d] = f.get(d, 0) + 1
            out //= d
        d += 1 if d == 2 else 2
        if d > 3_000_000:
            raise CalcError("Số quá lớn để phân tích.")
    if out > 1:
        f[out] = f.get(out, 0) + 1
    return f


def divisors(n):
    n = abs(int(n))
    ds = set()
    i = 1
    while i * i <= n:
        if n % i == 0:
            ds.add(i)
            ds.add(n // i)
        i += 1
    return sorted(ds)


UNITS = {
    "Độ dài": {"m": 1, "km": 1000, "cm": 0.01, "mm": 0.001, "μm": 1e-6, "nm": 1e-9, "inch": 0.0254, "ft": 0.3048, "yd": 0.9144, "mile": 1609.344, "hải lý": 1852, "năm ánh sáng": 9.4607e15, "AU": 1.495978707e11},
    "Khối lượng": {"kg": 1, "g": 0.001, "mg": 1e-6, "tấn": 1000, "tạ": 100, "yến": 10, "lb": 0.45359237, "oz": 0.028349523, "u (amu)": 1.66053907e-27},
    "Diện tích": {"m²": 1, "km²": 1e6, "cm²": 1e-4, "ha": 1e4, "sào Bắc Bộ": 360, "mẫu": 1e4, "acre": 4046.8564, "ft²": 0.09290304},
    "Thể tích": {"lít": 1, "mL": 0.001, "m³": 1000, "cm³": 0.001, "gallon (US)": 3.785411784, "pint (US)": 0.473176473},
    "Thời gian": {"giây": 1, "phút": 60, "giờ": 3600, "ngày": 86400, "tuần": 604800, "năm": 31556952, "ms": 0.001},
    "Vận tốc": {"m/s": 1, "km/h": 1 / 3.6, "mph": 0.44704, "knot": 0.514444, "c (ánh sáng)": 299792458},
    "Áp suất": {"Pa": 1, "kPa": 1000, "atm": 101325, "bar": 1e5, "mmHg": 133.322, "torr": 133.322, "psi": 6894.757},
    "Năng lượng": {"J": 1, "kJ": 1000, "cal": 4.184, "kcal": 4184, "eV": 1.602176634e-19, "kWh": 3.6e6, "BTU": 1055.056},
    "Công suất": {"W": 1, "kW": 1000, "mã lực (HP)": 745.7, "BTU/h": 0.29307},
    "Dữ liệu": {"bit": 1, "byte": 8, "KB": 8e3, "MB": 8e6, "GB": 8e9, "TB": 8e12, "KiB": 8192, "MiB": 8388608, "GiB": 8589934592},
    "Góc": {"độ": 1, "rad": 180 / math.pi, "grad": 0.9, "vòng": 360, "phút (′)": 1 / 60, "giây (″)": 1 / 3600},
}


def convert_unit(cat, val, u_from, u_to):
    if cat == "Nhiệt độ":
        to_c = {"°C": lambda x: x, "°F": lambda x: (x - 32) * 5 / 9, "K": lambda x: x - 273.15}
        from_c = {"°C": lambda x: x, "°F": lambda x: x * 9 / 5 + 32, "K": lambda x: x + 273.15}
        return from_c[u_to](to_c[u_from](val))
    return val * UNITS[cat][u_from] / UNITS[cat][u_to]


PHYS_CONSTS = [
    ("Tốc độ ánh sáng c", 299792458, "m/s"), ("Hằng số hấp dẫn G", 6.6743e-11, "m³/(kg·s²)"), ("Gia tốc trọng trường g", 9.80665, "m/s²"),
    ("Hằng số Planck h", 6.62607015e-34, "J·s"), ("Planck rút gọn ħ", 1.054571817e-34, "J·s"), ("Điện tích nguyên tố e", 1.602176634e-19, "C"),
    ("Khối lượng electron mₑ", 9.1093837015e-31, "kg"), ("Khối lượng proton mₚ", 1.67262192369e-27, "kg"), ("Khối lượng neutron mₙ", 1.67492749804e-27, "kg"),
    ("Hằng số Avogadro Nₐ", 6.02214076e23, "mol⁻¹"), ("Hằng số Boltzmann k", 1.380649e-23, "J/K"), ("Hằng số khí R", 8.314462618, "J/(mol·K)"),
    ("Hằng số Faraday F", 96485.33212, "C/mol"), ("Hằng số Coulomb kₑ", 8.9875517923e9, "N·m²/C²"), ("Hằng số điện ε₀", 8.8541878128e-12, "F/m"),
    ("Hằng số từ μ₀", 1.25663706212e-6, "N/A²"), ("Hằng số Stefan–Boltzmann σ", 5.670374419e-8, "W/(m²·K⁴)"), ("Hằng số Rydberg R∞", 10973731.568160, "m⁻¹"),
    ("Bán kính Bohr a₀", 5.29177210903e-11, "m"), ("Hằng số cấu trúc tinh tế α", 7.2973525693e-3, ""), ("Đơn vị khối lượng nguyên tử u", 1.66053906660e-27, "kg"),
    ("Thể tích mol khí (đktc)", 22.41396954, "L/mol"), ("Khí quyển chuẩn atm", 101325, "Pa"), ("Hằng số Wien b", 2.897771955e-3, "m·K"),
    ("Khối lượng Trái Đất", 5.9722e24, "kg"), ("Bán kính Trái Đất", 6.371e6, "m"), ("Khối lượng Mặt Trời", 1.98847e30, "kg"),
    ("Khoảng cách Trái Đất - Mặt Trời (AU)", 1.495978707e11, "m"), ("Khối lượng Mặt Trăng", 7.342e22, "kg"), ("Nhiệt dung riêng của nước", 4186, "J/(kg·K)"),
    ("Nhiệt nóng chảy của nước đá", 3.34e5, "J/kg"), ("Nhiệt hóa hơi của nước", 2.26e6, "J/kg"), ("Khối lượng riêng của nước", 1000, "kg/m³"),
    ("Tốc độ âm thanh (20 °C)", 343, "m/s"), ("Hằng số Euler–Mascheroni γ", 0.5772156649, ""), ("Tỉ số vàng φ", (1 + 5 ** 0.5) / 2, ""),
    ("Năng lượng 1 u", 931.49410242, "MeV"), ("Eletron-vôn eV", 1.602176634e-19, "J"), ("Từ tử Bohr μB", 9.2740100783e-24, "J/T"),
]
