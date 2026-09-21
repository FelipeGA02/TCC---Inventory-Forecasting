# ADR-009: Granularidade Diária e Política de Reposição para Produtos Perecíveis

**Status**: Parcialmente revisado por [ADR-011](ADR-011-escopo-previsao-sem-reposicao.md)
(2026-08-30, 2026-09-21) — a **granularidade diária** e as camadas **L1/L2** seguem
valendo; a **camada L3 (política de reposição)** e o `shelf_life_dias` **saíram de
escopo**; o grão do L1 passou de `unidade × categoria` (6 séries) para **`unidade`**
(2 séries), com `categoria` obtida por desagregação (ver seção "Revisão — 2026-09-21" ao
final e ADR-011 §4). As seções sobre L3 abaixo ficam como registro histórico; a tabela da
seção 2 e as seções 6 e 8 já refletem a granularidade atual.
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo
**Substitui**: decisão de "granularidade mensal para produção" registrada em
`SPECS.md` §2.2, `plan.md` (Phase 0), ADR-001 e ADR-004 (todos revisados nesta data)

---

## Contexto

A primeira versão do sistema (spec aprovada em 2026-07-28) definiu **previsão mensal**
por produto, com horizonte de 1–3 meses, justificada por dois argumentos:

1. o ciclo de reposição da floricultura seria "semanal/mensal";
2. a série **diária por SKU** tem >90% de zeros, o que inviabiliza SARIMAX por SKU.

A revisão de requisitos com a entidade parceira mostrou que a premissa (1) está errada
para o negócio real: **flores de corte e folhagens são altamente perecíveis — parte do
mix dura de 3 a 7 dias na loja**. Uma previsão mensal agrega para dentro do total do mês
justamente a informação que decide a compra: *quanto precisa chegar em cada dia*, e *com
que frequência repor* para não faltar nem perder por murcha. O entregável correto é uma
**recomendação de reposição diária por produto**, não um volume mensal.

O argumento (2) continua **verdadeiro** e é tratado pela arquitetura hierárquica abaixo:
o SKU nunca é modelado sozinho.

## Decisão

### 1. Entregável

Para cada produto do Top-N e para os próximos **14 dias**, o sistema entrega:

- demanda diária prevista (valor central + intervalo de 95%);
- **quantidade sugerida de reposição** por dia, considerando validade (shelf-life),
  estoque de segurança e — quando informado — estoque atual;
- **cadência sugerida** de reposição ("repor a cada N dias") e data-limite de cobertura;
- **risco de perda** (excesso sobre o que vende dentro da validade) e **risco de ruptura**.

### 2. Arquitetura de modelagem — hierárquica em 3 camadas

| Camada | Escopo | Técnica | Papel |
| --- | --- | --- | --- |
| **L1 — Demanda agregada** | uma série **diária por `unidade`** (2 séries: Jardim Canadá, Itabirito — densa, sem excesso de zeros) | **SARIMAX** sazonal semanal (`m=7`, `D=0`), exógenas de calendário | captura tendência, dia-da-semana, feriados e datas comemorativas |
| **L2 — Desagregação para categoria e SKU** | dois passos em cascata: `unidade → categoria` (3 categorias), depois `categoria → SKU` do Top-N | participação móvel (share das últimas 4–8 semanas) × perfil de dia-da-semana **do nível** (categoria ou SKU), com suavização | converte a previsão da unidade em previsão por categoria, e a de categoria em previsão por SKU, **sem** ajustar um modelo próprio em nenhum dos dois níveis |
| **L3 — Política de reposição** *(histórico — fora de escopo, ADR-011)* | cada SKU do Top-N | fórmula determinística sobre a demanda prevista + `shelf_life_dias` + estoque de segurança | transforma previsão em decisão de compra perecível-consciente |

**Fórmula L3** (por SKU, dia `t`):

