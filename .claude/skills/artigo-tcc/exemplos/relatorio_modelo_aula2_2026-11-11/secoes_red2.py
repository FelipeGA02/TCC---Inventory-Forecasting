#@@ cap5
h1("5 REFERENCIAL TEÓRICO")
p("Este capítulo apresenta, nas Seções 5.1 a 5.6, a fundamentação teórica sobre o problema e sobre a solução "
  "e, na Seção 5.7, as soluções correlatas, com a diferença entre elas e a solução desenvolvida.")
h2("5.1 Previsão de demanda e modelos estatísticos de séries temporais")
cp("A previsão de demanda é tema consolidado na análise de séries temporais")
cp("Entre os modelos estatísticos de séries temporais, destacam-se")
cp("Uma decisão de especificação particularmente relevante para séries diárias")
h2("5.2 Variáveis exógenas de calendário")
cp("As variáveis exógenas de um modelo de previsão precisam ter valores conhecidos",
   ("o que orienta a seleção de variáveis feita neste trabalho", "o que orienta a seleção das variáveis do modelo"))
h2("5.3 Demanda intermitente e nível de agregação")
cp("A demanda é intermitente quando a maior parte dos períodos não registra venda")
cp("Quando as séries individuais são esparsas, a previsão hierárquica organiza")
h2("5.4 Tratamento de observações atípicas")
cp("Observações atípicas distorcem a estimação dos parâmetros")
h2("5.5 Métricas de avaliação de previsões")
cp("Para a avaliação de previsões, Hyndman e Koehler (2006) propuseram")
p("Para verificar se a diferença de erro entre duas previsões da mesma série é estatisticamente significativa, "
  "aplica-se o teste de Diebold e Mariano (1995), válido para erros autocorrelacionados, e, quando o teste é "
  "repetido em muitas séries, o procedimento de Holm (1979) ajusta os valores-p para controlar a probabilidade de "
  "ao menos um falso positivo no conjunto.")
h2("5.6 Processo de desenvolvimento de software e de análise de dados")
p("A engenharia de software organiza o desenvolvimento em atividades de especificação, projeto, implementação, "
  "validação e evolução, que podem ser conduzidas de forma sequencial ou iterativa (SOMMERVILLE, 2018). Nos "
  "modelos iterativos e incrementais, o sistema é entregue em partes funcionais, avaliadas pelo cliente a cada "
  "ciclo, e a separação entre a lógica de domínio e os mecanismos de entrada e saída favorece os testes isolados e "
  "a manutenção do código (PRESSMAN; MAXIM, 2021). Em projetos de análise de dados, o modelo ⟨Cross-Industry "
  "Standard Process for Data Mining⟩ (CRISP-DM) organiza o trabalho nas fases de compreensão do negócio, "
  "compreensão dos dados, preparação dos dados, modelagem, avaliação e implantação, percorridas de forma cíclica "
  "(WIRTH; HIPP, 2000).")
h2("5.7 Soluções correlatas")
p("Arunraj, Ahrens e Fernandes (2016) aplicaram um modelo sazonal autorregressivo integrado de médias móveis com "
  "regressores exógenos à previsão das vendas diárias no varejo de alimentos e mostraram que as variáveis de "
  "calendário e de promoção reduzem o erro em relação ao modelo sem regressores, e Huber, Gossmann e Stuckenschmidt "
  "(2017) trataram a demanda de produtos perecíveis com previsão hierárquica, prevendo em níveis agregados as séries "
  "de venda esparsa. Entre as ferramentas de mercado, a biblioteca Prophet, de código aberto, ajusta modelos "
  "aditivos com tendência, sazonalidades e feriados e foi concebida para que analistas sem formação específica em "
  "séries temporais produzam previsões em escala (TAYLOR; LETHAM, 2018), mas exige preparar os dados e manter o "
  "código. O sistema de gestão da entidade parceira registra as vendas, mas não estima a demanda futura "
  "(Seção 2.1). O {qd:correlatas} compara essas soluções com a desenvolvida neste trabalho.")
