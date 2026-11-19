# -*- coding: utf-8 -*-
"""Atualiza as páginas das listas de figuras, quadros e tabelas pela paginação do PDF do Word.

    python listas.py <final.pdf> <work>/word/document.xml
"""
import re
import sys

import fitz
from lxml import etree

sys.stdout.reconfigure(encoding="utf-8")
pdf, xml = sys.argv[1], sys.argv[2]
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
q = lambda t: f"{{{W}}}{t}"

d = fitz.open(pdf)
norm = lambda s: re.sub(r"\s+", " ", s.replace(" ", " ")).strip()
lines = [[norm(l) for l in p.get_text().splitlines() if l.strip()] for p in d]
intro = next(i for i, ls in enumerate(lines) if i > 8 and "1 INTRODUÇÃO" in ls)
paginas = {}
for i in range(intro, len(lines)):
    num = next((l for l in lines[i][:2] if re.fullmatch(r"\d{1,3}", l)), None)
    for l in lines[i]:
        mt = re.match(r"^(Figura|Quadro|Tabela) (\d+) – ", l)
        if mt and f"{mt.group(1)} {mt.group(2)}" not in paginas:
            paginas[f"{mt.group(1)} {mt.group(2)}"] = num
tree = etree.parse(xml)
mud = 0
for p in tree.getroot().iter(q("p")):
    ts = p.findall(f".//{q('t')}")
    if not ts or p.find(f".//{q('tab')}") is None:
        continue
    mt = re.match(r"(Figura|Quadro|Tabela) (\d+) – ", "".join(t.text or "" for t in ts))
    if not mt or not re.fullmatch(r"\d+", (ts[-1].text or "").strip()):
        continue
    k = f"{mt.group(1)} {mt.group(2)}"
    if paginas.get(k) and ts[-1].text != paginas[k]:
        print(f"  {k}: {ts[-1].text} -> {paginas[k]}")
        ts[-1].text = paginas[k]
        mud += 1
tree.write(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
print("páginas do PDF:", len(d), "| entradas alteradas:", mud, "| legendas achadas:", len(paginas))
