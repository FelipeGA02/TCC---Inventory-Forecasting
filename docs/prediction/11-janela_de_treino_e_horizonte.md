# 11 — Janela de treino e até onde a previsão aguenta

**Data:** 2026-11-10 ·
**Status:** experimento concluído. Adotado em 2026-11-10 pelo
[ADR-022](ADR-022-janela-de-treino-de-545-dias.md): janela de 545 dias para todas as séries
(opção 1 do §6), regra dos 28 dias com venda mantida nos últimos 365, horizonte da tela sem
mudança e um ícone de informação nas 4 gramas pequenas de Jardim Canadá (§4.1).
**Script:** `ia-predictor/training_scripts/validation/janela_treino_e_horizonte.py`
**Resultados:** `ia-predictor/training_scripts/results/metrics/janela_treino_e_horizonte/`
(fora do git: 276 arquivos `.csv.gz`, um por série × janela × d, além de `tabelas.md`,
`comparacao1_*.csv`, `comparacao2_*.csv` e `melhor_treino.json`). **Não apagar:** o melhor
treino de cada série vai servir de base para atualizar o Neon.

---

## 1. As perguntas

1. **Janela de treino:** cada série é treinada com os últimos 365 dias. Treinar com menos
   (90, 180, 270 dias), com mais (545 dias) ou com todo o histórico erra menos?
2. **Horizonte:** com a melhor janela de cada série, quanto o erro aumenta de 2 semanas para 3,
   4, 6, 8 semanas e 3 meses à frente? **A partir de quando a previsão fica ruim?**

As duas perguntas foram respondidas para as **23 séries que têm previsão**: 4 categorias × 2 lojas e
15 produtos de grama. A receita é a de produção (ADR-017/018/019/020): SARIMAX m = 7, d por série,
calendário da loja, fator das datas comemorativas, fluxo diário sem encomendas grandes. Só a janela
muda.

**Resposta curta:**

- **Janela:**
  - **Janela curta piora.** 90 dias erra 8,6% a mais nas categorias e 5,5% a mais na média
    das 23 séries.
  - **Janela mais longa ajuda pouco.** Usar 545 dias em todas as séries erra 1,9% a menos que 365;
    o histórico inteiro, 2,2% a menos nas categorias.
  - **A diferença é clara em poucas séries.** Nas categorias, só em Flores de corte, com o
    histórico inteiro: −7,9% em Itabirito e −4,9% em Jardim Canadá. Nos produtos, a melhor
    janela varia: três produtos pequenos de Jardim Canadá melhoram com o histórico inteiro e um
    com 180 dias.
- **Horizonte:**
  - **Na média, o erro sobe devagar.** Nas categorias, fica +3% na 4ª semana, +5% na 8ª e +7% no
    3º mês, comparado com as 2 primeiras semanas.
  - **As categorias nunca perdem da naïve,** e a faixa de 95% continua acertando de 88% a 97% até
    3 meses.
  - **As séries grandes de Jardim Canadá pioram de forma significativa a partir de 4 a 6
    semanas:** Produtos de jardim e Grama Esmeralda na 4ª, Grama na 6ª e Plantas diversas na 8ª.
    Em Itabirito, só a Grama Esmeralda (ITO) piora na 4ª semana; a Grama piora no 3º mês e o
    resto não piora.

## 2. Como foi testado

**Cortes semanais,** o ritmo em que a loja manda a planilha:
- 60 sábados, de 04/01/2025 a 21/02/2026.
- Em cada corte, cada série é treinada só com a venda até aquele dia e prevê 91 dias.
- Os 8 primeiros cortes só aquecem a escolha de d.
- A Tabela 1 avalia 51 cortes, de 01/03/2025 a 14/02/2026; o último corte avaliado é o último com
  os 14 dias seguintes conhecidos.
- Os dados são a base local, com venda até 28/02/2026.

**Janelas:** 90, 180, 270, 365 (produção), 545 dias e o histórico inteiro.
- O histórico inteiro vai desde janeiro de 2024: cerca de 425 dias no 1º corte avaliado e 780 no
  último.
- A janela é deslizante: o ajuste usa os últimos W dias até o corte.

**Igual à produção (ADR-020):**
- **d:** em cada corte, cada janela testa d = 0 e d = 1. Fica o d que errou menos nos 8 cortes
  anteriores cujos 14 dias já eram conhecidos no corte, sem olhar o futuro. Em produção, o d é
  escolhido pelas 56 origens do walk-forward; aqui ele sai dos cortes semanais anteriores.
