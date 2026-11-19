# -*- coding: utf-8 -*-
"""Aplica ao TCC2 - Relatorio Tecnico - Final.docx (desempacotado) as correções do orientador
(PDF COMENTÁRIOS, 18/11/2026) e troca as telas das Figuras 9 a 13.

    python editar.py <work> <pasta-das-capturas>
"""
import copy
import os
import re
import sys

from lxml import etree
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
WORK, SHOTS = sys.argv[1], sys.argv[2]
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
XML = "http://www.w3.org/XML/1998/namespace"
q = lambda t: f"{{{W}}}{t}"
mq = lambda t: f"{{{M}}}{t}"
NB = " "

DOC = os.path.join(WORK, "word", "document.xml")
tree = etree.parse(DOC)
body = tree.getroot().find(q("body"))


def paras():
    return [p for p in body.iter(q("p"))]


def ptext(p):
    return "".join(t.text or "" for t in p.iter(q("t")))


def norm(s):
    return s.replace(NB, " ")


def find(sub, startswith=False):
    """Parágrafo único que contém `sub` (espaço inseparável conta como espaço)."""
    hits = [p for p in paras() if (norm(ptext(p)).startswith(norm(sub)) if startswith else norm(sub) in norm(ptext(p)))]
    if len(hits) != 1:
        raise SystemExit(f"esperava 1 parágrafo com {sub!r}, achei {len(hits)}")
    return hits[0]


def runs_t(p):
    return [t for t in p.iter(q("t"))]


def replace(old, new, p=None):
    """Troca `old` por `new` dentro de um parágrafo, entre runs; o texto novo herda a
    formatação do run em que `old` começa."""
    p = p if p is not None else find(old)
    ts = runs_t(p)
    full = norm("".join(t.text or "" for t in ts))
    i = full.find(norm(old))
    if i < 0 or full.find(norm(old), i + 1) >= 0:
        raise SystemExit(f"{old!r}: ocorrência não única no parágrafo")
    j = i + len(old)
    pos = 0
    first = True
    for t in ts:
        s = t.text or ""
        a, b = pos, pos + len(s)
        pos = b
        if b <= i or a >= j:
            continue
        lo, hi = max(i, a) - a, min(j, b) - a
        if first:
            t.text = s[:lo] + new + s[hi:]
            first = False
        else:
            t.text = s[:lo] + s[hi:]
        t.set(f"{{{XML}}}space", "preserve")
    return p


def rpr_base(p):
    r = p.find(q("r"))
    rp = r.find(q("rPr")) if r is not None else None
    rp = copy.deepcopy(rp) if rp is not None else etree.Element(q("rPr"))
    for x in rp.findall(q("i")) + rp.findall(q("iCs")):
        rp.remove(x)
    return rp


ORDEM = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
         "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
         "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
         "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath"]


def make_run(text, rpr, italic=False):
    r = etree.Element(q("r"))
    rp = copy.deepcopy(rpr)
    if italic:
        rp.append(etree.Element(q("i")))
        kids = sorted(rp, key=lambda e: ORDEM.index(etree.QName(e).localname) if etree.QName(e).localname in ORDEM else 99)
        for k in list(rp):
            rp.remove(k)
        for k in kids:
            rp.append(k)
    if len(rp):
        r.append(rp)
    t = etree.SubElement(r, q("t"))
    t.text = text
    t.set(f"{{{XML}}}space", "preserve")
    return r


def set_text(p, text, rpr=None):
    """Reescreve o parágrafo mantendo pPr e bookmarks; [[...]] = itálico."""
    rpr = rpr if rpr is not None else rpr_base(p)
    for r in p.findall(q("r")) + p.findall(q("hyperlink")):
        p.remove(r)
    for k, seg in enumerate(re.split(r"\[\[|\]\]", text)):
        if seg:
            p.append(make_run(seg, rpr, italic=k % 2 == 1))
    return p


def clone_after(model, ref, text=None):
    new = copy.deepcopy(model)
    for b in new.findall(q("bookmarkStart")) + new.findall(q("bookmarkEnd")):
        new.remove(b)
    for x in new.iter(q("lastRenderedPageBreak")):
        x.getparent().remove(x)
    ref.addnext(new)
    if text is not None:
        set_text(new, text, rpr_base(model))
    return new