```
cobertura_alvo   = min(shelf_life_dias, HORIZONTE_REPOSICAO_DIAS)
demanda_cobertura = Σ demanda_prevista[t .. t + cobertura_alvo - 1]
qtd_repor(t)     = max(0, demanda_cobertura + estoque_seguranca - estoque_atual(t))
perda_esperada(t) = max(0, estoque_atual(t) + qtd_repor(t) - Σ demanda_prevista[t .. t + shelf_life_dias - 1])
```

`estoque_atual` é opcional: a floricultura não tem estoque em tempo real, então o padrão
é `estoque_atual = 0` (recomendação de compra "a seco") e o campo fica disponível para
quando houver contagem manual.

### 3. SARIMAX continua central — Croston/TSB entram como trilha de comparação

- **L1 é SARIMAX** — o Princípio II da constituição (estatística antes de ML) permanece
  satisfeito no núcleo do sistema.
- Modelos de **demanda intermitente** (Croston, TSB, SBA) passam a ser **permitidos**
  especificamente para o nível de SKU, onde SARIMAX é matematicamente inaplicável
  (série quase toda zero). Eles formam a **trilha de comparação** que substitui a antiga
  comparação "mensal × diária": agora é **SARIMAX hierárquico × demanda intermitente por
  SKU**, ambos em granularidade diária (contribuição acadêmica (ii) — ver `SPECS.md` §12.5).
  Não é só uma escolha de conveniência: aplicando o critério de classificação de demanda de
  Syntetos, Boylan & Croston (2005) aos SKUs da base, 99,3% caem nos padrões
  (intermitente/lumpy) em que a literatura recomenda Croston/TSB/SBA sobre um modelo de
  série temporal contínua — ver a aplicação completa e as referências em
  `01-pre_processing.md` §5.2 e `00-eda_report.md` §2.5b.
- Redes neurais / gradient boosting continuam exigindo evidência empírica de
  superioridade antes de entrar (Princípio II inalterado nesse ponto).

### 4. Sazonalidade

| Efeito | Como entra |
| --- | --- |
| Dia-da-semana (fim de semana vende mais) | termo sazonal SARIMAX `m=7` **+** dummies de dia-da-semana / termos de Fourier como exógenas em L1; perfil de dia-da-semana por SKU em L2 |
| Feriados e vésperas | exógenas binárias em L1 (feriado nacional/municipal, véspera) |
| Datas comemorativas (Dia das Mães, Namorados, Finados) | exógena "dias até a data" em L1, substitui o `alta_temporada` binário mensal |
| Sazonalidade anual | com ~26 meses de histórico não há ciclos anuais suficientes para termo sazonal `m=365`; capturada de forma aproximada por exógena de mês/estação |

### 5. Validação (substitui os limiares mensais)

| Item | Antes (mensal) | Agora (diário) |
| --- | --- | --- |
| Métrica primária | MAPE < 20% / SMAPE < 30% | **MASE < 1.0** (bate a naïve sazonal semanal) em L1 e no SKU |
| Métrica de escala | — | **RMSSE** (usada na M5 para varejo intermitente) |
| Erro operacional | — | **erro agregado na janela de cobertura** (soma de `shelf_life_dias`), não ponto a ponto |
| Simulação de negócio | — | **perda (murcha) + ruptura simuladas** em hold-out, contra uma regra ingênua ("repor a média dos últimos 7 dias") |
| Cobertura do IC 95% | — | cobertura empírica do intervalo ∈ [90%, 98%] |
| Walk-forward CV | ≥ 4 folds, horizonte 1 mês | ≥ 4 folds, **origem móvel, horizonte 14 dias** |
| Diagnóstico de resíduos | Ljung-Box + Shapiro-Wilk (L1) | inalterado — só L1, apenas log, não bloqueia deploy |
| MAPE/SMAPE | limiar | ainda calculados e reportados, mas **informativos** (instáveis com contagem baixa) |

