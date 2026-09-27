# Relatório de Análise Exploratória (EDA)

**Projeto**: Sistema de Previsão de Estoque · Floricultura Verde Perto
**Data**: 2026-09-21 · atualizado em 2026-09-23 (seção 3.12 — encomendas grandes)
**Base analisada**: 333.019 transações · 02/01/2024 – 28/02/2026 · 5.166 produtos · 2 unidades

---

## 0. Por que a análise foi feita em cinco etapas

A compreensão dos dados aconteceu em cinco momentos, com perguntas diferentes:

- **Primeira etapa**: análise da base bruta de vendas, como ela chega da floricultura — o que
  existe, com que qualidade, e quais informações fazem sentido usar.
- **Segunda etapa**: análise já sobre as séries diárias de venda agrupadas por unidade e
  categoria de produto — a base que efetivamente alimenta o modelo de previsão.
- **Terceira etapa**: teste de granularidade — se vale separar as categorias em grupos mais
  finos (Plantas diversas × Insumos e acessórios) ou se basta mostrá-los como grupos do painel.
- **Quarta etapa**: teste de separação — se prever cada unidade e cada categoria com o seu
  próprio modelo erra menos do que prever o total e repartir.
- **Quinta etapa** *(2026-09-23)*: encomendas grandes — se tirar da série as linhas de venda
  enormes (obra/paisagismo) e limitar os picos restantes resolve o erro alto de Itabirito
  (seção 3.12).

A primeira etapa orientou as regras de limpeza e organização dos dados; a segunda confirmou
(ou contestou) as premissas de modelagem — sazonalidade, tendência, e quais fatores explicam
melhor o comportamento das vendas; a terceira e a quarta mediram se abrir mais séries melhora a previsão;
a quinta separou dois tipos de venda que estavam misturados na mesma série.

---

## 1. Resumo executivo

### 1.1 O que a análise confirmou

- Prever vendas por produto individual não é viável: a maioria dos produtos vende muito pouco
  e de forma irregular. Por isso a previsão é feita por unidade e categoria de produto (o
  "todo"), e depois distribuída entre os produtos dentro de cada categoria.
- Agrupar as vendas por unidade e categoria produz um padrão de venda regular — vendas quase
  todos os dias, com sequências de no máximo 3 a 5 dias seguidos sem venda.
- Existe um padrão de calendário forte: dia da semana e datas comemorativas influenciam
  fortemente a demanda.
- As séries não mostram, de modo geral, uma tendência de longo prazo "fora de controle" —
  não é necessário um tratamento agressivo de tendência na maioria dos casos. A exceção é a
  Grama em Itabirito, que cresce cerca de 96% ao ano.
- Forma de pagamento e vendedor não ajudam a prever vendas futuras — são informações que só
  existem depois que a venda já aconteceu.
- O negócio se organiza bem em três grandes categorias: Produtos de jardim e Grama
  concentram quase todo o volume; Flores de corte é pequena em volume, mas vende com
  regularidade.
- Separar Produtos de jardim em Plantas diversas e Insumos e acessórios não melhora a
  previsão: os dois grupos têm séries tão densas quanto as demais, mas modelar cada um
  separadamente não erra menos do que repartir a previsão de Produtos de jardim entre eles.
  Os grupos aparecem no painel somando a previsão dos produtos de cada um (seção 3.10).
- **A previsão é feita por unidade, não por unidade e categoria juntas.** Separar por unidade
  tem apoio nos dados (Itabirito e Jardim Canadá têm tendências opostas), mas separar por
  categoria não melhora a previsão, mesmo em torno das datas comemorativas — então o modelo
  prevê 2 séries (uma por loja), e a categoria de cada produto é obtida repartindo essa
  previsão, do mesmo jeito que já se fazia para chegar no produto individual (seção 3.11).
- **O modelo prevê a venda de balcão; as encomendas grandes ficam de fora.** Em Itabirito,
  80 linhas de venda (36% do volume, a maioria Grama de obra paga por boleto) faziam o erro
  ficar pior do que o de uma previsão ingênua (MASE 1,43). Separando essas encomendas e
  limitando os picos restantes, o erro cai para 0,80. Em Jardim Canadá, onde encomendas são
  1,3% do volume, quase nada muda (seção 3.12, ADR-012).

### 1.2 O que a análise contrariou — pontos a corrigir

**"Fim de semana vende mais" está errado — é o oposto.**
Aos domingos a loja está fechada (venda zero). Aos sábados a venda cai bastante em relação à
média da semana para Grama e Produtos de jardim. O pico de vendas é de dia útil: terça a
quarta para Grama; quarta a quinta para Produtos de jardim em Jardim Canadá (em Itabirito a
semana é mais uniforme, com segunda e sexta um pouco acima); e sexta-feira para Flores de
corte. É o padrão típico de um negócio voltado a paisagismo e jardinagem (compra em dia
útil), não de uma floricultura de presente de fim de semana. Essa premissa estava
registrada de forma incorreta na documentação do projeto e precisou ser corrigida.

**A variação diária das vendas é grande em todas as combinações unidade×categoria, não só em
algumas.**
Isso confirma que é necessário suavizar essa variação em todas as séries antes de ajustar o
modelo, não apenas nas mais instáveis. Duas combinações em especial (Grama em Itabirito,
Flores de corte em Jardim Canadá) têm dias de pico de 79 e 86 vezes a venda média do dia
comum. Em cinco das seis séries, uma única linha de venda concentra de 31% a 96% do volume
do dia de pico — o padrão de um pedido grande isolado (seção 3.7). Mesmo com a suavização,
essas duas combinações têm boa chance de gerar previsões de confiança reduzida.
*Atualização 2026-09-23*: esses pedidos grandes agora são separados da série antes do
treino (seção 3.12), o que resolve o caso de Itabirito.

**Para Flores de corte, em Jardim Canadá, a previsibilidade vem quase inteiramente do
calendário, não do histórico recente de vendas.**
Nessa combinação a venda de um dia não indica praticamente nada sobre a venda do dia
seguinte — não há "inércia". O que explica a venda é a proximidade de datas comemorativas.
Isso reforça a necessidade de comparar o modelo estatístico principal com uma abordagem
baseada em regras de calendário para essa categoria.

**O efeito das datas comemorativas depende da categoria — e às vezes é negativo.**
Grama e Produtos de jardim **caem** de venda no Natal (0,4 a 0,6 vez a média) e, na maioria
das vezes, no Dia das Mães (o cliente troca a compra de grama por flores nessas ocasiões).
Já Flores de corte dispara — de 1,7 a 5,0 vezes a média — no Dia da Mulher, no Dia das Mães
e no Dia dos Namorados. Uma mesma data comemorativa não pode ter o mesmo efeito para todas
as categorias; o efeito precisa ser calculado separadamente por categoria.

**As unidades têm tendências diferentes.**
Jardim Canadá (que reúne as vendas da Floricultura e do Garden Center) está estável em Grama
e Flores de corte (−3% ao ano) e em queda moderada em Produtos de jardim (−23% ao ano);
Itabirito vem crescendo (altas de 18% a 96% ao ano). Isso pode ser deslocamento real de
demanda entre as unidades, mudança de mix de produtos, ou uma mudança na forma como as
vendas são registradas — é uma pergunta em aberto para a floricultura (seção 5). Na prática,
as previsões das combinações com tendência forte precisam levar essa tendência em conta.
*Atualização 2026-09-23*: em Itabirito, a maior parte do crescimento vem das encomendas
grandes, que saltaram de 68 mil unidades em 2024 para 377 mil em 2025. A venda de balcão
cresce cerca de +8% ao ano (seção 3.12).

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
| Documentos de venda distintos | 130.728 |
| Produtos distintos | 5.166 |
| Período coberto | 02/01/2024 – 28/02/2026 |
| Dias de calendário no período | 789 |
| Dias com pelo menos 1 venda | 654 (os demais são domingos e feriados, loja fechada) |

