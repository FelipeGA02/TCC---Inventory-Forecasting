"""Intervalo de confiança em todo o texto e palavra-chave do atacado e varejo (21/11/2026)."""
import sys
sys.path.insert(0, sys.argv[2])
from docx_lib import Doc, q

d = Doc(sys.argv[1])
trocas = [
    ("A cobertura do intervalo de predição", "A cobertura do intervalo de confiança"),
    ("The prediction-interval coverage", "The confidence-interval coverage"),
    ("O modelo também produz um intervalo de previsão", "O modelo também produz um intervalo de confiança"),
    ("Varejo de floricultura.", "Atacado e varejo de floricultura."),
    ("Floriculture retail.", "Floriculture wholesale and retail."),
]
for old, new in trocas:
    n = d.replace_text(old, new)
    print(n, old)
    assert n == 1

# objetivo f: "...cobertura do intervalo " + "de previsão " + "de 95%;" em runs separados
p = d.find(startswith="f)comparadas experimentalmente", top_level=False) if False else None
alvos = [t for t in d.body.iter(q("t")) if t.text == "de previsão "]
assert len(alvos) == 1, len(alvos)
ant = alvos[0].getparent().getprevious()
assert ant is not None and "".join(x.text or "" for x in ant.iter(q("t"))).endswith("cobertura do intervalo ")
alvos[0].text = "de confiança "
print(1, "objetivo f")
d.save()
