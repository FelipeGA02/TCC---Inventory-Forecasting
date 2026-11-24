"""Leitura do relatório "Contas a Receber" (Etapa 1): a linha `Cliente:` e o cabeçalho dos itens são opcionais."""
import os

import pytest

from training_scripts.preprocessing.extrair_base_01 import FIELDS, parse_xlsx

PASTA = os.path.join(os.path.dirname(__file__), "..", "upload_marco_2026")
COM_ERROS = os.path.join(PASTA, "marco_2026_com_erros.xlsx")


@pytest.fixture(scope="module")
def leitura():
    if not os.path.exists(COM_ERROS):
        pytest.skip("planilha de teste de março ausente")
    return parse_xlsx(COM_ERROS, com_linha=True)


def test_nota_sem_linha_do_cliente_entra_sem_cliente(leitura):
    registros, puladas = leitura
    nota = [r for r in registros if r["doc_numero"] == "30744"]
    assert len(nota) == 1
    assert nota[0]["sem_linha_cliente"] is True
    assert (nota[0]["cliente_cod"], nota[0]["cliente_nome"]) == ("", "")
    assert nota[0]["empresa"] == "VERDE PERTO JARDINAGEM LTDA"  # a empresa (loja) é lida certo
    assert nota[0]["linha_documento"] == 9089 and nota[0]["linha_planilha"] == 9094


def test_nota_sem_cabecalho_dos_itens_entra(leitura):
    """Sem a linha `Produto | Qtdade | ...`, a lista de itens começa no primeiro item."""
    registros, puladas = leitura
    nota = [r for r in registros if r["doc_numero"] == "11031"]
    assert len(nota) == 1
    assert (nota[0]["produto_cod"], nota[0]["qtdade"], nota[0]["vl_total"]) == ("242", "1", "250")
    assert nota[0]["linha_planilha"] == 21816
    assert puladas == []  # nenhuma nota da planilha de teste fica de fora por formato


def test_sem_com_linha_o_registro_tem_so_as_colunas_da_base():
    if not os.path.exists(COM_ERROS):
        pytest.skip("planilha de teste de março ausente")
    registros, _ = parse_xlsx(COM_ERROS)
    assert set(registros[0]) == set(FIELDS) - {"arquivo_origem"}
