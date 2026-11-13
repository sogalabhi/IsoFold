"""Choose the two lines that bound one bed (outer = extrados, inner = intrados) and the fold they share.
Every pair of complete lines is checked; each check that fails is recorded as a plain-English reason."""
import itertools

import numpy as np
from scipy.spatial import cKDTree
from foldclass import config

import prepare

N = 200                     # points per line for the gap profile
END = 0.05                  # nearest point within b's last 5% at either end = a runs past b there
MIN_OVERLAP = 0.7           # both ways
MAX_GAP_RATE = 1.0          # gap may change by at most 1 px per px along the line (lines meeting at > 45 deg)
MAX_SWAP = 0.02             # fraction of points allowed on the "wrong" side before we call it a crossing
MIN_GAP_PX = 10             # closer than this = one boundary traced twice (detector merges lines within 2x4+1 px)
MIN_LIMB_DEG = config.ALPHA_MIN_DEG     # each limb must turn at least this far from the hinge
BETWEEN_FRAC = 0.3          # another line lying between a and b for this much of the overlap = layer package
THICK = config.MIN_LAYER_THICKNESS_PX


def _profile(A, B):
    gap, idx = cKDTree(B).query(A)
    k = round(END * N)
    return gap, idx, (idx >= k) & (idx < N - k)


def _crosses(A, B, gap, idx, inside):
    # which side of b is a on? It must not change along the overlap (points within 2 px are ignored)
    t = np.gradient(B, axis=0)[idx]
    v = A - B[idx]
    side = np.sign(t[:, 0] * v[:, 1] - t[:, 1] * v[:, 0])[inside & (gap >= 2)]
    return len(side) > 0 and min((side > 0).mean(), (side < 0).mean()) > MAX_SWAP


def _faces(hinge, f):
    # does the point on f's line nearest to this hinge fall inside fold f?
    return f['i0'] <= int(np.argmin(np.hypot(*(f['q'] - hinge).T))) <= f['i1']


def _shared_folds(a, b):
    # folds present on both lines: each line's hinge faces the other line's fold. (Comparing the hinge points
    # directly fails on lopsided noses, where each line's hinge sits at a different place along the nose.)
    out = []
    for fa in prepare.fold_segments(a['pts']):
        for fb in prepare.fold_segments(b['pts']):
            if _faces(fa['hinge'], fb) and _faces(fb['hinge'], fa):
                out.append(dict(hinge_a=fa['hinge'], hinge_b=fb['hinge'],
                                limb_turn=min(*fa['limb_turn'], *fb['limb_turn'])))
    return sorted(out, key=lambda f: -f['limb_turn'])


def _between(lines, a, b, A, B, gap, overlap_len):
    # other lines that run between a and b: the "bed" is then several beds together
    ta, tb, ids = cKDTree(A), cKDTree(B), []
    lim = max(MIN_GAP_PX / 2, 0.2 * gap)      # closer than this to a or b = a duplicate trace of that boundary
    for c in lines:
        if c['id'] in (a['id'], b['id']):
            continue
        C = prepare.thin(c['pts'], N)
        da, db = ta.query(C)[0], tb.query(C)[0]
        n_between = ((da > lim) & (db > lim) & (da < gap) & (db < gap)).sum()
        length = np.hypot(*np.diff(C, axis=0).T).sum()
        if n_between * length / N >= BETWEEN_FRAC * overlap_len:
            ids.append(c['id'])
    return ids


