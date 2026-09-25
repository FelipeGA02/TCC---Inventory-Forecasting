# 002 — Análise 2: como as vendas se comportam dia a dia

> Explicação em linguagem simples da segunda etapa da EDA.
> Detalhes técnicos: [00-eda_report.md](../00-eda_report.md) §3.0–3.9.
> Scripts: `eda_series.py` (6 séries unidade × categoria) e `eda_series_unidade.py` (2 séries por unidade).

---

## 1. A pergunta desta análise

> **Como a venda de cada dia se comporta? Existe padrão de dia da semana, de datas comemorativas, de tendência? Os pressupostos do projeto se confirmam?**

A Análise 1 mostrou que produto isolado não dá para prever. Aqui olhamos o **total somado por dia**,
que é o que o modelo de fato vai prever.

## 2. Como foi feita

As vendas foram somadas **por dia**, em dois níveis:

- **Por unidade** (2 séries): Jardim Canadá e Itabirito. Este é o nível que o modelo principal prevê.
- **Por unidade × categoria** (6 séries): serve de insumo para repartir a previsão entre categorias.

Para cada série foram feitas estas medições:

| Medição | O que responde, em linguagem simples |
|---|---|
| Dias com venda e maior sequência sem venda | A série é regular ou cheia de buracos? |
| Coeficiente de variação | O quanto a venda "pula" de um dia para o outro |
| Índice de dia da semana | Cada dia vende mais ou menos que a média? (1,0 = na média) |
| Índice de data comemorativa | Em torno do Dia das Mães, Natal etc., vende mais ou menos? |
| Tendência (primeiros × últimos 90 dias) | A venda está subindo ou caindo? |
| Testes de estabilidade (ADF/KPSS) | A série "anda para longe" sem controle? |
| Autocorrelação (ACF) | Saber quanto vendeu ontem ajuda a prever hoje? E uma semana atrás? |
| Decomposição STL | Separar a série em tendência, ciclo semanal e sobra |
| Dias fora do padrão (mais de 3 desvios) | Existem picos isolados? O que os causa? |
| Estabilidade da participação por produto | A fatia de cada produto na categoria é estável? |

## 3. O que foi descoberto

### 3.1 As séries são regulares

Todas vendem em cerca de 82% dos dias do período. Os dias sem venda são quase todos domingos e feriados,
uma ausência previsível. A maior sequência sem venda é de 3 a 5 dias. Todas têm bem mais que os 180 dias
de histórico mínimo. Isso valida somar por unidade e categoria.

### 3.2 A premissa "fim de semana vende mais" estava errada

Foi comparada a venda de cada dia da semana com a média da série.

- **Domingo:** loja fechada, venda zero.
- **Sábado:** fraco. Grama vende 0,42× a média em Jardim Canadá e 0,14× em Itabirito.
- **Grama:** pico de terça a quarta, compatível com paisagista e obra.
- **Produtos de jardim:** pico de quarta a quinta em Jardim Canadá. Em Itabirito a semana é mais uniforme.
- **Flores de corte:** pico na **sexta** (1,73× e 1,96×) e sábado acima da média, compatível com presente.

É o padrão de um negócio de **jardinagem em dia útil**, não de floricultura de presente. A documentação do
projeto estava com essa premissa errada e foi corrigida.

Ressalva: o ciclo semanal é real, mas explica uma fração pequena da variação total (força entre 0,00 e
0,29, numa escala de 0 a 1). A maior parte da oscilação vem de pedidos grandes pontuais.

### 3.3 Datas comemorativas: o efeito muda de sinal por categoria

Razão contra a média (1,0 = sem efeito):

| Data | Flores de corte | Grama | Produtos de jardim |
|---|---|---|---|
| Dia da Mulher | 4,0 · 4,2 | 0,6 · 0,5 | 0,7 · 0,7 |
| Dia das Mães | 2,1 · 5,0 | 0,8 · 0,2 | 0,5 · 1,0 |
| Dia dos Namorados | 1,7 · 3,8 | 1,2 · 0,6 | 1,1 · 2,2 |
| Finados | 1,1 · 3,1 | 0,7 · 3,3 | 0,7 · 2,6 |
| Natal | 2,1 · 1,1 | 0,6 · 0,5 | 0,4 · 0,5 |

