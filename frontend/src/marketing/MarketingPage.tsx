// ─── Motavi Marketing Site (ported from design handoff marketing.jsx) ───────
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react'
import { Link } from 'react-router-dom'

// ── Demo / Calendly modal context ──────────────────────────────────────────
const CALENDLY_URL = 'https://calendly.com/motavi/demo'

const DemoContext = createContext<() => void>(() => {})
const useDemo = () => useContext(DemoContext)

function CalendlyModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])
  if (!open) return null
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 2000,
        background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(3px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'relative', width: '100%', maxWidth: 900, height: '80vh',
          background: '#fff', borderRadius: 12, overflow: 'hidden',
          boxShadow: '0 24px 80px rgba(0,0,0,0.35)',
        }}
      >
        <button
          onClick={onClose}
          aria-label="Schließen"
          style={{
            position: 'absolute', top: 12, right: 12, zIndex: 2,
            background: '#fff', border: '1px solid #E5E7EB', borderRadius: '50%',
            width: 34, height: 34, cursor: 'pointer', display: 'flex',
            alignItems: 'center', justifyContent: 'center', color: '#6B7280',
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
        <iframe
          title="Demo buchen"
          src={`${CALENDLY_URL}?hide_gdpr_banner=1&primary_color=6c3aed`}
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      </div>
    </div>
  )
}

// ── Logo ────────────────────────────────────────────────────────────────────
function Logo({ light = false }: { light?: boolean }) {
  const c = light ? '#fff' : '#1A1A1A'
  return (
    <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <rect width="32" height="32" rx="6" fill="#6C3AED" />
        <path d="M8 23L12 9l4 10 4-10 4 14" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>
      <span style={{ fontFamily: 'Outfit,sans-serif', fontWeight: 700, fontSize: 20, color: c, letterSpacing: '-0.3px' }}>motavi</span>
    </Link>
  )
}

// ── Dotted Divider ─────────────────────────────────────────────────────────
function DottedDivider() {
  const items = Array.from({ length: 40 }, (_, i) => i)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 0 40px 0', justifyContent: 'flex-start' }}>
      {items.map((i) => {
        const t = i / 39
        const size = 6 - t * 4
        const radius = t * 50
        return (
          <div key={i} style={{ width: size, height: size, borderRadius: `${radius}%`, background: `rgba(108,58,237,${1 - t * 0.5})`, flexShrink: 0 }} />
        )
      })}
    </div>
  )
}

// ── Category Label ─────────────────────────────────────────────────────────
function CatLabel({ children, light = false }: { children: ReactNode; light?: boolean }) {
  return (
    <div style={{
      fontFamily: 'Inter,sans-serif', fontSize: 12, fontWeight: 600,
      letterSpacing: '0.12em', textTransform: 'uppercase',
      color: light ? 'rgba(255,255,255,0.6)' : '#6C3AED',
      display: 'flex', alignItems: 'center', gap: 6, marginBottom: 16,
    }}>
      <span>●</span> {children}
    </div>
  )
}

