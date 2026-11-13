# IsoFold: web app handoff (upload a photo, get the Ramsay isogon result)

This package holds all the code written in the Claude sessions of 3 Nov 2026, the test photos and results, and a plan for the next step:
**a simple web UI plus a backend that runs locally** (hosting comes later). You upload a fold photo, and it returns the boundary lines, dip isogons and Ramsay class, or a clear refusal.

Read sections 1–5 for context and 6–10 to build the app. Section 11 is a prompt you can paste into Claude Code.

---

## 1. What exists today

| Part | Where | Status |
|---|---|---|
| Frozen geometry engine (spline fit, tangent angles, isogon matching, t0 and R fit, Ramsay class, refusal checks) | IsoFold repo, `foldclass/` (tag `core-v1.0-frozen`, spec `docs/CORE_V1_FROZEN_SPEC.md`) | Done. 10/10 tests pass. **Do not edit.** |
| Automatic boundary detection, no AI model | `code/autotrace.py` (this package) | Works on clear photos. Not in the repo yet. |
| Glue from detected lines to the engine | `code/run_pairs_experiment.py` | Experiment only. Hard-coded to two test photos. |
| Automatic pairing (pick the inner and outer line of one bed) | – | **Not built.** This is the biggest missing piece. |
| Verdict and confidence logic | – | **Not built.** |
| Web UI and API | – | **Not built.** This is the next job. |

Repo: <https://github.com/sogalabhi/IsoFold> (latest commit `32a46ab`, no newer commits as of 9 Nov 2026).

---

## 2. How the pipeline goes from photo to result

```
photo ─► 1 detect lines ─► 2 keep complete fold lines ─► 3 pick a pair (inner/outer)  [NOT BUILT]
      ─► 4 cut each line to one fold ─► 5 same direction + thin to ~60 points
      ─► 6 frozen engine: debug_pipeline() ─► 7 checks and verdict  [NOT BUILT]
      ─► 8 drawing: lines + isogons + result card
```

### Step 1: Detect lines (`autotrace.detect`)
The goal is to find edges that run *with* the layering and ignore everything else.

1. **Contrast boost:** CLAHE on the L channel of the LAB colour space.
2. **Layer direction everywhere:** a structure tensor gives the main layer direction at each pixel, plus a 0–1 "how layered is this area" score (`coh`).
   ```python
   phi = 0.5*np.arctan2(2*Jxy, Jxx - Jyy)   # direction across the layers
   ```
   Window size: `sigma_int` = 0.035 × image short side.
3. **Edges parallel to the layers only:** take the colour gradient (L, a and b channels, at two blur scales) along the across-layer direction. A crack cutting across beds has its gradient along the layers, so it scores about 0.
4. **Tool mask:** strongly saturated pixels (S > 150) are blanked. This catches hammers and coloured pens.
5. **Tracing:** start from the strongest edge points and step 1.5 px along the layer direction. At each step, nudge sideways onto the nearest edge maximum. Small gaps (8 steps) are allowed, which carries a line through a hinge.
6. **Clean-up:** join pieces whose ends meet heading the same way, smooth slightly, drop near-duplicates, and keep the longest and strongest lines.

### Step 2: Keep complete fold lines (`autotrace.pick_best`)
- **Bend:** the total turn of the line is at least 100°, so both limbs and the hinge are present.
- **Limbs:** each side of the hinge is at least 15% of the image short side.
- **Smoothness:** "wobble" (line length ÷ length of a heavily smoothed copy) is at most 1.12.
- **Inside the rock:** at most 5% of the line lies outside a grey-rock mask (saturation < 45, biggest region, shrunk by 3%). This rejects lines that hug the rock's outer edge or run into grass.
- **Ranking:** score = strength × length × bend × smoothness. Keep the top `n_best`.
- **Final smoothing:** a spline (`spline_smooth`) with a tolerance of 0.6% of the image short side.

### Step 3: Pick a pair (to build). See section 7.3.

### Step 4: Cut to one fold (`cut_at_inflections` in `run_pairs_experiment.py`)
The engine refuses a limb whose dip goes up and then down again ("phi is not monotonic"). That happens when a line runs past the inflection into the next fold. So:
1. Turn the line so the fold's hinge points up.
2. Find the hinge (top point).
3. On each side, find the point with the largest dip relative to the hinge. That is the inflection.
4. Keep only the part between the two inflections.

The maximum dip on each side is also returned. Use it for the "validated range" check (≤ 54°).

