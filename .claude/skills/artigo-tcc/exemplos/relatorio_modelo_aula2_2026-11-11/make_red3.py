# -*- coding: utf-8 -*-
"""Terceira redução (alvo ~60 páginas), sobre conteudo_red.py."""
src = open("conteudo_red.py", encoding="utf-8").read()


def between(s, a, b, new):
    i, j = s.index(a), s.index(b)
    assert i < j, (a, b)
    return s[:i] + new + s[j:]


def rep(s, a, b):
    assert a in s, a[:80]
    return s.replace(a, b)


CAP1 = r'''h1("1 INTRODUÇÃO")
cp("A previsão de demanda pode apoiar o planejamento de compras")
p("A Floricultura Verde Perto atua no varejo de flores, plantas, grama e produtos de jardinagem, com unidades em "
  "Jardim Canadá, em Nova Lima, e em Itabirito, em Minas Gerais. O planejamento das compras é feito com base na "
  "experiência da equipe e em relatórios do sistema de gestão da empresa, que registram as vendas realizadas, mas "
  "não estimam as vendas futuras. A procura varia com o dia da semana, com a época do ano e com datas "
  "comemorativas, como o Dia das Mães e o Dia dos Namorados, e difere entre os produtos e as unidades, o que "
  "dificulta definir as quantidades a adquirir de produtos que perdem valor em poucos dias.")
p("Para atender a essa necessidade, foi desenvolvido um sistema de previsão de vendas que utiliza o histórico de "
  "vendas e o calendário de cada unidade para estimar quanto se espera vender em cada dia das semanas seguintes, em "
  "cada uma das quatro categorias de produto e em cada produto de grama das duas unidades. A gestora de compras "
  "envia as planilhas exportadas do sistema de gestão, confere-as antes da gravação e solicita o treinamento dos "
  "modelos, e o sistema apresenta, em um painel acessível pelo navegador, a previsão diária com uma faixa provável "
  "de venda, o histórico das previsões, análises das vendas e relatórios. O sistema informa quanto se espera vender, "
  "e a decisão de compra permanece com a empresa.")
p("A solução se justifica pela perecibilidade dos produtos, que torna custosos tanto o excesso quanto a falta de "
  "estoque, e pela existência de 26 meses de histórico de vendas, de janeiro de 2024 a fevereiro de 2026, até então "
  "utilizado apenas para consulta. O desenvolvimento seguiu uma metodologia iterativa e incremental, validada com a "
  "entidade parceira em oito reuniões, e a análise dos dados seguiu as fases do modelo CRISP-DM. Após esta "
  "introdução, os Capítulos 2 a 4 apresentam a problematização, a justificativa e os objetivos, o Capítulo 5, o "
  "referencial teórico, e o Capítulo 6, as metodologias adotadas. Os Capítulos 7 a 10 tratam dos requisitos, da "
  "modelagem, da prototipação e da implementação, o Capítulo 11 apresenta e discute os resultados, e o Capítulo 12 "
  "traz a conclusão e os trabalhos futuros.")

'''
src = between(src, 'h1("1 INTRODUÇÃO")', 'h1("2 PROBLEMATIZAÇÃO")', CAP1)

