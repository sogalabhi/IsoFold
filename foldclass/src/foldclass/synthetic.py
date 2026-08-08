"""Synthetic fold generators — the test harness for geometry.py, not
training data (Readme.md, Critical decision 7). There is no model here to
train; these exist to validate known classes, decouple debugging, choose
the smoothing parameter, and quantify boundary-perturbation sensitivity.

Amplitude and width share a single `scale` factor deliberately (Y = scale
* amplitude_ratio * f(x), X = scale * x): mixing independent scale factors
for X and Y was exactly the bug that produced a near-cusp hinge in the
first hand-rolled smoke test, with radius of curvature far smaller than
the offset distance and a self-intersecting inner arc as a result.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import geometry as geo


@dataclass
class SyntheticFold:
    outer_xy: np.ndarray
    inner_xy: np.ndarray
    t0_true: float
    R_true: float


def base_outer_curve(scale: float = 100.0, amplitude_ratio: float = 1.1,
                      half_width_rad: float = 1.3, n_points: int = 400) -> tuple[np.ndarray, np.ndarray]:
    """A single fold: one hinge at x=0, no curvature sign change within
    (-half_width_rad, half_width_rad) by default, so both limbs run out to
    the trace's own endpoints rather than a second inflection (exercises
    the endpoint-fallback reference angle). Returns (xy, x) — x is kept
    because the analytic tangent angle and normal are simplest to build
    directly from it rather than by re-differencing xy."""
    x = np.linspace(-half_width_rad, half_width_rad, n_points)
    y = -amplitude_ratio * np.cos(x)
    xy = scale * np.column_stack([x, y])
    return xy, x


def _analytic_normal(x: np.ndarray, amplitude_ratio: float) -> np.ndarray:
    """Unit normal of Y = -amplitude_ratio*cos(x), X = x (both in the same
    shared `scale`, which cancels out of the slope). Points towards +y;
    flip the whole construction if the "core" should be on the other side."""
    slope = amplitude_ratio * np.sin(x)  # dY/dX
    nx, ny = -slope, np.ones_like(x)
    norm = np.hypot(nx, ny)
    return np.column_stack([nx / norm, ny / norm])


def _endpoint_ref_angle(arc: geo.Arc) -> float:
    return float(np.arctan2(*(arc.xy[-1] - arc.xy[0])[::-1]))


def make_class_1B(outer_xy: np.ndarray, x: np.ndarray, amplitude_ratio: float, t0: float) -> np.ndarray:
    """Exact parallel/offset curve: constant t0 along the analytic normal
    at every point. Exact because thickness doesn't vary (Readme.md,
    synthetic.py spec)."""
    normal = _analytic_normal(x, amplitude_ratio)
    return outer_xy + t0 * normal


def make_class_2(outer_xy: np.ndarray, t0: float) -> np.ndarray:
    """Exact: translate by a constant vector parallel to the true hinge
    normal (here (0, 1) — the hinge of base_outer_curve is at x=0, where
    the tangent is horizontal by construction, so its normal is vertical).
    Every isogon in the resulting family is that same vector, which is
    exactly why similar folds have T'alpha = 1 (Readme.md, dip isogon
    construction, "Class 2 is the clean anchor")."""
    return outer_xy + np.array([0.0, t0])


def make_variable_R(outer_xy: np.ndarray, x: np.ndarray, amplitude_ratio: float,
                     t0: float, R: float, refine: bool = True, n_iter: int = 3,
                     smoothing: float | None = None) -> np.ndarray:
    """Normal-offset construction for 1A / 1C / 3 (R != 1, R != 0), with
    optional iterative refinement (Readme.md, synthetic.py spec): the
    normal-offset curve is only exactly tangent-parallel for constant
    thickness, so for variable t'_alpha(alpha) the naive offset deviates
    slightly. Refine by measuring the actual t'_alpha with geometry.py's
    own isogon-matching code and correcting.

    Falls back to the unrefined (looser-tolerance) construction if
    refinement can't get a stable hinge/isogon read — this is a synthetic
    generator, not a promise that every combination of R and domain shape
    is well-conditioned."""
    normal = _analytic_normal(x, amplitude_ratio)
    phi_analytic = np.arctan(amplitude_ratio * np.sin(x))
    alpha_x = np.abs(phi_analytic - phi_analytic[np.argmin(np.abs(x))])
    correction = np.ones_like(x)
    if smoothing is None:
        smoothing = 0.01 * len(x)

    def build(corr):
        t_target = t0 * (R + (1 - R) * np.cos(alpha_x))
        return outer_xy + (t_target * corr)[:, None] * normal

    if not refine:
        return build(correction)

    for _ in range(n_iter):
        inner_xy = build(correction)
        try:
            outer_arc = geo.fit_arc(outer_xy, smoothing=smoothing)
            inner_arc = geo.fit_arc(inner_xy, smoothing=smoothing)
            ref_o = _endpoint_ref_angle(outer_arc)
            ref_i = _endpoint_ref_angle(inner_arc)
            s_ho = geo.find_hinge(outer_arc, ref_o)
            s_hi = geo.find_hinge(inner_arc, ref_i)
            sep = geo.typical_separation(outer_arc, inner_arc)
            axis_vec = geo.xy_at(inner_arc, s_hi) - geo.xy_at(outer_arc, s_ho)
            hg = float(np.linalg.norm(axis_vec))
            if not (0.3 * sep < hg < 3.0 * sep):
                break
            axial = geo.Line(point=geo.xy_at(outer_arc, s_ho), direction=axis_vec / hg)

            measured_alpha: list[float] = []
            measured_t: list[float] = []
            for limb, s_bound_o, s_bound_i in (
                ("left", outer_arc.s[0], inner_arc.s[0]),
                ("right", outer_arc.s[-1], inner_arc.s[-1]),
            ):
                alphas = np.radians(np.arange(2.0, 89.0, 2.0))
                pairs = geo.isogon_pairs(outer_arc, inner_arc, s_ho, s_bound_o, s_hi, s_bound_i,
                                          ref_o, ref_i, axial, alphas, limb, separation=sep)
                measured_alpha += [pr.alpha for pr in pairs]
                measured_t += [pr.t for pr in pairs]
            if len(measured_alpha) < 5:
                break
            order = np.argsort(measured_alpha)
            m_alpha = np.array(measured_alpha)[order]
            m_t = np.array(measured_t)[order]
            target_at_measured = t0 * (R + (1 - R) * np.cos(m_alpha))
            ratio_samples = np.clip(target_at_measured / np.maximum(m_t, 1e-6), 0.5, 2.0)
            # Fit a smooth low-order polynomial of ratio vs alpha rather than
            # interpolating the sparse measured points directly: linear
            # interpolation through ~20-40 measurement points put small kinks
            # into the correction field, which under light smoothing (needed
            # for clean synthetics to fit tightly) showed up as genuine
            # non-monotonic phi and tripped the limb-monotonicity assertion.
            poly = np.polyfit(m_alpha, ratio_samples, deg=3)
            ratio_of_alpha = np.clip(np.polyval(poly, alpha_x), 0.5, 2.0)
            correction = np.clip(correction * ratio_of_alpha, 0.3, 3.0)
        except geo.GeometryError:
            break

    return build(correction)


def generate(R: float, t0: float = 25.0, scale: float = 100.0, amplitude_ratio: float = 1.1,
             half_width_rad: float = 1.3, n_points: int = 400, refine: bool = True) -> SyntheticFold:
    """Generate a single-hinge synthetic fold at the given R (Readme.md
    thickness law: t'_alpha = R + (1-R)*cos(alpha)). R=1.0 and R=0.0 use
    the exact constructions (Class 1B, Class 2); everything else uses the
    normal-offset construction with iterative refinement."""
    outer_xy, x = base_outer_curve(scale=scale, amplitude_ratio=amplitude_ratio,
                                    half_width_rad=half_width_rad, n_points=n_points)
    if abs(R - 1.0) < 1e-9:
        inner_xy = make_class_1B(outer_xy, x, amplitude_ratio, t0)
    elif abs(R - 0.0) < 1e-9:
        inner_xy = make_class_2(outer_xy, t0)
    else:
        inner_xy = make_variable_R(outer_xy, x, amplitude_ratio, t0, R, refine=refine)
    return SyntheticFold(outer_xy=outer_xy, inner_xy=inner_xy, t0_true=t0, R_true=R)


def limited_coverage_fold(t0: float = 20.0, scale: float = 100.0) -> SyntheticFold:
    """A fold whose limbs never reach ALPHA_MIN_DEG + MIN_ALPHA_SPAN_DEG of
    dip — the measurable failure signature of a chevron fold (Readme.md,
    Critical decision 6: "alpha jumps from 0 at the hinge to the limb dip
    and stays there"). Used to test that classify() refuses rather than
    reporting a number built on a couple of alpha values."""
    return generate(R=1.0, t0=t0, scale=scale, amplitude_ratio=0.75,
                     half_width_rad=1.4, n_points=400, refine=False)
