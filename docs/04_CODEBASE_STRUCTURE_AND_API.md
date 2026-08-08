# Chapter 4: Codebase Architecture & API Reference

This chapter details the codebase structure, module responsibilities, function signatures, data structures, and exception types in the `foldclass` core package.

---

## 1. Package Module Map (`foldclass/src/foldclass/`)

```
foldclass/src/foldclass/
├── __init__.py
├── config.py         # Central registry for named constants and thresholds
├── geometry.py       # Pure NumPy + SciPy geometry engine (C++ port target)
├── synthetic.py      # Analytical fold synthetic generators & oracle
├── debug.py          # Intermediate stage extraction & 6-panel visual grid
└── plots.py          # Publication-quality annotated figure rendering
```

---

## 2. API Reference: `foldclass.config`

Central configuration file storing all quantitative thresholds with their provenance comments:

```python
ALPHA_MIN_DEG = 20.0             # R denominator (1 - cos alpha) -> 0 below this
ALPHA_MAX_DEG = 70.0             # Tangent matching unreliable near inflection
ALPHA_STEP_DEG = 2.5            # Alpha sweep sampling step
MIN_ALPHA_SPAN_DEG = 30.0        # Chevron guard: minimum dip span required to classify

INFLECTION_MIN_PROMINENCE_DEG = 15.0 # Minimum phi swing to count as genuine inflection

MAX_ISOGON_LENGTH_FACTOR = 3.0   # Reject pairs with |pq| > factor * typical_separation

AXIAL_TRACE_MAX_ITER = 20        # Fixed-point iteration cap
AXIAL_TRACE_TOL_DEG = 0.5        # Fixed-point convergence tolerance

HG_SEPARATION_RATIO_MIN = 0.5    # H/G separation plausibility bounds
HG_SEPARATION_RATIO_MAX = 2.0
T0_MIN_SEPARATION_FRACTION = 0.3 # Minimum t0 fit fraction check
```

---

## 3. API Reference: `foldclass.geometry`

The core mathematical engine. Dependent **ONLY on NumPy and SciPy**.

### Core Data Structures
```python
@dataclass
class Arc:
    s: np.ndarray        # Arc length samples
    xy: np.ndarray       # (N, 2) coordinates
    phi: np.ndarray      # Unwrapped tangent angle in radians
    tck: tuple            # Underlying SciPy spline tuple

@dataclass
class Line:
    point: np.ndarray    # Reference point (2,)
    direction: np.ndarray # Unit direction vector (2,)

@dataclass
class IsogonPair:
    alpha: float         # Dip angle in radians
    p: np.ndarray        # Outer surface point (2,)
    q: np.ndarray        # Inner surface point (2,)
    t: float             # Perpendicular thickness t_alpha
    T: float             # Axial plane thickness T_alpha
    pq: float            # Segment distance |p - q|

@dataclass
class ThicknessFit:
    A: float
    B: float
    t0: float            # Fitted hinge thickness (A + B)
    R: float             # Fitted R index (A / (A + B))
    sigma_R: float       # Delta-method uncertainty estimate
    residuals: np.ndarray

@dataclass
class CaseDiagnostic:
    beta: float          # Fitted axial trace offset angle in radians
    case: int            # 1 (Hudleston Case 1) or 2 (Hudleston Case 2)

@dataclass
class ClassResult:
    r_mean: float
    r_std: float
    fold_class: str | None # "1A", "1B", "1C", "2", "3", or None if ambiguous/refused
    alpha_span: float
    n_samples: int
    fit: ThicknessFit
    warnings: list[str]
```

### Core Functions
```python
def fit_arc(points: np.ndarray, smoothing: float, n_samples: int = 800) -> Arc:
    """Fits B-spline to boundary points and computes analytic tangent angle phi(s)."""

def find_inflections(arc: Arc, min_prominence_deg: float | None = None) -> list[float]:
    """Finds extrema of phi(s) filtered by prominence threshold."""

def find_hinge(arc: Arc, reference_angle: float) -> float:
    """Finds arc-length position where phi(s) equals reference_angle (modulo pi)."""

def find_axial_trace(outer: Arc, inner: Arc, seed_s_outer: float, seed_s_inner: float,
                      max_iter: int | None = None, tol_deg: float | None = None,
                      separation: float | None = None) -> tuple[float, float, Line, list[str]]:
    """Runs Hudleston Case 1 fixed-point iteration to converge hinges H and G."""

def isogon_pairs(outer: Arc, inner: Arc, s_hinge_outer: float, s_bound_outer: float,
                  s_hinge_inner: float, s_bound_inner: float, ref_angle_outer: float,
                  ref_angle_inner: float, axial_trace: Line, alphas: np.ndarray,
                  limb: Literal["left", "right"], separation: float | None = None) -> list[IsogonPair]:
    """Extracts dip isogon pairs along a limb and asserts t_alpha <= |pq| projection bound."""

def fit_thickness_law(pairs: list[IsogonPair], separation: float | None = None) -> ThicknessFit:
    """Jointly fits t_alpha = A + B*cos(alpha) for t0 and R index."""

def case_diagnostic(pairs: list[IsogonPair]) -> CaseDiagnostic:
    """Fits (t/T - cos alpha) against -beta*sin(alpha) for Hudleston Case 1/2 detection."""

def classify(fit: ThicknessFit, alpha_span_deg: float, n_samples: int) -> ClassResult:
    """Assigns Ramsay class from fit and enforces chevron alpha-span coverage guard."""
```

### Exception Type
```python
class GeometryError(RuntimeError):
    """Raised when a geometric invariant assertion fails (e.g. t_alpha > |pq| or |HG| implausible)."""
```

---

## 4. API Reference: `foldclass.synthetic`

Analytical test harness oracle:

```python
def generate(R: float, t0: float = 25.0, scale: float = 100.0, amplitude_ratio: float = 1.1,
             half_width_rad: float = 1.3, n_points: int = 400, refine: bool = True) -> SyntheticFold:
    """Generates analytical synthetic fold at exact target R (Class 1B, 2, 1A, 1C, 3)."""
```

---

## 5. API Reference: `foldclass.debug`

Intermediate stage inspection:

```python
def debug_pipeline(outer_pts: np.ndarray, inner_pts: np.ndarray,
                   truth: Optional[SyntheticFold] = None,
                   smoothing_o: Optional[float] = None, smoothing_i: Optional[float] = None,
                   seed_hinge: Optional[Tuple[float, float]] = None,
                   save_path: Optional[str] = None) -> Dict[str, Any]:
    """Executes geometry analysis stage-by-stage and plots 6-panel visual grid."""
```

---

## 6. API Reference: `foldclass.plots`

Publication figure generation:

```python
def plot_annotated_fold(img: np.ndarray, results: Dict[str, Any], output_path: str = "annotated_fold.png",
                       highlight_alphas_deg: Optional[list[float]] = None,
                       hide_other_isogons: bool = False,
                       limbs_to_show: Optional[list[str]] = None) -> None:
    """Renders single annotated outcrop section diagram with custom dip angle & limb filtering."""

def plot_publication_figure(img: np.ndarray, results: Dict[str, Any], output_path: str = "publication_figure.png") -> None:
    """Renders 2-panel journal figure with annotated outcrop photo and Ramsay t'alpha chart."""
```
