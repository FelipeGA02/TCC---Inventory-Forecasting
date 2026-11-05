# -*- coding: utf-8 -*-
"""Conteúdo do artigo: elementos pré-textuais e capítulos 1 a 7.

Blocos: ("h1", texto) · ("h2", texto) · ("p", texto) · ("i", rótulo, texto) ·
("fig", chave, legenda, largura_emu[, fonte]) · ("quadro"|"tabela", legenda, larguras, cabeçalho,
linhas, alinhamentos, fonte) · ("pb",) quebra de página.
Marcação: [[itálico]], **negrito**. NB = espaço não separável.
"""
NB = " "

RESUMO = (
    "Este trabalho apresenta o desenvolvimento e a avaliação de um sistema de previsão de vendas para a "
    "Floricultura Verde Perto, construído a partir do histórico de vendas de janeiro de 2024 a fevereiro de 2026 "
    "das duas unidades da empresa, Jardim Canadá e Itabirito. O setor de floricultura apresenta desafios "
    "decorrentes da perecibilidade dos produtos, do padrão semanal de vendas e da oscilação da demanda em datas "
    "comemorativas, e a empresa planejava as compras sem estimativas quantitativas. A solução contempla a "
    "preparação dos dados, a separação das encomendas grandes, definidas como vendas acima de 2.000 unidades em "
    "um mesmo documento, o treinamento de um modelo SARIMAX para cada uma das quatro categorias de produto e para "
    "cada produto de grama de cada unidade, com variáveis exógenas de calendário, e um painel ([[dashboard]]) que "
    "apresenta a previsão diária dos 14 dias seguintes com intervalo de 95%, o histórico das previsões e relatórios "
    "exportáveis. A configuração do modelo resultou de uma sequência de experimentos avaliados por validação "
    "[[walk-forward]]: as variáveis de calendário reduziram em 9% o erro anual e praticamente eliminaram o erro nos "
    "feriados, enquanto as variáveis climáticas não trouxeram ganho; a separação das encomendas reduziu o MASE de "
    "Itabirito de 1,434 para 0,796; a transformação logarítmica reduziu o erro diário, mas fez a previsão cobrir "
    "apenas de 48% a 90% do volume vendido e não foi adotada; e o modelo próprio de cada categoria superou a "
    "desagregação da previsão da loja em 7 de 8 combinações de categoria e unidade, com cobertura do intervalo de "
    "95% entre 91% e 96%, contra 60% a 94% da desagregação. {RESUMO_FINAL} O efeito do sistema sobre perdas e "
    "rupturas de estoque não foi mensurado e constitui trabalho futuro."
)

PALAVRAS = "Previsão de demanda. Séries temporais. SARIMAX. Floricultura. Gestão de estoque."

ABSTRACT = (
    "This work presents the development and evaluation of a sales forecasting system for Floricultura Verde Perto, "
    "built on the sales history from January 2024 to February 2026 of the company's two stores, Jardim Canadá and "
    "Itabirito. The floriculture sector faces challenges arising from product perishability, the weekly sales "
    "pattern and demand swings around commemorative dates, and the company planned its purchases without "
    "quantitative estimates. The solution comprises data preparation, the separation of large orders, defined as "
    "sales above 2,000 units in a single document, the training of a SARIMAX model for each of the four product "
    "categories and for each grass product of each store, with calendar exogenous variables, and a dashboard that "
    "shows the daily forecast for the next 14 days with a 95% interval, the forecast history and exportable "
    "reports. The model configuration resulted from a sequence of experiments evaluated by walk-forward "
    "validation: calendar variables reduced the yearly error by 9% and practically eliminated the error on "
    "holidays, while weather variables brought no gain; separating large orders reduced the MASE of Itabirito from "
    "1.434 to 0.796; the logarithmic transformation reduced the daily error but made the forecast cover only 48% "
    "to 90% of the volume sold and was not adopted; and a dedicated model for each category outperformed the "
    "disaggregation of the store forecast in 7 of 8 category and store combinations, with 95% interval coverage "
    "between 91% and 96%, against 60% to 94% for disaggregation. {ABSTRACT_FINAL} The effect of the system on "
    "losses and stockouts was not measured and is left for future work."
)

KEYWORDS = "Demand forecasting. Time series. SARIMAX. Floriculture. Inventory management."

SIGLAS = [
    ("ADF", "[[Augmented Dickey-Fuller]] (teste de Dickey-Fuller aumentado)"),
    ("ADI", "[[Average Demand Interval]] (intervalo médio entre demandas)"),
    ("AIC", "[[Akaike Information Criterion]] (Critério de Informação de Akaike)"),
    ("API", "[[Application Programming Interface]] (interface de programação de aplicações)"),
    ("AR", "Autorregressivo"),
    ("ARIMA", "[[AutoRegressive Integrated Moving Average]] (modelo autorregressivo integrado de médias móveis)"),
    ("CRISP-DM", "[[Cross-Industry Standard Process for Data Mining]] (processo padrão para mineração de dados)"),
    ("CV²", "Quadrado do coeficiente de variação"),
    ("JWT", "[[JSON Web Token]]"),
    ("KPSS", "Teste de Kwiatkowski-Phillips-Schmidt-Shin"),
    ("LGPD", "Lei Geral de Proteção de Dados Pessoais"),
    ("MA", "Médias móveis ([[Moving Average]])"),
    ("MAE", "[[Mean Absolute Error]] (erro absoluto médio)"),
    ("MAPE", "[[Mean Absolute Percentage Error]] (erro percentual absoluto médio)"),
    ("MASE", "[[Mean Absolute Scaled Error]] (erro absoluto médio escalonado)"),
    ("MDI", "[[Mean Decrease in Impurity]] (redução média da impureza)"),
    ("REST", "[[Representational State Transfer]] (transferência representacional de estado)"),
    ("RF", "Requisito funcional"),
    ("RMSE", "[[Root Mean Squared Error]] (raiz do erro quadrático médio)"),
    ("RN", "Regra de negócio"),
    ("RNF", "Requisito não funcional"),
    ("SARIMAX", "[[Seasonal AutoRegressive Integrated Moving Average with eXogenous inputs]] (modelo autorregressivo "
                "integrado de médias móveis sazonal com variáveis exógenas)"),
    ("SBA", "[[Syntetos-Boylan Approximation]] (aproximação de Syntetos-Boylan)"),
    ("TSB", "Teunter-Syntetos-Babai (método de Teunter, Syntetos e Babai)"),
    ("UML", "[[Unified Modeling Language]] (linguagem de modelagem unificada)"),
]

