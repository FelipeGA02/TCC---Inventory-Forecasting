# -*- coding: utf-8 -*-
"""Gera conteudo_red.py (versão reduzida, ~60 páginas) a partir de conteudo.py."""
src = open("conteudo.py", encoding="utf-8").read()


def between(s, a, b, new):
    i, j = s.index(a), s.index(b)
    assert i < j, (a, b)
    return s[:i] + new + s[j:]


def rep(s, a, b, count=1):
    assert s.count(a) >= 1, a[:70]
    return s.replace(a, b) if count == 0 else s.replace(a, b, count)


# ---------------- introdução: estrutura
src = rep(src, '"trabalhos futuros. Os apêndices reúnem as atas das reuniões com a entidade parceira, a especificação dos "\n'
               '  "casos de uso e o dicionário dos dados de vendas, e o anexo apresenta telas do sistema de gestão da empresa.")',
          '"trabalhos futuros. Os apêndices reúnem a especificação dos casos de uso e o dicionário dos dados de vendas, e "\n'
          '  "o anexo apresenta telas do sistema de gestão da empresa.")')

# ---------------- 6.2: sem remissão às atas
src = rep(src, '"solicitações do cliente, as pendências e a validação do representante da empresa. As atas estão no "\n  "Apêndice A.")',
          '"solicitações do cliente, as pendências e a validação do representante da empresa.")')

# ---------------- 8: figuras menores
for a, b in [('os.path.join(IMG, "casos_uso.png"), 14.5,', 'os.path.join(IMG, "casos_uso.png"), 12.5,'),
             ('os.path.join(MED, "image4.png"), 11.0,', 'os.path.join(MED, "image4.png"), 9.0,'),
             ('os.path.join(MED, "image5.png"), 16.0,', 'os.path.join(MED, "image5.png"), 14.0,'),
             ('os.path.join(IMG, "sequencia.png"), 15.0,', 'os.path.join(IMG, "sequencia.png"), 12.0,'),
             ('os.path.join(MED, "image6.png"), 16.0,', 'os.path.join(MED, "image6.png"), 14.5,'),
             ('os.path.join(MED, "image7.png"), 9.5,', 'os.path.join(MED, "image7.png"), 7.5,'),
             ("A especificação de cada caso de uso está no Apêndice B.", "A especificação de cada caso de uso está no Apêndice A.")]:
    src = rep(src, a, b)

# ---------------- 9.2: dois protótipos
src = between(src, 'h2("9.2 Protótipos de Interface")', 'h2("9.3 Validação dos Protótipos com Usuários/Entidade")', r'''h2("9.2 Protótipos de Interface")
p("O protótipo reunia sete telas: Início, Carregar Planilha, Conferir Dados, Previsão de Compras, Produtos para "
  "Repor, Simular Promoções e Baixar Relatórios. A tela inicial ({fig:p_inicio}) reunia indicadores e gráficos de "
  "vendas da rede, e a tela Previsão de Compras ({fig:p_previsao}) apresentava, para um produto e uma unidade, as "
  "vendas das semanas anteriores, a estimativa das semanas seguintes com a margem de variação, indicadores de erro, "
  "um aviso de data comemorativa e a quantidade a comprar por semana. A tela Simular Promoções estimava o efeito de "
  "um desconto e de um produto vendido em conjunto sobre as vendas da semana. As figuras usam os dados fictícios do "
  "protótipo.")
fig("p_inicio", os.path.join(IMG, "p_inicio.jpg"), 13.5, "Protótipo: tela inicial", F_AUT)
fig("p_previsao", os.path.join(IMG, "p_previsao.jpg"), 13.5, "Protótipo: previsão de compras", F_AUT)
''')
src = rep(src, '"previsão, quando a empresa considerou os resultados satisfatórios e solicitou ajustes na interface "\n  "(Apêndice A). A validação',
          '"previsão, quando a empresa considerou os resultados satisfatórios e solicitou ajustes na interface. A validação')

