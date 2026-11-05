"""Regras de categoria da Etapa 3 (`taxonomy/categorias.py`) e chave da encomenda (Etapa 6)
nos casos que já classificaram errado."""
import pandas as pd
import pytest

from training_scripts.preprocessing.remove_encomendas_06 import marcar_encomendas
from training_scripts.preprocessing.taxonomy.categorias import map_categoria_negocio


@pytest.mark.parametrize("nome, categoria", [
    # ferramenta com "GRAMA" no nome não é grama
    ("RASTELO PARA GRAMA COM 30 DENTES TRAPP", "Produtos de jardim"),
    ("VASSOURA P/ GRAMA PALHA PVC RASTELO", "Produtos de jardim"),
    ("TESOURA GRAMA 12 TRAMON.78330/125", "Produtos de jardim"),
    ("GRAMA DE GATO PT 11 / CLOROFILA", "Plantas diversas"),
    ("GRAMA ESMERALDA", "Grama"),
    ("GRAMA AMENDOIM UNID. BDJA", "Grama"),
    # não vivos que caíam em "Outros" ou numa regra de planta
    ("VASO CER. COLONIAL 01", "Produtos de jardim"),
    ("POTE COR CERAMICA 01", "Produtos de jardim"),
    ("EMBALAGEM P/MUDA 14,3 LITROS", "Produtos de jardim"),
    ("CARRINHO CONST C PLAST 90L METASUL", "Produtos de jardim"),
    ("ASPERSOR ROTATIVO DE 3 BRACOS C/ 24CM MERAX", "Produtos de jardim"),
    ("FORMILIX C/ VALVULA GATILHO 500ML", "Produtos de jardim"),
    ("GRANITINA BRANCA 5KG", "Produtos de jardim"),
    ("CABO DE ACO 60CM", "Produtos de jardim"),
    ("(ITO) CORRENTE 64 CM", "Produtos de jardim"),
    ("BOMBOM FERRERO ROCHER C/ 8 UNID", "Produtos de jardim"),
    ("PETALAS DE ROSA", "Flores de corte"),
    ("FLORES DESIDRATADAS DIVERSAS", "Flores de corte"),
    ("credito icms", "Servico e taxa"),
    # planta com palavra de insumo no nome, ou com o termo no meio do nome
    ("JIBOIA ESTACA PT 30", "Plantas diversas"),
    ("BOUGAINVILLE ESTACA 0,60 A 1,00M (BUGANVILLE)", "Plantas diversas"),
    ("SAMAMBAIA MANTA AZUL PT15", "Plantas diversas"),
    ("SUCULENTA ( ROSA DE PEDRA ) CUIA", "Plantas diversas"),
    ("MUSGO VARIADO PT 11 / C13", "Plantas diversas"),
    ("JABUTICABA SABARA 3,00 M (CAIXA D`ÁGUA) C/COPA", "Plantas diversas"),
    ("GLICINIA EMBALAGEM MACIA PRETA", "Plantas diversas"),
    ("CAQUI CHOCOLATE MEDIO (ENXERTO)", "Plantas diversas"),
    ("JASMIM DO CABO", "Plantas diversas"),
    ("ALOE VASO QUADRADO (BABOSA)", "Plantas diversas"),
    ("PAU FORMIGA GDE", "Plantas diversas"),
    # insumo continua insumo
    ("MUSGO ENSACADO PCTE PEQUENO", "Produtos de jardim"),
    ("ESTACA DE MADEIRA", "Produtos de jardim"),
    ("MANTA BIDIM METRO", "Produtos de jardim"),
    ("SUBSTRATO P/SUCULENTA 10L (BIOPLANT)", "Produtos de jardim"),
    # classificação SKU a SKU de 2026-11-04: não vivos que casavam uma regra de planta
    ("CUIA PLAST.PRETO CBB-25", "Produtos de jardim"),
    ("KIT CUIA NUTRICOCO GDE", "Produtos de jardim"),
    ("POTE ORQUIDEA N 15 MD", "Produtos de jardim"),
    ("PREPARO PARA ORQUIDEAS 1KG (NUTRIPLAN)", "Produtos de jardim"),
    ("FORTH HORTALICA 400GR", "Produtos de jardim"),
    ("SEMENTE QUIABO SANTA CRUZ LINHA BOX", "Produtos de jardim"),
    ("BANDEJA 01 CELULA 21X35", "Produtos de jardim"),
    ("JARRAO DE AGUA FILTRO DE BARRO M MD", "Produtos de jardim"),
    ("ROUNDUP 1L ( RANDAP)", "Produtos de jardim"),
    ("GRAMA AMENDOIM BANDEJA", "Grama"),
    # e o que passou a Grama
    ("GRAMA PRETA PELO DE URSO BDJA (UNID)", "Grama"),
    ("CAPIM DOS TEXAS ROXO", "Grama"),
    ("SEMENTE BRACHIARIA 1KG", "Grama"),
    ("SUCULENTA ( ROSA DE PEDRA ) CUIA", "Plantas diversas"),
])
def test_categoria_pelo_nome(nome, categoria):
    assert map_categoria_negocio("", nome) == categoria


def test_encomenda_nao_soma_documentos_de_tipos_diferentes():
    """Mesmo número no mesmo dia em dois tipos de documento são duas vendas."""
    df = pd.DataFrame({"unidade": ["JC"] * 3, "emissao": ["2026-02-02"] * 3,
                       "doc_tipo": ["C7", "N3", "N3"], "doc_numero": ["10"] * 3,
                       "qtdade": [1500.0, 600.0, 100.0], "categoria": ["Grama"] * 3})
    assert not marcar_encomendas(df, 2000).any()
    df.loc[0, "doc_tipo"] = "N3"
    assert marcar_encomendas(df, 2000).all()