O volume mensal de vendas oscila ao longo do ano, com pico em outubro de 2025 e uma queda
visível no início de 2026 (transações por mês, por unidade, com as linhas verticais
marcando Dia das Mães e Finados, em `01_transacoes_por_mes_unidade.png`). O mês mais
recente da base (fevereiro/2026) tem volume comparável ao mesmo mês em anos anteriores, o
que sugere que o mês está completo — mas isso precisa ser confirmado com a floricultura,
pois, se for um recorte parcial, distorceria a ponta mais recente dos dados usados para
treinar e validar o modelo (ver seção 5).

### 2.2 O que veio nos dados

A base de vendas ("Contas a Receber") trouxe originalmente 20 informações por transação
(data, empresa, produto, quantidade, valores, forma de pagamento, vendedor, cliente etc.).
Dessas:

- **9 foram mantidas** para a previsão: data, empresa, código do produto, quantidade vendida
  (o que se quer prever) e os valores financeiros da venda.
- **11 foram descartadas**: identificação do documento, forma de pagamento, operador, dados do
  cliente (removidos por serem informação pessoal), vendedor, observações livres e outras
  informações que não ajudam a prever vendas futuras.
- **3 foram criadas** a partir das existentes: a unidade, a categoria do produto e uma
  subcategoria mais detalhada.

Um dicionário completo, com o significado de cada informação da base original, está
documentado separadamente.

### 2.3 Perfil por unidade

| Unidade | Transações | Produtos distintos | Quantidade total vendida | Faturamento | Primeira venda registrada | Dias com venda |
| --- | --- | --- | --- | --- | --- | --- |
| Jardim Canadá | 197.471 | 4.276 | 2.618.198 | R$ 32,6 mi | 02/01/2024 | 650 |
| Itabirito | 135.548 | 4.146 | 1.328.388 | R$ 16,6 mi | 02/01/2024 | 653 |

Jardim Canadá é a maior unidade, com quase o dobro do volume de Itabirito. Ela reúne dois
CNPJs: a Floricultura (167.149 linhas de produto) e o Garden Center (29.408), cujas vendas
começam em 13/02/2025. Em abril de 2025 o volume mensal do CNPJ da Floricultura cai de 87
mil para 47 mil unidades enquanto o do Garden Center chega a 37 mil; a soma dos dois (84
mil) fica próxima dos 81 mil de janeiro e fevereiro. A série diária da unidade é a soma dos
dois CNPJs (volume mensal de cada CNPJ dentro de Jardim Canadá em
`06_jardim_canada_por_cnpj.png`).

### 2.4 Perfil por categoria

| Categoria | Quantidade total vendida | Participação | Produtos distintos |
| --- | --- | --- | --- |
| Produtos de jardim | 2.034.205 | 51,5% | 5.062 |
| Grama | 1.837.995 | 46,6% | 14 |
| Flores de corte | 68.526 | 1,7% | 88 |
| Serviços e taxas (não é produto) | 5.860 | 0,1% | 2 |

Grama movimenta quase metade do volume total com apenas 14 variedades — uma categoria
concentrada. Produtos de jardim é o oposto: mais de 5 mil itens diferentes, cada um vendendo
pouco. Flores de corte é pequena em volume, mas vende de forma consistente ao longo do tempo
(ver seção 3). O volume por subcategoria detalhada (`categoria_fina`, o nível mais fino
antes do agrupamento em 3 categorias) está em `05_volume_categoria_fina.png`.

Dentro de Produtos de jardim, os grupos do cliente se dividem assim:

| Grupo | Quantidade total vendida | Participação | Produtos distintos |
| --- | --- | --- | --- |
| Plantas diversas (todas as plantas, exceto flores de corte e árvores) | 1.626.502 | 41,2% | 3.514 |
| Insumos e acessórios (terra, adubo, vasos, seixos, ferramentas) | 407.703 | 10,3% | 1.548 |

As árvores não têm um grupo próprio na base (a lista do sistema do cliente não está
disponível) e ficam dentro de Plantas diversas; uma estimativa por palavra-chave as coloca
em 0,4% (Jardim Canadá) a 1,2% (Itabirito) do volume da unidade.

### 2.5 Por que a previsão não pode ser feita produto a produto

Olhando produto por produto, o produto típico vendeu em apenas 9 dos 789 dias do período — ou
seja, ficou praticamente todo o tempo sem nenhuma venda registrada. Mais da metade dos
produtos vendeu em 1,1% dos dias do período, ou menos, e 13,2% dos produtos venderam uma única
vez em mais de dois anos de dados (histograma de dias com venda por produto, com a linha do
corte de 28 dias usado no rateio de categoria, em `03_esparsidade_dias_ativos_sku.png`).

Isso significa que quase três em cada quatro produtos (72,2%) não têm histórico suficiente
para receber uma previsão individual confiável — para esses, a melhor estimativa disponível é
distribuir a previsão feita para a categoria como um todo, proporcionalmente ao que cada
produto costuma representar dentro dela. É essa constatação que sustenta a decisão de prever a
demanda agregada por unidade e categoria (onde o padrão é regular e previsível) e depois
repartir essa previsão entre os produtos, em vez de tentar prever cada um dos mais de 5 mil
produtos individualmente.

### 2.5b Classificação formal da demanda por SKU

A conclusão da seção anterior — "a maioria dos produtos não sustenta previsão individual"
— tem um critério da literatura por trás, não só a observação de que a série é esparsa.

Modelos de previsão como o **SARIMAX**, usado neste projeto, funcionam suavizando o
histórico: olham os valores mais recentes (e o padrão de dia da semana) para estimar o
próximo. Isso funciona bem quando a série vende quase todo dia. Quando a série passa a
maior parte do tempo zerada — como a maioria dos produtos individuais — essa suavização
erra dos dois lados: no dia sem venda ela "acha" que vai vender um pouco, e no dia com
venda ela "acha" que vai vender pouco. Croston (1972) resolveu isso, para esse tipo de
série, separando duas perguntas — *quando* costuma vender e *quanto* costuma vender
quando vende — e estimando cada uma separadamente. TSB e SBA são variações do método de
Croston que corrigem vieses dele.

Syntetos, Boylan e Croston (2005)¹ deram um critério objetivo para saber, olhando só o
histórico de vendas, qual dos dois caminhos (SARIMAX ou Croston/TSB/SBA) tende a funcionar
melhor. O critério usa dois números:

- **de quanto em quanto tempo** o produto costuma vender (em média, quantos dias se
  passam entre uma venda e a próxima) — quanto maior, mais esparsa é a série;
- **quão variável** é a quantidade vendida, contando só os dias em que teve venda —
  quanto maior, mais imprevisível é o tamanho de cada venda.

Cruzando os dois, todo produto cai em um de quatro grupos: vende quase todo dia em
quantidade estável (SARIMAX funciona bem); vende quase todo dia mas em quantidade muito
variável (SARIMAX ainda funciona, com um ajuste); vende raramente mas sempre uma
quantidade parecida; ou vende raramente **e** em quantidade imprevisível — o pior caso.
Nos dois últimos grupos, o artigo mostra que o método de Croston erra menos que um modelo
como o SARIMAX.

Aplicando esse critério aos 5.162 produtos físicos da base (script
`eda_classificacao_sku.py`, gráfico `24_classificacao_demanda_sku.png`): 13,4% venderam em
um único dia (não dá para calcular a variabilidade); dos demais, **99,3% caem nos dois
grupos em que a literatura recomenda os métodos de demanda intermitente (Croston, TSB,
SBA)** em vez de um modelo de série temporal contínua. Aplicando o mesmo critério às 2
séries diárias por unidade (seção 3.0) e às 6 séries por unidade e categoria (seção 3.1),
todas caem no grupo "vende quase todo dia, quantidade variável" — exatamente o grupo em
que a suavização (`log1p`) e um modelo como o SARIMAX são a escolha adequada. Ou seja:
agregar por unidade não só reduz o número de séries a prever, mas move a série do grupo
errado para o grupo certo segundo esse critério.

