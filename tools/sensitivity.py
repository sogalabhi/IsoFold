"""Scale-invariant sensitivity study for IsoFold.

Sweeps relative noise ratio (sigma / t0) across varying layer thicknesses (t0 in {15, 25, 50, 100} px)
and noise levels (sigma in {0.5, 1.0, 2.0, 3.0, 5.0, 8.0} px).

Tracks:
1. R-recovery error |R_rec - R_true|
2. Ramsay Class flip rate
3. Spurious inflection count (noise wiggles breaking reference angle detection)

Establishes the minimum reliable layer thickness threshold for app UI guidance.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import numpy as np

from foldclass import config
from foldclass import geometry as geo
from foldclass import synthetic as syn


def run_sensitivity_study(n_folds_per_cell: int = 10, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    t0_values = [15.0, 25.0, 40.0, 60.0]

    sigma_values = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]
    target_classes = [("1B", 1.0), ("2", 0.0), ("1C", 0.5)]

    r_errors = defaultdict(lambda: defaultdict(list))
    class_flips = defaultdict(lambda: defaultdict(int))
    spurious_inflections = defaultdict(lambda: defaultdict(int))
    total_trials = defaultdict(lambda: defaultdict(int))

    for target_label, target_R in target_classes:
        for t0 in t0_values:
            for sigma in sigma_values:
                rel_noise = sigma / t0
                for fold_idx in range(n_folds_per_cell):
                    total_trials[t0][sigma] += 1
                    amp = float(rng.uniform(1.1, 1.4))
                    width = float(rng.uniform(1.6, 1.8))
                    fold = syn.generate(R=target_R, t0=t0, amplitude_ratio=amp, half_width_rad=width)

                    # Perturb boundaries
                    outer_p = syn.perturb_boundary(fold.outer_xy, sigma=sigma, seed=fold_idx * 1000 + int(sigma*10) + int(t0))
                    inner_p = syn.perturb_boundary(fold.inner_xy, sigma=sigma, seed=fold_idx * 1000 + int(sigma*10) + int(t0) + 1)

                    try:
                        outer_arc = geo.fit_arc(outer_p)
                        inner_arc = geo.fit_arc(inner_p)


                        # Check for spurious inflections on outer/inner arcs (true count for single-hinge arc = 0)
                        infl_o = geo.find_inflections(outer_arc)
                        infl_i = geo.find_inflections(inner_arc)
                        if len(infl_o) > 0 or len(infl_i) > 0:
                            spurious_inflections[t0][sigma] += 1

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
                            span = np.degrees(max(p.alpha for p in pairs) - min(p.alpha for p in pairs))
                            fit = geo.fit_thickness_law(pairs, separation=sep)
                            cls_res = geo.classify(fit, span, len(pairs))

                            r_errors[t0][sigma].append(abs(fit.R - target_R))
                            if cls_res.fold_class != target_label and cls_res.fold_class is not None:
                                class_flips[t0][sigma] += 1

                    except Exception:
                        class_flips[t0][sigma] += 1

    print("\n================================================================================")
    print("  SCALE-INVARIANT SENSITIVITY & NOISE ROBUSTNESS ANALYSIS")
    print("================================================================================\n")

    print("--- 1. Class Flip Rate vs Layer Thickness (t0) and Boundary Noise (sigma) ---")
    header = f"t0 (px) \\ Sigma (px) | " + " | ".join(f"{s:5.1f}px" for s in sigma_values)
    print(header)
    print("-" * len(header))
    for t0 in t0_values:
        row = [f"    t0 = {t0:4.0f} px   |"]
        for sigma in sigma_values:
            flips = class_flips[t0][sigma]
            tot = total_trials[t0][sigma]
            pct = (flips / tot) * 100.0 if tot > 0 else 0.0
            row.append(f"{flips:2d}/{tot:<2d} ({pct:4.0f}%)")
        print(" | ".join(row))
    print()

    print("--- 2. Spurious Inflection Count vs Layer Thickness (t0) and Noise (sigma) ---")
    header = f"t0 (px) \\ Sigma (px) | " + " | ".join(f"{s:5.1f}px" for s in sigma_values)
    print(header)
    print("-" * len(header))
    for t0 in t0_values:
        row = [f"    t0 = {t0:4.0f} px   |"]
        for sigma in sigma_values:
            sp = spurious_inflections[t0][sigma]
            tot = total_trials[t0][sigma]
            row.append(f"{sp:3d}/{tot:<3d}")
        print(" | ".join(row))
    print()

    print("--- 3. Mean |R_rec - R_true| vs Relative Noise Ratio (sigma / t0) ---")
    print(f"{'t0 (px)':>8} | {'Sigma (px)':>10} | {'sigma / t0':>12} | {'Mean |delta R|':>14} | {'Class Flips':>12}")
    print("-" * 65)
    for t0 in t0_values:
        for sigma in sigma_values:
            rel = sigma / t0
            errs = r_errors[t0][sigma]
            mean_e = np.mean(errs) if errs else float("nan")
            flips = class_flips[t0][sigma]
            tot = total_trials[t0][sigma]
            print(f"{t0:8.0f} | {sigma:10.1f} | {rel:12.4f} | {mean_e:14.4f} | {flips:2d}/{tot:<2d}")

    # Determine critical sigma / t0 threshold (where class flip rate <= 5%)
    crit_ratio = 0.10
    for t0 in t0_values:
        for sigma in sigma_values:
            if sigma == 0:
                continue
            rel = sigma / t0
            flips = class_flips[t0][sigma]
            tot = total_trials[t0][sigma]
            if flips / max(tot, 1) > 0.05:
                if rel > 0:
                    crit_ratio = min(crit_ratio, rel)

    crit_ratio = max(crit_ratio, 0.01)
    print(f"\n--> EMPIRICAL CRITICAL RELATIVE NOISE THRESHOLD: sigma / t0 <= {crit_ratio:.3f}")
    print(f"--> RECOMMENDED MINIMUM LAYER THICKNESS (for sigma=1.5px trace jitter): t0 >= {1.5 / crit_ratio:.1f} px\n")

    print("================================================================================\n")

    return {"r_errors": r_errors, "class_flips": class_flips, "spurious_inflections": spurious_inflections}


def main():
    parser = argparse.ArgumentParser(description="Run scale-invariant sensitivity study.")
    parser.add_argument("-n", "--n-folds", type=int, default=10, help="Folds per cell (default: 10)")
    parser.add_argument("-s", "--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()
    run_sensitivity_study(n_folds_per_cell=args.n_folds, seed=args.seed)


if __name__ == "__main__":
    main()
