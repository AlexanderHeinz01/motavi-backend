/**
 * SVG body-region heatmap.
 * Each highlighted region is coloured by its region score based on REBA (raw → normalised).
 * Regions: lumbar, shoulder_l/r, neck, forearm, knee_l/r.
 */

const REGION_MAX: Record<string, number> = {
  lumbar:     8.0,
  shoulder_l: 7.2,
  shoulder_r: 8.0,
  neck:       6.5,
  knee_l:     6.175,
  knee_r:     6.5,
  forearm:    4.5,
}

function regionColor(key: string, raw: number): string {
  const norm = raw / (REGION_MAX[key] ?? 8.0)
  if (norm < 0.38) return '#22c55e'
  if (norm < 0.63) return '#eab308'
  return '#e63946'
}

function regionOpacity(key: string, raw: number): number {
  const norm = raw / (REGION_MAX[key] ?? 8.0)
  return 0.25 + norm * 0.65
}

function Region({
  id, regions, children,
}: {
  id: string
  regions: Record<string, number>
  children: React.ReactNode
}) {
  const raw   = regions[id] ?? 1
  const color = regionColor(id, raw)
  const alpha = regionOpacity(id, raw)
  return (
    <g fill={color} fillOpacity={alpha} stroke={color} strokeOpacity={alpha * 0.6} strokeWidth={0.5}>
      {children}
    </g>
  )
}

const NEUTRAL = '#1a2744'

interface Props {
  regions: Record<string, number>
}

export default function BodyHeatmap({ regions }: Props) {
  return (
    <svg viewBox="0 0 200 390" xmlns="http://www.w3.org/2000/svg"
      className="w-full max-h-80 mx-auto">

      {/* ── Head ── */}
      <ellipse cx="100" cy="33" rx="22" ry="26" fill={NEUTRAL} stroke="#2a3a5c" strokeWidth="1" />

      {/* ── Neck (highlighted) ── */}
      <Region id="neck" regions={regions}>
        <rect x="89" y="59" width="22" height="24" rx="4" />
      </Region>

      {/* ── Torso (non-highlighted fill) ── */}
      <rect x="66" y="83" width="68" height="115" rx="4" fill={NEUTRAL} />

      {/* ── Shoulder bar left (highlighted) ── */}
      <Region id="shoulder_l" regions={regions}>
        <rect x="28" y="83" width="38" height="26" rx="4" />
      </Region>
      {/* ── Shoulder bar right (highlighted) ── */}
      <Region id="shoulder_r" regions={regions}>
        <rect x="134" y="83" width="38" height="26" rx="4" />
      </Region>

      {/* ── Upper arms (neutral) ── */}
      <rect x="28"  y="109" width="28" height="68" rx="4" fill={NEUTRAL} />
      <rect x="144" y="109" width="28" height="68" rx="4" fill={NEUTRAL} />

      {/* ── Forearms (highlighted) ── */}
      <Region id="forearm" regions={regions}>
        <rect x="23"  y="177" width="26" height="64" rx="4" />
        <rect x="151" y="177" width="26" height="64" rx="4" />
      </Region>

      {/* ── Lumbar (highlighted, lower torso overlay) ── */}
      <Region id="lumbar" regions={regions}>
        <rect x="66" y="162" width="68" height="36" rx="4" />
      </Region>

      {/* ── Hips (neutral) ── */}
      <rect x="58" y="198" width="84" height="26" rx="4" fill={NEUTRAL} />

      {/* ── Upper legs (neutral) ── */}
      <rect x="60"  y="224" width="34" height="74" rx="4" fill={NEUTRAL} />
      <rect x="106" y="224" width="34" height="74" rx="4" fill={NEUTRAL} />

      {/* ── Knees (highlighted) ── */}
      <Region id="knee_l" regions={regions}>
        <rect x="60" y="298" width="34" height="22" rx="3" />
      </Region>
      <Region id="knee_r" regions={regions}>
        <rect x="106" y="298" width="34" height="22" rx="3" />
      </Region>

      {/* ── Lower legs (neutral) ── */}
      <rect x="63"  y="320" width="28" height="52" rx="4" fill={NEUTRAL} />
      <rect x="109" y="320" width="28" height="52" rx="4" fill={NEUTRAL} />

      {/* ── Region labels ── */}
      {[
        { id: 'neck',       x: 100, y: 74,  anchor: 'middle',  label: 'Nacken' },
        { id: 'shoulder_l', x: 20,  y: 82,  anchor: 'end',     label: 'Sch. L' },
        { id: 'shoulder_r', x: 180, y: 82,  anchor: 'start',   label: 'Sch. R' },
        { id: 'lumbar',     x: 100, y: 156, anchor: 'middle',  label: 'Lende' },
        { id: 'forearm',    x: 8,   y: 210, anchor: 'start',   label: 'Unterarm' },
        { id: 'knee_l',     x: 57,  y: 295, anchor: 'end',     label: 'Knie L' },
        { id: 'knee_r',     x: 143, y: 295, anchor: 'start',   label: 'Knie R' },
      ].map(({ id, x, y, anchor, label }) => {
        const raw  = regions[id] ?? 1
        const col  = regionColor(id, raw)
        return (
          <text key={id} x={x} y={y} textAnchor={anchor as 'middle' | 'start' | 'end'}
            fontFamily="Inter, sans-serif" fontSize={8.5} fill={col} fontWeight="600">
            {label}
          </text>
        )
      })}
    </svg>
  )
}
