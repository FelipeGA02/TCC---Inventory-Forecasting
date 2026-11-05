# ADR-019 — Fator das datas comemorativas na previsão

**Status:** proposto · **Data:** 2026-11-03 (números refeitos em 2026-11-05 com a classificação
SKU a SKU; em 2026-11-05, o Ano Novo em Flores de corte e a regra da queda, §2.1) · **Revisa:**
ADR-017 (receita da previsão: entra um ajuste depois do SARIMAX)
**Afeta:** `backend/domain/models/datas_comemorativas.py` (novo), `backend/domain/models/trainer.py`,
`backend/services/servico_previsao.py`, `backend/domain/historico_previsao.py`,
`series_forecasts.event_factor` e `forecast_history.event_factor` (colunas novas),
`FORECAST_SERVICE_EVENT_FACTOR`
**Evidência:** `docs/prediction/08-fator_datas_comemorativas.md` (§5 a alta, §9.3 a queda) ·
`training_scripts/datas_comemorativas/fator_multiplicativo.py`, `eda_eventos.py`, `eda_reducao.py`

---

## 1. O problema

O SARIMAX do sistema (ADR-017) só conhece o dia da semana, a loja fechada e a abertura
excepcional. Ele erra para os 2 lados: para baixo nas datas de flor, para cima de 26 a 31/12
(a Grama de Itabirito vende 0,35 de uma semana comum, e o modelo prevê 3,6 vezes o vendido;
doc 08 §9.3). Na semana do Dia da Mulher, do Dia das Mães, do Dia dos Namorados e do Natal, ele
prevê uma semana comum de Flores de corte: de 195 a 310 flores, quando a loja vende de 415 a
803. Nesses dias a faixa de 95% cobre só 77–81% do vendido, abaixo do mínimo de 90%
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
                Dia dos Namorados (12/06), Natal (25/12), Ano Novo (01/01: de 26 a 31/12)
                — pela regra, não pelo calendário gravado
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
  para o outro: em Itabirito, o fator cheio de 2024 errou para cima de 87% a 159% em 2025, e a
  metade melhorou o total da semana nas 10 ocorrências testadas.
- **Nunca abaixo de 1** em Flores de corte. A queda das outras séries tem regra própria (§2.1). **Teto de 3:** uma semana
  fora do comum não estraga o ano seguinte. O teto não foi testado. No teste, só o Dia das
  Mães de Itabirito o atingiria (3,4, com o fator só de 2024). Com 2024 e 2025 juntos,
  nenhuma data passa de 2,74 (tabela abaixo).
- **Sem ocorrência passada completa, sem ajuste.** No walk-forward, o fator usa só a venda
  anterior à origem: as métricas e o status saem com o ajuste, sem olhar o período avaliado.
- **As datas vêm da regra**, não de `calendar_days.special_date_name`: o calendário gravado
  vai até 31/12/2026, e sem a data marcada o ajuste sumiria sem aviso.
- **Desligável** com `FORECAST_SERVICE_EVENT_FACTOR=false` (a alta e a queda). A configuração
  gravada no disparo (`forecast_jobs.config`) leva `fator_datas`, `fator_regra`, `queda_datas`,
  `queda_regra` e `categorias_com_fator`.
- **Ano Novo (2026-11-05):** a flor do Réveillon (doc 08 §9.2). Na metade do fator, o erro da
  semana em Jardim Canadá cai de 34% para 17% (2025) e de 49% para 28% (2026). Em Itabirito
  fica igual (30% e 31% em 2026). Entra nas 2 lojas, como as outras datas.

### 2.1 A queda: 26 a 31/12 e Dia do Trabalho (2026-11-05)

```
séries        = todas menos Flores de corte: as outras 3 categorias e os produtos de grama
datas         = Ano Novo (de 26 a 31/12), Dia do Trabalho (de 25/04 a 01/05)
fator         = o mesmo da alta (venda ÷ base, últimas 3 ocorrências)
condição      = pelo menos 2 ocorrências passadas, cada uma em até 0,8 de uma semana comum
multiplicador = mín(1, máx(0,2, fator))   — a queda inteira
```

