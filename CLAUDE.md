# CLAUDE.md — Sistema de Previsão de Vendas · Floricultura

Guia para sessões de desenvolvimento com Claude Code.
Leia este arquivo antes de qualquer implementação.

---

## O que é este projeto

TCC de Ciência da Computação (Centro Universitário Dom Helder, 2026), em parceria com a
Floricultura Verde Perto (unidades em Nova Lima — Jardim Canadá — e Itabirito/MG).
Sistema de **previsão de demanda diária** para rede de floricultura com 2 unidades
operacionais, baseado em modelagem hierárquica (SARIMAX na venda total de cada
unidade + desagregação em cascata para categoria e SKU) e dashboard React. A loja decide
a compra; o sistema informa quanto deve vender (ADR-011).

**Domínio**: floricultura / garden center · grama e produtos de jardim ≈ 98% do volume,
flores de corte ≈ 2% · sazonalidade semanal de dia útil + datas comemorativas  
**Dados**: 324k+ transações · Jan/2024–Fev/2026 · 5.100+ SKUs · 2 unidades  
**Entregável**: previsão de demanda **por dia**, horizonte de **14 dias**, com intervalo de
confiança de 95%, por unidade (L1) e, por desagregação, por categoria e SKU (L2). A
recomendação de reposição (L3) saiu de escopo — ver
`docs/prediction/ADR-011-escopo-previsao-sem-reposicao.md`  
**Granularidade**: diária. Ver `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md`
(revisão de escopo de 2026-08-30 — antes era mensal; L3 e o grão `unidade × categoria`
revisados pelo ADR-011)  
**Metodologia**: ágil/iterativa para o software; CRISP-DM (compreensão do negócio →
compreensão dos dados → preparação → modelagem → avaliação → implantação) para o
pipeline de dados e modelagem preditiva

---

## Stack

| Camada | Tecnologia |
| --- | --- |
| Backend API | FastAPI 0.111 + Python 3.11 |
| Modelagem | statsmodels 0.14 (SARIMAX — camada agregada L1) + scikit-learn 1.4 (RF) + Croston/TSB/SBA (demanda intermitente por SKU — trilha de comparação) |
| Análise exploratória (EDA) | Jupyter Notebooks + matplotlib, seaborn, plotly (não entram no runtime de produção) |
| Auth | python-jose (JWT HS256) + passlib (bcrypt) |
| Banco | Postgres no Neon (compartilhado) e SQLite (local), via SQLAlchemy 2.0 + psycopg 3 — ADR-014 |
| Scheduler | APScheduler 3.10 (ajuste dos modelos 10 min após planilha com venda nova — outra planilha no intervalo adia — e segunda 02:00 como rede de segurança, ambos pulados sem venda nova · conferência do calendário 03:00, gera de novo a previsão só se ele mudou — ainda não ativa, depende dos modelos em joblib) |
| Serialização | joblib (modelos), openpyxl (XLSX), reportlab (PDF) |
| Frontend | React 18 + Recharts + MUI (em `app-react/`) — decisão pós-prototipagem; o projeto técnico original cogitava Streamlit/Dash |
| Cliente HTTP | gerado de `openapi.yaml` via openapi-typescript-codegen |

---

## Estrutura de Diretórios

