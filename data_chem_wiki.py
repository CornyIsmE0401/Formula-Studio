# -*- coding: utf-8 -*-
"""data_chem_wiki.py - Bách khoa Hóa học chuẩn danh pháp quốc tế IUPAC (GDPT 2018):
hồ sơ chuyên sâu cho các chất trọng tâm, tự động liên kết phương trình điều chế & phản ứng từ kho 686 PT,
và trình xuất bài viết dạng Wiki trực quan cho học sinh tự tra cứu."""
import html
import re
from urllib.parse import quote

import formula_engine as fe

# Chuẩn hóa khóa công thức để so khớp phản ứng chính xác (không khớp nhầm CO trong CO2 hay HCl trong NH4Cl)
_COND_RE = re.compile(r"\[[^\]]*\]")
_ARROW_RE = re.compile(r"\s*(?:<=>|<->|⇌|->|→)\s*")
_COEFF_RE = re.compile(r"^\d+\s*")
_TAIL_RE = re.compile(r"\s*(?:\((?:s|l|g|aq)\)|[\^v↑↓])+$")


def _clean_species(tok: str) -> str:
    s = tok.strip()
    s = _COEFF_RE.sub("", s)
    s = _TAIL_RE.sub("", s).strip()
    s = s.replace(" ", "")
    return s


# Một số bí danh công thức đồng phân/viết gọn hay gặp trong kho phương trình
_FORMULA_ALIASES = {
    "C2H5OH": {"C2H5OH", "CH3CH2OH", "C2H6O"},
    "CH3OH": {"CH3OH", "CH4O"},
    "CH3COOH": {"CH3COOH", "C2H4O2"},
    "HCOOH": {"HCOOH", "CH2O2"},
    "CH3CHO": {"CH3CHO", "C2H4O"},
    "HCHO": {"HCHO", "CH2O"},
    "C6H5OH": {"C6H5OH", "C6H6O"},
    "C6H5NH2": {"C6H5NH2", "C6H7N"},
    "CH3COOC2H5": {"CH3COOC2H5", "C4H8O2"},
    "C3H5(OH)3": {"C3H5(OH)3", "C3H8O3"},
    "C6H12O6": {"C6H12O6"},
    "C12H22O11": {"C12H22O11"},
    "(C6H10O5)n": {"(C6H10O5)n", "C6H10O5"},
    "CH4": {"CH4"},
    "C2H4": {"C2H4", "CH2=CH2"},
    "C2H2": {"C2H2", "CH#CH"},
    "C6H6": {"C6H6"},
    "C6H5CH3": {"C6H5CH3", "C7H8"},
    "CH3NH2": {"CH3NH2", "CH5N"},
    "H2NCH2COOH": {"H2NCH2COOH", "NH2CH2COOH", "C2H5NO2"},
    "Ca(OCl)2": {"Ca(OCl)2", "CaOCl2"},
}

_RXN_INDEX = None


def _build_rxn_index(reactions_list):
    """Lập chỉ mục toàn bộ kho phản ứng theo từng chất tham gia (LHS) và sản phẩm (RHS) để tra cứu O(1)."""
    lhs_map = {}
    rhs_map = {}
    for title, cat, eq in reactions_list:
        clean_eq = _COND_RE.sub("", eq)
        parts = _ARROW_RE.split(clean_eq, maxsplit=1)
        if len(parts) != 2:
            continue
        lhs_raw, rhs_raw = parts
        lhs_toks = {_clean_species(p) for p in re.split(r"\s+\+\s+", lhs_raw) if p.strip()}
        rhs_toks = {_clean_species(p) for p in re.split(r"\s+\+\s+", rhs_raw) if p.strip()}
        for tok in lhs_toks:
            if tok:
                lhs_map.setdefault(tok, []).append((title, cat, eq))
        for tok in rhs_toks:
            if tok:
                rhs_map.setdefault(tok, []).append((title, cat, eq))
    return lhs_map, rhs_map


def compound_reactions(formula: str, reactions_list):
    """Trả về (prep_rxns, prop_rxns) gồm các phương trình điều chế (ở vế phải) và phản ứng đặc trưng (ở vế trái)."""
    global _RXN_INDEX
    if _RXN_INDEX is None:
        _RXN_INDEX = _build_rxn_index(reactions_list)
    lhs_map, rhs_map = _RXN_INDEX
    key = formula.replace(" ", "")
    keys = set(_FORMULA_ALIASES.get(key, {key}))
    # Thêm dạng bỏ dấu ngoặc đơn ngoài nếu có
    keys.add(key)

    prep, prop = [], []
    seen_p, seen_r = set(), set()
    for k in keys:
        for item in rhs_map.get(k, ()):
            if item[2] not in seen_p:
                seen_p.add(item[2])
                prep.append(item)
        for item in lhs_map.get(k, ()):
            if item[2] not in seen_r:
                seen_r.add(item[2])
                prop.append(item)
    return prep, prop


