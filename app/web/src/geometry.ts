import type { Anchor } from './types'

/** SVG path data for a pen-tool path (same segment rule as app/backend/bezier.py). */
export function pathD(anchors: Anchor[]): string {
  if (anchors.length === 0) return ''
  const f = (v: number) => v.toFixed(1)
  let d = `M${f(anchors[0].p[0])},${f(anchors[0].p[1])}`
  for (let i = 1; i < anchors.length; i++) {
    const a = anchors[i - 1]
    const b = anchors[i]
    const c1 = a.out ?? a.p
    const c2 = b.in ?? b.p
    d += ` C${f(c1[0])},${f(c1[1])} ${f(c2[0])},${f(c2[1])} ${f(b.p[0])},${f(b.p[1])}`
  }
  return d
}

/** Colour of an isogon / angle chip (green pencil): olive-lime (20°) → green (45°) → deep teal-green (70°). */
export function angleColor(alpha: number): string {
  const stops: [number, [number, number, number]][] = [
    [20, [128, 160, 22]],
    [45, [52, 140, 70]],
    [70, [14, 104, 96]],
  ]
  const a = Math.min(70, Math.max(20, alpha))
  const i = a <= 45 ? 0 : 1
  const [a0, c0] = stops[i]
  const [a1, c1] = stops[i + 1]
  const t = (a - a0) / (a1 - a0)
  const c = c0.map((v, k) => Math.round(v + (c1[k] - v) * t))
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`
}

export const FIT_RANGE: [number, number] = [20, 70]
export const inFitRange = (a: number) => a >= FIT_RANGE[0] && a <= FIT_RANGE[1]