- **Ordem:** escolhida por AIC (p, q ∈ 0..2; P, Q ∈ 0..1) na janela antes da 1ª origem do
  walk-forward do corte, como no treino de produção. Para caber no tempo, a ordem é escolhida de
  novo a cada 26 cortes: 3 escolhas por série, janela e d.
- **Fator das datas comemorativas:** calculado só com venda até o corte.
- **Corte inelegível:** o corte em que a série não seria treinada em produção
  (`motivo_inelegivel`: menos de 180 dias de histórico, ou produto com venda em menos de 28 dias
  da janela) fica fora **em todas as janelas**. Assim todas são comparadas nos mesmos cortes.

**Medida de erro:**
- MAE nos dias de loja aberta, em unidades por dia.
- A Tabela 1 usa os 14 dias seguintes a cada corte, o mesmo h do walk-forward.
- A naïve repete a última semana. A naïve e a escala do MASE saem sempre dos 365 dias antes do
  corte, qualquer que seja a janela: assim o denominador não muda com a janela.

**Teste estatístico:**
- Diebold-Mariano no erro absoluto de cada dia-alvo; os dias previstos por mais de um corte entram
  pela média.
- A variância de longo prazo usa o estimador EWC com ν = 0,4·T^(2/3) graus de liberdade e valor
  crítico t_ν. Com a autocorrelação dos erros de previsão diários, o teste de Diebold-Mariano
  original rejeita demais; o EWC corrige isso (Lazarus et al., 2018).
- Com 23 séries testadas, a Tabela 1 traz também o p ajustado por Holm (1979) no §3.1.

**Escolha da janela pelo sistema** (coluna "Janela escolhida a cada corte" da Tabela 1):
- Em cada corte, fica a janela que errou menos nos 8 cortes anteriores já conhecidos, a mesma regra
  do d.
- Escolher a janela pelo erro fora da amostra recente segue Pesaran & Timmermann (2007) e Inoue,
  Jin & Rossi (2017).
- A coluna "Melhor" é escolhida olhando o próprio período avaliado (*ex post*). Ela mostra o ganho
  máximo possível; a coluna da escolha automática mostra o ganho que o sistema conseguiria de
  verdade.

**Horizonte (Tabela 2):**
- Cada série usa a sua melhor janela.
- As faixas são marginais: 2 sem = dias 1–14, 3 sem = 15–21, 4 sem = 22–28, 6 sem = 29–42,
  8 sem = 43–56, 3 meses = 57–91.
- **Os dias-alvo são os mesmos em todas as faixas:** só entra o dia que foi previsto a 1, 2, …, 13
  semanas de distância. São 231–232 dias por série, de junho/2025 a fevereiro/2026. Assim a
  diferença entre as colunas vem só da distância, não de meses diferentes (doc 09 §3.3).
- **Regra de "fica ruim":**
  - a primeira faixa em que o erro é maior que o das 2 primeiras semanas com p < 0,05
    (Diebold-Mariano), ou
  - a primeira faixa em que o modelo erra tanto quanto ou mais que a naïve (erro ÷ naïve ≥ 1).

**Tempo de execução:**
- 274 tarefas (série × janela × d), cerca de 45 mil ajustes de SARIMAX.
- 5h50 em 8 processos, sem nenhuma falha.
- Na máquina de desenvolvimento, a vazão para de subir a partir de 4 processos.

## 3. Comparação 1 — janela de treino

**Tabela 1.**
- Cada célula é o MAE dos 14 dias seguintes a cada corte, em % sobre a janela de 365 dias:
  negativo erra menos.
- A coluna "p (DM)" compara a melhor janela com a de 365 dias.
- MASE e cobertura são os da melhor janela.

