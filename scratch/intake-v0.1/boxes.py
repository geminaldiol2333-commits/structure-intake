# Structure boxes from page ink. Works the same on vector and raster pages.
#
# A page is rendered, every non-white pixel is ink (colour counts, pale panel
# shading does not), and ink closer than GAP_PT is one group. ChemDraw leaves
# about 1.6 pt between a bond end and its label, so a label joins its bond while
# a compound number or a caption, 5 pt or more away, stays a separate group.
# A group is kept when it is drawn like a structure: several straight strokes
# of bond length at hexagon angles. Text lines and arrows are not.

from __future__ import annotations

import math

import cv2
import fitz
import numpy as np

SCALE = 4.0          # px per pt for the ink pass
GAP_PT = 3.0         # ink closer than this is one group
INK_LEVEL = 200      # a pixel is ink when its darkest channel is below this


LONG_RULE_PT = 40.0  # straight ink runs longer than this are frames, rules, brackets or arrow shafts


def render(page, scale=SCALE, clip=None):
    rect = fitz.Rect(clip) if clip else page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
    rgb = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
    return rgb, rect


def page_ink(page, scale=SCALE, clip=None, drop_text=True, drop_rules=True, with_parts=False):
    """Ink mask with body text and long straight rules taken out.

    with_parts also returns the RGB render and the ink that was taken out, so a
    caller can tell what a frame touches and white it out of a crop.
    """
    rgb, rect = render(page, scale, clip)
    raw = (rgb.min(axis=2) < INK_LEVEL).astype(np.uint8)
    mask = raw.copy()
    if drop_text:
        # Body text, captions and headers are real text in a born-digital PDF.
        # Atom labels inside a drawing are usually glyph outlines or part of an
        # embedded picture. A real-text word within 2 pt of ink that is not
        # text is a label of that drawing and stays.
        boxes = []
        for x0, y0, x1, y1, word, *_ in page.get_text("words", clip=rect):
            a = max(int((x0 - rect.x0) * scale) - 1, 0)
            b = max(int((y0 - rect.y0) * scale) - 1, 0)
            c = max(int(math.ceil((x1 - rect.x0) * scale)) + 1, 0)
            d = max(int(math.ceil((y1 - rect.y0) * scale)) + 1, 0)
            boxes.append((a, b, c, d))
        text = np.zeros_like(mask)
        for a, b, c, d in boxes:
            text[b:d, a:c] = 1
        drawing = mask & (1 - text)
        near = int(2 * scale)
        for a, b, c, d in boxes:
            around = drawing[max(b - near, 0):d + near, max(a - near, 0):c + near]
            if around.any():
                continue
            mask[b:d, a:c] = 0
    if drop_rules:
        n = int(LONG_RULE_PT * scale)
        bridge = int(3 * scale)
        horiz = cv2.dilate(mask, np.ones((1, bridge), np.uint8))
        horiz = cv2.morphologyEx(horiz, cv2.MORPH_OPEN, np.ones((1, n), np.uint8))
        vert = cv2.dilate(mask, np.ones((bridge, 1), np.uint8))
        vert = cv2.morphologyEx(vert, cv2.MORPH_OPEN, np.ones((n, 1), np.uint8))
        rules = cv2.dilate(horiz | vert, np.ones((3, 3), np.uint8))
        mask = mask & (1 - rules)
    if with_parts:
        return mask, rect, rgb, raw & (1 - mask)
    return mask, rect


