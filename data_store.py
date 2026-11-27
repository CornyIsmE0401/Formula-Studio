import json
import os
from pathlib import Path

APP_NAME = "Formula Studio"
APP_VERSION = "v1.0"
APP_AUTHOR = "by ItzMe_Corniizt"

USER_DATA_PATH = Path.home() / ".formula_studio.json"

# ==============================================================================
# 1. BẢNG TUẦN HOÀN 118 NGUYÊN TỐ
# (Z, Symbol, English, Vietnamese, Latin, IPA, Mass, Category, Row, Col, Period, Group)
# Categories:
#   alkali, alkaline, transition, post_transition, metalloid, nonmetal, noble, lanthanide, actinide
# ==============================================================================
CATEGORY_LABELS = {
    "alkali": ("Kim loại kiềm", "#F97316"),
    "alkaline": ("Kim loại kiềm thổ", "#EAB308"),
    "transition": ("Kim loại chuyển tiếp", "#06B6D4"),
    "post_transition": ("Kim loại sau chuyển tiếp", "#3B82F6"),
    "metalloid": ("Á kim", "#10B981"),
    "nonmetal": ("Phi kim", "#22C55E"),
    "noble": ("Khí hiếm", "#A855F7"),
    "lanthanide": ("Họ Lantan", "#EC4899"),
    "actinide": ("Họ Actini", "#6366F1"),
}

