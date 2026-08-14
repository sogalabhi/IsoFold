# Walkthrough: closing out geometry.py before freeze

This covers one work session whose goal was to close the three open items
blocking a `core-v1.0-frozen` tag on `geometry.py`, verify everything in one
final run, and write the frozen-constants spec sheet. Two of the three
closeouts were straightforward fixes. The third (regenerating the confusion
table) led into a deeper investigation that surfaced a real bug, an attempted
fix that made things worse in a different way, and a decision to revert and
document rather than force a fix under time pressure.

---

## 1. The t0=100 "cusp singularity" claim

**Problem.** `synthetic.py`'s docstring asserted that large t0 relative to
scale produces a "cusp singularity," but this had never actually been
demonstrated against the current code — it was asserted, not shown.

**Investigation.** Ran `synthetic.generate()` at `t0=100, scale=100,
amplitude_ratio=1.1` across all five R values and checked for exceptions,
self-intersection, and warnings. No exception was raised anywhere — the code
silently proceeded. But the *inner* boundary's own points collapsed to
near-zero distance from each other (down to 0.004px), which is the signature
of a self-intersecting curve.

Worked out the analytic explanation: the base fold curve
`y = -amplitude_ratio*cos(x)`, scaled by `scale`, has radius of curvature
`scale/amplitude_ratio` at the hinge (`scale/1.1 ≈ 90.9px` here). A
normal-offset ("parallel") curve is a standard differential-geometry
construction that self-intersects once the offset distance exceeds the
radius of curvature of the curve it's offsetting from — this is the same
effect as CNC toolpath offsetting or contour-line crossing. Swept t0 from 50
to 100 and confirmed the self-intersection onset is sharp right around
t0≈85-91px, matching the 90.9px prediction almost exactly.

**Conclusion.** Real geometric limit of the *synthetic generator's*
normal-offset construction — not a `geometry.py` bug, and not a "geology
fact." `geometry.py` never even sees it fail because nothing catches it
before it happens.

**Fix.**
- Added `config.CUSP_SAFETY_MARGIN = 0.85` (a buffer below the exact
  onset, chosen from a finer sweep of the onset point).
- `synthetic.generate()` now computes the radius of curvature and raises
  `ValueError` with the actual numbers if the requested `t0` would exceed
  `CUSP_SAFETY_MARGIN * radius_of_curvature`, instead of silently building
  a degenerate fold.

Files: `foldclass/src/foldclass/synthetic.py`, `foldclass/src/foldclass/config.py`.

---

## 2. sigma² calibration in `estimate_smoothing`

**Problem.** `estimate_smoothing()` computes
`sigma2_est = median(‖d3‖²) / 20.0` from third finite differences of
boundary points, to auto-pick a spline smoothing factor. `d3` is a 2D vector
(x and y jitter combined) — flagged as a possible factor-of-2 issue that had
never been checked against known injected noise.

**Investigation.** Injected known Gaussian noise (`sigma` in {0.5, 1, 2, 3,
5}px) onto a clean synthetic boundary, computed `sigma2_est` the same way the
code does, and compared to the true `sigma²`. Result: **consistently biased
by a factor of ~1.375**, across every noise level tested — not the assumed
~2x, and not random.

Worked out why analytically: summing the squared third-differences of both
x and y components turns a single-dimension `20·sigma²·chi²(1)` variable
into a `20·sigma²·chi²(2)` variable (sum of two independent noise
components). The median of `chi²(2)` is `2·ln(2) ≈ 1.386`, not 1 — so a
median-based estimator with divisor 20 (which would be correct for a
*mean*-based 1D estimator) systematically overestimates `sigma²` by
`2·ln(2)`. The empirical 1.375 matched this prediction almost exactly.

**Fix.** Changed the divisor from `20.0` to `20.0 * 2.0 * np.log(2.0)`
(≈27.7), which is the median-unbiased value for this exact construction.
Added a comment explaining the derivation (non-obvious constant, would
otherwise look like a magic number).

**Verification.** Added `test_sigma_calibration` to `test_geometry.py`:
injects known sigma, recomputes the estimator, asserts recovery within 15%.
Passes for sigma in {1, 2, 3}px.

Files: `foldclass/src/foldclass/geometry.py`, `foldclass/tests/test_geometry.py`.

---

## 3. The stale 250-fold confusion table

This is the one that didn't go in a straight line.

### 3a. First regeneration — technically true, practically misleading

