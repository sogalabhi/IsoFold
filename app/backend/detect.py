"""Automatic bedding-boundary tracing guided by the layer orientation field (no AI model, no clicks).

Usage:
  python3 autotrace.py photo.png out.png                         # all detected lines (max 12)
  python3 autotrace.py photo.png out.png '{"best":true,"max_curves":30,"min_len":0.25}'   # best 3 complete fold lines
  python3 autotrace.py panel.png out.png '{"gt":"gt.npy"}'       # score against a hand-trace mask

Writes out.png (lines + faint yellow hand trace), out_auto_only.png, out_edges.png, out_curves.json.
Yellow hand-trace lines in the input are detected and painted over before detection (only matters for
annotated images); they are used only for scoring. See HANDOFF.md for how each step works."""
import sys, json, cv2, numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize, remove_small_objects


def yellow_mask(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (18, 90, 140), (38, 255, 255)) > 0
    m = remove_small_objects(m, max_size=150)
    return m


def bilinear(a, x, y):
    return ndi.map_coordinates(a, [[y], [x]], order=1, mode='nearest')[0]


def detect(bgr, ann_mask, P):
    H, W = bgr.shape[:2]
    # 1. remove annotation so detector sees only the rock
    inp_mask = cv2.dilate(ann_mask.astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
    clean = cv2.inpaint(bgr, inp_mask, 5, cv2.INPAINT_TELEA)
    lab = cv2.cvtColor(clean, cv2.COLOR_BGR2LAB)
    L = cv2.createCLAHE(2.0, (8, 8)).apply(lab[..., 0]).astype(np.float32) / 255.0

    # 2. structure tensor -> dominant layering direction everywhere
    s_g, s_i = P['sigma_grad'], P['sigma_int'] * min(H, W)
    gx = ndi.gaussian_filter(L, s_g, order=(0, 1))
    gy = ndi.gaussian_filter(L, s_g, order=(1, 0))
    Jxx = ndi.gaussian_filter(gx * gx, s_i)
    Jyy = ndi.gaussian_filter(gy * gy, s_i)
    Jxy = ndi.gaussian_filter(gx * gy, s_i)
    phi = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)          # normal to layers
    nx, ny = np.cos(phi), np.sin(phi)
    tr = Jxx + Jyy + 1e-9
    coh = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2) / tr  # 0..1, how "layered"

    # 3. keep only edges that run PARALLEL to layering (kills cross-cutting cracks)
    chans = [L, lab[..., 1].astype(np.float32) / 255.0 * P['color_w'], lab[..., 2].astype(np.float32) / 255.0 * P['color_w']]
    E = np.zeros_like(L)
    for se in P['sigma_edges']:
        acc = np.zeros_like(L)
        for C in chans:
            gx2 = ndi.gaussian_filter(C, se, order=(0, 1)) * se
            gy2 = ndi.gaussian_filter(C, se, order=(1, 0)) * se
            acc += (gx2 * nx + gy2 * ny) ** 2
        acc = np.sqrt(acc)
        E = np.maximum(E, acc / (np.percentile(acc, 99.5) + 1e-9))
    E = E * coh
    # 3b. mask field tools (pens, hammer handles): strongly saturated colours rock rarely has
    hsv = cv2.cvtColor(clean, cv2.COLOR_BGR2HSV)
    tool = (hsv[..., 1] > P['tool_sat']) & (hsv[..., 2] > 60)
    tool = remove_small_objects(tool, max_size=P['tool_min_px'])
    tool = cv2.dilate(tool.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    E[tool] = 0
    E /= np.percentile(E, 99.5) + 1e-9

    # non-max suppression across the layer -> thin ridge candidates
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    Ef = ndi.map_coordinates(E, [yy + ny, xx + nx], order=1, mode='nearest')
    Eb = ndi.map_coordinates(E, [yy - ny, xx - nx], order=1, mode='nearest')
    ridge = (E >= Ef) & (E >= Eb) & (E > P['seed_thr']) & (coh > P['coh_min'])
    border = int(0.03 * min(H, W))
    ridge[:border] = ridge[-border:] = False
    ridge[:, :border] = ridge[:, -border:] = False

    # 4. trace each seed along the layer direction, snapping to the edge
    def trace(x, y, sgn):
        pts = []
        tx0, ty0 = None, None
        miss = 0
        for _ in range(4000):
            ph = bilinear(phi, x, y)
            nxx, nyy = np.cos(ph), np.sin(ph)
            tx, ty = -nyy, nxx
            if tx0 is None:
                tx, ty = tx * sgn, ty * sgn
            elif tx * tx0 + ty * ty0 < 0:
                tx, ty = -tx, -ty
            if tx0 is not None and tx * tx0 + ty * ty0 < np.cos(np.radians(P['max_turn'])):
                break
            x, y = x + P['step'] * tx, y + P['step'] * ty
            # snap across the layer to the local edge maximum
            offs = np.linspace(-P['snap'], P['snap'], 2 * P['snap'] * 2 + 1)
            vals = ndi.map_coordinates(E, [y + offs * nyy, x + offs * nxx], order=1, mode='nearest')
            k = int(np.argmax(vals))
            if vals[k] > P['keep_thr']:
                x, y = x + offs[k] * nxx * 0.6, y + offs[k] * nyy * 0.6
                miss = 0
            else:
                miss += 1
                if miss > P['max_gap']:
                    pts = pts[:-P['max_gap']] if len(pts) > P['max_gap'] else []
                    break
            if not (2 <= x < W - 2 and 2 <= y < H - 2):
                break
            if bilinear(coh, x, y) < P['coh_min'] * 0.7:
                break
            pts.append((x, y))
            tx0, ty0 = tx, ty
        return pts

    ys, xs = np.nonzero(ridge)
    order = np.argsort(-E[ys, xs])
    used = np.zeros((H, W), bool)
    curves = []
    for i in order[: P['max_seeds']]:
        x, y = float(xs[i]), float(ys[i])
        if used[int(y), int(x)]:
            continue
        a = trace(x, y, +1)
        b = trace(x, y, -1)
        c = np.array(b[::-1] + [(x, y)] + a)
        if len(c) < 3:
            continue
        seg = np.diff(c, axis=0)
        length = np.hypot(seg[:, 0], seg[:, 1]).sum()
        ci = np.clip(c.round().astype(int), 0, [W - 1, H - 1])
        # mark corridor as used so we don't re-trace the same boundary
        tmp = np.zeros((H, W), np.uint8)
        cv2.polylines(tmp, [ci.reshape(-1, 1, 2)], False, 1, P['dedup_px'] * 2 + 1)
        used |= tmp > 0
        if length < 0.4 * P['min_len'] * min(H, W):
            continue
        strength = float(np.mean(E[ci[:, 1], ci[:, 0]]))
        curves.append(dict(pts=c, length=float(length), strength=strength))

    curves = merge_curves(curves, P)
    for d in curves:
        d['pts'] = smooth(d['pts'], P['smooth'])
    # 5. remove near-duplicates, longest+strongest first
    curves = [d for d in curves if d['length'] >= P['min_len'] * min(H, W)]
    curves.sort(key=lambda d: -d['length'] * d['strength'])
    kept, occ = [], np.zeros((H, W), bool)
    for d in curves:
        ci = np.clip(d['pts'].round().astype(int), 0, [W - 1, H - 1])
        overlap = occ[ci[:, 1], ci[:, 0]].mean()
        if overlap > 0.5:
            continue
        kept.append(d)
        tmp = np.zeros((H, W), np.uint8)
        cv2.polylines(tmp, [ci.reshape(-1, 1, 2)], False, 1, 2 * P['dedup_px'] + 1)
        occ |= tmp > 0
        if len(kept) >= P['max_curves']:
            break
    return clean, E, coh, phi, kept


def smooth(c, s):
    if len(c) < 7:
        return c
    return np.stack([ndi.gaussian_filter1d(c[:, 0], s, mode='nearest'),
                     ndi.gaussian_filter1d(c[:, 1], s, mode='nearest')], 1)


def _end(c, head):
    k = min(8, len(c) - 1)
    if head:
        p, q = c[0], c[k]
    else:
        p, q = c[-1], c[-1 - k]
    t = p - q
    return p, t / (np.linalg.norm(t) + 1e-9)


def merge_curves(curves, P):
    # join pieces that broke at a hinge or a gap: endpoints close and heading the same way
    changed = True
    while changed:
        changed = False
        best = None
        for i in range(len(curves)):
            for j in range(len(curves)):
                if i == j:
                    continue
                for hi in (False, True):
                    for hj in (True, False):
                        pi, ti = _end(curves[i]['pts'], hi)
                        pj, tj = _end(curves[j]['pts'], hj)
                        gap = np.linalg.norm(pj - pi)
                        if gap > P['join_px']:
                            continue
                        if ti @ (-tj) < np.cos(np.radians(35)):
                            continue
                        if gap > 1 and ti @ ((pj - pi) / gap) < np.cos(np.radians(45)):
                            continue
                        if best is None or gap < best[0]:
                            best = (gap, i, j, hi, hj)
        if best:
            _, i, j, hi, hj = best
            a = curves[i]['pts'][::-1] if hi else curves[i]['pts']
            b = curves[j]['pts'] if hj else curves[j]['pts'][::-1]
            pts = np.vstack([a, b])
            seg = np.diff(pts, axis=0)
            new = dict(pts=pts, length=float(np.hypot(seg[:, 0], seg[:, 1]).sum()),
                       strength=(curves[i]['strength'] * curves[i]['length'] + curves[j]['strength'] * curves[j]['length'])
                       / (curves[i]['length'] + curves[j]['length']))
            curves = [c for k, c in enumerate(curves) if k not in (i, j)] + [new]
            changed = True
    return curves


def fold_metrics(c, H, W):
    # how much of a fold does this line cover?
    cs = smooth(c, 6)
    d = np.diff(cs, axis=0)
    ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    span = float(np.degrees(ang.max() - ang.min()))         # total turn: both limbs + hinge
    # hinge = where the line is turning fastest; both limbs must be long enough
    k = np.abs(np.gradient(ndi.gaussian_filter1d(ang, 10)))
    h = int(np.argmax(k))
    seg = np.hypot(d[:, 0], d[:, 1])
    left, right = float(seg[:h].sum()), float(seg[h:].sum())
    wobble = float(seg.sum() / (np.hypot(*np.diff(smooth(c, 15), axis=0).T).sum() + 1e-9))
    return dict(span=span, limb_min=min(left, right) / min(H, W), wobble=wobble, hinge=cs[h].tolist())


def spline_smooth(c, tol_px):
    # resample evenly, then fit a smoothing spline that may stray ~tol_px from the trace
    from scipy.interpolate import splprep, splev
    seg = np.hypot(*np.diff(c, axis=0).T)
    t = np.concatenate([[0], np.cumsum(seg)])
    n = max(20, int(t[-1] / 4))
    u = np.linspace(0, t[-1], n)
    x, y = np.interp(u, t, c[:, 0]), np.interp(u, t, c[:, 1])
    tck, _ = splprep([x, y], u=u / t[-1], s=n * tol_px ** 2, k=3)
    xs, ys = splev(np.linspace(0, 1, n * 2), tck)
    return np.stack([xs, ys], 1)


def rock_mask(bgr, P):
    # rock is grey; grass and soil are coloured. Keep the biggest grey region, then shrink it
    # so lines that hug the rock's outer edge also fall outside.
    H, W = bgr.shape[:2]
    S = cv2.cvtColor(cv2.GaussianBlur(bgr, (0, 0), 6), cv2.COLOR_BGR2HSV)[..., 1]
    m = (S < P['rock_sat']).astype(np.uint8)
    k = int(0.03 * min(H, W)) | 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    lab, n = ndi.label(m)
    if n == 0:
        return np.ones((H, W), bool)
    m = (lab == np.argmax(np.bincount(lab.ravel())[1:]) + 1).astype(np.uint8)
    m = ndi.binary_fill_holes(m).astype(np.uint8)
    e = int(P['rock_erode'] * min(H, W)) | 1
    return cv2.erode(m, np.ones((e, e), np.uint8)) > 0


def pick_best(curves, H, W, P, rock=None):
    good = []
    for d in curves:
        if rock is not None:
            ci = np.clip(d['pts'].round().astype(int), 0, [W - 1, H - 1])
            d['outside'] = float(1 - rock[ci[:, 1], ci[:, 0]].mean())
            if d['outside'] > P['max_outside']:
                continue      # runs along the rock's edge or into grass/soil

        m = fold_metrics(d['pts'], H, W)
        d.update(m)
        if m['span'] < P['min_span'] or m['limb_min'] < P['min_limb']:
            continue          # incomplete: only one limb, or barely bends
        if m['wobble'] > P['max_wobble']:
            continue          # too jagged to be a clean bedding boundary
        d['score'] = d['strength'] * d['length'] * min(m['span'], 180) / 180 / m['wobble'] ** 4
        good.append(d)
    good.sort(key=lambda d: -d['score'])
    return good[:P['n_best']]


def score(ann_mask, curves, shape, tol=5):
    H, W = shape
    gt = skeletonize(ann_mask)
    lab, n = ndi.label(cv2.dilate(gt.astype(np.uint8), np.ones((3, 3))) > 0)
    out = []
    det = np.ones((H, W), np.uint8)
    for d in curves:
        cv2.polylines(det, [d['pts'].round().astype(np.int32).reshape(-1, 1, 2)], False, 0, 1)
    dist = cv2.distanceTransform(det, cv2.DIST_L2, 5)
    for k in range(1, n + 1):
        comp = gt & (lab == k)
        if comp.sum() < 60:
            continue
        gy, gx = np.nonzero(comp)
        dd = dist[gy, gx]
        # best single curve: does ONE detected curve follow the whole bed?
        best = 0.0
        for d in curves:
            m = np.ones((H, W), np.uint8)
            cv2.polylines(m, [d['pts'].round().astype(np.int32).reshape(-1, 1, 2)], False, 0, 1)
            dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
            best = max(best, float((dt[gy, gx] <= tol).mean()))
        out.append(dict(gt_px=int(comp.sum()), within_tol=float((dd <= tol).mean()),
                        median_px=float(np.median(dd)), best_single_curve=best))
    return out


COLORS = [(255, 255, 0), (255, 0, 255), (0, 255, 0), (0, 128, 255), (255, 128, 0),
          (128, 0, 255), (0, 255, 255), (255, 0, 128), (128, 255, 0), (0, 0, 255),
          (200, 200, 200), (255, 200, 120)]


def draw(clean, curves, ann_mask=None):
    o = clean.copy()
    if ann_mask is not None:  # faint yellow = hand trace, for comparison only
        ov = o.copy(); ov[ann_mask] = (0, 220, 255)
        o = cv2.addWeighted(ov, 0.35, o, 0.65, 0)
    for i, d in enumerate(curves):
        c = d['pts'].round().astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(o, [c], False, (0, 0, 0), 6, cv2.LINE_AA)
        cv2.polylines(o, [c], False, COLORS[i % len(COLORS)], 3, cv2.LINE_AA)
    return o


DEFAULT = dict(smooth_tol=0.006, rock_sat=45, rock_erode=0.03, max_outside=0.05, min_span=100, min_limb=0.15, max_wobble=1.12, n_best=3, best=False, tool_sat=150, tool_min_px=200, sigma_grad=1.5, sigma_int=0.035, sigma_edges=(2.0, 3.5), color_w=1.5, join_px=25, smooth=3, seed_thr=0.35, keep_thr=0.12,
               coh_min=0.25, step=1.5, snap=3, max_turn=25, max_gap=8, dedup_px=4,
               min_len=0.35, max_seeds=3000, max_curves=12)

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    P = dict(DEFAULT)
    if len(sys.argv) > 3:
        P.update(json.loads(sys.argv[3]))
    bgr = cv2.imread(src)
    gt_path = P.pop('gt', None)
    if gt_path:
        ann = np.load(gt_path) > 0
        clean, E, coh, phi, curves = detect(bgr, np.zeros_like(ann), P)
    else:
        ann = yellow_mask(bgr)
        clean, E, coh, phi, curves = detect(bgr, ann, P)
    if P['best']:
        allc = curves
        curves = pick_best(curves, *bgr.shape[:2], P, rock_mask(bgr, P))
        tol = P['smooth_tol'] * min(bgr.shape[:2])
        for d in curves:
            d['pts'] = spline_smooth(d['pts'], tol)
        for i, d in enumerate(allc):
            print('cand', i, 'out=%.2f' % d.get('outside', -1), 'len=%.0f span=%.0f limb=%.2f wobble=%.3f str=%.2f' % (d['length'], d.get('span', -1), d.get('limb_min', -1), d.get('wobble', -1), d['strength']), 'KEEP' if any(d is c for c in curves) else '')
    json.dump([dict(color=list(COLORS[i % len(COLORS)]), pts=d['pts'].tolist()) for i, d in enumerate(curves)],
              open(dst.replace('.png', '_curves.json'), 'w'))
    cv2.imwrite(dst, draw(clean, curves, ann))
    cv2.imwrite(dst.replace('.png', '_edges.png'), np.clip(E * 255, 0, 255).astype(np.uint8))
    cv2.imwrite(dst.replace('.png', '_auto_only.png'), draw(clean, curves, None))
    s = score(ann, curves, bgr.shape[:2])
    print(json.dumps(dict(n_curves=len(curves), traces=s), indent=None))
