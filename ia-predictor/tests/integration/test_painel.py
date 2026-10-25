"""Telas do frontend montadas do banco: formatos de `app-react/src/domain/types.ts`
(`BaseReal`) e de `app-react/src/app/data/analises.ts`."""
from datetime import date, timedelta

from sqlalchemy import delete, select

from backend.infrastructure.database import ForecastHistory, SessionLocal
from backend.services import treino_service
from tests.conftest import CATEGORIAS, FIM

IDS_CAT = [c for c, _, _ in CATEGORIAS]
CHAVES_BASE_REAL = {"gerado_em", "fonte", "base", "configuracao", "categorias", "unidades", "importacao"}
CHAVES_UNIDADE = {"id", "nome", "cidade", "periodo", "linhas", "skus_vendidos", "volume_total",
                  "volume_flores_de_corte", "volume_por_categoria", "skus_por_categoria",
                  "regulares_por_categoria", "volume_regulares_8_semanas_pct",
                  "flores_regulares_fora_do_painel", "encomendas", "modelo", "previsao",
                  "historico_diario", "historico_semanal", "produtos", "backtest", "desagregacao"}


def test_painel_no_formato_base_real(client, viewer, com_previsao):
    r = client.get("/api/v1/painel", headers=viewer)
    assert r.status_code == 200
    p = r.json()
    assert set(p) == CHAVES_BASE_REAL
    assert [c["id"] for c in p["categorias"]] == IDS_CAT  # sem Serviço e taxa
    assert p["base"]["fim"] == str(FIM)
    assert p["configuracao"]["horizonte_dias"] == 14
    assert [u["id"] for u in p["unidades"]] == ["jardim-canada", "itabirito"]

    u = p["unidades"][0]
    assert set(u) == CHAVES_UNIDADE
    assert u["nome"] == "Jardim Canadá"
    assert len(u["previsao"]) == 14
    dia = u["previsao"][0]
    assert set(dia["categorias"]) == set(IDS_CAT)
    assert dia["previsto"] == 40.0
    carnaval = next(d for d in u["previsao"] if d["data"] == "2026-03-03")
    assert carnaval["evento"] == "Carnaval"
    domingo = next(d for d in u["previsao"] if d["data"] == "2026-03-01")
    assert domingo["loja_fechada"] is True
    assert u["modelo"]["status"] == "trained"
    assert u["modelo"]["metricas"]["mase"] == 0.6
    assert u["modelo"]["rodadas"]  # erro por rodada recalculado do backtest
    assert set(u["desagregacao"]) == set(IDS_CAT)

    regulares = [prod for prod in u["produtos"] if prod["regular"]]
    assert [prod["codigo"] for prod in regulares] == ["100"]
    assert len(regulares[0]["previsao"]) == 14
    assert "backtest" not in regulares[0]  # vem sob demanda (test_backtest_do_produto)
    assert regulares[0]["modelo"]["status"] == "low_confidence"
    assert u["encomendas"]["vendas"] > 0  # notas de 3.000 un. no dia 15
    assert len(u["historico_diario"]) == 56


def test_planilhas_carregadas_no_painel(client, viewer, com_previsao):
    p = client.get("/api/v1/painel", headers=viewer).json()
    assert set(p["importacao"]) == {"arquivos", "qualidade"}


def test_analises_por_loja(client, viewer):
    r = client.get("/api/v1/analises", headers=viewer)
    assert r.status_code == 200
    a = r.json()
    assert set(a["unidades"]) == {"jardim-canada", "itabirito"}
    u = a["unidades"]["itabirito"]
    assert set(u["categorias"]) == set(IDS_CAT)
    assert len(u["dia_semana"]) == 7
    assert u["resumo"]["encomendas"]["volume"] > 0


def test_backtest_do_produto(client, viewer, com_previsao):
    r = client.get("/api/v1/painel/produtos/jardim-canada/100/backtest", headers=viewer)
    assert r.status_code == 200
    assert len(r.json()) == 28 and {"data", "previsto", "real"} <= set(r.json()[0])
    assert client.get("/api/v1/painel/produtos/jardim-canada/999/backtest", headers=viewer).status_code == 404


def test_historico_da_categoria(client, viewer, com_previsao):
    r = client.get("/api/v1/painel/historico/jardim-canada/categoria/grama", headers=viewer)
    assert r.status_code == 200
    serie = r.json()
    assert serie[0]["data"] == "2025-12-01" and serie[-1]["data"] == str(FIM)  # base inteira
    com_previsto = [d for d in serie if d["previsto"] is not None]
    assert len(com_previsto) == 28  # walk-forward do treino sintético
    assert serie[0]["previsto"] is None and serie[0]["inf"] is None
    assert serie[-1]["previsto"] == 40.0


def test_historico_do_produto_sem_encomendas_grandes(client, viewer, com_previsao):
    serie = client.get("/api/v1/painel/historico/jardim-canada/produto/100", headers=viewer).json()
    dia15 = next(d for d in serie if d["data"] == "2026-01-15")
    assert dia15["real"] == 0.0  # a nota de 3.000 un. é encomenda grande
    assert client.get("/api/v1/painel/historico/jardim-canada/produto/999", headers=viewer).status_code == 404
    assert client.get("/api/v1/painel/historico/jardim-canada/loja/x", headers=viewer).status_code == 422


