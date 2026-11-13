import { useEffect, useRef, useState } from 'react'
import type { Doc, LineKey, Paths, Result } from '../types'
import { angleColor, inFitRange } from '../geometry'
import { IconCheck, IconInfo, IconPlay, IconPlus, IconTrash, IconUndo, IconX } from './Icons'
import { RamsayChart } from './RamsayChart'
import { ClassCard } from './ClassCard'
import { RScale } from './RScale'
import { AngleTable } from './AngleTable'

interface Props {
  doc: Doc
  paths: Paths
  done: Record<LineKey, boolean>
  active: LineKey
  angles: number[]
  result: Result | null
  updating: boolean
  offline: boolean
  onAngles: (a: number[]) => void
  onStep: (key: LineKey) => void
  onUndo: () => void
  onClear: () => void
  onDone: () => void
  reveal: { shown: Set<string>; current?: string; showFit: boolean; concealClass: boolean } | null
  constructing: boolean
  onConstruction: () => void
}

export function Panel({ doc, paths, done, active, angles, result, updating, offline, onAngles, onStep, onUndo, onClear, onDone, reveal, constructing, onConstruction }: Props) {
  const both = done.outer && done.inner
  const line = paths[active]
  const hand = doc.example?.hand
  const live = both && result && result.verdict !== 'refused' ? result : null
  // bring the chart into view when the construction starts, so it can be watched filling in
  const chartRef = useRef<HTMLElement>(null)
  useEffect(() => {
    if (constructing) chartRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [constructing])

  return (
    <aside className="panel">
      <section className="panel-section">
        <ol className="steps">
          <Step n={1} label="Outer line" sub={stepSub(paths.outer.length, done.outer)} color="var(--outer)" done={done.outer} active={active === 'outer' && !both} selected={active === 'outer'} onClick={() => onStep('outer')} />
          <Step n={2} label="Inner line" sub={stepSub(paths.inner.length, done.inner)} color="var(--inner)" done={done.inner} active={active === 'inner' && !both} selected={active === 'inner'} onClick={() => onStep('inner')} />
          <Step n={3} label="Angles & result" sub={both ? 'drag any point to adjust' : 'after both lines'} done={false} active={both} />
        </ol>
        <div className="step-actions">
          <span className="step-actions-label">{active === 'outer' ? 'Outer' : 'Inner'} line:</span>
          <button className="btn btn-quiet btn-sm" onClick={onUndo} disabled={!line.length}>
            <IconUndo /> Undo point
          </button>
          <button className="btn btn-quiet btn-sm" onClick={onClear} disabled={!line.length}>
            <IconTrash /> Clear
          </button>
          {!done[active] && (
            <button className="btn btn-primary btn-sm" onClick={onDone} disabled={line.length < 2}>
              <IconCheck /> Done
            </button>
          )}
        </div>
      </section>

      <section className="panel-section">
        <h2 className="section-title">
          Dip angles
          <span className="hint" title="The class always uses the engine's full 20–70° grid. These angles only choose which isogons are drawn and listed.">
            <IconInfo width={14} height={14} /> display only
          </span>
        </h2>
        <AnglePicker angles={angles} onChange={onAngles} />
      </section>

      <section className="panel-section">
        <ClassCard result={result} ready={both} updating={updating} offline={offline} hand={hand} concealed={!!reveal?.concealClass} />
        {live && live.hinge && (
          <button className="btn btn-primary btn-construction" onClick={onConstruction} disabled={constructing}>
            <IconPlay width={15} height={15} /> {constructing ? 'Construction playing…' : 'Show construction'}
          </button>
        )}
        {hand && !(both && result && result.verdict !== 'refused') && (
          <div className="hand-card">
            <div className="hand-card-title">Hand measurement · {hand.label}</div>
            <div className="hand-card-value">
              R <b className="mono">{hand.R.toFixed(2)}</b> · Class <b>{hand.fold_class}</b>
            </div>
            <div className="hand-card-sub">measured in CorelDraw at {hand.angles.map((a) => Math.round(a) + '°').join(', ')}</div>
          </div>
        )}
      </section>

      {live && !reveal?.concealClass && (
        <section className="panel-section">
          <h2 className="section-title">Where R sits</h2>
          <RScale result={live} />
        </section>
      )}

      <section className="panel-section" ref={chartRef}>
        <h2 className="section-title">Ramsay diagram</h2>
        <RamsayChart result={live} hand={hand} reveal={reveal} />
      </section>

      {live && (
        <section className="panel-section">
          <h2 className="section-title">Isogons at your angles</h2>
          <AngleTable result={live} angles={angles} hand={hand} />
        </section>
      )}
    </aside>
  )
}

const stepSub = (n: number, done: boolean) => (done ? `${n} points · click to edit or redraw` : n ? `${n} point${n > 1 ? 's' : ''} so far` : 'not started')

interface StepProps {
  n: number
  label: string
  sub: string
  color?: string
  done: boolean
  active: boolean
  selected?: boolean
  onClick?: () => void
}

function Step({ n, label, sub, color, done, active, selected, onClick }: StepProps) {
  const cls = `step${active ? ' is-active' : ''}${done ? ' is-done' : ''}${selected ? ' is-selected' : ''}${onClick ? ' is-clickable' : ''}`
  return (
    <li className={cls} onClick={onClick}>
      <span className="step-num">{done ? <IconCheck width={14} height={14} /> : n}</span>
      <span className="step-text">
        <span className="step-label">{label}</span>
        <span className="step-sub">{sub}</span>
      </span>
      {color && <span className="step-swatch" style={{ background: color }} />}
    </li>
  )
}

/** "35" | "20, 30, 45" | "20-70/10" -> angles, or null if any part is not 0–89°. */
function parseAngles(text: string): number[] | null {
  const out: number[] = []
  for (const part of text.split(/[,\s]+/).filter(Boolean)) {
    const range = part.match(/^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(?:\/(\d+(?:\.\d+)?))?$/)
    if (range) {
      const [a, b, step] = [Number(range[1]), Number(range[2]), Number(range[3] ?? 10)]
      if (step <= 0 || b < a) return null
      for (let v = a; v <= b + 1e-9; v += step) out.push(Math.round(v * 100) / 100)
    } else if (/^\d+(\.\d+)?$/.test(part)) out.push(Number(part))
    else return null
  }
  return out.length && out.every((a) => a >= 0 && a < 90) ? out : null
}

const PRESETS: { label: string; angles: number[] }[] = [
  { label: '20 · 40 · 60', angles: [20, 40, 60] },
  { label: 'Every 10°', angles: [10, 20, 30, 40, 50, 60, 70] },
  { label: 'Ramsay 20–70', angles: [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70] },
]

function AnglePicker({ angles, onChange }: { angles: number[]; onChange: (a: number[]) => void }) {
  const [adding, setAdding] = useState(false)
  const [text, setText] = useState('')
  const [bad, setBad] = useState(false)

  const add = () => {
    const parsed = parseAngles(text)
    if (!parsed) {
      setBad(true)
      setTimeout(() => setBad(false), 400)
      return
    }
    onChange([...new Set([...angles, ...parsed])].sort((a, b) => a - b))
    setText('')
    setAdding(false)
  }

  return (
    <div className="angles">
      <div className="chips">
        {angles.map((a) => (
          <span
            key={a}
            className={`chip${inFitRange(a) ? '' : ' is-display-only'}`}
            style={{ ['--chip' as string]: angleColor(a) }}
            title={inFitRange(a) ? undefined : 'Shown on the photo but not used in the fit (outside 20–70°)'}
          >
            <span className="chip-dot" />
            {a}°
            <button className="chip-x" aria-label={`Remove ${a}°`} onClick={() => onChange(angles.filter((v) => v !== a))}>
              <IconX width={12} height={12} />
            </button>
          </span>
        ))}
        {adding ? (
          <input
            autoFocus
            className={`chip-input${bad ? ' is-bad' : ''}`}
            placeholder="35 or 20-70/10"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') add()
              if (e.key === 'Escape') setAdding(false)
            }}
            onBlur={() => (text ? add() : setAdding(false))}
          />
        ) : (
          <button className="chip chip-add" onClick={() => setAdding(true)} aria-label="Add angles">
            <IconPlus width={14} height={14} />
          </button>
        )}
      </div>
      {bad && <div className="field-error">Angles must be 0–89°, e.g. 35, or 20, 30, 45, or 20-70/10</div>}
      <div className="presets">
        {PRESETS.map((p) => (
          <button key={p.label} className="btn btn-chip" onClick={() => onChange(p.angles)}>
            {p.label}
          </button>
        ))}
      </div>
    </div>
  )
}