def split(p, at):
    """Divide o parágrafo: o trecho a partir de `at` vira um parágrafo novo, logo abaixo."""
    full = norm(ptext(p))
    k = full.find(norm(at))
    assert k > 0 and full.find(norm(at), k + 1) < 0, at
    new = copy.deepcopy(p)
    for b in new.findall(q("bookmarkStart")) + new.findall(q("bookmarkEnd")):
        new.remove(b)
    for x in new.iter(q("lastRenderedPageBreak")):
        x.getparent().remove(x)

    def corta(par, ini, fim):
        pos = 0
        for t in runs_t(par):
            s = t.text or ""
            a, b = pos, pos + len(s)
            pos = b
            lo, hi = max(ini, a) - a, min(fim, b) - a
            t.text = s[lo:hi] if hi > lo else ""
            t.set(f"{{{XML}}}space", "preserve")
        for r in par.findall(q("r")):
            if all(not (t.text or "") for t in r.findall(q("t"))) and r.find(q("t")) is not None:
                par.remove(r)

    corta(p, 0, k)
    corta(new, k, len(full))
    ts = runs_t(p)
    if ts:
        ts[-1].text = ts[-1].text.rstrip()
    p.addnext(new)
    return new


# ---------------------------------------------------------------- OMML (equações)
def m(tag, *kids, **attrs):
    e = etree.Element(mq(tag))
    for k, v in attrs.items():
        e.set(mq(k), v)
    for c in kids:
        if c is not None:
            e.append(c)
    return e


def mr(text, plain=False):
    r = m("r")
    if plain:
        r.append(m("rPr", m("sty", val="p")))
    t = etree.SubElement(r, mq("t"))
    t.text = text
    t.set(f"{{{XML}}}space", "preserve")
    return r


def e_(*kids):
    return m("e", *kids)


def sub(base, s):
    return m("sSub", e_(*base), m("sub", *s))


def sup(base, s):
    return m("sSup", e_(*base), m("sup", *s))


def subsup(base, s, u):
    return m("sSubSup", e_(*base), m("sub", *s), m("sup", *u))


def frac(n, d):
    return m("f", m("num", *n), m("den", *d))


def soma(lo, hi, corpo):
    return m("nary", m("naryPr", m("chr", val="∑"), m("limLoc", val="undOvr")), m("sub", *lo), m("sup", *hi), e_(*corpo))


def raiz(*corpo):
    return m("rad", m("radPr", m("degHide", val="1")), m("deg"), e_(*corpo))


def barra(*corpo):
    return m("bar", m("barPr", m("pos", val="top")), e_(*corpo))


def chapeu(*corpo):
    return m("acc", m("accPr", m("chr", val="̂")), e_(*corpo))


def parens(*corpo):
    return m("d", e_(*corpo))


def modulo(*corpo):
    return m("d", m("dPr", m("begChr", val="|"), m("endChr", val="|")), e_(*corpo))


def omath(*kids):
    return m("oMath", *kids)


XBAR = lambda: barra(mr("x"))
XI = lambda: sub([mr("x")], [mr("i")])

EQ1 = omath(XBAR(), mr("="), frac([mr("1")], [mr("n")]), soma([mr("i=1")], [mr("n")], [XI()]))
EQ2 = omath(mr("s"), mr("="), raiz(frac([mr("1")], [mr("n−1")]),
                                   soma([mr("i=1")], [mr("n")], [sup([parens(XI(), mr("−"), XBAR())], [mr("2")])])))
EQ3 = omath(mr("L"), mr("="), XBAR(), mr("+"), mr("4"), mr("s"))
EQ4 = omath(mr("MASE", plain=True), mr("="), frac(
    [frac([mr("1")], [mr("h")]), soma([mr("t=1")], [mr("h")], [modulo(sub([mr("y")], [mr("t")]), mr("−"), sub([chapeu(mr("y"))], [mr("t")]))])],
    [frac([mr("1")], [mr("n−m")]), soma([mr("t=m+1")], [mr("n")], [modulo(sub([mr("y")], [mr("t")]), mr("−"), sub([mr("y")], [mr("t−m")]))])]))


def inline(*kids):
    return omath(*kids)


