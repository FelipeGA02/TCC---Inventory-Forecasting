<!-- Sync Impact Report
  Version change: 3.1.0 → 4.0.0
  Motivação: a classificação `low_confidence` sai do sistema (pedido do usuário em
    2026-11-09; a tela já não mostrava selo nem aviso desde 2026-11-05). O walk-forward
    continua obrigatório e as métricas continuam registradas em cada série, mas não
    classificam a série: toda série que ajusta tem previsão (`status = "trained"`);
    `insufficient_data` e `error` continuam.
  MAJOR porque redefine o Princípio III (os limiares deixam de decidir o status e de exigir
    aviso no dashboard) e a coluna "Ação se falhar" dos Quality Gates.
  Modified:
    - Princípio III — "avaliado ... antes de ser persistido como `status = "trained"`" +
      "Limiares de aceitação" + "`status = "low_confidence"` e exibir aviso" → walk-forward
      antes de gravar a previsão; MASE, cobertura e simulação como métricas de referência
      registradas em cada série, sem classificar nem gerar aviso.
    - Quality Gates / Critérios de Aceitação de Modelos — MASE, cobertura e simulação:
      "`status = "low_confidence"` + alerta no dashboard" → "registrado nas métricas da
      série; não classifica nem gera aviso".
  Added sections: nenhuma. Removed sections: nenhuma.
  Templates:
    ✅ .specify/templates/spec-template.md (sem referência ao status)
    ✅ .specify/templates/plan-template.md (sem referência ao status)
    ✅ .specify/templates/tasks-template.md (sem referência ao status)
    ✅ CLAUDE.md, SPECS.md, specs/001-sistema-previsao-vendas/{spec,plan}.md, docs/
       (atualizados na mesma mudança)
  Follow-up TODOs (anteriores, não tratados aqui):
    - Princípio II: categoria por SARIMAX direto em vez de desagregação (ADR-016/017).
    - Simulação de reposição nos Quality Gates: L3 fora de escopo (ADR-011).
    - Princípio V: `retrain_history`/`forecast_runs` → `forecast_jobs` (ADR-017).
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
dia-da-semana do nível — não por um SARIMAX próprio: o teste de separação de
`training_scripts/eda/eda_separacao.py` (EDA 4) não mostrou redução de erro em modelar
`categoria` direto.

> **⚠️ Princípio sob contestação empírica — requer emenda via `/speckit-constitution`.**
> O experimento `disaggregation/categoria_direta_vs_desagregacao.py` (351 origens dia a
> dia, h=14, 4 categorias, fluxo diário — protocolo muito mais forte que o da EDA 4)
> mostra o SARIMAX **direto** na categoria vencendo a desagregação em **7 dos 8** pares
> categoria-unidade, com destaque em Flores de corte (erro relativo à naïve 0,733 vs
> 0,830 em Itabirito; 0,723 vs 0,878 em Jardim Canadá, onde a faixa de 95% da
> desagregação cobre só 60,3% do realizado). Ver ADR-016. Enquanto a emenda não for
> votada, este parágrafo continua valendo como norma.

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

Todo modelo treinado MUST ser avaliado com walk-forward cross-validation (≥ 4 folds,
origem móvel, horizonte de 14 dias) antes de a previsão ser gravada.

Métricas de referência, MUST ser registradas em cada série (`series_models.metrics`) e no
log do treino:

- **MASE** (referência: < 1.0, o modelo bate a previsão ingênua sazonal semanal);
- **cobertura empírica do intervalo de 95%** (referência: [90%, 98%]);
- a **simulação de reposição** (perda por perecibilidade + ruptura) sobre o hold-out,
  contra a regra ingênua "repor a média dos últimos 7 dias".

As métricas MUST NOT classificar a série nem gerar aviso no dashboard: toda série que
ajusta tem previsão (`status = "trained"`). Série sem histórico suficiente fica
`insufficient_data` e série cujo ajuste falha fica `error`, ambas sem previsão. MAPE e
SMAPE continuam sendo calculados e reportados, mas são **informativos** (instáveis com
contagem baixa).
**Rationale**: artigo TCC seção 6.5; o walk-forward mede a qualidade antes de a previsão
influenciar decisões de compra, e as métricas ficam disponíveis (tela de histórico, API,
log) sem um rótulo que a loja não usa para decidir.

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
| MASE (L1 e SKU) | < 1.0 | registrado nas métricas da série; não classifica nem gera aviso |
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

**Version**: 4.0.0 | **Ratified**: 2026-07-28 | **Last Amended**: 2026-11-09
