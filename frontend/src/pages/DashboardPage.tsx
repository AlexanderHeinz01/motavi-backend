import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { downloadReport, frameUrl } from '../api/motavi'
import { BERATER_ROLLEN } from '../api/workplace'
import { useAuth } from '../auth/AuthContext'
import ActionItems   from '../components/ActionItems'
import BodyHeatmap   from '../components/BodyHeatmap'
import MovementChart from '../components/MovementChart'
import REBAGauge     from '../components/REBAGauge'
import SteckbriefTab from '../components/SteckbriefTab'
import TimelineChart from '../components/TimelineChart'
import { useAnalysis } from '../hooks/useAnalysis'
import { rebaStufe, rebaText } from '../lib/rebaStufe'

function Card({
  title, children, className = '', tag,
}: {
  title: string
  children: React.ReactNode
  className?: string
  /** e.g. "Pilotphase" for values not yet validated */
  tag?: string
}) {
  return (
    <div className={`rounded-2xl bg-bg-secondary p-5 flex flex-col gap-4 ${className}`}>
      <h3 className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/40 flex items-center gap-2">
        {title}
        {tag && <span className="rounded border border-amber-400/40 px-1.5 py-0.5 font-mono text-[10px] text-amber-300 normal-case tracking-normal">{tag}</span>}
      </h3>
      {children}
    </div>
  )
}

function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`rounded-2xl bg-bg-secondary animate-pulse ${className}`} />
  )
}

