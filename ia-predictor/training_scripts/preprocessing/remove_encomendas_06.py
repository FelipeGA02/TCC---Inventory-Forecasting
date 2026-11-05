"""Separa cada loja em dois fluxos: a venda do dia a dia e as **encomendas grandes**.

Encomenda grande aqui e um **evento de logistica**: uma venda tao grande que a loja nao atende do
estoque de balcao e precisa encomendar do fornecedor. Ela sai do fluxo diario porque nao e
previsivel pela serie temporal — a loja sabe dela com antecedencia, por fora do historico.
Nao e descarte: as duas partes sao gravadas, e a previsao final e a soma.

A unidade de decisao e a **venda inteira** (`unidade` x `emissao` x `doc_numero`), nao a
linha. Uma encomenda grande chega como um documento com varias linhas (grama, substrato, mudas);
olhar linha a linha quebra o evento em pedacos que individualmente parecem normais, e ao
mesmo tempo marca como encomenda grande a linha avulsa de um cliente de balcao que levou um pouco
mais que a mediana da categoria.

Historico das versoes deste criterio
------------------------------------
1. `cliente_cod` (cadastrado x `CONSUMIDOR`) — descartado: a loja confirmou (2026-10-09)
   que cliente cadastrado nao e sinonimo de encomenda grande. Quem faz cadastro muitas vezes e
   cliente comum, e deve ser previsto junto com o balcao.
2. z-score modificado de Iglewicz & Hoaglin **por linha** (`marcar_outliers`, mantida
   abaixo para comparacao) — descartado como padrao: classifica pela quantidade da linha,
   sem saber a que venda ela pertence. Medido nos dados de 2026, tirava **21,6%** (Itabirito)
   e **22,2%** (Jardim Canada) do volume de `CONSUMIDOR` do fluxo diario, e ainda deixava a
   serie mais irregular que a regra por venda.
3. **tamanho da venda > 2.000 un.** (ADR-013) — limiar fixo, escolhido por sensibilidade.
4. **tamanho da venda > media + 4 desvios-padrao** (ADR-018, esta versao) — cada loja tem o
   seu limiar, tirado da distribuicao da quantidade de todos os pedidos dela (sem servico),
   em unidades: `calcular_limiares`. A planilha nova recalcula o limiar com a base mais os
   pedidos dela e classifica so as vendas inseridas; o que ja estava classificado fica.

Evidencia do criterio por venda (ADR-013): em todos os limiares testados (500 a 5.000 un.)
a regra por venda deixa o fluxo diario com CV menor **e** contamina menos o balcao que o
Hampel por linha. A evidencia do limiar por desvios esta no ADR-018 e em
`training_scripts/eda/eda_limiar_encomendas.py`.

O limiar e estimado da base inteira da loja, inclusive dos dias que o walk-forward testa: e
o "tamanho de pedido fora do comum" da loja, nao um parametro do modelo. Com 60-75 mil
pedidos por loja, uma semana nova quase nao o move (ver ADR-018).

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

# Desvios-padrao acima da media da quantidade dos pedidos da loja a partir dos quais o
# pedido e encomenda grande (ADR-018).
K_DESVIOS = 4.0

# Limiar fixo do ADR-013. Hoje so vale para a loja que ainda nao tem pedidos para calcular o
# limiar (`calcular_limiares`) e como comparacao no resumo.
LIMIAR_QTD_VENDA = 2000

# Excecao por categoria, quando a loja informar limiares diferentes. Vazio = todos usam
# LIMIAR_QTD_VENDA. Ex.: {'Flores de corte': 300}
LIMIAR_POR_CATEGORIA: dict[str, float] = {}

# Chave que identifica uma venda. `doc_numero` se repete entre meses/lojas, por isso
# `unidade` e `emissao` entram na chave; e cada tipo de documento (cupom, nota...) tem a
# propria numeracao — em 12 casos da base o mesmo numero sai no mesmo dia em dois tipos
# (ex.: C7 e N3), que sao vendas diferentes e nao podem ser somadas.
CHAVE_VENDA = ['unidade', 'emissao', 'doc_tipo', 'doc_numero']

COLUNAS_SAIDA = ['emissao', 'qtdade']

# Limiar de Iglewicz & Hoaglin (1993), usado so pela comparacao historica.
LIMIAR_Z_MODIFICADO = 3.5


def tamanho_da_venda(df: pd.DataFrame) -> pd.Series:
    """Quantidade total do documento a que cada linha pertence."""
    return df.groupby(CHAVE_VENDA)['qtdade'].transform('sum')


def tamanho_dos_pedidos(df: pd.DataFrame) -> pd.Series:
    """Quantidade total de cada pedido (documento), uma posicao por `CHAVE_VENDA`."""
    return df.groupby(CHAVE_VENDA)['qtdade'].sum()


def limiar_por_desvios(tamanhos: pd.Series, k: float = K_DESVIOS) -> float:
    """Media + `k` desvios-padrao da quantidade dos pedidos, em unidades. So pedidos com
    quantidade positiva entram (devolucao nao e tamanho de pedido); sem pedidos, o limiar
    fixo do ADR-013."""
    t = tamanhos[tamanhos > 0].astype(float)
    if len(t) < 2:
        return float(LIMIAR_QTD_VENDA)
    return float(t.mean() + k * t.std())


def calcular_limiares(df: pd.DataFrame, k: float = K_DESVIOS) -> dict:
    """Limiar de encomenda grande de cada loja (`unidade`): distribuicao da quantidade de
    todos os pedidos dela em `df` (sem as linhas de servico, que o chamador tira)."""
    return {u: limiar_por_desvios(t, k) for u, t in tamanho_dos_pedidos(df).groupby(level='unidade')}


def marcar_encomendas_por_unidade(df: pd.DataFrame, limiares: dict) -> pd.Series:
    """`True` nas linhas dos pedidos acima do limiar da sua loja (loja sem limiar: o fixo)."""
    limiar = df['unidade'].map(limiares).astype(float).fillna(float(LIMIAR_QTD_VENDA))
    return tamanho_da_venda(df) > limiar


def marcar_encomendas(df: pd.DataFrame, limiar: float = LIMIAR_QTD_VENDA,
                      por_categoria: dict | None = None) -> pd.Series:
    """`True` nas linhas que pertencem a uma venda maior que o limiar.

    A marcacao vale para a venda inteira: se o documento passa do limiar, todas as suas
    linhas saem do fluxo diario juntas — e isso que mantem o evento de logistica inteiro.
    Com `por_categoria`, o limiar de cada linha e o da sua categoria (o documento e
    comparado contra o MENOR limiar entre as categorias que ele contem, para que uma
    encomenda grande mista nao escape pelo limiar mais alto).
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


