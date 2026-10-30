from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent / "resipy-src" / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))
import resipy  # noqa: E402
from resipy import Project  # noqa: E402


PROFILES = [
    {
        "id": "L1_2026-10-22_COMBINADO_DD_WS",
        "date_folder": "20262210",
        "topography": "Linha01_Dolina_10m.xlsx",
        "arrays": [
            ("DD", "20262210_DD_FILTRADO.bin"),
            ("WS", "20262210_WS_FILTRADO.bin"),
        ],
        "remote": False,
    },
    {
        "id": "L2_2026-10-24_COMBINADO_DD_PD_WS",
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
    source = pd.read_excel(path)
    required = ["X", "Y", "Z"]
    missing = [c for c in required if c not in source.columns]
    if missing:
        raise ValueError(f"Topografia {path} sem colunas: {missing}")
    topo = source[required].apply(pd.to_numeric, errors="raise").astype(float)
    if len(topo) != 66:
        raise ValueError(f"Esperados 66 eletrodos em {path}; encontrados {len(topo)}")
    if topo.isna().any().any():
        raise ValueError(f"Topografia contém valores ausentes: {path}")
    if not np.all(np.diff(topo["X"].values) > 0):
        raise ValueError(f"Coordenada X não é estritamente crescente: {path}")
    return topo


def assign_source_after_add(project: Project, previous_count: int, source: str) -> None:
    survey = project.surveys[0]
    if "arranjo_origem" not in survey.df.columns:
        survey.df["arranjo_origem"] = np.nan
    survey.df.loc[survey.df["arranjo_origem"].isna(), "arranjo_origem"] = source


def plot_topography(topo: pd.DataFrame, output: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.plot(topo["X"], topo["Z"], color="#3A6B35", linewidth=1.8)
    ax.scatter(topo["X"], topo["Z"], s=11, color="#173F2A", zorder=3)
    ax.set_title(title)
    ax.set_xlabel("Distância ao longo da linha (m)")
    ax.set_ylabel("Cota (m)")
    ax.grid(True, color="#D9D9D9", linewidth=0.6)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def save_pseudo(project: Project, output: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))
    project.showPseudo(ax=ax)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def save_mesh(project: Project, output: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))
    project.showMesh(ax=ax)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def save_result(project: Project, output: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))
    project.showResults(ax=ax, sens=False, color_map="turbo", edge_color="none")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(output, dpi=220)
    plt.close(fig)


def save_inv_error(project: Project, output: Path, title: str) -> None:
    try:
        fig, ax = plt.subplots(figsize=(13, 5.5))
        project.showPseudoInvError(ax=ax)
        ax.set_title(title)
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
    except Exception:
        plt.close("all")


def physical_electrode_from_station(df: pd.DataFrame, role: str) -> pd.Series:
    """Recover the physical electrode number from the Syscal station coordinate."""
    x = pd.to_numeric(df[f"x{role}"], errors="coerce")
    physical = pd.Series(np.rint(x / 10.0) + 1, index=df.index)
    physical = physical.where(x.abs() < 10_000, 67)
    return physical.astype("Int64")


def make_columns_unique_case_insensitive(df: pd.DataFrame) -> pd.DataFrame:
    """Avoid CSV headers that collide in Excel/PowerShell (for example Rho/rho)."""
    output = df.copy()
    seen: dict[str, int] = {}
    unique = []
    for column in output.columns:
        base = str(column)
        key = base.casefold()
        count = seen.get(key, 0)
        seen[key] = count + 1
        unique.append(base if count == 0 else f"{base}_{count + 1}")
    output.columns = unique
    return output


