# -*- coding: utf-8 -*-
"""Apêndice B: atas das reuniões 05–08 (out.–nov./2026) como imagens das páginas."""
import copy, glob, os, re, shutil, sys
sys.path.insert(0, sys.argv[2])
from docx_lib import Doc, q, text_of, W  # noqa
from lxml import etree

WORK = sys.argv[1]; ATAS = sys.argv[3]
d = Doc(os.path.join(WORK, "word/document.xml"), seed=20261121)

# 1) Remissão em 6.2
p = d.find(startswith="Os requisitos foram levantados em oito reuniões remotas")
old = "com a pauta, as decisões, as solicitações do cliente e as pendências."
new = ("com a pauta, as decisões, as solicitações do cliente e as pendências, e as atas das quatro "
       "reuniões realizadas em outubro e novembro de 2026 estão reproduzidas no Apêndice B.")
assert d.replace_text(old, new, top_level=True) == 1

# 2) Título, introdução e atas, antes do ANEXO A
anexo = d.find(startswith="ANEXO A – TELAS", style="Ttulo1")
apA = d.find(startswith="APÊNDICE A – ESPECIFICAÇÃO", style="Ttulo1")
h = d.clone(apA, "APÊNDICE B – ATAS DAS REUNIÕES COM A ENTIDADE PARCEIRA", rpr=d.base_rpr(apA), trailing="")
d.add_bookmark(h, "_Toc900020")
intro_tpl = d.find(startswith="As telas a seguir foram compartilhadas pela entidade parceira")
intro = d.clone(intro_tpl,
    "As atas a seguir registram, no Formulário de Registro de Reuniões com Entidade fornecido pela "
    "instituição, as quatro reuniões com a entidade parceira realizadas entre outubro e novembro de "
    "2026, pela plataforma Google Meet. A reunião de 13 de outubro apresentou o painel de vendas por "
    "unidade e o envio e a conferência das planilhas e validou a classificação dos produtos em "
    "categorias; a de 20 de outubro apresentou a previsão diária e o histórico das previsões, validou "
    "o tratamento das encomendas grandes e definiu o nível de detalhe da previsão; a de 3 de novembro "
    "tratou da publicação do sistema e da atualização dos dados e validou o funcionamento das lojas "
    "nos feriados e nas datas comemorativas; e a de 10 de novembro apresentou o sistema finalizado e "
    "validou o seu uso pela loja.")
elems = [h, intro]

img_tpl = None
for pp in d.body.iter(q("p")):
    if pp.find(".//" + q("drawing")) is not None and "Picture 3014" in etree.tostring(pp, encoding="unicode"):
        img_tpl = pp
assert img_tpl is not None
cap_tpl = d.find(startswith="Figura 14 – Filtro do relatório")

# relações
rels_path = os.path.join(WORK, "word/_rels/document.xml.rels")
rels = etree.parse(rels_path); rroot = rels.getroot()
RNS = "http://schemas.openxmlformats.org/package/2006/relationships"
IMG_T = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
used = {int(r.get("Id")[3:]) for r in rroot if r.get("Id", "").startswith("rId") and r.get("Id")[3:].isdigit()}
nid = max(used) + 1
docpr = max(int(x) for x in d.root.xpath("//wp:docPr/@id", namespaces={"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"})) + 1
media = os.path.join(WORK, "word/media")
NSR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
from PIL import Image
CY = 8100000  # 22,5 cm de altura
datas = {"05": "13 de outubro de 2026", "06": "20 de outubro de 2026",
         "07": "3 de novembro de 2026", "08": "10 de novembro de 2026"}
img_paras = []
for n in ["05", "06", "07", "08"]:
    lab = d.clone(cap_tpl, "Ata da reunião %s – %s" % (n, datas[n]))
    elems.append(lab)
    pages = sorted(glob.glob(os.path.join(ATAS, "ata%s_p*.png" % n)), key=lambda s: int(re.search(r"_p(\d+)", s).group(1)))
    for f in pages:
        w, hh = Image.open(f).size
        cx = int(round(CY * w / hh))
        fname = "ata%s_%s" % (n, os.path.basename(f).split("_")[1])
        shutil.copy(f, os.path.join(media, fname))
        rid = "rId%d" % nid; nid += 1
        r = etree.SubElement(rroot, "{%s}Relationship" % RNS); r.set("Id", rid); r.set("Type", IMG_T); r.set("Target", "media/" + fname)
        ip = copy.deepcopy(img_tpl)
        ip.set("{http://schemas.microsoft.com/office/word/2010/wordml}paraId", d._new_pid())
        for e in ip.iter("{%s}extent" % WP): e.set("cx", str(cx)); e.set("cy", str(CY))
        for e in ip.iter("{%s}ext" % A): e.set("cx", str(cx)); e.set("cy", str(CY))
        for e in ip.iter("{%s}docPr" % WP): e.set("id", str(docpr)); e.set("name", "Picture %d" % docpr)
        docpr += 1
        for e in ip.iter("{%s}cNvPr" % PIC): e.set("name", fname)
        for e in ip.iter("{%s}blip" % A): e.set("{%s}embed" % NSR, rid)
        inl = ip.find(".//{%s}inline" % WP)
        for k in list(inl.attrib):
            if "anchorId" in k or "editId" in k: del inl.attrib[k]
        elems.append(ip); img_paras.append(ip)

d.insert_before(anexo, *elems)

# 3) Sumário
e = d.toc_find("APÊNDICE A")
d.toc_add_after(e, "APÊNDICE B – ATAS DAS REUNIÕES COM A ENTIDADE PARCEIRA", "_Toc900020")

d.keep_captions_with_next()
# as páginas das atas não ficam presas umas às outras (cada uma ocupa uma folha)
for ip in img_paras:
    ppr = ip.find(q("pPr"))
    for kn in ppr.findall(q("keepNext")): ppr.remove(kn)
d.save()
rels.write(rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)
print("ok", len(img_paras), "páginas")
