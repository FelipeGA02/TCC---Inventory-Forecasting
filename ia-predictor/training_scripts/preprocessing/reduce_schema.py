"""Etapa 2 do pipeline: remove colunas sem uso analítico para previsão de demanda.

Gera a planilha consolidada "pronta para treinamento" a partir do CSV bruto da Etapa 1
(`build_dataset.py`) — mesma decisão de colunas do protótipo original
(`src/data/drop_columns.py`, deletado no commit `ac4dd9e`). A justificativa de cada
coluna removida está em `docs/prediction/pre_processing.md`.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.reduce_schema
"""
import pandas as pd

from .constants import CONSOLIDATED_CSV, REDUCED_CSV, COLUMNS_TO_DROP


def reduce_schema(
    input_path: str = CONSOLIDATED_CSV,
    output_path: str = REDUCED_CSV,
    columns: list = None,
    verbose: bool = True,
) -> str:
    if columns is None:
        columns = COLUMNS_TO_DROP

    df = pd.read_csv(input_path, sep=';', dtype=str, low_memory=False)

    present = [c for c in columns if c in df.columns]
    absent = [c for c in columns if c not in df.columns]

    if absent and verbose:
        print(f'[reduce_schema] Colunas não encontradas (ignoradas): {absent}')

    df = df.drop(columns=present)
    df.to_csv(output_path, sep=';', index=False)

    if verbose:
        print(f'[reduce_schema] Colunas removidas: {present}')
        print(f'[reduce_schema] Arquivo gerado: {output_path}')
        print(f'[reduce_schema] {len(df):,} linhas x {len(df.columns)} colunas'.replace(',', '.'))
        print(f'[reduce_schema] Colunas restantes: {list(df.columns)}')

    return output_path


if __name__ == '__main__':
    reduce_schema()
