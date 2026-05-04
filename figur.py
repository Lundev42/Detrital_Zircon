from __future__ import annotations

import csv
import math
import re
from collections import OrderedDict
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parent

FULL_X_MIN = 480
FULL_X_MAX = 3100
FULL_BIN_WIDTH = 50
FULL_BAND_WIDTH = 30

YOUNG_X_MIN = 480
YOUNG_X_MAX = 750
YOUNG_BIN_WIDTH = 10
YOUNG_BAND_WIDTH = 5

FIG_WIDTH = 15
FIG_HEIGHT = 30

OUTPUT_PREFIX = "Codex"
MIN_OUTPUT_INDEX = 10

GROUP_GAP_AFTER_SAMPLE = "SK25-2"
SAMPLE_GROUPS = OrderedDict(
    [
        ("Gulagruppen", ["163706", "EM28", "SK25-2"]),
        (
            "Funnsjøgruppen",
            ["DG12", "AK_121", "119037", "GM34", "DG27", "DGA14_MN_121", "AK001"],
        ),
    ]
)
GROUP_COLORS = {
    "Gulagruppen": ("#a7eb82", "#1a1a1a"),
    "Funnsjøgruppen": ("#91522d", "#ffffff"),
}

AgePredicate = Callable[[float], bool]
AGE_GROUPS: tuple[tuple[str, str, str, AgePredicate], ...] = (
    ("archean", "Arkeisk (>2400 Ma)", "#CC8181", lambda age: age > 2400),
    (
        "paleo_meso",
        "Paleo- til Mesoproterozoisk (2100-900 Ma)",
        "#6895C1",
        lambda age: 900 <= age <= 2100,
    ),
    (
        "neo_cambrian",
        "Neoproterozoisk til Kambrisk (750-480)",
        "#7EBC8E",
        lambda age: 480 <= age <= 750,
    ),
)


def first_existing_path(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def resolve_csv_path() -> Path:
    local_csvs = sorted(PROJECT_DIR.glob("Alle_Zirkon*.csv"))
    if local_csvs:
        return local_csvs[0]

    candidates: list[Path] = []
    for root in Path.home().glob("OneDrive*Vestlandet"):
        candidates.extend((root / "7. Bachelor" / "Litteratur" / "Detrital_zircon_data").glob("Alle_Zirkon*.csv"))

    csv_path = first_existing_path(candidates)
    if csv_path is None:
        raise FileNotFoundError("Could not find Alle_Zirkon*.csv in the project or OneDrive data folder.")
    return csv_path


def resolve_output_dir() -> Path:
    for root in Path.home().glob("OneDrive*Vestlandet"):
        output_dir = root / "7. Bachelor" / "Zirkondatering" / "figur"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    output_dir = PROJECT_DIR / "figur"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def next_output_paths(output_dir: Path) -> tuple[Path, Path]:
    pattern = re.compile(rf"^{re.escape(OUTPUT_PREFIX)}(\d+)\.(?:png|pdf)$", re.IGNORECASE)
    used_indices: set[int] = set()

    for path in output_dir.glob(f"{OUTPUT_PREFIX}*"):
        match = pattern.match(path.name)
        if match:
            used_indices.add(int(match.group(1)))

    next_index = max([MIN_OUTPUT_INDEX - 1, *used_indices]) + 1
    stem = f"{OUTPUT_PREFIX}{next_index}"
    return output_dir / f"{stem}.pdf", output_dir / f"{stem}.png"


def read_ages_by_sample(csv_path: Path) -> OrderedDict[str, list[float]]:
    samples: OrderedDict[str, list[float]] = OrderedDict()

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")
        for row in reader:
            sample = row["sample"].strip()
            age_text = row["age"].strip().replace(",", ".")
            if not sample or not age_text:
                continue

            try:
                age = float(age_text)
            except ValueError:
                continue

            samples.setdefault(sample, []).append(age)

    return samples


def kde_count_curve(
    ages: np.ndarray,
    x_values: np.ndarray,
    bin_width: float,
    band_width: float,
) -> np.ndarray:
    if ages.size == 0:
        return np.zeros_like(x_values)

    scaled_distance = (x_values[:, None] - ages[None, :]) / band_width
    kernels = np.exp(-0.5 * scaled_distance**2)
    density_sum = kernels.sum(axis=1) / (band_width * math.sqrt(2 * math.pi))
    return density_sum * bin_width


def save_rgb_png(source_path: Path) -> None:
    with Image.open(source_path) as image:
        image.convert("RGB").save(source_path, format="PNG")


def grouped_counts(ages: list[float]) -> list[int]:
    counts: list[int] = []
    for _, _, _, predicate in AGE_GROUPS:
        counts.append(sum(1 for age in ages if predicate(age)))
    return counts


def add_histogram_kde(
    ax: plt.Axes,
    ages: np.ndarray,
    x_min: int,
    x_max: int,
    bin_width: int,
    band_width: int,
    *,
    fixed_y_max: float | None = None,
) -> None:
    bin_start = math.floor(x_min / bin_width) * bin_width
    bins = np.arange(bin_start, x_max + bin_width, bin_width)
    x_values = np.linspace(x_min, x_max, 1600)
    counts, edges = np.histogram(ages, bins=bins)
    kde_y = kde_count_curve(ages, x_values, bin_width, band_width)

    ax.bar(
        edges[:-1],
        counts,
        width=np.diff(edges),
        align="edge",
        color="#aeb3b7",
        edgecolor="#eeeeee",
        linewidth=1.35,
    )
    ax.plot(x_values, kde_y, color="#2a2a2a", linewidth=1.65)

    y_max = fixed_y_max
    if y_max is None:
        y_max = max(float(counts.max(initial=0)), float(kde_y.max(initial=0)))
        if y_max <= 0:
            y_max = 1.0

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-0.05 * y_max, 1.05 * y_max)
    ax.set_facecolor("white")
    ax.grid(False)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.tick_params(labelsize=12)
    ax.tick_params(axis="x", labelrotation=0)
    for label in ax.get_xticklabels():
        label.set_rotation(0)
        label.set_ha("center")


