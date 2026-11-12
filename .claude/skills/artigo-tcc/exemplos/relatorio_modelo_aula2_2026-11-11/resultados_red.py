h1("11 RESULTADOS E DISCUSSÕES")
p("Este capítulo apresenta o que foi alcançado com a implementação e os resultados que definiram a configuração do "
  "sistema: as funcionalidades em operação, a validação dos requisitos, os testes do sistema, a análise exploratória "
  "dos dados, os experimentos de modelagem e a validação da solução definitiva, seguidos da comparação com os "
  "objetivos e da discussão.")
h2("11.1 Apresentação dos Resultados")
p("As funcionalidades especificadas no Capítulo 7 estão implementadas e em operação com os dados reais da "
  "empresa. O banco de produção contém as 26 planilhas de janeiro de 2024 a fevereiro de 2026, com 351.092 linhas "
  "e nenhuma planilha duplicada, e o último treinamento, concluído em 10 de novembro de 2026 com as vendas até 28 "
  "de fevereiro de 2026, gerou a previsão de 23 séries, 8 categorias e 15 produtos de grama, e registrou 20 "
  "séries sem previsão por falta de dados. As telas da Seção 10.2 foram capturadas desse banco e evidenciam o "
  "funcionamento da análise das vendas, do envio e da conferência de planilhas, da consulta das vendas, da "
  "previsão diária no horizonte escolhido, do histórico das previsões e dos relatórios. O relatório gerencial em "
  "PDF gerado para as duas semanas seguintes à última venda, de 1º a 14 de março de 2026, prevê 42.313 unidades "
  "para as duas lojas, com média de 3.526 unidades por dia de loja aberta, e traz o acerto de cada categoria no "
  "teste do treinamento.")
h2("11.2 Validação dos Requisitos")
p("O {qd:validacao} retoma os requisitos do Capítulo 7 e as solicitações das reuniões iniciais e informa se cada "
  "um foi atendido.")
tnew("validacao", "qd", "Validação dos requisitos",
     ["Requisito", "Situação", "Observação"],
     [["RF01 – Envio de planilhas", "Atendido", "Envio em quatro etapas, por arrastar ou selecionar o arquivo"],
      ["RF02 – Previsão diária", "Atendido", "Previsão de 91 dias de 23 séries, exibida de duas semanas a três meses ({fig:previsao})"],
      ["RF03 – Atualização dos modelos", "Atendido", "Botão Treinar previsões e ⟨script⟩, com dispensa quando não há dados novos"],
      ["RF04 – Indicadores de desempenho", "Atendido", "Erro por dia e margem de incerteza explicados na tela e acerto por série nos relatórios ({fig:historico})"],
      ["RF05 – Gráficos de vendas e previsão", "Atendido", "Telas Início e Previsão de Vendas"],
      ["RF06 – Produtos mais vendidos", "Atendido", "Tabela dos produtos mais vendidos no último ano ({fig:inicio})"],
      ["RF07 – Conferência da planilha", "Atendido", "Período, vendas novas e dias sem venda antes da gravação ({fig:conferencia})"],
      ["RF08 – Histórico das previsões", "Atendido", "Previsão mais antiga de cada dia comparada ao vendido ({fig:historico})"],
      ["RF09 – Notificações", "Atendido", "Andamento do treinamento e avisos sobre a base no cabeçalho"],
      ["RF10 – Exportação de relatórios", "Atendido", "Relatórios em PDF, Excel e CSV ({fig:relatorios})"],
      ["RF11 – Painel centralizado", "Atendido", "Cinco telas acessíveis por um menu único"],
      ["RF12 – Documentação", "Parcialmente atendido", "Documentação técnica, contrato da API e registros de decisão no repositório, sem manual do usuário"],
      ["RNF01 – Usabilidade", "Parcialmente atendido", "Telas aprovadas pela empresa nas reuniões, sem teste formal de usabilidade"],
      ["RNF02 – Confiabilidade", "Atendido", "Registro de cada planilha e de cada treinamento, com log série a série"],
      ["RNF03 – Desempenho", "Atendido", "Treinamento de produção em 75 minutos, em segundo plano (Seção 11.3)"],
      ["RNF04 – Segurança", "Atendido", "JWT, perfis de acesso, senhas em ⟨bcrypt⟩, limite de tentativas de login e nenhum dado pessoal de cliente armazenado"],
      ["RNF05 – Manutenibilidade", "Atendido", "Código modular e versionado, com 196 testes automatizados"],
      ["Produtos comprados em conjunto, simulação de promoções e avisos de reposição", "Não atendido", "Fora do escopo desta versão e indicados como trabalhos futuros"]],
     [3000, 1700, 4372], F_AUT, "grade", ["left", "center", "left"])
