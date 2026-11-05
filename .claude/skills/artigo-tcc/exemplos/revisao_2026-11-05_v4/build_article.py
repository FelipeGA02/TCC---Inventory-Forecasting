# -*- coding: utf-8 -*-
"""Monta a nova versão do relatório técnico a partir do DOCX nativo v2 (work_dl).

    python build_article.py <scratch> [pages.json]

Lê <scratch>/work_dl, grava <scratch>/work_out. Com pages.json (gerado por extract_pages.py a
partir do PDF do Word), preenche os números de página do sumário e das listas e o início da
numeração do texto (pgNumType da última seção).
"""
import copy
import json
import os
import re
import shutil
import sys

from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docbuild as B  # noqa: E402
from content_a import (ABSTRACT, CAP1_7, KEYWORDS, PALAVRAS, RESUMO, SIGLAS)  # noqa: E402
from content_b import CAP5B, CAP6  # noqa: E402
import content_c as C  # noqa: E402

W = B.W
q = B.q
SCR = sys.argv[1]
PAGES = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else {}
SRC = os.path.join(SCR, "work_dl")
OUT = os.path.join(SCR, "work_out")
DIAG = os.path.join(SCR, "diag")
SHOTS = os.path.join(SCR, "shots")

if os.path.exists(OUT):
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
doc_path = os.path.join(OUT, "word", "document.xml")
rels_path = os.path.join(OUT, "word", "_rels", "document.xml.rels")
tree = etree.parse(doc_path)
root = tree.getroot()
body = root.find(q("body"))
rels_tree = etree.parse(rels_path)
rels = rels_tree.getroot()

FILL = dict(C.FILL)


def fmt(s):
    for k, v in FILL.items():
        s = s.replace("{" + k + "}", v)
    assert not re.search(r"\{[A-Z_0-9]+\}", s), "marcador sem valor: " + s[:120]
    return s


def find_top(startswith=None, equals=None):
    hits = []
    for e in body:
        if etree.QName(e).localname != "p":
            continue
        t = B.text_of(e).strip()
        if (startswith and t.startswith(startswith)) or (equals is not None and t == equals):
            hits.append(e)
    assert len(hits) == 1, (startswith, equals, len(hits))
    return hits[0]


def set_runs(p, runs):
    for r in list(p):
        if etree.QName(r).localname != "pPr":
            p.remove(r)
    for r in runs:
        p.append(r)


def page(key):
    return str(PAGES.get(key, 0))


# ------------------------------------------------------------------ pré-textuais
resumo_p = find_top(startswith="Este trabalho apresenta o desenvolvimento")
set_runs(resumo_p, B.runs(fmt(RESUMO)))
kw = find_top(startswith="Palavras-chave:")
set_runs(kw, B.runs("**Palavras-chave: **" + PALAVRAS))

resumo_h = find_top(equals="RESUMO")
pb_after_kw = kw.getnext()          # parágrafo vazio
while not any(br.get(q("type")) == "page" for br in pb_after_kw.iter(q("br"))):
    pb_after_kw = pb_after_kw.getnext()
abs_h = copy.deepcopy(resumo_h)
for lr in abs_h.iter(q("lastRenderedPageBreak")):
    lr.getparent().remove(lr)
set_runs(abs_h, B.runs("ABSTRACT", bold=True))
abs_p = copy.deepcopy(resumo_p)
set_runs(abs_p, B.runs(fmt(ABSTRACT)))
blank = copy.deepcopy(kw.getprevious())
abs_kw = copy.deepcopy(kw)
set_runs(abs_kw, B.runs("**Keywords: **" + KEYWORDS))
abs_pb = copy.deepcopy(pb_after_kw)
cur = pb_after_kw
for e in (abs_h, abs_p, blank, abs_kw, abs_pb):
    cur.addnext(e)
    cur = e


def replace_list(heading_text, entries):
    h = find_top(equals=heading_text)
    nxt = h.getnext()
    while not any(br.get(q("type")) == "page" for br in nxt.iter(q("br"))) and nxt.find(q("pPr") + "/" + q("sectPr")) is None:
        nn = nxt.getnext()
        body.remove(nxt)
        nxt = nn
    cur = h
    for e in entries:
        cur.addnext(e)
        cur = e


