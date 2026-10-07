# 000 — Mapa completo das análises exploratórias (EDA)

> **O que é este documento.** Um mapa de todas as análises exploratórias do projeto. Para
> cada uma, ele responde quatro perguntas:
>
> 1. **O que a análise faz** e o que ela encontrou.
> 2. **Pseudocódigo**: o que o script de fato executa.
> 3. **O que ela muda no treino do SARIMAX** (o treino final está em
>    [`sarimax_l1_por_loja.py`](../../../ia-predictor/training_scripts/baseline/sarimax_l1_por_loja.py),
>    resultados no [doc 04](../04-treino_l1_por_loja.md)).
> 4. **Que artigo dá base** ao método ou à decisão.
>
> **Fontes.** Os scripts em
> [`ia-predictor/training_scripts/eda/`](../../../ia-predictor/training_scripts/eda/), os
> JSONs em `training_scripts/results/metrics/`, o [relatório de EDA](../00-eda_report.md),
> as explicações em linguagem simples ([001](<001 - Analise 1 critério de Syntetos, Boylan e Croston.md>)
> a [005](<005 - Analise 5 encomendas grandes.md>)), os ADRs
> [010](../ADR-010-exogenas-nominais-fora-do-l1.md),
> [011](../ADR-011-escopo-previsao-sem-reposicao.md) e
> [012](../ADR-012-encomendas-grandes-fora-do-l1.md) e o
> [pré-processamento](../01-pre_processing.md). Os números foram conferidos nos JSONs em
> 2026-10-04.

---

## Sumário

