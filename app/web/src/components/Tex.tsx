// LaTeX via KaTeX (bundled, works offline).
//   <Tex tex="t'_\alpha = \frac{t_\alpha}{t_0}" />          inline formula
//   <Tex tex="..." display />                                 centred display formula
//   <Rich text="fits $t'_\alpha = R + (1-R)\cos\alpha$ …" />  prose with $…$ formulas inside
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { useMemo } from 'react'

export function Tex({ tex, display = false }: { tex: string; display?: boolean }) {
  const html = useMemo(() => katex.renderToString(tex, { displayMode: display, throwOnError: false, output: 'html' }), [tex, display])
  return <span className={display ? 'tex tex-display' : 'tex'} dangerouslySetInnerHTML={{ __html: html }} />
}

export function Rich({ text }: { text: string }) {
  const parts = text.split(/(\$[^$]+\$)/g)
  return (
    <>
      {parts.map((p, i) => (p.startsWith('$') && p.endsWith('$') && p.length > 2 ? <Tex key={i} tex={p.slice(1, -1)} /> : <span key={i}>{p}</span>))}
    </>
  )
}
