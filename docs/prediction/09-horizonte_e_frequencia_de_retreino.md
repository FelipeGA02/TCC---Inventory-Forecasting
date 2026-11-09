# 09 — Horizonte da previsão e frequência do retreino

**Data:** 2026-11-08 ·
**Status:** experimento concluído. Adotado em 2026-11-09 pelo
[ADR-021](ADR-021-horizonte-de-previsao-selecionavel.md), de um jeito diferente do §6/§7: o treino
prevê 91 dias e a loja escolhe na tela de 2 semanas a 3 meses (padrão 2 semanas); o walk-forward
continua com h = 14 (sem emenda da constituição); treino a cada planilha semanal. Este
documento mede d = 0; com d = 1 (o d de cada série sai do walk-forward, ADR-020), ver ADR-021 §3.1
**Script:** `ia-predictor/training_scripts/validation/horizonte_e_retreino_categorias.py`, sobre
os 52 treinos semanais de `treino_trimestral_vs_semanal.py` (mesma pasta)
**Resultados:** `ia-predictor/training_scripts/results/metrics/horizonte_e_retreino_categorias/`

---

## 1. A pergunta

A loja envia a planilha toda semana e o sistema prevê 14 dias. Duas perguntas:

1. **Horizonte:** a partir de quantos dias à frente a previsão fica ruim? Dá para prever 1, 2 ou
   3 meses?
2. **Retreino:** treinar só a cada 2 semanas, 1, 2 ou 3 meses (a loja mandaria a planilha com
   essa frequência) piora quanto?

Tudo nas **4 categorias das 2 lojas** (8 séries), com a receita de produção (ADR-017/018/019:
SARIMAX m = 7, d = 0, calendário, janela de 365 dias, fator das datas comemorativas), no fluxo
diário sem encomendas grandes.

Resposta curta:

- **A previsão não "quebra" num ponto.** O erro de cada dia sobe uns 2% na 2ª semana, 3–4% da
  4ª semana em diante e para de subir. Até 16 semanas, o erro médio fica entre 2% e 4% acima da
  1ª semana. A faixa de 95% continua acertando ~93% em qualquer horizonte.
- **Mas, depois de ~2 semanas, a previsão é só "uma semana típica do último ano".** Com d = 0 o
  modelo esquece o nível recente e volta para a média dos 365 dias. Ele não erra muito mais,
  mas também não informa mais nada: não antecipa a virada de temporada.
- **Retreino espaçado piora pouco na média e muito no pior mês.** Treinar a cada mês erra 2% a
  mais que toda semana na média do ano; no pior mês, 15% a mais (média das 8 séries), e até 33%
  (Grama de Itabirito, janeiro). A cada 2 ou 3 meses: 3% na média, 29% a 32% no pior mês, até
  69%.
- **Recomendação (§6): treinar a cada planilha semanal e prever 28 dias.** Treinar toda semana
  não custa nada (sem dado novo o treino fica `skipped`), e com 28 dias a loja sempre enxerga
  pelo menos 20 dias à frente (hoje, no pior momento, 6).

## 2. Como foi testado

### 2.1 Erro pela distância do treino e retreino

Base: os 52 treinos semanais de `treino_trimestral_vs_semanal.py`, com cortes de 01/03/2025 a
21/02/2026. Cada treino escolhe a ordem por AIC (janela antes da 1ª origem, como em produção),
ajusta nos últimos 365 dias até o corte e prevê os dias seguintes com o fator das datas
calculado só com venda até o corte. O original prevê até 91 dias; este experimento refaz o
ajuste final com a mesma ordem e estende até 118 dias (as previsões até 91 dias saíram
idênticas às originais nas 33.488 linhas comparadas).

- **Curva pela distância do treino (§3.1):** cada dia de 28/06/2025 a 28/02/2026 é previsto
  por um treino de cada idade (1 a 16 semanas antes). As faixas comparam **os mesmos dias**,
  então só a idade do modelo muda — não a época do ano.
