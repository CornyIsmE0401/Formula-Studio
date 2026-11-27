"""molecule.py - Lõi dựng cấu trúc phân tử 2D (không cần RDKit; nếu có RDKit sẽ dùng để dựng tọa độ đẹp hơn).

Gồm: đọc SMILES (có Kekulé hóa vòng thơm), đọc công thức cấu tạo thu gọn (CH3COOH, CH3CH(OH)CH3...),
tìm vòng (SSSR), dựng tọa độ 2D, ghi SMILES, tạo "cảnh vẽ" dùng chung cho Matplotlib (PNG/SVG) và QPainter.
"""
import io
import math
import re
import unicodedata
from collections import defaultdict, deque

from data_store import ATOMIC_MASSES

try:  # RDKit là tùy chọn
    from rdkit import Chem
    from rdkit.Chem import rdDepictor
    HAS_RDKIT = True
except Exception:  # pragma: no cover
    HAS_RDKIT = False

SUBS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
SUPS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

ORGANIC_VAL = {"B": (3,), "C": (4,), "N": (3, 5), "O": (2,), "P": (3, 5), "S": (2, 4, 6),
               "F": (1,), "Cl": (1,), "Br": (1,), "I": (1,), "Si": (4,), "Se": (2, 4, 6)}
CHARGED_VAL = {("N", 1): (4,), ("O", 1): (3,), ("S", 1): (3,), ("P", 1): (4,), ("O", -1): (1,),
               ("N", -1): (2,), ("S", -1): (1,), ("C", -1): (3,), ("C", 1): (3,), ("B", -1): (4,),
               ("Cl", 1): (2,), ("Br", 1): (2,), ("I", 1): (2,)}
SMILES_ORGANIC = ("Cl", "Br", "B", "C", "N", "O", "P", "S", "F", "I")
AROMATIC_ATOMS = {"b": "B", "c": "C", "n": "N", "o": "O", "p": "P", "s": "S", "se": "Se", "as": "As"}

PALETTE_LIGHT = {"C": "#1F2937", "H": "#4B5563", "N": "#2563EB", "O": "#DC2626", "S": "#B45309", "P": "#EA580C",
                 "F": "#15803D", "Cl": "#15803D", "Br": "#9A3412", "I": "#7E22CE", "Na": "#7C3AED",
                 "K": "#7C3AED", "Fe": "#B45309", "Cu": "#C2410C", "default": "#0F766E"}
PALETTE_DARK = {"C": "#E5E7EB", "H": "#CBD5E1", "N": "#60A5FA", "O": "#F87171", "S": "#FBBF24", "P": "#FB923C",
                "F": "#4ADE80", "Cl": "#4ADE80", "Br": "#FB923C", "I": "#C084FC", "Na": "#A78BFA",
                "K": "#A78BFA", "Fe": "#FBBF24", "Cu": "#FB923C", "default": "#2DD4BF"}


# ==============================================================================
# 1. ĐỒ THỊ PHÂN TỬ
# ==============================================================================
class Mol:
    def __init__(self):
        self.atoms = []   # {"el","charge","h"(None=tự tính),"arom","x","y"}
        self.bonds = []   # {"u","v","o"}

    def add_atom(self, el, charge=0, h=None, arom=False, x=0.0, y=0.0):
        self.atoms.append({"el": el, "charge": charge, "h": h, "arom": arom, "x": x, "y": y})
        return len(self.atoms) - 1

    def add_bond(self, u, v, o=1, stereo=0):
        if u == v:
            return
        for b in self.bonds:
            if {b["u"], b["v"]} == {u, v}:
                b["o"] = o
                if stereo:
                    b["u"], b["v"], b["stereo"] = u, v, stereo
                elif "stereo" in b and o != 1:
                    b["stereo"] = 0
                return
        b = {"u": u, "v": v, "o": o}
        if stereo:
            b["stereo"] = stereo
        self.bonds.append(b)

    def adj(self):
        a = defaultdict(list)
        for b in self.bonds:
            a[b["u"]].append(b["v"])
            a[b["v"]].append(b["u"])
        return a

    def bond_order(self, u, v):
        for b in self.bonds:
            if (b["u"] == u and b["v"] == v) or (b["u"] == v and b["v"] == u):
                return b["o"]
        return 0

    def hcounts(self):
        s = [0.0] * len(self.atoms)
        for b in self.bonds:
            s[b["u"]] += b["o"]
            s[b["v"]] += b["o"]
        out = []
        for i, a in enumerate(self.atoms):
            if a["h"] is not None:
                out.append(a["h"])
                continue
            el, ch = a["el"], a["charge"]
            vals = CHARGED_VAL.get((el, ch)) if ch else ORGANIC_VAL.get(el)
            if not vals:
                out.append(0)
                continue
            v = math.ceil(s[i] - 1e-9)
            h = 0
            for val in vals:
                if val >= v:
                    h = val - v
                    break
            out.append(h)
        return out

    def formula_counts(self):
        cnt = defaultdict(int)
        for a, h in zip(self.atoms, self.hcounts()):
            cnt[a["el"]] += 1
            if h:
                cnt["H"] += h
        return dict(cnt)

    def formula(self, unicode_sub=False):
        cnt = self.formula_counts()
        keys = [k for k in ("C", "H") if k in cnt] + sorted(k for k in cnt if k not in ("C", "H"))
        if "C" not in cnt:
            keys = sorted(cnt)
        txt = "".join(f"{k}{'' if cnt[k] == 1 else cnt[k]}" for k in keys)
        return txt.translate(SUBS) if unicode_sub else txt

    def mass(self):
        return sum(ATOMIC_MASSES.get(k, 0.0) * c for k, c in self.formula_counts().items())

    def copy(self):
        m = Mol()
        m.atoms = [dict(a) for a in self.atoms]
        m.bonds = [dict(b) for b in self.bonds]
        return m


# ==============================================================================
# 2. ĐỌC SMILES (+ KEKULÉ HÓA)
# ==============================================================================
_BRACKET = re.compile(r"^\[(\d+)?([A-Z][a-z]?|se|as|[bcnops])(@{1,2}(?:TH|AL|SP|TB|OH)?\d*)?(H\d*)?((?:\+\d*|-\d*|\++|-+)?)(?::\d+)?\]$")


