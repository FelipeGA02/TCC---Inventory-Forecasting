# =====================================================================================
# EXEMPLO HISTÓRICO — não execute sobre o artigo atual.
# Script que consolidou o artigo em 30/09/2026 a partir da versão "TCC1 - Final" convertida
# de PDF (commit c70291d). Ele endereça parágrafos por ÍNDICE do documento daquela época;
# no artigo atual os índices são outros. Para novas edições use scripts/docx_lib.py, que
# localiza parágrafos por texto (Doc.find). Serve como referência de: decisões de texto,
# uso de clone/set_text, inserção de seção, tabela e referências, entradas de sumário com
# PAGEREF e keepNext em legendas.
# =====================================================================================
# -*- coding: utf-8 -*-
"""Consolida o artigo: edita word/document.xml preservando a formatação original.

Os índices (P<n>, T<n>) referem-se aos filhos do <w:body> do documento original.
Itálico é marcado no texto com [[...]].
"""
import copy
import random
import re
import sys

from lxml import etree

SRC = sys.argv[1]
DST = sys.argv[2]

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
XML = "http://www.w3.org/XML/1998/namespace"


def q(tag):
    return "{%s}%s" % (W, tag)


tree = etree.parse(SRC)
root = tree.getroot()
body = root.find(q("body"))
K = list(body)  # snapshot dos elementos originais

random.seed(20260930)
used_ids = set(root.xpath("//@w14:paraId", namespaces={"w14": W14}))


def new_pid():
    while True:
        v = "%08X" % random.randint(0x10000000, 0x7FFFFFFF)
        if v not in used_ids:
            used_ids.add(v)
            return v


def text_of(el):
    return "".join(t.text or "" for t in el.iter(q("t")))


def make_run(text, rpr=None, italic=False):
    r = etree.Element(q("r"))
    rp = copy.deepcopy(rpr) if rpr is not None else None
    if italic:
        if rp is None:
            rp = etree.Element(q("rPr"))
        if rp.find(q("i")) is None:
            i = etree.Element(q("i"))
            # ordem do schema: rStyle, rFonts, b, bCs, i, ...
            anchor = None
            for tag in ("bCs", "b", "rFonts", "rStyle"):
                anchor = rp.find(q(tag))
                if anchor is not None:
                    break
            if anchor is not None:
                anchor.addnext(i)
            else:
                rp.insert(0, i)
    else:
        if rp is not None and rp.find(q("i")) is not None:
            rp.remove(rp.find(q("i")))
    if rp is not None and len(rp):
        r.append(rp)
    t = etree.SubElement(r, q("t"))
    t.text = text
    t.set("{%s}space" % XML, "preserve")
    return r


def runs_from_markup(text, rpr=None):
    parts = re.split(r"(\[\[.*?\]\])", text)
    out = []
    for part in parts:
        if not part:
            continue
        if part.startswith("[["):
            out.append(make_run(part[2:-2], rpr, italic=True))
        else:
            out.append(make_run(part, rpr, italic=False))
    return out


def base_rpr(p):
    """rPr do primeiro run não itálico (ou o primeiro run), sem w:i."""
    for r in p.iter(q("r")):
        rp = r.find(q("rPr"))
        if rp is None or rp.find(q("i")) is None:
            if rp is not None:
                rp = copy.deepcopy(rp)
                for tag in ("lastRenderedPageBreak",):
                    pass
            return rp
    return None


def set_text(p, text, rpr="auto", trailing=" "):
    """Substitui o conteúdo do parágrafo mantendo pPr e marcadores de bookmark."""
    if rpr == "auto":
        rpr = base_rpr(p)
    had_pb = any(br.get(q("type")) == "page" for br in p.iter(q("br")))
    keep = []
    for ch in list(p):
        tag = etree.QName(ch).localname
        if tag == "pPr":
            continue
        if tag in ("bookmarkStart", "bookmarkEnd"):
            keep.append(ch)
        p.remove(ch)
    starts = [b for b in keep if etree.QName(b).localname == "bookmarkStart"]
    ends = [b for b in keep if etree.QName(b).localname == "bookmarkEnd"]
    for b in starts:
        p.append(b)
    for r in runs_from_markup(text + trailing, rpr):
        p.append(r)
    if had_pb:
        br_run = etree.SubElement(p, q("r"))
        etree.SubElement(br_run, q("br")).set(q("type"), "page")
    for b in ends:
        p.append(b)
    return p


def clone(template, text=None, rpr="auto", strip_bookmarks=True, trailing=" "):
    p = copy.deepcopy(template)
    p.set("{%s}paraId" % W14, new_pid())
    if strip_bookmarks:
        for b in p.findall(q("bookmarkStart")) + p.findall(q("bookmarkEnd")):
            p.remove(b)
    # remove quebras de página herdadas
    for br in p.iter(q("br")):
        if br.get(q("type")) == "page":
            br.getparent().remove(br)
    if text is not None:
        set_text(p, text, rpr=rpr if rpr != "auto" else base_rpr(template), trailing=trailing)
    return p


def insert_after(anchor, *els):
    cur = anchor
    for el in els:
        cur.addnext(el)
        cur = el
    return cur


def remove(*els):
    for el in els:
        el.getparent().remove(el)


def set_ppr_spacing_after(p, val):
    ppr = p.find(q("pPr"))
    sp = ppr.find(q("spacing"))
    if sp is None:
        sp = etree.Element(q("spacing"))
        # spacing vem depois de numPr/pStyle e antes de ind
        ind = ppr.find(q("ind"))
        if ind is not None:
            ind.addprevious(sp)
        else:
            ppr.append(sp)
    sp.set(q("after"), str(val))


def add_page_break_before(p):
    ppr = p.find(q("pPr"))
    pb = etree.Element(q("pageBreakBefore"))
    # ordem do schema: pStyle, keepNext, keepLines, pageBreakBefore ...
    anchor = None
    for tag in ("keepLines", "keepNext", "pStyle"):
        anchor = ppr.find(q(tag))
        if anchor is not None:
            break
    if anchor is not None:
        anchor.addnext(pb)
    else:
        ppr.insert(0, pb)


def add_bookmark(p, name, bid):
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


def set_cell_text(tc, text):
    p = tc.find(q("p"))
    for extra in tc.findall(q("p"))[1:]:
        tc.remove(extra)
    set_text(p, text, rpr=base_rpr(p))


P = lambda i: K[i]  # noqa: E731

BODY = P(53)     # parágrafo de corpo padrão
SPACER = P(54)   # parágrafo vazio entre parágrafos
H2 = P(128)      # título de seção (Ttulo2)

# --------------------------------------------------------------------------
# RESUMO
# --------------------------------------------------------------------------
set_text(P(44), (
    "Este trabalho apresenta o desenvolvimento de um sistema de previsão de vendas para a Floricultura Verde Perto, "
    "com histórico consolidado de vendas cobrindo o período de janeiro de 2024 a fevereiro de 2026. O setor de "
    "floricultura apresenta desafios decorrentes do alto nível de perecibilidade dos produtos, da sazonalidade acentuada "
    "e da oscilação da demanda em datas comemorativas. A ausência de previsão gera riscos de quebra de estoque e perdas "
    "por excesso de compra. A solução desenvolvida contempla um fluxo completo de processamento de dados históricos de "
    "vendas, com engenharia de atributos, treinamento e atualização automática de modelos preditivos baseados em SARIMAX "
    "([[Seasonal AutoRegressive Integrated Moving Average with eXogenous inputs]]), um modelo estatístico de previsão de "
    "séries temporais que considera padrões históricos, sazonalidade e fatores externos que podem influenciar a demanda, "
    "apresentação de indicadores em [[dashboard]] interativo e simulações de cenários de promoção e venda. A previsão é "
    "diária, com horizonte de 14 dias, e segue uma arquitetura hierárquica: o SARIMAX é ajustado à venda diária de balcão "
    "de cada unidade operacional, com variáveis de calendário, e a previsão é desagregada para categorias e produtos, "
    "enquanto as encomendas de grande porte são tratadas como fluxo de demanda à parte. Em validação [[walk-forward]] com "
    "26 janelas de 14 dias, os modelos das duas unidades obtiveram MASE de 0,58, superaram a previsão ingênua sazonal em "
    "24 das 26 janelas e apresentaram cobertura do intervalo de 95% entre 91% e 94%. A metodologia adota abordagem ágil "
    "e iterativa, com entregas parciais orientadas a valor. Os requisitos foram consolidados em reuniões formais com a "
    "entidade parceira e incluem módulos de [[upload]] de planilhas, geração automática de previsões, emissão de alertas "
    "de demanda, exportação de relatórios e simulação de estratégias comerciais, visando a redução de desperdícios, a "
    "mitigação de rupturas e o aumento da assertividade no planejamento logístico e comercial."), rpr=None)