(cada par é Jardim Canadá · Itabirito)

Flores **disparam** e grama **cai**: o cliente troca a compra de grama por flores. A exceção é Finados em
Itabirito, quando a grama sobe (provável jardinagem de cemitério).

**Consequência:** o efeito de cada data precisa ser calculado **por categoria**. Um ajuste único erraria
o sentido em pelo menos uma delas.

No total da unidade, o Dia das Mães **cai** (0,66× e 0,70×), embora as flores disparem. Flores são só 1,4%
do volume em Jardim Canadá, e grama e jardim dominam a média. O agregado esconde o pico das flores.

### 3.4 As unidades têm tendências opostas

| Unidade | Tendência (total) |
|---|---|
| Jardim Canadá | −13% ao ano (Produtos de jardim −23%) |
| Itabirito | +54% ao ano (Grama +96%) |

Pode ser mudança real de demanda, de mix de produtos ou de forma de registrar as vendas. Ficou como
pergunta para a floricultura. (A Análise 5 mostra que boa parte do crescimento de Itabirito era encomenda.)

### 3.5 A "memória" da série é fraca

Saber quanto vendeu **ontem** diz pouco sobre hoje. Existe um eco fraco de uma semana atrás. Em Flores de
corte (Jardim Canadá) e Produtos de jardim (Itabirito) nem esse eco existe. Para elas a previsão depende quase
só do calendário.

### 3.6 Existem picos gigantes isolados

Cada série tem de 4 a 20 dias fora do padrão. Em cinco das seis séries, **uma única linha de venda** responde
por 31% a 96% do dia de pico.

| Exemplo | Detalhe |
|---|---|
| Itabirito · Grama, 16/12/2025 | 61.561 unidades, com uma linha de 19.200 |
| Jardim Canadá · Grama, 08/10/2025 | 15.956 unidades, com uma linha de 15.000 |
| Jardim Canadá · Flores, 30/04/2024 | 3.880 unidades, com uma linha de 1.200 rosas |

O padrão é o de um pedido grande isolado (obra, paisagista). Um erro de digitação teria a mesma aparência,
por isso a confirmação com o cliente ficou como pergunta em aberto. Só dois picos mensais se repetem nos
dois anos: flores em Itabirito em dezembro e grama em Jardim Canadá em outubro. Os demais eram de um único
pedido.

### 3.7 A fatia de cada produto na categoria muda muito de mês a mês

Nenhuma das 6 combinações teve participação estável, mesmo entre os 10 maiores produtos. Por isso a
repartição precisa de uma janela de tempo mais longa, e a média da categoria vira o caminho padrão para a
maioria dos produtos.

## 4. Situação de cada série

| Série | Situação |
|---|---|
| Itabirito · Flores de corte | Boa |
| Jardim Canadá · Grama | Boa |
| Jardim Canadá · Produtos de jardim | Boa (com ajuste de tendência) |
| Itabirito · Produtos de jardim | Atenção (comporta-se como sinal aleatório) |
| Itabirito · Grama | Atenção (pico de 79× a média, tendência muito forte) |
| Jardim Canadá · Flores de corte | Atenção (pico de 86× a média, depende só do calendário) |

"Atenção" não bloqueia a previsão. Ela é gerada com um aviso de menor confiança.

## 5. O que foi decidido e em que se baseou

| Decisão | Baseada em |
|---|---|
| Corrigir a premissa do fim de semana | Índices por dia da semana |
| Dar mais peso ao **dia da semana** no modelo | Ciclo semanal consistente, mas fraco na variância |
| Calcular o efeito de cada data comemorativa **por categoria** | Sinal oposto entre flores e grama |
| Suavizar os picos (`log1p`) em todas as séries | Variação diária alta em todas |
| Incluir na comparação uma abordagem só de regras de calendário | Séries sem "memória" |
| Sinalizar séries extremas com aviso de menor confiança | Picos de 79× e 86× a média |
| Ampliar a janela de repartição entre produtos | Instabilidade da participação mensal |

## 6. Perguntas que ficaram abertas

- A queda de Jardim Canadá e o crescimento de Itabirito são reais ou mudança de registro?
- Os maiores pedidos são vendas reais ou erros de digitação?
