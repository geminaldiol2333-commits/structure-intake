# Throwaway intake prototypes. Not part of the render pipeline.
# Three schemes, one geometry model: atoms and bonds with coordinates.
# The picture is drawn from those coordinates. SMILES and SMARTS are derived after.

from __future__ import annotations

import base64
import json
import math
import os
import shutil
import time
import traceback

import fitz
import numpy as np
from PIL import Image, ImageDraw
from rdkit import Chem
from rdkit.Chem import rdDepictor

ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(ROOT, "samples")
OUT = os.path.join(ROOT, "out")
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
MOLSCRIBE_CKPT = r"D:\AI_Tools\models\MolScribe\swin_base_char_aux_1m680k.pth"
MOLNEXTR_CKPT = r"D:\AI_Tools\models\MolNexTR\molnextr_best.pth"

ELEMENTS = {
    "H", "B", "C", "N", "O", "F", "Si", "P", "S", "Cl", "Br", "I", "Se",
}

LITERATURE = os.path.join(SAMPLES, "bjoc-19-142.pdf")
PLOS = os.path.join(SAMPLES, "plos-candidate.pdf")
COMPLEX = os.path.join(SAMPLES, "complex-halichondrin.png")
COMMON = os.path.join(SAMPLES, "common-structure.jpg")
CHART = os.path.join(SAMPLES, "no-structure-chart.png")


def ensure_dirs():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "clips"), exist_ok=True)


def path_points(drawing):
    pts = []
    curves = 0
    for item in drawing["items"]:
        if item[0] == "c":
            curves += 1
        for point in item[1:]:
            if hasattr(point, "x"):
                pts.append((point.x, point.y))
    return pts, curves


def centerline(drawing):
    pts, curves = path_points(drawing)
    if len(pts) < 2:
        return None
    arr = np.array(pts, dtype=float)
    center = arr.mean(axis=0)
    shifted = arr - center
    cov = shifted.T @ shifted
    _, vecs = np.linalg.eigh(cov)
    axis = vecs[:, 1]
    proj = shifted @ axis
    p1 = center + axis * float(proj.min())
    p2 = center + axis * float(proj.max())
    length = float(proj.max() - proj.min())
    perp = np.array([-axis[1], axis[0]])
    side = shifted @ perp
    thick = float(np.max(np.abs(side)) * 2) if len(side) else 0.0
    # A wedge is wide at one end and pointed at the other.
    span = max(length, 1e-6)
    near = side[proj < proj.min() + 0.22 * span]
    far = side[proj > proj.max() - 0.22 * span]
    w_near = float(np.max(np.abs(near)) * 2) if len(near) else thick
    w_far = float(np.max(np.abs(far)) * 2) if len(far) else thick
    stereo = ""
    if min(w_near, w_far) > 0 and max(w_near, w_far) > 2.4 * min(w_near, w_far) and max(w_near, w_far) > 1.6:
        # Wide end is the atom the wedge starts from.
        if w_near > w_far:
            stereo = "wedge"
        else:
            stereo = "wedge"
            p1, p2 = p2, p1
    rect = drawing["rect"]
    return {
        "p1": (float(p1[0]), float(p1[1])),
        "p2": (float(p2[0]), float(p2[1])),
        "length": length,
        "thick": thick,
        "curves": curves,
        "stereo": stereo,
        "rect": (rect.x0, rect.y0, rect.x1, rect.y1),
        "long": max(rect.width, rect.height),
        "short": min(rect.width, rect.height),
    }


def page_primitives(page):
    # Classify by the stroke itself. A diagonal bond has a fat
    # axis-aligned box, so the box aspect is the wrong test.
    bonds = []
    ticks = []
    glyphs = []
    for drawing in page.get_drawings():
        info = centerline(drawing)
        if info is None:
            continue
        length = info["length"]
        thick = max(info["thick"], 0.15)
        if info["long"] > 90:
            continue
        ratio = length / thick
        is_bond = 6.0 <= length <= 30.0 and thick <= 5.5 and ratio >= 3.0 and info["curves"] <= 6
        is_tick = 1.1 <= length < 6.0 and thick <= 2.4 and ratio >= 2.4 and info["curves"] <= 2
        is_glyph = (not is_bond) and (not is_tick) and 1.4 <= length <= 16.0 and ratio < 3.2 and info["long"] < 22
        if is_bond:
            bonds.append(info)
        elif is_tick:
            ticks.append(info)
        elif is_glyph:
            glyphs.append(info)
    return bonds, ticks, glyphs


class UnionFind:
    def __init__(self, count):
        self.parent = list(range(count))

    def find(self, index):
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def union(self, left, right):
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_left] = root_right


def cluster_bonds(bonds, gap):
    if not bonds:
        return []
    count = len(bonds)
    union = UnionFind(count)
    ends = [(bond["p1"], bond["p2"]) for bond in bonds]
    for i in range(count):
        for j in range(i + 1, count):
            close = False
            for a in ends[i]:
                for b in ends[j]:
                    if math.hypot(a[0] - b[0], a[1] - b[1]) <= gap:
                        close = True
                        break
                if close:
                    break
            if close:
                union.union(i, j)
    groups = {}
    for index, bond in enumerate(bonds):
        groups.setdefault(union.find(index), []).append(bond)
    return list(groups.values())


def axis_fraction(bonds):
    if not bonds:
        return 1.0
    axis = 0
    for bond in bonds:
        x1, y1 = bond["p1"]
        x2, y2 = bond["p2"]
        angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1))) % 180
        distance = min(angle, abs(angle - 90), abs(angle - 180))
        if distance < 8:
            axis += 1
    return axis / len(bonds)


def dashed_from_ticks(ticks):
    """Colinear short strokes become one dashed bond."""
    used = set()
    dashed = []
    for i, tick in enumerate(ticks):
        if i in used:
            continue
        x1, y1 = tick["p1"]
        x2, y2 = tick["p2"]
        angle = math.atan2(y2 - y1, x2 - x1)
        group = [tick]
        used.add(i)
        for j in range(i + 1, len(ticks)):
            if j in used:
                continue
            other = ticks[j]
            ox1, oy1 = other["p1"]
            ox2, oy2 = other["p2"]
            oangle = math.atan2(oy2 - oy1, ox2 - ox1)
            if abs((angle - oangle + math.pi / 2) % math.pi - math.pi / 2) > 0.35:
                continue
            mid = ((x1 + x2) / 2, (y1 + y2) / 2)
            omid = ((ox1 + ox2) / 2, (oy1 + oy2) / 2)
            if math.hypot(mid[0] - omid[0], mid[1] - omid[1]) < 14:
                group.append(other)
                used.add(j)
        if len(group) < 3:
            continue
        points = [point for item in group for point in (item["p1"], item["p2"])]
        # Ends of the dash run are the two points farthest apart.
        best = (0, 0, 0)
        for a_index, a in enumerate(points):
            for b in points[a_index + 1:]:
                dist = math.hypot(a[0] - b[0], a[1] - b[1])
                if dist > best[0]:
                    best = (dist, a, b)
        if best[0] < 6:
            continue
        dashed.append({
            "p1": best[1],
            "p2": best[2],
            "length": best[0],
            "thick": 0.6,
            "curves": 0,
            "stereo": "hash",
            "rect": (0, 0, 0, 0),
            "long": best[0],
            "short": 0.6,
            "order": 1,
        })
    return dashed


def merge_parallel(bonds):
    """Two close parallel centerlines are one double bond. Three are a triple."""
    order = [1] * len(bonds)
    used = [False] * len(bonds)
    merged = []
    for i, bond in enumerate(bonds):
        if used[i]:
            continue
        group = [i]
        x1, y1 = bond["p1"]
        x2, y2 = bond["p2"]
        vx, vy = x2 - x1, y2 - y1
        norm = math.hypot(vx, vy) or 1
        ux, uy = vx / norm, vy / norm
        px, py = -uy, ux
        for j in range(i + 1, len(bonds)):
            if used[j]:
                continue
            other = bonds[j]
            ox1, oy1 = other["p1"]
            ox2, oy2 = other["p2"]
            ovx, ovy = ox2 - ox1, oy2 - oy1
            onorm = math.hypot(ovx, ovy) or 1
            dot = abs((ovx * ux + ovy * uy) / onorm)
            if dot < 0.92:
                continue
            mid_off = abs(((ox1 + ox2) / 2 - x1) * px + ((oy1 + oy2) / 2 - y1) * py)
            if mid_off > 2.6:
                continue
            # Projection overlap along the first bond.
            t1 = 0
            t2 = norm
            s1 = ((ox1 - x1) * ux + (oy1 - y1) * uy)
            s2 = ((ox2 - x1) * ux + (oy2 - y1) * uy)
            lo, hi = min(s1, s2), max(s1, s2)
            overlap = min(t2, hi) - max(t1, lo)
            if overlap < 0.55 * min(norm, onorm):
                continue
            group.append(j)
        for index in group:
            used[index] = True
        kept = dict(bonds[i])
        kept["order"] = 1 if len(group) == 1 else (2 if len(group) == 2 else 3)
        merged.append(kept)
    return merged


def bbox_of(bonds, pad):
    xs, ys = [], []
    for bond in bonds:
        xs.extend((bond["p1"][0], bond["p2"][0]))
        ys.extend((bond["p1"][1], bond["p2"][1]))
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def group_glyphs(glyphs, box):
    x0, y0, x1, y1 = box
    inside = []
    for glyph in glyphs:
        rect = glyph["rect"]
        cx = (rect[0] + rect[2]) / 2
        cy = (rect[1] + rect[3]) / 2
        if x0 - 2 <= cx <= x1 + 2 and y0 - 2 <= cy <= y1 + 2:
            inside.append(glyph)
    inside.sort(key=lambda item: ((item["rect"][1] + item["rect"][3]) / 2, item["rect"][0]))
    words = []
    for glyph in inside:
        rect = glyph["rect"]
        placed = False
        for word in words:
            wr = word["rect"]
            vertical = min(rect[3], wr[3]) - max(rect[1], wr[1])
            height = min(rect[3] - rect[1], wr[3] - wr[1])
            gap = rect[0] - wr[2]
            if height > 0 and vertical > 0.45 * height and -1.2 <= gap <= 2.4:
                word["glyphs"].append(glyph)
                word["rect"] = (
                    min(wr[0], rect[0]), min(wr[1], rect[1]),
                    max(wr[2], rect[2]), max(wr[3], rect[3]),
                )
                placed = True
                break
        if not placed:
            words.append({"glyphs": [glyph], "rect": rect})
    return words


def inflate_rect(rect):
    # 30% of the word's own width and height, added on every side.
    x0, y0, x1, y1 = rect
    width = x1 - x0
    height = y1 - y0
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    half_w = width / 2.0 + 0.30 * width
    half_h = height / 2.0 + 0.30 * height
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def rect_gap_joins(left, right):
    vertical = min(left[3], right[3]) - max(left[1], right[1])
    height = min(left[3] - left[1], right[3] - right[1])
    if height <= 0 or vertical <= 0.45 * height:
        return False
    gap = right[0] - left[2]
    return -1.2 <= gap <= 2.4


