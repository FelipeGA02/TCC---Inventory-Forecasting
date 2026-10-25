"""Serviço de previsão (`/api/v1/servico-previsao/*`): só admin, treino em segundo plano com
andamento e log no banco, e treino só quando os dados mudaram.

A base sintética do `conftest` tem 3 meses — menos que a janela e o histórico mínimo de
produção —, então o treino de ponta a ponta roda com uma configuração reduzida.
"""
import time
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select

from backend.config import settings
from backend.domain.models.trainer import ConfigTreino
from backend.infrastructure.database import (
    ForecastJob,
    ForecastJobLog,
    Sale,
    SeriesBacktestPoint,
    SeriesForecast,
    SeriesModel,
    SessionLocal,
)
from backend.services import servico_previsao

BASE = "/api/v1/servico-previsao"
CONFIG_TESTE = ConfigTreino(janela_dias=30, origens=3, grade_pq=(0, 1), grade_PQ=(0,), min_historico_dias=20,
                            min_dias_com_venda=10)


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


def test_status_antes_do_primeiro_treino(client, admin):
    s = client.get(f"{BASE}/status", headers=admin).json()
    assert s["treino_na_api"] is True
    assert s["em_andamento"] is None and s["ultimo_concluido_em"] is None
    assert s["dados_alterados"] is True  # nunca treinou: um disparo treina
    assert (s["config"]["m"], s["config"]["d"], s["config"]["D"]) == (7, 0, 0)
    assert s["config"]["passo_dias"] == 1 and s["config"]["horizonte_dias"] == 14


def test_treino_completo_em_segundo_plano(client, admin, config_rapida):
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

    logs = client.get(f"{BASE}/treinos/{treino_id}/logs", headers=admin).json()
    assert logs[0]["mensagem"].startswith("Treino iniciado com vendas até 28/02/2026")
    assert logs[-1]["mensagem"].startswith("Treino concluído")
    assert sum(1 for l in logs if l["serie"]) == 10  # uma linha por série
    depois = client.get(f"{BASE}/treinos/{treino_id}/logs", headers=admin, params={"apos_id": logs[-2]["id"]}).json()
    assert [l["id"] for l in depois] == [logs[-1]["id"]]


def test_sem_dados_novos_nao_treina(client, admin, config_rapida):
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


def _forcar_novo_treino(monkeypatch):
    """Ignora o último treino concluído, para disparar de novo sem mudar a base."""
    monkeypatch.setattr(servico_previsao, "ultimo_concluido", lambda db: None)


def test_treino_em_processos_paralelos(client, admin, config_rapida, monkeypatch):
    _forcar_novo_treino(monkeypatch)
    monkeypatch.setattr(settings, "TRAINING_WORKERS", 2)
    r = client.post(f"{BASE}/treinos", headers=admin)
    assert r.status_code == 202, r.text
    t = _esperar_fim(client, admin, limite_s=300)["ultimo"]
    assert t["status"] == "done", t["mensagem"]
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
    monkeypatch.setattr(servico_previsao, "_treino_da_loja_rodando", lambda db: True)
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
