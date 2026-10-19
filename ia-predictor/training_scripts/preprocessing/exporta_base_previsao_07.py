"""Etapa 7: publica em `ia-predictor/data/processed/` a base que o backend de previsao le.

E a ponte entre o pre-processamento (que roda em `training_scripts/`) e o backend
(`backend/services/forecast_service.py`). O backend nao conhece os CSVs intermediarios:
le so o que esta etapa grava.

Arquivos gravados em `data/processed/`:

  * `vendas_diarias.csv` — uma linha por `unidade x data x categoria x produto_cod`, com
    `qtd_fluxo` (venda do dia a dia) e `qtd_encomenda` (vendas > 2.000 un. no documento,
    ADR-013). Sem `Servico e taxa`. Nenhum dado de cliente: so produto e quantidade;
  * `calendario_diario.csv` — copia do calendario por loja da Etapa 10 (exogenas);
  * `manifesto.json` — periodo, contagens e o hash SHA-256 dos dois arquivos, que o backend
    usa para saber se a base mudou desde a ultima previsao.

A marcacao de encomenda e a mesma da Etapa 6 (`marcar_encomendas`), aplicada sobre a
`BaseClassificada03.csv`.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.exporta_base_previsao_07
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime

import pandas as pd

from .classificacao_03 import CLASSIFIED_CSV
from .dados_externos_10 import CALENDAR_CSV
from .extrair_base_01 import _IA_PREDICTOR_ROOT
from .limpeza_para_treino_04 import CATEGORIA_NAO_PRODUTO
from .remove_encomendas_06 import LIMIAR_QTD_VENDA, marcar_encomendas

PROCESSED_DIR = os.path.join(_IA_PREDICTOR_ROOT, 'data', 'processed')
VENDAS_CSV = os.path.join(PROCESSED_DIR, 'vendas_diarias.csv')
CALENDARIO_CSV = os.path.join(PROCESSED_DIR, 'calendario_diario.csv')
MANIFESTO_JSON = os.path.join(PROCESSED_DIR, 'manifesto.json')

COLUNAS_LIDAS = ['unidade', 'emissao', 'doc_numero', 'produto_cod', 'produto_nome',
                 'qtdade', 'categoria']
COLUNAS_SAIDA = ['unidade', 'data', 'categoria', 'produto_cod', 'produto_nome',
                 'qtd_fluxo', 'qtd_encomenda']


def _sha256(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, 'rb') as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b''):
            h.update(bloco)
    return h.hexdigest()


def vendas_diarias(df: pd.DataFrame) -> pd.DataFrame:
    """Linhas da base classificada -> venda diaria por produto, fluxo e encomenda a parte."""
    df = df[(df['categoria'] != CATEGORIA_NAO_PRODUTO) & df['emissao'].notna()].copy()
    df['encomenda'] = marcar_encomendas(df, LIMIAR_QTD_VENDA)
    df['qtd_fluxo'] = df['qtdade'].where(~df['encomenda'], 0.0)
    df['qtd_encomenda'] = df['qtdade'].where(df['encomenda'], 0.0)
    # Nome mais recente de cada produto (o cadastro muda de grafia ao longo do tempo).
    nomes = df.sort_values('emissao').groupby('produto_cod')['produto_nome'].last()
    out = (df.groupby(['unidade', 'emissao', 'categoria', 'produto_cod'], as_index=False)
           [['qtd_fluxo', 'qtd_encomenda']].sum()
           .rename(columns={'emissao': 'data'}))
    out['produto_nome'] = out['produto_cod'].map(nomes)
    return out.sort_values(['unidade', 'data', 'categoria', 'produto_cod'])[COLUNAS_SAIDA]


def exportar(input_csv: str = CLASSIFIED_CSV, calendario_csv: str = CALENDAR_CSV,
             processed_dir: str = PROCESSED_DIR, verbose: bool = True) -> dict:
    os.makedirs(processed_dir, exist_ok=True)
    df = pd.read_csv(input_csv, sep=';', usecols=COLUNAS_LIDAS, dtype=str,
                     keep_default_na=False)
    df['qtdade'] = pd.to_numeric(df['qtdade'], errors='coerce').fillna(0.0)
    df['emissao'] = pd.to_datetime(df['emissao'], errors='coerce')
    out = vendas_diarias(df)

    vendas_csv = os.path.join(processed_dir, os.path.basename(VENDAS_CSV))
    cal_csv = os.path.join(processed_dir, os.path.basename(CALENDARIO_CSV))
    out.to_csv(vendas_csv, sep=';', index=False, decimal='.', date_format='%Y-%m-%d')
    shutil.copyfile(calendario_csv, cal_csv)

    cal = pd.read_csv(cal_csv, sep=';', usecols=['data'])
    manifesto = {
        'gerado_em': datetime.now().isoformat(timespec='seconds'),
        'fonte': input_csv,
        'limiar_encomenda_qtd_venda': LIMIAR_QTD_VENDA,
        'periodo_vendas': [str(out['data'].min().date()), str(out['data'].max().date())],
        'periodo_calendario': [cal['data'].min(), cal['data'].max()],
        'linhas': int(len(out)),
        'por_unidade': {u: {'qtd_fluxo': round(float(g['qtd_fluxo'].sum()), 1),
                            'qtd_encomenda': round(float(g['qtd_encomenda'].sum()), 1),
                            'produtos': int(g['produto_cod'].nunique())}
                        for u, g in out.groupby('unidade')},
        'sha256': {'vendas_diarias.csv': _sha256(vendas_csv),
                   'calendario_diario.csv': _sha256(cal_csv)},
    }
    with open(os.path.join(processed_dir, os.path.basename(MANIFESTO_JSON)), 'w',
              encoding='utf-8') as fh:
        json.dump(manifesto, fh, ensure_ascii=False, indent=2)
    if verbose:
        print(f"[exporta_base_previsao07] {len(out):,} linhas · vendas "
              f"{manifesto['periodo_vendas'][0]} -> {manifesto['periodo_vendas'][1]} · "
              f"calendario ate {manifesto['periodo_calendario'][1]} -> {processed_dir}")
    return manifesto


if __name__ == '__main__':
    exportar()
