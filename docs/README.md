# Documentação — Sistema de Previsão de Vendas (Floricultura Verde Perto)

Documentação organizada por área do projeto. Veja também `SPECS.md` (raiz) para a
referência técnica completa e `CLAUDE.md` (raiz) para o guia de desenvolvimento.

| Pasta | Área | Conteúdo |
| --- | --- | --- |
| [`project/`](project/) | Visão geral / acadêmico | Projeto técnico original (PDF) e o raio-x do estado atual do sistema |
| [`prediction/`](prediction/) | Modelagem / previsão de demanda | ADRs sobre SARIMAX, **revisão de escopo mensal→diário ([ADR-009](prediction/ADR-009-granularidade-diaria-e-reposicao.md))**, plano de experimentos comparativos, pipeline de pré-processamento |
| [`backend/`](backend/) | API / arquitetura de serviço | ADRs sobre monolito modular, autenticação JWT, scheduler de retrain |
| [`database/`](database/) | Persistência | ADR sobre a escolha do SQLite + **[dicionário de dados da fonte](database/dicionario_dados_fonte.md)** |
| [`prediction/00-eda_report.md`](prediction/00-eda_report.md) | Análise exploratória | Relatório de EDA (T000b) — base transacional, as 2 séries do L1 (por unidade) e as 6 séries de desagregação (por categoria); achados que ajustam pré-processamento e modelagem |
| [`prediction/02-baseline_serie_crua_pre_eda.md`](prediction/02-baseline_serie_crua_pre_eda.md) | Primeiro treino (linha de base) | SARIMA sobre 1 série diária crua, dados pré-EDA: como foi feito, resultados, por que foi fraco e o que resolver no próximo treino |
| [`prediction/03-enriquecimento_serie_crua.md`](prediction/03-enriquecimento_serie_crua.md) | Segundo treino (enriquecimento) | A mesma série crua com calendário (feriados BrasilAPI + fechamentos locais) e clima (Open-Meteo): o calendário ajuda, o clima não |
| [`prediction/04-treino_l1_por_loja.md`](prediction/04-treino_l1_por_loja.md) | Terceiro treino (L1 por loja) | Achados do EDA + calendário corrigido: MASE 0,58, 24/26 rodadas vencidas, faixa útil; pendências (encomendas, viés) e próximos passos com a solução de cada uma |
| [`frontend/`](frontend/) | Dashboard React | ADR sobre geração do cliente TypeScript a partir do OpenAPI |
| [`uml/`](uml/) | Modelagem UML | Diagramas de casos de uso e atividades (entregável acadêmico, seção 6.4 do artigo) — caminho fixo, referenciado em `SPECS.md`/`tasks.md`, não mover |

## Convenção de ADRs

Cada ADR mora na pasta da área a que pertence (`ADR-00N-titulo.md`), não mais em um
`docs/adr/` único. A numeração sequencial (001, 002, 003...) é preservada — ela reflete
a ordem cronológica das decisões, mesmo estando fisicamente separada por área. Ao criar
uma nova ADR, use o próximo número livre (o maior `ADR-0NN` já usado em qualquer pasta
+ 1) e coloque-a na pasta da área correspondente.

| ADR | Área | Decisão |
| --- | --- | --- |
| [ADR-001](prediction/ADR-001-sarimax_central_model.md) | predição | SARIMAX como modelo central de previsão *(revisado — ADR-009)* |
| [ADR-002](backend/ADR-002-monolito-modular.md) | backend | Monolito modular como padrão arquitetural |
| [ADR-003](backend/ADR-003-jwt-autentication.md) | backend | JWT com perfis admin/viewer |
| [ADR-004](prediction/ADR-004-d0-sarimax-sazonal.md) | predição | D=0 no SARIMAX sazonal *(revisado — ADR-009)* |
| [ADR-005](database/ADR-005-sqlite-vs-postgresql.md) | banco de dados | SQLite como banco de dados |
| [ADR-006](backend/ADR-006-apscheduler-vs-celery.md) | backend | APScheduler in-process vs. Celery |
| [ADR-007](frontend/ADR-007-openapi-typescript-codegen.md) | frontend | openapi-typescript-codegen para o cliente TS |
| [ADR-009](prediction/ADR-009-granularidade-diaria-e-reposicao.md) | predição | Granularidade **diária** e política de reposição perecível (hierárquico L1/L2/L3) — revisa ADR-001 e ADR-004; **L3 revisado por ADR-011** |
| [ADR-010](prediction/ADR-010-exogenas-nominais-fora-do-l1.md) | predição | `pagamento`/`vendedor` fora das exógenas; `empresa` vira chave `unidade`; Etapa 3 removida do pipeline |
| [ADR-011](prediction/ADR-011-escopo-previsao-sem-reposicao.md) | predição | Escopo: **previsão de demanda diária, sem camada de reposição L3**; 2 unidades (Jardim Canadá e Itabirito); L1 por **unidade** (2 séries) — categoria e grupos do cliente via desagregação L2 — revisa ADR-009 |

## Documentos "a criar" com caminho fixo (não mover ao criar)

Estes caminhos são referenciados literalmente em `SPECS.md`, `specs/001-.../tasks.md` e
`specs/001-.../plan.md` como entregáveis — mantenha-os na raiz de `docs/` quando forem
criados, para não quebrar essas referências:

- ~~`docs/eda_report.md`~~ — **criado**, relatório de EDA (Fase 0/T000b), em `docs/prediction/00-eda_report.md`
- `docs/quickstart.md` — guia de instalação/uso para a entidade parceira (T079)
