"""Etapa 6 do pipeline: calendário diário **por loja**, com o que se sabe de cada dia antes
de ele acontecer.

As variáveis de calendário são as únicas informações externas que ajudaram o modelo
(doc 03: erro em feriados ≈ 0, faixa de 95% 6× mais estreita, −9% de erro no ano; clima
sem ganho, por isso fica fora — EDA §4 item 19). O calendário é por loja porque as regras
diferem: só Itabirito abre no Dia das Mães e em Finados, e só Itabirito fechou em
02/01/2025.

Colunas (uma linha por `data × unidade`, de CALENDAR_START a CALENDAR_END):

  * `dia_semana` (0 = segunda … 6 = domingo) e `nome_dia`;
  * `feriado_nacional` / `nome_feriado` — BrasilAPI (inclui Carnaval e Consciência Negra);
  * `fechamento_local` — feriado municipal ou ponte observado nos dados (constants.py);
  * `data_comemorativa` — nome da data no próprio dia (Dia das Mães, Namorados, Dia da
    Mulher, Pais, Finados, Natal);
  * `abertura_excepcional` — a loja abre num dia em que estaria fechada (EDA §4 item 18);
  * **`loja_fechada`** — domingo, feriado nacional ou fechamento local, exceto abertura
    excepcional. É a variável que mais pesa (doc 03, §3.2);
  * `vespera_feriado`, `pos_feriado` — dia aberto antes/depois de um fechamento que não é
    domingo;
  * `inicio_mes` — dias 1 a 7 (semana de pagamento);
  * `janela_7d_<data>` e `dias_ate_<data>` — candidatas para a desagregação por categoria
    (EDA §3.4: o efeito das datas muda de sentido entre categorias). No L1 total não
    mostraram efeito (doc 03 §3.4) e a janela de 7 dias, sozinha, confundiu o modelo nas
    datas com abertura excepcional (doc 03 §4.3): usar junto com `abertura_excepcional`.

Entrada : `data/external/feriados_nacionais_<ano>.json` (baixado uma vez; ver
          `dados_externos.py`).
Saída   : `output/calendario_diario.csv`.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.build_calendar
"""
from datetime import date, timedelta

import pandas as pd

from .constants import (
    ABERTURA_EXCEPCIONAL, CALENDAR_CSV, CALENDAR_END, CALENDAR_START,
    FECHAMENTOS_LOCAIS_PONTUAIS, FECHAMENTOS_LOCAIS_RECORRENTES, JANELA_DATA_DIAS, UNIDADES,
)
from .dados_externos import feriados_nacionais

NOMES_DIA = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
DATAS = {  # nome da data → sufixo das colunas
    'Dia das Mães': 'maes', 'Dia dos Namorados': 'namorados', 'Dia da Mulher': 'mulher',
    'Dia dos Pais': 'pais', 'Finados': 'finados', 'Natal': 'natal',
}


def _segundo_domingo(ano: int, mes: int) -> date:
    d = date(ano, mes, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)  # 1º domingo
    return d + timedelta(days=7)


def datas_comemorativas(anos) -> pd.DataFrame:
    """Uma linha por (data comemorativa, ano)."""
    linhas = []
    for a in anos:
        linhas += [
            ('Dia das Mães', _segundo_domingo(a, 5)), ('Dia dos Namorados', date(a, 6, 12)),
            ('Dia da Mulher', date(a, 3, 8)), ('Dia dos Pais', _segundo_domingo(a, 8)),
            ('Finados', date(a, 11, 2)), ('Natal', date(a, 12, 25)),
        ]
    df = pd.DataFrame(linhas, columns=['evento', 'data'])
    df['data'] = pd.to_datetime(df['data'])
    return df


