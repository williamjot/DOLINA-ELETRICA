from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent / "resipy-src" / "src"
sys.path.insert(0, str(SRC))

from resipy import Project  # noqa: E402


def numeric_summary(series: pd.Series) -> dict:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return {"count": 0}
    return {
        "count": int(values.size),
        "min": float(values.min()),
        "p05": float(values.quantile(0.05)),
        "median": float(values.median()),
        "p95": float(values.quantile(0.95)),
        "max": float(values.max()),
        "negative": int((values < 0).sum()),
        "zero": int((values == 0).sum()),
    }


def diagnose(path: Path, work_root: Path) -> dict:
    name = path.stem
    workdir = work_root / name
    workdir.mkdir(parents=True, exist_ok=True)
    project = Project(dirname=str(workdir), typ="R2")
    project.createSurvey(str(path), ftype="Syscal", debug=False, estMemory=False)
    survey = project.surveys[0]
    df = survey.df.copy()
    result = {
        "name": name,
        "path": str(path),
        "project_type_after_import": project.typ,
        "measurements": int(len(df)),
        "electrodes": int(len(project.elec)),
        "electrode_columns": list(project.elec.columns),
        "electrode_x_min": float(project.elec.x.min()),
        "electrode_x_max": float(project.elec.x.max()),
        "electrode_z_min": float(project.elec.z.min()),
        "electrode_z_max": float(project.elec.z.max()),
        "columns": list(df.columns),
        "numeric": {},
    }
    for col in [
        "resist",
        "app",
        "dev",
        "recipError",
        "recipMean",
        "ip",
        "magErr",
        "phiErr",
        "cR",
    ]:
        if col in df.columns:
            result["numeric"][col] = numeric_summary(df[col])
    if "irecip" in df.columns:
        irecip = pd.to_numeric(df["irecip"], errors="coerce").fillna(0)
        result["irecip_nonzero"] = int((irecip != 0).sum())
        result["irecip_positive"] = int((irecip > 0).sum())
        result["irecip_negative"] = int((irecip < 0).sum())
    if all(col in df.columns for col in ["a", "b", "m", "n"]):
        result["electrode_labels_used"] = int(
            pd.unique(df[["a", "b", "m", "n"]].astype(str).values.ravel()).size
        )
    return result


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: resipy_diagnose.py ROOT OUTPUT_JSON")
    root = Path(sys.argv[1]).resolve()
    output_json = Path(sys.argv[2]).resolve()
    files = sorted((root / "02_DADOS_GEOFISICOS").glob("*/FILTRADOS/*.bin"))
    # The two PD files are byte-identical; retain the ResIPy-labelled copy as canonical.
    seen_hash_size: set[tuple[int, bytes]] = set()
    unique_files = []
    import hashlib

    for path in files:
        digest = hashlib.sha256(path.read_bytes()).digest()
        key = (path.stat().st_size, digest)
        if key in seen_hash_size:
            print(f"SKIP_BYTE_DUPLICATE: {path}")
            continue
        seen_hash_size.add(key)
        unique_files.append(path)

    work_root = output_json.parent / "diagnostic_projects"
    work_root.mkdir(parents=True, exist_ok=True)
    results = []
    for path in unique_files:
        print(f"DIAGNOSE: {path}")
        try:
            results.append(diagnose(path, work_root))
        except Exception as exc:
            results.append({"name": path.stem, "path": str(path), "error": repr(exc)})
            print(f"ERROR: {path}: {exc!r}")
    output_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