> ¹ Syntetos, A.A.; Boylan, J.E.; Croston, J.D. (2005). "On the categorization of demand
> patterns." *Journal of the Operational Research Society*, 56(5), 495–503. O critério
> usa dois indicadores técnicos, ADI (intervalo médio entre vendas) e CV² (variabilidade
> do tamanho da venda), com cortes em 1,32 e 0,49 — os nomes técnicos dos quatro grupos são
> "suave", "errático", "intermitente" e "lumpy". Referências completas, as fórmulas e a
> tabela de resultado em `01-pre_processing.md` §5.2.

### 2.6 Concentração de vendas por produto

Poucos produtos respondem por boa parte do volume: 7 produtos já somam metade de tudo que é
vendido; os 20 produtos mais vendidos respondem por 61,7% do volume; os 100 mais vendidos, por
81,6% (curva de Pareto do volume por produto em `04_pareto_volume_sku.png`). Isso justifica
focar o relatório detalhado nos 20 produtos de maior giro — mas vale notar que quais produtos
ocupam essas posições muda com o tempo (seção 3.9), então essa lista não é fixa.

### 2.7 Padrão semanal preliminar

Olhando o volume bruto de transações (antes do agrupamento por unidade e categoria), o padrão
de domingo fechado e queda de movimento no sábado já aparece claramente
(`02_sazonalidade_semanal_unidade.png`). Uma leitura mais precisa, por unidade e por
categoria, está na seção 3.3 — é essa versão detalhada que orienta o modelo.

### 2.8 Qualidade dos dados — detalhamento

A única informação com muitos valores em branco era um campo de observações de texto livre
(89% vazio), que foi descartado. Praticamente nenhuma das informações usadas na previsão tem
valor faltante.

---

## 3. Comportamento da demanda diária

Esta etapa olha para a demanda diária agrupada em dois níveis: por **unidade** sozinha —
a granularidade que o modelo de previsão (L1) de fato ajusta desde 2026-09-21 (seção 3.11
explica por quê) — e por **unidade e categoria de produto** juntas (6 combinações), que
alimentam o passo de desagregação da previsão da unidade para cada categoria.

### 3.0 As séries do L1: por unidade (2 séries)

| Unidade | Dias com venda | % do período | CV | Força do ciclo semanal | Tendência |
| --- | --- | --- | --- | --- | --- |
| Jardim Canadá | 650 | 82,4% | 1,01 | 0,25 | −13%/ano |
| Itabirito | 653 | 82,8% | 2,39 | 0,07 | +54%/ano |

(as duas séries diárias e a média móvel de 28 dias estão em `16_series_l1_unidade.png`)

- **Padrão semanal**: pico na quarta-feira em Jardim Canadá (1,44 vez a média) e na
  terça-feira em Itabirito (1,47, com a segunda quase empatada em 1,46); sábado fraco nas
  duas (0,59 e 0,42 vez a média); domingo fechado. **Padrão mensal**: pico em outubro em
  Jardim Canadá — o mesmo mês mesmo recalculando sem o maior dia da série, então é
  sazonalidade real, não um pico isolado — e em dezembro em Itabirito (ver
  `17_perfil_semanal_mensal_unidade.png`).
- **Datas comemorativas** (razão vs. média geral da unidade): Dia dos Namorados sobe nas
  duas unidades (1,16 em Jardim Canadá, 1,52 em Itabirito); Finados sobe forte em Itabirito
  (2,96) — ali, Grama, Flores de corte e Produtos de jardim sobem juntos nessa data (seção
  3.4), então o agregado reflete bem as três; já o Dia das Mães **cai** no agregado das duas
  unidades (0,66 e 0,70) apesar de Flores de corte disparar 2,14× nessa data em Jardim
  Canadá — o agregado por unidade dilui esse pico porque Flores de corte é só 1,4% do
  volume ali (seção 3.11 detalha por que a desagregação por categoria precisa do efeito de
  data *da própria categoria*, não só da proporção histórica).
- **Autocorrelação e estacionariedade**: as duas séries têm autocorrelação significativa
  no lag 7 (eco semanal — Ljung-Box p < 0,001 nas duas), e os testes ADF/KPSS divergem nas
  duas — sugestão inicial `d=0`, a confirmar pelo resíduo (ACF e distribuição diária em
  `18_acf_dist_unidade.png`; decomposição STL completa das duas séries em
  `19_stl_unidade.png`).
- **Veredito**: Jardim Canadá está "ok" para o L1 sem ressalvas. Itabirito entra com
  "atenção": cauda extrema (dia de pico = 37× a média — o maior, 16/12/2025, somou 62.456
  unidades em 80 documentos, com uma única linha de 19.200 unidades = 30,7% do dia), ciclo
  semanal fraco na variância (Fs = 0,07), e tendência de alta forte (+54%/ano, de 892
  unidades/dia nos primeiros 90 dias para 3.033 nos últimos 90) — recomenda-se avaliar
  `d=1` ou um termo de nível/deriva na modelagem.
  **Atualização 2026-09-23 (seção 3.12)**: a cauda extrema e a maior parte da tendência
  vêm de encomendas grandes. Sem elas, o CV cai de 2,40 para 1,25, a tendência do balcão é
  de +8%/ano (774 → 910 unidades/dia) e o MASE cai de 1,434 para 0,796. A recomendação de
  `d=1` perde força e fica para ser reavaliada sobre a série de balcão.

### 3.1 Regularidade das vendas — desagregação `unidade → categoria`

As 6 séries abaixo (`unidade × categoria`) não são mais série L1 própria (seção 3.11) —
são o insumo do passo de desagregação que reparte a previsão de cada unidade entre as 3
categorias.

| Combinação | Dias com venda | % do período | Maior sequência sem venda |
| --- | --- | --- | --- |
| Jardim Canadá · Grama | 650 | 82,4% | 3 dias |
| Jardim Canadá · Flores de corte | 648 | 82,2% | 3 dias |
| Jardim Canadá · Produtos de jardim | 650 | 82,4% | 3 dias |
| Itabirito · Grama | 641 | 81,2% | 5 dias |
| Itabirito · Flores de corte | 653 | 82,8% | 3 dias |
| Itabirito · Produtos de jardim | 653 | 82,8% | 3 dias |

Em todas as combinações, os dias sem venda são quase todos domingos e feriados — uma ausência
previsível, não uma falha de venda. Todas as 6 combinações têm histórico suficiente (mínimo
de 180 dias com venda) para receber um modelo de previsão: a menor tem 641 dias. As 6 séries
diárias, com sua média móvel de 28 dias, estão em `10_series_l1_paineis.png`.

### 3.2 Variação diária muito grande — por que suavizar

Em todas as 6 combinações, o volume vendido varia muito de um dia para o outro — bem mais do
que seria esperado só pelo padrão semanal (o coeficiente de variação vai de 1,15 a 4,49,
visível também no título de cada painel de `10_series_l1_paineis.png`). As
duas combinações mais extremas (Grama em Itabirito e Flores de corte em Jardim Canadá) têm
dias de pico de 79 e 86 vezes a venda média do dia comum (a distribuição de cada uma das 6
séries, com a assimetria à direita que motiva o `log1p`, está em `14_dist_qtd_diaria_l1.png`).

Essa variação alta em todas as combinações confirma que é preciso suavizar essa oscilação
antes de ajustar o modelo — sem isso, os poucos dias de pico distorceriam a previsão dos dias
comuns. Mesmo com esse tratamento, as duas combinações mais extremas têm boa chance de gerar
previsões de confiança reduzida.

### 3.3 Padrão semanal — corrige a premissa do projeto

Comparando a venda de cada dia da semana com a média da combinação unidade×categoria (o
índice completo das 6 séries está em `11_perfil_dia_semana_l1.png`), o padrão observado é:

- **Domingo**: loja fechada, venda zero em praticamente todas as combinações.
- **Sábado**: fraco para Grama (0,42 vez a média em Jardim Canadá; 0,14 em Itabirito) e
  para Produtos de jardim (0,73 e 0,63); acima da média para Flores de corte (1,13 e 1,39)
  — presente de fim de semana.
- **Grama** vende mais de terça a quarta (1,5 a 1,6 vez a média em Jardim Canadá; 2,1 na
  terça em Itabirito) — compatível com compra de paisagista ou obra em dia útil.