// ── Sticky Header ──────────────────────────────────────────────────────────
function Header() {
  const openDemo = useDemo()
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 60)
    window.addEventListener('scroll', handler)
    return () => window.removeEventListener('scroll', handler)
  }, [])

  const navStyle: CSSProperties = {
    position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000,
    background: scrolled ? 'rgba(17,17,17,0.97)' : 'transparent',
    backdropFilter: scrolled ? 'blur(12px)' : 'none',
    borderBottom: scrolled ? '1px solid rgba(255,255,255,0.08)' : 'none',
    transition: 'all 0.3s ease',
  }

  const navLinks = [
    { label: "So funktioniert's", href: '#wie' },
    { label: 'Use Cases', href: '#usecases' },
    { label: 'Unsere Vision', href: '#vision' },
  ]

  return (
    <nav style={navStyle}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 40px', height: 68, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Logo light />
        <div style={{ display: 'flex', alignItems: 'center', gap: 36 }}>
          {navLinks.map((item) => (
            <a key={item.label} href={item.href} style={{ fontFamily: 'Inter,sans-serif', fontSize: 14, fontWeight: 500, color: '#fff', textDecoration: 'none', opacity: 0.85, transition: 'opacity 0.2s' }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')} onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.85')}>
              {item.label}
            </a>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link to="/app" style={{ fontFamily: 'Inter,sans-serif', fontSize: 14, fontWeight: 500, color: '#fff', padding: '8px 18px', textDecoration: 'none', transition: 'border-color 0.2s', border: '1px solid rgba(255,255,255,0.35)', borderRadius: '6px' }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.7)')}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.35)')}>
            Anmelden
          </Link>
          <button onClick={openDemo} style={{ fontFamily: 'Inter,sans-serif', fontSize: 14, fontWeight: 600, color: '#fff', padding: '8px 18px', border: 'none', cursor: 'pointer', transition: 'background 0.2s', lineHeight: '1.4', borderRadius: '6px', background: 'rgb(108, 58, 237)' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#5a2fd6')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#6C3AED')}>
            Demo buchen
          </button>
        </div>
      </div>
    </nav>
  )
}

// ── Hero ───────────────────────────────────────────────────────────────────
function Hero() {
  const openDemo = useDemo()
  return (
    <section style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden', background: '#0a0a0f' }}>
      <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(rgba(108,58,237,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(108,58,237,0.08) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 80% 60% at 50% 40%, rgba(108,58,237,0.15) 0%, transparent 60%)' }} />
      <div style={{ position: 'absolute', top: '15%', right: '12%', width: 300, height: 300, borderRadius: '50%', background: 'rgba(108,58,237,0.07)', filter: 'blur(80px)' }} />
      <div style={{ position: 'absolute', bottom: '20%', left: '8%', width: 200, height: 200, borderRadius: '50%', background: 'rgba(108,58,237,0.05)', filter: 'blur(60px)' }} />

      <div style={{ position: 'relative', zIndex: 2, textAlign: 'center', maxWidth: 860, padding: '0 40px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 28, background: 'rgba(108,58,237,0.15)', border: '1px solid rgba(108,58,237,0.3)', borderRadius: 20, padding: '6px 16px' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#6C3AED', display: 'inline-block' }} />
          <span style={{ fontFamily: 'Inter,sans-serif', fontSize: 12, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.7)' }}>
            KI-gestützte Ergonomieanalyse
          </span>
        </div>
        <h1 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 'clamp(38px,5vw,64px)', fontWeight: 800, color: '#fff', lineHeight: 1.1, marginBottom: 24, letterSpacing: '-1px' }}>
          Ergonomie im Betrieb sollte keine<br />
          <span style={{ color: '#6C3AED' }}>Bauchentscheidung</span> sein.
        </h1>
        <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 18, color: 'rgba(255,255,255,0.65)', lineHeight: 1.7, maxWidth: 620, margin: '0 auto 40px' }}>
          Motavi analysiert Bewegungen Ihrer Mitarbeitenden automatisch. Kamerabasiert, KI-gestützt, datenschutzkonform.
        </p>
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap' }}>
          <button onClick={openDemo} style={{ fontFamily: 'Inter,sans-serif', fontWeight: 600, fontSize: 15, color: '#fff', padding: '14px 28px', border: 'none', cursor: 'pointer', transition: 'all 0.2s', background: 'rgb(108, 58, 237)', borderRadius: '6px', boxShadow: 'none' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#5a2fd6'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(108,58,237,0.4)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '#6C3AED'; e.currentTarget.style.boxShadow = 'none' }}>
            Demo buchen
          </button>
          <a href="#wie" style={{ fontFamily: 'Inter,sans-serif', fontWeight: 500, fontSize: 15, color: 'rgba(255,255,255,0.8)', textDecoration: 'underline', textUnderlineOffset: 4, padding: '14px 4px' }}>
            Mehr erfahren
          </a>
        </div>
      </div>
    </section>
  )
}

// ── Problem ────────────────────────────────────────────────────────────────
function Problem() {
  return (
    <section style={{ background: '#fff', padding: '120px 40px' }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <CatLabel>Handeln oder Haftungsrisiko tragen</CatLabel>
        <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 24, lineHeight: 1.7, color: '#1A1A1A', fontWeight: 400, marginBottom: 32 }}>
          Ergonomieanalysen werden heute manuell, punktuell und teuer durchgeführt. Durch externe Berater, zeitaufwändige Begehungen, subjektive Einschätzungen. CSRD-Berichtspflichten und steigende BG-Anforderungen erhöhen den Druck. Unternehmen handeln reaktiv statt präventiv.
        </p>
        <p style={{ fontFamily: 'Outfit,sans-serif', fontSize: 32, fontWeight: 800, color: '#1A1A1A', letterSpacing: '-0.5px' }}>
          Motavi ändert das.
        </p>
      </div>
    </section>
  )
}

// ── Abstract dot icons for steps ───────────────────────────────────────────
const stepIconStyles = `
  @keyframes dotPop {
    0%   { opacity: 0; transform: scale(0) translateY(4px); }
    60%  { opacity: 1; transform: scale(1.3) translateY(-1px); }
    100% { opacity: 1; transform: scale(1) translateY(0); }
  }
  @keyframes dotFloat {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-3px); }
  }
`

function StepIcon({ variant, animate = false }: { variant: number; animate?: boolean }) {
  const purple = '#6C3AED'
  const gray = '#D1D5DB'
  const SIZE = 80

  const dotStyle = (i: number): CSSProperties => ({
    animation: animate
      ? `dotPop 0.45s cubic-bezier(.34,1.56,.64,1) ${i * 0.055}s both, dotFloat ${1.8 + i * 0.12}s ease-in-out ${0.5 + i * 0.06}s infinite`
      : 'none',
    transformOrigin: 'center',
  })

  const dots1 = [[8, 8], [20, 12], [34, 8], [14, 22], [28, 18], [40, 24], [8, 36], [22, 32], [36, 36], [16, 44], [30, 42]]
  const dots2 = [[24, 6], [18, 12], [30, 12], [12, 20], [24, 18], [36, 20], [8, 28], [18, 28], [30, 28], [40, 28], [12, 36], [24, 36], [36, 36], [18, 44], [30, 44]]
  const dots3 = [[6, 6], [16, 10], [30, 8], [42, 6], [10, 20], [22, 16], [38, 22], [6, 32], [18, 28], [32, 30], [44, 34], [12, 42], [26, 44], [40, 40]]
  const dots4 = [[8, 8], [20, 8], [32, 8], [44, 8], [8, 20], [20, 20], [32, 20], [44, 20], [8, 32], [20, 32], [32, 32], [44, 32], [8, 44], [20, 44], [32, 44], [44, 44]]

  const sets = [dots1, dots2, dots3, dots4]
  const data = sets[variant - 1]
  const purpleCount = [4, 8, 4, 16][variant - 1]
  const radii = variant === 3 ? data.map((_, i) => (i % 3 === 0 ? 3.5 : 2)) : data.map(() => 2.5)

  return (
    <>
      <style>{stepIconStyles}</style>
      <svg width={SIZE} height={SIZE} viewBox="0 0 48 48" style={{ overflow: 'visible' }}>
        {data.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={radii[i]} fill={i < purpleCount ? purple : gray} style={dotStyle(i)} />
        ))}
      </svg>
    </>
  )
}

