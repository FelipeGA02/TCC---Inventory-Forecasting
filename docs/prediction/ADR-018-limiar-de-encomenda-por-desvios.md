# ADR-018 — Limiar de encomenda grande de cada loja: média + 4 desvios-padrão dos pedidos

**Status:** proposto · **Data:** 2026-10-29 · **Revisa:** ADR-013 (limiar fixo de 2.000 un.)
**Afeta:** `training_scripts/preprocessing/remove_encomendas_06.py` (Etapa 6),
`backend/scripts/carga_inicial.py`, `backend/services/upload_service.py`, `sales.is_bulk_order`,
`processing_log.quality.limiar_encomenda_un`, `openapi.yaml` 5.0.0
**Evidência:** `training_scripts/eda/eda_limiar_encomendas.py` →
`training_scripts/results/plots/encomendas/` e `training_scripts/results/metrics/limiar_encomendas_*`

---

## 1. O problema

O ADR-013 decidiu que encomenda grande é o tamanho do **pedido** (a nota inteira) e
escolheu o limiar de 2.000 unidades por sensibilidade. O próprio ADR registra que o número
é "uma escolha nossa, não dos dados" (§6), e ele vale igual para duas lojas com pedidos de
tamanhos diferentes. A partir de agora, cada loja tem o seu limiar, tirado da distribuição
dos seus pedidos e recalculado quando chegam planilhas.

## 2. Decisão

```
pedido            = unidade × emissao × doc_tipo × doc_numero (CHAVE_VENDA, a do ADR-013)
quantidade        = soma de qtdade das linhas do pedido, sem Serviço e taxa, em unidades
limiar da loja    = média + 4 · desvio-padrão da quantidade de todos os pedidos da loja
                    (só pedidos com quantidade positiva)
encomenda grande  = pedido com quantidade > limiar da sua loja  →  todas as suas linhas
```

- **Unidades, sem transformação:** é a quantidade que a loja vê na nota.
- **Na carga inicial** (e na Etapa 6), o limiar de cada loja sai da base inteira dela e
  classifica a base.
- **Na planilha nova**, o limiar de cada loja é recalculado com os pedidos já gravados mais
  os da planilha e **classifica só as vendas inseridas**. O que já estava na base mantém a
  classificação que recebeu quando entrou.
  - Por isso a marcação de um pedido pode ter sido feita com um limiar diferente do atual.
  - É o mesmo princípio do histórico da previsão: o que a loja viu não é reescrito.
- **Onde o limiar fica gravado:** o de cada carga, por loja, em
  `processing_log.quality.limiar_encomenda_un`. As telas mostram o último
  (`limiares_encomenda_un`). O treino guarda o do momento na configuração do disparo, e o
  painel mostra o do treino que gerou a previsão.
- **Funções:** `calcular_limiares`, `limiar_por_desvios` e `marcar_encomendas_por_unidade`
  em `remove_encomendas_06.py`, as mesmas na Etapa 6, na carga inicial e no envio.
- **Loja sem pedidos:** vale o limiar fixo de 2.000.

## 3. A distribuição

Base de janeiro de 2024 a fevereiro de 2026 (`distribuicao_pedidos.png`):

| | Jardim Canadá | Itabirito |
| --- | ---: | ---: |
| pedidos | 73.943 | 58.625 |
| mediana | 6 | 3 |
| p90 | 57 | 19 |
| p99 | 531 | 200 |
| p99,9 | 3.011 | 3.783 |
| máximo | 42.043 | 61.172 |
| média | 38,6 | 25,1 |
| desvio-padrão | 326,0 | 483,6 |

| Limiar | Jardim Canadá | Itabirito |
| --- | --- | --- |
| média + 3 desvios | 1.017 un. · 294 pedidos · 30,4% do volume | 1.476 un. · 107 pedidos · 53,8% |
| **média + 4 desvios** | **1.343 un. · 209 pedidos · 26,9%** | **1.960 un. · 96 pedidos · 52,5%** |
| fixo do ADR-013 | 2.000 un. · 131 pedidos · 22,5% | 2.000 un. · 93 pedidos · 52,1% |

As distribuições são muito assimétricas: a média fica perto do p90 e o desvio-padrão é 8 a
19 vezes a média. Por isso "4 desvios" não corresponde aos 0,003% de uma normal. Ele marca
os 0,2% maiores pedidos, que respondem por um quarto (Jardim Canadá) a metade (Itabirito)
do volume.

