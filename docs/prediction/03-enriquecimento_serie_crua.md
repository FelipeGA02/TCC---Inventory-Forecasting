# 03 — Segundo treino: a mesma série crua, agora com calendário e clima

**Experimento:** `enriquecimento_serie_crua_pre_eda` · **Data:** 2026-09-27 ·
**Branch:** `train/sarimax-serie-crua-enriquecida` · Continuação de
[02-baseline_serie_crua_pre_eda.md](02-baseline_serie_crua_pre_eda.md)

> **Resumo:** ensinar o **calendário** ao modelo valeu a pena. Ele passou a acertar 100%
> dos feriados (loja fechada), a faixa de segurança ficou **6 vezes mais estreita** e, no
> teste de um ano inteiro, o erro caiu 9% e o modelo passou a ganhar da regra simples em
> 22 de 26 rodadas (antes eram 19). Já o **clima não ajudou em nada**, mesmo no cenário mais
> favorável. Os dois problemas maiores continuam: as **encomendas grandes** (dezembro segue
> com só 35% previsto) e a dificuldade em **acompanhar mudanças de nível**, que ficou mais
> visível: em fevereiro o modelo com calendário previu 23% a mais do que foi vendido.

---

## 1. O que foi feito

**Mesma estratégia do primeiro treino.** A mesma linha do tempo (todas as lojas somadas,
dados de antes do estudo, sem separar encomendas), o mesmo modelo, a mesma forma de escolher
a configuração e os mesmos testes. **A única diferença é a informação extra** que o modelo
recebe. Assim, qualquer melhora vem só do enriquecimento.

Três versões, lado a lado:

| Versão | O que o modelo recebe além do histórico de vendas |
| --- | --- |
| **A0** · sem nada extra | nada: é o primeiro treino, refeito aqui para conferência (deu os mesmos números) |
| **A1** · + calendário | dia da semana; **feriado / loja fechada**; véspera e dia seguinte a feriado; os 7 dias até cada data comemorativa (Dia das Mães, Namorados, Dia da Mulher, Pais, Finados, Natal); primeira semana do mês (dia de pagamento) |
| **B** · + calendário + clima | tudo do A1 + chuva do dia, chuva acumulada na semana e temperatura máxima |

### De onde vieram os dados novos

