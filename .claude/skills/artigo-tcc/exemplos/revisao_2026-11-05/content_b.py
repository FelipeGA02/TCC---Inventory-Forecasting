# -*- coding: utf-8 -*-
"""Conteúdo do artigo: seções 5.6 e 5.7 e capítulos 6 e 7."""
from content_a import FONTE, FONTE_ENT, NB

CAP5B = [
    ("h2", "5.6 Delineamento experimental"),
    ("p", "A configuração da solução final foi definida por uma sequência de experimentos, executados em [[scripts]] "
          "Python separados da aplicação. Cada experimento partiu da melhor configuração disponível até então e "
          "alterou um único fator, mantendo a série, o período de teste e as métricas, de modo que a diferença de "
          "desempenho pudesse ser atribuída ao fator alterado. O Quadro 2 resume os experimentos, o fator avaliado, a "
          "série e o protocolo de validação de cada um."),
    ("quadro", "Quadro 2 – Experimentos realizados", [794, 2041, 2948, 3289],
     ["Exp.", "Fator avaliado", "Série e protocolo", "Configurações comparadas"],
     [["E1", "Referência inicial", "Série total da rede; 26 janelas de 14 dias e teste de fevereiro de 2026",
       "SARIMA sem variáveis exógenas, em log(1 + y), com d definido pelo teste ADF"],
      ["E2", "Variáveis exógenas", "Mesma série e protocolo de E1",
       "Sem exógenas; calendário; calendário e clima"],
      ["E3", "Separação das encomendas por linha e limitação de picos", "Série de cada unidade; 26 janelas de 14 dias",
       "Original; só limitação no percentil 99; só separação; separação e limitação"],
      ["E4", "Modelo por unidade, calendário e diferenciação", "Venda de balcão de cada unidade; 26 janelas de 14 dias",
       f"Sem calendário; calendário com d{NB}={NB}0; calendário com d{NB}={NB}1; Holt-Winters"],
      ["E5", "Critério de encomenda grande", "Vendas das duas unidades, de janeiro de 2024 a fevereiro de 2026",
       "Limiares de 500 a 5.000 unidades por venda; escore z modificado por linha"],
      ["E6", "Transformação logarítmica e janela de treinamento", "Itabirito; 351 origens diárias, horizonte de 14 dias",
       "log(1 + y) e escala original; série total e fluxo diário; janela expansiva e deslizante"],
      ["E7", "Modelo por produto", "Produtos de venda regular de Itabirito; 351 origens diárias",
       f"SARIMAX por produto com d{NB}={NB}0 e d{NB}={NB}1, em log(1 + y) e na escala original; desagregação da "
       "previsão da loja"],
      ["E8", "Nível de agregação das categorias", "Quatro categorias das duas unidades; 351 origens diárias",
       "SARIMAX direto na categoria; desagregação da previsão da loja"],
      ["E9", "Diferenciação nas categorias e nos produtos de grama",
       "Quatro categorias e dois produtos de grama por unidade", f"Testes ADF e KPSS; d{NB}={NB}0 e d{NB}={NB}1 com "
       "janela deslizante de 365 dias"],
      ["E10", "Solução definitiva", "Quatro categorias e produtos de grama das duas unidades; 56 origens diárias",
       "Configuração final (Seção 5.5)"]],
     ["center", "left", "left", "left"], FONTE),
    ("p", "Foram utilizados dois protocolos de validação [[walk-forward]]. Nos experimentos E1 a E4, o período de "
          "março de 2025 a fevereiro de 2026 foi dividido em 26 janelas consecutivas de 14 dias, e a ordem do modelo "
          "foi escolhida apenas com os dados anteriores a 2 de março de 2025; cobrir um ano completo garante que todas "
          "as datas comemorativas sejam avaliadas, e dezembro de 2025 e fevereiro de 2026, meses de alta e de queda das "
          "vendas, foram analisados também em separado. Nos experimentos E6 a E8, a origem da previsão avançou um dia "
          "por vez a partir de 2 de março de 2025, em 351 origens, cada uma prevendo os 14 dias seguintes, o que "
          "reproduz o uso diário do sistema; nesse caso, cada dia avaliado aparece em até 14 janelas, uma por "
          "horizonte. Em todos os casos, o modelo é ajustado apenas com os dados anteriores a cada origem, e todo "
          "parâmetro estimado dos dados, como o limiar das encomendas em E3 e E4, é recalculado em cada rodada."),
    ("p", "A métrica primária é o MASE, calculado com a escala da previsão ingênua sazonal semanal no período de "
          "treinamento. Como essa escala pode tornar o MASE otimista quando o treinamento contém picos, reporta-se "
          "também o erro relativo à previsão ingênua na mesma janela de teste, dado pela razão entre o erro absoluto "
          "acumulado do modelo e o da previsão ingênua, o número de janelas em que o modelo supera a previsão ingênua, "
          "o MAE e a RMSE em unidades vendidas, a cobertura empírica e a largura média do intervalo de 95% e a razão "
          "entre o volume previsto e o vendido, que mede o viés da previsão. Nos experimentos E7, E8 e E10, as "
          "métricas são calculadas apenas nos dias de loja aberta, pois domingos e feriados, com venda e previsão "
          "próximas de zero, reduzem o MASE e elevam a cobertura sem informar sobre a qualidade da previsão. "
          "Diferenças de erro inferiores a 5% foram tratadas como empate."),
    ("p", "No experimento E2, as variáveis candidatas foram dia da semana, feriado ou loja fechada, véspera e dia "
          "seguinte a feriado, janelas de sete dias antes de cada data comemorativa (Dia das Mães, Dia dos Namorados, "
          "Dia da Mulher, Dia dos Pais, Finados e Natal), primeira semana do mês e, na versão com clima, a precipitação "
          "do dia, a precipitação acumulada em sete dias e a temperatura máxima, obtidas do serviço Open-Meteo com os "
          "valores observados. As variáveis foram avaliadas pela significância dos coeficientes, pela importância "
          "relativa calculada pela [[Random Forest]] e pelo ganho de acurácia na validação. A importância relativa foi "
          "usada como diagnóstico, e não como peso das variáveis, porque, em um modelo linear como o SARIMAX, a escala "
          "atribuída a uma variável é absorvida pelo seu coeficiente."),
    ("p", "Nos experimentos E1 a E4, a série foi modelada em log(1" + NB + "+" + NB + "y), e a previsão pontual foi "
          "obtida pela conversão da previsão de volta à escala original, o que corresponde à mediana da distribuição "
          "prevista. Em E4, foram avaliadas ainda duas formas de corrigir o viés dessa conversão: um fator "
          "multiplicativo estimado dos resíduos e uma calibração pela razão entre o volume vendido e o previsto nas "
          "quatro janelas anteriores. O experimento E6 isolou o efeito da transformação, mantendo a ordem do modelo, "
          f"as variáveis exógenas e d{NB}={NB}1 iguais em todas as variantes."),
    ("h2", "5.7 Testes e validação"),
    ("p", "A validação do sistema contempla três dimensões, descritas a seguir com a justificativa de cada teste; os "
          "valores obtidos são apresentados na Seção 8:"),
    ("i", "a)", "validação estatística dos modelos: validação [[walk-forward]] da solução definitiva, executada a cada "
                "treinamento. A origem avança um dia por vez nas 56 datas mais recentes que dispõem de 14 dias de "
                "vendas conhecidas, isto é, nas últimas oito semanas, e em cada origem o modelo é reajustado nos 365 "
                "dias anteriores e prevê os 14 dias seguintes; a ordem do modelo é escolhida apenas com os dados "
                "anteriores à primeira origem. As métricas, calculadas nos dias de loja aberta, são as descritas na "
                "Seção 5.6. O modelo recebe o status de confiável quando o MASE é inferior a 1,0, pois um valor abaixo "
                "de 1 indica que o modelo erra menos do que repetir as vendas da semana anterior, e quando a cobertura "
                "empírica do intervalo de 95% fica entre 90% e 98%, para que a faixa apresentada ao usuário seja "
                "confiável. Os modelos que não atendem aos limiares recebem o status de baixa confiança e continuam "
                "gerando previsões, acompanhadas de aviso de uso com cautela no painel;"),
    ("i", "b)", "testes de diagnóstico de resíduos: teste de Ljung-Box, com defasagens de até 14 dias, que verifica se "
                "os erros do modelo ainda guardam relação com os erros dos dias anteriores; caso guardem, há um padrão "
                "nas vendas que o modelo não capturou. Teste de Shapiro-Wilk, que verifica se os erros seguem "
                "distribuição normal, hipótese em que se baseiam os intervalos teóricos; caso seja rejeitada, a "
                "cobertura dos intervalos passa a ser verificada empiricamente na validação [[walk-forward]]. Os dois "
                "testes são aplicados aos resíduos do ajuste final de cada modelo e registrados como diagnóstico "
                "complementar, sem impedir sua disponibilização;"),
    ("i", "c)", "testes funcionais do sistema: {TESTES_TEXTO} A validação junto à entidade parceira foi feita por "
                "demonstração da versão em desenvolvimento na reunião de outubro de 2026, em que a empresa considerou "
                "o sistema satisfatório e aprovou a continuidade do projeto; os testes de usabilidade com a gestora de "
                "compras, usuária não técnica com perfil de administrador (Quadro 5), ainda não foram realizados."),
]