ELEMENTS_RAW = [
    (1, "H", "Hydrogen", "Hiđro", "Hydrogenium", "/ˈhaɪdrədʒən/", 1.008, "nonmetal", 0, 0, 1, 1),
    (2, "He", "Helium", "Heli", "Helium", "/ˈhiːliəm/", 4.0026, "noble", 0, 17, 1, 18),
    (3, "Li", "Lithium", "Liti", "Lithium", "/ˈlɪθiəm/", 6.94, "alkali", 1, 0, 2, 1),
    (4, "Be", "Beryllium", "Beri", "Beryllium", "/bəˈrɪliəm/", 9.0122, "alkaline", 1, 1, 2, 2),
    (5, "B", "Boron", "Bo", "Borum", "/ˈbɔːrɒn/", 10.81, "metalloid", 1, 12, 2, 13),
    (6, "C", "Carbon", "Cacbon", "Carboneum", "/ˈkɑːrbən/", 12.011, "nonmetal", 1, 13, 2, 14),
    (7, "N", "Nitrogen", "Nitơ", "Nitrogenium", "/ˈnaɪtrədʒən/", 14.007, "nonmetal", 1, 14, 2, 15),
    (8, "O", "Oxygen", "Oxi", "Oxygenium", "/ˈɒksɪdʒən/", 15.999, "nonmetal", 1, 15, 2, 16),
    (9, "F", "Fluorine", "Flo", "Fluorum", "/ˈflʊəriːn/", 18.998, "nonmetal", 1, 16, 2, 17),
    (10, "Ne", "Neon", "Neon", "Neon", "/ˈniːɒn/", 20.180, "noble", 1, 17, 2, 18),
    (11, "Na", "Sodium", "Natri", "Natrium", "/ˈsoʊdiəm/", 22.990, "alkali", 2, 0, 3, 1),
    (12, "Mg", "Magnesium", "Magie", "Magnesium", "/mæɡˈniːziəm/", 24.305, "alkaline", 2, 1, 3, 2),
    (13, "Al", "Aluminium", "Nhôm", "Aluminium", "/ˌæljʊˈmɪniəm/", 26.982, "post_transition", 2, 12, 3, 13),
    (14, "Si", "Silicon", "Silic", "Silicium", "/ˈsɪlɪkən/", 28.085, "metalloid", 2, 13, 3, 14),
    (15, "P", "Phosphorus", "Photpho", "Phosphorus", "/ˈfɒsfərəs/", 30.974, "nonmetal", 2, 14, 3, 15),
    (16, "S", "Sulfur", "Lưu huỳnh", "Sulphur", "/ˈsʌlfər/", 32.06, "nonmetal", 2, 15, 3, 16),
    (17, "Cl", "Chlorine", "Clo", "Chlorum", "/ˈklɔːriːn/", 35.45, "nonmetal", 2, 16, 3, 17),
    (18, "Ar", "Argon", "Argon", "Argon", "/ˈɑːrɡɒn/", 39.948, "noble", 2, 17, 3, 18),
    (19, "K", "Potassium", "Kali", "Kalium", "/pəˈtæsiəm/", 39.098, "alkali", 3, 0, 4, 1),
    (20, "Ca", "Calcium", "Canxi", "Calcium", "/ˈkælsiəm/", 40.078, "alkaline", 3, 1, 4, 2),
    (21, "Sc", "Scandium", "Scandi", "Scandium", "/ˈskændiəm/", 44.956, "transition", 3, 2, 4, 3),
    (22, "Ti", "Titanium", "Titan", "Titanium", "/taɪˈteɪniəm/", 47.867, "transition", 3, 3, 4, 4),
    (23, "V", "Vanadium", "Vanadi", "Vanadium", "/vəˈneɪdiəm/", 50.942, "transition", 3, 4, 4, 5),
    (24, "Cr", "Chromium", "Crom", "Chromium", "/ˈkroʊmiəm/", 51.996, "transition", 3, 5, 4, 6),
    (25, "Mn", "Manganese", "Mangan", "Manganum", "/ˈmæŋɡəniːz/", 54.938, "transition", 3, 6, 4, 7),
    (26, "Fe", "Iron", "Sắt", "Ferrum", "/ˈaɪərn/", 55.845, "transition", 3, 7, 4, 8),
    (27, "Co", "Cobalt", "Coban", "Cobaltum", "/ˈkoʊbɔːlt/", 58.933, "transition", 3, 8, 4, 9),
    (28, "Ni", "Nickel", "Niken", "Niccolum", "/ˈnɪkəl/", 58.693, "transition", 3, 9, 4, 10),
    (29, "Cu", "Copper", "Đồng", "Cuprum", "/ˈkɒpər/", 63.546, "transition", 3, 10, 4, 11),
    (30, "Zn", "Zinc", "Kẽm", "Zincum", "/zɪŋk/", 65.38, "transition", 3, 11, 4, 12),
    (31, "Ga", "Gallium", "Gali", "Gallium", "/ˈɡæliəm/", 69.723, "post_transition", 3, 12, 4, 13),
    (32, "Ge", "Germanium", "Gemani", "Germanium", "/dʒɜːrˈmeɪniəm/", 72.630, "metalloid", 3, 13, 4, 14),
    (33, "As", "Arsenic", "Asen", "Arsenicum", "/ˈɑːrsənɪk/", 74.922, "metalloid", 3, 14, 4, 15),
    (34, "Se", "Selenium", "Selen", "Selenium", "/səˈliːniəm/", 78.971, "nonmetal", 3, 15, 4, 16),
    (35, "Br", "Bromine", "Brom", "Bromum", "/ˈbroʊmiːn/", 79.904, "nonmetal", 3, 16, 4, 17),
    (36, "Kr", "Krypton", "Kripton", "Krypton", "/ˈkrɪptɒn/", 83.798, "noble", 3, 17, 4, 18),
    (37, "Rb", "Rubidium", "Rubiđi", "Rubidium", "/ruːˈbɪdiəm/", 85.468, "alkali", 4, 0, 5, 1),
    (38, "Sr", "Strontium", "Stronti", "Strontium", "/ˈstrɒntiəm/", 87.62, "alkaline", 4, 1, 5, 2),
    (39, "Y", "Yttrium", "Ytri", "Yttrium", "/ˈɪtriəm/", 88.906, "transition", 4, 2, 5, 3),
    (40, "Zr", "Zirconium", "Ziriconi", "Zirconium", "/zɜːrˈkoʊniəm/", 91.224, "transition", 4, 3, 5, 4),
    (41, "Nb", "Niobium", "Niobi", "Niobium", "/naɪˈoʊbiəm/", 92.906, "transition", 4, 4, 5, 5),
    (42, "Mo", "Molybdenum", "Molipđen", "Molybdaenum", "/məˈlɪbdənəm/", 95.95, "transition", 4, 5, 5, 6),
    (43, "Tc", "Technetium", "Tecneti", "Technetium", "/tɛkˈniːʃiəm/", 98.0, "transition", 4, 6, 5, 7),
    (44, "Ru", "Ruthenium", "Ruteni", "Ruthenium", "/ruːˈθiːniəm/", 101.07, "transition", 4, 7, 5, 8),
    (45, "Rh", "Rhodium", "Rođi", "Rhodium", "/ˈroʊdiəm/", 102.91, "transition", 4, 8, 5, 9),
    (46, "Pd", "Palladium", "Palađi", "Palladium", "/pəˈleɪdiəm/", 106.42, "transition", 4, 9, 5, 10),
    (47, "Ag", "Silver", "Bạc", "Argentum", "/ˈsɪlvər/", 107.87, "transition", 4, 10, 5, 11),
    (48, "Cd", "Cadmium", "Cađimi", "Cadmium", "/ˈkædmiəm/", 112.41, "transition", 4, 11, 5, 12),
    (49, "In", "Indium", "Inđi", "Indium", "/ˈɪndiəm/", 114.82, "post_transition", 4, 12, 5, 13),
    (50, "Sn", "Tin", "Thiếc", "Stannum", "/tɪn/", 118.71, "post_transition", 4, 13, 5, 14),
    (51, "Sb", "Antimony", "Antimon", "Stibium", "/ˈæntɪmoʊni/", 121.76, "metalloid", 4, 14, 5, 15),
    (52, "Te", "Tellurium", "Telu", "Tellurium", "/təˈlʊəriəm/", 127.60, "metalloid", 4, 15, 5, 16),
    (53, "I", "Iodine", "Iot", "Iodum", "/ˈaɪədaɪn/", 126.90, "nonmetal", 4, 16, 5, 17),
    (54, "Xe", "Xenon", "Xenon", "Xenon", "/ˈziːnɒn/", 131.29, "noble", 4, 17, 5, 18),
    (55, "Cs", "Caesium", "Xesi", "Caesium", "/ˈsiːziəm/", 132.91, "alkali", 5, 0, 6, 1),
    (56, "Ba", "Barium", "Bari", "Barium", "/ˈbɛəriəm/", 137.33, "alkaline", 5, 1, 6, 2),
    (57, "La", "Lanthanum", "Lantan", "Lanthanum", "/ˈlænθənəm/", 138.91, "lanthanide", 8, 2, 6, 3),
    (58, "Ce", "Cerium", "Xeri", "Cerium", "/ˈsɪəriəm/", 140.12, "lanthanide", 8, 3, 6, 3),
    (59, "Pr", "Praseodymium", "Prazeođim", "Praseodymium", "/ˌpreɪzioʊˈdɪmiəm/", 140.91, "lanthanide", 8, 4, 6, 3),
    (60, "Nd", "Neodymium", "Neođim", "Neodymium", "/ˌniːoʊˈdɪmiəm/", 144.24, "lanthanide", 8, 5, 6, 3),
    (61, "Pm", "Promethium", "Prometi", "Promethium", "/prəˈmiːθiəm/", 145.0, "lanthanide", 8, 6, 6, 3),
    (62, "Sm", "Samarium", "Samari", "Samarium", "/səˈmɛəriəm/", 150.36, "lanthanide", 8, 7, 6, 3),
    (63, "Eu", "Europium", "Europi", "Europium", "/jʊˈroʊpiəm/", 151.96, "lanthanide", 8, 8, 6, 3),
    (64, "Gd", "Gadolinium", "Gađolini", "Gadolinium", "/ˌɡædəˈlɪniəm/", 157.25, "lanthanide", 8, 9, 6, 3),
    (65, "Tb", "Terbium", "Tebi", "Terbium", "/ˈtɜːrbiəm/", 158.93, "lanthanide", 8, 10, 6, 3),
    (66, "Dy", "Dysprosium", "Đisprozi", "Dysprosium", "/dɪsˈproʊziəm/", 162.50, "lanthanide", 8, 11, 6, 3),
    (67, "Ho", "Holmium", "Honmi", "Holmium", "/ˈhoʊlmiəm/", 164.93, "lanthanide", 8, 12, 6, 3),
    (68, "Er", "Erbium", "Ebi", "Erbium", "/ˈɜːrbiəm/", 167.26, "lanthanide", 8, 13, 6, 3),
    (69, "Tm", "Thulium", "Tuli", "Thulium", "/ˈθjuːliəm/", 168.93, "lanthanide", 8, 14, 6, 3),
    (70, "Yb", "Ytterbium", "Ytebi", "Ytterbium", "/ɪˈtɜːrbiəm/", 173.05, "lanthanide", 8, 15, 6, 3),
    (71, "Lu", "Lutetium", "Luteti", "Lutetium", "/luːˈtiːʃiəm/", 174.97, "lanthanide", 8, 16, 6, 3),
    (72, "Hf", "Hafnium", "Hafini", "Hafnium", "/ˈhæfniəm/", 178.49, "transition", 5, 3, 6, 4),
    (73, "Ta", "Tantalum", "Tantan", "Tantalum", "/ˈtæntələm/", 180.95, "transition", 5, 4, 6, 5),
    (74, "W", "Tungsten", "Vonfam", "Wolframium", "/ˈtʌŋstən/", 183.84, "transition", 5, 5, 6, 6),
    (75, "Re", "Rhenium", "Reni", "Rhenium", "/ˈriːniəm/", 186.21, "transition", 5, 6, 6, 7),
    (76, "Os", "Osmium", "Osimi", "Osmium", "/ˈɒzmiəm/", 190.23, "transition", 5, 7, 6, 8),
    (77, "Ir", "Iridium", "Iriđi", "Iridium", "/ɪˈrɪdiəm/", 192.22, "transition", 5, 8, 6, 9),
    (78, "Pt", "Platinum", "Bạch kim", "Platinum", "/ˈplætɪnəm/", 195.08, "transition", 5, 9, 6, 10),
    (79, "Au", "Gold", "Vàng", "Aurum", "/ɡoʊld/", 196.97, "transition", 5, 10, 6, 11),
    (80, "Hg", "Mercury", "Thủy ngân", "Hydrargyrum", "/ˈmɜːrkjʊri/", 200.59, "transition", 5, 11, 6, 12),
    (81, "Tl", "Thallium", "Tali", "Thallium", "/ˈθæliəm/", 204.38, "post_transition", 5, 12, 6, 13),
    (82, "Pb", "Lead", "Chì", "Plumbum", "/lɛd/", 207.2, "post_transition", 5, 13, 6, 14),
    (83, "Bi", "Bismuth", "Bitmut", "Bismuthum", "/ˈbɪzməθ/", 208.98, "post_transition", 5, 14, 6, 15),
    (84, "Po", "Polonium", "Poloni", "Polonium", "/pəˈloʊniəm/", 209.0, "post_transition", 5, 15, 6, 16),
    (85, "At", "Astatine", "Atatin", "Astatum", "/ˈæstətiːn/", 210.0, "metalloid", 5, 16, 6, 17),
    (86, "Rn", "Radon", "Rađon", "Radon", "/ˈreɪdɒn/", 222.0, "noble", 5, 17, 6, 18),
    (87, "Fr", "Francium", "Franxi", "Francium", "/ˈfrænsiəm/", 223.0, "alkali", 6, 0, 7, 1),
    (88, "Ra", "Radium", "Rađi", "Radium", "/ˈreɪdiəm/", 226.0, "alkaline", 6, 1, 7, 2),
    (89, "Ac", "Actinium", "Actini", "Actinium", "/ækˈtɪniəm/", 227.0, "actinide", 9, 2, 7, 3),
    (90, "Th", "Thorium", "Thori", "Thorium", "/ˈθɔːriəm/", 232.04, "actinide", 9, 3, 7, 3),
    (91, "Pa", "Protactinium", "Protactini", "Protactinium", "/ˌproʊtækˈtɪniəm/", 231.04, "actinide", 9, 4, 7, 3),
    (92, "U", "Uranium", "Urani", "Uranium", "/jʊˈreɪniəm/", 238.03, "actinide", 9, 5, 7, 3),
    (93, "Np", "Neptunium", "Neptuni", "Neptunium", "/nɛpˈtjuːniəm/", 237.0, "actinide", 9, 6, 7, 3),
    (94, "Pu", "Plutonium", "Plutoni", "Plutonium", "/pluːˈtoʊniəm/", 244.0, "actinide", 9, 7, 7, 3),
    (95, "Am", "Americium", "Amerixi", "Americium", "/ˌæməˈrɪʃiəm/", 243.0, "actinide", 9, 8, 7, 3),
    (96, "Cm", "Curium", "Curi", "Curium", "/ˈkjʊəriəm/", 247.0, "actinide", 9, 9, 7, 3),
    (97, "Bk", "Berkelium", "Beckeli", "Berkelium", "/ˈbɜːrkliəm/", 247.0, "actinide", 9, 10, 7, 3),
    (98, "Cf", "Californium", "Califoni", "Californium", "/ˌkælɪˈfɔːrniəm/", 251.0, "actinide", 9, 11, 7, 3),
    (99, "Es", "Einsteinium", "Ensteni", "Einsteinium", "/aɪnˈstaɪniəm/", 252.0, "actinide", 9, 12, 7, 3),
    (100, "Fm", "Fermium", "Fecmi", "Fermium", "/ˈfɜːrmiəm/", 257.0, "actinide", 9, 13, 7, 3),
    (101, "Md", "Mendelevium", "Menđelevi", "Mendelevium", "/ˌmɛndəˈliːviəm/", 258.0, "actinide", 9, 14, 7, 3),
    (102, "No", "Nobelium", "Nobeli", "Nobelium", "/noʊˈbiːliəm/", 259.0, "actinide", 9, 15, 7, 3),
    (103, "Lr", "Lawrencium", "Lorenxi", "Lawrencium", "/lɒˈrɛnsiəm/", 266.0, "actinide", 9, 16, 7, 3),
    (104, "Rf", "Rutherfordium", "Rơdơfođi", "Rutherfordium", "/ˌrʌðərˈfɔːrdiəm/", 267.0, "transition", 6, 3, 7, 4),
    (105, "Db", "Dubnium", "Đupni", "Dubnium", "/ˈdʌbniəm/", 268.0, "transition", 6, 4, 7, 5),
    (106, "Sg", "Seaborgium", "Xibogi", "Seaborgium", "/siːˈbɔːrɡiəm/", 269.0, "transition", 6, 5, 7, 6),
    (107, "Bh", "Bohrium", "Bori", "Bohrium", "/ˈbɔːriəm/", 270.0, "transition", 6, 6, 7, 7),
    (108, "Hs", "Hassium", "Haxi", "Hassium", "/ˈhæsiəm/", 277.0, "transition", 6, 7, 7, 8),
    (109, "Mt", "Meitnerium", "Meitneri", "Meitnerium", "/maɪtˈnɪəriəm/", 278.0, "transition", 6, 8, 7, 9),
    (110, "Ds", "Darmstadtium", "Đamstati", "Darmstadtium", "/dɑːrmˈʃtætiəm/", 281.0, "transition", 6, 9, 7, 10),
    (111, "Rg", "Roentgenium", "Rơngeni", "Roentgenium", "/rɛntˈɡɛniəm/", 282.0, "transition", 6, 10, 7, 11),
    (112, "Cn", "Copernicium", "Copernixi", "Copernicium", "/ˌkoʊpərˈnɪsiəm/", 285.0, "transition", 6, 11, 7, 12),
    (113, "Nh", "Nihonium", "Nihoni", "Nihonium", "/nɪˈhoʊniəm/", 286.0, "post_transition", 6, 12, 7, 13),
    (114, "Fl", "Flerovium", "Flerovi", "Flerovium", "/fləˈroʊviəm/", 289.0, "post_transition", 6, 13, 7, 14),
    (115, "Mc", "Moscovium", "Moscovi", "Moscovium", "/mɒsˈkoʊviəm/", 290.0, "post_transition", 6, 14, 7, 15),
    (116, "Lv", "Livermorium", "Livermori", "Livermorium", "/ˌlɪvərˈmɔːriəm/", 293.0, "post_transition", 6, 15, 7, 16),
    (117, "Ts", "Tennessine", "Tennessin", "Tennessine", "/ˌtɛnəˈsiːn/", 294.0, "metalloid", 6, 16, 7, 17),
    (118, "Og", "Oganesson", "Oganeson", "Oganesson", "/ˌɒɡəˈnɛsɒn/", 294.0, "noble", 6, 17, 7, 18),
]

