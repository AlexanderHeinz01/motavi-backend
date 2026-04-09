// TODO: implement in Step 3

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''

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

export async function uploadVideo(_file: File): Promise<UploadResponse> {
  // TODO: implement
  throw new Error('Not implemented')
}

export async function getAnalysisStatus(_jobId: string): Promise<AnalysisStatus> {
  // TODO: implement
  throw new Error('Not implemented')
}

export function getReportPdfUrl(jobId: string): string {
  return `${API_BASE}/api/v1/report/${jobId}/pdf`
}
