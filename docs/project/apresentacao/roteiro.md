# Roteiro da apresentação do TCC (online)

**Sistema de previsão de vendas: uma solução inteligente para a gestão de demanda da Floricultura Verde Perto**
Daniel Nunes da Silva · Felipe Gurgel Araújo — Ciência da Computação, Centro Universitário Dom Helder, 2026

- **Slides:** https://claude.ai/artifact/Fw2jt5pU9ipFquZYvFjYpS (privado até ser compartilhado pelo menu *Share*; exporta para PowerPoint e PDF). Fonte dos slides em `docs/project/apresentacao/deck/`.
- **Formato:** 15 min de apresentação + 15 min de perguntas, online.
- **Base:** artigo final (*TCC2 – Relatório Técnico – Final – Corrigido*) e orientações da última reunião com o orientador.

## 1. Como as orientações do orientador foram atendidas

| Orientação | Onde está |
| --- | --- |
| Contextualização de ~5 min | Slides 1–6 (0:00–4:45) |
| Objetivos | Slide 5 (geral + 4 grupos de específicos) |
| 2 artigos principais | Slide 6: Arunraj, Ahrens e Fernandes (2016) e Huber, Gossmann e Stuckenschmidt (2017) |
| ~10 min de desenvolvimento | Slides 7–16 (4:45–13:45, 9 min) + encerramento em 1 min 15 s |
| Fluidez na fala | Falas completas nas notas de cada slide e na seção 3; só 2 trocas de voz |
| Slides da aplicação no final | Slide 16 (visão geral) + apêndice 19–25 com 6 telas |
| Aplicação com dados fictícios | Todas as telas vêm da base sintética dos testes E2E; demo ao vivo com a mesma base (seção 4) |
| Pronto para "por que não LSTM?" | Slide 26 + resposta roteirizada (seção 5.1) |

## 2. Divisão e tempos

Divisão: **Daniel** abre e apresenta contexto, problema e objetivos (slides 1–5); **Felipe** apresenta os artigos, a metodologia, a análise exploratória, o modelo e os resultados (6–14); **Daniel** volta com arquitetura, aplicação e encerramento (15–18). A metodologia (7) ficou com o Felipe porque está entre os artigos e a análise exploratória: assim são só duas trocas de voz. Tempo de fala: Daniel ~6 min 30 s, Felipe ~8 min 30 s.

| # | Slide | Quem | Tempo | Ideia que precisa ficar |
| --- | --- | --- | --- | --- |
| 1 | Capa | Daniel | 0:00–0:30 | quem somos e o roteiro da fala |
| 2 | A Floricultura Verde Perto | Daniel | 0:30–1:20 | perecível: errar a compra custa caro |
| 3 | Situação atual | Daniel | 1:20–2:10 | compra pela experiência, histórico sem uso |
| 4 | Pergunta de pesquisa | Daniel | 2:10–2:35 | o sistema informa, a loja decide |
| 5 | Objetivos | Daniel | 2:35–3:30 | previsão diária por categoria e por grama → **passa ao Felipe** |
| 6 | Os dois artigos | Felipe | 3:30–4:45 | Arunraj → modelo; Huber → nível de agregação |
| 7 | Metodologia | Felipe | 4:45–5:35 | iterativa + CRISP-DM, 8 reuniões |
| 8 | Análise exploratória | Felipe | 5:35–6:30 | produto não dá; categoria sim |
| 9 | Pipeline | Felipe | 6:30–7:25 | encomendas grandes à parte (média + 4 desvios) |
| 10 | SARIMAX | Felipe | 7:25–8:30 | calendário como exógena; 23 séries |
| 11 | Experimentos | Felipe | 8:30–9:15 | cada decisão veio de um experimento |
| 12 | Três escolhas | Felipe | 9:15–10:15 | calendário, agregação, datas |
| 13 | Walk-forward | Felipe | 10:15–11:00 | testar como se usa; MASE < 1 = melhor que a referência |
| 14 | Resultados | Felipe | 11:00–12:00 | 19 de 23 com MASE < 1; 8 de 8 categorias → **passa ao Daniel** |
| 15 | Arquitetura | Daniel | 12:00–12:45 | React + FastAPI + serviço de previsão + Postgres |
| 16 | A aplicação | Daniel | 12:45–13:45 | ciclo da gestora |
| 17 | Limitações e futuros | Daniel | 13:45–14:25 | encomendas grandes e histórico curto |
| 18 | Conclusão | Daniel | 14:25–15:00 | objetivo alcançado; abre para perguntas |
| 19–27 | Apêndice | — | perguntas | telas, LSTM, respostas rápidas |

