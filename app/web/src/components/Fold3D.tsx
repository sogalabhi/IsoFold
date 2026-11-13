// 3D block diagram of the traced bed. ILLUSTRATION: assumes a cylindrical fold, i.e. the traced profile is
// carried unchanged along the fold axis (perpendicular to the photo). The photo is the front face of the block;
// hinge lines, the axial plane and the isogon planes are the 2D construction extended along the axis.
import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CSS2DObject, CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import type { Doc, Pt, Result } from '../types'
import { angleColor } from '../geometry'
import { IconX } from './Icons'

interface Props {
  result: Result
  doc: Doc
  title: string
  onClose: () => void
}

interface Toggles {
  photo: boolean
  isogons: boolean
  axial: boolean
  labels: boolean
}

const STONE = 0xcbb592
const OUTER = 0xd9412a
const INNER = 0x1e66c4
const INK = 0x1f1c17

function dispose(o: THREE.Object3D) {
  o.traverse((c) => {
    const m = c as THREE.Mesh
    m.geometry?.dispose()
    const mat = m.material as THREE.Material | THREE.Material[] | undefined
    if (Array.isArray(mat)) mat.forEach((x) => x.dispose())
    else if (mat) {
      ;(mat as THREE.MeshStandardMaterial).map?.dispose()
      mat.dispose()
    }
    if (c instanceof CSS2DObject) c.element.remove()
  })
}

function label(text: string, cls = '') {
  const el = document.createElement('div')
  el.className = `l3d ${cls}`
  el.textContent = text
  return new CSS2DObject(el)
}

