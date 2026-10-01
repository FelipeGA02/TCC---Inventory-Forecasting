# -*- coding: utf-8 -*-
"""Troca a imagem de uma figura no DOCX desempacotado e ajusta o tamanho de exibição.

    python replace_figure.py <work> "Picture 2234" nova.png --width-emu 5760085
    python replace_figure.py <work> "Picture 1909" fig2_hi.png --ppi 274

A figura é localizada pelo nome do desenho (wp:docPr name), que é estável; o nome do arquivo em
word/media muda quando o Word salva. A imagem é gravada no formato do arquivo existente (jpg/png),
então o [Content_Types].xml não precisa mudar. Altura = largura × proporção da nova imagem.

--ppi N: largura = largura_px / N polegadas (mantém o tamanho tipográfico dos diagramas originais:
Fig. 1 ≈ 240, Fig. 2 ≈ 274, Fig. 3 ≈ 316, Fig. 4 ≈ 256, Fig. 5 ≈ 200 px/pol para render a 110 dpi;
dobre o valor se renderizar a 220 dpi). Largura máxima útil da página: 5.760.085 EMU (≈ 6,3 pol).
"""
import argparse
import os
import re

from PIL import Image
import sys

sys.stdout.reconfigure(encoding="utf-8")

EMU_IN = 914400
MAX_W = 5760085

ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("name")
ap.add_argument("image")
g = ap.add_mutually_exclusive_group()
g.add_argument("--width-emu", type=int)
g.add_argument("--ppi", type=float)
a = ap.parse_args()

doc_p = os.path.join(a.work, "word", "document.xml")
rels_p = os.path.join(a.work, "word", "_rels", "document.xml.rels")
doc = open(doc_p, encoding="utf-8").read()
rels = open(rels_p, encoding="utf-8").read()

blocks = [m for m in re.finditer(r"<wp:inline.*?</wp:inline>", doc, flags=re.S) if 'name="%s"' % a.name in m.group(0)]
if len(blocks) != 1:
    raise SystemExit("desenho %r: %d ocorrências" % (a.name, len(blocks)))
block = blocks[0].group(0)
rid = re.search(r'r:embed="(rId\d+)"', block).group(1)
rel = [r for r in re.findall(r"<Relationship [^>]*>", rels) if 'Id="%s"' % rid in r][0]
target = re.search(r'Target="([^"]+)"', rel).group(1)
media = os.path.join(a.work, "word", target)

im = Image.open(a.image).convert("RGB")
if media.lower().endswith((".jpg", ".jpeg")):
    im.save(media, "JPEG", quality=92)
else:
    im.save(media, "PNG", optimize=True)

old_cx, old_cy = map(int, re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"/>', block).groups())
if a.width_emu:
    cx = a.width_emu
elif a.ppi:
    cx = int(im.width / a.ppi * EMU_IN)
else:
    cx = old_cx
cx = min(cx, MAX_W)
cy = int(cx * im.height / im.width)
new_block = re.sub(r'<wp:extent cx="\d+" cy="\d+"/>', '<wp:extent cx="%d" cy="%d"/>' % (cx, cy), block)
new_block = re.sub(r'<a:ext cx="\d+" cy="\d+"/>', '<a:ext cx="%d" cy="%d"/>' % (cx, cy), new_block)
open(doc_p, "w", encoding="utf-8").write(doc.replace(block, new_block))
print(f"{a.name} → {target}: {im.size[0]}x{im.size[1]} px, {cx / EMU_IN:.2f} x {cy / EMU_IN:.2f} pol"
      f" (antes {old_cx / EMU_IN:.2f} x {old_cy / EMU_IN:.2f})")