def eq_paragraph(after, eq, numero):
    """Equação centralizada com o número à direita, entre parênteses."""
    p = etree.Element(q("p"))
    ppr = etree.SubElement(p, q("pPr"))
    sp = etree.SubElement(ppr, q("spacing"))
    sp.set(q("before"), "120")
    sp.set(q("after"), "120")
    ind = etree.SubElement(ppr, q("ind"))
    ind.set(q("firstLine"), "0")
    jc = etree.SubElement(ppr, q("jc"))
    jc.set(q("val"), "center")
    # equação em modo de exibição; "#(n)" num eqArr é a numeração à direita do próprio Word
    kids = list(eq)
    arr = m("eqArr", m("eqArrPr", m("maxDist", val="1"), m("ctrlPr")), e_(*kids, mr("#"), parens(mr(str(numero), plain=True))))
    para = m("oMathPara", m("oMathParaPr", m("jc", val="center")), omath(arr))
    p.append(para)
    after.addnext(p)
    return p


def mixed_paragraph(model, after, partes, sem_recuo=False):
    """Parágrafo de corpo com trechos de texto e de equação em linha."""
    p = clone_after(model, after, "")
    for r in p.findall(q("r")):
        p.remove(r)
    if sem_recuo:
        ppr = p.find(q("pPr"))
        ind = ppr.find(q("ind"))
        if ind is None:
            ind = etree.SubElement(ppr, q("ind"))
        ind.set(q("firstLine"), "0")
    rpr = rpr_base(model)
    for parte in partes:
        if isinstance(parte, str):
            for k, seg in enumerate(re.split(r"\[\[|\]\]", parte)):
                if seg:
                    p.append(make_run(seg, rpr, italic=k % 2 == 1))
        else:
            p.append(parte)
    return p


# ================================================================ correções
# Folha de rosto
replace("Relatório técnico apresentado ao Curso", "Trabalho de Conclusão de Curso apresentado ao Curso")

# Resumo
RESUMO = ("A Floricultura Verde Perto, com unidades em Jardim Canadá e em Itabirito, em Minas Gerais, comercializa "
          "produtos perecíveis cuja demanda varia com o dia da semana e com as datas comemorativas, e planejava as "
          "compras apenas com base na experiência da equipe, sem estimativas quantitativas das vendas. Este trabalho "
          "teve como objetivo desenvolver um sistema de previsão de vendas que fornecesse a previsão diária da demanda "
          "de cada categoria de produto e de cada produto de grama das duas unidades, a partir do histórico de vendas "
          "de janeiro de 2024 a fevereiro de 2026. Foi desenvolvido um sistema web, com um painel ([[dashboard]]) "
          "acessível pelo navegador, no qual a empresa envia as planilhas de vendas, solicita o treinamento dos "
          "modelos e consulta a previsão diária, em horizontes de duas semanas a três meses, o histórico das "
          "previsões e relatórios exportáveis. A solução contempla a preparação dos dados, a separação das "
          "encomendas grandes e o treinamento de modelos regressores SARIMAX com variáveis exógenas de calendário, "
          "cuja configuração resultou de uma sequência de experimentos avaliados por validação [[walk-forward]]. Na "
          "solução definitiva, validada nas oito semanas mais recentes do histórico, a métrica de erro MASE, que "
          "compara o erro do modelo com o de uma previsão ingênua que repete as vendas da semana anterior, ficou "
          "abaixo de 1, isto é, o modelo errou menos do que essa referência, em 19 das 23 séries com previsão, que "
          "reúnem as oito séries de categoria e 11 dos 15 produtos de grama, e a cobertura do intervalo de predição "
          "de 95%, que é a proporção dos dias em que a venda real ficou dentro da faixa prevista, variou de 91% a 100%.")
set_text(find("Este trabalho apresenta o desenvolvimento e a avaliação", startswith=True), RESUMO)
replace("Séries temporais. Modelos regressores. Floricultura.",
        "Previsão de séries temporais. Modelos regressores. Varejo de floricultura.")

