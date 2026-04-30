import csv
import os
from datetime import datetime

try:
    from ..utils import (
        FIELDS, RAW_DIR, PROCESSED_DIR, OUTPUT_CSV, LOG_FILE,
        file_hash, load_log, save_log, load_existing_record_keys,
    )
    from .parser import parse_xlsx
except ImportError:
    from src.utils import (
        FIELDS, RAW_DIR, PROCESSED_DIR, OUTPUT_CSV, LOG_FILE,
        file_hash, load_log, save_log, load_existing_record_keys,
    )
    from src.data.parser import parse_xlsx

DUPLICATE_KEY_FIELDS = ('doc_numero', 'produto_cod')


def debug_raw_directory(raw_dir=RAW_DIR):
    print(f"\n=== DEBUG: Checking {raw_dir} ===")
    if not os.path.exists(raw_dir):
        print(f"  [!] Directory does NOT exist: {raw_dir}")
        return

    print(f"  [OK] Directory exists")
    all_files = os.listdir(raw_dir)
    print(f"  Total files: {len(all_files)}")

    if all_files:
        print("  Files present:")
        for f in all_files:
            is_xlsx = f.lower().endswith(('.xlsx', '.xlsm'))
            status = "[XLSX]" if is_xlsx else "[OTHER]"
            print(f"    {status} {f}")
    else:
        print("  Directory is empty")
    print()


def ensure_directories(raw_dir=RAW_DIR, processed_dir=PROCESSED_DIR):
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)


def list_raw_xlsx_files(raw_dir=RAW_DIR):
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir, exist_ok=True)
        return []

    all_files = os.listdir(raw_dir)
    return sorted(f for f in all_files if f.lower().endswith(('.xlsx', '.xlsm')))


def build_pending_files(file_names, raw_dir=RAW_DIR, log=None):
    """Return files not yet registered in the log or whose hash changed."""
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


def process_pending_files(pending, csv_path=OUTPUT_CSV, verbose=True):
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
                print(f'Processing: {name}')

            records, skipped = parse_xlsx(path)
            file_records = 0
            file_duplicates = 0

            for rec in records:
                rec['arquivo_origem'] = name
                key = tuple(rec.get(field, '') for field in DUPLICATE_KEY_FIELDS)
                if key in existing_keys:
                    file_duplicates += 1
                    continue
                writer.writerow(rec)
                existing_keys.add(key)
                file_records += 1

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
                        print(f'      Conteúdo: {s["content"]}')
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


def preprocess_raw_data_by_month(
    raw_dir=RAW_DIR,
    processed_dir=PROCESSED_DIR,
    output_csv=OUTPUT_CSV,
    log_file=LOG_FILE,
    verbose=True,
):
    ensure_directories(raw_dir=raw_dir, processed_dir=processed_dir)
    log = load_log(log_file)

    files = list_raw_xlsx_files(raw_dir=raw_dir)
    if not files:
        if verbose:
            all_files = os.listdir(raw_dir) if os.path.exists(raw_dir) else []
            print(f'Nenhum arquivo .xlsx/.xlsm encontrado em {raw_dir}/')
            if all_files:
                print(f'  Arquivos presentes: {all_files}')
        return {'status': 'no_files', 'pending': [], 'summary': None}

    pending = build_pending_files(files, raw_dir=raw_dir, log=log)
    if not pending:
        if verbose:
            print('Todos os arquivos já foram processados. Nada de novo.')
        return {'status': 'no_pending', 'pending': [], 'summary': None}

    if verbose:
        print(f'{len(pending)} arquivo(s) novo(s) para processar.\n')

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
