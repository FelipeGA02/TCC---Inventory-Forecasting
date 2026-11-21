# O que ainda falta mudar — TCC2 - Relatório Técnico - Final - Corrigido

> **Aplicado em 21/11/2026 no DOCX Corrigido.** As correções abaixo entraram no texto.
>
> Entraram: §2.1–2.4, §3.1 (itens 1, 3 e 4), §3.2, §3.3 (exceto o termo do intervalo) e §3.4.
>
> Decisões tomadas na aplicação:
> - a referência de Iglewicz e Hoaglin saiu, e o limiar se apoia no E2;
> - o CRISP-DM saiu da 6.1;
> - o retreinamento ficou **mensal** (Quadro 7, 2.2 e 10.1.2 alinhados ao texto do E7);
> - as referências sem citação passaram a ser citadas (nenhuma foi removida);
> - as siglas MAPE, WAPE e ARIMA saíram; KPSS e ADF agora aparecem no E5.
>
> Continuam abertos:
> - §3.1 item 2 (Render × Azure), que depende de decisão;
> - o termo do intervalo (o orientador pediu "intervalo de confiança" na conclusão);
> - §2.5 (tamanho das Figuras 2–5);
> - a repaginação no Word: Sumário e listas.

Conferência de 21/11/2026: cada pedido do orientador (anotações do Acrobat em
`TCC2 - Relatorio Tecnico - Final - COMENTÁRIOS.pdf`, mapeadas uma a uma em
[correcoes_TCC2_comentarios.md](correcoes_TCC2_comentarios.md), itens 1–119) foi procurado no
texto de `TCC2 - Relatorio Tecnico - Final - Corrigido.pdf` (64 páginas). Os números de página
abaixo são os **impressos** no Corrigido.

- O Corrigido não tem nenhuma anotação: os comentários existem só no PDF de 18/11.
- As marcações coloridas que aparecem no Corrigido não são anotações do Acrobat: o texto
  "Trabalho de Conclusão de Curso" (p. 2), o Abstract, a nota da Tabela 2, as Keywords e as notas
  das Tabelas 3 e 4 estão marcados em roxo ou laranja. Se foram feitas para marcar o que mudou,
  **é preciso tirá-las antes de entregar**.

---

## 1. Situação dos 119 pedidos

**Resolvidos: 110. Resolvidos com alguma ressalva: 5. Pendentes: 4.**

| Situação | Itens |
| --- | --- |
| ✅ Resolvidos | 2–9, 12–16, 18, 20–41, 44–45, 47–57, 59–119 |
| ⚠️ Resolvidos, mas com ressalva (ver §2) | 10, 11 e 19 (decisão a justificar), 46 (frase nova truncada), 58 (leitura duvidosa) |
| ❌ Pendentes (ver §2) | 1 (revisão geral: há erros novos, §3), 17 (cobertura não explicada no Abstract/Resumo), 42–43 (conferir as figuras na versão final) |

Conferidos e corretos no Corrigido:

- **Listas de Figuras, Quadros e Tabelas e Sumário** (itens 3, 4, 21–30): todas as páginas
  batem com o PDF. "Anexo A –" e "Apêndice A –" estão nas linhas das Figuras 14–15 e do
  Quadro 8.
- **";" nas listas** (itens 2, 32, 33, 39, 40, 44, 119): seções 2.2, 4.2, 6.3, 7.3, 10.4 e 12.
- **Fórmulas** (itens 36, 37): Equações 1–3 (média, desvio-padrão, limiar) e 4 (MASE).
- **Série esparsa explicada** (item 35), **Introdução reescrita** (item 31) e **Resumo
  reestruturado** (itens 6–8).
- **Trocas pontuais de palavra** dos Capítulos 11 e 12 (itens 47–119): todas estão aplicadas.

---

## 2. Pedidos do orientador que ainda precisam de ação

### 2.1 Coverage sem explicação — item 17 (Abstract, p. 3; Resumo, p. 2)

O orientador perguntou, sobre "coverage… 100%": *"Of precision or effectiveness?"*. A frase
continua sem dizer o que é a cobertura. Sugestão:

- **Resumo**: "A cobertura do intervalo de predição, isto é, a proporção de dias em que a venda
  real ficou dentro da faixa prevista, ficou entre 90,5% e 100%, próxima do nível nominal de
  95%."
- **Abstract**: "The prediction-interval coverage, that is, the share of days in which actual
  sales fell within the forecast range, ranged from 90.5% to 100%, close to the nominal 95%."

