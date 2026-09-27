"""Etapa 4 do pipeline: base transacional limpa, só com demanda de produto.

Aplica as regras de negócio que o EDA e os treinos na série crua fecharam
(docs/prediction/01-pre_processing.md §6):

  * sai `Servico e taxa` (frete, taxa, mão de obra): não é demanda de produto;
  * sai linha sem data válida ou com `unidade` fora das 2 lojas (contada no relatório);
  * `emissao` (dd/mm/aaaa) vira `data` ISO (aaaa-mm-dd), para ordenar e juntar com o
    calendário sem ambiguidade;
  * `qtdade` e os valores viram número (a leitura das etapas anteriores é toda texto);
  * `devolucao` marca as linhas com quantidade negativa. Elas **ficam** na base e entram
    somadas na série (venda líquida do dia), até a floricultura responder como tratá-las
    (EDA §5, pergunta 4). São 44 linhas, volume desprezível;
  * `grupo` (vocabulário do cliente: Grama, Flores de corte, Plantas diversas, Insumos e
    acessórios) vira coluna, para o painel e para a desagregação (EDA §4, item 9);
  * o arquivo é gravado em UTF-8. As saídas antigas saíam com acentuação inconsistente
    (o EDA precisava ler tentando vários encodings).

Entrada : `output/contas_a_receber_taxonomia.csv` (Etapa 3, 12 colunas).
Saída   : `output/contas_a_receber_limpa.csv` — uma linha por (documento, produto), colunas
          `data; unidade; empresa; categoria; categoria_fina; grupo; produto_cod; qtdade;
          vl_unit; vl_total; vl_desconto; tot_liq; devolucao`.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.clean_transactions
"""
import pandas as pd

from .constants import CATEGORIA_NAO_PRODUTO, CLEAN_CSV, TAXONOMY_CSV, UNIDADES
from .taxonomy.categorias import GRUPO_PRODUTO, GRUPO_PRODUTO_DEFAULT

COLUNAS_NUMERICAS = ['qtdade', 'vl_unit', 'vl_total', 'vl_desconto', 'tot_liq']
COLUNAS_SAIDA = ['data', 'unidade', 'empresa', 'categoria', 'categoria_fina', 'grupo',
                 'produto_cod', *COLUNAS_NUMERICAS, 'devolucao']


def ler_csv_texto(path: str, **kw) -> pd.DataFrame:
    """Lê um CSV do pipeline como texto, tolerando o encoding inconsistente das saídas
    antigas (UTF-8 ou cp1252/latin-1)."""
    for enc in ('utf-8', 'latin-1'):
        try:
            return pd.read_csv(path, sep=';', dtype=str, low_memory=False, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError('utf-8/latin-1', b'', 0, 1, f'não foi possível ler {path}')


def para_numero(s: pd.Series) -> pd.Series:
    """Texto no padrão da Etapa 1 (`helpers.format_decimal`: vírgula decimal, sem separador
    de milhar) → float. Texto vazio vira 0 (célula de valor vazia = zero, não faltante)."""
    txt = s.fillna('0').astype(str).str.strip().replace('', '0')
    return pd.to_numeric(txt.str.replace(',', '.', regex=False), errors='coerce')


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica as regras da Etapa 4. Função pura: recebe a base da Etapa 3 (texto) e devolve
    a base limpa e as contagens de cada regra, para o relatório."""
    n0 = len(df)
    out = df.copy()
    for c in ('unidade', 'categoria', 'categoria_fina', 'empresa'):
        out[c] = out[c].astype(str).str.strip()

    servico = out['categoria'] == CATEGORIA_NAO_PRODUTO
    out = out[~servico]

    out['data'] = pd.to_datetime(out['emissao'], format='%d/%m/%Y', errors='coerce')
    sem_data = out['data'].isna()
    fora_unidade = ~out['unidade'].isin(UNIDADES)
    out = out[~sem_data & ~fora_unidade].copy()

    for c in COLUNAS_NUMERICAS:
        out[c] = para_numero(out[c])
    qtd_invalida = out['qtdade'].isna()
    out = out[~qtd_invalida].copy()

    out['devolucao'] = (out['qtdade'] < 0).astype(int)
    out['grupo'] = out['categoria_fina'].map(GRUPO_PRODUTO).fillna(GRUPO_PRODUTO_DEFAULT)
    out = out.sort_values(['data', 'unidade', 'produto_cod'], kind='stable')[COLUNAS_SAIDA]
    out['data'] = out['data'].dt.strftime('%Y-%m-%d')

    resumo = {
        'linhas_entrada': int(n0),
        'linhas_servico_e_taxa_removidas': int(servico.sum()),
        'linhas_sem_data_removidas': int(sem_data.sum()),
        'linhas_unidade_desconhecida_removidas': int(fora_unidade.sum()),
        'linhas_qtd_invalida_removidas': int(qtd_invalida.sum()),
        'linhas_saida': int(len(out)),
        'linhas_devolucao': int(out['devolucao'].sum()),
        'qtd_devolvida': float(out.loc[out['devolucao'] == 1, 'qtdade'].sum()),
        'qtd_total': float(out['qtdade'].sum()),
        'periodo': [out['data'].min(), out['data'].max()],
        'linhas_por_unidade': out['unidade'].value_counts().to_dict(),
        'qtd_por_categoria': out.groupby('categoria')['qtdade'].sum().round(1).to_dict(),
        'qtd_por_grupo': out.groupby('grupo')['qtdade'].sum().round(1).to_dict(),
    }
    return out, resumo


def clean_transactions(input_path: str = TAXONOMY_CSV, output_path: str = CLEAN_CSV,
                       verbose: bool = True) -> dict:
    df = ler_csv_texto(input_path)
    out, resumo = limpar(df)
    out.to_csv(output_path, sep=';', decimal=',', index=False, encoding='utf-8')
    if verbose:
        print(f'[clean_transactions] Arquivo gerado: {output_path}')
        print(f'[clean_transactions] {resumo["linhas_entrada"]:,} → {resumo["linhas_saida"]:,} linhas'.replace(',', '.'))
        print(f'[clean_transactions] Removidas: {resumo["linhas_servico_e_taxa_removidas"]} serviço/taxa, '
              f'{resumo["linhas_sem_data_removidas"]} sem data, '
              f'{resumo["linhas_unidade_desconhecida_removidas"]} unidade desconhecida, '
              f'{resumo["linhas_qtd_invalida_removidas"]} qtd inválida')
        print(f'[clean_transactions] Devoluções (qtd < 0, mantidas): {resumo["linhas_devolucao"]} linhas, '
              f'{resumo["qtd_devolvida"]:.0f} unidades')
        print(f'[clean_transactions] Período: {resumo["periodo"][0]} → {resumo["periodo"][1]}')
    return resumo


if __name__ == '__main__':
    clean_transactions()
