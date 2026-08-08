"""
Smoke test: trace one folded layer by hand and run the Ramsay dip-isogon
measurement on it.

This is NOT geometry.py. No synthetic validation has happened yet, and a
few things are simplified relative to Readme.md so this stays a single
file:

  - hinge/reference angle uses only the inflection-to-inflection chord
    (the non-iterative branch). The Case 1 fixed-point iteration for the
    axial trace is not implemented here.
  - R's uncertainty (sigma_R) is the raw delta-method estimate, not
    cross-checked against a boundary-perturbation study.

Treat any class this prints as "does the pipeline run end to end and look
geometrically sane," not "is this the correct class." That needs the
synthetic round-trip test, which comes later.

Usage:
    source .venv/bin/activate
    python3 trace_and_measure.py test-fold.png
"""
import argparse
from pathlib import Path

import numpy as np
from scipy.interpolate import splprep, splev
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt

ALPHA_MIN_DEG = 20.0
ALPHA_MAX_DEG = 70.0
ALPHA_STEP_DEG = 2.5
MIN_ALPHA_SPAN_DEG = 30.0
N_SAMPLES = 800
R_AMBIGUITY_SIGMA = 2.0


def angdiff(a, b):
    """a - b wrapped into (-pi, pi]."""
    return (a - b + np.pi) % (2 * np.pi) - np.pi


def click_trace(img, title, save_path):
    fig, ax = plt.subplots()
    ax.imshow(img)
    ax.set_title(f"{title}\nleft-click = add point, right-click = undo, enter = finish")
    pts = plt.ginput(n=-1, timeout=0)
    plt.close(fig)
    pts = np.array(pts)
    if len(pts) < 4:
        raise SystemExit(f"only {len(pts)} points clicked for '{title}' — need at least 4")
    np.savetxt(save_path, pts, delimiter=",", header="x,y", comments="")
    print(f"saved {len(pts)} points -> {save_path}")
    return pts


def get_trace(img, name, label, out_dir, retrace):
    csv_path = out_dir / f"{name}.csv"
    if csv_path.exists() and not retrace:
        print(f"reusing existing trace: {csv_path}")
        return np.loadtxt(csv_path, delimiter=",", skiprows=1)
    return click_trace(img, label, csv_path)


def fit_arc(points, smoothing):
    """Fit a smoothing spline, resample uniformly, return (s, xy, phi).
    phi is the analytic tangent angle from the spline's first derivative —
    never a finite difference on pixel coordinates."""
    tck, _ = splprep([points[:, 0], points[:, 1]], s=smoothing)
    u_dense = np.linspace(0, 1, N_SAMPLES)
    x, y = splev(u_dense, tck)
    xy = np.column_stack([x, y])
    seg = np.diff(xy, axis=0)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
    dx, dy = splev(u_dense, tck, der=1)
    phi = np.unwrap(np.arctan2(dy, dx))
    return s, xy, phi


def find_inflections(s, phi):
    """Arc-length positions of local extrema of phi(s)."""
    dphi = np.diff(phi)
    sign = np.sign(dphi)
    idx = np.where(np.diff(sign) != 0)[0] + 1
    return s[idx]


def limb_bounds(s, s_hinge, inflection_s):
    left = inflection_s[inflection_s < s_hinge]
    right = inflection_s[inflection_s > s_hinge]
    s_left = left.max() if len(left) else s[0]
    s_right = right.min() if len(right) else s[-1]
    left_is_real = len(left) > 0
    right_is_real = len(right) > 0
    return s_left, s_right, left_is_real, right_is_real


def xy_at(s_arr, xy_arr, s_query):
    return np.array([np.interp(s_query, s_arr, xy_arr[:, 0]),
                      np.interp(s_query, s_arr, xy_arr[:, 1])])


def phi_at(s_arr, phi_arr, s_query):
    return np.interp(s_query, s_arr, phi_arr)


