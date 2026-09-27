"""Etapa 5 do pipeline: marca as encomendas grandes (ADR-012).

Uma linha (documento × produto) é **encomenda** quando sua quantidade, sozinha, supera
`K = 5` dias típicos da própria `unidade × categoria` (dia típico = mediana do volume diário
em dias com venda, seg–sáb). A regra e o racional estão em `encomendas.py` e no ADR-012; esta
etapa só a aplica e grava o resultado.

**Qual histórico define o limiar.** Por padrão, todo o histórico da base, que é exatamente o
que a produção usa ao ajustar o modelo com todos os dados disponíveis. Para validar sem
vazamento (walk-forward), o treino recalcula o limiar só com as linhas anteriores a cada
origem, com `limiares_encomenda()` sobre a base desta etapa (a coluna `qtdade` está aí), ou
passando `data_corte` aqui. O teto no 99º percentil (segunda camada do ADR-012) **não** é
aplicado no pré-processamento: ele só altera o treino, nunca a base (ver `teto_quantil()`).

Também mede as **vendas médias** (EDA §4, item 17): linhas de balcão acima de 1 dia típico,
grandes mas abaixo do limiar. Não muda nada na base; só entra no relatório.

Entrada : `output/contas_a_receber_limpa.csv` (Etapa 4).
Saídas  : `output/contas_a_receber_encomendas.csv` — a base limpa + `encomenda` (0/1),
          `limiar_encomenda` e `dias_tipicos_linha` (quantos dias típicos a linha vale);
          `output/limiares_encomenda.csv` — um limiar por `unidade × categoria`.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.preprocessing.mark_orders
"""
import pandas as pd

from .constants import CLEAN_CSV, ORDER_THRESHOLDS_CSV, ORDERS_CSV
from .encomendas import K_DIAS_TIPICOS, limiares_encomenda, marcar_encomendas


def ler_base(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=';', decimal=',', encoding='utf-8', dtype={'produto_cod': str})
    df['data'] = pd.to_datetime(df['data'])
    return df


def marcar(df: pd.DataFrame, data_corte=None, k: float = K_DIAS_TIPICOS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Função pura: devolve (base com as colunas de encomenda, tabela de limiares).
    `data_corte`: se informada, o limiar usa só as linhas com `data < data_corte`."""
    hist = df if data_corte is None else df[df['data'] < pd.Timestamp(data_corte)]
    lim = limiares_encomenda(hist, k=k, col_qtd='qtdade')
    out = df.copy()
    out['encomenda'] = marcar_encomendas(out, lim, col_qtd='qtdade').astype(int)
    chave = list(zip(out['unidade'], out['categoria']))
    out['limiar_encomenda'] = [lim.get(c, float('nan')) for c in chave]
    out['dias_tipicos_linha'] = (out['qtdade'] / (out['limiar_encomenda'] / k)).round(3)

    linhas = []
    for (u, c), g in out.groupby(['unidade', 'categoria']):
        e = g[g['encomenda'] == 1]
        linhas.append({
            'unidade': u, 'categoria': c, 'k_dias_tipicos': k,
            'dia_tipico': lim.get((u, c), float('nan')) / k,
            'limiar_encomenda': lim.get((u, c), float('nan')),
            'linhas_encomenda': len(e), 'dias_com_encomenda': e['data'].nunique(),
            'pct_volume_encomenda': round(e['qtdade'].sum() / g['qtdade'].sum() * 100, 2),
        })
    return out, pd.DataFrame(linhas)


def resumir(out: pd.DataFrame, lim: pd.DataFrame) -> dict:
    res = {'k_dias_tipicos': K_DIAS_TIPICOS, 'por_unidade': {}, 'por_par': {}}
    for u, g in out.groupby('unidade'):
        e = g[g['encomenda'] == 1]
        bal = g[g['encomenda'] == 0]
        medias = bal[bal['dias_tipicos_linha'] > 1]
        dez = bal[bal['data'].dt.to_period('M') == pd.Period('2025-12')]
        dez_m = dez[dez['dias_tipicos_linha'] > 1]
        res['por_unidade'][u] = {
            'linhas_encomenda': int(len(e)),
            'dias_com_encomenda': int(e['data'].nunique()),
            'pct_volume_encomenda': round(float(e['qtdade'].sum() / g['qtdade'].sum() * 100), 1),
            'vendas_medias_balcao': {  # EDA §4 item 17
                'linhas': int(len(medias)),
                'pct_volume_balcao': round(float(medias['qtdade'].sum() / bal['qtdade'].sum() * 100), 1),
                'pct_volume_balcao_dez_2025': round(float(dez_m['qtdade'].sum() / dez['qtdade'].sum() * 100), 1)
                if len(dez) else None,
            },
        }
    for r in lim.to_dict('records'):
        res['por_par'][f"{r['unidade']} · {r['categoria']}"] = {
            'limiar_encomenda': round(r['limiar_encomenda'], 1), 'linhas_encomenda': int(r['linhas_encomenda']),
            'pct_volume_encomenda': round(r['pct_volume_encomenda'], 1)}
    return res


def mark_orders(input_path: str = CLEAN_CSV, output_path: str = ORDERS_CSV,
                thresholds_path: str = ORDER_THRESHOLDS_CSV, data_corte=None, verbose: bool = True) -> dict:
    df = ler_base(input_path)
    out, lim = marcar(df, data_corte=data_corte)
    grava = out.copy()
    grava['data'] = grava['data'].dt.strftime('%Y-%m-%d')
    grava.to_csv(output_path, sep=';', decimal=',', index=False, encoding='utf-8')
    lim.to_csv(thresholds_path, sep=';', decimal=',', index=False, encoding='utf-8')
    resumo = resumir(out, lim)
    resumo['data_corte'] = None if data_corte is None else str(pd.Timestamp(data_corte).date())
    if verbose:
        print(f'[mark_orders] Arquivos gerados: {output_path} · {thresholds_path}')
        for u, r in resumo['por_unidade'].items():
            print(f'[mark_orders] {u}: {r["linhas_encomenda"]} linhas de encomenda em {r["dias_com_encomenda"]} dias '
                  f'= {r["pct_volume_encomenda"]}% do volume · vendas médias no balcão: '
                  f'{r["vendas_medias_balcao"]["pct_volume_balcao"]}% do balcão')
    return resumo


if __name__ == '__main__':
    mark_orders()
