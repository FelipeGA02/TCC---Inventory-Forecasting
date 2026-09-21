# Relatório de Análise Exploratória (EDA)

**Projeto**: Sistema de Previsão de Estoque · Floricultura Verde Perto
**Data**: 2026-09-01
**Base analisada**: 333.019 transações · 02/01/2024 – 28/02/2026 · 5.166 produtos · 3 lojas

---

## 0. Por que a análise foi feita em duas etapas

A compreensão dos dados aconteceu em dois momentos, com perguntas diferentes:

- **Primeira etapa**: análise da base bruta de vendas, como ela chega da floricultura — o que
  existe, com que qualidade, e quais informações fazem sentido usar.
- **Segunda etapa**: análise já sobre as séries diárias de venda agrupadas por loja e categoria
  de produto — a base que efetivamente alimenta o modelo de previsão.

A primeira etapa orientou as regras de limpeza e organização dos dados; a segunda confirmou
(ou contestou) as premissas de modelagem — sazonalidade, tendência, e quais fatores explicam
melhor o comportamento das vendas.

---

## 1. Resumo executivo

### 1.1 O que a análise confirmou

- Prever vendas por produto individual não é viável: a maioria dos produtos vende muito pouco
  e de forma irregular. Por isso a previsão é feita por loja e categoria de produto (o "todo"),
  e depois distribuída entre os produtos dentro de cada categoria.
- Agrupar as vendas por loja e categoria produz um padrão de venda regular — vendas quase
  todos os dias, com sequências de no máximo 3 a 5 dias seguidos sem venda.
- Existe um padrão de calendário forte: dia da semana e datas comemorativas influenciam
  fortemente a demanda.
- As séries não mostram, de modo geral, uma tendência de longo prazo "fora de controle" —
  não é necessário um tratamento agressivo de tendência na maioria dos casos.
- Forma de pagamento e vendedor não ajudam a prever vendas futuras — são informações que só
  existem depois que a venda já aconteceu.
- O negócio se organiza bem em três grandes categorias: Produtos de jardim e Grama concentram
  quase todo o volume; Plantas de corte é pequena em volume, mas vende com regularidade.

### 1.2 O que a análise contrariou — pontos a corrigir

**"Fim de semana vende mais" está errado — é o oposto.**
Aos domingos a loja está fechada (venda zero). Aos sábados a venda cai bastante em relação à
média da semana. O pico de vendas é no meio da semana (terça a quinta) para Grama e Produtos
de jardim, e na sexta-feira para Plantas de corte. É o padrão típico de um negócio voltado a
paisagismo e jardinagem (compra em dia útil), não de uma floricultura de presente de fim de
semana. Essa premissa estava registrada de forma incorreta na documentação do projeto e
precisou ser corrigida.

**A variação diária das vendas é grande em todas as combinações loja×categoria, não só em
algumas.**
Isso confirma que é necessário suavizar essa variação em todas as séries antes de ajustar o
modelo, não apenas nas mais instáveis. Duas combinações em especial (Grama em Itabirito,
Plantas de corte em Jardim Canadá) têm dias de pico entre 79 e 90 vezes a venda média do dia
comum — coincidindo com pedidos grandes, provavelmente de paisagistas ou compras coletivas.
Mesmo com a suavização, essas duas têm boa chance de gerar previsões de confiança reduzida.

**Para "Plantas de corte", em uma das lojas, a previsibilidade vem quase inteiramente do
calendário, não do histórico recente de vendas.**
Nessa combinação a venda de um dia não indica quase nada sobre a venda do dia seguinte — não
há "inércia". O que explica a venda é a proximidade de datas comemorativas. Isso reforça a
necessidade de comparar o modelo estatístico principal com uma abordagem baseada em regras de
calendário para essa categoria.

**O efeito das datas comemorativas depende da categoria — e às vezes é negativo.**
Grama e Produtos de jardim **caem** de venda no Dia das Mães e no Natal (o cliente troca a
compra de grama por flores nessas ocasiões). Já Plantas de corte dispara — de 2 a 5,6 vezes a
média — exatamente nessas datas. Uma mesma data comemorativa não pode ter o mesmo efeito para
todas as categorias; o efeito precisa ser calculado separadamente por categoria.