export function Fold3D({ result, doc, title, onClose }: Props) {
  const mount = useRef<HTMLDivElement>(null)
  const three = useRef<{
    scene: THREE.Scene
    camera: THREE.PerspectiveCamera
    controls: OrbitControls
    pivot: THREE.Group
    home: (span?: number) => void
  } | null>(null)
  const span = useRef(20) // size of the block, for framing the camera
  const parts = useRef<{ photo?: THREE.Object3D; front?: THREE.Object3D; isogons?: THREE.Object3D; axial?: THREE.Object3D; labels: CSS2DObject[] }>({ labels: [] })
  const [depthFactor, setDepthFactor] = useState(0.9)
  const [plunge, setPlunge] = useState(0)
  const [trend, setTrend] = useState(0)
  const [tg, setTg] = useState<Toggles>({ photo: true, isogons: true, axial: true, labels: true })

  // ---- renderer, camera, controls, lights (once)
  useEffect(() => {
    const el = mount.current!
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    el.appendChild(renderer.domElement)
    const labels = new CSS2DRenderer()
    labels.domElement.className = 'l3d-layer'
    el.appendChild(labels.domElement)

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf4f1ea)
    scene.add(new THREE.HemisphereLight(0xffffff, 0xb9ab92, 1.6))
    const sun = new THREE.DirectionalLight(0xffffff, 1.7)
    sun.position.set(6, 12, 9)
    scene.add(sun)
    const grid = new THREE.GridHelper(40, 40, 0xc7bead, 0xddd6c8)
    grid.position.y = -7
    scene.add(grid)
    const north = label('N ↑ (axis trend 0°)', 'l3d-muted')
    north.position.set(0, -7, -19)
    scene.add(north)

    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 500)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    const pivot = new THREE.Group()
    scene.add(pivot)
    // three-quarter view from the front-right, far enough to see the whole block
    const home = (sz = span.current) => {
      camera.position.set(0.95 * sz, 0.6 * sz, 1.25 * sz)
      controls.target.set(0, -0.5, 0)
      controls.update()
    }
    home()

    const resize = () => {
      const { width, height } = el.getBoundingClientRect()
      renderer.setSize(width, height)
      labels.setSize(width, height)
      camera.aspect = width / Math.max(1, height)
      camera.updateProjectionMatrix()
    }
    const ro = new ResizeObserver(resize)
    ro.observe(el)
    resize()
    renderer.setAnimationLoop(() => {
      controls.update()
      renderer.render(scene, camera)
      labels.render(scene, camera)
    })
    three.current = { scene, camera, controls, pivot, home }
    return () => {
      renderer.setAnimationLoop(null)
      ro.disconnect()
      controls.dispose()
      dispose(scene)
      renderer.dispose()
      el.innerHTML = ''
      three.current = null
    }
  }, [])

  // ---- the block: rebuilt when the result or the axis length changes
  useEffect(() => {
    const t = three.current
    if (!t || !result.cut || !result.hinge) return
    for (const c of [...t.pivot.children]) {
      t.pivot.remove(c)
      dispose(c)
    }
    parts.current = { labels: [] }

    const { outer, inner } = result.cut
    const { H, G } = result.hinge
    const all: Pt[] = [...outer, ...inner]
    const xs = all.map((p) => p[0])
    const ys = all.map((p) => p[1])
    let [x0, y0, x1, y1] = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
    const m = 0.18 * Math.max(x1 - x0, y1 - y0)
    ;[x0, y0, x1, y1] = [Math.max(0, x0 - m), Math.max(0, y0 - m), Math.min(doc.width, x1 + m), Math.min(doc.height, y1 + m)]
    const bw = x1 - x0
    const bh = y1 - y0
    const cx = (x0 + x1) / 2
    const cy = (y0 + y1) / 2
    const s = 10 / Math.max(bw, bh)
    const D = depthFactor * 10 // axis length, world units
    const firstBuild = span.current === 20 && !(t.pivot.userData.built as boolean)
    span.current = Math.max(10, D) + 6
    t.pivot.userData.built = true
    if (firstBuild) t.home(span.current)
    const w = (p: Pt): [number, number] => [(p[0] - cx) * s, -(p[1] - cy) * s]

    // the block content sits in [z = 0 (photo face) … z = -D]; centre it on the pivot so tilting turns it in place
    const block = new THREE.Group()
    block.position.z = D / 2
    t.pivot.add(block)

    const ribbon = (line: Pt[], color: number) => {
      const pos: number[] = []
      const idx: number[] = []
      line.forEach((p, i) => {
        const [x, y] = w(p)
        pos.push(x, y, 0, x, y, -D)
        if (i > 0) idx.push(2 * i - 2, 2 * i - 1, 2 * i, 2 * i - 1, 2 * i + 1, 2 * i)
      })
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
      g.setIndex(idx)
      g.computeVertexNormals()
      return new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color, roughness: 0.85, side: THREE.DoubleSide }))
    }
    const quad = (a: Pt, b: Pt, mat: THREE.Material) => {
      const [ax, ay] = w(a)
      const [bx, by] = w(b)
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.Float32BufferAttribute([ax, ay, 0, bx, by, 0, ax, ay, -D, bx, by, -D], 3))
      g.setIndex([0, 2, 1, 1, 2, 3])
      g.computeVertexNormals()
      return new THREE.Mesh(g, mat)
    }
    const tube = (pts: THREE.Vector3[], color: number, r: number) =>
      new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), Math.max(8, pts.length), r, 6, false), new THREE.MeshStandardMaterial({ color, roughness: 0.6 }))

    // bed: outer surface (red), inner surface (blue), stone caps and limb ends
    const tint = (c: number) => new THREE.Color(c).lerp(new THREE.Color(STONE), 0.45).getHex()
    block.add(ribbon(outer, tint(OUTER)))
    block.add(ribbon(inner, tint(INNER)))
    const stone = new THREE.MeshStandardMaterial({ color: STONE, roughness: 0.95, side: THREE.DoubleSide })
    block.add(quad(outer[0], inner[0], stone))
    block.add(quad(outer[outer.length - 1], inner[inner.length - 1], stone))
    const shape = new THREE.Shape([...outer, ...[...inner].reverse()].map((p) => new THREE.Vector2(...w(p))))
    const back = new THREE.Mesh(new THREE.ShapeGeometry(shape), stone)
    back.position.z = -D
    block.add(back)
    const front = new THREE.Mesh(new THREE.ShapeGeometry(shape), stone)
    block.add(front)
    parts.current.front = front

    // bed edges on both faces, in the pencil colours
    for (const [line, color] of [
      [outer, OUTER],
      [inner, INNER],
    ] as const)
      for (const z of [0.01, -D]) block.add(tube(line.filter((_, i) => i % 4 === 0 || i === line.length - 1).map((p) => new THREE.Vector3(...w(p), z)), color, 0.035))

    // hinge lines (H and G carried along the axis) and the fold axis arrow
    for (const [p, name] of [
      [H, 'hinge line (H)'],
      [G, 'hinge line (G)'],
    ] as const) {
      const [x, y] = w(p)
      block.add(tube([new THREE.Vector3(x, y, 0.02), new THREE.Vector3(x, y, -D)], INK, 0.05))
      const l = label(name)
      l.position.set(x, y, -D * 0.55)
      block.add(l)
      parts.current.labels.push(l)
    }
    const [hx, hy] = w(H)
    const arrow = new THREE.ArrowHelper(new THREE.Vector3(0, 0, -1), new THREE.Vector3(hx, hy, -D), 2.6, INK, 0.6, 0.35)
    block.add(arrow)
    const axisLabel = label('fold axis', 'l3d-strong')
    axisLabel.position.set(hx, hy, -D - 3)
    block.add(axisLabel)
    parts.current.labels.push(axisLabel)

    // axial plane: the axial trace carried along the axis
    const d: Pt = [H[0] - G[0], H[1] - G[1]]
    const A: Pt = [H[0] + 0.35 * d[0], H[1] + 0.35 * d[1]]
    const B: Pt = [G[0] - 0.35 * d[0], G[1] - 0.35 * d[1]]
    const axial = new THREE.Group()
    axial.add(quad(A, B, new THREE.MeshBasicMaterial({ color: INK, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false })))
    const al = label('axial plane')
    al.position.set(...w(A), -D * 0.5)
    axial.add(al)
    parts.current.labels.push(al)
    block.add(axial)
    parts.current.axial = axial

    // isogon planes at the chosen angles
    const isos = new THREE.Group()
    for (const iso of result.isogons) {
      if (!iso.in_fit_range) continue
      const c = new THREE.Color(angleColor(iso.alpha))
      isos.add(quad(iso.p, iso.q, new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.3, side: THREE.DoubleSide, depthWrite: false })))
      isos.add(tube([new THREE.Vector3(...w(iso.p), 0.02), new THREE.Vector3(...w(iso.q), 0.02)], c.getHex(), 0.025))
    }
    block.add(isos)
    parts.current.isogons = isos

    // the photo as the front face of the block
    const photo = new THREE.Mesh(new THREE.PlaneGeometry(bw * s, bh * s), new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide }))
    photo.position.set((x0 + bw / 2 - cx) * s, -(y0 + bh / 2 - cy) * s, 0.005)
    new THREE.TextureLoader().load(doc.url, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace
      tex.repeat.set(bw / doc.width, bh / doc.height)
      tex.offset.set(x0 / doc.width, 1 - y1 / doc.height)
      const mat = photo.material as THREE.MeshBasicMaterial
      mat.map = tex
      mat.needsUpdate = true
    })
    block.add(photo)
    parts.current.photo = photo
    setTg((v) => ({ ...v })) // re-apply visibility to the new objects
  }, [result, doc.url, doc.width, doc.height, depthFactor])

  // ---- toggles and orientation
  useEffect(() => {
    const p = parts.current
    if (p.photo) p.photo.visible = tg.photo
    if (p.front) p.front.visible = !tg.photo
    if (p.isogons) p.isogons.visible = tg.isogons
    if (p.axial) p.axial.visible = tg.axial
    for (const l of p.labels) l.visible = tg.labels && (l.parent?.visible ?? true)
  }, [tg])

  useEffect(() => {
    const t = three.current
    if (!t) return
    // plunge tilts the axis (-z) down from horizontal; trend turns it clockwise from north (-z)
    t.pivot.rotation.set((-plunge * Math.PI) / 180, (-trend * Math.PI) / 180, 0, 'YXZ')
  }, [plunge, trend])

  const toggle = (k: keyof Toggles) => setTg((v) => ({ ...v, [k]: !v[k] }))

  return (
    <div className="sheet fold3d" role="dialog" aria-label="3D view">
      <header className="sheet-head">
        <div>
          <div className="sheet-kicker">3D view · illustration</div>
          <h2>{title} as a cylindrical fold</h2>
        </div>
        <button className="btn btn-quiet" style={{ marginLeft: 'auto' }} onClick={onClose}>
          <IconX width={16} height={16} /> Close
        </button>
      </header>
      <div className="fold3d-body">
        <div ref={mount} className="fold3d-canvas" />
        <aside className="fold3d-side">
          <p className="fold3d-note">
            A photo shows one slice of the fold. Here the traced bed is carried unchanged along the fold axis, the usual <b>cylindrical fold</b>{' '}
            assumption, so this is an illustration, not a 3D measurement.
          </p>
          <div className="fold3d-group">
            <div className="fold3d-title">Show</div>
            {(
              [
                ['photo', 'Photo as the front face'],
                ['isogons', 'Isogon planes'],
                ['axial', 'Axial plane'],
                ['labels', 'Labels'],
              ] as const
            ).map(([k, text]) => (
              <label key={k} className="check">
                <input type="checkbox" checked={tg[k]} onChange={() => toggle(k)} /> {text}
              </label>
            ))}
          </div>
          <div className="fold3d-group">
            <div className="fold3d-title">Fold axis</div>
            <label className="slider">
              <span>
                Length <b className="mono">{depthFactor.toFixed(1)}×</b>
              </span>
              <input type="range" min={0.3} max={2} step={0.1} value={depthFactor} onChange={(e) => setDepthFactor(Number(e.target.value))} />
            </label>
            <label className="slider">
              <span>
                Plunge <b className="mono">{plunge}°</b>
              </span>
              <input type="range" min={0} max={90} step={1} value={plunge} onChange={(e) => setPlunge(Number(e.target.value))} />
            </label>
            <label className="slider">
              <span>
                Trend <b className="mono">{trend}°</b>
              </span>
              <input type="range" min={0} max={359} step={1} value={trend} onChange={(e) => setTrend(Number(e.target.value))} />
            </label>
            <p className="fold3d-hint">Enter the plunge and trend of the fold axis from your compass readings to tilt the block.</p>
          </div>
          <div className="fold3d-group">
            <button className="btn" onClick={() => three.current?.home()}>
              Reset view
            </button>
            <p className="fold3d-hint">Drag to orbit · scroll to zoom · right-drag to pan</p>
          </div>
          <div className="fold3d-legend">
            <span>
              <i style={{ background: '#d9412a' }} /> outer surface
            </span>
            <span>
              <i style={{ background: '#1e66c4' }} /> inner surface
            </span>
            <span>
              <i style={{ background: '#348c46' }} /> isogon planes
            </span>
            <span>
              <i style={{ background: '#1f1c17' }} /> hinge lines
            </span>
          </div>
        </aside>
      </div>
    </div>
  )
}
