from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent / "resipy-src" / "src"
sys.path.insert(0, str(SRC))
from resipy import Project  # noqa: E402


root = Path(sys.argv[1]).resolve()
check_root = Path(__file__).parent / "label_check"
check_root.mkdir(exist_ok=True)
for path in sorted((root / "02_DADOS_GEOFISICOS").glob("*/FILTRADOS/*.bin")):
    project = Project(dirname=str(check_root / path.stem), typ="R2")
    project.createSurvey(str(path), ftype="Syscal", debug=False, estMemory=False)
    survey = project.surveys[0]
    used = sorted(set(survey.df[["a", "b", "m", "n"]].astype(str).values.ravel()), key=lambda x: float(x))
    print("\n", path.name)
    print("used labels:", used)
    print("survey elec labels:", survey.elec["label"].astype(str).tolist())
    print("survey remote rows:\n", survey.elec[survey.elec["remote"]].to_string(index=False))