def annotate_pie_percentages(
    ax: plt.Axes,
    wedges: list,
    values: list[int],
    *,
    total: int,
) -> None:
    outside_labels: list[tuple[int, object, str, float]] = []

    for group_index, (wedge, value) in enumerate(zip(wedges, values)):
        if value <= 0 or total <= 0:
            continue

        percent = value / total * 100
        label = f"{percent:.0f}%"
        angle = math.radians((wedge.theta1 + wedge.theta2) / 2)

        if percent >= 6:
            radius = 0.62
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            ax.text(x, y, label, ha="center", va="center", fontsize=13, color="#111111")
            continue

        outside_labels.append((group_index, wedge, label, angle))

    for group_index, wedge, label, angle in outside_labels:
        edge_x = 1.14 * math.cos(angle)
        edge_y = 1.14 * math.sin(angle)

        # Place outside labels biased horizontally for readability
        label_x = 1.24 * math.cos(angle)
        label_y = 1.24 * math.sin(angle)

        ax.annotate(
            label,
            xy=(edge_x, edge_y),
            xytext=(label_x, label_y),
            ha="center",
            va="center",
            fontsize=12,
            color="#111111",
            annotation_clip=False,
            arrowprops={
                "arrowstyle": "-",
                "color": "#333333",
                "linewidth": 0.8,
                "shrinkA": 0,
                "shrinkB": 0,
            },
        )


def add_pie(ax: plt.Axes, ages: list[float]) -> None:
    values = grouped_counts(ages)
    colors = [color for _, _, color, _ in AGE_GROUPS]
    total = sum(values)

    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=True,
        radius=1.18,
        wedgeprops={"edgecolor": "white", "linewidth": 1.1},
    )
    annotate_pie_percentages(ax, wedges, values, total=total)
    ax.set_aspect("equal")
    ax.set_xlim(-1.55, 1.55)
    ax.set_ylim(-1.45, 1.45)
    ax.axis("off")


def style_strip(
    ax: plt.Axes,
    label: str,
    *,
    fontsize: int = 12,
    facecolor: str = "#d9d9d9",
    text_color: str = "#222222",
    spaced: bool = False,
    weight: str = "normal",
) -> None:
    ax.set_facecolor(facecolor)
    ax.set_xticks([])
    ax.set_yticks([])
    display_label = "  ".join(list(label)) if spaced else label
    ax.text(
        0.5,
        0.5,
        display_label,
        rotation=-90,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=text_color,
        weight=weight,
    )
    for spine in ax.spines.values():
        spine.set_color("#575757")
        spine.set_linewidth(1.2)


