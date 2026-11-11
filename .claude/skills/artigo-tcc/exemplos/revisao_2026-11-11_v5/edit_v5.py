"""v5 como versão completa: ADR-022 (545 dias), ADR-023 (histórico), E12 (janela), E13 (solução
definitiva do treino 15 do Neon), Seção 7.2 (métricas), Seção 7.5 (testes), referências novas."""
import copy
import re
import sys

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
q = lambda t: f"{{{W}}}{t}"
XS = "{http://www.w3.org/XML/1998/namespace}space"
NB = " "
doc_path, art_path = sys.argv[1], sys.argv[2]
tree = etree.parse(doc_path)
body = tree.getroot().find(q("body"))


def text(p):
    return "".join(t.text or "" for t in p.iter(q("t")))


def find(prefix, tag="p"):
    hits = [p for p in body if p.tag == q(tag) and text(p).startswith(prefix)]
    assert len(hits) == 1, (prefix, len(hits))
    return hits[0]


def find_tbl(contains):
    hits = [t for t in body if t.tag == q("tbl") and contains in text(t)]
    assert len(hits) == 1, (contains, len(hits))
    return hits[0]


def runs_from(s, base_rpr=None):
    """[[x]] itálico, {{x}} negrito."""
    out = []
    for part in re.split(r"(⟨.*?⟩|⟪.*?⟫)", s):
        if not part:
            continue
        r = etree.Element(q("r"))
        rpr = copy.deepcopy(base_rpr) if base_rpr is not None else None
        if part[0] in "⟨⟪":
            rpr = rpr if rpr is not None else etree.Element(q("rPr"))
            etree.SubElement(rpr, q("i" if part[0] == "⟨" else "b"))
            part = part[1:-1]
        if rpr is not None:
            r.append(rpr)
        t = etree.SubElement(r, q("t"))
        t.text = part
        t.set(XS, "preserve")
        out.append(r)
    return out


def set_text(p, s, keep_rpr=False):
    base = None
    if keep_rpr:
        r0 = p.find(q("r"))
        base = r0.find(q("rPr")) if r0 is not None else None
    for c in [c for c in p if c.tag != q("pPr")]:
        p.remove(c)
    for r in runs_from(s, base):
        p.append(r)


def clean_ids(el):
    for e in el.iter():
        for a in list(e.attrib):
            if a.endswith("paraId") or a.endswith("textId"):
                del e.attrib[a]
    for b in list(el.iter(q("bookmarkStart"))) + list(el.iter(q("bookmarkEnd"))):
        b.getparent().remove(b)
    return el


def clone(model, s, keep_rpr=False):
    p = clean_ids(copy.deepcopy(model))
    set_text(p, s, keep_rpr)
    return p


def rep(p, old, new):
    for t in p.iter(q("t")):
        if t.text and old in t.text:
            t.text = t.text.replace(old, new)
            return
    raise AssertionError(("não achei", old, text(p)[:80]))


def cell_set(tc, s):
    p = tc.find(q("p"))
    rs = p.findall(q("r"))
    base = rs[0].find(q("rPr")) if rs else None
    for r in rs:
        p.remove(r)
    for r in runs_from(s, base):
        p.append(r)


def row_set(tr, values):
    tcs = tr.findall(q("tc"))
    assert len(tcs) == len(values), (len(tcs), values)
    for tc, v in zip(tcs, values):
        cell_set(tc, v)


def after(anchor, *els):
    for e in reversed(els):
        anchor.addnext(e)


LOG = f"log(1{NB}+{NB}y)"

# ---------- modelos de parágrafo ----------
m_body = find("A análise exploratória classificou o padrão de demanda")
m_h2 = find("7.1 Caracterização da demanda")
m_cap = find("Tabela 10 – Erro e cobertura por semana do horizonte")
m_src = find("Fonte: Elaborado pelos autores (2026). Oito categorias, mesmos dias-alvo")
m_ref = find("HYNDMAN, R. J.; KOEHLER")