- **Feriados nacionais:** [BrasilAPI](https://brasilapi.com.br), gratuita. Já inclui
  Carnaval, Sexta-feira Santa, Corpus Christi e Consciência Negra (20/11, feriado nacional
  desde 2024). Isso responde à dúvida anotada no plano de experimentos: a fonte traz o
  Carnaval.
- **Fechamentos locais:** não existe fonte pronta de feriados municipais. Olhamos nos
  próprios dados os dias úteis em que **as duas lojas** ficaram sem venda sem ser feriado
  nacional. Apareceram **15/08** (nos dois anos) e **08/12/2025**. Entraram como "loja
  fechada" e viraram pergunta para a floricultura (EDA §5, pergunta 10).
- **Clima:** [Open-Meteo](https://open-meteo.com), gratuito, dados diários de chuva e
  temperatura para Jardim Canadá (Nova Lima) e Itabirito.
- **Ficaram de fora, de propósito:** indicadores econômicos (inflação, juros). São mensais e
  mudam devagar, e não explicam a venda de um dia para o outro num horizonte de 2 semanas.
  Buscas no Google também ficaram de fora, porque a fonte é instável.

Os dados baixados ficam guardados em `ia-predictor/data/external/`, para o experimento
poder ser refeito sem internet.

### Uma descoberta antes de treinar

Em **todos os 27 feriados** que caíram de segunda a sábado, as duas lojas venderam **zero**.
A única exceção foi Itabirito no Finados de 2024 (718 unidades). O modelo sem calendário não
sabe disso e prevê cerca de 4 mil unidades nesses dias.

### Como testamos

Os mesmos testes do primeiro treino, mais dois novos:

| Teste | Período | Observação |
| --- | --- | --- |
| Fevereiro (principal) | 01 a 28/02/2026 | igual ao primeiro treino |
| 4 rodadas | 04/01 a 28/02/2026 | igual ao primeiro treino |
| **Dezembro** | 01 a 28/12/2025 | o mês mais difícil |
| **Ano inteiro** | 26 rodadas de 2 semanas, mar/2025 a fev/2026 | **teste mais confiável**: passa por todas as estações, feriados e datas |

No teste do ano inteiro (e em dezembro), a melhor configuração do modelo foi escolhida
**só com dados até 01/03/2025**, antes de qualquer período testado. Isso corrige o detalhe
apontado no primeiro treino (§5, item 6).

---

## 2. Resultados

### 2.1 Erro comparado com a regra simples

A régua é a mesma do primeiro treino: o erro do modelo dividido pelo erro da regra simples
"repetir a semana passada", **no mesmo período**. Abaixo de 100%, o modelo é melhor.

![Erro relativo por teste](../../ia-predictor/training_scripts/results/plots/enriquecido/01_erro_relativo_por_teste.png)

| Teste | A0 · sem nada | A1 · + calendário | B · + calendário + clima |
| --- | --- | --- | --- |
| Fevereiro | 82% | 81% | 85% |
| 4 rodadas (jan–fev) | 60% · ganhou 2 de 4 | 60% · ganhou 2 de 4 | 62% · ganhou 2 de 4 |
| Dezembro | 102% (perdeu) | **92%** | 92% |
| **Ano inteiro** | 68% · ganhou **19** de 26 | **62%** · ganhou **22** de 26 | 62% · ganhou 22 de 26 |
| Erro médio no ano (unidades/dia) | 3.024 | **2.749** (−9%) | 2.775 |

> **Nota sobre as "4 rodadas":** no primeiro documento o resultado aparece como 83%, que é
> a média do ganho de cada rodada. Aqui usamos o erro total do período dividido pelo erro
> total da regra simples (60%). É a mesma medida usada para o ano inteiro, e é menos
> sensível a uma rodada isolada. Os dois números descrevem o mesmo modelo.

![Ano rodada a rodada](../../ia-predictor/training_scripts/results/plots/enriquecido/04_ano_rodada_a_rodada.png)

### 2.2 Feriados: o calendário resolveu

![Erro em feriados](../../ia-predictor/training_scripts/results/plots/enriquecido/05_erro_em_feriados.png)

No ano de teste caíram 14 feriados de segunda a sábado. O modelo sem calendário errava, em
média, **3.988 unidades** em cada um. Com calendário, o erro caiu para **praticamente
zero**: ele sabe que a loja fecha.

![Fevereiro](../../ia-predictor/training_scripts/results/plots/enriquecido/02_fevereiro_previsoes.png)

O Carnaval de fevereiro/2026, que sozinho respondia por 23% do erro do primeiro treino,
agora é previsto certo (zero).

### 2.3 A faixa de segurança ficou 6 vezes mais estreita

![Faixa de segurança](../../ia-predictor/training_scripts/results/plots/enriquecido/06_largura_faixa_seguranca.png)

A faixa de "mínimo e máximo prováveis" caiu de **~79 mil** para **~13 mil** unidades por
dia. No ano inteiro, ela acerta 94% das vezes, dentro do esperado para uma faixa de 95%.

**Correção do primeiro treino.** No documento 02 atribuímos a faixa larga às encomendas.
Este experimento mostrou que **a causa principal eram os feriados**. O modelo trabalha
numa escala que "comprime" os números grandes e "estica" a diferença entre zero e o resto.
Nessa escala, um feriado com loja fechada (zero) destoa muito mais do que uma encomenda
grande. Medimos: no modelo sem calendário, **79%** da variação que alarga a faixa vinha dos
feriados e só **5%** dos dias com encomenda. O documento 02 foi corrigido.

A faixa ainda é larga para uso prático: ~2,5 vezes a venda média do dia no ano, e ~4 vezes em fevereiro, que foi um mês fraco. A parte que resta
vem das encomendas e da variação do dia a dia.

### 2.4 O clima não ajudou

O modelo B (com clima) empatou ou ficou um pouco **pior** que o A1 em todos os testes. E isso
usando o clima que **de fato aconteceu**, ou seja, como se a previsão do tempo fosse
perfeita. Com a previsão do tempo real, que erra, o resultado só poderia ser igual ou pior.

![Efeito de cada variável](../../ia-predictor/training_scripts/results/plots/enriquecido/07_efeito_de_cada_variavel.png)

Pelo modelo, nenhuma das variáveis de clima tem efeito confiável:

| Variável | Efeito estimado na venda do dia | Confiável? |
| --- | --- | --- |
| Chuva de 10 mm no dia | +3% (entre −5% e +12%) | não |
| Semana chuvosa (50 mm contra 10 mm) | −1% (entre −7% e +5%) | não |
| +5 °C na temperatura máxima | +8% (entre −4% e +21%) | não |

Na análise por floresta aleatória (a ponderação prevista no projeto), o clima somou **1,4%**
da importância, contra 83% do dia da semana e 15% do feriado:

![Importância das variáveis](../../ia-predictor/training_scripts/results/plots/enriquecido/08_importancia_variaveis_rf.png)

**Por que o clima não pesa aqui:** grama e produtos de jardim (98% do volume) são comprados
para obras e jardins planejados com antecedência. A chuva de um dia não muda muito essa
compra. Pode ser que o clima faça diferença em flores de corte, mas elas são só 2% do
volume e ficam invisíveis numa série que soma tudo. Vale testar de novo quando a previsão
for por loja e categoria.

### 2.5 O que o calendário mostrou sobre as datas comemorativas

- **Dia das Mães e Finados aparecem com efeito enorme** (+159% e +280%), mas o motivo não é
  uma semana de vendas mais forte. Conferindo nos dados, a venda de balcão na semana antes
  dessas datas variou só de −18% a +18%. O efeito vem do **próprio dia**: a loja **abre
  excepcionalmente** num domingo ou feriado em que estaria fechada (os únicos domingos com
  venda em todo o histórico são os dois Dias das Mães e o Finados de 2025). Sair de 0 para
  ~700 unidades pesa muito na escala do modelo.
- As demais datas (Namorados, Dia da Mulher, Pais, Natal) **não mostraram efeito confiável**
  na venda total. Faz sentido com o EDA (§3.4): elas empurram flores para cima e grama para
  baixo, e no total os efeitos se anulam.
- Véspera de feriado, dia seguinte a feriado e primeira semana do mês: nenhum efeito
  confiável.

---

## 3. O que ainda não funciona

### 3.1 Dezembro continua ruim

![Dezembro](../../ia-predictor/training_scripts/results/plots/enriquecido/03_dezembro_previsoes.png)

Com calendário, o erro de dezembro caiu 9% e o modelo passou a ganhar da regra simples, mas
ele previu só **35%** do que foi vendido. Mais da metade de dezembro veio de encomendas
grandes, e nenhum calendário prevê em que dia um cliente vai fechar um pedido de 20 mil m²
de grama.

### 3.2 O modelo com calendário demora a acompanhar mudanças de nível

Em fevereiro, o A1 previu **23% a mais** do que foi vendido (108 mil contra 88 mil). O A0
tinha ficado só 4% acima. Por quê:

- Com o calendário explicando feriados e domingos, a configuração escolhida pelo modelo
  passou a ter pouca "memória" das semanas recentes. A previsão volta rápido para a média
  do histórico, de cerca de 5,3 mil por dia útil.
- Janeiro e fevereiro de 2026 foram meses fracos (~3,5 mil por dia útil), e o modelo não
  "desceu" junto.
- É o mesmo problema de mudança de nível já visto no primeiro treino (dezembro), agora no
  sentido contrário.

Por isso, em fevereiro, o ganho com os feriados (Carnaval) foi quase todo compensado pelo
erro nos dias normais. No ano inteiro o saldo é positivo, mas esse é o próximo ponto a
atacar.

---

## 4. Conclusões e próximos passos

1. **O calendário entra.** Ele resolve os feriados, estreita a faixa de segurança 6 vezes e
   melhora o ano inteiro (erro −9%; vitórias 19 → 22 de 26). O efeito vem quase todo de
   **dia da semana + feriado/loja fechada**. As outras variáveis de calendário podem ser
   simplificadas.
2. **O clima fica de fora** da versão principal, por não ter mostrado ganho nem no cenário
   ideal. Reavaliar só no nível de flores de corte, se um dia essa categoria for prevista
   separadamente.
3. **Trocar "7 dias até a data" por "loja aberta excepcionalmente"** no Dia das Mães e no
   Finados (e perguntar à floricultura se há outras datas assim). Hoje o modelo espalha pela
   semana inteira um efeito que é do próprio dia.
4. **Separar as encomendas** (ADR-012) continua sendo o passo de maior impacto esperado,
   principalmente para dezembro. É o próximo experimento: A0 e A1 **com os achados do EDA**.
5. **Acompanhar o nível recente:** testar configurações com mais memória (por exemplo,
   forçar um termo autorregressivo) ou dar mais peso às semanas recentes.
6. **Confirmar com a floricultura** os fechamentos de 15/08 e 08/12 (EDA §5, pergunta 10).

---

## 5. Arquivos

| O quê | Onde |
| --- | --- |
| Script do experimento | `ia-predictor/training_scripts/enriched/sarimax_serie_crua_enriquecida.py` |
| Busca de feriados e clima | `ia-predictor/training_scripts/enriched/dados_externos.py` |
| Dados externos (cache) | `ia-predictor/data/external/` |
| Resultados | `training_scripts/results/metrics/enriquecimento_serie_crua_pre_eda.json` |
| Previsões dia a dia (todos os testes e modelos) | `…/enriquecimento_serie_crua_pre_eda_previsoes.csv` |
| Variáveis usadas, dia a dia | `…/enriquecimento_serie_crua_pre_eda_exogenas.csv` |
| Gráficos 01–08 | `training_scripts/results/plots/enriquecido/` |

Para refazer (a partir de `ia-predictor/`):

```bash
python -m training_scripts.enriched.sarimax_serie_crua_enriquecida                # ~30 min
python -m training_scripts.enriched.sarimax_serie_crua_enriquecida --so-graficos  # só os gráficos
```

### Ficha técnica (para o texto do TCC)

- **Série:** a mesma do A0-crua (doc 02). Mesmo grid (p,q ∈ {0,1,2}; P,Q ∈ {0,1}; D = 0;
  m = 7), AIC, log1p, d por ADF.
- **Ordens escolhidas:** A0 SARIMA(1,0,1)(1,0,1)₇ no hold-out e (1,0,2)(1,0,1)₇ no ano. A1 e
  B SARIMAX(0,0,2)(0,0,1)₇ nos dois. AIC do hold-out: A0 2.898,2 · A1 1.528,4 · B 1.531,4.
- **Exógenas A1 (16):** 6 dummies de dia da semana (ref. domingo), feriado (BrasilAPI +
  fechamentos locais 15/08/2024, 15/08/2025, 08/12/2025; só seg–sáb), véspera, pós-feriado,
  6 janelas de 7 dias até datas comemorativas, dias 1–7 do mês. **B (19):** + log1p(chuva
  do dia), log1p(chuva 7 d), temperatura máxima (média de 2 pontos Open-Meteo/ERA5).
- **Hold-out 28 d:** MAE 1.415 / 1.397 / 1.467 · MASE 0,404 / 0,399 / 0,419 · MAE/naïve
  0,82 / 0,81 / 0,85 · cobertura IC95 92,9 / 100 / 100% · largura 79,2 / 12,8 / 13,1 mil ·
  previsto/real 104 / 123 / 126%.
- **Ano (26 × 14 d, ordem escolhida com dados até 01/03/2025):** MAE 3.024 / 2.749 / 2.775
  · ΣAE/ΣAE_naïve 0,677 / 0,616 / 0,622 · vence naïve 19 / 22 / 22 · cobertura 95,6 /
  93,7 / 93,7% · largura 70,8 / 13,1 / 13,0 mil · MAE em feriados (14 dias) 3.988 / 0,5 /
  0,5.
- **Dezembro/2025:** MAE 7.807 / 7.102 / 7.101 · MAE/naïve 1,02 / 0,92 / 0,92 ·
  previsto/real 33 / 35 / 35%.
- **Coeficientes (B, hold-out), efeito = e^β − 1:** feriado −100% (p < 0,001); janela Mães
  +159% (p < 0,001) e Finados +280% (p < 0,001), ambos dominados pela abertura excepcional
  no próprio dia; chuva do dia +3% (p = 0,46); chuva 7 d −1% (p = 0,74); temp. máx. +1,5%/°C
  (p = 0,21); demais datas, véspera, pós-feriado e início do mês com p > 0,3.
- **Faixa de 95% no A0:** 79% da soma dos resíduos² (escala log) vinha dos feriados e 5%
  dos dias com encomenda. No A1, os feriados caem para 11%.
- **Importância RF/MDI (B):** dia da semana 83,2% · feriado 15,2% · clima 1,4% · demais
  < 0,5%. Pesar as exógenas pela importância, como previsto no CLAUDE.md, não muda o ajuste
  de um SARIMAX linear: o coeficiente absorve a escala. Por isso o MDI foi usado aqui só
  como diagnóstico.
- **Resíduos:** Ljung-Box p (7/14) A1 0,69/0,48, B 0,70/0,45 (sem autocorrelação); Shapiro
  p ≈ 0 em todos.