```
TCC---Inventory-Forecasting/
├── CLAUDE.md                    ← este arquivo
├── SPECS.md                     ← referência técnica completa
├── ia-predictor/
│   ├── openapi.yaml             ← FONTE DA VERDADE dos contratos de API
│   ├── backend/                 ← aplicação Python (monolito modular)
│   │   ├── main.py              ← entrypoint FastAPI
│   │   ├── config.py            ← Settings (pydantic-settings + .env)
│   │   ├── auth/                ← JWT, bcrypt, dependencies, seed_users
│   │   ├── api/                 ← routers HTTP (um por recurso)
│   │   ├── schemas/             ← Pydantic (contratos request/response)
│   │   ├── services/            ← casos de uso (orquestração)
│   │   ├── domain/              ← lógica pura SEM I/O
│   │   │   ├── etl/             ← parser, normalizer, deduplicator
│   │   │   ├── features/        ← daily_series (unidade), calendar_exogenous, importance
│   │   │   ├── models/          ← L1: stationarity, order_selection, trainer, evaluator, forecaster
│   │   │   └── disaggregation/  ← L2: rateio em cascata unidade→categoria→SKU (share móvel × perfil dia-da-semana)
│   │   └── infrastructure/      ← DB, storage, scheduler
│   ├── data/
│   │   ├── raw/                 ← XLSX brutos (upload)
│   │   └── processed/
│   │       └── contas_a_receber.csv   ← base consolidada (sep=";")
│   ├── models/                  ← artefatos joblib por unidade (L1) + params de desagregação L2 (categoria/SKU)
│   ├── training_scripts/        ← experimentação pré-produção (fora do backend)
│   │   ├── preprocessing/       ← XLSX bruto → base limpa → encomendas → calendário por loja → séries diárias (L1 e desagregação); `run_all.py` roda as 7 etapas (docs/prediction/01-pre_processing.md)
│   │   ├── eda/                 ← análise exploratória (base transacional, séries do L1, granularidade das categorias, classificação de demanda)
│   │   ├── baseline/            ← L1: série crua (doc 02) e treino por loja `sarimax_l1_por_loja.py` (doc 04: A0, A1, A1 d=1, Holt-Winters)
│   │   ├── enriched/            ← L1 na série crua + calendário e clima (doc 03)
│   │   ├── alternative_models/  ← Croston/TSB/SBA por SKU, ETS, XGBoost, rede neural global
│   │   ├── disaggregation/      ← L2: desagregação em cascata unidade→categoria→SKU (a criar)
│   │   ├── validation/          ← walk-forward CV (origem móvel, h=14d), MASE/RMSSE, resíduos (compartilhado)
│   │   ├── output/               ← CSV/JSON gerados pelo preprocessing/ (gitignored)
│   │   └── results/             ← metrics/ e plots/ da experimentação (staging, não é o results/ de produção)
│   └── tests/
│       ├── unit/                ← testes de domínio isolado
│       ├── integration/         ← testes de API e pipeline
│       └── fixtures/            ← sample.xlsx, sample_data.csv
├── app-react/                   ← frontend React (existente)
│   └── src/
│       ├── services/api/        ← GERADO de openapi.yaml (não editar manualmente)
│       └── app/
│           ├── auth/            ← AuthContext, LoginPage, PrivateRoute
│           ├── pages/           ← Dashboard, ProductDetail, Alerts, Simulation
│           └── components/      ← ForecastChart (diário), AlertList, UploadPanel, ExportButton
├── specs/
│   └── 001-sistema-previsao-vendas/
│       ├── spec.md              ← especificação funcional (User Stories)
│       ├── plan.md              ← plano técnico e arquitetura
│       └── tasks.md             ← tarefas por fase com TDD
└── docs/                        ← documentação organizada por área (ver docs/README.md)
    ├── project/                 ← projeto técnico (PDF) e estado atual do sistema
    ├── prediction/              ← ADRs de modelagem + plano de experimentos comparativos
    ├── backend/                 ← ADRs de arquitetura de serviço/API
    ├── database/                ← ADRs de persistência
    ├── frontend/                ← ADRs do dashboard React
    └── uml/                     ← diagramas UML (caminho fixo, seção 6.4 do artigo)
```

---

## Regras Invioláveis (Constituição v3.1.0)

Consulte `.specify/memory/constitution.md` para o texto completo. Resumo:

1. **Domínio Puro**: `backend/domain/` NUNCA importa FastAPI, SQLAlchemy ou APScheduler.
2. **Estatística antes de ML**: SARIMAX é o modelo central da camada agregada L1
   (`unidade`, diário — 2 séries). `categoria` e SKU são obtidos por desagregação em
   cascata (participação móvel × perfil de dia-da-semana do nível), não por modelo
   próprio: o teste de separação (ADR-011 §4) não mostrou ganho de acurácia em modelar
   categoria direto. Croston/TSB/SBA são permitidos no nível de SKU (série quase toda
   zero, SARIMAX inaplicável). NN/boosting só com evidência empírica.
3. **Validação obrigatória**: walk-forward CV (≥4 folds, origem móvel, h=14 dias) +
   `MASE < 1.0` + cobertura do IC 95% em [90%, 98%], antes de `status = "trained"`.
   A simulação de perda/ruptura caiu junto com a L3 (ADR-011); a constituição ainda a
   exige (Princípio III e Quality Gates) e precisa de emenda via `/speckit-constitution`.
4. **Linguagem do usuário**: mensagens de erro e alertas em PT-BR sem jargão técnico.
5. **Rastreabilidade**: todo upload e retrain gravados em `processing_log` e `retrain_history`
   (treino pulado por falta de venda nova fica como `skipped`); toda geração da previsão
   registra data, período previsto e contagem de SKUs atendidos em `forecast_runs`.
6. **Segurança por padrão**: JWT obrigatório em todos os `/api/v1/*`; bcrypt para senhas; API não expõe dados pessoais de clientes.

---

## Comandos Essenciais

```bash
# Instalar dependências do backend
pip install -r ia-predictor/requirements.txt

# Criar usuários iniciais (roda uma vez ou via startup)
python ia-predictor/backend/auth/seed_users.py

# Iniciar o servidor de desenvolvimento
uvicorn backend.main:app --reload --app-dir ia-predictor

# Acessar documentação interativa
# http://localhost:8000/docs   (Swagger UI)
# http://localhost:8000/redoc  (ReDoc)

# Pré-processamento completo (Etapas 1–7 + relatório de qualidade), a partir de ia-predictor/
python -m training_scripts.preprocessing.run_all

# Carga inicial do banco de DATABASE_URL (SQLite ou Neon) a partir do pré-processamento,
# a partir de ia-predictor/ — só com o banco vazio; --recriar apaga tudo antes
python -m backend.scripts.carga_inicial

# Rodar testes unitários
pytest ia-predictor/tests/unit/ -v

# Rodar testes de integração
pytest ia-predictor/tests/integration/ -v

# Regenerar cliente TypeScript após mudar openapi.yaml
cd app-react && npm run generate:api

# Iniciar frontend React
cd app-react && npm run dev
```

---

## Variáveis de Ambiente (.env)

```
# Banco
DATABASE_URL=sqlite:///./floricultura.db   # local; Neon: postgresql://usuario:senha@ep-...neon.tech/neondb?sslmode=require

# Diretórios
DATA_DIR=data
MODELS_DIR=models

# Auth (OBRIGATÓRIO: sem valor padrão; a API não sobe com chave < 32 caracteres, senha < 8
# ou valor de exemplo — Settings.exigir_segredos)
JWT_SECRET_KEY=<string_aleatoria_32_chars_minimo>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=8
REFRESH_TOKEN_EXPIRE_DAYS=7

# Usuários iniciais
ADMIN_EMAIL=gestora@floricultura.com
ADMIN_PASSWORD=<senha_forte>
VIEWER_EMAIL=gerente@floricultura.com
VIEWER_PASSWORD=<senha_forte>
DOCS_ENABLED=true              # /docs, /redoc, /openapi.json — false no Render (render.yaml)

# Pipeline ML — camada agregada L1 (unidade, diário — 2 séries)
TOP_N_PRODUCTS=20               # SKUs com desagregação (L2) detalhada
FORECAST_HORIZON_DAYS=14        # horizonte da previsão (a API mostra 14 dias a partir de hoje)
FORECAST_STORED_DAYS=60         # dias previstos e gravados por geração, a partir do último dia com venda
TEST_DAYS=28                    # hold-out para avaliação
MIN_OBSERVATIONS_DAYS=180       # mínimo de dias por unidade para treinar L1
SEASONAL_PERIOD=7              # sazonalidade semanal do SARIMAX (m=7)
LOG_CV_THRESHOLD=0.7           # log1p acima deste CV

# Scheduler
RETRAIN_DAY_OF_WEEK=mon        # ajuste (fit) dos modelos; pulado sem venda nova desde o último treino
RETRAIN_HOUR=2
RETRAIN_AFTER_UPLOAD_MINUTES=10  # treino após planilha com venda nova; outra planilha no intervalo adia
TRAINING_RUNNER=local          # local: treino em thread da API · externo: a API não treina (Render, ADR-015)
TRAINING_WORKERS=8             # processos no treino dos produtos
DAILY_FORECAST_HOUR=3          # confere o calendário; gera de novo a previsão só se ele mudou
```