FIGS = C.FIGURE_LIST          # [(n, titulo)]
QUADROS = C.QUADRO_LIST
TABELAS = C.TABELA_LIST
replace_list("LISTA DE FIGURAS", [B.list_entry("Figura %d –" % n, t, page("Figura %d" % n)) for n, t in FIGS])
replace_list("LISTA DE QUADROS", [B.list_entry("Quadro %d –" % n, t, page("Quadro %d" % n)) for n, t in QUADROS])
replace_list("LISTA DE TABELAS", [B.list_entry("Tabela %d –" % n, t, page("Tabela %d" % n)) for n, t in TABELAS])
replace_list("LISTA DE ABREVIATURAS E SIGLAS", [B.sigla(s, d) for s, d in SIGLAS])

# --------------------------------------------------------------------- corpo
BLOCKS = CAP1_7 + CAP5B + CAP6 + C.CAP7 + C.CAP8 + C.CAP9

toc = []
for b in BLOCKS:
    if b[0] in ("h1", "h2"):
        m = re.match(r"^(\d+(?:\.\d+)?)\s+(.*)$", b[1])
        toc.append((m.group(1), m.group(2), b[1]))
toc.append(("", "REFERÊNCIAS", "REFERÊNCIAS"))
replace_list("SUMÁRIO", [B.toc_entry(n, t, page(k)) for n, t, k in toc])

# localiza o parágrafo com a quebra de seção que encerra os pré-textuais
sect_ps = [e for e in body if etree.QName(e).localname == "p" and e.find(q("pPr") + "/" + q("sectPr")) is not None]
last_pre = sect_ps[-1]
fig_tpl = None
for e in body:
    if etree.QName(e).localname == "p" and e.find(".//" + q("drawing")) is not None and "Picture 2" in etree.tostring(e, encoding="unicode"):
        fig_tpl = e
assert fig_tpl is not None
final_sect = body.find(q("sectPr"))
# remove o texto principal antigo
e = last_pre.getnext()
while e is not None and e is not final_sect:
    nn = e.getnext()
    body.remove(e)
    e = nn

figs = B.Figures(fig_tpl, rels, os.path.join(OUT, "word", "media"))


def img_path(key):
    for d in (DIAG, SHOTS):
        p = os.path.join(d, key + ".png")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(key)


new = []
for b in BLOCKS:
    kind = b[0]
    if kind == "h1":
        new.append(B.h1(b[1]))
    elif kind == "h2":
        new.append(B.h2(b[1]))
    elif kind == "p":
        new.append(B.body(fmt(b[1])))
    elif kind == "i":
        new.append(B.item(b[1], fmt(b[2])))
    elif kind == "fig":
        _, key, cap, width = b[:4]
        src = b[4] if len(b) > 4 else "Fonte: Elaborado pelos autores (2026)."
        p, _ = figs.add(img_path(key), width, key + ".png")
        new += [B.caption(cap), p, B.source(src)]
    elif kind in ("quadro", "tabela"):
        _, cap, widths, header, rows, aligns, src = b
        new += [B.caption(cap), B.table(kind, widths, header, [[fmt(c) for c in r] for r in rows], aligns),
                B.source(src)]
    else:
        raise ValueError(kind)
new.append(B.h1("REFERÊNCIAS", center=True))
for r in C.REFERENCIAS:
    new.append(B.reference(r))
for e in new:
    final_sect.addprevious(e)

# início da numeração do texto principal
start = PAGES.get("__start__", 9)
pg = final_sect.find(q("pgNumType"))
pg.set(q("start"), str(start))

# relações e mídias órfãs
used = set(root.xpath("//@r:embed", namespaces={"r": B.R}))
REL_IMG = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
for rel in list(rels):
    if rel.get("Type") == REL_IMG and rel.get("Id") not in used:
        f = os.path.join(OUT, "word", rel.get("Target"))
        if os.path.exists(f):
            os.remove(f)
        rels.remove(rel)

tree.write(doc_path, xml_declaration=True, encoding="UTF-8", standalone=True)
rels_tree.write(rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)
json.dump({"toc": toc, "figs": FIGS, "quadros": QUADROS, "tabelas": TABELAS},
          open(os.path.join(SCR, "structure.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok:", len(new), "elementos no corpo;", figs.n, "figuras; início da numeração", start)
