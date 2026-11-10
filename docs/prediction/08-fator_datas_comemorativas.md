# 08 — Fator multiplicativo das datas comemorativas: EDA e teste no SARIMAX de produção

**Data:** 2026-10-31, refeito em 2026-11-05 com a classificação SKU a SKU de 2026-11-04 ·
**Status:** experimento concluído; adotado pelo ADR-019 (2026-11-03): a alta em Flores de corte
(4 datas de presente e, desde 2026-11-05, o Ano Novo) e a queda de 26 a 31/12 e do Dia do
Trabalho nas outras séries (§9.3)
**Script:** `ia-predictor/training_scripts/datas_comemorativas/fator_multiplicativo.py`
**Resultados:** `ia-predictor/training_scripts/results/metrics/fator_datas_comemorativas/` (EDA e
backtest por ocorrência) e `fator_datas_comemorativas.csv` (consolidado). A rodada com a
classificação anterior ficou em `fator_datas_comemorativas_antes_sku/`.

---

## 1. A pergunta

A floricultura vende mais nas datas comemorativas? Se vende, multiplicar a previsão dos dias
em volta da data por um fator melhora a previsão das séries do sistema (ADR-017)? Tudo sobre
o **fluxo**: sem as encomendas grandes (média + 4 desvios dos pedidos da loja, ADR-018).

Resposta curta:

- **Flores de corte vende de 1,6 a 5,8 vezes uma semana comum** na semana do Dia da Mulher,
  do Dia das Mães, do Dia dos Namorados e do Natal, nas 2 lojas. No Dia dos Pais e no Finados,
  a flor de corte não sobe.
- **A flor de Finados é a flor em vaso, e só em Itabirito** (§2.3): crisântemo e kalanchoe,
  em Plantas diversas. Uma semana comum vende uns 10 crisântemos; os 7 dias antes de Finados
  venderam 126 em 2024 e 741 em 2025.
- **O total da loja não sobe** em Jardim Canadá em nenhuma data. Em Itabirito, sobe na semana
  de Finados (1,4 a 1,8) e, em parte, na do Dia das Mães.
- **Em Flores de corte, o fator pela metade faz sentido:** o erro do total da semana cai 40%
  a 45%, e melhora nas 10 ocorrências testadas. O erro de cada dia não melhora de forma
  consistente.
- **Em Finados, não:**
  - **Grama:** o ganho vem de o modelo já prever pouco no período inteiro, não da data.
  - **Produtos de jardim:** o fator piora muito.
  - **Plantas diversas:** apesar do crisântemo, o fator melhora uma ocorrência e piora a
    outra.

## 2. O que o EDA mostra

### 2.1 Como foi medido

Para cada série (as 4 categorias e o total de cada loja) e cada data:

- **Base do dia:** a mediana da venda do **mesmo dia da semana** nas 4 semanas antes e nas 4
  depois, só com dias normais. Dia normal é loja aberta, sem feriado, sem abertura
  excepcional, fora de 7 dias antes a 3 depois de outra data e fora de 20/12 a 10/01. Assim o
  efeito da data não se mistura com o do dia da semana nem com o nível do período.
- **Fator da semana:** venda ÷ base, somadas nos dias de loja aberta de 6 dias antes até o
  dia. O dia de abertura excepcional (Dia das Mães e Finados em Itabirito) fica de fora: a
  exógena `abertura_excepcional` do modelo já o explica.
- **Semanas comuns:** o mesmo fator calculado para toda janela de 7 dias sem data, feriado nem
  fim de ano. A faixa de 5% a 95% delas mostra quanto uma semana varia **sem** data
  nenhuma. Fator dentro dessa faixa não se distingue do ruído.

Há 2 ocorrências de cada data (2024 e 2025). O Dia da Mulher de 2026 fica depois da última
venda (28/02/2026).

### 2.2 Resultado

Fator da semana, 2024 / 2025. Entre parênteses, a faixa de 5% a 95% das semanas comuns:

| Data | Flores · JC (0,57–2,27) | Flores · ITA (0,61–2,31) | Total · JC (0,76–1,38) | Total · ITA (0,74–1,54) |
| --- | --- | --- | --- | --- |
| Dia da Mulher | **2,62 / 4,17** | **5,65 / 3,54** | 1,08 / 0,83 | 1,41 / 0,97 |
| Dia das Mães | **2,72 / 4,26** | **5,83 / 2,90** | 0,95 / 1,12 | 1,32 / **1,64** |
| Dia dos Namorados | 1,64 / 2,22 | **4,42 / 3,07** | 1,03 / 0,98 | 1,25 / 1,08 |
| Natal | **3,03 / 2,29** | 2,21 / 1,52 | 1,04 / 0,97 | 1,22 / 1,33 |
| Finados | 1,71 / 0,75 | 1,21 / 0,81 | 0,98 / 0,88 | **1,80 / 1,39** |
| Dia dos Pais | 1,16 / 1,33 | 1,59 / 1,25 | 1,10 / 1,08 | 1,01 / 0,97 |

- **Flores de corte** fica acima de 95% das semanas comuns, ou perto disso, nas 4 datas de
  presente, nas 2 lojas e nos 2 anos.
  - **Onde fica o pico:** nas datas que caem em dia útil (Mulher e Namorados), na véspera e
    no dia: 9 a 16 vezes a base em Itabirito nos Namorados. No Dia das Mães (domingo, loja
    fechada em Jardim Canadá), o pico se espalha de quinta a sábado.
  - **Em unidades:** uma semana comum de flor vende cerca de 285–305 un. por loja; essas
    semanas vendem de 400 a 800.
