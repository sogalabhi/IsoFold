"""Every threshold used by geometry.py / synthetic.py lives here, named,
with a comment explaining its provenance. See Readme.md, Critical
technical decisions and the config.py module spec."""

# --- R index / classification (Readme.md: "The R index") ---
ALPHA_MIN_DEG = 20.0
"""R's denominator (1 - cos alpha) -> 0 as alpha -> 0; below this the
isogon pair is too noisy to trust."""

ALPHA_MAX_DEG = 70.0
"""Tangent matching gets unreliable close to the inflection point."""

ALPHA_STEP_DEG = 2.5
"""Sampling step for the alpha sweep used to build the isogon family."""

MIN_ALPHA_SPAN_DEG = 30.0
"""Below this spread of recovered alpha values, refuse to classify — the
chevron guard (Readme.md, Critical decision 6)."""

R_AMBIGUITY_SIGMA = 2.0
"""Minimum |R - class boundary| / sigma_R required to commit to 1B or 2
rather than reporting the class as ambiguous (Critical decision 2)."""

R_MIN_AMBIGUITY_WINDOW = 0.05
"""Floor on the +/- window used to snap R to 1B or 2, applied when
R_AMBIGUITY_SIGMA * sigma_R would otherwise be smaller than this. Needed
because sigma_R can be near-zero on a clean fit (a near-perfect synthetic,
or a real fold with unusually tight scatter), which would otherwise make
classify() require R to equal the boundary to float precision instead of
"close enough" -- turning an exact Class 1B/2 synthetic into a spurious
1A/1C/3 on the strength of a rounding error."""

# --- isogon matching (Critical decision 3) ---
MAX_ISOGON_LENGTH_FACTOR = 3.0
"""Reject an isogon pair if |pq| exceeds this factor times the typical
outer-inner separation — catches matches that pass the angle test but are
geometrically implausible."""

INFLECTION_MIN_PROMINENCE_DEG = 15.0
"""A candidate inflection (sign change in dphi/ds) must show at least this
much phi swing on both sides to count as real, rather than a smoothing
wiggle. Added after the first real-photo run produced spurious inflections
that silently corrupted the reference angle -> hinge -> everything
downstream."""

# --- axial trace / Case 1 iteration (Critical decision 4) ---
AXIAL_TRACE_MAX_ITER = 20
"""Cap on the Case 1 fixed-point iteration (tangent at H and G both
perpendicular to the trial axial trace HG)."""

AXIAL_TRACE_TOL_DEG = 0.5
"""Convergence tolerance for the same iteration: stop when H and G each
move by less than this much arc-length-equivalent angle between rounds."""

CASE2_BETA_THRESHOLD_DEG = 3.0
"""Fitted axial-trace offset beta (from case_diagnostic) beyond this
magnitude is reported as Hudleston Case 2 rather than Case 1."""

# --- plausibility guards (added after the test-fold.png failure: H and G
# landed on the same limb, giving |HG| ~ 4-6x the true layer thickness and
# a fit with t0 ~ 0. These turn that class of failure into a loud one.) ---
HG_SEPARATION_RATIO_MIN = 0.5
HG_SEPARATION_RATIO_MAX = 2.0
"""|HG| must fall within [MIN, MAX] x the typical outer-inner separation.
Outside that range, H and G are not corresponding hinge points."""

T0_MIN_SEPARATION_FRACTION = 0.3
"""Fitted t0 must exceed this fraction of the typical outer-inner
separation, or the fit is dividing by noise rather than measuring a real
layer thickness."""

# --- misc ---
MIN_LAYER_THICKNESS_PX = 15.0
"""Below this, flag low confidence (derived from the boundary-perturbation
sensitivity study — see Readme.md build order step 3; placeholder until
that study is run)."""

SPLINE_SMOOTHING = None
"""Chosen by sweep.py against synthetics — not yet run. None means
callers must supply an explicit value; there is deliberately no silent
default here."""

QUARTER_WAVELENGTH_B = None
"""Fourier F-T diagram divisor convention (Ghosh: quarter wavelength =
pi/2). Not used until fourier.py exists."""
