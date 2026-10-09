# 004 — Análise 4: vale prever cada unidade e cada categoria separadamente?

> Explicação em linguagem simples da quarta etapa da EDA.
> Detalhes técnicos: [00-eda_report.md](../00-eda_report.md) §3.11 e ADR-011 §4. Script: `eda_separacao.py`.

---

## 1. A pergunta desta análise

Até aqui o modelo previa **6 séries**: 2 unidades × 3 categorias. Cada uma com seu próprio modelo.

> **Cada nível de separação se paga? Prever cada parte com um modelo próprio erra menos do que prever o total e repartir?**

Menos modelos significa menos trabalho de ajuste e validação, além de menos risco de falhas. Mas menos
modelos só vale se a previsão não piorar.

## 2. Como foi feito

O desenho é o mesmo da Análise 3.

| Elemento | Escolha |
|---|---|
| Janelas | 26 janelas consecutivas de 14 dias (um ano inteiro) |
| Comparação | Modelo **próprio** da parte × previsão do **total** repartida pelo peso recente da parte |
| Régua do erro | MASE (abaixo de 1 = melhor que repetir a semana anterior) |
| Modelos | SARIMAX e suavização exponencial, para a conclusão não depender de um só |
| Regra de decisão | Ganho mínimo de **5%** nos dois modelos, aplicada a cada parte |
| Teste extra | Nas **7 janelas com data comemorativa**, Flores de corte com modelo próprio também não erra menos? |
| Teste inverso | A **soma das partes** erra menos que o modelo do agregado? |

A ideia central é a **previsão hierárquica top-down**: prever o total com bastante dado e repartir pela fatia
histórica de cada parte. O outro caminho seria prever cada parte e somar (*bottom-up*).

## 3. Resultado

MASE, "próprio × repartido" com SARIMAX:

| Parte | Peso no total | Próprio × repartido | Ganho do próprio (SARIMAX · suav.) |
|---|---|---|---|
| Itabirito | 33,6% | 1,434 × 1,736 | +17% · +11% |
| Jardim Canadá | 66,4% | 0,659 × 0,829 | +21% · −11% |
| JC · Grama | 46,7% | 0,794 × 0,807 | +2% · +2% |
| JC · Flores de corte | 1,4% | 0,696 × 0,699 | +0% · −17% |
| JC · Produtos de jardim | 52,0% | 0,550 × 0,532 | −3% · −2% |
| Itabirito · Grama | 46,6% | 1,715 × 1,886 | +9% · −1% |
| Itabirito · Flores de corte | 2,5% | 0,811 × 0,893 | +9% · +4% |
| Itabirito · Produtos de jardim | 51,0% | 0,954 × 0,895 | −7% · −12% |

### Leitura

- **Por unidade: apoiado, mas não por unanimidade.**
  - Itabirito ganha com modelo próprio nos dois modelos (+17% e +11%). A tendência dele é oposta à de Jardim
    Canadá.
  - Jardim Canadá ganha 21% com SARIMAX, mas perde 11% com suavização.
  - Somar os modelos das duas unidades melhora o total da rede em 22% com SARIMAX e empata com suavização.
- **Por categoria: não melhora.**
  - Nenhuma das 6 partes atende a regra dos 5%.
  - Os ganhos vão de −7% a +9% (SARIMAX) e de −17% a +4% (suavização).
  - A soma das três categorias fica a menos de 5% do modelo da unidade.
  - Nas janelas com datas comemorativas, Flores de corte com modelo próprio **também não** erra menos
    (0,85 × 0,77 em Jardim Canadá; 1,18 × 1,09 em Itabirito).

As diferenças de comportamento entre categorias (a Análise 2 mostrou que são reais) existem, mas com dois
anos de dados **não viram previsão melhor**.

### Cuidados

- Em Itabirito, vários valores passam de 1, ou seja, pior que repetir a semana anterior. A causa são os
  pedidos gigantes (encomendas grandes; tratamento em aberto).
- Diferenças de até cerca de 10% estão dentro do ruído.
- 2 dos 234 ajustes SARIMAX não convergiram. A ordem do SARIMAX no teste é fixa.

## 4. O que foi decidido e em que se baseou

| Decisão | Baseada em |
|---|---|
| **O modelo principal (L1) prevê 2 séries, uma por unidade**, em vez de 6 | Nenhuma categoria ganha os 5% mínimos. A soma das categorias fica a menos de 5% do modelo da unidade |
| Manter a separação **por unidade** | Ganho em Itabirito nos dois modelos e tendências opostas entre as unidades |
| **Categoria** e produto passam a ser obtidos por **repartição em cascata** (unidade → categoria → produto) | Prever categoria direto não melhora a acurácia |
| Repartir usando o **efeito de data comemorativa da própria categoria**, não só a fatia histórica | A Análise 2 mostrou que o agregado esconde o pico de flores |
| Manter as 6 séries unidade × categoria como insumo da repartição | Elas continuam úteis para calcular as fatias |

### Por que o efeito de data por categoria importa na repartição

Exemplo na véspera do Dia das Mães, em Jardim Canadá:

- A unidade **cai** para 0,66× (grama e jardim vendem menos). Suponha 250 unidades em vez de 380.
- Repartir só pela fatia histórica (1,4%) daria cerca de 3,5 unidades de flores.
- Mas flores **disparam 2,14×** nessa data, e o cálculo correto dá cerca de 11 unidades: mais que o dobro de
  um dia comum, mesmo com o total da unidade menor.

Por isso a repartição usa a fatia móvel, o perfil de dia da semana **e** o índice de data da categoria.

## 5. Efeito prático

- **4 modelos a menos** para ajustar e validar.
- **Acurácia equivalente** à de 6 modelos.
- **Base acadêmica:** previsão hierárquica top-down (Fliedner 2001; Gross e Sohl 1990, que mostram que a
  proporção média histórica é simples e muito precisa; Zotteri e Kalchschmidt 2007, sobre o nível certo de
  agregação com poucas observações).