- **Retreino (§3.2):** rotinas de treino a cada 7, 14, 28, 56 e 91 dias. Em cada dia t de
  31/05/2025 a 31/01/2026 (os mesmos em todas as rotinas), vale o treino mais recente da rotina
  com corte ≤ t, e mede-se o que a loja enxerga: os próximos L = 7, 14 ou 28 dias. Cada rotina
  é medida em todas as fases possíveis (a mensal começando na 1ª, 2ª, 3ª ou 4ª semana), para
  não depender da sorte do calendário.

Métricas nos dias de loja aberta: erro diário (MAE), erro do total da janela
(|Σ previsto − Σ vendido| / Σ vendido, o que pesa numa compra para o período) e cobertura do
IC 95%.

### 2.2 Métricas do walk-forward com horizonte maior

O MASE e a cobertura do IC 95% são calculados sobre todo o horizonte do walk-forward. Mudar o
horizonte muda as duas. Duas medidas:

- **Treino de produção (§3.3):** `treinar_serie` com `horizonte` = 14, 21, 28, 35, 42, 56 e 91,
  sobre a base até 28/02/2026: 56 origens andando 1 dia, cada uma prevendo `horizonte` dias. É
  o que o sistema registraria hoje. Com h > 14 a previsão final dá erro (o calendário
  gravado cobre só 14 dias depois da última venda); o walk-forward já terminou antes, e as
  métricas são as dele.
- **Métricas no ano (§3.3):** as mesmas medidas, mas com os 40 treinos semanais de 01/03/2025 a
  29/11/2025 como origens (as mesmas em todo horizonte), cada um avaliado nos `h` dias
  seguintes. O walk-forward de produção vê só 8 semanas; este vê 9 meses.

## 3. Resultados

### 3.1 Quanto o erro sobe com a distância do treino

Erro diário médio por semana depois do treino; 1ª semana = 100. Mesmos 204 dias de loja aberta
em todas as colunas.

| Série | 1 | 2 | 3 | 4 | 6 | 8 | 10 | 12 | 14 | 16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Itabirito · Flores de corte | 100 | 100 | 99 | 99 | 97 | 97 | 97 | 97 | 97 | 96 |
| Itabirito · Grama | 100 | 105 | 106 | 107 | 107 | 108 | 108 | 104 | 104 | 104 |
| Itabirito · Plantas diversas | 100 | 99 | 100 | 102 | 100 | 99 | 101 | 101 | 100 | 101 |
| Itabirito · Produtos de jardim | 100 | 102 | 103 | 105 | 104 | 105 | 104 | 103 | 103 | 102 |
| Jardim Canadá · Flores de corte | 100 | 101 | 100 | 99 | 98 | 97 | 97 | 97 | 98 | 98 |
| Jardim Canadá · Grama | 100 | 102 | 102 | 107 | 108 | 109 | 111 | 108 | 107 | 106 |
| Jardim Canadá · Plantas diversas | 100 | 103 | 104 | 105 | 106 | 105 | 105 | 106 | 104 | 105 |
| Jardim Canadá · Produtos de jardim | 100 | 102 | 102 | 103 | 102 | 104 | 106 | 104 | 104 | 105 |
| **Média** | **100** | **101,8** | **102,0** | **103,4** | **102,8** | **103,0** | **103,6** | **102,5** | **102,1** | **102,1** |
| Cobertura do IC 95% (média) | 93,3 | 92,8 | 92,9 | 92,7 | 92,7 | 92,8 | 92,6 | 92,6 | 92,8 | 92,8 |

- **Grama é a que mais sente:** +7% na 4ª semana, até +11% (Jardim Canadá, 10ª semana).
- **Flores de corte erra um pouco menos com a distância** (96–98): o modelo velho prevê a
  média, e na flor, que oscila muito dia a dia, a média é tão boa quanto o nível recente.
