"""Separa cada loja em dois fluxos: a venda do dia a dia e as **encomendas grandes**.

Encomenda aqui e um **evento de logistica**: uma venda tao grande que a loja nao atende do
estoque de balcao e precisa encomendar do fornecedor. Ela sai do fluxo diario porque nao e
previsivel pela serie temporal — a loja sabe dela com antecedencia, por fora do historico.
Nao e descarte: as duas partes sao gravadas, e a previsao final e a soma.

A unidade de decisao e a **venda inteira** (`unidade` x `emissao` x `doc_numero`), nao a
linha. Uma encomenda chega como um documento com varias linhas (grama, substrato, mudas);
olhar linha a linha quebra o evento em pedacos que individualmente parecem normais, e ao
mesmo tempo marca como encomenda a linha avulsa de um cliente de balcao que levou um pouco
mais que a mediana da categoria.

Historico das tres versoes deste criterio
-----------------------------------------
1. `cliente_cod` (cadastrado x `CONSUMIDOR`) — descartado: a loja confirmou (2026-10-09)
   que cliente cadastrado nao e sinonimo de encomenda. Quem faz cadastro muitas vezes e
   cliente comum, e deve ser previsto junto com o balcao.
2. z-score modificado de Iglewicz & Hoaglin **por linha** (`marcar_outliers`, mantida
   abaixo para comparacao) — descartado como padrao: classifica pela quantidade da linha,
   sem saber a que venda ela pertence. Medido nos dados de 2026, tirava **21,6%** (Itabirito)
   e **22,2%** (Jardim Canada) do volume de `CONSUMIDOR` do fluxo diario, e ainda deixava a
   serie mais irregular que a regra por venda.
3. **tamanho da venda** (esta versao) — a regra atual.

Evidencia (base de 2026, as duas lojas). "cons. tirado" = quanto do volume de `CONSUMIDOR`
sai do fluxo diario, ou seja, contaminacao do que se quer prever:

    Itabirito (total: CV 2,35)        vendas  vol.enc.  CV fluxo  cons. tirado
      venda > 2.000 un                    93    52,1%      0,78          2,7%
      Hampel por linha (anterior)          -    61,2%      1,04         21,6%

    Jardim Canada (total: CV 1,18)
      venda > 2.000 un                   131    22,5%      0,69          3,7%
      Hampel por linha (anterior)          -    34,8%      0,87         22,2%

Em todos os limiares testados (500, 1.000, 2.000, 3.000, 5.000) a regra por venda deixa o
fluxo diario com CV menor **e** contamina menos o balcao. Ver
`docs/prediction/ADR-013-encomendas-por-tamanho-da-venda.md`.

O limiar e **fixo em unidades**, nao estimado dos dados — por isso nao precisa ser
recalculado a cada rodada do walk-forward e nao ha risco de vazamento. Em compensacao ele
e uma hipotese operacional, ainda **a confirmar com a parceira**: a partir de quantas
unidades a loja precisa encomendar do fornecedor? O numero provavelmente varia por
categoria (2.000 mudas de grama e 2.000 flores de corte nao sao o mesmo problema
logistico), e `LIMIAR_POR_CATEGORIA` ja existe para acomodar isso quando houver resposta.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.remove_encomendas_06
"""
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd

from .classificacao_03 import CLASSIFIED_CSV
from .extrair_base_01 import OUTPUT_DIR
from .limpeza_para_treino_04 import CATEGORIA_NAO_PRODUTO, UNIDADES
from .separa_unidades_05 import UNIDADE_SLUG

REMOVE_REPORT_JSON = os.path.join(OUTPUT_DIR, 'remove_encomendas_resumo.json')

# Quantidade total da VENDA (documento) a partir da qual ela conta como encomenda.
# Provisorio — a confirmar com a parceira (ver docstring).
LIMIAR_QTD_VENDA = 2000

# Excecao por categoria, quando a loja informar limiares diferentes. Vazio = todos usam
# LIMIAR_QTD_VENDA. Ex.: {'Flores de corte': 300}
LIMIAR_POR_CATEGORIA: dict[str, float] = {}

