# 08 — Fator multiplicativo das datas comemorativas: EDA e teste no SARIMAX de produção

**Data:** 2026-10-31 · **Status:** experimento concluído; adotado em Flores de corte pelo
ADR-019 (2026-11-03)
**Script:** `ia-predictor/training_scripts/datas_comemorativas/fator_multiplicativo.py`
**Resultados:** `ia-predictor/training_scripts/results/metrics/fator_datas_comemorativas/` (EDA e
backtest por ocorrência) e `fator_datas_comemorativas.csv` (consolidado)

---

## 1. A pergunta

A floricultura vende mais nas datas comemorativas? Se vende, multiplicar a previsão dos dias
em volta da data por um fator melhora a previsão das séries do sistema (ADR-017)? Tudo sobre
o **fluxo**: sem as encomendas grandes (média + 4 desvios dos pedidos da loja, ADR-018).

Resposta curta:

- **Flores de corte vende de 1,5 a 5,7 vezes uma semana comum** na semana do Dia da Mulher,
  do Dia das Mães, do Dia dos Namorados e do Natal, nas 2 lojas. Finados e Dia dos Pais não
  mexem com flores.
- **O total da loja não sobe** em Jardim Canadá em nenhuma data. Em Itabirito, sobe na semana
  de Finados (1,4 a 1,8) e, em parte, na do Dia das Mães.
- **Em Flores de corte, o fator pela metade faz sentido:** o erro do total da semana cai 42%
  a 47%, nas 10 ocorrências testadas. O erro de cada dia não melhora de forma consistente.
- **Em Finados de Itabirito, não:** o ganho em Grama vem de o modelo já prever pouco no
  período inteiro, não da data. Em Produtos de jardim o fator piora muito. Em Plantas
  diversas o ganho é pequeno e vem de 2 ocorrências.

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

| Data | Flores · JC (0,57–2,24) | Flores · ITA (0,61–2,30) | Total · JC (0,76–1,38) | Total · ITA (0,74–1,54) |
| --- | --- | --- | --- | --- |
| Dia da Mulher | **2,62 / 4,17** | **5,62 / 3,54** | 1,08 / 0,83 | 1,41 / 0,97 |
| Dia das Mães | **2,74 / 4,23** | **5,74 / 2,92** | 0,95 / 1,12 | 1,32 / **1,64** |
| Dia dos Namorados | 1,64 / 2,22 | **4,55 / 3,07** | 1,03 / 0,98 | 1,25 / 1,08 |
| Natal | **3,03 / 2,30** | 2,21 / 1,51 | 1,04 / 0,97 | 1,22 / 1,33 |
| Finados | 1,69 / 0,74 | 1,20 / 0,84 | 0,98 / 0,88 | **1,80 / 1,40** |
| Dia dos Pais | 1,16 / 1,33 | 1,58 / 1,24 | 1,10 / 1,08 | 1,01 / 0,97 |

- **Flores de corte** fica acima de 95% das semanas comuns, ou perto disso, nas 4 datas de
  presente, nas 2 lojas e nos 2 anos.
  - **Onde fica o pico:** nas datas que caem em dia útil (Mulher e Namorados), na véspera e
    no dia: 9 a 16 vezes a base em Itabirito nos Namorados. No Dia das Mães (domingo, loja
    fechada em Jardim Canadá), o pico se espalha de quinta a sábado.
  - **Em unidades:** uma semana comum de flor vende cerca de 290–300 un. por loja; essas
    semanas vendem de 400 a 800.
- **Total da loja em Jardim Canadá:** nenhuma data sai da faixa. Flores de corte é 1,5% das
  unidades e 2,4% do faturamento da loja, e o pico não aparece no total.
- **Total da loja em Itabirito:** Finados (1,80 e 1,40) é a única alta que pega a loja
  inteira, em Grama (2,26 / 1,98), Plantas diversas (1,74 / 1,31) e Produtos de jardim (2,75
  / 1,19). Mas Grama de Itabirito é tão instável que, em 5% das semanas comuns, o fator passa
  de 3,5. Flores de corte é 4,8% das unidades e 7,6% do faturamento em Itabirito.
- **Correção ao `00-eda_report.md` §3.4:** a queda de Grama nas datas (0,2 no Dia dos Pais,
  por exemplo) quase toda some quando se compara com o mesmo dia da semana. Em Jardim Canadá,
  Grama fica entre 0,69 e 1,25, dentro da faixa comum. A §3.4 comparava com a média geral da
  série, sem descontar o dia da semana. Provavelmente as datas que caem no domingo (Mães e
  Pais) puxavam para a janela dias de loja fechada, de venda zero.

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
- **Ocorrências testáveis:** as que têm 180 dias de histórico antes da 1ª origem. São as 4
  datas de 2025, mais o Natal e Finados de 2024. As de 2024 do Dia da Mulher, do Dia das Mães
  e dos Namorados ficam de fora, por falta de histórico. No total, 10 ocorrências em Flores
  de corte e 2 em cada categoria de Finados.