def match_alpha(s_arr, phi_arr, s_hinge, s_bound, ref_angle, alpha_rad):
    """Find the arc-length position within [s_hinge, s_bound] (either order)
    where |phi - ref_angle| == alpha_rad. Returns (s_match, warning|None)."""
    lo, hi = sorted([s_hinge, s_bound])
    mask = (s_arr >= lo) & (s_arr <= hi)
    s_sub, phi_sub = s_arr[mask], phi_arr[mask]
    ds = np.abs(s_sub - s_hinge)
    order = np.argsort(ds)
    abs_phi = np.abs(angdiff(phi_sub[order], ref_angle))
    if np.any(np.diff(abs_phi) < -np.radians(1.0)):
        return None, "phi not monotonic within limb — likely under-smoothed"
    if alpha_rad > abs_phi[-1]:
        return None, None  # alpha simply out of this limb's range, not an error
    s_match = np.interp(alpha_rad, abs_phi, s_sub[order])
    return s_match, None


def line_point_distance(p, q, d):
    """Perpendicular distance from p to the line through q with unit direction d."""
    v = p - q
    return abs(v[0] * d[1] - v[1] * d[0])


def line_intersection_param(p, a_hat, q, d):
    """Solve p + u*a_hat = q + v*d for u (T_alpha, up to sign)."""
    A = np.array([[a_hat[0], -d[0]], [a_hat[1], -d[1]]])
    b = q - p
    if abs(np.linalg.det(A)) < 1e-9:
        return np.nan
    u, _ = np.linalg.solve(A, b)
    return u


def build_isogon_family(s_o, phi_o, xy_o, s_ho, s_bo,
                         s_i, phi_i, xy_i, s_hi, s_bi,
                         ref_o, ref_i, axial_dir, alphas_rad):
    pairs = []
    for a in alphas_rad:
        s_p, warn_p = match_alpha(s_o, phi_o, s_ho, s_bo, ref_o, a)
        s_q, warn_q = match_alpha(s_i, phi_i, s_hi, s_bi, ref_i, a)
        if warn_p:
            print(f"  alpha={np.degrees(a):.1f}: outer — {warn_p}")
        if warn_q:
            print(f"  alpha={np.degrees(a):.1f}: inner — {warn_q}")
        if s_p is None or s_q is None:
            continue
        p = xy_at(s_o, xy_o, s_p)
        q = xy_at(s_i, xy_i, s_q)
        phi_p = phi_at(s_o, phi_o, s_p)
        d = np.array([np.cos(phi_p), np.sin(phi_p)])
        t_a = line_point_distance(p, q, d)
        pq_len = np.linalg.norm(p - q)
        if t_a > pq_len + 1e-6:
            print(f"  WARNING alpha={np.degrees(a):.1f}: t_alpha > |pq| — geometry bug")
        T_a = abs(line_intersection_param(p, axial_dir, q, d))
        pairs.append(dict(alpha=a, p=p, q=q, t=t_a, T=T_a, pq=pq_len))
    return pairs


def fit_thickness_law(pairs):
    alphas = np.array([pr["alpha"] for pr in pairs])
    t = np.array([pr["t"] for pr in pairs])
    X = np.column_stack([np.ones_like(alphas), np.cos(alphas)])
    coef, *_ = np.linalg.lstsq(X, t, rcond=None)
    A, B = coef
    resid = t - X @ coef
    n, k = X.shape
    cov = np.full((2, 2), np.nan)
    if n > k:
        sigma2 = np.sum(resid ** 2) / (n - k)
        cov = sigma2 * np.linalg.inv(X.T @ X)
    t0 = A + B
    R = A / t0 if t0 != 0 else np.nan
    dRdA, dRdB = B / t0 ** 2, -A / t0 ** 2
    var_R = dRdA ** 2 * cov[0, 0] + dRdB ** 2 * cov[1, 1] + 2 * dRdA * dRdB * cov[0, 1]
    sigma_R = np.sqrt(var_R) if var_R >= 0 else np.nan
    return dict(A=A, B=B, t0=t0, R=R, sigma_R=sigma_R, alphas=alphas, t=t, resid=resid)


def case_diagnostic(pairs):
    """Fit (t/T - cos(alpha)) ~ -beta * sin(alpha), forced through the
    origin (Readme.md, Critical decision 4)."""
    alphas = np.array([pr["alpha"] for pr in pairs])
    ratio_resid = np.array([pr["t"] / pr["T"] - np.cos(pr["alpha"]) for pr in pairs])
    s = np.sin(alphas)
    denom = np.sum(s ** 2)
    beta = -np.sum(ratio_resid * s) / denom if denom > 0 else np.nan
    return beta