# --------------------------------------------------------------------------
# 1 INTRODUÇÃO
# --------------------------------------------------------------------------
set_text(P(55), (
    "Este trabalho apresenta o desenvolvimento de um sistema de previsão de vendas para a Floricultura Verde Perto, "
    "empresa com unidades localizadas em Nova Lima (Jardim Canadá) e Itabirito, Minas Gerais. A empresa possui "
    "aproximadamente dois anos de histórico consolidado de vendas e dados financeiros, totalizando mais de 333 mil "
    "registros transacionais com informações detalhadas por transação, segmentação por grupos de produtos e separação de "
    "dados entre as três empresas do grupo, que correspondem a duas unidades operacionais."))
set_text(P(57), (
    "A base de dados cobre o período de janeiro de 2024 a fevereiro de 2026, contendo 5.166 produtos distintos SKU "
    "([[Stock Keeping Unit]]), um código utilizado para identificar individualmente produtos no controle de estoque, "
    "aproximadamente 2.500 clientes únicos, 38 vendedores e duas unidades operacionais: Jardim Canadá, que reúne as "
    "vendas da floricultura e do [[garden center]], e Itabirito. Esse conjunto de dados possui informações necessárias "
    "para a construção de modelos preditivos que capturam padrões sazonais e tendências."), rpr=None)
set_text(P(59), (
    "Embora os dados disponíveis apresentem potencial analítico, demandam etapas de tratamento e normalização para "
    "viabilizar seu uso em modelagem preditiva. A solução desenvolvida contempla um fluxo de processamento: geração e "
    "gestão de dados, tratamento e normalização, engenharia de atributos, treinamento e atualização de modelos preditivos, "
    "apresentação de indicadores em [[dashboard]] interativo e simulações de cenários de promoção e vendas conjugadas de "
    "produtos. A previsão é gerada com granularidade diária e horizonte de 14 dias, alinhado ao ciclo operacional de "
    "reposição da empresa e à curta vida útil dos produtos perecíveis."), rpr=None)
set_text(P(61), (
    "Para apresentar a solução de forma estruturada, este projeto está organizado da seguinte maneira. O Capítulo 2 "
    "descreve a problematização, contrastando a situação atual e a desejada. O Capítulo 3 apresenta a justificativa "
    "científica e técnica da abordagem. O Capítulo 4 define os objetivos geral e específicos. O Capítulo 5 reúne o "
    "referencial teórico que fundamenta a escolha do SARIMAX. O Capítulo 6 detalha a metodologia adotada. O Capítulo 7 "
    "consolida os requisitos do sistema. O Capítulo 8 apresenta a modelagem, com os diagramas técnicos da solução. O "
    "Capítulo 9 trata da prototipação das telas. O Capítulo 10 expõe os resultados obtidos e o Capítulo 11 apresenta o "
    "cronograma de execução do projeto."))

# --------------------------------------------------------------------------
# 3 JUSTIFICATIVA
# --------------------------------------------------------------------------
set_text(P(69), (
    "A situação desejada consiste na adoção de um sistema integrado e unificado, acessível a todos os usuários, capaz de "
    "receber dados, atualizar automaticamente as previsões e apresentar recomendações fundamentadas em evidências "
    "quantitativas. Com a solução, a empresa poderá determinar quantas unidades de cada produto adquirir para um período "
    "definido, antecipar o impacto de datas comemorativas, avaliar o efeito de promoções e de vendas conjugadas e "
    "identificar produtos frequentemente comprados em conjunto. O problema central pode ser sintetizado nas seguintes "
    "questões operacionais:"))
set_text(P(77), (
    "A falta de controle de estoque, planejamento e previsão de vendas da empresa gera ineficiências operacionais que se traduzem "
    "diretamente em perdas financeiras. Para enfrentá-las, foi desenvolvido um sistema integrado e unificado, acessível a "
    "todos os usuários, capaz de receber dados, atualizar automaticamente os modelos preditivos em periodicidade semanal "
    "e as previsões diariamente, e apresentar recomendações com base em evidências quantitativas."))
set_text(P(81), (
    "A justificativa técnica complementar está nos resultados da competição M4 (MAKRIDAKIS; SPILIOTIS; ASSIMAKOPOULOS, "
    "2020), que demonstrou que métodos estatísticos superam, em média, abordagens puras de aprendizado de máquina, "
    "sobretudo em séries com histórico reduzido, o que é o cenário do presente projeto, com 26 meses de histórico, "
    "insuficientes para estimar uma sazonalidade anual. Essa evidência legitima a escolha do SARIMAX como modelo abordado "
    "neste trabalho. Como a demanda por produto é esparsa, com o produto típico registrando venda em apenas 9 dos 789 "
    "dias do período, o modelo é aplicado à demanda diária agregada de cada unidade operacional, uma série densa, e as "
    "previsões por categoria e por produto são obtidas por desagregação."))
set_text(P(83), (
    "Além da contribuição operacional direta à empresa parceira, o projeto contribui academicamente com: (i) uma "
    "estratégia de seleção de variáveis exógenas por importância relativa calculada via [[Random Forest]], adaptando ao "
    "contexto do SARIMAX a medida MDI formalizada por Breiman (2001); (ii) uma avaliação empírica do nível de agregação "
    "adequado à previsão diária de um catálogo perecível de cauda longa, comparando a modelagem direta de unidades e "
    "categorias com a desagregação da previsão agregada e tratando as encomendas de grande porte como fluxo de demanda "
    "distinto da venda de balcão."), rpr=None)
set_text(P(85), "O sistema desenvolvido permite:")
set_text(P(91), (
    "Com essa estrutura, a empresa dispõe de subsídios para reduzir desperdícios de produtos perecíveis, mitigar rupturas "
    "de estoque e aumentar a assertividade no planejamento comercial e logístico."))

# --------------------------------------------------------------------------
# 4 OBJETIVOS
# --------------------------------------------------------------------------
set_text(P(94), (
    "Desenvolver um sistema de previsão de vendas para a Floricultura Verde Perto, baseado em dados históricos de vendas "
    "e técnicas de modelagem preditiva utilizando o modelo SARIMAX, capaz de apoiar decisões operacionais e estratégicas "
    "de reposição e compra, com previsão diária e horizonte de 14 dias."))
set_text(P(97), (
    "Estruturar [[pipeline]], sequência de etapas realizadas desde a entrada dos dados até a geração dos resultados, "
    "automatizado de ingestão e tratamento de dados provenientes de planilhas mensais exportadas do sistema financeiro, "
    "incluindo deduplicação, normalização, classificação dos produtos em categorias e separação das encomendas de grande "
    "porte;"), rpr=None)
set_text(P(99), (
    "Desenvolver módulo de engenharia de atributos que produza variáveis exógenas diárias de calendário para cada unidade "
    "operacional, incluindo dia da semana, feriados, fechamentos e aberturas excepcionais da loja e proximidade de datas "
    "comemorativas;"))
