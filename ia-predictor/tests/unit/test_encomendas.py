"""Encomenda grande: pedido acima de média + 4 desvios-padrão da quantidade dos pedidos da
loja (Etapa 6, ADR-018)."""
import numpy as np
import pandas as pd

from training_scripts.preprocessing.remove_encomendas_06 import (
    LIMIAR_QTD_VENDA,
    calcular_limiares,
    limiar_por_desvios,
    marcar_encomendas,
    marcar_encomendas_por_unidade,
    tamanho_dos_pedidos,
)


def _linha(doc: str, qtd: float, dia: str = "2025-03-10", tipo: str = "C1", loja: str = "Itabirito") -> dict:
    return {"unidade": loja, "emissao": pd.Timestamp(dia), "doc_tipo": tipo, "doc_numero": doc, "qtdade": qtd}


def _base(n: int = 200, loja: str = "Itabirito", escala: float = 1) -> list[dict]:
    """Pedidos de 1 a 10 unidades (vezes `escala`)."""
    return [_linha(f"N{i}", escala * (1 + i % 10), loja=loja) for i in range(n)]


def test_pedido_soma_as_suas_linhas():
    df = pd.DataFrame([_linha("A", 3), _linha("A", 4), _linha("B", 5)])
    assert tamanho_dos_pedidos(df).tolist() == [7.0, 5.0]


def test_limiar_e_media_mais_4_desvios_em_unidades():
    df = pd.DataFrame(_base())
    t = tamanho_dos_pedidos(df)
    assert np.isclose(calcular_limiares(df)["Itabirito"], t.mean() + 4 * t.std())
    assert np.isclose(calcular_limiares(df, k=3)["Itabirito"], t.mean() + 3 * t.std())


def test_devolucao_nao_entra_na_distribuicao():
    com_devolucao = pd.DataFrame(_base() + [_linha("DEV", -500)])
    assert np.isclose(calcular_limiares(com_devolucao)["Itabirito"], calcular_limiares(pd.DataFrame(_base()))["Itabirito"])


def test_marca_o_pedido_inteiro_acima_do_limiar():
    # 60 unidades em 3 linhas: abaixo de 2.000, mas muito fora do padrão de 1 a 10 por pedido
    df = pd.DataFrame(_base() + [_linha("OBRA", 20), _linha("OBRA", 20), _linha("OBRA", 20)])
    limiares = calcular_limiares(df)
    assert limiares["Itabirito"] < 60 < LIMIAR_QTD_VENDA
    marca = marcar_encomendas_por_unidade(df, limiares)
    assert marca[df["doc_numero"] == "OBRA"].all() and marca.sum() == 3


def test_mesmo_numero_em_tipos_diferentes_sao_pedidos_diferentes():
    df = pd.DataFrame(_base() + [_linha("X", 40, tipo="C7"), _linha("X", 40, tipo="N3")])
    assert len(tamanho_dos_pedidos(df)) == 202
    assert not marcar_encomendas(df, 60).any()


def test_base_sem_pedidos_usa_o_limiar_fixo():
    assert limiar_por_desvios(pd.Series(dtype=float)) == LIMIAR_QTD_VENDA


def test_cada_loja_tem_o_seu_limiar():
    # Jardim Canadá vende pedidos 10 vezes maiores: 60 un. é encomenda só em Itabirito
    df = pd.DataFrame(_base() + _base(loja="Jardim Canadá", escala=10)
                      + [_linha("OBRA", 60), _linha("OBRA", 60, loja="Jardim Canadá")])
    limiares = calcular_limiares(df)
    assert limiares["Itabirito"] < 60 < limiares["Jardim Canadá"]
    marca = marcar_encomendas_por_unidade(df, limiares)
    obra = df["doc_numero"] == "OBRA"
    assert marca[obra & (df["unidade"] == "Itabirito")].all()
    assert not marca[obra & (df["unidade"] == "Jardim Canadá")].any()


def test_loja_sem_limiar_usa_o_fixo():
    df = pd.DataFrame([_linha("A", LIMIAR_QTD_VENDA + 1), _linha("B", 50)])
    assert marcar_encomendas_por_unidade(df, {}).tolist() == [True, False]
