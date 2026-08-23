# Diagramas de Atividades — Sistema de Previsão de Estoque

> Diagrama 2 de 5. Ver índice em [`README.md`](README.md).

Este arquivo contém dois diagramas de atividades (Mermaid `flowchart`), cobrindo os dois
fluxos operacionais centrais do sistema, conforme SPECS.md §1.2 (fluxo ponta a ponta) e
§10 (agendamento).

---

## (a) Fluxo de Upload → ETL → Retrain

Cobre US1 (Upload de Planilha Mensal) e o fluxo descrito em SPECS.md §4.4
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
    F --> G[deduplicator.deduplicate<br/>chave: doc_numero + produto_cod]
    G --> H[file_manager.append_to_csv<br/>contas_a_receber.csv]
    H --> I[file_manager.log_processing<br/>grava processing_log]
    I --> J["Retorna UploadResponse<br/>(rows_added, rows_skipped, rows_duplicate)"]
    J --> K{retrain_scheduled?}
    K -- sim --> L[retrain_service.schedule_async_retrain<br/>dispara retrain em background]
    L --> M[Pipeline SARIMAX por produto<br/>ver diagrama (b)]
    M --> N[model_registry.save_artifact<br/>persiste ordem, métricas, status]
    N --> O[Invalida forecasts_cache]
    O --> P([Fim — previsões atualizadas<br/>disponíveis no dashboard])
    K -- não --> P

    style C1 fill:#f94144,color:#fff
    style E1 fill:#f94144,color:#fff
    style J fill:#90be6d
    style P fill:#43aa8b,color:#fff
```

**Notas de rastreabilidade**: FR-001, FR-002, FR-011 (log de upload/retrain), RNF-02
(rastreabilidade), SC-001 (confirmação em <30s).

---

## (b) Fluxo de Retrain Semanal Automático

Cobre REQ-03/FR-005 e SPECS.md §10 (`weekly_retrain.py` + `retrain_service.py`).

```mermaid
flowchart TD
    A([APScheduler dispara job<br/>toda segunda-feira 02:00]) --> B[RetrainService.run_full_retrain<br/>trigger='scheduled']
    B --> C[Carrega contas_a_receber.csv<br/>completo]
    C --> D[Seleciona TOP_N_PRODUCTS=20<br/>por qtdade total vendida]
    D --> E{Para cada produto<br/>do Top N}
    E --> F[prepare_monthly_series<br/>agrega mensal, freq='MS']
    F --> G{len(série) ≥<br/>MIN_OBSERVATIONS=15?}
    G -- não --> G1[status = insufficient_data<br/>produto excluído do pipeline]
    G1 --> N
    G -- sim --> H[build_exogenous_features<br/>15 variáveis exógenas mensais]
    H --> I[compute_rf_importance +<br/>weight_features clip 0.1]
    I --> J[suggest_d via ADF/KPSS →<br/>select_sarimax_order grid AIC<br/>36 combinações]
    J --> K[fit_sarimax<br/>maxiter=300]
    K --> L[walk_forward_cv<br/>4 folds expanding-window]
    L --> M[residual_tests<br/>Ljung-Box + Shapiro-Wilk]
    M --> M1{MAPE < 20%<br/>e/ou SMAPE < 30%?}
    M1 -- sim --> M2[status = trained]
    M1 -- não --> M3[status = low_confidence<br/>previsão ainda gerada, com aviso]
    M2 --> N[model_registry.save_artifact<br/>joblib: modelo + importâncias]
    M3 --> N
    N --> O{Mais produtos<br/>no Top N?}
    O -- sim --> E
    O -- não --> P[Invalida forecasts_cache<br/>de todos os produtos retreinados]
    P --> Q[Registra RetrainHistory<br/>started_at, finished_at, contagens]
    Q --> R([Fim — modelos e previsões<br/>disponíveis via API])

    style G1 fill:#f9c74f
    style M3 fill:#f9c74f
    style M2 fill:#90be6d
    style R fill:#43aa8b,color:#fff
```

**Notas de rastreabilidade**: exceções por produto são capturadas e logadas
individualmente — não abortam o pipeline completo (SPECS.md §10.2). RNF-03 exige que o
ciclo completo (≤20 produtos) conclua em menos de 2 horas. Princípio III da constituição
(validação obrigatória via walk-forward CV ≥4 folds antes de `status = "trained"`).
