# Relatório de Análise Exploratória (EDA)

**Projeto**: Sistema de Previsão de Estoque · Floricultura Verde Perto
**Tarefa**: T000b (Fase 0 — Modelagem, EDA e Documentação Acadêmica)
**Data**: 2026-09-01
**Base analisada**: 333.019 linhas · 02/01/2024 – 28/02/2026 · 5.166 SKUs · 3 lojas
**Scripts**: [`ia-predictor/training_scripts/eda/`](../ia-predictor/training_scripts/eda/)
**Métricas cruas**: [`results/metrics/eda_source.json`](../ia-predictor/training_scripts/results/metrics/eda_source.json) ·
[`results/metrics/eda_series.json`](../ia-predictor/training_scripts/results/metrics/eda_series.json)
**Figuras**: [`results/plots/eda/`](../ia-predictor/training_scripts/results/plots/eda/)

---

## 0. Por que dois EDAs

O CRISP-DM coloca a **compreensão dos dados** antes da **preparação**, mas o ciclo
é iterativo: depois de preparar, olha-se de novo, agora com os dados no formato que
o modelo vai consumir. Este relatório cobre os **dois momentos**, com objetos e
perguntas distintos:

| | EDA 1 — antes da preparação | EDA 2 — depois da preparação |
| --- | --- | --- |
| **Objeto** | base transacional (`contas_a_receber.csv`, 1 linha por documento×produto) | as 9 séries diárias `unidade × categoria` (alvo do L1) |
| **Pergunta** | o que existe? com que qualidade? o que condiciona as regras de pré-processamento? | essas séries sustentam um SARIMAX? com quais parâmetros? |
| **Alimenta** | dicionário de dados, regras de limpeza, taxonomia, triagem de exógenas | ordem do SARIMAX, `log1p`, exógenas de calendário, limiares de confiança |
| **Fase CRISP-DM** | compreensão dos dados | volta à compreensão, com dados preparados |

Reproduzir:

```bash
cd ia-predictor
python -m training_scripts.preprocessing.map_taxonomy   # gera o CSV da Etapa 3
python -m training_scripts.eda.run_all                    # roda EDA 1 + EDA 2
```

---

## 1. Sumário executivo

### 1.1 O que a EDA confirmou (premissas do projeto que se sustentam)

| Premissa | Evidência |
| --- | --- |
| **Modelar SKU como série temporal é inviável** — daí a camada L2 | SKU mediano tem **9 dias com venda** em 789 dias de calendário (densidade 1,1%); **72,2%** dos SKUs cairiam no *fallback* de rateio uniforme da L2 (< 28 dias com venda ou < 8 vendas); **13,2%** venderam uma única vez |
| **Agregar em `unidade × categoria` produz série densa** | os 9 pares têm **78–83% dos dias com venda**; maior sequência de zeros = 3–5 dias; todos ≥ 180 dias (mín. 221) |
| **Existe estrutura de calendário forte** (dia-da-semana + datas comemorativas) | ver §4.3 e §4.4 — efeitos de 2× a 5,6× em datas comemorativas para `Plantas de corte`; perfil semanal nítido e estável |
| **`d = 0` no SARIMAX** (ADR-004) | ADF rejeita raiz unitária (p < 0,05) nos 9 pares |
| **Excluir `pagamento`/`vendedor` das exógenas** (ADR-010) | 13 formas de pagamento e 38 vendedores — atributos de transação, desconhecidos no horizonte; sem papel de *driver* |
| **Estrutura de 3 categorias** (ADR-011) | volume concentra em `Produtos de jardim` (51,4%) e `Grama` (46,6%); `Plantas de corte` = 1,9% mas densa (≥ 221 dias com venda por par) |

### 1.2 O que a EDA **contraria** — ajustes necessários

| Achado | Impacto | Onde ajustar |
| --- | --- | --- |
| **"Fim de semana vende mais" está errado.** É o oposto: sábado vende **36% da média**, domingo é **loja fechada** (0), e o pico de volume é **terça/quarta** (`Grama`, `Produtos de jardim`) ou **sexta** (`Plantas de corte`). Padrão de *garden center* / paisagismo B2B, não de floricultura de presente. | O `m = 7` continua, mas o texto do `CLAUDE.md` e do ADR-001/009 sobre "fim de semana vende mais" precisa ser corrigido. As **dummies de dia-da-semana** (exógenas) vão explicar mais que os termos sazonais `P/Q`. | `CLAUDE.md` (tabela L1), `docs/prediction/ADR-001` / `ADR-009` |
| **Todos os 9 pares precisam de `log1p`** (CV de 1,3 a 4,5; assimetria de 3 a 20), não "alguns". | Aplicar `log1p` incondicionalmente no L1, ou baixar `LOG_CV_THRESHOLD`. `Itabirito · Grama` (CV 4,5, dia-pico = 79× a média) e as duas `Plantas de corte` de maior variância podem ficar `low_confidence` mesmo com `log1p`. | `config.py` (`LOG_CV_THRESHOLD`), `domain/models/` |
| **`Plantas de corte` é quase ruído branco na parte ARIMA** (`Jardim Canadá`: ACF ≈ 0 em todos os lags, Ljung-Box p = 0,99). A previsibilidade vem **inteira** das exógenas de calendário. | A parte `(p,d,q)(P,D,Q)` do SARIMAX vai colapsar para média + regressão. Uma **regressão de calendário simples (linear/RF)** é concorrente séria — reforça a comparação acadêmica (ii). | `plano_experimentos_modelagem.md` (incluir baseline de regressão de calendário) |
| **Efeito de data comemorativa é dependente da categoria e às vezes negativo.** `Grama` **cai** no Dia das Mães (0,6–0,8×) e no Natal (0,5×) — canibalização; `Plantas de corte` dispara (2–5,6×). | A exógena "dias até a data comemorativa" **não pode** ser um único regressor global — tem de ser por par (o L1 já é por par ✔) ou interagida com `categoria`. | `domain/features/calendar_exogenous.py` |
| **Tendências fortes e divergentes por loja.** `Jardim Canadá` encolhe (`Grama` −37%/ano, `Produtos de jardim` −49%/ano); `Itabirito` cresce (`Grama` +96%/ano, `Plantas de corte` +29%/ano). | Com `d = 0`, o SARIMAX precisa de **termo de tendência/constante** ou de reavaliar `d = 1` nesses pares. ADF e KPSS **divergem** exatamente nos pares com tendência. | `domain/models/order_selection.py` (permitir `trend='t'`/`d=1` condicional) |
| **`Garden Center` tem < 1 ano de histórico** (abriu 13/02/2025; 221–302 dias com venda). | Acima do mínimo de 180, mas **sem ciclo anual completo** — cada data comemorativa foi vista 1×. Previsões dessa loja com IC mais largo / `low_confidence` no 1º ano. | dashboard (aviso visual), `evaluator.py` |
| **Participação de SKU dentro da categoria é instável** mesmo em janela mensal (CV do share dos top-10 = 0,67 a 2,0). | A L2 com "média móvel de 4–8 semanas" vai ser ruidosa; a janela precisa ser mais longa e o *fallback* é **carregador**, não exceção. Teto de acurácia por SKU limitado — argumento central da comparação (ii). | `domain/disaggregation/` (janela, suavização) |

