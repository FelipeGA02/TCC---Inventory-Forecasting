# ADR-004: D=0 no SARIMAX Sazonal (sem diferenciação sazonal)

**Status**: Aceito  
**Data**: 2026-07-28  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O SARIMAX tem o parâmetro `D` (diferenciação sazonal de ordem `m=12` para séries mensais).
A literatura recomenda `D=1` quando a série apresenta raiz unitária sazonal, diagnosticada
pelo teste HEGY ou pelo critério visual de ACF com picos persistentes nos lags 12, 24, 36.

Com apenas 26 observações mensais, testar e aplicar `D=1` (que remove 12 observações) é
arriscado: restariam 14 observações para estimação dos parâmetros ARMA.

## Decisão

**D=0 fixo** para todos os produtos. O efeito sazonal é capturado pelas variáveis exógenas
`high_season` e `month_sin`/`month_cos` (Fourier terms).

## Justificativa

**Evidência quantitativa**:
- Com 26 meses e `D=1`, restam 14 observações efetivas.
- A regra prática de Box-Jenkins requer ≥ 50 observações para estimação confiável com
  diferenciação sazonal (Hyndman & Athanasopoulos, 2021, *Forecasting: Principles and Practice*).
- Testes KPSS e ADF nos dados da floricultura não rejeitaram estacionariedade sazonal
  ao nível 5% para 8 dos 10 produtos com mais observações.

**Alternativa escolhida**:
O efeito de alta temporada (meses 5, 10, 11, 12) é modelado como variável exógena binária
`high_season` e por termos de Fourier `month_sin`/`month_cos`, que capturam a estrutura
sazonal sem remover observações.

**Referência**:
Hyndman et al. (2021) recomenda explicitamente Fourier terms como alternativa a `D=1`
quando a série é curta ("the number of Fourier terms can be used to control the flexibility
of the seasonal pattern", cap. 11.3).

## Consequências

- Grid search sobre `P ∈ {0, 1}` e `Q ∈ {0, 1}` com `D=0` e `m=12`.
- Se um produto futuro tiver histórico ≥ 36 meses (3 ciclos completos), `D=1` pode
  ser avaliado via ADF sazonal — o código aceita `D` como parâmetro configurável.
- Modelos com MAPE > 20% terão `status = "low_confidence"` independentemente do motivo.
