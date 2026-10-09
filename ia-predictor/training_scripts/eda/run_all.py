"""Roda os EDAs em sequência (T000b).

    python -m training_scripts.eda.run_all

Pré-requisito: `training_scripts/output/contas_a_receber_taxonomia.csv` gerado
(rodar `python -m training_scripts.preprocessing.map_taxonomy` antes).
"""
from . import (
    eda_classificacao_sku, eda_grupos, eda_separacao, eda_series, eda_series_unidade, eda_source,
)


def main() -> None:
    print("=" * 72)
    print("EDA 1 — compreensão dos dados (base transacional)")
    print("=" * 72)
    eda_source.main()
    print()
    print("=" * 72)
    print("EDA 2 — série-alvo do L1: unidade (2 séries)")
    print("=" * 72)
    eda_series_unidade.main()
    print()
    print("=" * 72)
    print("EDA 2b — série de desagregação: unidade × categoria (6 séries)")
    print("=" * 72)
    eda_series.main()
    print()
    print("=" * 72)
    print("EDA 3 — granularidade das categorias do L1")
    print("=" * 72)
    eda_grupos.main()
    print()
    print("=" * 72)
    print("EDA 4 — separar por unidade e por categoria melhora a previsão?")
    print("=" * 72)
    eda_separacao.main()
    print()
    print("=" * 72)
    print("EDA 5 — classificação de demanda por SKU (Syntetos, Boylan & Croston, 2005)")
    print("=" * 72)
    eda_classificacao_sku.main()


if __name__ == "__main__":
    main()