### 1.3 Qualidade dos dados — resumo

| Item | Resultado | Ação |
| --- | --- | --- |
| Meses faltando | **nenhum** (26/26, jan/2024–fev/2026) | — |
| Codificação | fonte é **UTF-8 válido** (sem mojibake); `unidade` derivada limpa | — |
| `emissao` não parseável | **0** | — |
| `qtdade <= 0` | **880 linhas** (44 negativas = devolução, 836 zeros) | limpar no `normalizer.py` de produção (já previsto) — **confirmar regra de devolução com a parceira** |
| `qtdade` fracionária | 2.279 linhas (grama/terra por m²/kg) — **legítimo** | manter `float` na série |
| Integridade documento (Σ linhas ≈ total do doc) | **90,2%** batem em ±R$ 0,02 | os ~10% de divergência vêm de documentos com serviço/frete fora das linhas de produto — não bloqueia |
| `icms_ret` | constante = 0 | removida na Etapa 2 ✔ |
| `obs` | 89% nula, com quebras de linha | removida na Etapa 2 ✔ |

---

## 2. EDA 1 — Compreensão dos dados

### 2.1 Volume e completude da fonte

| Métrica | Valor |
| --- | --- |
| Linhas (documento × produto) | 333.019 |
| Documentos distintos | 62.553 |
| SKUs distintos | 5.166 |
| Arquivos de origem | 26 XLSX mensais |
| Período | 02/01/2024 – 28/02/2026 |
| Meses esperados × presentes | 26 × 26 — **sem lacunas** |
| Dias de calendário no período | 789 |
| Dias com ≥ 1 venda | 654 (os 135 restantes = domingos + feriados; loja fechada) |

**Linhas por mês** (amostra): mai/2024 = 14.437 · mai/2025 = 14.465 · out/2025 =
16.299 (pico) · jan/2026 = 10.144 · **fev/2026 = 9.352**.

**Completude da ponta da série** — `fev/2026` tem 9.352 linhas, comparável a
`fev/2024` (9.259) e `fev/2025` (11.437). **Não aparenta export parcial**, mas
**confirmar com a parceira** (§6, item 1): se for parcial, a última quinzena da
série de treino estaria truncada e enviesaria a validação.

→ Figura [`01_transacoes_por_mes_unidade.png`](../ia-predictor/training_scripts/results/plots/eda/01_transacoes_por_mes_unidade.png)

### 2.2 Dicionário de dados da fonte

Documento dedicado, campo a campo (20 colunas, semântica, faixa de valores, etapa
de remoção e ADR): **[`docs/database/dicionario_dados_fonte.md`](database/dicionario_dados_fonte.md)**.

Resumo do destino das 20 colunas:

- **Mantidas até a modelagem (9)**: `emissao`, `empresa`, `produto_cod`, `qtdade`
  (alvo), `vl_unit`, `vl_total`, `vl_desconto`, `tot_liq`, `total_liquido_doc`.
- **Removidas na Etapa 2 (11)**: `doc_tipo`, `doc_numero`, `pagamento`, `operador`,
  `cliente_cod`, `cliente_nome` (PII), `vendedor`, `obs`, `produto_nome` (reusada
  1× na Etapa 3), `icms_ret` (constante), `arquivo_origem`.
- **Derivadas na Etapa 3 (3)**: `unidade`, `categoria`, `categoria_fina`.

### 2.3 Perfil por unidade

| Unidade | Linhas | SKUs | Qtd total | Faturamento (`tot_liq`) | 1ª venda | Dias c/ venda |
| --- | --- | --- | --- | --- | --- | --- |
| **Jardim Canadá** | 168.063 | 4.155 | 2.212.951 | R$ 26,5 mi | 02/01/2024 | 650 |
| **Itabirito** | 135.548 | 4.146 | 1.328.388 | R$ 16,6 mi | 02/01/2024 | 653 |
| **Garden Center** | 29.408 | 2.492 | 405.248 | R$ 6,1 mi | **13/02/2025** | 308 |

Jardim Canadá é a maior operação; Garden Center abriu (no registro) em fev/2025 —
**~12 meses de histórico**, sem ciclo anual fechado.

### 2.4 Perfil por categoria

**Categoria L1** (a que vira modelo):

| Categoria | Qtd total | Share | SKUs | Linhas |
| --- | --- | --- | --- | --- |
| Produtos de jardim | 2.028.097 | 51,4% | 5.043 | 285.934 |
| Grama | 1.837.995 | 46,6% | **14** | 17.286 |
| Plantas de corte | 74.634 | 1,9% | 107 | 24.457 |
| *Servico e taxa* (não-produto) | 5.860 | 0,1% | 2 | 5.342 |

`Grama` move quase metade do volume com **14 SKUs** — categoria concentrada, poucos
tipos (esmeralda, são-carlos, amendoim…). `Produtos de jardim` é a cauda longa
(5.043 SKUs). `Plantas de corte` é pequena em volume mas **não é rala** no tempo.

→ Figura [`05_volume_categoria_fina.png`](../ia-predictor/training_scripts/results/plots/eda/05_volume_categoria_fina.png)

### 2.5 Esparsidade da série diária por SKU → justifica a L2

| Métrica (por SKU) | Valor |
| --- | --- |
| Dias com venda — mediana | **9** (de 789 dias de calendário) |
| Dias com venda — média / p90 / máx | 36 / 86 / 653 |
| Densidade da série (dias ativos / calendário) — mediana | **1,1%** |
| SKUs com série ≥ 20% dos dias | 5,1% |
| SKUs com série ≥ 50% dos dias | 1,3% |
| SKUs que caem no *fallback* L2 (< 28 dias c/ venda ou < 8 vendas) | **72,2%** |
| SKUs com uma única venda no período inteiro | 13,2% |

