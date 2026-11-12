"""Monta o relatório no modelo da Aula 2 a partir do DOCX completo (formatação) e de conteudo.py.

Uso: python builder.py <work_base> <work_novo>
  work_base: DOCX completo desempacotado (só leitura)
  work_novo: cópia que recebe o novo corpo
Marcação no texto: ⟨itálico⟩, ⟪negrito⟫, {fig:chave} / {tab:chave} / {qd:chave} -> "Figura N" etc.
"""
import copy
import os
import re
import shutil
import sys

from lxml import etree
from PIL import Image

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
q = lambda t: f"{{{W}}}{t}"
XS = "{http://www.w3.org/XML/1998/namespace}space"
NB = " "
EMU_CM = 360000

BASE, NOVO = sys.argv[1], sys.argv[2]
if os.path.exists(NOVO):
    shutil.rmtree(NOVO)
shutil.copytree(BASE, NOVO)
DOC = os.path.join(NOVO, "word", "document.xml")
tree = etree.parse(DOC)
root = tree.getroot()
body = root.find(q("body"))
ELS = list(body)


def text(e):
    return "".join(t.text or "" for t in e.iter(q("t")))


def find_p(prefix, start=0):
    hits = [e for e in ELS[start:] if e.tag == q("p") and text(e).startswith(prefix)]
    assert hits, prefix
    return hits[0]


def find_tbl(contains):
    hits = [e for e in ELS if e.tag == q("tbl") and contains in text(e)]
    assert len(hits) == 1, (contains, len(hits))
    return hits[0]


def clean_ids(el):
    for e in el.iter():
        for a in list(e.attrib):
            if a.endswith("paraId") or a.endswith("textId"):
                del e.attrib[a]
    for b in list(el.iter(q("bookmarkStart"))) + list(el.iter(q("bookmarkEnd"))):
        b.getparent().remove(b)
    for b in list(el.iter(q("lastRenderedPageBreak"))):
        b.getparent().remove(b)
    return el


# ---------------------------------------------------------------- runs
def runs_from(s, base_rpr=None):
    out = []
    for part in re.split(r"(⟨.*?⟩|⟪.*?⟫)", s):
        if not part:
            continue
        r = etree.Element(q("r"))
        rpr = copy.deepcopy(base_rpr) if base_rpr is not None else None
        if part[0] in "⟨⟪":
            rpr = rpr if rpr is not None else etree.Element(q("rPr"))
            tag = "i" if part[0] == "⟨" else "b"
            if rpr.find(q(tag)) is None:
                el = etree.Element(q(tag))
                # ordem do schema: b antes de i, ambos antes de sz
                sz = rpr.find(q("sz"))
                if sz is not None:
                    sz.addprevious(el)
                else:
                    rpr.append(el)
            part = part[1:-1]
        if rpr is not None and len(rpr):
            r.append(rpr)
        t = etree.SubElement(r, q("t"))
        t.text = part
        t.set(XS, "preserve")
        out.append(r)
    return out


def to_markup(p):
    """Texto do parágrafo com ⟨itálico⟩ e ⟪negrito⟫ (ignora sz)."""
    s = []
    for r in p.iter(q("r")):
        t = "".join(x.text or "" for x in r.iter(q("t")))
        if r.find(q("tab")) is not None:
            t = "\t" + t
        rp = r.find(q("rPr"))
        if rp is not None and rp.find(q("i")) is not None and t.strip():
            t = "⟨" + t + "⟩"
        elif rp is not None and rp.find(q("b")) is not None and t.strip():
            t = "⟪" + t + "⟫"
        s.append(t)
    return re.sub(r"⟩⟨", "", re.sub(r"⟫⟪", "", "".join(s)))


# ---------------------------------------------------------------- modelos (do DOCX completo)
M_BODY = clean_ids(copy.deepcopy(find_p("A previsão de demanda pode apoiar o planejamento")))
M_H1 = clean_ids(copy.deepcopy(find_p("1 INTRODUÇÃO", 130)))
M_H2 = clean_ids(copy.deepcopy(find_p("1.1 Problematização")))
M_LI = clean_ids(copy.deepcopy(find_p("\ta)\tlevantar e validar") if False else
                               [e for e in ELS if e.tag == q("p") and text(e).startswith("a)levantar e validar")][0]))