- **De onde vem o fator:** o de 2025 vem da ocorrência de 2024, como o sistema faria. O de
  2024 vem da de 2025 (*fora de ordem*: o fator olha o futuro, o SARIMAX não), só para ter
  mais uma ocorrência. A §5 mostra também o resultado só em ordem.
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
| erro de cada dia ÷ naïve | 0,87 · **0,79** · 0,91 | **0,83** · 0,90 · 1,48 |
| erro do total da semana | 60% · 32% · **24%** | 54% · **32%** · 94% |
| previsto ÷ vendido nos dias da semana da data | 41% · 70% · 100% | 46% · 113% · 181% |
| cobertura da faixa de 95% | 80% · 85% · 88% | 77% · 96% · 100% |
| largura média da faixa (un./dia) | 144 · 249 · 353 | 155 · 382 · 609 |
| controle: previsto ÷ vendido fora da semana | 72% | 83% |

Só em ordem, com o fator de 2024 aplicado em 2025, o erro do total da semana fica assim
(sem · ½ fator · fator):
- Jardim Canadá: 59% · 28% · 25%;
- Itabirito: 53% · 27% · 107%.

Por ocorrência (vendido e previsto: média, por origem, do total da semana):

| Loja | Data | Fator | Vendido | Previsto sem · ½ · cheio | Erro da semana sem · ½ · cheio |
| --- | --- | ---: | ---: | --- | --- |
| JC | Mulher 2025 | 2,62 | 803 | 199 · 360 · 521 | 75% · 55% · 35% |
| JC | Mães 2025 | 2,74 | 766 | 282 · 526 · 771 | 63% · 31% · 1% |
| JC | Namorados 2025 | 1,64 | 416 | 296 · 390 · 485 | 29% · 6% · 16% |
| JC | Natal 2024 (fora de ordem) | 2,30 | 677 | 232 · 382 · 532 | 66% · 44% · 21% |
| JC | Natal 2025 | 3,03 | 536 | 269 · 542 · 815 | 50% · 1% · 52% |
| ITA | Mulher 2025 | 5,62 | 525 | 201 · 664 · 1.128 | 62% · 27% · 115% |
| ITA | Mães 2025 | 5,74 | 648 | 283 · 955 · 1.627 | 56% · 47% · 151% |
| ITA | Namorados 2025 | 4,55 | 701 | 294 · 816 · 1.338 | 58% · 16% · 91% |
| ITA | Natal 2024 (fora de ordem) | 1,51 | 557 | 218 · 274 · 329 | 61% · 51% · 41% |
| ITA | Natal 2025 | 2,21 | 429 | 308 · 495 · 681 | 28% · 15% · 59% |

Leitura:

- **Sem fator, o modelo prevê uma semana comum.** Prevê 200 a 310 un., quando a loja vende
  de 416 a 803. Nesses dias, a faixa de 95% cobre só 77–80% do vendido, abaixo do mínimo de
  90% do sistema.
- **O fator pela metade melhora o total da semana nas 10 ocorrências.** O erro cai 47% em
  Jardim Canadá e 42% em Itabirito. Nos dias fora da semana o modelo prevê 72–83% do
  vendido, e na semana da data só 41–46%: a falta é maior na data, então o ganho vem do
  efeito dela, não de um viés geral do modelo.
- **O fator cheio não serve.** Em Itabirito, os fatores de 2024 (4,5 a 5,7) foram bem maiores
  que os de 2025 (2,9 a 3,5), e o fator cheio erra para cima de 91% a 151%. Com uma
  ocorrência só, o fator é ruidoso e volta para perto de 1 no ano seguinte; encolher pela
  metade é o que dá certo nas duas lojas. Em Jardim Canadá o fator cheio também funciona
  (24%), mas perde para o meio em 2 das 5 ocorrências.
- **O erro de cada dia quase não muda:** melhora 9% em Jardim Canadá e piora 8% em
  Itabirito. O fator sobe todos os dias da semana igualmente, mas o pico cai na véspera, ou
  na quinta, ou no sábado, conforme a data e o ano. **O fator acerta o quanto a semana vende,
  não em que dia.**
- **A faixa de 95%** passa a cobrir 85–96% do vendido, mas fica 1,7 a 2,5 vezes mais larga
  nesses dias.

### 5.2 Finados em Itabirito

| | sem · ½ fator · fator: erro do total da semana | erro de cada dia ÷ naïve | controle: previsto ÷ vendido fora da semana |
| --- | --- | --- | --- |
| Grama | 63% · 43% · 23% | 1,01 · 0,90 · 0,84 | **58%** |
| Plantas diversas | 32% · 26% · 36% | 1,04 · 0,90 · 1,05 | 96% |
| Produtos de jardim | 39% · 74% · 109% | 0,97 · 1,44 · 2,12 | **131%** |
| Total da loja (soma das 4) | 44% · 27% · 38% | 1,00 · 0,79 · 0,87 | 86% |

Por ocorrência, erro do total da semana:

