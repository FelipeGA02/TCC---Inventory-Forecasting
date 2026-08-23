"""Funções utilitárias de baixo nível usadas pelo parser e pelo orquestrador."""
import csv
import hashlib
import json
import os


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


def load_existing_record_keys(csv_path, key_fields=('doc_numero', 'produto_cod')):
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


def cell_str(row_map, col):
    """Extrai o valor de uma célula como string limpa (trim), tolerando None."""
    return str(row_map.get(col, '') or '').strip()
