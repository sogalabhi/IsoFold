# References

> Rebuild this list after the final text and citations are settled. Verify author names, titles, publication details, pages, and DOI/URL against the original sources. Alphabetize by first author if that remains the department requirement.

- Ghosh, S. K. (1993). *Structural Geology: Fundamentals and Modern Developments*. Pergamon Press. **[Verify edition and cited page references.]**
- Ramsay, J. G. (1967). *Folding and Fracturing of Rocks*. McGraw-Hill. **[Verify publication details and exact pages.]**
- He, K., Zhang, X., Ren, S., & Sun, J. (2016). “Deep Residual Learning for Image Recognition.” CVPR. **[Retain only if the final text discusses ResNet as background/future work.]**
- Ronneberger, O., Fischer, P., & Brox, T. (2015). “U-Net: Convolutional Networks for Biomedical Image Segmentation.” MICCAI. **[Retain only if relevant to background/future work.]**
- Zhang, T. Y., & Suen, C. Y. (1984). “A Fast Parallel Algorithm for Thinning Digital Patterns.” *Communications of the ACM*, 27(3), 236–239. **[Retain only if thinning is discussed as related work, not as implemented method.]**
- Zuiderveld, K. (1994). “Contrast Limited Adaptive Histogram Equalization.” In *Graphics Gems IV*. **[Retain only if CLAHE is discussed as part of the actual detection trial; verify full details.]**
- **[Add verified primary reference(s) for Segment Anything if the SAM experiment is described in detail.]**
- **[Add verified source(s) for any other computer-vision or geological methods discussed.]**

# Figures and tables to prepare

The repository already contains 14 current-app screenshots under `IsoFold/docs/figures/trace/`. They are not all needed in the main report. Use a small, readable selection in Chapters 3–4 and keep the rest as supporting material unless the team specifically wants a full interface gallery.

## Recommended report screenshots

| Report placement | Screenshot asset | Suggested caption / purpose | Action |
|---|---|---|---|
| Chapter 3, interface | `01_welcome.jpg` | IsoFold Trace welcome screen and field-example gallery | Include if introducing the app |
| Chapter 3, tracing method | `02_pen_tracing.jpg` | Manual tracing of the outer and inner boundaries using the pen tool | Include |
| Chapter 4, primary result | `03_fold11_result.jpg` | Fold 11 tracing, dip-isogon overlay, and Ramsay class result | Include; main system result figure |
| Chapter 4, construction | `08_construction_isogon.jpg` **or** `09_construction_reveal.jpg` | Example step from the dip-isogon construction animation | Choose one; these are adjacent animation states |
| Chapter 4, worked calculation | `10_worked_sheet_table.jpg` **or** `11_worked_sheet_R_and_class.jpg` | Worked measurement table or R/class calculation | Choose the clearer one; both together may be redundant |
| Chapter 4, low-confidence behavior | `14_fold13_low_confidence.jpg` | Example of a 2/1C boundary result reported with low confidence | Include to show uncertainty handling |
| Chapter 3 or 4, optional | `13_3d_view.jpg` | Cylindrical-fold 3D illustration | Include only if the report discusses this explanatory feature and labels the assumption |

`04_fold11_hinge_labels.jpg` can replace or supplement the primary result if the hinge labels are discussed in detail. `06_construction_hinge.jpg` and `07_construction_turn_ruler.jpg` are earlier states of the same animation; `12_help_R.jpg` is an optional UI detail. `05_results_panel.jpg` is unusually narrow (380 × 1660 px) and will become too small if fitted to a normal portrait page. Recapture it at a wider viewport or crop a relevant section; do not stretch it.

## Screenshot handling rules

- Preserve each image's aspect ratio. Never set an independent width and height that distorts the screenshot.
- Fit landscape screenshots within the text area. Most are 1440 × 900 px and fit a normal report page at about 6 inches wide.
- Keep text and chart labels readable at final print size. If a screenshot is unreadable when scaled to page width, recapture at a better viewport, crop to the relevant panel, or omit it.
- Add a concise caption that explains the evidence shown. Do not caption UI screenshots as validation unless they show measured results.
- Prefer placing figures next to the method/result they support rather than placing every screenshot in an appendix.
- The 14 screenshots are evidence assets, not 14 mandatory report figures.

## Other figures and tables to prepare

1. Fold geometry schematic with hinge, limbs, inflections, axial trace, and dip-isogon elements; identify whether author-drawn or adapted and cite accordingly.
2. A compact automatic-detection trial figure with representative classical-tracing and SAM outcomes, only if source images and captions can be documented. Existing older experiment images are in `IsoFold_UI_handoff/results/` and `IsoFold/app/backend/samples/`; verify what each depicts before use. No clearly identified SAM comparison screenshot set has yet been found.
3. Table comparing hand and app normalized-thickness values for Fold 11 and Fold 3.
4. Summary table for all 12 examples with left/right limb class, R, verdict, and confidence reason; verify exact outputs before finalizing.
5. Optional table summarizing the two automatic-detection trials, their evaluation criteria, and outcomes. Avoid implying a statistically broad benchmark from these exploratory trials.
6. Avoid the current Figure 1.5 U-Net pipeline unless explicitly relabeled as **proposed future work**.

# Final verification checklist

- [ ] Confirm title, students, roll numbers, guide name/title, and submission date.
- [ ] Confirm whether abstract length and keywords are specified by CV449.
- [ ] Verify dataset counts and example identities from the manifest and trace index.
- [ ] Verify the 2/26 detector result and trial definition against experiment records.
- [ ] Verify SAM setup and use only supported observations.
- [ ] Recheck Fold 3B’s trace, hand table, and current app result.
- [ ] Verify the Fold 11 and Fold 3 values against source spreadsheets.
- [ ] Resolve or remove the Figure 1.4 source placeholder.
- [ ] Check every in-text citation against the reference list and original sources.
- [ ] Generate the contents, figure list, and table list from the final document.