p("Dos 17 requisitos funcionais e não funcionais, 15 foram atendidos e 2 foram atendidos parcialmente, a "
  "documentação, que não inclui um manual do usuário, e a usabilidade, que foi avaliada apenas de forma "
  "qualitativa nas reuniões. As solicitações das reuniões iniciais que não integram esta versão foram retiradas do "
  "escopo de comum acordo com a entidade parceira.")
h2("11.3 Resultados dos Testes")
p("Os testes automatizados foram executados em 11 de novembro de 2026, e a {tab:testes} resume os resultados. Os "
  "testes verificam a seleção da ordem e da diferenciação, a validação " + WF + " e as métricas do treinamento, o "
  "fator das datas comemorativas, a regra do histórico das previsões, a conferência das planilhas, a autenticação "
  "e os perfis de acesso e as respostas do painel, e os 196 casos foram aprovados. A suíte de ponta a ponta, com 39 "
  "testes, não foi concluída nessa execução, porque a preparação da base sintética excedeu o tempo limite do "
  "servidor de testes.")
tnew("testes", "tab", "Resultados dos testes automatizados",
     ["Conjunto", "Casos executados", "Casos aprovados", "Sucesso"],
     [["Testes unitários (⟨pytest⟩)", "120", "120", "100%"],
      ["Testes de integração (⟨pytest⟩)", "76", "76", "100%"],
      ["Total", "196", "196", "100%"]],
     [3672, 1800, 1800, 1800], "Fonte: Elaborado pelos autores (2026). Execução de 11 de novembro de 2026, concluída em 3 min 37 s.",
     "aberta", ["left", "center", "center", "center"])
cp("A importação foi testada com planilhas de vendas fictícias de março de 2026",
   ("O teste também mostrou um caso não detectado: uma nota repetida inteira dentro da mesma planilha entra duas "
    "vezes, porque a duplicidade é verificada apenas contra a base já gravada.",
    "O teste também revelou um defeito ainda não corrigido: uma nota repetida inteira dentro da mesma planilha entra "
    "duas vezes, porque a duplicidade é verificada apenas em relação à base já gravada."))
p("O tempo de resposta da API foi medido com a API executada localmente e conectada ao banco de produção, em dez "
  "requisições a cada rota de consulta ({tab:tempo}). As rotas responderam, em média, entre 0,44 e 0,87 segundo, "
  "inclusive a do painel, que transfere cerca de 311 kB com a previsão de 91 dias de todas as séries. O "
  "treinamento de produção, com as 43 séries, foi executado com 12 processos paralelos e levou 75 minutos, dentro "
  "do limite de duas horas do requisito RNF03. Não foram realizados testes formais de usabilidade, e a avaliação "
  "da interface foi qualitativa, nas reuniões de outubro e novembro de 2026, em que a empresa aprovou as telas.")
tnew("tempo", "tab", "Tempo médio de resposta das rotas de consulta da API",
     ["Rota", "Conteúdo", "Tempo médio (s)"],
     [["/api/v1/contexto", "Lojas, categorias, última venda e situação das séries", "0,867"],
      ["/api/v1/painel", "Previsão de 91 dias, vendas recentes e acerto", "0,550"],
      ["/api/v1/analises", "Resumos da tela inicial", "0,521"],
      ["/api/v1/registros/linhas", "Página de 50 vendas da conferência", "0,570"],
      ["/api/v1/servico-previsao/status", "Andamento do treinamento", "0,728"],
      ["/api/v1/atividades", "Planilhas enviadas e treinamentos", "0,443"]],
     [3200, 4072, 1800], "Fonte: Elaborado pelos autores (2026). Dez requisições por rota, API local conectada ao banco de produção, em 11 de novembro de 2026.",
     "aberta", ["left", "left", "center"])
