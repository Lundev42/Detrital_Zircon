"""Combine Claude9 (AllePrøver), PieClaude3 (pies), Claude10 (YngstePrøver)
into one figure, side-by-side with 3 cm top/bottom margins and 2 cm of
white space on the right reserved for later additions.

Layout (cm):

   ┌──── 3 cm top ─────────────────────────────────────────┐
   │                                                       │
   │  Claude9   PieClaude3   Claude10            (white)   │
   │   15 wide    6 wide      10 wide             2 wide   │
   │   30 tall    30 tall     30 tall                      │
   │                                                       │
   └──── 3 cm bottom ──────────────────────────────────────┘

Total canvas: 33 cm wide × 36 cm tall.

Uses PyMuPDF (fitz) so the merged PDF stays fully vector — no rasterizing
of the source figures.
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf as fitz


PROJECT_DIR = Path(__file__).resolve().parent
ZIRKON_DIR = Path(
    r"C:\Users\vetle\OneDrive - Høgskulen på Vestlandet\7. Bachelor\Zirkondatering"
)
RIKTIGE_DIR = ZIRKON_DIR / "Riktige_figurer"

CLAUDE9_PATH = RIKTIGE_DIR / "Claude9.pdf"   # AllePrøver, 15 x 30 cm
PIE_PATH     = ZIRKON_DIR / "PieClaude3.pdf" # 10 pies,    6 x 30 cm
CLAUDE10_PATH = RIKTIGE_DIR / "Claude10.pdf" # YngstePrøver, 10 x 30 cm

OUTPUT_PREFIX = "Combined"

TOP_CM         = 3.0
BOTTOM_CM      = 3.0
RIGHT_WHITE_CM = 2.0

CLAUDE9_W,  CLAUDE9_H  = 15.0, 30.0
PIE_W,      PIE_H      =  6.0, 30.0
CLAUDE10_W, CLAUDE10_H = 10.0, 30.0


def cm_to_pt(cm: float) -> float:
    return cm * 72.0 / 2.54


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


def main() -> None:
    for p in (CLAUDE9_PATH, PIE_PATH, CLAUDE10_PATH):
        if not p.exists():
            raise FileNotFoundError(p)

    total_w = CLAUDE9_W + PIE_W + CLAUDE10_W + RIGHT_WHITE_CM
    total_h = TOP_CM + max(CLAUDE9_H, PIE_H, CLAUDE10_H) + BOTTOM_CM

    out_doc = fitz.open()
    page = out_doc.new_page(width=cm_to_pt(total_w), height=cm_to_pt(total_h))

    def insert(src_path: Path, x_cm: float, y_cm: float, w_cm: float, h_cm: float) -> None:
        src = fitz.open(src_path)
        rect = fitz.Rect(
            cm_to_pt(x_cm),
            cm_to_pt(y_cm),
            cm_to_pt(x_cm + w_cm),
            cm_to_pt(y_cm + h_cm),
        )
        page.show_pdf_page(rect, src, 0)
        src.close()

    insert(CLAUDE9_PATH,  x_cm=0,                          y_cm=TOP_CM, w_cm=CLAUDE9_W,  h_cm=CLAUDE9_H)
    insert(PIE_PATH,      x_cm=CLAUDE9_W,                  y_cm=TOP_CM, w_cm=PIE_W,      h_cm=PIE_H)
    insert(CLAUDE10_PATH, x_cm=CLAUDE9_W + PIE_W,          y_cm=TOP_CM, w_cm=CLAUDE10_W, h_cm=CLAUDE10_H)

    pdf_path, png_path = next_pair(ZIRKON_DIR)
    out_doc.save(pdf_path)

    # Render the same page to PNG at ~300 dpi
    dpi_scale = 300.0 / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi_scale, dpi_scale), alpha=False)
    pix.save(png_path)

    out_doc.close()
    print(f"Saved: {pdf_path.name}")
    print(f"Saved: {png_path.name}")


if __name__ == "__main__":
    main()