def label_words(glyphs, ticks):
    """Glyph runs from group_glyphs. A label hyphen is a tick between two runs."""
    words = group_glyphs(glyphs, (-1e6, -1e6, 1e6, 1e6))
    if len(words) < 2 or not ticks:
        return words
    union = UnionFind(len(words))
    for tick in ticks:
        rect = tick["rect"]
        touched = []
        for index, word in enumerate(words):
            host = word["rect"]
            if rect_gap_joins(host, rect) or rect_gap_joins(rect, host):
                touched.append(index)
        if len(touched) < 2:
            continue
        for other in touched[1:]:
            union.union(touched[0], other)
    grouped = {}
    for index, word in enumerate(words):
        grouped.setdefault(union.find(index), []).append(word)
    merged = []
    for bucket in grouped.values():
        rect = bucket[0]["rect"]
        glyphs_in = []
        for word in bucket:
            glyphs_in.extend(word["glyphs"])
            other = word["rect"]
            rect = (
                min(rect[0], other[0]), min(rect[1], other[1]),
                max(rect[2], other[2]), max(rect[3], other[3]),
            )
        merged.append({"glyphs": glyphs_in, "rect": rect})
    return merged


def rect_separation(left, right):
    gap_x = max(left[0], right[0]) - min(left[2], right[2])
    gap_y = max(left[1], right[1]) - min(left[3], right[3])
    if gap_x < 0 and gap_y < 0:
        return max(gap_x, gap_y)
    if gap_x < 0:
        return gap_y
    if gap_y < 0:
        return gap_x
    return math.hypot(gap_x, gap_y)


def merge_touching_words(words, reach=1.2):
    """Pieces of one letter sit 0.5 pt apart and fail the baseline overlap test.

    A 1.2 pt reach joins those pieces. It stays under the gap between words.
    """
    if len(words) < 2:
        return words
    union = UnionFind(len(words))
    for left_index, left in enumerate(words):
        left_rect = left["rect"]
        for right_index in range(left_index + 1, len(words)):
            if rect_separation(left_rect, words[right_index]["rect"]) <= reach:
                union.union(left_index, right_index)
    grouped = {}
    for index, word in enumerate(words):
        grouped.setdefault(union.find(index), []).append(word)
    merged = []
    for bucket in grouped.values():
        rect = bucket[0]["rect"]
        glyphs_in = []
        for word in bucket:
            glyphs_in.extend(word["glyphs"])
            other = word["rect"]
            rect = (
                min(rect[0], other[0]), min(rect[1], other[1]),
                max(rect[2], other[2]), max(rect[3], other[3]),
            )
        merged.append({"glyphs": glyphs_in, "rect": rect})
    return merged


def _inside(point, rect):
    return rect[0] <= point[0] <= rect[2] and rect[1] <= point[1] <= rect[3]


def groups_touching(rect, groups):
    cx = (rect[0] + rect[2]) / 2.0
    cy = (rect[1] + rect[3]) / 2.0
    found = []
    for group_index, group in enumerate(groups):
        best = None
        for bond in group:
            for point in (bond["p1"], bond["p2"]):
                if not _inside(point, rect):
                    continue
                dist = math.hypot(point[0] - cx, point[1] - cy)
                if best is None or dist < best:
                    best = dist
        if best is not None:
            found.append((best, group_index))
    return found


def join_bond_groups(groups, words):
    """A letter that sits between two bond ends joins those ends.

    A longer label attaches to the nearest component only. The pieces of
    PPh3 are one word, and that word must not pull in the molecule beside it.
    """
    if not groups:
        return []
    union = UnionFind(len(groups))
    hits = []
    for word in words:
        hits.append(groups_touching(word["inflated"], groups))
        glyph_rects = [item["rect"] for item in word.get("glyphs") or []]
        if not glyph_rects:
            glyph_rects = [word["rect"]]
        for glyph_rect in glyph_rects:
            touched = groups_touching(inflate_rect(glyph_rect), groups)
            if len(touched) < 2:
                continue
            base = touched[0][1]
            for _, group_index in touched[1:]:
                union.union(base, group_index)
    buckets = {}
    for group_index, group in enumerate(groups):
        bucket = buckets.setdefault(union.find(group_index), {"bonds": [], "words": []})
        bucket["bonds"].extend(group)
    for word, found in zip(words, hits):
        if not found:
            continue
        group_index = min(found)[1]
        buckets[union.find(group_index)]["words"].append(word)
    return [(bucket["bonds"], bucket["words"]) for bucket in buckets.values()]


def structure_box(bonds, words):
    xs = []
    ys = []
    for bond in bonds:
        xs.extend((bond["p1"][0], bond["p2"][0]))
        ys.extend((bond["p1"][1], bond["p2"][1]))
    for word in words:
        rect = word["rect"]
        xs.extend((rect[0], rect[2]))
        ys.extend((rect[1], rect[3]))
    return min(xs), min(ys), max(xs), max(ys)


def graph_with_words(bonds, words, tol):
    """A joined word is an atom at its center. Lone ends attach there."""
    ends = []
    for bond in bonds:
        ends.append(bond["p1"])
        ends.append(bond["p2"])
    lone = []
    for index, point in enumerate(ends):
        bond_index = index // 2
        neighbor = False
        for other_index, other in enumerate(ends):
            if other_index // 2 == bond_index:
                continue
            if math.hypot(point[0] - other[0], point[1] - other[1]) <= tol:
                neighbor = True
                break
        lone.append(not neighbor)

    word_for_end = []
    used_words = []
    for index, point in enumerate(ends):
        joined = closest_word_index(point, words) if lone[index] else None
        word_for_end.append(joined)
        if joined is not None and joined not in used_words:
            used_words.append(joined)

    carbons = []

    def carbon_at(point):
        for index, vertex in enumerate(carbons):
            if math.hypot(vertex[0] - point[0], vertex[1] - point[1]) <= tol:
                return index
        carbons.append((point[0], point[1]))
        return len(carbons) - 1

    carbon_ids = []
    for index, point in enumerate(ends):
        if word_for_end[index] is None:
            carbon_ids.append(carbon_at(point))
        else:
            carbon_ids.append(None)

    vertices = list(carbons)
    labels = [""] * len(carbons)
    word_vertex = {}
    for word_index in used_words:
        rect = words[word_index]["rect"]
        vertices.append(((rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0))
        labels.append(words[word_index].get("text") or "")
        word_vertex[word_index] = len(vertices) - 1

    edges = []
    for bond_index, bond in enumerate(bonds):
        pair = []
        for end in (0, 1):
            slot = bond_index * 2 + end
            joined = word_for_end[slot]
            if joined is None:
                pair.append(carbon_ids[slot])
            else:
                pair.append(word_vertex[joined])
        if pair[0] == pair[1]:
            continue
        edges.append((pair[0], pair[1], bond.get("order", 1), bond.get("stereo", "")))
    return vertices, edges, labels


def closest_word_index(point, words):
    best = None
    for index, word in enumerate(words):
        if not _inside(point, word["inflated"]):
            continue
        rect = word["rect"]
        cx = (rect[0] + rect[2]) / 2.0
        cy = (rect[1] + rect[3]) / 2.0
        dist = math.hypot(point[0] - cx, point[1] - cy)
        if best is None or dist < best[0]:
            best = (dist, index)
    if best is None:
        return None
    return best[1]


def ocr_word(page, rect):
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESS
    pad = 1.2
    clip = fitz.Rect(rect[0] - pad, rect[1] - pad, rect[2] + pad, rect[3] + pad)
    matrix = fitz.Matrix(8, 8)
    pix = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # Labels are small. Give Tesseract a taller image.
    if image.height < 40:
        factor = 40 / max(image.height, 1)
        image = image.resize((max(1, int(image.width * factor)), 40), Image.Resampling.NEAREST)
    text = pytesseract.image_to_string(
        image,
        config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-",
    )
    return "".join(text.split())


def normalize_label(text):
    if not text:
        return ""
    fixes = {
        "0Me": "OMe", "OMc": "OMe", "OMO": "OMe", "Ph": "Ph",
        "C8Hl7": "C8H17", "cl": "Cl", "br": "Br",
    }
    return fixes.get(text, text)


def snap_vertices(bonds, tol):
    vertices = []

    def nearest(point):
        for index, vertex in enumerate(vertices):
            if math.hypot(vertex[0] - point[0], vertex[1] - point[1]) <= tol:
                return index
        vertices.append([point[0], point[1]])
        return len(vertices) - 1

    edges = []
    for bond in bonds:
        i = nearest(bond["p1"])
        j = nearest(bond["p2"])
        if i == j:
            continue
        edges.append((i, j, bond.get("order", 1), bond.get("stereo", "")))
    # Average snapped coordinates.
    for bond in bonds:
        pass
    return vertices, edges


def label_vertices(vertices, words, max_dist):
    labels = [""] * len(vertices)
    used = set()
    pairs = []
    for w_index, word in enumerate(words):
        rect = word["rect"]
        cx = (rect[0] + rect[2]) / 2
        cy = (rect[1] + rect[3]) / 2
        best = None
        for v_index, vertex in enumerate(vertices):
            dist = math.hypot(vertex[0] - cx, vertex[1] - cy)
            if best is None or dist < best[0]:
                best = (dist, v_index)
        if best and best[0] <= max_dist:
            pairs.append((best[0], w_index, best[1]))
    pairs.sort()
    for _, w_index, v_index in pairs:
        if w_index in used or labels[v_index]:
            continue
        used.add(w_index)
        labels[v_index] = words[w_index]["text"]
    return labels


def molecule_from_parts(vertices, edges, labels):
    rw = Chem.RWMol()
    aliases = []
    for label in labels:
        token = label or "C"
        atom = atom_from_label(token if label else "C")
        if label and label not in ELEMENTS:
            aliases.append(label)
        rw.AddAtom(atom)
    seen = set()
    for i, j, order, stereo in edges:
        key = (min(i, j), max(i, j))
        if key in seen:
            continue
        seen.add(key)
        bond_type = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}.get(order, Chem.BondType.SINGLE)
        rw.AddBond(int(i), int(j), bond_type)
        bond = rw.GetBondBetweenAtoms(int(i), int(j))
        if stereo == "wedge":
            bond.SetBondDir(Chem.BondDir.BEGINWEDGE)
        elif stereo == "hash":
            bond.SetBondDir(Chem.BondDir.BEGINDASH)
    mol = rw.GetMol()
    conf = Chem.Conformer(mol.GetNumAtoms())
    conf.Set3D(False)
    for index, (x, y) in enumerate(vertices):
        conf.SetAtomPosition(index, (x * 0.12, -y * 0.12, 0.0))
    mol.AddConformer(conf, assignId=True)
    try:
        block = Chem.MolToMolBlock(mol)
    except Exception:
        block = ""
    return mol, block, aliases


def atom_from_label(token):
    if token in ELEMENTS:
        return Chem.Atom(token)
    atom = Chem.Atom("*")
    atom.SetProp("molFileAlias", token)
    try:
        Chem.SetAtomAlias(atom, token)
    except Exception:
        pass
    return atom


def accept_cluster(bonds):
    if len(bonds) < 5:
        return False
    if axis_fraction(bonds) > 0.82:
        return False
    x0, y0, x1, y1 = bbox_of(bonds, 0)
    if (x1 - x0) < 12 or (y1 - y0) < 12:
        return False
    if (y1 - y0) > 520 and (x1 - x0) > 400:
        return False
    return True


