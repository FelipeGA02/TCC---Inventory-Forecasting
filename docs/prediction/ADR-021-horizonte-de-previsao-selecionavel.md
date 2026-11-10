# ADR-021 — Previsão de 91 dias, horizonte escolhido na tela

**Status:** aceito · **Data:** 2026-11-09 · **Revisa:** ADR-017 (previsão dos 14 dias seguintes à
última venda)
**Afeta:** `backend/config.py` (`FORECAST_MAX_HORIZON_DAYS`), `backend/domain/models/trainer.py`
(`ConfigTreino.horizonte_previsao`, `dias_previsao`), `backend/services/servico_previsao.py`,
`backend/services/painel_service.py`, `backend/domain/painel.py`, `openapi.yaml` 8.0.0
(`horizonte_previsao_dias`), frontend (`FiltroHorizonte`, tela Previsão e Relatórios)
**Evidência:** [doc 09](09-horizonte_e_frequencia_de_retreino.md) (horizonte e retreino, d = 0) e
§3 abaixo (d = 1, ADR-020)

---

## 1. Contexto

O sistema previa os 14 dias seguintes à última venda. Com planilha semanal chegando ~2 dias depois
da última venda, na véspera da planilha seguinte a loja enxergava só 6 dias à frente (doc 09 §5),
e não via nada do mês seguinte para planejar compra de prazo maior.

O doc 09 mediu, nas 8 categorias, quanto a previsão piora com a distância do treino: o erro de
cada dia sobe ~3% até a 4ª semana e fica plano até a 16ª; a faixa de 95% cobre ~93% do vendido em
qualquer horizonte (com d = 0). A previsão longe do treino não "quebra" — ela vira o ritmo típico
das vendas, sem acompanhar viradas recentes.

## 2. Decisão

1. **O treino prevê 91 dias** (`FORECAST_MAX_HORIZON_DAYS=91`) a partir do dia seguinte à última
   venda, com a faixa de 95%. Tudo é gravado (`series_forecasts`, `forecast_history`).
2. **A tela escolhe quantos mostrar**, numa caixa de opções "Horizonte": 2, 3, 4, 6 ou 8 semanas,
   ou 3 meses (14, 21, 28, 42, 56 ou 91 dias). **Padrão: 2 semanas.** A escolha vale para a tela de Previsão (gráfico por categoria e
   por produto, tabela dia a dia, totais) e para os relatórios de previsão e o gerencial. Treino
   anterior a este ADR (14 dias gravados): o seletor continua na tela, e as opções que ele não
   cobre aparecem desativadas ("disponível no próximo treino").
3. **O teste de acerto não muda**: walk-forward com 56 origens andando 1 dia e **h = 14**, com as
   mesmas métricas da tela de histórico.
   A tela não mostra aviso sobre os dias além de 2 semanas (decisão da loja, 09/11/2026); a
   diferença de acerto fica documentada aqui (§3.1).
4. **Histórico congelado** (`forecast_history`): a regra não muda — o previsto de cada dia é o da
   última previsão feita antes dele. Com 91 dias gravados, um intervalo de até 91 dias entre
   treinos não deixa buraco (antes, mais de 14); o walk-forward (h = 1) só preenche o que nenhuma
   previsão cobriu.
5. **Calendário**: `calendar_days` precisa cobrir os 91 dias seguintes à última venda (hoje vai até
   31/12/2026). Dia que faltar usa o padrão da loja (fechada só no domingo) e o treino registra o
   aviso no log.
6. **Retreino: continua a cada planilha semanal** (doc 09 §6, tabela no §4).

## 3. Por que o walk-forward continua com h = 14

- **Constituição, Princípio III:** walk-forward com horizonte de 14 dias antes da previsão. Manter
  h = 14 cumpre o princípio sem emenda.
- **Custo e histórico mínimo:** com h = 91 a última origem completa recua 77 dias, o histórico
  mínimo da 1ª à última venda iria de 249 para 326 dias (produto novo de grama esperaria 11 semanas
  a mais) e o complemento passaria de 13 para 90 origens (+77 ajustes por série, ~70% a mais de
  tempo de treino).
