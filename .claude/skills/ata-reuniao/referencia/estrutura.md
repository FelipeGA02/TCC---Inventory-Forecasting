# Estrutura da ata: engenharia reversa das atas 01–04

Fonte: `Documento - Registro de Reuniao com Entidade 01..04.docx` (pasta `Relatórios`) e os PDFs
assinados. O `gerar_ata.py` reproduz o XML abaixo; este arquivo explica o que vai em cada lugar.

## Página e estilos (vêm do modelo, não mexer)

- A4 (11906 × 16838), margens 2,5 cm em cima/embaixo e 3 cm nas laterais (1417 / 1701 twips).
- Texto: Aptos 11 pt, espaço depois 8 pt, entrelinha 1,08. Título: estilo `Ttulo1` (Aptos Display
  20 pt, azul 0F4761), centralizado, em duas linhas forçadas por 20 espaços.
- Logo do Dom Helder: imagem ancorada no 1º parágrafo, centrada na margem, acima do título.
- Títulos de seção: parágrafo Normal em negrito, "N. Nome da seção". Sem estilo de título.
- Bullets: `numbering.xml` da ata 04. numId 1 (seção 1), 13 (seção 5, nível 0 "•" e 1 "o"),
  8 e 9 (seção 8), 3 (seção 9).

## Paginação

Nas 4 atas: pág. 1 = seções 1–3; pág. 2 = seções 4–5; a seção 6 abre a pág. 3; 9 e 10 ficam
juntas na última página (em 3 das 4). Os originais conseguiam isso com parágrafos vazios; o
gerador usa "quebra de página antes" nos títulos 4, 6 e 9, que dá o mesmo resultado sem depender
do tamanho do texto. Ata longa (muitos requisitos) pode passar de 5 páginas: tudo bem.

## Seções

| # | Seção | Formato | Conteúdo |
| --- | --- | --- | --- |
| 1 | Identificação da Reunião | 7 bullets "**Rótulo:** valor" | Projeto, Entidade / Empresa, Número (2 dígitos), Data `dd / mm / aaaa`, Horário `Início: hh:mm, Término: hh:mm`, Local `( ) Presencial (X) Online`, Plataforma |
| 2 | Participantes | tabela 2 col. sem borda (4253 + 4819), tudo em negrito, cabeçalho Nome / Papel / Função | equipe primeiro, depois cliente |
| 3 | Objetivo da Reunião | 1 parágrafo | 1 frase longa ou 2 curtas, começando por verbo no infinitivo ("Apresentar…", "Levantar e validar…") |
| 4 | Pauta / Assuntos Tratados | 6 linhas fixas "☐ item" | item tratado = **marca-texto amarelo na linha inteira** (o ☐ nunca vira X). "Outros:" recebe um texto curto e fica amarelo quando usado |
| 5 | Decisões Tomadas | bullets (Parágrafo da Lista), subitens "o" | 6–10 itens de 1–3 linhas; **negrito** só em termo-chave, como na ata 02 |
| 6 | Requisitos / Solicitações do Cliente | tabela 3 col. (1134 + 6237 + 1134): Código 9 pt / Descrição / `Alta (  ) Média (  ) Baixa (  )` | **cumulativa**: repete todos os REQ da ata anterior, na mesma ordem e redação, e acrescenta os novos com o próximo número |
| 7 | Pendências e Ações Futuras | tabela 2 col. (6663 + 1984): Ação / Prazo, termina com 1 linha vazia | até ~9 ações |
| 8 | Impactos no Projeto | 4 linhas "(   ) …" / "( X  ) …" num parágrafo; "**Descrição do impacto (se houver):**"; parágrafo(s); opcional "Pontos de atenção:" + bullets | |
| 9 | Próxima Reunião | 2 bullets: **Data prevista:** / **Objetivo:** | data `dd / mm / aaaa` ou texto ("A definir…") |
| 10 | Validação | declaração fixa, representante, assinatura, responsáveis, assinatura(s) | |

## O que escrever em cada seção