- **A queda inteira, não a metade:** o fator da queda muda pouco de um ano para o outro (0,35
  e 0,35 na Grama de Itabirito), e no teste a inteira venceu a metade e o sistema em todas as
  ocorrências (doc 08 §9.3).
- **A condição é o critério do EDA, recalculado a cada treino:** a série tem de ter caído nas
  2 últimas ocorrências. Série que caiu num ano só (Plantas diversas de Itabirito: 1,75 e 0,64)
  fica sem ajuste. Com uma ocorrência só, também fica sem ajuste: é por isso que, na base de
  hoje, a queda só aparece a partir do Dia do Trabalho de 2026.
- **Piso de 0,2:** a São Carlos de Jardim Canadá não vendeu nada na semana de 2025, e o fator
  zero zeraria a previsão.
- **O Dia do Trabalho entra na regra das datas:** os dias perto dele saem da base de todas as
  datas. Com isso, o multiplicador do Dia das Mães de 2026 em Flores de corte cai de 2,22 para
  2,11 (Jardim Canadá) e de 2,49 para 2,40 (Itabirito): a semana fraca do feriado deixa de
  puxar a base para baixo.

Com a base até 28/02/2026, a regra pega:
- **no Dia do Trabalho de 2026:** a Grama de Itabirito (0,54);
- **no Ano Novo de 2027:**
  - Jardim Canadá: Grama 0,58, Plantas diversas 0,57, Produtos de jardim 0,61, Esmeralda 0,41,
    São Carlos 0,20;
  - Itabirito: Grama 0,35, Esmeralda (ITO) 0,31, São Carlos 0,21.

Todas passaram pelo teste (a São Carlos de Itabirito no doc 08 §9.4). A queda de Flores de
corte em Itabirito depois do Réveillon (2 a 8/01) ficou fora: só 1 ocorrência caiu (§9.4).

Multiplicadores de 2026, com as ocorrências de 2024 e 2025 (base até 28/02/2026). A previsão
que sai dessa base, de 01 a 14/03/2026, já pega o Dia da Mulher:

| Data | Jardim Canadá: fator → multiplicador | Itabirito: fator → multiplicador |
| --- | --- | --- |
| Dia da Mulher | 3,47 → 2,23 | 4,49 → 2,74 |
| Dia das Mães | 3,44 → 2,22 | 3,99 → 2,49 |
| Dia dos Namorados | 1,92 → 1,46 | 3,61 → 2,31 |
| Natal | 2,65 → 1,82 | 1,84 → 1,42 |
| Ano Novo (previsão de dez./2026) | 2,10 → 1,55 | 2,26 → 1,63 |

Com o Dia do Trabalho fora da base (§2.1), o Dia das Mães passa a 3,22 → 2,11 em Jardim Canadá
e 3,81 → 2,40 em Itabirito.

## 3. O que fica gravado

| Onde | O quê |
| --- | --- |
| `series_forecasts.event_factor` | o multiplicador de cada dia da previsão; nulo sem ajuste |
| `forecast_history.event_factor` | o mesmo, no histórico congelado: o previsto do modelo sem o ajuste é `predicted / event_factor` |
| `series_models.params` | `fator_datas` (a série leva o ajuste) e `ajustes_datas` (evento, data, fator, multiplicador, anos, dias) |
| `series_models.params` | `queda_datas` (a série leva a queda) |
| log da série | "Dia das Mães (10/05/2026): previsão dos 6 dia(s) da semana da data multiplicada por 2,40 — nessa semana, em 2024 e 2025, a loja vendeu 3,8 vezes uma semana comum." · "Ano Novo (01/01/2027): previsão dos 5 dia(s) da semana da data reduzida a 35% — nessa semana, em 2025 e 2026, a loja vendeu 35% de uma semana comum." |

## 4. Por que estas séries e datas

Doc 08, treino de produção (SARIMAX do ADR-017) com e sem o fator, 20 origens por ocorrência:

| | sem fator | metade do fator |
| --- | --- | --- |
| Flores de corte, Jardim Canadá — erro do total da semana | 61% | 33% |
| Flores de corte, Itabirito — erro do total da semana | 54% | 32% |
| cobertura da faixa de 95% nesses dias | 77–81% | 84–96% |

