# IsoFold: Automated Ramsay Fold Classification & Geometry Core Documentation

Welcome to the comprehensive documentation for **IsoFold** (Automated Ramsay Classification of Folds from Field Photographs).

This documentation suite serves as both a **structural geology textbook guide** and a **complete software engineering manual** for measuring, classifying, and diagnosing geological folds in profile section.

---

## Master Table of Contents

### [Chapter 1: Structural Geology Textbook Fundamentals](01_GEOLOGY_FUNDAMENTALS.md)
Detailed domain theory, equations, and morphological definitions from structural geology literature (*Ramsay 1967*, *Ghosh 1993*, *Stabler 1968*, *Hudleston 1973*, *Hatui & Chattopadhyay 2020*):
- **Structural Profile Elements**: Extrados ($S_0$), Intrados ($S_1$), Axial Trace ($S_2$), Inflections, Hinges, Limbs.
- **Dip Isogon Construction**: Definition of dip isogon family $pq$, orthogonal thickness $t_\alpha$, axial plane thickness $T_\alpha$, and the projection bound trap ($t_\alpha \le |pq|$).
- **Ramsay Morphological Classes**: Class 1A, 1B (Parallel/Concentric), 1C, Class 2 (Similar), and Class 3 (Divergent).
- **Joint Thickness Fit & R-Index**: Reparameterisation $t_\alpha = A + B\cos\alpha$, joint fit of hinge thickness $t_0 = A+B$ and $R = A/(A+B)$.
- **Fourier Harmonic Shape Analysis**: Series $y = \sum a_n \sin(nx)$, Stabler 3-point method, Hudleston trapezoidal integration, $F = a_1/b$ vs $T = a_3/b$ chart, Hudleston shape letters A–F and amplitude numbers 1–5.
- **Multi-Layer Deformation**: Competent vs incompetent bed alternation, disharmony index $B(h)$.

### [Chapter 2: Technical Architecture & Critical Decisions](02_TECHNICAL_ARCHITECTURE.md)
Software engineering design, core technology stack, and methodological principles:
- **Package Stack**: Python 3.11+, NumPy, SciPy, Matplotlib, scikit-image, PyQt6, pytest.
- **8 Critical Engineering Decisions**: Curvature-free tangent formulation $\phi(s)$, joint $t_0, R$ fit, limb disambiguation, Case 1 fixed-point iteration, C++ portability.
- **Automated Synthetic Test Suite**: 8 unit test invariants in `test_geometry.py` (scaling/rotation invariance, $t_\alpha/T_\alpha = \cos\alpha$, projection bound $t_\alpha \le |pq|$, oblique distance disambiguation, prominence filtering, chevron guard, Case 2 diagnostic).
- **50-Fold Synthetic Round-Trip Verification**: 100% confusion matrix classification accuracy across all 5 Ramsay classes.

### [Chapter 3: User Guide & CLI Command Reference](03_USER_GUIDE_AND_CLI.md)
Complete user manual for interactive GUI tracing, automated CLI tools, and multi-layer analysis:
- **Interactive GUI Tracing (`tools/trace.py`)**: Step-by-step click tracing for $S_0, S_1$, and single-click hinge nose seeding.
- **CLI Command Runner (`tools/run.py`)**: Full flag reference (`--angles`, `--limb`, `--clean`, `--output`, `--smoothing`) with copy-paste terminal commands.
- **Orientation Field & Multi-Layer Extraction (`tools/orientation_isogons.py`)**: Structure tensor dip fields $\theta(x, y)$, coherence mask $C(x, y)$, and Frangi vesselness filtering.
- **Debug Pipeline (`debug.py`)**: 6-panel visual diagnostic grid.

### [Chapter 4: Codebase Architecture & API Reference](04_CODEBASE_STRUCTURE_AND_API.md)
Detailed source code walkthroughs, function signatures, data structures, and module dependencies:
- **Directory Layout**: Overview of `foldclass/src/foldclass/`, `tools/`, `data/`, and `tests/`.
- **API Specs**:
  - `config.py`: Threshold constants, provenance, and tuning parameters.
  - `geometry.py`: Core functions (`fit_arc`, `find_inflections`, `find_hinge`, `find_axial_trace`, `isogon_pairs`, `fit_thickness_law`, `case_diagnostic`, `classify`), dataclasses (`Arc`, `Line`, `IsogonPair`, `ThicknessFit`, `CaseDiagnostic`, `ClassResult`), and `GeometryError`.
  - `synthetic.py`: Analytical fold generators for Class 1B, 2, and variable $R$.
  - `debug.py`: `debug_pipeline` and 6-panel grid visualizer.
  - `plots.py`: `plot_annotated_fold` and `plot_publication_figure`.

