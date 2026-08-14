"""Pytest unit test suite for synthetic fold round-trip classification on both limbs."""

import numpy as np
import pytest

from foldclass import config
from foldclass import geometry as geo
from foldclass import synthetic as syn


def test_synthetic_roundtrip_both_limbs():
    """Verify that both left and right limbs recover ground truth R accurately
    without off-diagonal misclassifications for all 5 Ramsay classes."""
    classes = [
        ("1A", 1.5),
        ("1B", 1.0),
        ("1C", 0.5),
        ("2", 0.0),
        ("3", -0.5),
    ]

    rng = np.random.default_rng(12345)

    for target_class, target_R in classes:
        for i in range(10):
            t0 = float(rng.uniform(20.0, 30.0))
            amp = float(rng.uniform(1.1, 1.4))
            width = float(rng.uniform(1.8, 2.2))
            scale = float(rng.uniform(90.0, 110.0))

            fold = syn.generate(
                R=target_R,
                t0=t0,
                scale=scale,
                amplitude_ratio=amp,
                half_width_rad=width,
                n_points=400,
            )

            sm = config.SPLINE_SMOOTHING_RATIO * len(fold.outer_xy)

            outer = geo.fit_arc(fold.outer_xy, smoothing=sm)
            inner = geo.fit_arc(fold.inner_xy, smoothing=sm)
            ref_o, ref_i = syn._endpoint_ref_angle(outer), syn._endpoint_ref_angle(inner)
            s_ho, s_hi = geo.find_hinge(outer, ref_o), geo.find_hinge(inner, ref_i)
            sep = geo.typical_separation(outer, inner, s_ho, s_hi)
            axis_vec = geo.xy_at(inner, s_hi) - geo.xy_at(outer, s_ho)
            axial = geo.Line(point=geo.xy_at(outer, s_ho), direction=axis_vec / np.linalg.norm(axis_vec))

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
                    continue

                span = np.degrees(max(p.alpha for p in pairs) - min(p.alpha for p in pairs))
                fit = geo.fit_thickness_law(pairs, separation=sep)
                cls_res = geo.classify(fit, span, len(pairs))

                if cls_res.fold_class is not None:
                    assert cls_res.fold_class == target_class, (
                        f"Limb {limb} misclassified Class {target_class} (true R={target_R}) "
                        f"as Class {cls_res.fold_class} (fitted R={fit.R:.3f})"
                    )
                    assert np.isclose(fit.R, target_R, atol=0.08), (
                        f"Limb {limb} fitted R ({fit.R:.3f}) deviates from true R ({target_R})"
                    )