# ---------- 1.2 objetivos ----------
rep(find("\th)") if False else [p for p in body if p.tag == q("p") and "com as métricas de erro MASE, MAE e RMSE" in text(p)][0],
    "com as métricas de erro MASE, MAE e RMSE", "com as métricas de erro MASE, MAE, RMSE e WAPE")

# ---------- 3.6 referencial: Diebold-Mariano e Holm ----------
after(find("Para a avaliação de previsões, Hyndman e Koehler (2006)"), clone(m_body,
    "Para verificar se a diferença de erro entre duas previsões da mesma série é estatisticamente "
    "significativa, Diebold e Mariano (1995) propuseram um teste da hipótese de igual acurácia baseado na "
    "série das diferenças entre as perdas das duas previsões, válido para erros autocorrelacionados, como "
    "os de previsões com vários dias de horizonte. Quando o teste é repetido em muitas séries, o "
    "procedimento de Holm (1979) ajusta os valores-p para controlar a probabilidade de ao menos um falso "
    "positivo no conjunto."))

# ---------- 4.5 modelo preditivo ----------
p = find("Os valores de p e q são testados entre 0 e 2")
rep(p, "janela de 365 dias anterior", "janela de 545 dias anterior")
rep(p, "os 365 dias mais recentes", "os 545 dias mais recentes")
rep(p, "Seção 7.2", "Seção 7.3")
rep(find("O efeito das datas comemorativas é aplicado depois do ajuste"),
    "cada data aparece uma única vez na janela de 365 dias", "cada data aparece no máximo duas vezes na janela de 545 dias")
set_text(find("A previsão de cada dia é preservada depois que o dia passa"),
    "A previsão de cada dia é preservada depois que o dia passa, formando um histórico congelado que guarda, "
    "para cada dia, a previsão mais antiga feita para ele, que não é trocada por treinamentos posteriores. "
    "Cada treinamento grava apenas os dias ainda sem registro: os 14 primeiros dias da sua previsão e, para "
    "os dias que nenhuma previsão cobriu, como os anteriores ao primeiro treinamento ou os de intervalos "
    "maiores que 14 dias entre treinamentos, a janela mais antiga da validação ⟨walk-forward⟩ que os "
    "previu, até 14 dias antes. Assim, o histórico compara a quantidade vendida com a previsão feita com a "
    "antecedência com que a loja planeja a compra, sem reescrever o passado.")

# ---------- 4.6 delineamento ----------
rep(find("A configuração da solução final foi definida por uma sequência"), "na Seção 7.2", "na Seção 7.3")
set_text(find("A métrica primária é o MASE"),
    "A métrica de referência é o MASE, calculado com a escala da previsão ingênua sazonal semanal no "
    "período de treinamento. Como essa escala pode tornar o MASE otimista quando o treinamento contém "
    "picos, reporta-se também o erro relativo à previsão ingênua na mesma janela de teste, dado pela razão "
    "entre o erro absoluto acumulado do modelo e o da previsão ingênua, o número de janelas em que o "
    "modelo supera a previsão ingênua, o MAE e a RMSE em unidades vendidas, o WAPE, que divide o erro "
    "absoluto acumulado pelo volume vendido, a cobertura empírica e a largura média do intervalo de 95%, a "
    "razão entre o volume previsto e o vendido, que mede o viés da previsão, e o erro no total da janela, "
    "que compara a soma prevista com a soma vendida. Na avaliação por categoria e por produto, as métricas "
    "são calculadas apenas nos dias de loja aberta, pois domingos e feriados, com venda e previsão "
    "próximas de zero, reduzem o MASE e elevam a cobertura sem informar sobre a qualidade da previsão. "
    "Diferenças de erro inferiores a 5% foram tratadas como empate, e, nos experimentos E9 e E12, a "
    "significância das diferenças foi verificada pelo teste de Diebold e Mariano (1995). A Seção 7.2 "
    "relaciona cada métrica à decisão de compra.")