def group_for_sample(sample: str) -> str:
    for group_name, group_samples in SAMPLE_GROUPS.items():
        if sample in group_samples:
            return group_name
    raise KeyError(f"Sample {sample!r} is not listed in SAMPLE_GROUPS.")


def add_column_headers(fig: plt.Figure, left_ax: plt.Axes, pie_ax: plt.Axes, right_ax: plt.Axes) -> None:
    left_pos = left_ax.get_position()
    pie_pos = pie_ax.get_position()
    right_pos = right_ax.get_position()

    left_x = (left_pos.x0 + left_pos.x1) / 2
    pie_x = (pie_pos.x0 + pie_pos.x1) / 2
    right_x = (right_pos.x0 + right_pos.x1) / 2

    fig.text(left_x, 0.962, "Aldersfordeling\n(480-3100 Ma)", ha="center", va="top", fontsize=16)
    fig.text(pie_x, 0.965, "Aldersgrupper", ha="center", va="top", fontsize=16)
    fig.text(right_x, 0.962, "Yngste aldersgrupper\n(480-750 Ma)", ha="center", va="top", fontsize=16)

    handles = [Patch(facecolor=color, edgecolor=color) for _, _, color, _ in AGE_GROUPS]
    labels = [label for _, label, _, _ in AGE_GROUPS]
    fig.legend(
        handles,
        labels,
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(pie_x, 0.940),
        bbox_transform=fig.transFigure,
        frameon=False,
        fontsize=11.5,
        handlelength=1.1,
        handleheight=1.1,
        columnspacing=1.2,
        borderaxespad=0.0,
    )


