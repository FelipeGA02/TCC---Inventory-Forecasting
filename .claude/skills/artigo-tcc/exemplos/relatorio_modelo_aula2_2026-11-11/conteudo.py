# -*- coding: utf-8 -*-
"""Conteúdo do relatório no modelo da Aula 2 (Partes do Relatório Técnico)."""
import os

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(S, "img")
MED = os.path.join(S, "base", "work", "word", "media")
NB = " "
F_AUT = "Fonte: Elaborado pelos autores (2026)."
F_ENT = "Fonte: Elaborado pelos autores com base em reuniões com a entidade parceira (2026)."
F_TELA = "Fonte: Elaborado pelos autores (2026), a partir do sistema em execução com a base de vendas da entidade parceira."
WF = "⟨walk-forward⟩"

PRE_REPLACE = [
    ("o MASE ficou abaixo de 1 em 17 das 23 séries", "o MASE ficou abaixo de 1 em 19 das 23 séries"),
    ("the MASE remained below 1 in 17 of the 23", "the MASE remained below 1 in 19 of the 23"),
]
SIGLAS_NOVAS = [
    ("CSV", "Comma-Separated Values", "valores separados por vírgula"),
    ("DER", "", "Diagrama Entidade-Relacionamento"),
    ("ERP", "Enterprise Resource Planning", "sistema integrado de gestão empresarial"),
    ("HTTP", "Hypertext Transfer Protocol", "protocolo de transferência de hipertexto"),
    ("JSON", "JavaScript Object Notation", "notação de objetos JavaScript"),
]

B = []
h1 = lambda s: B.append(("h1", s))
h2 = lambda s: B.append(("h2", s))
h3 = lambda s: B.append(("h3", s))
p = lambda s: B.append(("p", s))
ul = lambda *items: B.append(("ul", list(items)))
cp = lambda prefix, *reps: B.append(("copy", prefix, list(reps)))


def fig(key, path, width, title, source=F_AUT, maxh=20.0):
    B.append(("fig", key, path, width, title, source, maxh))


def tnew(key, kind, title, header, rows, widths, source=F_AUT, style=None, align=None):
    style = style or ("grade" if kind == "qd" else "aberta")
    B.append(("table_new", key, kind, title, header, rows, widths, style, align, source))


def tcopy(key, kind, title, contains, source=F_AUT, fix=None):
    B.append(("table_copy", key, kind, title, contains, fix, source))


# =====================================================================================
h1("1 INTRODUÇÃO")
cp("A previsão de demanda pode apoiar o planejamento de compras")
p("A Floricultura Verde Perto atua no varejo de flores, plantas, grama e produtos de jardinagem, com duas "
  "unidades operacionais, uma em Jardim Canadá, no município de Nova Lima, e outra em Itabirito, em Minas "
  "Gerais. O planejamento das compras é feito com base na experiência da equipe e em relatórios extraídos do "
  "sistema de gestão da empresa, que registram as vendas realizadas, mas não estimam as vendas futuras. A "
  "procura varia com o dia da semana, com a época do ano e com datas comemorativas, como o Dia das Mães, o Dia "
  "dos Namorados e o Dia Internacional da Mulher, e difere entre os produtos e entre as unidades, o que "
  "dificulta definir as quantidades a adquirir de produtos que perdem valor em poucos dias.")
p("Para atender a essa necessidade, foi desenvolvido um sistema de previsão de vendas que utiliza o histórico de "
  "vendas da empresa e o calendário de cada unidade para estimar quanto se espera vender em cada dia das "
  "semanas seguintes, em cada uma das quatro categorias de produto e em cada produto de grama das duas "
  "unidades. A gestora de compras envia as planilhas de vendas exportadas do sistema de gestão, confere-as "
  "antes da gravação e solicita o treinamento dos modelos, e o sistema apresenta, em um painel acessível pelo "
  "navegador, a previsão diária com uma faixa provável de venda, o histórico das previsões comparado às vendas "
  "realizadas, análises das vendas e relatórios exportáveis. O sistema informa quanto se espera vender, e a "
  "decisão de compra permanece com a empresa.")
p("O objetivo geral do trabalho é desenvolver esse sistema, e os objetivos específicos abrangem o levantamento "
  "dos requisitos com a entidade parceira, a modelagem do sistema, a preparação dos dados, a construção e a "
  "avaliação dos modelos de previsão e a implementação do painel. A solução se justifica pela perecibilidade "
  "dos produtos, que torna custosos tanto o excesso quanto a falta de estoque, e pela existência de um histórico "
  "de 26 meses de vendas, de janeiro de 2024 a fevereiro de 2026, até então utilizado apenas para consulta. O "
  "desenvolvimento seguiu uma metodologia iterativa e incremental, com validação junto à entidade parceira em "
  "oito reuniões, e a análise dos dados seguiu as fases do modelo CRISP-DM, da compreensão do negócio à "
  "implantação. Os modelos utilizados são modelos estatísticos de séries temporais, que aprendem com as vendas "
  "passadas e com o calendário de cada loja, e a sua qualidade é medida comparando as previsões com vendas que o "
  "modelo não conhecia no momento em que previu.")
p("O trabalho está organizado em doze capítulos. O Capítulo 2 apresenta a problematização, com a situação atual "
  "e a situação desejada, e o Capítulo 3, a justificativa. O Capítulo 4 apresenta os objetivos geral e "
  "específicos, e o Capítulo 5, o referencial teórico e as soluções correlatas. O Capítulo 6 descreve as "
  "metodologias adotadas, e o Capítulo 7, a análise de requisitos. O Capítulo 8 apresenta a modelagem do "
  "sistema, o Capítulo 9, a prototipação, e o Capítulo 10, a implementação. O Capítulo 11 apresenta e discute "
  "os resultados, inclusive os dos testes e dos experimentos realizados, e o Capítulo 12 traz a conclusão e os "
  "trabalhos futuros. Os apêndices reúnem as atas das reuniões com a entidade parceira, a especificação dos "
  "casos de uso e o dicionário dos dados de vendas, e o anexo apresenta telas do sistema de gestão da empresa.")

# =====================================================================================
h1("2 PROBLEMATIZAÇÃO")
p("Este capítulo descreve a necessidade que motivou o desenvolvimento do sistema, a partir da situação "
  "encontrada na Floricultura Verde Perto e da situação que a empresa deseja alcançar.")
h2("2.1 Situação Atual")
p("As vendas das duas unidades são registradas no sistema integrado de gestão (⟨Enterprise Resource "
  "Planning⟩ – ERP) da empresa, que emite relatórios, como o de contas a receber, mas não estima a demanda "
  "futura nem oferece uma interface de integração com outros sistemas (Anexo A). Para analisar as vendas, a "
  "equipe administrativa exporta esses relatórios em planilhas, organizadas em blocos por documento de venda, "
  "que precisam ser reunidas e organizadas manualmente a cada consulta. A extração é demorada e depende do "
  "computador do setor financeiro, e o relatório exportado não informa o grupo de cada produto, de modo que "
  "somar as vendas por categoria exige classificar os produtos pela descrição.")
p("O planejamento das compras depende, assim, do conhecimento prático da equipe. A reposição de grama e de "
  "flores leva cerca de uma semana, e a decisão de quanto comprar é tomada sem uma estimativa quantitativa das "
  "vendas dos dias seguintes. O catálogo é extenso, com milhares de produtos, mas o volume vendido se concentra "
  "em poucos itens, sobretudo nas gramas, enquanto a maioria dos produtos vende de forma esporádica. As datas "
  "comemorativas afetam as categorias de forma desigual: a venda de flores de corte cresce nas semanas de datas "
  "como o Dia da Mulher, o Dia das Mães e o Dia dos Namorados, enquanto as demais categorias vendem menos no fim "
  "do ano. Acompanhar essas variações apenas pela experiência é difícil, sobretudo em duas unidades com perfis "
  "de venda distintos.")
p("Os impactos dessa situação recaem sobre o estoque de produtos perecíveis. Quando a compra supera a venda, "
  "flores e plantas ficam sujeitas a perda, e, quando fica abaixo, a loja deixa de atender os clientes. O "
  "histórico de vendas, embora disponível, não é utilizado de forma sistemática para orientar as compras, a "
  "equipe gasta tempo organizando planilhas sem obter delas uma estimativa do que será vendido e não há registro "
  "que permita verificar, depois, se as estimativas feitas estavam corretas.")
p("O problema, portanto, é a ausência de um meio de transformar os dados históricos de vendas em estimativas "
  "quantitativas e antecipadas da demanda, capazes de apoiar a decisão de compra. Assim, este trabalho buscou "
  "responder à seguinte questão: como utilizar os dados históricos de vendas de uma floricultura para gerar, de "
  "forma sistemática e antecipada, previsões de demanda diária que apoiem o planejamento de compras?")
h2("2.2 Situação Desejada")
p("Na situação desejada, a empresa poderá consultar, antes de cada compra, uma estimativa das vendas de cada dia "
  "das semanas seguintes, para cada categoria de produto e para cada produto de grama de cada unidade, "
  "acompanhada de uma faixa provável que indique a incerteza da estimativa. As vendas poderão ser enviadas "
  "semanalmente, na forma das planilhas que a empresa já exporta, sem exigir conhecimento técnico, e as "
  "estimativas poderão ser atualizadas a cada nova carga de dados. A empresa poderá ainda comparar o que foi "
  "previsto com o que foi vendido, para saber o quanto confiar nas estimativas, e consultar as vendas por "
  "período, categoria, produto e unidade, com acesso restrito conforme o perfil de cada usuário.")
p("Nessa situação, a equipe poderá responder com dados a questões operacionais como:")
ul("quanto se espera vender de cada categoria, em cada unidade, em cada dia das próximas semanas,",
   "quanto se espera vender de cada produto de grama, que a empresa compra produto a produto,",
   "quais feriados e datas comemorativas alteram as vendas do período e em que direção,",
   "quanto as estimativas anteriores erraram em relação às vendas realizadas.")

# =====================================================================================
h1("3 JUSTIFICATIVA")
p("A importância do trabalho decorre do efeito das decisões de compra sobre produtos perecíveis. Na "
  "floricultura, flores e plantas têm vida útil curta e demanda sujeita a datas comemorativas, e a compra acima "
  "ou abaixo da demanda resulta em descarte ou em vendas perdidas. Ao transformar o histórico de vendas em "
  "previsões diárias, acompanhadas de medidas de incerteza e de desempenho, o sistema oferece à empresa uma base "
  "quantitativa para a compra, que até então dependia apenas da experiência da equipe. Para os autores, o "
  "trabalho representou a oportunidade de aplicar a um problema real os conhecimentos de engenharia de "
  "software, de banco de dados e de ciência de dados adquiridos no curso.")
p("Do ponto de vista técnico e acadêmico, a principal contribuição é a aplicação de modelos estatísticos de "
  "séries temporais com regressores exógenos, isto é, com variáveis externas que ajudam a explicar as vendas, à "
  "previsão de demanda no setor de floricultura. Os estudos que fundamentam essa abordagem concentram-se no "
  "varejo de alimentos perecíveis (ARUNRAJ; AHRENS; FERNANDES, 2016; HUBER; GOSSMANN; STUCKENSCHMIDT, 2017), "
  "enquanto a floricultura, que compartilha com esse varejo a alta perecibilidade e a forte influência de datas "
  "comemorativas, é um setor pouco explorado nesse tipo de aplicação. A escolha de um modelo estatístico como "
  "modelo central é sustentada pelos resultados da competição M4, em que métodos estatísticos superaram, em "
  "média, abordagens puramente baseadas em aprendizado de máquina, sobretudo em séries com histórico reduzido "
  "(MAKRIDAKIS; SPILIOTIS; ASSIMAKOPOULOS, 2020), como os 26 meses disponíveis neste projeto.")
p("Do ponto de vista administrativo, o sistema reúne em uma base única as vendas das três empresas do grupo, "
  "consolidadas nas duas unidades operacionais, elimina a consolidação manual das planilhas, registra cada carga "
  "de dados e cada treinamento dos modelos e preserva as previsões feitas para cada dia, o que permite avaliar a "
  "qualidade das estimativas ao longo do tempo. A solução também foi concebida em conformidade com a Lei Geral de "
  "Proteção de Dados Pessoais (LGPD) (BRASIL, 2018): os relatórios de vendas contêm dados pessoais de clientes, "
  "sem valor para a previsão, que não são armazenados pelo sistema.")
p("A viabilidade do desenvolvimento apoiou-se na disponibilidade dos dados, na participação da entidade parceira "
  "e em ferramentas de uso livre. A empresa forneceu o histórico de vendas das duas unidades e participou de "
  "oito reuniões, nas quais definiu requisitos, esclareceu as regras do negócio e avaliou o protótipo e as "
  "versões do sistema. As bibliotecas de modelagem estatística, os ⟨frameworks⟩ de desenvolvimento ⟨web⟩ e os "
  "bancos de dados utilizados são de código aberto ou oferecem planos gratuitos, o que permitiu construir a "
  "solução sem custo de licenciamento.")
p("A solução é oportuna porque a empresa já mantinha o histórico de vendas no seu sistema de gestão, mas não "
  "dispunha de meios para utilizá-lo no planejamento, e manifestou, desde a primeira reunião, o interesse em uma "
  "ferramenta que considerasse as datas comemorativas e fosse atualizada semanalmente. A previsão por produto de "
  "grama atende à forma como a empresa compra esses itens, e a apresentação das encomendas grandes em separado "
  "corresponde à prática da empresa de preparar esses pedidos com antecedência junto aos fornecedores. Para a "
  "empresa e para os seus clientes, a contribuição social está na redução do desperdício de produtos perecíveis "
  "e na maior disponibilidade dos produtos procurados.")
