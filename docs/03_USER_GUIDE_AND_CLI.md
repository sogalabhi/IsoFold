# Chapter 3: User Guide & CLI Command Reference

This chapter provides a user manual for operating the interactive click-tracing GUI, executing command-line analysis tools, and using advanced dip-angle and limb filtering parameters.

---

## 1. Environment Setup

Activate the local Python virtual environment before executing any commands:

```bash
cd /home/abhijith/coding/major-project
source .venv/bin/activate
```

---

## 2. Interactive GUI Tracing (`tools/trace.py`)

The interactive click-tracing GUI allows you to digitize layer boundaries directly on outcrop photographs and automatically save coordinates to CSV.

### Execution Command
```bash
python tools/trace.py test-fold-2.png
```

```
+-------------------------------------------------------------------------+
|                  INTERACTIVE FOLD TRACING WORKFLOW                      |
|                                                                         |
|  Step 1: Click Outer Boundary (S0 - Extrados)                           |
|          - Left-click points along the outer curve                      |
|          - Right-click to undo a point                                  |
|          - Press ENTER to finish (Saves traces/test-fold-2_outer.csv)   |
|                                                                         |
|  Step 2: Click Inner Boundary (S1 - Intrados)                           |
|          - Left-click points along the inner curve in same direction   |
|          - Press ENTER to finish (Saves traces/test-fold-2_inner.csv)   |
|                                                                         |
|  Step 3: Click Hinge Seed (1 Click near Fold Nose Apex)                 |
|          - Click 1 point near the top/bottom central arch closure      |
|          - Press ENTER to run automatic geometry pipeline               |
+-------------------------------------------------------------------------+
```

---

## 3. Command-Line Runner (`tools/run.py`)

The CLI runner processes saved CSV traces or raw fold images with customizable visual parameters.

### Command Syntax
```bash
python tools/run.py <IMAGE_PATH> [FLAGS]
```

### Full Flag Reference Table

| Flag | Short | Description | Allowed Values | Default |
|---|---|---|---|---|
| `--angles` | `-a` | Specific dip angles to highlight and label | Comma-separated floats (e.g. `20,40,60` or `30`) | Default Range ($20^\circ-70^\circ$) |
| `--limb` | `-l` | Filter analysis to specific limb | `left`, `right`, `both` | `both` |
| `--clean` | `-c` | Hide non-selected background isogons to prevent visual congestion | Boolean flag | `False` (Show all) |
| `--output` | `-o` | Custom output path for annotated diagram | File path string | `traces/<stem>_annotated.png` |
| `--output-dir` | — | Directory for saved CSVs and output diagrams | Path string | `traces` |
| `--smoothing` | — | Explicit spline smoothing factor $s$ | Float | `len(pts) * 10.0` |

---

## 4. Copy-Paste CLI Examples

### Example A: Basic Analysis & Multi-Panel Journal Figure
```bash
python tools/run.py test-fold.png
```
*Outputs `traces/test-fold_publication.png` and `traces/test-fold_annotated.png`.*

### Example B: Highlight Dip Angles (20°, 40°, 60°) on Both Limbs
```bash
python tools/run.py test-fold-2.png -a 20,40,60
```
*Highlights $20^\circ, 40^\circ, 60^\circ$ isogons in distinct colors with angle labels.*

### Example C: Clean Single-Angle View (30° on Left Limb Only)
```bash
python tools/run.py test-fold.png -a 30 -l left -c -o traces/test-fold_left_30deg.png
```
*Hides all background lines, showing only the $30^\circ$ dip isogon on the left limb.*

### Example D: Clean View (20°, 40°, 60° on Right Limb Only)
```bash
python tools/run.py test-fold-2.png -a 20,40,60 -l right -c -o traces/test-fold-2_right_angles.png
```

---

## 5. Multi-Layer Orientation Field & Frangi Extraction (`tools/orientation_isogons.py`)

Extracts continuous orientation fields and detects multi-layer bedding ridges automatically.

### Execution Command
```bash
python tools/orientation_isogons.py test-fold-2.png --min-coherence 0.2 --output orientation_isogons_test2.png
```

### Generated Output Panels
1. **Multi-Layer Bedding Skeleton**: Frangi vesselness filter skeletonizing all bedding centerlines.
2. **Orientation Field $\theta(x, y)$**: Local bedding orientation in HSV color space.
3. **Coherence Mask $C(x, y)$**: Structure tensor directional confidence mask.
4. **Continuous Dip Isogons**: Iso-contours $\theta(x, y) = \alpha$ drawn across the entire multi-layer stack.
