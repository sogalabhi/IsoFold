// "Show construction": the hand method replayed step by step from the engine's own measurement
// (plan.md 4.12). This file only builds the timeline; ConstructionOverlay draws a frame of it.
import type { Isogon, Pt, Result } from './types'
import { inFitRange } from './geometry'

export type StepKind = 'hinge' | 't0' | 'turn' | 'outer' | 'inner' | 'isogon' | 'plot' | 'fit'

export interface CStep {
  kind: StepKind
  dur: number // ms at 1x speed
  caption: string
  iso?: Isogon
  order?: number // which isogon (0, 1, …) this step belongs to
}

export interface Timeline {
  steps: CStep[]
  starts: number[] // start time of each step
  total: number
  isogons: Isogon[] // in the order they are constructed
  t0: number // hinge thickness |G - foot of G on the tangent at H|
}

export interface Frame {
  i: number // current step
  u: number // progress through it, 0..1
}

const sub = (a: Pt, b: Pt): Pt => [a[0] - b[0], a[1] - b[1]]
const dot = (a: Pt, b: Pt) => a[0] * b[0] + a[1] * b[1]

/** Foot of the perpendicular from G onto the tangent line at H. */
export function hingeFoot(result: Result): Pt {
  const { H, G, tan_H } = result.hinge!
  const s = dot(sub(G, H), tan_H)
  return [H[0] + s * tan_H[0], H[1] + s * tan_H[1]]
}

export const isoKey = (i: Isogon) => `${i.limb}-${i.alpha}`

export function buildTimeline(result: Result, angles: number[]): Timeline {
  const steps: CStep[] = []
  const foot = hingeFoot(result)
  const t0 = Math.hypot(...sub(result.hinge!.G, foot))

  steps.push({
    kind: 'hinge',
    dur: 3000,
    caption: "Find the hinge: the point on each edge where the bed's tangent is perpendicular to the axial trace (H on the outer edge, G on the inner).",
  })
  steps.push({ kind: 't0', dur: 2400, caption: `t₀ = ${t0.toFixed(0)} px: the bed's thickness at the hinge, measured between the two parallel tangents.` })

  // left limb first, then right; only angles inside the fit range (the ones that build R)
  const chosen = [...angles].filter(inFitRange).sort((a, b) => a - b)
  const isogons: Isogon[] = []
  for (const limb of ['left', 'right'] as const)
    for (const a of chosen) {
      const iso = result.isogons.find((i) => i.limb === limb && i.alpha === a)
      if (iso) isogons.push(iso)
    }

  isogons.forEach((iso, order) => {
    const f = order === 0 ? 1 : order === 1 ? 0.7 : 0.45 // the first one slowly, later ones quicker
    const side = iso.limb === 'left' ? 'left' : 'right'
    steps.push({ kind: 'turn', dur: 1800 * f, iso, order, caption: `Turn the ruler to α = ${iso.alpha}° from the hinge tangent (${side} limb).` })
    steps.push({ kind: 'outer', dur: 1600 * f, iso, order, caption: `Slide it, keeping the angle, until it just touches the outer edge: that point is p.` })
    steps.push({ kind: 'inner', dur: 1600 * f, iso, order, caption: `Slide a parallel copy across until it touches the inner edge: that point is q.` })
    steps.push({
      kind: 'isogon',
      dur: 2200 * f,
      iso,
      order,
      caption: `Join p and q: the dip isogon for ${iso.alpha}°. t_α = ${iso.t_px.toFixed(0)} px is the gap between the two parallel tangents.`,
    })
    steps.push({
      kind: 'plot',
      dur: 1500 * f,
      iso,
      order,
      caption: `t′ = t_α / t₀ = ${iso.t_prime?.toFixed(2) ?? '–'} at ${iso.alpha}°: one point on the Ramsay diagram.`,
    })
  })

  const o = result.overall
  const cls = o?.fold_class
  steps.push({
    kind: 'fit',
    dur: 3800,
    caption: cls
      ? `The engine repeats this every 2.5° from 20° to 70° and fits t′ = R + (1 − R) cos α: R = ${o!.R?.toFixed(2)} → Class ${cls}.`
      : `The engine repeats this every 2.5° from 20° to 70° and fits t′ = R + (1 − R) cos α on each limb: the limbs fall in different classes.`,
  })

  const starts: number[] = []
  let t = 0
  for (const s of steps) {
    starts.push(t)
    t += s.dur
  }
  return { steps, starts, total: t, isogons, t0 }
}

export function frameAt(tl: Timeline, t: number): Frame {
  let i = tl.starts.length - 1
  while (i > 0 && tl.starts[i] > t) i--
  return { i, u: Math.min(1, Math.max(0, (t - tl.starts[i]) / tl.steps[i].dur)) }
}

export const ease = (u: number) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2)
/** Progress of a sub-interval [a, b] of a step, eased. */
export const span = (u: number, a: number, b: number) => ease(Math.min(1, Math.max(0, (u - a) / (b - a))))
