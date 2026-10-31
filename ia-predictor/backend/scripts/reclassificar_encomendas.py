"""Reclassifica as encomendas grandes da base inteira com o limiar de cada loja (ADR-018).

Para o banco carregado antes do ADR-018, marcado com o limiar fixo de 2.000 un.: calcula o
limiar de cada loja — média + 4 desvios-padrão da quantidade de todos os pedidos dela, sem
Serviço e taxa — e atualiza `sales.is_bulk_order` dos pedidos que mudam de lado. É a mesma
classificação que a carga inicial faria com a base de hoje, sem apagar usuários, treinos nem
o histórico da previsão.

Grava uma linha em `processing_log` (`kind = "reclassification"`) com os limiares, que as
telas passam a mostrar. Depois dela as planilhas novas seguem a regra do envio: recalculam o
limiar e classificam só as linhas que inserem. A marcação entra na impressão digital do
treino: o próximo "Treinar previsões" treina de novo.

Sem `--aplicar` só mostra o que mudaria.

Uso (a partir de `ia-predictor/`):
    python -m backend.scripts.reclassificar_encomendas [--aplicar]
"""
from __future__ import annotations

import argparse
from datetime import datetime

from sqlalchemy import update

from backend.infrastructure.database import ProcessingLog, Sale, SessionLocal, create_tables, engine
from backend.services.base_vendas import KIND_RECLASSIFICACAO
from backend.services.upload_service import pedidos_da_base, produtos_de_servico
from training_scripts.preprocessing.remove_encomendas_06 import K_DESVIOS, limiar_por_desvios


def log(msg: str) -> None:
    print(f"[reclassificar_encomendas] {msg}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--aplicar", action="store_true", help="grava a reclassificação (sem ele, só mostra)")
    args = parser.parse_args()
    log(f"banco: {engine.url.render_as_string(hide_password=True)}")
    create_tables()
    with SessionLocal() as db:
        pedidos = pedidos_da_base(db)
        limiares = {loja: limiar_por_desvios(t) for loja, t in pedidos.groupby("unidade")["tam"]}
        pedidos["grande"] = pedidos["tam"] > pedidos["unidade"].map(limiares)
        muda = pedidos[pedidos["grande"] != pedidos["marcado"]]

        resumo = {}
        for loja, p in pedidos.groupby("unidade"):
            m = muda[muda["unidade"] == loja]
            resumo[loja] = {"limiar_un": round(limiares[loja], 1), "pedidos": int(len(p)),
                            "encomendas_antes": int(p["marcado"].sum()), "encomendas_depois": int(p["grande"].sum()),
                            "passam_a_encomenda": int(m["grande"].sum()), "deixam_de_ser": int((~m["grande"]).sum())}
            log(f"{loja}: limiar {limiares[loja]:,.0f} un. (média + {K_DESVIOS:g} desvios de {len(p):,} pedidos) · "
                f"encomendas grandes {resumo[loja]['encomendas_antes']} → {resumo[loja]['encomendas_depois']} "
                f"(+{resumo[loja]['passam_a_encomenda']}, −{resumo[loja]['deixam_de_ser']})")
        if not args.aplicar:
            log("nada gravado (use --aplicar)")
            return

        servico = produtos_de_servico()
        for r in muda.itertuples(index=False):
            db.execute(update(Sale).where(Sale.unit_id == r.unidade, Sale.sale_date == r.emissao.date(),
                                          Sale.document_type == r.doc_tipo, Sale.document_number == r.doc_numero,
                                          Sale.product_code.not_in(servico))
                       .values(is_bulk_order=bool(r.grande)))
        agora = datetime.now()
        db.add(ProcessingLog(
            kind=KIND_RECLASSIFICACAO, filename="Reclassificação das encomendas grandes (ADR-018)",
            file_sha256="", file_size_bytes=0, status="done", stage="Concluído", started_at=agora,
            finished_at=agora,
            message=(f"Encomenda grande = pedido acima de média + {K_DESVIOS:g} desvios da loja; "
                     f"{len(muda)} pedidos mudaram de marcação"),
            quality={"limiar_encomenda_un": {loja: round(v, 1) for loja, v in limiares.items()},
                     "k_desvios": K_DESVIOS, "pedidos_remarcados": int(len(muda)), "por_loja": resumo}))
        db.commit()
        log(f"{len(muda)} pedidos remarcados e limiares gravados em processing_log")


if __name__ == "__main__":
    main()
