import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface Point {
  minute: number
  reba: number
}

interface Props {
  timeline: Point[]
}

const TOOLTIP_STYLE: React.CSSProperties = {
  background: '#1a2744',
  border: '1px solid #00b4d8',
  borderRadius: '6px',
  padding: '6px 12px',
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  color: '#f4f4f6',
}

export default function TimelineChart({ timeline }: Props) {
  if (!timeline.length) {
    return (
      <div className="w-full h-48 flex items-center justify-center text-neutral/30 font-body text-sm">
        Keine Zeitreihendaten verfügbar.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={timeline} margin={{ top: 8, right: 8, bottom: 4, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a2744" vertical={false} />

        <XAxis
          dataKey="minute"
          stroke="#f4f4f630"
          tick={{ fill: '#f4f4f660', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
          tickLine={false}
          label={{ value: 'min', position: 'insideBottomRight', offset: -4,
                   fill: '#f4f4f640', fontSize: 9 }}
        />
        <YAxis
          domain={[0, 10]}
          stroke="#f4f4f630"
          tick={{ fill: '#f4f4f660', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
          tickLine={false}
          tickCount={6}
        />

        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          labelFormatter={(v) => `Minute ${v}`}
          formatter={(v: number) => [v.toFixed(2), 'REBA']}
          cursor={{ stroke: '#00b4d820', strokeWidth: 1 }}
        />

        {/* Risk threshold */}
        <ReferenceLine y={7} stroke="#e6394660" strokeDasharray="4 3" strokeWidth={1} />
        <ReferenceLine y={4} stroke="#22c55e40" strokeDasharray="4 3" strokeWidth={1} />

        <Line
          type="monotone"
          dataKey="reba"
          stroke="#00b4d8"
          strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 3, fill: '#00b4d8', stroke: '#0a0f1e', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
