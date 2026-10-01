# ADR-011: Escopo — previsão de demanda diária, sem camada de reposição (L3)

**Status**: Aceito (2026-08-30) · atualizado em 2026-09-21
**Autores**: Felipe Gurgel Araújo, Daniel Nunes da Silva
**Relacionado**: [ADR-009](ADR-009-granularidade-diaria-e-reposicao.md) (revisa),
[ADR-010](ADR-010-exogenas-nominais-fora-do-l1.md),
`docs/prediction/01-pre_processing.md` §5, `docs/prediction/00-eda_report.md` §3.10–§3.11

---

## Contexto

O [ADR-009](ADR-009-granularidade-diaria-e-reposicao.md) definiu um pipeline hierárquico
de três camadas — **L1** (SARIMAX da demanda agregada por `unidade × categoria`),
**L2** (desagregação para SKU) e **L3** (política de reposição perecível-consciente com
`shelf_life_dias`, estoque de segurança e simulação de perda/ruptura) — cujo entregável
era a **quantidade sugerida de reposição por produto por dia**.

No levantamento com a entidade parceira (Floricultura Verde Perto), três pontos foram
definidos:

1. **Unidades.** A rede tem **2 unidades operacionais** — Jardim Canadá e Itabirito. O
   campo `empresa` traz 3 pessoas jurídicas (CNPJ) porque as vendas do Garden Center
   pertencem a Jardim Canadá. Cada unidade é modelada **separadamente**.
2. **Categorias.** O catálogo se organiza em grupos de produto: **Grama** (grama de
   plantio); **Flores de corte** (as que compõem arranjos e buquês); **Plantas diversas**
   (todas as plantas, exceto flores de corte e árvores); e os insumos e acessórios de
   jardinagem.
3. **Reposição.** A loja **decide sozinha quando e quanto comprar** para o estoque. O que
   agrega valor é saber **quanto vai vender por dia**; a conversão disso em ordem de
   compra (e, portanto, `shelf_life_dias`, cobertura-alvo, risco de murcha) **não faz
   parte do que se espera do sistema**.

## Decisão

### 1. Entregável

O sistema entrega **previsão de demanda diária** por `unidade` (L1) e, por desagregação em
cascata, por `categoria` e por SKU (L2 — ver §4), com horizonte de **14 dias** e intervalo
de confiança. **A camada L3 (política de reposição) sai de escopo.**

### 2. Unidades

`empresa → unidade` é N:1 e definitivo (`taxonomy/unidades.py`):
`FLORICULTURA VERDE PERTO CANADÁ LTDA → Jardim Canadá`,
`GARDEN CENTER VERDE PERTO LTDA → Jardim Canadá`,
`VERDE PERTO JARDINAGEM LTDA → Itabirito`.

A série diária de Jardim Canadá é a soma das vendas dos dois CNPJs.

### 3. Categorias — 3 de demanda + 1 rótulo de não-produto

| `categoria` (nível L1) | Origem (a partir da `categoria_fina` detalhada) |
| --- | --- |
| **Grama** | grama de plantio (esmeralda, são carlos, amendoim, batatais, coreana) |
| **Flores de corte** | as que compõem arranjos e buquês, e os próprios arranjos e buquês (rosa em cabo, alstroemeria, maço de hastes) |
| **Produtos de jardim** | plantas (muda e forração, planta em vaso, arbusto/planta formada, hortaliça e erva), insumos e acessórios (substrato e adubo, vasos, seixos, ferramentas) e `Outros` |
| `Servico e taxa` | frete, taxa, mão de obra — **não é produto**; excluído da série de demanda L1 |

- São **2 modelos L1** — uma série por unidade (ver §4: separar por categoria não reduz o
  erro de previsão). `categoria` é obtida por desagregação da unidade; `Servico e taxa`
  não entra na série de demanda em nenhum nível.
- A `categoria_fina` (~10 rótulos, produzida pelas regras de `taxonomy/categorias.py`)
  **continua no CSV da Etapa 3** — serve à EDA e à desagregação L2 (que precisa de um
  agrupamento mais fino do que 3 baldes), e preserva a opção de subdividir depois sem
  reprocessar os XLSX.
- **Grupos do cliente na apresentação.** `Plantas diversas` (`Hortalica e erva`, `Muda e
  forracao`, `Planta em vaso`, `Arbusto e planta formada`, `Outros`) e `Insumos e
  acessórios` (`Substrato e adubo`, `Insumo e acessorio`) são funções puras da
  `categoria_fina` (`GRUPO_PRODUTO` em `taxonomy/categorias.py`). **Não são séries L1**: a
  previsão de um grupo é a soma da previsão dos SKUs dele (L2). Árvores não têm regra
  própria (a lista do grupo no sistema do cliente não está disponível) e ficam em
  `Plantas diversas`.

