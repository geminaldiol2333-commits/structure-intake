"""Turn gt_raw.jsonl (picked proposals + rough boxes) into gt.json with ink-tight boxes."""
import json, os, sys
import numpy as np, cv2, fitz
from render_pages import PDFS, draw
ROOT = os.path.dirname(os.path.abspath(__file__))
SCALE = 4.0

def page_ink(name, page_no):
    doc = fitz.open(PDFS[name]); page = doc[page_no - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), alpha=False)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    doc.close()
    return (img.min(axis=2) < 200).astype(np.uint8)

def snap(ink, labels, rough, keep=0.3):
    x0, y0, x1, y1 = [int(round(v * SCALE)) for v in rough]
    x0, y0 = max(0, x0), max(0, y0)
    window = labels[y0:y1, x0:x1]
    ids, inside = np.unique(window[window > 0], return_counts=True)
    chosen = []
    for comp, count in zip(ids, inside):
        total = STATS[comp, cv2.CC_STAT_AREA]
        if count >= keep * total:
            chosen.append(comp)
    ys, xs = np.nonzero(ink[y0:y1, x0:x1])
    if len(xs) == 0:
        return None
    bx0, by0, bx1, by1 = x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1
    if not chosen:
        return [round(bx0 / SCALE, 1), round(by0 / SCALE, 1), round(bx1 / SCALE, 1), round(by1 / SCALE, 1)]
    xs0 = min(STATS[c, cv2.CC_STAT_LEFT] for c in chosen)
    ys0 = min(STATS[c, cv2.CC_STAT_TOP] for c in chosen)
    xs1 = max(STATS[c, cv2.CC_STAT_LEFT] + STATS[c, cv2.CC_STAT_WIDTH] for c in chosen)
    ys1 = max(STATS[c, cv2.CC_STAT_TOP] + STATS[c, cv2.CC_STAT_HEIGHT] for c in chosen)
    return [round(xs0 / SCALE, 1), round(ys0 / SCALE, 1), round(xs1 / SCALE, 1), round(ys1 / SCALE, 1)]

if __name__ == "__main__":
    out = {}
    cache = {}
    for line in open(os.path.join(ROOT, "gt_raw.jsonl"), encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row["pdf"], row["page"])
        if key not in cache:
            ink = page_ink(*key)
            # components on the raw ink: bonds touch at atoms, labels sit within ~1 pt
            dil = cv2.dilate(ink, np.ones((5, 5), np.uint8))
            n, lab, stats, _ = cv2.connectedComponentsWithStats(dil, connectivity=8)
            cache[key] = (ink, lab * (ink > 0), stats)
        ink, lab, STATS = cache[key]
        entry = out.setdefault(f"{row['pdf']}|{row['page']}", {"structures": [], "ignore": []})
        rough = list(row.get("manual") or [])
        if row.get("inkpick"):
            sys.path.insert(0, os.path.join(ROOT, "..", "intake-v0.1"))
            import boxes as inkboxes
            doc = fitz.open(PDFS[row["pdf"]])
            try:
                found = inkboxes.page_structures(doc[row["page"] - 1])
            finally:
                doc.close()
            rough += [found[i]["ink_box"] for i in row["inkpick"]]
        if row.get("pick"):
            props = json.load(open(os.path.join(ROOT, "gt_pages",
                f"{row['pdf']}_p{row['page']}_{'_'.join(str(int(v)) for v in row['region'])}.json")))
            rough += [props[i] for i in row["pick"]]
        for box in rough:
            snapped = snap(ink, lab, [box[0] - 0.5, box[1] - 0.5, box[2] + 0.5, box[3] + 0.5])
            if snapped:
                entry["structures"].append(snapped)
        for box in row.get("exact") or []:
            x0, y0, x1, y1 = [int(round(v * SCALE)) for v in box]
            ys, xs = np.nonzero(ink[y0:y1, x0:x1])
            if len(xs):
                entry["structures"].append([round((x0 + xs.min()) / SCALE, 1), round((y0 + ys.min()) / SCALE, 1),
                                            round((x0 + xs.max() + 1) / SCALE, 1), round((y0 + ys.max() + 1) / SCALE, 1)])
        entry["ignore"] += row.get("ignore") or []
    json.dump(out, open(os.path.join(ROOT, "gt.json"), "w"), indent=1)
    os.makedirs(os.path.join(ROOT, "gt_check"), exist_ok=True)
    for key, entry in out.items():
        name, page_no = key.split("|")
        boxes = [{"box": b, "label": f"S{i}"} for i, b in enumerate(entry["structures"])]
        boxes += [{"box": b, "label": "ign", "color": (150, 150, 150)} for b in entry["ignore"]]
        draw(name, int(page_no) - 1, boxes, out=os.path.join(ROOT, "gt_check", f"{name}_p{page_no}.png"), scale=2.0)
        print(key, len(entry["structures"]), "ignore", len(entry["ignore"]))
