import { type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { BERATER_ROLLEN } from '../api/workplace'
import { useAuth } from './AuthContext'
import RequireAuth from './RequireAuth'

/** Signed in and role "berater" (or "admin"); the API checks the same. */
export default function RequireBerater({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <BeraterOnly>{children}</BeraterOnly>
    </RequireAuth>
  )
}

function BeraterOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (user && BERATER_ROLLEN.includes(user.role)) return <>{children}</>
  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-6">
      <div className="max-w-md w-full p-8 rounded-2xl bg-bg-secondary text-center">
        <p className="font-headline text-xl text-white mb-2">Nur für angemeldete Berater</p>
        <p className="font-body text-sm text-neutral/60 mb-6">
          Die Bewertung der Ablaufschritte ist Beratern vorbehalten.
        </p>
        <Link to="/app" className="font-body text-sm text-data underline underline-offset-4">
          Zur Analyse
        </Link>
      </div>
    </div>
  )
}
