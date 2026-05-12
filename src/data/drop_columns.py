import os
import pandas as pd
from src.utils.constants import PROCESSED_DIR

COLUMNS_TO_DROP = ['operador', 'obs', 'icms_ret', 'arquivo_origem', 'cliente_nome', 'produto_nome', 'doc_tipo']

INPUT_CSV = os.path.join(PROCESSED_DIR, 'contas_a_receber.csv')
OUTPUT_CSV = os.path.join(PROCESSED_DIR, 'contas_a_receber_sem_colunas.csv')


def drop_columns(
    input_path: str = INPUT_CSV,
    output_path: str = OUTPUT_CSV,
    columns: list = None,
    verbose: bool = True,
) -> str:
    if columns is None:
        columns = COLUMNS_TO_DROP

    df = pd.read_csv(input_path, sep=';', dtype=str, low_memory=False)

    present = [c for c in columns if c in df.columns]
    absent = [c for c in columns if c not in df.columns]

    if absent and verbose:
        print(f'[drop_columns] Colunas não encontradas (ignoradas): {absent}')

    df = df.drop(columns=present)
    df.to_csv(output_path, sep=';', index=False)

    if verbose:
        print(f'[drop_columns] Colunas removidas: {present}')
        print(f'[drop_columns] Arquivo gerado: {output_path}')
        print(f'[drop_columns] {len(df):,} linhas x {len(df.columns)} colunas')

    return output_path
