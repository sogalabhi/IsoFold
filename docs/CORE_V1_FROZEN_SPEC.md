# core-v1.0-frozen spec sheet

`foldclass/src/foldclass/geometry.py` and its frozen constants
(`foldclass/src/foldclass/config.py`), as of the tag `core-v1.0-frozen`.
No edits to `geometry.py` after this point except genuine bug fixes.

## Scope of validity — read this before using anything below

**This freeze is validated for fold curvature such that `amplitude_ratio`
(in `synthetic.py`'s generator, and by extension the limb curvature it's a
proxy for) stays at or below ~1.4 — equivalently, a base-curve limb dip up
to ~54°.** Every constant in this document, and the confusion-table/
sensitivity results backing it, were measured inside that range.

Outside it — `amplitude_ratio` roughly 1.6 and up — two specific failures
were characterized (not fixed) during this freeze's investigation:
tangent-matching accuracy degrades under the fixed-budget
`SPLINE_SMOOTHING_RATIO` (a real, noise-free bias, not a coverage
artifact), and the pipeline becomes fragile to realistic pixel noise
regardless of how the smoothing is tuned. See "Known limitations" for the
full mechanism. This is a stated precondition of the freeze, not a
footnote: **do not assume `geometry.py`'s classification behaves reliably
on folds whose curvature falls outside this range** until that's
characterized with real data (build order step 5) and revisited.

## Verification run (pytest + confusion table + sensitivity, one sitting, no edits between)

- `pytest foldclass/tests/` — 10/10 passed, including the new
  `test_sigma_calibration` (item 3 below).
- `benchmarks/confusion_table.py` (250-fold, seed=42) — **0 misclassifications**
  on both limbs across all 5 classes. ~70-80% of folds REFUSED by the
  chevron guard rather than classified — a known limitation of this
  benchmark's `amplitude_ratio` range, documented in the script's
  docstring, not a classification error. See "Known limitations" below.
- `tools/sensitivity.py` — ran clean; empirical critical noise ratio
  `sigma/t0 <= 0.017` (re-verified at n=180 folds/cell and independently
  at n=600 on the single most sensitive cell — 8.2% vs. the study's 9.4%,
  confirming this is a real effect, not small-sample noise). Feeds
  `MIN_LAYER_THICKNESS_PX` below, now reconciled.

## Closeouts resolved before freezing

1. **t0=100 cusp** — confirmed real (not a geometry.py artifact): a
   normal-offset curve self-intersects once the offset exceeds the base
   curve's radius of curvature at the hinge (`scale/amplitude_ratio`).
   Now enforced by `synthetic.generate()` via `CUSP_SAFETY_MARGIN`
   (raises `ValueError` instead of silently building a degenerate fold).
2. **Confusion table** — regenerated against the current file (see run
   above). Confirmed the "0 misclassifications" claim still holds;
   surfaced that most folds are refused rather than classified under
   the benchmark's current curvature range (known limitation, not fixed
   — see below).
3. **sigma2_est calibration** — was biased: summing squared 2D
   third-differences before taking the median follows a scaled chi2(2),
   whose median is `2*ln(2)` times its mean, not the divisor-of-20
   value that assumed a 1D mean-based estimator. Fixed the divisor to
   `20 * 2 * ln(2)`; empirically recovers injected sigma within 15%
   across sigma in {1,2,3}px (`test_sigma_calibration`).

## Frozen constants (`config.py`)