# ==============================================================================
# KHO BÁCH KHOA CHUYÊN SÂU (65+ chất trọng tâm chương trình Hóa học phổ thông & đại học)
# 100% chuẩn danh pháp quốc tế IUPAC (GDPT 2018)
# ==============================================================================
COMPOUND_WIKI = {
    "H2O": {
        "state": "Chất lỏng không màu, không mùi, không vị; nóng chảy ở 0 °C, sôi ở 100 °C (1 atm); khối lượng riêng cực đại 1,00 g/cm³ ở 4 °C.",
        "props": "Phân tử phân cực mạnh (góc liên kết H–O–H = 104,5°), tạo mạng liên kết hydrogen nên có nhiệt dung riêng và nhiệt độ sôi cao bất thường. Tác dụng với kim loại kiềm/kiềm thổ (K, Na, Ca, Ba), oxide base tan, oxide acid; là dung môi phân cực phổ biến nhất và chất điện li rất yếu (K_w = 10⁻¹⁴ ở 25 °C).",
        "prep": "Tạo thành khi đốt cháy hydrogen trong oxygen, phản ứng trung hòa acid–base, và là sản phẩm phụ phổ biến của phản ứng ester hóa, đốt cháy hợp chất hữu cơ.",
        "uses": "Dung môi số 1 trong phòng thí nghiệm và công nghiệp; chất tải nhiệt, làm mát; nguyên liệu điện phân sản xuất H₂, O₂; thiết yếu cho mọi quá trình sinh học.",
        "safety": "An toàn sinh học. Lưu ý: KHÔNG đổ nước trực tiếp vào H₂SO₄ đặc (gây tỏa nhiệt mạnh bắn tung tóe) và không dùng nước dập cháy kim loại kiềm (Na, K) hoặc dầu mỡ.",
    },
    "H2": {
        "state": "Chất khí không màu, không mùi, không vị; nhẹ nhất trong tất cả các chất khí (d = 2/29 so với không khí); rất ít tan trong nước.",
        "props": "Tính khử mạnh ở nhiệt độ cao: khử được nhiều oxide kim loại đứng sau Al (CuO, Fe₂O₃, Fe₃O₄, PbO…) về kim loại tự do; cháy trong O₂ với ngọn lửa xanh nhạt tỏa nhiệt rất lớn; phản ứng cộng với hydrocarbon không no (xúc tác Ni/Pd/Pt).",
        "prep": "Phòng thí nghiệm: cho Zn hoặc Fe tác dụng với dung dịch HCl / H₂SO₄ loãng. Công nghiệp: điện phân nước có màng ngăn hoặc reforming khí methane bằng hơi nước.",
        "uses": "Tổng hợp ammonia (quy trình Haber–Bosch), sản xuất methanol, hydrogen hóa dầu thực vật thành bơ thực vật, nhiên liệu tên lửa và pin nhiên liệu (fuel cell) sạch.",
        "safety": "Rất dễ cháy nổ! Hỗn hợp H₂ : O₂ tỉ lệ thể tích 2 : 1 là hỗn hợp nổ mạnh nhất — luôn kiểm tra độ tinh khiết trước khi đốt.",
    },
    "O2": {
        "state": "Chất khí không màu, không mùi, không vị; nặng hơn không khí một chút; ít tan trong nước; hóa lỏng ở −183 °C (màu xanh nhạt).",
        "props": "Phi kim có tính oxi hóa mạnh (độ âm điện 3,44): tác dụng với hầu hết kim loại (trừ Au, Pt), hầu hết phi kim (C, S, P, Si, H₂…) và đốt cháy hầu hết hợp chất hữu cơ.",
        "prep": "Phòng thí nghiệm: nhiệt phân KMnO₄, KClO₃ (xúc tác MnO₂) hoặc phân hủy H₂O₂ (xúc tác MnO₂). Công nghiệp: chưng cất phân đoạn không khí lỏng và điện phân nước.",
        "uses": "Duy trì sự hô hấp (y tế, lặn biển, hàng không), luyện gang thép (thổi O₂ vào lò luyện), hàn cắt kim loại bằng đèn xì oxygen–acetylene, chất oxi hóa nhiên liệu tên lửa.",
        "safety": "Không tự cháy nhưng duy trì và thúc đẩy sự cháy cực mạnh; tuyệt đối tránh tiếp xúc dầu mỡ với van bình khí O₂ áp suất cao.",
    },
    "O3": {
        "state": "Chất khí màu xanh nhạt, có mùi hắc đặc trưng (mùi sau cơn giông); hóa lỏng ở −112 °C; tan trong nước tốt hơn O₂ gần 15 lần.",
        "props": "Tính oxi hóa mạnh hơn O₂ rõ rệt: oxi hóa được Ag ở điều kiện thường (2Ag + O₃ → Ag₂O + O₂) và đẩy I₂ ra khỏi dung dịch KI (nhận biết bằng hồ tinh bột hóa xanh tím).",
        "prep": "Phóng điện êm qua khí O₂ khô (máy ozon hóa) hoặc tác dụng của tia cực tím (UV) lên O₂ ở tầng bình lưu khí quyển.",
        "uses": "Tầng ozone hấp thụ tia UV bảo vệ sinh vật Trái Đất; ứng dụng khử trùng nước uống, khử mùi, tẩy trắng giấy/vải và bảo quản nông sản (liều rất nhỏ).",
        "safety": "Độc hại với đường hô hấp ở nồng độ cao (> 0,1 ppm) và gây ăn mòn cao su.",
    },
    "Cl2": {
        "state": "Chất khí màu vàng lục, mùi xốc khó chịu, nặng gấp ~2,45 lần không khí; tan vừa phải trong nước tạo nước chlorine màu vàng nhạt.",
        "props": "Tính oxi hóa rất mạnh: oxi hóa hầu hết kim loại lên mức oxi hóa cao nhất (Fe → FeCl₃, Cu → CuCl₂), tác dụng với H₂ (nổ khi chiếu sáng), đẩy Br₂, I₂ khỏi muối halide; tự oxi hóa – khử trong nước và dung dịch kiềm (tạo nước Javel, chloride vôi).",
        "prep": "Phòng thí nghiệm: oxi hóa HCl đặc bằng MnO₂ hoặc KMnO₄. Công nghiệp: điện phân dung dịch NaCl bão hòa có màng ngăn xốp.",
        "uses": "Khử trùng nước sinh hoạt, sản xuất PVC, HCl, nước Javel (NaClO), chloride vôi (CaOCl₂), dung môi hữu cơ và thuốc bảo vệ thực vật.",
        "safety": "Khí rất độc! Gây tổn thương phổi và niêm mạc mắt; khi thao tác phải thực hiện trong tủ hút và có bông tẩm dung dịch NaOH để hấp thụ khí dư.",
    },
    "N2": {
        "state": "Chất khí không màu, không mùi, không vị; hơi nhẹ hơn không khí; rất ít tan trong nước; hóa lỏng ở −196 °C.",
        "props": "Ở nhiệt độ thường rất trơ về mặt hóa học do phân tử có liên kết ba N≡N rất bền (năng lượng liên kết 945 kJ/mol). Ở nhiệt độ cao hoặc tia lửa điện, thể hiện cả tính oxi hóa (tác dụng với H₂, Mg, Li) và tính khử (tác dụng với O₂ tạo NO ở ~3000 °C).",
        "prep": "Công nghiệp: chưng cất phân đoạn không khí lỏng. Phòng thí nghiệm: đun nóng dung dịch bão hòa NH₄Cl và NaNO₂ (NH₄NO₂ → N₂ + 2H₂O).",
        "uses": "Tổng hợp ammonia (NH₃) làm phân đạm; tạo khí quyển trơ trong luyện kim, điện tử và đóng gói thực phẩm; nitrogen lỏng (−196 °C) dùng bảo quản mẫu sinh học.",
        "safety": "Không độc nhưng có thể gây ngạt trong không gian kín nếu làm giảm nồng độ O₂; nitrogen lỏng gây bỏng lạnh nghiêm trọng.",
    },
    "NH3": {
        "state": "Chất khí không màu, mùi khai xốc đặc trưng, nhẹ hơn không khí (M = 17); tan cực tốt trong nước (~800 thể tích khí/1 thể tích nước ở 20 °C).",
        "props": "Phân tử hình chóp tam giác, phân cực mạnh và còn cặp electron tự do trên N nên có: (1) Tính base yếu (làm xanh quỳ tím ẩm, hồng phenolphthalein, tác dụng với acid tạo muối ammonium, tạo kết tủa hydroxide với nhiều muối kim loại, tạo phức tan với Cu(OH)₂, AgCl); (2) Tính khử mạnh (cháy trong O₂ tạo N₂ hoặc NO khi có xúc tác Pt).",
        "prep": "Công nghiệp: tổng hợp trực tiếp từ N₂ và H₂ (quy trình Haber–Bosch: 400–450 °C, 150–200 bar, xúc tác Fe). Phòng thí nghiệm: đun nóng muối ammonium với Ca(OH)₂ hoặc NaOH.",
        "uses": "Sản xuất phân đạm (urea, NH₄NO₃, (NH₄)₂SO₄), sản xuất nitric acid (HNO₃), chất làm lạnh trong công nghiệp thực phẩm, sản xuất sợi nylon.",
        "safety": "Gây kích ứng mạnh mắt và đường hô hấp; mùi khai dễ phát hiện sớm. Khi rò rỉ cần thông gió mạnh và tránh xa nguồn lửa.",
    },
    "HCl": {
        "state": "Hydrogen chloride là khí không màu, mùi xốc, tan rất tốt trong nước tạo dung dịch hydrochloric acid (nồng độ đặc thương mại ~37%, bốc khói trắng trong không khí ẩm).",
        "props": "Acid mạnh, phân li hoàn toàn trong nước: làm đỏ quỳ tím, tác dụng với kim loại đứng trước H (Fe → FeCl₂, Zn → ZnCl₂), oxide base, base và muối carbonate/sulfite. Ngoài ra ion Cl⁻ còn có tính khử khi tác dụng với chất oxi hóa mạnh (MnO₂, KMnO₄, K₂Cr₂O₇).",
        "prep": "Phòng thí nghiệm: phương pháp sulfate (NaCl rắn + H₂SO₄ đặc, đun nóng). Công nghiệp: tổng hợp từ H₂ và Cl₂ rồi hấp thụ khí HCl vào nước.",
        "uses": "Tẩy gỉ thép trước khi mạ, sản xuất PVC (vinyl chloride), sản xuất muối chloride, chế biến thực phẩm, điều chỉnh pH nước và là thành phần của dịch vị dạ dày (~0,03–0,1 M).",
        "safety": "Ăn mòn da, mắt và niêm mạc; hơi HCl đặc gây rát đường hô hấp — cần đeo kính bảo hộ và mở chai trong tủ hút.",
    },
    "H2SO4": {
        "state": "Chất lỏng sánh như dầu, không màu, không bay hơi; nặng gần gấp đôi nước (D = 1,84 g/cm³ ở 98%); tan vô hạn trong nước và tỏa nhiệt cực mạnh.",
        "props": "H₂SO₄ loãng có đầy đủ tính chất của một acid mạnh 2 nấc (tác dụng với kim loại trước H tạo muối hóa trị thấp, base, oxide base, muối). H₂SO₄ đặc, nóng có tính oxi hóa rất mạnh (oxi hóa hầu hết kim loại trừ Au, Pt lên mức cao nhất như Fe → Fe³⁺, Cu → Cu²⁺ và giải phóng SO₂) cùng tính háo nước cực mạnh (làm than hóa đường sucrose, giấy, vải). Lưu ý: Al, Fe, Cr bị thụ động hóa trong H₂SO₄ đặc, nguội.",
        "prep": "Sản xuất công nghiệp theo phương pháp tiếp xúc gồm 3 giai đoạn: đốt S hoặc FeS₂ → SO₂; oxi hóa SO₂ → SO₃ (450 °C, xúc tác V₂O₅); hấp thụ SO₃ bằng H₂SO₄ 98% tạo oleum rồi pha loãng.",
        "uses": "“Máu của ngành công nghiệp hóa chất”: sản xuất phân bón (superphosphate, (NH₄)₂SO₄), chất tẩy rửa, sơn, sợi tổng hợp, chế biến dầu mỏ, điện giải ắc quy chì.",
        "safety": "CỰC KÌ NGUY HIỂM! Gây bỏng hóa chất sâu. Quy tắc vàng khi pha loãng: RÓT TỪ TỪ ACID VÀO NƯỚC dọc theo đũa thủy tinh và khuấy nhẹ — tuyệt đối KHÔNG làm ngược lại!",
    },
    "HNO3": {
        "state": "Chất lỏng không màu, bốc khói mạnh trong không khí ẩm; dễ bị phân hủy bởi ánh sáng tạo NO₂ màu nâu đỏ làm dung dịch ngả vàng.",
        "props": "Acid mạnh và là chất oxi hóa rất mạnh ở mọi nồng độ: oxi hóa hầu hết kim loại (trừ Au, Pt) lên số oxi hóa cao nhất (Fe → Fe³⁺, Cu → Cu²⁺) KHÔNG giải phóng H₂ mà tạo sản phẩm khử của N⁺⁵ (NO₂ với HNO₃ đặc, NO/N₂O/N₂/NH₄NO₃ với HNO₃ loãng). Oxi hóa cả phi kim (C, S, P) và nitro hóa hợp chất thơm. Al, Fe, Cr bị thụ động hóa trong HNO₃ đặc, nguội.",
        "prep": "Công nghiệp (quy trình Ostwald): oxi hóa NH₃ bằng O₂ (850 °C, xúc tác Pt) → NO → NO₂ → hấp thụ vào nước có O₂. Phòng thí nghiệm: NaNO₃ rắn + H₂SO₄ đặc, đun nhẹ.",
        "uses": "Sản xuất phân đạm ammonium nitrate (NH₄NO₃), thuốc nổ (TNT, nitroglycerin), thuốc nhuộm, dược phẩm và hòa tan/tinh chế kim loại (nước cường toan 1 HNO₃ : 3 HCl hòa tan được cả Au, Pt).",
        "safety": "Gây bỏng nặng và nhuộm vàng protein da (phản ứng xanthoproteic); bảo quản trong chai thủy tinh tối màu, nơi mát.",
    },
    "H3PO4": {
        "state": "Tinh thể trong suốt nóng chảy ở 42,5 °C; thường gặp dạng dung dịch đặc sánh 85%, không màu, không mùi, tan vô hạn trong nước.",
        "props": "Acid trung bình, 3 nấc phân li (nấc 1 mạnh nhất); không có tính oxi hóa mạnh như HNO₃ hay H₂SO₄ đặc. Khi tác dụng với kiềm (NaOH/KOH) tùy tỉ lệ mol T = n(OH⁻)/n(H₃PO₄) sẽ tạo muối H₂PO₄⁻ (T ≤ 1), HPO₄²⁻ (T = 2) hoặc PO₄³⁻ (T ≥ 3).",
        "prep": "Công nghiệp: cho quặng phosphorite/apatite Ca₃(PO₄)₂ tác dụng với H₂SO₄ đặc, hoặc đốt phosphorus trắng tạo P₄O₁₀ rồi hợp nước để thu acid tinh khiết.",
        "uses": "Sản xuất phân lân (superphosphate kép, ammophos), chất tạo vị chua trong nước giải khát (E338), xử lí chống gỉ kim loại và sản xuất chất tẩy rửa.",
        "safety": "Gây kích ứng da và mắt ở nồng độ cao; ít bay hơi nên dễ thao tác hơn HCl/HNO₃.",
    },
    "NaOH": {
        "state": "Chất rắn dạng hạt/vảy màu trắng, hút ẩm cực mạnh (chảy rữa ngoài không khí), tan nhiều trong nước và tỏa nhiệt mạnh; dung dịch có cảm giác nhờn tay.",
        "props": "Base mạnh (kiềm mạnh), phân li hoàn toàn tạo OH⁻: làm xanh quỳ tím, hóa hồng phenolphthalein; trung hòa mọi acid; hấp thụ CO₂, SO₂ tạo muối; tác dụng với dung dịch muối tạo kết tủa hydroxide; hòa tan kim loại/oxide/hydroxide lưỡng tính (Al, Zn, Al₂O₃, Al(OH)₃); thủy phân ester, chất béo (xà phòng hóa).",
        "prep": "Công nghiệp: điện phân dung dịch NaCl bão hòa có màng ngăn xốp (2NaCl + 2H₂O → 2NaOH + H₂ + Cl₂).",
        "uses": "Sản xuất xà phòng, chất tẩy rửa, giấy (tách lignin từ bột gỗ), tơ nhân tạo (viscose), tinh chế quặng bauxite (quy trình Bayer sản xuất Al), xử lí nước thải.",
        "safety": "Ăn mòn da và đặc biệt nguy hiểm cho mắt (xà phòng hóa mô sống); luôn bảo quản kín để tránh hút ẩm và hấp thụ CO₂ thành Na₂CO₃.",
    },
    "KOH": {
        "state": "Chất rắn màu trắng, hút ẩm rất mạnh, tan tốt trong nước và ethanol kèm tỏa nhiệt.",
        "props": "Base mạnh tương tự NaOH nhưng có tính kiềm nhỉnh hơn một chút; dùng nhiều trong phản ứng xà phòng hóa tạo xà phòng mềm và phản ứng tách HX trong dung môi rượu (KOH/C₂H₅OH, t°).",
        "prep": "Điện phân dung dịch KCl bão hòa có màng ngăn xốp.",
        "uses": "Sản xuất xà phòng lỏng/mềm, chất điện giải trong pin kiềm (alkaline battery), sản xuất phân bón chứa potassium và tổng hợp hữu cơ.",
        "safety": "Tính ăn mòn tương đương NaOH; tránh tiếp xúc da, mắt và đóng kín nắp sau khi dùng.",
    },
    "Ca(OH)2": {
        "state": "Chất rắn dạng bột màu trắng, ít tan trong nước (~1,7 g/L ở 20 °C); dung dịch trong suốt bão hòa gọi là nước vôi trong, hỗn hợp huyền phù gọi là vôi sữa.",
        "props": "Base mạnh (phần tan phân li hoàn toàn). Thuốc thử đặc trưng nhận biết khí CO₂ và SO₂ (làm đục nước vôi trong tạo kết tủa trắng CaCO₃/CaSO₃, nếu khí dư kết tủa tan lại tạo muối acid).",
        "prep": "Tôi vôi sống CaO bằng nước (CaO + H₂O → Ca(OH)₂, phản ứng tỏa nhiệt rất lớn).",
        "uses": "Vật liệu xây dựng (vữa vôi), khử chua đất nông nghiệp, làm mềm nước cứng tạm thời, sản xuất chloride vôi (CaOCl₂) và tinh chế đường mía.",
        "safety": "Bột vôi tôi gây kích ứng mắt, da và đường hô hấp; tránh tiếp xúc trực tiếp khi đang tôi vôi nóng.",
    },
    "Al(OH)3": {
        "state": "Chất rắn dạng kết tủa keo màu trắng, không tan trong nước.",
        "props": "Hydroxide lưỡng tính điển hình: vừa tan trong dung dịch acid mạnh (tạo Al³⁺) vừa tan trong dung dịch kiềm mạnh NaOH/KOH (tạo [Al(OH)₄]⁻ hay AlO₂⁻), nhưng KHÔNG tan trong dung dịch NH₃ dư hay CO₂ dư! Bị nhiệt phân thành Al₂O₃ và H₂O.",
        "prep": "Cho dung dịch muối Al³⁺ tác dụng với dung dịch NH₃ dư, hoặc sục khí CO₂ dư vào dung dịch Na[Al(OH)₄] (NaAlO₂).",
        "uses": "Chất keo tụ lọc trong nước (từ phèn chua), thuốc kháng acid dạ dày (antacid), chất chống cháy thân thiện môi trường cho nhựa và cáp điện.",
        "safety": "Độc tính rất thấp; an toàn trong y tế ở liều chỉ định.",
    },
    "CO2": {
        "state": "Chất khí không màu, không mùi, nặng gấp ~1,52 lần không khí; tan một phần trong nước tạo cân bằng yếu với H₂CO₃; hóa rắn ở −78,5 °C thành băng khô (thăng hoa trực tiếp).",
        "props": "Oxide acid: không duy trì sự cháy (trừ kim loại hoạt động rất mạnh như Mg cháy trong CO₂ tạo MgO + C). Tác dụng với dung dịch kiềm (NaOH, Ca(OH)₂, Ba(OH)₂) tạo muối carbonate trung hòa hoặc hydrogencarbonate tùy tỉ lệ mol.",
        "prep": "Phòng thí nghiệm: CaCO₃ + 2HCl → CaCl₂ + CO₂ + H₂O. Công nghiệp: thu hồi từ lò nung vôi, lên men rượu và đốt nhiên liệu.",
        "uses": "Quang hợp của thực vật; bình chữa cháy khí CO₂; tạo ga cho nước giải khát; băng khô bảo quản thực phẩm và tạo khói sân khấu; sản xuất urea và soda.",
        "safety": "Không độc nhưng gây ngạt ở nồng độ cao (> 5%) và là khí nhà kính chính gây biến đổi khí hậu; băng khô (−78,5 °C) gây bỏng lạnh.",
    },
    "CO": {
        "state": "Chất khí không màu, không mùi, không vị, hơi nhẹ hơn không khí (M = 28), hầu như không tan trong nước.",
        "props": "Oxide trung tính (không tạo muối, không tác dụng với nước, acid hay kiềm ở điều kiện thường). Tính khử rất mạnh ở nhiệt độ cao: khử nhiều oxide kim loại sau Al (Fe₂O₃, Fe₃O₄, CuO…) về kim loại; cháy trong O₂ với ngọn lửa xanh lam.",
        "prep": "Phòng thí nghiệm: tách nước formic acid HCOOH bằng H₂SO₄ đặc đun nóng. Công nghiệp: thổi hơi nước hoặc không khí qua than cốc nung đỏ (khí than ướt / khí than khô).",
        "uses": "Chất khử chủ lực trong luyện gang thép từ quặng sắt; nguyên liệu tổng hợp methanol, acetic acid và nhiên liệu khí công nghiệp.",
        "safety": "CỰC ĐỘC & KHÔNG MÙI! Liên kết chặt với hemoglobin trong máu mạnh gấp ~200 lần O₂ gây ngạt ngầm chết người — tuyệt đối không đốt than tổ ong/than củi trong phòng kín!",
    },
    "SO2": {
        "state": "Chất khí không màu, mùi hắc khó chịu (mùi diêm cháy), nặng gấp ~2,2 lần không khí, tan tốt trong nước.",
        "props": "Oxide acid (tác dụng với kiềm tạo muối sulfite/hydrogensulfite). Lưu huỳnh có số oxi hóa trung gian +4 nên SO₂ vừa có tính khử (làm mất màu dung dịch Br₂, KMnO₄; oxi hóa bởi O₂ tạo SO₃) vừa có tính oxi hóa (tác dụng với H₂S tạo kết tủa vàng S).",
        "prep": "Phòng thí nghiệm: Na₂SO₃ + H₂SO₄ (hoặc Cu + H₂SO₄ đặc, nóng). Công nghiệp: đốt sulfur (S) hoặc quặng pyrite (FeS₂).",
        "uses": "Nguyên liệu trung gian sản xuất H₂SO₄; chất tẩy trắng giấy, đường, sợi; chất chống nấm mốc/bảo quản rượu vang và hoa quả khô (liều kiểm soát).",
        "safety": "Khí độc gây kích ứng phế quản và là nguyên nhân chính gây mưa acid (tạo H₂SO₃/H₂SO₄ trong khí quyển).",
    },
    "NO2": {
        "state": "Chất khí màu nâu đỏ đặc trưng, mùi xốc khó chịu, nặng hơn không khí; ở nhiệt độ thấp dimer hóa thuận nghịch thành N₂O₄ không màu.",
        "props": "Oxide hỗn tạp: tác dụng với nước tạo hỗn hợp hai acid HNO₃ và HNO₂ (có O₂ tạo chỉ HNO₃); tác dụng với kiềm tạo hai muối nitrate và nitrite. Có tính oxi hóa mạnh.",
        "prep": "Cho Cu tác dụng với dung dịch HNO₃ đặc, hoặc nhiệt phân muối nitrate của kim loại trung bình (Cu(NO₃)₂, Pb(NO₃)₂), hoặc oxi hóa NO bằng O₂ trong không khí.",
        "uses": "Giai đoạn trung gian sản xuất HNO₃ (quy trình Ostwald); chất oxi hóa (dạng N₂O₄) trong động cơ tên lửa đẩy; chất xúc tác nitro hóa.",
        "safety": "Rất độc với phổi (có thể gây phù phổi muộn) và góp phần tạo sương mù quang hóa, mưa acid — luôn thao tác trong tủ hút.",
    },
    "Fe": {
        "state": "Kim loại màu trắng hơi xám, dẻo, dễ rèn, dẫn điện/nhiệt tốt và có tính nhiễm từ (sắt từ); D = 7,87 g/cm³, t_nc = 1538 °C.",
        "props": "Kim loại có tính khử trung bình với hai trạng thái oxi hóa phổ biến +2 và +3: tác dụng với chất oxi hóa yếu/trung bình (HCl, H₂SO₄ loãng, S, CuSO₄, FeCl₃) tạo hợp chất Fe(II); tác dụng với chất oxi hóa mạnh (Cl₂, HNO₃, H₂SO₄ đặc nóng) tạo hợp chất Fe(III). Bị thụ động hóa trong HNO₃ đặc nguội và H₂SO₄ đặc nguội.",
        "prep": "Luyện gang trong lò cao (khử quặng hematite Fe₂O₃, magnetite Fe₃O₄ bằng CO), sau đó luyện thép để giảm hàm lượng carbon và tạp chất.",
        "uses": "Kim loại quan trọng nhất nền văn minh hiện đại: sản xuất gang, thép xây dựng, cầu đường, ô tô, tàu thủy, máy móc, nam châm và là thành phần hemoglobin vận chuyển O₂ trong máu.",
        "safety": "Dễ bị ăn mòn điện hóa (gỉ sắt Fe₂O₃·nH₂O) trong không khí ẩm; bảo vệ bằng sơn phủ, mạ kẽm hoặc chế tạo thép không gỉ (inox).",
    },
    "Al": {
        "state": "Kim loại màu trắng bạc, rất nhẹ (D = 2,70 g/cm³), mềm, dễ dát mỏng và kéo sợi, dẫn điện/nhiệt rất tốt.",
        "props": "Kim loại có tính khử mạnh, bề mặt luôn được bảo vệ bởi lớp màng oxide Al₂O₃ siêu mỏng rất bền trong không khí và nước. Phản ứng mạnh với acid (HCl, H₂SO₄ loãng), tan trong dung dịch kiềm (NaOH, KOH) giải phóng H₂ (do lớp Al₂O₃ bị hòa tan rồi Al phản ứng với nước); phản ứng nhiệt nhôm (khử Fe₂O₃, Cr₂O₃ ở nhiệt độ cao). Bị thụ động hóa trong HNO₃ đặc nguội và H₂SO₄ đặc nguội.",
        "prep": "Điện phân nóng chảy Al₂O₃ tinh chế từ quặng bauxite với chất chảy cryolite (Na₃AlF₆) ở ~950 °C.",
        "uses": "Chế tạo hợp kim nhẹ cho máy bay, ô tô, khung cửa, dây dẫn điện cao thế, giấy bọc thực phẩm, lon nước giải khát và hỗn hợp thermite hàn đường ray.",
        "safety": "Không nên đựng thực phẩm quá chua (giấm, chanh) hoặc kiềm (nước vôi) lâu ngày trong đồ nhôm vì lớp màng bảo vệ bị hòa tan.",
    },
    "Cu": {
        "state": "Kim loại màu đỏ gạch đặc trưng, dẻo, độ dẫn điện và dẫn nhiệt đứng thứ 2 chỉ sau bạc (Ag); D = 8,96 g/cm³.",
        "props": "Kim loại kém hoạt động (đứng sau H trong dãy điện hóa): KHÔNG tan trong HCl và H₂SO₄ loãng (trừ khi có O₂). Tan tốt trong HNO₃ và H₂SO₄ đặc nóng tạo muối Cu²⁺ (dung dịch màu xanh lam đặc trưng); tan trong dung dịch FeCl₃ và AgNO₃.",
        "prep": "Luyện đồng từ quặng chalcopyrite (CuFeS₂) bằng phương pháp nhiệt luyện rồi tinh luyện bằng điện phân anode tan.",
        "uses": "Lõi dây cáp điện, mạch điện tử, ống dẫn nhiệt/điều hòa, hợp kim đồng thau (Cu–Zn), đồng thanh (Cu–Sn), đúc tượng và tiền xu.",
        "safety": "Các muối đồng hòa tan (CuSO₄) có độc tính với sinh vật thủy sinh và gây nôn nếu nuốt phải.",
    },
    "Na": {
        "state": "Kim loại kiềm màu trắng bạc, rất mềm (cắt được bằng dao), nhẹ hơn nước (D = 0,97 g/cm³), nóng chảy ở 97,8 °C.",
        "props": "Tính khử cực mạnh (nhóm IA): tự bốc cháy hoặc nóng chảy thành giọt tròn chạy trên mặt nước giải phóng H₂ và tạo dung dịch NaOH; phản ứng mãnh liệt với phi kim (Cl₂, O₂, S) và acid; cháy cho ngọn lửa màu vàng tươi đặc trưng.",
        "prep": "Điện phân nóng chảy NaCl (quy trình Downs, có thêm CaCl₂ hạ nhiệt độ nóng chảy) hoặc điện phân nóng chảy NaOH.",
        "uses": "Chất truyền nhiệt trong lò phản ứng hạt nhân nhanh, đèn hơi sodium ánh sáng vàng chiếu sáng đường phố, chất khử điều chế kim loại hiếm (Ti, Zr) và tổng hợp hữu cơ.",
        "safety": "Nguy hiểm cháy nổ khi tiếp xúc nước và độ ẩm! Luôn bảo quản ngập trong dầu hỏa khan; không chạm tay trần và không dập cháy bằng nước.",
    },
    "NaCl": {
        "state": "Tinh thể lập phương không màu/trắng, vị mặn đặc trưng, tan tốt trong nước (~36 g/100 g nước ở 20 °C), nóng chảy ở 801 °C.",
        "props": "Muối trung hòa của acid mạnh và base mạnh nên dung dịch có pH = 7. Tác dụng với dung dịch AgNO₃ tạo kết tủa trắng AgCl (nhận biết ion Cl⁻); rắn + H₂SO₄ đặc tạo khí HCl; điện phân dung dịch tạo NaOH, Cl₂, H₂ (hoặc nước Javel nếu không màng ngăn); điện phân nóng chảy tạo Na và Cl₂.",
        "prep": "Khai thác bằng cách làm bay hơi nước biển trên ruộng muối hoặc khai thác mỏ muối đá tự nhiên.",
        "uses": "Gia vị và bảo quản thực phẩm thiết yếu; nước muối sinh lí 0,9% trong y tế; nguyên liệu nền tảng của công nghiệp chlor-alkali (sản xuất NaOH, Cl₂, H₂, Na₂CO₃, NaHCO₃).",
        "safety": "An toàn; tuy nhiên tiêu thụ quá nhiều muối (> 5 g/ngày theo WHO) làm tăng nguy cơ cao huyết áp và bệnh tim mạch.",
    },
    "Na2CO3": {
        "state": "Chất rắn dạng bột màu trắng (soda khan), dễ tan trong nước; dung dịch có môi trường kiềm rõ rệt (pH ≈ 11,5) do ion CO₃²⁻ bị thủy phân.",
        "props": "Muối của acid yếu: sủi bọt khí CO₂ mạnh khi gặp acid; tạo kết tủa carbonate với Ca²⁺, Ba²⁺, Mg²⁺ (làm mềm mọi loại nước cứng); bền nhiệt không bị phân hủy khi đun nóng.",
        "prep": "Công nghiệp (quy trình Solvay): từ NaCl, NH₃, CO₂ và CaCO₃ (tạo NaHCO₃ kết tủa rồi nhiệt phân thành Na₂CO₃).",
        "uses": "Sản xuất thủy tinh, xà phòng và bột giặt, giấy, dệt nhuộm, làm mềm nước cứng và điều chế nhiều muối sodium khác.",
        "safety": "Bụi soda gây kích ứng mắt và đường hô hấp nhẹ.",
    },
    "NaHCO3": {
        "state": "Chất rắn dạng bột mịn màu trắng (baking soda), ít tan trong nước hơn Na₂CO₃; dung dịch có tính kiềm rất nhẹ (pH ≈ 8,3).",
        "props": "Muối acid có tính lưỡng tính: vừa phản ứng với acid (sủi bọt khí CO₂ nhanh) vừa phản ứng với dung dịch kiềm (tạo muối trung hòa CO₃²⁻). Dễ bị nhiệt phân ở ~100–200 °C thành Na₂CO₃, CO₂ và H₂O.",
        "prep": "Giai đoạn trung gian của quy trình Solvay hoặc sục khí CO₂ dư vào dung dịch Na₂CO₃ bão hòa.",
        "uses": "Bột nở làm bánh (sinh CO₂ làm xốp bánh), thuốc giảm đau dạ dày (trung hòa HCl dư), khử mùi, làm sạch nhà bếp và bột chữa cháy.",
        "safety": "Rất an toàn (dùng được trong thực phẩm và dược phẩm).",
    },
    "CaCO3": {
        "state": "Chất rắn màu trắng (đá vôi, đá hoa, đá phấn, vỏ sò ốc), hầu như không tan trong nước tinh khiết.",
        "props": "Tan mạnh trong dung dịch acid giải phóng CO₂; bị nhiệt phân ở ~900–1000 °C tạo vôi sống CaO và CO₂; tan chậm trong nước có hòa tan CO₂ tạo Ca(HCO₃)₂ (cơ chế hình thành hang động karst và thạch nhũ đá vôi).",
        "prep": "Khai thác trực tiếp từ các mỏ đá vôi tự nhiên; trong PTN tạo kết tủa khi sục CO₂ vào nước vôi trong Ca(OH)₂.",
        "uses": "Sản xuất xi măng, vôi sống, thủy tinh; chất độn trong sơn, nhựa, giấy, kem đánh răng; bổ sung calcium trong y học.",
        "safety": "An toàn sinh học.",
    },
    "CuSO4": {
        "state": "CuSO₄ khan dạng bột màu trắng (hút ẩm mạnh chuyển sang màu xanh lam thành tinh thể CuSO₄·5H₂O — phèn xanh); tan tốt trong nước tạo dung dịch màu xanh lam.",
        "props": "Thể hiện tính chất muối Cu²⁺: tác dụng với kiềm tạo kết tủa xanh lam Cu(OH)₂; phản ứng với kim loại đứng trước Cu (Fe, Zn, Mg) đẩy Cu đỏ bám lên bề mặt; tác dụng với BaCl₂ tạo kết tủa trắng BaSO₄; điện phân dung dịch thu Cu ở cathode và O₂ ở anode.",
        "prep": "Hòa tan CuO trong H₂SO₄ loãng hoặc cho Cu tác dụng với H₂SO₄ đặc nóng (hoặc H₂SO₄ loãng có sục khí O₂).",
        "uses": "CuSO₄ khan dùng phát hiện vết nước trong dung môi hữu cơ; thuốc trừ nấm Bordeaux (CuSO₄ + Ca(OH)₂) trong nông nghiệp; dung dịch mạ đồng và xử lí tảo hồ bơi.",
        "safety": "Có hại nếu nuốt phải và độc với cá/sinh vật nước; rửa tay sạch sau khi thao tác.",
    },
    "AgNO3": {
        "state": "Tinh thể không màu, rất dễ tan trong nước; bị phân hủy dần dưới ánh sáng mạnh nên đựng trong lọ thủy tinh tối màu.",
        "props": "Thuốc thử kinh điển nhận biết các ion halide (AgCl trắng, AgBr vàng nhạt, AgI vàng đậm) và phosphate (Ag₃PO₄ vàng). Oxi hóa được Fe²⁺ thành Fe³⁺ (tạo kết tủa Ag), và là thành phần của thuốc thử Tollens [Ag(NH₃)₂]OH tráng gương aldehyde/glucose.",
        "prep": "Hòa tan kim loại bạc (Ag) trong dung dịch HNO₃ loãng.",
        "uses": "Thuốc thử phân tích định tính/định lượng, phản ứng tráng gương, sản xuất phim ảnh truyền thống và chất sát khuẩn y tế.",
        "safety": "Gây vết đen khó rửa trên da (tạo bạc kim loại mịn) và ăn mòn nhẹ; tránh ánh sáng trực tiếp.",
    },
    "KMnO4": {
        "state": "Tinh thể hình lăng trụ màu tím đen ánh kim (thuốc tím), tan trong nước tạo dung dịch màu tím đỏ đậm.",
        "props": "Chất oxi hóa cực mạnh phụ thuộc môi trường: trong môi trường acid (H₂SO₄) khử về Mn²⁺ không màu; môi trường trung tính về kết tủa nâu đen MnO₂; môi trường kiềm về MnO₄²⁻ màu xanh lục. Làm mất màu tức thì alkene, alkyne, SO₂, H₂S, Fe²⁺; oxi hóa nhánh alkyl của arene (toluene → benzoic acid) khi đun nóng. Bị nhiệt phân tạo O₂.",
        "prep": "Oxi hóa quặng pyrolusite (MnO₂) bằng KOH và O₂ nóng chảy tạo K₂MnO₄, sau đó điện phân hoặc oxi hóa bằng Cl₂.",
        "uses": "Điều chế O₂ trong PTN; chất chuẩn độ oxi hóa – khử (phương pháp permanganate); sát khuẩn vết thương loãng, rửa rau củ và xử lí nước nuôi trồng thủy sản.",
        "safety": "Chất oxi hóa mạnh — KHÔNG trộn với glycerol, đường hay chất dễ cháy (có thể tự bốc cháy!).",
    },
    "CH4": {
        "state": "Chất khí không màu, không mùi, nhẹ hơn không khí (M = 16), hầu như không tan trong nước; thành phần chính của khí thiên nhiên và khí biogas.",
        "props": "Alkane đơn giản nhất (phân tử tứ diện đều, góc 109,5°, chỉ có liên kết đơn C–H bền): tương đối trơ ở điều kiện thường (không làm mất màu Br₂ hay KMnO₄). Tham gia phản ứng thế chlorine khi có ánh sáng (tạo CH₃Cl, CH₂Cl₂, CHCl₃, CCl₄), phản ứng cháy tỏa nhiều nhiệt và nhiệt phân ở 1500 °C làm lạnh nhanh tạo acetylene (C₂H₂).",
        "prep": "Khai thác khí thiên nhiên, khí dầu mỏ, biogas. Phòng thí nghiệm: nung nóng CH₃COONa với vôi tôi xút (NaOH + CaO) hoặc thủy phân Al₄C₃.",
        "uses": "Nhiên liệu sạch sinh nhiệt lớn (bếp gas, nhà máy nhiệt điện khí), nguyên liệu sản xuất H₂, methanol, acetylene và muội than.",
        "safety": "Cực kì dễ cháy nổ trong không khí (nổ hầm lò khi tỉ lệ CH₄ : O₂ ≈ 1 : 2); gas thương mại được pha thêm chất tạo mùi để dễ phát hiện rò rỉ.",
    },
    "C2H4": {
        "state": "Chất khí không màu, mùi hơi ngọt nhẹ, nhẹ hơn không khí một chút, rất ít tan trong nước.",
        "props": "Alkene đơn giản nhất có 1 liên kết đôi C=C (1 σ + 1 π kém bền) nên rất hoạt động: phản ứng cộng (H₂, Br₂ làm mất màu nước bromine ngay lập tức, HCl, H₂O tạo ethanol), trùng hợp tạo nhựa polyethylene (PE), và bị oxi hóa không hoàn toàn bởi dung dịch KMnO₄ (mất màu tím tạo ethylene glycol + MnO₂ nâu đen).",
        "prep": "Phòng thí nghiệm: tách nước ethanol (C₂H₅OH) với H₂SO₄ đặc ở 170 °C. Công nghiệp: cracking dầu mỏ hoặc tách H₂ từ ethane.",
        "uses": "Sản xuất nhựa PE, PVC, ethanol công nghiệp, ethylene glycol (chất chống đông) và là hormone thực vật kích thích quả chín đều.",
        "safety": "Khí dễ cháy nổ khi trộn với không khí.",
    },
    "C2H2": {
        "state": "Chất khí không màu, không mùi khi tinh khiết (khí điều chế từ đất đèn có mùi tỏi do tạp chất PH₃/H₂S), ít tan trong nước.",
        "props": "Alkyne đơn giản nhất có liên kết ba C≡C (1 σ + 2 π) và nguyên tử H linh động ở đầu mạch: cộng 2 phân tử H₂/Br₂/HCl (hoặc dừng ở alkene với xúc tác Pd/PbCO₃); cộng H₂O (xúc tác HgSO₄/H₂SO₄ 80 °C) tạo ethanal (CH₃CHO); phản ứng đặc trưng tạo kết tủa vàng nhạt Ag₂C₂ với dung dịch AgNO₃/NH₃; dimer hóa tạo vinylacetylene và trimer hóa (600 °C, C) tạo benzene.",
        "prep": "Phòng thí nghiệm: cho đất đèn CaC₂ tác dụng với nước. Công nghiệp: nhiệt phân methane (CH₄) ở 1500 °C rồi làm lạnh nhanh.",
        "uses": "Đèn xì oxygen–acetylene hàn cắt kim loại (nhiệt độ ngọn lửa lên tới ~3000 °C), nguyên liệu tổng hợp PVC, cao su chloroprene và acetic acid.",
        "safety": "Rất dễ cháy nổ ngay cả khi chịu áp suất cao (phải hòa tan trong acetone đựng trong bình xốp chuyên dụng).",
    },
    "C6H6": {
        "state": "Chất lỏng không màu, mùi thơm nhẹ đặc trưng, nhẹ hơn nước và không tan trong nước, sôi ở 80,1 °C, hóa rắn ở 5,5 °C.",
        "props": "Arene điển hình với hệ 6 electron π liên hợp kín rất bền: “dễ thế, khó cộng, bền với chất oxi hóa” (không làm mất màu nước bromine hay KMnO₄). Tham gia phản ứng thế bromine (xúc tác bột Fe/FeBr₃), nitro hóa (HNO₃/H₂SO₄ đặc tạo nitrobenzene), cộng H₂ (Ni, t°) tạo cyclohexane và cộng Cl₂ (ánh sáng UV) tạo 666.",
        "prep": "Chưng cất nhựa than đá và reforming xúc tác phân đoạn dầu mỏ (dehydrogen hóa cyclohexane / hexane).",
        "uses": "Nguyên liệu quan trọng tổng hợp styrene (nhựa PS), phenol, aniline, nylon, chất tẩy rửa tổng hợp và dược phẩm.",
        "safety": "ĐỘC & GÂY UNG THƯ (tác động tủy xương)! Hạn chế tối đa tiếp xúc trực tiếp và chỉ dùng trong tủ hút.",
    },
    "C2H5OH": {
        "state": "Chất lỏng không màu, mùi thơm nhẹ đặc trưng, vị cay, sôi ở 78,3 °C, nhẹ hơn nước (D = 0,789 g/cm³); tan vô hạn trong nước nhờ tạo liên kết hydrogen.",
        "props": "Alcohol bậc I điển hình: tác dụng với kim loại kiềm (Na, K) giải phóng H₂; phản ứng tách nước tạo alkene C₂H₄ (H₂SO₄ đặc, 170 °C) hoặc diethyl ether (140 °C); oxi hóa không hoàn toàn bởi CuO đun nóng tạo ethanal CH₃CHO; lên men giấm tạo CH₃COOH; ester hóa với carboxylic acid; cháy tỏa nhiều nhiệt.",
        "prep": "Lên men tinh bột/đường glucose bằng enzyme nấm men; trong công nghiệp còn sản xuất bằng cách hydrate hóa ethylene (C₂H₄ + H₂O, xúc tác H₃PO₄, 300 °C).",
        "uses": "Cồn sát khuẩn y tế 70°–75°, dung môi công nghiệp và nước hoa, nhiên liệu sinh học xăng E5/E10, sản xuất đồ uống có cồn và tổng hợp acetic acid, ethyl acetate.",
        "safety": "Rất dễ cháy (ngọn lửa xanh nhạt khó thấy ban ngày); lạm dụng đồ uống có cồn gây hại gan và thần kinh.",
    },
    "CH3OH": {
        "state": "Chất lỏng không màu, mùi tương tự ethanol, sôi ở 64,7 °C, tan vô hạn trong nước.",
        "props": "Alcohol đơn giản nhất: tác dụng với Na, oxi hóa bởi CuO tạo methanal (HCHO), ester hóa với carboxylic acid, cháy ngọn lửa xanh.",
        "prep": "Công nghiệp: tổng hợp từ khí tổng hợp (CO + 2H₂, xúc tác ZnO/Cr₂O₃ hoặc CuO, 200–300 °C, áp suất cao).",
        "uses": "Sản xuất formaldehyde (HCHO), acetic acid, dung môi công nghiệp, nhiên liệu pin nhiên liệu trực tiếp (DMFC) và biodiesel.",
        "safety": "CỰC ĐỘC! Uống nhầm chỉ 10–30 mL methanol có thể gây mù vĩnh viễn (chuyển hóa thành HCHO và HCOOH) hoặc tử vong — tuyệt đối không dùng pha rượu!",
    },
    "C3H5(OH)3": {
        "state": "Chất lỏng sánh, không màu, không mùi, vị ngọt đậm, hút ẩm mạnh, sôi ở 290 °C, tan vô hạn trong nước.",
        "props": "Polyalcohol có 3 nhóm –OH liền kề nên ngoài tính chất chung của alcohol còn hòa tan kết tủa Cu(OH)₂ ở nhiệt độ thường tạo dung dịch phức màu xanh lam thẫm (phản ứng nhận biết polyalcohol kề nhau); tác dụng với HNO₃ đặc/H₂SO₄ đặc tạo nitroglycerin.",
        "prep": "Sản phẩm phụ của quá trình xà phòng hóa chất béo (triglyceride) hoặc sản xuất biodiesel; tổng hợp từ propene.",
        "uses": "Chất giữ ẩm trong mỹ phẩm, kem dưỡng da, kem đánh răng, dược phẩm, siro thuốc ho, phụ gia thực phẩm (E422) và sản xuất nitroglycerin (thuốc giãn mạch và thuốc nổ).",
        "safety": "An toàn, không độc; được sử dụng rộng rãi trong thực phẩm và mỹ phẩm.",
    },
    "C6H5OH": {
        "state": "Tinh thể không màu (dễ chuyển hồng khi để lâu ngoài không khí do bị oxi hóa nhẹ), mùi đặc trưng, nóng chảy ở 43 °C; ít tan trong nước lạnh nhưng tan vô hạn trên 66 °C.",
        "props": "Do ảnh hưởng qua lại giữa vòng benzene và nhóm –OH: (1) Có tính acid yếu hơn H₂CO₃ (không làm đổi màu quỳ tím, tan được trong NaOH tạo C₆H₅ONa nhưng bị CO₂ đẩy ngược lại thành phenol); (2) Vòng thơm hoạt hóa mạnh ở vị trí ortho, para: tạo kết tủa trắng 2,4,6-tribromophenol ngay với nước bromine và tạo picric acid (vàng) với HNO₃ đặc.",
        "prep": "Công nghiệp: phương pháp cumene (oxi hóa isopropylbenzene rồi thủy phân tạo đồng thời phenol và acetone). Ngoài ra thủy phân chlorobenzene bằng NaOH đặc ở nhiệt độ, áp suất cao.",
        "uses": "Sản xuất nhựa phenol–formaldehyde (bakelite), bisphenol A (nhựa polycarbonate), thuốc sát trùng, thuốc nhuộm và dược phẩm (aspirin, paracetamol).",
        "safety": "Độc và gây bỏng hóa chất nặng khi dính lên da (gây tê cục bộ nên dễ chủ quan); rửa ngay bằng nước nhiều hoặc dung dịch PEG nếu bị dính.",
    },
    "HCHO": {
        "state": "Chất khí không màu, mùi xốc rất hắc, tan rất tốt trong nước; dung dịch 37–40% gọi là formalin (fomon).",
        "props": "Aldehyde đơn giản nhất, hoạt động rất mạnh: có 2 nguyên tử H gắn nhóm –CHO nên khi tráng bạc với [Ag(NH₃)₂]OH cho tỉ lệ 1 HCHO → 4 Ag! Khử Cu(OH)₂/OH⁻ đun nóng tạo kết tủa đỏ gạch Cu₂O; cộng H₂ tạo CH₃OH; trùng ngưng với phenol/urea tạo nhựa.",
        "prep": "Oxi hóa methanol (CH₃OH) bằng O₂ không khí trên xúc tác Ag hoặc Fe₂O₃–MoO₃ ở 500–600 °C.",
        "uses": "Sản xuất nhựa phenol–formaldehyde, urea–formaldehyde (keo dán gỗ ép), chất bảo quản mẫu sinh học (formalin) và tẩy uế.",
        "safety": "Độc, gây kích ứng mắt/mũi mạnh và được xếp vào nhóm chất gây ung thư — cấm tuyệt đối dùng trong thực phẩm!",
    },
    "CH3CHO": {
        "state": "Chất lỏng không màu, rất dễ bay hơi (sôi ở 20,2 °C), mùi hăng táo xanh, tan vô hạn trong nước.",
        "props": "Aldehyde tiêu biểu: vừa có tính oxi hóa (cộng H₂ → C₂H₅OH) vừa có tính khử mạnh (tráng bạc 1 CH₃CHO → 2 Ag; tạo kết tủa đỏ gạch Cu₂O với Cu(OH)₂/NaOH đun nóng; làm mất màu nước bromine; bị O₂ oxi hóa thành CH₃COOH); tạo kết tủa vàng CHI₃ (iodoform) với I₂/NaOH.",
        "prep": "Oxi hóa không hoàn toàn ethylene (quy trình Wacker, xúc tác PdCl₂/CuCl₂), hydrate hóa acetylene hoặc oxi hóa ethanol bằng CuO.",
        "uses": "Nguyên liệu sản xuất acetic acid, ethyl acetate, butan-1-ol, nhựa và hương liệu.",
        "safety": "Dễ cháy, dễ bay hơi và gây kích ứng hô hấp.",
    },
    "CH3COOH": {
        "state": "Chất lỏng không màu, vị chua, mùi giấm đặc trưng, sôi ở 118 °C; nguyên chất đông đặc ở 16,6 °C giống nước đá nên gọi là acetic acid băng; tan vô hạn trong nước.",
        "props": "Carboxylic acid điển hình, tính acid yếu (pK_a = 4,76) nhưng mạnh hơn H₂CO₃ và phenol: làm quỳ tím hóa đỏ nhạt, tác dụng với kim loại trước H, base, oxide base và muối carbonate (sủi bọt CO₂); phản ứng ester hóa thuận nghịch với alcohol (xúc tác H₂SO₄ đặc, t°).",
        "prep": "Công nghiệp: carbonyl hóa methanol (CH₃OH + CO, xúc tác Rh/Ir) hoặc oxi hóa butane/ethanal. Sinh học: lên men giấm từ dung dịch ethanol loãng.",
        "uses": "Giấm ăn (dung dịch 2–5%), sản xuất vinyl acetate (keo sữa PVA), cellulose acetate (tơ nhân tạo), dung môi ethyl acetate và tổng hợp aspirin.",
        "safety": "Acetic acid đậm đặc (> 80%) gây bỏng da và ăn mòn mạnh; giấm ăn 2–5% an toàn trong nấu ăn.",
    },
    "CH3COOC2H5": {
        "state": "Chất lỏng không màu, mùi thơm dễ chịu (hương lê/táo chín), sôi ở 77,1 °C, nhẹ hơn nước và ít tan trong nước (tách lớp trên mặt nước).",
        "props": "Ester điển hình: thủy phân thuận nghịch trong môi trường acid (tạo lại CH₃COOH và C₂H₅OH) và thủy phân một chiều trong môi trường kiềm (phản ứng xà phòng hóa tạo muối CH₃COONa và C₂H₅OH).",
        "prep": "Đun hồi lưu hỗn hợp acetic acid và ethanol có xúc tác H₂SO₄ đặc (phản ứng ester hóa Fischer).",
        "uses": "Dung môi xanh ít độc dùng trong sơn, mực in, nước tẩy sơn móng tay (thay acetone), tách caffeine khỏi cà phê và tạo hương thực phẩm.",
        "safety": "Chất lỏng rất dễ cháy; tránh xa tia lửa điện và nguồn nhiệt.",
    },
    "C6H12O6": {
        "state": "Chất rắn kết tinh không màu, vị ngọt dịu (ngọt bằng ~0,7 lần đường mía), tan rất tốt trong nước; tồn tại chủ yếu ở dạng vòng 6 cạnh pyranose (α và β) cân bằng với dạng mạch hở.",
        "props": "Monosaccharide chứa đồng thời 5 nhóm –OH kề nhau và 1 nhóm –CHO: (1) Hòa tan Cu(OH)₂ ở nhiệt độ thường tạo dung dịch xanh lam thẫm; (2) Phản ứng tráng bạc (1 glucose → 2 Ag), khử Cu(OH)₂ đun nóng tạo đỏ gạch Cu₂O, làm mất màu nước bromine (tạo gluconic acid); (3) Cộng H₂ tạo sorbitol; (4) Lên men rượu tạo 2 C₂H₅OH + 2 CO₂.",
        "prep": "Tự nhiên: tổng hợp nhờ quá trình quang hợp ở cây xanh, có nhiều trong quả nho chín và mật ong. Công nghiệp: thủy phân tinh bột hoặc cellulose bằng acid/enzyme.",
        "uses": "Nguồn năng lượng trực tiếp của tế bào (nồng độ đường huyết chuẩn ~4,4–7,2 mmol/L), dịch truyền tĩnh mạch y tế, tráng gương/tráng ruột phích, sản xuất ethanol và vitamin C.",
        "safety": "An toàn sinh học; người bệnh đái tháo đường cần kiểm soát lượng glucose nạp vào.",
    },
    "C12H22O11": {
        "state": "Tinh thể không màu, vị ngọt đậm, tan rất tốt trong nước (tăng nhanh theo nhiệt độ); có nhiều trong mía, củ cải đường và hoa thốt nốt.",
        "props": "Disaccharide cấu tạo từ 1 gốc α-glucose liên kết với 1 gốc β-fructose qua nguyên tử oxygen (C1–O–C2) nên KHÔNG còn nhóm –CHO tự do: hòa tan Cu(OH)₂ tạo dung dịch xanh lam thẫm nhưng KHÔNG tham gia phản ứng tráng bạc! Khi thủy phân (acid/enzyme) tạo hỗn hợp equimolar glucose + fructose (lúc này mới tráng bạc được).",
        "prep": "Ép nước mía/củ cải đường, làm sạch bằng sữa vôi, lọc tẩy màu và kết tinh chân không.",
        "uses": "Thực phẩm thiết yếu (đường kính), công nghiệp bánh kẹo, đồ uống, pha chế dược phẩm và nguyên liệu sản xuất ethanol.",
        "safety": "Tiêu thụ quá mức làm tăng nguy cơ sâu răng, béo phì và đái tháo đường type 2.",
    },
    "C6H5NH2": {
        "state": "Chất lỏng dạng dầu, không màu khi mới chưng cất (để lâu ngoài không khí hóa nâu đen), mùi đặc trưng, sôi ở 184 °C, ít tan trong nước và nặng hơn nước.",
        "props": "Amine thơm điển hình: (1) Tính base rất yếu do cặp electron trên N liên hợp vào vòng benzene — KHÔNG làm đổi màu quỳ tím nhưng tan trong HCl tạo muối phenylammonium chloride (C₆H₅NH₃Cl); (2) Nhóm –NH₂ hoạt hóa mạnh vòng benzene nên tạo ngay kết tủa trắng 2,4,6-tribromoaniline với nước bromine.",
        "prep": "Khử nitrobenzene (C₆H₅NO₂) bằng Fe + HCl hoặc hydrogen hóa xúc tác (Ni/Pd).",
        "uses": "Sản xuất polyurethane (MDI), phẩm nhuộm azo, chất xúc tiến lưu hóa cao su và dược phẩm (paracetamol, sulfonamide).",
        "safety": "Rất độc (hấp thụ qua cả da và đường hô hấp, gây methemoglobin huyết); thao tác phải mang găng tay và dùng tủ hút.",
    },
    "H2NCH2COOH": {
        "state": "Tinh thể màu trắng, vị hơi ngọt, dễ tan trong nước, nóng chảy (phân hủy) ở ~233 °C do tồn tại ở dạng ion lưỡng cực ⁺H₃N–CH₂–COO⁻.",
        "props": "Amino acid đơn giản nhất, có tính lưỡng tính rõ rệt: vừa tác dụng với acid mạnh (HCl) vừa tác dụng với base mạnh (NaOH); dung dịch gần như trung tính (không đổi màu quỳ tím); tham gia phản ứng ester hóa với alcohol và trùng ngưng tạo chuỗi peptide/protein.",
        "prep": "Thủy phân protein (nhất là collagen/gelatin) hoặc tổng hợp từ chloroacetic acid và NH₃.",
        "uses": "Đơn vị cấu tạo protein và collagen trong cơ thể, chất dẫn truyền thần kinh ức chế, chất điều vị thực phẩm và dung dịch đệm sinh hóa.",
        "safety": "An toàn sinh học.",
    },
    "C9H8O4": {
        "state": "Tinh thể hình kim màu trắng, không mùi (có mùi giấm nhẹ nếu bị ẩm thủy phân), ít tan trong nước lạnh, tan tốt trong ethanol.",
        "props": "Aspirin (acetylsalicylic acid) chứa đồng thời nhóm carboxylic acid (–COOH) và nhóm ester của phenol (–OCOCH₃): tác dụng với NaHCO₃ (sủi CO₂), khi đun nóng với NaOH dư tiêu thụ tỉ lệ 1 : 3 (1 mol –COOH + 2 mol ester của phenol).",
        "prep": "Ester hóa salicylic acid với acetic anhydride ((CH₃CO)₂O) có xúc tác H₂SO₄ hoặc H₃PO₄.",
        "uses": "Thuốc giảm đau, hạ sốt, kháng viêm kinh điển; liều thấp (75–100 mg/ngày) giúp chống kết tập tiểu cầu phòng ngừa nhồi máu cơ tim và đột quỵ.",
        "safety": "Có thể gây kích ứng/loét dạ dày; KHÔNG dùng cho trẻ em đang sốt virus (nguy cơ hội chứng Reye).",
    },
    "C8H9NO2": {
        "state": "Bột kết tinh màu trắng, không mùi, vị hơi đắng, tan ít trong nước lạnh, tan tốt trong nước nóng và ethanol.",
        "props": "Paracetamol (acetaminophen) chứa nhóm phenol (–OH) và nhóm amide (–NHCOCH₃): cho phức màu tím đặc trưng với FeCl₃, bị thủy phân trong môi trường acid/kiềm đun nóng tạo p-aminophenol và acetic acid.",
        "prep": "Acetyl hóa p-aminophenol bằng acetic anhydride.",
        "uses": "Thuốc hạ sốt và giảm đau phổ biến nhất thế giới, ít gây kích ứng dạ dày hơn aspirin.",
        "safety": "Tuyệt đối KHÔNG dùng quá liều (> 4 g/ngày ở người lớn) hoặc uống chung với rượu bia vì gây tổn thương gan cấp rất nguy hiểm!",
    },
    "C8H10N4O2": {
        "state": "Tinh thể hình kim màu trắng mượt, vị đắng, ít tan trong nước lạnh nhưng tan tốt trong nước nóng và chloroform; thăng hoa ở ~178 °C.",
        "props": "Alkaloid nhóm xanthine (dị vòng purine), có tính base rất yếu.",
        "prep": "Chiết xuất từ hạt cà phê, lá trà xanh, hạt ca cao hoặc tổng hợp hóa học.",
        "uses": "Chất kích thích hệ thần kinh trung ương tự nhiên giúp tỉnh táo, tăng tập trung (có trong cà phê, trà, nước tăng lực) và phối hợp trong một số thuốc giảm đau đầu.",
        "safety": "Liều khuyến nghị người lớn khỏe mạnh ≤ 400 mg/ngày (~3–4 tách cà phê); dùng quá nhiều gây mất ngủ, hồi hộp, tim đập nhanh.",
    },
    "C6H8O6": {
        "state": "Tinh thể màu trắng hoặc hơi vàng nhạt, vị chua dễ chịu, tan rất tốt trong nước.",
        "props": "Vitamin C (L-ascorbic acid) có cấu trúc enediol nên có tính acid yếu và TÍNH KHỬ (chống oxi hóa) rất mạnh: làm mất màu dung dịch iodine (I₂) và KMnO₄ ngay lập tức; dễ bị phân hủy bởi nhiệt độ cao và O₂ không khí.",
        "prep": "Có tự nhiên trong trái cây họ cam chanh, ổi, ớt chuông; công nghiệp sản xuất từ D-glucose (quy trình Reichstein / lên men sinh học).",
        "uses": "Thiết yếu cho tổng hợp collagen, tăng cường miễn dịch, hấp thụ sắt và chống oxi hóa; phụ gia chống thâm thực phẩm (E300).",
        "safety": "Vitamin tan trong nước nên ít tích lũy; tuy nhiên dùng liều quá cao kéo dài (> 2 g/ngày) có thể gây rối loạn tiêu hóa hoặc tăng nguy cơ sỏi thận oxalate.",
    },
    "Na2SO4": {
        "state": "Tinh thể trắng, tan tốt trong nước; dạng ngậm nước Na₂SO₄·10H₂O gọi là muối Glauber.",
        "props": "Muối trung hòa bền, dung dịch pH = 7; tạo kết tủa trắng BaSO₄ không tan trong acid với BaCl₂/Ba(OH)₂.",
        "prep": "Thu hồi từ mỏ tự nhiên hoặc sản phẩm phụ sản xuất HCl (2NaCl + H₂SO₄ → Na₂SO₄ + 2HCl).",
        "uses": "Chất độn bột giặt, sản xuất bột giấy (quy trình Kraft), thủy tinh và chất hút ẩm làm khô dung môi hữu cơ trong PTN.",
        "safety": "Độc tính rất thấp.",
    },
    "BaSO4": {
        "state": "Chất rắn bột màu trắng tinh khiết, nặng (D = 4,5 g/cm³), hầu như KHÔNG tan trong nước cũng như mọi acid/kiềm thông thường.",
        "props": "Rất trơ về mặt hóa học; sự hình thành kết tủa trắng BaSO₄ là phản ứng định tính/định lượng chuẩn để nhận biết ion SO₄²⁻ và Ba²⁺.",
        "prep": "Cho dung dịch muối Ba²⁺ (BaCl₂, Ba(NO₃)₂) tác dụng với dung dịch muối SO₄²⁻ hoặc H₂SO₄.",
        "uses": "Chất cản quang đường tiêu hóa khi chụp X-quang (do không tan nên không gây ngộ độc Ba²⁺), chất độn trắng cao cấp trong sơn, giấy và dung dịch khoan dầu khí.",
        "safety": "An toàn nhờ độ tan cực nhỏ (trái ngược với các muối Ba²⁺ tan như BaCl₂ rất độc!).",
    },
    "Fe2O3": {
        "state": "Chất rắn dạng bột màu đỏ nâu (quặng hematite và thành phần chính của gỉ sắt), không tan trong nước.",
        "props": "Oxide base: tan trong HCl, H₂SO₄ loãng tạo muối Fe(III) màu vàng nâu; bị khử bởi CO, H₂, C ở nhiệt độ cao về Fe; tham gia phản ứng nhiệt nhôm với Al tạo Fe nóng chảy.",
        "prep": "Khai thác từ quặng hematite, hoặc nhiệt phân Fe(OH)₃ (2Fe(OH)₃ → Fe₂O₃ + 3H₂O) và đốt quặng pyrite FeS₂.",
        "uses": "Quặng luyện gang thép, bột màu đỏ oxit sắt trong sơn/gốm sứ, chất đánh bóng kính và hạt từ tính.",
        "safety": "Ít độc; tránh hít bụi mịn kéo dài.",
    },
    "CaO": {
        "state": "Chất rắn dạng cục màu trắng (vôi sống), hút ẩm rất mạnh, phản ứng tỏa nhiệt lớn với nước.",
        "props": "Oxide base mạnh: tác dụng mãnh liệt với nước tạo Ca(OH)₂, hấp thụ CO₂ tạo CaCO₃, tác dụng với mọi acid và oxide acid (SiO₂ tạo xỉ CaSiO₃).",
        "prep": "Nung đá vôi CaCO₃ ở 900–1000 °C (CaCO₃ → CaO + CO₂).",
        "uses": "Xây dựng, luyện kim (tạo xỉ loại tạp chất SiO₂/P/S), khử chua đất, xử lí nước thải và chất hút ẩm rẻ tiền.",
        "safety": "Gây bỏng nhiệt và bỏng kiềm khi gặp ẩm trên da/mắt; luôn đeo kính bảo hộ khi thao tác.",
    },
    "H2O2": {
        "state": "Chất lỏng không màu, hơi nhớt hơn nước, tan vô hạn trong nước; thường gặp dung dịch 3% (nước oxy già y tế) hoặc 30% trong PTN.",
        "props": "Nguyên tử O có số oxi hóa trung gian −1 nên vừa có tính oxi hóa mạnh (oxi hóa KI → I₂, Fe²⁺ → Fe³⁺) vừa có tính khử (làm mất màu KMnO₄/H⁺ giải phóng O₂); dễ tự phân hủy thành H₂O + O₂ khi có xúc tác MnO₂, ánh sáng hoặc enzyme catalase trong máu.",
        "prep": "Công nghiệp: quy trình anthraquinone (oxi hóa tự động từ H₂ và O₂).",
        "uses": "Sát trùng vết thương (3%), tẩy trắng bột giấy và vải sợi thân thiện môi trường, xử lí nước thải và chất đẩy tên lửa (nồng độ cao).",
        "safety": "Dung dịch ≥ 30% gây bỏng trắng da và có thể phân hủy nổ nếu nhiễm bụi kim loại; bảo quản trong chai tối màu mát mẻ.",
    },
    "KClO3": {
        "state": "Tinh thể trắng hình vảy, vị mặn mát, ít tan trong nước lạnh nhưng tan tốt trong nước nóng.",
        "props": "Chất oxi hóa mạnh ở trạng thái rắn và nóng chảy: nhiệt phân có xúc tác MnO₂ ở ~200 °C tạo KCl + O₂; tác dụng với HCl đặc tạo khí Cl₂.",
        "prep": "Điện phân dung dịch KCl nóng không có màng ngăn, hoặc sục Cl₂ vào dung dịch KOH đặc nóng.",
        "uses": "Điều chế O₂ trong PTN, thuốc đầu que diêm an toàn, pháo hoa và chất oxi hóa.",
        "safety": "Không nghiền chung với sulfur, phosphorus hay đường vì có thể gây nổ do ma sát!",
    },
    "NaClO": {
        "state": "Tồn tại chủ yếu trong dung dịch nước màu vàng lục nhạt có mùi chlorine đặc trưng (nước Javel).",
        "props": "Muối của acid rất yếu HClO (yếu hơn cả H₂CO₃) nên hấp thụ CO₂ không khí giải phóng HClO có tính oxi hóa tẩy màu và diệt khuẩn rất mạnh.",
        "prep": "Sục khí Cl₂ vào dung dịch NaOH nguội, hoặc điện phân dung dịch NaCl không có màng ngăn.",
        "uses": "Tẩy trắng quần áo, khử trùng bề mặt, xử lí nước sinh hoạt và hồ bơi.",
        "safety": "TUYỆT ĐỐI KHÔNG trộn nước Javel với chất tẩy rửa chứa acid (HCl, nước tẩy bồn cầu) vì sẽ sinh khí Cl₂ cực độc!",
    },
}


