// One frame of the construction animation, drawn on the photo (image-pixel coordinates; k = image px per
// screen px). Everything comes from the engine's result: hinge tangents, p, q, the perpendicular foot, t_α.
import type { Isogon, Pt, Result } from '../types'
import { angleColor } from '../geometry'
import { type Frame, type Timeline, hingeFoot, span } from '../construction'

const add = (a: Pt, b: Pt): Pt => [a[0] + b[0], a[1] + b[1]]
const sub = (a: Pt, b: Pt): Pt => [a[0] - b[0], a[1] - b[1]]
const mul = (a: Pt, s: number): Pt => [a[0] * s, a[1] * s]
const lerp = (a: Pt, b: Pt, u: number): Pt => [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]
const dot = (a: Pt, b: Pt) => a[0] * b[0] + a[1] * b[1]
const cross = (a: Pt, b: Pt) => a[0] * b[1] - a[1] * b[0]
const unit = (a: Pt): Pt => {
  const l = Math.hypot(a[0], a[1]) || 1
  return [a[0] / l, a[1] / l]
}
const dir = (phi: number): Pt => [Math.cos(phi), Math.sin(phi)]
const ang = (d: Pt) => Math.atan2(d[1], d[0])
const pts = (p: Pt[]) => p.map((v) => `${v[0].toFixed(1)},${v[1].toFixed(1)}`).join(' ')

/** A straight-edge ruler whose measuring edge lies on the line through c with direction d; its body sits on the `away` side. */
function Ruler({ c, d, L, k, away, opacity = 1 }: { c: Pt; d: Pt; L: number; k: number; away: Pt; opacity?: number }) {
  const n: Pt = [-d[1], d[0]]
  const flip = dot(n, away) < 0 ? -1 : 1
  const w = 16 * k
  const ticks = []
  const step = 10 * k
  for (let x = -L / 2 + step, j = 1; x < L / 2; x += step, j++) ticks.push(<line key={j} x1={x} y1={0} x2={x} y2={(j % 5 === 0 ? 8 : 4.5) * k} className="ruler-tick" strokeWidth={1 * k} />)
  return (
    <g transform={`translate(${c[0]} ${c[1]}) rotate(${(ang(d) * 180) / Math.PI}) scale(1 ${flip})`} opacity={opacity}>
      <rect x={-L / 2} y={0} width={L} height={w} className="ruler-body" strokeWidth={1.2 * k} />
      {ticks}
      <line x1={-L / 2 - 30 * k} y1={0} x2={L / 2 + 30 * k} y2={0} className="ruler-edge" strokeWidth={1.4 * k} />
    </g>
  )
}

function Dot({ p, k, u = 1, cls }: { p: Pt; k: number; u?: number; cls: string }) {
  if (u <= 0) return null
  const pop = u < 1 ? 1 + 0.6 * Math.sin(Math.PI * u) : 1
  return <circle cx={p[0]} cy={p[1]} r={5.5 * k * pop} className={cls} strokeWidth={2 * k} />
}

function Tag({ at, text, k, color }: { at: Pt; text: string; k: number; color?: string }) {
  const w = (text.length * 7.2 + 12) * k
  const h = 19 * k
  return (
    <g>
      <rect x={at[0] - w / 2} y={at[1] - h / 2} width={w} height={h} rx={3 * k} className="c-tag" stroke={color ?? 'var(--ink)'} strokeWidth={1.4 * k} />
      <text x={at[0]} y={at[1] + 4.5 * k} fontSize={12.5 * k} className="c-tag-text" textAnchor="middle">
        {text}
      </text>
    </g>
  )
}

/** Dimension line a→b drawn to fraction u, with arrowheads and a label once it has length. */
function Dimension({ a, b, u, k, label }: { a: Pt; b: Pt; u: number; k: number; label?: string }) {
  if (u <= 0) return null
  const e = lerp(a, b, u)
  const d = unit(sub(b, a))
  const n: Pt = [-d[1], d[0]]
  const head = (p: Pt, back: Pt) => pts([add(p, add(mul(back, 9 * k), mul(n, 4 * k))), p, add(p, sub(mul(back, 9 * k), mul(n, 4 * k)))])
  return (
    <g className="dim">
      <line x1={a[0]} y1={a[1]} x2={e[0]} y2={e[1]} className="dim-halo" strokeWidth={5 * k} />
      <line x1={a[0]} y1={a[1]} x2={e[0]} y2={e[1]} className="dim-line" strokeWidth={1.8 * k} />
      <polyline points={head(a, d)} className="dim-line" strokeWidth={1.8 * k} fill="none" />
      {u > 0.98 && <polyline points={head(b, mul(d, -1))} className="dim-line" strokeWidth={1.8 * k} fill="none" />}
      {label && <Tag at={add(lerp(a, b, 0.5), mul(n, 22 * k))} text={label} k={k} />}
    </g>
  )
}

