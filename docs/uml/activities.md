# Diagramas de Atividades — Sistema de Previsão de Vendas

> Diagrama 2 de 5. Ver índice em [`README.md`](README.md).

Este arquivo contém três diagramas de atividades (Mermaid `flowchart`), cobrindo os
fluxos operacionais centrais do sistema, conforme SPECS.md §1.2 (fluxo ponta a ponta),
§10 (agendamento) e [ADR-009](../prediction/ADR-009-granularidade-diaria-e-reposicao.md)
(arquitetura hierárquica L1 → L2 → L3).

---

## (a) Fluxo de Upload → ETL → Reajuste

Cobre US1 (Upload de Planilha) e o fluxo descrito em SPECS.md §4.4
(`upload_service.process_upload`).

```mermaid
flowchart TD
    A([Início: gestora seleciona<br/>arquivo .xlsx no dashboard]) --> B[/POST /api/v1/upload<br/>multipart/form-data/]
    B --> C{Arquivo é .xlsx/.xlsm<br/>e ≤ 50 MB?}
    C -- não --> C1[Retorna erro 400/413<br/>em PT-BR] --> Z1([Fim — usuário corrige e reenvia])
    C -- sim --> D[parser.parse_xlsx<br/>XLSX → records + skipped]
    D --> E{Estrutura reconhecida?<br/>possui campos obrigatórios}
    E -- não --> E1[Retorna erro 422<br/>'estrutura não reconhecida'] --> Z1
    E -- sim --> F[normalizer.normalize_records<br/>cast tipos, strip, remove qtdade≤0]
    F --> G[deduplicator.deduplicate<br/>chave: doc_numero + produto_cod +<br/>emissao + qtdade + vl_total]
    G --> H[file_manager.append_to_csv<br/>contas_a_receber.csv]
    H --> I[file_manager.log_processing<br/>grava processing_log]
    I --> J["Retorna UploadResponse<br/>(rows_added, rows_skipped, rows_duplicate)"]
    J --> K{retrain_scheduled?}
    K -- sim --> L[retrain_service.schedule_async_retrain<br/>dispara reajuste L1 em background]
    L --> M[Pipeline L1 por unidade × categoria<br/>ver diagrama (b)]
    M --> N[model_registry.save_artifact<br/>persiste ordem, MASE/RMSSE, status]
    N --> O["Gera a previsão de 60 dias<br/>trigger='retrain' — ver (c)"]
    O --> P([Fim — modelos e previsão atualizados])
    K -- não --> P

    style C1 fill:#f94144,color:#fff
    style E1 fill:#f94144,color:#fff
    style J fill:#90be6d
    style P fill:#43aa8b,color:#fff
```

**Notas de rastreabilidade**: FR-001, FR-002, FR-011 (log de upload/retrain), RNF-02
(rastreabilidade), SC-001 (confirmação em <30s).

---

## (b) Fluxo de Reajuste Semanal dos Modelos L1

Cobre FR-005 e SPECS.md §10 (`weekly_retrain.py` + `retrain_service.py`). Ajusta um
SARIMAX por `unidade × categoria` sobre a série **diária agregada**.

