"""CLI runner for automated fold classification and publication diagram generation.

Usage Examples:
    # Full analysis with publication multi-panel diagram
    python tools/run.py test-fold.png

    # Highlight specific dip angles (e.g. 20, 40, 60 deg) on both limbs
    python tools/run.py test-fold.png --angles 20,40,60

    # Highlight 30 deg dip isogon on LEFT limb only, hiding background isogons
    python tools/run.py test-fold.png --angles 30 --limb left --clean
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from foldclass import geometry as geo
from foldclass.debug import debug_pipeline
from foldclass.plots import plot_annotated_fold, plot_publication_figure


def process_image_cli(img_path: Path,
                      output_dir: Path = Path("traces"),
                      angles: list[float] | None = None,
                      limb: str = "both",
                      clean: bool = False,
                      output_file: str | None = None,
                      smoothing: float | None = None) -> None:
    output_dir.mkdir(exist_ok=True)
    stem = img_path.stem

    outer_csv = output_dir / f"{stem}_outer.csv"
    inner_csv = output_dir / f"{stem}_inner.csv"

    if not outer_csv.exists() or not inner_csv.exists():
        raise SystemExit(
            f"Error: Trace CSV files for '{img_path.name}' not found in '{output_dir}'.\n"
            f"Please run 'python tools/trace.py {img_path.name}' first to trace the layer boundaries."
        )

    print(f"Loading traces: {outer_csv} and {inner_csv}")
    outer_pts = np.loadtxt(outer_csv, delimiter=",", skiprows=1)
    inner_pts = np.loadtxt(inner_csv, delimiter=",", skiprows=1)

    img = plt.imread(img_path)

    # Seed hinge at nose (min y point)
    outer_arc = geo.fit_arc(outer_pts, smoothing=len(outer_pts)*4.0)
    inner_arc = geo.fit_arc(inner_pts, smoothing=len(inner_pts)*4.0)

    s_ho_seed = float(outer_arc.s[np.argmin(outer_arc.xy[:, 1])])
    s_hi_seed = float(inner_arc.s[np.argmin(inner_arc.xy[:, 1])])
    seed_hinge = (s_ho_seed, s_hi_seed)

    sm_o = smoothing if smoothing is not None else len(outer_pts) * 10.0
    sm_i = smoothing if smoothing is not None else len(inner_pts) * 10.0

    debug_png = output_dir / f"{stem}_debug.png"
    results = debug_pipeline(outer_pts, inner_pts, smoothing_o=sm_o, smoothing_i=sm_i,
                             seed_hinge=seed_hinge, save_path=str(debug_png))

    # Parse limbs choice
    limbs_to_show = None if limb.lower() == "both" else [limb.lower()]

    annotated_png = Path(output_file) if output_file else output_dir / f"{stem}_annotated.png"
    publication_png = output_dir / f"{stem}_publication.png"

    plot_annotated_fold(
        img, results,
        output_path=str(annotated_png),
        highlight_alphas_deg=angles,
        hide_other_isogons=clean,
        limbs_to_show=limbs_to_show
    )

    plot_publication_figure(img, results, output_path=str(publication_png))

    print("\n=======================================================")
    print(f"  PROCESSING COMPLETE FOR {img_path.name}")
    print("=======================================================")
    print(f"  Hinge Separation |HG|: {results['hg_dist']:.1f} px")
    for l_name in ["left", "right"]:
        if l_name in results["fits"]:
            fit = results["fits"][l_name]
            cls = results["classes"][l_name]
            print(f"  {l_name.capitalize()} Limb: t0={fit.t0:.1f}px, R={fit.R:.3f} +/- {fit.sigma_R:.3f} (Class {cls.fold_class})")
    print(f"  Highlighted Angles: {angles if angles else 'Default Range'}")
    print(f"  Selected Limb(s):   {limb.capitalize()}")
    print(f"  Clean Mode (Hidden Background): {clean}")
    print(f"  Output Annotated Overlay:   {annotated_png}")
    print(f"  Output Publication Diagram: {publication_png}")
    print("=======================================================\n")


def parse_angles(angles_str: str | None) -> list[float] | None:
    if not angles_str:
        return None
    try:
        return [float(a.strip()) for a in angles_str.split(",") if a.strip()]
    except ValueError:
        raise SystemExit(f"Error: Invalid --angles input '{angles_str}'. Provide comma-separated numbers (e.g. 20,40,60).")


def main():
    parser = argparse.ArgumentParser(description="CLI fold geometry runner.")
    parser.add_argument("image", nargs="?", default="test-fold.png", help="Path to input fold image")
    parser.add_argument("-a", "--angles", type=str, default=None,
                        help="Comma-separated dip angles to highlight (e.g. '20,40,60' or '30')")
    parser.add_argument("-l", "--limb", choices=["left", "right", "both"], default="both",
                        help="Limb selection: 'left', 'right', or 'both' (default: both)")
    parser.add_argument("-c", "--clean", action="store_true",
                        help="Clean mode: hide non-selected background isogons")
    parser.add_argument("-o", "--output", type=str, default=None, help="Custom output image path")
    parser.add_argument("--output-dir", default="traces", help="Directory containing CSV traces and output diagrams")
    parser.add_argument("--smoothing", type=float, default=None, help="Explicit spline smoothing factor")

    args = parser.parse_args()

    angles_list = parse_angles(args.angles)

    process_image_cli(
        Path(args.image),
        output_dir=Path(args.output_dir),
        angles=angles_list,
        limb=args.limb,
        clean=args.clean,
        output_file=args.output,
        smoothing=args.smoothing
    )


if __name__ == "__main__":
    main()
