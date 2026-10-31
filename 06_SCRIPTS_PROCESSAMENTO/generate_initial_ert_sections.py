"""Export initial raw ERT pseudosections, individual and combined by line."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from resipy import Project


LINES = {
    "L1": {
        "folder": "20262210",
        "topography": "Linha01_Dolina_10m.xlsx",
        "arrays": [
            ("DD", "20262210_DD_BRUTO.bin", False),
            ("WS", "20262210_WS_BRUTO.bin", False),
        ],
    },
    "L2": {
        "folder": "20262410",
        "topography": "Linha02_Dolina_10m.xlsx",
        "arrays": [
            ("DD", "20262410_DD_BRUTO.bin", False),
            ("WS", "20262410_WS_BRUTO.bin", False),
            ("PD", "20262410_PD_BRUTO.bin", True),
        ],
    },
}


def load_topography(path: Path) -> pd.DataFrame:
    topo = pd.read_excel(path)[["X", "Y", "Z"]].astype(float)
    if len(topo) != 66:
        raise ValueError(f"Esperados 66 eletrodos: {path}")
    return topo


def apply_electrodes(project: Project, topo: pd.DataFrame, remote: bool) -> None:
    elec = topo.rename(columns={"X": "x", "Y": "y", "Z": "z"}).copy()
    elec.insert(0, "label", np.arange(1, 67).astype(str))
    elec["buried"] = False
    elec["remote"] = False
    if remote:
        elec = pd.concat(
            [
                elec,
                pd.DataFrame(
                    [{"label": "67", "x": 99_999.0, "y": 0.0, "z": 0.0, "buried": False, "remote": False}]
                ),
            ],
            ignore_index=True,
        )
    project.setElec(elec)
    if remote:
        mask = project.elec["label"].astype(str) == "67"
        project.elec.loc[mask, "remote"] = True
        project.surveys[0].elec = project.elec
        project.pinfo["Remote electrodes"] = True
    project.surveys[0].computeK()
    project.surveys[0].df["app"] = (
        pd.to_numeric(project.surveys[0].df["K"], errors="coerce")
        * pd.to_numeric(project.surveys[0].df["resist"], errors="coerce")
    )


def save_pseudosection(project: Project, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))
    project.showPseudo(ax=ax, color_map="turbo")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def stats(project: Project) -> dict:
    df = project.surveys[0].df
    app = pd.to_numeric(df["app"], errors="coerce")
    return {
        "measurements": int(len(df)),
        "finite_positive_apparent_resistivity": int((np.isfinite(app) & (app > 0)).sum()),
        "apparent_resistivity_min_ohm_m": float(app.min()),
        "apparent_resistivity_median_ohm_m": float(app.median()),
        "apparent_resistivity_max_ohm_m": float(app.max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Saída já existe; não será sobrescrita: {output}")
    individual_dir = output / "INDIVIDUAIS"
    combined_dir = output / "COMBINADAS"
    projects_dir = output / "projetos_temporarios"
    individual_dir.mkdir(parents=True)
    combined_dir.mkdir(parents=True)
    projects_dir.mkdir(parents=True)
    summary = {
        "description": "Pseudoseções iniciais dos arquivos originais em BRUTOS, sem QC, corte de contato ou inversão.",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "individual": [],
        "combined": [],
    }

    for line, cfg in LINES.items():
        date_root = root / "02_DADOS_GEOFISICOS" / cfg["folder"]
        topo = load_topography(date_root / cfg["topography"])
        source_paths = []
        combined = None
        for array, filename, remote in cfg["arrays"]:
            source = date_root / "BRUTOS" / filename
            source_paths.append(source)
            project = Project(dirname=str(projects_dir / f"{line}_{array}"), typ="R2")
            project.createSurvey(str(source), ftype="Syscal", debug=False, estMemory=False)
            apply_electrodes(project, topo, remote)
            save_pseudosection(
                project,
                individual_dir / f"{line}_{array}_PSEUDOSECAO_BRUTA_INICIAL.png",
                f"Pseudoseção ERT bruta inicial — {line} {array}",
            )
            summary["individual"].append(
                {"line": line, "array": array, "source": str(source), **stats(project)}
            )
            if combined is None:
                combined = Project(dirname=str(projects_dir / f"{line}_COMBINADA"), typ="R2")
                combined.createSurvey(str(source), ftype="Syscal", debug=False, estMemory=False)
                combined.surveys[0].df["arranjo_origem"] = array
            else:
                before = len(combined.surveys[0].df)
                combined.addData(index=0, fname=str(source), ftype="Syscal")
                combined.surveys[0].df.loc[
                    combined.surveys[0].df["arranjo_origem"].isna(), "arranjo_origem"
                ] = array
                if len(combined.surveys[0].df) <= before:
                    raise RuntimeError(f"Nenhum dado adicionado em {line}-{array}")
        assert combined is not None
        has_remote = any(remote for _, _, remote in cfg["arrays"])
        apply_electrodes(combined, topo, has_remote)
        arrays = "+".join(array for array, _, _ in cfg["arrays"])
        save_pseudosection(
            combined,
            combined_dir / f"{line}_{arrays}_PSEUDOSECAO_BRUTA_INICIAL_COMBINADA.png",
            f"Pseudoseção ERT bruta inicial combinada — {line} {arrays}",
        )
        combined.surveys[0].df.to_csv(
            combined_dir / f"{line}_{arrays}_DADOS_BRUTOS_COMBINADOS.csv", index=False, encoding="utf-8-sig"
        )
        summary["combined"].append(
            {"line": line, "arrays": arrays, "sources": [str(path) for path in source_paths], **stats(combined)}
        )

    (output / "RESUMO_SECOES_BRUTAS.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("SECOES_BRUTAS_CONCLUIDAS")


if __name__ == "__main__":
    main()
