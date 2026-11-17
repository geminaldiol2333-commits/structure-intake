import json, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "intake-v0.1"))
import fitz, boxes
from render_pages import PDFS
from box_eval import area, inter
gt = json.load(open(os.path.join(ROOT, "gt.json")))
rows = []
for key, entry in gt.items():
    name, p = key.split("|")
    doc = fitz.open(PDFS[name]); page = doc[int(p) - 1]
    for g in boxes.page_boxes(page, with_features=True):
        b = g["box"]
        lab = "neg"
        for t in entry["structures"]:
            ov = inter(b, t)
            if ov / area(t) >= 0.8 and ov / area(b) >= 0.5:
                lab = "POS"
            elif ov / area(t) >= 0.3:
                lab = "part" if lab == "neg" else lab
        if lab == "neg" and any(area(b) and inter(b, z) / area(b) >= 0.5 for z in entry["ignore"]):
            lab = "ign"
        f = g["features"]
        rows.append((lab, key, b, f))
    doc.close()
import collections
print(collections.Counter(r[0] for r in rows))
for lab in ("POS", "part", "neg"):
    sel = [r for r in rows if r[0] == lab and r[3]["w"] >= 12 and r[3]["h"] >= 10]
    print("==", lab, len(sel))
    for r in sorted(sel, key=lambda r: r[3]["n_slant"])[:60 if lab != "neg" else 400]:
        f = r[3]
        if lab == "neg" and f["n_slant"] < 1.5:
            continue
        print(f"{r[1]:8s} {str([round(v) for v in r[2]]):24s} w{f['w']:5.0f} h{f['h']:5.0f} slant{f['n_slant']:5.1f} long{f['n_long']:4d} hz{f['n_horiz']:4.1f} max{f['max_len']:5.1f} d{f['density']:.2f}")