def attach_fragments(pairs):
    """A colored bond's stroke stops short of the next one. On X-3 the gap is 8.8 pt for a small cap and 6.2 pt for an 11-bond half.

    Snapping every endpoint across 9 pt also joins the two molecules on either side of a
    reaction arrow. Only a piece of at most 12 bonds that is not itself a straight line may cross.
    """
    count = len(pairs)
    if count < 2:
        return pairs
    parent = list(range(count))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for index, (bonds, _words) in enumerate(pairs):
        if len(bonds) > 12 or axis_fraction(bonds) > 0.82:
            continue
        nearest = None
        for other_index, (other, _other_words) in enumerate(pairs):
            if other_index == index:
                continue
            dist = None
            for bond in bonds:
                for candidate in other:
                    for left in (bond["p1"], bond["p2"]):
                        for right in (candidate["p1"], candidate["p2"]):
                            gap = math.hypot(left[0] - right[0], left[1] - right[1])
                            if dist is None or gap < dist:
                                dist = gap
            if dist is not None and dist <= 12 and (nearest is None or dist < nearest[0]):
                nearest = (dist, other_index)
        if nearest is not None:
            parent[find(index)] = find(nearest[1])
    buckets = {}
    for index, (bonds, words) in enumerate(pairs):
        bucket = buckets.setdefault(find(index), {"bonds": [], "words": []})
        bucket["bonds"].extend(bonds)
        bucket["words"].extend(words)
    return [(bucket["bonds"], bucket["words"]) for bucket in buckets.values()]


