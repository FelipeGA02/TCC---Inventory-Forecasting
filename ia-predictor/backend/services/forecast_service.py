"""Retreino e previsao semanal: le a base tratada, ajusta os SARIMAX e grava os resultados.

Uso, toda terca, a partir de `ia-predictor/`:
    python -m training_scripts.preprocessing.run_all      # base nova -> data/processed/
    python -m backend.services.forecast_service           # SARIMAX + previsao + logs/CSV
Opcoes: --data-carga AAAA-MM-DD (padrao: 1a terca a partir do 1o dia sem dado),
--reselecionar-ordens, --forcar (roda mesmo sem base nova), --workers N.

Cadencia
--------
O cliente envia a base atualizada toda **terca**. Depois do pre-processamento (que publica
`data/processed/`), esta rotina roda uma vez por carga:

  1. monta as series do fluxo diario: loja, as 4 categorias e os produtos regulares de
     cada unidade (`backend/domain/previsao.py`);
  2. ordem do SARIMAX: reaproveita a do registro (`models/registro_modelos.json`); serie
     nova — ou `reselecionar=True` — escolhe por AIC so com dados anteriores a 1a origem do
     backtest, como nos experimentos (sem vazamento);
  3. backtest: walk-forward com janela deslizante (`TRAIN_WINDOW_DAYS`) nas ultimas
     `BACKTEST_ORIGINS` origens do MESMO dia da semana da origem atual — a cadencia real
     (uma previsao por carga) — com o mesmo horizonte da previsao. Define o status;
  4. ajuste final com os ultimos `TRAIN_WINDOW_DAYS` dias e previsao a partir do 1o dia sem
     dado. Se o ajuste nao convergir, reaplica os parametros da semana anterior;
  5. grava previsao, metricas, registro e logs (`Armazenamento`, abaixo).

Horizonte: os 14 dias seguintes ao ultimo dia com dado (`FORECAST_HORIZON_DAYS`). Com dados
ate segunda e carga na terca, a previsao vai dessa terca ate a segunda 13 dias depois.

Receita por nivel (experimentos em `training_scripts/`): loja e categoria com d = 1 (a
previsao parte do nivel recente — doc 04); produto com d = 0 e constante. Sem log1p, m = 7,
exogenas de calendario. Encomendas (> 2.000 un. no documento) ficam fora (ADR-013).

Arquivos
--------
Entrada (`PROCESSED_DIR`, publicada pela Etapa 7 do pre-processamento):
  * `vendas_diarias.csv`, `calendario_diario.csv`, `manifesto.json`.

Saidas:
  * `MODELS_DIR/registro_modelos.json` — ordem, parametros, versao e status de cada serie;
  * `RESULTS_DIR/previsoes/previsao_<data_carga>.csv` — previsao da execucao;
  * `RESULTS_DIR/previsoes/historico_previsoes.csv` — todas as previsoes ja geradas (so
    acrescenta). Cruzada com a venda realizada das cargas seguintes, e o walk-forward real;
  * `RESULTS_DIR/metricas/metricas_<data_carga>.csv` — backtest e status por serie;
  * `RESULTS_DIR/logs/execucoes.jsonl` — uma linha por execucao (equivale ao
    `retrain_history`); `RESULTS_DIR/logs/previsao_<execucao_id>.log` — log detalhado.
"""
from __future__ import annotations

import os

# Um thread de BLAS por processo: as series ja rodam em paralelo.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402

from backend.config import settings  # noqa: E402
from backend.domain import previsao as dom  # noqa: E402
from backend.domain.previsao import (  # noqa: E402
    ALPHA, CHAVE_LOJA, GRID_PQ, GRID_SPQ, M, NIVEL_CATEGORIA, NIVEL_LOJA, NIVEL_PRODUTO,
    Especificacao, Serie, ajustar, desde_primeira_venda, dias_fechados,
    indice_diario, matriz_exogenas, origens_backtest, parametros, prever, produtos_regulares,
    proxima_data_de_carga, reaplicar, selecionar_ordem, series_da_unidade,
)

D_POR_NIVEL = {NIVEL_LOJA: 1, NIVEL_CATEGORIA: 1, NIVEL_PRODUTO: 0}
DIA_CURTO = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


