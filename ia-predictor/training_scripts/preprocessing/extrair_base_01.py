"""Etapa 1 do pipeline: lê todos os XLSX de `data/raw/` e gera `Base01.csv`.

Script único e autocontido — faz o parse estrutural do XLSX de "Contas a Receber"
(um registro por par documento/produto) e escreve direto no CSV consolidado, sem
nenhuma alteração de dados além da decodificação numérica (vírgula/ponto) necessária
para ler os valores. Nenhuma limpeza de regra de negócio acontece aqui (isso é Etapa 2+).

Cada "Documento:" no XLSX é um bloco de linhas: cabeçalho (cliente, empresa, vendedor,
data, forma de pagamento) seguido de N linhas de produto até a linha "Totais". Cada
planilha só é reprocessada se for nova ou tiver mudado (controle por hash MD5 em
`processamento_log.json`) e a deduplicação só compara registros ENTRE arquivos
diferentes (sobreposição de datas nas bordas do mês) — nunca dentro do mesmo arquivo,
pois um produto pode legitimamente aparecer mais de uma vez no mesmo documento.

Reconstrução de `src/data/parser.py` + `src/data/preprocess_raw_data_by_month.py`
(deletados no commit `ac4dd9e`), fundidos em um único arquivo. Roda contra os XLSX
reais de produção (`ia-predictor/data/raw/`, só leitura) mas escreve a saída em
`training_scripts/output/` — nunca no `data/processed/` de produção, para nunca
arriscar duplicar/corromper o CSV canônico usado pelo backend.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.extrair_base01
"""
import csv
import hashlib
import json
import os
from datetime import datetime

import openpyxl

# --------------------------------------------------------------------------- #
# Caminhos do pipeline — `OUTPUT_DIR` é importado pelas etapas seguintes
# (tratamento_de_dados_02, classificacao_03, limpeza_para_treino_04, dados_externos_10,
# run_all) para montar os próprios arquivos de saída no mesmo diretório.
# --------------------------------------------------------------------------- #
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

CONSOLIDATED_CSV = os.path.join(OUTPUT_DIR, 'Base01.csv')
LOG_FILE = os.path.join(OUTPUT_DIR, 'processamento_log.json')

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


# --------------------------------------------------------------------------- #
# Utilitários de baixo nível
# --------------------------------------------------------------------------- #

def format_decimal(value):
    """Formata um valor numérico usando vírgula como separador decimal (padrão BR)."""
    if value is None:
        return '0'
    try:
        num = float(value)
        if num == int(num):
            return str(int(num))
        return f'{num:.2f}'.replace('.', ',')
    except (ValueError, TypeError):
        return str(value).replace('.', ',')


