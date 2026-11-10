# CLAUDE.md — Sistema de Previsão de Vendas · Floricultura

Guia para sessões de desenvolvimento com Claude Code.
Leia este arquivo antes de qualquer implementação.

---

## O que é este projeto

TCC de Ciência da Computação (Centro Universitário Dom Helder, 2026), em parceria com a
Floricultura Verde Perto (unidades em Nova Lima — Jardim Canadá — e Itabirito/MG).
Sistema de **previsão de demanda diária** para rede de floricultura com 2 unidades
operacionais: um SARIMAX direto em cada uma das 4 categorias e em cada produto de grama,
por loja (ADR-017), e dashboard React. A loja decide a compra; o sistema informa quanto
deve vender (ADR-011).

**Domínio**: floricultura / garden center · grama e produtos de jardim ≈ 98% do volume,
flores de corte ≈ 2% · sazonalidade semanal de dia útil + datas comemorativas  
**Dados**: 324k+ transações · Jan/2024–Fev/2026 · 5.100+ SKUs · 2 unidades  
**Entregável**: previsão de demanda **por dia**, horizonte de **14 a 91 dias** escolhido na tela
(padrão 14; o treino grava 91 — ADR-021), com intervalo de confiança de 95%, por categoria e por produto de grama de cada loja (o total da loja é a
soma das categorias), e o histórico das previsões congelado dia a dia — ver
`docs/prediction/ADR-017-previsao-por-categoria-e-grama.md`. A recomendação de reposição
(L3) saiu de escopo (ADR-011)  
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
| Modelagem | statsmodels 0.14 (SARIMAX por categoria e por produto de grama, por loja — ADR-017); scikit-learn, Croston/TSB/SBA e outros só nos experimentos (`training_scripts/`) |
| Análise exploratória (EDA) | Jupyter Notebooks + matplotlib, seaborn, plotly (não entram no runtime de produção) |
| Auth | python-jose (JWT HS256) + passlib (bcrypt) |
| Banco | Postgres no Neon (compartilhado) e SQLite (local), via SQLAlchemy 2.0 + psycopg 3 — ADR-014 |
| Treino | Sem agendador (ADR-017): botão "Treinar previsões" (admin; thread da API com `TRAINING_RUNNER=local`) ou `python -m backend.scripts.treinar_previsoes` (API que não treina, Render); pulado (`skipped`) sem dados novos |
| Serialização | openpyxl (XLSX), reportlab (PDF); os modelos não são salvos em joblib (coeficientes em `series_models.params`) |
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
│   │   │   ├── etl/             ← cobertura (dias de venda faltando na planilha, antes de gravar)
│   │   │   ├── features/        ← time_series (série diária), exogenous (calendário)
│   │   │   ├── models/          ← order_selection, trainer (walk-forward + complemento), evaluator (métricas, resíduos), forecaster
│   │   │   ├── historico_previsao.py ← regra do histórico congelado
│   │   │   └── painel.py        ← montagem do painel das telas
│   │   └── infrastructure/      ← DB (ORM, colunas novas em banco existente), storage
│   ├── data/
│   │   ├── raw/                 ← XLSX brutos (upload)
│   │   └── processed/
│   │       └── contas_a_receber.csv   ← base consolidada (sep=";")
│   ├── models/                  ← registro dos modelos dos experimentos (o sistema não salva joblib)
│   ├── training_scripts/        ← experimentação pré-produção (fora do backend)
│   │   ├── preprocessing/       ← XLSX bruto → base limpa → encomendas → calendário por loja → séries diárias (L1 e desagregação); `run_all.py` roda as 7 etapas (docs/prediction/01-pre_processing.md)
│   │   ├── eda/                 ← análise exploratória (base transacional, séries do L1, granularidade das categorias, classificação de demanda, distribuição da quantidade dos pedidos e limiar de encomenda grande — ADR-018)
│   │   ├── baseline/            ← L1: série crua (doc 02) e treino por loja `sarimax_l1_por_loja.py` (doc 04: A0, A1, A1 d=1, Holt-Winters)
│   │   ├── enriched/            ← L1 na série crua + calendário e clima (doc 03)
│   │   ├── alternative_models/  ← Croston/TSB/SBA por SKU, ETS, XGBoost, rede neural global
│   │   ├── disaggregation/      ← categoria direta × desagregação (ADR-016), estacionariedade por categoria e SKU
│   │   ├── encomendas/          ← treino de produção com cada limiar de encomenda grande (fixo 2.000 × 4 × 3 desvios por loja, ADR-018)
│   │   ├── datas_comemorativas/ ← EDA das datas e treino de produção com e sem fator multiplicativo (doc 08)
│   │   ├── validation/          ← walk-forward CV (origem móvel, h=14d), MASE/RMSSE, resíduos (compartilhado)
│   │   ├── frontend_mock/       ← receita do treino anterior (loja + desagregação), registro histórico
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

