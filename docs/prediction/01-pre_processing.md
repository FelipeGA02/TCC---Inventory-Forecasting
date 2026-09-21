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

Este documento é deliberadamente verboso no **porquê**: cada decisão de parsing, cada
coluna removida, cada regra de taxonomia e cada valor default está justificado, porque o
pré-processamento é onde a maior parte das escolhas metodológicas do CRISP-DM (compreensão
dos dados → preparação) ficam gravadas em código.

---

## 1. Visão geral

O alvo do modelo L1 é uma **série temporal diária por unidade**: para cada `unidade`, a
soma de `qtdade` vendida por dia, de todas as categorias de produto. `categoria` (e depois
SKU) são obtidos por desagregação em cascata, não por um modelo próprio (ver §5.2). O
pré-processamento não constrói nenhuma dessas séries (isso é `prepare_daily_series()`, no
backend/experimentação) — ele entrega a **base transacional limpa e enriquecida** de onde
as séries são somadas.

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
│  → output/contas_a_receber_taxonomia.csv     │  12 colunas · pronto para prepare_daily_series
└──────────────────────────────────────────────┘
        │
        ▼
   prepare_daily_series(df, unidade)             ← alvo do L1 — FORA deste pipeline
   prepare_daily_series(df, unidade, categoria)  ← perfil de desagregação (L2)
   (training_scripts/baseline/ — Fase 1 do plano de experimentos)
```

### Por que entregar uma base transacional, e não a série diária pronta

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
python -m training_scripts.preprocessing.build_dataset
python -m training_scripts.preprocessing.reduce_schema
python -m training_scripts.preprocessing.map_taxonomy
```

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
`categoria` + `categoria_fina`). É o arquivo que `prepare_daily_series()` consome, em dois
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

## 6. O que este pipeline NÃO resolve (e onde reaparece)

Cada item abaixo foi **deixado de fora de propósito** — ou porque é regra de negócio que
pertence ao backend de produção, ou porque depende de decisões de modelagem ainda abertas.

- **Validação de qualidade de dado** (`qtdade <= 0` — 880 linhas, `emissao` nula, vírgula
  decimal malformada). O parser só extrai e formata; não julga. As regras de negócio ficam
  no `domain/etl/normalizer.py` de produção (`SPECS.md` §4.2, ainda stub), para que exista
  **um só lugar** com a política de limpeza, versionado e testado.
- **Curadoria fina de `categoria_fina`** — os ~34 SKUs do `CATEGORIA_POR_SKU` são
  provisórios e a cauda de `"Outros"` (1,3%) não foi esgotada. Impacto no L1 é nulo (tudo
  colapsa em `Produtos de jardim`); a curadoria interessa à EDA e à L2. A estrutura de
  `unidade` e de `categoria` L1 já está **fechada** (ADR-011), não é mais pendência.
- **Recomendação de reposição (L3), `shelf_life_dias`, risco de perda/ruptura** — **fora
  de escopo** por decisão da parceira (ADR-011). O entregável é só a previsão de demanda.
- **Construção da série diária** (`prepare_daily_series`) — Fase 1 do
  [plano de experimentos](plano_experimentos_modelagem.md), em `training_scripts/baseline/`.
  Fora daqui pelo motivo da seção 1 (não reprocessar XLSX a cada ajuste de parâmetro).
- **Exógenas de calendário** (dia-da-semana, feriados nacionais/municipais, datas
  comemorativas) — `domain/features/calendar_exogenous.py`; feriados municipais e clima na
  Fase 2 do plano.
- **Features de preço/desconto** a partir de `vl_*` — avaliadas na Fase 3, não no baseline.
  As colunas cruas já ficam no CSV para não reprocessar depois.
- **Desagregação para SKU (L2)** — usa `produto_cod` do CSV da Etapa 3 + histórico; fora
  deste pipeline.

---

## 7. Artefatos

```text
ia-predictor/training_scripts/
├── preprocessing/
│   ├── constants.py            # caminhos + layout de colunas do XLSX + COLUMNS_TO_DROP + DUPLICATE_KEY_FIELDS
│   ├── helpers.py              # format_decimal, parse_field, file_hash, load/save_log, load_existing_record_keys...
│   ├── parser.py               # parse_xlsx() — extrai registros do XLSX por posição de coluna fixa
│   ├── build_dataset.py        # Etapa 1 — parsing + dedup entre arquivos + log + idempotência por hash
│   ├── reduce_schema.py        # Etapa 2 — remove 11 colunas → CSV de 9 colunas
│   ├── map_taxonomy.py         # Etapa 3 — deriva unidade (L1) + categoria/categoria_fina (desagregação) + diagnóstico (% "Outros", cobertura ≥180d por unidade e por par)
│   └── taxonomy/               # tabelas de/para versionadas (curadas à mão)
│       ├── __init__.py
│       ├── unidades.py         # empresa → unidade (2 unidades, fechado) (+ NORMALIZE_EMPRESA)
│       └── categorias.py       # produto → categoria_fina (cascata) + CATEGORIA_L1 (3 categorias) + GRUPO_PRODUTO (grupos do cliente)
└── output/                      # gerado ao rodar os scripts — não versionado (.gitignore)
    ├── contas_a_receber.csv               # Etapa 1 (20 colunas)
    ├── processamento_log.json
    ├── contas_a_receber_sem_colunas.csv   # Etapa 2 (9 colunas)
    └── contas_a_receber_taxonomia.csv     # Etapa 3 (12 colunas) — entrada de prepare_daily_series
```

`training_scripts/output/` é `.gitignore` (dado gerado; o que se versiona é o código que o
reproduz). Quando a Fase 1 do plano de experimentos fechar a forma final, a lógica migra
para `backend/domain/etl/` (Fase 5), com as validações de qualidade que faltam hoje. A
antiga Etapa 3 de one-hot (`discretize_fields.py`, `contas_a_receber_discretizado.csv`,
`encodings.py`) foi removida em 2026-08-30 — está no histórico do git se precisar como
referência (ADR-010): aquele one-hot codificava `pagamento`/`empresa`/`vendedor` como
exógenas do L1, e a revisão de escopo concluiu que essas categóricas não entram no modelo.
