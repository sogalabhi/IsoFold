# Chapter 4 — Results and Discussion

## 4.1 Automatic-detection trial results

### 4.1.1 Classical edge tracing

The classical detector found a usable pair of bed boundaries on 2 of 26 field photographs. This result showed that classical image-processing could identify useful candidates in some images but was not reliable enough to serve as the only input method for the project’s field-photo set. Boundary contrast, occlusion, competing linear features, and the challenge of pairing two boundaries from the same bed limited the workflow.

### 4.1.2 Pretrained SAM

Pretrained SAM did not isolate one bed in the documented trials. Automatic segmentation selected visually distinct objects such as tools or vegetation, and prompted segmentation did not consistently separate the target bed from the surrounding rock or adjacent beds. SAM therefore did not remove the need for a user to identify and trace the target boundaries.

These experiments are important project results: they informed the design choice to build a manual-tracing application around the available geometry engine. They do not show that all automatic methods are ineffective; they show that the investigated methods and configurations did not meet the single-bed boundary requirement on this dataset.

**[VERIFY]** Add example images or a compact results table for representative successes and failures if the source images and captions can be identified.

## 4.2 Agreement with hand measurements

### 4.2.1 Fold 11

For Fold 11 (Shear Zone; hand table Fold-2A), the hand-measured value was `R = 0.186`, corresponding to class 1C. The app returned `R = 0.186` on the left limb and `R = 0.152` on the right limb; both limbs were classified as 1C. The app’s normalized thickness values were close to the hand measurements at the compared angles:

| Dip angle | Hand `t′_alpha` | App left limb | App right limb |
|---:|---:|---:|---:|
| 30° | 0.879 | 0.892 | 0.888 |
| 45° | 0.751 | 0.759 | 0.746 |
| 60° | 0.577 | 0.591 | 0.573 |
| 70° | 0.462 | 0.473 | 0.454 |

The comparison indicates close agreement for this traced example. It should not be generalized to all field images because the boundaries supplied to the app were already traced by hand.

### 4.2.2 Fold 3

For Fold 3 (IMG_20180211_145755; hand table Fold-3A), the hand value was `R = 0.224`, class 1C. The app returned `R = 0.223` and `R = 0.164` for the two limbs; both limbs remained class 1C. The comparison supports agreement in class for this example, although the limb estimates differ and should be presented rather than averaged away.

### 4.2.3 Fold 3B discrepancy

The documentation reports app values of approximately `R = 0.800` and `R = 0.463` for Fold 3B, with an overall value near 0.632, compared with a hand-table value near 0.084. The class is reported as 1C in both sources, but the R values differ substantially. The hand table contains an unusual normalized-thickness entry at about 52°, and the trace and table require rechecking. Until resolved, do not use Fold 3B as evidence of numerical agreement. If retained in the overall dataset results, state the discrepancy explicitly.

## 4.3 Results on the 12 field examples

The development record reports 9 of 12 examples as confident and 3 as low confidence. The low-confidence cases had specific causes: Folds 13 and 16B were near the 1C/2 class boundary and their limbs fell on opposite sides of it; Fold 15B was an 82-pixel bed, below the configured 90-pixel criterion, and was sensitive to trace direction.

| Example | Reported limb/overall result | Verdict | Discussion |
|---|---|---|---|
| Fold 11 | 1C / 1C; overall 1C, R ≈ 0.169 | Confident | Hand R = 0.186; left-limb app R agrees with hand value |
| Fold 3 | 1C / 1C; overall 1C, R ≈ 0.194 | Confident | Hand R = 0.224; class agrees |
| Fold 3B | 1C / 1C; overall 1C, R ≈ 0.632 | Reported confident | Large discrepancy with hand R ≈ 0.084; recheck before relying on it |
| Fold 17A | 1C / 1C; overall 1C, R ≈ 0.198 | Confident | No hand R available in current table |
| Fold 14 | 1C / 1C; overall 1C, R ≈ 0.239 | Confident | Hinge sensitivity noted in development record |
| Fold 13 | 2 / 1C; overall near boundary | Low confidence | Limbs disagree near 1C/2 boundary |
| Fold 12 | 1C / 1C; overall R ≈ 0.524 | Confident | No hand R available in current table |
| Fold 9 | 1C / 1C; overall R ≈ 0.340 | Confident | No hand R available in current table |
| Fold 15A | 2 / 2; overall R ≈ −0.001 | Confident | No hand R available in current table |
| Fold 15B | 3 / 1C; overall ambiguous | Low confidence | Bed thickness 82 px; trace sensitivity |
| Fold 16A | 1C / 1C; overall R ≈ 0.131 | Confident | No hand R available in current table |
| Fold 16B | 1C / 2; overall near boundary | Low confidence | Limbs disagree near 1C/2 boundary |

**[VERIFY]** Re-run or inspect the app results and example metadata before treating this summary table as final. In particular, confirm Fold 3B’s verdict and exact R values; the app-level text may now differ from the chapter development snapshot.

## 4.4 Interpretation

The hand-measurement comparisons support the geometry engine’s ability to reproduce Ramsay measurements when the bed boundaries are supplied as hand traces. The field-example results also show the value of reporting each limb and its confidence rather than hiding disagreement in a single average. However, these results validate the measurement stage on selected traces; they do not validate fully automatic fold detection from photographs.

The automatic trials and manual-app results address different parts of the larger task. The detector trials assessed whether candidate boundaries could be found from raw photographs. The manual app evaluates the downstream geometric analysis after a user supplies appropriate boundaries. Keeping these claims separate avoids overstating the current system’s automation.

## 4.5 Limitations

- Boundary placement remains dependent on the user and can affect the fitted hinge and R value, especially around tight noses.
- Small trace perturbations were reported to shift R by approximately 0.01–0.04 in sensitive cases, although the class did not change in those noted cases.
- Automatic edge tracing and pretrained SAM did not reliably isolate one bed in the available photo set.
- Only a limited number of examples have corresponding hand-measured tables.
- Most field folds have steep limbs, while the synthetic validation range was narrower; additional validation is needed.
- A single photograph provides image-plane geometry and cannot by itself determine all true three-dimensional structural orientations.
- The Fold 3B app/hand discrepancy remains unresolved.

## 4.6 Future work

Future work includes improving automatic boundary detection and bed pairing, using verified manual traces as labels for a trained segmentation model, expanding validation against independent hand measurements, quantifying trace sensitivity, and improving export and measurement tools. These are proposed next steps and should not be described as completed features.
