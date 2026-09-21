# Primeiro treinamento dos modelos de previsão — sem enriquecimento

**Projeto**: Sistema de Previsão de Estoque · Floricultura Verde Perto
**Data**: 2026-09-20
**Base usada**: 333.019 transações · 02/01/2024 – 28/02/2026 · 3 lojas × 3 categorias = 9 previsões
**Etapa do plano**: Fase 1 — modelo de referência, sem dados externos
([plano de experimentos](plano_experimentos_modelagem.md))

Este documento explica, sem jargão técnico, o que foi treinado, como foi testado, o que cada
número significa e o que os resultados querem dizer para o negócio. Um anexo técnico curto no
final reúne os detalhes para quem precisar reproduzir o experimento.

---

## 1. Resumo em um minuto

- **O que fizemos**: treinamos o primeiro modelo estatístico de previsão de vendas diárias para
  cada uma das 9 combinações de loja e categoria (Grama, Plantas de corte e Produtos de jardim
  em Jardim Canadá, Itabirito e Garden Center).
- **"Sem enriquecimento"** significa que o modelo usou **só o histórico de vendas e o calendário
  básico** (dia da semana e feriados nacionais fixos). Não usou clima, feriados municipais nem
  datas comemorativas como Dia das Mães. Isso é proposital: precisamos de um **ponto de partida
  honesto** para, mais adiante, provar (ou não) que buscar dados externos vale o esforço.
