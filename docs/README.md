# Documentação — Sistema de Previsão de Estoque (Floricultura Verde Perto)

Documentação organizada por área do projeto. Veja também `SPECS.md` (raiz) para a
referência técnica completa e `CLAUDE.md` (raiz) para o guia de desenvolvimento.

| Pasta | Área | Conteúdo |
| --- | --- | --- |
| [`projeto/`](projeto/) | Visão geral / acadêmico | Projeto técnico original (PDF) e o raio-x do estado atual do sistema |
| [`predicao/`](predicao/) | Modelagem / previsão de demanda | ADRs sobre SARIMAX, plano de experimentos comparativos (baseline × enriquecido × outros modelos) |
| [`backend/`](backend/) | API / arquitetura de serviço | ADRs sobre monolito modular, autenticação JWT, scheduler de retrain |
| [`banco-de-dados/`](banco-de-dados/) | Persistência | ADR sobre a escolha do SQLite |
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
| [ADR-001](predicao/ADR-001-sarimax-como-modelo-central.md) | predição | SARIMAX como modelo central de previsão |
| [ADR-002](backend/ADR-002-monolito-modular.md) | backend | Monolito modular como padrão arquitetural |
| [ADR-003](backend/ADR-003-jwt-autenticacao.md) | backend | JWT com perfis admin/viewer |
| [ADR-004](predicao/ADR-004-d0-sarimax-sazonal.md) | predição | D=0 no SARIMAX sazonal |
| [ADR-005](banco-de-dados/ADR-005-sqlite-vs-postgresql.md) | banco de dados | SQLite como banco de dados |
| [ADR-006](backend/ADR-006-apscheduler-vs-celery.md) | backend | APScheduler in-process vs. Celery |
| [ADR-007](frontend/ADR-007-openapi-typescript-codegen.md) | frontend | openapi-typescript-codegen para o cliente TS |

## Documentos "a criar" com caminho fixo (não mover ao criar)

Estes caminhos são referenciados literalmente em `SPECS.md`, `specs/001-.../tasks.md` e
`specs/001-.../plan.md` como entregáveis — mantenha-os na raiz de `docs/` quando forem
criados, para não quebrar essas referências:

- `docs/eda_report.md` — relatório de análise exploratória (Fase 0/T000b)
- `docs/quickstart.md` — guia de instalação/uso para a entidade parceira (T079)
