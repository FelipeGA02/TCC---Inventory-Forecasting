# -*- coding: utf-8 -*-
"""Lê o PDF exportado pelo Word e grava pages.json com a página impressa de cada título,
figura, quadro e tabela.

    python extract_pages.py <final.pdf> <structure.json> <pages.json>

A capa (índice 0) não é numerada e a folha de rosto é a página 1, então a página impressa é o
índice 0-based da folha no PDF; "__start__" é o índice da folha de "1 INTRODUÇÃO", valor do
pgNumType da seção do texto principal.
"""
import json
import re
import sys

import fitz

pdf, struct_path, out = sys.argv[1:4]
st = json.load(open(struct_path, encoding="utf-8"))
doc = fitz.open(pdf)
pages = [p.get_text("text") for p in doc]


def norm(s):
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


lines = [[norm(l) for l in t.splitlines() if l.strip()] for t in pages]
intro = next(i for i, ls in enumerate(lines) if "1 INTRODUÇÃO" in ls and not any("SUMÁRIO" == x for x in ls))
res = {"__start__": intro, "__pages__": len(pages)}


def first_page(pred, start):
    for i in range(start, len(lines)):
        if any(pred(l) for l in lines[i]):
            return i
    return None


for num, title, key in st["toc"]:
    target = norm(key)
    p = first_page(lambda l: l == target, intro)
    res[key] = p
for n, t in st["figs"]:
    res["Figura %d" % n] = first_page(lambda l, n=n: l.startswith("Figura %d –" % n), intro)
for n, t in st["quadros"]:
    res["Quadro %d" % n] = first_page(lambda l, n=n: l.startswith("Quadro %d –" % n), intro)
for n, t in st["tabelas"]:
    res["Tabela %d" % n] = first_page(lambda l, n=n: l.startswith("Tabela %d –" % n), intro)
missing = [k for k, v in res.items() if v is None]
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("introdução na folha", intro, "· total", len(pages), "· sem página:", missing)
