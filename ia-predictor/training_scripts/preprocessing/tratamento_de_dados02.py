"""Trata o `Base01.csv` (extração crua) e gera o `BaseFormatada02.csv`.

Esta etapa faz só limpeza genérica de dados, sem nenhuma regra de negócio (nada de
derivar `unidade`/`categoria`, separar encomendas ou remover colunas sem uso analítico
— isso é tratamento posterior):

  * remove linhas sem os campos essenciais para qualquer uso futuro (`produto_cod`,
    `qtdade`, `emissao`) e linhas totalmente em branco;
  * remove linhas com valor não numérico em algum campo numérico (lixo de parsing,
    ex.: rodapé do relatório "impresso em 14/04/2026 10:36 ... X/951" capturado pela
    Etapa 1 como se fosse uma linha de produto);
  * padroniza texto: remove espaços nas pontas e espaços duplicados no meio dos campos;
  * padroniza `emissao` de `dd/mm/aaaa` (formato do XLSX) para ISO `aaaa-mm-dd`, que não
    é ambíguo e já vem ordenável como string;
  * converte os campos numéricos (`qtdade`, `vl_unit`, `vl_total`, `vl_desconto`,
    `tot_liq`, `icms_ret`, `total_liquido_doc`), hoje texto em formato BR (vírgula
    decimal, herdado do parser da Etapa 1), para `float` de fato.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.tratamento_de_dados02
"""
import re

import pandas as pd

from .constants import CONSOLIDATED_CSV, FORMATTED_CSV

CAMPOS_OBRIGATORIOS = ['produto_cod', 'qtdade', 'emissao']
CAMPOS_NUMERICOS = [
    'qtdade', 'vl_unit', 'vl_total', 'vl_desconto', 'tot_liq', 'icms_ret', 'total_liquido_doc',
]

_ESPACOS = re.compile(r'\s+')


def _padronizar_texto(valor: str) -> str:
    """Remove espaços nas pontas e colapsa espaços duplicados no meio."""
    if not isinstance(valor, str):
        return valor
    return _ESPACOS.sub(' ', valor.strip())


def _para_float(valor: str):
    """Converte número em formato BR ('1.234,56' ou '54') para float.

    Retorna `None` se o valor não for numérico (lixo de parsing, ex.: rodapé do
    relatório capturado como linha de produto) — a linha é descartada depois.
    """
    if valor is None or valor == '':
        return 0.0
    try:
        return float(valor.replace('.', '').replace(',', '.'))
    except ValueError:
        return None


def _emissao_para_iso(valor: str) -> str:
    """Converte 'dd/mm/aaaa' para 'aaaa-mm-dd'. Mantém o valor original se não casar o padrão."""
    partes = valor.split('/')
    if len(partes) != 3:
        return valor
    dia, mes, ano = partes
    return f'{ano}-{mes}-{dia}'


def tratar_dados(
    input_csv: str = CONSOLIDATED_CSV,
    output_csv: str = FORMATTED_CSV,
    verbose: bool = True,
) -> dict:
    df = pd.read_csv(input_csv, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
    linhas_lidas = len(df)

    for col in df.columns:
        df[col] = df[col].map(_padronizar_texto)

    vazias = df[CAMPOS_OBRIGATORIOS].apply(lambda col: col.str.strip() == '').any(axis=1)
    df = df.loc[~vazias].copy()
    linhas_vazias = linhas_lidas - len(df)

    df['emissao'] = df['emissao'].map(_emissao_para_iso)

    for col in CAMPOS_NUMERICOS:
        df[col] = df[col].map(_para_float)

    invalidas = df[CAMPOS_NUMERICOS].isna().any(axis=1)
    linhas_invalidas = int(invalidas.sum())
    df = df.loc[~invalidas].copy()

    df.to_csv(output_csv, sep=';', index=False, encoding='utf-8')

    resumo = {
        'linhas_lidas': linhas_lidas,
        'linhas_removidas_campo_vazio': linhas_vazias,
        'linhas_removidas_valor_invalido': linhas_invalidas,
        'linhas_gravadas': len(df),
        'output_csv': output_csv,
    }
    if verbose:
        print(f'[tratamento_de_dados02] {linhas_lidas} linhas lidas de {input_csv}')
        print(f'[tratamento_de_dados02] {linhas_vazias} linha(s) removida(s) '
              f'(campo obrigatório vazio: {", ".join(CAMPOS_OBRIGATORIOS)})')
        print(f'[tratamento_de_dados02] {linhas_invalidas} linha(s) removida(s) '
              f'(valor não numérico em {", ".join(CAMPOS_NUMERICOS)})')
        print(f'[tratamento_de_dados02] {len(df)} linhas gravadas em {output_csv}')
    return resumo


if __name__ == '__main__':
    tratar_dados()