### Step 5: Prepare for the engine
- **Same direction:** both lines must run the same way. If not, reverse the inner one.
  ```python
  if np.dot(outer[-1]-outer[0], inner[-1]-inner[0]) < 0: inner = inner[::-1]
  ```
- **Thin:** resample evenly to about 60 points (what was tested). The engine's spline smoothing is `s = 0.15 × N`.

### Step 6: Frozen engine
```python
from foldclass.debug import debug_pipeline
r = debug_pipeline(outer_pts, inner_pts)          # seed_hinge=None -> automatic hinge
r['fits'][limb].t0, .R, .sigma_R;  r['classes'][limb].fold_class, .alpha_span, .warnings;  r['hg_dist']
```
- It raises an exception with a plain-English reason when it refuses. Catch it and show the reason.
- `plot_annotated_fold(img, r, output_path=...)` draws the publication-style figure. **Don't use its summary box as-is** (see section 4).

---

## 3. Results so far

| Photo | Detection | Engine result | Trust? |
|---|---|---|---|
| Collage panel 8 (S-fold) | Whole beds traced through both hinges | – | Detection good |
| Collage panel 9 | Top of white bed: median 1 px from hand trace, ~55% within 5 px; bottom ~43% | – | Partial |
| Collage panel 7 | Inner arcs 50–68% within ~5 px; outer arc missed (low contrast) | – | Partial |
| Collage panel 6 (hazy) | Mostly fails | – | No |
| `photo1_sfold_screenshot.png` | Best 3 lines all on real beds; green + magenta = top and bottom of one bed | Antiform: left limb Class 3, right limb 1C. Synform: 1C / 3. t0 ≈ 18–22 px | **No:** too thin, limbs disagree |
| `photo2_lenscap_screenshot.png` | 2 of 3 best lines good; magenta slips onto the rock edge | Left limb 1C (R = 0.15), right limb refused (15° span). t0 ≈ 65 px | **No:** below 90 px, dip up to 121° |
| `photo3_tight_fullres.jpg` | Limbs traced, no line goes around the tight nose → 0 complete lines | Not run | Correct outcome = refuse (fold too tight) |

Images: `results/*.jpg`. The lines found on photos 1 and 2: `results/*_curves.json`.

**Conclusion:** the full chain runs without clicks, but no photo so far meets the engine's limits (t0 ≥ 90 px, limb dip ≤ 54°). The app has to say so clearly instead of showing a class as if it were reliable.

---

## 4. Bugs found in the repo (not fixed: the repo was only read)

1. **`tools/run.py` crashes:** it uses `config.SPLINE_SMOOTHING_RATIO` without importing it. Fix:
   ```python
   from foldclass import config
   ```
   (`code/run_fixed.py` is a copy with this one line added.)
2. **`test-fold.png` traces fail** on the current commit: the engine says the two hinge points aren't matching points on the two boundaries (in the error, `|HG|` = 537 px vs ~92 px between the lines), even with the automatic hinge. `test-fold-2` works.
3. **`MIN_LAYER_THICKNESS_PX = 90` is never checked.** It's defined in `config.py` but no code reads it. The app must check it.
4. **The `plots.py` summary box is misleading:**
   - It shows only the first limb's class (`cls_labels[0]`), so a disagreement is hidden.
   - "Mean R" averages in limbs the engine refused.
   - The box labels `|HG|` as "Hinge Thickness t₀", but it isn't the fitted t0.

   The app should build its own result card from the per-limb values.

---

## 5. Photo rules (show these in the UI next to the upload button)

1. **Camera square to the rock face**, no tilt. This avoids perspective stretch.
2. **Rock face cuts across the fold axis** (a true profile section). Note the axis or plunge if known.
3. **Full-resolution original**, not a phone screenshot.
4. **Target bed at least 90 px thick** in the photo.
5. **Open, rounded fold with limbs dipping under ~54°.** Tight, isoclinal or chevron folds will be refused.
6. **Even light, no hard shadows.** A scale object such as a pen is fine.

---

## 6. App: what it does

**User flow:**
1. Open `http://localhost:5173`.
2. Read the photo checklist and drop a photo.
3. Wait about 5–30 s.
4. See the result:
   - the photo with an overlay (all lines / chosen pair / isogons)
   - a verdict banner (**Classified**, **Low confidence** or **Refused**)
   - per-limb numbers
   - the reasons
5. Optional: tap two other lines to choose a different pair, and the analysis reruns.
6. Download the annotated PNG and the result JSON.

**Not in v1:** accounts, a database, multiple beds per photo, Fourier analysis, uncertainty runs.

---

## 7. App: how to build it