**Marcos de tempo** (para quem estiver cronometrando): slide 7 começa por volta de **4:45**; slide 12 por volta de **9:15**; slide 17 por volta de **13:45**. Se estiverem atrasados no slide 12, encurtem o 13 (só a frase do MASE) e o 15 (só "painel, API, serviço de previsão e banco").

## 3. Falas

As mesmas falas estão nas notas do apresentador de cada slide. São um guia, não um texto para ler: decorem a primeira frase de cada slide e falem o resto com as próprias palavras.

**1 · Capa (Daniel)** — Boa noite, professores e colegas. Eu sou o Daniel Nunes da Silva e este é o Felipe Gurgel Araújo. Vamos apresentar o nosso trabalho de conclusão de curso: um sistema de previsão de vendas desenvolvido para a Floricultura Verde Perto, sob orientação do professor Marcos Wander Rodrigues, no conteúdo, e do professor Ricardo Luiz de Freitas, na metodologia. Nos próximos quinze minutos vamos mostrar o problema da empresa, o que nos propusemos a fazer, como desenvolvemos a solução e o que ela entregou. Eu começo pelo contexto e pelos objetivos, o Felipe apresenta a fundamentação, os dados, o modelo e os resultados, e eu volto para o sistema e a conclusão.

**2 · A empresa (Daniel)** — A nossa entidade parceira é a Floricultura Verde Perto, que vende flores, plantas, grama e produtos de jardinagem em duas lojas: Jardim Canadá, em Nova Lima, e Itabirito. Boa parte do que ela vende é perecível: se a loja compra demais, a flor e a planta se perdem; se compra de menos, o cliente não encontra o produto. A grama responde por quase metade do volume, seguida de plantas diversas e produtos de jardim. Flores de corte pesam pouco no volume, mas são as mais sensíveis ao calendário — guardem esse detalhe, ele volta no modelo.

**3 · Situação atual (Daniel)** — As vendas ficam no ERP, que emite relatórios, mas não estima demanda. As planilhas exportadas vêm em blocos por nota e nem informam o grupo do produto. A reposição de grama e flores leva cerca de uma semana, então a compra acontece antes da venda, e era decidida só pela experiência. A demanda muda com o dia da semana, com as datas comemorativas e de uma loja para a outra, e não havia como verificar depois se a estimativa acertou. O histórico existia, mas não era usado de forma sistemática.

**4 · Pergunta de pesquisa (Daniel)** — Isso nos levou à pergunta: como utilizar os dados históricos de vendas de uma floricultura para gerar, de forma sistemática e antecipada, previsões de demanda diária que apoiem o planejamento de compras? E um ponto de escopo combinado com a empresa: o sistema não decide a compra; ele informa quanto se espera vender, com uma faixa de incerteza.

**5 · Objetivos (Daniel)** — O objetivo geral foi desenvolver um sistema de previsão de vendas, baseado no histórico e em modelos regressores com dados de calendário, que entregue a previsão diária de cada categoria e de cada produto de grama das duas lojas — grama produto a produto porque é assim que a loja compra. Os específicos se agrupam em quatro frentes: requisitos e modelagem validados com a empresa; os dados, do pipeline das planilhas à análise exploratória e ao calendário; os modelos, comparados por validação walk-forward; e o sistema, com API, serviço de previsão, painel, testes e documentação. *"Felipe, com você."*

