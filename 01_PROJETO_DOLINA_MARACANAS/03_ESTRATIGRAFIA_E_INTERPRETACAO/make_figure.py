from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle
import numpy as np


ROOT = Path(__file__).resolve().parent


def add_unit(ax, y0, y1, color, name, lithology, hatch=None, edge="#31343a"):
    ax.add_patch(Rectangle((0.08, y0), 0.42, y1-y0, facecolor=color,
                           edgecolor=edge, linewidth=1.0, hatch=hatch))
    ax.text(0.54, (y0+y1)/2, name, va="center", ha="left",
            fontsize=9.5, fontweight="bold")
    ax.text(0.54, (y0+y1)/2-0.035, lithology, va="top", ha="left",
            fontsize=7.7, color="#454952")


fig = plt.figure(figsize=(15, 9), dpi=180, facecolor="white")
gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.42], width_ratios=[1.25, 1.25, 0.92],
                      hspace=0.28, wspace=0.34)

# Panel A — regional stratigraphic column
ax = fig.add_subplot(gs[0, 0])
ax.set_xlim(-0.08, 1.18); ax.set_ylim(0, 1); ax.axis("off")
ax.set_title("A  Sucessão regional Formosa–Bezerra", loc="left", fontsize=14, pad=10)
units = [
    (0.87, 0.98, "#d9c59d", "Formação Três Marias", "arcósios e siltitos arcoseanos", ".."),
    (0.77, 0.87, "#b9aaa0", "Formação Serra da Saudade", "argilitos e siltitos", "--"),
    (0.64, 0.77, "#87b9c9", "Formação Lagoa do Jacaré", "calcários/calcarenitos e margas", "oo"),
    (0.53, 0.64, "#a8a6ad", "Formação Serra de Santa Helena", "arenitos finos e ritmitos pelíticos", "--"),
    (0.24, 0.53, "#6aa6b7", "Formação Sete Lagoas", "dolomito basal; calcilutito, calcarenito e marga", "oo"),
    (0.16, 0.24, "#8b7b70", "Formação Jequitaí", "diamictitos, arenitos líticos e pelitos", "xx"),
    (0.02, 0.16, "#c6a36a", "Topo do Grupo Paranoá", "quartzitos, ritmitos, arcósios e lentes carbonáticas", "//"),
]
for u in units:
    add_unit(ax, *u)

ax.plot([0.035, 0.035], [0.24, 0.77], color="#0f4c5c", lw=2.0)
ax.plot([0.035, 0.075], [0.24, 0.24], color="#0f4c5c", lw=2.0)
ax.plot([0.035, 0.075], [0.77, 0.77], color="#0f4c5c", lw=2.0)
ax.text(-0.005, 0.505, "intervalos carbonáticos\ncarstificáveis", rotation=90,
        ha="center", va="center", fontsize=8.6, color="#0f4c5c")
ax.text(0.08, -0.035, "Coluna esquemática; espessuras não estão em escala.",
        transform=ax.transAxes, fontsize=8.5, color="#5b6068")

# Panel B — collapse model
ax = fig.add_subplot(gs[0, 1:])
ax.set_title("B  Posição conceitual da dolina de colapso", loc="left", fontsize=14, pad=10)
ax.set_xlim(-180, 180); ax.set_ylim(-145, 28); ax.set_aspect("equal");
ax.set_xlabel("distância transversal (m)"); ax.set_ylabel("cota relativa (m)")
ax.grid(alpha=0.12)

# Layered background
layers = [
    (-145, -115, "#6aa6b7", "carbonato competente"),
    (-115, -76, "#83b7c5", "calcário/calcarenito fraturado"),
    (-76, -38, "#9aa0a7", "níveis margosos/pelíticos intercalados"),
    (-38, 0, "#73aebe", "calcário/calcarenito"),
    (0, 18, "#c7a97c", "solo e cobertura residual"),
]
for z0, z1, c, label in layers:
    ax.add_patch(Rectangle((-180, z0), 360, z1-z0, fc=c, ec="none", alpha=0.62))
    ax.text(174, (z0+z1)/2, label, ha="right", va="center", fontsize=8.4, color="#25282d")