- **Produtos de jardim** vende mais de quarta a quinta em Jardim Canadá (1,35 a 1,37 vez a
  média); em Itabirito a semana é mais uniforme, com segunda (1,43) e sexta (1,42) um pouco
  acima.
- **Flores de corte** vende mais na sexta-feira (1,73 vez a média em Jardim Canadá; quase o
  dobro — 1,96 — em Itabirito) — compatível com compra para presente ou consumo de fim de
  semana.

Esse resultado **contradiz a premissa original do projeto**, de que "fim de semana vende
mais". Na prática, o padrão é o oposto do que se esperava — e essa correção já foi refletida
na documentação do projeto. Vale notar também que, apesar de o padrão semanal existir e ser
consistente, ele explica uma fração relativamente pequena da variação total da demanda (a
força do ciclo semanal vai de 0,00 a 0,29, em uma escala de 0 a 1) — a maior parte da
variação dia a dia vem de eventos pontuais (pedidos grandes), não do dia da semana em si.

### 3.4 Datas comemorativas — efeito muda de sinal por categoria

Comparando a venda média nos dias em torno de cada data comemorativa com a média geral da
combinação unidade×categoria (razão em relação à média; 1,0 = sem efeito):

| Data | Flores de corte (Jardim Canadá · Itabirito) | Grama (Jardim Canadá · Itabirito) | Produtos de jardim (Jardim Canadá · Itabirito) |
| --- | --- | --- | --- |
| Dia da Mulher | 4,0 · 4,2 | 0,6 · 0,5 | 0,7 · 0,7 |
| Dia das Mães | 2,1 · 5,0 | 0,8 · 0,2 | 0,5 · 1,0 |
| Dia dos Namorados | 1,7 · 3,8 | 1,2 · 0,6 | 1,1 · 2,2 |
| Dia dos Pais | 0,8 · 1,2 | 0,2 · 0,2 | 0,6 · 0,5 |
| Finados | 1,1 · 3,1 | 0,7 · 3,3 | 0,7 · 2,6 |
| Natal | 2,1 · 1,1 | 0,6 · 0,5 | 0,4 · 0,5 |

- **Flores de corte** é a categoria "de presente": a venda dispara em torno do Dia da Mulher,
  do Dia das Mães e do Dia dos Namorados, e também em Finados em Itabirito.
- **Grama** sofre o efeito oposto — **cai** de venda na maior parte das datas (o cliente
  troca a compra de grama pela compra de flores). As exceções são Finados em Itabirito, onde
  a venda de grama sobe (provável cuidado de túmulo/jardinagem de cemitério), e o Dia dos
  Namorados em Jardim Canadá, com leve alta.
- **Produtos de jardim** tem um efeito misto: cai no Natal e no Dia dos Pais, e sobe nos
  Namorados e em Finados em Itabirito (2,2 e 2,6 vezes a média).

Essa inversão de sinal entre categorias é a razão pela qual o efeito de cada data comemorativa
precisa ser calculado separadamente por categoria — um único ajuste "geral" para todas as
categorias erraria o sentido do efeito em pelo menos uma delas.

Ao longo do ano, com apenas dois ciclos completos, só dois picos mensais se repetem nos dois
anos (o índice mensal das 6 séries, com maio e novembro marcados, está em
`12_perfil_mensal_l1.png`): as flores de corte em Itabirito sobem em dezembro (2,0 vezes a
média em 2024 e 1,5 em 2025) e a grama em Jardim Canadá sobe em outubro (1,5 e 1,9). Os
demais picos mensais vêm de um único ano ou de um único pedido, e não são sazonalidade:

- A grama em Itabirito tem dezembro em 3,4 vezes a média, mas isso é quase todo dezembro de
  2025 (6,3 vezes, com pedidos de dezenas de milhares de unidades); dezembro de 2024 ficou
  abaixo da média (0,5).
- As flores de corte em Jardim Canadá têm abril em 2,1 vezes a média por causa de um único
  pedido de 3.880 unidades em 30/04/2024 (seção 3.7); sem esse dia, abril fica em 0,7.

### 3.5 Tendências diferentes entre unidades

- **Jardim Canadá** (Floricultura + Garden Center): estável em Grama (−3% ao ano) e em Flores
  de corte (−3% ao ano); em queda moderada em Produtos de jardim (−23% ao ano — a média
  diária dos primeiros 90 dias é 2.286 unidades e a dos últimos 90 dias é 1.198).
- **Itabirito**: crescendo em todas as categorias — Grama +96% ao ano, Flores de corte +24%,
  Produtos de jardim +18%. Na Grama, a média diária vai de 316 unidades nos primeiros 90
  dias para 2.191 nos últimos 90, e boa parte desse salto vem dos pedidos grandes de
  dezembro de 2025 (seção 3.4).

Essa divergência pode refletir uma mudança real na demanda entre as unidades, uma mudança de
mix de produtos, ou uma mudança na forma como as vendas são registradas — é uma das
perguntas em aberto para a floricultura (seção 5). Na prática, as previsões das combinações
com tendência forte precisam incorporar essa tendência explicitamente, em vez de assumir que
o patamar de vendas é estável. A decomposição STL (observado/tendência/sazonal/resíduo) do
par de maior volume está em `15_stl_par_denso.png`.

### 3.6 Estabilidade e "memória" da série

As séries diárias, de forma geral, não mostram sinais de estarem "fora de controle" (sem
tendência de longo prazo que impeça a previsão): os testes de estabilidade sugerem tratar
todas as seis como estáveis, com a exceção já discutida — Grama em Itabirito, que cresce
+96% ao ano e exige tratamento especial.

Olhando quanto o valor de um dia se relaciona com o valor dos dias anteriores, a "memória" de
curto prazo é fraca em todas as combinações — saber quanto vendeu ontem diz pouco sobre quanto
vai vender hoje. Existe um eco fraco do padrão semanal (o valor de uma semana atrás importa um
pouco mais que o de outros dias), mas em duas combinações — Flores de corte em Jardim Canadá
e Produtos de jardim em Itabirito — esse eco praticamente não existe: a série se comporta
como um sinal aleatório, sem padrão de repetição algum. Para essas duas combinações, a
previsão vai depender quase inteiramente do calendário (dia da semana, proximidade de datas
comemorativas), e não do comportamento recente das vendas. A autocorrelação (ACF) das 6
séries, com o pico em múltiplos de 7 quando o eco semanal existe, está em
`13_acf_l1_paineis.png`.

### 3.7 Dias fora do padrão (picos)

Cada combinação unidade×categoria tem entre 4 e 20 dias claramente fora do padrão normal (mais
de 3 desvios-padrão acima da média) ao longo dos mais de dois anos analisados. Eles se
concentram em dois tipos de situação:

- **Fim de ano**: por exemplo, um único dia de dezembro de 2025 (16/12) em que a venda de
  grama em Itabirito somou mais de 61 mil unidades, em 12 documentos.
- **Pedidos grandes isolados**: por exemplo, 30/04/2024, com 3.880 unidades de flores de corte
  em Jardim Canadá (11 documentos, com uma linha de 1.200 rosas), e 08/10/2025, com 15.956
  unidades de grama em Jardim Canadá, das quais 15.000 em uma única linha.

Nos maiores dias de cada série, a maior linha de venda sozinha responde por:

| Combinação | Maior dia | Quantidade no dia | Documentos | Maior linha (% do dia) |
| --- | --- | --- | --- | --- |
| Jardim Canadá · Grama | 08/10/2025 | 15.956 | 29 | 15.000 (94,0%) |
| Jardim Canadá · Flores de corte | 30/04/2024 | 3.880 | 11 | 1.200 (30,9%) |
| Jardim Canadá · Produtos de jardim | 31/01/2024 | 40.407 | 104 | 5.000 (12,4%) |
| Itabirito · Grama | 16/12/2025 | 61.561 | 12 | 19.200 (31,2%) |
| Itabirito · Flores de corte | 04/12/2024 | 551 | 16 | 530 (96,2%) |
| Itabirito · Produtos de jardim | 17/12/2025 | 18.259 | 62 | 16.940 (92,8%) |

