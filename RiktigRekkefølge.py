"""Wrapper that runs RiktigRekkefølge.R.

The figure is built by RiktigRekkefølge.R, which calls detzrcr's own
plot_dens_hist() (the function defined in detzrcr-master/R/plotting.R).
This Python file just lets you launch the same job from a Python shell
via `python RiktigRekkefølge.py`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
R_SCRIPT = PROJECT_DIR / "RiktigRekkefølge.R"


def find_rscript() -> Path:
    on_path = shutil.which("Rscript")
    if on_path:
        return Path(on_path)
    for r_root in Path(r"C:\Program Files\R").glob("R-*"):
        candidate = r_root / "bin" / "Rscript.exe"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate Rscript.exe.")


def main() -> None:
    rscript = find_rscript()
    result = subprocess.run(
        [str(rscript), "--encoding=UTF-8", str(R_SCRIPT)],
        cwd=str(PROJECT_DIR),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
