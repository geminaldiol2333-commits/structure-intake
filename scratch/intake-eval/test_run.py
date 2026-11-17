"""Run the extraction pipeline (read_pdf) over new organic-chemistry PDFs and
report per-file acceptance, then build crop-vs-render contact sheets for eyeballing.

    python scratch/intake-eval/test_run.py file1.pdf file2.pdf ...
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "intake-v0.1"))
import app  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

OUT = os.path.join(ROOT, "out", "new_tests")


def sheets(view, job_id, folder, name):
    import fitz
    src = app.JOB["source"]
    doc = fitz.open(src) if view["kind"] == "pdf" else None
    pairs = []
    for page_view in view.get("pages") or []:
        number = page_view.get("page") or 1
        for index, frame in enumerate(page_view.get("frames") or []):
            structure = page_view["structures"][frame["structure"]]
            if not structure.get("render") and not structure.get("pending"):
                continue
            pt = frame.get("pt")
            if pt and doc:
                x0, y0, x1, y1 = pt
            else:
                box = frame["box"]
                if view["kind"] == "pdf":
                    rect = doc[number - 1].rect
                    sc = page_view.get("scale") or app.PREVIEW_SCALE
                    x0, y0, x1, y1 = box[0] / sc, box[1] / sc, box[2] / sc, box[3] / sc
                else:
                    x0, y0, x1, y1 = box
            pairs.append((page_view, structure, (x0, y0, x1, y1), number, index))
    if doc:
        doc.close()
    if not pairs:
        return 0
    W, H = 460, 300
    rows_per = 6
    for k in range(0, len(pairs), rows_per):
        chunk = pairs[k:k + rows_per]
        sheet = Image.new("RGB", (2 * W + 10, len(chunk) * (H + 22)), "white")
        d = ImageDraw.Draw(sheet)
        for r, (page_view, structure, box, number, index) in enumerate(chunk):
            y = r * (H + 22)
            d.text((5, y + 2),
                   f"p{number} f{index} ok={structure.get('ok')} atoms={structure.get('n_atoms')} "
                   f"pending={structure.get('pending')} review={';'.join(structure.get('review') or [])[:60]}",
                   fill="red" if (structure.get("pending") or not structure.get("ok")) else "black")
            for col, img_path in ((0, page_view.get("source")), (1, structure.get("render"))):
                if not img_path:
                    continue
                full = os.path.join(folder, img_path.split("/jobs/" + job_id + "/", 1)[-1].replace("/", os.sep))
                if not os.path.isfile(full):
                    continue
                with Image.open(full) as im:
                    im = im.convert("RGB")
                    if view["kind"] == "pdf" and col == 0:
                        pw, ph = im.size
                        sc = page_view.get("scale") or app.PREVIEW_SCALE
                        im = im.crop((int(box[0] * sc), int(box[1] * sc), int(box[2] * sc), int(box[3] * sc)))
                    im.thumbnail((W, H))
                    sheet.paste(im, (col * (W + 10), y + 18))
        sheet.save(os.path.join(OUT, f"{name}_sheet{k // rows_per:02d}.png"))
    return len(pairs)


def main(paths):
    os.makedirs(OUT, exist_ok=True)
    app.start_sta()
    for path in paths:
        name = os.path.splitext(os.path.basename(path))[0][:40]
        try:
            import threading, time as _t
            job_id = _t.strftime("%H%M%S") + "t"
            folder = os.path.join(app.JOBS, job_id)
            os.makedirs(folder, exist_ok=True)
            stored = os.path.join(folder, "upload.pdf")
            import shutil
            shutil.copyfile(path, stored)
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                view, clips = app.on_sta(app.read_pdf, stored, folder, job_id)
                app.JOB.update({"id": job_id, "clips": clips, "view": view, "folder": folder,
                                "source": stored, "kind": "pdf", "serial": {}})
            else:
                print(f"== {name}: image input not handled by this runner", flush=True)
                continue
        except Exception as exc:
            print(f"== {name}: FAILED {exc!r}"[:200], flush=True)
            continue
        kept = pend = rev = 0
        pages_with = 0
        for page_view in view.get("pages") or []:
            frames = page_view.get("frames") or []
            if frames:
                pages_with += 1
            for frame in frames:
                s = page_view["structures"][frame["structure"]]
                kept += 1 if s.get("ok") else 0
                rev += 1 if s.get("ok") and s.get("review") else 0
                pend += 1 if s.get("pending") else 0
        n = sheets(view, job_id, folder, name)
        print(f"== {name}: {view['status']} {view['reason']} | pages_with {pages_with} "
              f"ok {kept} review {rev} pending {pend} sheets {n}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
