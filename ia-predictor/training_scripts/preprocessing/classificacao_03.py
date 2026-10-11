"""Classifica a `BaseFormatada02.csv` e gera a `BaseClassificada03.csv`.

Acrescenta as colunas de agrupamento que a base transacional não tem, a partir das tabelas
de/para versionadas em `taxonomy/`:

  * `unidade`          de `empresa` (3 CNPJs → 2 lojas: o Garden Center é Jardim Canadá,
                       confirmado com o cliente). Empresa sem de/para vira "Desconhecida";
  * `categoria_fina`   classificação detalhada (~10 rótulos) pela cascata de
                       `taxonomy/categorias.py`: de/para por código → regra pelo nome →
                       "Outros";
  * `categoria`        nível de desagregação da L2: Grama, Flores de corte, Produtos de
                       jardim e "Servico e taxa" (não é produto);
  * `grupo`            vocabulário do cliente (Grama, Flores de corte, Plantas diversas,
                       Insumos e acessórios), para apresentar a previsão;
  * `origem_categoria` como a `categoria_fina` foi decidida: `codigo` (de/para por
                       produto_cod), `nome` (regra sobre o nome) ou `padrao` (nenhuma regra
                       casou → "Outros"). Serve para auditar e priorizar a curadoria.

A classificação é feita por PRODUTO, não por linha: cada `produto_cod` recebe uma categoria
só, decidida pelo nome mais recente do código (o da última venda). 12 códigos mudaram de
nome no período; se cada linha usasse o próprio nome, um mesmo SKU poderia cair em duas
categorias e partir sua série na desagregação. O resumo lista os códigos em que o nome
antigo daria outra categoria.

Também grava `produtos_classificados03.csv`, uma linha por produto (nome de referência,
categorias, origem, volume, primeira e última venda, lojas), para a curadoria da
taxonomia com a floricultura.

O que esta etapa NÃO faz, de propósito: não remove linha nenhuma. "Servico e taxa"
(frete, mão de obra), unidade "Desconhecida" e devoluções continuam na base e saem, ou são
tratadas, na etapa de escopo (04). Aqui só se rotula.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.classificacao03
"""
import json
import os
from datetime import datetime

import pandas as pd

from .extrair_base_01 import OUTPUT_DIR
from .tratamento_de_dados_02 import FORMATTED_CSV
from .taxonomy.categorias import (
    CATEGORIA_DEFAULT, CATEGORIA_L1, CATEGORIA_L1_DEFAULT, CATEGORIA_POR_SKU,
    GRUPO_PRODUTO, GRUPO_PRODUTO_DEFAULT, map_categoria,
)
from .taxonomy.unidades import UNIDADE_DEFAULT, map_unidade

CLASSIFIED_CSV = os.path.join(OUTPUT_DIR, 'BaseClassificada03.csv')
CLASSIFIED_REPORT_JSON = os.path.join(OUTPUT_DIR, 'classificacao03_resumo.json')
CLASSIFIED_PRODUCTS_CSV = os.path.join(OUTPUT_DIR, 'produtos_classificados03.csv')

COLUNAS_CLASSIFICACAO = ['unidade', 'categoria', 'categoria_fina', 'grupo', 'origem_categoria']
TOP_OUTROS = 30


def _origem(produto_cod: str, categoria_fina: str) -> str:
    if produto_cod in CATEGORIA_POR_SKU:
        return 'codigo'
    if categoria_fina == CATEGORIA_DEFAULT:
        return 'padrao'
    return 'nome'


