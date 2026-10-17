<!-- Sync Impact Report
  Version change: 3.0.0 → 3.1.0
  Motivação: a previsão deixa de ser regerada todo dia. Com o mesmo modelo e os mesmos
    dados, regerar a previsão todo dia repete os mesmos números. Cada treino (ou mudança
    em `calendar_days` depois dele, conferida às 03:00) gera uma vez a previsão de
    FORECAST_STORED_DAYS (60) dias a partir do último dia com venda, gravada em
    `forecast_runs` + `forecasts_cache`; a API entrega os 14 dias a partir de hoje. O
    treino agendado de segunda é pulado (`skipped`) sem venda nova e com a mesma config.
  MINOR porque amplia uma exigência do Princípio V (treino pulado registrado) e
    redefine o gatilho da geração, sem remover nem renomear princípio.
  Modified:
    - Princípio V — "geração diária de previsão/reposição MUST registrar data e contagem
      de SKUs" → toda geração da previsão MUST registrar em `forecast_runs` data, período
      previsto e contagem de SKUs atendidos; treino pulado MUST ficar como `skipped` em
      `retrain_history`.
    - Critérios de Aceitação da API — "Geração diária de previsão + reposição < 15min" →
      "Geração da previsão < 15min".
  Templates updated:
    ✅ .specify/templates/spec-template.md (compatible — sem referência à geração diária)
    ✅ .specify/templates/plan-template.md (compatible)
    ✅ .specify/templates/tasks-template.md (compatible)
    ✅ CLAUDE.md (regra 5 e agendamento já descrevem o novo comportamento)
  Follow-up TODOs:
    - Propagar a SPECS.md e specs/001-sistema-previsao-vendas/{spec,plan,tasks}.md.
    - Pendência anterior (v3.0.0): simulação de reposição nos Quality Gates (ADR-011).
-->

# Sistema de Previsão de Vendas — Floricultura Constitution

## Core Principles

### I. Domínio Puro (NON-NEGOTIABLE)

A camada de domínio (`backend/domain/`) MUST conter exclusivamente lógica de negócio.
Ela MUST NOT importar FastAPI, SQLAlchemy, APScheduler ou qualquer framework de I/O.
Toda dependência externa MUST ser injetada via interfaces — nunca instanciada no domínio.
**Rationale**: domínio testável de forma isolada, sem infraestrutura; permite trocar banco,
framework ou scheduler sem tocar na lógica de previsão.

### II. Estatística Antes de Machine Learning

O modelo central da **camada de demanda agregada (L1)** — uma série diária por
`unidade` — MUST ser SARIMAX (statsmodels), com sazonalidade semanal (`m=7`) e exógenas
de calendário.

`categoria` e SKU MUST ser obtidos por **desagregação proporcional em cascata**
(`unidade` → `categoria` → SKU), cada passo pela participação móvel × perfil de
dia-da-semana do nível — não por um SARIMAX próprio: o teste de separação (ADR-011 §4)
não mostrou redução de erro em modelar `categoria` direto.

Para a **camada de SKU** especificamente, onde a série diária individual é
majoritariamente composta de zeros e o SARIMAX é matematicamente inaplicável, também são
PERMITIDOS modelos de **demanda intermitente** (Croston, TSB, SBA) como trilha de
comparação formal contra a abordagem hierárquica.

Modelos de ML (redes neurais, gradient boosting) MUST NOT ser introduzidos em nenhuma
camada sem evidência quantitativa de superioridade sobre a abordagem vigente no conjunto
de dados disponível, avaliada com o mesmo protocolo de walk-forward CV.
Ponderação de variáveis exógenas via Random Forest MDI é PERMITIDA como pré-processamento,
não como modelo de previsão.
**Rationale**: a M4/M5 Competition mostra que métodos estatísticos e de demanda
intermitente superam ML em séries curtas e esparsas de varejo. SARIMAX governa o sinal
agregado (denso); Croston/TSB governam o padrão esparso por item. Introduzir ML sem
ganho empírico viola a parcimônia estatística.

### III. Validação Obrigatória Antes de Produção

Todo modelo L1 treinado MUST ser avaliado com walk-forward cross-validation (≥ 4 folds,
origem móvel, horizonte de 14 dias) antes de ser persistido como `status = "trained"`.

Limiares de aceitação:

- **MASE < 1.0** (o modelo MUST bater a previsão ingênua sazonal semanal), medido em L1 e
  no nível de SKU após desagregação;
- **cobertura empírica do intervalo de 95%** MUST ficar em [90%, 98%];
- a **simulação de reposição** (perda por perecibilidade + ruptura) sobre o hold-out MUST
  ser melhor que a regra ingênua "repor a média dos últimos 7 dias".

Modelos que não atingirem os limiares MUST ter `status = "low_confidence"` e exibir aviso
explícito no dashboard. MAPE e SMAPE continuam sendo calculados e reportados, mas são
**informativos** (instáveis com contagem baixa) — não bloqueiam nem classificam.
**Rationale**: artigo TCC seção 6.5; garantia de qualidade mínima antes de influenciar
decisões de compra de produto perecível.

### IV. Interface para Usuário Não Técnico