ELEMENTS_BY_SYMBOL = {e[1]: e for e in ELEMENTS_RAW}
ELEMENTS_BY_Z = {e[0]: e for e in ELEMENTS_RAW}
ATOMIC_MASSES = {e[1]: e[6] for e in ELEMENTS_RAW}



MATH_SAMPLES = [
    ("Phương trình bậc hai", "Đại số", r"ax^2 + bx + c = 0,\quad x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}"),
    ("Định lý Pythagore", "Hình học", r"a^2 + b^2 = c^2"),
    ("Khai triển Newton", "Đại số", r"(x + y)^n = \sum_{k=0}^{n} C_n^k x^{n-k} y^k"),
    ("Định nghĩa đạo hàm", "Giải tích", r"f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}"),
    ("Tích phân xác định", "Giải tích", r"\int_{a}^{b} f(x)\,dx = F(b) - F(a)"),
    ("Tích phân từng phần", "Giải tích", r"\int u\,dv = uv - \int v\,du"),
    ("Ma trận vuông 2×2", "Đại số", r"A = \begin{bmatrix} a_{11} & a_{12} \\ a_{21} & a_{22} \end{bmatrix}"),
    ("Định thức ma trận 2×2", "Đại số", r"\det(A) = a_{11}a_{22} - a_{12}a_{21}"),
    ("Hệ phương trình tuyến tính", "Đại số", r"\begin{cases} a_1 x + b_1 y = c_1 \\ a_2 x + b_2 y = c_2 \end{cases}"),
    ("Công thức xác suất Bayes", "Xác suất", r"P(A|B) = \frac{P(B|A) \cdot P(A)}{P(B)}"),
    ("Đẳng thức Euler", "Giải tích", r"e^{i\pi} + 1 = 0"),
    ("Công thức Heron (diện tích tam giác)", "Hình học", r"S = \sqrt{p(p-a)(p-b)(p-c)},\quad p = \frac{a+b+c}{2}"),
    ("Định lý Cosin", "Hình học", r"c^2 = a^2 + b^2 - 2ab\cos C"),
    ("Định lý Sin", "Hình học", r"\frac{a}{\sin A} = \frac{b}{\sin B} = \frac{c}{\sin C} = 2R"),
    ("Tổng cấp số cộng", "Đại số", r"S_n = \frac{n(u_1 + u_n)}{2} = \frac{n[2u_1 + (n-1)d]}{2}"),
    ("Tổng cấp số nhân", "Đại số", r"S_n = u_1 \cdot \frac{1 - q^n}{1 - q}\quad (q \neq 1)"),
    ("Phương trình đường tròn", "Hình học", r"(x - a)^2 + (y - b)^2 = R^2"),
    ("Khoảng cách điểm đến đường thẳng", "Hình học", r"d(M, \Delta) = \frac{|Ax_0 + By_0 + C|}{\sqrt{A^2 + B^2}}"),
    ("Thể tích & Diện tích mặt cầu", "Hình học", r"V = \frac{4}{3}\pi R^3,\quad S = 4\pi R^2"),
    ("Giới hạn lượng giác cơ bản", "Giải tích", r"\lim_{x \to 0} \frac{\sin x}{x} = 1"),
    ("Giới hạn số e", "Giải tích", r"\lim_{n \to \infty} \left(1 + \frac{1}{n}\right)^n = e"),
    ("Chuỗi Taylor", "Giải tích", r"f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!}(x - a)^n"),
    ("Phân phối chuẩn (Gaussian)", "Xác suất", r"f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{1}{2}\left(\frac{x-\mu}{\sigma}\right)^2}"),
    ("Độ lệch chuẩn mẫu", "Xác suất", r"s = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar{x})^2}"),
    ("Kỳ vọng & Phương sai", "Xác suất", r"\mathrm{Var}(X) = E[X^2] - (E[X])^2"),
    ("Công thức lãi kép", "Ứng dụng", r"A = P\left(1 + \frac{r}{n}\right)^{nt}"),
    ("Giá trị hiện tại thuần (NPV)", "Ứng dụng", r"\mathrm{NPV} = \sum_{t=0}^{n} \frac{CF_t}{(1 + r)^t}"),
    ("Bất đẳng thức Cauchy (AM-GM)", "Đại số", r"\frac{a + b}{2} \geq \sqrt{ab}\quad (a, b \geq 0)"),
    ("Bất đẳng thức Bunhiacopxki", "Đại số", r"(a^2 + b^2)(x^2 + y^2) \geq (ax + by)^2"),
    ("Hệ thức lượng giác cơ bản", "Lượng giác", r"\sin^2 x + \cos^2 x = 1,\quad \tan x = \frac{\sin x}{\cos x}"),
    ("Công thức hạ bậc", "Lượng giác", r"\cos^2 x = \frac{1 + \cos 2x}{2},\quad \sin^2 x = \frac{1 - \cos 2x}{2}"),
    ("Công thức đổi cơ số Logarit", "Đại số", r"\log_a b = \frac{\log_c b}{\log_c a}\quad (a, b, c > 0,\ a,c \neq 1)"),
]


