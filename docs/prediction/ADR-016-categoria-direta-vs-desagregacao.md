# ADR-016 — SARIMAX direto na categoria vence a desagregação do L1

**Status:** aceito pelo [ADR-017](ADR-017-previsao-por-categoria-e-grama.md) (2026-10-26) · **Data:** 2026-10-25 · **Contesta:** Princípio II da constituição (v3.1.0)
**Afeta:** `.specify/memory/constitution.md` (Princípio II), `CLAUDE.md` (Regra Inviolável nº 2,
seção L2), `backend/domain/disaggregation/`

> **Aceito, com outra forma (ADR-017).** A categoria passou a ter SARIMAX próprio, como este
> ADR propõe, mas o sistema foi além do §3: saíram também o L1 por unidade (o total da loja
> é a soma das categorias) e a desagregação para SKU — os produtos de grama têm modelo
> próprio, e os de outras categorias não são previstos. A receita é `d = 0` com janela de
> 365 dias (§5, pendência resolvida no `trainer.py`). A emenda do Princípio II continua
> pendente (`/speckit-constitution`).

---

## 1. O problema: a norma se apoia numa citação errada e num teste fraco

A constituição (Princípio II) e o `CLAUDE.md` (Regra Inviolável nº 2) proibiam modelo
próprio por categoria citando **"o teste de separação (ADR-011 §4)"**.

Essa citação está errada por dois motivos:

1. **ADR-011 §4 é "`shelf_life_dias` removido"** — não há teste de separação em nenhuma
   das 4 seções daquele ADR. Confirmado recuperando o arquivo do histórico
   (`git show 8e5aa6e:docs/prediction/ADR-011-escopo-previsao-sem-reposicao.md`; o ADR foi
   apagado do disco nos commits `c761312` e `4215042`).
2. **O teste existe, mas em outro lugar e com outro protocolo**: é a EDA 4, em
   `training_scripts/eda/eda_separacao.py` — "Separar por unidade e por categoria melhora
   a previsão?".

A EDA 4 é um teste de triagem, não de decisão:

| | EDA 4 (base da norma) | `categoria_direta_vs_desagregacao.py` |
| --- | --- | --- |
| Rodadas de validação | 26 janelas de 14 dias | **351 origens, passo de 1 dia** |
| Categorias | 3 (antes da taxonomia atual) | **4** |
| Alvo | base transacional da EDA | **fluxo diário (ADR-013)** |
| Métrica de decisão | MASE com `GANHO_MINIMO` | MASE, erro relativo à naïve, cobertura e largura do IC 95% |
| Previsores | SARIMAX e ETS | SARIMAX (ordem por AIC por série) e 3 formas de rateio |

Rodar o experimento forte era o passo que faltava. Ele já estava implementado e seus
resultados estão no disco — mas sem nenhum documento que os registrasse, e apontando para
o lado oposto da norma.

## 2. Evidência

Protocolo idêntico nos dois métodos: fluxo diário (sem `Servico e taxa`, sem encomendas
acima de 2.000 unidades no documento — ADR-013), janela deslizante de 425 dias, primeira
origem 2025-03-02, 351 origens com passo de 1 dia, h = 14. Métricas nos **dias de loja
aberta**, horizontes 1 a 14 agregados. `desag_8sem` = previsão do L1 da loja × participação
da categoria nas últimas 8 semanas; `direto` = SARIMAX na série da categoria (sem `log1p`,
d = 1, D = 0, m = 7, exógenas de calendário, ordem por AIC antes da 1ª origem).

| Unidade · categoria | Método | Erro rel. naïve | MASE | Cobertura IC95 | Largura IC95 (× venda média do dia) |
| --- | --- | --- | --- | --- | --- |
| ITA · Grama | desag_8sem | **0,798** | 0,840 | 78,1% | 1,80× |
| ITA · Grama | direto | 0,803 | 0,845 | **94,3%** | 3,39× |
| ITA · Plantas diversas | desag_8sem | 0,763 | 0,894 | 93,9% | 1,88× |
| ITA · Plantas diversas | direto | **0,736** | 0,862 | 94,8% | 1,95× |
| ITA · Produtos de jardim | desag_8sem | 0,771 | 1,023 | 91,8% | 1,86× |
| ITA · Produtos de jardim | direto | **0,737** | 0,976 | 92,8% | 2,05× |
| ITA · Flores de corte | desag_8sem | 0,830 | 0,982 | 85,0% | 1,93× |
| ITA · Flores de corte | direto | **0,733** | 0,865 | **93,6%** | 2,87× |
| JC · Grama | desag_8sem | 0,761 | 0,819 | 81,0% | 1,44× |
| JC · Grama | direto | **0,740** | 0,797 | **94,3%** | 2,24× |
| JC · Plantas diversas | desag_8sem | **0,720** | 0,931 | 89,6% | 1,47× |
| JC · Plantas diversas | direto | 0,734 | 0,948 | 90,6% | 1,59× |
| JC · Produtos de jardim | desag_8sem | 0,695 | 0,878 | 90,4% | 1,47× |
| JC · Produtos de jardim | direto | **0,689** | 0,869 | 92,2% | 1,54× |
| JC · Flores de corte | desag_8sem | 0,878 | 1,081 | 60,3% | 1,48× |
| JC · Flores de corte | direto | **0,723** | 0,892 | **96,2%** | 2,90× |