tnew("correlatas", "qd", "Soluções correlatas e solução desenvolvida",
     ["Solução", "Abordagem", "Limitação para o problema da entidade"],
     [["Arunraj, Ahrens e Fernandes (2016)", "Modelo sazonal com regressores de calendário e promoção, vendas diárias do varejo de alimentos", "Estudo de método, sem ferramenta para a carga dos dados e a consulta pela empresa"],
      ["Huber, Gossmann e Stuckenschmidt (2017)", "Previsão hierárquica de produtos perecíveis, com agrupamento dos itens", "Estudo de método, sem ferramenta para a carga dos dados e a consulta pela empresa"],
      ["Prophet (TAYLOR; LETHAM, 2018)", "Modelo aditivo com tendência, sazonalidades e feriados", "Biblioteca de programação, que exige preparo dos dados e manutenção do código"],
      ["Sistema de gestão da entidade", "Registro das vendas e emissão de relatórios", "Não estima as vendas futuras"],
      ["Solução desenvolvida", "Modelo estatístico com regressores de calendário por categoria e por produto de grama de cada loja, encomendas grandes à parte e ajuste das datas comemorativas", "Sistema ⟨web⟩ com carga semanal das planilhas, validação a cada treinamento e histórico das previsões"]],
     [2400, 3400, 3272])
p("A solução desenvolvida diferencia-se dessas abordagens por reunir, em um sistema de uso da própria empresa, a "
  "carga das planilhas que ela já exporta, o treinamento dos modelos a cada nova carga, com a validação registrada "
  "em cada série, a consulta das previsões por usuários não técnicos e o histórico das previsões, que permite à "
  "empresa acompanhar o erro com a antecedência com que planeja a compra.")

#@@ cap6b
h2("6.2 Levantamento e Análise de Requisitos")
p("Os requisitos foram levantados em oito reuniões remotas com a entidade parceira, pela plataforma Google Meet, "
  "entre março e novembro de 2026, com a participação das duas sócias administrativas proprietárias da empresa, "
  "de um auxiliar administrativo e dos dois desenvolvedores. Cada reunião foi registrada no Formulário de Registro "
  "de Reuniões com Entidade fornecido pela instituição, com a pauta, as decisões, as solicitações do cliente e as "
  "pendências. As duas primeiras reuniões levantaram as necessidades do negócio, a origem dos dados e o horizonte "
  "de previsão desejado, e as seguintes apresentaram o protótipo, os resultados preliminares do modelo e as versões "
  "do sistema, a partir das quais os requisitos foram revistos e validados pela empresa.")
p("O levantamento foi complementado pela análise documental dos relatórios de vendas exportados do sistema de "
  "gestão, pela observação das telas desse sistema, compartilhadas pela empresa em reunião (Anexo A), e pela "
  "inspeção das planilhas de janeiro de 2024 a fevereiro de 2026. Os requisitos foram consolidados em requisitos "
  "funcionais, não funcionais, regras de negócio e atores, apresentados no Capítulo 7.")
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
   "bancos de dados: PostgreSQL, no serviço Neon, na produção, e ⟨SQLite⟩, no desenvolvimento e nos testes,",
   "testes: ⟨pytest⟩, para os testes unitários e de integração, e Playwright, para os testes de ponta a ponta,",
   "ambiente de desenvolvimento: Visual Studio Code, no sistema operacional Windows 11,",
   "ambiente operacional: aplicação ⟨web⟩, acessada pelo navegador, com a API em contêiner Docker sobre Linux,",
   "versionamento: ⟨Git⟩, com o repositório hospedado no ⟨GitHub⟩.")
h2("6.4 Ferramentas de Modelagem")
p("A modelagem utilizou a linguagem ⟨Unified Modeling Language⟩ (UML), com os diagramas de casos de uso, de "
  "atividades, de classes e de sequência, complementados pelo Diagrama Entidade-Relacionamento (DER) e por um "
  "diagrama da arquitetura lógica, apresentados no Capítulo 8. Os diagramas foram descritos em texto, na linguagem "
  "DOT, e renderizados com a ferramenta Graphviz, o que permite versioná-los com o código, exceto o de sequência, "
  "desenhado em Python com a biblioteca ⟨matplotlib⟩. O protótipo das telas foi construído na ferramenta Figma "
  "(Capítulo 9).")