| Série | Dias avaliados | MAE 365 dias (un./dia) | 90 | 180 | 270 | 365 (hoje) | 545 | Histórico inteiro | Melhor | Ganho sobre 365 | p (DM) | Janela escolhida a cada corte | MASE (melhor) | IC 95% (melhor) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| Itabirito · Flores de corte | 300 | 37,5 | +8,9% | +11,4% | +5,4% | — | -6,2% | -7,9% | **tudo** | -7,9% | 0,000 | -6,6% | 0,79 | 94,6% |
| Itabirito · Grama | 300 | 247,7 | +11,6% | +2,9% | +0,4% | — | -2,0% | -1,9% | **545** | -2,0% | 0,147 | -1,3% | 0,83 | 93,6% |
| Itabirito · Plantas diversas | 300 | 217,6 | +4,3% | +0,8% | +0,7% | — | -0,6% | -0,0% | **545** | -0,6% | 0,693 | -0,4% | 0,88 | 94,9% |
| Itabirito · Produtos de jardim | 300 | 83,2 | +7,8% | +2,9% | +1,2% | — | -1,6% | -2,3% | **tudo** | -2,3% | 0,157 | +1,1% | 0,90 | 91,9% |
| Jardim Canadá · Flores de corte | 298 | 34,3 | +20,9% | +5,3% | +0,0% | — | -3,8% | -4,9% | **tudo** | -4,9% | 0,018 | -4,0% | 0,81 | 96,6% |
| Jardim Canadá · Grama | 298 | 626,4 | +8,3% | +1,5% | +0,0% | — | +0,3% | -0,2% | **tudo** | -0,2% | 0,811 | +1,4% | 0,81 | 94,7% |
| Jardim Canadá · Plantas diversas | 298 | 426,3 | +1,1% | -1,4% | -0,4% | — | -1,3% | +0,5% | **180** | -1,4% | 0,326 | -0,6% | 0,91 | 90,3% |
| Jardim Canadá · Produtos de jardim | 298 | 154,0 | +7,3% | +0,3% | +0,9% | — | -0,2% | -0,8% | **tudo** | -0,8% | 0,420 | +2,3% | 0,87 | 91,8% |
| Itabirito · GRAMA ESMERALDA ( ITO) (00013475) | 300 | 191,4 | +4,0% | +1,4% | -0,2% | — | +0,5% | +0,3% | **270** | -0,2% | 0,885 | -1,0% | 0,91 | 92,9% |
| Itabirito · GRAMA AMENDOIM UNID. BDJA (147) | 300 | 96,3 | -0,7% | -3,5% | -3,7% | — | +1,0% | -0,0% | **270** | -3,7% | 0,066 | -2,0% | 1,02 | 96,9% |
| Itabirito · GRAMA ESMERALDA (3) | 103 | 6,3 | -43,3% | -26,3% | -23,7% | — | +17,2% | +13,3% | **90** | -43,3% | 0,170 | -33,0% | 0,95 | 94,2% |
| Itabirito · GRAMA SAO CARLOS (710) | 300 | 25,1 | +9,9% | +0,5% | +1,1% | — | -2,8% | -2,1% | **545** | -2,8% | 0,136 | -1,5% | 1,14 | 98,0% |
| Jardim Canadá · GRAMA ESMERALDA ( ITO) (00013475) | 208 | 10,3 | -15,0% | +3,5% | +10,6% | — | -20,3% | -23,6% | **tudo** | -23,6% | 0,000 | -25,9% | 0,41 | 99,5% |
| Jardim Canadá · CAPIM DOS TEXAS ROXO (00020227) | 298 | 8,0 | +75,3% | +20,3% | +5,3% | — | -7,1% | -9,9% | **tudo** | -9,9% | 0,000 | -7,4% | 1,49 | 97,8% |
| Jardim Canadá · GRAMA PRETA PELO URSO SAQ (00150005) | 298 | 25,5 | +23,8% | -0,5% | -0,8% | — | +2,9% | +4,2% | **270** | -0,8% | 0,819 | +0,4% | 0,99 | 95,7% |
| Jardim Canadá · CAPIM DOS TEXAS ROXO (1293) | 298 | 15,4 | +20,9% | -0,5% | +1,2% | — | +3,4% | +8,4% | **180** | -0,5% | 0,978 | +2,3% | 1,35 | 94,4% |
| Jardim Canadá · CAPIM DOS TEXAS VERDE (1294) | 298 | 7,7 | -12,8% | -5,3% | +0,2% | — | +4,8% | +9,6% | **90** | -12,8% | 0,237 | -19,5% | 0,64 | 95,6% |
| Jardim Canadá · GRAMA AMENDOIM UNID. BDJA (147) | 298 | 447,0 | +4,9% | +0,6% | +0,3% | — | +0,3% | -0,4% | **tudo** | -0,4% | 0,572 | +0,8% | 0,89 | 92,8% |
| Jardim Canadá · GRAMA PRETA PELO DE URSO BDJA (UNID) (166) | 298 | 46,6 | -5,1% | -10,9% | -6,6% | — | +3,4% | +6,0% | **180** | -10,9% | 0,001 | -9,3% | 0,74 | 96,6% |
| Jardim Canadá · GRAMA PRETA ANA (167) | 112 | 23,6 | +12,5% | +6,8% | -9,6% | — | -19,2% | -6,9% | **545** | -19,2% | 0,035 | -19,1% | 0,88 | 96,6% |
| Jardim Canadá · GRAMA ZEON (1739) | 298 | 10,6 | +16,0% | +5,4% | +3,0% | — | -3,2% | -3,0% | **545** | -3,2% | 0,103 | -5,0% | 1,29 | 96,4% |
| Jardim Canadá · GRAMA ESMERALDA (3) | 298 | 331,5 | +6,6% | +2,0% | -0,5% | — | -0,9% | -1,2% | **tudo** | -1,2% | 0,261 | -0,2% | 0,86 | 95,6% |
| Jardim Canadá · GRAMA SAO CARLOS (710) | 298 | 71,1 | +2,8% | -0,5% | -1,6% | — | -1,2% | -0,5% | **270** | -1,6% | 0,062 | -0,6% | 0,97 | 92,8% |
| **Média (cada série pesa igual)** | | | **+5,5%** | **+0,4%** | **-0,9%** | — | **-1,9%** | **-1,3%** | | **-7,4%** | | **-6,1%** | | |
| **Média das 8 categorias** | | | **+8,6%** | **+2,9%** | **+1,0%** | — | **-1,9%** | **-2,2%** | | **-2,5%** | | **-1,1%** | | |

