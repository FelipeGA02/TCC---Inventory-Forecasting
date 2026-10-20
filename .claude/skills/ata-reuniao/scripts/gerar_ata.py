# -*- coding: utf-8 -*-
"""Gera a ata (DOCX) no Formulário de Registro de Reuniões com Entidade.

    python gerar_ata.py <conteudo.json> <saida.docx> [--modelo <modelo_ata.docx>]

O DOCX de saída é o modelo com o corpo (word/document.xml) reescrito. Estilos, numeração,
tema, logo, margens e metadados vêm do modelo sem alteração; o XML de cada parágrafo e tabela
repete o das atas 01–04 (engenharia reversa em ../referencia/estrutura.md). Só usa a biblioteca
padrão. Formato do JSON: ../exemplos/ata_05.json.

Marcação aceita nos textos: **negrito** e quebra de linha com "\n".
"""
import argparse
import datetime
import json
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

sys.stdout.reconfigure(encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO_PADRAO = os.path.join(AQUI, "..", "modelo", "modelo_ata.docx")

PAUTA = [
    "Levantamento de requisitos",
    "Validação de funcionalidades",
    "Alterações solicitadas pelo cliente",
    "Apresentação de protótipo",
    "Acompanhamento do cronograma",
]
IMPACTOS = [
    "Não há impacto no escopo",
    "Alteração de escopo",
    "Alteração de prazo",
    "Alteração de custo",
]
NUM_IDENTIFICACAO = 1   # bullets da seção 1
NUM_PROXIMA = 3         # bullets da seção 9
NUM_DESCRICAO = 8       # bullets da descrição do impacto ("- texto"), seção 8
NUM_PONTOS = 9          # bullets de "Pontos de atenção" (seção 8)
NUM_DECISOES = 13       # bullets da seção 5 (nível 0 = •, nível 1 = o)

BOLD = "<w:b/><w:bCs/>"
PPR_BOLD = "<w:pPr><w:rPr><w:b/><w:bCs/></w:rPr></w:pPr>"


# ---------- primitivas ----------

def _t(s):
    s = escape(s)
    sp = ' xml:space="preserve"' if (s != s.strip() or "  " in s) else ""
    return f"<w:t{sp}>{s}</w:t>"


def run(texto, negrito=False, rpr_extra=""):
    """Um run por linha; linhas seguintes começam com <w:br/> (como nas atas originais)."""
    inner = (BOLD if negrito else "") + rpr_extra
    rpr = f"<w:rPr>{inner}</w:rPr>" if inner else ""
    out = []
    for i, linha in enumerate(texto.split("\n")):
        br = "<w:br/>" if i else ""
        out.append(f"<w:r>{rpr}{br}{_t(linha) if linha else ''}</w:r>")
    return "".join(out)


def rico(texto, negrito=False, rpr_extra=""):
    """Converte **trecho** em run negrito."""
    out = []
    for i, parte in enumerate(re.split(r"\*\*(.+?)\*\*", texto or "")):
        if parte:
            out.append(run(parte, negrito or i % 2 == 1, rpr_extra))
    return "".join(out)


def par(runs="", ppr=""):
    return f"<w:p>{ppr}{runs}</w:p>" if (runs or ppr) else "<w:p/>"


def vazio():
    return "<w:p/>"


def vazio_negrito():
    return par("", PPR_BOLD)


def titulo_secao(texto, nova_pagina=False):
    quebra = "<w:pageBreakBefore/>" if nova_pagina else ""
    return par(run(texto, True), f"<w:pPr>{quebra}<w:rPr>{BOLD}</w:rPr></w:pPr>")


def item(num_id, runs, nivel=0, estilo=None):
    st = f'<w:pStyle w:val="{estilo}"/>' if estilo else ""
    return par(runs, f'<w:pPr>{st}<w:numPr><w:ilvl w:val="{nivel}"/>'
                     f'<w:numId w:val="{num_id}"/></w:numPr></w:pPr>')


def campo(num_id, rotulo, valor):
    return item(num_id, run(rotulo, True) + run(" ") + rico(valor or ""))


# ---------- tabelas (sem borda, espaçamento de célula 15) ----------

TBL_PR = ('<w:tblPr><w:tblW w:w="{w}" w:type="dxa"/><w:tblCellSpacing w:w="15" w:type="dxa"/>'
          '<w:tblCellMar><w:top w:w="15" w:type="dxa"/><w:left w:w="15" w:type="dxa"/>'
          '<w:bottom w:w="15" w:type="dxa"/><w:right w:w="15" w:type="dxa"/></w:tblCellMar>'
          '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" '
          'w:noHBand="0" w:noVBand="1"/></w:tblPr>')
TR_PR = '<w:trPr><w:tblCellSpacing w:w="15" w:type="dxa"/></w:trPr>'


def tabela(grade, larguras, linhas):
    """linhas: lista de (lista de XML de parágrafo por célula, hideMark)."""
    cols = "".join(f'<w:gridCol w:w="{g}"/>' for g in grade)
    trs = []
    for celulas, hide in linhas:
        tcs = "".join(
            f'<w:tc><w:tcPr><w:tcW w:w="{larguras[i]}" w:type="dxa"/><w:vAlign w:val="center"/>'
            f'{"<w:hideMark/>" if hide else ""}</w:tcPr>{c}</w:tc>'
            for i, c in enumerate(celulas))
        trs.append(f"<w:tr>{TR_PR}{tcs}</w:tr>")
    return f'<w:tbl>{TBL_PR.format(w=sum(grade))}<w:tblGrid>{cols}</w:tblGrid>{"".join(trs)}</w:tbl>'


def p_negrito(texto):
    return par(run(texto, True), PPR_BOLD) if texto else vazio_negrito()


def p_simples(texto):
    return par(rico(texto)) if texto else vazio()


def p_pequeno(texto):
    sz = '<w:sz w:val="18"/><w:szCs w:val="18"/>'
    return par(run(texto, rpr_extra=sz), f"<w:pPr><w:rPr>{sz}</w:rPr></w:pPr>") if texto else vazio()


def tabela_participantes(participantes):
    linhas = [([p_negrito("Nome"), p_negrito("Papel / Função")], True)]
    for p in participantes or [{}]:
        linhas.append(([p_negrito(p.get("nome", "")), p_negrito(p.get("papel", ""))], False))
    return tabela([4253, 4819], [4208, 4774], linhas)


def prioridade(valor):
    v = (valor or "").strip().lower()
    marca = lambda nome: "( X )" if v.startswith(nome.lower()[:3]) else "(  )"
    return f"Alta {marca('Alta')} Média {marca('Média')} Baixa {marca('Baixa')}"


def tabela_requisitos(requisitos):
    linhas = [([p_simples("Código"), p_simples("Descrição da Solicitação"), p_simples("Prioridade")], True)]
    for r in requisitos or [{}]:
        linhas.append(([p_pequeno(r.get("codigo", "")), p_simples(r.get("descricao", "")),
                        p_simples(prioridade(r.get("prioridade")))], True))
    return tabela([1134, 6237, 1134], [1089, 6207, 1089], linhas)


def tabela_pendencias(pendencias):
    linhas = [([p_simples("Ação"), p_simples("Prazo")], True)]
    for p in pendencias or []:
        linhas.append(([p_simples(p.get("acao", "")), p_simples(p.get("prazo", ""))], False))
    # todas as atas terminam a tabela com uma linha vazia; o hideMark a deixa quase sem altura
    linhas.append(([vazio(), vazio()], True))
    return tabela([6663, 1984], [6618, 1939], linhas)


# ---------- formatação de campos ----------

def data_formulario(valor):
    """'20/10/2026' ou '2026-10-20' -> '20 / 10 / 2026'; texto livre fica como está."""
    v = (valor or "").strip()
    m = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", v)
    if m:
        return f"{int(m[1]):02d} / {int(m[2]):02d} / {m[3]}"
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return f"{m[3]} / {m[2]} / {m[1]}"
    return v


def local(valor):
    presencial = (valor or "online").strip().lower().startswith("pres")
    return "(X) Presencial ( ) Online" if presencial else "( ) Presencial (X) Online"


def nomes(lista):
    lista = [n for n in (lista or []) if n]
    if len(lista) <= 1:
        return lista[0] if lista else ""
    return ", ".join(lista[:-1]) + " e " + lista[-1]


# ---------- corpo ----------

def corpo(d, logo):
    x = []
    a = x.append

    a(logo)
    a(par(run("FORMULÁRIO DE REGISTRO DE ") + run("                    ") + run("REUNIÕES")
          + run(" COM ENTIDADE"), '<w:pPr><w:pStyle w:val="Ttulo1"/><w:jc w:val="center"/></w:pPr>'))
    a(vazio_negrito())

    # 1. Identificação
    a(titulo_secao("1. Identificação da Reunião"))
    n = NUM_IDENTIFICACAO
    a(campo(n, "Projeto:", d.get("projeto")))
    a(item(n, run("Entidade", True) + run(" / Empresa:", True) + run(" ") + rico(d.get("entidade", ""))))
    a(campo(n, "Número da reunião:", d.get("numero")))
    a(campo(n, "Data:", data_formulario(d.get("data"))))
    a(item(n, run("Horário:", True)
           + run(f" Início: {d.get('inicio', '')}, Término: {d.get('termino', '')}")))
    a(item(n, run("Local:", True) + run(" " + local(d.get("local")))))
    a(item(n, run("Plataforma (se online):", True) + run(" " + d.get("plataforma", ""))))
    a(vazio())

    # 2. Participantes
    a(titulo_secao("2. Participantes"))
    a(tabela_participantes(d.get("participantes")))
    a(vazio_negrito())

    # 3. Objetivo
    a(titulo_secao("3. Objetivo da Reunião"))
    a(par(rico(d.get("objetivo", "")), PPR_BOLD))

    # 4. Pauta (o item tratado é marcado com marca-texto amarelo, não com X)
    a(titulo_secao("4. Pauta / Assuntos Tratados", nova_pagina=True))
    pauta = d.get("pauta", {})
    marcados = {m.strip().lower() for m in pauta.get("marcados", [])}
    amarelo = '<w:highlight w:val="yellow"/>'
    for nome in PAUTA:
        a(par(run("☐ " + nome, rpr_extra=amarelo if nome.lower() in marcados else "")))
    outros = (pauta.get("outros") or "").strip()
    a(par(run("☐ Outros:", rpr_extra=amarelo if outros else "")
          + (run(" " + outros, rpr_extra=amarelo) if outros else "")))
    a(vazio())

    # 5. Decisões
    a(titulo_secao("5. Decisões Tomadas"))
    for dec in d.get("decisoes", []) or [""]:
        if isinstance(dec, str):
            dec = {"texto": dec}
        a(item(NUM_DECISOES, rico(dec.get("texto", "")), 0, "PargrafodaLista"))
        for sub in dec.get("subitens", []):
            a(item(NUM_DECISOES, rico(sub), 1, "PargrafodaLista"))

    # 6. Requisitos
    a(titulo_secao("6. Requisitos / Solicitações do Cliente", nova_pagina=True))
    a(tabela_requisitos(d.get("requisitos")))
    a(vazio())
    a(vazio_negrito())

    # 7. Pendências
    a(titulo_secao("7. Pendências e Ações Futuras"))
    a(tabela_pendencias(d.get("pendencias")))
    a(vazio_negrito())

    # 8. Impactos
    a(titulo_secao("8. Impactos no Projeto"))
    imp = d.get("impactos", {})
    marc = {m.strip().lower() for m in imp.get("marcados", [])}
    linhas = [("( X  ) " if nome.lower() in marc else "(   ) ") + nome for nome in IMPACTOS]
    a(par(run("\n".join(linhas))))
    a(par(run("Descrição do impacto (se houver):", True)))
    for paragrafo in imp.get("descricao", []) or [""]:
        if paragrafo.startswith("- "):
            a(item(NUM_DESCRICAO, rico(paragrafo[2:])))
        else:
            a(p_simples(paragrafo))
    pontos = imp.get("pontos_de_atencao", [])
    if pontos:
        a(par(run("Pontos de atenção:")))
        for ponto in pontos:
            a(item(NUM_PONTOS, rico(ponto)))

    # 9. Próxima reunião
    a(titulo_secao("9. Próxima Reunião", nova_pagina=True))
    prox = d.get("proxima_reuniao", {})
    a(campo(NUM_PROXIMA, "Data prevista:", data_formulario(prox.get("data"))))
    a(campo(NUM_PROXIMA, "Objetivo:", prox.get("objetivo")))
    a(vazio_negrito())

    # 10. Validação
    a(titulo_secao("10. Validação"))
    a(par(run("Declaro que as informações registradas acima representam fielmente o conteúdo da reunião.")))
    a(vazio())
    val = d.get("validacao", {})
    a(par(run("Representante do Cliente:", True) + run(" ") + run(val.get("representante_cliente", ""), True)))
    x.extend([vazio()] * 4)
    a(par(run("Assinatura: " + "_" * 40)))
    a(vazio())
    resp = [r for r in val.get("responsaveis", []) if r]
    a(par(run("Responsável pelo Projeto:", True) + run(" ") + run(nomes(resp), True)))
    x.extend([vazio()] * 4)
    if len(resp) > 1:
        tab = "<w:r><w:tab/></w:r>"
        a(par(run("Assinaturas:") + tab + run(" ") + tab.join(run("_" * 32) for _ in resp)))
    else:
        a(par(run("Assinatura: " + "_" * 40)))
    x.extend([vazio()] * 2)
    return "".join(x)


# ---------- pacote ----------

def gerar(conteudo, saida, modelo):
    with zipfile.ZipFile(modelo) as zin:
        doc = zin.read("word/document.xml").decode("utf-8")
        abertura = doc[: doc.index("<w:body>") + len("<w:body>")]
        corpo_modelo = doc[len(abertura):]
        logo = corpo_modelo[: corpo_modelo.index("</w:p>") + len("</w:p>")]
        if "<w:drawing>" not in logo:
            raise SystemExit("modelo inválido: o 1º parágrafo deveria conter o logo")
        sect = re.search(r"<w:sectPr\b.*?</w:sectPr>", corpo_modelo, re.S).group(0)
        novo = abertura + corpo(conteudo, logo) + sect + "</w:body></w:document>"

        agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")
        os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
        with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                dados = zin.read(info.filename)
                if info.filename == "word/document.xml":
                    dados = novo.encode("utf-8")
                elif info.filename == "docProps/core.xml":
                    xml = dados.decode("utf-8")
                    xml = re.sub(r"(<dcterms:(?:created|modified)[^>]*>)[^<]*", r"\g<1>" + agora, xml)
                    xml = re.sub(r"<cp:lastPrinted>[^<]*</cp:lastPrinted>", "", xml)
                    xml = re.sub(r"<cp:revision>\d+</cp:revision>", "<cp:revision>1</cp:revision>", xml)
                    dados = xml.encode("utf-8")
                zout.writestr(info, dados)
    print("ata gerada:", os.path.abspath(saida))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("saida")
    ap.add_argument("--modelo", default=MODELO_PADRAO)
    a = ap.parse_args()
    with open(a.json, encoding="utf-8") as f:
        gerar(json.load(f), a.saida, a.modelo)