Uma série 99% zerada não sustenta SARIMAX (não há tendência, autocorrelação nem
sazonalidade estimáveis). **Confirma a arquitetura hierárquica**: modelar a
demanda no agregado denso (L1) e repartir por participação (L2), em vez de milhares
de modelos por SKU.

→ Figura [`03_esparsidade_dias_ativos_sku.png`](../ia-predictor/training_scripts/results/plots/eda/03_esparsidade_dias_ativos_sku.png)

### 2.6 Concentração de volume (Pareto por SKU)

| Marco | SKUs | % dos SKUs |
| --- | --- | --- |
| 50% do volume | 7 | 0,14% |
| 80% do volume | 86 | 1,7% |
| 90% do volume | 253 | 4,9% |
| 95% do volume | 571 | 11,1% |

Top-20 SKUs = **61,7%** do volume; top-100 = **81,6%**. Sustenta
`TOP_N_PRODUCTS = 20` para a desagregação/relatório detalhado — mas ver §4.10: o
share desses líderes **não é estável no tempo**.

→ Figura [`04_pareto_volume_sku.png`](../ia-predictor/training_scripts/results/plots/eda/04_pareto_volume_sku.png)

### 2.7 Sazonalidade preliminar (contagem de transações)

Transações por dia da semana (toda a base): sex 66.119 · seg 54.848 · sáb 59.703
· **dom 1.130**. Índice fim-de-semana vs. média = **0,64**.

> O perfil **por volume de `qtdade`** e **por par** está na §4.3 (é o que importa
> para o modelo). A contagem mensal agregada da fonte é confundida (pool de
> 2024+2025+2026, alguns meses com 3 anos de dado) — não usar para sazonalidade
> anual; usar o índice mensal **por par** da §4.4.

→ Figura [`02_sazonalidade_semanal_unidade.png`](../ia-predictor/training_scripts/results/plots/eda/02_sazonalidade_semanal_unidade.png)

### 2.8 Qualidade de dados

Ver §1.3. Detalhe dos nulos: só `obs` (89%) e `cliente_cod` (17 linhas). Nenhuma
coluna usada pela modelagem tem nulo. `total_liquido_doc` tem 38.803 zeros
(documentos de valor líquido zero — bonificação/troca) e 42 negativos (devolução).

### 2.9 Exógenas nominais descartadas (registro do ADR-010)

`pagamento` (13 valores; mix: crédito 39%, débito 23%, PIX 19%, dinheiro 12%,
boleto/a-prazo/vale/link o resto) e `vendedor` (38) **não entram** como exógenas
do L1: são atributos de transação, **desconhecidos no horizonte de previsão**
(*leakage*) e consequência — não *driver* — da venda. Registrado aqui para
rastreabilidade; decisão em
[ADR-010](prediction/ADR-010-exogenas-nominais-fora-do-l1.md).

---

## 3. EDA 2 — Série modelável (as 9 séries L1)

Série-alvo reconstruída como `prepare_daily_series` fará: soma de `qtdade` por dia
por par `(unidade, categoria)`, reindexada no calendário diário contínuo do par
(dias sem venda = 0).

### 3.1 Densidade e cobertura

| Par | Dias c/ venda | % do calendário | Maior seq. de zeros | SKUs |
| --- | --- | --- | --- | --- |
| Jardim Canadá · Grama | 645 | 81,7% | 3 | 11 |
| Jardim Canadá · Plantas de corte | 641 | 81,3% | 4 | 86 |
| Jardim Canadá · Produtos de jardim | 650 | 82,4% | 3 | 4.054 |
| Itabirito · Grama | 641 | 81,2% | 5 | 13 |
| Itabirito · Plantas de corte | 653 | 82,8% | — | 101 |
| Itabirito · Produtos de jardim | 653 | 82,8% | — | 4.028 |
| Garden Center · Grama | 299 | 78,5% | — | 9 |
| Garden Center · Plantas de corte | **221** | **59,9%** | — | 63 |
| Garden Center · Produtos de jardim | 302 | 80,7% | — | 2.418 |

Os ~18% de dias zerados nos pares grandes são **quase todos domingos** (14,3%) +
feriados — zero **estrutural e previsível**, não intermitência. `Garden Center ·
Plantas de corte` é a exceção: 30% dos **dias úteis** zerados — série curta e rala.

→ Figura [`10_series_l1_9paineis.png`](../ia-predictor/training_scripts/results/plots/eda/10_series_l1_9paineis.png)

### 3.2 Distribuição da quantidade diária → `log1p`

| Par | Média/dia | CV | Assimetria | Dia-pico ÷ média | `log1p`? |
| --- | --- | --- | --- | --- | --- |
| Jardim Canadá · Grama | 1.263 | 1,31 | 3,0 | 12× | sim |
| Jardim Canadá · Plantas de corte | 43 | **3,56** | **20,4** | **90×** | sim |
| Jardim Canadá · Produtos de jardim | ~1.900 | 1,53 | — | — | sim |
| Itabirito · Grama | 781 | **4,49** | **10,3** | **79×** | sim |
| Itabirito · Plantas de corte | ~30 | 1,55 | — | — | sim |
| Itabirito · Produtos de jardim | ~1.400 | 1,82 | — | — | sim |
| Garden Center · Grama | — | 1,46 | — | — | sim |
| Garden Center · Plantas de corte | — | 1,84 | — | — | sim |
| Garden Center · Produtos de jardim | — | 1,33 | — | — | sim |

**Todos** acima de `LOG_CV_THRESHOLD = 0,7`. As duas séries de CV extremo
(`Itabirito · Grama`, `Jardim Canadá · Plantas de corte`) são dominadas por
**pedidos B2B pontuais** (um dia = 61.561 unidades de grama; um dia = 3.882 hastes
véspera de Dia das Mães) — `log1p` ajuda mas não elimina o risco de
`low_confidence`.

→ Figura [`14_dist_qtd_diaria_l1.png`](../ia-predictor/training_scripts/results/plots/eda/14_dist_qtd_diaria_l1.png)

### 3.3 Sazonalidade semanal (m = 7) — **corrige a premissa do projeto**

Índice de demanda por dia da semana (1,0 = média do par):

