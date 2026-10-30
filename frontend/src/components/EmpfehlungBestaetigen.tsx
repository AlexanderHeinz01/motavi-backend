import { useEffect, useState } from 'react'
import {
  EMPFEHLUNG_IDS,
  getSteckbrief,
  putEmpfehlung,
  type EmpfehlungId,
  type SteckbriefDaten,
} from '../api/workplace'
import { useAuth } from '../auth/AuthContext'

const TEXT: Record<EmpfehlungId, string> = {
  'improve-then-automate': 'Erst verbessern, dann automatisieren',
  improve: 'Verbessern',
  automate: 'Automatisieren',
  keep: 'Beibehalten',
}
const MIT_AUTOMATISIERUNG: EmpfehlungId[] = ['improve-then-automate', 'automate']

/**
 * Expert view (STECKBRIEF_MODUL §6.4): confirm or change the recommendation
 * and the automation type. The tool's proposal stays visible.
 */
export default function EmpfehlungBestaetigen({ jobId, version }: { jobId: string; version?: string | null }) {
  const { token } = useAuth()
  const [daten, setDaten] = useState<SteckbriefDaten | null>(null)
  const [wahl, setWahl] = useState<EmpfehlungId | null>(null)
  const [typ, setTyp] = useState<string>('')
  const [kommentar, setKommentar] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [speichert, setSpeichert] = useState(false)

  const uebernehmen = (d: SteckbriefDaten) => {
    setDaten(d)
    setWahl(d.empfehlung.id)
    setTyp(d.automatisierungstyp.id ?? '')
    setKommentar(d.empfehlung.kommentar ?? '')
  }

  useEffect(() => {
    if (!token) return
    getSteckbrief(jobId, token).then(uebernehmen).catch((e: Error) => setFehler(e.message))
  }, [jobId, token, version])

  if (!daten) return fehler ? <p role="alert" className="font-body text-sm text-accent">{fehler}</p> : null

  const e = daten.empfehlung
  const t = daten.automatisierungstyp
  const mitAuto = wahl !== null && MIT_AUTOMATISIERUNG.includes(wahl)

  const bestaetigen = async () => {
    if (!token || !wahl) return
    setSpeichert(true)
    setFehler(null)
    try {
      uebernehmen(await putEmpfehlung(jobId, token, { empfehlung_id: wahl, typ_id: mitAuto && typ ? typ : null, kommentar }))
    } catch (err) {
      setFehler((err as Error).message)
    } finally {
      setSpeichert(false)
    }
  }

  return (
    <section className="rounded-2xl bg-bg-secondary p-5 flex flex-col gap-5" aria-labelledby="empfehlung-titel">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="empfehlung-titel" className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/40">
          Empfehlung und Automatisierungstyp bestätigen
        </h2>
        <span className="font-body text-xs text-neutral/60">
          Verbesserungs-Score {daten.verbesserungs_score.wert ?? 'n. b.'} · Automatisierungs-Score {daten.automatisierungs_score.wert ?? 'n. b.'}
        </span>
      </div>

      <fieldset className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <legend className="sr-only">Empfehlung</legend>
        {EMPFEHLUNG_IDS.map((id) => (
          <label key={id}
            className={`flex items-center justify-between gap-3 rounded-xl border px-4 py-3 cursor-pointer ${
              wahl === id ? 'border-data bg-data/10' : 'border-neutral/10 hover:border-neutral/30'}`}>
            <span className="flex items-center gap-3">
              <input type="radio" name="empfehlung" value={id} checked={wahl === id} onChange={() => setWahl(id)} className="accent-[#00b4d8]" />
              <span className="font-body text-sm text-white">{TEXT[id]}</span>
            </span>
            {e.vorschlag_id === id && <span className="font-body text-[11px] text-neutral/60 border border-neutral/20 rounded-full px-2 py-0.5">Vorschlag</span>}
          </label>
        ))}
      </fieldset>

      {e.gruende.length > 0 && e.vorschlag_id === e.id && (
        <p className="font-body text-xs text-neutral/55">Ausschlaggebend für den Vorschlag: {e.gruende.join(' · ')}</p>
      )}

      {mitAuto && (
        <label className="flex flex-col gap-1 max-w-md">
          <span className="font-body text-xs text-neutral/60">
            Automatisierungstyp{t.vorschlag ? ` (Vorschlag: ${t.vorschlag})` : ' (kein Vorschlag aus den Regeln)'}
          </span>
          <select value={typ} onChange={(ev) => setTyp(ev.target.value)}
            className="px-3 py-2 rounded-lg bg-bg-primary border border-neutral/15 font-body text-sm text-white">
            <option value="">offen lassen</option>
            {t.auswahl.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        </label>
      )}

      <label className="flex flex-col gap-1">
        <span className="font-body text-xs text-neutral/60">Kommentar (erscheint im Steckbrief)</span>
        <textarea value={kommentar} onChange={(ev) => setKommentar(ev.target.value)} rows={2} maxLength={2000}
          className="px-3 py-2 rounded-lg bg-bg-primary border border-neutral/15 font-body text-sm text-white" />
      </label>

      <div className="flex flex-wrap items-center gap-4">
        <button onClick={bestaetigen} disabled={!wahl || speichert}
          className="px-5 py-2.5 rounded-xl bg-data text-bg-primary font-body text-sm font-semibold disabled:opacity-40">
          {speichert ? 'Wird gespeichert …' : 'Empfehlung bestätigen'}
        </button>
        <span className="font-body text-xs text-neutral/55">
          {e.status === 'bestaetigt'
            ? `Bestätigt am ${new Date(e.bestaetigt_am!).toLocaleDateString('de-DE')}: ${e.text}${t.name ? `, ${t.name}` : ''}`
            : 'Noch nicht bestätigt: der Kunde sieht den Vorschlag des Tools.'}
        </span>
      </div>
      {daten.hinweise.filter((h) => h.includes('seit der Bestätigung')).map((h) => (
        <p key={h} role="status" className="font-body text-sm text-accent">{h}</p>
      ))}
      {fehler && <p role="alert" className="font-body text-sm text-accent">{fehler}</p>}
    </section>
  )
}
