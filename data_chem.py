# -*- coding: utf-8 -*-
"""data_chem.py - Kho chất (700+ chuẩn danh pháp IUPAC), phản ứng mẫu (680+), SMILES mẫu và tiện ích tra cứu."""
import re
import unicodedata

from data_compounds_inorg import INORGANIC
from data_compounds_org import ORGANIC
from data_reactions import REACTIONS as _RAW_REACTIONS

# Chuẩn hóa tên nhóm theo danh pháp quốc tế IUPAC (chương trình GDPT 2018)
CAT_IUPAC = {
    "Đơn chất": "Đơn chất (Elements)",
    "Khí & hợp chất đơn giản": "Khí & hợp chất đơn giản",
    "Axit vô cơ": "Acid vô cơ",
    "Bazơ - Hiđroxit": "Base - Hydroxide",
    "Oxit": "Oxide",
    "Muối": "Muối (Salts)",
    "Ion & gốc axit": "Ion & gốc acid",
    "Khoáng vật - Hỗn hợp": "Khoáng vật - Vật liệu",
    "Hiđrocacbon": "Hydrocarbon",
    "Ancol - Phenol - Ete": "Alcohol - Phenol - Ether",
    "Anđehit - Xeton": "Aldehyde - Ketone",
    "Axit hữu cơ": "Carboxylic acid",
    "Este - Chất béo": "Ester - Lipid",
    "Amin - Amino axit": "Amine - Amino acid",
    "Cacbohiđrat": "Carbohydrate",
    "Polime - Vật liệu": "Polymer - Vật liệu",
    "Hợp chất thơm & dị vòng": "Hợp chất thơm & Dị vòng",
    "Dược phẩm - Vitamin - Khác": "Dược phẩm - Vitamin - Sinh học",
}

RXN_CAT_IUPAC = {
    "Kim loại": "Kim loại",
    "Phi kim": "Phi kim",
    "Axit - Bazơ - Muối": "Acid - Base - Muối",
    "Oxi hóa - Khử": "Oxi hóa - Khử",
    "Kết tủa": "Kết tủa",
    "Nhiệt phân": "Nhiệt phân",
    "Điện phân": "Điện phân",
    "Điều chế": "Điều chế",
    "Ion": "Phản ứng ion",
    "Cân bằng": "Cân bằng hóa học",
    "Hữu cơ: Hiđrocacbon": "Hữu cơ: Hydrocarbon",
    "Hữu cơ: Ancol - Phenol": "Hữu cơ: Alcohol - Phenol",
    "Hữu cơ: Anđehit - Axit": "Hữu cơ: Aldehyde - Acid",
    "Hữu cơ: Este - Lipit": "Hữu cơ: Ester - Lipid",
    "Hữu cơ: Amin - Amino axit": "Hữu cơ: Amine - Amino acid",
    "Hữu cơ: Cacbohiđrat": "Hữu cơ: Carbohydrate",
    "Polime": "Polymer",
}

REACTION_CATEGORIES = list(RXN_CAT_IUPAC.values())
REACTIONS = [[t, RXN_CAT_IUPAC.get(c, c), eq] for t, c, eq in _RAW_REACTIONS]

# Chỉ giữ lại tên dân gian/thông thường thực sự bằng tiếng Việt (bỏ toàn bộ phiên âm cũ như 'Nitơ đioxit', 'Axit sunfuric'...)
_COMMON_VN_KEYWORDS = (
    "nước", "muối ăn", "vôi sống", "vôi tôi", "đá vôi", "xút", "phèn", "thạch cao",
    "khí cười", "giấm", "rượu", "cồn", "đường", "dầu chuối", "dầu gió", "băng phiến",
    "thạch anh", "gỉ sắt", "than chì", "kim cương", "bột tan", "chu sa", "long não",
    "sữa magie", "đá khô", "diêm tiêu", "hàn the", "bột nở", "thuốc tím", "bồ tạt",
    "phân đạm", "phân lân", "nước javen", "clorua vôi", "cát", "đất đèn", "quặng",
    "vàng", "bạc", "đồng", "sắt", "nhôm", "kẽm", "chì", "thiếc", "thủy ngân", "bạch kim",
    "lưu huỳnh", "tinh dầu", "tinh chất", "chất cay", "hương vani",
)


_PHONETIC_RE = re.compile(
    r"^(axit|natri|kali|canxi|bari|magie|nitơ|cacbon|hiđro|oxi|clo|brom|iot|flo|photpho|silic|crom|mangan|coban|niken|liti|"
    r"etyl|metyl|propyl|butyl|xiclo|ancol|anđehit|đimetyl|trimetyl|eten|propen|etin|benzen|toluen|anilin|stiren|glucozơ|fructozơ)\b",
    re.IGNORECASE,
)


