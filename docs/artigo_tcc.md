# SISTEMA DE PREVISÃO DE ESTOQUE: UMA SOLUÇÃO INTELIGENTE PARA A GESTÃO DE DEMANDA DA FLORICULTURA VERDE PERTO

**Daniel Nunes da Silva | Felipe Gurgel Araújo**

Centro Universitário Dom Helder — Bacharelado em Ciência da Computação

Projeto técnico apresentado ao Centro Universitário Dom Helder como requisito parcial
para obtenção do título de Bacharel em Ciência da Computação.

Orientador de conteúdo: Prof. Marcos Wander Rodrigues

Orientador de metodologia: Prof. Me. Ricardo Luiz de Freitas

Belo Horizonte — 2026

> *Versão: espelho em Markdown do Projeto Técnico Verde Perto — Final, Revisado pelo
> Prof. Orientador (fonte: `Projeto Tecnico Verde Perto Final - Revisado pelo Prof.
> Orientador.pdf`, sincronizado em 2026-08-21).*

---

## RESUMO

Este trabalho propõe o desenvolvimento de um sistema de previsão de estoque para a
Floricultura Verde Perto, com histórico consolidado de vendas cobrindo o período de
janeiro de 2024 a fevereiro de 2026. O setor de floricultura apresenta desafios
decorrentes do alto nível de perecibilidade dos produtos, da sazonalidade acentuada e
da oscilação da demanda em datas comemorativas. A ausência de previsão gera riscos de
quebra de estoque e perdas por excesso de compra. A solução proposta contempla um fluxo
completo de processamento de dados históricos de vendas, com engenharia de atributos,
treinamento e atualização automática de modelos preditivos baseados em SARIMAX
(*Seasonal AutoRegressive Integrated Moving Average with eXogenous inputs*), um modelo
estatístico de previsão de séries temporais que considera padrões históricos,
sazonalidade e fatores externos que podem influenciar a demanda, apresentação de
indicadores em dashboard interativo e simulações de cenários de promoção e venda. O
horizonte de previsão definido é de duas a três semanas, alinhado ao ciclo operacional
de reposição da empresa. A metodologia adota abordagem ágil e iterativa, com entregas
parciais orientadas a valor. Os requisitos foram consolidados em reuniões formais com a
entidade parceira e incluem módulos de upload de planilhas, geração automática de
previsões, emissão de alertas de reposição, exportação de relatórios e simulação de
estratégias comerciais, visando a redução de desperdícios, a mitigação de rupturas e o
aumento da assertividade no planejamento logístico e comercial.

**Palavras-chave:** previsão de demanda; gestão de estoque; floricultura; aprendizado
de máquina; SARIMAX.

---

## SUMÁRIO

1. Introdução
2. Contexto e Problematização
3. Justificativa
4. Objetivos
5. Referencial Teórico
6. Metodologia Adotada
7. Requisitos do Sistema
8. Cronograma

Referências

---

## 1 INTRODUÇÃO

Este trabalho propõe o desenvolvimento de um sistema de previsão de estoque para a
Floricultura Verde Perto, empresa com unidades localizadas em Nova Lima (Jardim Canadá)
e Itabirito, Minas Gerais. A empresa possui aproximadamente dois anos de histórico
consolidado de vendas e dados financeiros, totalizando mais de 324 mil registros
transacionais com informações detalhadas por transação, segmentação por grupos de
produtos e separação de dados entre as três unidades operacionais.

A base de dados cobre o período de janeiro de 2024 a fevereiro de 2026, contendo mais
de 5.100 produtos distintos SKU (*Stock Keeping Unit*), um código utilizado para
identificar individualmente produtos no controle de estoque, aproximadamente 2.500
clientes únicos, 38 vendedores e três unidades operacionais. Esse conjunto de dados
possui informações necessárias para a construção de modelos preditivos que capturam
padrões sazonais e tendências.

Embora os dados disponíveis apresentem potencial analítico, demandam etapas de
tratamento e normalização para viabilizar seu uso em modelagem preditiva. A solução
proposta contempla um fluxo de processamento: geração e gestão de dados, tratamento e
normalização, engenharia de atributos, treinamento e atualização de modelos preditivos,
apresentação de indicadores em dashboard interativo e simulações de cenários de
promoção e vendas conjugadas de produtos. O horizonte de previsão foi definido entre
duas e três semanas, alinhado ao ciclo operacional de reposição atual da empresa.

