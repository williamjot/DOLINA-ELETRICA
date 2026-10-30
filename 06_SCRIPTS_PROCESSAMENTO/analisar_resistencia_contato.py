from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from resipy.parsers import syscalParser


THRESHOLD_OHM = 40_000.0
SATURATION_OHM = 999_000.0
SPACING_M = 10.0


def load_syscal(path: Path, line: str, array: str, stage: str) -> pd.DataFrame:
    _, df = syscalParser(str(path))
    out = df.copy()
    for col in ["a", "b", "m", "n"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    out["line"] = line
    out["array"] = array
    out["stage"] = stage
    out["source_file"] = path.name
    out["source_row"] = np.arange(1, len(out) + 1)
    out["cR_ohm"] = pd.to_numeric(out["cR"], errors="coerce")
    out["cR_kohm"] = out["cR_ohm"] / 1000.0
    out["over_40k"] = out["cR_ohm"].abs() > THRESHOLD_OHM
    out["saturated_999k"] = out["cR_ohm"].abs() >= SATURATION_OHM
    # The parser may renumber labels after filtering if an electrode disappears.
    # Recover the physical electrode number from the stored station coordinate.
    for role in ["A", "B", "M", "N"]:
        x = pd.to_numeric(out[f"x{role}"], errors="coerce")
        physical = np.rint(x / SPACING_M).astype("int64") + 1
        physical = pd.Series(physical, index=out.index).where(x.abs() < 10_000, 67)
        out[f"{role.lower()}_phys"] = physical.astype("Int64")
    # In these multichannel files RsChk varies with the receiver channel M-N.
    out["contact_e1"] = out[["m_phys", "n_phys"]].min(axis=1).astype("Int64")
    out["contact_e2"] = out[["m_phys", "n_phys"]].max(axis=1).astype("Int64")
    out["contact_pair"] = out["contact_e1"].astype(str) + "-" + out["contact_e2"].astype(str)
    return out


def file_summary(df: pd.DataFrame) -> dict:
    cr = df["cR_ohm"].abs()
    high = df["over_40k"]
    good_mag = pd.to_numeric(df.get("magErr"), errors="coerce")
    current = pd.to_numeric(df.get("in"), errors="coerce").abs()
    return {
        "line": df["line"].iat[0],
        "array": df["array"].iat[0],
        "stage": df["stage"].iat[0],
        "source_file": df["source_file"].iat[0],
        "measurements": len(df),
        "above_40k": int(high.sum()),
        "above_40k_pct": float(100 * high.mean()),
        "saturated_999k": int(df["saturated_999k"].sum()),
        "median_cR_kohm": float(cr.median() / 1000),
        "p90_cR_kohm": float(cr.quantile(0.90) / 1000),
        "p95_cR_kohm": float(cr.quantile(0.95) / 1000),
        "max_cR_kohm": float(cr.max() / 1000),
        "median_magErr_below_40k_pct": float(good_mag[~high].median()),
        "median_magErr_above_40k_pct": float(good_mag[high].median()) if high.any() else np.nan,
        "median_current_below_40k": float(current[~high].median()),
        "median_current_above_40k": float(current[high].median()) if high.any() else np.nan,
    }


def pair_stats(raw: pd.DataFrame) -> pd.DataFrame:
    keys = ["line", "array", "contact_e1", "contact_e2", "contact_pair"]
    rows = []
    for key, group in raw.groupby(keys, dropna=False):
        cr = group["cR_ohm"].abs()
        rows.append(
            dict(
                zip(keys, key),
                measurements=len(group),
                median_cR_kohm=cr.median() / 1000,
                p90_cR_kohm=cr.quantile(0.90) / 1000,
                max_cR_kohm=cr.max() / 1000,
                above_40k=int(group["over_40k"].sum()),
                above_40k_pct=100 * group["over_40k"].mean(),
                saturated_999k=int(group["saturated_999k"].sum()),
            )
        )
    out = pd.DataFrame(rows)
    out["pair_median_above_40k"] = out["median_cR_kohm"] > 40
    return out.sort_values(["line", "median_cR_kohm"], ascending=[True, False])


def electrode_stats(raw: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    role_rows = []
    for role in ["m_phys", "n_phys"]:
        part = raw[["line", "array", role, "contact_pair", "cR_ohm", "over_40k", "saturated_999k"]].copy()
        part = part.rename(columns={role: "electrode"})
        part["role"] = role[0].upper()
        role_rows.append(part)
    long = pd.concat(role_rows, ignore_index=True)
    long = long[long["electrode"].notna()].copy()
    long["electrode"] = long["electrode"].astype(int)

    pair_long = pd.concat(
        [
            pairs.rename(columns={"contact_e1": "electrode"}),
            pairs.rename(columns={"contact_e2": "electrode"}),
        ],
        ignore_index=True,
    )
    pair_long["electrode"] = pair_long["electrode"].astype(int)

    rows = []
    for (line, electrode), group in long.groupby(["line", "electrode"]):
        p = pair_long[(pair_long["line"] == line) & (pair_long["electrode"] == electrode)]
        ptests = p.drop_duplicates(["array", "contact_pair"])
        cr = group["cR_ohm"].abs()
        rows.append(
            {
                "line": line,
                "electrode": electrode,
                "distance_m": (electrode - 1) * SPACING_M if electrode <= 66 else np.nan,
                "receiver_occurrences": len(group),
                "above_40k": int(group["over_40k"].sum()),
                "above_40k_pct": 100 * group["over_40k"].mean(),
                "saturated_999k": int(group["saturated_999k"].sum()),
                "median_pair_cR_kohm": cr.median() / 1000,
                "p90_pair_cR_kohm": cr.quantile(0.90) / 1000,
                "max_pair_cR_kohm": cr.max() / 1000,
                "pair_array_tests": int(len(ptests)),
                "pair_array_tests_median_above_40k": int(ptests["pair_median_above_40k"].sum()),
                "arrays": ",".join(sorted(group["array"].unique())),
            }
        )
    out = pd.DataFrame(rows)
    out["high_pair_pct"] = 100 * out["pair_array_tests_median_above_40k"] / out["pair_array_tests"].clip(lower=1)
    out["evidence_score"] = (
        out["above_40k"].clip(upper=50)
        + 5 * out["pair_array_tests_median_above_40k"]
        + 0.1 * out["above_40k_pct"]
        + 2 * out["saturated_999k"].clip(upper=10)
    )
    return out.sort_values(["line", "evidence_score"], ascending=[True, False])


def measurement_position(row: pd.Series) -> float:
    m, n = int(row["m_phys"]), int(row["n_phys"])
    local = [e for e in (m, n) if e <= 66]
    if not local:
        return np.nan
    return float(np.mean([(e - 1) * SPACING_M for e in local]))


def plot_contact(raw: pd.DataFrame, filtered: pd.DataFrame, electrode: pd.DataFrame, outdir: Path) -> None:
    colors = {"DD": "#2563eb", "WS": "#16a34a", "PD": "#dc2626"}
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), constrained_layout=True)
    for ax, line in zip(axes, ["L1", "L2"]):
        subset = raw[raw["line"] == line].copy()
        subset["position_m"] = subset.apply(measurement_position, axis=1)
        for array, group in subset.groupby("array"):
            y = group["cR_kohm"].clip(upper=150)
            ax.scatter(group["position_m"], y, s=13, alpha=0.36, color=colors[array], label=array)
        suspects = electrode[(electrode["line"] == line) & (electrode["pair_array_tests_median_above_40k"] > 0)]
        for _, row in suspects.head(12).iterrows():
            if pd.notna(row["distance_m"]):
                ax.axvline(row["distance_m"], color="#7c3aed", alpha=0.16, lw=1)
                ax.text(row["distance_m"], 147, str(int(row["electrode"])), ha="center", va="top", fontsize=8)
        ax.axhline(40, color="black", ls="--", lw=1.5, label="limite 40 kΩ")
        ax.set_title(f"{line}: resistência de contato bruta por posição do dipolo receptor")
        ax.set_ylabel("cR associado ao par M–N [kΩ] (limitado a 150 no gráfico)")
        ax.set_xlim(-5, 655)
        ax.set_ylim(0, 150)
        ax.grid(alpha=0.2)
        ax.legend(ncol=4, loc="upper left")
    axes[-1].set_xlabel("Distância ao longo da linha [m]")
    fig.savefig(outdir / "01_resistencia_contato_bruta_por_posicao.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), constrained_layout=True)
    for ax, line in zip(axes, ["L1", "L2"]):
        subset = electrode[(electrode["line"] == line) & (electrode["electrode"] <= 66)].sort_values("electrode")
        ax.bar(subset["electrode"], subset["above_40k_pct"], color="#f97316", alpha=0.75, label="medições >40 kΩ")
        ax.plot(subset["electrode"], subset["high_pair_pct"], color="#7c3aed", marker="o", ms=3, lw=1, label="combinações par/arranjo com mediana >40 kΩ")
        ax.set_title(f"{line}: evidência de contato alto por eletrodo receptor")
        ax.set_ylabel("Percentual [%]")
        ax.set_xlim(0, 67)
        ax.set_ylim(0, 105)
        ax.grid(alpha=0.2)
        ax.legend(loc="upper right")
    axes[-1].set_xlabel("Número do eletrodo (passo de 10 m)")
    fig.savefig(outdir / "02_ranking_eletrodos_contato.png", dpi=220)
    plt.close(fig)

    summary_rows = []
    for (line, array), group in filtered.groupby(["line", "array"]):
        summary_rows.append(
            {
                "line": line,
                "array": array,
                "kept": int((~group["over_40k"]).sum()),
                "remove": int(group["over_40k"].sum()),
            }
        )
    s = pd.DataFrame(summary_rows)
    fig, ax = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    labels = s["line"] + " " + s["array"]
    ax.bar(labels, s["kept"], color="#10b981", label="mantidas ≤40 kΩ")
    ax.bar(labels, s["remove"], bottom=s["kept"], color="#ef4444", label="removidas >40 kΩ")
    for x, (_, row) in enumerate(s.iterrows()):
        ax.text(x, row["kept"] + row["remove"] + 12, str(row["remove"]), ha="center", color="#b91c1c", fontweight="bold")
    ax.set_ylabel("Número de medições")
    ax.set_title("Impacto do corte de resistência de contato nos arquivos já filtrados")
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    fig.savefig(outdir / "03_impacto_corte_40k_filtrados.png", dpi=220)
    plt.close(fig)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("uso: analisar_resistencia_contato.py <raiz_dados> <saida>")
    root = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)

    specs = [
        ("L1", "DD", "raw", root / "02_DADOS_GEOFISICOS/20262210/BRUTOS/20262210_DD_BRUTO.bin"),
        ("L1", "WS", "raw", root / "02_DADOS_GEOFISICOS/20262210/BRUTOS/20262210_WS_BRUTO.bin"),
        ("L1", "DD", "filtered", root / "02_DADOS_GEOFISICOS/20262210/FILTRADOS/20262210_DD_FILTRADO.bin"),
        ("L1", "WS", "filtered", root / "02_DADOS_GEOFISICOS/20262210/FILTRADOS/20262210_WS_FILTRADO.bin"),
        ("L2", "DD", "raw", root / "02_DADOS_GEOFISICOS/20262410/BRUTOS/20262410_DD_BRUTO.bin"),
        ("L2", "WS", "raw", root / "02_DADOS_GEOFISICOS/20262410/BRUTOS/20262410_WS_BRUTO.bin"),
        ("L2", "PD", "raw", root / "02_DADOS_GEOFISICOS/20262410/BRUTOS/20262410_PD_BRUTO.bin"),
        ("L2", "DD", "filtered", root / "02_DADOS_GEOFISICOS/20262410/FILTRADOS/20262410_DD_FILTRADO.bin"),
        ("L2", "WS", "filtered", root / "02_DADOS_GEOFISICOS/20262410/FILTRADOS/20262410_WS_FILTRADO.bin"),
        ("L2", "PD", "filtered", root / "02_DADOS_GEOFISICOS/20262410/FILTRADOS/20262410_PD_FILTRADO_RESIPY.bin"),
    ]
    frames = [load_syscal(path, line, array, stage) for line, array, stage, path in specs]
    all_data = pd.concat(frames, ignore_index=True)
    raw = all_data[all_data["stage"] == "raw"].copy()
    filtered = all_data[all_data["stage"] == "filtered"].copy()

    summaries = pd.DataFrame([file_summary(df) for df in frames])
    pairs = pair_stats(raw)
    electrodes = electrode_stats(raw, pairs)

    summaries.to_csv(outdir / "resumo_por_arquivo.csv", index=False, encoding="utf-8-sig")
    pairs.to_csv(outdir / "pares_contato_brutos.csv", index=False, encoding="utf-8-sig")
    electrodes.to_csv(outdir / "ranking_eletrodos_brutos.csv", index=False, encoding="utf-8-sig")
    cols = ["line", "array", "stage", "source_file", "source_row", "a", "b", "m", "n", "a_phys", "b_phys", "m_phys", "n_phys", "contact_pair", "cR_ohm", "cR_kohm", "magErr", "in", "vp", "Rho", "over_40k", "saturated_999k"]
    all_data.loc[all_data["over_40k"], cols].to_csv(outdir / "medicoes_acima_40k.csv", index=False, encoding="utf-8-sig")
    filtered.loc[filtered["over_40k"], cols].to_csv(outdir / "medicoes_filtradas_a_remover_40k.csv", index=False, encoding="utf-8-sig")

    plot_contact(raw, filtered, electrodes, outdir)

    result = {
        "threshold_ohm": THRESHOLD_OHM,
        "threshold_kohm": THRESHOLD_OHM / 1000,
        "raw_measurements": int(len(raw)),
        "raw_above_threshold": int(raw["over_40k"].sum()),
        "filtered_measurements": int(len(filtered)),
        "filtered_above_threshold": int(filtered["over_40k"].sum()),
        "filtered_remaining_after_cut": int((~filtered["over_40k"]).sum()),
        "top_suspects": electrodes.groupby("line", group_keys=False).head(15).to_dict(orient="records"),
    }
    (outdir / "resumo.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