# Chave que identifica uma venda. `doc_numero` se repete entre meses/lojas, por isso
# `unidade` e `emissao` entram na chave.
CHAVE_VENDA = ['unidade', 'emissao', 'doc_numero']

COLUNAS_SAIDA = ['emissao', 'qtdade']

# Limiar de Iglewicz & Hoaglin (1993), usado so pela comparacao historica.
LIMIAR_Z_MODIFICADO = 3.5


def tamanho_da_venda(df: pd.DataFrame) -> pd.Series:
    """Quantidade total do documento a que cada linha pertence."""
    return df.groupby(CHAVE_VENDA)['qtdade'].transform('sum')


def marcar_encomendas(df: pd.DataFrame, limiar: float = LIMIAR_QTD_VENDA,
                      por_categoria: dict | None = None) -> pd.Series:
    """`True` nas linhas que pertencem a uma venda maior que o limiar.

    A marcacao vale para a venda inteira: se o documento passa do limiar, todas as suas
    linhas saem do fluxo diario juntas — e isso que mantem o evento de logistica inteiro.
    Com `por_categoria`, o limiar de cada linha e o da sua categoria (o documento e
    comparado contra o MENOR limiar entre as categorias que ele contem, para que uma
    encomenda mista nao escape pelo limiar mais alto).
    """
    tam = tamanho_da_venda(df)
    por_categoria = por_categoria or {}
    if not por_categoria:
        return tam > limiar
    limiar_linha = df['categoria'].map(por_categoria).fillna(limiar)
    limiar_venda = limiar_linha.groupby([df[c] for c in CHAVE_VENDA]).transform('min')
    return tam > limiar_venda


def marcar_outliers(qtdade: pd.Series, grupo: pd.Series,
                    limiar: float = LIMIAR_Z_MODIFICADO) -> pd.Series:
    """z-score modificado de Iglewicz & Hoaglin sobre `log1p(qtdade)`, POR LINHA.

    Criterio anterior, mantido so para a comparacao registrada no resumo — ver o historico
    na docstring do modulo. Grupo com MAD = 0 cai para o desvio medio absoluto, para ainda
    detectar o valor fora da curva sem dividir por zero.
    """
    log_qtd = np.log1p(qtdade.clip(lower=0))
    mediana = log_qtd.groupby(grupo).transform('median')
    desvio_abs = (log_qtd - mediana).abs()
    mad = desvio_abs.groupby(grupo).transform('median')
    mad = mad.where(mad > 0, desvio_abs.groupby(grupo).transform('mean'))
    z_modificado = 0.6745 * (log_qtd - mediana) / mad.replace(0, np.nan)
    return z_modificado.abs() > limiar


def _cv_diario(parte: pd.DataFrame, calendario: pd.DatetimeIndex) -> float:
    """CV da serie diaria de um fluxo, no calendario cheio (dia sem venda = 0)."""
    s = parte.groupby('emissao')['qtdade'].sum().reindex(calendario, fill_value=0.0)
    return float(s.std() / s.mean()) if s.mean() else float('nan')