CAP3 = r'''h1("3 JUSTIFICATIVA")
p("A importância do trabalho decorre do efeito das decisões de compra sobre produtos perecíveis: flores e plantas "
  "têm vida útil curta e demanda sujeita a datas comemorativas, e a compra acima ou abaixo da demanda resulta em "
  "descarte ou em vendas perdidas. Ao transformar o histórico de vendas em previsões diárias, acompanhadas de medidas "
  "de incerteza e de desempenho, o sistema oferece à empresa uma base quantitativa para a compra, que até então "
  "dependia apenas da experiência da equipe. Para os autores, o trabalho representou a oportunidade de aplicar a um "
  "problema real os conhecimentos de engenharia de software, de banco de dados e de ciência de dados do curso.")
p("Do ponto de vista técnico e acadêmico, a principal contribuição é a aplicação de modelos estatísticos de séries "
  "temporais com regressores exógenos, isto é, com variáveis externas que ajudam a explicar as vendas, à previsão de "
  "demanda no setor de floricultura. Os estudos que fundamentam essa abordagem concentram-se no varejo de alimentos "
  "perecíveis (ARUNRAJ; AHRENS; FERNANDES, 2016; HUBER; GOSSMANN; STUCKENSCHMIDT, 2017), e a escolha de um modelo "
  "estatístico como modelo central é sustentada pela competição M4, em que métodos estatísticos superaram, em média, "
  "abordagens de aprendizado de máquina em séries com histórico reduzido (MAKRIDAKIS; SPILIOTIS; ASSIMAKOPOULOS, "
  "2020), como os 26 meses disponíveis. Do ponto de vista administrativo, o sistema reúne em uma base única as vendas "
  "das duas unidades, elimina a consolidação manual das planilhas e preserva as previsões feitas para cada dia, em "
  "conformidade com a Lei Geral de Proteção de Dados Pessoais (LGPD) (BRASIL, 2018), pois não armazena os dados "
  "pessoais de clientes presentes nos relatórios.")
p("A viabilidade apoiou-se na disponibilidade dos dados, na participação da entidade parceira, que forneceu o "
  "histórico de vendas e participou de oito reuniões, e em ferramentas de código aberto ou com planos gratuitos. A "
  "solução é oportuna porque a empresa já mantinha o histórico de vendas, mas não dispunha de meios para utilizá-lo "
  "no planejamento, e manifestou, desde a primeira reunião, o interesse em uma ferramenta que considerasse as datas "
  "comemorativas e fosse atualizada semanalmente. A contribuição social está na redução do desperdício de produtos "
  "perecíveis e na maior disponibilidade dos produtos procurados pelos clientes.")

'''
src = between(src, 'h1("3 JUSTIFICATIVA")', 'h1("4 OBJETIVOS")', CAP3)

CAP4 = r'''h1("4 OBJETIVOS")
h2("4.1 Objetivo Geral")
p("Desenvolver um sistema de previsão de vendas para a Floricultura Verde Perto, baseado em dados históricos e "
  "em modelos estatísticos de séries temporais com regressores exógenos de calendário, que forneça a previsão "
  "diária da demanda de cada categoria de produto e de cada produto de grama das unidades da empresa, de modo a "
  "apoiar as decisões de compra.")
h2("4.2 Objetivos Específicos")
p("Para alcançar o objetivo geral, foram cumpridas as seguintes etapas:")
ul("levantados e validados, junto à entidade parceira, os requisitos, as regras de negócio e os atores do sistema,",
   "definidas a arquitetura e a modelagem do sistema, em diagramas UML, modelo de dados e arquitetura lógica,",
   "estruturado o ⟨pipeline⟩ que leva as planilhas de vendas até a base de dados, com deduplicação, padronização, "
   "classificação dos produtos em categorias e separação das encomendas grandes,",
   "realizada a análise exploratória dos dados históricos e construído o calendário diário de cada unidade, com dias "
   "de loja fechada, aberturas excepcionais e o efeito das datas comemorativas,",
   "treinados modelos estatísticos de séries temporais com regressores exógenos para cada categoria e para cada "
   "produto de grama de cada unidade, com seleção automática da ordem pelo Critério de Informação de Akaike (AIC),",
   "comparadas experimentalmente configurações de modelagem e avaliado o desempenho dos modelos por validação "
   "⟨walk-forward⟩, com métricas de erro e com a cobertura do intervalo de 95%,",
   "implementados a interface de programação, o serviço de previsão e o painel interativo,",
   "validado o software por testes automatizados e por demonstrações à entidade parceira,",
   "produzida a documentação técnica da solução.")

'''
src = between(src, 'h1("4 OBJETIVOS")', 'h1("5 REFERENCIAL TEÓRICO")', CAP4)

