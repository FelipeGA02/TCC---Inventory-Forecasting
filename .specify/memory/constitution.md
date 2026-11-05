<!-- Sync Impact Report
  Version change: 3.1.0 → 4.0.0
  Motivação: alinhar a constituição ao sistema que roda desde o ADR-017 (2026-10-26) e às
    decisões seguintes (ADR-018, ADR-019, retirada do selo de confiança em 2026-11-05). As
    pendências estavam listadas no CLAUDE.md ("emenda pendente").
  MAJOR porque redefine os Princípios II, III e V e remove um Quality Gate (simulação de
    reposição).
  Modified:
    - Princípio II — "L1 por unidade + desagregação em cascata (unidade → categoria → SKU)" →
      SARIMAX direto em cada uma das 4 categorias e em cada produto de grama, por loja
      (ADR-016: categoria direta vence a desagregação em 7 de 8 pares; ADR-017). Ajuste
      pós-modelo das datas comemorativas (ADR-019) permitido como estatística, não ML.
    - Princípio III — walk-forward com o protocolo do sistema (56 origens andando 1 dia,
      h = 14, janela deslizante de 365 dias); sem a simulação de reposição (L3 fora,
      ADR-011); `low_confidence` não exibe selo nem aviso no dashboard (status no log, no
      serviço de previsão e na API); o fator das datas é validado em experimento próprio
      (doc 08), fora do walk-forward do treino.
    - Princípio IV — exemplos sem reposição; status sem rótulo de confiança.
    - Princípio V — `retrain_history`/`forecast_runs` → `processing_log`, `forecast_jobs`,
      `forecast_job_logs`, `series_models`, `forecast_history`; treino sem dados novos =
      `skipped`; logs pela API `/api/v1/servico-previsao/*`.
    - Princípio VI — perfis com as rotas atuais (admin: upload e treino; viewer: contexto,
      painel, histórico, análises, registros).
  Removed:
    - Quality Gate "Simulação de reposição (perda + ruptura)".
    - Critério "Geração da previsão < 15min" (a previsão sai do próprio treino).
  Templates:
    ✅ .specify/templates/plan-template.md (genérico: gates lidos desta constituição)
    ✅ .specify/templates/spec-template.md (genérico, sem referência a princípio)
    ✅ .specify/templates/tasks-template.md (genérico)
    ✅ .claude/skills/speckit-*/SKILL.md (sem nome de princípio desatualizado)
    ✅ CLAUDE.md (Regras Invioláveis sem "emenda pendente"; v4.0.0)
    ✅ docs/prediction/ADR-016, ADR-017, ADR-019 (pendência da emenda resolvida)
  Follow-up TODOs:
    - SPECS.md e specs/001-sistema-previsao-vendas/{spec,plan,tasks}.md ainda descrevem
      o desenho antigo (L1/L2/L3, constituição v2.0.0): registro histórico, a reescrever
      numa revisão das specs (/speckit-specify ou /speckit-plan).
-->

# Sistema de Previsão de Vendas — Floricultura Constitution

## Core Principles

### I. Domínio Puro (NON-NEGOTIABLE)

A camada de domínio (`backend/domain/`) MUST conter exclusivamente lógica de negócio.
Ela MUST NOT importar FastAPI, SQLAlchemy, APScheduler ou qualquer framework de I/O.
Toda dependência externa MUST ser injetada via interfaces — nunca instanciada no domínio.
**Rationale**: domínio testável de forma isolada, sem infraestrutura; permite trocar banco,
framework ou forma de disparo do treino sem tocar na lógica de previsão.

### II. Estatística Antes de Machine Learning

O modelo do sistema MUST ser SARIMAX (statsmodels) com sazonalidade semanal (`m = 7`) e
exógenas de calendário (dia da semana, loja fechada, abertura excepcional), ajustado
**direto em cada série**: cada uma das 4 categorias e cada produto de grama, em cada loja
(ADR-017). O total da loja MUST ser a soma das categorias.

A categoria MUST NOT ser obtida por desagregação de uma série da loja: o experimento
`disaggregation/categoria_direta_vs_desagregacao.py` (351 origens dia a dia, h = 14, fluxo
diário) mostrou o SARIMAX direto na categoria vencendo a desagregação em 7 dos 8 pares
categoria-loja (ADR-016). Produto fora da categoria Grama MUST NOT ganhar modelo próprio
sem novo experimento.

