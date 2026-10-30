"""Plot the cavity model and the two georeferenced ERT survey lines."""

from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parent
data = np.load(ROOT / "dolina_model.npz", allow_pickle=False)
vertices = data["vertices_open_local"]
faces = data["faces_open_0based"]
l1 = data["L1_xyz_local"]
l2 = data["L2_xyz_local"]
meta = json.loads(str(data["metadata_json"]))

fig = plt.figure(figsize=(12, 7), constrained_layout=True)
ax = fig.add_subplot(121, projection="3d")
triangles = vertices[faces]
depth = -triangles[:, :, 2].mean(axis=1)
colors = plt.get_cmap("terrain_r")(np.clip(depth / meta["depth_m"], 0, 1))
mesh = Poly3DCollection(triangles, facecolors=colors, linewidths=0.04, edgecolors=(0, 0, 0, 0.08), alpha=0.82)
ax.add_collection3d(mesh)
ax.plot(l1[:, 0], l1[:, 1], l1[:, 2], color="#174a7e", lw=2.2, label="L1")
ax.plot(l2[:, 0], l2[:, 1], l2[:, 2], color="#b44638", lw=2.2, label="L2")
ax.set(xlabel="Leste local (m)", ylabel="Norte local (m)", zlabel="Cota relativa (m)")
ax.set_xlim(-190, 190); ax.set_ylim(-150, 150); ax.set_zlim(-115, 25)
ax.set_box_aspect((380, 300, 140)); ax.view_init(elev=26, azim=-57)
ax.legend(loc="upper left")
ax.set_title("Superficie parametrica e linhas ERT")

ax2 = fig.add_subplot(122)
n_theta = int(meta["n_azimuth"])
rim = vertices[:n_theta]
ax2.fill(rim[:, 0], rim[:, 1], color="#d8c7a6", alpha=0.35, label="abertura modelada")
ax2.plot(np.r_[rim[:, 0], rim[0, 0]], np.r_[rim[:, 1], rim[0, 1]], color="#6e5b3e", lw=1.5)
ax2.plot(l1[:, 0], l1[:, 1], color="#174a7e", lw=2.0, label="L1")
ax2.plot(l2[:, 0], l2[:, 1], color="#b44638", lw=2.0, label="L2")
ax2.scatter([0], [0], s=25, color="black", marker="+", label="centro do modelo")
ax2.set_aspect("equal", adjustable="box")
ax2.set(xlabel="Leste local (m)", ylabel="Norte local (m)", title="Planta")
ax2.grid(alpha=0.2); ax2.legend(loc="best")

fig.suptitle("Dolina dos Maracanas - modelo 3D interpretativo", fontsize=14)
fig.savefig(ROOT / "preview_modelo_3d.png", dpi=220)
plt.show()