Regras gerais: português formal, impessoal, frases curtas, sem gíria nem jargão técnico
(escreva "faixa de confiança", não "IC 95%"; "vendas muito acima do padrão", não "outliers").
Registrar só o que a transcrição sustenta; nada inventado. Sucinto: a ata resume, não transcreve.

- **Projeto / Entidade**: copiar da ata anterior ("Sistema de Previsão de Estoque", "Floricultura
  Verde Perto").
- **Número**: o da última ata + 1. **Data/horário**: do cabeçalho da transcrição (início + duração).
- **Plataforma**: Google Meet, salvo indicação contrária.
- **Participantes**: nome completo e papel pela tabela abaixo. Incluir quem fala ou é chamado pelo
  nome durante a reunião mesmo que não esteja na lista do transcritor (ex.: Carolina ao lado do
  Arthur); avisar o usuário quando fizer isso.
- **Objetivo**: o propósito da reunião do ponto de vista da equipe.
- **Pauta**: marcar só o que de fato ocorreu. Exibir telas ou o sistema = "Apresentação de
  protótipo" e "Validação de funcionalidades"; pedido novo do cliente = "Alterações solicitadas pelo
  cliente"; prazos/reuniões do TCC = "Acompanhamento do cronograma".
- **Decisões**: o que foi apresentado, aprovado, definido ou descartado. Modelos de frase das atas:
  "Foi apresentado ao cliente…", "O cliente considerou… satisfatório", "Foi definido que…",
  "O sistema permitirá/será…", "A previsão será…".
- **Requisitos**: novos pedidos do cliente, redigidos como necessidade dele ("Poder…", "Ter…",
  "Ver…", "Filtrar…"). Prioridade só marcada se o cliente disser (`"prioridade": "Alta"`); nas atas
  01–04 nunca foi marcada. Não apagar nem reescrever REQ antigo sem pedido explícito.
- **Pendências**: ações no infinitivo ("Definir…", "Enviar…", "Testar…"). Ação do cliente leva
  "(cliente)" no fim. Prazos usados: "Próxima reunião", "TCC2", "Após …", ou uma data. Da ata
  anterior, manter as pendências que continuam abertas; tirar as concluídas ou já tratadas na
  reunião, e dizer ao usuário quais saíram.
- **Impactos**: marcar "Alteração de escopo" quando entra ou sai funcionalidade; "Não há impacto"
  quando só houve validação. Descrição em 1 parágrafo; riscos em "Pontos de atenção".
- **Próxima reunião**: data combinada ou "A definir…"; objetivo em 1 frase.
- **Validação**: representante do cliente = Carolina Araujo Nonato; responsáveis = Felipe Gurgel
  Araújo e Daniel Nunes da Silva (desde a ata 03), mesmo que um deles falte.

## Participantes conhecidos

| Nome | Papel / Função |
| --- | --- |
| Felipe Gurgel Araújo | Desenvolvedor da Solução |
| Daniel Nunes da Silva | Desenvolvedor da Solução |
| Carolina Araujo Nonato ("Carol") | Sócia Administrativa Proprietária |
| Rosely Aparecida Araújo Nonato ("Roseli") | Sócia Administrativa Proprietária |
| Arthur Vasconcelos | Auxiliar Administrativo Terceirizado |

Outros nomes citados na loja: Adelson e Edilson (tratam os pedidos com fornecedores). Não são
participantes, salvo se estiverem na reunião.

## Erros comuns da transcrição automática (Tactiq)

Falas sobrepostas, trechos repetidos e frases de outra pessoa coladas no meio. Ler a transcrição
inteira antes de escrever e juntar as partes de cada assunto.

| Na transcrição | Significa |
| --- | --- |
| outline, outlares, Outlander, Outlets | outliers: vendas muito acima do padrão, que no sistema se chamam **encomendas grandes** (ADR-013); nunca escrever só "encomendas" |
| sarimax, SARMAX | SARIMAX (modelo de previsão) |
| JC, JRS | sistema de gestão usado pela loja |
| Roseli / Carol | Rosely / Carolina |
| Felipinho / Felipe Gurgel | Felipe Gurgel Araújo |
| documento N / tipo N | tipo de documento da venda (N = venda com nota fiscal) |