**As lojas têm tendências opostas e fortes.**
A loja de Jardim Canadá vem encolhendo em volume (quedas de 31% a 49% ao ano nas categorias
principais); a loja de Itabirito vem crescendo (altas de 18% a 96% ao ano). Isso pode ser
deslocamento real de demanda entre as lojas, mudança de mix de produtos, ou uma mudança na
forma como as vendas são registradas — é uma pergunta em aberto para a floricultura
(seção 5). Na prática, as previsões dessas lojas precisam levar essa tendência em conta.

**A loja Garden Center tem menos de um ano de histórico** (abriu em fevereiro de 2025). Isso
está acima do mínimo necessário para gerar previsão, mas a loja ainda não passou por um ciclo
comemorativo completo (Dia das Mães, Natal etc. só foram vistos uma vez). As previsões dessa
loja devem vir com um aviso de menor confiança no primeiro ano de operação.

**A participação de cada produto dentro de sua categoria varia bastante mês a mês**, mesmo
entre os produtos mais vendidos. Isso significa que a distribuição da previsão da categoria
entre os produtos individuais precisa considerar uma janela de tempo mais longa do que o
inicialmente previsto, e que, para boa parte dos produtos, a melhor estimativa disponível será
a média da categoria — não uma estimativa individual.

### 1.3 Qualidade dos dados — resumo

- Não há meses faltando no período analisado (26 de 26 meses, de janeiro/2024 a
  fevereiro/2026).
- Não há problema de codificação de caracteres (acentuação) nos dados.
- Todas as datas de venda foram interpretadas corretamente.
- 880 linhas (0,3% da base) têm quantidade zero ou negativa — a maioria (836) é zero, e 44 são
  negativas (provavelmente devoluções); a regra de tratamento de devoluções precisa ser
  confirmada com a floricultura.
- Algumas linhas têm quantidade fracionária (venda de grama ou terra por metro quadrado ou
  quilo) — isso é esperado e legítimo, não é erro de dado.
- Em cerca de 90% dos documentos de venda, a soma dos itens bate exatamente com o valor total
  do documento; a diferença nos demais vem de serviços e fretes cobrados fora das linhas de
  produto, o que não compromete a análise.
- Duas informações da base original eram inúteis (uma sempre com valor zero, outra quase
  sempre vazia) e foram descartadas.

---

## 2. Compreensão da base de vendas

### 2.1 Volume e completude

| Métrica | Valor |
| --- | --- |
| Transações (documento × produto) | 333.019 |
| Documentos de venda distintos | 62.553 |
| Produtos distintos | 5.166 |
| Período coberto | 02/01/2024 – 28/02/2026 |
| Dias de calendário no período | 789 |
| Dias com pelo menos 1 venda | 654 (os demais são domingos e feriados, loja fechada) |

O volume mensal de vendas oscila ao longo do ano, com pico em outubro de 2025 e uma queda
visível no início de 2026. O mês mais recente da base (fevereiro/2026) tem volume comparável
ao mesmo mês em anos anteriores, o que sugere que o mês está completo — mas isso precisa ser
confirmado com a floricultura, pois, se for um recorte parcial, distorceria a ponta mais
recente dos dados usados para treinar e validar o modelo (ver seção 5).

### 2.2 O que veio nos dados

A base de vendas ("Contas a Receber") trouxe originalmente 20 informações por transação
(data, loja, produto, quantidade, valores, forma de pagamento, vendedor, cliente etc.). Dessas:

- **9 foram mantidas** para a previsão: data, loja, código do produto, quantidade vendida (o
  que se quer prever) e os valores financeiros da venda.
- **11 foram descartadas**: identificação do documento, forma de pagamento, operador, dados do
  cliente (removidos por serem informação pessoal), vendedor, observações livres e outras
  informações que não ajudam a prever vendas futuras.
- **3 foram criadas** a partir das existentes: a loja, a categoria do produto e uma
  subcategoria mais detalhada.

Um dicionário completo, com o significado de cada informação da base original, está
documentado separadamente.

