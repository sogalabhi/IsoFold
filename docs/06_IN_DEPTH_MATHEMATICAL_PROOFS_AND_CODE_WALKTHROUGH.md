# Chapter 6: In-Depth Mathematical Proofs & Code Walkthrough

This chapter provides a detailed, rigorous breakdown of the mathematical proofs, line-by-line code walkthroughs, system demonstration workflows, and technical FAQ governing the geometry core.

---

## 1. Formal Mathematical Proofs & Derivations

### Proof 1: The Dip Isogon Projection Bound ($t_\alpha \le |pq|$)
**Domain Question**: *Why is layer thickness $t_\alpha$ computed as point-to-line perpendicular distance rather than Euclidean distance $|pq|$?*

**Mathematical Proof**:
1. Points $p$ (on extrados $S_0$) and $q$ (on intrados $S_1$) are identified purely by matching tangent angles: $\phi(p) = \phi(q)$.
2. Let $\hat{d} = (\cos\phi, \sin\phi)^T$ be the unit tangent vector, and $\hat{n} = (-\sin\phi, \cos\phi)^T$ be the unit normal vector perpendicular to the parallel tangents.
3. The displacement vector connecting the two points is $\mathbf{v} = p - q$.
4. The orthogonal thickness $t_\alpha$ is defined as the scalar projection of $\mathbf{v}$ onto the unit normal $\hat{n}$:
   $$t_\alpha = |\mathbf{v} \cdot \hat{n}| = |(p_x - q_x)(-\sin\phi) + (p_y - q_y)(\cos\phi)|$$
5. Using vector dot product properties, $\mathbf{v} \cdot \hat{n} = |\mathbf{v}| |\hat{n}| \cos\theta = |pq| \cdot 1 \cdot \cos\theta$, where $\theta$ is the angle between segment $pq$ and normal $\hat{n}$.
6. Since $|\cos\theta| \le 1$ for all real $\theta$:
   $$t_\alpha = |pq| \cdot |\cos\theta| \le |pq|$$
7. **Conclusion**: $|pq|$ is an upper bound on $t_\alpha$. Only when the isogon happens to be exactly perpendicular to the surface ($\theta = 0$) does $t_\alpha = |pq|$. Measuring $|pq|$ directly overestimates layer thickness and silently corrupts the Ramsay class.

---

### Proof 2: Joint Least-Squares Reparameterisation & Delta Method $\sigma_R$
**Domain Question**: *Why fit $t_0$ and $R$ jointly instead of measuring $t_0$ at the hinge and dividing?*

**Mathematical Derivation**:
1. Ramsay's thickness law states:
   $$t_\alpha = t_0 \cdot [R + (1 - R)\cos\alpha]$$
2. Single-point measurement of $t_0$ at the hinge ($\alpha = 0$) is poorly conditioned because tangent angle $\phi(s)$ changes slowly near broad hinges, introducing high positional variance.
3. We reparameterise by defining:
   $$A = t_0 R, \quad B = t_0 (1 - R)$$
   $$t_\alpha = A + B \cos\alpha$$
4. For $N$ isogon pairs $\{(\alpha_i, t_{\alpha, i})\}_{i=1}^N$, we formulate the linear system:
   $$\mathbf{X} \mathbf{c} = \mathbf{t}$$
   $$\mathbf{X} = \begin{bmatrix} 1 & \cos\alpha_1 \\ 1 & \cos\alpha_2 \\ \vdots & \vdots \\ 1 & \cos\alpha_N \end{bmatrix}, \quad \mathbf{c} = \begin{bmatrix} A \\ B \end{bmatrix}, \quad \mathbf{t} = \begin{bmatrix} t_{\alpha, 1} \\ t_{\alpha, 2} \\ \vdots \\ t_{\alpha, N} \end{bmatrix}$$
5. The Ordinary Least-Squares (OLS) solution is:
   $$\hat{\mathbf{c}} = (\mathbf{X}^T \mathbf{X})^{-1} \mathbf{X}^T \mathbf{t}$$
6. Physical parameters $t_0$ and $R$ are recovered directly:
   $$t_0 = A + B$$
   $$R = \frac{A}{A + B}$$
