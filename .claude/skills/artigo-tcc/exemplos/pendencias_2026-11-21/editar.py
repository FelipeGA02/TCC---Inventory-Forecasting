# -*- coding: utf-8 -*-
"""Correções de 21/11/2026 sobre o 'Final - Corrigido' (pendências do orientador e revisão)."""
import copy
import sys

sys.path.insert(0, "/home/dev/TCC---Inventory-Forecasting/.claude/skills/artigo-tcc/scripts")
from docx_lib import Doc, NBSP, q, text_of  # noqa: E402

d = Doc(sys.argv[1])


def par(contains):
    r = [p for p in d.paragraphs() if contains in text_of(p)]
    assert len(r) == 1, (contains, len(r))
    return r[0]


def rep(p, old, new):
    """Troca dentro de um único run (falha se o trecho estiver partido)."""
    for t in p.iter(q("t")):
        if t.text and old in t.text:
            t.text = t.text.replace(old, new, 1)
            return
    # trecho partido entre runs: reescreve o parágrafo preservando o itálico existente
    m = markup(p)
    assert old in m, "não achei: %r" % old
    d.set_text(p, m.replace(old, new, 1).rstrip(" "), rpr=d.base_rpr(p))


def markup(p):
    out = ""
    for r in p.iter(q("r")):
        t = "".join(x.text or "" for x in r.iter(q("t")))
        rp = r.find(q("rPr"))
        it = rp is not None and rp.find(q("i")) is not None
        out += "[[%s]]" % t if it and t.strip() else t
    return out.replace("]][[", "")


def italic(p, word):
    """Põe em itálico a 1ª ocorrência de `word` que esteja inteira num run sem itálico."""
    for r in list(p.iter(q("r"))):
        t = r.find(q("t"))
        rp = r.find(q("rPr"))
        if t is None or not t.text or word not in t.text:
            continue
        if rp is not None and rp.find(q("i")) is not None:
            continue
        a, b = t.text.split(word, 1)
        news = []
        if a:
            news.append(d.make_run(a, rp))
        news.append(d.make_run(word, rp, italic=True))
        if b:
            news.append(d.make_run(b, rp))
        for n in news:
            r.addprevious(n)
        r.getparent().remove(r)
        return
    raise ValueError("não achei para itálico: %r" % word)


# ---------------------------------------------------------------- Resumo e Abstract (item 17)
p = par("A cobertura do intervalo de predição ficou entre 91% a 100%")
rep(p, "A cobertura do intervalo de predição ficou entre 91% a 100%.",
    "A cobertura do intervalo de predição, isto é, a proporção de dias em que a venda real ficou "
    "dentro da faixa prevista, ficou entre 90,5% e 100%, próxima ou acima do nível nominal de 95%.")
p = par("The prediction-interval coverage ranged from 91% to 100%")
rep(p, "The prediction-interval coverage ranged from 91% to 100%.",
    "The prediction-interval coverage, that is, the share of days in which actual sales fell within "
    "the forecast range, ranged from 90.5% to 100%, close to or above the nominal level of 95%.")

# ---------------------------------------------------------------- 2.2 e 10.1.2 (rotina mensal)
rep(par("As vendas poderão ser enviadas semanalmente"),
    "As vendas poderão ser enviadas semanalmente", "As vendas poderão ser enviadas a cada mês")
rep(par("O objetivo é incorporar as vendas de cada semana"),
    "as vendas de cada semana", "as vendas de cada mês")

# ---------------------------------------------------------------- 5.3: refs. de demanda irregular
p = par("Esse fundamento delimita as séries modeladas neste trabalho")
rep(p, "restritas às de venda frequente.",
    "restritas às de venda frequente. Para as séries de venda esporádica, a literatura propõe métodos "
    "próprios, como o de Croston (1972), que prevê separadamente o tamanho das vendas e o intervalo "
    "entre elas, e suas variações (SYNTETOS; BOYLAN, 2005; TEUNTER; SYNTETOS; BABAI, 2011).")
