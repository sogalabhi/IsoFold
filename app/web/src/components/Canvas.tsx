import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { Doc, Paths, Pt } from '../types'
import { pathD } from '../geometry'
import { IconFit, IconHand, IconMinus, IconPen, IconPlus, IconPointer } from './Icons'

export type Tool = 'pen' | 'edit' | 'pan'

interface View {
  s: number // screen px per image px
  x: number // screen position of image (0,0)
  y: number
}

interface Props {
  doc: Doc
  paths: Paths
  tool: Tool
  onTool: (t: Tool) => void
  onCursor: (p: Pt | null) => void
  onZoom: (s: number) => void
  onPhotoSize: (w: number, h: number) => void
}

const MAX_ZOOM = 8
const FIT_PAD = 28
const FIT_LEFT = 96 // keep the fitted photo clear of the tool palette

export function Canvas({ doc, paths, tool, onTool, onCursor, onZoom, onPhotoSize }: Props) {
  const box = useRef<HTMLDivElement>(null)
  const [view, setView] = useState<View | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [animate, setAnimate] = useState(false)
  const [panning, setPanning] = useState(false)
  const fitted = useRef(true) // still showing the "fit" view: keep fitting when the window resizes
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null)

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

  // new photo: fit it, and refit on window resize while the user hasn't zoomed
  useLayoutEffect(() => {
    setLoaded(false)
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

  // wheel zoom around the cursor (non-passive so the page doesn't scroll)
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

  const toImage = (e: React.PointerEvent): Pt | null => {
    if (!view || !box.current) return null
    const r = box.current.getBoundingClientRect()
    return [(e.clientX - r.left - view.x) / view.s, (e.clientY - r.top - view.y) / view.s]
  }

  const onPointerDown = (e: React.PointerEvent) => {
    // pan with the Pan tool, or the middle / right mouse button with any tool
    if (!view || !(tool === 'pan' || e.button === 1 || e.button === 2)) return
    e.preventDefault()
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y }
    setPanning(true)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    const d = drag.current
    if (d) {
      fitted.current = false
      setAnimate(false)
      setView((v) => v && { ...v, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y })
    }
    const p = toImage(e)
    onCursor(p && p[0] >= 0 && p[1] >= 0 && p[0] <= doc.width && p[1] <= doc.height ? p : null)
  }

  const endPan = () => {
    drag.current = null
    setPanning(false)
  }

  const k = view ? 1 / view.s : 1 // image px per screen px: keeps overlay strokes a constant on-screen size
  const cursor = panning ? 'grabbing' : tool === 'pan' ? 'grab' : tool === 'pen' ? 'crosshair' : 'default'

  return (
    <div
      ref={box}
      className="canvas"
      style={{ cursor }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endPan}
      onPointerCancel={endPan}
      onPointerLeave={() => onCursor(null)}
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
            {(['outer', 'inner'] as const).map(
              (key) =>
                paths[key].length > 1 && (
                  <g key={key}>
                    <path d={pathD(paths[key])} className="trace-halo" strokeWidth={6 * k} />
                    <path d={pathD(paths[key])} className={`trace trace-${key}`} strokeWidth={2.5 * k} />
                  </g>
                ),
            )}
          </svg>
        </div>
      )}

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
        <button className="icon-btn" title="Fit photo to screen" onClick={() => fit(true)}>
          <IconFit />
        </button>
      </div>
    </div>
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