CAP6 = [
    ("h1", "6 REQUISITOS DO SISTEMA"),
    ("p", "Os requisitos foram levantados conforme o procedimento descrito na Seção 5.2, validados junto à equipe da "
          "Floricultura Verde Perto e priorizados conforme seu impacto operacional e estratégico. A partir das "
          "reuniões, da análise dos relatórios financeiros e da inspeção das planilhas, identificaram-se as "
          "necessidades de negócio, as restrições operacionais e os critérios de aceitação de cada funcionalidade, "
          "organizados nas subseções a seguir."),
    ("h2", "6.1 Requisitos funcionais"),
    ("p", "O Quadro 3 apresenta os requisitos funcionais do sistema."),
    ("quadro", "Quadro 3 – Requisitos funcionais do sistema de previsão de vendas", [1134, 6521, 1417],
     ["Código", "Descrição", "Prioridade"],
     [["RF01", "Permitir o envio de planilhas de vendas de forma simples, sem necessidade de conhecimento técnico", "Alta"],
      ["RF02", "Gerar a previsão diária dos 14 dias seguintes para cada categoria e para cada produto de grama de cada "
               "unidade, com intervalo de 95%", "Alta"],
      ["RF03", "Atualizar os modelos preditivos com os novos dados inseridos, por solicitação do administrador", "Alta"],
      ["RF04", "Exibir indicadores de desempenho do modelo de forma simples e explicada para usuários não técnicos", "Alta"],
      ["RF05", "Apresentar gráficos de vendas e de previsão por período, categoria, produto e unidade", "Alta"],
      ["RF06", "Identificar e destacar os produtos mais vendidos em cada período", "Alta"],
      ["RF07", "Conferir cada planilha antes da gravação, informando o período de cada unidade, as vendas novas e já "
               "carregadas e os dias de loja aberta sem venda", "Alta"],
      ["RF08", "Apresentar o histórico das previsões, comparando a quantidade prevista com a vendida em cada dia", "Alta"],
      ["RF09", "Notificar o andamento e o resultado do treinamento, a existência de vendas ainda não utilizadas pela "
               "previsão e as previsões de uso com cautela", "Média"],
      ["RF10", "Exportar relatórios de previsão, de vendas e de desempenho nos formatos PDF e Excel", "Média"],
      ["RF11", "Disponibilizar painel centralizado para visualização de dados, gráficos e envio de planilhas", "Alta"],
      ["RF12", "Disponibilizar documentação funcional e técnica sobre o uso e o funcionamento do sistema", "Média"]],
     ["center", "left", "center"], FONTE_ENT),
    ("p", "As solicitações de identificar produtos comprados em conjunto, de simular promoções e vendas conjugadas e de "
          "emitir avisos de reposição, registradas nas reuniões iniciais, não integram esta versão do sistema: o escopo "
          "foi delimitado à previsão diária da demanda, com a decisão de compra mantida pela empresa, e essas "
          "funcionalidades são indicadas como trabalhos futuros (Seção 9)."),
    ("h2", "6.2 Requisitos não funcionais"),
    ("p", "Os requisitos não funcionais estabelecem critérios de qualidade da solução e são apresentados no Quadro 4."),
    ("quadro", "Quadro 4 – Requisitos não funcionais do sistema", [1134, 1814, 6124],
     ["Código", "Categoria", "Descrição"],
     [["RNF01", "Usabilidade", "A interface deve ser intuitiva e acessível a usuários não técnicos, sem necessidade de "
                               "treinamento especializado para as funções principais de visualização e envio de planilhas."],
      ["RNF02", "Confiabilidade", "O processamento dos dados deve ser consistente e rastreável, com registro de logs de "
                                  "execução e identificação de anomalias na entrada de dados."],
      ["RNF03", "Desempenho", "O treinamento dos modelos deve ser concluído em menos de duas horas e executado em "
                              "segundo plano, sem comprometer a disponibilidade do painel."],
      ["RNF04", "Segurança", "O sistema deve implementar controle de acesso por perfil de usuário e proteção dos dados "
                             "operacionais da empresa, em conformidade com a LGPD (BRASIL, 2018)."],
      ["RNF05", "Manutenibilidade", "O código deve ser modular, documentado e versionado, permitindo evolução e "
                                    "manutenção por equipe técnica sem dependência dos desenvolvedores originais."]],
     ["center", "left", "left"], FONTE),
    ("h2", "6.3 Regras de negócio"),
    ("p", "As regras de negócio expressam restrições e políticas operacionais que o sistema deve respeitar, derivadas "
          "da rotina da floricultura e das definições acordadas com a entidade parceira:"),
    ("i", "a)", "RN01: a previsão de demanda deve ser diária e respeitar o horizonte operacional de reposição, definido "
                "em 14 dias;"),
    ("i", "b)", "RN02: os modelos preditivos devem ser retreinados somente quando houver vendas, calendário ou catálogo "
                "novos desde o último treinamento concluído, e cada treinamento deve registrar a configuração, a versão "
                "do código e o período dos dados utilizados;"),
    ("i", "c)", "RN03: a previsão exibida para um dia não deve ser alterada por treinamentos realizados depois dessa "
                "data, de modo que o histórico reflita a previsão disponível antes de cada venda;"),
    ("i", "d)", "RN04: séries com menos de 180 dias de histórico e produtos com venda em menos de 28 dos últimos 365 "
                "dias não recebem previsão, e séries que não atingem os critérios de aceitação recebem previsão "
                "acompanhada de aviso de uso com cautela;"),
    ("i", "e)", "RN05: apenas usuários com perfil autorizado podem enviar planilhas e disparar o treinamento dos "
                "modelos;"),
    ("i", "f)", "RN06: o calendário de cada unidade, com feriados, fechamentos e aberturas excepcionais, deve ser "
                "considerado no cálculo da previsão, e os dias sem cadastro seguem o padrão de loja fechada apenas aos "
                "domingos;"),
    ("i", "g)", "RN07: toda importação de dados e todo treinamento devem registrar log de execução, permitindo "
                "rastreabilidade e identificação de anomalias;"),
    ("i", "h)", "RN08: encomendas grandes, isto é, vendas com mais de 2.000 unidades no mesmo documento, devem ser "
                "separadas da série utilizada no ajuste dos modelos e apresentadas como fluxo de demanda à parte."),
    ("h2", "6.4 Atores do sistema"),
    ("p", "Os atores representam os perfis de usuários que interagem com o sistema, conforme o Quadro 5."),
    ("quadro", "Quadro 5 – Atores do sistema", [2835, 6237], ["Ator", "Descrição"],
     [["Administrador (gestora de compras)", "Envia e confere planilhas, solicita o treinamento das previsões e acessa "
                                             "as funcionalidades de consulta e exportação."],
      ["Usuário de consulta (gerente de operações)", "Consulta a previsão, o histórico das previsões, as análises de "
                                                     "vendas e as vendas importadas, recebe notificações e exporta "
                                                     "relatórios, sem permissão para enviar planilhas ou treinar os "
                                                     "modelos."]],
     ["left", "left"], FONTE_ENT),
    ("h2", "6.5 Modelagem do sistema"),
    ("p", "Os requisitos e a estrutura da solução foram modelados por meio de diagramas de casos de uso, de atividades "
          "e de classes, em notação [[Unified Modeling Language]] (UML), complementados pelo modelo de dados e pela "
          "arquitetura lógica, apresentados a seguir."),
    ("p", "O diagrama de casos de uso, apresentado na Figura 2, sintetiza as funcionalidades do sistema sob a "
          "perspectiva dos atores. A gestora de compras, com perfil de administrador, concentra as interações que "
          "alteram a base e os modelos, como o envio de planilhas, que inclui a conferência antes da gravação, e o "
          "treinamento das previsões, que inclui a validação e o treinamento de cada série, além de todas as "
          "funcionalidades de consulta. O gerente de operações, com perfil de consulta, consulta a previsão diária, o "
          "histórico das previsões, as análises de vendas e as vendas importadas, recebe notificações e exporta "
          "relatórios."),
    ("fig", "fig1_casos_de_uso", "Figura 2 – Diagrama de casos de uso", 5040000),
    ("p", "O diagrama de atividades, exibido na Figura 3, representa o fluxo principal, desde o envio da planilha de "
          "vendas até a exibição das previsões. Após o envio, a planilha é conferida sem gravação, e o sistema "
          "apresenta o período de cada unidade, as vendas novas e já carregadas e os dias de loja aberta que ficariam "
          "sem venda; confirmada pela gestora, as vendas novas são gravadas e as encomendas grandes, marcadas. Quando o "
          "treinamento é solicitado, o sistema verifica se os dados mudaram desde o último treinamento concluído e, em "
          "caso afirmativo, monta as séries diárias de cada unidade e, para cada série com histórico suficiente, "
          "seleciona a ordem do modelo, executa a validação [[walk-forward]] e classifica o modelo como confiável ou "
          "de uso com cautela. Em seguida, gera a previsão dos 14 dias seguintes, grava o histórico congelado e "
          "disponibiliza os resultados no painel e nos relatórios."),
    ("fig", "fig2_atividades", "Figura 3 – Diagrama de atividades do fluxo de previsão", 3960000),
    ("p", "O diagrama de classes, apresentado na Figura 4, descreve as principais entidades do domínio e seus "
          "relacionamentos. As classes de origem dos dados (Usuario, Planilha, Venda, Produto, Categoria, Loja e "
          "DiaCalendario) alimentam a construção da SerieDiaria de cada categoria ou produto de grama de uma loja, que, "
          "com as variáveis de calendário, sustenta o ModeloSerie. Cada Treino reúne os modelos das séries; cada "
          "modelo gera objetos de PrevisaoDiaria, que, depois que o dia passa, são preservados como PontoHistorico e "
          "subsidiam a geração de Relatorios."),
    ("fig", "fig3_classes", "Figura 4 – Diagrama de classes", 5760000),
    ("p", "O modelo entidade-relacionamento, apresentado na Figura 5, organiza o armazenamento em banco de dados "
          "relacional, PostgreSQL no ambiente de publicação e SQLite no desenvolvimento. As tabelas users e "
          "revoked_tokens registram os usuários, com senhas armazenadas em [[hash]] bcrypt, e as sessões encerradas; "
          "units, categories, products e calendar_days mantêm as unidades, o catálogo e o calendário de cada loja; "
          "sales armazena cada item vendido, com a marcação de encomenda grande, e processing_log registra cada "
          "planilha importada. As tabelas forecast_jobs e forecast_job_logs registram cada treinamento e o resultado "
          "de cada série; series_models guarda a ordem, as métricas e os coeficientes de cada modelo; "
          "series_forecasts e series_backtest_points armazenam a previsão dos 14 dias e os pontos da validação "
          "[[walk-forward]]; e forecast_history guarda o histórico congelado das previsões."),
    ("fig", "fig4_modelo_de_dados", "Figura 5 – Modelo de dados (entidade-relacionamento)", 5760000),
    ("p", "A arquitetura lógica, ilustrada na Figura 6, organiza-se em quatro camadas. A camada de ingestão recebe as "
          "planilhas de vendas, confere-as antes da gravação, registra cada importação e mantém a base de vendas "
          "deduplicada; a camada de processamento realiza a padronização, a classificação dos produtos, a marcação das "
          "encomendas grandes e a construção do calendário e das séries diárias; a camada de modelagem, implementada "
          "como serviço de previsão, ajusta o modelo de cada série, executa a validação [[walk-forward]], gera a "
          "previsão e grava o histórico; e a camada de apresentação expõe os resultados por meio de uma API no padrão "
          "[[Representational State Transfer]] (REST) com autenticação, consumida pelo painel interativo, que também "
          "gera a exportação dos relatórios. O [[backend]] é implementado como monólito modular, no qual a lógica de "
          "domínio não depende de [[frameworks]] de entrada e saída, o que favorece os testes isolados, a "
          "manutenibilidade e a evolução independente dos componentes."),
    ("fig", "fig5_arquitetura", "Figura 6 – Arquitetura lógica do sistema", 3600000),
]
