# 001 — Análise 1: a base bruta e o critério de Syntetos, Boylan e Croston

> Explicação em linguagem simples da primeira etapa da EDA (análise exploratória).
> Detalhes técnicos completos: [00-eda_report.md](../00-eda_report.md) §1–2 e
> [01-pre_processing.md](../01-pre_processing.md).
> Scripts: `eda_source.py` (base bruta) e `eda_classificacao_sku.py` (critério de Syntetos).

---

## 1. A pergunta desta análise

> **O que a floricultura nos entregou, com que qualidade, e dá para prever a venda produto por produto?**

Antes de qualquer modelo, é preciso conhecer os dados. Esta etapa olha a base **como ela chegou**, sem
agrupar nada, e decide quais informações servem e qual deve ser o "tamanho" da previsão.

## 2. O que chegou

26 planilhas mensais (jan/2024 a fev/2026) de um relatório chamado "Contas a Receber". Ele foi feito
para uma pessoa ler, não para um programa. Um programa converteu tudo em uma tabela única, em que
cada linha é **um produto dentro de uma venda**.

| Métrica | Valor |
|---|---|
| Linhas (documento × produto) | 333.019 |
| Vendas (documentos) distintas | 130.728 |
| Produtos distintos | 5.166 |
| Período | 02/01/2024 a 28/02/2026 |
| Dias com venda | 654 de 789 (o resto é domingo e feriado, loja fechada) |

## 3. Como a qualidade foi verificada

| Verificação | Resultado |
|---|---|
| Faltam meses? | Não. 26 de 26 meses presentes |
| Problema de acentuação? | Não |
| Datas interpretadas corretamente? | Sim, todas |
| Quantidade zero ou negativa | 880 linhas (0,3%): 836 zeros e 44 negativas (provável devolução) |
| Quantidades fracionadas | Esperado (grama e terra vendidas por m² ou kg) |
| Soma dos itens = total da venda? | Em cerca de 90% dos documentos. O resto vem de frete e serviço cobrados à parte |

### Um erro que foi descoberto e corrigido: "duplicatas" que não eram duplicatas

A primeira regra removia linhas com o mesmo número de venda e o mesmo produto. Ela sinalizou 201
"duplicatas" em um único mês. Foi feita uma prova:

- O documento `995` tem duas linhas do mesmo produto (`433NL`), ambas com quantidade 3 e valor 6.
- A soma das 12 linhas do documento bate **exatamente** com o total impresso no relatório (756,30).
- Se uma das duas fosse removida, o total seria 750,30 e não bateria.
- Conclusão: o item foi bipado duas vezes no caixa. **As duas são vendas reais.**

**Decisão:** a remoção passou a comparar só linhas de **arquivos diferentes** (o mesmo documento exportado
no fim de um mês e no começo do seguinte). Também passou a exigir data, quantidade e valor idênticos.
Resultado real: 0 duplicatas. A regra continua no código para o caso de um lote futuro ter meses
sobrepostos.

## 4. O que foi mantido e o que foi descartado

O relatório tinha 20 colunas. O critério para cada uma foi: **isso muda a resposta de "quanto vai ser vendido amanhã"?**

| Decisão | Colunas | Por quê |
|---|---|---|
| Mantidas (9) | data, empresa, código do produto, quantidade, valores | São o que se prevê e o que pode ajudar a explicar |
| Descartadas (11) | forma de pagamento, vendedor, operador, cliente, observações, tipo/número do documento etc. | Ou **só existem depois** da venda (não dá para usar para prever o futuro), ou são dados pessoais, ou são texto livre sem valor |
| Criadas (3) | unidade, categoria, subcategoria | A base original não tem essas dimensões |

Pagamento e vendedor merecem destaque. "Como o cliente vai pagar amanhã" é desconhecido no momento da
previsão. Usar essa informação seria "trapaça de dados" (*data leakage*): o modelo pareceria bom nos testes e
não funcionaria na prática.

As 3 empresas (CNPJs) viraram **2 unidades**: Jardim Canadá (que inclui o Garden Center) e Itabirito.
Isso foi confirmado com o cliente.

## 5. Como é o negócio, de acordo com os números

| Categoria | Participação no volume | Produtos distintos |
|---|---|---|
| Produtos de jardim | 51,5% | 5.062 |
| Grama | 46,6% | 14 |
| Flores de corte | 1,7% | 88 |

A Verde Perto funciona mais como **garden center e jardinagem** do que como floricultura de flores de
presente. Grama é quase metade do volume com só 14 variedades. Produtos de jardim é o oposto: mais de 5 mil
itens, cada um vendendo pouco.

Poucos produtos concentram o volume (**curva de Pareto**): 7 produtos somam metade de tudo, os 20 maiores
somam 61,7% e os 100 maiores somam 81,6%.

## 6. O problema central: produto por produto é inviável

- O produto típico vendeu em **9 dos 789 dias**.
- Mais da metade dos produtos vendeu em 1,1% dos dias, ou menos.
- 13,2% dos produtos venderam **uma única vez** em mais de dois anos.
- 72,2% não têm histórico para receber uma previsão própria confiável.