p("Por esses motivos, um sistema de previsão integrado ao fluxo de trabalho da empresa, que reúne a carga das "
  "planilhas, o treinamento dos modelos e a consulta das previsões em um mesmo ambiente, foi considerado a "
  "solução mais adequada, em lugar de análises pontuais em planilhas ou de bibliotecas genéricas de previsão, que "
  "exigiriam conhecimento técnico da equipe e não incorporariam o calendário de cada unidade.")

# =====================================================================================
h1("4 OBJETIVOS")
p("Este capítulo apresenta o objetivo geral do trabalho e os objetivos específicos que o tornaram operacional.")
h2("4.1 Objetivo Geral")
p("Desenvolver um sistema de previsão de vendas para a Floricultura Verde Perto, baseado em dados históricos e "
  "em modelos estatísticos de séries temporais com regressores exógenos de calendário, que forneça a previsão "
  "diária da demanda de cada categoria de produto e de cada produto de grama das unidades da empresa, de modo a "
  "apoiar as decisões de compra.")
h2("4.2 Objetivos Específicos")
p("Os objetivos específicos, desdobramentos do objetivo geral, são apresentados pelas etapas cumpridas para "
  "alcançá-lo:")
ul("levantados e validados, junto à entidade parceira, os requisitos funcionais e não funcionais, as regras de "
   "negócio e os atores do sistema,",
   "definidas a arquitetura e a modelagem do sistema, em diagramas UML, modelo de dados e arquitetura lógica,",
   "estruturado o ⟨pipeline⟩ que leva as planilhas de vendas até a base de dados, com deduplicação, "
   "padronização, classificação dos produtos em categorias e separação das encomendas grandes,",
   "realizada a análise exploratória dos dados históricos, identificados a sazonalidade, o padrão de demanda dos "
   "produtos e o comportamento de cada unidade,",
   "construído o calendário diário de cada unidade, com dias de loja fechada e aberturas excepcionais, e "
   "tratado o efeito das datas comemorativas na previsão,",
   "treinados modelos estatísticos de séries temporais com regressores exógenos para cada categoria e para cada "
   "produto de grama de cada unidade, com seleção automática da ordem pelo Critério de Informação de Akaike "
   "(AIC) e escolha da diferenciação pela validação,",
   "comparadas experimentalmente configurações de modelagem, como as variáveis exógenas, o tratamento das "
   "encomendas grandes, o nível de agregação, a diferenciação, a janela de treinamento e o horizonte de previsão,",
   "avaliado o desempenho dos modelos por validação " + WF + ", com métricas de erro, com o erro relativo à "
   "previsão ingênua e com a cobertura e a largura do intervalo de 95%,",
   "implementados a interface de programação, o serviço de previsão e o painel interativo, com envio e "
   "conferência de planilhas, treinamento sob demanda, previsão, histórico das previsões, análises de vendas e "
   "relatórios,",
   "validado o software por testes automatizados e por demonstrações à entidade parceira,",
   "produzida a documentação técnica da solução.")

# =====================================================================================
h1("5 REFERENCIAL TEÓRICO")
p("Este capítulo apresenta, nas Seções 5.1 a 5.7, a fundamentação teórica sobre o problema e sobre a solução "
  "e, na Seção 5.8, as soluções correlatas, com a diferença entre elas e a solução desenvolvida.")
h2("5.1 Previsão de demanda e modelos estatísticos de séries temporais")
cp("A previsão de demanda é tema consolidado na análise de séries temporais")
cp("Entre os modelos estatísticos de séries temporais, destacam-se")
cp("Uma decisão de especificação particularmente relevante para séries diárias")
cp("A adequação dessa categoria de modelos ao varejo perecível")
cp("Para séries com histórico reduzido, Makridakis, Spiliotis e Assimakopoulos (2020)")
h2("5.2 Variáveis exógenas de calendário")
cp("As variáveis exógenas de um modelo de previsão precisam ter valores conhecidos",
   ("o que orienta a seleção de variáveis feita neste trabalho", "o que orienta a seleção das variáveis do modelo"))
h2("5.3 Demanda intermitente")
cp("A demanda é intermitente quando a maior parte dos períodos não registra venda")
h2("5.4 Previsão hierárquica e nível de agregação")
cp("Quando as séries individuais são esparsas, a previsão hierárquica organiza")
h2("5.5 Tratamento de observações atípicas")
cp("Observações atípicas distorcem a estimação dos parâmetros")
h2("5.6 Métricas de avaliação de previsões")
cp("Para a avaliação de previsões, Hyndman e Koehler (2006) propuseram")
cp("Para verificar se a diferença de erro entre duas previsões da mesma série")
h2("5.7 Processo de desenvolvimento de software e de análise de dados")
p("A engenharia de software organiza o desenvolvimento em atividades de especificação, projeto, implementação, "
  "validação e evolução, que podem ser conduzidas de forma sequencial ou iterativa (SOMMERVILLE, 2018). Nos "
  "modelos iterativos e incrementais, o sistema é entregue em partes funcionais, avaliadas pelo cliente a cada "
  "ciclo, o que favorece os projetos cujos requisitos se tornam mais precisos à medida que o cliente conhece o "
  "produto (PRESSMAN; MAXIM, 2021). A separação entre a lógica de domínio e os mecanismos de entrada e saída "
  "favorece os testes isolados e a manutenção do código, e a definição da estratégia de validação desde o projeto "
  "é determinante para a qualidade da entrega (SOMMERVILLE, 2018; PRESSMAN; MAXIM, 2021).")
p("Em projetos de análise de dados, o modelo ⟨Cross-Industry Standard Process for Data Mining⟩ (CRISP-DM) "
  "organiza o trabalho em seis fases, compreensão do negócio, compreensão dos dados, preparação dos dados, "
  "modelagem, avaliação e implantação, percorridas de forma cíclica, de modo que os resultados da avaliação podem "
  "levar de volta à preparação dos dados ou à compreensão do negócio (WIRTH; HIPP, 2000).")
h2("5.8 Soluções correlatas")
p("Entre as soluções desenvolvidas para a previsão de demanda de produtos perecíveis, Arunraj, Ahrens e Fernandes "
  "(2016) aplicaram um modelo sazonal autorregressivo integrado de médias móveis com regressores exógenos à "
  "previsão das vendas diárias no varejo de alimentos e mostraram que as variáveis de calendário e de promoção "
  "reduzem o erro em relação ao modelo sem regressores. Huber, Gossmann e Stuckenschmidt (2017) trataram a "
  "previsão da demanda de produtos perecíveis com previsão hierárquica, agrupando os itens e prevendo em níveis "
  "agregados as séries de venda esparsa.")
p("Entre as ferramentas disponíveis no mercado, a biblioteca Prophet, de código aberto, ajusta modelos aditivos "
  "com tendência, sazonalidades e efeitos de feriados informados pelo usuário e foi concebida para que analistas "
  "sem formação específica em séries temporais produzam previsões em escala (TAYLOR; LETHAM, 2018). Trata-se, "
  "porém, de uma biblioteca de programação, que exige preparar os dados, configurar o calendário e manter o "
  "código. O sistema de gestão utilizado pela entidade parceira, por sua vez, registra as vendas e emite "
  "relatórios, mas não estima a demanda futura (Seção 2.1). O {qd:correlatas} compara essas soluções com a "
  "desenvolvida neste trabalho.")
tnew("correlatas", "qd", "Soluções correlatas e solução desenvolvida",
     ["Solução", "Abordagem", "Limitação para o problema da entidade"],
     [["Arunraj, Ahrens e Fernandes (2016)", "Modelo sazonal com regressores de calendário e promoção, vendas diárias do varejo de alimentos", "Estudo de método, sem ferramenta para a carga dos dados e a consulta pela empresa"],
      ["Huber, Gossmann e Stuckenschmidt (2017)", "Previsão hierárquica de produtos perecíveis, com agrupamento dos itens", "Estudo de método, sem ferramenta para a carga dos dados e a consulta pela empresa"],
      ["Prophet (TAYLOR; LETHAM, 2018)", "Modelo aditivo com tendência, sazonalidades e feriados", "Biblioteca de programação, que exige preparo dos dados e manutenção do código"],
      ["Sistema de gestão da entidade", "Registro das vendas e emissão de relatórios", "Não estima as vendas futuras"],
      ["Solução desenvolvida", "Modelo estatístico com regressores de calendário por categoria e por produto de grama de cada loja, encomendas grandes à parte e ajuste das datas comemorativas", "Sistema ⟨web⟩ com carga semanal das planilhas, validação a cada treinamento e histórico das previsões"]],
     [2400, 3400, 3272])
p("A solução desenvolvida diferencia-se dessas abordagens por reunir, em um sistema de uso da própria empresa, a "
  "carga das planilhas que ela já exporta, o treinamento dos modelos a cada nova carga, com a validação "
  "registrada em cada série, e a consulta das previsões por usuários não técnicos. Quanto ao método, combina o "
  "modelo estatístico com regressores de calendário, aplicado diretamente às séries de categoria e de produto de "
  "grama, com o tratamento separado das encomendas grandes e com um ajuste das datas comemorativas próprio da "
  "floricultura, e preserva o histórico das previsões para que a empresa acompanhe o erro com a antecedência com "
  "que planeja a compra.")

# =====================================================================================
h1("6 METODOLOGIAS ADOTADAS")
p("Este capítulo descreve como a solução foi planejada, desenvolvida, testada e validada: a metodologia de "
  "desenvolvimento, o levantamento dos requisitos, as ferramentas e tecnologias, as ferramentas de modelagem, a "
  "preparação dos dados e o modelo preditivo e os procedimentos de testes e validação. Os resultados dos testes "
  "e dos experimentos são apresentados no Capítulo 11.")
h2("6.1 Metodologia de Desenvolvimento Adotada")
p("Foi adotada uma metodologia híbrida, iterativa e incremental, que combina práticas ágeis com o planejamento "
  "por fases. O sistema foi entregue em partes funcionais, como o envio de planilhas, o painel de análises e o "
  "serviço de previsão, e cada parte evoluiu por ciclos de refinamento, com definição das histórias de usuário, "
  "implementação, testes e validação com a entidade parceira nas reuniões. A especificação funcional, o plano "
  "técnico e a lista de tarefas de cada fase foram mantidos no repositório do projeto, e cada mudança do código "
  "foi integrada à versão principal por solicitações de integração (⟨pull requests⟩) revisadas antes da "
  "incorporação.")
p("A análise dos dados e a modelagem preditiva seguiram o modelo CRISP-DM (WIRTH; HIPP, 2000), adaptado ao "
  "contexto de séries temporais, com as fases de compreensão do negócio, compreensão dos dados, preparação dos "
  "dados, modelagem, avaliação e implantação. A {fig:etapas} apresenta as etapas da metodologia.")
fig("etapas", os.path.join(MED, "image2.png"), 15.0, "Etapas da metodologia")
cp("O projeto foi organizado em oito iterações, distribuídas entre abril e novembro de 2026",
   ("conforme o Quadro 1", "conforme o {qd:iter}"),
   ("como ocorreu com o tratamento das encomendas grandes, definido a partir do erro observado na unidade de Itabirito (Seção 7)",
    "como ocorreu com o tratamento das encomendas grandes"))
tcopy("iter", "qd", "Iterações do projeto segundo as fases do CRISP-DM", "Backlog de requisitos consolidado")
h2("6.2 Levantamento e Análise de Requisitos")
p("Os requisitos foram levantados em oito reuniões com a entidade parceira, realizadas entre março e novembro de "
  "2026, de forma remota, pela plataforma Google Meet. Cada reunião foi registrada no Formulário de Registro de "
  "Reuniões com Entidade fornecido pela instituição, com a pauta, as decisões tomadas, os requisitos e as "
  "solicitações do cliente, as pendências e a validação do representante da empresa. As atas estão no "
  "Apêndice A.")
p("Participaram das reuniões as duas sócias administrativas proprietárias da empresa, um auxiliar "
  "administrativo e os dois desenvolvedores da solução. As duas primeiras reuniões levantaram as necessidades do "
  "negócio, a origem dos dados e o horizonte de previsão desejado. As seguintes apresentaram o protótipo das "
  "telas, os resultados preliminares do modelo e as versões do sistema em desenvolvimento, e, a partir delas, os "
  "requisitos foram revistos e validados pela empresa.")
p("O levantamento foi complementado pela análise documental dos relatórios de vendas exportados do sistema de "
  "gestão, pela observação das telas desse sistema, compartilhadas pela empresa em reunião (Anexo A), e pela "
  "inspeção das planilhas de janeiro de 2024 a fevereiro de 2026. Os requisitos registrados nas atas foram "
  "consolidados em requisitos funcionais, requisitos não funcionais, regras de negócio e atores, priorizados "
  "conforme o impacto operacional discutido nas reuniões e apresentados no Capítulo 7.")
