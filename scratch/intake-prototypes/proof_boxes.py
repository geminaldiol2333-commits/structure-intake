"""Crop the joined boxes. OCR stays off so the check only measures geometry."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from PIL import Image

import prototype as proto


def save_crop(image, box, name, scale, pad=2):
    crop = image.crop((
        int((box[0] - pad) * scale),
        int((box[1] - pad) * scale),
        int((box[2] + pad) * scale),
        int((box[3] + pad) * scale),
    ))
    path = os.path.join(proto.ROOT, "preview", "crops", name + ".png")
    crop.save(path)
    print("saved", name, crop.size, path)


def main():
    pages = proto.extract_pdf(proto.LITERATURE, ocr=False)
    structs = pages[1]["structures"]
    print("page2", len(structs))
    for index, structure in enumerate(structs):
        box = structure["box"]
        print(
            f"{index:02d} atoms {structure['n_atoms']:3d} bonds {structure['n_bonds']:3d} "
            f"w {box[2] - box[0]:6.1f} h {box[3] - box[1]:6.1f} "
            f"xy {box[0]:6.1f},{box[1]:6.1f}"
        )
    doc = fitz.open(proto.LITERATURE)
    page = doc[1]
    scale = 3
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    os.makedirs(os.path.join(proto.ROOT, "preview", "crops"), exist_ok=True)
    perylene = [
        item for item in structs
        if (item["box"][2] - item["box"][0]) > 90 and item["box"][1] < 470
    ]
    ru = [
        item for item in structs
        if item["box"][0] > 360
        and 470 < item["box"][1] < 560
        and (item["box"][2] - item["box"][0]) > 40
    ]
    print("perylene_candidates", len(perylene), "ru_candidates", len(ru))
    if perylene:
        save_crop(image, perylene[0]["box"], "fixed-perylene", scale)
    if ru:
        widest = max(ru, key=lambda item: item["box"][2] - item["box"][0])
        save_crop(image, widest["box"], "fixed-ru", scale)
    save_crop(image, structs[12]["box"], "fixed-ru-12", scale)
    save_crop(image, structs[5]["box"], "fixed-dimer", scale)
    doc.close()
    plos = proto.extract_pdf(proto.PLOS, ocr=False)
    print("plos_structures", sum(len(item["structures"]) for item in plos))


if __name__ == "__main__":
    main()
