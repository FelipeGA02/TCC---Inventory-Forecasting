"""Base de demonstração no SQLite: o schema e o volume do Neon, com as vendas inventadas (LGPD).

Para a apresentação: um SQLite com as mesmas tabelas, colunas e índices do Neon (inclusive as
tabelas do treino anterior, vazias, e `processing_log.retrain_id`), as mesmas contagens — vendas
por planilha e loja, planilhas, séries de cada treino e o motivo de cada série sem previsão,
linhas do log, previsões, walk-forward e histórico — e os mesmos ids e horários do treino. Nenhum
número de venda vem do Neon.

O que é lido do Neon (só leitura: a sessão abre com `TRANSACTION READ ONLY`):
  * estrutura: o schema, lojas, categorias, o catálogo (código, nome, categoria), o calendário
    das lojas, os usuários (sem a senha) e as planilhas (nome, mês, horários, linhas);
  * contagens: linhas de venda e encomendas grandes por planilha e loja, quais produtos cada loja
    vendeu, a proporção dos tipos de documento, das formas de pagamento, de cliente cadastrado,
    de desconto e de devolução;
  * o último treino concluído: a configuração, os horários e cada série com o status e o motivo.

O que é inventado (`semente`): toda quantidade, preço, desconto, valor, número de nota, forma de
pagamento e cliente de cada venda, e o tamanho das encomendas grandes. A venda diária de cada
categoria e produto de grama segue um padrão limpo — semana de dia útil, temporada, tendência,
nível que varia devagar e as datas comemorativas do ADR-019 — com ruído moderado, para o treino
ter resultados bons e coerentes. Os produtos de grama sem previsão no Neon recebem venda esparsa
com os mesmos dias com venda (ou o mesmo histórico curto), e ficam sem previsão pelo mesmo motivo.

Os resultados das séries não são inventados: saem do treino do sistema (`servico_previsao`, com
a configuração do treino do Neon) sobre as vendas inventadas — as mesmas séries, o log, a
gravação e o histórico. Por padrão o ajuste de cada série é o rápido (`treinar_serie_rapida`:
ordem fixa, ajustada antes do walk-forward e aplicada a cada origem, ~2 min no total); com
`--treino-completo`, o do botão "Treinar previsões" (grid de ordens e reajuste a cada origem,
~1 h). Depois os ids (treino, séries, log, previsões, walk-forward, histórico, vendas) e os
horários do treino viram os do Neon.

Uso (a partir de `ia-predictor/`):
    python -m backend.scripts.gerar_base_demonstracao [--destino floricultura.db] [--recriar]
        [--origem URL_DO_NEON] [--semente 2026] [--workers N] [--sem-treino] [--treino-completo]

`--origem`: o banco a espelhar (padrão: `DATABASE_URL` do `.env`). Depois, para usar a base:
`DATABASE_URL=sqlite:///./floricultura.db` no `.env`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import MetaData, create_engine, insert, inspect, text

IA_PREDICTOR = Path(__file__).resolve().parents[2]
LOTE = 5_000

CATEGORIAS_PREVISAO = ("grama", "plantas-diversas", "produtos-de-jardim", "flores-de-corte")
CATEGORIA_SERVICO = "servico-e-taxa"
OUTRAS = ("plantas-diversas", "produtos-de-jardim", "flores-de-corte")  # as categorias de muitos SKUs

# --------------------------------------------------------------------------- #
# Padrão das vendas inventadas (un./dia no fluxo, sem as encomendas grandes)
# --------------------------------------------------------------------------- #
NIVEL = {
    "jardim-canada": {"grama": 950.0, "plantas-diversas": 520.0, "produtos-de-jardim": 330.0, "flores-de-corte": 48.0},
    "itabirito": {"grama": 420.0, "plantas-diversas": 360.0, "produtos-de-jardim": 190.0, "flores-de-corte": 42.0},
}
# Parte de cada produto de grama com previsão na grama da loja; produto fora da lista: 3%
PARTICIPACAO_GRAMA = {
    "jardim-canada": {"147": 0.34, "3": 0.28, "710": 0.10, "00150005": 0.05, "166": 0.045, "167": 0.04,
                      "1293": 0.035, "00013475": 0.03, "1739": 0.025, "1294": 0.02, "00020227": 0.02},
    "itabirito": {"147": 0.40, "00013475": 0.30, "710": 0.14, "3": 0.10},
}
PARTICIPACAO_PADRAO = 0.03
# seg..sáb (domingo fechado): pico de ter a qui, sábado fraco; Flores de corte na sexta (doc 00 §3.3)
SEMANA = {
    "grama": [1.00, 1.22, 1.25, 1.18, 0.98, 0.42],
    "plantas-diversas": [0.92, 1.08, 1.10, 1.08, 1.06, 0.80],
    "produtos-de-jardim": [0.98, 1.15, 1.15, 1.10, 1.00, 0.62],
    "flores-de-corte": [0.78, 0.90, 0.98, 1.08, 1.45, 0.85],
}
SAZONAL = {  # amplitude, dia do ano do pico
    "grama": (0.22, 300), "plantas-diversas": (0.12, 285), "produtos-de-jardim": (0.10, 290), "flores-de-corte": (0.05, 130),
}
TENDENCIA_ANO = 0.07
CV = {"grama": 0.12, "plantas-diversas": 0.11, "produtos-de-jardim": 0.11, "flores-de-corte": 0.14}
# grama: o ruído do dia comum a todos os produtos da loja (`CV["grama"]`) e o de cada produto,
# com mais / menos de 50 un./dia — sem o comum, a soma ficaria lisa e a naïve empataria
CV_PRODUTO = (0.10, 0.16)
SIGMA_NIVEL = 0.009  # variação diária do nível (AR(1) no log)
# alta de Flores de corte na semana da data (ADR-019) e queda das outras séries
ALTA_FLORES = {"Dia da Mulher": 2.6, "Dia das Mães": 3.0, "Dia dos Namorados": 2.4, "Natal": 2.2, "Ano Novo": 1.6}
QUEDA = {"Ano Novo": {"grama": 0.72, "plantas-diversas": 0.76, "produtos-de-jardim": 0.76},
         "Dia do Trabalho": {"grama": 0.55, "plantas-diversas": 0.72, "produtos-de-jardim": 0.70}}
# domingo de abertura excepcional (Itabirito no Dia das Mães e em Finados), sobre o sábado
ABERTURA = {"Dia das Mães": {"grama": 0.4, "plantas-diversas": 1.6, "produtos-de-jardim": 0.7, "flores-de-corte": 3.4},
            "Finados": {"grama": 0.4, "plantas-diversas": 2.2, "produtos-de-jardim": 0.6, "flores-de-corte": 1.5}}
TAMANHO_LINHA_GRAMA = ((100, 35), (20, 12), (0, 4))  # (venda média do produto acima de, un. por linha)
MAX_LINHA_GRAMA = 150
MAX_PEDIDO_BALCAO = 200  # nenhum pedido do dia a dia passa disto: só as encomendas ficam acima do limiar
ENCOMENDA_GRAMA = {"jardim-canada": 1500.0, "itabirito": 2000.0}  # mediana da grama de uma encomenda grande
PRECO = {  # mediana (R$) e dispersão do preço inventado de cada produto
    "grama": (9.0, 0.30), "plantas-diversas": (22.0, 0.80), "produtos-de-jardim": (28.0, 0.90),
    "flores-de-corte": (9.0, 0.50), CATEGORIA_SERVICO: (80.0, 0.60),
}
REAJUSTE_ANO = 0.05


def log(msg: str) -> None:
    print(f"[gerar_base_demonstracao] {msg}", flush=True)


def _url_sqlalchemy(url: str) -> str:
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


def _url_origem(arg: str | None) -> str:
    if arg:
        return _url_sqlalchemy(arg)
    from dotenv import dotenv_values

    url = dotenv_values(IA_PREDICTOR / ".env").get("DATABASE_URL") or ""
    if not url.startswith("postgres"):
        raise SystemExit("Informe o banco a espelhar com --origem (o DATABASE_URL do .env não é Postgres).")
    return _url_sqlalchemy(url)


# --------------------------------------------------------------------------- #
# 1. Perfil do Neon (só leitura)
# --------------------------------------------------------------------------- #
def _ler_perfil(origem) -> dict:
    def linhas(conn, sql: str) -> list[dict]:
        return [dict(r._mapping) for r in conn.execute(text(sql))]

    meta = MetaData()
    meta.reflect(origem)
    with origem.connect() as c:
        c.execute(text("SET TRANSACTION READ ONLY"))
        job = linhas(c, "SELECT * FROM forecast_jobs WHERE status = 'done' ORDER BY id DESC LIMIT 1")
        if not job:
            raise SystemExit("O banco de origem não tem treino concluído para espelhar.")
        job = job[0]
        perfil = {
            "meta": meta,
            "contagens": {t: c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in meta.tables},
            "ids": {t: c.execute(text(f'SELECT min(id) FROM "{t}"')).scalar()
                    for t, tab in meta.tables.items() if "id" in tab.c and t != "forecast_jobs"},
            "users": linhas(c, "SELECT id, email, name, role, is_active, created_at FROM users ORDER BY id"),
            "units": linhas(c, "SELECT * FROM units"),
            "categories": linhas(c, "SELECT * FROM categories ORDER BY sort_order"),
            "products": linhas(c, "SELECT code, name, category_id, subcategory, updated_at FROM products"),
            "calendar": linhas(c, "SELECT * FROM calendar_days ORDER BY unit_id, day"),
            "planilhas": linhas(c, "SELECT * FROM processing_log ORDER BY id"),
            "cotas": linhas(c, """
                SELECT import_id, unit_id, count(*) AS linhas, min(sale_date) AS inicio, max(sale_date) AS fim,
                       sum(CASE WHEN is_bulk_order THEN 1 ELSE 0 END) AS linhas_encomenda,
                       count(DISTINCT CASE WHEN is_bulk_order THEN sale_date || document_type || document_number END)
                           AS encomendas
                FROM sales GROUP BY import_id, unit_id ORDER BY import_id, unit_id"""),
            "skus": linhas(c, """
                SELECT DISTINCT s.unit_id, p.category_id, s.product_code
                FROM sales s JOIN products p ON p.code = s.product_code ORDER BY 1, 2, 3"""),
            "linhas_categoria": linhas(c, """
                SELECT s.unit_id, p.category_id, count(*) AS linhas
                FROM sales s JOIN products p ON p.code = s.product_code GROUP BY 1, 2"""),
            "tipos_doc": linhas(c, "SELECT unit_id, document_type, count(*) AS n FROM sales GROUP BY 1, 2"),
            "pagamentos": linhas(c, "SELECT payment_method, count(*) AS n FROM sales GROUP BY 1"),
            "proporcoes": linhas(c, """
                SELECT unit_id, avg(CASE WHEN is_registered_customer THEN 1.0 ELSE 0 END) AS cadastrado,
                       avg(CASE WHEN discount > 0 THEN 1.0 ELSE 0 END) AS desconto,
                       avg(CASE WHEN quantity < 0 THEN 1.0 ELSE 0 END) AS devolucao,
                       count(*) * 1.0 / count(DISTINCT (sale_date, document_type, document_number)) AS linhas_por_nota
                FROM sales GROUP BY 1"""),
            "job": job,
            "series": linhas(c, f"SELECT series_key, unit_id, level, category_id, product_code, status, message, "
                                f"mase, ci95_coverage_pct, metrics FROM series_models WHERE job_id = {job['id']} ORDER BY id"),
        }
    for k in ("cadastrado", "desconto", "devolucao", "linhas_por_nota"):
        for p in perfil["proporcoes"]:
            p[k] = float(p[k])
    return perfil


# --------------------------------------------------------------------------- #
# 2. Schema igual ao do Neon
# --------------------------------------------------------------------------- #
def _criar_schema(meta: MetaData, destino) -> None:
    """As tabelas do Neon, com os tipos genéricos (o SQLite não tem `double precision` nem
    sequência) e sem o `nextval` padrão dos ids."""
    for tabela in meta.tables.values():
        for coluna in tabela.columns:
            coluna.server_default = None
            coluna.type = coluna.type.as_generic()
    meta.create_all(destino)


# --------------------------------------------------------------------------- #
# 3. Vendas inventadas
# --------------------------------------------------------------------------- #
def _ar(n: int, rng, phi: float = 0.985, sigma: float = SIGMA_NIVEL) -> np.ndarray:
    """Nível que varia devagar (AR(1) no log), em torno de 1."""
    e = rng.normal(0.0, sigma, n)
    x = np.empty(n)
    x[0] = rng.normal(0.0, sigma / math.sqrt(1 - phi ** 2))
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return np.exp(x)


def _janelas_das_datas(dias: pd.DatetimeIndex, eventos) -> dict[str, np.ndarray]:
    """Dias da semana de cada data (de 6 dias antes até ela, como `datas_comemorativas`)."""
    from backend.domain.models.datas_comemorativas import DIAS_ANTES, data_do_evento

    janelas = {}
    for evento in eventos:
        m = np.zeros(len(dias), dtype=bool)
        for ano in range(dias.min().year, dias.max().year + 2):
            d = data_do_evento(evento, ano)
            m |= (dias >= d - pd.Timedelta(days=DIAS_ANTES)) & (dias <= d)
        janelas[evento] = m
    return janelas


def _venda_esperada(cat: str, nivel: float, dias: pd.DatetimeIndex, cal: pd.DataFrame, rng,
                    janelas: dict[str, np.ndarray]) -> np.ndarray:
    """Venda esperada de uma série em cada dia (0 com a loja fechada)."""
    amp, pico = SAZONAL[cat]
    anos = np.asarray((dias - pd.Timestamp("2024-01-01")).days) / 365.25
    base = nivel * (1 + amp * np.cos(2 * np.pi * (np.asarray(dias.dayofyear) - pico) / 365.25)) \
        * (1 + TENDENCIA_ANO * anos) * _ar(len(dias), rng)
    semana = np.array(SEMANA[cat] + [0.0])
    semana = semana / semana[:6].mean()
    mu = base * semana[np.asarray(dias.weekday)]
    if cat == "flores-de-corte":
        for evento, fator in ALTA_FLORES.items():
            mu = np.where(janelas[evento], mu * fator, mu)
    else:
        for evento, por_cat in QUEDA.items():
            mu = np.where(janelas[evento], mu * por_cat[cat], mu)
    excepcional = cal["abertura_excepcional"].values.astype(bool)
    for i in np.flatnonzero(excepcional):
        evento = next((v for v in (cal["data_comemorativa"].iloc[i], cal["nome_feriado"].iloc[i])
                       if isinstance(v, str)), None)
        mu[i] = base[i] * semana[5] * ABERTURA.get(evento, {}).get(cat, 1.0)
    mu[cal["loja_fechada"].values.astype(bool)] = 0.0
    return mu


def _sortear(mu: np.ndarray, cv: float, rng) -> np.ndarray:
    """Quantidade do dia: Poisson com média gama (média `mu`, coeficiente de variação `cv`)."""
    k = 1.0 / cv ** 2
    return rng.poisson(mu * rng.gamma(k, 1.0 / k, len(mu))).astype(int)


def _dividir(total: int, partes: int, rng, alpha: float = 3.0) -> np.ndarray:
    """`total` em `partes` inteiras, cada uma >= 1."""
    if partes <= 1:
        return np.array([total])
    return 1 + rng.multinomial(total - partes, rng.dirichlet(np.full(partes, alpha)))


def _ratear(total: int, pesos: np.ndarray) -> np.ndarray:
    """Inteiros proporcionais a `pesos` somando `total` (maiores restos)."""
    if total <= 0 or pesos.sum() <= 0:
        return np.zeros(len(pesos), dtype=int)
    bruto = total * pesos / pesos.sum()
    n = np.floor(bruto).astype(int)
    n[np.argsort(-(bruto - n))[: total - n.sum()]] += 1
    return n


def _venda_esparsa(motivo: str, dias: pd.DatetimeIndex, abertos: np.ndarray, data_ate: pd.Timestamp,
                   primeira_origem: pd.Timestamp, rng) -> np.ndarray:
    """Quantidade de cada dia de um produto de grama que fica sem previsão pelo mesmo motivo do Neon."""
    q = np.zeros(len(dias), dtype=int)
    if m := re.search(r"vendeu em (\d+) dia\(s\) nos últimos (\d+)", motivo or ""):
        k, janela = int(m.group(1)), int(m.group(2))
        recente = abertos & (dias > data_ate - pd.Timedelta(days=janela))
        antigo = abertos & (dias < data_ate - pd.Timedelta(days=janela + 30)) & (dias < primeira_origem - pd.Timedelta(days=200))
        for mascara, n in ((recente, k), (antigo, int(rng.integers(12, 40)))):
            idx = np.flatnonzero(mascara)
            q[rng.choice(idx, size=min(n, len(idx)), replace=False)] = rng.integers(1, 25, min(n, len(idx)))
    elif m := re.search(r"histórico de (\d+) dias antes", motivo or ""):
        # a 1ª venda fica `h` dias antes da 1ª origem do walk-forward; depois, em ~35% dos dias abertos
        inicio = primeira_origem - pd.Timedelta(days=int(m.group(1)))
        primeiro = np.flatnonzero(dias == inicio)
        if not len(primeiro) or not abertos[primeiro[0]]:
            raise ValueError(f"o 1º dia de venda ({inicio:%d/%m/%Y}) cai com a loja fechada")
        idx = np.flatnonzero(abertos & (dias >= inicio))
        idx = idx[(idx == primeiro[0]) | (rng.random(len(idx)) < 0.35)]
        q[idx] = rng.integers(1, 30, len(idx))
    return q


def _gerar_vendas(perfil: dict, rng) -> tuple[pd.DataFrame, dict, dict]:
    """Uma linha por produto de cada nota, com as mesmas linhas por planilha e loja do Neon.
    Devolve (vendas, limiares de encomenda por loja, resumo das encomendas por loja)."""
    cfg = perfil["job"]["config"]
    data_ate = pd.Timestamp(perfil["job"]["data_until"])
    primeira_origem = data_ate - pd.Timedelta(days=cfg["horizonte"] - 1) - pd.Timedelta(days=(cfg["origens"] - 1) * cfg["passo"])
    cal_todo = pd.DataFrame(perfil["calendar"])
    cal_todo["day"] = pd.to_datetime(cal_todo["day"])
    cat_produto = {p["code"]: p["category_id"] for p in perfil["products"]}
    skus = defaultdict(list)
    for s in perfil["skus"]:
        skus[(s["unit_id"], s["category_id"])].append(s["product_code"])
    linhas_cat = {(x["unit_id"], x["category_id"]): x["linhas"] for x in perfil["linhas_categoria"]}
    proporcao = {p["unit_id"]: p for p in perfil["proporcoes"]}
    tipos = defaultdict(dict)
    for t in perfil["tipos_doc"]:
        tipos[t["unit_id"]][t["document_type"]] = t["n"]
    pag = pd.DataFrame(perfil["pagamentos"])
    pag = pag[pag["payment_method"].str.strip() != ""]
    pagamentos, p_pag = pag["payment_method"].to_numpy(), (pag["n"] / pag["n"].sum()).to_numpy()
    series = {s["series_key"]: s for s in perfil["series"]}

    todas = []
    limiares, resumo = {}, {}
    for loja in [u["id"] for u in perfil["units"]]:
        cotas = [c for c in perfil["cotas"] if c["unit_id"] == loja]
        inicio, fim = min(c["inicio"] for c in cotas), max(c["fim"] for c in cotas)
        cal = cal_todo[(cal_todo["unit_id"] == loja) & (cal_todo["day"] >= pd.Timestamp(inicio))
                       & (cal_todo["day"] <= pd.Timestamp(fim))].set_index("day")
        dias = pd.date_range(inicio, fim, freq="D")
        cal = cal.reindex(dias)
        cal = cal.assign(
            loja_fechada=cal["store_closed"].astype(object).fillna(pd.Series(dias.weekday == 6, index=dias)).astype(bool),
            abertura_excepcional=cal["exceptional_opening"].astype(object).fillna(False).astype(bool),
            data_comemorativa=cal["special_date_name"], nome_feriado=cal["holiday_name"])
        planilha = np.zeros(len(dias), dtype=int)  # import_id de cada dia
        for c in cotas:
            planilha[(dias >= pd.Timestamp(c["inicio"])) & (dias <= pd.Timestamp(c["fim"]))] = c["import_id"]
        abertos = ~cal["loja_fechada"].values & (planilha > 0)
        janelas = _janelas_das_datas(dias, set(ALTA_FLORES) | set(QUEDA))

        # Grama: produto a produto (com previsão: venda todo dia; sem: esparsa, pelo motivo do Neon)
        k = 1.0 / CV["grama"] ** 2
        mu_grama = _venda_esperada("grama", NIVEL[loja]["grama"], dias, cal, rng, janelas) * rng.gamma(k, 1.0 / k, len(dias))
        q_produto = {}
        for cod in skus[(loja, "grama")]:
            s = series.get(f"{loja}:product:{cod}")
            if s is not None and s["status"] != "trained":
                q_produto[cod] = _venda_esparsa(s["message"], dias, abertos, data_ate, primeira_origem, rng)
                continue
            parte = PARTICIPACAO_GRAMA[loja].get(cod, PARTICIPACAO_PADRAO)
            mu = mu_grama * parte * _ar(len(dias), rng, sigma=0.008)
            q_produto[cod] = _sortear(mu, CV_PRODUTO[0] if mu.mean() > 50 else CV_PRODUTO[1], rng) * abertos

        linhas_dia = defaultdict(list)  # dia → [(produto, quantidade)]
        for cod, q in q_produto.items():
            media = q[abertos].mean()
            tam = next(t for lim, t in TAMANHO_LINHA_GRAMA if media > lim)
            for i in np.flatnonzero(q > 0):
                n = min(int(q[i]), max(1, round(q[i] / tam), math.ceil(q[i] / MAX_LINHA_GRAMA)))
                linhas_dia[i].extend((cod, int(x)) for x in _dividir(int(q[i]), n, rng, alpha=5.0))
        grama_por_planilha = defaultdict(int)
        for i, lista in linhas_dia.items():
            grama_por_planilha[planilha[i]] += len(lista)

        # Encomendas grandes: o mesmo número de pedidos e de linhas do Neon, em dias abertos da planilha
        grandes = [cod for cod in sorted(q_produto, key=lambda c: -q_produto[c].sum())[:3]]
        encomendas = defaultdict(list)  # dia → [[(produto, quantidade), ...], ...]
        for c in cotas:
            n_enc, n_lin = int(c["encomendas"]), int(c["linhas_encomenda"])
            if not n_enc:
                continue
            dias_enc = rng.choice(np.flatnonzero(abertos & (planilha == c["import_id"])), size=n_enc)
            for dia, n in zip(dias_enc, _ratear(n_lin, np.ones(n_enc))):
                grama = float(np.clip(rng.lognormal(math.log(ENCOMENDA_GRAMA[loja]), 0.45),
                                      0.6 * ENCOMENDA_GRAMA[loja], 4 * ENCOMENDA_GRAMA[loja]))
                pedido = [(str(rng.choice(grandes)), round(grama))]
                for _ in range(max(0, n - 1)):
                    cat = "plantas-diversas" if rng.random() < 0.6 else "produtos-de-jardim"
                    pedido.append((str(rng.choice(skus[(loja, cat)])), int(rng.integers(5, 150))))
                encomendas[dia].append(pedido)

        # Plantas, produtos e flores: as linhas que faltam para fechar cada planilha, por dia
        mu_cat = {cat: _venda_esperada(cat, NIVEL[loja][cat], dias, cal, rng, janelas) for cat in OUTRAS}
        q_cat = {cat: _sortear(mu_cat[cat], CV[cat], rng) for cat in OUTRAS}
        peso_cat = np.array([linhas_cat.get((loja, cat), 1) for cat in OUTRAS], dtype=float)
        total_loja = sum(v for (u, _), v in linhas_cat.items() if u == loja)
        parte_servico = linhas_cat.get((loja, CATEGORIA_SERVICO), 0) / total_loja
        n_cat = {cat: np.zeros(len(dias), dtype=int) for cat in OUTRAS}
        n_servico = np.zeros(len(dias), dtype=int)
        for c in cotas:
            idx = np.flatnonzero(abertos & (planilha == c["import_id"]))
            servico = round(parte_servico * c["linhas"])
            resto = c["linhas"] - grama_por_planilha[c["import_id"]] - int(c["linhas_encomenda"]) - servico
            n_servico[idx] = _ratear(servico, np.ones(len(idx)))
            for cat, n in zip(OUTRAS, _ratear(resto, peso_cat)):
                n_cat[cat][idx] = _ratear(int(n), mu_cat[cat][idx])
        pesos_sku = {}
        for cat in OUTRAS + (CATEGORIA_SERVICO,):
            lista = skus[(loja, cat)]
            w = 1.0 / np.arange(1, len(lista) + 1)
            pesos_sku[cat] = (np.array(lista), rng.permutation(w) / w.sum())
        for i in np.flatnonzero(abertos):
            for cat in OUTRAS:
                n = int(n_cat[cat][i])
                if n:
                    codigos, p = pesos_sku[cat]
                    produtos = rng.choice(codigos, size=n, p=p)
                    q = _dividir(max(int(q_cat[cat][i]), n), n, rng)
                    linhas_dia[i].extend(zip(produtos.tolist(), q.tolist()))
            if n_servico[i]:
                codigos, p = pesos_sku[CATEGORIA_SERVICO]
                linhas_dia[i].extend((str(c), 1) for c in rng.choice(codigos, size=int(n_servico[i]), p=p))

        # Notas: as linhas de cada dia agrupadas em pedidos (com teto), e as encomendas inteiras
        t_tipos = np.array(list(tipos[loja])); p_tipos = np.array(list(tipos[loja].values()), dtype=float)
        p_tipos /= p_tipos.sum()
        numero = {t: int(rng.integers(10_000, 90_000)) for t in t_tipos}
        prop = proporcao[loja]
        media_linhas = max(1.05, prop["linhas_por_nota"] - 0.15)
        p_desconto = min(0.9, prop["desconto"] * 1.05)
        registros = []
        for i in np.flatnonzero(abertos):
            lista = linhas_dia.get(i, [])
            ordem = rng.permutation(len(lista))
            pedidos, atual, tam = [], [], 0
            alvo = 1 + rng.poisson(media_linhas - 1)
            for j in ordem:
                cod, q = lista[j]
                conta = 0 if cat_produto[cod] == CATEGORIA_SERVICO else q  # serviço não entra no tamanho
                if atual and (len(atual) >= alvo or tam + conta > MAX_PEDIDO_BALCAO):
                    pedidos.append((atual, False))
                    atual, tam, alvo = [], 0, 1 + rng.poisson(media_linhas - 1)
                atual.append((cod, q))
                tam += conta
            if atual:
                pedidos.append((atual, False))
            pedidos += [(p, True) for p in encomendas.get(i, [])]
            for itens, grande in pedidos:
                tipo = str(rng.choice(t_tipos, p=p_tipos))
                numero[tipo] += int(rng.integers(1, 3))
                pagamento = (str(rng.choice(["BOLETO", "PIX", "TRANSF. BANCARIA", "A PRAZO"])) if grande
                             else str(rng.choice(pagamentos, p=p_pag)))
                cadastrado = bool(rng.random() < (0.9 if grande else prop["cadastrado"]))
                desconto = float(rng.uniform(0.03, 0.12)) if rng.random() < p_desconto else 0.0
                for cod, q in itens:
                    registros.append((dias[i].date(), loja, tipo, str(numero[tipo]), cod, float(q), pagamento,
                                      cadastrado, desconto, int(planilha[i])))
        df = pd.DataFrame(registros, columns=["sale_date", "unit_id", "document_type", "document_number", "product_code",
                                              "quantity", "payment_method", "is_registered_customer", "taxa_desconto",
                                              "import_id"])

        # Devoluções: a proporção do Neon, em plantas e produtos
        devolucao = np.flatnonzero(df["product_code"].map(cat_produto).isin(["plantas-diversas", "produtos-de-jardim"]))
        n_dev = round(prop["devolucao"] * len(df))
        if n_dev:
            df.loc[rng.choice(devolucao, size=n_dev, replace=False), "quantity"] *= -1

        # Encomenda grande: pedido acima de média + 4 desvios-padrão dos pedidos da loja (ADR-018)
        from training_scripts.preprocessing.remove_encomendas_06 import K_DESVIOS, limiar_por_desvios

        produto = df["product_code"].map(cat_produto) != CATEGORIA_SERVICO
        chave = ["sale_date", "document_type", "document_number"]
        tam = df[produto].groupby(chave)["quantity"].sum()
        limiar = limiar_por_desvios(tam, K_DESVIOS)
        grandes_ = tam[tam > limiar].index
        df["is_bulk_order"] = produto & df.set_index(chave).index.isin(grandes_)
        limiares[loja] = round(limiar, 1)
        resumo[loja] = {"limiar_un": round(limiar, 1), "pedidos": int(len(tam)), "encomendas": int(len(grandes_)),
                        "encomendas_previstas": int(sum(len(v) for v in encomendas.values()))}
        log(f"{loja}: {len(df):,} linhas, {len(tam):,} pedidos, limiar de encomenda {limiar:,.1f} un., "
            f"{len(grandes_)} encomendas grandes ({resumo[loja]['encomendas_previstas']} geradas)")
        todas.append(df)

    vendas = pd.concat(todas, ignore_index=True).sort_values(["sale_date", "unit_id"], kind="stable", ignore_index=True)
    return _precificar(vendas, perfil, cat_produto, rng), limiares, resumo


def _precificar(vendas: pd.DataFrame, perfil: dict, cat_produto: dict, rng) -> pd.DataFrame:
    """Preço inventado de cada produto (reajustado a cada ano), valor bruto, desconto e líquido."""
    precos = {}
    for p in perfil["products"]:
        mediana, disp = PRECO.get(p["category_id"], (20.0, 0.8))
        if p["category_id"] == "grama" and re.search(r"SEMENTE|SAQ|KG", p["name"] or ""):
            mediana = 45.0
        precos[p["code"]] = max(0.99, round(float(rng.lognormal(math.log(mediana), disp)), 1) - 0.01)
    anos = pd.to_datetime(vendas["sale_date"]).dt.year - 2024
    preco = vendas["product_code"].map(precos) * (1 + REAJUSTE_ANO) ** anos
    vendas["unit_price"] = preco.round(2)
    vendas["gross_amount"] = (vendas["quantity"] * vendas["unit_price"]).round(2)
    vendas["discount"] = (vendas["gross_amount"].abs() * vendas.pop("taxa_desconto")).round(2)
    vendas["net_amount"] = (vendas["gross_amount"] - np.sign(vendas["gross_amount"]) * vendas["discount"]).round(2)
    return vendas


# --------------------------------------------------------------------------- #
# 4. Gravação
# --------------------------------------------------------------------------- #
def _gravar_base(perfil: dict, vendas: pd.DataFrame, limiares: dict, resumo: dict, semente: int) -> None:
    from backend.auth.password_handler import hash_password
    from backend.config import settings
    from backend.infrastructure.database import engine

    meta = perfil["meta"]
    t = meta.tables
    senhas = {settings.ADMIN_EMAIL: settings.ADMIN_PASSWORD, settings.VIEWER_EMAIL: settings.VIEWER_PASSWORD}
    total = vendas.groupby("product_code")["quantity"].sum()
    with engine.begin() as conn:
        conn.execute(insert(t["users"]), [
            {**u, "hashed_password": hash_password(senhas.get(u["email"]) or f"demo-{semente}-{u['id']}")}
            for u in perfil["users"]])
        conn.execute(insert(t["units"]), perfil["units"])
        conn.execute(insert(t["categories"]), perfil["categories"])
        conn.execute(insert(t["products"]), [{**p, "total_sold": float(round(total.get(p["code"], 0.0), 3))}
                                             for p in perfil["products"]])
        conn.execute(insert(t["calendar_days"]), perfil["calendar"])
        conn.execute(insert(t["processing_log"]), _planilhas(perfil, vendas, limiares, resumo, semente))
        id0 = perfil["ids"].get("sales") or 1
        # objetos Python: o driver do SQLite não aceita int64/bool_ do numpy
        registros = vendas.assign(id=np.arange(id0, id0 + len(vendas))).astype(object).to_dict("records")
        for i in range(0, len(registros), LOTE):
            conn.execute(insert(t["sales"]), registros[i:i + LOTE])
    log(f"base gravada: {len(vendas):,} vendas, {len(perfil['products']):,} produtos, "
        f"{len(perfil['calendar']):,} dias de calendário, {len(perfil['planilhas'])} planilhas")


def _planilhas(perfil: dict, vendas: pd.DataFrame, limiares: dict, resumo: dict, semente: int) -> list[dict]:
    """As planilhas do Neon com as contagens das vendas inventadas; sem o treino (`forecast_job_id`),
    que o treino liga. Hash e tamanho do arquivo também inventados."""
    por_planilha = vendas.groupby("import_id").size()
    saida = []
    for p in perfil["planilhas"]:
        p = {**p, "forecast_job_id": None}
        if p["kind"] != "reclassification":
            n = int(por_planilha.get(p["id"], 0))
            p.update(rows_read=n, rows_added=n,
                     file_sha256=hashlib.sha256(f"demonstracao:{semente}:{p['filename']}".encode()).hexdigest(),
                     file_size_bytes=int(n * 480 + (p["id"] * 7919) % 40_000))
        elif "limiar_encomenda_un" in (p["quality"] or {}):
            q = dict(p["quality"])
            por_loja = {}
            for loja, r in resumo.items():
                antes = max(0, r["encomendas"] - (passam := round(0.15 * r["encomendas"])))
                por_loja[loja] = {"limiar_un": r["limiar_un"], "pedidos": r["pedidos"], "encomendas_antes": antes,
                                  "encomendas_depois": r["encomendas"], "passam_a_encomenda": passam, "deixam_de_ser": 0}
            remarcados = sum(r["passam_a_encomenda"] for r in por_loja.values())
            q.update(limiar_encomenda_un=limiares, pedidos_remarcados=remarcados, por_loja=por_loja)
            p["quality"] = q
            p["message"] = re.sub(r"\d+ pedidos mudaram", f"{remarcados} pedidos mudaram", p["message"] or "")
        saida.append(p)
    return saida


# --------------------------------------------------------------------------- #
# 5. Treino e espelho dos ids e horários
# --------------------------------------------------------------------------- #
# Treino rápido: uma ordem fixa por `d` (as que o treino completo mais escolhe nestas séries)
ORDEM_RAPIDA = {0: (1, 0, 2), 1: (0, 1, 2)}
ORDEM_SAZONAL_RAPIDA = (0, 1)  # (P, Q)


def treinar_serie_rapida(y: pd.Series, X: pd.DataFrame, aberta: pd.Series, config, nivel: str,
                         ao_progredir=None, com_fator: bool = False, com_queda: bool = False):
    """`trainer.treinar_serie` sem o grid de ordens e sem reajustar a cada origem: para cada `d`,
    a ordem de `ORDEM_RAPIDA` é ajustada uma vez na janela antes da 1ª origem e aplicada (filtro
    de Kalman, sem reestimar) à janela de cada origem; fica o `d` do walk-forward que errou menos,
    reajustado na última janela para a previsão. Mesmas métricas, faixa, datas comemorativas e
    diagnóstico dos resíduos. ~3 ajustes por série em vez de ~185."""
    import warnings

    from backend.domain.models import evaluator
    from backend.domain.models.forecaster import ajustar, prever
    from backend.domain.models.trainer import (ResultadoSerie, _ajustes_datas, _janela, motivo_inelegivel,
                                               origens_walk_forward)

    fim = y.index.max()
    janela_final = y.iloc[-config.janela_dias:]
    base = ResultadoSerie(status=evaluator.STATUS_DADOS_INSUFICIENTES, dias_historico=len(y),
                          dias_com_venda_janela=int((janela_final > 0).sum()),
                          treino_inicio=janela_final.index.min(), treino_fim=fim)
    if motivo := motivo_inelegivel(y, config, nivel):
        base.motivo = motivo
        return base
    origens = origens_walk_forward(fim, config)
    try:
        avaliados = {}
        for d in config.ds:
            ordem, sazonal = ORDEM_RAPIDA[d], (ORDEM_SAZONAL_RAPIDA[0], config.D, ORDEM_SAZONAL_RAPIDA[1], config.m)
            pre = _janela(y, origens[0], config.janela_dias)
            ajuste = ajustar(pre, X.loc[pre.index], ordem, sazonal, config.maxiter)
            linhas = []
            for origem in origens:
                treino = _janela(y, origem, config.janela_dias)
                futuro = pd.date_range(origem, periods=config.horizonte, freq="D")
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    res = ajuste.apply(treino, exog=X.loc[treino.index], refit=False)
                prev, inf, sup = prever(res, X.loc[futuro], config.alpha)
                fator, _ = _ajustes_datas(y, X, origem, futuro, config, com_fator, com_queda)
                ultima_semana = treino.values[-config.m:]
                escala = float(np.mean(np.abs(treino.values[config.m:] - treino.values[:-config.m])))
                for h, dia in enumerate(futuro):
                    linhas.append({"origem": origem, "data": dia, "horizonte": h + 1, "previsto": float(prev[h] * fator[h]),
                                   "ic_inf": float(inf[h] * fator[h]), "ic_sup": float(sup[h] * fator[h]),
                                   "real": float(y.loc[dia]), "naive": float(ultima_semana[h % config.m]),
                                   "escala": escala, "aberta": bool(aberta.loc[dia]), "fator": float(fator[h])})
            pontos = pd.DataFrame(linhas)
            avaliados[d] = (ordem, sazonal, float(ajuste.aic), pontos, evaluator.metricas_walk_forward(pontos))
        d = min(avaliados, key=lambda k: (avaliados[k][4]["mae"], config.ds.index(k)))
        ordem, sazonal, aic, pontos, metricas = avaliados[d]
        base.ordem, base.ordem_sazonal, base.aic, base.ordens_convergidas = ordem, sazonal, round(aic, 2), 1
        base.metricas = {**metricas, "origens_com_falha": 0}
        if len(config.ds) > 1:
            base.metricas["d_escolhido"] = d
            base.metricas["selecao_d"] = {
                str(k): {"ordem": [list(o), list(s)], "aic": round(a, 2),
                         **{c: m.get(c) for c in ("mae", "mase", "cobertura_ic95_pct")}}
                for k, (o, s, a, _, m) in avaliados.items()}
        base.backtest = pontos.drop(columns=["escala", "aberta"])

        futuro = pd.date_range(fim + pd.Timedelta(days=1), periods=config.dias_previsao, freq="D")
        res = ajustar(janela_final, X.loc[janela_final.index], ordem, sazonal, config.maxiter)
        prev, inf, sup = prever(res, X.loc[futuro], config.alpha)
        fator, lista = _ajustes_datas(y, X, futuro[0], futuro, config, com_fator, com_queda)
        base.previsao = pd.DataFrame({"data": futuro, "previsto": prev * fator, "ic_inf": inf * fator,
                                      "ic_sup": sup * fator, "fator": fator})
        base.ajustes = [a.como_dict() for a in lista]
        base.coeficientes = {nome: round(float(v), 6) for nome, v in res.params.items()}
        base.diagnostico = evaluator.diagnostico_residuos(res.resid, descartar=config.m)
        base.status, base.motivo = evaluator.STATUS_TREINADO, None
        return base
    except Exception as erro:  # noqa: BLE001 — como no trainer: a falha de uma série não derruba as outras
        base.status = evaluator.STATUS_ERRO
        base.motivo = f"{type(erro).__name__}: {erro}"[:500]
        return base


def tarefa_rapida(args: tuple):
    """`trainer.treinar_serie_tarefa` com `treinar_serie_rapida` (processo separado)."""
    chave, y, X, aberta, config, nivel, com_fator, com_queda = args
    return chave, treinar_serie_rapida(y, X, aberta, config, nivel, com_fator=com_fator, com_queda=com_queda)


def _treinar(perfil: dict, completo: bool):
    from backend.services import servico_previsao

    if not completo:  # o resto do treino (séries, log, gravação, histórico) é o do serviço
        servico_previsao.treinar_serie = treinar_serie_rapida
        servico_previsao.treinar_serie_tarefa = tarefa_rapida
    job = perfil["job"]
    log(f"treinando ({'completo, o mesmo do botão' if completo else 'rápido'}, {os.environ['TRAINING_WORKERS']} processos)...")
    t0 = time.monotonic()
    feito = servico_previsao.treinar_agora(user_id=job["user_id"], trigger=job["trigger"])
    if feito.status != "done":
        raise SystemExit(f"O treino não concluiu: {feito.status} — {feito.message}")
    log(f"treino concluído em {(time.monotonic() - t0) / 60:.1f} min: {feito.message}")
    return feito.id


def _espelhar_ids_e_horarios(perfil: dict, job_id: int) -> None:
    """Ids do treino e das tabelas dele iguais aos do Neon; horários do treino no intervalo do
    treino do Neon (escala linear do início ao fim)."""
    from backend.infrastructure.database import engine

    neon = perfil["job"]
    with engine.connect() as conn:
        # fora de transação (dentro dela o PRAGMA não vale): os ids mudam antes das referências a eles
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.commit()
        j = conn.execute(text("SELECT created_at, started_at, finished_at FROM forecast_jobs WHERE id = :i"),
                         {"i": job_id}).one()
        ini, fim = (datetime.fromisoformat(str(v)) for v in (j.started_at, j.finished_at))
        escala = (neon["finished_at"] - neon["started_at"]) / max(fim - ini, timedelta(seconds=1))

        def horario(v) -> datetime:
            return neon["started_at"] + (datetime.fromisoformat(str(v)) - ini) * escala

        for tabela, coluna in (("forecast_job_logs", "logged_at"), ("series_models", "trained_at")):
            for rid, v in conn.execute(text(f"SELECT id, {coluna} FROM {tabela} WHERE job_id = :i"), {"i": job_id}).all():
                conn.execute(text(f"UPDATE {tabela} SET {coluna} = :v WHERE id = :r"), {"v": horario(v), "r": rid})
        conn.execute(text("UPDATE forecast_jobs SET created_at = :c, started_at = :s, finished_at = :f, heartbeat_at = :h "
                          "WHERE id = :i"), {"c": neon["created_at"], "s": neon["started_at"], "f": neon["finished_at"],
                                             "h": neon["heartbeat_at"], "i": job_id})

        novo = neon["id"]
        deslocar = {t: perfil["ids"][t] for t in ("series_models", "forecast_job_logs", "series_forecasts",
                                                  "series_backtest_points", "forecast_history") if perfil["ids"].get(t)}
        for tabela, id_neon in deslocar.items():
            atual = conn.execute(text(f"SELECT min(id) FROM {tabela}")).scalar()
            d = id_neon - atual
            if d:
                # passa por ids negativos para não colidir no meio do UPDATE
                conn.execute(text(f"UPDATE {tabela} SET id = -(id + :d)"), {"d": d})
                conn.execute(text(f"UPDATE {tabela} SET id = -id"))
                if tabela == "series_models":
                    for filha in ("series_forecasts", "series_backtest_points"):
                        conn.execute(text(f"UPDATE {filha} SET model_id = model_id + :d"), {"d": d})
        for tabela, coluna in (("forecast_jobs", "id"), ("series_models", "job_id"), ("forecast_job_logs", "job_id"),
                               ("forecast_history", "job_id"), ("processing_log", "forecast_job_id")):
            conn.execute(text(f"UPDATE {tabela} SET {coluna} = :n WHERE {coluna} = :a"), {"n": novo, "a": job_id})
        problemas = conn.exec_driver_sql("PRAGMA foreign_key_check").all()
        if problemas:
            raise SystemExit(f"Chaves estrangeiras quebradas depois de espelhar os ids: {problemas[:5]}")
        conn.commit()
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    log(f"ids e horários do treino espelhados (treino {novo}, {neon['started_at']:%d/%m/%Y %H:%M} a "
        f"{neon['finished_at']:%H:%M})")


# --------------------------------------------------------------------------- #
# 6. Conferência
# --------------------------------------------------------------------------- #
def _conferir(perfil: dict, origem) -> None:
    from backend.infrastructure.database import SessionLocal, engine
    from backend.services import painel_service

    def colunas(eng) -> dict:
        ins = inspect(eng)
        return {t: [(c["name"], type(c["type"].as_generic()).__name__, c["nullable"]) for c in ins.get_columns(t)]
                for t in ins.get_table_names()}

    neon, demo = colunas(origem), colunas(engine)
    diferencas = [t for t in set(neon) | set(demo) if neon.get(t) != demo.get(t)]
    log("schema: " + ("igual ao do Neon" if not diferencas else f"DIFERENTE em {sorted(diferencas)}"))

    with engine.connect() as c:
        print(f"\n{'tabela':<26}{'Neon':>10}{'demonstração':>14}")
        for tabela in sorted(perfil["contagens"]):
            n = c.execute(text(f'SELECT count(*) FROM "{tabela}"')).scalar()
            marca = "" if n == perfil["contagens"][tabela] else "  ←"
            print(f"{tabela:<26}{perfil['contagens'][tabela]:>10,}{n:>14,}{marca}")
        demo_series = {r.series_key: r for r in c.execute(text(
            f"SELECT series_key, status, message, mase, ci95_coverage_pct, metrics FROM series_models "
            f"WHERE job_id = {perfil['job']['id']}"))}

    print(f"\n{'série':<42}{'status':>10}{'MASE Neon':>11}{'demo':>7}{'faixa95 Neon':>14}{'demo':>7}{'× naïve demo':>14}")
    iguais = 0
    for s in perfil["series"]:
        d = demo_series.get(s["series_key"])
        if d is None:
            print(f"{s['series_key']:<42} falta na demonstração")
            continue
        iguais += d.status == s["status"] and (d.message or "") == (s["message"] or "")
        if s["status"] == "trained":
            m = json.loads(d.metrics) if isinstance(d.metrics, str) else d.metrics
            print(f"{s['series_key']:<42}{d.status:>10}{s['mase'] or 0:>11.3f}{d.mase or 0:>7.3f}"
                  f"{s['ci95_coverage_pct'] or 0:>14.1f}{d.ci95_coverage_pct or 0:>7.1f}"
                  f"{(m or {}).get('erro_relativo_naive') or 0:>14.3f}")
    log(f"séries com o mesmo status e motivo do Neon: {iguais} de {len(perfil['series'])}")

    with SessionLocal() as db:
        painel_service.contexto(db)
        painel_service.painel(db)
    log("painel e contexto montados sem erro sobre a base de demonstração")


# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--destino", type=Path, default=IA_PREDICTOR / "floricultura.db", help="arquivo SQLite a gerar")
    parser.add_argument("--recriar", action="store_true", help="apaga o arquivo de destino se ele existir")
    parser.add_argument("--origem", help="banco a espelhar (padrão: DATABASE_URL do .env)")
    parser.add_argument("--semente", type=int, default=2026, help="semente das vendas inventadas")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 4, help="processos no treino")
    parser.add_argument("--sem-treino", action="store_true", help="só grava a base, sem treinar")
    parser.add_argument("--treino-completo", action="store_true",
                        help="o treino do botão (grid de ordens e reajuste a cada origem, ~1 h) em vez do rápido")
    args = parser.parse_args()

    destino = args.destino.resolve()
    if destino.exists():
        if not args.recriar:
            raise SystemExit(f"{destino} já existe; use --recriar para gerar de novo.")
        for arq in destino.parent.glob(destino.name + "*"):
            arq.unlink()
    origem = create_engine(_url_origem(args.origem), pool_pre_ping=True)
    log(f"lendo o perfil de {origem.url.render_as_string(hide_password=True)} (só leitura)...")
    perfil = _ler_perfil(origem)
    cfg = perfil["job"]["config"]

    # O backend lê o banco e a configuração do treino das variáveis de ambiente (prioridade
    # sobre o .env): definidas antes do primeiro import dele.
    os.environ.update({
        "DATABASE_URL": "sqlite:///" + destino.as_posix(),
        "TRAINING_RUNNER": "local", "TRAINING_WORKERS": str(max(1, args.workers)),
        "SEASONAL_PERIOD": str(cfg["m"]), "FORECAST_HORIZON_DAYS": str(cfg["horizonte"]),
        "FORECAST_MAX_HORIZON_DAYS": str(cfg.get("horizonte_previsao") or cfg["horizonte"]),
        "FORECAST_SERVICE_D_CANDIDATES": json.dumps(cfg.get("d_candidatos") or [cfg["d"]]),
        "FORECAST_SERVICE_WINDOW_DAYS": str(cfg["janela_dias"]), "FORECAST_SERVICE_WF_ORIGINS": str(cfg["origens"]),
        "MIN_OBSERVATIONS_DAYS": str(cfg["min_historico_dias"]),
        "FORECAST_SERVICE_MIN_SALE_DAYS": str(cfg["min_dias_com_venda"]),
        "FORECAST_SERVICE_MIN_SALE_WINDOW_DAYS": str(cfg.get("janela_venda_dias") or cfg["janela_dias"]),
        "FORECAST_SERVICE_EVENT_FACTOR": "true" if cfg.get("fator_datas") else "false",
    })
    if str(IA_PREDICTOR) not in sys.path:
        sys.path.insert(0, str(IA_PREDICTOR))
    from backend.infrastructure.database import engine

    _criar_schema(perfil["meta"], engine)
    log(f"schema do Neon criado em {destino}")
    rng = np.random.default_rng(args.semente)
    vendas, limiares, resumo = _gerar_vendas(perfil, rng)
    _gravar_base(perfil, vendas, limiares, resumo, args.semente)
    if args.sem_treino:
        return
    _espelhar_ids_e_horarios(perfil, _treinar(perfil, args.treino_completo))
    _conferir(perfil, origem)
    log(f"pronto: {destino} — para usar, DATABASE_URL=sqlite:///./{destino.name} no .env (a partir de ia-predictor/)")


if __name__ == "__main__":
    main()
