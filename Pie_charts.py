"""Pie charts of age-group percentages per sample.

Reads Pie_charts_alder.xlsx, draws one pie per sample in the same order as
the histogram plots (163706 → AK001), stacked as a single column.

Slices start at 12 o'clock and sweep clockwise so the first/oldest group
(Archean) sits in the upper-right quadrant:

    Archean      (>2400 Ma)        #CC8181
    Paleo-Meso   (2100-900 Ma)     #6895C1
    Neo-Cambrian (750-480 Ma)      #7EBC8E

Percentages render inside each slice when it's large enough (>= 7 %), and
outside with a small connecting line otherwise.

Saves PDF + PNG to the Zirkondatering OneDrive folder, auto-numbered.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import openpyxl
from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parent
XLSX_PATH = PROJECT_DIR / "Pie_charts_alder.xlsx"
OUTPUT_DIR = Path(
    r"C:\Users\vetle\OneDrive - Høgskulen på Vestlandet\7. Bachelor\Zirkondatering"
)
OUTPUT_PREFIX = "PieClaude"

# Order matches the histogram column. The xlsx has DG_27 / AK_001 with
# underscores; everything else is identical.
SAMPLE_ORDER_XLSX = [
    "163706",
    "EM28",
    "SK25-2",
    "DG12",
    "AK_121",
    "119037",
    "GM34",
    "DG_27",
    "DGA14_MN_121",
    "AK_001",
]

GROUP_LABELS = [
    "Archean (>2400)",
    "Paleo- to Mesoproterozoic (900-2100)",
    "Neoproterozoic to Cambrian (480-750)",
]
GROUP_COLORS = ["#CC8181", "#6895C1", "#7EBC8E"]

FIG_WIDTH_CM = 6
FIG_HEIGHT_CM = 30
INSIDE_THRESHOLD_PCT = 7.0   # below this, label is drawn outside the slice

LABEL_FONTSIZE = 9
EDGE_COLOR = "white"
EDGE_LINEWIDTH = 0.8


def read_pie_data(xlsx_path: Path) -> dict[str, list[float]]:
    """Returns {sample: [archean_pct, paleo_meso_pct, neo_cambrian_pct]}."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    data: dict[str, list[float]] = {}
    i = 0
    while i < len(rows):
        row = rows[i]
        # Sample header row: (None, sample_name, 'Antall', 'Prosent')
        if (
            len(row) >= 4
            and row[1] is not None
            and row[2] == "Antall"
            and row[3] == "Prosent"
        ):
            sample = str(row[1]).strip()
            pcts: list[float] = []
            for k in range(1, 4):
                cell = rows[i + k][3] if i + k < len(rows) else None
                pcts.append(0.0 if cell is None else float(cell))
            data[sample] = pcts
            i += 5
        else:
            i += 1
    return data


def draw_pie(ax: plt.Axes, percents: list[float]) -> None:
    """Draw one pie. Slices in oldest→youngest order, starting at top."""
    # Keep only non-zero slices but preserve color mapping by index.
    items = [(p, c) for p, c in zip(percents, GROUP_COLORS) if p > 0]
    if not items:
        ax.axis("off")
        return
    values = [p for p, _ in items]
    colors = [c for _, c in items]

    # startangle=90 places the first slice's leading edge at 12 o'clock,
    # counterclock=False sweeps clockwise → first/oldest slice (Archean)
    # ends up in the upper-right quadrant.
    ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        radius=1.0,
        wedgeprops={"edgecolor": EDGE_COLOR, "linewidth": EDGE_LINEWIDTH},
    )

    ax.set_aspect("equal")
    ax.set_xlim(-1.55, 1.55)
    ax.set_ylim(-1.25, 1.25)
    ax.axis("off")


def next_pair(output_dir: Path) -> tuple[Path, Path]:
    pattern = re.compile(rf"^{re.escape(OUTPUT_PREFIX)}(\d+)\.(?:png|pdf)$", re.IGNORECASE)
    used: set[int] = set()
    for p in output_dir.glob(f"{OUTPUT_PREFIX}*"):
        m = pattern.match(p.name)
        if m:
            used.add(int(m.group(1)))
    next_idx = (max(used) + 1) if used else 1
    stem = f"{OUTPUT_PREFIX}{next_idx}"
    return output_dir / f"{stem}.pdf", output_dir / f"{stem}.png"


def save_rgb_png(path: Path) -> None:
    with Image.open(path) as image:
        image.convert("RGB").save(path, format="PNG")


def save_individual_pies(data: dict[str, list[float]]) -> None:
    """Save each pie as its own square PNG: Pie1.png .. Pie10.png."""
    for index, sample in enumerate(SAMPLE_ORDER_XLSX, start=1):
        fig, ax = plt.subplots(figsize=(4 / 2.54, 4 / 2.54))
        draw_pie(ax, data[sample])
        # Tight square bounds — labels were removed, so we only need room
        # for the wedge itself.
        ax.set_xlim(-1.05, 1.05)
        ax.set_ylim(-1.05, 1.05)
        png_path = OUTPUT_DIR / f"Pie{index}.png"
        fig.savefig(png_path, dpi=300, facecolor="white",
                    bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        save_rgb_png(png_path)
        print(f"Saved: {png_path.name}")


def save_individual_pdfs(data: dict[str, list[float]]) -> None:
    """Save each pie as its own PDF, named Pie{N}_{sample}.pdf."""
    for index, sample in enumerate(SAMPLE_ORDER_XLSX, start=1):
        fig, ax = plt.subplots(figsize=(4 / 2.54, 4 / 2.54))
        draw_pie(ax, data[sample])
        ax.set_xlim(-1.05, 1.05)
        ax.set_ylim(-1.05, 1.05)
        pdf_path = OUTPUT_DIR / f"Pie{index}_{sample}.pdf"
        fig.savefig(pdf_path, facecolor="white",
                    bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        print(f"Saved: {pdf_path.name}")


def main() -> None:
    data = read_pie_data(XLSX_PATH)
    missing = [s for s in SAMPLE_ORDER_XLSX if s not in data]
    if missing:
        raise RuntimeError(f"Missing samples in xlsx: {missing}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(
        nrows=len(SAMPLE_ORDER_XLSX),
        ncols=1,
        figsize=(FIG_WIDTH_CM / 2.54, FIG_HEIGHT_CM / 2.54),
    )
    fig.subplots_adjust(left=0.05, right=0.95, top=0.99, bottom=0.01,
                        hspace=0.10)

    for ax, sample in zip(axes, SAMPLE_ORDER_XLSX):
        draw_pie(ax, data[sample])

    pdf_path, png_path = next_pair(OUTPUT_DIR)
    fig.savefig(pdf_path, facecolor="white")
    fig.savefig(png_path, dpi=300, facecolor="white")
    save_rgb_png(png_path)
    plt.close(fig)
    print(f"Saved: {pdf_path.name}")
    print(f"Saved: {png_path.name}")

    save_individual_pies(data)
    save_individual_pdfs(data)


if __name__ == "__main__":
    main()