h2("6.3 Ferramentas e Tecnologias Utilizadas")
p("A solução foi desenvolvida com o seguinte conjunto de ferramentas e tecnologias:")
ul("linguagens de programação: Python, na versão 3.14 utilizada na imagem de publicação da API, no ⟨backend⟩, no "
   "⟨pipeline⟩ de dados e na modelagem, e ⟨TypeScript⟩, no painel,",
   "⟨frameworks⟩ e bibliotecas do ⟨backend⟩: ⟨FastAPI⟩, para a interface de programação de aplicações "
   "(⟨Application Programming Interface⟩ – API), ⟨SQLAlchemy⟩, para o acesso ao banco de dados, python-jose e "
   "⟨bcrypt⟩, para a autenticação, ⟨statsmodels⟩, para o modelo SARIMAX (⟨Seasonal AutoRegressive Integrated "
   "Moving Average with eXogenous inputs⟩) e os testes estatísticos, e ⟨pandas⟩ e ⟨numpy⟩, para o processamento "
   "dos dados,",
   "⟨frameworks⟩ e bibliotecas do painel: ⟨React⟩ 18, com Vite, Tailwind CSS e componentes MUI, e ⟨Recharts⟩, "
   "para os gráficos,",
   "análise exploratória e experimentos: ⟨scripts⟩ Python e Jupyter Notebooks, com as bibliotecas ⟨matplotlib⟩, "
   "seaborn e ⟨scikit-learn⟩, executados fora da aplicação,",
   "bancos de dados: PostgreSQL, no serviço Neon, no ambiente de produção, e ⟨SQLite⟩, no desenvolvimento e nos "
   "testes,",
   "testes: ⟨pytest⟩, para os testes unitários e de integração, e Playwright, para os testes de ponta a ponta,",
   "ambiente de desenvolvimento: Visual Studio Code, no sistema operacional Windows 11,",
   "ambiente operacional: aplicação ⟨web⟩, acessada pelo navegador, com a API em contêiner Docker sobre Linux e o "
   "painel publicado como conjunto de arquivos estáticos,",
   "versionamento: ⟨Git⟩, com o repositório hospedado no ⟨GitHub⟩.")
cp("O pipeline de dados está organizado em três camadas")
h2("6.4 Ferramentas de Modelagem")
p("A modelagem do sistema utilizou a linguagem ⟨Unified Modeling Language⟩ (UML), com os diagramas de casos de "
  "uso, de atividades, de classes e de sequência, complementados pelo Diagrama Entidade-Relacionamento (DER) do "
  "banco de dados e por um diagrama da arquitetura lógica, apresentados no Capítulo 8. Os diagramas de casos de "
  "uso, de atividades e de classes, o DER e a arquitetura foram descritos em texto, na linguagem DOT, e "
  "renderizados com a ferramenta Graphviz, o que permite versioná-los no mesmo repositório do código e "
  "atualizá-los a cada mudança do sistema. O diagrama de sequência foi desenhado em Python, com a biblioteca "
  "⟨matplotlib⟩. O protótipo das telas foi construído na ferramenta Figma, descrita no Capítulo 9.")
h2("6.5 Preparação dos Dados e Modelo Preditivo")
p("A preparação dos dados é realizada por um ⟨pipeline⟩ de sete etapas. A primeira extrai os registros do "
  "relatório de contas a receber, organizado em blocos por documento de venda, gerando uma linha por produto em "
  "cada documento, com deduplicação entre arquivos e controle de reprocessamento por ⟨hash⟩ de cada planilha. A "
  "segunda padroniza textos, datas e valores e descarta registros sem os campos essenciais. A base não armazena "
  "nome, documento ou código dos clientes, informações sem valor preditivo, e registra apenas se a venda foi feita "
  "a cliente cadastrado. A terceira deriva a unidade operacional, a partir da empresa emissora, e a categoria de "
  "cada produto, por tabelas de correspondência por código e regras aplicadas à descrição. A quarta remove os "
  "lançamentos de serviços e taxas, como frete e prestação de serviço, que não representam demanda de produto, e "
  "a quinta separa as vendas por unidade. A sexta separa as encomendas grandes do fluxo diário de vendas, e a "
  "sétima constrói o calendário diário de cada unidade, com feriados nacionais obtidos da BrasilAPI, fechamentos "
  "observados no histórico e aberturas excepcionais. O mesmo processamento é executado pelo sistema a cada "
  "planilha enviada, com deduplicação em relação às vendas já gravadas.")
p("As três empresas do grupo foram consolidadas em duas unidades operacionais, Jardim Canadá, que reúne a "
  "floricultura e o ⟨garden center⟩, e Itabirito, e os produtos foram organizados em quatro categorias: Grama, "
  "Plantas diversas, que reúne as plantas em geral, exceto as flores de corte, Produtos de jardim, que reúne "
  "substratos, adubos, vasos e demais insumos, e Flores de corte. A classificação é feita a partir da descrição "
  "dos produtos e foi mantida pela entidade parceira na reunião de outubro de 2026.")
p("As encomendas grandes são separadas da série modelada. Uma venda, identificada pela unidade, pela data e pelo "
  "número do documento, é classificada como encomenda grande quando a soma das quantidades de todos os seus itens "
  "supera o limiar da unidade, igual à média mais quatro desvios-padrão da quantidade de todos os pedidos da loja "
  "(IGLEWICZ; HOAGLIN, 1993). Todos os itens do documento passam a compor um fluxo à parte, e o restante, "
  "denominado fluxo diário, é a série prevista pelos modelos. A decisão é tomada sobre o documento inteiro porque "
  "uma encomenda chega como um documento com vários itens, como grama, substrato e mudas, que, isoladamente, "
  "podem parecer vendas comuns. O limiar é próprio de cada unidade, porque as lojas têm pedidos de tamanhos "
  "diferentes, e é recalculado a cada planilha enviada, classificando apenas as vendas inseridas. Segundo a "
  "entidade parceira, essa classe corresponde aos pedidos de empresas preparados com antecedência junto aos "
  "fornecedores, e essas vendas são apresentadas separadamente no painel. O critério foi escolhido, entre "
  "limiares fixos e limiares próprios de cada loja, pelo efeito sobre a regularidade da série e sobre o erro dos "
  "modelos (Seção 11.5).")
cp("Na implementação, o modelo estatístico de séries temporais com regressores exógenos adotado é o SARIMAX")
cp("Regressores exógenos são variáveis externas à série de vendas")
cp("As séries modeladas foram definidas a partir da regularidade das vendas.")
cp("Por isso, a solução define uma série diária para cada uma das quatro categorias",
   ("e porque a categoria concentra quase metade do volume vendido em 19 produtos.",
    "e porque a categoria concentra grande parte do volume vendido em poucos produtos. A modelagem direta das "
    "categorias foi adotada por errar menos que a repartição da previsão da loja entre as categorias (Seção 11.5)."))
cp("O modelo é representado pela notação SARIMAX(p, d, q)(P, D, Q)m")
B.append(("ul", ["y: quantidade vendida em um dia, em uma unidade, de uma categoria ou de um produto de grama, sem "
                 "as encomendas grandes, isto é, o valor que se deseja prever,",
                 "p: número de termos autorregressivos, isto é, quantos dias anteriores da própria série entram no "
                 "cálculo da previsão,",
                 f"d: ordem da diferenciação regular. Com d{NB}={NB}0, o modelo trabalha com o nível das vendas e "
                 "inclui uma constante, de modo que a previsão converge para a média do período de treinamento. Com "
                 f"d{NB}={NB}1, o modelo trabalha com a variação de um dia para o seguinte, sem constante, e a "
                 "previsão parte do nível recente das vendas. O valor é escolhido em cada série, como descrito a "
                 "seguir,",
                 "q: número de termos de médias móveis, isto é, quantos erros de previsão recentes são usados para "
                 "corrigir a previsão seguinte,",
                 f"m: período da sazonalidade. Com m{NB}={NB}7, a sazonalidade é semanal, pois o padrão de vendas "
                 "se repete a cada sete dias,",
                 "P, D e Q: equivalentes a p, d e q na escala sazonal, isto é, comparando o mesmo dia da semana em "
                 f"semanas anteriores. Com D{NB}={NB}0, não se aplica diferenciação sazonal, e o padrão semanal é "
                 "representado pelos termos sazonais P e Q e pelos indicadores de dia da semana."]))
cp("Os valores de p e q são testados entre 0 e 2",
   ("Essa configuração resultou dos experimentos apresentados na Seção 7.3.",
    "A escolha da diferenciação pela validação, a janela de 545 dias e a previsão na escala original, sem "
    "transformação logarítmica, resultaram dos experimentos apresentados na Seção 11.5."))
cp("O efeito das datas comemorativas é aplicado depois do ajuste do modelo",
   ("aplicado apenas quando cada uma das últimas ocorrências, no mínimo duas, ficou em até 0,8 de uma semana comum.",
    "aplicado apenas quando cada uma das últimas ocorrências, no mínimo duas, ficou em até 0,8 de uma semana comum. "
    "A proporção aplicada em cada caso foi definida pelo erro no total da semana das datas (Seção 11.5)."))
cp("O treinamento prevê os 91 dias seguintes à última venda",
   ("que corresponde à decisão de compra da semana.",
    "que corresponde à decisão de compra da semana. O horizonte máximo e a frequência de retreinamento foram "
    "definidos pela variação do erro com a distância do treinamento (Seção 11.5)."))
p("O modelo de cada série é reajustado a cada treinamento, solicitado pelo administrador após o envio das "
  "planilhas, e a validação e a previsão são refeitas com os dados mais recentes. A previsão de cada dia é "
  "preservada depois que o dia passa, formando um histórico que guarda, para cada dia, a previsão mais antiga "
  "feita para ele, até 14 dias antes, de modo que a comparação com o vendido reflita a antecedência com que a "
  "loja planeja a compra. O funcionamento do treinamento e do histórico é detalhado na Seção 10.1.")
h2("6.6 Procedimentos de Testes e Validação")
p("Os testes da solução foram de quatro tipos. Os testes unitários verificam a lógica de domínio isolada, como a "
  "seleção da ordem do modelo, a escolha da diferenciação, as métricas, o fator das datas comemorativas e a regra "
  "do histórico das previsões. Os testes de integração exercitam a API com o banco de dados, como a autenticação "
  "e os perfis de acesso, o envio e a conferência das planilhas, o treinamento e as respostas do painel. Os testes "
  "de ponta a ponta, escritos com a ferramenta Playwright, executam o painel no navegador, conectado à API, e "
  "percorrem os fluxos de login, consulta, envio de planilha, treinamento e exportação com cada perfil de "
  "usuário. Os testes de aceitação foram realizados com a entidade parceira, nas demonstrações do protótipo e das "
  "versões do sistema.")
p("Foram utilizados quatro ambientes. O ambiente de desenvolvimento é a máquina de cada desenvolvedor, com a API, "
  "o painel e um banco ⟨SQLite⟩ local. O ambiente de testes é criado a cada execução: os testes unitários e de "
  "integração usam um banco ⟨SQLite⟩ temporário, e os de ponta a ponta sobem a API e o painel em portas próprias, "
  "sobre uma base sintética de vendas, sem acesso aos dados reais. A homologação utiliza uma cópia da base real em "
  "⟨SQLite⟩ local, na qual o treinamento completo e a importação de planilhas são conferidos antes de serem "
  "executados sobre a produção. O ambiente de produção é formado pelo banco PostgreSQL no serviço Neon, que "
  "recebe as planilhas e o treinamento de produção, e pela configuração de publicação da API em contêiner "
  "Docker, no serviço Render, e do painel, no serviço Vercel.")
p("Os critérios de validação do sistema são os seguintes:")
ul("validação estatística dos modelos: validação " + WF + " da solução definitiva, executada a cada "
   "treinamento. A origem avança um dia por vez nas 56 datas mais recentes que dispõem de 14 dias de vendas "
   "conhecidas, isto é, nas últimas oito semanas, e em cada origem o modelo é reajustado nos 545 dias anteriores "
   "e prevê os 14 dias seguintes. A ordem do modelo é escolhida apenas com os dados anteriores à primeira origem, "
   f"e a validação é executada com d{NB}={NB}0 e com d{NB}={NB}1 para a escolha da diferenciação. As métricas "
   "são calculadas nos dias de loja aberta. Um MASE inferior a 1 indica que o modelo erra menos do que repetir as "
   "vendas da semana anterior, e uma cobertura empírica próxima de 95% indica que a faixa apresentada ao usuário "
   "contém a venda na proporção esperada,",
   "diagnóstico dos resíduos: teste de Ljung-Box, com defasagens de até 14 dias, que verifica se os erros do "
   "modelo ainda guardam relação com os erros dos dias anteriores, e teste de Shapiro-Wilk, que verifica se os "
   "erros seguem distribuição normal, hipótese em que se baseiam os intervalos teóricos. Os dois testes são "
   "aplicados aos resíduos do ajuste final de cada modelo e registrados como diagnóstico complementar, sem impedir "
   "a disponibilização da previsão,",
   "validação funcional: todos os testes automatizados devem ser aprovados antes da incorporação de uma mudança à "
   "versão principal, e o treinamento de produção deve terminar em menos de duas horas (RNF03),",
   "validação com a entidade parceira: aceitação das funcionalidades nas reuniões de demonstração, registrada nas "
   "atas, e verificação de que o sistema responde às questões operacionais da Seção 2.2.")
p("As métricas da validação foram escolhidas pela decisão que a previsão apoia, a compra de produtos perecíveis "
  "para os dias seguintes. O erro absoluto médio (⟨Mean Absolute Error⟩ – MAE) expressa o erro em unidades por "
  "dia, comparável à quantidade comprada, e o erro percentual absoluto ponderado (⟨Weighted Absolute Percentage "
  "Error⟩ – WAPE) expressa o mesmo erro como percentual do volume vendido. O MASE e o erro relativo à previsão "
  "ingênua, que repete as vendas do mesmo dia da semana anterior, indicam se a previsão acrescenta informação à "
  "estimativa mais simples que a loja faria sem o sistema. A razão entre o volume previsto e o vendido e o erro no "
  "total da janela indicam se a previsão levaria a comprar a mais ou a menos, e a cobertura e a largura do "
  "intervalo de 95% avaliam a faixa provável exibida no painel. Além da validação de cada treinamento, a "
  "configuração do modelo foi definida por experimentos comparativos, executados fora da aplicação, cujo "
  "protocolo e resultados estão na Seção 11.5.")

