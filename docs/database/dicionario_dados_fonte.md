# Dicionário de Dados — Fonte "Contas a Receber"

Descreve **campo a campo** o relatório `Contas a Receber` exportado pelo sistema
legado da Floricultura Verde Perto — a única fonte de dados do projeto — e a base
transacional consolidada que o pré-processamento produz a partir dele.

Consolida o que estava espalhado em
[`training_scripts/preprocessing/parser.py`](../../ia-predictor/training_scripts/preprocessing/parser.py),
[`constants.py`](../../ia-predictor/training_scripts/preprocessing/constants.py) e na
§4 de [`docs/prediction/01-pre_processing.md`](../prediction/01-pre_processing.md).

> **Escopo.** Documenta a fonte *como ela chega* (26 XLSX mensais, jan/2024–fev/2026)
> e a saída da **Etapa 1** do pré-processamento
> (`data/processed/contas_a_receber.csv`, 20 colunas, 333.019 linhas). As colunas
> derivadas (`unidade`, `categoria`, `categoria_fina`) estão na
> [§5 do doc de pré-processamento](../prediction/01-pre_processing.md).

---

## 1. O que é o relatório de origem

`Contas a Receber` é um relatório **financeiro / fiscal** (contas a receber = títulos
a liquidar), não um extrato de vendas. Foi desenhado para leitura humana: blocos de
texto, um por documento (venda), sem estrutura tabular. Cada bloco tem um cabeçalho
(`Documento:`, cliente, empresa, vendedor, observação), uma seção `Produto` com N
linhas de item, e uma linha `Totais`.

A **Etapa 1** do pré-processamento (`build_dataset.py` + `parser.py`) varre os 26
XLSX por **posição fixa de coluna** e expande cada bloco em **uma linha por
`(documento, produto)`** — o menor grão que preserva tudo que a modelagem pode
querer somar depois (por dia×unidade×categoria para o L1; por dia×SKU para a L2).

| Propriedade | Valor |
| --- | --- |
| Arquivos de origem | 26 XLSX (`data/raw/`), um por mês, jan/2024 – fev/2026 |
| Linhas na base consolidada | 333.019 (`csv.DictReader`, respeitando aspas) |
| Grão | 1 produto dentro de 1 documento |
| Período coberto | 02/01/2024 – 28/02/2026 (26 meses, **sem lacunas**) |
| Dias distintos com venda | 654 (os ~135 dias sem venda são domingos e feriados — loja fechada) |
| `produto_cod` distintos | 5.166 |
| Documentos distintos (`doc_numero`+`doc_tipo`) | 62.553 |
| Separador do CSV | `;` (a vírgula é o separador decimal, padrão BR) |
| Codificação | UTF-8 (verificado — sem mojibake na fonte) |

---

## 2. Campos da base consolidada (20 colunas)

Ordem conforme o CSV. **Uso** indica o destino do campo no pipeline hierárquico;
**Removido em** aponta a etapa do pré-processamento que o descarta e o ADR que
justifica.

### 2.1 Identificação do documento

| # | Campo | Tipo | Distintos / faixa | Descrição | Uso no pipeline |
| --- | --- | --- | --- | --- | --- |
| 1 | `doc_tipo` | texto | 21 valores (`C1`,`C4`,`C7`,`C9`,`CE`,`CN`,`F3`,`N3`,`NN`…) | Código interno de tipo de documento (cupom, nota, condicional, devolução…). `doc_numero` **repete** entre tipos diferentes — a chave real é o par. | **Removido na Etapa 2** (ADR-010) — sem valor preditivo de volume. Usado só como parte da chave de deduplicação na Etapa 1. |
| 2 | `doc_numero` | texto (inteiro) | 62.553 | Número sequencial do documento no sistema de origem. **Não é único isoladamente** (32.572 colisões entre `doc_tipo`). | **Removido na Etapa 2.** Compõe `DUPLICATE_KEY_FIELDS` na Etapa 1 (dedup entre arquivos). |
| 3 | `pagamento` | texto | 13 valores | Forma de pagamento: `CART. CREDITO` (39%), `CART. DEBITO` (23%), `PIX` (19%), `DINHEIRO` (12%), `BOLETO`, `A PRAZO`, `VALE`, `LINK PAGAMENTO STONE`… | **Removido na Etapa 2 (ADR-010):** atributo de *transação*, **desconhecido no horizonte de previsão** (leakage), e *consequência* da venda, não driver. Fica na Etapa 1 para triagem de importância na EDA. |
| 4 | `emissao` | data `DD/MM/AAAA` | 02/01/2024 – 28/02/2026 · 654 dias | Data de emissão do documento. **Eixo temporal** de toda a modelagem. Sem nulos; 100% parseável. | **Mantido** — vira o índice diário de `prepare_daily_series`. |
| 5 | `operador` | texto | 12 valores (nomes de caixa) | Usuário do PDV que registrou a venda. | **Removido na Etapa 2** — operacional interno; proxy de turno/loja já capturado por `unidade` + dia-da-semana. |