h2("11.4 Análise Exploratória dos Dados")
p("Aplicado às 26 planilhas mensais de janeiro de 2024 a fevereiro de 2026, o ⟨pipeline⟩ produziu 351.092 "
  "registros, sem duplicatas, dos quais 345.399 correspondem à demanda de produtos, distribuídos em 5.204 códigos "
  "de produto. Em volume vendido, a Grama responde por 48,4%, Plantas diversas, por 38,2%, Produtos de jardim, por "
  "11,5%, e Flores de corte, por 1,8%. Com o critério de encomenda grande, o limiar é de 1.343 unidades em Jardim "
  "Canadá e de 1.960 unidades em Itabirito, e 209 e 96 vendas, respectivamente, foram classificadas como "
  "encomendas grandes, correspondendo a 27,0% e 52,5% do volume de cada unidade.")
p("A análise classificou o padrão de demanda pelo critério de Syntetos, Boylan e Croston (2005), que combina o "
  "intervalo médio entre vendas (⟨Average Demand Interval⟩ – ADI) e o quadrado do coeficiente de variação do "
  "tamanho das vendas (CV²), com pontos de corte em 1,32 e 0,49. Entre os produtos classificáveis, 99,3% "
  "apresentam demanda intermitente ou ⟨lumpy⟩, isto é, vendem em poucos dias, 13,4% venderam em um único dia, o "
  "produto típico vendeu em apenas 9 dos 789 dias analisados, e os 20 produtos de maior giro respondem por 61,7% do "
  "volume. Agregadas por unidade e categoria, as séries registram venda em 81% a 83% dos dias, com ADI de "
  "aproximadamente 1,2, e apresentam demanda errática, padrão adequado a modelos como o SARIMAX. Esse resultado "
  "definiu as séries do sistema: as quatro categorias de cada unidade e os produtos de grama com venda regular, sem "
  "previsão individual para os demais produtos.")
p("O padrão semanal é de dia útil, com pico entre terça e quinta-feira para Grama e para os produtos de jardinagem "
  "de Jardim Canadá e na sexta-feira para Flores de corte, menor movimento aos sábados e loja fechada aos domingos, "
  "o que levou aos indicadores de dia da semana e de loja fechada como variáveis exógenas. O efeito das datas "
  "comemorativas muda de sinal entre as categorias: no Dia das Mães, a venda de Flores de corte em Jardim Canadá "
  "sobe para 2,14 vezes a média, enquanto a da unidade como um todo cai para 0,66 vez a média, e, nas semanas do Dia "
  "da Mulher, do Dia das Mães, do Dia dos Namorados e do Natal, Flores de corte vende de 1,6 a 5,8 vezes uma semana "
  "comum, o que levou ao tratamento das datas em cada categoria.")
h2("11.5 Experimentos de Modelagem")
p("A configuração do modelo foi definida por experimentos executados em ⟨scripts⟩ Python separados da aplicação. "
  "Cada experimento partiu da melhor configuração disponível e alterou um único fator, mantendo a série, o período "
  "de teste e as métricas. Foram utilizados dois protocolos de validação " + WF + ": 26 janelas consecutivas de 14 "
  "dias, de março de 2025 a fevereiro de 2026, com a ordem do modelo escolhida apenas com os dados anteriores a 2 de "
  "março de 2025, e origens que avançam um dia por vez, cada uma prevendo os 14 dias seguintes, o que reproduz o uso "
  "diário do sistema. Em todos os casos, o modelo é ajustado apenas com os dados anteriores a cada origem, as "
  "métricas por categoria e por produto são calculadas nos dias de loja aberta, diferenças de erro inferiores a 5% "
  "são tratadas como empate e, quando os erros ficaram próximos, a significância foi verificada pelo teste de "
  "Diebold e Mariano (1995). O {qd:experimentos} resume os experimentos que definiram a configuração do sistema.")
