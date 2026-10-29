interface TimelineFrame {
  second: number
  movement: string
}

interface Props {
  timeline_frames: TimelineFrame[]
}

const COLORS: Record<string, string> = {
  neutral:  '#6b7a99',
  bending:  '#e63946',
  overhead: '#00b4d8',
}

const LABELS: Record<string, string> = {
  neutral:  'Schulter',
  bending:  'Bücken',
  overhead: 'Überkopf',
}

export default function TimelineChart({ timeline_frames }: Props) {
  if (!timeline_frames.length) {
    return (
      <div className="w-full h-20 flex items-center justify-center text-neutral/30 font-body text-sm">
        Keine Zeitreihendaten verfügbar.
      </div>
    )
  }

  const firstSec = timeline_frames[0].second
  const lastSec  = timeline_frames[timeline_frames.length - 1].second
  // Estimate one frame's duration as the interval between first two frames (or 1s)
  const frameStep = timeline_frames.length > 1
    ? timeline_frames[1].second - timeline_frames[0].second
    : 1
  const totalDur = lastSec - firstSec + frameStep

  // Build rect segments in a 1000-unit wide SVG
  const segments = timeline_frames.map((f) => ({
    x:     ((f.second - firstSec) / totalDur) * 1000,
    w:     Math.max(1, (frameStep / totalDur) * 1000),
    color: COLORS[f.movement] ?? '#6b7a99',
  }))

  // Tick positions: one per minute, or every 30 s for short videos
  const tickStep = totalDur > 300 ? 60 : totalDur > 90 ? 30 : 15
  const ticks: number[] = []
  for (let t = 0; t <= totalDur; t += tickStep) ticks.push(t)

  return (
    <div className="flex flex-col gap-2">
      {/* Color bar */}
      <svg
        width="100%"
        height="32"
        viewBox="0 0 1000 32"
        preserveAspectRatio="none"
        className="rounded-lg overflow-hidden"
        style={{ display: 'block' }}
      >
        {segments.map((s, i) => (
          <rect key={i} x={s.x} y={0} width={s.w} height={32} fill={s.color} />
        ))}
      </svg>

      {/* X-axis ticks */}
      <div className="relative w-full h-4">
        {ticks.map((t) => {
          const pct = (t / totalDur) * 100
          const abs = firstSec + t
          const mm  = String(Math.floor(abs / 60)).padStart(2, '0')
          const ss  = String(Math.round(abs % 60)).padStart(2, '0')
          return (
            <span
              key={t}
              className="absolute font-mono text-[10px] text-neutral/40 -translate-x-1/2"
              style={{ left: `${pct}%` }}
            >
              {mm}:{ss}
            </span>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-1">
        {Object.entries(LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: COLORS[key] }} />
            <span className="font-body text-xs text-neutral/50">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
