# ADR-001: SARIMAX como Modelo Central de Previsão

**Status**: Aceito  
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
