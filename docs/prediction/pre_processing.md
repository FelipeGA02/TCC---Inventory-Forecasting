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
│ Etapa 3 — discretize_fields.py   │  converte 3 categóricas em código inteiro
│  → output/contas_a_receber_discretizado.csv │
│  → output/encodings.py (mapeamento gerado)  │
└───────────────────────┘
```

Cada etapa é um script independente, com função pura reaproveitável e um bloco
`if __name__ == '__main__':` para rodar isolado. A partir de `ia-predictor/`:

```bash
python -m training_scripts.preprocessing.build_dataset
python -m training_scripts.preprocessing.reduce_schema
python -m training_scripts.preprocessing.discretize_fields
```

---

## 2. Etapa 1 — `build_dataset.py`: parsing + deduplicação + log

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
- Deduplicação por chave composta **`(doc_numero, produto_cod)`** contra as chaves já
  presentes no CSV de saída — necessário porque os relatórios mensais exportados têm
  sobreposição de datas nas bordas do mês (a última venda de um dia pode aparecer em
  dois arquivos consecutivos).
- Linhas que não batem com o padrão esperado (`Cliente:` ausente, `Produto` ausente
  etc.) são contabilizadas em `skipped`, com linha e motivo, mas **não interrompem o
  processamento** — o objetivo é máxima recuperação de dados de um relatório que não
  foi desenhado para ser lido por máquina.

### O JSON de log gerado

`output/processamento_log.json` tem dois blocos:

```json
{
  "arquivos_processados": {
    "abril 24.xlsx": {
      "hash": "<md5>",
      "processado_em": "2026-08-23T13:47:22",
      "registros_adicionados": 11545,
      "registros_pulados": 0,
      "duplicatas_encontradas": 201
    }
  },
  "historico_execucoes": [
    {
      "executado_em": "2026-08-23T13:47:22",
      "arquivos": ["abril 24.xlsx", "..."],
      "total_registros_adicionados": 0,
      "total_pulados": 0,
      "total_duplicatas": 0
    }
  ],
  "ultima_atualizacao": "2026-08-23T13:47:22"
}
```

Isso resolve o gap de rastreabilidade apontado em
`docs/project/current_files_state.md` §4 e §8.2 — o `processamento_log.json` de
produção (`ia-predictor/data/processed/`) hoje só tem 1 entrada de teste, sem histórico
real de como o CSV de 343k linhas foi montado. O log gerado por este pipeline em
`training_scripts/` mostra exatamente isso, por arquivo, de forma reprodutível — é o
formato de referência para quando o `domain/etl/` de produção (ainda stub) for
implementado de verdade (Fase 5 do
[plano de experimentos](plano_experimentos_modelagem.md)).

---

## 3. Execução verificada e comparação com o CSV de produção

`build_dataset.py` foi rodado de ponta a ponta contra os 26 XLSX reais de `data/raw/`
(mais um 27º arquivo, `20260803013959_sample.xlsx`, que não gerou nenhum registro).
Resultado, ponto a ponto contra `ia-predictor/data/processed/contas_a_receber.csv` (o
CSV canônico usado hoje):

| Métrica | CSV de produção | CSV reconstruído (`training_scripts/output/`) |
| --- | --- | --- |
| `wc -l` (linhas físicas) | 343.117 | 343.112 |
| Registros reais (via `csv.DictReader`, respeitando aspas) | 324.830 | **324.825** |
| Cabeçalho (20 colunas, mesma ordem) | idêntico | idêntico |
| `empresa` (valores distintos) | 4 | 3 |
| `vendedor` (valores distintos) | 39 | 38 |

**Achado 1 — `wc -l` superestima o número de registros.** A diferença entre linhas
físicas e registros reais (~18 mil em ambos os arquivos) não é dado faltando: é `wc -l`
contando **quebras de linha dentro de campos entre aspas** como se fossem linhas novas.
O campo responsável é quase sempre `obs` (observações de texto livre do vendedor, ex.:
`"levar maquininha de cartao \n5 x"`), escrito corretamente entre aspas (RFC 4180), mas
que confunde qualquer contagem ingênua por linha — mais um motivo para removê-lo na
Etapa 2.

**Achado 2 — as 5 linhas extras na produção vêm de um upload de teste, não de dado
real.** Comparando as chaves `(doc_numero, produto_cod)` dos dois arquivos, o CSV
reconstruído é um **subconjunto exato** do CSV de produção — nenhuma chave existe só no
reconstruído, e exatamente 5 existem só na produção. As 5 têm `arquivo_origem =
sample.xlsx`, `empresa = 'LOJA CENTRO'`, `vendedor = 'PEDRO'` e `operador = 'ANA'` —
nomes fictícios que não aparecem em nenhum XLSX real de `data/raw/`. Isso bate com o
`processamento_log.json` **de produção**, que só tem uma entrada:

```json
[{"filename": "sample.xlsx", "rows_added": 5, "rows_skipped": 3,
  "rows_duplicate": 1, "logged_at": "2026-08-03T01:40:11.579052"}]