- **Total da loja em Jardim Canadá:** nenhuma data sai da faixa. Flores de corte é 1,5% das
  unidades e 2,4% do faturamento da loja, e o pico não aparece no total.
- **Total da loja em Itabirito:** Finados (1,80 e 1,39) é a única alta que pega a loja
  inteira.
  - **Por categoria:** Grama (2,27 / 2,14), Plantas diversas (1,70 / 1,20) e Produtos de
    jardim (2,80 / 1,20).
  - **Grama de Itabirito é instável:** em 5% das semanas comuns, o fator passa de 3,2.
  - **Peso de Flores de corte em Itabirito:** 4,8% das unidades e 7,6% do faturamento.
- **Correção ao `00-eda_report.md` §3.4:** a queda de Grama nas datas (0,2 no Dia dos Pais,
  por exemplo) quase toda some quando se compara com o mesmo dia da semana. Em Jardim Canadá,
  Grama fica entre 0,69 e 1,39, dentro da faixa comum. A §3.4 comparava com a média geral da
  série, sem descontar o dia da semana. Provavelmente as datas que caem no domingo (Mães e
  Pais) puxavam para a janela dias de loja fechada, de venda zero.
- **Efeito da classificação SKU a SKU (2026-11-04):** quase nenhum em Flores de corte (o Dia
  das Mães de Itabirito foi de 5,74 para 5,83; os Namorados, de 4,55 para 4,42). Em Plantas
  diversas de Itabirito no Finados, a alta caiu de 1,74 / 1,31 para 1,70 / 1,20, porque a
  grama preta (pelo de urso) passou para Grama.

### 2.3 Finados: a flor é em vaso, e só em Itabirito

Flores de corte (rosa, buquê, flor avulsa) não sobe no Finados, nem em unidades nem em R$:

| Semana de Finados | Unidades × normal | R$ × normal |
| --- | --- | --- |
| Jardim Canadá 2024 / 2025 | 1,26 / 0,74 | 0,85 / 0,92 |
| Itabirito 2024 / 2025 | 1,31 / 0,84 | 0,90 / 0,86 |

A exceção é uma encomenda de 300 flores em Itabirito em 31/10/2025, que fica fora do fluxo
por ser encomenda grande (ADR-018).

A flor de Finados é a **flor em vaso**, cadastrada em Plantas diversas (subcategoria
"Planta em vaso"). Unidades por semana, contadas a partir de Finados (semana −1 = os 7 dias
antes; semana 0 = de Finados até 6 dias depois):

| Itabirito | semanas −4 a −2 | semana −1 | semana 0 |
| --- | --- | --- | --- |
| Crisântemo 2024 | 10–14 | 126 | 254 |
| Crisântemo 2025 | 3–29 | **741** | 217 |
| Kalanchoe 2024 | 69–211 | 328 | 365 |
| Kalanchoe 2025 | 143–188 | **731** | 544 |

- **Em Itabirito:** o crisântemo quase só vende em outubro e novembro. Em 2025 foram 657 em
  outubro e 364 em novembro, contra 20 a 150 nos outros meses. "Planta em vaso" vendeu, na
  semana de Finados, 1,8 vez o normal em 2024 e 3,0 vezes em 2025, com R$ 17 mil e R$ 26 mil a
  mais na semana.
- **Em Jardim Canadá, não:** o crisântemo vai de ~7 para 20–46 unidades, e "Planta em vaso"
  fica em 0,8 e 1,0 vez o normal. A loja de lá fecha no Finados.
- **Por que a categoria quase não mostra a alta:** "Planta em vaso" é um quarto das unidades
  de Plantas diversas em Itabirito. Mudas e forrações, que são metade da categoria, não sobem
  (0,67 vez o normal em 2025), e a alta do crisântemo se dilui no total.

## 3. Como o fator funciona

```
fator(loja, série, data)  = Σ venda ÷ Σ base, nos dias abertos de 6 dias antes até a data,
                            na ocorrência anterior da data (§2.1)
previsão ajustada         = previsão do SARIMAX × (1 + λ · (fator − 1)),
                            só nos dias abertos de 6 dias antes até a data, sem abertura excepcional
faixa de 95% ajustada     = limites do SARIMAX × o mesmo multiplicador
λ                         = 1 (fator cheio) ou 0,5 (fator pela metade)
```

O fator fica **fora** do SARIMAX por três motivos:

1. **O modelo trabalha em unidades** (sem `log1p`, ADR-017). Uma exógena "semana da data"
   somaria um número fixo de unidades, em vez de multiplicar a previsão.
2. **A janela de treino é de 365 dias.** Cada data aparece nela uma vez só, e o coeficiente
   seria estimado com uma única semana.
3. **O doc 03 já mostrou o risco:** a exógena `janela_7d_*` atribuía à semana um efeito que
   era do dia e gerou 12% do erro do ano.

Calculado fora, o fator usa todas as ocorrências passadas e pode ser encolhido para 1 (λ <
1) quando a evidência é fraca.

## 4. O teste

- **Séries:** as que o EDA indicou.
  - Flores de corte nas 2 lojas, no Dia da Mulher, no Dia das Mães, nos Namorados e no Natal.
  - Grama, Plantas diversas e Produtos de jardim de Itabirito, em Finados.
  - Flores de corte de Itabirito em Finados treina **sem** fator, só para fechar o total da
    loja (soma das 4 categorias, como no sistema).
