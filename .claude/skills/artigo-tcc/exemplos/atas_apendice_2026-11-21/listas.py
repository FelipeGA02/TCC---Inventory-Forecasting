import re, sys, pymupdf
pdf = pymupdf.open(sys.argv[1])
pages = [pg.get_text() for pg in pdf]
def printed(i):
    m = re.search(r"^\s*(\d{1,3})\s*$", pages[i], flags=re.M)
    return m.group(1) if m else None
# primeiras páginas de listas: onde aparece "LISTA DE"
last_list = max(i for i,t in enumerate(pages) if "LISTA DE" in t or "SUMÁRIO" in t)
found = {}
for i in range(last_list+1, len(pages)):
    for m in re.finditer(r"^((Figura|Tabela|Quadro) \d+) – ", pages[i], flags=re.M):
        found.setdefault(m.group(1), printed(i))
for k,v in found.items(): print(k, v)
