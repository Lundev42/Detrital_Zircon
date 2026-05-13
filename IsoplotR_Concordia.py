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

SAMPLES_TO_PLOT = ["AK_001"]
RHO_OVERRIDE = None  # impute correlation coefficient (None to keep data ρ / 0)

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
    "DG12": [
        "DG12-50", "DG12-119", "DG12-88", "DG12-36", "DG12-08",
        "DG12-21", "DG12-11", "DG12-27", "DG12-107", "DG12-04",
        "DG12-23", "DG12-104", "DG12-92", "DG12-82", "DG12-05",
        "DG12-66", "DG12-73", "DG12-35", "DG12-98", "DG12-117",
        "DG12-30", "DG12-33", "DG12-42", "DG12-94", "DG12-76",
        "DG12-47", "DG12-29", "DG12-14", "DG12-72", "DG12-25",
        "DG12-87", "DG12-74", "DG12-102", "DG12-61", "DG12-12",
        "DG12-24", "DG12-32",
    ],
    "GM34": [
        "119028-110", "119028-29", "119028-85", "119028-54",
        "119028-79", "119028-104", "119028-66",
    ],
    "DGA14_MN_121": [
        "DGA14_MN_121-054",
    ],
    "AK_121": [
        "119022-121", "119022-147",
    ],
    "DG27": [
        "119040-15", "119040-11", "119040-25", "119040-129",
    ],
    "AK_001": [
        "197878-142", "197878-81", "197878-85",
    ],
    "EM28": [
        "EM28-28", "EM28-107", "EM28-06", "EM28-17", "EM28-40",
        "EM28-42", "EM28-09", "EM28-114", "EM28-97", "EM28-39",
        "EM28-88", "EM28-61", "EM28-20", "EM28-24", "EM28-49",
        "EM28-71", "EM28-43", "EM28-18", "EM28-83", "EM28-115",
        "EM28-22", "EM28-74", "EM28-94", "EM28-50", "EM28-52",
        "EM28-102", "EM28-30", "EM28-73", "EM28-55", "EM28-96",
        "EM28-98", "EM28-04", "EM28-51", "EM28-112", "EM28-14",
        "EM28-29", "EM28-110", "EM28-46", "EM28-27", "EM28-38",
        "EM28-69", "EM28-76", "EM28-91", "EM28-113", "EM28-60",
        "EM28-63",
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

age_ticks <- c(500, 1000, 1500, 2000, 2500, 3000)

# Override IsoplotR's plotConcordiaLine so tick labels render at the
# bottom-right of each tick (via adj) instead of pos= positions.
custom_plotConcordiaLine <- function(x, lims, pos = NA, type = 1,
                                      col = 'darksalmon', oerr = 3,
                                      exterr = FALSE, ticks = 5, box = TRUE) {{
    if (length(ticks) < 2) ticks <- IsoplotR:::prettier(lims$t, type = type, n = ticks)
    m <- min(lims$t[1], ticks[1])
    M <- max(lims$t[2], utils::tail(ticks, 1))
    nn <- 200
    tt <- IsoplotR:::cseq(max(1, m * 0.05), M * 1.05, type = type, n = nn)
    conc <- matrix(0, nn, 2)
    colnames(conc) <- c('x', 'y')
    md <- IsoplotR:::mediand(x$d)
    for (i in 1:nn) {{
        xy <- IsoplotR:::age_to_concordia_ratios(tt[i], type = type, exterr = exterr, d = md)
        if (exterr) {{
            if (i > 1) oldell <- ell
            ell <- IsoplotR:::ellipse(xy$x[1], xy$x[2], xy$cov, alpha = IsoplotR:::oerr2alpha(oerr))
            if (i > 1) {{
                xycd <- rbind(oldell, ell)
                ii <- grDevices::chull(xycd)
                graphics::polygon(xycd[ii, ], col = col, border = NA)
            }}
        }}
        conc[i, ] <- xy$x
    }}
    graphics::lines(conc[, 'x'], conc[, 'y'], col = col, lwd = 2)
    for (i in seq_along(ticks)) {{
        xy <- IsoplotR:::age_to_concordia_ratios(ticks[i], type = type, exterr = exterr, d = md)
        if (exterr) {{
            ell <- IsoplotR:::ellipse(xy$x[1], xy$x[2], xy$cov, alpha = IsoplotR:::oerr2alpha(oerr))
            graphics::polygon(ell, col = 'white')
        }} else {{
            graphics::points(xy$x[1], xy$x[2], pch = 21, bg = 'white')
        }}
        cw <- graphics::strwidth("0")
        ch <- graphics::strheight("0")
        graphics::text(xy$x[1] + cw * 0.4, xy$x[2] - ch * 0.3,
                       as.character(ticks[i]), adj = c(0, 1))
    }}
    if (box) graphics::box()
}}
assignInNamespace("plotConcordiaLine", custom_plotConcordiaLine, ns = "IsoplotR")

concordia(
    upb,
    type           = 1,
    oerr           = 3,
    ticks          = age_ticks,
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
       title  = " {sample_name}",
       title.adj  = 0,
       title.font = 2,
       title.cex  = 1.15,
       inset  = c(0.01, 0.01),
       pch = 22, pt.bg = c("#7EBC8E80", "#D9534F80"),
       col = c("#2f6f3d", "#8B1A1A"),
       pt.cex = 1.5, cex = 0.8, bty = "n")

invisible(dev.off())
"""


def plot_sample(sample: str, df: pd.DataFrame) -> None:
    df = df.reset_index(drop=True).copy()
    # Auto-detect mislabeled 206Pb/238U columns and invert to 238U/206Pb.
    # 238U/206Pb is typically 1.25-30; 206Pb/238U is 0.03-0.8.
    if df["U238Pb206"].median() < 1.0:
        x = df["U238Pb206"].to_numpy()
        sx = df["errU238Pb206"].to_numpy()
        df["U238Pb206"] = 1.0 / x
        df["errU238Pb206"] = sx / (x ** 2)
        print(f"  Inverted {sample}: column was 206Pb/238U, now 238U/206Pb")
    if RHO_OVERRIDE is not None:
        df["rXY"] = RHO_OVERRIDE
    def _norm(g: str) -> str:
        return str(g).strip().rstrip("-").replace("-", "_")

    disc_names = DISCORDANT_GRAINS.get(sample, [])
    grain_to_idx = {_norm(g): i + 1 for i, g in enumerate(df["grain"])}
    disc_indices: list[int] = []
    missing: list[str] = []
    for name in disc_names:
        key = _norm(name)
        if key in grain_to_idx:
            disc_indices.append(grain_to_idx[key])
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
            sample_name=sample,
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