def ink_groups(mask, scale=SCALE, gap_pt=GAP_PT):
    k = max(1, int(round(gap_pt * scale)))
    joined = cv2.dilate(mask, np.ones((k, k), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    groups = []
    for index in range(1, count):
        x, y, w, h, _ = stats[index]
        sub = (labels[y:y + h, x:x + w] == index) & (mask[y:y + h, x:x + w] > 0)
        ys, xs = np.nonzero(sub)
        if len(xs) < 8:
            continue
        groups.append({
            "id": index,
            "px": (x + int(xs.min()), y + int(ys.min()), x + int(xs.max()) + 1, y + int(ys.max()) + 1),
            "ink": int(len(xs)),
        })
    return groups, labels


_LSD = None


def strokes(mask_crop, scale=SCALE):
    """Straight segments as (length_pt, angle_deg in [0, 180))."""
    global _LSD
    if _LSD is None:
        _LSD = cv2.createLineSegmentDetector()
    image = np.where(mask_crop > 0, 0, 255).astype(np.uint8)
    found = _LSD.detect(image)[0]
    out = []
    if found is None:
        return out
    for x1, y1, x2, y2 in found.reshape(-1, 4):
        length = math.hypot(x2 - x1, y2 - y1) / scale
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
        out.append((length, angle))
    return out


def group_features(mask, labels, group, scale=SCALE):
    x0, y0, x1, y1 = group["px"]
    crop = ((labels[y0:y1, x0:x1] == group["id"]) & (mask[y0:y1, x0:x1] > 0)).astype(np.uint8)
    segs = strokes(crop, scale)
    long_segs = [s for s in segs if s[0] >= 4.0]
    slanted = [s for s in long_segs if 15 <= s[1] <= 75 or 105 <= s[1] <= 165]
    horizontal = [s for s in long_segs if s[1] < 8 or s[1] > 172]
    w_pt, h_pt = (x1 - x0) / scale, (y1 - y0) / scale
    return {
        "w": w_pt, "h": h_pt,
        "density": group["ink"] / max((x1 - x0) * (y1 - y0), 1),
        "n_long": len(long_segs),
        "n_slant": len(slanted) / 2.0,   # LSD reports both edges of a stroke
        "n_horiz": len(horizontal) / 2.0,
        "max_len": max((s[0] for s in long_segs), default=0.0),
    }


def looks_like_structure(f):
    if f["w"] < 14 or f["h"] < 12:
        return False
    if f["h"] < 14 and f["w"] / max(f["h"], 1e-6) > 4:
        return False          # one line of text, or an arrow
    if f["n_slant"] < 4 or f["n_long"] < 10:
        return False          # a cross mark or a stray glyph
    if f["n_slant"] / max(f["n_long"], 1) < 0.15:
        return False          # a block of text: many strokes, few of them slanted
    if f["n_long"] / max(f["w"] * f["h"], 1e-6) < 0.007:
        return False          # a chart or a sketch: big, with few strokes for its area
    return f["density"] <= 0.3


def to_pt(px_box, rect, scale=SCALE):
    x0, y0, x1, y1 = px_box
    return [round(rect.x0 + x0 / scale, 2), round(rect.y0 + y0 / scale, 2),
            round(rect.x0 + x1 / scale, 2), round(rect.y0 + y1 / scale, 2)]


TOUCH_PT = 1.5     # removed ink this close to a structure is something touching it
TOUCH_MIN_PX = 24  # at SCALE 4, about 1.5 pt of a 1 pt stroke


def page_structures(page, scale=SCALE, gap_pt=GAP_PT, pad_pt=2.0):
    """Kept groups with a clean crop each.

    Every pixel of the crop that is not this group's ink is white, so an arrow,
    a bracket, a compound number or a neighbour inside the padded box does not
    reach the recogniser. touch lists the sides where ink that was taken out
    (a rule, an arrow shaft, a frame, a caption word) comes within TOUCH_PT of
    the structure; such a frame is shown for review instead of recognised.
    """
    mask, rect, rgb, removed = page_ink(page, scale, with_parts=True)
    groups, labels = ink_groups(mask, scale, gap_pt)
    height, width = mask.shape
    pad = int(round(pad_pt * scale))
    reach = int(round(TOUCH_PT * scale))
    out = []
    for group in groups:
        f = group_features(mask, labels, group, scale)
        if not looks_like_structure(f):
            continue
        x0, y0, x1, y1 = group["px"]
        a, b = max(x0 - pad, 0), max(y0 - pad, 0)
        c, d = min(x1 + pad, width), min(y1 + pad, height)
        own = (labels[b:d, a:c] == group["id"]) & (mask[b:d, a:c] > 0)
        keep = cv2.dilate(own.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        crop = rgb[b:d, a:c].copy()
        crop[~keep] = 255
        near = cv2.dilate(own.astype(np.uint8), np.ones((2 * reach + 1, 2 * reach + 1), np.uint8)) > 0
        hit = near & (removed[b:d, a:c] > 0) & ~own
        sides = []
        if int(hit.sum()) >= TOUCH_MIN_PX:
            ys, xs = np.nonzero(hit)
            gx0, gy0, gx1, gy1 = x0 - a, y0 - b, x1 - a, y1 - b
            band = reach + 2
            for side, sel in (("left", xs <= gx0 + band), ("right", xs >= gx1 - band),
                              ("top", ys <= gy0 + band), ("bottom", ys >= gy1 - band)):
                if int(sel.sum()) >= TOUCH_MIN_PX // 2:
                    sides.append(side)
            if not sides:
                sides = ["inside"]
        out.append({
            "box": to_pt((a, b, c, d), rect, scale),
            "ink_box": to_pt(group["px"], rect, scale),
            "crop": crop,
            "touch": sides,
            "features": f,
        })
    return reading_order(out)


def reading_order(items):
    """Rows top to bottom, left to right in a row. A box joins a row when its
    vertical centre falls inside the row's span."""
    rows = []
    for item in sorted(items, key=lambda it: it["box"][1]):
        centre = (item["box"][1] + item["box"][3]) / 2
        for row in rows:
            if row["top"] <= centre <= row["bottom"]:
                row["items"].append(item)
                row["bottom"] = max(row["bottom"], item["box"][3])
                break
        else:
            rows.append({"top": item["box"][1], "bottom": item["box"][3], "items": [item]})
    ordered = []
    for row in rows:
        ordered.extend(sorted(row["items"], key=lambda it: it["box"][0]))
    return ordered


def page_boxes(page, scale=SCALE, gap_pt=GAP_PT, with_features=False):
    mask, rect = page_ink(page, scale)
    groups, labels = ink_groups(mask, scale, gap_pt)
    boxes = []
    for group in groups:
        f = group_features(mask, labels, group, scale)
        keep = looks_like_structure(f)
        if with_features:
            boxes.append({"box": to_pt(group["px"], rect, scale), "features": f, "keep": keep})
        elif keep:
            boxes.append(to_pt(group["px"], rect, scale))
    return boxes

