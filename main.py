# -*- coding: utf-8 -*-
"""Formula Studio v1.0 - by ItzMe_Corniizt
Toán học · Hình học động · Hóa học (IUPAC) · Máy tính khoa học (Song ngữ VI / EN). Chạy: python main.py"""
import os
import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMenu, QMessageBox, QPushButton, QRadioButton, QScrollArea,
                               QStackedWidget, QSystemTrayIcon, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

import data_chem as dc
import data_math as dm
import data_store as ds
import formula_engine as fe
import i18n
import icons
import molecule as mo
from pages_calc import TOOLS as CALC_TOOLS, CalculatorSection
from pages_chem import ChemSection, scroll_wrap
from pages_math import MathSection
from ui_common import ACCENTS, PALETTES, THEME_META, apply_win_titlebar, build_palette, build_qss, esc, is_dark_mode, mk_btn, mk_card, mk_label, mk_sep, shrink_x


def res_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


class Ctx:
    """Ngữ cảnh dùng chung cho các trang: cài đặt, thông báo, phát âm, giỏ Word."""

    def __init__(self, win):
        self.win = win
        self.prefs = ds.load_user_prefs()
        i18n.set_lang(self.prefs.get("lang", "vi"))
        self._speech = None
        self.basket = []
        self.on_basket = None
        self.qss = ""
        self.qss_ver = 0

    def add_basket(self, item):
        self.basket.append(item)
        self.basket_changed()
        self.say(f"Added to Word Document ({len(self.basket)} items)." if i18n.is_en() else f"Đã thêm vào Tài liệu Word ({len(self.basket)} mục).")

    def basket_changed(self):
        if self.on_basket:
            self.on_basket(len(self.basket))

    def open_basket(self):
        from word_ui import WordBasketDialog
        WordBasketDialog(self, self.win).exec()

    @property
    def dark(self):
        return is_dark_mode(self.prefs.get("mode", "light"))

    @property
    def palette(self):
        return PALETTES.get(self.prefs.get("mode", "light"), PALETTES["light"])

    def save_prefs(self):
        ds.save_user_prefs(self.prefs)

    def say(self, msg):
        self.win.statusBar().showMessage(msg, 6000)

    def speak(self, text, rate=1.0):
        if self._speech and self._speech.isRunning():
            self._speech.stop()
        self._speech = fe.SpeechThread(text, rate, self.win)
        self._speech.start()
        self.say(f"Speaking IUPAC pronunciation: {text}" if i18n.is_en() else f"Đang đọc phát âm chuẩn: {text}")