Toda mensagem exposta ao usuário final (alertas, erros, status de modelos) MUST ser
escrita em português claro, sem jargão técnico (sem "MASE", "SARIMAX", "p-value").
O equivalente em linguagem de negócio MUST ser fornecido (ex: "Precisão estimada: 92%",
"Repor 40 unidades até quinta — o restante murcha antes de vender").
A UI MUST permitir upload de planilha e visualização de previsões/reposição sem
treinamento técnico.
**Rationale**: REQ-04 e RNF-01 do artigo; os operadores da floricultura não têm formação técnica.

### V. Rastreabilidade Total

Todo upload de planilha MUST gerar registro em `processing_log` com: nome do arquivo,
hash, data, registros adicionados/pulados/duplicados.
Todo retrain (ajuste semanal dos modelos L1) MUST gerar registro em `retrain_history`
com: trigger, data de início/fim, categorias treinadas e falhas.
Treino agendado pulado por falta de venda nova MUST ficar registrado em `retrain_history`
com `status = "skipped"`.
Toda geração da previsão (ao fim de um treino ou após mudança no calendário) MUST
registrar em `forecast_runs` data, período previsto e contagem de SKUs atendidos.
Logs de execução MUST ser consultáveis via API (`GET /api/v1/models/status`).
**Rationale**: RNF-02 do artigo; auditabilidade é requisito de confiabilidade operacional
e rastreabilidade para a entidade parceira.

### VI. Segurança por Padrão (NON-NEGOTIABLE)

Todos os endpoints `/api/v1/*` MUST exigir `Authorization: Bearer <JWT>` válido.
O sistema MUST implementar dois perfis: `admin` (upload, retrain, export) e
`viewer` (forecast, replenishment, products, alerts, simulation — somente leitura).
A API MUST NOT expor dados pessoais de clientes (`cliente_nome`, `cliente_cod`,
CPF, endereço) em nenhum endpoint — somente dados agregados por produto/categoria.
Tokens JWT MUST expirar em 8h; refresh MUST ser suportado.
Senhas MUST ser armazenadas com hash bcrypt — nunca em texto plano.
**Rationale**: RNF-04 do artigo (LGPD e controle de acesso por perfil); proteção dos
dados operacionais da empresa parceira; evitar acesso não autorizado ao sistema de compras.

## Quality Gates

### Critérios de Aceitação de Modelos

| Métrica | Limiar | Ação se falhar |
| --- | --- | --- |
| MASE (L1 e SKU) | < 1.0 | `status = "low_confidence"` + alerta no dashboard |
| Cobertura do IC 95% | ∈ [90%, 98%] | idem |
| Simulação de reposição (perda + ruptura) | melhor que regra ingênua de 7 dias | idem |
| Ljung-Box p-value (resíduos L1) | > 0.05 | log de aviso; não bloqueia deploy |
| Shapiro-Wilk p-value (resíduos L1) | > 0.05 | log de aviso; não bloqueia deploy |
| Observações mínimas L1 (`unidade`) | ≥ 180 dias | `status = "insufficient_data"` |
| Observações mínimas SKU | ≥ 28 dias com venda ou ≥ 8 vendas | SKU cai no fallback de rateio da categoria |

### Critérios de Aceitação da API

- Todos os endpoints MUST retornar em < 2s para dados de até 50 produtos.
- Upload de XLSX ≤ 50 MB MUST processar em < 30s.
- Ajuste semanal dos modelos L1 MUST concluir em < 2h (RNF-03).
- Geração da previsão MUST concluir em < 15min.

### Critérios de Aceitação da Interface

- Usuário MUST conseguir fazer upload e visualizar previsão/reposição em ≤ 3 cliques.
- Exportação PDF/Excel MUST ser gerada em < 10s.

## Development Workflow

- O pipeline de dados e modelagem MUST seguir as fases do CRISP-DM (Cross-Industry
  Standard Process for Data Mining), adaptado a séries temporais: compreensão do
  negócio, compreensão dos dados, preparação dos dados, modelagem, avaliação e
  implantação (artigo, seção 6.1).
- Implementação MUST seguir a ordem dos Sprints definida em `SPECS.md`.
- Nenhuma funcionalidade de domínio MUST ser implementada sem teste unitário correspondente.
- Pull Requests que incluam lógica de negócio sem teste unitário MUST ser rejeitados.
- Mudanças nos contratos de API (schemas Pydantic) MUST ser refletidas em `openapi.yaml`.
- Após qualquer mudança em `openapi.yaml`, `openapi-typescript-codegen` MUST ser re-executado
  para regenerar o cliente TypeScript em `app-react/src/services/api/`.
- O arquivo `SPECS.md` é o documento de referência primário; esta constituição governa os
  princípios; conflitos MUST ser resolvidos pelo princípio mais restritivo.

## Governance

Esta constituição MUST ser consultada antes de qualquer decisão arquitetural.
Emendas MUST ser documentadas com: motivação, impacto nos princípios existentes e
migração do código afetado.
Versionamento semântico: MAJOR = remoção/redefinição de princípio; MINOR = novo princípio;
PATCH = clarificação ou correção de texto.
Revisão obrigatória a cada Sprint concluído.

**Version**: 3.1.0 | **Ratified**: 2026-07-28 | **Last Amended**: 2026-10-17