### [Chapter 5: Multi-Phase Roadmap: C++20 Core Engine, Desktop Qt GUI & Mobile App Architecture](05_FUTURE_ROADMAP_AND_MOBILE_APP.md)
Comprehensive multi-phase roadmap across Semester 1 and Semester 2:
- **Semester 1 C++20 Engine & Desktop Qt GUI**: C++20 geometry core (`isofold-cpp` using `Eigen3` & `tinyspline`), `pybind11` Python bindings (`cpp/src/bindings.cpp`), PyQt6 desktop application (`tools/qt_app.py`), Fourier shape engine, and synthetic test harness.
- **Semester 2 Offline Flutter Mobile App**: Field app architecture (`isofold_mobile`), Dart FFI native bridge, gyroscopic camera sectioning guide, offline SQLite/SpatiaLite outcrop structural database.
- **Future TODO List & Stretch Goals**: 3D profile extrusion, automatic multi-layer stack strain mapping, Fourier F-T chart numerical calibration against Hatui & Chattopadhyay Fig 11c.

### [Chapter 6: In-Depth Mathematical Proofs & Code Walkthrough](06_IN_DEPTH_MATHEMATICAL_PROOFS_AND_CODE_WALKTHROUGH.md)
Objective mathematical proofs, line-by-line code walk, system demonstration workflow, and technical FAQ:
- **4 Formal Mathematical Proofs**: Projection bound $t_\alpha \le |pq|$, OLS joint least-squares fit & delta method $\sigma_R$, Case 1 fixed-point iteration convergence, and Case 2 offset diagnostic derivation.
- **Line-by-Line Code Explanations**: Detailed breakdown of `fit_arc`, `find_inflections`, `find_hinge`, `isogon_pairs`, `fit_thickness_law`, and `classify` in `geometry.py`.
- **System Demonstration Workflow**: Step-by-step commands for executing system demonstrations.
- **Frequently Asked Technical & Methodological Questions (FAQ)**: Pre-formulated technical Q&A.

### [Chapter 7: IsoFold Trace, the manual-tracing web app](07_ISOFOLD_TRACE_WEB_APP.md)
The web app built for the mid-project review, recorded in build order: why manual tracing, the design decisions, each build step with the problems found and fixed, validation against the hand-measured t′α and R, results on all 12 field examples, limitations, and the report figures (`figures/trace/`).

### [Engine design notes (previous README)](ENGINE_DESIGN_NOTES.md)
The original project README with the critical design decisions that the `foldclass` code comments refer to as "Readme.md".

---

## Quick Reference Cheat Sheet

### Essential CLI Commands

```bash
# 1. Activate Virtual Environment
source .venv/bin/activate

# 2. Interactive GUI Click Tracing (S0, S1, and Hinge Nose Seed)
python tools/trace.py test-fold-2.png

# 3. Standard Non-Interactive Run (Generates Publication Diagrams)
python tools/run.py test-fold-2.png

# 4. Highlight Specific Dip Angles (e.g. 20°, 40°, 60°) on Both Limbs
python tools/run.py test-fold-2.png -a 20,40,60

# 5. Clean Single-Angle View (30° on Left Limb Only, Hiding Background Lines)
python tools/run.py test-fold.png -a 30 -l left -c -o traces/test-fold_left_30deg.png

# 6. Multi-Layer Orientation Field & Frangi Ridge Detection
python tools/orientation_isogons.py test-fold-2.png

# 7. Run Automated Synthetic Test Suite
python -m pytest foldclass/tests/test_geometry.py -v
```

---

## Project Repository Layout

```
major-project/
├── foldclass/
│   ├── src/foldclass/
│   │   ├── __init__.py
│   │   ├── config.py         # All named thresholds and constants
│   │   ├── geometry.py       # NumPy + SciPy ONLY geometry engine (C++ port target)
│   │   ├── synthetic.py      # Analytical fold generators (Class 1B, 2, variable R)
│   │   ├── debug.py          # Stage-by-stage inspection pipeline & 6-panel grid
│   │   └── plots.py          # Publication-quality annotated figures & Ramsay charts
│   ├── tests/
│   │   └── test_geometry.py  # Automated synthetic test suite
│   └── pyproject.toml
├── tools/
│   ├── trace.py              # Interactive GUI click-tracing tool
│   ├── run.py                # CLI runner with angle/limb/clean options
│   └── orientation_isogons.py # Structure tensor & Frangi ridge extraction
├── traces/                   # Saved trace CSVs and output PNG figures
├── app/                      # IsoFold Trace web app (backend + web), see Chapter 7
├── docs/                     # Full documentation suite (Chapters 1–7)
└── README.md                 # IsoFold Trace: what it is, installation, usage
```