Em cinco das seis séries, uma única linha concentra de 31% a 96% do dia — o padrão de um
pedido grande isolado (paisagista, obra ou compra coletiva), e não de muitas vendas
pequenas. Um valor digitado errado teria a mesma assinatura, então a confirmação com a
floricultura é uma pergunta em aberto (seção 5). Esses dias continuam na base; o que muda
(seção 3.12) é que as linhas de encomenda saem da série que o modelo prevê e ficam como um
registro à parte.

### 3.8 Situação de cada combinação unidade×categoria

| Combinação | Situação | Observações |
| --- | --- | --- |
| Itabirito · Flores de corte | Boa | — |
| Jardim Canadá · Grama | Boa | estável (−3% ao ano); o padrão semanal mais forte das seis séries |
| Jardim Canadá · Produtos de jardim | Boa | padrão semanal fraco; tendência de queda moderada (−23% ao ano) — vale um ajuste de tendência |
| Itabirito · Produtos de jardim | Atenção | padrão semanal fraco; comporta-se como sinal aleatório no curto prazo |
| Itabirito · Grama | Atenção | variação diária extrema; pico de até 79× a média; tendência de alta muito forte |
| Jardim Canadá · Flores de corte | Atenção | comporta-se como sinal aleatório no curto prazo; pico de até 86× a média — depende quase só do calendário |

"Atenção" não significa que a previsão falha — ela continua sendo gerada normalmente, mas
acompanhada de um aviso de menor confiança no painel. Nenhuma das 6 combinações ficou abaixo
do mínimo de histórico necessário para gerar previsão.

Os gráficos completos das 6 séries `unidade × categoria` citados nesta seção 3 estão em:
séries diárias (`10_series_l1_paineis.png`), perfil de dia da semana
(`11_perfil_dia_semana_l1.png`), perfil mensal (`12_perfil_mensal_l1.png`), autocorrelação
(`13_acf_l1_paineis.png`), distribuição da quantidade diária (`14_dist_qtd_diaria_l1.png`)
e decomposição STL do par de maior volume (`15_stl_par_denso.png`).

### 3.9 A participação de cada produto dentro da categoria não é estável

Mesmo olhando só para os produtos mais vendidos de cada categoria, a fatia que cada um
representa dentro do total muda bastante de mês a mês — nenhuma das 6 combinações
unidade×categoria mostrou uma participação de produtos estável ao longo do tempo (a variação
média da participação mensal dos 10 maiores produtos vai de 0,65 em Itabirito · Flores de
corte a 2,04 em Itabirito · Grama).

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

### 3.10 Vale abrir Produtos de jardim em Plantas diversas e Insumos e acessórios?

O cliente organiza o catálogo em grupos: Grama, Flores de corte (as que compõem arranjos e
buquês), Plantas diversas (todas as plantas, exceto flores de corte e árvores) e os insumos e
acessórios de jardinagem. O modelo trabalha com três categorias — Grama, Flores de corte e
Produtos de jardim, que reúne plantas e insumos. A pergunta desta seção: separar Plantas
diversas e Insumos e acessórios em duas séries próprias melhoraria a previsão, ou basta
mostrá-los como grupos do painel, calculando a parte de cada um a partir da previsão de
Produtos de jardim?

**Como foi testado.** Três perguntas, nesta ordem: (1) as séries separadas são densas o
bastante para sustentar um modelo? (2) os grupos se comportam de forma diferente? (3) um
modelo próprio para cada grupo erra menos? Para a terceira, em 26 janelas consecutivas de 14
dias (um ano inteiro, com todas as datas comemorativas), comparou-se prever cada grupo
com o seu próprio modelo com prever Produtos de jardim e repartir o resultado pelo peso
recente de cada grupo — que é o que a distribuição por produto já faz. O erro é medido em
relação ao método simples de repetir a semana anterior (métrica MASE: abaixo de 1, o
modelo é melhor do que repetir a semana anterior). O teste foi repetido com dois modelos
de famílias diferentes (SARIMAX com calendário e suavização exponencial semanal), para
conferir que a conclusão não depende de um deles. A regra de decisão foi fixada antes de
ver os números: só abrir se o modelo próprio ganhar pelo menos 5% em cada grupo e cada
unidade.

**1. Viabilidade.** As séries separadas são tão densas quanto as demais:

| Unidade · grupo | Dias com venda | Dias úteis sem venda | Variação diária (CV) | % do volume da unidade |
| --- | --- | --- | --- | --- |
| Jardim Canadá · Grama | 650 | 4,0% | 1,15 | 46,7% |
| Jardim Canadá · Flores de corte | 648 | 4,3% | 3,35 | 1,4% |
| Jardim Canadá · Plantas diversas | 650 | 4,0% | 1,48 | 41,0% |
| Jardim Canadá · Insumos e acessórios | 650 | 4,0% | 1,30 | 10,9% |
| Itabirito · Grama | 641 | 5,5% | 4,49 | 46,5% |
| Itabirito · Flores de corte | 653 | 4,0% | 1,47 | 2,5% |
| Itabirito · Plantas diversas | 653 | 4,0% | 2,09 | 41,7% |
| Itabirito · Insumos e acessórios | 653 | 4,0% | 1,30 | 9,2% |

Tecnicamente, nada impede abrir: a questão é se compensa.

**2. Diferenças entre os grupos** (índice de dia da semana dos 4 grupos em
`20_grupos_perfil_dia_semana.png`; matriz de correlação entre grupos, sem o perfil semanal,
em `21_grupos_correlacao_residuos.png`).

- **Flores de corte** se distingue de todos os outros: pico na sexta (os demais, no meio da
  semana), sábado acima da média, e um efeito de datas comemorativas de sinal oposto. A
  correlação diária com qualquer outro grupo é de no máximo 0,19.
- **Plantas diversas e Insumos e acessórios** são o par mais próximo — correlação diária de
  0,46 em Jardim Canadá e 0,53 em Itabirito, contra 0,30 ou menos entre qualquer outro par —
  e têm perfil semanal parecido (0,64 e 0,83). Ainda assim têm diferenças: em Itabirito,
  Plantas diversas sobe no Dia dos Namorados (2,4 vezes a média) e em Finados (2,9), e
  Insumos e acessórios fica perto da média (1,1 e 1,5); em Jardim Canadá, Plantas diversas
  cai 26% ao ano e Insumos e acessórios, 10%.

**3. Teste de previsão** (MASE, quanto menor melhor; "repartido" = previsão de Produtos de
jardim repartida pelo peso recente do grupo, na melhor das duas formas testadas; resumo
visual com SARIMAX em `22_grupos_teste_previsao_mase.png`):

| Grupo | Modelo | Jardim Canadá: direto | Jardim Canadá: repartido | Itabirito: direto | Itabirito: repartido |
| --- | --- | --- | --- | --- | --- |
| Plantas diversas | SARIMAX | 0,551 | 0,526 | 0,939 | 0,945 |
| Plantas diversas | Suav. exponencial | 0,610 | 0,586 | 0,898 | 0,898 |
| Insumos e acessórios | SARIMAX | 0,618 | 0,697 | 0,868 | 0,924 |
| Insumos e acessórios | Suav. exponencial | 0,680 | 0,769 | 0,887 | 0,876 |

E o total de Produtos de jardim — modelo do total × soma dos dois modelos próprios:

| Modelo | Jardim Canadá: total | Jardim Canadá: soma | Itabirito: total | Itabirito: soma |
| --- | --- | --- | --- | --- |
| SARIMAX | 0,550 | 0,551 | 0,954 | 0,924 |
| Suav. exponencial | 0,616 | 0,613 | 0,905 | 0,895 |

Leitura:

- **Plantas diversas** (41% do volume): o modelo próprio não ganha — a repartição erra igual
  ou até 5% menos.
- **Insumos e acessórios** (10% do volume): o modelo próprio ganha em Jardim Canadá (11% nos
  dois modelos), mas em Itabirito o ganho de 6% com o SARIMAX vira uma piora de 1% com a
  suavização exponencial — não é consistente.