## Regras Invioláveis (Constituição v4.0.0)

Consulte `.specify/memory/constitution.md` para o texto completo. Resumo:

1. **Domínio Puro**: `backend/domain/` NUNCA importa FastAPI, SQLAlchemy ou APScheduler.
2. **Estatística antes de ML**: SARIMAX é o modelo central. **No sistema (ADR-017)**, cada
   uma das 4 categorias e cada produto de grama, em cada loja, tem o seu SARIMAX; o total
   da loja é a soma das categorias. O L1 por unidade e a desagregação saíram: o
   experimento `disaggregation/categoria_direta_vs_desagregacao.py` (351 origens dia a dia,
   4 categorias, fluxo diário) mostrou o SARIMAX direto na categoria vencendo a
   desagregação em 7 dos 8 pares (ADR-016). O ajuste das datas comemorativas depois do
   SARIMAX (ADR-019) é estatística permitida. Croston/TSB/SBA ficam na trilha de comparação
   por SKU; NN/boosting só com evidência empírica.
3. **Validação obrigatória**: walk-forward CV (≥4 folds, origem móvel, h=14 dias; no
   sistema, 56 origens andando 1 dia) antes de gravar a previsão, com MASE, cobertura do
   IC 95% e as outras métricas registradas em cada série. As métricas não classificam a
   série: toda série que ajusta tem previsão (`trained`). Sem simulação de perda/ruptura
   (L3 fora, ADR-011). O fator das datas comemorativas, que o walk-forward do treino quase
   nunca atravessa, é validado em experimento próprio (doc 08) e revisto a cada ano de vendas.
4. **Linguagem do usuário**: mensagens de erro e alertas em PT-BR sem jargão técnico.
5. **Rastreabilidade**: todo upload e treino gravados em `processing_log` e `forecast_jobs`
   (treino sem dados novos fica como `skipped`). Cada treino registra a configuração com a
   versão do código, o período usado, as contagens de séries (com previsão, sem dados, com
   falha) e o log série a série (`forecast_job_logs`, `series_models`), liga a si as
   planilhas que entraram nele (`processing_log.forecast_job_id`) e congela a previsão em
   `forecast_history`.
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

# Treinar a previsão fora da API (o mesmo treino do botão "Treinar previsões"), a partir de
# ia-predictor/ — para a API no Render (TRAINING_RUNNER=externo); proot/Termux: --workers 1
python -m backend.scripts.treinar_previsoes --workers 8

# Reclassificar as encomendas grandes da base inteira com o limiar de cada loja (ADR-018),
# sem apagar nada; sem --aplicar só mostra o que mudaria. Rodado no Neon em 31/10/2026
python -m backend.scripts.reclassificar_encomendas [--aplicar]

# Reaplicar as regras de categoria (taxonomy/categorias.py) ao catálogo do banco: a planilha
# só classifica produto novo. Sem --aplicar só mostra o que mudaria; depois, conferir as
# encomendas com reclassificar_encomendas (produto que entra/sai de Serviço e taxa)
python -m backend.scripts.reclassificar_produtos [--aplicar]

# Preencher o histórico da previsão de um banco antigo a partir do último treino
python -m backend.scripts.semear_historico [--recriar]

# Rodar testes unitários
pytest ia-predictor/tests/unit/ -v

# Rodar testes de integração
pytest ia-predictor/tests/integration/ -v

# Testes de ponta a ponta (Playwright): front + API real num SQLite com base sintética
# (nunca o Neon), fotos de cada fluxo em app-react/e2e/fotos/ — ver app-react/e2e/README.md
cd app-react && npm run e2e:instalar   # uma vez: Chromium do Playwright
cd app-react && npm run e2e            # 1ª vez monta e treina a base (~5 min, cache em ia-predictor/tests/e2e/.cache/)

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

