# ADR-010: `pagamento` e `vendedor` fora das exógenas do modelo L1

**Status**: Aceito (2026-08-30)
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo
**Relacionado**: [ADR-009](ADR-009-granularidade-diaria-e-reposicao.md),
`docs/prediction/01-pre_processing.md` §4–5

---

## Contexto

O pré-processamento legado (Etapa 3, `discretize_fields.py`) convertia `pagamento` (13
valores), `empresa` (3) e `vendedor` (38) em 51 colunas one-hot, pensadas como exógenas
do SARIMAX. Com a revisão de escopo para modelagem **hierárquica diária** (ADR-009), o
modelo L1 é um SARIMAX por `unidade × categoria` sobre a série **diária agregada**.

## Decisão

- **`empresa`** é mantida — vira a chave de agrupamento `unidade` da camada L1 (um modelo
  por unidade × categoria), **não** uma exógena.
- **`pagamento`** e **`vendedor`** são removidos na Etapa 2 (`reduce_schema.py`) e **não**
  entram como exógenas em nenhuma camada.
- **A antiga Etapa 3 (`discretize_fields.py`, one-hot de pagamento/empresa/vendedor) foi
  removida** do repositório; o código está no histórico do git se precisar como
  referência. No lugar entra uma nova Etapa 3 (`map_taxonomy.py`) que deriva `unidade` e
  `categoria` — outro propósito.
- As exógenas do L1 são exclusivamente de **calendário**: dia-da-semana (dummies/Fourier),
  feriado nacional/municipal, véspera, "dias até data comemorativa".

## Justificativa

1. **Nível de agregação errado.** `pagamento` e `vendedor` descrevem uma *transação*. O
   alvo do L1 é a soma diária de uma categoria. `pagamento_PIX=1` não tem significado
   numa linha que representa "quarta-feira, 63 unidades" — no máximo viraria uma feature
   contínua derivada (`% no PIX no dia`), que é outra coisa.
2. **Vazamento (leakage).** Uma exógena só serve se seu valor for conhecido para os dias
   futuros previstos. O calendário é conhecido; o mix de forma de pagamento e a
   distribuição de vendas por vendedor de amanhã, não. E forma de pagamento é
   *consequência* da venda, não driver de demanda.
3. **Orçamento de parâmetros.** Mesmo com a série diária agregada (~790 pontos), somar 49
   dummies de `pagamento`+`vendedor` sobre exógenas de calendário e termos ARMA infla o
   modelo sem ganho — e o walk-forward com origem móvel e horizonte de 14 dias trabalha
   com janelas ainda menores.
4. **Redundância de `empresa`.** "Uma unidade vende mais que outra" já é capturado por
   treinar um modelo separado por unidade — uma dummy de `empresa` dentro do modelo de
   uma unidade é constante (variância zero) ou colinear com o intercepto.
5. **Codificação.** Se algum desses campos voltar (como feature derivada mensal/semanal),
   a codificação correta é one-hot com baseline omitido — nunca código inteiro
   sequencial, que impõe ordem e espaçamento artificiais a categorias nominais.

## Consequências

- Etapa 2 passa de 11 para **9 colunas**: `emissao, empresa, produto_cod, qtdade,
  vl_unit, vl_total, vl_desconto, tot_liq, total_liquido_doc`.
- `discretize_fields.py`, `FIELDS_TO_DISCRETIZE`, `DISCRETIZED_CSV`, `ENCODINGS_FILE`
  removidos de `constants.py` / do pacote `preprocessing`.
- `contas_a_receber_discretizado.csv` e `encodings.py` não são mais gerados.
- A pergunta "vendedor/pagamento têm sinal de demanda?" fica para a EDA (triagem RF MDI
  sobre o CSV da Etapa 1). Se algo aparecer, entra como **feature derivada agregada**
  (ex.: `n_vendedores_ativos_no_dia`), não como dummy crua — decisão da Fase 3 do
  [plano de experimentos](plano_experimentos_modelagem.md).
