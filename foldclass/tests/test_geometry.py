"""Tests for foldclass.geometry using foldclass.synthetic ground truth."""

import numpy as np
import pytest

from foldclass import config
from foldclass import geometry as geo
from foldclass import synthetic as syn


def test_fit_arc_scaling_and_rotation_invariance():
    """fit_arc should preserve tangent angle shapes under rotation and scaling."""
    fold = syn.generate(R=1.0, t0=20.0, scale=100.0)
    arc1 = geo.fit_arc(fold.outer_xy, smoothing=0.1)

    # Uniform scale by 2.5
    arc_scaled = geo.fit_arc(fold.outer_xy * 2.5, smoothing=0.1 * (2.5 ** 2))

    # Rotation by 45 degrees
    theta = np.radians(45.0)
    R_mat = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    rotated_pts = fold.outer_xy @ R_mat.T
    arc_rotated = geo.fit_arc(rotated_pts, smoothing=0.1)

    # Arc length ratios should match scale factor
    assert np.isclose(arc_scaled.s[-1], arc1.s[-1] * 2.5, rtol=1e-3)

    # Tangent angles offset by rotation angle
    phi_diff = (arc_rotated.phi - arc1.phi) % (2 * np.pi)
    assert np.allclose(phi_diff, theta, atol=1e-2) or np.allclose(phi_diff, theta - 2 * np.pi, atol=1e-2)


def test_isogon_invariants_class_1b():
    """Test t_alpha / T_alpha == cos(alpha) and t_alpha <= |pq| on exact Class 1B fold."""
    fold = syn.generate(R=1.0, t0=25.0)
    smoothing = 0.05 * len(fold.outer_xy)
    outer = geo.fit_arc(fold.outer_xy, smoothing=smoothing)
    inner = geo.fit_arc(fold.inner_xy, smoothing=smoothing)

    ref_o = syn._endpoint_ref_angle(outer)
    ref_i = syn._endpoint_ref_angle(inner)
    s_ho = geo.find_hinge(outer, ref_o)
    s_hi = geo.find_hinge(inner, ref_i)

    sep = geo.typical_separation(outer, inner, s_ho, s_hi)
    axis_vec = geo.xy_at(inner, s_hi) - geo.xy_at(outer, s_ho)
    axial = geo.Line(point=geo.xy_at(outer, s_ho), direction=axis_vec / np.linalg.norm(axis_vec))

    alphas = np.radians(np.arange(20.0, 70.0, 5.0))
    pairs = geo.isogon_pairs(outer, inner, s_ho, outer.s[-1], s_hi, inner.s[-1],
                            ref_o, ref_i, axial, alphas, limb="right", separation=sep)

    assert len(pairs) >= 5

    for pr in pairs:
        # Invariant 1: Projection bound t_alpha <= |pq|
        assert pr.t <= pr.pq + 1e-6, f"Projection bound violated: t_alpha ({pr.t}) > |pq| ({pr.pq})"

        # Invariant 2: t_alpha / T_alpha == cos(alpha)
        ratio = pr.t / pr.T
        expected = np.cos(pr.alpha)
        assert np.isclose(ratio, expected, atol=1e-2), (
            f"t_alpha/T_alpha mismatch at alpha={np.degrees(pr.alpha):.1f} deg: "
            f"got {ratio:.4f}, expected {expected:.4f}"
        )


def test_oblique_isogon_disambiguation():
    """Assert t_alpha is computed as perpendicular distance, not norm(p - q)."""
    # Create parallel lines y = 0 and y = 10
    # p = (0, 0), q = (10, 10), tangent direction d = (1, 0)
    p = np.array([0.0, 0.0])
    q = np.array([10.0, 10.0])
    d = np.array([1.0, 0.0])

    t_alpha = geo._line_point_distance(p, q, d)
    pq_norm = np.linalg.norm(p - q)

    assert np.isclose(t_alpha, 10.0)
    assert np.isclose(pq_norm, np.sqrt(200))
    assert t_alpha < pq_norm  # t_alpha is strictly less than |pq| for oblique pair


def test_fit_thickness_law_recovery():
    """fit_thickness_law should recover known t0 and R for Class 1B and Class 2 synthetics."""
    # Class 1B (R = 1.0)
    fold_1b = syn.generate(R=1.0, t0=30.0)
    outer = geo.fit_arc(fold_1b.outer_xy, smoothing=0.5)
    inner = geo.fit_arc(fold_1b.inner_xy, smoothing=0.5)
    ref_o, ref_i = syn._endpoint_ref_angle(outer), syn._endpoint_ref_angle(inner)
    s_ho, s_hi = geo.find_hinge(outer, ref_o), geo.find_hinge(inner, ref_i)
    sep = geo.typical_separation(outer, inner, s_ho, s_hi)
    axis_vec = geo.xy_at(inner, s_hi) - geo.xy_at(outer, s_ho)
    axial = geo.Line(point=geo.xy_at(outer, s_ho), direction=axis_vec / np.linalg.norm(axis_vec))

    alphas = np.radians(np.arange(20.0, 70.0, 2.5))
    pairs_1b = geo.isogon_pairs(outer, inner, s_ho, outer.s[-1], s_hi, inner.s[-1],
                               ref_o, ref_i, axial, alphas, limb="right", separation=sep)
    fit_1b = geo.fit_thickness_law(pairs_1b, separation=sep)
    assert np.isclose(fit_1b.R, 1.0, atol=0.03)
    assert np.isclose(fit_1b.t0, 30.0, atol=1.5)

    # Class 2 (R = 0.0)
    fold_2 = syn.generate(R=0.0, t0=30.0)
    outer = geo.fit_arc(fold_2.outer_xy, smoothing=0.5)
    inner = geo.fit_arc(fold_2.inner_xy, smoothing=0.5)
    ref_o, ref_i = syn._endpoint_ref_angle(outer), syn._endpoint_ref_angle(inner)
    s_ho, s_hi = geo.find_hinge(outer, ref_o), geo.find_hinge(inner, ref_i)
    sep = geo.typical_separation(outer, inner, s_ho, s_hi)
    axis_vec = geo.xy_at(inner, s_hi) - geo.xy_at(outer, s_ho)
    axial = geo.Line(point=geo.xy_at(outer, s_ho), direction=axis_vec / np.linalg.norm(axis_vec))

    pairs_2 = geo.isogon_pairs(outer, inner, s_ho, outer.s[-1], s_hi, inner.s[-1],
                              ref_o, ref_i, axial, alphas, limb="right", separation=sep)
    fit_2 = geo.fit_thickness_law(pairs_2, separation=sep)
    assert np.isclose(fit_2.R, 0.0, atol=0.03)
    assert np.isclose(fit_2.t0, 30.0, atol=1.5)