As médias são geométricas da razão de cada série ao MAE de 365 dias, para que uma série grande não
domine. Nos produtos (15 séries), a escolha automática fica em −8,8% e a melhor *ex post* em −9,8%.

### 3.1 O que é ganho de verdade

Foram testadas 23 séries. Com a correção de Holm para 23 testes, restam **4 ganhos
significativos**:

| Série | Melhor janela | Ganho | p | p (Holm) |
| --- | :---: | ---: | ---: | ---: |
| Jardim Canadá · GRAMA ESMERALDA ( ITO) (00013475) | tudo | −23,6% | < 0,001 | < 0,001 |
| Jardim Canadá · CAPIM DOS TEXAS ROXO (00020227) | tudo | −9,9% | < 0,001 | < 0,001 |
| Itabirito · Flores de corte | tudo | −7,9% | < 0,001 | 0,002 |
| Jardim Canadá · GRAMA PRETA PELO DE URSO BDJA (UNID) (166) | 180 | −10,9% | 0,001 | 0,026 |

**Não sobrevivem à correção** (p < 0,05 sem ela):
- Flores de corte de Jardim Canadá: −4,9%, p = 0,018, Holm 0,33.
- Grama Preta Ana: −19,2%, p = 0,035, Holm 0,63.

Nos dois casos a direção é a mesma das séries parecidas: Flores de corte nas 2 lojas, janela longa.
O mais provável é que o ganho seja real e menor.

**Os −43% da Grama Esmeralda (3) de Itabirito com 90 dias não são evidência:**
- A série vende 6 un./dia.
- Ela só foi treinável em 24 dos 60 cortes; nos outros, teve menos de 28 dias com venda na janela.
- O p é 0,17.

### 3.2 Leitura

**Janela curta piora quase sempre.**
- 90 dias erra mais em 18 das 23 séries; nas categorias, de +1% a +21%.
- Com 90 dias, o modelo tem pouca semana parecida para estimar o efeito de cada dia da semana e
  das datas.
- A faixa de 95% fica mais estreita (−8% a −15%), mas passa a errar mais: a cobertura cai de 2,5 a
  3,4 pontos. Ela fica estreita porque o modelo não viu variação suficiente, não porque a previsão
  ficou mais certa.

**Janela longa ajuda as séries que dependem das datas do ano.**
- Flores de corte vende pelas datas comemorativas. Com mais de um ano de janela, o modelo vê cada
  data mais de uma vez, e o fator da data (ADR-019) se apoia num nível mais estável.