# Previsão (ADR-017) — 4 categorias e cada produto de grama, por loja; m=SEASONAL_PERIOD, D=0 fixos; d de cada série pelo walk-forward (ADR-020)
FORECAST_HORIZON_DAYS=14           # horizonte do walk-forward (validação e métricas)
FORECAST_MAX_HORIZON_DAYS=91       # dias previstos a partir do dia seguinte à última venda; a tela escolhe de 14 a 91 (ADR-021)
FORECAST_SERVICE_D_CANDIDATES=[0,1]  # d testados no walk-forward de cada série; fica o que errou menos (ADR-020); [0] = d = 0 em tudo
SEASONAL_PERIOD=7                  # sazonalidade semanal do SARIMAX (m=7)
MIN_OBSERVATIONS_DAYS=180          # histórico mínimo antes da 1ª origem do walk-forward
FORECAST_SERVICE_WINDOW_DAYS=545   # janela deslizante de treino (ADR-022; antes 365)
FORECAST_SERVICE_WF_ORIGINS=56     # origens do walk-forward, andando 1 dia (8 semanas)
FORECAST_SERVICE_MIN_SALE_DAYS=28  # produto de grama: dias com venda nos últimos FORECAST_SERVICE_MIN_SALE_WINDOW_DAYS para treinar
FORECAST_SERVICE_MIN_SALE_WINDOW_DAYS=365  # período da regra acima, separado da janela de treino (ADR-022)
FORECAST_SERVICE_KEEP_BACKTEST_JOBS=4  # treinos concluídos que guardam o walk-forward inteiro
FORECAST_SERVICE_EVENT_FACTOR=true # fator das datas comemorativas: alta em Flores de corte, queda de fim de ano e Dia do Trabalho nas outras (ADR-019)
TRAINING_WORKERS=8                 # processos no treino (proot/Termux de desenvolvimento: use 1)
TRAINING_RUNNER=local              # local: botão "Treinar previsões" (thread da API) · externo: a API não treina (Render, script treinar_previsoes)
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
| `sales` | Uma linha de produto por nota, só com os campos da planilha que o sistema usa (sem cliente, vendedor, operador); `is_bulk_order` = encomenda grande: pedido acima de média + 4 desvios-padrão da quantidade de todos os pedidos da loja (ADR-018); cada planilha recalcula o limiar da loja e classifica só as linhas que insere (a base gravada não é remarcada); o limiar de cada carga fica em `processing_log.quality.limiar_encomenda_un`. Índice da deduplicação entre planilhas |
| `calendar_days` | Calendário por loja (loja fechada, abertura excepcional, feriado, data comemorativa); precisa cobrir os 14 dias seguintes à última venda (dia que faltar usa o padrão: fechada só no domingo) |
| `processing_log` | Cada planilha gravada (nome, SHA-256, linhas lidas/novas/duplicadas, qualidade); em `quality`, o período da planilha e os dias de loja aberta que ficaram sem venda, avisados na conferência antes de gravar; `forecast_job_id`, o primeiro treino que a usou. A planilha não é guardada. `kind = "reclassification"`: a reclassificação das encomendas grandes da base (`reclassificar_encomendas`), com os limiares de cada loja, ou das categorias do catálogo (`reclassificar_produtos`), com cada produto que mudou — fora da lista de arquivos |
| `forecast_jobs` | Cada treino da previsão (botão "Treinar previsões" ou script): status, andamento (série atual, %), impressão digital dos dados (`skipped` se não mudaram desde o último `done`), `data_until`, configuração com a versão do código, contagens por status. As telas leem o último `done` |
| `forecast_job_logs` | Log do treino, uma linha por série (ordem, AIC, métricas, resíduos, status ou motivo da recusa) e as do treino (planilhas novas, histórico gravado, limpeza do walk-forward) |
| `series_models` | Cada série (4 categorias + cada produto de grama, por loja): status, ordem, AIC, MASE, cobertura, métricas do walk-forward e diagnóstico dos resíduos (`metrics`), coeficientes do ajuste final (`params`); `insufficient_data`/`error` com o motivo |
| `series_forecasts` | Previsão dos 91 dias seguintes à última venda (14 até 08/11/2026; a tela mostra de 14 a 91, ADR-021), com IC 95%, por série; `event_factor`: multiplicador da data comemorativa que entrou no dia (ADR-019), nulo sem ajuste |
| `series_backtest_points` | Previsto × real × naïve de cada origem e horizonte do walk-forward (origem andando 1 dia), por série — só nos últimos `FORECAST_SERVICE_KEEP_BACKTEST_JOBS` treinos concluídos |
| `forecast_history` | Histórico da previsão por categoria e produto de grama, gravado por cada treino `done` do serviço de previsão (`job_id`): o previsto de cada dia é o da última previsão feita antes dele, congelado depois que o dia passa — treino seguinte 9 dias depois congela 9 dias; cada treino grava os 91 dias previstos, então só um intervalo de mais de 91 dias deixa sobra, que o 1º dia das janelas do walk-forward do treino seguinte (h = 1, com o complemento até a última venda) preenche, como antes do 1º treino (até 08/11/2026 a previsão gravada era de 14 dias). `store_closed`: se o calendário dava a loja fechada quando o dia foi previsto. `event_factor`: o multiplicador da data comemorativa (ADR-019) — o previsto do modelo sem ele é `predicted / event_factor`. A tela compara com o vendido de `sales` (sem encomendas grandes). `semear_historico [--recriar]` preenche a partir do último treino |

