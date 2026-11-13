import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { Anchor, Doc, LineKey, Paths, Pt, Result } from '../types'
import { pathD } from '../geometry'
import { IconCheck, IconFit, IconHand, IconMinus, IconPen, IconPlus, IconPointer } from './Icons'
import { ResultOverlay } from './ResultOverlay'
import { ConstructionOverlay } from './ConstructionOverlay'
import type { Frame, Timeline } from '../construction'

export type Tool = 'pen' | 'edit' | 'pan'

interface View {
  s: number // screen px per image px
  x: number // screen position of image (0,0)
  y: number
}

/** What is under the pointer: an anchor, or one of its handles. */
type Hit = { key: LineKey; idx: number; part: 'p' | 'in' | 'out' }

/** What the current pointer drag is doing. */
type Drag =
  | { mode: 'pan'; x: number; y: number; vx: number; vy: number }
  | { mode: 'pull'; key: LineKey; idx: number; start: Pt; sx: number; sy: number } // pen: new anchor, pulling its handles
  | { mode: 'move'; hit: Hit; start: Pt; anchor: Anchor }

interface Props {
  doc: Doc
  paths: Paths
  done: Record<LineKey, boolean>
  active: LineKey
  tool: Tool
  result: Result | null
  construction: { result: Result; tl: Timeline; frame: Frame } | null
  focus: [number, number, number, number] | null
  children?: React.ReactNode
  onTool: (t: Tool) => void
  onPaths: (key: LineKey, anchors: Anchor[]) => void
  onFinish: () => void
  onActive: (key: LineKey) => void
  onCursor: (p: Pt | null) => void
  onZoom: (s: number) => void
  onPhotoSize: (w: number, h: number) => void
}

const MAX_ZOOM = 8
const FIT_PAD = 28
const FIT_LEFT = 96 // keep the fitted photo clear of the tool palette
const HIT_PX = 10 // pick radius around anchors and handles, in screen px
const PULL_PX = 3 // a pen click that moves less than this places a sharp point
const KEYS: LineKey[] = ['outer', 'inner']

const sub = (a: Pt, b: Pt): Pt => [a[0] - b[0], a[1] - b[1]]
const add = (a: Pt, b: Pt): Pt => [a[0] + b[0], a[1] + b[1]]
const len = (a: Pt) => Math.hypot(a[0], a[1])

