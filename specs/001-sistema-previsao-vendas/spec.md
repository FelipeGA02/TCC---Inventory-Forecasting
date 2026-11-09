# Feature Specification: Sistema de Previsão de Vendas para Floricultura

**Feature Branch**: `001-sistema-previsao-vendas`

**Created**: 2026-07-28

**Status**: Revisado em 2026-08-30 — escopo alterado de **previsão mensal** para
**recomendação de reposição diária** (produtos perecíveis). Ver
`docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md`.

---

## User Scenarios & Testing

### User Story 1 — Upload de Planilha de Vendas (Priority: P1)

A gestora de compras recebe, periodicamente, uma planilha `.xlsx` exportada do sistema
financeiro. Ela acessa o dashboard, clica em "Enviar planilha", seleciona o arquivo e aguarda
a confirmação. O sistema processa o arquivo, adiciona os novos registros à base histórica e
agenda a atualização dos modelos.

**Why this priority**: Sem dados atualizados não há previsão. É o ponto de entrada de todo o sistema.

**Independent Test**: Enviar um arquivo XLSX e verificar que o número de registros novos
aparece na tela de confirmação.

**Acceptance Scenarios**:

1. **Given** a gestora tem um arquivo `.xlsx` válido do sistema financeiro, **When** ela faz
   upload pelo dashboard, **Then** o sistema exibe "X registros adicionados, Y duplicatas
   ignoradas" em menos de 30 segundos.
2. **Given** o arquivo já foi enviado anteriormente, **When** ela envia o mesmo arquivo de
   novo, **Then** o sistema informa "0 registros novos — arquivo já processado" sem duplicar dados.
3. **Given** o arquivo está corrompido ou não segue o formato esperado, **When** ela tenta
   o upload, **Then** o sistema exibe mensagem de erro em português claro, sem travar a tela.

---

### User Story 2 — Previsão Diária de Demanda por Produto (Priority: P1)

O gerente de operações quer saber quantas rosas vermelhas vão sair **em cada um dos
próximos dias**. Ele acessa o dashboard, busca o produto pelo nome, e visualiza um gráfico
com o histórico diário de vendas e a previsão para os próximos 14 dias, com faixa de
confiança e destaque para fins de semana e datas comemorativas.

**Why this priority**: É a base numérica da recomendação de reposição (US3).

**Acceptance Scenarios**:

1. **Given** a categoria do produto tem modelo treinado, **When** o gerente acessa a página
   do produto, **Then** vê gráfico com histórico diário + previsão para os próximos 14 dias
   com intervalo de confiança de 95%, com sábados/domingos e feriados marcados.
2. **Given** a categoria do produto tem histórico insuficiente (< 180 dias), **When** o
   gerente acessa a página, **Then** o sistema exibe "Dados insuficientes para previsão —
   mínimo de 6 meses de histórico da categoria" sem gráfico vazio nem erro técnico.
3. **Given** o SKU tem pouquíssimas vendas isoladas, **When** o gerente acessa a página,
   **Then** a previsão é exibida com aviso "Estimativa aproximada — produto de baixo giro".

---

### User Story 3 — Recomendação de Reposição Diária (Priority: P1)

Todo dia de manhã a gestora abre o dashboard e vê, para cada produto de maior volume,
**quanto comprar hoje** para cobrir a demanda até a próxima reposição sem que o produto
murche no balcão. A recomendação considera a validade do produto (flores de corte duram
poucos dias), um estoque de segurança e, se informado, o estoque atual.

**Why this priority**: É o resultado central do sistema — a decisão de compra de produto
perecível, que hoje depende da memória de quem compra.

**Independent Test**: Verificar que a lista de reposição do dia mostra, por produto,
quantidade sugerida, data-limite de cobertura e risco de perda/ruptura.

**Acceptance Scenarios**:

1. **Given** os modelos foram atualizados, **When** a gestora acessa "Reposição de Hoje",
   **Then** vê uma lista por produto com: quantidade sugerida, "cobre até [data]", cadência
   sugerida ("repor a cada N dias") e um selo de risco (perda / ruptura / ok).
2. **Given** um produto tem validade de 4 dias e demanda concentrada no fim de semana,
   **When** a gestora vê a recomendação numa terça, **Then** a quantidade sugerida cobre
   só até sexta e a justificativa menciona "validade curta — evitar sobra".
3. **Given** a previsão dos próximos 7 dias está ≥ 20% acima da média das últimas 4 semanas,
   **When** a gestora acessa alertas, **Then** o produto aparece em destaque com a variação
   em linguagem simples e a data prevista para o pico.
4. **Given** uma data comemorativa (Dia das Mães) se aproxima, **When** a gestora vê a
   recomendação, **Then** a justificativa menciona "período de alta procura" e a antecedência sugerida.

---

### User Story 4 — Controle de Acesso por Perfil (Priority: P1)

