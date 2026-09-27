"""Etapa 7 do pipeline: séries diárias do L1 (por loja) e da desagregação (loja × categoria).

Até aqui o pipeline parava na transação, porque os parâmetros da série ainda estavam em
aberto (01-pre_processing.md §1). O EDA e os treinos na série crua os fecharam: o L1 é uma
série **por unidade** (EDA §3.11, ADR-011 §4), a venda prevista é a de **balcão** (ADR-012),
e os dias sem venda entram como zero. Esta etapa grava essas séries prontas, com as três
parcelas lado a lado, para o treino escolher o alvo sem reprocessar nada:

  * `qtd_total`     — tudo o que saiu no dia (balcão + encomendas, devoluções descontadas);
  * `qtd_balcao`    — **alvo do L1** (ADR-012): sem as linhas de encomenda;
  * `qtd_encomenda` — o fluxo sob pedido, que não é previsto pelo histórico;
  * `qtd_devolucao` — soma das linhas negativas (já incluída em total/balcão), para auditoria;
  * `n_linhas`, `n_linhas_encomenda` — contagens do dia.

O teto no 99º percentil **não** é aplicado aqui: ele só altera o treino (ADR-012, §2). A
marcação de encomenda usa o limiar da Etapa 5 (histórico todo, como na produção); no
walk-forward, recalcular a partir de `contas_a_receber_encomendas.csv` com o limiar da
janela.

As duas lojas cobrem o mesmo intervalo de datas (primeiro ao último dia da base), com todos
os dias do calendário. Para juntar com o calendário, usar `data × unidade` com
`calendario_diario.csv` (Etapa 6).

Entrada : `output/contas_a_receber_encomendas.csv` (Etapa 5).
Saídas  : `output/serie_diaria_unidade.csv` (L1) e
          `output/serie_diaria_unidade_categoria.csv` (desagregação unidade → categoria).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.build_daily_series
"""
import pandas as pd

from .constants import ORDERS_CSV, SERIES_CATEGORIA_CSV, SERIES_UNIDADE_CSV
from .mark_orders import ler_base


def agregar(linhas: pd.DataFrame, chaves: list[str], idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Função pura: soma diária por `chaves`, com todos os dias de `idx` (dias sem venda = 0)."""
    l = linhas.assign(
        qtd_balcao=linhas['qtdade'].where(linhas['encomenda'] == 0, 0.0),
        qtd_encomenda=linhas['qtdade'].where(linhas['encomenda'] == 1, 0.0),
        qtd_devolucao=linhas['qtdade'].where(linhas['qtdade'] < 0, 0.0),
    )
    g = l.groupby([*chaves, 'data']).agg(
        qtd_total=('qtdade', 'sum'), qtd_balcao=('qtd_balcao', 'sum'),
        qtd_encomenda=('qtd_encomenda', 'sum'), qtd_devolucao=('qtd_devolucao', 'sum'),
        n_linhas=('qtdade', 'size'), n_linhas_encomenda=('encomenda', 'sum'),
    )
    grupos = l[chaves].drop_duplicates().sort_values(chaves).itertuples(index=False, name=None)
    completo = pd.MultiIndex.from_tuples([(*gr, d) for gr in grupos for d in idx], names=[*chaves, 'data'])
    g = g.reindex(completo, fill_value=0).reset_index()
    for c in ('n_linhas', 'n_linhas_encomenda'):
        g[c] = g[c].astype(int)
    return g[['data', *chaves, 'qtd_total', 'qtd_balcao', 'qtd_encomenda', 'qtd_devolucao',
              'n_linhas', 'n_linhas_encomenda']]


def build_daily_series(input_path: str = ORDERS_CSV, unidade_path: str = SERIES_UNIDADE_CSV,
                       categoria_path: str = SERIES_CATEGORIA_CSV, verbose: bool = True) -> dict:
    linhas = ler_base(input_path)
    idx = pd.date_range(linhas['data'].min(), linhas['data'].max(), freq='D')
    por_unidade = agregar(linhas, ['unidade'], idx)
    por_categoria = agregar(linhas, ['unidade', 'categoria'], idx)
    for df, path in ((por_unidade, unidade_path), (por_categoria, categoria_path)):
        grava = df.copy()
        grava['data'] = grava['data'].dt.strftime('%Y-%m-%d')
        grava.to_csv(path, sep=';', decimal=',', index=False, encoding='utf-8')

    resumo = {'periodo': [str(idx.min().date()), str(idx.max().date())], 'dias': int(len(idx)), 'por_unidade': {}}
    for u, g in por_unidade.groupby('unidade'):
        b = g['qtd_balcao']
        resumo['por_unidade'][u] = {
            'qtd_total': float(g['qtd_total'].sum()), 'qtd_balcao': float(b.sum()),
            'qtd_encomenda': float(g['qtd_encomenda'].sum()),
            'dias_com_venda': int((g['qtd_total'] != 0).sum()),
            'media_balcao_dia': round(float(b.mean()), 1),
            'cv_total': round(float(g['qtd_total'].std() / g['qtd_total'].mean()), 2),
            'cv_balcao': round(float(b.std() / b.mean()), 2),
        }
    if verbose:
        print(f'[build_daily_series] Arquivos gerados: {unidade_path} · {categoria_path}')
        print(f'[build_daily_series] {resumo["periodo"][0]} → {resumo["periodo"][1]} ({len(idx)} dias)')
        for u, r in resumo['por_unidade'].items():
            print(f'[build_daily_series] {u}: {r["dias_com_venda"]} dias com venda · '
                  f'CV total {r["cv_total"]} → balcão {r["cv_balcao"]}')
    return resumo


if __name__ == '__main__':
    build_daily_series()
