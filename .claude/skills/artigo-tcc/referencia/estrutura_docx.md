# Estrutura interna do DOCX e armadilhas conhecidas

## Formatação a preservar

- Página A4 (11900 × 16820 twips), margens 1702 (esq.) / 1060 (dir.) / 1708 (sup.) / 1142 (inf.).
  Largura útil para figuras: 5.760.085 EMU (≈ 6,3 pol).
- Estilo `Normal`: Arial 12, justificado, entrelinha 363 (≈ 1,5), recuo de 1ª linha 698.
- Parágrafo de corpo: `Normal` + `<w:ind w:left="-15" w:right="60"/>`. Entre parágrafos de corpo
  há um **parágrafo vazio** (" ") com `spacing after≈117 line=259`, `ind left=0 firstLine=0`.
  O último parágrafo de uma seção costuma ter `spacing after="239"`.
- Títulos: `Ttulo1` (capítulo, numeração automática, `spacing after=469`) e `Ttulo2` (seção).
  RESUMO é `Ttulo1` com `numId 0` (sem número). Capítulos 10, 11 e REFERÊNCIAS são parágrafos
  comuns com run em negrito e número digitado.
- Listas: `numId 1` questões operacionais (2.2); `2` itens "O sistema desenvolvido permite";
  `3` objetivos específicos; `4` stack (6.3); `5` regras de negócio (7.4). Novo item = clone de um
  item da mesma lista. As dimensões de validação (1°, 2°, 3°) em 6.6 são parágrafos com recuo
  pendente, não lista numerada.
