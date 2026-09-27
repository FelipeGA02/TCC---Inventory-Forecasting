# Plano de Pré-processamento dos Dados

Documenta o pipeline em [`ia-predictor/training_scripts/preprocessing/`](../../ia-predictor/training_scripts/preprocessing/):
como os XLSX brutos de "Contas a Receber" viram a base transacional consolidada, e como
essa base é preparada para alimentar a modelagem: **L1 SARIMAX** da demanda diária por
`unidade` → **L2** desagregação em cascata (`unidade → categoria → SKU`) — ver
[ADR-009](ADR-009-granularidade-diaria-e-reposicao.md) e
[ADR-011](ADR-011-escopo-previsao-sem-reposicao.md) §4.

> Escopo de 2026-08-30 (diário), revisado em 2026-09-21 (granularidade do L1). Reescrito
> por inteiro para o pipeline diário (a versão mensal está no histórico do git). Unidades,
> categorias e escopo definidos com o cliente ([ADR-011](ADR-011-escopo-previsao-sem-reposicao.md)):
> **2 unidades** (Jardim Canadá e Itabirito), **3 categorias de demanda**, e **sem camada
> de reposição L3** — o entregável é a previsão de demanda. O L1 ajusta uma série por
> **unidade** (2 séries); `categoria` é obtida por desagregação, não é mais série L1
> própria ([ADR-011](ADR-011-escopo-previsao-sem-reposicao.md) §4).

> **Revisão de 2026-09-27 — Etapas 4 a 7.** O EDA ([00-eda_report.md](00-eda_report.md) §4) e
> os dois treinos na série crua ([02](02-baseline_serie_crua_pre_eda.md) e
> [03](03-enriquecimento_serie_crua.md)) fecharam os parâmetros que faltavam. O pipeline
> passou a ir além da transação: limpa a base (4), marca as encomendas (5), monta o
> calendário por loja (6) e grava as séries diárias prontas (7). Tudo roda com
> `run_all.py`, que confere a consistência ao final. Ver §6 a §10.

Este documento é deliberadamente verboso no **porquê**: cada decisão de parsing, cada
coluna removida, cada regra de taxonomia e cada valor default está justificado, porque o
pré-processamento é onde a maior parte das escolhas metodológicas do CRISP-DM (compreensão
dos dados → preparação) ficam gravadas em código.

---

## 1. Visão geral

O alvo do modelo L1 é uma **série temporal diária por unidade**: para cada `unidade`, a
soma de `qtdade` vendida **no balcão** por dia (sem as encomendas grandes, ADR-012), de todas
as categorias de produto. `categoria` (e depois SKU) são obtidos por desagregação em
cascata, não por um modelo próprio (ver §5.2). Até 2026-09-21 o pré-processamento parava na
base transacional; desde 2026-09-27 ele também entrega a base limpa, a marcação de
encomendas, o calendário por loja e as **séries diárias prontas** (Etapas 4–7).

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
│ Etapa 3 — map_taxonomy.py                     │  deriva `unidade` (L1), `categoria` e `categoria_fina` (desagregação)
│  → output/contas_a_receber_taxonomia.csv     │  12 colunas
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ Etapa 4 — clean_transactions.py  (§6)         │  sai Servico e taxa · data ISO · números · devolução marcada · grupo · UTF-8
│  → output/contas_a_receber_limpa.csv         │  13 colunas · só demanda de produto
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ Etapa 5 — mark_orders.py  (§7)                │  encomenda = linha > 5 dias típicos (ADR-012)
│  → output/contas_a_receber_encomendas.csv    │  + encomenda, limiar_encomenda, dias_tipicos_linha
│  → output/limiares_encomenda.csv             │  1 limiar por unidade × categoria
└──────────────────────────────────────────────┘
        │                                    ┌──────────────────────────────────────────────┐
        │                                    │ Etapa 6 — build_calendar.py  (§8)             │  por loja: feriados (BrasilAPI), fechamentos
        │                                    │  → output/calendario_diario.csv              │  locais, abertura excepcional, loja_fechada
        ▼                                    └──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│ Etapa 7 — build_daily_series.py  (§9)         │  total · balcão (alvo do L1) · encomenda, dias sem venda = 0
│  → output/serie_diaria_unidade.csv           │  L1: 2 séries
│  → output/serie_diaria_unidade_categoria.csv │  desagregação: 6 séries
└──────────────────────────────────────────────┘
        │
        ▼
   run_all.py  (§10) → output/preprocessamento_relatorio.json   ← conferências de consistência
        │
        ▼
   treino (training_scripts/): série × calendário por `data × unidade`; teto p99 só no treino
```

### Por que entregar uma base transacional, e não a série diária pronta

> **Revisto em 2026-09-27.** O argumento abaixo valia enquanto os parâmetros da série
> estavam em aberto. O EDA e os treinos os fecharam (L1 por unidade, alvo = balcão, dias sem
> venda = 0), e a Etapa 7 passou a gravar as séries. A base transacional continua sendo
> entregue (Etapas 4–5), porque o walk-forward recalcula o limiar de encomenda por janela e
> a desagregação para SKU parte das linhas.

O pré-processamento **para na transação limpa** de propósito. A série diária depende de
parâmetros de modelagem que ainda estão em aberto (qual recorte de `unidade`, se a
categoria X tem histórico suficiente, qual janela de reindexação) e que vão ser decididos
na Fase 1 do plano de experimentos. Se o pipeline já cuspisse a série agregada, cada
ajuste desses parâmetros exigiria reprocessar os 26 XLSX. Mantendo a saída no nível de
transação, `prepare_daily_series()` roda em segundos sobre o CSV e pode ser reexecutado à
vontade durante a experimentação. É a mesma separação parser → normalizer → feature
builder do `backend/domain/etl/` de produção.

### Por que etapas separadas

Cada etapa resolve um problema distinto e tem uma saída inspecionável: extrair uma tabela
de um relatório que não é tabular (1), reduzir ao subconjunto de colunas com sinal (2), e
adicionar as duas dimensões de agrupamento que o L1 precisa e que não existem na origem
(3). Rodar em estágios — em vez de um script monolítico — tem três ganhos concretos:

- **Depuração por diff.** O problema de deduplicação da seção 3 só apareceu porque foi
  possível abrir o CSV intermediário da Etapa 1 e comparar ocorrências linha a linha. Num
  script único, esse estado intermediário nunca existiria em disco.
- **Reexecução barata.** Mexer nas regras de taxonomia (Etapa 3) não obriga a repassar o
  parser sobre os XLSX (Etapa 1, a mais lenta). Cada etapa lê o CSV da anterior.
- **Espelha a produção.** A divisão reproduz o `backend/domain/etl/` (parser → normalizer →
  feature builder), então a migração da lógica para o backend na Fase 5 é quase 1:1.

Cada etapa é um módulo com função pura e bloco `if __name__ == '__main__':`. A partir de
`ia-predictor/`, na ordem:

```bash
python -m training_scripts.preprocessing.run_all              # tudo, na ordem, + relatório (~1–2 min)

