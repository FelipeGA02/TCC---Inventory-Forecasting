# SISTEMA DE PREVISÃO DE ESTOQUE: UMA SOLUÇÃO INTELIGENTE PARA A GESTÃO DE DEMANDA EM FLORICULTURA

**Daniel Nunes da Silva | Felipe Gurgel Araújo**

Centro Universitário Dom Helder — Bacharelado em Ciência da Computação

Orientador de conteúdo: Prof. Marcos Wander Rodrigues

Orientador de metodologia: Prof. Me. Ricardo Luiz de Freitas

Belo Horizonte — 2026

---

## RESUMO

O presente projeto técnico propõe o desenvolvimento de um sistema de previsão de estoque para uma rede de floricultura com três unidades operacionais, empresa com histórico consolidado de vendas cobrindo o período de janeiro de 2024 a fevereiro de 2026. O setor de floricultura apresenta desafios singulares decorrentes da alta perecibilidade dos produtos, da sazonalidade acentuada e da oscilação da demanda em datas comemorativas. A ausência de previsão estruturada gera riscos de ruptura de estoque e perdas por excesso de compra. A solução proposta contempla um fluxo completo de processamento de dados históricos de vendas, com engenharia de atributos, treinamento e atualização automática semanal de modelos preditivos baseados em SARIMAX (Seasonal AutoRegressive Integrated Moving Average with eXogenous inputs), apresentação de indicadores em dashboard interativo e simulações de cenários de promoção e vendas casadas. O horizonte de previsão definido é de duas a três semanas, alinhado ao ciclo operacional de reposição da empresa. A metodologia adota abordagem ágil e iterativa, com entregas parciais orientadas a valor. Os requisitos foram consolidados em reuniões formais com a entidade parceira e incluem módulos de upload de planilhas, geração automática de previsões, emissão de alertas de reposição, exportação de relatórios e simulação de estratégias comerciais. Espera-se, como resultado, a redução de desperdícios, a mitigação de rupturas e o aumento da assertividade no planejamento logístico e comercial da empresa.

**Palavras-chave:** previsão de demanda; gestão de estoque; floricultura; aprendizado de máquina; SARIMAX; dashboard.

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

O presente projeto técnico propõe o desenvolvimento de um sistema de previsão de estoque para uma rede de floricultura com unidades operacionais em Minas Gerais. A empresa possui aproximadamente dois anos de histórico consolidado de vendas e dados financeiros, totalizando mais de 324 mil registros transacionais com informações detalhadas por transação, segmentação por grupos de produtos e separação de dados entre as três unidades operacionais.

Embora os dados disponíveis apresentem potencial analítico significativo, demandam etapas sistemáticas de tratamento e normalização para viabilizar seu uso efetivo em modelagem preditiva. A solução proposta contempla um fluxo completo de processamento: ingestão de dados, tratamento e normalização, engenharia de atributos, treinamento e atualização automática de modelos preditivos, apresentação de indicadores em dashboard interativo e simulações de cenários de promoção e vendas casadas. O horizonte de previsão foi definido em duas a três semanas, alinhado ao ciclo operacional de reposição atual da empresa.

A base de dados disponível cobre o período de janeiro de 2024 a fevereiro de 2026, abrangendo mais de 5.100 produtos distintos (SKUs), aproximadamente 2.500 clientes únicos, 38 vendedores e três unidades operacionais. Esse conjunto de dados constitui um insumo robusto para a construção de modelos preditivos capazes de capturar padrões sazonais, tendências e influências de variáveis externas sobre a demanda.

---

## 2 CONTEXTO E PROBLEMATIZAÇÃO

A gestão de estoque no setor de floricultura apresenta desafios singulares, fortemente impactados pela alta perecibilidade dos produtos, sazonalidade acentuada e oscilação significativa da demanda em períodos de datas comemorativas relevantes, como Dia das Mães, Dia dos Namorados, Dia das Mulheres e Natal. A ausência de previsão estruturada aumenta o risco de ruptura de estoque e perdas por excesso de compra, impactando negativamente a margem operacional da empresa.

Atualmente, o controle de estoque é realizado com apoio predominante do conhecimento tácito da equipe e de relatórios operacionais gerados manualmente a partir do sistema financeiro. Parte dos dados é disponibilizada em relatórios estruturados e parte em planilhas exportadas, exigindo etapas adicionais de extração e padronização. Essa heterogeneidade eleva o esforço técnico da etapa inicial de ingestão. Além disso, a empresa opera com múltiplos grupos de produtos, com flores de corte como categorias de maior valor estratégico e maior dificuldade de previsão.