| Par | seg | ter | qua | qui | sex | sáb | dom |
| --- | --- | --- | --- | --- | --- | --- | --- |
| JC · Grama | 1,14 | 1,45 | **1,55** | 1,30 | 1,12 | 0,43 | 0,00 |
| JC · Plantas de corte | 0,90 | 1,53 | 0,51 | 1,27 | **1,69** | 1,09 | 0,00 |
| JC · Produtos de jardim | 1,12 | 1,11 | 1,32 | **1,44** | 1,27 | 0,74 | 0,00 |
| Itab · Grama | 1,51 | **2,08** | 1,24 | 1,06 | 0,96 | 0,14 | 0,00 |
| Itab · Plantas de corte | 1,04 | 0,81 | 0,78 | 0,93 | **1,96** | 1,35 | 0,13 |
| Itab · Produtos de jardim | **1,43** | 0,94 | 1,27 | 1,30 | 1,42 | 0,63 | 0,02 |
| GC · Grama | 1,23 | **1,83** | 1,65 | 0,87 | 1,06 | 0,38 | 0,00 |
| GC · Plantas de corte | 1,40 | 0,67 | 0,59 | 0,84 | **2,19** | 1,30 | 0,00 |
| GC · Produtos de jardim | 1,25 | 1,35 | **1,58** | 0,91 | 1,25 | 0,68 | 0,00 |

**Leitura:**

- **Domingo = loja fechada** (índice 0,00–0,13). Zero determinístico.
- **Sábado é fraco** para `Grama` (0,14–0,43) e `Produtos de jardim` (0,63–0,74);
  **razoável** só para `Plantas de corte` (1,09–1,35 — presente de fim de semana).
- **`Grama` e `Produtos de jardim` picam no meio da semana** (ter/qua/qui) —
  compra de paisagista/pedreiro em dia útil.
- **`Plantas de corte` pica na sexta** (1,7–2,2) — consumo pessoal para o fim de
  semana.
- A **premissa "fim de semana vende mais"** (`CLAUDE.md`, ADR-001/009) **não se
  sustenta**. O ciclo `m = 7` é real, mas **invertido** em relação ao pressuposto,
  e sua **força na variância é baixa** (STL Fs = 0,00–0,27) porque o ruído
  diário (pedidos grandes) domina. Consequência de modelagem: as **dummies de
  dia-da-semana como exógenas** vão explicar mais que os termos sazonais
  `(P, Q)` do SARIMA.

→ Figuras [`11_perfil_dia_semana_l1.png`](../ia-predictor/training_scripts/results/plots/eda/11_perfil_dia_semana_l1.png) ·
[`02_sazonalidade_semanal_unidade.png`](../ia-predictor/training_scripts/results/plots/eda/02_sazonalidade_semanal_unidade.png)

### 3.4 Sazonalidade anual e datas comemorativas

**Efeito de data comemorativa** (razão da média na janela D-2…D vs. média geral do par):

| Par | Mães | Namorados | Mulher | Pais | Finados | Natal |
| --- | --- | --- | --- | --- | --- | --- |
| JC · Grama | 0,79 | 1,30 | 0,60 | 0,17 | 0,71 | 0,52 |
| JC · Plantas de corte | **2,38** | 1,67 | **4,18** | 0,75 | 1,13 | **2,17** |
| JC · Produtos de jardim | 0,59 | 1,13 | 0,78 | 0,61 | 0,65 | 0,43 |
| Itab · Grama | 0,19 | 0,64 | 0,52 | 0,16 | **3,33** | 0,50 |
| Itab · Plantas de corte | **4,87** | **3,60** | **3,98** | 1,19 | **5,62** | 1,11 |
| Itab · Produtos de jardim | 0,94 | **2,21** | 0,74 | 0,49 | **2,47** | 0,44 |
| GC · Grama | 0,60 | 0,81 | 0,58 | 0,18 | 0,59 | 0,82 |
| GC · Plantas de corte | 0,00* | 1,24 | 0,00* | 0,52 | 1,66 | 0,75 |
| GC · Produtos de jardim | 0,16 | 0,82 | 0,06 | 0,31 | 0,86 | 0,49 |

\* Garden Center abriu depois do Dia das Mães/Mulher de 2025 — janela sem dados.

**Leitura:**

- **`Plantas de corte`**: a categoria "presente". Dispara em Dia das Mães, Mulher,
  Namorados, Finados (2,2–5,6×). É onde a exógena "dias até a data comemorativa"
  vale ouro.
- **`Grama`**: **canibalização** — o cliente compra flor, não grama, na semana da
  data (índices 0,2–0,8). Exceção: `Itabirito · Grama` no **Finados** (3,3×) —
  paisagismo de cemitério.
- **`Produtos de jardim`**: efeito modesto e misto; algum empurrão em Namorados e
  Finados em Itabirito.
- **Consequência**: a exógena de data comemorativa **precisa ser por par**
  (o L1 já é) ou interagida com `categoria` — um coeficiente global teria sinal
  trocado entre `Grama` e `Plantas de corte`.

**Sazonalidade mensal** (índice, 1,0 = média do par) — destaques:

- `Jardim Canadá · Grama`: pico em **outubro (1,61)** e nov (1,19) — primavera,
  época de plantio; vale em abr–mai–ago (~0,78).
- `Itabirito · Grama`: **dezembro (3,37)** e nov (1,71) — concentração de fim de
  ano brutal.
- `Jardim Canadá · Plantas de corte`: **abril (2,09)** — preparação do Dia das Mães.
- `Itabirito · Plantas de corte`: **dezembro (1,69)**, out (1,47), mai (1,30).

→ Figura [`12_perfil_mensal_l1.png`](../ia-predictor/training_scripts/results/plots/eda/12_perfil_mensal_l1.png)

### 3.5 Tendência

| Par | Inclinação (%/ano da média) | Δ primeiros 90d → últimos 90d |
| --- | --- | --- |
| **Jardim Canadá · Produtos de jardim** | **−49%** | −63% |
| **Jardim Canadá · Grama** | **−37%** | −48% |
| Jardim Canadá · Plantas de corte | −31% | +12% |
| **Itabirito · Grama** | **+96%** | +593% |
| Itabirito · Plantas de corte | +29% | +50% |
| Itabirito · Produtos de jardim | +18% | +46% |
| Garden Center (3 pares) | +16% a +106% | (ramp-up de loja nova) |

**Jardim Canadá encolhe, Itabirito cresce.** Pode ser deslocamento real de
demanda entre lojas, mudança de mix, ou mudança na captura do relatório —
**pergunta para a parceira** (§6, item 5). Impacto: com `d = 0`, esses pares
precisam de **termo de tendência/deriva** no SARIMAX, ou reavaliar `d = 1`.

### 3.6 Estacionariedade (define `d`)

