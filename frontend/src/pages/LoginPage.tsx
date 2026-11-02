import { useState, type FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const inputCls =
  'w-full px-3 py-2.5 rounded-lg bg-bg-primary border border-bg-secondary focus:outline-none ' +
  'focus:border-data/50 font-body text-sm text-white placeholder:text-neutral/30'
const knopfCls =
  'w-full py-3 rounded-xl font-body text-sm border border-neutral/20 text-white hover:border-data/60 transition-colors'

/** Sign-in of the internal tool: options from the backend (Firebase or the former password sign-in). */
export default function LoginPage() {
  const { user, loading, anbieter, hinweis, loginPasswort, loginGoogle, loginMicrosoft, passwortVergessen, erneutPruefen, logout } = useAuth()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [passwort, setPasswort] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const ziel = (location.state as { from?: { pathname: string } } | null)?.from?.pathname || '/app/jobs'
  if (!loading && user) return <Navigate to={ziel} replace />

  const ausfuehren = async (f: () => Promise<void>) => {
    setFehler(null)
    setInfo(null)
    setBusy(true)
    try {
      await f()
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const mitPasswort = anbieter.includes('password') || anbieter.includes('passwort_alt')
  const senden = (e: FormEvent) => {
    e.preventDefault()
    void ausfuehren(() => loginPasswort(email, passwort))
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm flex flex-col gap-5">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-neutral/40">Motavi</p>
          <h1 className="font-headline text-3xl font-bold text-white mt-2">Anmelden</h1>
          <p className="font-body text-sm text-neutral/60 mt-2">Zugang für freigegebene Benutzer: Videos hochladen und Ergebnisse im Dashboard ansehen.</p>
        </div>

        {loading && <p className="font-body text-sm text-neutral/50">Lädt …</p>}

        {!loading && (
          <>
            {anbieter.includes('google') && (
              <button className={knopfCls} disabled={busy} onClick={() => ausfuehren(loginGoogle)}>Mit Google anmelden</button>
            )}
            {anbieter.includes('microsoft') && (
              <button className={knopfCls} disabled={busy} onClick={() => ausfuehren(loginMicrosoft)}>Mit Microsoft anmelden</button>
            )}
            {mitPasswort && (
              <form onSubmit={senden} className="flex flex-col gap-3">
                <label className="flex flex-col gap-1.5">
                  <span className="font-body text-xs text-neutral/50">E-Mail</span>
                  <input className={inputCls} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="font-body text-xs text-neutral/50">Passwort</span>
                  <input className={inputCls} type="password" autoComplete="current-password" required value={passwort} onChange={(e) => setPasswort(e.target.value)} />
                </label>
                <button type="submit" disabled={busy} className="w-full py-3 rounded-xl font-headline font-semibold text-base bg-accent hover:bg-accent/90 text-white">
                  Anmelden
                </button>
                {anbieter.includes('password') && (
                  <button
                    type="button"
                    className="font-body text-xs text-neutral/50 underline underline-offset-4 self-start"
                    onClick={() =>
                      email
                        ? ausfuehren(async () => { await passwortVergessen(email); setInfo('Wir haben Ihnen einen Link zum Zurücksetzen geschickt.') })
                        : setFehler('Bitte zuerst die E-Mail-Adresse eintragen.')
                    }
                  >
                    Passwort vergessen
                  </button>
                )}
              </form>
            )}
          </>
        )}

        {fehler && <p className="font-body text-sm text-accent" role="alert">{fehler}</p>}
        {info && <p className="font-body text-sm text-data">{info}</p>}
        {hinweis && (
          <div className="rounded-xl border border-bg-secondary p-4 flex flex-col gap-3">
            <p className="font-body text-sm text-white">{hinweis}</p>
            <div className="flex gap-4">
              <button className="font-body text-xs text-data underline underline-offset-4" onClick={() => ausfuehren(erneutPruefen)}>Erneut prüfen</button>
              <button className="font-body text-xs text-neutral/50 underline underline-offset-4" onClick={logout}>Abmelden</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
