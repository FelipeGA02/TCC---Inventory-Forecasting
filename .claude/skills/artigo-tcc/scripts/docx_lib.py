# -*- coding: utf-8 -*-
"""Edição cirúrgica do artigo do TCC (DOCX convertido de PDF) preservando a formatação.

Princípio: nunca recriar o documento. Todo parágrafo novo é CLONADO de um parágrafo existente
do mesmo tipo (corpo, espaçador, título de seção, legenda, fonte, referência, item de lista),
herdando o pPr original. Só o conteúdo dos runs é trocado.

Uso típico (script de edição em uma pasta temporária):

    from docx_lib import Doc
    d = Doc("work/word/document.xml")
    p = d.find(startswith="A previsão de demanda é um tema central")
    d.set_text(p, "Novo texto com [[itálico]] onde o autor usa itálico.")
    novo = d.clone(d.tpl_body(), "Parágrafo novo.")
    d.insert_after(p, d.clone(d.tpl_spacer()), novo)
    d.keep_captions_with_next()
    d.save("work/word/document.xml")

Marcação de itálico: [[texto]]. Use   (espaço não separável) em expressões como
"m = 7" ou "log(1 + y)" para não quebrarem no fim da linha.
"""
import copy
import random
import re

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
XML = "http://www.w3.org/XML/1998/namespace"
NBSP = " "


def q(tag):
    return "{%s}%s" % (W, tag)


def text_of(el):
    return "".join(t.text or "" for t in el.iter(q("t")))


def style_of(p):
    st = p.find(q("pPr") + "/" + q("pStyle"))
    return st.get(q("val")) if st is not None else None


