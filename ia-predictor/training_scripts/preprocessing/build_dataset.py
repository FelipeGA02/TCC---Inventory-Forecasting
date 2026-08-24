"""Orquestra a Etapa 1 do pipeline: XLSX brutos -> CSV consolidado + log JSON.

Lê todas as planilhas de `data/raw/`, faz o parse (parser.py), deduplica registros que
aparecem repetidos EM ARQUIVOS DIFERENTES (sobreposição de datas nas bordas do mês) e
acrescenta ao CSV consolidado. A deduplicação nunca compara linhas dentro do mesmo
arquivo entre si — um produto pode aparecer mais de uma vez no mesmo documento
legitimamente (ver docs/prediction/pre_processing.md, seção 3). Cada planilha só é
reprocessada se for nova ou tiver mudado (controle por hash MD5 em
`processamento_log.json`) — permite rodar de novo com segurança sem duplicar dados.

Reconstrução de `src/data/preprocess_raw_data_by_month.py` (deletado no commit
`ac4dd9e`). Roda contra os XLSX reais de produção (`ia-predictor/data/raw/`, só
leitura) mas escreve a saída em `training_scripts/preprocessing/output/` — nunca no
`data/processed/` de produção, para nunca arriscar duplicar/corromper o CSV canônico
usado pelo backend.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.build_dataset
"""
import csv
import os
from datetime import datetime

from .constants import (
    FIELDS, RAW_DIR, OUTPUT_DIR, CONSOLIDATED_CSV, LOG_FILE, DUPLICATE_KEY_FIELDS,
)
from .helpers import file_hash, load_log, save_log, load_existing_record_keys
from .parser import parse_xlsx


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


def build_dataset(
    raw_dir=RAW_DIR,
    output_dir=OUTPUT_DIR,
    output_csv=CONSOLIDATED_CSV,
    log_file=LOG_FILE,
    verbose=True,
):
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
    build_dataset()