---

## 2 CONTEXTO E PROBLEMATIZAÇÃO

A gestão de estoque no setor de floricultura apresenta desafios importantes e únicos,
fortemente impactados pelo alto nível de perecibilidade dos produtos, sazonalidade
acentuada e pela variabilidade significativa da demanda em períodos de datas
comemorativas, como Dia das Mães, Dia dos Namorados, Dia das Mulheres e Natal. A
ausência de uma previsão estruturada aumenta o risco de desabastecimento de estoque e
perdas por excesso de compra, impactando negativamente a margem de lucro operacional
da empresa.

Atualmente, o controle de estoque é realizado com apoio predominante do conhecimento
tácito da equipe e de relatórios operacionais gerados manualmente a partir do sistema
financeiro vigente. Parte dos dados é disponibilizada em relatórios estruturados e
parte em planilhas exportadas, exigindo etapas adicionais de extração dos dados e sua
padronização. Essa heterogeneidade eleva o esforço técnico da etapa inicial de geração
e gestão de dados. Além disso, a empresa opera com múltiplos grupos de produtos,
destacando-se as gramas como produto principal e as flores de corte como categorias de
maior valor estratégico e com uma determinada dificuldade de previsão.

Um estoque excessivo resulta em perda direta devido ao descarte de produtos perecíveis
não vendidos, enquanto o estoque insuficiente representa vendas perdidas em dias de
pico, podendo representar 30 a 40% do faturamento mensal em datas comemorativas
específicas. A inexistência de um sistema de previsão estruturado impede que a equipe
gestora antecipe essas oscilações com base em evidências quantitativas, limitando o
planejamento ao horizonte imediato e à memória organizacional.

O problema central pode ser sintetizado nas seguintes questões operacionais:

- Como determinar o número de unidades de cada produto comprar para um determinado
  período sem incorrer em excesso ou escassez?
- Como antecipar o impacto de datas comemorativas em relação à demanda de produtos
  específicos?
- Como avaliar o efeito de promoções e estratégias de vendas conjugadas de produtos
  sobre o volume vendido?
- Qual produto pode ser sugerido ao cliente que está comprando outro produto, visando
  maximizar o valor da transação?

Tais questões constituem uma lacuna operacional que se propõe preencher por meio de um
sistema baseado em dados históricos e técnicas de modelagem preditiva.

---

## 3 JUSTIFICATIVA

A falta de controle, planejamento e previsão de estoque da empresa gera ineficiências
operacionais que se traduzem diretamente em perdas financeiras. O objetivo é
desenvolver um sistema integrado e unificado, acessível a todos os usuários, capaz de
receber dados, atualizar automaticamente previsões em períodos semanais e apresentar
recomendações com base em evidências quantitativas.

A justificativa científica para a adoção de modelos da família SARIMAX neste contexto
reside em sua adequação para séries temporais sazonais com variáveis exógenas, fatores
externos que influenciam o comportamento da demanda. Arunraj, Ahrens e Fernandes (2016)
demonstraram a eficácia da abordagem SARIMAX no varejo de alimentos perecíveis,
evidenciando ganhos expressivos de acurácia pela incorporação de variáveis exógenas de
calendário e promoção. De forma complementar, Pavlyshenko (2019) confirmou que o
SARIMAX aplicado ao varejo de alimentos perecíveis produz erros de previsão inferiores
a 5% em média para produtos de alto giro, com redução adicional de até 18% pelo uso de
variáveis exógenas. Itens como flores e plantas compartilham com o varejo alimentar
perecível os atributos de alta perecibilidade, forte sazonalidade, além do impacto
elevado de eventos externos, o que reforça a importância deste trabalho.

A justificativa técnica complementar está nos resultados da competição M4
(MAKRIDAKIS; SPILIOTIS; ASSIMAKOPOULOS, 2020), que demonstrou que modelos estatísticos
da família ARIMA superam abordagens de aprendizado de máquina em séries temporais com
menos de 50 observações por sazonalidade, o que é exatamente o cenário do presente
projeto, com 26 meses de histórico mensal. Essa evidência legitima a escolha do
SARIMAX como modelo abordado neste trabalho.

