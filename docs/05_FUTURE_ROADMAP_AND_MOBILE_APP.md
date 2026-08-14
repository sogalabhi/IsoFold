# Chapter 5: Multi-Phase Roadmap: C++20 Core Engine, Desktop Qt GUI & Mobile App Architecture

This chapter outlines the comprehensive execution roadmap across **Semester 1** and **Semester 2**. Semester 1 delivers the Python baseline, native C++20 geometry core backend (`isofold-cpp`), `pybind11` Python bindings, Fourier shape engine, and a desktop PyQt6 GUI. Semester 2 expands IsoFold into an offline Flutter mobile application for field surveyors.

---

## 1. Multi-Phase Execution Overview & Goals

| Semester | Target Platform | Primary Deliverables | Core Dependencies & Tech Stack |
|---|---|---|---|
| **Semester 1 (Current)** | Python + C++20 / Desktop (Laptop) | • Validated Python geometry core & 50-fold synthetic test harness<br>• **Native C++20 Geometry Core Engine (`cpp/` / `isofold-cpp`)**<br>• **`pybind11` C++ Python Bindings (`cpp/src/bindings.cpp`)**<br>• **Desktop Qt GUI Application (`tools/qt_app.py`)** with point-clicking & live overlays<br>• **Fourier Shape Engine ($a_1, a_3, a_5$) & Hudleston $b_1–b_3$ shape chart** | C++20, Eigen3, tinyspline, pybind11, CMake, Python 3.11+, NumPy, SciPy, PyQt6 |
| **Semester 2 (Next)** | Offline Field Mobile (iOS & Android) | • **Flutter Field Mobile App (`isofold_mobile`)**<br>• **Dart FFI Direct Binding to Native `isofold-cpp` Core**<br>• **Offline SQLite / SpatiaLite Outcrop Structural Database**<br>• **Gyroscopic Camera Sectioning Guide Overlay** | Flutter (Dart FFI), C++20 Dynamic Library (`libfoldclass.so`/`.dylib`/`.dll`), SQLite/SpatiaLite |

---

## 2. Semester 1 Architecture: C++20 Core Engine & Desktop Qt GUI

```
                                [DESKTOP QT GUI (PyQt6 / Qt6)]
                                  - Image viewer & interactive point clicker
                                  - Real-time S0 / S1 boundary overlay
                                  - Ramsay Class & Fourier results panel
                                                │
                                                ▼
                                    [PYTHON / PYBIND11 WRAPPER]
                                                │
                                                ▼
                                    [C++20 GEOMETRY CORE ENGINE]
                                      - Eigen matrix linear algebra & least-squares
                                      - tinyspline B-spline derivatives φ(s)
                                      - Hudleston Case 1 fixed-point hinge iteration
                                      - Joint thickness law fit (t_α = A + B cos α)
```

### 2.1 C++20 Engine Structure (`cpp/`)

`geometry.py` was strictly designed with **NumPy and SciPy ONLY** (Critical Decision 8) to ensure 1:1 translation into C++20.

```
cpp/
├── CMakeLists.txt              # CMake build setup linking Eigen3, tinyspline, pybind11
├── include/
│   └── isofold/
│       └── geometry.hpp        # C++ data structures (Arc, Line, IsogonPair, ThicknessFit, ClassResult)
└── src/
    ├── geometry.cpp            # C++ implementation of spline fitting, hinge iteration, OLS fit
    └── bindings.cpp            # pybind11 module bindings for Python integration
```

### 2.2 Mapping Python Core to C++20 Replacements

| Python Component | C++20 Replacement | Engineering Purpose |
|---|---|---|
| `numpy.ndarray` | `Eigen::VectorXd`, `Eigen::MatrixXd` | Zero-copy vector & matrix operations |
| `scipy.interpolate.splprep` | `tinyspline` or `Eigen::Spline` | Spline fitting & analytic derivative $\phi(s) = \arctan2(dy/du, dx/du)$ |
| `scipy.linalg.lstsq` | `Eigen::HouseholderQR` | Linear least-squares solver for joint $t_0, R$ fit ($t_\alpha = A + B\cos\alpha$) |
| `foldclass.geometry` API | C++ Dynamic Library (`isofold-cpp`) | Shared engine compiled with pybind11 / C-ABI exports |

### 2.3 Desktop Qt GUI Application (`tools/qt_app.py`)