# ==============================================================================
# DỮ LIỆU HƯỚNG DẪN TƯƠNG TÁC TỪNG CHỨC NĂNG
# ==============================================================================
GUIDE_MODULES = [
    (
        "Công thức Toán (LaTeX)",
        "Toán học",
        ("math", 0),
        "Soạn thảo công thức trực quan (WYSIWYG) song song với mã LaTeX, kèm 385+ mẫu có sẵn, thay số tức thì và tính giá trị trực tiếp.",
        [
            ("Chỉnh trực tiếp trên công thức (WYSIWYG)", "Ở chế độ «Trực quan», nhấp trực tiếp vào từng ô phân số/căn/mũ/chỉ số để sửa ngay không cần gõ mã LaTeX. Gõ / tạo phân số, ^ tạo số mũ, _ tạo chỉ số dưới, bấm Tab để nhảy ô."),
            ("Chuyển mượt sang Mã LaTeX khi cần", "Bấm «Mã LaTeX» bất cứ lúc nào để chỉnh cú pháp nâng cao (ma trận, tích phân, tổng Σ, giới hạn lim, hệ phương trình) — hai chế độ tự động đồng bộ 2 chiều."),
            ("Thay số & xuất bản sắc nét", "Nhập số vào thanh Thay số nhanh rồi bấm «Tính giá trị», hoặc xuất ảnh PNG 300 DPI / SVG vector / Equation gốc sang Microsoft Word."),
        ],
        [("/  ^  _  Tab", "Tạo phân số / mũ / chỉ số dưới / chuyển ô trong chế độ Trực quan"), ("Ctrl+B", "Thu gọn thanh bên thành thanh icon để mở rộng vùng làm việc"), ("Quét ảnh", "Dán ảnh chụp màn hình để nhận diện thành công thức")],
        r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}   |   \int_0^{\pi} \sin x\,dx = 2",
    ),
    (
        "Hình học động & Đồ thị",
        "Toán học",
        ("math", 1),
        "Dựng hình động kiểu GeoGebra với dải thu phóng siêu rộng 1%–1250%, 28 hình mẫu 2D/3D có nét đứt, đồ thị tương tác và đo đạc tự động.",
        [
            ("Chọn công cụ ở dock trái", "Hỗ trợ đầy đủ: điểm, đoạn, đường, tia, vectơ, đường tròn 2/3 điểm, đa giác, góc (tự động vẽ ký hiệu góc vuông ∟ 90°), trung điểm, vuông góc, song song, phân giác, trung trực, đối xứng trục/tâm, tiếp tuyến và 4 tâm tam giác."),
            ("Thu phóng siêu rộng 1%–1250% & dò đồ thị", "Cuộn chuột hoặc bấm + / - để thu nhỏ xuống tận 1% (nhìn toàn cảnh hình cực lớn ±1000) hoặc phóng to 1250%; lưới tọa độ tự giãn bước 1-2-5 thông minh. Rê chuột lên đồ thị để dò (x; f(x))."),
            ("Tùy chỉnh nhãn, chú thích & lưu trữ", "Ở chế độ Chọn (V), có thể kéo điểm, kéo tự do tên điểm (A, B…), số đo góc/cạnh và chú thích để không bị đè lên đường thẳng; nhấp đúp để đổi tên/sửa chữ, chuột phải để đặt lại vị trí nhãn hoặc lưu/mở file .geo, xuất PNG/SVG."),
        ],
        [("V / P / S / L / C / G / A / E", "Chọn / Điểm / Đoạn / Đường / Tròn / Đa giác / Góc / Xóa"), ("F / 0 / + / -", "Vừa khít toàn hình / Về gốc O / Phóng to / Thu nhỏ (1%–1250%)"), ("Ctrl+Z / Ctrl+Y / Delete", "Hoàn tác / Làm lại / Xóa đối tượng đang chọn")],
        "y = x^2 - 2x - 3   |   y = sin(x)   |   y = (2x - 1)/(x + 1)",
    ),
    (
        "Phương trình & Cân bằng",
        "Hóa học",
        ("chem", 0),
        "Cân bằng tự động phương trình hóa học (kể cả ion & oxi hóa - khử), tính khối lượng mol M và dựng hình phương trình.",
        [
            ("Cân bằng tức thì", "Gõ phương trình ở dòng Cân bằng (VD: Fe + O2 -> Fe3O4 hoặc phản ứng ion có điện tích) rồi nhấn Enter — hệ thống tự giải hệ bảo toàn nguyên tố và điện tích."),
            ("Ghi điều kiện phản ứng", "Đặt điều kiện trong ngoặc vuông ngay sau mũi tên: ->[t^o], <=>[t^o, P, xt], ->[dpdd, mn]. Dùng bảng ký hiệu nhanh phía dưới để chèn chỉ số, điện tích, mũi tên."),
            ("Tính M & Tra cứu 686 phản ứng", "Nhập công thức bất kỳ (kể cả tinh thể ngậm nước như CuSO4.5H2O) để xem M (g/mol) và % từng nguyên tố, hoặc chọn từ 686 phản ứng đã kiểm chứng."),
        ],
        [("Enter", "Cân bằng ngay / Tính khối lượng mol"), ("->", "Mũi tên một chiều"), ("<=>", "Mũi tên thuận nghịch (cân bằng hóa học)")],
        "KMnO4 + HCl -> KCl + MnCl2 + Cl2 ^ + H2O   |   Fe^{2+} + MnO4^- + H^+ -> Fe^{3+} + Mn^{2+} + H2O",
    ),
    (
        "Cấu trúc SMILES 2D",
        "Hóa học",
        ("chem", 1),
        "Chuyển đổi tên chuẩn IUPAC, công thức thu gọn hoặc mã SMILES thành hình vẽ cấu trúc phân tử 2D chuẩn hóa trị.",
        [
            ("Nhập linh hoạt", "Gõ tên chuẩn IUPAC (Aspirin, Caffeine, Ethanol, Nitrogen dioxide…), công thức thu gọn (CH3COOH, CH3CH(OH)CH3) hoặc mã SMILES bất kỳ."),
            ("Phân tích tự động", "Hệ thống tự hiển thị CTPT, khối lượng mol M, số nguyên tử, số liên kết, số vòng, mã SMILES chuẩn và gợi ý đồng phân."),
            ("Chuyển sang Trình vẽ", "Bấm «Chỉnh sửa ở Trình vẽ» để đưa ngay phân tử sang canvas tương tác, thêm nhóm chức hoặc liên kết lập thể."),
        ],
        [("307 mẫu phân tử", "Chọn nhanh theo nhóm chất chuẩn IUPAC"), ("Nền Trong suốt / Trắng / Tối", "Tùy chọn nền xuất ảnh PNG 300 DPI / SVG")],
        "CC(=O)Oc1ccccc1C(=O)O (Aspirin)   |   CH3CH(OH)COOH (Lactic acid)",
    ),
    (
        "Trình vẽ Phân tử (ChemDraw)",
        "Hóa học",
        ("chem", 2),
        "Trình vẽ cấu trúc hóa học 3 cột hỗ trợ liên kết lập thể nêm đặc/nêm đứt, phím tắt đổi nguyên tố siêu nhanh và chuẩn hóa bố cục.",
        [
            ("Vẽ nhanh bằng dock trái", "Chọn liên kết Đơn (1), Đôi (2), Ba (3), Nêm đặc (4), Nêm đứt (5) hoặc chọn 1-click nguyên tố (C, H, N, O, S, P, F, Cl, Br, I…) và vòng (Benzene, C₆, C₅…). Khi rê chuột sẽ thấy bóng mờ vị trí ghép vòng và góc xoay 15°."),
            ("Đổi nguyên tố không cần rời chuột", "Rê chuột lên nguyên tử bất kỳ rồi nhấn trực tiếp phím C, N, O, S, P, F, B, H, I, L (Cl), R (Br); rê lên liên kết rồi nhấn 1–5 để đổi loại liên kết."),
            ("Di chuyển, chọn vùng, xóa vùng & chuẩn hóa", "Dùng công cụ Di chuyển (H) để kéo trượt vùng vẽ; ở chế độ Chọn (V) kéo khoanh nhiều nguyên tử; ở chế độ Xóa (E) nhấp để xóa 1 đối tượng hoặc kéo khung chọn vùng để xóa hàng loạt; bấm «Chuẩn hóa» để dàn bố cục 2D đẹp chuẩn góc."),
        ],
        [("1 / 2 / 3 / 4 / 5", "Đơn / Đôi / Ba / Nêm đặc ▸ / Nêm đứt ┄"), ("C N O S P F B H I L R", "Đổi nhanh nguyên tử đang rê chuột (L=Cl, R=Br)"), ("Space / Ctrl+A / Chuột phải", "Căn giữa vừa khung / Chọn hết / Menu ngữ cảnh")],
        "Nhấp chọn Benzene → Nhấp canvas → Bấm chọn nhóm OH / COOH → Nhấp lên đỉnh vòng",
    ),
    (
        "Bảng tuần hoàn & Tra cứu 705 chất",
        "Hóa học",
        ("chem", 3),
        "Bảng tuần hoàn 118 nguyên tố chuẩn IUPAC kèm mô hình Bohr, sơ đồ ô orbital ↑↓ và kho tra cứu 705 hợp chất vô cơ – hữu cơ.",
        [
            ("Bảng tuần hoàn 118 nguyên tố", "Nhấp vào bất kỳ nguyên tố nào để xem tên chuẩn quốc tế IUPAC, phiên âm IPA, cấu hình electron rút gọn/đầy đủ, số e độc thân, mô hình Bohr và sơ đồ ô orbital ↑↓ (xuất SVG/PNG)."),
            ("Nghe phát âm chuẩn quốc tế", "Bấm «Nghe phát âm IUPAC» (có tùy chỉnh tốc độ 0.75× / 1.0× / 1.25× hoặc bật Tự đọc) để luyện đọc tên nguyên tố và hợp chất."),
            ("Bách khoa 705 hợp chất IUPAC & ★ Đã Lưu", "Mỗi chất trình bày đầy đủ như Wiki (lí tính, hóa tính, % nguyên tố, ứng dụng, phương trình điều chế & phản ứng liên quan bấm mở thẳng sang tab Cân bằng). Bấm «Đánh dấu sao» để lưu chất vào danh sách ★ Đã Lưu."),
        ],
        [("Tìm kiếm thông minh", "Gõ Z, ký hiệu (Fe, Cu), tên IUPAC (Nitrogen dioxide) hoặc tên thường gọi (xút, vôi tôi)"), ("Xuất ảnh bảng", "Xuất toàn bộ Bảng tuần hoàn 118 nguyên tố sắc nét ra PNG")],
        "Nitrogen dioxide (NO₂) · Sulfuric acid (H₂SO₄) · Sodium hydroxide · Aspirin · Caffeine",
    ),
    (
        "Máy tính khoa học (43 bộ giải)",
        "Máy tính",
        ("calc", 0),
        "Màn hình hiển thị công thức tự nhiên (phân số, căn, lũy thừa) cùng 43 công cụ giải toán & hóa học có lời giải từng bước.",
        [
            ("Nhập biểu thức tự nhiên", "Dùng bàn phím ảo hoặc gõ trực tiếp: / tạo phân số, ^ tạo số mũ, sqrt( tạo căn. Bấm S⇔D để chuyển đổi giữa dạng chính xác (phân số/căn/π) và thập phân."),
            ("Lưu biến nhớ & xuất Word", "Dùng nút →A, →B ngay trên màn hình LCD để lưu nhanh kết quả vào biến nhớ, hoặc bấm «Word» để đưa kết quả vào tài liệu."),
            ("Tìm nhanh trong 43 công cụ giải", "Gõ từ khóa vào ô «Tìm nhanh công cụ» ở góc trên phải để nhảy tức thì tới Giải phương trình bậc 1–10, Hệ 2–4 ẩn, Đạo hàm, Tích phân, Ma trận, Thống kê, Giải tam giác, Tính pH & Pha loãng dung dịch."),
        ],
        [("Enter / =", "Tính kết quả và lưu lịch sử"), ("◀ ▶ ▲ ▼", "Di chuyển con trỏ giữa các ô công thức"), ("SHIFT", "Mở chức năng phụ (sin⁻¹, ∛, eˣ, |x|, nPr…)")],
        "2*sin(30) + sqrt(144)/3   |   Tìm công cụ: «bậc 2», «tích phân», «pH», «ma trận»",
    ),
    (
        "Tài liệu Word & Quét ảnh OCR",
        "Tiện ích",
        ("settings", 0),
        "Xuất trực tiếp công thức Toán/Hóa thành Equation gốc của Word và quét ảnh chụp màn hình thành LaTeX / SMILES.",
        [
            ("Gom vào Tài liệu Word", "Trên mọi trang, bấm nút «Word» để chèn ngay vào cửa sổ Microsoft Word đang mở (cần pywin32) hoặc thêm vào giỏ «Tài liệu Word» ở góc dưới trái."),
            ("Xuất file .docx chuyên nghiệp", "Mở «Tài liệu Word» để sắp xếp thứ tự các mục, sau đó xuất ra file .docx — công thức Toán & Phương trình Hóa học trở thành Equation gốc sửa được trong Word, còn hình vẽ/phân tử là ảnh sắc nét."),
            ("Quét ảnh công thức (OCR)", "Dán khóa Gemini API miễn phí trong tab Cài đặt (chỉ lưu cục bộ trên máy bạn) để dùng nút «Quét ảnh» nhận diện công thức từ ảnh chụp màn hình."),
        ],
        [("Ctrl+D", "Chuyển nhanh chế độ Sáng / Tối"), ("Ctrl+1..4", "Chuyển nhanh 4 không gian làm việc")],
        "Chụp màn hình (Win+Shift+S) → Bấm «Quét ảnh» → Dán ảnh → Nhận diện",
    ),
]


