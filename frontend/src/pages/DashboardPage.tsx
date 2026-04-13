import { useNavigate, useParams } from 'react-router-dom'
import { getFrameUrl, getReportPdfUrl } from '../api/motavi'
import ActionItems   from '../components/ActionItems'
import BodyHeatmap   from '../components/BodyHeatmap'
import MovementChart from '../components/MovementChart'
import REBAGauge     from '../components/REBAGauge'
import TimelineChart from '../components/TimelineChart'
import { useAnalysis } from '../hooks/useAnalysis'

function Card({
  title, children, className = '',
}: {
  title: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-2xl bg-bg-secondary p-5 flex flex-col gap-4 ${className}`}>
      <h3 className="font-headline text-xs font-semibold uppercase tracking-widest text-neutral/40">
        {title}
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

  const loading = status === 'processing'
  const failed  = status === 'error'

  if (failed) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center px-6">
        <div className="max-w-md w-full p-8 rounded-2xl bg-bg-secondary text-center">
          <p className="font-headline text-xl text-accent mb-2">Analyse fehlgeschlagen</p>
          <p className="font-body text-sm text-neutral/60 mb-6">{error}</p>
          <button onClick={() => navigate('/')}
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
            onClick={() => navigate('/')}
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

        {/* PDF Export */}
        {result && (
          <a
            href={getReportPdfUrl(result.job_id)}
            download
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-bg-secondary
              border border-neutral/10 hover:border-data/50 transition-colors
              font-body text-sm text-neutral/70 hover:text-white"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            PDF-Report
          </a>
        )}
      </header>

      {/* Dashboard grid */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <SkeletonCard className="h-72" />
            <SkeletonCard className="h-72" />
            <SkeletonCard className="h-52" />
            <SkeletonCard className="h-52" />
            <SkeletonCard className="h-40 md:col-span-2" />
          </div>
        )}

        {result && (
          <>
            {/* Summary strip */}
            <div className="mb-6 flex flex-wrap gap-4 items-center">
              <div className="flex flex-col">
                <span className="font-mono text-3xl font-bold"
                  style={{ color: result.reba_score <= 4 ? '#22c55e' : result.reba_score <= 6 ? '#eab308' : '#e63946' }}>
                  {result.reba_score.toFixed(1)}
                </span>
                <span className="font-body text-xs text-neutral/40">REBA-Score</span>
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

              {/* 1 — REBA Gauge */}
              <Card title="REBA-Score">
                <REBAGauge score={result.reba_score} level={result.reba_level} />
              </Card>

              {/* 2 — Body Heatmap */}
              <Card title="Körperregionen-Heatmap">
                <BodyHeatmap regions={result.body_regions} />
              </Card>

              {/* 3 — Movement chart */}
              <Card title="Bewegungsklassifikation">
                <MovementChart
                  movements={result.movements}
                  shiftMin={result.shift_duration_min}
                />
              </Card>

              {/* 4 — Timeline */}
              <Card title="Bewegungszeitverlauf">
                <TimelineChart timeline_frames={result.timeline_frames ?? []} />
              </Card>

              {/* 5 — Action items (full width) */}
              <Card title="Handlungsfelder" className="md:col-span-2">
                <ActionItems items={result.action_items} />
              </Card>

            </div>

            {/* 6 — Critical frames */}
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
                          <img
                            src={getFrameUrl(result.job_id, `critical_${cf.rank}.jpg`)}
                            alt={`Kritischer Frame ${cf.rank}`}
                            className="w-full aspect-video object-cover"
                          />
                          <div className="p-3 flex flex-col gap-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-xs text-neutral/50">{mm}:{ss}</span>
                              <span className="font-mono text-sm font-bold" style={{ color: '#e63946' }}>
                                REBA {cf.reba.toFixed(1)}
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
          Erstellt durch Motavi · DSGVO-konform · EU-Server (europe-west3)
        </p>
      </footer>
    </div>
  )
}