set_text(P(100), (
    "Implementar estratégia de avaliação da importância relativa das variáveis exógenas calculada via [[Random Forest]], "
    "apoiando a seleção das variáveis incorporadas ao SARIMAX;"), rpr=None)
set_text(P(101), (
    "Treinar modelos SARIMAX com seleção automática de ordem via Critério de Informação de Akaike (AIC) para a demanda "
    "diária de cada unidade operacional, com atualização semanal automatizada, e desagregar as previsões para categorias "
    "e produtos;"))
# P102-P104 eram um único item quebrado em três parágrafos na conversão
set_text(P(102), (
    "Avaliar o desempenho dos modelos com métricas de erro padronizadas (MASE, MAE e RMSE) e com a cobertura do "
    "intervalo de confiança, em conjuntos de teste [[hold-out]] e validação [[walk-forward]], técnica em que o modelo é "
    "treinado com dados anteriores e testado em períodos futuros simulando uma situação real, comparando-os com a "
    "previsão ingênua sazonal;"), rpr=None)
ppr102 = P(102).find(q("pPr"))
ppr102.remove(ppr102.find(q("spacing")))
remove(P(103), P(104))

# --------------------------------------------------------------------------
# 5 REFERENCIAL TEÓRICO
# --------------------------------------------------------------------------
set_text(P(115), (
    "Para séries com histórico reduzido, Makridakis, Spiliotis e Assimakopoulos (2020) demonstraram na competição M4 que "
    "métodos estatísticos superam, em média, abordagens puras de aprendizado de máquina. Esse resultado fundamenta a "
    "escolha do SARIMAX como modelo central em detrimento de alternativas como redes neurais e modelos de árvore de "
    "decisão, que tendem ao sobreajuste ([[overfitting]]), fenômeno que ocorre quando um modelo se ajusta excessivamente "
    "aos dados de treinamento, para um número reduzido de amostras."), rpr=None)
set_text(P(117), (
    "A avaliação da importância relativa das variáveis exógenas fundamenta-se na medida MDI ([[Mean Decrease in "
    "Impurity]]), técnica utilizada para medir a importância das variáveis em modelos de aprendizado de máquina, calculada "
    "por Florestas Aleatórias (BREIMAN, 2001). Essa abordagem permite ordenar as variáveis candidatas segundo sua "
    "contribuição para explicar a demanda sem incorrer nos vieses da seleção [[stepwise]] convencional, método de seleção "
    "automática de variáveis que adiciona ou remove atributos do modelo com base em critérios estatísticos."), rpr=None)
set_text(P(119), (
    "Para produtos com demanda intermitente, em que a maior parte dos dias não registra venda, Croston (1972) propôs "
    "estimar separadamente o tamanho das vendas e o intervalo entre elas. Syntetos e Boylan (2005) demonstraram que esse "
    "método superestima a demanda e propuseram a correção conhecida como SBA, e Teunter, Syntetos e Babai (2011) "
    "propuseram o método TSB, que atualiza a probabilidade de ocorrência de venda a cada período. Syntetos, Boylan e "
    "Croston (2005) estabeleceram um critério que classifica a demanda em suave, errática, intermitente ou [[lumpy]], a "
    "partir do intervalo médio entre vendas (ADI) e do quadrado do coeficiente de variação do tamanho das vendas (CV²), "
    "com pontos de corte em 1,32 e 0,49; nos padrões intermitente e [[lumpy]], os métodos de demanda intermitente "
    "produzem erros menores que os modelos convencionais de séries temporais."), rpr=None)
new5 = [
    clone(SPACER),
    clone(BODY, (
        "Quando as séries individuais são esparsas, a previsão hierárquica permite estimar a demanda em um nível "
        "agregado, no qual o sinal é mais regular, e distribuí-la aos níveis inferiores. Na abordagem [[top-down]], a "
        "previsão do agregado é repartida pela proporção histórica de cada componente, o que exige um único modelo bem "
        "alimentado por dados, ao custo de não capturar a dinâmica própria de cada parte (FLIEDNER, 2001). Gross e Sohl "
        "(1990) mostraram que a proporção média histórica está entre os métodos de desagregação mais simples e precisos, e "
        "Zotteri e Kalchschmidt (2007) formalizaram a escolha do nível de agregação como um equilíbrio entre o erro de "
        "especificação, que cresce com a agregação, e o erro de amostragem, que cresce com a fragmentação dos dados. "
        "Huber, Gossmann e Stuckenschmidt (2017) aplicaram esse princípio à previsão de demanda de produtos perecíveis, "
        "prevendo em níveis agregados as séries de itens com venda esparsa."), rpr=None),
    clone(SPACER),
    clone(BODY, (
        "Observações atípicas distorcem a estimação dos parâmetros e alargam os intervalos de previsão de modelos ARIMA "
        "(CHEN; LIU, 1993). Quando os picos decorrem de pedidos de poucos clientes de grande porte, a literatura recomenda "
        "separar essa demanda da demanda regular e tratá-la com a informação antecipada dos próprios pedidos, em vez de "
        "extrapolar o histórico (BARTEZZAGHI; VERGANTI, 1995; KALCHSCHMIDT; VERGANTI; ZOTTERI, 2006). A identificação "
        "desses pedidos por múltiplos de uma medida robusta, como a mediana, aproxima-se dos filtros de Hampel, empregados "
        "na detecção de valores atípicos (PEARSON et al., 2016)."), rpr=None),
    clone(SPACER),
    clone(BODY, (
        "Para a avaliação de previsões, Hyndman e Koehler (2006) propuseram o erro absoluto médio escalonado (MASE), que "
        "divide o erro absoluto médio do modelo pelo erro de uma previsão ingênua no conjunto de treinamento, de modo que "
        "valores inferiores a 1 indicam desempenho superior ao do método ingênuo. Diferentemente do MAPE, o MASE permanece "
        "definido em séries com valores nulos, como as vendas diárias em dias de loja fechada, e permite comparar séries "
        "de escalas distintas."), rpr=None),
]
insert_after(P(119), *new5)

# --------------------------------------------------------------------------
# 6 METODOLOGIA
# --------------------------------------------------------------------------
set_text(P(125), (
    "Foi utilizada abordagem ágil, com entregas parciais orientadas a valor. Cada iteração contemplou definição de "
    "histórias de usuário, implementação, testes e validação com a entidade parceira. O processo de desenvolvimento segue "
    "o modelo CRISP-DM ([[Cross-Industry Standard Process for Data Mining]]), metodologia utilizada para organizar "
    "projetos de análise de dados em etapas como entendimento do negócio, preparação, modelagem e avaliação (WIRTH; HIPP, "
    "2000), adaptado ao contexto de séries temporais, com as seguintes fases: compreensão do negócio, compreensão dos "
    "dados, preparação dos dados, modelagem, avaliação e implantação. As decisões técnicas de cada iteração foram "
    "registradas em documentos de decisão arquitetural, preservando a rastreabilidade entre os achados da análise dos "
    "dados e as escolhas de modelagem."), rpr=None)
set_text(P(129), (
    "A solução foi estruturada com [[stack]], conjunto de ferramentas, linguagens e bancos de dados usados para construir "
    "uma aplicação, voltada para ciência de dados e aplicações web, incluindo:"), rpr=None)
set_text(P(131), (
    "Modelagem preditiva: biblioteca [[statsmodels]] (estimação SARIMAX, suavização exponencial de Holt-Winters e testes "
    "estatísticos), [[scikit-learn]] ([[Random Forest]] para importância de variáveis);"), rpr=None)
set_text(P(132), "Processamento de dados: bibliotecas [[pandas]], [[numpy]];", rpr=None)
set_text(P(133), (
    "Visualização: biblioteca [[matplotlib]], utilizada na análise exploratória e no diagnóstico dos modelos;"), rpr=None)