def _distribuicao(tamanhos: pd.Series) -> dict:
    """Resumo da distribuicao da quantidade dos pedidos (so os positivos)."""
    t = tamanhos[tamanhos > 0]
    return {'pedidos': int(len(t)), 'media_un': round(float(t.mean()), 2),
            'desvio_padrao_un': round(float(t.std()), 2),
            'quantis_un': {f'p{q * 100:g}': float(t.quantile(q)) for q in (0.5, 0.9, 0.99, 0.999)},
            'max_un': float(t.max())}


def _cv_diario(parte: pd.DataFrame, calendario: pd.DatetimeIndex) -> float:
    """CV da serie diaria de um fluxo, no calendario cheio (dia sem venda = 0)."""
    s = parte.groupby('emissao')['qtdade'].sum().reindex(calendario, fill_value=0.0)
    return float(s.std() / s.mean()) if s.mean() else float('nan')


def remover(
    input_csv: str = CLASSIFIED_CSV,
    output_dir: str = OUTPUT_DIR,
    report_json: str = REMOVE_REPORT_JSON,
    k: float = K_DESVIOS,
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

    tamanhos = tamanho_dos_pedidos(df)
    limiares = calcular_limiares(df, k)
    df['encomenda'] = marcar_encomendas_por_unidade(df, limiares)
    # Comparacao com os criterios anteriores, so para o resumo.
    fixo = marcar_encomendas(df, LIMIAR_QTD_VENDA, LIMIAR_POR_CATEGORIA)
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
            'comparacao_limiar_fixo_2000_adr013': {
                'vendas_encomenda': int(base.loc[fixo.loc[base.index]].groupby(CHAVE_VENDA).ngroups),
                'pct_volume_removido': round(
                    100 * base.loc[fixo.loc[base.index], 'qtdade'].sum() / vol, 1) if vol else None,
                'cv_diario_fluxo': round(_cv_diario(base.loc[~fixo.loc[base.index]], cal), 2),
            },
        }

    resumo = {
        'executado_em': datetime.now().isoformat(),
        'input_csv': input_csv,
        'metodo': f'tamanho da venda (documento): encomenda grande se a soma de qtdade do '
                  f'documento > media + {k:g} desvios-padrao da quantidade de todos os pedidos '
                  f'da loja (ADR-018)',
        'unidade_de_decisao': CHAVE_VENDA,
        'limiar_qtd_venda_por_unidade': {u: round(v, 1) for u, v in limiares.items()},
        'k_desvios': k,
        'distribuicao_dos_pedidos_por_unidade': {u: _distribuicao(t) for u, t in tamanhos.groupby(level='unidade')},
        'limiar_por_categoria': LIMIAR_POR_CATEGORIA or None,
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
        print(f'[remove_encomendas] criterio: venda (documento) > media + {k:g} desvios dos pedidos da loja: '
              + ', '.join(f'{u} {v:.0f} un.' for u, v in limiares.items()))
        for unidade, i in por_unidade.items():
            f = i['comparacao_limiar_fixo_2000_adr013']
            print(f'[remove_encomendas] {unidade}: {i["vendas_encomenda"]} encomenda(s) grande(s) em '
                  f'{i["dias_com_encomenda"]} dia(s) = {i["pct_volume_encomenda"]}% do volume '
                  f'· CV diario {i["cv_diario_total"]} -> {i["cv_diario_fluxo"]} '
                  f'(limiar fixo de 2.000: {f["vendas_encomenda"]} encomendas, {f["pct_volume_removido"]}% / '
                  f'CV {f["cv_diario_fluxo"]})')
        for unidade, a in arquivos.items():
            print(f'[remove_encomendas] {unidade}: {a["fluxo_diario_csv"]} · {a["encomendas_csv"]}')
        print(f'[remove_encomendas] resumo em {report_json}')
    return resumo


if __name__ == '__main__':
    remover()
