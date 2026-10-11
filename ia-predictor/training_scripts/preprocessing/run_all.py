"""Roda o pipeline de pré-processamento e grava um relatório com o resumo de cada etapa.

  1. extrair_base01          XLSX → Base01.csv (incremental: só planilhas novas)
  2. tratamento_de_dados02   Base01.csv → BaseFormatada02.csv (limpeza genérica)
  3. classificacao03         BaseFormatada02.csv → BaseClassificada03.csv (unidade e categorias)
  4. limpeza_para_treino04   BaseClassificada03.csv → BaseTreino.csv (remove Servico e taxa
                              e mantém só as colunas que o SARIMAX do L1 usa)
  5. separa_unidades05       BaseTreino.csv → BaseTreino_<unidade>.csv (1 série por loja)
  6. remove_encomendas06     BaseClassificada03.csv → BaseTreino_<unidade>_sem_encomendas.csv
                              (ramo experimental: só vendas de CONSUMIDOR — ver docstring do
                              módulo sobre por que isso não é a decisão de escopo atual)
  10. dados_externos10       calendário diário por loja (exógenas do L1 — não depende da base
                              transacional, por isso numerada fora da sequência 1→6)

O pipeline está sendo refeito: a etapa antiga de séries diárias (build_daily_series)
saiu daqui e volta conforme for reescrita sobre a base nova. `reduce_schema.py`,
`map_taxonomy.py` (desenho anterior, L1 por `unidade x categoria`) e `clean_transactions.py`
foram removidos — superados por `tratamento_de_dados_02.py`, `classificacao_03.py` e
`limpeza_para_treino_04.py`.

Não existe mais um módulo central de constantes (`constants.py`): cada etapa define os
próprios caminhos e regras, importando de `extrair_base_01` só o que é comum a todas
(`OUTPUT_DIR`) e da etapa anterior o CSV que consome como entrada.

O relatório (`output/preprocessamento_relatorio.json`) junta o resumo de cada etapa.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.run_all
"""
import json
import os
import sys
from datetime import datetime

from .classificacao_03 import classificar
from .dados_externos_10 import build_calendar
from .extrair_base_01 import OUTPUT_DIR, extrair_base01
from .limpeza_para_treino_04 import limpar
from .remove_encomendas_06 import remover
from .separa_unidades_05 import separar
from .tratamento_de_dados_02 import tratar_dados

REPORT_JSON = os.path.join(OUTPUT_DIR, 'preprocessamento_relatorio.json')

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
    etapas['3_classificacao03'] = classificar(verbose=verbose)
    etapas['4_limpeza_para_treino04'] = limpar(verbose=verbose)
    etapas['5_separa_unidades05'] = separar(verbose=verbose)
    etapas['6_remove_encomendas06'] = remover(verbose=verbose)
    etapas['10_dados_externos10'] = build_calendar(verbose=verbose)
    rel = {'gerado_em': datetime.now().isoformat(timespec='seconds'), 'etapas': etapas}
    with open(REPORT_JSON, 'w', encoding='utf-8') as fh:
        json.dump(rel, fh, ensure_ascii=False, indent=2, default=str)

    if verbose:
        print(f'\n[run_all] Relatório: {REPORT_JSON}')
    return rel


if __name__ == '__main__':
    run_all()
