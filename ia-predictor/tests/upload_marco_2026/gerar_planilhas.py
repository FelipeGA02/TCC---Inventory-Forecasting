"""Planilhas "Contas a Receber" de março/2026 com dados inventados, para testar a importação.

Gera, nesta pasta:

  * `marco_2026_com_erros.xlsx`   — o mês com cada caso que a importação trata ou avisa
    (ver `README.md`, que traz o gabarito e os números esperados na tela);
  * `marco_2026_corrigida.xlsx`   — o mesmo mês com os erros corrigidos;
  * `erro_sem_vendas.xlsx`, `erro_so_empresa_desconhecida.xlsx`, `erro_formato.csv` —
    recusas da planilha inteira.

As vendas são inventadas: cada dia de loja aberta de março recebe o número de notas de um
dia real da mesma loja e do mesmo dia da semana, e cada nota copia só produto, quantidade e
preço de uma nota real desse conjunto (fev/2026 e mar/2025, sem encomendas grandes nem
devoluções). Número da nota, cliente, operador e vendedor são fictícios. A exceção são as
notas que testam a duplicata com a base: são cópias exatas de notas de 27 e 28/02/2026 que
já estão no banco (chave da Etapa 1: nota, produto, data, quantidade e valor), com cliente
fictício.

Lê o banco só para sortear (nunca grava). Use o SQLite local — o mesmo conteúdo do Neon até
28/02/2026.

Uso (a partir de `ia-predictor/`):
    python -m tests.upload_marco_2026.gerar_planilhas --banco caminho/floricultura.db
"""
from __future__ import annotations

import argparse
import random
import sqlite3
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import openpyxl
import pandas as pd

AQUI = Path(__file__).resolve().parent
SEMENTE = 20260301
INICIO, FIM = date(2026, 3, 1), date(2026, 3, 31)

EMPRESA = {"jardim-canada": "FLORICULTURA VERDE PERTO CANADÁ LTDA", "itabirito": "VERDE PERTO JARDINAGEM LTDA"}
GARDEN = "GARDEN CENTER VERDE PERTO LTDA"  # CNPJ do Garden Center: também é Jardim Canadá
EMPRESA_DESCONHECIDA = "VERDE PERTO FILIAL BH LTDA"
TITULO_EMPRESA = "VERDE PERTO JARDINAGEM"
OPERADORES = {"jardim-canada": ["CAIXA CANADA 1", "CAIXA CANADA 2"], "itabirito": ["CAIXA ITABIRITO"]}
VENDEDORES = [f"VENDEDOR TESTE {i:02d}" for i in range(1, 9)]
LINHAS_POR_PAGINA = 75

# Dias em que a planilha com erros não traz a loja (aviso de dias faltando)
DIAS_FALTANDO = {"jardim-canada": {date(2026, 3, 2)},
                 "itabirito": {date(2026, 3, 16), date(2026, 3, 17), date(2026, 3, 18)}}
PRODUTO_NOVO = ("00999001", "SUBSTRATO PARA SUCULENTAS 5KG", 2, 24.9)
ENCOMENDA = ("3", 2400, 11.9)  # GRAMA ESMERALDA, m²: acima do limiar de Jardim Canadá (ADR-018)


# --------------------------------------------------------------------------- dados

def _ler_base(banco: Path) -> tuple[pd.DataFrame, dict, dict]:
    con = sqlite3.connect(f"file:{banco.as_posix()}?mode=ro", uri=True)
    vendas = pd.read_sql(
        "select s.unit_id, s.sale_date, s.document_type, s.document_number, s.product_code, s.quantity, "
        "s.unit_price, s.gross_amount, s.discount, s.net_amount, s.payment_method, s.is_registered_customer, "
        "s.is_bulk_order from sales s where s.sale_date between '2025-03-01' and '2025-03-31' "
        "or s.sale_date between '2026-01-26' and '2026-02-28'", con)
    nomes = dict(con.execute("select code, name from products").fetchall())
    numeros = {(u, t): int(n) for u, t, n in con.execute(
        "select unit_id, document_type, max(cast(document_number as integer)) from sales group by 1, 2")}
    con.close()
    vendas["sale_date"] = pd.to_datetime(vendas["sale_date"]).dt.date
    return vendas, nomes, numeros


