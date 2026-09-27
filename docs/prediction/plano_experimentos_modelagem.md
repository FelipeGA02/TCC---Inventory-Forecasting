# Plano de Ação — Experimentação Comparativa de Modelos de Previsão

**Objetivo**: produzir evidência empírica, conforme exige o Princípio II da constituição
("Estatística Antes de Machine Learning") e o ADR-001, comparando, **em granularidade
diária** (ver [ADR-009](ADR-009-granularidade-diaria-e-reposicao.md)):

1. **L1 SARIMAX sem enriquecimento** — série diária por `unidade` (2 séries), só com
   exógenas de calendário derivadas dos próprios dados (dia-da-semana);
2. **L1 SARIMAX enriquecido** — mais feriados precisos, clima e datas comemorativas;
3. **Demanda intermitente por SKU** (Croston, TSB, SBA) contra a abordagem hierárquica
   (L1 SARIMAX por unidade + L2 desagregação em cascata unidade→categoria→SKU), usando
   os mesmos protocolos de validação;
4. **Redes neurais / outros modelos** (modelo global), como teto de comparação.

**Onde isso roda**: em `ia-predictor/training_scripts/`, não em `backend/domain/`. É uma
pasta de scripts Python dedicada a testar, treinar e validar antes de qualquer variante
entrar no backend de produção. Os módulos `backend/domain/` hoje são stubs; prototipa-se
tudo em `training_scripts/`, decide-se o vencedor com números, e só então se implementa
uma vez em `backend/domain/` (Fase 4/5 do `tasks.md`).

Subpastas, uma por etapa da comparação:

| Subpasta | Fase | Conteúdo |
| --- | --- | --- |
| `eda/` | 1.1 | Sazonalidade **semanal** e anual, tendência por unidade, **esparsidade da série diária por SKU** (justifica L2), seleção do Top-N |
| `baseline/` | 1 | **L1** — Modelo A0 (SARIMA puro diário) e A1 (SARIMAX + exógenas de calendário) por `unidade` |
| `enriched/` | 3 | **L1** Modelo B (SARIMAX + exógenas externas: clima, feriados municipais, datas comemorativas) |
| `replenishment/` | 3–4 | **L2** desagregação em cascata unidade→categoria→SKU + **L3** política de reposição; simulação de perda/ruptura |
| `alternative_models/` | 4 | Croston/TSB/SBA por SKU; ETS/Holt-Winters; XGBoost; rede neural global |
| `validation/` | 1, 3, 4 | Walk-forward CV (origem móvel, horizonte 14 dias), MASE/RMSSE, cobertura do IC, testes de resíduos (Ljung-Box, Shapiro-Wilk) e de significância (Diebold-Mariano/Wilcoxon) — compartilhado entre fases |
| `results/` | todas | `metrics/*.csv` e `plots/` — staging; só o pipeline vencedor migra para `ia-predictor/results/` (produção) na Fase 5 |

---

## Fase 1 — Baseline L1 sem enriquecimento

**Dados**: só `data/processed/contas_a_receber.csv` (transacional interno).

- [x] 1.0 **Modelo A0-crua: ponto zero, antes do EDA** (`training_scripts/baseline/sarimax_serie_crua.py`,
      2026-09-27). SARIMA puro sobre **1 série** diária total (todas as lojas e categorias)
      da base de 2026-08-30, sem separar encomendas e sem exógenas. Ganho de só ~17–18% sobre
      a naïve na mesma janela (vence em 2 de 4 folds); dezembro/2025 previsto em 34%; IC 95%
      de ~80 mil. Serve de referência para medir o ganho do EDA (A0), do calendário (A1) e do
      enriquecimento (B) → [02-baseline_serie_crua_pre_eda.md](02-baseline_serie_crua_pre_eda.md)