def remover(
    input_csv: str = CLASSIFIED_CSV,
    output_dir: str = OUTPUT_DIR,
    report_json: str = REMOVE_REPORT_JSON,
    limiar: float = LIMIAR_QTD_VENDA,
    verbose: bool = True,
) -> dict:
    df = pd.read_csv(input_csv, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
    linhas_lidas = len(df)
    df['qtdade'] = pd.to_numeric(df['qtdade'], errors='coerce').fillna(0.0)
    df['emissao'] = pd.to_datetime(df['emissao'], errors='coerce')

    servico = df['categoria'] == CATEGORIA_NAO_PRODUTO
    fora_unidade = ~df['unidade'].isin(UNIDADES)
    sem_data = df['emissao'].isna()
    df = df.loc[~servico & ~fora_unidade & ~sem_data].copy()

    df['encomenda'] = marcar_encomendas(df, limiar, LIMIAR_POR_CATEGORIA)
    # Comparacao com o criterio anterior, so para o resumo.
    hampel = marcar_outliers(df['qtdade'], df['unidade'] + ' | ' + df['categoria'])

    arquivos, por_unidade = {}, {}
    for unidade, slug in UNIDADE_SLUG.items():
        base = df.loc[df['unidade'] == unidade]
        if base.empty:
            continue
        cal = pd.date_range(base['emissao'].min(), base['emissao'].max(), freq='D')
        fluxo = base.loc[~base['encomenda']]
        enc = base.loc[base['encomenda']]

        csv_fluxo = os.path.join(output_dir, f'BaseTreino_{slug}_sem_encomendas.csv')
        csv_enc = os.path.join(output_dir, f'BaseTreino_{slug}_encomendas.csv')
        fluxo[COLUNAS_SAIDA].to_csv(csv_fluxo, sep=';', index=False, encoding='utf-8')
        enc[COLUNAS_SAIDA].to_csv(csv_enc, sep=';', index=False, encoding='utf-8')

        vol = base['qtdade'].sum()
        arquivos[unidade] = {'fluxo_diario_csv': csv_fluxo, 'encomendas_csv': csv_enc}
        por_unidade[unidade] = {
            'vendas_encomenda': int(enc.groupby(CHAVE_VENDA).ngroups),
            'linhas_encomenda': int(len(enc)),
            'linhas_fluxo_diario': int(len(fluxo)),
            'pct_volume_encomenda': round(100 * enc['qtdade'].sum() / vol, 1) if vol else None,
            'dias_com_encomenda': int(enc['emissao'].nunique()),
            'cv_diario_total': round(_cv_diario(base, cal), 2),
            'cv_diario_fluxo': round(_cv_diario(fluxo, cal), 2),
            'comparacao_criterio_anterior_hampel_por_linha': {
                'pct_volume_removido': round(
                    100 * base.loc[hampel.loc[base.index], 'qtdade'].sum() / vol, 1) if vol else None,
                'cv_diario_fluxo': round(_cv_diario(base.loc[~hampel.loc[base.index]], cal), 2),
            },
        }

    resumo = {
        'executado_em': datetime.now().isoformat(),
        'input_csv': input_csv,
        'metodo': 'tamanho da venda (documento): encomenda se a soma de qtdade do '
                  f'documento > {limiar} unidades',
        'unidade_de_decisao': CHAVE_VENDA,
        'limiar_qtd_venda': limiar,
        'limiar_por_categoria': LIMIAR_POR_CATEGORIA or None,
        'limiar_e_fixo_sem_vazamento': True,
        'criterio_anterior': 'z-score modificado por linha (Iglewicz & Hoaglin, 1993) — '
                             'ver ADR-013 e docstring do modulo',
        'linhas_lidas': linhas_lidas,
        'linhas_removidas_servico_e_taxa': int(servico.sum()),
        'linhas_removidas_unidade_desconhecida': int(fora_unidade.sum()),
        'linhas_removidas_sem_data': int(sem_data.sum()),
        'por_unidade': por_unidade,
        'arquivos': arquivos,
    }
    with open(report_json, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f'[remove_encomendas] {linhas_lidas} linhas lidas de {input_csv}')
        print(f'[remove_encomendas] criterio: venda (documento) > {limiar} unidades')
        for unidade, i in por_unidade.items():
            h = i['comparacao_criterio_anterior_hampel_por_linha']
            print(f'[remove_encomendas] {unidade}: {i["vendas_encomenda"]} encomenda(s) em '
                  f'{i["dias_com_encomenda"]} dia(s) = {i["pct_volume_encomenda"]}% do volume '
                  f'· CV diario {i["cv_diario_total"]} -> {i["cv_diario_fluxo"]} '
                  f'(criterio anterior: {h["pct_volume_removido"]}% / CV {h["cv_diario_fluxo"]})')
        for unidade, a in arquivos.items():
            print(f'[remove_encomendas] {unidade}: {a["fluxo_diario_csv"]} · {a["encomendas_csv"]}')
        print(f'[remove_encomendas] resumo em {report_json}')
    return resumo


if __name__ == '__main__':
    remover()
