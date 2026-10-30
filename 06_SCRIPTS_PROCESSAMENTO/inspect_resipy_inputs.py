from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd


def inspect_xlsx(path: Path) -> None:
    print(f"\n=== XLSX: {path} ===")
    book = pd.ExcelFile(path)
    print("sheets:", book.sheet_names)
    for sheet in book.sheet_names:
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        print(f"-- sheet={sheet!r} shape={raw.shape}")
        print(raw.head(12).to_string(index=True, header=False))
        if len(raw) > 12:
            print("... tail ...")
            print(raw.tail(5).to_string(index=True, header=False))


def inspect_kmz(path: Path) -> None:
    print(f"\n=== KMZ: {path} ===")
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        print("members:", names)
        kml_names = [name for name in names if name.lower().endswith(".kml")]
        for name in kml_names:
            text = zf.read(name).decode("utf-8", errors="replace")
            print(text[:8000])


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_resipy_inputs.py ROOT")
    root = Path(sys.argv[1]).resolve()
    candidates = [
        root / "02_DADOS_GEOFISICOS/20262210/Linha01_Dolina_10m.xlsx",
        root / "02_DADOS_GEOFISICOS/20262410/Linha02_Dolina_10m.xlsx",
        root / "01_PROJETO_DOLINA_MARACANAS/01_MODELO_3D/L1_electrodes_utm.xlsx",
        root / "01_PROJETO_DOLINA_MARACANAS/01_MODELO_3D/L2_electrodes_utm.xlsx",
        root / "01_PROJETO_DOLINA_MARACANAS/01_MODELO_3D/section_template.xlsx",
        root / "02_DADOS_GEOFISICOS/20262210/L1_linha.kmz",
        root / "02_DADOS_GEOFISICOS/20262210/L1.kmz",
        root / "02_DADOS_GEOFISICOS/20262410/L2.kmz",
    ]
    for path in candidates:
        if not path.exists():
            print(f"MISSING: {path}")
        elif path.suffix.lower() == ".xlsx":
            inspect_xlsx(path)
        elif path.suffix.lower() == ".kmz":
            inspect_kmz(path)


if __name__ == "__main__":
    main()