- **Modelo:** a receita de produção sem mudança (`ConfigTreino()`, ADR-017). SARIMAX m = 7,
  d = 0, D = 0, com constante; ordem por AIC na janela de 365 dias antes da 1ª origem; janela
  deslizante de 365 dias; exógenas de calendário; fluxo do ADR-018.
- **Origens:** 20 por ocorrência, andando 1 dia, de 19 dias antes da data até a data, h =
  14. Cada dia da semana da data é previsto em vários horizontes. As 8 origens de 13 a 6
  dias antes têm a semana inteira à frente e medem o erro do total da semana.
- **Ocorrências testáveis:** as que têm 180 dias de histórico antes da 1ª origem.
  - **Entram:** as 4 datas de 2025, mais o Natal e o Finados de 2024.
  - **Ficam de fora**, por falta de histórico: o Dia da Mulher, o Dia das Mães e os Namorados
    de 2024.
  - **No total:** 10 ocorrências em Flores de corte e 2 em cada categoria de Finados.
- **De onde vem o fator:**
  - **Em 2025:** vem da ocorrência de 2024, como o sistema faria.
  - **Em 2024:** vem da ocorrência de 2025 (*fora de ordem*: o fator olha o futuro, o SARIMAX
    não), só para ter mais uma ocorrência.
  - A §5 mostra também o resultado só em ordem.
- **Métricas, nos dias abertos da semana da data:**
  - erro de cada dia relativo à naïve (Σ|erro| ÷ Σ|erro da naïve|, como nos docs 03 e 04);
  - erro do total da semana (Σ|previsto − vendido| ÷ Σ vendido, por origem);
  - previsto ÷ vendido;
  - cobertura e largura da faixa de 95%.
- **Controle:** o previsto ÷ vendido nos dias **fora** da semana, no mesmo backtest, onde o
  fator não mexe. Se o modelo já prevê pouco fora da data, qualquer aumento "ajuda", e o
  ganho não é da data.

## 5. Resultados

### 5.1 Flores de corte

Todas as ocorrências (5 por loja):

| | Jardim Canadá: sem · ½ fator · fator | Itabirito: sem · ½ fator · fator |
| --- | --- | --- |
| erro de cada dia ÷ naïve | 0,88 · **0,80** · 0,89 | **0,83** · 0,91 · 1,49 |
| erro do total da semana | 61% · 33% · **23%** | 54% · **32%** · 95% |
| previsto ÷ vendido nos dias da semana da data | 40% · 69% · 97% | 46% · 114% · 182% |
| cobertura da faixa de 95% | 81% · 84% · 88% | 77% · 96% · 100% |
| largura média da faixa (un./dia) | 143 · 247 · 350 | 155 · 381 · 607 |
| controle: previsto ÷ vendido fora da semana | 71% | 83% |

Só em ordem, com o fator de 2024 aplicado em 2025, o erro do total da semana fica assim
(sem · ½ fator · fator):
- Jardim Canadá: 60% · 30% · 23%;
- Itabirito: 52% · 28% · 109%.

Por ocorrência (vendido e previsto: média, por origem, do total da semana):

| Loja | Data | Fator | Vendido | Previsto sem · ½ · cheio | Erro da semana sem · ½ · cheio |
| --- | --- | ---: | ---: | --- | --- |
| JC | Mulher 2025 | 2,62 | 803 | 195 · 353 · 511 | 76% · 56% · 36% |
| JC | Mães 2025 | 2,72 | 766 | 282 · 524 · 766 | 63% · 32% · 1% |
| JC | Namorados 2025 | 1,64 | 415 | 296 · 391 · 486 | 29% · 6% · 17% |
| JC | Natal 2024 (fora de ordem) | 2,29 | 677 | 231 · 379 · 528 | 66% · 44% · 22% |
| JC | Natal 2025 | 3,03 | 534 | 245 · 494 · 742 | 54% · 10% · 39% |
| ITA | Mulher 2025 | 5,65 | 525 | 200 · 665 · 1.131 | 62% · 27% · 115% |
| ITA | Mães 2025 | 5,83 | 639 | 284 · 968 · 1.653 | 56% · 52% · 159% |
| ITA | Namorados 2025 | 4,42 | 698 | 296 · 801 · 1.306 | 58% · 15% · 87% |
| ITA | Natal 2024 (fora de ordem) | 1,52 | 556 | 218 · 274 · 330 | 61% · 51% · 41% |
| ITA | Natal 2025 | 2,21 | 424 | 307 · 492 · 677 | 28% · 16% · 60% |

Leitura:

- **Sem fator, o modelo prevê uma semana comum.** Prevê 195 a 310 un., quando a loja vende
  de 415 a 803. Nesses dias, a faixa de 95% cobre só 77–81% do vendido, abaixo do mínimo de
  90% do sistema.
- **O fator pela metade melhora o total da semana nas 10 ocorrências.** O erro cai 45% em
  Jardim Canadá e 40% em Itabirito. Nos dias fora da semana o modelo prevê 71–83% do
  vendido, e na semana da data só 40–46%: a falta é maior na data, então o ganho vem do
  efeito dela, não de um viés geral do modelo.
- **O fator cheio não serve.**
  - **Em Itabirito:** os fatores de 2024 (4,4 a 5,8) foram bem maiores que os de 2025 (2,9 a
    3,5), e o fator cheio erra para cima de 87% a 159%. Com uma ocorrência só, o fator é
    ruidoso e volta para perto de 1 no ano seguinte.
  - **Em Jardim Canadá:** o fator cheio também funciona (23%), mas perde para a metade em 2
    das 5 ocorrências.
  - **Encolher pela metade** é o que dá certo nas duas lojas.
