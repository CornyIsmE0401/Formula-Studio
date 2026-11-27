# -*- coding: utf-8 -*-
"""i18n.py - Hệ thống đa ngôn ngữ song song (Tiếng Việt ⇄ English) chuyển tức thì <20ms,
giữ nguyên khóa nội bộ của mọi QComboBox và khôi phục 100% không mất dữ liệu khi đổi qua lại."""
import re

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QRadioButton, QTabWidget, QWidget,
)

_LANG = "vi"


def get_lang() -> str:
    return _LANG


def is_en() -> bool:
    return _LANG == "en"


def set_lang(lang: str):
    global _LANG
    _LANG = "en" if str(lang).lower().startswith("en") else "vi"


# Các từ/ký hiệu toán-hóa & tiền tố hóa học GIỮ NGUYÊN kiểu viết khi định dạng Title Case
_PRESERVE_WORDS = {
    "pH", "pOH", "pKa", "pKb", "Ka", "Kb", "Kw", "Kc", "Kp", "Ksp",
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan",
    "ln", "lg", "log", "lim", "exp", "sqrt", "det", "rank", "tr", "mod", "inf",
    "rad", "deg", "mol", "mL", "g/mol", "px", "pt", "mm", "cm", "km", "nm", "bar", "atm",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "k", "l", "m", "n", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "dx", "dy", "dt", "fx", "xy", "xyz", "abc",
    "tert", "sec", "iso", "neo", "cis", "trans", "ortho", "meta", "para", "alpha", "beta", "gamma", "delta",
    "and", "or", "of", "in", "to", "at", "on", "for", "via", "by", "the", "with", "from", "a", "an",
}
_CHEM_PREFIX_RE = re.compile(r"^(?:n|s|t|o|m|p|sec|tert|iso|neo|cis|trans|dl|α|β|γ|δ)-", re.IGNORECASE)
_HAS_UPPER_INNER_RE = re.compile(r"[A-Z]")
_TOKEN_SPLIT_RE = re.compile(r"(\s+|[()\[\]{},;:/+·•—–-]+)")


def smart_title(text: str) -> str:
    """Định dạng Viết Hoa Chữ Cái Đầu (Title Case) lịch sự & chuyên nghiệp cho tiêu đề, tab,
    drop-down, tên hình học, công thức mẫu và tên chất — giữ nguyên ký hiệu Toán/Hóa học."""
    if not text:
        return text
    parts = _TOKEN_SPLIT_RE.split(text)
    out = []
    first_word = True
    for tok in parts:
        if not tok or _TOKEN_SPLIT_RE.fullmatch(tok):
            out.append(tok)
            continue
        # Giữ nguyên nếu chứa chữ số, dấu toán học, tiền tố hóa học (n-Propyl, tert-Butyl...) hoặc chữ hoa nội tại (LaTeX, NaOH, S.ABC)
        if (
            tok in _PRESERVE_WORDS and not (first_word and tok in ("của", "và", "từ"))
        ) or any(ch.isdigit() or ch in "=^_°×÷<>|±∓∑∫√∞αβγδεθλμπσφωΔΣΠ" for ch in tok):
            out.append(tok)
        elif _CHEM_PREFIX_RE.match(tok):
            out.append(tok)
        elif len(tok) > 1 and _HAS_UPPER_INNER_RE.search(tok[1:]):
            out.append(tok)
        elif tok[0].isalpha():
            out.append(tok[0].upper() + tok[1:])
        else:
            out.append(tok)
        first_word = False
    return "".join(out)