h2("6.5 Preparação dos Dados e Modelo Preditivo")
p("A preparação dos dados é realizada por um ⟨pipeline⟩ de sete etapas, executado também pelo sistema a cada "
  "planilha enviada: extração de uma linha por produto de cada documento do relatório de contas a receber, com "
  "deduplicação entre arquivos e controle por ⟨hash⟩ de cada planilha, padronização de textos, datas e valores, "
  "derivação da unidade e da categoria de cada produto, remoção dos lançamentos de serviços e taxas, separação das "
  "vendas por unidade, separação das encomendas grandes e construção do calendário diário de cada unidade, com "
  "feriados nacionais obtidos da BrasilAPI, fechamentos observados e aberturas excepcionais. A base não armazena "
  "nome, documento ou código dos clientes e registra apenas se a venda foi feita a cliente cadastrado. As três "
  "empresas do grupo foram consolidadas em duas unidades, Jardim Canadá, que reúne a floricultura e o ⟨garden "
  "center⟩, e Itabirito, e os produtos, em quatro categorias, Grama, Plantas diversas, Produtos de jardim e Flores "
  "de corte, classificadas pela descrição dos produtos.")
p("Uma venda, identificada pela unidade, pela data e pelo número do documento, é classificada como encomenda grande "
  "quando a soma das quantidades de seus itens supera o limiar da unidade, igual à média mais quatro "
  "desvios-padrão da quantidade de todos os pedidos da loja (IGLEWICZ; HOAGLIN, 1993), recalculado a cada planilha "
  "enviada. Os itens desses documentos formam um fluxo à parte, apresentado separadamente no painel, e o restante, "
  "o fluxo diário, é a série prevista pelos modelos. Segundo a entidade parceira, essas vendas correspondem a "
  "pedidos de empresas preparados com antecedência junto aos fornecedores.")
p("O modelo adotado é o SARIMAX, estimado com a biblioteca ⟨statsmodels⟩, que combina em um único modelo a "
  "dependência das vendas em relação aos dias anteriores, a sazonalidade semanal e o efeito de regressores "
  "exógenos, variáveis externas à série cujos valores futuros são conhecidos no momento da previsão, como saber que "
  "um dia será domingo, feriado ou dia de abertura excepcional da loja. Uma regressão linear com as mesmas variáveis "
  "ignoraria a dependência entre dias consecutivos, e modelos de aprendizado de máquina exigiriam um histórico maior "
  "que os 26 meses disponíveis (MAKRIDAKIS; SPILIOTIS; ASSIMAKOPOULOS, 2020). O modelo também produz um intervalo "
  "de previsão para cada dia, apresentado ao usuário como a faixa provável de venda.")
p("Cada uma das quatro categorias de cada unidade e cada produto de grama tem a sua série diária, sem as "
  "encomendas grandes, e o seu próprio modelo, e a previsão total da unidade é a soma das previsões das categorias, "
  "inclusive dos limites do intervalo. A previsão por produto foi restrita à grama porque a empresa compra esses "
  "itens produto a produto e porque os demais produtos vendem de forma esporádica (Seção 11.4). Uma série só é "
  "modelada quando dispõe de pelo menos 180 dias de histórico antes do período de validação e, no caso de produto, "
  "quando registra venda em pelo menos 28 dos 365 dias mais recentes.")
p("Na notação SARIMAX(p, d, q)(P, D, Q)m, p é o número de termos autorregressivos, isto é, de dias anteriores da "
  "própria série usados na previsão, d é a ordem da diferenciação regular, q é o número de termos de médias móveis, "
  "isto é, de erros recentes usados para corrigir a previsão, e P, D e Q são os equivalentes na escala sazonal, de "
  f"período m. Com d{NB}={NB}0, o modelo trabalha com o nível das vendas e inclui uma constante, e a previsão "
  f"converge para a média do período de treinamento. Com d{NB}={NB}1, trabalha com a variação de um dia para o "
  f"seguinte, e a previsão parte do nível recente das vendas. A sazonalidade é semanal (m{NB}={NB}7), sem "
  f"diferenciação sazonal (D{NB}={NB}0).")
