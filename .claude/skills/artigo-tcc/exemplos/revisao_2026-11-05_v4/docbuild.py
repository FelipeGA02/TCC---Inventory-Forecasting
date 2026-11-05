"""Montagem de parágrafos e tabelas no padrão do DOCX nativo do relatório técnico (v2).

Cada fábrica reproduz exatamente o pPr/rPr que o documento original usa para aquele tipo:
corpo (recuo de 1a linha 709), item "a)" (tab 1077, recuo pendente 369), títulos Ttulo1/Ttulo2
com número digitado, legenda (sz 20, keepNext, antes 240), fonte (sz 20, depois 240), Tabela
(bordas abertas: topo 12, cabeçalho 8, fim 12), Quadro (grade simples sz 4), entradas de
sumário e de listas (tabs com pontilhado até 9071) e referências (título em negrito).

Marcação no texto: [[itálico]] e **negrito**; "\t" vira <w:tab/>.
"""
import copy
import re

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
XML = "http://www.w3.org/XML/1998/namespace"
NBSP = " "


def q(tag, ns=W):
    return "{%s}%s" % (ns, tag)


def el(tag, attrs=None, ns=W, children=()):
    e = etree.Element(q(tag, ns))
    for k, v in (attrs or {}).items():
        e.set(q(k), str(v))
    for c in children:
        e.append(c)
    return e


def text_of(p):
    return "".join(t.text or "" for t in p.iter(q("t")))


# ----------------------------------------------------------------------------- runs
_TOK = re.compile(r"(\[\[.*?\]\]|\*\*.*?\*\*)")


def runs(text, sz=None, bold=False):
    """Lista de <w:r> a partir de texto com [[itálico]] e **negrito**; tabs viram <w:tab/>."""
    out = []
    # "[[[S. l.]]]" = colchete literal + itálico + colchete literal
    text = text.replace("[[[", "\x00[[").replace("]]]", "]]\x01")
    for part in _TOK.split(text):
        if not part:
            continue
        it = bo = False
        if part.startswith("[[") and part.endswith("]]"):
            part, it = part[2:-2], True
        elif part.startswith("**") and part.endswith("**"):
            part, bo = part[2:-2], True
        part = part.replace("\x00", "[").replace("\x01", "]")
        for k, chunk in enumerate(part.split("\t")):
            r = el("r")
            props = []
            if bold or bo:
                props.append(el("b"))
            if it:
                props.append(el("i"))
            if sz:
                props.append(el("sz", {"val": sz}))
            if props:
                rpr = el("rPr")
                for pr in props:
                    rpr.append(pr)
                r.append(rpr)
            if k > 0:
                r.append(el("tab"))
            if chunk:
                t = el("t")
                t.text = chunk
                t.set(q("space", XML), "preserve")
                r.append(t)
            if len(r) > (1 if r.find(q("rPr")) is not None else 0):
                out.append(r)
    return out


def _p(ppr_children, rs):
    p = el("p")
    if ppr_children:
        ppr = el("pPr")
        for c in ppr_children:
            ppr.append(c)
        p.append(ppr)
    for r in rs:
        p.append(r)
    return p


# ------------------------------------------------------------------ parágrafos do corpo
def body(text):
    return _p([el("ind", {"firstLine": 709})], runs(text))


def item(label, text):
    tabs = el("tabs", children=[el("tab", {"val": "left", "pos": 1077})])
    return _p([tabs, el("ind", {"left": 1077, "hanging": 369})], runs(label + "\t" + text))


def h1(text, center=False):
    ch = [el("pStyle", {"val": "Ttulo1"})]
    if center:
        ch.append(el("jc", {"val": "center"}))
    return _p(ch, runs(text))


def h2(text):
    return _p([el("pStyle", {"val": "Ttulo2"})], runs(text))


def caption(text):
    return _p([el("keepNext"), el("spacing", {"before": 240, "line": 240, "lineRule": "auto"}),
               el("jc", {"val": "center"})], runs(text, sz=20))


def source(text="Fonte: Elaborado pelos autores (2026)."):
    return _p([el("spacing", {"after": 240, "line": 240, "lineRule": "auto"}),
               el("jc", {"val": "center"})], runs(text, sz=20))


def reference(text):
    return _p([el("spacing", {"after": 240, "line": 240, "lineRule": "auto"}), el("jc", {"val": "left"})],
              runs(text))


def toc_entry(num, title, page):
    tabs = el("tabs", children=[el("tab", {"val": "left", "pos": 794}),
                                el("tab", {"val": "right", "leader": "dot", "pos": 9071})])
    rs = runs(num, bold=True) + runs("\t" + title, bold=True) + runs("\t" + str(page), bold=True)
    return _p([tabs, el("jc", {"val": "left"})], rs)


def list_entry(label, title, page):
    """Entrada das listas de figuras, quadros e tabelas."""
    tabs = el("tabs", children=[el("tab", {"val": "left", "pos": 1474}),
                                el("tab", {"val": "right", "leader": "dot", "pos": 9071})])
    rs = runs(label) + runs("\t" + title) + runs("\t" + str(page))
    return _p([tabs, el("ind", {"left": 1474, "hanging": 1474}), el("jc", {"val": "left"})], rs)