_CALC_PHRASES = [
    ("Phương trình bậc nhất ax + b = 0", "Linear Equation ax + b = 0"),
    ("Phương trình bậc hai ax² + bx + c = 0", "Quadratic Equation ax² + bx + c = 0"),
    ("Phương trình bậc ", "Polynomial Equation of Degree "),
    ("Bất phương trình bậc ", "Polynomial Inequality of Degree "),
    ("Đạo hàm của ", "Derivative of "),
    ("Tích phân xác định", "Definite Integral"),
    ("Phân phối chuẩn N(μ, σ²)", "Normal Distribution N(μ, σ²)"),
    ("Phân phối nhị thức", "Binomial Distribution"),
    ("Phân phối Poisson", "Poisson Distribution"),
    ("Giá trị tới hạn (InvN)", "Inverse Normal Quantile (InvN)"),
    ("Thống kê 1 biến", "1-Variable Statistics"),
    ("Giải tam giác ABC", "Triangle Solver (ABC)"),
    ("Đường thẳng qua 2 điểm", "Line Through 2 Points"),
    ("Đường tròn qua 3 điểm", "Circle Through 3 Points"),
    ("Đổi đơn vị — ", "Unit Converter — "),
    ("Ma trận — ", "Matrix — "),
    ("Định thức det(A)", "Determinant det(A)"),
    ("Nghịch đảo A⁻¹", "Inverse A⁻¹"),
    ("Chuyển vị Aᵀ", "Transpose Aᵀ"),
    ("Hạng rank(A)", "Rank rank(A)"),
    ("Vết tr(A)", "Trace tr(A)"),
    ("Trị riêng của A", "Eigenvalues of A"),
    ("Tính pH dung dịch — ", "Solution pH — "),
    ("Pha loãng dung dịch (C₁V₁ = C₂V₂)", "Solution Dilution (C₁V₁ = C₂V₂)"),
    ("Có thể nhập biểu thức:", "Tip: enter expressions like"),
    ("Độ dài", "Length"),
    ("Khối lượng", "Mass"),
    ("Nhiệt độ", "Temperature"),
    ("Diện tích", "Area"),
    ("Thể tích", "Volume"),
    ("Thời gian", "Time"),
    ("Vận tốc", "Speed"),
    ("Áp suất", "Pressure"),
    ("Năng lượng", "Energy"),
    ("Công suất", "Power"),
    ("Góc", "Angle"),
    ("Dữ liệu", "Data"),
    ("trung bình", "mean"),
    ("độ lệch chuẩn tổng thể", "population std dev"),
    ("độ lệch chuẩn mẫu", "sample std dev"),
    ("phương sai tổng thể", "population variance"),
    ("phương sai mẫu", "sample variance"),
    ("trung vị", "median"),
    ("Khoảng tứ phân vị", "IQR (interquartile)"),
    ("Mốt (Mode)", "Mode      "),
    ("tứ phân vị", "quartile"),
    ("tổng", "sum"),
    ("nhỏ nhất", "min"),
    ("lớn nhất", "max"),
    ("cỡ mẫu", "sample size"),
    ("tại x =", "at x ="),
    ("Môi trường:", "Medium:"),
    ("Trung tính", "Neutral"),
    ("Nghiệm duy nhất:", "Unique root:"),
    ("Phương trình có 2 nghiệm phân biệt", "Two distinct real roots"),
    ("Phương trình có nghiệm kép", "Repeated real root"),
    ("Phương trình vô nghiệm thực", "No real roots"),
    ("Vô nghiệm", "No solution"),
    ("Vô số nghiệm", "Infinitely many solutions"),
    ("Thể tích sau pha loãng:", "Final volume:"),
    ("Lượng nước cần thêm:", "Water to add:"),
    ("Đường chéo", "Diagonal"),
    ("Tâm", "Center"),
    ("Chu vi", "Perimeter"),
    ("Chuyển vế:", "Rearrange:"),
    ("Chia hai vế cho", "Divide both sides by"),
    ("Thay vào công thức", "Substitute into formula"),
    ("Xấp xỉ sai phân trung tâm", "Central difference approximation"),
    ("Nhập a = -1e9 để tính P(X < b); b = 1e9 để tính P(X > a).", "Tip: set a = -1e9 for P(X < b), or b = 1e9 for P(X > a)."),
    ("Ô 1, 2, 3 lần lượt là các đại lượng theo thứ tự trong ngoặc.", "Params 1, 2, 3 correspond to the variables shown in parentheses."),
    ("Dạng lượng giác:", "Polar form:"),
    ("Dạng mũ:", "Exponential form:"),
    ("Căn bậc ", "Root #"),
    ("Hình chiếu của a lên b =", "Projection of a onto b ="),
    ("Diện tích hình bình hành =", "Parallelogram area ="),
    ("Diện tích tam giác =", "Triangle area ="),
    ("Góc (a, b) =", "Angle (a, b) ="),
    ("Phương trình:", "Equation:"),
    ("Đạo hàm số (sai phân trung tâm, ngoại suy Richardson)", "Numerical derivative (central difference, Richardson extrapolation)"),
    ("(phương sai)", "(variance)"),
    ("Định lí hàm số cos:", "Law of Cosines:"),
    ("Đơn vị có sẵn:", "Available units:"),
    ("hải lý", "nmi"),
    ("năm ánh sáng", "ly"),
    ("Tiếp tuyến:", "Tangent line:"),
    ("Giá trị min", "Min value  "),
    ("Giá trị max", "Max value  "),
    ("Khoảng biến thiên", "Range            "),
    ("Tứ phân vị", "Quartile  "),
    ("Trung vị", "Median  "),
    ("Tổng bình phương", "Sum of squares  "),
    ("Tổng", "Sum "),
    ("(ngoại tiếp)", "(circumradius)"),
    ("(nội tiếp)", "(inradius)"),
    ("Đường cao", "Altitudes"),
    ("Trung tuyến", "Medians"),
    # --- Đầy đủ lời giải từng bước & hằng số của 43 bộ giải Máy tính
    ("phương trình có 2 nghiệm thực phân biệt", "two distinct real roots"),
    ("Nghiệm tính số (độ chính xác ~10⁻¹⁰); nghiệm phức hiển thị dạng a + bi.", "Numerical roots (precision ~10⁻¹⁰); complex roots shown as a + bi."),
    ("Khử Gauss–Jordan trên phân số", "Gauss–Jordan elimination over exact fractions"),
    ("Hệ:", "System:"),
    ("Vi-ét:", "Vieta:"),
    ("Đỉnh parabol:", "Parabola vertex:"),
    ("Bình phương liên tiếp (square-and-multiply)", "Binary exponentiation (square-and-multiply)"),
    ("Bảng giá trị", "Value Table"),
    ("CALC: thay giá trị biến", "CALC: Substitute Variables"),
    ("Chia thử cho các số nguyên tố", "Trial division by prime numbers"),
    ("Các ước:", "Divisors:"),
    ("cặp (x; y)", "data pairs (x, y)"),
    ("Dự đoán", "Predicted"),
    ("Giải phương trình bậc 2:", "Solve quadratic equation:"),
    ("Giới hạn của", "Limit of"),
    ("Hoán vị lặp:", "Permutations with repetition:"),
    ("Hệ số góc", "Slope"),
    ("Hệ số tương quan", "Correlation coefficient"),
    ("Hỗn số:", "Mixed number:"),
    ("Lãi kép:", "Compound interest:"),
    ("Lãi đơn:", "Simple interest:"),
    ("Nhập số thập phân hoặc tiền tố 0b (nhị phân), 0x (hex), 0o (bát phân)", "Enter decimal or prefix 0b (binary), 0x (hex), 0o (octal)"),
    ("Phân số tối giản:", "Reduced fraction:"),
    ("Phân số ⇄ số thập phân", "Fraction ⇄ Decimal"),
    ("Phân tích ra thừa số nguyên tố", "Prime Factorization"),
    ("Phép chia có dư", "Euclidean Division"),
    ("Phép toán logic bit", "Bitwise Logic Operations"),
    ("Phương pháp Newton–Raphson từ nhiều điểm xuất phát", "Newton–Raphson method from multiple starting points"),
    ("Phương pháp bình phương tối thiểu", "Ordinary least squares regression"),
    ("Phần trăm:", "Percentage:"),
    ("Quy tắc Simpson với 4000 khoảng chia", "Composite Simpson's rule (4,000 intervals)"),
    ("Acid yếu (C, Ka)", "Weak Acid (C, Ka)"),
    ("Acid mạnh (H⁺)", "Strong Acid (H⁺)"),
    ("Base yếu (C, Kb)", "Weak Base (C, Kb)"),
    ("Base mạnh (OH⁻)", "Strong Base (OH⁻)"),
    ("Số tiền trả đều mỗi kỳ:", "Equal payment per period:"),
    ("Thuật toán Euclid", "Euclidean algorithm"),
    ("Thương =", "Quotient ="),
    ("Dư =", "Remainder ="),
    ("Thập phân:", "Decimal:"),
    ("Trung điểm", "Midpoint"),
    ("Trả góp đều:", "Amortized loan payment:"),
    ("Tài chính cơ bản", "Financial Math"),
    ("Tìm nghiệm thực của đa thức:", "Real roots of polynomial:"),
    ("Tìm x sao cho", "Find x such that"),
    ("Tích có hướng:", "Cross product:"),
    ("Tính giá trị tiến gần về điểm cần tìm giới hạn từ hai phía", "Evaluate left- and right-hand approaches near the limit point"),
    ("Tỉ lệ", "Proportion"),
    ("Tổ hợp – Chỉnh hợp – Hoán vị", "Combinations · Permutations"),
    ("Xét dấu đa thức trên từng khoảng", "Sign analysis across real intervals"),
    ("Áp dụng định luật bảo toàn số mol chất tan:", "Apply solute mole conservation:"),
    ("Đường thẳng AB:", "Line AB:"),
    ("Đường trung trực:", "Perpendicular bisector:"),
    ("Đổi hệ cơ số", "Base-N Conversion"),
    ("ƯCLN và BCNN", "GCD and LCM"),
    ("ƯCLN =", "GCD ="),
    ("BCNN =", "LCM ="),
    ("hình bình hành", "Parallelogram"),
    ("tam giác", "Triangle"),
    ("sau pha loãng:", "after dilution:"),
    # --- Hằng số vật lí
    ("Bán kính Bohr", "Bohr radius"),
    ("Bán kính Trái Đất", "Earth radius"),
    ("Eletron-vôn", "Electronvolt"),
    ("Gia tốc trọng trường", "Standard gravity"),
    ("Hằng số Avogadro", "Avogadro constant"),
    ("Hằng số Boltzmann", "Boltzmann constant"),
    ("Hằng số Coulomb", "Coulomb constant"),
    ("Hằng số Euler–Mascheroni", "Euler–Mascheroni constant"),
    ("Hằng số Faraday", "Faraday constant"),
    ("Hằng số Planck", "Planck constant"),
    ("Hằng số Rydberg", "Rydberg constant"),
    ("Hằng số Stefan–Boltzmann", "Stefan–Boltzmann constant"),
    ("Hằng số Wien", "Wien displacement constant"),
    ("Hằng số cấu trúc tinh tế", "Fine-structure constant"),
    ("Hằng số hấp dẫn", "Gravitational constant"),
    ("Hằng số khí", "Ideal gas constant"),
    ("Hằng số từ", "Vacuum permeability"),
    ("Hằng số điện", "Vacuum permittivity"),
    ("Khoảng cách Trái Đất - Mặt Trời", "Astronomical unit"),
    ("Khí quyển chuẩn", "Standard atmosphere"),
    ("Mặt Trăng", "of the Moon"),
    ("Mặt Trời", "of the Sun"),
    ("Trái Đất", "of Earth"),
    ("Nhiệt dung riêng của nước", "Specific heat of water"),
    ("Nhiệt hóa hơi của nước", "Latent heat of vaporization (water)"),
    ("Nhiệt nóng chảy của nước đá", "Latent heat of fusion (ice)"),
    ("riêng của nước", "density of water"),
    ("Planck rút gọn", "Reduced Planck constant"),
    ("Tỉ số vàng", "Golden ratio"),
    ("Tốc độ ánh sáng", "Speed of light"),
    ("Tốc độ âm thanh", "Speed of sound"),
    ("Từ tử Bohr", "Bohr magneton"),
    ("mol khí (đktc)", "molar gas volume (STP)"),
    ("Điện tích nguyên tố", "Elementary charge"),
    ("Đơn vị khối lượng nguyên tử", "Atomic mass unit"),
    (" và tích Π ", " & Product Π "),
    (" với x từ ", " for x from "),
    (" từ ", " from "),
    (" đến ", " to "),
    ("của", "of"),
]