# =====================================================================================
h1("7 ANÁLISE DE REQUISITOS")
p("Os requisitos foram levantados conforme o procedimento descrito na Seção 6.2, em reuniões com a entidade "
  "parceira, com a análise dos relatórios de vendas e a inspeção das planilhas, e validados pela equipe da "
  "Floricultura Verde Perto. Este capítulo apresenta os requisitos funcionais, que descrevem o que o sistema faz, "
  "os requisitos não funcionais, que estabelecem as qualidades e restrições da solução, as regras de negócio, "
  "que expressam condições próprias do domínio, e os atores do sistema.")
h2("7.1 Requisitos Funcionais")
p("O {qd:rf} apresenta os requisitos funcionais do sistema.")
tcopy("rf", "qd", "Requisitos funcionais do sistema de previsão de vendas", "Permitir o envio de planilhas", F_ENT)
cp("As solicitações de identificar produtos comprados em conjunto",
   ("(Seção 8)", "(Capítulo 12)"))
h2("7.2 Requisitos Não Funcionais")
p("Os requisitos não funcionais estabelecem critérios de qualidade da solução e são apresentados no {qd:rnf}.")
tcopy("rnf", "qd", "Requisitos não funcionais do sistema", "Manutenibilidade")
h2("7.3 Regras de Negócio")
cp("As regras de negócio expressam restrições e políticas operacionais")
B.append(("ul", [
    "RN01: a previsão de demanda deve ser diária, com horizonte de até 91 dias, exibido a partir de duas semanas "
    "conforme a escolha do usuário,",
    "RN02: os modelos preditivos devem ser retreinados somente quando houver vendas, calendário, catálogo ou "
    "configuração do modelo novos desde o último treinamento concluído, e cada treinamento deve registrar a "
    "configuração, a versão do código e o período dos dados utilizados,",
    "RN03: a previsão exibida para um dia não deve ser alterada por treinamentos realizados depois dessa data, de "
    "modo que o histórico reflita a previsão mais antiga feita para cada dia,",
    "RN04: séries com menos de 180 dias de histórico e produtos com venda em menos de 28 dos últimos 365 dias não "
    "recebem previsão,",
    "RN05: apenas usuários com perfil autorizado podem enviar planilhas e disparar o treinamento dos modelos,",
    "RN06: o calendário de cada unidade, com feriados, fechamentos e aberturas excepcionais, deve ser considerado "
    "no cálculo da previsão, e os dias sem cadastro seguem o padrão de loja fechada apenas aos domingos,",
    "RN07: toda importação de dados e todo treinamento devem registrar log de execução, permitindo "
    "rastreabilidade e identificação de anomalias,",
    "RN08: encomendas grandes, isto é, vendas cuja quantidade no mesmo documento supera a média mais quatro "
    "desvios-padrão da quantidade dos pedidos da unidade, devem ser separadas da série utilizada no ajuste dos "
    "modelos e apresentadas como fluxo de demanda à parte."]))
h2("7.4 Atores do Sistema")
p("Os atores representam os perfis de usuários que interagem com o sistema, conforme o {qd:atores}.")
tcopy("atores", "qd", "Atores do sistema", "Administrador (gestora de compras)", F_ENT)

# =====================================================================================
h1("8 MODELAGEM")
p("Este capítulo apresenta a representação técnica e visual do sistema, construída a partir dos requisitos do "
  "Capítulo 7: os diagramas UML de casos de uso, de atividades, de classes e de sequência, o modelo do banco de "
  "dados, a arquitetura e os componentes, com as tecnologias de cada um.")
h2("8.1 Diagrama de Casos de Uso")
cp("O diagrama de casos de uso, apresentado na Figura 2",
   ("apresentado na Figura 2", "apresentado na {fig:casos}"),
   ("recebe notificações e exporta relatórios.",
    "recebe notificações e exporta relatórios. A especificação de cada caso de uso está no Apêndice B."))
fig("casos", os.path.join(IMG, "casos_uso.png"), 14.5, "Diagrama de casos de uso")
h2("8.2 Diagrama de Atividades")
cp("O diagrama de atividades, exibido na Figura 3",
   ("exibido na Figura 3", "exibido na {fig:atividades}"))
fig("atividades", os.path.join(MED, "image4.png"), 11.0, "Diagrama de atividades do fluxo de previsão")
h2("8.3 Diagrama de Classes")
cp("O diagrama de classes, apresentado na Figura 4",
   ("apresentado na Figura 4", "apresentado na {fig:classes}"))
fig("classes", os.path.join(MED, "image5.png"), 16.0, "Diagrama de classes")
h2("8.4 Diagrama de Sequência")
p("O diagrama de sequência, apresentado na {fig:sequencia}, mostra a ordem das interações entre a gestora de "
  "compras, o painel, a API, o serviço de previsão e o banco de dados no fluxo principal do sistema. A planilha "
  "selecionada é enviada para conferência, e a API consulta as lojas, o catálogo e as vendas já gravadas e "
  "devolve o período, as vendas novas e os dias sem venda, sem gravar nada. Após a confirmação, a API grava as "
  "vendas, marca as encomendas grandes e registra a planilha. Quando a gestora solicita o treinamento, a API "
  "inicia o serviço de previsão em segundo plano e responde de imediato, e o serviço processa cada série, "
  "gravando os modelos, as previsões e o histórico. Enquanto isso, o painel consulta o andamento do treinamento a "
  "cada três segundos e, ao final, carrega a previsão do último treinamento concluído. Todas as requisições do "
  "painel levam o ⟨token⟩ de acesso do usuário.")
fig("sequencia", os.path.join(IMG, "sequencia.png"), 15.0, "Diagrama de sequência do envio da planilha ao treinamento")
h2("8.5 Modelagem do Banco de Dados")
cp("O modelo entidade-relacionamento, apresentado na Figura 5",
   ("O modelo entidade-relacionamento, apresentado na Figura 5,", "O DER, apresentado na {fig:der},"))
fig("der", os.path.join(MED, "image6.png"), 16.0, "Modelo de dados (entidade-relacionamento)")
h2("8.6 Arquitetura do Sistema")
cp("A arquitetura lógica, ilustrada na Figura 6",
   ("ilustrada na Figura 6", "ilustrada na {fig:arquitetura}"))
fig("arquitetura", os.path.join(MED, "image7.png"), 9.5, "Arquitetura lógica do sistema")
h2("8.7 Tecnologias, Ferramentas e Componentes")
p("O {qd:componentes} relaciona os componentes da arquitetura, a responsabilidade de cada um e as tecnologias "
  "empregadas.")
tnew("componentes", "qd", "Componentes do sistema e tecnologias empregadas",
     ["Componente", "Responsabilidade", "Tecnologias"],
     [["Painel ⟨web⟩", "Telas, gráficos, filtros e geração dos relatórios no navegador", "⟨React⟩ 18, ⟨TypeScript⟩, Vite, Tailwind CSS, MUI, ⟨Recharts⟩"],
      ["Cliente HTTP do painel", "Chamadas à API, renovação do ⟨token⟩ e consulta do andamento do treinamento", "API ⟨fetch⟩ do navegador, contrato OpenAPI"],
      ["API REST", "Rotas de autenticação, envio de planilhas, painel, registros e serviço de previsão", "⟨FastAPI⟩, Pydantic, Uvicorn"],
      ["Autenticação", "Login, ⟨tokens⟩ de acesso e de renovação, perfis e senhas", "JWT (python-jose), ⟨bcrypt⟩"],
      ["Importação", "Leitura do relatório XLSX, padronização, classificação e marcação das encomendas", "openpyxl, ⟨pandas⟩"],
      ["Serviço de previsão", "Seleção da ordem, validação, previsão, fator das datas e histórico", "⟨statsmodels⟩, ⟨pandas⟩, ⟨numpy⟩, processos paralelos"],
      ["Persistência", "Mapeamento das tabelas e transações", "⟨SQLAlchemy⟩ 2.0, psycopg 3"],
      ["Banco de dados", "Vendas, catálogo, calendário, treinamentos, previsões e histórico", "PostgreSQL (Neon), ⟨SQLite⟩"],
      ["Publicação", "Execução da API e entrega do painel", "Docker, Render, Vercel"]],
     [2000, 4072, 3000])

# =====================================================================================
h1("9 PROTOTIPAÇÃO")
p("Antes da implementação das telas definitivas, a interface foi prototipada para validar com a entidade "
  "parceira a organização das funcionalidades e a linguagem das telas. Este capítulo apresenta a ferramenta "
  "utilizada, os protótipos e a sua validação.")
h2("9.1 Ferramentas de Prototipação Utilizadas")
p("O protótipo foi construído na ferramenta Figma, com o recurso Figma Make, que gera um protótipo navegável em "
  "⟨React⟩ a partir das instruções e do desenho das telas. O protótipo usava dados fictícios, definidos no "
  "próprio código, e podia ser percorrido no navegador como o sistema final, sem conexão com a API. O pacote "
  "gerado foi incorporado ao repositório e serviu de base visual para o painel definitivo, que manteve a "
  "identidade visual, o menu lateral e os componentes de interface do protótipo, com os dados fictícios "
  "substituídos pelos dados da API.")
h2("9.2 Protótipos de Interface")
p("O protótipo reunia sete telas: Início, Carregar Planilha, Conferir Dados, Previsão de Compras, Produtos para "
  "Repor, Simular Promoções e Baixar Relatórios. As Figuras {n:p_inicio} a {n:p_simulador} apresentam três delas, "
  "com os dados fictícios do protótipo.")
p("A tela inicial do protótipo ({fig:p_inicio}) reunia indicadores e gráficos de vendas da rede. A tela "
  "Previsão de Compras ({fig:p_previsao}) apresentava, para um produto e uma unidade, as vendas das semanas "
  "anteriores, a estimativa das semanas seguintes com a margem de variação, indicadores de erro, um aviso de data "
  "comemorativa e a quantidade a comprar por semana. A tela Simular Promoções ({fig:p_simulador}) estimava o "
  "efeito de um desconto, de sua duração e de um produto vendido em conjunto sobre as vendas de cada dia da "
  "semana.")
fig("p_inicio", os.path.join(IMG, "p_inicio.jpg"), 16.0, "Protótipo: tela inicial", F_AUT)
fig("p_previsao", os.path.join(IMG, "p_previsao.jpg"), 16.0, "Protótipo: previsão de compras", F_AUT)
fig("p_simulador", os.path.join(IMG, "p_simulador.jpg"), 16.0, "Protótipo: simulação de promoções", F_AUT)
h2("9.3 Validação dos Protótipos com Usuários/Entidade")
p("O protótipo foi apresentado à entidade parceira na reunião de 26 de maio de 2026, em que a empresa definiu os "
  "requisitos da versão final, e na reunião de 2 de junho de 2026, junto com a prova de conceito do modelo de "
  "previsão, quando a empresa considerou os resultados satisfatórios e solicitou ajustes na interface "
  "(Apêndice A). A validação definiu o escopo do sistema final. A tela Produtos para Repor, que comparava o "
  "estoque com um mínimo, foi retirada, porque a empresa não dispõe do estoque atual dos produtos, e a "
  "tela Previsão de Compras passou a apresentar a previsão de vendas, uma vez que a decisão de compra permanece "
  "com a empresa. A simulação de promoções e a identificação de produtos comprados em conjunto foram mantidas "
  "como trabalhos futuros, e a previsão passou a ser diária, por categoria e por produto de grama, conforme "
  "definido nas reuniões de outubro de 2026.")
p("As versões seguintes do sistema, já conectadas aos dados reais, foram validadas nas reuniões de 13 e 20 de "
  "outubro e de 10 de novembro de 2026, em que a empresa aprovou o painel por unidade, o envio e a conferência "
  "das planilhas, a previsão com faixa provável, o histórico das previsões e o botão de treinamento.")

# =====================================================================================
h1("10 IMPLEMENTAÇÃO")
p("Este capítulo descreve como o software foi construído: as funcionalidades principais, as interfaces "
  "desenvolvidas, a integração entre os componentes e as dificuldades encontradas. O ⟨backend⟩ foi implementado "
  "como monólito modular em Python, organizado em camadas: as rotas da API, os esquemas de entrada e saída, os "
  "serviços, que orquestram os casos de uso, o domínio, que contém a lógica de previsão sem dependência de "
  "⟨frameworks⟩ ou do banco de dados, e a infraestrutura, com o acesso ao banco. O painel foi implementado em "
  "⟨React⟩, com uma tela por funcionalidade e componentes compartilhados de leiaute, gráficos e tabelas. Os "
  "contratos entre o painel e a API estão documentados na especificação OpenAPI do projeto.")
h2("10.1 Funcionalidades")
p("As funcionalidades mais importantes são descritas a seguir pelo objetivo, pela forma de implementação, pelos "
  "componentes envolvidos, pelas regras de negócio aplicadas e pela interação com o banco de dados.")
