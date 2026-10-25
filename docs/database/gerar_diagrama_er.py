"""Gera `modelo_dados.drawio` (diagrama entidade-relacionamento) a partir do ORM.

Tabelas, colunas, tipos, chaves, relacionamentos, índices e cascatas saem de
`backend/infrastructure/database.py`; aqui fica só a posição e o grupo de cada tabela.
Rode de novo sempre que o modelo mudar.

Uso (a partir de `ia-predictor/`):
    python ../docs/database/gerar_diagrama_er.py
"""
from __future__ import annotations

import os
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.getcwd())
from backend.infrastructure.database import Base  # noqa: E402

SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelo_dados.drawio")

# grupo: (rótulo, preenchimento do cabeçalho, borda)
GRUPOS = {
    "acesso": ("Acesso e cargas", "#E6E6E6", "#666666"),
    "vendas": ("Vendas", "#DAE8FC", "#6C8EBF"),
    "catalogo": ("Catálogo", "#D5E8D4", "#82B366"),
    "previsao": ("Previsão", "#FFE6CC", "#D79B00"),
}

# tabela: (grupo, (x, y))
LAYOUT = {
    "users": ("acesso", (40, 40)),
    "processing_log": ("acesso", (40, 300)),
    "revoked_tokens": ("acesso", (40, 860)),
    "sales": ("vendas", (640, 40)),
    "calendar_days": ("vendas", (640, 520)),
    "units": ("catalogo", (1240, 40)),
    "products": ("catalogo", (1240, 200)),
    "categories": ("catalogo", (1240, 440)),
    "retrain_history": ("previsao", (1840, 40)),
    "model_artifacts": ("previsao", (1840, 440)),
    "forecast_runs": ("previsao", (2440, 40)),
    "forecasts_cache": ("previsao", (2440, 400)),
    "backtest_points": ("previsao", (2440, 720)),
}

W_KEY, W_NOME, W_TIPO = 46, 200, 200
W = W_KEY + W_NOME + W_TIPO
H_ROW, H_HEAD = 26, 32
ESTILO_CELULA = ("shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;bottom=0;"
                 "right=0;overflow=hidden;html=1;whiteSpace=wrap;fontSize=12;")
ESTILO_ARESTA = ("fontSize=10;html=1;endArrow=ERzeroToMany;endFill=0;startFill=0;rounded=0;"
                 "strokeColor=#7F7F7F;fontColor=#7F7F7F;")


def v(s: str) -> str:
    return escape(s, {'"': "&quot;"})


def chave(col) -> str:
    marcas = []
    if col.primary_key:
        marcas.append("PK")
    if col.foreign_keys:
        marcas.append("FK")
    if col.unique:
        marcas.append("UQ")
    return ",".join(marcas)


def tipo(col) -> str:
    t = str(col.type).split("(")[0]
    if col.nullable and not col.primary_key:
        t += " NULL"
    if col.info.get("hint"):
        t += f"  {col.info['hint']}"
    return t


def relacoes(tabelas):
    """(tabela filha, coluna FK, tabela pai, coluna PK, FK aceita nulo, ondelete)."""
    for nome, t in tabelas.items():
        for col in t.columns:
            for fk in col.foreign_keys:
                yield nome, col.name, fk.column.table.name, fk.column.name, col.nullable, fk.ondelete


def pagina(id_, nome, cells) -> str:
    return (f'<diagram id="{id_}" name="{v(nome)}"><mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" math="0" '
            f'shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>{"".join(cells)}'
            f'</root></mxGraphModel></diagram>')


def faixas(cells, largura, y=-30):
    """Faixa colorida com o nome do grupo acima das colunas de tabelas."""
    xs = {}
    for g, (x, _) in LAYOUT.values():
        lo, hi = xs.get(g, (x, x))
        xs[g] = (min(lo, x), max(hi, x))
    for i, (g, (lo, hi)) in enumerate(xs.items()):
        rotulo, head, borda = GRUPOS[g]
        cells.append(
            f'<mxCell id="g{i}" value="{v(rotulo)}" style="rounded=1;whiteSpace=wrap;html=1;'
            f'fillColor={head};strokeColor={borda};fontStyle=1;fontSize=16;" vertex="1" parent="1">'
            f'<mxGeometry x="{lo}" y="{y}" width="{hi - lo + largura}" height="40" as="geometry"/></mxCell>')