M_CAP = clean_ids(copy.deepcopy(find_p("Figura 1 – Etapas da metodologia", 150)))
M_FIG = clean_ids(copy.deepcopy([e for e in ELS if e.tag == q("p") and e.find(f".//{{{WP}}}docPr") is not None
                                 and e.find(f".//{{{WP}}}docPr").get("name") == "Picture 1001"][0]))
M_SRC = clean_ids(copy.deepcopy(find_p("Fonte: Elaborado pelos autores (2026).", 190)))
M_REF = clean_ids(copy.deepcopy(find_p("BREIMAN, L. Random forests.")))
M_LIST_ENTRY = clean_ids(copy.deepcopy(find_p("Figura 1 –Etapas da metodologia")))
M_SIGLA = clean_ids(copy.deepcopy(find_p("ADFAugmented")))


def set_runs(p, s, base_rpr=None):
    for c in [c for c in p if c.tag != q("pPr")]:
        p.remove(c)
    for r in runs_from(s, base_rpr):
        p.append(r)
    return p


def sz20():
    rp = etree.Element(q("rPr"))
    etree.SubElement(rp, q("sz")).set(q("val"), "20")
    return rp


def para_body(s):
    return set_runs(copy.deepcopy(M_BODY), s)


def para_h(level, s):
    m = M_H1 if level == 1 else M_H2
    p = set_runs(copy.deepcopy(m), s)
    if level == 3:
        p.find(q("pPr")).find(q("pStyle")).set(q("val"), "Ttulo3")
    return p


def para_li(letter, s):
    p = copy.deepcopy(M_LI)
    for c in [c for c in p if c.tag != q("pPr")]:
        p.remove(c)
    r = etree.SubElement(p, q("r"))
    t = etree.SubElement(r, q("t"))
    t.text = f"{letter})"
    first = True
    for rr in runs_from(s):
        if first:
            rr.insert(0, etree.Element(q("tab")))
            first = False
        p.append(rr)
    return p


def para_caption(s):
    return set_runs(copy.deepcopy(M_CAP), s, sz20())


def para_source(s):
    return set_runs(copy.deepcopy(M_SRC), s, sz20())


def para_center(s, bold=False, before=0, after=0, page_break=False):
    p = etree.Element(q("p"))
    ppr = etree.SubElement(p, q("pPr"))
    if page_break:
        etree.SubElement(ppr, q("pageBreakBefore"))
    sp = etree.SubElement(ppr, q("spacing"))
    sp.set(q("before"), str(before)); sp.set(q("after"), str(after))
    etree.SubElement(ppr, q("jc")).set(q("val"), "center")
    return set_runs(p, f"⟪{s}⟫" if bold else s)


# ---------------------------------------------------------------- imagens
RELS = os.path.join(NOVO, "word", "_rels", "document.xml.rels")
rels_tree = etree.parse(RELS)
rels_root = rels_tree.getroot()
_rid = [max(int(r.get("Id")[3:]) for r in rels_root) + 1]
_docpr = [3000]
MEDIA = os.path.join(NOVO, "word", "media")


