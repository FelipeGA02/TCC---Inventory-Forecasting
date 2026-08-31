# Plano de Pré-processamento dos Dados

Documenta o pipeline em [`ia-predictor/training_scripts/preprocessing/`](../../ia-predictor/training_scripts/preprocessing/):
como os XLSX brutos de "Contas a Receber" viram a base transacional consolidada, e como
essa base é preparada para alimentar a modelagem hierárquica (L1 SARIMAX por
`unidade × categoria` → L2 desagregação → L3 reposição — ver
[ADR-009](ADR-009-granularidade-diaria-e-reposicao.md)).

> Escopo de 2026-08-30 (diário). Este documento foi reescrito por inteiro para o pipeline
> diário; a versão mensal anterior está no histórico do git.

---

## 1. Visão geral

O alvo do modelo L1 é uma **série temporal diária**: para cada par `(unidade, categoria)`,
a soma de `qtdade` vendida por dia. O pré-processamento não constrói essa série (isso é
`prepare_daily_series()`, no backend/experimentação) — ele entrega a **base transacional
limpa e enriquecida** de onde a série é somada.

```
data/raw/*.xlsx  (26 planilhas mensais, jan/2024–fev/2026)
        │
        ▼
┌──────────────────────────────────────────────┐
│ Etapa 1 — build_dataset.py                    │  parser + dedup entre arquivos + log
│  → output/contas_a_receber.csv               │  20 colunas · 1 linha por (documento, produto)
│  → output/processamento_log.json             │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ Etapa 2 — reduce_schema.py                    │  remove 11 colunas sem uso na modelagem
│  → output/contas_a_receber_sem_colunas.csv   │  9 colunas
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ Etapa 3 — map_taxonomy.py                     │  deriva `unidade` e `categoria`
│  → output/contas_a_receber_taxonomia.csv     │  11 colunas · pronto para prepare_daily_series
└──────────────────────────────────────────────┘
        │
        ▼
   prepare_daily_series(df, unidade, categoria)   ← FORA deste pipeline
   (training_scripts/baseline/ — Fase 1 do plano de experimentos)
```

### Por que etapas separadas

Cada etapa resolve um problema distinto e tem uma saída inspecionável: extrair uma tabela
de um relatório que não é tabular (1), reduzir ao subconjunto de colunas com sinal (2), e
adicionar as duas dimensões de agrupamento que o L1 precisa e que não existem na origem
(3). Rodar em estágios — em vez de um script monolítico — foi o que permitiu, por exemplo,
achar o problema de deduplicação da seção 3 olhando o CSV intermediário da Etapa 1. A
divisão espelha o `backend/domain/etl/` de produção (parser → normalizer → feature builder).

Cada etapa é um módulo com função pura e bloco `if __name__ == '__main__':`. A partir de
`ia-predictor/`, na ordem:

```bash
python -m training_scripts.preprocessing.build_dataset
python -m training_scripts.preprocessing.reduce_schema
python -m training_scripts.preprocessing.map_taxonomy
```

---

## 2. Etapa 1 — `build_dataset.py`: parsing + deduplicação + log

### Por que existe

O relatório de "Contas a Receber" foi feito para uma pessoa ler, não para um modelo
consumir: é texto em blocos, uma venda por bloco, sem estrutura de tabela. É preciso
transformá-lo numa tabela onde cada linha é uma unidade de análise consistente — aqui,
**1 produto dentro de 1 documento**. Esta é também a única etapa que toca os 26 arquivos
brutos; a deduplicação e o controle de hash vivem aqui porque é a única chance de garantir
que cada venda real apareça exatamente uma vez.

### O que o script faz

Cada bloco começa numa linha `Documento: C1 44799`, seguido de linhas de cabeçalho
(Cliente, Empresa, Vendedor, Obs), uma linha `Produto` e N linhas de item até `Totais`. O
`parser.py` varre por posição de coluna fixa (`HEADER_COLUMNS`, `DETAIL_COLUMNS`,
`PRODUCT_COLUMNS` em `constants.py` — layout do relatório, estável entre meses) e expande
cada bloco em **um registro por (documento, produto)**.

`build_dataset.py` orquestra as 26 planilhas:

- Cada planilha só é (re)processada se for nova ou o **hash MD5** mudou
  (`processamento_log.json`) — rodar de novo é seguro e idempotente.
- **Deduplicação por chave composta `(doc_numero, produto_cod, emissao, qtdade,
  vl_total)`**, aplicada **só entre arquivos diferentes**, nunca dentro do mesmo arquivo.
  Existe porque os relatórios mensais têm sobreposição de datas nas bordas do mês. Ver o
  achado abaixo.