**6 · Os dois artigos (Felipe)** — Obrigado, Daniel. Dois artigos sustentam as decisões principais. Arunraj, Ahrens e Fernandes, 2016, aplicam o SARIMAX à venda diária de perecíveis no varejo de alimentos, com variáveis de calendário e promoção: daí veio o nosso modelo central, e o resultado se repetiu aqui — o calendário praticamente zerou o erro nos feriados. Huber, Gossmann e Stuckenschmidt, 2017, tratam da previsão hierárquica de perecíveis, ou seja, em que nível prever: loja, categoria ou produto. Testamos a estratégia top-down — prever a loja e dividir — contra um modelo direto por categoria, e o direto venceu. Os dois são estudos de método, sem uma ferramenta que a empresa use: essa é a lacuna que o trabalho preenche. Como apoio: Hyndman e Athanasopoulos, Syntetos e Boylan e a competição M4.

**7 · Metodologia (Felipe)** — Usamos uma abordagem híbrida: no software, iterativa e incremental, com entregas em partes funcionais validadas com a empresa; nos dados, o CRISP-DM, do negócio à implantação. E o ciclo foi real: a avaliação nos levou de volta à preparação, como no caso das encomendas grandes. Foram oito iterações, de abril a novembro, e oito reuniões com as sócias da empresa. Cada decisão técnica ficou registrada em documentos de decisão arquitetural e cada mudança entrou por pull request revisado.

**8 · Análise exploratória (Felipe)** — A análise definiu o que dava para prever: vinte e seis planilhas, cerca de trezentas e cinquenta mil linhas e mais de cinco mil produtos. Pelo critério de Syntetos e Boylan, 99,3% dos produtos têm demanda irregular — o produto típico vendeu em nove de setecentos e oitenta e nove dias. Por produto, não funciona. Somando por loja e categoria, as séries têm venda em mais de 80% dos dias, e o SARIMAX se aplica. A análise também mostrou o padrão da semana: pico de terça a quinta na grama, sexta nas flores, domingo fechado. A seguir, como esses dados foram preparados.

**9 · Pipeline (Felipe)** — O próprio sistema executa a preparação a cada planilha enviada: extrai uma linha por produto de cada nota, com um hash que impede a mesma planilha de entrar duas vezes; padroniza textos, datas e valores; classifica cada produto numa das quatro categorias pelo nome; separa as encomendas grandes; e monta o calendário e a série diária. As encomendas grandes foram o ponto que mais mudou o resultado: em Itabirito, cinco por cento dos dias concentravam quase dois terços do erro. Eram pedidos de empresas, combinados com antecedência. Um pedido acima da média mais quatro desvios-padrão da loja vira um fluxo à parte, e o modelo prevê a venda do dia a dia — o coeficiente de variação caiu de 2,35 para 0,77.

**10 · SARIMAX (Felipe)** — O modelo central é o SARIMAX. A previsão de cada dia combina as vendas e os erros dos dias anteriores, o ciclo semanal e as variáveis de calendário: segunda a sábado, loja fechada e abertura excepcional. A vantagem é que os valores futuros dessas variáveis já são conhecidos. A diferenciação, zero ou um, é escolhida série a série pelo menor erro na validação, e as datas comemorativas entram como um fator depois do ajuste, porque cada data aparece no máximo duas vezes no histórico. São vinte e três séries, cada uma com o seu modelo, treinadas em 545 dias, prevendo 91 dias com faixa de 95%. O total da loja é a soma das categorias.

**11 · Experimentos (Felipe)** — Nenhuma escolha foi no achismo: cada uma saiu de um experimento, mudando um fator por vez, com o mesmo período de teste e as mesmas métricas, e diferenças abaixo de 5% contam como empate. Foram nove experimentos — exógenas, encomendas, logaritmo, que descartamos porque subestimava o volume, agregação, diferenciação, datas, horizonte, janela e a solução definitiva. Destaco os três que mais pesaram.

**12 · Três escolhas (Felipe)** — Primeiro, o calendário: a faixa de 95% ficou mais de cinco vezes mais estreita e o erro nos feriados praticamente zerou, como no artigo de Arunraj. Segundo, a agregação, a pergunta do artigo de Huber: prever a loja e dividir perdeu para o modelo direto em sete de oito casos; em flores de corte, os picos das datas se anulam no total da loja e a divisão não os recupera. Terceiro, as datas comemorativas: sem ajuste, o modelo previa uma semana comum de flores; com metade da alta medida nas ocorrências anteriores, o erro da semana caiu de 61% para 33% em Jardim Canadá, com melhora nas dez ocorrências testadas.