# ---------- 4.7 testes ----------
rep(find("\ta)", ) if False else [p for p in body if p.tag == q("p") and "e em cada origem o modelo é reajustado nos 365 dias anteriores" in text(p)][0],
    "reajustado nos 365 dias anteriores", "reajustado nos 545 dias anteriores")
pc = [p for p in body if p.tag == q("p") and "com 193 casos, sendo 120 unitários e 73 de integração" in text(p)][0]
rep(pc, "com 193 casos, sendo 120 unitários e 73 de integração", "com 196 casos, sendo 120 unitários e 76 de integração")
rep(pc, "Na execução realizada em novembro de 2026, os 193 casos foram aprovados.",
    "A importação também foi testada com planilhas que contêm erros conhecidos.")
rep(pc, "Complementam esses testes", "Os resultados desses testes são apresentados na Seção 7.5. Complementam esses testes")

# ---------- 5.3 RN03 ----------
rep([p for p in body if p.tag == q("p") and "RN03:" in text(p)][0],
    "de modo que o histórico reflita a previsão disponível antes de cada venda",
    "de modo que o histórico reflita a previsão mais antiga feita para cada dia")

# ---------- 6 interface ----------
rep(find("O painel do sistema, implementado em React"),
    ", com a base real de vendas e o treinamento descrito na Seção 7.3.", ", com a base real de vendas.")
rep(find("O núcleo analítico da solução está na tela de previsão"),
    "na qual os dias de loja fechada são sinalizados.",
    "na qual os dias de loja fechada são sinalizados. Nos quatro produtos de grama de pouco volume de "
    "Jardim Canadá que erram mais que a previsão ingênua já nas duas primeiras semanas (Seção 7.3), um "
    "ícone de informação explica que os números servem como referência, junto com a experiência da loja.")
rep(find("A aba de histórico, apresentada na Figura 12"),
    "com a previsão que estava disponível antes daquele dia (RF08)",
    "com a previsão mais antiga feita para ele, até 14 dias antes, e informa, ao passar o cursor sobre o "
    "dia, com quantos dias de antecedência ele foi previsto (RF08)")

# ---------- 7 resultados: abertura e subseções ----------
set_text(find("Esta seção apresenta a caracterização da demanda obtida"),
    "Esta seção apresenta a caracterização da demanda obtida na análise exploratória, as métricas de "
    "avaliação e a sua relação com a decisão de compra, os resultados dos experimentos E1 a E12, que "
    "fundamentaram a configuração do modelo, o desempenho da solução definitiva (E13) e os testes do "
    "sistema, seguidos da discussão das limitações.")
rep(find("7.4 Discussão e limitações"), "7.4 ", "7.6 ")
rep(find("7.3 Desempenho da solução definitiva"), "7.3 ", "7.4 ")
h_exp = find("7.2 Resultados dos experimentos")
rep(h_exp, "7.2 ", "7.3 ")