p("Os valores de p e q são testados entre 0 e 2, e os de P e Q entre 0 e 1, em 36 combinações, e, para cada valor "
  "de d, fica a combinação de menor AIC, ajustada apenas na janela anterior ao período de validação. A ordem de "
  "diferenciação é escolhida em cada série pela validação " + WF + f", executada com d{NB}={NB}0 e com "
  f"d{NB}={NB}1, e fica o valor de menor erro absoluto médio nos dias de loja aberta (E5). As variáveis exógenas "
  "são seis indicadores de dia da semana, de segunda-feira a sábado, um indicador de loja fechada, que reúne "
  "domingos, feriados nacionais e fechamentos observados, e um indicador de abertura excepcional, que representa os "
  "dias de Dia das Mães e de Finados em que a unidade de Itabirito abre (E1). O modelo é ajustado sobre uma janela "
  "deslizante com os 545 dias mais recentes (E8), e a previsão pontual corresponde à média da distribuição prevista "
  "na escala original (E3), truncada em zero e acompanhada do intervalo de 95%. Nos dias de loja fechada, a "
  "previsão e o intervalo são iguais a zero.")
p("O efeito das datas comemorativas é aplicado depois do ajuste do modelo, porque é proporcional ao nível das "
  "vendas e cada data aparece no máximo duas vezes na janela de treinamento. A previsão e os limites do intervalo "
  "dos dias de loja aberta, de seis dias antes da data até ela, são multiplicados por um fator recalculado a cada "
  "treinamento, a razão entre a venda e a mediana do mesmo dia da semana nas quatro semanas anteriores e nas quatro "
  "posteriores, nas últimas três ocorrências da data. Em Flores de corte, nas semanas do Dia da Mulher, do Dia das "
  "Mães, do Dia dos Namorados, do Natal e do Ano-Novo, aplica-se metade do aumento medido, com multiplicador entre 1 "
  "e 3. Nas demais séries, de 26 a 31 de dezembro e na semana do Dia do Trabalho, aplica-se a queda inteira, com "
  "piso de 0,2, apenas quando cada uma das últimas ocorrências, no mínimo duas, ficou em até 0,8 de uma semana comum "
  "(E6).")
p("O treinamento prevê e grava os 91 dias seguintes à última venda, e o usuário escolhe na tela o horizonte "
  "exibido, de duas semanas a três meses, enquanto a validação permanece com horizonte de 14 dias, que corresponde à "
  "decisão de compra da semana (E7). A previsão de cada dia é preservada depois que o dia passa, em um histórico que "
  "guarda a previsão mais antiga feita para ele, até 14 dias antes, para que a comparação com o vendido reflita a "
  "antecedência com que a loja planeja a compra. Os experimentos que definiram cada escolha, identificados entre "
  "parênteses nesta seção, são apresentados na Seção 11.5.")
h2("6.6 Procedimentos de Testes e Validação")
p("Os testes unitários verificam a lógica de domínio isolada, como a seleção da ordem, a escolha da "
  "diferenciação, as métricas, o fator das datas e a regra do histórico das previsões, os testes de integração "
  "exercitam a API com o banco de dados, como a autenticação, os perfis de acesso, o envio de planilhas, o "
  "treinamento e as respostas do painel, e os testes de ponta a ponta, escritos com a ferramenta Playwright, executam "
  "o painel no navegador conectado à API. Os testes de aceitação foram realizados com a entidade parceira, nas "
  "demonstrações do protótipo e das versões do sistema.")
p("O desenvolvimento usa a máquina de cada desenvolvedor, com um banco ⟨SQLite⟩ local, e os testes automatizados "
  "criam a cada execução um banco ⟨SQLite⟩ temporário ou, nos de ponta a ponta, uma base sintética de vendas. A "
  "homologação utiliza uma cópia da base real em ⟨SQLite⟩ local, na qual o treinamento completo e a importação de "
  "planilhas são conferidos antes de serem executados na produção, formada pelo banco PostgreSQL no serviço Neon e "
  "pela configuração de publicação da API no serviço Render e do painel no serviço Vercel.")