MATH_PALETTES = {
    "Khung mẫu": [
        ("a/b", r"\frac{a}{b}"), ("√x", r"\sqrt{x}"), ("ⁿ√x", r"\sqrt[n]{x}"),
        ("xⁿ", r"x^{n}"), ("xₙ", r"x_{n}"), ("xₙᵐ", r"x_{n}^{m}"),
        ("( )", r"\left( x \right)"), ("[ ]", r"\left[ x \right]"), ("{ }", r"\left\{ x \right\}"),
        ("|x|", r"\left| x \right|"), ("{ hệ", r"\begin{cases} x + y = 1 \\ x - y = 0 \end{cases}"),
        ("∫", r"\int_{a}^{b} f(x)\,dx"), ("∑", r"\sum_{i=1}^{n} x_i"),
        ("lim", r"\lim_{x \to 0} f(x)"), ("log", r"\log_{a}(b)"),
        ("AB→", r"\vec{AB}"), ("x̄", r"\bar{x}"), ("M₂ₓ₂", r"\begin{bmatrix} a & b \\ c & d \end{bmatrix}"),
    ],
    "Cơ bản": [
        ("±", r"\pm "), ("×", r"\times "), ("÷", r"\div "), ("·", r"\cdot "),
        ("≠", r"\neq "), ("≤", r"\leq "), ("≥", r"\geq "), ("≈", r"\approx "),
        ("∞", r"\infty "), ("°", r"^\circ "), ("x²", r"x^2"), ("x³", r"x^3"),
        ("%", r"\%"), ("…", r"\dots "), ("≡", r"\equiv "), ("∝", r"\propto "),
    ],
    "Hàm số": [
        ("sin", r"\sin(x)"), ("cos", r"\cos(x)"), ("tan", r"\tan(x)"), ("cot", r"\cot(x)"),
        ("arcsin", r"\arcsin(x)"), ("arccos", r"\arccos(x)"), ("ln", r"\ln(x)"), ("lg", r"\lg(x)"),
        ("exp", r"e^{x}"), ("max", r"\max(a,b)"), ("min", r"\min(a,b)"), ("det", r"\det(A)"),
        ("f'(x)", r"f'(x)"), ("∂/∂x", r"\frac{\partial f}{\partial x}"),
    ],
    "Hy Lạp": [
        ("α", r"\alpha "), ("β", r"\beta "), ("γ", r"\gamma "), ("δ", r"\delta "),
        ("Δ", r"\Delta "), ("ε", r"\varepsilon "), ("θ", r"\theta "), ("λ", r"\lambda "),
        ("μ", r"\mu "), ("π", r"\pi "), ("ρ", r"\rho "), ("σ", r"\sigma "),
        ("Σ", r"\Sigma "), ("τ", r"\tau "), ("φ", r"\varphi "), ("ω", r"\omega "), ("Ω", r"\Omega "),
    ],
    "Tập hợp": [
        ("∈", r"\in "), ("∉", r"\notin "), ("⊂", r"\subset "), ("⊆", r"\subseteq "),
        ("∪", r"\cup "), ("∩", r"\cap "), ("∅", r"\emptyset "), ("∀", r"\forall "),
        ("∃", r"\exists "), ("⇒", r"\Rightarrow "), ("⇔", r"\Leftrightarrow "),
        ("ℝ", r"\mathbb{R}"), ("ℕ", r"\mathbb{N}"), ("ℤ", r"\mathbb{Z}"), ("ℚ", r"\mathbb{Q}"),
    ],
    "Hình học": [
        ("⊥", r"\perp "), ("∥", r"\parallel "), ("∠", r"\angle "), ("△", r"\triangle "),
        ("≅", r"\cong "), ("∼", r"\sim "), ("°", r"^\circ"), ("′", r"'"),
        ("″", r"''"), ("π", r"\pi "), ("AB→", r"\vec{AB}"), ("|u→|", r"|\vec{u}|"),
    ],
}