ADF rejeita raiz unitária (p < 0,05) nos **9 pares** → suporta `d = 0` (ADR-004).
KPSS **diverge** (rejeita estacionariedade) nos pares com tendência forte
(`Itabirito · Grama`, `Jardim Canadá · Produtos de jardim`, ambos `Plantas de
corte` de Canadá parcial). Recomendação: **`d = 0` como padrão + termo `trend`**;
testar `d = 1` só nos 3–4 pares onde ADF e KPSS discordam, comparando por AIC e
resíduo (o `order_selection.py` já faz busca — só ampliar o range de `d` para
esses pares).

→ Figura [`15_stl_par_denso.png`](../ia-predictor/training_scripts/results/plots/eda/15_stl_par_denso.png)

### 3.7 Autocorrelação (define `p, q, P, Q`)

| Par | ACF lag 1 | ACF lag 7 | Ljung-Box lag 7 (p) | autocorr. significativa? |
| --- | --- | --- | --- | --- |
| JC · Grama | 0,18 | 0,20 | 1e-13 | sim |
| JC · Plantas de corte | 0,00 | **0,01** | **0,99** | **não** |
| JC · Produtos de jardim | — | 0,12 | — | sim (fraca) |
| Itab · Grama | −0,01 | 0,19 | 2e-6 | sim |
| Itab · Plantas de corte | — | 0,15 | — | sim |
| Itab · Produtos de jardim | — | **0,06** | — | **não** |
| GC · Grama | — | 0,30 | — | sim |
| GC · Plantas de corte | — | 0,20 | — | sim |
| GC · Produtos de jardim | — | 0,28 | — | sim |

- ACF **baixa em todos os lags** (< 0,3 mesmo no lag 1) — pouca memória de curto
  prazo; o dia-a-dia é dominado por dia-da-semana + ruído, não por inércia.
- **Bump visível nos lags 7 e 14** para Garden Center (3), `Itabirito · Grama`,
  `Jardim Canadá · Grama` — confirma `m = 7`, fraco.
- **`Jardim Canadá · Plantas de corte` e `Itabirito · Produtos de jardim` são
  ruído branco** na estrutura ARIMA (Ljung-Box não rejeita). Para esses, o
  SARIMAX vira **regressão com exógenas de calendário** — a parte `(p,q)(P,Q)`
  não tem o que capturar.
- **Ordens esperadas**: `p, q` baixos (0–1), `P, Q ∈ {0, 1}` com peso pequeno. O
  grid atual (`p,q ≤ 2`, `P,Q ≤ 1`) cobre; o AIC provavelmente escolherá modelos
  enxutos.

→ Figura [`13_acf_l1_9paineis.png`](../ia-predictor/training_scripts/results/plots/eda/13_acf_l1_9paineis.png)

### 3.8 Outliers

Dias acima de média + 3σ: 4 a 16 por par. Concentrados em:

- **Fim de ano** (`Itabirito · Grama`: 16/12/2025 = 61.561; `Jardim Canadá ·
  Produtos de jardim`: 31/01/2024 = 40.406).
- **Vésperas de data comemorativa** (`Jardim Canadá · Plantas de corte`:
  30/04/2024 = 3.882, véspera do Dia das Mães).

São **pedidos B2B/paisagismo reais**, não erro de dado — não remover. Tratamento:
`log1p` + o modelo os absorve como cauda; monitorar resíduo. Um regressor
"pedido-grande" (flag) é opção futura se a parceira conseguir marcar contrato de
paisagismo.

### 3.9 Veredito por par para o L1

| Par | Veredito | Ressalvas principais |
| --- | --- | --- |
| **Itabirito · Plantas de corte** | ✅ ok | — |
| **Jardim Canadá · Grama** | ✅ ok | tendência de queda (−37%/ano) — termo de trend |
| Jardim Canadá · Produtos de jardim | ⚠️ atenção | Fs baixo; sem autocorr.; trend −49%/ano → exógenas carregam |
| Itabirito · Produtos de jardim | ⚠️ atenção | Fs baixo; ruído branco na parte ARIMA |
| Itabirito · Grama | ⚠️ atenção | CV 4,5; dia-pico 79× média; trend +96%/ano — candidato a `low_confidence` |
| Jardim Canadá · Plantas de corte | ⚠️ atenção | ruído branco (Ljung-Box p=0,99); dia-pico 90× — quase só calendário |
| Garden Center · Grama | ⚠️ atenção | 299 dias — sem ciclo anual |
| Garden Center · Produtos de jardim | ⚠️ atenção | 302 dias — sem ciclo anual |
| Garden Center · Plantas de corte | ⚠️ atenção | 221 dias; 30% de dias úteis zerados; trend +106% |

"Atenção" ≠ falha — a previsão é gerada, com aviso visual no dashboard
(`low_confidence`), conforme a política de limiares do `CLAUDE.md`. **Nenhum par
cai em `insufficient_data`** (todos ≥ 180 dias).

### 3.10 Estabilidade de share por SKU dentro da categoria → parâmetros da L2

| Par | Nº SKUs | SKUs p/ 80% vol. | Share do 1º SKU | CV do share mensal (top-10) | Leitura |
| --- | --- | --- | --- | --- | --- |
| JC · Grama | 11 | 2 | 61% | 2,01 | instável — poucos SKUs, lumpy |
| Itab · Grama | 13 | 2 | 70% | 2,04 | instável |
| GC · Grama | 9 | 2 | 49% | 2,02 | instável |
| JC · Plantas de corte | 86 | 11 | 26% | 0,98 | instável |
| Itab · Plantas de corte | 101 | 11 | 26% | **0,67** | menos instável |
| GC · Plantas de corte | 63 | 8 | 20% | 1,05 | instável |
| JC · Produtos de jardim | 4.054 | 175 | 4% | **0,77** | menos instável |
| Itab · Produtos de jardim | 4.028 | 206 | 5% | 1,26 | instável |
| GC · Produtos de jardim | 2.418 | 141 | 5% | 1,07 | instável |

**Nenhum par tem share de SKU estável** (CV alvo < 0,5). Mesmo os líderes oscilam
mês a mês. Implicações para a L2:

1. A janela de "média móvel de 4–8 semanas" do ADR-009 é **curta demais** — testar
   8–12 semanas, ou EWMA.
2. O *fallback* (rateio uniforme / share da categoria) atende **72% dos SKUs** e
   pega parte dos outros 28% em semanas ruins — é **componente principal**, não
   exceção.