def _notas(vendas: pd.DataFrame) -> list[dict]:
    """Uma entrada por nota real: loja, data, tipo, pagamento e as linhas de produto."""
    notas = []
    for (loja, dia, tipo, numero), g in vendas.groupby(
            ["unit_id", "sale_date", "document_type", "document_number"], sort=True):
        notas.append({"loja": loja, "dia": dia, "tipo": tipo, "numero": numero,
                      "pagamento": g["payment_method"].iloc[0] or "DINHEIRO",
                      "cadastrado": bool(g["is_registered_customer"].iloc[0]),
                      "grande": bool(g["is_bulk_order"].any()), "negativa": bool((g["quantity"] <= 0).any()),
                      "linhas": [{"cod": r.product_code, "qtd": float(r.quantity), "unit": float(r.unit_price),
                                  "total": float(r.gross_amount), "desc": float(r.discount or 0),
                                  "liq": float(r.net_amount)} for r in g.itertuples()]})
    return notas


def _abertos() -> list[date]:
    dias = (INICIO + timedelta(days=i) for i in range((FIM - INICIO).days + 1))
    return [d for d in dias if d.weekday() != 6]  # março/2026: nenhum feriado em dia útil


def gerar_mes(notas_reais: list[dict], numeros: dict, rnd: random.Random) -> list[dict]:
    """As notas inventadas de março, das 2 lojas, em ordem de data."""
    sorteio = [n for n in notas_reais if n["dia"] < date(2026, 2, 27) and not n["grande"] and not n["negativa"]]
    por_dia: dict[tuple, list[dict]] = {}
    for n in sorteio:
        por_dia.setdefault((n["loja"], n["dia"].weekday()), []).append(n)
    contagem: dict[tuple, list[int]] = {}
    for (loja, dia_semana), lista in por_dia.items():
        por_data: dict[date, int] = {}
        for n in lista:
            por_data[n["dia"]] = por_data.get(n["dia"], 0) + 1
        contagem[(loja, dia_semana)] = [c for c in por_data.values() if c >= 10]  # sem os dias de meio expediente
    proximo = dict(numeros)
    mes = []
    for dia in _abertos():
        for loja in ("jardim-canada", "itabirito"):
            for modelo in rnd.sample(por_dia[(loja, dia.weekday())],
                                     k=rnd.choice(contagem[(loja, dia.weekday())])):
                proximo[(loja, modelo["tipo"])] = proximo.get((loja, modelo["tipo"]), 0) + 1
                cliente = (f"{9000 + rnd.randrange(400)} - CLIENTE FICTICIO {rnd.randrange(1, 400):03d}"
                           if modelo["cadastrado"] else "1 - CONSUMIDOR")
                empresa = GARDEN if loja == "jardim-canada" and rnd.random() < 0.08 else EMPRESA[loja]
                mes.append({"loja": loja, "dia": dia, "tipo": modelo["tipo"],
                            "numero": str(proximo[(loja, modelo["tipo"])]), "pagamento": modelo["pagamento"],
                            "cliente": cliente, "empresa": empresa, "operador": rnd.choice(OPERADORES[loja]),
                            "vendedor": rnd.choice(VENDEDORES), "linhas": deepcopy(modelo["linhas"]),
                            "caso": None})
    return mes


def _nota(mes: list[dict], loja: str, dia: date, minimo_linhas: int = 1, pular: int = 0) -> dict:
    candidatas = [n for n in mes if n["loja"] == loja and n["dia"] == dia and len(n["linhas"]) >= minimo_linhas
                  and n["caso"] is None]
    return candidatas[pular]


def _nova_nota(mes: list[dict], numeros_usados: dict, loja: str, dia: date, linhas: list[dict], caso: str,
               cliente: str = "1 - CONSUMIDOR") -> dict:
    tipo = "C4" if loja == "jardim-canada" else "C9"
    numeros_usados[(loja, tipo)] += 1
    nota = {"loja": loja, "dia": dia, "tipo": tipo, "numero": str(numeros_usados[(loja, tipo)]),
            "pagamento": "PIX", "cliente": cliente, "empresa": EMPRESA[loja], "operador": OPERADORES[loja][0],
            "vendedor": VENDEDORES[0], "linhas": linhas, "caso": caso}
    pos = max(i for i, n in enumerate(mes) if n["dia"] <= dia) + 1
    mes.insert(pos, nota)
    return nota


