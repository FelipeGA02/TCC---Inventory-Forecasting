# Contexto do artigo e fatos consolidados

## Estado em 05/11/2026 (vale sobre as seções antigas abaixo)

- **DOCX vigente:** `docs/project/TCC2 - Relatorio Tecnico - v4.docx` (v4, 05/11/2026: sem a classificação confiável/cautela, 4.7 integrada à arquitetura; scripts em `exemplos/revisao_2026-11-05_v4/`). A v3 foi montada a partir do DOCX **nativo** da v2
  (`Downloads/TCC2 - Relatorio Tecnico - v2 (comentarios atendidos).docx`). A cópia de mesmo nome em `docs/project/`
  é uma conversão de PDF para Word: não use como base.
- **Estrutura do DOCX nativo** (diferente da antiga convertida): Times New Roman 12, entrelinha 1,5; corpo com
  `ind firstLine=709` e sem parágrafos vazios entre parágrafos; títulos `Ttulo1`/`Ttulo2` com o número digitado
  ("5.6 Delineamento experimental") e `pageBreakBefore` no `Ttulo1`; listas "a)" com tab 1077 e recuo pendente 369;
  sumário e listas de figuras/quadros/tabelas **estáticos** (números digitados); "Quadro" = grade sz 4, "Tabela" =
  aberta (topo 12, cabeçalho 8, fim 12); referências com título em **negrito**; a numeração do texto começa pelo
  `pgNumType start` da última seção (= índice 0-based da folha da introdução no PDF; hoje 10). Os scripts antigos
  (`docx_lib.py`, `check_article.py`) foram escritos para a versão convertida; para a v3 use
  `exemplos/revisao_2026-11-05/` (`docbuild.py` gera cada tipo de parágrafo; `build_article.py` monta tudo;
  `extract_pages.py` lê as páginas do PDF do Word; repetir até a paginação estabilizar).
- **Solução descrita:** ADR-017 (SARIMAX por categoria e por produto de grama, por loja; d = 0; escala original;
  janela de 365 dias; 56 origens; treino sob demanda; histórico congelado; conferência da planilha). Sem alertas, sem
  simulação, sem agendador, sem quantidade de referência (só trabalhos futuros).
- **Experimentos E0 a E10:** Quadro 2 e Seção 8.2; quadro de rastreabilidade em
  `docs/project/TCC2 - Relatorio Tecnico - v3 - quadro de rastreabilidade dos experimentos.md`. E10 vem do treino do
  sistema reproduzido em SQLite local (código `c8b0b55`, dados até 28/02/2026).
- **Figuras:** 1 a 6 de `diagramas/*.dot` (Graphviz); 7 a 13 capturadas do sistema real (API + Vite sobre SQLite local,
  Chrome DevTools, 1600 × 720). Telas com **dados reais** da parceira: autorização pendente.
- **Pendências:** ver `docs/project/TCC2 - Relatorio Tecnico - v3 - relatorio de alteracoes.md` §7 e §8.

---

Estado em 30/09/2026, quando o artigo foi consolidado. Antes de reutilizar qualquer número,
confira a fonte indicada: se o repositório evoluiu (novo treino, novo ADR), a fonte manda.

## O documento

- Arquivo vigente: `docs/project/TCC2 - Inicial.docx`. É a versão consolidada em 30/09/2026
  (entregue como `TCC1 - Final.PDF.docx`), renomeada e reaberta pelo usuário no Word. Versão
  anterior à consolidação: commit `c70291d`
  (`git show c70291d:"docs/project/TCC1 - Final.PDF.docx" > <tmp>/anterior.docx`).
