import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_DIR = os.path.join(_PROJECT_ROOT, 'data', 'raw')
PROCESSED_DIR = os.path.join(_PROJECT_ROOT, 'data', 'processed')
OUTPUT_CSV = os.path.join(PROCESSED_DIR, 'contas_a_receber.csv')
LOG_FILE = os.path.join(PROCESSED_DIR, 'processamento_log.json')

FIELDS = [
    'doc_tipo', 'doc_numero', 'pagamento', 'emissao', 'operador',
    'cliente_cod', 'cliente_nome', 'empresa', 'vendedor', 'obs',
    'produto_cod', 'produto_nome', 'qtdade', 'vl_unit',
    'vl_total', 'vl_desconto', 'tot_liq', 'icms_ret', 'total_liquido_doc',
    'arquivo_origem',
]

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