def parse_smiles(smiles: str) -> Mol:
    s = smiles.strip()
    if not s:
        raise ValueError("Chưa nhập mã SMILES.")
    mol = Mol()
    stack, rings = [], {}
    prev, pending = None, None
    i = 0

    def link(a, b, order, ar_a, ar_b):
        if order is None:
            order = 1.5 if (ar_a and ar_b) else 1
        mol.bonds.append({"u": a, "v": b, "o": order})

    while i < len(s):
        ch = s[i]
        if ch == "(":
            if prev is None:
                raise ValueError("Nhánh '(' xuất hiện trước nguyên tử đầu tiên.")
            stack.append(prev)
            i += 1
        elif ch == ")":
            if not stack:
                raise ValueError("Ngoặc ')' không có ngoặc '(' tương ứng.")
            prev = stack.pop()
            i += 1
        elif ch in "=#-:/\\$~":
            pending = {"=": 2, "#": 3, "-": 1, ":": 1.5, "/": 1, "\\": 1, "$": 4, "~": 1}[ch]
            i += 1
        elif ch == ".":
            prev, pending = None, None
            i += 1
        elif ch.isdigit() or ch == "%":
            if ch == "%":
                num = s[i + 1:i + 3]
                if len(num) < 2 or not num.isdigit():
                    raise ValueError("Số vòng %nn không hợp lệ.")
                key, i = int(num), i + 3
            else:
                key, i = int(ch), i + 1
            if prev is None:
                raise ValueError("Số đóng vòng đứng trước nguyên tử.")
            if key in rings:
                a, o1 = rings.pop(key)
                o = pending if pending is not None else o1
                if a == prev:
                    raise ValueError("Vòng tự nối chính nó.")
                link(a, prev, o, mol.atoms[a]["arom"], mol.atoms[prev]["arom"])
            else:
                rings[key] = (prev, pending)
            pending = None
        else:
            if ch == "[":
                end = s.find("]", i)
                if end < 0:
                    raise ValueError("Thiếu dấu ']' đóng nguyên tử trong ngoặc vuông.")
                m = _BRACKET.match(s[i:end + 1])
                if not m:
                    raise ValueError(f"Nguyên tử không hợp lệ: {s[i:end + 1]}")
                sym = m.group(2)
                arom = sym[0].islower()
                el = AROMATIC_ATOMS.get(sym, sym) if arom else sym
                if el not in ATOMIC_MASSES:
                    raise ValueError(f"Không có nguyên tố '{el}'.")
                hh = m.group(4)
                h = 0 if not hh else (int(hh[1:]) if len(hh) > 1 else 1)
                cs = m.group(5) or ""
                charge = 0
                if cs:
                    sign = 1 if cs[0] == "+" else -1
                    charge = sign * (int(cs[1:]) if cs[1:].isdigit() else len(cs))
                idx = mol.add_atom(el, charge, h, arom)
                i = end + 1
            else:
                two = s[i:i + 2]
                if two in ("Cl", "Br"):
                    el, arom, i = two, False, i + 2
                elif ch in "BCNOPSFI":
                    el, arom, i = ch, False, i + 1
                elif ch in "bcnops":
                    el, arom, i = AROMATIC_ATOMS[ch], True, i + 1
                else:
                    raise ValueError(f"Ký tự '{ch}' không hợp lệ trong SMILES (nguyên tử ngoài [ ] chỉ gồm B C N O P S F Cl Br I).")
                idx = mol.add_atom(el, 0, None, arom)
            if prev is not None:
                link(prev, idx, pending, mol.atoms[prev]["arom"], arom)
            prev, pending = idx, None
    if rings:
        raise ValueError("Số vòng chưa đóng (VD benzen phải là c1ccccc1).")
    if stack:
        raise ValueError("Thiếu dấu ')' đóng nhánh.")
    kekulize(mol)
    return mol


def kekulize(mol: Mol):
    arom_b = [b for b in mol.bonds if b["o"] == 1.5]
    if not arom_b:
        return
    used = [0.0] * len(mol.atoms)
    for b in mol.bonds:
        used[b["u"]] += 1 if b["o"] == 1.5 else b["o"]
        used[b["v"]] += 1 if b["o"] == 1.5 else b["o"]
    needy = set()
    for i, a in enumerate(mol.atoms):
        if not a["arom"] or not any(b["o"] == 1.5 and i in (b["u"], b["v"]) for b in mol.bonds):
            continue
        el, ch = a["el"], a["charge"]
        if a["h"] is None:
            if el == "C" and used[i] <= 3 or el == "N" and used[i] <= 2 or el in ("P",) and used[i] <= 2:
                needy.add(i)
        else:
            vals = CHARGED_VAL.get((el, ch)) if ch else ORGANIC_VAL.get(el)
            tgt = vals[0] if vals else 0
            if used[i] + a["h"] < tgt and el in ("C", "N", "P", "B"):
                needy.add(i)
    nb = defaultdict(list)
    for bi, b in enumerate(mol.bonds):
        if b["o"] == 1.5 and b["u"] in needy and b["v"] in needy:
            nb[b["u"]].append((b["v"], bi))
            nb[b["v"]].append((b["u"], bi))
    matched, chosen = {}, []

    def solve():
        free = [a for a in needy if a not in matched]
        if not free:
            return True
        a = min(free, key=lambda x: sum(1 for v, _ in nb[x] if v not in matched))
        for v, bi in nb[a]:
            if v in matched:
                continue
            matched[a], matched[v] = v, a
            chosen.append(bi)
            if solve():
                return True
            chosen.pop()
            del matched[a], matched[v]
        return False

    ok = solve()
    for bi, b in enumerate(mol.bonds):
        if b["o"] == 1.5:
            b["o"] = 2 if (ok and bi in chosen) else 1
            if not ok and b["u"] in needy and b["v"] in needy:
                b["o"] = 1.5


# ==============================================================================
# 3. GHI SMILES
# ==============================================================================
def to_smiles(mol: Mol) -> str:
    n = len(mol.atoms)
    if n == 0:
        return ""
    adj = defaultdict(list)
    for b in mol.bonds:
        adj[b["u"]].append((b["v"], b["o"]))
        adj[b["v"]].append((b["u"], b["o"]))
    hc = mol.hcounts()
    seen, order_idx, ring_ids, ring_next = set(), {}, {}, [1]
    # bước 1: DFS xác định cạnh đóng vòng
    tree_parent, ring_edges = {}, []

    def dfs_scan(u, p):
        seen.add(u)
        for v, o in adj[u]:
            if v == p and tree_parent.get(u) == p:
                continue
            if v in seen:
                key = frozenset((u, v))
                if key not in [e[0] for e in ring_edges]:
                    ring_edges.append((key, o))
            else:
                tree_parent[v] = u
                dfs_scan(v, u)

    for s in range(n):
        if s not in seen:
            tree_parent[s] = None
            dfs_scan(s, None)
    ring_label = defaultdict(list)
    for k, (key, o) in enumerate(ring_edges):
        a, b = tuple(key)
        ring_label[a].append((k + 1, o, b))
        ring_label[b].append((k + 1, o, a))
    sym = {1: "", 2: "=", 3: "#", 4: "$", 1.5: ":"}

    def atom_txt(i):
        a = mol.atoms[i]
        el, ch, h = a["el"], a["charge"], hc[i]
        default_h = Mol()
        default_h.atoms = [{"el": el, "charge": ch, "h": None, "arom": False, "x": 0, "y": 0}]
        # so sánh H tự tính khi chỉ xét hóa trị thực tế
        val = sum(o for v, o in adj[i])
        vals = CHARGED_VAL.get((el, ch)) if ch else ORGANIC_VAL.get(el)
        auto = None
        if vals:
            v = math.ceil(val - 1e-9)
            for vv in vals:
                if vv >= v:
                    auto = vv - v
                    break
        if el in SMILES_ORGANIC and ch == 0 and (a["h"] is None or a["h"] == auto):
            return el
        t = "[" + el
        if h:
            t += "H" + (str(h) if h > 1 else "")
        if ch:
            t += ("+" if ch > 0 else "-") + (str(abs(ch)) if abs(ch) > 1 else "")
        return t + "]"

    visited = set()

    def write(u, p):
        visited.add(u)
        out = atom_txt(u)
        for num, o, other in ring_label[u]:
            out += (sym.get(o, "") if (other in visited or True) and ring_closure_first(u, other, num) else "") + (str(num) if num < 10 else f"%{num}")
        kids = [(v, o) for v, o in adj[u] if v != p and tree_parent.get(v) == u]
        for j, (v, o) in enumerate(kids):
            piece = sym.get(o, "") + write(v, u)
            out += piece if j == len(kids) - 1 else f"({piece})"
        return out

    def ring_closure_first(u, other, num):
        return other not in visited and True

    parts = []
    for s in range(n):
        if tree_parent.get(s) is None and s not in visited:
            parts.append(write(s, None))
    return ".".join(parts)