ABSTRACT = ("Floricultura Verde Perto, with stores in Jardim Canadá and Itabirito, in Minas Gerais, Brazil, sells "
            "perishable products whose demand varies with the day of the week and with commemorative dates, and "
            "planned its purchases based only on the staff's experience, without quantitative sales estimates. This "
            "work aimed to develop a sales forecasting system providing the daily demand forecast for each product "
            "category and each grass product of the two stores, based on the sales history from January 2024 to "
            "February 2026. A web system was developed, with a dashboard accessed through the browser, in which the "
            "company uploads its sales spreadsheets, requests model training, and consults the daily forecast, with "
            "horizons from two weeks to three months, the forecast history, and exportable reports. The solution "
            "includes data preparation, separating large orders, and training SARIMAX regressor models with "
            "exogenous calendar variables, whose configuration resulted from a sequence of experiments evaluated by "
            "walk-forward validation. In the final solution, validated over the eight most recent weeks of "
            "historical data, the MASE error metric, which compares the model error with that of a naive forecast "
            "that repeats the previous week's sales, remained below 1, meaning that the model erred less than this "
            "benchmark, in 19 of the 23 forecasted series, which comprise the eight category series and 11 of the 15 "
            "grass products, and the 95% prediction-interval coverage, the share of days on which actual sales fell "
            "within the forecast range, ranged from 91% to 100%.")
set_text(find("This paper presents the development and evaluation", startswith=True), ABSTRACT)
replace("Time series. Regressor models. Floriculture.", "Time series forecasting. Regressor models. Floriculture retail.")

# Listas de figuras, quadros e tabelas: sem o espaço (tabulação) entre o número e o título;
# indicação do Anexo A e do Apêndice A. As páginas são refeitas depois da paginação do Word.
ANEXO = {"Figura 14": "Anexo A – ", "Figura 15": "Anexo A – ", "Quadro 8": "Apêndice A – "}
n_lista = 0
for p in paras():
    rs = p.findall(q("r"))
    if len(rs) < 3:
        continue
    t0 = rs[0].find(q("t"))
    mt = re.fullmatch(r"(Figura|Quadro|Tabela) (\d+) –", (t0.text or "").strip()) if t0 is not None else None
    if not mt or rs[1].find(q("tab")) is None:
        continue
    rs[1].remove(rs[1].find(q("tab")))
    t0.text = t0.text.strip() + " "
    t0.set(f"{{{XML}}}space", "preserve")
    t1 = rs[1].find(q("t"))
    t1.text = ANEXO.get(f"{mt.group(1)} {mt.group(2)}", "") + t1.text
    n_lista += 1
print("entradas das listas:", n_lista)

# 1 Introdução: período confuso
replace("A gestora de compras envia as planilhas exportadas do sistema de gestão, confere-as antes da gravação e "
        "solicita o treinamento dos modelos, e o sistema apresenta, em um painel acessível pelo navegador,",
        "No sistema, a gestora de compras envia e confere as planilhas de vendas e solicita o treinamento dos "
        "modelos. O sistema, então, apresenta, em um painel acessível pelo navegador,")

# Listas em itens: ";" no fim de cada item, exceto o último
n_itens = 0
for p in paras():
    rs = p.findall(q("r"))
    t0 = rs[0].find(q("t")) if rs else None
    if t0 is None or not re.fullmatch(r"[a-z]\)", (t0.text or "").strip()):
        continue
    ts = runs_t(p)
    if ts[-1].text.rstrip().endswith(","):
        ts[-1].text = ts[-1].text.rstrip()[:-1] + ";"
        n_itens += 1
print("itens com ponto e vírgula:", n_itens)

# 5 Referencial teórico
replace("Este capítulo apresenta, nas Seções 5.1 a 5.6, a fundamentação teórica sobre o problema e sobre a solução e, "
        "na Seção 5.7, as soluções correlatas,",
        "Este capítulo apresenta a fundamentação teórica sobre o problema e as soluções correlatas,")
# 5.3 série esparsa
replace("Quando as séries de vendas dos produtos são esparsas, uma alternativa",
        "Quando as séries de vendas dos produtos são esparsas, isto é, quando a maior parte dos dias não registra "
        "venda e as vendas ocorrem de forma esporádica e em quantidades variáveis, uma alternativa")

# 5.4 fórmulas da média, do desvio-padrão e do limiar
p54 = find("Para identificar essas ocorrências, foi utilizado um critério", startswith=True)
resto54 = split(p54, "Essas observações foram removidas")
replace("(IGLEWICZ; HOAGLIN, 1993).", "(IGLEWICZ; HOAGLIN, 1993). A média e o desvio-padrão das quantidades dos "
        "pedidos são calculados pelas Equações 1 e 2, e o limiar de cada loja, pela Equação 3:", p54)
