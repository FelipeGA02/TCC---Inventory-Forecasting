"""Regras das Etapas 4–7 do pré-processamento (01-pre_processing.md §6–§9).

Só funções puras, com dados sintéticos: não leem os CSVs reais nem acessam a internet.
"""
import pandas as pd
import pytest

from training_scripts.preprocessing.build_calendar import datas_comemorativas, montar_calendario
from training_scripts.preprocessing.build_daily_series import agregar
from training_scripts.preprocessing.clean_transactions import limpar, para_numero
from training_scripts.preprocessing.mark_orders import marcar


# --------------------------------------------------------------------------- #
# Etapa 4 — limpeza
# --------------------------------------------------------------------------- #
def _linha(emissao, qtd, categoria='Grama', unidade='Itabirito'):
    return {'emissao': emissao, 'empresa': 'X', 'produto_cod': '001', 'qtdade': qtd, 'vl_unit': '1,5',
            'vl_total': '3', 'vl_desconto': '', 'tot_liq': '3', 'total_liquido_doc': '3',
            'unidade': unidade, 'categoria': categoria, 'categoria_fina': 'Grama'}


def test_limpar_remove_servico_data_invalida_e_unidade_desconhecida():
    df = pd.DataFrame([
        _linha('02/01/2024', '2'),
        _linha('02/01/2024', '1', categoria='Servico e taxa'),
        _linha('31/02/2024', '1'),
        _linha('03/01/2024', '1', unidade='Desconhecida'),
        _linha('03/01/2024', '-3'),
    ])
    out, r = limpar(df)
    assert len(out) == 2
    assert r['linhas_servico_e_taxa_removidas'] == 1
    assert r['linhas_sem_data_removidas'] == 1
    assert r['linhas_unidade_desconhecida_removidas'] == 1
    assert out['data'].tolist() == ['2024-01-02', '2024-01-03']
    assert out['devolucao'].tolist() == [0, 1]          # devolução fica na base, marcada
    assert out['grupo'].tolist() == ['Grama', 'Grama']


def test_para_numero_virgula_decimal_e_vazio_vira_zero():
    assert para_numero(pd.Series(['79,90', '3', '', None, '-2'])).tolist() == [79.9, 3.0, 0.0, 0.0, -2.0]


# --------------------------------------------------------------------------- #
# Etapa 5 — encomendas (ADR-012)
# --------------------------------------------------------------------------- #
def _base_encomendas():
    dias = pd.date_range('2024-01-01', '2024-01-13')           # 2 semanas
    uteis = [d for d in dias if d.dayofweek < 6]
    linhas = [{'data': d, 'unidade': 'Itabirito', 'categoria': 'Grama', 'qtdade': 10.0} for d in uteis]
    linhas.append({'data': uteis[3], 'unidade': 'Itabirito', 'categoria': 'Grama', 'qtdade': 100.0})
    return pd.DataFrame(linhas)


def test_linha_maior_que_5_dias_tipicos_e_encomenda():
    out, lim = marcar(_base_encomendas())
    assert lim.loc[0, 'dia_tipico'] == 10.0                  # mediana diária seg–sáb
    assert lim.loc[0, 'limiar_encomenda'] == 50.0            # 5 × dia típico
    assert out['encomenda'].sum() == 1
    assert out.loc[out['encomenda'] == 1, 'qtdade'].item() == 100.0


def test_data_corte_calcula_limiar_so_com_o_passado():
    df = _base_encomendas()
    out, _ = marcar(df, data_corte='2024-01-04')             # antes da linha de 100
    assert out['encomenda'].sum() == 1
    out_cedo, lim = marcar(df, data_corte='2024-01-01')      # sem histórico: nada é encomenda
    assert out_cedo['encomenda'].sum() == 0


