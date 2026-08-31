# Plano de Pré-processamento dos Dados

Documenta o pipeline em [`ia-predictor/training_scripts/preprocessing/`](../../ia-predictor/training_scripts/preprocessing/):
como os XLSX brutos de "Contas a Receber" viram a base transacional consolidada, e como
essa base é preparada para alimentar a modelagem: **L1 SARIMAX** da demanda diária por
`unidade × categoria` → **L2** desagregação para SKU (ver
[ADR-009](ADR-009-granularidade-diaria-e-reposicao.md)).

> Escopo de 2026-08-30 (diário). Reescrito por inteiro para o pipeline diário (a versão
> mensal está no histórico do git). Revisado na reunião com a parceira de 2026-08-30
> ([ADR-011](ADR-011-escopo-previsao-sem-reposicao.md)): 3 lojas separadas, **3 categorias
> de demanda**, e **sem camada de reposição L3** — o entregável é a previsão de demanda.

Este documento é deliberadamente verboso no **porquê**: cada decisão de parsing, cada
coluna removida, cada regra de taxonomia e cada valor default está justificado, porque o
pré-processamento é onde a maior parte das escolhas metodológicas do CRISP-DM (compreensão
dos dados → preparação) ficam gravadas em código.

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
│ Etapa 3 — map_taxonomy.py                     │  deriva `unidade`, `categoria` (L1) e `categoria_fina`
│  → output/contas_a_receber_taxonomia.csv     │  12 colunas · pronto para prepare_daily_series
└──────────────────────────────────────────────┘
        │
        ▼
   prepare_daily_series(df, unidade, categoria)   ← FORA deste pipeline
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
| `qtdade` | **Variável alvo** — somada por dia por `unidade × categoria`. |
| `vl_unit`, `vl_total`, `vl_desconto`, `tot_liq` | Matéria-prima de features de preço/desconto, avaliadas na Fase 3 do plano de experimentos (não obrigatórias no L1 baseline). Mantidas agora para não ter de reprocessar depois. |
| `total_liquido_doc` | Reconferência de integridade — o teste do documento `995` (seção 2) depende dele; útil também para validar futuras mudanças no parser. |

---

## 5. Etapa 3 — `map_taxonomy.py`: derivar `unidade`, `categoria` e `categoria_fina`

O modelo L1 agrupa por `unidade × categoria`. **Nenhuma coluna de agrupamento existe na
base transacional** — a origem só tem `empresa`, `produto_cod` e `produto_nome`. Derivá-las
é o principal trabalho novo do pré-processamento no escopo diário, e é uma decisão
metodológica: define *quantos* modelos L1 existem e *o que* cada um agrega.

> **Decisões da reunião com a parceira (2026-08-30) — ver [ADR-011](ADR-011-escopo-previsao-sem-reposicao.md):**
>
> 1. **As 3 empresas (CNPJ) são as 3 lojas** e devem ser modeladas separadas. `unidades.py`
>    está **fechado**.
> 2. **O modelo L1 usa 3 categorias de demanda** — `Grama`, `Plantas de corte`,
>    `Produtos de jardim` — mais o rótulo `Servico e taxa` (não é produto). O negócio se
>    organiza em "grama de plantio × plantas de corte"; todo o resto do catálogo (o maior
>    volume: muda, vaso, substrato, insumo) foi agrupado em `Produtos de jardim`.
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

`empresa` tem 3 valores, um por CNPJ. **Confirmado com a parceira**: cada um é uma loja e
as três são modeladas separadamente. De/para em `taxonomy/unidades.py`:

| `empresa` | `unidade` | linhas |
| --- | --- | --- |
| `FLORICULTURA VERDE PERTO CANADÁ LTDA` | `Jardim Canadá` | 168.063 |
| `VERDE PERTO JARDINAGEM LTDA` | `Itabirito` | 135.548 |
| `GARDEN CENTER VERDE PERTO LTDA` | `Garden Center` | 29.408 |

Detalhes de implementação:

- **`NORMALIZE_EMPRESA`** corrige o mojibake `CANAD�` → `CANADÁ` (encoding trocado no
  acento em exportações anteriores). Aplicado *antes* do de/para; sem isso a linha cairia
  no default e a unidade inteira sumiria. Não custa nada quando o dado vem correto.