**Por que não abrir `Produtos de jardim` em `Plantas diversas` e `Insumos e acessórios` na
desagregação.** O teste abaixo foi rodado quando `Produtos de jardim` ainda era candidata a
série L1 própria; a conclusão (não abrir) vale igual agora que ela mesma é obtida por
desagregação da unidade (§4) — o teste mede se granular mais um nível ajuda, independente
de onde a previsão do nível de cima vem. A EDA de granularidade (`00-eda_report.md` §3.10)
comparou, em walk-forward de 26 janelas de 14 dias, o modelo direto de cada grupo contra a
repartição da previsão de `Produtos de jardim` pela participação móvel — que é o que a L2
já faz sem modelo adicional. As duas séries são viáveis (≥ 650 dias com venda, 4% de dias
úteis zerados), mas:

| MASE (SARIMAX) | Jardim Canadá — direto × repartido | Itabirito — direto × repartido |
| --- | --- | --- |
| Plantas diversas (41% do volume) | 0,551 × 0,526 | 0,939 × 0,945 |
| Insumos e acessórios (10% do volume) | 0,618 × 0,697 | 0,868 × 0,924 |
| Produtos de jardim: direto × soma dos dois modelos diretos | 0,550 × 0,551 | 0,954 × 0,924 |

O modelo direto não ganha em `Plantas diversas`; em `Insumos e acessórios` ganha em
Jardim Canadá, mas o ganho não se repete em Itabirito com o segundo previsor
(Holt-Winters: 0,887 × 0,876); e a soma dos dois modelos diretos iguala o total de
`Produtos de jardim` em Jardim Canadá e o melhora em 3% em Itabirito, abaixo do limite de
5%. A regra foi fixada antes dos resultados (abrir só se o modelo direto ganhar ≥ 5% de
MASE em cada grupo e unidade, com cada um dos dois previsores) e não foi atendida. Abrir o
grupo acrescentaria 2 modelos L1 (8 no total), cada um com sua validação, sem ganho
consistente de acurácia.

### 4. Granularidade do L1 — `unidade`, não `unidade × categoria`

**Decisão:** o L1 ajusta um SARIMAX por **unidade** — 2 séries (Jardim Canadá, Itabirito;
cada uma soma todas as categorias de produto). `categoria` deixa de ser série L1 própria e
passa a ser nível de desagregação, como o SKU já era de `categoria`: a L2 passa a ter
**dois passos em cascata** — `unidade → categoria` e `categoria → SKU` — pelo mesmo método
(participação móvel × perfil de dia-da-semana do nível; ver `01-pre_processing.md` §5.2).

O teste de separação (`eda_separacao.py`, mesmo desenho do teste acima: walk-forward de 26
janelas de 14 dias, dois modelos — SARIMAX e Holt-Winters —, regra de ganho mínimo de 5%
fixada antes de rodar) mostrou:

- **Separar por unidade tem apoio.** Modelar Itabirito direto ganha 17% de MASE com
  SARIMAX e 11% com Holt-Winters sobre repartir a previsão do total da rede — as duas
  unidades têm tendências opostas (Jardim Canadá em queda moderada, Itabirito em alta
  forte; `00-eda_report.md` §3.5) que um único modelo do total não capturaria. A soma dos
  dois modelos por unidade melhora o total da rede em 22% com SARIMAX e empata com
  Holt-Winters.
- **Separar por categoria não melhora.** Nenhuma das 6 séries `unidade × categoria` ganha
  o mínimo de 5% ao ser modelada direto em vez de obtida por repartição da unidade
  (ganhos de −7% a +9% com SARIMAX, de −17% a +4% com Holt-Winters); a soma das 3
  categorias por unidade fica a menos de 5% do modelo da própria unidade; nas 7 janelas de
  teste com data comemorativa, o resultado não muda.

Prever 2 séries com acurácia equivalente a 6 significa 4 modelos L1 a menos para ajustar,
validar (walk-forward CV, diagnóstico de resíduos — constituição, Princípio III) e
monitorar no retreino semanal, sem perda de acerto.

**O que isso muda na prática:**

- A análise por `unidade × categoria` (`eda_series.py`, `00-eda_report.md` §3) não perde
  valor — vira o insumo do passo de desagregação `unidade → categoria`: o perfil de
  dia-da-semana e o efeito de datas comemorativas *da categoria* (não mais parâmetros de
  um SARIMAX próprio) são exatamente o que esse passo precisa.
- **A desagregação por categoria precisa do efeito de data *da categoria*, não só da
  proporção histórica.** A série agregada por unidade dilui sinais de categorias pequenas:
  em Jardim Canadá, o agregado da unidade **cai** 0,66× no Dia das Mães, mas isso esconde
  Flores de corte **disparando** 2,14× nessa data — só não aparece no agregado porque
  Flores de corte é 1,4% do volume da unidade e Grama/Produtos de jardim (que caem no Dia
  das Mães) dominam a média. Repartir a previsão da unidade só pela proporção histórica
  perderia esse pico; a desagregação usa também o índice de data-por-categoria (mesmo
  bloco `4b_datas_comemorativas` de `eda_series.py`, por par).
