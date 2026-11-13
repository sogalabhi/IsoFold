// The engine's result drawn on the photo (inside the canvas SVG, image-pixel coordinates).
// k = image px per screen px, so every size here is a constant on-screen size.
import type { LineKey, Pt, Result } from '../types'
import { angleColor } from '../geometry'
import { hingeFoot } from '../construction'
import { type LabelItem, Pill, layoutLabels, subscript } from './Labels'

const add = (a: Pt, b: Pt): Pt => [a[0] + b[0], a[1] + b[1]]
const sub = (a: Pt, b: Pt): Pt => [a[0] - b[0], a[1] - b[1]]
const mul = (a: Pt, s: number): Pt => [a[0] * s, a[1] * s]
const unit = (a: Pt): Pt => {
  const l = Math.hypot(a[0], a[1]) || 1
  return [a[0] / l, a[1] / l]
}
const pts = (p: Pt[]) => p.map((v) => `${v[0].toFixed(1)},${v[1].toFixed(1)}`).join(' ')
const mean = (p: Pt[]): Pt => mul(p.reduce((s, v) => add(s, v), [0, 0] as Pt), 1 / p.length)

/** Every label on the photo, by priority: hinge points, then limbs / axial trace / inflections / t₀,
 * then the isogon angles, then p and q. */
function labelItems(result: Result): LabelItem[] {
  const { cut, hinge, isogons } = result
  const items: LabelItem[] = []
  if (!hinge || !cut) return items
  const { H, G } = hinge
  const axis = unit(sub(H, G))
  items.push({ key: 'H', text: 'H', anchor: H, dir: axis, priority: 0, strong: true })
  items.push({ key: 'G', text: 'G', anchor: G, dir: mul(axis, -1), priority: 0, strong: true })

  // axial trace label at the far end beyond H
  items.push({ key: 'axial', text: 'axial trace', anchor: add(H, mul(sub(H, G), 0.35)), dir: axis, gap: 6, priority: 1 })

  // t0 beside the middle of H-G
  const foot = hingeFoot(result)
  const t0 = Math.hypot(...sub(G, foot))
  const side: Pt = [-axis[1], axis[0]]
  items.push({ key: 't0', text: `t₀ ${t0.toFixed(0)} px`, anchor: mean([H, G]), dir: side, gap: 10, priority: 1 })

  // inflection points: the ends of the stretch of each line the engine measured
  const core = mean(cut.inner)
  for (const key of ['outer', 'inner'] as const) {
    const line = cut[key]
    for (const [end, prev, tag] of [
      [line[0], line[Math.min(6, line.length - 1)], 'a'],
      [line[line.length - 1], line[Math.max(0, line.length - 7)], 'b'],
    ] as const) {
      items.push({ key: `I-${key}-${tag}`, text: 'I', anchor: end, dir: unit(sub(end, prev)), gap: 8, priority: 1 })
    }
  }

  // limb names beside the outer line, near each end. Same rule as the backend (manual.py): the limb whose
  // end lies further left on screen is the left limb, so the photo and the table always agree.
  const outer = cut.outer
  const firstIsLeft = outer[0][0] <= outer[outer.length - 1][0]
  for (const [i, isFirst] of [
    [Math.round(outer.length * 0.2), true],
    [Math.round(outer.length * 0.8), false],
  ] as const) {
    const p = outer[i]
    const name = isFirst === firstIsLeft ? 'left limb' : 'right limb'
    items.push({ key: `limb-${isFirst ? 'a' : 'b'}`, text: name, anchor: p, dir: unit(sub(p, core)), gap: 26, priority: 1 })
  }

  // isogon angles just outside the outer line, steepest first; then p and q
  for (const iso of [...isogons].sort((a, b) => b.alpha - a.alpha)) {
    const out = unit(sub(iso.p, iso.q))
    items.push({ key: `a-${iso.limb}-${iso.alpha}`, text: `${iso.alpha}°`, anchor: iso.p, dir: out, gap: 14, priority: 2, color: angleColor(iso.alpha) })
  }
  for (const iso of isogons) {
    const s = subscript(iso.alpha)
    const along = unit(iso.tan_p)
    items.push({ key: `p-${iso.limb}-${iso.alpha}`, text: `p${s}`, anchor: iso.p, dir: along, gap: 10, priority: 3 })
    items.push({ key: `q-${iso.limb}-${iso.alpha}`, text: `q${s}`, anchor: iso.q, dir: unit(iso.tan_q), gap: 10, priority: 3 })
  }
  return items
}