d.set_text(par("Essa abordagem foi considerada e testada neste trabalho"),
           "Essa abordagem foi considerada e testada neste trabalho, com a previsão da venda total de "
           "cada loja repartida entre as categorias pela participação recente de cada uma (GROSS; SOHL, "
           "1990). Entretanto, os resultados obtidos foram inferiores aos alcançados pela previsão direta "
           "de cada categoria (Seção 11.5, experimento E4).", rpr=None)

# ---------------------------------------------------------------- 5.4: sem Iglewicz e Hoaglin
d.set_text(par("Observações atípicas podem distorcer"),
           "Observações atípicas podem distorcer os padrões identificados pelos modelos de previsão, "
           "porque afetam a estimação dos parâmetros e as previsões seguintes (CHEN; LIU, 1993), "
           "especialmente quando representam vendas muito superiores ao comportamento habitual. No "
           "contexto da floricultura, esses valores estavam associados principalmente a encomendas de "
           "grande porte, que não representavam a demanda regular do dia a dia. Pedidos grandes de "
           "poucos clientes podem ser tratados como um fluxo de demanda à parte, separado da venda "
           "regular (BARTEZZAGHI; VERGANTI, 1995; KALCHSCHMIDT; VERGANTI; ZOTTERI, 2006).", rpr=None)
d.set_text(par("Para identificar essas ocorrências, foi utilizado"),
           "Para identificar essas ocorrências, foi utilizado um critério baseado na média e no "
           "desvio-padrão das quantidades dos pedidos de cada loja, que classifica como atípicos os "
           "pedidos que ultrapassam a média em mais de quatro desvios-padrão, número de desvios "
           "definido experimentalmente (Seção 11.5, experimento E2). A média e o desvio-padrão das "
           "quantidades dos pedidos são calculados pelas Equações 1 e 2, e o limiar de cada loja, pela "
           "Equação 3:", rpr=None)

# ---------------------------------------------------------------- 6.1: sem CRISP-DM
d.set_text(par("A análise dos dados e a modelagem preditiva foi marcada"),
           "A análise dos dados e a modelagem preditiva seguiram a mesma lógica iterativa, da preparação "
           "dos dados ao modelo preditivo, ao delineamento experimental e aos testes e validação. A "
           "Figura 1 apresenta as etapas da metodologia.", rpr=None)
rep(par("O projeto foi organizado em oito iterações"),
    "entre abril e novembro de 2026 e encerrada com", "entre abril e novembro de 2026, cada uma encerrada com")

# ---------------------------------------------------------------- 6.3: itálico padronizado
italic(par("frameworks e bibliotecas do backend"), "python-jose")
for w in ("Vite", "Tailwind CSS", "MUI"):
    italic(par("frameworks e bibliotecas do painel"), w)
italic(par("análise exploratória e experimentos:"), "seaborn")
italic(par("para os testes unitários e de integração, e Playwright"), "Playwright")

# ---------------------------------------------------------------- 6.5
rep(par("Uma venda, identificada pela unidade"), " (IGLEWICZ; HOAGLIN, 1993)", "")
rep(par("as três ocorrências mais recentes da data.."), "da data..", "da data.")

# ---------------------------------------------------------------- 6.6: itálico
p = par("A validação estatística dos modelos é a validação walk-forward")
italic(p, "walk-forward")
italic(p, "Mean Absolute Error")

# ---------------------------------------------------------------- 10.2: Figura 10 × 11.3
rep(par("No exemplo, foi conferida, sem gravação"),
    "No exemplo, foi conferida, sem gravação, uma planilha de teste com vendas fictícias de março de 2026.",
    "No exemplo, foi conferida, sem gravação, a planilha de teste com vendas fictícias de março de 2026 "
    "descrita na Seção 11.3. Como a duplicidade é verificada pelo número do documento, pelo produto, pela "
    "data, pela quantidade e pelo valor, que são fictícios na base de demonstração, as 22 vendas que já "
    "estavam na base real aparecem como novas, e o total de vendas novas passa de 12.388 para 12.410.")

