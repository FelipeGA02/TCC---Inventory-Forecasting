import json, re, sys
from lxml import etree
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"; q = lambda t: f"{{{W}}}{t}"
path, pj = sys.argv[1], sys.argv[2]
pages = json.load(open(pj))
tree = etree.parse(path); body = tree.getroot().find(q("body"))
n = 0
for p in body.iter(q("p")):
    ts = p.findall(f".//{q('t')}")
    if len(ts) < 3: continue
    m = re.match(r"^(Figura|Quadro|Tabela) (\d+) –$", (ts[0].text or "").strip())
    if not m or not re.fullmatch(r"\d+", (ts[-1].text or "").strip()): continue
    k = f"{m.group(1)} {m.group(2)}"
    if ts[-1].text != str(pages[k]): print("  ", k, ts[-1].text, "->", pages[k])
    ts[-1].text = str(pages[k]); n += 1
tree.write(path, xml_declaration=True, encoding="UTF-8", standalone=True)
print("entradas", n)