# ==============================================================================
# 4. TÌM VÒNG (SSSR)
# ==============================================================================
def find_rings(n_atoms, bonds):
    adj = defaultdict(list)
    edges = []
    for b in bonds:
        u, v = (b["u"], b["v"]) if isinstance(b, dict) else (b[0], b[1])
        adj[u].append(v)
        adj[v].append(u)
        edges.append((u, v))
    if not edges:
        return []
    # số thành phần liên thông
    seen, comps = set(), 0
    for s in range(n_atoms):
        if s in seen or s not in adj:
            continue
        comps += 1
        q = [s]
        seen.add(s)
        while q:
            x = q.pop()
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    q.append(y)
    n_conn = len(seen)
    need = len(edges) - n_conn + comps
    if need <= 0:
        return []
    cands = []
    for (u, v) in edges:
        # đường ngắn nhất u->v không dùng cạnh (u,v)
        prev = {u: None}
        dq = deque([u])
        while dq and v not in prev:
            x = dq.popleft()
            for y in adj[x]:
                if x == u and y == v:
                    continue
                if y not in prev:
                    prev[y] = x
                    dq.append(y)
        if v in prev:
            path, x = [], v
            while x is not None:
                path.append(x)
                x = prev[x]
            cands.append(path[::-1])
    cands.sort(key=len)
    eidx = {frozenset(e): i for i, e in enumerate(edges)}
    basis, rings, seen_sets = [], [], set()
    for cyc in cands:
        key = frozenset(cyc)
        if key in seen_sets:
            continue
        vec = 0
        for k in range(len(cyc)):
            vec ^= 1 << eidx[frozenset((cyc[k], cyc[(k + 1) % len(cyc)]))]
        red = vec
        for bvec in basis:
            red = min(red, red ^ bvec)
        if red:
            basis.append(red)
            rings.append(cyc)
            seen_sets.add(key)
            if len(rings) >= need:
                break
    return rings


# ==============================================================================
# 5. DỰNG TỌA ĐỘ 2D
# ==============================================================================
def layout(mol: Mol, use_rdkit: bool = True):
    if not mol.atoms:
        return
    if use_rdkit and HAS_RDKIT:
        try:
            if _layout_rdkit(mol):
                return
        except Exception:
            pass
    _layout_own(mol)


def _layout_rdkit(mol: Mol) -> bool:
    rw = Chem.RWMol()
    for a in mol.atoms:
        at = Chem.Atom(a["el"])
        at.SetFormalCharge(a["charge"])
        at.SetNoImplicit(True)
        at.SetNumExplicitHs(0)
        rw.AddAtom(at)
    bt = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE, 1.5: Chem.BondType.SINGLE, 4: Chem.BondType.QUADRUPLE}
    for b in mol.bonds:
        rw.AddBond(b["u"], b["v"], bt.get(b["o"], Chem.BondType.SINGLE))
    m = rw.GetMol()
    m.UpdatePropertyCache(strict=False)
    rdDepictor.Compute2DCoords(m)
    conf = m.GetConformer()
    pts = [(conf.GetAtomPosition(i).x, conf.GetAtomPosition(i).y) for i in range(len(mol.atoms))]
    if mol.bonds:
        ls = [math.hypot(pts[b["u"]][0] - pts[b["v"]][0], pts[b["u"]][1] - pts[b["v"]][1]) for b in mol.bonds]
        scale = 1.0 / (sum(ls) / len(ls) or 1.0)
    else:
        scale = 1.0
    for a, (x, y) in zip(mol.atoms, pts):
        a["x"], a["y"] = x * scale, y * scale
    return True


def _components(n, adj):
    seen, comps = set(), []
    for s in range(n):
        if s in seen:
            continue
        comp, q = [], [s]
        seen.add(s)
        while q:
            x = q.pop()
            comp.append(x)
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        comps.append(sorted(comp))
    return comps


def _layout_own(mol: Mol):
    n = len(mol.atoms)
    adj = mol.adj()
    rings_all = find_rings(n, mol.bonds)
    xoff = 0.0
    for comp in _components(n, adj):
        cset = set(comp)
        rings = [r for r in rings_all if r[0] in cset]
        P = _layout_component(mol, comp, adj, rings)
        xs = [p[0] for p in P.values()]
        shift = xoff - min(xs)
        for i, (x, y) in P.items():
            mol.atoms[i]["x"], mol.atoms[i]["y"] = x + shift, y
        xoff += (max(xs) - min(xs)) + 1.7


def _ring_systems(rings):
    groups = []
    for r in rings:
        sr = set(r)
        merged = [g for g in groups if g["atoms"] & sr]
        new = {"atoms": set(sr), "rings": [r]}
        for g in merged:
            new["atoms"] |= g["atoms"]
            new["rings"] += g["rings"]
            groups.remove(g)
        groups.append(new)
    return groups


def _longest_end(comp, adj):
    def far(s):
        dist, dq, last = {s: 0}, deque([s]), s
        while dq:
            x = dq.popleft()
            last = x
            for y in adj[x]:
                if y not in dist:
                    dist[y] = dist[x] + 1
                    dq.append(y)
        return last
    ends = [a for a in comp if len(adj[a]) <= 1]
    return far(far(ends[0] if ends else comp[0]))