set_text(P(134), (
    "[[Dashboard]] interativo: biblioteca [[React]], com [[TypeScript]] e gráficos em [[Recharts]];"), rpr=None)
backend_item = clone(P(134), (
    "[[Backend]]: [[framework FastAPI]], com autenticação JWT, banco de dados [[SQLite]] acessado via [[SQLAlchemy]] e "
    "agendamento de rotinas com [[APScheduler]];"), rpr=None)
P(133).addnext(backend_item)
set_text(P(136), (
    "Ambiente de desenvolvimento: [[scripts]] Python para experimentação e módulos Python estruturados para produção, com "
    "testes automatizados em [[pytest]]."), rpr=None)
set_text(P(138), (
    "O [[pipeline]] de dados está organizado em três camadas: (i) ingestão e armazenamento dos arquivos XLSX mensais; (ii) "
    "processamento e geração das séries temporais e variáveis exógenas; (iii) treinamento, avaliação e geração de "
    "previsões, com ajuste semanal dos modelos e geração diária das previsões."), rpr=None)

# Nova seção 6.4 — Preparação dos Dados e Modelagem Preditiva
h64 = clone(H2, "Preparação dos Dados e Modelagem Preditiva")
add_bookmark(h64, "_Toc900001", 900001)
sec64 = [
    (
        "A preparação dos dados é realizada por um [[pipeline]] de sete etapas. A primeira extrai os registros do "
        "relatório de contas a receber, organizado em blocos por documento de venda, gerando uma linha por produto em "
        "cada documento, com deduplicação entre arquivos e controle de reprocessamento por [[hash]] de cada planilha. A "
        "segunda reduz o esquema de 20 para 9 atributos, removendo dados pessoais de clientes e atributos sem valor "
        "preditivo, como forma de pagamento e vendedor, que só são conhecidos após a venda. A terceira deriva a unidade "
        "operacional e a categoria de cada produto por tabelas de correspondência e regras aplicadas à descrição. As "
        "etapas seguintes limpam a base, removendo serviços e taxas e padronizando datas e valores, marcam as encomendas "
        "de grande porte, constroem o calendário diário de cada unidade e geram as séries diárias. Ao final, o "
        "[[pipeline]] verifica a conservação dos volumes entre as etapas e a aderência do calendário às vendas. Aplicado "
        "às 26 planilhas do período, ele produziu 333.019 registros, sem duplicatas, dos quais 327.677 correspondem à "
        "demanda de produtos."
    ),
    (
        "As três empresas do grupo foram consolidadas em duas unidades operacionais, Jardim Canadá e Itabirito, e os "
        "produtos foram organizados em três categorias de demanda: Grama, Flores de corte e Produtos de jardim, esta "
        "última reunindo plantas, insumos e acessórios. Os grupos utilizados pela empresa, como Plantas diversas e "
        "Insumos e acessórios, são preservados para fins de apresentação no [[dashboard]]."
    ),
    (
        "A previsão segue uma arquitetura hierárquica em duas camadas. Pelo critério de Syntetos, Boylan e Croston "
        "(2005), as séries de cada unidade apresentam demanda errática, padrão adequado a modelos como o SARIMAX após a "
        "transformação logarítmica, ao passo que 99,3% dos produtos classificáveis apresentam demanda intermitente ou "
        "[[lumpy]]. Na primeira camada, um modelo SARIMAX é ajustado à série diária de cada unidade operacional, que soma "
        "todas as categorias. Na segunda, a previsão da unidade é desagregada em cascata, primeiro para as categorias e "
        "depois para os produtos, pela participação recente de cada nível, calculada em janelas de quatro a oito "
        "semanas, combinada ao seu perfil de dia da semana; no passo para as categorias, considera-se também o efeito "
        "das datas comemorativas sobre cada uma delas. Produtos com menos de 28 dias com venda ou menos de oito vendas "
        "recebem o rateio uniforme da categoria, e os métodos de Croston, SBA e TSB constituem, no nível de produto, a "
        "referência de comparação para a previsão obtida por desagregação."
    ),
    (
        "As encomendas de grande porte são separadas da série modelada. Uma linha de venda é considerada encomenda "
        "quando sua quantidade supera cinco vezes a mediana do volume diário de segunda a sábado da respectiva unidade e "
        "categoria, limiar calculado apenas com os dados de treinamento. Essas vendas, em geral destinadas a obras e "
        "serviços de paisagismo combinados com antecedência, formam um fluxo à parte, e o modelo prevê a venda de "
        "balcão. Nos picos restantes, os valores acima do 99º percentil dos dias de loja aberta são limitados a esse "
        "percentil apenas durante o treinamento."
    ),
    (
        "O modelo de cada unidade é ajustado sobre a série transformada por log(1 + y), que estabiliza a variância, com "
        "sazonalidade semanal (m = 7), sem diferenciação sazonal (D = 0) e com diferenciação regular (d = 1), que faz a "
        "previsão partir do nível recente da série em vez de retornar à média histórica. As ordens são selecionadas por "
        "AIC em uma grade com p e q entre 0 e 2 e P e Q entre 0 e 1, utilizando apenas os dados anteriores ao período de "
        "teste. As variáveis exógenas são seis indicadores de dia da semana, um indicador de loja fechada, que reúne "
        "domingos, feriados nacionais obtidos da BrasilAPI, inclusive o Carnaval, e fechamentos observados no "
        "histórico, e um indicador de abertura excepcional, que representa os dias de Dia das Mães e de Finados em que a "
        "unidade de Itabirito abre. Essas variáveis resultaram da avaliação de um conjunto mais amplo de candidatas, que "
        "incluía vésperas e dias seguintes a feriados, proximidade de datas comemorativas e variáveis climáticas, com base "
        "na importância relativa calculada por [[Random Forest]] e na significância dos coeficientes estimados; a "
        "proximidade de datas comemorativas, sem efeito na série da unidade, é empregada na desagregação por categoria. A "
        "previsão pontual corresponde à mediana da distribuição prevista e é acompanhada do intervalo de confiança de "
        "95%."
    ),
    (
        "Os modelos são reajustados semanalmente, às segundas-feiras, e a previsão para os 14 dias seguintes é gerada "
        "diariamente a partir dos modelos vigentes, por meio de rotinas agendadas no próprio servidor da aplicação. A "
        "partir da previsão, o sistema emite alertas de pico de demanda quando a quantidade prevista para os sete dias "
        "seguintes supera em pelo menos 20% a média das quatro semanas anteriores, e alertas de risco de sobra para "
        "produtos de vida útil curta com demanda em queda."
    ),
]
els = [h64]
for i, txt in enumerate(sec64):
    if i == len(sec64) - 1:
        els.append(clone(P(138), txt, rpr=None))  # último parágrafo: espaçamento de fim de seção
    else:
        els.append(clone(BODY, txt, rpr=None))
        els.append(clone(SPACER))
insert_after(P(138), *els)

set_text(P(140), (
    "Foram produzidos diagramas de casos de uso, atividades, classes, modelo de dados e arquitetura lógica, utilizando "
    "ferramentas de modelagem UML compatíveis com os padrões acadêmicos exigidos."))
set_text(P(142), "A validação do sistema contempla três dimensões:")
set_text(P(143), (
    "1°. Validação estatística dos modelos: validação [[walk-forward]] com origem móvel e horizonte de 14 dias, em 26 "
    "janelas consecutivas que cobrem um ano completo, de março de 2025 a fevereiro de 2026, além de conjuntos de teste "
    "[[hold-out]]. A ordem de cada modelo é selecionada apenas com dados anteriores à primeira janela, e o limiar das "
    "encomendas é recalculado em cada janela com os dados disponíveis até ela. A métrica primária é o MASE em relação à "
    "previsão ingênua sazonal semanal, com limiar de aceitação inferior a 1,0, e exige-se cobertura empírica do intervalo "
    "de 95% entre 90% e 98%. Reportam-se também o erro relativo à previsão ingênua na mesma janela de teste, o número de "
    "janelas em que o modelo a supera, a largura do intervalo, o MAE e o RMSE; MAPE e SMAPE, instáveis em séries com "
    "dias de venda nula, têm caráter informativo. Os modelos que não atendem aos limiares recebem o status de baixa "
    "confiança e continuam gerando previsões, acompanhadas de aviso no [[dashboard]];"), rpr=None)