O estoque excessivo resulta em perda direta pelo descarte de produtos perecíveis não vendidos, enquanto o estoque insuficiente representa vendas perdidas em dias de pico — que podem representar 30 a 40% do faturamento mensal em datas comemorativas específicas. A inexistência de um sistema de previsão estruturado impede que a equipe gestora antecipe essas oscilações com base em evidências quantitativas, limitando o planejamento ao horizonte imediato e à memória organizacional.

O problema central que este projeto busca endereçar pode ser sintetizado nas seguintes questões operacionais:

- Como determinar quantas unidades de cada produto comprar para o período seguinte sem incorrer em excesso ou escassez?
- Como antecipar o impacto de datas comemorativas sobre a demanda de produtos específicos?
- Como avaliar o efeito de promoções e estratégias de vendas casadas sobre o volume vendido?
- Qual produto sugerir ao cliente que está comprando um buquê, maximizando o valor da transação?

A ausência de respostas estruturadas a essas perguntas constitui uma lacuna operacional que este projeto propõe preencher por meio de um sistema baseado em dados históricos e técnicas de modelagem preditiva.

---

## 3 JUSTIFICATIVA

A situação atual da empresa — planejamento de estoque por conhecimento tácito, relatórios manuais e ausência de previsão quantitativa — gera ineficiências operacionais que se traduzem diretamente em perdas financeiras. A situação desejada é um sistema integrado e unificado, acessível a usuários não técnicos, capaz de receber dados periodicamente, atualizar automaticamente previsões em cadência semanal e apresentar recomendações fundamentadas em evidências quantitativas.

A justificativa científica para a adoção de modelos da família SARIMAX neste contexto reside em sua adequação comprovada para séries temporais sazonais com variáveis exógenas. O estudo de Pavlyshenko (2019), referência central deste trabalho, demonstrou que o SARIMAX aplicado ao varejo de alimentos perecíveis — domínio com características análogas à floricultura — produz erros de previsão inferiores a 5% em média para produtos de alto giro, com redução adicional de até 18% pelo uso de variáveis exógenas como promoções e calendário comemorativo. Flores e plantas compartilham com o varejo alimentar perecível os atributos de alta perecibilidade, forte sazonalidade e impacto elevado de eventos externos, o que reforça a pertinência metodológica da abordagem proposta.

A justificativa técnica complementar reside nos resultados da competição M4 (MAKRIDAKIS; SPILIOTIS; ASSIMAKOPOULOS, 2020), que demonstrou empiricamente que modelos estatísticos da família ARIMA superam abordagens de aprendizado de máquina em séries com menos de 50 observações por sazonalidade — exatamente o cenário do presente projeto, com 26 meses de histórico mensal. Essa evidência legitima a escolha do SARIMAX como modelo central, em detrimento de alternativas de maior complexidade computacional.

Além da contribuição operacional direta à empresa parceira, o projeto contribui academicamente com: (i) uma estratégia de ponderação de variáveis exógenas por importância relativa calculada via Random Forest, adaptando ao contexto do SARIMAX a medida MDI formalizada por Breiman (2001); (ii) uma avaliação comparativa entre granularidades mensal e diária para o mesmo conjunto de produtos perecíveis.

O sistema proposto deverá permitir:

- **Visualização:** indicadores de desempenho dos modelos preditivos de forma acessível a usuários não técnicos.
- **Acompanhamento:** tendências de demanda por período temporal e por grupo de produto.
- **Simulação:** efeitos de estratégias de promoção e vendas casadas sobre o volume esperado de vendas.
- **Exportação:** relatórios em formatos de uso gerencial e decisório.

Com essa estrutura, espera-se que a empresa consiga reduzir desperdícios de produtos perecíveis, mitigar rupturas de estoque e aumentar a assertividade no planejamento comercial e logístico.

---

## 4 OBJETIVOS

### 4.1 Objetivo Geral

Desenvolver um sistema de previsão de estoque para uma rede de floricultura, baseado em dados históricos de vendas e técnicas de modelagem preditiva com o modelo SARIMAX, capaz de apoiar decisões operacionais e estratégicas de reposição e compra, com horizonte de previsão de duas a três semanas.

### 4.2 Objetivos Específicos