export default function DashboardPage() {
  const { jobId }  = useParams<{ jobId: string }>()
  const navigate   = useNavigate()
  const { status, result, error } = useAnalysis(jobId)
  const { user, token } = useAuth()
  const [reportFehler, setReportFehler] = useState<string | null>(null)
  const berater = !!user && BERATER_ROLLEN.includes(user.role)
  // tab in the URL (?tab=steckbrief), so a link opens the Steckbrief directly
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'steckbrief' ? 'steckbrief' : 'ergonomie'

  const loading = status === 'processing'
  const failed  = status === 'error'

  if (failed) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center px-6">
        <div className="max-w-md w-full p-8 rounded-2xl bg-bg-secondary text-center">
          <p className="font-headline text-xl text-accent mb-2">Analyse fehlgeschlagen</p>
          <p className="font-body text-sm text-neutral/60 mb-6">{error}</p>
          <button onClick={() => navigate('/app')}
            className="px-6 py-2.5 rounded-xl bg-accent text-white font-body text-sm hover:bg-accent/90 transition-colors">
            Neues Video
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary text-white">
      {/* Top bar */}
      <header className="border-b border-bg-secondary px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/app')}
            className="text-neutral/30 hover:text-neutral/70 transition-colors"
            aria-label="Zurück"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="font-headline text-xl font-bold tracking-tight">MOTAVI</h1>
          {jobId && (
            <span className="font-mono text-xs text-neutral/30 hidden sm:block">
              {jobId.slice(0, 8)}…
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
        {/* Expert view, only for consultants */}
        {result && berater && (
          <button
            onClick={() => navigate(`/app/experte/${result.job_id}`)}
            className="px-4 py-2 rounded-lg bg-bg-secondary border border-neutral/10 hover:border-data/50 transition-colors font-body text-sm text-neutral/70 hover:text-white"
          >
            Expertenansicht
          </button>
        )}
        {/* PDF Export */}
        {result && token && (
          <button
            onClick={() => downloadReport(result.job_id, token).catch((e: Error) => setReportFehler(e.message))}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-bg-secondary
              border border-neutral/10 hover:border-data/50 transition-colors
              font-body text-sm text-neutral/70 hover:text-white"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            PDF-Report
          </button>
        )}
        {reportFehler && <span className="font-body text-xs text-accent">{reportFehler}</span>}
        </div>
      </header>

      {/* Dashboard grid */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {result && (
          <div role="tablist" aria-label="Auswertung" className="mb-6 inline-flex rounded-xl bg-bg-secondary p-1">
            {([['ergonomie', 'Ergonomie'], ['steckbrief', 'Steckbrief']] as const).map(([id, label]) => (
              <button key={id} role="tab" aria-selected={tab === id}
                onClick={() => setParams(id === 'steckbrief' ? { tab: id } : {}, { replace: true })}
                className={`px-5 py-2 rounded-lg font-body text-sm transition-colors ${
                  tab === id ? 'bg-bg-primary text-white' : 'text-neutral/55 hover:text-white'}`}>
                {label}
              </button>
            ))}
          </div>
        )}

        {result && tab === 'steckbrief' && <SteckbriefTab jobId={result.job_id} />}

        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <SkeletonCard className="h-72" />
            <SkeletonCard className="h-72" />
            <SkeletonCard className="h-52" />
            <SkeletonCard className="h-52" />
            <SkeletonCard className="h-40 md:col-span-2" />
          </div>
        )}

        {result && tab === 'ergonomie' && (
          <>
            {/* Summary strip */}
            <div className="mb-6 flex flex-wrap gap-4 items-center">
              <div className="flex flex-col">
                <span className="font-mono text-3xl font-bold"
                  style={{ color: rebaStufe(result.reba_score).farbe }}>
                  {rebaText(result.reba_score)}
                </span>
                <span className="font-body text-xs text-neutral/40">Haltungsindex auf REBA-Basis (1 bis 10) · {rebaStufe(result.reba_score).stufe} · Pilotphase</span>
              </div>
              <div className="h-10 w-px bg-bg-secondary" />
              <div className="flex flex-col">
                <span className="font-mono text-base font-semibold text-neutral/70">
                  {result.shift_duration_min} min
                </span>
                <span className="font-body text-xs text-neutral/40">Analysierte Schicht</span>
              </div>
              <div className="h-10 w-px bg-bg-secondary" />
              <div className="flex flex-col">
                <span className="font-mono text-base font-semibold text-neutral/70">
                  {result.action_items.filter(i => i.priority === 'CRITICAL').length} kritisch
                </span>
                <span className="font-body text-xs text-neutral/40">Handlungsfelder</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

              {/* 1: posture index gauge */}
              <Card title="Haltungsindex auf REBA-Basis" tag="Pilotphase">
                <REBAGauge score={result.reba_score} />
              </Card>

              {/* 2: body heatmap */}
              <Card title="Körperregionen-Heatmap" tag="Pilotphase">
                <BodyHeatmap regions={result.body_regions} />
              </Card>

              {/* 3: movement chart */}
              <Card title="Bewegungsklassifikation">
                <MovementChart
                  movements={result.movements}
                  shiftMin={result.shift_duration_min}
                />
              </Card>

              {/* 4: timeline */}
              <Card title="Bewegungszeitverlauf">
                <TimelineChart timeline_frames={result.timeline_frames ?? []} />
              </Card>

              {/* 5: action items (full width) */}
              <Card title="Handlungsfelder" className="md:col-span-2">
                <ActionItems items={result.action_items} />
              </Card>

            </div>

            {/* 6: critical frames */}
            {result.critical_frames && result.critical_frames.length > 0 && (
              <div className="mt-5">
                <Card title="Kritische Bewegungsmomente" className="">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {result.critical_frames.map((cf) => {
                      const mm = String(Math.floor(cf.second / 60)).padStart(2, '0')
                      const ss = String(Math.round(cf.second % 60)).padStart(2, '0')
                      const mvLabel = cf.movement === 'overhead' ? 'Überkopf'
                        : cf.movement === 'bending' ? 'Bücken' : 'Schulter'
                      return (
                        <div key={cf.rank}
                          className="flex flex-col rounded-xl overflow-hidden border border-bg-primary bg-bg-primary">
                          {cf.bild_url && (
                            <img
                              src={frameUrl(cf.bild_url)}
                              alt={`Kritischer Moment ${cf.rank}, Köpfe geschwärzt`}
                              className="w-full aspect-video object-cover"
                            />
                          )}
                          <div className="p-3 flex flex-col gap-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-xs text-neutral/50">{mm}:{ss}</span>
                              <span className="font-mono text-sm font-bold" style={{ color: '#e63946' }}>
                                Index {rebaText(cf.reba)}
                              </span>
                            </div>
                            <span className="font-body text-xs text-neutral/40">{mvLabel}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </Card>
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-bg-secondary px-6 py-4 text-center">
        <p className="font-body text-xs text-neutral/20">
          Erstellt durch Motavi · Analyse auf Servern in Deutschland (Frankfurt)
        </p>
      </footer>
    </div>
  )
}
