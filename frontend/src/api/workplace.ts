/** Steckbrief module API: process steps and expert review (only for consultants). */
const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? ''

export type Klasse = 'wertschoepfend' | 'notwendig' | 'verschwendung'
export type Art = 'bewegung' | 'ruhe' | 'ortswechsel'

export interface SegmentVorschlag {
  start_phase: number
  ende_phase: number
  start_s: number
  ende_s: number
  dauer_s: number
  art: Art
  vorschlag_typ?: string | null
}

export interface SegmentReview {
  start_phase: number
  ende_phase: number
  typ: string
  klasse?: Klasse | null
}

export interface AblaufResponse {
  job_id: string
  zyklen: {
    erkannt: boolean
    hinweis?: string | null
    median_s?: number | null
    anzahl_gueltig: number
    konfidenz: number
    zyklen_pro_schicht?: number | null
  }
  median_zyklus?: {
    dauer_s: number
    anzahl_zyklen: number
    phase: number[]
    hand_speed: number[]
    hip_speed: number[]
  } | null
  vorschlag: SegmentVorschlag[]
  typen: Record<string, Klasse>
  review?: {
    segmente: SegmentReview[]
    kommentar?: string | null
    bestaetigt_von: string
    bestaetigt_am: string
  } | null
  ergebnis?: {
    ablaufschritte: { typ: string; klasse: Klasse; anteil: number; dauer_s: number }[]
    anteile_ablauf: Record<Klasse, number>
    sekunden_je_zyklus: Record<Klasse, number>
    minuten_pro_schicht: Record<Klasse, number | null>
    anzahl_zyklen: number
    hinweis: string
  } | null
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Anfrage fehlgeschlagen (${res.status}).`
    try {
      const data = await res.json()
      if (typeof data?.detail === 'string') detail = data.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export async function getAblauf(jobId: string, token: string): Promise<AblaufResponse> {
  const res = await fetch(`${API_BASE}/api/v1/workplace/${jobId}/ablauf`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parse(res)
}

export async function putReview(
  jobId: string,
  token: string,
  segmente: SegmentReview[],
  kommentar?: string,
): Promise<AblaufResponse> {
  const res = await fetch(`${API_BASE}/api/v1/workplace/${jobId}/review`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ segmente, kommentar: kommentar || null }),
  })
  return parse(res)
}

export const KLASSEN_TEXT: Record<Klasse, string> = {
  wertschoepfend: 'wertschöpfend',
  notwendig: 'notwendig',
  verschwendung: 'Verschwendung',
}

export const ART_TEXT: Record<Art, string> = {
  bewegung: 'Bewegung',
  ruhe: 'Ruhe',
  ortswechsel: 'Ortswechsel',
}

export const BERATER_ROLLEN = ['berater', 'admin']