- **O erro de cada dia quase não muda:** melhora 10% em Jardim Canadá e piora 9% em
  Itabirito. O fator sobe todos os dias da semana igualmente, mas o pico cai na véspera, ou
  na quinta, ou no sábado, conforme a data e o ano. **O fator acerta o quanto a semana vende,
  não em que dia.**
- **A faixa de 95%** passa a cobrir 84–96% do vendido, mas fica 1,7 a 2,5 vezes mais larga
  nesses dias.

### 5.2 Finados em Itabirito

| | erro do total da semana: sem · ½ fator · fator | erro de cada dia ÷ naïve | controle: previsto ÷ vendido fora da semana |
| --- | --- | --- | --- |
| Grama | 66% · 46% · 26% | 1,02 · 0,91 · 0,85 | **60%** |
| Plantas diversas | 27% · 30% · 42% | 1,01 · 0,99 · 1,15 | 98% |
| Produtos de jardim | 39% · 66% · 100% | 0,97 · 1,36 · 2,03 | **128%** |
| Total da loja (soma das 4) | 45% · 26% · 32% | 1,00 · 0,79 · 0,82 | 87% |

Por ocorrência, erro do total da semana:

| Série | 2024 (fora de ordem) sem · ½ · cheio | 2025 sem · ½ · cheio |
| --- | --- | --- |
| Grama | 65% · 46% · 26% | 68% · 47% · 27% |
| Plantas diversas | 43% · 37% · 31% | **9% · 22% · 54%** |
| Produtos de jardim | 56% · 51% · 47% | 14% · 89% · 178% |
| Total da loja | 54% · 43% · 31% | 34% · 7% · 33% |

Leitura:

- **Grama:** o fator melhora muito, mas o controle explica.
  - O modelo prevê só 60% do vendido também **fora** da semana de Finados.
  - Outubro e novembro são temporada de grama, e o SARIMAX com `d = 0` puxa a previsão para a
    média do ano (custo registrado no ADR-017 e no `trainer.py`).
  - Qualquer aumento nessas semanas melhoraria Grama, então o ganho não é efeito de Finados.
    O problema é de nível.
- **Produtos de jardim:** o modelo já prevê acima do vendido (128% fora da semana). O fator
  de 2024 (2,80) aplicado em 2025, quando a alta foi de 1,20, multiplica o erro do total da
  semana por 6 com o fator pela metade e por 13 com o fator cheio.
- **Plantas diversas:** é o caso limpo (controle de 98%), e a alta tem explicação: o
  crisântemo e o kalanchoe (§2.3).
  - **Mas o fator não ajuda:** melhora 2024 (fora de ordem, de 43% para 37%) e piora 2025
    (de 9% para 22%). Em 2025, o modelo sem fator já errava a semana em só 9%.
  - **Por quê:** o fator de 2024 (1,70) foi bem maior que a alta de 2025 (1,20).
  - **Mudou com a classificação nova:** na rodada com a classificação anterior, com a grama
    preta ainda em Plantas diversas, o fator pela metade melhorava as 2 ocorrências.
- **Total da loja:** melhora com o fator pela metade, mas puxado por Grama, cujo ganho o
  controle já desqualificou.

## 6. Faz sentido?

| Série | Datas | Faz sentido? | Por quê |
| --- | --- | --- | --- |
| Flores de corte, Jardim Canadá | Mulher, Mães, Namorados, Natal | **Sim, com o fator pela metade** | Total da semana −45%, melhor nas 5 ocorrências; a falta do modelo é maior na data (40%) que fora dela (71%) |
| Flores de corte, Itabirito | Mulher, Mães, Namorados, Natal | **Sim, com o fator pela metade** | Total da semana −40%, melhor nas 5 ocorrências; o fator cheio erra para cima de 87% a 159% |
| Flores de corte, as 2 lojas | Finados, Dia dos Pais | Não | Sem efeito no EDA; a flor de Finados é a em vaso (§2.3) |
| Grama, Itabirito | Finados | **Não** | O ganho vem do nível baixo do modelo no período inteiro (controle de 60%), não da data |
| Produtos de jardim, Itabirito | Finados | **Não** | Multiplica o erro da semana por 6 (fator pela metade) numa ocorrência |
| Plantas diversas, Itabirito | Finados | **Não** | A alta do crisântemo é real, mas o fator piora 2025 (9% → 22%); diluída na categoria, a alta muda muito de um ano para o outro |
| Outras categorias e total de Jardim Canadá | todas | Não | Nenhuma data sai da faixa das semanas comuns |

Mesmo onde faz sentido, o fator corrige **quanto a semana vende**. A tela mostra a previsão
dia a dia, e o dia do pico continua errado. Para a loja, o número útil é o total de flores da
semana da data, e é ele que o fator melhora.

O peso no negócio é pequeno: Flores de corte é 1,5% das unidades em Jardim Canadá e 4,8% em
Itabirito (2,4% e 7,6% do faturamento). O fator não muda o total da loja de forma
perceptível. Ele importa para a compra de flores: é produto perecível, e o sistema hoje
prevê menos da metade do que a semana vende.

O crisântemo de Finados em Itabirito é a mesma situação (perecível, compra concentrada numa
semana), mas o sistema não tem série dele: prevê Plantas diversas inteira, onde a alta se
dilui. Prever o crisântemo e o kalanchoe de Itabirito nessa época pediria uma série própria,
fora do que o sistema faz hoje (ADR-017).

## 7. No sistema (ADR-019)

