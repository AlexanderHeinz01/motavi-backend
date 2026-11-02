const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? ''

export interface JobEintrag {
  job_id: string
  erstellt_am: string | null
  erstellt_von: string | null
  quelle: 'intern' | 'upload_link' | null
  status: 'wartet_auf_upload' | 'processing' | 'fertig' | 'fehler' | null
  arbeitsplatz: string | null
  unternehmen: string | null
  link_gueltig_bis: string | null
}

export interface Zugang {
  email: string
  role: 'user' | 'berater' | 'admin'
  name?: string | null
  fest?: boolean
  freigegeben_von?: string
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Anfrage fehlgeschlagen (${res.status})`
    try { detail = (await res.json()).detail ?? detail } catch { /* no JSON */ }
    throw new Error(detail)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

export const getJobs = (token: string) => fetch(`${API_BASE}/api/v1/jobs`, { headers: auth(token) }).then((r) => json<JobEintrag[]>(r))

export const getZugaenge = (token: string) => fetch(`${API_BASE}/api/v1/zugaenge`, { headers: auth(token) }).then((r) => json<Zugang[]>(r))

export const setZugang = (token: string, email: string, role: Zugang['role'], name?: string) =>
  fetch(`${API_BASE}/api/v1/zugaenge/${encodeURIComponent(email)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...auth(token) },
    body: JSON.stringify({ role, name: name || null }),
  }).then((r) => json<Zugang>(r))

export const removeZugang = (token: string, email: string) =>
  fetch(`${API_BASE}/api/v1/zugaenge/${encodeURIComponent(email)}`, { method: 'DELETE', headers: auth(token) }).then((r) => json<void>(r))
