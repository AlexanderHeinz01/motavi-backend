import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ART_TEXT,
  KLASSEN_TEXT,
  getAblauf,
  putReview,
  type AblaufResponse,
  type Art,
  type Klasse,
} from '../api/workplace'
import { useAuth } from '../auth/AuthContext'

/**
 * Expert view (STECKBRIEF_MODUL §4.3): proposal of segments in the median
 * cycle on a timeline; the consultant assigns a type to each segment and
 * confirms or changes its class. Saving transfers the steps to all cycles.
 */

interface Zeile {
  start_phase: number
  ende_phase: number
  art: Art | null // from the proposal; null after a manual split of unequal kinds
  typ: string
  klasse: Klasse | ''
}

const KLASSEN: Klasse[] = ['wertschoepfend', 'notwendig', 'verschwendung']
const FARBE = '#00b4d8' // dashboard data colour

function fmt(v: number, digits = 1) {
  return v.toFixed(digits).replace('.', ',')
}

function Kachel({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex flex-col">
      <span className="font-mono text-2xl font-bold text-white">{value}</span>
      <span className="font-body text-xs text-neutral/50">{label}</span>
      {sub && <span className="font-body text-xs text-neutral/40">{sub}</span>}
    </div>
  )
}

/** Fill per class: strong, medium, hatched (never colour alone). */
function fill(k: Klasse | '') {
  if (k === 'wertschoepfend') return FARBE
  if (k === 'notwendig') return 'rgba(0,180,216,0.35)'
  if (k === 'verschwendung') return 'url(#schraffur)'
  return 'rgba(244,244,246,0.06)'
}

function Zeitleiste({
  data,
  zeilen,
  aktiv,
  onSelect,
}: {
  data: NonNullable<AblaufResponse['median_zyklus']>
  zeilen: Zeile[]
  aktiv: number
  onSelect: (i: number) => void
}) {
  const W = 1000
  const H = 190
  const top = 20
  const chartH = 90
  const barY = top + chartH + 18
  const barH = 40
  const max = Math.max(1, ...data.hand_speed, ...data.hip_speed)
  const line = (v: number[]) =>
    v.map((y, i) => `${i ? 'L' : 'M'}${(data.phase[i] * W).toFixed(1)} ${(top + chartH - (y / max) * chartH).toFixed(1)}`).join('')
  const ticks = Array.from({ length: Math.floor(data.dauer_s) + 1 }, (_, s) => s)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Zeitleiste des Median-Zyklus mit Geschwindigkeiten und Segmenten">
      <defs>
        <pattern id="schraffur" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill="rgba(0,180,216,0.08)" />
          <line x1="0" y1="0" x2="0" y2="8" stroke={FARBE} strokeWidth="2.5" />
        </pattern>
      </defs>
      {/* speeds */}
      <line x1="0" y1={top + chartH} x2={W} y2={top + chartH} stroke="rgba(244,244,246,0.15)" />
      <path d={line(data.hand_speed)} fill="none" stroke={FARBE} strokeWidth="2" />
      <path d={line(data.hip_speed)} fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="6 4" />
      <text x="4" y="12" fill="rgba(244,244,246,0.5)" fontSize="12" fontFamily="JetBrains Mono, monospace">
        Hand (durchgezogen) und Hüfte (gestrichelt), Rumpflängen pro Sekunde
      </text>
      {/* segments */}
      {zeilen.map((z, i) => {
        const x = z.start_phase * W
        const w = (z.ende_phase - z.start_phase) * W
        return (
          <g key={i} onClick={() => onSelect(i)} style={{ cursor: 'pointer' }}>
            <rect x={x + 1} y={barY} width={Math.max(1, w - 2)} height={barH} rx="3" fill={fill(z.klasse)}
              stroke={i === aktiv ? '#ffffff' : 'rgba(0,180,216,0.6)'} strokeWidth={i === aktiv ? 2.5 : 1} />
            {w > 60 && (
              <text x={x + w / 2} y={barY + barH / 2 + 4} textAnchor="middle" fontSize="13"
                fontFamily="Inter, sans-serif"
                // dark text on the bright fill (white on cyan has too little contrast)
                fill={z.klasse === 'wertschoepfend' ? '#0a0f1e' : '#ffffff'}
                style={z.klasse === 'wertschoepfend' ? undefined : { paintOrder: 'stroke', stroke: '#0a0f1e', strokeWidth: 3 }}>
                {z.typ || (z.art ? ART_TEXT[z.art] : '?')}
              </text>
            )}
          </g>
        )
      })}
      {/* time axis in seconds */}
      {ticks.map((s) => (
        <g key={s}>
          <line x1={(s / data.dauer_s) * W} y1={barY + barH + 2} x2={(s / data.dauer_s) * W} y2={barY + barH + 7} stroke="rgba(244,244,246,0.3)" />
          <text x={(s / data.dauer_s) * W} y={barY + barH + 19} textAnchor={s === 0 ? 'start' : (s / data.dauer_s) * W > W - 20 ? 'end' : 'middle'} fontSize="11" fill="rgba(244,244,246,0.45)" fontFamily="JetBrains Mono, monospace">
            {s} s
          </text>
        </g>
      ))}
    </svg>
  )
}

