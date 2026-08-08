"""Interactive click-to-trace tool for fold boundary extraction.

Allows clicking outer (S0) and inner (S1) boundary points and seeding the hinge nose,
saves coordinates to CSV, and automatically generates publication-ready annotated figures.

Usage:
    source .venv/bin/activate
    python tools/trace.py test-fold-2.png
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib
# Use interactive backend when running GUI trace
try:
    matplotlib.use("QtAgg")
except ImportError:
    matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
import numpy as np

from foldclass import config
from foldclass import geometry as geo
from foldclass.debug import debug_pipeline
from foldclass.plots import plot_annotated_fold, plot_publication_figure


def click_points(img: np.ndarray, title: str) -> np.ndarray:
    """Opens matplotlib GUI window for user to click points along a curve."""
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(img)
    ax.set_title(f"{title}\nLeft-click = Add point | Right-click = Undo | Enter = Finish",
                 fontsize=12, fontweight="bold", pad=10)
    pts = plt.ginput(n=-1, timeout=0)
    plt.close(fig)
    pts_arr = np.array(pts)
    if len(pts_arr) < 4 and "hinge" not in title.lower():
        raise SystemExit(f"Error: Clicked only {len(pts_arr)} points for '{title}' — need at least 4 points.")
    return pts_arr


def run_tracing_pipeline(img_path: Path, retrace: bool = False, smoothing: float | None = None) -> None:
    out_dir = Path("traces")
    out_dir.mkdir(exist_ok=True)
    stem = img_path.stem

    img = plt.imread(img_path)

    outer_csv = out_dir / f"{stem}_outer.csv"
    inner_csv = out_dir / f"{stem}_inner.csv"

    # Step 1: Trace Outer Boundary S0
    if outer_csv.exists() and not retrace:
        print(f"Loading existing outer trace: {outer_csv}")
        outer_pts = np.loadtxt(outer_csv, delimiter=",", skiprows=1)
    else:
        print(f"\n--- Click Outer Boundary (S0) for {img_path.name} ---")
        outer_pts = click_points(img, "OUTER boundary (S0, Extrados) — trace along curve")
        np.savetxt(outer_csv, outer_pts, delimiter=",", header="x,y", comments="")
        print(f"Saved {len(outer_pts)} points -> {outer_csv}")

    # Step 2: Trace Inner Boundary S1
    if inner_csv.exists() and not retrace:
        print(f"Loading existing inner trace: {inner_csv}")
        inner_pts = np.loadtxt(inner_csv, delimiter=",", skiprows=1)
    else:
        print(f"\n--- Click Inner Boundary (S1) for {img_path.name} ---")
        inner_pts = click_points(img, "INNER boundary (S1, Intrados) — trace in same direction")
        np.savetxt(inner_csv, inner_pts, delimiter=",", header="x,y", comments="")
        print(f"Saved {len(inner_pts)} points -> {inner_csv}")

    # Step 3: Seed Hinge Point (1 Click near the fold nose)
    print("\n--- Click Hinge Seed (Near Fold Nose) ---")
    hinge_seed_pt = click_points(img, "HINGE SEED: Click 1 point near the fold nose (closure point)")
    if len(hinge_seed_pt) > 0:
        seed_xy = hinge_seed_pt[0]
        # Find arc length seed for outer and inner arcs
        s_o_temp, xy_o_temp, _ = geo.fit_arc(outer_pts, smoothing=len(outer_pts)*4.0)
        s_i_temp, xy_i_temp, _ = geo.fit_arc(inner_pts, smoothing=len(inner_pts)*4.0)
        s_ho_seed = float(s_o_temp[np.argmin(np.linalg.norm(xy_o_temp - seed_xy, axis=1))])
        s_hi_seed = float(s_i_temp[np.argmin(np.linalg.norm(xy_i_temp - seed_xy, axis=1))])
        seed_hinge = (s_ho_seed, s_hi_seed)
        print(f"Seeded hinge nose at arc lengths: outer s={s_ho_seed:.1f}, inner s={s_hi_seed:.1f}")
    else:
        seed_hinge = None

    # Step 4: Run Stage-by-Stage Debug & Geometry Pipeline
    sm_o = smoothing if smoothing is not None else len(outer_pts) * 10.0
    sm_i = smoothing if smoothing is not None else len(inner_pts) * 10.0

    debug_png = out_dir / f"{stem}_debug.png"
    results = debug_pipeline(outer_pts, inner_pts, smoothing_o=sm_o, smoothing_i=sm_i,
                             seed_hinge=seed_hinge, save_path=str(debug_png))

    # Step 5: Output Publication Figures
    annotated_png = out_dir / f"{stem}_annotated.png"
    publication_png = out_dir / f"{stem}_publication.png"

    plot_annotated_fold(img, results, output_path=str(annotated_png))
    plot_publication_figure(img, results, output_path=str(publication_png))

    print("\n=======================================================")
    print(f"  ANALYSIS COMPLETE FOR {img_path.name}")
    print("=======================================================")
    print(f"  Outer Hinge H: {results['H']}")
    print(f"  Inner Hinge G: {results['G']}")
    print(f"  Hinge Layer Thickness |HG|: {results['hg_dist']:.1f} px")
    print(f"  Saved Traces: {outer_csv} and {inner_csv}")
    print(f"  Saved Publication Diagram: {publication_png}")
    print(f"  Saved Annotated Overlay:   {annotated_png}")
    print(f"  Saved 6-Panel Debug Grid:  {debug_png}")
    print("=======================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Interactive click-to-trace tool for fold profile sections.")
    parser.add_argument("image", nargs="?", default="test-fold.png", help="Path to input fold image")
    parser.add_argument("--retrace", action="store_true", help="Force re-clicking points even if CSVs exist")
    parser.add_argument("--smoothing", type=float, default=None, help="Explicit spline smoothing factor s")
    args = parser.parse_args()

    run_tracing_pipeline(Path(args.image), retrace=args.retrace, smoothing=args.smoothing)


if __name__ == "__main__":
    main()