p("A validação estatística dos modelos é a validação " + WF + " executada a cada treinamento: a origem avança um "
  "dia por vez nas 56 datas mais recentes com 14 dias de vendas conhecidas, e, em cada origem, o modelo é reajustado "
  "nos 545 dias anteriores e prevê os 14 dias seguintes. As métricas, calculadas nos dias de loja aberta, são o erro "
  "absoluto médio (⟨Mean Absolute Error⟩ – MAE), em unidades por dia, o erro percentual absoluto ponderado "
  "(⟨Weighted Absolute Percentage Error⟩ – WAPE), que expressa o erro como percentual do volume vendido, o MASE e o "
  "erro relativo à previsão ingênua, que repete as vendas do mesmo dia da semana anterior, a razão entre o volume "
  "previsto e o vendido e a cobertura e a largura do intervalo de 95%. Um MASE inferior a 1 indica que o modelo erra "
  "menos do que a previsão ingênua, e uma cobertura próxima de 95% indica que a faixa contém a venda na proporção "
  "esperada. Os resíduos do ajuste final de cada modelo são avaliados pelos testes de Ljung-Box, que verifica se os "
  "erros guardam relação com os dos dias anteriores, e de Shapiro-Wilk, que verifica a normalidade, como diagnóstico "
  "complementar. Na validação funcional, todos os testes automatizados devem ser aprovados antes da incorporação de "
  "uma mudança, e o treinamento de produção deve terminar em menos de duas horas (RNF03). Com a entidade parceira, a "
  "validação é a aceitação das funcionalidades nas reuniões de demonstração.")

#@@ cap92
h2("9.2 Protótipos de Interface")
p("O protótipo reunia sete telas: Início, Carregar Planilha, Conferir Dados, Previsão de Compras, Produtos para "
  "Repor, Simular Promoções e Baixar Relatórios. A tela Previsão de Compras ({fig:p_previsao}) apresentava, para um "
  "produto e uma unidade, as vendas das semanas anteriores, a estimativa das semanas seguintes com a margem de "
  "variação, indicadores de erro, um aviso de data comemorativa e a quantidade a comprar por semana, com os dados "
  "fictícios do protótipo.")
fig("p_previsao", os.path.join(IMG, "p_previsao.jpg"), 13.5, "Protótipo: previsão de compras", F_AUT)

#@@ cap1016
h3("10.1.6 Análise das vendas e relatórios")
p("O objetivo é apresentar as vendas da base e levar a previsão para fora do sistema (RF05, RF06, RF10 e RF11). Os "
  "resumos de vendas não são gravados: a API os calcula a partir da tabela sales a cada consulta, e a conferência "
  "das vendas consulta as linhas gravadas com paginação, busca e filtros. Os relatórios são montados no navegador, "
  "a partir dos dados da API: as planilhas Excel e os arquivos CSV são gerados pelo próprio painel, e os relatórios "
  "em PDF, como o relatório gerencial, pela impressão do navegador.")

#@@ cap102
h2("10.2 Interfaces Desenvolvidas")
p("O painel organiza as funcionalidades em cinco telas acessíveis pelo menu lateral, Início, Carregar Planilha, "
  "Conferir Dados, Previsão de Vendas e Relatórios, além da tela de login. No cabeçalho, ficam o botão Treinar "
  "previsões, visível apenas ao administrador, e o painel de notificações, que informa o andamento e o resultado do "
  "treinamento. As telas foram capturadas do sistema em execução local, conectado ao banco de dados de produção, "
  "com as vendas até 28 de fevereiro de 2026.")
p("A tela inicial ({fig:inicio}) apresenta a visão geral das vendas, com filtro de unidade, indicadores de "
  "faturamento, notas, quantidade vendida e encomendas grandes e o faturamento mensal, que separa a venda do dia a "
  "dia das encomendas grandes. Mais abaixo, a tela apresenta o faturamento por dia da semana, a participação das "
  "categorias, a comparação entre consumidores e clientes cadastrados, as formas de pagamento e os produtos mais "
  "vendidos, sem dados pessoais de clientes.")
