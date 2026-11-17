"""Render PDF pages with a point grid for hand-labelling structure boxes."""
import os, sys, fitz
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.abspath(__file__))
PDFS = {
    "bjoc": os.path.join(ROOT, "..", "intake-prototypes", "samples", "bjoc-19-142.pdf"),
    "X-1": r"C:\Users\ycc\Documents\出题人\仿生合成\X-1.pdf",
    "X-2": r"C:\Users\ycc\Documents\出题人\仿生合成\X-2.pdf",
    "X-3": r"C:\Users\ycc\Documents\出题人\仿生合成\X-3.pdf",
    "hima": r"C:\Users\ycc\Documents\出题人\Himastatin\Himastatin.pdf",
    "flavin": r"C:\Users\ycc\Documents\出题人\Flavin\Flavin.pdf",
    "aza": r"C:\Users\ycc\Documents\出题人\[3.1.1]\s41570-024-00623-0.pdf",
    "thia": r"C:\Users\ycc\Documents\出题人\SCNs\chen-et-al-2022-thiazole-5-carbaldehyde-synthesis-by-cascade-annulation-of-enaminones-and-kscn-with-dess-martin.pdf",
}
SCALE = 2.0
def draw(name, index, boxes=(), out=None, clip=None, scale=SCALE, step=20):
    doc = fitz.open(PDFS[name]); page = doc[index]
    rect = fitz.Rect(clip) if clip else page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    d = ImageDraw.Draw(im)
    font = ImageFont.load_default()
    x = (int(rect.x0) // step) * step
    while x <= rect.x1:
        px = (x - rect.x0) * scale
        d.line([(px, 0), (px, im.height)], fill=(180, 220, 255) if x % 100 else (90, 160, 255), width=1)
        d.text((px + 1, 1), str(x), fill=(0, 90, 220), font=font)
        x += step
    y = (int(rect.y0) // step) * step
    while y <= rect.y1:
        py = (y - rect.y0) * scale
        d.line([(0, py), (im.width, py)], fill=(180, 220, 255) if y % 100 else (90, 160, 255), width=1)
        d.text((1, py + 1), str(y), fill=(0, 90, 220), font=font)
        y += step
    for i, b in enumerate(boxes):
        x0, y0, x1, y1 = b["box"]
        col = b.get("color", (230, 0, 0))
        d.rectangle(((x0 - rect.x0) * scale, (y0 - rect.y0) * scale, (x1 - rect.x0) * scale, (y1 - rect.y0) * scale), outline=col, width=2)
        d.text(((x0 - rect.x0) * scale + 2, (y0 - rect.y0) * scale + 2), b.get("label", str(i)), fill=col, font=font)
    im.save(out)
    doc.close()
if __name__ == "__main__":
    for name, path in PDFS.items():
        doc = fitz.open(path)
        for i in range(len(doc)):
            draw(name, i, out=os.path.join(ROOT, "gt_pages", f"{name}_p{i+1}.png"))
        doc.close()