def _layout_component(mol, comp, adj, rings):
    P, side = {}, {}
    systems = _ring_systems(rings)
    atom_sys = {}
    for si, sy in enumerate(systems):
        for a in sy["atoms"]:
            atom_sys[a] = si
    placed_sys = set()

    def place_system(si, anchor=None, dirang=0.0):
        todo = sorted(systems[si]["rings"], key=len, reverse=True)
        if anchor is not None:
            first = next(r for r in todo if anchor in r)
        else:
            first = todo[0]
        todo.remove(first)
        k = len(first)
        R = 1.0 / (2 * math.sin(math.pi / k))
        if anchor is None:
            cx, cy, a0 = 0.0, 0.0, (math.pi / 2 if k != 4 else math.pi / 4)
            for j, at in enumerate(first):
                P[at] = (cx + R * math.cos(a0 + 2 * math.pi * j / k), cy + R * math.sin(a0 + 2 * math.pi * j / k))
        else:
            ax_, ay_ = P[anchor]
            cx, cy = ax_ + math.cos(dirang) * R, ay_ + math.sin(dirang) * R
            idx = first.index(anchor)
            for j in range(k):
                at = first[(idx + j) % k]
                ang = dirang + math.pi + 2 * math.pi * j / k
                P[at] = (cx + R * math.cos(ang), cy + R * math.sin(ang))
        centers = [(first, (cx, cy))]
        progress = True
        while todo and progress:
            progress = False
            for r in list(todo):
                placed = [a for a in r if a in P]
                if len(placed) == len(r):
                    todo.remove(r)
                    progress = True
                    continue
                if not placed:
                    continue
                k2 = len(r)
                R2 = 1.0 / (2 * math.sin(math.pi / k2))
                pair = None
                for j in range(k2):
                    a, b = r[j], r[(j + 1) % k2]
                    if a in P and b in P:
                        pair = (j, a, b)
                        break
                if pair:
                    j, a, b = pair
                    c0 = next((c for rr, c in centers if a in rr and b in rr), None)
                    if c0 is None:
                        c0 = (sum(P[t][0] for t in placed) / len(placed), sum(P[t][1] for t in placed) / len(placed))
                    mx, my = (P[a][0] + P[b][0]) / 2, (P[a][1] + P[b][1]) / 2
                    dx, dy = P[b][0] - P[a][0], P[b][1] - P[a][1]
                    d = math.hypot(dx, dy) or 1.0
                    nx, ny = -dy / d, dx / d
                    if (mx + nx - c0[0]) ** 2 + (my + ny - c0[1]) ** 2 < (mx - nx - c0[0]) ** 2 + (my - ny - c0[1]) ** 2:
                        nx, ny = -nx, -ny
                    ap = R2 * math.cos(math.pi / k2)
                    ccx, ccy = mx + nx * ap, my + ny * ap
                    r2 = r[j:] + r[:j]
                    aa = math.atan2(P[a][1] - ccy, P[a][0] - ccx)
                    ab = math.atan2(P[b][1] - ccy, P[b][0] - ccx)
                    sgn = 1 if ((ab - aa + math.pi) % (2 * math.pi) - math.pi) > 0 else -1
                    for m in range(k2):
                        at = r2[m]
                        if at not in P:
                            ang = aa + sgn * 2 * math.pi * m / k2
                            P[at] = (ccx + R2 * math.cos(ang), ccy + R2 * math.sin(ang))
                    centers.append((r, (ccx, ccy)))
                else:
                    a = placed[0]
                    c0 = next((c for rr, c in centers if a in rr), (0.0, 0.0))
                    out = math.atan2(P[a][1] - c0[1], P[a][0] - c0[0])
                    ccx, ccy = P[a][0] + math.cos(out) * R2, P[a][1] + math.sin(out) * R2
                    idx = r.index(a)
                    for m in range(k2):
                        at = r[(idx + m) % k2]
                        if at not in P:
                            ang = out + math.pi + 2 * math.pi * m / k2
                            P[at] = (ccx + R2 * math.cos(ang), ccy + R2 * math.sin(ang))
                    centers.append((r, (ccx, ccy)))
                todo.remove(r)
                progress = True
        placed_sys.add(si)

    if systems:
        biggest = max(range(len(systems)), key=lambda i: (len(systems[i]["rings"]), len(systems[i]["atoms"])))
        place_system(biggest)
        for a in systems[biggest]["atoms"]:
            side[a] = 1
    else:
        root = _longest_end(comp, adj)
        P[root] = (0.0, 0.0)
        side[root] = 1

    def is_linear(u):
        orders = [mol.bond_order(u, v) for v in adj[u]]
        return len(orders) == 2 and (3 in orders or orders.count(2) == 2)

    def subtree_size(v, block):
        seen, q = {v, block}, [v]
        cnt = 0
        while q:
            x = q.pop()
            cnt += 1
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        return cnt

    queue = deque(sorted(P.keys()))
    expanded = set()
    root_first = not systems
    while queue:
        u = queue.popleft()
        if u in expanded:
            continue
        expanded.add(u)
        un = [v for v in adj[u] if v not in P]
        if not un:
            continue
        pn = [v for v in adj[u] if v in P]
        ux, uy = P[u]
        m = len(un)
        sgn_u = side.get(u, 1)
        if not pn:
            base = math.pi / 6 if m == 1 else math.pi / 6 - math.pi / 2
            angs = [base] if m == 1 else [base + 2 * math.pi * k / m for k in range(m)]
            if m == 2 and is_linear(u):
                angs = [0.0, math.pi]
            elif m == 1 and is_linear(u):
                angs = [0.0]
            un_sorted = un
        elif len(pn) >= 2:
            vx = sum(ux - P[p][0] for p in pn)
            vy = sum(uy - P[p][1] for p in pn)
            out = math.atan2(vy, vx) if (abs(vx) + abs(vy)) > 1e-6 else 0.0
            if m == 1:
                angs = [out]
            else:
                spread = min(math.radians(60), math.radians(150) / m)
                angs = [out + spread * (k - (m - 1) / 2.0) * 1.0 for k in range(m)]
            un_sorted = sorted(un, key=lambda v: -subtree_size(v, u))
        else:
            p0 = pn[0]
            base = math.atan2(uy - P[p0][1], ux - P[p0][0])
            if m == 1:
                if is_linear(u):
                    angs = [base]
                else:
                    angs = [base - sgn_u * math.pi / 3]
                un_sorted = un
            elif m == 2:
                zz = base - sgn_u * math.pi / 3
                oth = base + sgn_u * math.pi / 3
                un_sorted = sorted(un, key=lambda v: -subtree_size(v, u))
                if is_linear(u):
                    zz, oth = base, base
                angs = [zz, oth]
            elif m == 3:
                un_sorted = sorted(un, key=lambda v: -subtree_size(v, u))
                angs = [base, base - math.pi / 2, base + math.pi / 2]
            else:
                un_sorted = un
                angs = [base + math.radians(-120 + 240 * k / (m - 1)) for k in range(m)]
        for v, ang in zip(un_sorted, angs):
            if v in P:
                continue
            P[v] = (ux + math.cos(ang), uy + math.sin(ang))
            if pn:
                base_ang = math.atan2(uy - P[pn[0]][1], ux - P[pn[0]][0]) if len(pn) == 1 else None
                if base_ang is None:
                    side[v] = 1
                else:
                    d = (ang - base_ang + math.pi) % (2 * math.pi) - math.pi
                    side[v] = (1 if d > 0 else -1) if abs(d) > 1e-6 else sgn_u
            else:
                side[v] = 1
            sv = atom_sys.get(v)
            if sv is not None and sv not in placed_sys:
                place_system(sv, anchor=v, dirang=ang)
                for a in systems[sv]["atoms"]:
                    side.setdefault(a, 1)
                    if a not in queue:
                        queue.append(a)
            queue.append(v)
        # các nguyên tử vòng mới đặt cũng cần mở rộng
        for a in list(P.keys()):
            if a not in expanded and a not in queue:
                queue.append(a)
    for a in comp:
        if a not in P:
            P[a] = (max(p[0] for p in P.values()) + 1.0, 0.0)
    ring_atoms = {a for r in rings for a in r}
    _resolve_overlaps(mol, comp, adj, P, ring_atoms)
    return P