- Linhas fora do padrão vão para `skipped` (com linha e motivo) sem interromper — o
  objetivo é recuperação máxima de um relatório não desenhado para máquina.

### Achado — a deduplicação original descartava vendas reais (corrigido)

A primeira versão deduplicava por `(doc_numero, produto_cod)` comparando cada registro
contra **todos** os já vistos, inclusive dentro do próprio arquivo. Isso presumia que um
produto só aparece uma vez por documento — presunção errada.

Em `abril 24.xlsx` isolado (11.746 registros), essa chave sinalizou 201 "duplicatas".
Comparando os campos de venda entre a 1ª e a 2ª ocorrência de cada chave:

| | Quantidade |
| --- | --- |
| Valores de venda diferentes entre as duas ocorrências | 165 |
| Valores de venda idênticos | 36 |

Os 165 com valores diferentes já eram claramente vendas distintas. Os 36 idênticos
pareciam duplicatas — até o teste contra o total do documento.

**Prova**: o documento `995` tem 12 linhas de produto, entre elas **duas** de `433NL`
(ambas `qtdade=3`, `tot_liq=6`). A soma dos 12 `tot_liq` bate **exatamente** com o
`total_liquido_doc` do relatório (756,30). Se a 2ª linha de `433NL` fosse duplicata de
exportação, o total seria 750,30. O sistema de origem contabilizou as duas linhas — só
possível se ambas forem vendas reais (item escaneado duas vezes no caixa). Ou seja:
**nenhuma** das 201 "duplicatas" era duplicata.

**Correção** (`build_dataset.py`, `process_pending_files`; `constants.py`,
`DUPLICATE_KEY_FIELDS`):

1. As chaves de um arquivo só entram no conjunto "já visto" **depois** que o arquivo
   inteiro é processado. A dedup passa a valer **exclusivamente entre arquivos**.
2. A chave endureceu: `(doc_numero, produto_cod)` → `(doc_numero, produto_cod, emissao,
   qtdade, vl_total)`. `doc_numero` sozinho não é único — o mesmo número se repete entre
   `doc_tipo` diferentes (32.572 casos nos dados reais). Exigir data, quantidade e valor
   batendo distingue uma duplicata real de exportação de dois documentos não relacionados
   que só compartilham o número.

### O JSON de log

`output/processamento_log.json`, dois blocos aninhados:

```json
{
  "arquivos_processados": {
    "abril 24.xlsx": {
      "hash": "919e1396c9f47cf2d09e486d7cc27830",
      "processado_em": "2026-08-23T18:32:44",
      "registros_adicionados": 11746,
      "registros_pulados": 0,
      "duplicatas_encontradas": 0
    }
  },
  "historico_execucoes": [
    { "executado_em": "...", "arquivos": ["..."],
      "total_registros_adicionados": 333019, "total_pulados": 0, "total_duplicatas": 0 }
  ],
  "ultima_atualizacao": "..."
}
```

`arquivos_processados` por hash + `historico_execucoes` por rodada = rastreabilidade
completa (Princípio V) sem reprocessar nada para auditar.

---

## 3. Execução real — volume e observações

`build_dataset.py` rodado de ponta a ponta contra as 26 planilhas reais
(jan/2024–fev/2026), com a correção da dedup:

| Métrica | Valor |
| --- | --- |
| Planilhas processadas | 26 |
| Registros reais (`csv.DictReader`, respeitando aspas) | 333.019 |
| Linhas físicas do CSV (`wc -l`) | 351.991 |
| Duplicatas entre arquivos / registros pulados | 0 / 0 |
| Cabeçalho | 20 colunas, 1 linha por (documento, produto) |
| `produto_cod` distintos | 5.166 |
| `empresa` (valores distintos) | 3 — `FLORICULTURA VERDE PERTO CANADÁ LTDA`, `GARDEN CENTER VERDE PERTO LTDA`, `VERDE PERTO JARDINAGEM LTDA` |
| Intervalo de datas | 02/01/2024 – 28/02/2026 |
| Dias **com** venda (em qualquer unidade) | 654 de ~789 do calendário — os ~135 sem venda batem com fechamento aos domingos/feriados; folga confortável sobre o mínimo de 180 dias do L1 |
| Linhas com `qtdade <= 0` | 880 — removidas pelo `normalizer` de produção, não por este pipeline (seção 6) |

