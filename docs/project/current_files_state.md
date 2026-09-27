# Estado Atual — Dados, Pré-processamento e Requisitos

**Levantado em**: 2026-08-23, por inspeção do código, histórico do git e arquivos em
disco (não é um relatório de execução — é um raio-x do que existe hoje).

> **Atualização 2026-08-30 — revisão de escopo mensal → diário.** O entregável do
> sistema mudou de *previsão mensal por produto* para *recomendação de reposição diária*
> (produtos perecíveis), com arquitetura hierárquica L1 (SARIMAX diário por
> `unidade × categoria`) → L2 (desagregação para SKU) → L3 (política de reposição). Ver
> [`docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md`](../prediction/ADR-009-granularidade-diaria-e-reposicao.md)
> e a constituição v2.0.0. Este raio-x continua válido quanto ao **estado do código**
> (backend/domain ainda são stubs, frontend ainda é mockup); onde ele fala em
> "granularidade mensal", "MAPE/SMAPE" ou "comparação mensal×diária", leia à luz do
> ADR-009 (agora: diária, MASE, e comparação SARIMAX hierárquico × demanda intermitente).
>
> **Atualização 2026-09-21 — granularidade do L1: `unidade`, não `unidade × categoria`.**
> O teste de separação (`eda_separacao.py`) mostrou que separar a série L1 por categoria
> não reduz o erro de previsão; o L1 passa a ser **2 séries** (uma por unidade), e
> `categoria` vira nível de desagregação (cascata `unidade → categoria → SKU`), como o SKU
> já era de categoria. Ver [ADR-011 §4](../prediction/ADR-011-escopo-previsao-sem-reposicao.md)
> e a constituição v3.0.0. Onde este raio-x fala em "L1 por unidade × categoria", leia
> "L1 por unidade; categoria por desagregação".
>
> **Atualização 2026-09-27: primeiro treino reproduzível (ponto zero).** O EDA está
> concluído ([00-eda_report.md](../prediction/00-eda_report.md)). Foi treinado e salvo o
> baseline **A0-crua**: SARIMA puro sobre 1 série diária total, com a base pré-EDA de
> 2026-08-30, em `training_scripts/baseline/sarimax_serie_crua.py`. Métricas, previsões e
> gráficos estão em `training_scripts/results/`. Ganho de ~17–18% sobre a naïve na mesma
> janela, dezembro/2025 previsto em 34%. Diagnóstico completo em
> [02-baseline_serie_crua_pre_eda.md](../prediction/02-baseline_serie_crua_pre_eda.md).
> Na mesma série, o enriquecimento com calendário (BrasilAPI) e clima (Open-Meteo) está em
> [03-enriquecimento_serie_crua.md](../prediction/03-enriquecimento_serie_crua.md): o calendário
> ajuda, o clima não. Dados externos ficam em cache em `ia-predictor/data/external/`.
>
> **Atualização 2026-09-27 — pré-processamento v2.** O pipeline de
> `training_scripts/preprocessing/` ganhou as Etapas 4–7 (base limpa, encomendas, calendário
> por loja, séries diárias prontas) e um `run_all.py` com relatório de qualidade; 10 testes
> unitários em `tests/unit/test_preprocessing_etapas.py`. Ver
> [01-pre_processing.md](../prediction/01-pre_processing.md) §6–§11.

---

## 1. Resumo executivo

- Os **dados brutos existem e estão completos**: 26 planilhas XLSX mensais
  (jan/2024–fev/2026) em `ia-predictor/data/raw/`.
- Existe um **CSV consolidado** (`ia-predictor/data/processed/contas_a_receber.csv`,
  343.116 registros) — mas ele foi gerado por um **pipeline legado que já foi
  deletado do repositório**, não pelo backend atual.
- Existe **evidência de que o SARIMAX funciona neste dataset** (métricas por produto,
  walk-forward CV, testes de resíduos) — mas esse código também foi deletado ao
  pivotar para a arquitetura limpa (`ia-predictor/backend/`).
- O **backend de produção atual não processa dado nenhum ainda**: todo o ETL,
  engenharia de atributos e modelagem em `backend/domain/` e `backend/services/` são
  arquivos vazios (stubs de 0 linhas). Só autenticação e o schema do banco estão
  implementados de verdade.