_CALC_REGEX = [
    (re.compile(r"Hệ (\d+) phương trình (\d+) ẩn"), r"System of \1 Linear Equations (\2 Variables)"),
    (re.compile(r"Định thức D = ([^≠]+) ≠ 0 ⇒ hệ có nghiệm duy nhất"), r"Determinant D = \1 ≠ 0 ⇒ unique solution"),
    (re.compile(r"Đa thức bậc (\d+):"), r"Degree-\1 polynomial:"),
    (re.compile(r"(\S+) giảm (\S+)% ="), r"\1 decreased by \2% ="),
    (re.compile(r"(\S+) tăng (\S+)% ="), r"\1 increased by \2% ="),
    (re.compile(r"(\S+) là bao nhiêu % của (\S+):"), r"\1 as a % of \2:"),
    (re.compile(r"Có (\d+) ước"), r"\1 divisors"),
    (re.compile(r"Chuyển (\S+) \(cơ số (\d+)\) sang thập phân:"), r"Convert \1 (base \2) to decimal:"),
]


def tr_calc_text(s: str) -> str:
    """Dịch các tiêu đề/bước giải/nhãn thống kê của Máy tính khoa học sang tiếng Anh khi LANG=='en'."""
    if not s or _LANG != "en":
        return s
    out = VI_TO_EN.get(s, s)
    for rx, rep in _CALC_REGEX:
        out = rx.sub(rep, out)
    for src, dst in _CALC_PHRASES:
        if src in out:
            out = out.replace(src, dst)
    return out


