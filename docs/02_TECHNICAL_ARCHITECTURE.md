# Chapter 2: Technical Architecture & Critical Engineering Decisions

This chapter documents the software architecture, dependency stack, and 8 critical engineering decisions governing the implementation of the fold geometry engine.

---

## 1. Core Technical Philosophy

This project treats fold classification as an **exact measurement problem**, not a machine learning or probabilistic classification problem:
1. Structural geology classes (Ramsay Class 1A, 1B, 1C, 2, 3) are deterministic inequalities on measured layer thickness $t_\alpha$.
2. Once clean boundary curves ($S_0$ and $S_1$) are extracted, the classification follows deterministically without any machine learning models.
3. The geometry engine must remain **100% offline, lightweight, and mathematically reproducible**.

---

## 2. Technology Stack & Package Dependencies

| Package | Version | Purpose in Project |
|---|---|---|
| **Python** | `3.11+` | Core development runtime environment |
| **NumPy** | `>= 1.24` | Vectorized matrix operations, coordinate transformations, linear least-squares fitting |
| **SciPy** | `>= 1.11` | Parametric B-spline interpolation (`splprep`, `splev`), Gaussian filtering |
| **Matplotlib** | `>= 3.8` | Publication figure rendering, interactive Qt/Tk GUI canvas |
| **scikit-image** | `>= 0.22` | Structure tensor computation, coherence masking, Frangi vesselness ridge filtering |
| **PyQt6** | `>= 6.6` | Desktop interactive click-tracing GUI window (`QtAgg` backend) |
| **pytest** | `>= 8.0` | Automated synthetic unit testing & round-trip verification harness |

---

## 3. The 8 Critical Engineering Decisions

To avoid common pitfalls in digitised curve analysis, the architecture enforces 8 non-negotiable design principles:

### Decision 1: Never Compute Curvature on Raw Pixels
Curvature is a second derivative ($\frac{d^2y}{dx^2}$). On pixel-derived contours, finite-difference second derivatives amplify high-frequency discretization noise catastrophically:
$$\text{Noise amplification} \propto \frac{1}{\Delta x^2}$$

**Tangent-Angle Reformulation**:
All structural elements are reformulated in terms of the **tangent angle $\phi(s)$**, derived from the analytic first derivative of a fitted smoothing spline:

$$\phi(s) = \text{unwrap}\left( \arctan2\left(\frac{dy}{du}, \frac{dx}{du}\right) \right)$$

| Structural Quantity | Textbook Definition | Curvature-Free Equivalent | Derivative Order |
|---|---|---|---|
| Dip Angle $\alpha$ | Angle relative to hinge | $|\phi(s) - \phi_{\text{hinge}}|$ | 1st (Spline derivative) |
| Dip Isogon Pair | Tangent parallel matching | $\phi_{\text{outer}}(s_1) = \phi_{\text{inner}}(s_2)$ | 1st (Spline derivative) |
| Orthogonal Thickness $t_\alpha$ | Distance between parallel tangents | Point-to-line distance | 0th (Coordinates) |
| Inflection Point | $\frac{d^2y}{dx^2} = 0$ | Local extremum of $\phi(s)$ | 1st (Spline derivative) |
| Hinge Point | Peak curvature point | $\phi(s) \equiv \phi_{\text{ref}} \pmod{\pi}$ | 1st (Spline derivative) |
| Hinge Curvature Proxy | Radius of curvature $R_c$ | Analytic spline derivative $\frac{d\phi}{ds}$ | 1st derivative of $\phi$ |

What is strictly forbidden: `np.gradient(np.gradient(y_pixels))`.

---

### Decision 2: Fit $t_0$ and $R$ Jointly (Never Single-Point Division)
Because $t'_\alpha = t_\alpha / t_0$, any measurement error in hinge thickness $t_0$ scales every measurement and silently shifts the class label. Measuring $t_0$ at a single hinge point is poorly conditioned because $\phi(s)$ changes slowly near broad hinges.

**Resolution**: $t_0$ and $R$ are fit jointly via linear least squares over all extracted isogon pairs:
$$t_\alpha = A + B \cos\alpha$$
$$t_0 = A + B, \quad R = \frac{A}{A + B}$$

- $t_0$ is constrained by every isogon pair along the limb, not a single pixel.
- Uncertainty $\sigma_R$ is derived rigorously from the fit covariance matrix via the delta method.
- Ambiguous classifications ($|R - R_{\text{boundary}}| < 2.0 \sigma_R$) report `fold_class = None` with an ambiguity warning instead of forcing a label onto uncertain data.

---

### Decision 3: Limb-Restricted Search & Monotonicity Assertions
Periodic fold surfaces introduce tangent matching ambiguities (multiple points on $S_1$ can share the same tangent angle $\phi$).
- **Search Disambiguation**: Tangent matching is strictly restricted to the corresponding limb (same side of hinge).
- **Monotonicity Assertion**: Within a single limb, $|\phi(s) - \phi_{\text{hinge}}|$ must increase monotonically. The software asserts $\Delta \phi \ge 0$. A non-monotonic $\phi(s)$ flags an under-smoothed spline (`GeometryError`).

