"""Etapa 5 do pipeline: toda a base de enriquecimento (calendário diário por loja) em
um único CSV.

Junta num só lugar o que antes estava em dois arquivos (`dados_externos.py` +
`build_calendar.py`): a busca das fontes externas e a montagem do calendário que usa
essas fontes. Não depende da base transacional (`BaseTreino.csv`) — é construído direto
do período configurado (`CALENDAR_START`/`CALENDAR_END`) + feriados nacionais (BrasilAPI,
cacheados em `data/external/`) + fatos do histórico cadastrados em `constants.py`.

As variáveis de calendário são as únicas informações externas que ajudaram o modelo
(doc 03: erro em feriados ≈ 0, faixa de 95% 6× mais estreita, −9% de erro no ano; clima
sem ganho, por isso fica fora da série — EDA §4 item 19). `clima_diario()` é mantida só
porque o experimento `enriched/sarimax_serie_crua_enriquecida.py` ainda a usa para
comparação. O calendário é por loja porque as regras diferem: só Itabirito abre no Dia
das Mães e em Finados, e só Itabirito fechou em 02/01/2025.

Colunas do CSV de saída (uma linha por `data × unidade`, de CALENDAR_START a CALENDAR_END):

  * `dia_semana` (0 = segunda … 6 = domingo) e `nome_dia`;
  * `feriado_nacional` / `nome_feriado` — BrasilAPI (inclui Carnaval e Consciência Negra);
  * `fechamento_observado` — dia útil em que a loja vendeu zero sem ser domingo nem feriado
    nacional (constants.py). Só datas do histórico: **não é projetado para o futuro**, porque
    o motivo não está confirmado (EDA §5, pergunta 10);
  * `data_comemorativa` — nome da data no próprio dia (Dia das Mães, Namorados, Dia da
    Mulher, Pais, Finados, Natal);
  * `abertura_excepcional` — a loja abre num dia em que estaria fechada (EDA §4 item 18);
  * **`loja_fechada`** — domingo, feriado nacional ou fechamento observado, exceto abertura
    excepcional. É a variável que mais pesa (doc 03, §3.2);
  * `vespera_feriado`, `pos_feriado` — dia aberto antes/depois de um fechamento que não é
    domingo;
  * `inicio_mes` — dias 1 a 7 (semana de pagamento);
  * `janela_7d_<data>` e `dias_ate_<data>` — candidatas para a desagregação por categoria
    (EDA §3.4: o efeito das datas muda de sentido entre categorias). No L1 total não
    mostraram efeito (doc 03 §3.4) e a janela de 7 dias, sozinha, confundiu o modelo nas
    datas com abertura excepcional (doc 03 §4.3): usar junto com `abertura_excepcional`.

Fontes externas, cada uma baixada uma vez e cacheada em `data/external/` (reproduzível
mesmo sem internet depois da 1ª execução):

  * feriados nacionais — BrasilAPI (`/api/feriados/v1/{ano}`). Já inclui Carnaval,
    Sexta-feira Santa, Corpus Christi e Consciência Negra (nacional desde 2024). O WAF na
    frente da API devolve 403 sem um User-Agent de navegador — por isso o header abaixo;
  * clima diário — Open-Meteo Archive (reanálise ERA5), gratuito e sem chave. Não entra
    no CSV de enriquecimento.

Feriados municipais não têm fonte pronta. Os dias em que a loja fechou sem explicação
estão em `constants.py` (`FECHAMENTOS_OBSERVADOS`), só como fatos do histórico.

Numerada 10 (fora da sequência 1→4 da base transacional) porque não depende dela: só do
período configurado e das fontes externas. Pode rodar antes, depois ou em paralelo às
etapas 1–4.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.dados_externos_10
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, timedelta

import pandas as pd

from .extrair_base_01 import OUTPUT_DIR

_PREPROCESSING_DIR = os.path.dirname(os.path.abspath(__file__))
_IA_PREDICTOR_ROOT = os.path.dirname(os.path.dirname(_PREPROCESSING_DIR))
EXTERNAL_DIR = os.path.join(_IA_PREDICTOR_ROOT, "data", "external")

CALENDAR_CSV = os.path.join(OUTPUT_DIR, 'calendario_diario.csv')

# Vai além do fim dos dados para cobrir o horizonte de previsão.
CALENDAR_START = '2024-01-01'
CALENDAR_END = '2026-12-31'

# Unidades operacionais (taxonomy/unidades.py). Duplicada em `limpeza_para_treino_04.py`
# (mesmo fato de negócio) — não há mais um módulo central de constantes para as duas
# etapas compartilharem.
UNIDADES = ['Jardim Canadá', 'Itabirito']

# Fechamentos observados nos dados: dias úteis em que a loja vendeu zero sem ser domingo nem
# feriado nacional. São FATOS do histórico, não uma regra de calendário: não se projetam
# para anos futuros. O motivo (feriado municipal? ponte?) é desconhecido e está em aberto
# com a floricultura (EDA §5, pergunta 10). Enquanto não houver confirmação, nenhuma data
# futura é marcada como fechada por esta lista.
#   - 15/08/2024, 15/08/2025 e 08/12/2025: as duas lojas;
#   - 02/01/2025: só Itabirito (Jardim Canadá vendeu 2.394).
FECHAMENTOS_OBSERVADOS = {
    'Jardim Canadá': ['2024-08-15', '2025-08-15', '2025-12-08'],
    'Itabirito': ['2024-08-15', '2025-08-15', '2025-12-08', '2025-01-02'],
}

# Abertura excepcional (EDA §4 item 18, doc 03 §4.3): Itabirito abre no Dia das Mães
# (domingo) e em Finados (feriado), vendendo 600–900 unidades. São os únicos domingos com
# venda do histórico. Jardim Canadá nunca abriu nesses dias.
ABERTURA_EXCEPCIONAL = {
    'Jardim Canadá': [],
    'Itabirito': ['Dia das Mães', 'Finados'],
}

# Janela usada nas colunas `janela_7d_*` (candidatas, sem efeito no L1 total — doc 03 §3.4).
JANELA_DATA_DIAS = 7

LOJAS_COORD = {  # (latitude, longitude)
    "jardim_canada": (-20.06, -43.97),
    "itabirito": (-20.25, -43.80),
}

# Lista plana usada pelo experimento enriquecido (doc 03): dias úteis sem venda nas duas
# lojas que não são feriado nacional. A regra completa, por loja, está em `constants.py`.
FECHAMENTOS_LOCAIS = ["2024-08-15", "2025-08-15", "2025-12-08"]

NOMES_DIA = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
DATAS = {  # nome da data → sufixo das colunas
    'Dia das Mães': 'maes', 'Dia dos Namorados': 'namorados', 'Dia da Mulher': 'mulher',
    'Dia dos Pais': 'pais', 'Finados': 'finados', 'Natal': 'natal',
}


# --------------------------------------------------------------------------- #
# Fontes externas (feriados nacionais e clima)
# --------------------------------------------------------------------------- #

def _baixar_json(url: str) -> object:
    # BrasilAPI (e o WAF na frente dela) devolve 403 sem um User-Agent de navegador —
    # o default do urllib ("Python-urllib/3.x") é bloqueado.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def feriados_nacionais(anos) -> pd.DataFrame:
    linhas = []
    for ano in anos:
        path = os.path.join(EXTERNAL_DIR, f"feriados_nacionais_{ano}.json")
        if not os.path.exists(path):
            os.makedirs(EXTERNAL_DIR, exist_ok=True)
            dados = _baixar_json(f"https://brasilapi.com.br/api/feriados/v1/{ano}")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(dados, fh, ensure_ascii=False)
        with open(path, encoding="utf-8") as fh:
            linhas += json.load(fh)
    df = pd.DataFrame(linhas)
    df["data"] = pd.to_datetime(df["date"])
    return df[["data", "name"]].rename(columns={"name": "nome"})


def clima_diario(inicio: str, fim: str) -> pd.DataFrame:
    """Chuva (mm) e temperatura máxima (°C) por dia, média das duas lojas."""
    path = os.path.join(EXTERNAL_DIR, f"clima_open_meteo_{inicio}_{fim}.csv")
    if not os.path.exists(path):
        os.makedirs(EXTERNAL_DIR, exist_ok=True)
        tabelas = []
        for loja, (lat, lon) in LOJAS_COORD.items():
            url = (
                "https://archive-api.open-meteo.com/v1/archive"
                f"?latitude={lat}&longitude={lon}&start_date={inicio}&end_date={fim}"
                "&daily=precipitation_sum,temperature_2m_max&timezone=America%2FSao_Paulo"
            )
            d = _baixar_json(url)["daily"]
            tabelas.append(pd.DataFrame({
                "data": d["time"], "loja": loja,
                "chuva_mm": d["precipitation_sum"], "temp_max": d["temperature_2m_max"],
            }))
        pd.concat(tabelas).to_csv(path, index=False)
    df = pd.read_csv(path, parse_dates=["data"])
    return df.groupby("data")[["chuva_mm", "temp_max"]].mean()


# --------------------------------------------------------------------------- #
# Calendário diário por loja (CSV de enriquecimento)
# --------------------------------------------------------------------------- #

def _segundo_domingo(ano: int, mes: int) -> date:
    d = date(ano, mes, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)  # 1º domingo
    return d + timedelta(days=7)


def datas_comemorativas(anos) -> pd.DataFrame:
    """Uma linha por (data comemorativa, ano)."""
    linhas = []
    for a in anos:
        linhas += [
            ('Dia das Mães', _segundo_domingo(a, 5)), ('Dia dos Namorados', date(a, 6, 12)),
            ('Dia da Mulher', date(a, 3, 8)), ('Dia dos Pais', _segundo_domingo(a, 8)),
            ('Finados', date(a, 11, 2)), ('Natal', date(a, 12, 25)),
        ]
    df = pd.DataFrame(linhas, columns=['evento', 'data'])
    df['data'] = pd.to_datetime(df['data'])
    return df


def montar_calendario(inicio: str, fim: str, feriados: pd.DataFrame,
                      unidades=UNIDADES) -> pd.DataFrame:
    """Função pura. `feriados`: colunas `data` (datetime) e `nome`."""
    idx = pd.date_range(inicio, fim, freq='D')
    anos = range(idx.min().year, idx.max().year + 2)  # +1 ano para `dias_ate_*` no fim
    fer = feriados.drop_duplicates('data').set_index('data')['nome']
    dc = datas_comemorativas(anos)
    nome_data = dc.set_index('data')['evento']

    blocos = []
    for u in unidades:
        c = pd.DataFrame({'data': idx, 'unidade': u})
        c['dia_semana'] = idx.dayofweek
        c['nome_dia'] = [NOMES_DIA[d] for d in idx.dayofweek]
        c['feriado_nacional'] = idx.isin(fer.index).astype(int)
        c['nome_feriado'] = fer.reindex(idx).fillna('').values

        c['fechamento_observado'] = idx.isin(pd.to_datetime(FECHAMENTOS_OBSERVADOS.get(u, []))).astype(int)

        c['data_comemorativa'] = nome_data.reindex(idx).fillna('').values
        c['abertura_excepcional'] = c['data_comemorativa'].isin(ABERTURA_EXCEPCIONAL.get(u, [])).astype(int)

        domingo = c['dia_semana'] == 6
        fechado_por_regra = domingo | (c['feriado_nacional'] == 1) | (c['fechamento_observado'] == 1)
        c['loja_fechada'] = (fechado_por_regra & (c['abertura_excepcional'] == 0)).astype(int)

        feriado_ou_local = ((c['feriado_nacional'] == 1) | (c['fechamento_observado'] == 1)) & ~domingo \
            & (c['abertura_excepcional'] == 0)
        aberto = c['loja_fechada'] == 0
        c['vespera_feriado'] = (aberto & feriado_ou_local.shift(-1, fill_value=False)).astype(int)
        c['pos_feriado'] = (aberto & feriado_ou_local.shift(1, fill_value=False)).astype(int)
        c['inicio_mes'] = (idx.day <= 7).astype(int)

        for evento, suf in DATAS.items():
            dias = dc.loc[dc['evento'] == evento, 'data'].sort_values().values
            pos = dias.searchsorted(idx.values)  # próxima ocorrência (ou o próprio dia)
            prox = pd.to_datetime(dias[pos])
            ate = (prox - idx).days
            c[f'dias_ate_{suf}'] = ate
            c[f'janela_7d_{suf}'] = (ate < JANELA_DATA_DIAS).astype(int)
        blocos.append(c)
    return pd.concat(blocos, ignore_index=True)


def build_calendar(output_path: str = CALENDAR_CSV, inicio: str = CALENDAR_START,
                   fim: str = CALENDAR_END, verbose: bool = True) -> dict:
    anos = range(pd.Timestamp(inicio).year, pd.Timestamp(fim).year + 1)
    cal = montar_calendario(inicio, fim, feriados_nacionais(anos))
    grava = cal.copy()
    grava['data'] = grava['data'].dt.strftime('%Y-%m-%d')
    grava.to_csv(output_path, sep=';', index=False, encoding='utf-8')

    resumo = {'periodo': [inicio, fim], 'linhas': int(len(cal)), 'por_unidade': {}}
    for u, g in cal.groupby('unidade'):
        uteis = g[g['dia_semana'] < 6]
        resumo['por_unidade'][u] = {
            'dias_loja_fechada': int(g['loja_fechada'].sum()),
            'feriados_nacionais_seg_sab': int(uteis['feriado_nacional'].sum()),
            'fechamentos_observados': g.loc[g['fechamento_observado'] == 1, 'data'].dt.strftime('%Y-%m-%d').tolist(),
            'aberturas_excepcionais': g.loc[g['abertura_excepcional'] == 1, 'data'].dt.strftime('%Y-%m-%d').tolist(),
        }
    if verbose:
        print(f'[dados_externos_10] Arquivo gerado: {output_path} ({len(cal):,} linhas)'.replace(',', '.'))
        for u, r in resumo['por_unidade'].items():
            print(f'[dados_externos_10] {u}: {r["dias_loja_fechada"]} dias fechada · '
                  f'{r["feriados_nacionais_seg_sab"]} feriados nacionais seg–sáb · '
                  f'{len(r["fechamentos_observados"])} fechamentos observados · '
                  f'{len(r["aberturas_excepcionais"])} aberturas excepcionais')
    return resumo


if __name__ == '__main__':
    build_calendar()
