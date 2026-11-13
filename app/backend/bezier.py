"""Cubic Bezier paths as the web app's pen tool draws them, and the one sampling rule both the app and the
examples use.

A path is a list of anchors {"p": [x, y], "in": [x, y] | None, "out": [x, y] | None} in image pixels: the
segment between anchors i and i+1 has control points p_i, out_i, in_{i+1}, p_{i+1} (a missing handle sits on
its anchor, i.e. a straight-ish corner). The browser only draws paths; turning them into points for the engine
happens here, so there is a single sampling rule.

SAMPLES_PER_SEGMENT = 24 is what dataset/traces/parse_svg.py used on the CorelDraw curves, so a CorelDraw
trace and the same curve drawn in the app reach the engine as the same points."""
import numpy as np

SAMPLES_PER_SEGMENT = 24


def _ctrl(a, b):
    p0, p3 = np.asarray(a['p'], float), np.asarray(b['p'], float)
    p1 = np.asarray(a['out'], float) if a.get('out') is not None else p0
    p2 = np.asarray(b['in'], float) if b.get('in') is not None else p3
    return p0, p1, p2, p3


def _bernstein(t):
    t = np.asarray(t, float)[:, None]
    return np.hstack([(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3])


def sample(anchors, per_segment=SAMPLES_PER_SEGMENT):
    """Anchors -> (N, 2) points: the first anchor, then per_segment points per segment (t = 1/n .. 1)."""
    if len(anchors) < 2:
        return np.array([a['p'] for a in anchors], float).reshape(-1, 2)
    B = _bernstein(np.linspace(0, 1, per_segment + 1)[1:])
    pts = [np.asarray(anchors[0]['p'], float)[None]]
    for a, b in zip(anchors[:-1], anchors[1:]):
        pts.append(B @ np.stack(_ctrl(a, b)))
    return np.vstack(pts)


def from_samples(points, per_segment=SAMPLES_PER_SEGMENT, tol=0.05):
    """Recover the anchors of a path sampled like parse_svg.sample_path: a cubic segment is per_segment+1
    points (its four control points then follow exactly by least squares on the Bernstein basis), a straight
    segment is one point. Walk along: if the next per_segment+1 points are an exact cubic (to `tol` px, the
    rounding of the stored points) take it, else take one straight step. Falls back to fit() if that yields
    nothing curved."""
    P = np.asarray(points, float)
    B = _bernstein(np.linspace(0, 1, per_segment + 1))
    anchors = [{'p': P[0].tolist(), 'in': None, 'out': None}]
    i, n_curves = 0, 0
    while i < len(P) - 1:
        if i + per_segment < len(P):
            seg = P[i:i + per_segment + 1]
            c, *_ = np.linalg.lstsq(B, seg, rcond=None)
            if np.abs(B @ c - seg).max() < tol:
                anchors[-1]['out'] = c[1].tolist()
                anchors.append({'p': seg[-1].tolist(), 'in': c[2].tolist(), 'out': None})
                i += per_segment
                n_curves += 1
                continue
        anchors.append({'p': P[i + 1].tolist(), 'in': None, 'out': None})      # straight piece
        i += 1
    return _rounded(anchors) if n_curves else fit(P)


def fit(points, n_anchors=None):
    """Any polyline -> a smooth path through anchors evenly spaced along it, with handles along the line's own
    tangent, a third of the way to the neighbouring anchor (Hermite-to-Bezier). Used when a line was not
    sampled per segment."""
    P = np.asarray(points, float)
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    n = n_anchors or int(np.clip(round(s[-1] / 250), 4, 14))
    sa = np.linspace(0, s[-1], n)
    A = np.stack([np.interp(sa, s, P[:, 0]), np.interp(sa, s, P[:, 1])], 1)
    eps = 0.02 * s[-1] / n
    ahead = np.stack([np.interp(np.minimum(sa + eps, s[-1]), s, P[:, k]) for k in (0, 1)], 1)
    behind = np.stack([np.interp(np.maximum(sa - eps, 0), s, P[:, k]) for k in (0, 1)], 1)
    T = ahead - behind
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    anchors = []
    for i in range(n):
        back = (sa[i] - sa[i - 1]) / 3 if i > 0 else None
        fwd = (sa[i + 1] - sa[i]) / 3 if i < n - 1 else None
        anchors.append({'p': A[i].tolist(), 'in': None if back is None else (A[i] - back * T[i]).tolist(),
                        'out': None if fwd is None else (A[i] + fwd * T[i]).tolist()})
    return _rounded(anchors)


def _rounded(anchors):
    r = lambda v: None if v is None else [round(float(v[0]), 2), round(float(v[1]), 2)]
    return [{'p': r(a['p']), 'in': r(a['in']), 'out': r(a['out'])} for a in anchors]
