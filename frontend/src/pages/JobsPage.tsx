import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getJobs, type JobEintrag } from '../api/jobs'
import { useAuth } from '../auth/AuthContext'
import AppNav from '../components/AppNav'

const STATUS: Record<string, string> = {
  wartet_auf_upload: 'wartet auf Video',
  processing: 'Analyse läuft',
  fertig: 'fertig',
  fehler: 'Fehler',
}

const datum = (iso: string | null) => (iso ? new Date(iso).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' }) : '')

/** Dashboard: all jobs the user may see, newest first, with links to the results. */
export default function JobsPage() {
  const { token } = useAuth()
  const [jobs, setJobs] = useState<JobEintrag[] | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    getJobs(token).then(setJobs).catch((e: Error) => setFehler(e.message))
  }, [token])

  return (
    <div className="min-h-screen bg-bg-primary text-white">
      <AppNav />
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
          <h1 className="font-headline text-2xl font-bold">Dashboard</h1>
          <Link to="/app" className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 font-body text-sm">
            Video hochladen oder Upload-Link erstellen
          </Link>
        </div>
        {fehler && <p className="font-body text-sm text-accent">{fehler}</p>}
        {!jobs && !fehler && <p className="font-body text-sm text-neutral/50">Lädt …</p>}
        {jobs && jobs.length === 0 && <p className="font-body text-sm text-neutral/60">Noch keine Jobs. Laden Sie ein Video hoch oder erstellen Sie einen Upload-Link.</p>}
        {jobs && jobs.length > 0 && (
          <div className="overflow-x-auto rounded-2xl bg-bg-secondary">
            <table className="w-full font-body text-sm">
              <thead>
                <tr className="text-left text-neutral/50 border-b border-bg-primary">
                  <th className="p-4 font-normal">Arbeitsplatz</th>
                  <th className="p-4 font-normal">Angelegt</th>
                  <th className="p-4 font-normal">Weg</th>
                  <th className="p-4 font-normal">Status</th>
                  <th className="p-4 font-normal"><span className="sr-only">Öffnen</span></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.job_id} className="border-b border-bg-primary last:border-0">
                    <td className="p-4">
                      <span className="text-white">{j.arbeitsplatz || 'ohne Bezeichnung'}</span>
                      {j.unternehmen && <span className="block text-xs text-neutral/40">{j.unternehmen}</span>}
                    </td>
                    <td className="p-4 text-neutral/70">
                      {datum(j.erstellt_am)}
                      {j.erstellt_von && <span className="block text-xs text-neutral/40">{j.erstellt_von}</span>}
                    </td>
                    <td className="p-4 text-neutral/70">{j.quelle === 'upload_link' ? 'Upload-Link' : 'intern'}</td>
                    <td className="p-4">
                      <span className={j.status === 'fehler' ? 'text-accent' : j.status === 'fertig' ? 'text-white' : 'text-neutral/60'}>
                        {STATUS[j.status ?? ''] ?? j.status}
                      </span>
                      {j.status === 'wartet_auf_upload' && j.link_gueltig_bis && (
                        <span className="block text-xs text-neutral/40">Link gültig bis {new Date(j.link_gueltig_bis).toLocaleDateString('de-DE')}</span>
                      )}
                    </td>
                    <td className="p-4 text-right whitespace-nowrap">
                      {(j.status === 'fertig' || j.status === 'fehler') && (
                        <Link to={`/app/dashboard/${j.job_id}`} className="text-data underline underline-offset-4">Ergebnis</Link>
                      )}
                      {j.status === 'processing' && (
                        <Link to={`/app/analyzing/${j.job_id}`} className="text-neutral/60 underline underline-offset-4">Fortschritt</Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
