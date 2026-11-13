import { useRef, useState } from 'react'
import type { Doc, Paths, Pt } from '../types'
import { Canvas, type Tool } from './Canvas'
import { IconImage, Logo } from './Icons'
import { Panel } from './Panel'

interface Props {
  doc: Doc
  paths: Paths
  angles: number[]
  engine: string
  onAngles: (a: number[]) => void
  onFile: (f: File) => void
  onHome: () => void
  onPhotoSize: (w: number, h: number) => void
}

export function Workspace({ doc, paths, angles, engine, onAngles, onFile, onHome, onPhotoSize }: Props) {
  const [tool, setTool] = useState<Tool>(paths.outer.length ? 'pan' : 'pen')
  const [cursor, setCursor] = useState<Pt | null>(null)
  const [zoom, setZoom] = useState(1)
  const input = useRef<HTMLInputElement>(null)

  const hint =
    paths.outer.length < 2
      ? 'Click along the outer edge of one bed. Drag while clicking to bend the curve.'
      : paths.inner.length < 2
        ? 'Now trace the inner edge of the same bed.'
        : 'Drag any point to adjust; the class updates live.'

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

      <Canvas doc={doc} paths={paths} tool={tool} onTool={setTool} onCursor={setCursor} onZoom={setZoom} onPhotoSize={onPhotoSize} />

      <Panel doc={doc} paths={paths} angles={angles} onAngles={onAngles} />

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
