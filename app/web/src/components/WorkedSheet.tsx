// "Worked calculation": the classification laid out step by step like the hand method's spreadsheet —
// t₀ at the hinge, the isogon table at the chosen angles, R from t′α = R + (1 − R) cos α, and the class rule.
import { useState } from 'react'
import type { HandMeasurement, Limb, Result } from '../types'
import { angleColor, inFitRange } from '../geometry'
import { hingeFoot } from '../construction'
import { CLASS_MEANING } from './ClassCard'
import { IconX } from './Icons'
import { Help } from './Help'

const RAD = Math.PI / 180
const f = (v: number | null | undefined, n = 3) => (v == null || !isFinite(v) ? '–' : v.toFixed(n))
const Ra = (tp: number, a: number) => {
  const c = Math.cos(a * RAD)
  return (tp - c) / (1 - c)
}
/** Least-squares R for t' = R + (1 − R) cos α through the given points (same as the hand-R fit). */
function fitR(rows: { a: number; tp: number }[]) {
  let num = 0
  let den = 0
  for (const { a, tp } of rows) {
    const c = Math.cos(a * RAD)
    num += (1 - c) * (tp - c)
    den += (1 - c) * (1 - c)
  }
  return den > 0 ? num / den : NaN
}

const RULES = (w: number) => [
  { cls: '1A', test: (R: number) => R > 1 + w, text: `R > 1 + ${w}` },
  { cls: '1B', test: (R: number) => Math.abs(R - 1) <= w, text: `R = 1 ± ${w}` },
  { cls: '1C', test: (R: number) => R > w && R < 1 - w, text: `0 < R < 1` },
  { cls: '2', test: (R: number) => Math.abs(R) <= w, text: `R = 0 ± ${w}` },
  { cls: '3', test: (R: number) => R < -w, text: `R < 0` },
]

interface Props {
  result: Result
  angles: number[]
  hand?: HandMeasurement | null
  title: string
  onClose: () => void
}

