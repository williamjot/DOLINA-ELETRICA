"""Individual quadrilateral ResIPy inversions and cavity resolution tests.

The workflow keeps each acquisition array independent, applies the documented
40 kOhm contact-resistance cut, uses an explicitly configured quadrilateral
mesh, and runs a ResIPy forward/inverse synthetic test with the exact measured
quadrupoles of each array.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import traceback
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

from resipy import Project


CASES = [
    {
        "id": "L1_DD",
        "line": "L1",
        "array": "DD",
        "date_folder": "20262210",
        "data": "20262210_DD_FILTRADO.bin",
        "topography": "Linha01_Dolina_10m.xlsx",
        "remote": False,
    },
    {
        "id": "L1_WS",
        "line": "L1",
        "array": "WS",
        "date_folder": "20262210",
        "data": "20262210_WS_FILTRADO.bin",
        "topography": "Linha01_Dolina_10m.xlsx",
        "remote": False,
    },
    {
        "id": "L2_DD",
        "line": "L2",
        "array": "DD",
        "date_folder": "20262410",
        "data": "20262410_DD_FILTRADO.bin",
        "topography": "Linha02_Dolina_10m.xlsx",
        "remote": False,
    },
    {
        "id": "L2_WS",
        "line": "L2",
        "array": "WS",
        "date_folder": "20262410",
        "data": "20262410_WS_FILTRADO.bin",
        "topography": "Linha02_Dolina_10m.xlsx",
        "remote": False,
    },
    {
        "id": "L2_PD",
        "line": "L2",
        "array": "PD",
        "date_folder": "20262410",
        "data": "20262410_PD_FILTRADO_RESIPY.bin",
        "topography": "Linha02_Dolina_10m.xlsx",
        "remote": True,
    },
]

MESH_PARAMETERS = {
    "typ": "quad",
    "fmd": 120.0,
    "elemx": 4,
    "xgf": 1.5,
    "zf": 1.1,
    "zgf": 1.5,
    "pad": 8,
}

INVERSION_PARAMETERS = {
    "data_type": 1,
    "inverse_type": 1,
    "reg_mode": 0,
    "alpha_aniso": 1.0,
    "alpha_s": 10.0,
    "max_iter": 10,
    "tolerance": 1.0,
    "error_mod": 2,
    "min_error": 0.01,
    "a_wgt": 0.0,
    "b_wgt": 0.0,
    "rho_min": 1.0,
    "rho_max": 1_000_000.0,
}

SYNTHETIC_PARAMETERS = {
    "background_resistivity_ohm_m": 5_000.0,
    "cavity_resistivity_ohm_m": 50_000.0,
    "gaussian_noise_percent": 3.0,
    "random_seed": 20_261_030,
    "comparison_threshold_ohm_m": math.sqrt(5_000.0 * 50_000.0),
}

PLOT_VMIN_LOG10 = math.log10(200.0)
PLOT_VMAX_LOG10 = math.log10(100_000.0)

IMAGE_PUBLISHER = None


class GitImagePublisher:
    """Commit and push exactly one exported image at a time."""

    def __init__(self, root: Path, remote: str = "origin", branch: str = "main") -> None:
        self.root = root.resolve()
        self.remote = remote
        self.branch = branch

    def publish(self, path: Path) -> None:
        path = path.resolve()
        relative = path.relative_to(self.root)
        subprocess.run(
            ["git", "-C", str(self.root), "add", "--", str(relative)],
            check=True,
        )
        changed = subprocess.run(
            ["git", "-C", str(self.root), "diff", "--cached", "--quiet", "--", str(relative)],
            check=False,
        ).returncode
        if changed == 0:
            print(f"[git] imagem sem alteração: {relative}", flush=True)
            return
        message = f"Adiciona figura {relative.as_posix()}"
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", message, "--", str(relative)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "push", self.remote, self.branch],
            check=True,
        )
        print(f"[git] imagem publicada: {relative}", flush=True)


def configure_image_publisher(root: Path, enabled: bool) -> None:
    global IMAGE_PUBLISHER
    IMAGE_PUBLISHER = GitImagePublisher(root) if enabled else None


def publish_image(path: Path) -> None:
    if IMAGE_PUBLISHER is not None:
        IMAGE_PUBLISHER.publish(path)


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    return str(value)


def load_topography(path: Path) -> pd.DataFrame:
    topo = pd.read_excel(path)[["X", "Y", "Z"]].apply(pd.to_numeric, errors="raise").astype(float)
    if len(topo) != 66:
        raise ValueError(f"Esperados 66 eletrodos em {path}; encontrados {len(topo)}")
    if topo.isna().any().any() or not np.all(np.diff(topo["X"]) > 0):
        raise ValueError(f"Topografia ausente, inválida ou não crescente: {path}")
    return topo


def build_electrodes(topo: pd.DataFrame, remote: bool) -> pd.DataFrame:
    elec = topo.rename(columns={"X": "x", "Y": "y", "Z": "z"}).copy()
    elec.insert(0, "label", np.arange(1, len(elec) + 1).astype(str))
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
    return elec


def apply_electrodes(project: Project, topo: pd.DataFrame, remote: bool) -> None:
    project.setElec(build_electrodes(topo, remote))
    if remote:
        remote_mask = project.elec["label"].astype(str) == "67"
        project.elec.loc[remote_mask, "remote"] = True
        if project.surveys:
            project.surveys[0].elec = project.elec
        project.pinfo["Remote electrodes"] = True
    project.fmd = MESH_PARAMETERS["fmd"]


def apply_qc(project: Project, contact_max_ohm: float, output: Path) -> dict:
    survey = project.surveys[0]
    survey.computeK()
    survey.df["app"] = pd.to_numeric(survey.df["K"], errors="coerce") * pd.to_numeric(
        survey.df["resist"], errors="coerce"
    )
    before = survey.df.copy()
    app = pd.to_numeric(before["app"], errors="coerce")
    resist = pd.to_numeric(before["resist"], errors="coerce")
    basic_keep = np.isfinite(app) & np.isfinite(resist) & (app > 0) & (resist != 0)
    invalid = before.loc[~basic_keep].copy()
    if len(invalid):
        invalid.to_csv(output / "dados_removidos_qc_basico.csv", index=False, encoding="utf-8-sig")
        survey.filterData(basic_keep)

    contact = pd.to_numeric(survey.df["cR"], errors="coerce")
    if contact.isna().any():
        raise ValueError("A coluna cR contém valores ausentes; o corte de contato não é auditável.")
    contact_remove = contact.abs() > contact_max_ohm
    removed_contact = survey.df.loc[contact_remove].copy()
    removed_contact.insert(0, "motivo_exclusao", f"abs(cR) > {contact_max_ohm:g} ohm")
    removed_contact.to_csv(output / "dados_removidos_contato_40k.csv", index=False, encoding="utf-8-sig")
    removed_reported = survey.filterContRes(vmax=contact_max_ohm, debug=True)
    if removed_reported != int(contact_remove.sum()):
        raise RuntimeError("A contagem independente do corte de contato divergiu do ResIPy.")

    if "magErr" in survey.df:
        survey.df["resError"] = pd.to_numeric(survey.df["magErr"], errors="coerce")
        project.err = bool(survey.df["resError"].notna().all())
    else:
        project.err = False

    cols = [c for c in ["a", "b", "m", "n", "resist", "app", "magErr", "resError", "cR"] if c in survey.df]
    survey.df[cols].to_csv(output / "dados_reais_qc.csv", index=False, encoding="utf-8-sig")
    project.elec.to_csv(output / "eletrodos_aplicados.csv", index=False, encoding="utf-8-sig")
    return {
        "measurements_imported": int(len(before)),
        "measurements_removed_basic_qc": int((~basic_keep).sum()),
        "measurements_removed_contact": int(contact_remove.sum()),
        "measurements_inverted": int(len(survey.df)),
        "instrument_error_used": bool(project.err),
        "contact_max_ohm": float(contact_max_ohm),
    }


def configure_inversion(project: Project) -> None:
    project.param.update(INVERSION_PARAMETERS)


def create_quad_mesh(project: Project, background: float) -> None:
    kwargs = {k: v for k, v in MESH_PARAMETERS.items() if k not in {"typ"}}
    project.createMesh(typ="quad", res0=background, show_output=False, **kwargs)
    configure_inversion(project)


def save_pseudo(project: Project, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))
    project.showPseudo(ax=ax)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    publish_image(path)


def save_mesh(project: Project, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))
    project.showMesh(ax=ax)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    publish_image(path)


def save_results(project: Project, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))
    project.showResults(
        ax=ax,
        sens=False,
        color_map="turbo",
        edge_color="none",
        clipCorners=True,
        cropMaxDepth=True,
        clipContour=True,
        vmin=PLOT_VMIN_LOG10,
        vmax=PLOT_VMAX_LOG10,
    )
    ax.set_title(title + " — Cut Corners")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    publish_image(path)


def save_true_model(project: Project, true_resistivity: np.ndarray, path: Path, title: str) -> None:
    attr = "True Resistivity(log10)"
    project.mesh.df[attr] = np.log10(true_resistivity)
    fig, ax = plt.subplots(figsize=(13, 5.5))
    project.mesh.show(
        ax=ax,
        attr=attr,
        color_map="turbo",
        edge_color="none",
        vmin=PLOT_VMIN_LOG10,
        vmax=PLOT_VMAX_LOG10,
        zlim=project.zlim,
    )
    project._clipContour(ax, project.mesh.cax, cropMaxDepth=True, clipCorners=True)
    ax.set_title(title + " — Cut Corners")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    publish_image(path)


def run_inversion(project: Project, output: Path, label: str) -> dict:
    messages: list[str] = []
    project.setTitle(label)
    project.invert(iplot=False, dump=lambda message: messages.append(str(message)))
    (output / "resipy_inversion_messages.log").write_text("\n".join(messages), encoding="utf-8")
    invdir = Path(project.dirname) / "invdir"
    if (invdir / "R2.out").exists():
        shutil.copy2(invdir / "R2.out", output / "R2.out")
    try:
        history = project.getR2out()
        history.to_csv(output / "historico_iteracoes.csv", index=False)
    except Exception:
        history = pd.DataFrame()
    project.exportMeshResults(dirname=str(output / "resultado_csv"), ftype=".csv", _forceLocal=True)
    project.exportMeshResults(dirname=str(output / "resultado_vtk"), ftype=".vtk", _forceLocal=True)
    project.saveProject(str(output / f"{label}.resipy"))
    return {
        "project_summary": dict(project.pinfo),
        "mesh_elements": int(project.pinfo.get("Number of Elements", 0)),
        "mesh_nodes": int(project.pinfo.get("Number of Nodes", 0)),
        "rms": project.pinfo.get("RMS of inverse solution"),
        "iterations": project.pinfo.get("Number of iterations"),
        "converged": project.pinfo.get("Convergence of inverse solution"),
    }


def cavity_polygon(model_path: Path, line: str) -> tuple[np.ndarray, dict]:
    model = np.load(model_path, allow_pickle=False)
    metadata = json.loads(str(model["metadata_json"]))
    station = model[f"{line}_station_m"].astype(float)
    xyz = model[f"{line}_xyz_utm"].astype(float)
    dense_station = np.linspace(float(station.min()), float(station.max()), 2601)
    x = np.interp(dense_station, station, xyz[:, 0])
    y = np.interp(dense_station, station, xyz[:, 1])
    center_x = float(metadata["center_easting_m"])
    center_y = float(metadata["center_northing_m"])
    dx, dy = x - center_x, y - center_y
    alpha = math.radians(90.0 - float(metadata["major_axis_azimuth_deg_from_north"]))
    ca, sa = math.cos(alpha), math.sin(alpha)
    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca
    a = float(metadata["major_diameter_m"]) / 2.0
    b = float(metadata["minor_diameter_m"]) / 2.0
    radial = np.sqrt((u / a) ** 2 + (v / b) ** 2)
    theta = np.arctan2(v / b, u / a)
    roughness = float(metadata["angular_roughness_fraction"])
    angular = 1.0 + roughness * np.sin(3.0 * theta + 0.35) + 0.6 * roughness * np.sin(7.0 * theta - 1.10)
    shape = PchipInterpolator(
        np.asarray(metadata["wall_depth_fraction"], dtype=float),
        np.asarray(metadata["wall_radius_factor"], dtype=float),
    )
    plane = metadata["topography_plane"]

    left, right = [], []
    for fraction in np.linspace(0.0, 1.0, 241):
        inside = radial <= float(shape(fraction)) * angular
        indices = np.flatnonzero(inside)
        if len(indices) == 0:
            continue
        groups = np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)
        group = max(groups, key=len)
        li, ri = int(group[0]), int(group[-1])
        for index, target in [(li, left), (ri, right)]:
            elevation = (
                float(plane["z0_m"])
                + float(plane["dz_dx"]) * (x[index] - center_x)
                + float(plane["dz_dy"]) * (y[index] - center_y)
                - fraction * float(metadata["depth_m"])
            )
            target.append([dense_station[index], elevation])
    if len(left) < 3:
        raise RuntimeError(f"O modelo de cavidade não intercepta suficientemente a linha {line}.")
    polygon = np.vstack([np.asarray(left), np.asarray(right)[::-1], np.asarray(left[:1])])
    details = {
        "line": line,
        "vertices": int(len(polygon)),
        "station_min_m": float(polygon[:, 0].min()),
        "station_max_m": float(polygon[:, 0].max()),
        "elevation_min_m": float(polygon[:, 1].min()),
        "elevation_max_m": float(polygon[:, 1].max()),
        "intersection_depth_m": float(polygon[:, 1].max() - polygon[:, 1].min()),
        "source_model": str(model_path),
        "model_interpretation": metadata.get("interpretation"),
    }
    return polygon, details


def reset_to_homogeneous_start(project: Project, background: float) -> None:
    count = project.mesh.numel
    project.mesh.df["res0"] = np.full(count, background)
    project.mesh.df["region"] = np.ones(count, dtype=int)
    project.mesh.df["zones"] = np.ones(count, dtype=int)
    project.mesh.df["param"] = np.arange(1, count + 1)
    project.param["num_regions"] = 0
    project.param.pop("regions", None)
    # ResIPy otherwise forces every non-fixed cell to 100 ohm.m and prepends
    # the true forward model to meshResults. The forward response is already
    # saved, so clear this state before a genuinely homogeneous reinversion.
    project.iForward = False
    configure_inversion(project)


def mesh_values(project: Project) -> tuple[np.ndarray, np.ndarray]:
    mesh = project.meshResults[0]
    centres = mesh.elmCentre[:, [0, 2]]
    resistivity = pd.to_numeric(mesh.df["Resistivity(ohm.m)"], errors="coerce").to_numpy()
    return centres, resistivity


def compare_metrics(
    polygon: np.ndarray,
    synthetic: Project,
    real: Project,
    real_app: np.ndarray,
    synthetic_app: np.ndarray,
) -> dict:
    threshold = SYNTHETIC_PARAMETERS["comparison_threshold_ohm_m"]
    path = MplPath(polygon)
    synth_centres, synth_rho = mesh_values(synthetic)
    real_centres, real_rho = mesh_values(real)
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
    valid_pair = np.isfinite(real_app) & np.isfinite(synthetic_app) & (real_app > 0) & (synthetic_app > 0)
    if valid_pair.sum() > 1:
        log_real = np.log10(real_app[valid_pair])
        log_synth = np.log10(synthetic_app[valid_pair])
        pearson = float(np.corrcoef(log_real, log_synth)[0, 1])
        log_rmse = float(np.sqrt(np.mean((log_real - log_synth) ** 2)))
    else:
        pearson, log_rmse = float("nan"), float("nan")
    return {
        "threshold_ohm_m": float(threshold),
        "synthetic_iou": float(intersection / union) if union else float("nan"),
        "synthetic_recall": float(intersection / true_synth.sum()) if true_synth.any() else float("nan"),
        "synthetic_precision": float(intersection / recovered.sum()) if recovered.any() else float("nan"),
        "synthetic_median_inside_ohm_m": float(np.nanmedian(synth_rho[true_synth])),
        "synthetic_median_local_outside_ohm_m": float(np.nanmedian(synth_rho[local_synth & ~true_synth])),
        "real_median_inside_modelled_cavity_ohm_m": float(np.nanmedian(real_rho[true_real])),
        "real_median_local_outside_ohm_m": float(np.nanmedian(real_rho[local_real & ~true_real])),
        "real_fraction_modelled_cavity_above_threshold": float(np.mean(real_rho[true_real] >= threshold)),
        "log10_apparent_resistivity_pearson_real_vs_synthetic": pearson,
        "log10_apparent_resistivity_rmse_real_vs_synthetic": log_rmse,
    }


def save_comparison(real: Project, synthetic: Project, true_mesh, output: Path, title: str) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(13, 14), sharex=True)
    true_mesh.show(
        ax=axes[0],
        attr="True Resistivity(log10)",
        color_map="turbo",
        edge_color="none",
        vmin=PLOT_VMIN_LOG10,
        vmax=PLOT_VMAX_LOG10,
        zlim=real.zlim,
    )
    real._clipContour(axes[0], true_mesh.cax, cropMaxDepth=True, clipCorners=True)
    axes[0].set_title("Modelo sintético verdadeiro — Cut Corners")
    synthetic.showResults(
        ax=axes[1], sens=False, color_map="turbo", edge_color="none", clipCorners=True,
        cropMaxDepth=True, clipContour=True, vmin=PLOT_VMIN_LOG10, vmax=PLOT_VMAX_LOG10,
    )
    axes[1].set_title("Recuperação do sintético — Cut Corners")
    real.showResults(
        ax=axes[2], sens=False, color_map="turbo", edge_color="none", clipCorners=True,
        cropMaxDepth=True, clipContour=True, vmin=PLOT_VMIN_LOG10, vmax=PLOT_VMAX_LOG10,
    )
    axes[2].set_title("Inversão dos dados reais — Cut Corners")
    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    fig.savefig(output, dpi=220)
    plt.close(fig)
    publish_image(output)


def process_case(root: Path, output_root: Path, case: dict, contact_max_ohm: float) -> dict:
    case_dir = output_root / case["id"]
    real_dir = case_dir / "REAL"
    synthetic_dir = case_dir / "SINTETICO"
    real_dir.mkdir(parents=True)
    synthetic_dir.mkdir(parents=True)
    date_root = root / "02_DADOS_GEOFISICOS" / case["date_folder"]
    data_path = date_root / "FILTRADOS" / case["data"]
    topo_path = date_root / case["topography"]
    topo = load_topography(topo_path)
    topo.to_csv(case_dir / "topografia_xyz.csv", index=False, float_format="%.6f")

    print(f"[{case['id']}] importando e auditando dados reais", flush=True)
    real = Project(dirname=str(real_dir / "projeto_resipy"), typ="R2")
    real.createSurvey(str(data_path), ftype="Syscal", debug=False, estMemory=False)
    apply_electrodes(real, topo, case["remote"])
    qc = apply_qc(real, contact_max_ohm, real_dir)
    real_app = pd.to_numeric(real.surveys[0].df["app"], errors="coerce").to_numpy(copy=True)
    real_sequence = real.surveys[0].df[["a", "b", "m", "n"]].to_numpy(copy=True)
    save_pseudo(real, real_dir / "01_pseudosecao_observada.png", f"{case['id']} — observado")

    print(f"[{case['id']}] criando malha quadrilateral e iniciando inversão real", flush=True)
    create_quad_mesh(real, SYNTHETIC_PARAMETERS["background_resistivity_ohm_m"])
    save_mesh(real, real_dir / "02_malha_quadrilateral.png", f"{case['id']} — malha quadrilateral")
    real.exportMesh(str(real_dir / "malha_quadrilateral.vtk"), _forceLocal=True)
    real_summary = run_inversion(real, real_dir, f"{case['id']}_REAL_QUAD")
    save_results(real, real_dir / "03_modelo_resistividade_cut_corners.png", f"{case['id']} — real")

    polygon, cavity_details = cavity_polygon(
        root / "01_PROJETO_DOLINA_MARACANAS" / "01_MODELO_3D" / "dolina_model.npz", case["line"]
    )
    pd.DataFrame(polygon, columns=["distance_m", "elevation_m"]).to_csv(
        synthetic_dir / "poligono_cavidade_na_linha.csv", index=False
    )

    print(f"[{case['id']}] criando dado sintético no ResIPy com os quadrupolos reais", flush=True)
    synthetic = Project(dirname=str(synthetic_dir / "projeto_resipy"), typ="R2")
    apply_electrodes(synthetic, topo, case["remote"])
    create_quad_mesh(synthetic, SYNTHETIC_PARAMETERS["background_resistivity_ohm_m"])
    synthetic.addRegion(
        polygon,
        res0=SYNTHETIC_PARAMETERS["cavity_resistivity_ohm_m"],
        blocky=False,
        fixed=False,
        iplot=False,
    )
    true_resistivity = pd.to_numeric(synthetic.mesh.df["res0"], errors="coerce").to_numpy(copy=True)
    synthetic.mesh.df["True Resistivity(log10)"] = np.log10(true_resistivity)
    true_mesh = synthetic.mesh.copy()
    save_true_model(
        synthetic,
        true_resistivity,
        synthetic_dir / "01_modelo_verdadeiro_cut_corners.png",
        f"{case['id']} — modelo verdadeiro",
    )
    synthetic.exportMesh(str(synthetic_dir / "modelo_verdadeiro.vtk"), _forceLocal=True)
    synthetic.sequence = real_sequence.copy()
    np.random.seed(SYNTHETIC_PARAMETERS["random_seed"] + CASES.index(case))
    forward_messages: list[str] = []
    synthetic.forward(
        noise=SYNTHETIC_PARAMETERS["gaussian_noise_percent"],
        iplot=False,
        dump=lambda message: forward_messages.append(str(message)),
    )
    (synthetic_dir / "resipy_forward_messages.log").write_text("\n".join(forward_messages), encoding="utf-8")
    synthetic.surveys[0].df.to_csv(synthetic_dir / "dados_sinteticos_forward.csv", index=False, encoding="utf-8-sig")
    synthetic.saveForwardModelResult(str(synthetic_dir / "dados_sinteticos_resipy.dat"))
    synthetic_app = pd.to_numeric(synthetic.surveys[0].df["app"], errors="coerce").to_numpy(copy=True)
    synthetic.surveys[0].df["resError"] = (
        pd.to_numeric(synthetic.surveys[0].df["resist"], errors="coerce").abs()
        * SYNTHETIC_PARAMETERS["gaussian_noise_percent"]
        / 100.0
    )
    synthetic.err = True
    save_pseudo(synthetic, synthetic_dir / "02_pseudosecao_sintetica.png", f"{case['id']} — sintético")

    print(f"[{case['id']}] invertendo dado sintético a partir de modelo homogêneo", flush=True)
    reset_to_homogeneous_start(synthetic, SYNTHETIC_PARAMETERS["background_resistivity_ohm_m"])
    synthetic_summary = run_inversion(synthetic, synthetic_dir, f"{case['id']}_SINTETICO_QUAD")
    save_results(
        synthetic,
        synthetic_dir / "03_recuperacao_sintetica_cut_corners.png",
        f"{case['id']} — recuperação sintética",
    )
    metrics = compare_metrics(polygon, synthetic, real, real_app, synthetic_app)
    save_comparison(
        real,
        synthetic,
        true_mesh,
        case_dir / "COMPARACAO_VERDADEIRO_SINTETICO_REAL_CUT_CORNERS.png",
        f"{case['id']} — cavidade paramétrica versus dados reais",
    )

    summary = {
        "case": case,
        "source_data": str(data_path),
        "topography": str(topo_path),
        "qc": qc,
        "mesh_parameters": MESH_PARAMETERS,
        "inversion_parameters": INVERSION_PARAMETERS,
        "synthetic_parameters": SYNTHETIC_PARAMETERS,
        "cavity_intersection": cavity_details,
        "real_inversion": real_summary,
        "synthetic_inversion": synthetic_summary,
        "comparison_metrics": metrics,
        "cut_corners": True,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    (case_dir / "resumo.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8"
    )
    (real_dir / "parametros_resipy.json").write_text(
        json.dumps(real.param, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8"
    )
    (synthetic_dir / "parametros_resipy.json").write_text(
        json.dumps(synthetic.param, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8"
    )
    print(f"[{case['id']}] concluído", flush=True)
    return summary


def write_method_report(output_root: Path, summaries: list[dict], failures: list[dict]) -> None:
    lines = [
        "# Inversões individuais quadrilaterais e teste sintético de cavidade",
        "",
        f"Execução: {datetime.now().isoformat(timespec='seconds')}",
        f"ResIPy: {version('resipy')}",
        f"Pandas: {version('pandas')}",
        "",
        "## Parâmetros comuns",
        "",
        f"- Malha: quadrilateral; FMD={MESH_PARAMETERS['fmd']} m; elemx={MESH_PARAMETERS['elemx']}; "
        f"xgf={MESH_PARAMETERS['xgf']}; zf={MESH_PARAMETERS['zf']}; zgf={MESH_PARAMETERS['zgf']}; pad={MESH_PARAMETERS['pad']}.",
        f"- Inversão: log-resistividade; L2 suave; isotrópica; até {INVERSION_PARAMETERS['max_iter']} iterações; "
        f"tolerância={INVERSION_PARAMETERS['tolerance']}%; erro individual com piso de {100*INVERSION_PARAMETERS['min_error']:.1f}%.",
        f"- Limites de resistividade: {INVERSION_PARAMETERS['rho_min']:g} a {INVERSION_PARAMETERS['rho_max']:g} ohm.m.",
        f"- Sintético: fundo={SYNTHETIC_PARAMETERS['background_resistivity_ohm_m']:g} ohm.m; "
        f"cavidade={SYNTHETIC_PARAMETERS['cavity_resistivity_ohm_m']:g} ohm.m; "
        f"ruído gaussiano={SYNTHETIC_PARAMETERS['gaussian_noise_percent']}%.",
        "- Todas as seções invertidas usam `clipCorners=True` (Cut Corners).",
        "",
        "## Justificativa",
        "",
        "- FMD de 120 m cobre os 105 m do modelo paramétrico com margem e mantém comparação uniforme entre arranjos.",
        "- Quatro subdivisões por intervalo de 10 m fornecem células horizontais próximas de 2,5 m sem custo excessivo.",
        "- O padding de 8 células (duas vezes `elemx`) reduz influência das fronteiras laterais.",
        "- A inversão L2 suave é a hipótese mínima para cobertura inconsolidada/rocha alterada sem impor contatos abruptos não demonstrados.",
        "- A isotropia evita introduzir direção preferencial sem informação geológica independente.",
        "- O piso de erro de 1% impede que leituras com erro instrumental igual a zero recebam peso infinito.",
        "- O contraste sintético 10:1 é conservador para uma cavidade resistiva e permanece dentro da faixa observada nas inversões existentes.",
        "- O ruído de 3% testa detectabilidade em condição não ideal; a semente fixa torna o ensaio reproduzível.",
        "- A sequência sintética é exatamente a sequência real após QC de cada arranjo, evitando vantagem de cobertura artificial.",
        "",
        "## Resultados",
        "",
    ]
    for item in summaries:
        metrics = item["comparison_metrics"]
        lines.extend(
            [
                f"### {item['case']['id']}",
                "",
                f"- Medições reais invertidas: {item['qc']['measurements_inverted']}.",
                f"- RMS real: {item['real_inversion']['rms']}; iterações: {item['real_inversion']['iterations']}.",
                f"- RMS sintético: {item['synthetic_inversion']['rms']}; iterações: {item['synthetic_inversion']['iterations']}.",
                f"- IoU sintético: {metrics['synthetic_iou']:.3f}; recall: {metrics['synthetic_recall']:.3f}; precisão: {metrics['synthetic_precision']:.3f}.",
                f"- Correlação log10(ρa) real–sintético: {metrics['log10_apparent_resistivity_pearson_real_vs_synthetic']:.3f}.",
                f"- Mediana real dentro/fora da cavidade modelada: {metrics['real_median_inside_modelled_cavity_ohm_m']:.0f} / {metrics['real_median_local_outside_ohm_m']:.0f} ohm.m.",
                "",
            ]
        )
    if failures:
        lines.extend(["## Falhas", ""])
        lines.extend([f"- {failure['case']}: {failure['error']}" for failure in failures])
        lines.append("")
    (output_root / "RELATORIO_METODO_E_RESULTADOS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--contact-max-ohm", type=float, default=40_000.0)
    parser.add_argument("--cases", nargs="*", choices=[case["id"] for case in CASES])
    parser.add_argument(
        "--publish-images",
        action="store_true",
        help="Cria um commit e faz push imediatamente após cada PNG exportado.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    configure_image_publisher(root, args.publish_images)
    if output.exists():
        raise FileExistsError(f"Saída já existe; não será sobrescrita: {output}")
    output.mkdir(parents=True)
    selected = CASES if not args.cases else [case for case in CASES if case["id"] in args.cases]
    run_metadata = {
        "resipy_version": version("resipy"),
        "pandas_version": version("pandas"),
        "numpy_version": version("numpy"),
        "mesh_parameters": MESH_PARAMETERS,
        "inversion_parameters": INVERSION_PARAMETERS,
        "synthetic_parameters": SYNTHETIC_PARAMETERS,
        "contact_max_ohm": args.contact_max_ohm,
        "cases": [case["id"] for case in selected],
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    (output / "PARAMETROS_USADOS.json").write_text(
        json.dumps(run_metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    summaries, failures = [], []
    for case in selected:
        try:
            summaries.append(process_case(root, output, case, args.contact_max_ohm))
        except Exception as exc:
            failures.append(
                {"case": case["id"], "error": repr(exc), "traceback": traceback.format_exc()}
            )
            print(f"[{case['id']}] FALHOU: {exc!r}", flush=True)
    (output / "RESUMO_GERAL.json").write_text(
        json.dumps({"success": summaries, "failures": failures}, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )
    write_method_report(output, summaries, failures)
    if failures:
        raise RuntimeError(f"{len(failures)} caso(s) falharam; consulte RESUMO_GERAL.json")
    print("TODOS_OS_CASOS_CONCLUIDOS", flush=True)


if __name__ == "__main__":
    main()
