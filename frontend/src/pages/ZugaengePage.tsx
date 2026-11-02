import { useEffect, useState, type FormEvent } from 'react'
import { getZugaenge, removeZugang, setZugang, type Zugang } from '../api/jobs'
import { useAuth } from '../auth/AuthContext'
import AppNav from '../components/AppNav'

const ROLLEN: { id: Zugang['role']; text: string }[] = [
  { id: 'berater', text: 'Berater (alle Jobs, Expertenansicht)' },
  { id: 'admin', text: 'Admin (zusätzlich Zugänge)' },
  { id: 'user', text: 'Benutzer (nur eigene Jobs)' },
]

const inputCls = 'px-3 py-2 rounded-lg bg-bg-primary border border-bg-secondary font-body text-sm text-white focus:outline-none focus:border-data/50'

/**
 * Access grants (admins only): who may sign in with Firebase. The account
 * itself is created by Firebase on the first sign-in (Google, Microsoft) or
 * in the Firebase console (e-mail and password).
 */
export default function ZugaengePage() {
  const { token, user } = useAuth()
  const [liste, setListe] = useState<Zugang[] | null>(null)
  const [email, setEmail] = useState('')
  const [rolle, setRolle] = useState<Zugang['role']>('berater')
  const [name, setName] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  const laden = () => { if (token) getZugaenge(token).then(setListe).catch((e: Error) => setFehler(e.message)) }
  useEffect(laden, [token])

  if (user?.role !== 'admin') {
    return (
      <div className="min-h-screen bg-bg-primary text-white"><AppNav />
        <p className="max-w-3xl mx-auto px-6 py-8 font-body text-sm text-neutral/60">Nur für Admins.</p>
      </div>
    )
  }

  const hinzufuegen = async (e: FormEvent) => {
    e.preventDefault()
    if (!token) return
    setFehler(null)
    try {
      await setZugang(token, email.trim(), rolle, name.trim())
      setEmail('')
      setName('')
      laden()
    } catch (err) {
      setFehler(err instanceof Error ? err.message : String(err))
    }
  }

  const entfernen = async (z: Zugang) => {
    if (!token || !window.confirm(`Zugang für ${z.email} entfernen?`)) return
    try {
      await removeZugang(token, z.email)
      laden()
    } catch (err) {
      setFehler(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <div className="min-h-screen bg-bg-primary text-white">
      <AppNav />
      <main className="max-w-3xl mx-auto px-6 py-8 flex flex-col gap-6">
        <div>
          <h1 className="font-headline text-2xl font-bold">Zugänge</h1>
          <p className="font-body text-sm text-neutral/60 mt-2">
            Nur hier eingetragene Adressen können sich anmelden. Wer sich mit Google oder Microsoft anmeldet, braucht kein weiteres Konto. Für E-Mail und Passwort legen Sie das Konto zusätzlich in der Firebase-Konsole an.
          </p>
        </div>

        <form onSubmit={hinzufuegen} className="flex flex-wrap gap-3 items-end rounded-2xl bg-bg-secondary p-4">
          <label className="flex flex-col gap-1.5 flex-1 min-w-[14rem]">
            <span className="font-body text-xs text-neutral/50">E-Mail</span>
            <input className={inputCls} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1.5 flex-1 min-w-[10rem]">
            <span className="font-body text-xs text-neutral/50">Name (optional)</span>
            <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="font-body text-xs text-neutral/50">Rolle</span>
            <select className={inputCls} value={rolle} onChange={(e) => setRolle(e.target.value as Zugang['role'])}>
              {ROLLEN.map((r) => <option key={r.id} value={r.id}>{r.text}</option>)}
            </select>
          </label>
          <button type="submit" className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 font-body text-sm">Freigeben</button>
        </form>

        {fehler && <p className="font-body text-sm text-accent" role="alert">{fehler}</p>}

        {liste && (
          <ul className="rounded-2xl bg-bg-secondary divide-y divide-bg-primary">
            {liste.map((z) => (
              <li key={z.email} className="p-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-body text-sm text-white">{z.email}{z.name ? `, ${z.name}` : ''}</p>
                  <p className="font-body text-xs text-neutral/50">{ROLLEN.find((r) => r.id === z.role)?.text ?? z.role}{z.fest ? ', fest eingetragen (ADMIN_EMAILS)' : ''}</p>
                </div>
                {!z.fest && z.email !== user.email && (
                  <button onClick={() => entfernen(z)} className="font-body text-xs text-neutral/50 hover:text-accent underline underline-offset-4">Entfernen</button>
                )}
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  )
}