h3("10.1.1 Autenticação e perfis de acesso")
p("O objetivo é restringir o acesso ao sistema aos usuários da empresa, conforme o perfil (RNF04 e RN05). O "
  "login recebe o e-mail e a senha, confere a senha com o ⟨hash⟩ ⟨bcrypt⟩ gravado na tabela users e emite dois "
  "⟨tokens⟩ JWT (⟨JSON Web Token⟩) assinados: um ⟨token⟩ de acesso, válido por oito horas, enviado em todas as "
  "requisições, e um ⟨token⟩ de renovação, válido por sete dias, usado para obter um novo ⟨token⟩ de acesso sem "
  "novo login. Ao sair, o ⟨token⟩ de renovação é registrado na tabela revoked_tokens e passa a ser recusado. As "
  "rotas de envio de planilhas e de treinamento exigem o perfil de administrador, e as demais aceitam também o "
  "perfil de consulta. O login limita o número de tentativas por e-mail e por endereço de origem, e a API não "
  "inicia com chave de assinatura ou senhas curtas ou de exemplo. Os componentes envolvidos são a tela de login, "
  "o contexto de autenticação do painel e o módulo de autenticação da API.")
h3("10.1.2 Envio e conferência das planilhas")
p("O objetivo é incorporar as vendas de cada semana à base sem conhecimento técnico e sem duplicar ou perder "
  "dados (RF01, RF07, RN07 e RN08). A importação ocorre em duas chamadas à API. Na conferência, a API lê o "
  "relatório de contas a receber, extrai uma linha por produto, padroniza datas, quantidades e valores, associa a "
  "empresa emissora à unidade e cada produto à sua categoria e compara as linhas com as vendas já gravadas, sem "
  "gravar nada. O resultado informa o período de cada unidade, as vendas novas e as já carregadas, as linhas "
  "ignoradas e os dias de loja aberta que ficariam sem venda, que seriam tratados como venda zero pelos modelos. "
  "Na gravação, confirmada pelo administrador, a API recalcula o limiar de encomenda grande de cada unidade, com "
  "os pedidos já gravados e os da planilha, marca as vendas novas que o superam e grava as linhas novas. Uma "
  "planilha já gravada, identificada pelo ⟨hash⟩ SHA-256 do arquivo, é recusada. Os componentes envolvidos são a "
  "tela Carregar Planilha, as rotas de envio e o serviço de importação, que reutiliza as etapas do ⟨pipeline⟩ de "
  "dados. A gravação insere as vendas na tabela sales, cadastra os produtos novos em products e registra a "
  "planilha, com o período, as contagens, o limiar e os avisos, em processing_log. O nome e o código dos "
  "clientes não são gravados: cada venda registra apenas se o cliente era cadastrado.")
h3("10.1.3 Treinamento das previsões")
p("O objetivo é atualizar os modelos com as vendas mais recentes (RF03, RF09, RN02, RN04 e RN06). O treinamento "
  "é solicitado pelo botão Treinar previsões, visível ao administrador, ou por um ⟨script⟩ executado pela equipe "
  "técnica sobre o mesmo banco. Antes de começar, o serviço calcula uma impressão digital, com ⟨hash⟩ SHA-256, "
  "das vendas, do calendário, do catálogo e da configuração do modelo e, se nada mudou desde o último "
  "treinamento concluído, registra o pedido como dispensado. Caso contrário, monta a série diária de cada "
  "categoria e de cada produto de grama de cada unidade, sem as encomendas grandes, separa as séries sem o "
  "histórico mínimo e distribui as demais entre processos paralelos. Para cada série, o serviço seleciona a ordem "
  f"do modelo, executa a validação {WF} com d{NB}={NB}0 e com d{NB}={NB}1, mantém o valor de menor erro, calcula "
  "as métricas e os testes dos resíduos, ajusta o modelo final, gera a previsão dos 91 dias seguintes e aplica o "
  "fator das datas comemorativas. O andamento, com a série atual e o percentual concluído, é gravado a cada "
  "etapa e apresentado no painel de notificações. Ao final, o treinamento grava os dias novos do histórico das "
  "previsões e passa a ser o exibido pelas telas. O treinamento é registrado na tabela forecast_jobs, com a "
  "configuração, a versão do código, o período dos dados e as contagens por situação, e cada série é registrada "
  "em series_models, com a ordem, as métricas, o diagnóstico dos resíduos e os coeficientes. As previsões ficam "
  "em series_forecasts, os pontos da validação em series_backtest_points e o log série a série em "
  "forecast_job_logs, e as planilhas usadas pelo treinamento ficam ligadas a ele em processing_log.")
h3("10.1.4 Previsão diária e horizonte")
p("O objetivo é apresentar quanto se espera vender em cada dia (RF02, RF04, RN01 e RN06). A rota do painel lê o "
  "último treinamento concluído e devolve, para cada série, a previsão dos 91 dias com o intervalo de 95%, a "
  "venda das semanas anteriores, o calendário com feriados e datas comemorativas e as métricas da validação. A "
  "tela recorta a previsão no horizonte escolhido, de duas semanas a três meses, soma as categorias para obter o "
  "total de cada unidade e marca os dias de loja fechada, cuja previsão é zero. Nos produtos de grama de menor "
  "volume de Jardim Canadá, um ícone de informação indica que os números servem como referência, junto com a "
  "experiência da loja (Seção 11.5). A funcionalidade lê as tabelas forecast_jobs, series_models, "
  "series_forecasts, sales e calendar_days.")
h3("10.1.5 Histórico das previsões")
p("O objetivo é permitir comparar, dia a dia, o previsto e o vendido (RF08 e RN03). Cada treinamento concluído "
  "grava, na tabela forecast_history, apenas os dias ainda sem registro: os 14 primeiros dias da sua previsão e, "
  "para os dias que nenhuma previsão cobriu, como os anteriores ao primeiro treinamento ou os de intervalos "
  f"maiores que 14 dias entre treinamentos, a janela mais antiga da validação {WF} que os previu, até 14 dias "
  "antes. Um registro gravado não é alterado por treinamentos posteriores, de modo que o histórico guarda a "
  "previsão mais antiga feita para cada dia, com a data em que foi feita e a indicação de loja fechada. A rota de "
  "histórico combina esses registros com as vendas do dia, sem as encomendas grandes, e com as métricas da "
  "validação do último treinamento que avaliou a série.")
h3("10.1.6 Análise e conferência das vendas")
p("O objetivo é apresentar as vendas da base e permitir conferi-las (RF05, RF06 e RF11). Os resumos não são "
  "gravados: a API os calcula a partir da tabela sales a cada consulta, como o faturamento mensal com as "
  "encomendas grandes em destaque, o faturamento médio por dia da semana, a participação das categorias, a "
  "comparação entre consumidores e clientes cadastrados, as formas de pagamento e os produtos mais vendidos. A "
  "conferência das vendas consulta as linhas gravadas com paginação, busca por produto, código ou número da nota, "
  "filtros por mês, unidade, categoria e tipo de venda e exportação do resultado do filtro.")
h3("10.1.7 Relatórios e registro de uso")
p("O objetivo é levar a previsão e os indicadores para fora do sistema (RF10 e RNF02). Os relatórios são montados "
  "no navegador, a partir dos dados já carregados da API: as planilhas Excel e os arquivos CSV são gerados pelo "
  "próprio painel, e os relatórios em PDF, como o relatório gerencial com a previsão do horizonte escolhido, o "
  "acerto da previsão no teste do treinamento e as encomendas grandes, são produzidos pela impressão do "
  "navegador. A mesma tela apresenta o registro de uso do sistema, com as planilhas enviadas e os treinamentos, "
  "lido das tabelas processing_log e forecast_jobs.")
h2("10.2 Interfaces Desenvolvidas")
p("O painel organiza as funcionalidades em cinco telas acessíveis pelo menu lateral, Início, Carregar Planilha, "
  "Conferir Dados, Previsão de Vendas e Relatórios, além da tela de login. No cabeçalho, ficam o botão Atualizar, "
  "o botão Treinar previsões, visível apenas ao administrador, e o painel de notificações. As telas a seguir "
  "foram capturadas do sistema em execução local, conectado ao banco de dados de produção, com as vendas até 28 "
  "de fevereiro de 2026.")
p("A tela de login ({fig:login}) tem a finalidade de identificar o usuário. Os seus componentes são os campos de "
  "e-mail e senha e o botão Entrar, que permanece desabilitado até o preenchimento dos campos. Após o login, o "
  "usuário é levado à tela inicial, e o perfil define as ações disponíveis.")
fig("login", os.path.join(IMG, "t_login.png"), 9.0, "Tela de login", F_TELA)
p("A tela inicial ({fig:inicio}) apresenta a visão geral das vendas da base. Os componentes são o filtro de "
  "unidade, quatro indicadores, de faturamento líquido, notas de venda, quantidade vendida e encomendas grandes, "
  "o gráfico de faturamento mensal, que separa a venda do dia a dia das encomendas grandes e alterna entre "
  "faturamento e quantidade, o faturamento médio por dia da semana, a participação de cada categoria na "
  "quantidade e no faturamento, a comparação entre consumidores e clientes cadastrados, as formas de pagamento e "
  "a tabela dos produtos mais vendidos no último ano. Nenhum dado pessoal de cliente é exibido, e o rodapé do "
  "menu informa a data da última venda carregada.")
fig("inicio", os.path.join(IMG, "t_inicio.png"), 14.0, "Tela inicial com a análise das vendas", F_TELA, 21.0)
p("A tela Carregar Planilha ({fig:importar}) conduz a importação em quatro etapas, envio do arquivo, "
  "conferência, gravação e conclusão, indicadas no topo da tela. O componente principal é a área de envio, que "
  "aceita arquivos XLSX e XLSM de até 50 MB, arrastados ou selecionados, e, abaixo dela, fica o quadro das "
  "planilhas já carregadas, com o mês e o número de linhas de cada uma.")
fig("importar", os.path.join(IMG, "t_importar.png"), 15.5, "Tela de envio de planilha", F_TELA)
p("Na conferência ({fig:conferencia}), a tela apresenta o período de cada unidade e a última venda já carregada, "
  "os totais de vendas novas, de vendas já carregadas e de linhas ignoradas, o aviso dos dias de loja aberta sem "
  "venda, com a orientação de enviar a planilha desses dias antes de treinar, e os avisos sobre linhas ignoradas, "
  "com os botões Cancelar e Gravar. No exemplo, foi conferida, sem gravação, uma planilha de teste com vendas "
  "fictícias de março de 2026.")
fig("conferencia", os.path.join(IMG, "t_conferencia.png"), 15.5, "Conferência da planilha antes da gravação", F_TELA)
p("A tela Conferir Dados ({fig:conferir}) permite consultar as vendas gravadas. Os componentes são a busca por "
  "produto, código ou número da nota, o botão de filtros, a escolha do mês, a seleção de colunas, a exportação, a "
  "tabela paginada, com data, loja, nota, produto, categoria, quantidade, valor líquido, forma de pagamento, tipo "
  "de cliente e tipo de venda, e a linha de total do filtro.")
fig("conferir", os.path.join(IMG, "t_conferir.png"), 15.5, "Tela de conferência das vendas importadas", F_TELA)
p("A tela Previsão de Vendas tem duas abas. Na aba Previsão ({fig:previsao}), a caixa Horizonte define o período "
  "exibido, de duas semanas a três meses, e o quadro de feriados e datas comemorativas lista as datas do período "
  "e se as lojas abrem. O gráfico mostra, para a unidade escolhida, a venda das semanas anteriores e a previsão de "
  "cada categoria, e a tabela Dia a dia apresenta a quantidade prevista em cada dia, por categoria ou por "
  "produto, com o total do dia e os dias de loja fechada sinalizados. Ao passar o cursor sobre um valor, a tela "
  "mostra a faixa provável, correspondente ao intervalo de 95%. Na visão por produto ({fig:previsao_produto}), a "
  "lista dos produtos de grama da unidade, ordenada pela quantidade prevista, permite escolher o produto, cujo "
  "gráfico apresenta o vendido, a previsão e a faixa provável, com acesso ao histórico do produto.")
fig("previsao", os.path.join(IMG, "t_previsao.png"), 15.0, "Previsão diária por categoria no horizonte escolhido", F_TELA, 21.0)
fig("previsao_produto", os.path.join(IMG, "t_previsao_produto.png"), 15.5, "Previsão de um produto de grama, com a faixa provável", F_TELA)
p("A aba Histórico de previsão ({fig:historico}) compara o vendido em cada dia, sem as encomendas grandes, com a "
  "previsão mais antiga feita para ele, por categoria ou por produto, nos últimos três meses, no último ano, em "
  "todo o período ou em um mês escolhido. Os indicadores resumem a validação do último treinamento: o erro médio "
  "por dia, em unidades, e a margem de incerteza, igual à metade da largura média do intervalo de 95%. O gráfico "
  "marca o início do período de teste do treinamento e mostra a faixa prevista.")
fig("historico", os.path.join(IMG, "t_historico.png"), 15.5, "Histórico da previsão: vendido e previsto", F_TELA)
p("A tela Relatórios ({fig:relatorios}) reúne os relatórios para baixar, com filtro de unidade: o relatório "
  "gerencial em PDF, as previsões diárias por loja e categoria e por produto de grama, o histórico de vendas por "
  "semana e por dia, as encomendas grandes por semana, o acerto da previsão de cada categoria e de cada produto de "
  "grama, o teste de acerto dia a dia e a lista das planilhas importadas, nos formatos Excel e PDF. Abaixo, o "
  "quadro Uso do sistema lista as planilhas enviadas e os treinamentos, do mais recente para o mais antigo.")