# ==============================================================================
# TỪ ĐIỂN ÁNH XẠ CHÍNH XÁC TIẾNG VIỆT → ENGLISH (TOÀN BỘ GIAO DIỆN FORMULA STUDIO)
# ==============================================================================
VI_TO_EN = {
    # --- Sidebar & Điều hướng chính
    "KHÔNG GIAN LÀM VIỆC": "WORKSPACES",
    "TIỆN ÍCH NHANH": "QUICK UTILITIES",
    "Toán học · Hình học": "Math · Geometry",
    "Hóa học · Phân tử": "Chemistry · Molecules",
    "Máy tính khoa học": "Scientific Calculator",
    "Cài đặt · Hướng dẫn": "Settings · Guide",
    "  Toán học · Hình học": "  Math · Geometry",
    "  Hóa học · Phân tử": "  Chemistry · Molecules",
    "  Máy tính khoa học": "  Scientific Calculator",
    "  Cài đặt · Hướng dẫn": "  Settings · Guide",
    "  Giao diện sáng": "  Light Mode",
    "  Giao diện tối": "  Dark Mode",
    "Chuyển Sáng / Tối (Ctrl+D)": "Toggle Light / Dark (Ctrl+D)",
    "Chuyển sang Giao diện sáng (Ctrl+D)": "Switch to Light Mode (Ctrl+D)",
    "Chuyển sang Giao diện tối (Ctrl+D)": "Switch to Dark Mode (Ctrl+D)",
    "Thu gọn / mở rộng thanh bên (Ctrl+B)": "Collapse / expand sidebar (Ctrl+B)",
    "Gom công thức, hình đã thêm rồi xuất .docx hoặc chèn vào Word": "Collect formulas/figures to export .docx or insert into Word",

    # --- Tabs chính
    "Công thức Toán (LaTeX)": "Math Formulas (LaTeX)",
    "Hình học động · Đồ thị": "Dynamic Geometry · Graphs",
    "Phương trình · Cân bằng": "Equations · Balancer",
    "Cấu trúc SMILES": "SMILES Structure",
    "Trình vẽ phân tử": "Molecule Sketcher",
    "Bảng tuần hoàn 118": "Periodic Table 118",
    "Cài đặt": "Settings",
    "Hướng dẫn trực quan": "Interactive Guide",
    "Giới thiệu": "About",
    "Gần đây": "Recent",
    "Yêu thích": "Favorites",

    # --- Nút thao tác chung
    "Sao chép": "Copy",
    "Sao chép ảnh": "Copy Image",
    "Quét ảnh": "Scan OCR",
    "Lưu mẫu": "Save",
    "Xóa": "Clear",
    "Đặt lại": "Reset",
    "Tính": "Evaluate",
    "Ghi mã": "Apply",
    "Mở": "Open",
    "Lưu": "Save",
    "Đóng": "Close",
    "Nạp": "Load",
    "Vẽ": "Plot",
    "Đo": "Measure",
    "Ẩn / Hiện": "Show / Hide",
    "Xóa đồ thị": "Delete Graph",
    "Khác…": "More…",
    "Hiện": "Show",
    "Ẩn": "Hide",
    "Lưu khóa": "Save Key",
    "Mở tính năng →": "Open Feature →",
    "Chuẩn hóa": "Clean 2D",
    "Vừa hình": "Fit View",
    "Gốc O": "Origin O",
    "Phân tích": "Analyze",
    "Mở SMILES": "Open SMILES",
    "Mở Trình vẽ": "Open Sketcher",
    "Copy CT": "Copy Formula",
    "Phát âm IUPAC": "IUPAC Audio",
    "Nghe phát âm IUPAC": "Play IUPAC Audio",
    "Xuất ảnh bảng": "Export Table PNG",
    "Sao chép Bohr": "Copy Bohr",
    "Sao chép orbital": "Copy Orbitals",
    "Tải SVG": "Save SVG",
    "Cân bằng": "Balance",
    "Tính g/mol": "Compute M",
    "Cân bằng khung soạn": "Balance Editor",
    "Hóa trị · Tính tan": "Valence · Solubility",
    "Đánh dấu sao": "Bookmark",
    "Đã đánh dấu": "Bookmarked",
    "Tất cả": "All",
    "Tất cả phản ứng": "All Reactions",
    "Tất cả nhóm chất": "All Groups",
    "Tất cả khung mẫu": "All Templates",
    "— Tìm nhanh trong 43 bộ giải —": "— Quick Find Across 43 Solvers —",
    "Tam giác + Đường tròn nội tiếp": "Triangle + Incircle",
    "Hình bình hành + Hai đường chéo": "Parallelogram + Diagonals",
    "Hình thoi + Hai đường chéo": "Rhombus + Diagonals",
    "Lăng trụ đứng tứ giác ABCD.A'B'C'D'": "Quadrilateral Prism ABCD.A'B'C'D'",

    # --- Cài đặt & Ngôn ngữ & Chủ đề
    "NGÔN NGỮ HIỂN THỊ (LANGUAGE)": "DISPLAY LANGUAGE",
    "Chọn ngôn ngữ giao diện ứng dụng (áp dụng tức thì)": "Choose application interface language (applies instantly)",
    "GIAO DIỆN & CHỦ ĐỀ MÀU SẮC": "APPEARANCE & STUDIO THEMES",
    "Chọn chủ đề giao diện (chuyển tức thì, đồng bộ thanh tiêu đề Windows)": "Pick a studio theme (instant switch, synced with Windows title bar)",
    "Màu nhấn chủ đạo (Accent Color)": "Accent Color",
    "CỬA SỔ & KHAY HỆ THỐNG": "WINDOW & SYSTEM TRAY",
    "Hiện biểu tượng Formula Studio ở khay hệ thống (System Tray)": "Show Formula Studio icon in System Tray",
    "Hành động khi nhấn nút đóng cửa sổ (X):": "Action when clicking Close (X):",
    "Hỏi mỗi lần": "Ask every time",
    "Thu nhỏ xuống khay hệ thống (ứng dụng vẫn chạy nền)": "Minimize to system tray (keep running in background)",
    "Thoát hẳn ứng dụng": "Quit application completely",
    "QUÉT ẢNH CÔNG THỨC (OCR)": "FORMULA IMAGE OCR",
    "Dán khóa Gemini API (tạo miễn phí tại aistudio.google.com/apikey) để dùng nút «Quét ảnh» ở các trang Toán, Phương trình hóa học và SMILES. Khóa chỉ lưu cục bộ trên máy này.": "Paste a free Gemini API key (aistudio.google.com/apikey) to enable 'Scan OCR' on Math, Chemical Equations, and SMILES tabs. Stored locally only.",
    "Đã cấu hình": "Configured",
    "Chưa nhập khóa": "Not set",
    "DANH MỤC TÍNH NĂNG": "FEATURE DIRECTORY",
    "MÔI TRƯỜNG & THƯ VIỆN HỆ THỐNG": "SYSTEM ENVIRONMENT & LIBRARIES",
    "  Studio Sáng\n  Nền trắng thanh lịch, sắc nét": "  Studio Light\n  Clean bright theme for documents",
    "  Midnight Pro\n  Nền tối sâu, dịu mắt ban đêm": "  Midnight Pro\n  Deep obsidian dark for night work",
    "  Nordic Frost\n  Xám lam dịu nhẹ cho học tập lâu": "  Nordic Frost\n  Calm slate-blue for long sessions",
    "  Warm Paper\n  Giấy kem ấm bảo vệ mắt": "  Warm Paper\n  Warm academic paper for eye comfort",
    "(g) khí": "(g) gas",
    "(l) lỏng": "(l) liquid",
    "(s) rắn": "(s) solid",
    "H₂SO₄ đặc": "Conc. H₂SO₄",
    "Nhiệt t°": "Heat t°",
    "Xúc tác xt": "Catalyst",
    "Ánh sáng": "Light (hν)",
    "Điện phân dd": "Electrolysis (aq)",
    "Điện phân nc": "Electrolysis (l)",
    "●  Chàm": "●  Indigo",
    "●  Lam": "●  Blue",
    "●  Xanh biển": "●  Sky",
    "●  Ngọc": "●  Teal",
    "●  Lục": "●  Emerald",
    "●  Cam": "●  Orange",
    "●  Hồng": "●  Rose",
    "●  Tím": "●  Violet",

    # --- Giới thiệu (About)
    "Hợp chất chuẩn IUPAC": "IUPAC Compounds",
    "Vô cơ, hữu cơ, dược phẩm, amino acid": "Inorganic, organic, pharmaceuticals, amino acids",
    "Phản ứng cân bằng": "Balanced Reactions",
    "Đầy đủ điều kiện & kiểm chứng tự động": "Full reaction conditions & auto-verified",
    "Công thức Toán · Lí · Hóa": "Math · Physics · Chem Formulas",
    "Thay số trực tiếp & xuất Word equation": "Live variable substitution & Word Equations",
    "Nguyên tố hóa học": "Chemical Elements",
    "Bohr, ô orbital ↑↓ & phát âm IPA chuẩn": "Bohr model, orbital boxes ↑↓ & IPA audio",
    "Cấu trúc 2D SMILES": "2D SMILES Structures",
    "Vẽ lập thể nêm đặc/đứt, xuất PNG & SVG": "Wedge/dash stereochemistry, PNG & SVG export",
    "Bộ giải Máy tính": "Calculator Solvers",
    "Phương trình, tích phân, ma trận, pH…": "Equations, integrals, matrices, pH…",
    "Toán học & Hình học động": "Mathematics & Dynamic Geometry",
    "Soạn công thức LaTeX kèm thay số & tính kết quả nhanh; bảng dựng hình động với 24 hình mẫu 2D/3D, đồ thị dò tọa độ tức thời và ký hiệu góc vuông chuẩn.": "WYSIWYG & LaTeX formula authoring with quick substitution; GeoGebra-style geometry with 24 2D/3D figures, interactive graphing, and draggable labels.",
    "Hóa học chuẩn danh pháp IUPAC": "IUPAC-Standard Chemistry Suite",
    "Chuẩn hóa tên gốc quốc tế cho toàn bộ 118 nguyên tố & 705 hợp chất; trình vẽ phân tử 3 cột kiểu ChemDraw với phím tắt đổi nguyên tố và liên kết nêm lập thể.": "International IUPAC nomenclature across all 118 elements & 705 compounds; 3-column ChemDraw-style sketcher with element hotkeys & stereobonds.",
    "Máy tính khoa học hiện đại": "Modern Scientific Calculator",
    "Hiển thị phân số/căn/mũ tự nhiên kiểu Casio fx-580VN X, lưu biến nhớ A/B/Ans trực quan và tìm nhanh 43 công cụ giải toán/hóa kèm lời giải từng bước.": "Natural textbook display (fractions, roots, powers), visual A/B/Ans memory, and 43 step-by-step math & chemistry solvers.",
    "Xuất Microsoft Word & Đồ họa": "Microsoft Word & Vector Export",
    "Chèn trực tiếp công thức thành Equation gốc của Word (.docx) hoặc xuất ảnh PNG độ phân giải cao (300 DPI) và vector SVG không vỡ nét.": "Insert native editable Microsoft Word Equations (.docx) or export crisp 300 DPI PNG and scalable SVG graphics.",
    "PySide6 · Sẵn sàng": "PySide6 · Ready",
    "Matplotlib · Sẵn sàng": "Matplotlib · Ready",
    "RDKit · Có": "RDKit · Installed",
    "RDKit · Tích hợp sẵn": "RDKit · Built-in Engine",
    "Offline OCR · Sẵn sàng": "Offline OCR · Ready",
    "Offline OCR · Dùng Gemini OCR": "Offline OCR · Using Gemini OCR",

    # --- Trang Công thức Toán
    "Trực quan": "Visual",
    "Mã LaTeX": "LaTeX Code",
    "Thay số nhanh": "Quick Substitute",
    "Cỡ:": "Size:",
    "Cỡ nhỏ": "Inline",
    "XEM TRƯỚC TRỰC TIẾP": "LIVE PREVIEW",
    "/ phân số · ^ mũ · _ chỉ số · Tab": "/ fraction · ^ power · _ subscript · Tab",
    "Hỗ trợ mọi cú pháp LaTeX": "Supports full LaTeX syntax",
    "Ma trận/hệ nhiều dòng → Mã LaTeX": "Matrix / multiline → LaTeX Code",
    "Công thức nâng cao → Mã LaTeX": "Advanced formula → LaTeX Code",
    "Ẩn": "Hide",
    "Lọc các chất đã đánh dấu sao": "Filter bookmarked compounds",
    "Lọc các chất đã đánh dấu sao để học sinh ôn tập": "Filter bookmarked compounds",
    "Đánh dấu sao để lưu chất này vào danh sách tự học": "Bookmark this compound for quick access",
    "Đánh dấu sao để lưu chất này vào danh sách đã lưu": "Bookmark this compound for quick access",
    "Đen": "Black",
    "Trắng": "White",
    "Xanh dương": "Blue",
    "Đỏ": "Red",
    "Lục": "Green",
    "Nền Trong suốt": "Transparent",
    "Nền Trắng": "White",
    "Nền Tối": "Dark",
    "{ hệ": "{ sys",
    "số…": "num…",
    "Sao chép kết quả": "Copy Result",
    "VD: aspirin, CH3COOH · CH3CH(OH)CH3 · aspirin · paracetamol · vanilin · c1ccccc1": "e.g. CH3COOH · CH3CH(OH)CH3 · aspirin · paracetamol · vanillin · c1ccccc1",
    "VD: CH3COOH · CH3CH(OH)CH3 · aspirin · paracetamol · vanilin · c1ccccc1": "e.g. CH3COOH · CH3CH(OH)CH3 · aspirin · paracetamol · vanillin · c1ccccc1",
    "VD: Fe + O2 -> Fe3O4   |   KMnO4 + HCl -> KCl + MnCl2 + Cl2 + H2O   |   Fe^{2+} + MnO4^- + H^+ -> Fe^{3+} + Mn^{2+} + H2O": "e.g. Fe + O2 -> Fe3O4  |  KMnO4 + HCl -> KCl + MnCl2 + Cl2 + H2O  |  Fe^{2+} + MnO4^- + H^+ -> Fe^{3+} + Mn^{2+} + H2O",
    "VD: CuSO4.5H2O, Ca(OH)2, Al2(SO4)3, KAl(SO4)2.12H2O": "e.g. CuSO4.5H2O, Ca(OH)2, Al2(SO4)3, KAl(SO4)2.12H2O",
    r"Nhập mã LaTeX, VD: \int_0^1 x^2\,dx = \frac{1}{3}": r"Enter LaTeX, e.g. \int_0^1 x^2\,dx = \frac{1}{3}",

    # --- Nhãn & tùy chọn cho toàn bộ 43 bộ giải Máy tính
    "A (độ)": "A (deg)",
    "B (độ)": "B (deg)",
    "C (độ)": "C (deg)",
    "Biểu thức": "Expression",
    "Bước": "Step",
    "Các số": "Numbers",
    "Căn bậc n (tùy chọn)": "nth root (optional)",
    "Cơ số của số nhập": "Input Number Base",
    "Cận dưới a": "Lower bound a",
    "Cận trên b": "Upper bound b",
    "Dãy x": "x values",
    "Dãy y": "y values",
    "Dạng hồi quy": "Regression Model",
    "Dấu": "Operator",
    "Dự đoán tại x =": "Predict at x =",
    "Giá trị": "Values",
    "Giá trị a": "Value a",
    "Giá trị đầu": "Initial guess",
    "Gán (x=2; y=3)": "Assign (x=2; y=3)",
    "Hình": "Solid Shape",
    "Hệ 2 phương trình": "2-Variable System",
    "Hệ 3 phương trình": "3-Variable System",
    "Hệ 4 phương trình": "4-Variable System",
    "Hệ số (cao → thấp)": "Coefficients (high → low)",
    "Hệ số đa thức (cao → thấp)": "Polynomial coeff. (high → low)",
    "Ka hoặc Kb (nếu yếu)": "Ka or Kb (if weak)",
    "Loại": "Category",
    "Loại dung dịch": "Solution Type",
    "Lãi suất mỗi kỳ (%)": "Rate per period (%)",
    "Lọc theo tên (để trống = tất cả)": "Filter by name (empty = all)",
    "Ma trận A": "Matrix A",
    "Ma trận B / mũ n": "Matrix B / power n",
    "Nồng độ C (M)": "Concentration C (M)",
    "Nồng độ ban đầu C₁": "Initial conc. C₁",
    "Nồng độ cần pha C₂": "Target conc. C₂",
    "Phép toán": "Operation",
    "Phần trăm b": "Percent b",
    "Sang đơn vị": "To unit",
    "Số": "Number",
    "Số bị chia": "Dividend",
    "Số chia": "Divisor",
    "Số kỳ n": "Periods n",
    "Số lượng": "Count",
    "Số nguyên": "Integer",
    "Thể tích ban đầu V₁ (mL)": "Initial volume V₁ (mL)",
    "Tần số (tùy chọn)": "Frequencies (optional)",
    "Từ": "From",
    "Từ đơn vị": "From unit",
    "Vectơ a (2–3 thành phần)": "Vector a (2D or 3D)",
    "Vectơ b": "Vector b",
    "Vốn P": "Principal P",
    "f(x) (biến x)": "f(x) (var x)",
    "x → (số hoặc inf)": "x → (number or inf)",
    "z / biểu thức": "z / expression",
    "Ô 1": "Param 1",
    "Ô 2": "Param 2",
    "Ô 3": "Param 3",
    "Điểm P (tùy chọn: x y)": "Point P (optional: x y)",
    "Đến": "To",
    "Acid mạnh (H⁺)": "Strong Acid (H⁺)",
    "Acid yếu (C, Ka)": "Weak Acid (C, Ka)",
    "Base mạnh (OH⁻)": "Strong Base (OH⁻)",
    "Base yếu (C, Kb)": "Weak Base (C, Kb)",
    "Aⁿ (n nhập ở ô B)": "Aⁿ (enter n in B)",
    "Bát phân (OCT)": "Octal (OCT)",
    "Nhị phân (BIN)": "Binary (BIN)",
    "Thập phân (DEC)": "Decimal (DEC)",
    "Thập lục phân (HEX)": "Hexadecimal (HEX)",
    "Chuyển vị Aᵀ": "Transpose Aᵀ",
    "Hạng rank(A)": "Rank rank(A)",
    "Nghịch đảo A⁻¹": "Inverse A⁻¹",
    "Trị riêng của A": "Eigenvalues of A",
    "Vết tr(A)": "Trace tr(A)",
    "Định thức det(A)": "Determinant det(A)",
    "Tuyến tính (y = a + bx)": "Linear (y = a + bx)",
    "Bậc 2 (y = ax² + bx + c)": "Quadratic (y = ax² + bx + c)",
    "Mũ (y = a·bˣ)": "Exponential (y = a·bˣ)",
    "Lôgarit (y = a + b·ln x)": "Logarithmic (y = a + b·ln x)",
    "Lũy thừa (y = a·xᵇ)": "Power (y = a·xᵇ)",
    "Nghịch đảo (y = a + b/x)": "Inverse (y = a + b/x)",
    "Hình cầu (R)": "Sphere (R)",
    "Hình trụ (R, h)": "Cylinder (R, h)",
    "Hình nón (R, h)": "Cone (R, h)",
    "Hình hộp chữ nhật (a, b, c)": "Rectangular Box (a, b, c)",
    "Hình lập phương (a)": "Cube (a)",
    "Hình chóp (S đáy, h)": "Pyramid (Base S, h)",
    "Hình nón cụt (R, r, h)": "Cone Frustum (R, r, h)",
    "Lăng trụ (S đáy, h)": "Prism (Base S, h)",
    "Độ dài": "Length",
    "Khối lượng": "Mass",
    "Nhiệt độ": "Temperature",
    "Diện tích": "Area",
    "Thể tích": "Volume",
    "Thời gian": "Time",
    "Vận tốc": "Speed",
    "Áp suất": "Pressure",
    "Năng lượng": "Energy",
    "Công suất": "Power",
    "Góc": "Angle",
    "Dữ liệu": "Data",
    "· (ngậm nước)": "· (hydrate)",
    "Số mũ n": "Exponent n",
    "cách nhau bằng dấu cách / ; /,": "separated by spaces / ; / ,",
    "để trống = mỗi giá trị 1 lần": "leave empty = frequency 1 each",
    "bỏ trống nếu chưa biết": "leave empty if unknown",
    "Hệ thống này không hỗ trợ khay hệ thống; nút đóng sẽ thoát ứng dụng.": "System tray is unavailable on this OS; closing the window will quit the app.",
    "Chọn / Di chuyển (V) — kéo điểm để di chuyển · kéo vùng trống để cuộn · cuộn chuột để thu phóng": "Select / Move (V) — drag points, labels, or notes · drag empty area to pan · scroll to zoom",
    "Mẹo: kéo điểm/nhãn/chú thích để bố trí đẹp · cuộn chuột thu phóng 1%–1250%": "Tip: drag points, labels & notes to arrange cleanly · scroll to zoom 1%–1250%",
    "Khung mẫu": "Templates",
    "Cơ bản": "Basic",
    "Hàm số": "Functions",
    "Hy Lạp": "Greek",
    "Tập hợp": "Sets",
    "Hình học": "Geometry",
    "Tìm công thức: tên, chuyên đề, LaTeX… (VD: tích phân, đạo hàm, hình cầu, Fourier, pH)": "Search formulas: name, topic, LaTeX… (e.g. integral, derivative, sphere, Fourier, pH)",
    "Đại số": "Algebra",
    "Giải tích": "Calculus",
    "Xác suất": "Probability",
    "Ứng dụng": "Applied",
    "Lượng giác": "Trigonometry",
    "Dãy số": "Sequences",
    "Mũ - Lôgarit": "Exp & Log",
    "Hình không gian": "3D Geometry",
    "Tọa độ": "Coordinates",
    "Vectơ": "Vectors",
    "Tổ hợp - Xác suất": "Combinatorics & Prob.",
    "Số phức": "Complex Numbers",
    "Đại số tuyến tính": "Linear Algebra",
    "Vật lí": "Physics",
    "Hóa học": "Chemistry",
    "Giải tích nâng cao": "Advanced Calculus",
    "Số học - Rời rạc": "Number Theory & Discrete",

    # --- Trang Hình học động
    "CƠ BẢN": "BASIC",
    "DỰNG HÌNH": "CONSTRUCT",
    "TÂM TAM GIÁC": "TRIANGLE CENTERS",
    "KHÁC": "OTHER",
    "Chọn": "Select",
    "• Điểm": "• Point",
    "╱ Đoạn": "╱ Segment",
    "↔ Đường": "↔ Line",
    "↗ Tia": "↗ Ray",
    "→ Vectơ": "→ Vector",
    "◯ Tròn": "◯ Circle",
    "◎ 3 điểm": "◎ 3-pt Circ",
    "⬠ Đa giác": "⬠ Polygon",
    "∠ Góc": "∠ Angle",
    "M Tr.điểm": "M Midpoint",
    "⟂M Tr.trực": "⟂M Perp Bis",
    "⊥ Vuông": "⊥ Perp",
    "∥ S.song": "∥ Parallel",
    "∠/ P.giác": "∠/ Bisector",
    "H Chân vg": "H Foot",
    "× Giao": "× Intersect",
    "⊘ Tiếp t.": "⊘ Tangent",
    "⇄ ĐX trục": "⇄ Reflect",
    "◎ ĐX tâm": "◎ Pt Sym",
    "G Trọng t.": "G Centroid",
    "O Ngoại t.": "O Circum",
    "I Nội tiếp": "I Incenter",
    "H₀ Trực t.": "H₀ Ortho",
    "T Chú thích": "T Text Note",
    "✕ Xóa": "✕ Erase",
    "ĐỒ THỊ  y = f(x)": "GRAPH  y = f(x)",
    "VD: x^2 - 2x - 3 | sin(x)": "e.g. x^2 - 2x - 3 | sin(x)",
    "Parabol": "Parabola",
    "Bậc 3": "Cubic",
    "— chọn hình để chèn —": "— insert a preset figure —",
    "KIỂU NÉT & MÀU": "STROKE & COLOR",
    "Nét đứt": "Dashed",
    "Dày:": "Width:",
    "HIỂN THỊ": "DISPLAY",
    "Lưới tọa độ": "Coordinate grid",
    "Trục Ox, Oy": "Ox, Oy axes",
    "Tên điểm": "Point labels",
    "Hiện số đo (dài, góc, S)": "Show measurements (L, ∠, S)",
    "Tô màu đa giác": "Fill polygons",
    "Bắt điểm vào lưới": "Snap to grid",
    "Mẹo: ở chế độ Chọn có thể kéo điểm, kéo tên điểm (A, B…), số đo góc/cạnh và chú thích · nhấp đúp để đổi tên/nội dung": "Tip: In Select mode, drag points, point labels (A, B…), measurements & notes · double-click to edit",
    "Tam giác thường": "Scalene Triangle",
    "Tam giác vuông": "Right Triangle",
    "Tam giác cân": "Isosceles Triangle",
    "Tam giác đều": "Equilateral Triangle",
    "Tam giác + Đường tròn ngoại tiếp": "Triangle + Circumcircle",
    "Tam giác + 3 đường cao (Trực tâm)": "Triangle + 3 Altitudes (Orthocenter)",
    "Hình chữ nhật": "Rectangle",
    "Hình vuông": "Square",
    "Hình bình hành": "Parallelogram",
    "Hình thang": "Trapezoid",
    "Hình thang cân": "Isosceles Trapezoid",
    "Hình thang vuông": "Right Trapezoid",
    "Hình thoi": "Rhombus",
    "Ngũ giác đều": "Regular Pentagon",
    "Lục giác đều": "Regular Hexagon",
    "Tứ diện đều S.ABC": "Regular Tetrahedron S.ABC",
    "Hình chóp tam giác S.ABC": "Triangular Pyramid S.ABC",
    "Hình chóp tứ giác S.ABCD": "Square Pyramid S.ABCD",
    "Hình chóp cụt tứ giác": "Frustum of Pyramid",
    "Hình lăng trụ tam giác ABC.A'B'C'": "Triangular Prism ABC.A'B'C'",
    "Hình hộp chữ nhật ABCD.A'B'C'D'": "Rectangular Box ABCD.A'B'C'D'",
    "Hình lập phương ABCD.A'B'C'D'": "Cube ABCD.A'B'C'D'",
    "Hình trụ (mô phỏng 3D)": "Cylinder (3D Projection)",
    "Hình nón (mô phỏng 3D)": "Cone (3D Projection)",

    # --- Hóa học: Phương trình, SMILES, Sketcher, Bảng tuần hoàn, Tra cứu
    "Cân bằng:": "Balance:",
    "Tính khối lượng mol M:": "Molar Mass M:",
    "MÃ HÓA HỌC (MHCHEM)": "CHEMICAL EQUATION (MHCHEM)",
    "Phản ứng": "Reactions",
    "Chỉ số": "Subscripts",
    "Điện tích": "Charges",
    "Trạng thái": "States",
    "Điều kiện": "Conditions",
    "Tìm phản ứng: tên, chất, công thức… (VD: aspirin, KMnO4, điện phân, xanh Phổ)": "Search reactions: name, species, formula… (e.g. aspirin, KMnO4, electrolysis)",
    "TÊN CHẤT · CÔNG THỨC · SMILES": "NAME · FORMULA · SMILES",
    "CẤU TRÚC 2D CHUẨN HÓA TRỊ": "2D VALENCE-CHECKED STRUCTURE",
    "Màu nguyên tố": "Element Colors",
    "Đơn sắc": "Monochrome",
    "— chọn chất —": "— Pick Compound —",
    "— Chọn Chất —": "— Pick Compound —",
    "THAO TÁC": "ACTIONS",
    "Di chuyển": "Pan View",
    "Tích +": "Charge +",
    "Tích −": "Charge −",
    "LIÊN KẾT": "BONDS",
    "─ Đơn": "─ Single",
    "═ Đôi": "═ Double",
    "≡ Ba": "≡ Triple",
    "▸ Nêm": "▸ Wedge",
    "┄ Đứt": "┄ Dash",
    "NGUYÊN TỐ": "ELEMENTS",
    "+ Nguyên tố khác…": "+ Other Element…",
    "VÒNG NHANH": "QUICK RINGS",
    "C₆ no": "C₆ Sat.",
    "C₅ đôi": "C₅ Diene",
    "NẠP TỪ TÊN / SMILES": "LOAD BY NAME / SMILES",
    "VD: aspirin, CH3COOH…": "e.g. aspirin, CH3COOH…",
    "— chọn từ kho chất mẫu —": "— pick from preset library —",
    "NHÓM CHỨC & GỐC THẾ": "FUNCTIONAL GROUPS",
    "KHUNG MẪU DỰNG SẴN": "SCAFFOLD TEMPLATES",
    "HIỂN THỊ PHÂN TỬ": "DISPLAY OPTIONS",
    "Thu gọn (CH₃, CH₂, CH, C)": "Condensed (CH₃, CH₂, CH, C)",
    "Tách H trên/dưới C": "Stacked H above/below C",
    "Khung xương (ẩn C)": "Skeletal (hide C)",
    "Hiện C trong vòng": "Show ring carbons",
    "Đơn sắc (đen trắng)": "Monochrome (B&W)",
    "Lưới chấm gợi ý": "Guide dot grid",
    "Cảnh báo hóa trị": "Valence warnings",
    "THÔNG TIN PHÂN TỬ": "MOLECULE INFO",
    "Tìm Z, ký hiệu, tên IUPAC…": "Search Z, symbol, IUPAC name…",
    "Tự đọc": "Auto-speak",
    "Mô hình Bohr": "Bohr Atomic Model",
    "Sơ đồ ô orbital ↑↓": "Orbital Box Diagram ↑↓",
    "Mạch thẳng (Chains)": "Aliphatic Chains",
    "Vòng thơm (Aromatics)": "Aromatic Rings",
    "Dị vòng (Heterocycles)": "Heterocycles",
    "Vòng no & Khung (Alicyclic)": "Alicyclic & Bridged",
    "Carbohydrate & Amino acid": "Carbohydrates & Amino Acids",
    "Dược phẩm & Sinh học": "Pharmaceuticals & Bio",
    "Đơn chất (Elements)": "Elements",
    "Khí & hợp chất đơn giản": "Gases & Simple Compounds",
    "Acid vô cơ": "Inorganic Acids",
    "Base - Hydroxide": "Bases & Hydroxides",
    "Oxide": "Oxides",
    "Muối (Salts)": "Salts",
    "Ion & gốc acid": "Ions & Acid Radicals",
    "Khoáng vật - Vật liệu": "Minerals & Materials",
    "Polymer - Vật liệu": "Polymers & Materials",
    "Hợp chất thơm & Dị vòng": "Aromatics & Heterocycles",
    "Dược phẩm - Vitamin - Sinh học": "Drugs, Vitamins & Biomolecules",
    "Vô cơ thường gặp (Inorganic)": "Common Inorganics",
    "Kim loại": "Metals",
    "Phi kim": "Nonmetals",
    "Acid - Base - Muối": "Acid · Base · Salt",
    "Oxi hóa - Khử": "Redox Reactions",
    "Kết tủa": "Precipitation",
    "Nhiệt phân": "Thermal Decomposition",
    "Điện phân": "Electrolysis",
    "Điều chế": "Synthesis / Preparation",
    "Phản ứng ion": "Ionic Reactions",
    "Cân bằng hóa học": "Chemical Equilibrium",
    "Hữu cơ: Hydrocarbon": "Organic: Hydrocarbons",
    "Hữu cơ: Alcohol - Phenol": "Organic: Alcohols & Phenols",
    "Hữu cơ: Aldehyde - Acid": "Organic: Aldehydes & Acids",
    "Hữu cơ: Ester - Lipid": "Organic: Esters & Lipids",
    "Hữu cơ: Amine - Amino acid": "Organic: Amines & Amino Acids",
    "Hữu cơ: Carbohydrate": "Organic: Carbohydrates",
    "● Kim loại kiềm": "● Alkali Metals",
    "● Kim loại kiềm thổ": "● Alkaline Earth",
    "● Kim loại chuyển tiếp": "● Transition Metals",
    "● Kim loại sau chuyển tiếp": "● Post-Transition",
    "● Á kim": "● Metalloids",
    "● Phi kim": "● Nonmetals",
    "● Khí hiếm": "● Noble Gases",
    "● Họ Lantan": "● Lanthanides",
    "● Họ Actini": "● Actinides",

    # --- Máy tính khoa học & 43 công cụ
    "Số phức: tắt": "Complex: OFF",
    "Số phức: bật": "Complex: ON",
    "S⇔D  Chính xác ⇄ Thập phân": "S⇔D  Exact ⇄ Decimal",
    "Tìm nhanh:": "Quick Find:",
    "Công cụ:": "Tool:",
    "Phương trình": "Equations",
    "Thống kê": "Statistics",
    "Ma trận · Vectơ": "Matrix · Vector",
    "Số · Phức": "Numbers · Complex",
    "Tiện ích · Hóa": "Utilities · Chem",
    "Lịch sử (nhấp đúp để dùng lại)": "History (double-click to reuse)",
    "Tính toán": "Calculate",
    "Bậc 1": "Linear (ax + b = 0)",
    "Bậc 2": "Quadratic (ax² + bx + c = 0)",
    "Bậc 3–10": "Polynomial (deg 3–10)",
    "Hệ 2 ẩn": "2×2 Linear System",
    "Hệ 3 ẩn": "3×3 Linear System",
    "Hệ 4 ẩn": "4×4 Linear System",
    "Bất phương trình": "Polynomial Inequality",
    "Đạo hàm tại điểm": "Derivative at Point",
    "Tích phân xác định": "Definite Integral",
    "Giới hạn": "Limit",
    "Σ và Π": "Summation Σ & Product Π",
    "Bảng giá trị f(x)": "Function Table f(x)",
    "CALC (thay biến)": "CALC (Evaluate Variables)",
    "Thống kê 1 biến": "1-Variable Statistics",
    "Hồi quy": "Regression Analysis",
    "Phân phối chuẩn": "Normal Distribution",
    "Phân vị chuẩn (InvN)": "Inverse Normal (InvN)",
    "Nhị thức": "Binomial Distribution",
    "Tổ hợp – Chỉnh hợp": "Combinations & Permutations",
    "Ma trận": "Matrix Operations",
    "Hệ cơ số": "Base-N Converter",
    "Logic bit": "Bitwise Logic",
    "ƯCLN · BCNN": "GCD · LCM",
    "Phân tích thừa số nguyên tố": "Prime Factorization",
    "Chia có dư": "Euclidean Division",
    "Phân số ⇄ thập phân": "Fraction ⇄ Decimal",
    "Lũy thừa modulo": "Modular Exponentiation",
    "Số ngẫu nhiên": "Random Numbers",
    "Giải tam giác": "Triangle Solver",
    "Đường thẳng qua 2 điểm": "Line Through 2 Points",
    "Đường tròn qua 3 điểm": "Circle Through 3 Points",
    "Diện tích – Thể tích": "Area & Volume",
    "Đổi đơn vị": "Unit Converter",
    "Tỉ lệ a:b = c:x": "Ratio a:b = c:x",
    "Phần trăm": "Percentage",
    "Lãi suất – Trả góp": "Interest & Loan EMI",
    "Hóa học: Tính pH dung dịch": "Chemistry: Solution pH",
    "Hóa học: Pha loãng C₁V₁ = C₂V₂": "Chemistry: Dilution C₁V₁ = C₂V₂",
    "Hằng số vật lí": "Physical Constants",
    "Tìm hoặc chọn…": "Search or select…",
}