def _overlap_score(P, atoms, bonded, thr=0.82):
    sc = 0.0
    for ia in range(len(atoms)):
        a = atoms[ia]
        for ib in range(ia + 1, len(atoms)):
            b = atoms[ib]
            if (a, b) in bonded:
                continue
            d = math.hypot(P[a][0] - P[b][0], P[a][1] - P[b][1])
            if d < thr:
                sc += (thr - d) ** 2 * 10
    return sc


def _resolve_overlaps(mol, comp, adj, P, ring_atoms):
    bonded = set()
    for b in mol.bonds:
        bonded.add((b["u"], b["v"]))
        bonded.add((b["v"], b["u"]))
    base = _overlap_score(P, comp, bonded)
    if base <= 0:
        return
    ring_bonds = set()
    rings = find_rings(len(mol.atoms), mol.bonds)
    for r in rings:
        for k in range(len(r)):
            ring_bonds.add(frozenset((r[k], r[(k + 1) % len(r)])))
    for _ in range(3):
        improved = False
        for b in mol.bonds:
            u, v = b["u"], b["v"]
            if frozenset((u, v)) in ring_bonds or u not in P or v not in P:
                continue
            side_v = {v}
            q = [v]
            while q:
                x = q.pop()
                for y in adj[x]:
                    if y != u and y not in side_v:
                        side_v.add(y)
                        q.append(y)
            if u in side_v or len(side_v) > len(comp) - 1:
                continue
            if len(side_v) > len(comp) / 2 + 1 and len(comp) > 3:
                tgt_u = True
                # lật phía u nếu phía v lớn hơn
                side_u = set(comp) - side_v
                mover, a_, b_ = side_u, v, u
            else:
                mover, a_, b_ = side_v, u, v
            if any(x in ring_atoms for x in mover) and len(mover & ring_atoms) != len(ring_atoms & mover):
                continue
            ax_, ay_ = P[a_]
            dx, dy = P[b_][0] - ax_, P[b_][1] - ay_
            d2 = dx * dx + dy * dy or 1.0
            old = {x: P[x] for x in mover}
            for x in mover:
                px, py = P[x][0] - ax_, P[x][1] - ay_
                t = (px * dx + py * dy) / d2
                fx, fy = t * dx, t * dy
                P[x] = (ax_ + 2 * fx - px, ay_ + 2 * fy - py)
            new_sc = _overlap_score(P, comp, bonded)
            if new_sc + 1e-9 < base:
                base = new_sc
                improved = True
            else:
                P.update(old)
            if base <= 0:
                return
        if not improved:
            break
    # nới lỏng nhẹ (PBD) cho nguyên tử không thuộc vòng
    if base > 0:
        fixed = ring_atoms
        for _ in range(60):
            moved = False
            for ia in range(len(comp)):
                for ib in range(ia + 1, len(comp)):
                    a, b = comp[ia], comp[ib]
                    if (a, b) in bonded:
                        continue
                    dx, dy = P[b][0] - P[a][0], P[b][1] - P[a][1]
                    d = math.hypot(dx, dy)
                    if d < 0.8:
                        if d < 1e-6:
                            dx, dy, d = 0.01, 0.0, 0.01
                        push = (0.8 - d) / 2
                        ux, uy = dx / d, dy / d
                        if a not in fixed:
                            P[a] = (P[a][0] - ux * push, P[a][1] - uy * push)
                        if b not in fixed:
                            P[b] = (P[b][0] + ux * push, P[b][1] + uy * push)
                        moved = True
            for bd in mol.bonds:
                u, v = bd["u"], bd["v"]
                if u not in P or v not in P:
                    continue
                dx, dy = P[v][0] - P[u][0], P[v][1] - P[u][1]
                d = math.hypot(dx, dy) or 1.0
                corr = (d - 1.0) / 2
                ux, uy = dx / d, dy / d
                if u in fixed and v in fixed:
                    continue
                if u in fixed:
                    P[v] = (P[v][0] - ux * corr * 2, P[v][1] - uy * corr * 2)
                elif v in fixed:
                    P[u] = (P[u][0] + ux * corr * 2, P[u][1] + uy * corr * 2)
                else:
                    P[u] = (P[u][0] + ux * corr, P[u][1] + uy * corr)
                    P[v] = (P[v][0] - ux * corr, P[v][1] - uy * corr)
            if not moved:
                break
    for a in comp:
        P[a] = (P[a][0], P[a][1])


# ==============================================================================
# 6. CÔNG THỨC CẤU TẠO THU GỌN  ->  ĐỒ THỊ
# ==============================================================================
# nhóm: tên -> (đoạn SMILES, nguyên tử vào, nguyên tử ra)
_GROUPS = {
    "COOH": ("C(=O)O", 0, None), "HOOC": ("C(=O)O", 0, 0), "COO": ("C(=O)O", 0, 2), "OOC": ("OC(=O)", 0, 1),
    "CHO": ("C=O", 0, None), "OHC": ("C=O", 0, 0), "CO": ("C=O", 0, 0),
    "CONH2": ("C(=O)N", 0, None), "CONH": ("C(=O)N", 0, 2), "NHCO": ("NC(=O)", 0, 1),
    "OH": ("O", 0, None), "HO": ("O", 0, 0), "NH2": ("N", 0, None), "H2N": ("N", 0, 0),
    "NO2": ("[N+](=O)[O-]", 0, None), "O2N": ("[N+](=O)[O-]", 0, 0), "CN": ("C#N", 0, None),
    "SH": ("S", 0, None), "HS": ("S", 0, 0), "SO3H": ("S(=O)(=O)O", 0, None), "HSO3": ("S(=O)(=O)O", 0, 0),
    "C6H5": ("c1ccccc1", 0, 0), "C6H4": ("c1ccc(cc1)", 0, 3), "C6H11": ("C1CCCCC1", 0, 0),
    "C5H9": ("C1CCCC1", 0, 0), "C3H5": ("CC=C", 0, None), "C2H3": ("C=C", 0, None),
    "Ph": ("c1ccccc1", 0, 0),
    "Cl": ("Cl", 0, 0), "Br": ("Br", 0, 0), "F": ("F", 0, 0), "I": ("I", 0, 0),
    "O": ("O", 0, 0), "S": ("S", 0, 0), "N": ("N", 0, 0), "NH": ("N", 0, 0), "P": ("P", 0, 0),
}
_GROUP_ORDER = sorted(_GROUPS, key=len, reverse=True)
_ALKYL = re.compile(r"^C(\d*)H(\d*)")