`low_confidence` = MASE ≥ 1.0 **ou** cobertura do IC fora da faixa **ou** simulação pior
que a regra ingênua. Não bloqueia a previsão; exibe aviso no dashboard.

### 6. Observações mínimas

| Camada | Mínimo | Se não atingir |
| --- | --- | --- |
| L1 (`unidade`, diário) | **180 dias** (~6 meses) de histórico | `insufficient_data` — unidade inteira sem previsão |
| L2, passo `categoria` | mesmo mínimo aplicado ao par `unidade × categoria`; hoje os 6 pares já atendem | categoria cai no fallback (rateio uniforme entre categorias da unidade) |
| L2, passo SKU | 28 dias com ≥ 1 venda **ou** ≥ 8 vendas no total | SKU cai no fallback (média móvel da categoria rateada) |

### 7. Retreino e geração

- **Ajuste dos modelos L1**: mantém-se **semanal** (segunda-feira 02:00, APScheduler).
- **Geração da previsão + reposição**: **diária**, todo dia às 03:00, a partir dos
  modelos L1 em cache (não re-ajusta — só estende o horizonte e roda L2/L3).
- `forecasts_cache` passa a ser regenerado diariamente; `retrain_history` continua
  registrando só os ajustes semanais.

### 8. Dependências de dado novas — taxonomia e `shelf_life_dias`

A camada L1 agrupa por `unidade`; a desagregação L2 usa `categoria` como passo
intermediário. A base transacional **não tem nenhuma das duas colunas**, nem a validade
dos produtos. Dependências resolvidas por uma nova Etapa 3 de pré-processamento
(`map_taxonomy.py` — ver [01-pre_processing.md](01-pre_processing.md) §5) com tabelas
de/para versionadas:

**`unidade`** *(fechado por [ADR-011](ADR-011-escopo-previsao-sem-reposicao.md))* —
derivada de `empresa` (3 valores: `FLORICULTURA VERDE PERTO CANADÁ LTDA`,
`GARDEN CENTER VERDE PERTO LTDA`, `VERDE PERTO JARDINAGEM LTDA`). As 3 LTDAs formam **2
unidades operacionais**: as vendas do Garden Center pertencem a Jardim Canadá. É a
**chave da série L1**.

**`categoria`** *(revisado por [ADR-011](ADR-011-escopo-previsao-sem-reposicao.md) §3 e §4)* —
**3 categorias de demanda** (`Grama`, `Flores de corte`, `Produtos de jardim`) + o rótulo
`Servico e taxa` (não-produto). São derivadas colapsando uma `categoria_fina` (~10
rótulos, produzida por regras sobre `produto_nome`); a fina fica no CSV para a EDA e a L2.
Desde 2026-09-21, `categoria` **não é mais chave de uma série L1 própria** — é o primeiro
passo da desagregação L2 (`unidade → categoria`), pelo mesmo motivo por que a `categoria_fina`
já era só um nível de desagregação: o teste de separação (ADR-011 §4) não mostrou ganho de
acurácia em modelá-la direto. Ver [01-pre_processing.md](01-pre_processing.md) §5.

**`shelf_life_dias`** — *removido do escopo* por [ADR-011](ADR-011-escopo-previsao-sem-reposicao.md):
sem a camada L3, não há uso para a validade por categoria. As subseções abaixo sobre
cobertura-alvo, estoque de segurança e simulação de perda/ruptura ficam como registro
histórico.

> **A confirmar com a entidade parceira** (Sprint 0, `tasks.md` T000d): mapa
> `produto → categoria` (ao menos do Top-N). O mapa `empresa → unidade` está fechado
> (ADR-011).

## Consequências

- **Constituição** emendada para v2.0.0 (Princípios II e III — escopo e limiares).
- **`SPECS.md`**: §1.1, §2.2, §2.3, §4 (features diárias), §5 (pipeline L1/L2/L3), §6
  (config), §7 (endpoints `/forecast` diário + novo `/replenishment`), §8 (schemas
  `DailyPoint`, `ReplenishmentRecommendation`), §9 (tabelas), §10 (geração diária),
  §12.5 (nova comparação) — todos revisados.