- Nos produtos pequenos de Jardim Canadá, a janela longa dá mais dias com venda para estimar uma
  série quase toda de zeros. É o caso da Esmeralda (ITO), que vende 10 un./dia, e do Capim Roxo
  00020227, com 8 un./dia.

**Nas séries grandes, 270 dias até o histórico inteiro empatam com 365.**
- Grama, Plantas diversas, Produtos de jardim e as gramas grandes (Esmeralda, Amendoim, São
  Carlos) ficam a ±2% de 365, sem diferença significativa.
- Nelas, ~55% dos cortes ficam com d = 1. O d = 1 faz a previsão partir do nível recente, então o
  tamanho da janela pesa menos.

**A largura da faixa quase não muda com janela longa.**
- Com 545 dias ou o histórico inteiro, a faixa fica 0,4% a 3% mais larga e a cobertura sobe
  0,2–0,3 ponto.

**Escolher a janela série a série compensa nos produtos, não nas categorias.**
- Nos produtos, a escolha automática (−8,8%) chega perto do máximo *ex post* (−9,8%).
- Nas categorias, ela fica em −1,1%, pior que fixar o histórico inteiro (−2,2%) ou 545 dias
  (−1,9%). As diferenças entre janelas nas categorias são pequenas, e a escolha corte a corte
  acompanha o ruído.

## 4. Comparação 2 — até onde a previsão aguenta

**Tabela 2.**
- Cada coluna de semana é o MAE dos dias naquela distância, em % sobre o das 2 primeiras semanas,
  nos mesmos dias-alvo.
- \* = piora significativa (Diebold-Mariano, p < 0,05).
- ⚠ = nessa faixa o modelo erra tanto quanto ou mais que a naïve.

