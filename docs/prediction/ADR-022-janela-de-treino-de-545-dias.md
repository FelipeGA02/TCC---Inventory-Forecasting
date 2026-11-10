# ADR-022 — Janela de treino de 545 dias

**Status:** aceito · **Data:** 2026-11-10 · **Revisa:** ADR-017 (janela deslizante de 365 dias)
**Afeta:** `backend/config.py` (`FORECAST_SERVICE_WINDOW_DAYS`, novo
`FORECAST_SERVICE_MIN_SALE_WINDOW_DAYS`), `backend/domain/models/trainer.py`
(`ConfigTreino.janela_venda_dias`, `motivo_inelegivel`), `backend/services/servico_previsao.py`,
`.env.example`, `openapi.yaml` 9.0.1 (só descrição e exemplos), frontend (ícone de informação nas
4 gramas pequenas de Jardim Canadá)
**Evidência:** [doc 11](11-janela_de_treino_e_horizonte.md)

---

## 1. Contexto

Cada série (4 categorias e cada produto de grama, por loja) era ajustada nos últimos 365 dias: na
escolha da ordem, em cada origem do walk-forward e no ajuste final. O doc 11 refez a receita de
produção em 51 cortes semanais (mar/2025–fev/2026) nas 23 séries com previsão, trocando só a
janela, e mediu também até onde a previsão aguenta.

| Janela (média das séries, erro dos 14 dias em % sobre 365) | 90 | 180 | 270 | **545** | histórico inteiro |
| --- | ---: | ---: | ---: | ---: | ---: |
| 23 séries | +5,5% | +0,4% | −0,9% | **−1,9%** | −1,3% |
| 8 categorias | +8,6% | +2,9% | +1,0% | **−1,9%** | −2,2% |

- **545 dias é a melhor janela única:** −1,9% nas 23 séries e nas categorias, sem piorar de forma
  relevante nenhuma categoria (a pior: Grama de Jardim Canadá, +0,3%).
- O histórico inteiro empata nas categorias (−2,2%), mas perde nos produtos e cresce sem limite a
  cada planilha. Ele tornaria o treino cada vez mais lento e misturaria regimes antigos (Pesaran &
  Timmermann, 2007).
- O maior ganho é em Flores de corte (−6,2% em Itabirito, −3,8% em Jardim Canadá com 545). Com mais
  de um ano de janela, o modelo vê cada data comemorativa mais de uma vez.
- A faixa de 95% fica 0,4% a 3% mais larga e a cobertura sobe 0,2–0,3 ponto.

## 2. Decisão

1. **`FORECAST_SERVICE_WINDOW_DAYS = 545`**: a janela deslizante de treino passa a 1 ano e meio, nos
   três usos (ordem por AIC, walk-forward, ajuste final).
2. **A regra de frequência de venda do produto de grama continua nos últimos 365 dias**
   (`FORECAST_SERVICE_MIN_SALE_WINDOW_DAYS = 365`, `ConfigTreino.janela_venda_dias`). Antes ela
   usava a janela de treino. Sem separar, um produto que parou de vender há mais de um ano voltaria
   a ter previsão. O doc 11 também comparou as janelas com a elegibilidade de produção (365).
3. **A janela não é escolhida série a série.** Isso ganharia mais nos produtos (−8,8% contra cerca
   de −2% com 545), mas:
   - o ganho vem quase todo de gramas que vendem poucas unidades por dia;
   - nas gramas grandes, o ganho fica em 1–2%;
   - o treino ficaria ~6 vezes mais lento (6 janelas × 2 d).
   Nas categorias, a escolha automática ganha menos que fixar 545 (−1,1%).
4. **O horizonte da tela não muda (ADR-021):** padrão de 2 semanas, opções até 3 meses, sem aviso
   além de 4 semanas. Pelo doc 11 §4, o erro sobe +3% na 4ª semana e +7% no 3º mês nas categorias,
   sem perder da naïve. As séries de temporada de Jardim Canadá pioram de forma significativa a
   partir de 4–8 semanas.
5. **Ícone de informação nas 4 gramas pequenas de Jardim Canadá.** São a Esmeralda (ITO) 00013475,
   a Preta pelo de urso saco 00150005, a Preta pelo de urso BDJA 166 e o Capim dos Texas verde 1294.
   - Na tela de Previsão, ao lado do nome do produto, um ícone explica, ao passar o mouse, que a
     previsão delas não acerta mais do que olhar a venda da semana anterior.
   - No doc 11 §4.1, elas perdem da naïve já nas 2 primeiras semanas (erro ÷ naïve 1,02–1,17).
   - A lista fica no frontend (`GRAMAS_ESPARSAS` em `PrevisaoSarimax.tsx`) e é revista quando o
     estudo for refeito.
   - Nenhuma outra mensagem foi acrescentada à tela.

## 3. Consequências

- **A receita do modelo muda** (`janela_dias` e o novo `janela_venda_dias` entram na impressão
  digital). O próximo treino não fica `skipped` mesmo sem planilha nova.
- **Ajustes um pouco mais lentos:** até 50% mais dias por ajuste. Até 28/02/2026, as séries mais
  longas têm ~790 dias; as que têm menos de 545 usam o que existe.
- **Histórico mínimo não muda:** 180 dias antes da 1ª origem (249 dias de calendário).
- **Experimentos em `training_scripts/`:** o padrão de `ConfigTreino.janela_dias` continua 365 para
  os scripts reproduzirem o que documentaram. A produção recebe 545 da configuração.
- **Neon:** a mudança vale a partir do próximo treino ("Treinar previsões" ou `treinar_previsoes`).
  Antes de gravar no banco compartilhado, o treino é conferido contra o doc 11.

## 4. Alternativas descartadas

| Alternativa | Por que não |
| --- | --- |
| Manter 365 | Erra 1,9% a mais na média e até 6% a mais em Flores de corte |
| Histórico inteiro | Empata nas categorias, perde nos produtos e cresce sem limite |
| Janela escolhida a cada treino, série a série | Ganho concentrado em gramas de baixo volume; treino ~6× mais lento; nas categorias ganha menos que 545 fixo |
| Misto (545 nas categorias, escolha nos produtos) | Mesmo custo de código e de tempo nos produtos, pelo mesmo ganho de baixo volume; fica para quando a loja precisar das gramas pequenas |
| Aviso na tela além de 4 semanas | Decisão do projeto em 10/11/2026: na tela, só o ícone das gramas pequenas |

## Referências

- Pesaran, M. H.; Timmermann, A. (2007). Selection of estimation window in the presence of breaks.
  *Journal of Econometrics*, 137(1), 134–161.
- Inoue, A.; Jin, L.; Rossi, B. (2017). Rolling window selection for out-of-sample forecasting with
  time-varying parameters. *Journal of Econometrics*, 196(1), 55–67.
