"""Ink groups inside a region, numbered, for picking ground-truth structure boxes."""
import os, sys, json
import numpy as np, cv2, fitz
from render_pages import PDFS, draw
ROOT = os.path.dirname(os.path.abspath(__file__))

def ink_groups(name, page_no, region, gap=3.0, scale=4.0):
    doc = fitz.open(PDFS[name]); page = doc[page_no - 1]
    clip = fitz.Rect(region)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    ink = (img.min(axis=2) < 200).astype(np.uint8)
    k = max(1, int(gap * scale))
    dil = cv2.dilate(ink, np.ones((k, k), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(dil, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        sub = ink[y:y + h, x:x + w] & (lab[y:y + h, x:x + w] == i)
        ys, xs = np.nonzero(sub)
        if len(xs) < 6:
            continue
        x0, y0 = clip.x0 + (x + xs.min()) / scale, clip.y0 + (y + ys.min()) / scale
        x1, y1 = clip.x0 + (x + xs.max() + 1) / scale, clip.y0 + (y + ys.max() + 1) / scale
        out.append([round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)])
    out.sort(key=lambda b: (round(b[1] / 10), b[0]))
    doc.close()
    return out

if __name__ == "__main__":
    name, page_no = sys.argv[1], int(sys.argv[2])
    region = [float(v) for v in sys.argv[3].split(",")]
    gap = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
    groups = ink_groups(name, page_no, region, gap)
    tag = f"{name}_p{page_no}_{'_'.join(str(int(v)) for v in region)}"
    json.dump(groups, open(os.path.join(ROOT, "gt_pages", tag + ".json"), "w"))
    draw(name, page_no - 1, [{"box": b, "label": str(i)} for i, b in enumerate(groups)],
         out=os.path.join(ROOT, "gt_pages", tag + ".png"), clip=region, scale=3.0)
    print(tag, len(groups))