| Série | Janela | Dias avaliados | MAE até 2 sem (un./dia) | WAPE até 2 sem | Erro ÷ naïve (2 sem → 3 meses) | 3 sem | 4 sem | 6 sem | 8 sem | 3 meses | Cobertura IC 95% (2 sem → 3 meses) | Fica ruim a partir de |
| --- | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: | :---: | --- |
| Itabirito · Flores de corte | tudo | 232 | 35,2 | 59% | 0,71 → 0,64 | -0,4% | -0,6% | -0,6% | -0,8% | -2,9% | 94% → 94% | não piora até 3 meses |
| Itabirito · Grama | 545 | 232 | 241,3 | 74% | 0,75 → 0,72 | +1,8% | +1,1% | +1,6% | +2,5% | +4,2%* | 93% → 94% | **3 meses** |
| Itabirito · Plantas diversas | 545 | 232 | 227,2 | 41% | 0,76 → 0,73 | +0,4% | +1,5% | -0,2% | -1,3% | +2,1% | 94% → 94% | não piora até 3 meses |
| Itabirito · Produtos de jardim | tudo | 232 | 85,2 | 41% | 0,73 → 0,69 | +2,0% | +2,1% | +2,7% | +3,1% | +5,6% | 91% → 91% | não piora até 3 meses |
| Jardim Canadá · Flores de corte | tudo | 231 | 32,1 | 59% | 0,71 → 0,64 | +0,6% | -0,2% | -0,8% | -1,8% | -1,9% | 97% → 97% | não piora até 3 meses |
| Jardim Canadá · Grama | tudo | 231 | 630,1 | 47% | 0,76 → 0,78 | +0,3% | +5,5% | +7,1%* | +12,3%* | +17,4%* | 95% → 94% | **6 sem** |
| Jardim Canadá · Plantas diversas | 180 | 231 | 435,6 | 36% | 0,73 → 0,78 | +5,0% | +9,0% | +12,8% | +17,4%* | +17,3%* | 90% → 88% | **8 sem** |
| Jardim Canadá · Produtos de jardim | tudo | 231 | 156,6 | 34% | 0,70 → 0,73 | +2,5% | +5,7%* | +8,5%* | +11,0%* | +11,3% | 91% → 89% | **4 sem** |
| Itabirito · GRAMA ESMERALDA ( ITO) (00013475) | 270 | 232 | 186,5 | 80% | 0,82 → 0,79 | +2,6% | +4,0%* | +4,7% | +9,8%* | +12,6%* | 93% → 93% | **4 sem** |
| Itabirito · GRAMA AMENDOIM UNID. BDJA (147) | 270 | 232 | 94,1 | 151% | 0,90 → 0,91 | +2,6% | +1,7% | +0,1% | +1,3% | +3,0% | 97% → 97% | não piora até 3 meses |
| Itabirito · GRAMA SAO CARLOS (710) | 545 | 232 | 24,9 | 169% | 0,81 → 0,77 | -1,7% | -2,4% | -3,6% | -4,8% | -6,3% | 98% → 98% | não piora até 3 meses |
| Jardim Canadá · GRAMA ESMERALDA ( ITO) (00013475) | tudo | 137 | 7,2 | 234% | 1,17 → 1,70 | +2,2% ⚠ | +4,5% ⚠ | +6,8% ⚠ | +11,6% ⚠ | +20,1%* ⚠ | 99% → 99% | **2 sem** (perde da naïve) |
| Jardim Canadá · CAPIM DOS TEXAS ROXO (00020227) | tudo | 231 | 6,9 | 135% | 0,76 → 0,63 | -0,2% | -0,5% | +1,6% | +1,9% | -2,0% | 98% → 98% | não piora até 3 meses |
| Jardim Canadá · GRAMA PRETA PELO URSO SAQ (00150005) | 270 | 231 | 24,3 | 186% | 1,05 → 1,07 | +1,4% ⚠ | +0,9% ⚠ | +4,4% ⚠ | +7,5% ⚠ | +8,3% ⚠ | 95% → 98% | **2 sem** (perde da naïve) |
| Jardim Canadá · CAPIM DOS TEXAS ROXO (1293) | 180 | 231 | 16,8 | 139% | 0,72 → 0,90 | -0,2% | -1,4% | -2,3% | -2,9% | -3,7% | 93% → 93% | não piora até 3 meses |
| Jardim Canadá · CAPIM DOS TEXAS VERDE (1294) | 90 | 231 | 5,6 | 187% | 1,02 → 1,08 | -7,1% | -5,0% ⚠ | -3,9% | +0,9% ⚠ | +16,4% ⚠ | 95% → 96% | **2 sem** (perde da naïve) |
| Jardim Canadá · GRAMA AMENDOIM UNID. BDJA (147) | tudo | 231 | 450,0 | 80% | 0,79 → 0,78 | -0,6% | +2,5% | +1,2% | +2,6% | +4,4%* | 93% → 93% | **3 meses** |
| Jardim Canadá · GRAMA PRETA PELO DE URSO BDJA (UNID) (166) | 180 | 231 | 38,0 | 197% | 1,12 → 0,98 | +3,7% | +4,6% | +7,0% | +8,5% ⚠ | +13,4% | 97% → 97% | **2 sem** (perde da naïve) |
| Jardim Canadá · GRAMA ZEON (1739) | 545 | 231 | 10,6 | 169% | 0,85 → 0,84 | -0,0% | -0,6% | -0,4% | -0,2% | -0,2% | 97% → 97% | não piora até 3 meses |
| Jardim Canadá · GRAMA ESMERALDA (3) | tudo | 231 | 325,3 | 54% | 0,78 → 0,73 | +1,9% | +4,2%* | +7,1%* | +10,8%* | +12,5%* | 96% → 92% | **4 sem** |
| Jardim Canadá · GRAMA SAO CARLOS (710) | 270 | 231 | 73,1 | 86% | 0,73 → 0,75 | +0,1% | -0,1% | +0,2% | +0,9% | +1,7% | 92% → 92% | não piora até 3 meses |
| **Média (cada série pesa igual)** | | | | | | **+0,8%** | **+1,7%** | **+2,6%** | **+4,3%** | **+6,3%** | | |
| **Média das 8 categorias** | | | | | | **+1,5%** | **+3,0%** | **+3,9%** | **+5,3%** | **+6,6%** | | |

**Duas séries ficaram fora da tabela, porque não há o que avaliar:**
- **Grama Esmeralda (3) de Itabirito:** nenhum dia-alvo foi previsto pelas 13 distâncias, porque a
  série só é treinável em trechos curtos do ano (§3.1).
- **Grama Preta Ana (167) de Jardim Canadá:** só 6 dias em comum, todos sem venda.

**Erro acumulado:** para quem olha o período inteiro da tela, de amanhã até H dias, a média das
categorias fica assim, em % sobre o erro dos primeiros 14 dias:

| Período mostrado | 2 sem | 3 sem | 4 sem | 6 sem | 8 sem | 3 meses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 categorias | — | +0,5% | +1,1% | +2,1% | +2,9% | +4,3% |
| 15 produtos de grama | — | +0,1% | +0,3% | +0,8% | +1,5% | +3,3% |