---

## Modelo de Dados — Tabelas SQLite

Definidas em `ia-predictor/backend/infrastructure/database.py` (docstrings com o detalhe);
diagrama em `docs/database/modelo_dados.drawio`, gerado por `docs/database/gerar_diagrama_er.py`.

| Tabela | Propósito |
| --- | --- |
| `users` | Usuários com e-mail, hash bcrypt, role (admin/viewer) |
| `revoked_tokens` | Refresh tokens encerrados no logout (`jti`), recusados por `/auth/refresh` até expirarem |
| `units` | As 2 lojas (`jardim-canada`, `itabirito`) |
| `categories` | As 4 categorias do negócio (coluna `categoria` da Etapa 3: Grama, Plantas diversas, Produtos de jardim, Flores de corte) + Serviço e taxa, com `show_on_dashboard` falso |
| `products` | Catálogo: código, nome mais recente, categoria, subcategoria (`categoria_fina`) |
| `sales` | Uma linha de produto por nota, só com os campos da planilha que o sistema usa (sem cliente, vendedor, operador); `is_bulk_order` = encomenda (ADR-013). Índice da deduplicação entre planilhas |
| `calendar_days` | Calendário por loja (loja fechada, abertura excepcional, feriado, data comemorativa); cobre até o fim da previsão gravada |
| `processing_log` | Cada planilha recebida (nome, SHA-256, linhas lidas/novas/duplicadas, qualidade); a planilha não é guardada |
| `retrain_history` | Cada treino (trigger, período usado, config, contagens); `skipped` quando não há venda nova |
| `model_artifacts` | Previsor de cada loja, categoria (desagregação, sem modelo próprio) e produto regular por treino: ordem, MASE, cobertura, `artifact_path` (joblib), métricas do walk-forward |
| `backtest_points` | Previsto × real × naïve de cada dia do walk-forward de cada previsor (loja, categoria, produto) — tela de histórico da previsão |
| `forecast_runs` | Cada geração da previsão (ao fim do treino ou quando o calendário muda): período previsto e SKUs atendidos |
| `forecasts_cache` | Previsão diária com IC 95% por geração, em 3 níveis (loja, categoria, produto); grava `FORECAST_STORED_DAYS` dias e a API entrega os 14 a partir de hoje |

Resumos (volume por loja/categoria, histórico, encomendas, venda das últimas 8 semanas)
não são gravados: saem de `sales`. A previsão não é recalculada todo dia: com o mesmo
modelo e os mesmos dados ela daria os mesmos números, então a janela de 14 dias só anda
sobre o que já foi gravado.

---

## Pipeline Hierárquico — Decisões Técnicas

Ver `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md` para o racional completo,
`ADR-011` para o escopo atual (L1 por `unidade`, sem L3) e
`docs/prediction/04-treino_l1_por_loja.md` para o treino que fixou os valores abaixo.

### L1 — SARIMAX na demanda agregada (`unidade`, série diária — 2 séries)