### 2.3 Perfil por loja

| Loja | Transações | Produtos distintos | Quantidade total vendida | Faturamento | Primeira venda registrada | Dias com venda |
| --- | --- | --- | --- | --- | --- | --- |
| Jardim Canadá | 168.063 | 4.155 | 2.212.951 | R$ 26,5 mi | 02/01/2024 | 650 |
| Itabirito | 135.548 | 4.146 | 1.328.388 | R$ 16,6 mi | 02/01/2024 | 653 |
| Garden Center | 29.408 | 2.492 | 405.248 | R$ 6,1 mi | 13/02/2025 | 308 |

Jardim Canadá é a maior operação das três. Garden Center é a loja mais nova, com cerca de
12 meses de histórico — ainda sem um ciclo anual completo.

### 2.4 Perfil por categoria

| Categoria | Quantidade total vendida | Participação | Produtos distintos |
| --- | --- | --- | --- |
| Produtos de jardim | 2.028.097 | 51,4% | 5.043 |
| Grama | 1.837.995 | 46,6% | 14 |
| Plantas de corte | 74.634 | 1,9% | 107 |
| Serviços e taxas (não é produto) | 5.860 | 0,1% | 2 |

Grama movimenta quase metade do volume total com apenas 14 variedades — uma categoria
concentrada. Produtos de jardim é o oposto: mais de 5 mil itens diferentes, cada um vendendo
pouco. Plantas de corte é pequena em volume, mas vende de forma consistente ao longo do tempo
(ver seção 3).

### 2.5 Por que a previsão não pode ser feita produto a produto

Olhando produto por produto, o produto típico vendeu em apenas 9 dos 789 dias do período — ou
seja, ficou praticamente todo o tempo sem nenhuma venda registrada. Mais da metade dos
produtos vendeu em 1,1% dos dias do período, ou menos, e 13,2% dos produtos venderam uma única
vez em mais de dois anos de dados.

Isso significa que quase três em cada quatro produtos (72,2%) não têm histórico suficiente
para receber uma previsão individual confiável — para esses, a melhor estimativa disponível é
distribuir a previsão feita para a categoria como um todo, proporcionalmente ao que cada
produto costuma representar dentro dela. É essa constatação que sustenta a decisão de prever a
demanda agregada por loja e categoria (onde o padrão é regular e previsível) e depois repartir
essa previsão entre os produtos, em vez de tentar prever cada um dos mais de 5 mil produtos
individualmente.

### 2.6 Concentração de vendas por produto

Poucos produtos respondem por boa parte do volume: 7 produtos já somam metade de tudo que é
vendido; os 20 produtos mais vendidos respondem por 61,7% do volume; os 100 mais vendidos, por
81,6%. Isso justifica focar o relatório detalhado de reposição nos 20 produtos de maior giro —
mas vale notar que quais produtos ocupam essas posições muda com o tempo (seção 3.10), então
essa lista não é fixa.

### 2.7 Padrão semanal preliminar

Olhando o volume bruto de transações (antes do agrupamento por loja e categoria), o padrão de
domingo fechado e queda de movimento no sábado já aparece claramente. Uma leitura mais
precisa, por loja e por categoria, está na seção 3.3 — é essa versão detalhada que orienta o
modelo.

### 2.8 Qualidade dos dados — detalhamento

A única informação com muitos valores em branco era um campo de observações de texto livre
(89% vazio), que foi descartado. Praticamente nenhuma das informações usadas na previsão tem
valor faltante.

---

## 3. Comportamento da demanda diária (loja × categoria)

Esta etapa olha para a demanda diária já agrupada por loja e categoria de produto — a
granularidade que efetivamente alimenta o modelo de previsão. São 9 combinações no total
(3 lojas × 3 categorias principais).

### 3.1 Regularidade das vendas