- Levantar e validar requisitos funcionais e não funcionais junto aos stakeholders da empresa parceira, garantindo que o sistema atenda às necessidades reais de operação e gestão.

- Estruturar pipeline automatizado de ingestão e tratamento de dados provenientes de planilhas mensais exportadas do sistema financeiro, incluindo deduplicação, normalização e discretização de variáveis categóricas.

- Realizar análise exploratória dos dados históricos para identificar padrões de sazonalidade, tendências, comportamento por unidade operacional e perfil de demanda por produto.

- Desenvolver módulo de engenharia de atributos que produza variáveis exógenas mensais a partir da base transacional, incluindo indicadores de mercado, indicadores específicos por produto e variáveis temporais derivadas.

- Implementar estratégia de ponderação das variáveis exógenas por importância relativa calculada via Random Forest, visando reduzir o impacto da multicolinearidade sobre os coeficientes estimados pelo SARIMAX.

- Treinar modelos SARIMAX com seleção automática de ordem via Critério de Informação de Akaike (AIC) para os produtos de maior volume, com atualização semanal automatizada.

- Avaliar o desempenho dos modelos com métricas padronizadas (MAE, RMSE, MAPE, SMAPE e R²) em conjuntos de teste hold-out e validação walk-forward, comparando granularidades mensal e diária.

- Implementar dashboard interativo com indicadores de desempenho do modelo, visualizações de tendências de demanda, módulo de upload de planilhas e exportação de relatórios.

- Disponibilizar módulo de simulação de promoções e vendas casadas para apoio à decisão comercial.

- Produzir documentação funcional e técnica para uso, manutenção e evolução da solução.

---

## 5 REFERENCIAL TEÓRICO

A previsão de demanda é tema consolidado na literatura de análise temporal e gestão de operações, com abordagem de modelos estatísticos e de aprendizado de máquina para capturar tendência, sazonalidade e efeitos exógenos (HYNDMAN; ATHANASOPOULOS, 2021). A escolha do modelo deve considerar disponibilidade de dados, interpretabilidade e custo operacional.

O modelo SARIMAX (Seasonal AutoRegressive Integrated Moving Average with eXogenous inputs) constitui a extensão natural da metodologia Box-Jenkins (BOX et al., 2015) para séries com sazonalidade e influências externas. O modelo captura simultaneamente componentes autorregressivos (AR), de médias móveis (MA) e de diferenciação (I) em escalas regular e sazonal, incorporando adicionalmente um vetor de regressores exógenos cujos coeficientes são estimados conjuntamente por máxima verossimilhança. A seleção das ordens do modelo é realizada por minimização do Critério de Informação de Akaike (AIC), procedimento que equilibra qualidade de ajuste e parcimônia.

A adequação do SARIMAX para varejo perecível foi demonstrada por Pavlyshenko (2019) em supermercados: o modelo produziu MAPE inferior a 5% para itens de alto giro, com redução de até 18% no erro pela inclusão de variáveis exógenas de calendário e promoção. O setor de floricultura compartilha com o varejo alimentar perecível os atributos de alta perecibilidade, sazonalidade marcada por datas comemorativas e dependência de fatores externos, tornando a abordagem diretamente aplicável.

Para amostras pequenas — como séries mensais com 26 observações —, Makridakis, Spiliotis e Assimakopoulos (2020) demonstraram na competição M4 que modelos estatísticos da família ARIMA superam consistentemente abordagens de aprendizado de máquina. Esse resultado fundamenta a escolha do SARIMAX como modelo central em detrimento de alternativas como redes neurais e modelos de árvore, que tendem ao sobreajuste em amostras reduzidas.

A estratégia de ponderação das variáveis exógenas por importância relativa — uma das contribuições metodológicas deste projeto — fundamenta-se na medida MDI (Mean Decrease in Impurity) calculada por Florestas Aleatórias (BREIMAN, 2001). Essa abordagem reduz o impacto da multicolinearidade entre variáveis de mercado altamente correlacionadas sem incorrer nos vieses da seleção stepwise convencional.

Para produtos com demanda irregular — caracterizados por Coeficiente de Variação (CV) superior a 0,7 —, Syntetos e Boylan (2005) demonstraram que modelos convencionais de séries temporais produzem resultados significativamente piores, justificando o desenvolvimento de módulos específicos para demanda intermitente nas etapas futuras do sistema.

