# Feature Specification: Sistema de Previsão de Estoque para Floricultura

**Feature Branch**: `001-sistema-previsao-estoque`

**Created**: 2026-07-28

**Status**: Approved

---

## User Scenarios & Testing

### User Story 1 — Upload de Planilha Mensal (Priority: P1)

A gestora de compras recebe, no final de cada mês, uma planilha `.xlsx` exportada do sistema
financeiro. Ela acessa o dashboard, clica em "Enviar planilha", seleciona o arquivo e aguarda
a confirmação. O sistema processa o arquivo, adiciona os novos registros à base histórica e
agenda a atualização dos modelos automaticamente.

**Why this priority**: Sem dados atualizados não há previsão. É o ponto de entrada de todo o sistema.

**Independent Test**: Pode ser testada isoladamente enviando um arquivo XLSX e verificando que
o número de registros novos aparece na tela de confirmação.

**Acceptance Scenarios**:

1. **Given** a gestora tem um arquivo `.xlsx` válido do sistema financeiro, **When** ela faz
   upload pelo dashboard, **Then** o sistema exibe "X registros adicionados, Y duplicatas
   ignoradas" em menos de 30 segundos.
2. **Given** o arquivo já foi enviado anteriormente, **When** ela envia o mesmo arquivo de
   novo, **Then** o sistema informa "0 registros novos — arquivo já processado" sem duplicar dados.
3. **Given** o arquivo está corrompido ou não segue o formato esperado, **When** ela tenta
   o upload, **Then** o sistema exibe mensagem de erro em português claro, sem travar a tela.

---

### User Story 2 — Visualização de Previsão por Produto (Priority: P1)

O gerente de operações quer saber quantas rosas vermelhas precisa comprar para o próximo mês.
Ele acessa o dashboard, busca o produto pelo nome, e visualiza um gráfico com o histórico de
vendas e a previsão para as próximas 2–3 semanas, com faixa de confiança.

**Why this priority**: É o resultado central do sistema — a previsão que apoia a decisão de compra.

**Independent Test**: Pode ser testada acessando a tela de produto e verificando se o gráfico
exibe valores históricos reais e uma linha de previsão futura com datas corretas.

**Acceptance Scenarios**:

1. **Given** o modelo do produto está treinado, **When** o gerente acessa a página do produto,
   **Then** vê gráfico com histórico mensal + previsão para os próximos 3 meses com intervalo
   de confiança de 95%.
2. **Given** o produto tem histórico insuficiente (< 15 meses), **When** o gerente acessa
   a página, **Then** o sistema exibe "Dados insuficientes para previsão — mínimo 15 meses
   necessários" sem mostrar gráfico vazio ou erro técnico.
3. **Given** a previsão do próximo mês é 38% acima da média recente, **When** o gerente
   acessa a lista de alertas, **Then** o produto aparece em destaque com a variação em linguagem simples.

---

### User Story 3 — Alerta Automático de Reposição (Priority: P1)

No início de cada semana a sistema atualiza os modelos e identifica quais produtos terão
demanda significativamente acima do padrão recente. A gestora recebe, no dashboard, uma lista
priorizada de produtos que precisam de atenção de compra nessa semana.

**Why this priority**: Resolve o problema central da empresa: antecipar picos de demanda sem
depender de memória organizacional.

**Independent Test**: Pode ser testada verificando se a lista de alertas aparece após o retrain
e se os produtos com maior variação aparecem no topo.

**Acceptance Scenarios**:

1. **Given** o retrain semanal foi concluído, **When** a gestora acessa "Alertas de Reposição",
   **Then** vê lista de produtos ordenada por urgência com a variação esperada em percentual.
2. **Given** nenhum produto tem variação acima de 20% no próximo mês, **When** a gestora
   acessa alertas, **Then** o sistema exibe "Nenhum alerta esta semana — demanda estável".
3. **Given** um produto tem previsão de alta por causa do Dia das Mães (maio), **When** a
   gestora vê o alerta, **Then** a justificativa menciona "período de alta temporada".

---

### User Story 4 — Controle de Acesso por Perfil (Priority: P1)

A gestora de compras (perfil `admin`) e o gerente de operações (perfil `viewer`) usam o
mesmo sistema com permissões diferentes. Ao acessar o dashboard pela primeira vez, cada
usuário vê uma tela de login. Após autenticação, `admin` pode fazer upload e disparar
retrain; `viewer` só pode visualizar previsões, alertas e exportar relatórios.

