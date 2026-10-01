# Regras de escrita do artigo

Estas regras vêm das instruções do usuário para a consolidação de 30/09/2026 e da análise do
texto original dos autores. Valem para qualquer produção ou alteração do artigo.

## Princípio: uma narrativa única, consolidada

- O artigo apresenta o projeto **como ele é**, como se sempre tivesse sido escrito assim.
- **Nunca** contar a história do projeto ou do documento: nada de "Inicialmente…",
  "Anteriormente acreditava-se…", "Na primeira versão…", "Durante o desenvolvimento percebeu-se…",
  "Foi alterado o método…", "Diferentemente do planejado…", "Posteriormente decidiu-se…",
  "Foi necessário abandonar…". Não comparar versões nem justificar mudanças editoriais.
- Exceção estreita: comparação metodológica que faz parte do método (ex.: "o modelo próprio de
  Itabirito reduziu o MASE em 17% em relação à repartição da previsão da rede"). Isso é resultado
  de experimento, não histórico do projeto.
- Não escrever que algo anterior estava errado; escrever diretamente a informação correta.
- Preservar o que continua verdadeiro. Não reescrever um trecho só para mudar a redação.

## Tempo verbal

- Funcionalidade existente: "O sistema realiza…", "Foi implementado…", "O módulo é responsável
  por…". Evitar "será", "deverá", "poderá", "pretende-se", "espera-se", "futuramente".
- Funcionalidade planejada que deve constar da versão final: descrever como implementada, em
  **nível conceitual**, sem inventar algoritmo, métrica, tecnologia ou resultado.
- Usos legítimos do futuro/condicional: requisitos ("Gerar previsão… será necessário"), regras de
  negócio ("deve ser emitido"), situação desejada (2.2, "a empresa poderá") e cronograma.
- Objetivos (cap. 4) continuam no infinitivo.

## Hierarquia das fontes (quando houver conflito)

1. código do repositório; 2. Markdown atualizado (ADRs, docs de treino, EDA, pré-processamento);
3. documentação técnica externa (RAG, se houver); 4. o próprio artigo.
O artigo é referência **editorial** (estilo, estrutura, formatação), não de fatos.

## Estilo do autor (imitar)

- Registro acadêmico formal, impessoal, parágrafos longos (5 a 9 linhas), frases completas e
  encadeadas por vírgulas e pontos e vírgulas; poucas frases curtas em sequência.
- Conceito técnico apresentado com a sigla e, na primeira vez, o nome por extenso em itálico se
  for estrangeiro: "MDI ([[Mean Decrease in Impurity]])", "SKU ([[Stock Keeping Unit]])".
- Termos estrangeiros explicados em aposto na primeira ocorrência: "[[pipeline]], sequência de
  etapas…", "[[stack]], conjunto de ferramentas…", "sobreajuste ([[overfitting]]), fenômeno que…".
- Conectivos do autor: "Além disso" (uma vez no texto), "Adicionalmente", "De forma
  complementar", "Por fim", "Esse resultado fundamenta…", "Essa evidência legitima…".
- Citações no padrão ABNT autor-data: parentética em maiúsculas "(HYNDMAN; ATHANASOPOULOS, 2021)",
  "(BOX et al., 2015)", várias obras separadas por ponto e vírgula; narrativa "Arunraj, Ahrens e
  Fernandes (2016)", "Pearson et al. (2016)" para 4 ou mais autores.
- Resultados apresentados com o número, a comparação e a leitura na mesma frase
  ("…o MASE caiu para 0,796; em Jardim Canadá…, passando de 0,659 para 0,646.").
- Números em português: vírgula decimal, ponto de milhar (1.282; 0,58; 61,7%).
- Requisitos citados entre parênteses no texto: (REQ02), (RNF-01); regras como RN03.
- Figuras e tabelas introduzidas no texto antes da legenda ("A Tabela 4 apresenta…",
  "Como ilustra a Figura 6, …").

## Proibido (padrões de texto gerado por LLM)

- Travessão (—) para separar ideias. O original usa "–" só em legendas ("Figura 1 – …") e em
  intervalos ("Jul.–Ago./2026").
- "Nesse contexto", "Vale destacar", "É importante ressaltar", "De maneira geral", "Em suma",
  "Por outro lado", "Além disso" repetido.
- Linguagem promocional sem fundamento: "robusta e inovadora", "altamente eficiente",
  "tecnologia de ponta", "revolucionário", "extremamente importante".
- Excesso de listas e subtítulos. O artigo usa listas só onde já usava (questões operacionais,
  itens de "O sistema desenvolvido permite", objetivos específicos, stack, regras de negócio).
- Setas (→), ∈, subscritos Unicode no texto corrido: escreva por extenso ("p e q entre 0 e 2";
  "ordem (0,1,1), com ordem sazonal (0,0,1) e m = 7").

## Itálico (convenção do autor)

Itálico em termos estrangeiros e nomes de bibliotecas/ferramentas: [[dashboard]], [[upload]],
[[pipeline]], [[hold-out]], [[walk-forward]], [[stack]], [[stakeholders]], [[dataset]], [[top]],
[[overfitting]], [[stepwise]], [[lumpy]], [[top-down]], [[backend]], [[framework]], [[scripts]],
[[tokens]], [[hash]], [[garden center]], [[Random Forest]], [[statsmodels]], [[scikit-learn]],
[[pandas]], [[numpy]], [[matplotlib]], [[FastAPI]], [[SQLite]], [[SQLAlchemy]], [[APScheduler]],
[[React]], [[TypeScript]], [[Recharts]], [[pytest]], [[Git]], [[GitHub]]. Sem itálico: Python,
SARIMAX (exceto onde o original já usa, no cap. 9), siglas (MASE, MAE, JWT, API, AIC), BrasilAPI,
nomes de métodos (Croston, SBA, TSB, Holt-Winters, CRISP-DM).

## Referências (ABNT NBR 6023, como no original)

- Periódico: `SOBRENOME, A. B.; SOBRENOME, C. Título do artigo. [[Nome do Periódico]], v. N,
  n. N, p. X–Y, ANO.` (traço meio "–" nas páginas; DOI só se o original já o tinha).
- Livro: `SOBRENOME, A. [[Título]]: subtítulo. N. ed. Cidade: Editora, ANO.`
- Evento: `SOBRENOME, A. Título. In: NOME DO EVENTO EM MAIÚSCULAS, N., ANO, Cidade.
  [[Proceedings]]... Cidade: Editora, ANO. p. X–Y.`
- Ordem alfabética pelo primeiro autor; mesmo primeiro autor: menos autores primeiro.
- Toda referência nova deve ser citada no texto; toda citação deve ter referência.
- Não inventar autor, título, periódico, volume, páginas, ano ou DOI. Se não for possível
  confirmar (repositório, RAG ou consulta), não use a obra.

## Checagem de coerência antes de entregar

Introdução ↔ capítulos; objetivos ↔ resultados; referencial ↔ técnicas de fato usadas;
metodologia ↔ implementação; arquitetura ↔ repositório; resultados ↔ metodologia (números e
limiares); requisitos ↔ telas/figuras; texto ↔ figuras (nomes de atores, camadas, métricas);
citações ↔ referências; numeração de figuras/tabelas ↔ menções no texto; "Seção 6.6" e outras
remissões ↔ numeração real.