| Combinação | Dias com venda | % do período | Maior sequência sem venda |
| --- | --- | --- | --- |
| Jardim Canadá · Grama | 645 | 81,7% | 3 dias |
| Jardim Canadá · Plantas de corte | 641 | 81,3% | 4 dias |
| Jardim Canadá · Produtos de jardim | 650 | 82,4% | 3 dias |
| Itabirito · Grama | 641 | 81,2% | 5 dias |
| Itabirito · Plantas de corte | 653 | 82,8% | — |
| Itabirito · Produtos de jardim | 653 | 82,8% | — |
| Garden Center · Grama | 299 | 78,5% | — |
| Garden Center · Plantas de corte | 221 | 59,9% | — |
| Garden Center · Produtos de jardim | 302 | 80,7% | — |

Nas combinações com mais histórico, os dias sem venda são quase todos domingos e feriados —
uma ausência previsível, não uma falha de venda. A exceção é Garden Center · Plantas de corte,
onde 30% dos dias úteis não tiveram venda nenhuma — uma série ainda curta e irregular,
resultado de a loja ser nova.

Todas as 9 combinações têm histórico suficiente (mínimo de 180 dias com venda) para receber um
modelo de previsão.

### 3.2 Variação diária muito grande — por que suavizar

Em todas as 9 combinações, o volume vendido varia muito de um dia para o outro — bem mais do
que seria esperado só pelo padrão semanal. As duas combinações mais extremas (Grama em
Itabirito e Plantas de corte em Jardim Canadá) têm dias de pico entre 79 e 90 vezes a venda
média do dia comum — coincidindo com pedidos grandes, provavelmente de paisagistas ou compras
coletivas para datas comemorativas.

Essa variação alta em todas as combinações confirma que é preciso suavizar essa oscilação
antes de ajustar o modelo — sem isso, os poucos dias de pico distorceriam a previsão dos dias
comuns. Mesmo com esse tratamento, as duas combinações mais extremas têm boa chance de gerar
previsões de confiança reduzida.

### 3.3 Padrão semanal — corrige a premissa do projeto

Comparando a venda de cada dia da semana com a média da combinação loja×categoria, o padrão
observado é:

- **Domingo**: loja fechada, venda zero em praticamente todas as combinações.
- **Sábado**: fraco para Grama e Produtos de jardim (bem abaixo da média); um pouco melhor
  para Plantas de corte, mais próximo da média — presente de fim de semana.
- **Grama e Produtos de jardim** vendem mais no meio da semana (terça a quinta) — compatível
  com compra de paisagista ou obra em dia útil.
- **Plantas de corte** vende mais na sexta-feira (podendo chegar a mais que o dobro da média)
  — compatível com compra para presente ou consumo de fim de semana.

Esse resultado **contradiz a premissa original do projeto**, de que "fim de semana vende
mais". Na prática, o padrão é o oposto do que se esperava — e essa correção já foi refletida
na documentação do projeto. Vale notar também que, apesar de o padrão semanal existir e ser
consistente, ele explica uma fração relativamente pequena da variação total da demanda — a
maior parte da variação dia a dia vem de eventos pontuais (pedidos grandes), não do dia da
semana em si.

### 3.4 Datas comemorativas — efeito muda de sinal por categoria

Comparando a venda média nos dias em torno de cada data comemorativa com a média geral da
combinação loja×categoria:

- **Plantas de corte** é a categoria "de presente": a venda dispara em torno do Dia das Mães,
  Dia da Mulher, Dia dos Namorados e Finados, chegando a 2 a 5,6 vezes a média nessas datas.
- **Grama** sofre o efeito oposto — **cai** de venda nessas mesmas datas (o cliente troca a
  compra de grama pela compra de flores). A única exceção é Finados em Itabirito, onde a venda
  de grama sobe (provável cuidado de túmulo/jardinagem de cemitério).
- **Produtos de jardim** tem um efeito misto e mais discreto, com algum aumento em Namorados e
  Finados em uma das lojas.

Essa inversão de sinal entre categorias é a razão pela qual o efeito de cada data comemorativa
precisa ser calculado separadamente por categoria — um único ajuste "geral" para todas as
categorias erraria o sentido do efeito em pelo menos uma delas.

Há também um padrão sazonal ao longo do ano: a venda de grama em Itabirito, por exemplo,
dispara em dezembro (mais de 3 vezes a média); a venda de plantas de corte em Jardim Canadá
sobe em abril, na preparação para o Dia das Mães.

