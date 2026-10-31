"""Serviço de previsão (`/api/v1/servico-previsao/*`): só admin, treino em segundo plano com
andamento e log no banco, treino só quando os dados mudaram, e o histórico da previsão
(`forecast_history`, `/api/v1/painel/historico/*`) que cada treino concluído atualiza.

Os treinos de ponta a ponta usam a configuração reduzida do `conftest` (`CONFIG_TESTE`).
O status antes do primeiro treino está em `test_01_sem_previsao`.
"""
import time
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select

from backend.config import settings
from backend.domain.models.trainer import ConfigTreino
from backend.infrastructure.database import (
    ForecastHistory,
    ForecastJob,
    ForecastJobLog,
    ProcessingLog,
    Sale,
    SeriesBacktestPoint,
    SeriesForecast,
    SeriesModel,
    SessionLocal,
)
from backend.services import servico_previsao
from tests.conftest import CONFIG_TESTE, FIM

BASE = "/api/v1/servico-previsao"


def _historico_gravado(db, *filtros) -> dict:
    return {(h.unit_id, h.level, h.item, h.day): (h.predicted, h.source, h.origin_date, h.job_id)
            for h in db.scalars(select(ForecastHistory).where(*filtros))}


def _esperar_fim(client, admin, limite_s: float = 180) -> dict:
    fim = time.time() + limite_s
    while time.time() < fim:
        s = client.get(f"{BASE}/status", headers=admin).json()
        if s["em_andamento"] is None:
            return s
        time.sleep(0.3)
    raise AssertionError("o treino não terminou a tempo")


@pytest.fixture
def config_rapida(monkeypatch):
    monkeypatch.setattr(servico_previsao, "config_treino", lambda: CONFIG_TESTE)
    monkeypatch.setattr(settings, "TRAINING_WORKERS", 1)


@pytest.mark.parametrize("metodo,rota", [("get", "/status"), ("post", "/treinos"), ("get", "/treinos/1"),
                                         ("get", "/treinos/1/logs"), ("get", "/treinos/1/series")])
def test_so_admin_usa_o_servico(client, viewer, metodo, rota):
    assert getattr(client, metodo)(f"{BASE}{rota}").status_code == 401
    r = getattr(client, metodo)(f"{BASE}{rota}", headers=viewer)
    assert r.status_code == 403
    assert r.json()["detail"] == "Você não tem permissão para esta ação."


def _forcar_novo_treino(monkeypatch):
    """Ignora o último treino concluído, para disparar de novo sem mudar a base."""
    monkeypatch.setattr(servico_previsao, "ultimo_concluido", lambda db: None)