3. Há um **teto de acurácia por SKU** imposto pela volatilidade do mix. É o
   argumento empírico central da **comparação acadêmica (ii)**: medir se
   Croston/TSB/SBA por SKU batem o L1+L2 exatamente onde o top-down sofre.

---

## 4. Impacto consolidado no pré-processamento e na modelagem

| # | Ajuste | Arquivo/artefato | Prioridade |
| --- | --- | --- | --- |
| 1 | Corrigir o texto "fim de semana vende mais" → "meio de semana (ter–qui) para Grama/Jardim; sexta para Plantas de corte; sábado fraco; domingo fechado" | `CLAUDE.md`, `ADR-001`, `ADR-009` | alta (é premissa errada citada em vários docs) |
| 2 | `log1p` para os 9 pares (não condicional) — ou baixar `LOG_CV_THRESHOLD` para ~0,5 | `config.py`, `domain/models/` | alta |
| 3 | Exógena de data comemorativa **por par / interagida com categoria** (sinal se inverte entre Grama e Plantas de corte) | `domain/features/calendar_exogenous.py` | alta |
| 4 | Dummies de dia-da-semana como exógenas de 1ª classe (fazem mais que P/Q) | `calendar_exogenous.py`, `order_selection.py` | alta |
| 5 | Permitir `trend='t'` / `d=1` condicional nos pares onde ADF×KPSS divergem (Itab·Grama, JC·Produtos, JC·Plantas) | `order_selection.py` | média |
| 6 | Baseline de **regressão de calendário simples** (linear/RF) no plano de experimentos — para os pares "ruído branco" o SARIMAX não adiciona nada | `plano_experimentos_modelagem.md`, `training_scripts/alternative_models/` | média |
| 7 | L2: janela de share 8–12 semanas (ou EWMA); tratar *fallback* como caminho principal | `domain/disaggregation/` | média |
| 8 | `Garden Center` e pares com CV extremo → `low_confidence` no 1º ano / IC largo; aviso no dashboard | `evaluator.py`, front | média |
| 9 | Regra de `qtdade` negativa (devolução) — definir com a parceira e implementar no `normalizer.py` | `domain/etl/normalizer.py` | baixa (44 linhas) |
| 10 | `map_taxonomy.py` / `reduce_schema.py`: passar `encoding='utf-8'` explícito no `to_csv` (defensivo; hoje o resultado está correto neste ambiente, mas depende do locale) | `training_scripts/preprocessing/` | baixa |

---

## 5. Questões abertas para a parceira (validação da fonte)

1. **`fev/2026` é mês fechado ou export parcial?** (9.352 linhas — aparenta
   completo, mas confirmar para não truncar a ponta da série de treino/validação.)
2. **O relatório "Contas a Receber" captura 100% das saídas de mercadoria?** Ou só
   as que geram título financeiro? Brinde, bonificação, consumo interno, ajuste de
   inventário entram?
3. **Algum `doc_tipo` não é venda real** e deve ser excluído da série de demanda
   (além de `Servico e taxa`)? Ex.: condicional (`CN`?), devolução (`NN`?).
4. **`qtdade` negativa (44 linhas) — são sempre devolução?** Devem abater a demanda
   do dia da devolução, do dia da venda original, ou ser ignoradas?
5. **A queda em Jardim Canadá e a alta em Itabirito são reais?** (Ex.: obra de
   grande porte migrou de loja, mudança de política de faturamento entre CNPJs,
   ou mudança de como o relatório é gerado.)
6. **Curadoria fina de SKUs em `Outros`** (1,3% do volume) — interessa à L2, não
   muda o L1.

---

## 6. Reprodutibilidade

| Artefato | Caminho |
| --- | --- |
| Infra comum (carga, calendário, plots) | `ia-predictor/training_scripts/eda/_common.py` |
| EDA 1 (fonte) | `ia-predictor/training_scripts/eda/eda_source.py` |
| EDA 2 (série) | `ia-predictor/training_scripts/eda/eda_series.py` |
| Runner | `ia-predictor/training_scripts/eda/run_all.py` |
| Métricas EDA 1 | `ia-predictor/training_scripts/results/metrics/eda_source.json` |
| Métricas EDA 2 | `ia-predictor/training_scripts/results/metrics/eda_series.json` |
| Figuras (11 PNG) | `ia-predictor/training_scripts/results/plots/eda/` |
| Dicionário de dados da fonte | [`docs/database/dicionario_dados_fonte.md`](database/dicionario_dados_fonte.md) |

Dependências além do `requirements.txt`: `matplotlib`, `seaborn` (já em
`requirements-dev.txt`); `scipy` e `statsmodels` (já em `requirements.txt`).

```bash
cd ia-predictor
pip install -r requirements.txt -r requirements-dev.txt
python -m training_scripts.preprocessing.build_dataset     # se output/ estiver vazio
python -m training_scripts.preprocessing.reduce_schema
python -m training_scripts.preprocessing.map_taxonomy
python -m training_scripts.eda.run_all
```

### Índice de figuras

| Arquivo | Conteúdo | Seção |
| --- | --- | --- |
| `01_transacoes_por_mes_unidade.png` | Volume mensal empilhado por loja | 2.1 |
| `02_sazonalidade_semanal_unidade.png` | Qtd média/linha por dia da semana × loja | 2.7 / 3.3 |
| `03_esparsidade_dias_ativos_sku.png` | Histograma de dias com venda por SKU | 2.5 |
| `04_pareto_volume_sku.png` | Curva de Pareto do volume por SKU | 2.6 |
| `05_volume_categoria_fina.png` | Volume por `categoria_fina` | 2.4 |
| `10_series_l1_9paineis.png` | As 9 séries diárias + média móvel 28d | 3.1 |
| `11_perfil_dia_semana_l1.png` | Índice de dia-da-semana por par | 3.3 |
| `12_perfil_mensal_l1.png` | Índice mensal por par | 3.4 |
| `13_acf_l1_9paineis.png` | ACF (lags 0–21) dos 9 pares | 3.7 |
| `14_dist_qtd_diaria_l1.png` | Histograma da qtd diária por par | 3.2 |
| `15_stl_par_denso.png` | Decomposição STL do par de maior volume | 3.6 |

---

## 7. Metodologia detalhada por análise

Como cada número/figura dos §2 e §3 foi calculado — técnica, biblioteca e
parâmetros. Todo o código está em `ia-predictor/training_scripts/eda/`
(`_common.py` = infraestrutura compartilhada; `eda_source.py` = EDA 1;
`eda_series.py` = EDA 2); stack: `pandas`/`numpy` para agregação,
`scipy.stats` para forma da distribuição, `statsmodels` para os testes de
série temporal, `matplotlib`/`seaborn` para as figuras. Nenhuma análise usa
amostragem — os 333.019 registros e as 9 séries completas são processados
inteiros.

