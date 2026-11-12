# -*- coding: utf-8 -*-
"""Quarta redução: elimina as sobras de página da introdução, da discussão e da conclusão."""
src = open("conteudo_red.py", encoding="utf-8").read()


def rep(s, a, b):
    assert a in s, a[:80]
    return s.replace(a, b)


def between(s, a, b, new):
    i, j = s.index(a), s.index(b)
    assert i < j, (a, b)
    return s[:i] + new + s[j:]


src = rep(src, 'h1("1 INTRODUÇÃO")\ncp("A previsão de demanda pode apoiar o planejamento de compras")',
          'h1("1 INTRODUÇÃO")\np("A previsão de demanda apoia o planejamento de compras e a gestão de estoques ao estimar as vendas futuras, o "\n'
          '  "que é especialmente relevante para produtos perecíveis, nos quais estimativas distantes da demanda expõem a "\n'
          '  "empresa à falta de produtos ou a compras acima do necessário (HYNDMAN; ATHANASOPOULOS, 2021).")')

src = rep(src, 'cp("A principal limitação está nas encomendas grandes", ("experimento E11", "experimento E7"))',
          'p("A principal limitação está nas encomendas grandes, que representaram 52,5% do volume de Itabirito e 27,0% "\n'
          '  "do de Jardim Canadá e não são previstas, pois dependem de negociações que o histórico não antecipa. O limiar que "\n'
          '  "as define ainda não foi calibrado pela entidade parceira, o histórico de 26 meses não permite estimar a "\n'
          '  "sazonalidade anual, e o fator das datas comemorativas se apoia em poucas ocorrências de cada data.")')
src = rep(src, '"defeito de duplicidade dentro da mesma planilha. As melhorias possíveis estão listadas como trabalhos futuros no "\n  "Capítulo 12.")',
          '"defeito de duplicidade dentro da mesma planilha.")')

FUT = r'''p("Como trabalhos futuros, propõem-se:")
ul("verificar a usabilidade com a gestora de compras, elaborar o manual do usuário e corrigir a verificação de notas "
   "repetidas na mesma planilha,",
   "integrar a informação antecipada das encomendas grandes e calibrar com a empresa o limiar que as define,",
   "oferecer uma quantidade de referência baseada em um quantil superior da distribuição prevista,",
   "estender a previsão por produto às Flores de corte e comparar métodos de demanda intermitente (Seção 5.3), redes "
   "neurais e métodos de ⟨ensemble⟩,",
   "implementar a identificação de produtos comprados em conjunto e a simulação de promoções,",
   "avaliar o efeito do sistema sobre as perdas por descarte e as rupturas de estoque.")
'''
src = between(src, 'p("Como trabalhos futuros, propõem-se:")', 'p("Por fim, o trabalho mostrou', FUT)
open("conteudo_red.py", "w", encoding="utf-8").write(src)
print("ok")

src = open("conteudo_red.py", encoding="utf-8").read()
i = src.index('p("Por fim, o trabalho mostrou')
j = src.index("\n\n", i)
src = src[:i] + ('p("Por fim, o trabalho mostrou que o histórico de vendas que a empresa já possuía, organizado e combinado com o "\n'
                 '  "calendário de cada loja, pode orientar as compras de produtos perecíveis com estimativas avaliadas ao longo do "\n'
                 '  "tempo, o que reforça a importância de levar métodos de previsão às pequenas empresas do varejo.")') + src[j:]
src = rep(src, '"estender a previsão por produto às Flores de corte e comparar métodos de demanda intermitente (Seção 5.3), redes "\n   "neurais e métodos de ⟨ensemble⟩,",',
          '"estender a previsão por produto às Flores de corte e comparar métodos de demanda intermitente (Seção 5.3),",')
open("conteudo_red.py", "w", encoding="utf-8").write(src)
print("ok2")

src = open("conteudo_red.py", encoding="utf-8").read()
src = rep(src, '"Como contribuições, o trabalho oferece à empresa uma base quantitativa para as compras, integrada à rotina de "\n'
               '  "exportação das planilhas, e um registro das previsões que permite avaliar a confiança nas estimativas. Do ponto "',
          '"Como contribuições, o trabalho oferece à empresa uma base quantitativa para as compras e um registro das "\n'
          '  "previsões que permite avaliar a confiança nas estimativas. Do ponto "')
src = rep(src, '"a validação restrita às oito semanas mais recentes e a base de vendas encerrada em fevereiro de 2026.")',
          '"e a base de vendas encerrada em fevereiro de 2026.")')
open("conteudo_red.py", "w", encoding="utf-8").write(src)
print("ok3")