No mesmo parágrafo há dois problemas:

- "**entre 91% a 100%**": o certo é "entre … **e** …" ou "**de** … a …".
- **O número não bate com o Capítulo 11**: Resumo e Abstract dizem 91%, mas a Tabela 4 e as
  Seções 11.6 e 11.7 dizem **90,5%** (JC, Produtos de jardim). Usar 90,5% nos dois.

### 2.2 Palavras-chave — itens 10, 11 e 19 (p. 2 e 3)

- **"Previsão de demanda"** foi mantida, e está certa: é o termo da área, *demand forecasting*.
  "Previsão sob/por demanda" mudaria o sentido. Vale responder isso ao orientador, já que ele
  pediu para verificar.
- **"Varejo de floricultura" / "Floriculture retail"**: o orientador sugeriu "atacado e varejo".
  As encomendas grandes (venda para empresas) existem, mas ficam fora da previsão. Por isso
  "varejo" é defensável, mas a decisão precisa ser consciente. Se quiserem "valorizar o
  alcance", como ele pediu, uma opção é "Varejo de produtos perecíveis" / "Perishable goods
  retail".

### 2.3 Primeira frase da 11.3 — item 46 (p. 49)

Hoje: "Na execução do grupo de scripts de teste para validar o comportamento e a estabilidade de
um software, de 11 de novembro de 2026, os 196 testes…". A frase ficou longa, e "de um software"
soa genérico. Sugestão: "**Na execução da suíte de testes automatizados, em 11 de novembro de
2026, os 196 testes…**".

### 2.4 "trata igualmente de lojas" — item 58 (p. 53)

Na leitura do comentário, o "de" inserido já era incerto. "Tratar **de**" significa "abordar",
então a frase fica com outro sentido. Sugestão: "**mas trata da mesma forma lojas com pedidos de
tamanhos diferentes**".

### 2.5 Tamanho das figuras — itens 42 e 43 (p. 35 e 36)

As Figuras 6 e 7 estão maiores no Corrigido. Falta só conferir no Word final se o texto do DER
ficou legível na impressão. As Figuras 2–5 (p. 31–34) também têm letra muito pequena; o mesmo
pedido vale para elas, se couber.

---

## 3. Problemas novos, fora dos comentários

Estes problemas foram encontrados na leitura do Corrigido. Entram no "faça uma correção
minuciosa de todo o texto" do orientador (item 1).

### 3.1 Contradições de conteúdo (prioridade alta)

1. **Frequência de retreinamento**. As passagens se contradizem:
   - O **Quadro 7** (p. 51), linha E7, diz "retreinamento **semanal**".
   - O texto do E7 (p. 55) diz que o sistema "é retreinado **mensalmente**, a cada exportação das
     planilhas do mês".
   - A 2.2 (p. 14) fala em envio semanal.
   - No repositório (CLAUDE.md, ADR-021), a regra é retreinar a cada planilha semanal.

   É preciso escolher uma regra e alinhar o Quadro 7, o E7 e a 2.2.

2. **Publicação da API desatualizada (ADR-024, 16/11)**. A API passou do Render para o Azure
   Container Apps, com o treino num job disparado pelo botão. O texto ainda descreve o Render
   grátis e o treino por *script* da equipe técnica em vários pontos:
   - 6.6 (p. 26): "API no serviço Render";
   - Quadro 5 (p. 37): "Docker, Render, Vercel";
   - 10.3 (p. 46): "forma utilizada na produção, porque o plano gratuito…";
   - 10.4 c (p. 46);
   - 11.8, último parágrafo (p. 58): "o treinamento fora da API publicada, que exige um *script*…".

   Há duas saídas: atualizar esses pontos para o Azure ou deixar claro que o relatório descreve
   a versão anterior ao ADR-024. Se for atualizar, a limitação da 11.8 deixa de existir.

3. **5.3, último parágrafo (p. 18)**: diz que a desagregação perdeu para "a previsão individual
   das séries de vendas dos produtos da categoria de gramas". O experimento (E4) comparou a
   desagregação loja → categoria com o modelo direto **de cada categoria**, e não com produtos de
   grama. Sugestão: "…foram inferiores aos da previsão direta de cada categoria (Seção 11.5,
   E4)."