def _linha(cod: str, qtd: float, unit: float) -> dict:
    total = round(qtd * unit, 2)
    return {"cod": cod, "qtd": qtd, "unit": unit, "total": total, "desc": 0.0, "liq": total}


def montar_casos(mes: list[dict], notas_reais: list[dict], numeros: dict) -> list[dict]:
    """Marca em `mes` as notas de cada caso (campo `caso`, lido por `escrever`) e devolve o
    mês com as notas da duplicata com a base no começo. Cada caso tem a versão errada (só
    na planilha com erros) e a certa (na corrigida)."""
    usados = {k: max(int(n["numero"]) for n in mes if (n["loja"], n["tipo"]) == k)
              for k in {(n["loja"], n["tipo"]) for n in mes}}
    for k in (("jardim-canada", "C4"), ("itabirito", "C9")):
        usados.setdefault(k, numeros.get(k, 0))

    # dias faltando: a planilha com erros não traz essas notas
    for n in mes:
        if n["dia"] in DIAS_FALTANDO[n["loja"]]:
            n["caso"] = "dia_faltando"

    _nota(mes, "itabirito", date(2026, 3, 5))["caso"] = "sem_cliente"
    _nota(mes, "jardim-canada", date(2026, 3, 10))["caso"] = "sem_cabecalho_produto"
    _nota(mes, "jardim-canada", date(2026, 3, 12), minimo_linhas=2)["caso"] = "emissao_vazia"
    _nota(mes, "itabirito", date(2026, 3, 20), minimo_linhas=2)["caso"] = "data_invalida"
    _nota(mes, "jardim-canada", date(2026, 3, 24))["caso"] = "data_fora_do_formato"
    _nota(mes, "itabirito", date(2026, 3, 13))["caso"] = "cliente_sem_nome"
    _nota(mes, "jardim-canada", date(2026, 3, 4), minimo_linhas=2)["caso"] = "espacos_extras"
    for _ in range(2):
        _nota(mes, "jardim-canada", date(2026, 3, 25))["caso"] = "empresa_desconhecida"
    _nota(mes, "jardim-canada", date(2026, 3, 27), minimo_linhas=2)["caso"] = "nota_repetida_na_planilha"
    # linha a linha: uma linha errada numa nota com outras linhas boas
    _nota(mes, "jardim-canada", date(2026, 3, 6), minimo_linhas=3)["caso"] = "produto_sem_codigo"
    _nota(mes, "itabirito", date(2026, 3, 11), minimo_linhas=3)["caso"] = "quantidade_texto"
    _nota(mes, "jardim-canada", date(2026, 3, 19), minimo_linhas=3)["caso"] = "valor_texto"

    # casos certos, iguais nas 2 planilhas
    _nova_nota(mes, usados, "jardim-canada", date(2026, 3, 18), [_linha(*ENCOMENDA)], "encomenda_grande",
               cliente="9399 - CLIENTE FICTICIO PAISAGISMO")
    _nova_nota(mes, usados, "itabirito", date(2026, 3, 23),
               [_linha(PRODUTO_NOVO[0], PRODUTO_NOVO[2], PRODUTO_NOVO[3])], "produto_novo")
    _nova_nota(mes, usados, "itabirito", date(2026, 3, 9),
               [_linha("00013475", 10, 12.8), _linha("2909", 1, 39.5), _linha("00013475", 10, 12.8)],
               "produto_repetido_na_nota")
    _nova_nota(mes, usados, "jardim-canada", date(2026, 3, 3),
               [_linha(c, 1, p) for c, p in [("00030197", 13.8), ("00030325", 34.5), ("2342", 34.5),
                                             ("637", 7.5), ("650", 12.0), ("1340", 18.0)] * 4],
               "nota_longa_com_quebra_de_pagina")

    # duplicata com a base: cópia exata de notas que já estão no banco
    copias = []
    for loja, dia, k in (("jardim-canada", date(2026, 2, 28), 3), ("itabirito", date(2026, 2, 27), 2)):
        for real in [n for n in notas_reais if n["loja"] == loja and n["dia"] == dia and not n["negativa"]][:k]:
            copias.append({**deepcopy(real), "cliente": "1 - CONSUMIDOR", "empresa": EMPRESA[loja],
                           "operador": OPERADORES[loja][0], "vendedor": VENDEDORES[1], "caso": "duplicada_com_base"})
    return copias + mes


