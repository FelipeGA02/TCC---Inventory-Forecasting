# ADR-019 — Fator das datas comemorativas na previsão de Flores de corte

**Status:** proposto · **Data:** 2026-11-03 · **Revisa:** ADR-017 (receita da previsão: entra
um ajuste depois do SARIMAX, só em Flores de corte)
**Afeta:** `backend/domain/models/datas_comemorativas.py` (novo), `backend/domain/models/trainer.py`,
`backend/services/servico_previsao.py`, `backend/domain/historico_previsao.py`,
`series_forecasts.event_factor` e `forecast_history.event_factor` (colunas novas),
`FORECAST_SERVICE_EVENT_FACTOR`
**Evidência:** `docs/prediction/08-fator_datas_comemorativas.md` ·
`training_scripts/datas_comemorativas/fator_multiplicativo.py`

---

## 1. O problema

O SARIMAX do sistema (ADR-017) só conhece o dia da semana, a loja fechada e a abertura
excepcional. Na semana do Dia da Mulher, do Dia das Mães, do Dia dos Namorados e do Natal, ele
prevê uma semana comum de Flores de corte: de 200 a 310 flores, quando a loja vende de 416 a
803. Nesses dias a faixa de 95% cobre só 77–80% do vendido, abaixo do mínimo de 90%
(doc 08 §5.1). Flores de corte é perecível, e o sistema prevê menos da metade da semana em
que a loja mais compra.

Uma exógena "semana da data" no SARIMAX não resolve:
- **o modelo trabalha em unidades** (sem `log1p`), e a exógena somaria um número fixo, em vez
  de multiplicar;
- **a janela de treino é de 365 dias**, então o coeficiente seria estimado com uma única
  semana;
- **o doc 03 já mostrou o risco:** a exógena `janela_7d_*` atribuiu à semana um efeito que era
  do dia e gerou 12% do erro do ano.

## 2. Decisão

```
séries        = Flores de corte, nas 2 lojas (CATEGORIAS_COM_FATOR)
datas         = Dia da Mulher (08/03), Dia das Mães (2º domingo de maio),
                Dia dos Namorados (12/06), Natal (25/12) — pela regra, não pelo calendário gravado
dias          = de 6 dias antes até a data, loja aberta, sem abertura excepcional
fator         = Σ venda ÷ Σ base nesses dias, nas últimas 3 ocorrências da data com as
                4 semanas seguintes já vendidas
base do dia   = mediana do mesmo dia da semana nas 4 semanas antes e 4 depois, só dias normais
multiplicador = mín(3, máx(1, 1 + 0,5 · (fator − 1)))
previsão      = previsão do SARIMAX × multiplicador, no previsto e nos limites da faixa
```

- **O fator sai das vendas a cada treino.** Ele não fica fixo no código: se a alta da data
  diminuir, o fator diminui no treino seguinte. A lista de séries e datas é decisão de
  projeto (doc 08 §6); o tamanho do ajuste é dos dados, como o limiar de encomenda do ADR-018.
- **Só metade do aumento entra.** Com uma ocorrência por ano, o fator muda até 2× de um ano
  para o outro: em Itabirito, o fator cheio de 2024 errou para cima de 91% a 151% em 2025, e a
  metade melhorou o total da semana nas 10 ocorrências testadas.
- **Nunca abaixo de 1:** o teste não avaliou reduzir a previsão. **Teto de 3:** uma semana
  fora do comum não estraga o ano seguinte. O teto não foi testado. No teste, só o Dia das
  Mães de Itabirito o atingiria (3,4, com o fator só de 2024). Com 2024 e 2025 juntos,
  nenhuma data passa de 2,74 (tabela abaixo).
- **Sem ocorrência passada completa, sem ajuste.** No walk-forward, o fator usa só a venda
  anterior à origem: as métricas e o status saem com o ajuste, sem olhar o período avaliado.
- **As datas vêm da regra**, não de `calendar_days.special_date_name`: o calendário gravado
  vai até 31/12/2026, e sem a data marcada o ajuste sumiria sem aviso.
- **Desligável** com `FORECAST_SERVICE_EVENT_FACTOR=false`. A configuração gravada no disparo
  (`forecast_jobs.config`) leva `fator_datas`, `fator_fracao`, `fator_teto`,
  `fator_ocorrencias` e `categorias_com_fator`.

Multiplicadores de 2026, com as ocorrências de 2024 e 2025 (base até 28/02/2026). A previsão
que sai dessa base, de 01 a 14/03/2026, já pega o Dia da Mulher:

