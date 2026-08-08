# Chapter 5: Future Roadmap & Offline Mobile App Architecture

This chapter outlines the project roadmap for **Semester 2**: porting the Python geometry engine to high-performance C++20 and building an offline Flutter mobile application for field surveyors.

---

## 1. Semester 2 Overview & Goals

| Semester | Target Platform | Primary Deliverable | Core Dependency |
|---|---|---|---|
| **Semester 1 (Current)** | Python / Desktop CLI | Validated Python geometry core, synthetic test harness, debug visualizer, CLI & GUI tools | NumPy, SciPy, Matplotlib |
| **Semester 2 (Next)** | Offline iOS & Android App | Native C++20 geometry core, Flutter field mobile app, SQLite outcrop database, camera sectioning assistant | C++20, Eigen/xtensor, Flutter (Dart FFI) |

---

## 2. C++20 Core Porting Specification

`geometry.py` was strictly designed with **NumPy and SciPy ONLY** (Critical Decision 8) to ensure smooth C++ translation.

### Mapping Python Libraries to C++ Alternatives

| Python Component | C++20 Replacement | Notes |
|---|---|---|
| `numpy.ndarray` | `Eigen::VectorXd`, `Eigen::MatrixXd` | Zero-copy matrix algebra & least-squares solver |
| `scipy.interpolate.splprep` | `tinyspline` or `Eigen::Spline` | B-spline fitting and analytic evaluation |
| `scipy.linalg.lstsq` | `Eigen::HouseholderQR` | Fast linear least-squares for joint $t_0, R$ fit |
| `foldclass.geometry` API | C++ Dynamic Library (`libfoldclass.so` / `.dylib` / `.dll`) | C-ABI exported functions for FFI binding |

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
|  - Spline Fitting & Tangent Angle phi(s) Evaluation                     |
|  - Hudleston Case 1 Fixed-Point Hinge Iteration                         |
|  - Dip Isogon Extraction & Projection Bound Verification                |
|  - Joint Thickness Law Fit (A + B cos alpha) & Ramsay Classification    |
+-------------------------------------------------------------------------+
```

---

## 3. Offline Mobile App Design for Field Surveyors

Geological surveyors working in remote field traverses operate in areas without cell phone reception or internet access. The mobile app MUST run 100% offline.

### Key Mobile App Features
1. **Camera Sectioning Guide**: Built-in compass/gyroscope overlay guiding the surveyor to position the phone camera perpendicular to the fold axis (transverse profile view).
2. **Touch-Screen Boundary Tracing**: Smooth touch canvas for drawing $S_0$ and $S_1$ boundaries on field photographs with immediate visual feedback.
3. **Single-Tap Hinge Nose Seeding**: Tapping near the fold nose initializes Case 1 fixed-point iteration on device.
4. **Instant Ramsay Field Report**: Displays $R \pm \sigma_R$, fold class (1A, 1B, 1C, 2, 3), $t_0$, and interlimb angle $\theta_{il}$ within milliseconds.
5. **Offline SpatiaLite/SQLite Database**: SavesGPS coordinates, strike/dip metadata, image files, and measured $R$ values locally on device for export to GIS (QGIS/ArcGIS).

---

## 4. Future TODO List & Roadmap

### High-Priority Core Items (Immediate Next Steps)
- [ ] **Smoothing Parameter Sweep (`tools/sweep.py`)**: Implement empirical sweep of `SPLINE_SMOOTHING` $s$ across synthetic folds with varying noise levels to determine optimal smoothing threshold.
- [ ] **Boundary Perturbation Sensitivity Study (`tools/sensitivity.py`)**: Perturb traced points by $\pm 1, \pm 2, \pm 5\text{ px}$ to measure $R$ variance under hand-tracing noise and derive authoritative `MIN_LAYER_THICKNESS_PX`.
- [ ] **Fourier Shape Engine (`foldclass/src/foldclass/fourier.py`)**: Implement Stabler 3-point and Hudleston numerical integration for harmonic series coefficients ($a_1, a_3, a_5$) and plot on the $b_1-b_3$ chart.

### Stretch Goals & Advanced Research Features
- [ ] **Fourier Chart Calibration**: Calibrate `QUARTER_WAVELENGTH_B` numerically against Hatui & Chattopadhyay (2020) Figure 11c.
- [ ] **Automatic Multi-Layer Stack Strain Mapping**: Run Frangi multi-layer extraction across entire outcrop faces and produce an $R$-index strain map across successive beds.
- [ ] **3D Profile Extrusion**: Extrude 2D profile section geometry along measured fold axis plunge angle for 3D visualization.