fig("inicio", os.path.join(IMG, "t_inicio_top.png"), 13.0, "Parte superior da tela inicial", F_TELA)
p("A tela Carregar Planilha conduz a importação em quatro etapas, envio do arquivo, conferência, gravação e "
  "conclusão. Na conferência ({fig:conferencia}), a tela apresenta o período de cada unidade, os totais de vendas "
  "novas, já carregadas e linhas ignoradas e o aviso dos dias de loja aberta sem venda, antes de o administrador "
  "confirmar a gravação. No exemplo, foi conferida, sem gravação, uma planilha de teste com vendas fictícias de "
  "março de 2026. A tela Conferir Dados permite consultar as vendas gravadas, com busca, filtros e exportação.")
fig("conferencia", os.path.join(IMG, "t_conferencia.png"), 13.0, "Conferência da planilha antes da gravação", F_TELA)
p("Na tela Previsão de Vendas ({fig:previsao}), a caixa Horizonte define o período exibido, de duas semanas a três "
  "meses, o quadro de feriados e datas comemorativas lista as datas do período, e o gráfico mostra a venda das "
  "semanas anteriores e a previsão de cada categoria da unidade escolhida ou de cada produto de grama. Abaixo do "
  "gráfico, a tabela Dia a dia apresenta a quantidade prevista em cada dia e, ao passar o cursor, a faixa provável. "
  "A aba Histórico de previsão ({fig:historico}) compara o vendido em cada dia com a previsão mais antiga feita para "
  "ele e resume a validação do último treinamento no erro médio por dia e na margem de incerteza.")
fig("previsao", os.path.join(IMG, "t_previsao_top.png"), 13.0, "Previsão diária por categoria no horizonte escolhido", F_TELA)
fig("historico", os.path.join(IMG, "t_historico.png"), 13.0, "Histórico da previsão: vendido e previsto", F_TELA)
p("A tela Relatórios ({fig:relatorios}) reúne os relatórios para baixar, com filtro de unidade, como o relatório "
  "gerencial em PDF, as previsões diárias por categoria e por produto de grama, o histórico de vendas, as "
  "encomendas grandes e o acerto da previsão de cada série, nos formatos Excel e PDF.")
fig("relatorios", os.path.join(IMG, "t_relatorios.png"), 12.0, "Tela de relatórios", F_TELA)
h2("10.3 Integração entre Componentes")
p("O painel comunica-se com a API por requisições HTTP no padrão REST (⟨Representational State Transfer⟩), com dados "
  "em JSON, definidas no contrato OpenAPI do projeto. O cliente HTTP do painel acrescenta o ⟨token⟩ de acesso a cada "
  "requisição e, quando ele expira, obtém um novo com o ⟨token⟩ de renovação e repete a requisição. No perfil de "
  "administrador, o painel consulta o andamento do treinamento a cada três segundos durante a execução e atualiza as "
  "telas quando o treinamento termina.")
p("A API acessa o banco por meio do ⟨SQLAlchemy⟩, que permite ao mesmo código operar sobre o PostgreSQL e sobre o "
  "⟨SQLite⟩, conforme o endereço configurado. Como o serviço Neon suspende o banco ocioso, as conexões são "
  "verificadas antes do uso, e as gravações do treinamento são repetidas em caso de falha temporária. Em execução, a "
  "API não depende de serviços externos: os feriados, obtidos da BrasilAPI no pré-processamento, ficam na tabela de "
  "calendário. O serviço de previsão é chamado pela API em segundo plano ou por um ⟨script⟩ que executa o mesmo "
  "treinamento sobre o mesmo banco, forma utilizada na produção, porque o plano gratuito do serviço de hospedagem da "
  "API não comporta o treinamento. Nos dois casos, as séries são distribuídas entre processos paralelos.")
h2("10.4 Dificuldades Encontradas")
p("Durante a implementação, foram enfrentadas as dificuldades descritas a seguir, com a solução adotada em cada "
  "caso:")