FONTE = "Fonte: Elaborado pelos autores (2026)."
FONTE_ENT = "Fonte: Elaborado pelos autores com base em reuniões com a entidade parceira (2026)."

CAP1_7 = [
    ("h1", "1 INTRODUÇÃO"),
    ("p", "A previsão de demanda pode apoiar o planejamento de compras e a gestão de estoques ao fornecer estimativas "
          "das vendas futuras. Essa informação é relevante para empresas que comercializam produtos perecíveis, nas "
          "quais decisões de reposição precisam considerar tanto a quantidade esperada de vendas quanto o tempo "
          "disponível para comercialização. Quando as estimativas não refletem o comportamento da demanda, a empresa "
          "fica mais exposta a situações de estoque insuficiente ou de aquisição de quantidades superiores às "
          "necessárias. Métodos de previsão permitem estimar valores futuros e fornecer informações para apoiar "
          "decisões de planejamento, incluindo aquelas relacionadas à gestão de estoques (HYNDMAN; ATHANASOPOULOS, "
          "2021)."),
    ("p", "Na Floricultura Verde Perto, o planejamento das compras enfrenta o desafio de acompanhar as variações da "
          "demanda ao longo do tempo. A procura por flores e outros produtos comercializados pela empresa pode variar "
          "conforme a época do ano e datas comemorativas, como Dia das Mães, Dia dos Namorados e Dia Internacional da "
          "Mulher, além de apresentar diferenças entre os produtos e as unidades operacionais. Essas variações "
          "dificultam a definição das quantidades a serem adquiridas, uma vez que o comportamento das vendas em "
          "períodos anteriores nem sempre se repete de maneira uniforme ao longo do ano. Nesse cenário, antecipar a "
          "demanda constitui um desafio para o planejamento da empresa, que precisa considerar tanto as oscilações "
          "sazonais quanto as particularidades da comercialização de cada produto."),
    ("p", "Diante desse cenário, este trabalho tem como objetivo desenvolver e avaliar um sistema de previsão de vendas "
          "para a Floricultura Verde Perto, que utiliza o histórico de vendas e variáveis de calendário para estimar a "
          "demanda diária de cada categoria de produto e de cada produto de grama em cada unidade operacional, com "
          "horizonte de 14 dias. A solução contempla o tratamento e a padronização dos dados, a separação das "
          "encomendas grandes, cuja natureza difere da demanda regular de balcão, a construção e a avaliação dos "
          "modelos preditivos e um painel que apresenta a previsão com sua faixa de incerteza, o histórico das "
          "previsões comparado às vendas realizadas, análises das vendas e relatórios exportáveis. O sistema informa "
          "quanto se espera vender, e a decisão de compra permanece com a empresa."),
    ("p", "A avaliação foi realizada com os dados de vendas de janeiro de 2024 a fevereiro de 2026, após procedimentos "
          "de tratamento, organização e análise exploratória. A configuração final dos modelos resultou de uma "
          "sequência de experimentos, em que cada etapa alterou um fator em relação à configuração anterior: as "
          "variáveis exógenas, o nível de agregação, o tratamento das encomendas, a transformação logarítmica, a ordem "
          "de diferenciação e a janela de treinamento. O desempenho foi examinado por validação [[walk-forward]], que "
          "reproduz o uso real do sistema ao prever, a partir de cada data, apenas com os dados disponíveis até ela, e "
          "comparado com uma previsão ingênua que repete as vendas da semana anterior, sem pressupor que o desempenho "
          "obtido se repetirá em todas as situações futuras."),
    ("h2", "1.1 Problematização"),
    ("p", "Na Floricultura Verde Perto, o planejamento de compras depende do conhecimento prático da equipe e de "
          "relatórios extraídos manualmente do sistema financeiro em planilhas, que precisam ser organizadas e "
          "padronizadas a cada consulta. Com isso, o histórico de vendas, embora disponível, não é utilizado de forma "
          "sistemática para estimar a demanda futura, e as decisões de reposição de produtos perecíveis são tomadas "
          "sem estimativas quantitativas."),
    ("p", "Essa limitação se torna evidente quando se observa o comportamento das vendas registrado no histórico da "
          "empresa. Um produto típico do catálogo registrou venda em apenas 9 dos 789 dias analisados, o que torna "
          "inviável acompanhar item a item a demanda apenas pela experiência. Nas datas comemorativas, o efeito "
          "também difere entre as categorias: a categoria Flores de corte vende de 1,7 a 5,0 vezes a sua média diária "
          "no Dia da Mulher, no Dia das Mães e no Dia dos Namorados, enquanto a venda de Grama cai na maior parte "
          "dessas datas. Em Itabirito, 93 vendas acima de 2.000 unidades, que representam 0,16% das vendas da "
          "unidade, responderam por 52,1% do volume vendido no período. Assim, uma compra planejada pela média "
          "recente tenderia a subestimar a demanda de Flores de corte no Dia das Mães e, ao mesmo tempo, a "
          "superestimar a de Grama, expondo uma categoria à ruptura e outra à sobra de produto perecível."),
    ("p", "O problema, portanto, é a ausência de um sistema que transforme os dados históricos de vendas em previsões "
          "quantitativas, avaliadas quanto à sua confiabilidade e disponíveis com antecedência suficiente para orientar "
          "as compras. Assim, este trabalho busca responder à seguinte questão: como utilizar os dados históricos de "
          "vendas de uma floricultura para gerar, de forma sistemática e antecipada, previsões de demanda diária que "
          "apoiem o planejamento de compras?"),
    ("h2", "1.2 Estrutura do trabalho"),
    ("p", "O trabalho está organizado em seções. Após esta introdução, que inclui a problematização, a Seção 2 "
          "apresenta os objetivos geral e específicos, a Seção 3 apresenta a justificativa do projeto e a Seção 4 "
          "reúne o referencial teórico. Em seguida, a Seção 5 descreve a metodologia adotada, incluindo a especificação "
          "do modelo preditivo da solução final e o delineamento dos experimentos que levaram a ela, a Seção 6 "
          "consolida os requisitos e a modelagem do sistema e a Seção 7 apresenta a interface do sistema. Por fim, a "
          "Seção 8 apresenta e discute os resultados dos experimentos e da solução definitiva, e a Seção 9 traz a "
          "conclusão e as propostas de trabalhos futuros."),

    ("h1", "2 OBJETIVOS"),
    ("h2", "2.1 Objetivo geral"),
    ("p", "Desenvolver um sistema de previsão de vendas para o ramo de floricultura, baseado em dados históricos e em "
          "modelos estatísticos de séries temporais com regressores exógenos, que forneça a previsão diária, com "
          "horizonte de 14 dias, da demanda de cada categoria de produto e de cada produto de grama das unidades da "
          "empresa, de modo a apoiar as decisões operacionais e estratégicas de reposição e compra."),
    ("h2", "2.2 Objetivos específicos"),
    ("p", "Para alcançar o objetivo geral, foram definidos os seguintes objetivos específicos:"),
    ("i", "a)", "levantar e validar requisitos funcionais e não funcionais junto às partes interessadas "
                "([[stakeholders]]), garantindo que o sistema atenda às necessidades reais de operação e gestão;"),
    ("i", "b)", "estruturar um [[pipeline]] automatizado que vai da entrada dos dados à geração dos resultados, "
                "incluindo deduplicação, normalização, classificação dos produtos em categorias e separação das "
                "encomendas grandes;"),
    ("i", "c)", "realizar análise exploratória dos dados históricos para identificar padrões de sazonalidade, "
                "tendências, comportamento por unidade operacional e perfil de demanda por produto;"),
    ("i", "d)", "desenvolver módulo de engenharia de atributos que produza variáveis exógenas diárias de calendário "
                "para cada unidade operacional, incluindo dia da semana, feriados, fechamentos e aberturas "
                "excepcionais da loja e proximidade de datas comemorativas;"),
    ("i", "e)", "avaliar as variáveis exógenas candidatas, de calendário e de clima, pela significância dos "
                "coeficientes, pela importância relativa calculada por um método de [[ensemble]] baseado em árvores "
                "de decisão e pelo ganho de acurácia na validação;"),
    ("i", "f)", "treinar modelos estatísticos de séries temporais com regressores exógenos, com seleção automática de "
                "parâmetros pelo Critério de Informação de Akaike (AIC), para a demanda diária, com retreinamento a "
                "cada nova carga de dados;"),
    ("i", "g)", "comparar experimentalmente configurações de modelagem, como a transformação logarítmica, a ordem de "
                "diferenciação, a janela de treinamento, o nível de agregação e o tratamento das encomendas grandes;"),
    ("i", "h)", "avaliar o desempenho dos modelos com as métricas de erro MASE, MAE e RMSE, com o erro relativo à "
                "previsão ingênua e com a cobertura e a largura do intervalo de 95%, em validação [[walk-forward]];"),
    ("i", "i)", "implementar painel interativo com indicadores de desempenho do modelo, visualizações das vendas e da "
                "previsão, histórico das previsões, módulo de envio de planilhas e exportação de relatórios;"),
    ("i", "j)", "produzir documentação funcional e técnica para uso, manutenção e evolução da solução."),

    ("h1", "3 JUSTIFICATIVA"),
    ("p", "A ausência de controle de estoque, de planejamento e de previsão de vendas expõe a empresa a ineficiências "
          "operacionais, como compras acima ou abaixo da demanda de produtos perecíveis. Para enfrentá-las, foi "
          "desenvolvido um sistema integrado, acessível aos usuários da empresa conforme o perfil de acesso, capaz de "
          "receber os dados de vendas, retreinar os modelos preditivos a cada nova carga de dados e apresentar "
          "previsões acompanhadas de medidas de incerteza e de desempenho."),
    ("p", "A principal contribuição acadêmica deste trabalho é a aplicação de modelos estatísticos de séries temporais "
          "com regressores exógenos à previsão de demanda no setor de floricultura. Os estudos que fundamentam essa "
          "abordagem concentram-se no varejo de alimentos perecíveis (ARUNRAJ; AHRENS; FERNANDES, 2016; HUBER; "
          "GOSSMANN; STUCKENSCHMIDT, 2017), enquanto a floricultura, que compartilha com esse varejo a alta "
          "perecibilidade e a forte influência de datas comemorativas, é um setor pouco explorado nesse tipo de "
          "aplicação. O trabalho avalia, com dados reais de uma floricultura, se essa categoria de modelos reproduz no "
          "setor os ganhos de acurácia observados no varejo alimentar."),
    ("p", "A justificativa científica para a adoção de modelos estatísticos de séries temporais nesse contexto reside "
          "em sua adequação a séries sazonais influenciadas por variáveis exógenas, isto é, fatores externos que "
          "influenciam o comportamento da demanda. Arunraj, Ahrens e Fernandes (2016) demonstraram a eficácia dessa "
          "categoria de modelos no varejo de alimentos perecíveis, evidenciando ganhos de acurácia pela incorporação de "
          "variáveis exógenas de calendário e de promoção. Itens como flores e plantas compartilham com o varejo "
          "alimentar perecível os atributos de alta perecibilidade e forte sazonalidade, além do impacto elevado de "
          "eventos externos, o que reforça a pertinência deste trabalho."),
    ("p", "A justificativa técnica complementar está nos resultados da competição M4 (MAKRIDAKIS; SPILIOTIS; "
          "ASSIMAKOPOULOS, 2020), que demonstrou que métodos estatísticos superam, em média, abordagens puramente "
          "baseadas em aprendizado de máquina, sobretudo em séries com histórico reduzido. Esse é o cenário do "
          "presente projeto, com 26 meses de histórico, insuficientes para estimar uma sazonalidade anual, o que "
          "legitima a escolha de um modelo estatístico de séries temporais como modelo central deste trabalho."),
    ("p", "Como contribuições complementares, o projeto apresenta: (i) uma avaliação experimental controlada das "
          "escolhas de modelagem para a previsão diária de uma floricultura, em que cada experimento altera um único "
          "fator em relação à configuração de referência e tem os ganhos e as perdas medidos em validação "
          "[[walk-forward]], abrangendo a seleção das variáveis exógenas por significância, por importância relativa "
          "pela redução média da impureza ([[Mean Decrease in Impurity]] – MDI), formalizada por Breiman (2001), e por "
          "ganho de acurácia, a transformação logarítmica, a ordem de diferenciação e a janela de treinamento; e (ii) "
          "uma avaliação empírica do nível de agregação adequado à previsão diária de um catálogo perecível de cauda "
          "longa, que compara a modelagem direta das categorias com a desagregação da previsão da loja e trata as "
          "encomendas grandes como fluxo de demanda distinto da venda de balcão."),
    ("p", "A solução também foi concebida em conformidade com a Lei Geral de Proteção de Dados Pessoais (LGPD) "
          "(BRASIL, 2018), uma vez que os relatórios de vendas da empresa contêm dados pessoais de clientes. Por isso, "
          "a base do sistema não armazena nome, documento ou código dos clientes, informações sem valor preditivo, e "
          "registra apenas se a venda foi feita a cliente cadastrado; o acesso ao sistema é controlado por perfil de "
          "usuário, com senhas protegidas por [[hash]]; e cada importação de dados e cada treinamento dos modelos são "
          "registrados para fins de rastreabilidade, alinhando o objetivo do trabalho ao requisito de segurança RNF04 "
          "(Seção 6.2)."),
    ("p", "O sistema desenvolvido permite:"),
    ("i", "a)", "consulta da previsão diária dos 14 dias seguintes por categoria e por produto de grama de cada "
                "unidade, com intervalo de 95% e indicação da confiabilidade de cada modelo;"),
    ("i", "b)", "comparação, dia a dia, entre a quantidade prevista e a vendida, a partir do histórico das previsões;"),
    ("i", "c)", "análise das vendas por período, categoria, produto e unidade, com as encomendas grandes apresentadas "
                "à parte;"),
    ("i", "d)", "envio e conferência das planilhas de vendas e exportação de relatórios em formatos de uso gerencial."),
    ("p", "Com essa estrutura, a gestão passa a dispor de estimativas quantitativas para o planejamento das compras. O "
          "efeito do uso do sistema sobre o desperdício de produtos perecíveis e sobre as rupturas de estoque não foi "
          "mensurado neste trabalho e é indicado como trabalho futuro (Seção 9)."),

    ("h1", "4 REFERENCIAL TEÓRICO"),
    ("p", "Esta seção apresenta os conceitos e estudos que fundamentam as escolhas de modelagem, de tratamento dos "
          "dados e de avaliação adotadas no sistema. Os modelos são tratados aqui por sua categoria; os modelos "
          "específicos utilizados na implementação são indicados na Seção 5.5."),
    ("h2", "4.1 Previsão de demanda e modelos estatísticos de séries temporais"),
    ("p", "A previsão de demanda é tema consolidado na literatura de análise de séries temporais e de gestão de "
          "operações, que reúne modelos estatísticos e de aprendizado de máquina para capturar tendência, sazonalidade "
          "e efeitos exógenos (HYNDMAN; ATHANASOPOULOS, 2021). A escolha do modelo deve considerar a disponibilidade "
          "de dados, a interpretabilidade e o custo operacional."),
    ("p", "Entre os modelos estatísticos de séries temporais, destacam-se os modelos autorregressivos integrados de "
          "médias móveis, derivados da metodologia de Box-Jenkins (BOX [[et al.]], 2015). Em sua forma sazonal e com "
          "regressores exógenos, extensão natural dessa metodologia para séries com sazonalidade e influências "
          "externas, esses modelos capturam simultaneamente componentes autorregressivos (AR), de médias móveis (MA) "
          "e de diferenciação (I), em escalas regular e sazonal, e incorporam um vetor de regressores exógenos cujos "
          "coeficientes são estimados conjuntamente por máxima verossimilhança. A seleção dos parâmetros do modelo é "
          "realizada pela minimização do AIC, procedimento que equilibra qualidade de ajuste e parcimônia."),
    ("p", "Duas decisões de especificação são particularmente relevantes para séries diárias de vendas. A primeira é a "
          "ordem de diferenciação: a série deve ser diferenciada quando apresenta raiz unitária, o que pode ser "
          "verificado por testes como o de Dickey-Fuller aumentado ([[Augmented Dickey-Fuller]] – ADF), ao passo que "
          "diferenciar uma série já estacionária tende a introduzir autocorrelação negativa na série diferenciada, "
          "sinal de sobrediferenciação (BOX [[et al.]], 2015; HYNDMAN; ATHANASOPOULOS, 2021). A segunda é a "
          "transformação da variável, como o logaritmo, usada para estabilizar a variância; quando a previsão é "
          "convertida de volta à escala original, o valor obtido corresponde à mediana da distribuição prevista, e não "
          "à sua média, o que introduz um viés que precisa ser avaliado ou corrigido (HYNDMAN; ATHANASOPOULOS, 2021)."),
    ("p", "A adequação dessa categoria de modelos ao varejo perecível foi investigada por Arunraj, Ahrens e Fernandes "
          "(2016), que demonstraram, em contexto de varejo de alimentos, a superioridade da variante com variáveis "
          "exógenas de calendário e de promoção em relação à variante sazonal sem regressores externos. O setor de "
          "floricultura compartilha com o varejo alimentar perecível os atributos de alta perecibilidade, sazonalidade "
          "marcada por datas comemorativas e dependência de fatores externos, o que torna a abordagem diretamente "
          "aplicável."),
    ("p", "Para séries com histórico reduzido, Makridakis, Spiliotis e Assimakopoulos (2020) demonstraram, na "
          "competição M4, que métodos estatísticos superam, em média, abordagens puramente baseadas em aprendizado de "
          "máquina. Esse resultado fundamenta a escolha de um modelo estatístico de séries temporais como modelo "
          "central, em detrimento de alternativas como redes neurais e modelos baseados em árvores de decisão, que "
          "tendem ao sobreajuste ([[overfitting]]), fenômeno que ocorre quando um modelo se ajusta excessivamente aos "
          "dados de treinamento, quando o número de amostras é reduzido."),
    ("h2", "4.2 Seleção de variáveis exógenas"),
    ("p", "A avaliação da importância relativa das variáveis exógenas fundamenta-se na medida MDI, utilizada para "
          "mensurar a importância das variáveis em modelos de aprendizado de máquina e calculada por métodos de "
          "[[ensemble]] baseados em árvores de decisão (BREIMAN, 2001). Essa abordagem permite ordenar as variáveis "
          "candidatas segundo sua contribuição para explicar a demanda, sem incorrer nos vieses da seleção "
          "[[stepwise]] convencional, método de seleção automática que adiciona ou remove atributos do modelo com base "
          "em critérios estatísticos."),
    ("h2", "4.3 Demanda intermitente"),
    ("p", "Para produtos com demanda intermitente, em que a maior parte dos dias não registra venda, Croston (1972) "
          "propôs estimar separadamente o tamanho das vendas e o intervalo entre elas. Syntetos e Boylan (2005) "
          "demonstraram que esse método superestima a demanda e propuseram uma correção, conhecida como SBA, e "
          "Teunter, Syntetos e Babai (2011) propuseram uma variante, conhecida como TSB, que atualiza a probabilidade "
          "de ocorrência de venda a cada período. Syntetos, Boylan e Croston (2005) estabeleceram um critério que "
          "classifica a demanda em suave, errática, intermitente ou [[lumpy]], a partir do intervalo médio entre "
          "vendas ([[Average Demand Interval]] – ADI) e do quadrado do coeficiente de variação do tamanho das vendas "
          "(CV²), com pontos de corte em 1,32 e 0,49; nos padrões intermitente e [[lumpy]], os métodos específicos "
          "para demanda intermitente produzem erros menores que os modelos convencionais de séries temporais. Esse "
          "critério permite delimitar as séries para as quais um modelo convencional é adequado."),
    ("h2", "4.4 Previsão hierárquica e desagregação"),
    ("p", "Quando as séries individuais são esparsas, a previsão hierárquica permite estimar a demanda em um nível "
          "agregado, no qual o sinal é mais regular, e distribuí-la aos níveis inferiores. Na abordagem [[top-down]], "
          "a previsão do agregado é repartida pela proporção histórica de cada componente, o que exige um único modelo "
          "bem alimentado por dados, ao custo de não capturar a dinâmica própria de cada parte (FLIEDNER, 2001). Gross "
          "e Sohl (1990) mostraram que a proporção média histórica está entre os métodos de desagregação mais simples "
          "e precisos, e Zotteri e Kalchschmidt (2007) formalizaram a escolha do nível de agregação como um equilíbrio "
          "entre o erro de especificação, que cresce com a agregação, e o erro de amostragem, que cresce com a "
          "fragmentação dos dados. Huber, Gossmann e Stuckenschmidt (2017) aplicaram esse princípio à previsão de "
          "demanda de produtos perecíveis, prevendo em níveis agregados as séries de itens com venda esparsa."),
    ("h2", "4.5 Tratamento de observações atípicas"),
    ("p", "Observações atípicas distorcem a estimação dos parâmetros e alargam os intervalos de previsão de modelos "
          "autorregressivos integrados de médias móveis ([[AutoRegressive Integrated Moving Average]] – ARIMA) (CHEN; "
          "LIU, 1993). Quando os picos decorrem de pedidos de poucos clientes de grande porte, a literatura recomenda "
          "separar essa demanda da demanda regular e tratá-la com a informação antecipada dos próprios pedidos, em vez "
          "de extrapolar o histórico (BARTEZZAGHI; VERGANTI, 1995; KALCHSCHMIDT; VERGANTI; ZOTTERI, 2006). Para "
          "identificar esses pedidos, podem ser empregados identificadores robustos de valores atípicos, que comparam "
          "cada observação com a mediana e com uma medida robusta de dispersão, como os filtros de Hampel (PEARSON "
          "[[et al.]], 2016) e o escore z modificado (IGLEWICZ; HOAGLIN, 1993), ou limiares definidos sobre o tamanho "
          "do pedido."),
    ("h2", "4.6 Métricas de avaliação de previsões"),
    ("p", "Para a avaliação de previsões, Hyndman e Koehler (2006) propuseram o erro absoluto médio escalonado ([[Mean "
          "Absolute Scaled Error]] – MASE), que divide o erro absoluto médio do modelo pelo erro de uma previsão "
          "ingênua no conjunto de treinamento, de modo que valores inferiores a 1 indicam desempenho superior ao do "
          "método ingênuo. Diferentemente do erro percentual absoluto médio ([[Mean Absolute Percentage Error]] – "
          "MAPE), o MASE permanece definido em séries com valores nulos, como as vendas diárias em dias de loja "
          "fechada, e permite comparar séries de escalas distintas. Os mesmos autores discutem medidas relativas, que "
          "dividem o erro do modelo pelo de um método de referência no próprio período de teste, o que evita que um "
          "período de treinamento atípico torne a comparação otimista. Para previsões intervalares, avalia-se a "
          "cobertura empírica, isto é, a proporção de observações contidas no intervalo, que deve ser próxima do nível "
          "nominal, em conjunto com a largura do intervalo (HYNDMAN; ATHANASOPOULOS, 2021)."),
    ("h2", "4.7 Engenharia de software aplicada"),
    ("p", "No contexto de engenharia de software, o desenho arquitetural e a estratégia de validação são determinantes "
          "para a qualidade da entrega (SOMMERVILLE, 2018; PRESSMAN; MAXIM, 2021). Em ambientes de negócio com "
          "variação sazonal elevada, o uso de indicadores de erro e o monitoramento contínuo do desempenho preditivo "
          "são indispensáveis (HYNDMAN; ATHANASOPOULOS, 2021)."),

    ("h1", "5 METODOLOGIA"),
    ("p", "A condução do projeto segue abordagem iterativa e incremental, com ciclos de levantamento, implementação, "
          "validação e refinamento. A Figura 1 apresenta as etapas da metodologia, detalhadas nas subseções a seguir."),
    ("fig", "fig0_etapas", "Figura 1 – Etapas da metodologia", 5400000),
    ("h2", "5.1 Desenvolvimento de software"),
    ("p", "Foi utilizada abordagem ágil, com entregas parciais orientadas a valor. Cada iteração contemplou definição "
          "de histórias de usuário, implementação, testes e validação com a entidade parceira. O processo de "
          "desenvolvimento segue o modelo [[Cross-Industry Standard Process for Data Mining]] (CRISP-DM), metodologia "
          "utilizada para organizar projetos de análise de dados (WIRTH; HIPP, 2000), adaptado ao contexto de séries "
          "temporais, com as seguintes fases: compreensão do negócio, compreensão dos dados, preparação dos dados, "
          "modelagem, avaliação e implantação."),
    ("p", "O projeto foi organizado em oito iterações, distribuídas entre abril e novembro de 2026, cada uma associada "
          "a uma ou mais fases do CRISP-DM e encerrada com uma entrega verificável, conforme o Quadro 1. Como prevê o "
          "CRISP-DM, as fases não foram percorridas uma única vez: os resultados da avaliação podiam levar de volta à "
          "preparação dos dados, como ocorreu com o tratamento das encomendas grandes, definido a partir do erro "
          "observado na unidade de Itabirito (Seção 8). As decisões técnicas de cada iteração foram registradas em "
          "documentos de decisão arquitetural, preservando a rastreabilidade entre os achados da análise dos dados e "
          "as escolhas de modelagem."),
    ("quadro", "Quadro 1 – Iterações do projeto segundo as fases do CRISP-DM", [1020, 1587, 2495, 3970],
     ["Iteração", "Período", "Fases do CRISP-DM", "Entrega"],
     [["1", "abr. 2026", "Compreensão do negócio", "Backlog de requisitos consolidado e validado com a entidade parceira"],
      ["2", "abr./ago. 2026", "Compreensão e preparação dos dados", "Pipeline de ingestão e pré-processamento"],
      ["3", "maio/jul. 2026", "Compreensão do negócio", "Diagramas UML e modelo de dados"],
      ["4", "ago./set. 2026", "Compreensão e preparação dos dados", "Base de atributos e relatório de análise exploratória"],
      ["5", "set./out. 2026", "Modelagem e avaliação", "Experimentos comparativos e configuração final dos modelos"],
      ["6", "set./out. 2026", "Implantação", "Painel, serviço de previsão e histórico das previsões"],
      ["7", "out. 2026", "Avaliação e implantação", "Testes integrados e versão candidata à entrega"],
      ["8", "nov. 2026", "Implantação", "Documentação final e entrega do projeto"]],
     ["center", "center", "left", "left"], FONTE),
    ("h2", "5.2 Levantamento e análise de requisitos"),
    ("p", "Os requisitos foram levantados por meio de cinco reuniões com a entidade parceira, realizadas entre março e "
          "outubro de 2026 com a participação da gestão e da equipe administrativa, complementadas pela análise dos "
          "relatórios financeiros disponíveis e pela inspeção das planilhas exportadas do sistema vigente. As reuniões "
          "permitiram identificar as necessidades de negócio, as restrições operacionais e os critérios de aceitação "
          "de cada funcionalidade e, nas três últimas, validar o protótipo das telas, os resultados preliminares do "
          "modelo e a versão em desenvolvimento do sistema. Os requisitos foram priorizados conforme seu impacto "
          "operacional e estratégico e organizados em requisitos funcionais, requisitos não funcionais, regras de "
          "negócio e atores, que foram então modelados em notação UML, conforme apresentado na Seção 6."),
    ("h2", "5.3 Decisão sobre tecnologias e processos utilizados"),
    ("p", "A solução foi estruturada com um conjunto de ferramentas, linguagens e bancos de dados ([[stack]]) voltado "
          "para ciência de dados e aplicações [[web]], que inclui:"),
    ("i", "a)", "linguagem: Python, na versão 3.14 utilizada na imagem de publicação da API;"),
    ("i", "b)", "modelagem preditiva: biblioteca [[statsmodels]] (estimação do modelo SARIMAX – [[Seasonal "
                "AutoRegressive Integrated Moving Average with eXogenous inputs]] –, suavização exponencial de "
                "Holt-Winters e testes estatísticos) e [[scikit-learn]] ([[Random Forest]], utilizada nos experimentos "
                "para a importância relativa das variáveis);"),
    ("i", "c)", "processamento de dados: bibliotecas [[pandas]] e [[numpy]];"),
    ("i", "d)", "visualização: biblioteca [[matplotlib]], utilizada na análise exploratória e no diagnóstico dos "
                "modelos;"),
    ("i", "e)", "[[backend]]: [[framework]] FastAPI, com autenticação por [[JSON Web Token]] (JWT), perfis de acesso e "
                "senhas protegidas por [[bcrypt]], e banco de dados relacional acessado por meio do SQLAlchemy, em "
                "PostgreSQL, no serviço Neon, no ambiente de publicação, e em SQLite no desenvolvimento;"),
    ("i", "f)", "painel interativo: biblioteca React, com TypeScript e gráficos em Recharts, que consome a interface de "
                "programação de aplicações ([[Application Programming Interface]] – API) documentada na especificação "
                "OpenAPI;"),
    ("i", "g)", "relatórios: exportação em CSV, Excel e PDF, gerada no navegador a partir dos dados da API;"),
    ("i", "h)", "controle de versão: Git e GitHub;"),
    ("i", "i)", "ambiente de desenvolvimento: [[scripts]] Python para experimentação, nos quais cada versão dos modelos "
                "é treinada e avaliada antes de ser incorporada à aplicação, e módulos Python estruturados para "
                "produção, com testes automatizados em [[pytest]]."),
    ("p", "O [[pipeline]] de dados está organizado em três camadas: (i) ingestão das planilhas XLSX de vendas, enviadas "
          "pela gestão em periodicidade semanal ou mensal e conferidas antes da gravação; (ii) processamento e geração "
          "das séries diárias e das variáveis exógenas; e (iii) treinamento, validação e previsão, executados por "
          "solicitação do administrador após a carga das planilhas."),
    ("h2", "5.4 Preparação dos dados"),
    ("p", "A preparação dos dados é realizada por um [[pipeline]] de sete etapas. A primeira extrai os registros do "
          "relatório de contas a receber, organizado em blocos por documento de venda, gerando uma linha por produto "
          "em cada documento, com deduplicação entre arquivos e controle de reprocessamento por [[hash]] de cada "
          "planilha. A segunda padroniza textos, datas e valores e descarta registros sem os campos essenciais. A "
          "terceira deriva a unidade operacional, a partir da empresa emissora, e a categoria de cada produto, por "
          "tabelas de correspondência por código e regras aplicadas à descrição. A quarta remove os lançamentos de "
          "serviços e taxas, como frete e prestação de serviço, que não representam demanda de produto, e a quinta "
          "separa as vendas por unidade. A sexta separa as encomendas grandes do fluxo diário de vendas, e a sétima "
          "constrói o calendário diário de cada unidade, com feriados nacionais obtidos da BrasilAPI, fechamentos "
          "observados no histórico e aberturas excepcionais. Aplicado às 26 planilhas mensais do período, o "
          "[[pipeline]] produziu 351.092 registros, sem duplicatas, dos quais 345.491 correspondem à demanda de "
          "produtos, distribuídos em 5.208 códigos de produto. O mesmo processamento é executado pelo sistema a cada "
          "planilha enviada, com deduplicação em relação às vendas já gravadas."),
    ("p", "As três empresas do grupo foram consolidadas em duas unidades operacionais, Jardim Canadá, que reúne a "
          "floricultura e o [[garden center]], e Itabirito, e os produtos foram organizados em quatro categorias: "
          "Grama, com 45,5% do volume vendido; Plantas diversas, que reúne as plantas em geral, exceto as flores de "
          "corte, com 41,9%; Produtos de jardim, que reúne substratos, adubos, vasos e demais insumos, com 10,6%; e "
          "Flores de corte, com 1,8%. A classificação é feita a partir da descrição dos produtos, uma vez que o sistema "
          "da empresa não informa o grupo de cada item, e foi mantida pela entidade parceira na reunião de outubro de "
          "2026."),
    ("p", "As encomendas grandes são separadas da série modelada. Uma venda, identificada pela unidade, pela data e "
          "pelo número do documento, é classificada como encomenda grande quando a soma das quantidades de todos os "
          "seus itens supera 2.000 unidades; todos os itens do documento passam, então, a compor um fluxo à parte, e o "
          "restante, denominado fluxo diário, é a série prevista pelos modelos. A decisão é tomada sobre o documento "
          "inteiro, e não sobre cada linha, porque uma encomenda chega como um documento com vários itens, como grama, "
          "substrato e mudas, que, isoladamente, podem parecer vendas comuns. O limiar é fixo em unidades, e não "
          "estimado dos dados, o que dispensa seu recálculo em cada rodada de validação e evita o uso de informação "
          "futura; seu valor foi escolhido por análise de sensibilidade (Seção 8.2), e a classe corresponde aos "
          "pedidos de empresas que, segundo a entidade parceira, são preparados com antecedência junto aos "
          "fornecedores. Por esse critério, 93 vendas de Itabirito e 131 de Jardim Canadá foram classificadas como "
          "encomendas grandes, correspondendo a 52,1% e 22,5% do volume de cada unidade. Essas vendas não são "
          "descartadas: são registradas e apresentadas separadamente no painel."),
    ("h2", "5.5 Modelo preditivo"),
    ("p", "Na implementação, o modelo estatístico de séries temporais com regressores exógenos adotado é o SARIMAX, "
          "estimado com a biblioteca [[statsmodels]]. A suavização exponencial de Holt-Winters e o método de "
          "[[ensemble]] [[Random Forest]], da biblioteca [[scikit-learn]], foram utilizados apenas nos experimentos, o "
          "primeiro como modelo de comparação e o segundo na avaliação da importância relativa das variáveis exógenas "
          "(Seção 5.6)."),
    ("p", "Regressores exógenos são variáveis externas à série de vendas que ajudam a explicá-la e cujos valores "
          "futuros são conhecidos no momento da previsão. Neste trabalho, são variáveis de calendário: saber, com "
          "antecedência, que um dia será domingo, feriado ou dia de abertura excepcional da loja permite ao modelo "
          "ajustar a previsão daquele dia, em vez de tratá-lo como um dia comum. O SARIMAX foi escolhido, em vez de "
          "outros modelos com regressores, porque combina em um único modelo três elementos necessários a este "
          "problema: a dependência das vendas em relação aos dias anteriores, a sazonalidade semanal e o efeito dos "
          "regressores de calendário. Uma regressão linear com as mesmas variáveis ignoraria a dependência entre dias "
          "consecutivos; a suavização exponencial de Holt-Winters não incorpora regressores exógenos; e modelos de "
          "aprendizado de máquina, como redes neurais e árvores de decisão, exigiriam um histórico maior que os 26 "
          "meses disponíveis (MAKRIDAKIS; SPILIOTIS; ASSIMAKOPOULOS, 2020). Além disso, o SARIMAX produz um intervalo "
          "de previsão para cada dia, apresentado ao usuário como a faixa provável de venda."),
    ("p", "As séries modeladas foram definidas a partir do padrão de demanda de cada série. Pelo critério de Syntetos, "
          "Boylan e Croston (2005), cada série é classificada por dois indicadores: o ADI, que mede de quantos em "
          "quantos dias, em média, ocorre uma venda, e o CV², que mede o quanto a quantidade vendida varia entre os "
          "dias com venda. Combinados, eles definem quatro padrões:"),
    ("i", "a)", "suave: vende quase todos os dias (ADI menor que 1,32), em quantidades parecidas (CV² menor que 0,49);"),
    ("i", "b)", "errática: vende quase todos os dias, mas em quantidades muito variáveis (ADI menor que 1,32 e CV² "
                "igual ou maior que 0,49);"),
    ("i", "c)", "intermitente: vende em poucos dias, em quantidades parecidas (ADI igual ou maior que 1,32 e CV² menor "
                "que 0,49);"),
    ("i", "d)", "[[lumpy]]: vende em poucos dias e em quantidades muito variáveis (ADI igual ou maior que 1,32 e CV² "
                "igual ou maior que 0,49)."),
    ("p", "As séries diárias de cada categoria em cada unidade registram venda em cerca de 82% dos dias, o que "
          "corresponde a um ADI de aproximadamente 1,2, mas o volume vendido varia fortemente entre dias comuns, "
          "datas comemorativas e dias de grandes pedidos; por isso, apresentam demanda errática, padrão adequado a "
          "modelos como o SARIMAX. Já o produto típico, que vende em apenas 9 dos 789 dias, tem ADI próximo de 88, e "
          "99,3% dos produtos classificáveis apresentam demanda intermitente ou [[lumpy]]. As séries também mostram "
          "sazonalidade clara: há um padrão semanal de dia útil, com pico entre terça e quinta-feira para Grama e para "
          "os demais produtos de jardinagem em Jardim Canadá e na sexta-feira para Flores de corte, menor movimento "
          "aos sábados e loja fechada aos domingos; e há um padrão de datas comemorativas, com Flores de corte "
          "vendendo de 1,7 a 5,0 vezes a média no Dia da Mulher, no Dia das Mães e no Dia dos Namorados."),
    ("p", "Por isso, a solução define uma série diária para cada uma das quatro categorias de cada unidade e uma para "
          "cada produto de grama, e cada série tem o seu próprio modelo SARIMAX. A previsão total da unidade é obtida "
          "pela soma das previsões das categorias, inclusive dos limites do intervalo, o que produz uma faixa "
          "conservadora, mais larga que a de um modelo ajustado à série da loja. Os demais produtos, de demanda "
          "intermitente, não recebem previsão individual. A previsão por produto foi restrita à grama porque a "
          "empresa compra esses itens produto a produto, conforme definido com a entidade parceira, e porque a "
          "categoria reúne 14 variedades que concentram quase metade do volume vendido, com séries densas o bastante "
          "para um modelo próprio. Uma série só é modelada quando dispõe de pelo menos 180 dias de histórico antes do "
          "período de validação e, no caso de produto, quando registra venda em pelo menos 28 dos 365 dias mais "
          "recentes; caso contrário, recebe o status de dados insuficientes e fica sem previsão."),
    ("p", "O modelo é representado pela notação SARIMAX(p, d, q)(P, D, Q)m, cujos termos são explicados a seguir:"),
    ("i", "a)", "y: quantidade vendida em um dia, em uma unidade, de uma categoria ou de um produto de grama, sem as "
                "encomendas grandes, isto é, o valor que se deseja prever;"),
    ("i", "b)", "p: número de termos autorregressivos, isto é, quantos dias anteriores da própria série entram no "
                "cálculo da previsão;"),
    ("i", "c)", f"d: ordem da diferenciação regular. Com d{NB}={NB}0, o modelo trabalha com o nível das vendas e inclui "
                "uma constante, de modo que a previsão converge para a média do período de treinamento; com "
                f"d{NB}={NB}1, o modelo trabalharia com a variação de um dia para o seguinte, e a previsão partiria do "
                "nível recente das vendas. As duas opções foram comparadas nos experimentos;"),
    ("i", "d)", "q: número de termos de médias móveis, isto é, quantos erros de previsão recentes são usados para "
                "corrigir a previsão seguinte;"),
    ("i", "e)", f"m: período da sazonalidade. Com m{NB}={NB}7, a sazonalidade é semanal, pois o padrão de vendas se "
                "repete a cada sete dias;"),
    ("i", "f)", "P, D e Q: equivalentes a p, d e q na escala sazonal, isto é, comparando o mesmo dia da semana em "
                f"semanas anteriores, por exemplo uma terça-feira com as terças-feiras anteriores. Com D{NB}={NB}0, não "
                "se aplica diferenciação sazonal, e o padrão semanal é representado pelos termos sazonais P e Q e pelos "
                "indicadores de dia da semana."),
    ("p", "Os valores de p e q são testados entre 0 e 2, e os de P e Q entre 0 e 1, em 36 combinações, com "
          f"m{NB}={NB}7, d{NB}={NB}0 e D{NB}={NB}0; o modelo escolhido é a combinação com menor AIC, ajustada apenas na "
          "janela de 365 dias anterior ao período de validação. As variáveis exógenas são seis indicadores de dia da "
          "semana, que valem 1 no dia correspondente, de segunda-feira a sábado, e 0 nos demais; um indicador de loja "
          "fechada, que reúne domingos, feriados nacionais obtidos da BrasilAPI, inclusive o Carnaval, e fechamentos "
          "observados no histórico; e um indicador de abertura excepcional, que representa os dias de Dia das Mães e "
          "de Finados em que a unidade de Itabirito abre. O modelo é ajustado à série na escala original, sem "
          "transformação logarítmica, sobre uma janela deslizante com os 365 dias mais recentes. A previsão pontual "
          "corresponde à média da distribuição prevista, truncada em zero, e é acompanhada do intervalo de previsão "
          "de 95%. Essa configuração resultou dos experimentos descritos na Seção 5.6, cujos resultados são "
          "apresentados na Seção 8.2."),
    ("p", "O treinamento é solicitado pelo administrador, por meio do botão “Treinar previsões” do painel, depois do "
          "envio das planilhas, ou por um [[script]] executado pela equipe técnica sobre o mesmo banco de dados. Ele é "
          "executado em segundo plano, com as séries distribuídas entre processos paralelos, e só ocorre quando as "
          "vendas, o calendário ou o catálogo de produtos mudaram desde o último treinamento concluído, o que é "
          "verificado por uma impressão digital ([[hash]] SHA-256) desses dados; sem mudança, o pedido é registrado "
          "como dispensado. Cada treinamento registra a configuração utilizada, a versão do código, o período dos "
          "dados e o resultado de cada série, e as telas exibem sempre o último treinamento concluído."),
    ("p", "A previsão de cada dia é preservada depois que o dia passa, formando um histórico congelado: cada novo "
          "treinamento substitui apenas os dias a partir do dia seguinte à última venda e preenche os dias ainda sem "
          "previsão com o primeiro dia de cada janela da validação [[walk-forward]]. Assim, o histórico mostra, para "
          "cada dia, a previsão disponível para a empresa antes de ele ocorrer, sem reescrever o passado, e permite "
          "comparar a quantidade prevista com a vendida."),
]