| Decisão | Valor | Motivo |
| --- | --- | --- |
| Alvo | qtd diária somada por `unidade` (todas as categorias), **venda total**: nenhuma venda sai da série | série densa (poucos zeros), ao contrário de SKU e categoria isolados; separar por categoria não reduz o erro (ADR-011 §4, `eda_separacao.py`) |
| Vendas grandes | **ficam na série e devem ser previstas.** A loja confirmou (2026-10-09) que não são encomendas: são empresas que compram no balcão com o estoque da loja (ex.: NN 5582, Cumbuco, 16/12/2025). Compras recorrentes e vendas entre empresas Verde Perto também são venda normal | clientes cadastrados (≠ `CONSUMIDOR`) são 69,5% do volume de Itabirito e 63,3% do de Jardim Canadá, com série errática (CV² 8,47 e 2,25); `CONSUMIDOR` é suave (CV² ≤ 0,36). Em estudo: prever as duas parcelas separadas e somar × SARIMAX direto no total, ambos avaliados contra o total |
| m (período sazonal) | 7 | sazonalidade semanal. **EDA (2026-09-21, `docs/prediction/00-eda_report.md` §3.3): o padrão é de dia útil — pico em ter–qui para Grama e para Produtos de jardim em Jardim Canadá (em Itabirito, Produtos de jardim tem semana mais uniforme) — e sexta para Flores de corte; sábado fraco; domingo = loja fechada (0).** Não "fim de semana vende mais". Ciclo real mas fraco na variância (Fs ≤ 0.29) — dummies de dia-da-semana como exógenas pesam mais que os termos P/Q |
| D (diferenciação sazonal) | 0 | o ciclo semanal já é capturado pelas dummies de dia-da-semana; com calendário, o termo sazonal AR cai a P = 0 e sobra só Q = 1 (doc 04). Diferenciar a semana (yₜ − yₜ₋₇) sobrediferenciaria e criaria picos falsos nas semanas com feriado. (Histórico curto não é o motivo: com m = 7 há > 100 ciclos.) |
| d (diferenciação regular) | **1** na versão escolhida (A1 d=1); ADF indicava 0 | com d = 1 a previsão parte do nível recente em vez de voltar à média do histórico: melhor no ano e em dezembro nas 2 lojas (doc 04). Limitado a 1 |
| log1p | se CV > 0.7 — na prática sempre (CV 1,0–2,4 nas 2 unidades) | estabiliza a variância (Box-Cox, λ = 0); não é suavização |
| Grid de ordens | p,q ∈ 0..2; P,Q ∈ 0..1; m=7 | balanceia tempo e qualidade |
| Critério de seleção | AIC, só com dados anteriores à 1ª origem do walk-forward | ajuste vs. parcimônia, sem vazamento. AIC não compara modelos com `d` diferente: d = 0 × d = 1 foi decidido no walk-forward |
| Exógenas | 6 dummies de dia-da-semana (ref. domingo), `loja_fechada` (domingo, feriado nacional BrasilAPI — inclui Carnaval —, fechamento observado), `abertura_excepcional` (Itabirito em Dia das Mães e Finados). Calendário por loja: `output/calendario_diario.csv` (Etapa 6) | erro em feriados ≈ 0 e IC 95% de ~79 mil para 5,5 mil (JC) / 2,3 mil (ITA) (docs 03 e 04). Clima, véspera, pós-feriado e início do mês sem efeito; a janela "7 dias até a data" gerou 12% do erro do ano (doc 03). Pesar exógenas por RF MDI não muda um SARIMAX linear (o coeficiente absorve a escala): MDI só como diagnóstico |
| Datas comemorativas | **não entram no L1** (só via `abertura_excepcional`) | no total da unidade os efeitos se anulam (flores sobem, grama cai); `dias_ate_*` e `janela_7d_*` ficam para a desagregação por categoria (L2) |
| Previsão pontual | mediana (`expm1` da média em log) | o fator de Duan (média) explodiu (4,6× em Itabirito sem calendário) e foi descartado (doc 04 §2). Efeito colateral: previsão cobre 81–88% do vendido |
| Mínimo de observações | 180 dias | abaixo disso: `insufficient_data` para a unidade inteira |
| Hold-out para avaliação | 28 dias | |
| Walk-forward CV | ≥4 folds, origem móvel, horizonte 14 dias. Protocolo atual (doc 04): 26 rodadas cobrindo um ano, janela expansiva; todo parâmetro estimado dos dados (ex.: limiar de encomenda) recalculado em cada rodada | obrigatório antes de `status = "trained"` |

