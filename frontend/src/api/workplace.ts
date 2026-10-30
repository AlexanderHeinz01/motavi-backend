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

// ── Steckbrief (S4, S5) ──────────────────────────────────────────────────────

export type EmpfehlungId = 'improve-then-automate' | 'improve' | 'automate' | 'keep'

/** A metric with its quality (guideline 3: below the threshold no value). */
export interface Kennzahl {
  wert: number | null
  qualitaet: number
  belastbar: boolean
  grund?: string | null
}

export interface ScoreDaten {
  wert: number | null
  belastbar: boolean
  vollstaendig: boolean
  fehlend: string[]
}

type Bereich = [number, number]

export interface SteckbriefDaten {
  job_id: string
  arbeitsplatz: string
  erstellt_am: string
  empfehlung: {
    id: EmpfehlungId | null
    text: string
    erklaerung: string | null
    status: 'vorschlag' | 'bestaetigt'
    vorlaeufig: boolean
    mit_automatisierung: boolean
    gruende: string[]
    vorschlag_id: EmpfehlungId | null
    vorschlag_text: string
    geaendert: boolean
    bestaetigt_am: string | null
    kommentar: string | null
    vorrangig: boolean
    vorrang_text: string | null
    vorrang_grund: string | null
  }
  verbesserungs_score: ScoreDaten
  automatisierungs_score: ScoreDaten
  automatisierungstyp: {
    id: string | null
    name: string | null
    text: string
    vorschlag_id: string | null
    vorschlag: string | null
    geaendert: boolean
    auswahl: { id: string; name: string }[]
  }
  zyklen: {
    erkannt: boolean
    hinweis: string | null
    anzahl_gueltig: number
    zykluszeit_median_s: Kennzahl
    zykluszeit_vk: Kennzahl
    zyklen_pro_schicht: Kennzahl
    zeitanteil_in_zyklen: Kennzahl
  }
  ablauf: {
    bestaetigt: boolean
    bestaetigt_am: string | null
    ablaufschritte: { typ: string; klasse: Klasse; anteil: number; dauer_s: number }[]
    anteile_ablauf: Record<Klasse, number> | null
    minuten_pro_schicht: Record<Klasse, number | null> | null
  }
  greifraum: {
    hoehenzonen: Record<'unter_knie' | 'knie_huefte' | 'huefte_schulter' | 'ueber_schulter', Kennzahl>
    griffe_ausserhalb: Kennzahl
    anzahl_griffe: number
    hinweis: string
  } | null
  belastung: Record<'reba_mittel' | 'reba_max' | 'buecken_anteil' | 'ueberkopf_anteil' | 'drehung_anteil' | 'drehungen_pro_zyklus', Kennzahl>
  kundenangaben: Kundenangaben
  wirtschaftlichkeit: {
    verbessern: {
      berechnet: boolean
      grund?: string
      verschwendung_min_schicht?: number
      verbesserung_min_schicht?: number
      euro_jahr?: number | null
      fehlende_angaben?: string[]
    }
    automatisieren: {
      berechnet: boolean
      grund?: string
      basis?: string
      typ?: string
      zykluszeit_basis_s?: number
      stunden_jahr?: Bereich | null
      euro_jahr_brutto?: Bereich | null
      betriebskosten_anteil?: Bereich
      euro_jahr_netto?: Bereich | null
      investition_euro?: Bereich
      investition_quelle?: string
      amortisation_jahre?: Bereich | null
      fehlende_angaben?: string[]
    }
    hinweis: string
  }
  hinweise: string[]
}

export interface Kundenangaben {
  teilegewicht_kg?: number
  abmessungen_cm?: { laenge?: number; breite?: number; hoehe?: number }
  anzahl_varianten?: number
  stueck_pro_schicht?: number
  schichten_pro_tag?: number
  schichtdauer_min?: number
  arbeitstage_pro_jahr?: number
  vollkosten_euro_pro_stunde?: number
  besetzung_schwierigkeit?: number
  investition_euro?: Bereich
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

export async function getSteckbrief(jobId: string, token: string): Promise<SteckbriefDaten> {
  return parse(await fetch(`${API_BASE}/api/v1/workplace/${jobId}`, { headers: auth(token) }))
}

export async function putKundenangaben(jobId: string, token: string, angaben: Kundenangaben): Promise<SteckbriefDaten> {
  const res = await fetch(`${API_BASE}/api/v1/workplace/${jobId}/inputs`, {
    method: 'PUT',
    headers: { ...auth(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(angaben),
  })
  return parse(res)
}

export async function putEmpfehlung(
  jobId: string,
  token: string,
  body: { empfehlung_id: EmpfehlungId; typ_id: string | null; kommentar?: string },
): Promise<SteckbriefDaten> {
  const res = await fetch(`${API_BASE}/api/v1/workplace/${jobId}/empfehlung`, {
    method: 'PUT',
    headers: { ...auth(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...body, kommentar: body.kommentar || null }),
  })
  return parse(res)
}

/** PDF or JSON export: the routes need the token, so a plain link does not work. */
export async function herunterladen(jobId: string, token: string, art: 'pdf' | 'export'): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/workplace/${jobId}/${art}`, { headers: auth(token) })
  if (!res.ok) await parse(res)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `motavi-steckbrief-${jobId.slice(0, 8)}.${art === 'pdf' ? 'pdf' : 'json'}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const EMPFEHLUNG_IDS: EmpfehlungId[] = ['improve-then-automate', 'improve', 'automate', 'keep']
