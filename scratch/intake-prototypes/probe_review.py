"""Re-run the frame review on X-3 and the literature PDF.

Prints how many sealed frames are sent back, and checks three frames on X-3
that the current seal still gets wrong.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fitz
import prototype as page

X3 = r"C:\Users\ycc\Documents\出题人\仿生合成\X-3.pdf"
LIT = page.LITERATURE
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview", "edge-probe")


def summarize(path, pages):
    doc = fitz.open(path)
    extracted = {info["page"]: info for info in page.extract_pdf(path, ocr=False)}
    rows = []
    for number in pages:
        info = extracted.get(number)
        if not info or not info["structures"]:
            print(f"{os.path.basename(path)} page {number} no structures")
            continue
        pdf_page = doc[number - 1]
        sealed = page.seal_boxes(pdf_page, info["structures"])
        kept, sent = page.review_boxes(pdf_page, sealed)
        print(
            f"{os.path.basename(path)} page {number} sealed {len(sealed)} "
            f"kept {len(kept)} sent {len(sent)}"
        )
        for item in sent:
            box = tuple(round(v, 1) for v in item["box"])
            print(f"  sent {box} cuts={item['cuts']}")
        for box in kept:
            print(f"  kept {tuple(round(v, 1) for v in box)}")
        rows.append((number, sealed, kept, sent, pdf_page))
    doc.close()
    return rows


def contains(box, point, pad=0):
    x, y = point
    return box[0] - pad <= x <= box[2] + pad and box[1] - pad <= y <= box[3] + pad


def main():
    os.makedirs(OUT, exist_ok=True)
    # 1d sits near (120, 450). Aspochalasin D's cut ring is the wider frame
    # near y=430 and y=580. The close arrow is on page 8.
    rows = summarize(X3, (5, 7, 8, 10))
    page5 = [row for row in rows if row[0] == 5][0]
    _number, _sealed, kept, sent, pdf_page = page5
    sent_boxes = [item["box"] for item in sent]
    one_d = [box for box in sent_boxes if contains(box, (124, 455), 30)]
    macro = [box for box in sent_boxes if contains(box, (210, 455), 8) or contains(box, (215, 600), 8)]
    allyl = [box for box in sent_boxes if contains(box, (240, 170), 6)]
    kept_1a = [box for box in kept if contains(box, (120, 600), 20)]
    print("page5 1d", len(one_d), "macro", len(macro), "allyl", len(allyl), "kept 1a", len(kept_1a))
    assert one_d, "1d TBSO frame was not sent back"
    assert macro, "macrocycle frame was not sent back"
    assert allyl, "AllylO frame between the arrows was not sent back"
    assert kept_1a, "complete 1a frame was sent back"
    summarize(LIT, (2, 5))
    print("review ok")


if __name__ == "__main__":
    main()
