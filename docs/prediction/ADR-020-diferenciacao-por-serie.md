# ADR-020 — Diferenciação (d) escolhida série a série pelo walk-forward

**Status:** aceito · **Data:** 2026-11-09 · **Revisa:** ADR-017 (o "d = 0 fixo" da receita)
**Histórico:** a 1ª versão deste ADR (mesmo dia) fixava d por família — d = 1 em Grama, Plantas
diversas e Produtos de jardim, d = 0 em Flores de corte —, com base num teste de estacionariedade
que não reproduzia a série nem a janela do modelo (doc 10 §3.1). Refeito o teste, a decisão passou
a ser série a série.
**Afeta:** `backend/domain/models/trainer.py` (`ConfigTreino.d_candidatos`, `_avaliar_d`),
`backend/services/servico_previsao.py` (`config_treino`, `_receita`, log),
`backend/config.py` (`FORECAST_SERVICE_D_CANDIDATES`), `openapi.yaml` 8.0.0 (`d_candidatos`)
**Evidência:** [doc 10](10-estacionariedade_e_diferenciacao.md) ·
`training_scripts/validation/estacionariedade_fiel_ao_modelo.py`, `variantes_nivel_sazonal.py`

---

## 1. Contexto

O ADR-017 fixou d = 0 em todas as séries: no histórico inteiro, o ADF rejeitava a raiz unitária. Com
d = 0 e constante, a previsão volta para a média da janela de 365 dias em ~2 semanas (doc 09 §4);
nas séries cujo nível muda dentro do ano, o modelo fica preso à média do ano. No walk-forward, d = 1
errou menos em 15 das 23 séries com previsão e mais em 8 (doc 10 §4.1).

## 2. Decisão

- **Em cada série, o treino roda a escolha da ordem por AIC e o walk-forward duas vezes, com d = 0
  e com d = 1, e fica com o d cujo walk-forward errou menos** (erro médio por dia, MAE, nos dias de
  loja aberta das 56 origens). Empate fica com d = 0. Se um dos d não ajusta, fica o outro.
- d = 0 leva constante; d = 1 não (`forecaster.ajustar`: a constante viraria tendência).
- O complemento, a previsão final e as métricas são os do d escolhido. O erro de cada d
  fica em `series_models.metrics.selecao_d` (com `d_escolhido`) e no log da série.
- `FORECAST_SERVICE_D_CANDIDATES` (padrão `[0, 1]`); `[0]` volta a d = 0 em tudo.
- A receita do modelo (os candidatos, horizontes, janela...) entra na impressão digital do treino:
  depois de mudá-la, o próximo "Treinar previsões" treina mesmo sem venda nova.

## 3. Fundamento

Resumo do doc 10 (teste no resíduo da regressão com as exógenas do SARIMAX, em todos os dias, na
janela de ajuste de cada um dos 52 treinos semanais):

1. **Como se escolhe d.** O AIC não compara modelos com d diferente; d sai de teste de
   estacionariedade (Hyndman & Khandakar, 2008: KPSS nos resíduos da regressão) ou do erro fora da
   amostra (Hyndman & Athanasopoulos, *FPP3* §5.10).
2. **O KPSS concorda com o walk-forward.** Nas 8 séries em que ele rejeita a estacionariedade do nível
   na maioria das janelas — Grama das 2 lojas, Plantas e Produtos de jardim de Jardim Canadá, e os
   produtos de grama que mais vendem —, d = 1 erra menos em todas; nenhuma série em que ele rejeita
   fica melhor com d = 0. O KPSS é o teste LM da variância do nível no modelo de nível local, cuja
   forma reduzida é integrada de ordem 1 (Harvey, 1989).
3. **Mas o KPSS não decide as séries esparsas.** Em 7 séries d = 1 ajuda sem que ele rejeite (3
   significativas: Esmeralda ITO de Jardim Canadá −23,5%, grama preta pelo de urso −6,5%, capim dos
   Texas verde −5,0%). Vendem de 3 a 61 un./dia; com o ruído do dia muito maior que a variação do
   nível, o KPSS tem pouco poder. Não rejeitar é falta de evidência.
4. **O ADF não serve aqui.** Com raiz MA perto de −1 na diferença (autocorrelação de lag 1 entre
   −0,43 e −0,54), ele rejeita a raiz unitária por distorção (Schwert, 1989): com poucos lags diria
   d = 0 em tudo; com o lag de Schwert, passa a concordar com o KPSS.
5. **Critérios comparados** (erro sobre d = 0 em tudo, 23 séries, ano de 03/2025 a 02/2026): KPSS
   a cada treino −2,5%; d fixo por família −3,6%; **erro do walk-forward da própria série −3,6% a
   −3,8%**; o melhor d de cada série escolhido olhando o ano inteiro, −3,9%.

