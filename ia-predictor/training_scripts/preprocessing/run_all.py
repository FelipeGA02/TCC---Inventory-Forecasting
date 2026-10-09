"""Roda o pipeline de pré-processamento e grava um relatório com o resumo de cada etapa.

  1. extrair_base01          XLSX → Base01.csv (incremental: só planilhas novas)
  2. tratamento_de_dados02   Base01.csv → BaseFormatada02.csv (limpeza genérica)

O pipeline está sendo refeito: as etapas antigas (reduce_schema, map_taxonomy,
clean_transactions, mark_orders, build_calendar, build_daily_series) saíram daqui e voltam
conforme forem reescritas sobre a `BaseFormatada02.csv`.

O relatório (`output/preprocessamento_relatorio.json`) junta o resumo de cada etapa.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.run_all
"""
import json
import sys
from datetime import datetime

from .constants import REPORT_JSON
from .extrair_base01 import extrair_base01
from .tratamento_de_dados02 import tratar_dados

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass


def _resumo_extracao(resultado: dict) -> dict:
    """Só os totais da Etapa 1 (o detalhe por arquivo fica em `processamento_log.json`)."""
    resumo = {'status': resultado['status'], 'arquivos_processados': resultado['pending']}
    if resultado['summary']:
        s = resultado['summary']
        resumo.update({
            'registros_adicionados': s['total_records'],
            'registros_pulados': s['total_skipped'],
            'duplicatas_ignoradas': s['total_duplicates'],
        })
    return resumo


def run_all(verbose: bool = True) -> dict:
    etapas = {}
    etapas['1_extrair_base01'] = _resumo_extracao(extrair_base01(verbose=verbose))
    etapas['2_tratamento_de_dados02'] = tratar_dados(verbose=verbose)
    rel = {'gerado_em': datetime.now().isoformat(timespec='seconds'), 'etapas': etapas}
    with open(REPORT_JSON, 'w', encoding='utf-8') as fh:
        json.dump(rel, fh, ensure_ascii=False, indent=2, default=str)

    if verbose:
        print(f'\n[run_all] Relatório: {REPORT_JSON}')
    return rel


if __name__ == '__main__':
    run_all()
