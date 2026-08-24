# Pré-processamento dos Dados — O Que Foi Feito e Por Quê

Documenta o pipeline em [`ia-predictor/training_scripts/preprocessing/`](../../ia-predictor/training_scripts/preprocessing/):
os scripts que transformam os XLSX brutos de "Contas a Receber" em uma planilha
consolidada pronta para o treinamento do SARIMAX, e as decisões (remoção de colunas,
discretização) por trás de cada etapa.

---

## 1. Visão geral do pipeline

```
data/raw/*.xlsx (26 planilhas, jan/2024–fev/2026)
        │
        ▼
┌───────────────────────┐
│ Etapa 1 — build_dataset.py       │  parser.py + dedup + log JSON
│  → output/contas_a_receber.csv   │  (20 colunas, 1 linha por documento×produto)
│  → output/processamento_log.json │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│ Etapa 2 — reduce_schema.py       │  remove 7 colunas sem uso analítico
│  → output/contas_a_receber_sem_colunas.csv │  (13 colunas)
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│ Etapa 3 — discretize_fields.py   │  converte 3 categóricas em one-hot (0/1)
│  → output/contas_a_receber_discretizado.csv │  (61 colunas)
│  → output/encodings.py (categorias geradas) │
└───────────────────────┘
```

### Por que três scripts separados, e não um só

Cada etapa resolve um problema diferente: extrair uma tabela de um relatório que não é
tabular (Etapa 1), reduzir essa tabela às colunas com sinal preditivo (Etapa 2), e
converter as categóricas restantes em algo que um modelo numérico consegue usar
(Etapa 3). Rodar isso como estágios separados — em vez de um script monolítico —
permite inspecionar e validar a saída de cada etapa isoladamente antes de seguir para
a próxima (foi assim, por exemplo, que o achado sobre `wc -l`/quebras de linha na
seção 3 apareceu: olhando o CSV intermediário da Etapa 1 antes de mexer em qualquer
coluna). Também espelha a divisão de responsabilidades que o pipeline de produção
(`backend/domain/etl/`) vai ter quando for implementado de verdade (parser → normalizer
→ feature builder), então esta experimentação já valida a divisão antes de virar
código de produção.

Cada etapa é um script independente, com função pura reaproveitável e um bloco
`if __name__ == '__main__':` para rodar isolado. A partir de `ia-predictor/`:

```bash
python -m training_scripts.preprocessing.build_dataset
python -m training_scripts.preprocessing.reduce_schema
python -m training_scripts.preprocessing.discretize_fields
```

---

## 2. Etapa 1 — `build_dataset.py`: parsing + deduplicação + log

### Por que essa etapa existe

O relatório de "Contas a Receber" exportado pelo sistema da floricultura foi feito
para uma pessoa ler, não para um modelo consumir: é texto organizado em blocos, uma
venda por bloco, sem estrutura de tabela. Antes de qualquer modelagem é preciso
transformar isso numa tabela onde cada linha representa uma unidade de análise
consistente (aqui, 1 produto dentro de 1 documento) — sem isso não dá nem para somar
quantas unidades de um produto foram vendidas em um mês, que é a pergunta que o
SARIMAX precisa responder. Esta etapa também é o único ponto do pipeline que toca os
26 arquivos brutos diretamente: depois dela, tudo o resto trabalha em cima de um único
CSV consolidado. Por isso a deduplicação e o controle de hash (abaixo) precisam viver
aqui — é a única chance de garantir que cada venda real apareça exatamente uma vez
antes que o dado siga para as próximas etapas.

### O que o script faz

O XLSX de "Contas a Receber" exportado pelo sistema da floricultura não é uma tabela
retangular — é um relatório com blocos: cada bloco começa numa linha `Documento: C1
44799`, seguido de linhas de cabeçalho (Cliente, Empresa, Vendedor, Obs), uma linha
`Produto` e N linhas de item até a linha `Totais`. O `parser.py` varre o arquivo linha a
linha, reconhece esse padrão por posição de coluna fixa (`HEADER_COLUMNS`,
`DETAIL_COLUMNS`, `PRODUCT_COLUMNS` em `constants.py` — layout do relatório, não muda
entre meses) e expande cada bloco em **um registro por (documento, produto)** — é por
isso que uma venda com 3 itens vira 3 linhas no CSV, todas com o mesmo `doc_numero`.

