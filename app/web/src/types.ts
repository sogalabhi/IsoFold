// Shapes shared with the Python API (app/backend/api.py, manual.py). Coordinates are image pixels.

export type Pt = [number, number]

/** One pen-tool anchor: the point and its two Bézier handles (null = handle sits on the point). */
export interface Anchor {
  p: Pt
  in: Pt | null
  out: Pt | null
}

export type LineKey = 'outer' | 'inner'
export type Paths = Record<LineKey, Anchor[]>

export interface HandMeasurement {
  label: string
  R: number
  fold_class: string
  angles: number[]
  t_prime: number[]
}

export interface Example {
  name: string
  title: string
  locality: string
  source: string
  photo_size: [number, number]
  hand: HandMeasurement | null
  thumb_url: string
  photo_url: string
}

export interface ExampleDetail extends Example {
  outer: { anchors: Anchor[] }
  inner: { anchors: Anchor[] }
}

/** The photo being worked on: a local file (object URL) or an example served by the API. */
export interface Doc {
  name: string
  url: string
  width: number
  height: number
  example: Example | null
}

export interface Health {
  ok: boolean
  engine: string
  examples: boolean
}

// ---- result of POST /api/classify (app/backend/manual.py classify) ----

export type Limb = 'left' | 'right'

export interface Isogon {
  limb: Limb
  alpha: number
  p: Pt // on the outer line
  q: Pt // on the inner line
  foot: Pt // q dropped onto the outer tangent at p: t_alpha = |q - foot|
  tan_p: Pt
  tan_q: Pt
  t_px: number
  t_prime: number | null
  in_fit_range: boolean
}

export interface LimbResult {
  fitted: boolean
  fold_class: string | null
  R: number | null
  sigma_R: number | null
  t0_px: number | null
  alpha_span_deg: number | null
  n_isogons: number
  max_dip_deg: number | null
  warnings: string[]
}

export interface Result {
  verdict: 'confident' | 'low_confidence' | 'refused'
  reasons: string[]
  notes: string[]
  engine_error: string | null
  swapped: boolean
  overall: { fold_class: string | null; R: number | null; sigma_R: number | null } | null
  limbs: Partial<Record<Limb, LimbResult>>
  hinge: { H: Pt; G: Pt; hg_px: number; tan_H: Pt; tan_G: Pt; axial_trace: { point: Pt; dir: Pt } } | null
  cut: { outer: Pt[]; inner: Pt[] } | null
  isogons: Isogon[]
  missing: { limb: Limb; alpha: number; why: string }[]
  chart: Partial<Record<Limb, { points: [number, number][]; fit: { R: number; t0_px: number } }>>
  engine: string
  timings_ms: Record<string, number>
}