- [x] 1.0b **A1-crua e B-crua: enriquecimento sobre a mesma série crua**
      (`training_scripts/enriched/sarimax_serie_crua_enriquecida.py`, 2026-09-27). O calendário
      (BrasilAPI + fechamentos locais) zera o erro em feriados, estreita o IC 95% de ~79 para
      ~13 mil e, num ano de 26 rodadas, reduz o erro em 9% (vence a naïve em 22/26, contra
      19/26). O clima (Open-Meteo, observado) não traz ganho. Dezembro segue em 35% previsto
      (encomendas), e o A1 superestima fases de baixa (fev/2026 +23%) →
      [03-enriquecimento_serie_crua.md](03-enriquecimento_serie_crua.md)
- [x] 1.1 EDA (`tasks.md` T000b, em `training_scripts/eda/`): sazonalidade semanal/anual,
      tendência, **% de zeros da série diária por SKU** (prova de que o SKU não pode ser
      modelado sozinho), perfil de demanda por categoria, seleção do Top-N →
      `docs/prediction/00-eda_report.md`
- [ ] 1.1b **Taxonomia** (Etapa 3 — `map_taxonomy.py` + `taxonomy/{unidades,categorias}.py`,
      ver [01-pre_processing.md](01-pre_processing.md) §5): o script e as tabelas de/para de
      trabalho já existem (rodada 2026-08-30: 27 pares `unidade × categoria`, 9,6% em
      "Outros"). Falta **refinar** as regras de `categoria` inspecionando os nomes que
      caem em "Outros", curar o `CATEGORIA_POR_SKU` do Top-N, e validar com a parceira o
      mapa `empresa → unidade` e o `shelf_life_dias` real
- [ ] 1.2 `prepare_daily_series()` (`training_scripts/baseline/`): a partir do CSV com
      taxonomia — série **diária** somada por `unidade` (alvo do L1) e por
      `unidade × categoria` (perfil de desagregação), freq='D', reindex completo
      (dias sem venda = 0), ≥ 180 dias
- [ ] 1.3 `build_calendar_exogenous()`: dummies/Fourier de dia-da-semana; flag de feriado
      nacional; véspera de feriado; **Carnaval (seg/ter) explícito**. É ponto facultativo,
      não feriado nacional, e a loja fecha: 23% do erro de fevereiro no A0-crua (EDA §4,
      item 13)
- [ ] 1.4 **Modelo A0 — SARIMA puro diário** (`training_scripts/baseline/`, sem exógena):
      ablação de referência, piso de desempenho
- [ ] 1.5 **Modelo A1 — SARIMAX + calendário** (`training_scripts/baseline/`): exógenas de
      calendário ponderadas por importância RF/MDI (clip 0.1)
- [ ] 1.6 Seleção de ordem via grid AIC (`p,q ∈ 0..2`; `P,Q ∈ 0..1`; `D=0`; `m=7`)
- [ ] 1.7 Avaliação (`training_scripts/validation/`): hold-out 28 dias + walk-forward CV
      (≥ 4 folds, origem móvel, horizonte 14 dias); métricas MASE, RMSSE, cobertura do IC,
      MAE/RMSE; diagnóstico de resíduos Ljung-Box + Shapiro-Wilk. Lições do A0-crua (EDA §4,
      itens 14–15):
      - MAE **relativo à naïve na mesma janela** e nº de folds em que o modelo vence (o MASE
        sozinho fica otimista quando o treino tem picos);
      - **largura** do IC 95% junto da cobertura;
      - folds cobrindo **um ano inteiro**, dezembro incluído (como os 26 folds do EDA);
      - seleção de ordem **dentro de cada fold** (ou ordem fixada de antemão), para a escolha
        não ver o período testado;
      - para comparar com o A0-crua, **somar as previsões das 2 unidades** e medir no total,
        nas mesmas datas
- [ ] 1.8 Consolidar `training_scripts/results/metrics/baseline_A0_A1.csv` por
      `unidade`

**Checkpoint**: scorecard A0-crua → A0 → A1 (no total e por `unidade`), mostrando o ganho
dos achados do EDA e, depois, o da exógena de calendário, antes de qualquer dado externo.

