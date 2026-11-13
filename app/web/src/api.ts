import type { Example, ExampleDetail, Health } from './types'

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url}: ${r.status}`)
  return r.json() as Promise<T>
}

export const api = {
  health: () => get<Health>('/api/health'),
  examples: () => get<Example[]>('/api/examples'),
  example: (name: string) => get<ExampleDetail>(`/api/examples/${encodeURIComponent(name)}`),
}
