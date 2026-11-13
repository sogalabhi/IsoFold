# Chapter 3 — Materials and Methods

## 3.1 Dataset and examples

The project dataset contains 26 field photographs. A set of 12 distinct field folds has hand-traced boundaries decoded from CorelDraw drawings and is used as the app’s example set. Some examples have corresponding hand-measured thickness tables from project spreadsheets.

**[VERIFY]** Confirm counts and inclusion criteria against `dataset/manifest.json`, `dataset/traces/`, and the app’s example index. State separately the number of photographs, the number of trace files, and the number of distinct fold examples where these differ.

## 3.2 Automatic-detection trials

Two approaches were investigated before the manual-tracing application was selected.

### 3.2.1 Classical image-processing and edge tracing

The classical trial used contrast enhancement and local layer-orientation information to favor edges aligned with bedding, followed by edge tracing and curve filtering. Candidate curves were evaluated for properties such as continuity, bend, length, smoothness, and location within the rock region. The intended next step was to identify a pair of curves representing the inner and outer boundary of the same bed.

A usable pair of bed boundaries was found on 2 of the 26 field photographs. The approach was unreliable where boundaries were faint, interrupted, or confused with other image features, and automatic pairing remained a difficult step.

**[VERIFY]** Confirm the exact algorithm settings, definition of “usable pair,” and per-image outcomes from `IsoFold/app/backend/` and experiment outputs. Avoid claiming that the detector successfully classifies all images.

### 3.2.2 Pretrained SAM segmentation trial

A pretrained Segment Anything Model (SAM, ViT-B in the documented trial) was evaluated in automatic and prompted modes. The purpose was to determine whether it could isolate a single bed or its boundaries without training a project-specific model.

The documented outcome was that automatic mode selected objects such as pens, grass, and pebbles rather than a single bed. Prompted mode returned the whole rock face or a packet of beds rather than the two boundaries of one target bed. It therefore did not provide usable single-bed boundaries for the classification pipeline.

**[VERIFY]** Confirm the trial configuration, prompt types, sample images, and stored outputs before adding quantitative claims about SAM.

## 3.3 Decision to use manual tracing

Automatic boundary extraction was the bottleneck in the image-to-classification pipeline. The geometry engine had been shown to reproduce hand-measured values when it was given hand-traced boundaries, while the automatic trials did not reliably supply the required pair. The project therefore developed a human-in-the-loop application: a user traces both boundaries of one bed, and the application performs the geometric measurement and reports the result. This provides a working analysis workflow and creates labeled traces that may support future automatic detection.

## 3.4 Manual tracing interface

IsoFold Trace is implemented as a React and TypeScript web interface with a local FastAPI server and Python backend. The user opens a local photo or a stored example, traces the outer and inner boundary of a bed using editable Bézier curves, and adjusts the curves as needed. The photograph remains in the browser; the traced coordinates are sent to the local engine for analysis.

The interface displays the boundaries, hinge and axial-trace information, dip isogons, point labels, measurements, per-limb Ramsay results, confidence reasons, an angle table, and a thickness-versus-angle chart. It also provides a worked-calculation view, a construction animation, and a 3D illustration under a cylindrical-fold assumption. The 3D view is explanatory and is not a reconstruction measured from multiple photographs.

## 3.5 Geometry-engine workflow

The traced curves pass through the following steps:

1. Evaluate whether the two curves share a fold and determine which is the outer boundary.
2. Cut the curves to the fold segment using their inflection limits.
3. Put the curves in a consistent direction and resample them for the engine.
4. Fit smooth curves and identify hinge points, limbs, and axial-trace geometry.
5. Match tangent directions on the two boundaries at dip angles and construct dip-isogon pairs.
6. Measure orthogonal thickness `t_alpha` and associated quantities for each pair.
7. Fit the thickness law over the engine’s angle grid and calculate `R = A/(A+B)`.
8. Classify each limb using the configured Ramsay class rules and report warnings or ambiguity.
9. Combine the per-limb outcomes into an overall result with confidence reasons.

The user-selected display angles control which measurements are drawn and shown in the table. The Ramsay classification itself uses the engine’s internal fit grid, documented as 20°–70° at 2.5° increments. The two limbs are analyzed independently.

## 3.6 Confidence, limitations, and refusal behavior

The app does not force a class when the geometry is inadequate or uncertain. It can report low confidence when limbs disagree, a bed is below the configured 90-pixel thickness criterion, a class is near a boundary, one limb cannot be fitted, or other trace or engine warnings apply. It can refuse analysis when the two lines do not define a common fold or insufficient dip-isogon matches are available.

Steep limbs are shown as an information limitation: the fit uses its documented angle range, while the synthetic validation range was narrower. The report should distinguish this information note from a rule that automatically invalidates every steep field fold.

## 3.7 Validation procedure

Validation compared app measurements on hand-traced CorelDraw boundaries with available hand-measured thickness tables. Fold 11 and Fold 3 have comparison tables in the project documentation. For each available dip angle, compare normalized thickness and report R and class. In addition, the 12 traced examples were analyzed to record per-limb class, overall outcome, confidence, and any hand comparison.

**[VERIFY]** Confirm that spreadsheet values, trace identities, and angle labels correspond before presenting the comparisons. Fold 3B requires special review because the reported app R differs substantially from the hand-table R.