# Các mẫu động có số liệu thay đổi (regex)
_DYNAMIC_PATTERNS = [
    (re.compile(r"^\[([^\]]+)\](\s+)(.+)$"), lambda m: f"[{tr(m.group(1))}]{m.group(2)}{tr(m.group(3))}"),
    (re.compile(r"^(\s*)Tài liệu Word \((\d+)\)$"), lambda m: f"{m.group(1)}Word Document ({m.group(2)})"),
    (re.compile(r"^Tra cứu chất \((\d+)\)$"), lambda m: f"Chemistry Wiki ({m.group(1)})"),
    (re.compile(r"^Công thức mẫu \((\d+)\)$"), lambda m: f"Sample Formulas ({m.group(1)})"),
    (re.compile(r"^Phản ứng mẫu \((\d+)\)$"), lambda m: f"Sample Reactions ({m.group(1)})"),
    (re.compile(r"^★ (?:Tự học|Đã Lưu) \((\d+)\)$"), lambda m: f"★ Bookmarked ({m.group(1)})"),
    (re.compile(r"^HÌNH MẪU 2D · 3D \((\d+)\)$"), lambda m: f"2D · 3D FIGURES ({m.group(1)})"),
    (re.compile(r"^Mẫu \((\d+)\):$"), lambda m: f"Presets ({m.group(1)}):"),
    (re.compile(r"^(\d+) chất$"), lambda m: f"{m.group(1)} compounds"),
    (re.compile(r"^(\d+) mẫu$"), lambda m: f"{m.group(1)} formulas"),
    (re.compile(r"^(\d+) phản ứng$"), lambda m: f"{m.group(1)} reactions"),
    (re.compile(r"^Tìm trong (\d+) chất chuẩn IUPAC:.*$"), lambda m: f"Search {m.group(1)} IUPAC compounds: name, formula, uses… (e.g. Nitrogen dioxide, Aspirin, H2SO4)"),
    (re.compile(r"^Gõ tên trong (\d+) bộ giải.*$"), lambda m: f"Search {m.group(1)} solvers (e.g. quadratic, integral, pH, matrix)…"),
]