- **Depois da 4ª semana a curva fica plana.** Não há um dia a partir do qual a previsão piora
  de vez.

O que cresce mais é o **viés** (previsto ÷ vendido na mesma faixa): em Produtos de jardim de
Itabirito, de 87% na 1ª semana para 83% na 16ª; em Grama de Jardim Canadá, de 97% para 103%.
O modelo de 2–4 meses atrás carrega o nível médio do ano, não o atual.

### 3.2 Retreino a cada 1 semana até 3 meses

Somei as 8 categorias e simulei cada dia de jun/2025 a jan/2026. Com treino semanal o erro vale
100.

| Retreino a cada | Erro diário, próx. 7 dias | Erro diário, próx. 14 dias | Erro diário, próx. 28 dias | Erro do total, próx. 14 dias | Cobertura IC 95% | Pior mês (média das séries) |
| --- | --- | --- | --- | --- | --- | --- |
| 7 dias (hoje) | 100 | 100 | 100 | 24,5% | 93,0% | — |
| 14 dias | 100,7 | 100,8 | 100,6 | 25,3% | 92,9% | +6,8% |
| 28 dias (mensal) | 102,1 | 102,0 | 101,5 | 26,2% | 92,9% | +15,0% |
| 56 dias (2 meses) | 103,4 | 103,1 | 102,2 | 27,0% | 92,9% | +28,6% |
| 91 dias (3 meses) | 103,8 | 103,3 | 102,1 | 27,0% | 92,8% | +32,1% |

"Pior mês": em cada série, o mês (de jun/2025 a jan/2026) e a fase da rotina em que o erro
diário dos próximos 14 dias mais passou o do treino semanal; a coluna é a média das 8 séries.

Piora do erro diário dos próximos 14 dias sobre o treino semanal, por série:

| Série | 14 dias | 28 dias | 56 dias | 91 dias | Pior mês, 28 dias | Pior mês, 91 dias |
| --- | --- | --- | --- | --- | --- | --- |
| Itabirito · Flores de corte | −0,5% | −0,9% | −1,6% | −2,1% | +2,8% | +9,5% |
| Itabirito · Grama | +1,3% | +2,2% | +2,6% | +2,0% | +33,0% | +69,1% |
| Itabirito · Plantas diversas | +0,2% | +0,2% | −0,3% | −0,1% | +14,9% | +15,2% |
| Itabirito · Produtos de jardim | +0,6% | +1,4% | +1,8% | +1,4% | +14,8% | +28,7% |
| Jardim Canadá · Flores de corte | −0,2% | −0,9% | −1,8% | −2,2% | +12,1% | +12,6% |
| Jardim Canadá · Grama | +1,1% | +3,3% | +5,8% | +6,6% | +18,4% | +32,5% |
| Jardim Canadá · Plantas diversas | +0,6% | +1,5% | +2,4% | +2,2% | +18,8% | +59,4% |
| Jardim Canadá · Produtos de jardim | +0,6% | +1,1% | +1,8% | +2,3% | +5,0% | +30,1% |

- **Na média do ano a diferença é pequena** e para de crescer depois de 2 meses: o modelo
  velho já está na média do ano, e ficar mais velho não muda isso.
- **O custo aparece nas viradas de temporada.** Os piores meses são:
  - **janeiro de 2026**, depois das festas: o modelo treinado antes de dezembro, ainda na alta,
    prevê 1,5 a 1,9 vez o vendido (Grama de Itabirito: 148% do vendido com treino mensal, 194%
    com trimestral; Plantas diversas de Jardim Canadá: 168% com trimestral);
  - **novembro de 2025**, começo das chuvas: na Grama de Jardim Canadá, o modelo treinado no
    início de setembro prevê metade do vendido.
  O treino semanal acompanha essas viradas em 1–2 semanas; o espaçado fica errando até o treino
  seguinte.