No contexto de engenharia de software, o desenho arquitetural e a estratégia de validação são determinantes para a qualidade da entrega. Para ambientes de negócio com variação sazonal elevada, o uso de indicadores de erro e monitoramento contínuo do desempenho preditivo é indispensável (HYNDMAN; ATHANASOPOULOS, 2021).

---

## 6 METODOLOGIA ADOTADA

A condução do projeto segue abordagem iterativa e incremental, com ciclos de levantamento, implementação, validação e refinamento.

### 6.1 Metodologia de Desenvolvimento de Software

Será utilizada abordagem ágil, com entregas parciais orientadas a valor. Cada iteração contempla definição de histórias de usuário, implementação, testes e validação com a entidade parceira. O processo de desenvolvimento segue o modelo CRISP-DM (Cross-Industry Standard Process for Data Mining) adaptado ao contexto de séries temporais, com as seguintes fases: compreensão do negócio, compreensão dos dados, preparação dos dados, modelagem, avaliação e implantação.

### 6.2 Levantamento e Análise de Requisitos

Os requisitos foram consolidados em reuniões formais com a entidade parceira. O processo contemplou entrevistas com os responsáveis operacionais e análise dos relatórios financeiros disponíveis. Os requisitos levantados foram priorizados conforme seu impacto operacional e estratégico, organizados em funcionais e não funcionais conforme apresentado na Seção 7.

### 6.3 Ferramentas, Tecnologias e Ambientes de Desenvolvimento

A solução será estruturada com stack voltada para ciência de dados e aplicações web, incluindo:

- **Linguagem:** Python 3.11
- **Modelagem preditiva:** biblioteca `statsmodels` (estimação SARIMAX), `scikit-learn` (Random Forest para importância de variáveis)
- **Processamento de dados:** `pandas`, `numpy`
- **Visualização:** `matplotlib`, `seaborn`, `plotly`
- **Dashboard interativo:** Streamlit ou Dash (a definir após prototipagem)
- **Controle de versão:** Git / GitHub
- **Ambiente de desenvolvimento:** Jupyter Notebooks para experimentação, módulos Python estruturados para produção

O pipeline de dados será organizado em três camadas: (i) ingestão e armazenamento dos arquivos XLSX mensais; (ii) processamento e geração das séries temporais e variáveis exógenas; (iii) treinamento, avaliação e geração de previsões com atualização semanal automatizada.

### 6.4 Ferramentas de Modelagem

Serão produzidos diagramas de casos de uso, atividades, classes, modelo de dados e arquitetura lógica, utilizando ferramentas de modelagem UML compatíveis com os padrões acadêmicos exigidos.

### 6.5 Procedimentos de Testes e Validação

A validação do sistema contemplará três dimensões:

**Validação estatística dos modelos:** aplicação de métricas de desempenho preditivo (MAE, RMSE, MAPE, SMAPE e R²) sobre conjuntos de teste hold-out e validação walk-forward com múltiplas dobras. Os limiares de aceitação adotados são MAPE inferior a 20% para produtos de alto giro e SMAPE inferior a 30% para pelo menos os dois produtos de maior volume.

**Testes de diagnóstico de resíduos:** Teste de Ljung-Box para verificar ausência de autocorrelação residual e Teste de Shapiro-Wilk para normalidade dos resíduos, garantindo a adequação estatística dos modelos treinados.

**Testes funcionais do sistema:** validação dos módulos de upload, processamento, visualização e exportação com dados reais da entidade parceira, verificando consistência, desempenho e usabilidade com usuários não técnicos.

---

## 7 REQUISITOS DO SISTEMA

Os requisitos foram validados junto à equipe da entidade parceira e priorizados conforme seu impacto operacional e estratégico.

### 7.1 Requisitos Funcionais

**Tabela 1** — Requisitos funcionais do sistema de previsão de estoque.