- O **frontend é um mockup visual** (telas geradas via Figma) com dado hard-coded
  (`data/mockData`), sem nenhuma chamada real à API.
- **Nenhum dos requisitos funcionais do artigo (REQ01–REQ12) está cumprido de ponta a
  ponta no sistema atual.** O que existe é a *prova de conceito* de que a abordagem
  funciona, feita fora da arquitetura de produção.

---

## 2. Linha do tempo real (via `git log`)

| Commit | O que fez |
| --- | --- |
| `f424770` Initial commit / `db1ddd6` project structure | Estrutura inicial |
| `7756055` feat: preprocess raw data | Parser de XLSX (`src/data/parser.py`) |
| `9301911` feat: Preprocess monthly | Consolidação mensal em CSV único com dedup |
| `a2b83df` feat: drop and discretizing columns | Remoção/discretização de colunas |
| `ba5f3eb` feat: remoção de mais 3 campos | Ajuste do schema tabular |
| `a162308` feat: SARIMAX | Pipeline completo de modelagem + avaliação (protótipo) |
| `ac4dd9e` feat: Specs para o backend | **Deleta todo o `src/`** e cria `ia-predictor/backend/` do zero (Clean Architecture), `SPECS.md`, constituição, spec-kit |
| `208674e` → `cd87ae1` | `.gitignore`, preprocessing (auth + DB), docs, frontend scaffold |

A pasta `src/` (protótipo) foi **intencionalmente descartada** ao decidir reconstruir
como monolito modular em `ia-predictor/backend/` — isso está registrado na memória do
projeto ("Implementação do zero — notebooks descartados") e no próprio `.gitignore`:

```
# ─── Jupyter (notebooks antigos — não fazem parte do novo sistema) ────────────
.ipynb_checkpoints/
*.ipynb
```

Um notebook (`notebooks/01_EDA-feature-engineering.ipynb`) ainda existe em disco, mas
é ignorado pelo git e importa módulos de `src/` que não existem mais — **não roda mais
no estado atual do repositório**.

---

## 3. O que o pipeline legado (deletado) fazia — recuperado do histórico do git

Não está no working tree, mas está no histórico (`git show ac4dd9e~1:src/...`), então
é reaproveitável se decidirmos portar essa lógica para `backend/domain/`.

### 3.1 Ingestão (`src/data/parser.py` + `preprocess_raw_data_by_month.py`)

- Parser estrutural do XLSX de contas a receber: cada "Documento:" é um bloco com
  cabeçalho (cliente, empresa, vendedor, data, forma de pagamento) seguido de N linhas
  de produto até a linha "Totais".
- Deduplicação por chave composta `(doc_numero, produto_cod)`, comparando com as chaves
  já presentes no CSV de saída.
- Controle de reprocessamento por **hash MD5** do arquivo — só processa planilhas novas
  ou alteradas (`processamento_log.json`).
- **Não fazia** as validações que `tasks.md`/`SPECS.md` preveem para o normalizer novo
  (remover `qtdade <= 0`, remover `emissao` nula, converter vírgula decimal) — o
  parser legado só extrai e formata, sem regra de negócio de limpeza.

### 3.2 Redução de schema (`src/data/drop_columns.py`, `discretize_fields.py`)

- Removia colunas sem uso analítico: `operador, obs, icms_ret, arquivo_origem,
  cliente_nome, produto_nome, doc_tipo` → `contas_a_receber_sem_colunas.csv`.
- Discretizava `pagamento`, `empresa`, `vendedor` em códigos inteiros, salvando o
  de/para em `src/utils/encodings.py` → `contas_a_receber_discretizado.csv`.
- **Esses dois arquivos de saída não existem hoje em `data/processed/`** — ou seja,
  mesmo se o código ainda existisse, essa etapa não foi reexecutada sobre os dados
  atuais.

### 3.3 Modelagem (`src/models/sarimax_model.py` + `evaluation.py`)

Pipeline funcional e testado, correspondente quase 1:1 ao que `SPECS.md` §5 descreve
hoje como especificação (ou seja, o protótipo *foi* a base da especificação):

- `prepare_monthly_data` / `build_exogenous_features`: série mensal + 15 variáveis
  exógenas (mercado, produto, calendário) — igual à tabela de `SPECS.md` §5.2.
