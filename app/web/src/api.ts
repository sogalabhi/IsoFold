import type { Example, ExampleDetail, Health, Paths, Result } from './types'

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url}: ${r.status}`)
  return r.json() as Promise<T>
}

export const api = {
  health: () => get<Health>('/api/health'),
  examples: () => get<Example[]>('/api/examples'),
  example: (name: string) => get<ExampleDetail>(`/api/examples/${encodeURIComponent(name)}`),
  classify: async (paths: Paths, angles: number[]): Promise<Result> => {
    const r = await fetch('/api/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outer: { anchors: paths.outer }, inner: { anchors: paths.inner }, angles }),
    })
    if (!r.ok) throw new Error(`classify: ${r.status}`)
    return r.json() as Promise<Result>
  },
}