# --------------------------------------------------------------------------- escrita

class _Folha:
    """Escreve no layout do relatório: colunas fixas e quebra de página a cada
    `LINHAS_POR_PAGINA` linhas (marca de impressão + cabeçalho repetido), como no original."""

    def __init__(self, ws, titulo: str):
        self.ws, self.titulo, self.linhas, self.pagina = ws, titulo, 0, 1
        self._linha({1: TITULO_EMPRESA})
        self._linha({})
        self._linha({1: titulo})
        self._linha({})

    def _linha(self, celulas: dict):
        valores = [None] * 22
        for col, v in celulas.items():
            valores[col - 1] = v
        self.ws.append(valores)
        self.linhas += 1

    def quebra_se_preciso(self):
        if self.linhas < LINHAS_POR_PAGINA * self.pagina:
            return
        self._linha({})
        self._linha({1: "14/04/2026 - 14:28", 18: f"{self.pagina}/999"})
        self._linha({})
        self._linha({1: TITULO_EMPRESA})
        self._linha({})
        self._linha({1: self.titulo})
        self._linha({})
        self.pagina += 1

    def linha(self, celulas: dict):
        self._linha(celulas)


def _escrever_nota(f: _Folha, n: dict, nomes: dict, com_erros: bool):
    caso = n["caso"] if com_erros else None
    emissao = f"{n['dia']:%d/%m/%Y}"
    if caso == "emissao_vazia":
        emissao = ""
    elif caso == "data_invalida":
        emissao = f"{n['dia'].day:02d}/13/2026"
    elif caso == "data_fora_do_formato":
        emissao = f"{n['dia']:%Y-%m-%d}"
    cliente = n["cliente"]
    if caso == "cliente_sem_nome":
        cliente = "3655 -"
    elif n["caso"] == "cliente_sem_nome":
        cliente = "3655 - CLIENTE FICTICIO 3655"
    empresa = EMPRESA_DESCONHECIDA if caso == "empresa_desconhecida" else n["empresa"]
    if caso == "espacos_extras":
        empresa = "  " + empresa.replace(" ", "  ") + "   "

    f.quebra_se_preciso()
    f.linha({1: f"Documento: {n['tipo']} {n['numero']}  ", 3: f"Pagto:{n['pagamento']}  ",
             8: f"Emissão: {emissao}", 17: f"Operador: {n['operador']}"})
    if caso != "sem_cliente":
        f.linha({1: f"Cliente: {cliente}"})
    f.linha({1: f"Empresa: {empresa}   ", 13: f"Vendedor: {n['vendedor']}"})
    f.linha({1: "Obs: "})
    f.linha({})
    if caso != "sem_cabecalho_produto":
        f.linha({1: "Produto", 8: "Qtdade", 9: "Vl. Unit.", 14: "Vl. Total", 15: "Vl. Desconto",
                 18: "Tot. Líq.", 20: "ICMS Ret."})
    for i, l in enumerate(n["linhas"]):
        f.quebra_se_preciso()
        nome = nomes.get(l["cod"], PRODUTO_NOVO[1] if l["cod"] == PRODUTO_NOVO[0] else "PRODUTO")
        produto = f"{l['cod']} - {nome}"
        qtd, total = l["qtd"], l["total"]
        if i == 1 and caso == "produto_sem_codigo":
            produto = nome
        if i == 1 and caso == "quantidade_texto":
            qtd = "dez"
        if i == 1 and caso == "valor_texto":
            total = f"R$ {total:.2f}".replace(".", ",")
        if i == 0 and caso == "espacos_extras":
            produto = f"  {l['cod']}  -  {nome.replace(' ', '   ')}  "
        f.linha({1: produto, 8: qtd, 9: l["unit"], 14: total, 15: l["desc"], 18: l["liq"], 20: 0})
    soma = lambda c: round(sum(l[c] for l in n["linhas"]), 2)
    f.linha({})
    f.linha({1: "Totais", 6: soma("qtd"), 14: soma("total"), 15: soma("desc"), 18: soma("liq"), 20: 0})
    f.linha({1: "Frete/IPI/Retenções", 14: 0, 16: 0, 19: 0})
    f.linha({1: "Total líquido", 5: soma("liq")})
    f.linha({})
    f.linha({1: ""})