// ── How It Works ───────────────────────────────────────────────────────────
function HowItWorks() {
  const sectionRef = useRef<HTMLElement>(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true) }, { threshold: 0.15 })
    if (sectionRef.current) obs.observe(sectionRef.current)
    return () => obs.disconnect()
  }, [])

  const steps = [
    { n: '01', icon: 1, title: 'Aufnehmen', text: 'Videoaufnahme mit handelsüblichen Kameras – keine Sensorik, keine Wearables, keine aufwändige Infrastruktur.' },
    { n: '02', icon: 2, title: 'Analysieren', text: 'KI erkennt Körperhaltungen und berechnet automatisch REBA-Score und LMM-Punktwert für jede Bewegungssequenz.' },
    { n: '03', icon: 3, title: 'Klassifizieren', text: 'Bewegungsmuster werden kategorisiert: Körperhaltung, Lastenhandhabung, Risikostufe – nach Häufigkeit und Belastung.' },
    { n: '04', icon: 4, title: 'Berichten', text: 'Strukturierter Ergebnisbericht für Gefährdungsbeurteilung, Betriebsrat und Arbeitsschutzdokumentation.' },
  ]

  return (
    <section id="wie" ref={sectionRef} style={{ background: '#fff', padding: '0 40px 120px' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 80, marginBottom: 60 }}>
          <CatLabel>Von der Begehung zur kontinuierlichen Analyse</CatLabel>
          <h2 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 'clamp(32px,4vw,52px)', fontWeight: 800, color: '#1A1A1A', letterSpacing: '-1px', marginBottom: 12 }}>So funktioniert Motavi.</h2>
          <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 17, color: '#6B7280', maxWidth: 560 }}>Vier Schritte von der Videoaufnahme zum validierten Ergebnisbericht.</p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 24 }}>
          {steps.map((s, i) => (
            <div key={s.n} style={{
              border: '1px solid #E5E7EB', borderRadius: 10, padding: 28,
              transition: `border-color 0.2s, opacity 0.55s ${i * 0.13}s, transform 0.55s ${i * 0.13}s`,
              cursor: 'default', opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(28px)',
            }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#6C3AED')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#E5E7EB')}>
              <div style={{ marginBottom: 20 }}>
                <StepIcon variant={s.icon} animate={visible} />
              </div>
              <div style={{ fontFamily: 'Outfit,sans-serif', fontSize: 12, fontWeight: 700, color: '#6C3AED', letterSpacing: '0.1em', marginBottom: 8 }}>Schritt {s.n}</div>
              <div style={{ fontFamily: 'Outfit,sans-serif', fontSize: 20, fontWeight: 700, color: '#1A1A1A', marginBottom: 12 }}>{s.title}</div>
              <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 14, color: '#6B7280', lineHeight: 1.6, margin: 0 }}>{s.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ── Stats ──────────────────────────────────────────────────────────────────
function Stats() {
  const openDemo = useDemo()
  const stats = [
    { val: '10×', label: 'schnellere Analyse', sub: 'Statt wochenlanger Begehungen: Ergebnisse in Stunden.' },
    { val: '80 %', label: 'Kosteneinsparung', sub: 'Gegenüber externer Ergonomieberatung mit vergleichbarem Analysescope.' },
    { val: '100 %', label: 'Datenschutzkonform', sub: 'Anonymisierung vor Upload – kein Mitarbeiterbild verlässt den Betrieb.' },
  ]
  return (
    <section style={{ background: '#fff', padding: '0 40px 120px' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 80, textAlign: 'center', marginBottom: 64 }}>
          <CatLabel>Bewährt in der Produktion</CatLabel>
          <h2 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 'clamp(28px,4vw,48px)', fontWeight: 800, color: '#1A1A1A', letterSpacing: '-0.8px', marginBottom: 16 }}>Weniger Aufwand. Niedrigere Kosten. Schnellere Analyse.</h2>
          <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 16, color: '#6B7280', maxWidth: 680, margin: '0 auto' }}>Zwei anerkannte Analysemethoden, REBA-Score für Körperhaltung und Leitmerkmalmethode (LMM) für Lastenhandhabung, kombiniert in einem Bericht.</p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 1, borderTop: '1px solid #E5E7EB', borderBottom: '1px solid #E5E7EB' }}>
          {stats.map((s, i) => (
            <div key={i} style={{ padding: '48px 40px', borderRight: i < 2 ? '1px solid #E5E7EB' : 'none', textAlign: 'center' }}>
              <div style={{ fontFamily: 'Outfit,sans-serif', fontSize: 72, fontWeight: 300, color: '#1A1A1A', lineHeight: 1, letterSpacing: '-3px', marginBottom: 8 }}>{s.val}</div>
              <div style={{ fontFamily: 'Outfit,sans-serif', fontSize: 18, fontWeight: 700, color: '#1A1A1A', marginBottom: 10 }}>{s.label}</div>
              <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 14, color: '#6B7280', lineHeight: 1.5, margin: 0 }}>{s.sub}</p>
            </div>
          ))}
        </div>
        <div style={{ textAlign: 'center', marginTop: 48 }}>
          <button onClick={openDemo} style={{ display: 'inline-block', fontFamily: 'Inter,sans-serif', fontWeight: 600, fontSize: 15, color: '#fff', background: '#6C3AED', padding: '14px 28px', border: 'none', cursor: 'pointer', borderRadius: '6px' }}>Demo buchen</button>
        </div>
      </div>
    </section>
  )
}