**13 · Walk-forward (Felipe)** — Para medir, usamos validação walk-forward, que reproduz o uso real: o modelo treina só com o que veio antes de uma data, prevê os catorze dias seguintes e compara com o vendido; depois a origem anda um dia. São cinquenta e seis origens a cada treino. A principal métrica é o MASE: o erro do modelo dividido pelo erro de repetir a semana anterior — abaixo de um, o modelo erra menos. Usamos o MASE e não o MAPE porque há muitos dias de venda baixa ou zero. E medimos a cobertura da faixa de 95%.

**14 · Resultados (Felipe)** — As oito categorias ficaram com MASE abaixo de um, entre 0,64 e 0,98. Com os produtos de grama, são dezenove de vinte e três. Os quatro acima de um são gramas de pouco volume em Jardim Canadá, e a tela mostra um aviso neles. A cobertura da faixa ficou entre 90,5 e 100%, e o Ljung-Box não encontrou autocorrelação nos resíduos em vinte e duas séries. Com honestidade: nesse período, com Natal, Ano-Novo e Carnaval e uma queda de vendas no início de 2026, o previsto ficou acima do vendido — e o histórico de previsões existe justamente para acompanhar esse viés. *"Daniel, com você."*

**15 · Arquitetura (Daniel)** — Obrigado, Felipe. O painel em React conversa com uma API REST em FastAPI, com JWT, bcrypt e contrato OpenAPI. Os dados ficam em PostgreSQL no Neon, e SQLite no desenvolvimento e nos testes. O serviço de previsão ajusta os modelos em processos paralelos — o treino de produção leva cerca de 75 minutos, dentro do limite de duas horas. A lógica de previsão fica num domínio sem dependência de framework nem de banco, o que facilitou os 196 testes automatizados.

**16 · A aplicação (Daniel)** — Para a gestora, é um ciclo de cinco passos: carrega a planilha que já exportava; confere antes de gravar — vendas novas, repetidas e dias sem venda; clica em "Treinar previsões"; consulta a previsão diária com a faixa, de duas semanas a três meses; e compara o previsto com o vendido e baixa relatórios. A imagem é da base de demonstração, com vendas fictícias. No final, se quiserem, mostramos as telas.

**17 · Limitações e futuros (Daniel)** — A principal limitação são as encomendas grandes, que pesam no volume, principalmente em Itabirito, e não são previstas porque dependem de negociação. Vinte e seis meses não bastam para a sazonalidade anual, a extração do ERP é manual e a usabilidade foi validada só nas reuniões. Como futuros: receber as encomendas com antecedência, oferecer uma quantidade de referência para estoque, prever flores de corte por produto e medir o efeito do sistema nas perdas e rupturas.

**18 · Conclusão (Daniel)** — O histórico que a empresa já tinha, organizado com o calendário de cada loja, virou uma previsão diária avaliada a cada treino. O objetivo geral foi alcançado, com quinze de dezessete requisitos atendidos e dois parcialmente. E os resultados indicam que modelos estatísticos com calendário funcionam na floricultura, desde que a demanda seja agregada em séries densas e as encomendas grandes sejam tratadas à parte. Agradecemos aos orientadores, à Verde Perto e à banca. Ficamos à disposição para as perguntas.

## 4. A aplicação na hora das perguntas (dados fictícios)

O orientador sugeriu ter a aplicação rodando para as perguntas, **com dados fictícios**. A base sintética dos testes de ponta a ponta serve para isso: 2 lojas, 4 categorias, 3 produtos de grama, vendas de 02/01/2025 a 28/02/2026, feriados, ciclo semanal e encomendas grandes, com um treino já concluído. As telas do apêndice (19–25) foram capturadas dela. Ela nunca toca o Neon.

**Antes do dia (uma vez):** ensaiar a subida abaixo. Não consegui executá-la nesta sessão, então confiram com antecedência.

Terminal 1 — API com a base sintética, em `ia-predictor/`:

```powershell
.venv\Scripts\python -m tests.e2e.servidor --porta 8100 --origem http://localhost:5174
```

