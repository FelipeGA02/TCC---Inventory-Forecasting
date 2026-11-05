"""API dos testes de ponta a ponta (Playwright, em `app-react/e2e/`).

Sobe a API real num SQLite temporário com uma base sintética de 14 meses e um treino já
concluído, para as telas terem previsão, histórico e teste de acerto. Nunca toca o banco do
`.env` (Neon ou o SQLite de desenvolvimento): as variáveis abaixo são definidas ANTES de
importar o backend, e variável de ambiente tem prioridade sobre o `.env` no pydantic-settings.

A base com o treino leva alguns minutos para montar (~3 min com 8 núcleos); fica em cache em `tests/e2e/.cache/`
(gitignored), com `VERSAO_BASE` no nome: mudou a base sintética ou o treino, suba o número. Cada execução copia a base do cache para um
banco novo, então o que os testes gravam (planilha enviada, treino) some na próxima.

Uso (a partir de `ia-predictor/`; o `playwright.config.ts` chama sozinho):
    python -m tests.e2e.servidor [--porta 8100] [--origem http://localhost:5174]
    python -m tests.e2e.servidor --planilha caminho.xlsx [--inicio 2026-03-02 --fim 2026-03-07]
                                                          # só gera uma planilha de importação
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Suba ao mudar a base sintética, o calendário ou a configuração do treino: refaz o cache.
VERSAO_BASE = 1

AQUI = Path(__file__).resolve().parent
IA_PREDICTOR = AQUI.parents[1]
CACHE = AQUI / ".cache"

# Credenciais dos testes (as mesmas em `app-react/e2e/dados.ts`)
ADMIN = ("gestora@floricultura.com", "senha-admin-e2e")
VIEWER = ("gerente@floricultura.com", "senha-viewer-e2e")

INICIO, FIM = date(2025, 1, 2), date(2026, 2, 28)
FIM_CALENDARIO = date(2026, 3, 31)

LOJAS = [("jardim-canada", "Jardim Canadá", "Nova Lima", 1.0), ("itabirito", "Itabirito", "Itabirito", 0.6)]
EMPRESA = {"jardim-canada": "FLORICULTURA VERDE PERTO CANADÁ LTDA", "itabirito": "VERDE PERTO JARDINAGEM LTDA"}
CATEGORIAS = [
    ("grama", "Grama", "Grama", "Grama em placa, rolo e muda (esmeralda, amendoim, são carlos…)"),
    ("plantas-diversas", "Plantas diversas", "Plantas diversas",
     "Todas as plantas, exceto flores de corte: mudas, forrações, plantas em vaso, arbustos, hortaliças e ervas"),
    ("produtos-de-jardim", "Produtos de jardim", "Produtos de jardim",
     "Substratos, adubos, vasos, ferramentas e demais insumos de jardinagem"),
    ("flores-de-corte", "Flores de corte", "Flores de corte", "Flores vendidas por haste ou dúzia"),
]
# código, nome, categoria, subcategoria, venda média por dia (Jardim Canadá), preço, dias da semana com venda
PRODUTOS = [
    ("100", "GRAMA ESMERALDA M2", "grama", "Grama esmeralda", 220.0, 9.5, None),
    ("101", "GRAMA SAO CARLOS M2", "grama", "Grama são carlos", 90.0, 11.0, None),
    ("102", "GRAMA AMENDOIM MUDA", "grama", "Grama amendoim", 25.0, 3.2, None),
    ("200", "SAMAMBAIA CUIA 21", "plantas-diversas", "Plantas em vaso", 14.0, 35.0, None),
    ("201", "MUDA DE IPE AMARELO", "plantas-diversas", "Mudas", 6.0, 28.0, None),
    ("300", "TERRA VEGETAL 25KG", "produtos-de-jardim", "Substratos", 30.0, 18.0, None),
    ("301", "ADUBO NPK 10-10-10 1KG", "produtos-de-jardim", "Adubos", 12.0, 22.0, None),
    ("302", "VASO PLASTICO 30", "produtos-de-jardim", "Vasos", 8.0, 15.0, None),
    ("400", "ROSA VERMELHA DZ", "flores-de-corte", "Rosas", 4.0, 60.0, {3, 4}),
    ("401", "GIRASSOL HASTE", "flores-de-corte", "Flores diversas", 3.0, 9.0, {4, 5}),
    ("900", "FRETE", "servico-e-taxa", "Frete", 2.0, 80.0, None),
]
# peso do dia da semana (seg..sáb): pico de ter a qui, sábado fraco
DIA_SEMANA = [0.9, 1.2, 1.25, 1.2, 1.0, 0.55]
FERIADOS = {date(2025, 1, 1): "Confraternização Universal", date(2025, 3, 3): "Carnaval",
            date(2025, 3, 4): "Carnaval", date(2025, 4, 18): "Sexta-feira Santa", date(2025, 4, 21): "Tiradentes",
            date(2025, 5, 1): "Dia do Trabalho", date(2025, 6, 19): "Corpus Christi",
            date(2025, 9, 7): "Independência", date(2025, 10, 12): "Nossa Senhora Aparecida",
            date(2025, 11, 2): "Finados", date(2025, 11, 15): "Proclamação da República",
            date(2025, 11, 20): "Consciência Negra", date(2025, 12, 25): "Natal",
            date(2026, 1, 1): "Confraternização Universal", date(2026, 2, 16): "Carnaval",
            date(2026, 2, 17): "Carnaval"}
DATAS_COMEMORATIVAS = {date(2025, 5, 11): "Dia das Mães", date(2025, 6, 12): "Dia dos Namorados",
                       date(2025, 11, 2): "Finados"}

SEGREDOS = {
    "JWT_SECRET_KEY": "chave-dos-testes-e2e-0123456789abcdef0123456789",
    "ADMIN_EMAIL": ADMIN[0], "ADMIN_PASSWORD": ADMIN[1],
    "VIEWER_EMAIL": VIEWER[0], "VIEWER_PASSWORD": VIEWER[1],
}
# Treino reduzido (14 origens em vez de 56): o mesmo código do botão "Treinar previsões",
# rápido o bastante para montar a base em poucos minutos. Vale também para o treino disparado nos testes.
CONFIG = {
    "FORECAST_SERVICE_WF_ORIGINS": "14",
    "FORECAST_SERVICE_KEEP_BACKTEST_JOBS": "2",
    "TRAINING_WORKERS": str(min(8, os.cpu_count() or 2)),
    "TRAINING_RUNNER": "local",
    "DOCS_ENABLED": "false",
}


def _dias(ini: date, fim: date):
    d = ini
    while d <= fim:
        yield d
        d += timedelta(days=1)


def _fechada(d: date) -> bool:
    return d.weekday() == 6 or d in FERIADOS


def _vendas_sinteticas(inicio: date, fim: date, semente: int, primeira_nota: int = 1) -> list[dict]:
    """Uma linha por produto, loja e dia de loja aberta, com tendência, ciclo semanal,
    dezembro forte e algumas encomendas grandes de grama."""
    import numpy as np

    rng = np.random.default_rng(semente)
    vendas, nota = [], primeira_nota
    for loja, _, _, escala in LOJAS:
        for d in _dias(inicio, fim):
            if _fechada(d):
                continue
            nivel = 1.0 + 0.15 * ((d - INICIO).days / 365) + (0.35 if d.month == 12 else 0.0)
            for cod, _, cat, _, media, preco, dias in PRODUTOS:
                if dias is not None and d.weekday() not in dias:
                    continue
                if cat != "grama" and rng.random() < 0.15:
                    continue  # dia sem venda do produto
                esperado = media * escala * nivel * DIA_SEMANA[d.weekday()]
                qtd = float(max(1, round(rng.gamma(4.0, esperado / 4.0))))
                if cod == "100" and rng.random() < 0.012:
                    qtd = float(round(rng.uniform(2500, 4000)))  # obra: encomenda grande
                bruto = round(qtd * preco, 2)
                vendas.append({"sale_date": d, "unit_id": loja, "document_type": "C1",
                               "document_number": str(nota), "product_code": cod, "quantity": qtd,
                               "unit_price": preco, "gross_amount": bruto, "discount": 0.0,
                               "net_amount": bruto, "payment_method": "PIX" if nota % 3 else "CARTAO",
                               "is_registered_customer": nota % 2 == 0, "is_bulk_order": False})
                nota += 1
    return vendas


def _limiares(vendas: list[dict]) -> dict[str, float]:
    """Encomenda grande: pedido acima de média + 4 desvios-padrão da loja (ADR-018)."""
    import numpy as np

    limiares = {}
    for loja, *_ in LOJAS:
        q = np.array([v["quantity"] for v in vendas if v["unit_id"] == loja])
        limiares[loja] = round(float(q.mean() + 4 * q.std()), 1)
    return limiares


def _montar_base() -> None:
    """Popula o banco de DATABASE_URL e treina a previsão (uma vez; vai para o cache)."""
    from sqlalchemy import insert

    from backend.infrastructure.database import (
        Base, CalendarDay, Category, ProcessingLog, Product, Sale, engine)
    from backend.services import servico_previsao

    vendas = _vendas_sinteticas(INICIO, FIM, semente=2026)
    limiares = _limiares(vendas)
    for v in vendas:
        v["is_bulk_order"] = v["quantity"] > limiares[v["unit_id"]]

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        from backend.infrastructure.database import Unit

        conn.execute(insert(Unit), [{"id": i, "name": n, "city": c} for i, n, c, _ in LOJAS])
        conn.execute(insert(Category), [
            {"id": i, "name": n, "source_category": g, "description": desc, "show_on_dashboard": True,
             "sort_order": k} for k, (i, n, g, desc) in enumerate(CATEGORIAS)] + [
            {"id": "servico-e-taxa", "name": "Serviço e taxa", "source_category": "Servico e taxa",
             "description": "Frete e mão de obra", "show_on_dashboard": False, "sort_order": 9}])
        total = {}
        for v in vendas:
            total[v["product_code"]] = total.get(v["product_code"], 0.0) + v["quantity"]
        conn.execute(insert(Product), [{"code": c, "name": n, "category_id": k, "subcategory": s,
                                        "total_sold": total.get(c, 0.0)} for c, n, k, s, *_ in PRODUTOS])
        log = conn.execute(insert(ProcessingLog).values(
            kind="upload", filename="base sintética e2e.xlsx", file_sha256="e2e" + "0" * 61,
            file_size_bytes=0, reference_month=None, status="done", message="Base sintética dos testes",
            started_at=datetime(2026, 3, 1, 8, 0), finished_at=datetime(2026, 3, 1, 8, 1),
            rows_read=len(vendas), rows_added=len(vendas), rows_duplicate=0, rows_skipped=0,
            quality={"periodo": [str(INICIO), str(FIM)], "limiar_encomenda_un": limiares,
                     "linhas_de_encomenda_grande": sum(v["is_bulk_order"] for v in vendas),
                     "clientes_sem_nome_corrigidos": 0, "avisos": []}))
        import_id = log.inserted_primary_key[0]
        conn.execute(insert(Sale), [dict(v, import_id=import_id) for v in vendas])
        conn.execute(insert(CalendarDay), [
            {"unit_id": loja, "day": d, "store_closed": _fechada(d),
             "exceptional_opening": d in DATAS_COMEMORATIVAS and d.weekday() == 6,
             "holiday_name": FERIADOS.get(d), "special_date_name": DATAS_COMEMORATIVAS.get(d)}
            for loja, *_ in LOJAS for d in _dias(date(2024, 1, 1), FIM_CALENDARIO)])

    job = servico_previsao.treinar_agora(trigger="script")
    if job.status != "done":
        raise SystemExit(f"Treino da base dos testes falhou: {job.status} — {job.message}")
    engine.dispose()


def gerar_planilha(caminho: Path, inicio: date, fim: date) -> Path:
    """Planilha "Contas a Receber" no layout do relatório (o que a loja envia), com as vendas
    de `inicio` a `fim`. A de 02 a 07/03/2026 continua a base sintética, sem dias faltando."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.cell(1, 1, "VERDE PERTO")
    ws.cell(2, 1, "Contas a Receber")
    linha = 4
    for v in _vendas_sinteticas(inicio, fim, semente=inicio.toordinal(), primeira_nota=inicio.toordinal() * 1000):
        loja = v["unit_id"]
        ws.cell(linha, 1, f"Documento: C1 {v['document_number']}")
        ws.cell(linha, 3, f"Pagto: {v['payment_method']}")
        ws.cell(linha, 8, f"Emissão: {v['sale_date']:%d/%m/%Y}")
        ws.cell(linha, 17, "Operador: CAIXA 1")
        ws.cell(linha + 1, 1, "Cliente: 1 - CONSUMIDOR")
        ws.cell(linha + 2, 1, f"Empresa: {EMPRESA[loja]}")
        ws.cell(linha + 2, 13, "Vendedor: BALCAO")
        ws.cell(linha + 3, 1, "Obs:")
        ws.cell(linha + 4, 1, "Produto")
        nome = next(p[1] for p in PRODUTOS if p[0] == v["product_code"])
        ws.cell(linha + 5, 1, f"{v['product_code']} - {nome}")
        ws.cell(linha + 5, 8, v["quantity"])
        ws.cell(linha + 5, 9, v["unit_price"])
        ws.cell(linha + 5, 14, v["gross_amount"])
        ws.cell(linha + 5, 15, 0)
        ws.cell(linha + 5, 18, v["net_amount"])
        ws.cell(linha + 5, 20, 0)
        ws.cell(linha + 6, 1, "Totais")
        ws.cell(linha + 8, 5, v["net_amount"])
        linha += 10
    caminho.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho)
    return caminho


