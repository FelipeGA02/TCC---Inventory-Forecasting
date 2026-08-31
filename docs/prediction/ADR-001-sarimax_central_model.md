# ADR-001: SARIMAX como Modelo Central de Previsão

**Status**: Aceito — **revisado em 2026-08-30** (ver seção "Revisão" ao final e
[ADR-009](ADR-009-granularidade-diaria-e-reposicao.md))  
**Data**: 2026-07-28  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O sistema precisa prever a demanda mensal de produtos de floricultura com histórico
de 26 meses (Jan/2024–Fev/2026). Os dados apresentam sazonalidade marcada por datas
comemorativas (Dia das Mães, Natal) e alta perecibilidade dos produtos.

Candidatos avaliados:
- SARIMAX (Seasonal ARIMA with eXogenous inputs)
- LSTM / redes neurais recorrentes
- XGBoost / LightGBM
- Prophet (Meta)

## Decisão

**SARIMAX** é o modelo central de previsão para todos os produtos modelados.

## Justificativa

1. **Volume de dados**: com 26 observações mensais por produto, modelos de ML tendem
   ao sobreajuste. A competição M4 (Makridakis et al., 2020) demonstrou empiricamente
   que modelos ARIMA superam ML em séries com menos de 50 observações por sazonalidade.

2. **Interpretabilidade**: coeficientes SARIMAX são interpretáveis e auditáveis —
   requisito implícito para uso em decisões de compra por usuários não técnicos.

3. **Variáveis exógenas**: o "X" do SARIMAX permite incorporar variáveis de mercado
   (volume total, taxa de desconto) e calendário (alta temporada), capturando influências
   externas sobre a demanda de forma estatisticamente fundamentada.

4. **Referência de domínio**: Pavlyshenko (2019) demonstrou MAPE < 5% com SARIMAX
   em varejo de alimentos perecíveis — domínio análogo à floricultura.

## Consequências

- Grid search de 36 combinações de ordens (p,q ∈ 0..2; P,Q ∈ 0..1) por produto,
  com tempo estimado de ~3 min/produto.
- Random Forest é usado apenas como pré-processamento para ponderação de variáveis
  exógenas (MDI), não como modelo de previsão.
- Produtos com demanda irregular (CV > 1,5) terão `status = "low_confidence"` —
  o modelo ainda é treinado mas o aviso é exibido no dashboard.
- Modelos de ML podem ser introduzidos no futuro mediante evidência de superioridade
  no dataset específico (ver Princípio II da constituição).

---

## Revisão — 2026-08-30 (escopo: mensal → diário)

O entregável mudou de previsão **mensal por produto** para **recomendação de reposição
diária** (produtos perecíveis). Ver [ADR-009](ADR-009-granularidade-diaria-e-reposicao.md).
Impacto nesta decisão:

- **SARIMAX continua central**, mas na **camada agregada L1**: uma série **diária** por
  `unidade × categoria` (densa), com sazonalidade semanal (`m=7`). Os argumentos de
  volume de dados, interpretabilidade e uso de exógenas seguem válidos — na verdade
  reforçados, porque a série agregada tem ~790 pontos diários em vez de ~26 mensais.
- O **nível de SKU** deixa de ser modelado com SARIMAX: a série diária por SKU é >90%
  zeros e o SARIMAX é inaplicável. O SKU é atendido por **desagregação proporcional**
  (L2) e a política de reposição (L3).
- Modelos de **demanda intermitente** (Croston/TSB/SBA) passam a ser **permitidos** no
  nível de SKU como **trilha de comparação** formal (contribuição acadêmica ii),
  substituindo a antiga comparação "mensal × diária". A porta para ML segue a mesma:
  só com evidência empírica de superioridade sob o mesmo protocolo de validação.
- O `m=12` do grid de ordens vira `m=7`; a comparação "produto 147 SMAPE 22,5%" etc.
  do protótipo mensal fica como registro histórico, não como referência de qualidade
  (a métrica primária agora é MASE — ver constituição v2.0.0).
