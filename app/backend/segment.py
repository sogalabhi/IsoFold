"""Bed detection by region segmentation (build plan stage 1: a pretrained SAM, no training).
Instead of tracing two thin boundary lines, SAM outlines a whole bed; the two long sides of that outline
are the bed's boundaries. They then go through the same pairing checks and engine as traced lines.

Needs torch + transformers (CPU is fine). The model is downloaded once to ~/.cache/huggingface."""
from collections import deque

import cv2
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

MODEL = 'facebook/sam-vit-base'
_cache = {}


def _load():
    if not _cache:
        import torch
        from transformers import SamModel, SamProcessor, pipeline
        torch.set_num_threads(max(1, (__import__('os').cpu_count() or 2) - 2))
        _cache['proc'] = SamProcessor.from_pretrained(MODEL)
        _cache['model'] = SamModel.from_pretrained(MODEL).eval()
        _cache['auto'] = pipeline('mask-generation', model=_cache['model'], image_processor=_cache['proc'].image_processor, device=-1)
    return _cache


def masks_from_points(rgb, points):
    """One mask per clicked point (x, y): SAM's best of its three guesses."""
    import torch
    c = _load()
    inputs = c['proc'](rgb, return_tensors='pt')
    with torch.no_grad():
        emb = c['model'].get_image_embeddings(inputs['pixel_values'])
    out = []
    for x, y in points:
        q = c['proc'](rgb, input_points=[[[float(x), float(y)]]], return_tensors='pt')
        q.pop('pixel_values')
        with torch.no_grad():
            r = c['model'](image_embeddings=emb, **q)
        m = c['proc'].image_processor.post_process_masks(r.pred_masks, q['original_sizes'], q['reshaped_input_sizes'])[0][0]
        k = int(r.iou_scores[0, 0].argmax())
        out.append(dict(mask=m[k].numpy().astype(bool), score=float(r.iou_scores[0, 0, k]), prompt=(x, y)))
    return out


def masks_auto(rgb, points_per_side=32):
    """Every object SAM finds on a grid of prompts (no clicks)."""
    from PIL import Image
    res = _load()['auto'](Image.fromarray(rgb), points_per_batch=64, points_per_side=points_per_side)
    return [dict(mask=np.asarray(m, bool), score=float(s)) for m, s in zip(res['masks'], res['scores'])]


def _clean(mask):
    # biggest piece, holes filled, edges smoothed
    lab, n = ndi.label(mask)
    if n == 0:
        return mask
    m = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    m = ndi.binary_fill_holes(m)
    k = np.ones((5, 5), np.uint8)
    return cv2.morphologyEx(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k) > 0


def _midline(mask):
    # longest path through the skeleton (two breadth-first searches give the two far ends)
    ys, xs = np.nonzero(skeletonize(mask))
    if len(xs) < 10:
        return None
    pix = set(zip(xs.tolist(), ys.tolist()))
    nbr = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]

    def bfs(start):
        prev, q, last = {start: None}, deque([start]), start
        while q:
            last = p = q.popleft()
            for dx, dy in nbr:
                n = (p[0] + dx, p[1] + dy)
                if n in pix and n not in prev:
                    prev[n] = p
                    q.append(n)
        return last, prev

    a, _ = bfs(next(iter(pix)))
    b, prev = bfs(a)
    path = [b]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    return np.array(path, float)


def band_shape(mask):
    """Describe a mask as a band: midline, width, length/width ratio and total bend of the midline (deg)."""
    m = _clean(mask)
    mid = _midline(m)
    if mid is None or len(mid) < 20:
        return None
    width = 2 * float(np.median(ndi.distance_transform_edt(m)[mid[:, 1].astype(int), mid[:, 0].astype(int)]))
    sm = np.stack([ndi.gaussian_filter1d(mid[:, i], 8, mode='nearest') for i in (0, 1)], 1)
    d = np.diff(sm[::4], axis=0)
    ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    length = float(np.hypot(*np.diff(mid, axis=0).T).sum())
    return dict(mask=m, midline=mid, width=width, elongation=length / max(width, 1.0),
                bend_deg=float(np.degrees(ang.max() - ang.min())), area=int(m.sum()))


def band_sides(shape):
    """Split the band's outline into its two long sides (the bed's two boundaries), dropping the end caps."""
    cs, _ = cv2.findContours(shape['mask'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :].astype(float)
    a, b = shape['midline'][0], shape['midline'][-1]
    ia, ib = (int(np.argmin(np.hypot(*(c - p).T))) for p in (a, b))
    if ia > ib:
        ia, ib = ib, ia
    s1, s2 = c[ia:ib + 1], np.vstack([c[ib:], c[:ia + 1]])[::-1]
    cap = 0.75 * shape['width']             # the outline near each end runs across the bed, not along it
    sides = []
    for s in (s1, s2):
        keep = (np.hypot(*(s - a).T) > cap) & (np.hypot(*(s - b).T) > cap)
        idx = np.nonzero(keep)[0]
        sides.append(s[idx.min(): idx.max() + 1] if len(idx) > 10 else s)
    return sides
