# -*- coding: utf-8 -*-
"""Conteúdo do artigo: capítulos 7 a 9, referências, listas e valores calculados (E10)."""
import json
import os

from content_a import FONTE, NB

_HERE = os.path.dirname(os.path.abspath(__file__))
E10 = json.load(open(os.path.join(_HERE, "..", "e10.json"), encoding="utf-8"))
FILL = E10["fill"]

FIGURE_LIST = [
    (1, "Etapas da metodologia"),
    (2, "Diagrama de casos de uso"),
    (3, "Diagrama de atividades do fluxo de previsão"),
    (4, "Diagrama de classes"),
    (5, "Modelo de dados (entidade-relacionamento)"),
    (6, "Arquitetura lógica do sistema"),
] + E10["fig_list"]
QUADRO_LIST = [
    (1, "Iterações do projeto segundo as fases do CRISP-DM"),
    (2, "Experimentos realizados"),
    (3, "Requisitos funcionais do sistema de previsão de vendas"),
    (4, "Requisitos não funcionais do sistema"),
    (5, "Atores do sistema"),
]
TABELA_LIST = [
    (1, "Efeito das variáveis exógenas na série total da rede (E1 e E2)"),
    (2, "MASE da separação das encomendas pelo limiar por linha (E3)"),
    (3, "Modelo por unidade: calendário, diferenciação e Holt-Winters (E4)"),
    (4, "Sensibilidade do critério de encomenda grande (E5)"),
    (5, "Transformação logarítmica e janela de treinamento em Itabirito (E6)"),
    (6, "Configurações do modelo por produto em Itabirito (E7)"),
    (7, "Previsão direta da categoria e desagregação da previsão da loja (E8)"),
    (8, "Desempenho da solução definitiva por série (E10)"),
]

CAP7 = E10["cap7"]