# Kiến thức nền theo từng nhóm phân loại IUPAC cho tất cả 705 chất còn lại
_CATEGORY_TEMPLATES = {
    "Acid vô cơ": {
        "state": "Thường tồn tại ở dạng dung dịch nước không màu hoặc chất rắn/khí dễ tan trong nước, có vị chua và làm đổi màu chất chỉ thị acid–base.",
        "props": "Phân li tạo ion H⁺ (H₃O⁺) trong dung dịch nước: làm đỏ quỳ tím, phản ứng trung hòa với base và oxide base tạo muối và nước, tác dụng với nhiều kim loại hoạt động và muối của acid yếu hơn.",
        "prep": "Điều chế bằng cách cho oxide acid hợp nước, trao đổi muối với acid mạnh ít bay hơi (như H₂SO₄ đặc) hoặc tổng hợp trực tiếp từ đơn chất.",
        "uses": "Hóa chất cơ bản trong phòng thí nghiệm, sản xuất phân bón, xử lí bề mặt kim loại, tổng hợp hóa chất và điều chỉnh pH.",
        "safety": "Acid đậm đặc có tính ăn mòn da và mắt — luôn đeo kính bảo hộ và pha loãng bằng cách rót từ từ acid vào nước.",
    },
    "Base - Hydroxide": {
        "state": "Các base kiềm (IA, Ba, Ca) là chất rắn trắng dễ hút ẩm, tan tạo dung dịch trơn nhờn; đa số hydroxide kim loại khác là chất rắn kết tủa màu đặc trưng, ít tan trong nước.",
        "props": "Base tan làm xanh quỳ tím và hóa hồng phenolphthalein, hấp thụ oxide acid (CO₂, SO₂) và phản ứng trao đổi với dung dịch muối. Mọi hydroxide đều bị trung hòa bởi acid; hydroxide không tan bị nhiệt phân thành oxide và H₂O.",
        "prep": "Base kiềm điều chế bằng điện phân dung dịch muối halide có màng ngăn hoặc cho kim loại/oxide tác dụng nước; hydroxide không tan điều chế bằng phản ứng trao đổi muối + kiềm.",
        "uses": "Sản xuất xà phòng, giấy, vật liệu xây dựng, xử lí nước thải, trung hòa acid và làm xúc tác trong công nghiệp hóa chất.",
        "safety": "Dung dịch kiềm đặc ăn mòn mạnh mô sinh học (đặc biệt là giác mạc); tránh tiếp xúc trực tiếp và bảo quản kín khí CO₂.",
    },
    "Oxide": {
        "state": "Oxide kim loại thường là chất rắn tinh thể có nhiệt độ nóng chảy cao; oxide phi kim thường ở thể khí, lỏng dễ bay hơi hoặc rắn phân tử.",
        "props": "Tùy bản chất nguyên tố mà thể hiện tính oxide base (tác dụng với acid), oxide acid (tác dụng với base), oxide lưỡng tính (tác dụng cả acid lẫn base như Al₂O₃, ZnO, Cr₂O₃) hoặc oxide trung tính (CO, NO, N₂O).",
        "prep": "Đốt cháy đơn chất trong oxygen, nhiệt phân muối carbonate/nitrate/hydroxide hoặc oxi hóa hợp chất ở nhiệt độ cao.",
        "uses": "Nguyên liệu luyện kim, sản xuất acid/base, vật liệu gốm sứ, thủy tinh, chất xúc tác và sắc tố vô cơ.",
        "safety": "Oxide kiềm dễ gây bỏng khi gặp ẩm; một số oxide phi kim dạng khí (SO₂, NO₂, CO) độc hại cần thao tác nơi thông thoáng.",
    },
    "Muối (Salts)": {
        "state": "Hợp chất ion kết tinh ở điều kiện thường, nhiệt độ nóng chảy cao; độ tan và màu sắc phụ thuộc bản chất cation kim loại và anion gốc acid.",
        "props": "Chất điện li mạnh khi tan trong nước. Tham gia phản ứng trao đổi ion với acid, base, muối khác (khi tạo kết tủa, khí hoặc chất điện li yếu), phản ứng thế với kim loại mạnh hơn và phản ứng nhiệt phân/điện phân.",
        "prep": "Phản ứng trung hòa acid–base, cho kim loại/oxide tác dụng với acid, phản ứng trao đổi dung dịch muối hoặc khai thác từ khoáng vật tự nhiên.",
        "uses": "Phân bón hóa học, hóa chất phân tích, mạ điện, y dược, thực phẩm, gốm thủy tinh và nguyên liệu công nghiệp vô cơ.",
        "safety": "Kiểm tra độc tính ion kim loại nặng (Pb²⁺, Hg²⁺, Ba²⁺ tan, Cr⁶⁺, Cd²⁺) và tránh hít bụi tinh thể.",
    },
    "Đơn chất (Elements)": {
        "state": "Đơn chất tinh khiết gồm một nguyên tố hóa học duy nhất; tính chất vật lí (kim loại sáng ánh kim dẫn điện tốt hay phi kim/khí hiếm) quyết định bởi cấu tạo mạng tinh thể hoặc phân tử.",
        "props": "Thể hiện số oxi hóa 0: kim loại có tính khử (nhường electron tạo cation), phi kim thường có tính oxi hóa (hoặc cả oxi hóa và khử), khí hiếm có lớp vỏ electron bão hòa rất trơ.",
        "prep": "Tách từ không khí lỏng, điện phân nóng chảy/dung dịch, nhiệt luyện hoặc thủy luyện từ quặng khoáng tự nhiên.",
        "uses": "Vật liệu kết cấu, điện tử, chất xúc tác, tổng hợp hợp chất vô cơ – hữu cơ và ứng dụng năng lượng, y học.",
        "safety": "Lưu ý tính dễ cháy/phản ứng mạnh với nước của kim loại kiềm và độc tính của halogen, kim loại nặng.",
    },
    "Hydrocarbon": {
        "state": "Hợp chất chỉ gồm C và H, không phân cực nên hầu như không tan trong nước, nhẹ hơn nước và tan tốt trong dung môi hữu cơ (C₁–C₄ thường là khí, C₅–C₁₇ là lỏng, ≥ C₁₈ là rắn).",
        "props": "Cháy hoàn toàn tạo CO₂ và H₂O tỏa nhiều nhiệt. Alkane đặc trưng bởi phản ứng thế halogen; alkene/alkyne có liên kết π dễ tham gia phản ứng cộng (H₂, Br₂, HX) và trùng hợp; arene dễ thế trên vòng thơm.",
        "prep": "Chưng cất phân đoạn và cracking/reforming dầu mỏ, khí thiên nhiên hoặc tổng hợp hữu cơ từ alcohol, dẫn xuất halogen.",
        "uses": "Nhiên liệu động cơ/nhiệt điện, dung môi không phân cực và monomer nền tảng của công nghiệp hóa dầu – nhựa polymer.",
        "safety": "Rất dễ cháy nổ khi hóa hơi trộn với không khí; bảo quản xa nguồn lửa và tia lửa điện.",
    },
    "Alcohol - Phenol - Ether": {
        "state": "Các alcohol mạch ngắn (C₁–C₃) tan vô hạn trong nước nhờ liên kết hydrogen và có nhiệt độ sôi cao hơn hydrocarbon tương ứng; ether dễ bay hơi và ít tan trong nước.",
        "props": "Alcohol phản ứng với kim loại kiềm (Na, K), tách nước tạo alkene/ether, ester hóa với acid và oxi hóa tạo aldehyde/ketone/acid. Phenol có tính acid yếu và dễ thế vào vòng thơm. Ether tương đối trơ, dùng làm dung môi.",
        "prep": "Hydrate hóa alkene, lên men carbohydrate, khử hợp chất carbonyl hoặc thủy phân dẫn xuất halogen.",
        "uses": "Dung môi phổ biến, nhiên liệu sinh học, chất sát khuẩn, nguyên liệu tổng hợp ester, nhựa và dược phẩm.",
        "safety": "Đa số dễ cháy; riêng methanol và phenol có độc tính cao, cần tránh tiếp xúc trực tiếp.",
    },
    "Aldehyde - Ketone": {
        "state": "Hợp chất chứa nhóm carbonyl (C=O) phân cực; các chất đầu dãy (HCHO, CH₃CHO, acetone) tan rất tốt trong nước và có mùi đặc trưng.",
        "props": "Tham gia phản ứng cộng hydrogen (tạo alcohol bậc I/II) và cộng nucleophile vào nhóm C=O. Riêng aldehyde có nhóm –CHO nên dễ bị oxi hóa (tráng bạc với [Ag(NH₃)₂]OH, tạo kết tủa đỏ gạch Cu₂O với Cu(OH)₂/OH⁻ đun nóng).",
        "prep": "Oxi hóa không hoàn toàn alcohol bậc I (tạo aldehyde) hoặc bậc II (tạo ketone), hydrate hóa alkyne hoặc oxi hóa alkene.",
        "uses": "Dung môi công nghiệp (acetone), sản xuất nhựa polymer, hương liệu mỹ phẩm (vanillin, cinnamaldehyde) và tổng hợp hữu cơ.",
        "safety": "Dễ bay hơi, dễ cháy và có thể gây kích ứng mắt/mũi khi hít ở nồng độ cao.",
    },
    "Carboxylic acid": {
        "state": "Phân tử tạo liên kết hydrogen bền (thường dạng dimer) nên có nhiệt độ sôi cao hơn hẳn alcohol tương ứng; các acid mạch ngắn có vị chua và tan tốt trong nước.",
        "props": "Thể hiện đầy đủ tính chất của một acid hữu cơ yếu (tác dụng với kim loại trước H, base, oxide base, muối carbonate) và phản ứng ester hóa thuận nghịch với alcohol tạo ester có mùi thơm.",
        "prep": "Oxi hóa aldehyde hoặc alcohol bậc I, lên men sinh học, thủy phân ester/nitrile hoặc carbonyl hóa alcohol.",
        "uses": "Chất bảo quản và tạo vị thực phẩm, tổng hợp ester/hương liệu, tơ sợi nhân tạo, nhựa và dược phẩm.",
        "safety": "Acid mạch ngắn đậm đặc (HCOOH, CH₃COOH) gây bỏng và kích ứng da, mắt.",
    },
    "Ester - Lipid": {
        "state": "Ester mạch ngắn là chất lỏng dễ bay hơi, nhẹ hơn nước, ít tan trong nước và thường có mùi thơm hoa quả đặc trưng; lipid (chất béo) là chất lỏng (dầu thực vật) hoặc rắn (mỡ động vật).",
        "props": "Đặc trưng bởi phản ứng thủy phân thuận nghịch trong môi trường acid và phản ứng xà phòng hóa một chiều trong môi trường kiềm (NaOH, KOH) tạo muối carboxylate + alcohol (hoặc glycerol với chất béo).",
        "prep": "Phản ứng ester hóa giữa carboxylic acid (hoặc anhydride) với alcohol, hoặc tách chiết trực tiếp dầu mỡ từ động thực vật.",
        "uses": "Hương liệu thực phẩm và nước hoa, dung môi sơn/mực in, sản xuất xà phòng, nhựa thủy tinh hữu cơ (PMMA) và năng lượng sinh học.",
        "safety": "Ester bay hơi dễ cháy; phần lớn có độc tính thấp.",
    },
    "Amine - Amino acid": {
        "state": "Amine mạch ngắn là khí có mùi khai/tanh giống NH₃, tan tốt trong nước; amino acid là tinh thể rắn có điểm nóng chảy cao do tồn tại ở dạng ion lưỡng cực.",
        "props": "Amine có tính base (nhận proton H⁺ từ acid tạo muối ammonium); amino acid có tính lưỡng tính (tác dụng cả acid lẫn base) và trùng ngưng tạo liên kết peptide (–CO–NH–).",
        "prep": "Khử hợp chất nitro (với amine thơm), alkyl hóa NH₃, hoặc thủy phân protein/lên men sinh học (với amino acid).",
        "uses": "Sản xuất dược phẩm, thuốc nhuộm, polymer (nylon, polyurethane), dinh dưỡng sinh học và chất điều vị (MSG).",
        "safety": "Nhiều amine thơm (aniline…) có độc tính cao, dễ thấm qua da; đa số α-amino acid tự nhiên an toàn sinh học.",
    },
    "Carbohydrate": {
        "state": "Hợp chất hữu cơ tạp chức có công thức chung C_n(H₂O)_m; đường đơn/đôi là tinh thể trắng vị ngọt dễ tan trong nước, polysaccharide (tinh bột, cellulose) là chất rắn không ngọt, không tan trong nước lạnh.",
        "props": "Chứa nhiều nhóm –OH kề nhau (đường tan hòa tan Cu(OH)₂ tạo phức xanh lam); đường khử (glucose, fructose, maltose) có phản ứng tráng bạc; disaccharide và polysaccharide bị thủy phân trong môi trường acid hoặc enzyme.",
        "prep": "Hình thành tự nhiên qua quá trình quang hợp ở thực vật xanh và chiết tách từ mía, ngũ cốc, bông gỗ.",
        "uses": "Nguồn năng lượng chính trong dinh dưỡng người và động vật, công nghiệp thực phẩm, sản xuất giấy, vải sợi, dược phẩm và nhiên liệu sinh học ethanol.",
        "safety": "An toàn sinh học.",
    },
    "Polymer - Vật liệu": {
        "state": "Hợp chất cao phân tử (M rất lớn) gồm nhiều mắt xích lặp lại; thường ở trạng thái rắn, không bay hơi, không có nhiệt độ nóng chảy cố định và không tan trong dung môi thông thường.",
        "props": "Phản ứng giữ nguyên mạch, cắt mạch (thủy phân/nhiệt phân) hoặc khâu mạch (lưu hóa cao su) làm thay đổi tính chất cơ lí (dẻo, đàn hồi, bền nhiệt).",
        "prep": "Phản ứng trùng hợp (từ monomer có liên kết bội/vòng kém bền) hoặc trùng ngưng (từ monomer có ít nhất 2 nhóm chức phản ứng).",
        "uses": "Chất dẻo (PE, PP, PVC, PET), tơ sợi dệt may (nylon, polyester), cao su lốp xe, keo dán và vật liệu composite công nghệ cao.",
        "safety": "Hạn chế đốt rác thải nhựa (sinh khí độc CO, HCl, dioxin) và ưu tiên tái chế, phân loại rác.",
    },
    "Hợp chất thơm & Dị vòng": {
        "state": "Chứa hệ vòng thơm liên hợp hoặc vòng có dị tố (N, O, S); đa số là chất lỏng mùi đặc trưng hoặc tinh thể kết tinh.",
        "props": "Hệ vòng thơm bền vững, ưu tiên phản ứng thế điện tử (SE); các dị vòng chứa N (pyridine, pyrrole, indole, purine) có tính chất acid–base đặc thù và là khung lõi của nhiều phân tử sinh học.",
        "prep": "Tách từ nhựa than đá, hóa dầu hoặc tổng hợp đóng vòng chuyên biệt.",
        "uses": "Nền tảng của công nghiệp dược phẩm, thuốc nhuộm, hương liệu, vật liệu bán dẫn hữu cơ (OLED) và hóa học sinh học (DNA/RNA).",
        "safety": "Nhiều dẫn xuất thơm độc và dễ cháy; thao tác trong không gian thông thoáng.",
    },
    "Dược phẩm - Vitamin - Sinh học": {
        "state": "Thường là tinh thể phân tử phức tạp có nhiều nhóm chức đặc hiệu quyết định hoạt tính sinh học tại thụ thể tế bào.",
        "props": "Tính chất hóa học là tổ hợp của các nhóm chức trên phân tử (acid, phenol, ester, amide, amine…); thường nhạy với ánh sáng, pH và nhiệt độ nên cần bảo quản đúng quy cách.",
        "prep": "Chiết tách từ dược liệu thiên nhiên, lên men vi sinh hoặc tổng hợp hữu cơ chọn lọc lập thể.",
        "uses": "Phòng và điều trị bệnh, bổ sung vi chất dinh dưỡng thiết yếu, nghiên cứu y sinh và hóa dược.",
        "safety": "Mọi dược chất chỉ sử dụng đúng liều lượng và hướng dẫn chuyên môn; tuyệt đối không tự ý dùng hóa chất phòng thí nghiệm thay thế thuốc!",
    },
}

