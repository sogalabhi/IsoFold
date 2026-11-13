# Chapter 1 — Introduction

## 1.1 Background

Structural geology studies the geometry, distribution, and origin of structures formed when rocks deform. Folds are curved or bent configurations of originally planar surfaces such as bedding or foliation. Their geometry records aspects of deformation and provides a basis for comparing structures across an exposure or region [Ghosh, 1993; verify full reference details].

Fold geometry is also relevant to engineering geology. Bedding orientation and continuity influence the characterization of rock masses and can affect the assessment of slopes, tunnels, excavations, and foundations. Because the orientation of bedding changes across a fold, the structural conditions observed on one limb may differ from those on the other.

A field photograph provides a convenient record of an outcrop, but it is a two-dimensional projection of a three-dimensional surface. Layer boundaries may be unclear because of weathering, shadows, vegetation, stains, fractures, or low contrast. Tracing the same boundary by different observers can also produce different curves. These issues make it useful to have a consistent way to digitize a bed profile and calculate its geometric properties, while keeping geological interpretation with the user.

## 1.2 Fold geometry and classification

A fold profile is commonly described using its hinge, limbs, inflection points, axial surface or its trace, and fold axis. Ramsay’s dip-isogon classification uses the relationship between layer thickness and dip angle to distinguish classes 1A, 1B, 1C, 2, and 3. The classification is based on how the thickness between folded-layer boundaries changes along the limbs [Ramsay, 1967; **VERIFY citation and edition**].

IsoFold implements the dip-isogon measurement for a pair of traced bed boundaries. For a dip angle α, it identifies points on the two boundaries whose tangents are parallel and measures the orthogonal separation. The thickness law is fitted in the form:

\[
t_\alpha = A + B\cos\alpha, \qquad R = \frac{A}{A+B}.
\]

The resulting value of R is used to assign a Ramsay class. The engine evaluates the two limbs independently because an asymmetric fold may give different measurements on each limb. Results near a class boundary or with insufficient geometric evidence are reported as ambiguous or low confidence rather than forced into a single class.

## 1.3 Problem statement

Extracting fold boundaries automatically from field photographs is challenging. Boundaries may be faint or interrupted, and image-processing methods can mistake fractures, vegetation, tools, or rock margins for bedding. At the same time, once appropriate boundary curves are available, quantitative dip-isogon measurements can be performed computationally. The project therefore addresses two related problems: the difficulty of obtaining reliable boundaries automatically from field images, and the need for an accessible tool that measures and explains fold geometry when boundaries are supplied by a user.

## 1.4 Aim

The aim of this project is to develop and evaluate a human-in-the-loop web application that allows users to trace folded-bed boundaries in outcrop photographs and classify the traced geometry using Ramsay’s dip-isogon method.

## 1.5 Objectives

1. Review the geometrical elements of folds and Ramsay’s dip-isogon classification.
2. Investigate automatic boundary-detection approaches on the available field photographs.
3. Develop an interactive application for tracing the two boundaries of one folded bed.
4. Connect the tracing interface to the frozen IsoFold geometry engine for per-limb measurement and classification.
5. Present measurements, construction steps, confidence information, and limitations in an interpretable form.
6. Compare app measurements with available hand-measured values on traced examples.
7. Identify limitations and outline future work toward automatic boundary detection.

## 1.6 Scope and limitations

The implemented application analyzes one bed at a time from two user-traced boundaries. It measures geometry in the image plane and reports apparent profile properties. It does not establish true dip, strike, or fold-axis plunge from a single photograph without additional orientation or camera information. The classification depends on the quality and suitability of the user’s traces. The application does not currently identify a bed and trace its boundaries automatically.

The geometry engine applies its own checks for insufficient data, ambiguous class boundaries, and other geometric failures. A low-confidence or refused result should be reported with its stated reasons. The current field examples and hand measurements form a limited validation set and do not establish performance across all rock types, image conditions, or fold geometries.

## 1.7 Organization of the report

Chapter 1 introduces the geological context, project problem, aim, objectives, and scope. Chapter 2 reviews fold geometry, Ramsay classification, and relevant image-analysis approaches. Chapter 3 describes the dataset, detection trials, manual-tracing application, geometry engine, and validation procedure. Chapter 4 presents the detection-trial outcomes, app validation and field-example results, limitations, and future work.
