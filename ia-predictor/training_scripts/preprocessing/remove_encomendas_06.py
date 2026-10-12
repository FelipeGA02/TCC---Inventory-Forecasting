"""Gera uma versão das 2 bases por loja (Etapa 5) sem os registros de `qtdade` destoantes
("encomendas") — ramo experimental para o lado da comparação do EDA item 12 (CLAUDE.md,
L1 "Vendas grandes") que isola as compras atípicas, versus o SARIMAX direto sobre a venda
total (sem remoção nenhuma).

**"Encomenda" aqui é estatística, não cadastral.** A primeira versão deste script usava
`cliente_cod` (cliente cadastrado × "CONSUMIDOR" de balcão) como proxy, mas o CLAUDE.md
registra que a loja confirmou (2026-10-09) que cliente cadastrado não é sinônimo de
encomenda — é só venda identificada, muitas vezes do tamanho normal da categoria. Quem
decide se um registro é destoante é a distribuição da própria `qtdade`, por
`unidade` × `categoria` (Grama vende em dezenas/centenas por natureza; Flores de corte,
quase sempre 1 a 3 — comparar os dois grupos na mesma régua marcaria toda Grama normal
como outlier).

Método (função `marcar_outliers`): **z-score modificado de Iglewicz & Hoaglin** (1993,
*How to Detect and Handle Outliers*, ASQC Basic References in Quality Control, Vol. 16 —
reproduzido no NIST/SEMATECH e-Handbook of Statistical Methods, §7.1.6) sobre
`log1p(qtdade)`:

    M_i = 0.6745 * (log1p(qtdade_i) - mediana) / MAD

com MAD = mediana dos desvios absolutos à mediana, dentro de cada `unidade` × `categoria`.
Outlier se `|M_i| > 3.5` — o limiar que os próprios autores recomendam.

Por que esse método e não z-score comum (média/desvio-padrão) ou um limiar fixo (ex.:
percentil 99): `qtdade` é extremamente assimétrica (poucos valores enormes, maioria
pequena) e a média/desvio-padrão comuns são dominados pelos próprios outliers que se quer
detectar — o mesmo problema de escala que o CLAUDE.md já resolve com `log1p` no SARIMAX
(seção L1, "log1p: se CV > 0.7"). Mediana e MAD são estatísticas robustas (não se deixam
deslocar por um único valor extremo), por isso a literatura de controle de qualidade as
recomenda justamente para esse cenário. `log1p` entra para não deixar a cauda longa (poucas
vendas de centenas de unidades) dominar a escala do próprio MAD.

Checado nos dados (2026): o filtro marca 4,4% das linhas (15.287 de 345.491) como outlier,
concentradas em Produtos de jardim e Flores de corte — Grama, cujo "normal" já inclui
compras grandes, sai quase intocada (≤ 1% das linhas nas 2 lojas). Essas 4,4% das linhas
somam 43,8% do volume: outliers por definição são valores grandes, então poucas linhas
carregam quantidade desproporcional — compatível com o que o EDA já via em "vendas
grandes" (CLAUDE.md, L1).

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

# Limiar recomendado por Iglewicz & Hoaglin (1993) para o z-score modificado (mediana/MAD).
LIMIAR_Z_MODIFICADO = 3.5

COLUNAS_SAIDA = ['emissao', 'qtdade']


def marcar_outliers(qtdade: pd.Series, grupo: pd.Series, limiar: float = LIMIAR_Z_MODIFICADO) -> pd.Series:
    """`True` onde o registro é outlier dentro do próprio `grupo` (ex.: unidade×categoria).

    z-score modificado de Iglewicz & Hoaglin sobre `log1p(qtdade)` — ver docstring do
    módulo para o racional. Grupo com MAD = 0 (quantidade igual em quase todo o grupo)
    cai para o desvio médio absoluto, única forma de ainda detectar o raro valor fora da
    curva sem dividir por zero.
    """
    log_qtd = np.log1p(qtdade.clip(lower=0))
    mediana = log_qtd.groupby(grupo).transform('median')
    desvio_abs = (log_qtd - mediana).abs()
    mad = desvio_abs.groupby(grupo).transform('median')
    mad_fallback = desvio_abs.groupby(grupo).transform('mean')
    mad = mad.where(mad > 0, mad_fallback)
    z_modificado = 0.6745 * (log_qtd - mediana) / mad.replace(0, np.nan)
    return z_modificado.abs() > limiar


def remover(
    input_csv: str = CLASSIFIED_CSV,
    output_dir: str = OUTPUT_DIR,
    report_json: str = REMOVE_REPORT_JSON,
    limiar: float = LIMIAR_Z_MODIFICADO,
    verbose: bool = True,
) -> dict:
    df = pd.read_csv(input_csv, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
    linhas_lidas = len(df)
    df['qtdade'] = pd.to_numeric(df['qtdade'], errors='coerce')

    servico = df['categoria'] == CATEGORIA_NAO_PRODUTO
    fora_unidade = ~df['unidade'].isin(UNIDADES)
    df = df.loc[~servico & ~fora_unidade].copy()

    grupo = df['unidade'] + ' | ' + df['categoria']
    df['outlier'] = marcar_outliers(df['qtdade'], grupo, limiar)

    por_grupo = {}
    for nome_grupo, g in df.groupby(grupo):
        por_grupo[nome_grupo] = {
            'linhas': int(len(g)),
            'outliers': int(g['outlier'].sum()),
            'pct_outliers': round(100 * g['outlier'].sum() / len(g), 2),
        }

    arquivos = {}
    for unidade, slug in UNIDADE_SLUG.items():
        base_unidade = df.loc[df['unidade'] == unidade]
        parte = base_unidade.loc[~base_unidade['outlier'], COLUNAS_SAIDA]
        output_csv = os.path.join(output_dir, f'BaseTreino_{slug}_sem_encomendas.csv')
        parte.to_csv(output_csv, sep=';', index=False, encoding='utf-8')
        arquivos[unidade] = {
            'output_csv': output_csv,
            'linhas_mantidas': len(parte),
            'linhas_removidas_outlier': int(len(base_unidade) - len(parte)),
        }

    resumo = {
        'executado_em': datetime.now().isoformat(),
        'input_csv': input_csv,
        'metodo': 'z-score modificado (Iglewicz & Hoaglin, 1993) sobre log1p(qtdade), por unidade x categoria',
        'limiar_z_modificado': limiar,
        'linhas_lidas': linhas_lidas,
        'linhas_removidas_servico_e_taxa': int(servico.sum()),
        'linhas_removidas_unidade_desconhecida': int(fora_unidade.sum()),
        'linhas_removidas_outlier_total': int(df['outlier'].sum()),
        'por_grupo_unidade_categoria': por_grupo,
        'por_unidade': arquivos,
    }
    with open(report_json, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f'[remove_encomendas] {linhas_lidas} linhas lidas de {input_csv}')
        print(f'[remove_encomendas] {resumo["linhas_removidas_outlier_total"]} linha(s) outlier '
              f'removida(s) (z-score modificado > {limiar})')
        for nome_grupo, info in por_grupo.items():
            print(f'[remove_encomendas]   {nome_grupo}: {info["outliers"]}/{info["linhas"]} '
                  f'({info["pct_outliers"]}%)')
        for unidade, info in arquivos.items():
            print(f'[remove_encomendas] {unidade}: {info["linhas_mantidas"]} linhas mantidas '
                  f'({info["linhas_removidas_outlier"]} removidas) em {info["output_csv"]}')
        print(f'[remove_encomendas] resumo em {report_json}')
    return resumo


if __name__ == '__main__':
    remover()
