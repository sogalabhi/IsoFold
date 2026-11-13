"""photo -> result dict (the JSON contract in HANDOFF.md section 7.2). No web code in here, so the CLI,
the API and the tests all call analyze().

Usage:  python -m pipeline photo.png [out_dir]      # prints the result JSON, writes result.json + overlay.png"""
import json
import sys
import time
import uuid
from pathlib import Path

import cv2
import numpy as np
from foldclass.debug import debug_pipeline

import detect as D
import pairing
import prepare
import render

ENGINE_TAG = 'core-v1.0-frozen'
MAX_SIDE = 2200                     # detection runs on a resized copy above this (it is slow on CPU)
DETECT = dict(D.DEFAULT, max_curves=30, min_len=0.25, n_best=8)
SMOOTH_FRAC = 0.015                 # re-smooth the chosen pair to 1.5% of the bed's thickness (not of the image)
DATA = Path(__file__).parent / 'data'


def detect_lines(bgr, P):
    """All detected lines in original-image pixels; complete fold lines first (ranked), then the rest."""
    H, W = bgr.shape[:2]
    scale = min(1.0, MAX_SIDE / max(H, W))
    small = bgr if scale == 1 else cv2.resize(bgr, (round(W * scale), round(H * scale)), interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    # empty annotation mask: the yellow-line eraser is only for the annotated collage
    _, _, _, _, curves = D.detect(small, np.zeros((h, w), bool), P)
    best = D.pick_best(curves, h, w, P, D.rock_mask(small, P))
    rest = [d for d in curves if not any(d is b for b in best)]
    tol = P['smooth_tol'] * min(h, w) / scale
    lines = []
    for d in best + rest:
        complete = any(d is b for b in best)
        raw = d['pts'] / scale          # kept unsmoothed: the chosen pair is re-smoothed to the bed's thickness
        lines.append(dict(id=len(lines), raw=raw, pts=D.spline_smooth(raw, tol) if complete else raw,
                          complete=complete, bend_deg=d.get('span'), strength=float(d['strength']),
                          inside_rock=None if 'outside' not in d else 1 - d['outside']))
    return lines, scale


def run_engine(outer, inner, hinge_o, hinge_i):
    """Cut to one fold, same direction, thin, engine. Returns (engine result or None, error, cut pair, dips)."""
    outer_c, dips_o = prepare.cut_at_inflections(outer, hinge_o)
    inner_c, dips_i = prepare.cut_at_inflections(inner, hinge_i)
    inner_c, flipped = prepare.same_direction(outer_c, inner_c)
    if flipped:
        dips_i = dips_i[::-1]
    dips = (max(dips_o[0], dips_i[0]), max(dips_o[1], dips_i[1]))     # (left, right) in the engine's order
    o60, i60 = prepare.thin(outer_c), prepare.thin(inner_c)
    try:
        return debug_pipeline(o60, i60), None, (outer_c, inner_c), dips
    except Exception as e:                                            # the engine refuses with a plain reason
        return None, f'{type(e).__name__}: {e}', (outer_c, inner_c), dips


def _limb(r, limb, dip):
    out = dict(max_dip_deg=round(dip, 1))
    if r is None or limb not in r['fits']:
        return dict(out, **{'class': None, 'R': None, 'sigma_R': None, 't0_px': None, 'alpha_span_deg': None,
                            'warnings': [] if r is None else ['fewer than 3 isogon pairs on this limb; the engine could not fit it']})
    fit, cl = r['fits'][limb], r['classes'][limb]
    return dict(out, **{'class': cl.fold_class, 'R': round(float(fit.R), 4), 'sigma_R': round(float(fit.sigma_R), 4),
                        't0_px': round(float(fit.t0), 2), 'alpha_span_deg': round(float(cl.alpha_span), 1),
                        'n_isogons': int(cl.n_samples), 'warnings': list(cl.warnings)})


def _candidate(c):
    return dict(ids=list(c['ids']), median_gap_px=c['median_gap_px'], overlap=c['overlap'], valid=c['valid'],
                reasons=c['reasons'], layer_package=c.get('layer_package'), score=c.get('score'))


def analyze(image_path, params=None, out_dir=None):
    params = params or {}
    job_id = params.get('job_id') or uuid.uuid4().hex
    out_dir = Path(out_dir or DATA / job_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    t = {}
    t0 = time.perf_counter()
    bgr = cv2.imread(str(image_path))
    if bgr is None:
        raise ValueError(f'could not read an image from {image_path}')
    H, W = bgr.shape[:2]
    lines, scale = detect_lines(bgr, dict(DETECT, **params.get('detect', {})))
    t['detect'] = round(1000 * (time.perf_counter() - t0))

    t0 = time.perf_counter()
    best, cands, notes = pairing.choose(lines)
    r, error, pair, limbs, dips = None, None, None, None, (0.0, 0.0)
    if best is not None:
        outer, inner = lines[best['outer_id']], lines[best['inner_id']]
        tol = SMOOTH_FRAC * best['median_gap_px']
        r, error, (outer_c, inner_c), dips = run_engine(D.spline_smooth(outer['raw'], tol), D.spline_smooth(inner['raw'], tol),
                                                        best['hinge_outer'], best['hinge_inner'])
        pair = dict(outer_id=best['outer_id'], inner_id=best['inner_id'], median_gap_px=best['median_gap_px'],
                    overlap=best['overlap'], layer_package=best['layer_package'], between_ids=best['between_ids'],
                    auto=True, outer_pts=np.round(outer_c, 1).tolist(), inner_pts=np.round(inner_c, 1).tolist())
        limbs = {limb: _limb(r, limb, dips[k]) for k, limb in enumerate(('left', 'right'))}
    t['engine'] = round(1000 * (time.perf_counter() - t0))

    result = dict(
        job_id=job_id,
        engine=ENGINE_TAG,
        image=dict(width=W, height=H, analysed_scale=round(scale, 4)),
        lines=[dict(id=d['id'], points=np.round(d['pts'], 1).tolist(), complete=d['complete'],
                    bend_deg=None if d['bend_deg'] is None else round(d['bend_deg']),
                    strength=round(d['strength'], 3),
                    inside_rock=None if d['inside_rock'] is None else round(d['inside_rock'], 3)) for d in lines],
        pair=pair,
        pair_candidates=[_candidate(c) for c in cands],
        limbs=limbs,
        isogons=[] if r is None else [[np.round(p.p, 1).tolist(), np.round(p.q, 1).tolist()]
                                      for pairs in r['isogons'].values() for p in pairs],
        hinges=None if r is None else dict(H=np.round(r['H'], 1).tolist(), G=np.round(r['G'], 1).tolist(),
                                           hg_dist_px=round(float(r['hg_dist']), 1)),
        notes=notes,
        engine_error=error,
        engine_warnings=[] if r is None else list(r['warnings']),
        verdict=None,                # build step 3
        files=dict(overlay=f'/api/files/{job_id}/overlay.png'),
        timings_ms=t,
    )
    render.overlay(bgr, result, out_dir / 'overlay.png')
    (out_dir / 'result.json').write_text(json.dumps(result))
    return result


def summary(result):
    # the result without the long point lists, for printing
    s = dict(result, lines=f"{len(result['lines'])} lines, {sum(d['complete'] for d in result['lines'])} complete")
    if result['pair']:
        s['pair'] = {k: v for k, v in result['pair'].items() if not k.endswith('_pts')}
    s['isogons'] = f"{len(result['isogons'])} isogon lines"
    return s


if __name__ == '__main__':
    out = sys.argv[2] if len(sys.argv) > 2 else None
    res = analyze(sys.argv[1], out_dir=out)
    print(json.dumps(summary(res), indent=2))
    print('wrote', Path(out or DATA / res['job_id']) / 'overlay.png', file=sys.stderr)
