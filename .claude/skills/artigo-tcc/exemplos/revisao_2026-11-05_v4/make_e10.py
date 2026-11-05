# -*- coding: utf-8 -*-
"""Gera e10.json: textos e Tabela 8 da solução definitiva (E10), a partir do treino reproduzido
no SQLite local (job 1, versão do código c8b0b5536596, dados até 28/02/2026), e o capítulo 7
com as telas capturadas do sistema em execução."""
import json
import os
import sys

NB = " "
d = NB + "=" + NB
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "e10.json")
TESTES = json.load(open(os.path.join(os.path.dirname(OUT), "testes.json"), encoding="utf-8"))
SHOT_W = 5760000
FONTE = "Fonte: Elaborado pelos autores (2026)."

fig_list = [
    (7, "Tela inicial com a análise das vendas"),
    (8, "Tela de envio de planilha"),
    (9, "Conferência da planilha antes da gravação"),
    (10, "Tela de conferência das vendas importadas"),
    (11, "Previsão diária dos 14 dias seguintes com a faixa provável"),
    (12, "Histórico da previsão: vendido e previsto"),
    (13, "Tela de relatórios"),
]


def fig(n, key):
    return ("fig", key, "Figura %d – %s" % (n, dict(fig_list)[n]), SHOT_W, FONTE)


cap7 = [
    ("h1", "7 INTERFACE DO SISTEMA"),
    ("p", "O painel do sistema, implementado em React, organiza as funcionalidades em cinco telas acessíveis pelo menu "
          "lateral: Início, Carregar Planilha, Conferir Dados, Previsão de Vendas e Relatórios. No cabeçalho, o botão "
          "“Treinar previsões”, visível apenas para o perfil de administrador, solicita o treinamento, e um painel de "
          "notificações informa o andamento do treinamento e a existência de vendas ainda não utilizadas pela "
          "previsão (RF09). As telas foram concebidas priorizando a usabilidade para usuários "
          "não técnicos, com linguagem simples e indicadores explicados, em conformidade com o requisito RNF01. As "
          "figuras a seguir foram capturadas do sistema em execução em ambiente local, com a base real de vendas e o "
          "treinamento descrito na Seção 8.3."),
    ("p", "A tela inicial, ilustrada na Figura 7, consolida a análise das vendas da base (RF05 e RF11): faturamento, "
          "número de notas, quantidade vendida e encomendas grandes, faturamento mensal com a venda do dia a dia e as "
          "encomendas grandes em destaque, faturamento médio por dia da semana, participação de cada categoria, "
          "comparação entre consumidores e clientes cadastrados, formas de pagamento e produtos mais vendidos no "
          "último ano (RF06), com filtro por unidade. Nenhum dado pessoal de cliente é exibido."),
    fig(7, "s1_inicio"),
    ("p", "A importação atende ao requisito RF01 e segue quatro etapas: envio do arquivo, conferência, gravação e "
          "conclusão (Figura 8). Uma planilha já carregada, identificada pelo [[hash]] SHA-256 do arquivo, é recusada "
          "sem duplicar dados. Na conferência, apresentada na Figura 9, o sistema processa a planilha sem gravá-la e "
          "informa o período de vendas de cada unidade, a última venda já carregada, o número de vendas novas e já "
          "existentes e, quando houver, os dias de loja aberta que ficariam sem venda e seriam tratados como venda "
          "zero pelos modelos (RF07); a gravação só ocorre após a confirmação do administrador. No exemplo, a planilha "
          "de fevereiro de 2026, regravada em um novo arquivo, não contém vendas novas."),
    fig(8, "s2_importar"),
    fig(9, "s3_conferencia"),
    ("p", "A tela de conferência das vendas importadas, apresentada na Figura 10, permite consultar as 345.491 linhas "
          "de venda da base, com busca por produto, código ou número da nota, filtros por mês, unidade e categoria, "
          "abas para encomendas grandes, clientes cadastrados, vendas com desconto e devoluções, detalhamento da nota "
          "completa e exportação do resultado do filtro."),
    fig(10, "s4_conferir"),
    ("p", "O núcleo analítico da solução está na tela de previsão (RF02 e RF04), ilustrada na Figura 11. Para cada "
          "unidade, a tela apresenta a venda das semanas anteriores e a previsão dos 14 dias seguintes por categoria "
          "ou por produto de grama, com a faixa provável correspondente ao intervalo de 95%, e uma tabela com a quantidade prevista em cada dia, na qual os dias de loja "
          "fechada e as datas comemorativas são sinalizados."),
    fig(11, "s5_previsao"),
    ("p", "A aba de histórico, apresentada na Figura 12, compara o vendido de cada dia, sem as encomendas grandes, com "
          "a previsão que estava disponível antes daquele dia (RF08) e resume a validação do modelo em quatro "
          "indicadores: o acerto no total de duas semanas, a proporção de dias em que a venda ficou dentro da faixa "
          "prevista, o número de janelas em que a previsão superou a repetição da semana anterior e a razão entre o "
          "volume previsto e o vendido."),
    fig(12, "s6_historico"),
    ("p", "Por fim, a tela de relatórios (RF10), apresentada na Figura 13, reúne o relatório gerencial em PDF, com a "
          "previsão dos 14 dias por categoria e por produto de grama, as encomendas grandes e a confiança da previsão, "
          "e relatórios de previsão, de histórico de vendas e de qualidade da previsão, com prévia na tela e "
          "exportação nos formatos Excel, CSV e PDF."),
    fig(13, "s7_exportar"),
]