fig("relatorios", os.path.join(IMG, "t_relatorios.png"), 15.5, "Tela de relatórios", F_TELA)
p("Por fim, o cabeçalho ({fig:notificacoes}) apresenta o botão Treinar previsões, que solicita o treinamento e "
  "indica o andamento durante a execução, e o painel de notificações, que informa o andamento e o resultado do "
  "treinamento, a existência de vendas ainda não usadas pela previsão ou, como no exemplo, o tempo sem vendas "
  "novas na base, com o atalho para carregar a planilha.")
fig("notificacoes", os.path.join(IMG, "t_notificacoes.png"), 11.0, "Botão Treinar previsões e painel de notificações", F_TELA)
h2("10.3 Integração entre Componentes")
p("O painel comunica-se com a API por requisições HTTP no padrão REST (⟨Representational State Transfer⟩), com "
  "dados em JSON, definidas no contrato OpenAPI do projeto, que documenta cada rota, os parâmetros, as respostas "
  "e o perfil exigido. As chamadas são feitas por um cliente HTTP do painel, que acrescenta o ⟨token⟩ de acesso "
  "ao cabeçalho de cada requisição e, quando a API responde que o ⟨token⟩ expirou, obtém um novo ⟨token⟩ com o de "
  "renovação e repete a requisição, com uma única renovação para todas as chamadas pendentes. O ⟨token⟩ de "
  "acesso é mantido apenas em memória, e o de renovação, no armazenamento local do navegador. No perfil de "
  "administrador, o painel consulta a rota de andamento do treinamento a cada três segundos durante a execução e "
  "a cada minuto fora dela, e atualiza as telas quando um novo treinamento é concluído.")
p("A API acessa o banco de dados por meio do ⟨SQLAlchemy⟩, que mapeia as tabelas em classes e isola o código do "
  "banco utilizado, de modo que o mesmo código opera sobre o PostgreSQL, por meio do ⟨driver⟩ psycopg, e sobre o "
  "⟨SQLite⟩, conforme o endereço configurado. Como o serviço Neon suspende o banco após um período ocioso, as "
  "conexões são verificadas antes do uso e renovadas periodicamente, e as gravações do treinamento são repetidas "
  "em caso de falha temporária da conexão.")
p("Em execução, a API não depende de serviços externos. Os feriados nacionais, obtidos da BrasilAPI no "
  "pré-processamento, e os fechamentos e aberturas excepcionais de cada loja são gravados na tabela de "
  "calendário, lida pelo serviço de previsão. O serviço de previsão é chamado pela API em uma linha de execução em "
  "segundo plano, quando a API está configurada para treinar, ou por um ⟨script⟩ de linha de comando, que executa "
  "o mesmo treinamento sobre o mesmo banco. A segunda forma é a utilizada na produção, porque o plano gratuito do "
  "serviço de hospedagem da API não dispõe de memória e processamento suficientes para o treinamento. Nos dois "
  "casos, as séries são distribuídas entre processos paralelos, e os resultados são gravados no banco, de onde as "
  "telas os leem.")
p("A API é empacotada em uma imagem Docker, e o painel é compilado em arquivos estáticos, configurados para "
  "publicação nos serviços Render e Vercel, respectivamente. A política de segurança do painel restringe as "
  "conexões ao endereço da API, e a API aceita requisições apenas da origem do painel.")
h2("10.4 Dificuldades Encontradas")
p("Durante a implementação, foram enfrentadas as dificuldades descritas a seguir, com a solução adotada em cada "
  "caso:")
ul("formato dos dados: as vendas chegam em relatórios de contas a receber organizados em blocos por documento, "
   "com cabeçalho, itens e totais, e não em uma tabela, o que exigiu um leitor próprio para extrair uma linha por "
   "produto e conferir a soma dos itens com o total de cada documento,",
   "duplicidade: o mesmo produto pode aparecer em duas linhas legítimas de uma mesma nota, de modo que a "
   "duplicidade é verificada em relação às vendas já gravadas, pela combinação do número do documento, do "
   "produto, da data, da quantidade e do valor, e cada planilha é identificada pelo ⟨hash⟩ do arquivo,",
   "classificação dos produtos: o relatório não informa o grupo de cada produto, e a classificação pela descrição "
   "gerava erros, corrigidos por uma revisão produto a produto e por um ⟨script⟩ que reaplica as regras ao "
   "catálogo gravado sem apagar dados,",
   "limitação do ambiente de publicação: o plano gratuito do serviço de hospedagem da API dispõe de 512 MB de "
   "memória e de uma fração de processador, insuficientes para o treinamento, que passou a ser executado por "
   "⟨script⟩ fora da API publicada, e a exportação das vendas passou a ser enviada em partes, para reduzir o uso "
   "de memória,",
   "conexão com o banco em nuvem: o serviço Neon suspende o banco ocioso, e quedas curtas de conexão "
   "interrompiam treinamentos longos, o que levou à verificação das conexões antes do uso e à repetição das "
   "gravações em caso de falha,",
   "tempo de treinamento: a escolha da diferenciação em cada série multiplica o número de ajustes do modelo, e o "
   "treinamento foi distribuído entre processos paralelos, com retorno ao processamento série a série quando os "
   "processos falham,",
   "momento do treinamento: treinar automaticamente após cada envio usaria semanas incompletas quando as vendas "
   "chegam em mais de uma planilha, e o treinamento passou a ser solicitado pelo administrador ao terminar o "
   "envio, com a verificação de dados novos para evitar treinamentos repetidos,",
   "compatibilidade de bibliotecas: a versão do Python da imagem de publicação exigiu a atualização das versões "
   "das bibliotecas, e a biblioteca de ⟨hash⟩ de senhas utilizada inicialmente era incompatível com a versão "
   "atual do ⟨bcrypt⟩, que passou a ser usado diretamente,",
   "atualização da base: a extração dos relatórios depende do computador do setor financeiro e é demorada, e a "
   "base disponível termina em fevereiro de 2026, o que levou à conferência, na importação, dos dias de loja "
   "aberta sem venda, para que semanas não enviadas não sejam tratadas como vendas nulas.")

# =====================================================================================
h1("11 RESULTADOS E DISCUSSÕES")
p("Este capítulo demonstra o que foi alcançado com a implementação e analisa criticamente os resultados: as "
  "funcionalidades em operação, a validação dos requisitos, os resultados dos testes do sistema, a análise "
  "exploratória dos dados, os experimentos de modelagem e a validação da solução definitiva, seguidos da "
  "comparação com os objetivos e da discussão.")
h2("11.1 Apresentação dos Resultados")
p("As funcionalidades especificadas no Capítulo 7 estão implementadas e em operação com os dados reais da "
  "empresa. O banco de produção contém as 26 planilhas de janeiro de 2024 a fevereiro de 2026, com 351.092 linhas "
  "e nenhuma planilha duplicada, e o último treinamento, concluído em 10 de novembro de 2026 com as vendas até 28 "
  "de fevereiro de 2026, gerou a previsão de 23 séries, 8 categorias e 15 produtos de grama, e registrou 20 "
  "séries sem previsão por falta de dados. As telas da Seção 10.2 foram capturadas desse banco e evidenciam o "
  "funcionamento do login com perfis, da análise das vendas, do envio e da conferência de planilhas, da consulta "
  "das vendas, da previsão diária no horizonte escolhido, do histórico das previsões, dos relatórios e das "
  "notificações.")
p("A {fig:pdf} apresenta a primeira página do relatório gerencial em PDF gerado pelo sistema para as duas "
  "semanas seguintes à última venda, de 1º a 14 de março de 2026, para todas as lojas e categorias. O relatório "
  "traz a previsão total de 42.313 unidades, com média de 3.526 unidades por dia de loja aberta, o acerto de cada "
  "categoria no teste do treinamento, a previsão por categoria, a previsão de cada dia com a faixa provável e a "
  "previsão de cada produto de grama. A {fig:uso} mostra o registro de uso do sistema, com o treinamento "
  "concluído e as cargas da base, que evidencia a rastreabilidade exigida pelo requisito RNF02.")
fig("pdf", os.path.join(IMG, "t_pdf.png"), 12.5, "Primeira página do relatório gerencial em PDF", F_TELA, 19.0)
fig("uso", os.path.join(IMG, "t_uso.png"), 13.0, "Registro de uso do sistema", F_TELA)
h2("11.2 Validação dos Requisitos")
p("O {qd:validacao} retoma os requisitos do Capítulo 7 e as solicitações registradas nas atas e informa se cada "
  "um foi atendido.")
tnew("validacao", "qd", "Validação dos requisitos",
     ["Requisito", "Situação", "Observação"],
     [["RF01 – Envio de planilhas", "Atendido", "Envio em quatro etapas, por arrastar ou selecionar o arquivo ({fig:importar})"],
      ["RF02 – Previsão diária", "Atendido", "Previsão de 91 dias de 23 séries, exibida de duas semanas a três meses ({fig:previsao})"],
      ["RF03 – Atualização dos modelos", "Atendido", "Botão Treinar previsões e ⟨script⟩, com dispensa quando não há dados novos"],
      ["RF04 – Indicadores de desempenho", "Atendido", "Erro por dia e margem de incerteza explicados na tela e acerto por série nos relatórios ({fig:historico} e {fig:pdf})"],
      ["RF05 – Gráficos de vendas e previsão", "Atendido", "Telas Início e Previsão de Vendas"],
      ["RF06 – Produtos mais vendidos", "Atendido", "Tabela dos produtos mais vendidos no último ano ({fig:inicio})"],
      ["RF07 – Conferência da planilha", "Atendido", "Período, vendas novas e dias sem venda antes da gravação ({fig:conferencia})"],
      ["RF08 – Histórico das previsões", "Atendido", "Previsão mais antiga de cada dia comparada ao vendido ({fig:historico})"],
      ["RF09 – Notificações", "Atendido", "Andamento do treinamento e avisos sobre a base ({fig:notificacoes})"],
      ["RF10 – Exportação de relatórios", "Atendido", "Relatórios em PDF, Excel e CSV ({fig:relatorios})"],
      ["RF11 – Painel centralizado", "Atendido", "Cinco telas acessíveis por um menu único"],
      ["RF12 – Documentação", "Parcialmente atendido", "Documentação técnica, contrato da API e registros de decisão no repositório, sem manual do usuário"],
      ["RNF01 – Usabilidade", "Parcialmente atendido", "Telas aprovadas pela empresa nas reuniões, sem teste formal de usabilidade"],
      ["RNF02 – Confiabilidade", "Atendido", "Registro de cada planilha e de cada treinamento, com log série a série ({fig:uso})"],
      ["RNF03 – Desempenho", "Atendido", "Treinamento de produção em 75 minutos, em segundo plano (Seção 11.3)"],
      ["RNF04 – Segurança", "Atendido", "JWT, perfis de acesso, senhas em ⟨bcrypt⟩, limite de tentativas de login e nenhum dado pessoal de cliente armazenado"],
      ["RNF05 – Manutenibilidade", "Atendido", "Código modular e versionado, com 196 testes automatizados"],
      ["Produtos comprados em conjunto, simulação de promoções e avisos de reposição (atas)", "Não atendido", "Fora do escopo desta versão e indicados como trabalhos futuros"]],
     [3000, 1700, 4372], F_AUT, "grade", ["left", "center", "left"])
p("Dos 17 requisitos funcionais e não funcionais, 15 foram atendidos e 2 foram atendidos parcialmente, a "
  "documentação, que não inclui um manual do usuário, e a usabilidade, que foi avaliada apenas de forma "
  "qualitativa nas reuniões. As solicitações registradas nas reuniões iniciais que não integram esta versão foram "
  "retiradas do escopo de comum acordo com a entidade parceira.")
h2("11.3 Resultados dos Testes")
p("Os testes automatizados foram executados em 11 de novembro de 2026, e a {tab:testes} resume os resultados.")
tnew("testes", "tab", "Resultados dos testes automatizados",
     ["Conjunto", "Casos executados", "Casos aprovados", "Sucesso"],
     [["Testes unitários (⟨pytest⟩)", "120", "120", "100%"],
      ["Testes de integração (⟨pytest⟩)", "76", "76", "100%"],
      ["Total", "196", "196", "100%"]],
     [3672, 1800, 1800, 1800], "Fonte: Elaborado pelos autores (2026). Execução de 11 de novembro de 2026, concluída em 3 min 37 s.",
     "aberta", ["left", "center", "center", "center"])
p("Os testes unitários e de integração verificam a seleção da ordem e da diferenciação, a validação " + WF +
  " e as métricas do treinamento, o fator das datas comemorativas, a regra do histórico das previsões, a "
  "conferência das planilhas, a autenticação e os perfis de acesso e as respostas do painel, e os 196 casos "
  "foram aprovados. A suíte de ponta a ponta, com 39 testes em oito fluxos, de login, início, conferência das "
  "vendas, previsão, relatórios, envio de planilha, treinamento e perfil de consulta, não foi concluída nessa "
  "execução: a preparação da base sintética, que inclui um treinamento completo, excedeu o tempo limite de dez "
  "minutos do servidor de testes, e os seus resultados não são apresentados.")
cp("A importação foi testada com planilhas de vendas fictícias de março de 2026",
   ("O teste também mostrou um caso não detectado: uma nota repetida inteira dentro da mesma planilha entra duas "
    "vezes, porque a duplicidade é verificada apenas contra a base já gravada.",
    "A mesma conferência, repetida sobre o banco de produção, apresentou os mesmos números ({fig:conferencia}). O "
    "teste também revelou um defeito ainda não corrigido: uma nota repetida inteira dentro da mesma planilha entra "
    "duas vezes, porque a duplicidade é verificada apenas em relação à base já gravada."))
