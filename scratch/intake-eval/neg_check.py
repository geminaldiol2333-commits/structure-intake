import os, sys, json
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "intake-v0.1"))
import app, fitz, boxes
from PIL import Image
from flag_exp import flags
page = app.page
tmp = os.path.join(ROOT, "out", "neg"); os.makedirs(tmp, exist_ok=True)
items = [("chart", os.path.join(ROOT, "..", "intake-prototypes", "samples", "no-structure-chart.png"))]
# false-positive boxes from the labelled pages
from render_pages import PDFS
for name, pno in (("bjoc", 6), ("bjoc", 7), ("bjoc", 9), ("bjoc", 1), ("X-3", 2), ("X-2", 3)):
    d = fitz.open(PDFS[name])
    for i, s in enumerate(boxes.page_structures(d[pno - 1])):
        if name == "X-2" and i > 0:
            break
        p = os.path.join(tmp, f"{name}_p{pno}_{i}.png"); Image.fromarray(s["crop"]).save(p)
        items.append((f"{name}_p{pno}_{i}", p))
for label, path in items:
    pred = app.predict_file(path)
    block = page.clear_either_doubles(pred.get("molfile") or "")
    f = flags(block) if block else {"empty": True}
    print(label, "conf", round(pred.get("confidence") or 0, 2), "atoms", len(pred.get("atoms") or []),
          {k: v for k, v in f.items() if v})