Adotado em Flores de corte, nas 4 datas de presente (e no Ano Novo, §9.2), pelo ADR-019; a
queda de 26 a 31/12 e do Dia do Trabalho nas outras séries, pela §9.3. As escolhas da alta, a
partir deste teste:

- **O fator é recalculado das vendas a cada treino** (`backend/domain/models/datas_comemorativas.py`).
  Junta as últimas 3 ocorrências com as 4 semanas seguintes já vendidas, entra pela metade e
  fica entre 1 e 3. Data sem ocorrência passada completa fica sem ajuste.
- **Aplicado depois de cada `prever` do `trainer.py`**: no walk-forward (com a venda anterior
  à origem), no complemento e na previsão final. Multiplica o previsto e a faixa dos dias
  abertos de 6 dias antes até a data, sem abertura excepcional.
- **As datas vêm da regra** (2º domingo de maio...), não de `calendar_days.special_date_name`:
  o calendário gravado vai até 31/12/2026.
- **O multiplicador fica gravado** em `series_forecasts.event_factor` e
  `forecast_history.event_factor`. O previsto do modelo sem o ajuste é `predicted / event_factor`,
  e é com ele que se mede, depois de cada data, se o ajuste ajudou.
- **O walk-forward do sistema quase nunca mostra o efeito:** as 56 origens terminam na última
  venda. Com a base atual (até 28/02/2026), cobrem de dezembro de 2025 a fevereiro de 2026, e
  só as primeiras origens pegam 3 dias da semana do Natal: o MASE de Flores de corte muda
  menos de 1% e a cobertura não muda. A avaliação do fator fica neste experimento, refeito
  quando entrar um ano novo de vendas.

## 8. Limitações

- **Poucas ocorrências:** 1 por data e loja em ordem, mais 1 fora de ordem no Natal. O fator
  de cada data é estimado com uma única semana, e é por isso que o fator pela metade vence o
  cheio.
- **Teste por janela, não pelo ano:** as 20 origens por ocorrência cobrem só as semanas em
  volta da data. Fora da semana, o fator não muda nada por construção.
- **Base da semana:** a mediana do mesmo dia da semana usa também as 4 semanas seguintes. No
  sistema, isso vale só para a ocorrência passada, que já está toda no histórico.
- **A classificação dos produtos mexe no resultado:** a de 2026-11-04 quase não mudou Flores
  de corte, mas inverteu o resultado de Plantas diversas em Finados (§5.2). Uma mudança de
  categoria futura pede refazer o teste.

## 9. Feriados e outras datas, em todas as séries (2026-11-05)

### 9.1 EDA

`training_scripts/datas_comemorativas/eda_eventos.py` olha **todos** os eventos do calendário em
**todas** as séries do sistema (as 4 categorias e os 15 produtos de grama com previsão, por
loja), no fluxo sem encomendas.
- **Eventos:** feriados nacionais, fechamentos observados, Páscoa, as 6 datas comemorativas e,
  pela regra, Dia dos Avós, Dia da Árvore, Dia da Secretária, Dia do Professor e Black Friday.
- **Janelas:** os 3 dias abertos antes, a semana até a data, o próprio dia (se a loja abre) e
  os 2 dias abertos depois.
- **Base:** mesmo dia da semana nas 6 semanas antes e depois, longe de qualquer evento.
- **Critério:** efeito em todas as ocorrências acima do percentil 90 das janelas comuns (ou
  abaixo do 10), com média ≥ 1,25 (ou ≤ 0,80).

**Resultado:** 51 de 507 combinações (10%) com efeito consistente.
- **Controle:** nas datas falsas (eventos deslocados 3 semanas), só 1,6%, o que dá uns 8 dos
  51 por acaso. Por isso só contam os efeitos com explicação no negócio e repetidos em mais de
  uma loja ou janela.
- **Flores de corte, altas:**
  - as 4 datas de presente, de novo;
  - o **Ano Novo**, nas 2 lojas: 4,0× nos 3 dias abertos antes de 1º/01, +240 a +300 flores
    por loja, a flor do Réveillon.
- **Grama, Plantas diversas e Produtos de jardim, só quedas:**
  - **no fim de ano:** de 0,46 a 0,63 do normal nos dias antes de 1º/01, em Jardim Canadá nas
    3 categorias e na Grama de Itabirito;
  - **nos feriados prolongados de abril e maio** (Semana Santa, Tiradentes, Dia do Trabalho):
    0,47 a 0,61 na Grama.
- **Sem efeito, ou só acaso:** o resto das datas e dos feriados, e as altas isoladas de produtos
  de grama que vendem em lotes (ex.: São Carlos de Jardim Canadá, 25× antes do Dia da Árvore).

### 9.2 Teste: Ano Novo em Flores de corte e fator de redução (`--grupo feriados`)

Mesmo protocolo da §4 (receita de produção, 20 origens por ocorrência), com duas diferenças.
A base usa 6 semanas e fica longe também dos feriados, como na EDA. E o fator pode dar abaixo
de 1. A janela é de 6 dias antes até a data: para o Ano Novo, de 26 a 31/12. Tiradentes de 2025
caiu na segunda depois da Páscoa e ficou fora, porque a semana dele é a mesma.

Erro do total da semana (sem · ½ fator · fator), e o controle (previsto ÷ vendido fora da
semana):