tnew("experimentos", "qd", "Experimentos que definiram a configuração do sistema",
     ["Exp.", "Fator avaliado", "Série e protocolo", "Decisão para o sistema"],
     [["E1", "Variáveis exógenas", "Série total da rede, 26 janelas de 14 dias", "Indicadores de dia da semana, loja fechada e abertura excepcional, sem clima"],
      ["E2", "Critério de encomenda grande", "Vendas das duas unidades e treinamento das 17 séries então modeladas", "Limiar de cada loja igual à média mais quatro desvios-padrão dos pedidos"],
      ["E3", "Transformação logarítmica", "Itabirito: série total, fluxo diário e produtos, 351 origens diárias", "Previsão na escala original"],
      ["E4", "Nível de agregação", "Quatro categorias das duas unidades, 351 origens diárias", "Modelo próprio de cada categoria e total da loja pela soma"],
      ["E5", "Diferenciação", "23 séries com previsão, 52 treinamentos semanais", "d escolhido em cada série pela validação"],
      ["E6", "Fator das datas comemorativas", "Flores de corte e demais séries, 20 origens por ocorrência", "Metade do aumento em Flores de corte e queda inteira no fim do ano e no Dia do Trabalho"],
      ["E7", "Horizonte e retreinamento", "Oito categorias, 52 treinamentos semanais", "Previsão de 91 dias, validação em 14 dias e retreinamento semanal"],
      ["E8", "Janela de treinamento", "23 séries com previsão, 51 cortes semanais", "Janela de 545 dias em todas as séries"],
      ["E9", "Solução definitiva", "23 séries com previsão, 56 origens diárias", "Configuração final (Seção 6.5)"]],
     [700, 2000, 3072, 3300], F_AUT, "grade", ["center", "left", "left", "left"])
p("No experimento E1, ajustado à série total da rede, com venda média de cerca de 5 mil unidades por dia, as "
  "variáveis de calendário reduziram o MAE anual de 3.024 para 2.749 unidades, redução de 9%, elevaram de 19 para "
  "22 as janelas em que o modelo superou a previsão ingênua, reduziram o erro nos 14 feriados do ano de 3.988 "
  "unidades para praticamente zero e estreitaram o intervalo de 95% de 70,8 mil para 13,1 mil unidades "
  "({tab:e1}). As variáveis climáticas, mesmo com os valores observados, empataram ou pioraram o resultado, com "
  "efeitos não significativos, e a véspera e o dia seguinte a feriados, a primeira semana do mês e as janelas das "
  "datas comemorativas também não apresentaram efeito confiável na série total. As janelas antes do Dia das Mães e "
  "de Finados captavam, na verdade, a abertura excepcional da loja no próprio dia. Por isso, o modelo adotou apenas "
  "os indicadores de dia da semana, de loja fechada e de abertura excepcional, resultado coerente com o ganho dos "
  "regressores de calendário observado por Arunraj, Ahrens e Fernandes (2016).")
tcopy("e1", "tab", "Efeito das variáveis exógenas na série total da rede (E1)", "MAE nos 14 feriados", F_AUT,
      [("Sem exógenas (E1)", "Sem exógenas"), ("Calendário e clima (E2)", "Calendário e clima"), ("Calendário (E2)", "Calendário")])
p("Na série total de Itabirito, 18 dias, 5% do período de teste, concentravam 61,8% do erro do modelo e 50,6% do "
  "volume vendido, o que motivou a separação das encomendas grandes. O experimento E2 comparou critérios aplicados "
  "à venda inteira, com limiares fixos de 500 a 5.000 unidades e limiares próprios de cada unidade, iguais à média "
  "mais três ou quatro desvios-padrão da quantidade dos pedidos da loja, com o escore z modificado aplicado a cada "
  "linha (IGLEWICZ; HOAGLIN, 1993), medindo o volume classificado como encomenda, o coeficiente de variação do "
  "fluxo diário resultante e a parcela retirada da venda de balcão ({tab:e5}).")