## 4. Efeito nas séries do treino

O protocolo é o do ADR-013, aplicado às 17 séries que o sistema treina
(`limiar_encomendas_series.csv`). Com a base inteira classificada como na carga inicial,
fixo 2.000 → 4 desvios da loja:

| Série | CV do fluxo | % do volume | % do consumidor tirado |
| --- | --- | --- | --- |
| Jardim Canadá · Grama | 0,92 → 0,88 | 23,2 → 29,7 | 7,1 → 11,5 |
| Jardim Canadá · Plantas diversas | 0,72 → 0,69 | 23,9 → 27,0 | 1,8 → 2,9 |
| Jardim Canadá · Produtos de jardim | 0,71 → 0,70 | 14,0 → 15,8 | 0,2 → 0,3 |
| Jardim Canadá · Flores de corte | 1,44 → 1,44 | 29,2 → 29,2 | 0,0 → 0,0 |
| Itabirito · Grama | 1,44 → 1,43 | 68,8 → 69,0 | 8,1 → 8,1 |
| Itabirito · Plantas diversas | 0,85 → 0,82 | 43,4 → 44,1 | 1,0 → 1,0 |
| Itabirito · Produtos de jardim | 0,88 → 0,88 | 23,6 → 23,7 | 0,7 → 0,7 |
| Itabirito · Flores de corte | 1,38 → 1,38 | 3,2 → 3,2 | 0,0 → 0,0 |

- **Itabirito:** o limiar dá 1.960, quase o fixo, e nada muda de forma relevante.
- **Jardim Canadá:** o limiar desce para 1.343, e saem mais pedidos de grama. O CV cai de
  0,92 para 0,88, ao custo de 4,4 pontos a mais de venda de balcão
  (`GRAMA AMENDOIM UNID. BDJA`: de 16,0% para 24,4%).

## 4.1 Efeito no SARIMAX (treino de produção)

`training_scripts/encomendas/treino_por_limiar.py` roda a receita do sistema (`treinar_serie`,
`ConfigTreino()`: 56 origens de 1 dia, h = 14, janela de 365 dias) nas 17 séries com
previsão, com cada marcação. O resultado está em `results/metrics/treino_limiar_encomendas.csv`.
Cada variante é avaliada no **próprio** fluxo, como o sistema avalia, por isso:

- o que compara variantes é o erro relativo à naïve na mesma janela (ΣAE / ΣAE_naïve);
- o **MASE não serve** para isso: a escala dele (a naïve do treino) encolhe quando saem
  pedidos grandes, e o MASE de Jardim Canadá sobe mesmo com o erro relativo caindo.

**Erro relativo à naïve (menor é melhor) e status:**

| Série | fixo 2.000 | 4 desvios | 3 desvios |
| --- | --- | --- | --- |
| Jardim Canadá · Grama | 0,830 T | **0,817 T** | 0,799 LC (IC 88,9%, MASE 1,02) |
| Jardim Canadá · Plantas diversas | 0,960 T | **0,902 T** | 0,964 LC (IC 89,6%) |
| Jardim Canadá · Produtos de jardim | 0,947 T | 0,911 T | **0,840 T** |
| Jardim Canadá · Flores de corte | 0,797 LC | 0,797 LC | 0,795 LC |
| Jardim Canadá · Grama Amendoim (bandeja) | 0,918 T | 0,837 T | 0,794 LC (MASE 1,05) |
| Jardim Canadá · Grama Esmeralda | 0,853 LC | 0,858 LC | 0,849 LC |
| Jardim Canadá · Grama São Carlos | 0,891 LC (IC 99,7%) | **0,883 T** | 0,880 T |
| Jardim Canadá · Grama Esmeralda (ITO) | 1,760 T | 1,760 T | 1,760 T |
| Jardim Canadá · Grama Zeon | 0,972 T | 0,972 T | 0,970 T |
| Itabirito · Grama | 0,802 T | 0,802 T | 0,801 T |
| Itabirito · Plantas diversas | **1,028** LC | 1,090 LC | 1,222 LC |
| Itabirito · Produtos de jardim | 0,933 T | 0,933 T | 0,913 T |
| Itabirito · Flores de corte | 0,980 LC | 0,980 LC | 0,980 LC |
| Itabirito · 4 produtos de grama | iguais nas 3 variantes | | |
| **Séries `trained`** | **8** | **9** | **6** |

