# 003 — Análise 3: vale abrir "Produtos de jardim" em Plantas e Insumos?

> Explicação em linguagem simples da terceira etapa da EDA.
> Detalhes técnicos: [00-eda_report.md](../00-eda_report.md) §3.10. Script: `eda_grupos.py`.

---

## 1. A pergunta desta análise

O cliente organiza o catálogo em quatro grupos: Grama, Flores de corte, **Plantas diversas** (todas as plantas,
exceto flores de corte e árvores) e **Insumos e acessórios** (terra, adubo, vasos, seixos, ferramentas).

O modelo trabalha com **três** categorias. Plantas e insumos ficam juntos em "Produtos de jardim".

> **Separar Plantas diversas e Insumos e acessórios melhora a previsão, ou basta mostrá-los como grupos do painel?**

Produtos de jardim é o maior volume (52%). Se a separação valesse a pena, ela tinha peso.

## 2. Como foi feito

O teste seguiu três perguntas, em ordem. Só se passa para a próxima se a anterior for favorável.

### Pergunta 1 — As séries separadas são densas o bastante para ter modelo próprio?

| Grupo | Dias com venda | Dias úteis sem venda |
|---|---|---|
| Plantas diversas (Jardim Canadá e Itabirito) | 650 · 653 | 4,0% |
| Insumos e acessórios (Jardim Canadá e Itabirito) | 650 · 653 | 4,0% |

**Resposta: sim.** Tecnicamente nada impede a separação.

### Pergunta 2 — Os grupos se comportam de forma diferente?

- **Flores de corte** é a mais distinta: pico na sexta, sábado forte e datas comemorativas de sinal oposto.
  A correlação diária dela com qualquer outro grupo é de no máximo 0,19.
- **Plantas e Insumos** são o par mais parecido (correlação 0,46 e 0,53, contra 0,30 ou menos nos demais
  pares). Mas há diferenças: em Itabirito, Plantas sobe no Dia dos Namorados (2,4×) e em Finados (2,9×), e Insumos
  fica perto da média.

**Resposta:** diferem em alguns pontos, mas não muito.

### Pergunta 3 — Um modelo próprio erra menos do que prever o total e repartir?

Este é o teste decisivo, e foi desenhado para ser justo.

| Elemento do teste | Escolha |
|---|---|
| Janelas | **26 janelas consecutivas de 14 dias** (um ano inteiro, incluindo todas as datas comemorativas) |
| Comparação | Modelo próprio de cada grupo **×** previsão de Produtos de jardim repartida pelo peso recente do grupo |
| Régua do erro | **MASE**: compara o erro do modelo com o de "repetir a semana anterior". Abaixo de 1, o modelo é melhor |
| Robustez | Repetido com **dois modelos de famílias diferentes** (SARIMAX e suavização exponencial), para a conclusão não depender de um só |
| Regra de decisão | **Fixada antes de ver os números**: só separar se o modelo próprio ganhar **pelo menos 5% em cada grupo e em cada unidade** |

Fixar a regra antes evita o viés comum de olhar o resultado e depois ajustar o critério ao que se quer.

## 3. Resultado

MASE (menor é melhor). "Repartido" é a previsão do total dividida pelo peso do grupo:

| Grupo | Modelo | Jardim Canadá: próprio · repartido | Itabirito: próprio · repartido |
|---|---|---|---|
| Plantas diversas | SARIMAX | 0,551 · 0,526 | 0,939 · 0,945 |
| Plantas diversas | Suav. exp. | 0,610 · 0,586 | 0,898 · 0,898 |
| Insumos e acessórios | SARIMAX | 0,618 · 0,697 | 0,868 · 0,924 |
| Insumos e acessórios | Suav. exp. | 0,680 · 0,769 | 0,887 · 0,876 |

**Como ler:**

- **Plantas diversas (41% do volume):** o modelo próprio não ganha. A repartição erra igual, ou até 5% menos.
- **Insumos e acessórios (10% do volume):** o modelo próprio ganha 11% em Jardim Canadá, mas em Itabirito o
  ganho de 6% com SARIMAX vira uma **piora de 1%** com a suavização. O resultado não é consistente.
- **A regra dos 5% não foi atendida** com nenhum dos dois modelos. O menor ganho foi −4,8% (SARIMAX) e −4,0%
  (suavização).

### Árvores

Uma estimativa por palavra-chave (299 produtos: ipê, oliveira, cítricos, palmeiras, ciprestes) mostrou que as
árvores são **0,4% do volume em Jardim Canadá e 1,2% em Itabirito**. A série é densa, mas pequena. Não sustenta
uma categoria própria e fica dentro de Plantas diversas.

## 4. O que foi decidido e em que se baseou

| Decisão | Baseada em |
|---|---|
| **Manter 3 categorias** (Grama, Flores de corte, Produtos de jardim) | Regra dos 5% não atendida nos dois modelos |
| Mostrar Plantas e Insumos como **grupos do painel**, somando a previsão dos produtos de cada um | Sem custo de modelo e sem perda de acerto |
| Árvores dentro de Plantas diversas | Só 0,4% a 1,2% do volume |
| **Reavaliar Insumos** com mais histórico | O ganho de 11% em Jardim Canadá pode ser real, mas com 26 meses de dados não se repete nas duas unidades |

## 5. Perguntas que ficaram abertas

- Quais produtos fazem parte de "Plantas diversas" e "Árvores" no sistema do cliente?
- O nome "Insumos e acessórios" está correto? (O rótulo é provisório.)
- Vale revisar à mão o 1,3% do volume que caiu na categoria "Outros"? (Isso afeta só a repartição por produto.)