# ==============================================================================
# 3. KHO 45+ PHƯƠNG TRÌNH & CÔNG THỨC HÓA HỌC MẪU
# ==============================================================================

CHEM_PALETTES = {
    "Phản ứng": [
        ("+", " + "), ("→", " -> "), ("⇌", " <=> "), ("↑", " ^ "), ("↓", " v "),
        ("Δ", " ->[t^o] "), ("· (ngậm nước)", "."),
    ],
    "Chỉ số": [
        ("₂", "2"), ("₃", "3"), ("₄", "4"), ("₅", "5"), ("₆", "6"), ("₇", "7"), ("₈", "8"), ("ₙ", "n"),
    ],
    "Điện tích": [
        ("⁺", "^{+}"), ("⁻", "^{-}"), ("²⁺", "^{2+}"), ("³⁺", "^{3+}"),
        ("²⁻", "^{2-}"), ("³⁻", "^{3-}"), ("e⁻", "e^-"),
    ],
    "Trạng thái": [
        ("(s) rắn", "(s)"), ("(l) lỏng", "(l)"), ("(g) khí", "(g)"), ("(aq) dd", "(aq)"),
    ],
    "Điều kiện": [
        ("Nhiệt t°", " ->[t^o] "), ("Ánh sáng", " ->[as] "), ("Xúc tác xt", " ->[xt] "),
        ("t°, xt", " ->[t^o, xt] "), ("t°, P, xt", " <=>[t^o, P, xt] "),
        ("Điện phân dd", " ->[dpdd] "), ("Điện phân nc", " ->[dpnc] "),
        ("H₂SO₄ đặc", " ->[H2SO4 dac, t^o] "), ("Men / Enzim", " ->[men] "),
    ],
}

