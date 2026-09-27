"""Roda o pipeline inteiro (Etapas 1–7) e grava um relatório de qualidade.

  1. build_dataset       XLSX → contas_a_receber.csv (incremental: só planilhas novas)
  2. reduce_schema       → contas_a_receber_sem_colunas.csv
  3. map_taxonomy        → contas_a_receber_taxonomia.csv
  4. clean_transactions  → contas_a_receber_limpa.csv
  5. mark_orders         → contas_a_receber_encomendas.csv + limiares_encomenda.csv
  6. build_calendar      → calendario_diario.csv
  7. build_daily_series  → serie_diaria_unidade.csv + serie_diaria_unidade_categoria.csv

O relatório (`output/preprocessamento_relatorio.json`) junta o resumo de cada etapa e
confere três coisas:

  * **conservação** — a quantidade total é a mesma na base limpa, nas séries por unidade e
    nas séries por categoria, e balcão + encomenda = total;
  * **calendário × vendas** — dia marcado como loja fechada que teve venda, e dia útil
    aberto sem venda nenhuma (fechamento que o calendário não conhece);
  * **ADR-012** — a marcação de encomendas reproduz os números do EDA (Itabirito 80 linhas e
    36,3% do volume; Jardim Canadá 14 linhas e 1,3%).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.run_all
"""
import json
import sys
from datetime import datetime

import pandas as pd

from .build_calendar import build_calendar
from .build_daily_series import build_daily_series
from .build_dataset import build_dataset
from .clean_transactions import clean_transactions
from .constants import (
    CALENDAR_CSV, CLEAN_CSV, MIN_DIAS_L1, REPORT_JSON, SERIES_CATEGORIA_CSV, SERIES_UNIDADE_CSV,
)
from .map_taxonomy import map_taxonomy
from .mark_orders import mark_orders
from .reduce_schema import reduce_schema

# Referência do EDA 6 / ADR-012 (limiar no histórico todo, k = 5).
ADR012_ESPERADO = {'Itabirito': {'linhas_encomenda': 80, 'pct_volume_encomenda': 36.3},
                   'Jardim Canadá': {'linhas_encomenda': 14, 'pct_volume_encomenda': 1.3}}

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass


def _ler(path, **kw):
    return pd.read_csv(path, sep=';', decimal=',', encoding='utf-8', **kw)


def checagens(ordens: dict) -> dict:
    base = _ler(CLEAN_CSV, usecols=['qtdade'])
    su = _ler(SERIES_UNIDADE_CSV, parse_dates=['data'])
    sc = _ler(SERIES_CATEGORIA_CSV, parse_dates=['data'])
    cal = pd.read_csv(CALENDAR_CSV, sep=';', encoding='utf-8', parse_dates=['data'])

    tot = float(base['qtdade'].sum())
    conserv = {
        'qtd_base_limpa': tot,
        'qtd_series_unidade': float(su['qtd_total'].sum()),
        'qtd_series_categoria': float(sc['qtd_total'].sum()),
        'balcao_mais_encomenda_igual_total': bool(
            ((su['qtd_balcao'] + su['qtd_encomenda'] - su['qtd_total']).abs() < 1e-6).all()),
    }
    conserv['ok'] = (abs(conserv['qtd_series_unidade'] - tot) < 1e-3
                     and abs(conserv['qtd_series_categoria'] - tot) < 1e-3
                     and conserv['balcao_mais_encomenda_igual_total'])

    j = su.merge(cal, on=['data', 'unidade'], how='left')
    fechada_com_venda = j[(j['loja_fechada'] == 1) & (j['qtd_total'] != 0)]
    aberta_sem_venda = j[(j['loja_fechada'] == 0) & (j['qtd_total'] == 0)]
    cal_x_venda = {
        'dias_sem_calendario': int(j['loja_fechada'].isna().sum()),
        'loja_fechada_com_venda': [f"{r.data.date()} {r.unidade} ({r.qtd_total:.0f})"
                                   for r in fechada_com_venda.itertuples()],
        'dia_aberto_sem_venda': [f"{r.data.date()} {r.unidade} ({r.nome_dia})"
                                 for r in aberta_sem_venda.itertuples()],
    }

    adr = {}
    for u, esp in ADR012_ESPERADO.items():
        obt = ordens['por_unidade'].get(u, {})
        adr[u] = {'esperado': esp, 'obtido': {k: obt.get(k) for k in esp},
                  'ok': obt.get('linhas_encomenda') == esp['linhas_encomenda']
                  and abs(obt.get('pct_volume_encomenda', -99) - esp['pct_volume_encomenda']) <= 0.2}

    dias_venda = su[su['qtd_total'] != 0].groupby('unidade')['data'].nunique()
    minimo = {u: {'dias_com_venda': int(d), 'ok': bool(d >= MIN_DIAS_L1)} for u, d in dias_venda.items()}
    return {'conservacao': conserv, 'calendario_x_vendas': cal_x_venda, 'adr012_reproducao': adr,
            'minimo_observacoes_l1': minimo}


def run_all(verbose: bool = True) -> dict:
    etapas = {}
    etapas['1_build_dataset'] = build_dataset(verbose=verbose)['status']
    etapas['2_reduce_schema'] = reduce_schema(verbose=verbose)
    etapas['3_map_taxonomy'] = map_taxonomy(verbose=verbose)
    etapas['4_clean_transactions'] = clean_transactions(verbose=verbose)
    etapas['5_mark_orders'] = mark_orders(verbose=verbose)
    etapas['6_build_calendar'] = build_calendar(verbose=verbose)
    etapas['7_build_daily_series'] = build_daily_series(verbose=verbose)
    rel = {'gerado_em': datetime.now().isoformat(timespec='seconds'), 'etapas': etapas,
           'checagens': checagens(etapas['5_mark_orders'])}
    with open(REPORT_JSON, 'w', encoding='utf-8') as fh:
        json.dump(rel, fh, ensure_ascii=False, indent=2, default=str)

    if verbose:
        c = rel['checagens']
        print(f'\n[run_all] Relatório: {REPORT_JSON}')
        print(f'[run_all] Conservação da quantidade: {"ok" if c["conservacao"]["ok"] else "FALHOU"}')
        for u, r in c['adr012_reproducao'].items():
            print(f'[run_all] ADR-012 {u}: {"ok" if r["ok"] else "DIFERENTE"} (obtido {r["obtido"]})')
        cv = c['calendario_x_vendas']
        print(f'[run_all] Calendário × vendas: {len(cv["loja_fechada_com_venda"])} dias "fechada" com venda · '
              f'{len(cv["dia_aberto_sem_venda"])} dias "aberta" sem venda')
        for u, r in c['minimo_observacoes_l1'].items():
            print(f'[run_all] {u}: {r["dias_com_venda"]} dias com venda ({"ok" if r["ok"] else "insufficient_data"})')
    return rel


if __name__ == '__main__':
    run_all()