7. **Uncertainty Propagation (Delta Method)**:
   Let $\boldsymbol{\Sigma}_{\mathbf{c}} = \sigma^2 (\mathbf{X}^T \mathbf{X})^{-1}$ be the $2 \times 2$ covariance matrix of $(A, B)$, where $\sigma^2 = \frac{\|\mathbf{t} - \mathbf{X}\hat{\mathbf{c}}\|^2}{N - 2}$.
   The variance of $R = f(A, B) = \frac{A}{A + B}$ is given by first-order Taylor expansion:
   $$\text{Var}(R) \approx \left(\frac{\partial R}{\partial A}\right)^2 \text{Var}(A) + \left(\frac{\partial R}{\partial B}\right)^2 \text{Var}(B) + 2 \left(\frac{\partial R}{\partial A}\right)\left(\frac{\partial R}{\partial B}\right) \text{Cov}(A, B)$$
   Evaluating partial derivatives:
   $$\frac{\partial R}{\partial A} = \frac{B}{(A + B)^2} = \frac{B}{t_0^2}, \quad \frac{\partial R}{\partial B} = \frac{-A}{(A + B)^2} = \frac{-A}{t_0^2}$$
   Standard error $\sigma_R = \sqrt{\text{Var}(R)}$.

---

### Proof 3: Hudleston Case 2 Offset Diagnostic
**Domain Question**: *How is an inclined axial trace (Hudleston Case 2) detected mathematically?*

**Mathematical Derivation**:
1. If trial axial trace $HG$ is inclined by an offset angle $\beta$ relative to the true hinge perpendicular (Case 2), then axial plane thickness $T_\alpha$ satisfies:
   $$T_\alpha = \frac{t_\alpha}{\cos(\alpha + \beta)}$$
2. Expanding the denominator using cosine addition formula:
   $$\cos(\alpha + \beta) = \cos\alpha \cos\beta - \sin\alpha \sin\beta$$
3. For small offset angle $\beta$, $\cos\beta \approx 1$ and $\sin\beta \approx \beta$:
   $$\cos(\alpha + \beta) \approx \cos\alpha - \beta \sin\alpha$$
4. Rearranging:
   $$\frac{t_\alpha}{T_\alpha} \approx \cos\alpha - \beta \sin\alpha$$
   $$\frac{t_\alpha}{T_\alpha} - \cos\alpha \approx -\beta \sin\alpha$$
5. **Conclusion**: Fitting the residual $\left(\frac{t_\alpha}{T_\alpha} - \cos\alpha\right)$ against $\sin\alpha$ recovers $\beta$ directly. If $|\beta| < 3.0^\circ$, it is Hudleston Case 1 ($t_0 = T_0$). If $|\beta| \ge 3.0^\circ$, it is flagged as Case 2.

---

## 2. Line-by-Line Code Walkthrough ([geometry.py](file:///home/abhijith/coding/major-project/foldclass/src/foldclass/geometry.py))

### Function 1: `fit_arc(points, smoothing)`
```python
# Validate input shape (at least 4 points needed for cubic B-spline)
if len(points) < 4:
    raise ValueError(f"need at least 4 points to fit a cubic spline, got {len(points)}")

# Fit parametric B-spline with SciPy splprep (s = smoothing parameter)
tck, _ = splprep([points[:, 0], points[:, 1]], s=smoothing)

# Resample spline at n_samples (default 800) uniform parameter steps u
u = np.linspace(0.0, 1.0, n_samples)
x, y = splev(u, tck)
xy = np.column_stack([x, y])

# Compute arc length s by integrating Euclidean chord distances
seg = np.diff(xy, axis=0)
s = np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])

# Compute ANALYTIC FIRST DERIVATIVE dx/du, dy/du from spline (Never pixel diff!)
dx, dy = splev(u, tck, der=1)
phi = np.unwrap(np.arctan2(dy, dx)) # Tangent angle in radians, unwrapped
return Arc(s=s, xy=xy, phi=phi, tck=tck)
```

---

### Function 2: `find_inflections(arc, min_prominence_deg)`
```python
# Find sign changes in dphi (where dphi/ds changes direction)
dphi = np.diff(arc.phi)
sign = np.sign(dphi)
sign[sign == 0] = 1
candidates = np.where(np.diff(sign) != 0)[0] + 1

# PROMINENCE FILTER (Decision 3)
# Reject candidates unless phi swings by at least min_prominence_deg (15 deg) on both sides
critical = np.concatenate([[0], candidates, [len(arc.phi) - 1]])
kept = []
for i in range(1, len(critical) - 1):
    idx = critical[i]
    swing_prev = abs(arc.phi[idx] - arc.phi[critical[i - 1]])
    swing_next = abs(arc.phi[critical[i + 1]] - arc.phi[idx])
    if swing_prev >= min_prom and swing_next >= min_prom:
        kept.append(float(arc.s[idx]))
return kept
```

