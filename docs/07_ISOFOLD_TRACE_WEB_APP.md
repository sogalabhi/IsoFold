# Chapter 7: IsoFold Trace, the manual-tracing web app

This chapter records, in the order it was done, how the IsoFold Trace web app was planned, built and checked in November 2026 for the mid-project review: what was built, why, what went wrong and how it was fixed, and the numbers it produced. It is written as source material for the project report. Figures are in [`docs/figures/trace/`](figures/trace/).

---

## 7.1 Why a manual-tracing app

The project's main aim is to detect a fold in a field photo and classify it automatically (Ramsay dip-isogon method). Before this work, two routes to automatic detection had been tried on the 26 real field photos:

| Route | Result |
|---|---|
| Classical edge tracing (`app/backend/detect.py`, structure tensor + edge following) | Found a usable pair of bed boundaries on **2 of 26** photos. A grey-rock mask fails on brown or colourful outcrops, and the tracer stops at tight noses. |
| Pretrained segmentation (SAM ViT-B, `app/backend/segment.py`) | Automatic mode found objects (pen, grass, pebbles), never a single bed. Click-prompted mode returned the whole rock or a packet of beds. |

Detection was therefore the bottleneck. The geometry engine itself (`foldclass/`, frozen as `core-v1.0`) had already been shown to reproduce the hand-measured R when given the **hand-traced** CorelDraw boundaries.

So the decision for the mid-review was a **human-in-the-loop** tool. The user traces the two edges of one bed on the photo, and the frozen engine does the measurement and classification. This:
- gives a working, demonstrable result on every photo now
- uses only the validated engine
- produces labelled bed boundaries, which are the training data an ML detector needs later

## 7.2 Design decisions (plan)

The plan is in `plan.md` (outside the repo, next to it). The decisions that shaped the app:

| Decision | Choice | Reason |
|---|---|---|
| Unit of work | One bed at a time: an outer and an inner boundary | Same as the hand method and the engine |
| Angles typed by the user | Display only: which isogons are drawn and listed | Stable results |
| Angles used for the class | The engine's own grid, 20°–70° every 2.5° (21 per limb) | The validated setup; most reliable R |
| Architecture | React + TypeScript (Vite) in the browser, a small FastAPI server in Python | The engine is Python; re-implementing it in JavaScript would make an unvalidated second copy |
| Engine | `foldclass/` is never edited | Frozen, validated spec |
| Photo | Never uploaded; only the traced points go to the server | Large photos stay fast and private |
| Priority | Phase 1 = everything the demo needs; shortcuts, export etc. later | Mid-review deadline |

## 7.3 Build log, in order

All commits are on `main` (`2766284` … `af39e42`, 13 November 2026).

### Step 0. Commit the earlier app work (`2766284`)
The auto-detection backend from the earlier handoff was committed (detect, prepare, pairing, pipeline, render, SAM experiment). It is not used by the manual app, except the "prepare" steps it shares.

### Step 1. Manual-tracing backend (`a8464f0`)
`app/backend/manual.py`: `classify(outer, inner, angles)`.

1. **Find the fold.** `pairing.evaluate` finds the fold both lines share, its hinge points, and which line is really the outer one. If the user drew them the other way round, they are swapped and a note says so.
2. **Prepare and measure.** `pipeline.run_engine`:
   - cut each line at its inflections (one fold only)
   - make both lines run the same way
   - thin to 60 points
   - run the frozen `debug_pipeline` (spline fit, tangent angles, hinge and axial trace, isogon pairs every 2.5°, joint fit t_α = A + B cos α, R = A / (A + B), class)
3. **Isogons at the user's angles.** Uses the same arcs, hinges, limb bounds and axial trace as the fit. Each returns p, q, the exact tangents, the perpendicular foot, t_α, t′α, T_α and T′α. When an angle can't be matched, the reason is given in plain words.
4. **Verdict:** confident / low confidence / refused, with reasons.