```mermaid
flowchart TD
    A([APScheduler dispara job<br/>toda segunda-feira 02:00]) --> A1{Venda nova desde o último<br/>treino done ou config mudou?}
    A1 -- não --> A2[Registra RetrainHistory<br/>status = skipped] --> A3([Fim — mesmo modelo,<br/>mesma previsão])
    A1 -- sim --> B[RetrainService.run_full_retrain<br/>trigger='scheduled']
    B --> C[Carrega contas_a_receber.csv<br/>completo]
    C --> D[Agrupa por unidade × categoria]
    D --> E{Para cada<br/>unidade × categoria}
    E --> F[prepare_daily_series<br/>soma diária, freq='D', reindex completo]
    F --> G{len(série) ≥<br/>MIN_OBSERVATIONS_DAYS=180?}
    G -- não --> G1[status = insufficient_data<br/>categoria sem previsão]
    G1 --> O
    G -- sim --> H[build_calendar_exogenous<br/>dia-da-semana, feriados, dias-até-data-comemorativa]
    H --> I[compute_rf_importance +<br/>weight_features clip 0.1]
    I --> J[suggest_d via ADF/KPSS →<br/>select_sarimax_order grid AIC<br/>D=0, m=7]
    J --> K[fit_sarimax]
    K --> L[walk_forward_cv<br/>≥4 folds, origem móvel, h=14d<br/>→ MASE, RMSSE, cobertura IC]
    L --> M[residual_tests<br/>Ljung-Box + Shapiro-Wilk]
    M --> M1{MASE < 1.0 E cobertura ∈ [90,98]<br/>E simulação de reposição<br/>melhor que regra ingênua 7d?}
    M1 -- sim --> M2[status = trained]
    M1 -- não --> M3[status = low_confidence<br/>previsão ainda gerada, com aviso]
    M2 --> N[model_registry.save_artifact<br/>joblib: modelo + importâncias]
    M3 --> N
    N --> O{Mais categorias?}
    O -- sim --> E
    O -- não --> Q[Registra RetrainHistory<br/>started_at, finished_at, contagens]
    Q --> P["Gera a previsão de 60 dias<br/>trigger='retrain' — ver (c)"]
    P --> R([Fim — modelos L1 e previsão prontos])

    style A2 fill:#f9c74f
    style G1 fill:#f9c74f
    style M3 fill:#f9c74f
    style M2 fill:#90be6d
    style R fill:#43aa8b,color:#fff
```

**Notas de rastreabilidade**: exceções por categoria são capturadas e logadas
individualmente — não abortam o pipeline. RNF-03 exige que o ciclo conclua em < 2h.
Princípio III da constituição (walk-forward CV ≥4 folds + MASE < 1.0 + simulação de
reposição antes de `status = "trained"`).

---

## (c) Fluxo de Geração da Previsão

Roda ao fim de cada treino (`trigger='retrain'`) e, todo dia às 03:00, só se o calendário
mudou depois da última geração (`trigger='calendar'`). **Não reajusta**: usa os modelos do
último treino. Prevê de uma vez 60 dias (`FORECAST_STORED_DAYS`) a partir do último dia com
venda; a API entrega os 14 dias a partir de hoje, então a janela anda com a data sem
recalcular — com o mesmo modelo e os mesmos dados, gerar todo dia repetiria os mesmos
números.

```mermaid
flowchart TD
    A0(["Fim de um treino — ver (a) e (b)"]) --> B
    A([APScheduler — todo dia 03:00]) --> A1{calendar_days mudou depois<br/>da última forecast_runs done?}
    A1 -- não --> Z0([Fim — nada a gerar])
    A1 -- sim --> B[Abre forecast_runs<br/>start_date = data_until + 1<br/>end_date = start_date + 59]
    B --> C{Para cada unidade<br/>com modelo trained/low_confidence}
    C --> D[Carrega o modelo da loja<br/>model_artifacts.artifact_path]
    D --> E[Prevê start_date…end_date<br/>exógenas de calendar_days, IC 95%]
    E --> F[Previsão por categoria<br/>e por produto da loja]
    F --> G[→ forecasts_cache<br/>níveis unit, category, product]
    G --> H{Mais unidades?}
    H -- sim --> C
    H -- não --> K[Fecha forecast_runs<br/>status, unidades e SKUs atendidos]
    K --> L([Fim — dashboard mostra os<br/>14 dias a partir de hoje])

    style Z0 fill:#90be6d
    style L fill:#43aa8b,color:#fff
```

**Notas de rastreabilidade**: FR-012 (log de cada geração), SC-004 (conclui em < 15min),
Princípio V (rastreabilidade — data, período previsto e contagem de SKUs por geração, em
`forecast_runs`). Se hoje + 14 dias passa de `end_date`, a base está desatualizada e o
dashboard avisa para carregar planilhas novas.