# ---------------- 10.2: seis telas
src = between(src, 'h2("10.2 Interfaces Desenvolvidas")', 'h2("10.3 Integração entre Componentes")', r'''h2("10.2 Interfaces Desenvolvidas")
p("O painel organiza as funcionalidades em cinco telas acessíveis pelo menu lateral, Início, Carregar Planilha, "
  "Conferir Dados, Previsão de Vendas e Relatórios, além da tela de login, com os campos de e-mail e senha. No "
  "cabeçalho, ficam o botão Atualizar, o botão Treinar previsões, visível apenas ao administrador, que solicita o "
  "treinamento e indica o andamento durante a execução, e o painel de notificações, que informa o resultado do "
  "treinamento e a existência de vendas ainda não usadas pela previsão. As telas a seguir foram capturadas do "
  "sistema em execução local, conectado ao banco de dados de produção, com as vendas até 28 de fevereiro de 2026.")
p("A tela inicial ({fig:inicio}) apresenta a visão geral das vendas da base. Os componentes são o filtro de "
  "unidade, quatro indicadores, de faturamento líquido, notas de venda, quantidade vendida e encomendas grandes, "
  "o gráfico de faturamento mensal, que separa a venda do dia a dia das encomendas grandes, o faturamento médio por "
  "dia da semana, a participação de cada categoria, a comparação entre consumidores e clientes cadastrados, as "
  "formas de pagamento e a tabela dos produtos mais vendidos no último ano. Nenhum dado pessoal de cliente é "
  "exibido.")
fig("inicio", os.path.join(IMG, "t_inicio.png"), 12.0, "Tela inicial com a análise das vendas", F_TELA, 17.0)
p("A tela Carregar Planilha conduz a importação em quatro etapas, envio do arquivo, conferência, gravação e "
  "conclusão, com uma área que aceita arquivos XLSX e XLSM arrastados ou selecionados e o quadro das planilhas já "
  "carregadas. Na conferência ({fig:conferencia}), a tela apresenta o período de cada unidade e a última venda já "
  "carregada, os totais de vendas novas, de vendas já carregadas e de linhas ignoradas e o aviso dos dias de loja "
  "aberta sem venda, com a orientação de enviar a planilha desses dias antes de treinar, e os botões Cancelar e "
  "Gravar. No exemplo, foi conferida, sem gravação, uma planilha de teste com vendas fictícias de março de 2026.")
fig("conferencia", os.path.join(IMG, "t_conferencia.png"), 14.0, "Conferência da planilha antes da gravação", F_TELA)
p("A tela Conferir Dados ({fig:conferir}) permite consultar as vendas gravadas, com busca por produto, código ou "
  "número da nota, filtros, escolha do mês, seleção de colunas, exportação e a tabela paginada, com a linha de total "
  "do filtro.")
fig("conferir", os.path.join(IMG, "t_conferir.png"), 14.0, "Tela de conferência das vendas importadas", F_TELA)
p("A tela Previsão de Vendas tem duas abas. Na aba Previsão ({fig:previsao}), a caixa Horizonte define o período "
  "exibido, de duas semanas a três meses, e o quadro de feriados e datas comemorativas lista as datas do período e "
  "se as lojas abrem. O gráfico mostra a venda das semanas anteriores e a previsão de cada categoria da unidade "
  "escolhida, e a tabela Dia a dia apresenta a quantidade prevista em cada dia, com o total do dia e os dias de loja "
  "fechada sinalizados. Ao passar o cursor sobre um valor, a tela mostra a faixa provável, correspondente ao "
  "intervalo de 95%. Na visão por produto, a lista dos produtos de grama da unidade permite escolher o produto e "
  "consultar o vendido, a previsão e a faixa provável.")
fig("previsao", os.path.join(IMG, "t_previsao.png"), 12.5, "Previsão diária por categoria no horizonte escolhido", F_TELA, 17.0)
p("A aba Histórico de previsão ({fig:historico}) compara o vendido em cada dia, sem as encomendas grandes, com a "
  "previsão mais antiga feita para ele, por categoria ou por produto, e resume a validação do último treinamento em "
  "dois indicadores: o erro médio por dia, em unidades, e a margem de incerteza, igual à metade da largura média do "
  "intervalo de 95%.")
fig("historico", os.path.join(IMG, "t_historico.png"), 14.0, "Histórico da previsão: vendido e previsto", F_TELA)
p("Por fim, a tela Relatórios ({fig:relatorios}) reúne os relatórios para baixar, com filtro de unidade: o relatório "
  "gerencial em PDF, as previsões diárias por loja e categoria e por produto de grama, o histórico de vendas, as "
  "encomendas grandes, o acerto da previsão de cada série e a lista das planilhas importadas, nos formatos Excel e "
  "PDF, além do quadro com as planilhas enviadas e os treinamentos realizados.")
fig("relatorios", os.path.join(IMG, "t_relatorios.png"), 14.0, "Tela de relatórios", F_TELA)
''')

# ---------------- 10.4: sem o item de compatibilidade de bibliotecas
src = rep(src, '''   "compatibilidade de bibliotecas: a versão do Python da imagem de publicação exigiu a atualização das versões "
   "das bibliotecas, e a biblioteca de ⟨hash⟩ de senhas utilizada inicialmente era incompatível com a versão "
   "atual do ⟨bcrypt⟩, que passou a ser usado diretamente,",
''', "")

# ---------------- 11: resultados reduzidos
src = between(src, 'h1("11 RESULTADOS E DISCUSSÕES")', 'h1("12 CONCLUSÃO E TRABALHOS FUTUROS")', open("resultados_red.py", encoding="utf-8").read())

# ---------------- referências sem uso
src = rep(src, '"BREIMAN, L.", ', '')
src = rep(src, '"PESARAN, M. H.", ', '')

# ---------------- apêndices: sem as atas
src = between(src, 'h1("APÊNDICE A – ATAS DAS REUNIÕES COM A ENTIDADE PARCEIRA")', 'h1("APÊNDICE B – ESPECIFICAÇÃO DOS CASOS DE USO")', "")
src = rep(src, 'h1("APÊNDICE B – ESPECIFICAÇÃO DOS CASOS DE USO")', 'h1("APÊNDICE A – ESPECIFICAÇÃO DOS CASOS DE USO")')
src = rep(src, 'h1("APÊNDICE C – DICIONÁRIO DE DADOS DO RELATÓRIO DE VENDAS")', 'h1("APÊNDICE B – DICIONÁRIO DE DADOS DO RELATÓRIO DE VENDAS")')

open("conteudo_red.py", "w", encoding="utf-8").write(src)
print("ok", len(src))