tcopy("e5", "tab", "Sensibilidade do critério de encomenda grande (E2)", "Escore z modificado por linha",
      "Fonte: Elaborado pelos autores (2026). Volume: parcela do volume classificada como encomenda, CV: coeficiente de variação do fluxo diário, balcão: parcela do volume de consumidores sem cadastro retirada do fluxo.")
p("O critério por venda produziu um fluxo diário mais regular e retirou menos venda de balcão que o critério por "
  "linha, que removia mais de 21% do volume de consumidores das duas unidades. Entre os limiares fixos, 2.000 "
  "unidades foi o ponto de equilíbrio, mas trata igualmente lojas com pedidos de tamanhos diferentes. Com a média "
  "mais quatro desvios-padrão, o limiar é de 1.343 unidades em Jardim Canadá e de 1.960 em Itabirito, e, no "
  "treinamento das 17 séries então modeladas, errou menos que o limiar fixo em cinco séries, todas de Jardim "
  "Canadá, errou mais em duas e empatou nas outras dez, sem levar a cobertura para fora do intervalo de 90% a 98% "
  "nem o MASE para cima de 1. Com três desvios-padrão, a cobertura caiu abaixo de 90% em Grama e em Plantas diversas "
  "de Jardim Canadá, e o MASE passou de 1 em duas séries dessa unidade. Por isso, o sistema adotou a média mais "
  "quatro desvios-padrão, com a qual o coeficiente de variação da série diária caiu de 2,35 para 0,77 em Itabirito "
  f"e de 1,18 para 0,67 em Jardim Canadá.")
p(f"O experimento E3 isolou o efeito da transformação log(1{NB}+{NB}y), que estabiliza a variância das vendas, "
  f"mantendo a ordem do modelo, as variáveis exógenas e d{NB}={NB}1. No fluxo diário de Itabirito, o logaritmo "
  "reduziu o MAE em 8,4%, mas a previsão cobriu 89,6% do volume vendido, contra 101,1% na escala original "
  "({tab:e6}), e, na série total com as encomendas, cobriu apenas 46,1%, porque a previsão convertida de volta à "
  "escala original corresponde à mediana da distribuição prevista, e não à média (HYNDMAN; ATHANASOPOULOS, 2021). "
  "Nos produtos de venda regular de Itabirito, o logaritmo reduziu o MAE em 13%, mas a previsão cobriu 48% do volume "
  "vendido, e o erro no total dos 14 dias aumentou de 45,5% para 55,0%. Como a compra é planejada sobre o volume de "
  "vários dias, uma previsão que subestima sistematicamente esse volume não é adequada ao uso do sistema, e a "
  "solução adotou a escala original, na qual a previsão acompanha o volume vendido e o intervalo mantém cobertura "
  "próxima do nível nominal.")
tcopy("e6", "tab", "Transformação logarítmica e janela de treinamento em Itabirito (E3)", "Série total, escala original",
      "Fonte: Elaborado pelos autores (2026). Métricas de todos os dias e horizontes, MAE, RMSE e largura em unidades.")
p("O experimento E4 comparou, nas quatro categorias das duas unidades, o SARIMAX ajustado diretamente à série da "
  "categoria com a desagregação da previsão da loja pela participação da categoria nas oito semanas anteriores "
  "(GROSS; SOHL, 1990), ambos sobre o fluxo diário ({tab:e8}). O modelo direto obteve erro menor em 7 dos 8 pares, e "
  "a exceção, Plantas diversas em Jardim Canadá, teve diferença de 1,9%, abaixo do limite de empate. O maior ganho "
  "ocorreu em Flores de corte, com redução de 12% do erro em Itabirito e de 18% em Jardim Canadá, onde o intervalo da "
  "desagregação cobriu apenas 60,3% dos dias, porque o pico das datas comemorativas dessa categoria se anula no total "
  "da unidade. Para o total da loja, a soma das previsões das categorias teve o mesmo erro do modelo ajustado à série "
  "da loja, com um intervalo mais largo. Esses resultados definiram um modelo próprio para cada categoria e o total "
  "da loja pela soma das categorias.")