- [Como ler](#como-ler)
- [As numerações do projeto (para não se perder)](#as-numerações-do-projeto-para-não-se-perder)
- [Mapa rápido](#mapa-rápido)
- [Análise 1 — A base bruta](#análise-1--a-base-bruta-o-que-chegou-com-que-qualidade-e-em-que-nível-prever)
- [Análise 2 — O comportamento das vendas dia a dia](#análise-2--o-comportamento-das-vendas-dia-a-dia)
- [Análise 3 — Granularidade das categorias](#análise-3--granularidade-das-categorias-abrir-produtos-de-jardim)
- [Análise 4 — Separar por unidade e por categoria](#análise-4--separar-por-unidade-e-por-categoria)
- [Análise 5 — Encomendas grandes](#análise-5--encomendas-grandes)
- [Síntese: de onde veio cada peça do treino final](#síntese-de-onde-veio-cada-peça-do-treino-final)
- [Ressalvas metodológicas (para a banca)](#ressalvas-metodológicas-para-a-banca)
- [Referências](#referências)

---

## Como ler

Cada sub-análise segue o mesmo formato:

| Bloco | O que traz |
| --- | --- |
| **O que é** | A pergunta e a medida, em linguagem simples |
| **Resultado** | Os números que saíram (dos JSONs de métricas) |
| **Pseudocódigo** | O passo a passo do script, com o nome da função de origem |
| **Impacto no SARIMAX** | O que mudou no treino. Quando o impacto é só na desagregação (L2) ou no painel, isso está dito: "nenhum direto no L1" |
| **Base na literatura** | O artigo que sustenta o método ou a decisão |

**Marcação das referências:**

| Marca | Significado |
| --- | --- |
| ✅ | Já está nas referências do artigo (`docs/project/TCC2 - Inicial.docx`) |
| 📄 | Citada nos documentos do repositório (ADRs, pré-processamento), mas ainda fora do artigo |
| 💡 | **Sugestão**: referência clássica do método, que o projeto **não usou** até aqui. Conferir o texto antes de citar |

Quando nenhum artigo guiou a análise, isso está escrito. Muitas verificações de EDA são
prática padrão e não vieram de um artigo específico. Nesses casos, a marca 💡 indica onde
o método está descrito, caso a banca pergunte.

**Convenções do pseudocódigo:** `←` é atribuição; `Σ` é soma; `s` é uma série diária
(um número por dia); `u` é unidade; `c` é categoria; dia da semana 0 = segunda … 6 =
domingo; "dia aberto" = segunda a sábado com venda.

---

## As numerações do projeto (para não se perder)

As mesmas análises aparecem com três numerações diferentes:

| Este mapa / pasta `eda-explicada` | "EDA n" no código (`eda/run_all.py`) | Script | Seção do [relatório](../00-eda_report.md) | Gráficos |
| --- | --- | --- | --- | --- |
| **Análise 1** — base bruta | EDA 1 + EDA 5 | `eda_source.py`, `eda_classificacao_sku.py` (+ `build_dataset.py`, `reduce_schema.py` do pré-processamento) | §1.3, §2.1–2.8, §2.5b | 01–06, 24 |
| **Análise 2** — vendas dia a dia | EDA 2 + EDA 2b | `eda_series_unidade.py` (2 séries), `eda_series.py` (6 séries) | §3.0–3.9 | 10–19 |
| **Análise 3** — granularidade | EDA 3 | `eda_grupos.py` | §3.10 | 20–22 |
| **Análise 4** — separação | EDA 4 | `eda_separacao.py` | §3.11 | 23 |
| **Análise 5** — encomendas | EDA 6 | `eda_encomendas.py` (+ `preprocessing/encomendas.py`) | §3.12 | 25–26 |

Os gráficos ficam em
[`training_scripts/results/plots/eda/`](../../../ia-predictor/training_scripts/results/plots/eda/).
Os números 07–09 não existem (foram pulados na numeração).

**Ordem cronológica.** Análises 1 e 2 em 01/09/2026 (T000b). Análises 3 e 4 antes de
21/09/2026. A Análise 4 gerou o [ADR-011](../ADR-011-escopo-previsao-sem-reposicao.md)
(L1 por unidade) em 21/09. A Análise 5 gerou o
[ADR-012](../ADR-012-encomendas-grandes-fora-do-l1.md) (encomendas fora do L1) em 23/09.
Os três treinos ([02](../02-baseline_serie_crua_pre_eda.md),
[03](../03-enriquecimento_serie_crua.md) e [04](../04-treino_l1_por_loja.md)) vieram depois,
em 27/09.

**Como rodar** (a partir de `ia-predictor/`, com o pré-processamento já executado):

```bash
python -m training_scripts.preprocessing.run_all   # gera as bases que o EDA lê
python -m training_scripts.eda.run_all              # roda os scripts de EDA em sequência
python -m training_scripts.eda.eda_encomendas       # Análise 5 (ver aviso abaixo)
```

> Aviso (2026-10-04): o `eda/run_all.py` chama `eda_encomendas.main()` no último passo, mas
> não importa `eda_encomendas`. Hoje ele roda as 6 primeiras análises e para com
> `NameError` no fim. Até a correção (acrescentar `eda_encomendas` ao `from . import`),
> rode a Análise 5 separadamente, como acima.

---

## Mapa rápido

| Nº | Sub-análise | Função | Gráfico | Impacto no SARIMAX (resumo) | Base principal |
| --- | --- | --- | --- | --- | --- |
| 1.1 | Volume e completude | `eda_source.bloco_volume_completude` | 01 | Histórico muito acima de 180 dias; série diária contínua | ✅ Wirth; Hipp (2000) |
| 1.2 | Qualidade dos dados | `eda_source.bloco_qualidade` | — | Alvo contínuo; `clip(0)` antes do log; sem serviço/taxa | ✅ Wirth; Hipp (2000) |
| 1.3 | Deduplicação (documento 995) | `build_dataset.process_pending_files` | — | Evita alvo subestimado | — (verificação interna) |
| 1.4 | Colunas e exógenas nominais | `eda_source.bloco_exogenas_nominais`, `reduce_schema` | — | Exógenas do SARIMAX = só calendário | 💡 Kaufman et al. (2012); ✅ LGPD |
| 1.5 | Perfil por unidade e CNPJ | `bloco_por_unidade`, `bloco_jardim_canada_por_cnpj` | 06 | 1 série por loja, sem quebra falsa em abr/2025 | 📄 Box; Tiao (1975), como alternativa |
| 1.6 | Perfil por categoria | `bloco_por_categoria` | 05 | Nenhum direto no L1 | — |
| 1.7 | Esparsidade por SKU | `bloco_esparsidade_sku` | 03 | SARIMAX não roda por produto | ✅ Croston (1972); ✅ Zotteri; Kalchschmidt (2007) |
| 1.8 | Concentração (Pareto) | `bloco_pareto_sku` | 04 | Nenhum direto no L1 | 💡 Silver; Pyke; Thomas (2017) |
| 1.9 | Sazonalidade preliminar | `bloco_sazonalidade_preliminar` | 02 | Primeira evidência de m = 7 | ✅ Box et al. (2015) |
| 1.10 | Classificação de Syntetos, Boylan e Croston | `eda_classificacao_sku` | 24 | Nível do L1 = unidade; `log1p` | ✅ Syntetos; Boylan; Croston (2005) |
| 2.1 | Densidade | `eda_series._densidade` | 10, 16 | Pode treinar; zeros → `loja_fechada` | ✅ Syntetos et al. (2005) |
| 2.2 | Distribuição e `log1p` | `_distribuicao` | 14, 18 | `log1p`; previsão = mediana | ✅ Hyndman; Athanasopoulos (2021) |
| 2.3 | Perfil por dia da semana | `_perfil_dow` | 11, 17 | 6 dummies de dia da semana | ✅ Hyndman; Athanasopoulos (2021); ✅ Arunraj et al. (2016) |
| 2.4 | Força do ciclo semanal (STL) | `_forca_sazonal_semanal` | 15, 19 | Dummies pesam mais que P/Q; D = 0 | 💡 Cleveland et al. (1990); 💡 Wang; Smith; Hyndman (2006) |
| 2.5 | Perfil mensal | `_perfil_mensal` | 12, 17 | Sem sazonalidade anual no L1 | ✅ Hyndman; Athanasopoulos (2021) |
| 2.6 | Datas comemorativas | `_efeito_datas` | — | Só `abertura_excepcional` no L1; datas → desagregação | ✅ Arunraj et al. (2016) |
| 2.7 | Tendência | `_tendencia` | — | Motivou testar d = 1 | ✅ Hyndman; Athanasopoulos (2021) |
| 2.8 | Estacionariedade (ADF + KPSS) | `_adf_kpss` | — | Variante d = 1 (a vencedora) | 💡 Dickey; Fuller (1979); 💡 Kwiatkowski et al. (1992) |
| 2.9 | Autocorrelação e Ljung-Box | `_acf_pacf` | 13, 18 | Grade pequena; ordem (0,1,1)(0,0,1)₇ | ✅ Box et al. (2015); 💡 Ljung; Box (1978) |
| 2.10 | Dias fora do padrão | `_outliers` | — | Levou à Análise 5 | ✅ Chen; Liu (1993) |
| 2.11 | Veredito para o SARIMAX | `_verdito` | — | Prévia do `status` do modelo | — (regra do projeto) |
| 2.12 | Participação dos produtos na categoria | `bloco_sku_dentro_categoria` | — | Nenhum direto no L1 | ✅ Gross; Sohl (1990) |
| 3.1 | Viabilidade dos grupos | `eda_grupos.bloco_viabilidade` | — | Nenhum direto no L1 | — |
| 3.2 | Diferenças entre grupos | `bloco_diferencas` | 20, 21 | Nenhum direto no L1 | — |
| 3.3 | Teste de previsão (walk-forward) | `teste_previsao` | 22 | Protocolo herdado pelo treino | ✅ Hyndman; Koehler (2006); 💡 Tashman (2000) |
| 3.4 | Regra de decisão fixada antes | `_veredito` | — | Nenhum direto no L1 | 💡 Nosek et al. (2018) |
| 3.5 | Árvores | `bloco_arvores` | — | Nenhum | — |
| 4.1 | Montagem da hierarquia | `eda_separacao._series` | — | Define os candidatos a série do L1 | ✅ Fliedner (2001) |
| 4.2 | Modelo próprio × repartição | `_compara` | 23 | **L1 = 2 séries, uma por loja** | ✅ Gross; Sohl (1990); ✅ Zotteri; Kalchschmidt (2007) |
| 4.3 | Soma das partes × agregado | `_soma_das_partes` | — | Confirma um modelo por loja | ✅ Fliedner (2001) |
| 4.4 | Janelas com data comemorativa | `_janelas_com_data` | — | Categoria não vira série nem perto das datas | ✅ Huber et al. (2017) |
| 4.5 | Decisão | `main` | — | ADR-011 | ✅ Zotteri; Kalchschmidt (2007) |
| 5.1 | Diagnóstico no nível da linha | ADR-012, `bloco_perfil` | — | Achou a causa do MASE 1,43 de Itabirito | 📄 Johnston; Boylan; Shale (2003) |
| 5.2 | Regra "K dias típicos" | `encomendas.limiares_encomenda` | 25 | **Alvo = venda de balcão** | ✅ Pearson et al. (2016); ✅ Bartezzaghi; Verganti (1995) |
| 5.3 | Conferência da regra (boleto, consumidor) | `bloco_perfil` | — | Regra validada sem virar exógena | ✅ Kalchschmidt; Verganti; Zotteri (2006) |
| 5.4 | Teto no 99º percentil | `encomendas.teto_quantil` | — | `teto_quantil` no treino | ✅ Hyndman; Athanasopoulos (2021, §13.9) |
| 5.5 | As 4 variantes, sem vazamento | `teste_previsao`, `_janelas` | 26 | Limiar recalculado em cada rodada | ✅ Hyndman; Koehler (2006) |
| 5.6 | Sensibilidade a K | `main` | — | K = 5 não é ajuste fino | ✅ Pearson et al. (2016) |
| 5.7 | Antes × depois | `bloco_antes_depois` | — | Ciclo semanal aparece; tendência cai | ✅ Syntetos et al. (2005) |

---

## Análise 1 — A base bruta: o que chegou, com que qualidade e em que nível prever

**Pergunta.** O que a floricultura entregou, com que qualidade, e dá para prever a venda
produto por produto?

**Fase do CRISP-DM.** Compreensão dos dados, nas tarefas "descrever", "explorar" e
"verificar a qualidade" (Wirth; Hipp, 2000).

**Scripts.** [`eda_source.py`](../../../ia-predictor/training_scripts/eda/eda_source.py)
(blocos 1–8) e
[`eda_classificacao_sku.py`](../../../ia-predictor/training_scripts/eda/eda_classificacao_sku.py).
A deduplicação e o corte de colunas moram no pré-processamento (`build_dataset.py`,
`reduce_schema.py`), mas foram decididos a partir desta análise.

**Saídas.** `eda_source.json`, `eda_classificacao_sku.json` e os gráficos 01–06 e 24.

**Explicação simples.** [001](<001 - Analise 1 critério de Syntetos, Boylan e Croston.md>).

### 1.1 Volume e completude

**O que é.** Conta linhas, documentos, produtos, meses presentes contra esperados e dias
com venda contra dias do calendário. Também compara o último mês com o mesmo mês de anos
anteriores, para saber se ele está completo.

**Resultado.** 333.019 linhas (documento × produto), 130.728 documentos e 5.166 produtos,
de 02/01/2024 a 28/02/2026. Os 26 de 26 meses estão presentes. São 789 dias de calendário,
654 com venda; os 135 restantes são domingos e feriados. Fevereiro/2026 tem volume
parecido com o de anos anteriores, mas isso ainda precisa ser confirmado com a floricultura.
Gráfico: [01](../../../ia-predictor/training_scripts/results/plots/eda/01_transacoes_por_mes_unidade.png).

**Pseudocódigo** (`bloco_volume_completude`):

```text
docs       ← distintos(doc_numero + "|" + doc_tipo)     # doc_numero sozinho NÃO é único
meses      ← mês de cada data
esperados  ← todos os meses entre min(data) e max(data)
faltando   ← esperados − meses                          # resultado: vazio
dias_cal   ← todos os dias entre min(data) e max(data)  # 789
dias_venda ← nº de datas distintas                      # 654
ult        ← último mês
comparar contagem(ult) com a contagem do mesmo mês nos anos anteriores
```

**Impacto no SARIMAX.**

- Confirma que a série diária pode ser montada sem buracos. Os dias sem venda entram como
  0 (`reindex(..., fill_value=0)`) e depois são explicados pelo calendário (2.1).
- O histórico (cerca de 650 dias com venda por loja) fica muito acima do mínimo de 180
  dias (`MIN_OBSERVATIONS_DAYS`). Por isso nenhuma loja cai em `insufficient_data`.
- Fevereiro/2026 é a janela de teste "Fevereiro" dos treinos 02 a 04. Se o mês for um
  recorte parcial, essa janela fica distorcida (pergunta 1 do relatório, §5).

**Base na literatura.** ✅ Wirth; Hipp (2000), CRISP-DM, tarefa "describe data". Não
houve artigo específico: é uma verificação padrão.

### 1.2 Qualidade dos dados

**O que é.** Procura quantidades zero, negativas, fracionárias e inválidas, datas que não
puderam ser lidas, campos vazios e problemas de acentuação. Também confere a integridade:
a soma das linhas de um documento deve bater com o total impresso no relatório.

**Resultado.**

- 880 linhas com quantidade ≤ 0 (0,3%): 836 zeros e 44 negativas, provavelmente devoluções.
- 2.279 linhas fracionárias. São legítimas: grama e terra são vendidas por m² ou kg.
- Nenhuma data ilegível e nenhuma quantidade não numérica.
- O campo de observações está 89% vazio (foi descartado).
- A integridade bate em 90,2% dos documentos. Nos demais, a diferença média é de R$ 593,
  que vem de frete e serviço cobrados fora das linhas de produto.
- A acentuação está correta (UTF-8 válido).

**Pseudocódigo** (`bloco_qualidade`):

```text
q ← qtdade convertida ("1.234,5" → 1234.5)
contar: q ≤ 0, q < 0, q com parte fracionária, q inválido, data inválida
para cada documento d:
    soma_linhas ← Σ tot_liq das linhas de d
    bate[d]     ← |soma_linhas − total_liquido_doc[d]| ≤ R$ 0,02
integridade ← média(bate)                                # 90,2%
nulos       ← nº de vazios por coluna da base bruta
encoding_ok ← "CANADÁ" aparece com os bytes UTF-8 corretos (C3 81)?
```

**Impacto no SARIMAX.**

- **O alvo é contínuo**, não uma contagem. Grama sai em m² fracionado. Por isso a série é
  tratada como contínua (SARIMAX gaussiano em escala `log1p`), e não com um modelo de
  contagem (Poisson).
- **Negativas.** Se ficassem soltas, gerariam dias com venda negativa. A Etapa 4 marca as
  devoluções, e o treino ainda faz `clip(lower=0)` antes do `log1p`
  (`np.log1p(teto_quantil(y).clip(lower=0))` em `selecionar()` e `prever()`).
- **"Serviço e taxa"** (frete, taxas) não é demanda de produto e sai do alvo.
- A integridade de 90% confirma que a quantidade por linha é confiável como alvo.

**Base na literatura.** ✅ Wirth; Hipp (2000), CRISP-DM, tarefa "verify data quality".
Nenhum artigo específico.

### 1.3 Deduplicação — a prova do documento 995

**O que é.** A primeira regra de limpeza removia linhas com o mesmo número de documento e
o mesmo produto. A análise testou se essas "duplicatas" eram mesmo duplicatas, conferindo
o total de cada documento.

**Resultado.** Em abril/2024, a regra antiga marcou 201 "duplicatas". Em 165 delas os
valores eram diferentes, então já eram vendas distintas. Nas outras 36 os valores eram
idênticos. O documento `995` decidiu a questão: ele tem duas linhas do produto `433NL`, e
a soma das 12 linhas dá exatamente 756,30, o total impresso. Sem a segunda linha, daria
750,30. Logo, as duas são vendas reais (o item foi bipado duas vezes). O mesmo
`doc_numero` também se repete entre tipos de documento diferentes (32.572 casos). A regra
corrigida só compara arquivos diferentes e usa uma chave mais rígida. Na base atual, ela
removeu 0 linhas.

**Pseudocódigo** (`build_dataset.process_pending_files`, regra corrigida):

```text
vistos ← ∅
para cada arquivo XLSX, em ordem:
    chaves_do_arquivo ← ∅
    para cada linha:
        k ← (doc_numero, produto_cod, emissao, qtdade, vl_total)
        se k ∈ vistos: descartar        # mesmo documento exportado em dois meses
        senão: manter; chaves_do_arquivo ← chaves_do_arquivo ∪ {k}
    vistos ← vistos ∪ chaves_do_arquivo  # só depois do arquivo inteiro:
                                         # linhas do MESMO documento nunca se comparam
# prova que validou a regra:
Σ tot_liq das 12 linhas do documento 995 = 756,30 = total do relatório
    → as duas linhas de 433NL são vendas reais
```

**Impacto no SARIMAX.** Sem a correção, a série perderia vendas reais justamente nos dias
de muito movimento, quando um item é bipado várias vezes. O resultado seria um alvo
subestimado, com viés para baixo no nível que o SARIMAX aprende.

**Base na literatura.** Nenhum artigo. É uma verificação de consistência interna (o total
do documento como "gabarito"), dentro da tarefa "verify data quality" do CRISP-DM
(✅ Wirth; Hipp, 2000).

### 1.4 Seleção de colunas e triagem de exógenas (pagamento, vendedor)

**O que é.** Para cada uma das 20 colunas, a análise faz uma pergunta: "isso muda a
resposta de quanto vai ser vendido amanhã?". Ela também mede o mix de pagamento e o número
de vendedores, para documentar o descarte.

**Resultado.** 9 colunas mantidas, 11 descartadas e 3 criadas (unidade, categoria,
subcategoria). Há 13 formas de pagamento (crédito 24,3%, PIX 22,9%, boleto 20,7%…) e 38
vendedores. Pagamento e vendedor saem da modelagem
([ADR-010](../ADR-010-exogenas-nominais-fora-do-l1.md)). Os dados pessoais de clientes
também saem.

**Pseudocódigo** (`reduce_schema.py` + `bloco_exogenas_nominais`):

```text
para cada coluna c:
    se c só existe DEPOIS da venda (pagamento, vendedor, operador) → descartar  # vazamento
    se c é dado pessoal (cliente_nome, cliente_cod)                → descartar  # LGPD
    se c é texto livre ou metadado (obs, icms_ret, arquivo_origem…) → descartar
    senão → manter (data, empresa, produto_cod, qtdade, valores, total do documento)
registrar o mix de pagamento e o nº de vendedores, só para documentar o descarte
```

**Impacto no SARIMAX.** Esta análise define o que pode entrar no "X" do SARIMAX. Só
entra variável **conhecida antes** dos 14 dias previstos. Daí as exógenas finais serem
apenas de calendário: `dia_seg … dia_sab`, `loja_fechada` e `abertura_excepcional`
(`COLS_CAL`). Usar a forma de pagamento seria vazamento de dados (*data leakage*): o
modelo pareceria bom no teste e falharia na prática. O pagamento volta uma única vez, na
Análise 5, só para **conferir** a regra das encomendas, nunca como variável do modelo.

**Base na literatura.**

- 💡 Kaufman et al. (2012) definem e classificam o vazamento de dados.
- ✅ Hyndman; Athanasopoulos (2021, §7.6) distinguem previsão *ex-ante* (só com o que se
  sabe antes) de *ex-post*.
- ✅ Brasil (2018), LGPD, para o descarte dos dados pessoais.

### 1.5 Perfil por unidade e composição de Jardim Canadá (CNPJs)

**O que é.** Mede o volume, o faturamento e o histórico de cada unidade. Abre Jardim
Canadá pelos dois CNPJs (Floricultura e Garden Center) mês a mês.

**Resultado.**

| Unidade | Linhas | Produtos | Quantidade | Faturamento | Dias com venda |
| --- | --- | --- | --- | --- | --- |
| Jardim Canadá | 197.471 | 4.276 | 2.618.198 | R$ 32,6 mi | 650 |
| Itabirito | 135.548 | 4.146 | 1.328.388 | R$ 16,6 mi | 653 |

O Garden Center começa a vender em 13/02/2025. Em abril/2025, a Floricultura cai de 87
mil para 47 mil unidades por mês, e o Garden Center chega a 37 mil. A soma (84 mil) fica
perto dos 81 mil de janeiro e fevereiro. Gráfico:
[06](../../../ia-predictor/training_scripts/results/plots/eda/06_jardim_canada_por_cnpj.png).

**Pseudocódigo** (`bloco_por_unidade`, `bloco_jardim_canada_por_cnpj`):

```text
para cada unidade u:
    linhas, produtos distintos, Σ qtd, Σ tot_liq, 1ª/última data, dias com venda
em Jardim Canadá:
    cnpj ← "Garden Center" se empresa contém "GARDEN", senão "Floricultura Canadá"
    tabela mês × cnpj com Σ qtd
    soma ← Floricultura + Garden
    comparar a soma antes e depois de 13/02/2025
```

**Impacto no SARIMAX.** Define a série de Jardim Canadá como a **soma dos dois CNPJs**.
Se a loja fosse modelada por CNPJ, a série da Floricultura teria uma queda falsa de nível
em abril/2025. Ela é só a venda migrando para o outro CNPJ, mas o SARIMAX a leria como
tendência de baixa. Somando, a quebra some. Esta análise fixa a chave `unidade` (Etapa 3)
e, com a Análise 4, leva a um SARIMAX por loja.

**Base na literatura.** Nenhum artigo guiou a decisão, que foi confirmada com a
floricultura. A alternativa da literatura seria modelar a quebra com uma variável de
intervenção (📄 Box; Tiao, 1975). Somar os CNPJs torna isso desnecessário.

### 1.6 Perfil por categoria e subcategoria

**O que é.** Mede a participação de cada categoria no volume e o número de produtos de
cada uma.

**Resultado.**

| Categoria | Quantidade | Participação | Produtos |
| --- | --- | --- | --- |
| Produtos de jardim | 2.034.205 | 51,5% | 5.062 |
| Grama | 1.837.995 | 46,6% | 14 |
| Flores de corte | 68.526 | 1,7% | 88 |
| Serviço e taxa (não é produto) | 5.860 | 0,1% | 2 |

Dentro de Produtos de jardim: Plantas diversas 41,2% (3.514 produtos) e Insumos e
acessórios 10,3% (1.548). A Verde Perto funciona como garden center, não como floricultura
de presente. Gráfico:
[05](../../../ia-predictor/training_scripts/results/plots/eda/05_volume_categoria_fina.png).

**Pseudocódigo** (`bloco_por_categoria`):

```text
para cada nível ∈ {categoria, categoria_fina}:
    para cada grupo g: Σ qtd, % do total, nº de produtos distintos, nº de linhas
    ordenar por volume
```

**Impacto no SARIMAX.** Nenhum direto no L1. Define as 3 categorias usadas na
desagregação (L2) e confirma a retirada de "Serviço e taxa" do alvo. O alvo do L1 soma só
produtos (`serie_unidade` exclui `Servico e taxa`).

**Base na literatura.** Nenhuma. A taxonomia é do negócio.

### 1.7 Esparsidade por produto (SKU)

**O que é.** Conta em quantos dias cada produto vendeu. Mede o quanto a série de um
produto típico é "cheia de zeros".

**Resultado.**

- O produto típico (mediana) vendeu em **9 dos 789 dias**. A média é 36 dias e o
  percentil 90 é 86 dias.
- Só 1,3% dos produtos vendem em metade dos dias ou mais, e 5,1% vendem em 20% dos dias
  ou mais.
- 13,2% venderam uma única vez.
- **72,2%** (3.732 produtos) cairiam no rateio da categoria: venderam em menos de 28 dias.

Gráfico: [03](../../../ia-predictor/training_scripts/results/plots/eda/03_esparsidade_dias_ativos_sku.png).
O painel de cima mostra só os dias com venda; o de baixo, os cortes em número de produtos.

> **Por que "ou menos de 8 vendas" não muda o número.** A regra de rateio está escrita como
> "menos de 28 dias com venda **ou** menos de 8 vendas". *Dias com venda* conta datas
> distintas; *vendas* conta linhas de venda, e um produto pode vender várias vezes no mesmo
> dia (há um com 16 vendas em 4 dias). Mas cada venda cai em algum dia, então vendas ≥ dias
> sempre. Quem tem menos de 8 vendas tem menos de 8 dias e já está entre os que venderam em
> menos de 28 dias; o inverso não vale. Por isso a regra separa os mesmos 3.732 produtos que
> "menos de 28 dias" sozinho, e os 2.279 com menos de 8 vendas (44,1%) estão todos dentro
> desse grupo. Atenção: o `CLAUDE.md` (limiares) e a constituição escrevem o mínimo como
> "≥ 28 dias **ou** ≥ 8 vendas", cuja negação é "< 28 dias **e** < 8 vendas" (2.279
> produtos). As duas formas precisam ser unificadas antes de implementar a L2.

**Pseudocódigo** (`bloco_esparsidade_sku`):

```text
para cada produto p:
    dias_ativos[p] ← nº de dias distintos com venda
    n_vendas[p]    ← nº de linhas de venda
densidade ← dias_ativos / 789
fallback  ← (dias_ativos < 28) OU (n_vendas < 8)     # regra de rateio da L2
reportar média, mediana, p10, p90 de dias_ativos; % com 1 venda; % em fallback
```

**Impacto no SARIMAX.** Decide **em que nível** o SARIMAX é ajustado: nunca por produto.
Uma série como `0, 0, 0, 2, 0, 0, 1…` não tem padrão semanal nem nível para o SARIMAX
estimar. O modelo vai para o agregado (L1), e o produto recebe uma fatia da previsão (L2).

**Base na literatura.**

- ✅ Croston (1972): suavização e ARIMA erram em séries com muitos zeros.
- ✅ Zotteri; Kalchschmidt (2007): o nível certo de agregação, que troca erro de
  amostragem (pouco dado) por erro de especificação (perder o padrão).
- ✅ Huber; Gossmann; Stuckenschmidt (2017): itens perecíveis esparsos demais, previstos
  numa hierarquia.

### 1.8 Concentração do volume (curva de Pareto)

**O que é.** Mede quantos produtos concentram o volume.

**Resultado.** 7 produtos (0,14%) somam metade do volume. 86 produtos (1,7%) somam 80%.
Os 20 maiores somam 61,7%, e os 100 maiores somam 81,6%. Gráfico:
[04](../../../ia-predictor/training_scripts/results/plots/eda/04_pareto_volume_sku.png).

**Pseudocódigo** (`bloco_pareto_sku`):

```text
v ← Σ qtd por produto, ordenado do maior para o menor (só v > 0)
acumulado ← soma acumulada de v / Σ v
para alvo ∈ {50%, 80%, 90%, 95%}: k ← nº de produtos até o acumulado passar o alvo
para N ∈ {20, 50, 100}: % do volume nos N maiores
```

**Impacto no SARIMAX.** Nenhum direto no L1. Justifica `TOP_N_PRODUCTS = 20` para o
detalhe por produto (L2 e painel). Como a lista dos 20 maiores muda com o tempo (2.12),
ela não é fixa.

**Base na literatura.** Não houve artigo. A ideia é a da classificação ABC de estoques
(💡 Silver; Pyke; Thomas, 2017).

### 1.9 Sazonalidade preliminar

**O que é.** Conta linhas e quantidade por dia da semana e por mês, ainda na base bruta,
sem agrupar por unidade e categoria.

**Resultado.**

- Domingo tem 1.130 linhas, contra 50 a 66 mil nos outros dias: a loja está fechada.
- **Sábado tem muitas linhas (59,7 mil), mas pouca quantidade** (303 mil unidades, contra
  680 a 776 mil nos dias úteis). No sábado entram muitas compras pequenas de consumidor.
  Nos dias úteis entram as compras grandes de paisagista.
- Por número de linhas, o fim de semana fica em 0,64 da média.

Gráfico: [02](../../../ia-predictor/training_scripts/results/plots/eda/02_sazonalidade_semanal_unidade.png).

**Pseudocódigo** (`bloco_sazonalidade_preliminar`):

```text
por dia da semana: nº de linhas e Σ qtd
índice_fds ← média(linhas de sáb e dom) / média(linhas dos 7 dias)
por mês do ano: nº de linhas; mês de pico e de vale
```

**Impacto no SARIMAX.** É a primeira evidência de que o ciclo é **semanal** (`m = 7`,
`SEASONAL_PERIOD`) e de que o domingo é estrutural (loja fechada, depois `loja_fechada`).
A leitura definitiva do padrão por dia vem em 2.3.

**Base na literatura.**

- ✅ Box et al. (2015): o SARIMA sazonal, com período m.
- ✅ Hyndman; Athanasopoulos (2021, §2.4): gráficos sazonais.

### 1.10 Classificação de demanda de Syntetos, Boylan e Croston

**O que é.** Aplica o critério da literatura que diz, só olhando o histórico, se uma série
é "suave" o bastante para SARIMAX ou se pede Croston. O critério usa dois números:

- **ADI** (intervalo médio entre vendas) = dias do período ÷ dias com venda.
- **CV²** (variabilidade do tamanho da venda) = (desvio ÷ média)², calculado **só nos dias
  com venda**.

Os cortes são ADI = 1,32 e CV² = 0,49. O critério foi aplicado em três níveis: produto,
unidade × categoria e unidade.

**Resultado.**

| Classe | ADI | CV² | % dos produtos | % do volume |
| --- | --- | --- | --- | --- |
| Suave | < 1,32 | < 0,49 | 0,2% | 0,0% |
| Errática | < 1,32 | ≥ 0,49 | 0,5% | 53,7% |
| Intermitente | ≥ 1,32 | < 0,49 | 52,2% | 1,4% |
| **Lumpy** | ≥ 1,32 | ≥ 0,49 | **47,1%** | **44,9%** |

- 692 produtos (13,4%) venderam num único dia e não têm CV² calculável.
- **99,3%** dos classificáveis são intermitentes ou lumpy.
- As 2 séries por unidade são **erráticas**: Jardim Canadá tem ADI 1,21 e CV² 0,67;
  Itabirito tem ADI 1,21 e CV² 4,58.
- As 6 séries unidade × categoria também são erráticas (ADI 1,21–1,23; CV² 0,92–16,2).

Gráfico: [24](../../../ia-predictor/training_scripts/results/plots/eda/24_classificacao_demanda_sku.png).

**Pseudocódigo** (`_adi_cv2_por_sku`, `_classifica`):

```text
para cada produto p (as duas unidades somadas por dia):
    v ← quantidades diárias de p, só dias com venda > 0
    se |v| < 2: "não classificável"                   # 13,4% dos produtos
    span ← último_dia(v) − primeiro_dia(v) + 1         # período do PRÓPRIO produto
    ADI  ← span / |v|
    CV²  ← (desvio_padrão(v, ddof = 1) / média(v))²
    classe ← suave        se ADI < 1,32 e CV² < 0,49
             errática     se ADI < 1,32 e CV² ≥ 0,49
             intermitente se ADI ≥ 1,32 e CV² < 0,49
             lumpy        caso contrário
repetir para as 6 séries unidade × categoria e para as 2 séries por unidade
```

**Impacto no SARIMAX.**

- **Justifica formalmente o nível do L1.** Agregar até a unidade move a série do quadrante
  errado (produto: intermitente/lumpy) para o quadrante em que o SARIMAX é apropriado
  (errático).
- **Errática pede suavização.** O CV² alto é o motivo do `log1p` (2.2). Depois da
  Análise 5, a série de balcão com teto de Jardim Canadá vira "suave" (CV² 0,40) e a de
  Itabirito cai para 0,84.
- O ADI de 1,21 das séries por unidade vem **inteiro** de domingos e feriados. São zeros
  determinísticos, que o SARIMAX recebe pela exógena `loja_fechada` (2.1), e não um sinal
  de demanda intermitente.
- Croston, TSB e SBA ficam como trilha de comparação no nível de produto (ADR-009).

**Base na literatura.**

- ✅ **Syntetos; Boylan; Croston (2005)**: o critério e os cortes. É o artigo central
  desta análise.
- ✅ Croston (1972): o método para demanda intermitente.
- ✅ Syntetos; Boylan (2005): a correção SBA.
- ✅ Teunter; Syntetos; Babai (2011): o TSB.
- ✅ Hyndman; Athanasopoulos (2021, §13.2): Croston em séries de contagem.

---

## Análise 2 — O comportamento das vendas dia a dia

**Pergunta.** Como a venda de cada dia se comporta? Há padrão de dia da semana, de datas
comemorativas, de tendência? As premissas do projeto se confirmam?

**Scripts.**
[`eda_series_unidade.py`](../../../ia-predictor/training_scripts/eda/eda_series_unidade.py)
analisa as **2 séries por unidade**, que são o alvo do L1.
[`eda_series.py`](../../../ia-predictor/training_scripts/eda/eda_series.py) analisa as
**6 séries unidade × categoria**, insumo da desagregação. Os dois chamam a mesma bateria,
`analisa_serie(s, linhas)`, de 9 blocos (2.1 a 2.11). O bloco 2.12 é só de
`eda_series.py`.

**Histórico.** Até 21/09/2026, as 6 séries unidade × categoria eram o alvo do L1. Depois do
[ADR-011](../ADR-011-escopo-previsao-sem-reposicao.md), as 2 séries por unidade passaram a
ser o alvo, e as 6 viraram insumo da repartição.

**Saídas.** `eda_series_unidade.json`, `eda_series.json` e os gráficos 10–19.

**Explicação simples.** [002](<002 - Analise 2 comportamento das vendas diarias.md>).

**Como a série é montada** (`_common.serie_unidade`, `_common.serie_diaria`):

```text
serie_unidade(u):
    linhas ← vendas da unidade u, sem "Servico e taxa"
    s      ← Σ qtdade por dia
    s      ← reindexar do 1º ao último dia com venda; dia sem venda = 0
serie_diaria(u, c): igual, filtrando também a categoria c
```

### 2.1 Densidade e regularidade

**O que é.** Mede se a série é regular ou cheia de buracos: dias com venda, maior sequência
de dias sem venda e dias úteis zerados.

**Resultado.**

- Por unidade: 650 e 653 dias com venda (82,4% e 82,8% do período).
- Unidade × categoria: de 641 a 653 dias.
- A maior sequência sem venda é de 3 dias (5 em Grama de Itabirito).
- Só 4,0% dos dias úteis ficam zerados.
- Quase todos os zeros são domingos e feriados.

Gráficos: [16](../../../ia-predictor/training_scripts/results/plots/eda/16_series_l1_unidade.png)
e [10](../../../ia-predictor/training_scripts/results/plots/eda/10_series_l1_paineis.png).

**Pseudocódigo** (`_densidade`):

```text
zero ← (s == 0)
dias_com_venda ← Σ(não zero);  pct ← dias_com_venda / nº de dias
maior_sequência ← maior número de zeros consecutivos (percorrendo a série)
atende_mínimo ← dias_com_venda ≥ 180
pct_zero_dia_útil ← % de zeros entre segunda e sábado     # (em _distribuicao)
```

**Impacto no SARIMAX.**

- As duas lojas passam do mínimo de 180 dias e podem ser treinadas.
- **Os zeros são previsíveis**: loja fechada, não falta de venda. Por isso o SARIMAX recebe
  `loja_fechada` como exógena, em vez de se usar um modelo de demanda intermitente. A
  Etapa 6 conferiu que o calendário explica **todos** os zeros. Nenhum dia marcado como
  fechado teve venda, e nenhum dia marcado como aberto ficou sem venda.
- No doc 04, com o calendário, o erro nos dias de loja fechada fica em ~0. Sem ele, era de
  2.512 unidades por feriado em Jardim Canadá.

**Base na literatura.** ✅ Syntetos; Boylan; Croston (2005): a densidade é o ADI. O mínimo
de 180 dias é regra do projeto (`CLAUDE.md`), não de um artigo.

### 2.2 Distribuição e decisão de usar `log1p`

**O que é.** Mede o quanto a venda "pula" de um dia para o outro (coeficiente de variação,
CV) e o formato da distribuição: assimetria, cauda e maior dia ÷ média. A regra do projeto
é aplicar `log1p` quando CV > 0,7.

**Resultado.**

- Jardim Canadá: CV 1,01, assimetria 4,4, curtose 40.
- Itabirito: CV 2,39, assimetria 7,6, curtose 83.
- Unidade × categoria: CV de 1,15 a 4,49, com dias de pico de até 86 vezes a média
  (Flores em Jardim Canadá) e 79 vezes (Grama em Itabirito).
- **Todas** as séries pedem `log1p`.

Gráficos: [14](../../../ia-predictor/training_scripts/results/plots/eda/14_dist_qtd_diaria_l1.png)
e [18](../../../ia-predictor/training_scripts/results/plots/eda/18_acf_dist_unidade.png).

**De onde vem o limiar 0,7.** É uma **convenção operacional, não um valor calibrado**. Não
houve experimento comparando 0,6 / 0,7 / 0,8, nem referência que fixe esse número: ele
existe para automatizar a decisão nas séries desagregadas (L2/SKU), onde o CV varia muito
e não se quer inspecionar cada série à mão. O racional é o usual do CV = σ/μ: abaixo de
~0,5 a série é razoavelmente homocedástica e o log só distorce; acima de ~1,0 a variância
cresce claramente com o nível (caso típico de contagem) e o log se justifica. 0,7 é o meio
desse intervalo cinzento.

No projeto, porém, **a decisão nunca foi marginal**: o menor CV observado é 1,01 (Jardim
Canadá), já 44% acima do limiar, e Itabirito está 3,4 vezes acima. Qualquer limiar entre
0,5 e 1,0 daria a mesma resposta em **todas** as séries. Duas consequências:

- O limiar é um guarda-corpo que nunca foi acionado na direção "não transformar". Por isso
  o treino L1 atual aplica `log1p` incondicionalmente, sem testar o CV
  (`baseline/sarimax_l1_por_loja.py`, `selecionar`/`prever`): dado este EDA, o teste era
  redundante. `LOG_CV_THRESHOLD` em `backend/config.py` e `aplicar_log1p` nos JSONs do EDA
  seguem como registro da regra, não como gate ativo do L1.
- **Para a banca:** apresentar o 0,7 como regra operacional, nunca como parâmetro
  calibrado. A formulação segura é "adotou-se `log1p` por assimetria à direita e variância
  proporcional ao nível (CV de 1,01 a 2,39 nas duas lojas), critério operacionalizado como
  CV > 0,7 para automatizar a decisão nas séries desagregadas" — e, se cutucarem, "a
  decisão é robusta a qualquer limiar entre 0,5 e 1,0".

**Pseudocódigo** (`_distribuicao`):

```text
cv ← desvio(s) / média(s)
assimetria, curtose, p50, p90, p99, max / média
pct_zero_dia_útil ← % de zeros de segunda a sábado
cv_dias_com_venda ← desvio / média só nos dias com venda
aplicar_log1p ← cv > 0,7                              # LOG_CV_THRESHOLD
```

**Impacto no SARIMAX.**

- O treino ajusta o modelo em `z = log1p(teto(y))`. O `log1p` encolhe os picos, para que
  poucos dias enormes não dominem os coeficientes.
- **Volta para unidades:** a previsão é `expm1(μ)`, que é a **mediana** na escala
  original. O intervalo de 95% é calculado em escala log e depois convertido, por isso
  fica assimétrico.
- O EDA usava o fator de Duan para corrigir o viés da volta. O treino final o descartou,
  porque com cauda pesada ele inflou as previsões em 4,6 vezes em Itabirito (doc 04 §2).
- Efeito colateral da mediana: a previsão fica abaixo do vendido (cobre 87,5% e 80,9% do
  balcão; doc 04 §4.2).

**Base na literatura.**

- ✅ Hyndman; Athanasopoulos (2021, §3.1 transformações; §5.6 previsão com transformação
  e correção de viés).
- 💡 Box; Cox (1964): o log é o caso λ = 0 da família de Box-Cox.
- 💡 Duan (1983): o fator de correção (*smearing*) usado no EDA.

**O que Box-Cox faz aqui (e o que não faz).** A referência entra como **ancoragem
teórica**, não como método aplicado — é o que o marcador 💡 significa. A família de
Box-Cox parametriza as transformações estabilizadoras de variância por um expoente λ
(λ = 1 não transforma, λ = 0,5 é raiz quadrada, λ = 0 é o logaritmo). Citá-la responde à
pergunta "por que logaritmo e não outra transformação?": o `log1p` não é escolha *ad hoc*,
é o caso λ = 0 do arcabouço canônico do tema.

O projeto **não executa Box-Cox**: λ nunca foi estimado por máxima verossimilhança, foi
fixado em 0 pela evidência de assimetria e variância proporcional ao nível (acima). Três
observações para não confundir as coisas:

- `SARIMAX` do statsmodels **não tem** parâmetro de Box-Cox automático. Só
  `ExponentialSmoothing` tem (`use_boxcox`), e o projeto não o usa — a transformação é
  sempre aplicada à mão, antes de entregar a série ao modelo.
- O `+1` do `log1p` não é detalhe de implementação: as séries têm **domingos zerados**
  (loja fechada), e λ = 0 puro exigiria `log(0)`. O deslocamento é obrigatório, e é o que
  distingue `log1p` de um Box-Cox λ = 0 estrito.
- Estimar λ não está no escopo e provavelmente não mudaria a conclusão: com CV de 1,01 a
  4,49 e curtose de 40 a 83, o λ estimado cairia perto de 0. O custo seria perder a volta
  simples para a escala de unidades (`expm1` = mediana) sem ganho de acurácia esperado.

### 2.3 Perfil por dia da semana

**O que é.** Divide a venda média de cada dia da semana pela média geral da série (1,0 =
na média).

**Resultado** (por unidade):

| | seg | ter | qua | qui | sex | sáb | dom |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jardim Canadá | 1,14 | 1,32 | **1,44** | 1,30 | 1,20 | 0,59 | 0 |
| Itabirito | 1,46 | **1,47** | 1,24 | 1,18 | 1,22 | 0,42 | 0 |

- **A premissa "fim de semana vende mais" estava errada.** O pico é em dia útil, o sábado
  é fraco e o domingo é fechado.
- Por categoria: Grama tem pico de terça a quarta (2,1 na terça em Itabirito), e Flores de
  corte tem pico na **sexta** (1,73 e 1,96).

Gráficos: [11](../../../ia-predictor/training_scripts/results/plots/eda/11_perfil_dia_semana_l1.png)
e [17](../../../ia-predictor/training_scripts/results/plots/eda/17_perfil_semanal_mensal_unidade.png).

**Pseudocódigo** (`_perfil_dow`):

```text
média_dia[d] ← média de s nos dias da semana d (seg..dom)
índice[d]    ← média_dia[d] / média(s)        # a média geral INCLUI os domingos (zero)
pico ← argmax(índice);  vale ← argmin(índice de seg a sáb)
amplitude ← max / min do índice de seg a sáb
```

**Impacto no SARIMAX.**

- **Seis dummies de dia da semana** entram no X (`dia_seg … dia_sab`). O domingo é a base
  e também é coberto por `loja_fechada`.
- No doc 03, o dia da semana respondeu por **83%** da importância das exógenas
  (Random Forest).
- A correção da premissa não muda o código, mas muda a leitura dos coeficientes e a
  documentação.

**Base na literatura.**

- ✅ Hyndman; Athanasopoulos (2021, §7.4 dummies sazonais; cap. 10, regressão com erros
  ARIMA, que é o que o SARIMAX faz).
- ✅ Arunraj; Ahrens; Fernandes (2016): SARIMAX com exógenas de calendário para venda
  diária no varejo de alimentos.

> Cuidado de leitura: como a média geral inclui o domingo (zero), os índices dos dias
> abertos ficam cerca de 1/6 acima do que seriam contra a média só dos dias abertos. O
> sábado de Jardim Canadá, 0,59, equivale a ≈ 0,51 da média de segunda a sábado. A ordem
> dos dias não muda.

### 2.4 Força do ciclo semanal (decomposição STL)

**O que é.** Separa a série em tendência, ciclo semanal e sobra (STL). Depois mede quanto
da variação o ciclo semanal explica, numa escala de 0 (nada) a 1 (tudo).

**Resultado.**

- Força sazonal (Fs): **0,25** em Jardim Canadá e **0,07** em Itabirito.
- Unidade × categoria: de 0,00 (Grama em Itabirito) a 0,29 (Grama em Jardim Canadá).
- Força da tendência: 0,06 e 0,03.
- **O ciclo semanal é real, mas explica pouco da variação.** A maior parte vem de picos
  pontuais.

Gráficos: [19](../../../ia-predictor/training_scripts/results/plots/eda/19_stl_unidade.png)
e [15](../../../ia-predictor/training_scripts/results/plots/eda/15_stl_par_denso.png).

**Pseudocódigo** (`_forca_sazonal_semanal`):

```text
STL(s, período = 7, robusto = sim) → tendência T, sazonal S, resíduo R
Fs ← max(0, 1 − Var(R) / Var(S + R))       # força do ciclo semanal
Ft ← max(0, 1 − Var(R) / Var(T + R))       # força da tendência
```

**Impacto no SARIMAX.** Com o ciclo fraco na variância, a recomendação foi dar mais peso às
**dummies de dia da semana** do que aos termos sazonais do SARIMA (P, Q). A grade manteve
P, Q ∈ {0, 1} e D = 0. O treino final confirmou isso:

| Loja | Sem calendário (A0) | Com calendário (A1) | AIC A0 → A1 |
| --- | --- | --- | --- |
| Jardim Canadá | (1,0,2)(**1**,0,1)₇ | (0,0,2)(**0**,0,1)₇ | 1.539 → 537 |
| Itabirito | (0,0,2)(**1**,0,1)₇ | (1,0,2)(**0**,0,1)₇ | 1.462 → 704 |

Quando as dummies entram, o termo autorregressivo sazonal (P) **some** nas duas lojas, e o
AIC cai pela metade ou mais. As dummies assumem o padrão semanal, como o EDA previa.

**Base na literatura.**

- 💡 Cleveland et al. (1990): o método STL.
- 💡 Wang; Smith; Hyndman (2006): a medida de força (Fs, Ft).
- ✅ Hyndman; Athanasopoulos (2021, §3.6 STL; §4.3 "STL features", com a mesma fórmula).

### 2.5 Perfil mensal (sazonalidade anual)

**O que é.** Calcula o índice de cada mês contra a média. Para não confundir um pedido
isolado com sazonalidade, abre o índice por ano e o recalcula sem o maior dia da série.

**Resultado.**

- Jardim Canadá tem pico em **outubro**, e ele continua mesmo sem o maior dia: é
  sazonalidade real. Itabirito tem pico em dezembro.
- Com só 2 ciclos anuais, apenas 2 picos mensais se repetem nos dois anos: Flores em
  Itabirito em dezembro (2,0 e 1,5) e Grama em Jardim Canadá em outubro (1,5 e 1,9).
- Os demais picos vêm de um único ano ou de um único pedido. Exemplo: o abril de Flores em
  Jardim Canadá cai de 2,1 para 0,7 sem o pedido de 30/04/2024.

Gráficos: [12](../../../ia-predictor/training_scripts/results/plots/eda/12_perfil_mensal_l1.png)
e [17](../../../ia-predictor/training_scripts/results/plots/eda/17_perfil_semanal_mensal_unidade.png).

**Pseudocódigo** (`_perfil_mensal`):

```text
índice_mês[m]          ← média(s no mês m) / média(s)
índice_mês_ano[a][m]   ← o mesmo, separado por ano
s'                     ← s com o maior dia trocado pela mediana
índice_mês_sem_pico[m] ← índice_mês recalculado em s'
sazonalidade real ⇔ o pico se repete nos 2 anos E sobrevive sem o maior dia
```

**Impacto no SARIMAX.**

- Com cerca de 2 ciclos anuais, **não há termo de sazonalidade anual** no L1: nem
  diferenciação sazonal anual, nem termos de Fourier anuais. É a mesma lógica do
  [ADR-004](../ADR-004-d0-sarimax-sazonal.md) (D = 0 com histórico curto).
- As fases de alta e baixa do ano (set–dez/2025 forte, jan/2026 fraco) são tratadas
  fazendo o modelo **acompanhar o nível recente** (d = 1, ver 2.8), e não com uma
  sazonalidade anual estimada com dois pontos.

**Base na literatura.**

- ✅ Hyndman; Athanasopoulos (2021, §12.1): sazonalidade múltipla em dados diários, com
  termos de Fourier para o ciclo anual. Fica como trabalho futuro, quando houver mais anos.
- ✅ Box et al. (2015): identificar sazonalidade exige ciclos suficientes.

### 2.6 Efeito de datas comemorativas

**O que é.** Mede a venda média nos dias em torno de cada data (o dia e os 2 anteriores)
contra a média geral (1,0 = sem efeito). As datas são Dia da Mulher, Mães, Namorados,
Pais, Finados e Natal.

**Resultado, como está no relatório** (Jardim Canadá · Itabirito):

| Data | Flores de corte | Grama | Produtos de jardim |
| --- | --- | --- | --- |
| Dia da Mulher | 4,0 · 4,2 | 0,6 · 0,5 | 0,7 · 0,7 |
| Dia das Mães | 2,1 · 5,0 | 0,8 · 0,2 | 0,5 · 1,0 |
| Dia dos Namorados | 1,7 · 3,8 | 1,2 · 0,6 | 1,1 · 2,2 |
| Finados | 1,1 · 3,1 | 0,7 · 3,3 | 0,7 · 2,6 |
| Natal | 2,1 · 1,1 | 0,6 · 0,5 | 0,4 · 0,5 |

A conclusão foi que o efeito **muda de sinal entre categorias**: Flores disparam e
Grama e Produtos de jardim caem.

> ⚠️ **Ressalva encontrada ao montar este mapa.** A razão compara a janela com a média
> geral **sem descontar o dia da semana nem a loja fechada**. O Dia das Mães e o Dia dos
> Pais caem num domingo, então a janela é sexta, sábado e domingo. Mesmo sem nenhum efeito
> da data, essa janela já fica abaixo da média. Com o ajuste, algumas leituras mudam (o
> Dia das Mães no total da unidade **não cai**). As conclusões principais se mantêm. A
> tabela completa está em
> [Ressalvas metodológicas](#ressalvas-metodológicas-para-a-banca).

**Pseudocódigo, como implementado** (`_efeito_datas`):

```text
para cada evento e e cada ano:
    janela ← {data, data − 1, data − 2}
razão[e] ← média(s nos dias da janela) / média(s)   # média geral, com domingos e feriados
```

**Pseudocódigo da versão ajustada** (recomendada para a desagregação):

```text
índice_dia[d] ← média(s nos dias ABERTOS de dia da semana d) / média(s)
para cada evento e:
    esperado ← média, na janela, de (0 se loja fechada no dia, senão índice_dia[dia da semana])
    razão_ajustada[e] ← razão[e] / esperado
```

**Impacto no SARIMAX.**

- **No L1 (total da loja), as datas pesam pouco**, porque o agregado as dilui.
- No doc 03, a janela de "7 dias até Mães e Finados" causou **12% do erro do ano**. O
  efeito real era do próprio dia, em que Itabirito **abre** excepcionalmente.
- Por isso o L1 final usa só `abertura_excepcional` e `loja_fechada`. No doc 04, o erro
  nesses dias caiu de 780 para 50 unidades.
- As variáveis `dias_ate_*` e `janela_7d_*` (Etapa 6) ficam para a **desagregação por
  categoria**, onde o sinal muda. Ali o índice deve ser o ajustado.

**Base na literatura.**

- ✅ Arunraj; Ahrens; Fernandes (2016): feriados e eventos como exógenas do SARIMAX diário.
- ✅ Hyndman; Athanasopoulos (2021, §7.4): variáveis de intervenção e de feriado.
- 📄 Box; Tiao (1975): análise de intervenção.

### 2.7 Tendência

**O que é.** Ajusta uma reta à série e expressa a inclinação em % da média por ano. Também
compara a média dos primeiros 90 dias com a dos últimos 90.

**Resultado.**

- Jardim Canadá: **−13%/ano** (Produtos de jardim −23%: de 2.286 para 1.198 unidades por
  dia).
- Itabirito: **+54%/ano** (de 892 para 3.033 unidades por dia; Grama +96%).
- Depois da Análise 5, o balcão de Itabirito cresce só **+8%/ano** (774 → 910). O resto
  era encomenda.

**Pseudocódigo** (`_tendencia`):

```text
ajustar a reta s(t) = b0 + b1·t por mínimos quadrados (t = 0, 1, …, n−1)
tendência_%_ano ← b1 × 365 / média(s) × 100
variação_90d    ← (média dos últimos 90 dias − média dos 90 primeiros) / média dos 90 primeiros
```

**Impacto no SARIMAX.**

- Uma tendência acima de 40%/ano dispara o aviso "avaliar d = 1 ou termo de nível".
- A recomendação perdeu força quando se viu que a tendência de Itabirito era encomenda.
- O treino testou mesmo assim a variante **A1 d = 1**, que **venceu nas duas lojas**
  (MASE 0,58). Ela prevê a variação em relação ao nível recente, em vez de voltar para a
  média do histórico.
- No código, o modelo só leva constante quando d = 0 (`trend="c" if order[1] == 0 else "n"`).

**Base na literatura.** ✅ Hyndman; Athanasopoulos (2021, §7.4, tendência como
preditora; §9.1, diferenciação para remover tendência e mudanças de nível).

### 2.8 Estacionariedade (ADF + KPSS)

**O que é.** Dois testes com hipóteses opostas:

- **ADF**: a hipótese nula é "não estacionária" (raiz unitária).
- **KPSS**: a hipótese nula é "estacionária".

Usar os dois evita confiar num teste só. A combinação sugere d (quantas vezes diferenciar).

**O que o ADF não responde.** Rejeitar a raiz unitária **não** é o mesmo que afirmar que o
nível é constante. O ADF só descarta o passeio aleatório puro ("a série não anda sem
rumo"). Uma série pode reverter à média dentro da amostra — e o ADF rejeitar com folga — e
ainda assim ter **fases de nível diferentes**, que é o que o KPSS acusa. Essa distinção é a
origem de todo o problema descrito abaixo: o ADF foi usado como se respondesse "o nível é
estável?", e ele não responde essa pergunta.

**Resultado.**

- Por unidade: o ADF rejeita a raiz unitária (p = 0,0003 e 0,0007), mas o KPSS rejeita a
  estacionariedade (p = 0,039 e ≤ 0,01). **Os testes divergem nas duas lojas.** O "≤ 0,01"
  é o limite da tabela do KPSS, não o p-valor exato (ressalva metodológica 7).
- Unidade × categoria: Grama e Flores de Jardim Canadá e Produtos de jardim de Itabirito
  são estacionárias pelos dois testes. As outras 3 divergem.

**Pseudocódigo** (`_adf_kpss`):

```text
p_adf  ← ADF(s, defasagens escolhidas por AIC)       # H0: raiz unitária
p_kpss ← KPSS(s, em torno do nível, defasagens auto)  # H0: estacionária; p limitado a [0,01; 0,10]
se p_adf < 0,05 e p_kpss > 0,05:  d ← 0   "estacionária"
se p_adf ≥ 0,05 e p_kpss ≤ 0,05:  d ← 1   "não estacionária"
senão:                            d ← 0   "testes divergem: começar com d = 0 e revisar pelo resíduo"
```

**O problema que isso criou.** A divergência não é um detalhe de relatório: ela levou o
treino ao d errado, em três camadas.

1. **A regra de desempate manda para d = 0.** O `senão` do pseudocódigo acima resolve a
   divergência com `d ← 0` ("começar com d = 0 e revisar pelo resíduo"). Como as duas lojas
   divergem, as duas caem no desempate.
2. **O treino é ainda mais direto: usa só o ADF.** Em `selecionar()`
   (`baseline/sarimax_l1_por_loja.py`), d sai de
   `0 if adfuller(z)[1] < 0.05 else 1` — o KPSS **não entra na conta**. A regra combinada
   acima descreve o EDA, não o trainer. Aqui as duas regras concordam (ambas dão d = 0),
   mas são regras diferentes, e isso precisa ser dito.
3. **d = 0 faz a previsão voltar para a média do histórico.** Com d = 0 o modelo recebe
   constante (`trend="c" if order[1] == 0 else "n"`), e a previsão converge para o nível
   médio do treino em vez de partir do nível atual. Foi exatamente a falha de dezembro do
   doc 02 §4.3: o balcão foi de 5,8 a 7,0 mil por dia entre setembro e dezembro contra
   3,5 mil em janeiro, e o modelo previu **28% menos que o balcão vendeu, mesmo sem as
   encomendas**. O teste principal tinha caído em fevereiro, um mês calmo, e escondeu o
   problema.

**A solução: decidir por experimento, não por teste.** Em vez de arbitrar a divergência com
outro teste, criou-se a variante `A1_eda_d1`, com d **fixo** em 1, e comparou-se com as
demais nas **mesmas 26 rodadas** de walk-forward. **A d = 1 venceu nas duas lojas**: MASE
0,58, 24 de 26 rodadas vencidas, IC95 entre 91% e 94% — o que levou o L1 a
`status = "trained"`. O ganho se concentra onde a teoria previa: nas janelas em que o nível
mudou, o erro de Itabirito caiu de 780 (A0) para 131 (A1) e 50 (A1 d = 1).

Leitura: o ADF diz que a série não "anda sem rumo", mas o KPSS acusa que o nível não é
constante. Há fases de alta e de baixa (EDA §4, item 16), e o d = 1 prevê a **variação**,
então a previsão parte do nível recente em vez de voltar à média histórica.

Dois detalhes que fecham o raciocínio:

- Com d = 1 o `trend` vira `"n"`: a diferenciação já remove a constante, e não se extrapola
  tendência determinística. O limite d ≤ 1 vem do `CLAUDE.md`, para não consumir dados de
  treino.
- **d não é D.** Aqui se fala da diferenciação regular (d). A sazonal (D = 0) é outra
  decisão, tomada por falta de ciclos anuais suficientes
  ([ADR-004](../ADR-004-d0-sarimax-sazonal.md)), e não se mexeu nela.

**O que levar para as séries desagregadas (L2/SKU).** O desempate `senão → d = 0` **não é
conservador** para estes dados: se ninguém tivesse testado d = 1, o modelo teria ficado
preso no d que falha quando o nível muda. Ao descer para `unidade × categoria` e SKU — onde
3 das 6 séries também divergem —, tratar d como **variante a testar fora da amostra**, não
como saída de teste de hipótese.

**Base na literatura.**

- 💡 Dickey; Fuller (1979): o teste ADF.
- 💡 Kwiatkowski et al. (1992): o teste KPSS.
- ✅ Hyndman; Athanasopoulos (2021, §9.1): testes de raiz unitária e a escolha de d pelo
  KPSS.

### 2.9 Autocorrelação (ACF/PACF) e teste de Ljung-Box

**O que é.** Mede o quanto a venda de hoje se parece com a de ontem (defasagem 1) e com a
de uma semana atrás (defasagens 7 e 14). O teste de Ljung-Box diz se essas correlações,
juntas, são significativas.

**Resultado.**

| Série | ACF 1 | ACF 7 | ACF 14 | PACF 7 | Ljung-Box (7), p |
| --- | --- | --- | --- | --- | --- |
| Jardim Canadá | 0,13 | 0,28 | 0,21 | 0,25 | < 0,001 |
| Itabirito | 0,06 | 0,19 | 0,05 | 0,18 | < 0,001 |

- A "memória" de curto prazo é fraca, com um eco semanal.
- Em Flores de Jardim Canadá (p = 0,998) e Produtos de jardim de Itabirito (p = 0,49) não
  há autocorrelação nenhuma: a série se comporta como ruído, e só o calendário explica a
  venda.

Gráficos: [13](../../../ia-predictor/training_scripts/results/plots/eda/13_acf_l1_paineis.png)
e [18](../../../ia-predictor/training_scripts/results/plots/eda/18_acf_dist_unidade.png).

**Pseudocódigo** (`_acf_pacf`):

```text
r_k  ← ACF(s) para k = 1..21;   φ_kk ← PACF(s)
Q(h) ← n(n+2) · Σ_{k=1..h} r_k² / (n − k),  para h ∈ {7, 14}     # Ljung-Box
memória_significativa ← p(Q(7)) < 0,05
olhar r_1 (ontem → hoje) e r_7, r_14 (eco semanal)
```

**Impacto no SARIMAX.**

- **Memória fraca + eco em 7** quer dizer que a grade pequena basta (p, q ≤ 2; P, Q ≤ 1).
- A ordem vencedora nas duas lojas é **SARIMAX(0,1,1)(0,0,1)₇**: um termo de média móvel
  e um termo sazonal de média móvel na defasagem 7.
- O ARIMA(0,1,1) equivale à suavização exponencial simples, que segue o nível recente.
  Isso é coerente com 2.8.
- As séries sem autocorrelação motivaram incluir na comparação uma abordagem só de
  calendário (EDA §4, item 6).
- O Ljung-Box volta depois **nos resíduos** do modelo, com limiar p > 0,05 (só gera
  aviso).

**Base na literatura.**

- ✅ Box et al. (2015): identificação da ordem pela ACF e PACF.
- 💡 Ljung; Box (1978): o teste.
- ✅ Hyndman; Athanasopoulos (2021, §2.8 autocorrelação; §5.4 diagnóstico dos resíduos;
  §9.10, equivalência ARIMA(0,1,1) ↔ suavização exponencial simples).

### 2.10 Dias fora do padrão (picos) e composição do maior dia

**O que é.** Conta os dias acima de 3 desvios-padrão e acima do limite de Tukey (Q3 + 3 ×
IQR). Para o maior dia de cada série, abre a composição: quantos documentos, quantas
linhas e quanto a maior linha representa do dia.

**Resultado.**

- Unidade × categoria: de 4 a 20 dias acima de 3σ por série.
- Por unidade: 11 dias em Jardim Canadá e 16 em Itabirito (59 pelo critério do IQR).
- **Em 5 das 6 séries, uma única linha responde por 31% a 96% do maior dia.** Exemplos:
  - 15.000 de 15.956 unidades em Grama de Jardim Canadá, 08/10/2025.
  - 19.200 de 61.561 em Grama de Itabirito, 16/12/2025.
  - 530 de 551 em Flores de Itabirito.

**Pseudocódigo** (`_outliers`):

```text
z ← (s − média(s)) / desvio(s)
picos_3σ   ← dias com z > 3
limite_IQR ← Q3 + 3·(Q3 − Q1);  picos_IQR ← dias acima do limite
maior_dia  ← dia de maior s
no maior dia: nº de documentos, nº de linhas, maior linha, maior_linha / total do dia
```

**Impacto no SARIMAX.** Foi o achado que levou à **Análise 5**. Os picos não são "dias
fortes", e sim **linhas** enormes de encomenda. Esses picos:

- distorciam os coeficientes;
- inflavam a escala do MASE (que fica otimista; doc 02 §4.4);
- alargavam o intervalo de 95% (cerca de 80 mil no doc 02).

A solução (encomendas fora do alvo e teto no p99) entra no treino.

**Base na literatura.**

- ✅ Chen; Liu (1993): picos distorcem os parâmetros e alargam os intervalos do ARIMA.
- ✅ Hyndman; Athanasopoulos (2021, §13.9).
- 💡 Tukey (1977): o limite pelo IQR.

### 2.11 Veredito para o SARIMAX

**O que é.** Junta os blocos anteriores numa classificação: "ok", "atenção" ou
"insuficiente", com os motivos.

**Resultado.**

- Por unidade: Jardim Canadá "ok". Itabirito "atenção", por três motivos: dia de pico de
  37 vezes a média, Fs = 0,07 e +54%/ano.
- Unidade × categoria: "atenção" em Grama de Itabirito, Flores de Jardim Canadá e Produtos
  de jardim de Itabirito.
- Depois da Análise 5, o balcão de Itabirito passa a "ok".

**Pseudocódigo** (`_verdito`):

```text
motivos ← []
se dias_com_venda < 180:        motivos += "insufficient_data"
se dias_com_venda < 400:        motivos += "sem ciclo anual completo"
se % de dias úteis zerados > 12: motivos += "intermitência além dos domingos"
se max / média > 30:            motivos += "cauda extrema"
se Fs < 0,1:                    motivos += "ciclo semanal fraco: dummies > termos sazonais"
se Ljung-Box(7) p ≥ 0,05:       motivos += "sem autocorrelação: o calendário carrega o modelo"
se |tendência| > 40%/ano:       motivos += "avaliar d = 1 ou termo de nível"
nível ← "insuficiente" se insufficient_data; "atenção" se há motivos; senão "ok"
```

**Impacto no SARIMAX.** É uma prévia do `status` que o modelo recebe (`trained`,
`low_confidence` ou `insufficient_data`). Itabirito iria para `low_confidence`. Com a
Análise 5 e o treino do doc 04, as duas lojas ficaram `trained`.

**Base na literatura.** Nenhuma. Os limites (180 dias, 12%, 30×, Fs 0,1, 40%/ano) são
**heurísticas do projeto**. Cada motivo aponta para um bloco que tem base própria
(2.1–2.10).

### 2.12 Estabilidade da participação dos produtos dentro da categoria

**O que é.** Mede o quanto a fatia de cada um dos 10 maiores produtos muda de um mês para
o outro dentro de sua categoria (coeficiente de variação da participação mensal).

**Resultado.** Nenhuma das 6 combinações tem participação estável. A variação média vai de
**0,65** (Flores de Itabirito) a **2,04** (Grama de Itabirito); o limite de "estável" seria
0,5.

**Pseudocódigo** (`bloco_sku_dentro_categoria`):

```text
para cada unidade × categoria:
    tabela mês × produto com Σ qtd
    share[mês, p] ← qtd[mês, p] / Σ qtd do mês
    para os 10 maiores produtos: cv_p ← desvio(share_p) / média(share_p)
    cv_médio ← média(cv_p);  "estável" se cv_médio < 0,5
```

**Impacto no SARIMAX.** Nenhum direto no L1. Na desagregação (L2), pede uma janela mais
longa e torna a média da categoria o caminho padrão para a maioria dos produtos.

**Base na literatura.**

- ✅ Gross; Sohl (1990): a proporção média histórica é simples e está entre os métodos
  mais precisos de desagregação.
- ✅ Fliedner (2001).

---

## Análise 3 — Granularidade das categorias: abrir "Produtos de jardim"?

**Pergunta.** Separar Produtos de jardim em Plantas diversas e Insumos e acessórios
melhora a previsão, ou basta mostrar os dois como grupos no painel?

**Script.** [`eda_grupos.py`](../../../ia-predictor/training_scripts/eda/eda_grupos.py).
Rodou quando as 6 séries ainda eram o L1. A conclusão continua valendo com o L1 por
unidade, porque a pergunta é a mesma: abrir mais um nível ajuda?

**Saídas.** `eda_grupos.json` e os gráficos 20–22.

**Explicação simples.** [003](<003 - Analise 3 granularidade das categorias.md>).

### 3.1 Viabilidade dos grupos candidatos

**O que é.** Verifica se cada série candidata é densa o bastante para ter modelo próprio:
pelo menos 180 dias com venda e no máximo 12% de dias úteis zerados.

**Resultado.**

| Unidade · grupo | Dias com venda | Dias úteis sem venda | CV | % do volume da unidade |
| --- | --- | --- | --- | --- |
| Jardim Canadá · Plantas diversas | 650 | 4,0% | 1,48 | 41,0% |
| Jardim Canadá · Insumos e acessórios | 650 | 4,0% | 1,30 | 10,9% |
| Itabirito · Plantas diversas | 653 | 4,0% | 2,09 | 41,7% |
| Itabirito · Insumos e acessórios | 653 | 4,0% | 1,30 | 9,2% |

Tecnicamente, nada impede abrir.

**Pseudocódigo** (`_viabilidade`):

```text
para cada unidade u e grupo g:
    s ← série diária do grupo (soma das subcategorias do grupo)
    viável ← (dias_com_venda ≥ 180) e (% de dias úteis zerados ≤ 12)
```

**Impacto no SARIMAX.** Nenhum direto no L1. Mostra que a pergunta não se resolve pela
densidade, e sim pelo teste de previsão (3.3).

**Base na literatura.** Os mesmos limites de 2.1 e 2.11 (regra do projeto).

### 3.2 O quanto os grupos se comportam diferente

**O que é.** Compara os grupos por perfil de dia da semana, perfil mensal, datas e,
principalmente, pela **correlação diária depois de remover o padrão semanal**. Sem essa
remoção, todos os grupos pareceriam correlacionados só porque "todo mundo vende em dia
útil".

**Resultado.**

- Flores de corte é o grupo mais distinto: correlação de no máximo 0,19 com qualquer
  outro.
- Plantas e Insumos são o par mais parecido: 0,46 em Jardim Canadá e 0,53 em Itabirito,
  contra 0,30 ou menos nos demais pares.
- Ainda assim há diferenças. Em Itabirito, Plantas sobe 2,4 vezes no Dia dos Namorados e
  2,9 em Finados, e Insumos fica perto da média.

Gráficos: [20](../../../ia-predictor/training_scripts/results/plots/eda/20_grupos_perfil_dia_semana.png)
e [21](../../../ia-predictor/training_scripts/results/plots/eda/21_grupos_correlacao_residuos.png).

**Pseudocódigo** (`bloco_diferencas`, `_residuo_semanal`):

```text
aberto ← dias em que algum grupo vendeu
para cada grupo g:
    x ← log1p(s_g), só em dias abertos de segunda a sábado
    resíduo_g ← x − média de x no mesmo dia da semana    # tira o padrão semanal
corr(g, h) ← correlação(resíduo_g, resíduo_h)
também: correlação dos totais semanais, dos perfis de dia da semana e dos perfis mensais;
        Fs, tendência e efeito das datas por grupo
```

**Impacto no SARIMAX.** Nenhum direto no L1. Indica que os grupos diferem pouco, mas não é
decisivo: quem decide é 3.3.

**Base na literatura.** Não houve artigo. Remover o componente sazonal comum antes de
correlacionar é cuidado padrão contra correlação espúria.

### 3.3 Teste de previsão: modelo próprio × repartição (walk-forward)

**O que é.** O teste decisivo. São 26 janelas consecutivas de 14 dias (um ano inteiro,
com todas as datas comemorativas). Em cada janela, o teste compara prever o grupo com o
seu próprio modelo contra prever Produtos de jardim e repartir pelo peso recente do grupo.
O teste roda com dois modelos de famílias diferentes (SARIMAX e Holt-Winters), para a
conclusão não depender de um só.

**Resultado** (MASE; menor é melhor):

| Grupo | Modelo | Jardim Canadá: próprio · repartido | Itabirito: próprio · repartido |
| --- | --- | --- | --- |
| Plantas diversas | SARIMAX | 0,551 · 0,526 | 0,939 · 0,945 |
| Plantas diversas | Holt-Winters | 0,610 · 0,586 | 0,898 · 0,898 |
| Insumos e acessórios | SARIMAX | 0,618 · 0,697 | 0,868 · 0,924 |
| Insumos e acessórios | Holt-Winters | 0,680 · 0,769 | 0,887 · 0,876 |

Dos 156 ajustes SARIMAX, 1 não convergiu. Gráfico:
[22](../../../ia-predictor/training_scripts/results/plots/eda/22_grupos_teste_previsao_mase.png).

**Pseudocódigo** (`teste_previsao`, `_participacoes`, `_erros`, `_prever_sarimax`,
`_prever_ets`, `_volta_escala`) — **é o protocolo que as Análises 4 e 5 e o treino
reaproveitam**:

```text
N ← 26 janelas;  H ← 14 dias
para i = 0..25:
    origem ← n − (26 − i) × 14
    treino ← série[: origem];  teste ← série[origem : origem + 14]
    f_pai, f_plantas, f_insumos ← prever(treino de cada série)
    # repartição do pai pelo peso recente do filho (últimas 8 semanas)
    nível       ← Σ filho / Σ pai
    nível_dia[d] ← Σ filho no dia d / Σ pai no dia d
    f_rep_nível ← f_pai × nível;   f_rep_dia ← f_pai × nível_dia[dia da semana]
    soma_filhos ← f_plantas + f_insumos                  # comparada com f_pai
    MASE ← média|real − previsão| / média|treino_t − treino_{t−7}|   # escala: naïve semanal no treino
    WAPE ← Σ|erro| / Σ real

prever(treino) =
    SARIMAX(1,0,1) com constante, em log1p, exógenas: 6 dummies de dia, feriado, janela de data
    OU Holt-Winters aditivo semanal (m = 7), em log1p
volta de escala: exp(μ) × smear − 1, com smear = média(exp(resíduo)) em dias abertos  (Duan)
```

**Impacto no SARIMAX.** Nenhum direto na configuração do L1 (que é por unidade), mas este
teste **criou o protocolo de avaliação** que o treino herdou: 26 rodadas × 14 dias,
comparação com a naïve sazonal ("repetir a semana passada") e MASE.

Os números daqui são **comparações relativas**. O modelo de teste tinha ordem fixa
(1,0,1), sem termos sazonais, e usava o fator de Duan. O treino final escolhe a ordem pelo
AIC e usa a mediana, então os valores absolutos não são comparáveis.

**Base na literatura.**

- ✅ Hyndman; Koehler (2006): o MASE.
- ✅ Hyndman; Athanasopoulos (2021, §5.10 validação cruzada para séries temporais; §8.3
  Holt-Winters; §11.2 repartição *top-down*).
- 💡 Tashman (2000): avaliação com origem móvel.
- 💡 Winters (1960) e Holt (2004): o Holt-Winters.
- 💡 Duan (1983): o fator de correção.
- ✅ Gross; Sohl (1990): repartir pela proporção histórica.

### 3.4 Regra de decisão fixada antes de ver os números

**O que é.** O critério foi escrito **antes** de rodar o teste, para evitar ajustar a régua
ao resultado desejado. Abrir em 4 categorias exige três coisas ao mesmo tempo:

1. séries viáveis;
2. ganho de pelo menos 5% do modelo próprio sobre a melhor repartição, em **cada** grupo,
   unidade e modelo;
3. a soma dos filhos não piorar o pai em mais de 2%.

**Resultado.** O menor ganho foi −4,8% com SARIMAX e −4,0% com Holt-Winters (pioras). A
mediana dos ganhos foi +3,4% e −0,6%. **A regra não foi atendida**, e as 3 categorias
ficam.

**Pseudocódigo** (`_veredito`):

```text
para cada (unidade, previsor, filho):
    ganho ← 1 − MASE(próprio) / min(MASE(repartição por nível), MASE(repartição por dia))
perda_pai ← MASE(soma dos filhos) / MASE(pai) − 1
abrir ← todas as séries viáveis
        E min(ganho) ≥ 5%
        E max(perda_pai) ≤ 2%
```

**Impacto no SARIMAX.** Nenhum direto no L1. Mantém 3 categorias na desagregação. Plantas
e Insumos aparecem no painel como grupos (soma dos produtos de cada um).

**Base na literatura.** Não houve artigo. A prática de fixar a regra antes corresponde ao
pré-registro de análises (💡 Nosek et al., 2018).

### 3.5 Árvores

**O que é.** Estima, por palavras-chave no nome do produto, se as árvores sustentariam uma
categoria própria. Exemplos de palavras: ÁRVORE, IPÊ, OLIVEIRA, cítricos, PALMEIRA,
CIPRESTE.

**Resultado.** São 299 produtos, com **0,4%** do volume de Jardim Canadá e **1,2%** do de
Itabirito. A série é densa (646 e 637 dias), mas pequena (13 e 20 unidades por dia) e com
picos de 42 e 64 vezes a média. As árvores ficam dentro de Plantas diversas.

**Pseudocódigo** (`bloco_arvores`):

```text
é_árvore ← subcategoria ∈ Plantas diversas E nome começa com (ÁRVORE|IPÊ|OLIVEIRA|…|CIPRESTE)
série ← Σ qtd diária dos produtos marcados, por unidade
viabilidade e % do volume (como em 3.1)
```

**Impacto no SARIMAX.** Nenhum.

**Base na literatura.** Nenhuma.

---

## Análise 4 — Separar por unidade e por categoria?

**Pergunta.** Cada nível de separação se paga? Prever cada parte com o seu próprio modelo
erra menos do que prever o total e repartir?

**Script.** [`eda_separacao.py`](../../../ia-predictor/training_scripts/eda/eda_separacao.py).
Usa o mesmo desenho da Análise 3: 26 × 14 dias, dois modelos, MASE e regra de 5%.

**Saídas.** `eda_separacao.json` e o gráfico 23.

**Explicação simples.** [004](<004 - Analise 4 separar por unidade e por categoria.md>).

**Decisão que gerou.** [ADR-011](../ADR-011-escopo-previsao-sem-reposicao.md): o L1 passa
de 6 para 2 séries.

### 4.1 Montagem da hierarquia

**O que é.** Monta as 9 séries no mesmo calendário: a rede, as 2 unidades e as 6
combinações unidade × categoria. Calcula o peso de cada parte no seu pai.

**Resultado.**

- Jardim Canadá é 66,4% da rede, e Itabirito é 33,6%.
- Em Jardim Canadá: Grama 46,7%, Flores 1,4% e Produtos de jardim 52,0%.
- Em Itabirito: Grama 46,6%, Flores 2,5% e Produtos de jardim 51,0%.

**Pseudocódigo** (`_series`, `_estrutura`):

```text
para cada unidade u e categoria c: s[u·c] ← Σ qtd por dia (calendário comum, 0 sem venda)
s[u]    ← Σ_c s[u·c]
s[rede] ← Σ_u s[u]
estrutura: rede → {Jardim Canadá, Itabirito};  u → {u·Grama, u·Flores, u·Produtos de jardim}
peso(parte) ← Σ parte / Σ pai
```

**Impacto no SARIMAX.** Define os candidatos a série do L1: rede, unidade ou unidade ×
categoria.

**Base na literatura.**

- ✅ Fliedner (2001): previsão hierárquica.
- ✅ Hyndman; Athanasopoulos (2021, §11.1): séries hierárquicas e agrupadas.

### 4.2 Modelo próprio × repartição do agregado (*top-down*)

**O que é.** Para cada parte, compara o modelo próprio com a previsão do pai repartida
pelo peso recente da parte.

**Resultado** (MASE, próprio × repartido):

| Parte | SARIMAX | Holt-Winters | Ganho do próprio (SARIMAX · HW) |
| --- | --- | --- | --- |
| Itabirito | 1,434 × 1,736 | 1,311 × 1,469 | **+17% · +11%** |
| Jardim Canadá | 0,659 × 0,829 | 0,727 × 0,656 | +21% · −11% |
| JC · Grama | 0,794 × 0,807 | 0,841 × 0,860 | +2% · +2% |
| JC · Flores de corte | 0,696 × 0,699 | 0,860 × 0,733 | +0% · −17% |
| JC · Produtos de jardim | 0,550 × 0,532 | 0,616 × 0,602 | −3% · −2% |
| Itabirito · Grama | 1,715 × 1,886 | 1,795 × 1,781 | +9% · −1% |
| Itabirito · Flores de corte | 0,811 × 0,893 | 0,868 × 0,904 | +9% · +4% |
| Itabirito · Produtos de jardim | 0,954 × 0,895 | 0,905 × 0,809 | −7% · −12% |

Dos 234 ajustes SARIMAX, 2 não convergiram. Gráfico:
[23](../../../ia-predictor/training_scripts/results/plots/eda/23_separacao_teste_previsao_mase.png).

**Pseudocódigo** (`_previsoes`, `_compara`):

```text
para cada previsor ∈ {SARIMAX, Holt-Winters}:
    prever as 9 séries nas 26 janelas (uma vez só; as comparações reaproveitam)
    para cada parte p com pai P:
        erro_próprio ← erro(previsão de p)
        erro_rep     ← erro(previsão de P × peso de p nas últimas 8 semanas)   # por nível e por dia
        ganho[p, previsor] ← 1 − MASE(próprio) / min(MASE das duas repartições)
separar p ⇔ min(ganho[p, SARIMAX], ganho[p, HW]) ≥ 5%
```

**Impacto no SARIMAX.** **É a decisão estrutural mais importante do treino: um SARIMAX
por loja (2 séries), e não 6.**

- Nenhuma categoria atinge 5% nos dois modelos, então a categoria passa a ser obtida por
  repartição em cascata (unidade → categoria → produto).
- Separar por unidade tem apoio: Itabirito ganha nos dois modelos, e as tendências das
  lojas são opostas.
- O MASE de **1,434** de Itabirito expôs o problema que a Análise 5 resolveu.

**Base na literatura.**

- ✅ Gross; Sohl (1990): repartir pela proporção histórica.
- ✅ Zotteri; Kalchschmidt (2007): o nível de agregação certo com poucas observações.
- ✅ Hyndman; Athanasopoulos (2021, §11.2): *top-down* e *bottom-up*.

### 4.3 O caminho inverso: soma das partes × modelo do agregado (*bottom-up*)

**O que é.** Verifica se somar as previsões das partes erra menos que prever o agregado
direto.

**Resultado** (MASE, agregado × soma das partes):

| Agregado | SARIMAX | Holt-Winters |
| --- | --- | --- |
| Rede (2 unidades) | 1,153 × **0,901** | 0,919 × 0,922 |
| Jardim Canadá (3 categorias) | 0,659 × 0,665 | 0,727 × 0,733 |
| Itabirito (3 categorias) | 1,434 × 1,367 | 1,311 × 1,372 |

**Pseudocódigo** (`_soma_das_partes`):

```text
para cada janela:
    erro_pai  ← erro(previsão do pai, real do pai)
    erro_soma ← erro(Σ previsões das partes, real do pai)
comparar MASE médio dos dois
```

**Impacto no SARIMAX.** Confirma o nível de unidade. Somar os modelos das 2 lojas melhora
o total da rede em 22% com SARIMAX (empata com Holt-Winters). Somar as 3 categorias não
muda o total da loja (diferença menor que 5%).

**Base na literatura.** ✅ Fliedner (2001): *top-down* × *bottom-up*.

### 4.4 Janelas com data comemorativa

**O que é.** Repete a comparação só nas 7 janelas que contêm uma data comemorativa (ou os 2
dias anteriores). A ideia é ver se Flores de corte, cuja venda dispara nas datas, ganha
com modelo próprio pelo menos ali.

**Resultado.** Também não ganha. Com SARIMAX, o modelo próprio de Flores fica em 0,85
contra 0,77 da repartição em Jardim Canadá, e em 1,18 contra 1,09 em Itabirito.

**Pseudocódigo** (`_janelas_com_data`, `_compara`):

```text
datas ← {data, data − 1, data − 2} de cada evento
com_data[i] ← a janela i contém algum dia de datas?
MASE(próprio) e MASE(melhor repartição) só nas janelas com_data[i] = verdadeiro (e só nas demais)
```

**Impacto no SARIMAX.** Reforça que a categoria **não vira série do L1** nem perto das
datas. O efeito das datas por categoria vai para a desagregação (ver a ressalva de 2.6
sobre como medi-lo).

**Base na literatura.** ✅ Huber; Gossmann; Stuckenschmidt (2017): o sinal está no
agregado, e o item herda a proporção.

### 4.5 Decisão

**O que é.** Aplica a regra (ganho de 5% nos dois modelos) a cada parte.

**Resultado.** Separar por categoria: **não**. Separar por unidade: **sim**.

**Pseudocódigo** (`main`, bloco do veredito):

```text
para cada parte p: separar[p] ← min(ganho SARIMAX, ganho HW) ≥ 5%
```

**Impacto no SARIMAX.**

- O L1 ajusta 2 SARIMAX (`SERIES_UNIDADE_CSV`, uma série por loja).
- São 4 modelos a menos para ajustar e validar, com a mesma acurácia.
- As 6 séries unidade × categoria continuam existindo como insumo da repartição.

**Base na literatura.**

- ✅ Zotteri; Kalchschmidt (2007).
- 📄 Babai; Boylan; Rostami-Tabar (2022): revisão de agregação e hierarquia.
- A reconciliação ótima (MinT) não foi testada. É a resposta para "por que não
  reconciliação?" (💡 Wickramasuriya; Athanasopoulos; Hyndman, 2019).

---

## Análise 5 — Encomendas grandes

**Pergunta.** Por que Itabirito erra tanto (MASE 1,434, pior que repetir a semana
anterior) e dá para corrigir?

**Scripts.**
[`eda_encomendas.py`](../../../ia-predictor/training_scripts/eda/eda_encomendas.py) (o
teste) e
[`preprocessing/encomendas.py`](../../../ia-predictor/training_scripts/preprocessing/encomendas.py)
(as funções puras usadas no pré-processamento e no treino).

**Saídas.** `eda_encomendas.json` e os gráficos 25–26.

**Explicação simples.** [005](<005 - Analise 5 encomendas grandes.md>).

**Decisão que gerou.** [ADR-012](../ADR-012-encomendas-grandes-fora-do-l1.md).

### 5.1 Diagnóstico no nível da linha de venda

**O que é.** Em vez de olhar a série diária, olha **cada linha de venda**: qual o dia
típico, qual o tamanho das maiores linhas e quem as compra (só em agregado, sem
identificar ninguém).

**Resultado.**

| Indicador | Itabirito | Jardim Canadá |
| --- | --- | --- |
| Grama num dia típico (mediana) | 203 m² | 1.403 m² |
| Maior linha de Grama | 20.000 m² | 15.000 m² |
| % da Grama nos 10 maiores dias | 43,6% | 8,6% |
| CV da série diária da unidade | 2,40 | 1,02 |

Em Itabirito, um único cliente responde por 32 das 40 maiores linhas, todas pagas por
boleto. São encomendas de obra e paisagismo, não venda de balcão.

**Pseudocódigo** (ADR-012 §Contexto; `bloco_perfil`):

```text
para cada unidade × categoria:
    dia_típico ← mediana(Σ qtd diária, dias com venda, segunda a sábado)
    maiores linhas; % do volume nos 10 maiores dias
    concentração: das 40 maiores linhas, quantas são do mesmo cliente (só a contagem)
```

**Impacto no SARIMAX.** Mostra que o problema **não está no modelo, e sim no alvo**. A
série somava duas demandas diferentes. Nenhum modelo de série temporal antecipa em que dia
cai um pedido de 20.000 m² numa loja que vende 200 m² por dia.

**Base na literatura.**

- 📄 Johnston; Boylan; Shale (2003): o tamanho do pedido tem cauda longa e deve ser
  estudado no nível da linha.
- ✅ Chen; Liu (1993): picos contaminam o ajuste.

### 5.2 A regra "K dias típicos"

**O que é.** Uma linha é **encomenda** quando, sozinha, vale mais que **K = 5 dias
típicos** da sua unidade × categoria. Um percentil das linhas não serviria: em Produtos de
jardim, linhas de 60 a 100 mudas são comuns, e o p99 marcaria 37–48% do volume como
encomenda.

**Resultado.**

| Unidade · categoria | Limite por linha | Linhas marcadas | % do volume |
| --- | --- | --- | --- |
| Itabirito · Grama | 1.015 | 68 | 67,7% |
| Itabirito · Produtos de jardim | 3.079 | 8 | 9,1% |
| Itabirito · Flores de corte | 155 | 4 | 4,2% |
| Jardim Canadá · Flores de corte | 160 | 12 | 17,8% |
| Jardim Canadá · Grama | 7.014 | 1 | 1,2% |
| Jardim Canadá · Produtos de jardim | 8.265 | 1 | 1,0% |

No total, as encomendas são **36,3% do volume de Itabirito** (80 linhas) e 1,3% do de
Jardim Canadá (14 linhas). Gráfico:
[25](../../../ia-predictor/training_scripts/results/plots/eda/25_encomendas_series.png).

**Pseudocódigo** (`limiares_encomenda`, `marcar_encomendas`):

```text
limiares(linhas_do_treino, K = 5):
    diário[u, c, dia] ← Σ qtd por dia, só segunda a sábado e dias com venda
    limiar[u, c]      ← K × mediana(diário[u, c, ·])
marcar(linhas, limiar):
    encomenda ← qtd da linha > limiar[unidade, categoria]   # par sem limiar: nunca marca
balcão ← linhas não marcadas
```

**Impacto no SARIMAX.**

- **O alvo do L1 passa a ser a venda de balcão** (`qtd_balcao`). As encomendas viram um
  fluxo à parte, que não é previsto pelo histórico.
- No treino, o limiar é **recalculado em cada rodada só com o passado**
  (`Dados.balcao(origem)` chama `marcar(linhas, data_corte=origem)`), para não haver
  vazamento.

**Base na literatura.**

- ✅ Bartezzaghi; Verganti (1995).
- 📄 Bartezzaghi; Verganti; Zotteri (1999).
- 📄 Verganti (1997).
- 📄 Kalchschmidt; Zotteri; Verganti (2003).

Esses trabalhos separam a demanda regular da demanda irregular de poucos clientes grandes.

- 📄 Olhager (2003): parte da demanda é sob pedido e fica fora da política de estoque.
- ✅ Pearson et al. (2016): filtro de Hampel. O limiar "K × mediana" é da mesma família.

**Nenhum** desses trabalhos usa exatamente "5 dias típicos". O valor é uma escolha do
projeto, testada em 5.6.

### 5.3 Conferência da regra com informações que ela não usa

**O que é.** A regra usa só quantidade, unidade, categoria e data. Para conferir se ela
separa mesmo outro tipo de cliente, a análise compara o perfil das linhas marcadas com o
do balcão, usando a forma de pagamento e o "cliente consumidor final". Essas duas
informações não entram na regra.

**Resultado** (Itabirito):

| Perfil | Encomendas | Balcão |
| --- | --- | --- |
| Pagas por boleto | 65% | 1,4% |
| Cliente "CONSUMIDOR" | 7,5% | 90,5% |

**Pseudocódigo** (`bloco_perfil`):

```text
para cada unidade:
    % de linhas pagas por boleto: encomenda × balcão
    % de linhas de "CONSUMIDOR" (cliente_cod = 1): encomenda × balcão
    (só agregados; cliente e pagamento NÃO entram na regra)
```

**Impacto no SARIMAX.** Valida a separação sem quebrar o ADR-010: pagamento e cliente
continuam **fora** do X do modelo e serviram só de evidência.

**Base na literatura.**

- ✅ Kalchschmidt; Verganti; Zotteri (2006): segmentar clientes heterogêneos e prever
  cada segmento à parte.
- 📄 Bartezzaghi; Verganti; Zotteri (1999).

### 5.4 Teto no 99º percentil (winsorização)

**O que é.** Nos picos que sobram no balcão, os dias acima do 99º percentil dos dias
abertos são rebaixados a esse valor. Isso é feito **só no treino**; o erro continua sendo
medido contra a venda real.

**Resultado.**

- Sozinho, o teto quase não ajuda Itabirito (MASE 1,434 → 1,401).
- Depois da separação, acrescenta de 1% a 2%.
- Em Jardim Canadá, o teto reduz o maior dia de 14 para 4,4 vezes a média e a curtose de
  43,9 para 2,7. A série vira "suave" pelo critério de 1.10 (CV² 0,40).

**Pseudocódigo** (`teto_quantil`):

```text
teto(série_de_treino, q = 0,99):
    abertos ← dias de segunda a sábado com venda > 0
    limite  ← quantil_q(abertos)
    devolver min(série, limite)          # só no treino; o erro é medido na série real
```

**Impacto no SARIMAX.** Está no treino: `z = log1p(teto_quantil(y).clip(lower=0))`,
recalculado em cada rodada.

**Base na literatura.**

- ✅ Hyndman; Athanasopoulos (2021, §13.9): tratar picos, mas não apagá-los sem entender
  a causa. Por isso as encomendas são **separadas**, não apagadas.
- ✅ Chen; Liu (1993).
- 💡 Dixon (1960): a winsorização.

### 5.5 Teste das quatro variantes, sem vazamento

**O que é.** O mesmo walk-forward (26 × 14 dias) com quatro receitas por unidade.

**Resultado** (MASE):

| Variante | Itabirito SARIMAX | Itabirito HW | Jardim Canadá SARIMAX | Jardim Canadá HW |
| --- | --- | --- | --- | --- |
| Como era (total → total) | 1,434 | 1,311 | 0,659 | 0,727 |
| Só o teto | 1,401 | 1,283 | 0,648 | 0,713 |
| Só separar | 0,810 | 0,699 | 0,656 | 0,724 |
| **Separar + teto** | **0,796** | **0,688** | **0,646** | **0,710** |

Gráfico: [26](../../../ia-predictor/training_scripts/results/plots/eda/26_encomendas_mase.png).

**Pseudocódigo** (`_janelas`, `teste_previsao`):

```text
para cada janela i (26 × 14 dias):
    limiar ← limiares(linhas com data < início da janela)      # SÓ o passado
    balcão ← série diária das linhas não marcadas
    original:     treina no total          → avalia contra o total
    só_teto:      treina em teto(total)    → avalia contra o total
    só_separar:   treina no balcão         → avalia contra o balcão
    separar_teto: treina em teto(balcão)   → avalia contra o balcão (e também contra o total)
    MASE com a escala do treino REAL (sem teto)
```

**Impacto no SARIMAX.** Define a receita que o treino usa: separar e aplicar o teto, com o
limiar recalculado por rodada. Itabirito vai de 1,434 para 0,796 já com o modelo de teste
simples. No treino final (com o calendário corrigido e d = 1), as duas lojas chegam a
**0,58**.

**Limite honesto:** contra a venda **total**, Itabirito volta a ter MASE 1,26. A encomenda
continua imprevisível pelo histórico. No ano de teste do doc 04, ela foi 51% da venda e
70% do erro de Itabirito.

**Base na literatura.**

- ✅ Hyndman; Koehler (2006): o MASE.
- 💡 Tashman (2000): origem móvel sem vazamento.

### 5.6 Sensibilidade ao número K

**O que é.** Repete a variante "separar + teto" com K = 3 e K = 10.

**Resultado.** O MASE de Itabirito fica entre **0,79 e 0,80** com K = 3, 5 ou 10.

**Pseudocódigo** (`main`):

```text
para K ∈ {3, 5, 10}: MASE(separar_teto, K)    # mesmo walk-forward
```

**Impacto no SARIMAX.** Mostra que K = 5 **não é um ajuste fino** que só funciona com esse
número. O treino usa `K_DIAS_TIPICOS = 5` sem precisar calibrar.

**Base na literatura.** ✅ Pearson et al. (2016). Filtros por múltiplo da mediana são
pouco sensíveis ao multiplicador, desde que ele separe a cauda.

### 5.7 Antes × depois (a bateria da Análise 2 reaplicada)

**O que é.** Roda o mesmo diagnóstico da Análise 2 (`analisa_serie`) na série total, na de
balcão e na de balcão com teto, e recalcula a classe de demanda (1.10).

**Resultado** (Itabirito):

| Indicador | Antes (total) | Balcão | Balcão + teto |
| --- | --- | --- | --- |
| Veredito | atenção | ok | ok |
| CV | 2,39 | 1,25 | 1,11 |
| Maior dia ÷ média | 37,2 | 13,4 | 7,2 |
| Curtose | 82,6 | 29,0 | 12,7 |
| **Força do ciclo semanal** | **0,07** | 0,20 | **0,24** |
| **Tendência** | **+54%/ano** | +8%/ano | +10%/ano |
| CV² (classe) | 4,58 (errática) | 1,11 (errática) | 0,84 (errática) |
| MASE SARIMAX | 1,434 | 0,810 | 0,796 |

**Pseudocódigo** (`bloco_antes_depois`, `_resumo_serie`):

```text
para cada unidade:
    para série ∈ {total, balcão, teto(balcão)}:
        diagnóstico ← analisa_serie(série)        # a bateria 2.1–2.11
        ADI, CV² e classe de Syntetos, Boylan e Croston
```

**Impacto no SARIMAX.**

- **O ciclo semanal estava escondido pelos picos.** Sem eles, fica mais de 3 vezes mais
  forte, e é exatamente o que o SARIMAX usa para prever.
- **A tendência de +54% era quase toda encomenda.** As encomendas foram de 68 mil
  unidades em 2024 para 377 mil em 2025. Por isso a recomendação de d = 1 "por tendência"
  (2.7) perdeu força, e o d = 1 ficou justificado pelas **mudanças de nível** (2.8).
- Itabirito sai de "atenção" para "ok".

**Base na literatura.** ✅ Syntetos; Boylan; Croston (2005): a mudança de CV² mostra a
série ficando mais regular.

---

## Síntese: de onde veio cada peça do treino final

O treino final é a variante **A1 d = 1** de
[`sarimax_l1_por_loja.py`](../../../ia-predictor/training_scripts/baseline/sarimax_l1_por_loja.py)
([doc 04](../04-treino_l1_por_loja.md)):

```text
para cada loja u e cada rodada do walk-forward (origem):
    limiar ← K × mediana diária, só com o passado                                   # 5.2, 5.5
    y ← venda diária de balcão (linhas abaixo do limiar)                             # 4.5, 5.2
    z ← log1p( min(y, p99 dos dias abertos) )                                        # 2.2, 5.4
    X ← [dia_seg … dia_sab, loja_fechada, abertura_excepcional]                      # 1.4, 2.1, 2.3, 2.6
    ordem ← escolhida uma vez, com dados até 01/03/2025, pelo menor AIC entre
            p, q ∈ {0,1,2}; P, Q ∈ {0,1}; m = 7; D = 0; d = 1                         # 2.4, 2.5, 2.8, 2.9
    ajustar SARIMAX(z, X) e prever 14 dias com o X futuro (o calendário é conhecido)
    previsão ← expm1(μ) = mediana;  IC95 ← expm1 dos limites em log                  # 2.2
    avaliar contra o balcão real: MASE, erro ÷ naïve semanal, rodadas vencidas,
                                  acerto e largura do IC95                           # 3.3, 5.5
```

| Peça do treino | Valor | Análise que justificou |
| --- | --- | --- |
| Nível do modelo | 2 séries, uma por loja | 1.5, 1.7, 1.10, 4.2–4.5 |
| Alvo | venda de balcão (encomendas fora) | 5.1–5.7 |
| Limiar de encomenda | 5 × mediana diária, recalculado a cada rodada | 5.2, 5.5, 5.6 |
| Teto | p99 dos dias abertos, só no treino | 5.4 |
| Transformação | `log1p`; previsão = mediana (`expm1`); Duan descartado | 2.2 (e doc 04 §2) |
| Período sazonal | m = 7 | 1.9, 2.3, 2.4 |
| Diferenciação sazonal | D = 0 | 2.4, 2.5 (ADR-004) |
| Diferenciação | d = 1 (venceu d = 0) | 2.7, 2.8 |
| Grade de ordens | p, q ≤ 2; P, Q ≤ 1; AIC | 2.9 |
| Ordem escolhida | (0,1,1)(0,0,1)₇ nas duas lojas | 2.4, 2.8, 2.9 |
| Exógenas | 6 dummies de dia, `loja_fechada`, `abertura_excepcional` | 1.4, 2.1, 2.3, 2.6 (e doc 03) |
| Fora das exógenas | pagamento, vendedor, clima, janela de 7 dias | 1.4, 2.6 (e doc 03) |
| Validação | 26 rodadas × 14 dias contra a naïve semanal | 3.3, 4.2, 5.5 |
| Resultado | MASE 0,58 nas 2 lojas; vence a naïve em 24/26 rodadas; IC95 com 91–94% de acerto → `trained` | doc 04 §3.2 |

---

## Ressalvas metodológicas (para a banca)

### 1. O efeito das datas comemorativas não desconta o dia da semana *(encontrada em 2026-10-04)*

A razão de 2.6 compara a janela (o dia e os 2 anteriores) com a média geral da série. Só
que a média geral inclui dias fortes (meio de semana) e dias fracos ou fechados (sábado,
domingo, feriado). Quando a data cai num domingo, como o Dia das Mães e o Dia dos Pais, a
janela é sexta, sábado e domingo, e fica abaixo da média **mesmo sem nenhum efeito da
data**.

Os números abaixo foram recalculados com os mesmos dados e funções do EDA
(`serie_unidade`, `serie_diaria`, `datas_comemorativas`) e o calendário da Etapa 6. O
"esperado" é a média dos índices de dia da semana dos dias da janela, contando 0 para
dia de loja fechada. **Essa conta não está gravada em nenhum script do repositório.**

**Dia das Mães:**

| Série | Razão do relatório | Esperado sem efeito da data | Razão ajustada | A leitura muda? |
| --- | --- | --- | --- | --- |
| Jardim Canadá (total) | 0,66 | 0,62 | **1,07** | **Sim**: não cai, fica neutro |
| Itabirito (total) | 0,70 | 0,57 | **1,24** | **Sim**: sobe |
| JC · Grama | 0,76 | 0,53 | **1,44** | **Sim**: sobe |
| Itabirito · Grama | 0,19 | 0,38 | 0,51 | Não: cai |
| JC · Produtos de jardim | 0,53 | 0,69 | 0,77 | Não: cai (menos) |
| Itabirito · Produtos de jardim | 0,95 | 0,71 | **1,35** | **Sim**: sobe |
| JC · Flores de corte | 2,14 | 0,99 | 2,17 | Não: dispara |
| Itabirito · Flores de corte | 5,00 | 1,15 | 4,34 | Não: dispara |

**Outras leituras que mudam:**

- **Dia dos Namorados:** no total de Jardim Canadá, passa de 1,16 para 0,84 (cai, em vez
  de subir). Em Grama de Jardim Canadá, de 1,21 para 0,82. No total de Itabirito, de 1,52
  para 1,09 (sobe menos).
- **Finados em Jardim Canadá:** o total passa de 0,70 para 0,93 e Grama de 0,69 para
  1,03. Fica neutro, em vez de cair.

**O que se mantém:**

- Flores disparam no Dia da Mulher (≈ 3×), nas Mães e nos Namorados.
- Grama e Produtos de jardim caem no Natal (0,42–0,59 ajustado), no Dia dos Pais e no Dia
  da Mulher.
- Finados sobe muito em Itabirito (total 3,80; Grama 5,83).
- **O efeito muda de sinal entre categorias**, que é a conclusão principal.

**O que isso muda no treino:** nada no L1 final, que não usa essas razões (usa
`abertura_excepcional`). O que muda:

- o texto de §3.0 e §3.4 do relatório;
- o exemplo do Dia das Mães na explicação 004 ("a unidade cai para 0,66×"; ajustado, ela
  fica neutra);
- a **desagregação por categoria**, que deve usar o índice ajustado (pseudocódigo em 2.6).

### 2. O índice de dia da semana usa uma média que inclui o domingo

Ver o "cuidado de leitura" em 2.3. A ordem dos dias não muda, mas os índices dos dias
abertos ficam cerca de 1/6 acima do que seriam contra a média dos dias abertos.

### 3. O ADI das séries por unidade conta domingos e feriados como "sem venda"

O ADI de 1,21 vem inteiro dos dias de loja fechada, que são determinísticos. Pelo critério
de Syntetos, Boylan e Croston, a série parece mais intermitente do que a demanda realmente
é. O SARIMAX trata esses dias com `loja_fechada`.

### 4. O MASE fica otimista quando o treino tem picos

A escala do MASE é o erro da naïve **no treino**. Picos de encomenda inflam essa escala,
e o MASE parece melhor do que é: no doc 02, MASE 0,40 correspondia a um ganho real de só
18%. Por isso os treinos também reportam o erro ÷ naïve na mesma janela e o número de
rodadas vencidas (EDA §4, item 14).

### 5. O EDA usou o fator de Duan, e o treino usa a mediana

Dentro do EDA, as comparações são justas, porque os dois lados recebem o mesmo tratamento.
Mas os valores absolutos do EDA (por exemplo, o 0,796 de Itabirito) não são comparáveis
diretamente aos do treino final (0,58).

### 6. O modelo de teste do EDA tem ordem fixa

As Análises 3–5 usam SARIMAX(1,0,1) com constante, sem termos sazonais, e com as dummies
de calendário. Não é o modelo final. Serve para comparar alternativas com o mesmo
instrumento.

### 7. O p-valor do KPSS é limitado à tabela

O p-valor do KPSS sai preso entre 0,01 e 0,10 (o script registra isso). "p = 0,01" quer
dizer "≤ 0,01".

### 8. Só cerca de 2 ciclos anuais

Os perfis mensais e o efeito das datas se apoiam em 2 ocorrências de cada data. Os
resultados de 2.5 e 2.6 são indícios, não estimativas firmes.

### 9. Diferenças pequenas entre modelos não têm teste de significância

A regra dos 5% e a menção de que "diferenças até ~10% estão no ruído" são heurísticas. Se
a banca pedir, o teste de Diebold–Mariano compara a acurácia de duas previsões nas mesmas
janelas (💡 Diebold; Mariano, 1995).

---

## Referências

### ✅ Já no artigo (`TCC2 - Inicial.docx`) e usadas neste mapa

| Referência | Usada em |
| --- | --- |
| ARUNRAJ, N. S.; AHRENS, D.; FERNANDES, M. Application of SARIMAX model to forecast daily sales in food retail industry. *International Journal of Operations Research and Information Systems*, v. 7, n. 2, p. 1–21, 2016. | 2.3, 2.6 |
| BARTEZZAGHI, E.; VERGANTI, R. Managing demand uncertainty through order overplanning. *International Journal of Production Economics*, v. 40, n. 2–3, p. 107–120, 1995. | 5.2 |
| BOX, G. E. P.; JENKINS, G. M.; REINSEL, G. C.; LJUNG, G. M. *Time Series Analysis: Forecasting and Control*. 5. ed. Hoboken: Wiley, 2015. | 1.9, 2.5, 2.9 |
| BRASIL. Lei nº 13.709, de 14 de agosto de 2018 (LGPD). | 1.4 |
| CHEN, C.; LIU, L.-M. Forecasting time series with outliers. *Journal of Forecasting*, v. 12, n. 1, p. 13–35, 1993. | 2.10, 5.1, 5.4 |
| CROSTON, J. D. Forecasting and stock control for intermittent demands. *Operational Research Quarterly*, v. 23, n. 3, p. 289–303, 1972. | 1.7, 1.10 |
| FLIEDNER, G. Hierarchical forecasting: issues and use guidelines. *Industrial Management & Data Systems*, v. 101, n. 1, p. 5–12, 2001. | 2.12, 4.1, 4.3 |
| GROSS, C. W.; SOHL, J. E. Disaggregation methods to expedite product line forecasting. *Journal of Forecasting*, v. 9, n. 3, p. 233–254, 1990. | 2.12, 3.3, 4.2 |
| HUBER, J.; GOSSMANN, A.; STUCKENSCHMIDT, H. Cluster-based hierarchical demand forecasting for perishable goods. *Expert Systems with Applications*, v. 76, p. 140–151, 2017. | 1.7, 4.4 |
| HYNDMAN, R. J.; ATHANASOPOULOS, G. *Forecasting: principles and practice*. 3. ed. Melbourne: OTexts, 2021. Seções usadas: §2.4, §2.8, §3.1, §3.6, §4.3, §5.4, §5.6, §5.10, §7.4, §7.6, cap. 10, §8.3, §9.1, §9.10, §11.1–11.2, §12.1, §13.2, §13.9. | 1.4, 1.9, 1.10, 2.2–2.9, 3.3, 4.1, 4.2, 5.4 |
| HYNDMAN, R. J.; KOEHLER, A. B. Another look at measures of forecast accuracy. *International Journal of Forecasting*, v. 22, n. 4, p. 679–688, 2006. | 3.3, 5.5 |
| KALCHSCHMIDT, M.; VERGANTI, R.; ZOTTERI, G. Forecasting demand from heterogeneous customers. *International Journal of Operations & Production Management*, v. 26, n. 6, p. 619–638, 2006. | 5.3 |
| PEARSON, R. K.; NEUVO, Y.; ASTOLA, J.; GABBOUJ, M. Generalized Hampel filters. *EURASIP Journal on Advances in Signal Processing*, v. 2016, art. 87, 2016. | 5.2, 5.6 |
| SYNTETOS, A. A.; BOYLAN, J. E. The accuracy of intermittent demand estimates. *International Journal of Forecasting*, v. 21, n. 2, p. 303–314, 2005. | 1.10 |
| SYNTETOS, A. A.; BOYLAN, J. E.; CROSTON, J. D. On the categorization of demand patterns. *Journal of the Operational Research Society*, v. 56, n. 5, p. 495–503, 2005. | 1.10, 2.1, 5.7 |
| TEUNTER, R. H.; SYNTETOS, A. A.; BABAI, M. Z. Intermittent demand: linking forecasting to inventory obsolescence. *European Journal of Operational Research*, v. 214, n. 3, p. 606–615, 2011. | 1.10 |
| WIRTH, R.; HIPP, J. CRISP-DM: towards a standard process model for data mining. In: *Proceedings of the 4th International Conference on the Practical Applications of Knowledge Discovery and Data Mining*. London, 2000. p. 29–39. | 1.1–1.3 |
| ZOTTERI, G.; KALCHSCHMIDT, M. A model for selecting the appropriate level of aggregation in forecasting processes. *International Journal of Production Economics*, v. 108, n. 1–2, p. 74–83, 2007. | 1.7, 4.2, 4.5 |

As outras referências do artigo (Breiman, 2001; Makridakis et al., 2020; Pavlyshenko, 2019;
Pressman; Maxim; Sommerville; normas ABNT) pertencem a outros capítulos e não sustentam as
análises exploratórias.

> **Conferir no artigo:** a entrada de PAVLYSHENKO (2019) repete o título do trabalho de
> ARUNRAJ et al. (2016) ("Application of SARIMAX model to forecast daily sales in food
> retail industry"). O evento citado (2nd IEEE Data Stream Mining and Processing, Lviv)
> também parece ser de 2018, não de 2019. Vale conferir título, evento e ano antes da
> entrega. O [ADR-001](../ADR-001-sarimax_central_model.md) atribui a Pavlyshenko um
> resultado com SARIMAX em perecíveis, que pode ser do trabalho de Arunraj et al.

### 📄 Citadas nos documentos do repositório, ainda fora do artigo

| Referência | Usada em |
| --- | --- |
| BABAI, M. Z.; BOYLAN, J. E.; ROSTAMI-TABAR, B. Demand forecasting in supply chains: a review of aggregation and hierarchical approaches. *International Journal of Production Research*, v. 60, n. 1, p. 324–348, 2022. | 4.5 |
| BARTEZZAGHI, E.; VERGANTI, R.; ZOTTERI, G. A simulation framework for forecasting uncertain lumpy demand. *International Journal of Production Economics*, v. 59, n. 1–3, p. 499–510, 1999. | 5.2, 5.3 |
| BOX, G. E. P.; TIAO, G. C. Intervention analysis with applications to economic and environmental problems. *Journal of the American Statistical Association*, v. 70, n. 349, p. 70–79, 1975. | 1.5, 2.6 |
| CHEN, C.; LIU, L.-M. Joint estimation of model parameters and outlier effects in time series. *Journal of the American Statistical Association*, v. 88, n. 421, p. 284–297, 1993. | 5 (ADR-012) |
| JOHNSTON, F. R.; BOYLAN, J. E.; SHALE, E. A. An examination of the size of orders from customers, their characterisation and the implications for inventory control of slow moving items. *Journal of the Operational Research Society*, v. 54, n. 8, p. 833–837, 2003. | 5.1 |
| KALCHSCHMIDT, M.; ZOTTERI, G.; VERGANTI, R. Inventory management in a multi-echelon spare parts supply chain. *International Journal of Production Economics*, v. 81–82, p. 397–413, 2003. (O ADR-012 avisa: conferir o texto completo antes de citar.) | 5.2 |
| OLHAGER, J. Strategic positioning of the order penetration point. *International Journal of Production Economics*, v. 85, n. 3, p. 319–329, 2003. | 5.2 |
| VERGANTI, R. Order overplanning with uncertain lumpy demand: a simplified theory. *International Journal of Production Research*, v. 35, n. 12, p. 3229–3248, 1997. | 5.2 |

### 💡 Sugestões: referências clássicas dos métodos, não usadas no projeto até aqui

Todas precisam ser conferidas no texto original antes de entrar no artigo.

| Referência | Para qual análise |
| --- | --- |
| BOX, G. E. P.; COX, D. R. An analysis of transformations. *Journal of the Royal Statistical Society: Series B*, v. 26, n. 2, p. 211–252, 1964. | 2.2 (`log1p`) |
| CLEVELAND, R. B.; CLEVELAND, W. S.; McRAE, J. E.; TERPENNING, I. STL: a seasonal-trend decomposition procedure based on loess. *Journal of Official Statistics*, v. 6, n. 1, p. 3–73, 1990. | 2.4 |
| DICKEY, D. A.; FULLER, W. A. Distribution of the estimators for autoregressive time series with a unit root. *Journal of the American Statistical Association*, v. 74, n. 366, p. 427–431, 1979. | 2.8 |
| DIEBOLD, F. X.; MARIANO, R. S. Comparing predictive accuracy. *Journal of Business & Economic Statistics*, v. 13, n. 3, p. 253–263, 1995. | Ressalva 9 |
| DIXON, W. J. Simplified estimation from censored normal samples. *The Annals of Mathematical Statistics*, v. 31, n. 2, p. 385–391, 1960. | 5.4 (winsorização) |
| DUAN, N. Smearing estimate: a nonparametric retransformation method. *Journal of the American Statistical Association*, v. 78, n. 383, p. 605–610, 1983. | 2.2, 3.3 |
| HOLT, C. C. Forecasting seasonals and trends by exponentially weighted moving averages. *International Journal of Forecasting*, v. 20, n. 1, p. 5–10, 2004 (reimpressão do relatório de 1957). | 3.3 |
| KAUFMAN, S.; ROSSET, S.; PERLICH, C.; STITELMAN, O. Leakage in data mining: formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data*, v. 6, n. 4, art. 15, 2012. | 1.4 |
| KWIATKOWSKI, D.; PHILLIPS, P. C. B.; SCHMIDT, P.; SHIN, Y. Testing the null hypothesis of stationarity against the alternative of a unit root. *Journal of Econometrics*, v. 54, n. 1–3, p. 159–178, 1992. | 2.8 |
| LJUNG, G. M.; BOX, G. E. P. On a measure of lack of fit in time series models. *Biometrika*, v. 65, n. 2, p. 297–303, 1978. | 2.9 |
| NOSEK, B. A.; EBERSOLE, C. R.; DeHAVEN, A. C.; MELLOR, D. T. The preregistration revolution. *Proceedings of the National Academy of Sciences*, v. 115, n. 11, p. 2600–2606, 2018. | 3.4 |
| SILVER, E. A.; PYKE, D. F.; THOMAS, D. J. *Inventory and production management in supply chains*. 4. ed. Boca Raton: CRC Press, 2017. | 1.8 |
| TASHMAN, L. J. Out-of-sample tests of forecasting accuracy: an analysis and review. *International Journal of Forecasting*, v. 16, n. 4, p. 437–450, 2000. | 3.3, 5.5 |
| TUKEY, J. W. *Exploratory data analysis*. Reading: Addison-Wesley, 1977. | 2.10 |
| WANG, X.; SMITH, K.; HYNDMAN, R. Characteristic-based clustering for time series data. *Data Mining and Knowledge Discovery*, v. 13, n. 3, p. 335–364, 2006. | 2.4 |
| WICKRAMASURIYA, S. L.; ATHANASOPOULOS, G.; HYNDMAN, R. J. Optimal forecast reconciliation for hierarchical and grouped time series through trace minimization. *Journal of the American Statistical Association*, v. 114, n. 526, p. 804–819, 2019. | 4.5 (alternativa não testada) |
| WINTERS, P. R. Forecasting sales by exponentially weighted moving averages. *Management Science*, v. 6, n. 3, p. 324–342, 1960. | 3.3 |