**`wc -l` superestima.** A diferença (351.991 − 333.019 ≈ 19 mil) não é dado faltando: é
`wc -l` contando **quebras de linha dentro de campos entre aspas** (RFC 4180) — quase
sempre o campo `obs` (`"levar maquininha de cartao \n5 x"`). Mais um motivo para removê-lo
na Etapa 2.

**Zero duplicatas entre arquivos neste dataset.** A lógica de dedup entre arquivos não é
inútil — o cenário que ela cobre (mesma venda exportada em dois meses consecutivos, na
borda do mês) é real no processo de exportação; só não se concretizou nos 26 arquivos
atuais. Fica pronta, sem custo quando não acontece.

---

## 4. Etapa 2 — `reduce_schema.py`: remoção de colunas

### Por que reduzir o schema

O relatório existe para controle financeiro e fiscal, não para série temporal de vendas.
Carrega colunas que são ruído puro para prever demanda, texto livre de alta cardinalidade
que atrapalha a leitura do arquivo, e PII que a constituição proíbe expor (Princípio VI).
Critério de cada remoção: **essa coluna muda a resposta de "quanto dessa categoria vai
ser vendido amanhã"?**

### Decisão

```python
COLUMNS_TO_DROP = [
    'operador', 'obs', 'icms_ret', 'arquivo_origem',
    'cliente_nome', 'produto_nome', 'doc_tipo',
    'doc_numero', 'cliente_cod',
    'pagamento', 'vendedor',            # revisão 2026-08-30 — ver ADR-010
]
```

| Coluna | Por que sai |
| --- | --- |
| `operador` | Quem operou o caixa — operacional interno, sem poder explicativo sobre volume. |
| `obs` | Texto livre; alta cardinalidade; campo com quebras de linha embutidas (seção 3). |
| `icms_ret` | Fiscal (ICMS retido). `0` na esmagadora maioria das linhas — metadado contábil. |
| `arquivo_origem` | Artefato do processamento (nome do XLSX) — redundante com `emissao`. |
| `cliente_nome` | PII — expor violaria o Princípio VI. |
| `produto_nome` | Texto livre com grafias variáveis. `produto_cod` já identifica o produto de forma unívoca — e é a chave da Etapa 3 e da modelagem. |
| `doc_tipo` | Código de documento interno (`C1`, `C7`, `F3`, `NN`...). Não é dimensão de negócio com valor preditivo. |
| `doc_numero` | Id do documento. Usado na dedup da Etapa 1 (que roda antes). Daqui pra frente é só um id — sem magnitude nem ordem. Rastreabilidade fica no CSV da Etapa 1. |
| `cliente_cod` | Id de cliente, cardinalidade altíssima. Se segmentação por cliente for útil, entra como feature derivada agregada, não o id cru. |
| `pagamento` | **ADR-010.** Atributo de *transação* (nível de agregação errado para a série diária da categoria), não conhecível para os dias futuros previstos (leakage) e *consequência* da venda, não driver. Fica no CSV da Etapa 1 para a triagem de importância na EDA. |
| `vendedor` | **ADR-010.** Mesma natureza. "Vendedor X vende mais" não é sinal de *demanda* da categoria. Se houver sinal, vira feature derivada agregada (ex.: `n_vendedores_ativos_no_dia`). |

**Colunas mantidas** (9): `emissao`, `empresa`, `produto_cod`, `qtdade`, `vl_unit`,
`vl_total`, `vl_desconto`, `tot_liq`, `total_liquido_doc`.

- `emissao` → **eixo temporal** da série diária.
- `empresa` → entra na Etapa 3 para derivar `unidade` (não é usada crua na modelagem).
- `produto_cod` → entra na Etapa 3 para derivar `categoria`; e é a chave da desagregação L2.
- `qtdade` → **variável alvo** (somada por dia).
- `vl_*`, `tot_liq` → matéria-prima de features de preço/desconto (avaliadas na Fase 3 do
  plano de experimentos, não obrigatórias no L1 baseline).
- `total_liquido_doc` → mantido para reconferência de integridade (o teste do documento
  `995` na seção 2 depende dele).

---

## 5. Etapa 3 — `map_taxonomy.py`: derivar `unidade` e `categoria`

O modelo L1 agrupa por `unidade × categoria`. **Nenhuma das duas colunas existe na base
transacional** (só `empresa`, `produto_cod` e `produto_nome`). Esta etapa as constrói a
partir de tabelas de/para versionadas em `training_scripts/preprocessing/taxonomy/`, e é o
principal trabalho novo do pré-processamento no escopo diário.