### L2 — Desagregação em cascata: `unidade` → `categoria` → SKU

| Decisão | Valor | Motivo |
| --- | --- | --- |
| Método | participação móvel (share das últimas 4–8 semanas) × perfil de dia-da-semana **do nível**, aplicado 2×: `unidade→categoria`, depois `categoria→SKU`; no passo `unidade→categoria`, também o índice de data comemorativa **da categoria** | evita modelar com SARIMAX uma série (categoria ou SKU) que não ganha acurácia por isso (categoria: ADR-011 §4) ou é quase toda zero (SKU). O índice de data recupera o que o total esconde: no Dia das Mães, Flores de corte sobe 2,14× enquanto a unidade cai 0,66× |
| Base | participações calculadas sobre a venda **total** (mesmo alvo do L1) | as vendas grandes são demanda real (confirmado pela loja em 2026-10-09) |
| Fallback | categoria com histórico curto → rateio uniforme entre categorias da unidade; SKU com < 28 dias com venda ou < 8 vendas → rateio uniforme da categoria | |

### L3 — Política de reposição: fora de escopo (ADR-011)

A loja decide quando e quanto comprar. `shelf_life_dias`, cobertura-alvo, estoque de
segurança, estoque atual e a simulação de perda/ruptura foram removidos. O que fica no
lugar está em estudo (doc 04 §5, passo 2): entregar **dois números por dia**, a venda mais
provável (mediana) e uma quantidade para ter disponível (quantil mais alto da faixa,
escolhido pela loja).

### Comparação acadêmica (ii)

SARIMAX hierárquico (L1+L2) **×** demanda intermitente por SKU (Croston/TSB/SBA),
ambos diários, mesmos splits de walk-forward. Substitui a antiga comparação "mensal ×
diária" — relatório em `docs/`.

---

## Limiares de Qualidade dos Modelos

| Métrica | Limiar | Status se falhar |
| --- | --- | --- |
| MASE (L1 e SKU) | < 1.0 (bate a naïve sazonal semanal) | `low_confidence` |
| Cobertura empírica do IC 95% | ∈ [90%, 98%] | `low_confidence` |
| Observações mínimas L1 (`unidade`) | ≥ 180 dias | `insufficient_data` |
| Observações mínimas SKU | ≥ 28 dias com venda ou ≥ 8 vendas | fallback de rateio da categoria |
| Ljung-Box (p-value, resíduos L1) | > 0.05 | log de aviso; não bloqueia deploy |
| Shapiro-Wilk (p-value, resíduos L1) | > 0.05 | log de aviso; não bloqueia deploy |

**Comparação entre experimentos** (docs 02 → 03 → 04): além do MASE, reportar o erro
relativo à naïve sazonal **na mesma janela de teste**, agregado como razão das somas
(ΣAE / ΣAE_naïve, como nos docs 03 e 04; o doc 02 usou média das razões por rodada), o nº
de folds em que o modelo vence a naïve e a **largura** do IC 95%. O MASE usa a escala do
treino e fica otimista quando o treino tem picos: no A0-crua, MASE 0,40 correspondia a um
ganho de só 18% sobre a naïve, e a própria naïve tirava MASE 0,49
(`docs/prediction/02-baseline_serie_crua_pre_eda.md` §4.4).