h_met = clone(m_h2, "7.2 Métricas de avaliação e decisão de compra", keep_rpr=True)
met = [
    "As métricas da validação ⟨walk-forward⟩ foram escolhidas pela decisão que a previsão apoia, a compra "
    "de produtos perecíveis para os dias seguintes, e são calculadas apenas nos dias de loja aberta, pois aos "
    "domingos e nos feriados a venda e a previsão são nulas, e esses dias reduziriam o erro sem informar nada "
    "sobre o modelo. O MAE expressa o erro na unidade de venda, em unidades por dia, e pode ser comparado "
    "diretamente com a quantidade comprada. O WAPE expressa o mesmo erro como percentual do volume vendido e, "
    "ao contrário do MAPE, não se torna indefinido nem cresce sem limite nos dias de venda nula ou muito "
    "baixa, frequentes nos produtos de grama, limitação dos erros percentuais apontada por Hyndman e Koehler "
    "(2006).",
    "A referência de comparação é a previsão ingênua sazonal, que repete as vendas do mesmo dia da semana "
    "anterior e equivale à estimativa mais simples que a loja faria sem o sistema. O erro relativo, razão "
    "entre a soma dos erros absolutos do modelo e a da previsão ingênua na mesma janela de teste, e o número "
    "de janelas em que o modelo a supera indicam se a previsão acrescenta informação a essa prática. O MASE "
    "responde à mesma pergunta com a escala medida no período de treinamento e permite comparar séries de "
    "volumes distintos, mas essa escala muda quando o tratamento dos dados altera os picos do treinamento, "
    "como na separação das encomendas, e por isso as variantes do critério de encomenda, no experimento E5, "
    "foram comparadas pelo erro relativo.",
    "Como a compra é planejada sobre o volume de vários dias, a razão entre o volume previsto e o vendido e o "
    "erro no total da janela, isto é, a diferença absoluta entre a soma prevista e a soma vendida dividida "
    "pela soma vendida, indicam se a previsão levaria a comprar a mais, com risco de descarte dos perecíveis, "
    "ou a menos, com risco de ruptura. O erro de cada dia e o erro do total podem divergir, pois erros de "
    "sinais opostos em dias diferentes se compensam na soma. Foi o que ocorreu nos experimentos E6 e E7, em "
    f"que {LOG} reduziu o MAE diário, mas previu de 48% a 90% do volume vendido, e no E10, em que o fator "
    "das datas comemorativas reduziu o erro da semana sem reduzir de forma consistente o erro de cada dia. "
    "Nos dois casos, a escolha seguiu o volume, que é a grandeza usada na compra.",
    "A cobertura e a largura do intervalo de 95% avaliam a faixa provável exibida no painel. A cobertura "
    "indica se a faixa pode ser usada como margem para a compra, e a largura, se ela é estreita o bastante "
    "para orientar uma quantidade, pois uma faixa larga demais contém quase todas as vendas sem ajudar a "
    "decidir. Nas séries de menor volume, parte da cobertura decorre dos dias sem venda, porque a previsão e "
    "o intervalo são truncados em zero e toda venda nula fica dentro da faixa, o que deve ser considerado na "
    "leitura das coberturas de 100% da Tabela 12. Por fim, quando duas configurações apresentaram erros "
    "próximos, como nos experimentos E9 e E12, o teste de Diebold e Mariano (1995) verificou se a diferença "
    "entre elas era estatisticamente significativa.",
]
h_exp.addprevious(h_met)
for s in met:
    h_exp.addprevious(clone(m_body, s))

# ---------- Quadro 5: E12 e E13 ----------
q5 = find_tbl("Configurações comparadas")
r12 = [tr for tr in q5.findall(q("tr")) if text(tr).startswith("E12")][0]
r13 = clean_ids(copy.deepcopy(r12))
row_set(r12, ["E12", "Janela de treinamento e horizonte", "23 séries com previsão, 51 cortes semanais",
              "Janelas de 90, 180, 270, 365 e 545 dias e histórico inteiro, horizonte de 2 semanas a 3 meses"])
row_set(r13, ["E13", "Solução definitiva",
              "Quatro categorias e produtos de grama das duas unidades, 56 origens diárias",
              "Configuração final (Seção 4.5)"])
r12.addnext(r13)

# ---------- E12: texto e Tabela 11 ----------
t10 = find_tbl("Semana do horizonte")
t11 = clean_ids(copy.deepcopy(t10))
trs = t11.findall(q("tr"))
head, mid, last = trs[0], trs[1], trs[-1]
for tr in trs[1:]:
    t11.remove(tr)
WID = [3312] + [1152] * 5
grid = t11.find(q("tblGrid"))
grid.remove(grid.findall(q("gridCol"))[-1])
for gc, w in zip(grid.findall(q("gridCol")), WID):
    gc.set(q("w"), str(w))
for tr in (head, mid, last):
    tr.remove(tr.findall(q("tc"))[-1])
    for tc, w in zip(tr.findall(q("tc")), WID):
        tc.find(q("tcPr")).find(q("tcW")).set(q("w"), str(w))
