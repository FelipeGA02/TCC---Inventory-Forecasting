"""Treino de uma série diária: escolha da ordem, walk-forward e previsão dos próximos dias.

Lógica pura — recebe a série, as exógenas e a configuração, devolve o resultado. Quem lê o
banco, grava e mostra o andamento é `backend/services/servico_previsao.py`.

Protocolo
---------
  1. **Ordem por AIC** no grid `(p, q) × (P, Q)`, com `D` e `m` fixos, ajustada só na janela
     que termina na véspera da primeira origem do walk-forward — a escolha não vê o período
     que vai ser avaliado. Com `d_candidatos` (ADR-020), a ordem é escolhida para cada `d` e os
     passos 1 e 2 rodam uma vez por `d`; fica o `d` cujo walk-forward errou menos (MAE nos dias
     de loja aberta — o AIC não compara modelos com `d` diferente). Sem `d_candidatos`, só
     `config.d`.
  2. **Walk-forward com janela deslizante**: a origem anda `passo` dia(s) por vez; em cada
     origem o modelo é reajustado nos últimos `janela_dias` dias antes dela e prevê os
     `horizonte` dias seguintes. As janelas de previsão se sobrepõem: cada dia avaliado
     aparece em até `horizonte` origens, uma por horizonte h = 1..`horizonte`.
  3. **Complemento** (fora das métricas): a última origem completa fica `horizonte − 1` dias
     antes do último dia com venda, então o 1º dia das janelas não chega até ele. As origens
     seguintes, até esse dia, preveem só o próprio dia (h = 1) e servem só para o histórico
     da previsão (`domain.historico_previsao`): sem elas, os últimos 13 dias antes da
     previsão nova ficariam sem previsto.
  4. **Previsão final**: o mesmo modelo ajustado nos últimos `janela_dias` dias com venda
     conhecida prevê os `dias_previsao` dias seguintes (`horizonte_previsao`, ou `horizonte`
     sem ele — ADR-021: o sistema prevê 91 dias e a tela escolhe quantos mostrar; o
     walk-forward continua em `horizonte` = 14). Desse ajuste saem os coeficientes e o
     diagnóstico dos resíduos (Ljung-Box e Shapiro-Wilk), registrados com as métricas.
  5. **Datas comemorativas** (ADR-019): em cada previsão — do walk-forward, do complemento e a
     final —, o previsto e a faixa dos dias da semana de uma data são multiplicados pelo fator
     dela (`domain.models.datas_comemorativas`), calculado só com a venda anterior ao primeiro
     dia previsto: com `com_fator`, a alta das datas de `fator_datas` (Flores de corte); com
     `com_queda`, a queda das datas de `queda_datas` (as outras séries). As métricas do walk-forward
     já saem com o ajuste: medem o que a loja veria. A coluna `fator` (1 = sem ajuste) fica
     no walk-forward, no complemento e na previsão.

Por que escolher `d` série a série pelo walk-forward (ADR-020, doc 10): o KPSS no resíduo da
regressão nas exógenas do modelo (Hyndman & Khandakar, 2008) rejeita a estacionariedade do nível
nas séries grandes de Grama, Plantas diversas e Produtos de jardim, e nenhuma série em que ele
rejeita fica melhor com `d = 0`; mas nas séries esparsas (3 a 22 un./dia) ele não tem poder para
decidir, e várias delas erram menos com `d = 1`. O ADF é distorcido nestas séries (raiz MA perto de
−1 na diferença; Schwert, 1989). Escolher pelo erro fora da amostra cobre os dois casos. Com
`d > 0` o modelo fica sem constante (`forecaster.ajustar`: a constante viraria tendência).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import numpy as np
import pandas as pd

from backend.domain.models import datas_comemorativas, evaluator
from backend.domain.models.forecaster import ajustar, prever
from backend.domain.models.order_selection import NenhumaOrdemConvergiu, selecionar_ordem

NIVEL_CATEGORIA = "category"
NIVEL_PRODUTO = "product"


@dataclass(frozen=True)
class ConfigTreino:
    m: int = 7
    d: int = 0
    D: int = 0
    # d testados no walk-forward de cada série (ADR-020); vazio = só `d`
    d_candidatos: tuple[int, ...] = ()
    horizonte: int = 14             # do walk-forward (validação e métricas)
    horizonte_previsao: int | None = None  # dias da previsão final; None = `horizonte`
    # janela deslizante de treino; a produção usa FORECAST_SERVICE_WINDOW_DAYS (545, ADR-022). O padrão
    # fica em 365 para os experimentos de training_scripts/ continuarem reproduzindo o que documentaram
    janela_dias: int = 365
    # período em que o produto precisa ter vendido em `min_dias_com_venda` dias para ser treinado;
    # separado da janela de treino para a janela maior não trazer de volta produto parado (ADR-022)
    janela_venda_dias: int = 365
    origens: int = 56
    passo: int = 1
    grade_pq: tuple[int, ...] = (0, 1, 2)
    grade_PQ: tuple[int, ...] = (0, 1)
    alpha: float = 0.05
    maxiter: int = 200
    min_historico_dias: int = 180   # antes da primeira origem (o 1º modelo do walk-forward também tem de cumprir)
    min_dias_com_venda: int = 28    # só produto: dias com venda na última janela
    max_origens_com_falha_pct: float = 50.0
    # datas comemorativas (ADR-019): a alta nas séries treinadas com `com_fator`, a queda nas
    # treinadas com `com_queda`
    fator_datas: tuple[str, ...] = datas_comemorativas.DATAS_FLORES_DE_CORTE
    fator_regra: datas_comemorativas.Regra = datas_comemorativas.REGRA_ALTA
    queda_datas: tuple[str, ...] = datas_comemorativas.DATAS_DE_QUEDA
    queda_regra: datas_comemorativas.Regra = datas_comemorativas.REGRA_QUEDA

    @property
    def ds(self) -> tuple[int, ...]:
        """Os `d` que o treino avalia: `d_candidatos`, ou só `d`."""
        return tuple(self.d_candidatos) or (self.d,)

    @property
    def dias_previsao(self) -> int:
        """Dias da previsão final (a partir do dia seguinte à última venda)."""
        return max(self.horizonte_previsao or self.horizonte, self.horizonte)

    def como_dict(self) -> dict:
        return {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()}


@dataclass
class ResultadoSerie:
    status: str
    motivo: str | None = None
    ordem: tuple | None = None
    ordem_sazonal: tuple | None = None
    aic: float | None = None
    ordens_convergidas: int | None = None
    metricas: dict | None = None
    backtest: pd.DataFrame | None = None   # origem, data, horizonte, previsto, ic_inf, ic_sup, real, naive, fator
    complemento: pd.DataFrame | None = None  # origem, data, previsto, ic_inf, ic_sup, fator — h = 1, fora das métricas
    previsao: pd.DataFrame | None = None   # data, previsto, ic_inf, ic_sup, fator
    ajustes: list[dict] | None = None      # datas comemorativas da previsão final (`Ajuste.como_dict`)
    coeficientes: dict | None = None       # do ajuste final: nome do termo → valor
    diagnostico: dict | None = None        # ljung_box_p, shapiro_p (resíduos do ajuste final)
    treino_inicio: pd.Timestamp | None = None
    treino_fim: pd.Timestamp | None = None
    dias_historico: int = 0
    dias_com_venda_janela: int = 0
    origens_com_falha: int = 0


def origens_walk_forward(fim: pd.Timestamp, config: ConfigTreino) -> list[pd.Timestamp]:
    """As `config.origens` últimas origens que ainda têm `horizonte` dias de venda conhecida
    à frente, andando `passo` dia(s) por vez."""
    ultima = fim - pd.Timedelta(days=config.horizonte - 1)
    primeira = ultima - pd.Timedelta(days=(config.origens - 1) * config.passo)
    return list(pd.date_range(primeira, ultima, freq=f"{config.passo}D"))


def origens_complemento(fim: pd.Timestamp, config: ConfigTreino) -> list[pd.Timestamp]:
    """As origens depois da última completa até `fim`, andando `passo` dia(s): cada uma só
    tem o próprio dia de venda conhecida à frente."""
    ultima = origens_walk_forward(fim, config)[-1]
    return list(pd.date_range(ultima + pd.Timedelta(days=config.passo), fim, freq=f"{config.passo}D"))


def _janela(y: pd.Series, antes_de: pd.Timestamp, dias: int) -> pd.Series:
    """Os últimos `dias` dias da série antes de `antes_de` (janela deslizante)."""
    return y[y.index < antes_de].iloc[-dias:]


def motivo_inelegivel(y: pd.Series, config: ConfigTreino, nivel: str) -> str | None:
    """Por que a série não pode ser treinada (texto para o log), ou None se pode."""
    if y.empty or float(y.sum()) <= 0:
        return "sem venda no período"
    antes = y[y.index < origens_walk_forward(y.index.max(), config)[0]]
    if len(antes) < config.min_historico_dias:
        return (f"histórico de {len(antes)} dias antes do período de validação; "
                f"o mínimo é {config.min_historico_dias}")
    if nivel == NIVEL_PRODUTO:
        dias = int((y.iloc[-config.janela_venda_dias:] > 0).sum())
        if dias < config.min_dias_com_venda:
            return (f"vendeu em {dias} dia(s) nos últimos {config.janela_venda_dias}; "
                    f"o mínimo é {config.min_dias_com_venda}")
    return None


def _ajustes_datas(y: pd.Series, X: pd.DataFrame, antes_de: pd.Timestamp, dias: pd.DatetimeIndex,
                   config: ConfigTreino, com_fator: bool, com_queda: bool = False) -> tuple[np.ndarray, list]:
    """(multiplicador de cada dia de `dias`, ajustes) das datas comemorativas, com a venda
    anterior a `antes_de`. Sem `com_fator` nem `com_queda`, tudo 1."""
    regras = [(config.fator_datas, config.fator_regra)] * com_fator + [(config.queda_datas, config.queda_regra)] * com_queda
    if not regras:
        return np.ones(len(dias)), []
    passado = y[y.index < antes_de]
    lista = [a for datas, regra in regras for a in datas_comemorativas.ajustes(passado, X, dias, datas, regra)]
    return datas_comemorativas.multiplicadores(dias, lista), lista


def _avaliar_d(y: pd.Series, X: pd.DataFrame, aberta: pd.Series, config: ConfigTreino, origens: list,
               com_fator: bool, com_queda: bool, tick) -> dict:
    """Ordem por AIC (com `config.d`) na janela antes da 1ª origem e o walk-forward dela.
    Devolve {escolha, pontos, metricas, falhas}; `metricas` = None se falhou em origens demais.
    Levanta `NenhumaOrdemConvergiu`."""
    pre = _janela(y, origens[0], config.janela_dias)
    escolha = selecionar_ordem(pre, X.loc[pre.index], d=config.d, D=config.D, m=config.m,
                               grade_pq=config.grade_pq, grade_PQ=config.grade_PQ,
                               maxiter=config.maxiter, ao_ajustar=tick)
    linhas, falhas = [], 0
    for origem in origens:
        treino = _janela(y, origem, config.janela_dias)
        futuro = pd.date_range(origem, periods=config.horizonte, freq="D")
        try:
            res = ajustar(treino, X.loc[treino.index], escolha.ordem, escolha.ordem_sazonal, config.maxiter)
            prev, inf, sup = prever(res, X.loc[futuro], config.alpha)
        except Exception:  # noqa: BLE001 — origem que não ajusta: conta e segue
            falhas += 1
            tick()
            continue
        fator, _ = _ajustes_datas(y, X, origem, futuro, config, com_fator, com_queda)
        ultima_semana = treino.values[-config.m:]
        escala = float(np.mean(np.abs(treino.values[config.m:] - treino.values[:-config.m])))
        for h, dia in enumerate(futuro):
            linhas.append({"origem": origem, "data": dia, "horizonte": h + 1, "previsto": float(prev[h] * fator[h]),
                           "ic_inf": float(inf[h] * fator[h]), "ic_sup": float(sup[h] * fator[h]),
                           "real": float(y.loc[dia]), "naive": float(ultima_semana[h % config.m]),
                           "escala": escala, "aberta": bool(aberta.loc[dia]), "fator": float(fator[h])})
        tick()
    if not linhas or falhas * 100 > config.max_origens_com_falha_pct * len(origens):
        return {"escolha": escolha, "pontos": None, "metricas": None, "falhas": falhas}
    pontos = pd.DataFrame(linhas)
    return {"escolha": escolha, "pontos": pontos, "metricas": evaluator.metricas_walk_forward(pontos), "falhas": falhas}


def treinar_serie(y: pd.Series, X: pd.DataFrame, aberta: pd.Series, config: ConfigTreino, nivel: str,
                  ao_progredir=None, com_fator: bool = False, com_queda: bool = False) -> ResultadoSerie:
    """Treina uma série. Nunca levanta exceção: falha vira `status = "error"` com o motivo.

    `X` e `aberta` (bool: loja aberta no dia) cobrem o índice de `y` e os `config.dias_previsao`
    dias depois dele. `ao_progredir(feitos, total)` é chamado a cada ajuste. `com_fator`: aplica a
    alta das datas de `config.fator_datas`; `com_queda`, a queda das de `config.queda_datas`
    (passo 5 do protocolo).
    """
    fim = y.index.max() if len(y) else None
    janela_final = y.iloc[-config.janela_dias:]
    base = ResultadoSerie(status=evaluator.STATUS_DADOS_INSUFICIENTES, dias_historico=len(y),
                          dias_com_venda_janela=int((janela_final > 0).sum()),
                          treino_inicio=janela_final.index.min() if len(y) else None, treino_fim=fim)
    motivo = motivo_inelegivel(y, config, nivel)
    if motivo:
        base.motivo = motivo
        return base

    origens = origens_walk_forward(fim, config)
    complemento = origens_complemento(fim, config)
    n_grade = len(config.grade_pq) ** 2 * len(config.grade_PQ) ** 2
    total, feitos = (n_grade + len(origens)) * len(config.ds) + len(complemento) + 1, 0

    def tick():
        nonlocal feitos
        feitos += 1
        if ao_progredir:
            ao_progredir(feitos, total)

    try:
        # 1 e 2. Para cada d: ordem por AIC antes da 1ª origem e walk-forward.
        avaliados: dict[int, dict] = {}
        for d in config.ds:
            try:
                avaliados[d] = _avaliar_d(y, X, aberta, replace(config, d=d), origens, com_fator, com_queda, tick)
            except NenhumaOrdemConvergiu:
                continue
        if not avaliados:
            base.motivo = "nenhuma ordem do grid conseguiu ajustar a série"
            return base
        validos = {d: a for d, a in avaliados.items() if a["metricas"] is not None}
        if not validos:
            d, a = next(iter(avaliados.items()))
            base.ordem, base.ordem_sazonal, base.origens_com_falha = a["escolha"].ordem, a["escolha"].ordem_sazonal, a["falhas"]
            base.status = evaluator.STATUS_ERRO
            base.motivo = f"o modelo não ajustou em {a['falhas']} de {len(origens)} origens da validação"
            return base
        # o d do walk-forward que errou menos; empate fica com o primeiro candidato
        d = min(validos, key=lambda k: (validos[k]["metricas"]["mae"], config.ds.index(k)))
        escolhido = validos[d]
        escolha = escolhido["escolha"]
        base.ordem, base.ordem_sazonal = escolha.ordem, escolha.ordem_sazonal
        base.aic, base.ordens_convergidas = round(escolha.aic, 2), escolha.ordens_convergidas
        base.origens_com_falha = escolhido["falhas"]
        base.metricas = {**escolhido["metricas"], "origens_com_falha": escolhido["falhas"]}
        if len(config.ds) > 1:
            base.metricas["d_escolhido"] = d
            base.metricas["selecao_d"] = {
                str(k): {"ordem": [list(a["escolha"].ordem), list(a["escolha"].ordem_sazonal)],
                         "aic": round(a["escolha"].aic, 2),
                         **({k2: a["metricas"].get(k2) for k2 in ("mae", "mase", "cobertura_ic95_pct")}
                            if a["metricas"] else {"falhou": True})}
                for k, a in avaliados.items()}
        base.backtest = escolhido["pontos"].drop(columns=["escala", "aberta"])

        # 3. Complemento: o 1º dia das origens que não têm o horizonte inteiro à frente.
        linhas = []
        for origem in complemento:
            treino = _janela(y, origem, config.janela_dias)
            try:
                res = ajustar(treino, X.loc[treino.index], escolha.ordem, escolha.ordem_sazonal, config.maxiter)
                prev, inf, sup = prever(res, X.loc[[origem]], config.alpha)
            except Exception:  # noqa: BLE001 — o dia fica sem previsto, como antes da 1ª origem
                tick()
                continue
            f = _ajustes_datas(y, X, origem, pd.DatetimeIndex([origem]), config, com_fator, com_queda)[0][0]
            linhas.append({"origem": origem, "data": origem, "previsto": float(prev[0] * f),
                           "ic_inf": float(inf[0] * f), "ic_sup": float(sup[0] * f), "fator": float(f)})
            tick()
        base.complemento = pd.DataFrame(linhas, columns=["origem", "data", "previsto", "ic_inf", "ic_sup", "fator"])

        # 4. Previsão dos próximos dias com a última janela.
        futuro = pd.date_range(fim + pd.Timedelta(days=1), periods=config.dias_previsao, freq="D")
        res = ajustar(janela_final, X.loc[janela_final.index], escolha.ordem, escolha.ordem_sazonal,
                      config.maxiter)
        prev, inf, sup = prever(res, X.loc[futuro], config.alpha)
        tick()
        # 5. Datas comemorativas da previsão final (no walk-forward e no complemento, já aplicadas).
        fator, lista = _ajustes_datas(y, X, futuro[0], futuro, config, com_fator, com_queda)
        base.previsao = pd.DataFrame({"data": futuro, "previsto": prev * fator, "ic_inf": inf * fator,
                                      "ic_sup": sup * fator, "fator": fator})
        base.ajustes = [a.como_dict() for a in lista]
        base.coeficientes = {nome: round(float(v), 6) for nome, v in res.params.items()}
        base.diagnostico = evaluator.diagnostico_residuos(res.resid, descartar=config.m)
        base.status = evaluator.STATUS_TREINADO
        base.motivo = None
        return base
    except Exception as erro:  # noqa: BLE001 — a falha de uma série não derruba as outras
        base.status = evaluator.STATUS_ERRO
        base.motivo = f"{type(erro).__name__}: {erro}"[:500]
        return base


def treinar_serie_tarefa(args: tuple) -> tuple[str, ResultadoSerie]:
    """Ponto de entrada para um processo separado (`ProcessPoolExecutor`): sem callback de
    progresso, que não atravessa processos. `args` = (chave, y, X, aberta, config, nivel, com_fator, com_queda)."""
    chave, y, X, aberta, config, nivel, com_fator, com_queda = args
    return chave, treinar_serie(y, X, aberta, config, nivel, com_fator=com_fator, com_queda=com_queda)