`low_confidence` ≠ falha: a previsão ainda é gerada, mas com aviso visual no dashboard.
MAPE e SMAPE continuam calculados e reportados, mas são **informativos** (instáveis com
contagem baixa) — não classificam. Ljung-Box e Shapiro-Wilk compõem a dimensão de
"diagnóstico de resíduos" (seção 6.5 do artigo) — não bloqueiam o deploy, mas MUST ser
logados por modelo L1 treinado.

---

## Contratos de API — Perfis de Acesso

| Endpoint | Método | Perfil |
| --- | --- | --- |
| `/health` | GET | público |
| `/auth/login` | POST | público |
| `/auth/refresh` | POST | qualquer |
| `/auth/logout` | POST | público — revoga o refresh token |
| `/auth/me` | GET | qualquer |
| `/api/v1/upload` | POST | **admin** |
| `/api/v1/models/retrain` | POST | **admin** |
| `/api/v1/forecast/{produto_cod}` | GET | viewer — previsão diária, `horizon_days` |
| `/api/v1/forecast/batch` | GET | viewer — previsão dos top N para o dashboard |
| `/api/v1/models/status` | GET | viewer — status dos 2 modelos L1 (um por unidade) |
| Demais `/api/v1/*` | GET/POST | viewer |

Os endpoints de reposição (`/api/v1/replenishment/*`) foram removidos do contrato na
versão 3.0.0 do `openapi.yaml` (ADR-011).

---

## Spec-Kit

Este projeto usa GitHub Spec-Kit (`specify-cli 0.14.3`) instalado como skills em `.claude/skills/`.

Comandos disponíveis (invocar via Skill tool ou como `/speckit-*`):

| Skill | Propósito |
| --- | --- |
| `/speckit-constitution` | Atualizar princípios em `.specify/memory/constitution.md` |
| `/speckit-specify` | Criar nova spec de feature em `specs/` |
| `/speckit-plan` | Criar plano técnico para a spec ativa |
| `/speckit-tasks` | Gerar lista de tarefas a partir do plano |
| `/speckit-analyze` | Verificar consistência entre spec, plan e tasks |
| `/speckit-converge` | Comparar codebase atual com tasks pendentes |
| `/speckit-implement` | Executar próxima tarefa pendente do tasks.md |

---

## Artefatos de Referência