`map_taxonomy.py` lê o CSV reduzido da Etapa 2 (9 colunas) e um lookup
`produto_cod → produto_nome` construído a partir do CSV da Etapa 1 (que ainda tem
`produto_nome`), e adiciona duas colunas: `unidade` e `categoria`.

### 5.1 `unidade` — a partir de `empresa`

`empresa` tem 3 valores, que são **entidades jurídicas** (LTDA), não necessariamente as 3
lojas físicas. De/para de trabalho em `taxonomy/unidades.py`:

| `empresa` | `unidade` (de trabalho) | linhas |
| --- | --- | --- |
| `FLORICULTURA VERDE PERTO CANADÁ LTDA` | `Jardim Canadá` | 168.063 |
| `VERDE PERTO JARDINAGEM LTDA` | `Itabirito` | 135.548 |
| `GARDEN CENTER VERDE PERTO LTDA` | `Garden Center` | 29.408 |

`NORMALIZE_EMPRESA` corrige defensivamente o mojibake `CANAD�` → `CANADÁ` já observado em
exportações anteriores (não na rodada atual).

> **A validar com a parceira** (`tasks.md` T000d): as 3 LTDAs correspondem 1:1 às 3
> unidades operacionais do artigo (Nova Lima/Jardim Canadá + Itabirito)? Vários nomes de
> vendedor trazem `(ITABIRITO)`/`(CANADÁ)` — se `empresa` não separar as lojas, a unidade
> terá de vir de outro campo (prefixo de `produto_cod`, faixa de `doc_numero` por loja...).

### 5.2 `categoria` — a partir de `produto_cod` / `produto_nome`

A amostra dos produtos de maior volume mostrou que a **Verde Perto opera como garden
center / jardinagem, não como floricultura de flor de corte**: o carro-chefe é **grama
plantada** (esmeralda, são carlos, amendoim), seguida de mudas em saquinho (`SAQ`),
plantas em vaso (`PT NN`), terra/adubo (`BIOPLANT`, `TERRA VEGETAL`) e insumos de jardim
(manta bidim, separador de grama). Flor de corte (`ROSA EM CABO`, `ALSTROEMERIA`) é fatia
pequena. As categorias refletem isso.

Cascata (primeira que casar vence), em `taxonomy/categorias.py`:

1. **`CATEGORIA_POR_SKU`** — de/para explícito por `produto_cod` (Top-N + curadoria
   manual). Vazio hoje; preenchido na curadoria do Top-N.
2. **`CATEGORIA_REGRAS`** — lista ordenada de `(regex sobre produto_nome, categoria)`. Ex.:
   `FLOR DE CORTE|ROSA EM CABO|ALSTROEMERIA|BUQUÊ|ARRANJO → "Flor de corte e arranjo"`;
   `TERRA|ADUBO|SUBSTRATO|BIOPLANT|CASCA DE PINUS → "Substrato e adubo"`;
   `GRAMA PRETA|PELO DE URSO → "Muda e forração"` (forração, não grama de plantio) e só
   depois `GRAMA → "Grama"`; medida de altura no nome (`0,20 A 0,30CM`, `50 A 60 CM`) →
   `"Arbusto e planta formada"`; `PT NN → "Planta em vaso"`; `SAQ|MUDA|BANDEJA|BEIJO →
   "Muda e forração"`.
3. **`CATEGORIA_DEFAULT = "Outros"`** — SKU sem match. É categoria própria (não descartado);
   se concentrar volume, as regras são refinadas.

`SHELF_LIFE_DIAS` no mesmo módulo mapeia cada categoria à sua validade (ADR-009 §8) —
usado pela camada L3. Não vai no CSV (deriva de `categoria`), pertence à config / tabela
`categories`.

### 5.3 Execução real (2026-08-30)

```text
[map_taxonomy] 333.019 linhas x 11 colunas
[map_taxonomy] Volume (qtdade) por categoria:
  Grama                       1.837.995   (shelf_life=3d)
  Muda e forracao               861.667   (shelf_life=20d)
  Outros                        377.847   (shelf_life=7d)
  Planta em vaso                326.706   (shelf_life=30d)
  Substrato e adubo             221.650   (shelf_life=180d)
  Arbusto e planta formada      128.977   (shelf_life=45d)
  Insumo e acessorio             86.952   (shelf_life=365d)
  Flor de corte e arranjo        72.061   (shelf_life=4d)
  Hortalica e erva               32.730   (shelf_life=7d)
[map_taxonomy] Volume em "Outros": 9.6%
[map_taxonomy] Pares unidade x categoria: 27
```