### 7.1 Folder layout (suggested: an `app/` folder in the IsoFold repo)
```
app/
  backend/
    main.py            # FastAPI app: routes only
    pipeline.py        # analyze(image_path, params) -> dict   (no web code in here)
    detect.py          # autotrace.py moved here (detect, pick_best, rock_mask, spline_smooth, ...)
    pairing.py         # NEW: choose outer/inner pair
    prepare.py         # cut_at_inflections, same-direction, thin  (from run_pairs_experiment.py)
    verdict.py         # NEW: classified / low confidence / refused
    render.py          # overlay PNG + engine figure
    requirements.txt
    tests/
  frontend/            # React + Vite (or one plain index.html + JS for the very first version)
```
- **Keep `pipeline.py` free of FastAPI code.** It can then be tested from the command line and reused by the mobile app later.
- **`foldclass` is installed from the repo**, with `pip install -e ../../foldclass`. Never copy or edit its geometry.

### 7.2 Backend API (FastAPI)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | – | `{"ok": true, "engine": "core-v1.0-frozen"}` |
| POST | `/api/analyze` | multipart `image` (+ optional JSON `params`) | result JSON (below) |
| POST | `/api/analyze/{job_id}/pair` | `{"outer_id": 2, "inner_id": 0}` | result JSON for a user-chosen pair (reuses saved lines, no new detection) |
| GET | `/api/files/{job_id}/{name}` | – | `overlay.png`, `engine.png`, `original.jpg` |

- **Storage:** save uploads in `app/backend/data/{job_id}/`, where `job_id` is a uuid. That's enough for local use.
- **Allow the frontend's address:** add CORS for `http://localhost:5173`.
- **Speed:** a synchronous request is fine for v1, with a spinner on the frontend. Later, for hosting, move analysis to a background worker (Celery + Redis) and have the frontend poll `/api/jobs/{id}`.

**Result JSON (contract between backend and frontend):**
```json
{
  "job_id": "…",
  "image": {"width": 2212, "height": 1659, "analysed_scale": 1.0},
  "lines": [{"id": 0, "points": [[x,y], …], "complete": true, "bend_deg": 185, "strength": 0.70, "inside_rock": 0.99}],
  "pair": {"outer_id": 2, "inner_id": 1, "median_gap_px": 18.0, "layer_package": false, "auto": true},
  "limbs": {
    "left":  {"class": "3",  "R": -0.452, "sigma_R": 0.016, "t0_px": 21.2, "alpha_span_deg": 37, "max_dip_deg": 80, "warnings": []},
    "right": {"class": "1C", "R": 0.884,  "sigma_R": 0.013, "t0_px": 18.4, "alpha_span_deg": 50, "max_dip_deg": 71, "warnings": []}
  },
  "isogons": [[[x1,y1],[x2,y2]], …],
  "hinges": {"H": [x,y], "G": [x,y], "hg_dist_px": 19.4},
  "verdict": {"status": "low_confidence", "class": null,
              "reasons": ["Bed is 19 px thick; engine is validated from 90 px.",
                          "Limbs disagree (3 vs 1C).",
                          "Limb dips up to 80°; validated range is ≤ 54°."]},
  "files": {"overlay": "/api/files/…/overlay.png", "engine": "/api/files/…/engine.png"},
  "timings_ms": {"detect": 4100, "engine": 900}
}
```
- Return **all line coordinates** so the frontend can draw them as SVG and toggle layers without new requests.
- Return **coordinates in original-image pixels**, even if detection ran on a resized copy (see 7.3, step 0).

### 7.3 `pipeline.analyze()`, step by step

0. **Load and resize.** Load with OpenCV. If the long side is over ~2200 px, run detection on a resized copy (this is slow: about 12 s at 2212×1659 on CPU). Multiply the line points back by the scale factor before step 4, so thickness is measured in original pixels.
1. **Detect.** Call `detect(bgr, np.zeros(bgr.shape[:2], bool), P)`. **Pass an empty annotation mask.** The yellow-line eraser only exists for the annotated collage and would paint over yellow grass or rock in real photos. Use `max_curves=30, min_len=0.25`.
2. **Complete lines.** Call `pick_best(curves, H, W, P, rock_mask(bgr, P))` with `n_best` ≈ 8, so there are enough candidates for pairing.
   - **Keep each line's unsmoothed points** (e.g. `d['raw'] = d['pts'].copy()`) before `spline_smooth`. Step 3b needs them.
