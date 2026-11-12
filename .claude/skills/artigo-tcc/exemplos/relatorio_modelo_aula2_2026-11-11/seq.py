import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
plt.rcParams["font.family"] = "Arial"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "sequencia.png")
parts = [("Gestora de compras\n(administrador)", "#fbeee8", "#b6662e"),
         ("Painel\n(React)", "#efe6fb", "#7a5ab5"),
         ("API REST\n(FastAPI)", "#e8f1fb", "#2e75b6"),
         ("Serviço de\nprevisão", "#eaf7ea", "#3e8e41"),
         ("Banco de dados\n(PostgreSQL)", "#fff6dd", "#c9a227")]
X = [1.0, 3.6, 6.4, 9.2, 11.8]
msgs = [  # (de, para, texto, tracejada)
    (0, 1, "seleciona a planilha de vendas", False),
    (1, 2, "POST /upload/verificacao (planilha)", False),
    (2, 4, "consulta lojas, catálogo e vendas gravadas", False),
    (2, 1, "período, vendas novas e dias sem venda", True),
    (0, 1, "confirma a gravação", False),
    (1, 2, "POST /upload", False),
    (2, 4, "grava vendas, encomendas e registro da planilha", False),
    (2, 1, "resultado: há vendas novas para treinar", True),
    (0, 1, "clica em \"Treinar previsões\"", False),
    (1, 2, "POST /servico-previsao/treinos", False),
    (2, 3, "inicia o treino em segundo plano", False),
    (2, 1, "202: treino aceito", True),
    ("loop1",),
    (3, 4, "lê as séries e o calendário", False),
    (3, 3, "ajusta, valida e prevê", False),
    (3, 4, "grava modelos, previsões e histórico", False),
    ("end",),
    ("loop2",),
    (1, 2, "GET /servico-previsao/status", False),
    (2, 1, "andamento ou treino concluído", True),
    ("end",),
    (1, 2, "GET /painel", False),
    (2, 4, "lê o último treino concluído", False),
    (2, 1, "previsão, histórico e análises", True),
    (1, 0, "exibe a previsão no horizonte escolhido", True),
]
step = 0.62
n = sum(1 for m in msgs if len(m) > 1) + 4
H = 1.6 + n * step + 0.6
fig, ax = plt.subplots(figsize=(13.0, H * 0.78))
ax.set_xlim(-0.15, 13.0); ax.set_ylim(-H, 0.3); ax.axis("off")
LIFE = []
for (name, fc, ec), x in zip(parts, X):
    ax.add_patch(FancyBboxPatch((x - 1.05, -1.15), 2.1, 1.15, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=1.6))
    ax.text(x, -0.58, name, ha="center", va="center", fontsize=11.5)
    LIFE.append(x) or None
    #, color="#888888", lw=1, ls=(0, (4, 3)), zorder=0)
y = -1.15 - 0.55
LIFE2 = None
frames = []
for m in msgs:
    if m[0] in ("loop1", "loop2"):
        frames.append((m[0], y + 0.25)); y -= 0.6; continue
    if m[0] == "end":
        kind, y0 = frames.pop()
        if kind == "loop1":
            x0, x1, lab = X[3] - 1.3, X[4] + 1.0, "loop  [para cada série]"
        else:
            x0, x1, lab = X[1] - 1.3, X[2] + 1.3, "loop  [a cada 3 s, até concluir]"
        ax.add_patch(Rectangle((x0, y + 0.2), x1 - x0, y0 - (y + 0.2), fill=False, ec="#555555", lw=1.1))
        ax.add_patch(Rectangle((x0, y0 - 0.32), 2.35, 0.32, fc="#f2f2f2", ec="#555555", lw=1.1))
        ax.text(x0 + 0.08, y0 - 0.16, lab, fontsize=9.5, va="center")
        y -= 0.25; continue
    a, b, txt, dash = m
    if a == b:
        x = X[a]
        ax.annotate("", xy=(x + 0.05, y - 0.32), xytext=(x + 0.05, y), arrowprops=dict(arrowstyle="-|>", color="#555555", lw=1.2, connectionstyle="bar,fraction=-0.6"))
        ax.text(x + 0.62, y - 0.16, txt, fontsize=10, va="center", ha="left")
        y -= step + 0.2; continue
    ax.annotate("", xy=(X[b], y), xytext=(X[a], y), arrowprops=dict(arrowstyle="-|>", color="#555555", lw=1.2, ls="--" if dash else "-"))
    ax.text((X[a] + X[b]) / 2, y + 0.09, txt, fontsize=10, ha="center", va="bottom")
    y -= step
for x in X: ax.plot([x, x], [-1.15, y + 0.1], color="#888888", lw=1, ls=(0, (4, 3)), zorder=0)
ax.set_ylim(y - 0.1, 0.3)
fig.set_size_inches(13.0, (0.4 - y) * 0.78)
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white"); print(OUT)