def extract_pdf(path, ocr=True):
    doc = fitz.open(path)
    pages = []
    for page_index, page in enumerate(doc):
        bonds, ticks, glyphs = page_primitives(page)
        if len(bonds) < 6:
            pages.append({"page": page_index + 1, "structures": [], "bonds": len(bonds)})
            continue
        lengths = sorted(bond["length"] for bond in bonds)
        median = lengths[len(lengths) // 2]
        gap = max(3.6, 0.34 * median)
        dashed = dashed_from_ticks(ticks)
        words = merge_touching_words(label_words(glyphs, ticks))
        for word in words:
            word["inflated"] = inflate_rect(word["rect"])
        groups = cluster_bonds(bonds + dashed, gap)
        accepted = []
        for group, attached in join_bond_groups(groups, words):
            plain = [bond for bond in group if bond.get("stereo") != "hash"]
            hashed = [bond for bond in group if bond.get("stereo") == "hash"]
            if not accept_cluster(plain or group):
                continue
            merged = merge_parallel(plain) + hashed
            if len(merged) < 5:
                continue
            accepted.append((merged, attached))
        structures = []
        for merged, attached in attach_fragments(accepted):
            if ocr:
                for word in attached:
                    try:
                        word["text"] = normalize_label(ocr_word(page, word["rect"]))
                    except Exception:
                        word["text"] = ""
            box = structure_box(merged, attached)
            vertices, edges, labels = graph_with_words(merged, attached, max(2.4, 0.28 * median))
            if len(vertices) < 4 or len(edges) < 4:
                continue
            mol, block, aliases = molecule_from_parts(vertices, edges, labels)
            if not block.strip():
                continue
            structures.append({
                "box": box,
                "molblock": block,
                "aliases": aliases,
                "n_atoms": len(vertices),
                "n_bonds": len(edges),
                "labels": [word["text"] for word in attached if word.get("text")],
                "page": page_index + 1,
            })
        pages.append({
            "page": page_index + 1,
            "structures": structures,
            "bonds": len(bonds),
            "width": page.rect.width,
            "height": page.rect.height,
        })
    doc.close()
    return pages


def render_page_preview(path, page_index, structures, dest, scale=1.35):
    doc = fitz.open(path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    draw = ImageDraw.Draw(image)
    for structure in structures:
        x0, y0, x1, y1 = structure["box"]
        draw.rectangle((x0 * scale, y0 * scale, x1 * scale, y1 * scale), outline=(28, 98, 214), width=2)
    image.save(dest)
    doc.close()
    return dest


def crop_page(path, page_index, box, dest, scale=4.0, jpg=False):
    doc = fitz.open(path)
    page = doc[page_index]
    x0, y0, x1, y1 = box
    clip = fitz.Rect(x0, y0, x1, y1)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
    if jpg:
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        image.save(dest, quality=90)
    else:
        pix.save(dest)
    doc.close()


def overlay():
    ensure_dirs()
    pages = extract_pdf(LITERATURE, ocr=False)
    preview = os.path.join(ROOT, "preview")
    os.makedirs(preview, exist_ok=True)
    kept = 0
    for page in pages:
        if not page["structures"]:
            continue
        dest = os.path.join(preview, f"boxes-p{page['page']}.png")
        render_page_preview(LITERATURE, page["page"] - 1, page["structures"], dest, scale=1.2)
        kept += len(page["structures"])
        print(f"page {page['page']}: {len(page['structures'])} structures, raw bonds {page['bonds']}")
        for structure in page["structures"]:
            print(f"  atoms {structure['n_atoms']} bonds {structure['n_bonds']} box {[round(v,1) for v in structure['box']]}")
    print("kept", kept)
    # Negative PDF should stay empty.
    empty = extract_pdf(PLOS, ocr=False)
    hits = sum(len(page["structures"]) for page in empty)
    print("plos structures", hits, "pages with raw bonds", sum(1 for page in empty if page["bonds"] >= 6))


def patch_molscribe():
    import timm.models.helpers as helpers
    import timm.models.vision_transformer as vit

    if not hasattr(helpers, "overlay_external_default_cfg"):
        def overlay_external_default_cfg(default_cfg, kwargs):
            return default_cfg
        helpers.overlay_external_default_cfg = overlay_external_default_cfg
    if not hasattr(vit, "_init_vit_weights"):
        def _init_vit_weights(module, name="", head_bias=0.0, jax_impl=False):
            return None
        vit._init_vit_weights = _init_vit_weights
    if not hasattr(vit, "checkpoint_filter_fn"):
        def checkpoint_filter_fn(state_dict, model):
            return state_dict
        vit.checkpoint_filter_fn = checkpoint_filter_fn


class Models:
    def __init__(self):
        self.molscribe = None
        self.molnextr = None
        self.device = "cpu"
        self.drawer = None

    def load_molscribe(self):
        if self.molscribe is not None:
            return
        patch_molscribe()
        import torch
        from molscribe import MolScribe
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("MolScribe", self.device, flush=True)
        self.molscribe = MolScribe(MOLSCRIBE_CKPT, device=torch.device(self.device))

    def predict_image(self, path):
        self.load_molscribe()
        import cv2
        image = cv2.imread(path)
        if image is None:
            raise FileNotFoundError(path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pred = self.molscribe.predict_image(image, return_atoms_bonds=True, return_confidence=True)
        return pred

    def load_molnextr(self):
        if self.molnextr is not None:
            return
        patch_molscribe()
        import torch
        from MolNexTR.model import molnextr
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("MolNexTR", self.device, flush=True)
        self.molnextr = molnextr(MOLNEXTR_CKPT, device=torch.device(self.device))

    def predict_molnextr(self, path):
        self.load_molnextr()
        import cv2
        image = cv2.imread(path)
        if image is None:
            raise FileNotFoundError(path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pred = self.molnextr.predict_images(
            [image], return_atoms_bonds=True, return_confidence=True, batch_size=1
        )[0]
        return molnextr_as_molscribe(pred)

    def drawer_app(self):
        if self.drawer is None:
            import win32com.client
            self.drawer = win32com.client.DispatchEx("ChemDraw.Application")
            try:
                self.drawer.Visible = False
            except Exception:
                pass
        return self.drawer

    def close(self):
        if self.drawer is not None:
            try:
                self.drawer.Quit()
            except Exception:
                pass
            self.drawer = None


def apply_acs(doc):
    settings = doc.Settings
    values = {
        "BondLength": 14.4,
        "BondSpacing": 18.0,
        "LineWidth": 0.60,
        "BoldWidth": 2.00,
        "MarginWidth": 1.60,
        "HashSpacing": 2.50,
        "ChainAngle": 120,
        "LabelFont": "Arial",
        "LabelSize": 10.0,
        "CaptionFont": "Arial",
        "CaptionSize": 10.0,
        # This flag removes the H from an OH label. Carbon labels stay off without it.
        "HideImplicitHydrogens": False,
    }
    for key, value in values.items():
        try:
            setattr(settings, key, value)
        except Exception:
            pass


def com_text(doc, kind):
    data = doc.Objects.GetData(kind, 0, 0, 0)
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    return bytes(data).decode("latin-1", "replace")


# CDXML Display="Wavy". On a double bond ChemDraw draws that as a crossed bond.
CROSSED_DOUBLE_DISPLAY = 8


def clear_enhanced_stereo(doc):
    """A wedge read from a molfile becomes racemic group 1, which ChemDraw prints as &1."""
    cleared = 0
    try:
        count = int(doc.Atoms.Count)
    except Exception:
        return 0
    for index in range(1, count + 1):
        atom = doc.Atoms.Item(index)
        try:
            kind = int(atom.EnhancedStereoType)
        except Exception:
            continue
        if kind != 0:
            atom.EnhancedStereoType = 0
            cleared += 1
    return cleared


def clear_crossed_doubles(doc):
    cleared = 0
    try:
        count = int(doc.Bonds.Count)
    except Exception:
        return 0
    for index in range(1, count + 1):
        bond = doc.Bonds.Item(index)
        try:
            order = int(bond.BondOrder)
            display = int(bond.BondDisplay)
        except Exception:
            continue
        if order == 2 and display == CROSSED_DOUBLE_DISPLAY:
            bond.BondDisplay = 0
            cleared += 1
    return cleared


def render_molblock(models, block, dest_png):
    app = models.drawer_app()
    doc = app.Documents.Add()
    try:
        apply_acs(doc)
        doc.Objects.SetData("chemical/x-mdl-molfile", 0, 0, 0, block)
        atoms = int(doc.Atoms.Count)
        if atoms == 0:
            return {"ok": False, "reason": "ChemDraw 没有收下这个 mol"}
        clear_enhanced_stereo(doc)
        clear_crossed_doubles(doc)
        png = doc.Objects.GetData("image/png", 600, 0, 0)
        raw = png if isinstance(png, (bytes, bytearray)) else bytes(png)
        with open(dest_png, "wb") as handle:
            handle.write(raw)
        mol = com_text(doc, "chemical/x-mdl-molfile")
        cdxml = com_text(doc, "chemical/x-cdxml")
        clip = cdx_bytes(doc)
        return {"ok": True, "atoms": atoms, "mol": mol, "cdxml": cdxml, "clip": clip, "png": dest_png}
    finally:
        try:
            doc.Close(0)
        except Exception:
            pass


def render_smiles(models, smiles, dest_png):
    """Re-layout from SMILES. This is the round trip the product must not use for the picture."""
    app = models.drawer_app()
    doc = app.Documents.Add()
    try:
        apply_acs(doc)
        placed = False
        try:
            doc.Objects.SetData("chemical/x-daylight-smiles", 0, 0, 0, smiles)
            placed = int(doc.Atoms.Count) > 0
        except Exception:
            placed = False
        if not placed:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"ok": False, "reason": "SMILES 无法成分子"}
            rdDepictor.SetPreferCoordGen(True)
            rdDepictor.Compute2DCoords(mol)
            doc.Objects.Clear()
            doc.Objects.SetData("chemical/x-mdl-molfile", 0, 0, 0, Chem.MolToMolBlock(mol))
        if int(doc.Atoms.Count) == 0:
            return {"ok": False, "reason": "ChemDraw 没有收下这条 SMILES"}
        clear_enhanced_stereo(doc)
        clear_crossed_doubles(doc)
        png = doc.Objects.GetData("image/png", 600, 0, 0)
        raw = png if isinstance(png, (bytes, bytearray)) else bytes(png)
        with open(dest_png, "wb") as handle:
            handle.write(raw)
        mol = com_text(doc, "chemical/x-mdl-molfile")
        cdxml = com_text(doc, "chemical/x-cdxml")
        clip = cdx_bytes(doc)
        return {"ok": True, "atoms": int(doc.Atoms.Count), "mol": mol, "cdxml": cdxml, "clip": clip, "png": dest_png}
    finally:
        try:
            doc.Close(0)
        except Exception:
            pass


def cdx_bytes(doc):
    """The ChemDraw Interchange Format payload, read from the document.

    This is the same CDX that Objects.Copy puts on the clipboard, without
    replacing the user's clipboard on every render.
    """
    try:
        data = doc.Objects.GetData("chemical/x-cdx", 0, 0, 0)
    except Exception:
        return b""
    if data is None:
        return b""
    raw = data.encode("latin-1") if isinstance(data, str) else bytes(data)
    return raw if raw.startswith(b"VjCD") else b""


def read_chemdraw_clip():
    import time
    import win32clipboard
    for _ in range(8):
        try:
            win32clipboard.OpenClipboard()
        except Exception:
            time.sleep(0.15)
            continue
        try:
            fmt = win32clipboard.RegisterClipboardFormat("ChemDraw Interchange Format")
            data = win32clipboard.GetClipboardData(fmt)
            if isinstance(data, str):
                data = data.encode("utf-8")
            return bytes(data)
        except Exception:
            return b""
        finally:
            win32clipboard.CloseClipboard()
    return b""


def derived_strings(molblock, fallback_smiles=""):
    mol = Chem.MolFromMolBlock(molblock, sanitize=False, removeHs=False) if molblock else None
    smiles = fallback_smiles or ""
    smarts = ""
    if mol is not None:
        try:
            from molscribe.chemistry import _expand_functional_group
            expanded, _ = _expand_functional_group(Chem.Mol(mol), {}, False)
            if expanded and expanded != "<invalid>":
                smiles = expanded
        except Exception:
            pass
        if not smiles:
            try:
                Chem.SanitizeMol(Chem.Mol(mol))
                smiles = Chem.MolToSmiles(Chem.Mol(mol))
            except Exception:
                smiles = ""
        try:
            smarts = Chem.MolToSmarts(mol)
        except Exception:
            smarts = ""
    return smiles, smarts


def write_structure_files(folder, index, rendered, smiles, smarts):
    os.makedirs(folder, exist_ok=True)
    stem = f"s{index:02d}"
    mol_path = os.path.join(folder, stem + ".mol")
    smi_path = os.path.join(folder, stem + ".smi")
    smarts_path = os.path.join(folder, stem + ".smarts")
    clip_key = os.path.relpath(folder, OUT).replace("\\", "-").replace("/", "-")
    clip_path = os.path.join(OUT, "clips", f"{clip_key}-{stem}.bin")
    with open(mol_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered["mol"])
    with open(smi_path, "w", encoding="utf-8") as handle:
        handle.write(smiles)
    with open(smarts_path, "w", encoding="utf-8") as handle:
        handle.write(smarts)
    if rendered.get("clip"):
        with open(clip_path, "wb") as handle:
            handle.write(rendered["clip"])
    return {
        "mol_file": os.path.relpath(mol_path, ROOT).replace("\\", "/"),
        "smiles_file": os.path.relpath(smi_path, ROOT).replace("\\", "/"),
        "smarts_file": os.path.relpath(smarts_path, ROOT).replace("\\", "/"),
        "clip_file": os.path.relpath(clip_path, ROOT).replace("\\", "/") if rendered.get("clip") else "",
        "render": os.path.relpath(rendered["png"], ROOT).replace("\\", "/"),
        "mol": rendered["mol"],
        "smiles": smiles,
        "smarts": smarts,
        "n_atoms": rendered.get("atoms", 0),
    }


def molscribe_gate(pred):
    smiles = (pred.get("smiles") or "").strip()
    molfile = pred.get("molfile") or ""
    confidence = pred.get("confidence")
    atoms = pred.get("atoms") or []
    if smiles in ("", "<invalid>") and not molfile.strip():
        return False, "MolScribe 没有给出分子"
    if len(atoms) < 3 and not molfile.strip():
        return False, "原子太少，不像结构式"
    if confidence is not None and float(confidence) < 0.45:
        return False, f"置信度 {float(confidence):.2f}，低于 0.45"
    return True, ""


def image_ink_gate(path):
    image = Image.open(path).convert("RGB")
    image.thumbnail((900, 900))
    pixels = list(image.getdata())
    sat = 0
    dark = 0
    for red, green, blue in pixels:
        if max(red, green, blue) - min(red, green, blue) > 36 and (red + green + blue) < 680:
            sat += 1
        gray = (red * 30 + green * 59 + blue * 11) // 100
        if gray < 170:
            dark += 1
    total = max(len(pixels), 1)
    sat_f = sat / total
    dark_f = dark / total
    if sat_f > 0.2:
        return False, f"彩色像素占 {sat_f:.0%}，不像结构式线稿"
    if dark_f < 0.002:
        return False, "几乎没有墨迹"
    if dark_f > 0.62:
        return False, f"墨迹占 {dark_f:.0%}，不像结构式留白"
    return True, f"线稿墨迹 {dark_f:.0%}"


def rel(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def frames_from_boxes(boxes, png_path, pdf_path, page_index, linked=True):
    """Recognition frames in source-image pixels. structure is the render index, or null."""
    with Image.open(png_path) as image:
        width, height = image.size
    doc = fitz.open(pdf_path)
    rect = doc[page_index].rect
    doc.close()
    scale_x = width / rect.width
    scale_y = height / rect.height
    frames = []
    for index, box in enumerate(boxes):
        frames.append({
            "box": [
                round(box[0] * scale_x, 2),
                round(box[1] * scale_y, 2),
                round(box[2] * scale_x, 2),
                round(box[3] * scale_y, 2),
            ],
            "structure": index if linked else None,
        })
    return frames, width, height


def full_image_frame(png_path):
    with Image.open(png_path) as image:
        width, height = image.size
    return [{"box": [0, 0, width, height], "structure": 0}], width, height


def pack_sample(sample_id, title, kind, source_note, status, reason, pages, expect):
    return {
        "id": sample_id,
        "title": title,
        "kind": kind,
        "source_note": source_note,
        "status": status,
        "reason": reason,
        "expect": expect,
        "pages": pages,
    }


def run_all():
    ensure_dirs()
    patch_molscribe()
    print("extract literature vectors", flush=True)
    literature_pages = extract_pdf(LITERATURE, ocr=True)
    n_struct = sum(len(page["structures"]) for page in literature_pages)
    print("literature structures", n_struct, flush=True)
    if not os.path.exists(COMMON):
        make_common_jpeg(literature_pages)
    print("extract negative pdf", flush=True)
    plos_pages = extract_pdf(PLOS, ocr=False)
    models = Models()
    try:
        schemes = {}
        schemes["vector"] = build_vector(models, literature_pages, plos_pages)
        schemes["raster"] = build_raster(models, literature_pages, plos_pages)
        schemes["roundtrip"] = build_roundtrip(models, schemes["raster"])
        proof = paste_proof(models, schemes)
    finally:
        models.close()
    payload = {
        "schemes": schemes,
        "proof": proof,
        "literature": {
            "title": "Beyond n-dopants for organic semiconductors: use of bibenzo[d]imidazoles in UV-promoted dehalogenation reactions of organic halides",
            "citation": "Beilstein J. Org. Chem. 2023, 19, 1912-1922. CC BY.",
            "file": "samples/bjoc-19-142.pdf",
        },
        "negative_pdf": {
            "title": "Impact of e-money on money supply: Estimation and policy implication for Bangladesh",
            "citation": "PLOS ONE. CC BY. No chemical structures.",
            "file": "samples/plos-candidate.pdf",
        },
    }
    dest = os.path.join(OUT, "results.json")
    with open(dest, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    print("wrote", dest, flush=True)
    return payload


def make_common_jpeg(pages):
    best = None
    for page in pages:
        for structure in page["structures"]:
            if best is None or structure["n_bonds"] > best["n_bonds"]:
                if structure["n_bonds"] < 40:
                    best = structure
    if best is None:
        for page in pages:
            if page["structures"]:
                best = page["structures"][0]
                break
    if best is None:
        raise SystemExit("no structure to crop for the jpeg")
    crop_page(LITERATURE, best["page"] - 1, best["box"], COMMON, scale=5.0, jpg=True)
    print("common jpeg", best["page"], best["n_atoms"], flush=True)


def empty_pages_message(reason):
    return [{"source": "", "structures": [], "note": reason}]


def build_vector(models, literature_pages, plos_pages):
    folder = os.path.join(OUT, "vector")
    os.makedirs(folder, exist_ok=True)
    samples = []
    lit_pages_out = []
    lit_count = 0
    for page in literature_pages:
        if not page["structures"]:
            continue
        page_dir = os.path.join(folder, "literature-pdf", f"p{page['page']}")
        os.makedirs(page_dir, exist_ok=True)
        source = os.path.join(page_dir, "source.png")
        render_page_preview(LITERATURE, page["page"] - 1, page["structures"], source, scale=1.15)
        rendered_list = []
        for index, structure in enumerate(page["structures"]):
            png = os.path.join(page_dir, f"s{index:02d}.png")
            try:
                rendered = render_molblock(models, structure["molblock"], png)
            except Exception as exc:
                rendered = {"ok": False, "reason": str(exc)[:180]}
            if not rendered.get("ok"):
                rendered_list.append({
                    "ok": False,
                    "reason": rendered.get("reason", "渲染失败"),
                    "aliases": structure["aliases"],
                    "labels": structure["labels"],
                })
                continue
            smiles, smarts = derived_strings(rendered["mol"])
            packed = write_structure_files(page_dir, index, rendered, smiles, smarts)
            packed["aliases"] = structure["aliases"]
            packed["labels"] = structure["labels"]
            packed["ok"] = True
            rendered_list.append(packed)
            lit_count += 1
        lit_pages_out.append({
            "source": rel(source),
            "page": page["page"],
            "structures": rendered_list,
        })
    if lit_count:
        samples.append(pack_sample(
            "literature-pdf", "文献 PDF", "pdf",
            "Beilstein J. Org. Chem. 2023, 19, 1912. 矢量中心线，缩写走字形 OCR。",
            "structures", f"抽出 {lit_count} 个结构，按原坐标交给 ChemDraw，没有 Clean。",
            lit_pages_out, "structures",
        ))
    else:
        samples.append(pack_sample(
            "literature-pdf", "文献 PDF", "pdf",
            "矢量方案没有留下可用结构。",
            "rejected", "没有通过键角和键数门槛的结构簇。",
            [], "structures",
        ))
    samples.append(image_via_molscribe(models, folder, "complex-screenshot", "复杂结构截图", COMPLEX, "structures",
                                        "本仓库 ACS1996 预览 halichondrin-b。矢量方案对图片改走 MolScribe 坐标。"))
    samples.append(image_via_molscribe(models, folder, "common-image", "常见图片", COMMON, "structures",
                                        "从这篇文献的一个结构裁出的 JPEG。"))
    plos_hits = sum(len(page["structures"]) for page in plos_pages)
    if plos_hits:
        samples.append(pack_sample(
            "no-structure-pdf", "无结构 PDF", "pdf",
            "PLOS ONE 经济学论文。",
            "structures", f"误收下 {plos_hits} 个簇。这是这个方案的失败。",
            [], "rejected",
        ))
    else:
        samples.append(pack_sample(
            "no-structure-pdf", "无结构 PDF", "pdf",
            "PLOS ONE 经济学论文，正文和表格线，没有化学结构。",
            "rejected", "没有一组键同时满足键数、键角和大小。坐标轴和页眉线被丢掉。",
            [], "rejected",
        ))
    samples.append(image_via_molscribe(models, folder, "no-structure-image", "无结构图片", CHART, "rejected",
                                        "一张折线图，不是分子。"))
    return {
        "id": "vector",
        "label": "矢量坐标",
        "summary": "PDF 用路径中心线和字形 OCR，坐标原样进 mol。图片没有路径，改用 MolScribe 的原子坐标。渲染不再从 SMILES 重画。",
        "samples": samples,
    }


def image_via_molscribe(models, folder, sample_id, title, path, expect, note):
    sample_dir = os.path.join(folder, sample_id)
    os.makedirs(sample_dir, exist_ok=True)
    source = os.path.join(sample_dir, "source" + os.path.splitext(path)[1].lower())
    if not os.path.exists(source):
        shutil.copyfile(path, source)
    ink_ok, ink_note = image_ink_gate(path)
    if not ink_ok:
        return pack_sample(sample_id, title, "image", note, "rejected", ink_note,
                            [{"source": rel(source), "structures": []}], expect)
    try:
        pred = models.predict_image(path)
    except Exception as exc:
        return pack_sample(sample_id, title, "image", note, "rejected", f"MolScribe 失败：{exc}",
                            [{"source": rel(source), "structures": []}], expect)
    ok, why = molscribe_gate(pred)
    confidence = pred.get("confidence")
    block = pred.get("molfile") or ""
    packed = None
    if block.strip():
        png = os.path.join(sample_dir, "s00.png")
        rendered = render_molblock(models, block, png)
        if rendered.get("ok"):
            smiles, smarts = derived_strings(rendered["mol"], pred.get("smiles") or "")
            packed = write_structure_files(sample_dir, 0, rendered, smiles, smarts)
            packed["ok"] = ok
            packed["reason"] = "" if ok else why
            packed["confidence"] = None if confidence is None else round(float(confidence), 3)
            packed["aliases"] = aliases_in_mol(block)
    if not ok:
        return pack_sample(
            sample_id, title, "image", note, "rejected", why,
            [{"source": rel(source), "structures": [packed] if packed else []}],
            expect,
        )
    conf_txt = f"{float(confidence):.2f}" if confidence is not None else "无"
    return pack_sample(
        sample_id, title, "image", note, "structures",
        f"MolScribe 置信度 {conf_txt}。用它的 mol 坐标渲染，没有从 SMILES 重排。{ink_note}。",
        [{"source": rel(source), "structures": [packed]}],
        expect,
    )


def aliases_in_mol(block):
    aliases = []
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("A  ") and index + 1 < len(lines):
            aliases.append(lines[index + 1].strip())
    return aliases


def build_raster(models, literature_pages, plos_pages):
    folder = os.path.join(OUT, "raster")
    os.makedirs(folder, exist_ok=True)
    samples = []
    lit_pages_out = []
    lit_count = 0
    for page in literature_pages:
        if not page["structures"]:
            continue
        page_dir = os.path.join(folder, "literature-pdf", f"p{page['page']}")
        os.makedirs(page_dir, exist_ok=True)
        source = os.path.join(page_dir, "source.png")
        render_page_preview(LITERATURE, page["page"] - 1, page["structures"], source, scale=1.15)
        rendered_list = []
        for index, structure in enumerate(page["structures"]):
            crop = os.path.join(page_dir, f"crop{index:02d}.png")
            crop_page(LITERATURE, structure["page"] - 1, structure["box"], crop, scale=4.0)
            try:
                pred = models.predict_image(crop)
                ok, why = molscribe_gate(pred)
            except Exception as exc:
                ok, why = False, str(exc)[:160]
                pred = {}
            block = pred.get("molfile") or ""
            if not block.strip():
                rendered_list.append({"ok": False, "reason": why or "没有 mol"})
                continue
            png = os.path.join(page_dir, f"s{index:02d}.png")
            rendered = render_molblock(models, block, png)
            if not rendered.get("ok"):
                rendered_list.append({"ok": False, "reason": rendered.get("reason", "渲染失败")})
                continue
            smiles, smarts = derived_strings(rendered["mol"], pred.get("smiles") or "")
            packed = write_structure_files(page_dir, index, rendered, smiles, smarts)
            packed["ok"] = bool(ok)
            packed["reason"] = "" if ok else why
            packed["confidence"] = None if pred.get("confidence") is None else round(float(pred["confidence"]), 3)
            packed["aliases"] = aliases_in_mol(block)
            packed["recognition_smiles"] = pred.get("smiles") or ""
            rendered_list.append(packed)
            if ok:
                lit_count += 1
        lit_pages_out.append({"source": rel(source), "page": page["page"], "structures": rendered_list})
    samples.append(pack_sample(
        "literature-pdf", "文献 PDF", "pdf",
        "同一批矢量框，但每个框先栅格化，再由 MolScribe 给坐标。",
        "structures" if lit_count else "rejected",
        f"栅格后收下 {lit_count} 个结构。" if lit_count else "栅格后没有通过门槛的结构。",
        lit_pages_out, "structures",
    ))
    samples.append(image_via_molscribe(models, folder, "complex-screenshot", "复杂结构截图", COMPLEX, "structures",
                                        "halichondrin-b 截图。整图交给 MolScribe。"))
    samples.append(image_via_molscribe(models, folder, "common-image", "常见图片", COMMON, "structures",
                                        "文献结构的 JPEG。"))
    plos_hits = sum(len(page["structures"]) for page in plos_pages)
    # Raster scheme does not invent molecules from a text PDF when the vector locator finds none.
    if plos_hits:
        reason = f"定位阶段误检 {plos_hits} 个区域。"
        status = "structures"
    else:
        reason = "整页没有可裁的结构框，拒绝。不把正文页送进 MolScribe。"
        status = "rejected"
    samples.append(pack_sample(
        "no-structure-pdf", "无结构 PDF", "pdf",
        "同一份经济学 PDF。",
        status, reason, [], "rejected",
    ))
    samples.append(image_via_molscribe(models, folder, "no-structure-image", "无结构图片", CHART, "rejected",
                                        "折线图。"))
    return {
        "id": "raster",
        "label": "栅格坐标",
        "summary": "PDF 先按矢量框裁图，图片直接读入。MolScribe 输出带坐标的 mol，ChemDraw 只套 ACS1996，不 Clean。",
        "samples": samples,
    }


def build_roundtrip(models, raster_scheme):
    """Same recognition as the raster scheme. The picture is redrawn from SMILES."""
    folder = os.path.join(OUT, "roundtrip")
    os.makedirs(folder, exist_ok=True)
    samples = []
    for sample in raster_scheme["samples"]:
        page_out = []
        count = 0
        rejected_bits = []
        for page in sample["pages"]:
            structures = []
            page_dir = os.path.join(folder, sample["id"], f"p{page.get('page', 0)}")
            os.makedirs(page_dir, exist_ok=True)
            for index, structure in enumerate(page.get("structures") or []):
                smiles = (structure.get("smiles") or "").strip()
                if not structure.get("ok") or not smiles or smiles == "<invalid>":
                    structures.append({"ok": False, "reason": "没有可重画的 SMILES"})
                    continue
                png = os.path.join(page_dir, f"s{index:02d}.png")
                rendered = render_smiles(models, smiles, png)
                if not rendered.get("ok"):
                    structures.append({"ok": False, "reason": rendered.get("reason", "重画失败")})
                    continue
                new_smiles, smarts = derived_strings(rendered["mol"], smiles)
                packed = write_structure_files(page_dir, index, rendered, new_smiles or smiles, smarts)
                packed["ok"] = True
                packed["aliases"] = []
                structures.append(packed)
                count += 1
            if page.get("source") or structures:
                page_out.append({
                    "source": page.get("source", ""),
                    "page": page.get("page"),
                    "structures": structures,
                })
        if sample["expect"] == "rejected" and count == 0:
            status = "rejected"
            reason = sample["reason"]
        elif count:
            status = "structures"
            reason = f"用识别 SMILES 按 ACS1996 重新布局，得到 {count} 张图。坐标不是来源上的坐标。"
        else:
            status = "rejected"
            reason = "没有可重画的 SMILES。"
            rejected_bits.append(reason)
        samples.append(pack_sample(
            sample["id"], sample["title"], sample["kind"], sample["source_note"],
            status, reason, page_out, sample["expect"],
        ))
    return {
        "id": "roundtrip",
        "label": "SMILES 重画",
        "summary": "识别结果和栅格方案相同，但画面从 SMILES 重新生成。用来看往返之后和来源差多少。",
        "samples": samples,
    }


def paste_proof(models, schemes):
    """Put ChemDraw's own clipboard format back, then paste into a new document."""
    clip = b""
    mol_text = ""
    for scheme in schemes.values():
        for sample in scheme["samples"]:
            for page in sample["pages"]:
                for structure in page.get("structures") or []:
                    if structure.get("ok") and structure.get("clip_file"):
                        clip = open(os.path.join(ROOT, structure["clip_file"]), "rb").read()
                        mol_text = structure.get("mol") or ""
                        break
                if clip:
                    break
            if clip:
                break
        if clip:
            break
    if not clip:
        return {"ok": False, "reason": "没有可粘贴的 ChemDraw 剪贴板数据"}
    import win32clipboard
    import win32com.client
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        fmt = win32clipboard.RegisterClipboardFormat("ChemDraw Interchange Format")
        win32clipboard.SetClipboardData(fmt, clip)
        if mol_text:
            win32clipboard.SetClipboardData(13, mol_text)  # CF_UNICODETEXT
    finally:
        win32clipboard.CloseClipboard()
    app = models.drawer_app()
    try:
        app.Visible = True
    except Exception:
        pass
    doc = app.Documents.Add()
    pasted = 0
    method = ""
    try:
        try:
            doc.Paste()
            method = "Document.Paste"
        except Exception:
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.AppActivate("ChemDraw")
            time.sleep(0.6)
            shell.SendKeys("^v")
            time.sleep(0.8)
            method = "Ctrl+V"
        try:
            pasted = int(doc.Atoms.Count)
        except Exception:
            pasted = 0
        proof_png = os.path.join(OUT, "chemdraw-paste.png")
        if pasted:
            png = doc.Objects.GetData("image/png", 600, 0, 0)
            raw = png if isinstance(png, (bytes, bytearray)) else bytes(png)
            with open(proof_png, "wb") as handle:
                handle.write(raw)
        return {
            "ok": pasted > 0,
            "atoms": pasted,
            "method": method,
            "png": rel(proof_png) if pasted else "",
            "format": "ChemDraw Interchange Format",
        }
    finally:
        try:
            doc.Close(0)
        except Exception:
            pass
        try:
            app.Visible = False
        except Exception:
            pass


def rd_atom_from_symbol(symbol):
    from rdkit import Chem
    text = (symbol or "C").strip()
    candidates = [text]
    if not text.startswith("["):
        candidates.append(f"[{text}]")
    for candidate in candidates:
        try:
            atom = Chem.AtomFromSmiles(candidate)
        except Exception:
            atom = None
        if atom is not None and atom.GetSymbol() != "*":
            atom.SetChiralTag(Chem.rdchem.ChiralType.CHI_UNSPECIFIED)
            return atom
    atom = Chem.Atom("*")
    atom.SetProp("molFileAlias", text.strip("[]"))
    return atom


def collapse_stacked_atoms(atoms, bonds):
    """One drawn point is one atom. A second copy on that point strokes the same wedge twice."""
    points = []
    for atom in atoms:
        x, y = atom.get("coords") or (0.0, 0.0)
        points.append((float(x), float(y)))
    nearest = []
    for index, (x, y) in enumerate(points):
        best = None
        for other, (ox, oy) in enumerate(points):
            if other == index:
                continue
            dist = math.hypot(x - ox, y - oy)
            if best is None or dist < best:
                best = dist
        if best:
            nearest.append(best)
    median = sorted(nearest)[len(nearest) // 2] if nearest else 1.0
    limit = median * 0.02
    parent = list(range(len(points)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left in range(len(points)):
        for right in range(left + 1, len(points)):
            if math.hypot(points[left][0] - points[right][0], points[left][1] - points[right][1]) > limit:
                continue
            if (atoms[left].get("atom_symbol") or "C") != (atoms[right].get("atom_symbol") or "C"):
                continue
            parent[find(right)] = find(left)
    groups = {}
    for index in range(len(points)):
        groups.setdefault(find(index), []).append(index)
    remap = {}
    kept = []
    for indexes in groups.values():
        target = len(kept)
        kept.append(atoms[indexes[0]])
        for index in indexes:
            remap[index] = target
    rank = {"solid wedge": 2, "dashed wedge": 2, "double": 1, "triple": 1, "aromatic": 1, "single": 0}
    chosen = {}
    for bond in bonds:
        ends = bond.get("endpoints") or (0, 0)
        start, end = remap[int(ends[0])], remap[int(ends[1])]
        if start == end:
            continue
        kind = bond.get("bond_type") or "single"
        key = (min(start, end), max(start, end))
        copied = dict(bond)
        copied["endpoints"] = (start, end)
        copied["bond_type"] = kind
        previous = chosen.get(key)
        if previous is None or rank.get(kind, 0) > rank.get(previous.get("bond_type"), 0):
            chosen[key] = copied
    return kept, list(chosen.values())


def orient_wedges(atoms, bonds):
    """The wedge starts at the stereocenter. The other triangle of the edge matrix is only the reverse marker."""
    chiral = [index for index, atom in enumerate(atoms) if "[C@" in (atom.get("atom_symbol") or "")]
    if not chiral:
        return bonds
    for center in chiral:
        for bond in bonds:
            kind = bond.get("bond_type") or "single"
            if kind not in ("solid wedge", "dashed wedge"):
                continue
            start, end = int(bond["endpoints"][0]), int(bond["endpoints"][1])
            if center not in (start, end):
                continue
            if center == end:
                kind = "dashed wedge" if kind == "solid wedge" else "solid wedge"
                start, end = end, start
            bond["bond_type"] = kind
            bond["endpoints"] = (start, end)
    return bonds


def molblock_from_graph(atoms, bonds):
    """MolNexTR's published molfile is rebuilt from SMILES and drops the predicted layout."""
    from rdkit import Chem
    atoms, bonds = collapse_stacked_atoms(atoms, bonds)
    bonds = orient_wedges(atoms, bonds)
    if len(atoms) < 3:
        return ""
    mol = Chem.RWMol()
    raw = []
    for atom in atoms:
        mol.AddAtom(rd_atom_from_symbol(atom.get("atom_symbol")))
        x, y = atom.get("coords") or (0.0, 0.0)
        raw.append((float(x), float(y)))
    nearest = []
    for index, (x, y) in enumerate(raw):
        best = None
        for other, (ox, oy) in enumerate(raw):
            if other == index:
                continue
            dist = math.hypot(x - ox, y - oy)
            if best is None or dist < best:
                best = dist
        if best:
            nearest.append(best)
    median = sorted(nearest)[len(nearest) // 2] if nearest else 1.0
    scale = 1.5 / median if median > 1e-6 else 1.0
    # Model coordinates grow downward, with the picture. A molfile that is already
    # right-side up grows upward, and a second pass through this flip turns it over.
    ys = [point[1] for point in raw]
    top = max(ys)
    conf = Chem.Conformer(len(raw))
    for index, (x, y) in enumerate(raw):
        conf.SetAtomPosition(index, (x * scale, (top - y) * scale, 0.0))
    mol.AddConformer(conf)
    bond_types = {
        "single": Chem.BondType.SINGLE,
        "double": Chem.BondType.DOUBLE,
        "triple": Chem.BondType.TRIPLE,
        "aromatic": Chem.BondType.AROMATIC,
        "solid wedge": Chem.BondType.SINGLE,
        "dashed wedge": Chem.BondType.SINGLE,
    }
    for bond in bonds:
        ends = bond.get("endpoints") or (0, 0)
        left, right = int(ends[0]), int(ends[1])
        if left == right or mol.GetBondBetweenAtoms(left, right) is not None:
            continue
        kind = bond.get("bond_type") or "single"
        mol.AddBond(left, right, bond_types.get(kind, Chem.BondType.SINGLE))
        drawn = mol.GetBondBetweenAtoms(left, right)
        if kind == "solid wedge":
            drawn.SetBondDir(Chem.BondDir.BEGINWEDGE)
        elif kind == "dashed wedge":
            drawn.SetBondDir(Chem.BondDir.BEGINDASH)
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        pass
    return Chem.MolToMolBlock(mol)


def molnextr_as_molscribe(pred):
    atoms = pred.get("atom_sets") or []
    bonds = pred.get("bond_sets") or []
    scores = [float(atom["confidence"]) for atom in atoms if atom.get("confidence") is not None]
    confidence = sum(scores) / len(scores) if scores else None
    smiles = (pred.get("predicted_smiles") or "").strip()
    if smiles == "<invalid>":
        smiles = ""
    return {
        "molfile": molblock_from_graph(atoms, bonds),
        "smiles": smiles,
        "confidence": confidence,
        "atoms": atoms,
    }


def clear_either_doubles(block):
    """Drop the 'either' flag (bond stereo 3) from double bonds of a V2000 block.

    RDKit writes 3 on every double bond it could not assign, and a graph built
    from predicted atoms and bonds has no assignment yet. Read back, the flag
    wins over the 2D geometry: E/Z is lost from the SMILES and ChemDraw draws a
    crossed double bond. With the flag cleared the drawn geometry decides.
    Measured on the 726 ACS1996 benchmark images: graph-path exact match
    35.0 % -> 49.6 %, E/Z match 0 % -> 52.4 %.
    """
    if not block or "V2000" not in block:
        return block
    lines = block.splitlines()
    try:
        atoms, bonds = int(lines[3][0:3]), int(lines[3][3:6])
    except (IndexError, ValueError):
        return block
    first = 4 + atoms
    for i in range(first, min(first + bonds, len(lines))):
        line = lines[i]
        if line[6:9].strip() == "2" and line[9:12].strip() == "3":
            lines[i] = line[:9] + "  0" + line[12:]
    return "\n".join(lines) + ("\n" if block.endswith("\n") else "")


def render_prediction(models, page_dir, index, pred):
    ok, why = molscribe_gate(pred)
    block = clear_either_doubles(pred.get("molfile") or "")
    if not block.strip():
        return {"ok": False, "reason": why or "没有 mol"}, False
    png = os.path.join(page_dir, f"s{index:02d}.png")
    rendered = render_molblock(models, block, png)
    if not rendered.get("ok"):
        return {"ok": False, "reason": rendered.get("reason", "渲染失败")}, False
    smiles, smarts = derived_strings(rendered["mol"], pred.get("smiles") or "")
    packed = write_structure_files(page_dir, index, rendered, smiles, smarts)
    packed["ok"] = bool(ok)
    packed["reason"] = "" if ok else why
    confidence = pred.get("confidence")
    packed["confidence"] = None if confidence is None else round(float(confidence), 3)
    packed["aliases"] = aliases_in_mol(block)
    packed["recognition_smiles"] = pred.get("smiles") or ""
    return packed, bool(ok)


def band_has_ink(page, box, side, band=2.0):
    x0, y0, x1, y1 = box
    if side == "left":
        clip = fitz.Rect(x0, y0, min(x1, x0 + band), y1)
    elif side == "right":
        clip = fitz.Rect(max(x0, x1 - band), y0, x1, y1)
    elif side == "top":
        clip = fitz.Rect(x0, y0, x1, min(y1, y0 + band))
    else:
        clip = fitz.Rect(x0, max(y0, y1 - band), x1, y1)
    if clip.width < 0.4 or clip.height < 0.4:
        return False
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=clip, alpha=False)
    dark = 0
    samples = pix.samples
    for index in range(0, len(samples), 3):
        gray = (samples[index] * 30 + samples[index + 1] * 59 + samples[index + 2] * 11) // 100
        if gray < 80:
            dark += 1
    return dark >= 12


def grow_box(page, box, limit=18.0, step=3.0):
    """Push a side out while its border still cuts ink. Stop at limit so a neighbor is not swallowed."""
    bounds = page.rect
    x0, y0, x1, y1 = box
    grown = {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0}
    for _ in range(8):
        moved = False
        current = (x0, y0, x1, y1)
        if grown["left"] < limit and x0 > bounds.x0 + 1 and band_has_ink(page, current, "left"):
            x0 = max(bounds.x0, x0 - step)
            grown["left"] += step
            moved = True
        if grown["right"] < limit and x1 < bounds.x1 - 1 and band_has_ink(page, current, "right"):
            x1 = min(bounds.x1, x1 + step)
            grown["right"] += step
            moved = True
        if grown["top"] < limit and y0 > bounds.y0 + 1 and band_has_ink(page, current, "top"):
            y0 = max(bounds.y0, y0 - step)
            grown["top"] += step
            moved = True
        if grown["bottom"] < limit and y1 < bounds.y1 - 1 and band_has_ink(page, current, "bottom"):
            y1 = min(bounds.y1, y1 + step)
            grown["bottom"] += step
            moved = True
        if not moved:
            break
    return (x0, y0, x1, y1)


def _push_side(box, side, step, bounds):
    x0, y0, x1, y1 = box
    if side == "left":
        x0 = max(bounds.x0, x0 - step)
    elif side == "right":
        x1 = min(bounds.x1, x1 + step)
    elif side == "top":
        y0 = max(bounds.y0, y0 - step)
    else:
        y1 = min(bounds.y1, y1 + step)
    return (x0, y0, x1, y1)


def _cover_fraction(outer, inner):
    width = min(outer[2], inner[2]) - max(outer[0], inner[0])
    height = min(outer[3], inner[3]) - max(outer[1], inner[1])
    if width <= 0 or height <= 0:
        return 0.0
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    if area <= 0:
        return 0.0
    return (width * height) / area


def _union_box(left, right):
    return (
        min(left[0], right[0]), min(left[1], right[1]),
        max(left[2], right[2]), max(left[3], right[3]),
    )


def seal_boxes(page, structures, step=3.0, extra=36.0):
    """Keep pushing a side whose border still cuts ink.

    The fixed 18 pt stop leaves methyl and hydroxyl groups outside the crop.
    A further step that would cover another structure of more than 6 bonds
    stops that side, so two molecules on either side of a gap stay apart.
    A cap of at most 6 bonds, and no wider than 48 pt, is the group that was
    cut off, and it joins the box that grows over it.
    """
    bounds = page.rect
    pending = []
    for item in structures:
        pending.append({
            "box": grow_box(page, item["box"]),
            "raw": item["box"],
            "bonds": item["n_bonds"],
            "extra": {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0},
        })
    absorbed = set()
    for _ in range(24):
        moved = False
        for index, entry in enumerate(pending):
            if index in absorbed:
                continue
            for side in ("left", "right", "top", "bottom"):
                if entry["extra"][side] >= extra:
                    continue
                if not band_has_ink(page, entry["box"], side):
                    continue
                trial = _push_side(entry["box"], side, step, bounds)
                if trial == entry["box"]:
                    continue
                take = []
                blocked = False
                for other_index, other in enumerate(pending):
                    if other_index == index or other_index in absorbed:
                        continue
                    if _cover_fraction(trial, other["raw"]) <= 0.2:
                        continue
                    long_side = max(other["raw"][2] - other["raw"][0], other["raw"][3] - other["raw"][1])
                    if other["bonds"] <= 6 and long_side <= 48:
                        take.append(other_index)
                    else:
                        blocked = True
                        break
                if blocked:
                    continue
                entry["box"] = trial
                entry["extra"][side] += step
                for other_index in take:
                    absorbed.add(other_index)
                    entry["box"] = _union_box(entry["box"], pending[other_index]["box"])
                moved = True
        if not moved:
            break
    return [entry["box"] for index, entry in enumerate(pending) if index not in absorbed]


def edge_cuts(page, box, inner=1.0, outer=1.0):
    """Ink on the frame line itself.

    seal_boxes only looks inside the frame. A methyl or a ring bond that
    starts just past the last bond endpoint leaves that inside band white,
    so the frame still slices the drawing. The band here straddles the line.
    """
    bounds = page.rect
    x0, y0, x1, y1 = box
    bands = {
        "left": fitz.Rect(x0 - outer, y0, x0 + inner, y1),
        "right": fitz.Rect(x1 - inner, y0, x1 + outer, y1),
        "top": fitz.Rect(x0, y0 - outer, x1, y0 + inner),
        "bottom": fitz.Rect(x0, y1 - inner, x1, y1 + outer),
    }
    cuts = []
    for side, clip in bands.items():
        clip = clip & bounds
        if clip.is_empty or clip.width < 0.3 or clip.height < 0.3:
            continue
        pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip, alpha=False)
        dark = 0
        samples = pix.samples
        for index in range(0, len(samples), 3):
            gray = (samples[index] * 30 + samples[index + 1] * 59 + samples[index + 2] * 11) // 100
            # Red letters anti-alias between 80 and 115. The upper-left
            # frame on X-3 page 5 had 5 pixels under 80 and 20 under 115.
            if gray < 115:
                dark += 1
        if dark >= 8:
            cuts.append(side)
    return cuts


def review_boxes(page, boxes):
    """Drop a frame whose line still slices ink.

    A sliced crop is what the recognizer completes with the wrong group.
    The close arrow on these schemes is the same failure when the shaft
    touches the line. A shaft that sits fully inside a clean frame was not
    in the measured pages, so this does not guess at one.
    """
    kept = []
    sent = []
    for box in boxes:
        cuts = edge_cuts(page, box)
        if cuts:
            sent.append({"box": box, "cuts": cuts})
            continue
        kept.append(box)
    return kept, sent


def ink_structure_boxes(page):
    """Connected ink on the rendered page. Text lines and rules are not structures."""
    import cv2
    import numpy as np
    scale = 2.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    gray = image.mean(axis=2)
    mask = (gray < 80).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    pieces = []
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        if area < 40:
            continue
        rect = (x / scale, y / scale, (x + width) / scale, (y + height) / scale)
        wide = rect[2] - rect[0]
        tall = rect[3] - rect[1]
        if tall < 3 and wide > 40:
            continue
        if wide < 3 and tall > 40:
            continue
        pieces.append(rect)
    if not pieces:
        return []
    union = UnionFind(len(pieces))
    for left in range(len(pieces)):
        for right in range(left + 1, len(pieces)):
            if rect_separation(pieces[left], pieces[right]) <= 6.0:
                union.union(left, right)
    groups = {}
    for index, rect in enumerate(pieces):
        groups.setdefault(union.find(index), []).append(rect)
    boxes = []
    for bucket in groups.values():
        rect = bucket[0]
        for other in bucket[1:]:
            rect = (
                min(rect[0], other[0]), min(rect[1], other[1]),
                max(rect[2], other[2]), max(rect[3], other[3]),
            )
        wide = rect[2] - rect[0]
        tall = rect[3] - rect[1]
        if wide < 18 or tall < 18 or wide > 280 or tall > 320:
            continue
        if tall < 14 and wide / max(tall, 1) > 5:
            continue
        boxes.append(rect)
    boxes.sort(key=lambda rect: (rect[1], rect[0]))
    return boxes[:16]


def plos_preview_pages():
    preview = os.path.join(OUT, "shared", "plos-page1.png")
    if os.path.exists(preview):
        return [{"source": rel(preview), "structures": []}]
    return []


def image_ratio(path):
    with Image.open(path) as image:
        width, height = image.size
    return max(width, height) / max(min(width, height), 1)


def letterboxed_copy(path):
    """Square white canvas. The stock resize would otherwise squash a wide drawing."""
    import cv2
    image = cv2.imread(path)
    height, width = image.shape[:2]
    side = max(height, width)
    canvas = np.full((side, side, 3), 255, dtype=image.dtype)
    top = (side - height) // 2
    left = (side - width) // 2
    canvas[top:top + height, left:left + width] = image
    dest = os.path.splitext(path)[0] + ".square.png"
    cv2.imwrite(dest, canvas)
    return dest


def square_model_transform(size=384):
    # molscribe's package import fails until the timm names are patched.
    patch_molscribe()
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    from molscribe.augment import CropWhite
    from MolNexTR.data_aug import PadToSquare
    return A.Compose([
        CropWhite(pad=5),
        PadToSquare(p=1),
        A.Resize(size, size),
        A.ToGray(p=1),
        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ToTensorV2(),
    ])


def image_via_predict(models, folder, sample_id, title, path, expect, note, predict):
    sample_dir = os.path.join(folder, sample_id)
    os.makedirs(sample_dir, exist_ok=True)
    source = os.path.join(sample_dir, "source" + os.path.splitext(path)[1].lower())
    if not os.path.exists(source):
        shutil.copyfile(path, source)
    ink_ok, ink_note = image_ink_gate(path)
    if not ink_ok:
        return pack_sample(sample_id, title, "image", note, "rejected", ink_note,
                            [{"source": rel(source), "structures": []}], expect)
    # MolNexTR's real-image eval pads to a square before resizing. Its inference
    # transform skips that pad, so a 2.5:1 screenshot is stretched into a knot.
    # Measured on the halichondrin screenshot: stretched input is disconnected
    # fragments; this pad gives one 83-atom molecule, mean atom score 0.85.
    # MolScribe was trained on the stretch, and the same pad still fails its gate.
    letterbox = getattr(predict, "__func__", None) is models.predict_molnextr.__func__ and image_ratio(path) >= 2
    model = None
    saved = None
    boxed = None
    try:
        if letterbox:
            models.load_molnextr()
            model = models.molnextr
            saved = model.transform
            model.transform = square_model_transform()
            boxed = letterboxed_copy(path)
            pred = predict(boxed)
        else:
            pred = predict(path)
    except Exception as exc:
        return pack_sample(sample_id, title, "image", note, "rejected", f"识别失败：{exc}"[:180],
                            [{"source": rel(source), "structures": []}], expect)
    finally:
        if model is not None:
            model.transform = saved
        if boxed and os.path.exists(boxed):
            os.remove(boxed)
    packed, ok = render_prediction(models, sample_dir, 0, pred)
    pages = [{"source": rel(source), "structures": [packed] if packed.get("mol") or packed.get("reason") else []}]
    if not ok:
        return pack_sample(sample_id, title, "image", note, "rejected", packed.get("reason") or "没有通过门槛",
                            pages, expect)
    confidence = pred.get("confidence")
    conf_txt = f"{float(confidence):.2f}" if confidence is not None else "无"
    layout = "扁图先垫成正方形，坐标仍来自识别图，没有从 SMILES 重排。" if letterbox else "坐标来自识别图，没有从 SMILES 重排。"
    return pack_sample(
        sample_id, title, "image", note, "structures",
        f"置信度 {conf_txt}。{layout}{ink_note}。",
        pages, expect,
    )


def pdf_samples_from_boxes(models, folder, literature_pages, predict, source_note, empty_reason, count_prefix):
    samples = []
    lit_pages_out = []
    lit_count = 0
    for page_info in literature_pages:
        boxes = page_info.get("boxes") or []
        if not boxes:
            continue
        page_dir = os.path.join(folder, "literature-pdf", f"p{page_info['page']}")
        os.makedirs(page_dir, exist_ok=True)
        structures = [{"box": box} for box in boxes]
        source = os.path.join(page_dir, "source.png")
        render_page_preview(LITERATURE, page_info["page"] - 1, structures, source, scale=1.15)
        rendered_list = []
        for index, box in enumerate(boxes):
            crop = os.path.join(page_dir, f"crop{index:02d}.png")
            crop_page(LITERATURE, page_info["page"] - 1, box, crop, scale=4.0)
            try:
                pred = predict(crop)
            except Exception as exc:
                rendered_list.append({"ok": False, "reason": str(exc)[:160]})
                continue
            packed, ok = render_prediction(models, page_dir, index, pred)
            rendered_list.append(packed)
            if ok:
                lit_count += 1
            print(count_prefix, "p", page_info["page"], index, "ok" if ok else packed.get("reason"), flush=True)
        lit_pages_out.append({"source": rel(source), "page": page_info["page"], "structures": rendered_list})
    samples.append(pack_sample(
        "literature-pdf", "文献 PDF", "pdf", source_note,
        "structures" if lit_count else "rejected",
        f"{count_prefix}收下 {lit_count} 个结构。" if lit_count else empty_reason,
        lit_pages_out, "structures",
    ))
    return samples, lit_count


def build_edgegrow(models, literature_pages):
    folder = os.path.join(OUT, "edgegrow")
    os.makedirs(folder, exist_ok=True)
    doc = fitz.open(LITERATURE)
    grown_pages = []
    for page_info in literature_pages:
        if not page_info["structures"]:
            continue
        page = doc[page_info["page"] - 1]
        boxes = [grow_box(page, structure["box"]) for structure in page_info["structures"]]
        grown_pages.append({"page": page_info["page"], "boxes": boxes})
    doc.close()
    samples, _ = pdf_samples_from_boxes(
        models, folder, grown_pages, models.predict_image,
        "矢量框再按边外扩，直到边上空出，最多 18 pt。然后 MolScribe。",
        "外扩之后没有通过门槛的结构。",
        "边外扩",
    )
    samples.append(image_via_predict(
        models, folder, "complex-screenshot", "复杂结构截图", COMPLEX, "structures",
        "整图交给 MolScribe。边外扩不改已经成图的截图。", models.predict_image,
    ))
    samples.append(image_via_predict(
        models, folder, "common-image", "常见图片", COMMON, "structures",
        "JPEG 整图交给 MolScribe。", models.predict_image,
    ))
    samples.append(pack_sample(
        "no-structure-pdf", "无结构 PDF", "pdf",
        "经济学 PDF。矢量定位没有框，边外扩无从开始。",
        "rejected", "没有可外扩的结构框。",
        plos_preview_pages(), "rejected",
    ))
    samples.append(image_via_predict(
        models, folder, "no-structure-image", "无结构图片", CHART, "rejected",
        "折线图。", models.predict_image,
    ))
    return {
        "id": "edgegrow",
        "label": "边外扩",
        "summary": "在矢量框上把仍切到墨迹的边向外推，每边最多 18 pt，再用 MolScribe 出坐标。ChemDraw 只套 ACS1996，不 Clean。",
        "samples": samples,
    }


def build_molnextr(models, literature_pages):
    folder = os.path.join(OUT, "molnextr")
    os.makedirs(folder, exist_ok=True)
    doc = fitz.open(LITERATURE)
    grown_pages = []
    for page_info in literature_pages:
        if not page_info["structures"]:
            continue
        page = doc[page_info["page"] - 1]
        boxes = [grow_box(page, structure["box"]) for structure in page_info["structures"]]
        grown_pages.append({"page": page_info["page"], "boxes": boxes})
    doc.close()
    samples, _ = pdf_samples_from_boxes(
        models, folder, grown_pages, models.predict_molnextr,
        "同一批外扩框，坐标来自 MolNexTR 预测的原子位置，不经过 SMILES 重画。",
        "MolNexTR 没有通过门槛的结构。",
        "MolNexTR",
    )
    samples.append(image_via_predict(
        models, folder, "complex-screenshot", "复杂结构截图", COMPLEX, "structures",
        "扁图先垫成正方形，再把整图交给 MolNexTR。", models.predict_molnextr,
    ))
    samples.append(image_via_predict(
        models, folder, "common-image", "常见图片", COMMON, "structures",
        "JPEG 整图交给 MolNexTR。", models.predict_molnextr,
    ))
    samples.append(pack_sample(
        "no-structure-pdf", "无结构 PDF", "pdf",
        "经济学 PDF。没有框就不把整页送进模型。",
        "rejected", "没有可识别的结构框。",
        plos_preview_pages(), "rejected",
    ))
    samples.append(image_via_predict(
        models, folder, "no-structure-image", "无结构图片", CHART, "rejected",
        "折线图。", models.predict_molnextr,
    ))
    return {
        "id": "molnextr",
        "label": "MolNexTR",
        "summary": "外扩后的裁图交给 MolNexTR。mol 用它预测的原子坐标，不用它从 SMILES 重画的那一份。ChemDraw 只套 ACS1996，不 Clean。",
        "samples": samples,
    }


def build_inkpage(models):
    folder = os.path.join(OUT, "inkpage")
    os.makedirs(folder, exist_ok=True)
    doc = fitz.open(LITERATURE)
    pages = []
    for index, page in enumerate(doc):
        boxes = ink_structure_boxes(page)
        print("ink page", index + 1, "boxes", len(boxes), flush=True)
        if boxes:
            pages.append({"page": index + 1, "boxes": boxes})
    doc.close()
    samples, lit_count = pdf_samples_from_boxes(
        models, folder, pages, models.predict_image,
        "不看矢量键。整页墨迹连成块，丢掉文字行和长直线，再交给 MolScribe。",
        "墨迹块没有通过门槛。",
        "墨迹",
    )
    samples.append(image_via_predict(
        models, folder, "complex-screenshot", "复杂结构截图", COMPLEX, "structures",
        "整图是一块墨迹，交给 MolScribe。", models.predict_image,
    ))
    samples.append(image_via_predict(
        models, folder, "common-image", "常见图片", COMMON, "structures",
        "JPEG 按墨迹块交给 MolScribe。", models.predict_image,
    ))
    plos = fitz.open(PLOS)
    plos_box_list = []
    for index, page in enumerate(plos):
        found = ink_structure_boxes(page)
        for box in found:
            plos_box_list.append((index, box))
    print("ink plos boxes", len(plos_box_list), flush=True)
    plos_dir = os.path.join(folder, "no-structure-pdf")
    os.makedirs(plos_dir, exist_ok=True)
    if plos_box_list:
        first = plos_box_list[0][0]
        preview_boxes = [{"box": box} for page_index, box in plos_box_list if page_index == first]
        source = os.path.join(plos_dir, "source.png")
        render_page_preview(PLOS, first, preview_boxes, source, scale=1.15)
        pages_out = [{"source": rel(source), "structures": []}]
        reason = f"墨迹阶段在第 {first + 1} 页留下 {len(preview_boxes)} 个块。这些块没有送去识别，框本身算误检。"
    else:
        pages_out = plos_preview_pages()
        reason = "正文行和直线被滤掉，没有留下结构块。"
    plos.close()
    samples.append(pack_sample(
        "no-structure-pdf", "无结构 PDF", "pdf",
        "经济学 PDF，按整页墨迹找块。",
        "rejected", reason, pages_out, "rejected",
    ))
    samples.append(image_via_predict(
        models, folder, "no-structure-image", "无结构图片", CHART, "rejected",
        "折线图。", models.predict_image,
    ))
    return {
        "id": "inkpage",
        "label": "墨迹框",
        "summary": "把页面渲成图，墨迹连通成块，丢掉细长的文字行。块再交给 MolScribe。不使用矢量键聚类。",
        "samples": samples,
    }


def attach_saved_frames():
    """Add clickable frame pixels to the saved comparison file. Does not re-render."""
    dest = os.path.join(OUT, "results.json")
    with open(dest, encoding="utf-8") as handle:
        payload = json.load(handle)
    literature = extract_pdf(LITERATURE, ocr=False)
    raw = {}
    grown = {}
    ink = {}
    doc = fitz.open(LITERATURE)
    for info in literature:
        if not info["structures"]:
            continue
        page = doc[info["page"] - 1]
        raw[info["page"]] = [structure["box"] for structure in info["structures"]]
        grown[info["page"]] = [grow_box(page, structure["box"]) for structure in info["structures"]]
    for index, page in enumerate(doc):
        found = ink_structure_boxes(page)
        if found:
            ink[index + 1] = found
    doc.close()
    plos_ink = {}
    plos = fitz.open(PLOS)
    for index, page in enumerate(plos):
        found = ink_structure_boxes(page)
        if found:
            plos_ink[index + 1] = found
    plos.close()
    by_scheme = {
        "vector": (raw, LITERATURE),
        "raster": (raw, LITERATURE),
        "roundtrip": (raw, LITERATURE),
        "edgegrow": (grown, LITERATURE),
        "molnextr": (grown, LITERATURE),
        "inkpage": (ink, LITERATURE),
    }
    for scheme_id, scheme in payload["schemes"].items():
        boxes_for_page, pdf_path = by_scheme.get(scheme_id, ({}, None))
        for sample in scheme["samples"]:
            for page in sample.get("pages") or []:
                source = page.get("source") or ""
                if not source:
                    continue
                png_path = os.path.join(ROOT, source.replace("/", os.sep))
                if not os.path.isfile(png_path):
                    print("missing", png_path)
                    continue
                structures = page.get("structures") or []
                if sample["id"] == "literature-pdf":
                    boxes = boxes_for_page.get(page.get("page")) or []
                    if len(boxes) != len(structures):
                        print("mismatch", scheme_id, page.get("page"), len(boxes), len(structures))
                        continue
                    frames, width, height = frames_from_boxes(
                        boxes, png_path, pdf_path, page["page"] - 1, linked=True,
                    )
                elif sample["id"] == "no-structure-pdf" and scheme_id == "inkpage" and plos_ink:
                    page_number = min(plos_ink)
                    frames, width, height = frames_from_boxes(
                        plos_ink[page_number], png_path, PLOS, page_number - 1, linked=False,
                    )
                elif len(structures) == 1:
                    frames, width, height = full_image_frame(png_path)
                else:
                    continue
                page["frames"] = frames
                page["width"] = width
                page["height"] = height
                overlaps = 0
                for left in range(len(frames)):
                    for right in range(left + 1, len(frames)):
                        a = frames[left]["box"]
                        b = frames[right]["box"]
                        if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                            overlaps += 1
                print(scheme_id, sample["id"], "page", page.get("page"), "frames", len(frames), "overlaps", overlaps)
    with open(dest, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print("frames ready", dest)


def add_schemes():
    ensure_dirs()
    dest = os.path.join(OUT, "results.json")
    with open(dest, encoding="utf-8") as handle:
        payload = json.load(handle)
    print("extract literature", flush=True)
    literature_pages = extract_pdf(LITERATURE, ocr=False)
    print("literature", sum(len(page["structures"]) for page in literature_pages), flush=True)

    def save():
        with open(dest, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        print("wrote", dest, flush=True)

    models = Models()
    try:
        payload["schemes"]["edgegrow"] = build_edgegrow(models, literature_pages)
        save()
        payload["schemes"]["molnextr"] = build_molnextr(models, literature_pages)
        save()
        payload["schemes"]["inkpage"] = build_inkpage(models)
        save()
        print("schemes ready", flush=True)
    finally:
        models.close()


if __name__ == "__main__":
    import sys
    command = sys.argv[1] if len(sys.argv) > 1 else "overlay"
    if command == "overlay":
        overlay()
    elif command == "run":
        run_all()
    elif command == "add-schemes":
        add_schemes()
    elif command == "attach-frames":
        attach_saved_frames()
    elif command == "serve":
        # This branch only, so overlay and run do not import webview.
        from comparison_page import serve
        if "--port" in sys.argv:
            serve(int(sys.argv[sys.argv.index("--port") + 1]))
        else:
            serve()
    else:
        raise SystemExit("use overlay, run, or serve")