- Legendas: centralizadas, run `sz=20` (10 pt), "Figura N – Título" acima da figura e
  "Fonte: Elaborado pelos autores (2026)." abaixo (ou "… com base em reuniões com a entidade
  parceira (2026)." nas Tabelas 1 e 3). Legendas e parágrafos de imagem têm `keepNext`.
- Tabelas: `TableGrid`, largura 9072, bordas simples `sz=2`, cabeçalho com fundo `D9D9D9` e negrito,
  texto `sz=22` (11 pt). Nova tabela = cópia profunda de uma existente (Tabela 2 ou 4) com
  `tblGrid`/`tcW` ajustados (somando 9072).
- Referências: parágrafos sem recuo de 1ª linha, `spacing after=240 line=240`, alinhados à
  esquerda (clone da entrada MAKRIDAKIS). Algumas entradas antigas estão quebradas em dois
  parágrafos pela conversão (ARUNRAJ, HYNDMAN; ATHANASOPOULOS, WIRTH): não "conserte".
- Quebras de página: capítulos começam em página nova por `<w:br w:type="page"/>` no fim do último
  parágrafo do capítulo anterior, ou por `pageBreakBefore` (cap. 11 e REFERÊNCIAS). Capítulos 6,
  7 e 8 seguem na mesma página no DOCX original; mantenha.

## Sumário

- O campo TOC fica num `w:sdt`; entradas com estilos `Sumrio1`/`Sumrio2`, hiperlink para o
  bookmark do título e `PAGEREF <bookmark> \h`. O fim do campo (`fldChar end`) está no final da
  entrada "9 PROTOTIPAÇÃO" (não deixe parágrafo vazio depois dela).
- Logo após o `sdt` vêm três entradas fora do campo: "10 RESULTADOS", "11 CRONOGRAMA DO PROJETO" e
  "REFERÊNCIAS", com `PAGEREF` para `_Toc900010/11/12`.
- Nova seção: crie o título (clone de `Ttulo2`), dê um bookmark novo (`Doc.add_bookmark`, nome
  `_Toc9000NN`) e crie a entrada com `Doc.toc_add_after(entrada_anterior, "6.7 Título", "_Toc9000NN")`.
  Renomeie as entradas seguintes (a numeração das seções é automática, a do sumário não).
- Nunca clone a primeira entrada (RESUMO): ela contém o início do campo TOC.
- Os números de página só ficam certos depois do `word_finalize.ps1`. Não peça ao Word para
  "atualizar o índice inteiro": isso apagaria as três entradas fora do campo.

## Fluxo de dados das figuras

- Figura = parágrafo com `w:drawing`/`wp:inline` → `wp:docPr name="Picture NNNN"` → `r:embed="rIdN"`
  → `word/_rels/document.xml.rels` → `word/media/imageN.(jpg|png)`. O Word renumera `imageN` e
  `rIdN` ao salvar; o `docPr name` é estável (tabela em `contexto.md`).
- Tamanho de exibição: `wp:extent` e `a:ext` (EMU) — `replace_figure.py` atualiza os dois.
- Remover uma figura: apague legenda, parágrafo da imagem, fonte e o espaçador extra; renumere as
  figuras seguintes (legenda e menções no texto) e remova a relação/arquivo de mídia órfãos.

## Diagramas (Graphviz)

- Fontes em `diagramas/*.dot`. Paleta dos originais: azul `#e8f1fb`/`#2e75b6`, verde
  `#eaf7ea`/`#3e8e41`, laranja `#fbeee8`/`#b6662e`, amarelo `#fff6dd`/`#c9a227`, lilás
  `#efe6fb`/`#7a5ab5`, arestas `#555555`, «include» tracejado `#999999`; classes `#f4f8fd`/`#8ab2d7`.
  Fonte Arial 12–13.
- Render: `dot -Tpng -Gdpi=220 fig.dot -o fig_hi.png`, depois `replace_figure.py` com `--ppi`
  (dobro do valor de 110 dpi listado no script) ou `--width-emu`.
- Graphviz portátil (sem instalar): baixar
  `https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/12.2.1/windows_10_cmake_Release_Graphviz-12.2.1-win64.zip`
  para a pasta temporária e usar `Graphviz-12.2.1-win64/bin/dot.exe`.
- Diagrama de classes: layout em grade (`newrank=true` + `rank=same` por linha) para ficar em
  paisagem como o original; `rankdir=TB` puro gera uma coluna alta demais.

## Armadilhas encontradas (e a solução)

| Sintoma | Causa | Solução |
| --- | --- | --- |
| Capítulo passou a começar no meio da página | `set_text` antigo apagava o run com `<w:br type=page>` | `Doc.set_text` preserva a quebra; confira no render |
| Duas linhas em branco seguidas | clonar um espaçador ao lado de outro já existente | olhe os vizinhos antes de inserir (`dump_docx.py`) |
| "log(1 +" / "y)" separados no fim da linha | espaço comum em expressão | use ` ` (constante `NBSP`) |
| Legenda no pé da página e figura na seguinte | falta de `keepNext` | `Doc.keep_captions_with_next()` antes de salvar |
| `renumber` não troca "Figura 12" | texto partido entre runs | reescreva o parágrafo com `set_text` |
| Itálico gera XML inválido | `w:i` antes de `w:b` no `rPr` | `make_run` já insere na ordem do schema |
| `PermissionError` ao abrir o DOCX | arquivo aberto no Word | leia de uma cópia; grave o final só com o Word fechado |
| `zip: command not found` | Git Bash sem zip | `docx_zip.py pack` |
| Acentos quebrados no console | cp1252 do Windows | grave em arquivo UTF-8 e leia com Read |
| Captura de tela com gráfico vazio / Edge travado / "invalid URL" | animação do Recharts, perfil do usuário em uso, conversão de caminho do Git Bash | `capture_screens.py` via CDP com `MSYS_NO_PATHCONV=1` |
| `can't open file 'c:\c\Users\...'` | `MSYS_NO_PATHCONV=1` também deixa o caminho do script sem conversão | passe todos os caminhos com `$(cygpath -w ...)` |
| Novo `vite` sai com código 1; porta 5199 ocupada | parar a tarefa em segundo plano não mata o `node` filho | encerre o PID que escuta na porta, depois de conferir a linha de comando |
| PDF não renderiza no Read | sem poppler | PyMuPDF em `<tmp>/pylib` + `render_pages.py` |
| Número de páginas difere do PDF original | o DOCX é conversão de PDF; o Word pagina diferente | compare com o render do DOCX anterior, não com o PDF |