p("O tempo de resposta da API foi medido com a API executada localmente e conectada ao banco de produção, em dez "
  "requisições a cada rota de consulta, e é apresentado na {tab:tempo}. As rotas responderam, em média, entre "
  "0,44 e 0,87 segundo, inclusive a do painel, que transfere cerca de 311 kB com a previsão de 91 dias de todas "
  "as séries. O treinamento de produção, com as 43 séries, foi executado sobre o banco de produção com 12 "
  "processos paralelos e levou 75 minutos, dentro do limite de duas horas do requisito RNF03.")
tnew("tempo", "tab", "Tempo médio de resposta das rotas de consulta da API",
     ["Rota", "Conteúdo", "Tempo médio (s)"],
     [["/api/v1/contexto", "Lojas, categorias, última venda e situação das séries", "0,867"],
      ["/api/v1/painel", "Previsão de 91 dias, vendas recentes e acerto", "0,550"],
      ["/api/v1/analises", "Resumos da tela inicial", "0,521"],
      ["/api/v1/registros/linhas", "Página de 50 vendas da conferência", "0,570"],
      ["/api/v1/servico-previsao/status", "Andamento do treinamento", "0,728"],
      ["/api/v1/atividades", "Registro de uso do sistema", "0,443"]],
     [3200, 4072, 1800], "Fonte: Elaborado pelos autores (2026). Dez requisições por rota, API local conectada ao banco de produção, em 11 de novembro de 2026.",
     "aberta", ["left", "left", "center"])
p("Não foram realizados testes formais de usabilidade. A avaliação da interface foi qualitativa, nas reuniões de "
  "13 e 20 de outubro e de 10 de novembro de 2026, em que a empresa aprovou as telas apresentadas e considerou o "
  "sistema satisfatório (Apêndice A).")
h2("11.4 Análise Exploratória dos Dados")
p("Aplicado às 26 planilhas mensais de janeiro de 2024 a fevereiro de 2026, o ⟨pipeline⟩ produziu 351.092 "
  "registros, sem duplicatas, dos quais 345.399 correspondem à demanda de produtos, distribuídos em 5.204 códigos "
  "de produto. Em volume vendido, a Grama responde por 48,4%, Plantas diversas, por 38,2%, Produtos de jardim, por "
  "11,5%, e Flores de corte, por 1,8%. Com o critério de encomenda grande, o limiar é de 1.343 unidades em Jardim "
  "Canadá e de 1.960 unidades em Itabirito, e 209 e 96 vendas, respectivamente, foram classificadas como "
  "encomendas grandes, correspondendo a 27,0% e 52,5% do volume de cada unidade.")
cp("A análise exploratória classificou o padrão de demanda pelo critério de Syntetos, Boylan e Croston (2005)")
B.append(("ul", ["suave: vende quase todos os dias (ADI menor que 1,32), em quantidades parecidas (CV² menor que "
                 "0,49),",
                 "errática: vende quase todos os dias, mas em quantidades muito variáveis (ADI menor que 1,32 e CV² "
                 "igual ou maior que 0,49),",
                 "intermitente: vende em poucos dias, em quantidades parecidas (ADI igual ou maior que 1,32 e CV² "
                 "menor que 0,49),",
                 "⟨lumpy⟩: vende em poucos dias e em quantidades muito variáveis (ADI igual ou maior que 1,32 e CV² "
                 "igual ou maior que 0,49)."]))
cp("Os resultados confirmam que a previsão individual da maior parte dos produtos não é viável")
cp("Testes preliminares de nível de agregação, executados na análise exploratória")
h2("11.5 Experimentos de Modelagem")
cp("A configuração da solução final foi definida por uma sequência de experimentos",
   ("A relação dos experimentos e das configurações comparadas é apresentada com os resultados, na Seção 7.3.",
    "O {qd:experimentos} relaciona os experimentos e as configurações comparadas."))
cp("Foram utilizados dois protocolos de validação walk-forward" if False else "Foram utilizados dois protocolos de validação")
cp("A métrica de referência é o MASE, calculado com a escala da previsão ingênua",
   ("A Seção 7.2 relaciona cada métrica à decisão de compra.",
    "A relação de cada métrica com a decisão de compra está descrita na Seção 6.6."))
tcopy("experimentos", "qd", "Experimentos realizados", "Referência inicial", F_AUT,
      [("Configuração final (Seção 4.5)", "Configuração final (Seção 6.5)")])
cp("No experimento E2, as variáveis candidatas foram")
cp("Nos experimentos E1 a E4, a série foi modelada em")
cp("A Tabela 1 apresenta os experimentos E1 e E2", ("A Tabela 1 apresenta", "A {tab:e1} apresenta"))
tcopy("e1", "tab", "Efeito das variáveis exógenas na série total da rede (E1 e E2)", "MAE nos 14 feriados")
cp("As variáveis climáticas não trouxeram ganho")
cp("O experimento E3 avaliou, na série de cada unidade", ("A Tabela 2 mostra", "A {tab:e3} mostra"))
tcopy("e3", "tab", "MASE da separação das encomendas pelo limiar por linha (E3)", "Só limitação dos picos")
cp("O experimento E4 aplicou esses achados", ("apresentadas na Tabela 3", "apresentadas na {tab:e4}"))
tcopy("e4", "tab", "Modelo por unidade: calendário, diferenciação e Holt-Winters (E4)", "Jardim Canadá: janelas vencidas")
cp("A versão com calendário e d = 1 obteve" if False else "A versão com calendário e d")
cp("Os experimentos anteriores classificavam como encomenda linhas de venda isoladas", ("(Tabela 4)", "({tab:e5})"))
tcopy("e5", "tab", "Sensibilidade do critério de encomenda grande (E5)", "Escore z modificado por linha",
      "Fonte: Elaborado pelos autores (2026). Volume: parcela do volume classificada como encomenda, CV: coeficiente de variação do fluxo diário, balcão: parcela do volume de consumidores sem cadastro retirada do fluxo.")
cp("Em todos os limiares, o critério por venda produziu")
cp("O experimento E6 isolou o efeito da transformação logarítmica", ("(Tabela 5)", "({tab:e6})"))
tcopy("e6", "tab", "Transformação logarítmica e janela de treinamento em Itabirito (E6)", "Série total, escala original",
      "Fonte: Elaborado pelos autores (2026). Métricas de todos os dias e horizontes, MAE, RMSE e largura em unidades.")
cp("O experimento E7 avaliou o modelo por produto", ("(Tabela 6)", "({tab:e7})"))
tcopy("e7", "tab", "Configurações do modelo por produto em Itabirito (E7)", "Desagregação, escala original",
      "Fonte: Elaborado pelos autores (2026). Métricas dos dias de loja aberta, MAE e largura em unidades.")
cp("Os experimentos E6 e E7 mostram o caso em que a configuração")
cp("Como a compra é planejada sobre o volume de vários dias, a razão entre o volume previsto",
   ("Foi o que ocorreu nos experimentos E6 e E7, em que", "Foi o que ocorreu nos experimentos E6 e E7, em que"))
cp("O experimento E8 comparou, nas quatro categorias", ("(Tabela 7)", "({tab:e8})"))
tcopy("e8", "tab", "Previsão direta da categoria e desagregação da previsão da loja (E8)", "Erro relativo (desag.)",
      "Fonte: Elaborado pelos autores (2026). Dias de loja aberta, desag.: desagregação, largura expressa em múltiplos da venda média diária.")
cp("Para o total da loja, a soma das previsões diretas das categorias")
cp("O experimento E9 avaliou a ordem de diferenciação", ("A Tabela 8 compara", "A {tab:e9} compara"))
tcopy("e9", "tab", "Critérios de escolha da diferenciação (E9)", "KPSS na janela de ajuste",
      "Fonte: Elaborado pelos autores (2026). 23 séries, treinamento semanal, erro diário dos 7 dias seguintes, de março de 2025 a fevereiro de 2026.")
cp("O experimento E10 avaliou o efeito das datas comemorativas", ("(Tabela 9)", "({tab:e10})"))
tcopy("e10", "tab", "Fator das datas comemorativas em Flores de corte (E10)", "Previsto / vendido na semana da data",
      "Fonte: Elaborado pelos autores (2026). Dias de loja aberta da semana da data, cinco ocorrências por unidade.")
cp("O experimento E11 mediu quanto a previsão piora", ("A Tabela 10 mostra", "A {tab:e11} mostra"))
tcopy("e11", "tab", "Erro e cobertura por semana do horizonte (E11)", "Semana do horizonte",
      "Fonte: Elaborado pelos autores (2026). Oito categorias, mesmos dias-alvo em todas as semanas, dias de loja aberta.")
cp("O experimento E12 avaliou a janela de treinamento e o horizonte", ("A Tabela 11 mostra", "A {tab:e12} mostra"))
tcopy("e12", "tab", "Variação do erro em relação à janela de 365 dias (E12)", "Média das 8 categorias",
      "Fonte: Elaborado pelos autores (2026). MAE dos 14 dias seguintes a cada corte, dias de loja aberta, 51 cortes semanais de março de 2025 a fevereiro de 2026, médias geométricas das razões ao MAE da janela de 365 dias.")
cp("Segundo Pesaran e Timmermann (2007)")
cp("Com a melhor janela de cada série, o erro das categorias subiu")
h2("11.6 Validação da Solução Definitiva")
cp("A solução definitiva foi avaliada pelo próprio treinamento do sistema",
   ("A Tabela 12 apresenta", "A {tab:e13} apresenta"))
tcopy("e13", "tab", "Desempenho da solução definitiva por série (E13)", "JC, Capim dos Texas verde",
      "Fonte: Elaborado pelos autores (2026). ITA: Itabirito, JC: Jardim Canadá. Dias de loja aberta, janelas vencidas de 56, ordem (p,d,q)(P,0,Q) com m = 7.")
cp("Nas oito categorias, o MASE ficou abaixo de 1")
cp("A cobertura e a largura do intervalo de 95% avaliam a faixa provável", ("da Tabela 12", "da {tab:e13}"))
cp("O teste de Ljung-Box não rejeitou")
cp("Em todas as categorias, o volume previsto superou o vendido",
   ("visível também no faturamento mensal da Figura 7", "visível também no faturamento mensal da {fig:inicio}"))
cp("Nos produtos de grama de menor volume, o MASE e o erro relativo")
cp("Essas séries têm padrão intermitente e foram modeladas",
   ("(Seção 3.3)", "(Seção 5.3)"))