row_set(head, ["Unidade e categoria", "90 dias", "180 dias", "270 dias", "545 dias", "Histórico inteiro"])
dados = [
    ["Itabirito, Flores de corte", "+8,9%", "+11,4%", "+5,4%", "−6,2%", "−7,9%"],
    ["Itabirito, Grama", "+11,6%", "+2,9%", "+0,4%", "−2,0%", "−1,9%"],
    ["Itabirito, Plantas diversas", "+4,3%", "+0,8%", "+0,7%", "−0,6%", "0,0%"],
    ["Itabirito, Produtos de jardim", "+7,8%", "+2,9%", "+1,2%", "−1,6%", "−2,3%"],
    ["Jardim Canadá, Flores de corte", "+20,9%", "+5,3%", "0,0%", "−3,8%", "−4,9%"],
    ["Jardim Canadá, Grama", "+8,3%", "+1,5%", "0,0%", "+0,3%", "−0,2%"],
    ["Jardim Canadá, Plantas diversas", "+1,1%", "−1,4%", "−0,4%", "−1,3%", "+0,5%"],
    ["Jardim Canadá, Produtos de jardim", "+7,3%", "+0,3%", "+0,9%", "−0,2%", "−0,8%"],
    ["Média das 8 categorias", "+8,6%", "+2,9%", "+1,0%", "−1,9%", "−2,2%"],
    ["Média das 23 séries", "+5,5%", "+0,4%", "−0,9%", "−1,9%", "−1,3%"],
]
for i, vals in enumerate(dados):
    tr = clean_ids(copy.deepcopy(last if i == len(dados) - 1 else mid))
    row_set(tr, vals)
    t11.append(tr)

src10 = m_src
e12_a = clone(m_body,
    "O experimento E12 avaliou a janela de treinamento e o horizonte de previsão nas 23 séries com previsão. "
    "Cada série foi treinada em 51 cortes semanais, de março de 2025 a fevereiro de 2026, com a configuração "
    "de produção, trocando apenas a janela de treinamento, de 90, 180, 270, 365 ou 545 dias ou o histórico "
    "inteiro, e as diferenças foram verificadas pelo teste de Diebold e Mariano (1995), com o ajuste de Holm "
    "(1979) para as 23 séries. A Tabela 11 mostra que a janela de 90 dias errou 8,6% a mais que a de 365 dias "
    "nas categorias, e que a de 545 dias foi a melhor janela única, com erro 1,9% menor nas 23 séries e nas "
    "categorias. O maior ganho ocorreu em Flores de corte, de 3,8% em Jardim Canadá e de 6,2% em Itabirito, "
    "pois, com mais de um ano de janela, o modelo observa cada data comemorativa mais de uma vez. O histórico "
    "inteiro reduziu o erro das categorias em 2,2%, mas ficou atrás da janela de 545 dias no conjunto das 23 "
    "séries, com redução de 1,3%. Depois do ajuste de Holm, o ganho da melhor janela foi significativo em "
    "quatro séries, Flores de corte de Itabirito e três produtos de grama de pouco volume de Jardim Canadá.")
cap11 = clone(m_cap, "Tabela 11 – Variação do erro em relação à janela de 365 dias (E12)", keep_rpr=True)
src11 = clone(src10, "Fonte: Elaborado pelos autores (2026). MAE dos 14 dias seguintes a cada corte, dias de "
              "loja aberta, 51 cortes semanais de março de 2025 a fevereiro de 2026, médias geométricas das "
              "razões ao MAE da janela de 365 dias.", keep_rpr=True)
e12_b = clone(m_body,
    "Segundo Pesaran e Timmermann (2007), a janela longa estima melhor os parâmetros, mas pode misturar "
    "comportamentos antigos, e, nas séries grandes, a escolha de d pela validação compensa as mudanças de "
    "nível. Escolher a janela em cada série, pelo erro dos oito cortes anteriores, reduziria o erro dos "
    "produtos de grama em 8,8% e o das categorias em 1,1%, mas o ganho vem de gramas de baixo volume e "
    "tornaria o treinamento cerca de seis vezes mais lento, por isso a solução adotou 545 dias em todas as "
    "séries. A regra de venda em pelo menos 28 dias continua medida nos 365 dias mais recentes, "
    "independentemente da janela de treinamento.")