| Arquivo | Conteúdo |
| --- | --- |
| `SPECS.md` | Especificação técnica completa (arquitectura, módulos, schemas) |
| `ia-predictor/openapi.yaml` | Contratos de API em OpenAPI 3.0 (fonte da verdade) |
| `specs/001-sistema-previsao-vendas/spec.md` | User Stories e requisitos funcionais |
| `specs/001-sistema-previsao-vendas/plan.md` | Plano técnico com constitution check |
| `specs/001-sistema-previsao-vendas/tasks.md` | Tarefas organizadas por fase (TDD) |
| `.specify/memory/constitution.md` | 6 princípios governantes (v3.1.0) |
| `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md` | **Espinha da revisão de escopo mensal→diário** — arquitetura L1/L2/L3, validação, shelf-life (L3 e grão `unidade × categoria` revisados pelo ADR-011) |
| `docs/prediction/ADR-011-escopo-previsao-sem-reposicao.md` | **Escopo atual**: previsão de demanda sem reposição (L3 fora), 2 unidades, 3 categorias + `Servico e taxa`, L1 por `unidade` (teste de separação §4). Lista o que ainda falta propagar |
| `docs/README.md` | Índice da documentação por área + convenção de ADRs |
| `docs/prediction/`, `docs/backend/`, `docs/database/`, `docs/frontend/` | ADRs organizados por área (ver `docs/README.md` para a lista completa) |
| `docs/project/Projeto Tecnico Verde Perto Final...pdf` | Projeto técnico acadêmico original (fonte primária, revisado pelo orientador) |
| `docs/project/current_files_state.md` | Raio-x do que já foi feito (dados, pré-processamento, modelagem) vs. requisitos do artigo |
| `docs/prediction/plano_experimentos_modelagem.md` | Plano de experimentos: L1 baseline × enriquecido × demanda intermitente/outros modelos |
| `docs/prediction/01-pre_processing.md` | O que os scripts de `training_scripts/preprocessing/` fazem e por quê: Etapas 1–3 (parsing, colunas removidas, taxonomia) e 4–7 (base limpa, encomendas, calendário por loja com `loja_fechada`/`abertura_excepcional`, séries diárias por unidade e unidade×categoria). §11 mapeia cada achado do EDA/treinos para a etapa que o resolve |
| `docs/uml/` *(parcial — 2 de 5 diagramas)* | Diagramas de casos de uso, atividades, classes, modelo de dados e arquitetura lógica (seção 6.4 do artigo) |
| `docs/prediction/02-baseline_serie_crua_pre_eda.md` | Primeiro treino (ponto zero): SARIMA puro sobre 1 série diária crua, pré-EDA. Como foi feito, resultados, diagnóstico de por que foi fraco (encomendas, Carnaval, mudança de nível, MASE inflado, IC largo) e o que resolver. Scripts em `training_scripts/baseline/` |
| `docs/prediction/03-enriquecimento_serie_crua.md` | Segundo treino: a mesma série crua com calendário (BrasilAPI + fechamentos locais 15/08 e 08/12) e clima (Open-Meteo). Calendário: erro em feriados ~0, IC 95% 6× mais estreito, −9% de erro no ano. Clima: sem ganho. Diagnóstico: encomendas = 48% do erro restante; janela "7 dias até Mães/Finados" = 12% do erro (usar "loja aberta excepcionalmente no dia"). Scripts em `training_scripts/enriched/`, cache em `data/external/` |
| `docs/prediction/04-treino_l1_por_loja.md` | Terceiro treino: L1 por loja sobre o pré-processamento v2. Melhor versão A1 com d=1 (calendário + acompanha o nível): MASE 0,58 nas 2 lojas, vence a naïve em 24/26 rodadas, IC95 91–94% → `trained`. Previsão pontual = mediana (fator de Duan descartado). §5 = próximos passos: encomendas como fluxo próprio, dois números (mediana + quantil para estoque), nível, desagregação L2 |
| `docs/prediction/05-dataframe_treino_l1_exemplo.md` | DataFrame real recebido pelo `SARIMAX(z, exog=X, ...)` na seleção de ordem do L1 (uma unidade): só o alvo transformado (`log1p` + teto p99) e 8 dummies de calendário — nenhuma coluna categórica/nominal. CSVs em `training_scripts/results/metrics/l1_dataframe_treino_exemplo_*.csv`, gerados por `training_scripts/baseline/export_dataframe_treino_exemplo.py` |
| `docs/prediction/06-experimento_janela_dias_proximos.md` | Testa se uma exógena "6 dias antes de qualquer data comemorativa" (isolada do dia de `abertura_excepcional`, coeficiente único entre as 6 datas) melhora o L1. Resultado: **não ajuda** (−0,8% / −0,1% no erro relativo à naïve, abaixo do limite de 5%) — confirma empiricamente que o efeito cancela no total da unidade e pertence à L2 (ainda não implementada). Script: `training_scripts/baseline/experimento_janela_dias_proximos.py` |
| `docs/prediction/00-eda_report.md` | Relatório de EDA (T000b) — as 2 séries do L1 por unidade (§3.0, `16_series_l1_unidade.png` a `19_stl_unidade.png`), as 6 séries de desagregação `unidade×categoria` (§3.1–3.9, `10_series_l1_paineis.png` a `15_stl_par_denso.png`), granularidade das categorias (§3.10) e separação unidade/categoria (§3.11); §4 = ajustes de modelagem; §5 = questões para o cliente. Scripts em `training_scripts/eda/` |
| `docs/database/dicionario_dados_fonte.md` | Dicionário campo a campo do relatório "Contas a Receber" (20 colunas, semântica, faixa, etapa de remoção) |
