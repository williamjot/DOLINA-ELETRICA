"""Combined-array quadrilateral ResIPy inversions and cavity resolution tests.

The two profiles are processed independently. L1 combines DD+WS; L2 combines
DD+WS+PD. The PD current electrode labelled 67 is explicitly represented as a
remote electrode (electrode at infinity) in both the measured and synthetic
projects.
"""

from __future__ import annotations

import argparse
import json
import traceback
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from resipy import Project

import resipy_individual_quad_synthetic as base


CASES = [
    {
        "id": "L1_DD_WS_COMBINADO",
        "line": "L1",
        "date_folder": "20262210",
        "topography": "Linha01_Dolina_10m.xlsx",
        "arrays": [
            ("DD", "20262210_DD_FILTRADO.bin"),
            ("WS", "20262210_WS_FILTRADO.bin"),
        ],
        "remote": False,
    },
    {
        "id": "L2_DD_WS_PD_COMBINADO",
        "line": "L2",
        "date_folder": "20262410",
        "topography": "Linha02_Dolina_10m.xlsx",
        "arrays": [
            ("DD", "20262410_DD_FILTRADO.bin"),
            ("WS", "20262410_WS_FILTRADO.bin"),
            ("PD", "20262410_PD_FILTRADO_RESIPY.bin"),
        ],
        "remote": True,
    },
]


def add_array(project: Project, path: Path, name: str) -> int:
    survey = project.surveys[0]
    before = len(survey.df)
    project.addData(index=0, fname=str(path), ftype="Syscal")
    survey = project.surveys[0]
    if "arranjo_origem" not in survey.df:
        survey.df["arranjo_origem"] = pd.NA
    column = survey.df.columns.get_loc("arranjo_origem")
    survey.df.iloc[before:, column] = name
    return len(survey.df) - before


def import_arrays(root: Path, case: dict, project_dir: Path) -> tuple[Project, pd.DataFrame, dict, list[str]]:
    date_root = root / "02_DADOS_GEOFISICOS" / case["date_folder"]
    filtered = date_root / "FILTRADOS"
    topo = base.load_topography(date_root / case["topography"])
    first_name, first_file = case["arrays"][0]
    first_path = filtered / first_file
    project = Project(dirname=str(project_dir), typ="R2")
    project.createSurvey(str(first_path), ftype="Syscal", debug=False, estMemory=False)
    project.surveys[0].df["arranjo_origem"] = first_name
    counts = {first_name: int(len(project.surveys[0].df))}
    sources = [str(first_path)]
    for name, filename in case["arrays"][1:]:
        path = filtered / filename
        counts[name] = add_array(project, path, name)
        sources.append(str(path))
    base.apply_electrodes(project, topo, case["remote"])
    return project, topo, counts, sources


