"""Separa a `BaseTreino.csv` (saída da Etapa 4) em 1 CSV por `unidade`, para o treino
independente do SARIMAX do L1 (uma série por loja — ver `04-treino_l1_por_loja.md`).

A base única misturava as 2 séries (`unidade` como coluna); o treino por loja precisa de
cada série isolada, sem a coluna `unidade` (constante dentro do arquivo, então deixa de
ser necessária).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.separa_unidades_05
"""
import json
import os
from datetime import datetime

import pandas as pd

from .extrair_base_01 import OUTPUT_DIR
from .limpeza_para_treino_04 import CLEAN_CSV

SEPARA_REPORT_JSON = os.path.join(OUTPUT_DIR, 'separa_unidades_resumo.json')

# Unidade → sufixo do arquivo de saída (mesmos slugs de `LOJAS_COORD` em dados_externos_10.py).
UNIDADE_SLUG = {
    'Jardim Canadá': 'jardim_canada',
    'Itabirito': 'itabirito',
}


def separar(
    input_csv: str = CLEAN_CSV,
    output_dir: str = OUTPUT_DIR,
    report_json: str = SEPARA_REPORT_JSON,
    verbose: bool = True,
) -> dict:
    df = pd.read_csv(input_csv, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
    linhas_lidas = len(df)

    arquivos = {}
    for unidade, slug in UNIDADE_SLUG.items():
        parte = df.loc[df['unidade'] == unidade].drop(columns=['unidade'])
        output_csv = os.path.join(output_dir, f'BaseTreino_{slug}.csv')
        parte.to_csv(output_csv, sep=';', index=False, encoding='utf-8')
        arquivos[unidade] = {'output_csv': output_csv, 'linhas': len(parte)}

    resumo = {
        'executado_em': datetime.now().isoformat(),
        'input_csv': input_csv,
        'linhas_lidas': linhas_lidas,
        'por_unidade': arquivos,
    }
    with open(report_json, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f'[separa_unidades] {linhas_lidas} linhas lidas de {input_csv}')
        for unidade, info in arquivos.items():
            print(f'[separa_unidades] {unidade}: {info["linhas"]} linhas em {info["output_csv"]}')
        print(f'[separa_unidades] resumo em {report_json}')
    return resumo


if __name__ == '__main__':
    separar()