# 6.1: sem o quadro de iterações
NEW61 = r'''p("O projeto foi organizado em oito iterações, entre abril e novembro de 2026, cada uma associada a uma ou mais "
  "fases do CRISP-DM e encerrada com uma entrega verificável, do levantamento dos requisitos à documentação final. "
  "Como prevê o CRISP-DM, os resultados da avaliação podiam levar de volta à preparação dos dados, como ocorreu com o "
  "tratamento das encomendas grandes, e as decisões técnicas de cada iteração foram registradas em documentos de "
  "decisão arquitetural.")
'''
src = between(src, 'cp("O projeto foi organizado em oito iterações', 'h2("6.2 Levantamento e Análise de Requisitos")', NEW61)
src = rep(src, 'fig("etapas", os.path.join(MED, "image2.png"), 13.0,', 'fig("etapas", os.path.join(MED, "image2.png"), 12.0,')
# 6.6: sem a frase repetida sobre aceitação
src = rep(src, '"o painel no navegador conectado à API. Os testes de aceitação foram realizados com a entidade parceira, nas "\n'
               '  "demonstrações do protótipo e das versões do sistema.")',
          '"o painel no navegador conectado à API.")')

# 8: figuras menores
for a, b in [('"casos_uso.png"), 11.0,', '"casos_uso.png"), 10.0,'), ('"image4.png"), 7.5,', '"image4.png"), 7.0,'),
             ('"image5.png"), 12.5,', '"image5.png"), 12.0,'), ('"sequencia.png"), 10.5,', '"sequencia.png"), 9.5,'),
             ('"image6.png"), 12.5,', '"image6.png"), 12.0,'), ('"image7.png"), 6.5,', '"image7.png"), 6.2,'),
             ('"p_previsao.jpg"), 13.5,', '"p_previsao.jpg"), 12.0,'),
             ('"t_inicio_top.png"), 13.0,', '"t_inicio_top.png"), 12.0,'), ('"t_conferencia.png"), 13.0,', '"t_conferencia.png"), 12.0,'),
             ('"t_previsao_top.png"), 13.0,', '"t_previsao_top.png"), 12.0,'), ('"t_historico.png"), 13.0,', '"t_historico.png"), 12.0,'),
             ('"t_relatorios.png"), 12.0,', '"t_relatorios.png"), 11.0,')]:
    src = rep(src, a, b)

# 9.3 mais curta
NEW93 = r'''h2("9.3 Validação dos Protótipos com Usuários/Entidade")
p("O protótipo foi apresentado à entidade parceira nas reuniões de 26 de maio e de 2 de junho de 2026, esta junto "
  "com a prova de conceito do modelo de previsão, quando a empresa considerou os resultados satisfatórios e "
  "solicitou ajustes na interface. A validação definiu o escopo do sistema final: a tela Produtos para Repor foi "
  "retirada, porque a empresa não dispõe do estoque atual dos produtos, a Previsão de Compras passou a apresentar a "
  "previsão de vendas, pois a decisão de compra permanece com a empresa, e a simulação de promoções ficou como "
  "trabalho futuro. As versões seguintes, já com os dados reais, foram aprovadas nas reuniões de 13 e 20 de outubro "
  "e de 10 de novembro de 2026.")

'''
src = between(src, 'h2("9.3 Validação dos Protótipos com Usuários/Entidade")', 'h1("10 IMPLEMENTAÇÃO")', NEW93)

# 11.5: tabelas de agregação, diferenciação e janela saem (números no texto)
src = rep(src, '(GROSS; SOHL, 1990), ambos sobre o fluxo diário ({tab:e8}).', '(GROSS; SOHL, 1990), ambos sobre o fluxo diário.')
src = rep(src, 'março de 2025 a fevereiro de 2026 ({tab:e9}).', 'março de 2025 a fevereiro de 2026.')
src = rep(src, 'o teste de Diebold e Mariano (1995) e o ajuste de Holm (1979) para as 23 séries ({tab:e12}).',
          'o teste de Diebold e Mariano (1995) e o ajuste de Holm (1979) para as 23 séries.')
