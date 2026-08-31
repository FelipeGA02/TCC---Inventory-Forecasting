# ADR-009: Granularidade Diária e Política de Reposição para Produtos Perecíveis

**Status**: Aceito (revisão de escopo — 2026-08-30)
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
| **L1 — Demanda agregada** | uma série **diária por `unidade × categoria`** (densa, sem excesso de zeros) | **SARIMAX** sazonal semanal (`m=7`, `D=0`), exógenas de calendário | captura tendência, dia-da-semana, feriados e datas comemorativas |
| **L2 — Desagregação para SKU** | cada SKU do Top-N dentro da sua categoria/unidade | participação móvel (share das últimas 4–8 semanas) × perfil de dia-da-semana do SKU, com suavização | converte a previsão da categoria em previsão por SKU **sem** ajustar um modelo por SKU |
| **L3 — Política de reposição** | cada SKU do Top-N | fórmula determinística sobre a demanda prevista + `shelf_life_dias` + estoque de segurança | transforma previsão em decisão de compra perecível-consciente |

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
| L1 (`unidade × categoria`, diário) | **180 dias** (~6 meses) de histórico | `insufficient_data` — categoria inteira sem previsão |
| L2 (SKU) | 28 dias com ≥ 1 venda **ou** ≥ 8 vendas no total | SKU cai no fallback (média móvel da categoria rateada) |

### 7. Retreino e geração

- **Ajuste dos modelos L1**: mantém-se **semanal** (segunda-feira 02:00, APScheduler).
- **Geração da previsão + reposição**: **diária**, todo dia às 03:00, a partir dos
  modelos L1 em cache (não re-ajusta — só estende o horizonte e roda L2/L3).
- `forecasts_cache` passa a ser regenerado diariamente; `retrain_history` continua
  registrando só os ajustes semanais.

### 8. Dependências de dado novas — taxonomia e `shelf_life_dias`

A camada L1 agrupa por `unidade × categoria`; a base transacional **não tem nenhuma das
duas colunas**, nem a validade dos produtos. Três dependências, resolvidas por uma nova
Etapa 3 de pré-processamento (`map_taxonomy.py` — ver
[01-pre_processing.md](01-pre_processing.md) §5) com tabelas de/para versionadas:

**`unidade`** — derivada de `empresa` (3 valores: `FLORICULTURA VERDE PERTO CANADÁ LTDA`,
`GARDEN CENTER VERDE PERTO LTDA`, `VERDE PERTO JARDINAGEM LTDA`). *A confirmar com a
parceira*: essas 3 LTDAs correspondem 1:1 às 3 unidades operacionais? Alguns nomes de
vendedor trazem `(ITABIRITO)`/`(CANADÁ)` — se `empresa` não separar as lojas, a unidade
precisa vir de outro campo.

**`categoria`** — derivada em cascata: de/para explícito do Top-N (curadoria) → regras
por palavra-chave em `produto_nome` → fallback `"Outros"`. A EDA valida o % de volume que
cai em `"Outros"` (alvo: baixo).

**`shelf_life_dias`** — validade por categoria. Enquanto não houver dado da parceira,
tabela de parâmetros default (por categoria, versionada em configuração / banco):

| Categoria (exemplo) | `shelf_life_dias` padrão |
| --- | --- |
| Flor de corte | 4 |
| Folhagem de corte | 7 |
| Arranjo / buquê montado | 3 |
| Planta em vaso | 30 |
| Insumo (vaso, terra, acessório) | 180 |

> **A confirmar com a entidade parceira** (Sprint 0, `tasks.md` T000c/T000d): mapa
> `empresa → unidade`, mapa `produto → categoria` (ao menos do Top-N), e a validade real
> por categoria / SKU.

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