def save_contact_cut_audit(
    survey,
    profile_dir: Path,
    threshold_ohm: float,
) -> tuple[int, dict, dict]:
    """Apply the contact-resistance cut and save a row-level audit trail."""
    if "cR" not in survey.df.columns:
        raise ValueError("A coluna cR não está disponível; corte de contato não aplicado.")

    before = survey.df.copy()
    c_r = pd.to_numeric(before["cR"], errors="coerce")
    if c_r.isna().any():
        raise ValueError(f"Há {int(c_r.isna().sum())} valores cR ausentes ou inválidos.")

    remove_mask = c_r.abs() > threshold_ohm
    removed_expected = int(remove_mask.sum())
    removed = before.loc[remove_mask].copy()
    kept_expected = before.loc[~remove_mask].copy()

    for role in ["A", "B", "M", "N"]:
        coordinate = f"x{role}"
        if coordinate in before.columns:
            removed[f"{role.lower()}_fisico"] = physical_electrode_from_station(removed, role)
            kept_expected[f"{role.lower()}_fisico"] = physical_electrode_from_station(kept_expected, role)

    removed.insert(0, "motivo_exclusao", f"abs(cR) > {threshold_ohm:g} ohm")
    removed.insert(1, "limite_cR_ohm", threshold_ohm)
    removed = make_columns_unique_case_insensitive(removed)
    removed.to_csv(
        profile_dir / "dados_removidos_contato_40k.csv",
        index=False,
        encoding="utf-8-sig",
    )

    before_by_array = before.groupby("arranjo_origem", dropna=False).size().astype(int).to_dict()
    removed_by_array = removed.groupby("arranjo_origem", dropna=False).size().astype(int).to_dict()

    removed_reported = survey.filterContRes(vmax=threshold_ohm, debug=True)
    if removed_reported != removed_expected:
        raise RuntimeError(
            f"Auditoria do corte divergiu: esperado {removed_expected}, ResIPy removeu {removed_reported}."
        )
    remaining_c_r = pd.to_numeric(survey.df["cR"], errors="coerce").abs()
    if remaining_c_r.isna().any() or bool((remaining_c_r > threshold_ohm).any()):
        raise RuntimeError("Ainda existem valores cR inválidos ou acima do limite após o corte.")
    if len(survey.df) != len(kept_expected):
        raise RuntimeError("A contagem final não confere com a máscara independente do corte.")

    after_by_array = survey.df.groupby("arranjo_origem", dropna=False).size().astype(int).to_dict()
    audit_rows = []
    for array_name in sorted(set(before_by_array) | set(after_by_array)):
        before_count = int(before_by_array.get(array_name, 0))
        after_count = int(after_by_array.get(array_name, 0))
        audit_rows.append(
            {
                "arranjo": array_name,
                "antes": before_count,
                "removidas_cR_acima_limite": int(removed_by_array.get(array_name, 0)),
                "depois": after_count,
                "limite_cR_ohm": threshold_ohm,
                "limite_inclusivo": True,
            }
        )
    pd.DataFrame(audit_rows).to_csv(
        profile_dir / "auditoria_corte_contato_40k.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return removed_reported, before_by_array, after_by_array


def process_profile(root: Path, output_root: Path, cfg: dict, contact_max_ohm: float) -> dict:
    profile_dir = output_root / cfg["id"]
    if profile_dir.exists():
        raise FileExistsError(f"Diretório de resultado já existe: {profile_dir}")
    profile_dir.mkdir(parents=True)
    project_root = profile_dir / "projeto_resipy"

    date_root = root / "02_DADOS_GEOFISICOS" / cfg["date_folder"]
    filtered_root = date_root / "FILTRADOS"
    topo_path = date_root / cfg["topography"]
    topo = load_topography(topo_path)
    topo_csv = profile_dir / "topografia_XYZ_sem_cabecalho.csv"
    topo.to_csv(topo_csv, index=False, header=False, float_format="%.6f")
    topo_numbered = topo.copy()
    topo_numbered.insert(0, "eletrodo", np.arange(1, len(topo) + 1))
    topo_numbered.to_csv(profile_dir / "topografia_eletrodos.csv", index=False, float_format="%.6f")
    plot_topography(topo, profile_dir / "01_topografia.png", f"{cfg['id']} — topografia aplicada")

    source_files = []
    source_counts = {}
    first_array, first_name = cfg["arrays"][0]
    first_path = filtered_root / first_name
    project = Project(dirname=str(project_root), typ="R2")
    project.createSurvey(str(first_path), ftype="Syscal", debug=False, estMemory=False)
    project.surveys[0].df["arranjo_origem"] = first_array
    source_files.append(str(first_path))
    source_counts[first_array] = int(len(project.surveys[0].df))

    for array_name, filename in cfg["arrays"][1:]:
        path = filtered_root / filename
        before = len(project.surveys[0].df)
        project.addData(index=0, fname=str(path), ftype="Syscal")
        assign_source_after_add(project, before, array_name)
        after = len(project.surveys[0].df)
        source_files.append(str(path))
        source_counts[array_name] = int(after - before)

    elec = topo.rename(columns={"X": "x", "Y": "y", "Z": "z"}).copy()
    elec.insert(0, "label", (np.arange(1, len(elec) + 1)).astype(str))
    elec["buried"] = False
    elec["remote"] = False
    if cfg["remote"]:
        remote = pd.DataFrame(
            # ResIPy 3.6.6 has a computeFineMeshDepth indexing bug when the
            # remote flag is already set during setElec(). Add it as a normal
            # electrode first, then flag it immediately afterwards and pass a
            # finite, surface-only FMD to createMesh().
            [{"label": "67", "x": 99999.0, "y": 0.0, "z": 0.0, "buried": False, "remote": False}]
        )
        elec = pd.concat([elec, remote], ignore_index=True)
    project.setElec(elec)
    if cfg["remote"]:
        remote_mask = project.elec["label"].astype(str) == "67"
        project.elec.loc[remote_mask, "remote"] = True
        project.surveys[0].elec = project.elec
        project.pinfo["Remote electrodes"] = True
        project.fmd = float((topo["X"].max() - topo["X"].min()) / 3.0)
    project.surveys[0].computeK()
    project.surveys[0].df["app"] = (
        project.surveys[0].df["K"] * project.surveys[0].df["resist"]
    )

    survey = project.surveys[0]
    measurements_before_qc = len(survey.df)
    app = pd.to_numeric(survey.df["app"], errors="coerce")
    resist = pd.to_numeric(survey.df["resist"], errors="coerce")
    keep = np.isfinite(app) & np.isfinite(resist) & (app > 0) & (resist != 0)
    invalid_removed = int((~keep).sum())
    if invalid_removed:
        survey.filterData(keep)
    measurements_after_basic_qc = len(survey.df)

    contact_removed, counts_before_contact, counts_after_contact = save_contact_cut_audit(
        survey, profile_dir, contact_max_ohm
    )
    measurements_after_qc = len(survey.df)

    # Survey.addData() does not propagate the instrument magErr column into
    # resError for appended Syscal files. Fill it explicitly so all combined
    # measurements receive the same documented error weighting used by a
    # single-file ResIPy import.
    if "magErr" in survey.df.columns:
        survey.df["resError"] = pd.to_numeric(survey.df["magErr"], errors="coerce")
        project.err = not survey.df["resError"].isna().any()

    reciprocity_available = bool("recipError" in survey.df.columns and survey.df["recipError"].notna().any())
    stacking_filter_available = "dev" in survey.df.columns
    measured_error_available = bool("magErr" in survey.df.columns and survey.df["magErr"].notna().any())

    qc_columns = [
        c
        for c in [
            "arranjo_origem",
            "a",
            "b",
            "m",
            "n",
            "resist",
            "app",
            "magErr",
            "cR",
            "recipError",
        ]
        if c in survey.df.columns
    ]
    survey.df[qc_columns].to_csv(profile_dir / "dados_combinados_qc.csv", index=False)
    project.elec.to_csv(profile_dir / "eletrodos_aplicados.csv", index=False)
    save_pseudo(project, profile_dir / "02_pseudosecao_observada.png", f"{cfg['id']} — dados observados combinados")

    print(f"[{cfg['id']}] criando malha triangular com topografia", flush=True)
    mesh_fmd = project.fmd if cfg["remote"] else None
    project.createMesh(typ="trian", show_output=False, fmd=mesh_fmd)
    save_mesh(project, profile_dir / "03_malha_topografica.png", f"{cfg['id']} — malha triangular")
    project.exportMesh(str(profile_dir / "malha_topografica.vtk"), _forceLocal=True)

    project.setTitle(cfg["id"])
    inversion_messages = []
    print(f"[{cfg['id']}] iniciando inversão R2 ({measurements_after_qc} medições)", flush=True)
    project.invert(iplot=False, dump=lambda msg: inversion_messages.append(str(msg)))
    (profile_dir / "resipy_inversion_messages.log").write_text(
        "\n".join(inversion_messages), encoding="utf-8"
    )
    r2_out = project_root / "invdir" / "R2.out"
    if r2_out.exists():
        (profile_dir / "R2.out").write_bytes(r2_out.read_bytes())

    result_csv = profile_dir / "resultado_csv"
    result_vtk = profile_dir / "resultado_vtk"
    project.exportMeshResults(dirname=str(result_csv), ftype=".csv", _forceLocal=True)
    project.exportMeshResults(dirname=str(result_vtk), ftype=".vtk", _forceLocal=True)
    save_result(project, profile_dir / "04_modelo_resistividade.png", f"{cfg['id']} — modelo invertido")
    save_inv_error(project, profile_dir / "05_erro_normalizado.png", f"{cfg['id']} — erro normalizado")

    try:
        iteration_df = project.getR2out()
        iteration_df.to_csv(profile_dir / "historico_iteracoes.csv", index=False)
    except Exception:
        iteration_df = pd.DataFrame()

    project.saveProject(str(profile_dir / f"{cfg['id']}.resipy"))
    (profile_dir / "parametros_inversao.json").write_text(
        json.dumps(project.param, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8"
    )

    summary = {
        "profile": cfg["id"],
        "source_files": source_files,
        "source_counts_after_import": source_counts,
        "topography_source": str(topo_path),
        "topography_electrodes": int(len(topo)),
        "topography_x_min_m": float(topo.X.min()),
        "topography_x_max_m": float(topo.X.max()),
        "topography_z_min_m": float(topo.Z.min()),
        "topography_z_max_m": float(topo.Z.max()),
        "remote_electrode_added": bool(cfg["remote"]),
        "measurements_before_qc": int(measurements_before_qc),
        "measurements_removed_invalid": invalid_removed,
        "measurements_after_basic_qc": int(measurements_after_basic_qc),
        "contact_resistance_max_ohm": float(contact_max_ohm),
        "contact_filter_applied": True,
        "measurements_removed_contact": int(contact_removed),
        "counts_before_contact_by_array": counts_before_contact,
        "counts_after_contact_by_array": counts_after_contact,
        "measurements_inverted": int(measurements_after_qc),
        "reciprocity_filter_applied": False,
        "reciprocity_filter_reason": "Nenhuma medição recíproca disponível." if not reciprocity_available else "Não aplicado; dados já filtrados.",
        "unpaired_filter_applied": False,
        "unpaired_filter_reason": "Sem pares recíprocos; removeria dados válidos.",
        "stacking_filter_applied": False,
        "stacking_filter_reason": "Coluna dev ausente; magErr foi usada como peso de erro." if not stacking_filter_available else "Dados já filtrados.",
        "negative_transfer_resistance_filter_applied": False,
        "negative_transfer_resistance_filter_reason": "Sinal negativo é geométrico em DD/PD; resistividade aparente é positiva.",
        "measured_error_weighting": measured_error_available,
        "resipy_version": getattr(resipy, "__version__", "3.6.6"),
        "project_summary": project.pinfo,
        "mesh_elements": int(project.pinfo.get("Number of Elements", 0)),
        "mesh_nodes": int(project.pinfo.get("Number of Nodes", 0)),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    (profile_dir / "resumo_processamento.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8"
    )
    print(f"[{cfg['id']}] concluído", flush=True)
    return summary


def write_report(output_root: Path, summaries: list[dict], failures: list[dict], contact_max_ohm: float) -> None:
    lines = [
        "# Processamento e inversão ResIPy — Dolina dos Maracanãs",
        "",
        f"Data de execução: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Metodologia",
        "",
        "- ResIPy 3.6.6, projeto 2D R2.",
        "- Arquivos Syscal `.bin` já filtrados foram importados e combinados por linha.",
        "- Topografia aplicada por eletrodo a partir das planilhas X, Y, Z, sem cabeçalho no arquivo de intercâmbio.",
        "- Malha triangular gerada pelo Gmsh com a topografia incorporada.",
        "- Inversão logarítmica regularizada com parâmetros padrão do ResIPy/R2 e pesos instrumentais `magErr`.",
        "- Foram removidos registros não finitos, com resistividade aparente não positiva ou resistência nula.",
        f"- Corte de resistência de contato aplicado por medição: `abs(cR) > {contact_max_ohm:,.0f} Ω`.",
        "- Os arquivos `.bin` de origem não foram modificados; cada remoção foi registrada em CSV.",
        "- Filtros de reciprocidade e dados sem par não foram aplicados porque não existem recíprocos nos arquivos.",
        "- O filtro `filterNegative()` não foi aplicado porque DD/PD apresentam resistência de transferência negativa por convenção geométrica, com resistividade aparente positiva.",
        "",
        "## Resultados",
        "",
    ]
    for summary in summaries:
        pinfo = summary.get("project_summary", {})
        lines.extend(
            [
                f"### {summary['profile']}",
                "",
                f"- Medições invertidas: {summary['measurements_inverted']}",
                f"- Medições removidas pelo corte de contato: {summary['measurements_removed_contact']}",
                f"- Eletrodos topográficos: {summary['topography_electrodes']}",
                f"- Faixa de cota: {summary['topography_z_min_m']:.2f} a {summary['topography_z_max_m']:.2f} m",
                f"- Elementos da malha: {summary.get('mesh_elements', 0)}",
                f"- RMS final informado pelo ResIPy: {pinfo.get('RMS of inverse solution', 'n.d.')}",
                f"- Iterações: {pinfo.get('Number of iterations', 'n.d.')}",
                f"- Convergência: {pinfo.get('Convergence of inverse solution', 'n.d.')}",
                "",
            ]
        )
    if failures:
        lines.extend(["## Falhas", ""])
        for failure in failures:
            lines.append(f"- {failure['profile']}: {failure['error']}")
        lines.append("")
    lines.extend(
        [
            "## Conteúdo de cada pasta de perfil",
            "",
            "- `04_modelo_resistividade.png`: seção de resistividade invertida.",
            "- `resultado_csv/` e `resultado_vtk/`: malha e valores numéricos para análise externa.",
            "- `dados_combinados_qc.csv`: quadrupolos efetivamente usados.",
            "- `dados_removidos_contato_40k.csv`: trilha linha a linha do corte.",
            "- `auditoria_corte_contato_40k.csv`: contagens antes/depois por arranjo.",
            "- `topografia_eletrodos.csv`: topografia aplicada.",
            "- `R2.out` e `historico_iteracoes.csv`: registro de convergência.",
            "- `.resipy`: projeto reabrível no ResIPy.",
            "",
        ]
    )
    (output_root / "RELATORIO_PROCESSAMENTO.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Combina, corta resistência de contato e reinverte L1/L2 no ResIPy."
    )
    parser.add_argument("root", type=Path, help="Raiz DOLINA DOS MARACANAS")
    parser.add_argument("output_dir", type=Path, help="Nova pasta de saída (não pode existir)")
    parser.add_argument(
        "--contact-max-ohm",
        type=float,
        default=40_000.0,
        help="Maior abs(cR) aceito, em ohm (padrão: 40000)",
    )
    args = parser.parse_args()
    if not math.isfinite(args.contact_max_ohm) or args.contact_max_ohm <= 0:
        parser.error("--contact-max-ohm deve ser positivo e finito")
    root = args.root.resolve()
    output_root = args.output_dir.resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    if output_root.exists():
        raise FileExistsError(f"Saída já existe; não será sobrescrita: {output_root}")
    output_root.mkdir(parents=True)

    summaries = []
    failures = []
    for cfg in PROFILES:
        try:
            summaries.append(process_profile(root, output_root, cfg, args.contact_max_ohm))
        except Exception as exc:
            failures.append(
                {
                    "profile": cfg["id"],
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            print(f"[{cfg['id']}] FALHOU: {exc!r}", flush=True)
    (output_root / "resumos.json").write_text(
        json.dumps({"success": summaries, "failures": failures}, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )
    write_report(output_root, summaries, failures, args.contact_max_ohm)
    if failures:
        raise RuntimeError(f"{len(failures)} perfil(is) falharam; consulte resumos.json")
    print("TODOS_OS_PERFIS_CONCLUIDOS", flush=True)


if __name__ == "__main__":
    main()