// ── Use Case Charts ────────────────────────────────────────────────────────
function DonutChart() {
  const data = [{ pct: 22, color: '#22c55e' }, { pct: 45, color: '#f59e0b' }, { pct: 33, color: '#ef4444' }]
  let cum = 0
  const r = 70, cx = 90, cy = 90
  const paths = data.map((d) => {
    const start = (cum / 100) * Math.PI * 2 - Math.PI / 2
    cum += d.pct
    const end = (cum / 100) * Math.PI * 2 - Math.PI / 2
    const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start)
    const x2 = cx + r * Math.cos(end), y2 = cy + r * Math.sin(end)
    const large = d.pct > 50 ? 1 : 0
    return { path: `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z`, color: d.color, pct: d.pct }
  })
  return (
    <div style={{ background: '#f9fafb', borderRadius: 12, padding: 24 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 16, fontFamily: 'Inter' }}>● Risikoverteilung</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <svg width="180" height="180" viewBox="0 0 180 180">
          {paths.map((p, i) => <path key={i} d={p.path} fill={p.color} opacity={0.85} />)}
          <circle cx={cx} cy={cy} r={40} fill="white" />
        </svg>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[{ c: '#22c55e', l: 'Gering', v: '22%' }, { c: '#f59e0b', l: 'Mittel', v: '45%' }, { c: '#ef4444', l: 'Kritisch', v: '33%' }].map((x) => (
            <div key={x.l} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 10, height: 10, borderRadius: 2, background: x.c }} />
              <span style={{ fontSize: 13, color: '#6B7280', fontFamily: 'Inter,sans-serif' }}>{x.l}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#1A1A1A', fontFamily: 'Inter,sans-serif', marginLeft: 'auto' }}>{x.v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function REBATable() {
  const rows = [
    { wp: 'Kommissionierung A', reba: 7.2, lmm: 41, risk: 'Kritisch', color: '#ef4444' },
    { wp: 'Montageband Linie 3', reba: 5.1, lmm: 28, risk: 'Mittel', color: '#f59e0b' },
    { wp: 'Verpackung Station 2', reba: 3.4, lmm: 12, risk: 'Gering', color: '#22c55e' },
  ]
  return (
    <div style={{ background: '#f9fafb', borderRadius: 12, padding: 24 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 16, fontFamily: 'Inter' }}>● Analyse-Ergebnisse</div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'Inter,sans-serif', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
            {['Arbeitsplatz', 'REBA', 'LMM', 'Risiko'].map((h) => <th key={h} style={{ padding: '8px 0', textAlign: 'left', color: '#6B7280', fontWeight: 600 }}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.wp} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '10px 0', color: '#1A1A1A' }}>{row.wp}</td>
              <td style={{ padding: '10px 0', color: '#1A1A1A', fontWeight: 600 }}>{row.reba}</td>
              <td style={{ padding: '10px 0', color: '#1A1A1A', fontWeight: 600 }}>{row.lmm}</td>
              <td style={{ padding: '10px 0' }}><span style={{ background: `${row.color}20`, color: row.color, borderRadius: 4, padding: '2px 8px', fontSize: 12, fontWeight: 600 }}>{row.risk}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function BarChart() {
  const bars = [{ l: 'Standort A', v: 78 }, { l: 'Standort B', v: 54 }, { l: 'Standort C', v: 62 }]
  return (
    <div style={{ background: '#f9fafb', borderRadius: 12, padding: 24 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 20, fontFamily: 'Inter' }}>● Belastungsindex nach Standort</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {bars.map((b) => (
          <div key={b.l}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13, fontFamily: 'Inter,sans-serif' }}>
              <span style={{ color: '#6B7280' }}>{b.l}</span>
              <span style={{ color: '#1A1A1A', fontWeight: 600 }}>{b.v}</span>
            </div>
            <div style={{ background: '#E5E7EB', borderRadius: 4, height: 8 }}>
              <div style={{ width: `${b.v}%`, height: '100%', borderRadius: 4, background: '#6C3AED' }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function BodyHeatmap() {
  const BodyFigure = ({ label, regions }: { label: string; regions: Record<string, string> }) => (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#6B7280', letterSpacing: '0.08em', textTransform: 'uppercase', fontFamily: 'Inter,sans-serif' }}>{label}</div>
      <svg viewBox="0 0 100 220" style={{ width: '100%', maxWidth: 100 }}>
        <ellipse cx="50" cy="20" rx="13" ry="15" fill={regions.head} opacity="0.85" />
        <rect x="28" y="40" width="44" height="54" rx="5" fill={regions.torso} opacity="0.85" />
        <rect x="8" y="42" width="17" height="44" rx="5" fill={regions.armL} opacity="0.85" />
        <rect x="75" y="42" width="17" height="44" rx="5" fill={regions.armR} opacity="0.85" />
        <rect x="28" y="98" width="19" height="50" rx="5" fill={regions.legLT} opacity="0.85" />
        <rect x="53" y="98" width="19" height="50" rx="5" fill={regions.legRT} opacity="0.85" />
        <rect x="28" y="152" width="19" height="44" rx="5" fill={regions.legLB} opacity="0.85" />
        <rect x="53" y="152" width="19" height="44" rx="5" fill={regions.legRB} opacity="0.85" />
      </svg>
    </div>
  )
  const ist = { head: '#f59e0b', torso: '#ef4444', armL: '#f59e0b', armR: '#22c55e', legLT: '#ef4444', legRT: '#f59e0b', legLB: '#f59e0b', legRB: '#22c55e' }
  const soll = { head: '#22c55e', torso: '#f59e0b', armL: '#22c55e', armR: '#22c55e', legLT: '#22c55e', legRT: '#22c55e', legLB: '#22c55e', legRB: '#22c55e' }
  return (
    <div style={{ background: '#f9fafb', borderRadius: 12, padding: 24 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 20, fontFamily: 'Inter,sans-serif' }}>● Körperregionen-Belastung</div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <BodyFigure label="Ist-Zustand" regions={ist} />
        <div style={{ display: 'flex', alignItems: 'center', paddingTop: 64, flexShrink: 0 }}>
          <svg width="24" height="18" viewBox="0 0 28 20" fill="none">
            <path d="M2 10h20M16 4l8 6-8 6" stroke="#6C3AED" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <BodyFigure label="Nach Optimierung" regions={soll} />
      </div>
      <div style={{ display: 'flex', gap: 12, marginTop: 14 }}>
        {[{ c: '#ef4444', l: 'Hoch' }, { c: '#f59e0b', l: 'Mittel' }, { c: '#22c55e', l: 'Gering' }].map((x) => (
          <div key={x.l} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontFamily: 'Inter,sans-serif', color: '#6B7280' }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: x.c }} />
            {x.l}
          </div>
        ))}
      </div>
    </div>
  )
}

function LineChartBefore() {
  const before = [7.8, 7.2, 7.5, 6.9, 6.4, 5.8, 5.1, 4.6]
  const after: (number | null)[] = [null, null, null, null, 5.9, 5.2, 4.8, 4.2]
  const W = 280, H = 120, pad = { t: 10, r: 10, b: 24, l: 30 }
  const iW = W - pad.l - pad.r, iH = H - pad.t - pad.b
  const xScale = (i: number) => pad.l + (i / (before.length - 1)) * iW
  const yScale = (v: number) => pad.t + iH - ((v - 3) / (9 - 3)) * iH
  const bPath = before.map((v, i) => `${i === 0 ? 'M' : 'L'}${xScale(i)},${yScale(v)}`).join(' ')
  const aIdxs = after.map((v, i) => [v, i] as const).filter(([v]) => v !== null).map(([, i]) => i)
  const aVals = after.filter((v): v is number => v !== null)
  const aPath = aVals.map((v, j) => `${j === 0 ? 'M' : 'L'}${xScale(aIdxs[j])},${yScale(v)}`).join(' ')
  return (
    <div style={{ background: '#f9fafb', borderRadius: 12, padding: 24 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 16, fontFamily: 'Inter' }}>● Score-Verlauf vor/nach Optimierung</div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`}>
        <path d={bPath} fill="none" stroke="#6C3AED" strokeWidth="2" />
        <path d={aPath} fill="none" stroke="#22c55e" strokeWidth="2" strokeDasharray="4 2" />
        {['KW10', '', 'KW12', '', 'KW14', '', 'KW16', 'KW17'].map((l, i) => l && (
          <text key={i} x={xScale(i)} y={H - 4} textAnchor="middle" fontSize="9" fill="#9ca3af" fontFamily="Inter">{l}</text>
        ))}
      </svg>
      <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontFamily: 'Inter,sans-serif', color: '#6B7280' }}>
          <div style={{ width: 16, height: 2, background: '#6C3AED' }} />Vorher
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontFamily: 'Inter,sans-serif', color: '#6B7280' }}>
          <div style={{ width: 16, height: 2, background: '#22c55e', borderTop: '2px dashed #22c55e' }} />Nachher
        </div>
      </div>
    </div>
  )
}

// ── Use Cases ──────────────────────────────────────────────────────────────
function UseCases() {
  const openDemo = useDemo()
  const [active, setActive] = useState(0)
  const tabs = [
    {
      label: 'Ergonomie-Erstanalyse',
      title: 'Schnelle Bestandsaufnahme ohne Berateraufwand',
      text: 'Innerhalb weniger Stunden erhalten Sie eine vollständige Übersicht der ergonomischen Risiken an Ihren Arbeitsplätzen – ohne externe Berater, ohne aufwändige Vorbereitung.',
      bullets: ['Kamerabasierte Aufnahme mit Standardgeräten', 'Automatische Berechnung von REBA-Score und LMM-Punktwert', 'Ergebnisse in Stunden statt Wochen', 'Keine Schulung erforderlich'],
      chart: <DonutChart />,
    },
    {
      label: 'Gefährdungsbeurteilung',
      title: 'Dokumentation, die vor dem Betriebsrat standhält',
      text: 'Motavi liefert normenkonforme, nachvollziehbare Auswertungen als Grundlage für Ihre gesetzlich vorgeschriebene Gefährdungsbeurteilung – mit REBA und LMM als anerkannte Methoden.',
      bullets: ['Normenkonforme Auswertung nach ArbSchG §5', 'REBA-Score und LMM-Punktwert in einem Analysedurchgang', 'Anonymisierte Videoauswertung', 'Betriebsratskonform nach §87 Abs. 1 Nr. 6 BetrVG'],
      chart: <REBATable />,
    },
    {
      label: 'CSRD-Berichterstattung',
      title: 'Ergonomiedaten für ESG-Reporting auf Knopfdruck',
      text: 'Bereiten Sie sich auf die Nachhaltigkeitsprüfung vor – mit strukturierten Kennzahlen, die direkt in Ihr CSRD-Reporting nach ESRS S1 einfließen.',
      bullets: ['Strukturierte Kennzahlen für ESRS S1', 'Standortübergreifende Auswertung', 'Exportfähige Datenbasis', 'Vorbereitung auf Nachhaltigkeitsprüfung'],
      chart: <BarChart />,
    },
    {
      label: 'Wiedereingliederung',
      title: 'Arbeitsplätze risikogerecht zuweisen nach Krankheit',
      text: 'Fundierte Entscheidungsgrundlage für HR und Betriebsarzt – welcher Arbeitsplatz ist für welche körperliche Belastbarkeit geeignet.',
      bullets: ['Belastungsprofil pro Arbeitsplatz (REBA + LMM)', 'Abgleich mit ärztlichen Vorgaben', 'Dokumentation für BG und HR', 'Fundierte Entscheidungsgrundlage'],
      chart: <BodyHeatmap />,
    },
    {
      label: 'Prozessoptimierung',
      title: 'Ergonomie und Effizienz gemeinsam verbessern',
      text: 'Nutzen Sie Ergonomiedaten als Input für die Arbeitsplatzgestaltung und messen Sie den Erfolg von Umbauten mit belastbaren Vorher/Nachher-Daten.',
      bullets: ['Bewegungsanalyse als Input für Arbeitsplatzgestaltung', 'Vorher/Nachher-Vergleich nach Umbau (REBA + LMM)', 'Priorisierung nach Risikostufe', 'Basis für Investitionsentscheidungen'],
      chart: <LineChartBefore />,
    },
  ]

  const t = tabs[active]
  return (
    <section id="usecases" style={{ background: '#fff', padding: '0 40px 120px' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 80, marginBottom: 48 }}>
          <CatLabel>Use Cases</CatLabel>
          <h2 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 'clamp(28px,4vw,48px)', fontWeight: 800, color: '#1A1A1A', letterSpacing: '-0.8px', marginBottom: 12 }}>Viele Belastungsszenarien, eine Plattform.</h2>
          <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 17, color: '#6B7280', maxWidth: 600 }}>Motavi deckt die häufigsten Risikobereiche in Produktion und Logistik ab. Strukturiert, nachvollziehbar, dokumentierbar.</p>
        </div>
        <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid #E5E7EB', marginBottom: 48, overflowX: 'auto' }}>
          {tabs.map((tab, i) => (
            <button key={i} onClick={() => setActive(i)} style={{
              fontFamily: 'Inter,sans-serif', fontSize: 14, fontWeight: active === i ? 600 : 400,
              color: active === i ? '#6C3AED' : '#6B7280', background: 'none', border: 'none',
              borderBottom: active === i ? '2px solid #6C3AED' : '2px solid transparent',
              padding: '12px 20px', cursor: 'pointer', whiteSpace: 'nowrap', transition: 'all 0.2s', marginBottom: -1,
            }}>
              {tab.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64, alignItems: 'start' }}>
          <div>
            <h3 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 26, fontWeight: 700, color: '#1A1A1A', marginBottom: 16, letterSpacing: '-0.3px' }}>{t.title}</h3>
            <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 16, color: '#6B7280', lineHeight: 1.7, marginBottom: 24 }}>{t.text}</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 32 }}>
              {t.bullets.map((b) => (
                <div key={b} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontFamily: 'Inter,sans-serif', fontSize: 15, color: '#1A1A1A' }}>
                  <span style={{ color: '#6C3AED', fontWeight: 700, marginTop: 1 }}>✓</span> {b}
                </div>
              ))}
            </div>
            <button onClick={openDemo} style={{ display: 'inline-block', fontFamily: 'Inter,sans-serif', fontWeight: 600, fontSize: 14, border: '1px solid #1A1A1A', padding: '10px 20px', cursor: 'pointer', transition: 'all 0.2s', color: 'rgb(26, 26, 26)', borderRadius: '6px', background: 'transparent' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = '#1A1A1A'; e.currentTarget.style.color = '#fff' }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#1A1A1A' }}>
              Demo buchen
            </button>
          </div>
          <div>{t.chart}</div>
        </div>
      </div>
    </section>
  )
}

// ── Testimonials ───────────────────────────────────────────────────────────
function Testimonials() {
  const cards = [
    { quote: 'Ergonomieanalysen haben uns bisher Wochen gekostet. Die Idee, das in Stunden zu erledigen, ist ein Paradigmenwechsel.', name: '[Platzhalter – Pilotpartner]', role: 'Leiter Arbeitssicherheit, Logistikunternehmen' },
    { quote: 'CSRD zwingt uns, Belastungsdaten zu dokumentieren. Bisher war das aufwändig. Das muss einfacher werden.', name: '[Platzhalter – Pilotpartner]', role: 'HSE Manager, Automobilzulieferer' },
    { quote: 'Wir haben zu wenige Fachkräfte für Arbeitssicherheit. Ein Tool, das die Analyse automatisiert, ist überfällig.', name: '[Platzhalter – Pilotpartner]', role: 'Betriebsrat, Produktionswerk' },
  ]
  return (
    <section style={{ background: '#fff', padding: '0 40px 120px' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 80, marginBottom: 56 }}>
          <CatLabel>Das sagt die Industrie</CatLabel>
          <h2 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 'clamp(28px,3.5vw,44px)', fontWeight: 800, color: '#1A1A1A', letterSpacing: '-0.8px' }}>Was Verantwortliche in der Produktion sagen.</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 24 }}>
          {cards.map((c, i) => (
            <div key={i} style={{ border: '1px solid #E5E7EB', borderRadius: 10, padding: 32, display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ fontSize: 40, color: '#6C3AED', fontFamily: 'Georgia,serif', lineHeight: 1 }}>"</div>
              <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 15, color: '#1A1A1A', lineHeight: 1.7, margin: 0, fontStyle: 'italic' }}>{c.quote}</p>
              <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 16, marginTop: 'auto' }}>
                <div style={{ fontFamily: 'Inter,sans-serif', fontSize: 14, fontWeight: 600, color: '#1A1A1A' }}>{c.name}</div>
                <div style={{ fontFamily: 'Inter,sans-serif', fontSize: 13, color: '#6B7280', marginTop: 2 }}>{c.role}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ── Live Demo CTA ──────────────────────────────────────────────────────────
function DemoCTA() {
  const openDemo = useDemo()
  return (
    <section id="demo" style={{ background: '#fff', padding: '0 40px 120px' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <DottedDivider />
        <div style={{ textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', marginBottom: 24, background: '#f5f3ff', borderRadius: '50%', width: 56, height: 56, alignItems: 'center', justifyContent: 'center' }}>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="6" fill="#6C3AED" />
              <path d="M8 23L12 9l4 10 4-10 4 14" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h2 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 'clamp(32px,4vw,52px)', fontWeight: 800, color: '#1A1A1A', letterSpacing: '-0.8px', marginBottom: 16 }}>Erleben Sie Motavi live.</h2>
          <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 17, color: '#6B7280', maxWidth: 560, margin: '0 auto 36px', lineHeight: 1.7 }}>In einer persönlichen Demo zeigen wir Ihnen, wie Motavi Ihre Ergonomieanalyse in Stunden statt Wochen umsetzt. Datenschutzkonform und ohne Infrastrukturaufwand.</p>
          <button onClick={openDemo} style={{ display: 'inline-block', fontFamily: 'Inter,sans-serif', fontWeight: 600, fontSize: 16, color: '#fff', background: '#6C3AED', padding: '15px 32px', border: 'none', cursor: 'pointer', borderRadius: '6px' }}>Demo buchen</button>
        </div>
      </div>
    </section>
  )
}

// ── Vision / Founder ───────────────────────────────────────────────────────
function Vision() {
  return (
    <section id="vision" style={{ background: '#111111', padding: '100px 40px' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'center' }}>
        <div>
          <CatLabel light>Unsere Vision · Ergonomie als Standard, nicht als Ausnahme</CatLabel>
          <p style={{ fontFamily: 'Outfit,sans-serif', fontSize: 24, fontWeight: 400, color: 'rgba(255,255,255,0.9)', lineHeight: 1.7, margin: 0 }}>Europas Fertigungsbetriebe stehen weiter vor einem Wandel: Steigende Belastungen, alternde Belegschaften, wachsende Compliance-Anforderungen. Wir glauben, dass kamerabasierte KI den Zugang zu professioneller Ergonomieanalyse demokratisiert. Für jeden Betrieb, nicht nur für Konzerne mit eigenem Arbeitsschutzstab. Motavi macht das möglich.</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 20 }}>
          <div style={{ width: 120, height: 120, borderRadius: '50%', background: 'linear-gradient(135deg, #2d1b6b 0%, #6C3AED 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid rgba(108,58,237,0.4)' }}>
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <circle cx="24" cy="18" r="10" fill="rgba(255,255,255,0.3)" />
              <ellipse cx="24" cy="38" rx="16" ry="10" fill="rgba(255,255,255,0.2)" />
            </svg>
          </div>
          <div>
            <div style={{ fontFamily: 'Outfit,sans-serif', fontSize: 18, fontWeight: 700, color: '#fff' }}>Alexander Heinz</div>
            <div style={{ fontFamily: 'Inter,sans-serif', fontSize: 14, color: 'rgba(255,255,255,0.55)', marginBottom: 12 }}>Gründer & CEO</div>
            <a href="https://www.linkedin.com" target="_blank" rel="noreferrer" style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'Inter,sans-serif', fontSize: 13, color: 'rgba(255,255,255,0.5)', textDecoration: 'none', transition: 'color 0.2s' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.9)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.5)')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" /><circle cx="4" cy="4" r="2" /></svg>
              LinkedIn
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Trust / Certifications ─────────────────────────────────────────────────
function Trust() {
  return (
    <section style={{ background: '#fff', padding: '80px 40px' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80 }}>
        <div>
          <div style={{ fontFamily: 'Inter,sans-serif', fontSize: 12, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#6C3AED', marginBottom: 24 }}>● Datenschutz & Compliance</div>
          {['Anonymisierung vor Upload (kein Personenbezug)', 'DSGVO-konform', 'Made in Germany', 'On-Premise-Betrieb möglich'].map((item) => (
            <div key={item} style={{ display: 'flex', gap: 10, alignItems: 'center', fontFamily: 'Inter,sans-serif', fontSize: 15, color: '#1A1A1A', marginBottom: 14 }}>
              <span style={{ color: '#6C3AED', fontWeight: 700 }}>✓</span> {item}
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontFamily: 'Inter,sans-serif', fontSize: 12, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#6C3AED', marginBottom: 24 }}>● Entwickelt mit / Unterstützt von</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ border: '1px solid #E5E7EB', borderRadius: 8, height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Inter,sans-serif', fontSize: 11, color: '#9CA3AF' }}>
                Partner {i}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Final CTA ──────────────────────────────────────────────────────────────
function FinalCTA() {
  const openDemo = useDemo()
  return (
    <section style={{ background: '#fff', borderTop: '1px solid #E5E7EB' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: 420 }}>
        <div style={{ background: 'linear-gradient(135deg, #1a1225 0%, #2d1b6b 50%, #0f0f1a 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,20px)', gap: 8, justifyContent: 'center', marginBottom: 16 }}>
              {Array.from({ length: 24 }).map((_, i) => (
                <div key={i} style={{ width: 20, height: 20, borderRadius: 2, background: `rgba(108,58,237,${0.2 + ((i * 37) % 60) / 100})` }} />
              ))}
            </div>
            <div style={{ fontFamily: 'Inter,sans-serif', fontSize: 11, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Produktionsumgebung</div>
          </div>
        </div>
        <div style={{ padding: '64px 56px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <CatLabel>Lernen Sie Motavi kennen</CatLabel>
          <h2 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 'clamp(24px,3vw,40px)', fontWeight: 800, color: '#1A1A1A', letterSpacing: '-0.5px', marginBottom: 16 }}>Ergonomie neu denken. Für Ihren Betrieb.</h2>
          <p style={{ fontFamily: 'Inter,sans-serif', fontSize: 16, color: '#6B7280', lineHeight: 1.7, marginBottom: 32 }}>Buchen Sie eine kostenfreie Demo und sehen Sie, wie Motavi Ihre erste Analyse in unter einem Tag ermöglicht.</p>
          <button onClick={openDemo} style={{ fontFamily: 'Inter,sans-serif', fontWeight: 600, fontSize: 15, color: '#fff', background: '#6C3AED', padding: '14px 28px', border: 'none', cursor: 'pointer', alignSelf: 'flex-start', borderRadius: '6px' }}>Demo buchen</button>
        </div>
      </div>
    </section>
  )
}

// ── Footer ─────────────────────────────────────────────────────────────────
function Footer() {
  const cols = [
    { head: 'Produkt', links: ["So funktioniert's", 'Use Cases', 'Demo buchen'] },
    { head: 'Unternehmen', links: ['Unsere Vision', 'LinkedIn'] },
    { head: 'Rechtliches', links: ['Datenschutzrichtlinie', 'Impressum', 'Cookie Einstellungen'] },
  ]
  return (
    <footer style={{ background: '#fff', borderTop: '1px solid #E5E7EB', padding: '0 40px' }}>
      <DottedDivider />
      <div style={{ maxWidth: 1200, margin: '0 auto', paddingBottom: 32 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 40, marginBottom: 48 }}>
          <div><Logo /></div>
          {cols.map((col) => (
            <div key={col.head}>
              <div style={{ fontFamily: 'Inter,sans-serif', fontSize: 12, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#1A1A1A', marginBottom: 16 }}>{col.head}</div>
              {col.links.map((l) => (
                <a key={l} href="#" style={{ display: 'block', fontFamily: 'Inter,sans-serif', fontSize: 14, color: '#6B7280', textDecoration: 'none', marginBottom: 10, transition: 'color 0.2s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = '#1A1A1A')} onMouseLeave={(e) => (e.currentTarget.style.color = '#6B7280')}>
                  {l}
                </a>
              ))}
            </div>
          ))}
        </div>
        <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'Inter,sans-serif', fontSize: 13, color: '#9CA3AF' }}>© 2026 Motavi</span>
          <a href="mailto:hello@motavi.ai" style={{ fontFamily: 'Inter,sans-serif', fontSize: 13, color: '#6B7280', textDecoration: 'none' }}>Kontakt</a>
        </div>
      </div>
    </footer>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────
export default function MarketingPage() {
  const [demoOpen, setDemoOpen] = useState(false)
  return (
    <DemoContext.Provider value={() => setDemoOpen(true)}>
      <div style={{ background: '#fff', color: '#1A1A1A' }}>
        <Header />
        <main>
          <Hero />
          <Problem />
          <HowItWorks />
          <Stats />
          <UseCases />
          <Testimonials />
          <DemoCTA />
          <Vision />
          <Trust />
          <FinalCTA />
        </main>
        <Footer />
        <CalendlyModal open={demoOpen} onClose={() => setDemoOpen(false)} />
      </div>
    </DemoContext.Provider>
  )
}
