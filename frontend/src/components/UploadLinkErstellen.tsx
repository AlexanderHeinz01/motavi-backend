import { useState } from 'react'
import { SCHICHT, createUploadLink, type UploadLink } from '../api/motavi'

const inputCls =
  'w-full px-3 py-2 rounded-lg bg-bg-primary border border-bg-secondary ' +
  'focus:outline-none focus:border-data/50 font-body text-sm text-white ' +
  'placeholder:text-neutral/25 transition-colors'

/** Upload link for a customer (Video-Check, decision G2): one link per workplace. */
export default function UploadLinkErstellen({ token }: { token: string }) {
  const [bereich, setBereich] = useState('')
  const [taetigkeit, setTaetigkeit] = useState('')
  const [schicht, setSchicht] = useState(SCHICHT.standard)
  const [link, setLink] = useState<UploadLink | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)

  const erstellen = async () => {
    setFehler(null)
    try {
      setLink(await createUploadLink({ department: bereich || undefined, task_description: taetigkeit || undefined, schichtdauer_min: schicht }, token))
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e))
    }
  }

  const absolut = link ? new URL(link.url, window.location.origin).toString() : ''

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-bg-secondary p-4">
      <p className="font-body text-xs text-neutral/40 uppercase tracking-widest">Upload-Link für Kunden</p>
      <div className="grid grid-cols-2 gap-3">
        <input className={inputCls} placeholder="Bereich" value={bereich} onChange={(e) => setBereich(e.target.value)} />
        <input className={inputCls} placeholder="Tätigkeit" value={taetigkeit} onChange={(e) => setTaetigkeit(e.target.value)} />
        <label className="col-span-2 flex flex-col gap-1.5">
          <span className="font-body text-xs text-neutral/50">Netto-Arbeitszeit je Schicht in Minuten, ohne Pausen</span>
          <input
            type="number"
            className={inputCls}
            min={SCHICHT.min}
            max={SCHICHT.max}
            value={schicht}
            onChange={(e) => setSchicht(Math.min(SCHICHT.max, Math.max(SCHICHT.min, Number(e.target.value) || SCHICHT.standard)))}
          />
        </label>
      </div>
      <button onClick={erstellen} className="rounded-lg border border-data/40 py-2 font-body text-sm text-data hover:bg-data/10">
        Link erstellen
      </button>
      {fehler && <p className="font-body text-sm text-accent">{fehler}</p>}
      {link && (
        <div className="flex flex-col gap-1">
          <input readOnly className={`${inputCls} font-mono text-xs`} value={absolut} onFocus={(e) => e.target.select()} />
          <p className="font-body text-xs text-neutral/40">
            Gültig bis {new Date(link.gueltig_bis).toLocaleDateString('de-DE')}, für ein Video. Danach erscheint der Job in der Übersicht unter
            /app/dashboard/{link.job_id}.
          </p>
        </div>
      )}
    </div>
  )
}