_DEFAULT_TEMPLATE = {
    "state": "Hợp chất hóa học có cấu trúc và trạng thái tồn tại đặc trưng theo bản chất liên kết (ion hoặc cộng hóa trị).",
    "props": "Tính chất hóa học quyết định bởi thành phần nguyên tố, số oxi hóa và các nhóm chức đặc trưng trong phân tử.",
    "prep": "Thu được từ nguồn khoáng vật/sinh học tự nhiên hoặc điều chế qua các phản ứng tổng hợp vô cơ/hữu cơ tiêu chuẩn.",
    "uses": "Ứng dụng trong nghiên cứu hóa học, giảng dạy, phân tích phòng thí nghiệm và các ngành công nghiệp liên quan.",
    "safety": "Tuân thủ quy tắc an toàn phòng thí nghiệm: không nếm, không hít trực tiếp và rửa tay sạch sau khi thực hành.",
}


_CATEGORY_TEMPLATES_EN = {
    "Acid vô cơ": {
        "state": "Typically exists as a colorless aqueous solution or water-soluble gas/crystalline solid with a sour taste that turns blue litmus red.",
        "props": "Dissociates to produce H⁺ (H₃O⁺) ions in water: neutralizes bases and basic oxides to form salts and water, reacts with active metals above H, and displaces weaker acids from carbonate/sulfite salts.",
        "prep": "Prepared by hydrating acidic oxides, reacting salts with a less volatile strong acid (such as concentrated H₂SO₄), or direct synthesis from elements.",
        "uses": "Core laboratory reagent, fertilizer production, metal pickling/cleaning, chemical manufacturing, and industrial pH control.",
        "safety": "Concentrated acids cause severe chemical burns — always wear eye protection and dilute by slowly adding acid into water, never the reverse.",
    },
    "Base - Hydroxide": {
        "state": "Alkali hydroxides (Group IA, Ba, Ca) are white hygroscopic solids dissolving into soapy alkaline solutions; most transition-metal hydroxides are characteristic colored precipitates.",
        "props": "Soluble bases turn red litmus blue and phenolphthalein pink, absorb acidic oxides (CO₂, SO₂), and precipitate metal hydroxides from salt solutions. All hydroxides are neutralized by acids; insoluble hydroxides decompose into oxides upon heating.",
        "prep": "Alkali bases are produced via chlor-alkali electrolysis or oxide hydration; insoluble hydroxides are obtained by double displacement between salts and alkalis.",
        "uses": "Soap and detergent manufacturing, papermaking, construction, wastewater neutralization, and chemical catalysis.",
        "safety": "Concentrated alkalis are highly corrosive to skin and especially eyes; store tightly sealed away from atmospheric moisture and CO₂.",
    },
    "Oxide": {
        "state": "Metal oxides are typically high-melting ionic crystalline solids; nonmetal oxides exist as gases, volatile liquids, or molecular solids.",
        "props": "Exhibits basic (reacts with acids), acidic (reacts with bases), amphoteric (reacts with both, e.g. Al₂O₃, ZnO), or neutral (CO, NO, N₂O) character depending on the element and oxidation state.",
        "prep": "Direct combustion of elements in oxygen, thermal decomposition of carbonates/nitrates/hydroxides, or controlled oxidation.",
        "uses": "Metallurgical ores, raw materials for acids and bases, ceramics, glass, catalysts, and inorganic pigments.",
        "safety": "Alkaline oxides generate heat on contact with moisture; gaseous nonmetal oxides (SO₂, NO₂, CO) are toxic and require good ventilation.",
    },
    "Muối (Salts)": {
        "state": "Ionic crystalline solids at room temperature with high melting points; solubility and color depend on the metal cation and acid anion.",
        "props": "Strong electrolytes when dissolved in water. Participate in ionic exchange (forming precipitates, gases, or weak electrolytes), single displacement with more active metals, electrolysis, and thermal decomposition.",
        "prep": "Acid–base neutralization, metal/oxide + acid reactions, salt metathesis, or extraction from natural mineral deposits.",
        "uses": "Fertilizers, analytical reagents, electroplating, pharmaceuticals, food preservation, ceramics, and industrial synthesis.",
        "safety": "Check for heavy-metal ion toxicity (Pb²⁺, Hg²⁺, soluble Ba²⁺, Cr⁶⁺, Cd²⁺) and avoid inhaling crystalline dust.",
    },
    "Đơn chất (Elements)": {
        "state": "Pure substance composed of a single chemical element; physical properties (metallic luster/conductivity vs. nonmetallic molecular/network forms) arise from atomic bonding.",
        "props": "Oxidation state 0: metals act as reducing agents (forming cations), nonmetals act primarily as oxidizing agents (or both), and noble gases have stable filled valence shells.",
        "prep": "Fractional distillation of liquid air, molten/aqueous electrolysis, pyrometallurgy, or hydrometallurgy from natural ores.",
        "uses": "Structural alloys, electronics, catalysis, chemical feedstocks, energy storage, and medical applications.",
        "safety": "Observe reactivity hazards for alkali metals (water-reactive), halogens (toxic oxidizers), and heavy metals.",
    },
    "Hydrocarbon": {
        "state": "Composed solely of C and H; nonpolar, virtually insoluble in water, less dense than water (C₁–C₄ gases, C₅–C₁₇ liquids, ≥ C₁₈ solids).",
        "props": "Burns completely to CO₂ and H₂O releasing high heat. Alkanes undergo halogen substitution; alkenes/alkynes undergo addition (H₂, Br₂, HX) and polymerization; arenes undergo electrophilic aromatic substitution.",
        "prep": "Fractional distillation, catalytic cracking/reforming of petroleum and natural gas, or organic synthesis.",
        "uses": "Transportation and heating fuels, nonpolar solvents, and primary petrochemical feedstocks for plastics and rubbers.",
        "safety": "Highly flammable and forms explosive vapor mixtures with air; keep strictly away from sparks and open flames.",
    },
    "Alcohol - Phenol - Ether": {
        "state": "Short-chain alcohols (C₁–C₃) are fully miscible with water via hydrogen bonding and boil higher than matching hydrocarbons; ethers are volatile, low-polarity liquids.",
        "props": "Alcohols react with alkali metals (Na, K), dehydrate to alkenes/ethers, esterify with acids, and oxidize to aldehydes/ketones/acids. Phenols are weakly acidic and activate ortho/para aromatic substitution.",
        "prep": "Alkene hydration, carbohydrate fermentation, carbonyl reduction, or cumene/halide hydrolysis.",
        "uses": "Universal solvents, antiseptics, biofuels, fragrances, and intermediates for esters, resins, and pharmaceuticals.",
        "safety": "Most are flammable; methanol and phenol are highly toxic — avoid ingestion and skin absorption.",
    },
    "Aldehyde - Ketone": {
        "state": "Contain a polar carbonyl group (C=O); low-molecular-weight members (HCHO, CH₃CHO, acetone) are water-miscible with sharp characteristic odors.",
        "props": "Undergo nucleophilic addition and hydrogenation to alcohols. Aldehydes (–CHO) are readily oxidized (silver-mirror Tollens test, red Cu₂O Fehling/Benedict test).",
        "prep": "Controlled oxidation of primary alcohols (aldehydes) or secondary alcohols (ketones), alkyne hydration, or Wacker oxidation.",
        "uses": "Industrial solvents (acetone), polymer resins, flavors/fragrances (vanillin), and organic synthesis.",
        "safety": "Volatile, flammable, and irritating to eyes and respiratory tract.",
    },
    "Carboxylic acid": {
        "state": "Strong intermolecular hydrogen bonding (dimers) produces high boiling points; short-chain acids are sour and fully water-soluble.",
        "props": "Weak organic acids that neutralize bases, react with active metals and carbonates (releasing CO₂), and undergo reversible Fischer esterification with alcohols.",
        "prep": "Oxidation of aldehydes or primary alcohols, microbial fermentation, ester/nitrile hydrolysis, or alcohol carbonylation.",
        "uses": "Food preservatives/acidulants, ester & fragrance synthesis, fibers, plastics, and pharmaceuticals.",
        "safety": "Concentrated short-chain acids (formic, glacial acetic) are corrosive and cause skin/eye burns.",
    },
    "Ester - Lipid": {
        "state": "Short-chain esters are volatile, pleasant-smelling liquids poorly soluble in water; lipids (triglycerides) are liquid plant oils or solid animal fats.",
        "props": "Undergo reversible acid-catalyzed hydrolysis and irreversible alkaline saponification (NaOH/KOH) yielding carboxylate salts (soaps) and alcohols/glycerol.",
        "prep": "Esterification of carboxylic acids/anhydrides with alcohols, or natural extraction from oilseeds and animal fats.",
        "uses": "Food flavorings, perfumes, low-toxicity coatings solvents, soaps, acrylic glass (PMMA), and biodiesel.",
        "safety": "Volatile esters are flammable; most have low biological toxicity.",
    },
    "Amine - Amino acid": {
        "state": "Light amines are fishy/ammonia-like gases soluble in water; amino acids are high-melting crystalline solids existing as zwitterions (⁺H₃N–R–COO⁻).",
        "props": "Amines act as Brønsted/Lewis bases forming ammonium salts with acids; amino acids are amphoteric (reacting with both acids and bases) and condense into peptides/proteins.",
        "prep": "Reduction of nitro compounds, ammonia alkylation, protein hydrolysis, or microbial fermentation.",
        "uses": "Pharmaceuticals, dyes, polyamides (nylon), polyurethanes, biological nutrition, and flavor enhancers.",
        "safety": "Aromatic amines (e.g. aniline) are toxic and absorb through skin; natural α-amino acids are biologically safe.",
    },
    "Carbohydrate": {
        "state": "Polyhydroxy aldehydes/ketones with general formula C_n(H₂O)_m; mono- and disaccharides are sweet water-soluble crystals, while polysaccharides (starch, cellulose) are tasteless polymers.",
        "props": "Adjacent –OH groups dissolve Cu(OH)₂ into deep-blue complexes; reducing sugars (glucose, fructose, maltose) give positive silver-mirror tests; di-/polysaccharides hydrolyze under acid or enzyme catalysis.",
        "prep": "Produced naturally via plant photosynthesis and refined from sugarcane, grains, cotton, and wood pulp.",
        "uses": "Primary cellular energy source, food industry, paper & textile manufacturing, pharmaceuticals, and bioethanol.",
        "safety": "Biologically safe.",
    },
    "Polymer - Vật liệu": {
        "state": "High-molecular-weight macromolecules built from repeating monomer units; typically non-volatile solids insoluble in common solvents without a sharp melting point.",
        "props": "Can undergo chain-preserving modification, chain scission (hydrolysis/pyrolysis), or cross-linking (vulcanization) to tune mechanical elasticity and heat resistance.",
        "prep": "Addition polymerization (from unsaturated/cyclic monomers) or condensation polymerization (from polyfunctional monomers).",
        "uses": "Plastics (PE, PP, PVC, PET), synthetic fibers (nylon, polyester), tires, adhesives, and advanced composites.",
        "safety": "Avoid open burning of plastics (emits toxic CO, HCl, dioxins); prioritize sorting and recycling.",
    },
    "Hợp chất thơm & Dị vòng": {
        "state": "Feature conjugated aromatic or heteroatom (N, O, S) ring systems; typically fragrant liquids or crystalline solids.",
        "props": "Delocalized π-systems favor electrophilic substitution over addition; nitrogen heterocycles (pyridine, indole, purine) display specialized acid–base chemistry and form key biological scaffolds.",
        "prep": "Coal-tar refining, petroleum reforming, or targeted cyclization synthesis.",
        "uses": "Core scaffolds in pharmaceuticals, dyes, fragrances, organic semiconductors (OLEDs), and nucleic acids (DNA/RNA).",
        "safety": "Many aromatic derivatives are toxic and flammable; handle inside a fume hood.",
    },
    "Dược phẩm - Vitamin - Sinh học": {
        "state": "Complex polyfunctional crystalline molecules whose 3D arrangement and functional groups govern biological receptor activity.",
        "props": "Chemical behavior reflects the combined reactivity of its functional groups (acid, phenol, ester, amide, amine…); often sensitive to light, pH, and temperature.",
        "prep": "Natural botanical extraction, microbial fermentation, or stereoselective organic synthesis.",
        "uses": "Disease prevention and therapy, essential micronutrient supplementation, and biomedical research.",
        "safety": "Use strictly under medical guidance and proper dosage — never substitute laboratory-grade chemicals for pharmaceutical products.",
    },
}