tcopy("e8", "tab", "Previsão direta da categoria e desagregação da previsão da loja (E4)", "Erro relativo (desag.)",
      "Fonte: Elaborado pelos autores (2026). Dias de loja aberta, desag.: desagregação, largura expressa em múltiplos da venda média diária.")
p("O experimento E5 avaliou a ordem de diferenciação nas 23 séries com previsão, em 52 treinamentos semanais de "
  "março de 2025 a fevereiro de 2026 ({tab:e9}). O teste de Kwiatkowski-Phillips-Schmidt-Shin (KPSS), cuja "
  "hipótese nula é a estacionariedade do nível (KWIATKOWSKI et al., 1992), aplicado ao resíduo da regressão das "
  "vendas nas variáveis exógenas, apontou nível não estacionário em oito séries, e d" + NB + "=" + NB + "1 errou "
  "menos em todas elas, mas não decidiu as séries esparsas, em que d" + NB + "=" + NB + "1 também errou menos em "
  "outras sete sem que o teste rejeitasse a estacionariedade. O teste de Dickey-Fuller aumentado (⟨Augmented "
  "Dickey-Fuller⟩ – ADF) rejeitou a raiz unitária em quase todas as janelas, distorção esperada em séries cuja "
  "diferença tem raiz de médias móveis próxima de −1 (SCHWERT, 1989). Escolher d pelo erro da validação " + WF +
  " da própria série reduziu o erro em 3,6% em relação a d" + NB + "=" + NB + "0 em todas as séries, perto do limite "
  "de quem escolhesse olhando o ano inteiro, de 3,9%, e por isso foi o critério adotado.")
tcopy("e9", "tab", "Critérios de escolha da diferenciação (E5)", "KPSS na janela de ajuste",
      "Fonte: Elaborado pelos autores (2026). 23 séries, treinamento semanal, erro diário dos 7 dias seguintes, de março de 2025 a fevereiro de 2026.")
p("O experimento E6 avaliou o fator das datas comemorativas, com a configuração de produção, em 20 origens por "
  "ocorrência ({tab:e10}). Sem ajuste, o modelo prevê uma semana comum de Flores de corte, com 40% a 46% do volume "
  "vendido na semana da data. Multiplicar a previsão por metade do aumento medido nas ocorrências anteriores reduziu "
  "o erro no total da semana de 61% para 33% em Jardim Canadá e de 54% para 32% em Itabirito, com melhora nas 10 "
  "ocorrências testadas, enquanto o fator inteiro errou para cima de 87% a 159% em Itabirito, e o erro de cada dia "
  "quase não mudou. Nas demais séries, o modelo previu de duas a cinco vezes o vendido entre 26 e 31 de dezembro, e a "
  "aplicação da queda inteira reduziu o erro da semana em todas as ocorrências testadas, como na Grama de Itabirito, "
  "de 268% para 27%. Em Finados, o fator não trouxe ganho consistente e não foi adotado.")
tcopy("e10", "tab", "Fator das datas comemorativas em Flores de corte (E6)", "Previsto / vendido na semana da data",
      "Fonte: Elaborado pelos autores (2026). Dias de loja aberta da semana da data, cinco ocorrências por unidade.")
p("O experimento E7 mediu quanto a previsão piora com a distância do treinamento e com a frequência de "
  "retreinamento, nas oito categorias, em 52 treinamentos semanais ({tab:e11}). O erro de cada dia cresceu pouco "
  "com o horizonte, e a cobertura do intervalo de 95% manteve-se entre 92% e 93% em todas as semanas. Retreinar a "
  "cada quatro semanas errou 2% a mais que retreinar toda semana, na média do ano, e 15% a mais no pior mês, e "
  "retreinar a cada 13 semanas errou 3% a mais na média e 32% a mais no pior mês, em viradas de temporada como "
  "janeiro e novembro. Por isso, o sistema grava a previsão de 91 dias, mantém a validação em 14 dias e é "
  "retreinado a cada planilha semanal.")