São PERMITIDOS, como estatística e não como ML:
- ajuste multiplicativo pós-modelo das datas comemorativas (ADR-019), com o fator
  recalculado das vendas a cada treino, só com venda anterior ao primeiro dia previsto;
- modelos de demanda intermitente (Croston, TSB, SBA) na trilha de comparação por SKU,
  onde a série diária é quase toda zero;
- ponderação de exógenas por Random Forest MDI como diagnóstico, não como previsão.

Modelos de ML (redes neurais, gradient boosting) MUST NOT entrar no sistema sem evidência
quantitativa de superioridade sobre o SARIMAX vigente, avaliada com o mesmo protocolo de
walk-forward.
**Rationale**: a M4/M5 Competition mostra que métodos estatísticos superam ML em séries
curtas e esparsas de varejo; a evidência do próprio projeto (ADR-016) decide o grão.

### III. Validação Obrigatória Antes de Produção

Toda série treinada MUST ser avaliada com walk-forward de origem móvel antes de receber
`status = "trained"`: no sistema, 56 origens andando 1 dia (≥ 4 folds), horizonte de 14
dias, janela deslizante de 365 dias, ordem escolhida só com a janela anterior à primeira
origem. Todo parâmetro estimado dos dados (fator das datas, limiar de encomenda) MUST usar
só a venda anterior a cada origem.

Limiares de aceitação:

- **MASE < 1.0** (a série MUST bater a previsão ingênua sazonal semanal);
- **cobertura empírica do intervalo de 95%** MUST ficar em [90%, 98%].

Série que não atingir os limiares MUST ficar com `status = "low_confidence"`: a previsão é
gerada e a tela a mostra do mesmo jeito, **sem selo nem aviso de confiança**; o status MUST
ficar registrado no log do treino, no serviço de previsão e na API. MAPE e SMAPE são
calculados e reportados como **informativos** (instáveis com contagem baixa) — não
classificam.

Ajuste que o walk-forward do treino quase nunca atravessa (as datas comemorativas,
ADR-019: as 56 origens cobrem só as 8 semanas antes da última venda) MUST ser validado em
experimento próprio, com a receita de produção, com e sem o ajuste, nas ocorrências
passadas da data (doc 08), e revisto quando entrar um ano novo de vendas.
**Rationale**: artigo TCC seção 6.5; qualidade mínima medida contra a naïve antes de
informar a compra de produto perecível. A loja decide a compra (ADR-011): o sistema
informa quanto deve vender, e a simulação de perda e ruptura saiu com a reposição.

### IV. Interface para Usuário Não Técnico