### 4.1 Leitura

**Não existe um ponto em que a previsão "quebra".**
- O erro sobe aos poucos: nas categorias, ~1,5 ponto a cada semana até a 4ª e depois mais devagar.
- Isso confirma o desenho do ADR-021 §3.1. Lá, com a receita do ADR-020 nas 8 categorias somadas
  e 365 dias, o erro ficava +6% na 4ª semana, +13% na 8ª e +17% na 13ª, sobre a 1ª semana. Aqui a
  curva é mais baixa (+7% no 3º mês, média das categorias). Cada série usa a sua melhor janela, as
  de janela longa (Flores de corte, Itabirito) quase não pioram, e a média dá a mesma importância
  a uma série pequena e a uma grande.

**Onde fica ruim, é por perder o nível atual.**
- Grama, Plantas diversas, Produtos de jardim e Grama Esmeralda de Jardim Canadá mudam de patamar
  ao longo do ano (temporada de grama, fim de ano).
- Com d = 1, a previsão parte da venda recente e segue reta. Quanto mais longe, mais a temporada já
  mudou: de +4–6% na 4ª semana para +11–17% no 3º mês.
- Mesmo assim, essas séries continuam bem melhores que a naïve até 3 meses (erro ÷ naïve de
  0,73–0,78).

**Onde não piora, a previsão boa é o ritmo da semana mais o fator das datas.**
- Flores de corte, Plantas diversas e Produtos de jardim de Itabirito, as gramas pequenas e médias.
- Isso não envelhece. A faixa de 95% acerta igual em 2 semanas e em 3 meses.

**Previsto ÷ vendido cai devagar.** Na mediana das categorias, vai de 95,5% nas 2 primeiras semanas
para 93% no 3º mês. A Grama de Itabirito é a que mais cai: de 93% para 86%. Mais longe, a previsão
tende a ficar um pouco abaixo do vendido.

**Quatro produtos pequenos de Jardim Canadá já perdem da naïve nas 2 primeiras semanas.** São a
Esmeralda (ITO) 00013475, a Preta pelo de urso saco 00150005, a Preta pelo de urso BDJA 166 e o
Capim Verde 1294.
- O "fica ruim a partir de 2 semanas" deles não é efeito da distância.
- São séries de 6 a 38 un./dia, com muitos dias sem venda, e o WAPE das 2 primeiras semanas já
  passa de 180%.
- Para elas, o problema é o modelo diário, não o horizonte. A trilha de comparação com
  Croston/TSB/SBA por SKU (Princípio II) é o lugar para tratar disso.

### 4.2 Quanto tempo no futuro a previsão fica ruim

| Grupo | A partir de |
| --- | --- |
| Grama, Produtos de jardim e Plantas diversas de Jardim Canadá; Grama Esmeralda das 2 lojas (3 de JC e ITO 00013475 de Itabirito) | **4 a 8 semanas** (Produtos de jardim e Esmeraldas na 4ª, Grama na 6ª, Plantas diversas na 8ª) |
| Grama de Itabirito; Grama Amendoim de Jardim Canadá | **3 meses** (+4%, significativo, mas pequeno) |
| Flores de corte das 2 lojas; Plantas diversas e Produtos de jardim de Itabirito; Amendoim de Itabirito, São Carlos, Zeon, Capim Roxo | **não piora até 3 meses** |
| Esmeralda (ITO), Preta pelo de urso saco, Preta pelo de urso BDJA e Capim Verde de Jardim Canadá | já perdem da naïve nas 2 primeiras semanas (série esparsa, §4.1) |

**Para a compra semanal, a previsão é confiável até 4 semanas em todas as séries grandes.** Daí até
3 meses, ela serve como tendência: ainda erra menos que repetir a última semana. Nas séries de
temporada de Jardim Canadá, porém, ela erra 10–17% a mais que a previsão das 2 primeiras semanas.

## 5. Por que é assim

- **Janela × mudança de nível:** a escolha da janela é uma troca entre viés e variância. A janela
  curta acompanha mudança recente, mas estima com pouco dado; a longa estima melhor, mas mistura
  regimes antigos (Pesaran & Timmermann, 2007).