GUIDE_MODULES_EN = [
    (
        "Math Formulas (LaTeX)",
        "Mathematics",
        ("math", 0),
        "Visual WYSIWYG formula editing synced with LaTeX code, 385+ built-in templates, instant variable substitution, and Word Equation export.",
        [
            ("Direct Visual Editing (WYSIWYG)", "In Visual mode, click directly inside fractions, roots, powers, subscripts, integrals, or matrices to edit naturally. Type / for fractions, ^ for superscripts, _ for subscripts, and Tab to jump slots."),
            ("Seamless LaTeX Code Sync", "Switch to LaTeX Code at any time for full syntax control — both Visual and LaTeX modes stay automatically synchronized in real time."),
            ("Quick Substitute & High-DPI Export", "Enter numbers in the Quick Substitute bar and click Evaluate, or export crisp 300 DPI PNG, scalable SVG, or native editable Microsoft Word Equations."),
        ],
        [("/  ^  _  Tab", "Fraction / power / subscript / jump slot in Visual mode"), ("Ctrl+B", "Collapse sidebar into compact icon rail"), ("Scan OCR", "Paste a screenshot to convert math images into LaTeX")],
        r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}   |   \int_0^{\pi} \sin x\,dx = 2",
    ),
    (
        "Dynamic Geometry & Graphs",
        "Mathematics",
        ("math", 1),
        "GeoGebra-style interactive geometry with 1%–1250% zoom, 28 2D/3D preset figures, live intersection snapping, draggable labels, and function graphing.",
        [
            ("Full Geometric Constructions", "Construct points, segments, lines, rays, vectors, circles, polygons, angles (auto 90° right-angle symbol), midpoints, perpendiculars, parallels, bisectors, reflections, tangents, and all 4 triangle centers."),
            ("Wide 1%–1250% Zoom & Graph Trace", "Scroll or press +/- to zoom smoothly from 1% (±1000) to 1250% with adaptive 1-2-5 grid steps. Hover any plotted curve y = f(x) to inspect live coordinates."),
            ("Draggable Labels, Notes & Save", "In Select mode (V), drag points, point labels (A, B…), angle/length measurements, and text notes so nothing overlaps lines. Double-click to edit, right-click to reset label position, or save .geo / PNG / SVG."),
        ],
        [("V / P / S / L / C / G / A / E", "Select / Point / Segment / Line / Circle / Polygon / Angle / Erase"), ("F / 0 / + / -", "Fit view / Center Origin O / Zoom in / Zoom out"), ("Ctrl+Z / Ctrl+Y / Delete", "Undo / Redo / Delete selected item")],
        "y = x^2 - 2x - 3   |   y = sin(x)   |   y = (2x - 1)/(x + 1)",
    ),
    (
        "Chemical Equations & Balancer",
        "Chemistry",
        ("chem", 0),
        "Automatic chemical equation balancer (including redox and ionic equations), molar mass calculator, and 686+ verified reactions.",
        [
            ("Instant Equation Balancing", "Type any unbalanced equation (e.g. Fe + O2 -> Fe3O4 or ionic equations with charges) and press Enter — the solver balances atoms and charges automatically."),
            ("Reaction Conditions & Symbols", "Write conditions in brackets right after the arrow: ->[t^o], <=>[t^o, P, xt]. Use the quick symbol tabs below for subscripts, charges, states, and arrows."),
            ("Molar Mass & 686 Reactions", "Compute exact molar mass M (g/mol) and elemental % (including hydrates like CuSO4.5H2O), or search 686 built-in balanced reactions."),
        ],
        [("Enter", "Balance equation / Compute molar mass"), ("->", "Irreversible reaction arrow"), ("<=>", "Reversible equilibrium arrow")],
        "KMnO4 + HCl -> KCl + MnCl2 + Cl2 ^ + H2O   |   Fe^{2+} + MnO4^- + H^+ -> Fe^{3+} + Mn^{2+} + H2O",
    ),
    (
        "2D SMILES Structure Renderer",
        "Chemistry",
        ("chem", 1),
        "Convert IUPAC names, condensed formulas, or SMILES strings into publication-ready valence-checked 2D molecular structures.",
        [
            ("Flexible Input", "Enter an IUPAC name (Aspirin, Caffeine, Ethanol, Nitrogen dioxide…), condensed formula (CH3COOH), or SMILES notation."),
            ("Automatic Analysis", "Instantly displays molecular formula, molar mass M, atom/bond/ring counts, canonical SMILES, and matching isomers."),
            ("Send to Molecule Sketcher", "Click 'Open Sketcher' to load the molecule into the interactive 2D editor to add functional groups or stereobonds."),
        ],
        [("307 Molecule Presets", "Searchable dropdowns grouped by IUPAC class"), ("Transparent / White / Dark", "Export crisp 300 DPI PNG or vector SVG")],
        "CC(=O)Oc1ccccc1C(=O)O (Aspirin)   |   CH3CH(OH)COOH (Lactic acid)",
    ),
    (
        "Molecule Sketcher (ChemDraw-Style)",
        "Chemistry",
        ("chem", 2),
        "3-column interactive molecule editor with wedge/dash stereobonds, fast element hotkeys, hand pan tool, drag-box region erase, and 2D layout cleaning.",
        [
            ("Fast Drawing from Left Dock", "Select Single (1), Double (2), Triple (3), Wedge (4), or Dash (5) bonds, 1-click elements, and quick rings (Benzene, C₆, C₅…) with live snap ghost previews."),
            ("Instant Element Hotkeys", "Hover any atom and press C, N, O, S, P, F, B, H, I, L (Cl), or R (Br) to change its element; hover any bond and press 1–5 to change bond type."),
            ("Pan, Region Select, Box-Erase & Clean 2D", "Use Pan View (H) to slide the canvas freely; in Erase mode (E), click to delete one item or drag a box to delete a region; click 'Clean 2D' for publication-ready bond angles."),
        ],
        [("1 / 2 / 3 / 4 / 5", "Single / Double / Triple / Wedge / Dash bond"), ("H / V / E", "Pan View / Select / Click & Box Erase"), ("Space / Ctrl+A / Right-Click", "Center view / Select all / Context menu")],
        "Click Benzene → Click canvas → Pick OH or COOH group → Click ring vertex",
    ),
    (
        "Periodic Table & 705-Compound Wiki",
        "Chemistry",
        ("chem", 3),
        "IUPAC 118-element Periodic Table with Bohr & orbital box diagrams, audio pronunciation, and a 705-compound Chemistry Wiki with ★ Bookmarked lists.",
        [
            ("118-Element Periodic Table", "Click any element to view IUPAC name, IPA pronunciation, condensed/full electron configuration, unpaired electrons, Bohr model, and ↑↓ orbital box diagram."),
            ("IUPAC Audio Pronunciation", "Click 'Play IUPAC Audio' (0.75× / 1.0× / 1.25× speed or Auto-speak) to practice standard international pronunciation."),
            ("705-Compound Chemistry Wiki & ★ Bookmarked", "Read full Wikipedia-style profiles (properties, mass % bars, applications, preparation & related reactions clickable straight to the Balancer) and click 'Bookmark' to save to ★ Bookmarked."),
        ],
        [("Smart Search", "Search by Z, symbol (Fe), IUPAC name (Nitrogen dioxide), or formula"), ("Export Table PNG", "Save a high-resolution PNG of the entire 118-element Periodic Table")],
        "Nitrogen dioxide (NO₂) · Sulfuric acid (H₂SO₄) · Sodium hydroxide · Aspirin · Caffeine",
    ),
    (
        "Scientific Calculator (43 Solvers)",
        "Calculator",
        ("calc", 0),
        "Natural textbook display (fractions, roots, powers) paired with 43 step-by-step solvers across algebra, calculus, matrices, statistics, geometry, and chemistry.",
        [
            ("Natural Math Input", "Use the keypad or keyboard: / for fractions, ^ for powers, sqrt( for roots. Press S⇔D to toggle exact form (fractions/radicals/π) and decimals."),
            ("Memory & Word Export", "Use →A and →B right on the display to store results in variables, or click 'Word' to export equations directly to your document."),
            ("Quick Search 43 Solvers", "Use the searchable Quick Find box to jump straight to Polynomials, 2–4 Variable Systems, Derivatives, Integrals, Matrices, Statistics, Triangle Solver, Solution pH, and Dilution."),
        ],
        [("Enter / =", "Evaluate expression and save to history"), ("◀ ▶ ▲ ▼", "Navigate smoothly between visual math slots"), ("SHIFT", "Access secondary functions (sin⁻¹, ∛, eˣ, |x|, nPr…)")],
        "2*sin(30) + sqrt(144)/3   |   Quick Find: quadratic, integral, pH, matrix",
    ),
    (
        "Word Export & Formula OCR",
        "Utilities",
        ("settings", 0),
        "Insert native editable Microsoft Word Equations (.docx) and scan screenshots into LaTeX or SMILES using Gemini AI.",
        [
            ("Collect into Word Document", "Click the 'Word' button on any tab to insert directly into an open Microsoft Word window or collect items in the 'Word Document' basket."),
            ("Export Clean .docx Files", "Open 'Word Document' from the sidebar to reorder items and export .docx — math and chemical equations become native editable Word Equations."),
            ("Image OCR Setup", "Paste a free Gemini API key in Settings (stored locally on your device only) to enable 'Scan OCR' across Math, Chemistry, and SMILES."),
        ],
        [("Ctrl+D", "Toggle Light / Dark theme"), ("Ctrl+1..4", "Switch between the 4 workspaces")],
        "Capture screenshot (Win+Shift+S) → Click 'Scan OCR' → Paste → Recognize",
    ),
]