**Problem.** The "0 misclassifications" confusion table was generated before
the inflection-guided auto-smoothing loop existed, so it needed regenerating
against the exact current code.

**What happened.** Ran `benchmarks/confusion_table.py` (250 folds, seed=42)
fresh. Result: **still 0 misclassifications** — that specific claim held up.
But **70-82% of folds were REFUSED**, not classified at all, because of the
chevron guard (`MIN_ALPHA_SPAN_DEG=30`). The "0 misclassifications" framing
was technically accurate but was quietly hiding that the classifier wasn't
actually running on most of its own benchmark.

**Root cause.** The benchmark randomizes `amplitude_ratio ∈ [1.0, 1.4]`,
which caps the max tangent angle any fold in that range can attain at
`arctan(amplitude_ratio)` = 45°-54.5°. Combined with `ALPHA_MIN_DEG=20`, the
theoretical max alpha span is only ~25-34.5° — right at the 30° threshold,
so most folds fell just short by chance and got refused.

### 3b. Attempted fix — widen the curvature range

**What we tried.** Widened `confusion_table.py`'s `amplitude_ratio` to
[1.6, 2.0] and bumped `scale` up to keep the cusp guard satisfied. Re-ran:
refusal rate dropped to **0%** — full coverage achieved, which was the goal.

**What broke instead.** With full coverage, real off-diagonal errors showed
up that had been invisible before: **Class 1B (R=1.0, exact by
construction, zero noise) was being misclassified as 1A** on 25/50 (right
limb) and 16/50 (left limb) folds. This was a genuine, deterministic,
noise-free bug — not a coverage artifact.

**Traced it.** Compared the spline-fitted tangent angle against the
*analytic* ground-truth tangent angle for the outer curve at
`amplitude_ratio=2.0`: fit error up to 1.5° (vs. ~0.3° at `amplitude_ratio
=1.1`). `SPLINE_SMOOTHING_RATIO=0.15*N` is a fixed budget that doesn't
account for the curve's actual curvature. Since outer and inner arcs have
different curvature profiles even for an exact-parallel offset, the same
fixed smoothing distorts each one's `phi(s)` differently — so points matched
by "equal fitted tangent angle" are no longer true corresponding points.
That mismatch biases the linear `t_alpha = A + B·cos(alpha)` fit's slope
away from zero, pushing R from 1.0 up to ~1.05-1.10.

**Second attempted fix — retune the smoothing constant.** Widened
`tools/sweep.py`'s curvature range to match and re-ran the smoothing-ratio
sweep to find a value that fixes the bias without breaking noise robustness.

**What broke this time.** At the wider curvature range, *any* pixel jitter
of ≥1.0px broke phi-monotonicity **regardless of smoothing ratio**, up to
and including the heaviest tested (`s = N`). At 0.5px jitter, only very
heavy smoothing (ratio ≥ 0.5, far more than the current 0.15) survived at
all. This wasn't a tuning problem anymore — the curvature needed to satisfy
`MIN_ALPHA_SPAN_DEG=30` against `ALPHA_MAX_DEG=70` is inherently fragile to
any realistic hand-trace jitter, independent of how the smoothing is tuned.

### 3c. What we actually did

This touches three interacting frozen-constant candidates
(`SPLINE_SMOOTHING_RATIO`, `MIN_ALPHA_SPAN_DEG`, `ALPHA_MAX_DEG`) and
possibly needs curvature-adaptive smoothing — real design work, not a
same-session retune. Decision: **reverted both `confusion_table.py` and
`tools/sweep.py` back to their original narrow `amplitude_ratio` ranges**,
keeping only the cusp guard and sigma² fixes (which are real and
independent of this issue). The high-coverage attempt and everything learned
from it — the 1B/1A bias, the noise-fragility wall — is written up as a
documented known limitation in `confusion_table.py`'s module docstring
instead of a live bug, so it isn't lost and isn't blocking.

Files touched (net, after revert): `benchmarks/confusion_table.py`
(docstring only — parameters unchanged from before this session).
`tools/sweep.py` was also modified and reverted, ending unchanged.

---

## Final verification run

Ran in one sitting, no edits between steps (per the original close-out
requirement):

1. `pytest foldclass/tests/` — **10/10 passed**, including the new
   `test_sigma_calibration`.
2. `benchmarks/confusion_table.py` (250 folds, seed=42) — **0
   misclassifications**, ~70-80% refused (known limitation, documented).
