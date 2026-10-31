import { type ActionItem } from '../api/motavi'

interface Props {
  items: ActionItem[]
}

const PRIORITY_CONFIG = {
  CRITICAL: {
    label:       'KRITISCH',
    border:      'border-accent',
    badge:       'bg-accent',
    text:        'text-accent',
    bg:          'bg-accent/5',
  },
  MEDIUM: {
    label:       'MITTEL',
    border:      'border-yellow-500',
    badge:       'bg-yellow-600',
    text:        'text-yellow-400',
    bg:          'bg-yellow-500/5',
  },
} as const

export default function ActionItems({ items }: Props) {
  if (!items.length) {
    return (
      <div className="p-6 rounded-xl bg-bg-secondary/50 text-center">
        <p className="font-body text-sm text-neutral/50">
          Keine Handlungsfelder erkannt.
        </p>
      </div>
    )
  }

  const critical = items.filter((i) => i.priority === 'CRITICAL')
  const medium   = items.filter((i) => i.priority === 'MEDIUM')
  const ordered  = [...critical, ...medium]

  return (
    <div className="flex flex-col gap-3">
      {ordered.map((item, idx) => {
        const cfg = PRIORITY_CONFIG[item.priority] ?? PRIORITY_CONFIG.MEDIUM
        return (
          <div
            key={idx}
            className={[
              'flex gap-4 p-4 rounded-xl border-l-2',
              cfg.border, cfg.bg,
            ].join(' ')}
          >
            {/* Priority badge + region */}
            <div className="flex-shrink-0 flex flex-col items-start gap-1.5 w-28">
              <span className={`${cfg.badge} text-white text-[10px] font-mono font-bold px-2 py-0.5 rounded`}>
                {cfg.label}
              </span>
              <span className={`${cfg.text} text-xs font-headline font-semibold`}>
                {item.region}
              </span>
            </div>

            {/* Description */}
            <p className="flex-1 font-body text-sm text-neutral/80 leading-relaxed">
              {item.text}
            </p>

          </div>
        )
      })}
    </div>
  )
}