# Tabela 8: valores do treino (series_models.metrics, dias de loja aberta)
rows8 = [
    ["ITA, Grama", "(1,0,2)(0,0,1)", "0,861", "0,805", "39", "97,5%", "128%"],
    ["ITA, Plantas diversas", "(0,0,2)(0,0,1)", "1,268", "1,026", "18", "95,4%", "124%"],
    ["ITA, Produtos de jardim", "(0,0,2)(1,0,1)", "0,907", "0,906", "34", "96,7%", "117%"],
    ["ITA, Flores de corte", "(0,0,2)(0,0,1)", "0,640", "1,001", "25", "98,7%", "149%"],
    ["JC, Grama", "(1,0,2)(0,0,1)", "0,855", "0,830", "45", "96,0%", "126%"],
    ["JC, Plantas diversas", "(1,0,2)(1,0,1)", "0,869", "0,884", "37", "96,8%", "143%"],
    ["JC, Produtos de jardim", "(0,0,2)(0,0,1)", "0,898", "0,963", "28", "94,0%", "135%"],
    ["JC, Flores de corte", "(0,0,2)(0,0,1)", "0,706", "0,797", "38", "98,1%", "117%"],
    ["ITA, Grama Esmeralda", "(0,0,2)(0,0,1)", "4,008", "0,649", "19", "94,5%", "31%"],
    ["ITA, Grama Esmeralda (ITO)", "(1,0,2)(1,0,1)", "0,861", "0,842", "45", "98,1%", "136%"],
    ["ITA, Grama Amendoim (bandeja)", "(2,0,2)(0,0,1)", "1,153", "0,838", "28", "96,8%", "103%"],
    ["ITA, Grama São Carlos", "(0,0,2)(0,0,1)", "0,740", "1,551", "10", "100,0%", "254%"],
    ["JC, Grama Esmeralda", "(1,0,2)(1,0,1)", "0,970", "0,853", "44", "98,7%", "119%"],
    ["JC, Grama Esmeralda (ITO)", "(0,0,2)(0,0,1)", "0,792", "1,761", "10", "97,8%", "317%"],
    ["JC, Grama Amendoim (bandeja)", "(2,0,2)(0,0,1)", "0,848", "0,918", "36", "96,8%", "121%"],
    ["JC, Grama Zeon", "(0,0,2)(0,0,1)", "0,991", "0,972", "19", "97,3%", "133%"],
    ["JC, Grama São Carlos", "(0,0,2)(1,0,1)", "0,894", "0,895", "36", "99,7%", "127%"],
]

