import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SCHICHT, uploadVideo, type Arbeitsplatz } from '../api/motavi'
import { useAuth } from '../auth/AuthContext'
import UploadLinkErstellen from '../components/UploadLinkErstellen'
import UploadZone from '../components/UploadZone'

type Phase = 'idle' | 'selected' | 'uploading' | 'error'

const inputCls =
  'w-full px-3 py-2 rounded-lg bg-bg-primary border border-bg-secondary ' +
  'focus:outline-none focus:border-data/50 font-body text-sm text-white ' +
  'placeholder:text-neutral/25 transition-colors disabled:opacity-50'

export default function UploadPage() {
  const navigate = useNavigate()
  const { user, token, logout } = useAuth()
  const [file,     setFile]     = useState<File | null>(null)
  const [phase,    setPhase]    = useState<Phase>('idle')
  const [progress, setProgress] = useState(0)
  const [error,    setError]    = useState<string | null>(null)
  const [meta,     setMeta]     = useState<Arbeitsplatz>({ schichtdauer_min: SCHICHT.standard })

  const setField = <K extends keyof Arbeitsplatz>(k: K, v: Arbeitsplatz[K]) =>
    setMeta(m => ({ ...m, [k]: v }))

  const handleFile = (f: File) => {
    setFile(f)
    setPhase('selected')
    setError(null)
  }

  const handleUpload = async () => {
    if (!file || !token) return
    setPhase('uploading')
    setError(null)
    setProgress(0)
    try {
      const { job_id } = await uploadVideo(file, meta, token, setProgress)
      navigate(`/app/analyzing/${job_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload fehlgeschlagen.')
      setPhase('error')
    }
  }

  const formatSize = (bytes: number) =>
    bytes >= 1_048_576
      ? `${(bytes / 1_048_576).toFixed(1)} MB`
      : `${(bytes / 1024).toFixed(0)} KB`

  const uploading = phase === 'uploading'

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col items-center justify-center px-6 py-10">
      {/* Account / logout */}
      <div className="absolute top-4 right-4 flex items-center gap-3">
        {user && (
          <span className="font-body text-xs text-neutral/40 hidden sm:inline">{user.email}</span>
        )}
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="font-body text-xs text-neutral/50 hover:text-white transition-colors
            px-3 py-1.5 rounded-lg border border-bg-secondary"
        >
          Abmelden
        </button>
      </div>

      <div className="w-full max-w-xl flex flex-col gap-6">

        {/* Header */}
        <div className="text-center">
          <h1 className="font-headline text-4xl font-bold text-white tracking-tight mb-2">
            MOTAVI
          </h1>
          <p className="font-body text-base text-neutral/50">
            Internes Werkzeug: Videos analysieren, Steckbriefe prüfen
          </p>
        </div>

        {/* Divider */}
        <div className="h-px bg-bg-secondary" />

        {/* Metadata form */}
        <div className="flex flex-col gap-3">
          <p className="font-body text-xs text-neutral/40 uppercase tracking-widest">
            Analyseparameter
          </p>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1.5">
              <span className="font-body text-xs text-neutral/50">Unternehmensname</span>
              <input
                type="text"
                value={meta.company_name ?? ''}
                onChange={e => setField('company_name', e.target.value || undefined)}
                placeholder="optional"
                disabled={uploading}
                className={inputCls}
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="font-body text-xs text-neutral/50">Bereich / Abteilung</span>
              <input
                type="text"
                value={meta.department ?? ''}
                onChange={e => setField('department', e.target.value || undefined)}
                placeholder="optional"
                disabled={uploading}
                className={inputCls}
              />
            </label>
            <label className="col-span-2 flex flex-col gap-1.5">
              <span className="font-body text-xs text-neutral/50">Aufgabenbeschreibung</span>
              <textarea
                value={meta.task_description ?? ''}
                onChange={e => setField('task_description', e.target.value || undefined)}
                placeholder='optional, z. B. „Montage Karosserie, stehend“'
                rows={2}
                disabled={uploading}
                className={`${inputCls} resize-none`}
              />
            </label>
            <label className="col-span-2 flex flex-col gap-1.5">
              <span className="font-body text-xs text-neutral/50">
                Netto-Arbeitszeit je Schicht in Minuten, ohne Pausen<span className="text-accent ml-0.5">*</span>
              </span>
              <input
                type="number"
                value={meta.schichtdauer_min}
                onChange={e => setField('schichtdauer_min', Math.min(SCHICHT.max, Math.max(SCHICHT.min, Number(e.target.value) || SCHICHT.standard)))}
                min={SCHICHT.min}
                max={SCHICHT.max}
                disabled={uploading}
                className={inputCls}
              />
            </label>
          </div>
        </div>

        {/* Divider */}
        <div className="h-px bg-bg-secondary" />

        {/* Upload zone */}
        <UploadZone onFile={handleFile} disabled={uploading} />

        {/* Selected file preview */}
        {file && phase !== 'idle' && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-bg-secondary border border-bg-secondary">
            <svg className="w-8 h-8 text-data flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <div className="flex-1 min-w-0">
              <p className="font-body text-sm text-white truncate">{file.name}</p>
              <p className="font-mono text-xs text-neutral/40">{formatSize(file.size)}</p>
            </div>
            {!uploading && (
              <button
                onClick={() => { setFile(null); setPhase('idle') }}
                className="text-neutral/30 hover:text-neutral/70 transition-colors"
                aria-label="Datei entfernen"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        )}

        {/* Progress bar */}
        {uploading && (
          <div className="flex flex-col gap-2">
            <div className="w-full h-1.5 rounded-full bg-bg-secondary overflow-hidden">
              <div
                className="h-full bg-data rounded-full transition-all duration-200"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs text-neutral/40">Upload läuft…</span>
              <span className="font-mono text-xs text-data">{progress} %</span>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <p className="text-center font-body text-sm text-accent">{error}</p>
        )}

        {/* CTA button */}
        {(phase === 'selected' || phase === 'error') && (
          <button
            onClick={handleUpload}
            className="w-full py-3.5 rounded-xl font-headline font-semibold text-base
              bg-accent hover:bg-accent/90 text-white transition-colors duration-150"
          >
            Analyse starten
          </button>
        )}

        {/* Upload links for customers: team only */}
        {user && ['berater', 'admin'].includes(user.role) && token && <UploadLinkErstellen token={token} />}

        {/* Footer note */}
        <p className="text-center font-body text-xs text-neutral/25">
          Analyse auf Servern in Deutschland (Frankfurt) · Originalvideo wird nach der Auswertung gelöscht
        </p>
      </div>
    </div>
  )
}
