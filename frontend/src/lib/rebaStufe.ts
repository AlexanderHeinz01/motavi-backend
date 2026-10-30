/**
 * REBA action levels as on the website and in the PDF report
 * (motavi: src/lib/steckbrief.ts rebaStufe; backend: services/pdf.py REBA_STUFEN):
 * below 2 negligible, below 4 low, below 8 medium, below 11 high, from 11 very high.
 * Derived from the mean score; reba_level in result.json uses older bounds.
 */
export interface RebaStufe {
  bis: number // score below this bound
  stufe: string
  massnahme: string
  farbe: string
}

export const REBA_STUFEN: RebaStufe[] = [
  { bis: 2, stufe: 'Vernachlässigbar', massnahme: 'keine Maßnahmen nötig', farbe: '#22c55e' },
  { bis: 4, stufe: 'Niedrig', massnahme: 'Maßnahmen eventuell nötig', farbe: '#22c55e' },
  { bis: 8, stufe: 'Mittel', massnahme: 'Maßnahmen nötig', farbe: '#eab308' },
  { bis: 11, stufe: 'Hoch', massnahme: 'Maßnahmen bald nötig', farbe: '#e63946' },
  { bis: Infinity, stufe: 'Sehr hoch', massnahme: 'Maßnahmen sofort nötig', farbe: '#ff4d5e' },
]

export const REBA_MAX = 15

export function rebaStufe(score: number): RebaStufe {
  return REBA_STUFEN.find((s) => score < s.bis)!
}

/** German format with decimal comma, e.g. 7,6. */
export const rebaText = (score: number) => score.toFixed(1).replace('.', ',')
