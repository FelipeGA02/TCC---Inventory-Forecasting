# 005 — Análise 5: encomendas grandes e o erro alto de Itabirito

> Explicação em linguagem simples da quinta etapa da EDA (2026-09-23).
> Detalhes técnicos: [00-eda_report.md](../00-eda_report.md) §3.12 e
> [ADR-012](../ADR-012-encomendas-grandes-fora-do-l1.md). Script: `eda_encomendas.py`.

---

## 1. A pergunta desta análise

Depois da Análise 4, o modelo previa 2 séries (uma por unidade). Uma delas ia bem e a outra não:

| Unidade | Erro (MASE) |
|---|---|
| Jardim Canadá | 0,659 (bom) |
| **Itabirito** | **1,434 (pior que repetir a semana anterior)** |

> **Por que Itabirito erra tanto, e dá para corrigir?**

MASE acima de 1 significa que o modelo é pior que a previsão mais ingênua possível.

## 2. O diagnóstico

O problema não estava no modelo, e sim no **tipo de venda**.

Em Itabirito, a Grama vende cerca de 200 m² num dia comum. Mas algumas linhas de venda sozinhas têm 12.800,
19.200 ou 20.000 m².

| Indicador | Itabirito | Jardim Canadá |
|---|---|---|
| Os 10 maiores dias, como % da Grama vendida | 43,6% | 8,6% |
| Cliente responsável por 32 das 40 maiores linhas | Um único cliente | — |
| Forma de pagamento dessas linhas | Boleto | — |

São **encomendas** de obra ou paisagismo, combinadas com antecedência. Não são a venda de balcão que o
calendário explica. Nenhum modelo de série temporal consegue adivinhar em que dia uma encomenda vai cair.

## 3. A regra criada

> Uma linha de venda é **encomenda** quando, sozinha, vale mais do que **5 dias típicos** de venda daquela
> unidade e categoria.

O "dia típico" é a **mediana** do volume diário, de segunda a sábado.

**Por que não usar o percentil 99 das linhas?** Em Produtos de jardim, linhas de 60 a 100 mudas são comuns.
Um percentil marcaria quase metade do volume como encomenda.

| Unidade · categoria | Limite por linha | Linhas marcadas | % do volume |
|---|---|---|---|
| Itabirito · Grama | 1.015 | 68 | 67,7% |
| Itabirito · Produtos de jardim | 3.079 | 8 | 9,1% |
| Itabirito · Flores de corte | 155 | 4 | 4,2% |
| Jardim Canadá · Flores de corte | 160 | 12 | 17,8% |
| Jardim Canadá · Grama | 7.014 | 1 | 1,2% |
| Jardim Canadá · Produtos de jardim | 8.265 | 1 | 1,0% |

**No total: 36,3% do volume de Itabirito (80 linhas) e só 1,3% do de Jardim Canadá (14 linhas).**

### A regra foi conferida com dados que ela não usa

A regra usa só quantidade, unidade, categoria e data. Cliente e forma de pagamento serviram **apenas para
conferir**:

| Perfil | Encomendas | Balcão |
|---|---|---|
| Pagas por boleto (Itabirito) | 65% | 1,4% |
| Cliente "CONSUMIDOR" (Itabirito) | 7,5% | 90,5% |

Isso confirma que são outro tipo de demanda.

## 4. A solução em duas camadas

1. **Separar as encomendas.** Elas saem da série que o modelo prevê e ficam como registro à parte.
2. **Limitar os picos que sobram no balcão.** Dias acima do percentil 99 são rebaixados a esse valor, **só no
   treino** do modelo.

O limite das encomendas e o teto são recalculados em **cada janela do teste**, usando só o passado. Assim não
há vazamento de informação do futuro.

## 5. Como foi testado

As mesmas 26 janelas de 14 dias das análises anteriores, com quatro variantes:

| MASE | Itabirito SARIMAX | Itabirito suav. exp. | Jardim Canadá SARIMAX | Jardim Canadá suav. exp. |
|---|---|---|---|---|
| Como era (total) | 1,434 | 1,311 | 0,659 | 0,727 |
| Só o teto | 1,401 | 1,283 | 0,648 | 0,713 |
| Só separar as encomendas | 0,810 | 0,699 | 0,656 | 0,724 |
| **Separar + teto** | **0,796** | **0,688** | **0,646** | **0,710** |

### Antes × depois em Itabirito

| Indicador | Antes | Depois (balcão + teto) |
|---|---|---|
| Veredito do diagnóstico | atenção | **ok** |
| Variação diária (CV) | 2,39 | 1,11 |
| Maior dia ÷ média | 37,2 | 7,2 |
| Força do ciclo semanal | 0,07 | 0,24 |
| Tendência | +54%/ano | +10%/ano |
| **MASE SARIMAX** | **1,434** | **0,796** |
| Erro percentual (WAPE) | 91,6% | 61,3% |

## 6. O que foi descoberto

1. **Itabirito passa a bater a previsão ingênua** com os dois modelos (0,80 e 0,69). Quem resolve é a
   **separação das encomendas**. O teto sozinho quase não ajuda.
2. **O ciclo semanal estava escondido pelos picos.** Sem eles, fica 3× mais forte, e é exatamente o que o
   SARIMAX usa para prever.
3. **A "tendência de alta de 54% ao ano" era quase toda encomenda.** As encomendas saltaram de 68 mil
   unidades em 2024 para 377 mil em 2025. A venda de balcão cresce cerca de **8% ao ano**.
4. **Jardim Canadá quase não muda** (0,659 → 0,646), o que é esperado com 1,3% de encomendas. A regra não
   estraga uma série que já estava boa.
5. **O resultado não depende do número 5.** Com limite de 3 ou de 10 dias típicos, o MASE de Itabirito fica
   entre 0,79 e 0,80.

## 7. O que foi decidido e em que se baseou

| Decisão | Baseada em |
|---|---|
| **Tirar as encomendas da série do modelo principal** (linha > 5 dias típicos) | MASE de Itabirito de 1,43 para 0,80; resultado estável entre 3 e 10 dias típicos |
| Limitar os picos restantes ao percentil 99, só no treino | Reduz a cauda de 29 para 12,7 (curtose), com ganho pequeno mas consistente |
| Recalcular limites em cada janela, só com o passado | Evita usar informação do futuro |
| A repartição por categoria passa a ser calculada sobre o **balcão** | Consistência com a série que o modelo prevê |
| O painel avisa que **encomendas não estão incluídas** | Transparência para o usuário |

### Apoio na literatura

Separar a demanda regular da demanda de poucos clientes grandes é recomendado por Bartezzaghi e Verganti
(1995), Bartezzaghi, Verganti e Zotteri (1999) e Kalchschmidt, Zotteri e Verganti (2003, 2006). Chen e Liu
(1993) mostram que picos distorcem o ajuste do ARIMA. Hyndman e Athanasopoulos (2021, §13.9) alertam para não
apagar picos sem entender a causa, e por isso aqui as encomendas **não são apagadas**: ficam como registro à
parte. O limite de "5 dias típicos" é uma escolha deste projeto, próxima dos filtros robustos por mediana
(filtro de Hampel).

## 8. Limite honesto

O sistema passa a prever **a venda de balcão, não as encomendas**. Comparada à venda total, a previsão de
Itabirito volta a ter MASE 1,26, porque a encomenda continua imprevisível pelo histórico.

Para prever encomendas seria preciso a **carteira de pedidos já combinados** (orçamento, pedido, agenda de
entrega).

## 9. Perguntas que ficaram abertas

- As vendas grandes de Grama em Itabirito são encomendas sob pedido? Saem do estoque da loja ou são pedidas
  ao fornecedor depois de fechadas?
- Existe algum registro dessas encomendas **antes** da venda? Se existir, ele permitiria incluí-las na
  previsão.
- Os maiores pedidos são vendas reais ou erros de digitação?