- **`UNIDADE_DEFAULT = "Desconhecida"`** para `empresa` nula/inesperada — falha visível
  (aparece nas contagens), não silenciosa.

### 5.2 `categoria` — dois níveis

**Por que categorizar, e não modelar por SKU.** São 5.166 SKUs; a série diária de quase
todos é esparsa (muitos zeros), regime em que SARIMAX não se aplica. Agrupar dá séries
densas com sinal para o L1. (A trilha por SKU com Croston/TSB/SBA existe em paralelo, para
comparação acadêmica — ADR-009.)

**Como o dado se parece.** A amostra dos produtos de maior volume mostrou que a
**Verde Perto opera como garden center / jardinagem, não como floricultura de flor de
corte**: o carro-chefe é **grama plantada** (esmeralda, são carlos, amendoim), seguida de
mudas em saquinho/sacola/cuia, plantas em vaso (`PT NN`), terra/adubo/argila e insumos de
jardim. Flor de corte (`ROSA EM CABO`, `ALSTROEMERIA`) é fatia pequena (~2%).

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
     venda em maço de hastes).
   - `Hortalica e erva`, `Substrato e adubo`, `Insumo e acessório` **antes das plantas
     ornamentais vivas**: `"TERRA PARA ROSAS"` deve virar substrato, não flor.
   - `GRAMA PRETA` / `PELO DE URSO` **antes** de `\bGRAMA\b`: são forração (Ophiopogon),
     não grama de plantio.
   - Faixa de altura no nome (`0,20 A 0,30CM`, `0,80 A 1,20MT`) → `Arbusto e planta formada`.
   - `PT\s?\d{1,2}`, depois código/volume de pote (`P14`, `3L`, `POTE PP`) → `Planta em vaso`.
   - `SAQ*`, `SACOLA`, `CUIA`, `BANDEJA`, `C21`, `CAPIM` → `Muda e forração`.
   - Só então o **fallback por espécie**: `BUXINHO|MURTA|IXORA|CALIANDRA|BAMBU|…` →
     `Arbusto e planta formada`; `BROMÉLIA|ORQUÍDEA` → `Planta em vaso`.
   - **Correções de regex** na mesma passada: `\b(...|SAQ|...)\b` não casava `"SAQUINHO"`
     (sem fronteira de palavra depois de `SAQ`) — virou `SAQ\w*`; o mesmo padrão travava
     `HORTALICAS` (plural), `ARGILA EXPANDIDA` e `PRESTAÇÃO DE SERVIÇO`.
3. **`CATEGORIA_DEFAULT = "Outros"`** — SKU sem match. Não é descarte. Após o refino de
   2026-08-30, `"Outros"` caiu de 9,6% → **1,3%** do volume; o resíduo é uma cauda longa
   de espécies sem palavra-chave estrutural. Colapsa em `Produtos de jardim`.

**`categoria` — o colapso L1** (`CATEGORIA_L1` + `map_categoria_l1()`):

| `categoria_fina` | → `categoria` (L1) |
| --- | --- |
| `Grama` | **Grama** |
| `Flor de corte e arranjo` | **Plantas de corte** |
| `Hortalica e erva`, `Muda e forracao`, `Planta em vaso`, `Arbusto e planta formada`, `Substrato e adubo`, `Insumo e acessorio`, `Outros` | **Produtos de jardim** |
| `Servico e taxa` | `Servico e taxa` (não-produto — excluído da série L1) |

Por que **3** e não as ~10: a parceira reconhece o negócio como "grama de plantio ×
plantas de corte"; o restante do catálogo é o grosso do volume mas não tem, para ela, um
recorte de gestão mais fino. Manter a `categoria_fina` no CSV preserva a opção de
subdividir depois (na EDA ou na L2) sem reprocessar. Não há mais `shelf_life_dias` — a
camada L3 saiu de escopo (ADR-011); o que a categoria alimenta agora é só a série de
demanda do L1.

### 5.3 Execução real (2026-08-30, taxonomia de 3 categorias)

