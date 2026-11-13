// The engine's result drawn on the photo (inside the canvas SVG, image-pixel coordinates).
// k = image px per screen px, so every size here is a constant on-screen size.
import type { Isogon, LineKey, Pt, Result } from '../types'
import { angleColor } from '../geometry'

const add = (a: Pt, b: Pt): Pt => [a[0] + b[0], a[1] + b[1]]
const sub = (a: Pt, b: Pt): Pt => [a[0] - b[0], a[1] - b[1]]
const mul = (a: Pt, s: number): Pt => [a[0] * s, a[1] * s]
const unit = (a: Pt): Pt => {
  const l = Math.hypot(a[0], a[1]) || 1
  return [a[0] / l, a[1] / l]
}
const pts = (p: Pt[]) => p.map((v) => `${v[0].toFixed(1)},${v[1].toFixed(1)}`).join(' ')

/** Label boxes for the isogons, steepest first; a label that would overlap one already placed is left out
 * (zooming in makes room and brings it back; the chip colours still identify every isogon). */
function placeLabels(isogons: Isogon[], k: number) {
  const placed: { x0: number; y0: number; x1: number; y1: number }[] = []
  const out = new Map<Isogon, { at: Pt; w: number; h: number }>()
  for (const iso of [...isogons].sort((a, b) => b.alpha - a.alpha)) {
    const label = `${iso.alpha}°`
    const w = (label.length * 7 + 10) * k
    const h = 17 * k
    const at = add(iso.p, mul(unit(sub(iso.p, iso.q)), 14 * k + w / 2))
    const pad = 3 * k
    const box = { x0: at[0] - w / 2 - pad, y0: at[1] - h / 2 - pad, x1: at[0] + w / 2 + pad, y1: at[1] + h / 2 + pad }
    if (placed.some((b) => box.x0 < b.x1 && box.x1 > b.x0 && box.y0 < b.y1 && box.y1 > b.y0)) continue
    placed.push(box)
    out.set(iso, { at, w, h })
  }
  return out
}

export function ResultOverlay({ result, k }: { result: Result; k: number }) {
  const { cut, hinge, isogons } = result
  const labels = placeLabels(isogons, k)
  // the engine may have read the red line as the inner edge; colour each cut line by the user's line
  const colorKey = (engineKey: LineKey): LineKey => (result.swapped ? (engineKey === 'outer' ? 'inner' : 'outer') : engineKey)

  return (
    <g className="result-layer">
      {/* the stretch of each line the engine used (cut at the inflections), drawn solid over the faded trace */}
      {cut &&
        (['outer', 'inner'] as const).map((key) => (
          <g key={key}>
            <polyline points={pts(cut[key])} className="trace-halo" strokeWidth={7 * k} />
            <polyline points={pts(cut[key])} className={`trace trace-${colorKey(key)}`} strokeWidth={3 * k} />
          </g>
        ))}

      {/* axial trace through H and G, extended past both */}
      {hinge && (
        <g className="axial">
          {(() => {
            const d = sub(hinge.H, hinge.G)
            const a = add(hinge.H, mul(d, 0.35))
            const b = sub(hinge.G, mul(d, 0.35))
            return (
              <>
                <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="axial-halo" strokeWidth={4 * k} />
                <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="axial-line" strokeWidth={1.5 * k} strokeDasharray={`${8 * k} ${6 * k}`} />
              </>
            )
          })()}
        </g>
      )}

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
        const lab = labels.get(iso)
        return (
          <g key={`${iso.limb}-${iso.alpha}`} className={iso.in_fit_range ? '' : 'is-display-only'}>
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
            {lab && (
              <>
                <rect x={lab.at[0] - lab.w / 2} y={lab.at[1] - lab.h / 2} width={lab.w} height={lab.h} rx={3 * k} className="iso-pill" stroke={c} strokeWidth={1.5 * k} />
                <text x={lab.at[0]} y={lab.at[1] + 4 * k} className="iso-label" fontSize={11.5 * k} textAnchor="middle">
                  {iso.alpha}°
                </text>
              </>
            )}
          </g>
        )
      })}

      {/* hinge points */}
      {hinge &&
        ([
          ['H', hinge.H, hinge.G],
          ['G', hinge.G, hinge.H],
        ] as const).map(([name, p, other]) => {
          const s = 7 * k
          const away = unit(sub(p, other))
          const lab = add(p, mul(away, 16 * k))
          return (
            <g key={name}>
              <polygon
                points={pts([
                  [p[0], p[1] - s],
                  [p[0] + s, p[1]],
                  [p[0], p[1] + s],
                  [p[0] - s, p[1]],
                ])}
                className="hinge-pt"
                strokeWidth={1.8 * k}
              />
              <text x={lab[0]} y={lab[1] + 5 * k} className="hinge-label" fontSize={14 * k} strokeWidth={4 * k} textAnchor="middle">
                {name}
              </text>
            </g>
          )
        })}
    </g>
  )
}