def test_historico_congela_os_dias_que_passaram(com_previsao):
    """Duas gerações seguidas: a 2ª troca só os dias a partir do início dela."""
    def ponto(dia, valor, source="forecast"):
        return {"level": "product", "item": "300", "day": dia, "predicted": valor, "lower_95": 0.0,
                "upper_95": valor, "source": source, "origin_date": dia}

    sem1 = date(2026, 4, 1)
    sem2 = sem1 + timedelta(days=7)
    with SessionLocal() as db:
        treino_service.gravar_historico(db, "itabirito", sem1, [],
                                        [ponto(sem1 + timedelta(days=i), 10.0) for i in range(14)], None, None)
        treino_service.gravar_historico(db, "itabirito", sem2, [ponto(sem1, 99.0, "walk_forward")],
                                        [ponto(sem2 + timedelta(days=i), 20.0) for i in range(14)], None, None)
        db.commit()
        valores = dict(db.execute(select(ForecastHistory.day, ForecastHistory.predicted).where(
            ForecastHistory.unit_id == "itabirito", ForecastHistory.item == "300")).all())
        db.execute(delete(ForecastHistory).where(ForecastHistory.item == "300"))
        db.commit()
    assert len(valores) == 21
    assert valores[sem1] == 10.0  # congelado: o walk-forward não troca
    assert valores[sem2 - timedelta(days=1)] == 10.0
    assert valores[sem2] == 20.0 and valores[sem2 + timedelta(days=13)] == 20.0


def test_contexto_leve(client, viewer, com_previsao):
    c = client.get("/api/v1/contexto", headers=viewer).json()
    assert [u["id"] for u in c["lojas"]] == ["jardim-canada", "itabirito"]
    assert [x["id"] for x in c["categorias"]] == IDS_CAT
    assert c["base"]["fim"] == str(FIM) and c["base"]["skus"] == 4  # sem o frete
    assert c["configuracao"]["horizonte_dias"] == 14
    assert {x["status"] for x in c["previsao"]["lojas"]} == {"trained"}
    assert c["previsao"]["produtos"][0]["nome"] == "GRAMA ESMERALDA M2"
    assert set(c["importacao"]) == {"arquivos", "qualidade"}


def test_registros_indice(client, viewer):
    indice = client.get("/api/v1/registros", headers=viewer).json()
    assert [m["mes"] for m in indice["meses"]] == ["2025-12", "2026-01", "2026-02"]
    assert indice["lojas"] == ["jardim-canada", "itabirito"]
    assert indice["pagamentos"] == ["Pix"]
    assert indice["total_registros"] == sum(m["registros"] for m in indice["meses"])


def test_registros_paginados(client, viewer):
    total = client.get("/api/v1/registros", headers=viewer).json()["total_registros"]
    p1 = client.get("/api/v1/registros/linhas", headers=viewer, params={"tamanho": 25}).json()
    p2 = client.get("/api/v1/registros/linhas", headers=viewer, params={"tamanho": 25, "pagina": 2}).json()
    assert len(p1["linhas"]) == 25 and len(p2["linhas"]) == 25
    assert not {r["id"] for r in p1["linhas"]} & {r["id"] for r in p2["linhas"]}
    assert p1["linhas"][0]["data"] == str(FIM)  # padrão: mais recentes primeiro
    assert all(r["cat"] != "servico-e-taxa" for r in p1["linhas"])
    linha = p1["linhas"][0]
    assert not {"cliente", "cliente_nome", "vendedor", "operador"} & set(linha)
    assert client.get("/api/v1/registros/linhas", headers=viewer, params={"tamanho": 500}).status_code == 422
    assert total > 50


def test_registros_filtros_e_resumo(client, viewer):
    filtro = {"meses": ["2026-01"], "lojas": ["itabirito"], "categorias": ["grama"]}
    r = client.get("/api/v1/registros/resumo", headers=viewer, params=filtro).json()
    pag = client.get("/api/v1/registros/linhas", headers=viewer, params={**filtro, "tamanho": 200}).json()
    assert r["registros"] == len(pag["linhas"]) > 0
    assert all(x["loja"] == "itabirito" and x["cat"] == "grama" and x["data"].startswith("2026-01")
               for x in pag["linhas"])
    assert r["quantidade"] == round(sum(x["qtd"] for x in pag["linhas"]), 3)
    assert r["por_visao"]["encomendas"] == 1  # 3.000 un. no dia 15

    enc = client.get("/api/v1/registros/resumo", headers=viewer, params={**filtro, "visao": "encomendas"}).json()
    assert enc["registros"] == 1 and enc["por_visao"] == r["por_visao"]

    busca = client.get("/api/v1/registros/linhas", headers=viewer, params={"busca": "esmeralda"}).json()
    assert {x["cod"] for x in busca["linhas"]} == {"100"}
    assert client.get("/api/v1/registros/linhas", headers=viewer, params={"meses": ["janeiro"]}).status_code == 422


def test_registros_ordem_nota_e_exportacao(client, viewer):
    asc = client.get("/api/v1/registros/linhas", headers=viewer, params={"ordem": "qtd", "direcao": "asc"}).json()
    qtds = [x["qtd"] for x in asc["linhas"]]
    assert qtds == sorted(qtds)
    x = asc["linhas"][0]
    itens = client.get("/api/v1/registros/nota", headers=viewer,
                       params={"loja": x["loja"], "data": x["data"], "nota": x["nota"]}).json()
    assert [i["id"] for i in itens] == [x["id"]]
    filtro = {"meses": ["2026-02"], "lojas": ["jardim-canada"]}
    exp = client.get("/api/v1/registros/exportar", headers=viewer, params=filtro).json()
    resumo = client.get("/api/v1/registros/resumo", headers=viewer, params=filtro).json()
    assert len(exp["linhas"]) == resumo["registros"] and exp["colunas"][0] == "data"
