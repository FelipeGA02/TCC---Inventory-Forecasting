"""Gera os .dot do diagrama de classes e do modelo de dados (rótulos HTML do Graphviz)."""
import os
import sys

out = sys.argv[1]

H = 'BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" BGCOLOR="#f4f8fd" COLOR="#8ab2d7"'


def cls(n, a, m=None):
    mm = f'<HR/><TR><TD ALIGN="LEFT" BALIGN="LEFT">{m}</TD></TR>' if m else ""
    return (f'<<TABLE {H}><TR><TD><B>{n}</B></TD></TR><HR/>'
            f'<TR><TD ALIGN="LEFT" BALIGN="LEFT">{a}</TD></TR>{mm}</TABLE>>')


C = {
    "usuario": cls("Usuario", "- email<BR/>- nome<BR/>- perfil", "+ autenticar()"),
    "planilha": cls("Planilha", "- arquivo<BR/>- hashSHA256<BR/>- linhasNovas<BR/>- linhasDuplicadas<BR/>- diasSemVenda",
                    "+ conferir()<BR/>+ gravar()"),
    "loja": cls("Loja", "- id<BR/>- nome<BR/>- cidade"),
    "calendario": cls("DiaCalendario", "- dia<BR/>- lojaFechada<BR/>- aberturaExcepcional<BR/>- feriado"),
    "venda": cls("Venda", "- data<BR/>- documento<BR/>- quantidade<BR/>- valor<BR/>- encomendaGrande"),
    "produto": cls("Produto", "- codigo<BR/>- nome<BR/>- subcategoria"),
    "categoria": cls("Categoria", "- id<BR/>- nome"),
    "serie": cls("SerieDiaria", "- loja<BR/>- nivel (categoria | produto)<BR/>- item<BR/>- quantidades[]", "+ montar()"),
    "treino": cls("Treino", "- status<BR/>- impressaoDigital<BR/>- dadosAte<BR/>- configuracao", "+ executar()"),
    "modelo": cls("ModeloSerie", "- ordem(p,d,q)<BR/>- ordemSazonal<BR/>- aic<BR/>- mase<BR/>- cobertura<BR/>- coeficientes",
                  "+ selecionarOrdem()<BR/>+ validarWalkForward()<BR/>+ prever()"),
    "previsao": cls("PrevisaoDiaria", "- data<BR/>- previsto<BR/>- limiteInferior<BR/>- limiteSuperior"),
    "historico": cls("PontoHistorico", "- dia<BR/>- previsto<BR/>- dataOrigem<BR/>- fonte<BR/>- lojaFechada", "+ congelar()"),
    "relatorio": cls("Relatorio", "- tipo<BR/>- formato", "+ exportar()"),
}
nodes = "\n".join(f"  {k} [label={v}];" for k, v in C.items())
with open(os.path.join(out, "fig3_classes.dot"), "w", encoding="utf-8") as f:
    f.write(f"""digraph CLS {{
  rankdir=TB; nodesep=0.5; ranksep=0.6; newrank=true; pad=0.2;
  node [shape=plaintext, fontname="Arial", fontsize=12];
  edge [color="#555555", arrowsize=0.8, penwidth=1.0, fontname="Arial", fontsize=10];
{nodes}
  usuario -> planilha [label=" envia"];
  planilha -> venda [label=" origina"];
  venda -> loja;
  venda -> produto;
  produto -> categoria;
  loja -> calendario [arrowhead=none, arrowtail=diamond, dir=back, label=" 1..*"];
  venda -> serie [label=" agrega"];
  calendario -> serie [style=dashed, arrowhead=open, label=" exógenas"];
  usuario -> treino [label=" solicita"];
  treino -> modelo [arrowhead=none, arrowtail=diamond, dir=back, label=" 1..*"];
  serie -> modelo [label=" alimenta"];
  modelo -> previsao [label=" gera"];
  previsao -> historico [label=" congela"];
  previsao -> relatorio;
  historico -> relatorio;
  {{rank=same; usuario; planilha; venda; loja;}}
  {{rank=same; treino; categoria; produto; serie; calendario;}}
  {{rank=same; previsao; historico; relatorio;}}
}}
""")

