// Ramsay's t'α–α diagram with the class fields shaded, the engine's fit points and fitted curve per limb,
// the user's chosen angles, and (for examples) the hand-measured CorelDraw points.
import type { HandMeasurement, Limb, Result } from '../types'
import { angleColor } from '../geometry'

const W = 340
const H = 236
const M = { l: 38, r: 12, t: 12, b: 32 }
const X_MAX = 90
const Y_MAX = 1.4
const RAD = Math.PI / 180

const x = (a: number) => M.l + (a / X_MAX) * (W - M.l - M.r)
const y = (t: number) => H - M.b - (Math.max(0, Math.min(Y_MAX, t)) / Y_MAX) * (H - M.t - M.b)

const curve = (f: (a: number) => number, from = 0, to = X_MAX) => {
  const pts: string[] = []
  for (let a = from; a <= to; a += 1) pts.push(`${x(a).toFixed(1)},${y(f(a)).toFixed(1)}`)
  return pts
}

const LIMBS: Limb[] = ['left', 'right']

interface Props {
  result?: Result | null
  hand?: HandMeasurement | null
}

export function RamsayChart({ result, hand }: Props) {
  const cos = curve((a) => Math.cos(a * RAD))
  const top = y(Y_MAX)
  const one = y(1)
  const field1A = `M${x(0)},${top} L${x(X_MAX)},${top} L${x(X_MAX)},${one} L${x(0)},${one} Z`
  const field1C = `M${x(0)},${one} L${x(X_MAX)},${one} L${cos.slice().reverse().join(' L')} Z`
  const field3 = `M${cos.join(' L')} L${x(X_MAX)},${y(0)} L${x(0)},${y(0)} Z`
  const live = result && result.verdict !== 'refused' ? result : null

  return (
    <div className="ramsay-wrap">
      <svg className={`ramsay${live ? '' : ' is-ghost'}`} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Ramsay t′α against α diagram">
        <path d={field1A} className="field field-1a" />
        <path d={field1C} className="field field-1c" />
        <path d={field3} className="field field-3" />
        <rect x={x(0)} y={top} width={x(20) - x(0)} height={y(0) - top} className="no-fit" />
        <rect x={x(70)} y={top} width={x(X_MAX) - x(70)} height={y(0) - top} className="no-fit" />

        {[0, 15, 30, 45, 60, 75, 90].map((a) => (
          <g key={a}>
            <line x1={x(a)} x2={x(a)} y1={top} y2={y(0)} className="grid" />
            <text x={x(a)} y={H - M.b + 16} className="tick" textAnchor="middle">
              {a}°
            </text>
          </g>
        ))}
        {[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4].map((t) => (
          <g key={t}>
            <line x1={x(0)} x2={x(X_MAX)} y1={y(t)} y2={y(t)} className="grid" />
            <text x={M.l - 6} y={y(t) + 3.5} className="tick" textAnchor="end">
              {t.toFixed(1)}
            </text>
          </g>
        ))}

        <line x1={x(0)} x2={x(X_MAX)} y1={one} y2={one} className="ref ref-1b" />
        <polyline points={cos.join(' ')} className="ref ref-2" />

        <text x={x(45)} y={y(1.2)} className="field-label" textAnchor="middle">1A</text>
        <text x={x(86)} y={y(1) - 5} className="field-label" textAnchor="middle">1B</text>
        <text x={x(66)} y={y(0.75)} className="field-label" textAnchor="middle">1C</text>
        <text x={x(87)} y={y(0.17)} className="field-label" textAnchor="middle">2</text>
        <text x={x(36)} y={y(0.38)} className="field-label" textAnchor="middle">3</text>

        {live && (
          <g>
            {/* chosen angles: guide lines in the chip colour */}
            {[...new Set(live.isogons.map((i) => i.alpha))].map((a) => (
              <line key={a} x1={x(a)} x2={x(a)} y1={top} y2={y(0)} stroke={angleColor(a)} className="guide" />
            ))}
            {/* fitted curve t' = R + (1 - R) cos α per limb */}
            {LIMBS.map((l) => {
              const c = live.chart[l]
              if (!c) return null
              return <polyline key={l} points={curve((a) => c.fit.R + (1 - c.fit.R) * Math.cos(a * RAD)).join(' ')} className={`fit fit-${l}`} />
            })}
            {/* the engine's 2.5° grid points used for the fit */}
            {LIMBS.map((l) =>
              live.chart[l]?.points.map(([a, t]) =>
                l === 'left' ? (
                  <circle key={`${l}${a}`} cx={x(a)} cy={y(t)} r={2.6} className="pt pt-left">
                    <title>{`left limb · α ${a}° · t′ ${t.toFixed(3)}`}</title>
                  </circle>
                ) : (
                  <path key={`${l}${a}`} d={`M${x(a)},${y(t) - 3.4} l3,5.4 h-6 z`} className="pt pt-right">
                    <title>{`right limb · α ${a}° · t′ ${t.toFixed(3)}`}</title>
                  </path>
                ),
              ),
            )}
            {/* chosen angles: the measured isogons, enlarged in their colour */}
            {live.isogons.map(
              (i) =>
                i.t_prime != null && (
                  <circle key={`${i.limb}-${i.alpha}`} cx={x(i.alpha)} cy={y(i.t_prime)} r={4.2} fill={angleColor(i.alpha)} className="pt-chosen">
                    <title>{`${i.limb} limb · α ${i.alpha}° · t_α ${i.t_px.toFixed(0)} px · t′ ${i.t_prime.toFixed(3)}`}</title>
                  </circle>
                ),
            )}
          </g>
        )}

        {/* hand measurements (CorelDraw), for the examples that have them */}
        {hand &&
          hand.angles.map((a, i) => (
            <rect key={a} x={x(a) - 3.6} y={y(hand.t_prime[i]) - 3.6} width={7.2} height={7.2} className="pt-hand" transform={`rotate(45 ${x(a)} ${y(hand.t_prime[i])})`}>
              <title>{`hand (${hand.label}) · α ${a}° · t′ ${hand.t_prime[i].toFixed(3)}`}</title>
            </rect>
          ))}

        <text x={(x(0) + x(X_MAX)) / 2} y={H - 2} className="axis-label" textAnchor="middle">
          dip α
        </text>
        <text x={10} y={(top + y(0)) / 2} className="axis-label" textAnchor="middle" transform={`rotate(-90 10 ${(top + y(0)) / 2})`}>
          t′α
        </text>
      </svg>

      <div className="legend">
        {live && (
          <>
            <span>
              <svg width="10" height="10"><circle cx="5" cy="5" r="3" className="pt pt-left" /></svg> left limb
            </span>
            <span>
              <svg width="10" height="10"><path d="M5,1 l3.4,6 h-6.8 z" className="pt pt-right" /></svg> right limb
            </span>
            <span>
              <svg width="18" height="10"><line x1="1" y1="5" x2="17" y2="5" className="fit fit-left" /></svg> fit
            </span>
          </>
        )}
        {hand && (
          <span>
            <svg width="10" height="10"><rect x="2" y="2" width="6" height="6" className="pt-hand" transform="rotate(45 5 5)" /></svg> hand ({hand.label})
          </span>
        )}
        <span className="legend-muted">shaded: outside the 20–70° fit</span>
      </div>
    </div>
  )
}