for key in ("e8", "e9", "e12"):
    i = src.index(f'tcopy("{key}", "tab",')
    j = src.index("\n", src.index('"Fonte:', i)) + 1 if '"Fonte:' in src[i:i + 900] else src.index("\n", i) + 1
    # remove até o fim da chamada tcopy (linha que termina com ')')
    k = i
    depth = 0
    while True:
        ch = src[k]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        k += 1
    src = src[:i] + src[k + 2:]

# 11.7 num parágrafo só
NEW117 = r'''h2("11.7 Comparação com os Objetivos")
p("O objetivo geral foi alcançado: o sistema gera, a cada treinamento, a previsão dos 91 dias seguintes de 23 "
  "séries, das quais as oito categorias erram menos que a previsão ingênua na validação, e a apresenta à empresa em um "
  "painel acessível a usuários não técnicos. Quanto aos objetivos específicos, os requisitos foram validados em oito "
  "reuniões, a modelagem está descrita no Capítulo 8, o ⟨pipeline⟩ carregou as 26 planilhas sem duplicatas, a "
  "análise exploratória definiu as séries e as variáveis do modelo, os experimentos E1 a E8 definiram a "
  "configuração, e os modelos atingiram MASE abaixo de 1 em 19 das 23 séries, com cobertura do intervalo entre 90,5% "
  "e 100%. A validação com usuários foi qualitativa, sem teste formal de usabilidade, e a documentação é técnica, sem "
  "manual do usuário, de modo que esses dois objetivos foram alcançados parcialmente.")

'''
src = between(src, 'h2("11.7 Comparação com os Objetivos")', 'h2("11.8 Discussão dos Resultados")', NEW117)

# 12 mais curta
CAP12 = r'''h1("12 CONCLUSÃO E TRABALHOS FUTUROS")
p("Este trabalho desenvolveu um sistema de previsão de vendas para a Floricultura Verde Perto, que transforma o "
  "histórico de vendas, antes disponível apenas em relatórios do sistema de gestão, em previsões diárias, em "
  "horizontes de duas semanas a três meses, por categoria e por produto de grama de cada unidade, acompanhadas de "
  "intervalo de 95% e de indicadores de desempenho. A solução reúne um ⟨pipeline⟩ de preparação dos dados, modelos "
  "SARIMAX com regressores de calendário, validados por ⟨walk-forward⟩ a cada treinamento, e um painel para "
  "usuários não técnicos, e o objetivo geral foi alcançado, com exceção do manual do usuário e da verificação formal "
  "da usabilidade.")
p("Como contribuições, o trabalho oferece à empresa uma base quantitativa para as compras, integrada à rotina de "
  "exportação das planilhas, e um registro das previsões que permite avaliar a confiança nas estimativas. Do ponto "
  "de vista acadêmico, os resultados indicam que modelos estatísticos com regressores de calendário são aplicáveis à "
  "previsão diária de uma floricultura quando a demanda é agregada em séries densas e as encomendas de grande porte "
  "são tratadas à parte, em linha com Arunraj, Ahrens e Fernandes (2016). Entre as limitações, destacam-se as "
  "encomendas grandes, não previstas pelos modelos, o histórico de 26 meses, insuficiente para a sazonalidade anual, "
  "a validação restrita às oito semanas mais recentes e a base de vendas encerrada em fevereiro de 2026.")
'''
src = between(src, 'h1("12 CONCLUSÃO E TRABALHOS FUTUROS")', 'p("Como trabalhos futuros, propõem-se:")', CAP12)
src = rep(src, 'PG_START = 12', 'PG_START = 11')
open("conteudo_red.py", "w", encoding="utf-8").write(src)
print("ok")