@dataclass
class ConfigPrevisao:
    janela_dias: int = settings.TRAIN_WINDOW_DAYS
    horizonte_dias: int = settings.FORECAST_HORIZON_DAYS
    dia_semana_carga: int = settings.FORECAST_LOAD_WEEKDAY
    n_origens_backtest: int = settings.BACKTEST_ORIGINS
    adi_corte: float = settings.ADI_CUTOFF
    min_obs_dias: int = settings.MIN_OBSERVATIONS_DAYS
    alpha: float = ALPHA
    workers: int = settings.FORECAST_WORKERS
    grid_pq: range = field(default_factory=lambda: GRID_PQ)
    grid_spq: range = field(default_factory=lambda: GRID_SPQ)

    def n_workers(self) -> int:
        return self.workers if self.workers > 0 else max(1, (os.cpu_count() or 2) - 2)


# --------------------------------------------------------------------------- #
# Arquivos: leitura da base tratada e gravacao dos resultados (sem banco)
# --------------------------------------------------------------------------- #
IA_PREDICTOR_ROOT = Path(__file__).resolve().parents[2]   # ia-predictor/


def resolver(caminho: str | os.PathLike) -> Path:
    p = Path(caminho)
    return p if p.is_absolute() else IA_PREDICTOR_ROOT / p


class BaseNaoEncontrada(FileNotFoundError):
    pass


