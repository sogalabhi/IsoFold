// Where R sits among the classes: a bar from -0.5 to 1.5 with the class bands, one marker per limb (± σ).
import type { Limb, Result } from '../types'

const LO = -0.5
const HI = 1.5
const WIN = 0.05 // the engine's minimum window around R = 0 (Class 2) and R = 1 (Class 1B)
const pct = (r: number) => ((Math.max(LO, Math.min(HI, r)) - LO) / (HI - LO)) * 100

const BANDS = [
  { cls: '3', from: LO, to: -WIN },
  { cls: '2', from: -WIN, to: WIN },
  { cls: '1C', from: WIN, to: 1 - WIN },
  { cls: '1B', from: 1 - WIN, to: 1 + WIN },
  { cls: '1A', from: 1 + WIN, to: HI },
]

export function RScale({ result }: { result: Result }) {
  const limbs = (['left', 'right'] as Limb[]).filter((l) => result.limbs[l]?.R != null)
  return (
    <div className="rscale">
      <div className="rscale-bar">
        {BANDS.map((b) => (
          <div key={b.cls} className={`rscale-band band-${b.cls}`} style={{ left: `${pct(b.from)}%`, width: `${pct(b.to) - pct(b.from)}%` }}>
            <span>{b.cls}</span>
          </div>
        ))}
        {limbs.map((l) => {
          const { R, sigma_R } = result.limbs[l]!
          const s = Math.max(sigma_R ?? 0, 0)
          return (
            <div key={l}>
              <div className={`rscale-whisker mark-${l}`} style={{ left: `${pct(R! - s)}%`, width: `${pct(R! + s) - pct(R! - s)}%` }} />
              <div className={`rscale-mark mark-${l}`} style={{ left: `${pct(R!)}%` }} title={`${l} limb: R ${R!.toFixed(3)} ± ${s.toFixed(3)}`}>
                {l === 'left' ? 'L' : 'R'}
              </div>
            </div>
          )
        })}
      </div>
      <div className="rscale-ticks mono">
        {[-0.5, 0, 0.5, 1, 1.5].map((t) => (
          <span key={t} style={{ left: `${pct(t)}%` }}>
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
