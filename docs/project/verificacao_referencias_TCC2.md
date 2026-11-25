# Verificação das referências — TCC2 Relatório Técnico (Corrigido)

Data: 22/11/2026. Um subagente por referência (24), com pesquisa na web (Crossref, editoras,
RePEc, repositórios, otexts.com, planalto.gov.br). Cada um conferiu os dados bibliográficos e se
a obra sustenta cada trecho em que é citada. Nenhum arquivo do artigo foi alterado.

**Limite da verificação:** a maior parte dos artigos é paga; em 15 das 24 obras os agentes leram
só o resumo, os metadados e fontes secundárias. Foram lidos por inteiro apenas o fpp3 (Hyndman e
Athanasopoulos), o preprint do MASE (Hyndman e Koehler), o working paper de Schwert, o texto da
LGPD e o PLOS ONE de 2018 (Makridakis et al.).

Veredito: **S** sustenta · **SP** sustenta parcialmente · **NS** não sustenta.

## 1. Dados bibliográficos

Nenhuma referência é inexistente ou tem autor, título, periódico, volume, número, páginas ou ano
errado. Ajustes de forma:

| Referência | Ajuste |
| --- | --- |
| BRASIL (LGPD) | A NBR 6023 pede a **ementa** da lei, que falta: "Dispõe sobre a proteção de dados pessoais e altera a Lei nº 12.965, de 23 de abril de 2014 (Marco Civil da Internet)." Pode entrar "n. 157" antes de "p. 59". |
| PRESSMAN; MAXIM | O selo da edição de 2021 aparece como AMGH (biblioteca da UVV) e como Bookman (Minha Biblioteca), ambos do Grupo A. Conferir na folha de rosto. |
| BOX et al. | A Wiley dá 2015; o copyright impresso é c2016. Manter 2015. "et al." é aceito (a NBR recomenda listar os 4 autores: Box, Jenkins, Reinsel, Ljung). |
| SOMMERVILLE | Correto. A ficha catalográfica traz "Pearson Education do Brasil" (a forma "Pearson" também é aceita). |
| Todas as de periódico | Os DOIs existem e podem ser acrescentados (lista no §4). Só Arunraj traz DOI hoje. |

## 2. Trechos que precisam de ajuste (por gravidade)

### NS — a obra não diz o que o texto atribui a ela

> **Corrigido no DOCX/PDF em 22/11/2026** (itens 1 a 4, com a redação sugerida; as 3 obras continuam
> nas Referências, citadas nos trechos sustentados). Script:
> `.claude/skills/artigo-tcc/exemplos/atas_apendice_2026-11-21/editar_sem_sustentacao.py`.

1. **P182 (5.3) — Syntetos, Boylan e Croston (2005)**: "mostraram que o intervalo entre as
   vendas e a variabilidade do seu tamanho permitem identificar as séries para as quais um
   modelo convencional é adequado". A classificação serve para escolher entre suavização
   exponencial simples, Croston e SBA (pelo erro quadrático médio teórico); a obra não trata de
   "modelo convencional" nem de ARIMA. Sugestão: "Syntetos, Boylan e Croston (2005) classificaram
   a demanda pelo intervalo médio entre vendas e pela variabilidade do tamanho das vendas, com o
   objetivo de escolher, em cada classe, entre a suavização exponencial simples, o método de
   Croston e a sua versão corrigida."
2. **P385 (11.4) — Syntetos, Boylan e Croston (2005)**: "apresentam demanda errática, padrão
   adequado a modelos como o SARIMAX". A classe errática está certa (EDA: vendem quase todo dia,
   ADI ≈ 1,2), mas "adequado ao SARIMAX" é conclusão do trabalho, não da obra. Sugestão: "...com
   ADI de aproximadamente 1,2, abaixo do corte de 1,32, o que as coloca no grupo de demanda
   errática. Como há venda na maioria dos dias, essas séries foram modeladas com o SARIMAX..."
3. **P302 (8.6) — Hyndman e Athanasopoulos (2021)**: "em negócios com variação sazonal elevada, o
   monitoramento contínuo do desempenho é indispensável". O livro (seção 1.7) só diz que o
   desempenho só pode ser avaliado depois que os dados do período previsto chegam. Sugestão: "O
   desempenho de um modelo só pode ser avaliado de forma adequada depois que as vendas do período
   previsto ficam disponíveis (HYNDMAN; ATHANASOPOULOS, 2021). Por isso, cada treinamento
   registra..."
4. **Quadro 5.7, linha de Huber, Gossmann e Stuckenschmidt (2017)**: "Estudo metodológico, sem
   ferramenta operacional". A obra propõe um sistema de apoio à decisão para as operações diárias
   de uma rede de padarias. Sugestão: "Sistema de apoio à decisão avaliado com dados de uma rede de
   padarias; setor e produto diferentes (pães vendidos no mesmo dia)."