def validate_remote_electrode(project: Project, case: dict, output: Path) -> dict:
    if not case["remote"]:
        result = {"required": False, "valid": True, "reason": "perfil sem polo-dipolo"}
    else:
        survey = project.surveys[0]
        pd_rows = survey.df.loc[survey.df["arranjo_origem"].astype(str) == "PD"]
        remote_rows = project.elec.loc[project.elec["remote"].astype(bool)]
        labels = sorted(pd_rows["a"].astype(str).unique().tolist())
        valid = (
            len(pd_rows) > 0
            and labels == ["67"]
            and len(remote_rows) == 1
            and str(remote_rows.iloc[0]["label"]) == "67"
        )
        result = {
            "required": True,
            "valid": bool(valid),
            "pd_measurements": int(len(pd_rows)),
            "pd_current_electrode_a_labels": labels,
            "remote_electrode_count": int(len(remote_rows)),
            "remote_label": str(remote_rows.iloc[0]["label"]) if len(remote_rows) else None,
            "representation": "ResIPy remote=True; R2 escreve o eletrodo 67 como remoto/infinito",
        }
        if not valid:
            raise RuntimeError(f"Validação do eletrodo remoto falhou: {result}")
    (output / "validacao_eletrodo_infinito.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def process_case(root: Path, output_root: Path, case: dict, contact_max_ohm: float, seed_offset: int) -> dict:
    case_dir = output_root / case["id"]
    real_dir = case_dir / "REAL"
    synthetic_dir = case_dir / "SINTETICO"
    real_dir.mkdir(parents=True)
    synthetic_dir.mkdir(parents=True)

    print(f"[{case['id']}] importando arranjos", flush=True)
    real, topo, source_counts, source_files = import_arrays(
        root, case, real_dir / "projeto_resipy"
    )
    topo.to_csv(case_dir / "topografia_xyz.csv", index=False, float_format="%.6f")
    remote_validation = validate_remote_electrode(real, case, real_dir)
    qc = base.apply_qc(real, contact_max_ohm, real_dir)
    qc_columns = [
        column
        for column in [
            "arranjo_origem", "a", "b", "m", "n", "resist", "app",
            "magErr", "resError", "cR",
        ]
        if column in real.surveys[0].df
    ]
    real.surveys[0].df[qc_columns].to_csv(
        real_dir / "dados_combinados_qc.csv", index=False, encoding="utf-8-sig"
    )
    after_qc = (
        real.surveys[0].df["arranjo_origem"].astype(str).value_counts().sort_index().to_dict()
    )
    real_app = pd.to_numeric(real.surveys[0].df["app"], errors="coerce").to_numpy(copy=True)
    sequence = real.surveys[0].df[["a", "b", "m", "n"]].to_numpy(copy=True)
    base.save_pseudo(
        real,
        real_dir / "01_pseudosecao_observada_combinada.png",
        f"{case['id']} — observado combinado",
    )

    print(f"[{case['id']}] malha quadrilateral e inversão real", flush=True)
    base.create_quad_mesh(real, base.SYNTHETIC_PARAMETERS["background_resistivity_ohm_m"])
    base.save_mesh(
        real,
        real_dir / "02_malha_quadrilateral.png",
        f"{case['id']} — malha quadrilateral",
    )
    real.exportMesh(str(real_dir / "malha_quadrilateral.vtk"), _forceLocal=True)
    real_summary = base.run_inversion(real, real_dir, f"{case['id']}_REAL_QUAD")
    base.save_results(
        real,
        real_dir / "03_modelo_resistividade_cut_corners.png",
        f"{case['id']} — real combinado",
    )

    polygon, cavity_details = base.cavity_polygon(
        root / "01_PROJETO_DOLINA_MARACANAS" / "01_MODELO_3D" / "dolina_model.npz",
        case["line"],
    )
    pd.DataFrame(polygon, columns=["distance_m", "elevation_m"]).to_csv(
        synthetic_dir / "poligono_cavidade_na_linha.csv", index=False
    )

    print(f"[{case['id']}] forward e inversão sintética combinada", flush=True)
    synthetic = Project(dirname=str(synthetic_dir / "projeto_resipy"), typ="R2")
    base.apply_electrodes(synthetic, topo, case["remote"])
    synthetic_remote_validation = validate_remote_electrode_for_synthetic(
        synthetic, case, sequence, synthetic_dir
    )
    base.create_quad_mesh(synthetic, base.SYNTHETIC_PARAMETERS["background_resistivity_ohm_m"])
    synthetic.addRegion(
        polygon,
        res0=base.SYNTHETIC_PARAMETERS["cavity_resistivity_ohm_m"],
        blocky=False,
        fixed=False,
        iplot=False,
    )
    true_resistivity = pd.to_numeric(synthetic.mesh.df["res0"], errors="coerce").to_numpy(copy=True)
    synthetic.mesh.df["True Resistivity(log10)"] = np.log10(true_resistivity)
    true_mesh = synthetic.mesh.copy()
    base.save_true_model(
        synthetic,
        true_resistivity,
        synthetic_dir / "01_modelo_verdadeiro_cut_corners.png",
        f"{case['id']} — modelo verdadeiro",
    )
    synthetic.exportMesh(str(synthetic_dir / "modelo_verdadeiro.vtk"), _forceLocal=True)
    synthetic.sequence = sequence.copy()
    np.random.seed(base.SYNTHETIC_PARAMETERS["random_seed"] + seed_offset)
    forward_messages = []
    synthetic.forward(
        noise=base.SYNTHETIC_PARAMETERS["gaussian_noise_percent"],
        iplot=False,
        dump=lambda message: forward_messages.append(str(message)),
    )
    (synthetic_dir / "resipy_forward_messages.log").write_text(
        "\n".join(forward_messages), encoding="utf-8"
    )
    synthetic.surveys[0].df.to_csv(
        synthetic_dir / "dados_sinteticos_forward.csv", index=False, encoding="utf-8-sig"
    )
    synthetic.saveForwardModelResult(str(synthetic_dir / "dados_sinteticos_resipy.dat"))
    synthetic_app = pd.to_numeric(
        synthetic.surveys[0].df["app"], errors="coerce"
    ).to_numpy(copy=True)
    synthetic.surveys[0].df["resError"] = (
        pd.to_numeric(synthetic.surveys[0].df["resist"], errors="coerce").abs()
        * base.SYNTHETIC_PARAMETERS["gaussian_noise_percent"]
        / 100.0
    )
    synthetic.err = True
    base.save_pseudo(
        synthetic,
        synthetic_dir / "02_pseudosecao_sintetica_combinada.png",
        f"{case['id']} — sintético combinado",
    )
    base.reset_to_homogeneous_start(
        synthetic, base.SYNTHETIC_PARAMETERS["background_resistivity_ohm_m"]
    )
    synthetic_summary = base.run_inversion(
        synthetic, synthetic_dir, f"{case['id']}_SINTETICO_QUAD"
    )
    base.save_results(
        synthetic,
        synthetic_dir / "03_recuperacao_sintetica_cut_corners.png",
        f"{case['id']} — recuperação sintética combinada",
    )
    metrics = base.compare_metrics(polygon, synthetic, real, real_app, synthetic_app)
    base.save_comparison(
        real,
        synthetic,
        true_mesh,
        case_dir / "COMPARACAO_VERDADEIRO_SINTETICO_REAL_CUT_CORNERS.png",
        f"{case['id']} — cavidade paramétrica versus arranjos combinados",
    )

    summary = {
        "case": case,
        "source_files": source_files,
        "source_counts_imported": source_counts,
        "source_counts_after_qc": after_qc,
        "qc": qc,
        "remote_electrode_real": remote_validation,
        "remote_electrode_synthetic": synthetic_remote_validation,
        "mesh_parameters": base.MESH_PARAMETERS,
        "inversion_parameters": base.INVERSION_PARAMETERS,
        "synthetic_parameters": base.SYNTHETIC_PARAMETERS,
        "cavity_intersection": cavity_details,
        "real_inversion": real_summary,
        "synthetic_inversion": synthetic_summary,
        "comparison_metrics": metrics,
        "cut_corners": True,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    (case_dir / "resumo.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=base.json_default),
        encoding="utf-8",
    )
    (real_dir / "parametros_resipy.json").write_text(
        json.dumps(real.param, indent=2, ensure_ascii=False, default=base.json_default),
        encoding="utf-8",
    )
    (synthetic_dir / "parametros_resipy.json").write_text(
        json.dumps(synthetic.param, indent=2, ensure_ascii=False, default=base.json_default),
        encoding="utf-8",
    )
    return summary


def validate_remote_electrode_for_synthetic(
    project: Project, case: dict, sequence: np.ndarray, output: Path
) -> dict:
    if not case["remote"]:
        result = {"required": False, "valid": True, "reason": "perfil sem polo-dipolo"}
    else:
        a_labels = pd.Series(sequence[:, 0]).astype(str)
        pd_count = int((a_labels == "67").sum())
        remote_rows = project.elec.loc[project.elec["remote"].astype(bool)]
        valid = pd_count > 0 and len(remote_rows) == 1 and str(remote_rows.iloc[0]["label"]) == "67"
        result = {
            "required": True,
            "valid": bool(valid),
            "sequence_rows_with_remote_a_67": pd_count,
            "remote_electrode_count": int(len(remote_rows)),
            "remote_label": str(remote_rows.iloc[0]["label"]) if len(remote_rows) else None,
            "representation": "ResIPy remote=True; forward R2 com polo no infinito",
        }
        if not valid:
            raise RuntimeError(f"Validação sintética do eletrodo remoto falhou: {result}")
    (output / "validacao_eletrodo_infinito.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def write_report(output: Path, summaries: list[dict], failures: list[dict]) -> None:
    lines = [
        "# Inversões combinadas quadrilaterais e ensaios sintéticos",
        "",
        f"Execução: {datetime.now().isoformat(timespec='seconds')}",
        f"ResIPy: {version('resipy')}",
        "",
        "- L1: DD + WS.",
        "- L2: DD + WS + PD; eletrodo 67 marcado como remoto/infinito.",
        "- Malha quadrilateral e parâmetros idênticos aos testes individuais.",
        "- Todas as seções invertidas usam Cut Corners.",
        "",
    ]
    for summary in summaries:
        metrics = summary["comparison_metrics"]
        lines.extend(
            [
                f"## {summary['case']['id']}",
                "",
                f"- Medições invertidas: {summary['qc']['measurements_inverted']}.",
                f"- RMS real: {summary['real_inversion']['rms']}.",
                f"- RMS sintético: {summary['synthetic_inversion']['rms']}.",
                f"- IoU sintético: {metrics['synthetic_iou']:.3f}.",
                "",
            ]
        )
    if failures:
        lines.extend(["## Falhas", ""])
        lines.extend([f"- {item['case']}: {item['error']}" for item in failures])
    (output / "RELATORIO_METODO_E_RESULTADOS.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--contact-max-ohm", type=float, default=40_000.0)
    parser.add_argument("--cases", nargs="*", choices=[case["id"] for case in CASES])
    parser.add_argument("--publish-images", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    base.configure_image_publisher(root, args.publish_images)
    if output.exists():
        raise FileExistsError(f"Saída já existe; não será sobrescrita: {output}")
    output.mkdir(parents=True)
    selected = CASES if not args.cases else [case for case in CASES if case["id"] in args.cases]
    metadata = {
        "resipy_version": version("resipy"),
        "mesh_parameters": base.MESH_PARAMETERS,
        "inversion_parameters": base.INVERSION_PARAMETERS,
        "synthetic_parameters": base.SYNTHETIC_PARAMETERS,
        "contact_max_ohm": args.contact_max_ohm,
        "cases": [case["id"] for case in selected],
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    (output / "PARAMETROS_USADOS.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    summaries, failures = [], []
    for index, case in enumerate(selected, start=100):
        try:
            summaries.append(process_case(root, output, case, args.contact_max_ohm, index))
        except Exception as exc:
            failures.append(
                {"case": case["id"], "error": repr(exc), "traceback": traceback.format_exc()}
            )
            print(f"[{case['id']}] FALHOU: {exc!r}", flush=True)
            break
    (output / "RESUMO_GERAL.json").write_text(
        json.dumps(
            {"success": summaries, "failures": failures},
            indent=2,
            ensure_ascii=False,
            default=base.json_default,
        ),
        encoding="utf-8",
    )
    write_report(output, summaries, failures)
    if failures:
        raise RuntimeError(f"{len(failures)} caso(s) falharam; consulte RESUMO_GERAL.json")
    print("TODOS_OS_CASOS_COMBINADOS_CONCLUIDOS", flush=True)


if __name__ == "__main__":
    main()