A gestora de compras (perfil `admin`) e o gerente de operações (perfil `viewer`) usam o
mesmo sistema com permissões diferentes. Ao acessar o dashboard pela primeira vez, cada
usuário vê uma tela de login. Após autenticação, `admin` pode fazer upload e disparar
retrain; `viewer` só pode visualizar previsões, reposição, alertas e exportar relatórios.

**Why this priority**: Sem controle de acesso qualquer pessoa com acesso à rede pode
alterar dados ou disparar retrain. É requisito de segurança (RNF-04, LGPD).

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
o sistema mostra a previsão diária ajustada — e a reposição correspondente — comparada com
o cenário sem promoção.

**Why this priority**: Apoia decisão estratégica, mas depende dos modelos já treinados (P1).

**Acceptance Scenarios**:

1. **Given** a categoria do produto está treinada, **When** o dono simula desconto de 15%
   numa semana, **Then** o sistema exibe previsão base vs. simulada (por dia) com delta em
   unidades e percentual, e a reposição recalculada.
2. **Given** dois produtos são frequentemente comprados juntos, **When** o dono simula uma
   promoção de venda casada, **Then** o sistema exibe o impacto estimado nos dois produtos.

---

### User Story 6 — Exportação de Relatório (Priority: P2)

Antes de uma reunião de planejamento, a gestora quer um arquivo para apresentar. Ela acessa
o dashboard, clica em "Exportar relatório" e escolhe PDF ou Excel. O arquivo gerado contém
a reposição sugerida dos top 10 produtos para os próximos 14 dias e os alertas.

**Acceptance Scenarios**:

1. **Given** há modelos treinados, **When** a gestora clica em "Exportar PDF", **Then** faz
   download em menos de 10 segundos com a reposição dos top 10 produtos e a lista de alertas.
2. **Given** a gestora escolhe Excel, **When** o download é concluído, **Then** o arquivo
   tem abas "Reposição", "Previsão diária", "Métricas" e "Alertas" prontas para edição.

---

### Edge Cases

- Arquivo XLSX com colunas fora da ordem esperada.
- Categoria com um feriado prolongado no meio do histórico (vários dias de venda zero).
- Retrain semanal automático falha no meio da execução.
- Produto sem categoria cadastrada — cai numa categoria "Outros" com shelf-life padrão.
- Previsão diária negativa (artefato do modelo) — truncada em zero antes de exibir.
- SKU novo, sem histórico suficiente para desagregação — usa rateio uniforme da categoria.
- `shelf_life_dias` ausente para a categoria — usa `SHELF_LIFE_DEFAULT_DAYS`.

---

## Requirements

### Functional Requirements

- **FR-000**: O sistema MUST exigir autenticação (login com e-mail + senha) para acessar
  qualquer funcionalidade. Usuários não autenticados MUST ser redirecionados para o login.
- **FR-000a**: O sistema MUST suportar dois perfis: `admin` (upload, retrain, export completo)
  e `viewer` (somente visualização de previsões, reposição, alertas e exportação). A UI MUST
  adaptar-se ao perfil.
- **FR-000b**: A API MUST NOT retornar dados pessoais de clientes em nenhum endpoint —
  apenas dados agregados por produto/categoria (LGPD).
- **FR-001**: O sistema MUST permitir upload de arquivos `.xlsx` e `.xlsm` de até 50 MB sem
  configuração técnica pelo usuário.
- **FR-002**: O sistema MUST processar o arquivo, deduplicar registros e confirmar quantos
  foram adicionados, ignorados e duplicados.
- **FR-003**: O sistema MUST gerar **previsão de demanda diária** para os produtos de maior
  volume, com horizonte de **14 dias**, a partir de um modelo por `unidade × categoria`
  desagregado para o SKU.
- **FR-004**: O sistema MUST exibir intervalo de confiança de 95% junto à previsão diária.
- **FR-005**: O sistema MUST reajustar automaticamente os modelos toda segunda-feira às
  02h00 (pulando o treino, registrado como `skipped`, quando não há venda nova desde o
  último) e, ao fim de cada treino, **gerar uma vez a previsão de 60 dias** a partir do
  último dia com venda; o dashboard mostra os 14 dias a partir de hoje, sem recalcular a
  cada dia. Às 03h00 o sistema MUST conferir o calendário e gerar a previsão de novo só se
  ele mudou depois da última geração. Tudo sem intervenção do usuário.
- **FR-006**: O sistema MUST produzir, por produto e por dia, uma **quantidade sugerida de
  reposição** que considere a validade do produto (`shelf_life_dias`), um estoque de
  segurança e o estoque atual (quando informado; 0 por padrão), além de cadência sugerida
  e risco de perda/ruptura.
- **FR-007**: O sistema MUST emitir alertas quando a previsão dos próximos 7 dias exceder
  em 20% ou mais a média das últimas 4 semanas do produto, e MUST sinalizar produtos de
  validade curta com risco de sobra.