```

Ou seja: o CSV canônico de produção = exatamente os dados reais que este pipeline
reconstrói a partir de `data/raw/` **+ 5 linhas de um teste manual do upload**
(`tests/fixtures/sample.xlsx`), feito em outra sessão com outro formato de log (lista
plana, diferente do formato aninhado `arquivos_processados`/`historico_execucoes` deste
pipeline e do protótipo original). Isso confirma e fecha o gap de rastreabilidade
apontado em `docs/project/current_files_state.md` §4/§8.2: não há dado real "perdido"
ou inexplicado — só um upload de teste que ficou misturado ao dado de produção e nunca
foi removido. **Antes de treinar o SARIMAX em cima do CSV de produção, vale filtrar
`arquivo_origem != 'sample.xlsx'` (ou usar o CSV reconstruído aqui, que já não os tem).**

---

## 4. Etapa 2 — `reduce_schema.py`: remoção de colunas

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
| `obs` | Texto livre do vendedor (ex.: instruções de entrega, forma de pagamento combinada). Sem estrutura, alta cardinalidade textual, **e é o campo com quebras de linha embutidas** que causava a divergência de contagem da seção 3 — removê-lo também simplifica qualquer leitura por linha do arquivo. |
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

## 5. Etapa 3 — `discretize_fields.py`: discretização (opcional)

### Decisão

Depois da Etapa 2, ainda sobram três colunas categóricas nominais de baixa
cardinalidade: `pagamento` (13 valores), `empresa` (3 valores) e `vendedor` (38
valores) — números confirmados na execução real (seção 3), batendo exatamente com o
mapeamento do protótipo original. `discretize_fields.py` mapeia cada valor único para um
código inteiro sequencial (1, 2, 3...) e salva o mapeamento gerado em
`output/encodings.py`, para que o mesmo código volte a ser interpretável depois
(ex.: `EMPRESA_ENCODING['VERDE PERTO JARDINAGEM LTDA'] == 3`).

### Ressalva — não é uma decisão fechada

Um código inteiro sequencial impõe uma **ordem artificial** a categorias que não têm
ordem natural (não existe "pagamento 5 > pagamento 3"). Isso é inofensivo se essas
colunas nunca virarem exógenas do SARIMAX como estão — mas a spec de exógenas
(`SPECS.md` §5.2, variáveis `mkt_*`/`prod_*`) sugere agregações e indicadores binários
por produto, não necessariamente a forma de pagamento discretizada dessa forma direta.
**Antes de travar isso em produção**, vale revisitar na Fase 1 do
[plano de experimentos](plano_experimentos_modelagem.md) se essas três colunas:

- entram como exógenas via one-hot/dummy (sem impor ordem), ou
- são agregadas em features derivadas (ex.: `%vendas_no_pix_do_mes` por produto), ou
- simplesmente não entram no SARIMAX por produto (pagamento/vendedor variam por
  transação, não por produto — o sinal relevante pode já estar diluído demais no nível
  de agregação mensal por produto que o modelo usa).

### Nota: por que o CSV de produção mostra 4 empresas e 39 vendedores

Quem inspecionar `ia-predictor/data/processed/contas_a_receber.csv` diretamente vai
encontrar um 4º valor de `empresa` (`LOJA CENTRO`) e um 39º `vendedor` que não existem
no `encodings.py` gerado por este pipeline (3 empresas, 38 vendedores — idêntico ao
protótipo original). Não é dado real novo: são as mesmas 5 linhas de teste
(`arquivo_origem = sample.xlsx`) identificadas na seção 3 — `LOJA CENTRO` e o vendedor
`PEDRO` (distinto de `PEDRO - VENDEDOR`, que já existe na lista) só existem nesse
upload de teste, nunca em um XLSX real. Reforça a recomendação da seção 3: filtrar
`sample.xlsx` antes de gerar qualquer encoding ou treinar sobre o CSV de produção.

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

`training_scripts/output/` é isolado de `ia-predictor/data/processed/` de propósito
(e listado no `.gitignore` — dado gerado, não versionado): rodar estes scripts
nunca sobrescreve o CSV canônico de produção. Quando a Fase 1 do plano de experimentos
decidir a forma final do pré-processamento, a lógica migra para `backend/domain/etl/`
(Fase 5) e passa a escrever em `data/processed/` de verdade, com as validações de
qualidade que faltam hoje.
