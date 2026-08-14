"""Committed 250-fold synthetic benchmark script for IsoFold.

Evaluates foldclass.geometry accuracy across all 5 Ramsay classes (1A, 1B, 1C, 2, 3)
with N=50 synthetic folds per class (250 total) using a deterministic random seed (42).
Evaluates both 'left' and 'right' limbs independently.

Outputs a clean Markdown confusion table, per-class mean +/- std of recovered R,
and an alpha_span distribution summary.

KNOWN LIMITATION: amplitude_ratio in [1.0, 1.4] caps the max attainable tangent
angle at arctan(amplitude_ratio) = 45-54.5deg, which combined with
ALPHA_MIN_DEG=20 leaves many folds short of MIN_ALPHA_SPAN_DEG=30 -- most
folds get REFUSED (not misclassified) rather than classified at all
(~70-80% refusal rate at time of writing). Off-diagonal accuracy on what
*does* classify is clean (0 misclassifications). Widening amplitude_ratio
to reach full alpha coverage was tried and reverted: at amplitude_ratio >=
1.6 two new problems appear -- (1) a real, noise-free bias where Class 1B
(R=1.0 exactly by construction) gets fit as R~1.05-1.10 and misclassified
as 1A, traced to SPLINE_SMOOTHING_RATIO not generalizing to higher
curvature; (2) the pipeline becomes fragile to any realistic pixel noise
(>=1.0px breaks phi-monotonicity regardless of smoothing -- see
tools/sweep.py). Both need real design work (curvature-adaptive smoothing,
possibly revisiting MIN_ALPHA_SPAN_DEG/ALPHA_MAX_DEG against what real
photo-traced folds can attain) before the amplitude_ratio range here can
be safely widened. Tracked as follow-up, not blocking the core-v1.0 freeze.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import numpy as np

from foldclass import config
from foldclass import geometry as geo
from foldclass import synthetic as syn


def run_benchmark(n_per_class: int = 50, seed: int = 42, verbose: bool = True) -> dict:
    rng = np.random.default_rng(seed)
    classes = [
        ("1A", 1.5),
        ("1B", 1.0),
        ("1C", 0.5),
        ("2", 0.0),
        ("3", -0.5),
    ]

    limbs = ["left", "right"]
    # Matrix structure: matrix[limb][true_class][pred_class]
    matrix = {l: defaultdict(lambda: defaultdict(int)) for l in limbs}
    r_recovered = {l: defaultdict(list) for l in limbs}
    alpha_spans = defaultdict(list)
    failures = defaultdict(int)

    for true_label, target_R in classes:
        for i in range(n_per_class):
            t0 = float(rng.uniform(18.0, 32.0))
            amp = float(rng.uniform(1.0, 1.4))
            width = float(rng.uniform(1.8, 2.2))
            scale = float(rng.uniform(80.0, 120.0))

            fold = syn.generate(
                R=target_R,
                t0=t0,
                scale=scale,
                amplitude_ratio=amp,
                half_width_rad=width,
                n_points=400,
            )

            sm = config.SPLINE_SMOOTHING_RATIO * len(fold.outer_xy)

            try:
                outer = geo.fit_arc(fold.outer_xy, smoothing=sm)
                inner = geo.fit_arc(fold.inner_xy, smoothing=sm)
                ref_o, ref_i = syn._endpoint_ref_angle(outer), syn._endpoint_ref_angle(inner)
                s_ho, s_hi = geo.find_hinge(outer, ref_o), geo.find_hinge(inner, ref_i)
                sep = geo.typical_separation(outer, inner, s_ho, s_hi)
                axis_vec = geo.xy_at(inner, s_hi) - geo.xy_at(outer, s_ho)
                axis_norm = float(np.linalg.norm(axis_vec))
                axial = geo.Line(point=geo.xy_at(outer, s_ho), direction=axis_vec / axis_norm)

                alphas_rad = np.radians(
                    np.arange(config.ALPHA_MIN_DEG, config.ALPHA_MAX_DEG + 1e-6, config.ALPHA_STEP_DEG)
                )

                ref_o_hinge = geo.phi_at(outer, s_ho)
                ref_i_hinge = geo.phi_at(inner, s_hi)

                limb_bounds = [
                    ("left", outer.s[0], inner.s[0]),
                    ("right", outer.s[-1], inner.s[-1]),
                ]

                for limb, s_bo, s_bi in limb_bounds:
                    pairs = geo.isogon_pairs(
                        outer, inner, s_ho, s_bo, s_hi, s_bi,
                        ref_o_hinge, ref_i_hinge, axial, alphas_rad, limb=limb, separation=sep
                    )
                    if len(pairs) < 3:
                        matrix[limb][true_label]["FAILED"] += 1
                        continue

                    span = np.degrees(max(p.alpha for p in pairs) - min(p.alpha for p in pairs))
                    alpha_spans[true_label].append(span)

                    fit = geo.fit_thickness_law(pairs, separation=sep)
                    cls_res = geo.classify(fit, span, len(pairs))
                    pred = cls_res.fold_class if cls_res.fold_class is not None else "REFUSED"

                    matrix[limb][true_label][pred] += 1
                    r_recovered[limb][true_label].append(fit.R)

            except Exception as e:
                failures[true_label] += 1

    if verbose:
        print_results(n_per_class, seed, matrix, r_recovered, alpha_spans, failures)

    return {
        "matrix": matrix,
        "r_recovered": r_recovered,
        "alpha_spans": alpha_spans,
        "failures": failures,
    }


def print_results(n_per_class, seed, matrix, r_recovered, alpha_spans, failures):
    print(f"\n================================================================================")
    print(f"  ISOFOLD {n_per_class*5}-FOLD SYNTHETIC BENCHMARK RESULTS (Seed={seed})")
    print(f"================================================================================\n")

    labels = ["1A", "1B", "1C", "2", "3", "REFUSED", "FAILED"]

    for limb in ["left", "right"]:
        print(f"--- LIMB: {limb.upper()} ---")
        header = f"True Class | " + " | ".join(f"{l:>7}" for l in labels) + " | Mean Recovered R (+/- std)"
        print(header)
        print("-" * len(header))
        for true_label in ["1A", "1B", "1C", "2", "3"]:
            row = [f"{true_label:>10} |"]
            for pred in labels[:-1]:
                row.append(f"{matrix[limb][true_label][pred]:>7}")
            row.append(f"{matrix[limb][true_label]['FAILED']:>7}")
            r_arr = r_recovered[limb][true_label]
            r_str = f"{np.mean(r_arr):.3f} +/- {np.std(r_arr):.3f}" if r_arr else "N/A"
            row.append(f"| {r_str}")
            print(" | ".join(row[:-1]) + f" | {row[-1]}")
        print()

    print("--- ALPHA SPAN DISTRIBUTION ---")
    for true_label in ["1A", "1B", "1C", "2", "3"]:
        spans = alpha_spans[true_label]
        if spans:
            p25, p50, p75 = np.percentile(spans, [25, 50, 75])
            print(f"  Class {true_label:>2}: Min={min(spans):.1f} deg, 25%={p25:.1f} deg, Median={p50:.1f} deg, 75%={p75:.1f} deg, Max={max(spans):.1f} deg")
    print("================================================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Run IsoFold synthetic benchmark.")
    parser.add_argument("-n", "--n-per-class", type=int, default=50, help="Folds per class (default: 50)")
    parser.add_argument("-s", "--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()
    run_benchmark(n_per_class=args.n_per_class, seed=args.seed)


if __name__ == "__main__":
    main()
