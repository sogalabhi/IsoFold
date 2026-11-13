"""Hand-traced bed -> result dict, for the IsoFold Trace web app (plan.md, section 5).

The user traces the outer and inner boundary of ONE bed. This runs the same steps that reproduced the
hand-measured R on the CorelDraw traces (dataset/traces/run_engine_on_traces.py):
pairing.evaluate (hinges, which line is outer) -> pipeline.run_engine (cut to one fold, same direction,
thin, frozen engine). The class always comes from the engine's own 20-70 deg grid; the angles the user picks
only choose which isogons are drawn and listed. No web code here: the API, the CLI and the tests call classify().

Usage:  python manual.py Fold_11 [--angles 30,45,60] [--out check.jpg]    # an example from examples.py
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from foldclass import config
from foldclass import geometry as geo

import pairing
import pipeline

VALIDATED_DIP_DEG = 54.0          # synthetic validation covered limb dips up to this (HANDOFF.md)
MAX_MATCH_DEG = 75.0              # debug_pipeline clamps each limb where it turns past this
FIT_RANGE = (config.ALPHA_MIN_DEG, config.ALPHA_MAX_DEG)


# --- copied from foldclass.debug.debug_pipeline (nested helper there, so it cannot be imported; the engine is
# frozen, so it is copied rather than moved). Must stay identical so display isogons use the same limb bounds.
def _clamp_limb_bound(arc, s_hinge, s_end, max_alpha_deg=MAX_MATCH_DEG):
    step = 1 if s_end >= s_hinge else -1
    mask = (arc.s >= min(s_hinge, s_end)) & (arc.s <= max(s_hinge, s_end))
    s_sub = arc.s[mask]
    if len(s_sub) < 2:
        return s_end
    if step == -1:
        s_sub = s_sub[::-1]
    ref = geo.phi_at(arc, s_hinge)
    phi_sub = arc.phi[mask] if step == 1 else arc.phi[mask][::-1]
    abs_phi = np.abs(geo._angdiff(phi_sub, ref))
    exceeded = np.where(abs_phi > np.radians(max_alpha_deg))[0]
    if len(exceeded) > 0:
        first_cut = max(exceeded[0] - 1, 0)
        return float(s_sub[first_cut])
    return float(s_sub[-1])


# engine refusals -> plain English, with what to do about it
_PLAIN = [
    ('not monotonic', 'The tangent direction doubles back within a limb. Smooth the line there, '
                      'or end it before it runs into the next fold.'),
    ('|HG|', "The hinge points of the two lines don't correspond. Make sure both lines cover the same fold "
             'and pass its hinge.'),
    ('implausibly small', 'The fitted layer thickness is far smaller than the gap between the lines, so the two '
                          'lines probably do not bound the same bed.'),
    ('isogon pairs', 'Too few matching tangent pairs. Extend both lines further down the limbs.'),
]


def plain_reason(msg):
    return next((p for key, p in _PLAIN if key in msg), 'The engine could not measure this pair of lines.')


def _r(v, n=1):
    return None if v is None or not np.isfinite(v) else round(float(v), n)


def _pt(p):
    return [round(float(p[0]), 1), round(float(p[1]), 1)]


def _pt4(v):
    return [round(float(v[0]), 4), round(float(v[1]), 4)]


def _unit(phi):
    return np.array([np.cos(phi), np.sin(phi)])


def _canonical(p):
    """Put a traced line into one fixed direction (left to right on screen; top to bottom if it runs mostly
    vertically). The engine's spline fit and hinge search are not exactly symmetric under reversal (a few px
    of hinge shift on a tight nose, ~0.01-0.02 in R), so without this the same tracing could give two answers
    depending on which end the user started from."""
    d = p[-1] - p[0]
    axis = 0 if abs(d[0]) >= abs(d[1]) else 1
    return p[::-1] if d[axis] < 0 else p


# pairing checks that also make sense for hand-drawn lines (lines on top of each other / touching / crossing).
# The others (gap changes too fast, too little side-by-side overlap) catch the auto-detector jumping to another
# boundary; on hand traces they fire on genuine Class 1C/3 noses, where the bed really is much thicker at the hinge.
_PAIR_CHECKS_FOR_HAND = ('traced twice', 'touch', 'cross')


def _limb_turn_deg(arc, s_hinge, s_end):
    # how far the tangent turns from the hinge to the end of this limb (largest dip reached)
    mask = (arc.s >= min(s_hinge, s_end)) & (arc.s <= max(s_hinge, s_end))
    return float(np.degrees(np.max(np.abs(geo._angdiff(arc.phi[mask], geo.phi_at(arc, s_hinge)))))) if mask.any() else 0.0


def _refused(reason, raw=None, swapped=False, t=None):
    return dict(verdict='refused', reasons=[reason], notes=[], engine_error=raw, swapped=swapped,
                overall=None, limbs={}, hinge=None, cut=None, isogons=[], missing=[], chart={},
                engine=pipeline.ENGINE_TAG, timings_ms=t or {})


def classify(outer, inner, angles=(20, 40, 60)):
    """outer, inner: (N, 2) points along the two traced boundaries, in image pixels.
    angles: dip angles (deg) whose isogons to draw. Returns the result dict (plan.md section 5)."""
    t_start = time.perf_counter()
    outer, inner = np.asarray(outer, float), np.asarray(inner, float)
    angles = sorted({round(float(a), 2) for a in angles if 0 <= float(a) < 90})
    for name, p in (('outer', outer), ('inner', inner)):
        if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or np.hypot(*np.diff(p, axis=0).T).sum() < 10:
            return _refused(f'The {name} line is too short. Trace it along the whole bed edge.')
    outer, inner = _canonical(outer), _canonical(inner)

    # 1. which fold the lines share, its hinges, and which line is really the outer one
    lines = [dict(id=0, pts=outer, strength=1.0), dict(id=1, pts=inner, strength=1.0)]
    ev = pairing.evaluate(lines[0], lines[1], lines)
    pair_problems = [m for m in ev['reasons'] if any(k in m for k in _PAIR_CHECKS_FOR_HAND)]
    if 'hinge_outer' not in ev:
        return _refused("The two lines don't share a fold: each line must pass the hinge of the same fold.")
    swapped = ev['outer_id'] == 1
    if swapped:
        outer, inner = inner, outer

    # 2. cut to one fold, same direction, thin, frozen engine (identical to the auto pipeline)
    r, err, cut, dips = pipeline.run_engine(outer, inner, ev['hinge_outer'], ev['hinge_inner'])
    t = dict(engine=round(1000 * (time.perf_counter() - t_start)))
    if r is None:
        return _refused(plain_reason(err), raw=err, swapped=swapped, t=t)

    oa, ia, s_ho, s_hi = r['outer_arc'], r['inner_arc'], r['s_hinge_outer'], r['s_hinge_inner']
    sep, axial = r['typical_separation'], r['axial_trace']
    ref_o, ref_i = geo.phi_at(oa, s_ho), geo.phi_at(ia, s_hi)          # tangent directions at H and G
    bounds = {'left': (_clamp_limb_bound(oa, s_ho, oa.s[0]), _clamp_limb_bound(ia, s_hi, ia.s[0])),
              'right': (_clamp_limb_bound(oa, s_ho, oa.s[-1]), _clamp_limb_bound(ia, s_hi, ia.s[-1]))}
    # the engine's "left" limb is the start of the outer line, which depends on the tracing direction.
    # Name limbs by where they end on screen instead.
    flip = oa.xy[0][0] > oa.xy[-1][0]
    show = {'left': 'right', 'right': 'left'} if flip else {'left': 'left', 'right': 'right'}

    limbs, isogons, missing, chart = {}, [], [], {}
    for k, eng in enumerate(('left', 'right')):
        name = show[eng]
        fit, cl = r['fits'].get(eng), r['classes'].get(eng)
        turn = min(_limb_turn_deg(oa, s_ho, bounds[eng][0]), _limb_turn_deg(ia, s_hi, bounds[eng][1]))
        limbs[name] = dict(
            fitted=fit is not None,
            fold_class=cl.fold_class if cl else None,
            R=_r(fit.R, 3) if fit else None, sigma_R=_r(fit.sigma_R, 3) if fit else None,
            t0_px=_r(fit.t0) if fit else None,
            alpha_span_deg=_r(cl.alpha_span) if cl else None, n_isogons=cl.n_samples if cl else len(r['isogons'][eng]),
            # half-width of the band around R = 0 (Class 2) and R = 1 (Class 1B) used by geometry.classify
            class_window=_r(max(config.R_AMBIGUITY_SIGMA * fit.sigma_R, config.R_MIN_AMBIGUITY_WINDOW)
                            if fit and np.isfinite(fit.sigma_R) else config.R_MIN_AMBIGUITY_WINDOW, 3),
            max_dip_deg=_r(dips[k]),
            warnings=list(cl.warnings) if cl else ['fewer than 3 isogon pairs on this limb, so it could not be fitted'])
        if fit:
            chart[name] = dict(
                points=[[_r(np.degrees(p.alpha), 2), _r(p.t / fit.t0, 4)] for p in r['isogons'][eng]],
                # the full table the fit used: alpha (deg), t_alpha (px), T_alpha (px)
                rows=[[_r(np.degrees(p.alpha), 2), _r(p.t, 2), _r(p.T, 2)] for p in r['isogons'][eng]],
                fit=dict(R=_r(fit.R, 4), t0_px=_r(fit.t0, 2)))

        # display isogons at the user's angles, same arcs / hinges / bounds / axial trace as the fit
        try:
            pairs = geo.isogon_pairs(oa, ia, s_ho, bounds[eng][0], s_hi, bounds[eng][1],
                                     ref_o, ref_i, axial,
                                     np.radians(angles), limb=eng, separation=sep)
        except geo.GeometryError as e:
            pairs = []
            missing += [dict(limb=name, alpha=a, why=plain_reason(str(e))) for a in angles]
            continue
        got = {round(float(np.degrees(p.alpha)), 2): p for p in pairs}
        for a in angles:
            p = got.get(a)
            if p is None:
                why = (f'{MAX_MATCH_DEG:.0f}° or steeper, where tangent matching is unreliable' if a >= MAX_MATCH_DEG - 0.5 else
                       f'this limb only turns {turn:.0f}°' if a > turn else
                       'no plausible match (isogon far longer than the bed is thick)')
                missing.append(dict(limb=name, alpha=a, why=why))
                continue
            # the exact tangents the engine matched (same lookup as inside isogon_pairs)
            tp = _unit(geo.phi_at(oa, geo._match_alpha(oa, s_ho, bounds[eng][0], ref_o, p.alpha)))
            tq = _unit(geo.phi_at(ia, geo._match_alpha(ia, s_hi, bounds[eng][1], ref_i, p.alpha)))
            foot = p.p + np.dot(p.q - p.p, tp) * tp      # q dropped onto the outer tangent: t_alpha = |q - foot|
            isogons.append(dict(limb=name, alpha=a, p=_pt(p.p), q=_pt(p.q), foot=_pt(foot),
                                tan_p=_pt4(tp), tan_q=_pt4(tq),
                                t_px=_r(p.t), t_prime=_r(p.t / fit.t0, 3) if fit else None,
                                T_px=_r(p.T), T_prime=_r(p.T / fit.t0, 3) if fit else None,
                                in_fit_range=FIT_RANGE[0] <= a <= FIT_RANGE[1]))

    # verdict
    fitted = {n: l for n, l in limbs.items() if l['fitted']}
    if not fitted:
        return dict(_refused('Neither limb has enough matching tangent pairs. Extend both lines further down the limbs.',
                             swapped=swapped, t=t),
                    limbs=limbs, cut=dict(outer=[_pt(p) for p in cut[0]], inner=[_pt(p) for p in cut[1]]))
    # reasons lower confidence; notes are information only
    reasons, notes = [], []
    if swapped:
        notes.append('Swapped: the line traced first is the inner edge of the bed, so it was used as the inner line.')
    classes = {l['fold_class'] for l in fitted.values()}
    if len(fitted) == 1:
        reasons.append(f'Only the {next(iter(fitted))} limb could be measured.')
    elif len(classes) > 1:
        reasons.append('The limbs disagree: ' + ', '.join(f"{n} says {l['fold_class'] or 'ambiguous'}" for n, l in fitted.items()) + '.')
    if None in classes:
        reasons.append('R is too close to a class boundary, given its uncertainty, to commit to a class.')
    thin = [l['t0_px'] for l in fitted.values() if l['t0_px'] < config.MIN_LAYER_THICKNESS_PX]
    if thin:
        reasons.append(f'The bed is only {min(thin):.0f} px thick (reliable from {config.MIN_LAYER_THICKNESS_PX:.0f} px). '
                       'Use a higher-resolution photo or zoom in on a thicker bed.')
    reasons += [f'The two lines: {m}.' for m in pair_problems]
    dip = max(l['max_dip_deg'] or 0 for l in limbs.values())
    if dip > VALIDATED_DIP_DEG:
        # not a confidence issue: the fit only uses 20-70 deg, and on hand traces dipping 86-88 deg the engine
        # matched the hand-measured R (Fold 11, Fold 3)
        notes.append(f'The limbs dip up to {dip:.0f}°. The fit uses only {FIT_RANGE[0]:.0f}–{FIT_RANGE[1]:.0f}°; '
                     f'synthetic tests covered dips up to {VALIDATED_DIP_DEG:.0f}°.')
    for n, l in fitted.items():
        reasons += [f'{n} limb: {w}' for w in l['warnings']]
    reasons += list(r['warnings'])

    Rs = [l['R'] for l in fitted.values()]
    sig = [l['sigma_R'] for l in fitted.values() if l['sigma_R'] is not None]
    overall = dict(fold_class=next(iter(classes)) if len(classes) == 1 else None,
                   R=_r(np.mean(Rs), 3), sigma_R=_r(np.sqrt(np.sum(np.square(sig))) / len(sig), 3) if sig else None)
    t['total'] = round(1000 * (time.perf_counter() - t_start))
    return dict(
        verdict='low_confidence' if reasons else 'confident',
        reasons=reasons, notes=notes, engine_error=None, swapped=swapped,
        overall=overall, limbs=limbs,
        hinge=dict(H=_pt(r['H']), G=_pt(r['G']), hg_px=_r(r['hg_dist']),
                   tan_H=_pt4(_unit(ref_o)), tan_G=_pt4(_unit(ref_i)),
                   axial_trace=dict(point=_pt(axial.point), dir=[round(float(v), 4) for v in axial.direction])),
        cut=dict(outer=[_pt(p) for p in cut[0]], inner=[_pt(p) for p in cut[1]]),
        isogons=isogons, missing=missing, chart=chart,
        fit_range_deg=list(FIT_RANGE), separation_px=_r(sep),
        engine=pipeline.ENGINE_TAG, timings_ms=t)


# ---------------------------------------------------------------- CLI: check an example and draw the result
def draw_check(photo_path, res, outer, inner, out_path):
    import cv2
    img = cv2.imread(str(photo_path))
    s = max(1, round(min(img.shape[:2]) / 600))
    dark = (20, 20, 20)

    def line(pts, col, w):
        p = np.round(np.asarray(pts)).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [p], False, dark, w + 2 * s, cv2.LINE_AA)
        cv2.polylines(img, [p], False, col, w, cv2.LINE_AA)

    line(outer, (60, 120, 160), s)            # full traces, dim
    line(inner, (160, 140, 60), s)
    if res['cut']:
        line(res['cut']['outer'], (32, 176, 255), 2 * s)      # amber
        line(res['cut']['inner'], (240, 230, 46), 2 * s)      # cyan
    for iso in res['isogons']:
        f = (iso['alpha'] - 20) / 50
        col = tuple(int(c) for c in np.array([230, 60, 150]) * (1 - f) + np.array([40, 140, 255]) * f)   # violet->orange
        line([iso['p'], iso['q']], col, 2 * s)
        for pt, d in ((iso['p'], iso['tan_p']), (iso['q'], iso['tan_q'])):
            d = 25 * s * np.array(d)
            line([np.array(pt) - d, np.array(pt) + d], col, s)
        mid = tuple(int(v) for v in (np.array(iso['p']) + np.array(iso['q'])) / 2)
        for w, c in ((3 * s, dark), (s, (255, 255, 255))):
            cv2.putText(img, f"{iso['alpha']:g}", mid, cv2.FONT_HERSHEY_SIMPLEX, 0.6 * s, c, w, cv2.LINE_AA)
    if res['hinge']:
        h = res['hinge']
        P, D = np.array(h['axial_trace']['point']), np.array(h['axial_trace']['dir'])
        L = 1.5 * np.hypot(*(np.array(res['cut']['outer'][0]) - res['cut']['outer'][-1]))
        line([P - L * D, P + L * D], (230, 230, 230), s)
        for key in ('H', 'G'):
            c = tuple(int(v) for v in h[key])
            cv2.circle(img, c, 5 * s, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.putText(img, key, (c[0] + 7 * s, c[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.8 * s, (255, 255, 255), 2 * s, cv2.LINE_AA)
    allp = np.vstack([outer, inner])
    x0, y0 = np.maximum(allp.min(0) - 200, 0).astype(int)
    x1, y1 = np.minimum(allp.max(0) + 200, img.shape[1::-1]).astype(int)
    crop = img[y0:y1, x0:x1]
    k = 1400 / max(crop.shape[:2])
    cv2.imwrite(str(out_path), cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])


def main():
    import examples
    ap = argparse.ArgumentParser()
    ap.add_argument('example', help='example name, see examples.py (or "all")')
    ap.add_argument('--angles', default='30,45,60')
    ap.add_argument('--out', default=None, help='check image path (default data/manual_check/<name>.jpg)')
    a = ap.parse_args()
    angles = [float(v) for v in a.angles.split(',')]
    names = [e['name'] for e in examples.catalog()] if a.example == 'all' else [a.example]
    for name in names:
        ex = examples.load(name)
        res = classify(ex['outer'], ex['inner'], angles)
        hand = ex['hand']
        print(f"{name:20} {res['verdict']:15} overall {res['overall']}  "
              + ' | '.join(f"{n} {l['fold_class']} R={l['R']}±{l['sigma_R']} t0={l['t0_px']} dip={l['max_dip_deg']}"
                           for n, l in res['limbs'].items())
              + (f"   [hand {hand['label']}: R={hand['R']}]" if hand else '') + f"  {res['timings_ms']}")
        if res['engine_error']:
            print('   refused:', res['reasons'][0], '|', res['engine_error'])
        if len(names) == 1:
            print(json.dumps({k: res[k] for k in ('reasons', 'notes', 'swapped', 'missing')}, indent=1))
            for iso in res['isogons']:
                print(f"   {iso['limb']:5} {iso['alpha']:5g} deg  t={iso['t_px']:7.1f}px  t'={iso['t_prime']}"
                      + ('' if iso['in_fit_range'] else '  (display only)'))
        out = Path(a.out) if a.out and len(names) == 1 else pipeline.DATA / 'manual_check' / f'{name}.jpg'
        out.parent.mkdir(parents=True, exist_ok=True)
        draw_check(ex['photo_path'], res, ex['outer'], ex['inner'], out)
        print('   wrote', out, file=sys.stderr)


if __name__ == '__main__':
    main()