`build_dataset.py` orquestra isso para as 26 planilhas de `data/raw/`:

- Cada planilha só é (re)processada se for nova ou o **hash MD5** mudou desde a última
  execução (controle em `processamento_log.json`) — permite rodar de novo com
  segurança, sem duplicar dados, mesmo se uma planilha for corrigida e re-enviada.
- Deduplicação por chave composta **`(doc_numero, produto_cod, emissao, qtdade,
  vl_total)`**, aplicada **só entre arquivos diferentes** — nunca dentro do mesmo
  arquivo — contra as chaves já vistas em planilhas anteriores. Existe porque os
  relatórios mensais exportados têm sobreposição de datas nas bordas do mês (a última
  venda de um dia pode aparecer em dois arquivos consecutivos). Ver o achado logo
  abaixo para o porquê dessa chave específica e da restrição "só entre arquivos".
- Linhas que não batem com o padrão esperado (`Cliente:` ausente, `Produto` ausente
  etc.) são contabilizadas em `skipped`, com linha e motivo, mas **não interrompem o
  processamento** — o objetivo é máxima recuperação de dados de um relatório que não
  foi desenhado para ser lido por máquina.

### Achado — a deduplicação original descartava vendas reais (corrigido)

A primeira versão deste script deduplicava por `(doc_numero, produto_cod)` comparando
cada registro contra **todos** os já vistos, inclusive dentro do próprio arquivo sendo
processado. Isso presumia que um produto só poderia aparecer uma vez por documento —
presunção errada, e que custava vendas reais.

Investigando `abril 24.xlsx` isoladamente (11.746 registros), essa chave sinalizou 201
"duplicatas". Comparando os campos de venda (`qtdade`, `vl_unit`, `vl_total`,
`vl_desconto`, `tot_liq`) entre a primeira e a segunda ocorrência de cada chave:

| | Quantidade |
| --- | --- |
| Valores de venda diferentes entre as duas ocorrências | 165 |
| Valores de venda idênticos nas duas ocorrências | 36 |

Os 165 com valores diferentes já eram evidência forte de vendas distintas — não dá pra
ser "duplicata de exportação" se a quantidade vendida é diferente. Os 36 com valores
idênticos pareciam, à primeira vista, duplicatas de verdade — até serem checados contra
o total do próprio documento.

**Prova**: o documento `995` tem 12 linhas de produto, entre elas duas ocorrências do
produto `433NL` (ambas com `qtdade=3` e `tot_liq=6`). Somando o `tot_liq` das 12 linhas,
o resultado bate **exatamente** com o `total_liquido_doc` informado no relatório
(756,30). Se a segunda linha de `433NL` fosse uma duplicata de exportação, o total real
da nota seria 750,30 — 6,00 a menos. O próprio sistema de origem contabilizou as duas
linhas separadamente no total da venda, o que só é possível se as duas forem vendas
reais (ex.: o item foi escaneado duas vezes no caixa), não um erro de exportação. Ou
seja: **nenhuma** das 201 "duplicatas" encontradas nesse arquivo era, de fato,
duplicata — 100% era venda real sendo silenciosamente descartada.

**Correção aplicada** (`build_dataset.py`, `process_pending_files`; `constants.py`,
`DUPLICATE_KEY_FIELDS`):

1. As chaves de um arquivo só entram no conjunto de "já vistas" **depois** que o
   arquivo inteiro termina de ser processado — nunca durante. Assim, um produto
   repetido dentro do mesmo documento nunca é comparado contra si mesmo, e a
   deduplicação passa a valer exclusivamente **entre arquivos diferentes**, que é o
   cenário real que ela foi criada para resolver.
2. A chave em si ficou mais rígida: de `(doc_numero, produto_cod)` para
   `(doc_numero, produto_cod, emissao, qtdade, vl_total)`. Motivo: `doc_numero` sozinho
   não é um identificador único — o mesmo número se repete entre `doc_tipo` diferentes
   (confirmado nos dados reais: 32.572 números de documento usados por mais de um
   tipo). Com a chave antiga, um documento de um arquivo podia colidir por acaso com um
   documento completamente diferente de outro arquivo que reaproveitou o mesmo número.
   Exigir também data, quantidade e valor batendo reduz drasticamente essa chance: uma
   duplicata real de exportação (o mesmo documento reaparecendo em dois arquivos) bate
   em todos esses campos; dois documentos não relacionados que só compartilham o
   número, não.