- **Flores de corte não ganha com treino frequente** (até −2%), pelo mesmo motivo do §3.1.

### 3.3 MASE e cobertura com horizonte maior

**Treino de produção** (walk-forward de 56 origens até 28/02/2026). Cada célula: MASE (cobertura
do IC 95%).

| Série | h = 14 | 21 | 28 | 35 | 42 | 56 | 91 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Origens do walk-forward | 22/12–15/02 | 15/12–08/02 | 08/12–01/02 | 01/12–25/01 | 24/11–18/01 | 10/11–04/01 | 06/10–30/11 |
| Itabirito · Flores de corte | 0,67 (100%) | 0,68 (100%) | 0,68 (99,5%) | 0,70 (99,0%) | 0,74 (98,4%) | 0,73 (97,7%) | 0,68 (96,9%) |
| Itabirito · Grama | 0,85 (97,5%) | 0,89 (97,5%) | 0,90 (96,9%) | 0,96 (95,8%) | 0,99 (95,2%) | 1,01 (94,4%) | 0,96 (90,6%) |
| Itabirito · Plantas diversas | 1,09 (97,6%) | 1,08 (96,9%) | 1,08 (96,5%) | 1,09 (96,1%) | 1,08 (95,5%) | 1,01 (95,2%) | 0,89 (95,7%) |
| Itabirito · Produtos de jardim | 0,93 (97,8%) | 0,89 (98,2%) | 0,78 (98,6%) | 0,78 (98,9%) | 0,76 (99,1%) | 0,70 (99,0%) | 0,85 (98,1%) |
| Jardim Canadá · Flores de corte | 0,68 (99,7%) | 0,70 (99,8%) | 0,72 (99,8%) | 0,72 (99,9%) | 0,74 (99,6%) | 0,76 (99,2%) | 0,76 (98,1%) |
| Jardim Canadá · Grama | 0,94 (92,1%) | 0,99 (90,6%) | 1,03 (90,0%) | 1,05 (89,7%) | 1,08 (88,5%) | 1,08 (87,6%) | 1,03 (89,0%) |
| Jardim Canadá · Plantas diversas | 0,97 (90,0%) | 1,04 (87,3%) | 1,03 (88,4%) | 1,17 (81,1%) | 1,25 (78,7%) | 1,29 (76,3%) | 1,09 (89,6%) |
| Jardim Canadá · Produtos de jardim | 0,86 (92,7%) | 0,90 (90,6%) | 0,90 (90,4%) | 0,89 (91,0%) | 0,88 (91,4%) | 0,88 (91,8%) | 0,92 (90,3%) |
| Previsto ÷ vendido (faixa das 8) | 119–157% | 118–154% | 112–146% | 111–144% | 108–143% | 103–133% | 70–124% |

**No ano** (40 origens semanais, mar–nov/2025):

| Horizonte | 14 | 21 | 28 | 35 | 42 | 56 | 91 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MASE, faixa das 8 | 0,83–0,95 | 0,83–0,94 | 0,84–0,94 | 0,83–0,94 | 0,83–0,95 | 0,84–0,95 | 0,85–0,97 |
| Cobertura do IC 95%, faixa das 8 | 91,4–95,9% | 90,9–96,0% | 90,8–96,0% | 90,7–96,0% | 90,6–96,0% | 90,4–96,0% | 90,0–96,3% |
| MASE, Grama JC | 0,866 | 0,872 | 0,882 | 0,892 | 0,902 | 0,917 | 0,927 |
| MASE, Plantas JC | 0,914 | 0,924 | 0,930 | 0,937 | 0,941 | 0,949 | 0,971 |
| MASE, Flores ITA | 0,904 | 0,890 | 0,886 | 0,887 | 0,890 | 0,895 | 0,887 |

- **No ano, o horizonte quase não mexe nas métricas:** o MASE sobe 0,01–0,06 de h = 14 para
  h = 91 e fica abaixo de 1 nas 8 séries; a cobertura fica em 90–96%.
