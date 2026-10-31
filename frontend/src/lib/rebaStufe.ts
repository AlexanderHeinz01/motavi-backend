/**
 * Levels of the posture index based on REBA (1 to 10), the same everywhere:
 * website (motavi: src/lib/steckbrief.ts), PDF report (services/pdf.py) and
 * analysis (services/analyzer.py stufe). Below 4 low, below 6 medium, below 8
 * high, from 8 very high. Not the standard REBA (1 to 15); docs/HALTUNGSINDEX.md.
 */
export interface RebaStufe {
  bis: number // index below this bound
  stufe: string
  massnahme: string
  farbe: string
}

export const REBA_STUFEN: RebaStufe[] = [
  { bis: 4, stufe: 'Niedrig', massnahme: 'derzeit kein Handlungsbedarf', farbe: '#22c55e' },
  { bis: 6, stufe: 'Mittel', massnahme: 'Gestaltung prüfen', farbe: '#eab308' },
  { bis: 8, stufe: 'Hoch', massnahme: 'Gestaltung bald verbessern', farbe: '#e63946' },
  { bis: Infinity, stufe: 'Sehr hoch', massnahme: 'Gestaltung vorrangig verbessern', farbe: '#ff4d5e' },
]

export const REBA_MAX = 10

export function rebaStufe(score: number): RebaStufe {
  return REBA_STUFEN.find((s) => score < s.bis)!
}

/** German format with decimal comma, e.g. 7,6. */
export const rebaText = (score: number) => score.toFixed(1).replace('.', ',')