- **As métricas com h longo são um retrato de outros meses:** no corte de 28/02/2026, com h = 91 as
  origens caem em out–nov e a avaliação mistura a alta de fim de ano com a queda de janeiro; o
  MASE e a cobertura mudam sem que a previsão de hoje mude (doc 09 §3.3).
- O que importa para a decisão da semana — a compra dos próximos dias — é o que o teste de 14 dias
  mede. Para os dias seguintes, a evidência é a do doc 09 e a do §3.1.

### 3.1 Com d = 1 (ADR-020)

O doc 09 mediu a curva só com d = 0. `training_scripts/validation/horizonte_d1_categorias.py`
refaz os 52 treinos semanais d = 1 de `variantes_nivel_sazonal.py` (mesma ordem) até 118 dias e
compara com os de d = 0 nos **mesmos dias-alvo** (28/06/2025 a 28/02/2026, loja aberta, 203–204
dias por série), cada um previsto por um treino de cada idade (1 a 16 semanas antes). "Receita
ADR-020" = d = 1 menos em Flores de corte (d = 0), a 1ª versão do ADR-020; com a escolha série a
série, cada categoria fica com o d que o walk-forward do treino indicar — no ano, d = 0 errou menos
em Flores de corte e em Plantas diversas de Itabirito. Erro diário das 8 categorias somadas; d = 0 na
1ª semana = 100.

| Semana do horizonte | 1 | 2 | 3 | 4 | 6 | 7 | 8 | 10 | 13 | 16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| d = 0 (antes) | 100 | 102,3 | 102,7 | 105,2 | 105,5 | 106,5 | 105,7 | 107,1 | 104,7 | 104,2 |
| Receita ADR-020 | **96,7** | **97,3** | **98,2** | **102,1** | **104,0** | 107,2 | 109,0 | 112,7 | 113,1 | 111,0 |
| Cobertura IC 95%, d = 0 | 93,3% | 92,8% | 92,9% | 92,7% | 92,7% | 92,6% | 92,3% | 92,0% | 92,4% | 93,1% |
| Cobertura IC 95%, ADR-020 | 92,6% | 92,7% | 93,0% | 92,4% | 92,3% | 92,1% | 92,3% | 92,0% | 92,6% | 93,1% |
| Previsto ÷ vendido, ADR-020 | 99,4% | 99,6% | 99,5% | 99,8% | 100,1% | 100,2% | 100,2% | 99,4% | 97,5% | 94,8% |

- **Até a 6ª semana a receita nova erra menos** (−3,3% na 1ª, −2,9% na 4ª); **da 7ª em diante, mais**
  (+3% na 8ª, +8% na 13ª). Com d = 0 a previsão volta à média do ano, que no longo prazo é um
  palpite melhor que o nível de hoje; com d = 1 ela fica no nível de hoje, e o nível muda com a
  temporada.
- Por série, na 13ª semana: Grama de Jardim Canadá 116 × 108 (d = 0), Produtos de jardim de
  Itabirito 113 × 102, Plantas diversas 111–115 × 100–104. Flores de corte não muda (d = 0 nas
  duas receitas).
- **A faixa de 95% continua calibrada** (92–93% em todas as semanas) e abre devagar com d = 1: a
  largura média passa de 992 na 1ª semana para 1.094 na 13ª (+10%), contra 1.019 → 1.037 com d = 0.
- **Consequência para a tela:** a compra da semana (2 primeiras semanas, que é o padrão e o que o
  teste de acerto mede) fica melhor com d = 1 nas séries que o pedem; os meses 2 e 3 do horizonte longo ficam ~5–8%
  piores do que seriam com d = 0. A tela não avisa isso; a loja usa o horizonte longo para
  planejar, e a compra da semana, com o padrão de 2 semanas. Uma receita mista — d = 1 até a 6ª semana e o modelo d = 0 depois —
  ficaria com o melhor dos dois, ao custo de um segundo ajuste por série; fica registrada como
  próximo passo, não implementada.