e12_c = clone(m_body,
    "Com a melhor janela de cada série, o erro das categorias subiu 3,0% na quarta semana e 6,6% no terceiro "
    "mês em relação às duas primeiras semanas, sem perder da previsão ingênua, e a cobertura do intervalo de "
    "95% ficou entre 88% e 97% até três meses. Pelo teste de Diebold e Mariano, as séries de temporada de "
    "Jardim Canadá, Grama, Plantas diversas e Produtos de jardim, a Grama Esmeralda de Jardim Canadá e a "
    "Grama Esmeralda (ITO) de Itabirito pioraram de forma significativa a partir da quarta à oitava semana, "
    "enquanto Flores de corte das duas unidades e Plantas diversas e Produtos de jardim de Itabirito não "
    "pioraram até três meses. Quatro produtos de grama de pouco volume de Jardim Canadá já erraram mais que "
    "a previsão ingênua nas duas primeiras semanas, e a tela de previsão indica, para eles, que os números "
    "servem como referência, junto com a experiência da loja.")
after(src10, e12_a, cap11, t11, src11, e12_b, e12_c)

# ---------- 7.4 solução definitiva (E13, treino 15) ----------
rep(find("Tabela 11 – Desempenho da solução definitiva por série (E12)"), "Tabela 11 – ", "Tabela 12 – ")
rep(find("Tabela 12 – Desempenho da solução definitiva por série (E12)"), "(E12)", "(E13)")
set_text(find("A solução definitiva foi avaliada pelo próprio treinamento"),
    "A solução definitiva foi avaliada pelo próprio treinamento do sistema, executado sobre a base completa, "
    "com vendas até 28 de fevereiro de 2026 (experimento E13). Foram identificadas 43 séries: as quatro "
    "categorias de cada unidade e 35 combinações de produto de grama e unidade, 18 em Itabirito e 17 em "
    "Jardim Canadá. Dessas combinações, 20 ficaram sem previsão por não atenderem ao requisito mínimo de "
    "dados, 17 por terem vendido em menos de 28 dos últimos 365 dias e 3 por terem menos de 180 dias de "
    "histórico. As 23 séries restantes, 8 categorias e 15 produtos de grama, foram validadas em 56 origens, "
    "de 22 de dezembro de 2025 a 15 de fevereiro de 2026, com dias avaliados até 28 de fevereiro de 2026, e "
    "receberam a previsão de 1º de março a 30 de maio de 2026. A diferenciação escolhida foi d = 1 em 9 "
    "séries e d = 0 em 14. O treinamento de produção, com a janela de 545 dias, foi executado sobre o banco "
    "de dados de publicação com 12 processos paralelos e levou 75 minutos, dentro do limite de duas horas do "
    "requisito RNF03. A Tabela 12 apresenta o desempenho de cada série.")

art = etree.parse(art_path).getroot().find(q("body"))
art_t1 = [t for t in art if t.tag == q("tbl") and "Previsto / vendido" in text(t) and "ITA, Grama" in text(t)][0]
t12 = find_tbl("ITA, Grama Esmeralda (ITO)")
a_rows, v_rows = art_t1.findall(q("tr")), t12.findall(q("tr"))
assert len(a_rows) == len(v_rows)
for ar, vr in zip(a_rows, v_rows):
    vals = [text(tc) for tc in ar.findall(q("tc"))]
    assert text(vr.findall(q("tc"))[0]) == vals[0], (text(vr), vals)
    row_set(vr, vals)

