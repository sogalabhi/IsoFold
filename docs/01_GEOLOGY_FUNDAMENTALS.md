# Chapter 1: Structural Geology Textbook Fundamentals

This chapter outlines the theoretical foundations of structural geology, profile geometry, dip isogon analysis, and shape quantification as established in classic domain literature (*Ramsay 1967*, *Ramsay & Huber 1987*, *Ghosh 1993*, *Stabler 1968*, *Hudleston 1973*, *Hatui & Chattopadhyay 2020*).

---

## 1. Structural Profile Elements

A geological fold viewed in **profile section** (a planar cross-section cut perpendicular to the fold axis) reveals two bounding surfaces of a deformed rock layer:

1. **Extrados ($S_0$)**: The outer, convex bounding surface of the fold layer.
2. **Intrados ($S_1$)**: The inner, concave bounding surface of the fold layer.
3. **Core**: The region enclosed on the concave side of the intrados.

```
                    Extrados (S0 - Outer Surface)
                  /-------------------------------\
                 /           FOLD LAYER            \
                /  /---------------------------\  \
               /  /   Intrados (S1 - Inner)     \  \
              /  /                               \  \
             /  /            CORE                 \  \
```

### Key Reference Points & Surfaces
- **Inflection Point**: The point on a surface where curvature changes sign ($\frac{d^2y}{dx^2} = 0$). Operationally, it is a local extremum of the tangent angle function $\phi(s)$ along arc length $s$.
- **Hinge Point**: The point on a surface where the tangent is perpendicular to the axial trace direction. Operationally, it is the point where tangent angle $\phi(s)$ equals the hinge reference angle.
- **Axial Trace ($S_2$)**: The line connecting corresponding hinge points on successive surfaces ($H$ on extrados, $G$ on intrados).
- **Limb**: The segment of a surface bounded between a hinge point and the adjacent inflection point.
- **Interlimb Angle ($\theta_{il}$)**: The angle subtended between the maximum dip tangents of opposite limbs ($\theta_{il} = 180^\circ - |\phi_{\text{left}} - \phi_{\text{right}}|$).

---

## 2. The Ramsay Dip Isogon Construction

A **dip isogon** is a line connecting a point $p$ on the outer surface ($S_0$) to a point $q$ on the inner surface ($S_1$) where the tangent to $S_0$ at $p$ is **parallel** to the tangent to $S_1$ at $q$.

### Isogon Orientation & Orientation Families
As dip angle $\alpha$ varies from $0^\circ$ at the hinge to maximum dip at the inflection point, dip isogons fan out into an **isogon family**. At $\alpha = 0^\circ$, $p = H$ and $q = G$, making the $0^\circ$ isogon identical to the **axial trace segment $HG$**.

```
                p (outer point, tangent angle phi)
               / \
              /   \      Tangent line at p  (parallel)
             /     \===================================
            /       \         ^
           /    |pq| \        | t_alpha (perpendicular distance)
          /           \       v
         /=============\==============================
        /               \   Tangent line at q  (parallel)
       /                 q (inner point, same tangent angle phi)
```

### Thickness Definitions & The Projection Bound Trap
- **Orthogonal Thickness ($t_\alpha$)**: The perpendicular distance between the two parallel tangent lines through $p$ and $q$.
- **Axial Plane Thickness ($T_\alpha$)**: The distance between the parallel tangents measured along a line parallel to the axial trace.

> [!CAUTION]
> **Implementation Trap: $t_\alpha \neq |pq|$**
> The point $q$ is found purely by matching tangent angles ($\phi(p) = \phi(q)$). Nothing forces the segment $pq$ to lie along the surface normal. If $\theta$ is the angle between segment $pq$ and the common normal vector $\hat{n}$, then:
> $$t_\alpha = |pq| \cdot \cos\theta$$
> Only when the isogon happens to be normal to the surface does $t_\alpha = |pq|$. In general, $t_\alpha < |pq|$.
>
> **Free Runtime Guard**: $t_\alpha \le |pq|$ always holds (projection bound). The software asserts this invariant on every extracted pair.

The relationship between $t_\alpha$ and $T_\alpha$ is given by Ramsay's Fundamental Equation:
$$t_\alpha / T_\alpha = \cos\alpha$$

At the hinge ($\alpha = 0^\circ$), $\cos(0^\circ) = 1$, so $t_0 = T_0 = |HG|$ (provided Hudleston Case 1 hinge perpendicularity holds).

---

## 3. Ramsay Fold Classification

Ramsay (1967) classified folds based on how dip isogons behave relative to the core and how normalized orthogonal thickness $t'_\alpha = t_\alpha / t_0$ varies with dip angle $\alpha$:

| Class | Dip Isogon Pattern | Condition on $t'_\alpha$ | Common Geological Term |
|---|---|---|---|
| **Class 1A** | Strongly Convergent towards core | $t'_\alpha > 1$ | Supratenuous fold |
| **Class 1B** | Convergent towards core | $t'_\alpha = 1$ (Constant) | Parallel / Concentric fold |
| **Class 1C** | Weakly Convergent towards core | $\cos\alpha < t'_\alpha < 1$ | Modified parallel fold |
| **Class 2** | Parallel to each other ($T'_\alpha = 1$) | $t'_\alpha = \cos\alpha$ | Similar fold |
| **Class 3** | Divergent towards core | $t'_\alpha < \cos\alpha$ | Flattened / Divergent fold |

```
    Class 1A              Class 1B              Class 1C             Class 2               Class 3
 (Convergent)          (Parallel t'=1)       (Weak Converg.)      (Similar T'=1)        (Divergent)
   \   /                  |   |                 \   /                |||                  /   \
    \ /                   |   |                  \ /                 |||                 /     \
     v                    |   |                   v                  |||                v       v
```

---

## 4. The $R$ Index & Joint Thickness Law Fit

Rather than evaluating $t'_\alpha$ with arbitrary conditional thresholds, Ramsay defined the normalized **$R$ index**:
$$R(\alpha) = \frac{t'_\alpha - \cos\alpha}{1 - \cos\alpha}$$

| $R$ Index | Ramsay Class | Physical Interpretation |
|---|---|---|
| $R > 1.0$ | **Class 1A** | Layer thickens away from hinge |
| $R = 1.0$ | **Class 1B** | Ideal parallel fold; constant orthogonal thickness |
| $0 < R < 1.0$ | **Class 1C** | Intermediate thinning between Class 1B and Class 2 |
| $R = 0.0$ | **Class 2** | Ideal similar fold; constant axial thickness $T_\alpha = T_0$ |
| $R < 0.0$ | **Class 3** | Severe thinning on limbs relative to hinge |

### Joint Thickness Fit (Critical Decision 2)
Measuring $t_0$ as a single point at the hinge is unstable because $\phi(s)$ varies slowly near broad hinges. The software reformulates Ramsay's thickness law:
$$t_\alpha = t_0 \cdot [R + (1 - R)\cos\alpha]$$

Substituting $A = t_0 R$ and $B = t_0 (1 - R)$:
$$t_\alpha = A + B \cos\alpha$$

This is a linear least-squares fit over the basis $\{1, \cos\alpha\}$ using every isogon pair in the reliable range $\alpha \in [20^\circ, 70^\circ]$. The physical parameters are recovered as:
$$t_0 = A + B$$
$$R = \frac{A}{A + B}$$

Uncertainty $\sigma_R$ is derived via the delta method from the covariance matrix of $(A, B)$.

---

## 5. Fourier Shape Analysis (Stabler & Hudleston Methods)

A periodic symmetric fold profile $y(x)$ with origin at the inflection point can be expanded in an odd sine Fourier series:
$$y(x) = a_1 \sin x + a_3 \sin 3x + a_5 \sin 5x + \dots \quad (a_1 > a_3 > a_5)$$

### Stabler Three-Point Method (1968)
Given a quarter wavelength $b$ (inflection to adjacent hinge), hinge amplitude $a$, and y-values $y_1, y_2$ at $x = b/3$ and $x = 2b/3$:
$$a_1 = \frac{a + y_1}{3} + 0.577 \cdot y_2$$
$$a_3 = \frac{2y_1 - a}{3}$$
$$a_5 = \frac{a + y_1}{3} - 0.577 \cdot y_2$$

### Hudleston Numerical Integration (1973) & $b_1-b_3$ Chart
For densely sampled curves, numerical integration yields robust harmonic ratios $T/F = a_3/a_1$:
- **Positive $T/F$**: Rounded hinge (parabola / semi-ellipse).
- **Negative $T/F$**: Sharp hinge (chevron fold).
- **Hudleston Shape Letters (A–F)**: Box $\to$ Semi-ellipse $\to$ Parabola $\to$ Sine $\to$ Chevron.
- **Hudleston Amplitude Numbers (1–5)**: Increasing amplitude-to-wavelength ratio.

---

## 6. Multi-Layer Deformation & Disharmony

In multi-layer rock sequences, adjacent layers deform according to their relative mechanical competence:
- **Competent Beds** (e.g., Quartzite/Sandstone): Resist ductile flow $\to$ maintain constant thickness ($R \approx 1.0$, Class 1B/1C).
- **Incompetent Beds** (e.g., Shale/Schist): Flow into fold cores $\to$ undergo severe thinning ($R < 0$, Class 3).

### Disharmony Index $B(h)$
Ghosh (§12.5) defines disharmonic folding where adjacent layers differ strongly in wavelength or fold class. With multi-layer trace extraction, the variance of $R$ across neighboring beds quantifies disharmony across the outcrop stack.