The Semester 1 desktop app is built with PyQt6 for laptop field/lab use:
- **Interactive Point Clicker**: Click extrados $S_0$ and intrados $S_1$ boundaries on outcrop photos.
- **Single-Tap Hinge Seeding**: Click near the fold nose to initialize Case 1 fixed-point iteration ($H, G$).
- **Live Angle & Limb Controls**: Adjust dip angle sliders ($20^\circ, 40^\circ, 60^\circ$), toggle left/right/both limbs, and switch to clean view.
- **Dual Display & Export**: Outcrop overlay panel + Ramsay $t'_\alpha - \alpha$ field plot with single-click PNG/PDF publication export.

---

## 3. Semester 2 Roadmap: Offline Mobile App Design (`isofold_mobile`)

Geological surveyors working in remote field traverses operate without cell phone reception or internet access. The mobile app MUST run 100% offline.

### Dart FFI Binding Layer Architecture

```
+-------------------------------------------------------------------------+
|                        FLUTTER MOBILE APP (DART)                        |
|                                                                         |
|  - Outcrop Camera View Finder & Sectioning Guide                        |
|  - Interactive Touch Screen Boundary Tracing Canvas                     |
|  - Local Offline Outcrop SpatiaLite/SQLite Database                     |
+-------------------------------------------------------------------------+
                                    |
                         Dart FFI C-Bridge Interface
                                    |
+-------------------------------------------------------------------------+
|                       NATIVE C++20 GEOMETRY CORE                        |
|                                                                         |
|  - Spline Fitting & Tangent Angle φ(s) Evaluation                       |
|  - Hudleston Case 1 Fixed-Point Hinge Iteration                         |
|  - Dip Isogon Extraction & Projection Bound Verification                |
|  - Joint Thickness Law Fit (A + B cos α) & Ramsay Classification        |
+-------------------------------------------------------------------------+
```

### Key Mobile App Features
1. **Camera Sectioning Guide**: Built-in compass/gyroscope overlay guiding the surveyor to position the phone camera perpendicular to the fold axis (transverse profile view).
2. **Touch-Screen Boundary Tracing**: Smooth touch canvas for drawing $S_0$ and $S_1$ boundaries on field photographs with immediate visual feedback.
3. **Single-Tap Hinge Nose Seeding**: Tapping near the fold nose initializes Case 1 fixed-point iteration on device.
4. **Instant Ramsay Field Report**: Displays $R \pm \sigma_R$, fold class (1A, 1B, 1C, 2, 3), $t_0$, and interlimb angle $\theta_{il}$ within milliseconds.
5. **Offline SpatiaLite/SQLite Database**: Saves GPS coordinates, strike/dip metadata, image files, and measured $R$ values locally on device for export to GIS (QGIS/ArcGIS).

---

## 4. Work Breakdown & Implementation TODO List

### Semester 1 High-Priority Deliverables (Current)
- [ ] **C++20 Geometry Core (`cpp/`)**: Implement `geometry.hpp`, `geometry.cpp`, and `CMakeLists.txt` using Eigen3 & tinyspline.
- [ ] **`pybind11` Bindings (`cpp/src/bindings.cpp`)**: Build C++ Python extension module and verify dual C++/Python unit test pass.
- [ ] **Desktop Qt GUI (`tools/qt_app.py`)**: Build PyQt6 laptop GUI with interactive point clicker, live isogon overlays, and Ramsay plot export.
- [ ] **Fourier Shape Engine (`foldclass/src/foldclass/fourier.py`)**: Implement Stabler 3-point and Hudleston trapezoidal numerical integration for harmonic series coefficients ($a_1, a_3, a_5$) and $b_1-b_3$ chart classification.
- [ ] **Smoothing Parameter Sweep (`tools/sweep.py`)**: Implement empirical sweep of `SPLINE_SMOOTHING` $s$ across synthetic folds with varying noise levels.
- [ ] **Boundary Perturbation Sensitivity Study (`tools/sensitivity.py`)**: Perturb traced points by $\pm 1, \pm 2, \pm 5\text{ px}$ to measure $R$ variance under hand-tracing noise.

### Semester 2 Mobile & Advanced Research Items
- [ ] **Flutter Field App (`isofold_mobile`)**: Create Flutter project with touch drawing canvas and Dart FFI bindings.
- [ ] **Fourier Chart Calibration**: Calibrate `QUARTER_WAVELENGTH_B` numerically against Hatui & Chattopadhyay (2020) Figure 11c.
- [ ] **Automatic Multi-Layer Stack Strain Mapping**: Run Frangi multi-layer extraction across entire outcrop faces and produce an $R$-index strain map across successive beds.
- [ ] **3D Profile Extrusion**: Extrude 2D profile section geometry along measured fold axis plunge angle for 3D visualization.