# --------------------------------------------------------------------------- #
# Etapa 6 — calendário por loja
# --------------------------------------------------------------------------- #
@pytest.fixture(scope='module')
def calendario():
    feriados = pd.DataFrame({'data': pd.to_datetime(['2025-11-02', '2026-02-16', '2026-02-17']),
                             'nome': ['Finados', 'Carnaval', 'Carnaval']})
    cal = montar_calendario('2025-01-01', '2026-03-31', feriados)
    return cal.set_index(['data', 'unidade'])


def _dia(cal, data, unidade):
    return cal.loc[(pd.Timestamp(data), unidade)]


def test_carnaval_fecha_as_duas_lojas(calendario):
    for u in ('Jardim Canadá', 'Itabirito'):
        assert _dia(calendario, '2026-02-16', u)['loja_fechada'] == 1
        assert _dia(calendario, '2026-02-17', u)['loja_fechada'] == 1
        assert _dia(calendario, '2026-02-14', u)['vespera_feriado'] == 0   # sábado antes de domingo
        assert _dia(calendario, '2026-02-18', u)['pos_feriado'] == 1


def test_itabirito_abre_no_dia_das_maes_e_em_finados(calendario):
    maes = '2025-05-11'                                     # domingo
    assert _dia(calendario, maes, 'Itabirito')['abertura_excepcional'] == 1
    assert _dia(calendario, maes, 'Itabirito')['loja_fechada'] == 0
    assert _dia(calendario, maes, 'Jardim Canadá')['loja_fechada'] == 1
    assert _dia(calendario, '2025-11-02', 'Itabirito')['loja_fechada'] == 0
    assert _dia(calendario, '2025-11-02', 'Jardim Canadá')['loja_fechada'] == 1


def test_fechamentos_locais(calendario):
    for u in ('Jardim Canadá', 'Itabirito'):
        assert _dia(calendario, '2025-08-15', u)['fechamento_local'] == 1
        assert _dia(calendario, '2025-12-08', u)['loja_fechada'] == 1
    assert _dia(calendario, '2025-01-02', 'Itabirito')['loja_fechada'] == 1
    assert _dia(calendario, '2025-01-02', 'Jardim Canadá')['loja_fechada'] == 0


def test_dias_ate_data_comemorativa(calendario):
    assert _dia(calendario, '2025-05-11', 'Itabirito')['dias_ate_maes'] == 0
    assert _dia(calendario, '2025-05-05', 'Itabirito')['dias_ate_maes'] == 6
    assert _dia(calendario, '2025-05-05', 'Itabirito')['janela_7d_maes'] == 1
    assert _dia(calendario, '2025-05-04', 'Itabirito')['janela_7d_maes'] == 0


def test_dia_das_maes_e_segundo_domingo_de_maio():
    dc = datas_comemorativas([2024, 2025, 2026]).set_index('evento')['data']
    assert pd.Timestamp('2024-05-12') in dc['Dia das Mães'].tolist()
    assert pd.Timestamp('2026-05-10') in dc['Dia das Mães'].tolist()


# --------------------------------------------------------------------------- #
# Etapa 7 — séries diárias
# --------------------------------------------------------------------------- #
def test_agregar_conserva_quantidade_e_preenche_dias_sem_venda():
    linhas = pd.DataFrame({
        'data': pd.to_datetime(['2024-01-01', '2024-01-01', '2024-01-03']),
        'unidade': ['Itabirito'] * 3, 'qtdade': [10.0, 100.0, -2.0], 'encomenda': [0, 1, 0],
    })
    idx = pd.date_range('2024-01-01', '2024-01-04')
    s = agregar(linhas, ['unidade'], idx).set_index('data')
    assert len(s) == 4                                        # dias sem venda entram como zero
    assert s['qtd_total'].tolist() == [110.0, 0.0, -2.0, 0.0]
    assert s['qtd_balcao'].tolist() == [10.0, 0.0, -2.0, 0.0]
    assert s['qtd_encomenda'].tolist() == [100.0, 0.0, 0.0, 0.0]
    assert s['qtd_devolucao'].tolist() == [0.0, 0.0, -2.0, 0.0]
    assert (s['qtd_balcao'] + s['qtd_encomenda'] == s['qtd_total']).all()
