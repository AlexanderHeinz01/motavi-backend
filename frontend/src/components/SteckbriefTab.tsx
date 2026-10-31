import { useEffect, useState, type CSSProperties, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BERATER_ROLLEN,
  KLASSEN_TEXT,
  getSteckbrief,
  herunterladen,
  putKundenangaben,
  type Kennzahl,
  type Klasse,
  type Kundenangaben,
  type SteckbriefDaten,
} from '../api/workplace'
import { useAuth } from '../auth/AuthContext'

/**
 * Dashboard tab "Steckbrief" (STECKBRIEF_MODUL §6.1): recommendation as a
 * large label, both scores, metrics, process steps, reach, economics.
 * All four recommendations look the same: they are equal results.
 */

const NB = 'nicht belastbar messbar'
const SCHWELLE = { verbesserung: 50, automatisierung: 60 }
// strong, medium, hatched: never colour alone
const KLASSE_STIL: Record<Klasse, CSSProperties> = {
  wertschoepfend: { background: '#00b4d8' },
  notwendig: { background: 'rgba(0,180,216,0.4)' },
  verschwendung: { background: 'repeating-linear-gradient(45deg, #e63946 0 4px, rgba(230,57,70,0.25) 4px 9px)' },
}
const ZONEN: [keyof NonNullable<SteckbriefDaten['greifraum']>['hoehenzonen'], string][] = [
  ['ueber_schulter', 'über Schulter'],
  ['huefte_schulter', 'Hüfte bis Schulter'],
  ['knie_huefte', 'Knie bis Hüfte'],
  ['unter_knie', 'unter Knie'],
]

// German numbers with a non-breaking space before the unit
const zahl = (v: number, d = 0) => v.toLocaleString('de-DE', { minimumFractionDigits: d, maximumFractionDigits: d })
const prozent = (v: number) => `${zahl(v * 100)} %`
const euro = (v: number) => `${zahl(Math.round(v / 100) * 100)} €`
const bereich = (r: [number, number] | null | undefined, f: (v: number) => string) => (r ? `${f(r[0])} bis ${f(r[1])}` : null)
const datum = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('de-DE') : '')
const kz = (k: Kennzahl | undefined, f: (v: number) => string) => (k && k.belastbar && k.wert !== null ? f(k.wert) : NB)

function Card({ title, children, className = '', tag }: { title: string; children: ReactNode; className?: string; tag?: string }) {
  return (
    <section className={`rounded-2xl bg-bg-secondary p-5 flex flex-col gap-4 ${className}`}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/50">{title}</h3>
        {tag && <span className="font-body text-[11px] text-neutral/50 border border-neutral/15 rounded-full px-2 py-0.5">{tag}</span>}
      </div>
      {children}
    </section>
  )
}

function Zeile({ label, value }: { label: string; value: string | null }) {
  const nb = value === NB || value === null
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 border-b border-neutral/10 last:border-0">
      <span className="font-body text-sm text-neutral/70">{label}</span>
      <span className={nb ? 'font-body text-xs text-neutral/45' : /^[\d.,]/.test(value) ? 'font-mono text-sm text-white text-right' : 'font-body text-sm text-white text-right'}>
        {value ?? 'Angaben fehlen'}
      </span>
    </div>
  )
}

function ScoreBalken({ name, wert, schwelle, hoch }: { name: string; wert: number | null; schwelle: number; hoch: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between">
        <span className="font-body text-sm text-white">{name}</span>
        <span className={wert === null ? 'font-body text-xs text-neutral/45' : 'font-mono text-2xl font-bold text-white'}>
          {wert === null ? NB : wert}
        </span>
      </div>
      <div className="relative h-3 rounded-full bg-bg-primary" role="img" aria-label={`${name}: ${wert ?? NB} von 100, hoch ab ${schwelle}`}>
        {wert !== null && <div className="h-3 rounded-full bg-neutral/80" style={{ width: `${wert}%` }} />}
        <div className="absolute -top-1 -bottom-1 w-0.5 bg-accent" style={{ left: `${schwelle}%` }} />
      </div>
      <span className="font-body text-xs text-neutral/45">hoch ab {schwelle}: {hoch}</span>
    </div>
  )
}

