export async function request<T>(path: string, body?: unknown, method = 'GET', signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method, signal, cache: 'no-store',
    ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string | { loc: string[]; msg: string }[] } | null
    const detail = payload?.detail
    const message = Array.isArray(detail) ? detail.map(issue => `${issue.loc.join('.')}: ${issue.msg}`).join(' · ') : detail
    throw new Error(message || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}