Resumos (volume por loja/categoria, histórico, encomendas, venda das últimas 8 semanas)
não são gravados: saem de `sales`. A previsão não é recalculada todo dia: com o mesmo
modelo e os mesmos dados ela daria os mesmos números. Ela muda quando a loja treina de
novo com vendas novas. As tabelas do treino anterior (`retrain_history`, `model_artifacts`,
`backtest_points`, `forecast_runs`, `forecasts_cache`) saíram do ORM (ADR-017); num banco
antigo continuam lá, sem uso.

---

## Previsão — Decisões Técnicas (ADR-017)

Ver `docs/prediction/ADR-017-previsao-por-categoria-e-grama.md` para a decisão e
`docs/prediction/07-previsao_14_dias_e_historico.md` para o funcionamento (ciclo da loja,
treino, histórico, conferência da planilha). Código: `backend/services/servico_previsao.py`
e `backend/domain/models/trainer.py`.

| Decisão | Valor | Motivo |
| --- | --- | --- |
| Séries | em cada loja, as 4 categorias e cada produto de grama (com ≥ 180 dias antes da 1ª origem; produto, venda em ≥ 28 dos últimos 365 dias). Até 28/02/2026, com a classificação SKU a SKU de 04/11/2026 (grama preta, capim dos Texas e semente de braquiária em Grama): 19 produtos de grama → 43 séries (8 categorias + 35 grama × loja), 23 com previsão (8 + 15); antes, 9 produtos → 25 séries, 17 com previsão (9 + 8) — lista e resultado no doc 07 §2 | categoria direta vence a desagregação em 7 de 8 pares (ADR-016); a loja compra grama produto a produto. Total da loja = soma das categorias (faixa conservadora). Outras categorias não têm previsão por produto |
| Alvo | fluxo diário: sem as encomendas grandes — pedido acima de média + 4 desvios-padrão da quantidade de todos os pedidos da loja, hoje 1.343 un. em Jardim Canadá e 1.960 em Itabirito (ADR-018; antes, 2.000 fixo, ADR-013) —, sem `Servico e taxa` | no treino de produção (17 séries, ADR-018 §4.1), 4 desvios erra menos que o 2.000 fixo em 5 séries de Jardim Canadá, mais em 2 e igual em 10; 3 desvios piora a cobertura da faixa (abaixo de 90%) ou leva o MASE acima de 1 em 3 séries |
| Modelo | SARIMAX m = 7, D = 0; **d escolhido série a série (ADR-020)**: ordem por AIC (p, q ∈ 0..2; P, Q ∈ 0..1) só com a janela antes da 1ª origem, para d = 0 (com constante) e d = 1 (sem); fica o d cujo walk-forward errou menos (MAE) | doc 10 (teste no resíduo da regressão com as exógenas do modelo, todos os dias, janela de ajuste): nas 8 séries em que o KPSS rejeita o nível estacionário (Grama das 2 lojas, Plantas e Produtos de JC, gramas grandes), d = 1 erra menos em todas; nas esparsas o KPSS não tem poder e d = 1 ajuda em 7; o ADF é distorcido (MA perto de −1, Schwert). Critérios: KPSS a cada treino −2,5%, família −3,6%, walk-forward da série −3,6 a −3,8% (limite olhando o ano: −3,9%). Custo: treino ~3× mais lento (40 min × 13,5 no local). Antes (ADR-017): d = 0 fixo |
| Exógenas | 6 dummies de dia da semana, `loja_fechada`, `abertura_excepcional` (calendário de cada loja) | as do L1 (docs 03 e 04) |
| Datas comemorativas | ADR-019. **Alta**, só Flores de corte: previsto e faixa dos dias abertos de 6 dias antes até o Dia da Mulher, das Mães, dos Namorados, o Natal e o Ano Novo (26–31/12) × mín(3, máx(1, 1 + 0,5 · (fator − 1))). **Queda**, nas outras séries (categorias e produtos de grama): de 26 a 31/12 e na semana do Dia do Trabalho × máx(0,2, fator), só se cada uma das últimas ocorrências (≥ 2) ficou em até 0,8 de uma semana comum. Fator = venda ÷ base (mesmo dia da semana, 4 semanas antes e depois) nas últimas 3 ocorrências, recalculado a cada treino, só com venda anterior ao 1º dia previsto; datas pela regra, não pelo calendário gravado | alta: sem o ajuste o modelo prevê uma semana comum (40–46% do vendido); com ele, −40% a −45% no erro do total da semana nas 10 ocorrências (doc 08), sem melhorar o erro de cada dia. Queda: o modelo prevê 2 a 5× o vendido de 26 a 31/12; a queda inteira corta o erro da semana em todas as ocorrências testadas (Grama de Itabirito 268% → 27%) e o de cada dia (doc 08 §9.3). Finados, Sexta-feira Santa e Corpus Christi ficam fora |
| Janela | deslizante de **545 dias** (ADR-022; até 10/11/2026, 365) | doc 11: 545 é a melhor janela única, −1,9% no erro dos 14 dias nas 23 séries e nas categorias (Flores de corte −4 a −6%); 90 dias piora (+8,6% nas categorias); escolher a janela série a série ganharia nos produtos de pouco volume, com treino ~6× mais lento |
| Walk-forward | 56 origens andando 1 dia (8 semanas), h = 14; métricas nos dias de loja aberta; + 13 origens parciais (complemento, h = 1, fora das métricas) até a última venda | o 1º dia de cada janela alimenta o histórico até a véspera da previsão |
| Previsão | os 91 dias seguintes à última venda (ADR-021), faixa de 95% (sem `log1p`); a tela e os relatórios mostram 2, 3, 4, 6 ou 8 semanas ou 3 meses (caixa de opções "Horizonte", padrão 2 semanas), sem aviso além de 2 semanas; o teste de acerto é o das 2 primeiras; dia de loja fechada no calendário = previsto e faixa zero (também no walk-forward) | a exógena `loja_fechada` só desconta um valor fixo: os termos MA deixavam previsão no domingo depois de dias fortes (Flores de corte de Jardim Canadá, 7,2 em 01/03/2026; doc 07 §3) |
| Resíduos | Ljung-Box (14 dias) e Shapiro-Wilk do ajuste final, em `series_models.metrics`, citados no log quando p ≤ 0,05 | dimensão "diagnóstico de resíduos" do artigo; não bloqueia |
| Treino | botão "Treinar previsões" (admin) ou script `treinar_previsoes`; `skipped` se vendas, calendário, catálogo e a receita do modelo (d de cada família, horizontes, janela...) não mudaram (SHA-256) | com planilhas semanais, a gestora treina quando termina de enviar; não há agendador |
| Histórico | `forecast_history`: o previsto de cada dia é o da última previsão feita antes dele; cada treino `done` troca os dias ≥ dia seguinte à última venda (os 91 previstos) e o walk-forward (h = 1) preenche só os vazios |
| Retreino | a cada planilha semanal | doc 09 / ADR-021 §4: treino mensal erra 2% a mais na média e 15% no pior mês; trimestral, 3% e 32% (viradas de temporada: janeiro, novembro) | a tela mostra o que a loja viu, sem reescrever o passado |
| Conferência da planilha | `POST /upload/verificacao` avisa os dias de loja aberta que ficariam sem venda antes de gravar | uma semana esquecida viraria venda zero no treino e no histórico |

