import type { Frame, Timeline } from '../construction'
import { IconX } from './Icons'

interface Props {
  tl: Timeline
  frame: Frame
  playing: boolean
  speed: number
  onPlay: () => void
  onPause: () => void
  onStep: (delta: number) => void
  onRestart: () => void
  onEnd: () => void
  onSpeed: () => void
  onClose: () => void
}

const Btn = ({ title, onClick, children }: { title: string; onClick: () => void; children: React.ReactNode }) => (
  <button className="player-btn" title={title} aria-label={title} onClick={onClick}>
    {children}
  </button>
)

// simple glyph icons for the transport controls
const I = {
  first: <path d="M6 5v14M19 5l-9 7 9 7V5z" />,
  prev: <path d="M17 5l-9 7 9 7V5z" />,
  play: <path d="M7 4l13 8-13 8V4z" />,
  pause: <path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" />,
  next: <path d="M7 5l9 7-9 7V5z" />,
  last: <path d="M18 5v14M5 5l9 7-9 7V5z" />,
}
const Glyph = ({ d }: { d: React.ReactNode }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    {d}
  </svg>
)

export function Player({ tl, frame, playing, speed, onPlay, onPause, onStep, onRestart, onEnd, onSpeed, onClose }: Props) {
  const step = tl.steps[frame.i]
  const progress = (tl.starts[frame.i] + frame.u * step.dur) / tl.total
  return (
    <div className="player" onPointerDown={(e) => e.stopPropagation()}>
      <div className="player-caption">
        <span className="player-count mono">
          {frame.i + 1}/{tl.steps.length}
        </span>
        <span className="player-text">{step.caption}</span>
      </div>
      <div className="player-bar">
        <div className="player-progress">
          <div style={{ width: `${progress * 100}%` }} />
        </div>
        <div className="player-controls">
          <Btn title="Start" onClick={onRestart}>
            <Glyph d={I.first} />
          </Btn>
          <Btn title="Previous step" onClick={() => onStep(-1)}>
            <Glyph d={I.prev} />
          </Btn>
          {playing ? (
            <Btn title="Pause" onClick={onPause}>
              <Glyph d={I.pause} />
            </Btn>
          ) : (
            <Btn title="Play" onClick={onPlay}>
              <Glyph d={I.play} />
            </Btn>
          )}
          <Btn title="Next step" onClick={() => onStep(1)}>
            <Glyph d={I.next} />
          </Btn>
          <Btn title="End" onClick={onEnd}>
            <Glyph d={I.last} />
          </Btn>
          <button className="player-speed mono" onClick={onSpeed} title="Speed">
            {speed}×
          </button>
          <button className="player-close" onClick={onClose} title="Close construction">
            <IconX width={16} height={16} /> Close
          </button>
        </div>
      </div>
    </div>
  )
}
