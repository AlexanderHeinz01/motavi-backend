import { useRef, useState, type DragEvent } from 'react'

interface Props {
  onFile: (file: File) => void
  disabled?: boolean
  /** largest file; same as UPLOAD_MAX_BYTES in the backend */
  maxBytes?: number
}

const ACCEPT = ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo']
const MAX_BYTES = 1024 * 1024 * 1024

export default function UploadZone({ onFile, disabled, maxBytes = MAX_BYTES }: Props) {
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = (file: File) => {
    setError(null)
    if (!ACCEPT.includes(file.type) && !file.name.match(/\.(mp4|webm|mov|avi)$/i)) {
      setError('Nicht unterstütztes Format. Bitte MP4, WebM, MOV oder AVI verwenden.')
      return
    }
    if (file.size > maxBytes) {
      setError(`Datei zu groß (höchstens ${Math.round(maxBytes / 1024 / 1024)} MB).`)
      return
    }
    onFile(file)
  }

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (disabled) return
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="w-full">
      <div
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={[
          'relative flex flex-col items-center justify-center gap-5 rounded-2xl',
          'border-2 border-dashed p-16 transition-all duration-200',
          disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
          dragging
            ? 'border-data bg-data/10 scale-[1.01]'
            : 'border-bg-secondary hover:border-data/40 hover:bg-bg-secondary/30',
        ].join(' ')}
      >
        {/* Upload icon */}
        <svg
          className={`w-14 h-14 transition-colors ${dragging ? 'text-data' : 'text-neutral/30'}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>

        <div className="text-center">
          <p className="font-headline text-xl text-white mb-1">
            {dragging ? 'Datei hier ablegen' : 'Video hier ablegen oder klicken'}
          </p>
          <p className="font-body text-sm text-neutral/50">
            MP4 · WebM · MOV · AVI, höchstens {Math.round(maxBytes / 1024 / 1024)} MB
          </p>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          disabled={disabled}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
            e.target.value = ''
          }}
        />
      </div>

      {error && (
        <p className="mt-3 text-center text-sm text-accent font-body">{error}</p>
      )}
    </div>
  )
}
