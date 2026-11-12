# -*- coding: utf-8 -*-
"""Segunda redução: aplica cortes sobre conteudo_red.py (gerado por make_red.py)."""
src = open("conteudo_red.py", encoding="utf-8").read()
SEC = open("secoes_red2.py", encoding="utf-8").read()
parts = {}
for chunk in SEC.split("#@@ ")[1:]:
    name, body = chunk.split("\n", 1)
    parts[name.strip()] = body


def between(s, a, b, new):
    i, j = s.index(a), s.index(b)
    assert i < j, (a, b)
    return s[:i] + new + s[j:]


src = between(src, 'h1("5 REFERENCIAL TEÓRICO")', 'h1("6 METODOLOGIAS ADOTADAS")', parts["cap5"])
src = between(src, 'h2("6.2 Levantamento e Análise de Requisitos")', 'h1("7 ANÁLISE DE REQUISITOS")', parts["cap6b"])
src = between(src, 'h2("9.2 Protótipos de Interface")', 'h2("9.3 Validação dos Protótipos com Usuários/Entidade")', parts["cap92"])
src = between(src, 'h3("10.1.6 Análise e conferência das vendas")', 'h2("10.2 Interfaces Desenvolvidas")', parts["cap1016"])
src = between(src, 'h2("10.2 Interfaces Desenvolvidas")', 'h1("11 RESULTADOS E DISCUSSÕES")', parts["cap102"])
src = between(src, 'h2("11.3 Resultados dos Testes")', 'h2("11.4 Análise Exploratória dos Dados")', parts["cap113"])
src = between(src, 'p(f"O experimento E3 isolou', 'p("O experimento E4 comparou', parts["e3"])
src = between(src, 'p("O experimento E7 mediu', 'p("O experimento E8 avaliou', parts["e7"])
src = between(src, 'h2("11.7 Comparação com os Objetivos")', 'h2("11.8 Discussão dos Resultados")', parts["cap117"])
src = between(src, 'p("Como trabalhos futuros, propõem-se:")', 'p("Por fim, o trabalho mostrou', parts["futuros"])
src = between(src, 'h1("APÊNDICE B – DICIONÁRIO DE DADOS DO RELATÓRIO DE VENDAS")', 'h1("ANEXO A – TELAS DO SISTEMA DE GESTÃO DA EMPRESA")', "")
src = between(src, 'h1("ANEXO A – TELAS DO SISTEMA DE GESTÃO DA EMPRESA")', "BLOCKS = B", parts["anexo"])

# 6.1: figura menor
src = src.replace('fig("etapas", os.path.join(MED, "image2.png"), 15.0,', 'fig("etapas", os.path.join(MED, "image2.png"), 13.0,')
# 8: figuras ainda menores
for a, b in [('"casos_uso.png"), 12.5,', '"casos_uso.png"), 11.0,'), ('"image4.png"), 9.0,', '"image4.png"), 7.5,'),
             ('"image5.png"), 14.0,', '"image5.png"), 12.5,'), ('"sequencia.png"), 12.0,', '"sequencia.png"), 10.5,'),
             ('"image6.png"), 14.5,', '"image6.png"), 12.5,'), ('"image7.png"), 7.5,', '"image7.png"), 6.5,')]:
    assert a in src, a
    src = src.replace(a, b)
# introdução: estrutura sem o dicionário
a = '"trabalhos futuros. Os apêndices reúnem a especificação dos casos de uso e o dicionário dos dados de vendas, e "\n  "o anexo apresenta telas do sistema de gestão da empresa.")'
assert a in src
src = src.replace(a, '"trabalhos futuros. O apêndice reúne a especificação dos casos de uso, e o anexo apresenta telas do sistema de "\n  "gestão da empresa.")')
src = src.replace("SIGLAS_NOVAS = [", "SIGLAS_REMOVER = ['RMSE']\nSIGLAS_NOVAS = [")
open("conteudo_red.py", "w", encoding="utf-8").write(src)
print("ok")