3. **Pairing (NEW, `pairing.py`).** For every pair (a, b) of complete lines:
   - Resample both to about 200 points.
   - **Gap profile:** the distance from each point on a to the nearest point on b, using `scipy.spatial.cKDTree`.
     ```python
     gap, idx = cKDTree(b).query(a)
     ```
   - **Overlap:** the fraction of a's points whose nearest b-point is not one of b's last ~5% at either end, so the two lines really run side by side. Need ≥ 0.7, checked both ways.
   - **No crossing:** the side of b that a is on must not change sign along the overlap. Ignore points closer than 2 px.
   - **Same fold:** the hinge points (from `fold_metrics`) are within 1.5 × the median gap.
   - **Thickness:** median gap ≥ `config.MIN_LAYER_THICKNESS_PX` (90) in original pixels. If no pair reaches 90, still return the best pair, but the verdict becomes "low confidence".
   - **Score:** overlap × mean strength. Prefer the smallest gap that is ≥ 90.
   - **Layer package:** if other complete lines lie between a and b, set `layer_package = true`. The engine still works, but the result describes several beds together, so say so in the UI.
   - **Outer vs inner:** find the fold's opening direction, `o` = (midpoint of the two limb ends) − hinge. The outer line (extrados) is the one whose hinge lies further along −o, away from the fold core.

   3b. **Smoothing tied to thickness.** Re-smooth both chosen lines from their raw points with `spline_smooth(raw, tol)`, where `tol` ≈ 1–2% of the median gap. Don't use the fixed 0.6% of image size: on a 20 px bed that moved the line by ~35% of the thickness, against a validated limit of 1.7%.
4. **Cut to one fold.** Generalise `cut_at_inflections`:
   - Rotate the points so the opening direction `o` points down (+y). The hinge is then at the top.
   - Cut, then rotate back. The engine itself doesn't care about orientation.
   - Keep the returned maximum dips.
5. **Prepare.** Same direction, then thin to 60 points (section 2, step 5).
6. **Engine.** Wrap `debug_pipeline(o, i)` in try/except. On an exception, set verdict "refused" with the exception message as the reason. Get the isogon lines from `r['isogons']` (see `plots.py` for how they are drawn).
7. **Verdict (NEW, `verdict.py`):**

| Status | When |
|---|---|
| **refused** | No complete lines, or no valid pair, or the engine raised, or both limbs have `fold_class = None` |
| **low_confidence** | Any of: t0 < 90 px on a limb; max limb dip > 54°; the two limbs give different classes; one limb refused; `layer_package` is true; `sigma_R` large (start with > 0.1 and tune on real data) |
| **classified** | Both limbs give the same class, t0 ≥ 90 px, dips ≤ 54°, no warnings |

   Always return every reason, written in plain words, not just the first one.

8. **Render.**
   - `overlay.png`: the photo, all lines thin and grey, the chosen pair thick (outer solid, inner dashed), the isogons, and H/G marked.
   - `engine.png`: from `plot_annotated_fold`. If it's shown, hide or replace its summary box (section 4).

### 7.4 Frontend (React + Vite)
- **Upload page:**
  - a drag-and-drop area accepting `.jpg`/`.png` (warn above ~20 MB)
  - the photo checklist from section 5, as tick boxes the user confirms
  - an "Analyse" button
- **Waiting:** a spinner with "Detecting layers… / Running geometry engine…" (one request in v1).
- **Result page:**
  - **Left:** the photo with an SVG overlay. Toggles: *All lines*, *Chosen pair*, *Isogons*, *Hinges*. Zoom and pan help on big photos.
  - **Right:**
    - Verdict banner: green "Classified: Class 1B", amber "Low confidence", or red "Refused", with the reasons listed under it.
    - Limb table: Class, R ± σ, t0 (px), α span, max dip, warnings.
    - The pair's gap in px, and "layer package" if set.
    - Buttons: *Pick a different pair* (click two lines on the image, then POST `/pair`), *Download PNG*, *Download JSON*, *New photo*.
- **Error states:** the backend is not running, the upload is too big, or the server returned an error. Show a clear message for each.

### 7.5 Run locally
```bash
# backend
cd app/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ../../foldclass
uvicorn main:app --reload --port 8000
# frontend
cd app/frontend && npm install && npm run dev      # http://localhost:5173, proxy /api -> :8000
```
**requirements.txt** (versions used in testing): `fastapi`, `uvicorn[standard]`, `python-multipart`, `numpy` (2.5), `scipy` (1.18), `opencv-python-headless` (5.0), `scikit-image` (0.26), `matplotlib` (3.11). Python ≥ 3.11 (tested on 3.13).