# Collapse doline and underground remnant
x = np.linspace(-147.5, 147.5, 400)
z_top = 3 + 0.012*np.abs(x)
z_wall = -105 + 105*(np.abs(x)/147.5)**0.57
mask = np.abs(x) <= 147.5
void_poly = np.c_[np.r_[x[mask], x[mask][::-1]],
                  np.r_[z_top[mask], z_wall[mask][::-1]]]
ax.add_patch(Polygon(void_poly, closed=True, fc="white", ec="#7c3f2b", lw=2.0, zorder=6))

# Cave remnant and lake
theta = np.linspace(0, np.pi, 160)
cx = 0 + 52*np.cos(theta)
cz = -110 + 23*np.sin(theta)
cave = np.c_[np.r_[cx, 52, -52], np.r_[cz, -122, -122]]
ax.add_patch(Polygon(cave, closed=True, fc="white", ec="#31343a", lw=1.5, zorder=7))
ax.add_patch(Rectangle((-45, -122), 90, 6, fc="#3c83a6", ec="none", zorder=8))

# Rubble/breccia cone
rubble = Polygon([(-46, -105), (0, -72), (46, -105)], closed=True,
                 fc="#9a7459", ec="#5e4636", hatch="xx", alpha=0.78, zorder=8)
ax.add_patch(rubble)
ax.text(0, -91, "brecha de\ncolapso", ha="center", va="center", fontsize=8.6, zorder=9)
ax.text(0, -118.5, "cavidade remanescente + água", ha="center", va="center",
        fontsize=8.5, color="white", zorder=9)

# Fracture/collapse chimney
for dx in (-60, -35, 35, 60):
    ax.plot([dx*0.35, dx], [-72, -5], color="#7c3f2b", lw=1.0, ls=(0, (3, 3)), zorder=5)

ax.add_patch(FancyArrowPatch((-160, 2), (-160, -103), arrowstyle="<->",
                             mutation_scale=12, lw=1.8, color="#1d252d"))
ax.text(-153, -51, "105 m", rotation=90, va="center", ha="left", fontsize=10, fontweight="bold")
ax.annotate("295 m (maior dimensão)", xy=(-147.5, 14), xytext=(147.5, 14),
            ha="center", va="bottom", fontsize=10, fontweight="bold",
            arrowprops=dict(arrowstyle="<->", lw=1.8, color="#1d252d"))
ax.text(-171, -139,
        "Hipótese mais provável: dissolução e remoção subterrânea em carbonatos do Subgrupo Paraopeba,\n"
        "seguidas por falhas repetidas do teto. O vazio atual pode ser apenas o remanescente do sistema.",
        fontsize=8.2, ha="left", va="bottom", color="#30343a",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.82, pad=2.5), zorder=12)

# Panel C — line-position ranges
ax = fig.add_subplot(gs[1, :])
ax.set_title("C  Intervalo previsto da abertura nas linhas de eletrorresistividade", loc="left", fontsize=13, pad=8)
ax.set_xlim(0, 650); ax.set_ylim(-0.75, 1.75)
ax.set_xlabel("distância ao longo do perfil (m)")
ax.set_yticks([0, 1], ["L2", "L1"])
ax.grid(axis="x", alpha=0.18)
for y, color in [(0, "#b44638"), (1, "#174a7e")]:
    ax.plot([0, 650], [y, y], color="#7b8087", lw=7, solid_capstyle="butt", alpha=0.28)
    ax.plot([0, 650], [y, y], color=color, lw=1.6)

intervals = {"L1": (202, 307, 1, "#174a7e"), "L2": (301, 385, 0, "#b44638")}
for key, (a, b, y, c) in intervals.items():
    ax.plot([a, b], [y, y], color="#d98c10", lw=13, solid_capstyle="butt", alpha=0.85)
    ax.text((a+b)/2, y+0.22, f"{a}–{b} m", ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.text(645, -0.53,
        "Intervalos derivados da interseção entre os KMZ e a borda elíptica 295 × 130 m do modelo 3D;\n"
        "devem ser refinados com pontos GNSS da borda real.",
        ha="right", va="bottom", fontsize=8.8, color="#555b63")
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)

fig.suptitle("Dolina dos Maracanãs (Buraco das Araras), Formosa–GO\n"
             "interpretação estratigráfica e modelo de colapso", fontsize=17, y=0.995)

out = ROOT / "interpretacao_estratigrafica_dolina_maracanas.png"
fig.savefig(out, bbox_inches="tight", facecolor="white")
print(out)

