from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SRC = Path(__file__).resolve().parent / "resipy-src" / "src"
sys.path.insert(0, str(SRC))
from resipy import Project  # noqa: E402


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    out = Path(__file__).resolve().parent / "pilot_ws_l1"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    data = root / "02_DADOS_GEOFISICOS/20262210/FILTRADOS/20262210_WS_FILTRADO.bin"
    topo_xlsx = root / "02_DADOS_GEOFISICOS/20262210/Linha01_Dolina_10m.xlsx"
    topo = pd.read_excel(topo_xlsx)
    topo = topo[["X", "Y", "Z"]].astype(float)
    topo_csv = out / "topografia_xyz.csv"
    topo.to_csv(topo_csv, index=False, header=False)

    project = Project(dirname=str(out / "project"), typ="R2")
    project.createSurvey(str(data), ftype="Syscal", debug=False, estMemory=False)
    project.importElec(str(topo_csv))
    project.surveys[0].computeK()

    fig, ax = plt.subplots(figsize=(12, 5))
    project.showPseudo(ax=ax)
    fig.tight_layout()
    fig.savefig(out / "pseudosecao.png", dpi=160)
    plt.close(fig)

    project.createMesh(typ="trian", show_output=False)
    fig, ax = plt.subplots(figsize=(12, 5))
    project.showMesh(ax=ax)
    fig.tight_layout()
    fig.savefig(out / "malha.png", dpi=160)
    plt.close(fig)

    lines = []
    project.invert(iplot=False, dump=lambda msg: lines.append(str(msg)))
    (out / "inversion_dump.log").write_text("\n".join(lines), encoding="utf-8")
    project.exportMeshResults(dirname=str(out / "result_csv"), ftype=".csv")
    project.exportMeshResults(dirname=str(out / "result_vtk"), ftype=".vtk")
    project.saveProject(str(out / "pilot.resipy"))

    fig, ax = plt.subplots(figsize=(12, 5))
    project.showResults(ax=ax, sens=False, color_map="turbo")
    fig.tight_layout()
    fig.savefig(out / "inversao.png", dpi=180)
    plt.close(fig)

    print(project.summary())
    print(json.dumps(project.param, default=str, indent=2))


if __name__ == "__main__":
    main()