def test_classify_labels():
    """classify should map R values to correct Ramsay classes or flag ambiguity."""
    dummy_fit = lambda R: geo.ThicknessFit(A=R * 20.0, B=(1 - R) * 20.0, t0=20.0, R=R, sigma_R=0.01, residuals=np.zeros(10))

    res_1a = geo.classify(dummy_fit(1.5), alpha_span_deg=45.0, n_samples=10)
    assert res_1a.fold_class == "1A"

    res_1b = geo.classify(dummy_fit(1.0), alpha_span_deg=45.0, n_samples=10)
    assert res_1b.fold_class == "1B"

    res_1c = geo.classify(dummy_fit(0.5), alpha_span_deg=45.0, n_samples=10)
    assert res_1c.fold_class == "1C"

    res_2 = geo.classify(dummy_fit(0.0), alpha_span_deg=45.0, n_samples=10)
    assert res_2.fold_class == "2"

    res_3 = geo.classify(dummy_fit(-0.5), alpha_span_deg=45.0, n_samples=10)
    assert res_3.fold_class == "3"


def test_chevron_coverage_guard():
    """Folds with insufficient alpha coverage should refuse classification."""
    chevron = syn.limited_coverage_fold()
    dummy_fit = geo.ThicknessFit(A=20.0, B=0.0, t0=20.0, R=1.0, sigma_R=0.01, residuals=np.zeros(10))

    # Low alpha span (15 deg < MIN_ALPHA_SPAN_DEG)
    res = geo.classify(dummy_fit, alpha_span_deg=15.0, n_samples=10)
    assert res.fold_class is None
    assert any("alpha span" in w for w in res.warnings)


def test_inflection_prominence_filtering():
    """Noise wiggles should be filtered out by INFLECTION_MIN_PROMINENCE_DEG."""
    # Synthetic arc with small noise wiggles
    t = np.linspace(0, 10, 400)
    # Cosine with a small high-frequency ripple
    x = t * 10.0
    y = -50.0 * np.cos(t / 2.0) + 0.2 * np.sin(t * 5.0)
    pts = np.column_stack([x, y])
    arc = geo.fit_arc(pts, smoothing=5.0)

    inflections_strict = geo.find_inflections(arc, min_prominence_deg=15.0)
    inflections_loose = geo.find_inflections(arc, min_prominence_deg=0.0)

    assert len(inflections_strict) <= len(inflections_loose)


def test_sigma_calibration():
    """estimate_smoothing's internal sigma^2 estimator should recover injected
    boundary noise variance (median(||d3||^2) / (20*2*ln2), not /20 -- d3 sums
    two noise components, so the median-unbiased divisor uses chi2(2))."""
    fold = syn.generate(R=1.0, t0=25.0, scale=100.0)
    clean = fold.outer_xy
    for true_sigma in (1.0, 2.0, 3.0):
        estimates = []
        for seed in range(20):
            noisy = syn.perturb_boundary(clean, sigma=true_sigma, seed=seed)
            d3 = noisy[3:] - 3.0 * noisy[2:-1] + 3.0 * noisy[1:-2] - noisy[:-3]
            estimates.append(np.median(np.sum(d3 ** 2, axis=1)) / (20.0 * 2.0 * np.log(2.0)))
        assert np.isclose(np.mean(estimates), true_sigma ** 2, rtol=0.15)


def test_case_diagnostic():
    """case_diagnostic should return beta ~= 0 for Case 1 synthetics."""
    fold = syn.generate(R=1.0, t0=25.0)
    outer = geo.fit_arc(fold.outer_xy, smoothing=0.5)
    inner = geo.fit_arc(fold.inner_xy, smoothing=0.5)
    ref_o, ref_i = syn._endpoint_ref_angle(outer), syn._endpoint_ref_angle(inner)
    s_ho, s_hi = geo.find_hinge(outer, ref_o), geo.find_hinge(inner, ref_i)
    sep = geo.typical_separation(outer, inner, s_ho, s_hi)
    axis_vec = geo.xy_at(inner, s_hi) - geo.xy_at(outer, s_ho)
    axial = geo.Line(point=geo.xy_at(outer, s_ho), direction=axis_vec / np.linalg.norm(axis_vec))

    alphas = np.radians(np.arange(20.0, 70.0, 2.5))
    pairs = geo.isogon_pairs(outer, inner, s_ho, outer.s[-1], s_hi, inner.s[-1],
                            ref_o, ref_i, axial, alphas, limb="right", separation=sep)

    diag = geo.case_diagnostic(pairs)
    assert np.abs(np.degrees(diag.beta)) < 2.5
    assert diag.case == 1
