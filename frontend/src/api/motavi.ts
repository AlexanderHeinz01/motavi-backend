const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? ''

export interface UploadResponse {
  job_id: string
  status: string
}

/** Workplace data of a job, no person. schichtdauer_min: net working time without breaks. */
export interface Arbeitsplatz {
  company_name?: string
  department?: string
  task_description?: string
  schichtdauer_min: number
}

export const SCHICHT = { standard: 450, min: 60, max: 720 }

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

async function fehlertext(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
  } catch {
    /* no JSON */
  }
  return `${fallback} (${res.status})`
}

/** PUT the file to a Cloud Storage upload session, with progress. */
function putDatei(url: string, file: File, onProgress: (pct: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload fehlgeschlagen (${xhr.status})`)))
    xhr.onerror = () => reject(new Error('Netzwerkfehler beim Upload'))
    xhr.open('PUT', url)
    xhr.send(file)
  })
}

const datei = (file: File) => ({ dateiname: file.name, groesse_bytes: file.size, content_type: file.type || 'application/octet-stream' })

/**
 * Upload in three steps (backend routers/upload.py): session, file straight
 * into Cloud Storage (Cloud Run accepts at most 32 MiB per request), start.
 */
export async function uploadVideo(file: File, meta: Arbeitsplatz, token: string, onProgress: (pct: number) => void): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE}/api/v1/upload/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...auth(token) },
    body: JSON.stringify({ ...meta, ...datei(file) }),
  })
  if (!res.ok) throw new Error(await fehlertext(res, 'Upload nicht möglich'))
  const { job_id, upload_url } = await res.json()
  await putDatei(upload_url, file, onProgress)
  const start = await fetch(`${API_BASE}/api/v1/upload/${job_id}/start`, { method: 'POST', headers: auth(token) })
  if (!start.ok) throw new Error(await fehlertext(start, 'Analyse konnte nicht gestartet werden'))
  return start.json()
}

export interface UploadLink {
  job_id: string
  url: string
  gueltig_bis: string
}

/** Upload link for a customer (team only, routers/upload_links.py). */
export async function createUploadLink(meta: Arbeitsplatz & { gueltig_tage?: number }, token: string): Promise<UploadLink> {
  const res = await fetch(`${API_BASE}/api/v1/upload-links`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...auth(token) },
    body: JSON.stringify(meta),
  })
  if (!res.ok) throw new Error(await fehlertext(res, 'Link konnte nicht erstellt werden'))
  return res.json()
}

export interface UploadLinkInfo {
  arbeitsplatz: string | null
  schichtdauer_min: number
  gueltig_bis: string
  max_bytes: number
}

export async function getUploadLink(linkToken: string): Promise<UploadLinkInfo> {
  const res = await fetch(`${API_BASE}/api/v1/upload-links/${linkToken}`)
  if (!res.ok) throw new Error(await fehlertext(res, 'Der Link ist ungültig'))
  return res.json()
}

/** Customer upload through a link, without sign-in. */
export async function uploadViaLink(linkToken: string, file: File, onProgress: (pct: number) => void): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/upload-links/${linkToken}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(datei(file)),
  })
  if (!res.ok) throw new Error(await fehlertext(res, 'Upload nicht möglich'))
  const { upload_url } = await res.json()
  await putDatei(upload_url, file, onProgress)
  const start = await fetch(`${API_BASE}/api/v1/upload-links/${linkToken}/start`, { method: 'POST' })
  if (!start.ok) throw new Error(await fehlertext(start, 'Übermittlung fehlgeschlagen'))
}

export interface TimelineFrame {
  second: number
  movement: string
}

export interface CriticalFrame {
  rank: number
  second: number
  reba: number
  movement: string
  gcs_path: string
  /** short-lived address of the image, relative to the API */
  bild_url?: string
}

export interface ActionItem {
  priority: 'CRITICAL' | 'MEDIUM'
  region: string
  text: string
}

export interface AnalysisResult {
  job_id: string
  company_name?: string
  department?: string
  task_description?: string
  shift_duration_min: number
  erkennung_anteil?: number
  reba_score: number
  reba_level: string
  body_regions: Record<string, number>
  movements: Record<string, { pct: number; minutes: number }>
  timeline: Array<{ minute: number; reba: number }>
  timeline_frames?: TimelineFrame[]
  critical_frames?: CriticalFrame[]
  action_items: ActionItem[]
}

export interface AnalysisStatus {
  status: 'processing' | 'done' | 'error'
  result?: AnalysisResult
  error?: string
}

export async function getAnalysisStatus(jobId: string, token: string): Promise<AnalysisStatus> {
  const res = await fetch(`${API_BASE}/api/v1/analysis/${jobId}`, { headers: auth(token) })
  if (!res.ok) throw new Error(await fehlertext(res, 'Statusabfrage fehlgeschlagen'))
  return res.json() as Promise<AnalysisStatus>
}

/** Download the ergonomics report (needs the sign-in header, so no plain link). */
export async function downloadReport(jobId: string, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/report/${jobId}/pdf`, { headers: auth(token) })
  if (!res.ok) throw new Error(await fehlertext(res, 'Report konnte nicht geladen werden'))
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = `motavi-report-${jobId.slice(0, 8)}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export function frameUrl(bildUrl: string): string {
  return `${API_BASE}${bildUrl}`
}
