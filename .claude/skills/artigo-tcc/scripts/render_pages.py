# -*- coding: utf-8 -*-
"""Renderiza o PDF exportado pelo Word em PNGs e monta folhas de contato para inspeção visual.

    PYTHONPATH=<tmp>/pylib python render_pages.py <final.pdf> <tmp>/pages [--dpi 60] [--cols 7] [--per-sheet 14]
    python render_pages.py <final.pdf> <tmp>/pages --only 17,18 --dpi 90   # páginas legíveis

Requer PyMuPDF (pip install --target <tmp>/pylib pymupdf) e Pillow. Gera p01.png... e sheet_01.png...
Leia as folhas com a ferramenta Read: procure legenda separada da figura, página quase vazia,
título de capítulo sem quebra de página, linha em branco dupla, tabela cortada.
"""
import argparse
import glob
import os

import fitz  # PyMuPDF
from PIL import Image
import sys

sys.stdout.reconfigure(encoding="utf-8")

ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("outdir")
ap.add_argument("--dpi", type=int, default=60)
ap.add_argument("--cols", type=int, default=7)
ap.add_argument("--per-sheet", type=int, default=14)
ap.add_argument("--only", default="")
a = ap.parse_args()

os.makedirs(a.outdir, exist_ok=True)
for f in glob.glob(os.path.join(a.outdir, "*.png")):
    os.remove(f)
doc = fitz.open(a.pdf)
only = {int(x) for x in a.only.split(",") if x}
pages = []
for i in range(doc.page_count):
    if only and (i + 1) not in only:
        continue
    out = os.path.join(a.outdir, f"p{i + 1:02d}.png")
    doc[i].get_pixmap(dpi=a.dpi).save(out)
    pages.append(out)
print("páginas no PDF:", doc.page_count)

for s in range(0, len(pages), a.per_sheet):
    ims = [Image.open(f) for f in pages[s:s + a.per_sheet]]
    w = max(i.width for i in ims)
    h = max(i.height for i in ims)
    cols = min(a.cols, len(ims))
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), "white")
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * w, (k // cols) * h))
    name = os.path.join(a.outdir, f"sheet_{s // a.per_sheet + 1:02d}.png")
    sheet.save(name)
    print(name, os.path.basename(pages[s]), "→", os.path.basename(pages[min(s + a.per_sheet, len(pages)) - 1]))
