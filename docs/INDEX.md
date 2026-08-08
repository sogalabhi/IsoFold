# Automated Ramsay Fold Classification & Geometry Core Documentation

Welcome to the comprehensive documentation for the **Automated Ramsay Classification of Folds from Field Photographs** project.

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

### [Chapter 5: Future Roadmap & Offline Mobile App](05_FUTURE_ROADMAP_AND_MOBILE_APP.md)
Semester 2 roadmap, C++ porting specification, and offline mobile app design:
- **Semester 2 C++ Geometry Port**: C++20 refactoring using `Eigen`/`xtensor` and wrapping with `pybind11` / Dart FFI.
- **Offline Flutter Mobile App**: Architecture for field surveyors (iOS/Android), on-device camera sectioning assistant, offline SQLite/SpatiaLite database for structural outcrop measurements.
- **Future TODO List & Stretch Goals**: 3D profile extrusion, automatic multi-layer stack strain mapping, Fourier F-T chart calibration against Hatui & Chattopadhyay Fig 11c.

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
├── docs/                     # Full documentation suite (Chapters 1–5)
└── Readme.md                 # Root README summary
```