- `compute_feature_importance` + `weight_features`: ponderação via Random Forest (MDI).
- `select_sarimax_order`: grid search por AIC.
- `walk_forward_cv` (janela expansiva, 5 folds por padrão) e
  `evaluate_monthly_horizons` (degradação do erro em 1–4 meses à frente).
- `residual_tests`: Ljung-Box, Shapiro-Wilk **e** Jarque-Bera.
- Gráficos de IC 95%, relatórios consolidados em `results/metrics/*.csv` — **essa
  pasta `results/` não existe mais em disco**, os artefatos não foram preservados.

**Métricas obtidas no protótipo** (registradas em memória de sessões anteriores, não
verificadas novamente nesta sessão):

| Produto | SMAPE | R² | Observação |
| --- | --- | --- | --- |
| 147 | 22,5% | 0,73 | Bom ajuste |
| 3 | 12,2% | 0,08 | Erro baixo, mas pouca variância explicada |
| 167, 143 | > 120% | — | CV > 1 (demanda "lumpy"), SARIMAX inadequado |

Isso **prova a viabilidade da abordagem SARIMAX no dataset real** — que é o objetivo
geral do artigo — mas é uma prova de conceito descartada, não o sistema entregável.

---

## 4. Estado atual dos dados em disco

| Caminho | Estado |
| --- | --- |
| `ia-predictor/data/raw/*.xlsx` | 26 planilhas mensais completas (jan/24–fev/26) + 1 fixture de teste |
| `ia-predictor/data/processed/contas_a_receber.csv` | 343.116 linhas, 20 colunas, `sep=';'`. Gerado pelo parser legado (código já não existe) |
| `ia-predictor/data/processed/processamento_log.json` | Só tem **1 entrada**, referente a um upload de teste (`sample.xlsx`, 5 linhas) — **não há registro de como/quando os 26 arquivos reais viraram o CSV de 343k linhas**. Gap de rastreabilidade (Princípio V da constituição) |
| `contas_a_receber_sem_colunas.csv` / `..._discretizado.csv` | Não existem — etapa de redução/discretização de schema não foi rodada sobre os dados atuais |
| `ia-predictor/models/*.joblib` | Não existem — nenhum modelo treinado e persistido ainda |
| `results/` (plots, métricas) | Não existe — artefatos do protótipo não foram preservados |

---

## 5. Estado atual do backend de produção (`ia-predictor/backend/`)

| Módulo | Linhas | Status |
| --- | --- | --- |
| `config.py`, `main.py`, `dependencies.py` | 45 / 58 / 5 | ✅ Implementado |
| `auth/` (password_handler, jwt_handler, dependencies, seed_users) | 30–80 | ✅ Implementado |
| `api/router_auth.py`, `api/router_health.py` | 89 / 10 | ✅ Implementado |
| `schemas/auth.py` | 44 | ✅ Implementado |
| `infrastructure/database.py` | 129 | ✅ Implementado — as 6 tabelas ORM completas (`users`, `products`, `model_artifacts`, `forecasts_cache`, `processing_log`, `retrain_history`) já existem, prontas para receber dados |
| `domain/etl/*` (parser, normalizer, deduplicator) | 0 | ❌ Stub vazio |
| `domain/features/*` (time_series, exogenous, importance) | 0 | ❌ Stub vazio |
| `domain/models/*` (stationarity, order_selection, trainer, evaluator, forecaster) | 0 | ❌ Stub vazio |
| `services/*` (upload, forecast, alert, simulation, report) | 0 | ❌ Stub vazio |
| `api/router_upload.py`, `router_products.py`, `router_forecast.py`, `router_alerts.py`, `router_simulation.py`, `router_reports.py`, `router_models.py` | 0 | ❌ Stub vazio |
| `schemas/alerts.py`, `forecast.py`, `products.py`, `reports.py`, `simulation.py` | 0 | ❌ Stub vazio |
| `infrastructure/scheduler.py`, `infrastructure/storage.py` | 0 | ❌ Stub vazio |

**Risco imediato**: `backend/main.py` já importa e registra todos esses routers vazios
(`app.include_router(router_upload.router, ...)` etc.). Como os arquivos estão vazios,
`router_upload.router` não existe — a aplicação **não sobe** (`ImportError`/
`AttributeError`) até que pelo menos um objeto `router` mínimo exista em cada um desses
arquivos. Vale confirmar isso rodando `uvicorn backend.main:app --reload`.