### 7.1 Preparação comum (`_common.py`)

- **Carga resiliente** (`_read_csv_resiliente`): tenta decodificar o CSV em
  `utf-8`, depois `latin-1`, depois `cp1252`; último recurso substitui bytes
  inválidos (`encoding_errors="replace"`) em vez de falhar — necessário porque
  o CSV da Etapa 3 do pré-processamento é gravado sem encoding explícito e
  cai em `cp1252` neste Windows (achado registrado em §2.8/§1.3).
- **Canonicalização de rótulos** (`_canon`): `unidade` e `categoria` são
  normalizadas (strip + lowercase) e mapeadas para uma lista fechada de
  valores; qualquer rótulo fora do dicionário levanta erro imediatamente, em
  vez de virar categoria fantasma silenciosa.
- **Conversão numérica** (`_to_num`): trata separador de milhar `.` e decimal
  `,` (padrão BR) antes de `pd.to_numeric`.
- **Série-alvo do L1** (`serie_diaria`): soma de `qtdade_n` por dia para o par
  `(unidade, categoria)`, reindexada com `pd.date_range` no calendário diário
  contínuo do próprio par (`span="par"` = do primeiro ao último dia em que o
  par vendeu); dias sem transação viram `0.0` explícito — é essa série,
  idêntica à que `prepare_daily_series` vai gerar em produção, que alimenta
  todo o §3.
- **Calendário de datas comemorativas** (`datas_comemorativas`): Dia das
  Mães (2º domingo de maio) e Dia dos Pais (2º domingo de agosto) calculados
  por regra de calendário; Namorados/Finados/Natal/Dia da Mulher são datas
  fixas — tabela `(evento, ano, data)` para todos os anos cobertos pela base.
- Cada bloco de análise devolve um `dict` serializado em JSON
  (`dump_metrics`) — os números citados no relatório vêm diretamente desses
  arquivos (`results/metrics/eda_source.json`, `eda_series.json`), não de
  leitura visual de gráfico.

### 7.2 EDA 1 — técnicas por bloco (`eda_source.py`)

| Bloco (relatório) | Como foi calculado |
| --- | --- |
| §2.1 Volume/completude | Meses **presentes**: `Series.dt.to_period("M").value_counts()`. Meses **esperados**: `pd.period_range(min, max, freq="M")` — a diferença de conjuntos dá `meses_faltando`. Dias de calendário: `pd.date_range(min, max, freq="D")`; "dias com venda" = `nunique()` das datas normalizadas. |
| §2.3 Por unidade / §2.4 por categoria | `groupby("unidade"/"categoria")` com `sum` de `qtdade_n`/`tot_liq_n` e `nunique` de `produto_cod`; share = valor do grupo ÷ soma total. |
| §2.5 Esparsidade por SKU | Por `produto_cod`: dias ativos = `nunique()` de datas distintas com venda; densidade = dias ativos ÷ `span_dias_base` (intervalo entre a 1ª e a última venda **de toda a base**, não do SKU). Regra de *fallback* L2 replicada aqui exatamente como no domínio de produção: `(dias_ativos < 28) OR (n_vendas < 8)`. |
| §2.6 Pareto de SKU | `qtdade` somada por SKU, ordenada decrescente; `cumsum() / soma_total` dá a curva; o marco "N% do volume" é o menor `k` tal que a acumulada em `k` SKUs ≥ N%. |
| §2.7 Sazonalidade preliminar | Contagem de **linhas** (não quantidade) por `dayofweek`/mês — nota do relatório já registra que essa contagem mistura 2024+2025+2026 e por isso não serve para sazonalidade anual (só a versão por par em §3.4 serve). Índice fim de semana = média(sáb, dom) ÷ média geral. |
| §2.8 Qualidade | Nulos: `isna().sum()` por coluna do CSV bruto. Integridade de documento: agrupa por `(doc_numero, doc_tipo)`, compara `soma(tot_liq)` das linhas com `total_liquido_doc` (primeiro valor do grupo); "bate" = diferença absoluta ≤ R$ 0,02. Encoding: inspeção **binária** do arquivo — procura o byte-sequence UTF-8 de "CANADÁ" (`0xC3 0x81`) no CSV fonte e tenta `.decode("utf-8")` no CSV da Etapa 3, sem depender do `pandas` já ter mascarado o problema. |
| §2.9 Exógenas nominais | `groupby("pagamento"/"vendedor")` para contar categorias e o mix percentual — só para registrar a decisão do ADR-010, sem teste estatístico associado (é uma decisão de design: atributo de transação, não *driver* causal, e desconhecido no horizonte de previsão). |

### 7.3 EDA 2 — técnicas por bloco (`eda_series.py`)

Cada um dos 9 pares `unidade × categoria` passa pela mesma bateria de 9
análises (`analisa_par`), sobre a série diária reconstruída em `serie_diaria`:

| Bloco (relatório) | Técnica | Detalhe |
| --- | --- | --- |
| §3.1 Densidade | Contagem de sequência | Maior corrida de zeros consecutivos via varredura sequencial (contador que zera a cada valor não-zero); "atende_min_180d" = dias com venda ≥ `MIN_OBSERVATIONS_DAYS` (180, mesmo limiar do `config.py` de produção). |
| §3.2 Distribuição / `log1p` | CV, assimetria, curtose | `CV = desvio_padrão / média` sobre a série completa (incl. zeros); assimetria (`skew`) e curtose via `scipy.stats`; regra de decisão **idêntica à de produção**: `aplicar_log1p = CV > LOG_CV_THRESHOLD` (0,7, de `CLAUDE.md`/`config.py`). `pct_dias_zero_excl_domingo` isola intermitência real de fechamento estrutural. |
| §3.3 Sazonalidade semanal | Perfil + força STL | Perfil: média por `dayofweek` ÷ média geral = "índice do dia". Força do ciclo: decomposição **STL** (`statsmodels.tsa.seasonal.STL`, `period=7`, `robust=True` — robusto a outliers de pedidos B2B) e `Fs = max(0, 1 − Var(resíduo) / Var(resíduo + sazonal))`, a métrica padrão de Hyndman para "quanto da variância o componente sazonal explica" (0 = ciclo irrelevante, 1 = ciclo domina). |
| §3.4 Sazonalidade anual / datas comemorativas | Perfil mensal + janela de evento | Perfil mensal: média por mês-do-ano ÷ média geral. Efeito de data comemorativa: janela de **3 dias** (a data + 2 dias antes, `D-2…D`) por evento/ano, comparando a média da série nessa janela com a média geral do par inteiro — não com a média do mês, para isolar o efeito da data em si. |
| §3.5 Tendência | Regressão linear (OLS) | `numpy.polyfit(x, y, 1)` com `x` = índice sequencial de dias (não a data calendário, para inclinação em "unidade/dia"); "%/ano" = inclinação × 365 ÷ média da série. Segundo indicador, não-paramétrico: razão entre a média dos **primeiros 90 dias** e a dos **últimos 90 dias** da série — usado para checar se a tendência linear é só efeito de outlier isolado (concordância entre os dois valida o achado). |
| §3.6 Estacionariedade (`d`) | ADF + KPSS | **ADF** (`adfuller`, `autolag="AIC"`) — H0: existe raiz unitária (não-estacionária); rejeita se p < 0,05. **KPSS** (`kpss`, `regression="c"`, `nlags="auto"`) — H0 inversa: a série é estacionária em torno de constante; rejeita se p ≤ 0,05. Os dois são cruzados porque testam hipóteses opostas: ADF+KPSS concordando em "estacionária" → `d=0`; concordando em "não-estacionária" → sugere `d=1`; **divergência** (achado central do §3.6, presente nos pares com tendência forte) → mantém `d=0` mas sinaliza revisão por resíduo. p-valor do KPSS é limitado pela tabela do teste a `[0,01; 0,10]` — o script registra quando o valor bate nesse limite (`kpss_pvalue_no_limite_da_tabela`) para não ler falsa precisão. |
| §3.7 Autocorrelação (`p,q,P,Q`) | ACF/PACF + Ljung-Box | `acf`/`pacf` (`statsmodels.tsa.stattools`) até `min(21, n/2 − 1)` lags (`fft=True` na ACF, mais estável numericamente para séries longas); leitura nos lags 1 (memória de curto prazo), 7 e 14 (múltiplos da semana). **Ljung-Box** (`acorr_ljungbox`, lags 7 e 14) testa H0 = "os resíduos/série são ruído branco (sem autocorrelação conjunta até aquele lag)"; usado aqui de forma informativa sobre a série bruta (não sobre resíduo de modelo ajustado) para antecipar se a parte ARIMA terá o que capturar. |
| §3.8 Outliers | Z-score + IQR | Dia é outlier se `z = (x − média)/desvio > 3` (regra dos "3σ", usada para contar e ranquear os picos) **e** reportado também pelo critério robusto `x > Q3 + 3×IQR` (menos sensível à própria cauda pesada que o z-score, que usa média/desvio — enviesados pelos mesmos outliers). Os 5 maiores dias de cada par são listados com data e valor para inspeção manual (todos confirmados como pedidos B2B/datas comemorativas reais, não erro de digitação). |
| §3.9 Veredito por par | Heurística de regras | Função `_verdito` combina os resultados acima em texto: sinaliza "insuficiente" se dias com venda < 180; acumula ressalvas de "atenção" para histórico curto (< 400 dias, sem ciclo anual), intermitência de dias úteis > 12%, cauda extrema (pico > 30× a média), ciclo semanal fraco (`Fs < 0,1`), ausência de autocorrelação (Ljung-Box não rejeita) e tendência forte (> 40%/ano). Não é um modelo estatístico — é a mesma lógica de threshold que o `evaluator.py` de produção usará para `low_confidence`, aplicada aqui de forma antecipada aos dados brutos. |
| §3.10 Share de SKU (L2) | Participação mensal + CV | Para cada par, monta uma tabela `mês × SKU` (`pivot_table`, soma de `qtdade`) e calcula o **share mensal** de cada SKU (valor do mês ÷ total do mês). Para os 10 SKUs de maior volume no par, calcula o CV (`desvio/média`) do share **ao longo dos meses**; janela mensal (não semanal) escolhida deliberadamente para alinhar com a janela de 4–8 semanas do rateio L2 do ADR-009 e evitar inflar o CV com semanas estruturalmente zeradas do SKU. CV médio dos top-10 < 0,5 seria lido como "participação estável" — nenhum dos 9 pares atinge esse limiar (§3.10). |

### 7.4 Figuras — como cada uma foi gerada

Todas em `matplotlib` (`Agg`, sem exibição interativa), salvas via `savefig`
comum (`dpi=130`, `bbox="tight"`). Nenhuma figura usa suavização/estimativa
além do que está descrito: `10_series_l1_9paineis.png` sobrepõe a série
diária crua (cinza) com sua média móvel de 28 dias (`rolling(28,
min_periods=7).mean()`); `13_acf_l1_9paineis.png` usa `plot_acf` do
`statsmodels` com banda de confiança `alpha=0,05`; `15_stl_par_denso.png`
plota os 4 componentes (`observado`, `trend`, `seasonal`, `resid`) do mesmo
objeto `STL` usado para calcular `Fs` em §3.3, aplicado ao par de maior
volume.

### 7.5 Limitações do método

- **STL com `period=7` fixo**: assume um único ciclo semanal; não captura
  sazonalidade de múltiplas frequências (ex.: semanal + anual) simultaneamente
  — por isso a sazonalidade anual (§3.4) foi tratada à parte, por índice
  mensal simples, não por um segundo componente STL.
- **Ljung-Box na série bruta, não no resíduo de um modelo ajustado**: é uma
  leitura preliminar ("há alguma estrutura de autocorrelação a explorar?"),
  não substitui o diagnóstico de resíduo pós-ajuste do SARIMAX exigido pela
  Constituição do projeto (`CLAUDE.md` — Ljung-Box/Shapiro-Wilk por modelo
  treinado).
- **Efeito de data comemorativa por janela fixa de 3 dias**: não isola o
  efeito de "véspera" vs. "no dia" nem controla por tendência/mês — é uma
  razão simples de médias, suficiente para o veredito qualitativo do §3.4 mas
  não para estimar o coeficiente que a exógena usará no SARIMAX (isso cabe ao
  próprio ajuste do modelo).
- **CV do share de SKU calculado só para os top-10 por par**: SKUs de cauda
  (que já caem no *fallback* por baixo volume/poucos dias) não entram nesse
  cálculo — a instabilidade medida em §3.10 é, portanto, um piso: entre os
  SKUs "bons o suficiente" para não cair no fallback, mesmo esses são
  instáveis.
