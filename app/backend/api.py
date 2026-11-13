"""IsoFold Trace web API (plan.md, section 5). Local only for now.

    POST /api/classify                 {outer: Path, inner: Path, angles: [deg]}  ->  manual.classify result
    GET  /api/health                   engine tag, whether the example dataset is present
    GET  /api/examples                 the hand-traced field folds (title, locality, hand-measured R, thumb url)
    GET  /api/examples/{name}          one example: photo url + both lines as editable Bezier paths
    GET  /api/examples/{name}/photo    the full-resolution photo
    GET  /api/examples/{name}/thumb    a small crop around the traced fold, for the example cards

A Path is {"anchors": [{"p": [x, y], "in": [x, y] | null, "out": [x, y] | null}, ...]} (what the pen tool
draws; sampled here by bezier.sample) or {"points": [[x, y], ...]}. Coordinates are image pixels.
If app/web/dist exists (the built React app) it is served at /.

Run:  app/run.sh"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import bezier
import examples
import manual
import pipeline

WEB_DIST = Path(__file__).resolve().parents[1] / 'web' / 'dist'
THUMBS = pipeline.DATA / 'thumbs'

app = FastAPI(title='IsoFold Trace')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
                   allow_methods=['*'], allow_headers=['*'])        # the Vite dev server


class Anchor(BaseModel):
    p: list[float] = Field(min_length=2, max_length=2)
    in_: Optional[list[float]] = Field(None, alias='in')
    out: Optional[list[float]] = None


class TracedPath(BaseModel):
    anchors: Optional[list[Anchor]] = None
    points: Optional[list[list[float]]] = None

    def to_points(self):
        if self.anchors is not None:
            return bezier.sample([{'p': a.p, 'in': a.in_, 'out': a.out} for a in self.anchors])
        return np.asarray(self.points or [], float).reshape(-1, 2)


class ClassifyRequest(BaseModel):
    outer: TracedPath
    inner: TracedPath
    angles: list[float] = [20, 40, 60]


@app.post('/api/classify')
def classify(req: ClassifyRequest):
    return manual.classify(req.outer.to_points(), req.inner.to_points(), req.angles)


@app.get('/api/health')
def health():
    return dict(ok=True, engine=pipeline.ENGINE_TAG, examples=(examples.TRACES / 'boundaries' / 'index.json').exists())


def _urls(name):
    return dict(thumb_url=f'/api/examples/{name}/thumb', photo_url=f'/api/examples/{name}/photo')


@app.get('/api/examples')
def list_examples():
    try:
        return [dict(e, **_urls(e['name'])) for e in examples.catalog()]
    except FileNotFoundError:
        return []


@lru_cache(maxsize=None)
def _example(name):
    try:
        ex = examples.load(name)
    except (StopIteration, FileNotFoundError):
        raise HTTPException(404, f'no example called {name}')
    # colour the lines the way the engine reads them: the line it takes as the outer edge is "outer"
    if manual.classify(ex['outer'], ex['inner'])['swapped']:
        ex = dict(ex, outer=ex['inner'], inner=ex['outer'])
    return ex


@app.get('/api/examples/{name}')
def get_example(name: str):
    ex = _example(name)
    info = {k: v for k, v in ex.items() if k not in ('outer', 'inner', 'photo_path')}
    return dict(info, **_urls(name), outer=dict(anchors=bezier.from_samples(ex['outer'])),
                inner=dict(anchors=bezier.from_samples(ex['inner'])))


@app.get('/api/examples/{name}/photo')
def example_photo(name: str):
    return FileResponse(_example(name)['photo_path'], media_type='image/jpeg')


@app.get('/api/examples/{name}/thumb')
def example_thumb(name: str):
    path = THUMBS / f'{name}.jpg'
    if not path.exists():
        ex = _example(name)
        img = cv2.imread(str(ex['photo_path']))
        H, W = img.shape[:2]
        pts = np.vstack([ex['outer'], ex['inner']])
        (x0, y0), (x1, y1) = pts.min(0), pts.max(0)
        # a 4:3 box around the traced fold with a margin, kept inside the photo
        w, h = (x1 - x0) * 1.3, (y1 - y0) * 1.3
        w, h = min(max(w, h * 4 / 3), W), min(max(h, w * 3 / 4), H)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        x0, y0 = int(np.clip(cx - w / 2, 0, W - w)), int(np.clip(cy - h / 2, 0, H - h))
        crop = img[y0:y0 + int(h), x0:x0 + int(w)]
        THUMBS.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), cv2.resize(crop, (480, 360), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return FileResponse(path, media_type='image/jpeg')


if WEB_DIST.exists():
    app.mount('/', StaticFiles(directory=WEB_DIST, html=True), name='web')