class Doc:
    def __init__(self, xml_path, seed=None):
        self.path = xml_path
        self.tree = etree.parse(xml_path)
        self.root = self.tree.getroot()
        self.body = self.root.find(q("body"))
        self._rand = random.Random(seed)
        self._ids = set(self.root.xpath("//@w14:paraId", namespaces={"w14": W14}))
        bm = [int(x) for x in self.root.xpath("//w:bookmarkStart/@w:id", namespaces={"w": W}) if x.isdigit()]
        self._next_bm = max(bm + [900100]) + 1

    # ------------------------------------------------------------------ busca
    def paragraphs(self):
        """Parágrafos do corpo (inclui os de dentro de tabelas e do sumário)."""
        return list(self.body.iter(q("p")))

    def find_all(self, contains=None, startswith=None, style=None, top_level=True):
        cands = list(self.body) if top_level else self.paragraphs()
        out = []
        for p in cands:
            if etree.QName(p).localname != "p":
                continue
            t = text_of(p).strip()
            if contains is not None and contains not in t:
                continue
            if startswith is not None and not t.startswith(startswith):
                continue
            if style is not None and style_of(p) != style:
                continue
            out.append(p)
        return out

    def find(self, contains=None, startswith=None, style=None, top_level=True):
        """Exatamente um parágrafo; falha se houver zero ou mais de um (evita editar o lugar errado)."""
        r = self.find_all(contains, startswith, style, top_level)
        if len(r) != 1:
            raise LookupError("find(%r, %r, %r) encontrou %d parágrafos" % (contains, startswith, style, len(r)))
        return r[0]

    def find_table(self, caption_startswith):
        """Tabela que vem logo depois da legenda 'Tabela N – ...'."""
        cap = self.find(startswith=caption_startswith)
        nxt = cap.getnext()
        while nxt is not None and etree.QName(nxt).localname != "tbl":
            nxt = nxt.getnext()
        return nxt

    # ------------------------------------------------------- modelos (clonar)
    def tpl_body(self):
        return self.find(startswith="A previsão de demanda é um tema central")

    def tpl_spacer(self):
        return self.tpl_body().getnext()  # parágrafo vazio padrão entre parágrafos de corpo

    def tpl_section_end(self):
        """Último parágrafo de uma seção (espaçamento maior antes do próximo título)."""
        return self.find(startswith="O pipeline de dados está organizado em três camadas: (i)")

    def tpl_heading2(self):
        return self.find(startswith="Situação Atual", style="Ttulo2")

    def tpl_caption(self):
        return self.find(startswith="Tabela 2 –")

    def tpl_source(self):
        return self.find_all(startswith="Fonte: Elaborado pelos autores (2026).")[0]

    def tpl_reference(self):
        return self.find(startswith="MAKRIDAKIS, S.")

    # ------------------------------------------------------------- runs/texto
    def _new_pid(self):
        while True:
            v = "%08X" % self._rand.randint(0x10000000, 0x7FFFFFFF)
            if v not in self._ids:
                self._ids.add(v)
                return v

    @staticmethod
    def make_run(text, rpr=None, italic=False):
        r = etree.Element(q("r"))
        rp = copy.deepcopy(rpr) if rpr is not None else None
        if italic:
            if rp is None:
                rp = etree.Element(q("rPr"))
            if rp.find(q("i")) is None:
                i = etree.Element(q("i"))
                anchor = None
                for tag in ("bCs", "b", "rFonts", "rStyle"):  # ordem do schema
                    anchor = rp.find(q(tag))
                    if anchor is not None:
                        break
                if anchor is not None:
                    anchor.addnext(i)
                else:
                    rp.insert(0, i)
        elif rp is not None and rp.find(q("i")) is not None:
            rp.remove(rp.find(q("i")))
        if rp is not None and len(rp):
            r.append(rp)
        t = etree.SubElement(r, q("t"))
        t.text = text
        t.set("{%s}space" % XML, "preserve")
        return r

    def runs_from_markup(self, text, rpr=None):
        out = []
        for part in re.split(r"(\[\[.*?\]\])", text):
            if not part:
                continue
            if part.startswith("[["):
                out.append(self.make_run(part[2:-2], rpr, italic=True))
            else:
                out.append(self.make_run(part, rpr, italic=False))
        return out

    @staticmethod
    def base_rpr(p):
        """rPr do primeiro run não itálico (tamanho de fonte de tabela/legenda, negrito de título)."""
        for r in p.iter(q("r")):
            rp = r.find(q("rPr"))
            if rp is None or rp.find(q("i")) is None:
                return copy.deepcopy(rp) if rp is not None else None
        return None

    def set_text(self, p, text, rpr="auto", trailing=" "):
        """Troca o conteúdo mantendo pPr, bookmarks e quebras de página (w:br type=page).

        rpr="auto" herda a formatação do primeiro run não itálico; passe rpr=None para texto de
        corpo puro (evita herdar um rPr acidental). O espaço final imita o padrão da conversão.
        """
        if rpr == "auto":
            rpr = self.base_rpr(p)
        had_pb = any(br.get(q("type")) == "page" for br in p.iter(q("br")))
        starts, ends = [], []
        for ch in list(p):
            tag = etree.QName(ch).localname
            if tag == "pPr":
                continue
            if tag == "bookmarkStart":
                starts.append(ch)
            elif tag == "bookmarkEnd":
                ends.append(ch)
            p.remove(ch)
        for b in starts:
            p.append(b)
        for r in self.runs_from_markup(text + trailing, rpr):
            p.append(r)
        if had_pb:
            br_run = etree.SubElement(p, q("r"))
            etree.SubElement(br_run, q("br")).set(q("type"), "page")
        for b in ends:
            p.append(b)
        return p

    def clone(self, template, text=None, rpr="auto", trailing=" ", keep_page_breaks=False):
        """Cópia do parágrafo-modelo, sem bookmarks, com novo paraId e (opcionalmente) novo texto."""
        p = copy.deepcopy(template)
        p.set("{%s}paraId" % W14, self._new_pid())
        for b in p.findall(q("bookmarkStart")) + p.findall(q("bookmarkEnd")):
            p.remove(b)
        if not keep_page_breaks:
            for br in list(p.iter(q("br"))):
                if br.get(q("type")) == "page":
                    br.getparent().remove(br)
        if text is not None:
            self.set_text(p, text, rpr=self.base_rpr(template) if rpr == "auto" else rpr, trailing=trailing)
        return p

    # ------------------------------------------------------------ estrutura
    @staticmethod
    def insert_after(anchor, *els):
        cur = anchor
        for el in els:
            cur.addnext(el)
            cur = el
        return cur

    @staticmethod
    def insert_before(anchor, *els):
        for el in els:
            anchor.addprevious(el)

    @staticmethod
    def remove(*els):
        for el in els:
            el.getparent().remove(el)

    @staticmethod
    def _ppr(p):
        ppr = p.find(q("pPr"))
        if ppr is None:
            ppr = etree.Element(q("pPr"))
            p.insert(0, ppr)
        return ppr

    def set_spacing_after(self, p, val):
        ppr = self._ppr(p)
        sp = ppr.find(q("spacing"))
        if sp is None:
            sp = etree.Element(q("spacing"))
            ind = ppr.find(q("ind"))
            if ind is not None:
                ind.addprevious(sp)
            else:
                ppr.append(sp)
        sp.set(q("after"), str(val))

    def remove_spacing(self, p):
        ppr = self._ppr(p)
        sp = ppr.find(q("spacing"))
        if sp is not None:
            ppr.remove(sp)

    def _insert_ppr_flag(self, p, tag):
        ppr = self._ppr(p)
        if ppr.find(q(tag)) is not None:
            return
        el = etree.Element(q(tag))
        order = ["pStyle", "keepNext", "keepLines", "pageBreakBefore"]
        anchor = None
        for t in reversed(order[: order.index(tag)]):
            anchor = ppr.find(q(t))
            if anchor is not None:
                break
        if anchor is not None:
            anchor.addnext(el)
        else:
            ppr.insert(0, el)

    def add_page_break_before(self, p):
        self._insert_ppr_flag(p, "pageBreakBefore")

    def keep_with_next(self, p):
        self._insert_ppr_flag(p, "keepNext")

    def keep_captions_with_next(self):
        """Legendas 'Figura N –'/'Tabela N –' e parágrafos de imagem ficam com o elemento seguinte."""
        cap_re = re.compile(r"^(Figura|Tabela) \d+ –")
        for p in self.body.iter(q("p")):
            if cap_re.match(text_of(p).strip()) or p.find(".//" + q("drawing")) is not None:
                self.keep_with_next(p)

    def add_bookmark(self, p, name):
        bid = self._next_bm
        self._next_bm += 1
        bs = etree.Element(q("bookmarkStart"))
        bs.set(q("id"), str(bid))
        bs.set(q("name"), name)
        be = etree.Element(q("bookmarkEnd"))
        be.set(q("id"), str(bid))
        ppr = p.find(q("pPr"))
        if ppr is not None:
            ppr.addnext(bs)
        else:
            p.insert(0, bs)
        p.append(be)
        return name

    def renumber(self, p, old, new):
        """Troca 'Figura 12' por 'Figura 11' etc. Falha se o texto estiver partido entre runs."""
        hit = False
        for t in p.iter(q("t")):
            if t.text and old in t.text:
                t.text = t.text.replace(old, new)
                hit = True
        if not hit and old in text_of(p):
            raise ValueError("'%s' está partido entre runs; use set_text no parágrafo inteiro" % old)
        return hit

    # --------------------------------------------------------------- tabelas
    def set_cell_text(self, tc, text):
        ps = tc.findall(q("p"))
        for extra in ps[1:]:
            tc.remove(extra)
        self.set_text(ps[0], text, rpr=self.base_rpr(ps[0]))

    @staticmethod
    def rows(tbl):
        return tbl.findall(q("tr"))

    @staticmethod
    def cells(tr):
        return tr.findall(q("tc"))

    def clone_row(self, tr):
        new = copy.deepcopy(tr)
        new.set("{%s}paraId" % W14, self._new_pid())
        for p in new.iter(q("p")):
            p.set("{%s}paraId" % W14, self._new_pid())
        return new

    # --------------------------------------------------------------- sumário
    def toc_entries(self):
        """Entradas do sumário (estilos Sumrio1/Sumrio2), dentro e fora do campo TOC."""
        return [p for p in self.body.iter(q("p")) if (style_of(p) or "").startswith("Sumrio")]

    def toc_find(self, label_startswith):
        r = [p for p in self.toc_entries() if text_of(p).startswith(label_startswith)]
        if len(r) != 1:
            raise LookupError("entrada de sumário %r: %d encontradas" % (label_startswith, len(r)))
        return r[0]

    @staticmethod
    def toc_set(entry, label, anchor=None):
        hl = entry.find(q("hyperlink"))
        hl.find(q("r")).find(q("t")).text = label
        if anchor:
            hl.set(q("anchor"), anchor)
            for it in hl.iter(q("instrText")):
                it.text = "PAGEREF %s \\h" % anchor

    def toc_add_after(self, existing_entry, label, anchor):
        """Nova entrada (mesmo nível da existente) apontando para o bookmark `anchor` do título."""
        e = copy.deepcopy(existing_entry)
        e.set("{%s}paraId" % W14, self._new_pid())
        # entradas copiadas da 1a linha do campo TOC carregariam o início do campo: proibido
        if e.find(".//" + q("instrText")) is not None and "TOC" in "".join(
                x.text or "" for x in e.iter(q("instrText"))):
            raise ValueError("não clone a primeira entrada do sumário (contém o início do campo TOC)")
        for fc in e.findall(q("r")):  # remove um eventual fim do campo TOC herdado
            if fc.find(q("fldChar")) is not None:
                e.remove(fc)
        self.toc_set(e, label, anchor)
        existing_entry.addnext(e)
        return e

    # -------------------------------------------------------------- salvar
    def save(self, path=None):
        self.tree.write(path or self.path, xml_declaration=True, encoding="UTF-8", standalone=True)