def _check_fold(a, b, fold):
    # only the cut fold goes to the engine, so side-by-side, crossing and thickness are judged on it
    ca, _ = prepare.cut_at_inflections(a['pts'], fold['hinge_a'])
    cb, _ = prepare.cut_at_inflections(b['pts'], fold['hinge_b'])
    A, B = prepare.thin(ca, N), prepare.thin(cb, N)
    g_ab, i_ab, in_ab = _profile(A, B)
    g_ba, i_ba, in_ba = _profile(B, A)
    overlap = float(min(in_ab.mean(), in_ba.mean()))
    gap = float(np.median(g_ab[in_ab])) if in_ab.any() else float(np.median(g_ab))
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(A, axis=0).T))]
    rate = np.abs(np.gradient(np.convolve(g_ab, np.ones(5) / 5, 'same'), s))[in_ab]
    reasons = []
    if fold['limb_turn'] < MIN_LIMB_DEG:
        reasons.append(f'a limb of the shared fold turns only {fold["limb_turn"]:.0f} deg from the hinge (need {MIN_LIMB_DEG:.0f})')
    if gap < MIN_GAP_PX:
        reasons.append(f'the lines are only {gap:.0f} px apart, so they are probably one boundary traced twice')
    elif in_ab.any() and np.percentile(g_ab[in_ab], 5) < MIN_GAP_PX / 2:
        reasons.append('the lines touch within the fold')
    if len(rate) and rate.max() > MAX_GAP_RATE:
        reasons.append('the gap between the lines changes too fast (they meet at more than 45 deg): '
                       'one of them probably jumps to another boundary')
    if overlap < MIN_OVERLAP:
        reasons.append(f'within the fold the lines run side by side for only {overlap:.0%} of their length (need {MIN_OVERLAP:.0%})')
    if _crosses(A, B, g_ab, i_ab, in_ab) or _crosses(B, A, g_ba, i_ba, in_ba):
        reasons.append('the lines cross each other within the fold, so they are not the two boundaries of one bed')
    o = prepare.opening_direction(ca, fold['hinge_a'])
    return dict(fold, A=A, B=B, gap=gap, overlap=overlap, reasons=reasons, o=o)


def evaluate(a, b, lines):
    """Check one pair of lines. Returns the pair's numbers, which line is outer, and every failed check."""
    folds = [_check_fold(a, b, f) for f in _shared_folds(a, b)]
    res = dict(ids=(a['id'], b['id']))
    if not folds:
        return dict(res, median_gap_px=None, overlap=None, thick_enough=False, valid=False,
                    reasons=['the lines do not share a fold: neither hinge faces a fold on the other line'])
    f = next((f for f in folds if not f['reasons']), folds[0])      # the best-developed fold that passes
    res.update(median_gap_px=round(f['gap'], 1), overlap=round(f['overlap'], 3), thick_enough=f['gap'] >= THICK,
               reasons=f['reasons'], valid=not f['reasons'])
    # outer line = the one whose hinge lies further from the fold core (against the opening direction)
    a_outer = f['hinge_a'] @ -f['o'] > f['hinge_b'] @ -f['o']
    outer, inner = (a, b) if a_outer else (b, a)
    between = _between(lines, a, b, f['A'], f['B'], f['gap'], f['overlap'] * np.hypot(*np.diff(f['A'], axis=0).T).sum())
    res.update(outer_id=outer['id'], inner_id=inner['id'], layer_package=bool(between), between_ids=between,
               hinge_outer=(f['hinge_a'] if a_outer else f['hinge_b']),
               hinge_inner=(f['hinge_b'] if a_outer else f['hinge_a']),
               limb_turn_deg=round(f['limb_turn'], 1),
               # nothing reaches 90 px -> the thicker the better, since thickness is what limits reliability
               score=round(f['overlap'] * (a['strength'] + b['strength']) / 2 * min(f['gap'], THICK) / THICK, 4))
    return res


def rank_key(p):
    # thick enough first, then a single bed over a layer package; among thick pairs the thinnest (one bed),
    # otherwise the best score
    return (p['thick_enough'], not p['layer_package'], -p['median_gap_px'] if p['thick_enough'] else p['score'])


def choose(lines):
    """Best pair of complete lines, or None. Returns (best, every candidate checked, notes)."""
    complete = [d for d in lines if d['complete']]
    if len(complete) < 2:
        return None, [], ['no complete fold lines were found (a line must show both limbs and the hinge)'
                          if not complete else 'only one complete fold line was found; a bed needs two']
    cands = [evaluate(a, b, lines) for a, b in itertools.combinations(complete, 2)]
    valid = [c for c in cands if c['valid']]
    if not valid:
        return None, cands, ['no two complete lines bound the same bed (see the reasons for each pair)']
    return max(valid, key=rank_key), cands, []