def escrever(caminho: Path, notas: list[dict], nomes: dict, com_erros: bool):
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("Página 1")
    datas = [n["dia"] for n in notas]
    f = _Folha(ws, f"Consulta lançamento de vendas ( Total Documento ) de {min(datas):%d/%m/%Y} "
                   f"até {max(datas):%d/%m/%Y}")
    total = {"liq": 0.0, "qtd": 0.0}
    for n in notas:
        if com_erros and n["caso"] == "dia_faltando":
            continue
        if not com_erros and n["caso"] == "duplicada_com_base":
            continue
        _escrever_nota(f, n, nomes, com_erros)
        if com_erros and n["caso"] == "nota_repetida_na_planilha":
            _escrever_nota(f, n, nomes, com_erros)
        total["liq"] += sum(l["liq"] for l in n["linhas"])
        total["qtd"] += sum(l["qtd"] for l in n["linhas"])
    f.linha({})
    f.linha({1: "Total geral...", 6: round(total["qtd"], 2), 18: round(total["liq"], 2), 20: 0})
    f.linha({1: "Frete/IPI/Retenções", 12: 0, 15: 0, 18: 0})
    f.linha({1: "Total geral líquido", 5: round(total["liq"], 2)})
    f.linha({})
    f.linha({1: "14/04/2026 - 14:28", 18: f"{f.pagina}/{f.pagina}"})
    wb.save(caminho)


def escrever_recusas(notas: list[dict], nomes: dict):
    # sem nenhum "Documento:": a planilha não é o relatório
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "Relatório de estoque — março/2026"
    ws["A3"], ws["B3"] = "Produto", "Saldo"
    ws["A4"], ws["B4"] = "3 - GRAMA ESMERALDA", 1200
    wb.save(AQUI / "erro_sem_vendas.xlsx")

    # todas as notas de empresa sem loja cadastrada
    so_desconhecida = [{**deepcopy(n), "caso": "empresa_desconhecida"}
                       for n in notas if n["loja"] == "jardim-canada" and n["dia"] == date(2026, 3, 30)][:5]
    escrever(AQUI / "erro_so_empresa_desconhecida.xlsx", so_desconhecida, nomes, com_erros=True)

    (AQUI / "erro_formato.csv").write_text(
        "Documento;Emissao;Produto;Qtdade\nC4 1;02/03/2026;3 - GRAMA ESMERALDA;10\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--banco", type=Path, required=True, help="SQLite com a base até 28/02/2026")
    args = parser.parse_args()
    rnd = random.Random(SEMENTE)
    vendas, nomes, numeros = _ler_base(args.banco)
    reais = _notas(vendas)
    notas = montar_casos(gerar_mes(reais, numeros, rnd), reais, numeros)
    escrever(AQUI / "marco_2026_com_erros.xlsx", notas, nomes, com_erros=True)
    escrever(AQUI / "marco_2026_corrigida.xlsx", notas, nomes, com_erros=False)
    escrever_recusas(notas, nomes)
    casos = {}
    for n in notas:
        if n["caso"]:
            casos.setdefault(n["caso"], []).append(f"{n['loja']} {n['dia']:%d/%m} {n['tipo']} {n['numero']}")
    for caso, lista in casos.items():
        print(f"{caso:32} {len(lista):4}  {lista[0]}{' …' if len(lista) > 1 else ''}")


if __name__ == "__main__":
    main()