| Série | Data | 2025 | 2026 | Controle |
| --- | --- | --- | --- | --- |
| Flores de corte, JC | Ano Novo | 34% · 17% · 47% *(fora de ordem)* | 49% · **28%** · 6% | 68% |
| Flores de corte, ITA | Ano Novo | 63% · 47% · 31% *(fora de ordem)* | **30%** · 31% · 92% | 96% |
| Grama, ITA | Ano Novo | 278% · 174% · 70% *(fora de ordem)* | 268% · 156% · **45%** | **106%** |
| Grama, JC | Ano Novo | 117% · 96% · 74% *(fora de ordem)* | 83% · 38% · **8%** | 125% |
| Plantas diversas, JC | Ano Novo | 93% · 54% · 16% *(fora de ordem)* | 142% · 91% · **41%** | 145% |
| Produtos de jardim, JC | Ano Novo | 90% · 44% · 2% *(fora de ordem)* | 128% · 96% · **63%** | 129% |
| Total da loja, JC | Ano Novo | 97% · 69% · 40% *(fora de ordem)* | 99% · 57% · **15%** | 131% |
| Grama, ITA | Sexta-feira Santa | 20% · **13%** · 45% | — | 245% |
| Grama, ITA | Dia do Trabalho | 244% · 152% · **60%** | — | 139% |
| Grama, JC | Sexta-feira Santa | 53% · 22% · **9%** | — | 110% |
| Grama, JC | Dia do Trabalho | 77% · 79% · 80% (fator 1,02: sem queda) | — | 126% |

Fatores: Flores JC 2,23 / 1,85, ITA 1,84 / 2,73; Grama ITA 0,45 / 0,39 (Ano Novo), 0,46 (Sexta
Santa), 0,47 (Trabalho); Grama JC 0,80 / 0,50 (Ano Novo), 0,60 (Sexta Santa); Plantas JC
0,60 / 0,58; Produtos JC 0,52 / 0,72.

Leitura:

- **Grama de Itabirito no fim de ano: o caso mais claro.**
  - Fora da semana, o modelo prevê quase certo (106% do vendido); na semana de 26 a 31/12, prevê
    3,6 vezes o que a loja vende.
  - O fator cheio (0,39 a 0,45) melhora as 2 ocorrências: erro de 268–278% para 45–70%.
  - O fator é estável de um ano para o outro, e é por isso que o cheio vence a metade, ao
    contrário de Flores de corte.
- **Jardim Canadá no fim de ano (Grama, Plantas diversas, Produtos de jardim):**
  - o fator melhora as 2 ocorrências nas 3 categorias, e o total da loja (erro de 99% para 15%
    em 2026, em ordem, com o fator cheio);
  - mas o controle mostra que o modelo também prevê de 25% a 45% acima do vendido **fora** da
    semana: a queda é da temporada de festas, que vai do Natal ao começo de janeiro, e uma
    janela só de 26 a 31/12 corrige parte dela;
  - o fator cheio reduz a faixa de 95% junto: na Grama de Jardim Canadá, a cobertura nesses
    dias cai de 71% para 53%.
- **Feriados prolongados na Grama:** uma ocorrência testável de cada, porque os de 2024 não têm
  180 dias de histórico antes.
  - **Dia do Trabalho em Itabirito:** ajuda muito.
  - **Sexta-feira Santa em Jardim Canadá:** ajuda.
  - **Sexta-feira Santa em Itabirito:** só ajuda pela metade. O fator cheio piora, e o controle
    (245%) mostra o modelo errando o período inteiro.
  - **Dia do Trabalho em Jardim Canadá:** não há queda.
- **Ano Novo em Flores de corte:**
  - **Em Jardim Canadá:** a metade do fator melhora as 2 ocorrências (erro de 34% para 17% e de
    49% para 28%), como nas outras datas de presente.
  - **Em Itabirito:** melhora a ocorrência fora de ordem e piora um pouco a que está em ordem
    (30% para 31%). O fator de 2025 (2,73) foi bem maior que a alta de 2026 (1,84).

| Série | Data | Faz sentido? |
| --- | --- | --- |
| Flores de corte | Ano Novo | **Sim em Jardim Canadá; neutro em Itabirito.** Como o fator sai das vendas de cada loja, entrar com o Ano Novo nas 2 lojas, com a metade, é coerente com as outras datas de presente. **Adotado** (ADR-019) |
| Grama, Itabirito | Ano Novo (26–31/12) | **Sim, com fator de redução cheio**: controle limpo, 2 de 2, fator estável. **Adotado** (§9.3) |
| Grama, Plantas diversas, Produtos de jardim, JC | Ano Novo (26–31/12) | **A §9.3 resolveu:** a queda é de 26 a 31/12, não da temporada, e a inteira vence. **Adotado** |
| Grama, as 2 lojas | Sexta-feira Santa, Dia do Trabalho | **Sexta-feira Santa, ainda não**: não se repete. **Dia do Trabalho:** adotado onde cai nos 2 anos, hoje só a Grama de Itabirito (§9.3) |

O ADR-019 não deixava o multiplicador ficar abaixo de 1. A §9.3 testou a janela e o tamanho
da redução, e o ADR-019 ganhou a regra da queda.

### 9.3 A queda: onde fica e o teste com o fator do backend (2026-11-05)

**EDA** (`eda_reducao.py`): venda ÷ base dia a dia, de 01/12 a 31/01, nas 2 temporadas
(2024/25 e 2025/26), em blocos, e nas semanas dos feriados de abril a junho. Base e critério
da §9.1: as 2 temporadas abaixo do percentil 10 das semanas comuns, média ≤ 0,80.

