"""Caminhos e layout de colunas do pipeline de pré-processamento.

Reconstrução do pipeline legado (`src/data/`, deletado no commit `ac4dd9e` ao migrar
para a arquitetura limpa em `backend/`). Ver `docs/prediction/01-pre_processing.md`
para o relato completo das decisões.
"""
import os

_PREPROCESSING_DIR = os.path.dirname(os.path.abspath(__file__))
_TRAINING_SCRIPTS_DIR = os.path.dirname(_PREPROCESSING_DIR)
_IA_PREDICTOR_ROOT = os.path.dirname(_TRAINING_SCRIPTS_DIR)

# Entrada: os XLSX brutos de produção (só leitura — este pipeline nunca escreve aqui).
RAW_DIR = os.path.join(_IA_PREDICTOR_ROOT, 'data', 'raw')

# Saída: sandbox de experimentação, isolado do `data/processed/` de produção para que
# rodar estes scripts nunca sobrescreva o CSV canônico usado pelo backend. Fica em
# `training_scripts/output/` (compartilhado por todas as etapas de pré-processamento),
# não dentro de `preprocessing/`, para não misturar código-fonte com dado gerado.
OUTPUT_DIR = os.path.join(_TRAINING_SCRIPTS_DIR, 'output')

CONSOLIDATED_CSV = os.path.join(OUTPUT_DIR, 'contas_a_receber.csv')          # Etapa 1
LOG_FILE = os.path.join(OUTPUT_DIR, 'processamento_log.json')                # Etapa 1
REDUCED_CSV = os.path.join(OUTPUT_DIR, 'contas_a_receber_sem_colunas.csv')   # Etapa 2
TAXONOMY_CSV = os.path.join(OUTPUT_DIR, 'contas_a_receber_taxonomia.csv')    # Etapa 3

# Schema do parser — um registro por (documento, produto). Ordem espelha o CSV de
# produção (`ia-predictor/data/processed/contas_a_receber.csv`).
FIELDS = [
    'doc_tipo', 'doc_numero', 'pagamento', 'emissao', 'operador',
    'cliente_cod', 'cliente_nome', 'empresa', 'vendedor', 'obs',
    'produto_cod', 'produto_nome', 'qtdade', 'vl_unit',
    'vl_total', 'vl_desconto', 'tot_liq', 'icms_ret', 'total_liquido_doc',
    'arquivo_origem',
]

# Índices de coluna (1-based) do XLSX de "Contas a Receber" exportado pelo sistema da
# floricultura — layout fixo do relatório, não muda entre meses.
HEADER_COLUMNS = {
    'documento': 1,
    'pagamento': 3,
    'emissao': 8,
    'operador': 17,
}

DETAIL_COLUMNS = {
    'cliente': 1,
    'empresa': 1,
    'vendedor': 13,
    'obs': 1,
}

PRODUCT_COLUMNS = {
    'produto': 1,
    'qtdade': 8,
    'vl_unit': 9,
    'vl_total': 14,
    'vl_desconto': 15,
    'tot_liq': 18,
    'icms_ret': 20,
}

NET_TOTAL_COLUMN = 5

# Chave composta usada para deduplicar registros ENTRE arquivos diferentes (sobreposição
# de datas nas bordas do mês — o mesmo documento pode ser exportado em dois meses
# consecutivos). Nunca é aplicada dentro do mesmo arquivo: um produto pode legitimamente
# aparecer em mais de uma linha no mesmo documento (comprovado em
# docs/prediction/01-pre_processing.md, seção 3 — o total_liquido_doc só fecha contando as
# duas linhas). `emissao`, `qtdade` e `vl_total` além de `doc_numero`/`produto_cod`
# reduzem o risco de colisão acidental entre documentos não relacionados que reaproveitam
# o mesmo número (confirmado que `doc_numero` se repete entre `doc_tipo` diferentes).
DUPLICATE_KEY_FIELDS = ('doc_numero', 'produto_cod', 'emissao', 'qtdade', 'vl_total')

# Fase 2 do pipeline (reduce_schema.py) — colunas sem uso analítico para a modelagem
# hierárquica diária. Ver docs/prediction/01-pre_processing.md (seção 4) e
# docs/prediction/ADR-010-exogenas-nominais-fora-do-l1.md para a justificativa.
#
# `doc_numero` faz parte de DUPLICATE_KEY_FIELDS (dedup da Etapa 1, que roda ANTES desta
# e não é afetada). `doc_numero` e `cliente_cod` saem por serem identificadores.
#
# `pagamento` e `vendedor` saem (revisão 2026-08-30 / ADR-009 + ADR-010): não são
# exógenas do modelo L1 (`unidade × categoria`, diário) — são atributos de transação
# (nível de agregação errado), não conhecíveis no horizonte de previsão (leakage) e
# custosos no orçamento de parâmetros. Ficam disponíveis no CSV da Etapa 1 para a
# triagem de importância na EDA.
#
# `empresa` é MANTIDA — é a chave de agrupamento `unidade` da camada L1, não uma exógena.
COLUMNS_TO_DROP = [
    'operador', 'obs', 'icms_ret', 'arquivo_origem',
    'cliente_nome', 'produto_nome', 'doc_tipo',
    'doc_numero', 'cliente_cod',
    'pagamento', 'vendedor',
]

# Etapa 3 do pipeline (map_taxonomy.py) — deriva `unidade` (de `empresa`) e `categoria`
# (de `produto_cod`/`produto_nome`) a partir das tabelas de/para em `taxonomy/`.
# Ver docs/prediction/01-pre_processing.md (seção 5) e ADR-009 (seção 8).
#
# A antiga Etapa 3 (`discretize_fields.py`, one-hot de pagamento/empresa/vendedor) foi
# REMOVIDA em 2026-08-30 (ADR-009 + ADR-010): essas categóricas não entram como exógenas
# do L1. O one-hot está no histórico do git se precisar como referência.