e1 = eq_paragraph(p54, EQ1, 1)
e2 = eq_paragraph(e1, EQ2, 2)
e3 = eq_paragraph(e2, EQ3, 3)
emq = mixed_paragraph(p54, e3, [
    "em que ", inline(sub([mr("x")], [mr("i")])), " é a quantidade do pedido ", inline(mr("i")), ", ",
    inline(mr("n")), " é o número de pedidos da loja, ", inline(barra(mr("x"))), " é a média, ", inline(mr("s")),
    " é o desvio-padrão e ", inline(mr("L")), " é o limiar acima do qual o pedido é considerado atípico. ",
    ptext(resto54).strip()], sem_recuo=True)
resto54.getparent().remove(resto54)

# 5.5 fórmula do MASE
p55 = find("A avaliação das previsões utiliza métricas", startswith=True)
resto55 = split(p55, "Valores inferiores a 1 indicam")
replace("baseada no histórico de treinamento.", "baseada no histórico de treinamento, conforme a Equação 4:", p55)
e4 = eq_paragraph(p55, EQ4, 4)
mixed_paragraph(p55, e4, [
    "em que ", inline(sub([mr("y")], [mr("t")])), " é a venda observada no dia ", inline(mr("t")), ", ",
    inline(sub([chapeu(mr("y"))], [mr("t")])), " é a venda prevista, ", inline(mr("h")),
    " é o número de dias previstos, ", inline(mr("n")), " é o número de dias do histórico de treinamento e ",
    inline(mr("m")), " é o período sazonal, igual a 7 dias, de modo que o denominador corresponde ao erro médio de "
    "uma previsão ingênua que repete a venda da semana anterior. ", ptext(resto55).strip()], sem_recuo=True)
resto55.getparent().remove(resto55)

# 6 Metodologias: sem a remissão ao Capítulo 11
replace(" Os resultados dos testes e dos experimentos são apresentados no Capítulo 11.", "")
# 8 Modelagem
replace(", construída a partir dos requisitos do Capítulo 7:", ":")

# 10.2 telas da base de demonstração
replace("As telas foram capturadas do sistema em execução local, conectado ao banco de dados de produção, com as "
        "vendas até 28 de fevereiro de 2026.",
        "As telas foram capturadas do sistema em execução local, conectado a uma base de demonstração com a mesma "
        "estrutura e o mesmo volume da base de produção e com as vendas até 28 de fevereiro de 2026, mas com "
        "quantidades e valores de venda fictícios, para preservar os dados da entidade parceira.")
n_fonte = 0
for p in paras():
    if norm(ptext(p)) == "Fonte: Elaborado pelos autores (2026), a partir do sistema em execução com a base de vendas da entidade parceira.":
        replace("com a base de vendas da entidade parceira.", "com a base de demonstração.", p)
        n_fonte += 1
print("fontes das telas:", n_fonte)

# 11 Resultados
replace("Este capítulo apresenta o que foi alcançado com a implementação", "Este capítulo apresenta a implementação")
replace("As telas da Seção 10.2 foram capturadas desse banco e evidenciam",
        "As telas da Seção 10.2, capturadas de uma base de demonstração com a mesma estrutura e vendas fictícias, "
        "evidenciam")
replace("Na execução de 11 de novembro de 2026, os 196 testes automatizados em ",
        "Na execução da suíte de testes automatizados de 11 de novembro de 2026, os 196 testes em ")
replace("Aplicado às 26 planilhas mensais de janeiro de 2024 a fevereiro de 2026, o ",
        "A análise exploratória de dados foi aplicada às 26 planilhas mensais de janeiro de 2024 a fevereiro de "
        "2026, cujo ")
replace("padrão de demanda pelo critério", "padrão de demanda segundo o critério")
replace("O padrão semanal é de dia útil, com pico", "O padrão semanal é para dias úteis, com pico")
replace("de Jardim Canadá e na sexta-feira", "de Jardim Canadá, e na sexta-feira")
replace("o que levou aos indicadores de dia da semana", "o que levou à inclusão dos indicadores de dia da semana")
replace("foi definida por experimentos", "foi definida por meio de experimentos")
replace("alterou um único fator", "alterou apenas um fator")
replace("abertura excepcional, resultado coerente", "abertura excepcional, o que é coerente")
replace("mais regular que o da série total", "mais regular do que o da série total")
replace("mas trata igualmente lojas", "mas trata igualmente de lojas")
replace("nem o MASE para cima de 1.", "nem o MASE acima de 1.")
split(find("Todos os critérios tornaram o fluxo diário", startswith=True), "Com três desvios-padrão")