def test_treino_completo_em_segundo_plano(client, admin, config_rapida, monkeypatch):
    ultimo_concluido = servico_previsao.ultimo_concluido
    _forcar_novo_treino(monkeypatch)  # `com_previsao` pode já ter treinado com a mesma base
    with SessionLocal() as db:
        db.add(ProcessingLog(filename="semana.xlsx", file_sha256="0" * 64, file_size_bytes=1, status="done",
                             reference_month="2026-02"))
        db.commit()
    r = client.post(f"{BASE}/treinos", headers=admin)
    assert r.status_code == 202, r.text
    assert r.json()["iniciado"] is True and "segundo plano" in r.json()["mensagem"]
    treino_id = r.json()["treino"]["id"]

    s = _esperar_fim(client, admin)
    t = s["ultimo"]
    assert t["id"] == treino_id and t["status"] == "done", t["mensagem"]
    # 2 lojas × (4 categorias + 1 produto de grama)
    assert t["total_series"] == t["series_concluidas"] == 10
    assert t["progresso_pct"] == 100.0
    assert t["series_treinadas"] + t["series_baixa_confianca"] == 10
    assert t["dados_ate"] == "2026-02-28"
    monkeypatch.setattr(servico_previsao, "ultimo_concluido", ultimo_concluido)  # volta a ver os treinos
    s = client.get(f"{BASE}/status", headers=admin).json()
    assert s["dados_alterados"] is False and s["ultimo_concluido_em"] is not None

    series = client.get(f"{BASE}/treinos/{treino_id}/series", headers=admin).json()
    assert {(x["loja"], x["nivel"]) for x in series} == {(l, n) for l in ("itabirito", "jardim-canada")
                                                          for n in ("category", "product")}
    for x in series:
        assert x["ordem"][1] == 0  # d = 0
        assert x["ordem_sazonal"][1] == 0  # D = 0
        assert x["ordem_sazonal"][3] == 7  # m = 7
        assert len(x["previsao"]) == 14
        assert x["previsao"][0]["data"] == "2026-03-01" and x["previsao"][-1]["data"] == "2026-03-14"
        assert x["metricas"]["origens"] == 3
    produtos = [x for x in series if x["nivel"] == "product"]
    assert {x["produto_codigo"] for x in produtos} == {"100"} and produtos[0]["nome"] == "GRAMA ESMERALDA M2"

    with SessionLocal() as db:
        modelos = [m.id for m in db.scalars(select(SeriesModel).where(SeriesModel.job_id == treino_id))]
        assert db.scalar(select(func.count()).select_from(SeriesForecast)
                         .where(SeriesForecast.model_id.in_(modelos))) == 10 * 14
        assert db.scalar(select(func.count()).select_from(SeriesBacktestPoint)
                         .where(SeriesBacktestPoint.model_id.in_(modelos))) == 10 * 3 * 14
        job = db.get(ForecastJob, treino_id)
        assert job.config["d"] == 0 and job.config["D"] == 0 and job.config["m"] == 7
        assert job.config["passo"] == 1 and job.data_fingerprint == servico_previsao.impressao_digital(db)
        assert "versao_codigo" in job.config
        # coeficientes e diagnóstico dos resíduos do ajuste final de cada série
        for m in db.scalars(select(SeriesModel).where(SeriesModel.job_id == treino_id)):
            assert "intercept" in m.params["coeficientes"] and "loja_fechada" in m.params["coeficientes"]
            assert {"ljung_box_p", "shapiro_p", "erro_total_14d_pct", "origens_vence_naive"} <= set(m.metrics)
            # o que saiu da série como encomenda grande, com o limiar da loja (ADR-018)
            assert {"limiar_un", "pedidos", "pct_venda"} <= set(m.params["encomendas_grandes"])
        # a planilha que ainda não tinha entrado em treino fica ligada a este
        planilha = db.scalar(select(ProcessingLog).where(ProcessingLog.filename == "semana.xlsx"))
        assert planilha.forecast_job_id == treino_id

    logs = client.get(f"{BASE}/treinos/{treino_id}/logs", headers=admin).json()
    assert logs[0]["mensagem"].startswith("Treino iniciado com vendas até 28/02/2026")
    assert "Limiar de encomenda grande de cada loja (média + 4 desvios-padrão dos pedidos dela)" in logs[0]["mensagem"]
    # cada série treinada diz o limiar da sua loja e o que saiu dela (ADR-018)
    treinadas = [l for l in logs if l["serie"] and "SARIMAX" in l["mensagem"]]
    assert treinadas and all("Encomendas grandes (pedido acima de " in l["mensagem"] for l in treinadas)
    # base de teste sem limiar gravado: vale o fixo de 2.000; nos últimos 30 dias não há venda acima dele
    grama = next(l["mensagem"] for l in treinadas if l["serie"] == "jardim-canada:category:grama")
    assert ("Encomendas grandes (pedido acima de 2.000 un., média + 4 desvios-padrão dos pedidos de Jardim Canadá): "
            "nenhuma nos últimos 30 dias.") in grama
    assert any(l["mensagem"] == "1 planilha(s) nova(s) neste treino: semana.xlsx." for l in logs)
    assert logs[-1]["mensagem"].startswith("Treino concluído")
    assert sum(1 for l in logs if l["serie"]) == 10  # uma linha por série
    depois = client.get(f"{BASE}/treinos/{treino_id}/logs", headers=admin, params={"apos_id": logs[-2]["id"]}).json()
    assert [l["id"] for l in depois] == [logs[-1]["id"]]


