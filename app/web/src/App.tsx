import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import type { Doc, Example, Health, Paths } from './types'
import { Welcome } from './components/Welcome'
import { Workspace } from './components/Workspace'

const EMPTY: Paths = { outer: [], inner: [] }

export default function App() {
  const [health, setHealth] = useState<Health | 'down' | null>(null)
  const [examples, setExamples] = useState<Example[]>([])
  const [doc, setDoc] = useState<Doc | null>(null)
  const [paths, setPaths] = useState<Paths>(EMPTY)
  const [angles, setAngles] = useState<number[]>([20, 40, 60])
  const [loadingExample, setLoadingExample] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<{ text: string; go: () => void } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false) // the user has drawn or edited lines since the photo opened

  useEffect(() => {
    api.health().then(setHealth, () => setHealth('down'))
    api.examples().then(setExamples, () => setExamples([]))
  }, [])

  // ask before throwing away the user's own tracing
  const guard = (go: () => void) => {
    if (dirty) setConfirm({ text: 'Discard the current tracing?', go })
    else go()
  }

  const showDoc = (d: Doc, p: Paths) => {
    setDoc((old) => {
      if (old && !old.example) URL.revokeObjectURL(old.url)
      return d
    })
    setPaths(p)
    setDirty(false)
  }

  const openFile = (file: File) =>
    guard(() => {
      if (!file.type.startsWith('image/')) {
        setError(`${file.name} is not an image.`)
        return
      }
      const url = URL.createObjectURL(file)
      const im = new Image()
      im.onload = () => {
        showDoc({ name: file.name, url, width: im.naturalWidth, height: im.naturalHeight, example: null }, EMPTY)
        setAngles([20, 40, 60])
      }
      im.onerror = () => {
        URL.revokeObjectURL(url)
        setError(`Couldn't open ${file.name}. Try a JPG or PNG.`)
      }
      im.src = url
    })

  const openExample = (e: Example) =>
    guard(async () => {
      setLoadingExample(e.name)
      try {
        const d = await api.example(e.name)
        const [w, h] = d.photo_size
        showDoc({ name: d.title, url: d.photo_url, width: w, height: h, example: d }, { outer: d.outer.anchors, inner: d.inner.anchors })
        if (d.hand) setAngles(d.hand.angles.filter((a) => a < 90).map((a) => Math.round(a)))
      } catch {
        setError(`Couldn't load ${e.title}. Is the engine running?`)
      } finally {
        setLoadingExample(null)
      }
    })

  // deep link: #example=Fold_11 opens that example (handy to bookmark for the demo)
  useEffect(() => {
    const name = new URLSearchParams(location.hash.slice(1)).get('example')
    const ex = name && examples.find((e) => e.name === name)
    if (ex && !doc) openExample(ex)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examples])

  const onPhotoSize = useCallback((width: number, height: number) => setDoc((d) => d && { ...d, width, height }), [])

  return (
    <>
      {doc ? (
        <Workspace
          key={doc.url}
          doc={doc}
          paths={paths}
          angles={angles}
          engine={health && health !== 'down' ? health.engine : 'offline'}
          onPaths={(key, anchors) => {
            setPaths((p) => ({ ...p, [key]: anchors }))
            setDirty(true)
          }}
          onAngles={setAngles}
          onFile={openFile}
          onHome={() => guard(() => setDoc(null))}
          onPhotoSize={onPhotoSize}
        />
      ) : (
        <Welcome health={health} examples={examples} loadingExample={loadingExample} onFile={openFile} onExample={openExample} />
      )}

      {confirm && (
        <div className="modal-backdrop" onClick={() => setConfirm(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <p>{confirm.text}</p>
            <div className="modal-actions">
              <button className="btn" onClick={() => setConfirm(null)} autoFocus>
                Keep tracing
              </button>
              <button
                className="btn btn-danger"
                onClick={() => {
                  setConfirm(null)
                  setPaths(EMPTY)
                  setDirty(false)
                  confirm.go()
                }}
              >
                Discard
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="toast" role="alert" onClick={() => setError(null)}>
          {error}
        </div>
      )}
    </>
  )
}