function AblaufBalken({ schritte }: { schritte: SteckbriefDaten['ablauf']['ablaufschritte'] }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-11 w-full gap-0.5" role="img"
        aria-label={`Ablaufschritte im Zyklus: ${schritte.map((s) => `${s.typ} ${prozent(s.anteil)}`).join(', ')}`}>
        {schritte.map((s, i) => (
          <div key={i} className="h-full rounded-[3px] overflow-hidden flex items-center px-2" style={{ width: `${s.anteil * 100}%`, ...KLASSE_STIL[s.klasse] }}
            title={`${s.typ}: ${prozent(s.anteil)}`}>
            {s.anteil >= 0.07 && (
              <span className={`font-body text-sm text-white truncate [text-shadow:0_1px_2px_rgba(0,0,0,0.6)] ${s.anteil < 0.2 ? 'hidden md:inline' : ''}`}>{s.typ}</span>
            )}
          </div>
        ))}
      </div>
      <p className="font-body text-sm text-neutral/75">
        {schritte.map((s) => `${s.typ} ${prozent(s.anteil)}`).join(' · ')}
      </p>
      <div className="flex flex-wrap gap-4 font-body text-xs text-neutral/60">
        {(['wertschoepfend', 'notwendig', 'verschwendung'] as Klasse[]).map((k) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm" style={KLASSE_STIL[k]} />
            {KLASSEN_TEXT[k]}
          </span>
        ))}
      </div>
    </div>
  )
}

const FELDER: { key: string; label: string; einheit?: string; step?: string }[] = [
  { key: 'teilegewicht_kg', label: 'Teilegewicht', einheit: 'kg', step: '0.1' },
  { key: 'laenge', label: 'Größte Kante des Teils', einheit: 'cm' },
  { key: 'anzahl_varianten', label: 'Anzahl Varianten' },
  { key: 'stueck_pro_schicht', label: 'Stück pro Schicht' },
  { key: 'schichten_pro_tag', label: 'Schichten pro Tag' },
  { key: 'schichtdauer_min', label: 'Schichtdauer', einheit: 'min' },
  { key: 'arbeitstage_pro_jahr', label: 'Arbeitstage pro Jahr' },
  { key: 'vollkosten_euro_pro_stunde', label: 'Vollkosten pro Stunde', einheit: '€', step: '0.5' },
  { key: 'besetzung_schwierigkeit', label: 'Stellenbesetzung schwierig (1 bis 5)' },
  { key: 'inv_von', label: 'Investition Automatisierung von', einheit: '€' },
  { key: 'inv_bis', label: 'bis', einheit: '€' },
]

function alsFormular(k: Kundenangaben): Record<string, string> {
  const s = (v: number | undefined) => (v === undefined ? '' : String(v))
  return {
    teilegewicht_kg: s(k.teilegewicht_kg),
    laenge: s(k.abmessungen_cm?.laenge),
    anzahl_varianten: s(k.anzahl_varianten),
    stueck_pro_schicht: s(k.stueck_pro_schicht),
    schichten_pro_tag: s(k.schichten_pro_tag),
    schichtdauer_min: s(k.schichtdauer_min),
    arbeitstage_pro_jahr: s(k.arbeitstage_pro_jahr),
    vollkosten_euro_pro_stunde: s(k.vollkosten_euro_pro_stunde),
    besetzung_schwierigkeit: s(k.besetzung_schwierigkeit),
    inv_von: s(k.investition_euro?.[0]),
    inv_bis: s(k.investition_euro?.[1]),
  }
}