## Experimentos anteriores: L1 por unidade + desagregação (registro histórico)

**Fora do sistema desde o ADR-017.** As tabelas abaixo documentam o treino que as telas
usavam até 2026-10-26 (receita em `training_scripts/frontend_mock/gerar_dados_frontend.py`)
e os experimentos que levaram a ele — evidência para o artigo.

Ver `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md` para o racional completo,
`ADR-011` para o escopo da época (L1 por `unidade`, sem L3) e
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
| Walk-forward CV | ≥4 folds, origem móvel, horizonte 14 dias. Protocolo atual (doc 04): 26 rodadas cobrindo um ano, janela expansiva; todo parâmetro estimado dos dados (ex.: limiar de encomenda) recalculado em cada rodada | obrigatório antes de gravar a previsão |

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

As métricas do walk-forward (MAE, WAPE, MASE, cobertura e largura do IC 95%, erro relativo à
naïve) são registradas em cada série e mostradas na tela de histórico; não classificam a série.
Os limiares abaixo decidem só se a série tem previsão.

| Critério | Limiar | Status se falhar |
| --- | --- | --- |
| Histórico antes da 1ª origem do walk-forward | ≥ 180 dias (= 249 dias de calendário da 1ª à última venda: 180 + 56 origens + 13 do complemento; doc 07 §2) | `insufficient_data` (sem previsão) |
| Produto de grama: dias com venda na última janela de 365 | ≥ 28 | `insufficient_data` (sem previsão) |
| Ljung-Box (p-value, resíduos do ajuste final) | > 0.05 | citado no log; não bloqueia |
| Shapiro-Wilk (p-value, resíduos do ajuste final) | > 0.05 | citado no log; não bloqueia |

**Comparação entre experimentos** (docs 02 → 03 → 04): além do MASE, reportar o erro
relativo à naïve sazonal **na mesma janela de teste**, agregado como razão das somas
(ΣAE / ΣAE_naïve, como nos docs 03 e 04; o doc 02 usou média das razões por rodada), o nº
de folds em que o modelo vence a naïve e a **largura** do IC 95%. O MASE usa a escala do
treino e fica otimista quando o treino tem picos: no A0-crua, MASE 0,40 correspondia a um
ganho de só 18% sobre a naïve, e a própria naïve tirava MASE 0,49
(`docs/prediction/02-baseline_serie_crua_pre_eda.md` §4.4).

