from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from Concordia_plots import extract_samples

RSCRIPT = r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe"
OUTPUT_PDF = Path(
    r"C:\Users\vetle\OneDrive - Høgskulen på Vestlandet\7. Bachelor\Zirkondatering"
) / "IsoplotR_DG12_pure.pdf"

R_SCRIPT = r"""
suppressWarnings(suppressMessages(library(IsoplotR)))

pdf(file = "{pdf_path}", width = 7, height = 7)

upb <- read.data("{csv_path}", method = "U-Pb", format = 2, ierr = 2)

concordia(upb, type = 1, oerr = 3)

invisible(dev.off())
"""


def main() -> None:
    df = extract_samples()["DG12"].reset_index(drop=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        csv_path = tmp_dir / "DG12.csv"
        df[["U238Pb206", "errU238Pb206", "Pb207Pb206", "errPb207Pb206", "rXY"]].to_csv(
            csv_path, index=False
        )
        r_path = tmp_dir / "pure.R"
        r_path.write_text(
            R_SCRIPT.format(csv_path=csv_path.as_posix(), pdf_path=OUTPUT_PDF.as_posix()),
            encoding="utf-8",
        )
        result = subprocess.run(
            [RSCRIPT, "--vanilla", str(r_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("R stdout:\n", result.stdout)
            print("R stderr:\n", result.stderr)
            raise RuntimeError("Rscript failed")
    print(f"Saved: {OUTPUT_PDF}  ({len(df)} grains)")


if __name__ == "__main__":
    main()
