# IsoFold: Automated Ramsay Classification of Folds from Field Photographs

> [!NOTE]
> 📖 **Full Documentation Suite**: For the detailed structural geology textbook guide, technical architecture, user manual, CLI commands, and API specifications, see the **[docs/INDEX.md](docs/INDEX.md)**.

## What IsoFold is

A tool that takes a photograph of a geological fold in **profile section** (a face cut perpendicular to the fold axis) and returns:

1. The **Ramsay morphological class** of a chosen folded layer — 1A, 1B, 1C, 2, or 3
2. A **Fourier shape analysis** of the folded surface (Stabler/Hudleston harmonic coefficients)
3. An **annotated diagram** showing traced boundaries, inflection points, hinge points, axial trace, dip isogons and interlimb angle
4. Diagnostic plots: the t′α–α field diagram and the b₁–b₃ Hudleston chart

Semester 1 (this semester): a validated Python core plus a desktop tool.
Semester 2: port the geometry core to C++ and wrap it in an offline Flutter mobile app for field surveyors.

**This is a measurement problem, not a classification problem.** Ramsay's classes are hard inequalities on a measured quantity. Once two clean boundary curves are extracted, the class follows deterministically. There is no machine learning anywhere in this project.

---

## Domain background

### Structural elements

A folded layer in profile section has two bounding surfaces: the **extrados** (outer, convex) and the **intrados** (inner, concave). The region on the concave side is the **core**.

On each surface:
- **Inflection point** — where curvature changes sign; operationally, a local extremum of the tangent-angle function φ(s)
- **Hinge point** — operationally, the point where φ equals the reference direction (see Critical decision 1). This coincides with the point of maximum absolute curvature for symmetric folds, but not necessarily for asymmetric ones — treat the φ-based definition as primary, not the curvature one
- **Axial trace** — the line joining the hinge points of the two surfaces (H on outer, G on inner)
- **Limb** — the segment between a hinge and the adjacent inflection point

### The dip isogon construction

Take a point `p` on the outer surface. Find the point `q` on the inner surface where the tangent is **parallel** to the tangent at `p`. The segment `pq` is the **dip isogon**.

**There isn't one isogon — it's a family, one per value of α**, fanning out from the hinge. At α = 0, `p = H` and `q = G`, so the isogon *is* the segment HG — the axial trace itself, and the one isogon whose position is known without any tangent matching. Useful as the first debugging anchor.

**Orientation of the family is the classification.** Extend the isogons and see where they go relative to the core:

| Isogons | Class |
|---|---|
| Converge towards the core | 1 (all subclasses) |
| Stay parallel to each other | 2 |
| Diverge towards the core | 3 |

Class 2 is the clean anchor: the inner arc is constructed as the outer arc translated by a constant vector parallel to the axial trace (see `synthetic.py`), so every isogon in the family *is* that same vector — parallel to the axial trace and to every other isogon, with `T_α` constant. That's exactly why similar folds have `T′α = 1`.

Let `α` be the angle between the tangent at `p` and the tangent to the folded surface at the hinge point. Then:

- **Orthogonal thickness** `t_α` = perpendicular distance between the two parallel tangents at `p` and `q`
- **Axial plane thickness** `T_α` = intercept between those tangents measured along a line parallel to the axial trace

**Implementation trap: `t_α` is not `|pq|`.** `q` is found purely by tangent-angle matching — nothing constrains it to lie along the normal from `p`. If `n̂` is the shared normal direction (⊥ to the common tangent at `p` and `q`) and `θ` is the angle between segment `pq` and `n̂`, then:

```
t_α = |pq| · cos θ
```

