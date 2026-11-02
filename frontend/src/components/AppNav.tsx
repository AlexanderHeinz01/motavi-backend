import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `font-body text-sm transition-colors ${isActive ? 'text-white' : 'text-neutral/55 hover:text-white'}`

/** Menu of the internal tool: Dashboard (job overview), upload, accesses (admins). */
export default function AppNav() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <header className="border-b border-bg-secondary px-6 py-4 flex flex-wrap items-center justify-between gap-4">
      <nav aria-label="Werkzeug" className="flex items-center gap-6">
        <span className="font-headline text-lg font-bold tracking-tight text-white">MOTAVI</span>
        <NavLink to="/app/jobs" className={linkCls}>Dashboard</NavLink>
        <NavLink to="/app" end className={linkCls}>Hochladen</NavLink>
        {user?.role === 'admin' && <NavLink to="/app/zugaenge" className={linkCls}>Zugänge</NavLink>}
      </nav>
      <div className="flex items-center gap-3">
        {user && <span className="font-body text-xs text-neutral/40 hidden sm:inline">{user.email}</span>}
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="font-body text-xs text-neutral/50 hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-bg-secondary"
        >
          Abmelden
        </button>
      </div>
    </header>
  )
}