| Constant | Value | Provenance |
|---|---|---|
| `ALPHA_MIN_DEG` | 20.0 | R's denominator (1-cos alpha)->0 near alpha=0; below this an isogon pair is too noisy to trust |
| `ALPHA_MAX_DEG` | 70.0 | Tangent matching gets unreliable close to the inflection point |
| `ALPHA_STEP_DEG` | 2.5 | Sampling step for the alpha sweep building the isogon family |
| `MIN_ALPHA_SPAN_DEG` | 30.0 | Chevron guard: below this spread of recovered alpha, refuse to classify |
| `R_AMBIGUITY_SIGMA` | 2.0 | Min \|R - boundary\|/sigma_R required to commit to 1B/2 vs. reporting ambiguous |
| `R_MIN_AMBIGUITY_WINDOW` | 0.05 | Floor on the ambiguity window when sigma_R is near-zero on a clean fit |
| `MAX_ISOGON_LENGTH_FACTOR` | 3.0 | Reject an isogon pair if \|pq\| exceeds this x the typical outer/inner separation |
| `INFLECTION_MIN_PROMINENCE_DEG` | 15.0 | Min phi swing on both sides of a candidate inflection to count as real, not smoothing wiggle |
| `AXIAL_TRACE_MAX_ITER` | 20 | Cap on the Case 1 fixed-point iteration |
| `AXIAL_TRACE_TOL_DEG` | 0.5 | Convergence tolerance for the same iteration |
| `CASE2_BETA_THRESHOLD_DEG` | 3.0 | Fitted axial-trace offset beta beyond this magnitude reports Case 2, not Case 1 |
| `HG_SEPARATION_RATIO_MIN` | 0.5 | \|HG\| below this x typical separation means H/G are not corresponding hinge points |
| `HG_SEPARATION_RATIO_MAX` | 2.0 | \|HG\| above this x typical separation, same failure mode |
| `T0_MIN_SEPARATION_FRACTION` | 0.3 | Fitted t0 below this fraction of typical separation means the fit is dividing by noise |
| `MIN_LAYER_THICKNESS_PX` | 90.0 | Low-confidence flag threshold. `= 1.5px / 0.017`: the 0.017 critical noise ratio is validated (see run above); the 1.5px assumed trace jitter is not measured yet — recompute once step 5 gives a real number |
| `SPLINE_SMOOTHING_RATIO` | 0.15 | Default s/N ratio from `tools/sweep.py`, tuned against `amplitude_ratio` in [1.1, 1.4] only — see "Scope of validity" above |
| `CUSP_SAFETY_MARGIN` | 0.85 | New (this freeze): `synthetic.generate()` refuses t0 >= this fraction of the hinge radius of curvature |
| `QUARTER_WAVELENGTH_B` | `None` | Unused — reserved for `fourier.py` (step 4, not yet built) |

## Known limitations carried into the freeze (not blocking, tracked as follow-up)

- **Coverage vs. robustness tension at high curvature** (mechanism behind
  the "Scope of validity" boundary above). Widening
  `confusion_table.py`'s `amplitude_ratio` to reach fuller alpha-span
  coverage (fewer REFUSED folds) was tried and reverted. At
  `amplitude_ratio >= 1.6`: (a) a real, noise-free bias appears where
  Class 1B (R=1.0 exactly by construction) fits to R~1.05-1.10 and
  misclassifies as 1A — traced to `SPLINE_SMOOTHING_RATIO` applying the
  same fixed absolute smoothing budget to two arcs with different
  curvature profiles, which distorts their `phi(s)` unequally, so "equal
  fitted tangent angle" stops meaning "true corresponding points" and the
  linear `t_alpha = A + B*cos(alpha)` fit's slope picks up the resulting
  bias; (b) independent of that, the pipeline becomes fragile to any
  realistic pixel noise — sigma >= 1.0px breaks phi-monotonicity
  regardless of smoothing ratio (tested up to s=N). Needs real design work
  (curvature-adaptive smoothing, or revisiting `MIN_ALPHA_SPAN_DEG`/
  `ALPHA_MAX_DEG` against what real photo-traced folds actually attain,
  informed by build order step 5) — not something to retune blindly
  pre-freeze.
- `MIN_LAYER_THICKNESS_PX` is reconciled with the sensitivity study
  (see table above) but the study's absolute px figure rests on an
  assumed 1.5px trace jitter that has no measurement behind it yet.
  Recompute `MIN_LAYER_THICKNESS_PX = measured_sigma_px / 0.017` once
  step 5 (hand-traced real photos) gives an actual jitter number.