| Série | 2024 (fora de ordem) sem · ½ · cheio | 2025 sem · ½ · cheio |
| --- | --- | --- |
| Grama | 67% · 51% · 34% | 59% · 34% · 10% |
| Plantas diversas | 46% · 38% · 29% | 17% · 13% · 44% |
| Produtos de jardim | 58% · 54% · 50% | 12% · 104% · 199% |
| Total da loja | 56% · 45% · 34% | 30% · 6% · 41% |

Leitura:

- **Grama:** o fator melhora muito, mas o controle explica. O modelo prevê só 58% do
  vendido também **fora** da semana de Finados. Outubro e novembro são temporada de grama, e
  o SARIMAX com `d = 0` puxa a previsão para a média do ano (custo registrado no ADR-017 e no
  `trainer.py`). Qualquer aumento nessas semanas melhoraria Grama, então o ganho não é
  efeito de Finados. O problema é de nível.
- **Produtos de jardim:** o modelo já prevê acima do vendido (131% fora da semana). O fator
  de 2024 (2,75) aplicado em 2025, quando a alta foi de 1,19, multiplica o erro do total da
  semana por 9 com o fator pela metade e por 16 com o fator cheio.
- **Plantas diversas:** o único caso limpo (controle de 96%). O fator pela metade melhora as
  2 ocorrências (−20% no total da semana), mas o fator cheio piora 2025. São 2 ocorrências,
  uma fora de ordem.
- **Total da loja:** melhora com o fator pela metade, mas puxado por Grama, cujo ganho o
  controle já desqualificou.

## 6. Faz sentido?

| Série | Datas | Faz sentido? | Por quê |
| --- | --- | --- | --- |
| Flores de corte, Jardim Canadá | Mulher, Mães, Namorados, Natal | **Sim, com o fator pela metade** | Total da semana −47%, melhor nas 5 ocorrências; a falta do modelo é maior na data (41%) que fora dela (72%) |
| Flores de corte, Itabirito | Mulher, Mães, Namorados, Natal | **Sim, com o fator pela metade** | Total da semana −42%, melhor nas 5 ocorrências; o fator cheio erra para cima de 91% a 151% |
| Flores de corte, as 2 lojas | Finados, Dia dos Pais | Não | Sem efeito no EDA |
| Grama, Itabirito | Finados | **Não** | O ganho vem do nível baixo do modelo no período inteiro (controle de 58%), não da data |
| Produtos de jardim, Itabirito | Finados | **Não** | Multiplica o erro da semana por 9 (fator pela metade) numa ocorrência |
| Plantas diversas, Itabirito | Finados | Ainda não | Ganho pequeno (−20%), com 2 ocorrências; refazer com mais um ano |
| Outras categorias e total de Jardim Canadá | todas | Não | Nenhuma data sai da faixa das semanas comuns |

Mesmo onde faz sentido, o fator corrige **quanto a semana vende**. A tela mostra a previsão
dia a dia, e o dia do pico continua errado. Para a loja, o número útil é o total de flores da
semana da data, e é ele que o fator melhora.

O peso no negócio é pequeno: Flores de corte é 1,5% das unidades em Jardim Canadá e 4,8% em
Itabirito (2,4% e 7,6% do faturamento). O fator não muda o total da loja de forma
perceptível. Ele importa para a compra de flores: é produto perecível, e o sistema hoje
prevê menos da metade do que a semana vende.

## 7. No sistema (ADR-019)

Adotado em Flores de corte, nas 4 datas de presente, pelo ADR-019. As escolhas, a partir deste
teste:

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
  venda. Com a base atual (até 28/02/2026), cobrem de dezembro de 2025 a fevereiro de 2026, sem
  nenhuma data de presente. A avaliação do fator fica neste experimento, refeito quando entrar
  um ano novo de vendas.

## 8. Limitações

- **Poucas ocorrências:** 1 por data e loja em ordem, mais 1 fora de ordem no Natal. O fator
  de cada data é estimado com uma única semana, e é por isso que o fator pela metade vence o
  cheio.
- **Teste por janela, não pelo ano:** as 20 origens por ocorrência cobrem só as semanas em
  volta da data. Fora da semana, o fator não muda nada por construção.
- **Base da semana:** a mediana do mesmo dia da semana usa também as 4 semanas seguintes. No
  sistema, isso vale só para a ocorrência passada, que já está toda no histórico.

## 9. Como reproduzir

A partir de `ia-predictor/`:

```bash
python -m training_scripts.datas_comemorativas.fator_multiplicativo --eda        # §2
python -m training_scripts.datas_comemorativas.fator_multiplicativo --preparar   # séries em cache
python -m training_scripts.datas_comemorativas.fator_multiplicativo --listar     # 18 ocorrências
python -m training_scripts.datas_comemorativas.fator_multiplicativo --caso 0     # uma por processo
python -m training_scripts.datas_comemorativas.fator_multiplicativo --consolidar # §5
```

Cada ocorrência leva de 1 a 4 min (escolha da ordem + 20 ajustes). No proot de
desenvolvimento, rodar no máximo 3 a 4 de uma vez. Com 6 processos em paralelo, o Android
derrubou o Termux 4 vezes seguidas, inclusive depois que o cache baixou a memória de cada
processo de ~500 MB para ~130 MB.