```text
[map_taxonomy] 333.019 linhas x 12 colunas
[map_taxonomy] Linhas por unidade:
  Jardim Canadá  168.063 | Itabirito  135.548 | Garden Center  29.408
[map_taxonomy] Volume (qtdade) por categoria L1:
  Produtos de jardim        2.028.097
  Grama                     1.837.995
  Plantas de corte             74.634
  Servico e taxa                5.860
[map_taxonomy] Volume (qtdade) por categoria_fina:
  Grama 1.837.995 · Muda e forracao 935.421 · Planta em vaso 377.654 ·
  Substrato e adubo 266.314 · Arbusto e planta formada 177.208 ·
  Insumo e acessorio 140.445 · Hortalica e erva 79.277 ·
  Flor de corte e arranjo 74.634 · Outros 51.779 · Servico e taxa 5.860
[map_taxonomy] Volume em "Outros" (categoria_fina): 1.3%
[map_taxonomy] Pares unidade x categoria (modelos L1, sem Servico e taxa): 9
[map_taxonomy] Dias com venda por par: min=221, max=653, pares < 180 dias: 0
```

**Leitura**:

- **9 modelos L1** — 3 categorias de demanda × 3 lojas. `Servico e taxa` (0,1% do volume)
  não vira modelo: é excluído da série.
- O volume se divide quase meio a meio entre **`Produtos de jardim`** (51%) e **`Grama`**
  (47%); **`Plantas de corte`** é só **1,9%** — série pequena, mas com venda em ≥ 221 dias
  por par, densa o suficiente para o L1 avaliar (a EDA confirma).
- `"Outros"` (na `categoria_fina`) caiu de **9,6% → 1,3%** com o refino de 5.2 e some de
  vista no L1 ao colapsar em `Produtos de jardim`. A `categoria_fina` fica no CSV para a
  EDA e a L2.
- **Todos os 9 pares têm ≥ 180 dias com venda** (mín. 221) — nenhum cai em
  `insufficient_data`. Garden Center tem histórico mais curto (abre no CSV só em 2025),
  mas acima do mínimo.

As estatísticas — incluindo o diagnóstico de cobertura por par — são impressas pelo
próprio `map_taxonomy.py` (converte `qtdade` vírgula→ponto; `emissao` com `dayfirst=True`),
para que cada rodada entregue o raio-x sem análise externa.

### 5.4 Saída

`output/contas_a_receber_taxonomia.csv` — **12 colunas** (as 9 da Etapa 2 + `unidade` +
`categoria` + `categoria_fina`). É o arquivo que `prepare_daily_series(df, unidade,
categoria)` consome: filtra por par (usando `categoria` L1, ignorando `Servico e taxa`),
soma `qtdade` por dia, reindexa o range diário completo (dias sem venda = 0) e exige
≥ 180 dias.

### 5.5 O que ainda depende da parceira e da EDA

Resolvido nesta passada (dentro do pré-processamento):

- ✅ `empresa → unidade` **fechado** — 3 lojas, modeladas separadas.
- ✅ **Estrutura de categorias fechada** — 3 de demanda (`Grama` · `Plantas de corte` ·
  `Produtos de jardim`) + `Servico e taxa`. `shelf_life_dias` removido (L3 fora de escopo).
- ✅ `"Outros"` (na `categoria_fina`) reduzido de 9,6% para 1,3%.
- ✅ Cobertura de histórico por par verificada — os 9 pares têm ≥ 180 dias com venda; o
  script reporta isso a cada rodada.

Ainda em aberto:

- **EDA** — a série diária de cada um dos 9 pares é densa o suficiente para SARIMAX?
  distribuição de `qtdade` por par (define quem recebe `log1p`, CV > 0.7); sazonalidade
  semanal por categoria; peso de `Plantas de corte` (série pequena — verificar variância).
- **Parceira** — curadoria fina de SKUs de alto volume que hoje caem em `Outros` (impacto
  baixo, pois tudo colapsa em `Produtos de jardim`; relevante mais para a EDA e a L2).

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
│   ├── map_taxonomy.py         # Etapa 3 — deriva unidade + categoria (L1) + categoria_fina + diagnóstico (% "Outros", cobertura ≥180d por par)
│   └── taxonomy/               # tabelas de/para versionadas (curadas à mão)
│       ├── __init__.py
│       ├── unidades.py         # empresa → unidade (3 lojas, fechado) (+ NORMALIZE_EMPRESA)
│       └── categorias.py       # produto → categoria_fina (cascata) + CATEGORIA_L1 (colapso p/ 3 categorias)
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