- **No walk-forward de produção, mexe, e não numa direção só.** A última venda é a mesma
  (28/02/2026), mas a última origem completa fica `h − 1` dias antes dela: com h maior, as
  origens recuam (de dez–fev com h = 14 para out–nov com h = 91) e a avaliação cobre outros meses.
  - Com h = 14 a 56, as origens caem em nov–jan, e quase toda a avaliação é a queda depois das
    festas: o modelo prevê 103% a 157% do vendido. As séries que já estavam perto de 1 (MASE
    0,93–0,97: Grama e Plantas de Jardim Canadá, Grama de Itabirito) passam de 1.
  - Com h = 91, a avaliação vai de outubro a fevereiro, pega a alta de out–dez e a queda de
    jan–fev, e os erros se compensam em parte (70% a 124% do vendido).
- **Flores de corte tem a faixa larga** em todo horizonte (cobertura de 97% a 100%), e Plantas
  diversas de Jardim Canadá perde cobertura com h maior (76–90%).

O walk-forward de produção é um **retrato das semanas avaliadas**, não do ano. As métricas mudam
com o horizonte e com a época do treino; em março, com o walk-forward fora das festas, o mesmo
h = 28 daria outro quadro.

## 4. Por que é assim

- **d = 0, sem tendência:** a previsão parte do nível recente e, pelos termos MA/AR, volta à
  média da janela de 365 dias em ~2 semanas. Daí em diante é o perfil do dia da semana e do
  calendário em torno dessa média, e não muda mais. Por isso a curva do §3.1 sobe nas primeiras
  semanas e depois fica plana.
- **Sem sazonalidade anual:** com 365 dias de janela e ~2 anos de base, o modelo não sabe que
  janeiro cai e novembro sobe na grama. Quem informa a virada é o próprio dado novo, via
  retreino. Daí o custo do retreino espaçado ficar concentrado nas viradas (§3.2).
- **A faixa de 95% já nasce larga:** como o nível recente pesa pouco além de alguns dias, a
  faixa de h = 1 já é quase a variância incondicional da série. Ela quase não abre com o
  horizonte, e a cobertura fica estável (~93%).

## 5. Quanto o horizonte precisa cobrir

O horizonte não é só "quanto à frente a loja quer ver": ele precisa durar até a planilha
seguinte. Com treino a cada **k** dias, a planilha chegando **a** dias depois da última venda, e
a loja querendo ver sempre **L** dias à frente:

> horizonte ≥ k + a − 1 + L

| Planilha | Loja quer ver sempre | Horizonte mínimo (a = 2) |
| --- | --- | --- |
| semanal | 14 dias | 22 |
| semanal | 21 dias | 29 |
| semanal | 28 dias | 36 |
| mensal | 14 dias | 43 |
| mensal | 28 dias | 57 |
| trimestral | 14 dias | 106 |

Hoje (semanal, h = 14), na véspera da planilha seguinte a loja vê só 6 dias à frente.

## 6. Recomendação

**Retreino: a cada planilha, toda semana — como já é.**

- Não custa nada: sem venda nova o treino fica `skipped`, e o treino de produção leva ~27 min.
- Na média do ano, mensal ou trimestral perde só 2–3%, mas no pior mês perde 15% (mensal) a
  32% (trimestral), e esses meses são as viradas de temporada (janeiro, novembro), exatamente
  quando a compra mais importa.
- O histórico "vendido × previsto" e a conferência da planilha (dias de loja aberta sem venda)
  andam toda semana; com planilha mensal, uma semana esquecida só apareceria um mês depois.
- Se a loja não conseguir mandar toda semana, **a cada 2 semanas** é o limite razoável: +0,8%
  na média, +7% no pior mês.

**Horizonte: 28 dias.**

- O erro de cada dia na 4ª semana é ~3% maior que na 1ª (§3.1); a faixa de 95% continua
  calibrada.
