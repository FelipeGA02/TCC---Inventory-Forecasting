# -*- coding: utf-8 -*-
"""Renderiza o PDF da ata em PNGs e monta uma folha com todas as páginas lado a lado.

    C:/Users/Felipe_2clix/.claude/tcc-env/Scripts/python.exe renderizar_pdf.py <ata.pdf> <pasta>

Requer PyMuPDF e Pillow (já instalados no tcc-env; senão: python -m pip --python <python do
venv> install pymupdf pillow). Gera p1.png… e folha.png; leia folha.png com a ferramenta Read.
"""
import os
import sys

import fitz  # PyMuPDF
from PIL import Image

pdf, pasta = sys.argv[1], sys.argv[2]
os.makedirs(pasta, exist_ok=True)
doc = fitz.open(pdf)
paginas = []
for i, pagina in enumerate(doc):
    caminho = os.path.join(pasta, f"p{i + 1}.png")
    pagina.get_pixmap(dpi=70).save(caminho)
    paginas.append(Image.open(caminho))
largura, altura = paginas[0].size
folha = Image.new("RGB", (len(paginas) * (largura + 6) - 6, altura), "red")
for k, im in enumerate(paginas):
    folha.paste(im, (k * (largura + 6), 0))
folha.save(os.path.join(pasta, "folha.png"))
print(f"{doc.page_count} páginas ->", os.path.join(pasta, "folha.png"))
