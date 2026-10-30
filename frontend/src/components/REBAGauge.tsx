/**
 * SVG semicircle gauge for the REBA score (1 to 15).
 * Background zones and label follow the REBA action levels (lib/rebaStufe.ts),
 * the same as on the website and in the PDF report.
 * Active arc fills from left (score 1) clockwise to current score.
 */
import { REBA_MAX, REBA_STUFEN, rebaStufe, rebaText } from '../lib/rebaStufe'

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

/** Map score (1 to 15, the REBA scale) to angle: score 1 → 180°, score 15 → 0°. */
function scoreAngle(score: number): number {
  return 180 - ((Math.max(1, Math.min(REBA_MAX, score)) - 1) / (REBA_MAX - 1)) * 180
}

interface Props {
  score: number
}

export default function REBAGauge({ score }: Props) {
  const { stufe, massnahme, farbe: col } = rebaStufe(score)
  const fillAng = scoreAngle(score)

  // Full background track
  const trackPath = arc(180, 0)

  return (
    <svg viewBox="0 0 300 185" xmlns="http://www.w3.org/2000/svg" className="w-full max-w-xs mx-auto"
      role="img" aria-label={`REBA-Score ${rebaText(score)} von ${REBA_MAX}: ${stufe}, ${massnahme}`}>
      {/* Shadow / track */}
      <path d={trackPath} stroke="#0f1830" strokeWidth={26} fill="none" strokeLinecap="round" />

      {/* Zones of the action levels */}
      {REBA_STUFEN.map((s, i) => {
        const von = i === 0 ? 1 : REBA_STUFEN[i - 1].bis
        const bis = Math.min(s.bis, REBA_MAX)
        return (
          <path key={s.stufe} d={arc(scoreAngle(von), scoreAngle(bis))} stroke={s.farbe} strokeWidth={20} fill="none"
            strokeOpacity={0.18} strokeLinecap="butt" />
        )
      })}

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
        {rebaText(score)}
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
        {stufe}: {massnahme}
      </text>

      {/* Axis labels */}
      <text x={22}  y={CY + 20} textAnchor="middle" fontFamily="monospace" fontSize={10} fill="#f4f4f660">1</text>
      <text x={278} y={CY + 20} textAnchor="middle" fontFamily="monospace" fontSize={10} fill="#f4f4f660">{REBA_MAX}</text>
    </svg>
  )
}