**Leitura**: até **27 modelos L1** (9 categorias × 3 unidades). "Grama" domina — e tem
validade curta (~3 dias plantada), então o produto perecível central do negócio é grama,
não flor. `"Outros"` em **9,6%** está acima do ideal (~5%); refinar `CATEGORIA_REGRAS`
com uma inspeção dos nomes que caem nele é tarefa da EDA.

### 5.4 Saída

`output/contas_a_receber_taxonomia.csv` — 11 colunas (as 9 da Etapa 2 + `unidade` +
`categoria`). É o arquivo que `prepare_daily_series(df, unidade, categoria)` consome:
filtra por par, soma `qtdade` por dia, reindexa o range diário completo (dias sem venda =
0) e exige ≥ 180 dias.

### 5.5 O que a EDA ainda precisa confirmar

- Quantos dos 27 pares `unidade × categoria` têm ≥ 180 dias de histórico (os que não têm
  ficam `insufficient_data`).
- Reduzir `"Outros"` inspecionando os nomes que caem nele.
- Se a série diária de cada par é densa o suficiente para SARIMAX (a esparsidade por SKU é
  o motivo de agrupar por categoria — validar que o agrupamento resolve).
- Distribuição de `qtdade` por par (define quem recebe `log1p`, CV > 0.7).
- Com a parceira: mapa `empresa → unidade`, mapa `produto → categoria` (ao menos do
  Top-N) e o `shelf_life_dias` real por categoria.

---

## 6. O que este pipeline NÃO resolve (e onde reaparece)

- **Validação de qualidade de dado** (`qtdade <= 0`, `emissao` nula, vírgula decimal) — o
  parser só extrai e formata. Regras de negócio ficam no `domain/etl/normalizer.py` de
  produção (`SPECS.md` §4.2, ainda stub).
- **Confirmação da taxonomia** (`unidade`, `categoria`, `shelf_life_dias` reais) — itens
  de levantamento com a parceira (`tasks.md` T000c e T000d). A Etapa 3 entrega uma versão
  de trabalho com defaults.
- **Construção da série diária** (`prepare_daily_series`) — Fase 1 do
  [plano de experimentos](plano_experimentos_modelagem.md), em `training_scripts/baseline/`.
- **Exógenas de calendário** (dia-da-semana, feriados nacionais/municipais, datas
  comemorativas) — `domain/features/calendar_exogenous.py`; feriados municipais e clima na
  Fase 2 do plano.
- **Features de preço/desconto** a partir de `vl_*` — avaliadas na Fase 3, não no baseline.
- **Desagregação para SKU (L2)** — usa `produto_cod` do CSV da Etapa 3 + histórico; fora
  deste pipeline.

---

## 7. Artefatos

```text
ia-predictor/training_scripts/
├── preprocessing/
│   ├── constants.py            # caminhos + layout de colunas do XLSX + COLUMNS_TO_DROP
│   ├── helpers.py              # format_decimal, parse_field, file_hash, load/save_log...
│   ├── parser.py               # parse_xlsx() — extrai registros do XLSX
│   ├── build_dataset.py        # Etapa 1 — parsing + dedup entre arquivos + log
│   ├── reduce_schema.py        # Etapa 2 — remove 11 colunas → CSV de 9 colunas
│   ├── map_taxonomy.py         # Etapa 3 — deriva unidade + categoria
│   └── taxonomy/               # tabelas de/para versionadas (curadas à mão)
│       ├── __init__.py
│       ├── unidades.py         # empresa → unidade  (+ NORMALIZE_EMPRESA)
│       └── categorias.py       # produto → categoria (cascata) + SHELF_LIFE_DIAS
└── output/                      # gerado ao rodar os scripts — não versionado (.gitignore)
    ├── contas_a_receber.csv               # Etapa 1 (20 colunas)
    ├── processamento_log.json
    ├── contas_a_receber_sem_colunas.csv   # Etapa 2 (9 colunas)
    └── contas_a_receber_taxonomia.csv     # Etapa 3 (11 colunas) — entrada de prepare_daily_series
```

`training_scripts/output/` é `.gitignore` (dado gerado). Quando a Fase 1 do plano de
experimentos fechar a forma final, a lógica migra para `backend/domain/etl/` (Fase 5),
com as validações de qualidade que faltam hoje. A antiga Etapa 3 de one-hot
(`discretize_fields.py`, `contas_a_receber_discretizado.csv`, `encodings.py`) foi removida
em 2026-08-30 — está no histórico do git se precisar como referência (ADR-010).