- **A queda é de 26 a 31/12, não da temporada.** De 15 a 24/12 e de 2 a 20/01 nenhuma série
  cai nas 2 temporadas, e a Grama de Itabirito chega a vender o dobro na semana do Natal.
  Logo, a janela maior (do Natal a ~10/01) que a §9.2 pedia não tem apoio nos dados.
- **De 26 a 31/12, as 2 temporadas caem em:**
  - Grama de Itabirito (0,46 e 0,46) e a Esmeralda (ITO) de lá (0,54 e 0,35);
  - Plantas diversas (0,60 e 0,63) e Produtos de jardim (0,73 e 0,54) de Jardim Canadá;
  - a Esmeralda (0,37 e 0,75) e a São Carlos (0,0 e 0,12) de Jardim Canadá.
- **Caem num ano e não no outro:** a Grama de Jardim Canadá (0,55 e 0,94), as Plantas
  diversas de Itabirito (2,21 e 0,71). Os Produtos de jardim de Itabirito não caem.
- **Feriados:**
  - na semana do Dia do Trabalho, só a Grama de Itabirito cai nos 2 anos (0,47 e 0,48);
  - Sexta-feira Santa e Corpus Christi não se repetem;
  - os 2 dias depois de Tiradentes caem na Grama de Itabirito, mas em 2025 eles foram a
    semana da Páscoa.
- **Flores de corte de Itabirito cai de 2 a 10/01** (0,55 e 0,62), depois do Réveillon. É uma
  loja só, e fica fora.

**Teste** (`--grupo reducao`): o mesmo protocolo da §4 (receita de produção, 20 origens por
ocorrência), nas 7 séries com a queda de 26 a 31/12 (a Grama de Jardim Canadá entra como
controle) e, na Grama e na Esmeralda (ITO) de Itabirito, no Dia do Trabalho. O fator é o do
backend: base de 4 semanas, datas pela regra, só com a venda anterior à 1ª origem. As
ocorrências de 2026 e o Dia do Trabalho de 2025 estão em ordem (fator do ano anterior); as do
Ano Novo de 2025 tiram o fator de 2026 (fora de ordem).

Erro do total da semana (sem · ½ queda · queda inteira), o fator, e o controle (previsto ÷
vendido fora da semana):

| Série | Ano Novo 2025 *(fora de ordem)* | Ano Novo 2026 | Fator 2025 / 2026 | Controle |
| --- | --- | --- | --- | --- |
| Grama, ITA | 278% · 155% · **32%** | 268% · 147% · **27%** | 0,35 / 0,35 | 106% |
| Esmeralda (ITO), ITA | 195% · 82% · **32%** | 458% · 302% · **146%** | 0,23 / 0,44 | 86% |
| Plantas diversas, JC | 93% · 50% · **7%** | 142% · 91% · **39%** | 0,55 / 0,58 | 145% |
| Produtos de jardim, JC | 90% · 45% · **1%** | 128% · 95% · **62%** | 0,53 / 0,71 | 129% |
| Esmeralda, JC | 157% · 100% · **42%** | 118% · 44% · **29%** | 0,55 / 0,33 | 123% |
| São Carlos, JC | a loja não vendeu | 849% · 374% · **90%** (piso 0,2) | 0,10 / 0,0 | 161% |
| Grama, JC *(controle)* | 117% · 75% · **33%** | 83% · 41% · **3%** | 0,61 / 0,53 | 125% |
| Grama, ITA — Dia do Trabalho 2025 | | 244% · 159% · **73%** | 0,50 | 139% |
| Esmeralda (ITO) — Dia do Trabalho 2025 | | 194% · 172% · **149%** | 0,85 | 147% |

Erro de cada dia relativo à naïve, nas 2 ocorrências, sem → com a queda inteira:
- **Grama, ITA:** 0,82 → 0,22;
- **Esmeralda (ITO):** 0,63 → 0,20;
- **Plantas diversas, JC:** 1,16 → 0,42;
- **Produtos de jardim, JC:** 1,02 → 0,53;
- **Esmeralda, JC:** 0,95 → 0,59;
- **São Carlos, JC:** 1,69 → 0,18;
- **Grama, JC:** 0,83 → 0,62.

A faixa de 95% encolhe junto. A cobertura nesses dias sobe onde o modelo errava muito para
cima (Plantas diversas, JC: 71% → 96%; Produtos de jardim, JC: 70% → 89%) e cai em outras
(Grama, JC: 71% → 60%; Esmeralda, JC: 87% → 69%).

Leitura:
- **A queda inteira vence a metade e o sistema em todas as ocorrências do Ano Novo**, nas 2
  ordens, e nas 2 do Dia do Trabalho. Na São Carlos de 2025, a loja não vendeu nada na
  semana, e só o erro de cada dia compara. Ao contrário da alta de Flores de corte, o fator da
  queda muda pouco de um ano para o outro (0,35 e 0,35 na Grama de Itabirito; 0,55 e 0,58 nas
  Plantas diversas), e a metade deixa metade do erro.
- **O ganho não é só da semana.** Em Jardim Canadá o modelo prevê 23% a 61% acima do vendido
  também fora dela (controle): a previsão de dezembro vem alta. A semana de 26 a 31/12 é onde
  isso mais pesa (2 a 5 vezes o vendido). Em Itabirito, fora da semana o modelo acerta (86% a
  106%), e a queda é só dela.
- **A Grama de Jardim Canadá, que caiu num ano só, também melhora:** o fator dela vem de 0,53 a
  0,61 e o modelo está alto. Ela entra pela regra a partir do Ano Novo de 2027, com 2025 e 2026
  abaixo de 0,8 (0,53 e 0,61).
