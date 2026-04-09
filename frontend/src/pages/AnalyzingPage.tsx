import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAnalysis } from '../hooks/useAnalysis'

const STEPS = [
  'Anonymisierung läuft…',
  'Pose-Landmarks werden berechnet…',
  'REBA-Subscores werden ermittelt…',
  'Bewegungsklassifikation läuft…',
  'Bericht wird zusammengestellt…',
]

function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div className={`rounded-xl bg-bg-secondary animate-pulse ${className}`} />
  )
}

export default function AnalyzingPage() {
  const { jobId }  = useParams<{ jobId: string }>()
  const navigate   = useNavigate()
  const { status, error } = useAnalysis(jobId)

  useEffect(() => {
    if (status === 'done' && jobId) {
      navigate(`/dashboard/${jobId}`, { replace: true })
    }
  }, [status, jobId, navigate])

  const stepIdx = Math.floor((Date.now() / 4000)) % STEPS.length

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-2xl flex flex-col gap-10">

        {/* Header */}
        <div className="text-center">
          <h1 className="font-headline text-3xl font-bold text-white mb-2">MOTAVI</h1>
          <p className="font-body text-sm text-neutral/40 font-mono">
            Job: {jobId?.slice(0, 8)}…
          </p>
        </div>

        {/* Status */}
        {status === 'error' ? (
          <div className="p-6 rounded-xl border border-accent/30 bg-accent/5 text-center">
            <p className="font-headline text-lg text-accent mb-1">Analyse fehlgeschlagen</p>
            <p className="font-body text-sm text-neutral/60">{error}</p>
            <button
              onClick={() => navigate('/')}
              className="mt-4 px-5 py-2 rounded-lg bg-bg-secondary text-neutral/80
                hover:text-white transition-colors font-body text-sm"
            >
              ← Neues Video hochladen
            </button>
          </div>
        ) : (
          <>
            {/* Animated scanner line */}
            <div className="relative w-full h-1 rounded-full bg-bg-secondary overflow-visible">
              <div
                className="absolute top-0 h-full w-1/3 rounded-full bg-gradient-to-r from-transparent via-data to-transparent"
                style={{ animation: 'scan 2.2s ease-in-out infinite' }}
              />
            </div>

            {/* Current step */}
            <p className="text-center font-mono text-sm text-data animate-pulse">
              {STEPS[stepIdx]}
            </p>

            {/* Dashboard skeleton */}
            <div className="grid grid-cols-2 gap-4">
              <SkeletonBlock className="col-span-1 h-52" />
              <SkeletonBlock className="col-span-1 h-52" />
              <SkeletonBlock className="col-span-2 h-36" />
              <SkeletonBlock className="col-span-2 h-28" />
            </div>
          </>
        )}

        {/* Footer */}
        <p className="text-center font-body text-xs text-neutral/20">
          Die Analyse läuft serverseitig — diese Seite kann offen bleiben.
        </p>
      </div>

      {/* Scan animation */}
      <style>{`
        @keyframes scan {
          0%   { left: -33%; }
          100% { left: 100%; }
        }
      `}</style>
    </div>
  )
}