Além da contribuição operacional direta à empresa parceira, o projeto contribui
academicamente com: (i) uma estratégia de ponderação de variáveis exógenas por
importância relativa calculada via Random Forest, adaptando ao contexto do SARIMAX a
medida MDI formalizada por Breiman (2001); (ii) uma avaliação comparativa entre
granularidade mensal e diária para o mesmo conjunto de produtos perecíveis.

O sistema proposto deve permitir:

- **Visualização:** indicadores de desempenho dos modelos preditivos;
- **Acompanhamento:** tendências de demanda por período temporal e por grupo de
  produto;
- **Simulação:** efeitos de estratégias de promoção e vendas casadas;
- **Exportação:** relatórios em formatos de uso gerencial e decisório.

Com essa estrutura, a empresa poderá reduzir desperdícios de produtos perecíveis,
mitigar rupturas de estoque e aumentar a assertividade no planejamento comercial e
logístico.

---

## 4 OBJETIVOS

### 4.1 Objetivo Geral

Desenvolver um sistema de previsão de estoque para a Floricultura Verde Perto, baseado
em dados históricos de vendas e técnicas de modelagem preditiva utilizando o modelo
SARIMAX, capaz de apoiar decisões operacionais e estratégicas de reposição e compra,
com horizonte de previsão de duas a três semanas.

### 4.2 Objetivos Específicos

- Levantar e validar requisitos funcionais e não funcionais junto aos stakeholders,
  pessoas ou grupos envolvidos ou afetados pelo desenvolvimento do sistema da empresa
  parceira, garantindo que o sistema atenda às necessidades reais de operação e gestão.

- Estruturar pipeline, sequência de etapas realizadas desde a entrada dos dados até a
  geração dos resultados, automatizado de ingestão e tratamento de dados provenientes
  de planilhas mensais exportadas do sistema financeiro, incluindo deduplicação,
  normalização e discretização de variáveis categóricas.

- Realizar análise exploratória dos dados históricos para identificar padrões de
  sazonalidade, tendências, comportamento por unidade operacional e perfil de demanda
  por produto.

- Desenvolver módulo de engenharia de atributos que produza variáveis exógenas mensais
  a partir da base transacional, incluindo indicadores de mercado, indicadores
  específicos por produto e variáveis temporais derivadas.

- Implementar estratégia de ponderação das variáveis exógenas por importância relativa
  calculada via Random Forest, visando reduzir o impacto da multicolinearidade sobre os
  coeficientes estimados pelo SARIMAX.

- Treinar modelos SARIMAX com seleção automática de ordem via Critério de Informação de
  Akaike (AIC) para os produtos de maior volume, com atualização semanal automatizada.

- Avaliar o desempenho dos modelos com métricas de erro padronizadas (MAE, RMSE, MAPE,
  SMAPE e R²) em conjuntos de teste hold-out, dividir parte dos dados para avaliar o
  modelo após o treinamento, e validação walk-forward, técnica de validação em que o
  modelo é treinado com dados anteriores e testado em períodos futuros simulando uma
  situação real, comparando as granularidades mensais e diárias.

- Implementar dashboard interativo com indicadores de desempenho do modelo,
  visualizações de tendências de demanda, módulo de upload de planilhas e exportação
  de relatórios.

- Disponibilizar módulo de simulação de promoções e vendas conjugadas de produtos para
  apoio à decisão comercial.

- Produzir documentação funcional e técnica para uso, manutenção e evolução da
  solução.

---

## 5 REFERENCIAL TEÓRICO

A previsão de demanda é tema consolidado na literatura de análise temporal e gestão de
operações, com abordagem de modelos estatísticos e de aprendizado de máquina para
capturar tendência, sazonalidade e efeitos exógenos (HYNDMAN; ATHANASOPOULOS, 2021). A
escolha do modelo deve considerar disponibilidade de dados, interpretabilidade e custo
operacional.

O modelo SARIMAX (*Seasonal AutoRegressive Integrated Moving Average with eXogenous
inputs*) constitui a extensão natural da metodologia Box-Jenkins (BOX et al., 2015)
para séries com sazonalidade e influências externas. O modelo captura simultaneamente
componentes autorregressivos (AR), de médias móveis (MA) e de diferenciação (I) em
escalas regular e sazonal, incorporando adicionalmente um vetor de regressores exógenos
cujos coeficientes são estimados conjuntamente por máxima verossimilhança. A seleção
das ordens do modelo é realizada por minimização do Critério de Informação de Akaike
(AIC), procedimento que equilibra qualidade de ajuste e parcimônia.