# ou etapa por etapa
python -m training_scripts.preprocessing.build_dataset
python -m training_scripts.preprocessing.reduce_schema
python -m training_scripts.preprocessing.map_taxonomy
python -m training_scripts.preprocessing.clean_transactions
python -m training_scripts.preprocessing.mark_orders
python -m training_scripts.preprocessing.build_calendar
python -m training_scripts.preprocessing.build_daily_series
```

Testes das regras das Etapas 4–7 (dados sintéticos, sem internet):
`pytest ia-predictor/tests/unit/test_preprocessing_etapas.py`.

### Por que a saída fica em `training_scripts/output/` e não em `data/processed/`

`data/processed/contas_a_receber.csv` é o CSV **canônico** que o backend consome. Estes
scripts leem os XLSX reais de produção (`data/raw/`, só leitura) mas escrevem num sandbox
de experimentação isolado. Assim, rodar o pipeline durante o desenvolvimento nunca
sobrescreve nem corrompe a base de produção — e o `output/` inteiro está no `.gitignore`
(dado gerado não é versionado; o que se versiona é o código que o reproduz).

### Por que o CSV usa `;` como separador

Os valores monetários e de quantidade são formatados no **padrão brasileiro, com vírgula
decimal** (`format_decimal` em `helpers.py`: `1234.5` → `"1234,5"`). Com vírgula ocupada
pelo decimal, o separador de campo tem de ser outro — `;`, que é também o separador do CSV
de produção. Todas as leituras a jusante passam `sep=';'` e `dtype=str` explicitamente
(ver seção 4).

---

## 2. Etapa 1 — `build_dataset.py`: parsing + deduplicação + log

### Por que existe

O relatório de "Contas a Receber" foi feito para uma pessoa ler, não para um modelo
consumir: é texto em blocos, uma venda por bloco, sem estrutura de tabela. É preciso
transformá-lo numa tabela onde cada linha é uma unidade de análise consistente — aqui,
**1 produto dentro de 1 documento**. Esta é também a única etapa que toca os 26 arquivos
brutos; a deduplicação e o controle de hash vivem aqui porque é a única chance de garantir
que cada venda real apareça exatamente uma vez.

### Por que a granularidade é "1 produto dentro de 1 documento"

É o menor grão que preserva **todas** as informações que a modelagem pode querer somar
depois, sem perder nada por agregação precoce:

- Somar por `(dia, unidade, categoria)` → série L1.
- Somar por `(dia, produto_cod)` → histórico para a desagregação L2.
- Manter `total_liquido_doc` em cada linha → permite reconferir a integridade do documento
  inteiro (o teste do documento `995`, mais abaixo).

Agregar mais cedo (por exemplo, já somando por produto/dia no parser) fecharia portas sem
ganho — o CSV transacional não é grande o bastante para justificar.

### Por que ler por posição de coluna fixa

Cada bloco começa numa linha `Documento: C1 44799`, seguido de linhas de cabeçalho
(Cliente, Empresa, Vendedor, Obs), uma linha `Produto` e N linhas de item até `Totais`. O
`parser.py` varre por **índice de coluna fixo** (`HEADER_COLUMNS`, `DETAIL_COLUMNS`,
`PRODUCT_COLUMNS`, `NET_TOTAL_COLUMN` em `constants.py`) porque:

- O relatório é gerado por um sistema legado com **layout estável** — as mesmas colunas,
  nas mesmas posições, em todos os 26 meses. Não há cabeçalho de tabela para ancorar uma
  detecção dinâmica; a posição *é* o contrato.
- Casar por rótulo de texto seria frágil: os rótulos (`Emissão:`, `Operador:`) aparecem
  concatenados com o valor na mesma célula, e a extração é feita por `parse_field`
  (`"Emissão: 02/01/2024"` → `"02/01/2024"`), que exige saber em qual célula olhar.
- O parser lê o XLSX com `openpyxl` mantendo o **número da coluna** (`values_only=False`,
  `cell_map = {c.column: c.value}`), então a varredura posicional é direta.

### O que o script faz

`parse_xlsx()` expande cada bloco `Documento:` em **um registro por (documento, produto)**.
A máquina de estados é tolerante a folgas do relatório:

- **Linhas em branco entre cabeçalho e `Produto`** são puladas (`if cell_check == ''`).
- **A lista de produtos termina** em `Totais` *ou* numa linha vazia (`_parse_products`).
- **O total líquido do documento** é lido alguns passos após `Totais` (`i += 2`, coluna 5),
  posição empírica do relatório.
- `split_code_name` separa `"2820 - TATIANE"` em `("2820", "TATIANE")` — o relatório
  embute código e nome no mesmo campo, e a modelagem só quer o código.
- `format_decimal` normaliza todo número para string com vírgula decimal; `None` vira
  `"0"` (célula vazia de valor = zero, não faltante).

`build_dataset.py` orquestra as 26 planilhas:

- **Idempotência por hash MD5.** Cada planilha só é (re)processada se for nova ou se o
  conteúdo mudou (`file_hash` vs. `processamento_log.json`). O objetivo é poder rodar o
  script quantas vezes quiser — num pipeline de TCC que evolui em iterações, reprocessar
  tudo a cada rodada seria lento e arriscaria duplicar linhas no CSV `append`-only. O hash
  (e não a data de modificação) porque copiar/mover arquivo mexe no mtime sem mexer no
  conteúdo.
- **Deduplicação por chave composta `(doc_numero, produto_cod, emissao, qtdade,
  vl_total)`**, aplicada **só entre arquivos diferentes**, nunca dentro do mesmo arquivo.
  Existe porque os relatórios mensais têm sobreposição de datas nas bordas do mês. Ver o
  achado abaixo.
- **Recuperação máxima.** Linhas fora do padrão vão para `skipped` (com número de linha e
  motivo) sem interromper a execução. Um relatório não desenhado para máquina sempre tem
  casos de borda; abortar no primeiro perderia os milhares de registros bons do arquivo.
  O que foi pulado fica registrado no log para auditoria.

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

1. **Escopo entre arquivos.** As chaves de um arquivo só entram no conjunto "já visto"
   (`existing_keys`) **depois** que o arquivo inteiro é processado — o loop acumula em
   `keys_found_in_this_file` e faz `existing_keys |= ...` no fim. Assim, duas linhas
   idênticas *no mesmo documento* nunca são comparadas entre si; a dedup só age contra o
   que veio de **outros** arquivos. É exatamente o cenário real: o mesmo documento
   exportado no relatório de março e de novo no de abril, por cair na virada do mês.
2. **Chave endurecida.** `(doc_numero, produto_cod)` → `(doc_numero, produto_cod, emissao,
   qtdade, vl_total)`. Motivo: `doc_numero` **não é único** — o mesmo número se repete
   entre `doc_tipo` diferentes (32.572 casos nos dados reais; `C1 995` e `F3 995` são
   documentos distintos). A chave curta marcaria esses como duplicata e apagaria vendas.
   Exigir data, quantidade e valor idênticos torna uma colisão acidental entre documentos
   não relacionados praticamente impossível, sem deixar passar a duplicata de exportação
   verdadeira (que é, por definição, byte a byte igual).

### Por que a dedup entre arquivos continua no código mesmo com 0 duplicatas hoje

Na rodada atual ela não removeu nada (seção 3). Mantê-la é barato (um `set` de tuplas) e o
cenário que ela cobre — exportação com sobreposição de mês — é uma propriedade do
*processo* de extração da parceira, não dos 26 arquivos específicos. Se um próximo lote de
XLSX vier com a borda sobreposta, o pipeline já está correto sem intervenção.

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

Por que os dois blocos:

- `arquivos_processados` (por hash) responde "este arquivo já entrou, e com qual
  resultado?" — é o que torna a idempotência possível e o que se consulta para saber a
  origem de qualquer linha.
- `historico_execucoes` (por rodada) responde "o que aconteceu em cada vez que rodei o
  script?" — trilha temporal para auditoria.

Juntos dão a rastreabilidade que o Princípio V exige (todo upload registrado) **sem
reprocessar nada** para auditar: o log basta.

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

**Por que `wc -l` superestima.** A diferença (351.991 − 333.019 ≈ 19 mil) não é dado
faltando: é `wc -l` contando **quebras de linha dentro de campos entre aspas** (RFC 4180) —
quase sempre o campo `obs` (`"levar maquininha de cartao \n5 x"`). A contagem correta é a
do `csv.DictReader`, que respeita as aspas. É mais um motivo para remover `obs` na Etapa 2:
além de ser texto livre sem valor preditivo, ele "suja" a leitura ingênua do arquivo.

**Por que 0 duplicatas neste dataset não invalida a lógica.** Ver a subseção "Por que a
dedup entre arquivos continua no código" na seção 2.

---

## 4. Etapa 2 — `reduce_schema.py`: remoção de colunas

### Por que reduzir o schema

O relatório existe para controle financeiro e fiscal, não para série temporal de vendas.
Carrega colunas que são ruído puro para prever demanda, texto livre de alta cardinalidade
que atrapalha a leitura do arquivo, e PII que a constituição proíbe expor (Princípio VI).

**O critério de cada remoção é uma pergunta única:** *essa coluna muda a resposta de
"quanto dessa categoria vai ser vendido amanhã"?* Se não muda — ou se só poderia ajudar
como feature derivada e agregada, nunca no formato cru — ela sai. Reduzir de 20 para 9
colunas também deixa o CSV mais leve e legível para a EDA.

### Por que a leitura é `dtype=str, low_memory=False`

`reduce_schema` (e as etapas seguintes) lê o CSV com **tudo como string**. Se deixasse o
pandas inferir tipos, ele:

- transformaria `produto_cod` como `"00200512"` em `200512` (perde os zeros à esquerda, e o
  código deixa de casar com a taxonomia);
- interpretaria a vírgula decimal errado ou geraria `NaN` em campos mistos;
- mudaria o dtype de uma coluna conforme o *chunk* (daí `low_memory=False`).

A conversão numérica só acontece onde e quando é necessária (ex.: as estatísticas de
volume em `map_taxonomy`, que fazem `str.replace(',', '.')` antes de `to_numeric`).

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
| `operador` | Quem operou o caixa. Atributo operacional interno; não é driver de *demanda* da categoria. No máximo um proxy de turno/loja, já capturado por `unidade` e pelo dia-da-semana. |
| `obs` | Texto livre, cardinalidade quase 1:1 com as linhas, e com quebras de linha embutidas (seção 3). Zero sinal estruturado; só custo de leitura. |
| `icms_ret` | ICMS retido — metadado contábil. `0` na esmagadora maioria das linhas. Não descreve a venda física. |
| `arquivo_origem` | Nome do XLSX de origem — artefato do processamento, redundante com `emissao`. A rastreabilidade de origem já vive no CSV da Etapa 1 e no log. |
| `cliente_nome` | **PII.** Expor nome de cliente na base que alimenta a API violaria o Princípio VI. |
| `produto_nome` | Texto livre com grafias variáveis para o mesmo item. `produto_cod` já identifica o produto de forma unívoca e é a chave da Etapa 3 e da L2. O nome ainda é usado **uma vez** — na Etapa 3, via lookup a partir do CSV da Etapa 1 — para casar as regras de categoria; depois disso não serve mais. |
| `doc_tipo` | Código interno de tipo de documento (`C1`, `C7`, `F3`, `NN`…). Não é dimensão de negócio com valor preditivo sobre volume. |
| `doc_numero` | Id do documento. **Necessário na dedup da Etapa 1, que roda antes desta.** Daqui pra frente é só um identificador — sem magnitude, sem ordem temporal útil, cardinalidade altíssima. A ligação linha↔documento fica preservada no CSV da Etapa 1. |
| `cliente_cod` | Id de cliente, cardinalidade altíssima. Como feature crua explodiria a dimensionalidade sem sinal de demanda agregada. Se segmentação por cliente for útil um dia, entra como feature **derivada e agregada** (ex.: % de vendas B2B no dia), não o id. |
| `pagamento` | **ADR-010.** Três razões independentes: (1) é atributo de *transação*, nível de agregação errado para uma série diária de categoria; (2) **não é conhecível para os dias futuros** que o modelo prevê — usá-lo seria *data leakage*; (3) é *consequência* da venda (como o cliente pagou), não *driver* dela. Fica no CSV da Etapa 1 para a triagem de importância na EDA. |
| `vendedor` | **ADR-010.** Mesma natureza de `pagamento`. "Vendedor X vende mais" mede desempenho de equipe, não *demanda* da categoria; e o mix de vendedores de um dia futuro é desconhecido. Se houver sinal, vira feature derivada agregada (ex.: `n_vendedores_ativos_no_dia`). |

**Colunas mantidas** (9), e para quê cada uma serve adiante:

| Coluna | Papel a jusante |
| --- | --- |
| `emissao` | **Eixo temporal** da série diária. |
| `empresa` | Entra na Etapa 3 para derivar `unidade`. É **chave de agrupamento** do L1, não uma exógena — por isso não sai junto com `pagamento`/`vendedor`. |
| `produto_cod` | Entra na Etapa 3 para derivar `categoria`; e é a chave da desagregação L2. |
| `qtdade` | **Variável alvo** — somada por dia por `unidade` (L1) e por `unidade × categoria` (desagregação). |
| `vl_unit`, `vl_total`, `vl_desconto`, `tot_liq` | Matéria-prima de features de preço/desconto, avaliadas na Fase 3 do plano de experimentos (não obrigatórias no L1 baseline). Mantidas agora para não ter de reprocessar depois. |
| `total_liquido_doc` | Reconferência de integridade — o teste do documento `995` (seção 2) depende dele; útil também para validar futuras mudanças no parser. |

---

## 5. Etapa 3 — `map_taxonomy.py`: derivar `unidade`, `categoria` e `categoria_fina`

O modelo L1 agrupa por `unidade`; a desagregação (L2) usa `categoria` como passo
intermediário. **Nenhuma coluna de agrupamento existe na base transacional** — a origem só
tem `empresa`, `produto_cod` e `produto_nome`. Derivá-las
é o principal trabalho novo do pré-processamento no escopo diário, e é uma decisão
metodológica: define *quantos* modelos L1 existem e *o que* cada um agrega.

> **Definições com o cliente — ver [ADR-011](ADR-011-escopo-previsao-sem-reposicao.md):**
>
> 1. **A rede tem 2 unidades** — Jardim Canadá e Itabirito — e cada uma é modelada
>    separadamente. As 3 empresas (CNPJ) do relatório viram 2 unidades porque as vendas do
>    Garden Center pertencem a Jardim Canadá. `unidades.py` está **fechado**.
> 2. **O modelo L1 usa 3 categorias de demanda** — `Grama`, `Flores de corte`,
>    `Produtos de jardim` — mais o rótulo `Servico e taxa` (não é produto). O cliente
>    organiza o catálogo em Grama, Flores de corte (as que compõem arranjos e buquês) e
>    Plantas diversas (todas as plantas, exceto flores de corte e árvores), além de
>    insumos e acessórios de jardinagem. Plantas e insumos formam `Produtos de jardim` no
>    L1: a EDA de granularidade ([relatório §3.10](00-eda_report.md)) mostra que modelar
>    Plantas diversas e Insumos e acessórios em separado não erra menos do que repartir a
>    previsão de `Produtos de jardim`. Os grupos do cliente aparecem na apresentação, via
>    `categoria_fina` e L2 (`GRUPO_PRODUTO`), e não como séries L1.
> 3. **A recomendação de reposição (camada L3) saiu de escopo.** O entregável é a
>    **previsão de demanda diária** por 14 dias; a loja decide a compra. Logo
>    `shelf_life_dias` foi **removido** do pré-processamento.

`map_taxonomy.py` lê o CSV reduzido da Etapa 2 (9 colunas) e adiciona **três** colunas:

- **`unidade`** — de `empresa`.
- **`categoria`** — o nível L1 do modelo (3 de demanda + `Servico e taxa`).
- **`categoria_fina`** — a classificação detalhada (~10 rótulos). Fica no CSV para a EDA e
  para a desagregação L2 (que vai da categoria ao SKU e precisa de um agrupamento mais
  fino do que 3 baldes). É a `categoria` fina colapsada em L1 pelo mapa `CATEGORIA_L1`.

Como `produto_nome` foi removido na Etapa 2, ele reconstrói um lookup
`produto_cod → produto_nome` **a partir do CSV da Etapa 1** (`_load_nome_lookup`), que
ainda tem a coluna. O lookup faz `drop_duplicates('produto_cod')` — se o mesmo código
aparece com grafias diferentes de nome ao longo dos meses, fica a **primeira** ocorrência.
Limitação conhecida: se uma grafia posterior casaria uma regra que a primeira não casa, o
SKU vai para `"Outros"` (que colapsa em `Produtos de jardim`) — por isso os SKUs de maior
volume nessa situação entram no `CATEGORIA_POR_SKU` explícito, que independe do nome.

### 5.1 `unidade` — a partir de `empresa` (fechado)

`empresa` tem 3 valores, um por CNPJ, mas a rede tem 2 unidades. **Confirmado com o
cliente**: as vendas do Garden Center pertencem a Jardim Canadá; Jardim Canadá e Itabirito
são modeladas separadamente. De/para em `taxonomy/unidades.py`:

| `empresa` | `unidade` | linhas |
| --- | --- | --- |
| `FLORICULTURA VERDE PERTO CANADÁ LTDA` | `Jardim Canadá` | 168.063 |
| `GARDEN CENTER VERDE PERTO LTDA` | `Jardim Canadá` | 29.408 |
| `VERDE PERTO JARDINAGEM LTDA` | `Itabirito` | 135.548 |

`Jardim Canadá` soma, portanto, 197.471 linhas: a série diária da unidade é a soma das
vendas dos dois CNPJs (o Garden Center só registra vendas a partir de 13/02/2025).

Detalhes de implementação:

- **`NORMALIZE_EMPRESA`** corrige o mojibake `CANAD�` → `CANADÁ` (encoding trocado no
  acento em exportações anteriores). Aplicado *antes* do de/para; sem isso a linha cairia
  no default e a unidade inteira sumiria. Não custa nada quando o dado vem correto.
- **`UNIDADE_DEFAULT = "Desconhecida"`** para `empresa` nula/inesperada — falha visível
  (aparece nas contagens), não silenciosa.

### 5.2 `categoria` — desagregação, não série L1

#### Por que o L1 é só `unidade`, com categoria e SKU por desagregação

Prever "cada SKU" **não quer dizer treinar um modelo de série temporal por SKU** — e não
daria: são ~5.100 SKUs em ~650 dias, e a série diária de um SKU típico é quase toda zero
(`0,0,0,2,0,0,0,0,1,0,…`). SARIMAX precisa de uma série **densa e contínua** para estimar
tendência, autocorrelação e sazonalidade; numa série 90%+ zerada ele não converge, a
variância explode e não há padrão semanal estável para capturar. A maioria dos SKUs
cairia em `insufficient_data`.

O sinal que interessa vive no **agregado**: "fim de semana vende mais", pico no Dia das
Mães e em Finados, tendência — são propriedades da demanda que aparecem melhor quanto mais
se agrega. Mas agregar não precisa parar em `categoria`: o teste de separação
(`eda_separacao.py`, ver [ADR-011 §4](ADR-011-escopo-previsao-sem-reposicao.md)) mostrou
que agregar até `unidade` — sem abrir por categoria — já captura o sinal, e abrir mais uma
vez em categoria não reduz o erro de previsão (nenhuma das 6 séries ganha o mínimo de 5% de
MASE ao ser modelada direto). Por isso o L1 ajusta **2 modelos** — um por unidade, somando
todas as categorias —, cada um com muito dado, em vez de 6 modelos mais finos sem ganho de
acurácia.

**Como a categoria e o SKU continuam sendo previstos — a camada L2, em cascata:**

```text
previsão da categoria = previsão da unidade (L1)  ×  participação da categoria na unidade
previsão do SKU        = previsão da categoria     ×  participação do SKU na categoria
```

A L2 reparte a previsão de cada nível para o nível abaixo pela **participação móvel** (share
das últimas 4–8 semanas) × o **perfil de dia-da-semana do nível** — o mesmo método aplicado
duas vezes: primeiro de `unidade` para `categoria`, depois de `categoria` para SKU. Nenhum
dos dois níveis precisa de um modelo temporal próprio — precisam só de uma estimativa
**estável de proporção** ("Flores de corte é ~1,4% de Jardim Canadá"; "este vaso é ~3% de
`Produtos de jardim` nesta unidade"), que até uma série esparsa fornece se tiver vendas
suficientes no total. Categoria ou SKU com histórico curto demais (< 28 dias com venda ou
< 8 vendas, no caso do SKU) cai no rateio uniforme do nível acima.

É **empréstimo de força** (*borrowing strength*), agora em dois passos: a série `unidade`
carrega a **dinâmica temporal** (quando vende), e cada passo de desagregação carrega o
**mix** do nível abaixo (o que vende) — previsão hierárquica top-down, técnica padrão. É
também o motivo de a Etapa 3 manter `categoria` e `categoria_fina` no CSV mesmo sem série L1
própria: a L2 desagrega em três passos (`unidade` → 3 categorias → ~10 finas → SKU), o que
dá uma estimativa de share menos ruidosa do que pular direto de `unidade` para SKU.

**Por que a desagregação por categoria precisa do efeito de data *da categoria*, não só da
proporção histórica.** A série `unidade` dilui sinais de categorias pequenas: em Jardim
Canadá, a série da unidade **cai** 0,66× no Dia das Mães (`00-eda_report.md` §3.0), mas
isso esconde Flores de corte **disparando** 2,14× nessa mesma data (§3.4) — o pico só não
aparece no agregado porque Flores de corte é 1,4% do volume da unidade e Grama/Produtos de
jardim (que caem no Dia das Mães) dominam a média. Repartir a previsão da unidade só pela
proporção histórica perderia esse pico; por isso a desagregação usa também o índice de
data-por-categoria (bloco `4b_datas_comemorativas` de `eda_series.py`, por par), não só o
share médio.

**Exemplo prático — dia comum.** Sexta-feira em Jardim Canadá, sem data comemorativa por
perto:

1. **L1 prevê a unidade.** SARIMAX prevê 380 unidades vendidas na unidade nesse dia (soma
   de Grama, Flores de corte e Produtos de jardim).
2. **`unidade → categoria`.** Flores de corte tem participação móvel de ~1,4% do volume de
   Jardim Canadá (share das últimas 4–8 semanas); sexta é o pico semanal da categoria, então
   o perfil de dia-da-semana pesa um pouco acima da média do nível. Previsão de Flores de
   corte nessa sexta ≈ `380 × 1,4% × perfil do dia` ≈ 8–9 unidades (o restante do total é
   repartido entre Grama e Produtos de jardim).
3. **`categoria → SKU`.** Dentro de Flores de corte, "Rosa vermelha maço" tem participação
   móvel de ~12% dos SKUs da categoria na unidade. Previsão do SKU ≈ `8,5 × 12%` ≈ 1 unidade
   nessa sexta.

**Exemplo prático — data comemorativa (por que a % sozinha erraria).** Na véspera do Dia
das Mães:

- A **unidade inteira cai** para 0,66× o normal (Grama e Produtos de jardim vendem menos
  perto da data) — L1 prevê, digamos, 250 unidades em vez de 380.
- Se a desagregação usasse só a participação histórica (1,4%), Flores de corte cairia
  junto com o total: `250 × 1,4%` ≈ 3,5 unidades.
- Mas Flores de corte **dispara 2,14×** nessa data especificamente (é o produto mais
  comprado pra presentear) — o índice de data-por-categoria captura isso mesmo com o
  agregado da unidade caindo: `8,5 (baseline) × 2,14` ≈ 11 unidades, mais que o dobro do
  dia comum, apesar do total da unidade ser menor.

Isso ilustra por que a desagregação usa participação móvel **e** perfil de dia-da-semana
**e** (no passo `unidade → categoria`) o índice de data comemorativa da própria categoria —
a % de participação é um dos multiplicadores do rateio, não o único, e sozinha perderia
picos que o agregado da unidade esconde.

**Limitação** (e por que existe a comparação acadêmica): o top-down assume que os SKUs de
uma categoria se movem juntos, e que as categorias de uma unidade se movem juntas. Um SKU
com timing próprio (uma flor específica só no Namorados) o método puro erra. Por isso o TCC
compara, nos mesmos splits de walk-forward, o **SARIMAX hierárquico (L1+L2)** contra
**Croston/TSB/SBA por SKU** — métodos feitos para demanda intermitente — para medir qual
ganha (ADR-009).

#### Referências de literatura — por que agregar, e como desagregar

A decisão acima ("SKU isolado não sustenta SARIMAX, agregar até `unidade` sim") não é só
uma leitura visual do gráfico de esparsidade — é o resultado esperado pelo critério padrão
da área para classificar séries de demanda, aplicado aos nossos dados:

**O que são SES, ARIMA/SARIMAX e Croston.** Os três são famílias de método de previsão de
série temporal, do mais simples ao mais específico:

- **SES** (*Simple Exponential Smoothing*, suavização exponencial simples) — a previsão do
  próximo dia é uma média dos dias passados que dá peso cada vez menor a quem é mais
  antigo. Não usa sazonalidade nem tendência; é o piso da família.
- **ARIMA** (*AutoRegressive Integrated Moving Average*) generaliza o SES: modela quanto o
  valor de hoje se explica pelos valores e erros de previsão de dias anteriores (a parte
  "autorregressiva"), e pode diferenciar a série para remover tendência (a parte
  "integrada"). **SARIMAX** — o modelo deste projeto — é o ARIMA com dois acréscimos: um
  componente **sazonal** (o "S", aqui `m=7`, o ciclo semanal) e **exógenas** (o "X": dia da
  semana, feriado, proximidade de data comemorativa).
- **Croston (1972)** — pensado para série com muitos dias de venda zero, onde SES e ARIMA
  se confundem: como eles suavizam a série bruta, ficam "no meio do caminho" entre acertar
  o dia de venda e acertar o zero, errando os dois. Croston separa a série em duas —
  **quanto** vende quando vende, e **de quanto em quanto tempo** vende — suaviza cada uma
  com SES separadamente, e divide uma pela outra para estimar a demanda média por dia.

**Como a literatura decide qual usar — a classificação de Syntetos, Boylan & Croston
(2005).** O artigo deriva, a partir do erro quadrático médio de SES e do método de
Croston, dois cortes numéricos que separam quatro padrões de demanda:

- **ADI** (*average inter-demand interval*, intervalo médio entre vendas) =
  (dias do período) ÷ (dias com venda). ADI = 3, por exemplo, quer dizer "em média, uma
  venda a cada 3 dias".
- **CV²** (coeficiente de variação ao quadrado) = (desvio-padrão do tamanho da venda ÷
  média do tamanho da venda)², calculado **só nos dias em que houve venda**. CV² alto
  quer dizer que o tamanho do pedido varia muito de uma venda para outra (um dia vende 2,
  outro vende 200).

Com ADI < 1,32 e CV² < 0,49 a série é **suave** (venda quase todo dia, tamanho estável —
SES/SARIMAX bastam); ADI < 1,32 e CV² ≥ 0,49 é **errática** (venda quase todo dia, mas
tamanho instável — SARIMAX ainda serve, com suavização como o `log1p`); ADI ≥ 1,32 e
CV² < 0,49 é **intermitente** (vende pouco, mas quando vende é sempre uma quantidade
parecida); ADI ≥ 1,32 e CV² ≥ 0,49 é **lumpy** — o pior caso, vende pouco **e** em
quantidade imprevisível quando vende. Para os dois últimos quadrantes (ADI alto) o artigo
mostra que Croston erra menos que SES/ARIMA — é exatamente aí que entram TSB e SBA
(variações do método de Croston explicadas mais abaixo).

Aplicamos o critério (script `training_scripts/eda/eda_classificacao_sku.py`,
`00-eda_report.md` gráfico `24_classificacao_demanda_sku.png`) aos 5.162 produtos físicos
da base (exclui `Servico e taxa`),
usando o próprio período de venda de cada SKU (do 1º ao último dia com venda). 692 SKUs
(13,4%) venderam em um único dia — CV² indefinido, não classificável. Dos 4.470 restantes:

| Classe | % dos SKUs | % do volume |
| --- | --- | --- |
| Suave | 0,2% | 0,0% |
| Errático | 0,5% | 53,7% |
| Intermitente | 52,2% | 1,4% |
| **Lumpy** | **47,1%** | **44,9%** |

**99,3% dos SKUs classificáveis caem em intermitente ou lumpy** — o par de quadrantes em
que a própria literatura desaconselha SES/ARIMA em favor de Croston/TSB/SBA. É a mesma
conclusão a que o projeto já tinha chegado olhando dias ativos e % de fallback L2 (§5.2
acima), agora obtida pelo instrumento de diagnóstico padrão da área, não por um limiar
específico deste projeto. Aplicando o **mesmo** critério às **2 séries `unidade`** que o L1
de fato ajusta (span do 1º ao último dia com venda da unidade): Jardim Canadá (ADI 1,21,
CV² 0,67) e Itabirito (ADI 1,21, CV² 4,58) caem as duas em **errática** — vendem quase todo
dia útil, mas em quantidade muito variável, dados os pedidos grandes das seções 3.2/3.7 do
relatório de EDA —, exatamente o quadrante em que SARIMAX (com `log1p` para estabilizar o
CV² alto) é apropriado. As 6 séries de desagregação `unidade × categoria` também caem todas
em errática (ADI 1,21–1,23; CV² 0,92–16,2), então subir de categoria para unidade não muda
o quadrante — reforça o que o teste de separação (ADR-011 §4) já mostrava por outro
caminho: agregar até `unidade` já move a série do quadrante errado (SKU) para o quadrante
certo, e agregar mais um nível (categoria) não muda nada.

**Por que agregar e desagregar em vez de modelar cada SKU** (arquitetura hierárquica
top-down, e a escolha do nível de agregação):

- Fliedner, G. (2001). "Hierarchical forecasting: issues and use guidelines." *Industrial
  Management & Data Systems*, 101(1), 5–12. https://doi.org/10.1108/02635570110365952 —
  contrapõe *top-down* (prevê o agregado, desagrega por proporção histórica — o que a L2
  faz) a *bottom-up* (prevê cada série da base e soma); *top-down* exige um único modelo
  bem alimentado por dado, ao custo de perder a dinâmica própria de cada parte — o
  trade-off explícito na seção "Limitação" acima.
- Zotteri, G.; Kalchschmidt, M. (2007). "A model for selecting the appropriate level of
  aggregation in forecasting processes." *International Journal of Production Economics*,
  108(1–2), 74–83. — modela o erro de previsão como troca entre erro de especificação
  (agregado demais, perde padrão) e erro de amostragem (agregado de menos, dado
  insuficiente); com poucas observações por série — nosso caso, 26 meses — a agregação
  reduz mais erro de amostragem do que introduz de especificação, o que empiricamente
  favorece `unidade × categoria` sobre SKU aqui.
- Gross, C.W.; Sohl, J.E. (1990). "Disaggregation methods to expedite product line
  forecasting." *Journal of Forecasting*, 9(3), 233–254. — avalia 21 esquemas de
  desagregação por proporção e conclui que a **proporção média histórica** (a série
  desagregada como fração média do agregado ao longo do tempo) é o método mais simples e,
  ao mesmo tempo, um dos mais precisos — o fundamento acadêmico da participação móvel da L2
  (§5.2 acima), aqui com janela móvel de 4–8 semanas em vez de média de todo o histórico,
  por causa da instabilidade de share documentada na EDA (`00-eda_report.md` §3.9).
- Huber, J.; Gossmann, A.; Stuckenschmidt, H. (2017). "Cluster-based hierarchical demand
  forecasting for perishable goods." *Expert Systems with Applications*, 76, 140–151.
  https://doi.org/10.1016/j.eswa.2017.01.022 — aplicação mais próxima do nosso domínio:
  um varejista de produtos perecíveis (padaria industrial) com séries de venda por item
  esparsas demais para prever direto monta uma hierarquia (item → cluster → loja) e prevê
  nos níveis agregados, com o mesmo racional de "o sinal está no agregado, o item herda a
  proporção".
- Babai, M.Z.; Boylan, J.E.; Rostami-Tabar, B. (2022). "Demand forecasting in supply
  chains: a review of aggregation and hierarchical approaches." *International Journal of
  Production Research*, 60(1), 324–348. — revisão que organiza esse campo (agregação
  temporal, cruzada e hierárquica) e serve de referência guarda-chuva para a arquitetura
  L1→L2 como um todo.

**Croston/TSB/SBA — a trilha de comparação no nível de SKU** (citados por nome desde o
`CLAUDE.md`, aqui com a referência completa):

- Croston, J.D. (1972). "Forecasting and Stock Control for Intermittent Demands." *Journal
  of the Operational Research Society*, 23(3), 289–303.
  https://doi.org/10.1057/jors.1972.50 — o método original, explicado acima.
- Syntetos, A.A.; Boylan, J.E. (2005). "The accuracy of intermittent demand estimates."
  *International Journal of Forecasting*, 21(2), 303–314.
  https://doi.org/10.1016/j.ijforecast.2004.10.001 — mostra que o método de Croston
  superestima a demanda sistematicamente (15–20%) e propõe a correção **SBA**
  (multiplicar por `1 - α/2`).
- Teunter, R.H.; Syntetos, A.A.; Babai, M.Z. (2011). "Intermittent demand: Linking
  forecasting to inventory obsolescence." *European Journal of Operational Research*,
  214(3), 606–615. — propõe **TSB**: atualiza a probabilidade de venda a cada período (em
  vez do intervalo), o que faz a previsão decair mais rápido quando a venda para de
  acontecer — mais adequado a SKU que pode sair de linha, o que a cauda de "Outros"
  (§5.2) sugere ser comum aqui.

#### Como o dado se parece

A amostra dos produtos de maior volume mostrou que a
**Verde Perto opera como garden center / jardinagem, não como floricultura de flor de
corte**: o carro-chefe é **grama plantada** (esmeralda, são carlos, amendoim), seguida de
mudas em saquinho/sacola/cuia, plantas em vaso (`PT NN`), terra/adubo/argila e insumos de
jardim. Flor de corte (`ROSA EM CABO`, `ALSTROEMERIA`) é fatia pequena (~1,7%).

**`categoria_fina` — a cascata detalhada** (`map_categoria()` em `taxonomy/categorias.py`),
**primeira que casar vence**:

1. **`CATEGORIA_POR_SKU`** — de/para explícito por `produto_cod`. Fonte mais confiável
   (curadoria manual), vem primeiro. **Semeado em 2026-08-30** com ~34 SKUs de alto
   volume da cauda de `"Outros"` que as regras não classificam bem (nome só com a espécie,
   sem formato) ou classificariam errado — frutíferas cítricas envasadas (`LARANJA BAHIA`,
   `LIMÃO THAITI`…), folhagens (`FILODENDRO ONDULATO`), touceiras (`MOREIA`). Provisório
   até a curadoria da parceira, mas cada entrada tem comentário com o nome do produto.
2. **`CATEGORIA_REGRAS`** — lista ordenada de `(regex sobre produto_nome, categoria_fina)`.
   **A ordem importa** e segue um princípio de duas camadas: **sinais de formato/recipiente
   primeiro (fortes — dizem *como* o produto é vendido), fallback por espécie/tipo botânico
   depois (fracos — só o nome)**. Assim `IXORA PT 13` cai em `Planta em vaso` (o código de
   vaso vence), enquanto `BUXINHO 20 CM` (sem recipiente no nome) cai no fallback
   `Arbusto e planta formada`. Decisões de ordem:
   - `Servico e taxa` **antes de tudo** — `FRETE`, `TAXA DE …`, `PRESTAÇÃO DE SERVIÇO` não
     são produto físico; rótulo próprio para serem **excluídos da série de demanda**.
   - `Flor de corte e arranjo` no topo das categorias de produto (inclui `MOLIO`/`MOLHO`,
     venda em maço de hastes). Flor de corte é a que compõe arranjos e buquês:
     `GERBERA PT 15`, `CRISANTEMO VB` e `COROA DE CRISTO` são plantas envasadas e seguem a
     cascata (`GERBERA`/`CRISANTEMO` só entram aqui sem sinal de embalagem no nome; a
     `COROA` que vale é a de flores, de funeral).
   - `Hortalica e erva`, `Substrato e adubo`, `Insumo e acessório` **antes das plantas
     ornamentais vivas**: `"TERRA PARA ROSAS"` deve virar substrato, não flor.
   - `GRAMA PRETA` / `PELO DE URSO` **antes** de `\bGRAMA\b`: são forração (Ophiopogon),
     não grama de plantio.
   - Faixa de altura no nome (`0,20 A 0,30CM`, `0,80 A 1,20MT`) → `Arbusto e planta formada`.
   - `PT\s?\d{1,2}` ou `VB` (vaso de barro), depois código/volume de pote (`P14`, `3L`,
     `POTE PP`) → `Planta em vaso`. Vasos vazios (`VASO BIG`, `VASO TRANCADO`, cachepô) já
     foram para `Insumo e acessório` antes, na regra de acessórios.
   - `SAQ*`, `SACOLA`, `CUIA`, `BANDEJA`, `C21`, `CAPIM` → `Muda e forração`.
   - Só então o **fallback por espécie**: `BUXINHO|MURTA|IXORA|CALIANDRA|BAMBU|…` →
     `Arbusto e planta formada`; `BROMÉLIA|ORQUÍDEA` → `Planta em vaso`.
   - **Correções de regex** na mesma passada: `\b(...|SAQ|...)\b` não casava `"SAQUINHO"`
     (sem fronteira de palavra depois de `SAQ`) — virou `SAQ\w*`; o mesmo padrão travava
     `HORTALICAS` (plural), `ARGILA EXPANDIDA` e `PRESTAÇÃO DE SERVIÇO`.
3. **`CATEGORIA_DEFAULT = "Outros"`** — SKU sem match. Não é descarte. Após o refino de
   2026-08-30, `"Outros"` caiu de 9,6% → **1,3%** do volume; o resíduo é uma cauda longa
   de espécies sem palavra-chave estrutural. Colapsa em `Produtos de jardim`.

**`categoria` — o colapso de desagregação** (`CATEGORIA_L1` + `map_categoria_l1()` — nome
mantido por compatibilidade, embora `categoria` não seja mais série L1):

| `categoria_fina` | → `categoria` (nível de desagregação) |
| --- | --- |
| `Grama` | **Grama** |
| `Flor de corte e arranjo` | **Flores de corte** |
| `Hortalica e erva`, `Muda e forracao`, `Planta em vaso`, `Arbusto e planta formada`, `Substrato e adubo`, `Insumo e acessorio`, `Outros` | **Produtos de jardim** |
| `Servico e taxa` | `Servico e taxa` (não-produto — excluído de qualquer série de demanda) |

Por que **3** e não as ~10: `Grama` e `Flores de corte` têm dinâmica própria (efeito de
datas comemorativas de sinal oposto, perfil semanal distinto) — mas isso justifica um
passo de desagregação com perfil próprio para cada uma, não um SARIMAX próprio: o teste de
separação (`00-eda_report.md` [§3.11](00-eda_report.md)) mostra que nenhuma categoria ganha
o mínimo de acurácia exigido ao ser modelada direto (ADR-011 §4). Plantas e insumos são o
par de grupos mais próximo dentro de `Produtos de jardim`, e modelar cada um direto também
não erra menos do que repartir (EDA de granularidade, [relatório §3.10](00-eda_report.md)).
Manter a `categoria_fina` no CSV preserva a opção de subdividir depois (na EDA ou na L2)
sem reprocessar. Não há mais `shelf_life_dias` — a camada L3 saiu de escopo (ADR-011); o
que a categoria alimenta agora é o passo de desagregação `unidade → categoria` (§5.2), não
uma série de demanda própria.

#### Grupos de produto do cliente (apresentação)

O cliente organiza o catálogo em grupos próprios. Eles são funções puras da
`categoria_fina` (`GRUPO_PRODUTO` / `map_grupo()` em `taxonomy/categorias.py`), por isso
não viram coluna do CSV nem série L1 — a previsão de um grupo é a soma da previsão dos
SKUs dele (L2):

| Grupo do cliente | `categoria_fina` | `categoria` (desagregação) |
| --- | --- | --- |
| **Grama** | `Grama` | Grama |
| **Flores de corte** — as que compõem arranjos e buquês (inclui os arranjos montados) | `Flor de corte e arranjo` | Flores de corte |
| **Plantas diversas** — todas as plantas, exceto flores de corte e árvores | `Hortalica e erva`, `Muda e forracao`, `Planta em vaso`, `Arbusto e planta formada`, `Outros` | Produtos de jardim |
| **Insumos e acessórios** — substrato, adubo, vasos, seixos, ferramentas | `Substrato e adubo`, `Insumo e acessorio` | Produtos de jardim |

Limitações: **árvores** não têm regra própria (a lista do grupo no sistema do cliente não
está disponível) e ficam em `Plantas diversas` — estimativa por palavra-chave: 0,4% (Jardim
Canadá) a 1,2% (Itabirito) do volume da unidade; e o rótulo `Insumos e acessórios` é
provisório até o cliente confirmar o nome do grupo (§5.5).

### 5.3 Execução real (2026-09-21)

```text
[map_taxonomy] 333.019 linhas x 12 colunas
[map_taxonomy] Linhas por unidade:
  Jardim Canadá  197.471 | Itabirito  135.548
