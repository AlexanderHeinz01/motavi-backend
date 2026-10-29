/**
 * SVG semicircle gauge for REBA score (1–10).
 * Background shows three colour zones (green / yellow / red).
 * Active arc fills from left (score 1) clockwise to current score.
 */

const CX = 150
const CY = 145
const R  = 120

function toXY(angleDeg: number): [number, number] {
  const rad = (angleDeg * Math.PI) / 180
  return [
    CX + R * Math.cos(rad),
    CY - R * Math.sin(rad),   // SVG y is inverted
  ]
}

/** Arc path from angle a1 to a2 (both in degrees, clockwise in display). */
function arc(a1: number, a2: number): string {
  const [x1, y1] = toXY(a1)
  const [x2, y2] = toXY(a2)
  const span  = Math.abs(a1 - a2)
  const large = span > 180 ? 1 : 0
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${R} ${R} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`
}

/** Map score (1–10) to angle: score 1 → 180°, score 10 → 0°. */
function scoreAngle(score: number): number {
  return 180 - ((Math.max(1, Math.min(10, score)) - 1) / 9) * 180
}

function scoreColor(score: number): string {
  if (score <= 4) return '#22c55e'
  if (score <= 6) return '#eab308'
  return '#e63946'
}

const _LEVEL: Record<string, string> = {
  LOW:       'Niedriges Risiko',
  MEDIUM:    'Mittleres Risiko',
  HIGH:      'Hohes Risiko',
  VERY_HIGH: 'Sehr hohes Risiko',
}

interface Props {
  score: number
  level?: string
}

export default function REBAGauge({ score, level }: Props) {
  const col     = scoreColor(score)
  const fillAng = scoreAngle(score)

  // Zone boundary angles
  const ang4  = scoreAngle(4)   // 120°
  const ang6  = scoreAngle(6)   // 80°

  // Full background track
  const trackPath = arc(180, 0)

  return (
    <svg viewBox="0 0 300 185" xmlns="http://www.w3.org/2000/svg" className="w-full max-w-xs mx-auto">
      {/* Shadow / track */}
      <path d={trackPath} stroke="#0f1830" strokeWidth={26} fill="none" strokeLinecap="round" />

      {/* Zone: green (1–4) */}
      <path d={arc(180, ang4)} stroke="#22c55e" strokeWidth={20} fill="none"
        strokeOpacity={0.18} strokeLinecap="butt" />
      {/* Zone: yellow (4–6) */}
      <path d={arc(ang4, ang6)} stroke="#eab308" strokeWidth={20} fill="none"
        strokeOpacity={0.18} strokeLinecap="butt" />
      {/* Zone: red (6–10) */}
      <path d={arc(ang6, 0)} stroke="#e63946" strokeWidth={20} fill="none"
        strokeOpacity={0.18} strokeLinecap="butt" />

      {/* Active fill */}
      {score > 1.05 && (
        <path
          d={arc(180, fillAng)}
          stroke={col}
          strokeWidth={22}
          fill="none"
          strokeLinecap="round"
          style={{ transition: 'stroke 0.4s ease' }}
        />
      )}

      {/* Tick at position 1 */}
      <circle cx={toXY(180)[0]} cy={toXY(180)[1]} r={4} fill={col} opacity={0.5} />
      {/* Tick at position 10 */}
      <circle cx={toXY(0)[0]}   cy={toXY(0)[1]}   r={4} fill={col} opacity={0.5} />

      {/* Score label */}
      <text
        x={CX} y={CY + 8}
        textAnchor="middle"
        fontFamily="'JetBrains Mono', monospace"
        fontWeight="700"
        fontSize={54}
        fill={col}
      >
        {score.toFixed(1)}
      </text>

      {/* Level label */}
      <text
        x={CX} y={CY + 35}
        textAnchor="middle"
        fontFamily="Inter, sans-serif"
        fontSize={12}
        fill="#f4f4f6"
        opacity={0.7}
      >
        {level ? (_LEVEL[level] ?? level) : ''}
      </text>

      {/* Axis labels */}
      <text x={22}  y={CY + 20} textAnchor="middle" fontFamily="monospace" fontSize={10} fill="#f4f4f660">1</text>
      <text x={278} y={CY + 20} textAnchor="middle" fontFamily="monospace" fontSize={10} fill="#f4f4f660">10</text>
    </svg>
  )
}