- **Dia do Trabalho:** na Grama de Itabirito, uma ocorrência e um ganho grande (de 244% para 73%),
  com a queda repetida nos 2 anos do EDA. A Esmeralda (ITO) cai pouco (0,85) e não entra.

**Decisão (ADR-019, regra da queda):**
- **Onde:** em todas as séries menos Flores de corte (categorias e produtos de grama).
- **Quando:** de 26 a 31/12 (Ano Novo) e na semana do Dia do Trabalho, e só se cada uma das
  últimas ocorrências da data (2 ou 3) ficou em até 0,8 de uma semana comum. É o critério do
  EDA, recalculado a cada treino.
- **Quanto:** a queda inteira, com piso de 0,2: a São Carlos não vendeu nada na semana de 2025,
  e com o piso o erro da semana de 2026 cai de 100% para 90%, e a faixa volta a cobrir o
  vendido.

Com as vendas até 28/02/2026, a regra pega no Ano Novo de 2027:
- **Jardim Canadá:** Grama 0,58, Plantas diversas 0,57, Produtos de jardim 0,61, Esmeralda 0,41,
  São Carlos 0,20 (piso);
- **Itabirito:** Grama 0,35, Esmeralda (ITO) 0,31, São Carlos 0,21.

No Dia do Trabalho de 2026, só a Grama de Itabirito (0,54). As Plantas diversas e os Produtos
de jardim de Itabirito e a Amendoim das 2 lojas ficam fora, porque caíram num ano só. A São
Carlos de Itabirito, que a regra também pega, foi testada depois (§9.4).

Com 1 ocorrência só, a regra não ajusta: em 2025/26, o teste em ordem usou o fator de uma
ocorrência, que o sistema não usaria. O teste valida o tamanho do fator. A escolha das séries
(2 ocorrências abaixo de 0,8) é a do EDA.

### 9.4 As que ficaram de fora (2026-11-05)

Mesmo protocolo e fator da §9.3 (`--grupo reducao`), em duas perguntas que a §9.3 deixou
abertas.

**A São Carlos de Itabirito,** que a regra da queda pega sem ter passado pelo teste. Fator
0,05 (2025, fora de ordem) e 0,30 (2026, em ordem). Erro do total da semana, sem → com a queda
(piso 0,2):
- **2025:** de 703% para 61%;
- **2026:** de 8.133% para 2.386%. A loja vendeu 8 unidades na semana.

O modelo dessa grama prevê 20 vezes o vendido também fora da semana (controle de 2.027%): a
série é fraca. A queda corta a maior parte do erro onde ele mais pesa, e a série continua na
regra.

**A queda de Flores de corte depois do Réveillon** (de 2 a 8/01, a janela da data em 08/01),
que a EDA viu em Itabirito (0,55 e 0,62 de 2 a 10/01). Jardim Canadá entra como controle.

| Série | 2025 (fator de 2024) | 2026 (fator de 2025) |
| --- | --- | --- |
| Flores de corte, ITA | fator 1,60 · erro 156% → 309% | fator 0,45 · erro 103% → **9%** |
| Flores de corte, JC *(controle)* | fator 1,99 · erro 13% → 73% | fator 1,62 · erro 4% → 56% |

(erro do total da semana, sem → com o fator inteiro)

- **Itabirito:**
  - em 2024 a semana subiu (1,60), em 2025 caiu (0,45), e o fator só acerta quando o ano
    anterior caiu;
  - pela regra da queda, a série só entraria com 2 ocorrências seguidas abaixo de 0,8, ou
    seja, a partir de janeiro de 2027;
  - a evidência de hoje é 1 ocorrência, numa loja.
- **Jardim Canadá:** não cai, e o modelo acerta a semana sem ajuste.
- **Decisão:** fica fora do sistema. Refazer com janeiro de 2027. Se a semana cair de novo
  em Itabirito, Flores de corte passa a ter também a regra da queda, só nessa janela.

A Sexta-feira Santa espera as vendas de abril de 2026: a de 2025 é a única testável hoje
(§9.2), e o resultado não se repetiu entre as lojas.

## 10. Como reproduzir

A partir de `ia-predictor/`:

```bash
python -m training_scripts.datas_comemorativas.fator_multiplicativo --eda        # §2.2
python -m training_scripts.datas_comemorativas.fator_multiplicativo --preparar   # séries em cache
python -m training_scripts.datas_comemorativas.fator_multiplicativo --listar     # 18 ocorrências
python -m training_scripts.datas_comemorativas.fator_multiplicativo --caso 0     # uma por processo
python -m training_scripts.datas_comemorativas.fator_multiplicativo --consolidar # §5
python -m training_scripts.datas_comemorativas.eda_eventos [--controle]         # §9.1
python -m training_scripts.datas_comemorativas.fator_multiplicativo --grupo feriados --listar  # §9.2
python -m training_scripts.datas_comemorativas.eda_reducao                                     # §9.3
python -m training_scripts.datas_comemorativas.fator_multiplicativo --grupo reducao --listar   # §9.3 e §9.4
```

O `--preparar` monta as séries da `BaseClassificada03.csv`: depois de mudar a classificação,
rodar o pré-processamento e o `--preparar` de novo.

Cada ocorrência leva de 1 a 4 min (escolha da ordem + 20 ajustes). No proot de
desenvolvimento, rodar no máximo 3 a 4 de uma vez. Com 6 processos em paralelo, o Android
derrubou o Termux 4 vezes seguidas, inclusive depois que o cache baixou a memória de cada
processo de ~500 MB para ~130 MB.
