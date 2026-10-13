"""Treino B — SARIMAX de Itabirito com `log1p`.

Par do `treino_itabirito_sem_log.py`: mesmos parametros do SARIMAX, mesmas exogenas,
mesmo protocolo de walk-forward, mesma ordem (p,d,q)(P,D,Q)m. A unica diferenca e que o
modelo e ajustado em z = log(1 + qtdade) e a previsao volta por `expm1`.

Dois efeitos dessa escolha, ambos medidos nas metricas de saida:

  * estabiliza a variancia — um erro de 10% passa a custar o mesmo num dia de 60 mil e num
    de 800 unidades, entao os picos deixam de dominar o ajuste;
  * `expm1` da media em log devolve a **mediana** em unidades, nao a media. Com cauda
    pesada a mediana fica abaixo da media, o que aparece como previsao sistematicamente
    menor que o realizado (ver `vies_previsto_sobre_real_pct`).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.baseline.treino_itabirito_log1p
"""
from training_scripts.baseline.sarimax_itabirito_core import executar

NOME = "itabirito_log1p"

if __name__ == "__main__":
    executar(NOME, usar_log1p=True)