GUIDE_NAV_VI = [
    "Công Thức Toán",
    "Hình Học & Đồ Thị",
    "Phương Trình Hóa",
    "Cấu Trúc SMILES 2D",
    "Trình Vẽ Phân Tử",
    "Bảng Tuần Hoàn & Wiki",
    "Máy Tính Khoa Học",
    "Xuất Word & Quét OCR",
]

GUIDE_NAV_EN = [
    "Math Formulas",
    "Dynamic Geometry",
    "Equations & Balancer",
    "SMILES 2D Renderer",
    "Molecule Sketcher",
    "Periodic Table & Wiki",
    "Scientific Calculator",
    "Word Export & OCR",
]


def _render_guide_html(mod, dark: bool, accent: str) -> str:
    en = i18n.is_en()
    title, cat, _, summary, steps, shortcuts, example = mod
    fg = "#F1F5F9" if dark else "#0F172A"
    muted = "#94A3B8" if dark else "#475569"
    card_bg = "#1E293B" if dark else "#F8FAFC"
    border = "#334155" if dark else "#E2E8F0"
    kbd_bg = "#0F172A" if dark else "#FFFFFF"
    code_bg = "#0B1120" if dark else "#EEF2FF"

    step_rows = []
    for idx, (st_title, st_body) in enumerate(steps, 1):
        step_rows.append(
            f"<tr>"
            f"<td width='34' valign='top' style='padding:6px 4px;'>"
            f"<div style='background:{accent}; color:#FFFFFF; font-weight:800; font-size:12px; "
            f"width:24px; height:24px; line-height:24px; text-align:center; border-radius:12px;'>{idx}</div></td>"
            f"<td style='padding:5px 6px;'>"
            f"<div style='font-weight:700; color:{fg}; font-size:13.5px; margin-bottom:2px;'>{st_title}</div>"
            f"<div style='color:{muted}; font-size:12.5px; line-height:1.45;'>{st_body}</div></td>"
            f"</tr>"
        )

    sc_rows = []
    for key, desc in shortcuts:
        sc_rows.append(
            f"<tr>"
            f"<td style='padding:5px 8px; white-space:nowrap;'>"
            f"<span style='background:{kbd_bg}; border:1px solid {border}; padding:2px 7px; border-radius:5px; "
            f"font-family:Consolas,monospace; font-size:12px; font-weight:700; color:{accent};'>{key}</span></td>"
            f"<td style='padding:5px 8px; color:{fg}; font-size:12.5px;'>{desc}</td>"
            f"</tr>"
        )

    h_steps = "QUICK START STEPS" if en else "QUY TRÌNH THAO TÁC NHANH"
    h_keys = "SHORTCUTS &amp; TIPS" if en else "PHÍM TẮT &amp; MẸO HAY"
    h_ex = "TRY THIS EXAMPLE" if en else "VÍ DỤ THỬ NGAY"
    return f"""
    <div style='color:{fg}; font-family:"Segoe UI",sans-serif;'>
        <div style='font-size:13.5px; color:{muted}; line-height:1.5; margin-bottom:14px;'>{summary}</div>

        <div style='font-size:11px; font-weight:800; letter-spacing:0.8px; color:{accent}; margin-bottom:6px;'>{h_steps}</div>
        <table width='100%' cellspacing='0' cellpadding='4' style='background:{card_bg}; border:1px solid {border}; border-radius:10px; padding:6px; margin-bottom:14px;'>
            {''.join(step_rows)}
        </table>

        <div style='font-size:11px; font-weight:800; letter-spacing:0.8px; color:{accent}; margin-bottom:6px;'>{h_keys}</div>
        <table width='100%' cellspacing='0' cellpadding='3' style='background:{card_bg}; border:1px solid {border}; border-radius:10px; padding:4px; margin-bottom:14px;'>
            {''.join(sc_rows)}
        </table>

        <div style='font-size:11px; font-weight:800; letter-spacing:0.8px; color:{accent}; margin-bottom:6px;'>{h_ex}</div>
        <div style='background:{code_bg}; border:1px solid {border}; border-radius:8px; padding:9px 12px; font-family:Consolas,monospace; font-size:12.5px; color:{fg};'>
            {example}
        </div>
    </div>
    """


