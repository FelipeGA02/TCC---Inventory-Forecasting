# ADR-023 — Histórico da previsão com o registro mais antigo de cada dia

**Status:** aceito · **Data:** 2026-11-10 · **Revisa:** ADR-017 (histórico congelado: a última previsão antes do dia)
**Afeta:** `backend/domain/historico_previsao.py`, `backend/domain/models/trainer.py` (sai o
complemento), `backend/services/servico_previsao.py` (`gravar_historico`, `semear_historico`),
`openapi.yaml` 9.0.2 (só descrição), tela "Histórico de previsão" (tooltip com a antecedência)
**Funcionamento:** [doc 07 §4](07-previsao_14_dias_e_historico.md)

---

## 1. Contexto

A tela de histórico compara o vendido de cada dia com o previsto gravado em `forecast_history`.
Até aqui, a regra era a do ADR-017: o previsto de um dia era o da **última** previsão feita antes
dele. Cada treino apagava os dias a partir do dia seguinte à última venda e gravava a previsão
inteira (91 dias, ADR-021). Do walk-forward entrava só o 1º dia de cada janela (h = 1), com 13
origens parciais (o "complemento") para chegar até a última venda.

Com isso, nos dias que vinham do walk-forward (antes do 1º treino, ou quando a loja demorava a
treinar), o histórico mostrava a previsão **da véspera**. É a mais fácil de acertar e não é a que
a loja usa para comprar: a loja olha as 2 semanas seguintes. O walk-forward já calcula, para cada
dia, as previsões feitas de 1 a 14 dias antes, mas a tela só via a de 1 dia.

## 2. Decisão

1. **Cada dia guarda o registro mais antigo dele, que não é trocado.** Um treino só grava os
   dias de cada série que ainda não têm registro.
2. **Do walk-forward, a janela mais antiga que previu o dia**: a origem mais cedo, ou seja, o
   maior horizonte (até 14 dias antes, com as vendas até a véspera da origem). Os 13 primeiros
   dias do período testado só aparecem nas primeiras janelas e ficam com horizonte 1 a 13.
3. **Da previsão final, só os 14 primeiros dias** (`FORECAST_HORIZON_DAYS`, o horizonte do
   walk-forward e do teste de acerto). Os 91 dias continuam em `series_forecasts` para a tela de
   Previsão.
4. **Sai o complemento** do trainer: as janelas completas já cobrem todos os dias até a última
   venda, e o complemento só servia para o h = 1 do histórico.
5. A tela mostra no tooltip com quantos dias de antecedência o dia foi previsto e se o número
   veio da previsão ou do teste do treino.

Com o treino semanal, cada dia fica com a previsão do treino que o previu primeiro (horizontes
de 8 a 14 dias para a maior parte da semana seguinte). A linha do histórico passa a mostrar o
erro com a antecedência com que a loja de fato planeja, tanto no teste quanto na previsão.

## 3. Consequências

- O histórico fica mais pessimista que antes nos dias do walk-forward (h = 14 em vez de h = 1),
  e coerente com as métricas do teste de acerto, que avaliam os 14 horizontes.
- Um treino repetido com os mesmos dados, ou uma venda apagada que faz a última venda voltar,
  não muda nenhum dia já gravado.
- O treino fica 13 ajustes mais curto por série (sem o complemento).
- `semear_historico --recriar` refaz o histórico de um banco com a regra anterior a partir do
  último treino: walk-forward guardado (`series_backtest_points`, com todos os horizontes) + os
  14 primeiros dias da previsão. O walk-forward guardado não tem o fator das datas comemorativas
  (ADR-019): nesses dias, `event_factor` fica nulo, e o previsto já vem com o fator aplicado.
- A constituição (Princípio V) segue atendida: o treino continua gravando o histórico em
  `forecast_history`, só com outra regra de qual previsão fica.