def _read_group(s, i):
    for g in _GROUP_ORDER:
        if s.startswith(g, i):
            # tránh nhầm "CO" + "NH2"... ưu tiên theo độ dài đã sắp xếp
            if g in ("C6H5", "C6H4") or g.isalpha() or any(ch.isdigit() for ch in g):
                nxt = s[i + len(g):i + len(g) + 1]
                if g in ("O", "S", "N", "P", "F", "I", "Cl", "Br", "NH") and nxt.isdigit():
                    # O2, N2... xem như nhiều nguyên tử, bỏ qua kiểm tra
                    pass
                return g, _GROUPS[g], i + len(g)
    m = _ALKYL.match(s[i:])
    if m:
        n = int(m.group(1)) if m.group(1) else 1
        h = int(m.group(2)) if m.group(2) else (1 if "H" in m.group(0) else 0)
        return m.group(0), ("C" * n, 0, n - 1), i + m.end()
    if s[i] == "C":
        return "C", ("C", 0, 0), i + 1
    if s[i] == "H":
        return "H", ("[H]", 0, 0), i + 1
    raise ValueError(f"Không nhận diện được '{s[i:i + 4]}' trong công thức thu gọn.")


def parse_condensed(text: str) -> Mol:
    s = text.replace(" ", "").replace("−", "-").replace("≡", "#").replace("–", "-")
    s = s.translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789"))
    if not s:
        raise ValueError("Chưa nhập công thức.")
    mol = Mol()
    pos = [0]
    BOND = {"-": 1, "=": 2, "#": 3}

    def add_group(frag_smi):
        sub = parse_smiles(frag_smi.replace("[H]", "[H]"))
        base = len(mol.atoms)
        for a in sub.atoms:
            mol.atoms.append(dict(a))
        for b in sub.bonds:
            mol.bonds.append({"u": b["u"] + base, "v": b["v"] + base, "o": b["o"]})
        return base

    def parse_chain(parent_exit, pending_attach):
        """Trả về (atom_vào_đầu_tiên, exit_cuối)."""
        first_entry, prev_exit = None, parent_exit
        order = 1
        attach_now = list(pending_attach)
        while pos[0] < len(s):
            ch = s[pos[0]]
            if ch == ")":
                break
            if ch in BOND:
                order = BOND[ch]
                pos[0] += 1
                continue
            if ch == "(":
                pos[0] += 1
                saved = order
                sub_first, _ = parse_chain(prev_exit, [])
                if pos[0] >= len(s) or s[pos[0]] != ")":
                    raise ValueError("Thiếu dấu ')' trong công thức thu gọn.")
                pos[0] += 1
                mult = 1
                m = re.match(r"\d+", s[pos[0]:])
                if m:
                    mult = int(m.group(0))
                    pos[0] += m.end()
                if prev_exit is None:
                    attach_now.append((sub_first, saved, mult))
                order = 1
                if mult > 1 and prev_exit is not None:
                    for _ in range(mult - 1):
                        # nhân bản nhánh vừa tạo
                        pass
                continue
            name, (frag, ent, ext), npos = _read_group(s, pos[0])
            pos[0] = npos
            # hệ số lặp cho nguyên tử đơn như O2, N2 (khí): bỏ qua, xử lý ở từ điển công thức
            base = add_group(frag)
            entry = base + ent
            exit_ = None if ext is None else base + ext
            if exit_ is None and first_entry is None and prev_exit is None and pos[0] < len(s) and s[pos[0]] not in ")":
                exit_ = entry   # nhóm đứng đầu mạch (NH2-CH2-COOH, OH-CH2-...): nối bằng nguyên tử vào
            if first_entry is None:
                first_entry = entry
            for (pa, o2, mult) in attach_now:
                mol.add_bond(entry, pa, o2)
            attach_now = []
            if prev_exit is not None:
                mol.add_bond(prev_exit, entry, order)
            order = 1
            prev_exit = exit_
            if exit_ is None and pos[0] < len(s) and s[pos[0]] not in ")":
                # nhóm cụt (COOH, OH...) mà vẫn còn ký tự sau -> lỗi cấu tạo
                if s[pos[0]] in BOND or s[pos[0]] == "(":
                    raise ValueError(f"Nhóm '{name}' là nhóm đầu mạch, không thể nối tiếp.")
        return first_entry, prev_exit

    # Xử lý nhánh có hệ số: viết lại đơn giản bằng cách nhân bản chuỗi ký tự trong ngoặc
    s_expanded = _expand_parens(s)
    s = s_expanded
    parse_chain(None, [])
    if pos[0] < len(s):
        raise ValueError("Công thức thu gọn có dấu ')' thừa.")
    kekulize(mol)
    return mol


def _expand_parens(s: str) -> str:
    """(CH3)3C -> (CH3)(CH3)(CH3)C: nhân bản nhánh theo hệ số."""
    out, i = "", 0
    while i < len(s):
        if s[i] == "(":
            depth, j = 1, i + 1
            while j < len(s) and depth:
                depth += (s[j] == "(") - (s[j] == ")")
                j += 1
            inner = _expand_parens(s[i + 1:j - 1])
            m = re.match(r"\d+", s[j:])
            mult = int(m.group(0)) if m else 1
            j += m.end() if m else 0
            out += f"({inner})" * mult
            i = j
        else:
            out += s[i]
            i += 1
    return out


# ==============================================================================
# 7. TỰ NHẬN DIỆN ĐẦU VÀO: TÊN CHẤT / CÔNG THỨC / SMILES
# ==============================================================================
def _norm(t: str) -> str:
    t = t.strip().lower().replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s\-_,'()]+", "", t)