ul("formato dos dados: as vendas chegam em relatórios organizados em blocos por documento, com cabeçalho, itens e "
   "totais, o que exigiu um leitor próprio para extrair uma linha por produto e conferir a soma dos itens com o total "
   "de cada documento,",
   "classificação dos produtos: o relatório não informa o grupo de cada produto, e a classificação pela descrição "
   "gerava erros, corrigidos por uma revisão produto a produto e por um ⟨script⟩ que reaplica as regras ao catálogo "
   "sem apagar dados,",
   "limitação do ambiente de publicação: o plano gratuito do serviço de hospedagem da API dispõe de 512 MB de "
   "memória, insuficientes para o treinamento, que passou a ser executado por ⟨script⟩ fora da API publicada,",
   "conexão com o banco em nuvem: quedas curtas de conexão interrompiam treinamentos longos, o que levou à "
   "verificação das conexões e à repetição das gravações em caso de falha,",
   "atualização da base: a extração dos relatórios depende do computador do setor financeiro, e a base disponível "
   "termina em fevereiro de 2026, o que levou à conferência, na importação, dos dias de loja aberta sem venda.")

#@@ cap113
h2("11.3 Resultados dos Testes")
p("Na execução de 11 de novembro de 2026, os 196 testes automatizados em ⟨pytest⟩, 120 unitários e 76 de "
  "integração, foram aprovados, em 3 minutos e 37 segundos. A suíte de ponta a ponta, com 39 testes, não foi "
  "concluída nessa execução, porque a preparação da base sintética excedeu o tempo limite do servidor de testes.")
cp("A importação foi testada com planilhas de vendas fictícias de março de 2026",
   ("O teste também mostrou um caso não detectado: uma nota repetida inteira dentro da mesma planilha entra duas "
    "vezes, porque a duplicidade é verificada apenas contra a base já gravada.",
    "O teste também revelou um defeito ainda não corrigido: uma nota repetida inteira dentro da mesma planilha entra "
    "duas vezes, porque a duplicidade é verificada apenas em relação à base já gravada."))
p("Com a API executada localmente e conectada ao banco de produção, as rotas de consulta responderam, em média de "
  "dez requisições, entre 0,44 e 0,87 segundo, e a do painel, que transfere cerca de 311 kB com a previsão de 91 "
  "dias de todas as séries, em 0,55 segundo. O treinamento de produção, com as 43 séries, levou 75 minutos com 12 "
  "processos paralelos, dentro do limite de duas horas do requisito RNF03. Não foram realizados testes formais de "
  "usabilidade, e a interface foi aprovada pela empresa nas reuniões de outubro e novembro de 2026.")

#@@ e3
p(f"O experimento E3 isolou o efeito da transformação log(1{NB}+{NB}y), que estabiliza a variância das vendas, "
  f"mantendo a ordem do modelo, as variáveis exógenas e d{NB}={NB}1. No fluxo diário de Itabirito, o logaritmo "
  "reduziu o MAE em 8,4%, mas a previsão cobriu 89,6% do volume vendido, contra 101,1% na escala original, e, na "
  "série total com as encomendas, cobriu apenas 46,1%, porque a previsão convertida de volta à escala original "
  "corresponde à mediana da distribuição prevista, e não à média (HYNDMAN; ATHANASOPOULOS, 2021). Nos produtos de "
  "venda regular de Itabirito, o logaritmo reduziu o MAE em 13%, mas a previsão cobriu 48% do volume vendido, e o "
  "erro no total dos 14 dias aumentou de 45,5% para 55,0%. Como a compra é planejada sobre o volume de vários dias, "
  "uma previsão que subestima sistematicamente esse volume não é adequada ao uso do sistema, e a solução adotou a "
  "escala original, na qual a previsão acompanha o volume vendido.")

#@@ e7
p("O experimento E7 mediu quanto a previsão piora com a distância do treinamento e com a frequência de "
  "retreinamento, nas oito categorias, em 52 treinamentos semanais. O erro de cada dia cresceu pouco com o "
  "horizonte, no máximo 6% com d" + NB + "=" + NB + "0, e a cobertura do intervalo de 95% manteve-se entre 92% e "
  "93% em todas as semanas. Até a sexta semana, d" + NB + "=" + NB + "1 errou menos que d" + NB + "=" + NB + "0 nas "
  "categorias que o utilizam, e, da sétima em diante, errou mais. Retreinar a cada quatro semanas errou 2% a mais que retreinar toda semana, na média "
  "do ano, e 15% a mais no pior mês, e retreinar a cada 13 semanas errou 3% a mais na média e 32% a mais no pior mês, "
  "em viradas de temporada como janeiro e novembro. Por isso, o sistema grava a previsão de 91 dias, mantém a "
  "validação em 14 dias e é retreinado a cada planilha semanal.")