def test_historico_do_primeiro_treino_vem_do_walk_forward(client, viewer):
    """Antes do 1º treino não há previsão congelada: o 1º dia de cada janela do walk-forward
    (3 origens completas e as 13 do complemento) cobre os 16 dias até a última venda, cada
    um previsto com as vendas até a véspera."""
    r = client.get("/api/v1/painel/historico/jardim-canada/categoria/grama", headers=viewer)
    assert r.status_code == 200, r.text
    serie = r.json()
    assert serie[0]["data"] == "2025-12-01" and serie[-1]["data"] == str(FIM)  # base inteira
    com_previsto = [d for d in serie if d["previsto"] is not None]
    assert [d["data"] for d in com_previsto] == [str(FIM - timedelta(days=i)) for i in range(15, -1, -1)]
    assert {(d["fonte"], d["horizonte"]) for d in com_previsto} == {("walk_forward", 1)}
    assert {d["loja_fechada"] for d in com_previsto if d["data"] == "2026-02-22"} == {True}  # domingo
    assert serie[0]["previsto"] is None and serie[0]["fonte"] is None and serie[0]["horizonte"] is None

    with SessionLocal() as db:
        job = servico_previsao.ultimo_concluido(db)
        futuro = _historico_gravado(db, ForecastHistory.day > FIM)
        # o calendário que a previsão usou: 01/03/2026 é domingo, loja fechada
        domingo = {h.store_closed for h in db.scalars(select(ForecastHistory).where(
            ForecastHistory.day == FIM + timedelta(days=1)))}
        segunda = {h.store_closed for h in db.scalars(select(ForecastHistory).where(
            ForecastHistory.day == FIM + timedelta(days=2)))}
    assert domingo == {True} and segunda == {False}
    # a previsão dos 14 dias de cada uma das 10 séries, esperando os dias passarem
    assert len(futuro) == 10 * 14
    assert {(fonte, origem, jid) for _, fonte, origem, jid in futuro.values()} == {
        ("forecast", FIM + timedelta(days=1), job.id)}


def test_historico_do_produto_sem_encomendas_grandes(client, viewer):
    serie = client.get("/api/v1/painel/historico/jardim-canada/produto/100", headers=viewer).json()
    dia15 = next(d for d in serie if d["data"] == "2026-01-15")
    assert dia15["real"] == 0.0  # a nota de 3.000 un. é encomenda grande
    assert serie[-1]["previsto"] is not None
    assert client.get("/api/v1/painel/historico/jardim-canada/produto/999", headers=viewer).status_code == 404
    assert client.get("/api/v1/painel/historico/jardim-canada/loja/x", headers=viewer).status_code == 422


def test_sem_dados_novos_nao_treina(client, admin, config_rapida):
    with SessionLocal() as db:
        antes = _historico_gravado(db)
    r = client.post(f"{BASE}/treinos", headers=admin)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["iniciado"] is False and corpo["treino"]["status"] == "skipped"
    assert "não mudaram" in corpo["mensagem"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SeriesModel)
                         .where(SeriesModel.job_id == corpo["treino"]["id"])) == 0
        assert db.scalar(select(func.count()).select_from(ForecastJobLog)
                         .where(ForecastJobLog.job_id == corpo["treino"]["id"])) == 1
        assert _historico_gravado(db) == antes  # `skipped` não mexe no histórico


def test_treino_em_processos_paralelos(client, admin, config_rapida, monkeypatch):
    _forcar_novo_treino(monkeypatch)
    monkeypatch.setattr(settings, "TRAINING_WORKERS", 2)
    with SessionLocal() as db:
        passado = _historico_gravado(db, ForecastHistory.day <= FIM)
    r = client.post(f"{BASE}/treinos", headers=admin)
    assert r.status_code == 202, r.text
    t = _esperar_fim(client, admin, limite_s=300)["ultimo"]
    assert t["status"] == "done", t["mensagem"]
    with SessionLocal() as db:
        # dias com venda ficam como estavam; a previsão nova (mesmo início) troca os 14 dias
        assert _historico_gravado(db, ForecastHistory.day <= FIM) == passado
        futuro = _historico_gravado(db, ForecastHistory.day > FIM)
    assert len(futuro) == 10 * 14 and {jid for *_, jid in futuro.values()} == {t["id"]}
    assert t["series_concluidas"] == 10 and t["series_com_erro"] == 0
    logs = client.get(f"{BASE}/treinos/{t['id']}/logs", headers=admin).json()
    assert not any("seguem uma a uma" in l["mensagem"] for l in logs)  # rodou mesmo em paralelo