**Why this priority**: Sem controle de acesso qualquer pessoa com acesso à rede pode
alterar dados ou disparar retrain. É requisito de segurança (RNF-04, LGPD).

**Independent Test**: Pode ser testada fazendo login com credenciais `viewer` e tentando
acessar `POST /upload` — deve retornar "Acesso negado".

**Acceptance Scenarios**:

1. **Given** a gestora tem credenciais válidas, **When** ela faz login, **Then** recebe
   acesso ao dashboard completo (upload + retrain + visualização).
2. **Given** o gerente tem perfil `viewer`, **When** ele tenta fazer upload de planilha,
   **Then** o botão de upload não aparece e a API retorna "Você não tem permissão para
   esta ação".
3. **Given** o token expirou (após 8 horas), **When** o usuário tenta acessar qualquer
   tela protegida, **Then** é redirecionado para login sem perder os dados que estava vendo.
4. **Given** alguém tenta acessar `/api/v1/forecast/147` sem token, **Then** recebe
   erro "Autenticação necessária" — sem expor dados de previsão.

---

### User Story 5 — Simulação de Promoção (Priority: P2)

Antes de lançar uma promoção de 15% de desconto em arranjos de mesa, o dono quer estimar
o impacto nas vendas. Ele seleciona o produto, informa o desconto planejado e o período, e
o sistema mostra a previsão ajustada comparada com o cenário sem promoção.

**Why this priority**: Apoia decisão estratégica, mas depende dos modelos já treinados (P1).

**Independent Test**: Pode ser testada comparando a previsão base com a previsão simulada —
a simulada deve ser maior quando há desconto aplicado.

**Acceptance Scenarios**:

1. **Given** o modelo do produto está treinado, **When** o dono simula desconto de 15% em
   agosto, **Then** o sistema exibe previsão base vs. previsão simulada com delta em unidades
   e percentual.
2. **Given** dois produtos são frequentemente comprados juntos, **When** o dono simula uma
   promoção de venda casada, **Then** o sistema exibe o impacto estimado nos dois produtos.

---

### User Story 6 — Exportação de Relatório (Priority: P2)

Antes de uma reunião de planejamento mensal, a gestora quer um arquivo para apresentar.
Ela acessa o dashboard, clica em "Exportar relatório" e escolhe PDF ou Excel. O arquivo
gerado contém as previsões dos top 10 produtos e os alertas da semana.

**Why this priority**: Facilita comunicação com a diretoria, mas é secundário à visualização online.

**Independent Test**: Pode ser testada baixando o arquivo e verificando se contém previsões
e alertas com dados corretos e formatação legível.

**Acceptance Scenarios**:

1. **Given** há modelos treinados, **When** a gestora clica em "Exportar PDF", **Then** faz
   download de arquivo em menos de 10 segundos com previsões dos top 10 produtos e lista de alertas.
2. **Given** a gestora escolhe Excel, **When** o download é concluído, **Then** o arquivo
   tem abas "Previsões", "Métricas" e "Alertas" com dados tabulares prontos para edição.

---

### Edge Cases

- O que acontece quando o arquivo XLSX tem colunas fora da ordem esperada?
- Como o sistema se comporta quando todos os produtos têm demanda zero em um mês (ex: feriado prolongado)?
- O que ocorre se o retrain semanal automático falha no meio da execução?
- Como tratar produtos com código numérico vs. alfanumérico no mesmo arquivo?
- O que exibir quando o produto tem previsão negativa (artefato matemático do modelo)?

---

## Requirements

### Functional Requirements

- **FR-000**: O sistema MUST exigir autenticação (login com e-mail + senha) para acessar
  qualquer funcionalidade. Usuários não autenticados MUST ser redirecionados para a tela de login.
- **FR-000a**: O sistema MUST suportar dois perfis: `admin` (upload, retrain, export completo)
  e `viewer` (somente visualização de previsões, alertas e exportação). A UI MUST adaptar-se
  ao perfil — botões de upload e retrain MUST NOT ser exibidos para `viewer`.
- **FR-000b**: A API MUST NOT retornar dados pessoais de clientes (`nome`, `código`, CPF)
  em nenhum endpoint — apenas dados agregados por produto (LGPD).
- **FR-001**: O sistema MUST permitir upload de arquivos `.xlsx` e `.xlsm` de até 50 MB sem
  necessidade de configuração técnica pelo usuário.
- **FR-002**: O sistema MUST processar o arquivo, deduplicar registros por `(doc_numero, produto_cod)`
  e confirmar quantos registros foram adicionados, ignorados e duplicados.
