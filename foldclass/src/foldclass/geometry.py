"""Curvature-free measurement of the Ramsay dip-isogon construction.

numpy + scipy ONLY. No OpenCV, no matplotlib, no I/O — this module is the
port target for the C++ core next semester (Readme.md, Critical decision
8). Everything works in tangent-angle terms, never curvature, per Critical
decision 1: curvature is a second derivative, and on pixel-derived
contours second derivatives amplify noise catastrophically. Nothing in
Ramsay's construction requires it — see Readme.md domain background and
Critical decision 1 for the full argument.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np
from scipy.interpolate import splev, splprep

from . import config


class GeometryError(RuntimeError):
    """Raised when a self-test / plausibility check on the geometry fails.

    These are the "free self-tests" Readme.md asks for: cheap invariants
    that turn a plausible-looking wrong answer into a loud failure instead
    of a silently wrong class."""


def _angdiff(a: np.ndarray | float, b: np.ndarray | float) -> np.ndarray | float:
    """a - b wrapped into (-pi, pi]."""
    return (a - b + np.pi) % (2 * np.pi) - np.pi


# ---------------------------------------------------------------------------
# Arc: a fitted, arc-length-parameterised boundary curve
# ---------------------------------------------------------------------------

@dataclass
class Arc:
    """A fitted, arc-length-parameterised boundary curve."""
    s: np.ndarray          # arc length samples
    xy: np.ndarray         # (N, 2) coordinates
    phi: np.ndarray        # tangent angle at each sample, radians, unwrapped
    tck: tuple              # underlying spline


def estimate_smoothing(points: np.ndarray) -> float:
    """Estimate optimal spline smoothing factor s from third finite differences of
    ordered boundary points. Third differences isolate high-frequency pixel jitter
    from smooth geometric curvature (O(h^3) ~ 0 for smooth curves), enabling robust,
    noise-adaptive spline fitting without requiring caller-supplied noise parameters."""
    N = len(points)
    if N < 4:
        return config.SPLINE_SMOOTHING_RATIO * N
    d3 = points[3:] - 3.0 * points[2:-1] + 3.0 * points[1:-2] - points[:-3]
    # ||d3||^2 sums two iid noise-driven components, each ~20*sigma^2 * chi2(1);
    # their sum is 20*sigma^2 * chi2(2), whose median is 20*sigma^2 * 2*ln(2).
    # Dividing by that (not by 20) is what makes the median-based estimator
    # unbiased for sigma^2 -- see test_geometry.py::test_sigma_calibration.
    sigma2_est = float(np.median(np.sum(d3 ** 2, axis=1)) / (20.0 * 2.0 * np.log(2.0)))
    return float(max(2.0 * N * sigma2_est, config.SPLINE_SMOOTHING_RATIO * N))




def fit_arc(points: np.ndarray, smoothing: float | None = None, n_samples: int = 800) -> Arc:
    """Fit a smoothing spline to ordered boundary points and resample
    densely. Tangent angles come from the spline's analytic first
    derivative — never from finite differences on pixels (Critical
    decision 1). If smoothing is None, estimates optimal s from boundary
    point third finite differences and auto-adjusts if spurious inflections exist."""

    points = np.asarray(points, dtype=float)
    if len(points) < 4:
        raise ValueError(f"need at least 4 points to fit a cubic spline, got {len(points)}")

    auto_adjust = (smoothing is None)
    if smoothing is None:
        smoothing = estimate_smoothing(points)

    tck, _ = splprep([points[:, 0], points[:, 1]], s=smoothing)
    u = np.linspace(0.0, 1.0, n_samples)
    x, y = splev(u, tck)
    xy = np.column_stack([x, y])
    seg = np.diff(xy, axis=0)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
    dx, dy = splev(u, tck, der=1)
    phi = np.unwrap(np.arctan2(dy, dx))
    arc = Arc(s=s, xy=xy, phi=phi, tck=tck)

    # Inflection-guided auto-smoothing fallback: single hinge limbs should have 0 inflections
    if auto_adjust:
        max_tries = 5
        while len(find_inflections(arc)) > 0 and max_tries > 0:
            smoothing *= 2.0
            tck, _ = splprep([points[:, 0], points[:, 1]], s=smoothing)
            x, y = splev(u, tck)
            xy = np.column_stack([x, y])
            seg = np.diff(xy, axis=0)
            s = np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
            dx, dy = splev(u, tck, der=1)
            phi = np.unwrap(np.arctan2(dy, dx))
            arc = Arc(s=s, xy=xy, phi=phi, tck=tck)
            max_tries -= 1

    return arc




def xy_at(arc: Arc, s_query: float) -> np.ndarray:
    """Interpolated (x, y) at arc-length s_query."""
    return np.array([np.interp(s_query, arc.s, arc.xy[:, 0]),
                      np.interp(s_query, arc.s, arc.xy[:, 1])])


def phi_at(arc: Arc, s_query: float) -> float:
    """Interpolated tangent angle at arc-length s_query."""
    return float(np.interp(s_query, arc.s, arc.phi))


# ---------------------------------------------------------------------------
# Inflections and hinge
# ---------------------------------------------------------------------------

def find_inflections(arc: Arc, min_prominence_deg: float | None = None) -> list[float]:
    """Arc-length positions of local extrema of phi(s), i.e. curvature
    sign changes (Critical decision 1's curvature-free equivalent).

    A candidate must show at least min_prominence_deg of phi swing on
    both the approaching and departing monotonic run, or it is discarded
    as a smoothing wiggle rather than a real inflection. Added after a
    real-photo run where two unfiltered candidates — noise on the traced
    boundary — became the reference angle, which put the hinge on the
    wrong limb entirely."""
    if min_prominence_deg is None:
        min_prominence_deg = config.INFLECTION_MIN_PROMINENCE_DEG
    dphi = np.diff(arc.phi)
    sign = np.sign(dphi)
    sign[sign == 0] = 1
    candidates = np.where(np.diff(sign) != 0)[0] + 1
    if len(candidates) == 0:
        return []
    critical = np.concatenate([[0], candidates, [len(arc.phi) - 1]])
    min_prom = np.radians(min_prominence_deg)
    kept = []
    for i in range(1, len(critical) - 1):
        idx = critical[i]
        swing_prev = abs(arc.phi[idx] - arc.phi[critical[i - 1]])
        swing_next = abs(arc.phi[critical[i + 1]] - arc.phi[idx])
        if swing_prev >= min_prom and swing_next >= min_prom:
            kept.append(float(arc.s[idx]))
    return kept


def find_hinge(arc: Arc, reference_angle: float) -> float:
    """Arc-length position where phi equals reference_angle (modulo pi).

    reference_angle comes from the inflection-to-inflection line when both
    inflections are in frame, otherwise from the Case 1 condition (axial
    trace perpendicular to the surface at the hinge) — see
    find_axial_trace, which drives this via fixed-point iteration."""
    idx = int(np.argmin(np.abs(_angdiff(2.0 * arc.phi, 2.0 * reference_angle))))
    return float(arc.s[idx])


def typical_separation(outer: Arc, inner: Arc,
                        s_hinge_outer: float | None = None,
                        s_hinge_inner: float | None = None,
                        window_frac: float = 0.15,
                        n_probe: int = 200) -> float:
    """Median nearest-neighbour distance from outer samples to the inner
    arc — a robust estimate of the layer's typical thickness. Used as the
    reference scale for the isogon-length guard and the H/G plausibility
    check in find_axial_trace. Added after a real-photo run where H and G
    landed on the same limb: |HG| came out at ~4-6x the true layer
    thickness with nothing to catch it.

    When hinge positions are supplied, restricts the probe to samples
    within window_frac of each arc's total span around its hinge. Without
    this, a fold whose thickness varies a lot along the limb (a strongly
    divergent Class 3, say, approaching zero thickness well out on the
    limb) drags the whole-curve median down to a value that has nothing
    to do with the thickness near the hinge — which is what the isogon
    guard and the H/G check actually care about."""
    outer_xy = outer.xy
    if s_hinge_outer is not None:
        span = outer.s[-1] - outer.s[0]
        w = max(window_frac * span, 1.0)
        m = np.abs(outer.s - s_hinge_outer) <= w
        if m.sum() >= 5:
            outer_xy = outer.xy[m]
    inner_xy = inner.xy
    if s_hinge_inner is not None:
        span = inner.s[-1] - inner.s[0]
        w = max(window_frac * span, 1.0)
        m = np.abs(inner.s - s_hinge_inner) <= w
        if m.sum() >= 5:
            inner_xy = inner.xy[m]
    idx = np.linspace(0, len(outer_xy) - 1, min(len(outer_xy), n_probe)).astype(int)
    d = np.linalg.norm(outer_xy[idx, None, :] - inner_xy[None, :, :], axis=-1)
    return float(np.median(d.min(axis=1)))


# ---------------------------------------------------------------------------
# Axial trace: Hudleston Case 1 fixed-point iteration
# ---------------------------------------------------------------------------

@dataclass
class Line:
    point: np.ndarray
    direction: np.ndarray  # unit vector


def find_axial_trace(outer: Arc, inner: Arc, seed_s_outer: float, seed_s_inner: float,
                      max_iter: int | None = None, tol_deg: float | None = None,
                      separation: float | None = None
                      ) -> tuple[float, float, Line, list[str]]:
    """Hudleston Case 1 fixed-point iteration (Critical decision 4): the
    axial trace direction and the hinge points define each other, so
    neither can be looked up directly.

        1. Seed H0, G0 (from a user tap, typically).
        2. Draw the trial axial trace H0G0.
        3. H1 = point on outer where the tangent is perpendicular to
           H0G0; G1 likewise on inner.
        4. Redraw the trial trace through H1G1, repeat to convergence.

    Falls back — with a warning, not a silent wrong answer — when the
    iteration doesn't converge within max_iter. Always checks |HG| against
    typical_separation before returning: being 4-6x too large or too small
    means H and G are not corresponding hinge points, exactly the failure
    mode a first real-photo run produced.
    """
    if max_iter is None:
        max_iter = config.AXIAL_TRACE_MAX_ITER
    if tol_deg is None:
        tol_deg = config.AXIAL_TRACE_TOL_DEG

    s_h, s_g = seed_s_outer, seed_s_inner
    prev_ref: float | None = None
    warnings: list[str] = []
    converged = False

    for _ in range(max_iter):
        H, G = xy_at(outer, s_h), xy_at(inner, s_g)
        axis = G - H
        norm = np.linalg.norm(axis)
        if norm < 1e-9:
            warnings.append("H and G coincided during the Case 1 iteration")
            break
        axis_angle = float(np.arctan2(axis[1], axis[0]))
        ref_angle = axis_angle + np.pi / 2
        s_h = find_hinge(outer, ref_angle)
        s_g = find_hinge(inner, ref_angle)
        if prev_ref is not None and abs(np.degrees(_angdiff(ref_angle, prev_ref))) < tol_deg:
            converged = True
            break
        prev_ref = ref_angle

    if not converged:
        warnings.append(f"Case 1 iteration did not converge within {max_iter} steps")

    H, G = xy_at(outer, s_h), xy_at(inner, s_g)
    axis = G - H
    hg = float(np.linalg.norm(axis))

    if separation is None:
        separation = typical_separation(outer, inner, s_hinge_outer=s_h, s_hinge_inner=s_g)
    if not (config.HG_SEPARATION_RATIO_MIN * separation < hg < config.HG_SEPARATION_RATIO_MAX * separation):
        raise GeometryError(
            f"|HG| = {hg:.1f}px but the outer/inner arcs are ~{separation:.1f}px "
            "apart -- H and G are not corresponding hinge points"
        )

    axial_dir = axis / hg
    return s_h, s_g, Line(point=H, direction=axial_dir), warnings


# ---------------------------------------------------------------------------
# Dip isogons
# ---------------------------------------------------------------------------

@dataclass
class IsogonPair:
    alpha: float        # radians
    p: np.ndarray
    q: np.ndarray
    t: float              # t_alpha: perpendicular distance between the tangents
    T: float               # T_alpha: intercept along the axial-trace direction
    pq: float                # |p - q|, for diagnostics — NOT t_alpha, see below


def _line_point_distance(p: np.ndarray, q: np.ndarray, d: np.ndarray) -> float:
    """Perpendicular distance from p to the line through q with unit
    direction d. This is t_alpha. It is emphatically not norm(p - q): q is
    found purely by tangent-angle matching, so nothing constrains pq to
    lie along the normal (Readme.md, "implementation trap")."""
    v = p - q
    return abs(v[0] * d[1] - v[1] * d[0])


def _line_intersection_param(p: np.ndarray, a_hat: np.ndarray, q: np.ndarray, d: np.ndarray) -> float:
    """Solve p + u*a_hat = q + v*d for u. This is T_alpha (up to sign): the
    intercept between the two parallel tangents measured along the axial
    trace direction a_hat."""
    A = np.array([[a_hat[0], -d[0]], [a_hat[1], -d[1]]])
    b = q - p
    if abs(np.linalg.det(A)) < 1e-9:
        return float("nan")
    u, _ = np.linalg.solve(A, b)
    return float(u)


def _match_alpha(arc: Arc, s_hinge: float, s_bound: float, ref_angle: float, alpha: float) -> Optional[float]:
    """Find the arc-length position within [s_hinge, s_bound] where
    |phi - ref_angle| == alpha. Uses absolute angular distance from the
    hinge so it works regardless of which side of the hinge s_bound is on
    (Critical decision 3)."""
    lo, hi = sorted([s_hinge, s_bound])
    mask = (arc.s >= lo) & (arc.s <= hi)
    s_sub, phi_sub = arc.s[mask], arc.phi[mask]
    if len(s_sub) < 2:
        return None
    ds = np.abs(s_sub - s_hinge)
    order = np.argsort(ds)
    abs_phi = np.abs(_angdiff(phi_sub[order], ref_angle))
    if np.any(np.diff(abs_phi) < -np.radians(1.0)):
        raise GeometryError(
            "phi is not monotonic within the limb — likely under-smoothed "
            "(Critical decision 3); this assertion doubles as a smoothing diagnostic"
        )
    if alpha > abs_phi[-1]:
        return None
    return float(np.interp(alpha, abs_phi, s_sub[order]))


def isogon_pairs(outer: Arc, inner: Arc,
                  s_hinge_outer: float, s_bound_outer: float,
                  s_hinge_inner: float, s_bound_inner: float,
                  ref_angle_outer: float, ref_angle_inner: float,
                  axial_trace: Line,
                  alphas: np.ndarray,
                  limb: Literal["left", "right"],
                  separation: float | None = None) -> list[IsogonPair]:
    """For each alpha, find p on outer and q on inner where the tangent
    angles match, restricted to the given limb's [hinge, bound] span
    (Critical decision 3 — same-limb only, monotonic phi asserted inside
    _match_alpha). t_alpha is computed as the point-to-line distance
    between the two parallel tangents, never norm(p - q). Pairs where |pq|
    exceeds MAX_ISOGON_LENGTH_FACTOR times the typical outer/inner
    separation are dropped as implausible matches."""
    if separation is None:
        separation = typical_separation(outer, inner)
    max_len = config.MAX_ISOGON_LENGTH_FACTOR * separation

    pairs: list[IsogonPair] = []
    for a in alphas:
        s_p = _match_alpha(outer, s_hinge_outer, s_bound_outer, ref_angle_outer, a)
        s_q = _match_alpha(inner, s_hinge_inner, s_bound_inner, ref_angle_inner, a)
        if s_p is None or s_q is None:
            continue
        p, q = xy_at(outer, s_p), xy_at(inner, s_q)
        phi_p = phi_at(outer, s_p)
        d = np.array([np.cos(phi_p), np.sin(phi_p)])
        pq_len = float(np.linalg.norm(p - q))
        if pq_len > max_len:
            continue
        t_a = _line_point_distance(p, q, d)
        if t_a > pq_len + 1e-6:
            raise GeometryError(
                f"t_alpha ({t_a:.3f}) > |pq| ({pq_len:.3f}) at alpha={np.degrees(a):.1f} deg "
                "-- this is a projection and can never happen; the geometry is wrong"
            )
        T_a = abs(_line_intersection_param(p, axial_trace.direction, q, d))
        pairs.append(IsogonPair(alpha=float(a), p=p, q=q, t=t_a, T=T_a, pq=pq_len))
    return pairs


def t_prime(pairs: list[IsogonPair], t0: float) -> np.ndarray:
    """Pointwise normalised orthogonal thickness, for the t'alpha(alpha)
    diagnostic plot only (Ghosh Fig. 12.24). Not used for classification —
    see fit_thickness_law."""
    return np.array([pr.t for pr in pairs]) / t0


# ---------------------------------------------------------------------------
# Joint t0/R fit (Critical decision 2)
# ---------------------------------------------------------------------------

@dataclass
class ThicknessFit:
    """Joint fit t_alpha = A + B*cos(alpha) over one limb's isogon pairs
    (Ramsay eq. 12.1, reparameterised so t0 and R come from the same fit
    instead of t0 being measured first and R computed by division)."""
    A: float
    B: float
    t0: float             # = A + B
    R: float                # = A / (A + B)
    sigma_R: float            # delta-method estimate — a LOWER BOUND, see Readme.md
    residuals: np.ndarray


def fit_thickness_law(pairs: list[IsogonPair], separation: float | None = None) -> ThicknessFit:
    """Linear least-squares fit of t_alpha = A + B*cos(alpha).

    Checks: Class 1B (t_alpha constant = t0) gives A=t0, B=0 -> R=1.
    Class 2 (t_alpha = t0*cos(alpha)) gives A=0, B=t0 -> R=0.

    Raises if the fitted t0 is implausibly small relative to the typical
    outer/inner separation — the signature of a hinge-matching failure
    (H and G on the wrong limb) rather than a real thin layer: R = A/(A+B)
    blows up when the fit is dividing by near-zero t0."""
    if len(pairs) < 3:
        raise GeometryError(f"only {len(pairs)} isogon pairs -- need at least 3 to fit t0 and R")
    alphas = np.array([pr.alpha for pr in pairs])
    t = np.array([pr.t for pr in pairs])
    X = np.column_stack([np.ones_like(alphas), np.cos(alphas)])
    coef, *_ = np.linalg.lstsq(X, t, rcond=None)
    A, B = coef
    resid = t - X @ coef
    n, k = X.shape
    cov = np.full((2, 2), np.nan)
    if n > k:
        sigma2 = float(np.sum(resid ** 2) / (n - k))
        cov = sigma2 * np.linalg.inv(X.T @ X)

    t0 = float(A + B)
    if separation is not None and t0 <= config.T0_MIN_SEPARATION_FRACTION * separation:
        raise GeometryError(
            f"fitted t0 = {t0:.1f}px is implausibly small next to the "
            f"~{separation:.1f}px outer/inner separation -- the fit is dividing by noise, "
            "not measuring a real layer thickness"
        )
    R = float(A / t0) if t0 != 0 else float("nan")
    dRdA, dRdB = B / t0 ** 2, -A / t0 ** 2
    var_R = dRdA ** 2 * cov[0, 0] + dRdB ** 2 * cov[1, 1] + 2 * dRdA * dRdB * cov[0, 1]
    sigma_R = float(np.sqrt(var_R)) if var_R >= 0 else float("nan")
    return ThicknessFit(A=float(A), B=float(B), t0=t0, R=R, sigma_R=sigma_R, residuals=resid)


# ---------------------------------------------------------------------------
# Hudleston Case 1/2/3 diagnostic (Critical decision 4)
# ---------------------------------------------------------------------------

@dataclass
class CaseDiagnostic:
    beta: float   # fitted axial-trace offset angle, radians
    case: int      # 1 or 2 by CASE2_BETA_THRESHOLD_DEG; Case 3 is not detected here


def case_diagnostic(pairs: list[IsogonPair]) -> CaseDiagnostic:
    """Fit the isogon self-test residual (t_alpha/T_alpha - cos(alpha))
    against sin(alpha), forced through the origin, to recover the
    axial-trace offset beta:

        t_alpha/T_alpha - cos(alpha) ~= -beta * sin(alpha)     (small beta)

    NOT a constant-offset check — the failure signature vanishes at the
    hinge (O(beta^2) there) and grows with sin(alpha) away from it. A flat
    residual-mean check would miss this signature entirely."""
    usable = [pr for pr in pairs if pr.T > 1e-6 and not np.isnan(pr.T)]
    if len(usable) < 2:
        return CaseDiagnostic(beta=float("nan"), case=1)
    alphas = np.array([pr.alpha for pr in usable])
    resid = np.array([pr.t / pr.T - np.cos(pr.alpha) for pr in usable])
    s = np.sin(alphas)
    denom = float(np.sum(s ** 2))
    beta = float(-np.sum(resid * s) / denom) if denom > 0 else float("nan")
    case = 2 if abs(np.degrees(beta)) >= config.CASE2_BETA_THRESHOLD_DEG else 1
    return CaseDiagnostic(beta=beta, case=case)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

@dataclass
class ClassResult:
    r_mean: float
    r_std: float
    fold_class: str | None      # None when coverage check fails or R is ambiguous
    alpha_span: float
    n_samples: int
    fit: ThicknessFit
    warnings: list[str] = field(default_factory=list)


def classify(fit: ThicknessFit, alpha_span_deg: float, n_samples: int) -> ClassResult:
    """Assign a class from a ThicknessFit.

    Returns fold_class=None with a warning when alpha_span_deg is below
    MIN_ALPHA_SPAN_DEG (the chevron guard, Critical decision 6), or when
    sigma_R leaves R within R_AMBIGUITY_SIGMA of the 1B/2 boundaries —
    reporting "ambiguous" instead of forcing a label onto a measurement
    that can't support one."""
    warnings: list[str] = []

    if alpha_span_deg < config.MIN_ALPHA_SPAN_DEG:
        warnings.append(
            f"sharp-hinged fold; alpha span {alpha_span_deg:.1f} deg < "
            f"{config.MIN_ALPHA_SPAN_DEG} deg — dip isogon method poorly constrained"
        )
        return ClassResult(r_mean=fit.R, r_std=fit.sigma_R, fold_class=None,
                            alpha_span=alpha_span_deg, n_samples=n_samples,
                            fit=fit, warnings=warnings)

    R, sigma_R = fit.R, fit.sigma_R
    fold_class: str | None = None
    window = config.R_MIN_AMBIGUITY_WINDOW
    if not np.isnan(sigma_R):
        window = max(config.R_AMBIGUITY_SIGMA * sigma_R, config.R_MIN_AMBIGUITY_WINDOW)
    if abs(R - 1.0) < window:
        fold_class = "1B"
    elif abs(R - 0.0) < window:
        fold_class = "2"
    if fold_class is None:
        if R > 1.0:
            fold_class = "1A"
        elif 0.0 < R < 1.0:
            fold_class = "1C"
        elif R < 0.0:
            fold_class = "3"
        else:
            warnings.append("R exactly at a class boundary with no usable sigma_R")

    return ClassResult(r_mean=R, r_std=sigma_R, fold_class=fold_class,
                        alpha_span=alpha_span_deg, n_samples=n_samples,
                        fit=fit, warnings=warnings)
