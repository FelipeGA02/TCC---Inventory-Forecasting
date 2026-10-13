"""Treino C — SARIMAX no FLUXO DIARIO de Itabirito, escala original (sem `log1p`).

Terceiro da serie de quatro. Difere dos treinos A e B num unico ponto: o alvo e o fluxo
diario (`BaseTreino_itabirito_sem_encomendas.csv`), com as encomendas grandes separadas
pela Etapa 6 (ADR-013: venda com mais de 2.000 unidades). Todo o resto — parametros do
SARIMAX, exogenas, ordem, protocolo de walk-forward — vem de `sarimax_itabirito_core`,
igual aos outros tres.

Por que isso deve ajudar: na venda total o CV de Itabirito e 2,35 e 18 dias concentram
61,8% do erro. Separando as encomendas, o fluxo diario fica com CV 0,78 e maximo de 4.610
em vez de 62.595 — regime em que o SARIMAX funciona.

Duas avaliacoes sao gravadas:
  * contra o proprio fluxo diario, que e o que o modelo preve;
  * contra a venda TOTAL, somando as encomendas realmente ocorridas no dia. Esse segundo
    numero e o comparavel com os treinos A e B, e pressupoe o que justifica a separacao:
    a loja conhece a encomenda com antecedencia, porque ela mesma a encomendou.

Uso (a partir de `ia-predictor/`, depois da Etapa 6):
    python -m training_scripts.baseline.treino_itabirito_fluxo_sem_log
"""
from training_scripts.baseline.sarimax_itabirito_core import (
    BASE_ENCOMENDAS, BASE_FLUXO_DIARIO, executar,
)

NOME = "itabirito_fluxo_sem_log"

if __name__ == "__main__":
    executar(NOME, usar_log1p=False,
             base_csv=BASE_FLUXO_DIARIO, encomendas_csv=BASE_ENCOMENDAS)