cap8_3 = [
    ("p", "A solução definitiva foi avaliada pelo próprio treinamento do sistema, executado sobre a base completa, com "
          "vendas até 28 de fevereiro de 2026 (experimento E10). Foram identificadas 32 séries: as quatro categorias "
          "de cada unidade e 24 produtos classificados na categoria Grama, 13 em Itabirito e 11 em Jardim Canadá. Dos "
          "produtos, 15 ficaram sem previsão por não atenderem ao requisito mínimo de dados, 13 por terem vendido em "
          "menos de 28 dos últimos 365 dias e 2 por terem menos de 180 dias de histórico. As 17 séries restantes, 8 "
          "categorias e 9 produtos de grama, foram validadas em 56 origens, de 22 de dezembro de 2025 a 15 de "
          "fevereiro de 2026, com dias avaliados até 28 de fevereiro de 2026, e receberam a previsão de 1º a 14 de "
          "março de 2026. O treinamento das 32 séries, com 14 processos paralelos em um computador de 16 núcleos "
          "lógicos, levou 27 minutos, dentro do limite de duas horas do requisito RNF03. A Tabela 8 apresenta o "
          "desempenho de cada série."),
    ("tabela", "Tabela 8 – Desempenho da solução definitiva por série (E10)",
     [2262, 1480, 880, 1000, 1000, 1150, 1300],
     ["Série", "Ordem", "MASE", "Erro relativo", "Janelas vencidas", "Cobertura", "Previsto / vendido"],
     rows8, ["left"] + ["center"] * 6,
     "Fonte: Elaborado pelos autores (2026). ITA: Itabirito; JC: Jardim Canadá. Dias de loja aberta; janelas vencidas de "
     "56; ordem (p,0,q)(P,0,Q) com m" + d + "7."),
    ("p", "Nas categorias, o MASE ficou abaixo de 1 em sete das oito séries, entre 0,640 e 0,907, e foi de 1,268 em "
          "Plantas diversas de Itabirito. Medido na própria janela de teste, o erro foi menor que o da previsão "
          "ingênua em seis categorias, com erro relativo entre 0,797 e 0,963, praticamente igual em Flores de corte de "
          "Itabirito (1,001) e 2,6% maior em Plantas diversas de Itabirito. A cobertura do intervalo de 95% ficou entre "
          "94,0% e 98,7%, acima de 98% em Flores de corte nas duas unidades, o que indica, nessas séries, um intervalo "
          "mais largo que o necessário. Entre os nove produtos de grama, o MASE e o erro relativo ficaram abaixo de 1 "
          "em sete séries cada, e a cobertura ficou entre 94,5% e 100,0%."),
    ("p", "O teste de Ljung-Box não rejeitou a ausência de autocorrelação residual em nenhuma das 17 séries, com p "
          "entre 0,23 e 1,00, o que indica que os modelos capturaram a dependência entre os dias e o padrão semanal "
          "das vendas. O teste de Shapiro-Wilk rejeitou a normalidade dos resíduos em todas elas (p" + NB + "<" + NB +
          "0,001), comportamento esperado em vendas com dias de pico; por isso, a cobertura dos intervalos foi "
          "verificada empiricamente, e as coberturas obtidas, entre 94,0% e 100,0%, ficaram próximas ou acima do "
          "nível nominal de 95%."),
    ("p", "Em todas as categorias, o volume previsto superou o vendido no período avaliado, de 117% a 149%. Esse "
          "período, de dezembro de 2025 a fevereiro de 2026, coincide com a queda de vendas do início de 2026, "
          f"visível também no faturamento mensal da Figura 7, e, com d{d}0, a previsão converge para a média dos 365 "
          "dias anteriores, superior ao nível desse período. O comportamento é coerente com o custo de d" + d + "0 "
          f"identificado em E4 e E9, em que d{d}1 acompanhou melhor as fases de queda, e deve ser monitorado pelo "
          "histórico das previsões, que registra a razão entre o volume previsto e o vendido a cada treinamento."),
    ("p", "Nos produtos de grama de menor volume, o MASE e o erro relativo à previsão ingênua divergiram, e os dados "
          "de venda explicam a divergência. A Grama Esmeralda (ITO) em Jardim Canadá vendeu, em média, 22,6 unidades "
          "por dia de loja aberta no primeiro semestre de 2025 e 2,3 no segundo, e registrou venda em apenas 2 dos 56 "
          "dias abertos da validação. O modelo, ajustado nos 365 dias anteriores, ainda refletia o nível mais alto do "
          "início de 2025 e previu 3,2 vezes o volume vendido, com erro 76% maior que o da previsão ingênua, embora o "
          "MASE tenha sido de 0,792: a escala do MASE vem do período de treinamento, em que dias de até 1.000 unidades "
          "tornavam grande o erro da previsão ingênua. A Grama Esmeralda em Itabirito apresentou o caso inverso: nos 365 "
          "dias anteriores à validação, vendeu em apenas 25 dos 301 dias abertos, com média de 1,1 unidade por dia, e "
          "concentrou 260 unidades em 7 dias da validação, um deles com 200 unidades. O modelo previu 31% do vendido e "
          "obteve MASE de 4,008, porque a escala do treinamento, quase sem vendas, era pequena, mas ainda errou 35% "
          "menos que a previsão ingênua."),
    ("p", "As duas séries têm padrão intermitente, com venda em cerca de um a cada dez dias, e foram modeladas por "
          "atenderem ao requisito mínimo de 28 dias com venda no último ano. Para esse padrão, a literatura recomenda "
          "métodos específicos de demanda intermitente (Seção 4.3), e o MASE, calculado com a escala do treinamento, "
          "não reflete mudanças de nível entre o treinamento e o teste; por isso, nessas séries, o erro relativo na "
          "própria janela de teste e a razão entre o previsto e o vendido descrevem melhor o desempenho observado."),
]

