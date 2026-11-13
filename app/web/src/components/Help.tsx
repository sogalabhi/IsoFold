// A small "?" that explains a term on hover or keyboard focus. The popover is rendered into <body> with fixed
// positioning so scrolling panels never clip it. Text in $…$ is rendered as LaTeX.
import { useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Rich } from './Tex'

export const GLOSSARY = {
  R: {
    title: 'R: the thickness ratio',
    body: [
      'One number that says how the bed thins or thickens around the fold.',
      "The engine fits $t'_\\alpha = R + (1 - R)\\cos\\alpha$ to the measured thicknesses.",
      '$R = 1$: thickness stays the same everywhere (parallel fold). $R = 0$: thickness falls exactly like $\\cos\\alpha$ (similar fold). In between: the limbs thin, but less than in a similar fold.',
      'Equivalently, fitting $t_\\alpha = A + B\\cos\\alpha$ gives $R = \\frac{A}{A+B}$: the share of the hinge thickness that does not depend on dip.',
    ],
  },
  classes: {
    title: 'How the class is decided',
    body: [
      "Ramsay's classes compare the $t'_\\alpha$ curve with two reference curves: $t'_\\alpha = 1$ (parallel fold) and $t'_\\alpha = \\cos\\alpha$ (similar fold).",
      'With $R$ that becomes: $R > 1$ → 1A · $R \\approx 1$ → 1B · $0 < R < 1$ → 1C · $R \\approx 0$ → 2 · $R < 0$ → 3.',
      '$\\approx$ means within $\\pm 0.05$, or $\\pm 2\\sigma_R$ if that is larger, so a value right at a boundary is not forced into a neighbouring class.',
      'Each limb is classified on its own; if they disagree, both are shown.',
    ],
  },
  tprime: {
    title: "t'α: normalised thickness",
    body: [
      '$t_\\alpha$ is the orthogonal thickness of the bed where both edges dip $\\alpha$: the distance between the two parallel tangents at $p_\\alpha$ and $q_\\alpha$.',
      "$t'_\\alpha = \\dfrac{t_\\alpha}{t_0}$ divides it by the thickness at the hinge, so beds of any size can be compared. $t' = 1$ means as thick as at the hinge.",
    ],
  },
  Tprime: {
    title: "T'α: thickness along the axial trace",
    body: [
      "$T_\\alpha$ is the thickness measured parallel to the axial trace instead of perpendicular to the layer: $T'_\\alpha = \\dfrac{T_\\alpha}{t_0}$.",
      "For a similar fold (Class 2) $T'_\\alpha$ stays 1.",
    ],
  },
  t0: {
    title: 't₀: thickness at the hinge',
    body: ['The orthogonal thickness of the bed at the hinge, between the tangents at $H$ (outer edge) and $G$ (inner edge). Every other thickness is divided by it.'],
  },
  isogon: {
    title: 'Dip isogon',
    body: [
      'A line joining the points on the outer and inner edge of a bed where both edges have the same dip $\\alpha$.',
      'Converging isogons (towards the core) → Class 1. Parallel → Class 2. Diverging → Class 3.',
      'The angles you pick only choose which isogons are drawn and listed; the class always uses every 2.5° from 20° to 70°.',
    ],
  },
  alpha: {
    title: 'Dip α',
    body: [
      'The angle between the tangent to the layer and the tangent at the hinge. $\\alpha = 0^\\circ$ at the hinge and grows down each limb.',
      'Only 20°–70° is used for $R$: near the hinge thicknesses barely differ, and near the inflection tangents are hard to match.',
    ],
  },
  confidence: {
    title: 'Confident or low confidence',
    body: [
      'Confident: both limbs give the same class, $R$ is clearly inside it, and the bed is thick enough in the photo.',
      'Low confidence: the limbs disagree, $R$ sits right on a class boundary, the bed is thinner than 90 px, or the lines touch or cross. The reasons are listed under the result.',
      'Information notes (grey) never lower confidence.',
    ],
  },
  rscale: {
    title: 'Where R sits',
    body: [
      'The bar runs from $R = -0.5$ to $1.5$ with the class bands. L and R mark the left and right limb, with $\\pm\\sigma_R$ whiskers. A marker near a band edge means the fold is close to the next class.',
    ],
  },
  chart: {
    title: 'Ramsay diagram',
    body: [
      "$t'_\\alpha$ plotted against dip $\\alpha$. The flat line $t' = 1$ is a parallel fold (1B); the dashed curve $t' = \\cos\\alpha$ is a similar fold (2).",
      'Points above the flat line → 1A; between the two → 1C; below the dashed curve → 3.',
      "Dots and triangles are the engine's measurements on each limb; the solid curves are the fitted $t'_\\alpha = R + (1 - R)\\cos\\alpha$; diamonds are the hand measurements.",
    ],
  },
  hinge: {
    title: 'Hinge points H and G',
    body: ["$H$ (outer edge) and $G$ (inner edge) are where each edge's tangent is perpendicular to the axial trace; the line through them is the axial trace."],
  },
} as const

export type Term = keyof typeof GLOSSARY

export function Help({ term }: { term: Term }) {
  const ref = useRef<HTMLButtonElement>(null)
  const pop = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null)
  const g = GLOSSARY[term]

  // place the popover below the "?" (above if there's no room), kept inside the window
  useLayoutEffect(() => {
    if (!open || !ref.current || !pop.current) return
    const r = ref.current.getBoundingClientRect()
    const p = pop.current.getBoundingClientRect()
    const left = Math.min(Math.max(8, r.left + r.width / 2 - p.width / 2), window.innerWidth - p.width - 8)
    const below = r.bottom + 8
    const top = below + p.height > window.innerHeight - 8 ? Math.max(8, r.top - p.height - 8) : below
    setPos({ left, top })
  }, [open])

  return (
    <>
      <button
        ref={ref}
        type="button"
        className="help"
        aria-label={`What is this: ${g.title}`}
        aria-expanded={open}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => {
          e.stopPropagation()
          setOpen((v) => !v)
        }}
      >
        ?
      </button>
      {open &&
        createPortal(
          <div ref={pop} className="help-pop" role="tooltip" style={pos ? { left: pos.left, top: pos.top } : { left: -9999, top: 0 }}>
            <div className="help-title">{g.title}</div>
            {g.body.map((t) => (
              <p key={t}>
                <Rich text={t} />
              </p>
            ))}
          </div>,
          document.body,
        )}
    </>
  )
}