### 3.5 Tendências opostas entre lojas

- **Jardim Canadá está encolhendo**: quedas de 31% a 49% ao ano nas três categorias
  principais.
- **Itabirito está crescendo**: altas de 18% a 96% ao ano.
- **Garden Center** está em ramp-up natural de loja nova, com altas fortes em todas as
  categorias.

Essa divergência pode refletir uma mudança real na demanda entre as lojas, uma mudança de mix
de produtos, ou uma mudança na forma como as vendas são registradas — é uma das perguntas em
aberto para a floricultura (seção 5). Na prática, as previsões das combinações com tendência
forte precisam incorporar essa tendência explicitamente, em vez de assumir que o patamar de
vendas é estável.

### 3.6 Estabilidade e "memória" da série

As séries diárias, de forma geral, não mostram sinais de estarem "fora de controle" (sem
tendência de longo prazo que impeça a previsão), exceto nas combinações com tendência forte já
discutidas acima, que exigem tratamento especial.

Olhando quanto o valor de um dia se relaciona com o valor dos dias anteriores, a "memória" de
curto prazo é fraca em todas as combinações — saber quanto vendeu ontem diz pouco sobre quanto
vai vender hoje. Existe um eco fraco do padrão semanal (o valor de uma semana atrás importa um
pouco mais que o de outros dias), mas em duas combinações — Plantas de corte em Jardim Canadá
e Produtos de jardim em Itabirito — esse eco praticamente não existe: a série se comporta como
um sinal aleatório, sem padrão de repetição algum. Para essas duas combinações, a previsão vai
depender quase inteiramente do calendário (dia da semana, proximidade de datas comemorativas),
e não do comportamento recente das vendas.

### 3.7 Dias fora do padrão (picos)

Cada combinação loja×categoria tem entre 4 e 16 dias claramente fora do padrão normal ao longo
dos mais de dois anos analisados. Eles se concentram em dois tipos de situação:

- **Fim de ano**: por exemplo, um único dia de dezembro de 2025 em que a venda de grama em
  Itabirito somou mais de 60 mil unidades.
- **Vésperas de datas comemorativas**: por exemplo, a véspera do Dia das Mães de 2024, com um
  pico de venda de plantas de corte em Jardim Canadá.

A análise desses casos confirma que são pedidos reais (provavelmente compras de paisagistas ou
compras coletivas), não erros de registro — por isso não foram removidos da base, apenas
tratados com a suavização mencionada na seção 3.2.

### 3.8 Situação de cada combinação loja×categoria

| Combinação | Situação | Observações |
| --- | --- | --- |
| Itabirito · Plantas de corte | Boa | — |
| Jardim Canadá · Grama | Boa | tendência de queda — precisa de ajuste de tendência na previsão |
| Jardim Canadá · Produtos de jardim | Atenção | padrão semanal fraco; sem "memória" recente; tendência de queda acentuada — depende mais do calendário |
| Itabirito · Produtos de jardim | Atenção | padrão semanal fraco; comporta-se como sinal aleatório no curto prazo |
| Itabirito · Grama | Atenção | variação diária extrema; pico de até 79× a média; tendência de alta muito forte |
| Jardim Canadá · Plantas de corte | Atenção | comporta-se como sinal aleatório no curto prazo; pico de até 90× a média — depende quase só do calendário |
| Garden Center · Grama | Atenção | menos de um ano de histórico, sem ciclo comemorativo completo |
| Garden Center · Produtos de jardim | Atenção | menos de um ano de histórico, sem ciclo comemorativo completo |
| Garden Center · Plantas de corte | Atenção | histórico curto; 30% dos dias úteis sem venda; crescimento acelerado de loja nova |

"Atenção" não significa que a previsão falha — ela continua sendo gerada normalmente, mas
acompanhada de um aviso de menor confiança no painel. Nenhuma das 9 combinações ficou abaixo
do mínimo de histórico necessário para gerar previsão.

### 3.9 A participação de cada produto dentro da categoria não é estável

