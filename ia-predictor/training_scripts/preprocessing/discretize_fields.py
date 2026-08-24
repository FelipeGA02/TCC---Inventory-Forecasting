"""Etapa 3 (opcional) do pipeline: converte categóricas nominais em colunas one-hot.

Discretiza `pagamento`, `empresa` e `vendedor` — as três colunas categóricas de baixa
cardinalidade que sobram após `reduce_schema.py` — em indicadores binários (0/1), um por
categoria, e salva as categorias geradas em `output/encodings.py`.

Por que one-hot e não código inteiro sequencial: um código sequencial (1, 2, 3...)
impõe ordem artificial a categorias nominais sem ordem natural (não existe "pagamento
5 > pagamento 3"). Isso quebra a hipótese de linearidade do SARIMAX ao usar essas
colunas como exógenas — o coeficiente passaria a interpretar a categoria como uma
escala contínua. One-hot evita isso: cada categoria vira sua própria coluna
independente. A categoria alfabeticamente mais baixa de cada campo é usada como
baseline e fica de fora do one-hot (dummy variable trap) — as demais categorias são
lidas em relação a ela.

Ver docs/prediction/pre_processing.md (seção 5) para a decisão completa.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.discretize_fields
"""
import re

import pandas as pd

from .constants import REDUCED_CSV, DISCRETIZED_CSV, ENCODINGS_FILE, FIELDS_TO_DISCRETIZE


def _slugify(value: str) -> str:
    slug = re.sub(r'[^0-9A-Za-z]+', '_', value.strip()).strip('_').upper()
    return slug or 'VAZIO'


def _one_hot_encode(df: pd.DataFrame, fields: list) -> tuple:
    categories = {}
    for field in fields:
        if field not in df.columns:
            continue

        unique_vals = sorted(df[field].dropna().unique())
        if len(unique_vals) < 2:
            continue

        baseline, *dummies = unique_vals
        categories[field] = {'baseline': baseline, 'dummies': dummies}

        for val in dummies:
            column = f'{field}_{_slugify(val)}'
            df[column] = (df[field] == val).astype(int)

        df = df.drop(columns=[field])

    return df, categories


def _write_encodings_module(categories: dict, path: str) -> None:
    lines = [
        '# Auto-gerado por discretize_fields.py — categorias one-hot por campo original.\n',
        "# 'baseline' é a categoria de referência, omitida do one-hot (dummy variable trap).\n",
        "# 'dummies' lista as categorias que viraram coluna própria, na ordem em que foram\n",
        '# geradas (coluna = f"{campo}_{categoria_normalizada}").\n\n',
    ]
    for field, info in categories.items():
        var_name = f'{field.upper()}_CATEGORIES'
        lines.append(f'{var_name} = {{\n')
        lines.append(f"    'baseline': {info['baseline']!r},\n")
        lines.append(f"    'dummies': {info['dummies']!r},\n")
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

    df, categories = _one_hot_encode(df, fields)
    _write_encodings_module(categories, encodings_path)

    if verbose:
        print(f'[discretize_fields] Categorias salvas em: {encodings_path}')
        for field, info in categories.items():
            n_categorias = len(info['dummies']) + 1
            print(
                f"[discretize_fields] {field} -> {len(info['dummies'])} colunas one-hot "
                f"({n_categorias} categorias, baseline='{info['baseline']}' omitida)"
            )

    df.to_csv(output_path, sep=';', index=False)

    if verbose:
        print(f'[discretize_fields] Arquivo gerado: {output_path}')
        print(f'[discretize_fields] {len(df):,} linhas x {len(df.columns)} colunas'.replace(',', '.'))

    return output_path


if __name__ == '__main__':
    discretize_fields()