set_text(P(144), (
    "2°. Testes de diagnóstico de resíduos: Teste de Ljung-Box para verificar ausência de autocorrelação residual e Teste "
    "de Shapiro-Wilk para normalidade dos resíduos, registrados para cada modelo treinado como diagnóstico complementar "
    "da adequação estatística, sem impedir sua disponibilização;"))
set_text(P(145), (
    "3°. Testes funcionais do sistema: testes unitários automatizados das regras de pré-processamento, executados com "
    "dados sintéticos, conferências de consistência a cada execução do [[pipeline]] e validação dos módulos de "
    "[[upload]], processamento, visualização e exportação com dados reais da entidade parceira, verificando consistência, "
    "desempenho e usabilidade com usuários não técnicos."), rpr=None)

# --------------------------------------------------------------------------
# 7 REQUISITOS
# --------------------------------------------------------------------------
rows = K[153].findall(q("tr"))
set_cell_text(rows[2].findall(q("tc"))[1],
              "Gerar previsão diária de quanto de cada produto será necessário nos próximos 14 dias")
for tr in rows:
    cells = tr.findall(q("tc"))
    if text_of(cells[0]).strip() == "REQ09":
        set_cell_text(cells[1], "Emitir alertas automáticos quando a previsão indicar pico de demanda ou risco de "
                                "sobra de determinado produto")

set_text(P(162), "RN01: A previsão de demanda deve ser diária e respeitar o horizonte operacional de reposição, definido em 14 dias;")
set_text(P(163), "RN02: Os modelos preditivos devem ser atualizados automaticamente a cada semana, e as previsões, geradas diariamente a partir dos dados mais recentes;")
set_text(P(164), "RN03: Deve ser emitido alerta sempre que a previsão indicar pico de demanda de um produto monitorado, com a justificativa e a data prevista do pico em linguagem simples;")
set_text(P(165), "RN04: Produtos de alta perecibilidade com demanda prevista em queda devem ser sinalizados com alerta de risco de sobra, evitando compras em volume incompatível com sua vida útil;")
set_text(P(167), "RN06: O calendário de cada unidade, com feriados, fechamentos e aberturas excepcionais, e as datas comemorativas cadastradas devem ser considerados no cálculo da previsão;")
set_text(P(168), "RN07: Toda importação de dados deve registrar log de execução, permitindo rastreabilidade e identificação de anomalias;")
rn08 = clone(P(168), "RN08: Encomendas de grande porte devem ser separadas da venda de balcão utilizada no ajuste dos modelos e apresentadas como fluxo de demanda à parte.")
P(168).find(q("pPr")).remove(P(168).find(q("pPr")).find(q("spacing")))
P(168).addnext(rn08)

rows = K[172].findall(q("tr"))
atores = [
    ("Administrador (gestora de compras)",
     "Envia planilhas, dispara a atualização manual dos modelos e acessa as funcionalidades de consulta, simulação e "
     "exportação."),
    ("Usuário de consulta (gerente de operações)",
     "Consulta previsões, acompanha tendências, recebe alertas, simula promoções e exporta relatórios, sem permissão "
     "para enviar planilhas ou atualizar os modelos."),
    ("Sistema (rotina automática)",
     "Executa a atualização semanal dos modelos SARIMAX e a geração diária das previsões e dos alertas."),
]
for tr, (a, d) in zip(rows[1:], atores):
    c = tr.findall(q("tc"))
    set_cell_text(c[0], a)
    set_cell_text(c[1], d)

# --------------------------------------------------------------------------
# 8 MODELAGEM
# --------------------------------------------------------------------------
set_text(P(177), (
    "O diagrama de casos de uso, apresentado na Figura 1, sintetiza as funcionalidades do sistema sob a perspectiva dos "
    "atores. A gestora de compras, com perfil de administrador, concentra as interações que alteram a base e os modelos, "
    "como o envio de planilhas e o disparo da atualização manual dos modelos, além de todas as funcionalidades de "
    "consulta. O gerente de operações, com perfil de consulta, visualiza o [[dashboard]], consulta previsões, acompanha "
    "tendências, recebe alertas, simula promoções e exporta relatórios. A rotina automática do sistema é responsável "
    "pela atualização semanal dos modelos e pela geração diária das previsões e dos alertas."), rpr=None)
set_text(P(182), (
    "O diagrama de atividades, exibido na Figura 2, representa o fluxo principal de processamento, desde o envio da "
    "planilha de vendas até a exportação dos relatórios. Após o envio, os dados são validados e normalizados; caso sejam "
    "detectadas inconsistências, o sistema registra log, sinaliza a anomalia e solicita novo envio. Confirmada a "
    "consistência, os produtos são classificados, as encomendas de grande porte são marcadas e são construídas as séries "
    "diárias de balcão e o calendário de cada unidade, que alimentam o ajuste dos modelos SARIMAX. Os modelos passam pela "
    "validação [[walk-forward]] e são registrados como treinados ou de baixa confiança, conforme os critérios de "
    "aceitação; em seguida, é gerada a previsão diária, desagregada por categoria e produto, que atualiza o "
    "[[dashboard]], origina os alertas e alimenta a exportação dos relatórios."), rpr=None)
set_text(P(188), (
    "O diagrama de classes, apresentado na Figura 3, descreve as principais entidades do domínio e seus relacionamentos. "
    "As classes de origem dos dados (Usuario, PlanilhaUpload, Transacao, ItemVenda, Produto e Unidade) alimentam a "
    "construção da SerieDiaria de cada unidade, que separa a venda de balcão das encomendas e, em conjunto com as "
    "variáveis exógenas de calendário (VariavelExogena), sustenta o ModeloSARIMAX. A previsão da unidade é repartida pela "
    "classe Desagregacao, com base na participação de categorias e produtos, originando objetos de Previsao, que por sua "
    "vez disparam Alertas e subsidiam a geração de Relatorios e simulações."))
set_text(P(193), (
    "O modelo entidade-relacionamento, apresentado na Figura 4, organiza o armazenamento dos dados operacionais e dos "
    "artefatos analíticos em banco de dados SQLite. A tabela Usuario registra os perfis de acesso, com as senhas "
    "armazenadas em [[hash]] bcrypt. As tabelas Categoria e Produto mantêm o catálogo e a participação de cada categoria "
    "por unidade, utilizada na desagregação, enquanto a tabela Modelo registra a ordem, as métricas de validação e o "
    "status do modelo de cada unidade, e a tabela Previsao armazena as previsões diárias geradas a partir dele. As tabelas "
    "Log_Processamento e Historico_Retreino registram cada importação de planilha e cada atualização dos modelos. A base "
    "transacional consolidada é mantida em arquivo gerado pelo [[pipeline]] de dados, e o modelo privilegia a "
    "rastreabilidade e a integridade referencial entre produtos, modelos e previsões."), rpr=None)