class SettingsPage(QWidget):
    def __init__(self, ctx, win, parent=None):
        super().__init__(parent)
        self.ctx, self.win = ctx, win
        self.swatch_btns = {}
        self.guide_btns = []
        self.cur_guide = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._settings_tab(), "Cài đặt")
        self.tabs.addTab(self._guide_tab(), "Hướng dẫn trực quan")
        self.tabs.addTab(self._about_tab(), "Giới thiệu")
        lay.addWidget(self.tabs)

    # ------------------------------------------------------------- 1. Cài đặt
    def _settings_tab(self):
        ctx, win = self.ctx, self.win
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(2, 8, 10, 12)
        lay.setSpacing(12)

        # 1. Ngôn ngữ hiển thị (Tiếng Việt / English)
        lc = mk_card(QVBoxLayout(), margins=(16, 14, 16, 14), spacing=10)
        lh = QHBoxLayout()
        lh.setSpacing(8)
        lh.addWidget(shrink_x(mk_label("NGÔN NGỮ HIỂN THỊ (LANGUAGE)", "caption")), 1)
        self.lbl_lang_badge = mk_label("", "badge")
        self.lbl_lang_badge.setProperty("_i18n_skip", True)
        lh.addWidget(self.lbl_lang_badge)
        lc.layout().addLayout(lh)
        lc.layout().addWidget(shrink_x(mk_label("Chọn ngôn ngữ giao diện ứng dụng (áp dụng tức thì)", "muted", True)))
        lrow = QHBoxLayout()
        lrow.setSpacing(10)
        self.lang_btns = {}
        for lkey, ltxt in (("vi", "Tiếng Việt (VN)"), ("en", "English (EN)")):
            lb = shrink_x(mk_btn(ltxt, checkable=True, prop=("themecard", True)))
            lb.setProperty("_i18n_skip", True)
            lb.setMinimumHeight(44)
            lb.clicked.connect(lambda _, lk=lkey: win.set_lang(lk))
            self.lang_btns[lkey] = lb
            lrow.addWidget(lb, 1)
        lc.layout().addLayout(lrow)
        lay.addWidget(lc)

        # 2. Giao diện 4 chủ đề Studio + 8 Swatch màu nhấn trực quan
        s = mk_card(QVBoxLayout(), margins=(16, 14, 16, 14), spacing=10)
        s.layout().addWidget(shrink_x(mk_label("GIAO DIỆN & CHỦ ĐỀ MÀU SẮC", "caption")))
        s.layout().addWidget(shrink_x(mk_label("Chọn chủ đề giao diện (chuyển tức thì, đồng bộ thanh tiêu đề Windows)", "muted", True)))

        self.theme_btns = {}
        t_grid = QGridLayout()
        t_grid.setHorizontalSpacing(10)
        t_grid.setVerticalSpacing(8)
        for idx, (key, title, desc, is_d, bg_h, card_h, dot_h) in enumerate(THEME_META):
            b = shrink_x(mk_btn(f"  {title}\n  {desc}", checkable=True, prop=("themecard", True)))
            b.setIconSize(QSize(20, 20))
            b.setMinimumHeight(58)
            b.setProperty("_theme_dark", is_d)
            b.clicked.connect(lambda _, k=key: win.set_theme(k))
            self.theme_btns[key] = b
            t_grid.addWidget(b, idx // 2, idx % 2)
        s.layout().addLayout(t_grid)

        s.layout().addWidget(mk_sep())
        s.layout().addWidget(shrink_x(mk_label("Màu nhấn chủ đạo (Accent Color)", "h2", True)))
        sw_grid = QGridLayout()
        sw_grid.setHorizontalSpacing(8)
        sw_grid.setVerticalSpacing(8)
        for idx, (name, acc_t) in enumerate(ACCENTS.items()):
            col = acc_t[0]
            b = shrink_x(mk_btn(f"●  {name}", checkable=True, prop=("subtle", True)))
            b.setMinimumHeight(34)
            b.setProperty("_acc_hex", col)
            b.clicked.connect(lambda _, n=name: win.set_theme(None, n))
            self.swatch_btns[name] = b
            sw_grid.addWidget(b, idx // 4, idx % 4)
        s.layout().addLayout(sw_grid)
        lay.addWidget(s)

        # 3. Cửa sổ & khay hệ thống
        t = mk_card(QVBoxLayout(), margins=(16, 14, 16, 14), spacing=9)
        t.layout().addWidget(shrink_x(mk_label("CỬA SỔ & KHAY HỆ THỐNG", "caption")))
        self.chk_tray = shrink_x(QCheckBox("Hiện biểu tượng Formula Studio ở khay hệ thống (System Tray)"))
        self.chk_tray.setChecked(bool(ctx.prefs.get("tray_icon", True)))
        self.chk_tray.stateChanged.connect(self._tray_changed)
        t.layout().addWidget(self.chk_tray)
        close_box = QFrame()
        close_box.setProperty("panel", True)
        cbl = QVBoxLayout(close_box)
        cbl.setContentsMargins(12, 9, 12, 9)
        cbl.setSpacing(6)
        cbl.addWidget(shrink_x(mk_label("Hành động khi nhấn nút đóng cửa sổ (X):", "muted", True)))
        self.rb = {}
        for key, text in (
            ("ask", "Hỏi mỗi lần"),
            ("tray", "Thu nhỏ xuống khay hệ thống (ứng dụng vẫn chạy nền)"),
            ("quit", "Thoát hẳn ứng dụng"),
        ):
            rb = shrink_x(QRadioButton(text))
            rb.toggled.connect(lambda on, k=key: on and self._close_changed(k))
            self.rb[key] = rb
            cbl.addWidget(rb)
        self.rb.get(ctx.prefs.get("close_action", "ask"), self.rb["ask"]).setChecked(True)
        t.layout().addWidget(close_box)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            t.layout().addWidget(shrink_x(mk_label("Hệ thống này không hỗ trợ khay hệ thống; nút đóng sẽ thoát ứng dụng.", "muted", True)))
        lay.addWidget(t)

        # 4. Quét ảnh OCR
        k = mk_card(QVBoxLayout(), margins=(16, 14, 16, 14), spacing=9)
        kh = QHBoxLayout()
        kh.setSpacing(8)
        kh.addWidget(shrink_x(mk_label("QUÉT ẢNH CÔNG THỨC (OCR)", "caption")), 1)
        self.lbl_key_st = mk_label("", "badge_ok" if ctx.prefs.get("gemini_key") else "badge_muted")
        kh.addWidget(self.lbl_key_st)
        k.layout().addLayout(kh)
        k.layout().addWidget(shrink_x(mk_label("Dán khóa Gemini API (tạo miễn phí tại aistudio.google.com/apikey) để dùng nút «Quét ảnh» ở các trang Toán, Phương trình hóa học và SMILES. Khóa chỉ lưu cục bộ trên máy này.", "muted", True)))
        kr = QHBoxLayout()
        kr.setSpacing(8)
        self.key = shrink_x(QLineEdit(ctx.prefs.get("gemini_key", "")))
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("AIza…")
        self.key.editingFinished.connect(self._save_key)
        kr.addWidget(self.key, 1)
        self.b_eye = mk_btn("Hiện", checkable=True, prop=("subtle", True))
        self.b_eye.setProperty("_i18n_skip", True)
        self.b_eye.toggled.connect(self._toggle_key_vis)
        kr.addWidget(self.b_eye)
        b_savek = mk_btn("Lưu khóa", primary=True)
        b_savek.clicked.connect(self._save_key)
        kr.addWidget(b_savek)
        k.layout().addLayout(kr)
        lay.addWidget(k)
        lay.addStretch(1)

        self._update_key_badge()
        self.sync()
        sc = scroll_wrap(body)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return sc

    def _toggle_key_vis(self, on: bool):
        self.key.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
        if i18n.is_en():
            self.b_eye.setText("Hide" if on else "Show")
        else:
            self.b_eye.setText("Ẩn" if on else "Hiện")

    def _save_key(self):
        self.ctx.prefs["gemini_key"] = self.key.text().strip()
        self.ctx.save_prefs()
        self._update_key_badge()
        self.ctx.say("Saved Gemini API key." if i18n.is_en() else "Đã lưu Gemini API key.")

    def _update_key_badge(self):
        has = bool(self.ctx.prefs.get("gemini_key", "").strip())
        self.lbl_key_st.setProperty("_i18n_skip", True)
        self.lbl_key_st.setText(("Configured" if has else "Not set") if i18n.is_en() else ("Đã cấu hình" if has else "Chưa nhập khóa"))
        if hasattr(self, "lbl_lang_badge"):
            self.lbl_lang_badge.setText("English (EN)" if i18n.is_en() else "Tiếng Việt (VN)")
        if hasattr(self, "b_eye"):
            self._toggle_key_vis(self.b_eye.isChecked())

    def _tray_changed(self, state):
        self.ctx.prefs["tray_icon"] = bool(state)
        self.ctx.save_prefs()
        self.win.update_tray()

    def _close_changed(self, key):
        self.ctx.prefs["close_action"] = key
        self.ctx.save_prefs()
        if key == "tray" and not self.chk_tray.isChecked():
            self.chk_tray.setChecked(True)

    # ------------------------------------------------------------- 2. Hướng dẫn trực quan
    def _guide_tab(self):
        w = QWidget()
        root = QHBoxLayout(w)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(10)

        # Cột trái: mục lục 8 tính năng (đủ rộng để không bao giờ bị cắt chữ ở VI & EN)
        nav_card = mk_card(QVBoxLayout(), margins=(10, 12, 10, 12), spacing=4)
        nav_card.setFixedWidth(256)
        nav_card.layout().addWidget(shrink_x(mk_label("DANH MỤC TÍNH NĂNG", "caption")))
        nav_card.layout().addSpacing(4)
        for idx, mod in enumerate(GUIDE_MODULES):
            b = shrink_x(mk_btn(f"{idx + 1}.  {GUIDE_NAV_VI[idx]}", checkable=True, prop=("guideitem", True)))
            b.clicked.connect(lambda _, i=idx: self.show_guide(i))
            nav_card.layout().addWidget(b)
            self.guide_btns.append(b)
        nav_card.layout().addStretch(1)
        root.addWidget(nav_card)

        # Cột phải: thẻ hướng dẫn trực quan + nút mở ngay
        detail = mk_card(QVBoxLayout(), margins=(16, 14, 16, 14), spacing=10)
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        hcol = QVBoxLayout()
        hcol.setSpacing(3)
        self.g_cat = mk_label("", "badge")
        self.g_cat.setSizePolicy(self.g_cat.sizePolicy().horizontalPolicy(), self.g_cat.sizePolicy().verticalPolicy())
        self.g_title = shrink_x(mk_label("", "h1", True))
        hrow = QHBoxLayout()
        hrow.setSpacing(8)
        hrow.addWidget(self.g_title, 1)
        hrow.addWidget(self.g_cat, 0, Qt.AlignVCenter)
        hcol.addLayout(hrow)
        hdr.addLayout(hcol, 1)
        self.b_open_feat = mk_btn("Mở tính năng →", primary=True)
        self.b_open_feat.clicked.connect(self._jump_guide_target)
        hdr.addWidget(self.b_open_feat, 0, Qt.AlignVCenter)
        detail.layout().addLayout(hdr)
        detail.layout().addWidget(mk_sep())

        self.g_browser = QTextBrowser()
        self.g_browser.setFrameShape(QFrame.NoFrame)
        self.g_browser.setOpenExternalLinks(True)
        detail.layout().addWidget(self.g_browser, 1)
        root.addWidget(detail, 1)

        self.show_guide(0)
        return w

    def show_guide(self, idx: int):
        self.cur_guide = idx
        en = i18n.is_en()
        mods = GUIDE_MODULES_EN if en else GUIDE_MODULES
        navs = GUIDE_NAV_EN if en else GUIDE_NAV_VI
        for i, b in enumerate(self.guide_btns):
            b.setProperty("_i18n_skip", True)
            b.setText(esc(f"{i + 1}.  {navs[i]}"))
            b.setToolTip(i18n.smart_title(mods[i][0]))
            b.setChecked(i == idx)
        mod = mods[idx]
        self.g_title.setProperty("_i18n_skip", True)
        self.g_cat.setProperty("_i18n_skip", True)
        self.g_title.setText(i18n.smart_title(mod[0]))
        self.g_cat.setText(i18n.smart_title(mod[1]))
        acc = ACCENTS.get(self.ctx.prefs.get("accent", "Chàm"), ACCENTS["Chàm"])[0]
        self.g_browser.setHtml(_render_guide_html(mod, self.ctx.dark, acc))

    def _jump_guide_target(self):
        sec_key, tab_idx = GUIDE_MODULES[self.cur_guide][2]
        self.win.jump_to(sec_key, tab_idx)

    # ------------------------------------------------------------- 3. Giới thiệu chuyên nghiệp
    def _about_tab(self):
        import sys as _s
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 8, 4, 8)
        lay.setSpacing(12)

        # Hero Banner
        hero = QFrame()
        hero.setProperty("hero", True)
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(20, 18, 20, 18)
        hl.setSpacing(18)
        logo = QLabel()
        logo.setFixedSize(82, 82)
        pm = QPixmap(res_path("assets/logo_tile.png")).scaled(82, 82, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pm)
        hl.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(5)
        trow = QHBoxLayout()
        trow.setSpacing(8)
        trow.addWidget(mk_label(f"{ds.APP_NAME} {ds.APP_VERSION}", "h1"))
        trow.addWidget(mk_label("IUPAC 2018", "badge"))
        trow.addWidget(mk_label("Offline-First", "badge_ok"))
        trow.addStretch()
        col.addLayout(trow)
        self.lbl_about_sub = mk_label(f"Phát triển bởi {ds.APP_AUTHOR.replace('by ', '')}  ·  Bộ công cụ khoa học toàn diện cho học tập, giảng dạy và biên soạn tài liệu.", "muted", True)
        self.lbl_about_sub.setProperty("_i18n_skip", True)
        self.lbl_about_desc = mk_label("Tích hợp đầy đủ Soạn công thức LaTeX, Hình học động & Đồ thị, Cân bằng phản ứng, Trình vẽ phân tử 2D lập thể, Bảng tuần hoàn 118 nguyên tố và Máy tính khoa học 43 bộ giải.", None, True)
        self.lbl_about_desc.setProperty("_i18n_skip", True)
        col.addWidget(self.lbl_about_sub)
        col.addWidget(self.lbl_about_desc)
        hl.addLayout(col, 1)
        lay.addWidget(hero)

        # 6 KPI Tiles (3x2)
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)
        kpis = [
            (f"{len(dc.COMPOUNDS)}+", "Hợp chất chuẩn IUPAC", "Vô cơ, hữu cơ, dược phẩm, amino acid"),
            (f"{len(dc.REACTIONS)}+", "Phản ứng cân bằng", "Đầy đủ điều kiện & kiểm chứng tự động"),
            (f"{len(dm.MATH_SAMPLES)}+", "Công thức Toán · Lí · Hóa", "Thay số trực tiếp & xuất Word equation"),
            ("118", "Nguyên tố hóa học", "Bohr, ô orbital ↑↓ & phát âm IPA chuẩn"),
            (f"{len(dc.SMILES_PRESETS)}+", "Cấu trúc 2D SMILES", "Vẽ lập thể nêm đặc/đứt, xuất PNG & SVG"),
            (f"{len(CALC_TOOLS)}", "Bộ giải Máy tính", "Phương trình, tích phân, ma trận, pH…"),
        ]
        for idx, (num_txt, lbl_txt, sub_txt) in enumerate(kpis):
            tile = QFrame()
            tile.setProperty("kpi", True)
            tl = QVBoxLayout(tile)
            tl.setContentsMargins(16, 12, 16, 12)
            tl.setSpacing(2)
            tl.addWidget(mk_label(num_txt, "kpi_num"))
            tl.addWidget(mk_label(lbl_txt, "h2"))
            tl.addWidget(mk_label(sub_txt, "muted", True))
            kpi_grid.addWidget(tile, idx // 3, idx % 3)
        lay.addLayout(kpi_grid)

        # 4 Feature Highlights (2x2)
        feat_grid = QGridLayout()
        feat_grid.setSpacing(10)
        feats = [
            ("Toán học & Hình học động", "Soạn công thức LaTeX kèm thay số & tính kết quả nhanh; bảng dựng hình động với 24 hình mẫu 2D/3D, đồ thị dò tọa độ tức thời và ký hiệu góc vuông chuẩn."),
            ("Hóa học chuẩn danh pháp IUPAC", "Chuẩn hóa tên gốc quốc tế cho toàn bộ 118 nguyên tố & 705 hợp chất; trình vẽ phân tử 3 cột kiểu ChemDraw với phím tắt đổi nguyên tố và liên kết nêm lập thể."),
            ("Máy tính khoa học hiện đại", "Hiển thị phân số/căn/mũ tự nhiên kiểu Casio fx-580VN X, lưu biến nhớ A/B/Ans trực quan và tìm nhanh 43 công cụ giải toán/hóa kèm lời giải từng bước."),
            ("Xuất Microsoft Word & Đồ họa", "Chèn trực tiếp công thức thành Equation gốc của Word (.docx) hoặc xuất ảnh PNG độ phân giải cao (300 DPI) và vector SVG không vỡ nét."),
        ]
        for idx, (ft, fd) in enumerate(feats):
            card = mk_card(QVBoxLayout(), margins=(16, 12, 16, 12), spacing=4)
            card.layout().addWidget(mk_label(ft, "h2"))
            card.layout().addWidget(mk_label(fd, "muted", True))
            feat_grid.addWidget(card, idx // 2, idx % 2)
        lay.addLayout(feat_grid)

        # Hệ thống & Môi trường
        env_card = mk_card(QVBoxLayout(), margins=(16, 12, 16, 12), spacing=8)
        env_card.layout().addWidget(mk_label("MÔI TRƯỜNG & THƯ VIỆN HỆ THỐNG", "caption"))
        egrid = QGridLayout()
        egrid.setSpacing(6)
        py_v = f"Python {_s.version_info.major}.{_s.version_info.minor}.{_s.version_info.micro}"
        env_items = (
            (py_v, True),
            ("PySide6 · Sẵn sàng", True),
            ("Matplotlib · Sẵn sàng", True),
            (f"RDKit · {'Có' if mo.HAS_RDKIT else 'Tích hợp sẵn'}", True),
            (f"Offline OCR · {'Sẵn sàng' if (fe.HAS_RAPID_OCR or fe.HAS_PIX2TEX) else 'Dùng Gemini OCR'}", fe.HAS_RAPID_OCR or fe.HAS_PIX2TEX),
        )
        for idx, (label, ok) in enumerate(env_items):
            egrid.addWidget(mk_label(label, "badge_ok" if ok else "badge_muted"), idx // 3, idx % 3)
        env_card.layout().addLayout(egrid)
        lay.addWidget(env_card)
        lay.addStretch(1)
        sc = scroll_wrap(body)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return sc

    def refresh_lang(self):
        lang = i18n.get_lang()
        for lk, lb in getattr(self, "lang_btns", {}).items():
            lb.setChecked(lk == lang)
        self._update_key_badge()
        if hasattr(self, "lbl_about_sub"):
            author = ds.APP_AUTHOR.replace("by ", "")
            if i18n.is_en():
                self.lbl_about_sub.setText(f"Developed by {author}  ·  All-in-one STEM desktop suite for studying, teaching, and technical authoring.")
                self.lbl_about_desc.setText("Includes Visual & LaTeX Math Editor, Dynamic Geometry & Graphing, Chemical Equation Balancer, 2D Molecule Sketcher, 118-Element Periodic Table, 705-Compound Chemistry Wiki, and 43-Solver Scientific Calculator.")
            else:
                self.lbl_about_sub.setText(f"Phát triển bởi {author}  ·  Bộ công cụ khoa học toàn diện cho học tập, giảng dạy và biên soạn tài liệu.")
                self.lbl_about_desc.setText("Tích hợp đầy đủ Soạn công thức LaTeX, Hình học động & Đồ thị, Cân bằng phản ứng, Trình vẽ phân tử 2D lập thể, Bảng tuần hoàn 118 nguyên tố và Máy tính khoa học 43 bộ giải.")
        if hasattr(self, "g_browser"):
            self.show_guide(self.cur_guide)

    def sync(self):
        mode = self.ctx.prefs.get("mode", "light")
        acc_name = self.ctx.prefs.get("accent", "Chàm")
        lang = i18n.get_lang()
        c = self.ctx.palette
        acc = ACCENTS.get(acc_name, ACCENTS["Chàm"])[0]
        for lk, lb in getattr(self, "lang_btns", {}).items():
            lb.setChecked(lk == lang)
        for key, b in self.theme_btns.items():
            b.setChecked(key == mode)
            ic_nm = "moon" if b.property("_theme_dark") else "sun"
            b.setIcon(icons.make_icon(ic_nm, c["muted"], acc, size=19))
        for name, b in self.swatch_btns.items():
            b.setChecked(name == acc_name)
            hx = b.property("_acc_hex")
            if name == acc_name:
                b.setStyleSheet(f"border: 2px solid {hx}; color: {hx}; font-weight: 700;")
            else:
                b.setStyleSheet(f"color: {c['text']};")
        if hasattr(self, "g_browser"):
            self.show_guide(self.cur_guide)


class MainWindow(QMainWindow):
    NAV = (
        ("math", "Toán học · Hình học"),
        ("chem", "Hóa học · Phân tử"),
        ("calc", "Máy tính khoa học"),
        ("settings", "Cài đặt · Hướng dẫn"),
    )

    def __init__(self):
        super().__init__()
        self.ctx = Ctx(self)
        self._quitting = False
        self.tray = None
        self.setWindowTitle(f"{ds.APP_NAME} {ds.APP_VERSION}")
        self.resize(1420, 890)
        self.setMinimumSize(960, 640)
        self._side_collapsed = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- SIDEBAR CĂN LỀ ĐỒNG TRỤC TUYỆT ĐỐI + HỖ TRỢ THU GỌN THÀNH THANH ICON
        self.side = QFrame()
        side = self.side
        side.setObjectName("sidebar")
        side.setFixedWidth(240)
        self._sv = QVBoxLayout(side)
        sv = self._sv
        sv.setContentsMargins(12, 14, 12, 12)
        sv.setSpacing(4)

        # Đầu thanh bên: logo + tên + nút thu gọn
        self._hd = QHBoxLayout()
        hd = self._hd
        hd.setContentsMargins(6, 0, 2, 0)
        hd.setSpacing(8)
        self._logo_pm_full = QPixmap(res_path("assets/logo_icon.png")).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._logo_pm_mini = QPixmap(res_path("assets/logo_icon.png")).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(40, 40)
        self.lbl_logo.setPixmap(self._logo_pm_full)
        hd.addWidget(self.lbl_logo)
        self.brand_box = QWidget()
        tcol = QVBoxLayout(self.brand_box)
        tcol.setContentsMargins(0, 0, 0, 0)
        tcol.setSpacing(1)
        tcol.addStretch(1)
        tcol.addWidget(mk_label(ds.APP_NAME, "brand"))
        tcol.addWidget(mk_label(f"{ds.APP_VERSION}  ·  {ds.APP_AUTHOR}", "brandsub"))
        tcol.addStretch(1)
        hd.addWidget(self.brand_box, 1)
        self.b_toggle_side = mk_btn("«", tip="Thu gọn / mở rộng thanh bên (Ctrl+B)", prop=("sidetoggle", True))
        self.b_toggle_side.setProperty("_i18n_skip", True)
        self.b_toggle_side.setFixedSize(28, 28)
        self.b_toggle_side.clicked.connect(self.toggle_sidebar)
        hd.addWidget(self.b_toggle_side)
        sv.addLayout(hd)

        sv.addSpacing(10)
        sv.addWidget(mk_sep())
        sv.addSpacing(10)
        self.cap_ws = mk_label("KHÔNG GIAN LÀM VIỆC", "sidecap")
        sv.addWidget(self.cap_ws)
        sv.addSpacing(4)

        self.stack = QStackedWidget()
        self.nav = []
        self.math = MathSection(self.ctx)
        self.chem = ChemSection(self.ctx)
        self.calc = CalculatorSection(self.ctx)
        self.about = SettingsPage(self.ctx, self)
        self._sections = {"math": self.math, "chem": self.chem, "calc": self.calc, "settings": self.about}

        for idx, ((icon_key, name), w) in enumerate(zip(self.NAV, (self.math, self.chem, self.calc, self.about)), 1):
            b = QPushButton("  " + esc(name))
            b.setProperty("nav", True)
            b.setProperty("_i18n_skip", True)
            b.setProperty("icon_key", icon_key)
            b.setProperty("vi_name", name)
            b.setProperty("full_text", "  " + esc(name))
            b.setCheckable(True)
            b.setIconSize(QSize(19, 19))
            b.setToolTip(f"{name}  (Ctrl+{idx})")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, ww=w: self.go(ww))
            sv.addWidget(b)
            self.nav.append((b, w))
            self.stack.addWidget(w)
            QShortcut(QKeySequence(f"Ctrl+{idx}"), self, activated=lambda ww=w: self.go(ww))

        QShortcut(QKeySequence("Ctrl+D"), self, activated=lambda: self.set_theme("light" if self.ctx.dark else "dark"))
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self.toggle_sidebar)

        sv.addStretch(1)
        sv.addWidget(mk_sep())
        sv.addSpacing(8)
        self.cap_util = mk_label("TIỆN ÍCH NHANH", "sidecap")
        sv.addWidget(self.cap_util)
        sv.addSpacing(4)

        self.b_word = mk_btn("  Tài liệu Word (0)", tip="Gom công thức, hình đã thêm rồi xuất .docx hoặc chèn vào Word", prop=("navutil", True))
        self.b_word.setProperty("_i18n_skip", True)
        self.b_word.setIconSize(QSize(18, 18))
        self.b_word.clicked.connect(self.ctx.open_basket)
        self.ctx.on_basket = self._update_word_btn
        sv.addWidget(self.b_word)
        sv.addSpacing(4)

        self.b_lang = mk_btn("", tip="Chuyển ngôn ngữ Tiếng Việt / English", prop=("navutil", True))
        self.b_lang.setProperty("_i18n_skip", True)
        self.b_lang.setIconSize(QSize(18, 18))
        self.b_lang.clicked.connect(lambda: self.set_lang("vi" if i18n.is_en() else "en"))
        sv.addWidget(self.b_lang)
        sv.addSpacing(4)

        self.b_theme = mk_btn("", tip="Chuyển Sáng / Tối (Ctrl+D)", prop=("navutil", True))
        self.b_theme.setProperty("_i18n_skip", True)
        self.b_theme.setIconSize(QSize(18, 18))
        self.b_theme.clicked.connect(lambda: self.set_theme("light" if self.ctx.dark else "dark"))
        sv.addWidget(self.b_theme)
        root.addWidget(side)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(10, 8, 10, 6)
        rl.addWidget(self.stack)
        root.addWidget(right, 1)

        self.go(self.math)
        self.apply_theme()
        self.apply_lang()
        self.update_tray()

    def showEvent(self, e):
        super().showEvent(e)
        apply_win_titlebar(self, self.ctx.dark)

    def _update_word_btn(self, n):
        lbl = f"  Word Document ({n})" if i18n.is_en() else f"  Tài Liệu Word ({n})"
        self.b_word.setText("" if self._side_collapsed else esc(lbl))
        self.b_word.setToolTip(
            f"Word Document ({n} items) — collect formulas/figures to export .docx" if i18n.is_en()
            else f"Tài Liệu Word ({n} mục) — gom công thức/hình để xuất .docx hoặc chèn vào Word"
        )

    def _sync_sidebar_labels(self):
        mini = self._side_collapsed
        for idx, (b, _) in enumerate(self.nav, 1):
            nm = i18n.smart_title(i18n.tr(b.property("vi_name")))
            b.setProperty("full_text", "  " + esc(nm))
            b.setText("" if mini else "  " + esc(nm))
            b.setToolTip(f"{nm}  (Ctrl+{idx})")
        self._update_word_btn(len(self.ctx.basket))
        lang_lbl = "  Tiếng Việt (VN)" if i18n.is_en() else "  English (EN)"
        self.b_lang.setText("" if mini else esc(lang_lbl))
        self.b_lang.setToolTip("Switch to Vietnamese (VN)" if i18n.is_en() else "Switch to English (EN)")
        th_lbl = ("  Light Mode" if self.ctx.dark else "  Dark Mode") if i18n.is_en() else ("  Giao Diện Sáng" if self.ctx.dark else "  Giao Diện Tối")
        self.b_theme.setText("" if mini else esc(th_lbl))
        self.b_theme.setToolTip(
            ("Switch to Light Mode (Ctrl+D)" if self.ctx.dark else "Switch to Dark Mode (Ctrl+D)") if i18n.is_en()
            else ("Chuyển sang Giao diện sáng (Ctrl+D)" if self.ctx.dark else "Chuyển sang Giao diện tối (Ctrl+D)")
        )

    def toggle_sidebar(self):
        self._side_collapsed = not self._side_collapsed
        mini = self._side_collapsed
        self.side.setFixedWidth(64 if mini else 240)
        self._sv.setContentsMargins(6, 12, 6, 12) if mini else self._sv.setContentsMargins(12, 14, 12, 12)
        self._hd.setContentsMargins(0, 0, 0, 0) if mini else self._hd.setContentsMargins(6, 0, 2, 0)
        self.brand_box.setVisible(not mini)
        self.cap_ws.setVisible(not mini)
        self.cap_util.setVisible(not mini)
        self.lbl_logo.setVisible(not mini)
        self.b_toggle_side.setText("☰" if mini else "«")
        self.b_toggle_side.setFixedSize(40, 32) if mini else self.b_toggle_side.setFixedSize(26, 26)
        for b, _ in self.nav:
            b.setProperty("nav", not mini)
            b.setProperty("nav_mini", mini)
        for ub in (self.b_word, self.b_lang, self.b_theme):
            ub.setProperty("navutil", not mini)
            ub.setProperty("nav_mini", mini)
        self._sync_sidebar_labels()
        if self.ctx.qss:
            self.side.setStyleSheet(self.ctx.qss)

    def set_lang(self, lang: str):
        lang = "en" if str(lang).lower().startswith("en") else "vi"
        if lang == i18n.get_lang():
            return
        self.ctx.prefs["lang"] = lang
        self.ctx.save_prefs()
        i18n.set_lang(lang)
        self.apply_lang()

    def apply_lang(self):
        self.setUpdatesEnabled(False)
        try:
            i18n.apply_lang_to_tree(self)
            self._sync_sidebar_labels()
            self.about.refresh_lang()
            self.math.refresh_lang()
            self.chem.refresh_lang()
            self.calc.refresh_lang()
            if i18n.is_en():
                self.statusBar().showMessage(f"{ds.APP_NAME} {ds.APP_VERSION} — Ready (Ctrl+1..4 switch workspace · Ctrl+B collapse sidebar · Ctrl+D Light/Dark)")
            else:
                self.statusBar().showMessage(f"{ds.APP_NAME} {ds.APP_VERSION} — Sẵn sàng (Ctrl+1..4 chuyển mục · Ctrl+B thu gọn thanh bên · Ctrl+D đổi Sáng/Tối)")
        finally:
            self.setUpdatesEnabled(True)

    def _sync_widget_qss(self, w):
        if getattr(w, "_qss_ver", -1) != self.ctx.qss_ver:
            w.setStyleSheet(self.ctx.qss)
            w._qss_ver = self.ctx.qss_ver

    def go(self, w):
        self._sync_widget_qss(w)
        self.stack.setCurrentWidget(w)
        for b, ww in self.nav:
            b.setChecked(ww is w)

    def jump_to(self, sec_key: str, tab_idx: int = 0):
        w = self._sections.get(sec_key)
        if not w:
            return
        self.go(w)
        if hasattr(w, "tabs") and 0 <= tab_idx < w.tabs.count():
            w.tabs.setCurrentIndex(tab_idx)

    def set_theme(self, mode=None, accent=None):
        changed = False
        if mode and mode != self.ctx.prefs.get("mode"):
            self.ctx.prefs["mode"] = mode
            changed = True
        if accent and accent != self.ctx.prefs.get("accent"):
            self.ctx.prefs["accent"] = accent
            changed = True
        if not changed:
            return
        self.ctx.save_prefs()
        self.apply_theme()

    def apply_theme(self):
        mode = self.ctx.prefs.get("mode", "light")
        acc = self.ctx.prefs.get("accent", "Chàm")
        c = PALETTES.get(mode, PALETTES["light"])
        acc_hex = ACCENTS.get(acc, ACCENTS["Chàm"])[0]
        qss = build_qss(mode, acc)
        self.ctx.qss = qss
        self.ctx.qss_ver += 1

        # Đổi theme siêu mượt (<30ms): cập nhật QPalette nhẹ + chỉ áp QSS lên vùng đang hiển thị!
        # Các trang đang ẩn sẽ tự nhận QSS mới ngay khi người dùng mở sang (lazy sync).
        dark = is_dark_mode(mode)
        self.setUpdatesEnabled(False)
        try:
            QApplication.instance().setPalette(build_palette(mode, acc))
            apply_win_titlebar(self, dark)
            self.side.setStyleSheet(qss)
            self.statusBar().setStyleSheet(f"QStatusBar {{ background: {c['side']}; color: {c['muted']}; border-top: 1px solid {c['border']}; font-size: 12px; padding: 2px 10px; }}")
            cur = self.stack.currentWidget()
            if cur is not None:
                self._sync_widget_qss(cur)
            for b, _ in self.nav:
                b.setIcon(icons.make_icon(b.property("icon_key"), c["muted"], acc_hex, size=19))
            self.b_word.setIcon(icons.make_icon("doc", c["muted"], acc_hex, size=18))
            self.b_lang.setIcon(icons.make_icon("globe", c["muted"], acc_hex, size=18))
            self.b_theme.setIcon(icons.make_icon("sun" if dark else "moon", c["muted"], acc_hex, size=18))
            self._sync_sidebar_labels()
            self.about.sync()
            self.math.refresh_theme()
            self.chem.refresh_theme()
            self.calc.refresh_theme()
        finally:
            self.setUpdatesEnabled(True)

    # ------------------------------------------------------------- khay hệ thống
    def update_tray(self):
        want = QSystemTrayIcon.isSystemTrayAvailable() and (self.ctx.prefs.get("tray_icon", True) or self.ctx.prefs.get("close_action") == "tray")
        if want and self.tray is None:
            self.tray = QSystemTrayIcon(self.windowIcon() if not self.windowIcon().isNull() else QIcon(res_path("app.ico")), self)
            self.tray.setToolTip(f"{ds.APP_NAME} {ds.APP_VERSION}")
            menu = QMenu()
            act_open = QAction("Mở Formula Studio", menu)
            act_open.triggered.connect(self.show_from_tray)
            act_quit = QAction("Thoát", menu)
            act_quit.triggered.connect(self.quit_app)
            menu.addAction(act_open)
            menu.addSeparator()
            menu.addAction(act_quit)
            self._tray_menu = menu
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(lambda reason: self.show_from_tray() if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
        if self.tray is not None:
            self.tray.setVisible(bool(want))

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self._quitting = True
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, e):
        if self._quitting:
            e.accept()
            return
        act = self.ctx.prefs.get("close_action", "ask")
        can_tray = QSystemTrayIcon.isSystemTrayAvailable()
        if not can_tray:
            self.quit_app()
            e.accept()
            return
        if act == "ask":
            en = i18n.is_en()
            box = QMessageBox(self)
            box.setWindowTitle(ds.APP_NAME)
            box.setIcon(QMessageBox.Question)
            box.setText("Would you like to quit or minimize to the system tray?" if en else "Bạn muốn thoát hay thu nhỏ xuống khay hệ thống?")
            b_tray = box.addButton("Minimize to Tray" if en else "Thu nhỏ xuống khay", QMessageBox.AcceptRole)
            b_quit = box.addButton("Quit" if en else "Thoát", QMessageBox.DestructiveRole)
            box.addButton("Cancel" if en else "Hủy", QMessageBox.RejectRole)
            chk = QCheckBox("Remember my choice" if en else "Ghi nhớ lựa chọn này")
            box.setCheckBox(chk)
            box.exec()
            clicked = box.clickedButton()
            if clicked is b_tray:
                act = "tray"
            elif clicked is b_quit:
                act = "quit"
            else:
                e.ignore()
                return
            if chk.isChecked():
                self.ctx.prefs["close_action"] = act
                self.ctx.save_prefs()
                self.about.rb[act].setChecked(True)
        if act == "tray":
            self.update_tray()
            if self.tray is not None:
                self.tray.setVisible(True)
                self.tray.showMessage(
                    ds.APP_NAME,
                    "Application is still running in the system tray." if i18n.is_en() else "Ứng dụng vẫn đang chạy ở khay hệ thống.",
                    QSystemTrayIcon.Information, 2500,
                )
            self.hide()
            e.ignore()
        else:
            self.quit_app()
            e.accept()


def selftest():
    """python main.py --selftest : kiểm tra nhanh các chức năng lõi (dùng sau khi đóng gói .exe)."""
    import word_export as we
    res = []

    def chk(name, fn):
        try:
            fn()
            res.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            res.append((name, False, repr(exc)))
    chk("Vẽ công thức Toán", lambda: fe.render_formula_to_bytes("\\frac{a}{b}+\\sqrt{x}", 24, "#111", "white", True, "png", 80))
    chk("Cân bằng PT", lambda: fe.balance_chemical_equation("Fe + O2 -> Fe3O4"))
    chk("Vẽ PT hóa học", lambda: fe.render_chem_equation_bytes("2H2 + O2 ->[t^o] 2H2O", 24, "#111", "white", "png", 80))
    chk("Vẽ phân tử", lambda: mo.render_mol_bytes(mo.make_mol("CC(=O)Oc1ccccc1C(=O)O", False)[0], "png", "white", out_dpi=80))
    chk("Máy tính", lambda: __import__("calc_engine").Calc().evaluate("2*sin(30)+sqrt(144)"))
    chk("Biểu thức dạng công thức", lambda: __import__("natural_display").parse_pretty("-2√3/3"))
    chk("Xuất Word (.docx)", lambda: we.build_docx_bytes([{"kind": "math", "latex": r"x^2+1"}, {"kind": "chem", "text": "H2 + O2 -> H2O"}]))
    lines = [("OK   " if ok else "LỖI ") + name + (" - " + err if err else "") for name, ok, err in res]
    print("\n".join(lines))
    try:
        with open("selftest_result.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass
    return 0 if all(r[1] for r in res) else 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    base_font = QFont("Segoe UI", 10)
    base_font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(base_font)
    app.setQuitOnLastWindowClosed(False)
    ico = res_path("app.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ItzMeCorniizt.FormulaStudio.2")
        except Exception:
            pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