def montar_calendario(inicio: str, fim: str, feriados: pd.DataFrame,
                      unidades=UNIDADES) -> pd.DataFrame:
    """Função pura. `feriados`: colunas `data` (datetime) e `nome`."""
    idx = pd.date_range(inicio, fim, freq='D')
    anos = range(idx.min().year, idx.max().year + 2)  # +1 ano para `dias_ate_*` no fim
    fer = feriados.drop_duplicates('data').set_index('data')['nome']
    dc = datas_comemorativas(anos)
    nome_data = dc.set_index('data')['evento']

    blocos = []
    for u in unidades:
        c = pd.DataFrame({'data': idx, 'unidade': u})
        c['dia_semana'] = idx.dayofweek
        c['nome_dia'] = [NOMES_DIA[d] for d in idx.dayofweek]
        c['feriado_nacional'] = idx.isin(fer.index).astype(int)
        c['nome_feriado'] = fer.reindex(idx).fillna('').values

        recorr = {(m, d) for m, d in FECHAMENTOS_LOCAIS_RECORRENTES.get(u, [])}
        pont = set(pd.to_datetime(FECHAMENTOS_LOCAIS_PONTUAIS.get(u, [])))
        c['fechamento_local'] = [int((d.month, d.day) in recorr or d in pont) for d in idx]

        c['data_comemorativa'] = nome_data.reindex(idx).fillna('').values
        c['abertura_excepcional'] = c['data_comemorativa'].isin(ABERTURA_EXCEPCIONAL.get(u, [])).astype(int)

        domingo = c['dia_semana'] == 6
        fechado_por_regra = domingo | (c['feriado_nacional'] == 1) | (c['fechamento_local'] == 1)
        c['loja_fechada'] = (fechado_por_regra & (c['abertura_excepcional'] == 0)).astype(int)

        feriado_ou_local = ((c['feriado_nacional'] == 1) | (c['fechamento_local'] == 1)) & ~domingo \
            & (c['abertura_excepcional'] == 0)
        aberto = c['loja_fechada'] == 0
        c['vespera_feriado'] = (aberto & feriado_ou_local.shift(-1, fill_value=False)).astype(int)
        c['pos_feriado'] = (aberto & feriado_ou_local.shift(1, fill_value=False)).astype(int)
        c['inicio_mes'] = (idx.day <= 7).astype(int)

        for evento, suf in DATAS.items():
            dias = dc.loc[dc['evento'] == evento, 'data'].sort_values().values
            pos = dias.searchsorted(idx.values)  # próxima ocorrência (ou o próprio dia)
            prox = pd.to_datetime(dias[pos])
            ate = (prox - idx).days
            c[f'dias_ate_{suf}'] = ate
            c[f'janela_7d_{suf}'] = (ate < JANELA_DATA_DIAS).astype(int)
        blocos.append(c)
    return pd.concat(blocos, ignore_index=True)


def build_calendar(output_path: str = CALENDAR_CSV, inicio: str = CALENDAR_START,
                   fim: str = CALENDAR_END, verbose: bool = True) -> dict:
    anos = range(pd.Timestamp(inicio).year, pd.Timestamp(fim).year + 1)
    cal = montar_calendario(inicio, fim, feriados_nacionais(anos))
    grava = cal.copy()
    grava['data'] = grava['data'].dt.strftime('%Y-%m-%d')
    grava.to_csv(output_path, sep=';', index=False, encoding='utf-8')

    resumo = {'periodo': [inicio, fim], 'linhas': int(len(cal)), 'por_unidade': {}}
    for u, g in cal.groupby('unidade'):
        uteis = g[g['dia_semana'] < 6]
        resumo['por_unidade'][u] = {
            'dias_loja_fechada': int(g['loja_fechada'].sum()),
            'feriados_nacionais_seg_sab': int(uteis['feriado_nacional'].sum()),
            'fechamentos_locais': int(g['fechamento_local'].sum()),
            'aberturas_excepcionais': g.loc[g['abertura_excepcional'] == 1, 'data'].dt.strftime('%Y-%m-%d').tolist(),
        }
    if verbose:
        print(f'[build_calendar] Arquivo gerado: {output_path} ({len(cal):,} linhas)'.replace(',', '.'))
        for u, r in resumo['por_unidade'].items():
            print(f'[build_calendar] {u}: {r["dias_loja_fechada"]} dias fechada · '
                  f'{r["feriados_nacionais_seg_sab"]} feriados nacionais seg–sáb · '
                  f'{r["fechamentos_locais"]} fechamentos locais · '
                  f'{len(r["aberturas_excepcionais"])} aberturas excepcionais')
    return resumo


if __name__ == '__main__':
    build_calendar()