def test_produto_sem_vendas_suficientes_fica_registrado_sem_previsao(client, admin, monkeypatch):
    _forcar_novo_treino(monkeypatch)
    monkeypatch.setattr(settings, "TRAINING_WORKERS", 1)
    exigente = ConfigTreino(janela_dias=30, origens=3, grade_pq=(0, 1), grade_PQ=(0,), min_historico_dias=20,
                            min_dias_com_venda=29)  # o produto 100 vende 25 dias por janela de 30
    monkeypatch.setattr(servico_previsao, "config_treino", lambda: exigente)
    assert client.post(f"{BASE}/treinos", headers=admin).status_code == 202
    t = _esperar_fim(client, admin)["ultimo"]
    assert t["status"] == "done", t["mensagem"]
    # o andamento conta só o que treina: as 8 categorias; os 2 produtos vão para "insuficientes"
    assert t["total_series"] == t["series_concluidas"] == 8 and t["progresso_pct"] == 100.0
    assert t["series_dados_insuficientes"] == 2 and "2 sem vendas suficientes" in t["mensagem"]
    produtos = [x for x in client.get(f"{BASE}/treinos/{t['id']}/series", headers=admin).json()
                if x["nivel"] == "product"]
    assert len(produtos) == 2
    for x in produtos:
        assert x["status"] == "insufficient_data" and x["previsao"] == [] and x["ordem"] is None
        assert "o mínimo é 29" in x["mensagem"]


class _PoolQuebrado:
    """Imita o pool que cai no meio do treino (o modo de falha do proot/Termux)."""

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def submit(self, *a, **k):
        from concurrent.futures import Future
        from concurrent.futures.process import BrokenProcessPool

        f = Future()
        f.set_exception(BrokenProcessPool("processo filho morreu"))
        return f


def test_pool_quebrado_segue_uma_serie_por_vez(client, admin, config_rapida, monkeypatch):
    _forcar_novo_treino(monkeypatch)
    monkeypatch.setattr(settings, "TRAINING_WORKERS", 4)
    monkeypatch.setattr(servico_previsao, "ProcessPoolExecutor", _PoolQuebrado)
    r = client.post(f"{BASE}/treinos", headers=admin)
    assert r.status_code == 202, r.text
    t = _esperar_fim(client, admin)["ultimo"]
    assert t["status"] == "done", t["mensagem"]
    assert t["series_concluidas"] == 10 and t["series_com_erro"] == 0
    logs = client.get(f"{BASE}/treinos/{t['id']}/logs", headers=admin).json()
    assert any(l["nivel"] == "warning" and "seguem uma a uma" in l["mensagem"] for l in logs)


def test_series_do_treino_nao_tem_encomendas(client):
    """O `conftest` marca como encomenda (`is_bulk_order`) a venda de 3.000 un. do produto 100
    no dia 15; ela não pode entrar nem na série da categoria Grama nem na do produto."""
    with SessionLocal() as db:
        job = ForecastJob(status="running", heartbeat_at=datetime.now())
        db.add(job)
        db.commit()
        try:
            series, _ = servico_previsao._montar_series(db, CONFIG_TESTE, job.id)
            dia = date(2026, 1, 15)  # quinta-feira, com a encomenda
            encomenda = db.scalar(select(func.sum(Sale.quantity)).where(
                Sale.unit_id == "itabirito", Sale.sale_date == dia, Sale.is_bulk_order.is_(True)))
            balcao = db.scalar(select(func.sum(Sale.quantity)).where(
                Sale.unit_id == "itabirito", Sale.sale_date == dia, Sale.product_code == "100",
                Sale.is_bulk_order.is_(False))) or 0.0
        finally:
            db.delete(job)
            db.commit()
    assert encomenda == 3000.0  # a encomenda existe na base...
    por_chave = {s.chave: s.y for s in series}
    for chave in ("itabirito:category:grama", "itabirito:product:100"):
        assert por_chave[chave].loc["2026-01-15"] == balcao  # ...e fica fora das duas séries


def test_venda_nova_ou_alterada_muda_a_impressao_digital(client, admin):
    with SessionLocal() as db:
        antes = servico_previsao.impressao_digital(db)
        venda = db.scalar(select(Sale).order_by(Sale.id.desc()))
        quantidade = venda.quantity
        venda.quantity = quantidade + 1  # venda corrigida na base
        db.commit()
        assert servico_previsao.impressao_digital(db) != antes
        assert client.get(f"{BASE}/status", headers=admin).json()["dados_alterados"] is True
        venda.quantity = quantidade
        db.commit()

        nova = Sale(sale_date=date(2026, 2, 28), unit_id="itabirito", document_type="C1", document_number="999999",
                    product_code="100", quantity=1.0)
        db.add(nova)
        db.commit()
        try:
            assert servico_previsao.impressao_digital(db) != antes
        finally:
            db.execute(delete(Sale).where(Sale.id == nova.id))
            db.commit()
        assert servico_previsao.impressao_digital(db) == antes
    assert client.get(f"{BASE}/status", headers=admin).json()["dados_alterados"] is False


