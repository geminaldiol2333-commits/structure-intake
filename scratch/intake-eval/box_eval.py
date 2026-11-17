"""Score structure boxes against the hand-labelled gt.json.

A ground-truth box G is *found* when some predicted box P covers >= 80 % of G and
>= 50 % of P is G. It is *complete* when P also contains G shrunk by 1.5 pt.
A predicted box is a false positive when it matches no G and lies mostly
outside the ignore regions (3D models, mechanism brackets, partial drawings).

    python scratch/intake-eval/box_eval.py                 # current pipeline
    python scratch/intake-eval/box_eval.py --method sealed  # before edge review
"""
import argparse, json, os, sys, time
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "intake-prototypes"))
import fitz  # noqa: E402
from render_pages import PDFS, draw  # noqa: E402


def area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def inter(a, b):
    return area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def contains(p, g, tol=1.5):
    return p[0] <= g[0] + tol and p[1] <= g[1] + tol and p[2] >= g[2] - tol and p[3] >= g[3] - tol


def score_page(pred, gt, ignore):
    found = complete = loose = 0
    used = set()
    per_gt = []
    for g in gt:
        best, best_i = None, None
        for i, p in enumerate(pred):
            ov = inter(p, g)
            if area(g) and ov / area(g) >= 0.8 and area(p) and ov / area(p) >= 0.5:
                if best is None or ov / (area(p) + area(g) - ov) > best:
                    best, best_i = ov / (area(p) + area(g) - ov), i
        state = "missed"
        if best_i is not None:
            found += 1
            used.add(best_i)
            state = "found"
            if area(pred[best_i]) >= 1.6 * area(g):
                loose += 1
                state = "loose"
            if contains(pred[best_i], g):
                complete += 1
                state = "complete"
        per_gt.append(state)
    fp = merged = 0
    for i, p in enumerate(pred):
        if i in used:
            continue
        if any(area(g) and inter(p, g) / area(g) >= 0.5 for g in gt):
            continue
        covered = []
        if len(covered) >= 2:
            merged += 1
            continue
        ign = sum(inter(p, z) for z in ignore)
        if area(p) and ign / area(p) >= 0.5:
            continue
        fp += 1
    return {"gt": len(gt), "pred": len(pred), "found": found, "complete": complete,
            "loose": loose, "fp": fp, "merged": merged, "per_gt": per_gt}


def method_current(name, page_no, stage):
    """The v0.1 app path: vector clusters -> seal_boxes -> review_boxes."""
    import prototype as page
    doc = fitz.open(PDFS[name])
    try:
        pages = page.extract_pdf(PDFS[name], ocr=False)
        info = next(p for p in pages if p["page"] == page_no)
        if not info.get("structures"):
            return []
        if stage == "raw":
            return [s["box"] for s in info["structures"]]
        sealed = page.seal_boxes(doc[page_no - 1], info["structures"])
        if stage == "sealed":
            return sealed
        kept, _sent = page.review_boxes(doc[page_no - 1], sealed)
        return kept
    finally:
        doc.close()


def method_ink(name, page_no):
    sys.path.insert(0, os.path.join(ROOT, "..", "intake-v0.1"))
    import boxes
    doc = fitz.open(PDFS[name])
    try:
        return boxes.page_boxes(doc[page_no - 1])
    finally:
        doc.close()


METHODS = {
    "ink": method_ink,
    "current": lambda n, p: method_current(n, p, "kept"),
    "sealed": lambda n, p: method_current(n, p, "sealed"),
    "raw": lambda n, p: method_current(n, p, "raw"),
}


def run(method, out_dir=None, verbose=True):
    gt = json.load(open(os.path.join(ROOT, "gt.json")))
    total = {"gt": 0, "pred": 0, "found": 0, "complete": 0, "loose": 0, "fp": 0, "merged": 0}
    unverified = 0
    by_pdf = {}
    rows = []
    keys = set(gt)
    for name in PDFS:
        with fitz.open(PDFS[name]) as doc:
            keys.update(f"{name}|{i + 1}" for i in range(len(doc)))
    for key in sorted(keys, key=lambda k: (k.split("|")[0], int(k.split("|")[1]))):
        gt.setdefault(key, {"structures": [], "ignore": []})
        name, page_no = key.split("|")[0], int(key.split("|")[1])
        t0 = time.time()
        pred = [list(map(float, b)) for b in METHODS[method](name, page_no)]
        if not gt[key]["structures"] and not gt[key]["ignore"]:
            unverified += len(pred)
            continue
        res = score_page(pred, gt[key]["structures"], gt[key]["ignore"])
        res["seconds"] = round(time.time() - t0, 2)
        rows.append((key, res))
        for k in total:
            total[k] += res[k]
            by_pdf.setdefault(name, {kk: 0 for kk in total})[k] += res[k]
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            boxes = [{"box": g, "label": f"G{i}:{s[0]}", "color": (0, 160, 0)}
                     for i, (g, s) in enumerate(zip(gt[key]["structures"], res["per_gt"]))]
            boxes += [{"box": p, "label": f"P{i}", "color": (220, 0, 0)} for i, p in enumerate(pred)]
            draw(name, page_no - 1, boxes, out=os.path.join(out_dir, f"{name}_p{page_no}.png"), scale=2.0)
    if verbose:
        print(f"method={method}")
        print(f"{'page':10s} {'gt':>4s} {'pred':>5s} {'found':>6s} {'compl':>6s} {'fp':>4s} {'merge':>6s}")
        for key, r in rows:
            if not r["gt"] and not r["pred"]:
                continue
            print(f"{key:10s} {r['gt']:4d} {r['pred']:5d} {r['found']:6d} {r['complete']:6d} {r['fp']:4d} {r['merged']:6d}")
        for name, t in sorted(by_pdf.items()):
            print(f"{name:10s} {t['gt']:4d} {t['pred']:5d} {t['found']:6d} {t['complete']:6d} {t['fp']:4d} {t['merged']:6d}")
        t = total
        print(f"{'TOTAL':10s} {t['gt']:4d} {t['pred']:5d} {t['found']:6d} {t['complete']:6d} {t['fp']:4d} {t['merged']:6d}")
        print(f"recall(found) {t['found']/t['gt']:.1%}  recall(complete) {t['complete']/t['gt']:.1%}  "
              f"precision {t['found']/max(t['found']+t['fp']+t['merged'],1):.1%}  "
              f"(boxes on unlabelled pages, not scored: {unverified})")
    return total, rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="current", choices=sorted(METHODS))
    ap.add_argument("--overlay", default="")
    args = ap.parse_args()
    run(args.method, args.overlay or None)