---

### Function 3: `find_hinge(arc, reference_angle)`
```python
# Match tangent angle phi against reference angle MODULO PI (2.0 * phi)
# Tangents are unoriented lines (phi == phi + pi mod pi)
idx = int(np.argmin(np.abs(_angdiff(2.0 * arc.phi, 2.0 * reference_angle))))
return float(arc.s[idx])
```

---

### Function 4: `isogon_pairs(...)`
```python
# For each dip angle alpha, find matching points p (outer) and q (inner)
for a in alphas:
    s_p = _match_alpha(outer, s_hinge_outer, s_bound_outer, ref_angle_outer, a)
    s_q = _match_alpha(inner, s_hinge_inner, s_bound_inner, ref_angle_inner, a)
    
    # Extract coordinates p and q
    p, q = xy_at(outer, s_p), xy_at(inner, s_q)
    
    # Compute tangent direction unit vector d = (cos phi, sin phi)
    phi_p = phi_at(outer, s_p)
    d = np.array([np.cos(phi_p), np.sin(phi_p)])
    
    # Calculate t_alpha as POINT-TO-LINE distance (NOT norm(p - q))
    t_a = _line_point_distance(p, q, d)
    pq_len = float(np.linalg.norm(p - q))
    
    # ASSERT PROJECTION BOUND t_alpha <= |pq|
    if t_a > pq_len + 1e-6:
        raise GeometryError(f"t_alpha ({t_a:.3f}) > |pq| ({pq_len:.3f}) -- geometry bug")
        
    # Solve p + u*a_hat = q + v*d for axial thickness T_alpha
    T_a = abs(_line_intersection_param(p, axial_trace.direction, q, d))
    pairs.append(IsogonPair(alpha=float(a), p=p, q=q, t=t_a, T=T_a, pq=pq_len))
```

---

## 3. End-to-End System Demonstration Workflow

Follow this command sequence for executing system demonstrations:

```bash
# -------------------------------------------------------------------------
# STEP 1: Run Synthetic Ground Truth Verification Harness (0% Error)
# -------------------------------------------------------------------------
python -m pytest foldclass/tests/test_geometry.py -v

# -------------------------------------------------------------------------
# STEP 2: Interactive GUI Tracing & Hinge Nose Seeding
# -------------------------------------------------------------------------
python tools/trace.py test-fold-2.png

# -------------------------------------------------------------------------
# STEP 3: Automated CLI Processing & Journal Figure Generation
# -------------------------------------------------------------------------
python tools/run.py test-fold-2.png

# -------------------------------------------------------------------------
# STEP 4: Custom Dip Angle Filtering & De-congested Clean View
# -------------------------------------------------------------------------
python tools/run.py test-fold-2.png -a 20,40,60 -l right -c -o traces/test-fold-2_right_clean.png

# -------------------------------------------------------------------------
# STEP 5: Structure Tensor Orientation Field & Frangi Multi-Layer Extraction
# -------------------------------------------------------------------------
python tools/orientation_isogons.py test-fold-2.png
```

---

## 4. Frequently Asked Technical & Methodological Questions (FAQ)

### Q1: *Why does the system avoid machine learning or neural networks for classification?*
**Answer**: Ramsay's fold classification is defined by deterministic mathematical inequalities ($t'_\alpha = t_\alpha / t_0$). Machine learning is non-deterministic and requires massive training datasets. Once boundary curves are extracted, the geometry engine returns the exact, mathematically proven Ramsay class with zero training requirement and zero hallucination risk.

### Q2: *How are asymmetric folds handled when two limbs differ in shape?*
**Answer**: Decision 5 requires analyzing the left and right limbs completely independently. We fit $t_\alpha = A + B\cos\alpha$ separately for each limb, recovering separate $R_{\text{left}}$ and $R_{\text{right}}$ values rather than averaging them into a single misleading number.

### Q3: *What happens if the fold has a sharp chevron hinge?*
**Answer**: Chevron folds have straight limbs, so dip angle $\alpha$ stays constant along each limb. Decision 6 enforces an $\alpha$-span coverage check (`MIN_ALPHA_SPAN_DEG = 30.0`). If recovered dip angles span less than $30^\circ$, the tool refuses to report a numeric class and outputs `"sharp-hinged fold; dip isogon method poorly constrained"`.

### Q4: *Does this software operate completely offline?*
**Answer**: Yes, 100% offline. All computations run locally on the CPU using NumPy and SciPy. There are no web API calls or remote dependencies.