set_text(P(205), (
    "A arquitetura lógica, ilustrada na Figura 5, organiza-se em quatro camadas. A camada de ingestão recebe as planilhas "
    "de vendas, registra cada importação e mantém a base consolidada; a camada de processamento realiza a validação, a "
    "deduplicação, a classificação dos produtos, a marcação das encomendas e a construção do calendário e das séries "
    "diárias; a camada de modelagem executa a seleção das variáveis exógenas, o ajuste do SARIMAX de cada unidade com "
    "seleção via AIC, a validação [[walk-forward]] e a desagregação das previsões; e a camada de apresentação expõe os "
    "resultados por meio de uma API REST com autenticação, consumida pelo [[dashboard]] interativo, pelo módulo de "
    "simulação de promoções e pela exportação de relatórios. O [[backend]] é implementado como monolito modular, no qual "
    "a lógica de domínio não depende de [[frameworks]] de entrada e saída, o que favorece os testes isolados, a "
    "manutenibilidade e a evolução independente dos componentes."), rpr=None)
set_text(P(216), (
    "A solução foi construída em Python 3.11, organizada em módulos estruturados para produção e em [[scripts]] de "
    "experimentação, nos quais cada versão dos modelos é treinada e avaliada antes de ser incorporada à aplicação. A "
    "modelagem preditiva utiliza a biblioteca [[statsmodels]] para a estimação do SARIMAX e a [[scikit-learn]] para o "
    "cálculo da importância de variáveis via [[Random Forest]]. O processamento de dados é realizado com [[pandas]] e "
    "[[numpy]], e a visualização da análise exploratória com [[matplotlib]]. A API é implementada em [[FastAPI]], com "
    "autenticação por [[tokens]] JWT, perfis de acesso e senhas protegidas por bcrypt, persistência em [[SQLite]] por "
    "meio do [[SQLAlchemy]] e agendamento das rotinas com [[APScheduler]]; os relatórios são gerados em Excel e PDF. O "
    "[[dashboard]] interativo é implementado em [[React]], com [[TypeScript]] e gráficos em [[Recharts]], e consome a API "
    "por meio de um cliente gerado a partir da especificação OpenAPI. O versionamento do código é feito com [[Git]] e "
    "[[GitHub]]."), rpr=None)
set_text(P(218), (
    "O [[pipeline]] de dados está organizado em três camadas: ingestão e armazenamento dos arquivos XLSX mensais; "
    "processamento e geração das séries diárias e variáveis exógenas; e treinamento, avaliação e geração de previsões, "
    "com ajuste semanal dos modelos e geração diária das previsões. Essa organização modular alinha os componentes "
    "técnicos às camadas descritas na arquitetura lógica."), rpr=None)

# --------------------------------------------------------------------------
# 9 PROTOTIPAÇÃO
# --------------------------------------------------------------------------
set_text(P(220), (
    "A prototipação tem por objetivo validar, junto à entidade parceira, a navegação e a disposição das informações. O "
    "protótipo de telas, implementado em [[React]], contempla o painel principal ([[dashboard]]) com indicadores de "
    "desempenho dos modelos e gráficos de tendência de demanda, a tela de [[upload]] de planilhas, a tela de conferência "
    "dos dados importados, a tela de previsão por produto e período, o módulo de simulação de promoções e vendas "
    "conjugadas e a tela de exportação de relatórios em PDF e Excel."), rpr=None)
set_text(P(222), (
    "As telas foram concebidas priorizando a usabilidade para usuários não técnicos, com linguagem simples e indicadores "
    "explicados, em conformidade com o requisito de usabilidade definido no projeto. As figuras a seguir apresentam o "
    "protótipo desenvolvido, cujas telas utilizam dados fictícios para validar a navegação e a disposição das "
    "informações; os valores exibidos não correspondem aos resultados dos modelos apresentados no Capítulo 10."))
remove(P(223), P(224))  # parágrafo duplicado do modelo entidade-relacionamento
set_text(P(226), (
    "O painel centralizado constitui a interface principal do sistema, projetado para consolidar as informações "
    "estratégicas e operacionais em uma única visualização, atendendo ao requisito de disponibilização de um "
    "[[dashboard]] (REQ11). Como ilustra a Figura 6, a tela inicial destaca os produtos com maior volume de saída no "
    "período, evidenciando o [[top]] 3 de vendas para facilitar a identificação rápida de tendências e o planejamento "
    "para datas especiais pela gestão (REQ06). Adicionalmente, a interface apresenta os indicadores de desempenho do "
    "modelo preditivo, o número de produtos monitorados e o horário do próximo cálculo automático, traduzindo as métricas "
    "estatísticas de erro em informações visuais acessíveis e garantindo a transparência e a confiabilidade das "
    "previsões para usuários não técnicos (REQ04)."), rpr=None)
set_text(P(248), (
    "O núcleo analítico da solução reside na projeção de demanda baseada no modelo estatístico (REQ02). A Figura 10 "
    "ilustra a tela de previsões do [[SARIMAX]], que exibe a estimativa de demanda com sua margem de variação, a "
    "quantidade sugerida para cada período e os indicadores de desempenho do modelo (REQ04), visando aumentar a "
    "assertividade do planejamento logístico."), rpr=None)
set_text(P(254), (
    "A mitigação de rupturas de estoque no setor perecível precisa ser tratada de forma proativa. Os alertas automáticos "
    "(REQ09) são gerados a partir da própria previsão, sem depender da contagem de estoque, e notificam a gestão sobre os "
    "produtos com pico de demanda previsto ou com risco de sobra, conforme as regras de negócio RN03 e RN04."))
remove(P(255), P(256), P(257), P(258), P(259))  # figura do painel de reposição por estoque

def renum(p, old, new):
    for t in p.iter(q("t")):
        if t.text and old in t.text:
            t.text = t.text.replace(old, new)

renum(P(261), "Figura 12", "Figura 11")
renum(P(263), "Figura 12", "Figura 11")
renum(P(267), "Figura 13", "Figura 12")
renum(P(269), "Figura 13", "Figura 12")

# --------------------------------------------------------------------------
# 10 RESULTADOS
# --------------------------------------------------------------------------
set_text(P(273), "10 RESULTADOS")
add_bookmark(P(273), "_Toc900010", 900010)

res_A = (
    "A análise exploratória confirmou que a previsão individual por produto não é viável na base da Floricultura Verde "
    "Perto. O produto típico registrou venda em apenas 9 dos 789 dias do período, e 99,3% dos produtos classificáveis "
    "enquadram-se nos padrões intermitente ou [[lumpy]] segundo o critério de Syntetos, Boylan e Croston (2005), enquanto "
    "as séries diárias de cada unidade registram venda em cerca de 82% dos dias, com os dias sem venda concentrados em "
    "domingos e feriados. A análise mostrou ainda que o padrão semanal é de dia útil, com pico entre terça e quinta-feira "
    "para Grama e para Produtos de jardim em Jardim Canadá e na sexta-feira para Flores de corte, sábado de menor "
    "movimento e loja fechada aos domingos, e que o efeito das datas comemorativas muda de sinal conforme a categoria: "
    "Flores de corte vende de 1,7 a 5,0 vezes a média no Dia da Mulher, no Dia das Mães e no Dia dos Namorados, enquanto "
    "a venda de Grama cai na maior parte dessas datas. Os 20 produtos de maior giro respondem por 61,7% do volume "
    "vendido.")
res_B = (
    "Os testes de nível de agregação, realizados em validação [[walk-forward]] com 26 janelas de 14 dias e com regra de "
    "decisão fixada antes da execução, sustentaram a modelagem por unidade: o modelo próprio de Itabirito reduziu o MASE "
    "em 17% em relação à repartição da previsão da rede, enquanto nenhuma das seis séries por unidade e categoria obteve "
    "o ganho mínimo de 5% exigido para ser modelada diretamente. Em Itabirito, as encomendas de grande porte somavam 36,3% "
    "do volume em apenas 80 linhas de venda, a maioria de Grama faturada por boleto, e elevavam o MASE a 1,434, pior que o "
    "da previsão ingênua. Com sua separação e a limitação dos picos restantes, o MASE caiu para 0,796; em Jardim Canadá, "
    "onde as encomendas representam 1,3% do volume, o resultado praticamente não se alterou, passando de 0,659 para "
    "0,646.")
