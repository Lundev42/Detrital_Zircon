from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
EXCEL_PATH = PROJECT_DIR / "Alle_ZirkonPrøver_Ratios.xlsx"
RSCRIPT = r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe"
OUTPUT_PDF = PROJECT_DIR / "Concordia_plots.pdf"


def extract_samples() -> dict[str, pd.DataFrame]:
    raw = pd.read_excel(EXCEL_PATH, header=None)
    n_cols = raw.shape[1]
    samples: dict[str, pd.DataFrame] = {}

    col = 0
    while col < n_cols:
        name_cell = raw.iat[0, col + 1] if col + 1 < n_cols else None
        if name_cell is None or pd.isna(name_cell):
            col += 1
            continue

        sample = str(name_cell).strip()
        rho_label = raw.iat[1, col + 5] if col + 5 < n_cols else None
        has_rho = isinstance(rho_label, str) and "RHO" in rho_label.upper()

        block = raw.iloc[2:, col : col + 5].copy()
        block.columns = ["grain", "U238Pb206", "errU238Pb206", "Pb207Pb206", "errPb207Pb206"]
        if has_rho:
            block["rXY"] = pd.to_numeric(raw.iloc[2:, col + 5], errors="coerce")
        else:
            block["rXY"] = 0.0

        for c in ["U238Pb206", "errU238Pb206", "Pb207Pb206", "errPb207Pb206"]:
            block[c] = pd.to_numeric(block[c], errors="coerce")
        block["rXY"] = block["rXY"].fillna(0.0)
        block = block.dropna(subset=["U238Pb206", "errU238Pb206", "Pb207Pb206", "errPb207Pb206"])
        block = block.reset_index(drop=True)

        samples[sample] = block
        col += 7 if has_rho else 6

    return samples


def write_csvs(samples: dict[str, pd.DataFrame], out_dir: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for sample, df in samples.items():
        safe = sample.replace("/", "_")
        path = out_dir / f"{safe}.csv"
        df[["U238Pb206", "errU238Pb206", "Pb207Pb206", "errPb207Pb206", "rXY"]].to_csv(
            path, index=False
        )
        paths[sample] = path
    return paths


R_TEMPLATE = r"""
suppressWarnings(suppressMessages(library(IsoplotR)))

samples <- list({sample_entries})

# A4 = 8.27 x 11.69 inches; margins 2.5 cm = 0.984"; bottom caption 2 cm = 0.787"
pdf(file = "{pdf_path}", width = 8.27, height = 11.69)
par(omi = c(0.984 + 0.787, 0.984, 0.984, 0.984))
par(mfrow = c(5, 2))
par(mar = c(3.6, 3.8, 1.6, 0.6))
par(mgp = c(2.2, 0.7, 0))
par(cex.axis = 0.7, cex.lab = 0.8, cex.main = 0.9)

disc_filter <- discfilter(option = "r")  # relative age difference, default cutoff (-5, 15)%

for (sample in names(samples)) {{
    csv_path <- samples[[sample]]
    upb <- read.data(csv_path, method = "U-Pb", format = 2, ierr = 2)

    disc_idx <- IsoplotR:::is.discordant(upb, cutoff.disc = disc_filter)
    if (length(disc_idx) == 0) disc_idx <- NULL

    concordia(
        upb,
        type = 1,
        ellipse.fill   = "#7EBC8E80",
        ellipse.stroke = "#2f6f3d",
        omit           = disc_idx,
        omit.fill      = "#D9534F80",
        omit.stroke    = "#8B1A1A",
        cutoff.disc    = discfilter(option = 0),
        oerr           = 2,
        title          = FALSE,
        show.numbers   = FALSE
    )

    if (!is.null(disc_idx)) {{
        d <- data2york(upb, option = 1)
        x <- d[disc_idx, "X"]; y <- d[disc_idx, "Y"]
        text(x, y, labels = disc_idx, pos = 3, cex = 0.55, col = "#8B1A1A")
    }}

    mtext(sample, side = 3, line = 0.3, cex = 0.85, font = 2)

    n_total <- nrow(upb$x)
    n_disc  <- length(disc_idx)
    legend("topleft",
           legend = c(sprintf("Concordant (n=%d)", n_total - n_disc),
                      sprintf("Discordant (n=%d)", n_disc)),
           pch = 22, pt.bg = c("#7EBC8E80", "#D9534F80"),
           col = c("#2f6f3d", "#8B1A1A"),
           pt.cex = 1.2, cex = 0.6, bty = "n")
}}

invisible(dev.off())
"""


def build_r_script(sample_csvs: dict[str, Path], pdf_path: Path) -> str:
    entries = ", ".join(
        f'"{name}" = "{path.as_posix()}"' for name, path in sample_csvs.items()
    )
    return R_TEMPLATE.format(
        sample_entries=entries,
        pdf_path=pdf_path.as_posix(),
    )


def main() -> None:
    samples = extract_samples()
    if len(samples) != 10:
        print(f"Warning: expected 10 samples, found {len(samples)}: {list(samples)}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        csv_paths = write_csvs(samples, tmp_dir)
        r_script = build_r_script(csv_paths, OUTPUT_PDF)
        r_path = tmp_dir / "concordia.R"
        r_path.write_text(r_script, encoding="utf-8")

        result = subprocess.run(
            [RSCRIPT, "--vanilla", str(r_path)],
            cwd=tmp_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("R stdout:\n", result.stdout)
            print("R stderr:\n", result.stderr)
            raise RuntimeError("Rscript failed")
        if result.stderr.strip():
            print("R messages:\n", result.stderr)

    print(f"Saved: {OUTPUT_PDF}")
    for name, df in samples.items():
        print(f"  {name}: {len(df)} grains")


if __name__ == "__main__":
    main()