function ausFormular(f: Record<string, string>, alt: Kundenangaben): Kundenangaben {
  const n = (key: string) => (f[key].trim() === '' ? undefined : Number(f[key].replace(',', '.')))
  const out: Kundenangaben = {}
  for (const key of ['teilegewicht_kg', 'anzahl_varianten', 'stueck_pro_schicht', 'schichten_pro_tag', 'schichtdauer_min',
    'arbeitstage_pro_jahr', 'vollkosten_euro_pro_stunde', 'besetzung_schwierigkeit'] as const) {
    const v = n(key)
    if (v !== undefined) out[key] = v
  }
  const laenge = n('laenge')
  if (laenge !== undefined) out.abmessungen_cm = { ...alt.abmessungen_cm, laenge }
  const von = n('inv_von')
  const bis = n('inv_bis')
  if (von !== undefined && bis !== undefined) out.investition_euro = [von, bis]
  return out
}

function Angaben({ jobId, daten, onSaved }: { jobId: string; daten: SteckbriefDaten; onSaved: (d: SteckbriefDaten) => void }) {
  const { token } = useAuth()
  const leer = Object.keys(daten.kundenangaben).length === 0
  const [offen, setOffen] = useState(leer)
  const [form, setForm] = useState(() => alsFormular(daten.kundenangaben))
  const [fehler, setFehler] = useState<string | null>(null)
  const [speichert, setSpeichert] = useState(false)

  const speichern = async () => {
    if (!token) return
    setSpeichert(true)
    setFehler(null)
    try {
      onSaved(await putKundenangaben(jobId, token, ausFormular(form, daten.kundenangaben)))
      setOffen(false)
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e))
    } finally {
      setSpeichert(false)
    }
  }

  return (
    <Card title="Angaben zum Arbeitsplatz" className="md:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-body text-sm text-neutral/60">
          {leer ? 'Noch keine Angaben. Teilegewicht, Varianten und Kosten verbessern die Bewertung und ergeben Euro-Werte.'
            : 'Ihre Angaben fließen in Bewertung und Wirtschaftlichkeit ein.'}
        </p>
        <button onClick={() => setOffen(!offen)} aria-expanded={offen}
          className="px-3 py-1.5 rounded-lg border border-neutral/15 font-body text-sm text-neutral/80 hover:border-data/50">
          {offen ? 'Schließen' : leer ? 'Angaben eintragen' : 'Angaben ändern'}
        </button>
      </div>
      {offen && (
        <form className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" onSubmit={(e) => { e.preventDefault(); speichern() }}>
          {FELDER.map((f) => (
            <label key={f.key} className="flex flex-col gap-1">
              <span className="font-body text-xs text-neutral/60">{f.label}{f.einheit ? ` (${f.einheit})` : ''}</span>
              <input type="number" inputMode="decimal" min={0} step={f.step ?? '1'} value={form[f.key]}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                className="px-3 py-2 rounded-lg bg-bg-primary border border-neutral/15 font-mono text-sm text-white focus:outline-none focus:border-data" />
            </label>
          ))}
          <div className="sm:col-span-2 lg:col-span-3 flex items-center gap-4">
            <button type="submit" disabled={speichert}
              className="px-5 py-2 rounded-lg bg-data text-bg-primary font-body text-sm font-semibold disabled:opacity-50">
              {speichert ? 'Wird gespeichert …' : 'Speichern und neu bewerten'}
            </button>
            {fehler && <span role="alert" className="font-body text-sm text-accent">{fehler}</span>}
          </div>
        </form>
      )}
    </Card>
  )
}