- **Total**: a soma dos dois modelos próprios iguala o modelo do total em Jardim Canadá e o
  melhora em 1% a 3% em Itabirito, abaixo dos 5% exigidos.
- Nos dois grupos e unidades, o menor ganho do modelo próprio foi −4,8% (uma piora) com o
  SARIMAX e −4,0% com a suavização exponencial, e a mediana dos ganhos foi +3,4% e −0,6%: a
  regra de decisão (mínimo de 5% em todos) **não foi atendida** com nenhum dos dois modelos.
- Dos 156 ajustes SARIMAX do teste, 1 não convergiu.

**4. Árvores.** Estimativa por palavra-chave (299 produtos: ipê, oliveira, citrus e outras
frutíferas, palmeiras, ciprestes): 0,4% do volume de Jardim Canadá e 1,2% do de Itabirito
(1,0% e 2,9% de Plantas diversas). A série é densa (646 e 637 dias com venda), mas pequena —
13 e 20 unidades por dia, com dias de pico de 42 e 64 vezes a média. Não sustenta uma
categoria própria; ficam dentro de Plantas diversas até a floricultura informar a lista do
grupo (seção 5).

**Conclusão.** O modelo segue com três categorias por unidade (6 séries). Plantas diversas
e Insumos e acessórios aparecem no painel como grupos, somando a previsão dos produtos de
cada um — sem custo de modelo adicional e sem perda de acerto. Vale reavaliar a abertura de
Insumos e acessórios quando houver mais histórico: o ganho em Jardim Canadá (11%) pode ser
real, mas com 26 meses de dados não se repete nas duas unidades.

### 3.11 Separar por unidade e por categoria melhora a previsão? — decisão: só por unidade

Até aqui o modelo previa uma série para cada combinação de unidade e categoria (6 séries,
seção 3.1). Este teste pergunta se cada nível de separação se paga: prever cada parte com
o próprio modelo erra menos do que prever o total e repartir pelo peso recente de cada
parte? É o mesmo desenho da seção 3.10 (26 janelas de 14 dias, dois modelos, MASE) e a
mesma regra (ganho mínimo de 5% nos dois modelos), aplicada a cada parte
(`23_separacao_teste_previsao_mase.png` resume o resultado com SARIMAX).

| Parte | Peso no total | SARIMAX: próprio × repartido | Suav. exponencial: próprio × repartido | Ganho do próprio (SARIMAX · suav.) |
| --- | --- | --- | --- | --- |
| Itabirito (total da rede) | 33,6% | 1,434 × 1,736 | 1,311 × 1,469 | +17% · +11% |
| Jardim Canadá (total da rede) | 66,4% | 0,659 × 0,829 | 0,727 × 0,656 | +21% · −11% |
| Jardim Canadá · Grama | 46,7% | 0,794 × 0,807 | 0,841 × 0,860 | +2% · +2% |
| Jardim Canadá · Flores de corte | 1,4% | 0,696 × 0,699 | 0,860 × 0,733 | +0% · −17% |
| Jardim Canadá · Produtos de jardim | 52,0% | 0,550 × 0,532 | 0,616 × 0,602 | −3% · −2% |
| Itabirito · Grama | 46,6% | 1,715 × 1,886 | 1,795 × 1,781 | +9% · −1% |
| Itabirito · Flores de corte | 2,5% | 0,811 × 0,893 | 0,868 × 0,904 | +9% · +4% |
| Itabirito · Produtos de jardim | 51,0% | 0,954 × 0,895 | 0,905 × 0,809 | −7% · −12% |

E o inverso — a soma das partes contra o modelo do agregado:

| Agregado | SARIMAX: total × soma das partes | Suav. exponencial: total × soma das partes |
| --- | --- | --- |
| Total da rede (2 unidades) | 1,153 × 0,901 | 0,919 × 0,922 |
| Jardim Canadá (3 categorias) | 0,659 × 0,665 | 0,727 × 0,733 |
| Itabirito (3 categorias) | 1,434 × 1,367 | 1,311 × 1,372 |

Leitura:

- **Unidade: apoiada, mas não por unanimidade.** Itabirito ganha com o modelo próprio nos dois
  modelos (17% e 11%): a tendência dele é oposta à de Jardim Canadá (seção 3.5). Jardim
  Canadá, que é dois terços do total, ganha 21% com o SARIMAX e perde 11% com a suavização
  exponencial. Somar os modelos das duas unidades melhora o total da rede em 22% com o
  SARIMAX e empata com a suavização exponencial.
- **Categoria: não melhora a previsão.** Nenhuma das 6 partes atende a regra. Os ganhos vão
  de −7% a +9% (SARIMAX) e de −17% a +4% (suavização exponencial), e a soma das três
  categorias fica a menos de 5% do modelo da unidade. Nas 7 janelas que contêm data
  comemorativa, o modelo próprio de Flores de corte também não erra menos (SARIMAX: 0,85 ×
  0,77 em Jardim Canadá e 1,18 × 1,09 em Itabirito). As diferenças de dinâmica entre
  categorias (seção 3.4) existem, mas com dois anos de dados não viram previsão melhor.
- **Cuidados**: em Itabirito vários valores passam de 1 (Grama, 1,7), ou seja, pior do que
  repetir a semana anterior, por causa dos pedidos gigantes (seção 3.7; tratados na seção
  3.12, que leva Itabirito a 0,80); diferenças de até
  cerca de 10% estão dentro do ruído; 2 dos 234 ajustes SARIMAX não convergiram; o SARIMAX do
  teste tem ordem fixa.

**Decisão**: o L1 passa a ajustar **2 séries** — uma por unidade (seção 3.0) — em vez de 6.
Prever as 2 unidades e repartir por categoria tem acurácia equivalente a prever as 6
séries, com 4 modelos a menos para ajustar e validar. As 6 séries `unidade × categoria`
(seção 3.1) não deixam de existir — elas viram o insumo do passo de desagregação
`unidade → categoria`, pelo mesmo motivo por que a `categoria_fina` já era só um nível de
desagregação para o SKU (seção 2.5).

### 3.12 Encomendas grandes — por que Itabirito errava tanto, e a correção

*(adicionada em 2026-09-23 · decisão registrada no
[ADR-012](ADR-012-encomendas-grandes-fora-do-l1.md) · script `eda_encomendas.py` ·
gráficos `25_encomendas_series.png` e `26_encomendas_mase.png`)*

**O problema.** Com a previsão por unidade (seção 3.11), Itabirito ficou com MASE 1,434,
pior do que simplesmente repetir a semana anterior. Jardim Canadá ficou em 0,659. A
diferença não está no modelo, está no tipo de venda. Em Itabirito, a Grama vende cerca de
200 m² num dia comum, mas algumas linhas de venda sozinhas têm 12.800, 19.200 ou 20.000 m².
Os 10 maiores dias concentram 43,6% de toda a Grama vendida ali (8,6% em Jardim Canadá), e
um único cliente responde por 32 das 40 maiores linhas, todas pagas por boleto. São
**encomendas** de obra ou paisagismo, combinadas com antecedência. Não são a venda de
balcão que o calendário explica, e nenhum modelo de série temporal consegue adivinhar em
que dia uma delas vai cair.

**A regra.** Uma linha de venda é considerada encomenda quando, sozinha, vale mais do que
**5 dias típicos** de venda daquela unidade e categoria. O dia típico é a mediana do volume
diário, de segunda a sábado. Na Grama de Itabirito, por exemplo, o limite é de 1.015 m² por
linha. A regra não usa percentil das linhas porque, em Produtos de jardim, linhas de 60 a
100 mudas são comuns: o 99º percentil marcaria quase metade do volume como encomenda.

| Unidade · categoria | Limite por linha | Linhas marcadas | Parte do volume |
| --- | --- | --- | --- |
| Itabirito · Grama | 1.015 | 68 | 67,7% |
| Itabirito · Produtos de jardim | 3.079 | 8 | 9,1% |
| Itabirito · Flores de corte | 155 | 4 | 4,2% |
| Jardim Canadá · Flores de corte | 160 | 12 | 17,8% |
| Jardim Canadá · Grama | 7.014 | 1 | 1,2% |
| Jardim Canadá · Produtos de jardim | 8.265 | 1 | 1,0% |

