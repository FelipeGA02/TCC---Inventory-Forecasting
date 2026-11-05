# -*- coding: utf-8 -*-
"""Verificações automáticas do artigo antes da entrega.

    python check_article.py <final.docx>

1. Estilo: padrões proibidos (travessão, clichês de LLM, linguagem promocional), linguagem de
   plano ("será desenvolvido", "pretende-se") e narrativa de "antes e depois".
2. Fatos obsoletos: valores que já foram substituídos no artigo e não podem voltar.
3. Citações × referências: toda citação tem referência e toda referência nova é citada.
4. Numeração de figuras e tabelas: legendas em sequência e cada uma citada no texto.

Nada aqui substitui a releitura integral; os avisos são pistas para conferir no contexto.
"""
import io
import re
import sys
import unicodedata
import zipfile

from lxml import etree

sys.stdout.reconfigure(encoding="utf-8")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

STYLE = [  # (padrão, motivo)
    ("—", "travessão: o autor não usa; reescreva a frase"),
    ("Nesse contexto", "clichê"), ("Vale destacar", "clichê"), ("É importante ressaltar", "clichê"),
    ("De maneira geral", "clichê"), ("Em suma", "clichê"), ("Por outro lado", "clichê"),
    ("inovador", "promocional"), ("inovadora", "promocional"), ("de ponta", "promocional"),
    ("revolucion", "promocional"), ("altamente eficiente", "promocional"), ("extremamente importante", "promocional"),
    ("será desenvolvid", "plano: descreva como realizado"), ("serão desenvolvid", "plano"),
    ("pretende-se", "plano"), ("Pretende-se", "plano"), ("Espera-se", "plano"), ("espera-se", "plano"),
    ("futuramente", "plano"), ("o sistema deverá", "plano"), ("O sistema deverá", "plano"),
    ("propõe-se", "plano"), ("Inicialmente", "antes/depois"), ("Anteriormente", "antes/depois"),
    ("anteriormente", "antes/depois"), ("versão anterior", "antes/depois"), ("primeira versão", "antes/depois"),
    ("Posteriormente decidiu", "antes/depois"), ("foi necessário abandonar", "antes/depois"),
    ("percebeu-se", "antes/depois"), ("Diferentemente do que havia", "antes/depois"),
]
OBSOLETE = [
    ("duas a três semanas", "horizonte é 14 dias"), ("duas e três semanas", "horizonte é 14 dias"),
    ("mensal e diária", "comparação mensal × diária não faz parte do trabalho"),
    ("granularidades mensal", "idem"), ("Streamlit", "dashboard é React"), ("R²", "R² não é métrica do trabalho"),
    ("MAPE inferior a 20", "critério é MASE < 1 e cobertura do IC"), ("SMAPE inferior a 30", "idem"),
    ("324 mil", "base tem 333.019 registros"), ("três unidades operacionais", "são 2 unidades (3 empresas)"),
    ("ponderação de variáveis exógenas", "RF/MDI é seleção/avaliação, não ponderação"),
    ("estoque crítico", "o sistema não usa estoque atual"), ("Estoque Crítico", "idem"),
    ("shelf", "camada L3 (validade) está fora de escopo"),
    ("previsão de estoque", "o sistema se chama 'previsão de vendas' (decisão de 30/09/2026)"),
    ("PREVISÃO DE ESTOQUE", "idem"), ("Plantas de corte", "nome atual da categoria: Flores de corte"),
]


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def paragraphs(docx):
    with zipfile.ZipFile(docx) as z:
        root = etree.parse(io.BytesIO(z.read("word/document.xml"))).getroot()
    body = root.find("{%s}body" % W)
    out = []
    for p in body.iter("{%s}p" % W):
        out.append("".join(t.text or "" for t in p.iter("{%s}t" % W)).strip())
    return [p for p in out if p]


ps = paragraphs(sys.argv[1])
try:
    i_ref = max(i for i, p in enumerate(ps) if p == "REFERÊNCIAS")
except ValueError:
    sys.exit("título REFERÊNCIAS não encontrado")
i_intro = next(i for i, p in enumerate(ps) if p in ("INTRODUÇÃO", "1 INTRODUÇÃO"))
body = "\n".join(ps[:i_ref])
text = "\n".join(ps[i_intro:i_ref])   # sem capa/sumário
refs = ps[i_ref + 1:]