4. **Figura 10 × 11.3**:
   - A Figura 10 (p. 44) mostra **12.410** vendas novas e **0** já carregadas.
   - A 11.3 (p. 49) relata **12.388** novas e **22** já carregadas para "a planilha de teste".

   São bases diferentes (demonstração × cópia da base real), mas o leitor vai achar que é a
   mesma planilha. Dizer isso explicitamente em uma das duas passagens.

### 3.2 Referências e siglas (ABNT)

1. **Referências não citadas no texto**: ABNT exige que toda referência listada seja citada.
   Hoje 11 não aparecem no corpo do texto:
   - Bartezzaghi e Verganti (1995)
   - Chen e Liu (1993)
   - Croston (1972)
   - Diebold e Mariano (1995)
   - Gross e Sohl (1990)
   - Holm (1979)
   - Kalchschmidt, Verganti e Zotteri (2006)
   - Kwiatkowski *et al.* (1992)
   - Schwert (1989)
   - Syntetos e Boylan (2005)
   - Teunter, Syntetos e Babai (2011)

   A saída é citar cada uma onde fizer sentido ou removê-la da lista. Por exemplo:
   - Croston e Syntetos e Boylan (2005) na 5.3;
   - Kwiatkowski e Schwert no E5;
   - Gross e Sohl no E4;
   - Holm no E8.
2. **Siglas sem uso**: ADF, KPSS, MAPE, WAPE e ARIMA estão na lista de siglas, mas não aparecem
   no texto. Remover da lista ou usar no texto, por exemplo KPSS/ADF no E5.
3. **5.4 (p. 18)**: o critério "média + 4 desvios" está atribuído a Iglewicz e Hoaglin (1993).
   Esse livro recomenda o escore-z modificado pela mediana e pelo MAD e critica justamente média
   e desvio. Vale reformular, por exemplo: "critério baseado em média e desvio-padrão, discutido
   por…", ou justificar o 4s pelo experimento E2.
4. **KWIATKOWSKI, D. et al.** deve ter o "*et al.*" em itálico, como em BOX.

### 3.3 Redação e revisão gramatical

| Página | Trecho atual | Correção |
| --- | --- | --- |
| 22 (6.1) | "A análise dos dados e a modelagem preditiva **foi marcada com** as fases de…" | "…**foram organizadas segundo** as fases do CRISP-DM: compreensão do negócio…". Hoje o CRISP-DM não é nomeado |
| 22 (6.1) | "oito iterações, entre abril e novembro de 2026 **e encerrada** com uma entrega" | "…de 2026, **cada uma encerrada** com uma entrega…" |
| 26 (6.5) | "…as três ocorrências mais recentes da data**..**" | ponto duplo → um ponto |
| 53 (E3) | "A solução foi descartada e **adotamos** a escala original" | o resto do texto é impessoal: "…descartada, e **adotou-se** a escala original" |
| 2 / 54 / 58 / 59 | o mesmo intervalo aparece como "intervalo de predição", "intervalo de previsão", "intervalo de confiança" e "faixa provável" | escolher um termo técnico e mantê-lo em todo o texto. A "faixa provável" pode ficar só para a tela. O orientador pediu "intervalos de confiança" na conclusão, mas tecnicamente é intervalo de **previsão** |
| 27 (6.6) | "Mean Absolute Error", "walk-forward" sem itálico | itálico, como no resto do texto |
| 23–24 (6.3) | itálico irregular nos nomes: *FastAPI*, *pandas*, *Recharts* em itálico; seaborn, Vite, python-jose, Playwright, Neon sem itálico | padronizar: todos os nomes de software em itálico, ou nenhum |

### 3.4 Notas das tabelas

- **Tabela 4** (p. 56): explicar na nota o "–" de *JC, Grama Preta Pelo de Urso (bandeja)*,
  "sem venda no período de validação". Definir também "Erro relativo": "erro do modelo ÷ erro da
  previsão ingênua; abaixo de 1, o modelo erra menos".
- As notas das Tabelas 2, 3 e 4 estão destacadas em cor no PDF (ver o início deste documento).

---

## 4. Ordem sugerida

1. Itens de conteúdo da §3.1 (retreinamento, Azure, 5.3, Figura 10).
2. Resumo e Abstract (§2.1, §2.2).
3. Referências e siglas (§3.2).
4. Redação (§2.3, §2.4, §3.3) e notas das tabelas (§3.4).
5. Tirar os destaques coloridos, passar o corretor gramatical no texto inteiro (item 1) e, por
   último, atualizar o Sumário e as listas no Word (as mudanças acima podem mudar a paginação).