### 2.2 Cliente e unidade

| # | Campo | Tipo | Distintos | Descrição | Uso no pipeline |
| --- | --- | --- | --- | --- | --- |
| 6 | `cliente_cod` | texto (inteiro) | 2.523 (17 nulos) | Código do cliente. `1` = `CONSUMIDOR` (balcão, maioria das linhas). | **Removido na Etapa 2** — cardinalidade alta, sem sinal de demanda agregada. Se segmentação por cliente for útil, entra como feature **derivada agregada** (ex.: % B2B no dia), nunca o id. |
| 7 | `cliente_nome` | texto | 2.486 | Nome/razão social do cliente. `CONSUMIDOR` para balcão; nomes de empresas (paisagismo, construtoras) no B2B. | **Removido na Etapa 2 — PII** (Princípio VI da constituição). Nunca chega à API. |
| 8 | `empresa` | texto | **3** | Razão social da entidade jurídica (CNPJ) que emitiu o documento. As 3 são as **3 lojas** (confirmado com a parceira, 2026-08-30). | **Mantido** — é a **chave de agrupamento `unidade`** do L1 (via `taxonomy/unidades.py`), não uma exógena. |
| 9 | `vendedor` | texto | 38 | Vendedor que atendeu (nomes; inclui `PEDRO - VENDEDOR`, `BALCÃO`…). | **Removido na Etapa 2 (ADR-010):** mede desempenho de equipe, não demanda; mix de vendedores de um dia futuro é desconhecido. |
| 10 | `obs` | texto livre | 3.619 (**89% nulo**) | Observação digitada no PDV (instruções de entrega, combinados de pagamento). Contém quebras de linha embutidas — infla `wc -l` em ~19 mil linhas físicas. | **Removido na Etapa 2** — texto livre sem sinal estruturado; "suja" a leitura ingênua do arquivo. |

### 2.3 Produto

| # | Campo | Tipo | Distintos | Descrição | Uso no pipeline |
| --- | --- | --- | --- | --- | --- |
| 11 | `produto_cod` | texto | 5.166 | Código do produto (SKU). **Preserva zeros à esquerda** (`00020227`) — por isso lido como string. Chave da desagregação L2. | **Mantido** — deriva `categoria`/`categoria_fina` (Etapa 3) e é a chave do rateio L2. |
| 12 | `produto_nome` | texto | 5.162 | Descrição do produto. Grafias variáveis para o mesmo item ao longo dos meses. | **Removido na Etapa 2**, mas **reusado uma vez** na Etapa 3 (lookup `produto_cod → produto_nome` a partir do CSV da Etapa 1) para casar as regras de taxonomia. |

### 2.4 Valores (todos com **vírgula decimal**, padrão BR)

