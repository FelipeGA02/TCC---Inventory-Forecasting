"""Telas do frontend montadas do banco: formatos de `app-react/src/domain/types.ts`
(`BaseReal`) e de `app-react/src/app/data/analises.ts`. A previsão é a do último treino
concluído (`com_previsao`: as 4 categorias e o produto de grama 100, nas 2 lojas)."""
from datetime import timedelta

from tests.conftest import CATEGORIAS, CONFIG_TESTE, FIM

IDS_CAT = [c for c, _, _ in CATEGORIAS]
CHAVES_BASE_REAL = {"gerado_em", "fonte", "base", "configuracao", "categorias", "unidades", "importacao"}
CHAVES_UNIDADE = {"id", "nome", "cidade", "periodo", "linhas", "skus_vendidos", "volume_total",
                  "volume_flores_de_corte", "volume_por_categoria", "skus_por_categoria", "encomendas",
                  "categorias_modelo", "previsao", "historico_diario", "historico_semanal", "produtos",
                  "backtest_categorias"}
CHAVES_METRICAS = {"rodadas", "rodadas_vence_naive", "dias_avaliados", "mae", "mase", "erro_relativo_naive",
                   "cobertura_ic95_pct", "largura_ic95", "venda_media_dia", "previsto_sobre_real_pct",
                   "erro_total_14d_pct", "ljung_box_p", "shapiro_p"}


def test_painel_no_formato_base_real(client, viewer, com_previsao):
    r = client.get("/api/v1/painel", headers=viewer)
    assert r.status_code == 200
    p = r.json()
    assert set(p) == CHAVES_BASE_REAL
    assert [c["id"] for c in p["categorias"]] == IDS_CAT  # sem Serviço e taxa
    assert p["base"]["fim"] == str(FIM)
    cfg = p["configuracao"]
    assert cfg["horizonte_dias"] == 14 and (cfg["m"], cfg["d"], cfg["D"]) == (7, 0, 0)
    assert cfg["origens"] == CONFIG_TESTE.origens and cfg["dados_ate"] == str(FIM)
    assert [u["id"] for u in p["unidades"]] == ["jardim-canada", "itabirito"]

    u = p["unidades"][0]
    assert set(u) == CHAVES_UNIDADE
    assert u["nome"] == "Jardim Canadá"
    # 14 dias a partir do dia seguinte à última venda; o total é a soma das 4 categorias
    assert [d["data"] for d in u["previsao"]] == [str(FIM + timedelta(days=i)) for i in range(1, 15)]
    for dia in u["previsao"]:
        assert set(dia["categorias"]) == set(IDS_CAT)
        assert abs(dia["previsto"] - sum(c["previsto"] for c in dia["categorias"].values())) < 0.01
        assert abs(dia["sup"] - sum(c["sup"] for c in dia["categorias"].values())) < 0.01
    carnaval = next(d for d in u["previsao"] if d["data"] == "2026-03-03")
    assert carnaval["evento"] == "Carnaval"
    domingo = next(d for d in u["previsao"] if d["data"] == "2026-03-01")
    assert domingo["loja_fechada"] is True and domingo["previsto"] < 5

    # um modelo por categoria, com as métricas da tela e o diagnóstico dos resíduos
    assert set(u["categorias_modelo"]) == set(IDS_CAT)
    for m in u["categorias_modelo"].values():
        assert m["status"] in ("trained", "low_confidence")
        assert m["ordem"][1] == 0 and m["ordem_sazonal"][3] == 7
        assert set(m["metricas"]) == CHAVES_METRICAS and m["metricas"]["rodadas"] == CONFIG_TESTE.origens
    # o 1º dia de cada janela completa do walk-forward, por categoria
    assert all(len(pts) == CONFIG_TESTE.origens for pts in u["backtest_categorias"].values())

    # só os produtos de grama, cada um com o seu modelo
    assert [prod["codigo"] for prod in u["produtos"]] == ["100"]
    prod = u["produtos"][0]
    assert "regular" not in prod and "backtest" not in prod
    assert len(prod["previsao"]) == 14 and prod["previsao_14d"] is not None
    assert prod["modelo"]["status"] in ("trained", "low_confidence")
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


def test_contexto_leve(client, viewer, com_previsao):
    c = client.get("/api/v1/contexto", headers=viewer).json()
    assert [u["id"] for u in c["lojas"]] == ["jardim-canada", "itabirito"]
    assert [x["id"] for x in c["categorias"]] == IDS_CAT
    assert c["base"]["fim"] == str(FIM) and c["base"]["skus"] == 4  # sem o frete
    assert c["configuracao"]["horizonte_dias"] == 14
    assert c["previsao"]["dados_ate"] == str(FIM)
    assert {(x["loja"], x["categoria"]) for x in c["previsao"]["categorias"]} == {
        (loja, cat) for loja in ("jardim-canada", "itabirito") for cat in IDS_CAT}
    assert {x["status"] for x in c["previsao"]["categorias"]} <= {"trained", "low_confidence"}
    assert c["previsao"]["produtos"][0]["nome"] == "GRAMA ESMERALDA M2"
    assert set(c["importacao"]) == {"arquivos", "qualidade"}


def test_rota_do_teste_por_produto_saiu(client, viewer, com_previsao):
    assert client.get("/api/v1/painel/produtos/jardim-canada/100/backtest", headers=viewer).status_code == 404


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