export default function SteckbriefTab({ jobId }: { jobId: string }) {
  const { token, user } = useAuth()
  const navigate = useNavigate()
  const berater = !!user && BERATER_ROLLEN.includes(user.role)
  const [daten, setDaten] = useState<SteckbriefDaten | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)
  const [laedt, setLaedt] = useState<'pdf' | 'export' | null>(null)

  useEffect(() => {
    if (!token) return
    getSteckbrief(jobId, token).then(setDaten).catch((e) => setFehler(e instanceof Error ? e.message : String(e)))
  }, [jobId, token])

  const download = async (art: 'pdf' | 'export') => {
    if (!token) return
    setLaedt(art)
    try {
      await herunterladen(jobId, token, art)
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e))
    } finally {
      setLaedt(null)
    }
  }

  if (fehler && !daten) {
    return <div className="rounded-2xl bg-bg-secondary p-8 text-center font-body text-sm text-neutral/70">{fehler}</div>
  }
  if (!daten) {
    return <div className="rounded-2xl bg-bg-secondary h-72 animate-pulse" aria-label="Steckbrief wird berechnet" />
  }

  const e = daten.empfehlung
  const t = daten.automatisierungstyp
  const z = daten.zyklen
  const b = daten.belastung
  const ab = daten.ablauf
  const g = daten.greifraum
  const wv = daten.wirtschaftlichkeit.verbessern
  const wa = daten.wirtschaftlichkeit.automatisieren
  const fehlend = [...new Set([...daten.verbesserungs_score.fehlend, ...daten.automatisierungs_score.fehlend])]

  return (
    <div className="flex flex-col gap-5">
      {/* recommendation */}
      <section className="rounded-2xl bg-bg-secondary p-6 md:p-8 border-l-4 border-neutral/80">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/50">Empfehlung</span>
            <p className="font-body text-sm text-neutral/60">{daten.arbeitsplatz}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => download('pdf')} disabled={laedt !== null}
              className="px-4 py-2 rounded-lg border border-neutral/15 font-body text-sm text-neutral/80 hover:border-data/50 disabled:opacity-50">
              {laedt === 'pdf' ? 'Wird erstellt …' : 'PDF-Steckbrief'}
            </button>
            <button onClick={() => download('export')} disabled={laedt !== null}
              className="px-4 py-2 rounded-lg border border-neutral/15 font-body text-sm text-neutral/80 hover:border-data/50 disabled:opacity-50">
              {laedt === 'export' ? 'Wird erstellt …' : 'JSON-Export'}
            </button>
          </div>
        </div>
        <h2 className="mt-3 font-headline text-3xl md:text-5xl font-bold tracking-tight text-white">{e.text}</h2>
        {e.erklaerung && <p className="mt-3 max-w-3xl font-body text-base text-neutral/80">{e.erklaerung}</p>}
        <div className="mt-4 flex flex-wrap gap-2">
          <span className={`font-body text-xs rounded-full px-3 py-1 ${e.status === 'bestaetigt' ? 'bg-data/15 text-data' : 'bg-neutral/10 text-neutral/70'}`}>
            {e.status === 'bestaetigt'
              ? `Vom Experten bestätigt am ${datum(e.bestaetigt_am)}${e.geaendert ? ` (Vorschlag des Tools: ${e.vorschlag_text})` : ''}`
              : `Vorschlag des Tools, noch nicht vom Experten bestätigt${e.vorlaeufig ? '; vorläufig, weil Angaben fehlen' : ''}`}
          </span>
          {e.vorrangig && (
            <span className="font-body text-xs font-semibold rounded-full px-3 py-1 bg-accent text-white">
              {e.vorrang_text} ({e.vorrang_grund})
            </span>
          )}
        </div>
        {e.gruende.length > 0 && (
          <div className="mt-5">
            <h3 className="font-body text-sm font-semibold text-white">Ausschlaggebend</h3>
            <ul className="mt-2 flex flex-col gap-1 font-body text-sm text-neutral/75 list-disc pl-5">
              {e.gruende.map((x) => <li key={x}>{x}</li>)}
            </ul>
          </div>
        )}
        {e.mit_automatisierung && (
          <p className="mt-4 font-body text-sm text-neutral/75">
            Automatisierungstyp: <span className="font-semibold text-white">{t.name ?? t.text}</span>
            {t.geaendert && t.vorschlag ? ` (Vorschlag des Tools: ${t.vorschlag})` : ''}
            <span className="text-neutral/45"> · nur der Typ, keine Herstellerempfehlung</span>
          </p>
        )}
        {e.kommentar && <p className="mt-2 font-body text-sm text-neutral/60">Kommentar des Experten: {e.kommentar}</p>}
        {berater && (
          <button onClick={() => navigate(`/app/experte/${jobId}`)}
            className="mt-4 font-body text-sm text-data underline underline-offset-4">
            Ablauf und Empfehlung in der Expertenansicht bewerten
          </button>
        )}
      </section>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <Card title="Bewertung">
          <ScoreBalken name="Verbesserungs-Score" wert={daten.verbesserungs_score.wert} schwelle={SCHWELLE.verbesserung} hoch="Verbessern lohnt sich" />
          <ScoreBalken name="Automatisierungs-Score" wert={daten.automatisierungs_score.wert} schwelle={SCHWELLE.automatisierung} hoch="Automatisieren lohnt sich" />
          {fehlend.length > 0 && (
            <p className="font-body text-xs text-neutral/50">Ohne Wert, Gewicht auf die übrigen Kriterien verteilt: {fehlend.join(', ')}.</p>
          )}
        </Card>

        <Card title="Kennzahlen" tag="Pilotphase">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
            <div>
              <Zeile label="Zykluszeit (Median)" value={kz(z.zykluszeit_median_s, (v) => `${zahl(v, 1)} s`)} />
              <Zeile label="Schwankung" value={kz(z.zykluszeit_vk, prozent)} />
              <Zeile label="Zyklen pro Schicht" value={kz(z.zyklen_pro_schicht, (v) => zahl(v))} />
              <Zeile label="Zeitanteil in Zyklen" value={kz(z.zeitanteil_in_zyklen, prozent)} />
            </div>
            <div>
              <Zeile label="Haltungsindex Mittel / Max (1 bis 10)" value={b.reba_mittel.belastbar ? `${kz(b.reba_mittel, (v) => zahl(v, 1))} / ${kz(b.reba_max, (v) => zahl(v, 1))}` : NB} />
              <Zeile label="Bücken" value={kz(b.buecken_anteil, prozent)} />
              <Zeile label="Überkopf" value={kz(b.ueberkopf_anteil, prozent)} />
              <Zeile label="Drehung" value={kz(b.drehung_anteil, prozent)} />
            </div>
          </div>
          {!z.erkannt && <p className="font-body text-xs text-neutral/50">{z.hinweis}. Das ist ein Ergebnis und fließt in die Empfehlung ein.</p>}
        </Card>

        <Card title="Ablaufschritte im Zyklus" className="md:col-span-2" tag="Pilotphase">
          {ab.bestaetigt && ab.ablaufschritte.length > 0 && ab.anteile_ablauf ? (
            <>
              <AblaufBalken schritte={ab.ablaufschritte} />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {(['wertschoepfend', 'notwendig', 'verschwendung'] as Klasse[]).map((k) => (
                  <div key={k} className="flex flex-col">
                    <span className="font-mono text-2xl font-bold text-white">{prozent(ab.anteile_ablauf![k])}</span>
                    <span className="font-body text-xs text-neutral/55">
                      {KLASSEN_TEXT[k]}
                      {ab.minuten_pro_schicht?.[k] != null ? ` · ${zahl(ab.minuten_pro_schicht[k]!)} min pro Schicht` : ''}
                    </span>
                  </div>
                ))}
              </div>
              <p className="font-body text-xs text-neutral/45">Vom Experten bestätigt am {datum(ab.bestaetigt_am)}, auf alle gültigen Zyklen übertragen.</p>
            </>
          ) : (
            <p className="font-body text-sm text-neutral/60">
              Die Ablaufschritte sind noch nicht vom Experten bestätigt. Bis dahin fehlt die Verschwendung in der Bewertung.
            </p>
          )}
        </Card>

        {g && (
          <Card title="Greifraum und Arbeitshöhen" tag="Pilotphase">
            <div className="flex flex-col gap-2">
              {ZONEN.map(([key, label]) => {
                const k = g.hoehenzonen[key]
                const ok = k.belastbar && k.wert !== null
                return (
                  <div key={key} className="grid grid-cols-[8.5rem_1fr_3.5rem] items-center gap-3">
                    <span className="font-body text-sm text-neutral/70">{label}</span>
                    <div className="h-2.5 rounded-full bg-bg-primary">
                      {ok && <div className={`h-2.5 rounded-full ${key === 'huefte_schulter' ? 'bg-data' : 'bg-data/40'}`} style={{ width: `${k.wert! * 100}%` }} />}
                    </div>
                    <span className={ok ? 'font-mono text-sm text-white text-right' : 'font-body text-[11px] text-neutral/45 text-right'}>
                      {ok ? prozent(k.wert!) : 'n. b.'}
                    </span>
                  </div>
                )
              })}
            </div>
            <Zeile label="Griffe außerhalb des günstigen Greifraums" value={kz(g.griffe_ausserhalb, prozent)} />
            <p className="font-body text-xs text-neutral/45">{g.hinweis}</p>
          </Card>
        )}

        <Card title="Wirtschaftlichkeit">
          <div className="flex flex-col gap-1">
            <h4 className="font-body text-sm font-semibold text-white">Verbessern</h4>
            {wv.berechnet ? (
              <>
                <Zeile label="Verschwendung pro Schicht" value={`${zahl(wv.verschwendung_min_schicht!)} min`} />
                <Zeile label="davon vermeidbar" value={`${zahl(wv.verbesserung_min_schicht!)} min`} />
                <Zeile label="Wert pro Jahr" value={wv.euro_jahr != null ? euro(wv.euro_jahr) : null} />
              </>
            ) : <p className="font-body text-xs text-neutral/50">{wv.grund}</p>}
          </div>
          <div className="flex flex-col gap-1">
            <h4 className="font-body text-sm font-semibold text-white">Automatisieren</h4>
            {wa.berechnet ? (
              <>
                <Zeile label="Grundlage" value={`${wa.basis}, ${zahl(wa.zykluszeit_basis_s!, 1)} s je Zyklus`} />
                <Zeile label="Stunden pro Jahr" value={bereich(wa.stunden_jahr, (v) => zahl(v))} />
                <Zeile label="Ersparnis netto pro Jahr" value={bereich(wa.euro_jahr_netto, euro)} />
                <Zeile label="Betriebskosten abgezogen" value={bereich(wa.betriebskosten_anteil, prozent)} />
                <Zeile label={`Investition (${wa.investition_quelle})`} value={bereich(wa.investition_euro, euro)} />
                <Zeile label="Amortisation" value={bereich(wa.amortisation_jahre, (v) => zahl(v, 1)) && `${bereich(wa.amortisation_jahre, (v) => zahl(v, 1))} Jahre`} />
              </>
            ) : <p className="font-body text-xs text-neutral/50">{wa.grund}</p>}
          </div>
          {[...(wv.fehlende_angaben ?? []), ...(wa.fehlende_angaben ?? [])].length > 0 && (
            <p className="font-body text-xs text-neutral/50">
              Für Euro-Werte fehlt: {[...new Set([...(wv.fehlende_angaben ?? []), ...(wa.fehlende_angaben ?? [])])].join(', ')}.
            </p>
          )}
          <p className="font-body text-sm font-semibold text-white">{daten.wirtschaftlichkeit.hinweis}</p>
        </Card>

        <Angaben jobId={jobId} daten={daten} onSaved={setDaten} />
      </div>

      {daten.hinweise.length > 0 && (
        <ul className="flex flex-col gap-1 font-body text-xs text-neutral/50 list-disc pl-5">
          {daten.hinweise.map((h) => <li key={h}>{h}</li>)}
        </ul>
      )}
      {fehler && <p role="alert" className="font-body text-sm text-accent">{fehler}</p>}
    </div>
  )
}