Toda mensagem exposta ao usuário final (avisos, erros, situação das previsões) MUST ser
escrita em português claro, sem jargão técnico (sem "MASE", "SARIMAX", "p-value").
O equivalente em linguagem de negócio MUST ser fornecido (ex.: "Intervalo acertou 94% dos
dias no teste", "previsão de 26/12 a 31/12 reduzida a 35% pelo Ano Novo").
A UI MUST permitir enviar a planilha, treinar e ver a previsão sem treinamento técnico.
**Rationale**: REQ-04 e RNF-01 do artigo; os operadores da floricultura não têm formação técnica.

### V. Rastreabilidade Total

Todo upload de planilha MUST gerar registro em `processing_log` com: nome do arquivo,
SHA-256, data, linhas lidas/novas/duplicadas e a qualidade (período, dias de loja aberta
sem venda, limiar de encomenda grande).
Todo treino MUST gerar registro em `forecast_jobs` com: origem do disparo, início/fim,
status, impressão digital dos dados, último dia com venda, a configuração com a versão do
código e as contagens de séries por status; e ligar a si as planilhas que entraram nele
(`processing_log.forecast_job_id`).
Treino sem dados novos (vendas, calendário e catálogo iguais ao último concluído) MUST
ficar com `status = "skipped"`.
Cada série MUST ter o seu resultado em `series_models` (status, ordem, métricas,
diagnóstico dos resíduos, coeficientes, ajustes das datas) e uma linha no log do treino
(`forecast_job_logs`). A previsão que a loja viu MUST ficar congelada em `forecast_history`.
Os logs MUST ser consultáveis via API (`/api/v1/servico-previsao/*`).
**Rationale**: RNF-02 do artigo; auditabilidade é requisito de confiabilidade operacional
e rastreabilidade para a entidade parceira.

### VI. Segurança por Padrão (NON-NEGOTIABLE)

Todos os endpoints `/api/v1/*` MUST exigir `Authorization: Bearer <JWT>` válido.
O sistema MUST implementar dois perfis: `admin` (envio de planilha e treino da previsão) e
`viewer` (contexto, painel, histórico da previsão, análises e registros — somente leitura).
A API MUST NOT expor dados pessoais de clientes (`cliente_nome`, `cliente_cod`,
CPF, endereço) em nenhum endpoint — somente dados agregados por produto/categoria.
Tokens JWT MUST expirar em 8h; refresh MUST ser suportado e o logout MUST revogar o
refresh token.
Senhas MUST ser armazenadas com hash bcrypt — nunca em texto plano.
**Rationale**: RNF-04 do artigo (LGPD e controle de acesso por perfil); proteção dos
dados operacionais da empresa parceira.

## Quality Gates

### Critérios de Aceitação de Modelos

| Métrica | Limiar | Ação se falhar |
| --- | --- | --- |
| MASE (categoria e produto de grama) | < 1.0 | `status = "low_confidence"` (previsão gerada, sem aviso na tela) |
| Cobertura do IC 95% | ∈ [90%, 98%] | idem |
| Ljung-Box p-value (resíduos do ajuste final) | > 0.05 | citado no log; não bloqueia |
| Shapiro-Wilk p-value (resíduos do ajuste final) | > 0.05 | citado no log; não bloqueia |
| Histórico antes da 1ª origem do walk-forward | ≥ 180 dias | `status = "insufficient_data"` (sem previsão) |
| Produto de grama: dias com venda na última janela de 365 | ≥ 28 | `status = "insufficient_data"` (sem previsão) |
| Ajuste das datas comemorativas (ADR-019) | reduz o erro do total da semana no experimento do doc 08 | a data sai da lista na revisão anual |

### Critérios de Aceitação da API

- Todos os endpoints de leitura MUST retornar em < 2s para os dados das 2 lojas.
- Upload de XLSX ≤ 50 MB MUST processar em < 30s.
- O treino da previsão (todas as séries) MUST concluir em < 2h (RNF-03).

### Critérios de Aceitação da Interface

- Usuário MUST conseguir enviar a planilha e ver a previsão em ≤ 3 cliques.
- Exportação PDF/Excel MUST ser gerada em < 10s.

## Development Workflow

- O pipeline de dados e modelagem MUST seguir as fases do CRISP-DM (Cross-Industry
  Standard Process for Data Mining), adaptado a séries temporais: compreensão do
  negócio, compreensão dos dados, preparação dos dados, modelagem, avaliação e
  implantação (artigo, seção 6.1).
- Toda decisão de modelagem MUST vir de experimento com o protocolo do Princípio III,
  reportando o erro relativo à naïve na mesma janela (não só o MASE), e ficar registrada
  num ADR em `docs/`.
- Nenhuma funcionalidade de domínio MUST ser implementada sem teste unitário correspondente.
- Pull Requests que incluam lógica de negócio sem teste unitário MUST ser rejeitados.
- Mudanças nos contratos de API (schemas Pydantic) MUST ser refletidas em `openapi.yaml`.
- Após qualquer mudança em `openapi.yaml`, `openapi-typescript-codegen` MUST ser re-executado
  para regenerar o cliente TypeScript em `app-react/src/services/api/`.
- O `CLAUDE.md` e os ADRs vigentes descrevem o sistema atual; `SPECS.md` e
  `specs/001-*` guardam o desenho original. Conflitos MUST ser resolvidos por esta
  constituição e, entre documentos, pelo ADR mais recente.

## Governance

Esta constituição MUST ser consultada antes de qualquer decisão arquitetural.
Emendas MUST ser documentadas com: motivação, impacto nos princípios existentes e
migração do código afetado.
Versionamento semântico: MAJOR = remoção/redefinição de princípio; MINOR = novo princípio
ou exigência ampliada; PATCH = clarificação ou correção de texto.
Revisão obrigatória a cada Sprint concluído.

**Version**: 4.0.0 | **Ratified**: 2026-07-28 | **Last Amended**: 2026-11-05