MAPE e SMAPE continuam calculados e reportados, mas são **informativos** (instáveis com
contagem baixa) — não classificam. Ljung-Box e Shapiro-Wilk compõem a dimensão de
"diagnóstico de resíduos" (seção 6.5 do artigo) — não bloqueiam o deploy, mas MUST ser
logados por modelo treinado: ficam em `series_models.metrics` (`ljung_box_p`, `shapiro_p`)
e no log do treino.

---

## Contratos de API — Perfis de Acesso

| Endpoint | Método | Perfil |
| --- | --- | --- |
| `/health` | GET | público |
| `/auth/login` | POST | público |
| `/auth/refresh` | POST | qualquer |
| `/auth/logout` | POST | público — revoga o refresh token |
| `/auth/me` | GET | qualquer |
| `/api/v1/upload/verificacao` | POST | **admin** — confere a planilha sem gravar: período por loja, vendas novas/já carregadas e dias de loja aberta que ficariam sem venda (aviso antes de confirmar) |
| `/api/v1/upload` | POST | **admin** — grava, depois da confirmação; `needs_training` quando há venda nova |
| `/api/v1/servico-previsao/*` | GET/POST | **admin** — treino da previsão: status, disparo (`POST /treinos`: 202 treina em segundo plano, 200 `skipped` sem dados novos, 503 se a API não treina), log e resultado por série |
| `/api/v1/contexto` | GET | viewer — layout: lojas, categorias, última venda, status das séries do último treino |
| `/api/v1/painel` | GET | viewer — previsão de 91 dias (categorias e grama por loja; `configuracao.horizonte_previsao_dias`; a tela recorta de 14 a 91 — v8.0.0), histórico de vendas, encomendas, teste de acerto. O fator das datas comemorativas (ADR-019) já vem no previsto e não é exposto |
| `/api/v1/painel/historico/{loja}/{categoria\|produto}/{item}` | GET | viewer — `serie` (vendido × previsto congelado) e `avaliacao` (MAE, WAPE, MASE e amplitude do IC 95% do walk-forward do último treino que avaliou a série) — v7.0.0 |
| Demais `/api/v1/*` (análises, registros) | GET | viewer |