---

## 6. Estado atual do frontend (`app-react/`)

- Existe um **scaffold de UI completo** gerado via Figma (`components/screens/`):
  `Dashboard`, `PrevisaoSarimax`, `AlertasReposicao`, `SimuladorCenarios`,
  `ExportarRelatorios`, `ImportarPlanilha`, `PreVisualizacao`, mais toda a biblioteca de
  componentes shadcn/ui (`components/ui/*`, ~50 componentes).
- **Esse scaffold usa dado mockado** — ex. `Dashboard.tsx` importa
  `tendenciaProdutos, alertasUrgentes` de `../../data/mockData`, não de uma API.
- `AuthContext.tsx`, `LoginPage.tsx`, `PrivateRoute.tsx` (spec `tasks.md` T023–T026)
  estão **vazios** (0 bytes) — login não está funcional.
- `src/services/api/` só tem `.gitkeep` e um `httpClient.ts` — o cliente TypeScript
  gerado a partir de `openapi.yaml` (T061–T062) ainda não foi criado; `openapi.yaml`
  em si também não existe em `ia-predictor/`.

Ou seja: o frontend é hoje um **protótipo visual estático**, desconectado de qualquer
backend real.

---

## 7. Rastreamento de requisitos do artigo

### 7.1 Requisitos Funcionais (artigo, seção 7.1 / `SPECS.md` §13)

| Código | Requisito | Status | Evidência |
| --- | --- | --- | --- |
| REQ01 | Upload de planilhas sem conhecimento técnico | ❌ Não cumprido | `router_upload.py` e `upload_service.py` vazios; `ImportarPlanilha.tsx` é mockup |
| REQ02 | Previsão 2–3 semanas à frente | ⚠️ Provado em protótipo, não em produção | Lógica existiu em `src/models/sarimax_model.py` (deletado); nada em `backend/domain/models/` |
| REQ03 | Atualização automática semanal | ❌ Não cumprido | `infrastructure/scheduler.py` vazio |
| REQ04 | Indicadores de desempenho para não técnicos | ❌ Não cumprido | Sem endpoint `/models/status`, sem UI conectada |
| REQ05 | Gráficos de tendência de demanda | ❌ Não cumprido | `PrevisaoSarimax.tsx` existe mas usa mock |
| REQ06 | Destacar produtos por período especial | ⚠️ Provado em protótipo | `alta_temporada` existia no protótipo; não portado |
| REQ07 | Produtos comprados juntos | ❌ Não iniciado | Documentado como "fase 2" mesmo em `SPECS.md` |
| REQ08 | Simular promoções/vendas casadas | ❌ Não cumprido | `simulation_service.py` vazio; `SimuladorCenarios.tsx` é mockup |
| REQ09 | Alertas automáticos de reposição | ❌ Não cumprido | `alert_service.py` vazio; `AlertasReposicao.tsx` é mockup |
| REQ10 | Exportação PDF/Excel | ❌ Não cumprido | `report_service.py` vazio |
| REQ11 | Dashboard centralizado | ⚠️ UI existe, sem dado real | `Dashboard.tsx` renderiza, mas 100% mock |
| REQ12 | Documentação funcional e técnica | ⚠️ Parcial | `SPECS.md`, `CLAUDE.md`, ADRs, constituição existem; falta `docs/quickstart.md` e docs voltadas ao usuário final |

### 7.2 Requisitos Não Funcionais

| Código | Requisito | Status |
| --- | --- | --- |
| RNF-01 Usabilidade | ❌ Não avaliável — não há fluxo funcional ponta a ponta |
| RNF-02 Confiabilidade/rastreabilidade | ⚠️ Parcial — tabela `processing_log` existe no schema, mas o CSV atual não tem histórico rastreável de geração (seção 4) |
| RNF-03 Retrain < 2h | ❌ Não avaliável — não há retrain implementado |
| RNF-04 Segurança/LGPD | ✅ Parcial cumprido — JWT, bcrypt, perfis admin/viewer e `require_admin` já implementados na camada de auth |
| RNF-05 Manutenibilidade | ✅ Estrutura em camadas (`domain/services/api/infrastructure`) já criada e seguida, mesmo vazia |