| # | Campo | Tipo | Faixa observada | Descrição | Uso no pipeline |
| --- | --- | --- | --- | --- | --- |
| 13 | `qtdade` | decimal | −55 … 20.000 · **44 negativas, 836 zeros** · 2.279 fracionárias | **Quantidade vendida** do item. Fracionária para grama/terra vendidas por m²/kg. Negativa = devolução/estorno. | **VARIÁVEL-ALVO** — somada por dia × `unidade × categoria` (L1) e por dia × SKU (L2). Linhas `qtdade <= 0` **NÃO** são tratadas neste pipeline — a limpeza é responsabilidade do `domain/etl/normalizer.py` de produção (ver §6 do doc de pré-processamento). |
| 14 | `vl_unit` | decimal | 0 … 105.378 · 836 zeros | Preço unitário. | Mantido até a Etapa 3 — matéria-prima de features de preço/desconto (Fase 3 do plano de experimentos, **não** obrigatórias no baseline). |
| 15 | `vl_total` | decimal | −2.200 … 105.378 | `qtdade × vl_unit` antes do desconto. | Idem. Também compõe `DUPLICATE_KEY_FIELDS`. |
| 16 | `vl_desconto` | decimal | −229 … 13.702 · **74% zeros** | Desconto aplicado à linha. | Idem (feature de preço, Fase 3). |
| 17 | `tot_liq` | decimal | −2.200 … 91.676 · sem zeros | Total líquido da **linha** (`vl_total − vl_desconto`). | Reconferência de integridade do documento (soma das linhas ≈ `total_liquido_doc`). |
| 18 | `icms_ret` | decimal | **constante = 0** | ICMS retido da linha. Zero em 100% das linhas nesta base. | **Removido na Etapa 2** — variância nula, zero informação. |
| 19 | `total_liquido_doc` | decimal | −3.245 … 154.200 · 38.803 zeros | Total líquido do **documento inteiro**, repetido em todas as suas linhas. | Reconferência de integridade (o "teste do documento 995" — §2 do doc de pré-processamento). |

### 2.5 Rastreabilidade

| # | Campo | Tipo | Distintos | Descrição | Uso no pipeline |
| --- | --- | --- | --- | --- | --- |
| 20 | `arquivo_origem` | texto | 26 | Nome do XLSX de onde a linha foi extraída (`abril 24.xlsx`). | **Removido na Etapa 2** — redundante com `emissao`; a rastreabilidade de origem vive no `processamento_log.json`. |

---

## 3. Como o relatório é gerado (o que sabemos e o que falta confirmar)

**Sabemos** (por inspeção dos dados):

- Layout de coluna **estável** nos 26 meses — o parser lê por índice fixo.
- Um documento pode ter **a mesma linha de produto repetida** legitimamente (item
  escaneado 2× no caixa) — a soma das linhas fecha com `total_liquido_doc`.
- Relatórios mensais têm **sobreposição de datas nas bordas** do mês (mesmo
  documento exportado em dois meses) — tratado pela deduplicação entre arquivos.
- O relatório inclui pagamentos **`A PRAZO`, `BOLETO`, `VALE`** e devoluções
  (`qtdade` negativa) — ou seja, **não é só venda à vista quitada**.

**Falta confirmar com a parceira** (ver
[`docs/eda_report.md` §6](../eda_report.md)):

1. `fev/2026` (`fev 26.xlsx`) é **mês fechado** ou export parcial? (9.352 linhas —
   compatível com fev/2024 = 9.259 e fev/2025 = 11.437; **aparenta completo**, mas
   confirmar para não truncar a ponta da série de treino.)
2. O relatório "Contas a Receber" captura **100% das saídas de mercadoria**, ou só
   as que geram um título financeiro? (Ex.: brinde, bonificação, consumo interno,
   ajuste de inventário entrariam?)
3. Há algum tipo de documento (`doc_tipo`) que **não** seja venda real e deva ser
   excluído da série de demanda (além de `Servico e taxa`)? Ex.: `CN`/`NN` =
   condicional/devolução?
4. `qtdade` negativa (44 linhas) — são sempre devoluções? Devem **abater** a
   demanda do dia da devolução, do dia da venda original, ou serem ignoradas?

---

## 4. Arquivos

| Arquivo | Papel |
| --- | --- |
| `ia-predictor/data/raw/*.xlsx` | 26 relatórios brutos (entrada, só leitura) |
| `ia-predictor/data/processed/contas_a_receber.csv` | Base consolidada (Etapa 1) — **este dicionário** |
| `ia-predictor/training_scripts/output/contas_a_receber_taxonomia.csv` | + `unidade`/`categoria`/`categoria_fina` (Etapa 3) |
| [`docs/prediction/01-pre_processing.md`](../prediction/01-pre_processing.md) | Racional de cada decisão de parsing / remoção de coluna |
| [`docs/prediction/ADR-010-exogenas-nominais-fora-do-l1.md`](../prediction/ADR-010-exogenas-nominais-fora-do-l1.md) | Por que `pagamento`/`vendedor` saem e `empresa` fica |