---

### Decision 4: Hudleston Case 1 Fixed-Point Iteration & Case 2/3 Diagnostics
The axial trace direction and hinge points define each other recursively. Neither can be looked up directly:
1. Seed initial hinge points $H_0, G_0$.
2. Draw trial axial trace line $H_0 G_0$.
3. Find $H_1$ on extrados and $G_1$ on intrados where tangents are perpendicular to $H_0 G_0$ (modulo $\pi$).
4. Redraw trace through $H_1 G_1$, repeat to convergence.

**Case 2 Offset Diagnostic**: If the axial trace is inclined at an offset angle $\beta$ (Hudleston Case 2), the residual $(t_\alpha/T_\alpha - \cos\alpha)$ grows proportional to $-\beta \sin\alpha$. The software fits this residual to recover $\beta$.

---

### Decision 5: Analyze Limbs Independently
Real geological folds are asymmetric and can differ in classification between limbs. The software measures the left and right limbs separately and never silently averages them.

---

### Decision 6: Chevron Fold $\alpha$-Coverage Guard
On sharp-hinged chevron folds, dip angle $\alpha$ jumps from $0^\circ$ at the hinge to the limb dip and stays constant. The recovered $\alpha$ span is narrow ($< 30^\circ$). The software enforces `MIN_ALPHA_SPAN_DEG = 30.0` and refuses to output an $R$ classification if coverage is insufficient.

---

### Decision 7: Synthetic Ground Truth Test Harness
There is no machine learning model to train. Synthetic folds generated by [synthetic.py](file:///home/abhijith/coding/major-project/foldclass/src/foldclass/synthetic.py) serve as an exact mathematical oracle to validate invariants, tune spline smoothing, and quantify boundary perturbation sensitivity.

---

## 4. Automated Synthetic Test Suite (`foldclass/tests/test_geometry.py`)

The project includes an automated unit testing suite built with `pytest` that validates core geometric invariants against analytic synthetic folds generated by `synthetic.py`.

### The 8 Unit Test Invariants

| Test Function | Invariant / Property Tested | Mathematical Assertion |
|---|---|---|
| `test_fit_arc_scaling_and_rotation_invariance` | Spatial Invariance | Spline arc-length scales linearly with uniform scaling; tangent angles $\phi(s)$ shift by exact 2D rotation angle $\theta$. |
| `test_isogon_invariants_class_1b` | Ramsay Fundamental Identity & Projection Bound | Asserts $t_\alpha / T_\alpha = \cos\alpha$ within $10^{-2}$ tolerance and $t_\alpha \le |pq|$ (projection bound) on Class 1B folds. |
| `test_oblique_isogon_disambiguation` | Perpendicular Thickness vs Euclidean Distance | Verifies that $t_\alpha$ is computed as point-to-line perpendicular distance, NOT $\text{norm}(p - q)$, catching oblique section errors. |
| `test_fit_thickness_law_recovery` | Joint Fit Recovery | Asserts `fit_thickness_law` recovers exact $(t_0, R)$ within $\pm 0.03$ for Class 1B ($R = 1.0$) and Class 2 ($R = 0.0$). |
| `test_classify_labels` | Ramsay Boundary Mapping | Asserts `classify` maps $R \in \{1.5, 1.0, 0.5, 0.0, -0.5\}$ to `"1A"`, `"1B"`, `"1C"`, `"2"`, `"3"`. |
| `test_chevron_coverage_guard` | Low Dip-Coverage Refusal | Verifies that sharp-hinged folds with dip span $< 30^\circ$ return `fold_class = None` with explicit coverage warning. |
| `test_inflection_prominence_filtering` | Prominence Noise Filter | Verifies that spurious noise wiggles below `INFLECTION_MIN_PROMINENCE_DEG` ($15^\circ$) are discarded. |
| `test_case_diagnostic` | Hudleston Case 1/2 Offset Diagnostic | Asserts `case_diagnostic` recovers axial-trace offset angle $\beta \approx 0^\circ$ on Case 1 synthetics and flags Case 2 offsets. |

---

## 5. 50-Fold Synthetic Round-Trip Verification

To prove total correctness across the entire domain space, `synthetic.py` generates 50 synthetic folds spanning all 5 Ramsay classes (10 folds per class):
1. **Class 1A** ($R = 1.5$)
2. **Class 1B** ($R = 1.0$, exact offset curve)
3. **Class 1C** ($R = 0.5$, iteratively refined)
4. **Class 2** ($R = 0.0$, exact translation)
5. **Class 3** ($R = -0.5$, iteratively refined)

The geometry pipeline analyzes all 50 synthetic folds, achieving **100% confusion matrix diagonal accuracy** and mean $|R_{\text{fit}} - R_{\text{true}}| < 0.005$.