res_C = (
    "A contribuição do calendário foi avaliada de forma incremental, sobre a série total da rede. Com as variáveis de "
    "calendário, o erro nos 14 feriados do ano de teste caiu de cerca de 4 mil unidades para praticamente zero, a largura "
    "média do intervalo de 95% reduziu-se de cerca de 79 mil para 13 mil unidades, o erro médio anual diminuiu 9% e o "
    "número de janelas em que o modelo superou a previsão ingênua passou de 19 para 22. As variáveis climáticas de "
    "precipitação e temperatura não trouxeram ganho, mesmo com os valores observados, e responderam por 1,4% da "
    "importância relativa calculada pela [[Random Forest]], contra 83,2% do dia da semana e 15,2% dos feriados; por esse "
    "motivo, não integram o modelo.")
res_D = (
    "O modelo adotado em cada unidade é o SARIMAX ajustado à venda de balcão, com diferenciação regular e exógenas de "
    "calendário, cuja ordem selecionada foi (0,1,1), com ordem sazonal (0,0,1) e m = 7, nas duas unidades. A Tabela 4 "
    "apresenta seu desempenho nas 26 janelas de 14 dias compreendidas entre março de 2025 e fevereiro de 2026.")
res_E = (
    "Os modelos das duas unidades atendem aos critérios de aceitação definidos na Seção 6.6 e recebem o status de "
    "treinados. O MASE é inferior ao erro relativo medido na mesma janela de teste porque sua escala é calculada no "
    "período de treinamento, mais irregular; por isso, os dois indicadores são reportados em conjunto. Nos "
    "feriados, o erro é praticamente nulo, e nos dias de abertura excepcional de Itabirito o erro médio caiu de 780 para "
    "50 unidades. Somadas e comparadas com a venda total, as previsões das duas unidades reduzem em 16% o erro médio "
    "diário em relação ao modelo ajustado à série total da rede sem tratamento. No modelo com calendário ajustado à série "
    "total, o teste de Ljung-Box não indicou autocorrelação residual (p = 0,69 e 0,48 nas defasagens 7 e 14), ao passo "
    "que o teste de Shapiro-Wilk rejeitou a normalidade dos resíduos, comportamento esperado em vendas com dias de pico e "
    "que reforça a verificação empírica da cobertura do intervalo de 95%.")
res_F = (
    "Duas limitações foram identificadas e mensuradas. A primeira são as encomendas, que no ano de teste representaram "
    "51,2% do volume de Itabirito e 70% do erro dessa unidade quando a previsão é comparada à venda total; por dependerem "
    "do fechamento de negócios com clientes específicos, essas vendas não são extrapoladas do histórico e são "
    "apresentadas como fluxo à parte, com a previsão referente à venda de balcão. A segunda é o viés da previsão pontual, "
    "que, por corresponder à mediana da distribuição prevista, cobre 87,5% da venda de balcão de Jardim Canadá e 80,9% da "
    "de Itabirito. Assim, o sistema apresenta, além da venda mais provável, uma quantidade de referência para "
    "disponibilidade, correspondente a um quantil superior da mesma distribuição, cujo nível é definido pela gestão "
    "conforme a tolerância a sobras.")
res_G = (
    "Ao substituir o planejamento baseado em conhecimento tácito por previsões fundamentadas em evidências quantitativas, "
    "o sistema oferece à Floricultura Verde Perto subsídios para a redução de desperdícios de produtos perecíveis, a "
    "mitigação de rupturas de estoque e o aumento da assertividade no planejamento comercial e logístico. Como resultados "
    "de apoio à decisão, o sistema entrega a visualização de indicadores de desempenho dos modelos, o acompanhamento de "
    "tendências de demanda por período e grupo de produto, os alertas de pico de demanda e de risco de sobra, a simulação "
    "de efeitos de promoções e vendas conjugadas e a exportação de relatórios em formato gerencial. Adicionalmente, o "
    "projeto contribui academicamente com a estratégia de seleção de variáveis exógenas por importância relativa adaptada "
    "ao SARIMAX e com a avaliação empírica do nível de agregação adequado à previsão diária de produtos perecíveis, que "
    "inclui o tratamento das encomendas de grande porte como fluxo de demanda distinto da venda de balcão.")

set_text(P(274), res_A, rpr=None)
set_text(P(276), res_B, rpr=None)

# Tabela 4 — desempenho por unidade (estrutura copiada da Tabela 2)
cap4 = clone(K[157], "Tabela 4 – Desempenho dos modelos por unidade na validação [[walk-forward]]", trailing="")
cap4.append(make_run(" "))
src4 = clone(K[159], "Fonte: Elaborado pelos autores (2026).", trailing="")
src4.append(make_run(" "))
tbl = copy.deepcopy(K[158])
grid = [4392, 2340, 2340]
for g, w in zip(tbl.find(q("tblGrid")).findall(q("gridCol")), grid):
    g.set(q("w"), str(w))
trs = tbl.findall(q("tr"))
header, tmpl = trs[0], trs[1]
for tr in trs[1:]:
    tbl.remove(tr)
dados = [
    ("MASE médio", "0,58", "0,58"),
    ("Janelas com MASE inferior a 1", "25 de 26", "23 de 26"),
    ("Erro em relação à previsão ingênua no mesmo período", "66%", "62%"),
    ("Janelas em que o modelo supera a previsão ingênua", "24 de 26", "24 de 26"),
    ("Erro absoluto médio diário: modelo × previsão ingênua", "1.282 × 1.948", "486 × 780"),
    ("Cobertura do intervalo de 95%", "91,2%", "93,7%"),
    ("Largura média do intervalo de 95%", "5.463", "2.255"),
    ("Status do modelo", "treinado", "treinado"),
]


def fix_cell(tc, width, text, center):
    tc.find(q("tcPr")).find(q("tcW")).set(q("w"), str(width))
    p = tc.find(q("p"))
    ppr = p.find(q("pPr"))
    jc = ppr.find(q("jc"))
    if jc is None:
        jc = etree.SubElement(ppr, q("jc"))
    jc.set(q("val"), "center" if center else "left")
    ind = ppr.find(q("ind"))
    if ind is not None:
        ind.set(q("left"), "0")
    set_cell_text(tc, text)
    for t in tc.iter(q("t")):
        pass


hdr_cells = header.findall(q("tc"))
for tc, w, txt in zip(hdr_cells, grid, ["Indicador", "Jardim Canadá", "Itabirito"]):
    tc.find(q("tcPr")).find(q("tcW")).set(q("w"), str(w))
    set_cell_text(tc, txt)
for k, (a, b, c) in enumerate(dados):
    tr = copy.deepcopy(tmpl)
    tr.set("{%s}paraId" % W14, new_pid())
    tr.find(q("trPr")).find(q("trHeight")).set(q("val"), "331")
    for p in tr.iter(q("p")):
        p.set("{%s}paraId" % W14, new_pid())
    cells = tr.findall(q("tc"))
    for tc in cells:
        vc = tc.find(q("tcPr")).find(q("vAlign"))
        if vc is None:
            vc = etree.SubElement(tc.find(q("tcPr")), q("vAlign"))
        vc.set(q("val"), "center")
    fix_cell(cells[0], grid[0], a, False)
    fix_cell(cells[1], grid[1], b, True)
    fix_cell(cells[2], grid[2], c, True)
    tbl.append(tr)
for p in header.iter(q("p")):
    p.set("{%s}paraId" % W14, new_pid())

