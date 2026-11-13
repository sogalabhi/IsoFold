// Ramsay's t'α–α diagram with the class fields shaded. Data comes in step 6; with none it draws the empty frame.

const W = 340
const H = 230
const M = { l: 38, r: 12, t: 12, b: 32 }
const X_MAX = 90
const Y_MAX = 1.4

const x = (a: number) => M.l + (a / X_MAX) * (W - M.l - M.r)
const y = (t: number) => H - M.b - (t / Y_MAX) * (H - M.t - M.b)

const cosCurve = (from = 0, to = X_MAX) => {
  const pts: string[] = []
  for (let a = from; a <= to; a += 1) pts.push(`${x(a).toFixed(1)},${y(Math.cos((a * Math.PI) / 180)).toFixed(1)}`)
  return pts
}

export function RamsayChart({ ghost = false }: { ghost?: boolean }) {
  const cos = cosCurve()
  const top = y(Y_MAX)
  const one = y(1)
  // fields: 1A above t' = 1, 1C between t' = 1 and cos α, 3 below cos α
  const field1A = `M${x(0)},${top} L${x(X_MAX)},${top} L${x(X_MAX)},${one} L${x(0)},${one} Z`
  const field1C = `M${x(0)},${one} L${x(X_MAX)},${one} L${cos.slice().reverse().join(' L')} Z`
  const field3 = `M${cos.join(' L')} L${x(X_MAX)},${y(0)} L${x(0)},${y(0)} Z`

  return (
    <svg className={`ramsay${ghost ? ' is-ghost' : ''}`} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Ramsay t′α against α diagram">
      <path d={field1A} className="field field-1a" />
      <path d={field1C} className="field field-1c" />
      <path d={field3} className="field field-3" />
      {/* outside the fit range */}
      <rect x={x(0)} y={top} width={x(20) - x(0)} height={y(0) - top} className="no-fit" />
      <rect x={x(70)} y={top} width={x(X_MAX) - x(70)} height={y(0) - top} className="no-fit" />

      {[0, 15, 30, 45, 60, 75, 90].map((a) => (
        <g key={a}>
          <line x1={x(a)} x2={x(a)} y1={top} y2={y(0)} className="grid" />
          <text x={x(a)} y={H - M.b + 16} className="tick" textAnchor="middle">
            {a}°
          </text>
        </g>
      ))}
      {[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4].map((t) => (
        <g key={t}>
          <line x1={x(0)} x2={x(X_MAX)} y1={y(t)} y2={y(t)} className="grid" />
          <text x={M.l - 6} y={y(t) + 3.5} className="tick" textAnchor="end">
            {t.toFixed(1)}
          </text>
        </g>
      ))}

      <line x1={x(0)} x2={x(X_MAX)} y1={one} y2={one} className="ref ref-1b" />
      <polyline points={cos.join(' ')} className="ref ref-2" />

      <text x={x(45)} y={y(1.2)} className="field-label" textAnchor="middle">1A</text>
      <text x={x(86)} y={y(1) - 5} className="field-label" textAnchor="middle">1B</text>
      <text x={x(66)} y={y(0.75)} className="field-label" textAnchor="middle">1C</text>
      <text x={x(87)} y={y(0.17)} className="field-label" textAnchor="middle">2</text>
      <text x={x(36)} y={y(0.38)} className="field-label" textAnchor="middle">3</text>

      <text x={(x(0) + x(X_MAX)) / 2} y={H - 2} className="axis-label" textAnchor="middle">dip α</text>
      <text x={10} y={(top + y(0)) / 2} className="axis-label" textAnchor="middle" transform={`rotate(-90 10 ${(top + y(0)) / 2})`}>
        t′α
      </text>
    </svg>
  )
}
