"""Trata o `Base01.csv` (extração crua) e gera o `BaseFormatada02.csv`.

Esta etapa faz só limpeza genérica de dados, sem nenhuma regra de negócio (nada de
derivar `unidade`/`categoria`, separar encomendas grandes ou remover colunas sem uso analítico
— isso é tratamento posterior):

  * padroniza texto: remove espaços nas pontas e espaços duplicados no meio dos campos;
  * corrige o cliente sem nome: o relatório traz `Cliente: 3655 -` e a Etapa 1 grava o
    código no `cliente_nome` (com `cliente_cod` vazio). Aqui o código volta para
    `cliente_cod` e o nome fica vazio;
  * remove linhas sem os campos essenciais para qualquer uso futuro (`produto_cod`,
    `qtdade`, `emissao`);
  * valida `emissao` como data de calendário (`dd/mm/aaaa`; 31/02 ou texto fora do padrão
    são descartados e contados) e grava em ISO `aaaa-mm-dd`, que não é ambíguo e já vem
    ordenável como string;
  * converte os campos numéricos (`qtdade`, `vl_unit`, `vl_total`, `vl_desconto`,
    `tot_liq`, `icms_ret`, `total_liquido_doc`), hoje texto em formato BR (vírgula
    decimal, herdado da Etapa 1), para `float`. Linha com valor não numérico é removida
    (lixo de parsing, ex.: rodapé do relatório capturado como linha de produto). Campo
    vazio vira 0: é o esperado em `vl_desconto` e `icms_ret`; nos demais é contado como
    alerta no resumo;
  * grava o resumo com a contagem de cada regra em `tratamento_de_dados02_resumo.json`.

O que esta etapa NÃO faz, de propósito:

  * não remove linhas repetidas iguais. São vendas reais: o mesmo produto lançado mais de
    uma vez no mesmo cupom (1.478 linhas), e o `total_liquido_doc` só fecha contando todas;
  * não tira zeros à esquerda de `produto_cod`: `20` (AMEIXA) e `0000000000020` (PRESILHA)
    são produtos diferentes. O código é lido e gravado como texto.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.tratamento_de_dados02
"""
import json
import os
import re
from datetime import datetime

import pandas as pd

from .extrair_base_01 import CONSOLIDATED_CSV, OUTPUT_DIR

FORMATTED_CSV = os.path.join(OUTPUT_DIR, 'BaseFormatada02.csv')
FORMATTED_REPORT_JSON = os.path.join(OUTPUT_DIR, 'tratamento_de_dados02_resumo.json')

CAMPOS_OBRIGATORIOS = ['produto_cod', 'qtdade', 'emissao']
CAMPOS_NUMERICOS = [
    'qtdade', 'vl_unit', 'vl_total', 'vl_desconto', 'tot_liq', 'icms_ret', 'total_liquido_doc',
]
# Campos numéricos em que vazio = 0 é o normal (sem desconto, sem ICMS retido).
VAZIO_ZERO_ESPERADO = ['vl_desconto', 'icms_ret']

_ESPACOS = re.compile(r'\s+')
_CLIENTE_SEM_NOME = re.compile(r'^(\d+)\s*-$')


def _padronizar_texto(valor: str) -> str:
    """Remove espaços nas pontas e colapsa espaços duplicados no meio."""
    if not isinstance(valor, str):
        return valor
    return _ESPACOS.sub(' ', valor.strip())


def _corrigir_cliente_sem_nome(df: pd.DataFrame) -> int:
    """'3655 -' em `cliente_nome` com `cliente_cod` vazio → código 3655, nome vazio."""
    codigo = df['cliente_nome'].str.extract(_CLIENTE_SEM_NOME, expand=False)
    alvo = (df['cliente_cod'] == '') & codigo.notna()
    df.loc[alvo, 'cliente_cod'] = codigo[alvo]
    df.loc[alvo, 'cliente_nome'] = ''
    return int(alvo.sum())