Na primeira vez sem cache ela monta a base e treina (~3–5 min); com o cache em `tests/e2e/.cache/`, sobe em segundos. Cada execução começa de uma cópia limpa.

Terminal 2 — painel apontando para essa API, em `app-react/`:

```powershell
$env:VITE_API_URL = "http://localhost:8100"; npx vite --port 5174 --strictPort
```

Abrir http://localhost:5174 e entrar como **gestora@floricultura.com / senha-admin-e2e** (perfil administrador). O perfil de consulta é **gerente@floricultura.com / senha-viewer-e2e**.

Para mostrar a importação ao vivo, gerar antes uma planilha fictícia (em `ia-predictor/`):

```powershell
.venv\Scripts\python -m tests.e2e.servidor --planilha planilha-demo.xlsx --inicio 2026-03-02 --fim 2026-03-07
```

**Roteiro de demo (≤ 3 min, só se pedirem):** Início (filtro de loja, faturamento separando encomendas) → Previsão de Vendas (trocar a loja, ver uma grama, passar o mouse na tabela Dia a dia) → aba Histórico de previsão (indicadores de acerto) → Carregar Planilha com `planilha-demo.xlsx` até a conferência (mostrar o aviso de dias sem venda; pode gravar) → Relatórios (prévia e Baixar Excel). Evitem disparar "Treinar previsões" ao vivo: na base de demonstração é rápido, mas não é necessário.

**Como falar dos dados:** na demo, chamem de "base de demonstração". Se perguntarem diretamente se o modelo usou os dados da empresa, respondam com a verdade, como está no artigo: os modelos foram treinados e validados com o histórico de vendas cedido pela empresa, e a demonstração usa vendas fictícias para preservar os dados da parceira.

**Plano B:** se a aplicação não subir, usem os slides 19–25 (as mesmas telas).

## 5. Perguntas prováveis

### 5.1 Por que não usaram LSTM? (slide 26)

> Consideramos, mas escolhemos começar pelo modelo estatístico por quatro motivos. **Volume de dados:** são 26 meses de vendas, e cada série treina com 545 dias; uma LSTM tem milhares de parâmetros e, com tão poucas observações por série, tende a decorar o histórico. **Literatura:** na competição M4 (Makridakis et al., 2020), com cem mil séries, os métodos puramente de aprendizado de máquina ficaram atrás dos estatísticos, e os melhores resultados vieram de métodos estatísticos ou híbridos. **O que a loja usa:** ela precisa de uma faixa de incerteza e de entender o efeito de domingo, feriado e data comemorativa; o SARIMAX dá a faixa de 95% e coeficientes interpretáveis direto do modelo. **Custo:** retreinamos 23 séries, com 56 origens e dois valores de d, a cada carga, numa hospedagem gratuita de 512 MB. Por isso a regra do projeto é que um modelo de aprendizado de máquina só entra se vencer o SARIMAX no mesmo walk-forward — fica como trabalho futuro, de preferência um modelo global treinado em todas as séries juntas.

Cuidados:
- Não digam que "o ML perdeu tudo" na M4: o vencedor (Smyl, ES-RNN) foi um **híbrido** de suavização exponencial com rede neural.
- Se citarem a **M5**, vencida por LightGBM: ela tinha cerca de 42 mil séries do Walmart e 5 anos de dados, com um modelo **global** treinado em todas as séries — cenário bem diferente das nossas 23 séries e 26 meses. É um argumento a favor da nossa escolha, não contra.
- Sejam honestos: **não treinamos uma LSTM**. Os experimentos compararam variações do modelo estatístico e a desagregação hierárquica.

### 5.2 Outras