def test_disparo_com_treino_em_andamento_responde_409(client, admin, monkeypatch):
    monkeypatch.setattr(servico_previsao, "em_andamento", lambda db: ForecastJob(id=0, status="running"))
    r = client.post(f"{BASE}/treinos", headers=admin)
    assert r.status_code == 409
    assert "andamento" in r.json()["detail"]


def test_api_que_nao_treina_responde_503(client, admin, monkeypatch):
    monkeypatch.setattr(settings, "TRAINING_RUNNER", "externo")
    assert client.post(f"{BASE}/treinos", headers=admin).status_code == 503
    assert client.get(f"{BASE}/status", headers=admin).json()["treino_na_api"] is False


def test_treino_sem_sinal_vira_erro(client, admin):
    with SessionLocal() as db:
        parado = ForecastJob(status="running", created_at=datetime.now() - timedelta(hours=3),
                             heartbeat_at=datetime.now() - timedelta(hours=2))
        db.add(parado)
        db.commit()
        pid = parado.id
    s = client.get(f"{BASE}/status", headers=admin).json()
    assert s["em_andamento"] is None
    t = client.get(f"{BASE}/treinos/{pid}", headers=admin).json()
    assert t["status"] == "error" and "interrompido" in t["mensagem"]


def test_disparo_direto_libera_treino_morto(client, admin, config_rapida, monkeypatch):
    """Sem consultar o status antes: o disparo em si reconhece o treino morto e treina."""
    _forcar_novo_treino(monkeypatch)
    with SessionLocal() as db:
        morto = ForecastJob(status="running", created_at=datetime.now() - timedelta(hours=1),
                            heartbeat_at=datetime.now() - timedelta(minutes=10))
        db.add(morto)
        db.commit()
        mid = morto.id
    r = client.post(f"{BASE}/treinos", headers=admin)
    assert r.status_code == 202, r.text
    assert client.get(f"{BASE}/treinos/{mid}", headers=admin).json()["status"] == "error"
    assert _esperar_fim(client, admin)["ultimo"]["status"] == "done"


def test_treino_inexistente_responde_404(client, admin):
    assert client.get(f"{BASE}/treinos/99999", headers=admin).status_code == 404
    assert client.get(f"{BASE}/treinos/99999/series", headers=admin).status_code == 404


def test_historico_congela_ate_a_previsao_seguinte(client):
    """Três treinos: o 2º 9 dias depois do 1º, o 3º 20 dias depois do 2º. Ficam os 9 dias
    da 1ª previsão, os 14 da 2ª, e o walk-forward do 3º preenche os 6 que nenhuma cobriu.
    O produto B fica sem modelo no 2º treino: os dias dele a partir do 2º início saem."""
    loja, a, b = "itabirito", "300", "200"
    t1 = date(2026, 4, 4)
    t2, t3 = t1 + timedelta(days=9), t1 + timedelta(days=29)

    def ponto(item, dia, valor, source, origem):
        return {"level": "product", "item": item, "day": dia, "predicted": valor, "lower_95": 0.0,
                "upper_95": valor * 2, "source": source, "origin_date": origem}

    def previsao(item, inicio, valor):
        return [ponto(item, inicio + timedelta(days=i), valor, "forecast", inicio) for i in range(14)]

    def walk_forward(item, inicio, valor):  # 1º dia das 56 + 13 janelas, até a véspera do início
        return [ponto(item, inicio - timedelta(days=i), valor, "walk_forward", inicio - timedelta(days=i))
                for i in range(69, 0, -1)]

    with SessionLocal() as db:
        try:
            servico_previsao.gravar_historico(db, loja, t1, walk_forward(a, t1, 1.0) + walk_forward(b, t1, 1.0),
                                              previsao(a, t1, 10.0) + previsao(b, t1, 10.0), None)
            servico_previsao.gravar_historico(db, loja, t2, walk_forward(a, t2, 2.0), previsao(a, t2, 20.0), None)
            servico_previsao.gravar_historico(db, loja, t3, walk_forward(a, t3, 3.0) + walk_forward(b, t3, 3.0),
                                              previsao(a, t3, 30.0) + previsao(b, t3, 30.0), None)
            db.commit()
            gravado = {(item, dia): (v, fonte, origem) for (_, _, item, dia), (v, fonte, origem, _)
                       in _historico_gravado(db, ForecastHistory.item.in_((a, b))).items()}
        finally:
            db.execute(delete(ForecastHistory).where(ForecastHistory.unit_id == loja,
                                                     ForecastHistory.item.in_((a, b))))
            db.commit()

    def dias(ini, fim):
        return [ini + timedelta(days=i) for i in range((fim - ini).days + 1)]

    um = timedelta(days=1)
    for d in dias(t1 - 69 * um, t1 - um):  # antes do 1º treino: o walk-forward dele
        assert gravado[(a, d)] == (1.0, "walk_forward", d)
    for d in dias(t1, t2 - um):  # 9 dias congelados da 1ª previsão, horizontes 1..9
        assert gravado[(a, d)] == (10.0, "forecast", t1)
    for d in dias(t2, t2 + 13 * um):  # os 14 da 2ª previsão
        assert gravado[(a, d)] == (20.0, "forecast", t2)
    for d in dias(t2 + 14 * um, t3 - um):  # 6 dias que nenhuma previsão cobriu
        assert gravado[(a, d)] == (3.0, "walk_forward", d)
    for d in dias(t3, t3 + 13 * um):
        assert gravado[(a, d)] == (30.0, "forecast", t3)

    # B: os 9 dias da 1ª previsão ficam; os que ela previa depois do 2º início saíram, e o
    # walk-forward do 3º treino, quando B volta a ter modelo, preenche esses dias
    for d in dias(t1, t2 - um):
        assert gravado[(b, d)] == (10.0, "forecast", t1)
    for d in dias(t2, t3 - um):
        assert gravado[(b, d)] == (3.0, "walk_forward", d)
    # o walk-forward do 2º e do 3º treino não troca nenhum dia já gravado: só os 6 vazios
    assert len([k for k in gravado if k[0] == a]) == 69 + 9 + 14 + 6 + 14


