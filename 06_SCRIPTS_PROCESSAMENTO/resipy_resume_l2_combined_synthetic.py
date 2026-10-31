"""Continue only the L2 combined synthetic test after a completed real inversion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd
from resipy import Project

import resipy_combined_quad_synthetic as combined
import resipy_individual_quad_synthetic as base


def metrics_from_real_csv(
    polygon: np.ndarray,
    synthetic: Project,
    real_mesh_csv: Path,
    real_app: np.ndarray,
    synthetic_app: np.ndarray,
) -> dict:
    threshold = base.SYNTHETIC_PARAMETERS["comparison_threshold_ohm_m"]
    path = MplPath(polygon)
    synth_centres, synth_rho = base.mesh_values(synthetic)
    real_df = pd.read_csv(real_mesh_csv)
    real_centres = real_df[["x", "z"]].to_numpy(dtype=float)
    real_rho = pd.to_numeric(real_df["Resistivity(ohm.m)"], errors="coerce").to_numpy()
    true_synth = path.contains_points(synth_centres)
    true_real = path.contains_points(real_centres)
    recovered = synth_rho >= threshold
    intersection = int(np.sum(true_synth & recovered))
    union = int(np.sum(true_synth | recovered))
    local_synth = (
        (synth_centres[:, 0] >= polygon[:, 0].min() - 75.0)
        & (synth_centres[:, 0] <= polygon[:, 0].max() + 75.0)
        & (synth_centres[:, 1] >= polygon[:, 1].min())
    )
    local_real = (
        (real_centres[:, 0] >= polygon[:, 0].min() - 75.0)
        & (real_centres[:, 0] <= polygon[:, 0].max() + 75.0)
        & (real_centres[:, 1] >= polygon[:, 1].min())
    )
    valid = np.isfinite(real_app) & np.isfinite(synthetic_app) & (real_app > 0) & (synthetic_app > 0)
    log_real = np.log10(real_app[valid])
    log_synthetic = np.log10(synthetic_app[valid])
    return {
        "threshold_ohm_m": float(threshold),
        "synthetic_iou": float(intersection / union) if union else float("nan"),
        "synthetic_recall": float(intersection / true_synth.sum()),
        "synthetic_precision": float(intersection / recovered.sum()),
        "synthetic_median_inside_ohm_m": float(np.nanmedian(synth_rho[true_synth])),
        "synthetic_median_local_outside_ohm_m": float(np.nanmedian(synth_rho[local_synth & ~true_synth])),
        "real_median_inside_modelled_cavity_ohm_m": float(np.nanmedian(real_rho[true_real])),
        "real_median_local_outside_ohm_m": float(np.nanmedian(real_rho[local_real & ~true_real])),
        "real_fraction_modelled_cavity_above_threshold": float(np.mean(real_rho[true_real] >= threshold)),
        "log10_apparent_resistivity_pearson_real_vs_synthetic": float(np.corrcoef(log_real, log_synthetic)[0, 1]),
        "log10_apparent_resistivity_rmse_real_vs_synthetic": float(
            np.sqrt(np.mean((log_real - log_synthetic) ** 2))
        ),
        "real_mesh_source": str(real_mesh_csv),
    }


def save_composite(source_case: Path, recovery: Path, output: Path) -> None:
    images = [
        (source_case / "SINTETICO" / "01_modelo_verdadeiro_cut_corners.png", "Modelo sintético verdadeiro"),
        (recovery, "Recuperação do sintético combinado"),
        (source_case / "REAL" / "03_modelo_resistividade_cut_corners.png", "Inversão dos dados reais combinados"),
    ]
    fig, axes = plt.subplots(3, 1, figsize=(14, 15))
    for ax, (path, title) in zip(axes, images):
        ax.imshow(plt.imread(path))
        ax.set_title(title)
        ax.axis("off")
    fig.suptitle("L2 DD+WS+PD — verdadeiro, sintético recuperado e real", fontsize=15)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)
    base.publish_image(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("source_case", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--publish-images", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    source_case = args.source_case.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Saída já existe; não será sobrescrita: {output}")
    output.mkdir(parents=True)
    synthetic_dir = output / "SINTETICO"
    synthetic_dir.mkdir()
    base.configure_image_publisher(root, args.publish_images)

    case = combined.CASES[1]
    date_root = root / "02_DADOS_GEOFISICOS" / case["date_folder"]
    topo = base.load_topography(date_root / case["topography"])
    qc = pd.read_csv(source_case / "REAL" / "dados_combinados_qc.csv")
    sequence = qc[["a", "b", "m", "n"]].to_numpy(copy=True)
    real_app = pd.to_numeric(qc["app"], errors="coerce").to_numpy(copy=True)

    synthetic = Project(dirname=str(synthetic_dir / "projeto_resipy"), typ="R2")
    base.apply_electrodes(synthetic, topo, True)
    remote_validation = combined.validate_remote_electrode_for_synthetic(
        synthetic, case, sequence, synthetic_dir
    )
    base.create_quad_mesh(synthetic, base.SYNTHETIC_PARAMETERS["background_resistivity_ohm_m"])
    polygon, cavity_details = base.cavity_polygon(
        root / "01_PROJETO_DOLINA_MARACANAS" / "01_MODELO_3D" / "dolina_model.npz", "L2"
    )
    synthetic.addRegion(
        polygon,
        res0=base.SYNTHETIC_PARAMETERS["cavity_resistivity_ohm_m"],
        blocky=False,
        fixed=False,
        iplot=False,
    )
    pd.DataFrame(polygon, columns=["distance_m", "elevation_m"]).to_csv(
        synthetic_dir / "poligono_cavidade_na_linha.csv", index=False
    )
    synthetic.exportMesh(str(synthetic_dir / "modelo_verdadeiro.vtk"), _forceLocal=True)
    synthetic.sequence = sequence
    np.random.seed(base.SYNTHETIC_PARAMETERS["random_seed"] + 100)
    messages = []
    base.forward_with_remote_workaround(
        synthetic,
        noise=base.SYNTHETIC_PARAMETERS["gaussian_noise_percent"],
        iplot=False,
        dump=lambda message: messages.append(str(message)),
    )
    (synthetic_dir / "resipy_forward_messages.log").write_text("\n".join(messages), encoding="utf-8")
    synthetic.surveys[0].df.to_csv(
        synthetic_dir / "dados_sinteticos_forward.csv", index=False, encoding="utf-8-sig"
    )
    synthetic.saveForwardModelResult(str(synthetic_dir / "dados_sinteticos_resipy.dat"))
    synthetic_app = pd.to_numeric(synthetic.surveys[0].df["app"], errors="coerce").to_numpy(copy=True)
    synthetic.surveys[0].df["resError"] = (
        pd.to_numeric(synthetic.surveys[0].df["resist"], errors="coerce").abs()
        * base.SYNTHETIC_PARAMETERS["gaussian_noise_percent"]
        / 100.0
    )
    synthetic.err = True
    base.save_pseudo(
        synthetic,
        synthetic_dir / "02_pseudosecao_sintetica_combinada.png",
        "L2 DD+WS+PD — sintético combinado",
    )
    base.reset_to_homogeneous_start(
        synthetic, base.SYNTHETIC_PARAMETERS["background_resistivity_ohm_m"]
    )
    inversion = base.run_inversion(
        synthetic, synthetic_dir, "L2_DD_WS_PD_COMBINADO_SINTETICO_QUAD"
    )
    recovery = synthetic_dir / "03_recuperacao_sintetica_cut_corners.png"
    base.save_results(
        synthetic, recovery, "L2 DD+WS+PD — recuperação sintética combinada"
    )
    real_mesh_csv = next((source_case / "REAL" / "resultado_csv").glob("*.csv"))
    metrics = metrics_from_real_csv(
        polygon, synthetic, real_mesh_csv, real_app, synthetic_app
    )
    comparison = output / "COMPARACAO_VERDADEIRO_SINTETICO_REAL_CUT_CORNERS.png"
    save_composite(source_case, recovery, comparison)
    summary = {
        "case": case,
        "continued_from": str(source_case),
        "remote_electrode_synthetic": remote_validation,
        "measurements": int(len(sequence)),
        "mesh_parameters": base.MESH_PARAMETERS,
        "inversion_parameters": base.INVERSION_PARAMETERS,
        "synthetic_parameters": base.SYNTHETIC_PARAMETERS,
        "cavity_intersection": cavity_details,
        "synthetic_inversion": inversion,
        "comparison_metrics": metrics,
        "cut_corners": True,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    (output / "resumo.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=base.json_default),
        encoding="utf-8",
    )
    (synthetic_dir / "parametros_resipy.json").write_text(
        json.dumps(synthetic.param, indent=2, ensure_ascii=False, default=base.json_default),
        encoding="utf-8",
    )
    print("L2_SINTETICO_COMBINADO_CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