- **`openapi.yaml`**: `MonthlyPoint` → `DailyPoint`; `horizon_months` → `horizon_days`;
  novos endpoints `/api/v1/replenishment/{produto_cod}` e `/batch`; métricas com MASE/RMSSE.
- **`spec.md`**: User Stories reescritas para reposição diária; FR-003, FR-006, FR-007,
  SC-002/003/004 revisados.
- **`tasks.md`**: Fase 3 (modelagem) reescrita para L1/L2/L3; nova fase de política de
  reposição; T044a vira "SARIMAX hierárquico × demanda intermitente".
- **`training_scripts/`**: `baseline/` passa a treinar L1 diário por `unidade×categoria`;
  novo `replenishment/`; `alternative_models/` inclui Croston/TSB/SBA.
- **Pré-processamento** (`docs/prediction/01-pre_processing.md` — reescrito): a série
  alvo passa a ser diária agregada por `unidade × categoria`; `pagamento`/`vendedor` saem
  na Etapa 2 (ADR-010); nova **Etapa 3 `map_taxonomy.py`** deriva `unidade` e `categoria`
  de tabelas de/para versionadas (`taxonomy/`); a antiga Etapa 3 de one-hot
  (`discretize_fields.py`) foi removida (histórico do git).
- **ADR-001** e **ADR-004**: recebem seção "Revisão 2026-08-30" apontando para este ADR.
- **Contribuição acadêmica (ii)**: deixa de ser "mensal é melhor que diário" e passa a
  ser "qual arquitetura diária (SARIMAX hierárquico vs. demanda intermitente) serve
  melhor um catálogo perecível de cauda longa".

---

## Revisão — 2026-09-21 (L1: `unidade × categoria` → `unidade`)

O teste de separação (`training_scripts/eda/eda_separacao.py`, ver
[ADR-011 §4](ADR-011-escopo-previsao-sem-reposicao.md)) mostrou que separar a série L1 por
**categoria** não reduz o erro de previsão — nenhuma das 6 séries `unidade × categoria`
ganha o mínimo de 5% de MASE ao ser modelada direto em vez de obtida por repartição da
unidade, com os dois previsores testados (SARIMAX e Holt-Winters). Separar por **unidade**
tem apoio: Itabirito ganha 17%/11% de MASE com modelo próprio, e a soma dos dois modelos
de unidade melhora o total da rede em 22% (SARIMAX) — as duas unidades têm tendências
opostas (§3.5 do relatório de EDA) que um único modelo do total não capturaria.

Impacto nesta decisão:

- **L1 passa a ser 2 séries** (uma por unidade), não 6. A tabela da seção 2 e as seções 6
  e 8 acima já refletem essa granularidade.
- **`categoria` vira nível de desagregação**, como o SKU já era de `categoria`: a L2 ganha
  um passo em cascata a mais (`unidade → categoria → SKU`), pelo mesmo método
  (participação móvel × perfil de dia-da-semana do nível).
- A análise por `unidade × categoria` que já existia (`eda_series.py`,
  `00-eda_report.md` §3) não perde valor — ela é o insumo do novo passo de desagregação
  `unidade → categoria` (perfil de dia-da-semana e efeito de datas comemorativas *da
  categoria*). Uma nova análise (`eda_series_unidade.py`, mesmo relatório §3.0) cobre a
  mesma bateria de diagnóstico para as 2 séries que o SARIMAX do L1 agora ajusta de fato.
- **Constituição** emendada para v3.0.0 (Princípio II e Quality Gates — grão do L1).
- Detalhes completos, tabelas de MASE por parte e o racional de por que a desagregação por
  categoria precisa do efeito de data *da própria categoria* (não só da proporção
  histórica) estão em [ADR-011 §4](ADR-011-escopo-previsao-sem-reposicao.md).