tcopy("e11", "tab", "Erro e cobertura por semana do horizonte (E7)", "Semana do horizonte",
      "Fonte: Elaborado pelos autores (2026). Oito categorias, mesmos dias-alvo em todas as semanas, dias de loja aberta.")
p("O experimento E8 avaliou a janela de treinamento nas 23 séries com previsão, em 51 cortes semanais de março de "
  "2025 a fevereiro de 2026, trocando apenas a janela, de 90, 180, 270, 365 ou 545 dias ou o histórico inteiro, com "
  "o teste de Diebold e Mariano (1995) e o ajuste de Holm (1979) para as 23 séries ({tab:e12}). A janela de 90 dias "
  "errou 8,6% a mais que a de 365 dias nas categorias, e a de 545 dias foi a melhor janela única, com erro 1,9% "
  "menor nas 23 séries e nas categorias e o maior ganho em Flores de corte, de 3,8% em Jardim Canadá e de 6,2% em "
  "Itabirito, pois o modelo observa cada data comemorativa mais de uma vez. Escolher a janela em cada série "
  "reduziria mais o erro dos produtos de grama de baixo volume, mas tornaria o treinamento cerca de seis vezes mais "
  "lento, e o sistema adotou 545 dias em todas as séries. No mesmo experimento, quatro produtos de grama de pouco "
  "volume de Jardim Canadá erraram mais que a previsão ingênua já nas duas primeiras semanas, e a tela de previsão "
  "indica, para eles, que os números servem como referência, junto com a experiência da loja.")
tcopy("e12", "tab", "Variação do erro em relação à janela de 365 dias (E8)", "Média das 8 categorias",
      "Fonte: Elaborado pelos autores (2026). MAE dos 14 dias seguintes a cada corte, dias de loja aberta, 51 cortes semanais de março de 2025 a fevereiro de 2026, médias geométricas das razões ao MAE da janela de 365 dias.")
h2("11.6 Validação da Solução Definitiva")
cp("A solução definitiva foi avaliada pelo próprio treinamento do sistema",
   ("(experimento E13)", "(experimento E9)"), ("A Tabela 12 apresenta", "A {tab:e13} apresenta"))
tcopy("e13", "tab", "Desempenho da solução definitiva por série (E9)", "JC, Capim dos Texas verde",
      "Fonte: Elaborado pelos autores (2026). ITA: Itabirito, JC: Jardim Canadá. Dias de loja aberta, janelas vencidas de 56, ordem (p,d,q)(P,0,Q) com m = 7.")
cp("Nas oito categorias, o MASE ficou abaixo de 1")
p("O teste de Ljung-Box não rejeitou a ausência de autocorrelação residual em 22 das 23 séries, o que indica que os "
  "modelos capturaram a dependência entre os dias e o padrão semanal das vendas, e o teste de Shapiro-Wilk rejeitou "
  "a normalidade dos resíduos em todas elas, comportamento esperado em vendas com dias de pico. Por isso, a "
  "cobertura dos intervalos é verificada empiricamente na validação, e as coberturas obtidas, entre 90,5% e 100,0%, "
  "ficaram próximas ou acima do nível nominal de 95%.")
cp("Em todas as categorias, o volume previsto superou o vendido",
   ("visível também no faturamento mensal da Figura 7", "visível também no faturamento mensal da {fig:inicio}"),
   ("(E9)", "(E5)"))
p("Nos produtos de grama de menor volume, de padrão intermitente, o MASE e o erro relativo à previsão ingênua "
  "divergiram, como no Capim dos Texas roxo (1293) de Jardim Canadá, com MASE de 2,236 e erro 43% menor que o da "
  "previsão ingênua. A escala do MASE vem do erro da previsão ingênua no período de treinamento e não reflete "
  "mudanças de nível entre o treinamento e a validação, de modo que, nessas séries, o erro relativo na própria "
  "janela de teste e a razão entre o previsto e o vendido descrevem melhor o desempenho, e a literatura recomenda "
  "métodos específicos de demanda intermitente (Seção 5.3).")
