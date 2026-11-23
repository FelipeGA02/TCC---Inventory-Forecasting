"""Remove/reescreve os trechos que a obra citada não sustenta (verificação de 22/11/2026).
As 3 obras continuam nas Referências: seguem citadas em trechos sustentados."""
import sys
sys.path.insert(0, sys.argv[2])
from docx_lib import Doc

d = Doc(sys.argv[1])
trocas = [
    # 5.3 — Syntetos, Boylan e Croston (2005): a classificação serve para escolher o método, não "modelo convencional"
    ("Syntetos, Boylan e Croston (2005) mostraram que o intervalo entre as vendas e a variabilidade do seu "
     "tamanho permitem identificar as séries para as quais um modelo convencional é adequado. Esse fundamento "
     "delimita as séries modeladas neste trabalho, restritas às de venda frequente.",
     "Syntetos, Boylan e Croston (2005) classificaram a demanda pelo intervalo médio entre as vendas e pela "
     "variabilidade do seu tamanho, para escolher o método de previsão adequado a cada classe. Neste trabalho, "
     "essa classificação delimitou as séries modeladas, restritas às de venda frequente."),
    # 11.4 — "adequado ao SARIMAX" não vem da obra
    ("e apresentam demanda errática, padrão adequado a modelos como o SARIMAX.",
     "e apresentam demanda errática, isto é, vendem na maioria dos dias, em quantidades variáveis."),
    # 8.6 — Hyndman e Athanasopoulos não falam de monitoramento contínuo indispensável
    ("Em ambientes de negócio com variação sazonal elevada, o monitoramento contínuo do desempenho preditivo "
     "é indispensável (HYNDMAN; ATHANASOPOULOS, 2021).",
     "O desempenho de um modelo só pode ser avaliado depois que as vendas do período previsto ficam "
     "disponíveis (HYNDMAN; ATHANASOPOULOS, 2021)."),
]
for old, new in trocas:
    n = d.replace_text(old, new)
    print(n, old[:60])
    assert n == 1, old

# Quadro 1 — Huber et al. (2017) propõem um sistema de apoio à decisão
lin = [tr for tr in d.body.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
       if "Huber, Gossmann e Stuckenschmidt (2017)" in "".join(t.text or "" for t in tr.iter(
           "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))]
assert len(lin) == 1, len(lin)
n = 0
for t in lin[0].iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
    if t.text == "Estudo metodológico, sem ferramenta operacional para a empresa.":
        t.text = "Sistema de apoio à decisão para uma rede de padarias, com outro setor e outro tipo de produto."
        n += 1
assert n == 1, n
print(1, "Quadro 1 Huber")
d.save()