### SP — a ideia está na obra, mas o texto vai além dela

5. **P157 (3) — Makridakis, Spiliotis e Assimakopoulos (2020), M4**: "métodos estatísticos
   superaram, em média, abordagens de aprendizado de máquina em séries com histórico reduzido
   [...], como os 26 meses disponíveis". Na M4, os seis métodos só de aprendizado de máquina foram
   mal, mas o vencedor foi um híbrido (suavização exponencial + rede neural) e a M4 não fala de
   "histórico reduzido". Essa ideia está em Makridakis, Spiliotis e Assimakopoulos (2018, PLOS ONE),
   com séries mensais de 81 a 126 pontos; 26 meses de dados diários (~790 dias) não são histórico
   curto nesse sentido. Sugestão: "...se apoia na competição M4, com 100 mil séries, 4.227 delas
   diárias. Nela, os métodos puramente de aprendizado de máquina tiveram erro maior que uma
   combinação simples de suavizações exponenciais, e os métodos mais precisos foram combinações de
   modelos estatísticos ou híbridos com redes neurais (MAKRIDAKIS; SPILIOTIS; ASSIMAKOPOULOS,
   2020)." Retirar "como os 26 meses disponíveis".
6. **P157 e RNF04 — LGPD**: "em conformidade com a LGPD, pois não armazena os dados pessoais de
   clientes" e "proteção dos dados operacionais [...] em conformidade com a LGPD". A LGPD protege
   dados pessoais (não dados operacionais); ler a planilha já é tratamento (art. 5º, X), e o
   sistema guarda e-mails de usuários. Sugestões: "Segundo o princípio da necessidade da LGPD
   (BRASIL, 2018, art. 6º, III), o sistema não grava os dados de clientes, vendedores e operadores
   presentes nos relatórios." e, no RNF04, "...proteger os dados operacionais da empresa e os dados
   pessoais que guarda (e-mail e senha dos usuários), conforme o art. 46 da LGPD (BRASIL, 2018)."
7. **P186 (5.4) — Bartezzaghi e Verganti (1995); Kalchschmidt, Verganti e Zotteri (2006)**:
   "Pedidos grandes de poucos clientes podem ser tratados como um fluxo de demanda à parte". Nenhuma
   das duas separa pedidos pelo **tamanho**: Bartezzaghi e Verganti planejam a demanda irregular de
   poucos clientes pedido a pedido (order overplanning); Kalchschmidt et al. agrupam **clientes**
   pelo padrão de demanda e preveem cada grupo à parte, em empresas industriais. Sugestão: "Quando a
   demanda irregular vem de poucos clientes, ela pode ser planejada pedido a pedido, e não por uma
   série agregada (BARTEZZAGHI; VERGANTI, 1995), e clientes com padrões de demanda diferentes podem
   ser previstos em separado (KALCHSCHMIDT; VERGANTI; ZOTTERI, 2006). Neste trabalho, a separação é
   feita pelo tamanho do pedido."
8. **P183 (5.3) — Fliedner (2001); Zotteri e Kalchschmidt (2007)**: as duas sustentam prever no
   agregado e repartir (top-down). Não confirmado: que os níveis agregados "tendem a ser mais
   regulares" (atribuído na literatura a Fliedner, 1999) e o uso para séries esparsas. Zotteri e
   Kalchschmidt tratam de um item em várias lojas, com demanda estacionária. Sugestão: "...uma
   alternativa é a previsão hierárquica, que organiza a demanda em níveis de agregação, como loja,
   categoria e produto (FLIEDNER, 2001). Na estratégia top-down, a previsão é feita no nível
   agregado e depois repartida entre os componentes. A escolha entre prever no detalhe ou no
   agregado depende da variabilidade da demanda e de quanto os componentes diferem entre si
   (ZOTTERI; KALCHSCHMIDT, 2007)."
9. **P184 (5.3) — Gross e Sohl (1990)**: "repartida [...] pela participação recente de cada uma".
   Os métodos de Gross e Sohl usam proporções do histórico inteiro; a janela recente (4–8
   semanas) e o perfil do dia da semana são adaptação do trabalho. Sugestão: "...repartida entre as
   categorias por proporções históricas, como em Gross e Sohl (1990), aqui calculadas sobre as
   últimas semanas e combinadas com o perfil do dia da semana."
