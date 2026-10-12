"""Limpa a `BaseClassificada03.csv` e gera a `BaseTreino.csv`, só com o que o SARIMAX
do L1 (`unidade`, diário) consome.

Faz três coisas:

  * remove os registros de `categoria` = "Servico e taxa" (frete, mão de obra — não é
    demanda de produto);
  * remove linha com `unidade` fora das 2 lojas (`UNIDADES`) — hoje são 0 linhas (os 3
    CNPJs da base mapeiam 100% para Jardim Canadá/Itabirito, ver `taxonomy/unidades.py`);
    a checagem fica como trava defensiva para um upload futuro trazer CNPJ sem de/para
    cadastrado, o que criaria uma 3ª série fantasma na soma por `unidade` do L1;
  * mantém só `COLUNAS_SARIMAX` (`emissao`, `unidade`, `qtdade` — ver `constants.py`) e
    descarta o resto: categoria/produto (servem à desagregação L2, não ao L1) e os
    valores monetários (o alvo é quantidade vendida, não receita).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.limpeza_para_treino_04
"""
import json
import os
from datetime import datetime

import pandas as pd

from .classificacao_03 import CLASSIFIED_CSV
from .extrair_base_01 import OUTPUT_DIR

CLEAN_CSV = os.path.join(OUTPUT_DIR, 'BaseTreino.csv')
CLEAN_REPORT_JSON = os.path.join(OUTPUT_DIR, 'limpeza_para_treino_resumo.json')

# Colunas que o SARIMAX do L1 (`unidade`, diário) de fato consome: `emissao` vira o
# índice da série, `qtdade` é somada por dia como alvo, `unidade` separa as 2 séries.
# As demais colunas da base classificada (categoria/produto/valores monetários) servem
# só para a desagregação L2 ou para rastreio — não entram no L1.
COLUNAS_SARIMAX = ['emissao', 'unidade', 'qtdade']

# Etapa 3 (classificacao_03.py) marca essa `categoria` para registros que não são demanda
# de produto (frete, taxa, mão de obra) — ver docs/prediction/01-pre_processing.md §5.
CATEGORIA_NAO_PRODUTO = 'Servico e taxa'

# Unidades operacionais (taxonomy/unidades.py). Linha com unidade fora desta lista é
# descartada aqui e contada no relatório. Duplicada em `dados_externos_10.py` (mesmo fato
# de negócio, usado para montar o calendário por loja) — não há mais um módulo central de
# constantes para as duas etapas compartilharem.
UNIDADES = ['Jardim Canadá', 'Itabirito']


def limpar(
    input_csv: str = CLASSIFIED_CSV,
    output_csv: str = CLEAN_CSV,
    report_json: str = CLEAN_REPORT_JSON,
    verbose: bool = True,
) -> dict:
    df = pd.read_csv(input_csv, sep=';', encoding='utf-8', dtype=str, keep_default_na=False)
    linhas_lidas = len(df)

    servico = df['categoria'] == CATEGORIA_NAO_PRODUTO
    fora_unidade = ~df['unidade'].isin(UNIDADES)
    empresas_fora_unidade = sorted(df.loc[fora_unidade, 'empresa'].unique().tolist()) \
        if 'empresa' in df.columns else []
    df = df.loc[~servico & ~fora_unidade, COLUNAS_SARIMAX].copy()

    df.to_csv(output_csv, sep=';', index=False, encoding='utf-8')

    resumo = {
        'executado_em': datetime.now().isoformat(),
        'input_csv': input_csv,
        'output_csv': output_csv,
        'linhas_lidas': linhas_lidas,
        'linhas_removidas_servico_e_taxa': int(servico.sum()),
        'linhas_removidas_unidade_desconhecida': int(fora_unidade.sum()),
        'empresas_com_unidade_desconhecida': empresas_fora_unidade,
        'colunas_mantidas': COLUNAS_SARIMAX,
        'linhas_gravadas': len(df),
    }
    with open(report_json, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f'[limpeza_para_treino] {linhas_lidas} linhas lidas de {input_csv}')
        print(f'[limpeza_para_treino] {resumo["linhas_removidas_servico_e_taxa"]} linha(s) de '
              f'"{CATEGORIA_NAO_PRODUTO}" removida(s)')
        if fora_unidade.any():
            print(f'[limpeza_para_treino] [!] {resumo["linhas_removidas_unidade_desconhecida"]} '
                  f'linha(s) com unidade desconhecida removida(s) — empresas: {empresas_fora_unidade}')
        print(f'[limpeza_para_treino] colunas mantidas: {COLUNAS_SARIMAX}')
        print(f'[limpeza_para_treino] {len(df)} linhas gravadas em {output_csv}')
        print(f'[limpeza_para_treino] resumo em {report_json}')
    return resumo


if __name__ == '__main__':
    limpar()
