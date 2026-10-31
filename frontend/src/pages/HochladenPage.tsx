import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getUploadLink, uploadViaLink, type UploadLinkInfo } from '../api/motavi'
import UploadZone from '../components/UploadZone'

type Phase = 'laden' | 'bereit' | 'hochladen' | 'fertig' | 'fehler'

/**
 * Upload page for customers (decision G2 on 31.10.2026): opened through a
 * personal upload link, no sign-in. The customer sees no results; the
 * Motavi team evaluates and sends the report.
 */
export default function HochladenPage() {
  const { token = '' } = useParams()
  const [info, setInfo] = useState<UploadLinkInfo | null>(null)
  const [phase, setPhase] = useState<Phase>('laden')
  const [datei, setDatei] = useState<File | null>(null)
  const [fortschritt, setFortschritt] = useState(0)
  const [fehler, setFehler] = useState<string | null>(null)

  useEffect(() => {
    getUploadLink(token)
      .then((i) => { setInfo(i); setPhase('bereit') })
      .catch((e: Error) => { setFehler(e.message); setPhase('fehler') })
  }, [token])

  const senden = async () => {
    if (!datei) return
    setPhase('hochladen')
    setFehler(null)
    try {
      await uploadViaLink(token, datei, setFortschritt)
      setPhase('fertig')
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e))
      setPhase('bereit')
    }
  }

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col items-center px-6 py-12">
      <div className="w-full max-w-xl flex flex-col gap-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-neutral/40">Motavi Video-Check</p>
          <h1 className="font-headline text-3xl font-bold text-white mt-2">Video hochladen</h1>
          {info?.arbeitsplatz && <p className="font-body text-base text-neutral/60 mt-2">Arbeitsplatz: {info.arbeitsplatz}</p>}
        </div>

        {phase === 'laden' && <p className="font-body text-sm text-neutral/50">Link wird geprüft …</p>}

        {phase === 'fehler' && <p className="font-body text-base text-accent">{fehler}</p>}

        {phase === 'fertig' && (
          <div className="rounded-xl border border-bg-secondary p-5">
            <p className="font-body text-base text-white">Vielen Dank. Ihr Video ist angekommen.</p>
            <p className="font-body text-sm text-neutral/60 mt-2">
              Das Originalvideo wird unmittelbar nach der Auswertung automatisch gelöscht. Den Report erhalten Sie von uns.
            </p>
          </div>
        )}

        {(phase === 'bereit' || phase === 'hochladen') && info && (
          <>
            <ul className="font-body text-sm text-neutral/70 space-y-1.5 list-disc pl-5">
              <li>Kamera fest aufstellen, seitlich oder schräg von vorn.</li>
              <li>Die ganze Person im Bild, von Kopf bis Fuß, möglichst nur eine Person.</li>
              <li>Mindestens fünf, besser zehn vollständige Arbeitsdurchgänge.</li>
              <li>Gutes Licht, kein starkes Gegenlicht.</li>
              <li>Wir empfehlen, die Beschäftigten vorher zu informieren und den Betriebsrat zu beteiligen.</li>
            </ul>
            <UploadZone onFile={(f) => { setDatei(f); setFehler(null) }} disabled={phase === 'hochladen'} maxBytes={info.max_bytes} />
            {datei && <p className="font-mono text-xs text-neutral/50">{datei.name}</p>}
            {phase === 'hochladen' && (
              <div className="w-full h-1.5 rounded-full bg-bg-secondary overflow-hidden">
                <div className="h-full bg-data rounded-full transition-all duration-200" style={{ width: `${fortschritt}%` }} />
              </div>
            )}
            {fehler && <p className="font-body text-sm text-accent">{fehler}</p>}
            {datei && phase === 'bereit' && (
              <button onClick={senden} className="w-full py-3.5 rounded-xl font-headline font-semibold text-base bg-accent hover:bg-accent/90 text-white">
                Video übermitteln
              </button>
            )}
            <p className="font-body text-xs text-neutral/40">
              Der Link gilt bis {new Date(info.gueltig_bis).toLocaleDateString('de-DE')} und für ein Video. Die Analyse läuft auf Servern in Deutschland (Frankfurt).
            </p>
          </>
        )}
      </div>
    </div>
  )
}
