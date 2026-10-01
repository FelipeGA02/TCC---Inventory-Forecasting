---
name: "artigo-tcc"
description: "Atualizar, revisar ou produzir o artigo/projeto técnico do TCC (DOCX vigente em docs/project/, hoje TCC2 - Inicial.docx) a partir do estado real do repositório, preservando estilo e formatação do DOCX original. Use sempre que o pedido envolver o artigo, o TCC em Word, seus capítulos, figuras, tabelas, sumário ou referências."
argument-hint: "O que mudar no artigo (ex.: 'incorporar o treino da desagregação L2', 'revisar coerência')"
user-invocable: true
disable-model-invocation: false
---

# Artigo do TCC: produção e atualização

Esta skill registra como o artigo foi consolidado em 30/09/2026 e define o procedimento para
toda alteração futura. Objetivo de qualquer edição: o artigo deve parecer **sempre ter sido escrito
assim**, pelo mesmo autor, com a formatação do DOCX original, descrevendo o estado consolidado do
projeto.

## Entrada do usuário

```text
$ARGUMENTS
```

## Antes de começar, leia

1. `referencia/estilo.md`: regras de escrita (obrigatórias).
2. `referencia/contexto.md`: estrutura do artigo, decisões de escopo, números e suas fontes,
   mapa de figuras e referências (inclusive pendências).
3. `referencia/estrutura_docx.md`: como o DOCX é montado e as armadilhas já conhecidas.

## Fluxo obrigatório

Trabalhe numa pasta temporária (a pasta de rascunho da sessão), nunca direto no arquivo final.
Python com `lxml` e `Pillow`: `/c/Users/felip/anaconda3/python.exe`. Scripts em
`.claude/skills/artigo-tcc/scripts/` (abaixo, `S=` esse caminho e `T=` a pasta temporária).

### 1. Analisar antes de escrever

- Identifique o DOCX vigente em `docs/project/` (em 30/09/2026: `TCC2 - Inicial.docx`, a versão
  consolidada renomeada pelo usuário). Se houver mais de um candidato, pergunte qual usar.
- Desempacote e liste o artigo atual; leia a listagem inteira com Read:
  ```bash
  python $S/docx_zip.py unpack "docs/project/TCC2 - Inicial.docx" $T/work
  python $S/dump_docx.py $T/work/word/document.xml > $T/dump.txt
  ```
- Leia **todas** as fontes que tocam o pedido: ADRs e relatórios em `docs/prediction/`, ADRs de
  backend/banco/frontend, `CLAUDE.md`, `SPECS.md`, `specs/001-*/`, `ia-predictor/openapi.yaml` e o
  código. Hierarquia: código > Markdown atualizado > documentação técnica externa > artigo.
- Confira no código se o que a documentação diz existe. O que ainda for esqueleto pode ser
  descrito como implementado **só em nível conceitual** (instrução do usuário), sem inventar.
- Monte para si um mapa *trecho atual → fato real → alteração*; não o coloque no artigo.

### 2. Editar o XML preservando a formatação

Escreva um script de edição em `$T` usando `docx_lib.Doc` (veja a docstring do módulo e
`exemplos/consolidacao_2026-09-30.py`):

- Localize parágrafos **por texto** (`d.find(startswith=...)`), nunca por índice fixo.
- Reescreva com `d.set_text(p, "…[[itálico]]…")`: mantém `pPr`, bookmarks e quebra de página.
  Texto de corpo: `rpr=None`; células e legendas: deixe `rpr="auto"` (herda `sz`).
- Parágrafo novo = `d.clone(modelo, texto)` do tipo certo (`tpl_body`, `tpl_spacer`,
  `tpl_heading2`, `tpl_caption`, `tpl_source`, `tpl_reference`, item da mesma lista). Respeite o
  padrão corpo / espaçador / corpo; o último parágrafo da seção clona `tpl_section_end`.
- Tabela nova: cópia de uma tabela existente; ajuste `tblGrid` e `tcW` (soma 9072).
- Nova seção: título `Ttulo2` clonado + `add_bookmark` + `toc_add_after`; renomeie as entradas
  seguintes do sumário e as remissões no texto ("Seção 6.6").
- Figuras e tabelas: mantenha numeração sequencial, legenda + fonte, menção no texto; ao final
  chame `d.keep_captions_with_next()`.
- Expressões com `=` ou `+` no texto: use `NBSP` para não quebrar a linha.
- Referência nova: entrada ABNT clonada de `tpl_reference`, inserida na ordem alfabética, e
  citada no texto. Sem confirmação dos dados bibliográficos, não use a obra.

### 3. Figuras, quando o conteúdo mudar

- Diagramas: edite `diagramas/*.dot`, renderize com Graphviz (portátil, ver `estrutura_docx.md`) e
  troque com `replace_figure.py $T/work "Picture NNNN" img.png --ppi N` ou `--width-emu`.
- Telas: suba o protótipo (`cd app-react && npx vite --port 5199 --strictPort`, em segundo plano)
  e capture todas. Com `MSYS_NO_PATHCONV=1` nenhum caminho é convertido, então passe **todos** em
  formato Windows:
  ```bash
  MSYS_NO_PATHCONV=1 python "$(cygpath -w $S)\capture_screens.py" "$(cygpath -w $T)\shots" 9449 \
    "$(cygpath -w 'ia-predictor/data/raw/abril 25.xlsx')"
  ```
  Troque as imagens com `replace_figure.py`. Ao terminar, parar a tarefa em segundo plano não
  encerra o `node`: localize o PID com `netstat -ano | grep ":5199 .*LISTENING"`, confirme pela
  linha de comando (`Get-CimInstance Win32_Process -Filter "ProcessId = N"`) que é o vite que você
  subiu e só então encerre. Uma tela que deixou de existir no app sai do artigo (figura removida e
  as demais renumeradas).
- Não crie imagem de interface que não exista nem gráfico decorativo.

### 4. Empacotar, paginar e exportar

```bash
python $S/docx_zip.py pack $T/work $T/draft.docx
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $S)\word_finalize.ps1" \
  -In "$(cygpath -w $T)\draft.docx" -OutDocx "$(cygpath -w $T)\final.docx" -OutPdf "$(cygpath -w $T)\final.pdf"
```

### 5. Verificar (tudo, sempre)

- Automático: `python $S/check_article.py $T/final.docx` (estilo, fatos obsoletos, citações ×
  referências, numeração de figuras/tabelas) e o validador da skill docx
  (`scripts/office/validate.py final.docx --original <anterior>.docx`).
- Visual: `PYTHONPATH=$T/pylib python $S/render_pages.py $T/final.pdf $T/pages` (instale antes
  `pip install --target $T/pylib pymupdf`) e leia as folhas: legendas separadas, capítulos sem
  página nova, linhas em branco duplas, tabelas cortadas, sumário com números coerentes.
- Releitura integral: `dump_docx.py $T/final.docx` e leia do RESUMO às REFERÊNCIAS checando a lista
  de coerência de `estilo.md` (introdução ↔ resultados, metodologia ↔ implementação, texto ↔
  figuras, remissões).

### 6. Entregar

- Só com o Word fechado, copie `$T/final.docx` sobre o DOCX vigente (mesmo nome). A versão anterior fica no git; não faça commit sem pedido.
- Atualize `referencia/contexto.md` se mudaram fatos, figuras, referências ou pendências.
- Resposta ao usuário: comece com a linha de público ("Escrito para: banca e orientadores do TCC"),
  diga o que mudou e liste o que precisa de confirmação (decisões de escopo, funcionalidades
  descritas em nível conceitual, referências não conferidas).