def mol_from_input(raw: str):
    """Trả về (Mol, ghi_chú, smiles). Nhận SMILES, công thức thu gọn, công thức phân tử quen thuộc, hoặc tên chất."""
    import data_chem as dc
    s = raw.strip()
    if not s:
        raise ValueError("Chưa nhập nội dung.")
    compact = s.replace(" ", "")
    if compact in dc.FORMULA_TO_SMILES:
        smi = dc.FORMULA_TO_SMILES[compact]
        return parse_smiles(smi), f"Nhận diện công thức {compact} → SMILES: {smi}", smi
    key = _norm(s)
    smi = dc.name_to_smiles(key)
    if smi:
        return parse_smiles(smi), f"Nhận diện tên chất «{s}» → SMILES: {smi}", smi
    has_h_atom = bool(re.search(r"H", re.sub(r"\[[^\]]*\]", "", s)))
    errs = []
    order = ("cond", "smi") if has_h_atom and re.match(r"^[A-Za-z0-9()=#\-≡₀-₉]+$", compact) else ("smi", "cond")
    for kind in order:
        try:
            if kind == "smi":
                m = parse_smiles(s)
                return m, "", s
            m = parse_condensed(s)
            smi = to_smiles(m)
            return m, f"Đã chuyển công thức thu gọn {compact} → SMILES: {smi}", smi
        except Exception as exc:
            errs.append(str(exc))
    raise ValueError(errs[0] if errs else "Không nhận diện được đầu vào.")


# ==============================================================================
# 8. CẢNH VẼ (DÙNG CHUNG MATPLOTLIB / QPAINTER)
# ==============================================================================
def atom_label(mol, i, hc, adj, show_ch3=True, cmode="skeleton", ring_atoms=frozenset(), ring_c=False):
    """Trả về (prefix, el, suffix, charge, vert) hoặc None nếu ẩn nhãn. vert=(text,'up'|'down') khi H nằm trên/dưới.
    cmode: skeleton (ẩn C trong mạch) | inline (CH3, CH2, CH, C cùng dòng) | stacked (C có H trên/dưới)."""
    a = mol.atoms[i]
    el, ch, h = a["el"], a["charge"], hc[i]
    deg = len(adj[i])
    hs = "" if h <= 0 else ("H" if h == 1 else "H" + str(h).translate(SUBS))
    cs = ""
    if ch:
        cs = (str(abs(ch)).translate(SUPS) if abs(ch) > 1 else "") + ("⁺" if ch > 0 else "⁻")
    if el == "C" and ch == 0:
        in_ring = i in ring_atoms
        if cmode == "skeleton" or (in_ring and not ring_c and deg >= 2):
            if deg >= 2:
                orders = sorted(mol.bond_order(i, v) for v in adj[i])
                if not (deg == 2 and orders == [2, 2]):
                    return None
            elif deg == 1 and not show_ch3:
                return None
        elif cmode == "inline":
            return "", "C" + hs, "", cs, None
        elif cmode == "stacked" and deg >= 2 and hs:
            angs = [math.atan2(mol.atoms[v]["y"] - a["y"], mol.atoms[v]["x"] - a["x"]) for v in adj[i]]

            def gap(t):
                return min(abs((t - x + math.pi) % (2 * math.pi) - math.pi) for x in angs)
            up, dn = gap(math.pi / 2), gap(-math.pi / 2)
            if max(up, dn) < math.radians(40):      # cả trên và dưới đều vướng liên kết -> viết cùng dòng
                return "", "C" + hs, "", cs, None
            return "", el, "", cs, (hs, "up" if up >= dn else "down")
    if not hs:
        return "", el, "", cs, None
    if deg == 0:
        return "", el, hs, cs, None
    if deg == 1:
        nb = adj[i][0]
        flip = mol.atoms[nb]["x"] - a["x"] > 0.28
        return (hs if flip else ""), el, ("" if flip else hs), cs, None
    vx = sum(a["x"] - mol.atoms[v]["x"] for v in adj[i])
    vy = sum(a["y"] - mol.atoms[v]["y"] for v in adj[i])
    if abs(vy) > 1.2 * abs(vx) and abs(vy) > 0.4:
        return "", el, "", cs, (hs, "up" if vy > 0 else "down")
    if vx < -0.4:
        return hs, el, "", cs, None
    return "", el, hs, cs, None


