<!-- Sync Impact Report
  Version change: 1.1.0 → 1.1.1
  Added: Quality Gate de Shapiro-Wilk (diagnóstico de resíduos, alinhado à seção 6.5
    do Projeto Técnico revisado — validação tem 3 dimensões: estatística, diagnóstico
    de resíduos [Ljung-Box + Shapiro-Wilk] e testes funcionais)
  Modified: Development Workflow — referência à metodologia CRISP-DM adotada para o
    pipeline de dados (compreensão do negócio → dados → preparação → modelagem →
    avaliação → implantação), conforme seção 6.1 do artigo
  Templates updated:
    ✅ .specify/templates/spec-template.md (compatible)
    ✅ .specify/templates/plan-template.md (compatible)
    ✅ .specify/templates/tasks-template.md (compatible)
  Follow-up TODOs: none
-->

# Sistema de Previsão de Estoque — Floricultura Constitution

## Core Principles

### I. Domínio Puro (NON-NEGOTIABLE)

A camada de domínio (`backend/domain/`) MUST conter exclusivamente lógica de negócio.
Ela MUST NOT importar FastAPI, SQLAlchemy, APScheduler ou qualquer framework de I/O.
Toda dependência externa MUST ser injetada via interfaces — nunca instanciada no domínio.
**Rationale**: domínio testável de forma isolada, sem infraestrutura; permite trocar banco,
framework ou scheduler sem tocar na lógica de previsão.

### II. Estatística Antes de Machine Learning

O modelo central MUST ser SARIMAX (statsmodels). Modelos de ML (redes neurais, XGBoost)
MUST NOT ser introduzidos sem evidência quantitativa de superioridade sobre SARIMAX no
conjunto de dados disponível (≤ 26 observações mensais por produto).
Ponderação de variáveis exógenas via Random Forest MDI é PERMITIDA como pré-processamento,
não como modelo de previsão.
**Rationale**: M4 Competition demonstra que ARIMA/SARIMA supera ML com N < 50 por sazonalidade.
Introduzir complexidade sem ganho empírico viola o princípio de parcimônia estatística.

### III. Validação Obrigatória Antes de Produção

Todo modelo treinado MUST ser avaliado com walk-forward cross-validation (≥ 4 folds)
antes de ser persistido como `status = "trained"`.
Os limiares de aceitação MUST ser: MAPE < 20% para produtos de alto giro;
SMAPE < 30% para os 2 produtos de maior volume.
Modelos que não atingirem os limiares MUST ter `status = "low_confidence"` e
exibir aviso explícito no dashboard.
**Rationale**: artigo TCC seção 6.5; garantia de qualidade mínima antes de influenciar decisões de compra.

### IV. Interface para Usuário Não Técnico

Toda mensagem exposta ao usuário final (alertas, erros, status de modelos) MUST ser
escrita em português claro, sem jargão técnico (sem "MAPE", "SARIMAX", "p-value").
O equivalente em linguagem de negócio MUST ser fornecido (ex: "Modelo com 92% de acerto").
A UI MUST permitir upload de planilha e visualização de previsões sem treinamento técnico.
**Rationale**: REQ-04 e RNF-01 do artigo; os operadores da floricultura não têm formação técnica.

### V. Rastreabilidade Total

Todo upload de planilha MUST gerar registro em `processing_log` com: nome do arquivo,
hash, data, registros adicionados/pulados/duplicados.
Todo retrain MUST gerar registro em `retrain_history` com: trigger, data de início/fim,
produtos treinados e falhas.
Logs de execução MUST ser consultáveis via API (`GET /api/v1/models/status`).
**Rationale**: RNF-02 do artigo; auditabilidade é requisito de confiabilidade operacional
e rastreabilidade para a entidade parceira.

### VI. Segurança por Padrão (NON-NEGOTIABLE)

Todos os endpoints `/api/v1/*` MUST exigir `Authorization: Bearer <JWT>` válido.
O sistema MUST implementar dois perfis: `admin` (upload, retrain, export) e
`viewer` (forecast, products, alerts, simulation — somente leitura).
A API MUST NOT expor dados pessoais de clientes (`cliente_nome`, `cliente_cod`,
CPF, endereço) em nenhum endpoint — somente dados agregados por produto.
Tokens JWT MUST expirar em 8h; refresh MUST ser suportado.
Senhas MUST ser armazenadas com hash bcrypt — nunca em texto plano.
**Rationale**: RNF-04 do artigo (LGPD e controle de acesso por perfil); proteção dos
dados operacionais da empresa parceira; evitar acesso não autorizado ao sistema de compras.

## Quality Gates

### Critérios de Aceitação de Modelos

| Métrica | Limiar | Ação se falhar |
| --- | --- | --- |
| MAPE (alto giro) | < 20% | `status = "low_confidence"` + alerta no dashboard |
| SMAPE (top 2 produtos) | < 30% | idem |
| Ljung-Box p-value | > 0.05 | log de aviso; não bloqueia deploy |
| Shapiro-Wilk p-value | > 0.05 | log de aviso; não bloqueia deploy |
| Observações mínimas | ≥ 15 mensais | `status = "insufficient_data"` |

### Critérios de Aceitação da API

- Todos os endpoints MUST retornar em < 2s para dados de até 50 produtos.
- Upload de XLSX ≤ 50 MB MUST processar em < 30s.
- Retrain semanal MUST concluir em < 2h (RNF-03).

### Critérios de Aceitação da Interface

- Usuário MUST conseguir fazer upload e visualizar previsão em ≤ 3 cliques.
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

**Version**: 1.1.1 | **Ratified**: 2026-07-28 | **Last Amended**: 2026-08-21