set_text(find("Nas categorias, o MASE ficou abaixo de 1 em sete das oito"),
    "Nas oito categorias, o MASE ficou abaixo de 1, entre 0,637 e 0,980, e o erro foi menor que o da "
    "previsão ingênua, com erro relativo entre 0,738 e 0,958. A cobertura do intervalo de 95% ficou entre "
    "90,5% e 100,0%, acima de 98% em Flores de corte nas duas unidades, o que indica, nessas séries, um "
    "intervalo mais largo que o necessário. Entre os 15 produtos de grama, o MASE ficou abaixo de 1 em 11 "
    "séries, o erro relativo ficou abaixo de 1 em 10 das 14 séries com venda no período, e a cobertura ficou "
    "entre 91,1% e 100,0%.")
set_text(find("O teste de Ljung-Box não rejeitou a ausência de autocorrelação residual em nenhuma"),
    "O teste de Ljung-Box não rejeitou a ausência de autocorrelação residual em 22 das 23 séries, com "
    "exceção da Grama Esmeralda de Itabirito (p = 0,042), o que indica que os modelos capturaram a "
    "dependência entre os dias e o padrão semanal das vendas. O teste de Shapiro-Wilk rejeitou a normalidade "
    "dos resíduos em todas elas (p < 0,001), comportamento esperado em vendas com dias de pico. Por isso, a "
    "cobertura dos intervalos foi verificada empiricamente, e as coberturas obtidas, entre 90,5% e 100,0%, "
    "ficaram próximas ou acima do nível nominal de 95%.")
rep(find("Em todas as categorias, o volume previsto superou o vendido"), "de 107% a 157%", "de 109% a 151%")
set_text(find("Nos produtos de grama de menor volume, o MASE e o erro relativo"),
    "Nos produtos de grama de menor volume, o MASE e o erro relativo à previsão ingênua divergiram. O Capim "
    "dos Texas roxo (1293) de Jardim Canadá obteve MASE de 2,236, mas errou 43% menos que a previsão "
    "ingênua e previu 37% do volume vendido, enquanto o Capim dos Texas roxo (00020227), com MASE de 0,759, "
    "errou o dobro da previsão ingênua e previu 2,7 vezes o vendido. O mesmo ocorreu com a Grama Esmeralda de "
    "Itabirito, com MASE de 1,238 e erro relativo de 0,895, e com o Capim dos Texas verde, com MASE de 0,574 "
    "e erro relativo de 1,986. A escala do MASE vem do erro da previsão ingênua no período de treinamento, e "
    "a divergência surge quando o nível de vendas muda entre o treinamento e a validação: se o produto "
    "vendia pouco no treinamento, a escala é pequena e o MASE fica alto mesmo com erro menor que o da "
    "previsão ingênua, e, no caso inverso, o MASE fica baixo mesmo com erro maior.")
p398 = find("As duas séries têm padrão intermitente")
set_text(p398,
    "Essas séries têm padrão intermitente e foram modeladas por atenderem ao requisito mínimo de 28 dias com "
    "venda no último ano. Para esse padrão, a literatura recomenda métodos específicos de demanda "
    "intermitente (Seção 3.3), e o MASE, calculado com a escala do treinamento, não reflete mudanças de "
    "nível entre o treinamento e o teste. Por isso, nessas séries, o erro relativo na própria janela de teste "
    "e a razão entre o previsto e o vendido descrevem melhor o desempenho observado.")
after(p398, clone(m_body,
    "No mesmo período de validação e com a mesma base, o treinamento com a janela de 365 dias tinha MASE "
    "abaixo de 1 em sete das oito categorias. A janela de 545 dias reduziu o MAE das categorias em 2,0%, com "
    "melhora em seis delas, sobretudo em Flores de corte de Itabirito (8,2%), e manteve praticamente igual o "
    "erro dos produtos de grama (+0,2%), resultado coerente com o experimento E12."))

# ---------- 7.5 testes do sistema ----------
h_disc = find("7.6 Discussão e limitações")
h_disc.addprevious(clone(m_h2, "7.5 Testes do sistema", keep_rpr=True))
h_disc.addprevious(clone(m_body,
    "Os testes automatizados, descritos na Seção 4.7, somam 196 casos em ⟨pytest⟩, 120 unitários e 76 de "
    "integração, e verificam a seleção da ordem e da diferenciação, a validação ⟨walk-forward⟩ e as "
    "métricas do treinamento, o fator das datas comemorativas, a regra do histórico das previsões, a "
    "conferência das planilhas, a autenticação e os perfis de acesso e as respostas do painel. Na execução "
    "de 10 de novembro de 2026, os 196 casos foram aprovados."))
