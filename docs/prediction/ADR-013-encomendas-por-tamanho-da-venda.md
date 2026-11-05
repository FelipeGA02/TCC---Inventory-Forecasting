# ADR-013 — Encomenda é tamanho da venda, não tipo de cliente nem outlier de linha

**Status:** aceito; o limiar de 2.000 un. foi revisado pelo ADR-018 (média + 4 desvios-padrão) · **Data:** 2026-10-13 · **Revisa:** ADR-012 (encomendas grandes fora do L1)
**Afeta:** `training_scripts/preprocessing/remove_encomendas_06.py`, Etapa 6 do pré-processamento

---

## 1. O problema

A previsão diária do L1 falha num punhado de dias. Medido em Itabirito, no walk-forward de
351 origens com horizonte de 14 dias:

- **18 dias (5% do período) concentram 61,8% de todo o erro** do modelo com `log1p`;
- nesses dias o erro médio é de **22.957 unidades**; nos outros 346 dias, de **769**;
- e esses 18 dias somam **50,6% de todo o volume vendido** no período de teste.

O modelo é bom no dia a dia — 769 unidades de erro numa série de mediana 909 — e inútil
nesses 18 dias. Qualquer ganho relevante tem de vir daí.

Esses dias têm uma causa concreta: **vendas isoladas muito grandes**. A venda típica da
loja é de 3 unidades (mediana de 58.622 documentos), p99 = 200. Mas 93 vendas acima de
2.000 unidades — **0,16% das vendas** — respondem por 52,1% do volume. O maior dia da
série, 16/12/2025, tem 62.595 unidades, das quais uma única venda responde por 61.172.

Essas vendas não são ruído a limpar: são demanda real que a loja precisa atender. Mas são
um **evento de logística**, não fluxo de balcão — a loja não as atende do estoque, precisa
encomendar do fornecedor. E, do ponto de vista estatístico, não há sinal no histórico da
série que anuncie em que dia uma obra vai fechar um pedido.

## 2. Decisão

Separar cada loja em **dois fluxos**, pelo tamanho da **venda inteira** (documento):

```
venda (unidade × emissao × doc_tipo × doc_numero) com soma de qtdade > 2.000 un  →  encomenda
caso contrário                                                        →  fluxo diário
```

O tipo do documento entra na chave desde 2026-10-27: cada tipo (cupom, nota…) tem a própria
numeração, e em 12 casos da base o mesmo número sai no mesmo dia em dois tipos — vendas
diferentes que a chave sem o tipo somava (nenhuma marcação mudou na base de 2026-02).

Os dois são gravados. **Não é descarte**: o fluxo diário vai para o SARIMAX, as encomendas
viram um fluxo próprio, e a previsão entregue é a soma.

A unidade de decisão é a venda, não a linha, porque uma encomenda chega como um documento
com várias linhas (grama, substrato, mudas). Olhar linha a linha quebra o evento em pedaços
que individualmente parecem normais — e, ao mesmo tempo, marca como encomenda a linha
avulsa de um cliente de balcão que levou um pouco mais que a mediana da categoria.

## 3. Alternativas descartadas

### 3.1 `cliente_cod` — cadastrado × `CONSUMIDOR`

Descartado: a loja confirmou (2026-10-09) que cliente cadastrado **não** é sinônimo de
encomenda. Quem faz cadastro muitas vezes é cliente comum, e deve ser previsto junto com o
balcão. "Fez cadastro" é um fato administrativo, não uma categoria de demanda.

### 3.2 z-score modificado por linha (Iglewicz & Hoaglin, 1993)

Era o critério vigente: `M_i = 0,6745 · (log1p(qtdade) − mediana) / MAD` por
`unidade × categoria`, outlier se `|M_i| > 3,5`. O método é robusto e bem fundamentado — o
problema não é o estimador, é a **unidade de análise**.

Classificando pela quantidade da linha, sem saber a que venda ela pertence, ele erra nos
dois sentidos. Medido na base de 2026:

| | Hampel por linha | Regra por venda |
| --- | --- | --- |
| Volume de `CONSUMIDOR` tirado do fluxo diário (Itabirito) | **21,6%** | **2,7%** |
| Idem, Jardim Canadá | **22,2%** | **3,7%** |
| Volume classificado como encomenda (Itabirito) | 61,2% | 52,1% |
| CV da série diária do fluxo (Itabirito) | 1,04 | **0,78** |
| CV da série diária do fluxo (Jardim Canadá) | 0,87 | **0,69** |

Ou seja: tira mais volume, contamina 8× mais o balcão que se quer prever, e ainda deixa a
série resultante mais irregular. É dominado em todas as dimensões.

A função `marcar_outliers` **permanece no módulo**, usada apenas para registrar essa
comparação no resumo de cada execução, de modo que a decisão continue auditável.

## 4. Evidência — sensibilidade ao limiar

