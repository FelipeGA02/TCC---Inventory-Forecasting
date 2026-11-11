# Planilhas de teste da importação — março/2026

Vendas **inventadas** de 01 a 31/03/2026 no layout do relatório "Contas a Receber", para
testar a tela "Importar planilha" com cada caso que a importação trata ou avisa. Geradas por
`gerar_planilhas.py` (semente fixa: rodar de novo dá os mesmos arquivos).

> **Não envie estas planilhas para o Neon.** As vendas são fictícias: entrariam na base de
> produção, no treino e no histórico da previsão. Teste numa cópia do SQLite local
> (`DATABASE_URL=sqlite:///caminho/copia.db`) com a base real até 28/02/2026. A
> duplicata com a base (caso 10) só funciona com a base real, não com a base sintética dos
> testes e2e.

| Arquivo | Para quê |
| --- | --- |
| `marco_2026_com_erros.xlsx` | o mês com os erros abaixo |
| `marco_2026_corrigida.xlsx` | o mesmo mês com tudo corrigido |
| `erro_sem_vendas.xlsx` | planilha que não é o relatório |
| `erro_so_empresa_desconhecida.xlsx` | só notas de empresa sem loja cadastrada |
| `erro_formato.csv` | extensão recusada |

Como as vendas foram inventadas: cada dia de loja aberta recebe o número de notas de um dia
real da mesma loja e do mesmo dia da semana (fev/2026 e mar/2025). Cada nota copia produto,
quantidade e preço de uma nota real desse conjunto, sem encomendas grandes nem devoluções.
Número da nota, cliente, operador e vendedor são fictícios. A venda por dia aberto fica cerca
de 10% acima de fevereiro.

## Casos da planilha com erros

| # | Caso | Onde | O que a importação faz | Na corrigida |
| --- | --- | --- | --- | --- |
| 1 | Nota sem a linha `Cliente:` | Itabirito 05/03, CE 30744 | Etapa 1 pula a nota → **Linhas ignoradas** | linha do cliente de volta |
| 2 | Nota sem o cabeçalho `Produto` | J. Canadá 10/03, F3 11031 | Etapa 1 pula a nota → **Linhas ignoradas** | cabeçalho de volta |
| 3 | `Emissão:` vazia | J. Canadá 12/03, C7 28418 (5 linhas) | Etapa 2: campo obrigatório vazio → **Linhas ignoradas** | data 12/03/2026 |
| 4 | Produto sem código (`GRAMA ESMERALDA`, sem `cód - `) | J. Canadá 06/03, CN 28240 (1 de 4 linhas) | Etapa 2: campo obrigatório vazio → **Linhas ignoradas** | código de volta |
| 5 | Data inexistente `20/13/2026` | Itabirito 20/03, C9 28793 (4 linhas) | Etapa 2: data inválida → **Linhas ignoradas** | 20/03/2026 |
| 6 | Data fora do padrão `2026-03-24` | J. Canadá 24/03, C7 28980 (1 linha) | Etapa 2: data inválida → **Linhas ignoradas** | 24/03/2026 |
| 7 | Quantidade em texto (`dez`) | Itabirito 11/03, C9 28390 (1 de 9 linhas) | Etapa 2: valor não numérico → **Linhas ignoradas** | número |
| 8 | Valor total em texto (`R$ 0,00`, com o valor da linha) | J. Canadá 19/03, F3 11153 (1 de 6 linhas) | Etapa 2: valor não numérico → **Linhas ignoradas** | número |
| 9 | Empresa sem loja (`VERDE PERTO FILIAL BH LTDA`) | J. Canadá 25/03, 2 notas, 4 linhas | aviso **"4 linha(s) de empresa sem loja cadastrada foram ignoradas: VERDE PERTO FILIAL BH LTDA"** | empresa de Jardim Canadá |
| 10 | Duplicata com a base: 5 notas de 27 e 28/02 que já estão no banco (22 linhas) | início da planilha | **Já estavam carregadas: 22**; período passa a começar em 27/02 | removidas (são de fevereiro) |
| 11 | Dias sem venda com a loja aberta | J. Canadá 02/03; Itabirito 16 a 18/03 | aviso de **dias faltando** por loja; botão vira "Gravar mesmo assim" | vendas desses dias |
| 12 | Cliente sem nome (`Cliente: 3655 -`) | Itabirito 13/03, CE 30946 (3 linhas) | Etapa 2 corrige em silêncio (só em `processing_log.quality.clientes_sem_nome_corrigidos`) | cliente com nome |
| 13 | Espaços sobrando na empresa e no produto | J. Canadá 04/03, N3 7558 | Etapa 2 corrige em silêncio; a nota é gravada normal | sem espaços |
| 14 | Nota repetida inteira na mesma planilha | J. Canadá 27/03, CN 28503 (5 linhas, 2×) | **não é detectado** (ver abaixo) | aparece 1 vez |

Casos certos, iguais nas duas planilhas:

| Caso | Onde | O que se espera |
| --- | --- | --- |
| Encomenda grande de propósito: 2.400 m² de grama esmeralda | J. Canadá 18/03, C4 78252 | marcada como encomenda grande |
| Encomenda grande por acaso: pedido sorteado de 1.333 un. (1.280 bandejas de grama amendoim + 5 itens) | J. Canadá 17/03, C4 78022 | também marcada: o limiar recalculado com março cai de 1.343 para 1.320 un. (ADR-018) |
| Produto novo `00999001 - SUBSTRATO PARA SUCULENTAS 5KG` | Itabirito 23/03 | entra no catálogo em Produtos de jardim / Substrato e adubo |
| Mesmo produto 2× na mesma nota | Itabirito 09/03, C9 29476 | as 2 linhas gravadas (venda real, não é duplicata) |
| Nota de 24 linhas com quebra de página no meio | J. Canadá 03/03, C4 78253 | lida inteira (a quebra de página repete o cabeçalho do relatório) |
| Notas do Garden Center (`GARDEN CENTER VERDE PERTO LTDA`) | ~8% das notas de J. Canadá | contam como Jardim Canadá |
| Frete e serviços | sorteados | gravados; ficam fora do tamanho do pedido e da previsão |

As **19 linhas ignoradas** são 2 notas puladas na leitura (casos 1 e 2), 13 linhas removidas na
limpeza (6 com campo vazio, casos 3 e 4; 5 com data inválida, casos 5 e 6; 2 com valor não
numérico, casos 7 e 8) e 4 de empresa sem loja (caso 9).

## Números esperados na tela (conferidos com o serviço de importação)

Base: SQLite local com as vendas até 28/02/2026.

**1. `marco_2026_com_erros.xlsx`, conferência:** período 27/02/2026 a 31/03/2026 · Vendas
novas **12.388** · Já estavam carregadas **22** · Linhas ignoradas **19**. Avisos:

- Itabirito: faltam as vendas de 3 dias com a loja aberta (16/03/2026 a 18/03/2026). A última venda da loja já carregada é de 28/02/2026 e esta planilha traz a loja de 27/02/2026 a 31/03/2026.
- Jardim Canadá: faltam as vendas de 1 dia com a loja aberta (02/03/2026). A última venda da loja já carregada é de 28/02/2026 e esta planilha traz a loja de 28/02/2026 a 31/03/2026.
- 4 linha(s) de empresa sem loja cadastrada foram ignoradas: VERDE PERTO FILIAL BH LTDA

Depois de "Gravar mesmo assim": os mesmos números, com o aviso de treinar a previsão. O
registro diz "7 linha(s) nova(s) de encomenda grande", com limiar Itabirito 1.926 un. e
Jardim Canadá 1.321 un. São os 2 pedidos da tabela acima.

**2. `marco_2026_corrigida.xlsx` numa base em 28/02:** período 02/03 a 31/03 · Vendas novas
**13.057** · Já estavam carregadas **0** · Linhas ignoradas **0** · nenhum aviso. Depois de
gravar: 7 linhas de encomenda grande (os mesmos 2 pedidos), limiares 1.923 e 1.320 un.

**3. A corrigida depois de gravar a com erros:** Vendas novas **674** (as linhas que a
planilha com erros perdeu e os 4 dias que faltavam) · Já estavam carregadas **12.383** ·
Linhas ignoradas **0** · nenhum aviso. Ficam **5 linhas a mais** na base: a 2ª cópia da nota
repetida (caso 14). A corrigida não as apaga, porque a importação só acrescenta.

**4. A mesma planilha enviada 2 vezes:** "Esta planilha já foi carregada antes. Nada foi
duplicado." (409).

**5. Recusas da planilha inteira (400):**

- `erro_sem_vendas.xlsx`: "Não encontramos vendas nesta planilha. Confira se é o relatório “Contas a Receber” exportado do sistema da loja."
- `erro_so_empresa_desconhecida.xlsx`: "Nenhuma linha da planilha é de uma loja cadastrada."
- `erro_formato.csv`: "Apenas arquivos .xlsx e .xlsm são aceitos."

## O que a importação não pega

- **Nota repetida dentro da mesma planilha** (caso 14). A duplicata só é procurada contra a
  base, nunca dentro do arquivo, porque o mesmo produto pode vir em duas linhas da mesma nota.
  Uma nota inteira repetida (mesmo número, mesmos itens) entra duas vezes.
- **Nota pulada na leitura conta 1 em "Linhas ignoradas"**, tenha quantas linhas tiver (casos
  1 e 2 têm 1 linha cada, por isso o total fecha).
- **Correções silenciosas** (casos 12 e 13): nenhum aviso na tela.
- **Categoria desconhecida:** a classificação sempre devolve uma categoria, então o aviso
  "linha(s) de categoria desconhecida" não tem como aparecer a partir de uma planilha.
- **Arquivo acima de 50 MB** (413): não foi gerado.