| Pergunta | Resposta curta |
| --- | --- |
| Por que SARIMAX e não uma regressão linear com as mesmas variáveis? | A regressão ignora a dependência entre dias seguidos; o SARIMAX modela os dias anteriores, os erros recentes e o calendário juntos, e dá a faixa de 95%. |
| E o Prophet? | Não comparamos experimentalmente. Ele modela tendência, sazonalidade e feriados — o mesmo que o SARIMAX com calendário trata aqui. A diferença do trabalho é a ferramenta operacional; a comparação fica como futuro. |
| Por que tirar as encomendas grandes? | São pedidos de empresas combinados com antecedência (confirmado pela loja). Em Itabirito, 5% dos dias concentravam 61,8% do erro. Elas aparecem num fluxo à parte no painel. |
| Por que média + 4 desvios e não um valor fixo? | O limiar fixo trata igual lojas com pedidos de tamanhos diferentes. Com 4 desvios: 1.343 un. em Jardim Canadá e 1.960 em Itabirito; com 3 desvios a cobertura caía abaixo de 90% em duas séries. |
| Por que não usar log nas vendas? | E3: reduzia o MAE, mas a volta à escala original dá a mediana: previa só 89,6% do volume. A compra depende do volume de vários dias. |
| Por que não prever cada produto? | 99,3% dos produtos têm demanda irregular; o produto típico vende em 9 de 789 dias. A grama é prevista por produto porque é comprada assim. |
| Por que MASE e não MAPE? | O MAPE explode em dias de venda baixa ou zero; o MASE compara com a previsão ingênua e permite comparar séries de volumes diferentes (Hyndman e Koehler, 2006). |
| E as 4 séries com MASE acima de 1? | Gramas de pouco volume em Jardim Canadá, com aviso na tela. Nelas o MASE e o erro relativo divergem: Capim dos Texas roxo tem MASE 2,24, mas erra 43% menos que a referência. |
| Cobertura de 100% em Flores de corte não é ruim? | Indica faixa mais larga que o necessário nessas séries (o artigo reconhece). É conservador: a loja vê o máximo provável. |
| O previsto ficou acima do vendido (109–151%). Por quê? | A validação pegou dez/2025–fev/2026, com Natal, Ano-Novo, Carnaval e queda de vendas no início de 2026; com d = 0, a previsão volta à média. O histórico de previsões acompanha esse viés a cada treino. |
| Como foi escolhido d? | O AIC não compara modelos com d diferentes; o walk-forward de cada série decide entre 0 e 1 (−3,6% no erro, E5). Ficou d = 1 em 9 séries e d = 0 em 14. |
| Por que 545 dias de janela? | E8: melhor janela única (−1,9% no erro); 90 dias piorava 8,6%. O modelo vê cada data comemorativa mais de uma vez. |
| Com que frequência retreinar? | Mensal, a cada exportação: perde 2% na média do ano frente ao semanal. Máximo recomendado de 2 meses (pior mês +28,6%). |
| Por que o sistema não diz quanto comprar? | Escopo acordado com a empresa: ela não tem o estoque atual no sistema. Fica como futuro uma quantidade de referência por um quantil superior. |
| Como garantem que o histórico não é "maquiado"? | Cada dia guarda a previsão mais antiga feita para ele e nunca é reescrito por treinos posteriores (RN03). |
| Segurança e LGPD? | JWT com expiração, bcrypt, perfis administrador/consulta, limite de tentativas de login; o banco não guarda nome, documento nem código de clientes. |
| Como validaram com o usuário? | Oito reuniões com as sócias; protótipo no Figma validado em maio/junho e versões aprovadas em outubro e novembro. Sem teste formal de usabilidade (limitação assumida). |
| Quem fez o quê? | [preencher juntos antes do dia: divisão de backend, modelagem, frontend e artigo] |

## 6. Checklist do dia (online)

- [ ] Compartilhar o link dos slides entre os dois (menu *Share*) e baixar um **PDF de reserva** (*Share › Export*).
- [ ] Quem compartilha a tela abre o deck em modo apresentação; as notas ficam no outro monitor ou no celular.
- [ ] Testar câmera, microfone e compartilhamento na plataforma da banca 15 min antes; fechar notificações (e-mail, WhatsApp, Teams).
- [ ] API e painel da demonstração já abertos e logados numa aba separada (seção 4).
- [ ] Cronômetro visível para quem não está falando; combinar um sinal discreto para "acelerar".
- [ ] Ensaiar a apresentação inteira cronometrada pelo menos duas vezes, com as trocas de voz.
- [ ] Na troca de falante, quem entra agradece em uma frase e já começa ("Obrigado, Daniel. Dois artigos sustentam…").
- [ ] Nas perguntas: repetir a pergunta em uma frase, responder curto, e abrir o slide de apoio se ajudar.
