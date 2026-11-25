import re, sys
sys.path.insert(0, sys.argv[2])
from docx_lib import Doc, q, text_of
real = dict(l.rsplit(" ",1) for l in open(sys.argv[3], encoding="utf-8").read().split("\n") if l.strip())
d = Doc(sys.argv[1])
for p in list(d.body):
    t = text_of(p)
    m = re.match(r"^((Figura|Tabela|Quadro) \d+) – (Apêndice A – |Anexo A – )?", t)
    if not m or p.find(".//" + q("tab")) is None: continue
    ts = [x for x in p.iter(q("t"))]
    last = ts[-1]
    if not (last.text or "").strip().isdigit(): continue
    new = real[m.group(1)]
    if last.text.strip() != new:
        print(m.group(1), last.text, "->", new); last.text = new
d.save()