h_disc.addprevious(clone(m_body,
    "A importação foi testada com planilhas de vendas fictícias de março de 2026, no formato do relatório da "
    "empresa, enviadas a uma cópia da base com as vendas até 28 de fevereiro de 2026. A planilha com erros "
    "reúne 14 casos, como nota sem cliente, data inexistente, quantidade em texto, empresa sem loja "
    "cadastrada, vendas que já estavam na base e dias de loja aberta sem venda. Na conferência, o sistema "
    "informou 12.388 vendas novas, 22 já carregadas e 19 linhas ignoradas, avisou os dias sem venda de cada "
    "unidade, um em Jardim Canadá e três em Itabirito, e marcou como encomendas grandes os dois pedidos acima "
    "do limiar recalculado de cada loja. A mesma planilha, enviada de novo, foi recusada sem duplicar dados. "
    "O teste também mostrou um caso não detectado: uma nota repetida inteira dentro da mesma planilha entra "
    "duas vezes, porque a duplicidade é verificada apenas contra a base já gravada."))

# ---------- 7.6 discussão e 8 conclusão ----------
rep(find("As escolhas de modelagem com maior efeito medido"),
    "O fator das datas comemorativas corrige o volume da semana da data, mas não o dia do pico.",
    "O fator das datas comemorativas corrige o volume da semana da data, mas não o dia do pico. A janela de "
    "treinamento de 545 dias reduziu o erro em 1,9% em relação à de 365 dias, com o maior ganho em Flores de "
    "corte, cujas datas comemorativas passam a aparecer mais de uma vez na janela.")
rep(find("A principal limitação está nas encomendas grandes"),
    "não permite estimar a sazonalidade anual, e o fator",
    "não permite estimar a sazonalidade anual, a janela de 545 dias foi avaliada em um único ano de vendas, e o fator")
rep(find("A sequência de experimentos permitiu medir"), "17 das 23 séries", "19 das 23 séries")

# ---------- lista de tabelas ----------
ent = find("Tabela 11 –\tDesempenho") if False else [p for p in body if p.tag == q("p") and text(p).startswith("Tabela 11 –Desempenho")][0]
novo = clean_ids(copy.deepcopy(ent))
rep(ent, "Tabela 11 –", "Tabela 12 –")
rep(ent, "(E12)", "(E13)")
rep(novo, "Desempenho da solução definitiva por série (E12)", "Variação do erro em relação à janela de 365 dias (E12)")
ent.addprevious(novo)

# ---------- referências ----------
def ref(after_prefix, s):
    p = clean_ids(copy.deepcopy(m_ref))
    for c in [c for c in p if c.tag != q("pPr")]:
        p.remove(c)
    for r in runs_from(s):
        p.append(r)
    find(after_prefix).addnext(p)

ref("CROSTON, J. D.", "DIEBOLD, F. X.; MARIANO, R. S. Comparing predictive accuracy. ⟪Journal of Business & "
    "Economic Statistics⟫, [⟨S. l.⟩], v. 13, n. 3, p. 253-263, 1995.")
ref("GROSS, C. W.", "HOLM, S. A simple sequentially rejective multiple test procedure. ⟪Scandinavian Journal of "
    "Statistics⟫, [⟨S. l.⟩], v. 6, n. 2, p. 65-70, 1979.")
ref("MAKRIDAKIS, S.", "PESARAN, M. H.; TIMMERMANN, A. Selection of estimation window in the presence of breaks. "
    "⟪Journal of Econometrics⟫, [⟨S. l.⟩], v. 137, n. 1, p. 134-161, 2007.")

tree.write(doc_path, xml_declaration=True, encoding="UTF-8", standalone=True)
print("ok")