function FinishedIsogon({ iso, k }: { iso: Isogon; k: number }) {
  const c = angleColor(iso.alpha)
  const at = add(iso.p, mul(unit(sub(iso.p, iso.q)), 26 * k))
  return (
    <g>
      <line x1={iso.p[0]} y1={iso.p[1]} x2={iso.q[0]} y2={iso.q[1]} className="iso-halo" strokeWidth={5 * k} />
      <line x1={iso.p[0]} y1={iso.p[1]} x2={iso.q[0]} y2={iso.q[1]} stroke={c} strokeWidth={2.4 * k} strokeLinecap="round" />
      <Dot p={iso.p} k={k * 0.7} cls="c-dot" />
      <Dot p={iso.q} k={k * 0.7} cls="c-dot" />
      <Tag at={at} text={`${iso.alpha}°`} k={k * 0.85} color={c} />
    </g>
  )
}

interface Props {
  result: Result
  tl: Timeline
  frame: Frame
  k: number
}

export function ConstructionOverlay({ result, tl, frame, k }: Props) {
  const { H, G, tan_H, tan_G } = result.hinge!
  const step = tl.steps[frame.i]
  const u = frame.u
  const HG = Math.hypot(...sub(G, H))
  const L = Math.max(0.9 * HG, 220 * k) // ruler length
  const awayH = unit(sub(H, G))
  const awayG = unit(sub(G, H))
  const footH = hingeFoot(result)

  const hingeU = step.kind === 'hinge' ? u : 1
  const curOrder = step.order ?? (step.kind === 'fit' ? tl.isogons.length : -1)
  const done = tl.isogons.filter((_, o) => o < curOrder || (o === curOrder && step.kind === 'plot'))

  // ----- current isogon
  let current: React.ReactNode = null
  if (step.iso && step.kind !== 'plot') {
    const iso = step.iso
    const c = angleColor(iso.alpha)
    const tp: Pt = dot(iso.tan_p, tan_H) >= 0 ? iso.tan_p : mul(iso.tan_p, -1)
    const theta = Math.atan2(cross(tan_H, tp), dot(tan_H, tp)) // signed turn from the hinge tangent, |θ| = α
    const awayP = unit(sub(iso.p, iso.q))
    const awayQ = unit(sub(iso.q, iso.p))

    if (step.kind === 'turn') {
      const e = span(u, 0.1, 0.9)
      const d = dir(ang(tan_H) + theta * e)
      const R = Math.min(90 * k, 0.45 * HG)
      const a0 = ang(tan_H)
      const a1 = a0 + theta * e
      const arc = `M${H[0] + R * Math.cos(a0)},${H[1] + R * Math.sin(a0)} A${R},${R} 0 0 ${theta > 0 ? 1 : 0} ${H[0] + R * Math.cos(a1)},${H[1] + R * Math.sin(a1)}`
      const mid = a0 + (theta * e) / 2
      current = (
        <g>
          <Ruler c={H} d={d} L={L} k={k} away={awayH} />
          <path d={arc} className="protractor" strokeWidth={2 * k} />
          <Tag at={add(H, mul(dir(mid), R + 22 * k))} text={`${Math.round(iso.alpha * e)}°`} k={k} color={c} />
        </g>
      )
    } else if (step.kind === 'outer') {
      const e = span(u, 0.05, 0.85)
      current = (
        <g>
          <Ruler c={lerp(H, iso.p, e)} d={tp} L={L} k={k} away={awayP} />
          <Dot p={iso.p} k={k} u={span(u, 0.8, 1)} cls="c-dot-outer" />
          {u > 0.85 && <Tag at={add(iso.p, mul(awayP, 30 * k))} text="p" k={k} />}
        </g>
      )
    } else if (step.kind === 'inner') {
      const e = span(u, 0.05, 0.85)
      current = (
        <g>
          <Ruler c={iso.p} d={tp} L={L} k={k} away={awayP} opacity={0.55} />
          <Ruler c={lerp(iso.p, iso.q, e)} d={tp} L={L} k={k} away={awayQ} />
          <Dot p={iso.p} k={k} cls="c-dot-outer" />
          <Tag at={add(iso.p, mul(awayP, 30 * k))} text="p" k={k} />
          <Dot p={iso.q} k={k} u={span(u, 0.8, 1)} cls="c-dot-inner" />
          {u > 0.85 && <Tag at={add(iso.q, mul(awayQ, 30 * k))} text="q" k={k} />}
        </g>
      )
    } else if (step.kind === 'isogon') {
      const e1 = span(u, 0.0, 0.45)
      const e2 = span(u, 0.5, 0.95)
      const end = lerp(iso.p, iso.q, e1)
      current = (
        <g>
          <Ruler c={iso.p} d={tp} L={L} k={k} away={awayP} opacity={0.45} />
          <Ruler c={iso.q} d={tp} L={L} k={k} away={awayQ} opacity={0.45} />
          <line x1={iso.p[0]} y1={iso.p[1]} x2={end[0]} y2={end[1]} className="iso-halo" strokeWidth={6 * k} />
          <line x1={iso.p[0]} y1={iso.p[1]} x2={end[0]} y2={end[1]} stroke={c} strokeWidth={3 * k} strokeLinecap="round" />
          <Dimension a={iso.foot} b={iso.q} u={e2} k={k} label={e2 > 0.2 ? `t_α ${Math.round(iso.t_px * e2)} px` : undefined} />
          <Dot p={iso.p} k={k} cls="c-dot-outer" />
          <Dot p={iso.q} k={k} cls="c-dot-inner" />
        </g>
      )
    }
  }

  return (
    <g className="construction">
      {/* the stretch of each line the engine measured */}
      {result.cut &&
        (['outer', 'inner'] as const).map((key) => {
          const color = result.swapped ? (key === 'outer' ? 'inner' : 'outer') : key
          return (
            <g key={key}>
              <polyline points={pts(result.cut![key])} className="trace-halo" strokeWidth={7 * k} />
              <polyline points={pts(result.cut![key])} className={`trace trace-${color}`} strokeWidth={3 * k} />
            </g>
          )
        })}

      {/* hinge: ruler settles on the tangent at H, a parallel copy at G, then the axial trace */}
      {(() => {
        const inH = span(hingeU, 0.0, 0.3)
        const toG = span(hingeU, 0.35, 0.65)
        const axial = span(hingeU, 0.65, 0.95)
        const ext = 0.35
        const A = add(H, mul(sub(H, G), ext))
        const B = lerp(A, sub(G, mul(sub(H, G), ext)), axial)
        const tangentsOnly = step.kind !== 'hinge'
        return (
          <g>
            {tangentsOnly ? (
              <>
                {[
                  [H, tan_H],
                  [G, tan_G],
                ].map(([p, d], j) => {
                  const a = add(p as Pt, mul(d as Pt, L / 2))
                  const b = sub(p as Pt, mul(d as Pt, L / 2))
                  return <line key={j} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="c-tangent" strokeWidth={1.4 * k} strokeDasharray={`${6 * k} ${4 * k}`} />
                })}
              </>
            ) : (
              <>
                <Ruler c={add(H, mul(awayH, 140 * k * (1 - inH)))} d={tan_H} L={L} k={k} away={awayH} opacity={inH} />
                {toG > 0 && <Ruler c={lerp(H, G, toG)} d={tan_G} L={L} k={k} away={awayG} />}
              </>
            )}
            {axial > 0 && (
              <>
                <line x1={A[0]} y1={A[1]} x2={B[0]} y2={B[1]} className="axial-halo" strokeWidth={4 * k} />
                <line x1={A[0]} y1={A[1]} x2={B[0]} y2={B[1]} className="axial-line" strokeWidth={1.6 * k} strokeDasharray={`${8 * k} ${6 * k}`} />
              </>
            )}
            <Dot p={H} k={k} u={span(hingeU, 0.25, 0.4)} cls="c-dot-hinge" />
            <Dot p={G} k={k} u={span(hingeU, 0.6, 0.75)} cls="c-dot-hinge" />
            {hingeU > 0.35 && <Tag at={add(H, mul(awayH, 30 * k))} text="H" k={k} />}
            {hingeU > 0.7 && <Tag at={add(G, mul(awayG, 30 * k))} text="G" k={k} />}
          </g>
        )
      })()}

      {/* t0 between the hinge tangents */}
      {step.kind === 't0' ? (
        <Dimension a={footH} b={G} u={span(u, 0.05, 0.6)} k={k} label={u > 0.25 ? `t₀ ${Math.round(tl.t0 * span(u, 0.25, 0.9))} px` : undefined} />
      ) : (
        frame.i > 1 && <Dimension a={footH} b={G} u={1} k={k} label="t₀" />
      )}

      {done.map((iso) => (
        <FinishedIsogon key={`${iso.limb}-${iso.alpha}`} iso={iso} k={k} />
      ))}
      {current}
    </g>
  )
}
