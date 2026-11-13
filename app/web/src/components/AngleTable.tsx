// One row per chosen angle: t_α (px) and t'α on each limb, the hand-measured t'α where the example has one,
// and why an angle could not be measured.
import type { HandMeasurement, Limb, Result } from '../types'
import { angleColor, inFitRange } from '../geometry'
import { Rich } from './Tex'

const LIMBS: Limb[] = ['left', 'right']

export function AngleTable({ result, angles, hand }: { result: Result; angles: number[]; hand?: HandMeasurement | null }) {
  const iso = (l: Limb, a: number) => result.isogons.find((i) => i.limb === l && i.alpha === a)
  const miss = (l: Limb, a: number) => result.missing.find((m) => m.limb === l && m.alpha === a)
  const handAt = (a: number) => {
    if (!hand) return null
    const i = hand.angles.findIndex((h) => Math.abs(h - a) < 0.6)
    return i < 0 ? null : hand.t_prime[i]
  }

  return (
    <div className="atable-wrap">
      <table className="atable">
        <thead>
          <tr>
            <th>α</th>
            <th>Left limb</th>
            <th>Right limb</th>
            {hand && <th>Hand</th>}
          </tr>
        </thead>
        <tbody>
          {angles.map((a) => {
            const h = handAt(a)
            return (
              <tr key={a} className={inFitRange(a) ? '' : 'is-display-only'}>
                <td className="atable-alpha">
                  <span className="chip-dot" style={{ background: angleColor(a) }} />
                  <span className="mono">{a}°</span>
                  {!inFitRange(a) && <span className="atable-flag" title="Shown on the photo but not used in the fit (outside 20–70°)">⋯</span>}
                </td>
                {LIMBS.map((l) => {
                  const i = iso(l, a)
                  if (i)
                    return (
                      <td key={l}>
                        <span className="mono atable-t">{i.t_prime?.toFixed(3) ?? '–'}</span>
                        <span className="mono atable-px">{i.t_px.toFixed(0)} px</span>
                      </td>
                    )
                  const m = miss(l, a)
                  return (
                    <td key={l} className="atable-missing" title={m?.why}>
                      <span className="mono">–</span>
                      {m && <span className="atable-why">{m.why}</span>}
                    </td>
                  )
                })}
                {hand && <td className="mono atable-hand">{h == null ? '' : h.toFixed(3)}</td>}
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="atable-foot">
        <Rich text="Each cell: $t'_\alpha = t_\alpha / t_0$ (bold) and $t_\alpha$ in px. $t_0$ is the thickness at the hinge." />
      </div>
    </div>
  )
}
