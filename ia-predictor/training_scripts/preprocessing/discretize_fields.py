"""Etapa 3 (opcional) do pipeline: converte categóricas nominais em códigos inteiros.

Discretiza `pagamento`, `empresa` e `vendedor` — as três colunas categóricas de baixa
cardinalidade que sobram após `reduce_schema.py` — e salva o mapeamento de/para em
`output/encodings.py`, gerado automaticamente. Reconstrução de
`src/data/discretize_fields.py` (deletado no commit `ac4dd9e`).

Ressalva registrada em docs/prediction/pre_processing.md: um código inteiro
sequencial (1, 2, 3...) impõe uma ordem artificial a categorias nominais sem ordem
natural (ex.: forma de pagamento). Isso é aceitável se o SARIMAX as tratar como
exógenas numéricas simples, mas vale reavaliar na Fase 1 do plano de experimentos se
one-hot/dummy encoding não é mais apropriado antes de travar a decisão em produção.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.discretize_fields
"""
import pandas as pd

from .constants import REDUCED_CSV, DISCRETIZED_CSV, ENCODINGS_FILE, FIELDS_TO_DISCRETIZE


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
            escaped = val.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            lines.append(f"    '{escaped}': {code},\n")
        lines.append('}\n\n')
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def discretize_fields(
    input_path: str = REDUCED_CSV,
    output_path: str = DISCRETIZED_CSV,
    fields: list = None,
    encodings_path: str = ENCODINGS_FILE,
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
            print(f'[discretize_fields] {field} -> código inteiro ({len(mapping)} valores únicos)')

    df.to_csv(output_path, sep=';', index=False)

    if verbose:
        print(f'[discretize_fields] Arquivo gerado: {output_path}')
        print(f'[discretize_fields] {len(df):,} linhas x {len(df.columns)} colunas'.replace(',', '.'))

    return output_path


if __name__ == '__main__':
    discretize_fields()