export function WorkedSheet({ result, angles, hand, title, onClose }: Props) {
  const limbs = (['left', 'right'] as Limb[]).filter((l) => result.limbs[l]?.fitted)
  const [limb, setLimb] = useState<Limb>(limbs[0] ?? 'left')
  const [showAll, setShowAll] = useState(false)
  const L = result.limbs[limb]
  const chart = result.chart[limb]
  if (!L || !chart || L.R == null || L.t0_px == null) return null

  const t0 = L.t0_px
  const t0Hinge = Math.hypot(result.hinge!.G[0] - hingeFoot(result)[0], result.hinge!.G[1] - hingeFoot(result)[1])
  const A = L.R * t0
  const B = t0 - A
  const w = L.class_window
  const handAt = (a: number) => {
    if (!hand) return null
    const i = hand.angles.findIndex((h) => Math.abs(h - a) < 0.6)
    return i < 0 ? null : hand.t_prime[i]
  }
  const rows = angles
    .map((a) => ({ a, iso: result.isogons.find((i) => i.limb === limb && i.alpha === a), miss: result.missing.find((m) => m.limb === limb && m.alpha === a) }))
    .filter((r) => r.iso || r.miss)
  const used = rows.filter((r) => r.iso && r.iso.t_prime != null && inFitRange(r.a)).map((r) => ({ a: r.a, tp: r.iso!.t_prime! }))
  const Rmine = fitR(used)
  const all = chart.rows.map(([a, t, T]) => ({ a, t, T, tp: t / t0 }))
  const rule = RULES(w).find((r) => r.test(L.R!))

  return (
    <div className="sheet" role="dialog" aria-label="Worked calculation">
      <header className="sheet-head">
        <div>
          <div className="sheet-kicker">Worked calculation</div>
          <h2>How {title} was classified</h2>
        </div>
        <div className="sheet-tabs" role="tablist">
          {limbs.map((l) => (
            <button key={l} role="tab" aria-selected={l === limb} className={`sheet-tab${l === limb ? ' is-on' : ''}`} onClick={() => setLimb(l)}>
              {l === 'left' ? 'Left limb' : 'Right limb'}
            </button>
          ))}
        </div>
        <button className="btn btn-quiet" onClick={onClose}>
          <IconX width={16} height={16} /> Close
        </button>
      </header>

      <div className="sheet-body">
        <section className="sheet-step">
          <div className="step-no">1</div>
          <div>
            <h3>
              Thickness at the hinge, t₀ <Help term="t0" />
            </h3>
            <p>
              Orthogonal thickness of the bed at the hinge, between the parallel tangents at H (outer edge) and G (inner edge).
            </p>
            <div className="calc">
              <div>
                measured between the hinge tangents: <b className="mono">{f(t0Hinge, 0)} px</b>
              </div>
              <div>
                fitted t₀ for the {limb} limb (thickness law at α = 0): <b className="mono">t₀ = {f(t0, 1)} px</b> ← used below
              </div>
            </div>
          </div>
        </section>

        <section className="sheet-step">
          <div className="step-no">2</div>
          <div>
            <h3>
              Isogons at your angles <Help term="tprime" /> <Help term="Tprime" />
            </h3>
            <p>
              For each α: the tangents on the outer and inner edge that dip α from the hinge tangent give p and q. t_α is the
              orthogonal thickness between those tangents, T_α the thickness parallel to the axial trace. Dividing by t₀ normalises them.
            </p>
            <div className="sheet-table-wrap">
              <table className="sheet-table">
                <thead>
                  <tr>
                    <th>α</th>
                    <th>cos α</th>
                    <th>t_α (px)</th>
                    <th>T_α (px)</th>
                    <th>t′α = t_α / t₀</th>
                    <th>T′α = T_α / t₀</th>
                    <th>R_α = (t′α − cos α) / (1 − cos α)</th>
                    {hand && <th>hand t′α</th>}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(({ a, iso, miss }) => (
                    <tr key={a} className={inFitRange(a) ? '' : 'is-display-only'}>
                      <td>
                        <span className="chip-dot" style={{ background: angleColor(a) }} /> {a}°
                      </td>
                      <td>{f(Math.cos(a * RAD))}</td>
                      {iso ? (
                        <>
                          <td>{f(iso.t_px, 1)}</td>
                          <td>{f(iso.T_px, 1)}</td>
                          <td className="em">{f(iso.t_prime)}</td>
                          <td>{f(iso.T_prime)}</td>
                          <td>{iso.t_prime == null ? '–' : f(Ra(iso.t_prime, a))}</td>
                        </>
                      ) : (
                        <td colSpan={5} className="why">
                          not measured: {miss?.why}
                        </td>
                      )}
                      {hand && <td className="hand">{f(handAt(a))}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {rows.some((r) => !inFitRange(r.a)) && <p className="small">Rows shaded grey are outside 20–70° and are not used for R.</p>}
          </div>
        </section>

        <section className="sheet-step">
          <div className="step-no">3</div>
          <div>
            <h3>
              The ratio R <Help term="R" />
            </h3>
            <p>
              Ramsay's thickness law: <span className="formula">t′α = R + (1 − R) cos α</span>. R = 1 means constant thickness (parallel fold),
              R = 0 means t′α = cos α (similar fold). Each row gives R_α; fitting all of them gives one R.
            </p>
            <div className="calc">
              <div>
                from your {used.length} angle{used.length === 1 ? '' : 's'} (least squares through the rows above):{' '}
                <b className="mono">R = {f(Rmine)}</b>
              </div>
              <div>
                engine, from all {all.length} angles from 20° to 70° every 2.5°: fit <span className="formula">t_α = A + B cos α</span> →{' '}
                <span className="mono">
                  A = {f(A, 1)}, B = {f(B, 1)}, t₀ = A + B = {f(t0, 1)} px
                </span>
              </div>
              <div className="calc-result">
                R = A / (A + B) = <b className="mono">{f(L.R)}</b>
                <span className="mono muted"> ± {f(L.sigma_R)}</span>
                {hand && (
                  <span className="muted">
                    {' '}
                    · hand ({hand.label}): <b className="mono">{f(hand.R)}</b>
                  </span>
                )}
              </div>
            </div>
            <button className="btn btn-chip sheet-more" onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Hide' : 'Show'} all {all.length} angles the engine used
            </button>
            {showAll && (
              <div className="sheet-table-wrap">
                <table className="sheet-table is-compact">
                  <thead>
                    <tr>
                      <th>α</th>
                      <th>cos α</th>
                      <th>t_α (px)</th>
                      <th>T_α (px)</th>
                      <th>t′α</th>
                      <th>R_α</th>
                    </tr>
                  </thead>
                  <tbody>
                    {all.map((r) => (
                      <tr key={r.a}>
                        <td>{r.a}°</td>
                        <td>{f(Math.cos(r.a * RAD))}</td>
                        <td>{f(r.t, 1)}</td>
                        <td>{f(r.T, 1)}</td>
                        <td className="em">{f(r.tp)}</td>
                        <td>{f(Ra(r.tp, r.a))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        <section className="sheet-step">
          <div className="step-no">4</div>
          <div>
            <h3>
              Class from R <Help term="classes" />
            </h3>
            <p>
              R is compared with the class boundaries. Values within ±{w} of 0 or 1 count as exactly Class 2 or 1B (the band is the larger of 2σ_R and
              0.05).
            </p>
            <ul className="rules">
              {RULES(w).map((r) => (
                <li key={r.cls} className={r.cls === rule?.cls ? 'is-hit' : ''}>
                  <span className="mono rule-test">{r.text}</span>
                  <span className="rule-arrow">→</span>
                  <b>Class {r.cls}</b>
                  <span className="rule-meaning">{CLASS_MEANING[r.cls]}</span>
                </li>
              ))}
            </ul>
            <div className="calc calc-final">
              {limb === 'left' ? 'Left' : 'Right'} limb: R = <b className="mono">{f(L.R)}</b> → <b>Class {L.fold_class ?? '?'}</b>
              {limbs.length > 1 && (
                <>
                  <br />
                  Both limbs:{' '}
                  {limbs.map((l) => `${l} ${result.limbs[l]!.fold_class ?? '?'} (R ${f(result.limbs[l]!.R)})`).join(', ')} →{' '}
                  <b>{result.overall?.fold_class ? `Class ${result.overall.fold_class}` : 'the limbs disagree'}</b>
                </>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
