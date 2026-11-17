"""One-page locator evidence. Does not change the comparison page."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from PIL import Image, ImageDraw

import prototype as proto

PDF = proto.LITERATURE
PAGE_INDEX = 1
SCALE = 2.0


def main():
    doc = fitz.open(PDF)
    page = doc[PAGE_INDEX]
    drawings = page.get_drawings()
    print("drawings", len(drawings))
    print("keys", sorted(drawings[0].keys()) if drawings else [])
    invisible = 0
    white = 0
    for drawing in drawings:
        stroke = drawing.get("stroke_opacity", 1)
        fill = drawing.get("fill_opacity", 1)
        color = drawing.get("color")
        fill_color = drawing.get("fill")
        if stroke == 0 and (fill == 0 or fill is None):
            invisible += 1
        if color in ((1, 1, 1), (1.0, 1.0, 1.0)) or fill_color in ((1, 1, 1),):
            white += 1
    print("invisible", invisible, "white", white)
    sample = drawings[0]
    items = sample["items"][:2]
    print("sample_rect", tuple(round(v, 2) for v in (sample["rect"].x0, sample["rect"].y0, sample["rect"].x1, sample["rect"].y1)))
    print("sample_items", items)
    print("sample_width", sample.get("width"), "closePath", sample.get("closePath"), "type", sample.get("type"))

    bonds, ticks, glyphs = proto.page_primitives(page)
    lengths = sorted(bond["length"] for bond in bonds)
    median = lengths[len(lengths) // 2]
    gap = max(3.6, 0.34 * median)
    print("bonds", len(bonds), "ticks", len(ticks), "glyphs", len(glyphs), "median", round(median, 2), "gap", round(gap, 2))
    inside = 0
    for bond in bonds:
        mx = (bond["p1"][0] + bond["p2"][0]) / 2
        my = (bond["p1"][1] + bond["p2"][1]) / 2
        for glyph in glyphs:
            rect = glyph["rect"]
            if rect[0] <= mx <= rect[2] and rect[1] <= my <= rect[3]:
                inside += 1
                break
    print("bond_midpoints_inside_glyph_rect", inside)
    long_bonds = [bond for bond in bonds if bond["length"] > 1.6 * median]
    print("bonds_longer_than_1.6_median", len(long_bonds), "longest", round(max(bond["length"] for bond in bonds), 2))

    dashed = proto.dashed_from_ticks(ticks)
    groups = proto.cluster_bonds(bonds + dashed, gap)
    accepted = []
    for group in groups:
        plain = [bond for bond in group if bond.get("stereo") != "hash"]
        if proto.accept_cluster(plain or group):
            accepted.append(plain or group)
    print("groups", len(groups), "accepted", len(accepted))
    for index, group in enumerate(sorted(accepted, key=len, reverse=True)):
        box = proto.bbox_of(group, 8)
        print(
            f"box {index:02d} bonds {len(group):3d} "
            f"w {box[2] - box[0]:6.1f} h {box[3] - box[1]:6.1f} "
            f"xy {box[0]:6.1f},{box[1]:6.1f}"
        )

    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    draw = ImageDraw.Draw(image)

    def xy(point):
        return point[0] * SCALE, point[1] * SCALE

    for glyph in glyphs:
        rect = glyph["rect"]
        draw.rectangle(
            [rect[0] * SCALE, rect[1] * SCALE, rect[2] * SCALE, rect[3] * SCALE],
            outline=(0, 160, 0),
        )
    for bond in bonds:
        draw.line([xy(bond["p1"]), xy(bond["p2"])], fill=(220, 0, 0), width=2)
    for group in accepted:
        box = proto.bbox_of(group, 8)
        draw.rectangle(
            [box[0] * SCALE, box[1] * SCALE, box[2] * SCALE, box[3] * SCALE],
            outline=(0, 80, 255),
            width=2,
        )
    dest = os.path.join(proto.ROOT, "preview", "diag-p2.png")
    image.save(dest)
    print("wrote", dest)
    doc.close()


if __name__ == "__main__":
    main()