10. **P406 (11.5) — Kwiatkowski et al. (1992)**: a falta de poder nas séries de baixo volume e os
    2,5% são resultados do trabalho, mas a frase parece atribuí-los à obra; e o KPSS é teste de
    estacionariedade (hipótese nula), não "de raiz unitária". Sugestão: "Os testes de
    estacionariedade e de raiz unitária serviram apenas de apoio: o KPSS (KWIATKOWSKI et al.,
    1992), cuja hipótese nula é a estacionariedade, indicou d = 1 nas séries em que o nível das
    vendas muda ao longo do tempo, mas, neste trabalho, não decidiu as séries de baixo volume, e
    usá-lo como critério reduziu o erro em apenas 2,5%; ..."
11. **P406 — Schwert (1989)**: "termo de médias móveis próximo de −1". Na notação de Schwert
    (1 − θL), o caso problemático é θ ≈ +1; "−1" só vale na notação do statsmodels (1 + θL), que o
    texto não diz. Sugestão: "...quando a série diferenciada tem um termo de médias móveis forte,
    que quase cancela a raiz unitária (SCHWERT, 1989)..."
12. **P414 (11.5) — Diebold e Mariano (1995)**: o código usa a variância de longo prazo EWC de
    Lazarus et al. (2018) com valor crítico t, não a do artigo original, e a melhor janela foi
    escolhida no próprio período testado, o que deixa os valores de p otimistas (a correção de Holm
    cobre as 23 séries, não as 6 janelas). Mínimo sugerido: acrescentar "Como a melhor janela foi
    escolhida no próprio período avaliado, esses valores de p tendem a ser otimistas." Citar o EWC
    exigiria incluir Lazarus et al. (2018) nas referências (dados não conferidos).
13. **P193–P195 (5.5) — Hyndman e Koehler (2006)**: o MASE de 2006 usa a previsão ingênua de 1
    passo (m = 1); a forma sazonal da Equação 4 (m = 7) está no fpp3. E o denominador é o erro da
    ingênua no **treino**, diferente da previsão ingênua da validação. Sugestão: "...proposto por
    Hyndman e Koehler (2006), divide o erro do modelo pelo erro médio, no histórico de treinamento,
    de uma previsão ingênua. Na versão sazonal (HYNDMAN; ATHANASOPOULOS, 2021), adotada neste
    trabalho, conforme a Equação 4:"
14. **P196 (5.5) — Hyndman e Athanasopoulos (2021)**: o livro avalia intervalos pelo escore de
    Winkler (largura + penalidade), não por "cobertura empírica". Sugestão: "Os intervalos são
    avaliados pela largura e pelos valores reais que ficam fora deles (HYNDMAN; ATHANASOPOULOS,
    2021). Neste trabalho, as duas partes são reportadas em separado: a cobertura empírica e a
    largura média."
15. **P176 — Hyndman e Athanasopoulos (2021)**: o livro não fala de "aprendizado de máquina" nem de
    gestão de operações. Sugestão: "A previsão de demanda reúne modelos estatísticos que representam
    tendência, sazonalidade e o efeito de variáveis externas, além de modelos não lineares como as
    redes neurais (HYNDMAN; ATHANASOPOULOS, 2021)."
16. **P177 (5.1) — Box et al. (2015)**: "A seleção dos parâmetros do modelo é realizada pela
    minimização do AIC". O AIC escolhe as **ordens** (os parâmetros saem da máxima verossimilhança),
    é de Akaike (1974), não do método de Box-Jenkins, e no sistema o d sai do walk-forward.
    Sugestão: "Neste trabalho, as ordens p, q, P e Q são escolhidas pelo menor AIC, critério que
    pesa o ajuste contra o número de parâmetros, e a ordem de diferenciação d pelo menor erro na
    validação walk-forward."
17. **P180 e P392 — Arunraj, Ahrens e Fernandes (2016)**: o ganho sobre o SARIMA vem do conjunto
    de exógenas, que inclui **promoções** além de feriados. Sugestão (P392): "...coerente com o
    ganho obtido por Arunraj, Ahrens e Fernandes (2016) ao incluir feriados e promoções como
    variáveis externas do SARIMA."
18. **P157 — Huber et al. (2017)**: citada como estudo de "modelos com regressores exógenos"; o
    resumo fala de ARIMA multivariado diário, sem confirmar regressores exógenos.
19. **P198 e P302 — Pressman e Maxim (2021); Sommerville (2018)**: "separar as regras de negócio
    dos mecanismos de entrada e saída" é formulação da arquitetura hexagonal/limpa; os livros falam
    de modularidade, separação de interesses, coesão e acoplamento. "Determinantes" é mais forte que
    os livros. Sugestão (P302): "...a arquitetura escolhida influencia atributos não funcionais do
    sistema, como a manutenibilidade, e a verificação e a validação dão confiança de que o software
    atende ao que se espera dele (SOMMERVILLE, 2018; PRESSMAN; MAXIM, 2021)."

