# ADR-011: Escopo — previsão de demanda diária, sem camada de reposição (L3)

**Status**: Aceito (2026-08-30)
**Autores**: Felipe Gurgel Araújo, Daniel Nunes da Silva
**Relacionado**: [ADR-009](ADR-009-granularidade-diaria-e-reposicao.md) (revisa),
[ADR-010](ADR-010-exogenas-nominais-fora-do-l1.md),
`docs/prediction/01-pre_processing.md` §5

---

## Contexto

O [ADR-009](ADR-009-granularidade-diaria-e-reposicao.md) definiu um pipeline hierárquico
de três camadas — **L1** (SARIMAX da demanda agregada por `unidade × categoria`),
**L2** (desagregação para SKU) e **L3** (política de reposição perecível-consciente com
`shelf_life_dias`, estoque de segurança e simulação de perda/ruptura) — cujo entregável
era a **quantidade sugerida de reposição por produto por dia**.

Na reunião de levantamento com a entidade parceira (Floricultura Verde Perto) em
2026-08-30, três pontos foram definidos:

1. **Unidades.** As 3 pessoas jurídicas (CNPJ) que aparecem no campo `empresa` são as 3
   lojas. Devem ser modeladas **separadamente**.
2. **Categorias.** A parceira organiza o negócio em **grama de plantio × "plantas de
   corte"**. Não há, para a gestão dela, um recorte mais fino do restante do catálogo.
3. **Reposição.** A loja **decide sozinha quando e quanto comprar** para o estoque. O que
   agrega valor é saber **quanto vai vender por dia**; a conversão disso em ordem de
   compra (e, portanto, `shelf_life_dias`, cobertura-alvo, risco de murcha) **não faz
   parte do que se espera do sistema**.

## Decisão

### 1. Entregável

O sistema entrega **previsão de demanda diária** por `unidade × categoria` (L1) e, por
desagregação, por SKU (L2), com horizonte de **14 dias** e intervalo de confiança. **A
camada L3 (política de reposição) sai de escopo.**

### 2. Unidades

`empresa → unidade` é 1:1 e definitivo (`taxonomy/unidades.py`):
`FLORICULTURA VERDE PERTO CANADÁ LTDA → Jardim Canadá`,
`VERDE PERTO JARDINAGEM LTDA → Itabirito`,
`GARDEN CENTER VERDE PERTO LTDA → Garden Center`.

### 3. Categorias — 3 de demanda + 1 rótulo de não-produto

| `categoria` (nível L1) | Origem (a partir da `categoria_fina` detalhada) |
| --- | --- |
| **Grama** | grama de plantio (esmeralda, são carlos, amendoim, batatais, coreana) |
| **Plantas de corte** | flor de corte e arranjos montados (rosa em cabo, alstroemeria, maço de hastes) |
| **Produtos de jardim** | todo o restante: muda e forração, planta em vaso, arbusto/planta formada, substrato e adubo, insumo e acessório, hortaliça e erva, e `Outros` |
| `Servico e taxa` | frete, taxa, mão de obra — **não é produto**; excluído da série de demanda L1 |

- São **9 modelos L1** (3 categorias × 3 lojas). `Servico e taxa` não vira modelo.
- A `categoria_fina` (~10 rótulos, produzida pelas regras de `taxonomy/categorias.py`)
  **continua no CSV da Etapa 3** — serve à EDA e à desagregação L2 (que precisa de um
  agrupamento mais fino do que 3 baldes), e preserva a opção de subdividir depois sem
  reprocessar os XLSX.

### 4. `shelf_life_dias` removido

Sem L3, não há uso para a validade por categoria. `SHELF_LIFE_DIAS` e a função
`shelf_life()` foram **removidos** de `taxonomy/categorias.py`; o CSV da Etapa 3 nunca
carregou a coluna. O levantamento de validade real com a parceira (antigo `tasks.md`
T000c) deixa de ser necessário.

## Justificativa

1. **Alinhamento com o pedido da parceira.** O valor prático é a previsão; a decisão de
   compra é da loja e envolve fatores fora do dado transacional (negociação com
   fornecedor, espaço físico, datas comemorativas planejadas à mão).
2. **Menos suposições frágeis.** L3 dependia de `shelf_life_dias` estimado por nós, de
   `estoque_atual` (que a floricultura não tem em tempo real) e de uma regra ingênua de
   comparação — três fontes de erro que não seriam validáveis no horizonte do TCC.
3. **Foco metodológico.** O núcleo acadêmico (SARIMAX hierárquico × demanda intermitente
   por SKU, walk-forward CV, MASE/RMSSE, diagnóstico de resíduos) permanece intacto e
   fica mais nítido sem a camada de política de estoque por cima.
4. **3 categorias refletem a visão de negócio real** da parceira. As ~10 categorias
   detalhadas viram um artefato interno (`categoria_fina`) para análise, não a unidade de
   modelagem.

## Consequências

**Já aplicado (pré-processamento — `training_scripts/preprocessing/`):**

- `taxonomy/unidades.py` — docstring atualizada (mapa confirmado, sem "a validar").
- `taxonomy/categorias.py` — `SHELF_LIFE_DIAS`/`shelf_life()` removidos; adicionados
  `CATEGORIA_L1` (colapso fina → 3) e `map_categoria_l1()`.
- `map_taxonomy.py` — emite `categoria` (L1) **e** `categoria_fina`; CSV da Etapa 3 passa
  a ter **12 colunas**; diagnóstico reporta volume por L1 e por fina, e cobertura ≥ 180 d
  dos 9 pares.
- `docs/prediction/01-pre_processing.md` §1 e §5 — reescritos.
- `docs/prediction/ADR-009` §8 — marcado como revisado por este ADR.

**Pendente (propagação — fora do pré-processamento, exige revisão dedicada):**

- `CLAUDE.md` — descrição do projeto, "Pipeline Hierárquico" (remover L3), tabela de
  endpoints (`/replenishment/*`), variáveis de ambiente (`SAFETY_STOCK_DAYS`,
  `SHELF_LIFE_DEFAULT_DAYS`), tabelas SQLite (`replenishment_cache`).
- `.specify/memory/constitution.md` — Princípio III (simulação de perda/ruptura) e
  referências a reposição.
- `SPECS.md`, `specs/001-sistema-previsao-estoque/{spec,plan,tasks}.md` — remover a fase
  de política de reposição; ajustar user stories e critérios de sucesso.
- `ia-predictor/openapi.yaml` — remover `/api/v1/replenishment/{produto_cod}` e `/batch`,
  o schema `ReplenishmentRecommendation`.
- `docs/prediction/ADR-009` — reescrever as seções de L3 (ou marcar L3 como histórico).
- `docs/prediction/plano_experimentos_modelagem.md` — remover a simulação de reposição da
  trilha de avaliação; manter MASE/RMSSE/resíduos.

Até essa propagação, os documentos acima ainda descrevem L3 — a fonte da verdade do
escopo é **este ADR**.
