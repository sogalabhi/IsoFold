"""Turn two detected lines into what the frozen engine expects: one fold only, both traced the same way,
~60 evenly spaced points. Moved from run_pairs_experiment.py; cutting now works for any fold orientation
and for lines that run through several folds."""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from foldclass import config

PROMINENCE = np.radians(config.INFLECTION_MIN_PROMINENCE_DEG)   # same rule as the engine's inflections


def thin(p, n=60):
    # resample evenly along the line
    seg = np.hypot(*np.diff(p, axis=0).T)
    t = np.r_[0, np.cumsum(seg)]
    u = np.linspace(0, t[-1], n)
    return np.stack([np.interp(u, t, p[:, 0]), np.interp(u, t, p[:, 1])], 1)


def _phi(q):
    # tangent angle along the line, lightly smoothed
    d = np.gradient(q, axis=0)
    return gaussian_filter1d(np.unwrap(np.arctan2(d[:, 1], d[:, 0])), 8)


def fold_segments(p, n=400):
    """Split a line into folds at its inflections (turning points of the tangent angle). Each fold has a hinge
    and the turn of each limb away from the hinge, in degrees. The hinge is where the tangent lies halfway
    between the two limb ends: on a broad round nose the sharpest-turn point wanders, this does not."""
    q = thin(p, n)
    phi = _phi(q)
    ext = sorted(np.r_[find_peaks(phi, prominence=PROMINENCE)[0], find_peaks(-phi, prominence=PROMINENCE)[0]])
    bounds = [0] + [int(i) for i in ext] + [n - 1]
    folds = []
    for i0, i1 in zip(bounds[:-1], bounds[1:]):
        ih = i0 + int(np.argmin(np.abs(phi[i0:i1 + 1] - (phi[i0] + phi[i1]) / 2)))
        folds.append(dict(q=q, i0=i0, ih=ih, i1=i1, hinge=q[ih], limb_turn=(float(np.degrees(abs(phi[i0] - phi[ih]))),
                                                  float(np.degrees(abs(phi[i1] - phi[ih]))))))
    return folds


def _walk(dev):
    # follow dev outward from the hinge; stop once it has fallen well below its peak (past the inflection)
    best = 0
    for i, v in enumerate(dev):
        if v > dev[best]:
            best = i
        elif dev[best] - v > PROMINENCE:
            break
    return best


def cut_at_inflections(p, hinge):
    """Keep one fold only: from the steepest point on one limb to the steepest point on the other, walking out
    from the given hinge. Returns the cut line and the largest dip (deg, relative to the hinge) at its start and end."""
    q = thin(p, 400)
    phi = _phi(q)
    h = int(np.argmin(np.hypot(*(q - hinge).T)))
    dev = np.abs(phi - phi[h])
    iL, iR = h - _walk(dev[h::-1]), h + _walk(dev[h:])
    return q[iL:iR + 1], (float(np.degrees(dev[iL])), float(np.degrees(dev[iR])))


def opening_direction(p, hinge):
    # unit vector from the hinge towards the middle of the two limb ends, i.e. into the fold core
    o = (p[0] + p[-1]) / 2 - np.asarray(hinge, float)
    return o / (np.linalg.norm(o) + 1e-9)


def same_direction(outer, inner):
    # the engine needs both boundaries traced the same way; returns (inner, was_reversed)
    if np.dot(outer[-1] - outer[0], inner[-1] - inner[0]) < 0:
        return inner[::-1], True
    return inner, False