3. `tools/sensitivity.py` — ran clean; empirical critical noise ratio
   `sigma/t0 <= 0.017`; recommends minimum layer thickness `t0 >= 90px` for
   1.5px trace jitter (this is larger than the current
   `MIN_LAYER_THICKNESS_PX=15.0` placeholder — flagged, not reconciled yet).

## Output

Wrote `docs/CORE_V1_FROZEN_SPEC.md`: the one-page spec listing every frozen
constant in `config.py` with its value and rationale, the verification run
results, and the known limitations carried into the freeze.

## Round 2: two things resolved before tagging

A review of the write-up above pushed back on tagging yet — not because
anything was broken, but because two loose ends in "Not done yet" were
actually part of the session's real finding and deserved to be closed
properly rather than deferred by default.

**Check: was the 15px/90px gap actually a leftover wide-curvature
parameter?** Grepped `amplitude_ratio`/`half_width_rad` across
`sensitivity.py`, `confusion_table.py`, and `sweep.py`. Confirmed
`sensitivity.py` was never touched during the widen-and-revert experiment
in step 3b — it was at `amplitude_ratio ∈ [1.1, 1.4]` (the narrow,
validated range) the entire session. So the discrepancy is real and lives
entirely *inside* the already-validated curvature regime, not a symptom of
the curvature-scope issue. That ruled out the "five-minute fix" hypothesis
and meant it needed actual reconciliation.

**Is the t0≥90px recommendation robust, or a small-sample artifact?**
The original run used n=30/cell, and the critical ratio was driven by one
borderline cell (t0=60, sigma=1.0: 3/30 = 10% flips, just over the 5%
threshold). Re-ran at n=180/cell — same critical ratio (0.017), same 90px
conclusion. Independently spot-checked the specific borderline cell at
n=600: 8.2% flip rate, consistent with the larger run's 9.4%. Confirmed
real, not noise.

**Where does the "90px" number actually come from?** `t0 >= 1.5px / 0.017`.
The 0.017 critical ratio is now validated (above). The 1.5px assumed trace
jitter is not — grepped the whole codebase and found no measurement behind
it anywhere, just a hardcoded guess in `sensitivity.py`'s print statement.

**Fix.** `MIN_LAYER_THICKNESS_PX` is declared in `config.py` but not
referenced anywhere else in the codebase yet — a dormant constant, so
changing its value has no behavioral effect on `geometry.py` today, only
on documentation accuracy. Updated it from the stale `15.0` placeholder to
`90.0`, with a docstring that states plainly which half of that number is
validated (the 0.017 ratio) and which half is a provisional assumption
(the 1.5px jitter) pending real measurement from step 5, plus the formula
to recompute it once that data exists.

**Spec sheet.** Added an explicit "Scope of validity" section at the top
of `docs/CORE_V1_FROZEN_SPEC.md`, stating the `amplitude_ratio <= 1.4`
precondition as a hard boundary of the freeze rather than a footnote
buried in "known limitations" — matching how `MIN_ALPHA_SPAN_DEG` is
already documented as a stated refusal threshold rather than an implicit
one.

**Re-verification.** Ran the full triad again, one sitting, no edits in
between: pytest 10/10, confusion table 0 misclassifications (unchanged —
the `MIN_LAYER_THICKNESS_PX` edit is dormant, so no behavioral change
expected), sensitivity study consistent with the n=180 re-check.

## Not done yet

- Nothing has been committed or tagged (`core-v1.0-frozen`) — held for
  explicit go-ahead before any commit/tag, per this session's ground rules.
  Both pre-tag blockers identified in the review are now resolved.
- The coverage-vs-robustness tension from step 3 remains unresolved by
  design and is now the stated scope boundary of the freeze (see
  `docs/CORE_V1_FROZEN_SPEC.md`, "Scope of validity"): it needs
  curvature-adaptive smoothing or a rethink of `MIN_ALPHA_SPAN_DEG`/
  `ALPHA_MAX_DEG` against what real photo-traced folds actually attain,
  informed by real data from step 5 (hand-traced photos) rather than more
  synthetic parameter sweeps.
- `MIN_LAYER_THICKNESS_PX=90.0` is reconciled with the validated part of
  the sensitivity study, but still carries the unmeasured 1.5px jitter
  assumption — flagged in both `config.py` and the spec sheet, to be
  recomputed once step 5 provides a real number.