cap8_4 = [
    ("p", "As escolhas de modelagem com maior efeito medido foram a separação das encomendas, que reduziu o MASE de "
          "Itabirito de 1,434 para 0,796; as variáveis de calendário, que eliminaram o erro nos feriados e estreitaram "
          "o intervalo de 95% da série total de 70,8 mil para 13,1 mil unidades; e a modelagem direta das categorias, "
          "que superou a desagregação em 7 de 8 pares, sobretudo em Flores de corte, com cobertura do intervalo "
          "próxima do nível nominal. Outras escolhas foram decididas por critérios além do erro diário: a "
          "transformação logarítmica, que reduziu o MAE em 8% a 13%, foi descartada por subestimar o volume vendido; "
          f"e a diferenciação d{d}0, sustentada pelos testes de estacionariedade, foi adotada mesmo com erro de 1% a 7% "
          "maior na família Grama, e o viés positivo observado em E10 indica que essa escolha deve ser reavaliada à "
          "medida que novos dados forem incorporados."),
    ("p", "Os resultados da solução definitiva não são diretamente comparáveis aos dos experimentos E1 a E8: estes "
          "cobriram um ano de teste, de março de 2025 a fevereiro de 2026, enquanto a validação do sistema cobre as "
          "oito semanas mais recentes, que incluem o Natal, o Ano-Novo e o Carnaval e coincidem com um período de "
          "queda das vendas. A validação curta é renovada a cada treinamento e acompanha o comportamento recente das "
          "séries, mas é mais sensível a períodos atípicos."),
    ("p", "Entre as limitações, destacam-se: as encomendas grandes, que representaram 52,1% do volume de Itabirito e "
          "22,5% do de Jardim Canadá, não são previstas, pois dependem de negociações que o histórico não antecipa, e "
          "são apresentadas à parte; o limiar de 2.000 unidades que as define foi escolhido por sensibilidade e ainda "
          "não foi calibrado pela entidade parceira; o histórico de 26 meses não permite estimar a sazonalidade "
          "anual; a classificação dos produtos pela descrição inclui na categoria Grama ferramentas cujo nome contém "
          "a palavra grama, como rastelos, vassouras e tesouras, que não receberam previsão por falta de vendas "
          "suficientes; o requisito mínimo de 28 dias com venda admite produtos de grama de venda esporádica, para os "
          "quais o SARIMAX é pouco adequado; e os testes de usabilidade com a gestora de compras e a avaliação do efeito do sistema sobre "
          "perdas e rupturas não foram realizados."),
]