d = NB + "=" + NB
CAP8 = [
    ("h1", "8 RESULTADOS E DISCUSSÕES"),
    ("p", "Esta seção apresenta a caracterização da demanda obtida na análise exploratória, os resultados dos "
          "experimentos E1 a E9, que fundamentaram a configuração do modelo, e o desempenho da solução definitiva "
          "(E10), seguidos da discussão das limitações."),
    ("h2", "8.1 Caracterização da demanda"),
    ("p", "A análise exploratória confirmou que a previsão individual da maior parte dos produtos não é viável na base "
          "da Floricultura Verde Perto, como antecipado na Seção 5.5: 99,3% dos produtos classificáveis apresentam "
          "demanda intermitente ou [[lumpy]], 13,4% dos produtos venderam em um único dia, e os 20 produtos de maior "
          "giro respondem por 61,7% do volume vendido. Agregadas por unidade e categoria, as séries passam a registrar "
          "venda em 81% a 83% dos dias, com no máximo cinco dias seguidos sem venda, quase sempre domingos e feriados. "
          "O padrão semanal é de dia útil, e não de fim de semana, e o efeito das datas comemorativas muda de sinal "
          "entre as categorias: no Dia das Mães, a venda de Flores de corte em Jardim Canadá sobe para 2,14 vezes a "
          "média, enquanto a da unidade como um todo cai para 0,66 vez a média."),
    ("p", "Testes preliminares de nível de agregação, executados na análise exploratória com 26 janelas de 14 dias e "
          "regra de decisão fixada antes da execução, indicaram ganho do modelo próprio de Itabirito, cujo MASE caiu "
          "17% em relação à repartição da previsão da rede, e nenhum ganho igual ou superior a 5% para as seis séries "
          "de unidade e categoria então definidas, com três categorias. Esses testes usavam a série com as "
          "encomendas e apenas o MASE como critério; o experimento E8 retomou a questão das categorias com o fluxo "
          "diário, as quatro categorias atuais e a cobertura do intervalo entre os critérios."),
    ("h2", "8.2 Resultados dos experimentos"),
    ("p", "A Tabela 1 apresenta os experimentos E1 e E2, ajustados à série total da rede, que somava todas as unidades "
          "e categorias e tinha venda média de cerca de 5 mil unidades por dia. Sem variáveis exógenas, o modelo de "
          "referência errou 32% menos que a previsão ingênua no ano de teste, mas venceu em apenas 19 das 26 janelas, "
          "empatou com ela em dezembro e tinha intervalo de 95% com largura média de 70,8 mil unidades. Com as "
          "variáveis de calendário, o MAE anual caiu de 3.024 para 2.749 unidades, redução de 9%, as janelas vencidas "
          "passaram de 19 para 22, o erro nos 14 feriados do ano caiu de 3.988 unidades para praticamente zero e a "
          "largura do intervalo reduziu-se a 13,1 mil unidades. A decomposição dos resíduos mostrou que 79% da "
          "variância que alargava o intervalo vinha dos feriados, que o modelo sem calendário não antecipava, e "
          "apenas 5% dos dias com encomenda."),
    ("tabela", "Tabela 1 – Efeito das variáveis exógenas na série total da rede (E1 e E2)", [3672, 1800, 1800, 1800],
     ["Indicador", "Sem exógenas (E1)", "Calendário (E2)", "Calendário e clima (E2)"],
     [["MAE no ano de teste (unidades)", "3.024", "2.749", "2.775"],
      ["Erro relativo à previsão ingênua", "0,677", "0,616", "0,622"],
      ["Janelas em que supera a previsão ingênua", "19 de 26", "22 de 26", "22 de 26"],
      ["Cobertura do intervalo de 95%", "95,6%", "93,7%", "93,7%"],
      ["Largura média do intervalo de 95% (mil unidades)", "70,8", "13,1", "13,0"],
      ["MAE nos 14 feriados (unidades)", "3.988", "0,5", "0,5"],
      ["Erro relativo em dezembro de 2025", "1,02", "0,92", "0,92"],
      ["MAE em fevereiro de 2026 (unidades)", "1.415", "1.397", "1.467"]],
     ["left", "center", "center", "center"], FONTE),
    ("p", "As variáveis climáticas não trouxeram ganho: mesmo com os valores observados, situação mais favorável que a "
          "de uso real, que dependeria da previsão do tempo, o modelo com clima empatou ou piorou em todos os testes. "
          "Os efeitos estimados da precipitação do dia (+3%, p" + d + "0,46), da precipitação acumulada em sete dias "
          "(−1%, p" + d + "0,74) e da temperatura máxima (+1,5% por grau, p" + d + "0,21) não foram significativos, e "
          "as variáveis climáticas somaram 1,4% da importância relativa calculada pela [[Random Forest]], contra 83,2% "
          "do dia da semana e 15,2% dos feriados. Véspera e dia seguinte a feriado, primeira semana do mês e as "
          "janelas de Namorados, Dia da Mulher, Dia dos Pais e Natal também não apresentaram efeito confiável "
          "(p" + NB + ">" + NB + "0,3), o que é coerente com a inversão de sinal entre categorias observada na análise "
          "exploratória. As janelas de sete dias antes do Dia das Mães e de Finados tiveram coeficientes elevados, de "
          "+159% e +280%, mas o efeito vinha da abertura excepcional da loja no próprio dia: o modelo atribuía o salto "
          "do dia à semana inteira, e essas duas semanas responderam por 12% do erro do ano. Por isso, a configuração "
          "seguinte substituiu as janelas pelo indicador de abertura excepcional e manteve apenas o dia da semana, a "
          "loja fechada e a abertura excepcional. Esses números confirmam, para a floricultura, o ganho dos "
          "regressores de calendário observado por Arunraj, Ahrens e Fernandes (2016) no varejo alimentar."),
    ("p", "O experimento E3 avaliou, na série de cada unidade, a separação das encomendas por um limiar aplicado a cada "
          "linha de venda, igual a cinco vezes a mediana do volume diário da unidade e categoria, e a limitação dos "
          "picos restantes ao percentil 99 durante o treinamento. A Tabela 2 mostra que a separação respondeu por quase "
          "todo o ganho em Itabirito, onde o MASE passou de 1,434, pior que a previsão ingênua, para 0,810, e para "
          "0,796 com a limitação dos picos, enquanto a limitação isolada pouco alterou o resultado. Em Jardim Canadá, "
          "onde essas encomendas representavam 1,3% do volume, o MASE passou apenas de 0,659 para 0,646. Com três, "
          "cinco e dez vezes a mediana, o MASE de Itabirito ficou em 0,795, 0,796 e 0,789, de modo que o resultado não "
          "dependeu do múltiplo escolhido. Esse contraste mostra que o tratamento das encomendas é decisivo apenas "
          "onde elas têm peso relevante no volume, em linha com a recomendação de tratá-las como fluxo separado "
          "(BARTEZZAGHI; VERGANTI, 1995)."),
    ("tabela", "Tabela 2 – MASE da separação das encomendas pelo limiar por linha (E3)", [2672, 1600, 1600, 1600, 1600],
     ["Variante", "Itabirito SARIMAX", "Itabirito Holt-Winters", "Jardim Canadá SARIMAX", "Jardim Canadá Holt-Winters"],
     [["Série original", "1,434", "1,311", "0,659", "0,727"],
      ["Só limitação dos picos", "1,401", "1,283", "0,648", "0,713"],
      ["Só separação das encomendas", "0,810", "0,699", "0,656", "0,724"],
      ["Separação e limitação", "0,796", "0,688", "0,646", "0,710"]],
     ["left", "center", "center", "center", "center"], FONTE),
    ("p", "O experimento E4 aplicou esses achados ao modelo de cada unidade, ajustado à venda de balcão, e comparou "
          "quatro versões, apresentadas na Tabela 3. Com o calendário, o erro nos feriados ficou próximo de zero nas "
          "duas unidades e o erro nos dias de abertura excepcional de Itabirito caiu de 780 unidades, sem calendário, "
          f"para 131 e, com d{d}1, para 50. A versão com d{d}1, em que a previsão parte do nível recente das "
          "vendas, foi a melhor nas duas unidades: em Jardim Canadá, o erro relativo à previsão ingênua caiu de 0,69 "
          "para 0,66, as janelas vencidas subiram de 22 para 24 e o erro relativo em fevereiro de 2026, fase de queda "
          "das vendas, caiu de 0,80 para 0,58; em Itabirito, o ganho no ano foi pequeno (de 0,63 para 0,62) e "
          "concentrou-se em dezembro (de 0,74 para 0,63). O Holt-Winters superou o SARIMAX apenas em fevereiro em "
          "Jardim Canadá e teve intervalo largo demais para uso."),
    ("tabela", "Tabela 3 – Modelo por unidade: calendário, diferenciação e Holt-Winters (E4)", [3072, 1500, 1500, 1500, 1500],
     ["Indicador", "Sem calendário", f"Calendário, d{d}0", f"Calendário, d{d}1", "Holt-Winters"],
     [["Jardim Canadá: erro relativo à previsão ingênua", "0,83", "0,69", "0,66", "0,72"],
      ["Jardim Canadá: janelas vencidas (de 26)", "21", "22", "24", "22"],
      ["Jardim Canadá: MASE", "0,73", "0,61", "0,58", "0,64"],
      ["Jardim Canadá: erro relativo em dezembro e em fevereiro", "1,06 e 0,66", "0,76 e 0,80", "0,74 e 0,58", "0,95 e 0,54"],
      ["Jardim Canadá: largura (mil unidades) e cobertura do intervalo de 95%", "38 e 96%", "5,7 e 91%", "5,5 e 91%", "41 e 100%"],
      ["Itabirito: erro relativo à previsão ingênua", "0,71", "0,63", "0,62", "0,69"],
      ["Itabirito: janelas vencidas (de 26)", "24", "24", "24", "23"],
      ["Itabirito: MASE", "0,66", "0,58", "0,58", "0,65"],
      ["Itabirito: erro relativo em dezembro e em fevereiro", "0,90 e 0,75", "0,74 e 0,66", "0,63 e 0,64", "0,84 e 0,65"],
      ["Itabirito: largura (mil unidades) e cobertura do intervalo de 95%", "11,7 e 96%", "2,2 e 94%", "2,3 e 94%", "10,1 e 100%"]],
     ["left", "center", "center", "center", "center"], FONTE),
    ("p", f"A versão com calendário e d{d}1 atendeu aos critérios de aceitação nas duas unidades, com MASE de 0,58, "
          "cobertura de 91,2% e 93,7% e MAE de 1.282 e 486 unidades por dia, contra 1.948 e 780 da previsão "
          "ingênua, em Jardim Canadá e Itabirito. Somadas e comparadas com a venda total, as previsões das duas "
          "unidades reduziram o erro médio diário em 16% em relação ao modelo de referência E1 (de 3.024 para 2.539 "
          "unidades). Nessa configuração, a série era modelada em log(1" + NB + "+" + NB + "y), e a previsão, por "
          "corresponder à mediana da distribuição prevista, cobriu 87,5% da venda de balcão de Jardim Canadá e 80,9% "
          "da de Itabirito no ano de teste. A correção desse viés por um fator multiplicativo estimado dos resíduos "
          "mostrou-se instável, chegando a multiplicar as previsões de Itabirito por 4,6, e a calibração pela razão "
          "entre o vendido e o previsto nas quatro janelas anteriores eliminou o viés (104% e 102%), mas aumentou o "
          "MAE em 9% em Jardim Canadá (de 1.277 para 1.387 unidades) e em 14% em Itabirito (de 486 para 552). Não "
          "houve, portanto, um único valor ótimo ao mesmo tempo para o erro diário e para o volume acumulado, questão "
          "examinada em E6 e E7."),
    ("p", "Os experimentos anteriores classificavam como encomenda linhas de venda isoladas, com um limiar estimado dos "
          "dados. Na série total de Itabirito, 18 dias, 5% do período de teste, concentravam 61,8% do erro do modelo e "
          "50,6% do volume vendido, e a maior venda do histórico, em 16 de dezembro de 2025, respondia sozinha por "
          "61.172 das 62.595 unidades do dia. O experimento E5 comparou o critério pelo tamanho da venda inteira, com "
          "limiares de 500 a 5.000 unidades, com o escore z modificado aplicado a cada linha (IGLEWICZ; HOAGLIN, 1993), "
          "medindo o volume classificado como encomenda, o coeficiente de variação do fluxo diário resultante e a "
          "parcela retirada do volume de consumidores sem cadastro, que representam a venda de balcão (Tabela 4)."),
    ("tabela", "Tabela 4 – Sensibilidade do critério de encomenda grande (E5)", [2172, 1150, 1150, 1150, 1150, 1150, 1150],
     ["Critério", "Itabirito: volume", "Itabirito: CV", "Itabirito: balcão",
      "Jardim Canadá: volume", "Jardim Canadá: CV", "Jardim Canadá: balcão"],
     [["Série total, sem separação", "–", "2,35", "–", "–", "1,18", "–"],
      ["Venda acima de 500 unidades", "60,2%", "0,66", "6,1%", "42,9%", "0,62", "16,1%"],
      ["Venda acima de 1.000 unidades", "55,5%", "0,71", "4,0%", "30,9%", "0,66", "7,7%"],
      ["Venda acima de 2.000 unidades", "52,1%", "0,78", "2,7%", "22,5%", "0,69", "3,7%"],
      ["Venda acima de 3.000 unidades", "48,4%", "0,86", "2,1%", "17,7%", "0,72", "2,9%"],
      ["Venda acima de 5.000 unidades", "42,1%", "1,08", "0,0%", "12,1%", "0,77", "2,5%"],
      ["Escore z modificado por linha", "61,2%", "1,04", "21,6%", "34,8%", "0,87", "22,2%"]],
     ["left"] + ["center"] * 6,
     "Fonte: Elaborado pelos autores (2026). Volume: parcela do volume classificada como encomenda; CV: coeficiente de "
     "variação do fluxo diário; balcão: parcela do volume de consumidores sem cadastro retirada do fluxo."),
    ("p", "Em todos os limiares, o critério por venda produziu um fluxo diário mais regular e retirou menos venda de "
          "balcão que o critério por linha, que removia 21,6% do volume de consumidores de Itabirito e 22,2% do de "
          "Jardim Canadá. O limiar de 2.000 unidades foi adotado como ponto de equilíbrio: abaixo dele, o critério "
          "passa a retirar venda de balcão, como os 16,1% do volume de consumidores de Jardim Canadá com 500 "
          "unidades; acima dele, o fluxo volta a ficar irregular, como mostra o coeficiente de variação de 1,08 de "
          "Itabirito com 5.000 unidades. Com esse limiar, o coeficiente de variação da série diária caiu de 2,35 para "
          "0,78 em Itabirito e de 1,18 para 0,69 em Jardim Canadá. O valor é uma escolha justificada pela análise de "
          "sensibilidade, e não um parâmetro calibrado com a entidade parceira."),
    ("p", f"O experimento E6 isolou o efeito da transformação logarítmica em Itabirito, com a mesma ordem do modelo, as "
          f"mesmas variáveis exógenas e d{d}1 em todas as variantes (Tabela 5). Na série total, com as encomendas, o "
          "logaritmo reduziu o MAE em 30%, de 2.722 para 1.917 unidades, mas a previsão cobriu apenas 46,1% do volume "
          "vendido, porque a mediana da distribuição prevista não acompanha os dias de encomenda; nas duas escalas, o "
          "MASE ficou acima de 1 (1,151 e 1,588). No fluxo diário, o logaritmo reduziu o MAE em 8,4% e a largura do "
          "intervalo em 17%, mas a previsão cobriu 89,6% do vendido, contra 101,1% na escala original, e a RMSE foi "
          "ligeiramente maior (518 contra 512 unidades), o que indica erros maiores nos dias de venda alta. A janela "
          "deslizante de 425 dias, que descarta os dados mais antigos a cada origem, não alterou o resultado, com "
          "variação de até 0,4% no MAE."),
    ("tabela", "Tabela 5 – Transformação logarítmica e janela de treinamento em Itabirito (E6)",
     [2872, 900, 900, 1000, 1150, 1000, 1250],
     ["Série e configuração", "MAE", "RMSE", "Erro relativo", "Cobertura", "Largura", "Previsto / vendido"],
     [["Série total, log(1 + y)", "1.917", "6.042", "0,606", "89,7%", "4.457", "46,1%"],
      ["Série total, escala original", "2.722", "5.941", "0,860", "92,6%", "8.536", "97,8%"],
      ["Fluxo diário, log(1 + y)", "319", "518", "0,624", "93,7%", "1.582", "89,6%"],
      ["Fluxo diário, escala original", "348", "512", "0,681", "95,0%", "1.902", "101,1%"],
      ["Fluxo diário, log(1 + y), janela deslizante", "320", "517", "0,627", "93,4%", "1.559", "90,5%"],
      ["Fluxo diário, escala original, janela deslizante", "349", "511", "0,683", "94,8%", "1.902", "101,7%"]],
     ["left"] + ["center"] * 6,
     "Fonte: Elaborado pelos autores (2026). Métricas de todos os dias e horizontes; MAE, RMSE e largura em unidades."),
    ("p", "O experimento E7 avaliou o modelo por produto nos itens de venda regular de Itabirito, isto é, com ADI "
          "inferior a 1,32, que somaram de 8 a 10 produtos por origem e 13 produtos distintos no período. Foram "
          "comparados o SARIMAX ajustado a cada produto, nas quatro combinações de diferenciação e transformação, e a "
          "desagregação da previsão da loja pela participação do produto nas oito semanas anteriores (Tabela 6). O "
          "logaritmo reduziu o MAE em 13% e levou o MASE abaixo de 1, mas a previsão passou a cobrir apenas 48% do "
          "volume vendido, o intervalo de 95% ficou 57% mais largo e o erro no total dos 14 dias, que mede a "
          "quantidade acumulada relevante para a compra, aumentou de 45,5% para 55,0%. Na escala original, o volume "
          "previsto ficou entre 98% e 100% do vendido, com cobertura de 96,0%. A diferenciação teve efeito pequeno: "
          f"d{d}1 reduziu o MAE em 0,9% e o erro no total dos 14 dias de 48,7% para 45,5%, mas elevou o MASE de 0,988 "
          "para 1,024. A desagregação teve erro semelhante ao do SARIMAX por produto na escala original, mas cobertura "
          "de apenas 76,8%, distante do nível nominal de 95%."),
    ("tabela", "Tabela 6 – Configurações do modelo por produto em Itabirito (E7)",
     [2172, 800, 800, 1000, 1150, 950, 1000, 1200],
     ["Configuração", "MAE", "MASE", "Erro relativo", "Cobertura", "Largura", "Previsto / vendido", "Erro no total de 14 dias"],
     [[f"SARIMAX, d{d}0, escala original", "33,9", "0,988", "0,811", "96,0%", "134,5", "98,3%", "48,7%"],
      [f"SARIMAX, d{d}1, escala original", "33,5", "1,024", "0,804", "96,0%", "134,6", "100,3%", "45,5%"],
      [f"SARIMAX, d{d}0, log(1 + y)", "29,3", "0,871", "0,703", "92,5%", "211,7", "48,6%", "55,0%"],
      [f"SARIMAX, d{d}1, log(1 + y)", "29,2", "0,869", "0,700", "92,3%", "210,7", "48,4%", "55,0%"],
      ["Desagregação, escala original", "33,9", "1,056", "0,813", "76,8%", "69,8", "99,6%", "47,8%"],
      ["Desagregação, log(1 + y)", "32,6", "1,005", "0,780", "48,6%", "64,5", "89,4%", "44,8%"]],
     ["left"] + ["center"] * 7,
     "Fonte: Elaborado pelos autores (2026). Métricas dos dias de loja aberta; MAE e largura em unidades."),
    ("p", "Os experimentos E6 e E7 mostram o caso em que a configuração com melhor resultado em uma métrica isolada não "
          "é a mais adequada ao uso do sistema. A transformação logarítmica reduziu o erro diário, mas a compra é "
          "planejada sobre o volume de vários dias, e uma previsão que cobre de 48% a 90% do vendido subestima "
          "sistematicamente esse volume; a correção do viés, avaliada em E4, piorou o erro diário. Na escala original, "
          "a previsão pontual corresponde à média da distribuição prevista e acompanha o volume vendido, e o intervalo "
          "manteve cobertura próxima do nível nominal. Por esses motivos, a solução final adotou a escala original, "
          "configuração já utilizada no modelo por produto do sistema e no experimento E8."),
    ("p", "O experimento E8 comparou, nas quatro categorias das duas unidades, o SARIMAX ajustado diretamente à série "
          "da categoria com a desagregação da previsão da loja pela participação da categoria nas oito semanas "
          f"anteriores, ambos sobre o fluxo diário, na escala original, com d{d}1 e janela deslizante de 425 dias "
          "(Tabela 7). O modelo direto obteve erro menor em 7 dos 8 pares; a exceção, Plantas diversas em Jardim "
          "Canadá, teve diferença de 1,9%, abaixo do limite de 5% adotado como empate. O maior ganho ocorreu em Flores "
          "de corte, com redução de 12% do erro em Itabirito e de 18% em Jardim Canadá, onde o intervalo da "
          "desagregação cobriu apenas 60,3% dos dias. Esse resultado é coerente com a análise exploratória: o pico de "
          "Flores de corte nas datas comemorativas se anula no total da unidade, e a repartição por participação não "
          "recupera um sinal que a série agregada não contém. A cobertura do intervalo foi melhor no modelo direto em "
          "todos os pares, ao custo de intervalos mais largos."),
    ("tabela", "Tabela 7 – Previsão direta da categoria e desagregação da previsão da loja (E8)",
     [2172, 1150, 1150, 1150, 1150, 1150, 1150],
     ["Unidade e categoria", "Erro relativo (desag.)", "Erro relativo (direto)", "Cobertura (desag.)",
      "Cobertura (direto)", "Largura (desag.)", "Largura (direto)"],
     [["Itabirito, Grama", "0,798", "0,803", "78,1%", "94,3%", "1,80", "3,39"],
      ["Itabirito, Plantas diversas", "0,763", "0,736", "93,9%", "94,8%", "1,88", "1,95"],
      ["Itabirito, Produtos de jardim", "0,771", "0,737", "91,8%", "92,8%", "1,86", "2,05"],
      ["Itabirito, Flores de corte", "0,830", "0,733", "85,0%", "93,6%", "1,93", "2,87"],
      ["Jardim Canadá, Grama", "0,761", "0,740", "81,0%", "94,3%", "1,44", "2,24"],
      ["Jardim Canadá, Plantas diversas", "0,720", "0,734", "89,6%", "90,6%", "1,47", "1,59"],
      ["Jardim Canadá, Produtos de jardim", "0,695", "0,689", "90,4%", "92,2%", "1,47", "1,54"],
      ["Jardim Canadá, Flores de corte", "0,878", "0,723", "60,3%", "96,2%", "1,48", "2,90"]],
     ["left"] + ["center"] * 6,
     "Fonte: Elaborado pelos autores (2026). Dias de loja aberta; desag.: desagregação; largura expressa em múltiplos "
     "da venda média diária."),
    ("p", "Para o total da loja, a soma das previsões diretas das categorias teve o mesmo erro do modelo ajustado à "
          "série da loja, com MAE de 409 e 1.079 unidades por dia, contra 409 e 1.078, em Itabirito e em Jardim "
          "Canadá, e erro relativo à previsão ingênua de 0,73 nos dois casos. A soma produziu intervalo mais largo, "
          "com cobertura de 98,5% e 96,3%, contra 93,8% e 92,7% do modelo da loja. Esses resultados sustentaram a "
          "adoção de um modelo próprio para cada categoria e a obtenção do total da loja pela soma das categorias, sem "
          "perda de acurácia e com uma faixa conservadora."),
    ("p", "O experimento E9 verificou a ordem de diferenciação nas séries de categoria e de produto de grama. Os testes "
          "ADF e KPSS foram aplicados às quatro categorias e aos dois produtos de grama mais vendidos de cada unidade: "
          "o ADF rejeitou a raiz unitária nas 12 séries, nenhuma série foi classificada como integrada de primeira "
          "ordem, e a autocorrelação de primeira ordem da série diferenciada ficou entre −0,42 e −0,53, sinal de "
          f"sobrediferenciação com d{d}1. Na validação, d{d}1 ainda errou de 1% a 7% menos que d{d}0 na família "
          "Grama, com diferença acima de 5% apenas na categoria Grama de Jardim Canadá (6,6%), enquanto nas demais "
          f"categorias d{d}0 empatou ou foi melhor, com erro de 6% a 8% menor em Flores de corte. A hipótese de que a "
          f"vantagem de d{d}1 decorresse da janela expansiva, cuja média envelhece, foi testada com janela deslizante "
          f"de 365 dias e não se confirmou. A solução final adotou d{d}0 com constante, especificação sustentada pelos "
          "testes de estacionariedade, e o custo medido na família Grama ficou registrado como limitação. Os valores "
          "por série desse experimento foram registrados de forma resumida nos documentos do projeto."),
    ("h2", "8.3 Desempenho da solução definitiva"),
] + E10["cap8_3"] + [
    ("h2", "8.4 Discussão e limitações"),
] + E10["cap8_4"]

