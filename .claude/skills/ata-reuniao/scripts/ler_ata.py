# -*- coding: utf-8 -*-
"""Lê uma ata já feita (DOCX) e devolve o conteúdo no mesmo JSON que gerar_ata.py recebe.

    python ler_ata.py <ata.docx> [saida.json]
    python ler_ata.py --ultima [<pasta>]      # imprime o caminho e o JSON da ata de maior número

Serve de base para a ata seguinte: a tabela de requisitos é cumulativa e as pendências em
aberto passam adiante. Só usa a biblioteca padrão.
"""
import glob
import json
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

PASTA_ATAS = r"C:\Users\felip\OneDrive\Documentos\Estudos\TCC\Relatórios"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def texto(el, negrito_md=False):
    """Texto do elemento; <w:br/> vira \\n, <w:tab/> vira espaço."""
    partes = []
    for r in el.iter(W + "r"):
        rpr = r.find(W + "rPr")
        b = negrito_md and rpr is not None and rpr.find(W + "b") is not None
        s = ""
        for c in r:
            if c.tag == W + "t":
                s += c.text or ""
            elif c.tag == W + "br":
                s += "\n"
            elif c.tag == W + "tab":
                s += " "
        partes.append(f"**{s}**" if b and s.strip() else s)
    out = "".join(partes).replace("****", "")
    return re.sub(r"[ \t]+\n", "\n", out)


def destacado(p):
    return any(h.get(W + "val") == "yellow" for h in p.iter(W + "highlight"))


def nivel(p):
    ppr = p.find(W + "pPr")
    num = ppr.find(W + "numPr") if ppr is not None else None
    if num is None:
        return None
    il = num.find(W + "ilvl")
    return int(il.get(W + "val")) if il is not None else 0


def linhas_tabela(tbl):
    out = []
    for tr in tbl.findall(W + "tr"):
        # parágrafos da célula (inclusive de tabelas aninhadas, que existem nas atas 01–04)
        cels = [" ".join(t for t in (texto(p).strip() for p in tc.iter(W + "p")) if t)
                for tc in tr.findall(W + "tc")]
        out.append(cels)
    return out[1:]  # sem cabeçalho


def data_iso(v):
    m = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", v.strip())
    return f"{int(m[1]):02d}/{int(m[2]):02d}/{m[3]}" if m else v.strip()


