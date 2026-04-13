const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? ''

export interface UploadResponse {
  job_id: string
  status: string
}

export interface ActionItem {
  priority: 'CRITICAL' | 'MEDIUM'
  region: string
  text: string
  reduction_pct?: number
}

export interface AnalysisResult {
  job_id: string
  worker_id?: string
  shift_duration_min: number
  reba_score: number
  reba_level: string
  body_regions: Record<string, number>
  movements: Record<string, { pct: number; minutes: number }>
  timeline: Array<{ minute: number; reba: number }>
  action_items: ActionItem[]
}

export interface AnalysisStatus {
  status: 'processing' | 'done' | 'error'
  result?: AnalysisResult
  error?: string
}

export function uploadVideoWithProgress(
  file: File,
  onProgress: (pct: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append('file', file)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status === 202) {
        resolve(JSON.parse(xhr.responseText) as UploadResponse)
      } else {
        reject(new Error(`Upload fehlgeschlagen: ${xhr.status} ${xhr.statusText}`))
      }
    }
    xhr.onerror = () => reject(new Error('Netzwerkfehler beim Upload'))
    xhr.open('POST', `${API_BASE}/api/v1/upload`)
    xhr.send(form)
  })
}

export async function getAnalysisStatus(jobId: string): Promise<AnalysisStatus> {
  const res = await fetch(`${API_BASE}/api/v1/analysis/${jobId}`)
  if (!res.ok) throw new Error(`Statusabfrage fehlgeschlagen: ${res.status}`)
  return res.json() as Promise<AnalysisStatus>
}

export function getReportPdfUrl(jobId: string): string {
  return `${API_BASE}/api/v1/report/${jobId}/pdf`
}