A adequação do SARIMAX para varejo perecível foi investigada de forma pioneira por
Arunraj, Ahrens e Fernandes (2016), que demonstraram, em contexto de supermercado, a
superioridade da abordagem SARIMAX com variáveis exógenas de calendário e promoção em
relação a modelos SARIMA puros, alcançando ganhos de acurácia consistentes em produtos
de alta rotatividade. Esses resultados foram corroborados por Pavlyshenko (2019), que
confirmou MAPE inferior a 5% para itens de alto giro, com redução de até 18% no erro
pela inclusão de variáveis exógenas adicionais. O setor de floricultura compartilha com
o varejo alimentar perecível os atributos de alta perecibilidade, sazonalidade marcada
por datas comemorativas e dependência de fatores externos, tornando a abordagem
diretamente aplicável.

Para amostras pequenas, como séries mensais com 26 observações, Makridakis, Spiliotis e
Assimakopoulos (2020) demonstraram na competição M4 que modelos estatísticos da família
ARIMA superam consistentemente abordagens de aprendizado de máquina. Esse resultado
fundamenta a escolha do SARIMAX como modelo central em detrimento de alternativas como
redes neurais e modelos de árvore de decisão, que tendem ao sobreajuste (ou
*overfitting* — ocorre quando um modelo se ajusta excessivamente aos dados de
treinamento) para um número de amostras reduzidas.

A estratégia de ponderação das variáveis exógenas por importância relativa
fundamenta-se na medida MDI (*Mean Decrease in Impurity*), uma técnica utilizada para
medir a importância das variáveis em modelos de aprendizado de máquina, calculada por
Florestas Aleatórias (BREIMAN, 2001). Essa abordagem reduz o impacto da
multicolinearidade entre variáveis de mercado altamente correlacionadas sem incorrer
nos vieses da seleção stepwise convencional, método de seleção automática de variáveis
que adiciona ou remove atributos do modelo com base em critérios estatísticos.

Para produtos com demanda irregular caracterizados por Coeficiente de Variação (CV)
superior a 0,7, os autores Syntetos e Boylan (2005) demonstraram que modelos
convencionais de séries temporais produzem resultados significativamente piores,
justificando o desenvolvimento de módulos específicos para demanda intermitente nas
etapas futuras do sistema.

No contexto de engenharia de software, o desenho arquitetural e a estratégia de
validação são determinantes para a qualidade da entrega (SOMMERVILLE, 2018;
PRESSMAN; MAXIM, 2021). Para ambientes de negócio com variação sazonal elevada, o uso
de indicadores de erro e o monitoramento contínuo de desempenho preditivo é
indispensável (HYNDMAN; ATHANASOPOULOS, 2021).

---

## 6 METODOLOGIA ADOTADA

A condução do projeto segue abordagem iterativa e incremental, com ciclos de
levantamento, implementação, validação e refinamento.

### 6.1 Metodologia de Desenvolvimento de Software

Será utilizada abordagem ágil, com entregas parciais orientadas a valor. Cada iteração
contempla definição de histórias de usuário, implementação, testes e validação com a
entidade parceira. O processo de desenvolvimento segue o modelo CRISP-DM
(*Cross-Industry Standard Process for Data Mining*), uma metodologia utilizada para
organizar projetos de análise de dados em etapas como entendimento do negócio,
preparação, modelagem e avaliação, adaptado ao contexto de séries temporais, com as
seguintes fases: compreensão do negócio, compreensão dos dados, preparação dos dados,
modelagem, avaliação e implantação.

### 6.2 Levantamento e Análise de Requisitos

Os requisitos foram consolidados em reuniões formais com a entidade parceira. O
processo contemplou entrevistas com os responsáveis operacionais e análise dos
relatórios financeiros disponíveis. Os requisitos levantados foram priorizados
conforme seu impacto operacional e estratégico, organizados em requisitos funcionais e
requisitos não funcionais.

### 6.3 Ferramentas, Tecnologias e Ambientes de Desenvolvimento

A solução será estruturada com stack, conjunto de ferramentas, linguagens e bancos de
dados usados para construir uma aplicação, voltada para ciência de dados e aplicações
web, incluindo:

- **Linguagem:** Python 3.11;
- **Modelagem preditiva:** biblioteca `statsmodels` (estimação SARIMAX), `scikit-learn`
  (Random Forest para importância de variáveis);
- **Processamento de dados:** bibliotecas `pandas`, `numpy`;
- **Visualização:** bibliotecas `matplotlib`, `seaborn`, `plotly`;
- **Dashboard interativo:** bibliotecas Streamlit ou Dash (a definir após
  prototipagem);
- **Controle de versão:** Git / GitHub;
- **Ambiente de desenvolvimento:** Jupyter Notebooks para experimentação, módulos
  Python estruturados para produção.

O pipeline de dados será organizado em três camadas: (i) ingestão e armazenamento dos
arquivos XLSX mensais; (ii) processamento e geração das séries temporais e variáveis
exógenas; (iii) treinamento, avaliação e geração de previsões com atualização semanal
automatizada.

> **Nota de implementação** *(fora do texto original do artigo)*: o dashboard foi
> implementado em React (não Streamlit/Dash) após a fase de prototipagem, por já haver
> uma base React (`app-react/`) que atende RNF-01. Ver `SPECS.md` §2.2 e `docs/adr/`.

### 6.4 Ferramentas de Modelagem

Serão produzidos diagramas de casos de uso, atividades, classes, modelo de dados e
arquitetura lógica, utilizando ferramentas de modelagem UML compatíveis com os padrões
acadêmicos exigidos.

### 6.5 Procedimentos de Testes e Validação

A validação do sistema contemplará três dimensões:

1. **Validação estatística dos modelos:** aplicação de métricas de desempenho
   preditivo (MAE, RMSE, MAPE, SMAPE e R²) sobre conjuntos de teste hold-out e
   validação walk-forward com múltiplas dobras. Os limiares de aceitação adotados são
   MAPE inferior a 20% para produtos de alto giro e SMAPE inferior a 30% para pelo
   menos os dois produtos de maior volume;

2. **Testes de diagnóstico de resíduos:** Teste de Ljung-Box para verificar ausência
   de autocorrelação residual e Teste de Shapiro-Wilk para normalidade dos resíduos,
   garantindo a adequação estatística dos modelos treinados;

3. **Testes funcionais do sistema:** validação dos módulos de upload, processamento,
   visualização e exportação com dados reais da entidade parceira, verificando
   consistência, desempenho e usabilidade com usuários não técnicos.

---

## 7 REQUISITOS DO SISTEMA

Os requisitos foram validados junto à equipe da Floricultura Verde Perto e priorizados
conforme seu impacto operacional e estratégico.

### 7.1 Requisitos Funcionais

**Tabela 1** — Requisitos funcionais do sistema de previsão de estoque.

| Código | Descrição da Solicitação | Prioridade |
|---|---|---|
| REQ01 | Permitir o envio de planilhas com dados de vendas e financeiro de forma simples, sem necessidade de conhecimento técnico | Alta |
| REQ02 | Gerar previsão de quanto de cada produto será necessário no horizonte de duas a três semanas | Alta |
| REQ03 | Atualizar automaticamente os modelos preditivos toda semana com os novos dados inseridos | Alta |
| REQ04 | Exibir indicadores de desempenho do modelo de forma simples e explicada para usuários não técnicos | Alta |
| REQ05 | Apresentar gráficos de tendência de demanda por produto e por período temporal | Alta |
| REQ06 | Identificar e destacar os produtos que vendem mais em cada período, especialmente em datas especiais | Alta |
| REQ07 | Identificar produtos que costumam ser comprados juntos na mesma transação | Média |
| REQ08 | Simular promoções e vendas casadas e prever o impacto esperado nas vendas | Média |
| REQ09 | Emitir alertas automáticos quando for necessário repor o estoque de determinado produto | Alta |
| REQ10 | Exportar relatórios de previsão e desempenho nos formatos PDF e Excel | Média |
| REQ11 | Disponibilizar painel (dashboard) centralizado para visualização de dados, gráficos e upload de planilhas | Alta |
| REQ12 | Disponibilizar documentação funcional e técnica explicando como utilizar e como o sistema funciona | Média |

*Fonte: Elaborado pelos autores com base em reuniões com a entidade parceira (2026).*

