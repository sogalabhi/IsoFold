# Identification of Folds Using Ramsay Dip-Isogon Analysis

**Major Project-I (CV449) — report content draft**

> Drafting note: This file is a content draft, not a formatted final report. It is based on the current report, the IsoFold repository documentation, and the project handoffs. Items marked **[VERIFY]** or **[TEAM INPUT]** need confirmation before submission. Do not present proposed deep-learning work as completed work.

## Title-page details

**Project title:** Identification of Folds Using Ramsay Dip-Isogon Analysis  
**Students:** Abhijith Sogal V (231CV203); Priyal Neekhra (231CV239); Vidya S.J (231CV155)  
**Guide:** Kalyan Brata Hatui **[VERIFY approved designation/title]**  
**Department:** Department of Civil Engineering, National Institute of Technology Karnataka, Surathkal  
**Submission date:** November 2026 **[VERIFY]**

## Declaration and certificate

Use the department-approved wording from the CV449 template. Confirm the students’ names/order, the project title, and the guide’s exact designation. Do not use the uncorrected wording from the current export without review.

## Acknowledgement

**[TEAM INPUT: Add only acknowledgements the team approves, including names and designations.]**

## Abstract

Fold geometry is important in structural and engineering geology, but identifying and measuring folded layers from outcrop photographs is difficult. Manual interpretation takes time and may vary between observers, while automatic boundary detection can fail when beds have weak contrast, weathering, shadows, vegetation, or complex fold shapes. This project developed IsoFold Trace, a local web application that lets a user trace the inner and outer boundaries of one folded bed and then analyzes the traced geometry using Ramsay’s dip-isogon method.

The application uses an interactive React and TypeScript interface with a local Python and FastAPI backend. Traced curves are passed to a frozen geometry engine, which prepares the fold profile, matches points with parallel tangents at selected dip angles, measures normalized layer thickness, fits the thickness law, and estimates the Ramsay class independently for the two limbs. The interface displays the traced bed, dip isogons, measurements, class results, confidence information, a worked calculation, and a construction animation.

Two automatic-detection approaches were investigated on 26 field photographs. Classical image-processing and edge-tracing methods found a usable pair of bed boundaries on 2 photographs. Pretrained Segment Anything (SAM) did not isolate a single bed in the trials. These results motivated the human-in-the-loop design. On 12 hand-traced field examples, 9 were reported as confident and 3 as low confidence. For Fold 11, the app’s left-limb value of R = 0.186 matched the hand-measured value of 0.186; measured normalized thicknesses were also close at the compared angles. Fold 3 showed agreement in class, while a discrepancy for Fold 3B remains to be checked. The application therefore demonstrates repeatable geometric analysis when suitable boundaries are supplied, while automatic boundary extraction remains future work.

**Keywords:** geological folds; Ramsay classification; dip isogons; fold geometry; image analysis; human-in-the-loop application

> **Abstract checks:** Verify the 26-photo and 12-example counts, the 9/3 confidence summary, and Fold 11 values against the final experiment outputs. Add or remove keywords according to department requirements.