export default function ExpertPage() {
  const { jobId = '' } = useParams<{ jobId: string }>()
  const { token } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState<AblaufResponse | null>(null)
  const [zeilen, setZeilen] = useState<Zeile[]>([])
  const [aktiv, setAktiv] = useState(0)
  const [kommentar, setKommentar] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [speichert, setSpeichert] = useState(false)

  const uebernehmen = (d: AblaufResponse) => {
    setData(d)
    if (d.review) {
      setZeilen(d.review.segmente.map((s) => {
        const art = d.vorschlag.find((v) => Math.abs(v.start_phase - s.start_phase) < 1e-6)?.art ?? null
        return { start_phase: s.start_phase, ende_phase: s.ende_phase, art, typ: s.typ, klasse: s.klasse ?? d.typen[s.typ] ?? '' }
      }))
      setKommentar(d.review.kommentar ?? '')
    } else {
      setZeilen(d.vorschlag.map((v) => ({
        start_phase: v.start_phase, ende_phase: v.ende_phase, art: v.art,
        typ: v.vorschlag_typ ?? '', klasse: v.vorschlag_typ ? d.typen[v.vorschlag_typ] : '',
      })))
    }
  }

  useEffect(() => {
    if (!token) return
    getAblauf(jobId, token).then(uebernehmen).catch((e: Error) => setFehler(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, token])

  const dauer = data?.median_zyklus?.dauer_s ?? 0
  const typen = data ? Object.keys(data.typen) : []
  const vollstaendig = zeilen.length > 0 && zeilen.every((z) => z.typ && z.klasse)

  // live shares of the median cycle
  const anteile = useMemo(() => {
    const out: Record<Klasse, number> = { wertschoepfend: 0, notwendig: 0, verschwendung: 0 }
    for (const z of zeilen) if (z.klasse) out[z.klasse] += z.ende_phase - z.start_phase
    return out
  }, [zeilen])

  const setZeile = (i: number, patch: Partial<Zeile>) =>
    setZeilen((zs) => zs.map((z, k) => (k === i ? { ...z, ...patch } : z)))

  const teilen = (i: number) =>
    setZeilen((zs) => {
      const z = zs[i]
      const mitte = (z.start_phase + z.ende_phase) / 2
      return [...zs.slice(0, i), { ...z, ende_phase: mitte }, { ...z, start_phase: mitte }, ...zs.slice(i + 1)]
    })

  const zusammenfuehren = (i: number) =>
    setZeilen((zs) => {
      if (i >= zs.length - 1) return zs
      const a = zs[i]
      const b = zs[i + 1]
      return [...zs.slice(0, i), { ...a, ende_phase: b.ende_phase, art: a.art === b.art ? a.art : null }, ...zs.slice(i + 2)]
    })

  const speichern = async () => {
    if (!token) return
    setFehler(null)
    setSpeichert(true)
    try {
      const d = await putReview(jobId, token, zeilen.map((z) => ({
        start_phase: z.start_phase, ende_phase: z.ende_phase, typ: z.typ, klasse: z.klasse || null,
      })), kommentar)
      uebernehmen(d)
    } catch (e) {
      setFehler((e as Error).message)
    } finally {
      setSpeichert(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg-primary text-white">
      <header className="border-b border-bg-secondary px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate(`/app/dashboard/${jobId}`)} className="text-neutral/40 hover:text-neutral/80" aria-label="Zurück zum Dashboard">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="font-headline text-xl font-bold tracking-tight">MOTAVI</h1>
        <span className="font-body text-sm text-neutral/60">Ablaufschritte bewerten</span>
        <span className="font-mono text-xs text-neutral/30 hidden sm:block">{jobId.slice(0, 8)}…</span>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 flex flex-col gap-6">
        {fehler && <div role="alert" className="rounded-xl border border-accent/50 bg-accent/10 px-4 py-3 font-body text-sm text-white">{fehler}</div>}
        {!data && !fehler && <p className="font-body text-sm text-neutral/50">Lädt…</p>}

        {data && (
          <>
            <section className="rounded-2xl bg-bg-secondary p-5 flex flex-wrap gap-8 items-center">
              <Kachel label="Median-Zyklus" value={data.zyklen.median_s ? `${fmt(data.zyklen.median_s)} s` : '–'} />
              <Kachel label="gültige Zyklen" value={String(data.zyklen.anzahl_gueltig)} />
              <Kachel label="Konfidenz" value={fmt(data.zyklen.konfidenz, 2)} />
              <div className="ml-auto">
                {data.review ? (
                  <span className="rounded-full border border-data/60 px-3 py-1 font-mono text-xs uppercase tracking-widest text-data">
                    Bestätigt von {data.review.bestaetigt_von}, {new Date(data.review.bestaetigt_am).toLocaleString('de-DE')}
                  </span>
                ) : (
                  <span className="rounded-full border border-neutral/30 px-3 py-1 font-mono text-xs uppercase tracking-widest text-neutral/60">
                    Vorschlag, noch nicht bestätigt
                  </span>
                )}
              </div>
            </section>

            {!data.zyklen.erkannt && (
              <section className="rounded-2xl bg-bg-secondary p-5 font-body text-sm text-neutral/70">
                {data.zyklen.hinweis}. Ohne wiederkehrenden Zyklus gibt es keinen Median-Zyklus und keine Übertragung.
              </section>
            )}

            {data.median_zyklus && (
              <>
                <section className="rounded-2xl bg-bg-secondary p-5">
                  <h2 className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/40 mb-3">
                    Median-Zyklus aus {data.median_zyklus.anzahl_zyklen} Zyklen
                  </h2>
                  <Zeitleiste data={data.median_zyklus} zeilen={zeilen} aktiv={aktiv} onSelect={setAktiv} />
                  <ul className="mt-3 flex flex-wrap gap-5 font-body text-xs text-neutral/60">
                    {KLASSEN.map((k) => (
                      <li key={k} className="flex items-center gap-2">
                        <svg width="20" height="12" aria-hidden="true"><rect width="20" height="12" rx="2" fill={k === 'verschwendung' ? 'none' : fill(k)} stroke={FARBE} />{k === 'verschwendung' && <path d="M0 12L12 0M6 12L18 0M12 12L20 4" stroke={FARBE} strokeWidth="2" />}</svg>
                        {KLASSEN_TEXT[k]}
                      </li>
                    ))}
                    <li className="flex items-center gap-2"><svg width="20" height="12" aria-hidden="true"><rect width="20" height="12" rx="2" fill="rgba(244,244,246,0.06)" stroke={FARBE} /></svg>noch nicht zugeordnet</li>
                  </ul>
                </section>

                <section className="rounded-2xl bg-bg-secondary p-5 overflow-x-auto">
                  <h2 className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/40 mb-3">Segmente</h2>
                  <table className="w-full min-w-[760px] font-body text-sm">
                    <thead>
                      <tr className="text-left text-neutral/40 text-xs uppercase tracking-wider">
                        <th className="py-2 pr-3 font-medium">Nr.</th>
                        <th className="py-2 pr-3 font-medium">Zeit im Zyklus</th>
                        <th className="py-2 pr-3 font-medium">Dauer</th>
                        <th className="py-2 pr-3 font-medium">Erkannt</th>
                        <th className="py-2 pr-3 font-medium">Typ</th>
                        <th className="py-2 pr-3 font-medium">Einstufung</th>
                        <th className="py-2 font-medium"><span className="sr-only">Aktionen</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {zeilen.map((z, i) => {
                        const geaendert = z.typ && z.klasse && data.typen[z.typ] !== z.klasse
                        return (
                          <tr key={i} onClick={() => setAktiv(i)} className={`border-t border-white/5 ${i === aktiv ? 'bg-white/5' : ''}`}>
                            <td className="py-2 pr-3 font-mono text-neutral/60">{i + 1}</td>
                            <td className="py-2 pr-3 font-mono">{fmt(z.start_phase * dauer)} bis {fmt(z.ende_phase * dauer)} s</td>
                            <td className="py-2 pr-3 font-mono">{fmt((z.ende_phase - z.start_phase) * dauer)} s</td>
                            <td className="py-2 pr-3 text-neutral/60">{z.art ? ART_TEXT[z.art] : '–'}</td>
                            <td className="py-2 pr-3">
                              <select aria-label={`Typ für Segment ${i + 1}`} value={z.typ}
                                onChange={(e) => setZeile(i, { typ: e.target.value, klasse: e.target.value ? data.typen[e.target.value] : '' })}
                                className="rounded-lg bg-bg-primary border border-white/20 px-2 py-1.5 text-white focus:outline-none focus:ring-2 focus:ring-data">
                                <option value="">Typ wählen</option>
                                {typen.map((t) => <option key={t} value={t}>{t}</option>)}
                              </select>
                            </td>
                            <td className="py-2 pr-3">
                              <select aria-label={`Einstufung für Segment ${i + 1}`} value={z.klasse}
                                onChange={(e) => setZeile(i, { klasse: e.target.value as Klasse })}
                                className="rounded-lg bg-bg-primary border border-white/20 px-2 py-1.5 text-white focus:outline-none focus:ring-2 focus:ring-data">
                                <option value="">Einstufung wählen</option>
                                {KLASSEN.map((k) => <option key={k} value={k}>{KLASSEN_TEXT[k]}</option>)}
                              </select>
                              {geaendert && <span className="ml-2 font-mono text-[11px] text-data">geändert</span>}
                            </td>
                            <td className="py-2 whitespace-nowrap">
                              <button onClick={(e) => { e.stopPropagation(); teilen(i) }} className="px-2 py-1 text-xs text-neutral/70 hover:text-white underline underline-offset-4">Teilen</button>
                              {i < zeilen.length - 1 && (
                                <button onClick={(e) => { e.stopPropagation(); zusammenfuehren(i) }} className="px-2 py-1 text-xs text-neutral/70 hover:text-white underline underline-offset-4">Mit nächstem zusammenführen</button>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </section>

                <section className="rounded-2xl bg-bg-secondary p-5 grid gap-6 md:grid-cols-2">
                  <div>
                    <h2 className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/40 mb-3">Anteile im Median-Zyklus</h2>
                    <dl className="flex flex-col gap-2 font-body text-sm">
                      {KLASSEN.map((k) => (
                        <div key={k} className="flex justify-between border-b border-white/5 pb-1">
                          <dt className="text-neutral/70">{KLASSEN_TEXT[k]}</dt>
                          <dd className="font-mono">{fmt(anteile[k] * 100, 0)} % · {fmt(anteile[k] * dauer)} s</dd>
                        </div>
                      ))}
                    </dl>
                    <label className="mt-4 block font-body text-sm text-neutral/70" htmlFor="kommentar">Kommentar (optional)</label>
                    <textarea id="kommentar" value={kommentar} onChange={(e) => setKommentar(e.target.value)} rows={2}
                      className="mt-1 w-full rounded-lg bg-bg-primary border border-white/20 px-3 py-2 font-body text-sm text-white focus:outline-none focus:ring-2 focus:ring-data" />
                    <button onClick={speichern} disabled={!vollstaendig || speichert}
                      className="mt-4 rounded-xl bg-brand px-5 py-2.5 font-body text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-40 disabled:cursor-not-allowed">
                      {speichert ? 'Speichert…' : `Bestätigen und auf alle ${data.zyklen.anzahl_gueltig} Zyklen übertragen`}
                    </button>
                    {!vollstaendig && <p className="mt-2 font-body text-xs text-neutral/50">Jedem Segment Typ und Einstufung zuordnen.</p>}
                  </div>

                  <div>
                    <h2 className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/40 mb-3">Übertragen auf alle Zyklen</h2>
                    {data.ergebnis ? (
                      <dl className="flex flex-col gap-2 font-body text-sm">
                        {KLASSEN.map((k) => (
                          <div key={k} className="flex justify-between border-b border-white/5 pb-1">
                            <dt className="text-neutral/70">{KLASSEN_TEXT[k]}</dt>
                            <dd className="font-mono">
                              {fmt(data.ergebnis!.anteile_ablauf[k] * 100, 0)} % · {fmt(data.ergebnis!.sekunden_je_zyklus[k])} s je Zyklus
                              {data.ergebnis!.minuten_pro_schicht[k] != null && ` · ${fmt(data.ergebnis!.minuten_pro_schicht[k]!, 0)} min pro Schicht`}
                            </dd>
                          </div>
                        ))}
                        <p className="mt-2 text-xs text-neutral/50">{data.ergebnis.hinweis} ({data.ergebnis.anzahl_zyklen} Zyklen)</p>
                      </dl>
                    ) : (
                      <p className="font-body text-sm text-neutral/50">Noch keine bestätigte Bewertung.</p>
                    )}
                  </div>
                </section>
              </>
            )}
          </>
        )}
      </main>
    </div>
  )
}
