"""Empirical spline smoothing parameter sweep script for IsoFold.

Evaluates candidate spline smoothing factors (s / N ratio) against synthetic
fold boundaries perturbed by realistic pixel noise (sigma in [0.5, 3.0] px).

Finds the optimal smoothing factor that minimizes R-recovery error while
eliminating non-monotonic phi wiggles (spurious inflection noise).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import numpy as np

from foldclass import config
from foldclass import geometry as geo
from foldclass import synthetic as syn


def run_sweep(n_folds: int = 15, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    smoothing_ratios = np.array([0.01, 0.05, 0.1, 0.15, 0.2, 0.5, 1.0])
    noise_sigmas = [0.0, 0.5, 1.0, 2.0]

    r_errors = defaultdict(lambda: defaultdict(list))
    monotonicity_failures = defaultdict(lambda: defaultdict(int))
    total_evals = defaultdict(lambda: defaultdict(int))

    test_targets = [1.0, 0.0, 0.5]  # 1B, 2, 1C

    for target_R in test_targets:
        for fold_idx in range(n_folds):
            t0 = float(rng.uniform(20.0, 30.0))
            amp = float(rng.uniform(1.1, 1.4))
            fold = syn.generate(R=target_R, t0=t0, amplitude_ratio=amp, half_width_rad=1.6)

            for sigma in noise_sigmas:
                outer_p = syn.perturb_boundary(fold.outer_xy, sigma=sigma, seed=fold_idx * 100 + int(sigma * 10))
                inner_p = syn.perturb_boundary(fold.inner_xy, sigma=sigma, seed=fold_idx * 100 + int(sigma * 10) + 1)
                N_o, N_i = len(outer_p), len(inner_p)

                for ratio in smoothing_ratios:
                    # For sigma > 0, scale smoothing as s = ratio * N * max(sigma^2, 1.0)
                    scale_fac = max(sigma ** 2, 1.0) if sigma > 0 else 1.0
                    s_o = ratio * N_o * scale_fac
                    s_i = ratio * N_i * scale_fac
                    total_evals[sigma][ratio] += 1

                    try:
                        outer_arc = geo.fit_arc(outer_p, smoothing=s_o)
                        inner_arc = geo.fit_arc(inner_p, smoothing=s_i)

                        ref_o, ref_i = syn._endpoint_ref_angle(outer_arc), syn._endpoint_ref_angle(inner_arc)
                        s_ho, s_hi = geo.find_hinge(outer_arc, ref_o), geo.find_hinge(inner_arc, ref_i)
                        sep = geo.typical_separation(outer_arc, inner_arc, s_ho, s_hi)
                        axis_vec = geo.xy_at(inner_arc, s_hi) - geo.xy_at(outer_arc, s_ho)
                        axial = geo.Line(point=geo.xy_at(outer_arc, s_ho), direction=axis_vec / np.linalg.norm(axis_vec))

                        alphas_rad = np.radians(np.arange(config.ALPHA_MIN_DEG, config.ALPHA_MAX_DEG + 1e-6, config.ALPHA_STEP_DEG))
                        ref_o_hinge = geo.phi_at(outer_arc, s_ho)
                        ref_i_hinge = geo.phi_at(inner_arc, s_hi)

                        pairs = geo.isogon_pairs(
                            outer_arc, inner_arc, s_ho, outer_arc.s[-1], s_hi, inner_arc.s[-1],
                            ref_o_hinge, ref_i_hinge, axial, alphas_rad, limb="right", separation=sep
                        )

                        if len(pairs) >= 3:
                            fit = geo.fit_thickness_law(pairs, separation=sep)
                            r_errors[sigma][ratio].append(abs(fit.R - target_R))

                    except geo.GeometryError as e:
                        if "not monotonic" in str(e):
                            monotonicity_failures[sigma][ratio] += 1

    print("\n================================================================================")
    print(f"  NOISE-COUPLED SPLINE SMOOTHING PARAMETER SWEEP RESULTS")
    print(f"================================================================================\n")

    print("--- R-Recovery Mean Error |R_rec - R_true| vs Noise Multiplier k = s / (N * sigma^2) ---")
    header = f"Sigma (px) | " + " | ".join(f"k={r:5.2f}" for r in smoothing_ratios)
    print(header)
    print("-" * len(header))
    for sigma in noise_sigmas:
        row = [f"{sigma:9.1f} |"]
        for ratio in smoothing_ratios:
            errs = r_errors[sigma][ratio]
            if errs:
                row.append(f"{np.mean(errs):7.4f}")
            else:
                row.append("    N/A")
        print(" | ".join(row))
    print()

    print("--- Monotonicity Assertion Failures vs Noise Multiplier k = s / (N * sigma^2) ---")
    header = f"Sigma (px) | " + " | ".join(f"k={r:5.2f}" for r in smoothing_ratios)
    print(header)
    print("-" * len(header))
    for sigma in noise_sigmas:
        row = [f"{sigma:9.1f} |"]
        for ratio in smoothing_ratios:
            fails = monotonicity_failures[sigma][ratio]
            tot = total_evals[sigma][ratio]
            row.append(f"{fails:2d}/{tot:<2d}")
        print(" | ".join(row))
    print("================================================================================\n")

    return {"r_errors": r_errors, "failures": monotonicity_failures}



def main():
    parser = argparse.ArgumentParser(description="Run noise-coupled spline smoothing sweep.")
    parser.add_argument("-n", "--n-folds", type=int, default=15, help="Folds per target (default: 15)")
    parser.add_argument("-s", "--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()
    run_sweep(n_folds=args.n_folds, seed=args.seed)


if __name__ == "__main__":
    main()
