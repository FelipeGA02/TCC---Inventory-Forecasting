"""Roda os dois EDAs em sequência (T000b).

    python -m training_scripts.eda.run_all

Pré-requisito: `training_scripts/output/contas_a_receber_taxonomia.csv` gerado
(rodar `python -m training_scripts.preprocessing.map_taxonomy` antes).
"""
from . import eda_series, eda_source


def main() -> None:
    print("=" * 72)
    print("EDA 1 — compreensão dos dados (base transacional)")
    print("=" * 72)
    eda_source.main()
    print()
    print("=" * 72)
    print("EDA 2 — série modelável (9 pares unidade × categoria)")
    print("=" * 72)
    eda_series.main()


if __name__ == "__main__":
    main()