def sigla(sig, desc):
    tabs = el("tabs", children=[el("tab", {"val": "left", "pos": 1474})])
    return _p([tabs, el("ind", {"left": 1474, "hanging": 1474}), el("jc", {"val": "left"})],
              runs(sig + "\t" + desc))


def page_break():
    return _p([], [el("r", children=[el("br", {"type": "page"})])])


# ---------------------------------------------------------------------------- tabelas
def _cell_p(text, align, bold=False, keep=False):
    ch = [el("keepNext")] if keep else []
    ch += [el("spacing", {"before": 40, "after": 40, "line": 240, "lineRule": "auto"}), el("jc", {"val": align})]
    return _p(ch, runs(text, sz=20, bold=bold))


def _borders(kind, pos, last):
    """kind 'quadro' = grade; 'tabela' = aberta (topo 12 e base 8 no cabeçalho, base 12 no fim)."""
    b = el("tcBorders")
    if kind == "quadro":
        for side in ("top", "left", "bottom", "right"):
            b.append(el(side, {"val": "single", "sz": 4, "space": 0, "color": "000000"}))
        return b
    if pos == "header":
        b.append(el("top", {"val": "single", "sz": 12, "space": 0, "color": "000000"}))
        b.append(el("left", {"val": "nil"}))
        b.append(el("bottom", {"val": "single", "sz": 8, "space": 0, "color": "000000"}))
        b.append(el("right", {"val": "nil"}))
    else:
        b.append(el("top", {"val": "nil"}))
        b.append(el("left", {"val": "nil"}))
        if last:
            b.append(el("bottom", {"val": "single", "sz": 12, "space": 0, "color": "000000"}))
        else:
            b.append(el("bottom", {"val": "nil"}))
        b.append(el("right", {"val": "nil"}))
    return b


def table(kind, widths, header, rows, aligns=None):
    assert sum(widths) == 9072, (sum(widths), widths)
    n = len(widths)
    aligns = aligns or (["left"] + ["center"] * (n - 1))
    tbl = el("tbl")
    tblpr = el("tblPr", children=[
        el("tblW", {"w": 9072, "type": "dxa"}), el("jc", {"val": "center"}),
        el("tblLayout", {"type": "fixed"}),
        el("tblLook", {"val": "04A0", "firstRow": 1, "lastRow": 0, "firstColumn": 1, "lastColumn": 0,
                       "noHBand": 0, "noVBand": 1})])
    tbl.append(tblpr)
    grid = el("tblGrid")
    for w in widths:
        grid.append(el("gridCol", {"w": w}))
    tbl.append(grid)
    allrows = [("header", header)] + [("body", r) for r in rows]
    for i, (pos, cells) in enumerate(allrows):
        assert len(cells) == n, cells
        tr = el("tr")
        trpr = el("trPr")
        trpr.append(el("cantSplit"))
        if pos == "header":
            trpr.append(el("tblHeader"))
        trpr.append(el("jc", {"val": "center"}))
        tr.append(trpr)
        last = i == len(allrows) - 1
        for j, txt in enumerate(cells):
            tc = el("tc")
            tcpr = el("tcPr", children=[el("tcW", {"w": widths[j], "type": "dxa"}),
                                        _borders(kind, pos, last)])
            tc.append(tcpr)
            al = "center" if pos == "header" else aligns[j]
            for k, line in enumerate(str(txt).split("\n")):
                tc.append(_cell_p(line, al, bold=(pos == "header"), keep=not last))
            tr.append(tc)
        tbl.append(tr)
    return tbl


# ---------------------------------------------------------------------------- figuras
class Figures:
    """Cria parágrafos de imagem clonando o desenho de um parágrafo-modelo do documento."""

    def __init__(self, template_p, rels_root, media_dir):
        self.tpl = copy.deepcopy(template_p)
        self.rels = rels_root
        self.media_dir = media_dir
        self.n = 0
        self.next_docpr = 1000

    def add(self, png_path, width_emu, name):
        import os
        import shutil
        from PIL import Image
        self.n += 1
        fname = "fig_rev_%02d.png" % self.n
        shutil.copyfile(png_path, os.path.join(self.media_dir, fname))
        rid = "rIdRev%02d" % self.n
        rel = etree.SubElement(self.rels, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        rel.set("Id", rid)
        rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
        rel.set("Target", "media/" + fname)
        w, h = Image.open(png_path).size
        cx = int(width_emu)
        cy = int(round(cx * h / w))
        p = copy.deepcopy(self.tpl)
        inline = p.find(".//" + q("inline", WP))
        inline.find(q("extent", WP)).set("cx", str(cx))
        inline.find(q("extent", WP)).set("cy", str(cy))
        dp = inline.find(q("docPr", WP))
        self.next_docpr += 1
        dp.set("id", str(self.next_docpr))
        dp.set("name", "Picture %d" % self.next_docpr)
        inline.find(".//" + q("cNvPr", PIC)).set("name", name)
        inline.find(".//" + q("blip", A)).set(q("embed", R), rid)
        ext = inline.find(".//" + q("xfrm", A)).find(q("ext", A))
        ext.set("cx", str(cx))
        ext.set("cy", str(cy))
        for a in ("anchorId", "editId"):
            if inline.get(q(a, "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing")):
                del inline.attrib[q(a, "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing")]
        return p, (cx, cy)