def colunas(tabelas) -> str:
    cells, linha = [], {}

    def celula(id_, parent, valor, x, w, estilo):
        cells.append(
            f'<mxCell id="{id_}" value="{v(valor)}" style="{ESTILO_CELULA}{estilo}" vertex="1" '
            f'parent="{parent}"><mxGeometry x="{x}" width="{w}" height="{H_ROW}" as="geometry">'
            f'<mxRectangle width="{w}" height="{H_ROW}" as="alternateBounds"/></mxGeometry></mxCell>')

    for nome, (grupo, (x, y)) in LAYOUT.items():
        _, head, borda = GRUPOS[grupo]
        cols = list(tabelas[nome].columns)
        tid = f"t_{nome}"
        cells.append(
            f'<mxCell id="{tid}" value="{v(nome)}" style="shape=table;startSize={H_HEAD};container=1;'
            f'collapsible=1;childLayout=tableLayout;fixedRows=1;rowLines=0;fontStyle=1;align=center;'
            f'resizeLast=1;html=1;fillColor={head};strokeColor={borda};swimlaneFillColor=#FFFFFF;fontSize=14;" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{W}" '
            f'height="{H_HEAD + H_ROW * len(cols)}" as="geometry"/></mxCell>')
        for i, col in enumerate(cols):
            rid = f"{tid}_r{i}"
            linha[(nome, col.name)] = rid
            cells.append(
                f'<mxCell id="{rid}" value="" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;'
                f'swimlaneBody=0;fillColor=none;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];'
                f'portConstraint=eastwest;top=0;left=0;right=0;bottom=0;html=1;" vertex="1" parent="{tid}">'
                f'<mxGeometry y="{H_HEAD + H_ROW * i}" width="{W}" height="{H_ROW}" as="geometry"/></mxCell>')
            celula(f"{rid}_k", rid, chave(col), 0, W_KEY, "fontStyle=1;align=center;fontColor=#555555;")
            celula(f"{rid}_n", rid, col.name, W_KEY, W_NOME,
                   ("fontStyle=5;" if col.primary_key else "") + "align=left;spacingLeft=6;")
            celula(f"{rid}_t", rid, tipo(col), W_KEY + W_NOME, W_TIPO,
                   "align=left;spacingLeft=6;fontColor=#666666;fontSize=11;")

    cascatas = []
    for i, (filho, fk, pai, pk, nulo, ondelete) in enumerate(relacoes(tabelas)):
        inicio = "ERzeroToOne" if nulo else "ERmandOne"
        cells.append(
            f'<mxCell id="e{i}" style="edgeStyle=entityRelationEdgeStyle;{ESTILO_ARESTA}startArrow={inicio};" '
            f'edge="1" parent="1" source="{linha[(pai, pk)]}" target="{linha[(filho, fk)]}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')
        if ondelete:
            cascatas.append(f"{filho}.{fk} → {pai}: ON DELETE {ondelete}")

    restricoes = []
    for nome, t in tabelas.items():
        for c in t.constraints:
            if c.__class__.__name__ == "UniqueConstraint" and len(c.columns) > 1:
                restricoes.append(f"{nome}: UNIQUE ({', '.join(x.name for x in c.columns)})")
        for ix in sorted(t.indexes, key=lambda i: i.name):
            if len(ix.columns) > 1:
                restricoes.append(f"{nome}: índice ({', '.join(x.name for x in ix.columns)})")

    faixas(cells, W)
    legenda = (
        "<b>Legenda</b><br>"
        "PK = chave primária (sublinhada) · FK = chave estrangeira · UQ = único<br>"
        "NULL = coluna aceita nulo · texto após o tipo = valores aceitos<br>"
        "─┤├──&lt; : 1 para N (FK obrigatória) · ─o┤──&lt; : 0..1 para N (FK opcional)<br><br>"
        "<b>Índices compostos</b><br>" + "<br>".join(restricoes) + "<br><br>"
        "<b>Exclusão em cascata</b><br>" + "<br>".join(cascatas) + "<br><br>"
        "<b>Notas</b><br>"
        "A planilha enviada não é guardada: os campos usados vão para sales e<br>"
        "processing_log guarda nome, SHA-256 e o resultado da carga.<br>"
        "sales não guarda nome de cliente, vendedor ou operador (LGPD).<br>"
        "Resumos por loja, categoria e produto são calculados de sales (não gravados).<br>"
        "params e metrics de model_artifacts são JSON (ver docstring do ORM).<br>"
        "O painel lê os próximos 14 dias da última forecast_runs com status = done<br>"
        "(gerada ao fim de cada treino e quando calendar_days muda depois dele)."
    )
    cells.append(
        f'<mxCell id="legenda" value="{v(legenda)}" style="rounded=1;whiteSpace=wrap;html=1;align=left;'
        f'verticalAlign=top;spacing=12;fillColor=#FFFFFF;strokeColor=#999999;fontSize=12;" vertex="1" '
        f'parent="1"><mxGeometry x="640" y="760" width="{W + 60}" height="420" as="geometry"/></mxCell>')
    return pagina("modelo", "Modelo de dados", cells)


def main() -> None:
    tabelas = Base.metadata.tables
    faltando = set(tabelas) ^ set(LAYOUT)
    if faltando:
        raise SystemExit(f"Ajuste LAYOUT: tabelas sem posição ou que não existem mais: {faltando}")
    xml = f'<mxfile host="app.diagrams.net">{colunas(tabelas)}</mxfile>'
    with open(SAIDA, "w", encoding="utf-8") as fh:
        fh.write(xml)
    print(f"{len(tabelas)} tabelas, {len(list(relacoes(tabelas)))} relacionamentos -> {SAIDA}")


if __name__ == "__main__":
    main()
