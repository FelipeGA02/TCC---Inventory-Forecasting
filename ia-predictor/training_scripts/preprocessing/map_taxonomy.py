"""Etapa 3 do pipeline: deriva `unidade` e `categoria` (+ `shelf_life_dias`).

A camada L1 da modelagem agrupa por `unidade x categoria` (serie diaria). Nenhuma das
duas colunas existe na base transacional — esta etapa as constroi a partir das tabelas
de/para versionadas em `taxonomy/`.

Entrada : `output/contas_a_receber_sem_colunas.csv` (Etapa 2, 9 colunas).
          O de/para de `produto_nome` (removido na Etapa 2) vem do CSV da Etapa 1.
Saida   : `output/contas_a_receber_taxonomia.csv` (11 colunas: as 9 + `unidade` +
          `categoria`) — entrada de `prepare_daily_series(df, unidade, categoria)`.
          `shelf_life_dias` NAO vai no CSV (deriva de `categoria` via
          `taxonomy.categorias.shelf_life`); pertence a config / tabela `categories`.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.map_taxonomy
"""
import pandas as pd

from .constants import CONSOLIDATED_CSV, REDUCED_CSV, TAXONOMY_CSV
from .taxonomy.categorias import map_categoria, shelf_life
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

    df['unidade'] = df['empresa'].map(map_unidade)
    df['categoria'] = [map_categoria(cod, nome_por_cod.get(cod)) for cod in df['produto_cod']]

    df.to_csv(output_path, sep=';', index=False)

    if verbose:
        q = pd.to_numeric(df['qtdade'].str.replace(',', '.'), errors='coerce').fillna(0)
        pct_outros = 100 * q[df['categoria'] == 'Outros'].sum() / q.sum() if q.sum() else 0.0
        n_pares = df.groupby(['unidade', 'categoria']).ngroups

        print(f'[map_taxonomy] Arquivo gerado: {output_path}')
        print(f'[map_taxonomy] {len(df):,} linhas x {len(df.columns)} colunas'.replace(',', '.'))
        print('[map_taxonomy] Linhas por unidade:')
        print(df['unidade'].value_counts().to_string())
        print('[map_taxonomy] Volume (qtdade) por categoria:')
        vol = q.groupby(df['categoria']).sum().sort_values(ascending=False)
        for cat, v in vol.items():
            print(f'  {cat:<28} {v:>14,.0f}  (shelf_life={shelf_life(cat)}d)'.replace(',', '.'))
        print(f'[map_taxonomy] Volume em "Outros": {pct_outros:.1f}%  '
              f'(alvo: baixo — se alto, refinar CATEGORIA_REGRAS)')
        print(f'[map_taxonomy] Pares unidade x categoria: {n_pares}')

    return output_path


if __name__ == '__main__':
    map_taxonomy()
