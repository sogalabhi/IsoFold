"""Publication-quality visualization for fold classification diagrams.

Generates annotated field photograph overlays matching geological journal figures
(e.g., Hatui & Chattopadhyay / Ghosh), showing bedding traces S0/S1, axial trace S2,
hinge points H/G, dip isogon families, and Ramsay diagnostic field plots.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import matplotlib.pyplot as plt
import numpy as np

from . import geometry as geo


def calculate_interlimb_angle(outer_arc: geo.Arc, s_hinge: float) -> float:
    """Calculates interlimb angle in degrees between maximum dip points on both limbs."""
    mask_l = outer_arc.s < s_hinge
    mask_r = outer_arc.s > s_hinge
    if not np.any(mask_l) or not np.any(mask_r):
        return float("nan")

    phi_l = outer_arc.phi[mask_l][np.argmax(np.abs(geo._angdiff(outer_arc.phi[mask_l], geo.phi_at(outer_arc, s_hinge))))]
    phi_r = outer_arc.phi[mask_r][np.argmax(np.abs(geo._angdiff(outer_arc.phi[mask_r], geo.phi_at(outer_arc, s_hinge))))]

    dip_diff = abs(geo._angdiff(phi_l, phi_r))
    interlimb = np.pi - dip_diff
    return float(np.degrees(interlimb))


def plot_annotated_fold(img: np.ndarray,
                       results: Dict[str, Any],
                       output_path: str = "annotated_fold.png",
                       highlight_alphas_deg: Optional[list[float]] = None,
                       hide_other_isogons: bool = False,
                       limbs_to_show: Optional[list[str]] = None) -> None:
    """Generates publication-quality annotated outcrop photograph figure.

    Args:
        img: Input photograph array.
        results: Results dict from debug_pipeline / geometry analysis.
        output_path: Target save path for output image.
        highlight_alphas_deg: Optional list of specific dip angles (e.g. [20.0, 40.0, 60.0])
            to explicitly draw and label on the diagram.
        hide_other_isogons: If True, hides all non-selected background isogons to reduce congestion.
        limbs_to_show: Optional list of limbs to display (e.g. ['left'], ['right'], or ['left', 'right']).
    """
    fig, ax = plt.subplots(figsize=(10, 8), dpi=200)

    # Background photo
    ax.imshow(img)

    outer_arc: geo.Arc = results["outer_arc"]
    inner_arc: geo.Arc = results["inner_arc"]
    H = results["H"]
    G = results["G"]
    axial_line: geo.Line = results["axial_trace"]
    isogons = results["isogons"]
    fits = results["fits"]
    classes = results["classes"]

    # Filter limbs if limbs_to_show is specified
    if limbs_to_show is not None:
        valid_limbs = [l.lower() for l in limbs_to_show]
        active_isogons = {k: v for k, v in isogons.items() if k in valid_limbs}
    else:
        active_isogons = isogons

    # 1. Traced Bedding Boundaries S0 / S1 (Bold Yellow Lines)
    ax.plot(outer_arc.xy[:, 0], outer_arc.xy[:, 1], color="#FFE600", lw=3.0, label=r"$S_0$ (Extrados)")
    ax.plot(inner_arc.xy[:, 0], inner_arc.xy[:, 1], color="#FFE600", lw=2.5, linestyle="--", label=r"$S_1$ (Intrados)")

    # Labels S0, S1 near mid-limb
    idx_mid_o = len(outer_arc.xy) // 4
    idx_mid_i = len(inner_arc.xy) // 4
    ax.text(outer_arc.xy[idx_mid_o, 0] - 25, outer_arc.xy[idx_mid_o, 1] + 15, r"$S_0$",
            color="#FFE600", fontsize=14, fontweight="bold", bbox=dict(boxstyle="square,pad=0.1", fc="black", ec="none", alpha=0.6))
    ax.text(inner_arc.xy[idx_mid_i, 0] + 15, inner_arc.xy[idx_mid_i, 1] + 15, r"$S_1$",
            color="#FFE600", fontsize=14, fontweight="bold", bbox=dict(boxstyle="square,pad=0.1", fc="black", ec="none", alpha=0.6))

    # 2. Dip Isogons (Thin translucent lines, if not hidden)
    colors = {"left": "#FF3333", "right": "#33CC33"}
    if not hide_other_isogons:
        for limb, pairs in active_isogons.items():
            for pr in pairs[::2]:
                ax.plot([pr.p[0], pr.q[0]], [pr.p[1], pr.q[1]], "-", color=colors[limb], lw=1.0, alpha=0.6)

    # 2b. Highlight specific user-selected dip angles (e.g. 20 deg, 40 deg, 60 deg)
    if highlight_alphas_deg is not None:
        target_rads = [np.radians(a) for a in highlight_alphas_deg]
        highlight_colors = ["#00FFFF", "#FF00FF", "#FFFF00", "#00FF00", "#FF6600"]
        for limb, pairs in active_isogons.items():
            for idx, target_rad in enumerate(target_rads):
                # Find closest isogon pair to target angle
                best_pair = min(pairs, key=lambda pr: abs(pr.alpha - target_rad), default=None)
                if best_pair is not None and abs(best_pair.alpha - target_rad) < np.radians(2.0):
                    p, q = best_pair.p, best_pair.q
                    angle_deg = np.degrees(best_pair.alpha)
                    color = highlight_colors[idx % len(highlight_colors)]

                    # Draw prominent highlighted line
                    ax.plot([p[0], q[0]], [p[1], q[1]], "-", color=color, lw=2.5, alpha=0.95,
                            label=f"Dip Isogon α={angle_deg:.0f}°" if limb == "left" else "")

                    # Label angle text near outer point p
                    mid = (p + q) / 2
                    ax.text(mid[0] + 8, mid[1], f"{angle_deg:.0f}°", color=color, fontsize=10, fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.2", fc="black", ec=color, lw=1.0, alpha=0.85))

    # 3. Axial Trace (Bold Red Line)
    axis_extent = results["typical_separation"] * 2.5
    start_pt = H - axial_line.direction * axis_extent * 0.5
    end_pt = G + axial_line.direction * axis_extent * 1.5
    ax.plot([start_pt[0], end_pt[0]], [start_pt[1], end_pt[1]], color="#FF0000", lw=2.5, label=r"Axial Trace ($S_2$)")
    ax.text(end_pt[0] + 10, end_pt[1], r"$S_2$", color="#FF0000", fontsize=14, fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.1", fc="black", ec="none", alpha=0.6))

    # 4. Hinge Points H & G
    ax.plot(H[0], H[1], "s", color="#FFA500", ms=9, mec="black", mew=1.5, label="H (Outer Hinge)")
    ax.plot(G[0], G[1], "o", color="#00FFFF", ms=9, mec="black", mew=1.5, label="G (Inner Hinge)")

    # Calculate interlimb angle
    interlimb_deg = calculate_interlimb_angle(outer_arc, results["s_hinge_outer"])

    # 5. Publication Summary Callout Box
    r_vals = [fits[l].R for l in fits if l in fits]
    cls_labels = [classes[l].fold_class for l in classes if l in classes and classes[l].fold_class]
    mean_r = float(np.mean(r_vals)) if r_vals else float("nan")
    primary_cls = cls_labels[0] if cls_labels else "Unclassified"

    textstr = (
        f"Ramsay Classification: Class {primary_cls}\n"
        f"Mean R Index: {mean_r:.3f}\n"
        f"Hinge Thickness t₀: {results['hg_dist']:.1f} px\n"
        f"Interlimb Angle: {interlimb_deg:.1f}°"
    )

    ax.text(0.03, 0.95, textstr, transform=ax.transAxes, fontsize=11, fontweight="bold",
            verticalalignment="top", color="white",
            bbox=dict(boxstyle="round,pad=0.5", fc="#111111", ec="#FFA500", lw=1.5, alpha=0.85))

    ax.set_title("Fold Profile Section & Ramsay Dip Isogon Analysis", fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.85, facecolor="#222222", labelcolor="white")
    ax.axis("off")

    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved publication-style annotated image -> {output_path}")


def plot_publication_figure(img: np.ndarray,
                           results: Dict[str, Any],
                           output_path: str = "publication_figure.png") -> None:
    """Generates multi-panel journal figure combining annotated photo and Ramsay t'alpha chart."""
    fig = plt.figure(figsize=(15, 7), dpi=200)

    # Panel A: Annotated Photo
    ax1 = fig.add_subplot(1, 2, 1)
    ax1.imshow(img)

    outer_arc: geo.Arc = results["outer_arc"]
    inner_arc: geo.Arc = results["inner_arc"]
    H = results["H"]
    G = results["G"]
    axial_line: geo.Line = results["axial_trace"]
    isogons = results["isogons"]
    fits = results["fits"]
    classes = results["classes"]

    ax1.plot(outer_arc.xy[:, 0], outer_arc.xy[:, 1], color="#FFE600", lw=2.5, label=r"$S_0$")
    ax1.plot(inner_arc.xy[:, 0], inner_arc.xy[:, 1], color="#FFE600", lw=2.0, linestyle="--", label=r"$S_1$")

    colors = {"left": "#FF3333", "right": "#33CC33"}
    for limb, pairs in isogons.items():
        for pr in pairs[::2]:
            ax1.plot([pr.p[0], pr.q[0]], [pr.p[1], pr.q[1]], "-", color=colors[limb], lw=1.0, alpha=0.7)

    axis_extent = results["typical_separation"] * 2.5
    start_pt = H - axial_line.direction * axis_extent * 0.5
    end_pt = G + axial_line.direction * axis_extent * 1.5
    ax1.plot([start_pt[0], end_pt[0]], [start_pt[1], end_pt[1]], color="#FF0000", lw=2.2, label=r"Axial Trace ($S_2$)")

    ax1.plot(H[0], H[1], "s", color="#FFA500", ms=8, mec="black", label="H (Extrados)")
    ax1.plot(G[0], G[1], "o", color="#00FFFF", ms=8, mec="black", label="G (Intrados)")

    ax1.text(0.03, 0.95, "(a)", transform=ax1.transAxes, fontsize=16, fontweight="bold", color="white",
             bbox=dict(boxstyle="square,pad=0.2", fc="black", ec="none"))

    ax1.set_title("Annotated Fold Outcrop Profile", fontsize=12, fontweight="bold")
    ax1.legend(loc="lower right", fontsize=8, framealpha=0.8)
    ax1.axis("off")

    # Panel B: Ramsay t'alpha Field Diagram
    ax2 = fig.add_subplot(1, 2, 2)
    alpha_dense = np.radians(np.linspace(0.0, 75.0, 100))
    alpha_deg_dense = np.degrees(alpha_dense)

    # Standard Ramsay Class Reference Curves
    ax2.plot(alpha_deg_dense, np.ones_like(alpha_dense), "k--", lw=1.5, label="Class 1B (t'=1)")
    ax2.plot(alpha_deg_dense, np.cos(alpha_dense), "k:", lw=1.5, label="Class 2 (t'=cos α)")

    for limb, fit in fits.items():
        pairs = isogons[limb]
        a_deg = [np.degrees(pr.alpha) for pr in pairs]
        t_prime_val = [pr.t / fit.t0 for pr in pairs]
        ax2.plot(a_deg, t_prime_val, "o", color=colors[limb], ms=6, label=f"{limb.capitalize()} Limb (R={fit.R:.2f})")
        t_fit_prime = (fit.A + fit.B * np.cos(alpha_dense)) / fit.t0
        ax2.plot(alpha_deg_dense, t_fit_prime, "-", color=colors[limb], lw=2.0)

    ax2.text(0.03, 0.95, "(b)", transform=ax2.transAxes, fontsize=16, fontweight="bold", color="black")
    ax2.set_title(r"Ramsay Normalised Thickness Field Diagram $t'_\alpha(\alpha)$", fontsize=12, fontweight="bold")
    ax2.set_xlabel(r"Dip Angle $\alpha$ (degrees)", fontsize=11)
    ax2.set_ylabel(r"Normalised Thickness $t'_\alpha = t_\alpha / t_0$", fontsize=11)
    ax2.set_xlim(0, 75)
    ax2.set_ylim(0.0, 1.4)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.legend(fontsize=9, loc="upper right")

    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved multi-panel publication figure -> {output_path}")