def classify(R, sigma_R, alpha_span_deg):
    if alpha_span_deg < MIN_ALPHA_SPAN_DEG:
        return None, f"sharp-hinged fold; alpha span {alpha_span_deg:.1f} deg < {MIN_ALPHA_SPAN_DEG} — dip isogon method poorly constrained"
    if not np.isnan(sigma_R):
        if abs(R - 1.0) < R_AMBIGUITY_SIGMA * sigma_R:
            return "1B", None
        if abs(R - 0.0) < R_AMBIGUITY_SIGMA * sigma_R:
            return "2", None
    if R > 1.0:
        return "1A", None
    if 0.0 < R < 1.0:
        return "1C", None
    if R < 0.0:
        return "3", None
    return None, "R exactly at a boundary with no usable sigma_R"


def process_limb(name, s_o, phi_o, xy_o, s_ho, s_bo,
                  s_i, phi_i, xy_i, s_hi, s_bi,
                  ref_o, ref_i, axial_dir):
    print(f"\n--- limb: {name} ---")
    alphas_rad = np.radians(np.arange(ALPHA_MIN_DEG, ALPHA_MAX_DEG + 1e-6, ALPHA_STEP_DEG))
    pairs = build_isogon_family(s_o, phi_o, xy_o, s_ho, s_bo,
                                 s_i, phi_i, xy_i, s_hi, s_bi,
                                 ref_o, ref_i, axial_dir, alphas_rad)
    if len(pairs) < 3:
        print(f"  only {len(pairs)} usable isogon pairs — cannot fit")
        return None, []
    alpha_span = np.degrees(max(pr["alpha"] for pr in pairs) - min(pr["alpha"] for pr in pairs))
    fit = fit_thickness_law(pairs)
    beta = case_diagnostic(pairs)
    fold_class, warning = classify(fit["R"], fit["sigma_R"], alpha_span)
    print(f"  n_pairs={len(pairs)}  alpha_span={alpha_span:.1f} deg")
    print(f"  t0={fit['t0']:.2f}px  R={fit['R']:.3f} +/- {fit['sigma_R']:.3f}")
    print(f"  case-diagnostic beta={np.degrees(beta):.2f} deg "
          f"({'looks like Case 1' if abs(np.degrees(beta)) < 3 else 'possible Case 2 offset'})")
    print(f"  class: {fold_class if fold_class else 'UNCLASSIFIED — ' + warning}")
    return fit, pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", default="test-fold.png")
    ap.add_argument("--retrace", action="store_true", help="ignore saved CSVs and re-click")
    ap.add_argument("--smoothing", type=float, default=None,
                     help="spline smoothing factor s (default: guessed from point count)")
    args = ap.parse_args()

    img_path = Path(args.image)
    out_dir = Path("traces")
    out_dir.mkdir(exist_ok=True)
    stem = img_path.stem

    img = plt.imread(img_path)

    outer_pts = get_trace(img, f"{stem}_outer", "OUTER boundary (extrados) — trace one continuous direction", out_dir, args.retrace)
    inner_pts = get_trace(img, f"{stem}_inner", "INNER boundary (intrados) — same direction as outer", out_dir, args.retrace)

    smoothing_o = args.smoothing if args.smoothing is not None else len(outer_pts) * 4.0
    smoothing_i = args.smoothing if args.smoothing is not None else len(inner_pts) * 4.0
    print(f"spline smoothing: outer={smoothing_o:.0f} inner={smoothing_i:.0f} (guessed — sweep.py will pick this properly later)")

    s_o, xy_o, phi_o = fit_arc(outer_pts, smoothing_o)
    s_i, xy_i, phi_i = fit_arc(inner_pts, smoothing_i)

    infl_o = find_inflections(s_o, phi_o)
    infl_i = find_inflections(s_i, phi_i)
    print(f"outer inflections found: {len(infl_o)}   inner inflections found: {len(infl_i)}")

    if len(infl_o) < 2 or len(infl_i) < 2:
        print("WARNING: fewer than 2 inflections on one boundary — reference angle "
              "falls back to the trace's own endpoints, which is a weaker proxy for "
              "the axial-plane direction. Trace further out along both limbs if possible.")

    # reference angle = chord between whatever bounds (inflections, or trace
    # ends as fallback) are available on each arc
    left_bound_o = infl_o[infl_o < s_o[len(s_o) // 2]].max() if np.any(infl_o < s_o[len(s_o) // 2]) else s_o[0]
    right_bound_o = infl_o[infl_o > s_o[len(s_o) // 2]].min() if np.any(infl_o > s_o[len(s_o) // 2]) else s_o[-1]
    ref_o = np.arctan2(*(xy_at(s_o, xy_o, right_bound_o) - xy_at(s_o, xy_o, left_bound_o))[::-1])

    left_bound_i = infl_i[infl_i < s_i[len(s_i) // 2]].max() if np.any(infl_i < s_i[len(s_i) // 2]) else s_i[0]
    right_bound_i = infl_i[infl_i > s_i[len(s_i) // 2]].min() if np.any(infl_i > s_i[len(s_i) // 2]) else s_i[-1]
    ref_i = np.arctan2(*(xy_at(s_i, xy_i, right_bound_i) - xy_at(s_i, xy_i, left_bound_i))[::-1])

    s_ho = s_o[int(np.argmin(np.abs(angdiff(phi_o, ref_o))))]
    s_hi = s_i[int(np.argmin(np.abs(angdiff(phi_i, ref_i))))]
    H = xy_at(s_o, xy_o, s_ho)
    G = xy_at(s_i, xy_i, s_hi)
    axial_dir = (G - H) / np.linalg.norm(G - H)
    print(f"hinge H (outer) at s={s_ho:.1f}, hinge G (inner) at s={s_hi:.1f}, |HG|={np.linalg.norm(G-H):.2f}px")

    s_lo, s_ro, _, _ = limb_bounds(s_o, s_ho, infl_o)
    s_li, s_ri, _, _ = limb_bounds(s_i, s_hi, infl_i)

    results = {}
    results["left"] = process_limb("left", s_o, phi_o, xy_o, s_ho, s_lo,
                                    s_i, phi_i, xy_i, s_hi, s_li, ref_o, ref_i, axial_dir)
    results["right"] = process_limb("right", s_o, phi_o, xy_o, s_ho, s_ro,
                                     s_i, phi_i, xy_i, s_hi, s_ri, ref_o, ref_i, axial_dir)

    # --- annotated plot ---
    fig, ax = plt.subplots(figsize=(8, 12))
    ax.imshow(img)
    ax.plot(xy_o[:, 0], xy_o[:, 1], "-", color="tab:orange", lw=1.5, label="outer (fitted)")
    ax.plot(xy_i[:, 0], xy_i[:, 1], "-", color="tab:cyan", lw=1.5, label="inner (fitted)")
    ax.plot(*H, "s", color="tab:orange", ms=8, mec="k", label="H (outer hinge)")
    ax.plot(*G, "s", color="tab:cyan", ms=8, mec="k", label="G (inner hinge)")
    ax.plot([H[0], G[0]], [H[1], G[1]], "k--", lw=1, label="axial trace")
    for name, color in [("left", "tab:red"), ("right", "tab:green")]:
        fit, pairs = results[name]
        for pr in pairs[::2]:
            ax.plot([pr["p"][0], pr["q"][0]], [pr["p"][1], pr["q"][1]], "-", color=color, lw=0.7, alpha=0.7)
    for s_val in infl_o:
        ax.plot(*xy_at(s_o, xy_o, s_val), "o", color="tab:orange", ms=5, mec="k")
    for s_val in infl_i:
        ax.plot(*xy_at(s_i, xy_i, s_val), "o", color="tab:cyan", ms=5, mec="k")
    title_bits = []
    for name in ["left", "right"]:
        fit, _ = results[name]
        if fit:
            title_bits.append(f"{name}: R={fit['R']:.2f}+/-{fit['sigma_R']:.2f}")
    ax.set_title("  |  ".join(title_bits))
    ax.legend(loc="upper right", fontsize=8)
    out_png = out_dir / f"{stem}_annotated.png"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"\nsaved annotated plot -> {out_png}")
    plt.show()


if __name__ == "__main__":
    main()
