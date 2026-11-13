"""Overlay drawing: every line thin and grey, the chosen pair thick (outer solid, inner dashed), isogons, H and G."""
import cv2
import numpy as np

GREY, OUTER, INNER, ISOGON, DARK = (170, 170, 170), (0, 140, 255), (255, 200, 0), (80, 230, 80), (0, 0, 0)


def _poly(img, pts, color, w):
    cv2.polylines(img, [np.round(pts).astype(np.int32).reshape(-1, 1, 2)], False, color, w, cv2.LINE_AA)


def _dashed(img, pts, color, w, dash):
    # walk along the line and draw every other dash-length piece
    seg = np.hypot(*np.diff(pts, axis=0).T)
    t = np.r_[0, np.cumsum(seg)]
    for a in np.arange(0, t[-1], 2 * dash):
        m = (t >= a) & (t <= a + dash)
        if m.sum() >= 2:
            _poly(img, pts[m], color, w)


def overlay(bgr, result, path):
    o = bgr.copy()
    s = max(1, round(min(bgr.shape[:2]) / 500))          # stroke width grows with image size
    for d in result['lines']:
        _poly(o, np.array(d['points']), GREY, s)
    pair = result.get('pair')
    if pair and pair.get('outer_pts') is not None:
        outer, inner = np.array(pair['outer_pts']), np.array(pair['inner_pts'])
        _poly(o, outer, DARK, 3 * s + 2)
        _poly(o, outer, OUTER, 3 * s)
        _poly(o, inner, DARK, 3 * s + 2)
        _dashed(o, inner, INNER, 3 * s, 6 * s)
    for p, q in result.get('isogons', []):
        _poly(o, np.array([p, q]), DARK, s + 2)
        _poly(o, np.array([p, q]), ISOGON, s)
    hinges = result.get('hinges')
    if hinges:
        for key, col in (('H', OUTER), ('G', INNER)):
            c = tuple(int(round(v)) for v in hinges[key])
            cv2.circle(o, c, 4 * s, DARK, -1, cv2.LINE_AA)
            cv2.circle(o, c, 3 * s, col, -1, cv2.LINE_AA)
            cv2.putText(o, key, (c[0] + 5 * s, c[1] - 5 * s), cv2.FONT_HERSHEY_SIMPLEX, 0.5 * s, DARK, 3 * s, cv2.LINE_AA)
            cv2.putText(o, key, (c[0] + 5 * s, c[1] - 5 * s), cv2.FONT_HERSHEY_SIMPLEX, 0.5 * s, col, s, cv2.LINE_AA)
    cv2.imwrite(str(path), o)