Mesmo olhando só para os produtos mais vendidos de cada categoria, a fatia que cada um
representa dentro do total muda bastante de mês a mês — nenhuma das 9 combinações loja×categoria
mostrou uma participação de produtos estável ao longo do tempo.

Isso tem duas consequências práticas:

1. A distribuição da previsão da categoria entre os produtos individuais precisa olhar para
   uma janela de tempo mais longa do que uma estimativa baseada em poucas semanas recentes —
   do contrário, o resultado fica ruidoso.
2. Para a maior parte dos produtos (72%, como visto na seção 2.5), e mesmo para parte dos
   produtos "líderes" em meses de comportamento atípico, a melhor estimativa disponível
   continua sendo a média histórica de participação da categoria — não uma previsão
   individual mais refinada. Isso reforça a importância de também avaliar, como parte do
   trabalho acadêmico, se uma previsão dedicada por produto (para os poucos com histórico
   suficiente) supera essa abordagem de rateio exatamente nos casos em que ela é mais frágil.

---

## 4. Como isso muda as decisões de modelagem

| # | Ajuste necessário | Prioridade |
| --- | --- | --- |
| 1 | Corrigir a premissa de "fim de semana vende mais" na documentação do projeto — o padrão real é meio de semana para Grama/Produtos de jardim e sexta-feira para Plantas de corte, com sábado fraco e domingo fechado | Alta |
| 2 | Suavizar os picos de venda em todas as 9 combinações loja×categoria, não apenas nas mais instáveis | Alta |
| 3 | Calcular o efeito de cada data comemorativa separadamente por categoria, já que o efeito muda de sinal entre elas | Alta |
| 4 | Dar mais peso ao dia da semana como fator explicativo direto da previsão | Alta |
| 5 | Incorporar um ajuste de tendência nas combinações com crescimento ou queda mais acentuados | Média |
| 6 | Incluir, na comparação de modelos, uma abordagem baseada só em regras de calendário — para as combinações onde o histórico recente de vendas não ajuda a prever o próximo dia | Média |
| 7 | Ampliar a janela de tempo usada para distribuir a previsão da categoria entre os produtos, e tratar o rateio pela média da categoria como o caminho padrão (não uma exceção) para a maioria dos produtos | Média |
| 8 | Sinalizar a loja Garden Center e as combinações de variação mais extrema com aviso de menor confiança, especialmente no primeiro ano | Média |
| 9 | Definir com a floricultura a regra de tratamento das vendas com quantidade negativa (devoluções) | Baixa |

---

## 5. Perguntas em aberto para a floricultura

1. **Fevereiro de 2026 é um mês fechado ou um recorte parcial?** O volume parece completo
   (comparável a fevereiro de anos anteriores), mas isso precisa ser confirmado para não
   distorcer a parte mais recente dos dados usados para treinar e validar o modelo.
2. **O relatório de vendas usado captura 100% das saídas de mercadoria?** Ou só as que geram
   cobrança financeira? Brindes, bonificações, consumo interno e ajustes de estoque entram
   nesse relatório?
3. **Algum tipo de documento não representa venda real** e deveria ser excluído da análise
   (além dos registros de serviço/taxa, já excluídos)? Por exemplo, vendas condicionais ou
   devoluções registradas como novo documento.
4. **As vendas com quantidade negativa (44 registros) são sempre devolução?** Devem ser
   descontadas no dia em que a devolução aconteceu, no dia da venda original, ou simplesmente
   ignoradas?
5. **A queda de vendas em Jardim Canadá e o crescimento em Itabirito são reais?** Por exemplo:
   uma obra de grande porte migrou de uma loja para outra, houve mudança na forma de
   faturamento entre as unidades, ou mudou a forma como o relatório é gerado?
6. **Vale revisar manualmente a categorização dos produtos que caíram em "Outros"** (1,3% do
   volume)? Isso afeta apenas a distribuição da previsão entre produtos, não a previsão
   agregada por categoria.

---

Esta análise foi conduzida como parte da etapa de compreensão dos dados do projeto, antes da
modelagem propriamente dita, e será revisitada sempre que a base de dados for atualizada de
forma relevante.