def tr(text: str, en_fallback: str = None) -> str:
    """Dịch chuỗi UI sang tiếng Anh khi ngôn ngữ hiện tại là 'en'; trả nguyên bản khi là 'vi'."""
    if not text or _LANG != "en":
        return text
    if en_fallback is not None:
        return en_fallback
    # Bỏ ký tự && escape của QPushButton nếu có
    unesc = text.replace("&&", "&")
    hit = VI_TO_EN.get(unesc)
    if hit is not None:
        return hit.replace("&", "&&") if "&&" in text else hit
    for rx, fn in _DYNAMIC_PATTERNS:
        m = rx.match(unesc)
        if m:
            out = fn(m)
            return out.replace("&", "&&") if "&&" in text else out
    return text


def combo_key(cmb: QComboBox) -> str:
    """Trả về chuỗi khóa gốc (Tiếng Việt) của mục đang chọn trong QComboBox, bất kể đang hiển thị tiếng Anh."""
    idx = cmb.currentIndex()
    vi_items = cmb.property("_vi_items")
    if isinstance(vi_items, list) and 0 <= idx < len(vi_items):
        return vi_items[idx]
    return cmb.currentText()


def reset_combo_vi_cache(cmb: QComboBox):
    """Gọi sau khi nạp lại danh sách item mới vào QComboBox động để cập nhật bản dịch."""
    cmb.setProperty("_vi_items", None)