Os números da seção 3 já refletem o pipeline rodado com essa correção.

### O JSON de log gerado

`output/processamento_log.json` tem dois blocos:

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
    {
      "executado_em": "2026-08-23T18:32:44",
      "arquivos": ["abril 24.xlsx", "..."],
      "total_registros_adicionados": 333019,
      "total_pulados": 0,
      "total_duplicatas": 0
    }
  ],
  "ultima_atualizacao": "2026-08-23T18:32:44"
}
```

Esse formato aninhado (`arquivos_processados` por hash + `historico_execucoes` por
rodada) garante rastreabilidade completa: para cada execução é possível saber
exatamente quais arquivos entraram, quantos registros foram adicionados, pulados e
quantas duplicatas foram descartadas — sem precisar reprocessar nada para auditar.

---

## 3. Execução real — volume processado e observações

`build_dataset.py` foi rodado de ponta a ponta contra as 26 planilhas XLSX reais de
`data/raw/` (jan/2024–fev/2026), já com a correção da deduplicação (achado da seção 2).
Resultado:

| Métrica | Valor |
| --- | --- |
| Planilhas processadas | 26 |
| Registros reais (via `csv.DictReader`, respeitando aspas) | 333.019 |
| Linhas físicas do CSV de saída (`wc -l`) | 351.991 |
| Duplicatas encontradas **entre arquivos** (a única forma de dedup que ainda existe) | 0 |
| Cabeçalho | 20 colunas, 1 linha por (documento, produto) |
| `empresa` (valores distintos) | 3 |
| `vendedor` (valores distintos) | 38 |

**Observação — `wc -l` superestima o número de registros.** A diferença entre linhas
físicas (351.991) e registros reais (333.019) — quase 19 mil linhas — não é dado
faltando: é `wc -l` contando **quebras de linha dentro de campos entre aspas** como se
fossem linhas novas. O campo responsável é quase sempre `obs` (observações de texto
livre do vendedor, ex.: `"levar maquininha de cartao \n5 x"`), escrito corretamente
entre aspas (RFC 4180), mas que confunde qualquer contagem ingênua por linha do
arquivo — mais um motivo para removê-lo na Etapa 2 (seção 4).

**Observação — zero duplicatas reais entre arquivos neste dataset.** Com a chave
corrigida (`doc_numero, produto_cod, emissao, qtdade, vl_total`, aplicada só entre
arquivos), nenhuma das 26 planilhas teve registro descartado por duplicata. Isso não
significa que a lógica de dedup entre arquivos seja inútil — o cenário que ela cobre
(mesma venda exportada em dois meses consecutivos, na borda do mês) continua sendo uma
possibilidade real do processo de exportação — só que, nos 26 arquivos atuais, esse
cenário não chegou a se concretizar. A lógica fica pronta para o dia em que acontecer,
sem custar nada quando não acontece.

---

## 4. Etapa 2 — `reduce_schema.py`: remoção de colunas

### Por que essa etapa existe

Nem toda coluna do relatório operacional ajuda a prever demanda por produto. O
relatório de contas a receber existe para controle financeiro e fiscal (quem vendeu,
quem operou o caixa, quanto de imposto foi retido) — não foi desenhado pensando em
série temporal de vendas por produto, então carrega várias colunas que são ruído puro
para esse objetivo. Manter essas colunas infla a tabela à toa (mais dado para carregar
e processar sem ganho nenhum), atrapalha leituras ingênuas do arquivo (o campo `obs`,
com quebras de linha embutidas, é o exemplo visto na seção 3), e no caso dos campos de
cliente é um risco de privacidade que a constituição do projeto proíbe expor
(Princípio VI). Esta etapa existe para reduzir o CSV bruto ao subconjunto mínimo de
colunas com relação real com a demanda do produto — o critério por trás de cada
remoção na tabela abaixo é sempre o mesmo: **essa coluna muda a resposta de "quanto
desse produto vai ser vendido"?**

### Decisão

```python
COLUMNS_TO_DROP = [
    'operador', 'obs', 'icms_ret', 'arquivo_origem',
    'cliente_nome', 'produto_nome', 'doc_tipo',
]
```

| Coluna | Por que foi removida |
| --- | --- |
| `operador` | Identifica quem operou o caixa/sistema no momento da venda — é um dado operacional interno, sem relação com demanda do produto. 13 valores distintos, mas nenhum poder explicativo sobre *quanto* de um produto será vendido. |
| `obs` | Texto livre do vendedor (ex.: instruções de entrega, forma de pagamento combinada). Sem estrutura, alta cardinalidade textual, **e é o campo com quebras de linha embutidas** que causava a divergência de contagem observada na seção 3 — removê-lo também simplifica qualquer leitura por linha do arquivo. |
| `icms_ret` | Campo fiscal (ICMS retido). Verificado nos dados reais: é `0` na esmagadora maioria das linhas amostradas — não carrega sinal de demanda, é metadado contábil. |
| `arquivo_origem` | Artefato do próprio processamento (nome do XLSX de origem) — redundante com `emissao` (a data já localiza o registro no tempo) e não existe no domínio do negócio. |
| `cliente_nome` | Nome do cliente. Além de não ter uso preditivo por produto, expor nome de cliente violaria o Princípio VI da constituição (API não expõe dados pessoais de clientes) — `cliente_cod` já basta para qualquer segmentação futura por código. |
| `produto_nome` | Texto livre (ex.: "VASO POLIET. CLASSIC CONICO 46"), mesmo produto pode ter grafias levemente diferentes entre meses. `produto_cod` já identifica o produto de forma unívoca e é a chave usada em toda a modelagem (`prepare_monthly_series(df, produto_cod)`, `SPECS.md` §5.1) — manter as duas seria redundante. |
| `doc_tipo` | Código de tipo de documento interno do sistema de vendas (`C1`, `C7`, `F3`, `NN`, 21 valores distintos nos dados reais). Não corresponde a uma dimensão de negócio com valor preditivo separada da forma de pagamento (`pagamento`), que já é mantida. |

**Resultado**: de 20 para **13 colunas**:
`doc_numero, pagamento, emissao, cliente_cod, empresa, vendedor, produto_cod, qtdade,
vl_unit, vl_total, vl_desconto, tot_liq, total_liquido_doc`.

Essa é a "planilha consolidada para o treinamento" — sem os campos que atrapalhariam
(texto livre de alta cardinalidade, PII, metadado de processamento, campo fiscal) — que
alimenta a Fase 1 do [plano de experimentos](plano_experimentos_modelagem.md) 1.2
(`prepare_monthly_series()`).

---

## 5. Etapa 3 — `discretize_fields.py`: discretização em one-hot

### Por que essa etapa existe

SARIMAX, como qualquer modelo de regressão, só aceita número como entrada — não sabe o
que fazer com texto como `'PIX'` ou `'ADELSON'` diretamente. Ainda assim, depois da
Etapa 2 ainda sobram três colunas categóricas nominais de baixa cardinalidade:
`pagamento` (13 valores), `empresa` (3 valores) e `vendedor` (38 valores) — e forma de
pagamento, unidade e vendedor podem carregar sinal real sobre o comportamento de
demanda (ex.: uma unidade vender consistentemente mais que outra). Descartar essas
colunas jogaria fora esse sinal; esta etapa existe para torná-las utilizáveis como
exógenas sem inventar uma relação numérica entre categorias que, na realidade, não têm
ordem nenhuma entre si.

### Decisão

Essas colunas vão ser usadas como exógenas no treinamento, então precisam virar
número de alguma forma — mas sem distorcer o que representam.

A versão anterior deste script mapeava cada valor único para um código inteiro
sequencial (1, 2, 3...). Isso foi **trocado por one-hot encoding** (uma coluna binária
0/1 por categoria). Motivo: um código sequencial impõe uma **ordem artificial** a
categorias que não têm ordem natural — não existe "pagamento 5 > pagamento 3", nem
"vendedor 12" é "maior" que "vendedor 3". Se essas colunas entrassem assim, cruas, como
exógenas numéricas do SARIMAX, o modelo passaria a interpretar essa numeração como uma
escala contínua (ex.: como se "código 6" tivesse o dobro do efeito de "código 3"),
o que não corresponde a nada real — é só a ordem alfabética em que o valor apareceu.
One-hot evita esse problema por completo: cada categoria vira sua própria coluna
independente (`1` = a venda é dessa categoria, `0` = não é), sem impor nenhuma relação
de ordem ou magnitude entre elas.

Das três alternativas registradas anteriormente nesta seção (one-hot, agregação em
features derivadas por produto, ou simplesmente não usar essas colunas), one-hot foi a
escolhida porque é a única que se encaixa no nível em que este pipeline trabalha hoje
— linha a linha (documento × produto), sem agregação mensal. Agregar em algo como
`%vendas_no_pix_do_mes` por produto exigiria a lógica de agregação mensal que é
responsabilidade da Fase 1.2 (seção 6), fora do escopo deste script; e descartar as
colunas contradiz o objetivo de usá-las no treinamento.

`discretize_fields.py` agora, para cada uma das três colunas:

1. Ordena os valores únicos alfabeticamente e reserva o **primeiro como baseline**
   (categoria de referência, que não vira coluna).
2. Cria uma coluna nova `{campo}_{CATEGORIA}` (0/1) para cada valor restante.
3. Remove a coluna categórica original.

O baseline fica de fora de propósito — é a técnica padrão para evitar a **"dummy
variable trap"**: se todas as categorias virassem coluna, elas seriam linearmente
dependentes entre si (a soma de todas as colunas de um campo é sempre 1), o que causa
multicolinearidade perfeita e quebra a regressão. Com o baseline omitido, as demais
colunas são lidas *em relação a ele* (ex.: a coluna `pagamento_PIX = 1` diz "essa venda
foi no PIX, e não na forma de pagamento baseline").

### O baseline omitido não é informação perdida

Ficar de fora do one-hot não significa que o baseline vira invisível para o modelo.
Quando **todas** as colunas one-hot de um campo são `0` numa linha, essa é a única
combinação que sobra — ela já identifica sem ambiguidade "esta venda é da categoria
baseline". Essa informação não desaparece, ela é absorvida pelo **intercepto**
(constante) do modelo: o intercepto passa a representar "o valor esperado quando é a
categoria baseline e todo o resto é 0", e cada coeficiente das colunas one-hot passa a
representar o *efeito adicional* de sair do baseline para aquela categoria. É assim que
`patsy`/`statsmodels` (a biblioteca usada aqui) e o `OneHotEncoder(drop='first')` do
scikit-learn codificam categórica em regressão por padrão — não é um atalho deste
pipeline, é o jeito padrão de fazer isso.

**Por que não incluir todas as categorias.** Se o SARIMAX for treinado **com
intercepto** (`trend='c'`, padrão do statsmodels quando não há diferenciação) e todas
as categorias de um campo tiverem coluna própria (nenhuma omitida), a soma dessas
colunas é sempre `1` — exatamente igual à coluna implícita do intercepto. Isso causa
multicolinearidade perfeita: o sistema fica matematicamente indeterminado, e o
otimizador do SARIMAX tende a travar (matriz singular) ou devolver coeficientes
instáveis, porque existem infinitas combinações de intercepto + coeficientes que dão o
mesmo resultado.

A única forma segura de incluir todas as categorias seria treinar **sem intercepto**
(`trend='n'`) — aí cada coeficiente vira o valor médio absoluto daquela categoria, em
vez de "diferença pro baseline". Mas essa é uma decisão de **modelagem**, tomada na
Fase 1 ao chamar o SARIMAX — não do pré-processamento, que gera as colunas exógenas sem
saber se quem for treinar vai usar intercepto ou não. Omitir o baseline é a opção que
funciona nos dois casos (com ou sem intercepto); incluir todas as categorias só
funciona se o treino garantir `trend='n'`, o que é um risco de travar caso essa
combinação escape.

As categorias (baseline + colunas geradas) continuam documentadas em
`output/encodings.py`, agora no formato `{CAMPO}_CATEGORIES = {'baseline': ..., 'dummies': [...]}`,
para que dê pra saber depois o que cada coluna do CSV significa.

### Resultado da execução real

| Campo | Categorias totais | Baseline (omitido) | Colunas one-hot geradas |
| --- | --- | --- | --- |
| `pagamento` | 13 | `A PRAZO` | 12 |
| `empresa` | 3 | `FLORICULTURA VERDE PERTO CANADÁ LTDA` | 2 |
| `vendedor` | 38 | `ADELSON` | 37 |

O CSV final (`contas_a_receber_discretizado.csv`) saiu com **333.019 linhas × 61
colunas** (13 colunas da Etapa 2, menos as 3 categóricas originais, mais as 51 colunas
one-hot geradas). As categorias em si (baseline e colunas geradas) não mudam com a
correção da seção 2 — os ~8 mil registros recuperados eram vendas de produtos, formas
de pagamento e vendedores que já apareciam em outras linhas do dataset.

**Observação — dois valores de origem já chegam corrompidos no XLSX bruto.** Ao
inspecionar as categorias geradas, dois valores de `empresa`/`vendedor` aparecem com um
caractere `�` no lugar de um "Á" (ex.: `FLORICULTURA VERDE PERTO CANAD� LTDA`, `TIAGO
VIEIRA (CANAD�)`). Não é um bug deste pipeline — foi verificado lendo a célula
diretamente do XLSX com `openpyxl` (sem passar por nenhum código deste projeto) e o
caractere já vem assim no arquivo de origem, provavelmente de uma etapa de exportação
mal configurada no sistema da floricultura antes mesmo de o XLSX existir. Efeito
prático: isso só cria uma coluna one-hot com nome levemente errado para esses dois
valores — o dado de vendas em si (quantidade, valor) não é afetado. Se o valor
"correto" (com "Á") for necessário depois, precisa ser corrigido na origem ou por um
de-para manual — não dá pra reconstruir a partir do `�` (a informação sobre qual letra
era foi perdida antes de chegar aqui).

---

## 6. O que isso não resolve (e onde volta a aparecer)

- **Validação de qualidade de dado** (remover `qtdade <= 0`, `emissao` nula, converter
  vírgula decimal) — o parser aqui só extrai e formata, igual ao protótipo original;
  essas regras de negócio ficam para o `domain/etl/normalizer.py` de produção
  (`SPECS.md`, ainda stub), não para este pipeline de experimentação.
- **Agregação mensal por produto** (`prepare_monthly_series`) — este pipeline entrega
  dado no nível de linha (documento × produto); a granularidade mensal é responsabilidade
  da Fase 1.2 do [plano de experimentos](plano_experimentos_modelagem.md), em
  `training_scripts/baseline/`.
- **Dados externos** (feriados, clima, indicadores econômicos) — fora de escopo deste
  pipeline; ver Fase 2 do plano de experimentos.

---

## 7. Onde ficam os artefatos gerados

```
ia-predictor/training_scripts/
├── preprocessing/
│   ├── constants.py           # caminhos + layout de colunas do XLSX
│   ├── helpers.py              # format_decimal, parse_field, file_hash, load/save_log...
│   ├── parser.py                # parse_xlsx() — extrai registros do XLSX
│   ├── build_dataset.py       # Etapa 1 — orquestra parsing + dedup + log
│   ├── reduce_schema.py       # Etapa 2 — remove colunas sem uso analítico
│   └── discretize_fields.py   # Etapa 3 — discretiza categóricas (opcional/revisitar)
└── output/                     # gerado ao rodar os scripts — não versionar dados grandes
    ├── contas_a_receber.csv
    ├── processamento_log.json
    ├── contas_a_receber_sem_colunas.csv
    ├── contas_a_receber_discretizado.csv
    └── encodings.py
```

`training_scripts/output/` é isolado de propósito (listado no `.gitignore` — dado
gerado, não versionado). Quando a Fase 1 do plano de experimentos decidir a forma final
do pré-processamento, a lógica migra para `backend/domain/etl/` (Fase 5) e passa a
escrever no CSV consolidado do backend de verdade, com as validações de qualidade que
faltam hoje.