No total, as encomendas são **36,3% do volume de Itabirito** (80 linhas) e só 1,3% do de
Jardim Canadá (14 linhas). O perfil confirma que se trata de outra demanda: em Itabirito,
65% das linhas de encomenda são pagas por boleto, contra 1,4% no balcão, e só 7,5% são de
"CONSUMIDOR", contra 90,5% no balcão. Cliente e forma de pagamento serviram apenas para
conferir a regra; a regra em si usa só quantidade, unidade, categoria e data.

**A solução (duas camadas).** (1) As encomendas saem da série que o modelo prevê e ficam
como um registro à parte. (2) Nos picos que sobram na venda de balcão, os dias acima do
99º percentil são rebaixados a esse valor, só no treino do modelo. Tanto o limite das
encomendas quanto o teto são recalculados em cada janela do teste, usando só o passado.

| MASE (26 janelas de 14 dias) | Itabirito SARIMAX | Itabirito suav. exp. | Jardim Canadá SARIMAX | Jardim Canadá suav. exp. |
| --- | --- | --- | --- | --- |
| Como era (total) | 1,434 | 1,311 | 0,659 | 0,727 |
| Só o teto | 1,401 | 1,283 | 0,648 | 0,713 |
| Só separar as encomendas | 0,810 | 0,699 | 0,656 | 0,724 |
| **Separar + teto** | **0,796** | **0,688** | **0,646** | **0,710** |

**Antes × depois, por unidade.** "Antes" é a série total que o L1 usava. "Depois" é a
série de balcão, sem as encomendas, com e sem o teto. As características da série vêm do
mesmo diagnóstico do EDA 2 (`eda_series.analisa_serie`). O erro de previsão vem das 26
janelas de 14 dias. Na coluna "com teto", o erro é medido contra a venda de balcão real,
já que o teto só altera o treino.

*Itabirito*

| Indicador | Antes (total) | Depois: balcão | Depois: balcão + teto |
| --- | --- | --- | --- |
| Veredito do diagnóstico para SARIMAX | atenção | **ok** | **ok** |
| Venda média por dia | 1.677 | 1.069 | 1.043 |
| Variação diária (CV) | 2,39 | 1,25 | 1,11 |
| Maior dia ÷ média | 37,2 | 13,4 | 7,2 |
| Curtose (peso da cauda) | 82,6 | 29,0 | 12,7 |
| Força do ciclo semanal (0 a 1) | 0,07 | 0,20 | 0,24 |
| Tendência | +54%/ano | +8%/ano | +10%/ano |
| Média dos primeiros → últimos 90 dias | 892 → 3.033 | 774 → 910 | 773 → 910 |
| CV² dos dias com venda (classe de demanda) | 4,58 (errática) | 1,11 (errática) | 0,84 (errática) |
| **MASE SARIMAX** | **1,434** | 0,810 | **0,796** |
| WAPE SARIMAX | 91,6% | 62,4% | 61,3% |
| Erro acumulado em 14 dias, SARIMAX (média absoluta) | 47,4% | 32,2% | 30,4% |
| MASE suavização exponencial (Holt-Winters) | 1,311 | 0,699 | 0,688 |
| WAPE suavização exponencial | 84,4% | 53,8% | 53,0% |

*Jardim Canadá*

| Indicador | Antes (total) | Depois: balcão | Depois: balcão + teto |
| --- | --- | --- | --- |
| Veredito do diagnóstico para SARIMAX | ok | ok | ok |
| Venda média por dia | 3.317 | 3.273 | 3.191 |
| Variação diária (CV) | 1,01 | 1,00 | 0,84 |
| Maior dia ÷ média | 13,9 | 14,1 | 4,4 |
| Curtose (peso da cauda) | 40,2 | 43,9 | 2,7 |
| Força do ciclo semanal (0 a 1) | 0,25 | 0,25 | 0,38 |
| Tendência | −13%/ano | −13%/ano | −8%/ano |
| CV² dos dias com venda (classe de demanda) | 0,67 (errática) | 0,64 (errática) | 0,40 (**suave**) |
| **MASE SARIMAX** | **0,659** | 0,656 | **0,646** |
| WAPE SARIMAX | 47,3% | 46,7% | 46,0% |
| Erro acumulado em 14 dias, SARIMAX (média absoluta) | 27,7% | 27,0% | 25,4% |
| MASE suavização exponencial (Holt-Winters) | 0,727 | 0,724 | 0,710 |
| WAPE suavização exponencial | 52,2% | 51,6% | 50,6% |

Leitura do antes × depois:

- **Itabirito muda de natureza.** Tirar as encomendas corta a variação diária pela metade
  (CV 2,39 → 1,25) e reduz o peso da cauda de 82,6 para 29,0. O ciclo semanal, que estava
  escondido pelos picos, fica três vezes mais forte (0,07 → 0,20), e é justamente o que o
  SARIMAX usa para prever. Por isso o veredito passa de "atenção" para "ok" e o erro
  percentual (WAPE) cai de 92% para 61%.
- **Em Jardim Canadá, quem ajuda é o teto, não a separação.** Quase não há encomenda ali. O
  teto reduz o maior dia de 14 para 4,4 vezes a média e torna a série "suave" na
  classificação de demanda (CV² < 0,49), mas o ganho de previsão é pequeno (MASE 0,659 →
  0,646).
- **A tendência muda de figura.** Em Itabirito, os +54%/ano eram quase todos encomenda: a
  média dos últimos 90 dias do balcão (910) é só 18% maior que a dos primeiros 90 (774).

Leitura do teste por variante:

- **Itabirito passa a bater a previsão ingênua** com os dois modelos (0,80 e 0,69). Quem
  resolve é a separação; o teto sozinho quase não ajuda e, depois da separação, acrescenta
  de 1% a 2%.
- **Jardim Canadá praticamente não muda**, o que é esperado com 1,3% de encomendas. A
  regra não estraga a série que já estava boa.
- **O resultado não depende do número 5**: com limite de 3 ou 10 dias típicos, o MASE de
  Itabirito fica entre 0,79 e 0,80.
- **A "tendência de alta" de Itabirito era, em boa parte, encomenda.** Sem elas, a venda de
  balcão cresce cerca de +8% ao ano, e não +54%. As encomendas saltaram de 68 mil unidades
  em 2024 para 377 mil em 2025 (seções 3.0 e 3.5).
- **Limite honesto**: o sistema passa a prever a venda de balcão, não as encomendas.
  Comparada à venda total, a previsão de Itabirito volta a ter MASE 1,26, porque a
  encomenda continua imprevisível pelo histórico. Para prevê-la seria preciso a carteira de
  pedidos já combinados (pergunta 9 da seção 5).

**Apoio na literatura.** Separar a demanda regular da gerada por poucos clientes grandes, e
tratar esta com a informação do próprio pedido, é a recomendação de Bartezzaghi e Verganti
(1995), Bartezzaghi, Verganti e Zotteri (1999) e Kalchschmidt, Zotteri e Verganti (2003,
2006). Que picos distorcem o ajuste e as previsões do ARIMA é mostrado por Chen e Liu (1993).
Hyndman e Athanasopoulos (2021, §13.9) alertam para não apagar picos sem entender a causa.
Nenhum desses trabalhos usa exatamente o limite "5 dias típicos": ele é uma escolha deste
projeto, próxima dos filtros robustos baseados em mediana (filtro de Hampel). As referências
completas estão no [ADR-012](ADR-012-encomendas-grandes-fora-do-l1.md).

---

## 4. Como isso muda as decisões de modelagem

