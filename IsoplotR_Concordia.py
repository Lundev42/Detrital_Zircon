from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from Concordia_plots import extract_samples

PROJECT_DIR = Path(__file__).resolve().parent
RSCRIPT = r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe"
OUTPUT_DIR = Path(
    r"C:\Users\vetle\OneDrive - Høgskulen på Vestlandet\7. Bachelor\Zirkondatering"
)

SAMPLES_TO_PLOT = ["119037"]

DISCORDANT_GRAINS = {
    "SK25-2": [
        "SK25-2-85",
        "SK25-2-63",
        "SK25-2-99",
        "SK25-2-89",
        "SK25-2-84",
        "SK25-2-90",
        "SK25-2-61",
        "SK25-2-16",
    ],
    "163706": [
        "163706-89",
        "163706-51",
        "163706-54",
        "163706-69",
        "163706-62",
        "163706-96",
    ],
    "119037": [
        "119037-18",
        "119037-16",
        "119037-12",
        "119037-20",
        "119037-21",
        "119037-24",
        "119037-28",
        "119037-8",
    ],
}


def next_output_path() -> Path:
    pattern = re.compile(r"^IsoplotR_Claude(\d+)\.png$", re.IGNORECASE)
    existing = [
        int(m.group(1))
        for f in OUTPUT_DIR.iterdir()
        if (m := pattern.match(f.name))
    ]
    n = max(existing, default=0) + 1
    return OUTPUT_DIR / f"IsoplotR_Claude{n}.png"


R_TEMPLATE = r"""
suppressWarnings(suppressMessages(library(IsoplotR)))

png(filename = "{png_path}", width = 2400, height = 2400, res = 400, type = "cairo", antialias = "default")

upb <- read.data("{csv_path}", method = "U-Pb", format = 2, ierr = 2)

disc_idx <- c({disc_idx})
if (length(disc_idx) == 0) disc_idx <- NULL

age_ticks <- c(1000, 1500, 2000, 2500, 3000)

concordia(
    upb,
    type           = 1,
    oerr           = 2,
    ticks          = age_ticks,
    pos            = rep(4, length(age_ticks)),
    omit           = disc_idx,
    omit.fill      = "#D9534F80",
    omit.stroke    = "#8B1A1A",
    cutoff.disc    = discfilter(option = 0)
)

n_total <- nrow(upb$x)
n_disc  <- length(disc_idx)
legend("topleft",
       legend = c(sprintf("Concordant (n=%d)", n_total - n_disc),
                  sprintf("Discordant >10%% (n=%d)", n_disc)),
       pch = 22, pt.bg = c("#7EBC8E80", "#D9534F80"),
       col = c("#2f6f3d", "#8B1A1A"),
       pt.cex = 1.5, cex = 0.8, bty = "n")

invisible(dev.off())
"""


def plot_sample(sample: str, df: pd.DataFrame) -> None:
    df = df.reset_index(drop=True)
    disc_names = DISCORDANT_GRAINS.get(sample, [])
    grain_to_idx = {str(g): i + 1 for i, g in enumerate(df["grain"])}
    disc_indices: list[int] = []
    missing: list[str] = []
    for name in disc_names:
        if name in grain_to_idx:
            disc_indices.append(grain_to_idx[name])
        else:
            missing.append(name)
    if missing:
        print(f"  Warning: discordant grains not found in data: {missing}")

    out_png = next_output_path()
    safe = sample.replace("/", "_")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        csv_path = tmp_dir / f"{safe}.csv"
        df[["U238Pb206", "errU238Pb206", "Pb207Pb206", "errPb207Pb206", "rXY"]].to_csv(
            csv_path, index=False
        )

        r_script = R_TEMPLATE.format(
            csv_path=csv_path.as_posix(),
            png_path=out_png.as_posix(),
            disc_idx=", ".join(str(i) for i in disc_indices),
        )
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

    print(f"  Saved: {out_png}  ({len(df)} grains, {len(disc_indices)} discordant)")


def main() -> None:
    samples = extract_samples()
    for sample in SAMPLES_TO_PLOT:
        if sample not in samples:
            print(f"Sample {sample!r} not found. Available: {list(samples)}")
            continue
        print(f"Plotting {sample}...")
        plot_sample(sample, samples[sample])


if __name__ == "__main__":
    main()
