// Text labels on the photo (image px; k = image px per screen px). Labels are placed in priority order and a
// label that would overlap one already placed is left out, so zooming in (more room) brings more of them back.
import type { Pt } from '../types'

export interface LabelItem {
  key: string
  text: string
  anchor: Pt // the point being labelled
  dir: Pt // unit vector: the label sits this way from the anchor
  gap?: number // screen px between anchor and label edge (default 12)
  priority: number // lower = placed first
  color?: string // border colour
  strong?: boolean // filled dark tag (hinge points)
}

export interface PlacedLabel extends LabelItem {
  at: Pt
  w: number
  h: number
}

export function layoutLabels(items: LabelItem[], k: number, avoid: Pt[] = []): PlacedLabel[] {
  const boxes: [number, number, number, number][] = avoid.map((p) => [p[0] - 7 * k, p[1] - 7 * k, p[0] + 7 * k, p[1] + 7 * k])
  const out: PlacedLabel[] = []
  const order = items.map((it, i) => [it, i] as const).sort((a, b) => a[0].priority - b[0].priority || a[1] - b[1])
  for (const [it] of order) {
    const w = (it.text.length * 7.1 + 12) * k
    const h = 18 * k
    // distance from the anchor to the label centre along dir, so the box edge clears the anchor by `gap`
    const reach = Math.abs(it.dir[0]) * (w / 2) + Math.abs(it.dir[1]) * (h / 2) + (it.gap ?? 12) * k
    const at: Pt = [it.anchor[0] + it.dir[0] * reach, it.anchor[1] + it.dir[1] * reach]
    const pad = 2.5 * k
    const b: [number, number, number, number] = [at[0] - w / 2 - pad, at[1] - h / 2 - pad, at[0] + w / 2 + pad, at[1] + h / 2 + pad]
    if (it.priority > 0 && boxes.some((o) => b[0] < o[2] && b[2] > o[0] && b[1] < o[3] && b[3] > o[1])) continue
    boxes.push(b)
    out.push({ ...it, at, w, h })
  }
  return out
}

export function Pill({ l, k }: { l: PlacedLabel; k: number }) {
  return (
    <g className={`pill${l.strong ? ' is-strong' : ''}`}>
      <rect x={l.at[0] - l.w / 2} y={l.at[1] - l.h / 2} width={l.w} height={l.h} rx={3 * k} stroke={l.color ?? 'var(--ink)'} strokeWidth={1.4 * k} />
      <text x={l.at[0]} y={l.at[1] + 4.2 * k} fontSize={12 * k} textAnchor="middle">
        {l.text}
      </text>
    </g>
  )
}

const SUB = '₀₁₂₃₄₅₆₇₈₉'
/** 40 -> "₄₀", 22.5 -> "₂₂.₅" */
export const subscript = (n: number) => String(n).replace(/\d/g, (d) => SUB[Number(d)])