[map_taxonomy] Volume (qtdade) por categoria L1:
  Produtos de jardim        2.034.205
  Grama                     1.837.995
  Flores de corte              68.526
  Servico e taxa                5.860
[map_taxonomy] Volume (qtdade) por categoria_fina:
  Grama 1.837.995 · Muda e forracao 935.988 · Planta em vaso 383.003 ·
  Substrato e adubo 266.314 · Arbusto e planta formada 177.256 ·
  Insumo e acessorio 141.389 · Hortalica e erva 79.277 ·
  Flor de corte e arranjo 68.526 · Outros 50.979 · Servico e taxa 5.860
[map_taxonomy] Volume (qtdade) por grupo de produto (cliente):
  Grama 1.837.995 · Plantas diversas 1.626.502 · Insumos e acessórios 407.703 ·
  Flores de corte 68.526 · Servico e taxa 5.860
[map_taxonomy] Volume em "Outros" (categoria_fina): 1.3%
[map_taxonomy] Modelos L1 (series por unidade, sem Servico e taxa): 2
[map_taxonomy] Pares unidade x categoria (nivel de desagregacao, informativo): 6
[map_taxonomy] Dias com venda por unidade: min=650, max=653, unidades < 180 dias: 0
[map_taxonomy] Dias com venda por par unidade x categoria (desagregacao): min=641, max=653, pares < 180 dias: 0
```

**Leitura**:

- **2 modelos L1** — uma série por unidade (Jardim Canadá, Itabirito), somando todas as
  categorias. `Servico e taxa` (0,1% do volume) não entra na série de demanda em nenhum
  nível; `categoria` (6 pares, linha "nível de desagregação, informativo") não vira modelo
  próprio — é o primeiro passo da desagregação L2 (§5.2).
- O volume se divide quase meio a meio entre **`Produtos de jardim`** (51,5%) e **`Grama`**
  (46,6%); **`Flores de corte`** é só **1,7%** — série pequena, mas densa o suficiente para
  a desagregação (a EDA confirma). Dentro de `Produtos de jardim`, `Plantas diversas`
  responde por 41,2% do volume total e `Insumos e acessórios` por 10,3%.
- `"Outros"` (na `categoria_fina`) é **1,3%** do volume e some de vista ao colapsar em
  `Produtos de jardim`. A `categoria_fina` fica no CSV para a EDA e a L2.
- **As 2 unidades têm ≥ 180 dias com venda** (mín. 650) — nenhuma cai em
  `insufficient_data`. Jardim Canadá soma os dois CNPJs, então a série da unidade cobre
  todo o período (o Garden Center só entra a partir de 13/02/2025). Os 6 pares de
  desagregação também atendem o mínimo (≥ 641 dias) — nenhum cai no fallback de rateio
  uniforme entre categorias.

As estatísticas — incluindo o diagnóstico de cobertura por par — são impressas pelo
próprio `map_taxonomy.py` (converte `qtdade` vírgula→ponto; `emissao` com `dayfirst=True`),
para que cada rodada entregue o raio-x sem análise externa.

### 5.4 Saída

`output/contas_a_receber_taxonomia.csv` — **12 colunas** (as 9 da Etapa 2 + `unidade` +
`categoria` + `categoria_fina`). É a entrada da Etapa 4. *(Até 2026-09-21 era consumido
direto por `prepare_daily_series()`; desde 2026-09-27 as séries saem prontas da Etapa 7.)*
O `prepare_daily_series()` descrito a seguir é o que a Etapa 7 passou a fazer, em dois
usos: `prepare_daily_series(df, unidade)` — filtra por unidade (ignorando `Servico e
taxa`), soma `qtdade` por dia, reindexa o range diário completo (dias sem venda = 0) e
exige ≥ 180 dias — é a **série-alvo do L1**; e `prepare_daily_series(df, unidade,
categoria)` — o mesmo filtro incluindo `categoria`, usado para construir o perfil de
desagregação (participação móvel × perfil de dia-da-semana da categoria), não para treinar
um modelo próprio.

### 5.5 O que ainda depende do cliente e da EDA

Resolvido (dentro do pré-processamento):

- ✅ `empresa → unidade` **fechado** — 2 unidades (Jardim Canadá e Itabirito), modeladas
  separadas; as vendas do Garden Center são de Jardim Canadá.
- ✅ **Estrutura de categorias fechada** — 3 de demanda (`Grama` · `Flores de corte` ·
  `Produtos de jardim`) + `Servico e taxa`. `shelf_life_dias` removido (L3 fora de escopo).
- ✅ **Grupos do cliente mapeados** — Plantas diversas e Insumos e acessórios saem de
  `categoria_fina` (`GRUPO_PRODUTO`), sem série L1 própria.
- ✅ **Granularidade do L1 fechada** — uma série por `unidade` (2 séries); `categoria` e
  `categoria_fina` são níveis de desagregação, não modelos próprios (ADR-011 §4).
- ✅ `"Outros"` (na `categoria_fina`) em 1,3% do volume.
- ✅ Cobertura de histórico verificada — as 2 unidades têm ≥ 180 dias com venda; os 6 pares
  de desagregação também; o script reporta isso a cada rodada.

Ainda em aberto:

- ✅ **EDA** — feita (2026-09-21), ver **[`docs/prediction/00-eda_report.md`](00-eda_report.md)**.
  Confirmou: as 2 séries do L1 e as 6 séries de desagregação são densas o suficiente
  (81–83% dos dias com venda, zeros quase todos em domingo); **todas recebem `log1p`**
  (CV 1,01–2,39 nas 2 unidades; 1,15–4,49 nos 6 pares); a sazonalidade semanal existe mas é
  **invertida** em relação ao pressuposto do `CLAUDE.md` ("fim de semana vende mais" é
  falso — pico ter–qui / sex, sábado fraco); `Flores de corte` é densa apesar dos 1,7% de
  volume, mas em Jardim Canadá é quase **ruído branco** na parte ARIMA (só calendário
  prevê); separar por categoria não melhora a previsão, separar por unidade sim (§3.11).
  Achados detalhados e ajustes de modelagem na §4 do relatório; a granularidade das
  categorias na §3.10; a granularidade unidade × categoria na §3.11.
- **Cliente** — (a) confirmar os nomes dos grupos de produto (`Insumos e acessórios`) e
  fornecer a lista de produtos do grupo Árvores; (b) curadoria fina de SKUs de alto
  volume em `Outros` (impacto baixo no L1); (c) validar a completude da fonte —
  `fev/2026` fechado?, o relatório captura 100% das saídas?, tratamento de `qtdade`
  negativa (devolução). Lista completa na §5 do relatório.

---

## 6. Etapa 4 — `clean_transactions.py`: base limpa, só demanda de produto

### Por que existe

As Etapas 1–3 extraem e classificam, mas não julgam: a base da Etapa 3 ainda tem frete e
taxa, datas em texto `dd/mm/aaaa`, números em texto com vírgula e acentuação inconsistente
entre execuções (o EDA precisava tentar vários encodings para ler). Cada script de EDA e de
treino repetia essa limpeza por conta própria, com pequenas diferenças. A Etapa 4 faz isso
**uma vez**, com as regras que o EDA e os treinos fecharam.

### O que faz

| Regra | Motivo | Execução real |
| --- | --- | --- |
| Remove `categoria = Servico e taxa` | frete, taxa e mão de obra não são demanda de produto; já era excluída da série antes do EDA (§5) | 5.342 linhas |
| Remove linha sem data válida ou com `unidade` fora das 2 lojas | não há como colocá-la na série | 0 linhas |
| `emissao` → `data` ISO (`aaaa-mm-dd`) | ordena e junta com o calendário sem ambiguidade de formato | — |
| Números viram número (vírgula decimal; vazio = 0) | as Etapas 1–3 leem tudo como texto (§4) | 0 inválidos |
| `devolucao = 1` quando `qtdade < 0` | **as devoluções ficam na base** e entram somadas (venda líquida do dia) até a floricultura dizer como tratá-las (EDA §5, pergunta 4). Volume desprezível | 44 linhas, −481 unidades |
| `grupo` como coluna | vocabulário do cliente para o painel e a desagregação (EDA §4, item 9) | — |
| Grava em UTF-8 | acaba com o problema de acentuação das saídas antigas | — |

Linhas com `qtdade = 0` ficam: não mudam nenhuma soma e registram que o produto passou pelo
caixa.

### Saída

`output/contas_a_receber_limpa.csv` — 327.677 linhas, 13 colunas:
`data; unidade; empresa; categoria; categoria_fina; grupo; produto_cod; qtdade; vl_unit;
vl_total; vl_desconto; tot_liq; devolucao`. Período 2024-01-02 → 2026-02-28.

---

## 7. Etapa 5 — `mark_orders.py`: marcação das encomendas grandes (ADR-012)

### Por que existe

O EDA (§3.12) e os dois treinos mostraram que as **encomendas grandes** (obras e
paisagismo, combinadas com antecedência) são o maior erro de qualquer modelo de série
temporal: em Itabirito elas são 36% do volume, e no ano de teste do treino enriquecido
concentraram 48% do erro em 11% dos dias (doc 03, §4.1). A regra de separação já estava
decidida e implementada em `encomendas.py` (ADR-012); faltava aplicá-la de forma
padronizada e gravar o resultado.

### A regra

Uma linha é encomenda quando `qtdade > K × dia típico` da sua `unidade × categoria`, com
`K = 5` e dia típico = mediana do volume diário em dias com venda, de segunda a sábado.

| Unidade · categoria | Dia típico | Limiar da linha | Linhas de encomenda | % do volume do par |
| --- | --- | --- | --- | --- |
| Itabirito · Grama | 203 | 1.015 | 68 | 67,7% |
| Itabirito · Produtos de jardim | 616 | 3.079 | 8 | 9,1% |
| Itabirito · Flores de corte | 31 | 155 | 4 | 4,2% |
| Jardim Canadá · Grama | 1.403 | 7.014 | 1 | 1,2% |
| Jardim Canadá · Produtos de jardim | 1.653 | 8.265 | 1 | 1,0% |
| Jardim Canadá · Flores de corte | 32 | 160 | 12 | 17,8% |

Resultado por loja, **idêntico ao do EDA/ADR-012**: Itabirito 80 linhas em 58 dias (36,3%
do volume); Jardim Canadá 14 linhas em 9 dias (1,3%). O `run_all` confere isso a cada
execução.

### Por que agora a marca é gravada no CSV (revisão da §12)

A versão anterior deste documento dizia para **não** gravar a marca, porque um limiar
calculado com a base inteira usaria informação do futuro no walk-forward. A marca agora é
gravada, com duas salvaguardas:

- **Semântica de produção.** Ao ajustar o modelo, a produção usa todo o histórico
  disponível, exatamente o que o CSV traz. A marca gravada é a marca que a produção usaria
  hoje.
- **Validação sem vazamento.** Para testes com origem móvel, o limiar é recalculado com o
  passado de cada janela: `marcar(df, data_corte=origem)` nesta etapa, ou
  `limiares_encomenda()` sobre as linhas anteriores à origem. A coluna `qtdade` está na base
  justamente para isso.

O **teto no 99º percentil** (segunda camada do ADR-012) continua **fora** do
pré-processamento: ele só altera a série de treino, nunca a base (`teto_quantil()`).

### Vendas médias (EDA §4, item 17)

Linhas de balcão acima de 1 dia típico, grandes mas abaixo do limiar de encomenda. A etapa só
as mede (relatório), sem mudar a base:

| Loja | Linhas | % do volume de balcão | % do balcão de dez/2025 |
| --- | --- | --- | --- |
| Itabirito | 391 | 23,9% | 12,4% |
| Jardim Canadá | 216 | 14,5% | 12,3% |

São parte relevante do balcão, espalhadas pelo ano, não um fenômeno só de dezembro. O teto
p99 do treino atenua os dias mais extremos; se ainda sobrar erro nesses dias, a opção é
revisar `K`, não criar outra categoria.

### Saídas

- `output/contas_a_receber_encomendas.csv` — a base limpa + `encomenda` (0/1),
  `limiar_encomenda` e `dias_tipicos_linha` (quantos dias típicos a linha vale).
- `output/limiares_encomenda.csv` — a tabela acima.

---

## 8. Etapa 6 — `build_calendar.py`: calendário diário por loja

### Por que existe

O calendário foi a única informação externa que melhorou a previsão (doc 03): com ele, o
erro nos feriados cai de ~4 mil unidades para ~0, a faixa de 95% fica 6 vezes mais estreita
e o erro do ano cai 9%. O clima não trouxe ganho e **fica fora** (EDA §4, item 19). O
calendário precisa ser **por loja**, porque as regras diferem:

- **Só Itabirito abre** no Dia das Mães (domingo) e em Finados (feriado): de 629 a 891
  unidades nesses dias. Jardim Canadá nunca abriu num domingo.
- **Só Itabirito fechou** em 02/01/2025 (Jardim Canadá vendeu 2.394).

### Fontes e regras

| Informação | Fonte / regra |
| --- | --- |
| Feriados nacionais | BrasilAPI, cache em `data/external/` (`dados_externos.py`). Inclui **Carnaval** (ponto facultativo) e **Consciência Negra** (nacional desde 2024) |
| Fechamentos locais | observados nos dados: **15/08 e 08/12 todo ano** (as duas lojas fecharam em 15/08/2024, 15/08/2025 e 08/12/2025) e **02/01/2025 só em Itabirito**. A confirmar com a floricultura (EDA §5, pergunta 10). Em `constants.py` |
| Abertura excepcional | Itabirito no Dia das Mães e em Finados (`constants.py`) |
| **`loja_fechada`** | domingo, feriado nacional ou fechamento local, **exceto** abertura excepcional |
| Datas comemorativas | Dia das Mães (2º domingo de maio), Namorados (12/06), Dia da Mulher (08/03), Pais (2º domingo de agosto), Finados (02/11), Natal (25/12) |

### Colunas

Uma linha por `data × unidade`, de 2024-01-01 a 2026-12-31 (vai além dos dados para cobrir o
horizonte de previsão):

| Coluna | Uso recomendado |
| --- | --- |
| `dia_semana`, `nome_dia` | **L1** (dia da semana foi 83% da importância no doc 03) |
| **`loja_fechada`** | **L1** (feriado/fechamento: 15% da importância; erro nos feriados ≈ 0) |
| **`abertura_excepcional`** | **L1**, junto com `loja_fechada` (corrige o erro do doc 03 §4.3) |
| `feriado_nacional`, `nome_feriado`, `fechamento_local`, `data_comemorativa` | auditoria e gráficos |
| `vespera_feriado`, `pos_feriado`, `inicio_mes` | candidatas; sem efeito no L1 total (doc 03 §3.4) |
| `dias_ate_<data>`, `janela_7d_<data>` | candidatas para a **desagregação por categoria**, onde o efeito das datas muda de sentido (EDA §3.4). No L1, usar só junto com `abertura_excepcional` |

### Conferência com as vendas

No período dos dados, cada loja tem 27 dias úteis de loja fechada. O `run_all` cruza o
calendário com as vendas: **0 dias marcados como fechados tiveram venda, e 0 dias marcados
como abertos ficaram sem venda**. O calendário explica todos os zeros da série.

### Saída

`output/calendario_diario.csv` — 2.192 linhas (1.096 dias × 2 lojas), 25 colunas.

---

## 9. Etapa 7 — `build_daily_series.py`: séries diárias prontas

### Por que existe

Com os parâmetros da série fechados, cada experimento remontava a série do zero, a partir
da transação, com pequenas diferenças entre scripts. A Etapa 7 grava as séries uma vez, com
as três parcelas lado a lado, para o treino escolher o alvo sem reprocessar nada.

### Colunas

| Coluna | Significado |
| --- | --- |
| `qtd_total` | tudo o que saiu no dia (balcão + encomendas, devoluções descontadas) |
| **`qtd_balcao`** | **alvo do L1** (ADR-012): sem as linhas de encomenda |
| `qtd_encomenda` | fluxo sob pedido; não é previsto pelo histórico |
| `qtd_devolucao` | soma das linhas negativas (já incluída em total e balcão), para auditoria |
| `n_linhas`, `n_linhas_encomenda` | contagens do dia |

As duas lojas cobrem o mesmo intervalo (2024-01-02 → 2026-02-28, 789 dias), com todos os
dias do calendário; dia sem venda = 0.

### Execução real

| Loja | Total | Balcão (alvo L1) | Encomendas | Dias com venda | Variação diária (CV) total → balcão |
| --- | --- | --- | --- | --- | --- |
| Itabirito | 1.323.490 | 843.126 | 480.364 (36,3%) | 653 | 2,40 → 1,25 |
| Jardim Canadá | 2.617.236 | 2.582.431 | 34.805 (1,3%) | 650 | 1,02 → 1,00 |

A queda do CV de Itabirito reproduz o ADR-012. As duas lojas passam o mínimo de 180 dias com
venda do L1.

### Saídas

- `output/serie_diaria_unidade.csv` — **L1**: 1.578 linhas (789 dias × 2 lojas).
- `output/serie_diaria_unidade_categoria.csv` — **desagregação** `unidade → categoria`:
  4.734 linhas (789 dias × 6 pares).

A desagregação `categoria → SKU` continua partindo das linhas
(`contas_a_receber_encomendas.csv`, coluna `produto_cod`): uma série por SKU seria enorme
(~5 mil SKUs × 789 dias) e quase toda zero.

### Como o treino usa

```python
serie = pd.read_csv('output/serie_diaria_unidade.csv', sep=';', decimal=',', parse_dates=['data'])
cal = pd.read_csv('output/calendario_diario.csv', sep=';', parse_dates=['data'])
dados = serie.merge(cal, on=['data', 'unidade'])       # série + calendário da mesma loja
y = dados.query("unidade == 'Itabirito'").set_index('data')['qtd_balcao']
# teto p99 (ADR-012): só no treino → encomendas.teto_quantil(y_treino)
# walk-forward: recalcular o limiar de encomenda por janela (mark_orders.marcar(..., data_corte=origem))
```

---

## 10. `run_all.py`: o pipeline inteiro + relatório de qualidade

Roda as 7 etapas em ordem (~1–2 min; a Etapa 1 é incremental e só reprocessa planilhas novas)
e grava `output/preprocessamento_relatorio.json` com o resumo de cada etapa e quatro
conferências. Resultado da execução de 2026-09-27:

| Conferência | Resultado |
| --- | --- |
| Conservação: Σ quantidade da base limpa = Σ séries por loja = Σ séries por categoria; balcão + encomenda = total | ok |
| ADR-012 reproduzido (Itabirito 80 linhas / 36,3%; Jardim Canadá 14 / 1,3%) | ok |
| Calendário × vendas: dia "fechado" com venda / dia "aberto" sem venda | 0 / 0 |
| Mínimo de 180 dias com venda por loja (L1) | ok (653 e 650) |

Se alguma conferência falhar numa base nova (por exemplo, um dia útil sem venda que o
calendário não conhece), é sinal de fechamento local novo ou de problema no dado, e vale
investigar antes de treinar.

---

## 11. O que cada achado do EDA e dos treinos virou

| Achado | Onde foi resolvido |
| --- | --- |
| L1 = 2 séries, uma por loja; Garden Center dentro de Jardim Canadá (EDA §4 item 10) | Etapa 3 (`unidades.py`) + Etapa 7 |
| `Servico e taxa` fora da demanda | Etapa 4 |
| Devoluções (EDA §4 item 11) | Etapa 4: marcadas e mantidas até a resposta da floricultura |
| Grupos do cliente no painel (EDA §4 item 9) | Etapa 4: coluna `grupo` |
| Encomendas fora do L1 (EDA §4 item 12, ADR-012) | Etapa 5 (marca) + Etapa 7 (`qtd_balcao`) |
| Vendas médias abaixo do limiar (EDA §4 item 17) | Etapa 5: medidas no relatório |
| Dia da semana como variável direta (EDA §4 item 4) | Etapa 6: `dia_semana` |
| Carnaval explícito (EDA §4 item 13) | Etapa 6: BrasilAPI já traz |
| Fechamentos locais 15/08 e 08/12 (doc 03, EDA §5 pergunta 10) | Etapa 6: `fechamento_local` |
| Abertura excepcional em Mães/Finados (EDA §4 item 18) | Etapa 6: `abertura_excepcional`, por loja |
| Datas comemorativas por categoria (EDA §4 item 3) | Etapa 6: `dias_ate_*` e `janela_7d_*` para a desagregação |
| Clima fora (EDA §4 item 19) | não entra no pipeline |
| Teto p99 dos picos restantes (EDA §4 item 2, ADR-012) | **treino** (`encomendas.teto_quantil`), nunca na base |
| Limiar de encomenda sem vazamento no walk-forward | **treino** (`marcar(..., data_corte=)`) |
| Métrica comparável, largura do IC, ano inteiro de rodadas (EDA §4 itens 14–15) | **treino** (protocolo do doc 03) |
| Acompanhar mudanças de nível (EDA §4 item 16) | **treino** (configuração do modelo) |

---

## 12. O que este pipeline NÃO resolve (e onde reaparece)

Cada item abaixo foi **deixado de fora de propósito** — ou porque é regra de negócio que
pertence ao backend de produção, ou porque depende de decisões de modelagem ainda abertas.
*(Revisto em 2026-09-27: a limpeza, as séries, o calendário e a marcação de encomendas
passaram a ser feitos pelas Etapas 4–7; os itens abaixo dizem o que ainda sobra.)*

- **Validação de qualidade de dado** — a Etapa 4 aplica as regras já decididas (sem
  serviço/taxa, data e unidade válidas, número válido, devolução marcada). O que falta é a
  **política final de devoluções** (pergunta à floricultura) e a migração dessas regras para
  o `domain/etl/normalizer.py` de produção (`SPECS.md` §4.2, ainda stub), para que exista
  um só lugar com a política de limpeza no sistema.
- **Curadoria fina de `categoria_fina`** — os ~34 SKUs do `CATEGORIA_POR_SKU` são
  provisórios e a cauda de `"Outros"` (1,3%) não foi esgotada. Impacto no L1 é nulo (tudo
  colapsa em `Produtos de jardim`); a curadoria interessa à EDA e à L2. A estrutura de
  `unidade` e de `categoria` L1 já está **fechada** (ADR-011), não é mais pendência.
- **Recomendação de reposição (L3), `shelf_life_dias`, risco de perda/ruptura** — **fora
  de escopo** por decisão da parceira (ADR-011). O entregável é só a previsão de demanda.
- ~~**Construção da série diária**~~ — **feita na Etapa 7** (§9).
- ~~**Exógenas de calendário**~~ — **feitas na Etapa 6** (§8), por loja. O que sobra: a
  confirmação dos fechamentos locais com a floricultura e a migração para
  `domain/features/calendar_exogenous.py` na Fase 5. Clima fica fora (EDA §4 item 19).
- **Features de preço/desconto** a partir de `vl_*` — avaliadas na Fase 3, não no baseline.
  As colunas cruas já ficam no CSV para não reprocessar depois.
- **Desagregação para SKU (L2)** — usa `produto_cod` do CSV da Etapa 3 + histórico; fora
  deste pipeline.
- **Teto de picos** ([ADR-012](ADR-012-encomendas-grandes-fora-do-l1.md) §2) — continua
  fora: só altera a série de treino. *A separação das encomendas passou a ser gravada pela
  Etapa 5 (revisão explicada na §7); o texto a seguir registra o raciocínio original.*
- *(Original, 2026-09-23)* **Separação das encomendas grandes e teto de picos**. O código
  fica em `preprocessing/encomendas.py`, mas é aplicado **ao montar a série**, não gravado
  como coluna no CSV da Etapa 3. O motivo é que o limiar depende do
  período de treino: uma linha é encomenda quando `qtdade` > 5 × a mediana do volume
  diário (seg–sáb) da sua `unidade × categoria`, **calculada só com o treino**. Gravar uma
  marca fixa no CSV, calculada com a base inteira, vazaria informação do futuro para o
  walk-forward. Pelo mesmo motivo, o teto (winsorização no p99 dos dias abertos) só é
  aplicado à série de balcão do treino. Por que isso é necessário: em Itabirito, 80
  linhas (36% do volume, quase todas Grama de obra faturada por boleto) levavam o MASE a
  1,434; separadas, ele cai para 0,796 (`00-eda_report.md` §3.12). A regra usa só
  `qtdade`, `unidade`, `categoria` e `data`, colunas que já saem da Etapa 3, então não é
  preciso manter `cliente_cod` nem `pagamento` no schema reduzido.

---

## 13. Artefatos

```text
ia-predictor/training_scripts/
├── preprocessing/
│   ├── constants.py            # caminhos + layout de colunas do XLSX + COLUMNS_TO_DROP + DUPLICATE_KEY_FIELDS
│   ├── helpers.py              # format_decimal, parse_field, file_hash, load/save_log, load_existing_record_keys...
│   ├── parser.py               # parse_xlsx() — extrai registros do XLSX por posição de coluna fixa
│   ├── build_dataset.py        # Etapa 1 — parsing + dedup entre arquivos + log + idempotência por hash
│   ├── reduce_schema.py        # Etapa 2 — remove 11 colunas → CSV de 9 colunas
│   ├── map_taxonomy.py         # Etapa 3 — deriva unidade (L1) + categoria/categoria_fina (desagregação) + diagnóstico (% "Outros", cobertura ≥180d por unidade e por par)
│   ├── encomendas.py           # funções puras (ADR-012): limiar de encomenda por unidade × categoria, marcação das linhas, teto p99
│   ├── clean_transactions.py   # Etapa 4 — base limpa (sem serviço/taxa, data ISO, números, devolução, grupo, UTF-8)
│   ├── mark_orders.py          # Etapa 5 — marca encomendas (ADR-012) + limiares + vendas médias; `marcar(df, data_corte=)` p/ walk-forward
│   ├── dados_externos.py       # BrasilAPI (feriados, usado na Etapa 6) e Open-Meteo (clima, só no experimento do doc 03); cache em data/external/
│   ├── build_calendar.py       # Etapa 6 — calendário diário por loja (loja_fechada, abertura_excepcional, feriados, datas)
│   ├── build_daily_series.py   # Etapa 7 — séries diárias por unidade (L1) e unidade × categoria (desagregação)
│   ├── run_all.py              # roda as Etapas 1–7 e grava o relatório de qualidade
│   └── taxonomy/               # tabelas de/para versionadas (curadas à mão)
│       ├── __init__.py
│       ├── unidades.py         # empresa → unidade (2 unidades, fechado) (+ NORMALIZE_EMPRESA)
│       └── categorias.py       # produto → categoria_fina (cascata) + CATEGORIA_L1 (3 categorias) + GRUPO_PRODUTO (grupos do cliente)
└── output/                      # gerado ao rodar os scripts — não versionado (.gitignore)
    ├── contas_a_receber.csv               # Etapa 1 (20 colunas)
    ├── processamento_log.json
    ├── contas_a_receber_sem_colunas.csv   # Etapa 2 (9 colunas)
    ├── contas_a_receber_taxonomia.csv     # Etapa 3 (12 colunas)
    ├── contas_a_receber_limpa.csv         # Etapa 4 (13 colunas, só demanda de produto)
    ├── contas_a_receber_encomendas.csv    # Etapa 5 (+ encomenda, limiar_encomenda, dias_tipicos_linha)
    ├── limiares_encomenda.csv             # Etapa 5 (1 limiar por unidade × categoria)
    ├── calendario_diario.csv              # Etapa 6 (data × unidade, 2024-01-01 → 2026-12-31)
    ├── serie_diaria_unidade.csv           # Etapa 7 — L1 (total, balcão, encomenda)
    ├── serie_diaria_unidade_categoria.csv # Etapa 7 — desagregação
    └── preprocessamento_relatorio.json    # run_all — resumo + conferências

ia-predictor/data/external/               # versionado: fontes públicas baixadas uma vez
    ├── feriados_nacionais_<ano>.json      # BrasilAPI
    └── clima_open_meteo_*.csv             # Open-Meteo (só experimento do doc 03)

ia-predictor/tests/unit/test_preprocessing_etapas.py   # regras das Etapas 4–7 (10 testes)
```

`training_scripts/output/` é `.gitignore` (dado gerado; o que se versiona é o código que o
reproduz). Quando a Fase 1 do plano de experimentos fechar a forma final, a lógica migra
para `backend/domain/etl/` (Fase 5), com as validações de qualidade que faltam hoje. A
antiga Etapa 3 de one-hot (`discretize_fields.py`, `contas_a_receber_discretizado.csv`,
`encodings.py`) foi removida em 2026-08-30 — está no histórico do git se precisar como
referência (ADR-010): aquele one-hot codificava `pagamento`/`empresa`/`vendedor` como
exógenas do L1, e a revisão de escopo concluiu que essas categóricas não entram no modelo.