### 7.3 Objetivos específicos (artigo §4.2) — progresso

| Objetivo | Status |
| --- | --- |
| Levantar/validar requisitos com stakeholders | ✅ Feito — `SPECS.md`, `spec.md`, reuniões documentadas |
| Pipeline automatizado de ingestão (dedup, normalização, discretização) | ⚠️ Existiu uma versão (protótipo, deletada); versão de produção não iniciada |
| EDA (sazonalidade, tendência, comportamento por unidade) | ✅ Feito: [`docs/prediction/00-eda_report.md`](../prediction/00-eda_report.md), com scripts em `training_scripts/eda/` |
| Engenharia de atributos (exógenas de mercado/produto/tempo) | ⚠️ Especificada e prototipada; não portada para `backend/domain/features/` |
| Ponderação de exógenas via RF (MDI) | ⚠️ Prototipada e funcional; não portada |
| Treino SARIMAX com seleção AIC + atualização semanal | ⚠️ Baseline diário A0-crua treinado e salvo (2026-09-27, [02-baseline](../prediction/02-baseline_serie_crua_pre_eda.md)); A0/A1 por unidade pendentes; atualização semanal nunca existiu |
| Avaliação com MAE/RMSE/MAPE/SMAPE/R² + walk-forward + comparação mensal×diária | ⚠️ Walk-forward e métricas provados (só granularidade mensal); comparação mensal×diária (contribuição acadêmica ii) nunca foi feita |
| Dashboard interativo | ⚠️ UI mockada, sem integração |
| Simulação de promoções/vendas casadas | ❌ Não iniciado |
| Documentação funcional e técnica | ⚠️ Parcial |

---

## 8. Lacunas e riscos a resolver antes de avançar

1. **`main.py` importa módulos vazios** — a API provavelmente não sobe hoje. Confirmar
   com `uvicorn backend.main:app --reload --app-dir ia-predictor`.
2. **Rastreabilidade do CSV consolidado quebrada** — `processamento_log.json` não
   reflete como as 343k linhas foram geradas; se o CSV atual for reaproveitado como
   base "oficial", vale gerar um log retroativo ou reprocessar do zero pelo pipeline
   novo (`domain/etl/`) para ter histórico limpo desde o início.
3. **Nenhuma validação de qualidade de dado foi aplicada ainda** (remoção de
   `qtdade <= 0`, `emissao` nula, etc.) — o CSV atual é só o parser estrutural, sem as
   regras de negócio da Fase 4/T028 do `tasks.md`.
4. **Notebook órfão** (`notebooks/01_EDA-feature-engineering.ipynb`) referencia módulos
   que não existem mais. Decisão: a experimentação não volta a viver em notebook — a
   pasta `ia-predictor/training_scripts/` (scripts Python, com subpastas `eda/`,
   `baseline/`, `enriched/`, `alternative_models/`, `validation/`, `results/`) é o novo
   destino para reaproveitar essa lógica na Fase 1 do
   [plano de experimentação](../prediction/plano_experimentos_modelagem.md); o `.ipynb`
   órfão deve ser removido para não confundir.
5. ~~**Resultados do protótipo (`results/`) não foram preservados**~~ *(2026-09-27: a
   partir do A0-crua, os treinos salvam métricas, previsões e gráficos em
   `training_scripts/results/`, versionados no git)* — as métricas por
   produto citadas na seção 3.3 vêm só da memória de sessões anteriores; recomendo
   reexecutar e salvar os artefatos assim que o pipeline for reconstruído, para ter
   evidência auditável em vez de "lembrança".

---

## 9. Como isso se conecta ao próximo passo

O [plano de experimentos de modelagem](../prediction/plano_experimentos_modelagem.md) (Fase 1 —
Baseline L1 sem enriquecimento) é o ponto onde essa lacuna começa a ser fechada: ele
assume construir `prepare_daily_series(df, unidade, categoria)` e as exógenas de
calendário, comparar as variantes em `training_scripts/`, e só então portar o vencedor
para `backend/domain/`. Parte da lógica do protótipo legado (seção 3) ainda é
reaproveitável via `git show ac4dd9e~1:src/...` (parser, dedup, RF/MDI), mas a série
alvo e a granularidade mudaram — ver [ADR-009](../prediction/ADR-009-granularidade-diaria-e-reposicao.md).