- **FR-003**: O sistema MUST gerar previsão de demanda mensal para os produtos de maior volume
  com horizonte de 1 a 3 meses à frente.
- **FR-004**: O sistema MUST exibir intervalo de confiança de 95% junto à previsão.
- **FR-005**: O sistema MUST atualizar automaticamente os modelos toda segunda-feira às 02h00,
  sem intervenção do usuário.
- **FR-006**: O sistema MUST emitir alertas quando a previsão do próximo mês exceder em 20%
  ou mais a média dos últimos 3 meses do produto.
- **FR-007**: O sistema MUST identificar e destacar os meses de alta temporada (maio, outubro,
  novembro, dezembro) nas visualizações e alertas.
- **FR-008**: O sistema MUST permitir simulação do impacto de desconto sobre a previsão de
  um produto, com comparação entre cenário base e cenário simulado.
- **FR-009**: O sistema MUST exportar relatório em PDF e Excel contendo previsões e alertas.
- **FR-010**: O sistema MUST exibir indicadores de qualidade do modelo em linguagem acessível
  (ex: "Precisão estimada: 92%"), não em jargão técnico.
- **FR-011**: O sistema MUST registrar log de cada upload e retrain, consultável no dashboard.
- **FR-012**: O sistema MUST sinalizar produtos com dados insuficientes (< 15 meses) sem
  exibir previsão para eles.

### Key Entities

- **Produto**: identificado por `produto_cod` + `produto_nome`; possui histórico de vendas mensais
  e, opcionalmente, um modelo treinado associado.
- **Transação**: registro individual de venda com data, quantidade, valor, cliente, vendedor
  e unidade operacional.
- **Modelo**: artefato SARIMAX treinado para um produto; possui ordem, métricas de desempenho,
  data de treino e status (`trained`, `low_confidence`, `insufficient_data`, `error`).
- **Previsão**: resultado do modelo para um produto em um período futuro; possui valor central
  e intervalo de confiança.
- **Alerta**: sinal gerado quando a previsão indica variação significativa; possui severidade,
  produto, período e justificativa em linguagem natural.
- **Relatório**: exportação consolidada de previsões e alertas em PDF ou Excel.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: A gestora consegue fazer upload de uma planilha e visualizar a confirmação
  de processamento em menos de 30 segundos para arquivos de até 50 MB.
- **SC-002**: A previsão dos 2 produtos de maior volume atinge SMAPE ≤ 30% medido em
  conjunto de teste hold-out (3 meses retidos).
- **SC-003**: A previsão dos produtos de alto giro atinge MAPE ≤ 20% no mesmo hold-out.
- **SC-004**: A atualização semanal automática dos modelos conclui em menos de 2 horas
  para os 20 produtos de maior volume.
- **SC-005**: A gestora consegue acessar a lista de alertas e exportar o relatório PDF
  em menos de 3 cliques a partir da tela inicial.
- **SC-006**: 100% dos alertas emitidos têm justificativa em português sem termos técnicos.
- **SC-008**: Usuário com perfil `viewer` MUST NOT conseguir realizar upload ou retrain
  — tentativas via API ou UI retornam mensagem de permissão negada.
- **SC-009**: Nenhum dado pessoal de clientes é retornado pela API em nenhum cenário
  (validado por inspeção de todos os payloads de resposta).
- **SC-007**: O sistema mantém disponibilidade do dashboard durante o retrain semanal
  (retrain ocorre em background sem bloquear consultas).

---

## Assumptions

- Os usuários finais acessam o sistema via navegador web moderno (Chrome, Edge, Firefox).
- Os arquivos XLSX são exportados do mesmo sistema financeiro que gerou a base histórica
  existente — estrutura de colunas é consistente entre arquivos.
- O horizonte de reposição operacional da empresa é de 2 a 3 semanas, mapeado para
  granularidade mensal (previsão do próximo mês inteiro).
- Autenticação e controle de acesso por perfil (JWT, perfis `admin`/`viewer`) estão
  incluídos nesta especificação como P1 (FR-000, FR-000a, FR-000b, US4).
- A empresa não possui sistema de estoque em tempo real; os alertas são baseados em
  variação relativa à demanda histórica, não em nível de estoque atual.
- Mobile responsiveness é desejável mas não bloqueante para a entrega inicial.
- O número de produtos com modelo treinado estará na faixa de 15 a 30 (top N por volume),
  não todos os 5.100+ SKUs do catálogo.
