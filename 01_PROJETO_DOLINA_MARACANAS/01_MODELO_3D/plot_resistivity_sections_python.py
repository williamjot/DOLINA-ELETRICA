"""Plot numerical resistivity sections inside the cavity model.

CSV format (long form):
distance_m,elevation_m,resistivity_ohm_m
or
distance_m,depth_m,resistivity_ohm_m

Example:
python plot_resistivity_sections_python.py --l1 section_L1.csv --l2 section_L2.csv
"""

from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import LogNorm
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parent


def read_section(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    distance = np.asarray([float(row["distance_m"]) for row in rows])
    rho = np.asarray([float(row["resistivity_ohm_m"]) for row in rows])
    if "elevation_m" in rows[0] and rows[0]["elevation_m"] not in (None, ""):
        vertical = np.asarray([float(row["elevation_m"]) for row in rows])
        vertical_kind = "elevation"
    else:
        vertical = np.asarray([float(row["depth_m"]) for row in rows])
        vertical_kind = "depth"
    return distance, vertical, rho, vertical_kind


def add_section(ax, model, line_key: str, csv_path: Path, cmap, norm):
    distance, vertical, rho, kind = read_section(csv_path)
    station = model[f"{line_key}_station_m"]
    line = model[f"{line_key}_xyz_local"]
    x = np.interp(distance, station, line[:, 0])
    y = np.interp(distance, station, line[:, 1])
    if kind == "depth":
        top = np.interp(distance, station, line[:, 2])
        z = top - vertical
        plane_vertical = vertical
    else:
        center_z = model["center_utm"][2]
        z = vertical - center_z
        plane_vertical = vertical

    triangulation = mtri.Triangulation(distance, plane_vertical)
    triangles = np.column_stack([x, y, z])[triangulation.triangles]
    face_rho = rho[triangulation.triangles].mean(axis=1)
    collection = Poly3DCollection(triangles, linewidths=0, alpha=0.94)
    collection.set_facecolor(cmap(norm(face_rho)))
    ax.add_collection3d(collection)


parser = argparse.ArgumentParser()
parser.add_argument("--l1", type=Path)
parser.add_argument("--l2", type=Path)
parser.add_argument("--output", type=Path, default=ROOT / "resistivity_sections_3d.png")
args = parser.parse_args()

model = np.load(ROOT / "dolina_model.npz", allow_pickle=False)
meta = json.loads(str(model["metadata_json"]))
sources = [path for path in (args.l1, args.l2) if path]
if not sources:
    raise SystemExit("Provide at least --l1 or --l2 with a numerical inversion CSV.")

all_rho = []
for path in sources:
    all_rho.append(read_section(path)[2])
all_rho = np.concatenate(all_rho)
norm = LogNorm(vmin=max(np.nanmin(all_rho), 1e-6), vmax=np.nanmax(all_rho))
cmap = plt.get_cmap("turbo")

fig = plt.figure(figsize=(10, 8), constrained_layout=True)
ax = fig.add_subplot(111, projection="3d")
vertices = model["vertices_open_local"]
faces = model["faces_open_0based"]
wall = Poly3DCollection(vertices[faces][::2], facecolors=(0.65, 0.58, 0.45, 0.12), edgecolors="none")
ax.add_collection3d(wall)

if args.l1:
    add_section(ax, model, "L1", args.l1, cmap, norm)
if args.l2:
    add_section(ax, model, "L2", args.l2, cmap, norm)

for key, color in (("L1", "#174a7e"), ("L2", "#b44638")):
    line = model[f"{key}_xyz_local"]
    ax.plot(line[:, 0], line[:, 1], line[:, 2], color=color, lw=1.8, label=key)

sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
fig.colorbar(sm, ax=ax, shrink=0.66, pad=0.08, label="Resistividade (ohm.m)")
ax.set(xlabel="Leste local (m)", ylabel="Norte local (m)", zlabel="Cota relativa (m)")
ax.set_xlim(-190, 190); ax.set_ylim(-150, 150); ax.set_zlim(-125, 25)
ax.set_box_aspect((380, 300, 150)); ax.view_init(elev=25, azim=-58)
ax.legend(); ax.set_title("Secoes de eletrorresistividade na Dolina dos Maracanas")
fig.savefig(args.output, dpi=240)
plt.show()