new10 = [
    clone(BODY, res_C, rpr=None),
    clone(SPACER), clone(BODY, res_D, rpr=None),
    clone(SPACER), cap4, tbl, src4,
    clone(BODY, res_E, rpr=None),
    clone(SPACER), clone(BODY, res_F, rpr=None),
    clone(SPACER), clone(BODY, res_G, rpr=None),
]
insert_after(P(277), *new10)
# P278 continha o fim do capítulo 10 e o título do capítulo 11 no mesmo parágrafo
cap11 = clone(P(273), "11 CRONOGRAMA DO PROJETO", rpr=base_rpr(P(273)))
add_page_break_before(cap11)
add_bookmark(cap11, "_Toc900011", 900011)
remove(P(278))
new10[-1].addnext(cap11)

set_text(P(279), (
    "O projeto foi executado em ciclos iterativos ao longo de 2026, com entregas parciais orientadas a valor, conforme o "
    "cronograma apresentado na Tabela 5."))
renum(P(280), "Tabela 4", "Tabela 5")
periodos = {
    "Modelagem e arquitetura do sistema": "Mai.–Jul./2026",
    "Implementação do pipeline de ingestão": "Abr.–Ago./2026",
    "Engenharia de atributos e análise exploratória": "Ago.–Set./2026",
    "Modelagem preditiva SARIMAX": "Set./2026",
    "Dashboard e módulo de simulações": "Set.–Out./2026",
}
for tr in K[281].findall(q("tr")):
    cells = tr.findall(q("tc"))
    etapa = text_of(cells[0]).strip()
    if etapa in periodos:
        set_cell_text(cells[1], periodos[etapa])
    if etapa == "Implementação do pipeline de ingestão":
        set_cell_text(cells[2], "Pipeline de ingestão e pré-processamento")

# --------------------------------------------------------------------------
# REFERÊNCIAS
# --------------------------------------------------------------------------
add_page_break_before(P(283))
add_bookmark(P(283), "_Toc900012", 900012)
REF_T = K[293]  # modelo de referência de periódico (MAKRIDAKIS)


def ref(text):
    p = clone(REF_T, text, rpr=None)
    return p

refs_after = {
    287: [  # após ABNT NBR 14724
        "BARTEZZAGHI, E.; VERGANTI, R. Managing demand uncertainty through order overplanning. [[International Journal "
        "of Production Economics]], v. 40, n. 2-3, p. 107–120, 1995.",
    ],
    290: [  # após BREIMAN
        "CHEN, C.; LIU, L.-M. Forecasting time series with outliers. [[Journal of Forecasting]], v. 12, n. 1, p. 13–35, "
        "1993.",
        "CROSTON, J. D. Forecasting and stock control for intermittent demands. [[Operational Research Quarterly]], "
        "v. 23, n. 3, p. 289–303, 1972.",
        "FLIEDNER, G. Hierarchical forecasting: issues and use guidelines. [[Industrial Management & Data Systems]], "
        "v. 101, n. 1, p. 5–12, 2001.",
        "GROSS, C. W.; SOHL, J. E. Disaggregation methods to expedite product line forecasting. [[Journal of "
        "Forecasting]], v. 9, n. 3, p. 233–254, 1990.",
        "HUBER, J.; GOSSMANN, A.; STUCKENSCHMIDT, H. Cluster-based hierarchical demand forecasting for perishable goods. "
        "[[Expert Systems with Applications]], v. 76, p. 140–151, 2017.",
    ],
    292: [  # após HYNDMAN; ATHANASOPOULOS
        "HYNDMAN, R. J.; KOEHLER, A. B. Another look at measures of forecast accuracy. [[International Journal of "
        "Forecasting]], v. 22, n. 4, p. 679–688, 2006.",
        "KALCHSCHMIDT, M.; VERGANTI, R.; ZOTTERI, G. Forecasting demand from heterogeneous customers. [[International "
        "Journal of Operations & Production Management]], v. 26, n. 6, p. 619–638, 2006.",
    ],
    294: [  # após PAVLYSHENKO
        "PEARSON, R. K.; NEUVO, Y.; ASTOLA, J.; GABBOUJ, M. Generalized Hampel filters. [[EURASIP Journal on Advances in "
        "Signal Processing]], v. 2016, art. 87, 2016.",
    ],
    297: [  # após SYNTETOS; BOYLAN
        "SYNTETOS, A. A.; BOYLAN, J. E.; CROSTON, J. D. On the categorization of demand patterns. [[Journal of the "
        "Operational Research Society]], v. 56, n. 5, p. 495–503, 2005.",
        "TEUNTER, R. H.; SYNTETOS, A. A.; BABAI, M. Z. Intermittent demand: linking forecasting to inventory "
        "obsolescence. [[European Journal of Operational Research]], v. 214, n. 3, p. 606–615, 2011.",
    ],
    299: [  # após WIRTH; HIPP
        "ZOTTERI, G.; KALCHSCHMIDT, M. A model for selecting the appropriate level of aggregation in forecasting "
        "processes. [[International Journal of Production Economics]], v. 108, n. 1-2, p. 74–83, 2007.",
    ],
}
for idx, items in refs_after.items():
    insert_after(P(idx), *[ref(t) for t in items])

# --------------------------------------------------------------------------
# SUMÁRIO
# --------------------------------------------------------------------------
sdt = K[49]
toc_ps = list(sdt.iter(q("p")))


def toc_entry_set(p, label, anchor=None):
    hl = p.find(q("hyperlink"))
    hl.find(q("r")).find(q("t")).text = label
    if anchor:
        hl.set(q("anchor"), anchor)
        for it in hl.iter(q("instrText")):
            it.text = "PAGEREF %s \\h" % anchor


by_label = {text_of(p).rstrip("0123456789 "): p for p in toc_ps}
e64 = by_label["6.4 Ferramentas de Modelagem"]
e65 = by_label["6.5 Procedimentos de Testes e Validação"]
toc_entry_set(e64, "6.5 Ferramentas de Modelagem")
toc_entry_set(e65, "6.6 Procedimentos de Testes e Validação")
new_e = copy.deepcopy(e64)
new_e.set("{%s}paraId" % W14, new_pid())
toc_entry_set(new_e, "6.4 Preparação dos Dados e Modelagem Preditiva", "_Toc900001")
e64.addprevious(new_e)

# linhas estáticas do sumário (capítulos 10 e 11 e Referências) viram entradas com PAGEREF
last9 = by_label["9 PROTOTIPAÇÃO"]
static = K[50]
outs = []
for label, anchor in [("10 RESULTADOS", "_Toc900010"), ("11 CRONOGRAMA DO PROJETO", "_Toc900011"),
                      ("REFERÊNCIAS", "_Toc900012")]:
    e = copy.deepcopy(last9)
    e.set("{%s}paraId" % W14, new_pid())
    toc_entry_set(e, label, anchor)
    outs.append(e)
static.addprevious(outs[0])
outs[0].addnext(outs[1])
outs[1].addnext(outs[2])
remove(static)

# legendas e figuras ficam com o elemento seguinte (figura/tabela e fonte)
cap_re = re.compile(r"^(Figura|Tabela) \d+ –")
for p in body.iter(q("p")):
    is_cap = bool(cap_re.match(text_of(p).strip()))
    has_img = p.find(".//" + q("drawing")) is not None
    if not (is_cap or has_img):
        continue
    ppr = p.find(q("pPr"))
    if ppr is None:
        ppr = etree.Element(q("pPr"))
        p.insert(0, ppr)
    if ppr.find(q("keepNext")) is None:
        kn = etree.Element(q("keepNext"))
        st = ppr.find(q("pStyle"))
        if st is not None:
            st.addnext(kn)
        else:
            ppr.insert(0, kn)

# fim do campo do sumário passa para a última entrada (remove a linha em branco)
end_p = toc_ps[-1]
end_run = end_p.find(q("r"))
last9.find(q("hyperlink")).addnext(end_run)
end_p.getparent().remove(end_p)

set_ppr_spacing_after(P(299), 240)

tree.write(DST, xml_declaration=True, encoding="UTF-8", standalone=True)
print("ok")