cap9 = [
    ("h1", "9 CONCLUSÃO E TRABALHOS FUTUROS"),
    ("p", "Este trabalho desenvolveu um sistema de previsão de vendas para a Floricultura Verde Perto, que transforma "
          "o histórico de vendas, antes disponível apenas em planilhas, em previsões diárias para os 14 dias "
          "seguintes, por categoria e por produto de grama de cada unidade, acompanhadas de intervalo de 95% e de "
          "indicadores de desempenho. O problema apresentado na Seção 1.1, a ausência de um sistema que "
          "transformasse os dados históricos em previsões quantitativas e antecipadas, foi enfrentado com um "
          "[[pipeline]] de preparação dos dados, modelos SARIMAX com regressores exógenos de calendário, validados "
          "por [[walk-forward]] a cada treinamento, e um painel que apresenta a previsão, o histórico das previsões, "
          "as análises das vendas e relatórios a usuários não técnicos."),
    ("p", "A sequência de experimentos permitiu medir o efeito de cada escolha de modelagem. As variáveis de "
          "calendário reduziram em 9% o erro anual da série total e praticamente eliminaram o erro nos feriados, "
          "enquanto as variáveis climáticas não trouxeram ganho; a separação das encomendas grandes foi decisiva em "
          "Itabirito, onde reduziu o MASE de 1,434 para 0,796; e o modelo próprio de cada categoria superou a "
          "desagregação da previsão da loja em 7 de 8 combinações. A transformação logarítmica reduziu o erro diário, "
          "mas foi descartada por fazer a previsão cobrir apenas de 48% a 90% do volume vendido, o que mostra que a "
          "melhor configuração em uma métrica isolada não é necessariamente a mais adequada ao uso do sistema. Na "
          "solução definitiva, o MASE ficou abaixo de 1 em 14 das 17 séries com previsão, a cobertura do intervalo de "
          "95% ficou entre 94% e 100%, e as categorias superaram a previsão ingênua em 6 de 8 combinações, com previsão acima do volume vendido em um "
          "período de queda das vendas."),
    ("p", "Os resultados indicam que modelos estatísticos de séries temporais com regressores de calendário são "
          "aplicáveis à previsão diária de uma floricultura quando a demanda é agregada em séries densas e as "
          "encomendas de grande porte são tratadas à parte, em linha com os ganhos relatados por Arunraj, Ahrens e "
          "Fernandes (2016) no varejo alimentar. Entre as limitações, destacam-se as encomendas grandes, não previstas "
          "pelos modelos; o histórico de 26 meses, insuficiente para estimar a sazonalidade anual; a validação da "
          "solução final restrita às oito semanas mais recentes; e a ausência dos testes de usabilidade e da medição "
          "do efeito do sistema sobre perdas e rupturas."),
    ("p", "Como trabalhos futuros, propõem-se:"),
    ("i", "a)", "verificar formalmente a usabilidade do sistema com a gestora de compras da entidade parceira, com "
                "tarefas e instrumento padronizado;"),
    ("i", "b)", "integrar ao sistema a informação antecipada das encomendas grandes, como pedidos já negociados, e "
                "calibrar com a entidade parceira o limiar que as define;"),
    ("i", "c)", "reavaliar a ordem de diferenciação e a janela de treinamento à medida que novos dados forem "
                "incorporados, com base no histórico das previsões, e oferecer, além da previsão pontual, uma "
                "quantidade de referência baseada em um quantil superior da distribuição prevista, com nível definido "
                "pela empresa;"),
    ("i", "d)", "estender a previsão por produto à categoria Flores de corte, conforme solicitado pela entidade "
                "parceira, e comparar, nos produtos de demanda intermitente, inclusive os produtos de grama de venda "
                "esporádica, os métodos de Croston, SBA e TSB;"),
    ("i", "e)", "comparar o desempenho dos modelos estatísticos com redes neurais artificiais e com métodos de "
                "[[ensemble]] baseados em árvores de decisão aplicados como modelos de previsão;"),
    ("i", "f)", "incorporar a sazonalidade anual à medida que o histórico de vendas se ampliar;"),
    ("i", "g)", "implementar a identificação de produtos comprados em conjunto e a simulação de promoções e de vendas "
                "conjugadas, solicitadas pela entidade parceira;"),
    ("i", "h)", "avaliar, após a implantação, o efeito do uso do sistema sobre as perdas por descarte e sobre as "
                "rupturas de estoque."),
]

fill = {
    "RESUMO_FINAL": "Na solução definitiva, validada nas oito semanas mais recentes do histórico, o MASE ficou abaixo de "
                    "1 em 14 das 17 séries com previsão e a cobertura do intervalo de 95% ficou entre 94% e 100%; as "
                    "categorias superaram a previsão ingênua em 6 de 8 combinações, com previsão acima do volume vendido "
                    "em um período de queda das vendas.",
    "ABSTRACT_FINAL": "In the final solution, validated on the most recent eight weeks of history, the MASE was below 1 in "
                      "14 of the 17 forecast series and the 95% interval coverage ranged from 94% to 100%; the categories "
                      "beat the naive forecast in 6 of 8 combinations, with forecasts above the volume sold during a "
                      "period of declining sales.",
    "TESTES_TEXTO": TESTES["texto"],
}

json.dump({"fig_list": fig_list, "cap7": cap7, "cap8_3": cap8_3, "cap8_4": cap8_4, "cap9": cap9, "fill": fill},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", OUT)