def ler(caminho):
    with zipfile.ZipFile(caminho) as z:
        body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    secoes = {}
    atual = None
    for el in body:
        if el.tag == W + "p":
            t = texto(el).strip()
            m = re.match(r"^(\d{1,2})\.\s", t)
            if m and nivel(el) is None and len(t) < 60:
                atual = int(m[1])
                secoes[atual] = []
                continue
        if atual is not None:
            secoes[atual].append(el)

    d = {}
    for p in secoes.get(1, []):
        t = texto(p).strip()
        if ":" not in t:
            continue
        rot, val = [s.strip() for s in t.split(":", 1)]
        rot = rot.lower()
        if rot.startswith("projeto"):
            d["projeto"] = val
        elif rot.startswith("entidade"):
            d["entidade"] = val
        elif rot.startswith("número"):
            d["numero"] = val
        elif rot.startswith("data"):
            d["data"] = data_iso(val)
        elif rot.startswith("horário"):
            m = re.search(r"Início:\s*([\d:]+).*Término:\s*([\d:]+)", t)
            if m:
                d["inicio"], d["termino"] = m[1], m[2]
        elif rot.startswith("local"):
            d["local"] = "presencial" if re.search(r"\(\s*X\s*\)\s*Presencial", val, re.I) else "online"
        elif rot.startswith("plataforma"):
            d["plataforma"] = val

    for el in secoes.get(2, []):
        if el.tag == W + "tbl":
            d["participantes"] = [{"nome": c[0], "papel": c[1]} for c in linhas_tabela(el)
                                  if len(c) > 1 and (c[0] or c[1])]

    d["objetivo"] = "\n".join(texto(p).strip() for p in secoes.get(3, []) if texto(p).strip())

    marcados, outros = [], ""
    for p in secoes.get(4, []):
        t = texto(p).replace("☐", "").strip()
        if not t:
            continue
        if t.lower().startswith("outros"):
            outros = t.split(":", 1)[1].strip() if destacado(p) else ""
        elif destacado(p):
            marcados.append(t)
    d["pauta"] = {"marcados": marcados, "outros": outros}

    dec = []
    for p in secoes.get(5, []):
        t = texto(p, negrito_md=True).strip()
        if not t:
            continue
        if (nivel(p) or 0) >= 1 and dec:
            dec[-1].setdefault("subitens", []).append(t)
        else:
            dec.append({"texto": t})
    d["decisoes"] = [x if x.get("subitens") else x["texto"] for x in dec]

    for el in secoes.get(6, []):
        if el.tag == W + "tbl":
            reqs = []
            for c in linhas_tabela(el):
                if len(c) < 3 or not (c[0] or c[1]):
                    continue
                m = re.search(r"(Alta|Média|Baixa)\s*\(\s*X\s*\)", c[2], re.I)
                reqs.append({"codigo": c[0], "descricao": c[1], "prioridade": m[1] if m else None})
            d["requisitos"] = reqs

    for el in secoes.get(7, []):
        if el.tag == W + "tbl":
            d["pendencias"] = [{"acao": c[0], "prazo": c[1]} for c in linhas_tabela(el)
                               if len(c) > 1 and (c[0] or c[1])]

    imp = {"marcados": [], "descricao": [], "pontos_de_atencao": []}
    ps = [p for p in secoes.get(8, []) if p.tag == W + "p"]
    if ps:
        for linha in texto(ps[0]).split("\n"):
            m = re.match(r"\(\s*X\s*\)\s*(.+)", linha.strip(), re.I)
            if m:
                imp["marcados"].append(m[1].strip())
        em_pontos = False
        for p in ps[1:]:
            t = texto(p).strip()
            if not t or t.startswith("Descrição do impacto"):
                continue
            if t.lower().startswith("pontos de atenção"):
                em_pontos = True
                continue
            if em_pontos:
                imp["pontos_de_atencao"].append(t)
            else:  # item de lista na descrição vira "- texto" (como na ata 01)
                imp["descricao"].append(("- " + t) if nivel(p) is not None else t)
    d["impactos"] = imp

    prox = {}
    for p in secoes.get(9, []):
        t = texto(p).strip()
        if t.startswith("Data prevista:"):
            prox["data"] = data_iso(t.split(":", 1)[1])
        elif t.startswith("Objetivo:"):
            prox["objetivo"] = t.split(":", 1)[1].strip()
    d["proxima_reuniao"] = prox

    val = {}
    for p in secoes.get(10, []):
        t = texto(p).strip()
        if t.startswith("Representante do Cliente:"):
            val["representante_cliente"] = t.split(":", 1)[1].strip()
        elif t.startswith("Responsável pelo Projeto:"):
            val["responsaveis"] = [n.strip() for n in re.split(r",| e ", t.split(":", 1)[1]) if n.strip()]
    d["validacao"] = val
    return d


def ultima(pasta=PASTA_ATAS):
    atas = []
    for f in glob.glob(os.path.join(pasta, "Documento - Registro de Reuniao com Entidade *.docx")):
        m = re.search(r"Entidade (\d+)\.docx$", f)
        if m:
            atas.append((int(m[1]), f))
    return max(atas)[1] if atas else None


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--ultima":
        caminho = ultima(args[1] if len(args) > 1 else PASTA_ATAS)
        if not caminho:
            raise SystemExit("nenhuma ata encontrada")
        print(caminho)
        print(json.dumps(ler(caminho), ensure_ascii=False, indent=2))
    elif args:
        dados = json.dumps(ler(args[0]), ensure_ascii=False, indent=2)
        if len(args) > 1:
            with open(args[1], "w", encoding="utf-8") as f:
                f.write(dados + "\n")
            print("json gravado:", args[1])
        else:
            print(dados)
    else:
        print(__doc__)
