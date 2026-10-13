"""Treino D — SARIMAX no FLUXO DIARIO de Itabirito, com `log1p`.

Quarto e ultimo da serie. Combina as duas intervencoes que os treinos anteriores isolaram:
a transformacao `log1p` (treino B) e a separacao das encomendas grandes (treino C). Os
parametros do SARIMAX, as exogenas, a ordem e o protocolo de walk-forward continuam vindo
de `sarimax_itabirito_core`, identicos aos outros tres.

A matriz dos quatro experimentos:

                        venda total          fluxo diario (ADR-013)
    sem log1p           treino A             treino C
    com log1p           treino B             treino D   <- este

Com o fluxo diario ja em CV 0,78, o ganho do `log1p` deve ser menor do que foi na venda
total (CV 2,35) — e e exatamente isso que a comparacao C x D mede: se a transformacao
ainda se paga depois que a serie foi partida, ou se as duas intervencoes atacam o mesmo
problema e nao se somam.

Atencao ao viés: `expm1` devolve a mediana, nao a media. Na venda total isso fez a previsao
cobrir so 46,1% do realizado. Conferir `vies_previsto_sobre_real_pct` aqui antes de
concluir qualquer coisa pelo MAE.

Uso (a partir de `ia-predictor/`, depois da Etapa 6):
    python -m training_scripts.baseline.treino_itabirito_fluxo_log1p
"""
from training_scripts.baseline.sarimax_itabirito_core import (
    BASE_ENCOMENDAS, BASE_FLUXO_DIARIO, executar,
)

NOME = "itabirito_fluxo_log1p"

if __name__ == "__main__":
    executar(NOME, usar_log1p=True,
             base_csv=BASE_FLUXO_DIARIO, encomendas_csv=BASE_ENCOMENDAS)