## 4. Alternativas descartadas

| Alternativa | Erro sobre d = 0 | Por que não |
| --- | --- | --- |
| d = 0 em tudo (ADR-017) | 0 | o nível de várias séries muda dentro da janela; erra mais |
| d = 1 em tudo | −3,5% | piora Flores de corte, Zeon e capim dos Texas roxo, com significância |
| d fixo por família (1ª versão deste ADR) | −3,6% | põe d = 1 em séries em que d = 0 erra menos (Zeon, capim roxo, São Carlos de JC, Plantas de ITA) e não se ajusta quando a série muda |
| KPSS a cada treino (`auto.arima`) | −2,5% | sem poder nas séries esparsas, em que d = 1 ajuda |
| ADF a cada treino | 0 a −2,2% (conforme os lags) | distorcido pela raiz MA perto de −1 |

## 5. Consequências

- **Tempo de treino:** a escolha da ordem e o walk-forward rodam 2 vezes por série — 40 min contra 13,5 min no treino local (14 processos; o d = 1 ajusta mais devagar). No Render o treino é externo (script), sem limite de tempo da API.
- **Viés de seleção:** os indicadores vêm do walk-forward do d escolhido (o menor de 2
  erros), um pouco otimistas.
- **O d pode trocar entre treinos** quando os dois erros ficam próximos; a forma da previsão muda
  junto. O histórico congelado guarda o que a loja viu.
- **Faixa de 95% e horizonte longo:** com d = 1 a faixa abre com o horizonte (+10% de largura da 1ª à
  13ª semana, cobertura em 92–93%), e a previsão é melhor que a de d = 0 até a 6ª semana e pior da
  7ª em diante (ADR-021 §3.1).
- **Constituição:** o Princípio II pede SARIMAX com m = 7 e exógenas de calendário; não fixa d. O
  Princípio III pede o walk-forward antes da previsão, e ele continua rodando em toda série. Nada a
  emendar.

## 6. Resultado no treino de produção

Treino de produção na base local (vendas até 28/02/2026; walk-forward de 56 origens de 22/12/2025 a
15/02/2026), 09/11/2026. Comparado com o mesmo treino com d = 0 em tudo e com a 1ª versão (d por
família), na mesma base.

| Série | d escolhido | Erro médio por dia, d = 0 | Erro médio por dia, d = 1 | MASE (escolhido) |
| --- | --- | --- | --- | --- |
| JC · Grama | 0 | 688 | 700 | 0,945 |
| JC · Plantas diversas | **1** | 485 | 415 | 0,830 |
| JC · Produtos de jardim | **1** | 158 | 141 | 0,768 |
| JC · Flores de corte | 0 | 28,3 | 28,7 | 0,681 |
| ITA · Grama | 0 | 228 | 241 | 0,850 |
| ITA · Plantas diversas | **1** | 274 | 257 | 1,017 |
| ITA · Produtos de jardim | **1** | 91,0 | 78,3 | 0,803 |
| ITA · Flores de corte | 0 | 30,3 | 32,0 | 0,671 |
| JC · Grama Esmeralda ITO (00013475) | **1** | 16,3 | 10,7 | 0,520 |
| JC · Grama preta pelo de urso (166) | **1** | 25,1 | 14,5 | 0,385 |
| JC · Capim dos Texas verde (1294) | **1** | 5,2 | 4,7 | 0,673 |
| JC · Grama preta pelo de urso saq. (00150005) | **1** | 23,2 | 23,0 | 1,073 |
| ITA · Grama Amendoim (147) | **1** | 91,0 | 88,7 | 1,123 |
| As outras 10 séries de grama | 0 | — | — | — |

- **9 séries com d = 1 e 14 com d = 0.** As 23 têm previsão nas 3 receitas.
- **Erro do walk-forward deste treino, sobre d = 0 em tudo:** −4,2% nas 23 séries (família: −1,8%) e
  −6,0% nas 8 categorias (família: −4,7%). É o erro na mesma janela usada para escolher, então é
  otimista por construção; a estimativa honesta do ganho é a do ano (doc 10 §4.3: −3,6% a −3,8%).
- **Grama das 2 lojas e as gramas grandes (Esmeralda e Amendoim de JC, Esmeralda de ITA) ficaram com
  d = 0 neste treino**, embora no ano d = 1 erre menos nelas e o KPSS rejeite. As 8 semanas avaliadas
  são dez–fev, a queda depois das festas, e nessa virada d = 1 erra mais (doc 10 §6). A escolha
  segue o walk-forward do treino: quando a janela avaliada sair da virada, o treino volta a
  escolher d = 1 nelas.
- **Tempo:** 40 min com 14 processos (13,5 min com um d só), na mesma máquina.