_DEFAULT_TEMPLATE_EN = {
    "state": "Chemical compound with characteristic physical state and crystal/molecular structure governed by its ionic or covalent bonding.",
    "props": "Chemical reactivity is determined by elemental composition, oxidation states, and characteristic functional groups.",
    "prep": "Obtained from natural mineral/biological sources or synthesized through standard inorganic/organic reactions.",
    "uses": "Applied in chemical research, education, analytical laboratories, and industrial manufacturing.",
    "safety": "Follow standard laboratory safety rules: never taste or directly inhale fumes, and wash hands thoroughly after handling.",
}


def _fmt_eq_html(eq: str) -> str:
    """Hiển thị phương trình hóa học gọn đẹp bằng Unicode (chỉ số dưới, mũi tên, điều kiện)."""
    s = html.escape(eq)
    # Chuyển mũi tên kèm điều kiện ->[t^o] thành → (t°)
    def _arr_repl(m):
        cond = m.group(1)
        cond = cond.replace("^o", "°").replace("t^o", "t°")
        return f" <span style='opacity:0.82;font-size:11.5px'>({cond})</span> ⟶ " if cond else " ⟶ "

    s = re.sub(r"\s*->\s*\[([^\]]*)\]\s*", _arr_repl, s)
    s = re.sub(r"\s*<=>\s*\[([^\]]*)\]\s*", lambda m: f" <span style='opacity:0.82;font-size:11.5px'>({m.group(1)})</span> ⇌ ", s)
    s = s.replace("&lt;=&gt;", " ⇌ ").replace("-&gt;", " ⟶ ")
    s = re.sub(r"\s*\^\s*(?=$|\s|\+)", "↑", s)
    s = re.sub(r"\s+v(?=$|\s|\+)", "↓", s)
    # Chuyển chỉ số dưới cho số đi sau chữ cái hoặc )
    sub_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    s = re.sub(r"(?<=[A-Za-z)\]])(\d+)", lambda m: m.group(1).translate(sub_map), s)
    return s