def _preparar_banco() -> Path:
    """Copia a base do cache (montando-a se preciso) para um banco novo desta execução."""
    CACHE.mkdir(exist_ok=True)
    base = CACHE / f"base-v{VERSAO_BASE}.db"
    execucao = CACHE / "execucao.db"
    for antigo in CACHE.glob("execucao.db*"):
        antigo.unlink()
    if not base.exists():
        for velho in CACHE.glob("base-*.db*"):
            velho.unlink()
        montando = CACHE / "montando.db"
        for resto in CACHE.glob("montando.db*"):
            resto.unlink()
        os.environ["DATABASE_URL"] = "sqlite:///" + montando.as_posix()
        print("e2e: montando a base sintética e treinando a previsão (só na 1ª vez, alguns minutos)...", flush=True)
        _montar_base()
        shutil.move(montando, base)
    shutil.copyfile(base, execucao)
    return execucao


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--porta", type=int, default=8100)
    parser.add_argument("--origem", default="http://localhost:5174", help="endereço do front (CORS)")
    parser.add_argument("--planilha", type=Path, help="só gera uma planilha de importação neste caminho")
    parser.add_argument("--inicio", type=date.fromisoformat, default=date(2026, 3, 2), help="1º dia da planilha")
    parser.add_argument("--fim", type=date.fromisoformat, default=date(2026, 3, 7), help="último dia da planilha")
    args = parser.parse_args()

    if args.planilha:
        print(gerar_planilha(args.planilha, args.inicio, args.fim))
        return

    os.environ.update(SEGREDOS)
    os.environ.update(CONFIG)
    os.environ["CORS_ORIGINS"] = json.dumps([args.origem])
    if str(IA_PREDICTOR) not in sys.path:
        sys.path.insert(0, str(IA_PREDICTOR))

    # O engine nasce no import do backend: a base é montada num processo filho, com o
    # DATABASE_URL do cache, e esta execução importa o backend já com o banco dela.
    import subprocess

    r = subprocess.run([sys.executable, "-c", "from tests.e2e.servidor import _preparar_banco; _preparar_banco()"],
                       cwd=IA_PREDICTOR, env=os.environ.copy())
    if r.returncode != 0:
        raise SystemExit(r.returncode)
    banco = CACHE / "execucao.db"
    os.environ["DATABASE_URL"] = "sqlite:///" + banco.as_posix()

    import uvicorn

    print(f"e2e: API dos testes em http://127.0.0.1:{args.porta} (banco {banco})", flush=True)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=args.porta, log_level="warning")


if __name__ == "__main__":
    main()