def test_walk_forward_dos_treinos_antigos_e_apagado(client, admin, config_rapida, monkeypatch):
    """Com `FORECAST_SERVICE_KEEP_BACKTEST_JOBS = 1`, só o último treino guarda o walk-forward;
    modelos e previsões dos anteriores ficam."""
    _forcar_novo_treino(monkeypatch)
    monkeypatch.setattr(settings, "FORECAST_SERVICE_KEEP_BACKTEST_JOBS", 1)
    assert client.post(f"{BASE}/treinos", headers=admin).status_code == 202
    t = _esperar_fim(client, admin)["ultimo"]
    assert t["status"] == "done", t["mensagem"]
    with SessionLocal() as db:
        por_treino = dict(db.execute(
            select(SeriesModel.job_id, func.count(SeriesBacktestPoint.id))
            .outerjoin(SeriesBacktestPoint, SeriesBacktestPoint.model_id == SeriesModel.id)
            .group_by(SeriesModel.job_id)).all())
        anteriores = [j for j in por_treino if j != t["id"]]
        assert anteriores and all(por_treino[j] == 0 for j in anteriores)
        assert por_treino[t["id"]] == 10 * 3 * 14
        assert db.scalar(select(func.count()).select_from(SeriesForecast)
                         .join(SeriesModel, SeriesModel.id == SeriesForecast.model_id)
                         .where(SeriesModel.job_id.in_(anteriores))) > 0
    logs = client.get(f"{BASE}/treinos/{t['id']}/logs", headers=admin).json()
    assert any(l["mensagem"].startswith("Walk-forward de treinos antigos apagado") for l in logs)


def test_script_treina_fora_da_api_e_pula_sem_dados_novos(client, monkeypatch, capsys):
    """`treinar_previsoes` (API no Render, `TRAINING_RUNNER=externo`) roda o mesmo treino neste
    processo; com os dados iguais ao último treino, registra `skipped`."""
    from backend.scripts import treinar_previsoes

    monkeypatch.setattr(settings, "TRAINING_RUNNER", "externo")
    monkeypatch.setattr(settings, "TRAINING_WORKERS", 1)  # o script troca; o monkeypatch desfaz
    monkeypatch.setattr(servico_previsao, "config_treino", lambda: CONFIG_TESTE)
    monkeypatch.setattr("sys.argv", ["treinar_previsoes", "--workers", "1"])
    assert treinar_previsoes.main() == 0
    saida = capsys.readouterr().out
    assert "nada a treinar" in saida and ": skipped em" in saida
    with SessionLocal() as db:
        job = servico_previsao.ultimo(db)
    assert (job.trigger, job.status) == ("script", "skipped")