# ==============================================================================
# 4. KHO 65+ HỢP CHẤT & ĐƠN CHẤT (TRA CỨU DANH PHÁP)
# (Formula, IUPAC, Traditional, IPA, Category, MolarMass, Description)
# ==============================================================================

VALENCE_TABLE = [
    ("H, Li, Na, K, Ag, F", "I", "Kim loại kiềm, Silver (Ag), Hydrogen, Fluorine"),
    ("Be, Mg, Ca, Ba, Zn, O", "II", "Kim loại kiềm thổ, Zinc (Zn), Oxygen"),
    ("Al, B", "III", "Aluminium, Boron"),
    ("Fe", "II, III", "Iron (FeO, Fe2O3)"),
    ("Cu, Hg", "I, II", "Copper, Mercury (phổ biến II)"),
    ("C, Si", "II, IV", "Carbon, Silicon (phổ biến IV)"),
    ("N", "I, II, III, IV, V", "Nitrogen (NH3: III; HNO3: V)"),
    ("P", "III, V", "Phosphorus (PH3: III; H3PO4: V)"),
    ("S", "II, IV, VI", "Sulfur (H2S: II; SO2: IV; H2SO4: VI)"),
    ("Cl, Br, I", "I, III, V, VII", "Halogen (phổ biến I trong muối halide)"),
    ("Mn", "II, IV, VI, VII", "Manganese (MnCl2: II; MnO2: IV; KMnO4: VII)"),
    ("Cr", "II, III, VI", "Chromium (Cr2O3: III; K2Cr2O7: VI)"),
    ("Gốc -OH, -NO3, -Cl, -HCO3, -HSO4", "I", "Hydroxide, Nitrate, Chloride, Hydrogencarbonate"),
    ("Gốc =SO4, =SO3, =CO3, =S, =SiO3", "II", "Sulfate, Sulfite, Carbonate, Sulfide, Silicate"),
    ("Gốc ≡PO4", "III", "Phosphate"),
    ("Gốc NH4+", "I", "Ammonium (tương đương kim loại kiềm)"),
]