### 7.2 Requisitos Não Funcionais

- **RNF-01 (Usabilidade):** a interface deve ser intuitiva e acessível a usuários não
  técnicos, sem necessidade de treinamento especializado para as funções principais de
  visualização e upload.

- **RNF-02 (Confiabilidade):** o processamento dos dados deve ser consistente e
  rastreável, com registro de logs de execução e identificação de anomalias na entrada
  de dados.

- **RNF-03 (Desempenho):** a atualização semanal dos modelos deve ser concluída em
  janela operacional aceitável (inferior a duas horas), sem comprometer a
  disponibilidade do dashboard.

- **RNF-04 (Segurança):** o sistema deve implementar controle de acesso por perfil de
  usuário e proteção dos dados operacionais da empresa, em conformidade com a Lei
  Geral de Proteção de Dados (LGPD).

- **RNF-05 (Manutenibilidade):** o código deve ser modular, documentado e versionado,
  permitindo evolução e manutenção por equipe técnica sem dependência dos
  desenvolvedores originais.

---

## 8 CRONOGRAMA

O projeto será executado em ciclos iterativos ao longo do segundo semestre de 2026, com
entregas parciais orientadas a valor, conforme o cronograma apresentado na Tabela 2.

**Tabela 2** — Cronograma de execução do projeto.

| Etapa | Período | Entrega |
|---|---|---|
| Levantamento e refinamento de requisitos | Abr./2026 | Backlog consolidado e validado com a entidade parceira |
| Modelagem e arquitetura do sistema | Mai./2026 | Diagramas técnicos UML e modelo de dados |
| Implementação do pipeline de ingestão | Jun./2026 | Pipeline inicial de ingestão e pré-processamento |
| Engenharia de atributos e análise exploratória | Jun./2026 | Base de features e relatório de EDA |
| Modelagem preditiva SARIMAX | Jul.–Ago./2026 | Modelos treinados, avaliados e documentados |
| Dashboard e módulo de simulações | Set./2026 | Interface funcional e validada com usuários |
| Testes integrados e ajustes finais | Out./2026 | Versão candidata à entrega |
| Documentação final e entrega | Nov./2026 | Projeto finalizado e documentado |

*Fonte: Elaborado pelos autores (2026).*

---

## REFERÊNCIAS

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **ABNT NBR 14724**: trabalhos acadêmicos:
apresentação. Rio de Janeiro: ABNT, 2011.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **ABNT NBR 6023**: referências: elaboração.
Rio de Janeiro: ABNT, 2018.

ARUNRAJ, N. S.; AHRENS, D.; FERNANDES, M. Application of SARIMAX model to forecast
daily sales in food retail industry. **International Journal of Operations Research
and Information Systems**, v. 7, n. 2, p. 1–21, 2016. DOI: 10.4018/IJORIS.2016040101.

BOX, G. E. P.; JENKINS, G. M.; REINSEL, G. C.; LJUNG, G. M. **Time Series Analysis:
Forecasting and Control**. 5. ed. Hoboken: Wiley, 2015.

BREIMAN, L. Random forests. **Machine Learning**, v. 45, n. 1, p. 5–32, 2001.

HYNDMAN, R. J.; ATHANASOPOULOS, G. **Forecasting: principles and practice**. 3. ed.
Melbourne: OTexts, 2021.

MAKRIDAKIS, S.; SPILIOTIS, E.; ASSIMAKOPOULOS, V. The M4 Competition: 100,000 time
series and 61 forecasting methods. **International Journal of Forecasting**, v. 36,
n. 1, p. 54–74, 2020.

PAVLYSHENKO, B. Application of SARIMAX model to forecast daily sales in food retail
industry. In: **IEEE Second International Conference on Data Stream Mining and
Processing**, 2019, Lviv. *Proceedings*... Lviv: IEEE, 2019. p. 356–360.

PRESSMAN, R. S.; MAXIM, B. R. **Engenharia de software: uma abordagem profissional**.
9. ed. Porto Alegre: AMGH, 2021.

SOMMERVILLE, I. **Engenharia de software**. 10. ed. São Paulo: Pearson, 2018.

SYNTETOS, A. A.; BOYLAN, J. E. The accuracy of intermittent demand estimates.
**International Journal of Forecasting**, v. 21, n. 2, p. 303–314, 2005.