Os endpoints de reposição (`/api/v1/replenishment/*`) saíram na versão 3.0.0 do
`openapi.yaml` (ADR-011); os do treino anterior (`/api/v1/models/*`), o teste de acerto por
produto e as rotas nunca implementadas (products, forecast, alerts, simulation, reports),
na 4.0.0 (ADR-017).

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
| `.specify/memory/constitution.md` | 6 princípios governantes (v4.0.0, emendada em 2026-11-05 e 2026-11-09) |
| `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md` | **Espinha da revisão de escopo mensal→diário** — arquitetura L1/L2/L3, validação, shelf-life (L3 e grão `unidade × categoria` revisados pelo ADR-011) |
| `docs/prediction/ADR-011-escopo-previsao-sem-reposicao.md` | Escopo: previsão de demanda sem reposição (L3 fora), 2 unidades; o L1 por `unidade` foi revisado pelo ADR-017 |
| `docs/prediction/ADR-016-categoria-direta-vs-desagregacao.md` | Evidência: SARIMAX direto na categoria vence a desagregação em 7 de 8 pares categoria-loja (aceito pelo ADR-017) |
| `docs/prediction/ADR-018-limiar-de-encomenda-por-desvios.md` | Encomenda grande = pedido acima de média + 4 desvios-padrão da quantidade de todos os pedidos da loja, em unidades; a planilha nova recalcula o limiar e classifica só as linhas inseridas: distribuição, comparação com o limiar fixo de 2.000 e o treino de produção das 17 séries com fixo × 4 × 3 desvios (§4.1) |
| `docs/prediction/ADR-017-previsao-por-categoria-e-grama.md` | **A previsão do sistema**: SARIMAX direto em cada categoria e produto de grama, por loja; treino pelo botão ou script, sem agendador; histórico congelado; conferência da planilha. O que saiu e a emenda da constituição (v4.0.0) |
| `docs/prediction/07-previsao_14_dias_e_historico.md` | Como o sistema treina, guarda e mostra: ciclo planilha → conferência → treino → telas, receita e walk-forward, previsão de 14 dias, regras do histórico (9 e 20 dias entre treinos), dias faltando na planilha, tabelas e testes |
| `docs/prediction/08-fator_datas_comemorativas.md` | Datas comemorativas no fluxo (sem encomendas): só Flores de corte sobe (1,6–5,8× em Mulher, Mães, Namorados, Natal; Ano Novo em §9.2); a flor de Finados é a em vaso (crisântemo e kalanchoe, em Plantas diversas), só em Itabirito; fator multiplicativo pela metade no SARIMAX de produção corta 40–45% do erro do total da semana de Flores de corte (10 ocorrências), não o erro de cada dia; em Finados não serve (Grama: nível baixo do modelo; Produtos piora; Plantas diversas melhora uma ocorrência e piora a outra). Refeito em 2026-11-05 com a classificação SKU a SKU. §9: EDA de todos os feriados e datas em todas as séries; §9.3: a queda é de 26 a 31/12 (não da temporada) e, na Grama de Itabirito, do Dia do Trabalho, e a queda inteira vence no SARIMAX de produção. Adotado pelo ADR-019 |
| `docs/prediction/ADR-019-fator-das-datas-comemorativas.md` | *Proposto* — previsão de Flores de corte × fator da data na semana do Dia da Mulher, das Mães, dos Namorados, do Natal e do Ano Novo (metade do aumento, entre 1 e 3); nas outras séries, a queda de 26 a 31/12 e do Dia do Trabalho (inteira, piso 0,2, só se caiu nas 2 últimas ocorrências, §2.1). Recalculado das vendas a cada treino (últimas 3 ocorrências), gravado em `event_factor`; desligável por `FORECAST_SERVICE_EVENT_FACTOR` |
| `docs/prediction/09-horizonte_e_frequencia_de_retreino.md` | Horizonte e retreino nas 4 categorias × 2 lojas (d = 0): o erro de cada dia sobe 2–4% até a 4ª semana e fica plano até 16 semanas (d = 0 volta à média do ano); retreino a cada 28/56/91 dias perde 2–3% na média e 15–32% no pior mês (janeiro, novembro); o MASE e a cobertura do walk-forward de produção mudam com h (dependem de quais meses caem na avaliação), no ano as 8 têm MASE < 1 e cobertura em 90–98% até h = 56. Recomendou treino semanal e h = 28; adotado pelo ADR-021 como previsão de 91 dias com horizonte na tela e walk-forward em 14. Script `training_scripts/validation/horizonte_e_retreino_categorias.py` |
| `docs/prediction/10-estacionariedade_e_diferenciacao.md` | Base do d série a série (ADR-020): KPSS, ADF (4 regras de lags), DF-GLS e Phillips-Perron no resíduo da regressão com as exógenas do SARIMAX, em todos os dias, na janela de ajuste (23 séries × 52 treinos). KPSS acerta o lado do walk-forward em 16 de 23 (Spearman −0,48, p = 0,02), o ADF em 8–10 (distorção de Schwert); nenhuma série em que o KPSS rejeita fica melhor com d = 0, mas ele não decide as esparsas. Critério do walk-forward −3,6 a −3,8% × KPSS −2,5%. §3.1: os 2 erros da 1ª versão do teste. Script `training_scripts/validation/estacionariedade_fiel_ao_modelo.py` |
| `docs/prediction/11-janela_de_treino_e_horizonte.md` | Janela de treino (90, 180, 270, 365, 545 dias, histórico inteiro) e horizonte (2 semanas a 3 meses) nas 23 séries, 51 cortes semanais, receita de produção: 90 dias piora; 545 é a melhor janela única (−1,9%), histórico inteiro −2,2% nas categorias; ganho significativo (Holm) em Flores de corte de Itabirito e 3 produtos esparsos de JC; janela escolhida a cada treino −8,8% nos produtos, −1,1% nas categorias. Erro +3% na 4ª semana e +7% no 3º mês (categorias), sem perder da naïve; JC Grama/Plantas/Produtos e Esmeraldas pioram de forma significativa a partir de 4–8 semanas. §6: opções (545 fixo, janela por série, misto); adotado 545 fixo pelo ADR-022. Script `training_scripts/validation/janela_treino_e_horizonte.py`; resultados (não apagar) em `results/metrics/janela_treino_e_horizonte/` |
| `docs/prediction/ADR-020-diferenciacao-por-serie.md` | d de cada série escolhido pelo walk-forward entre 0 e 1 (`FORECAST_SERVICE_D_CANDIDATES`); erro de cada d em `series_models.metrics.selecao_d`; receita do modelo na impressão digital do treino. A 1ª versão (mesmo dia) fixava d por família |
| `docs/prediction/ADR-021-horizonte-de-previsao-selecionavel.md` | O treino prevê 91 dias (`FORECAST_MAX_HORIZON_DAYS`); tela e relatórios mostram de 2 semanas a 3 meses (padrão 2 semanas); walk-forward continua com h = 14 (Princípio III sem emenda); tabela do retreino a cada 1 semana até 3 meses; curva do erro e da faixa com d = 1 (§3.1, `training_scripts/validation/horizonte_d1_categorias.py`) |
| `docs/prediction/ADR-022-janela-de-treino-de-545-dias.md` | Janela de treino de 545 dias em todas as séries (doc 11 §6, opção 1); a regra dos 28 dias com venda do produto de grama continua nos últimos 365 (`FORECAST_SERVICE_MIN_SALE_WINDOW_DAYS`, `ConfigTreino.janela_venda_dias`); horizonte da tela sem mudança; ícone de informação nas 4 gramas pequenas de Jardim Canadá (`GRAMAS_ESPARSAS` em `PrevisaoSarimax.tsx`) |
| `docs/README.md` | Índice da documentação por área + convenção de ADRs |
| `docs/prediction/`, `docs/backend/`, `docs/database/`, `docs/frontend/` | ADRs organizados por área (ver `docs/README.md` para a lista completa) |
| `docs/project/Projeto Tecnico Verde Perto Final...pdf` | Projeto técnico acadêmico original (fonte primária, revisado pelo orientador) |
| `docs/project/current_files_state.md` | Raio-x do que já foi feito (dados, pré-processamento, modelagem) vs. requisitos do artigo |
| `docs/prediction/plano_experimentos_modelagem.md` | Plano de experimentos: L1 baseline × enriquecido × demanda intermitente/outros modelos |
| `docs/prediction/01-pre_processing.md` | O que os scripts de `training_scripts/preprocessing/` fazem e por quê: Etapas 1–3 (parsing, colunas removidas, taxonomia) e 4–7 (base limpa, encomendas, calendário por loja com `loja_fechada`/`abertura_excepcional`, séries diárias por unidade e unidade×categoria). §11 mapeia cada achado do EDA/treinos para a etapa que o resolve |
| `docs/uml/` *(parcial — 2 de 5 diagramas)* | Diagramas de casos de uso, atividades, classes, modelo de dados e arquitetura lógica (seção 6.4 do artigo) |
| `docs/prediction/02-baseline_serie_crua_pre_eda.md` | Primeiro treino (ponto zero): SARIMA puro sobre 1 série diária crua, pré-EDA. Como foi feito, resultados, diagnóstico de por que foi fraco (encomendas, Carnaval, mudança de nível, MASE inflado, IC largo) e o que resolver. Scripts em `training_scripts/baseline/` |
| `docs/prediction/03-enriquecimento_serie_crua.md` | Segundo treino: a mesma série crua com calendário (BrasilAPI + fechamentos locais 15/08 e 08/12) e clima (Open-Meteo). Calendário: erro em feriados ~0, IC 95% 6× mais estreito, −9% de erro no ano. Clima: sem ganho. Diagnóstico: encomendas = 48% do erro restante; janela "7 dias até Mães/Finados" = 12% do erro (usar "loja aberta excepcionalmente no dia"). Scripts em `training_scripts/enriched/`, cache em `data/external/` |
| `docs/prediction/04-treino_l1_por_loja.md` | Terceiro treino: L1 por loja sobre o pré-processamento v2. Melhor versão A1 com d=1 (calendário + acompanha o nível): MASE 0,58 nas 2 lojas, vence a naïve em 24/26 rodadas, IC95 91–94%. Previsão pontual = mediana (fator de Duan descartado). §5 = próximos passos: encomendas como fluxo próprio, dois números (mediana + quantil para estoque), nível, desagregação L2 |
| `docs/prediction/05-dataframe_treino_l1_exemplo.md` | DataFrame real recebido pelo `SARIMAX(z, exog=X, ...)` na seleção de ordem do L1 (uma unidade): só o alvo transformado (`log1p` + teto p99) e 8 dummies de calendário — nenhuma coluna categórica/nominal. CSVs em `training_scripts/results/metrics/l1_dataframe_treino_exemplo_*.csv`, gerados por `training_scripts/baseline/export_dataframe_treino_exemplo.py` |
| `docs/prediction/06-experimento_janela_dias_proximos.md` | Testa se uma exógena "6 dias antes de qualquer data comemorativa" (isolada do dia de `abertura_excepcional`, coeficiente único entre as 6 datas) melhora o L1. Resultado: **não ajuda** (−0,8% / −0,1% no erro relativo à naïve, abaixo do limite de 5%) — confirma empiricamente que o efeito cancela no total da unidade e pertence à L2 (ainda não implementada). Script: `training_scripts/baseline/experimento_janela_dias_proximos.py` |
| `docs/prediction/00-eda_report.md` | Relatório de EDA (T000b) — as 2 séries do L1 por unidade (§3.0, `16_series_l1_unidade.png` a `19_stl_unidade.png`), as 6 séries de desagregação `unidade×categoria` (§3.1–3.9, `10_series_l1_paineis.png` a `15_stl_par_denso.png`), granularidade das categorias (§3.10) e separação unidade/categoria (§3.11); §4 = ajustes de modelagem; §5 = questões para o cliente. Scripts em `training_scripts/eda/` |
| `docs/database/dicionario_dados_fonte.md` | Dicionário campo a campo do relatório "Contas a Receber" (20 colunas, semântica, faixa, etapa de remoção) |
