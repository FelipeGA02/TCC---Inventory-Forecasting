import os
from pathlib import Path
import pandas as pd
from src.utils.constants import PROCESSED_DIR

FIELDS_TO_DISCRETIZE = ['pagamento', 'empresa', 'vendedor']

INPUT_CSV = os.path.join(PROCESSED_DIR, 'contas_a_receber_sem_colunas.csv')
OUTPUT_CSV = os.path.join(PROCESSED_DIR, 'contas_a_receber_discretizado.csv')
ENCODINGS_PATH = str(Path(__file__).parent.parent / 'utils' / 'encodings.py')


def _build_encodings(df: pd.DataFrame, fields: list) -> dict:
    encodings = {}
    for field in fields:
        if field not in df.columns:
            continue
        unique_vals = sorted(df[field].dropna().unique())
        encodings[field] = {val: i + 1 for i, val in enumerate(unique_vals)}
    return encodings


def _write_encodings_module(encodings: dict, path: str) -> None:
    lines = ['# Auto-gerado por discretize_fields.py — mapeamento de/para campos discretizados\n\n']
    for field, mapping in encodings.items():
        var_name = f'{field.upper()}_ENCODING'
        lines.append(f'{var_name} = {{\n')
        for val, code in mapping.items():
            escaped = val.replace('\\', '\\\\').replace("'", "\\'")
            lines.append(f"    '{escaped}': {code},\n")
        lines.append('}\n\n')
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def discretize_fields(
    input_path: str = INPUT_CSV,
    output_path: str = OUTPUT_CSV,
    fields: list = None,
    encodings_path: str = ENCODINGS_PATH,
    verbose: bool = True,
) -> str:
    if fields is None:
        fields = FIELDS_TO_DISCRETIZE

    df = pd.read_csv(input_path, sep=';', dtype=str, low_memory=False)

    encodings = _build_encodings(df, fields)
    _write_encodings_module(encodings, encodings_path)

    if verbose:
        print(f'[discretize_fields] Encodings salvos em: {encodings_path}')

    for field, mapping in encodings.items():
        df[field] = df[field].map(mapping)
        if verbose:
            print(f'[discretize_fields] {field} -> codigo inteiro ({len(mapping)} valores unicos)')

    df.to_csv(output_path, sep=';', index=False)

    if verbose:
        print(f'[discretize_fields] Arquivo gerado: {output_path}')
        print(f'[discretize_fields] {len(df):,} linhas x {len(df.columns)} colunas')

    return output_path
