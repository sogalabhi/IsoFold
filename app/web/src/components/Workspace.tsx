import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api'
import type { Anchor, Doc, LineKey, Paths, Pt, Result } from '../types'
import { Canvas, type Tool } from './Canvas'
import { IconImage, Logo } from './Icons'
import { Panel } from './Panel'
import { Player } from './Player'
import { buildTimeline, frameAt, isoKey, type Timeline } from '../construction'

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

  // ---- "Show construction": replays the hand method from a snapshot of the current result
  const [show, setShow] = useState<{ result: Result; tl: Timeline } | null>(null)
  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)

  const startConstruction = () => {
    if (!result || result.verdict === 'refused' || !result.hinge) return
    setShow({ result, tl: buildTimeline(result, angles) })
    setT(0)
    setPlaying(true)
  }

  useEffect(() => {
    if (!show || !playing) return
    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      const dt = now - last
      last = now
      setT((prev) => {
        const n = prev + dt * speed
        if (n >= show.tl.total) {
          setPlaying(false)
          return show.tl.total
        }
        return n
      })
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [show, playing, speed])

  const frame = show ? frameAt(show.tl, t) : null
  const stepBy = (delta: number) => {
    if (!show || !frame) return
    const { starts, total } = show.tl
    if (delta > 0) setT(frame.i + 1 < starts.length ? starts[frame.i + 1] : total)
    else setT(starts[frame.u > 0.15 ? frame.i : Math.max(0, frame.i - 1)])
  }

  // what the panel reveals as the construction goes: chosen points one by one, the fit and class at the end
  const reveal = useMemo(() => {
    if (!show || !frame) return null
    const step = show.tl.steps[frame.i]
    const cur = step.order ?? (step.kind === 'fit' ? show.tl.isogons.length : -1)
    const shown = new Set(show.tl.isogons.filter((_, o) => o < cur || (o === cur && step.kind === 'plot')).map(isoKey))
    return {
      shown,
      current: step.kind === 'plot' && step.iso ? isoKey(step.iso) : undefined,
      showFit: step.kind === 'fit',
      concealClass: !(step.kind === 'fit' && frame.u > 0.55),
    }
  }, [show, frame?.i, frame?.u])

  // frame where the construction happens: the hinge points and the isogons being built
  const focus = useMemo(() => {
    if (!show?.result.hinge) return null
    const all = [show.result.hinge.H, show.result.hinge.G, ...show.tl.isogons.flatMap((i) => [i.p, i.q])]
    const xs = all.map((p) => p[0])
    const ys = all.map((p) => p[1])
    const pad = 0.25 * Math.hypot(...([0, 1].map((j) => show.result.hinge!.H[j] - show.result.hinge!.G[j]) as [number, number]))
    return [Math.min(...xs) - pad, Math.min(...ys) - pad, Math.max(...xs) + pad, Math.max(...ys) + pad] as [number, number, number, number]
  }, [show])

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
        construction={show && frame ? { result: show.result, tl: show.tl, frame } : null}
        focus={focus}
        onTool={setTool}
        onPaths={onPaths}
        onFinish={finish}
        onActive={setActive}
        onCursor={setCursor}
        onZoom={setZoom}
        onPhotoSize={onPhotoSize}
      >
        {show && frame && (
          <Player
            tl={show.tl}
            frame={frame}
            playing={playing}
            speed={speed}
            onPlay={() => {
              if (t >= show.tl.total) setT(0)
              setPlaying(true)
            }}
            onPause={() => setPlaying(false)}
            onStep={stepBy}
            onRestart={() => setT(0)}
            onEnd={() => {
              setPlaying(false)
              setT(show.tl.total)
            }}
            onSpeed={() => setSpeed((v) => (v === 1 ? 2 : v === 2 ? 0.5 : 1))}
            onClose={() => {
              setShow(null)
              setPlaying(false)
            }}
          />
        )}
      </Canvas>

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
        reveal={reveal}
        constructing={!!show}
        onConstruction={startConstruction}
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