SOLUBILITY_RULES = [
    ("Muối NO3⁻, CH3COO⁻, Na⁺, K⁺, NH4⁺", "Đều TAN hoàn toàn trong nước."),
    ("Muối Cl⁻, Br⁻, I⁻", "Hầu hết TAN — trừ AgCl, AgBr, AgI, PbCl2 (ít tan)."),
    ("Muối SO4²⁻", "Hầu hết TAN — trừ BaSO4, PbSO4 (không tan); CaSO4, Ag2SO4 (ít tan)."),
    ("Muối CO3²⁻, SO3²⁻, PO4³⁻, SiO3²⁻", "Hầu hết KHÔNG TAN — trừ muối của Na⁺, K⁺, NH4⁺."),
    ("Base (OH⁻)", "Hầu hết KHÔNG TAN — trừ NaOH, KOH, Ba(OH)2, LiOH (tan tốt) và Ca(OH)2 (ít tan)."),
]



# ==============================================================================
# LƯU TRỮ CÀI ĐẶT NGƯỜI DÙNG
# ==============================================================================
def load_user_prefs() -> dict:
    default = {
        "mode": "light",          # light | dark
        "accent": "Chàm",
        "math_favorites": [], "math_recents": [],
        "chem_favorites": [], "chem_recents": [],
        "gemini_key": "",
        "close_action": "ask",     # ask | tray | quit
        "tray_icon": True,
        "geo_files": [],
    }
    if USER_DATA_PATH.exists():
        try:
            data = json.loads(USER_DATA_PATH.read_text(encoding="utf-8"))
            default.update(data)
        except Exception:
            pass
    return default


def save_user_prefs(prefs: dict):
    try:
        USER_DATA_PATH.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
