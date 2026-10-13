"""Treino A — SARIMAX de Itabirito na escala ORIGINAL (sem `log1p`).

Experimento de controle da dupla: todos os parametros do SARIMAX, as exogenas e o
protocolo de walk-forward vem de `sarimax_itabirito_core`, identicos aos do treino B
(`treino_itabirito_log1p.py`). A unica diferenca entre os dois e a transformacao — aqui
o modelo ve a quantidade em unidades.

O que esperar: a serie tem CV 2,35 e maximo de 62,6 mil contra mediana de 853, entao a
verossimilhanca gaussiana na escala original tende a ser dominada pelos poucos dias
enormes. E exatamente esse efeito que o treino B isola.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.baseline.treino_itabirito_sem_log
"""
from training_scripts.baseline.sarimax_itabirito_core import executar

NOME = "itabirito_sem_log"

if __name__ == "__main__":
    executar(NOME, usar_log1p=False)