def split_document(text):
    """Separa 'C1 44799' em ('C1', '44799')."""
    if not text:
        return '', ''
    parts = text.strip().split(None, 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return '', text.strip()


def split_code_name(text):
    """Separa 'codigo - nome' em ('codigo', 'nome'). Ex.: '2820 - TATIANE' -> ('2820', 'TATIANE')."""
    if not text:
        return '', ''
    if ' - ' in text:
        code, name = text.split(' - ', 1)
        return code.strip(), name.strip()
    return '', text.strip()


def parse_field(text, prefix):
    """Extrai o valor após um prefixo. Ex.: parse_field('Cliente: João', 'Cliente:') -> 'João'."""
    if text and text.strip().startswith(prefix):
        return text.strip()[len(prefix):].strip()
    return None


def cell_str(row_map, col):
    """Extrai o valor de uma célula como string limpa (trim), tolerando None."""
    return str(row_map.get(col, '') or '').strip()


def file_hash(path):
    """Calcula o hash MD5 de um arquivo — usado para pular planilhas já processadas."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def load_log(log_file):
    """Carrega o log de processamento (histórico de execuções e hashes por arquivo)."""
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'arquivos_processados': {}, 'historico_execucoes': []}


def save_log(log, log_file):
    """Salva o log de processamento."""
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def load_existing_record_keys(csv_path, key_fields=DUPLICATE_KEY_FIELDS):
    """Monta o conjunto de chaves compostas já presentes no CSV, para deduplicação."""
    keys = set()
    if not os.path.exists(csv_path):
        return keys
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            key = tuple(row.get(field, '') for field in key_fields)
            keys.add(key)
    return keys


# --------------------------------------------------------------------------- #
# Parse estrutural do XLSX
# --------------------------------------------------------------------------- #

def _load_rows(input_path):
    """Carrega todas as linhas do XLSX como uma lista de dicts {coluna: valor}."""
    wb = openpyxl.load_workbook(input_path)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=False):
        cell_map = {c.column: c.value for c in row}
        rows.append(cell_map)
    return rows


def _parse_products(rows, i, total_rows):
    """Lê as linhas de produto até encontrar 'Totais'.

    Quando o documento ocupa mais de uma página impressa, o relatório intercala, entre
    as linhas de produto, um bloco de rodapé/cabeçalho repetido (marca de impressão
    'dd/mm/aaaa - hh:mm' + contador de página, nome da empresa, título do relatório,
    linhas em branco) antes de retomar os produtos restantes do mesmo documento. Esse
    bloco não tem valor na coluna de quantidade — inclusive a própria marca de
    impressão, que tem a mesma forma 'código - nome' de uma linha de produto e seria
    lida como um produto fantasma se só o texto da coluna 1 fosse checado. Por isso o
    critério real de "é produto" é ter quantidade, não só não ser 'Totais'/vazio.
    """
    products = []
    while i < total_rows:
        prod_a = cell_str(rows[i], PRODUCT_COLUMNS['produto'])
        if prod_a == 'Totais' or prod_a.startswith('Documento:'):
            break
        qtd = rows[i].get(PRODUCT_COLUMNS['qtdade'])
        if qtd is None:
            i += 1
            continue
        products.append({
            'produto': prod_a,
            'qtdade': qtd,
            'vl_unit': rows[i].get(PRODUCT_COLUMNS['vl_unit'], 0),
            'vl_total': rows[i].get(PRODUCT_COLUMNS['vl_total'], 0),
            'vl_desconto': rows[i].get(PRODUCT_COLUMNS['vl_desconto'], 0),
            'tot_liq': rows[i].get(PRODUCT_COLUMNS['tot_liq'], 0),
            'icms_ret': rows[i].get(PRODUCT_COLUMNS['icms_ret'], 0),
        })
        i += 1
    return products, i


def _build_record(doc_type, doc_number, header, product):
    """Monta um registro final a partir dos dados de cabeçalho + um produto."""
    prod_code, prod_name = split_code_name(product['produto'])
    return {
        'doc_tipo': doc_type,
        'doc_numero': doc_number,
        'pagamento': header['pagamento'],
        'emissao': header['emissao'],
        'operador': header['operador'],
        'cliente_cod': header['cliente_cod'],
        'cliente_nome': header['cliente_nome'],
        'empresa': header['empresa'],
        'vendedor': header['vendedor'],
        'obs': header['obs'],
        'produto_cod': prod_code,
        'produto_nome': prod_name,
        'qtdade': format_decimal(product['qtdade']),
        'vl_unit': format_decimal(product['vl_unit']),
        'vl_total': format_decimal(product['vl_total']),
        'vl_desconto': format_decimal(product['vl_desconto']),
        'tot_liq': format_decimal(product['tot_liq']),
        'icms_ret': format_decimal(product['icms_ret']),
        'total_liquido_doc': format_decimal(header['total_liquido_doc']),
    }


def parse_xlsx(input_path):
    """Faz o parse de um XLSX de contas a receber e retorna (records, skipped)."""
    rows = _load_rows(input_path)
    total_rows = len(rows)

    records = []
    skipped = []
    i = 0

    while i < total_rows:
        cell_a = cell_str(rows[i], 1)

        if not cell_a.startswith('Documento:'):
            i += 1
            continue

        start_line = i + 1
        try:
            # --- Cabeçalho do documento ---
            document = parse_field(cell_a, 'Documento:')
            payment = parse_field(cell_str(rows[i], HEADER_COLUMNS['pagamento']), 'Pagto:')
            issue_date = parse_field(cell_str(rows[i], HEADER_COLUMNS['emissao']), 'Emissão:')
            operator = parse_field(cell_str(rows[i], HEADER_COLUMNS['operador']), 'Operador:')

            # --- Cliente ---
            i += 1
            client_raw = cell_str(rows[i], DETAIL_COLUMNS['cliente'])
            client = parse_field(client_raw, 'Cliente:')
            if client is None:
                raise ValueError(f"Esperava 'Cliente:' na linha {i+1}, encontrado: '{client_raw}'")
            client_code, client_name = split_code_name(client)

            # --- Empresa / Vendedor ---
            i += 1
            company = parse_field(cell_str(rows[i], DETAIL_COLUMNS['empresa']), 'Empresa:')
            salesperson = parse_field(cell_str(rows[i], DETAIL_COLUMNS['vendedor']), 'Vendedor:')

            # --- Observações ---
            i += 1
            notes = parse_field(cell_str(rows[i], DETAIL_COLUMNS['obs']), 'Obs:') or ''

            # --- Pula até a linha de cabeçalho 'Produto' ---
            i += 1
            cell_check = cell_str(rows[i], 1)
            if cell_check == '':
                i += 1
                cell_check = cell_str(rows[i], 1)
            if cell_check != 'Produto':
                raise ValueError(f"Esperava 'Produto' na linha {i+1}, encontrado: '{cell_check}'")

            # --- Produtos ---
            i += 1
            products, i = _parse_products(rows, i, total_rows)

            # --- Totais ---
            if cell_str(rows[i], 1) != 'Totais':
                i += 1
            i += 2
            net_total = rows[i].get(NET_TOTAL_COLUMN, 0)

            doc_type, doc_number = split_document(document)

            header = {
                'pagamento': payment,
                'emissao': issue_date,
                'operador': operator,
                'cliente_cod': client_code,
                'cliente_nome': client_name,
                'empresa': company,
                'vendedor': salesperson,
                'obs': notes,
                'total_liquido_doc': net_total,
            }

            for product in products:
                records.append(_build_record(doc_type, doc_number, header, product))

            i += 1

        except Exception as e:
            skipped.append({
                'line': start_line,
                'reason': str(e),
                'content': cell_a,
            })
            i += 1

    return records, skipped


# --------------------------------------------------------------------------- #
# Orquestração: lê `data/raw/`, deduplica entre arquivos, grava `Base01.csv`
# --------------------------------------------------------------------------- #

def debug_raw_directory(raw_dir=RAW_DIR):
    print(f"\n=== Verificando {raw_dir} ===")
    if not os.path.exists(raw_dir):
        print(f"  [!] Diretório não existe: {raw_dir}")
        return

    all_files = os.listdir(raw_dir)
    print(f"  [OK] Diretório existe — {len(all_files)} arquivo(s)")
    for f in sorted(all_files):
        is_xlsx = f.lower().endswith(('.xlsx', '.xlsm'))
        status = "[XLSX]" if is_xlsx else "[OUTRO]"
        print(f"    {status} {f}")
    print()


def ensure_directories(raw_dir=RAW_DIR, output_dir=OUTPUT_DIR):
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)


def list_raw_xlsx_files(raw_dir=RAW_DIR):
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir, exist_ok=True)
        return []
    all_files = os.listdir(raw_dir)
    return sorted(f for f in all_files if f.lower().endswith(('.xlsx', '.xlsm')))


def build_pending_files(file_names, raw_dir=RAW_DIR, log=None):
    """Retorna os arquivos ainda não registrados no log ou cujo hash mudou."""
    if log is None:
        log = {}
    processados = log.get('arquivos_processados', {})
    pending = []
    for name in file_names:
        path = os.path.join(raw_dir, name)
        h = file_hash(path)
        entry = processados.get(name)
        if entry and entry.get('hash') == h:
            continue
        pending.append((name, path, h))
    return pending


def process_pending_files(pending, csv_path=CONSOLIDATED_CSV, verbose=True):
    csv_exists = os.path.exists(csv_path)
    existing_keys = load_existing_record_keys(csv_path, key_fields=DUPLICATE_KEY_FIELDS)

    total_records = 0
    total_skipped = 0
    total_duplicates = 0
    details = []

    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter=';')
        if not csv_exists:
            writer.writeheader()

        for name, path, h in pending:
            if verbose:
                print(f'Processando: {name}')

            records, skipped = parse_xlsx(path)
            file_records = 0
            file_duplicates = 0
            # Chaves só entram em `existing_keys` depois que o arquivo inteiro é
            # processado (ver loop abaixo) — assim um produto repetido em duas linhas
            # do MESMO documento nunca é comparado contra si mesmo. A deduplicação só
            # vale entre arquivos diferentes (o cenário real de sobreposição de mês).
            keys_found_in_this_file = set()

            for rec in records:
                rec['arquivo_origem'] = name
                key = tuple(rec.get(field, '') for field in DUPLICATE_KEY_FIELDS)
                if key in existing_keys:
                    file_duplicates += 1
                    continue
                writer.writerow(rec)
                keys_found_in_this_file.add(key)
                file_records += 1

            existing_keys |= keys_found_in_this_file

            total_records += file_records
            total_skipped += len(skipped)
            total_duplicates += file_duplicates
            details.append({
                'name': name,
                'hash': h,
                'records': file_records,
                'duplicates': file_duplicates,
                'skipped': skipped,
            })

            if verbose:
                if file_duplicates:
                    print(f'  [!] {file_duplicates} registro(s) duplicado(s) ignorado(s).')
                if skipped:
                    print(f'  [!] {len(skipped)} registro(s) pulado(s):')
                    for s in skipped:
                        print(f'    Linha {s["line"]}: {s["reason"]}')
                if not skipped and not file_duplicates:
                    print(f'  [OK] {file_records} linhas extraídas, sem erros.')
                elif file_records > 0:
                    print(f'  [OK] {file_records} linhas adicionadas.')

    return {
        'total_records': total_records,
        'total_skipped': total_skipped,
        'total_duplicates': total_duplicates,
        'details': details,
        'output_csv': csv_path,
    }


def extrair_base01(
    raw_dir=RAW_DIR,
    output_dir=OUTPUT_DIR,
    output_csv=CONSOLIDATED_CSV,
    log_file=LOG_FILE,
    verbose=True,
):
    """Lê todos os XLSX pendentes em `raw_dir` e acrescenta ao `Base01.csv`."""
    ensure_directories(raw_dir=raw_dir, output_dir=output_dir)
    log = load_log(log_file)

    files = list_raw_xlsx_files(raw_dir=raw_dir)
    if not files:
        if verbose:
            print(f'Nenhum arquivo .xlsx/.xlsm encontrado em {raw_dir}/')
        return {'status': 'no_files', 'pending': [], 'summary': None}

    pending = build_pending_files(files, raw_dir=raw_dir, log=log)
    if not pending:
        if verbose:
            print('Todos os arquivos já foram processados. Nada de novo.')
        return {'status': 'no_pending', 'pending': [], 'summary': None}

    if verbose:
        print(f'{len(pending)} arquivo(s) novo(s) ou alterado(s) para processar.\n')

    summary = process_pending_files(pending, csv_path=output_csv, verbose=verbose)

    now = datetime.now().isoformat()
    arquivos_processados = log.setdefault('arquivos_processados', {})

    for item in summary['details']:
        arquivos_processados[item['name']] = {
            'hash': item['hash'],
            'processado_em': now,
            'registros_adicionados': item['records'],
            'registros_pulados': len(item['skipped']),
            'duplicatas_encontradas': item['duplicates'],
        }

    log.setdefault('historico_execucoes', []).append({
        'executado_em': now,
        'arquivos': [item['name'] for item in summary['details']],
        'total_registros_adicionados': summary['total_records'],
        'total_pulados': summary['total_skipped'],
        'total_duplicatas': summary['total_duplicates'],
    })

    log['ultima_atualizacao'] = now
    save_log(log, log_file)

    if verbose:
        print(
            f'\nResumo: {summary["total_records"]} linhas adicionadas, '
            f'{summary["total_skipped"]} puladas, '
            f'{summary["total_duplicates"]} duplicatas ignoradas.'
        )
        print(f'CSV: {output_csv}')
        print(f'Log: {log_file}')

    return {
        'status': 'processed',
        'pending': [name for name, _, _ in pending],
        'summary': summary,
    }


if __name__ == '__main__':
    debug_raw_directory()
    extrair_base01()