Ficam de fora:
- **Finados em Itabirito:**
  - em Grama, o ganho vem de o modelo prever pouco no período inteiro (60% do vendido fora da
    semana da data);
  - em Produtos de jardim, o fator multiplica o erro da semana por 6;
  - em Plantas diversas, a alta é real (crisântemo e kalanchoe em vaso, doc 08 §2.3), mas o
    fator melhora uma ocorrência e piora a outra (de 9% para 22% de erro em 2025).
- **Dia dos Pais e Finados em Flores de corte:** não há alta. A flor de Finados é a em vaso, em
  Plantas diversas, e só em Itabirito.
- **Demais categorias e produtos de grama:** nenhuma data de alta sai da faixa de uma semana
  comum. As quedas de 26 a 31/12 e do Dia do Trabalho estão na §2.1.
- **Sexta-feira Santa e Corpus Christi:** a queda não se repete nos 2 anos (doc 08 §9.3).

## 5. Consequências e cuidados

- **O fator acerta o total da semana, não o dia do pico.** O erro de cada dia quase não muda
  (−10% em Jardim Canadá, +9% em Itabirito): o multiplicador sobe igual os 6 dias, e o pico cai
  na véspera, na quinta ou no sábado, conforme a data e o ano. Para a loja, o número útil
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
  - **O crisântemo de Finados em Itabirito** pede uma série própria (Plantas diversas inteira
    dilui a alta), fora do que o sistema faz hoje.
- **O total da loja** (soma das categorias) herda os ajustes: a alta de Flores de corte (no
  máximo 4,8% das unidades da loja) e, de 26 a 31/12, a queda das outras categorias.
- **A queda encolhe a faixa de 95% junto:** onde o modelo errava muito para cima, a cobertura
  desses dias sobe (Plantas diversas de Jardim Canadá: de 71% para 96%). Onde ele errava menos,
  ela cai (Grama de Jardim Canadá: de 71% para 60%).
- **A tela diz quando a semana foi ajustada** (`openapi.yaml` 5.1.0):
  - **Na Previsão,** um aviso lista cada série ajustada nos 14 dias, por exemplo "Grama em
    Itabirito: previsão de 26/12 a 31/12 reduzida a 35% pelo Ano Novo — nessa semana, em 2025 e
    2026, a loja vendeu 35% de uma semana comum". Os dados vêm de `ajustes_datas` em cada loja
    do `GET /api/v1/painel`, lido de `series_models.params.ajustes_datas`.
  - **No histórico da previsão,** a dica do dia diz "previsão reduzida a 35% pelo Ano Novo"
    (`ajuste`, de `forecast_history.event_factor`; a data sai da regra, por
    `evento_do_dia`).
  - **No relatório gerencial,** uma tabela "Datas comemorativas".
- **Constituição, Princípio III (v4.0.0):** o ajuste que o walk-forward do treino quase
  nunca atravessa é validado em experimento próprio (doc 08), com a receita de produção, e
  revisto a cada ano de vendas. O Princípio II permite o ajuste como estatística.

## 6. Referências

- `docs/prediction/08-fator_datas_comemorativas.md` — EDA (fator da semana × semanas comuns) e
  o teste com e sem o fator.
- `docs/prediction/ADR-017-previsao-por-categoria-e-grama.md` — a receita que este ADR estende.
- `docs/prediction/00-eda_report.md` §3.4 — o efeito por categoria, revisado pelo doc 08.
- Testes: `tests/unit/test_datas_comemorativas.py` (inclusive
  `test_ano_novo_pega_a_semana_antes_do_1o_de_janeiro_do_ano_seguinte` e
  `test_queda_inteira_so_quando_as_2_ultimas_ocorrencias_cairam`), `test_treino_serie.py::test_fator_das_datas_multiplica_so_a_semana_da_data`,
  `test_historico_previsao.py::test_ponto_guarda_o_fator_da_data_comemorativa`,
  `tests/integration/test_servico_previsao.py::test_so_flores_de_corte_leva_o_fator_das_datas`,
  `test_banco_existente.py::test_previsao_antiga_ganha_o_fator_das_datas`.