def extract_common_vn(old_vi: str) -> str:
    """Trích xuất tên thường gọi dân gian (nếu có); bỏ toàn bộ phiên âm tiếng Việt cũ."""
    s = (old_vi or "").strip()
    if not s:
        return ""
    m = re.search(r"\(([^)]+)\)", s)
    if m:
        parts = [p.strip() for p in m.group(1).split(",") if p.strip()]
        kept = [p for p in parts if any(k in p.lower() for k in _COMMON_VN_KEYWORDS) and not _PHONETIC_RE.match(p)]
        if kept:
            return ", ".join(kept)
    sl = s.lower()
    base = s.split(" (")[0].strip()
    if any(k == base.lower() or k in sl for k in _COMMON_VN_KEYWORDS) and len(base) <= 22:
        if not _PHONETIC_RE.match(base):
            return base
    return ""


def compound_display_name(en: str, old_vi: str = "") -> str:
    """Tên hiển thị chuẩn hóa quốc tế IUPAC (kèm tên thông thường dân gian ngắn nếu có)."""
    alias = extract_common_vn(old_vi)
    if alias and alias.lower() != en.lower():
        return f"{en} ({alias})"
    return en


_seen_c = set()
COMPOUNDS = []
for _f, _en, _vi, _cat, _desc, _smi in INORGANIC + ORGANIC:
    _ck = (_f.strip(), _en.strip().lower())
    if _ck not in _seen_c:
        _seen_c.add(_ck)
        # Lưu tuple chuẩn: (formula, iupac_name, legacy_vi_for_search, iupac_category, desc, smiles)
        COMPOUNDS.append((_f, _en, _vi, CAT_IUPAC.get(_cat, _cat), _desc, _smi))

COMPOUND_CATEGORIES = ["Tất cả"] + list(dict.fromkeys(c[3] for c in COMPOUNDS))


def _norm(t: str) -> str:
    t = t.strip().lower().replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s\-_,'()]+", "", t)


FORMULA_TO_SMILES = {}
_NAME_INDEX = {}
for _f, _en, _vi, _cat, _desc, _smi in COMPOUNDS:
    if not _smi:
        continue
    FORMULA_TO_SMILES.setdefault(_f.replace(" ", ""), _smi)
    keys = {_norm(_en), _norm(_vi)}
    for part in re.split(r"[()]", _vi):
        if len(part.strip()) > 2:
            keys.add(_norm(part))
    for part in re.split(r"[()]", _en):
        if len(part.strip()) > 2:
            keys.add(_norm(part))
    for k in keys:
        _NAME_INDEX.setdefault(k, _smi)
FORMULA_TO_SMILES.update({
    "C6H6": "c1ccccc1", "C2H6O": "CCO", "C2H4O2": "CC(=O)O", "H2O": "O", "NaCl": "[Na+].[Cl-]",
    "NH4+": "[NH4+]", "H3O+": "[OH3+]", "CO2": "O=C=O", "O2": "O=O", "N2": "N#N",
})


def name_to_smiles(norm_key: str):
    return _NAME_INDEX.get(norm_key)


def search_compounds(query: str, category: str = "Tất cả"):
    q = _norm(query) if query else ""
    ql = query.strip().lower()
    res = []
    for c in COMPOUNDS:
        if category != "Tất cả" and c[3] != category:
            continue
        if not q:
            res.append((0, c))
            continue
        name_hay = _norm(" ".join((c[1], c[2])))
        if ql == c[0].lower() or _norm(c[1]) == q or _norm(c[2]) == q:
            res.append((0, c))
        elif q in name_hay or ql in c[0].lower():
            res.append((1, c))
        elif q in _norm(c[4]):
            res.append((2, c))
    res.sort(key=lambda t: t[0])
    return [c for _, c in res]


def reaction_search(query: str, category: str = "Tất cả"):
    q = _norm(query) if query else ""
    return [r for r in REACTIONS if (category == "Tất cả" or r[1] == category) and (not q or q in _norm(r[0] + r[2]))]


# SMILES mẫu: đặt tên 100% theo chuẩn quốc tế IUPAC
SMILES_GROUPS = {}
_org_cats = {CAT_IUPAC.get(c[3], c[3]) for c in ORGANIC}
for _f, _en, _vi, _cat, _desc, _smi in COMPOUNDS:
    if not _smi or "." in _smi:
        continue
    if _cat in _org_cats:
        SMILES_GROUPS.setdefault(_cat, []).append((f"{_en}  ({_f})", _smi))
    elif _f in ("H2SO4", "HNO3", "H3PO4", "H2O2", "O3", "NH3", "CO2", "SO2", "H2O", "NO2", "SF6", "SOCl2", "PCl5", "H2SO5"):
        SMILES_GROUPS.setdefault("Vô cơ thường gặp (Inorganic)", []).append((f"{_en}  ({_f})", _smi))
SMILES_PRESETS = [item for grp in SMILES_GROUPS.values() for item in grp]
