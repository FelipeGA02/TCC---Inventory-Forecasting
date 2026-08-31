"""Etapa 3 do pipeline: deriva `unidade`, `categoria` (nivel L1) e `categoria_fina`.

A camada L1 da modelagem agrupa por `unidade x categoria` (serie diaria). Nenhuma coluna
de agrupamento existe na base transacional — esta etapa as constroi a partir das tabelas
de/para versionadas em `taxonomy/`.

  * `unidade`        — de `empresa` (3 lojas, confirmado com a parceira em 2026-08-30).
  * `categoria`      — nivel L1 do modelo: 3 categorias de demanda
                       (Grama / Plantas de corte / Produtos de jardim) + "Servico e taxa"
                       (nao-produto, excluir da serie). Ver 01-pre_processing.md §5 / ADR-011.
  * `categoria_fina` — classificacao detalhada (~10 rotulos) para EDA e desagregacao L2.

Entrada : `output/contas_a_receber_sem_colunas.csv` (Etapa 2, 9 colunas).
          O de/para de `produto_nome` (removido na Etapa 2) vem do CSV da Etapa 1.
Saida   : `output/contas_a_receber_taxonomia.csv` (12 colunas: as 9 + `unidade` +
          `categoria` + `categoria_fina`) — entrada de
          `prepare_daily_series(df, unidade, categoria)`.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.map_taxonomy
"""
import pandas as pd

from .constants import CONSOLIDATED_CSV, REDUCED_CSV, TAXONOMY_CSV
from .taxonomy.categorias import map_categoria, map_categoria_l1
from .taxonomy.unidades import map_unidade


def _load_nome_lookup(consolidated_path: str) -> dict:
    """produto_cod -> produto_nome, a partir do CSV completo da Etapa 1."""
    nomes = pd.read_csv(
        consolidated_path, sep=';', dtype=str, low_memory=False,
        usecols=['produto_cod', 'produto_nome'],
    )
    nomes = nomes.dropna(subset=['produto_cod']).drop_duplicates('produto_cod')
    return dict(zip(nomes['produto_cod'], nomes['produto_nome']))


def map_taxonomy(
    input_path: str = REDUCED_CSV,
    output_path: str = TAXONOMY_CSV,
    consolidated_path: str = CONSOLIDATED_CSV,
    verbose: bool = True,
) -> str:
    df = pd.read_csv(input_path, sep=';', dtype=str, low_memory=False)
    nome_por_cod = _load_nome_lookup(consolidated_path)

    nomes = [nome_por_cod.get(cod) for cod in df['produto_cod']]
    df['unidade'] = df['empresa'].map(map_unidade)
    df['categoria'] = [map_categoria_l1(cod, nome) for cod, nome in zip(df['produto_cod'], nomes)]
    df['categoria_fina'] = [map_categoria(cod, nome) for cod, nome in zip(df['produto_cod'], nomes)]

    df.to_csv(output_path, sep=';', index=False)

    if verbose:
        q = pd.to_numeric(df['qtdade'].str.replace(',', '.'), errors='coerce').fillna(0)
        pct_outros = 100 * q[df['categoria_fina'] == 'Outros'].sum() / q.sum() if q.sum() else 0.0
        # Pares que viram modelo L1: exclui "Servico e taxa" (nao e demanda de produto).
        demanda = df[df['categoria'] != 'Servico e taxa']
        n_pares = demanda.groupby(['unidade', 'categoria']).ngroups

        print(f'[map_taxonomy] Arquivo gerado: {output_path}')
        print(f'[map_taxonomy] {len(df):,} linhas x {len(df.columns)} colunas'.replace(',', '.'))
        print('[map_taxonomy] Linhas por unidade:')
        print(df['unidade'].value_counts().to_string())
        print('[map_taxonomy] Volume (qtdade) por categoria L1:')
        for cat, v in q.groupby(df['categoria']).sum().sort_values(ascending=False).items():
            print(f'  {cat:<20} {v:>14,.0f}'.replace(',', '.'))
        print('[map_taxonomy] Volume (qtdade) por categoria_fina:')
        for cat, v in q.groupby(df['categoria_fina']).sum().sort_values(ascending=False).items():
            print(f'  {cat:<28} {v:>14,.0f}'.replace(',', '.'))
        print(f'[map_taxonomy] Volume em "Outros" (categoria_fina): {pct_outros:.1f}%')
        print(f'[map_taxonomy] Pares unidade x categoria (modelos L1, sem Servico e taxa): {n_pares}')

        # Cobertura de historico por par — quantos DIAS distintos tem venda. O L1 exige
        # >= 180 (MIN_OBSERVATIONS_DAYS); pares abaixo disso viram `insufficient_data`.
        dt = pd.to_datetime(demanda['emissao'], dayfirst=True, errors='coerce')
        dias = (demanda.assign(_d=dt.dt.normalize())
                       .dropna(subset=['_d'])
                       .groupby(['unidade', 'categoria'])['_d'].nunique()
                       .sort_values())
        abaixo = dias[dias < 180]
        print(f'[map_taxonomy] Dias com venda por par: min={dias.min()}, '
              f'max={dias.max()}, pares < 180 dias: {len(abaixo)}')
        for (u, c), d in abaixo.items():
            print(f'  [insufficient_data] {u} x {c}: {d} dias')

    return output_path


if __name__ == '__main__':
    map_taxonomy()
