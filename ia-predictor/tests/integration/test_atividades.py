"""Log de uso do sistema (`GET /api/v1/atividades`, tela Relatórios): as planilhas enviadas e
os treinos da previsão, do mais recente para o mais antigo, para qualquer perfil."""
from datetime import datetime

from sqlalchemy import delete, insert

from backend.infrastructure.database import ProcessingLog, SessionLocal

CHAVES = {"tipo", "id", "inicio", "fim", "situacao", "usuario", "origem", "arquivo", "periodo",
          "linhas_novas", "linhas_duplicadas", "dados_ate", "series_com_previsao", "series_sem_dados",
          "series_com_falha", "mensagem"}


def _log(**campos) -> dict:
    base = {"kind": "upload", "file_sha256": "0" * 64, "file_size_bytes": 1, "status": "done",
            "rows_read": 10, "rows_added": 8, "rows_duplicate": 2}
    return {**base, **campos}


def test_atividades_planilhas_e_treinos(client, viewer, com_previsao):
    with SessionLocal() as db:
        ids = [db.execute(insert(ProcessingLog).values(v).returning(ProcessingLog.id)).scalar_one() for v in (
            _log(filename="mar 26.xlsx", started_at=datetime(2030, 1, 2, 9), finished_at=datetime(2030, 1, 2, 9, 1),
                 user_id=1, quality={"periodo": ["2026-03-01", "2026-03-07"]}),
            _log(filename="abr 26.xlsx", status="error", message="A planilha não tem a coluna de quantidade.",
                 started_at=datetime(2030, 1, 3, 9), rows_added=0, rows_duplicate=0),
            _log(kind="reclassification", filename="Reclassificação das categorias dos produtos",
                 started_at=datetime(2030, 1, 4, 9)),
        )]
        db.commit()
    try:
        r = client.get("/api/v1/atividades", headers=viewer)
        assert r.status_code == 200
        itens = r.json()
        assert all(set(i) == CHAVES for i in itens)
        assert [i["inicio"] for i in itens] == sorted((i["inicio"] for i in itens), reverse=True)

        planilhas = {i["id"]: i for i in itens if i["tipo"] == "planilha"}
        assert ids[2] not in planilhas  # reclassificação não é uso do sistema pela loja
        ok, erro = planilhas[ids[0]], planilhas[ids[1]]
        assert (ok["situacao"], ok["origem"], ok["arquivo"]) == ("concluido", "envio", "mar 26.xlsx")
        assert (ok["linhas_novas"], ok["linhas_duplicadas"]) == (8, 2)
        assert ok["periodo"] == ["2026-03-01", "2026-03-07"]
        assert ok["usuario"] and erro["usuario"] is None  # nome de quem enviou, quando há
        assert ok["mensagem"] is None
        assert erro["situacao"] == "erro" and erro["mensagem"] == "A planilha não tem a coluna de quantidade."

        treinos = [i for i in itens if i["tipo"] == "treino"]
        assert treinos and treinos[0]["situacao"] == "concluido"
        assert treinos[0]["series_com_previsao"] > 0 and treinos[0]["dados_ate"]
        assert treinos[0]["mensagem"] is None  # o texto do treino concluído não vai para a tela

        assert len(client.get("/api/v1/atividades", headers=viewer, params={"limite": 1}).json()) == 1
        assert client.get("/api/v1/atividades", headers=viewer, params={"limite": 0}).status_code == 422
        assert client.get("/api/v1/atividades").status_code == 401
    finally:
        with SessionLocal() as db:
            db.execute(delete(ProcessingLog).where(ProcessingLog.id.in_(ids)))
            db.commit()