### 7.6 Hosting later (not now)
- One Docker image for the backend, with the frontend built as static files and served by FastAPI or nginx.
- Add a background worker before going public, because analysis is CPU-heavy.
- Add an upload size limit and auto-delete old jobs.

---

## 8. Build order (each step ends with something you can check)

1. **CLI first.** `python -m pipeline samples/photo1_sfold_screenshot.png` prints the result JSON and writes `overlay.png`. Use the hard-coded pair from `run_pairs_experiment.py` until pairing exists.
   *Check:* photo 1 gives the same limb numbers as section 3.
2. **Pairing + 3b + generalised cutting.**
   *Check:* photo 1 picks green/magenta without hard-coding; photo 3 is refused with "no complete fold lines"; photo 2 picks cyan/green or explains why not.
3. **Verdict logic.**
   *Check:* all three sample photos come back `low_confidence` or `refused`, with the reasons from section 3.
4. **FastAPI routes** around `pipeline.analyze()`.
   *Check:* a `curl -F image=@samples/photo1_sfold_screenshot.png localhost:8000/api/analyze` round trip.
5. **Frontend:** upload → result page with SVG overlay and verdict.
6. **Pick-a-different-pair** route and UI.
7. **Tests** (pytest):
   - the pipeline on the 3 sample photos (status and pair, not exact floats)
   - a synthetic fold drawn as an image (two concentric arcs on a grey background), which should be classified with t0 ≥ 90
   - the API upload round trip
8. **Real check:** run on full-resolution, untouched photos of open folds and compare with hand traces (`tools/trace.py`). Only then trust "classified".

---

## 9. Known limits of the detector (tell users; fix later)

- **Tight, isoclinal or chevron noses:** lines stop at the hinge (photo 3). Correct behaviour is to refuse.
- **Hazy, low-contrast photos:** few lines (collage panel 6).
- **Clear or white pen barrels** aren't masked; only strongly coloured parts are.
- **Orange lichen and sandy patches** can be mistaken for soil by the rock mask (saturation < 45), which rejects good lines. The mask assumes grey rock.
- **Settings were chosen on very few photos.** Treat them as starting values, and tune them on a proper test set (about 70% for tuning, 30% kept untouched).
- **Screenshots** lower the resolution. Always use originals.

---

## 10. Package contents

| Path | What |
|---|---|
| `HANDOFF.md` | This file |
| `code/autotrace.py` | Detector: `detect`, `merge_curves`, `fold_metrics`, `pick_best`, `rock_mask`, `spline_smooth`, `score`, `draw`, `DEFAULT` settings, CLI |
| `code/run_pairs_experiment.py` | Glue experiment: `cut_at_inflections`, same direction, `thin`, `debug_pipeline`, plots. Hard-coded pairs. Run from the package root |
| `code/run_fixed.py` | Copy of `tools/run.py` with the missing `config` import added |
| `code/make_clean_paired_panels.py` | Test-only: merges collage panels 6A/6B and 7A/7B into trace-free images |
| `code/sweep_settings.sh` | Test-only: tries 4 settings on the merged panels |
| `samples/` | `photo1_sfold_screenshot.png`, `photo2_lenscap_screenshot.png` (both cropped from phone screenshots), `photo3_tight_fullres.jpg` (original) |
| `results/` | Overlays and engine figures from the runs in section 3, plus line JSON for photos 1 and 2 |
| `docs/previous_isofold_handoff.md` | The earlier project handoff (geometry engine history, dataset plan, ML plan) |

Both scripts were rerun from a fresh copy of this package on 9 Nov 2026 and reproduced the section 3 numbers exactly.

---

## 11. Prompt to paste into Claude Code (run it inside the IsoFold repo)

> Read `HANDOFF.md` in this folder first, then `docs/CORE_V1_FROZEN_SPEC.md`.
> Build the local web app described in sections 6–8 inside a new `app/` folder: a FastAPI backend (`pipeline.py` with no web code, plus routes) and a React + Vite frontend.
> Follow the build order in section 8 and stop after each step to show me the check result.
> Rules:
> (1) Never modify `foldclass/` geometry or config. Import it with `pip install -e foldclass`.
> (2) Move `code/autotrace.py` into `app/backend/detect.py` without changing its default settings.
> (3) Always pass an empty annotation mask to `detect()`.
> (4) Measure thickness in original-image pixels and enforce `config.MIN_LAYER_THICKNESS_PX` in the verdict.
> (5) Never show a class as reliable when the verdict is `low_confidence`; list every reason.
> (6) Explain each step in simple English, including why, before writing the code.