# Tabela 2: fio de fechamento na última linha, como nas demais tabelas
tab2 = None
for tbl in body.iter(q("tbl")):
    if "Média mais 4 desvios" in "".join(t.text or "" for t in tbl.iter(q("t"))):
        tab2 = tbl
last = tab2.findall(q("tr"))[-1]
for tc in last.findall(q("tc")):
    bt = tc.find(q("tcPr")).find(q("tcBorders")).find(q("bottom"))
    for k, v in (("val", "single"), ("sz", "12"), ("space", "0"), ("color", "000000")):
        bt.set(q(k), v)

replace("e o erro no total dos 14 dias", "e o erro total nos 14 dias")
replace("planejada sobre o volume", "planejada com base no volume")
replace("ao uso do sistema, e a solução foi descartada", "ao uso do sistema. A solução foi descartada")
replace("e divide-se essa previsão entre", "e essa previsão é dividida entre")
replace("e as duas variações se compensam", "e essas variações se compensam")
replace("não percebe o pico", "não capta o pico")
replace("conteve a venda real em apenas 60,3% dos dias.", "abarcou apenas 60,3% dos dias de venda real.")
replace("o mesmo erro de um modelo ajustado", "o mesmo erro que um modelo ajustado")
replace("pela soma das categorias.", "pela soma dos valores das categorias.")
replace("em todas as séries, perto do limite", "em todas as séries, próximo do limite")
replace("a aplicação da queda inteira reduziu", "a aplicação da queda integral reduziu")
replace("Até a sexta semana", "Até à sexta semana")
replace("errou menos que d = 0 nas categorias", "errou menos do que d = 0 nas categorias")
replace("retreinar a cada mês aumentou", "retreinar mensalmente aumentou")
replace("A perda maior aparece a partir", "A maior perda ocorre a partir")
replace("Na média do ano a diferença", "Na média do ano, a diferença")
replace("como janeiro, após as festas", "como em janeiro, após as festas")
replace("não mudou com a frequência e ficou em 93%", "não mudou com a frequência e permaneceu em 93%")
replace("o erro dos meses de virada de temporada cresce de forma acentuada.",
        "o erro nos meses de virada de temporada cresce acentuadamente.")
replace("errou 8,6% a mais que a de 365", "apresentou erro 8,6% maior que a de 365")
replace("nas 23 séries e nas categorias e o maior ganho", "nas 23 séries e nas categorias, e o maior ganho")
replace("reduziria mais o erro", "reduziria ainda mais o erro")
replace("adotou 545 dias em todas as séries.", "adotou 545 dias para todas as séries.")

# 11.6
replace("do sistema, executado sobre a base completa", "do sistema, realizado sobre a base completa")
replace("foi executado sobre o banco de dados de publicação com 12 processos paralelos e levou",
        "foi executado no banco de dados de publicação, com 12 processos paralelos, e levou")
p116 = find("A solução definitiva foi avaliada pelo próprio treinamento", startswith=True)
p116b = split(p116, "Dessas combinações, 20 ficaram")
split(p116b, "O treinamento de produção, com a janela")
replace("e o erro foi menor que o da previsão ingênua", "e o erro foi menor do que o da previsão ingênua")
replace("um intervalo mais largo que o necessário", "um intervalo mais largo do que o necessário")
replace("não rejeitou a ausência de autocorrelação", "não rejeitou a hipótese de ausência de autocorrelação")
replace("no período avaliado, de 109% a 151%", "no período avaliado, variando de 109% a 151%")
replace("coincide com a queda de vendas do início de 2026, visível também no faturamento mensal da Figura 9.",
        "coincide com a queda nas vendas do início de 2026.")
replace("escolheu d = 1 em Plantas diversas e em Produtos de jardim das duas unidades e d = 0 em Grama e em Flores de corte",
        f"escolheu d{NB}={NB}1 para Plantas diversas e Produtos de jardim das duas unidades, e d{NB}={NB}0 para Grama e Flores de corte")

# 11.7 e 11.8
replace("das quais as oito categorias erram menos que a previsão", "das quais oito categorias erram menos do que a previsão")
replace("e estreitaram o intervalo de 95% da série total", "e reduziram o intervalo de confiança de 95% da série total")
replace("foram decididas por critérios além", "foram tomadas com base em critérios além")
replace("até um ano de teste, enquanto a validação do sistema cobre as oito semanas mais recentes, que incluem o Natal, "
        "o Ano-Novo e o Carnaval e coincidem com um período de queda das vendas.",
        "até um ano de testes, enquanto a validação do sistema abrange as oito semanas mais recentes, incluindo o "
        "Natal, o Ano-Novo e o Carnaval, e coincide com um período de queda nas vendas.")