- **Resultado principal**: o modelo **erra menos do que uma regra simples** ("vai vender o mesmo
  que na semana passada") em 8 das 9 combinações, com folga na maioria delas. Só **Plantas de
  corte do Garden Center** ficou pior que a regra simples.
- **Ressalva importante**: no dia a dia, o erro ainda é grande em termos absolutos — na ordem de
  **cerca de metade a mais que o total da venda média do dia**. O modelo acerta bem o *formato* da semana
  (quais dias vendem mais), mas o *tamanho* de cada dia individual é muito variável.
- **O calendário ajuda**: incluir o dia da semana e feriados melhorou o modelo em 7 das 9
  combinações (em 2 delas, por margem mínima) e deixou os erros mais "limpos", sem padrão
  semanal sobrando.
- **Conclusão prática**: este modelo já serve como **primeira estimativa com aviso de confiança**,
  mas ainda **não é o resultado final**. O próximo passo é testar se dados externos melhoram os
  números.

---

## 2. O que estamos prevendo

O sistema prevê a **quantidade que deve ser vendida por dia**, nos próximos 14 dias, para cada
loja e categoria. Conforme decidido com a floricultura, ele **não** calcula quanto comprar nem
controla estoque — a loja continua decidindo sozinha quando e quanto repor
([ADR-011](ADR-011-escopo-previsao-sem-reposicao.md)). O que entregamos é a previsão de venda.

Prevemos por **loja × categoria** (e não por produto) porque produtos individuais vendem pouco e
de forma irregular demais para serem previstos sozinhos — isso foi mostrado na
[análise exploratória](00-eda_report.md).

---

## 3. Os dois modelos comparados

Treinamos duas versões, para saber quanto o calendário realmente acrescenta:

| Modelo | O que usa | Para que serve |
| --- | --- | --- |
| **A0 — só histórico** | Apenas o padrão das vendas passadas (inclusive o ritmo semanal) | Piso de comparação: o mínimo que se consegue só olhando para trás |
| **A1 — histórico + calendário** | O mesmo, mais: qual é o dia da semana, se é feriado nacional e se é véspera de feriado | O modelo de referência "sem enriquecimento" |

O que **ficou de fora de propósito** (será testado na Fase 3, "Modelo B"): clima, feriados
municipais de Nova Lima e Itabirito e datas comemorativas (Dia das Mães, Namorados, Finados,
Natal). Sabemos pela análise exploratória que essas datas mexem muito com **Plantas de corte** —
então já esperamos que essa categoria seja a mais beneficiada quando entrarem.

Um detalhe de precisão: o "feriado nacional" usado no A1 é uma lista fixa (Ano Novo, Tiradentes,
Dia do Trabalho, 7 de setembro, 12 de outubro, Finados, 15 de novembro e Natal). Por isso Finados
e Natal aparecem no modelo como feriados comuns; o que falta é o efeito dos **dias que
antecedem** essas datas, que é diferente para cada categoria.

**Como o modelo "pensa"** (analogia): é como um gerente experiente que olha as vendas das últimas
semanas, sabe que "terça costuma ser forte e sábado fraco" e ajusta a expectativa de cada dia
com base nisso. O nome técnico é SARIMAX (A0 é a versão sem a parte do calendário).

---

## 4. Como testamos — a "prova" do modelo

Um modelo sempre parece bom nos dados em que foi treinado. O que importa é como ele se sai **em
dias que nunca viu**. Usamos dois testes:

**Prova final (28 dias).** Treinamos com os dados até 31/01/2026 e pedimos a previsão de
**fevereiro de 2026 inteiro** (01 a 28/02), que o modelo não conhecia. Depois comparamos com o
que realmente foi vendido.

**Simulação de 4 previsões passadas (14 dias cada).** Para não depender de um único mês, o modelo
também "voltou no tempo" quatro vezes (cobrindo de 7/12/2025 a 31/01/2026), fez previsões de 14 dias como
se fosse o dia da previsão, e comparamos com o que aconteceu. O horizonte de 14 dias é o mesmo
que o sistema entregará no uso real. Se o modelo vai bem nas quatro janelas, é sinal de que não
foi sorte.

---

## 5. Como ler cada número

### Erro médio por dia

Em média, **quantas unidades por dia** a previsão erra, para mais ou para menos. É a métrica mais
intuitiva, mas depende do tamanho da categoria: errar 15 unidades é grave em Plantas de corte
(vende ~30/dia) e irrelevante em Grama (vende ~600/dia). Por isso comparamos sempre com a venda
média do dia.

### MASE — "estamos melhor que a regra simples?"

É a métrica de decisão principal. Compara o erro do modelo com o erro de uma regra bem simples:
**"vai vender o mesmo que vendeu no mesmo dia da semana anterior"**.

- **Abaixo de 1,0**: o modelo erra **menos** que a regra simples. **Quanto menor, melhor.**
- **Igual a 1,0**: empate com a regra simples — o modelo não acrescenta nada.
- **Acima de 1,0**: o modelo erra **mais** que a regra simples. Nesse caso, a regra simples seria
  melhor.

Exemplo: MASE de 0,40 significa que o modelo erra cerca de 40% do que a regra simples costuma
errar. É a nossa régua de aprovação: **precisa ser menor que 1,0**.

### RMSSE — o mesmo teste, mas punindo os "erros grandes"

Funciona como o MASE (abaixo de 1,0 é bom), porém dá mais peso a erros muito grandes em um único
dia. Serve para revelar se um bom resultado médio esconde alguns dias muito errados.

### Faixa de incerteza (cobertura do intervalo de 95%)

Além do número previsto, o modelo entrega uma **faixa** ("de X a Y unidades") que deveria conter a
venda real em cerca de 95% dos dias. Verificamos se isso é verdade: **dos 28 dias de teste,
quantos caíram dentro da faixa?**

- Aceitamos de **90% a 98%**.
- Muito abaixo: o modelo está **confiante demais** — a faixa é estreita e a realidade escapa.
- Muito acima: o modelo está **cauteloso demais** — a faixa é tão larga que não ajuda.
- **Atenção**: com só 28 dias, cada dia fora da faixa custa 3,6 pontos percentuais. Acertar 25 de
  28 dá 89,3% (reprovado por um ponto) e 26 de 28 dá 92,9% (aprovado). Ou seja, esse critério é
  **muito sensível a um único dia** nesta amostra pequena.

### Diagnóstico dos erros — "sobrou algum padrão que o modelo não percebeu?"

Dois testes olham para os erros do modelo (a diferença entre previsto e real nos dados de
treino):

- **Teste de padrão sobrando (Ljung-Box)**: verifica se os erros seguem algum ritmo (por exemplo,
  errar sempre para baixo às sextas). Se sim, o modelo deixou passar informação útil. **Resultado
  "aprovado" = os erros parecem aleatórios**, que é o desejado.
- **Teste de formato dos erros (Shapiro-Wilk)**: verifica se os erros têm o formato "de sino"
  esperado. Em vendas com picos (pedidos grandes de paisagismo) quase nunca têm. Por decisão do
  projeto, esse teste **só gera aviso e não reprova** o modelo.

### MAPE e sMAPE — percentuais de erro

Também foram calculados, mas são **apenas informativos**: como há dias de venda zero (domingo,
loja fechada) e dias de venda muito baixa, o erro percentual "explode" e passa uma impressão
exagerada. Por isso não entram na decisão.

### Status: "confiável" ou "com aviso"

- **`trained` (treinado)**: passou nos dois critérios — MASE abaixo de 1,0 **e** faixa de
  incerteza entre 90% e 98%.
- **`low_confidence` (confiança reduzida)**: falhou em pelo menos um. **Não é uma falha do
  sistema**: a previsão continua sendo gerada, mas o painel mostra um aviso visual para o
  usuário.

---

## 6. Resultados

### 6.1 O modelo bate a regra simples?

Resultado na prova final (fevereiro/2026) e na média das 4 simulações passadas. **Menor é
melhor; abaixo de 1,0 é aprovado.**

| Loja · Categoria | MASE prova final A0 | MASE prova final A1 | Média das 4 simulações A0 | Média das 4 simulações A1 |
| --- | --- | --- | --- | --- |
| Garden Center · Grama | 0,44 | 0,43 | 0,73 | 0,60 |
| Garden Center · Plantas de corte | **1,03** | **1,16** | **1,10** | **1,06** |
| Garden Center · Produtos de jardim | 0,66 | 0,46 | 0,99 | 0,53 |
| Itabirito · Grama | 0,44 | 0,43 | **2,19** | **2,19** |
| Itabirito · Plantas de corte | 0,39 | 0,33 | 0,56 | 0,55 |
| Itabirito · Produtos de jardim | 0,49 | 0,49 | 0,78 | 0,72 |
| Jardim Canadá · Grama | 0,38 | 0,37 | 0,72 | 0,65 |
| Jardim Canadá · Plantas de corte | 0,38 | 0,34 | 0,64 | 0,56 |
| Jardim Canadá · Produtos de jardim | 0,30 | 0,41 | 0,38 | 0,36 |

**Como ler:**

- Na prova final, **16 dos 18 modelos** ficaram abaixo de 1,0. Os dois que não ficaram são os de
  Garden Center · Plantas de corte.
- Os números das simulações passadas são **piores** que os da prova final. Isso é esperado: elas
  incluem períodos difíceis (fim de ano, com muito mais volatilidade) e fazem previsões de 14 dias
  seguidos, com menos informação recente. Duas linhas merecem atenção (em negrito): Garden Center
  · Plantas de corte (acima de 1,0) e Itabirito · Grama (2,19) — explicadas na seção 7.

### 6.2 O calendário ajuda? (A1 contra A0)

- **Prova final**: o A1 é melhor em **7 das 9** combinações. Em duas delas (Itabirito · Grama e
  Itabirito · Produtos de jardim) a diferença é mínima — na prática, empate. Melhoras claras:
  Garden Center · Produtos de jardim (0,66 → 0,46), Itabirito · Plantas de corte (0,39 → 0,33) e
  Jardim Canadá · Plantas de corte (0,38 → 0,34). O A1 foi pior em Garden Center · Plantas de
  corte e Jardim Canadá · Produtos de jardim.
- **Simulações passadas**: o A1 é **igual ou melhor em todas as 9**. Como essa avaliação junta
  quatro janelas diferentes, é a evidência mais robusta — ela sugere que o calendário realmente
  ajuda, e que o único caso "pior" na prova final (Jardim Canadá · Produtos de jardim) foi
  oscilação de uma amostra curta.
- **Qualidade dos erros**: no A0, **6 das 9** combinações têm erros com padrão sobrando (o modelo
  deixou passar informação). No A1, **só 2 das 9** (Garden Center · Grama e Garden Center ·
  Plantas de corte). Ou seja, o calendário "explica" o ritmo semanal que o A0 só capturava pela
  metade.

**Em resumo: o calendário simples já traz ganho real**, sobretudo em Plantas de corte e nas lojas
maiores. Isso é bom: significa que o caminho de enriquecer com mais informação de calendário faz
sentido.

### 6.3 Quão grande é o erro, na prática?

O MASE compara com uma regra simples, mas o gestor quer saber: **"em quantas unidades por dia o
modelo erra?"** Abaixo, o erro médio por dia do modelo A1 em fevereiro/2026, comparado com a
venda média do dia nesse mês (já incluindo os domingos fechados):

| Loja · Categoria | Venda média por dia (fev/26) | Erro médio por dia (A1) | Erro em relação à venda |
| --- | --- | --- | --- |
| Garden Center · Grama | 271 | 260 | ~96% |
| Garden Center · Plantas de corte | 15 | 16 | ~106% |
| Garden Center · Produtos de jardim | 294 | 208 | ~71% |
| Itabirito · Grama | 575 | 526 | ~91% |
| Itabirito · Plantas de corte | 31 | 15 | ~49% |
| Itabirito · Produtos de jardim | 690 | 402 | ~58% |
| Jardim Canadá · Grama | 613 | 443 | ~72% |
| Jardim Canadá · Plantas de corte | 30 | 18 | ~60% |
| Jardim Canadá · Produtos de jardim | 633 | 472 | ~75% |

**Leitura honesta**: no nível **diário**, o erro é alto — de cerca de metade a mais que o total
da venda média do dia. Isso não é falha do modelo, e sim da natureza dos dados: as vendas por dia oscilam muito
(pedidos grandes de paisagismo, dias sem movimento). A regra simples de "repetir a semana
passada" erra ainda mais, e é por isso que o MASE fica abaixo de 1,0. Mas **quem for usar a
previsão precisa saber que ela indica a ordem de grandeza e o formato da semana, não o número
exato de cada dia.** Ainda não medimos o erro em **totais semanais** (onde erros de um dia e de
outro podem se compensar) — essa medida é um dos próximos passos e pode ser mais favorável.

### 6.4 As faixas de incerteza estão calibradas?

Dos 28 dias de fevereiro, o número de dias que a venda real caiu dentro da faixa prevista foi de
**23 a 26** (82% a 93%). Na prática:

- 17 dos 18 modelos ficaram entre 89% e 93% — próximo da meta, dentro da margem de erro de uma
  amostra de 28 dias. Nenhum passou de 93%, ou seja, nenhuma faixa se mostrou larga demais.
- O pior caso foi Garden Center · Plantas de corte com A1 (82%, 23 de 28 dias) — a faixa dele é
  estreita demais para a realidade.

Ver a observação da seção 5: como um único dia muda o resultado em 3,6 pontos, **não devemos
tirar conclusões fortes de diferenças pequenas** nesse critério.

### 6.5 Quais ficaram com confiança normal?

| Loja · Categoria | A0 | A1 |
| --- | --- | --- |
| Garden Center · Grama | aviso | aviso |
| Garden Center · Plantas de corte | aviso | aviso |
| Garden Center · Produtos de jardim | aviso | aviso |
| Itabirito · Grama | confiável | aviso |
| Itabirito · Plantas de corte | aviso | confiável |
| Itabirito · Produtos de jardim | confiável | confiável |
| Jardim Canadá · Grama | confiável | confiável |
| Jardim Canadá · Plantas de corte | confiável | confiável |
| Jardim Canadá · Produtos de jardim | confiável | confiável |

**10 dos 18 modelos** ficaram como confiáveis. Todos os de Garden Center ficaram com aviso — o que
é coerente com a análise exploratória, que já indicava confiança reduzida para uma loja com
menos de um ano de histórico. Dos 8 avisos, 6 vêm **só** da faixa de incerteza (89,3% = 25 de 28
dias, a um dia de passar), e não do erro em si; 1 vem só do MASE e 1 dos dois — os dois de
Garden Center · Plantas de corte.

---

## 7. Os casos que merecem atenção

**Itabirito · Grama — o número de 2,19 nas simulações passadas.**
Na prova final o modelo foi bem (0,43), mas nas simulações o resultado médio foi ruim. O motivo
está em uma única janela: a de **7 a 20 de dezembro de 2025**, com MASE de **6,9**. Nela ocorreu
o maior pedido individual da base — **61.561 unidades de grama em um só dia (16/12/2025)** —, um
pedido pontual (provavelmente paisagismo ou obra), impossível de antecipar só pelo histórico.
Depois dessa janela, os resultados voltam a ser excelentes (0,13 e 0,16 nas duas últimas). Ou
seja, **o modelo é bom no dia a dia dessa combinação, mas não tem como prever pedidos gigantes
isolados** — o que precisa ser comunicado ao usuário.

**Garden Center · Plantas de corte — o único que perde para a regra simples.**
É a combinação com menos histórico (221 dias com venda) e é a mais irregular: cerca de 30% dos
dias úteis sem nenhuma venda. A análise exploratória já alertava que aqui a venda se explica
mais por **datas comemorativas** do que pelo ritmo semanal — justamente o que este modelo ainda
não tem. O calendário simples (A1) não ajudou; é o candidato mais forte para melhorar quando as
datas comemorativas entrarem.

**Jardim Canadá · Produtos de jardim — A0 melhor na prova final, A1 melhor nas simulações.**
As duas versões têm resultados muito bons (0,30 e 0,41 na prova final; 0,38 e 0,36 nas
simulações). A diferença não é consistente, então **não devemos concluir que o A0 é melhor**.

**Garden Center como um todo.**
Loja aberta em fevereiro de 2025: pouco histórico, ainda sem um ciclo completo de datas
comemorativas. Todos os modelos dela ficam com aviso de confiança reduzida, o que é o
comportamento correto.

**Jardim Canadá e Itabirito · Plantas de corte — bons resultados.**
Erros baixos em relação à regra simples (0,33 a 0,39) e, no A1, erros sem padrão sobrando.
Mesmo assim, o erro diário é alto em termos relativos (49% a 60% da venda) — vale lembrar que
são volumes pequenos (~30 unidades por dia).

---

## 8. O que isso significa para o negócio

1. **O modelo é utilizável como primeira estimativa, com avisos.** Ele acerta o ritmo semanal e
   bate uma regra simples na quase totalidade dos casos — mas não deve ser lido como uma previsão
   de precisão diária.
2. **O calendário simples já ajuda.** Isso valida o caminho do projeto: mais informações de
   calendário (datas comemorativas, feriados municipais) tendem a melhorar ainda mais,
   principalmente em Plantas de corte.
3. **Pedidos grandes e pontuais não são previsíveis** pelo histórico. Se houver informação
   comercial (obras contratadas, encomendas de paisagismo), ela precisa vir de fora — fica como
   sugestão de conversa com a floricultura.
4. **Garden Center precisa de mais tempo.** As previsões dessa loja devem continuar com aviso até
   completar pelo menos um ano de operação.
5. **Este é o ponto de partida.** Todos os números daqui viram a **linha de base** contra a qual
   os modelos enriquecidos serão comparados. Se o modelo enriquecido não superar esses números
   por uma margem que compense o esforço, não vale incorporá-lo.

---

## 9. Limitações e cuidados

- **A prova final é um único mês (fevereiro/2026)**, que para várias categorias é baixa
  temporada. Em Jardim Canadá, por exemplo, a venda média de fevereiro (~613 e ~633 por dia) foi
  menos da metade da média de todo o período anterior (~1.287 e ~1.529). Isso torna os números
  mais sensíveis à época do ano.
- **Fevereiro/2026 pode estar incompleto na base.** Ainda não sabemos se o mês foi fechado ou é uma
  exportação parcial (pergunta em aberto nº 1 da
  [análise exploratória](00-eda_report.md#5-perguntas-em-aberto-para-a-floricultura)).
- **Devoluções**: um dia de Jardim Canadá · Plantas de corte (30/07/2024) tinha soma negativa (−13
  unidades) por devolução. Tratamos como zero, por falta de definição da floricultura (pergunta
  nº 4).
- **Sem tendência de longo prazo.** O modelo assume um nível de vendas estável. Lojas em queda
  forte (Jardim Canadá, −37% a −49% ao ano) ou em alta forte (Itabirito · Grama, +96% ao ano)
  podem ter a previsão subestimada ou superestimada. Testar um termo de tendência é um dos
  próximos passos. Pelo mesmo motivo, o MASE pode parecer melhor do que a realidade nas séries
  que caíram de volume (o "ruído de referência" foi calculado em um período de vendas maiores).
- **O "status" atual olha só para a prova final**, não para as simulações passadas. Um exemplo é
  Itabirito · Grama com A0, que ficou "confiável" apesar do MASE 2,19 nas simulações. A regra de
  status precisa ser revista para considerar as duas avaliações.
- **Estes não são os modelos finais de produção.** Foram treinados só até 31/01/2026, para poder
  ser testados em fevereiro. Os modelos de uso real serão treinados com todo o histórico.

---

## 10. Próximos passos

1. **Fase 2–3 do plano**: incluir datas comemorativas, feriados municipais e clima (Modelo B) e
   comparar com estes números, combinação por combinação.
2. **Medir o erro em totais semanais**, mais próximo de como a previsão será usada.
3. **Testar um termo de tendência** nas lojas com crescimento ou queda forte.
4. **Revisar a regra de status** para considerar também as simulações passadas.
5. **Perguntas em aberto à floricultura**: fevereiro/2026 é mês fechado? Como tratar
   devoluções? A queda de Jardim Canadá e a alta de Itabirito são reais? Há informação
   antecipada sobre pedidos grandes?

---

## Anexo técnico

**Dados de teste.** Prova final: 01/02/2026 a 28/02/2026 (28 dias), com ajuste da ordem do modelo
feito só sobre os dados anteriores. Simulações passadas: 4 janelas de 14 dias, com origem móvel
(último dia de treino em 06/12/2025, 20/12/2025, 03/01/2026 e 17/01/2026, iguais para as 9
séries), sem sobrepor a prova final.

**Configuração.** SARIMAX com sazonalidade semanal (m = 7), diferenciação sazonal fixa em D = 0
([ADR-004](ADR-004-d0-sarimax-sazonal.md)), busca em grade de p, q ∈ 0..2 e P, Q ∈ 0..1 pelo
critério AIC (36 combinações por modelo), transformação `log1p` nas 9 séries (todas com
coeficiente de variação acima de 0,7), termo constante (`trend='c'`). Dias com soma negativa
foram truncados em 0. Métricas calculadas na escala original (unidades vendidas), não em log.
Tempo total de execução: 675 s (11 min).

**Ordens escolhidas** `(p,d,q)(P,D,Q,m)`:

| Loja · Categoria | A0 | A1 |
| --- | --- | --- |
| Garden Center · Grama | (1,0,2)(1,0,1,7) | (0,0,2)(0,0,1,7) |
| Garden Center · Plantas de corte | (1,0,2)(1,0,1,7) | (0,0,2)(1,0,1,7) |
| Garden Center · Produtos de jardim | (0,0,2)(1,0,1,7) | (1,0,2)(0,0,1,7) |
| Itabirito · Grama | (0,0,2)(1,0,1,7) | (0,0,2)(0,0,1,7) |
| Itabirito · Plantas de corte | (0,0,2)(1,0,1,7) | (2,0,2)(0,0,1,7) |
| Itabirito · Produtos de jardim | (1,0,1)(1,0,1,7) | (0,0,2)(0,0,1,7) |
| Jardim Canadá · Grama | (0,0,2)(1,0,1,7) | (1,0,1)(1,0,0,7) |
| Jardim Canadá · Plantas de corte | (0,0,2)(1,0,1,7) | (1,0,1)(0,0,1,7) |
| Jardim Canadá · Produtos de jardim | (0,0,2)(1,0,1,7) | (0,0,2)(0,0,1,7) |

Repare que, no A1, quase todas as combinações dispensam a parte sazonal do histórico
(`P = 0`): com o dia da semana informado diretamente, o modelo precisa de menos "memória" do
passado — exatamente o que a análise exploratória antecipava.

**Arquivos gerados**

- Resumo por loja × categoria × modelo:
  [`baseline_A0_A1.csv`](../../ia-predictor/training_scripts/results/metrics/baseline_A0_A1.csv)
- Detalhe completo (inclui cada janela das simulações passadas):
  [`baseline_A0_A1.json`](../../ia-predictor/training_scripts/results/metrics/baseline_A0_A1.json)
- Código: `ia-predictor/training_scripts/baseline/`

**Como reproduzir** (a partir de `ia-predictor/`, com a base de transações já preparada):

```bash
python -m training_scripts.baseline.run_baseline
```