- **FR-008**: O sistema MUST identificar e destacar fins de semana, feriados e a proximidade
  de datas comemorativas (Dia das Mães, Namorados, Finados, Natal) nas visualizações.
- **FR-009**: O sistema MUST permitir simulação do impacto de desconto sobre a previsão
  diária e a reposição de um produto, com comparação entre cenário base e simulado.
- **FR-010**: O sistema MUST exportar relatório em PDF e Excel contendo reposição, previsão
  diária e alertas.
- **FR-011**: O sistema MUST exibir indicadores de qualidade do modelo em linguagem
  acessível (ex.: "Precisão estimada: 92%"), não em jargão técnico.
- **FR-012**: O sistema MUST registrar log de cada upload, cada reajuste semanal (inclusive
  os pulados) e cada geração da previsão, consultável no dashboard.
- **FR-013**: O sistema MUST sinalizar categorias com histórico insuficiente (< 180 dias)
  sem exibir previsão, e SKUs de baixo giro com aviso de "estimativa aproximada".
- **FR-014** *(fora do MVP — fase 2)*: O sistema SHOULD identificar produtos comprados
  juntos na mesma transação (REQ-07, *market basket*), via `GET /api/v1/products/{id}/bundles`.

### Key Entities

- **Produto (SKU)**: `produto_cod` + `produto_nome`; pertence a uma **Categoria** e a uma
  **Unidade**; tem histórico de vendas diárias e uma previsão desagregada.
- **Categoria × Unidade**: unidade de modelagem da camada L1; tem série diária agregada,
  `shelf_life_dias`, um modelo SARIMAX treinado e status (`trained`,
  `insufficient_data`).
- **Transação**: registro individual de venda com data, quantidade, valor, unidade operacional.
- **Modelo**: artefato SARIMAX treinado para uma `Categoria × Unidade`; ordem, métricas
  (MASE, RMSSE, cobertura do IC), data de treino, status.
- **Previsão**: demanda diária estimada para um SKU num dia futuro; valor central + IC 95%.
- **Reposição**: recomendação por SKU/dia — quantidade a repor, cobertura até data,
  cadência, risco de perda e de ruptura.
- **Alerta**: sinal de variação significativa ou risco de sobra; severidade, produto,
  janela e justificativa em linguagem natural.
- **Relatório**: exportação consolidada em PDF ou Excel.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: A gestora faz upload de uma planilha e vê a confirmação em menos de 30
  segundos para arquivos de até 50 MB.
- **SC-002**: O modelo L1 de cada `unidade × categoria` de maior volume atinge **MASE < 1.0**
  em walk-forward CV (≥ 4 folds, horizonte 14 dias) — bate a previsão ingênua sazonal semanal.
- **SC-003**: A **simulação de reposição** sobre o hold-out reduz a soma de perda (murcha) +
  ruptura em relação à regra ingênua "repor a média dos últimos 7 dias" para os top 10 produtos.
- **SC-004**: O reajuste semanal automático conclui em menos de 2 horas; a geração da
  previsão conclui em menos de 15 minutos.
- **SC-005**: A gestora acessa a lista de reposição do dia e exporta o relatório PDF em
  menos de 3 cliques a partir da tela inicial.
- **SC-006**: 100% dos alertas e recomendações têm justificativa em português sem termos técnicos.
- **SC-007**: O dashboard permanece disponível durante o reajuste semanal (roda em background).
- **SC-008**: Usuário `viewer` não consegue realizar upload ou retrain — tentativas via API
  ou UI retornam mensagem de permissão negada.
- **SC-009**: Nenhum dado pessoal de clientes é retornado pela API em nenhum cenário.
- **SC-010**: A cobertura empírica do intervalo de 95% das previsões diárias fica entre 90% e 98%.

---

## Assumptions

- Os usuários finais acessam o sistema via navegador web moderno (Chrome, Edge, Firefox).
- Os arquivos XLSX são exportados do mesmo sistema financeiro que gerou a base histórica —
  estrutura de colunas consistente entre arquivos.
- A empresa repõe produtos perecíveis com frequência de poucos dias; a decisão relevante é
  "quanto comprar hoje", não "quanto no mês".
- A empresa **não** possui sistema de estoque em tempo real; o estoque atual é opcional
  (0 por padrão) e a recomendação é de compra "a seco".
- A validade por categoria (`shelf_life_dias`) será confirmada com a entidade parceira;
  até lá usa-se uma tabela de parâmetros com valores default por categoria.
- Cada produto tem uma categoria; produtos sem categoria caem em "Outros".
- Autenticação e controle de acesso por perfil (JWT, `admin`/`viewer`) fazem parte do P1.
- Mobile responsiveness é desejável mas não bloqueante para a entrega inicial.
- O número de produtos com reposição detalhada estará na faixa de 15 a 30 (top N por volume);
  a previsão de categoria cobre todo o catálogo agrupado.
