import { useState, type CSSProperties, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const inputStyle: CSSProperties = {
  width: '100%', border: '1px solid #E5E7EB', borderRadius: 8, padding: '12px 14px',
  fontSize: 15, fontFamily: 'Inter,sans-serif', color: '#1A1A1A', background: '#fff',
  outline: 'none', transition: 'border-color 0.2s, box-shadow 0.2s',
}

function MotaviMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#6C3AED" />
      <path d="M8 23L12 9l4 10 4-10 4 14" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  )
}

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/app'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [status, setStatus] = useState<'idle' | 'loading' | 'success'>('idle')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setStatus('loading')
    try {
      await login(email, password)
      setStatus('success')
      setTimeout(() => navigate(from, { replace: true }), 500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Anmeldung fehlgeschlagen.')
      setStatus('idle')
    }
  }

  const focusBrand = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.borderColor = '#6C3AED'
    e.currentTarget.style.boxShadow = '0 0 0 3px rgba(108,58,237,0.12)'
  }
  const blurBrand = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.borderColor = '#E5E7EB'
    e.currentTarget.style.boxShadow = 'none'
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '1fr 1fr', background: '#fff', fontFamily: 'Inter,sans-serif' }}>
      {/* Left panel */}
      <div style={{ background: '#111111', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 48, position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(rgba(108,58,237,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(108,58,237,0.1) 1px, transparent 1px)', backgroundSize: '50px 50px' }} />
        <div style={{ position: 'absolute', top: '30%', left: '20%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(108,58,237,0.2) 0%, transparent 70%)' }} />
        <Link to="/login" style={{ position: 'relative', zIndex: 2, display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <MotaviMark />
          <span style={{ fontFamily: 'Outfit,sans-serif', fontWeight: 700, fontSize: 20, color: '#fff', letterSpacing: '-0.3px' }}>motavi</span>
        </Link>
        <div style={{ position: 'relative', zIndex: 2, marginTop: 'auto', marginBottom: 40 }}>
          <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
            <div style={{ width: 28, height: 3, background: '#6C3AED', borderRadius: 2 }} />
            <div style={{ width: 8, height: 3, background: 'rgba(108,58,237,0.3)', borderRadius: 2 }} />
            <div style={{ width: 4, height: 3, background: 'rgba(108,58,237,0.15)', borderRadius: 2 }} />
          </div>
          <p style={{ fontFamily: 'Outfit,sans-serif', fontSize: 22, fontWeight: 600, color: '#fff', lineHeight: 1.5, letterSpacing: '-0.3px', marginBottom: 16 }}>
            Internes Werkzeug für Analyse, Expertenbewertung und Steckbrief.
          </p>
          <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.45)' }}>● Nur für das Motavi-Team</span>
        </div>
      </div>

      {/* Right panel */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
        <div style={{ width: '100%', maxWidth: 420 }}>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', marginBottom: 56 }}>
            <MotaviMark />
            <span style={{ fontFamily: 'Outfit,sans-serif', fontWeight: 700, fontSize: 20, color: '#1A1A1A', letterSpacing: '-0.3px' }}>motavi</span>
          </Link>

          <h1 style={{ fontFamily: 'Outfit,sans-serif', fontSize: 30, fontWeight: 800, color: '#1A1A1A', letterSpacing: '-0.5px', marginBottom: 8 }}>Willkommen zurück</h1>
          <p style={{ fontSize: 15, color: '#6B7280', marginBottom: 40 }}>Melden Sie sich an, um Ihre Analysen aufzurufen.</p>

          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, padding: '10px 14px', fontSize: 13, color: '#dc2626', marginBottom: 16 }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 20 }}>
              <label htmlFor="email" style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#1A1A1A', marginBottom: 6 }}>E-Mail-Adresse</label>
              <input id="email" type="email" autoComplete="email" placeholder="name@unternehmen.de" value={email}
                onChange={(e) => setEmail(e.target.value)} onFocus={focusBrand} onBlur={blurBrand} style={inputStyle} />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label htmlFor="password" style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#1A1A1A', marginBottom: 6 }}>Passwort</label>
              <div style={{ position: 'relative' }}>
                <input id="password" type={showPw ? 'text' : 'password'} autoComplete="current-password" placeholder="••••••••" value={password}
                  onChange={(e) => setPassword(e.target.value)} onFocus={focusBrand} onBlur={blurBrand} style={{ ...inputStyle, paddingRight: 44 }} />
                <button type="button" aria-label="Passwort anzeigen" onClick={() => setShowPw((v) => !v)}
                  style={{ position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#9CA3AF', display: 'flex', alignItems: 'center', padding: 0 }}>
                  {showPw ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            <button type="submit" disabled={status !== 'idle'}
              style={{
                width: '100%', background: status === 'success' ? '#22c55e' : '#6C3AED', color: '#fff',
                border: 'none', borderRadius: 8, padding: 14, fontSize: 15, fontWeight: 600,
                fontFamily: 'Inter,sans-serif', cursor: status === 'idle' ? 'pointer' : 'default',
                marginTop: 8, transition: 'background 0.2s',
              }}>
              {status === 'loading' ? 'Anmelden…' : status === 'success' ? '✓ Weiterleitung…' : 'Anmelden'}
            </button>
          </form>

          <p style={{ textAlign: 'center', marginTop: 24, fontSize: 14, color: '#6B7280' }}>
            Noch kein Zugang?{' '}
            <Link to="/#demo" style={{ color: '#6C3AED', textDecoration: 'none', fontWeight: 500 }}>Demo anfragen →</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