CAP9 = E10["cap9"]

REFERENCIAS = [
    "ARUNRAJ, N. S.; AHRENS, D.; FERNANDES, M. Application of SARIMAX model to forecast daily sales in food retail "
    "industry. **International Journal of Operations Research and Information Systems**, [[[S. l.]]], v. 7, n. 2, "
    "p. 1-21, 2016. DOI: https://doi.org/10.4018/IJORIS.2016040101.",
    "BARTEZZAGHI, E.; VERGANTI, R. Managing demand uncertainty through order overplanning. **International Journal "
    "of Production Economics**, [[[S. l.]]], v. 40, n. 2-3, p. 107-120, 1995.",
    "BOX, G. E. P. [[et al.]] **Time series analysis**: forecasting and control. 5th ed. Hoboken: Wiley, 2015.",
    "BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD). **Diário "
    "Oficial da União**: seção 1, Brasília, DF, p. 59, 15 ago. 2018.",
    "BREIMAN, L. Random forests. **Machine Learning**, [[[S. l.]]], v. 45, n. 1, p. 5-32, 2001.",
    "CHEN, C.; LIU, L.-M. Forecasting time series with outliers. **Journal of Forecasting**, [[[S. l.]]], v. 12, "
    "n. 1, p. 13-35, 1993.",
    "CROSTON, J. D. Forecasting and stock control for intermittent demands. **Operational Research Quarterly**, "
    "[[[S. l.]]], v. 23, n. 3, p. 289-303, 1972.",
    "FLIEDNER, G. Hierarchical forecasting: issues and use guidelines. **Industrial Management & Data Systems**, "
    "[[[S. l.]]], v. 101, n. 1, p. 5-12, 2001.",
    "GROSS, C. W.; SOHL, J. E. Disaggregation methods to expedite product line forecasting. **Journal of "
    "Forecasting**, [[[S. l.]]], v. 9, n. 3, p. 233-254, 1990.",
    "HUBER, J.; GOSSMANN, A.; STUCKENSCHMIDT, H. Cluster-based hierarchical demand forecasting for perishable goods. "
    "**Expert Systems with Applications**, [[[S. l.]]], v. 76, p. 140-151, 2017.",
    "HYNDMAN, R. J.; ATHANASOPOULOS, G. **Forecasting**: principles and practice. 3rd ed. Melbourne: OTexts, 2021. "
    "Disponível em: https://otexts.com/fpp3/. Acesso em: 9 out. 2026.",
    "HYNDMAN, R. J.; KOEHLER, A. B. Another look at measures of forecast accuracy. **International Journal of "
    "Forecasting**, [[[S. l.]]], v. 22, n. 4, p. 679-688, 2006.",
    "IGLEWICZ, B.; HOAGLIN, D. C. **How to detect and handle outliers**. Milwaukee: ASQC Quality Press, 1993. (ASQC "
    "Basic References in Quality Control: Statistical Techniques, v. 16).",
    "KALCHSCHMIDT, M.; VERGANTI, R.; ZOTTERI, G. Forecasting demand from heterogeneous customers. **International "
    "Journal of Operations & Production Management**, [[[S. l.]]], v. 26, n. 6, p. 619-638, 2006.",
    "MAKRIDAKIS, S.; SPILIOTIS, E.; ASSIMAKOPOULOS, V. The M4 Competition: 100,000 time series and 61 forecasting "
    "methods. **International Journal of Forecasting**, [[[S. l.]]], v. 36, n. 1, p. 54-74, 2020.",
    "PEARSON, R. K. [[et al.]] Generalized Hampel filters. **EURASIP Journal on Advances in Signal Processing**, "
    "[[[S. l.]]], v. 2016, art. 87, 2016.",
    "PRESSMAN, R. S.; MAXIM, B. R. **Engenharia de software**: uma abordagem profissional. 9. ed. Porto Alegre: "
    "AMGH, 2021.",
    "SOMMERVILLE, I. **Engenharia de software**. 10. ed. São Paulo: Pearson, 2018.",
    "SYNTETOS, A. A.; BOYLAN, J. E. The accuracy of intermittent demand estimates. **International Journal of "
    "Forecasting**, [[[S. l.]]], v. 21, n. 2, p. 303-314, 2005.",
    "SYNTETOS, A. A.; BOYLAN, J. E.; CROSTON, J. D. On the categorization of demand patterns. **Journal of the "
    "Operational Research Society**, [[[S. l.]]], v. 56, n. 5, p. 495-503, 2005.",
    "TEUNTER, R. H.; SYNTETOS, A. A.; BABAI, M. Z. Intermittent demand: linking forecasting to inventory "
    "obsolescence. **European Journal of Operational Research**, [[[S. l.]]], v. 214, n. 3, p. 606-615, 2011.",
    "WIRTH, R.; HIPP, J. CRISP-DM: towards a standard process model for data mining. In: INTERNATIONAL CONFERENCE ON "
    "THE PRACTICAL APPLICATIONS OF KNOWLEDGE DISCOVERY AND DATA MINING, 4., 2000, Manchester. **Proceedings** [...]. "
    "Manchester: [[[s. n.]]], 2000. p. 29-39.",
    "ZOTTERI, G.; KALCHSCHMIDT, M. A model for selecting the appropriate level of aggregation in forecasting "
    "processes. **International Journal of Production Economics**, [[[S. l.]]], v. 108, n. 1-2, p. 74-83, 2007.",
]
