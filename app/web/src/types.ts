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
