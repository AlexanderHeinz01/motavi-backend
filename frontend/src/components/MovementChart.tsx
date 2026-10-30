/**
 * Bewegungsklassifikation: stacked horizontal bar + table.
 * bending / overhead / neutral — shows % and minutes/shift.
 */

interface Movement {
  pct: number
  minutes: number
}

interface Props {
  movements: Record<string, Movement>
  shiftMin?: number
}

const SEGMENTS = [
  { key: 'bending',  label: 'Bücken',          color: '#e63946' },
  { key: 'overhead', label: 'Überkopf',         color: '#eab308' },
  { key: 'neutral',  label: 'Schulter neutral', color: '#00b4d8' },
] as const

export default function MovementChart({ movements, shiftMin = 480 }: Props) {
  return (
    <div className="w-full flex flex-col gap-5">
      {/* Stacked bar */}
      <div className="w-full h-7 flex rounded-lg overflow-hidden gap-px">
        {SEGMENTS.map(({ key, label, color }) => {
          const pct = movements[key]?.pct ?? 0
          return pct > 0.5 ? (
            <div
              key={key}
              style={{ width: `${pct}%`, backgroundColor: color }}
              title={`${label}: ${pct.toFixed(1).replace('.', ',')}\u00a0%`}
              className="flex items-center justify-center transition-all duration-700"
            >
              {pct > 8 && (
                <span className="text-[10px] font-mono font-bold text-white/90 select-none">
                  {pct.toFixed(0)} %
                </span>
              )}
            </div>
          ) : null
        })}
      </div>

      {/* Legend + data table */}
      <div className="flex flex-col gap-2">
        {SEGMENTS.map(({ key, label, color }) => {
          const mv      = movements[key]
          const pct     = mv?.pct ?? 0
          const mins    = mv?.minutes ?? 0
          const extrap  = Math.round(pct / 100 * 480)
          return (
            <div key={key} className="flex items-center gap-3">
              {/* Color dot */}
              <span
                className="flex-shrink-0 w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              {/* Label */}
              <span className="font-body text-sm text-neutral/80 w-28 flex-shrink-0">
                {label}
              </span>
              {/* Pct */}
              <span
                className="font-mono text-sm font-semibold w-14 text-right"
                style={{ color }}
              >
                {pct.toFixed(1).replace('.', ',')}&nbsp;%
              </span>
              {/* Minutes */}
              <span className="font-mono text-xs text-neutral/50 ml-auto">
                {mins.toFixed(0)} min
              </span>
              {/* Extrapolated */}
              <span className="font-mono text-xs text-neutral/30 w-16 text-right">
                ≈ {extrap} min/8h
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