- Ver [ADR-009](ADR-009-granularidade-diaria-e-reposicao.md) (arquitetura revisada) e
  `01-pre_processing.md` §5.2 (a cascata de desagregação completa, com os gráficos
  gerados por unidade e por par).

### 5. `shelf_life_dias` removido

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
4. **Categoria e grupos do cliente chegam por desagregação, não por modelo próprio.**
   `Grama` e `Flores de corte` diferem em dinâmica (efeito de datas comemorativas de sinal
   oposto, perfil semanal distinto) — mas essa diferença é descritiva, não um ganho de
   acurácia em modelá-las direto: o teste de separação (`00-eda_report.md` §3.11, §4 acima)
   mostra que nenhuma categoria bate o mínimo de 5% de MASE sobre a repartição da unidade.
   O L1 fica em `unidade` (2 séries); categoria, grupo do cliente e SKU chegam por
   desagregação em cascata, sem custo de modelo adicional. As ~10 categorias detalhadas
   (`categoria_fina`) seguem como artefato interno de desagregação, não a unidade de
   modelagem.

## Consequências

**Aplicado (pré-processamento — `training_scripts/preprocessing/`):**

- `taxonomy/unidades.py` — `GARDEN CENTER VERDE PERTO LTDA` mapeia para `Jardim Canadá`
  (2 unidades).
- `taxonomy/categorias.py` — `SHELF_LIFE_DIAS`/`shelf_life()` removidos; `CATEGORIA_L1`
  (colapso fina → 3) e `map_categoria_l1()`; `GRUPO_PRODUTO` e `map_grupo()` (grupos do
  cliente); regra de `Flor de corte e arranjo` restrita ao que compõe arranjos e buquês
  (planta envasada como `GERBERA PT 15` ou `CRISANTEMO VB` segue a cascata).
- `map_taxonomy.py` — emite `categoria` (nível de desagregação) **e** `categoria_fina`;
  CSV da Etapa 3 tem **12 colunas**; diagnóstico reporta volume por L1 (unidade), por
  categoria/fina/grupo do cliente, e cobertura ≥ 180 d por unidade e por par
  unidade×categoria.
- `training_scripts/eda/eda_grupos.py` e `eda_separacao.py` — testes de granularidade
  (viabilidade, diferenças entre grupos, modelo direto × repartição) que sustentam a
  decisão de categorias e de granularidade do L1 (§4).
- `training_scripts/eda/eda_series_unidade.py` — bateria de diagnóstico (densidade,
  distribuição, sazonalidade, tendência, estacionariedade, autocorrelação, outliers) das
  2 séries que o L1 de fato ajusta agora; `eda_series.py` (as 6 séries `unidade ×
  categoria`) e `_common.py` (`serie_unidade()`) ajustados para refletir que `categoria` é
  desagregação, não série L1.
- `docs/prediction/01-pre_processing.md` §1 e §5, `docs/prediction/00-eda_report.md` e
  `docs/prediction/ADR-009` §2/§3 — arquitetura L1/L2 revisada para `unidade` + cascata de
  desagregação.
- `.specify/memory/constitution.md` — Princípio II e Quality Gates atualizados para a
  granularidade `unidade` (v3.0.0).
- `docs/prediction/ADR-009` §8 — marcado como revisado por este ADR.

**Pendente (propagação — fora do pré-processamento, exige revisão dedicada):**

- `SPECS.md`, `specs/001-sistema-previsao-vendas/{spec,plan,tasks}.md` — remover a fase
  de política de reposição; ajustar user stories e critérios de sucesso; propagar
  `unidade × categoria` → `unidade` nos trechos ainda não revisados (schemas JSON de
  exemplo, diagramas de pipeline).
- `ia-predictor/openapi.yaml` — remover `/api/v1/replenishment/{produto_cod}` e `/batch`,
  o schema `ReplenishmentRecommendation`; refletir a granularidade `unidade` do L1 nos
  contratos de status de modelo.
- `docs/prediction/plano_experimentos_modelagem.md` — remover a simulação de reposição da
  trilha de avaliação; manter MASE/RMSSE/resíduos; ajustar as referências a
  `unidade × categoria` como grão do L1 baseline (Fase 1) para `unidade`.
- **Dashboard** — apresentar previsão por grupo do cliente (soma dos SKUs do grupo);
  o protótipo em `app-react/` usa dados fictícios de 2 unidades.

Até essa propagação, os documentos acima ainda descrevem L3 e/ou `unidade × categoria`
como grão do L1 — a fonte da verdade do escopo e da granularidade é **este ADR**.
