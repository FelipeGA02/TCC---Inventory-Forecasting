import csv
import os
import sys
from datetime import datetime

if __name__ == '__main__' and __package__ is None:
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from src.utils import (
    FIELDS, RAW_DIR, PROCESSED_DIR, OUTPUT_CSV, CONTROL_FILE,
    file_hash, load_control, save_control,
)
from src.data.parser import parse_xlsx

def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    control = load_control(CONTROL_FILE)

    files = sorted([
        f for f in os.listdir(RAW_DIR)
        if f.lower().endswith(('.xlsx', '.xlsm'))
    ])

    if not files:
        print('No .xlsx files found in data/raw/')
        return

    pending = []
    for name in files:
        path = os.path.join(RAW_DIR, name)
        h = file_hash(path)
        entry = control.get(name)
        if entry and entry.get('hash') == h:
            continue
        pending.append((name, path, h))

    if not pending:
        print('All files already processed. Nothing new.')
        return

    print(f'{len(pending)} new file(s) to process.\n')

    csv_exists = os.path.exists(OUTPUT_CSV)
    total_records = 0
    total_skipped = 0

    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter=';')
        if not csv_exists:
            writer.writeheader()

        for name, path, h in pending:
            print(f'Processing: {name}')
            records, skipped = parse_xlsx(path)

            for rec in records:
                rec['arquivo_origem'] = name
                writer.writerow(rec)

            total_records += len(records)
            total_skipped += len(skipped)

            if skipped:
                print(f'  [!] {len(skipped)} record(s) skipped:')
                for s in skipped:
                    print(f'    Line {s["line"]}: {s["reason"]}')
                    print(f'      Content: {s["content"]}')
            else:
                print(f'  [OK] {len(records)} rows extracted, no errors.')

            control[name] = {
                'hash': h,
                'processed_at': datetime.now().isoformat(),
                'records': len(records),
                'skipped': len(skipped),
            }

    save_control(control, CONTROL_FILE)
    print(f'\nSummary: {total_records} rows added, {total_skipped} skipped.')
    print(f'CSV: {OUTPUT_CSV}')


if __name__ == '__main__':
    main()