problems = 0
print("== 1. Estilo")
for pat, why in STYLE:
    for m in re.finditer(re.escape(pat), body):
        problems += 1
        print(f"  [{pat}] {why}: …{body[max(0, m.start() - 60):m.end() + 40]}…".replace("\n", " "))
print("== 2. Fatos obsoletos")
for pat, why in OBSOLETE:
    for m in re.finditer(re.escape(pat), body):
        problems += 1
        print(f"  [{pat}] {why}: …{body[max(0, m.start() - 60):m.end() + 40]}…".replace("\n", " "))
n_alem = text.count("Além disso")
if n_alem > 1:
    print(f"  aviso: 'Além disso' aparece {n_alem} vezes")

print("== 2b. Terminologia × título")
titulo = next((p for p in ps if p.startswith("SISTEMA DE PREVISÃO DE")), "")
termo = "vendas" if "VENDAS" in titulo else ("estoque" if "ESTOQUE" in titulo else None)
outro = {"vendas": "estoque", "estoque": "vendas"}.get(termo)
if outro:
    for m in re.finditer(rf"sistema de previsão de {outro}|previsão de {outro} da empresa", text):
        trecho = text[max(0, m.start() - 50):m.end() + 30].replace("\n", " ")
        print(f"  título diz 'previsão de {termo}'; texto diz: …{trecho}…")

print("== 3. Citações × referências")
UP = "A-ZÀ-ÖØ-Þ"
LO = "a-zß-öø-ÿ"
# referências: junta as linhas que a conversão quebrou (continuações começam por minúscula ou dígito)
entries = []
for line in refs:
    if re.match(rf"^[{UP}][{UP}\- ]+[,.]", line):
        entries.append(line)
    elif entries:
        entries[-1] += " " + line
ref_keys = {}
for e in entries:
    first = strip_accents(e.split(",")[0].split(".")[0]).upper().strip()
    years = re.findall(r"\b((?:19|20)\d{2})\b", e)
    ref_keys.setdefault((first, years[-1] if years else "?"), e[:70])
cited = set()
# parentéticas ABNT: (AUTOR; AUTOR, 2020), (AUTOR et al., 2015), (A; B, 1995; C; D; E, 2006)
author = rf"[{UP}][{UP}\-\.]*(?: [{UP}\-\.]+)*"
for grp in re.findall(r"\(([^()]*\d{4})\)", text):
    for m in re.finditer(rf"({author}(?: et al\.)?(?:; {author}(?: et al\.)?)*), ((?:19|20)\d{{2}})", grp):
        cited.add((strip_accents(m.group(1).split(";")[0].replace(" et al.", "")).strip(), m.group(2)))
# narrativas: Breiman (2001), Syntetos e Boylan (2005), Syntetos, Boylan e Croston (2005), Box et al. (2015)
name = rf"[{UP}][{LO}]+"
for m in re.finditer(rf"\b({name})(?:, {name})*(?: e {name})?(?: et al\.)? \(((?:19|20)\d{{2}})\)", text):
    cited.add((strip_accents(m.group(1)).upper(), m.group(2)))
for c in sorted(c for c in cited if c not in ref_keys):
    problems += 1
    print("  citado sem referência:", c)
for k in sorted(k for k in ref_keys if k not in cited and not k[0].startswith("ASSOCIACAO")):
    print("  referência não citada (confira se é intencional):", k, ref_keys[k])
print(f"  {len(cited)} citações distintas, {len(ref_keys)} referências")

print("== 4. Figuras e tabelas")
for kind in ("Figura", "Tabela", "Quadro"):
    caps = [int(m.group(1)) for p in ps for m in [re.match(kind + r" (\d+) –", p)] if m]
    if caps != list(range(1, len(caps) + 1)):
        problems += 1
        print(f"  legendas de {kind} fora de sequência: {caps}")
    for n in caps:
        mention = re.search(rf"{kind}s? {n}\b|{kind}s \d+ e {n}\b", "\n".join(p for p in ps[i_intro:i_ref]
                                                                         if not re.match(kind + r" \d+ –", p)))
        if not mention:
            problems += 1
            print(f"  {kind} {n} não é citada no texto")
    print(f"  {kind}: {len(caps)} legendas")

print("\nproblemas:", problems)
