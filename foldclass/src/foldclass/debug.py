"""Stage-by-stage inspection pipeline and diagnostic grid visualizer.

Allows running geometry analysis on synthetic folds or real photo traces and
extracting intermediate values at every stage, with optional comparison against
ground truth.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

from . import config
from . import geometry as geo
from .synthetic import SyntheticFold


def debug_pipeline(outer_pts: np.ndarray,
                   inner_pts: np.ndarray,
                   truth: Optional[SyntheticFold] = None,
                   smoothing_o: Optional[float] = None,
                   smoothing_i: Optional[float] = None,
                   seed_hinge: Optional[Tuple[float, float]] = None,
                   save_path: Optional[str] = None) -> Dict[str, Any]:
    """Runs geometry analysis stage-by-stage, collecting all intermediates.

    Args:
        outer_pts: (N, 2) array of outer boundary points.
        inner_pts: (N, 2) array of inner boundary points.
        truth: Optional SyntheticFold containing true t0 and R values.
        smoothing_o: Spline smoothing factor for outer boundary.
        smoothing_i: Spline smoothing factor for inner boundary.
        seed_hinge: Optional (s_outer_seed, s_inner_seed) tuple from user click.
        save_path: Optional file path to save 6-panel diagnostic plot.

    Returns:
        Dict containing intermediate results from each stage and error metrics.
    """
    if smoothing_o is None:
        smoothing_o = 0.05 * len(outer_pts)
    if smoothing_i is None:
        smoothing_i = 0.05 * len(inner_pts)

    # Stage 1: Arc fitting
    outer_arc = geo.fit_arc(outer_pts, smoothing=smoothing_o)
    inner_arc = geo.fit_arc(inner_pts, smoothing=smoothing_i)

    # Stage 2: Inflection detection with prominence filter
    infl_o = geo.find_inflections(outer_arc)
    infl_i = geo.find_inflections(inner_arc)

    # Reference angle determination
    if len(infl_o) >= 2:
        left_b = max([s for s in infl_o if s < outer_arc.s[len(outer_arc.s) // 2]], default=outer_arc.s[0])
        right_b = min([s for s in infl_o if s > outer_arc.s[len(outer_arc.s) // 2]], default=outer_arc.s[-1])
        ref_o = float(np.arctan2(*(geo.xy_at(outer_arc, right_b) - geo.xy_at(outer_arc, left_b))[::-1]))
    else:
        ref_o = float(np.arctan2(*(outer_arc.xy[-1] - outer_arc.xy[0])[::-1]))

    if len(infl_i) >= 2:
        left_b = max([s for s in infl_i if s < inner_arc.s[len(inner_arc.s) // 2]], default=inner_arc.s[0])
        right_b = min([s for s in infl_i if s > inner_arc.s[len(inner_arc.s) // 2]], default=inner_arc.s[-1])
        ref_i = float(np.arctan2(*(geo.xy_at(inner_arc, right_b) - geo.xy_at(inner_arc, left_b))[::-1]))
    else:
        ref_i = float(np.arctan2(*(inner_arc.xy[-1] - inner_arc.xy[0])[::-1]))

    # Stage 3: Hinge & Axial Trace
    if seed_hinge is not None:
        s_ho_seed, s_hi_seed = seed_hinge
    else:
        s_ho_seed = geo.find_hinge(outer_arc, ref_o)
        s_hi_seed = geo.find_hinge(inner_arc, ref_i)

    sep = geo.typical_separation(outer_arc, inner_arc, s_ho_seed, s_hi_seed)

    s_ho, s_hi, axial_trace, warnings = geo.find_axial_trace(
        outer_arc, inner_arc, s_ho_seed, s_hi_seed, separation=sep
    )

    H = geo.xy_at(outer_arc, s_ho)
    G = geo.xy_at(inner_arc, s_hi)
    hg_dist = float(np.linalg.norm(G - H))

    # Stage 4: Isogon Families per limb
    alphas_rad = np.radians(np.arange(config.ALPHA_MIN_DEG, config.ALPHA_MAX_DEG + 1e-6, config.ALPHA_STEP_DEG))

    isogons: Dict[str, list[geo.IsogonPair]] = {}
    fits: Dict[str, geo.ThicknessFit] = {}
    diagnostics: Dict[str, geo.CaseDiagnostic] = {}
    classes: Dict[str, geo.ClassResult] = {}

    def _clamp_limb_bound(arc: geo.Arc, s_hinge: float, s_end: float, max_alpha_deg: float = 75.0) -> float:
        step = 1 if s_end >= s_hinge else -1
        mask = (arc.s >= min(s_hinge, s_end)) & (arc.s <= max(s_hinge, s_end))
        s_sub = arc.s[mask]
        if len(s_sub) < 2:
            return s_end
        if step == -1:
            s_sub = s_sub[::-1]
        ref = geo.phi_at(arc, s_hinge)
        phi_sub = arc.phi[mask] if step == 1 else arc.phi[mask][::-1]
        abs_phi = np.abs(geo._angdiff(phi_sub, ref))
        exceeded = np.where(abs_phi > np.radians(max_alpha_deg))[0]
        if len(exceeded) > 0:
            first_cut = max(exceeded[0] - 1, 0)
            return float(s_sub[first_cut])
        return float(s_sub[-1])

    ref_o_hinge = geo.phi_at(outer_arc, s_ho)
    ref_i_hinge = geo.phi_at(inner_arc, s_hi)

    limbs = [
        ("left", _clamp_limb_bound(outer_arc, s_ho, outer_arc.s[0]), _clamp_limb_bound(inner_arc, s_hi, inner_arc.s[0])),
        ("right", _clamp_limb_bound(outer_arc, s_ho, outer_arc.s[-1]), _clamp_limb_bound(inner_arc, s_hi, inner_arc.s[-1])),
    ]

    for limb, s_bo, s_bi in limbs:
        pairs = geo.isogon_pairs(
            outer_arc, inner_arc, s_ho, s_bo, s_hi, s_bi, ref_o_hinge, ref_i_hinge,
            axial_trace, alphas_rad, limb=limb, separation=sep
        )
        isogons[limb] = pairs
        if len(pairs) >= 3:
            alpha_span = np.degrees(max(p.alpha for p in pairs) - min(p.alpha for p in pairs))
            fit = geo.fit_thickness_law(pairs, separation=sep)
            diag = geo.case_diagnostic(pairs)
            cls_res = geo.classify(fit, alpha_span, len(pairs))
            fits[limb] = fit
            diagnostics[limb] = diag
            classes[limb] = cls_res

    # Stage 5: Compare against truth if supplied
    errors = {}
    if truth is not None:
        r_fits = [fits[l].R for l in fits if l in fits]
        t0_fits = [fits[l].t0 for l in fits if l in fits]
        if r_fits:
            errors["R_error_mean"] = float(np.abs(np.mean(r_fits) - truth.R_true))
            errors["t0_error_mean"] = float(np.abs(np.mean(t0_fits) - truth.t0_true))

    results = {
        "outer_arc": outer_arc,
        "inner_arc": inner_arc,
        "inflections_outer": infl_o,
        "inflections_inner": infl_i,
        "ref_angle_outer": ref_o,
        "ref_angle_inner": ref_i,
        "s_hinge_outer": s_ho,
        "s_hinge_inner": s_hi,
        "H": H,
        "G": G,
        "hg_dist": hg_dist,
        "typical_separation": sep,
        "axial_trace": axial_trace,
        "isogons": isogons,
        "fits": fits,
        "diagnostics": diagnostics,
        "classes": classes,
        "warnings": warnings,
        "errors": errors,
    }

    # Plot 6-panel diagnostic grid if requested or if save_path provided
    if save_path is not None:
        plot_debug_grid(results, truth=truth, save_path=save_path)

    return results


def plot_debug_grid(results: Dict[str, Any],
                    truth: Optional[SyntheticFold] = None,
                    save_path: str = "debug_grid.png") -> None:
    """Plots a 6-panel diagnostic visualization grid of the pipeline stages."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle("Stage-by-Stage Fold Geometry Diagnostics", fontsize=14, fontweight="bold")

    outer_arc: geo.Arc = results["outer_arc"]
    inner_arc: geo.Arc = results["inner_arc"]
    H = results["H"]
    G = results["G"]
    isogons = results["isogons"]
    fits = results["fits"]

    # Panel 1: Fold Trace & Isogons Overlay
    ax1 = axes[0, 0]
    ax1.plot(outer_arc.xy[:, 0], outer_arc.xy[:, 1], "tab:orange", lw=2, label="Outer Arc")
    ax1.plot(inner_arc.xy[:, 0], inner_arc.xy[:, 1], "tab:cyan", lw=2, label="Inner Arc")
    ax1.plot(*H, "s", color="tab:orange", ms=8, mec="k", label="H (Outer Hinge)")
    ax1.plot(*G, "s", color="tab:cyan", ms=8, mec="k", label="G (Inner Hinge)")
    ax1.plot([H[0], G[0]], [H[1], G[1]], "k--", lw=1.5, label="Axial Trace")

    colors = {"left": "tab:red", "right": "tab:green"}
    for limb, pairs in isogons.items():
        for pr in pairs[::2]:
            ax1.plot([pr.p[0], pr.q[0]], [pr.p[1], pr.q[1]], "-", color=colors[limb], lw=0.8, alpha=0.7)

    ax1.set_title("1. Fold Geometry & Dip Isogons")
    ax1.set_aspect("equal")
    ax1.legend(fontsize=8, loc="upper right")

    # Panel 2: phi(s) vs Arc Length s (PRIMARY DIAGNOSTIC)
    ax2 = axes[0, 1]
    ax2.plot(outer_arc.s, np.degrees(outer_arc.phi), "tab:orange", lw=1.5, label="Outer phi(s)")
    ax2.plot(inner_arc.s, np.degrees(inner_arc.phi), "tab:cyan", lw=1.5, label="Inner phi(s)")
    ax2.axvline(results["s_hinge_outer"], color="tab:orange", linestyle="--", alpha=0.7, label="Outer Hinge s")
    ax2.axvline(results["s_hinge_inner"], color="tab:cyan", linestyle="--", alpha=0.7, label="Inner Hinge s")

    for s_val in results["inflections_outer"]:
        ax2.plot(s_val, np.degrees(geo.phi_at(outer_arc, s_val)), "o", color="tab:orange", ms=6, mec="k")
    for s_val in results["inflections_inner"]:
        ax2.plot(s_val, np.degrees(geo.phi_at(inner_arc, s_val)), "o", color="tab:cyan", ms=6, mec="k")

    ax2.set_title("2. Tangent Angle phi(s) vs Arc Length s")
    ax2.set_xlabel("Arc Length s (px)")
    ax2.set_ylabel("phi (deg)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Panel 3: Spline Curvature Proxy dphi/ds vs s
    ax3 = axes[0, 2]
    dphi_ds_o = np.gradient(outer_arc.phi, outer_arc.s)
    dphi_ds_i = np.gradient(inner_arc.phi, inner_arc.s)
    ax3.plot(outer_arc.s, dphi_ds_o, "tab:orange", lw=1.5, label="Outer dphi/ds")
    ax3.plot(inner_arc.s, dphi_ds_i, "tab:cyan", lw=1.5, label="Inner dphi/ds")
    ax3.axhline(0, color="k", linestyle=":", alpha=0.5)
    ax3.set_title("3. Curvature Proxy (dphi/ds)")
    ax3.set_xlabel("Arc Length s (px)")
    ax3.set_ylabel("dphi/ds (rad/px)")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # Panel 4: t_alpha vs alpha & Thickness Fit
    ax4 = axes[1, 0]
    alpha_dense = np.radians(np.linspace(15.0, 75.0, 100))
    for limb, fit in fits.items():
        pairs = isogons[limb]
        a_deg = [np.degrees(pr.alpha) for pr in pairs]
        t_val = [pr.t for pr in pairs]
        ax4.plot(a_deg, t_val, "o", color=colors[limb], label=f"{limb} data")
        t_fit_curve = fit.A + fit.B * np.cos(alpha_dense)
        ax4.plot(np.degrees(alpha_dense), t_fit_curve, "--", color=colors[limb],
                 label=f"{limb} fit (R={fit.R:.2f})")

    ax4.set_title("4. Orthogonal Thickness t_alpha vs alpha")
    ax4.set_xlabel("alpha (deg)")
    ax4.set_ylabel("t_alpha (px)")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    # Panel 5: Normalised Thickness t'alpha vs alpha
    ax5 = axes[1, 1]
    for limb, fit in fits.items():
        pairs = isogons[limb]
        a_deg = [np.degrees(pr.alpha) for pr in pairs]
        t_prime_val = [pr.t / fit.t0 for pr in pairs]
        ax5.plot(a_deg, t_prime_val, "o-", color=colors[limb], label=f"{limb} limb")

    ax5.plot(np.degrees(alpha_dense), np.ones_like(alpha_dense), "k--", alpha=0.5, label="Class 1B (t'=1)")
    ax5.plot(np.degrees(alpha_dense), np.cos(alpha_dense), "k:", alpha=0.5, label="Class 2 (t'=cos alpha)")
    ax5.set_title("5. Ramsay t'alpha Field Diagram")
    ax5.set_xlabel("alpha (deg)")
    ax5.set_ylabel("t'alpha")
    ax5.legend(fontsize=8)
    ax5.grid(True, alpha=0.3)

    # Panel 6: Case Diagnostic Residuals
    ax6 = axes[1, 2]
    for limb, diag in results["diagnostics"].items():
        pairs = isogons[limb]
        usable = [pr for pr in pairs if pr.T > 1e-6 and not np.isnan(pr.T)]
        if usable:
            sin_a = [np.sin(pr.alpha) for pr in usable]
            res = [pr.t / pr.T - np.cos(pr.alpha) for pr in usable]
            ax6.plot(sin_a, res, "o", color=colors[limb], label=f"{limb} (beta={np.degrees(diag.beta):.1f} deg)")
            s_dense = np.linspace(0, 1, 50)
            ax6.plot(s_dense, -diag.beta * s_dense, "--", color=colors[limb])

    ax6.axhline(0, color="k", linestyle=":", alpha=0.5)
    ax6.set_title("6. Axial Trace Case Diagnostic")
    ax6.set_xlabel("sin(alpha)")
    ax6.set_ylabel("Residual (t/T - cos alpha)")
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved diagnostic grid plot -> {save_path}")