T = `trained`, LC = `low_confidence`.

- **4 desvios contra o fixo:**
  - melhor em 5 séries, todas de Jardim Canadá: Grama, Plantas diversas, Produtos de
    jardim, Grama Amendoim e Grama São Carlos;
  - pior em 2: Itabirito · Plantas diversas, +0,06; Jardim Canadá · Grama Esmeralda,
    +0,005;
  - igual nas outras 10, porque em Itabirito o limiar (1.960) quase não muda a marcação;
  - a faixa de 95% de Jardim Canadá fica mais estreita (Grama: 3.154 → 2.604 un.) e a
    cobertura cai, mas fica dentro de 90–98%;
  - Grama São Carlos de Jardim Canadá passa a `trained` (a cobertura era 99,7%).
- **3 desvios:**
  - erra menos ainda em parte de Jardim Canadá;
  - mas a faixa de 95% passa a cobrir menos de 90% em Grama e Plantas diversas, e o MASE
    passa de 1 em Grama e Grama Amendoim: 3 séries caem para `low_confidence`;
  - em Itabirito, Plantas diversas piora para 1,222.
- **Ressalva:** a janela de teste são as últimas 8 semanas (jan–fev/2026), e as diferenças
  só aparecem quando a marcação muda dentro da janela de treino ou de teste.

**Leitura:** 4 desvios ganha do fixo e de 3 desvios no critério do sistema (séries
`trained`) e erra menos que o fixo em Jardim Canadá, onde a marcação muda. É o valor adotado.

## 5. Consequências e cuidados

- **O limiar anda com a base.** Recalculado com a base até o fim de cada mês
  (`limiar_no_tempo.png`):
  - **Jardim Canadá** desce devagar, de 4.067 (jan/2024, poucos pedidos) para 1.343.
  - **Itabirito** fica perto de 1.000 em 2024, sobe para ~1.300 em 2025 e salta para 1.976
    em dez/2025.
- **Um pedido gigante move o limiar da loja.** O salto de Itabirito é o pedido de 61 mil m²
  de 16/12/2025: o desvio-padrão em unidades é sensível à própria cauda que ele deveria
  detectar. Como a base não é remarcada, os pedidos gravados antes continuam marcados. Só
  os seguintes são julgados pelo limiar novo, mais alto. O teste
  `test_planilha_nova_recalcula_o_limiar_e_nao_remarca_a_base` cobre esse caso.
- **Ordem das planilhas.** Como só as vendas inseridas são classificadas, a base depende da
  ordem em que as planilhas chegam. Uma base carregada de uma vez (`carga_inicial`) e a
  mesma base carregada planilha a planilha podem ter marcações diferentes perto do limiar.
- **O limiar usa a base inteira da loja,** inclusive os dias que o walk-forward testa. É
  uma característica da loja ("tamanho de pedido fora do comum"), não um parâmetro do
  modelo. Com 60 a 75 mil pedidos por loja, uma semana nova quase não o move.
- **O treino muda.** A marcação muda (sobretudo em Jardim Canadá), e com ela o fluxo diário
  e a impressão digital do treino: o próximo "Treinar previsões" treina de novo. O efeito
  medido está no §4.1.
- **Banco existente.** A base gravada foi classificada com 2.000 e não é remarcada. As
  telas mostram 2.000 por loja até a próxima planilha. Para a base inteira seguir o limiar
  novo, refaça a carga (`run_all` + `carga_inicial --recriar`).
- **Custo no envio.** A gravação soma a quantidade de todos os pedidos da base numa
  consulta agregada, ~130 mil linhas de volta.

## 6. O que ainda depende da parceira

A pergunta do ADR-013 §6 continua: a partir de quantas unidades a loja encomenda do
fornecedor? O limiar de 4 desvios diz o que é fora do comum na distribuição de cada loja.
Hoje ele cai em 1.343 (Jardim Canadá) e 1.960 (Itabirito).

## 7. Referências

- ADR-013 — encomenda é tamanho da venda (chave do pedido, protocolo de comparação).
- ADR-017 — as séries do treino.
- `training_scripts/eda/eda_limiar_encomendas.py` — distribuição, limiar no tempo e efeito nas séries.