def _para_float(coluna: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Converte números em formato BR ('1.234,56' ou '54') para float.

    Devolve (valores, vazio, invalido): vazio vira 0; invalido marca o texto que não é
    número (a linha é descartada depois).
    """
    vazio = coluna == ''
    texto = coluna.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    valores = pd.to_numeric(texto.where(~vazio), errors='coerce')
    invalido = valores.isna() & ~vazio
    return valores.fillna(0.0), vazio, invalido


def tratar_dados(
    input_csv: str = CONSOLIDATED_CSV,
    output_csv: str = FORMATTED_CSV,
    report_json: str = FORMATTED_REPORT_JSON,
    verbose: bool = True,
) -> dict:
    df = pd.read_csv(input_csv, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
    linhas_lidas = len(df)

    for col in df.columns:
        df[col] = df[col].map(_padronizar_texto)

    clientes_corrigidos = _corrigir_cliente_sem_nome(df)

    vazias = (df[CAMPOS_OBRIGATORIOS] == '').any(axis=1)
    df = df.loc[~vazias].copy()

    datas = pd.to_datetime(df['emissao'], format='%d/%m/%Y', errors='coerce')
    data_invalida = datas.isna()
    exemplos_data_invalida = df.loc[data_invalida, 'emissao'].unique()[:10].tolist()
    df = df.loc[~data_invalida].copy()
    df['emissao'] = datas[~data_invalida].dt.strftime('%Y-%m-%d')

    invalidas = pd.Series(False, index=df.index)
    vazios = {}
    for col in CAMPOS_NUMERICOS:
        df[col], vazios[col], invalido = _para_float(df[col])
        invalidas |= invalido
    # Vazio contado só nas linhas que ficam na base.
    vazios_por_campo = {col: int((vazio & ~invalidas).sum()) for col, vazio in vazios.items()}
    df = df.loc[~invalidas].copy()

    df.to_csv(output_csv, sep=';', index=False, encoding='utf-8')

    resumo = {
        'executado_em': datetime.now().isoformat(),
        'input_csv': input_csv,
        'output_csv': output_csv,
        'linhas_lidas': linhas_lidas,
        'clientes_sem_nome_corrigidos': clientes_corrigidos,
        'linhas_removidas': {
            'campo_obrigatorio_vazio': int(vazias.sum()),
            'data_invalida': int(data_invalida.sum()),
            'valor_nao_numerico': int(invalidas.sum()),
        },
        'exemplos_data_invalida': exemplos_data_invalida,
        'vazio_virou_zero': {
            'esperado': {c: vazios_por_campo[c] for c in VAZIO_ZERO_ESPERADO},
            'alerta': {c: vazios_por_campo[c] for c in CAMPOS_NUMERICOS
                       if c not in VAZIO_ZERO_ESPERADO},
        },
        'linhas_gravadas': len(df),
    }
    with open(report_json, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    if verbose:
        removidas = resumo['linhas_removidas']
        print(f'[tratamento_de_dados02] {linhas_lidas} linhas lidas de {input_csv}')
        print(f'[tratamento_de_dados02] {clientes_corrigidos} cliente(s) sem nome corrigido(s)')
        print(f'[tratamento_de_dados02] removidas: {removidas["campo_obrigatorio_vazio"]} '
              f'(campo obrigatório vazio), {removidas["data_invalida"]} (data inválida), '
              f'{removidas["valor_nao_numerico"]} (valor não numérico)')
        alerta_vazio = {c: n for c, n in resumo['vazio_virou_zero']['alerta'].items() if n}
        if alerta_vazio:
            print(f'[tratamento_de_dados02] [!] campo numérico vazio virou 0: {alerta_vazio}')
        print(f'[tratamento_de_dados02] {len(df)} linhas gravadas em {output_csv}')
        print(f'[tratamento_de_dados02] resumo em {report_json}')
    return resumo


if __name__ == '__main__':
    tratar_dados()
