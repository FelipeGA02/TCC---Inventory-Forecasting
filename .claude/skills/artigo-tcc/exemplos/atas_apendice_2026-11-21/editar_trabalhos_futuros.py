"""Trabalhos futuros (21/11/2026): saem o quantil e as Flores de corte por produto; entra a base
atualizada com o teste de redes neurais. As letras dos itens são texto digitado (sem numPr)."""
import sys
sys.path.insert(0, sys.argv[2])
from docx_lib import Doc, q, text_of

d = Doc(sys.argv[1])


def item(inicio):
    return d.find(startswith=inicio)


c = item("c)oferecer uma quantidade de referência")
dd = item("d)estender a previsão por produto às Flores de corte")
e = item("e)implementar a identificação de produtos comprados")
f = item("f)avaliar o efeito do sistema")
assert c.getnext() is dd and dd.getnext() is e and e.getnext() is f

# c: novo texto no run depois da tabulação (o run da letra fica igual)
ts = list(c.iter(q("t")))
assert ts[0].text == "c)" and len(ts) == 2
ts[1].text = ("carregar as planilhas de vendas de março de 2026 em diante, mantendo a base "
              "atualizada até os dias mais recentes, e, com o histórico ampliado, testar modelos "
              "de redes neurais na previsão das vendas;")

d.remove(dd)

for p, old, new in ((e, "e)", "d)"), (f, "f)", "e)")):
    t = next(p.iter(q("t")))
    assert t.text == old
    t.text = new

d.save()
for p in (c, e, f):
    print(text_of(p))