#@@ cap117
h2("11.7 Comparação com os Objetivos")
p("Os objetivos específicos foram alcançados. Os requisitos foram levantados e validados em oito reuniões com a "
  "entidade parceira, a arquitetura e a modelagem estão descritas no Capítulo 8, e o ⟨pipeline⟩ carregou as 26 "
  "planilhas, com 351.092 registros e nenhuma duplicata, com a mesma rotina usada na importação semanal. A análise "
  "exploratória definiu as séries e as variáveis do modelo (Seção 11.4), o calendário eliminou o erro nos feriados e "
  "o fator das datas reduziu o erro da semana das datas em Flores de corte (E1 e E6), e os experimentos E1 a E8 "
  "definiram a configuração. Os modelos de 23 séries foram treinados e avaliados, com MASE abaixo de 1 em 19 delas e "
  "cobertura do intervalo entre 90,5% e 100%, e a API, o serviço de previsão e o painel estão em operação com os "
  "dados reais. A validação do software foi feita por testes automatizados e pela aprovação da empresa, sem teste "
  "formal de usabilidade, e a documentação é técnica, sem manual do usuário, de modo que esses dois objetivos foram "
  "alcançados parcialmente.")
p("O objetivo geral, desenvolver um sistema que forneça a previsão diária da demanda de cada categoria e de cada "
  "produto de grama das unidades da empresa, foi alcançado: o sistema gera, a cada treinamento, a previsão dos 91 "
  "dias seguintes de 23 séries, das quais as oito categorias erram menos que a previsão ingênua na validação, e a "
  "apresenta à empresa em um painel acessível a usuários não técnicos.")

#@@ futuros
p("Como trabalhos futuros, propõem-se:")
ul("verificar formalmente a usabilidade do sistema com a gestora de compras, elaborar o manual do usuário e corrigir a "
   "verificação de notas repetidas dentro da mesma planilha,",
   "integrar ao sistema a informação antecipada das encomendas grandes, como pedidos já negociados, e calibrar com a "
   "entidade parceira o limiar que as define,",
   "oferecer, além da previsão pontual, uma quantidade de referência baseada em um quantil superior da distribuição "
   "prevista, com nível definido pela empresa, e reavaliar a janela de treinamento com os novos dados,",
   "estender a previsão por produto às Flores de corte e comparar, nos produtos de demanda intermitente, os métodos "
   "específicos para esse padrão (Seção 5.3), além de redes neurais e métodos de ⟨ensemble⟩,",
   "implementar a identificação de produtos comprados em conjunto e a simulação de promoções, solicitadas pela "
   "entidade parceira,",
   "avaliar, após a implantação, o efeito do sistema sobre as perdas por descarte e sobre as rupturas de estoque.")

#@@ anexo
h1("ANEXO A – TELAS DO SISTEMA DE GESTÃO DA EMPRESA")
p("As telas a seguir foram compartilhadas pela entidade parceira em reunião, em março de 2026, e mostram a seleção "
  "do relatório de contas a receber por grupo de produto ({fig:erp_filtro}) e o relatório de recebimento por grupo "
  "de produto ({fig:erp_relatorio}) no sistema de gestão da empresa. O nome do usuário do sistema foi ocultado.")
fig("erp_filtro", os.path.join(IMG, "erp_filtro.png"), 11.5, "Filtro do relatório de contas a receber por grupo de produto",
    "Fonte: Floricultura Verde Perto (2026).")
fig("erp_relatorio", os.path.join(IMG, "erp_relatorio.png"), 11.5, "Relatório de recebimento por grupo de produto",
    "Fonte: Floricultura Verde Perto (2026).")