---

## Fase 2 — Aquisição das bases de enriquecimento externas

Parte **nova**, fora do que `SPECS.md`/artigo já documentam — precisa de ADR próprio
(`docs/prediction/ADR-008-variaveis-exogenas-externas.md`) justificando cada fonte.
Nenhuma envolve dado pessoal de cliente → sem conflito com Princípio VI/LGPD.

| Fonte | Dado | API/acesso | Observação |
| --- | --- | --- | --- |
| Feriados nacionais | Datas exatas | [BrasilAPI](https://brasilapi.com.br/api/feriados/v1/{ano}) — gratuita | Nível nacional. **Traz o Carnaval** (conferido em 2026-09-27) e Consciência Negra; cache em `data/external/` |
| Feriados municipais | Nova Lima e Itabirito/MG | Decretos municipais — **curadoria manual** | Tabela fixa versionada. Dados mostram fechamento das duas lojas em 15/08 e 08/12 (`FECHAMENTOS_LOCAIS` em `enriched/dados_externos.py`); confirmar com a parceira |
| Datas comemorativas móveis | Dia das Mães (2º dom. maio), Namorados (12/jun), Finados (2/nov), Natal | cálculo determinístico | Vira exógena "dias até a data" (diária) |
| Clima | Temperatura e precipitação **diária** em Nova Lima/Itabirito | [Open-Meteo](https://open-meteo.com) — gratuita, por lat/long | Chuva afeta venda de flor de corte. **Sem ganho na série total** (doc 03), mesmo com clima observado |
| Indicadores econômicos | IPCA, Selic, confiança do consumidor | [BCB SGS](https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados) | Séries mensais — **forward-fill para diário**; peso provavelmente baixo no horizonte de 14 dias |
| Interesse de busca | "flores", "buquê", "dia das mães presente" | `pytrends` (não oficial) | Instável; opcional |

- [ ] 2.1 Criar `backend/infrastructure/external_data/` (I/O — clientes HTTP, cache local
      em `data/external/`) — **não é domínio** (Princípio I)
- [ ] 2.2 Cliente para cada fonte, com cache em disco
- [ ] 2.3 Curadoria manual da tabela de feriados municipais (Nova Lima + Itabirito)
- [ ] 2.4 `docs/prediction/ADR-008-variaveis-exogenas-externas.md`: justificativa por fonte
- [ ] 2.5 Atualizar `SPECS.md` §5.2 com a tabela de exógenas externas **diárias**

**Checkpoint**: `data/external/` populado com séries **diárias** alinhadas ao período
Jan/2024–Fev/2026, prontas para merge com a série de cada `unidade`.

---

## Fase 3 — L1 SARIMAX enriquecido vs. baseline + camadas L2/L3

- [ ] 3.1 `domain/features/external_exogenous.py` (lógica **pura**): merge diário das
      séries externas com o índice de cada `unidade`
- [ ] 3.2 **Modelo B — SARIMAX + calendário + externo** (`training_scripts/enriched/`)
- [ ] 3.3 Reaplicar RF/MDI para ponderar o conjunto ampliado (mitiga multicolinearidade
      entre exógenas)
- [ ] 3.4 Mesmo protocolo de avaliação da Fase 1 (hold-out 28d + walk-forward h=14 ≥ 4
      folds + resíduos) — **mesmas categorias, mesmos splits** que A0/A1
- [ ] 3.5 Teste de significância pareado (Diebold-Mariano ou Wilcoxon nos erros de A1 vs B)
- [ ] 3.6 **L2** — `disaggregation/sku_split.py`: share móvel (4–8 semanas) × perfil de
      dia-da-semana do nível, em cascata (unidade→categoria→SKU); fallback uniforme;
      avaliar MASE no nível de categoria e de SKU
- [ ] 3.7 **L3** — `replenishment/policy.py` + `replenishment/simulation.py`: rodar a
      política sobre o hold-out e medir **perda (murcha) + ruptura** contra a regra
      ingênua "repor a média dos últimos 7 dias"
- [ ] 3.8 Relatório `docs/prediction/comparacao_enriquecimento.md`: A0 vs A1 vs B por
      `unidade`, e o efeito na simulação de reposição

**Checkpoint**: decisão documentada — variáveis externas entram ou não na versão de
produção do L1; a política L3 bate a regra ingênua.

---

## Fase 4 — Demanda intermitente por SKU e outros modelos

Duas comparações distintas:

### 4A — Hierárquico vs. demanda intermitente (contribuição acadêmica ii)

- [ ] 4A.1 Implementar Croston, TSB e SBA por SKU (`training_scripts/alternative_models/`),
      direto na série diária do SKU (sem agregação)
- [ ] 4A.2 Comparar contra **L1 SARIMAX + L2 desagregação** para os mesmos SKUs, **mesmos
      splits** de walk-forward (origem móvel, h=14)
- [ ] 4A.3 Métricas: MASE, RMSSE no nível de SKU + a **simulação de reposição** (perda +
      ruptura) de cada abordagem
- [ ] 4A.4 Relatório `docs/prediction/comparacao_hierarquico_vs_intermitente.md` — veredito
      sobre qual arquitetura serve melhor um catálogo perecível de cauda longa

### 4B — Teto de ML (modelo global)

O artigo (M4/M5, Makridakis et al.) argumenta que ML overfita com séries curtas **por
série**. A forma justa de testar é um **modelo global** (uma rede só, as 2 séries de
`unidade` empilhadas), como venceram a M5 (LightGBM global, N-BEATS, DeepAR).

| Modelo | Papel |
| --- | --- |
| Naïve sazonal semanal / ETS | Baseline clássico — é o denominador do MASE |
| LightGBM global (lags + exógenas) | Árvore com features tabulares, todas as séries juntas |
| N-BEATS / DeepAR simplificado | Rede global multi-série |

- [ ] 4B.1 Dataset "long format" (`unidade × dia × exógenas`)
- [ ] 4B.2 Treinar cada candidato com **os mesmos splits** de walk-forward
- [ ] 4B.3 Métricas + tempo de treino/inferência (relevante para RNF-03)
- [ ] 4B.4 Teste de significância pareado contra o melhor SARIMAX da Fase 3
- [ ] 4B.5 Relatório `docs/prediction/comparacao_modelos_final.md`
- [ ] 4B.6 Atualizar `ADR-001` com "Revisão empírica" — mantém SARIMAX se vencer, ou abre
      ADR-010 propondo o vencedor (a porta já está prevista no ADR-001)

**Checkpoint**: decisão final e documentada sobre qual família de modelo vai para
produção em cada camada — com números.

---

## Fase 5 — Consolidação e integração ao produto

- [ ] 5.1 Implementar `backend/domain/{features,models,disaggregation,replenishment}/`
      "para valer" usando o pipeline vencedor, seguindo `tasks.md` Fases 4–5
- [ ] 5.2 Se o vencedor usar dados externos, adicionar o job de atualização dessas bases
      ao scheduler (semanal, junto do reajuste L1)
- [ ] 5.3 Registrar os relatórios comparativos como suporte à seção 6.5 do artigo
      (dimensão "validação estatística") e às contribuições acadêmicas: (i) ponderação
      RF/MDI, (ii) SARIMAX hierárquico × demanda intermitente para catálogo perecível
- [ ] 5.4 Atualizar `SPECS.md` e a constituição se o vencedor não for SARIMAX no L1
      (emenda MAJOR/MINOR conforme Governance)

---

## Ordem de execução recomendada

Fase 1 → Fase 2 → Fase 3 → Fase 4 (4A e 4B) → Fase 5. Fases 1–4 rodam em
`training_scripts/` (rápido, descartável); só a Fase 5 mexe em código de produção.
