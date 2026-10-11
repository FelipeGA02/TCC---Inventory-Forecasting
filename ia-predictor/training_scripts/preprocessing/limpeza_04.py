"""Limpa a `BaseClassificada03.csv` e gera a `BaseLimpa04.csv`.

Faz só duas coisas:

  * remove os registros de `categoria` = "Servico e taxa" (frete, mão de obra — não é
    demanda de produto);
  * remove as colunas sem uso analítico para o treino (`COLUNAS_PARA_REMOVER`, definidas
    em `constants.py`).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.limpeza04
"""
import json
from datetime import datetime

import pandas as pd

from .constants import (
    CATEGORIA_NAO_PRODUTO, CLASSIFIED_CSV, CLEAN_CSV, CLEAN_REPORT_JSON, COLUMNS_TO_DROP,
)


def limpar(
    input_csv: str = CLASSIFIED_CSV,
    output_csv: str = CLEAN_CSV,
    report_json: str = CLEAN_REPORT_JSON,
    verbose: bool = True,
) -> dict:
    df = pd.read_csv(input_csv, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
    linhas_lidas = len(df)

    servico = df['categoria'] == CATEGORIA_NAO_PRODUTO
    df = df.loc[~servico].copy()

    colunas_removidas = [c for c in COLUMNS_TO_DROP if c in df.columns]
    df = df.drop(columns=colunas_removidas)

    df.to_csv(output_csv, sep=';', index=False, encoding='utf-8')

    resumo = {
        'executado_em': datetime.now().isoformat(),
        'input_csv': input_csv,
        'output_csv': output_csv,
        'linhas_lidas': linhas_lidas,
        'linhas_removidas_servico_e_taxa': int(servico.sum()),
        'colunas_removidas': colunas_removidas,
        'linhas_gravadas': len(df),
    }
    with open(report_json, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f'[limpeza04] {linhas_lidas} linhas lidas de {input_csv}')
        print(f'[limpeza04] {resumo["linhas_removidas_servico_e_taxa"]} linha(s) de '
              f'"{CATEGORIA_NAO_PRODUTO}" removida(s)')
        print(f'[limpeza04] colunas removidas: {colunas_removidas}')
        print(f'[limpeza04] {len(df)} linhas gravadas em {output_csv}')
        print(f'[limpeza04] resumo em {report_json}')
    return resumo


if __name__ == '__main__':
    limpar()