# ---------------------------------------------------------------- 11.3 (item 46)
rep(par("Na execução do grupo de scripts de teste"),
    "Na execução do grupo de scripts de teste para validar o comportamento e a estabilidade de um "
    "software, de 11 de novembro de 2026, os 196 testes em ",
    "Na execução da suíte de testes automatizados, em 11 de novembro de 2026, os 196 testes em ")

# ---------------------------------------------------------------- 11.5
rep(par("mas trata igualmente de lojas"), "mas trata igualmente de lojas",
    "mas trata da mesma forma lojas")
rep(par("A solução foi descartada e adotamos"),
    "A solução foi descartada e adotamos a escala original",
    "A solução foi descartada, e adotou-se a escala original")
rep(par("O experimento E5 avaliou a ordem de diferenciação"),
    "e por isso foi o critério adotado.",
    "e por isso foi o critério adotado. Os testes de raiz unitária serviram apenas de apoio: o KPSS "
    "(KWIATKOWSKI et al., 1992) indicou d" + NBSP + "=" + NBSP + "1 nas séries em que o nível das vendas "
    "muda ao longo do tempo, mas não tem poder para decidir as séries de baixo volume, e usá-lo como "
    "critério reduziu o erro em apenas 2,5%; o teste de Dickey-Fuller aumentado (Augmented "
    "Dickey-Fuller – ADF) rejeita a raiz unitária com frequência excessiva quando o termo de médias "
    "móveis é próximo de −1 (SCHWERT, 1989), situação comum nessas séries.")
p = par("O experimento E5 avaliou a ordem de diferenciação")
italic(p, "et al.")
italic(p, "Augmented Dickey-Fuller")
rep(par("O experimento E8 avaliou a janela de treinamento"),
    "e o sistema adotou 545 dias para todas as séries.",
    "e o sistema adotou 545 dias para todas as séries. Pelo teste de Diebold e Mariano (1995), com a "
    "correção de Holm (1979) para os 23 testes, o ganho da melhor janela de cada série sobre a de 365 "
    "dias foi significativo em quatro séries, Flores de corte de Itabirito e três produtos de grama de "
    "Jardim Canadá.")

# Quadro 7, linha E7: retreinamento mensal, como no texto do E7
for t in d.root.iter(q("t")):
    if t.text and "e retreinamento semanal" in t.text:
        t.text = t.text.replace("e retreinamento semanal", "e retreinamento mensal")
        break
else:
    raise ValueError("Quadro 7 E7")

# Tabela 4: nota
rep(par("(2026). ITA: Itabirito, JC: Jardim Canadá."),
    "ordem (p,d,q)(P,0,Q) com m = 7.",
    "ordem (p,d,q)(P,0,Q) com m = 7, erro relativo: erro do modelo dividido pelo da previsão ingênua, "
    "–: sem venda no período de validação.")

# ---------------------------------------------------------------- Siglas sem uso (MAPE, WAPE, ARIMA)
for sig in ("MAPE", "WAPE", "ARIMA"):
    hits = [p for p in d.paragraphs() if text_of(p).strip().startswith(sig)]
    if not hits:  # célula/linha de lista com tab
        hits = [p for p in d.paragraphs() if text_of(p).split("\t")[-2:-1] == [sig]
                or text_of(p).lstrip("\t").startswith(sig + "\t")]
    assert len(hits) == 1, (sig, len(hits))
    d.remove(hits[0])

# ---------------------------------------------------------------- Referências
d.remove(par("IGLEWICZ, B.; HOAGLIN, D. C."))
p = par("KWIATKOWSKI, D. et al.")
italic(p, "et al.")


d.save(sys.argv[1])
print("ok")