| Data | Jardim Canadá: fator → multiplicador | Itabirito: fator → multiplicador |
| --- | --- | --- |
| Dia da Mulher | 3,47 → 2,23 | 4,48 → 2,74 |
| Dia das Mães | 3,45 → 2,22 | 3,98 → 2,49 |
| Dia dos Namorados | 1,92 → 1,46 | 3,65 → 2,32 |
| Natal | 2,65 → 1,83 | 1,84 → 1,42 |

## 3. O que fica gravado

| Onde | O quê |
| --- | --- |
| `series_forecasts.event_factor` | o multiplicador de cada dia da previsão; nulo sem ajuste |
| `forecast_history.event_factor` | o mesmo, no histórico congelado: o previsto do modelo sem o ajuste é `predicted / event_factor` |
| `series_models.params` | `fator_datas` (a série leva o ajuste) e `ajustes_datas` (evento, data, fator, multiplicador, anos, dias) |
| log da série | "Dia das Mães (10/05/2026): previsão dos 6 dia(s) da semana da data multiplicada por 1,93 — nessa semana, em 2024 e 2025, a loja vendeu 2,9 vezes uma semana comum." |

## 4. Por que estas séries e datas

Doc 08, treino de produção (SARIMAX do ADR-017) com e sem o fator, 20 origens por ocorrência:

| | sem fator | metade do fator |
| --- | --- | --- |
| Flores de corte, Jardim Canadá — erro do total da semana | 60% | 32% |
| Flores de corte, Itabirito — erro do total da semana | 54% | 32% |
| cobertura da faixa de 95% nesses dias | 77–80% | 85–96% |

Ficam de fora:
- **Finados em Itabirito:**
  - em Grama, o ganho vem de o modelo prever pouco no período inteiro (58% do vendido fora da
    semana da data);
  - em Produtos de jardim, o fator multiplica o erro da semana por 9;
  - em Plantas diversas, o ganho é pequeno e vem de 2 ocorrências.
- **Dia dos Pais e Finados em Flores de corte:** não há alta.
- **Demais categorias e produtos de grama:** nenhuma data sai da faixa de uma semana comum.

## 5. Consequências e cuidados

- **O fator acerta o total da semana, não o dia do pico.** O erro de cada dia quase não muda
  (−9% em Jardim Canadá, +8% em Itabirito): o multiplicador sobe igual os 6 dias, e o pico cai
  na véspera, na quinta ou no sábado, conforme a data e o ano. Para a loja, o número confiável
  é quanta flor a semana vende.
- **A faixa de 95% fica de 1,7 a 2,5 vezes mais larga nesses dias:** é o preço de cobrir o
  vendido.
- **O walk-forward do sistema quase nunca passa por uma dessas datas:** as 56 origens cobrem as
  8 semanas antes da última venda. Quando passa, as métricas já saem com o ajuste. A avaliação
  de verdade é depois de cada data: comparar vendido, previsto ajustado e `predicted /
  event_factor` no `forecast_history`.
- **Revisão anual:** rodar de novo `fator_multiplicativo.py` com o ano novo de vendas.
  - **Tirar uma data da lista** se, em 2 ocorrências seguidas, o previsto ajustado errar a
    semana mais que o do modelo.
  - **Subir a fração** (por exemplo, para n/(n+1) com n ocorrências) só com um teste novo.
  - **Testar de novo Finados em Plantas diversas de Itabirito.**
- **O total da loja** (soma das categorias) herda o ajuste de Flores de corte: no máximo 4,8%
  das unidades da loja.
- **A tela ainda não diz que a semana foi ajustada:** `event_factor` está gravado, mas não
  aparece no `GET /api/v1/painel` nem no histórico. Mostrar, sem jargão, "previsão maior pela
  semana do Dia das Mães" é o próximo passo (`openapi.yaml` + cliente gerado).
- **Constituição, Princípio III:** a validação de cada ajuste é a do doc 08 (fora do
  walk-forward do treino), registrada aqui.

## 6. Referências

- `docs/prediction/08-fator_datas_comemorativas.md` — EDA (fator da semana × semanas comuns) e
  o teste com e sem o fator.
- `docs/prediction/ADR-017-previsao-por-categoria-e-grama.md` — a receita que este ADR estende.
- `docs/prediction/00-eda_report.md` §3.4 — o efeito por categoria, revisado pelo doc 08.
- Testes: `tests/unit/test_datas_comemorativas.py`, `test_treino_serie.py::test_fator_das_datas_multiplica_so_a_semana_da_data`,
  `test_historico_previsao.py::test_ponto_guarda_o_fator_da_data_comemorativa`,
  `tests/integration/test_servico_previsao.py::test_so_flores_de_corte_leva_o_fator_das_datas`,
  `test_banco_existente.py::test_previsao_antiga_ganha_o_fator_das_datas`.