### Ajustes de redação opcionais (uso sustentado)

- **P201 — Taylor e Letham (2018)**: "desenvolvido por" é aceitável; mais preciso: "ferramenta de
  código aberto desenvolvida na Facebook e descrita por Taylor e Letham (2018)".
- **P186 — Chen e Liu (1993)**: sustentado; a obra acrescenta que o efeito na previsão pontual é
  forte sobretudo quando a observação atípica está perto da origem da previsão.
- **P182 — Croston (1972); Syntetos e Boylan (2005); Teunter, Syntetos e Babai (2011)**:
  sustentado. Pode nomear as variações: "como o SBA, que corrige o viés do método de Croston
  (SYNTETOS; BOYLAN, 2005), e o TSB, que atualiza a probabilidade de venda a cada período
  (TEUNTER; SYNTETOS; BABAI, 2011)".
- **Terminologia**: o texto chama de "irregular" (P182, P385, P425) o que a classificação chama de
  *intermittent* (intermitente) ou *lumpy*; a definição do P182 ("a maior parte dos períodos sem
  venda e tamanho variável") descreve o *lumpy*, e o corte ADI > 1,32 é bem menos que "a maior
  parte dos períodos". Vale unificar.

## 3. Citações que faltam

- **Ljung-Box e Shapiro-Wilk** (P245, P423) aparecem sem fonte. Candidatas, a conferir:
  LJUNG, G. M.; BOX, G. E. P. On a measure of lack of fit in time series models. Biometrika, v. 65,
  n. 2, p. 297-303, 1978. SHAPIRO, S. S.; WILK, M. B. An analysis of variance test for normality
  (complete samples). Biometrika, v. 52, n. 3-4, p. 591-611, 1965.
- Se as sugestões dos itens 5, 12 e 16 forem usadas: Makridakis, Spiliotis e Assimakopoulos (2018,
  PLOS ONE, v. 13, n. 3, e0194889, DOI 10.1371/journal.pone.0194889 — conferida pelo agente),
  Lazarus et al. (2018) e Akaike (1974) — estas duas não conferidas.

## 4. Sustentadas sem ressalva

Croston (1972), Syntetos e Boylan (2005), Teunter, Syntetos e Babai (2011), Holm (1979), Chen e
Liu (1993), Taylor e Letham (2018); Hyndman e Athanasopoulos (2021) em P137, P178 e P180;
Arunraj et al. (2016) em P157, P200 e no quadro; Huber et al. (2017) em P200; Sommerville (2018)
em P198; LGPD na lista de siglas; Box et al. (2015) quanto a Box-Jenkins, sazonalidade e
regressores; Syntetos, Boylan e Croston (2005) quanto ao critério ADI/CV² e aos cortes.

## 5. DOIs

| Referência | DOI |
| --- | --- |
| Arunraj; Ahrens; Fernandes (2016) | 10.4018/IJORIS.2016040101 (já na referência) |
| Bartezzaghi; Verganti (1995) | 10.1016/0925-5273(95)00047-8 |
| Chen; Liu (1993) | 10.1002/for.3980120103 |
| Croston (1972) | 10.1057/jors.1972.50 |
| Diebold; Mariano (1995) | 10.1080/07350015.1995.10524599 |
| Fliedner (2001) | 10.1108/02635570110365952 |
| Gross; Sohl (1990) | 10.1002/for.3980090304 |
| Holm (1979) | sem DOI (JSTOR 4615733) |
| Huber; Gossmann; Stuckenschmidt (2017) | 10.1016/j.eswa.2017.01.022 |
| Hyndman; Koehler (2006) | 10.1016/j.ijforecast.2006.03.001 |
| Kalchschmidt; Verganti; Zotteri (2006) | 10.1108/01443570610666975 |
| Kwiatkowski et al. (1992) | 10.1016/0304-4076(92)90104-Y |
| Makridakis; Spiliotis; Assimakopoulos (2020) | 10.1016/j.ijforecast.2019.04.014 |
| Schwert (1989) | 10.1080/07350015.1989.10509723 |
| Syntetos; Boylan (2005) | 10.1016/j.ijforecast.2004.10.001 |
| Syntetos; Boylan; Croston (2005) | 10.1057/palgrave.jors.2601841 |
| Taylor; Letham (2018) | 10.1080/00031305.2017.1380080 |
| Teunter; Syntetos; Babai (2011) | 10.1016/j.ejor.2011.05.018 |
| Zotteri; Kalchschmidt (2007) | 10.1016/j.ijpe.2006.12.030 |