def _classificar_produtos(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Uma linha por `produto_cod`, classificada pelo nome mais recente do código.

    Devolve também os códigos em que algum nome antigo daria outra `categoria_fina`.
    """
    ordenado = df.sort_values('emissao', kind='stable')
    por_cod = ordenado.groupby('produto_cod', sort=True)
    produtos = pd.DataFrame({
        'nome_referencia': por_cod['produto_nome'].last(),
        'nomes_no_historico': por_cod['produto_nome'].nunique(),
        'linhas': por_cod.size(),
        'qtd_total': por_cod['qtd'].sum().round(2),
        'primeira_venda': por_cod['emissao'].first(),
        'ultima_venda': por_cod['emissao'].last(),
        'lojas': por_cod['unidade'].agg(lambda s: ' | '.join(sorted(s.unique()))),
    }).reset_index()

    produtos['categoria_fina'] = [map_categoria(c, n) for c, n in
                                  zip(produtos['produto_cod'], produtos['nome_referencia'])]
    produtos['categoria'] = produtos['categoria_fina'].map(CATEGORIA_L1).fillna(CATEGORIA_L1_DEFAULT)
    produtos['grupo'] = produtos['categoria_fina'].map(GRUPO_PRODUTO).fillna(GRUPO_PRODUTO_DEFAULT)
    produtos['origem_categoria'] = [_origem(c, f) for c, f in
                                    zip(produtos['produto_cod'], produtos['categoria_fina'])]

    renomeados = produtos.loc[produtos['nomes_no_historico'] > 1, ['produto_cod', 'categoria_fina']]
    pares = (df[df['produto_cod'].isin(renomeados['produto_cod'])]
             .groupby(['produto_cod', 'produto_nome'])['emissao'].max().reset_index())
    pares['categoria_pelo_nome'] = [map_categoria(c, n) for c, n in
                                    zip(pares['produto_cod'], pares['produto_nome'])]
    pares = pares.merge(renomeados, on='produto_cod')
    divergentes = []
    for cod, g in pares.groupby('produto_cod'):
        if (g['categoria_pelo_nome'] != g['categoria_fina']).any():
            divergentes.append({
                'produto_cod': cod,
                'categoria_usada': g['categoria_fina'].iloc[0],
                'nomes': {r.produto_nome: {'categoria': r.categoria_pelo_nome, 'ultima_venda': r.emissao}
                          for r in g.itertuples()},
            })
    return produtos, divergentes


def _volume(df: pd.DataFrame, por: list) -> list:
    """Linhas, quantidade e % da quantidade, agrupado por `por` (% dentro da unidade, se
    `unidade` estiver em `por`)."""
    g = df.groupby(por).agg(linhas=('qtd', 'size'), qtd=('qtd', 'sum')).reset_index()
    base = g.groupby('unidade')['qtd'].transform('sum') if 'unidade' in por and len(por) > 1 \
        else g['qtd'].sum()
    g['pct_qtd'] = (100 * g['qtd'] / base).round(2)
    g['qtd'] = g['qtd'].round(2)
    return g.sort_values(por[:-1] + ['qtd'], ascending=[True] * (len(por) - 1) + [False]) \
            .to_dict(orient='records')


def classificar(
    input_csv: str = FORMATTED_CSV,
    output_csv: str = CLASSIFIED_CSV,
    produtos_csv: str = CLASSIFIED_PRODUCTS_CSV,
    report_json: str = CLASSIFIED_REPORT_JSON,
    verbose: bool = True,
) -> dict:
    df = pd.read_csv(input_csv, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
    df['qtd'] = df['qtdade'].astype(float)

    unidade_por_empresa = {e: map_unidade(e) for e in df['empresa'].unique()}
    df['unidade'] = df['empresa'].map(unidade_por_empresa)

    produtos, divergentes = _classificar_produtos(df)
    por_cod = produtos.set_index('produto_cod')
    for col in COLUNAS_CLASSIFICACAO[1:]:
        df[col] = df['produto_cod'].map(por_cod[col])

    df.drop(columns='qtd').to_csv(output_csv, sep=';', index=False, encoding='utf-8')
    produtos.sort_values('qtd_total', ascending=False).to_csv(
        produtos_csv, sep=';', index=False, encoding='utf-8')

    sem_unidade = df[df['unidade'] == UNIDADE_DEFAULT]
    outros = produtos[produtos['categoria_fina'] == CATEGORIA_DEFAULT]
    servico = df[df['categoria'] == 'Servico e taxa']
    qtd_total = df['qtd'].sum()
    origem = produtos.groupby('origem_categoria').agg(produtos=('produto_cod', 'size'),
                                                      qtd=('qtd_total', 'sum'))
    origem['pct_qtd'] = (100 * origem['qtd'] / produtos['qtd_total'].sum()).round(2)

    resumo = {
        'executado_em': datetime.now().isoformat(),
        'input_csv': input_csv,
        'output_csv': output_csv,
        'produtos_csv': produtos_csv,
        'linhas_lidas': len(df),
        'linhas_gravadas': len(df),
        'unidade': {
            'de_para_empresa': unidade_por_empresa,
            'linhas_por_unidade': df['unidade'].value_counts().to_dict(),
            'linhas_sem_unidade': len(sem_unidade),
            'empresas_sem_de_para': sem_unidade['empresa'].value_counts().to_dict(),
        },
        'produtos': {
            'total': len(produtos),
            'com_mais_de_um_nome': int((produtos['nomes_no_historico'] > 1).sum()),
            'categoria_mudaria_pelo_nome_antigo': divergentes,
            'por_origem_categoria': origem.round(2).reset_index().to_dict(orient='records'),
        },
        'volume_por_categoria': _volume(df, ['categoria']),
        'volume_por_unidade_e_categoria': _volume(df, ['unidade', 'categoria']),
        'volume_por_categoria_fina': _volume(df, ['categoria_fina']),
        'volume_por_grupo': _volume(df, ['grupo']),
        'outros': {
            'produtos': len(outros),
            'linhas': int(outros['linhas'].sum()),
            'pct_qtd': round(100 * outros['qtd_total'].sum() / qtd_total, 2),
            'maiores_por_volume': outros.nlargest(TOP_OUTROS, 'qtd_total')[
                ['produto_cod', 'nome_referencia', 'qtd_total', 'linhas']].to_dict(orient='records'),
        },
        'servico_e_taxa': {
            'linhas': len(servico),
            'qtd': round(servico['qtd'].sum(), 2),
            'produtos': sorted(servico['produto_nome'].unique().tolist()),
        },
    }
    with open(report_json, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False, default=float)

    if verbose:
        print(f'[classificacao03] {len(df)} linhas lidas de {input_csv}')
        print(f'[classificacao03] Linhas por unidade: {resumo["unidade"]["linhas_por_unidade"]}')
        if len(sem_unidade):
            print(f'[classificacao03] [!] {len(sem_unidade)} linha(s) sem unidade: '
                  f'{resumo["unidade"]["empresas_sem_de_para"]}')
        print(f'[classificacao03] {len(produtos)} produtos; origem da categoria: '
              f'{origem["produtos"].to_dict()}')
        for d in divergentes:
            print(f'[classificacao03] [!] {d["produto_cod"]}: nome antigo daria outra categoria '
                  f'(usada: {d["categoria_usada"]})')
        print('[classificacao03] Volume (qtdade) por categoria:')
        for r in resumo['volume_por_categoria']:
            print(f'  {r["categoria"]:<20} {r["qtd"]:>14,.0f}  {r["pct_qtd"]:>6.2f}%'.replace(',', '.'))
        print(f'[classificacao03] "Outros": {len(outros)} produtos, {resumo["outros"]["pct_qtd"]}% do volume')
        print(f'[classificacao03] "Servico e taxa": {len(servico)} linhas (saem na etapa 04)')
        print(f'[classificacao03] {len(df)} linhas gravadas em {output_csv}')
        print(f'[classificacao03] produtos em {produtos_csv}')
        print(f'[classificacao03] resumo em {report_json}')
    return resumo


if __name__ == '__main__':
    classificar()