def build_compound_wiki_html(
    compound_tuple,
    alias: str,
    mass_str: str,
    elem_rows,
    smiles_stats,
    reactions_list,
    dark: bool = False,
    accent: str = "#4F46E5",
    lang: str = "vi",
) -> str:
    """Tạo trang bài viết Bách khoa Hóa học (Wiki) hoàn chỉnh (Song ngữ VI / EN) cho bất kỳ chất nào trong 705 chất."""
    en_mode = (lang == "en")
    f, en, vi, cat, desc, smi = compound_tuple
    fkey = f.replace(" ", "")
    if en_mode:
        wiki = _CATEGORY_TEMPLATES_EN.get(cat, _DEFAULT_TEMPLATE_EN)
    else:
        wiki = COMPOUND_WIKI.get(fkey) or _CATEGORY_TEMPLATES.get(cat, _DEFAULT_TEMPLATE)

    # Bảng màu thích ứng Sáng / Tối
    fg = "#E6EDF7" if dark else "#0F172A"
    muted = "#94A3B8" if dark else "#64748B"
    card_bg = "#131C2E" if dark else "#F8FAFC"
    card_bd = "#26334D" if dark else "#E2E8F0"
    chip_bg = "#1E293B" if dark else "#EEF2FF"
    chip_fg = "#A5B4FC" if dark else accent
    bar_bg = "#1E293B" if dark else "#E2E8F0"
    warn_bg = "#2B1F0F" if dark else "#FFFBEB"
    warn_bd = "#B45309" if dark else "#F59E0B"
    warn_fg = "#FDE68A" if dark else "#92400E"
    rxn_bg = "#0F172A" if dark else "#FFFFFF"

    f_uni = fe.species_to_unicode(f) if "n" not in f.replace("Na", "").replace("Mn", "").replace("Sn", "").replace("Zn", "").replace("Ni", "").replace("In", "") else f
    prep_rxns, prop_rxns = compound_reactions(f, reactions_list)

    cat_disp = cat
    if en_mode:
        import i18n
        cat_disp = i18n.VI_TO_EN.get(cat, cat)

    # Nhúng bảng Infobox tóm tắt đầu bài
    info_cells = [
        ("Formula" if en_mode else "Công thức", f"<b>{html.escape(f_uni)}</b>"),
        ("Molar Mass" if en_mode else "Khối lượng mol", f"<b>{html.escape(mass_str)}</b>"),
        ("IUPAC Class" if en_mode else "Phân loại IUPAC", f"<b>{html.escape(cat_disp)}</b>"),
    ]
    if alias and not en_mode:
        info_cells.append(("Tên thường gọi", html.escape(alias)))
    if smiles_stats:
        n_at, n_h, n_bd, n_rings = smiles_stats
        s_txt = f"{n_at} heavy atoms (+ {n_h} H) · {n_bd} bonds · {n_rings} rings" if en_mode else f"{n_at} nguyên tử nặng (+ {n_h} H) · {n_bd} liên kết · {n_rings} vòng"
        info_cells.append(("2D Structure" if en_mode else "Cấu trúc 2D", s_txt))

    parts = [
        f"<div style='font-family:\"Segoe UI\",sans-serif; color:{fg}; line-height:1.6; font-size:13.5px;'>"
    ]

    # --- 1. Tóm tắt nhanh (Lead paragraph + Infobox)
    lead_desc = (
        f"IUPAC-standardized chemical species in the <b>{html.escape(cat_disp)}</b> class."
        if en_mode else html.escape(desc)
    )
    parts.append(
        f"<div style='background:{card_bg}; border:1px solid {card_bd}; border-radius:10px; padding:10px 12px; margin-bottom:10px;'>"
        f"<div style='font-size:13.5px; margin-bottom:8px;'><b>{html.escape(en)}</b> "
        f"(<span style='color:{chip_fg}; font-weight:700;'>{html.escape(f_uni)}</span>) — {lead_desc}</div>"
        f"<table width='100%' cellspacing='0' cellpadding='3' style='font-size:12.5px; border-top:1px solid {card_bd}; padding-top:4px;'>"
    )
    for k, v in info_cells:
        parts.append(f"<tr><td width='34%' style='color:{muted};'>{k}</td><td>{v}</td></tr>")
    if smi:
        parts.append(f"<tr><td style='color:{muted};'>{'SMILES' if en_mode else 'Mã SMILES'}</td><td><code style='background:{chip_bg}; color:{chip_fg}; padding:1px 5px; border-radius:4px;'>{html.escape(smi)}</code></td></tr>")
    parts.append("</table></div>")

    # --- 2. Thành phần phần trăm khối lượng các nguyên tố (thanh trực quan)
    if elem_rows:
        parts.append(
            f"<div style='font-size:11px; font-weight:700; letter-spacing:0.6px; color:{chip_fg}; margin:8px 0 4px 0;'>"
            f"{'ELEMENTAL MASS COMPOSITION' if en_mode else 'THÀNH PHẦN PHẦN TRĂM KHỐI LƯỢNG'}</div>"
            f"<div style='background:{card_bg}; border:1px solid {card_bd}; border-radius:9px; padding:7px 10px; margin-bottom:10px;'>"
            f"<table width='100%' cellspacing='0' cellpadding='2' style='font-size:12px;'>"
        )
        bar_cols = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"]
        for idx, (el, cnt, ms, pct) in enumerate(elem_rows):
            bc = bar_cols[idx % len(bar_cols)]
            w_pct = max(4, min(100, int(round(pct))))
            parts.append(
                f"<tr>"
                f"<td width='14%'><b>{html.escape(el)}</b> <span style='color:{muted};'>×{cnt}</span></td>"
                f"<td width='18%' align='right' style='color:{muted};'>{ms:.2f} g</td>"
                f"<td width='48%' style='padding:0 8px;'>"
                f"<table width='100%' cellspacing='0' cellpadding='0' bgcolor='{bar_bg}'><tr>"
                f"<td width='{w_pct}%' height='7' bgcolor='{bc}'></td><td width='{100 - w_pct}%'></td>"
                f"</tr></table></td>"
                f"<td width='20%' align='right'><b>{pct:.2f}%</b></td>"
                f"</tr>"
            )
        parts.append("</table></div>")

    # --- 3. Nội dung Wiki chuẩn 4 mục: Lí tính · Hóa tính · Điều chế · Ứng dụng
    if en_mode:
        sections = [
            ("PHYSICAL STATE & PROPERTIES", wiki["state"]),
            ("KEY CHEMICAL PROPERTIES", wiki["props"]),
            ("PREPARATION & OCCURRENCE", wiki["prep"]),
            ("APPLICATIONS & USES", wiki["uses"]),
        ]
    else:
        sections = [
            ("TRẠNG THÁI & TÍNH CHẤT VẬT LÍ", wiki["state"]),
            ("TÍNH CHẤT HÓA HỌC TRỌNG TÂM", wiki["props"]),
            ("ĐIỀU CHẾ & NGUỒN GỐC", wiki["prep"]),
            ("ỨNG DỤNG TRONG ĐỜI SỐNG & CÔNG NGHIỆP", wiki["uses"]),
        ]
    for sec_title, body_txt in sections:
        parts.append(
            f"<div style='font-size:11px; font-weight:700; letter-spacing:0.6px; color:{chip_fg}; margin:10px 0 4px 0;'>{sec_title}</div>"
            f"<div style='margin-bottom:6px;'>{html.escape(body_txt)}</div>"
        )

    # --- 4. Phương trình điều chế / tạo thành (nhấp để mở ngay tab Cân bằng!)
    if prep_rxns:
        h_prep = f"FORMATION & PREPARATION EQUATIONS ({len(prep_rxns)})" if en_mode else f"PHƯƠNG TRÌNH TẠO THÀNH · ĐIỀU CHẾ ({len(prep_rxns)})"
        hint_prep = "— click an equation to open in Balancer" if en_mode else "— nhấp phương trình để cân bằng & xuất ảnh"
        parts.append(
            f"<div style='font-size:11px; font-weight:700; letter-spacing:0.6px; color:#10B981; margin:11px 0 5px 0;'>"
            f"{h_prep} <span style='font-weight:400; color:{muted};'>{hint_prep}</span></div>"
        )
        for title, rcat, eq in prep_rxns[:8]:
            href = "rxn:" + quote(eq, safe="")
            if en_mode:
                import i18n, i18n_data
                t_disp = i18n_data.reaction_title_en(title, eq)
                c_disp = i18n.tr(rcat)
                sub_line = f"{html.escape(t_disp)} · <i>{html.escape(c_disp)}</i>"
            else:
                sub_line = f"{html.escape(title)} · <i>{html.escape(rcat)}</i>"
            parts.append(
                f"<div style='background:{rxn_bg}; border:1px solid {card_bd}; border-left:3px solid #10B981; "
                f"border-radius:7px; padding:6px 9px; margin-bottom:5px;'>"
                f"<div style='font-size:12px; color:{muted};'>{sub_line}</div>"
                f"<div style='margin-top:2px; font-size:13.5px;'><a href='{href}' style='color:{fg}; text-decoration:none; font-weight:600;'>"
                f"{_fmt_eq_html(eq)}</a></div></div>"
            )

    # --- 5. Các phương trình hóa học liên quan (chất ở vế tham gia)
    if prop_rxns:
        h_prop = f"RELATED CHEMICAL REACTIONS ({len(prop_rxns)})" if en_mode else f"PHẢN ỨNG HÓA HỌC LIÊN QUAN ({len(prop_rxns)})"
        hint_prop = "— click to open in Equation Editor" if en_mode else "— nhấp để mở trình phương trình"
        parts.append(
            f"<div style='font-size:11px; font-weight:700; letter-spacing:0.6px; color:{chip_fg}; margin:11px 0 5px 0;'>"
            f"{h_prop} <span style='font-weight:400; color:{muted};'>{hint_prop}</span></div>"
        )
        for title, rcat, eq in prop_rxns[:10]:
            href = "rxn:" + quote(eq, safe="")
            if en_mode:
                import i18n, i18n_data
                t_disp = i18n_data.reaction_title_en(title, eq)
                c_disp = i18n.tr(rcat)
                sub_line = f"{html.escape(t_disp)} · <i>{html.escape(c_disp)}</i>"
            else:
                sub_line = f"{html.escape(title)} · <i>{html.escape(rcat)}</i>"
            parts.append(
                f"<div style='background:{rxn_bg}; border:1px solid {card_bd}; border-left:3px solid {accent}; "
                f"border-radius:7px; padding:6px 9px; margin-bottom:5px;'>"
                f"<div style='font-size:12px; color:{muted};'>{sub_line}</div>"
                f"<div style='margin-top:2px; font-size:13.5px;'><a href='{href}' style='color:{fg}; text-decoration:none; font-weight:600;'>"
                f"{_fmt_eq_html(eq)}</a></div></div>"
            )

    if not prep_rxns and not prop_rxns:
        if en_mode:
            parts.append(
                f"<div style='font-size:11px; font-weight:700; letter-spacing:0.6px; color:{chip_fg}; margin:11px 0 4px 0;'>"
                f"RELATED REACTIONS</div>"
                f"<div style='color:{muted}; font-size:12.5px; margin-bottom:6px;'>"
                f"No direct sample equations matched in the library — enter <b>{html.escape(f)}</b> directly in the "
                f"<i>Equations · Balancer</i> tab to balance any reaction instantly.</div>"
            )
        else:
            parts.append(
                f"<div style='font-size:11px; font-weight:700; letter-spacing:0.6px; color:{chip_fg}; margin:11px 0 4px 0;'>"
                f"PHƯƠNG TRÌNH LIÊN QUAN</div>"
                f"<div style='color:{muted}; font-size:12.5px; margin-bottom:6px;'>"
                f"Chưa có phương trình mẫu khớp trực tiếp trong kho — bạn có thể tự nhập công thức <b>{html.escape(f)}</b> "
                f"ở tab <i>Phương trình · Cân bằng</i> để cân bằng tức thì.</div>"
            )

    # --- 6. Lưu ý an toàn & Ghi nhớ
    safety_lbl = "Safety &amp; Study Note:" if en_mode else "Lưu ý an toàn &amp; Ghi nhớ:"
    parts.append(
        f"<div style='background:{warn_bg}; border:1px solid {warn_bd}; border-radius:9px; "
        f"padding:8px 10px; margin-top:10px; color:{warn_fg}; font-size:12.5px;'>"
        f"<b>{safety_lbl}</b> {html.escape(wiki['safety'])}</div>"
    )
    parts.append("</div>")
    return "".join(parts)