Only when the isogon happens to be normal to the surface does `|pq| = t_α`. Compute `t_α` as the distance from `p` to the tangent **line** through `q` (or vice versa) — never `np.linalg.norm(q - p)`. That bug produces plausible-looking numbers that silently shift the class. Free runtime guard: `t_α ≤ |pq|` always holds (it's a projection) — assert it in `isogon_pairs`.

These are related by:

```
t_α / T_α = cos α                                    (Ramsay eq. 12.1)
```

At the hinge, α = 0 and therefore `t₀ = T₀ = |HG|` — exactly, provided HG is perpendicular to the tangent at the hinge (Hudleston's Case 1; see Critical decision 4 for how H and G are actually found, and for what happens when this perpendicularity doesn't hold).

### Normalisation

Absolute thickness is scale-dependent (enlarge a photo and thicknesses change while shape does not). So use:

```
t′_α = t_α / t₀
T′_α = T_α / T₀
t′_α = T′_α · cos α
```

### The classification

| Class | Dip isogons | Condition on t′α | Also known as |
|---|---|---|---|
| 1A | strongly convergent | t′α > 1 | supratenuous (Nevin 1931) |
| 1B | convergent | t′α = 1 | parallel (Van Hise 1896), concentric (Leith 1923) |
| 1C | convergent | cos α < t′α < 1 | — |
| 2 | parallel | t′α = cos α, T′α = 1 | similar (Van Hise 1896) |
| 3 | divergent | t′α < cos α | — |

### The R index (primary output)

Rather than five if-statements with arbitrary tolerances, normalise:

```
R(α) = (t′_α − cos α) / (1 − cos α)
```

| R | Class |
|---|---|
| R > 1 | 1A |
| R ≈ 1 | 1B |
| 0 < R < 1 | 1C |
| R ≈ 0 | 2 |
| R < 0 | 3 |

Report **mean R with spread** over the reliable α range. The denominator → 0 as α → 0, so exclude small α. Default reliable range: **α ∈ [20°, 70°]** (make this a named config constant, not a magic number).

R and its spread are not measured pointwise and averaged — they come out of a joint fit together with t₀. See Critical decision 2.

### Fourier shape analysis

A periodic symmetric fold surface, with the x-axis through consecutive inflection points and y positive upward, can be written with **odd sine terms only** (sines because the curve passes through the origin; odd harmonics because of symmetry about the hinge):

```
y = a₁ sin x + a₃ sin 3x + a₅ sin 5x + ...        with a₁ > a₃ > a₅
```

**Stabler (1968) three-point method.** Take a quarter wavelength `b` (inflection → adjacent hinge), with amplitude `a` at the hinge and y-values `y₁`, `y₂` at x = b/3 and 2b/3. Then:

```
a₁ = (a + y₁)/3 + 0.577·y₂
a₃ = (2y₁ − a)/3
a₅ = (a + y₁)/3 − 0.577·y₂
```

(0.577 = 1/√3. This is verified against two independent sources: Ghosh eq. 12.5, and Hatui & Chattopadhyay 2020 eq. 4, which uses b₁/b₃/b₅ notation with y₃ in place of `a`.)

**Prefer Hudleston (1973) trapezoidal integration** over the three-point method — with a densely digitised curve you can integrate the Fourier coefficients numerically and get much lower error. Implement Stabler as a cross-check.

Outputs:
- `F = a₁/b`, `T = a₃/b` — plot as a single point on the F–T diagram. Ghosh (p. 239) confirms this exact form. **State the convention for `b` explicitly and adopt it**: Ghosh takes the quarter wavelength as π/2, making the division a fixed rescaling rather than a pixel-dependent one — a raw pixel-length `b` will land nowhere near Hatui & Chattopadhyay's Figure 11c. Calibrate numerically against that figure before trusting absolute chart positions. Note `T/F = a₃/a₁` is invariant to this choice, so the hinge-shape read below is robust even if `b` is wrong — only absolute chart position depends on it.
- Positive T/F → rounded hinge; negative T/F → sharp hinge; increasing F → increasing amplitude/quarter-wavelength ratio
- Hudleston shape letter (A–F: box → semi-ellipse → parabola → sine → chevron) and amplitude number (1–5)

**Hard limitation:** the Fourier series cannot represent folds with relative limb dips > 90°, because the surface stops being single-valued in x. Detect this and refuse to run the Fourier branch, with a clear message.

---

## Critical technical decisions — do not deviate without discussion

### 1. Never compute curvature

Curvature is a second derivative. On pixel-derived contours, second derivatives amplify noise catastrophically.

**Nothing in Ramsay's method requires it.** Work entirely with the **tangent angle** `φ(s)`, obtained from the analytic first derivative of a fitted spline:

| Quantity | How to get it | Derivative order |
|---|---|---|
| α (dip angle) | φ(s) relative to hinge reference | 1st |
| dip isogon | match φ_outer(s₁) = φ_inner(s₂) | 1st |
| t_α | distance between two parallel tangent lines | 0th |
| inflection point | local extremum of φ(s) | 1st |
| hinge point | where φ = reference direction | 1st |

**Why it feels like it should be needed.** The isogon construction *describes* how curvature differs between the two arcs — Class 1 exists because the outer arc has a larger radius of curvature than the inner. Curvature is what the method is *about*. But being what the method measures is different from being what you have to compute. α is a proxy for position along the curve, and it happens to be the right proxy: because it's defined by the tangent, it pairs corresponding points on the two arcs without ever asking how sharply either one bends. The curvature difference shows up in the *answer* — in how t_α varies with α — rather than in the calculation. That's the elegance of Ramsay's construction, and why "reformulate everything in tangent-angle terms" works rather than being a dodge.

**Where a curvature-like quantity would sneak in, and how each is handled:**

| Textbook definition | Curvature-free equivalent |
|---|---|
| Hinge = max \|d²y/dx²\| | where φ equals the reference direction |
| Inflection = d²y/dx² = 0 | local extremum of φ(s) |
| Hinge-zone extent = radius of curvature < half inflection spacing | threshold on dφ/ds |

The last one does use `dφ/ds`, which *is* curvature. The distinction that matters: it's the analytic derivative of a fitted spline's tangent-angle function, not a finite difference on pixel coordinates — the spline has already absorbed the noise, so it's well-conditioned. Safe to use for hinge-zone extent, and as an asymmetry diagnostic: if the max-|dφ/ds| point and the φ-reference hinge point diverge substantially, the fold is strongly asymmetric and worth flagging.

What must never happen: `np.gradient(np.gradient(y_pixels))`. That's the operation that destroys everything.

This reformulation of Ramsay's construction in tangent-angle terms is the methodological core of the project. State it explicitly in code comments.

### 2. Fit t₀ and R jointly — never measure t₀ as a single point

Because `t′_α = t_α / t₀`, any error in t₀ scales **every** measurement and shifts the class. Measuring t₀ at the hinge is the worst-conditioned option: near a broad hinge, φ changes slowly with arc length, so "find where φ = 0" has large positional uncertainty.

**Resolution: don't measure t₀ and then divide — fit t₀ and R jointly.** Start from the thickness law:

```
t_α = t₀ · [R + (1 − R)·cos α]
```

Substitute `A = t₀R`, `B = t₀(1 − R)`:

```
t_α = A + B·cos α
```

a plain linear least-squares fit over the basis {1, cos α}, using every isogon pair in the reliable α range on one limb. Then:

```
t₀ = A + B
R  = A / (A + B)
```

Check: Class 1B (`t_α` constant = t₀) gives A = t₀, B = 0 → R = 1. Class 2 (`t_α = t₀ cos α`) gives A = 0, B = t₀ → R = 0. Both correct by construction.

This buys:
- **t₀ is never a single-point measurement** — it's the fitted intercept from every isogon pair on the limb.
- **σ_R comes from the fit covariance** via the delta method — no invented tolerance constant for "R ≈ 1" vs "R ≈ 0".
- **The class label respects its own uncertainty**: if R = 0.95 ± 0.15, that's indistinguishable between 1B and 1C — report it as such rather than forcing a label. `R_AMBIGUITY_SIGMA` (config) sets how many σ_R away from a class boundary is required before committing to a label.
- **Fit residuals are diagnostic**: a poor fit means R genuinely varies with α — the fold doesn't have one well-defined class across the limb. That's a real geological result, not a failure. (These are fit residuals, not the axial-trace self-test residuals in decision 4 — don't conflate the two; they diagnose different things.)

**Caveat — don't over-trust the analytic σ_R.** OLS covariance assumes independent errors across isogon pairs. Adjacent pairs come from the same spline fit over overlapping neighbourhoods, so their errors are correlated — the analytic σ_R is a lower bound, not the true uncertainty. Cross-validate against the boundary-perturbation sensitivity study (decision 7) for the honest number. Errors are also plausibly heteroscedastic — matching gets less reliable near `ALPHA_MAX_DEG` — so an unweighted fit is a v1 simplification; revisit with weights if the perturbation study shows it matters.

Still plot the pointwise `t′_α(α)` values alongside the fit — Fig. 12.24 shows a fold as a curve, not a point. `t_prime()` stays, but demoted to a plotting utility: it is no longer an input to classification.

### 3. Isogon matching needs disambiguation

For a given α there can be more than one point on the inner arc with a matching tangent angle — periodic fold surfaces make this ambiguous, not just theoretical. Resolve as follows:

- Restrict the search to the **corresponding limb** (same side of the hinge). Decision 5 already requires analysing limbs separately — make that a hard constraint on the *search domain*, not just a reporting convention.
- Within a limb, φ should run monotonically from 0 at the hinge to its maximum at the inflection point, which makes the match unique.
- **Assert monotonicity.** A non-monotonic φ within a limb means spurious wiggles from under-smoothing — a smoothing failure, not a matching failure. This assertion doubles as a smoothing diagnostic.
- **Euclidean guard**: reject any pair where `|pq|` exceeds `MAX_ISOGON_LENGTH_FACTOR × t₀` (config) — catches mismatches that pass the angle test but are geometrically implausible.

See the "implementation trap" under the dip isogon construction above for the `t_α ≠ |pq|` distinction that applies once a pair is found.

### 4. The axial trace is a fixed point, not a given — and its error is detectable

The axial trace direction used for the reference angle and for `T_α` isn't known in advance — it's defined by the hinge points, which are found *using* that same reference direction. This is a **fixed-point iteration**, not a lookup:

1. Seed `H₀`, `G₀` from the user's tap (or an initial guess).
2. Draw the trial axial trace `H₀G₀`.
3. `H₁` = point on the outer arc where the tangent is ⊥ to `H₀G₀`; `G₁` likewise on the inner arc.
4. Redraw the trial trace through `H₁G₁`, repeat to convergence.

Cap the iteration count (`AXIAL_TRACE_MAX_ITER`) and define a divergence fallback — revert to the inflection-to-inflection reference angle, with a warning.

The converged condition — tangents at H and G both ⊥ to HG — is Hudleston's **Case 1**. It's why `t_α/T_α = cos α` holds and why `t₀ = T₀` at the hinge.

**The self-test is also a Case 1/2/3 detector.** If the true axial trace is off by a small angle `β` from the Case 1 condition — Hudleston's **Case 2**, where `t₀ ≠ T₀` — then `T_α = t_α / cos(α + β)`, so:

```
t_α/T_α − cos α = cos(α + β) − cos α ≈ −β·sin α     (small β)
```

The failure signature is **not a constant offset** — it's near zero at the hinge (the deviation there is only O(β²), consistent with `t₀ ≈ T₀` still holding approximately) and grows roughly proportional to `sin α` away from it. Detect Case 2 by fitting the self-test residual against `sin α` (equivalently, fitting `t_α/T_α = cos(α + β)` for β) — not by checking whether the residual mean is nonzero, which misses exactly this signature. If `β` is significant, flag Case 2 and report `t₀` and `T₀` separately rather than assuming they're equal.

**Case 3** — the two hinges have genuinely different reference angles, not just a shared offset — can't be classified in this scheme. Detect and refuse.

*To verify against source before relying on it*: Hudleston is reported to use a stronger reference condition for awkward cases — the point where `t_α` is maximal *and* `t_α = T_α` *and* the isogon is normal to the surface, all three coinciding. Plausible, and would sit naturally next to the α=0 anchor, but unconfirmed here — check Hudleston (1973) directly before implementing it as a named method.

### 5. Analyse the two limbs separately

Real folds are asymmetric and can genuinely differ in class between limbs. Report both. Never silently average them.

### 6. The α-coverage check

On a **chevron fold** the limbs are straight, so φ is nearly constant along each limb. α jumps from 0 at the hinge to the limb dip and stays there. You get one or two α values instead of a curve, and the classification is unconstrained.

Implement a coverage check: if the spread of recovered α values is below `MIN_ALPHA_SPAN` (default 30°), **refuse to output a class** and report *"sharp-hinged fold; dip isogon method poorly constrained."*

Sharp hinges also break the Fourier branch — they need more than two harmonics for faithful representation (Hudleston 1973a, Stowe 1988). Flag rather than silently producing numbers.

### 7. Synthetic ground truth is a test harness, not training data

There is no model to train. Synthetic folds exist to:
- **Validate** the geometry against known classes (real photos have no ground truth)
- **Decouple debugging** — feed a perfect mask and a rendered noisy image separately, so you know which stage failed
- **Choose the smoothing parameter** by sweeping `s` and picking what recovers known t′α curves, instead of asserting a value
- **Quantify sensitivity** — perturb the traced boundary by ±1, ±2, ±5 px and find where the class flips

**Normal sign convention.** In the offset construction (see `synthetic.py`), `n̂` must point consistently towards the core. Get it backwards and you generate a Class 3 fold while labelling it 1A — a bug that produces plausible-looking output and fails no other test. Assert the sign explicitly (e.g. check the offset point lies on the concave side) rather than trusting it implicitly.

### 8. Keep `geometry.py` portable

It must import **only numpy and scipy**. No OpenCV, no matplotlib, no I/O. This module is ported to C++ next semester and the Python version is its test oracle. Every extra dependency makes the port harder.

---

## Repository layout

```
foldclass/
  src/foldclass/
    geometry.py       # numpy + scipy ONLY. The port target.
    synthetic.py      # generators for classes 1A/1B/1C/2/3
    segment.py        # LAB clustering, GrabCut, contour → two arcs
    fourier.py        # Stabler + Hudleston harmonic analysis
    plots.py          # t′α field diagram, Hudleston b₁–b₃ chart, annotated overlay
    config.py         # all thresholds and tuning constants, named
    report.py         # assemble results into a PDF / HTML report
  tools/
    trace.py          # matplotlib click-to-trace GUI, saves CSV
    run.py            # CLI: image or trace in, report out
    sweep.py          # smoothing-parameter sweep against synthetics
  tests/
    test_geometry.py
    test_synthetic.py
    test_fourier.py
  data/
    images/           # field photographs
    traces/           # saved boundary coordinate CSVs — COMMIT THESE
    synthetic/        # generated test set
  pyproject.toml
  README.md
```

---

## Module specifications

### `geometry.py`

```python
@dataclass
class Arc:
    """A fitted, arc-length-parameterised boundary curve."""
    s: np.ndarray          # arc length samples
    xy: np.ndarray         # (N, 2) coordinates
    phi: np.ndarray        # tangent angle at each sample, radians, unwrapped
    tck: tuple             # underlying spline

def fit_arc(points: np.ndarray, smoothing: float) -> Arc:
    """Fit a smoothing spline to ordered boundary points and resample
    uniformly in arc length. Tangent angles come from the spline's
    analytic first derivative — never from finite differences on pixels."""

def find_inflections(arc: Arc) -> list[float]:
    """Arc-length positions of local extrema of phi(s)."""

def find_hinge(arc: Arc, reference_angle: float) -> float:
    """Arc-length position where phi equals reference_angle."""

def find_axial_trace(outer: Arc, inner: Arc, seed_h: float, seed_g: float,
                      max_iter: int = ...) -> tuple[float, float, Line]:
    """Hudleston Case 1 fixed-point iteration (Critical decision 4):
    alternately call find_hinge on each arc using the current trial axial
    trace's perpendicular as the reference angle, then redraw the trace
    through the resulting hinge points, until convergence. Falls back to
    the inflection-to-inflection line, with a warning, if it fails to
    converge within max_iter. Returns (s_hinge_outer, s_hinge_inner,
    axial_trace_line)."""

def isogon_pairs(outer: Arc, inner: Arc, alphas: np.ndarray,
                 limb: Literal["left", "right"]) -> list[IsogonPair]:
    """For each alpha, find p on outer and q on inner where the tangent
    angles match, restricted to the given limb (Critical decision 3).
    Asserts phi is monotonic within the limb and rejects pairs where |pq|
    exceeds MAX_ISOGON_LENGTH_FACTOR * t0. Computes t_alpha as the
    point-to-line distance between the two parallel tangents — NOT
    norm(q - p), see the dip isogon "implementation trap" in the domain
    background — and asserts t_alpha <= |pq| as a cheap correctness guard.
    Returns the pair plus t_alpha and T_alpha."""

def t_prime(pairs, t0: float) -> np.ndarray:
    """Pointwise normalised orthogonal thickness, for the t'alpha(alpha)
    diagnostic plot only (Ghosh Fig 12.24). Not used for classification —
    see fit_thickness_law."""

@dataclass
class ThicknessFit:
    """Joint fit t_alpha = A + B*cos(alpha) over one limb's isogon pairs
    in the reliable alpha range (Critical decision 2)."""
    A: float
    B: float
    t0: float            # = A + B
    R: float              # = A / (A + B)
    sigma_R: float         # delta-method estimate — a LOWER BOUND on the
                            # true uncertainty; cross-check against the
                            # boundary-perturbation study (decision 7)
    residuals: np.ndarray

def fit_thickness_law(alphas: np.ndarray, t_alphas: np.ndarray) -> ThicknessFit:
    """Linear least-squares fit of t_alpha = A + B*cos(alpha) (Ramsay eq.
    12.1 reparameterised so t0 and R are fit jointly rather than t0 being
    measured first and R computed by division). See Critical decision 2."""

@dataclass
class CaseDiagnostic:
    """Hudleston Case 1/2/3 detection from the isogon self-test residual
    (Critical decision 4)."""
    beta: float            # fitted axial-trace offset angle, radians
    sigma_beta: float
    case: Literal[1, 2, 3]

def case_diagnostic(pairs: list[IsogonPair]) -> CaseDiagnostic:
    """Fit the t_alpha/T_alpha - cos(alpha) residual against sin(alpha) to
    recover the axial-trace offset beta. |beta| small -> Case 1 (t0 = T0).
    Significant beta -> Case 2 (report t0, T0 separately). Divergent
    per-hinge reference angles -> Case 3 (refuse to classify)."""

@dataclass
class ClassResult:
    r_mean: float
    r_std: float           # from ThicknessFit.sigma_R
    fold_class: str | None      # None when coverage check fails, or when
                                 # sigma_R leaves adjacent classes
                                 # indistinguishable (R_AMBIGUITY_SIGMA)
    alpha_span: float
    n_samples: int
    fit: ThicknessFit
    warnings: list[str]

def classify(fit: ThicknessFit, alpha_span: float, n_samples: int) -> ClassResult:
    """Assign a class from a ThicknessFit. Returns fold_class=None with a
    warning when alpha_span < MIN_ALPHA_SPAN, or when R's uncertainty
    leaves it within R_AMBIGUITY_SIGMA of a class boundary."""
```

**Sanity checks to include as assertions — free self-tests, use them:**
- `t_α / T_α == cos α` to within tolerance at every isogon pair. If it does not, the geometry is wrong.
- `t_α ≤ |pq|` at every isogon pair (projection bound — see the implementation trap above).
- On a Case 1 synthetic, `case_diagnostic` recovers `β ≈ 0`; on a synthetic built with a known injected offset, it recovers that `β` within tolerance.

### `synthetic.py`

The generator is the foundation of the whole test suite. Get it exactly right.

**Outer arc:** a smooth periodic curve, e.g. `y = A·sin(x)` over one wave, or a Fourier curve with controllable hinge sharpness so chevron-like cases can be generated too.

**Thickness law.** Parameterise directly by a constant R, which makes assertions clean:

```
t′_α = R + (1 − R)·cos α
```

| R value | Produces |
|---|---|
| 1.0 | Class 1B exactly |
| 0.0 | Class 2 exactly |
| 0.5 | Class 1C |
| −0.5 | Class 3 |
| 1.5 | Class 1A |

A power-law alternative `t′_α = (cos α)^k` is also useful (k = 0 → 1B, k = 1 → 2, 0 < k < 1 → 1C, k > 1 → 3, k < 0 → 1A) but gives R varying with α, so it is less convenient for tests.

**Construction of the inner arc.** For each point `p` on the outer arc with tangent angle α:

```
t_α = t₀ · t′_α(α)
q   = p + t_α · n̂        where n̂ is the unit normal pointing towards the core
```

**Important caveat — read this.** This normal-offset construction is only *exactly* tangent-parallel when thickness is constant. For variable thickness the inner-arc tangent picks up a small normal component proportional to `dt/dα`, so the recovered t′α deviates slightly from the nominal law. Handle it as follows:

- **Class 1B** — construct as a true parallel/offset curve. Exact.
- **Class 2** — construct by translating the outer arc by a constant vector parallel to the axial trace. The two arcs then have identical shape, so tangent-parallel pairs are exactly the translated pairs. Exact.
- **1A, 1C, 3** — use the normal-offset construction. Implement an optional **iterative refinement**: measure the actual t′α using the same isogon-matching code, adjust the inner arc, repeat until the recovered law matches the target within tolerance. Converges quickly.

Use 1B and 2 as the strict-tolerance anchors in tests; give the other three a documented, looser tolerance unless refinement is enabled.

**For testing the Case 2 diagnostic** (Critical decision 4), provide an option to construct the axial-trace reference with a deliberate offset `β` from the Case 1 (hinge-perpendicular) condition, so `case_diagnostic` can be tested against a known ground-truth `β`.

**Also provide** `render(outer, inner, noise, blur, texture, rotation) -> np.ndarray` so segmentation can be tested on realistic images derived from known geometry.

### `segment.py`

Interactive by design — a surveyor tapping the layer is faster and more reliable than any automatic method on weathered rock. Implement in this order, each with a guaranteed fallback:

1. **LAB colour clustering** (k-means). Try `a*` and `b*` channels individually before grayscale — rusty/pale layers often differ in hue but barely in luminance.
2. **GrabCut** from a user-drawn box.
3. **Manual polygon trace** — always available.

Then: contour extraction, split the closed loop at the two frame-cut ends into outer and inner chains, and identify which is which by checking convexity relative to the core.

Optional later: a small on-device segmentation model. **No hard dependency on any neural network** — that is a design requirement for offline field use, and a claim the report will make.

### `config.py`

Every threshold lives here as a named constant with a comment explaining its provenance:

```python
ALPHA_MIN_DEG = 20.0             # R denominator → 0 below this
ALPHA_MAX_DEG = 70.0             # tangent matching unreliable near inflection
MIN_ALPHA_SPAN_DEG = 30.0        # below this, refuse to classify (chevron guard)
SPLINE_SMOOTHING = ...           # chosen by sweep.py against synthetics — cite the run
MIN_LAYER_THICKNESS_PX = ...     # below this, flag low confidence
MAX_ISOGON_LENGTH_FACTOR = ...   # reject isogon pairs with |pq| > this * t0 (decision 3)
AXIAL_TRACE_MAX_ITER = ...       # cap on the Case 1 fixed-point iteration (decision 4)
AXIAL_TRACE_TOL = ...            # convergence tolerance for the same iteration
R_AMBIGUITY_SIGMA = 2.0          # min |R - class boundary| / sigma_R to commit to a label (decision 2)
QUARTER_WAVELENGTH_B = np.pi / 2 # Ghosh's convention for the Fourier F-T diagram divisor
```

---

## Test requirements

```python
# test_geometry.py
- t_α / T_α == cos α for every isogon pair, tolerance 1e-6
- t_α <= |pq| for every isogon pair
- an oblique-isogon synthetic (where the true isogon is deliberately not
  normal to the tangent) recovers t_alpha via the line-distance formula,
  not norm(q - p) — construct a case where the two differ by a known
  factor and assert the code returns the correct one
- an under-smoothed synthetic trips the within-limb monotonicity assertion
- fit_thickness_law recovers known (t0, R) for a Class 1B and a Class 2
  synthetic, tolerance 0.02; sigma_R is finite and sane
- classify() returns the correct class for R ∈ {1.5, 1.0, 0.5, 0.0, −0.5}
- a chevron synthetic returns fold_class=None with the coverage warning
- find_axial_trace converges to the known Case 1 hinge points on standard
  synthetics, and falls back correctly (with a warning) on a synthetic
  constructed not to converge
- case_diagnostic recovers a known injected axial-trace offset beta on a
  Case 2 synthetic, and returns beta ≈ 0 on a Case 1 synthetic
- constructing a synthetic with n̂ flipped is caught by the sign-convention
  assertion (decision 7)
- fit_arc is invariant under rotation and uniform scaling of the input points

# test_synthetic.py
- round-trip: generate at known R → measure → recover R, for 50 folds
  spanning all five classes. Report a confusion table and mean |ΔR|.

# test_fourier.py
- Stabler and Hudleston coefficients agree on a clean synthetic
- known input y = a₁sin x + a₃sin 3x recovers a₁ and a₃
- T/F = a₃/a₁ is invariant to the choice of b, even when b is deliberately
  wrong — confirms the qualitative hinge-shape read doesn't depend on
  getting the quarter-wavelength convention right
- limb dip > 90° raises the documented refusal
```

The **50-fold round-trip confusion table** is the headline result for the Semester 1 report. Print it as a table with mean and standard deviation of recovered R per class.

---

## Build order

Work in this sequence. Do not start segmentation until the geometry passes on synthetics.

1. `synthetic.py` + `geometry.py` + `test_geometry.py` — get the round-trip green on clean synthetic curves. No images involved. Include the Case 1 fixed-point iteration (`find_axial_trace`) and the isogon disambiguation/trap guards (Critical decisions 3–4) in this pass — they're geometry-core, not later polish.
2. `sweep.py` — choose `SPLINE_SMOOTHING` empirically and record the justification.
3. Sensitivity study — perturb boundaries by ±1/±2/±5 px, find where classes flip, and derive `MIN_LAYER_THICKNESS_PX`. Use this study, not the analytic `σ_R` alone, as the authoritative uncertainty estimate (Critical decision 2).
4. `fourier.py` + tests. Calibrate the `QUARTER_WAVELENGTH_B` convention against Hatui & Chattopadhyay's Figure 11c before trusting chart positions.
5. `tools/trace.py` — click-to-trace, save CSV. Run the full pipeline on **hand-traced** real photographs. Any failure now is a tracing failure, not a geometry failure.
6. `segment.py` — automate what the hand-tracing proved possible.
7. `plots.py`, `report.py`, `run.py` — outputs and CLI.

---

## Conventions

- Python 3.11. Environment managed with `uv`.
- Type hints on every public function. Dataclasses for results, not dicts.
- Docstrings cite the source equation where one exists (e.g. `"""Ramsay eq. 12.1"""`).
- Angles in **radians internally**, degrees only at API and display boundaries. Name variables accordingly (`alpha_rad`, `alpha_deg`).
- No magic numbers anywhere outside `config.py`.
- Modules, not notebooks. A `.py` file that can be imported and tested; notebooks may import it for exploration but must not contain logic.
- Traced coordinates in `data/traces/` are **committed data**, not scratch. Never require a re-trace.

## Explicit non-goals

- **No machine learning.** Not for classification, not for the geometry. Any segmentation model is an optional convenience layer with a non-ML fallback.
- **No curvature computation.** See decision 1.
- **No correction for oblique sections.** The method assumes a transverse profile. If the outcrop face is not perpendicular to the fold axis, the tool will confidently return a wrong class. Mitigate by capturing face orientation as metadata and flagging, not by pretending robustness. Document this as the primary scope limitation.
- **No claim of full automation.** Interactive layer selection is a design choice, not a shortcoming — Ramsay's method requires choosing *one* layer, and on a multilayer outcrop that is a human judgement.

## Reference sources

- Ghosh, S.K., *Structural Geology: Fundamentals and Modern Developments* — Chapter 12, especially §12.3 (structural elements), §12.6 (morphological classification, Figs 12.22–12.24), §12.7 (Fourier shape, p. 239, Figs 12.25–12.27).
- Ramsay, J.G. (1967) *Folding and Fracturing of Rocks*; Ramsay & Huber (1987) vol. 2, pp. 347–349 and 314–316.
- Hatui, K. & Chattopadhyay, A. (2020) "Modification of pre-existing folds in a shear zone", *J. Earth Syst. Sci.* 129:126 — §4.3.1–4.3.2. This is the manual version of exactly what we are automating. Their Figures 10a, 10e, 11a, 11b and 11c are the target output formats.
- Stabler (1968), *Tectonophysics* 6(4) 343–350; Hudleston (1973), *Tectonophysics* 16(1–2) 1–46. **Unverified against source and worth checking before implementing:** Hudleston's exact reference-point construction for awkward/broad-hinge cases (Critical decision 4) and the Case 1/2/3 terminology used above — confirm the terminology and the three-way-coincidence condition directly against the 1973 paper.

## What we add over the published manual method

Hatui & Chattopadhyay measured t_α by hand from photographs for a limited set of folds, with **no reported uncertainty**. The contribution here is:

- Automated and **reproducible** — two workers get the same number
- **Uncertainty-quantified** — every R carries a `σ_R` from the joint thickness-law fit, cross-checked against the boundary-perturbation study
- Fast enough to process a whole traverse, enabling R to be used as a **strain proxy** mapped across outcrops (their core result is that class shifts 1B → 1C → 2 with increasing strain approaching a shear zone)
- Deployable **offline in the field**