Um produto típico se parece com `0, 0, 0, 2, 0, 0, 0, 0, 1, 0...`. Um modelo estatístico como o SARIMAX
precisa de uma série contínua para descobrir o padrão semanal e a tendência. Numa série quase toda zerada,
ele não encontra padrão.

Mas "achar que não dá" não é argumento acadêmico. Por isso entra o critério da literatura.

---

## 7. O critério de Syntetos, Boylan e Croston (2005)

### O problema que ele resolve

Cada método de previsão funciona melhor em um tipo de venda.

- **Vende todo dia:** métodos que "suavizam" o histórico, como o SARIMAX, funcionam bem.
- **Vende raramente:** esses métodos erram para os dois lados. No dia sem venda "acham" que vai vender um
  pouco, e no dia com venda "acham" que vai vender pouco.

Para vendas raras, Croston (1972) criou outro método. Ele separa duas perguntas: **de quanto em quanto tempo**
o produto vende, e **quanto** vende quando vende. TSB e SBA são versões corrigidas do método de Croston.

O artigo de 2005 responde à dúvida "qual método usar em cada série?" com um critério objetivo, que olha só o
histórico de vendas.

### Os dois números do critério

1. **ADI (intervalo médio entre vendas):** dias do período ÷ dias com venda. ADI = 3 significa uma venda a
   cada 3 dias, em média.
2. **CV² (variabilidade do tamanho da venda):** o quanto a **quantidade** muda de uma venda para outra,
   calculado **só nos dias em que houve venda**. CV² alto significa que um dia vende 2 e outro vende 200.

### Os quatro grupos

Os autores derivaram, matematicamente, os pontos de corte **ADI = 1,32** e **CV² = 0,49**.

| | **Quantidade estável** (CV² < 0,49) | **Quantidade instável** (CV² ≥ 0,49) |
|---|---|---|
| **Vende quase todo dia** (ADI < 1,32) | **Suave**: SARIMAX funciona bem | **Errática**: SARIMAX funciona, com suavização (`log1p`) |
| **Vende raramente** (ADI ≥ 1,32) | **Intermitente**: Croston é melhor | **Lumpy**: pior caso, Croston é melhor |

## 8. Como foi aplicado

1. Foram pegos os **5.162 produtos físicos** (fretes e taxas ficaram de fora).
2. Para cada produto, calculou-se ADI e CV² no período dele, do **primeiro ao último dia com venda**. Assim
   um produto lançado há dois meses não é penalizado por meses em que não existia.
3. Cada produto foi colocado em um dos quatro quadrantes (gráfico `24_classificacao_demanda_sku.png`).
4. **692 produtos (13,4%) venderam em um único dia.** O CV² não pode ser calculado, e ficaram sem classificação.

### Resultado (4.470 produtos classificáveis)

| Classe | % dos produtos | % do volume |
|---|---|---|
| Suave | 0,2% | 0,0% |
| Errático | 0,5% | 53,7% |
| Intermitente | 52,2% | 1,4% |
| **Lumpy** | **47,1%** | **44,9%** |

**99,3% dos produtos caem em intermitente ou lumpy**, os dois grupos em que a literatura desaconselha o
SARIMAX em favor de Croston, TSB ou SBA.

### O teste na direção oposta: e as séries agregadas?

O mesmo critério foi aplicado às séries somadas por unidade, que são as que o modelo principal vai prever.

| Série | ADI | CV² | Classe |
|---|---|---|---|
| Jardim Canadá | 1,21 | 0,67 | Errática |
| Itabirito | 1,21 | 4,58 | Errática |

As duas vendem quase todo dia útil (ADI 1,21 < 1,32). Estão no quadrante em que o SARIMAX é apropriado. As 6
séries de unidade × categoria também caem em errática.

## 9. O que foi decidido e em que se baseou

| Decisão | Baseada em |
|---|---|
| **Não** prever produto por produto com SARIMAX | 72% sem histórico suficiente; 99,3% intermitente/lumpy pelo critério de Syntetos |
| Prever o **total da unidade** e **repartir** entre categorias e produtos | Somar move a série do quadrante errado para o certo |
| Manter Croston/TSB/SBA como trilha de comparação no nível de produto | O critério os indica para esse tipo de série |
| Focar o detalhe nos 20 produtos de maior giro | Curva de Pareto (62% do volume). A lista muda com o tempo, então não é fixa |
| Descartar pagamento, vendedor e dados pessoais | Não existem no futuro, ou privacidade |
| Manter as linhas "duplicadas" do mesmo documento | Prova do documento `995` |

## 10. Perguntas que ficaram abertas para a floricultura

- Fevereiro/2026 é um mês fechado ou um recorte parcial?
- As 44 quantidades negativas são sempre devolução? Em que dia devem ser descontadas?
- O relatório captura 100% das saídas (brindes, consumo interno)? Algum tipo de documento não é venda real?
