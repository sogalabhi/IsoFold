import type { HandMeasurement, Result } from '../types'
import { Help } from './Help'

export const CLASS_MEANING: Record<string, string> = {
  '1A': 'Strongly convergent isogons; limbs thicker than the hinge',
  '1B': 'Parallel (concentric) fold; constant layer thickness',
  '1C': 'Weakly convergent isogons; limbs slightly thinned',
  '2': 'Similar fold; isogons parallel to each other',
  '3': 'Divergent isogons; limbs strongly thinned',
}

const VERDICT = {
  confident: { label: 'Confident', mark: '●' },
  low_confidence: { label: 'Low confidence', mark: '▲' },
  refused: { label: "Can't classify", mark: '✕' },
} as const

const fmt = (v: number | null | undefined, n = 3) => (v == null ? '–' : v.toFixed(n))

interface Props {
  result: Result | null
  ready: boolean // both lines finished
  updating: boolean
  offline: boolean
  hand: HandMeasurement | null | undefined
  concealed?: boolean // during the construction: the class is revealed at the end
}

export function ClassCard({ result, ready, updating, offline, hand, concealed }: Props) {
  if (offline)
    return (
      <div className="class-card is-offline">
        <b>Can't reach the engine.</b> Start it with <code>app/run.sh</code>; tracing still works and the result appears once it's running.
      </div>
    )

  if (!ready || !result)
    return (
      <div className="class-card is-waiting">
        <div className="class-card-ghost">{ready ? <div className="spinner" /> : '?'}</div>
        <p>{ready ? 'Measuring…' : 'Trace both edges of one bed to see its class.'}</p>
      </div>
    )

  if (concealed)
    return (
      <div className="class-card is-waiting is-concealed">
        <div className="class-card-ghost">?</div>
        <p>Watch the construction: the class is revealed once the points are fitted.</p>
      </div>
    )

  const v = VERDICT[result.verdict]
  const o = result.overall
  const limbs = (['left', 'right'] as const).filter((l) => result.limbs[l])
  const limbClasses = limbs.map((l) => result.limbs[l]!.fold_class ?? '?')
  const big = result.verdict === 'refused' ? '—' : o?.fold_class ?? [...new Set(limbClasses)].join(' / ')
  const meaning = o?.fold_class ? CLASS_MEANING[o.fold_class] : result.verdict === 'refused' ? null : 'The two limbs fall in different classes.'
  const agrees = hand && o?.fold_class ? hand.fold_class === o.fold_class : null

  return (
    <div className={`class-card is-${result.verdict}${updating ? ' is-updating' : ''}${concealed === false ? ' is-revealed' : ''}`}>
      <div className="class-card-head">
        <div className="class-big">{big}</div>
        <div className="class-head-text">
          <span className="verdict">
            <span className="verdict-mark">{v.mark}</span> {v.label} <Help term="confidence" />
          </span>
          {meaning && (
            <span className="class-meaning">
              {meaning} <Help term="classes" />
            </span>
          )}
        </div>
        {updating && <div className="spinner spinner-sm" />}
      </div>

      {result.verdict !== 'refused' && o && (
        <>
          <div className="class-r mono">
            R <b>{fmt(o.R)}</b>
            <span className="class-sigma"> ± {fmt(o.sigma_R)}</span> <Help term="R" />
          </div>
          <div className="class-limbs">
            {limbs.map((l) => {
              const lr = result.limbs[l]!
              return (
                <span key={l} className="class-limb">
                  <span className="class-limb-name">{l === 'left' ? 'Left limb' : 'Right limb'}</span>
                  <span className="mono">
                    {lr.fold_class ?? '?'} · R {fmt(lr.R)}
                  </span>
                </span>
              )
            })}
          </div>
        </>
      )}

      {result.reasons.length > 0 && (
        <ul className={`class-reasons${result.verdict === 'refused' ? ' is-refused' : ''}`}>
          {result.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      {result.notes.length > 0 && (
        <ul className="class-notes">
          {result.notes.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}

      {hand && result.verdict !== 'refused' && (
        <div className="class-hand">
          <span>
            Hand measurement <span className="mono">R {hand.R.toFixed(2)} · {hand.fold_class}</span>
          </span>
          {agrees != null && <span className={`agree ${agrees ? 'is-yes' : 'is-no'}`}>{agrees ? '✓ agrees' : '≠ differs'}</span>}
        </div>
      )}
    </div>
  )
}