h2("11.7 Comparação com os Objetivos")
p("O {qd:objetivos} retoma os objetivos específicos do Capítulo 4 e indica em que medida cada um foi alcançado.")
tnew("objetivos", "qd", "Alcance dos objetivos específicos",
     ["Objetivo específico", "Situação", "Evidência"],
     [["a) Requisitos levantados e validados", "Alcançado", "Oito reuniões com a entidade, 12 requisitos funcionais, 5 não funcionais e 8 regras de negócio"],
      ["b) Arquitetura e modelagem definidas", "Alcançado", "Diagramas de casos de uso, atividades, classes e sequência, DER e arquitetura (Capítulo 8)"],
      ["c) ⟨Pipeline⟩ de dados estruturado", "Alcançado", "26 planilhas e 351.092 registros carregados sem duplicatas, com a mesma rotina na importação semanal"],
      ["d) Análise exploratória realizada", "Alcançado", "Padrão de demanda dos produtos, sazonalidade de dia útil e efeito das datas por categoria (Seção 11.4)"],
      ["e) Calendário e datas comemorativas tratados", "Alcançado", "Erro nos feriados próximo de zero e redução do erro da semana das datas em Flores de corte (E1 e E6)"],
      ["f) Modelos treinados", "Alcançado", "23 séries com previsão, ordem pelo AIC e diferenciação escolhida pela validação"],
      ["g) Configurações comparadas", "Alcançado", "Experimentos E1 a E8, que definiram a configuração (Seção 11.5)"],
      ["h) Desempenho avaliado", "Alcançado", "MASE abaixo de 1 em 19 das 23 séries e cobertura do intervalo entre 90,5% e 100% (Seção 11.6)"],
      ["i) API, serviço de previsão e painel implementados", "Alcançado", "Cinco telas em operação com os dados reais (Seção 10.2)"],
      ["j) Software validado", "Alcançado", "Testes automatizados aprovados e aprovação da empresa nas reuniões, sem teste formal de usabilidade"],
      ["k) Documentação produzida", "Parcialmente alcançado", "Documentação técnica no repositório, sem manual do usuário"]],
     [3000, 1700, 4372], F_AUT, "grade", ["left", "center", "left"])
p("O objetivo geral, desenvolver um sistema que forneça a previsão diária da demanda de cada categoria e de cada "
  "produto de grama das unidades da empresa, foi alcançado: o sistema gera, a cada treinamento, a previsão dos 91 "
  "dias seguintes de 23 séries, das quais as oito categorias erram menos que a previsão ingênua na validação, e a "
  "apresenta à empresa em um painel acessível a usuários não técnicos.")
h2("11.8 Discussão dos Resultados")
p("As escolhas de modelagem com maior efeito medido foram as variáveis de calendário, que eliminaram o erro nos "
  "feriados e estreitaram o intervalo de 95% da série total de 70,8 mil para 13,1 mil unidades, a separação das "
  "encomendas grandes, que tornou o fluxo diário mais regular, e a modelagem direta das categorias, que superou a "
  "desagregação em 7 de 8 pares, sobretudo em Flores de corte. Outras escolhas foram decididas por critérios além do "
  "erro diário: a transformação logarítmica, que reduziu o MAE, foi descartada por subestimar o volume vendido, e o "
  "fator das datas comemorativas corrige o volume da semana da data, mas não o dia do pico.")
cp("Os resultados da solução definitiva não são diretamente comparáveis")
cp("A principal limitação está nas encomendas grandes", ("experimento E11", "experimento E7"))
p("Do ponto de vista do software, os resultados positivos são a operação do sistema com os dados reais, a "
  "conferência das planilhas antes da gravação, que evita tratar semanas não enviadas como vendas nulas, e a "
  "rastreabilidade de cada carga e de cada treinamento. Permanecem como dificuldades a dependência da extração "
  "manual dos relatórios, que mantém a base com vendas até fevereiro de 2026, o treinamento fora da API publicada, "
  "que exige um ⟨script⟩ executado pela equipe técnica enquanto o serviço de hospedagem for o plano gratuito, e o "
  "defeito de duplicidade dentro da mesma planilha. As melhorias possíveis estão listadas como trabalhos futuros no "
  "Capítulo 12.")