- Com planilha semanal, a loja sempre enxerga pelo menos 20 dias à frente (28 − 7 − 2 + 1),
  em vez de 6 dias no pior momento de hoje.
- **Mais que 28 não acrescenta informação:** da 3ª–4ª semana em diante a previsão é a semana
  típica do ano, igual em todas as semanas seguintes; e, com treino semanal, a parte além de 28
  dias é sempre substituída antes de chegar.
- **Custo nas métricas:** no corte de 28/02/2026, com o walk-forward em 28 dias, o MASE de 2
  séries passa de 1 (Grama e Plantas diversas de Jardim Canadá) e a cobertura de Plantas
  diversas de Jardim Canadá fica abaixo de 90% (§3.3), porque a avaliação cai inteira na queda
  depois das festas. Medir o teste em 14 dias (o que a loja usa para a compra da semana) e
  mostrar os dias seguintes com a mesma faixa de 95% evita misturar a época do ano com o
  horizonte; foi o que o ADR-021 fez.

**Prever 1 mês com planilha mensal não é recomendado:** o horizonte teria de ser ~57 dias para
a loja ver 28 dias no fim do mês (§5), o pior mês erra 15% a mais e a tela fica parada um mês.

## 7. O que muda no sistema se o horizonte for 28

> **Implementado de outro jeito (ADR-021, 2026-11-09):** a previsão gravada passou a 91 dias, a
> tela escolhe de 14 a 91, e o walk-forward ficou em h = 14 — sem mexer no histórico mínimo, no
> complemento nem na constituição. A lista abaixo é a do plano original, com h = 28 no
> walk-forward.

- `FORECAST_HORIZON_DAYS=28` (`ConfigTreino.horizonte`).
- **Calendário:** `calendar_days` precisa cobrir os 28 dias seguintes à última venda (hoje
  cobre 14; dia que faltar usa o padrão — fechada só no domingo). No experimento, a previsão
  final com h > 14 caiu por isso (`KeyError` no `X.loc[futuro]`).
- **Histórico mínimo:** a 1ª origem do walk-forward recua 14 dias; o mínimo de calendário da 1ª
  à última venda passa de 249 para 263 dias (180 + 56 + 27). Produto de grama novo demora 2
  semanas a mais para ter previsão.
- **Tempo do treino:** o complemento passa de 13 para 27 origens (+14 ajustes por série, de 106 para 120: ~13%).
- **Histórico congelado** (`forecast_history`): a regra não muda — cada dia guarda a última
  previsão feita antes dele. Com 28 dias, um intervalo de até 28 dias entre treinos não deixa
  buraco (hoje, mais de 14).
- **Constituição:** o Princípio III fixa h = 14 — emenda via `/speckit-constitution`. Também
  `CLAUDE.md`, doc 07, ADR-017 e `openapi.yaml` (se citam 14 dias).
- **Tela:** o gráfico de 14 dias passa a 28; o total da janela que a loja usa para a compra
  pode ser o da próxima semana ou das próximas 4.

## 8. Limitações

- **Um ano de teste** (mar/2025–fev/2026) e uma temporada de cada tipo; as viradas de janeiro e
  novembro aparecem uma vez.
- **Só as 4 categorias.** Os produtos de grama não entraram aqui; no experimento anterior
  (`treino_trimestral_vs_semanal.py`) o produto mais vendido de cada loja seguiu a Grama da
  categoria (+3% a +6% no erro com treino trimestral).
- **Treinos semanais, não diários:** a curva do §3.1 e as rotinas do §3.2 usam origens a cada 7
  dias; o walk-forward de produção anda 1 dia.
- **Atraso da planilha ignorado no §3.2:** o treino usa a venda até o corte; na prática a
  planilha chega dias depois (o §5 trata disso no tamanho do horizonte).
- **Métricas de produção num corte só** (28/02/2026). O §3.3 mostra que elas dependem da época.