cp("No mesmo período de validação e com a mesma base, o treinamento com a janela de 365 dias")
h2("11.7 Comparação com os Objetivos")
p("O {qd:objetivos} retoma os objetivos específicos do Capítulo 4 e indica em que medida cada um foi alcançado.")
tnew("objetivos", "qd", "Alcance dos objetivos específicos",
     ["Objetivo específico", "Situação", "Evidência"],
     [["a) Requisitos levantados e validados", "Alcançado", "Oito reuniões registradas em ata, 12 requisitos funcionais, 5 não funcionais e 8 regras de negócio"],
      ["b) Arquitetura e modelagem definidas", "Alcançado", "Diagramas de casos de uso, atividades, classes e sequência, DER e arquitetura (Capítulo 8)"],
      ["c) ⟨Pipeline⟩ de dados estruturado", "Alcançado", "26 planilhas e 351.092 registros carregados sem duplicatas, com a mesma rotina na importação semanal"],
      ["d) Análise exploratória realizada", "Alcançado", "Padrão de demanda dos produtos, sazonalidade de dia útil e efeito das datas por categoria (Seção 11.4)"],
      ["e) Calendário e datas comemorativas tratados", "Alcançado", "Erro nos feriados próximo de zero e redução do erro da semana das datas em Flores de corte (E2 e E10)"],
      ["f) Modelos treinados", "Alcançado", "23 séries com previsão, ordem pelo AIC e diferenciação escolhida pela validação"],
      ["g) Configurações comparadas", "Alcançado", "Doze experimentos, E1 a E12 (Seção 11.5)"],
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
cp("As escolhas de modelagem com maior efeito medido foram")
cp("Os resultados da solução definitiva não são diretamente comparáveis")
cp("A principal limitação está nas encomendas grandes")
p("Do ponto de vista do software, os resultados positivos são a operação do sistema com os dados reais, a "
  "conferência das planilhas antes da gravação, que evita tratar semanas não enviadas como vendas nulas, e a "
  "rastreabilidade de cada carga e de cada treinamento. Permanecem como dificuldades a dependência da extração "
  "manual dos relatórios, que mantém a base com vendas até fevereiro de 2026, o treinamento fora da API "
  "publicada, que exige um ⟨script⟩ executado pela equipe técnica enquanto o serviço de hospedagem for o plano "
  "gratuito, e o defeito de duplicidade dentro da mesma planilha. As decisões de projeto que mais influenciaram "
  "os resultados foram a separação das encomendas grandes, o modelo próprio de cada categoria e de cada produto "
  "de grama e a preservação da previsão mais antiga de cada dia, que permite à empresa medir o erro com a "
  "antecedência com que planeja a compra. As melhorias possíveis estão listadas como trabalhos futuros no "
  "Capítulo 12.")

# =====================================================================================
h1("12 CONCLUSÃO E TRABALHOS FUTUROS")
p("Este trabalho desenvolveu um sistema de previsão de vendas para a Floricultura Verde Perto, que transforma o "
  "histórico de vendas, antes disponível apenas em relatórios do sistema de gestão, em previsões diárias, em "
  "horizontes de duas semanas a três meses, por categoria e por produto de grama de cada unidade, acompanhadas de "
  "intervalo de 95% e de indicadores de desempenho. A solução reúne um ⟨pipeline⟩ de preparação dos dados, "
  "modelos SARIMAX com regressores exógenos de calendário, validados por " + WF + " a cada treinamento, e um "
  "painel que apresenta a previsão, o histórico das previsões, as análises das vendas e relatórios a usuários "
  "não técnicos.")
p("O objetivo geral foi alcançado, assim como os objetivos específicos, com exceção da documentação para o "
  "usuário final e da verificação formal da usabilidade, alcançadas parcialmente. A sequência de experimentos "
  "permitiu medir o efeito de cada escolha de modelagem e fundamentou a configuração final, e mostrou que a "
  "melhor configuração em uma métrica isolada não é necessariamente a mais adequada ao uso do sistema, pois a "
  "compra é planejada sobre o volume de vários dias.")
p("Como contribuições, o trabalho oferece à empresa uma base quantitativa para as compras, integrada à sua rotina "
  "de exportação das planilhas, e um registro das previsões que permite avaliar a confiança nas estimativas ao "
  "longo do tempo. Do ponto de vista acadêmico, os resultados indicam que modelos estatísticos de séries temporais "
  "com regressores de calendário são aplicáveis à previsão diária de uma floricultura quando a demanda é agregada "
  "em séries densas e as encomendas de grande porte são tratadas à parte, em linha com os ganhos relatados por "
  "Arunraj, Ahrens e Fernandes (2016) no varejo alimentar.")
p("Entre as limitações, destacam-se as encomendas grandes, não previstas pelos modelos, o histórico de 26 meses, "
  "insuficiente para estimar a sazonalidade anual, a validação da solução final restrita às oito semanas mais "
  "recentes, a ausência dos testes de usabilidade e da medição do efeito do sistema sobre perdas e rupturas e a "
  "base de vendas encerrada em fevereiro de 2026.")
p("Como trabalhos futuros, propõem-se:")
ul("verificar formalmente a usabilidade do sistema com a gestora de compras da entidade parceira, com tarefas e "
   "instrumento padronizado, e elaborar o manual do usuário,",
   "corrigir a verificação de duplicidade para detectar notas repetidas dentro da mesma planilha,",
   "integrar ao sistema a informação antecipada das encomendas grandes, como pedidos já negociados, e calibrar com "
   "a entidade parceira o limiar que as define,",
   "reavaliar a janela de treinamento à medida que novos dados forem incorporados, com base no histórico das "
   "previsões, e oferecer, além da previsão pontual, uma quantidade de referência baseada em um quantil superior "
   "da distribuição prevista, com nível definido pela empresa,",
   "estender a previsão por produto à categoria Flores de corte, conforme solicitado pela entidade parceira, e "
   "comparar, nos produtos de demanda intermitente, os métodos específicos para esse padrão (Seção 5.3),",
   "comparar o desempenho dos modelos estatísticos com redes neurais artificiais e com métodos de ⟨ensemble⟩ "
   "baseados em árvores de decisão,",
   "incorporar a sazonalidade anual à medida que o histórico de vendas se ampliar,",
   "implementar a identificação de produtos comprados em conjunto e a simulação de promoções e de vendas "
   "conjugadas, solicitadas pela entidade parceira,",
   "avaliar, após a implantação, o efeito do uso do sistema sobre as perdas por descarte e sobre as rupturas de "
   "estoque.")
p("Por fim, o trabalho mostrou que o histórico de vendas que a empresa já possuía, quando organizado e combinado "
  "com o calendário de cada loja, pode orientar as compras de produtos perecíveis com estimativas avaliadas e "
  "acompanhadas ao longo do tempo, o que reforça a importância de levar métodos de previsão a pequenas empresas "
  "do varejo, que raramente dispõem de ferramentas desse tipo.")

# =====================================================================================
h1("REFERÊNCIAS")
REFS = ["ARUNRAJ, N. S.", "BARTEZZAGHI, E.", "BOX, G. E. P.", "BRASIL. Lei", "BREIMAN, L.", "CHEN, C.",
        "CROSTON, J. D.", "DIEBOLD, F. X.", "FLIEDNER, G.", "GROSS, C. W.", "HOLM, S.", "HUBER, J.",
        "HYNDMAN, R. J.; ATHANASOPOULOS", "HYNDMAN, R. J.; KOEHLER", "IGLEWICZ, B.", "KALCHSCHMIDT, M.",
        "KWIATKOWSKI, D.", "MAKRIDAKIS, S.", "PESARAN, M. H.", "PRESSMAN, R. S.", "SCHWERT, G. W.",
        "SOMMERVILLE, I.", "SYNTETOS, A. A.; BOYLAN, J. E. The", "SYNTETOS, A. A.; BOYLAN, J. E.; CROSTON",
        "TAYLOR", "TEUNTER, R. H.", "WIRTH, R.", "ZOTTERI, G."]
for r in REFS:
    if r == "TAYLOR":
        B.append(("ref_new", "TAYLOR, S. J.; LETHAM, B. Forecasting at scale. ⟪The American Statistician⟫, [⟨S. l.⟩], "
                             "v. 72, n. 1, p. 37-45, 2018."))
    else:
        B.append(("ref_copy", r))

# =====================================================================================
h1("APÊNDICE A – ATAS DAS REUNIÕES COM A ENTIDADE PARCEIRA")
p("Este apêndice reúne as atas das oito reuniões realizadas com a Floricultura Verde Perto, registradas no "
  "Formulário de Registro de Reuniões com Entidade. Todas as reuniões foram realizadas de forma remota, pela "
  "plataforma Google Meet. O {qd:atas} resume o assunto de cada reunião, e as atas completas são apresentadas a "
  "seguir.")
tnew("atas", "qd", "Reuniões com a entidade parceira",
     ["Reunião", "Data", "Assuntos principais"],
     [["01", "24/03/2026", "Levantamento inicial das necessidades, origem dos dados, atualização semanal e datas comemorativas"],
      ["02", "24/03/2026", "Relatório de contas a receber, histórico de cerca de dois anos das três empresas e horizonte de previsão"],
      ["03", "26/05/2026", "Apresentação do protótipo inicial da interface e definição dos requisitos da versão final"],
      ["04", "02/06/2026", "Prova de conceito do modelo de previsão e protótipo das telas iniciais"],
      ["05", "13/10/2026", "Sistema em desenvolvimento, envio de planilhas por unidade e classificação dos produtos em quatro categorias"],
      ["06", "20/10/2026", "Previsão diária com faixa provável, histórico de acertos, encomendas grandes e previsão por produto de grama"],
      ["07", "03/11/2026", "Publicação do sistema, período da base de vendas e validação do calendário das lojas"],
      ["08", "10/11/2026", "Apresentação do sistema final"]],
     [1300, 1500, 6272], F_ENT, "grade", ["center", "center", "left"])
ATAS = [("01", 5), ("02", 5), ("03", 5), ("04", 5), ("05", 6), ("06", 6), ("07", 6), ("08", 6)]
for num_ata, npag in ATAS:
    B.append(("center", f"Ata da Reunião {num_ata}", True, True))
    for k in range(1, npag + 1):
        B.append(("img_page", os.path.join(IMG, f"ata{num_ata}_{k}.jpg"), 14.5))

h1("APÊNDICE B – ESPECIFICAÇÃO DOS CASOS DE USO")
p("O {qd:uc} especifica os casos de uso do diagrama da Seção 8.1. Em todos eles, o usuário deve estar autenticado, "
  "e os casos de uso de envio de planilha e de treinamento exigem o perfil de administrador.")
tnew("uc", "qd", "Especificação dos casos de uso",
     ["Caso de uso", "Ator", "Fluxo principal", "Requisitos"],
     [["UC01 – Enviar planilha de vendas", "Administrador", "Seleciona o arquivo, o sistema executa o UC02, o administrador confirma e o sistema grava as vendas novas e marca as encomendas grandes. Planilha já gravada é recusada", "RF01, RN05, RN07, RN08"],
      ["UC02 – Conferir planilha antes de gravar (incluído no UC01)", "Sistema", "Lê a planilha sem gravar e apresenta o período de cada unidade, as vendas novas e já carregadas, as linhas ignoradas e os dias de loja aberta sem venda", "RF07"],
      ["UC03 – Treinar previsões", "Administrador", "Solicita o treinamento, o sistema verifica se os dados mudaram e, sem mudança, registra o pedido como dispensado. Com mudança, executa o UC04 para cada série e grava a previsão e o histórico", "RF03, RF09, RN02, RN04"],
      ["UC04 – Validar e treinar cada série (incluído no UC03)", "Sistema", "Seleciona a ordem pelo AIC, executa a validação com d = 0 e d = 1, mantém o de menor erro, ajusta o modelo final, prevê 91 dias e aplica o fator das datas comemorativas", "RF02, RN01, RN06"],
      ["UC05 – Consultar previsão diária", "Administrador e consulta", "Escolhe o horizonte, a unidade e a categoria ou o produto de grama e consulta a previsão de cada dia com a faixa provável", "RF02, RF04"],
      ["UC06 – Consultar histórico da previsão", "Administrador e consulta", "Escolhe a unidade, a categoria ou o produto e o período e compara o previsto com o vendido", "RF08, RN03"],
      ["UC07 – Consultar análises de vendas", "Administrador e consulta", "Escolhe a unidade e consulta os indicadores, os gráficos e os produtos mais vendidos", "RF05, RF06"],
      ["UC08 – Conferir vendas importadas", "Administrador e consulta", "Busca e filtra as vendas gravadas, consulta a nota completa e exporta o resultado", "RF11"],
      ["UC09 – Receber notificações", "Administrador e consulta", "Consulta os avisos sobre a base de vendas e, no perfil de administrador, o andamento e o resultado do treinamento", "RF09"],
      ["UC10 – Exportar relatórios", "Administrador e consulta", "Escolhe o relatório, a unidade e o formato, Excel, CSV ou PDF, e obtém o arquivo", "RF10"]],
     [2300, 1500, 3972, 1300], F_AUT, "grade", ["left", "left", "left", "left"])

h1("APÊNDICE C – DICIONÁRIO DE DADOS DO RELATÓRIO DE VENDAS")
p("O {qd:dicionario} descreve os campos extraídos do relatório de contas a receber exportado do sistema de gestão "
  "da empresa e o uso de cada um no sistema. Os nomes são os adotados no ⟨pipeline⟩ de dados.")
tnew("dicionario", "qd", "Campos do relatório de contas a receber",
     ["Campo", "Descrição", "Uso no sistema"],
     [["doc_tipo", "Tipo do documento de venda, como cupom ou nota fiscal", "Gravado, filtro por tipo de documento"],
      ["doc_numero", "Número do documento", "Gravado, identifica a venda e compõe a verificação de duplicidade"],
      ["pagamento", "Forma de pagamento", "Gravado, análise das formas de pagamento"],
      ["emissao", "Data de emissão do documento", "Gravado, eixo das séries diárias"],
      ["operador", "Usuário do caixa", "Não gravado"],
      ["cliente_cod", "Código do cliente", "Não gravado, gera apenas o indicador de cliente cadastrado"],
      ["cliente_nome", "Nome ou razão social do cliente", "Não gravado (dado pessoal)"],
      ["empresa", "Empresa emissora do documento", "Convertido na unidade operacional"],
      ["vendedor", "Vendedor que atendeu", "Não gravado"],
      ["obs", "Observação digitada na venda", "Não gravado"],
      ["produto_cod", "Código do produto", "Gravado, catálogo e séries por produto"],
      ["produto_nome", "Descrição do produto", "Gravado no catálogo, base da classificação da categoria"],
      ["qtdade", "Quantidade vendida, negativa nas devoluções", "Gravado, variável prevista"],
      ["vl_unit", "Preço unitário", "Gravado, análises"],
      ["vl_total", "Valor da linha antes do desconto", "Gravado, verificação de duplicidade e análises"],
      ["vl_desconto", "Desconto aplicado à linha", "Gravado, análises"],
      ["tot_liq", "Valor líquido da linha", "Gravado, faturamento"],
      ["icms_ret", "ICMS retido, igual a zero em toda a base", "Não gravado"],
      ["total_liquido_doc", "Total líquido do documento", "Conferência da integridade na carga"],
      ["arquivo_origem", "Nome do arquivo de origem", "Registrado com a planilha importada"]],
     [2072, 3800, 3200], F_AUT, "grade", ["left", "left", "left"])

h1("ANEXO A – TELAS DO SISTEMA DE GESTÃO DA EMPRESA")
p("As telas a seguir foram compartilhadas pela entidade parceira em reunião, em março de 2026, e mostram o sistema "
  "de gestão utilizado pela empresa. A {fig:erp_filtro} apresenta a seleção do relatório de contas a receber por "
  "grupo de produto, e a {fig:erp_relatorio}, o relatório de recebimento por grupo de produto. O nome do usuário "
  "do sistema foi ocultado.")
fig("erp_filtro", os.path.join(IMG, "erp_filtro.png"), 15.5, "Filtro do relatório de contas a receber por grupo de produto",
    "Fonte: Floricultura Verde Perto (2026).")
fig("erp_relatorio", os.path.join(IMG, "erp_relatorio.png"), 15.5, "Relatório de recebimento por grupo de produto",
    "Fonte: Floricultura Verde Perto (2026).")

BLOCKS = B
PG_START = 12
