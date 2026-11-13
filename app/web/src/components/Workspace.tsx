import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import type { Anchor, Doc, LineKey, Paths, Pt, Result } from '../types'
import { Canvas, type Tool } from './Canvas'
import { IconImage, Logo } from './Icons'
import { Panel } from './Panel'

interface Props {
  doc: Doc
  paths: Paths
  angles: number[]
  engine: string
  onPaths: (key: LineKey, anchors: Anchor[]) => void
  onAngles: (a: number[]) => void
  onFile: (f: File) => void
  onHome: () => void
  onPhotoSize: (w: number, h: number) => void
}

/** Remounted per photo (keyed by doc.url in App), so tracing state starts fresh. */
export function Workspace({ doc, paths, angles, engine, onPaths, onAngles, onFile, onHome, onPhotoSize }: Props) {
  // a line is "done" once finished with Done (examples arrive finished)
  const [done, setDone] = useState<Record<LineKey, boolean>>({ outer: paths.outer.length > 1, inner: paths.inner.length > 1 })
  const [active, setActive] = useState<LineKey>(done.outer ? (done.inner ? 'outer' : 'inner') : 'outer')
  const [tool, setTool] = useState<Tool>(done.outer && done.inner ? 'edit' : 'pen')
  const [cursor, setCursor] = useState<Pt | null>(null)
  const [zoom, setZoom] = useState(1)
  const input = useRef<HTMLInputElement>(null)

  // ---- live classification: once both lines are finished, every edit / angle change is measured.
  // While a request is out, newer edits wait and only the latest shape is sent next, so dragging
  // updates as fast as the engine answers without queueing stale requests.
  const [result, setResult] = useState<Result | null>(null)
  const [updating, setUpdating] = useState(false)
  const [offline, setOffline] = useState(false)
  const ready = done.outer && done.inner && paths.outer.length > 1 && paths.inner.length > 1
  const latest = useRef({ paths, angles, ready })
  latest.current = { paths, angles, ready }
  const inflight = useRef(false)
  const pending = useRef(false)

  const measure = useCallback(() => {
    if (inflight.current) {
      pending.current = true
      return
    }
    inflight.current = true
    setUpdating(true)
    const { paths: p, angles: a } = latest.current
    api
      .classify(p, a)
      .then(
        (r) => {
          if (latest.current.ready) setResult(r)
          setOffline(false)
        },
        () => setOffline(true),
      )
      .finally(() => {
        inflight.current = false
        if (pending.current && latest.current.ready) {
          pending.current = false
          measure()
        } else {
          pending.current = false
          setUpdating(false)
        }
      })
  }, [])

  useEffect(() => {
    if (ready) measure()
    else setResult(null)
  }, [ready, paths, angles, measure])

  const finish = () => {
    if (paths[active].length < 2) return
    const next = { ...done, [active]: true }
    setDone(next)
    if (!next.outer) setActive('outer')
    else if (!next.inner) setActive('inner')
    else setTool('edit')
  }

  const undoPoint = () => {
    const line = paths[active]
    if (!line.length) return
    onPaths(active, line.slice(0, -1))
    setDone({ ...done, [active]: false }) // removing a point reopens the line
    setTool('pen')
  }

  const clear = () => {
    onPaths(active, [])
    setDone({ ...done, [active]: false })
    setTool('pen')
  }

  const pickStep = (key: LineKey) => {
    setActive(key)
    setTool(done[key] ? 'edit' : 'pen')
  }

  const drawing = !done[active]
  const name = active === 'outer' ? 'outer' : 'inner'
  const hint = (() => {
    if (tool === 'pan') return 'Drag to move around the photo. Scroll to zoom.'
    if (tool === 'pen' && drawing) {
      const n = paths[active].length
      if (n === 0) return `Click on the ${name} edge of one bed, starting at one end. Drag while clicking to bend the curve.`
      if (n < 3) return `Keep clicking along the ${name} edge, past the hinge and down the other limb.`
      return `Click the last point again, or press Done, to finish the ${name} line.`
    }
    if (tool === 'pen') return 'Both lines are finished. Use Edit to adjust them, or Clear a line to redraw it.'
    return 'Drag a point to move it, or a handle to bend the curve. Hold Alt to bend one side only.'
  })()

  return (
    <div className="ws">
      <header className="topbar">
        <button className="brand brand-btn" onClick={onHome} title="Back to start">
          <Logo />
          <span className="brand-name">IsoFold Trace</span>
        </button>
        <span className="crumb">
          <span className="crumb-sep">/</span>
          {doc.name}
          {doc.example && <span className="crumb-tag">{doc.example.locality}</span>}
        </span>
        <div className="topbar-actions">
          <button className="btn" onClick={() => input.current?.click()}>
            <IconImage /> New photo
          </button>
          <button className="btn" onClick={onHome}>
            Examples
          </button>
          <input
            ref={input}
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) onFile(f)
              e.target.value = ''
            }}
          />
        </div>
      </header>

      <Canvas
        doc={doc}
        paths={paths}
        done={done}
        active={active}
        tool={tool}
        result={result}
        onTool={setTool}
        onPaths={onPaths}
        onFinish={finish}
        onActive={setActive}
        onCursor={setCursor}
        onZoom={setZoom}
        onPhotoSize={onPhotoSize}
      />

      <Panel
        doc={doc}
        paths={paths}
        done={done}
        active={active}
        angles={angles}
        result={result}
        updating={updating}
        offline={offline}
        onAngles={onAngles}
        onStep={pickStep}
        onUndo={undoPoint}
        onClear={clear}
        onDone={finish}
      />

      <footer className="statusbar">
        <span className="status-hint">{hint}</span>
        <span className="status-right">
          <span className="mono">{cursor ? `x ${Math.round(cursor[0])}  y ${Math.round(cursor[1])}` : `${doc.width} × ${doc.height} px`}</span>
          <span className="mono">{Math.round(zoom * 100)}%</span>
          <span>
            engine <span className="mono">{engine}</span>
          </span>
        </span>
      </footer>
    </div>
  )
}