class Armazenamento:
    def __init__(self, processed_dir=None, models_dir=None, results_dir=None):
        self.processed = resolver(processed_dir or settings.PROCESSED_DIR)
        self.models = resolver(models_dir or settings.MODELS_DIR)
        self.results = resolver(results_dir or settings.RESULTS_DIR)
        self.dir_previsoes = self.results / "previsoes"
        self.dir_metricas = self.results / "metricas"
        self.dir_logs = self.results / "logs"

    # ------------------------------------------------------------------ entrada
    def _exigir(self, nome: str) -> Path:
        p = self.processed / nome
        if not p.exists():
            raise BaseNaoEncontrada(
                f"Base tratada não encontrada ({p}). Rode o pré-processamento "
                f"(python -m training_scripts.preprocessing.run_all) antes da previsão.")
        return p

    def ler_vendas(self) -> pd.DataFrame:
        df = pd.read_csv(self._exigir("vendas_diarias.csv"), sep=";",
                         dtype={"produto_cod": str, "produto_nome": str})
        df["data"] = pd.to_datetime(df["data"])
        return df

    def ler_calendario(self) -> pd.DataFrame:
        cal = pd.read_csv(self._exigir("calendario_diario.csv"), sep=";")
        cal["data"] = pd.to_datetime(cal["data"])
        return cal

    def ler_manifesto(self) -> dict:
        with open(self._exigir("manifesto.json"), encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------------ registro
    @property
    def _registro_path(self) -> Path:
        return self.models / "registro_modelos.json"

    def ler_registro(self) -> dict:
        if not self._registro_path.exists():
            return {"versao_formato": 1, "series": {}}
        with open(self._registro_path, encoding="utf-8") as fh:
            return json.load(fh)

    def gravar_registro(self, registro: dict) -> Path:
        self.models.mkdir(parents=True, exist_ok=True)
        tmp = self._registro_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(registro, fh, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, self._registro_path)
        return self._registro_path

    # ------------------------------------------------------------------ saidas
    def gravar_previsao(self, prev: pd.DataFrame, data_carga: pd.Timestamp) -> tuple[Path, Path]:
        self.dir_previsoes.mkdir(parents=True, exist_ok=True)
        arq = self.dir_previsoes / f"previsao_{data_carga.date()}.csv"
        prev.to_csv(arq, sep=";", index=False, decimal=".", date_format="%Y-%m-%d")
        hist = self.dir_previsoes / "historico_previsoes.csv"
        if hist.exists():
            antigo = pd.read_csv(hist, sep=";", dtype=str)
            # Reexecucao da mesma carga substitui a anterior em vez de duplicar.
            antigo = antigo[antigo["data_carga"] != str(data_carga.date())]
            novo = pd.concat([antigo, prev.astype(str)], ignore_index=True)
        else:
            novo = prev
        novo.to_csv(hist, sep=";", index=False, decimal=".", date_format="%Y-%m-%d")
        return arq, hist

    def gravar_metricas(self, met: pd.DataFrame, data_carga: pd.Timestamp) -> Path:
        self.dir_metricas.mkdir(parents=True, exist_ok=True)
        arq = self.dir_metricas / f"metricas_{data_carga.date()}.csv"
        met.to_csv(arq, sep=";", index=False, decimal=".")
        return arq

    @property
    def _execucoes_path(self) -> Path:
        return self.dir_logs / "execucoes.jsonl"

    def registrar_execucao(self, resumo: dict) -> Path:
        self.dir_logs.mkdir(parents=True, exist_ok=True)
        with open(self._execucoes_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(resumo, ensure_ascii=False, default=str) + "\n")
        return self._execucoes_path

    def ultima_execucao_concluida(self) -> dict | None:
        if not self._execucoes_path.exists():
            return None
        ultima = None
        with open(self._execucoes_path, encoding="utf-8") as fh:
            for linha in fh:
                if linha.strip():
                    r = json.loads(linha)
                    if r.get("status") == "completed":
                        ultima = r
        return ultima

    def logger(self, execucao_id: str) -> logging.Logger:
        self.dir_logs.mkdir(parents=True, exist_ok=True)
        log = logging.getLogger(f"previsao.{execucao_id}")
        log.setLevel(logging.INFO)
        log.propagate = False
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
        for h in (logging.FileHandler(self.dir_logs / f"previsao_{execucao_id}.log",
                                      encoding="utf-8"), logging.StreamHandler()):
            h.setFormatter(fmt)
            log.addHandler(h)
        return log


# --------------------------------------------------------------------------- #
# Trabalho de uma serie (roda num processo separado)
# --------------------------------------------------------------------------- #
def _treino(y: pd.Series, origem: pd.Timestamp, nivel: str, janela: int) -> pd.Series:
    s = desde_primeira_venda(y, origem) if nivel == NIVEL_PRODUTO else y[y.index < origem]
    return s.iloc[-janela:]


def processar_serie(t: dict) -> dict:
    """Ordem (se preciso) + backtest + ajuste final + previsao de uma serie."""
    serie: Serie = t["serie"]
    y, X, cfg, H = t["y"], t["X"], t["cfg"], t["horizonte"]
    out = {"id": serie.id, "spec": t["spec"], "ordem_selecionada": False, "backtest": [],
           "previsao": None, "params": None, "diagnostico": {}, "fallback": False,
           "erro": None, "falhas_backtest": 0}
    t0 = time.time()

    spec = Especificacao.de_dict(t["spec"]) if t["spec"] else None
    if spec is None:
        tr = _treino(y, t["corte_selecao"], serie.nivel, cfg.janela_dias)
        spec = selecionar_ordem(tr, X.loc[tr.index], D_POR_NIVEL[serie.nivel], M,
                                cfg.grid_pq, cfg.grid_spq)
        if spec is None:
            out["erro"] = "nenhuma ordem do SARIMAX convergiu"
            return out
        out["spec"], out["ordem_selecionada"] = spec.para_dict(), True

    for o in t["origens_backtest"]:
        tr = _treino(y, o, serie.nivel, cfg.janela_dias)
        fut = pd.date_range(o, periods=H, freq="D")
        try:
            p = prever(ajustar(tr, X.loc[tr.index], spec), X.loc[fut], cfg.alpha)
        except Exception:  # noqa: BLE001 — origem que nao converge fica fora do backtest
            out["falhas_backtest"] += 1
            continue
        naive = dom.naive_sazonal(tr, H, M)
        escala = dom.escala_mase(tr, M)
        real = y.reindex(fut).values
        for h in range(H):
            out["backtest"].append((o, fut[h], h + 1, p["previsto"].iat[h], p["ic_inf"].iat[h],
                                    p["ic_sup"].iat[h], real[h], naive[h], escala))

    tr = _treino(y, t["origem"], serie.nivel, cfg.janela_dias)
    fut = pd.date_range(t["origem"], periods=H, freq="D")
    try:
        res = ajustar(tr, X.loc[tr.index], spec)
    except Exception as exc:  # noqa: BLE001
        if not t.get("params_anteriores"):
            out["erro"] = f"ajuste final nao convergiu: {exc}"
            return out
        res = reaplicar(tr, X.loc[tr.index], spec, t["params_anteriores"])
        out["fallback"] = True
    out["previsao"] = prever(res, X.loc[fut], cfg.alpha)
    out["params"] = parametros(res)
    out["diagnostico"] = dom.diagnostico_residuos(res, M)
    out["n_obs_treino"] = int(len(tr))
    out["segundos"] = round(time.time() - t0, 1)
    return out


# --------------------------------------------------------------------------- #
# Montagem
# --------------------------------------------------------------------------- #
def _linha_metricas(serie: Serie, reg: dict, met: dict | None) -> dict:
    linha = {"unidade": serie.unidade, "nivel": serie.nivel, "chave": serie.chave,
             "nome": serie.nome, "status": reg["status"], "motivo": reg.get("motivo", ""),
             "ordem": str(tuple(reg["spec"]["order"])) if reg.get("spec") else "",
             "ordem_sazonal": str(tuple(reg["spec"]["seasonal_order"])) if reg.get("spec") else "",
             "aic_selecao": reg["spec"].get("aic") if reg.get("spec") else None,
             "versao_modelo": reg.get("versao"), "ordem_reselecionada": reg.get("ordem_reselecionada"),
             "ajuste_com_parametros_anteriores": reg.get("fallback"),
             "n_obs_treino": reg.get("n_obs_treino"),
             "ljung_box_p": reg.get("diagnostico", {}).get("ljung_box_p"),
             "shapiro_p": reg.get("diagnostico", {}).get("shapiro_p")}
    linha.update(met or {})
    return linha


def executar_previsao_semanal(armazenamento: Armazenamento | None = None,
                              cfg: ConfigPrevisao | None = None,
                              data_carga: pd.Timestamp | None = None,
                              reselecionar: bool = False, forcar: bool = False,
                              gatilho: str = "manual") -> dict:
    arm = armazenamento or Armazenamento()
    cfg = cfg or ConfigPrevisao()
    inicio = pd.Timestamp.now()
    execucao_id = inicio.strftime("%Y%m%dT%H%M%S")
    log = arm.logger(execucao_id)
    resumo = {"execucao_id": execucao_id, "iniciado_em": inicio.isoformat(timespec="seconds"),
              "gatilho": gatilho, "status": "running"}
    try:
        manifesto = arm.ler_manifesto()
        hash_base = manifesto.get("sha256", {})
        ultima = arm.ultima_execucao_concluida()
        if not forcar and not reselecionar and ultima and ultima.get("hash_base") == hash_base:
            log.info("Base sem mudança desde a execução %s: nada a fazer.", ultima["execucao_id"])
            return {**resumo, "status": "skipped", "motivo": "base sem mudanca",
                    "execucao_anterior": ultima["execucao_id"]}

        vendas, calendario = arm.ler_vendas(), arm.ler_calendario()
        idx = indice_diario(vendas)
        origem = idx[-1] + pd.Timedelta(days=1)
        data_carga = (pd.Timestamp(data_carga).normalize() if data_carga is not None
                      else proxima_data_de_carga(origem, cfg.dia_semana_carga))
        H = cfg.horizonte_dias
        bt_origens = origens_backtest(origem, H, cfg.n_origens_backtest)
        futuro = pd.date_range(origem, periods=H, freq="D")
        log.info("Execução %s · dados de %s a %s · carga %s · origem %s · horizonte %d dias "
                 "(até %s)", execucao_id, idx[0].date(), idx[-1].date(), data_carga.date(),
                 origem.date(), H, futuro[-1].date())
        log.info("Backtest: %d origens semanais (%s a %s), janela deslizante de %d dias",
                 len(bt_origens), bt_origens[0].date(), bt_origens[-1].date(), cfg.janela_dias)
        resumo.update(data_carga=str(data_carga.date()), dados_ate=str(idx[-1].date()),
                      origem=str(origem.date()), horizonte_dias=H, hash_base=hash_base)

        registro = arm.ler_registro()
        nomes_prod = (vendas.sort_values("data").groupby("produto_cod")["produto_nome"].last()
                      .to_dict())
        tarefas, series, fechados, sem_dados = [], {}, {}, []
        for unidade in sorted(vendas["unidade"].unique()):
            X = matriz_exogenas(calendario, unidade, idx.append(futuro))
            fechados[unidade] = dias_fechados(calendario, unidade)
            aberta = X.loc[idx, "loja_fechada"] == 0
            loja, cats, prods = series_da_unidade(vendas, unidade, idx)
            # Regularidade de cada produto em cada origem do backtest e na de producao.
            reg_em = {o: set(produtos_regulares(prods, aberta, o, cfg.adi_corte, cfg.min_obs_dias))
                      for o in [*bt_origens, origem]}
            candidatas = [(Serie(unidade, NIVEL_LOJA, CHAVE_LOJA, f"Loja {unidade}"), loja, bt_origens)]
            candidatas += [(Serie(unidade, NIVEL_CATEGORIA, c, c), cats[c], bt_origens)
                           for c in cats.columns]
            candidatas += [(Serie(unidade, NIVEL_PRODUTO, p, nomes_prod.get(p, p)), prods[p],
                            [o for o in bt_origens if p in reg_em[o]])
                           for p in sorted(reg_em[origem])]
            for serie, y, origens_s in candidatas:
                series[serie.id] = serie
                if serie.nivel != NIVEL_PRODUTO and (y.index < origem).sum() < cfg.min_obs_dias:
                    sem_dados.append(serie.id)
                    continue
                anterior = registro["series"].get(serie.id, {})
                spec = anterior.get("spec")
                if reselecionar or (spec and spec["order"][1] != D_POR_NIVEL[serie.nivel]):
                    spec = None
                tarefas.append({
                    "serie": serie, "y": y, "X": X, "cfg": cfg, "horizonte": H, "origem": origem,
                    "spec": spec, "corte_selecao": origens_s[0] if origens_s else origem,
                    "origens_backtest": origens_s, "params_anteriores": anterior.get("params"),
                })
        por_nivel = pd.Series([series[t["serie"].id].nivel for t in tarefas]).value_counts()
        log.info("Séries: %s · %d a escolher ordem · %d sem dados suficientes",
                 por_nivel.to_dict(), sum(t["spec"] is None for t in tarefas), len(sem_dados))

        resultados = _rodar(tarefas, cfg.n_workers(), log)

        # ------------------------------------------------------------- consolidacao
        linhas_prev, linhas_met, falhas = [], [], []
        hoje = str(data_carga.date())
        vistos = set()
        for sid in sem_dados:
            s = series[sid]
            reg = registro["series"].setdefault(sid, {})
            reg.update(unidade=s.unidade, nivel=s.nivel, chave=s.chave, nome=s.nome, ativa=True,
                       status=dom.INSUFFICIENT_DATA, motivo=f"menos de {cfg.min_obs_dias} dias de histórico",
                       ultima_execucao=execucao_id)
            linhas_met.append(_linha_metricas(s, reg, None))
            vistos.add(sid)
        for r in resultados:
            s = series[r["id"]]
            vistos.add(s.id)
            reg = registro["series"].setdefault(s.id, {})
            reg.update(unidade=s.unidade, nivel=s.nivel, chave=s.chave, nome=s.nome, ativa=True,
                       ultima_execucao=execucao_id, motivo="")
            if r["erro"]:
                falhas.append({"serie": s.id, "erro": r["erro"]})
                reg.update(status=dom.ERROR, motivo=r["erro"])
                log.error("%s: %s", s.id, r["erro"])
                linhas_met.append(_linha_metricas(s, reg, None))
                continue
            if r["ordem_selecionada"]:
                reg["versao"] = int(reg.get("versao", 0)) + 1
                reg["ordem_selecionada_em"] = hoje
            bt = pd.DataFrame(r["backtest"], columns=["origem", "data", "horizonte", "previsto",
                                                      "ic_inf", "ic_sup", "real", "naive", "escala"])
            # Metricas so nos dias de loja aberta (domingo/feriado inflam o acerto).
            met_s = dom.metricas(bt[~bt["data"].isin(fechados[s.unidade])])
            st = dom.status(met_s)
            reg.update(spec=r["spec"], params=r["params"], params_ajustados_com_dados_ate=str(idx[-1].date()),
                       status=st, diagnostico=r["diagnostico"], fallback=r["fallback"],
                       ordem_reselecionada=r["ordem_selecionada"], n_obs_treino=r["n_obs_treino"],
                       metricas_backtest=met_s,
                       motivo="" if met_s else "sem origens de backtest (série nova)")
            if r["fallback"]:
                log.warning("%s: ajuste não convergiu; usados os parâmetros da execução anterior", s.id)
            if r["falhas_backtest"]:
                log.warning("%s: %d origem(ns) do backtest sem convergência", s.id, r["falhas_backtest"])
            lb = r["diagnostico"].get("ljung_box_p")
            if lb is not None and lb <= 0.05:
                log.info("%s: Ljung-Box p = %.3f (resíduos com autocorrelação; só registro)", s.id, lb)
            linhas_met.append(_linha_metricas(s, reg, met_s))
            p = r["previsao"]
            for h, (d, v) in enumerate(p.iterrows(), start=1):
                linhas_prev.append({
                    "execucao_id": execucao_id, "data_carga": hoje, "origem": str(origem.date()),
                    "unidade": s.unidade, "nivel": s.nivel, "chave": s.chave, "nome": s.nome,
                    "data": d, "horizonte": h, "dia_semana": DIA_CURTO[d.weekday()],
                    "loja_fechada": int(d in fechados[s.unidade]),
                    "previsto": round(v["previsto"], 2), "ic_inf_95": round(v["ic_inf"], 2),
                    "ic_sup_95": round(v["ic_sup"], 2), "status": st, "versao_modelo": reg.get("versao"),
                    "ordem": f"{tuple(r['spec']['order'])}{tuple(r['spec']['seasonal_order'])}",
                })
        for sid, reg in registro["series"].items():
            if sid not in vistos and reg.get("ativa"):
                reg.update(ativa=False, motivo="produto deixou de ser regular (ADI ≥ corte)",
                           desativada_em=hoje)
                log.info("%s: desativada (deixou de ser regular)", sid)

        prev = pd.DataFrame(linhas_prev)
        met = pd.DataFrame(linhas_met).sort_values(["unidade", "nivel", "chave"])
        arq_prev, arq_hist = arm.gravar_previsao(prev, data_carga)
        arq_met = arm.gravar_metricas(met, data_carga)
        registro.update(atualizado_em=pd.Timestamp.now().isoformat(timespec="seconds"),
                        ultima_execucao=execucao_id)
        arq_reg = arm.gravar_registro(registro)

        contagem = met.groupby(["nivel", "status"]).size()
        resumo.update(
            status="completed", finalizado_em=pd.Timestamp.now().isoformat(timespec="seconds"),
            duracao_s=round((pd.Timestamp.now() - inicio).total_seconds()),
            n_series=int(len(met)),
            series_por_nivel_status={f"{n}|{s}": int(v) for (n, s), v in contagem.items()},
            n_previsoes=int(len(prev)), falhas=falhas,
            arquivos={"previsao": str(arq_prev), "historico": str(arq_hist),
                      "metricas": str(arq_met), "registro": str(arq_reg)})
        log.info("Concluído em %ss · %d séries · %s", resumo["duracao_s"], len(met),
                 resumo["series_por_nivel_status"])
        log.info("Arquivos: %s · %s · %s", arq_prev, arq_met, arq_reg)
        arm.registrar_execucao(resumo)
        return resumo
    except Exception as exc:
        log.exception("Falha na previsão semanal: %s", exc)
        resumo.update(status="failed", erro=str(exc),
                      finalizado_em=pd.Timestamp.now().isoformat(timespec="seconds"))
        arm.registrar_execucao(resumo)
        raise
    finally:
        for h in list(log.handlers):
            h.close()
            log.removeHandler(h)


def _rodar(tarefas: list[dict], workers: int, log) -> list[dict]:
    t0, saida = time.time(), []
    if workers <= 1:
        for i, t in enumerate(tarefas, 1):
            saida.append(processar_serie(t))
            log.info("[%d/%d] %s", i, len(tarefas), t["serie"].id)
        return saida
    with ProcessPoolExecutor(workers) as ex:
        futuros = {ex.submit(processar_serie, t): t["serie"].id for t in tarefas}
        for i, f in enumerate(as_completed(futuros), 1):
            try:
                saida.append(f.result())
            except Exception as exc:  # noqa: BLE001 — uma serie nao derruba a execucao
                saida.append({"id": futuros[f], "erro": f"falha inesperada: {exc}"})
            log.info("[%d/%d] %s (%.0fs)", i, len(tarefas), futuros[f], time.time() - t0)
    return saida


# --------------------------------------------------------------------------- #
# Linha de comando
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-carga", type=pd.Timestamp)
    ap.add_argument("--reselecionar-ordens", action="store_true")
    ap.add_argument("--forcar", action="store_true")
    ap.add_argument("--workers", type=int)
    a = ap.parse_args(argv)
    cfg = ConfigPrevisao()
    if a.workers:
        cfg.workers = a.workers
    resumo = executar_previsao_semanal(cfg=cfg, data_carga=a.data_carga,
                                       reselecionar=a.reselecionar_ordens, forcar=a.forcar)
    print(json.dumps({k: resumo.get(k) for k in ("status", "execucao_id", "data_carga", "origem",
                                                  "horizonte_dias", "n_series", "falhas", "arquivos")},
                     ensure_ascii=False, indent=2))
    return 0 if resumo["status"] in ("completed", "skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
