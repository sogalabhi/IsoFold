import { useRef, useState } from 'react'
import type { Example, Health } from '../types'
import { IconUpload, Logo } from './Icons'

interface Props {
  health: Health | 'down' | null
  examples: Example[]
  loadingExample: string | null
  onFile: (f: File) => void
  onExample: (e: Example) => void
}

export function Welcome({ health, examples, loadingExample, onFile, onExample }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)

  return (
    <div className="welcome graph-paper">
      <header className="welcome-top">
        <div className="brand">
          <Logo size={30} />
          <span className="brand-name">IsoFold Trace</span>
        </div>
      </header>

      <main className="welcome-main">
        <div className="welcome-kicker">Ramsay dip-isogon method</div>
        <h1 className="welcome-title">Classify a fold from a photo</h1>
        <p className="welcome-sub">
          Trace the two edges of one bed. IsoFold draws the dip isogons and gives its Ramsay class.
        </p>

        {health === 'down' && (
          <div className="banner banner-bad">
            Can't reach the engine. Start it with <code>app/run.sh</code>, then reload this page.
          </div>
        )}

        <div
          className={`dropzone${over ? ' is-over' : ''}`}
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setOver(true)
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setOver(false)
            const f = e.dataTransfer.files[0]
            if (f) onFile(f)
          }}
        >
          <div className="dropzone-icon">
            <IconUpload width={26} height={26} />
          </div>
          <div className="dropzone-text">
            Drop a fold photo here, or <span className="link">browse</span>
          </div>
          <div className="dropzone-sub">JPG or PNG, any size. The photo stays on this computer.</div>
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

        {examples.length > 0 && (
          <>
            <div className="examples-head">
              <h2>Or start from a field example</h2>
              <span>Traced and measured by hand in CorelDraw</span>
            </div>
            <div className="examples">
              {examples.map((e) => (
                <button key={e.name} className="example-card" onClick={() => onExample(e)} disabled={!!loadingExample}>
                  <div className="example-thumb">
                    <img src={e.thumb_url} alt="" loading="lazy" />
                    {loadingExample === e.name && (
                      <div className="example-loading">
                        <div className="spinner" />
                      </div>
                    )}
                  </div>
                  <div className="example-body">
                    <div className="example-title">{e.title}</div>
                    <div className="example-meta">{e.locality}</div>
                    {e.hand ? (
                      <div className="example-hand">
                        Hand R <b className="mono">{e.hand.R.toFixed(2)}</b> · {e.hand.fold_class}
                      </div>
                    ) : (
                      <div className="example-hand is-none">hand trace</div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </main>

      <footer className="welcome-foot">
        engine <span className="mono">{health && health !== 'down' ? health.engine : '…'}</span>
      </footer>
    </div>
  )
}