**O direto vence o erro em 7 dos 8 pares.** A única exceção é Plantas diversas em Jardim
Canadá (0,720 vs 0,734, diferença de 1,9% — abaixo do limite de materialidade de 5% do
projeto, portanto empate).

Dois resultados pesam mais que o placar:

**Flores de corte é o caso que decide.** Nas duas lojas é onde a desagregação mais falha
(erro relativo 0,830 e 0,878, MASE acima de 1 em JC) e onde o direto mais ganha (0,733 e
0,723 — queda de 12% e 18% no erro). Em Jardim Canadá a faixa de 95% da desagregação cobre
**60,3%** do realizado: a previsão vem com uma promessa de 95% que erra 2 em 5 dias. É
coerente com o que a EDA já indicava (§3.11 do `00-eda_report.md`): o pico de data
comemorativa de Flores de corte se anula no total da unidade — no Dia das Mães a categoria
sobe 2,14× enquanto a unidade cai 0,66× — e rateio por participação não tem como recuperar
um sinal que o agregado não carrega.

**A cobertura do IC é sistematicamente melhor no direto**, em 8 de 8 pares (78→94, 85→94,
60→96...). A desagregação multiplica a faixa do L1 pela participação da categoria, o que é
uma aproximação, e a cobertura medida mostra que ela não se sustenta. O custo é uma faixa
mais larga (1,4–1,9× contra 1,5–2,9× a venda média do dia) — mas uma faixa estreita que
cobre 60% não vale mais que uma larga que cobre 96%.

**O que o experimento não muda:** o nível de SKU. A desagregação segue sendo a saída para
SKU, e nada aqui contesta Croston/TSB/SBA na série quase toda zero.

## 3. Decisão proposta

1. **Categoria passa a ser prevista por SARIMAX próprio**, não por rateio do L1. O L1 por
   unidade continua existindo — para a previsão da loja e como fallback de categoria com
   histórico curto.
2. **SKU continua por desagregação** a partir da categoria (`categoria → SKU`), mantendo o
   fallback de rateio uniforme e a trilha de comparação com demanda intermitente.
3. **A cascata deixa de ter 2 passos e passa a ter 1**: `categoria → SKU`. O passo
   `unidade → categoria` sai.
4. **Emenda do Princípio II** via `/speckit-constitution` antes de qualquer implementação.
   Enquanto não houver emenda, `backend/domain/disaggregation/` não muda.

## 4. Consequências

**Custo de treino.** Passa de 2 modelos L1 para 2 L1 + 8 de categoria (4 por unidade). A
seleção de ordem por AIC é o passo caro (36 ajustes por série) e roda uma vez; o retreino
semanal é 1 ajuste por modelo. Pelo medido neste hardware (~2,3 s por ajuste), o retreino
de 10 modelos fica em segundos — cabe folgado na janela de `RETRAIN_AFTER_UPLOAD_MINUTES`.

**`model_artifacts` muda de semântica.** Hoje a tabela registra categoria como
"desagregação, sem modelo próprio". Passaria a registrar ordem, MASE, cobertura e
`artifact_path` por categoria, como já faz para loja e produto.

**Status dos modelos.** Com o protocolo deste experimento, `Produtos de jardim` em
Itabirito fica em `low_confidence` (MASE 0,976 no direto, no limite; 1,023 na desagregação).
As outras 7 categorias-unidade passam `MASE < 1` no direto.

**Risco.** 8 modelos de categoria é mais superfície de falha que 2 L1 + rateio
determinístico: uma categoria pode não convergir numa origem. O walk-forward deste
experimento teve 0 falhas de convergência em 351 origens × 8 séries, mas o código de
produção precisa do fallback (rateio do L1) para a origem que falhar.

## 5. Pendência

A receita do direto usada aqui (sem `log1p`, d = 1) não é a melhor: o teste de
transformação e diferenciação por nível (`variantes_log_d_categoria_sku.py`) indica que a
receita do L1 não desce para a categoria. Isso vai para um ADR próprio, com os resultados
das 2 unidades.

## 6. Referências

- `ia-predictor/training_scripts/disaggregation/categoria_direta_vs_desagregacao.py` — o experimento
- `ia-predictor/training_scripts/eda/eda_separacao.py` — EDA 4, base da norma vigente
- `docs/prediction/00-eda_report.md` §3.11 — separação unidade/categoria
- `docs/prediction/ADR-013-encomendas-por-tamanho-da-venda.md` — o fluxo diário usado como alvo
- Métricas: `training_scripts/results/metrics/categoria_direta_vs_desag_{itabirito,jardim-canada}.json`
  (**não versionado** — `results/` está no `.gitignore`; por isso os números estão no corpo
  deste ADR)