replace("se apoia em poucas ocorrências", "se baseia em poucas ocorrências")
replace("a operação do sistema com os dados reais", "a operação do sistema com dados reais")
replace("que mantém a base com vendas até", "que mantém a base de vendas até")
replace("enquanto o serviço de hospedagem for o plano gratuito", "enquanto o serviço de hospedagem estiver no plano gratuito")
replace("o defeito de duplicidade dentro da mesma planilha.", "o defeito de duplicidade na mesma planilha.")

# 12 Conclusão
replace("acompanhadas de intervalo de 95%", "acompanhadas de intervalos de confiança de 95%")
replace(" de preparação dos dados, modelos SARIMAX", " de preparação de dados, modelos SARIMAX")
replace("e um painel para usuários não técnicos, e o objetivo geral foi alcançado",
        "e um painel para usuários não técnicos. O objetivo geral foi alcançado")
replace("um registro das previsões que permite avaliar", "um registro das previsões, o que permite avaliar")
replace("destacam-se as encomendas grandes, não previstas", "destacam-se as encomendas de grande porte, não previstas")
replace("insuficiente para a sazonalidade anual", "insuficiente para capturar a sazonalidade anual")

tree.write(DOC, xml_declaration=True, encoding="UTF-8", standalone=True)

# ================================================================ figuras
doc = open(DOC, encoding="utf-8").read()
rels = open(os.path.join(WORK, "word", "_rels", "document.xml.rels"), encoding="utf-8").read()


def figura(nome):
    mt = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"/>(?:(?!</wp:inline>).)*?name="%s"(?:(?!</wp:inline>).)*?r:embed="(rId\d+)"' % nome, doc, re.S)
    alvo = re.search(r'Id="%s"[^>]*Target="([^"]+)"' % mt.group(3), rels).group(1)
    return int(mt.group(1)), int(mt.group(2)), os.path.join(WORK, "word", alvo)


def redimensiona(nome, cx, cy):
    global doc
    ini = doc.index(f'name="{nome}"')
    a = doc.rindex("<wp:inline", 0, ini)
    b = doc.index("</wp:inline>", ini)
    bloco = doc[a:b]
    bloco = re.sub(r'<wp:extent cx="\d+" cy="\d+"/>', f'<wp:extent cx="{cx}" cy="{cy}"/>', bloco)
    bloco = re.sub(r'<a:ext cx="\d+" cy="\d+"/>', f'<a:ext cx="{cx}" cy="{cy}"/>', bloco)
    doc = doc[:a] + bloco + doc[b:]


# Telas: mesma largura de exibição, altura pela proporção da captura
for nome, arq in (("Picture 3009", "fig09_inicio"), ("Picture 3010", "fig10_conferencia"),
                  ("Picture 3011", "fig11_previsao"), ("Picture 3012", "fig12_historico"),
                  ("Picture 3013", "fig13_relatorios")):
    cx, cy, destino = figura(nome)
    im = Image.open(os.path.join(SHOTS, arq + ".png")).convert("RGB")
    if destino.lower().endswith((".jpg", ".jpeg")):
        im.save(destino, quality=92)
    else:
        im.save(destino, optimize=True)
    redimensiona(nome, cx, round(cx * im.height / im.width))
    print(nome, "->", os.path.basename(destino), im.size)

# Figuras 6 e 7 maiores (pedido do orientador)
for nome, largura_in, altura_max_in in (("Picture 3006", 6.0, 6.2), ("Picture 3007", None, 6.6)):
    cx, cy, _ = figura(nome)
    if largura_in:
        ncx = int(largura_in * 914400)
        ncy = round(ncx * cy / cx)
    else:
        ncy = int(altura_max_in * 914400)
        ncx = round(ncy * cx / cy)
    redimensiona(nome, ncx, ncy)
    print(nome, f"{cx / 914400:.2f}x{cy / 914400:.2f} -> {ncx / 914400:.2f}x{ncy / 914400:.2f} pol")

open(DOC, "w", encoding="utf-8").write(doc)
print("ok")