| Codigo | Descricao | Prioridade |
|---|---|---|
| REQ-01 | Permitir o envio de planilhas com dados de vendas e financeiro de forma simples, sem necessidade de conhecimento técnico | Alta |
| REQ-02 | Gerar previsão de quanto de cada produto será necessário no horizonte de duas a três semanas | Alta |
| REQ-03 | Atualizar automaticamente os modelos preditivos toda semana com os novos dados inseridos | Alta |
| REQ-04 | Exibir indicadores de desempenho do modelo de forma simples e explicada para usuários não técnicos | Alta |
| REQ-05 | Apresentar gráficos de tendência de demanda por produto e por período temporal | Alta |
| REQ-06 | Identificar e destacar os produtos que vendem mais em cada período, especialmente em datas especiais | Alta |
| REQ-07 | Identificar produtos que costumam ser comprados juntos na mesma transação | Média |
| REQ-08 | Simular promoções e vendas casadas e prever o impacto esperado nas vendas | Média |
| REQ-09 | Emitir alertas automáticos quando for necessário repor o estoque de determinado produto | Alta |
| REQ-10 | Exportar relatórios de previsão e desempenho nos formatos PDF e Excel | Média |
| REQ-11 | Disponibilizar painel (dashboard) centralizado para visualização de dados, gráficos e upload de planilhas | Alta |
| REQ-12 | Disponibilizar documentação funcional e técnica explicando como utilizar e como o sistema funciona internamente | Média |

*Fonte: Elaborado pelos autores com base em reuniões com a entidade parceira (2026).*

### 7.2 Requisitos Não Funcionais

- **RNF-01 (Usabilidade):** A interface deve ser intuitiva e acessível a usuários não técnicos, sem necessidade de treinamento especializado para as funções principais de visualização e upload.

- **RNF-02 (Confiabilidade):** O processamento dos dados deve ser consistente e rastreável, com registro de logs de execução e identificação de anomalias na entrada de dados.

- **RNF-03 (Desempenho):** A atualização semanal dos modelos deve ser concluída em janela operacional aceitável (inferior a duas horas), sem comprometer a disponibilidade do dashboard.

- **RNF-04 (Segurança):** O sistema deve implementar controle de acesso por perfil de usuário e proteção dos dados operacionais da empresa, em conformidade com a Lei Geral de Proteção de Dados (LGPD).

- **RNF-05 (Manutenibilidade):** O código deve ser modular, documentado e versionado, permitindo evolução e manutenção por equipe técnica sem dependência dos desenvolvedores originais.

---

## 8 CRONOGRAMA

O projeto será executado em ciclos iterativos ao longo do segundo semestre de 2026, com entregas parciais orientadas a valor, conforme o cronograma apresentado na Tabela 2.

**Tabela 2** — Cronograma de execução do projeto.

| Etapa | Periodo | Entrega |
|---|---|---|
| Levantamento e refinamento de requisitos | Abr./2026 | Backlog consolidado e validado com a entidade |
| Modelagem e arquitetura do sistema | Mai./2026 | Diagramas técnicos UML e modelo de dados |
| Implementação do pipeline de ingestão | Jun./2026 | Pipeline inicial de ingestão e pré-processamento |
| Engenharia de atributos e análise exploratória | Jun./2026 | Base de features e relatório de EDA |
| Modelagem preditiva SARIMAX | Jul./2026 -- Ago./2026 | Modelos treinados, avaliados e documentados |
| Dashboard e módulo de simulações | Set./2026 | Interface funcional e validada com usuários |
| Testes integrados e ajustes finais | Out./2026 | Versão candidata à entrega |
| Documentação final e entrega | Nov./2026 | Projeto finalizado e documentado |

*Fonte: Elaborado pelos autores (2026).*

---

## REFERÊNCIAS

BOX, G. E. P.; JENKINS, G. M.; REINSEL, G. C.; LJUNG, G. M. **Time Series Analysis: Forecasting and Control**. 5. ed. Hoboken: Wiley, 2015.

BREIMAN, L. Random forests. **Machine Learning**, v. 45, n. 1, p. 5-32, 2001.

HYNDMAN, R. J.; ATHANASOPOULOS, G. **Forecasting: Principles and Practice**. 3. ed. Melbourne: OTexts, 2021. Disponivel em: https://otexts.com/fpp3/. Acesso em: 15 mar. 2026.

MAKRIDAKIS, S.; SPILIOTIS, E.; ASSIMAKOPOULOS, V. The M4 Competition: 100,000 time series and 61 forecasting methods. **International Journal of Forecasting**, v. 36, n. 1, p. 54-74, 2020.

PAVLYSHENKO, B. Application of SARIMAX model to forecast daily sales in food retail industry. In: **IEEE Second International Conference on Data Stream Mining and Processing**, 2019, Lviv. *Proceedings*... Lviv: IEEE, 2019. p. 356-360.

SYNTETOS, A. A.; BOYLAN, J. E. The accuracy of intermittent demand estimates. **International Journal of Forecasting**, v. 21, n. 2, p. 303-314, 2005.