def apply_lang_to_tree(root: QWidget):
    """Quét và cập nhật ngôn ngữ tức thì cho toàn bộ cây widget con — 100% có thể đảo chiều VI ⇄ EN."""
    if root is None:
        return

    def _sync_prop(w, prop_name, getter, setter):
        cur = getter()
        orig = w.property(prop_name)
        if orig is None:
            if not cur:
                return
            w.setProperty(prop_name, cur)
            orig = cur
        target = tr(orig)
        if target != cur:
            setter(target)

    widgets = [root] + root.findChildren(QWidget)
    for w in widgets:
        # Tooltip trên mọi widget
        tip = w.toolTip()
        orig_tip = w.property("_vi_tip")
        if orig_tip is None and tip:
            w.setProperty("_vi_tip", tip)
            orig_tip = tip
        if orig_tip:
            ntip = tr(orig_tip)
            if ntip != tip:
                w.setToolTip(ntip)

        if isinstance(w, QTabWidget):
            orig_tabs = w.property("_vi_tabs")
            if not isinstance(orig_tabs, list) or len(orig_tabs) != w.count():
                orig_tabs = [w.tabText(i) for i in range(w.count())]
                w.setProperty("_vi_tabs", orig_tabs)
            for i, ot in enumerate(orig_tabs):
                nt = smart_title(tr(ot))
                if nt != w.tabText(i):
                    w.setTabText(i, nt)
        elif isinstance(w, QComboBox):
            orig_items = w.property("_vi_items")
            if not isinstance(orig_items, list) or len(orig_items) != w.count():
                orig_items = [w.itemText(i) for i in range(w.count())]
                w.setProperty("_vi_items", orig_items)
            w.blockSignals(True)
            cur_i = w.currentIndex()
            for i, oi in enumerate(orig_items):
                ni = smart_title(tr(oi))
                if ni != w.itemText(i):
                    w.setItemText(i, ni)
            if w.isEditable() and 0 <= cur_i < w.count():
                w.setEditText(w.itemText(cur_i))
            w.blockSignals(False)
            if w.isEditable() and w.lineEdit() is not None:
                _sync_prop(w.lineEdit(), "_vi_ph", w.lineEdit().placeholderText, w.lineEdit().setPlaceholderText)
        elif isinstance(w, (QLineEdit, QPlainTextEdit)):
            _sync_prop(w, "_vi_ph", w.placeholderText, w.setPlaceholderText)
        elif isinstance(w, (QLabel, QPushButton, QCheckBox, QRadioButton)):
            # Bỏ qua widget tự quản lí nhãn động riêng (như nút sidebar thu gọn, nhãn tên chất Wiki)
            if w.property("_i18n_skip"):
                continue
            def _setter(val, _w=w):
                if isinstance(_w, QLabel) and (_w.property("h1") or _w.property("h2")) and len(val) <= 46:
                    val = smart_title(val)
                _w.setText(val)
            _sync_prop(w, "_vi_text", w.text, _setter)


def tr_math_latex(tex: str) -> str:
    """Dịch các từ tiếng Việt hiếm gặp bên trong \\mathrm{...}/\\text{...} của công thức mẫu khi bật tiếng Anh."""
    if not is_en() or not tex:
        return tex
    return (
        tex.replace(r"\mathrm{khi}", r"\mathrm{if}")
           .replace(r"\mathrm{hoặc}", r"\mathrm{or}")
           .replace(r"\text{hoặc}", r"\text{or}")
           .replace(r"\mathrm{là\ điểm\ cực\ tiểu}", r"\mathrm{is\ a\ local\ minimum}")
    )