## 4. Retreino a cada 1 semana até 3 meses

Somei as 8 categorias e simulei cada dia de jun/2025 a jan/2026, com a loja vendo os próximos 7, 14
ou 28 dias do treino mais recente de cada rotina (todas as fases de cada rotina). Com treino
semanal o erro vale 100 (doc 09 §3.2, d = 0).

| Retreino a cada | Erro de cada dia, próx. 7 dias | Erro de cada dia, próx. 14 dias | Erro de cada dia, próx. 28 dias | Erro do total dos próx. 14 dias | Cobertura IC 95% | Pior mês (média das séries) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 semana (como hoje) | 100 | 100 | 100 | 24,5% | 93,0% | — |
| 2 semanas | 100,7 | 100,8 | 100,6 | 25,3% | 92,9% | +6,8% |
| 4 semanas (mensal) | 102,1 | 102,0 | 101,5 | 26,2% | 92,9% | +15,0% |
| 8 semanas (2 meses) | 103,4 | 103,1 | 102,2 | 27,0% | 92,9% | +28,6% |
| 13 semanas (3 meses) | 103,8 | 103,3 | 102,1 | 27,0% | 92,8% | +32,1% |

- **Na média a piora é pequena e para de crescer depois de 2 meses:** depois de umas 2 semanas o
  modelo já prevê a média do último ano, e ficar mais velho não muda isso.
- **No pior mês a piora é grande**, e os piores meses são as viradas de temporada:
  - **janeiro, depois das festas:** o modelo treinado antes de dezembro prevê até 1,9 vez o que a
    Grama de Itabirito vendeu, e o erro dela sobe 69%;
  - **novembro, começo das chuvas:** na Grama de Jardim Canadá, o modelo treinado no início de
    setembro prevê metade do vendido.
- Treinar toda semana não custa nada (sem venda nova o treino fica `skipped`) e evita o erro alto
  nas viradas. A cada 2 semanas ainda é aceitável (+0,8% na média, +7% no pior mês). **Prever 3
  meses não substitui o retreino:** o horizonte longo é para planejamento; a compra da semana usa
  o treino da semana.

## 5. Consequências

- **Tamanho:** `series_forecasts` e `forecast_history` gravam 91 dias por série (antes 14): ~23
  séries com previsão × 91 = ~2.100 linhas por treino em cada tabela.
- **API (8.0.0):** a `previsao` do painel (loja e produto) traz os 91 dias; `configuracao` ganha
  `horizonte_previsao_dias`; `previsao_14d` do produto continua a soma dos 14 primeiros dias (só
  ordena a lista). O front recorta pelo horizonte escolhido.
- **Receita na impressão digital:** mudar `FORECAST_MAX_HORIZON_DAYS` pede treino novo (ADR-020 §2).
- **Limitação:** as métricas da tela valem para as 2 primeiras semanas; o erro além
  delas é o medido nos experimentos (doc 09 e §3.1), não o do treino de cada semana.

## 6. Resultado

Primeiro treino com a receita nova (base local, vendas até 28/02/2026, 09/11/2026): as 23 séries
com previsão gravaram 91 dias cada (2.093 linhas em `series_forecasts`; o histórico ficou com a
previsão de 01/03 a 30/05/2026). As métricas não mudam com o horizonte (o walk-forward
continua com h = 14). A receita entrou na impressão digital: o treino rodou sem `--forcar`, com a
mesma base do treino anterior. Na tela, o seletor abre em "2 semanas"; em "3 meses", o gráfico,
a tabela dia a dia e os relatórios mostram os 91 dias (Previsão diária: 728 linhas = 91 dias × 4
categorias × 2 lojas), e o quadro "Feriados e datas comemorativas no período" lista as do período
inteiro, uma por cartão, com a data, o dia da semana e se as lojas abrem (Dia da Mulher,
Sexta-feira Santa, Páscoa, Tiradentes, Dia do Trabalho, Dia das Mães — aberta só em Itabirito).