| # | Ajuste necessário | Prioridade |
| --- | --- | --- |
| 1 | Corrigir a premissa de "fim de semana vende mais" na documentação do projeto — o padrão real é de dia útil (meio de semana para Grama e Produtos de jardim; sexta-feira para Flores de corte), com sábado fraco para Grama e Produtos de jardim e domingo fechado | Alta |
| 2 | Suavizar os picos de venda em todas as 6 combinações unidade×categoria, não apenas nas mais instáveis | Alta |
| 3 | Calcular o efeito de cada data comemorativa separadamente por categoria, já que o efeito muda de sinal entre elas | Alta |
| 4 | Dar mais peso ao dia da semana como fator explicativo direto da previsão | Alta |
| 5 | Incorporar um ajuste de tendência nas combinações com crescimento ou queda mais acentuados (Grama e Produtos de jardim em Itabirito; Produtos de jardim em Jardim Canadá) | Média |
| 6 | Incluir, na comparação de modelos, uma abordagem baseada só em regras de calendário — para as combinações onde o histórico recente de vendas não ajuda a prever o próximo dia | Média |
| 7 | Ampliar a janela de tempo usada para distribuir a previsão da categoria entre os produtos, e tratar o rateio pela média da categoria como o caminho padrão (não uma exceção) para a maioria dos produtos | Média |
| 8 | Sinalizar as combinações de variação mais extrema (Grama em Itabirito, Flores de corte em Jardim Canadá) com aviso de menor confiança | Média |
| 9 | Apresentar Plantas diversas e Insumos e acessórios como grupos do painel (não como série própria), somando a previsão dos produtos de cada um; reavaliar Insumos e acessórios com mais histórico | Média |
| 10 | **Decidido**: o L1 ajusta 2 séries (por unidade), não 6 — a separação por categoria não melhora a acurácia (seção 3.11), a por unidade é apoiada; `categoria` passa a nível de desagregação (seção 3.0) | Alta |
| 11 | Definir com a floricultura a regra de tratamento das vendas com quantidade negativa (devoluções) | Baixa |
| 12 | **Decidido (ADR-012)**: separar da série do L1 as linhas de encomenda (linha > 5 dias típicos da unidade × categoria, limite calculado no treino) e limitar ao 99º percentil os picos restantes do balcão, só no treino. A participação da desagregação passa a ser calculada sobre o balcão; o painel informa que encomendas não estão incluídas. Substitui, para Itabirito, os itens 2, 5 e 8 (seção 3.12) | Alta |
| 13 | **Carnaval como feriado explícito** (segunda e terça, loja fechada, venda 0). É ponto facultativo, não feriado nacional por lei, e uma lista de feriados nacionais pode não trazê-lo. No primeiro treino, só 16–17/02/2026 responderam por 23% do erro de fevereiro. `eda/_common.py` já trata o Carnaval, mas faltava registrar. *Conferido em 2026-09-27: a BrasilAPI traz o Carnaval, e com calendário o erro nos feriados cai a ~0 (doc 03)* | Alta |
| 14 | **Medir de forma comparável entre experimentos.** O MASE usa a escala da naïve *no treino*: quando o treino tem picos de encomenda, essa escala infla e o MASE fica otimista (0,40 no primeiro treino, contra ganho real de 18% sobre a naïve). Reportar também o erro relativo à naïve **na mesma janela de teste**, em quantas rodadas o modelo vence a naïve e, entre alvos diferentes (total × por unidade), o erro no total somado nas mesmas datas | Alta |
| 15 | Avaliar a **largura** do intervalo de 95% junto com a cobertura: no primeiro treino a cobertura "passou" (96%) com uma faixa de ~80 mil para venda média de ~3 mil/dia. *Causa principal: feriados sem calendário (79% dos resíduos² em escala log), não as encomendas (5%); com calendário a faixa cai para ~13 mil (doc 03)* | Média |
| 16 | **Mudança de nível**: set–dez/2025 foi temporada alta no balcão (5,8 a 7,0 mil/dia, contra 3,5 mil em jan/2026), e o modelo puxa a previsão para a média do histórico. Complementa o item 5 (tendência): testar peso maior para as semanas recentes. *Doc 03 (§4.2): com calendário as previsões ficam quase planas o ano todo; em 15 de 26 rodadas o modelo previu < 90% do vendido e em 6 previu > 110%* | Média |
| 17 | **Vendas médias abaixo do limite de encomenda**: em dez/2025, 35 linhas de 500 ou mais unidades somaram 27% do balcão. O teto p99 (item 12) atenua; verificar se basta ou se o limite `k` precisa de ajuste sazonal | Baixa |

| 18 | **Abertura excepcional**: nos dois Dias das Mães (domingo) e nos Finados (sábado feriado em 2024, domingo em 2025) a loja **abriu** e vendeu de 600 a 900 unidades, quando estaria fechada. São os únicos domingos com venda do histórico. Modelar como "loja aberta excepcionalmente no dia", não como janela de 7 dias antes da data: a janela atribui à semana (+159% e +280%) um efeito que é do próprio dia; o balcão da semana anterior varia só de −18% a +39%. No ano de teste, isso fez o modelo prever ~12,7 e ~18,7 mil/dia útil nessas semanas (normal ~5 mil): **12% de todo o erro do ano** (doc 03, §4.3) | Alta |
| 19 | **Clima não entra no L1 total**: com chuva e temperatura observadas (cenário ideal), o erro não melhorou (ano: 0,616 → 0,622 do erro da naïve), nenhum coeficiente foi significativo (p > 0,2) e o clima somou 1,4% da importância RF. Reavaliar só para flores de corte, se a categoria for prevista à parte | Média |

*Itens 13–17 adicionados em 2026-09-27 a partir do primeiro treino com os dados pré-EDA
([02-baseline_serie_crua_pre_eda.md](02-baseline_serie_crua_pre_eda.md)); itens 18–19 a partir
do treino enriquecido ([03-enriquecimento_serie_crua.md](03-enriquecimento_serie_crua.md)).*

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
5. **A queda de Produtos de jardim em Jardim Canadá (−23% ao ano) e o crescimento de
   Itabirito (+18% a +96% ao ano) são reais?** Por exemplo: uma obra de grande porte migrou
   entre unidades, ou mudou a forma como as vendas são registradas entre os CNPJs (como
   aconteceu com o Garden Center)?
6. **Os maiores pedidos do período são vendas reais?** Por exemplo, uma linha de 15.000
   unidades de grama em 08/10/2025 (Jardim Canadá) e uma de 16.940 unidades em 17/12/2025
   (Itabirito, Produtos de jardim). Se algum for erro de digitação, deve ser corrigido ou
   removido antes do treino.
7. **Quais produtos fazem parte dos grupos "Plantas diversas" e "Árvores" no sistema de
   vocês?** Hoje as árvores (estimadas em 0,4% a 1,2% do volume por unidade) ficam dentro de
   Plantas diversas, e o grupo de itens que não são plantas (terra, adubo, vasos, seixos,
   ferramentas) está nomeado "Insumos e acessórios" — confirmar o nome e a lista.
8. **Vale revisar manualmente a categorização dos produtos que caíram em "Outros"** (1,3% do
   volume)? Isso afeta apenas a distribuição da previsão entre produtos, não a previsão
   agregada por categoria.
9. **As vendas grandes de Grama em Itabirito são encomendas sob pedido?** (seção 3.12) São 80
   linhas (36% do volume da unidade), a maioria paga por boleto e concentrada em poucos
   clientes. Elas saem do estoque da loja ou são pedidas ao fornecedor depois de fechadas
   com o cliente? Existe algum registro dessas encomendas **antes** da venda (orçamento,
   pedido, agenda de entrega)? Se existir, ele permitiria incluir as encomendas já
   combinadas na previsão.
10. **As lojas fecham em 15 de agosto e 8 de dezembro?** Nos dados, as duas lojas ficaram sem
    venda em 15/08/2024, 15/08/2025 e 08/12/2025, dias úteis que não são feriado nacional
    (provável feriado municipal: Assunção e Imaculada Conceição). Há outros dias de
    fechamento local? E em 02/01/2025 só Itabirito fechou: foi uma "ponte" pontual? Também:
    a loja **abre** sempre no Dia das Mães e em Finados, mesmo sendo domingo ou feriado?
    (doc [03](03-enriquecimento_serie_crua.md), §1)

---

Esta análise foi conduzida como parte da etapa de compreensão dos dados do projeto, antes da
modelagem propriamente dita, e será revisitada sempre que a base de dados for atualizada de
forma relevante.