def plot_age_groups(samples: OrderedDict[str, list[float]]) -> tuple[Path, Path]:
    sample_names = list(samples.keys())
    n_samples = len(sample_names)
    gap_after_index = sample_names.index(GROUP_GAP_AFTER_SAMPLE)
    grid_rows = n_samples + 1
    sample_to_grid_row: dict[str, int] = {}

    grid_row = 0
    for index, sample in enumerate(sample_names):
        sample_to_grid_row[sample] = grid_row
        grid_row += 1
        if index == gap_after_index:
            grid_row += 1

    height_ratios = [1.0] * grid_rows
    height_ratios[gap_after_index + 1] = 0.38

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": "#575757",
            "axes.linewidth": 1.2,
            "xtick.color": "#555555",
            "ytick.color": "#555555",
            "xtick.major.width": 1.35,
            "ytick.major.width": 1.35,
            "xtick.major.size": 4.5,
            "ytick.major.size": 4.5,
        }
    )

    fig = plt.figure(figsize=(FIG_WIDTH, FIG_HEIGHT))
    # columns: full | strip-left | pie | young | strip-right | group-box
    grid = fig.add_gridspec(
        nrows=grid_rows,
        ncols=6,
        height_ratios=height_ratios,
        width_ratios=[11.4, 1.05, 5.2, 7.2, 1.05, 1.4],
        hspace=0.06,
        wspace=0.05,
    )

    full_x_ticks = [FULL_X_MIN, *range(700, FULL_X_MAX + 1, 200)]
    young_x_ticks = np.arange(YOUNG_X_MIN, YOUNG_X_MAX + 1, 30)
    young_fixed_y_max = 8.0

    full_axes: list[plt.Axes] = []
    young_axes: list[plt.Axes] = []
    pie_axes: list[plt.Axes] = []
    left_strip_axes: list[plt.Axes] = []
    right_strip_axes: list[plt.Axes] = []

    def inset_xticklabels(ax: plt.Axes) -> None:
        labels = ax.get_xticklabels()
        if not labels:
            return
        labels[0].set_ha("left")
        labels[-1].set_ha("right")
        for lab in labels[1:-1]:
            lab.set_ha("center")

    for index, sample in enumerate(sample_names):
        row = sample_to_grid_row[sample]
        full_ax = fig.add_subplot(grid[row, 0])
        left_strip_ax = fig.add_subplot(grid[row, 1])
        pie_ax = fig.add_subplot(grid[row, 2])
        young_ax = fig.add_subplot(grid[row, 3])
        right_strip_ax = fig.add_subplot(grid[row, 4])

        full_axes.append(full_ax)
        young_axes.append(young_ax)
        pie_axes.append(pie_ax)
        left_strip_axes.append(left_strip_ax)
        right_strip_axes.append(right_strip_ax)

        ages = np.array(samples[sample], dtype=float)
        young_ages = ages[(ages >= YOUNG_X_MIN) & (ages <= YOUNG_X_MAX)]

        add_histogram_kde(full_ax, ages, FULL_X_MIN, FULL_X_MAX, FULL_BIN_WIDTH, FULL_BAND_WIDTH)
        add_histogram_kde(
            young_ax,
            young_ages,
            YOUNG_X_MIN,
            YOUNG_X_MAX,
            YOUNG_BIN_WIDTH,
            YOUNG_BAND_WIDTH,
            fixed_y_max=young_fixed_y_max,
        )
        add_pie(pie_ax, samples[sample])
        style_strip(left_strip_ax, sample, fontsize=12)
        style_strip(right_strip_ax, sample, fontsize=12)

        show_x_labels = index in {gap_after_index, n_samples - 1}
        for ax, ticks in ((full_ax, full_x_ticks), (young_ax, young_x_ticks)):
            ax.set_xticks(ticks)
            if show_x_labels:
                ax.tick_params(axis="x", labelbottom=True)
                ax.set_xlabel("Age (Ma)", fontsize=13, labelpad=5)
                inset_xticklabels(ax)
            else:
                ax.tick_params(axis="x", labelbottom=False)

        full_ax.tick_params(axis="x", labelsize=10)
        young_ax.tick_params(axis="x", labelsize=11)

    # Group boxes anchored against the right sample strip (snug, no dead space)
    group_axes_map: dict[str, plt.Axes] = {}
    for group_name, group_samples in SAMPLE_GROUPS.items():
        first_row = sample_to_grid_row[group_samples[0]]
        last_row = sample_to_grid_row[group_samples[-1]]
        group_ax = fig.add_subplot(grid[first_row : last_row + 1, 5])
        face, text_col = GROUP_COLORS[group_name]
        style_strip(
            group_ax,
            group_name,
            fontsize=18,
            facecolor=face,
            text_color=text_col,
            spaced=True,
            weight="bold",
        )
        group_axes_map[group_name] = group_ax

    fig.subplots_adjust(left=0.06, right=0.965, bottom=0.045, top=0.925)
    fig.canvas.draw()
    add_column_headers(fig, full_axes[0], pie_axes[0], young_axes[0])

    # One "Count" label on the far left per sample group
    for group_name, group_samples in SAMPLE_GROUPS.items():
        first_ax = full_axes[sample_names.index(group_samples[0])]
        last_ax = full_axes[sample_names.index(group_samples[-1])]
        p1 = first_ax.get_position()
        p2 = last_ax.get_position()
        y_mid = (p1.y1 + p2.y0) / 2
        fig.text(
            0.018,
            y_mid,
            "Count",
            rotation=90,
            ha="center",
            va="center",
            fontsize=15,
        )

    output_dir = resolve_output_dir()
    pdf_path = output_dir / f"{OUTPUT_PREFIX}18.pdf"
    png_path = output_dir / f"{OUTPUT_PREFIX}18.png"
    fig.savefig(pdf_path, facecolor="white", transparent=False)
    fig.savefig(png_path, dpi=160, facecolor="white", transparent=False)
    save_rgb_png(png_path)
    plt.close(fig)

    return pdf_path, png_path


def main() -> None:
    csv_path = resolve_csv_path()
    samples = read_ages_by_sample(csv_path)
    if not samples:
        raise RuntimeError(f"No samples with ages were found in {csv_path}")

    missing_samples = [
        sample
        for group_samples in SAMPLE_GROUPS.values()
        for sample in group_samples
        if sample not in samples
    ]
    if missing_samples:
        raise RuntimeError(f"These samples are listed for grouping but missing from the CSV: {missing_samples}")

    pdf_path, png_path = plot_age_groups(samples)
    print(f"Read CSV: {csv_path}")
    print(f"Saved PDF: {pdf_path}")
    print(f"Saved PNG: {png_path}")
    print("Sample order:")
    for sample in samples:
        print(f"  {sample} ({group_for_sample(sample)})")


if __name__ == "__main__":
    main()