E = 'BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4"'


def tb(n, a, c1, c2):
    return (f'<<TABLE {E} BGCOLOR="{c1}" COLOR="{c2}"><TR><TD>{n}</TD>'
            f'<TD ALIGN="LEFT" BALIGN="LEFT">{a}</TD></TR></TABLE>>')


G = ("#eaf7ea", "#75af77")
Y = ("#fff6dd", "#d6b655")
B = ("#f4f8fd", "#81acd3")
O = ("#fbeee8", "#c98a6a")
T = {
    "users": ("users", "PK id<BR/> email<BR/> name<BR/> hashed_password<BR/> role", G),
    "revoked": ("revoked_tokens", "PK jti<BR/>FK user_id<BR/> expires_at", G),
    "units": ("units", "PK id<BR/> name<BR/> city", B),
    "categories": ("categories", "PK id<BR/> name<BR/> show_on_dashboard", B),
    "products": ("products", "PK code<BR/>FK category_id<BR/> name<BR/> subcategory<BR/> total_sold", B),
    "calendar": ("calendar_days", "PK,FK unit_id<BR/>PK day<BR/> store_closed<BR/> exceptional_opening<BR/> holiday_name", B),
    "plog": ("processing_log", "PK id<BR/>FK user_id<BR/>FK forecast_job_id<BR/> filename<BR/> file_sha256<BR/> rows_added<BR/> rows_duplicate<BR/> quality", Y),
    "sales": ("sales", "PK id<BR/>FK unit_id<BR/>FK product_code<BR/>FK import_id<BR/> sale_date<BR/> document_number<BR/> quantity<BR/> net_amount<BR/> is_bulk_order", Y),
    "jobs": ("forecast_jobs", "PK id<BR/>FK user_id<BR/> trigger<BR/> status<BR/> data_fingerprint<BR/> data_until<BR/> config", O),
    "jlogs": ("forecast_job_logs", "PK id<BR/>FK job_id<BR/> series_key<BR/> message", O),
    "models": ("series_models", "PK id<BR/>FK job_id<BR/>FK unit_id<BR/>FK category_id<BR/>FK product_code<BR/> status<BR/> sarimax_order<BR/> aic<BR/> mase<BR/> ci95_coverage_pct<BR/> metrics<BR/> params", O),
    "fcst": ("series_forecasts", "PK id<BR/>FK model_id<BR/> forecast_date<BR/> predicted<BR/> lower_95<BR/> upper_95", O),
    "bt": ("series_backtest_points", "PK id<BR/>FK model_id<BR/> origin_date<BR/> day<BR/> horizon<BR/> predicted", O),
    "hist": ("forecast_history", "PK id<BR/>FK unit_id<BR/>FK job_id<BR/> level<BR/> item<BR/> day<BR/> predicted<BR/> source<BR/> store_closed", O),
}
nodes = "\n".join(f"  {k} [label={tb(n, a, c[0], c[1])}];" for k, (n, a, c) in T.items())
with open(os.path.join(out, "fig4_modelo_de_dados.dot"), "w", encoding="utf-8") as f:
    f.write(f"""digraph ER {{
  rankdir=LR; nodesep=0.3; ranksep=0.8; pad=0.2;
  node [shape=plaintext, fontname="Arial", fontsize=11];
  edge [color="#555555", fontname="Arial", fontsize=9, arrowhead=crow, penwidth=1.0];
{nodes}
  users -> revoked [label="1:N"];
  users -> plog [label="1:N"];
  users -> jobs [label="1:N"];
  categories -> products [label="1:N"];
  units -> calendar [label="1:N"];
  units -> sales [label="1:N"];
  products -> sales [label="1:N"];
  plog -> sales [label="1:N"];
  jobs -> plog [label="1:N"];
  jobs -> jlogs [label="1:N"];
  jobs -> models [label="1:N"];
  jobs -> hist [label="1:N"];
  models -> fcst [label="1:N"];
  models -> bt [label="1:N"];
}}
""")
print("ok")