def add_image(path):
    ext = os.path.splitext(path)[1].lower().replace(".jpeg", ".jpg")
    rid = f"rId{_rid[0]}"; _rid[0] += 1
    name = f"novo{_rid[0]}{ext}"
    shutil.copy(path, os.path.join(MEDIA, name))
    el = etree.SubElement(rels_root, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
    el.set("Id", rid)
    el.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
    el.set("Target", f"media/{name}")
    return rid


def para_image(path, width_cm, max_h_cm=21.0):
    w, h = Image.open(path).size
    cx = int(width_cm * EMU_CM)
    cy = int(cx * h / w)
    if cy > max_h_cm * EMU_CM:
        cy = int(max_h_cm * EMU_CM)
        cx = int(cy * w / h)
    p = copy.deepcopy(M_FIG)
    rid = add_image(path)
    for e in p.iter(f"{{{WP}}}extent"):
        e.set("cx", str(cx)); e.set("cy", str(cy))
    for e in p.iter(f"{{{A}}}ext"):
        e.set("cx", str(cx)); e.set("cy", str(cy))
    for e in p.iter(f"{{{WP}}}docPr"):
        _docpr[0] += 1
        e.set("id", str(_docpr[0])); e.set("name", f"Picture {_docpr[0]}")
    for e in p.iter(f"{{{PIC}}}cNvPr"):
        e.set("name", os.path.basename(path))
    for e in p.iter(f"{{{A}}}blip"):
        e.set(f"{{{R}}}embed", rid)
    return p


# ---------------------------------------------------------------- tabelas novas
def border(tag, val, sz=None):
    b = etree.Element(q(tag))
    b.set(q("val"), val)
    if sz:
        b.set(q("sz"), str(sz)); b.set(q("space"), "0"); b.set(q("color"), "000000")
    return b


def make_table(header, rows, widths, style="grade", align=None):
    assert sum(widths) == 9072, sum(widths)
    align = align or ["left"] * len(widths)
    tbl = etree.Element(q("tbl"))
    tp = etree.SubElement(tbl, q("tblPr"))
    etree.SubElement(tp, q("tblW")).attrib.update({q("w"): "9072", q("type"): "dxa"})
    etree.SubElement(tp, q("jc")).set(q("val"), "center")
    etree.SubElement(tp, q("tblLayout")).set(q("type"), "fixed")
    lk = etree.SubElement(tp, q("tblLook"))
    lk.attrib.update({q("val"): "04A0", q("firstRow"): "1", q("lastRow"): "0", q("firstColumn"): "1",
                      q("lastColumn"): "0", q("noHBand"): "0", q("noVBand"): "1"})
    g = etree.SubElement(tbl, q("tblGrid"))
    for w in widths:
        etree.SubElement(g, q("gridCol")).set(q("w"), str(w))
    allrows = [header] + rows
    for i, row in enumerate(allrows):
        tr = etree.SubElement(tbl, q("tr"))
        trp = etree.SubElement(tr, q("trPr"))
        etree.SubElement(trp, q("cantSplit"))
        if i == 0:
            etree.SubElement(trp, q("tblHeader"))
        etree.SubElement(trp, q("jc")).set(q("val"), "center")
        last = i == len(allrows) - 1
        for j, (cell, w) in enumerate(zip(row, widths)):
            tc = etree.SubElement(tr, q("tc"))
            tcp = etree.SubElement(tc, q("tcPr"))
            etree.SubElement(tcp, q("tcW")).attrib.update({q("w"): str(w), q("type"): "dxa"})
            bd = etree.SubElement(tcp, q("tcBorders"))
            if style == "grade":
                for t in ("top", "left", "bottom", "right"):
                    bd.append(border(t, "single", 4))
            else:  # aberta (Tabela)
                top = ("single", 12) if i == 0 else ("nil", None)
                bot = ("single", 8) if i == 0 else (("single", 12) if last else ("nil", None))
                bd.append(border("top", *top)); bd.append(border("left", "nil"))
                bd.append(border("bottom", *bot)); bd.append(border("right", "nil"))
            for k, line in enumerate(str(cell).split("\n")):
                p = etree.SubElement(tc, q("p"))
                pp = etree.SubElement(p, q("pPr"))
                if not last:
                    etree.SubElement(pp, q("keepNext"))
                sp = etree.SubElement(pp, q("spacing"))
                sp.attrib.update({q("before"): "40", q("after"): "40", q("line"): "240", q("lineRule"): "auto"})
                etree.SubElement(pp, q("jc")).set(q("val"), "center" if i == 0 else align[j])
                base = sz20()
                if i == 0:
                    base.insert(0, etree.Element(q("b")))
                for r in runs_from(line, base):
                    p.append(r)
    return tbl


def copy_table(contains, fix=None):
    t = clean_ids(copy.deepcopy(find_tbl(contains)))
    if fix:
        for tt in t.iter(q("t")):
            for a, b in fix:
                if tt.text and a in tt.text:
                    tt.text = tt.text.replace(a, b)
    return t


# ---------------------------------------------------------------- montagem
import importlib  # noqa: E402
conteudo = importlib.import_module(os.environ.get('CONTEUDO', 'conteudo'))

blocks = conteudo.BLOCKS
# 1) numeração de figuras, quadros e tabelas na ordem do texto
KIND = {"fig": "Figura", "qd": "Quadro", "tab": "Tabela"}
num, count, captions = {}, {"fig": 0, "qd": 0, "tab": 0}, []
for b in blocks:
    if b[0] in ("fig", "table_new", "table_copy"):
        kind = "fig" if b[0] == "fig" else b[2]
        count[kind] += 1
        num[f"{kind}:{b[1]}"] = count[kind]


def resolve(s):
    def rep(m):
        k = m.group(1) + ":" + m.group(2)
        assert k in num, k
        return f"{KIND[m.group(1)]}{NB}{num[k]}" if False else f"{KIND[m.group(1)]} {num[k]}"
    s = re.sub(r"\{n:([a-z0-9_]+)\}", lambda m: str(num['fig:' + m.group(1)]), s)
    return re.sub(r"\{(fig|qd|tab):([a-z0-9_]+)\}", rep, s)


# 2) remove o corpo antigo (da introdução até antes do sectPr final)
intro = find_p("1 INTRODUÇÃO", 130)
i0 = ELS.index(intro)
sect = ELS[-1]
assert sect.tag == q("sectPr")
for e in ELS[i0:-1]:
    body.remove(e)

out = []
letters = "abcdefghijklmnopqrstuvwxyz"
for b in blocks:
    t = b[0]
    if t == "h1":
        out.append(para_h(1, b[1]))
    elif t == "h2":
        out.append(para_h(2, b[1]))
    elif t == "h3":
        out.append(para_h(3, b[1]))
    elif t == "p":
        out.append(para_body(resolve(b[1])))
    elif t == "copy":  # parágrafo do DOCX completo, com substituições
        src = find_p(b[1])
        s = to_markup(src)
        for a, c in (b[2] if len(b) > 2 else []):
            assert a in s, (a, s[:80])
            s = s.replace(a, c)
        out.append(para_body(resolve(s)))
    elif t == "ul":
        items = b[1]
        for k, it in enumerate(items):
            out.append(para_li(letters[k], resolve(it)))
    elif t == "fig":
        _, key, path, width, title, source = b[:6]
        maxh = b[6] if len(b) > 6 else 20.0
        out.append(para_caption(f"Figura {num['fig:' + key]} – {title}"))
        out.append(para_image(path, width, maxh))
        out.append(para_source(source))
    elif t in ("table_new", "table_copy"):
        _, key, kind, title = b[:4]
        out.append(para_caption(f"{KIND[kind]} {num[kind + ':' + key]} – {title}"))
        if t == "table_new":
            header, rows, widths, style, align, source = b[4:10]
            out.append(make_table(header, [[resolve(c) for c in r] for r in rows], widths, style, align))
        else:
            contains, fix, source = b[4:7]
            out.append(copy_table(contains, fix))
        out.append(para_source(resolve(source)))
    elif t == "ref_copy":
        out.append(clean_ids(copy.deepcopy(find_p(b[1]))))
    elif t == "ref_new":
        p = copy.deepcopy(M_REF)
        r0 = M_REF.find(q("r"))
        set_runs(p, b[1], copy.deepcopy(r0.find(q("rPr"))) if r0 is not None and r0.find(q("rPr")) is not None else None)
        out.append(p)
    elif t == "center":
        out.append(para_center(b[1], bold=b[2] if len(b) > 2 else False,
                               page_break=b[3] if len(b) > 3 else False, after=120))
    elif t == "img_page":
        p = para_image(b[1], b[2] if len(b) > 2 else 15.0, 22.5)
        ppr = p.find(q("pPr"))
        kn = ppr.find(q("keepNext"))
        if kn is not None:
            ppr.remove(kn)
        out.append(p)
    else:
        raise ValueError(t)
for e in out:
    if e.tag == q("tbl"):  # última linha presa à fonte
        for p_ in e.findall(q("tr"))[-1].iter(q("p")):
            ppr = p_.find(q("pPr"))
            if ppr is None:
                ppr = etree.Element(q("pPr")); p_.insert(0, ppr)
            if ppr.find(q("keepNext")) is None:
                ppr.insert(0, etree.Element(q("keepNext")))
for e in out:
    sect.addprevious(e)

# 3) pré-textuais: resumo/abstract, listas e siglas
for a, c in conteudo.PRE_REPLACE:
    hit = False
    for p in body.iter(q("p")):
        for tt in p.iter(q("t")):
            if tt.text and a in tt.text:
                tt.text = tt.text.replace(a, c); hit = True
    assert hit, a


def rebuild_list(first_prefix, last_prefix, kind):
    first = find_p(first_prefix)
    last = find_p(last_prefix)
    i, j = list(body).index(first), list(body).index(last)
    anchor = first.getprevious()
    for e in list(body)[i:j + 1]:
        body.remove(e)
    entries = [(n, title) for (n, title) in captions_of(kind)]
    for n, title in reversed(entries):
        p = copy.deepcopy(M_LIST_ENTRY)
        ts = p.findall(f".//{q('t')}")
        ts[0].text = f"{KIND[kind]} {n} –"
        ts[1].text = title
        ts[2].text = "0"
        anchor.addnext(p)


def captions_of(kind):
    res = []
    for b in blocks:
        if kind == "fig" and b[0] == "fig":
            res.append((num["fig:" + b[1]], b[4]))
        elif kind != "fig" and b[0] in ("table_new", "table_copy") and b[2] == kind:
            res.append((num[f"{kind}:{b[1]}"], b[3]))
    return res


rebuild_list("Figura 1 –Etapas", "Figura 13 –Tela de relatórios", "fig")
rebuild_list("Quadro 1 –Iterações", "Quadro 5 –Experimentos", "qd")
rebuild_list("Tabela 1 –Efeito", "Tabela 12 –Desempenho", "tab")

# siglas novas (ordem alfabética)
lista_ini = find_p("LISTA DE ABREVIATURAS E SIGLAS")
lista = []
e = lista_ini.getnext()
while e is not None and e.tag == q("p") and e.find(f".//{q('tab')}") is not None:
    lista.append(e); e = e.getnext()
keyf = lambda x: x.findall(f".//{q('t')}")[0].text.upper()
for sig, ext, por in conteudo.SIGLAS_NOVAS:
    p = copy.deepcopy(M_SIGLA)
    for c in [c for c in p if c.tag != q("pPr")]:
        p.remove(c)
    r = etree.SubElement(p, q("r")); etree.SubElement(r, q("t")).text = sig
    r = etree.SubElement(p, q("r")); etree.SubElement(r, q("tab"))
    txt = (f"⟨{ext}⟩" + (f" ({por})" if por else "")) if ext else por
    for rr in runs_from(txt):
        p.append(rr)
    maiores = [s_p for s_p in lista if keyf(s_p) > sig.upper()]
    (maiores[0].addprevious(p) if maiores else lista[-1].addnext(p))
    lista = [x for x in body if x in lista or x is p]

for sig in getattr(conteudo, "SIGLAS_REMOVER", []):
    for s_p in list(lista):
        if keyf(s_p) == sig.upper():
            body.remove(s_p)
pg = [e for e in sect.iter(q("pgNumType"))]
assert pg, "pgNumType"
pg[0].set(q("start"), str(conteudo.PG_START))
tree.write(DOC, xml_declaration=True, encoding="UTF-8", standalone=True)
rels_tree.write(RELS, xml_declaration=True, encoding="UTF-8", standalone=True)

# content types: jpg
CT = os.path.join(NOVO, "[Content_Types].xml")
ct = open(CT, encoding="utf-8").read()
if 'Extension="jpg"' not in ct:
    ct = ct.replace('<Default Extension="png"', '<Default Extension="jpg" ContentType="image/jpeg"/><Default Extension="png"')
open(CT, "w", encoding="utf-8").write(ct)

# estilo Sumário 3
ST = os.path.join(NOVO, "word", "styles.xml")
st = open(ST, encoding="utf-8").read()
if 'w:styleId="Sumrio3"' not in st:
    m = re.search(r'<w:style w:type="paragraph" w:styleId="Sumrio2">.*?</w:style>', st, re.S).group(0)
    m3 = m.replace('Sumrio2', 'Sumrio3').replace('toc 2', 'toc 3').replace('w:left="240"', 'w:left="480"')
    st = st.replace(m, m + m3)
    open(ST, "w", encoding="utf-8").write(st)
print("figuras", count, "blocos", len(blocks))