def build_scene(mol: Mol, measure, show_ch3=True, mono=False, dark=False, cmode="skeleton", ring_c=False):
    """Trả về dict(lines, texts, bounds). Toạ độ: độ dài liên kết = 1, trục y hướng LÊN."""
    n = len(mol.atoms)
    adj = mol.adj()
    hc = mol.hcounts()
    pal = PALETTE_DARK if dark else PALETTE_LIGHT
    line_col = pal["C"]
    lines, texts, wedges = [], [], []
    labels = {}
    ring_atoms = {a for r in find_rings(n, mol.bonds) for a in r}
    for i in range(n):
        lb = atom_label(mol, i, hc, adj, show_ch3, cmode, ring_atoms, ring_c)
        if lb:
            labels[i] = lb
    half_h = 0.20

    def trim(i, ang):
        if i not in labels:
            return 0.0
        pre, el, suf, cs, vert = labels[i]
        hw = measure(el) / 2 + 0.07
        c, s_ = abs(math.cos(ang)), abs(math.sin(ang))
        t = min(hw / c if c > 1e-6 else 9, half_h / s_ if s_ > 1e-6 else 9)
        return min(t, 0.42) + 0.03

    rings = find_rings(n, mol.bonds)
    ring_of_bond = {}
    for r in sorted(rings, key=len):
        cx = sum(mol.atoms[a]["x"] for a in r) / len(r)
        cy = sum(mol.atoms[a]["y"] for a in r) / len(r)
        for k in range(len(r)):
            ring_of_bond.setdefault(frozenset((r[k], r[(k + 1) % len(r)])), (cx, cy))

    def ecol(i):
        if mono:
            return line_col
        return pal.get(mol.atoms[i]["el"], pal["default"])

    def add_line(x1, y1, x2, y2, c1, c2, dashed=False):
        if c1 == c2:
            lines.append((x1, y1, x2, y2, c1, dashed))
        else:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            lines.append((x1, y1, mx, my, c1, dashed))
            lines.append((mx, my, x2, y2, c2, dashed))

    for b in mol.bonds:
        u, v, o = b["u"], b["v"], b["o"]
        x1, y1, x2, y2 = mol.atoms[u]["x"], mol.atoms[u]["y"], mol.atoms[v]["x"], mol.atoms[v]["y"]
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        nx, ny = -uy, ux
        ang = math.atan2(dy, dx)
        t1, t2 = trim(u, ang), trim(v, ang + math.pi)
        c1, c2 = ecol(u), ecol(v)
        if c1 != c2 and (u not in labels or v not in labels):
            c1 = c2 = c1 if (u in labels or v not in labels) and mol.atoms[u]["el"] != "C" else (c2 if mol.atoms[v]["el"] != "C" else line_col)
            if u not in labels and v not in labels:
                c1 = c2 = line_col
        sx, sy = x1 + ux * t1, y1 + uy * t1
        ex, ey = x2 - ux * t2, y2 - uy * t2
        off = 0.12
        stereo = b.get("stereo", 0)
        if o == 1 and stereo == 1:
            hw = 0.115
            wedges.append(((sx, sy), (ex + nx * hw, ey + ny * hw), (ex - nx * hw, ey - ny * hw), c1))
        elif o == 1 and stereo == -1:
            steps = 6
            for k in range(1, steps + 1):
                frac = k / steps
                px = sx + (ex - sx) * frac
                py = sy + (ey - sy) * frac
                hw = 0.025 + 0.09 * frac
                col_h = c1 if frac < 0.5 else c2
                lines.append((px - nx * hw, py - ny * hw, px + nx * hw, py + ny * hw, col_h, False))
        elif o in (1, 4):
            add_line(sx, sy, ex, ey, c1, c2)
        elif o == 3:
            add_line(sx, sy, ex, ey, c1, c2)
            for sg in (1, -1):
                add_line(sx + nx * off * sg, sy + ny * off * sg, ex + nx * off * sg, ey + ny * off * sg, c1, c2)
        else:  # đôi (hoặc thơm 1.5)
            dashed2 = (o == 1.5)
            key = frozenset((u, v))
            rc = ring_of_bond.get(key)
            deg_u, deg_v = len(adj[u]), len(adj[v])
            if rc is not None:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                sg = 1 if (nx * (rc[0] - mx) + ny * (rc[1] - my)) > 0 else -1
                add_line(sx, sy, ex, ey, c1, c2)
                tr = 0.13
                a1 = (x1 + ux * (t1 + tr) + nx * off * 1.05 * sg, y1 + uy * (t1 + tr) + ny * off * 1.05 * sg)
                a2 = (x2 - ux * (t2 + tr), y2 - uy * (t2 + tr))
                a2 = (a2[0] + nx * off * 1.05 * sg, a2[1] + ny * off * 1.05 * sg)
                if t1 == 0:
                    a1 = (a1[0] + ux * 0.04, a1[1] + uy * 0.04)
                add_line(a1[0], a1[1], a2[0], a2[1], c1, c2, dashed2)
            elif (deg_u >= 2 and deg_v >= 2) and not (u in labels and v in labels):
                # nối đôi trong mạch: vạch phụ lệch về phía có nhóm thế
                others = [w for w in adj[u] if w != v] + [w for w in adj[v] if w != u]
                sc = sum(nx * (mol.atoms[w]["x"] - (x1 + x2) / 2) + ny * (mol.atoms[w]["y"] - (y1 + y2) / 2) for w in others)
                sg = 1 if sc >= 0 else -1
                add_line(sx, sy, ex, ey, c1, c2)
                add_line(sx + ux * 0.12 + nx * off * sg, sy + uy * 0.12 + ny * off * sg, ex - ux * 0.12 + nx * off * sg, ey - uy * 0.12 + ny * off * sg, c1, c2, dashed2)
            else:
                for sg in (0.5, -0.5):
                    add_line(sx + nx * off * sg, sy + ny * off * sg, ex + nx * off * sg, ey + ny * off * sg, c1, c2, dashed2)
    for i, (pre, el, suf, cs, vert) in labels.items():
        a = mol.atoms[i]
        w_el = measure(el)
        left = measure(pre) if pre else 0.0
        text = pre + el + suf + cs
        texts.append({"x": a["x"] - left - w_el / 2, "y": a["y"], "text": text, "color": ecol(i)})
        if vert:
            vt, where = vert
            texts.append({"x": a["x"] - measure(vt) / 2, "y": a["y"] + (0.40 if where == "up" else -0.40), "text": vt, "color": ecol(i)})
    xs = [a["x"] for a in mol.atoms]
    ys = [a["y"] for a in mol.atoms]
    for t in texts:
        xs += [t["x"], t["x"] + measure(t["text"])]
    pad = 0.55
    bounds = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    return {"lines": lines, "texts": texts, "wedges": wedges, "bounds": bounds}


_MOL_RENDER_CACHE = {}


def render_mol_bytes(mol: Mol, fmt="png", bg="transparent", mono=False, show_ch3=True, bond_px=64, out_dpi=200, cmode="skeleton", ring_c=False) -> bytes:
    cache_key = (
        tuple((a["el"], a["charge"], a["h"], round(a["x"], 3), round(a["y"], 3)) for a in mol.atoms),
        tuple((b["u"], b["v"], b["o"], b.get("stereo", 0)) for b in mol.bonds),
        fmt, bg, mono, show_ch3, bond_px, out_dpi, cmode, ring_c,
    )
    cached = _MOL_RENDER_CACHE.get(cache_key)
    if cached is not None:
        return cached
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    dark = (bg == "dark")
    fp = FontProperties(family=["DejaVu Sans"], size=bond_px * 0.36 * 72 / 100.0)
    probe = Figure(figsize=(2, 2), dpi=100)
    FigureCanvasAgg(probe)
    rend = probe.canvas.get_renderer()

    def measure(t):
        if not t:
            return 0.0
        w, _, _ = rend.get_text_width_height_descent(t, fp, False)
        return w / bond_px

    scene = build_scene(mol, measure, show_ch3, mono, dark, cmode, ring_c)
    x0, y0, x1, y1 = scene["bounds"]
    w_u, h_u = max(x1 - x0, 3.2), max(y1 - y0, 2.2)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0, x1, y0, y1 = cx - w_u / 2, cx + w_u / 2, cy - h_u / 2, cy + h_u / 2
    fig = Figure(figsize=(w_u * bond_px / 100.0, h_u * bond_px / 100.0), dpi=100)
    FigureCanvasAgg(fig)
    face = {"transparent": "none", "dark": "#0B1120", "white": "#FFFFFF"}.get(bg, "none")
    if bg == "transparent":
        fig.patch.set_alpha(0.0)
    else:
        fig.patch.set_facecolor(face)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    from matplotlib.patches import Polygon
    lw = bond_px * 0.034 * 72 / 100.0
    for (p1, p2, p3, col) in scene.get("wedges", ()):
        ax.add_patch(Polygon([p1, p2, p3], closed=True, facecolor=col, edgecolor=col, lw=lw * 0.4))
    for (ax1, ay1, ax2, ay2, col, dashed) in scene["lines"]:
        ax.plot([ax1, ax2], [ay1, ay2], color=col, lw=lw, solid_capstyle="round",
                linestyle=(0, (2.2, 1.6)) if dashed else "-")
    for t in scene["texts"]:
        ax.text(t["x"], t["y"], t["text"], color=t["color"], fontproperties=fp, ha="left", va="center_baseline")
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=out_dpi if fmt != "svg" else 100, facecolor=face if bg != "transparent" else "none",
                transparent=(bg == "transparent"))
    out = buf.getvalue()
    if len(_MOL_RENDER_CACHE) > 120:
        _MOL_RENDER_CACHE.clear()
    _MOL_RENDER_CACHE[cache_key] = out
    return out


def make_mol(raw: str, use_rdkit=True):
    """Tiện ích: đầu vào -> (Mol đã có tọa độ, ghi chú, smiles)."""
    mol, note, smi = mol_from_input(raw)
    layout(mol, use_rdkit)
    return mol, note, smi