- **Por que a janela longa não atrapalha aqui:** nas séries grandes, o d = 1 já cuida da mudança de
  nível, então o custo da janela longa é pequeno. Nas séries de data comemorativa e nas esparsas,
  falta dado, e a janela longa ganha.
- **Por que o horizonte pesa diferente em cada série:** num modelo com d = 1, a variância do erro
  cresce com o horizonte e a previsão pontual fica no último nível (Hyndman & Athanasopoulos, 2021,
  cap. 9). Isso não pesa onde a série não muda de nível (Flores de corte, Itabirito) e pesa onde
  muda (temporada de grama em Jardim Canadá).

## 6. O que fazer com isso

Adotada a opção 1 (ADR-022). Caminhos para o treino de produção, que entram no Neon via treino real
(`treinar_previsoes`), com confirmação na hora:

1. **Só mudar a janela (sem código): `FORECAST_SERVICE_WINDOW_DAYS = 545`.**
   - É a melhor janela única: −1,9% nas 23 séries e nas categorias.
   - Não piora de forma relevante nenhuma categoria; a pior é Grama de Jardim Canadá, com +0,3%.
   - Nos produtos pequenos, piora alguns: Capim Verde +4,8%, Capim Roxo 1293 e Preta pelo de urso
     BDJA +3,4%, Esmeralda (3) de Itabirito +17%.
   - Custo: ajustes um pouco mais lentos (50% mais dias por ajuste).
2. **Janela por série, escolhida a cada treino pelo erro recente,** como o d (ADR-020).
   - Ganho: −6,1% nas 23 séries, −8,8% nos produtos.
   - Pede código (a janela vira candidata, como `FORECAST_SERVICE_D_CANDIDATES`).
   - Leva cerca de 6 vezes o tempo de treino de hoje: 6 janelas × 2 d.
   - Nas categorias, ganha menos que fixar 545.
3. **Misto:** categorias com 545 dias fixos e produtos de grama com a janela escolhida a cada
   treino. É o que mais ganha em cada grupo (−1,9% e −8,8%), com custo extra só nos produtos.
   Pede código.

O `melhor_treino.json` guarda a melhor janela *ex post* de cada série, com o d e a ordem do último
corte. Ele serve para conferir o treino real, não para substituí-lo: o último corte é 21/02/2026, sem
o walk-forward de 56 origens nem a previsão a partir de 01/03/2026.

**Horizonte na tela:** os números não pedem mudar o padrão de 2 semanas nem as opções do ADR-021.
Se um aviso for colocado na tela, o ponto é a 4ª semana: é onde as séries de temporada de Jardim
Canadá começam a piorar de forma significativa.

## 7. Limitações

- **Um ano de avaliação** (mar/2025–fev/2026) e um só ciclo de temporada. Em especial, a janela de
  545 dias e o histórico inteiro só se diferenciam no fim do período: no 1º corte, o histórico
  inteiro tinha ~425 dias.
- **"Melhor" é *ex post*.** O ganho real de escolher a janela é o da coluna da escolha automática.
- **Muitos testes.** Na Tabela 2 há 5 testes por série, sem correção. Os casos de Jardim Canadá são
  consistentes (o erro sobe a cada coluna), mas um asterisco isolado pode ser acaso.
- **Simplificações em relação à produção:**
  - A ordem é escolhida de novo a cada 26 cortes, não a cada treino.
  - O d sai dos cortes semanais anteriores, não das 56 origens do walk-forward.
- **Base local** com venda até 28/02/2026, a mesma carga do Neon.

## Referências

- Diebold, F. X.; Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business &
  Economic Statistics*, 13(3), 253–263.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of
  Statistics*, 6(2), 65–70.
- Hyndman, R. J.; Athanasopoulos, G. (2021). *Forecasting: Principles and Practice*, 3ª ed. OTexts,
  §5.10 (validação cruzada de séries temporais) e cap. 9 (ARIMA).
- Inoue, A.; Jin, L.; Rossi, B. (2017). Rolling window selection for out-of-sample forecasting with
  time-varying parameters. *Journal of Econometrics*, 196(1), 55–67.
- Lazarus, E.; Lewis, D. J.; Stock, J. H.; Watson, M. W. (2018). HAR inference: recommendations for
  practice. *Journal of Business & Economic Statistics*, 36(4), 541–559.
- Pesaran, M. H.; Timmermann, A. (2007). Selection of estimation window in the presence of breaks.
  *Journal of Econometrics*, 137(1), 134–161.