- Título atual: **SISTEMA DE PREVISÃO DE VENDAS: UMA SOLUÇÃO INTELIGENTE PARA A GESTÃO DE
  DEMANDA DA FLORICULTURA VERDE PERTO**. Por decisão do usuário (30/09/2026), o nome do sistema é
  "previsão de **vendas**" em todo o repositório e no artigo; "previsão de estoque" não deve voltar.
  Termos de gestão continuam com "estoque" ("gestão de estoque", "ruptura de estoque", "controle de
  estoque"). `check_article.py` aponta divergências entre o título e o texto.
- Categorias: o nome antigo "Plantas de corte" (métricas dos treinos pré-EDA) corresponde à atual
  **Flores de corte**. "Plantas diversas" é outro grupo (plantas exceto flores de corte e árvores).
- Origem: o DOCX é uma **conversão de PDF para Word**. Por isso: não há estilos semânticos para o
  corpo (texto em `Normal` com `ind left=-15 right=60`), há um parágrafo vazio entre parágrafos,
  listas usam numeração própria (`numId` 1 a 5), e a renderização do Word não bate página a página
  com o PDF original. Essas peculiaridades são o padrão a preservar, não defeitos a corrigir.
- "Projeto técnico" apresentado ao Centro Universitário Dom Helder (Ciência da Computação, 2026).
  Autores: Daniel Nunes da Silva e Felipe Gurgel Araújo. Parceira: Floricultura Verde Perto.

## Estrutura (capítulos e seções)

| Cap. | Título | Observação |
| --- | --- | --- |
| — | RESUMO, Palavras-chave, SUMÁRIO | resumo inclui os resultados principais |
| 1 | INTRODUÇÃO | último parágrafo descreve o que cada capítulo traz |
| 2 | PROBLEMATIZAÇÃO (2.1 Situação Atual, 2.2 Situação Desejada) | situação desejada usa "poderá" de propósito |
| 3 | JUSTIFICATIVA | contribuições acadêmicas (i) e (ii) |
| 4 | OBJETIVOS (4.1 Geral, 4.2 Específicos) | objetivos no infinitivo |
| 5 | REFERENCIAL TEÓRICO | sem subseções |
| 6 | METODOLOGIA ADOTADA | 6.1 Metodologia de Desenvolvimento de Software · 6.2 Levantamento e Análise de Requisitos · 6.3 Ferramentas, Tecnologias e Ambientes de Desenvolvimento · **6.4 Preparação dos Dados e Modelagem Preditiva** · 6.5 Ferramentas de Modelagem · 6.6 Procedimentos de Testes e Validação |
| 7 | REQUISITOS DO SISTEMA | 7.1–7.5; Tabelas 1 (RF), 2 (RNF), 3 (atores); RN01–RN08 |
| 8 | MODELAGEM | 8.1–8.6; Figuras 1 a 5 (diagramas) |
| 9 | PROTOTIPAÇÃO | Figuras 6 a 12 (telas do protótipo React) |
| 10 | RESULTADOS | Tabela 4 (desempenho por unidade) |
| 11 | CRONOGRAMA DO PROJETO | Tabela 5 |
| — | REFERÊNCIAS | ABNT, ordem alfabética |

Capítulos 1 a 9 usam o estilo `Ttulo1` (numeração automática); seções usam `Ttulo2`. Os
capítulos **10, 11 e REFERÊNCIAS são parágrafos comuns em negrito**, com o número digitado, e
entram no sumário por entradas com `PAGEREF` para os bookmarks `_Toc900010`, `_Toc900011` e
`_Toc900012`. A seção 6.4 tem o bookmark `_Toc900001`.

## Decisões de escopo refletidas no artigo (e de onde vêm)

| Tema | Como o artigo apresenta | Fonte no repositório |
| --- | --- | --- |
| Entregável | previsão de demanda **diária**, horizonte de **14 dias**, com IC 95%; o sistema informa e a loja decide a compra | `docs/prediction/ADR-009`, `ADR-011` |
| Reposição L3 (validade, estoque de segurança, simulação de perda/ruptura) | **fora do artigo** (ADR-011). O CLAUDE.md ainda descreve L3; o artigo segue o ADR-011. Se a parceira reverter, mude o artigo inteiro de forma coerente | `ADR-011` §1, §5 |
| Arquitetura | hierárquica: L1 = SARIMAX por **unidade** (2 séries, venda de balcão); L2 = desagregação em cascata unidade → categoria → produto (participação móvel de 4–8 semanas × perfil de dia da semana; efeito de datas por categoria; fallback uniforme para produto com < 28 dias com venda ou < 8 vendas) | `ADR-011` §4, `01-pre_processing.md` §5.2 |
| Unidades | 3 empresas (CNPJ) → 2 unidades: Jardim Canadá (floricultura + garden center) e Itabirito | `ADR-011` §2 |
| Categorias | Grama, Flores de corte, Produtos de jardim; grupos do cliente (Plantas diversas, Insumos e acessórios) só na apresentação | `ADR-011` §3 |
| Encomendas | **em aberto**: a regra "linha > 5 × mediana diária" + teto p99 foi retirada em 2026-10-09 por não ter fonte publicada. O artigo ainda a descreve e precisa ser revisto | — |
| Modelo adotado | SARIMAX com log1p, m = 7, D = 0, d = 1; ordem (0,1,1)(0,0,1) nas duas lojas; exógenas: 6 dummies de dia da semana, `loja_fechada`, `abertura_excepcional`; previsão pontual = mediana | `04-treino_l1_por_loja.md` (ficha técnica) |
| Random Forest / MDI | **avaliação e seleção** de exógenas (não ponderação: um SARIMAX linear absorve a escala) | `03-enriquecimento_serie_crua.md` (ficha técnica) |
| Clima | avaliado e descartado (1,4% da importância; sem ganho) | doc 03 §3.3 |
| Validação | walk-forward, 26 janelas de 14 dias (mar/2025–fev/2026), ordem escolhida só com dados até 01/03/2025; MASE < 1 e cobertura do IC 95% ∈ [90%, 98%]; reportar erro relativo à naïve na mesma janela, janelas vencidas e largura do IC; MAPE/SMAPE só informativos; Ljung-Box e Shapiro-Wilk registrados sem bloquear | constituição, `CLAUDE.md`, doc 04 |
| Alertas | pico de demanda (previsão 7 dias ≥ 20% acima da média de 4 semanas) e risco de sobra (validade curta, demanda em queda); sem estoque atual | `openapi.yaml` (/alerts), `config.py` |
| Perfis | admin = gestora de compras (upload, retreino manual, tudo); viewer = gerente de operações (consulta, simulação, exportação) | `ADR-003`, `docs/uml/use_cases.md` |
| Agendamento | ajuste semanal (segunda, 02:00) e geração diária (03:00), APScheduler | `ADR-006`, `CLAUDE.md` |
| Stack | Python 3.11, statsmodels, scikit-learn, pandas/numpy, matplotlib (EDA); FastAPI + JWT/bcrypt, SQLite/SQLAlchemy, APScheduler, openpyxl/reportlab; React 18 + TypeScript + Recharts (MUI/Radix), cliente gerado do OpenAPI; Git/GitHub; pytest | `requirements.txt`, `app-react/package.json` |
| Banco | tabelas Usuario, Categoria, Produto, Modelo, Previsao, Log_Processamento, Historico_Retreino; base transacional em arquivo gerado pelo pipeline | `infrastructure/database.py`, `CLAUDE.md` (Modelo de Dados) |
| Frontend | telas: Início, Carregar Planilha, Conferir Dados, Previsão de Compras, Simular Promoções, Baixar Relatórios. A tela "Produtos para Repor" (estoque × mínimo) foi **removida** em 13/09/2026 e não pode voltar ao artigo | `app-react/src/app/App.tsx`, commit `78fc5fc` |

### Funcionalidades descritas como implementadas, mas ainda em esqueleto no código

Por instrução do usuário, o artigo apresenta a versão final do sistema, em nível conceitual, sem
inventar detalhes. Em 30/09/2026 eram esqueletos: `backend/domain/*`, `services/*`, routers além
de auth/health, `scheduler.py`, e a ligação do dashboard com a API (o React usa `mockData`).
Também entrou como funcionalidade a "quantidade de referência para disponibilidade" (quantil
superior da previsão), proposta no doc 04 §5 passo 2. Ao atualizar o artigo depois que essas
partes forem implementadas, confira se o texto continua correto e só então detalhe mais.

## Números usados no artigo

| Número | Valor | Fonte |
| --- | --- | --- |
| Registros (documento × produto) | 333.019 (327.677 após remover serviços/taxas) | `01-pre_processing.md` §3, §6 |
| Planilhas | 26 (jan/2024–fev/2026), 0 duplicatas | idem §3 |
| Produtos distintos | 5.166 | EDA §2.1 |
| Clientes / vendedores | ~2.500 (2.523 códigos) / 38 | base da Etapa 1 (`training_scripts/output/Base01.csv`) |
| Dias no período / produto típico vende em | 789 / 9 dias | EDA §2.5 |
| Produtos intermitentes ou lumpy | 99,3% dos classificáveis | EDA §2.5b |
| Séries por unidade com venda | ~82% dos dias | EDA §3.0 |
| 20 maiores produtos | 61,7% do volume | EDA §2.6 |
| Datas comemorativas (Flores de corte) | 1,7 a 5,0 × a média (Mulher, Mães, Namorados) | EDA §3.4 |
| Fator das datas no SARIMAX (ADR-019) | alta em Flores de corte (metade): −40 a −45% no erro da semana; queda de 26–31/12 nas outras séries (inteira): Grama de Itabirito 268% → 27% | doc 08 §5 e §9.3 |
| Separação por unidade | Itabirito −17% de MASE com modelo próprio; nenhuma categoria ganha ≥ 5% | EDA §3.11, ADR-011 §4 |
| Calendário (série total) | feriados ~4 mil → ~0; IC 79 mil → 13 mil; −9% de erro; janelas vencidas 19 → 22 | doc 03 |
| Importância RF | dia da semana 83,2%, feriado 15,2%, clima 1,4% | doc 03 (ficha) |
| Resultado final (Tabela 4) | MASE 0,58 / 0,58; MASE < 1 em 25 / 23 de 26; erro relativo 66% / 62%; vence 24 / 24 de 26; MAE 1.282 × 1.948 / 486 × 780; cobertura 91,2% / 93,7%; largura 5.463 / 2.255 (Jardim Canadá / Itabirito) | doc 04 (ficha) |
| Abertura excepcional (ITA) | erro 780 → 50 | doc 04 §3.4 |
| Lojas somadas × total | −16% de erro em relação à série crua | doc 04 §3.3 |
| Resíduos (A1 na série total) | Ljung-Box p = 0,69 / 0,48 (lags 7/14); Shapiro rejeita normalidade | doc 03 (ficha) |
| Limitações | encomendas 51,2% do volume e 70% do erro de Itabirito no ano de teste; mediana cobre 87,5% / 80,9% do balcão | doc 04 §4 |

## Figuras (localize pelo nome do desenho, não pelo arquivo de mídia)

| Figura | `wp:docPr name` | Conteúdo | Origem |
| --- | --- | --- | --- |
| logo | Picture 60 | capa | original |
| 1 | Picture 1859 | casos de uso | `diagramas/fig1_casos_de_uso.dot` |
| 2 | Picture 1909 | atividades | `diagramas/fig2_atividades.dot` |
| 3 | Picture 1949 | classes | `diagramas/fig3_classes.dot` |
| 4 | Picture 2000 | modelo de dados | `diagramas/fig4_modelo_de_dados.dot` |
| 5 | Picture 2064 | arquitetura lógica | `diagramas/fig5_arquitetura.dot` |
| 6 | Picture 2234 | tela Início | captura `/` |
| 7 | Picture 2236 | Carregar Planilha | captura `/importar` |
| 8 | Picture 2294 | validação pós-upload | captura `/importar` + upload |
| 9 | Picture 2296 | Conferir Dados | captura `/pre-visualizacao` |
| 10 | Picture 2343 | Previsão de Compras | captura `/previsao` |
| 11 | Picture 2394 | Simular Promoções | captura `/simulador` |
| 12 | Picture 2421 | Baixar Relatórios | captura `/exportar` |

As telas usam dados fictícios do protótipo; o Capítulo 9 diz isso explicitamente. Se uma tela
mudar no `app-react`, recapture todas para manter o menu lateral igual em todas as figuras.

## Referências

Acrescentadas na consolidação (todas citadas no texto): Bartezzaghi e Verganti (1995); Chen e Liu
(1993); Croston (1972); Fliedner (2001); Gross e Sohl (1990); Huber, Gossmann e Stuckenschmidt
(2017); Hyndman e Koehler (2006); Kalchschmidt, Verganti e Zotteri (2006); Pearson et al. (2016);
Syntetos, Boylan e Croston (2005); Teunter, Syntetos e Babai (2011); Zotteri e Kalchschmidt (2007).
Os dados bibliográficos vieram do antigo `ADR-012` (Referências; removido, está no histórico do git) e `01-pre_processing.md` §5.2, onde
estão os DOIs; não foram conferidos online na sessão.

**Pendência conhecida:** a entrada PAVLYSHENKO (2019), que já existia, repete o título do artigo
de Arunraj et al. e atribui a ela resultados (MAPE < 5%, redução de 18%) que precisam ser
verificados. Não foi alterada. Não reutilize esses números em texto novo sem confirmar a fonte.

Ainda disponíveis no repositório, não usadas no artigo: Kalchschmidt, Zotteri e Verganti (2003)
(conferir o texto completo antes de citar), Verganti (1997) (DOI não confirmado),
Bartezzaghi, Verganti e Zotteri (1999), Johnston, Boylan e Shale (2003), Olhager (2003),
Box e Tiao (1975), Babai, Boylan e Rostami-Tabar (2022).