export function Canvas(props: Props) {
  const { doc, paths, done, active, result, construction, focus, children, onTool, onPaths, onFinish, onActive, onCursor, onZoom, onPhotoSize } = props
  const box = useRef<HTMLDivElement>(null)
  const [view, setView] = useState<View | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [animate, setAnimate] = useState(false)
  const [drag, setDrag] = useState<Drag | null>(null)
  const [hover, setHover] = useState<Hit | null>(null)
  const [selected, setSelected] = useState<{ key: LineKey; idx: number } | null>(null)
  const [cursor, setCursorPt] = useState<Pt | null>(null)
  const [labels, setLabels] = useState(true)
  const fitted = useRef(true) // still showing the "fit" view: keep fitting when the window resizes

  // while the construction plays the canvas only pans
  const tool: Tool = construction ? 'pan' : props.tool
  const drawing: LineKey | null = done[active] ? null : active // the line the pen adds to

  // ---------------------------------------------------------------- view: fit, zoom, pan

  const fitView = useCallback((): View | null => {
    const el = box.current
    if (!el) return null
    const { width: cw, height: ch } = el.getBoundingClientRect()
    const s = Math.min((cw - FIT_LEFT - FIT_PAD) / doc.width, (ch - 2 * FIT_PAD) / doc.height)
    return { s, x: FIT_LEFT + (cw - FIT_LEFT - FIT_PAD - doc.width * s) / 2, y: (ch - doc.height * s) / 2 }
  }, [doc.width, doc.height])

  const fit = useCallback(
    (smooth = false) => {
      const v = fitView()
      if (!v) return
      fitted.current = true
      setAnimate(smooth)
      setView(v)
    },
    [fitView],
  )

  useLayoutEffect(() => {
    setLoaded(false)
    setSelected(null)
    fit()
  }, [doc.url, fit])

  useEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(() => fitted.current && fit())
    ro.observe(el)
    return () => ro.disconnect()
  }, [fit])

  useEffect(() => {
    if (view) onZoom(view.s)
  }, [view, onZoom])

  // zoom to a box (image px) with some margin, e.g. the fold while the construction plays
  useEffect(() => {
    const el = box.current
    if (!focus || !el) return
    const [x0, y0, x1, y1] = focus
    const mx = (x1 - x0) * 0.25
    const my = (y1 - y0) * 0.25
    const bw = x1 - x0 + 2 * mx
    const bh = y1 - y0 + 2 * my
    const { width: cw, height: ch } = el.getBoundingClientRect()
    const availH = ch - 2 * FIT_PAD - 150 // keep clear of the player at the bottom
    const s = Math.min(MAX_ZOOM, (cw - FIT_LEFT - FIT_PAD) / bw, availH / bh)
    fitted.current = false
    setAnimate(true)
    setView({ s, x: FIT_LEFT + (cw - FIT_LEFT - FIT_PAD - bw * s) / 2 - (x0 - mx) * s, y: FIT_PAD + (availH - bh * s) / 2 - (y0 - my) * s })
  }, [focus])

  const zoomAt = useCallback(
    (factor: number, mx: number, my: number, smooth: boolean) => {
      setView((v) => {
        if (!v) return v
        const minS = (fitView()?.s ?? v.s) * 0.5
        const s = Math.min(MAX_ZOOM, Math.max(minS, v.s * factor))
        const k = s / v.s
        fitted.current = false
        setAnimate(smooth)
        return { s, x: mx - (mx - v.x) * k, y: my - (my - v.y) * k }
      })
    },
    [fitView],
  )

  useEffect(() => {
    const el = box.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const r = el.getBoundingClientRect()
      const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY
      zoomAt(Math.exp(-dy * 0.0015), e.clientX - r.left, e.clientY - r.top, false)
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [zoomAt])

  const zoomCenter = (factor: number) => {
    const r = box.current!.getBoundingClientRect()
    zoomAt(factor, r.width / 2, r.height / 2, true)
  }

  // ---------------------------------------------------------------- pointer → image coordinates, hit testing

  const toImage = (e: { clientX: number; clientY: number }): Pt | null => {
    if (!view || !box.current) return null
    const r = box.current.getBoundingClientRect()
    return [(e.clientX - r.left - view.x) / view.s, (e.clientY - r.top - view.y) / view.s]
  }

  const k = view ? 1 / view.s : 1 // image px per screen px: overlay sizes stay constant on screen

  /** Which anchors are pickable / visible with the current tool. */
  const editableKeys: LineKey[] = tool === 'edit' ? KEYS.filter((key) => paths[key].length > 0) : tool === 'pen' && drawing ? [drawing] : []

  /** Handles are shown for the selected anchor (Edit) or the newest anchor of the line being drawn (Pen). */
  const handleOwner: { key: LineKey; idx: number } | null =
    tool === 'edit' ? selected : tool === 'pen' && drawing && paths[drawing].length ? { key: drawing, idx: paths[drawing].length - 1 } : null

  const hitTest = (pt: Pt): Hit | null => {
    const r = HIT_PX * k
    let best: Hit | null = null
    let bestD = r
    if (handleOwner) {
      const a = paths[handleOwner.key][handleOwner.idx]
      for (const part of ['in', 'out'] as const) {
        const h = a?.[part]
        if (h && len(sub(h, pt)) < bestD) {
          bestD = len(sub(h, pt))
          best = { ...handleOwner, part }
        }
      }
      if (best) return best // handles win over anchors
    }
    for (const key of editableKeys) {
      paths[key].forEach((a, idx) => {
        const d = len(sub(a.p, pt))
        if (d < bestD) {
          bestD = d
          best = { key, idx, part: 'p' }
        }
      })
    }
    return best
  }

  // ---------------------------------------------------------------- editing

  const setAnchor = (key: LineKey, idx: number, a: Anchor) => onPaths(key, paths[key].map((old, i) => (i === idx ? a : old)))

  /** Move one part of an anchor. Moving a handle mirrors the opposite one (keeping its length) unless `free`. */
  const moveTo = (hit: Hit, orig: Anchor, delta: Pt, free: boolean) => {
    if (hit.part === 'p') {
      const shift = (h: Pt | null) => (h ? add(h, delta) : null)
      setAnchor(hit.key, hit.idx, { p: add(orig.p, delta), in: shift(orig.in), out: shift(orig.out) })
      return
    }
    const other = hit.part === 'in' ? 'out' : 'in'
    const h = add(orig[hit.part]!, delta)
    const next: Anchor = { ...orig, [hit.part]: h }
    const o = orig[other]
    if (!free && o) {
      const dir = sub(orig.p, h)
      const d = len(dir)
      if (d > 1e-6) next[other] = add(orig.p, [(dir[0] / d) * len(sub(o, orig.p)), (dir[1] / d) * len(sub(o, orig.p))])
    }
    setAnchor(hit.key, hit.idx, next)
  }

  const onPointerDown = (e: React.PointerEvent) => {
    if (!view) return
    const pt = toImage(e)!
    const capture = () => (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    const startPan = () => {
      e.preventDefault()
      capture()
      setDrag({ mode: 'pan', x: e.clientX, y: e.clientY, vx: view.x, vy: view.y })
    }
    if (tool === 'pan' || e.button === 1 || e.button === 2) return startPan()
    if (e.button !== 0) return

    const hit = hitTest(pt)
    if (tool === 'pen') {
      if (!drawing) return
      const line = paths[drawing]
      if (hit && hit.part !== 'p') {
        // grab a handle of the newest point to re-bend it
        capture()
        setDrag({ mode: 'move', hit, start: pt, anchor: line[hit.idx] })
        return
      }
      if (hit && hit.part === 'p' && hit.idx === line.length - 1 && line.length >= 2) {
        onFinish() // clicking the last point again finishes the line (so does a double-click)
        return
      }
      capture()
      onPaths(drawing, [...line, { p: pt, in: null, out: null }])
      setDrag({ mode: 'pull', key: drawing, idx: line.length, start: pt, sx: e.clientX, sy: e.clientY })
      return
    }

    // edit tool
    if (hit) {
      capture()
      if (hit.part === 'p') {
        setSelected({ key: hit.key, idx: hit.idx })
        if (hit.key !== active) onActive(hit.key)
      }
      setDrag({ mode: 'move', hit, start: pt, anchor: paths[hit.key][hit.idx] })
    } else {
      setSelected(null)
      startPan() // dragging empty space pans
    }
  }

  const onPointerMove = (e: React.PointerEvent) => {
    const pt = toImage(e)
    setCursorPt(pt)
    onCursor(pt && pt[0] >= 0 && pt[1] >= 0 && pt[0] <= doc.width && pt[1] <= doc.height ? pt : null)
    if (!pt) return

    if (!drag) {
      setHover(hitTest(pt))
      return
    }
    if (drag.mode === 'pan') {
      fitted.current = false
      setAnimate(false)
      setView((v) => v && { ...v, x: drag.vx + e.clientX - drag.x, y: drag.vy + e.clientY - drag.y })
    } else if (drag.mode === 'pull') {
      // pen click-and-drag: pull out symmetric handles; a tiny move keeps a sharp point
      const a = paths[drag.key][drag.idx]
      if (!a) return
      const pulled = Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) >= PULL_PX
      const d = sub(pt, drag.start)
      setAnchor(drag.key, drag.idx, pulled ? { p: drag.start, out: pt, in: sub(drag.start, d) } : { p: drag.start, in: null, out: null })
    } else {
      moveTo(drag.hit, drag.anchor, sub(pt, drag.start), e.altKey)
    }
  }

  const endDrag = () => setDrag(null)

  // ---------------------------------------------------------------- render

  const showResult = !!result && result.verdict !== 'refused' && !drawing && !construction
  const pulling = drag?.mode === 'pull'
  const last = drawing ? paths[drawing][paths[drawing].length - 1] : undefined
  const overLast = !!(drawing && hover?.part === 'p' && hover.key === drawing && hover.idx === paths[drawing].length - 1 && paths[drawing].length >= 2)
  const preview = tool === 'pen' && last && cursor && !pulling && !overLast && !drag

  const cursorStyle =
    drag?.mode === 'pan'
      ? 'grabbing'
      : drag
        ? 'move'
        : tool === 'pan'
          ? 'grab'
          : tool === 'pen'
            ? drawing
              ? overLast
                ? 'pointer'
                : hover
                  ? 'move'
                  : 'crosshair'
              : 'not-allowed'
            : hover
              ? 'move'
              : 'default'

  // floating Done button next to the newest point of the line being drawn
  const lastScreen = view && last ? [view.x + last.p[0] * view.s, view.y + last.p[1] * view.s] : null
  const showDone = tool === 'pen' && drawing && paths[drawing].length >= 2 && !drag && lastScreen

  return (
    <div
      ref={box}
      className="canvas"
      style={{ cursor: cursorStyle }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onPointerLeave={() => {
        onCursor(null)
        setCursorPt(null)
      }}
      onContextMenu={(e) => e.preventDefault()}
    >
      {view && (
        <div
          className={`canvas-layer${animate ? ' is-animated' : ''}`}
          style={{ width: doc.width, height: doc.height, transform: `translate(${view.x}px, ${view.y}px) scale(${view.s})` }}
        >
          <img
            key={doc.url}
            src={doc.url}
            alt={doc.name}
            draggable={false}
            className={`canvas-photo${loaded ? ' is-loaded' : ''}`}
            onLoad={(e) => {
              const im = e.currentTarget
              if (im.naturalWidth !== doc.width || im.naturalHeight !== doc.height) onPhotoSize(im.naturalWidth, im.naturalHeight)
              setLoaded(true)
            }}
          />
          <svg className="overlay" width={doc.width} height={doc.height} viewBox={`0 0 ${doc.width} ${doc.height}`}>
            {KEYS.map(
              (key) =>
                paths[key].length > 1 && (
                  <g key={key} className={(showResult && result?.cut) || construction ? 'is-faded' : ''}>
                    <path d={pathD(paths[key])} className="trace-halo" strokeWidth={6 * k} />
                    <path d={pathD(paths[key])} className={`trace trace-${key}`} strokeWidth={2.5 * k} />
                  </g>
                ),
            )}

            {construction && <rect x={0} y={0} width={doc.width} height={doc.height} className="photo-dim" />}
            {showResult && <ResultOverlay result={result!} k={k} labels={labels} />}
            {construction && <ConstructionOverlay result={construction.result} tl={construction.tl} frame={construction.frame} k={k} />}

            {preview && drawing && (
              <path
                d={pathD([last!, { p: cursor!, in: cursor!, out: null }])}
                className={`trace-preview trace-${drawing}`}
                strokeWidth={1.5 * k}
                strokeDasharray={`${6 * k} ${5 * k}`}
              />
            )}

            {handleOwner && <Handles anchor={paths[handleOwner.key][handleOwner.idx]} lineKey={handleOwner.key} k={k} hover={hover} owner={handleOwner} />}

            {editableKeys.map((key) =>
              paths[key].map((a, idx) => {
                const isHover = hover?.key === key && hover.idx === idx && hover.part === 'p'
                const isSel = handleOwner?.key === key && handleOwner.idx === idx
                const size = (isHover ? 13 : 10) * k
                return (
                  <rect
                    key={`${key}-${idx}`}
                    x={a.p[0] - size / 2}
                    y={a.p[1] - size / 2}
                    width={size}
                    height={size}
                    className={`anchor anchor-${key}${isSel ? ' is-selected' : ''}`}
                    strokeWidth={1.8 * k}
                  />
                )
              }),
            )}

            {overLast && last && <circle cx={last.p[0]} cy={last.p[1]} r={11 * k} className="finish-ring" strokeWidth={2 * k} />}
          </svg>
        </div>
      )}

      {/* the pen's colour tag, so it's obvious which line is being drawn */}
      {tool === 'pen' && drawing && cursor && view && !drag && (
        <div
          className={`pen-tag pen-tag-${drawing}`}
          style={{ left: view.x + cursor[0] * view.s + 12, top: view.y + cursor[1] * view.s + 12 }}
        >
          {overLast ? 'finish' : drawing}
        </div>
      )}

      {showDone && (
        <button
          className="float-done"
          style={{ left: lastScreen![0] + 16, top: lastScreen![1] - 44 }}
          onPointerDown={(e) => e.stopPropagation()}
          onClick={onFinish}
        >
          <IconCheck width={14} height={14} /> Done
        </button>
      )}

      {children}

      {!loaded && (
        <div className="canvas-loading">
          <div className="spinner" />
          <span>Loading photo…</span>
        </div>
      )}

      <div className="tool-palette" onPointerDown={(e) => e.stopPropagation()}>
        <ToolButton label="Pen" active={tool === 'pen'} onClick={() => onTool('pen')}>
          <IconPen />
        </ToolButton>
        <ToolButton label="Edit" active={tool === 'edit'} onClick={() => onTool('edit')}>
          <IconPointer />
        </ToolButton>
        <ToolButton label="Pan" active={tool === 'pan'} onClick={() => onTool('pan')}>
          <IconHand />
        </ToolButton>
      </div>

      <div className="zoom-bar" onPointerDown={(e) => e.stopPropagation()}>
        <button className="icon-btn" title="Zoom out" onClick={() => zoomCenter(1 / 1.4)}>
          <IconMinus />
        </button>
        <button className="zoom-readout" title="Fit photo to screen" onClick={() => fit(true)}>
          {view ? Math.round(view.s * 100) : 100}%
        </button>
        <button className="icon-btn" title="Zoom in" onClick={() => zoomCenter(1.4)}>
          <IconPlus />
        </button>
        <span className="zoom-sep" />
        <button className={`zoom-labels${labels ? ' is-on' : ''}`} title="Show or hide point labels" onClick={() => setLabels((v) => !v)} aria-pressed={labels}>
          Labels {labels ? 'on' : 'off'}
        </button>
        <span className="zoom-sep" />
        <button className="icon-btn" title="Fit photo to screen" onClick={() => fit(true)}>
          <IconFit />
        </button>
      </div>
    </div>
  )
}

function Handles({ anchor, lineKey, k, hover, owner }: { anchor?: Anchor; lineKey: LineKey; k: number; hover: Hit | null; owner: { key: LineKey; idx: number } }) {
  if (!anchor) return null
  return (
    <g className={`handles handles-${lineKey}`}>
      {(['in', 'out'] as const).map((part) => {
        const h = anchor[part]
        if (!h) return null
        const isHover = hover?.key === owner.key && hover.idx === owner.idx && hover.part === part
        return (
          <g key={part}>
            <line x1={anchor.p[0]} y1={anchor.p[1]} x2={h[0]} y2={h[1]} className="handle-line" strokeWidth={1.2 * k} />
            <circle cx={h[0]} cy={h[1]} r={(isHover ? 6.5 : 4.5) * k} className="handle-dot" strokeWidth={1.5 * k} />
          </g>
        )
      })}
    </g>
  )
}

function ToolButton({ label, active, onClick, children }: { label: string; active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button className={`tool-btn${active ? ' is-active' : ''}`} onClick={onClick} aria-pressed={active}>
      {children}
      <span>{label}</span>
    </button>
  )
}