Base de 2026, as duas lojas. "cons. tirado" é quanto do volume de `CONSUMIDOR` sai do fluxo
diário, isto é, a contaminação do que se quer prever:

**Itabirito** (série total: CV 2,35 · máx. 62.595)

| Regra | Vendas | Vol. encomenda | CV do fluxo | Máx. do fluxo | Cons. tirado |
| --- | --- | --- | --- | --- | --- |
| venda > 500 | 225 | 60,2% | 0,66 | 2.828 | 6,1% |
| venda > 1.000 | 128 | 55,5% | 0,71 | 3.521 | 4,0% |
| **venda > 2.000** | **93** | **52,1%** | **0,78** | **4.610** | **2,7%** |
| venda > 3.000 | 70 | 48,4% | 0,86 | 5.051 | 2,1% |
| venda > 5.000 | 47 | 42,1% | 1,08 | 10.446 | 0,0% |
| *Hampel por linha* | *—* | *61,2%* | *1,04* | *7.036* | *21,6%* |

**Jardim Canadá** (série total: CV 1,18 · máx. 73.671)

| Regra | Vendas | Vol. encomenda | CV do fluxo | Máx. do fluxo | Cons. tirado |
| --- | --- | --- | --- | --- | --- |
| venda > 500 | 790 | 42,9% | 0,62 | 6.096 | 16,1% |
| venda > 1.000 | 309 | 30,9% | 0,66 | 8.608 | 7,7% |
| **venda > 2.000** | **131** | **22,5%** | **0,69** | **11.392** | **3,7%** |
| venda > 3.000 | 76 | 17,7% | 0,72 | 13.494 | 2,9% |
| venda > 5.000 | 34 | 12,1% | 0,77 | 15.782 | 2,5% |
| *Hampel por linha* | *—* | *34,8%* | *0,87* | *13.566* | *22,2%* |

Em **todos** os limiares testados a regra por venda deixa o fluxo diário com CV menor e
contamina menos o balcão que o critério anterior.

O limiar de 2.000 foi escolhido como ponto de equilíbrio: abaixo dele a regra começa a
engolir venda de balcão (em Jardim Canadá, 500 já tira 16,1% do consumidor); acima, a série
do fluxo volta a ficar irregular (em Itabirito, 5.000 devolve o CV para 1,08). **É uma
escolha nossa, não dos dados** — ver §6.

## 5. Consequências

**Para o L1.** O alvo do SARIMAX passa a ser o fluxo diário, com CV 0,78 (Itabirito) e 0,69
(Jardim Canadá), contra 2,35 e 1,18 da série total. É o regime em que o modelo funciona, e
deve melhorar bastante o MAE de 1.906 medido na série total.

**Para o entregável.** A previsão não cobre mais 100% do volume sozinha. O sistema precisa
somar as encomendas conhecidas — que a loja sabe com antecedência — à previsão do fluxo.
Isso é uma mudança de produto, não só de modelagem: pede um campo de entrada de encomenda
prevista.

**Para a série de encomendas.** Em Itabirito ela tem 707 dias zerados em 789 e mediana 0:
é demanda intermitente, e SARIMAX não se aplica. Também não é claro que precise de modelo —
são 93 eventos em 2 anos, conhecidos de antemão pela loja.

**Para a validação.** O limiar é **fixo em unidades**, não estimado dos dados. Por isso não
precisa ser recalculado a cada rodada do walk-forward e não há risco de vazamento — ao
contrário da regra do ADR-012 (`> 5 × mediana diária`), que era derivada dos dados e exigia
recálculo por rodada.

**Novos arquivos.** A Etapa 6 passa a gravar dois CSVs por loja:
`BaseTreino_<slug>_sem_encomendas.csv` (fluxo diário) e `BaseTreino_<slug>_encomendas.csv`.

## 6. O que ainda depende da parceira

O limiar de 2.000 unidades é uma **hipótese operacional**, derivada dos quantis da
distribuição. A pergunta a fazer é de negócio, não de estatística:

> A partir de quantas unidades vocês precisam encomendar do fornecedor, em vez de atender
> do estoque da loja?

É provável que o número **varie por categoria** — 2.000 mudas de grama e 2.000 flores de
corte não são o mesmo problema logístico. O parâmetro `LIMIAR_POR_CATEGORIA` já existe no
módulo para acomodar isso assim que houver resposta; vazio, todas as categorias usam o
limiar geral.

Enquanto não houver essa confirmação, o número deve ser apresentado no artigo como escolha
justificada por sensibilidade, nunca como parâmetro calibrado.

## 7. Referências

- Iglewicz, B.; Hoaglin, D. C. *How to Detect and Handle Outliers.* ASQC Basic References
  in Quality Control, v. 16, 1993 — o z-score modificado, critério anterior.
- ADR-012 — encomendas grandes fora do L1 (regra `> 5 × mediana diária`, por linha).
- `CLAUDE.md`, seção L1 "Vendas grandes" — a confirmação da loja de 2026-10-09.
