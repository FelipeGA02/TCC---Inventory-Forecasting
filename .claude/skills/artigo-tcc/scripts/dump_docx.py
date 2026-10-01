# -*- coding: utf-8 -*-
"""Lista os elementos do corpo do artigo, um por linha: índice, estilo, marcadores e texto.

    python dump_docx.py "docs/project/TCC2 - Inicial.docx" > dump.txt
    python dump_docx.py work/word/document.xml > dump.txt

Marcadores: [DRAWING] figura, [SECT] quebra de seção, [PB] quebra de página no parágrafo,
[KN] keepNext, [PBB] pageBreakBefore. Tabelas aparecem como T<n> com uma linha por linha da tabela.
Sempre grave a saída em arquivo e leia com a ferramenta Read (o console do Windows estraga acentos).
"""
import io
import sys
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ns = {"w": W}
sys.stdout.reconfigure(encoding="utf-8")


def load(path):
    if path.lower().endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            return etree.parse(io.BytesIO(z.read("word/document.xml")))
    return etree.parse(path)


def ptext(p):
    out = []
    for el in p.iter():
        tag = etree.QName(el).localname
        if tag == "t":
            out.append(el.text or "")
        elif tag == "tab":
            out.append("\t")
        elif tag == "br" and el.get("{%s}type" % W) == "page":
            out.append("[PB]")
    return "".join(out)


body = load(sys.argv[1]).getroot().find("w:body", ns)
for i, child in enumerate(body):
    tag = etree.QName(child).localname
    if tag == "p":
        st = child.find("w:pPr/w:pStyle", ns)
        s = st.get("{%s}val" % W) if st is not None else "-"
        marks = ""
        if child.findall(".//w:drawing", ns):
            marks += "[DRAWING]"
        if child.find("w:pPr/w:sectPr", ns) is not None:
            marks += "[SECT]"
        if child.find("w:pPr/w:keepNext", ns) is not None:
            marks += "[KN]"
        if child.find("w:pPr/w:pageBreakBefore", ns) is not None:
            marks += "[PBB]"
        print(f"P{i}\t{s}\t{marks}\t{ptext(child)}")
    elif tag == "tbl":
        rows = child.findall("w:tr", ns)
        print(f"T{i}\tTABLE rows={len(rows)}")
        for r in rows:
            print("   | " + " | ".join(ptext(c).replace("\n", " ") for c in r.findall("w:tc", ns)))
    elif tag == "sdt":
        print(f"X{i}\tSUMÁRIO (campo TOC)")
        for p in child.iter("{%s}p" % W):
            print("   ~ " + ptext(p))
    else:
        print(f"X{i}\t{tag}")
