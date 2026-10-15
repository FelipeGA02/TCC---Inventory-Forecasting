"""Exporta cada registro da base para a tela "Conferir Dados" do frontend.

A base tem ~350 mil linhas: um arquivo unico pesaria dezenas de MB e travaria a tela. Por
isso sai um arquivo POR MES, em formato colunar compacto, em
`app-react/public/dados/registros/AAAA-MM.json`, mais um `indice.json` com os meses e as
contagens. A tela carrega so o mes escolhido.

Campos por linha: dia, loja, nota, produto (codigo), quantidade, valor unitario, desconto,
valor liquido, forma de pagamento, tipo de cliente e encomenda. Nomes de cliente, vendedor e
operador NAO saem (dados pessoais — regra de seguranca do projeto); o cliente vira so
"consumidor" ou "cadastrado".

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.frontend_mock.gerar_registros_frontend
"""
from __future__ import annotations

import json
import os

import pandas as pd

from training_scripts.frontend_mock.gerar_dados_frontend import BASE, CAT_FORA, CAT_POR_GRUPO, UNIDADES
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA, marcar_encomendas

_AQUI = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
SAIDA = os.path.join(_REPO, "app-react", "public", "dados", "registros")

COLUNAS = ["dia", "loja", "nota", "produto", "quantidade", "valor_unitario", "desconto",
           "valor_liquido", "pagamento", "cadastrado", "encomenda"]


def num(v: float, casas: int = 2):
    v = round(float(v), casas)
    return int(v) if v.is_integer() else v


def main():
    cols = ["doc_numero", "emissao", "pagamento", "cliente_nome", "produto_cod", "produto_nome",
            "qtdade", "vl_unit", "vl_desconto", "tot_liq", "unidade", "categoria"]
    df = pd.read_csv(BASE, sep=";", usecols=cols, dtype={"produto_cod": str, "doc_numero": str,
                                                         "cliente_nome": str, "pagamento": str})
    df = df[df["categoria"] != "Servico e taxa"].copy()
    df["emissao"] = pd.to_datetime(df["emissao"])
    df["cat"] = df["categoria"].map(CAT_POR_GRUPO).fillna(CAT_FORA)
    df["encomenda"] = marcar_encomendas(df, LIMIAR_QTD_VENDA)
    df["cadastrado"] = df["cliente_nome"].fillna("").str.strip().str.upper() != "CONSUMIDOR"
    df["pagamento"] = df["pagamento"].fillna("").str.strip().replace("", "NÃO INFORMADO").str.title()
    lojas = {u["nome"]: i for i, u in enumerate(UNIDADES)}
    df["loja"] = df["unidade"].map(lojas)
    df = df.sort_values(["emissao", "loja", "doc_numero"], kind="stable")

    pagamentos = sorted(df["pagamento"].unique())
    idx_pag = {p: i for i, p in enumerate(pagamentos)}
    os.makedirs(SAIDA, exist_ok=True)
    meses = []
    for mes, g in df.groupby(df["emissao"].dt.strftime("%Y-%m")):
        nomes = g.groupby("produto_cod").agg(nome=("produto_nome", "last"), cat=("cat", "first"))
        linhas = [[int(r.emissao.day), int(r.loja), r.doc_numero, r.produto_cod, num(r.qtdade, 1),
                   num(r.vl_unit), num(r.vl_desconto), num(r.tot_liq), idx_pag[r.pagamento],
                   int(r.cadastrado), int(r.encomenda)]
                  for r in g.itertuples()]
        arquivo = {"mes": mes, "colunas": COLUNAS,
                   "produtos": {c: [r["nome"], r["cat"]] for c, r in nomes.iterrows()},
                   "linhas": linhas}
        with open(os.path.join(SAIDA, f"{mes}.json"), "w", encoding="utf-8") as fh:
            json.dump(arquivo, fh, ensure_ascii=False, separators=(",", ":"))
        meses.append({"mes": mes, "registros": len(linhas),
                      "por_loja": {u["id"]: int((g["loja"] == i).sum()) for i, u in enumerate(UNIDADES)}})

    indice = {"gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
              "lojas": [u["id"] for u in UNIDADES], "pagamentos": pagamentos,
              "limiar_encomenda_un": LIMIAR_QTD_VENDA, "total_registros": int(len(df)), "meses": meses}
    with open(os.path.join(SAIDA, "indice.json"), "w", encoding="utf-8") as fh:
        json.dump(indice, fh, ensure_ascii=False, separators=(",", ":"))
    tamanho = sum(os.path.getsize(os.path.join(SAIDA, f)) for f in os.listdir(SAIDA))
    print(f"[ok] {len(meses)} meses · {len(df):,} registros · {tamanho / 1e6:.1f} MB em {SAIDA}")


if __name__ == "__main__":
    main()