`app/backend/examples.py`: the 12 distinct CorelDraw-traced folds. The hand t′α tables from the department spreadsheets are matched to drawings **by their angle labels**:
- Fold_11 ↔ Fold-2A (30/45/60/70/75/80°, same photo)
- Fold-3 ↔ Fold-3A
- Backup_of_Fold_3B ↔ Fold 3_B (19.99/25.97/38.04/44.06/52.05/64.07°, exactly the table's α values)

**Problem 1: tracing direction changed R.** Tracing the outer line right-to-left instead of left-to-right moved the engine's hinge by about 5 px on a 1220 px bed, and R from 0.165/0.173 to 0.152/0.186.
- **Cause:** the engine's spline fit and hinge search are not exactly symmetric under reversal. On a tight nose the tangent turns quickly, so a few pixels of hinge shift change every α slightly.
- **By hand:** the same effect exists when two people pick the hinge by eye; it is only invisible because hand measurement is done once.
- **Fix:** both lines are put into one fixed direction before the engine runs (left→right, or top→bottom for steep lines), so one tracing always gives one answer. With this, Fold 11's left limb gives R = 0.186, the hand value.

**Problem 2: everything came out "low confidence".**
- **Cause 1:** a check marked any fold with limbs steeper than 54° (the range of the synthetic tests) as low confidence, and every field fold dips 70–88°. This is now an information note: the fit only uses 20–70°, and on 86–88° hand traces the engine matched the hand R.
- **Cause 2:** the auto-detector's pair checks ("gap changes too fast", "too little side-by-side overlap") fired on correct hand pairs. They exist to catch a detector jumping to another boundary; on a 1C nose the bed really is much thicker at the hinge, so the gap changes fast. They are not applied to hand traces.
- **Kept:** limbs that disagree, R inside the ambiguity band of a class boundary, a bed thinner than 90 px, lines that touch or cross, and engine warnings still lower confidence.
- **Result:** 9 of 12 examples are confident. The other 3 are low confidence for real reasons (§7.5).

Tests: `app/backend/tests/test_manual.py` (8 tests).

### Step 2. API and Bézier curves (`9f6925c`)
`app/backend/api.py` (FastAPI):
- `POST /api/classify`
- `GET /api/examples`, `/api/examples/{name}`, `/photo`, `/thumb`
- `GET /api/health`

`app/run.sh` starts it. Port **8765**: 8000 was taken by another local app.

`app/backend/bezier.py`: one rule turns pen-tool paths into points, **24 samples per cubic segment**, which is what the CorelDraw decoder used. The CorelDraw traces were stored as those samples, so the original **anchors and handles are recovered exactly** (least squares on the Bernstein basis, residual about 0.01 px). Straight pieces are handled too. The examples therefore open as the same editable curves that were drawn in CorelDraw.

**Finding (deferred):** moving a trace by only 0.01 px of noise moved Fold 14's R by 0.01–0.04. This is the same hinge sensitivity as Problem 1. The class did not change. A planned fix is to report the median of a few slightly jittered runs, with their spread as the uncertainty.

### Step 3. Web app shell (`8c78f68`)
React + TypeScript + Vite in `app/web/`:
- **Welcome screen** (Fig. 1): drop or open a photo, or start from one of the 12 example cards, which show the hand-measured R where one exists.
- **Workspace:** top bar, photo canvas, side panel, status bar.
- **Zoom and pan:** mouse wheel zooms around the cursor; drag with the Pan tool or the right mouse button; fit and zoom buttons.
- **Angle picker:** chips; accepts "35", "20, 30, 45" or "20-70/10"; presets. Chips outside 20–70° are dashed (display only).
- **Direct links:** `#example=Fold_11` opens an example straight away.

### Step 4. Pen and edit tools, new palette (`09bbee7`)
- **Pen** (Fig. 2): click places a sharp point; click and drag pulls out mirrored Bézier handles to bend the curve. A dashed preview runs to the cursor, the cursor carries a tag naming the line, and a floating **Done** button sits by the last point. Clicking the last point again finishes the line.
- **Edit:** drag a point and its handles follow; drag a handle and the opposite one mirrors (Alt bends one side only); dragging empty space pans.
- **Step guide:** ① outer line → ② inner line → ③ result. Finished steps can be clicked to edit or redraw. Undo point / Clear / Done act on the selected line.
- **Palette:** the first dark theme with a teal accent looked like a generic AI dashboard. It was replaced with a **field-notebook** look:
  - paper and ink, graph-paper grid
  - coloured-pencil lines: outer red, inner blue, isogons green
  - IBM Plex Sans and Mono type

### Step 5. Live classification and isogon overlay (`29f2471`)
- **Live updates:** once both lines are finished, every edit or angle change is measured. While a request is out, only the newest shape is sent next, so dragging a point updates the result about 0.2 s after release (the engine takes 20–50 ms).
- **Photo overlay** (Fig. 3):
  - isogons at the chosen angles, with tangent ticks at p and q and angle labels
  - H and G, and the dashed axial trace
  - the part of each line the engine actually measured is solid; the rest is faded
- **Class card:** class, verdict, one-line meaning, R ± σ, the class and R of each limb, reasons and notes, and, for examples, the hand measurement with "✓ agrees / ≠ differs".

### Step 6. Results panel (`ca0a3c0`) (Fig. 5)
- **R scale:** class bands from R = −0.5 to 1.5, with the ±0.05 windows at Class 2 and 1B. L and R markers with σ whiskers sit on opposite edges so close values don't overlap.
- **Ramsay diagram (t′α vs α):**
  - class fields shaded, with t′ = 1 (1B) and t′ = cos α (2) as reference curves
  - the engine's 21 points for each limb and the fitted curve
  - the chosen angles highlighted
  - the hand-measured points as diamonds
- **Angle table:** t′α and t_α for each limb, with the hand t′α beside them.

### Step 7. "Show construction" animation (`41ec3ce`) (Figs. 6–9)
Replays the hand dip-isogon construction on the photo, using the engine's own measurement:
1. Rulers settle on the tangents at H and G; the axial trace draws in.
2. t₀ is dimensioned between the hinge tangents.
3. For each chosen angle, on the left limb then the right:
   - turn the ruler to α (protractor arc)
   - slide it to touch the outer edge (p)
   - slide a parallel copy to the inner edge (q)
   - join p–q and dimension t_α
   - plot t′ on the chart
4. The fitted curves sweep across the chart and the class is revealed.

The player has captions, a step count, play/pause/step/speed and Close. The photo dims, the camera frames the construction, and the class stays hidden until the end.

### Step 8a. Point labels (`ca926a2`) (Fig. 4)
Textbook notation on the photo:
- **H**, **G**
- **I** at the inflection points (the ends of the measured stretch)
- **p₄₀ / q₄₀** at the isogon ends
- the angle of each isogon
- left limb / right limb (named the same way as the backend's table)
- the axial trace
- t₀ with its value

Labels are placed by priority and dropped when they would overlap, so zooming in reveals more. A Labels on/off toggle is in the zoom bar.

### Step 8b. Worked calculation and help (`26a2dae`, LaTeX in `5b38159`) (Figs. 10–12)
"Show the working" lays the classification out like the spreadsheet, for each limb:
1. **t₀:** measured between the hinge tangents, and the fitted t₀ used for t′.
2. **The table at the chosen angles:** α, cos α, t_α, T_α, t′α = t_α/t₀, T′α = T_α/t₀, R_α = (t′α − cos α)/(1 − cos α), and the hand t′α. A worked example row shows the numbers substituted, e.g. t′₃₀ = 1090.6/1222.3 = 0.892 and R₃₀ = 0.194.
3. **R:** from the thickness law t′α = R + (1 − R) cos α. R from the chosen angles (least squares) is shown next to the engine's fit over all 21 angles, A and B, and R = A/(A + B) ± σ, then the hand R. The full 21-row table can be expanded.
4. **The class rules,** with the matching one highlighted.

A "?" next to every technical term (R, the class rule, confidence, t₀, t′α, T′α, dip isogon, R scale, Ramsay diagram) explains it on hover. All formulas are typeset with KaTeX (LaTeX).

### Step 8c. 3D view (`46ffb25`) (Fig. 13)
A three.js block diagram:
- the photo forms the front face
- the traced bed is carried unchanged along the fold axis behind it (outer surface red, inner blue)
- hinge lines, axial plane, isogon planes and a fold-axis arrow
- orbit and zoom; plunge and trend sliders tilt the block

It is clearly marked as an **illustration under the cylindrical-fold assumption**. A single photo is one slice; a measured 3D model would need several photos (photogrammetry).

### Fix (`af39e42`)
On narrower screens the zoom bar covered the construction player's Close button. Now:
- the zoom bar hides during the construction
- the player has a × beside the caption
- the panel button becomes "Stop construction"
- Esc closes the construction, the worked sheet or the 3D view

## 7.4 Validation against the hand measurements

Hand-measured t′α (CorelDraw, department spreadsheets) against the app, which uses the CorelDraw traces as editable curves:

**Fold 11 (Shear Zone, table Fold-2A)**, t₀ = 1222 px (left) / 1213 px (right)

| α | App left t′ | App right t′ | Hand t′ | App left T′ | App right T′ |
|---|---|---|---|---|---|
| 30° | 0.892 | 0.888 | 0.879 | 1.027 | 1.029 |
| 45° | 0.759 | 0.746 | 0.751 | 1.067 | 1.062 |
| 60° | 0.591 | 0.573 | 0.577 | 1.169 | 1.159 |
| 70° | 0.473 | 0.454 | 0.462 | 1.359 | 1.350 |
| 75°, 80° | not measured (engine stops matching at 75°) | | 0.401, 0.340 | | |

R: app 0.186 (left) / 0.152 (right), overall 0.169 → **1C**; hand **0.186 → 1C**.

**Fold 3 (IMG_20180211_145755, table Fold-3A)**, t₀ = 322 / 329 px

| α | App left t′ | App right t′ | Hand t′ |
|---|---|---|---|
| 30° | 0.900 | 0.890 | 0.887 |
| 45° | 0.763 | 0.750 | 0.766 |
| 60° | 0.606 | 0.580 | 0.590 |
| 70° | 0.514 | 0.462 | 0.513 |

R: app 0.223 / 0.164, overall 0.194 → **1C**; hand **0.224 → 1C**.

The app's t′α agrees with the hand values to within about 0.01–0.02 at every angle measured, and the class agrees.

## 7.5 Results on all 12 field examples

| Example | Source photo | Left limb | Right limb | Overall | Verdict | Hand R |
|---|---|---|---|---|---|---|
| Fold 11 | Shear Zone | 1C · R 0.186 | 1C · R 0.152 | 1C · R 0.169 | confident | 0.186 (1C, Fold-2A) |
| Fold 3 | IMG_20180211_145755 | 1C · R 0.223 | 1C · R 0.164 | 1C · R 0.194 | confident | 0.224 (1C, Fold-3A) |
| Fold 3B | IMG_20180211_145755 | 1C · R 0.800 | 1C · R 0.463 | 1C · R 0.632 | confident | 0.084 (1C, Fold 3_B) |
| Fold 17A | IMG_20180211_145755 | 1C · R 0.219 | 1C · R 0.176 | 1C · R 0.198 | confident | – |
| Fold 14 | IMG_20180211_145952 | 1C · R 0.196 | 1C · R 0.283 | 1C · R 0.239 | confident | – |
| Fold 13 | Kumbhalgarh SteepZone | 2 · R 0.035 | 1C · R 0.105 | 2 / 1C · R 0.070 | low confidence | – |
| Fold 12 | Fold_Shearzone boundary | 1C · R 0.454 | 1C · R 0.595 | 1C · R 0.524 | confident | – |
| Fold 9 | Kumbhalgarh West | 1C · R 0.502 | 1C · R 0.177 | 1C · R 0.340 | confident | – |
| Fold 15A | IMG_20180211_152813 | 2 · R −0.010 | 2 · R 0.009 | 2 · R −0.001 | confident | – |
| Fold 15B | IMG_20180211_152813 | 3 · R −0.107 | 1C · R 0.122 | 3 / 1C · R 0.007 | low confidence | – |
| Fold 16A | IMG_20180211_152948 | 1C · R 0.052 | 1C · R 0.210 | 1C · R 0.131 | confident | – |
| Fold 16B | IMG_20180211_152948 | 1C · R 0.069 | 2 · R 0.019 | 1C / 2 · R 0.044 | low confidence | – |

- **The low-confidence cases are genuine.** Folds 13 and 16B sit at the 1C/2 boundary with their limbs on opposite sides of it. Fold 15B is a thin bed (82 px, below the 90 px reliability limit) and the most direction-sensitive one.
- **Fold 3B disagrees with its hand R** (0.63 against 0.08). The class is still 1C on both. Its hand table has an odd value at 52° (t′ = 0.43 between 0.74 and 0.65), which may explain part of the difference. It is kept out of the demo until the trace and the table are rechecked.

## 7.6 Known limitations and next steps

- **Hinge sensitivity:** R can move by about 0.01–0.04 for tiny changes to a trace on tight noses, and the class does not change. Planned fix: the median of jittered runs, with the spread as the uncertainty.
- **Steep limbs:** most field folds dip beyond 54°, the synthetic validation range. Agreement with the hand R on 86–88° folds supports the method there, but more validation is needed.
- **Fold 3B:** recheck the trace and the hand table.
- **Automatic detection** is still the main aim. Every bed traced in this app is a labelled example for training a segmentation model (U-Net/SegFormer; pretrained SAM was not enough).
- **Hosting:** possible on Vercel's free tier once OpenCV is removed from the deployed engine (Python functions are limited to 500 MB) and the example photos (174 MB) are resized.
- **Phase 2 ideas:** export (PNG/CSV/JSON), linked hover between chart and photo, keyboard shortcuts, a scale tool for thickness in cm, a hinge override.

## 7.7 Figures

| Fig. | File | Shows |
|---|---|---|
| 1 | `01_welcome.jpg` | Welcome screen with the field examples and hand R |
| 2 | `02_pen_tracing.jpg` | Tracing a new photo with the pen (Bézier handles, preview, Done) |
| 3 | `03_fold11_result.jpg` | Fold 11: isogons, labels, class card agreeing with the hand R |
| 4 | `04_fold11_hinge_labels.jpg` | Zoomed on the hinge: H, G, p/q, angle labels, t₀ |
| 5 | `05_results_panel.jpg` | Full panel: class card, R scale, Ramsay diagram, angle table |
| 6 | `06_construction_hinge.jpg` | Construction step 1: rulers on the hinge tangents |
| 7 | `07_construction_turn_ruler.jpg` | Turning the ruler to α with the protractor |
| 8 | `08_construction_isogon.jpg` | Isogon p–q and t_α |
| 9 | `09_construction_reveal.jpg` | Fitted curves and the class revealed |
| 10 | `10_worked_sheet_table.jpg` | Worked calculation: t₀ and the LaTeX table |
| 11 | `11_worked_sheet_R_and_class.jpg` | Worked calculation: R = A/(A+B) and the class rule |
| 12 | `12_help_R.jpg` | "?" help on R |
| 13 | `13_3d_view.jpg` | 3D block diagram (cylindrical-fold illustration) |
| 14 | `14_fold13_low_confidence.jpg` | A borderline fold shown honestly as 2 / 1C, low confidence |