export function ResultOverlay({ result, k, labels = true }: { result: Result; k: number; labels?: boolean }) {
  const { cut, hinge, isogons } = result
  // the engine may have read the red line as the inner edge; colour each cut line by the user's line
  const colorKey = (engineKey: LineKey): LineKey => (result.swapped ? (engineKey === 'outer' ? 'inner' : 'outer') : engineKey)
  const dots: Pt[] = hinge ? [hinge.H, hinge.G] : []
  const placed = labels ? layoutLabels(labelItems(result), k, dots) : layoutLabels(labelItems(result).filter((l) => l.priority === 0), k)

  return (
    <g className="result-layer">
      {/* the stretch of each line the engine used (cut at the inflections), drawn solid over the faded trace */}
      {cut &&
        (['outer', 'inner'] as const).map((key) => (
          <g key={key}>
            <polyline points={pts(cut[key])} className="trace-halo" strokeWidth={7 * k} />
            <polyline points={pts(cut[key])} className={`trace trace-${colorKey(key)}`} strokeWidth={3 * k} />
            {[cut[key][0], cut[key][cut[key].length - 1]].map((p, j) => (
              <rect key={j} x={p[0] - 4.5 * k} y={p[1] - 4.5 * k} width={9 * k} height={9 * k} className="infl-pt" strokeWidth={1.6 * k} />
            ))}
          </g>
        ))}

      {/* axial trace through H and G, extended past both */}
      {hinge &&
        (() => {
          const d = sub(hinge.H, hinge.G)
          const a = add(hinge.H, mul(d, 0.35))
          const b = sub(hinge.G, mul(d, 0.35))
          return (
            <g className="axial">
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="axial-halo" strokeWidth={4 * k} />
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="axial-line" strokeWidth={1.5 * k} strokeDasharray={`${8 * k} ${6 * k}`} />
            </g>
          )
        })()}

      {/* dip isogons at the chosen angles */}
      {isogons.map((iso) => {
        const c = angleColor(iso.alpha)
        const tick = (at: Pt, t: Pt) => {
          const a = add(at, mul(t, 20 * k))
          const b = sub(at, mul(t, 20 * k))
          return (
            <>
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="iso-halo" strokeWidth={4.5 * k} />
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={c} strokeWidth={2 * k} strokeLinecap="round" />
            </>
          )
        }
        return (
          <g key={`${iso.limb}-${iso.alpha}`}>
            <line x1={iso.p[0]} y1={iso.p[1]} x2={iso.q[0]} y2={iso.q[1]} className="iso-halo" strokeWidth={5.5 * k} />
            <line
              x1={iso.p[0]}
              y1={iso.p[1]}
              x2={iso.q[0]}
              y2={iso.q[1]}
              stroke={c}
              strokeWidth={2.5 * k}
              strokeLinecap="round"
              strokeDasharray={iso.in_fit_range ? undefined : `${7 * k} ${5 * k}`}
            />
            {tick(iso.p, iso.tan_p)}
            {tick(iso.q, iso.tan_q)}
            <circle cx={iso.p[0]} cy={iso.p[1]} r={3.6 * k} className="iso-end" stroke={c} strokeWidth={1.6 * k} />
            <circle cx={iso.q[0]} cy={iso.q[1]} r={3.6 * k} className="iso-end" stroke={c} strokeWidth={1.6 * k} />
          </g>
        )
      })}

      {/* hinge points */}
      {hinge &&
        [hinge.H, hinge.G].map((p, j) => {
          const s = 7 * k
          return (
            <polygon
              key={j}
              points={pts([
                [p[0], p[1] - s],
                [p[0] + s, p[1]],
                [p[0], p[1] + s],
                [p[0] - s, p[1]],
              ])}
              className="hinge-pt"
              strokeWidth={1.8 * k}
            />
          )
        })}

      {placed.map((l) => (
        <Pill key={l.key} l={l} k={k} />
      ))}
    </g>
  )
}
