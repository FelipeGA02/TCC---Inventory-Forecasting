import fitz, re, sys, json
doc = fitz.open(sys.argv[1])
def norm(s): return re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()
lines = [[norm(l) for l in p.get_text("text").splitlines() if l.strip()] for p in doc]
intro = next(i for i, ls in enumerate(lines) if "1 INTRODUÇÃO" in ls and not any("SUMÁRIO" in x for x in ls) and i > 5)
res = {}
for i in range(intro, len(lines)):
    for l in lines[i]:
        m = re.match(r"^(Figura|Quadro|Tabela) (\d+) – ", l)
        if m and (m.group(1), int(m.group(2))) not in res:
            res[(m.group(1), int(m.group(2)))] = i
# número impresso: procura um número isolado na 1ª ou última linha
def printed(i):
    cand = [l for l in (lines[i][:2] + lines[i][-2:]) if re.fullmatch(r"\d{1,3}", l)]
    return cand
print("intro idx", intro, "printed", printed(intro), "| total", len(doc))
json.dump({f"{k[0]} {k[1]}": v for k, v in res.items()}, open(sys.argv[2], "w"), ensure_ascii=False)
for k, v in sorted(res.items()): print(k, v, printed(v))
