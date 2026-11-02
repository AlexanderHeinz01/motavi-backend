/**
 * Sign-in of the internal tool. With Firebase (backend GET /auth/config
 * returns a web config, decision 02.11.2026): Google, Microsoft or e-mail and
 * password; the backend checks the Firebase ID token and the access grant.
 * Without Firebase: the former password sign-in (development).
 */
import { initializeApp, type FirebaseApp } from 'firebase/app'
import {
  GoogleAuthProvider,
  OAuthProvider,
  getAuth,
  onIdTokenChanged,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  type Auth,
} from 'firebase/auth'
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { ApiFehler, fetchAuthConfig, fetchMe, fetchMeStatus, loginRequest, type UserPublic } from '../api/auth'

const TOKEN_KEY = 'motavi_token'

interface AuthState {
  user: UserPublic | null
  token: string | null
  loading: boolean
  /** Sign-in options of the page */
  anbieter: string[]
  /** Message after sign-in, e.g. no access or address not confirmed */
  hinweis: string | null
  loginPasswort: (email: string, password: string) => Promise<void>
  loginGoogle: () => Promise<void>
  loginMicrosoft: () => Promise<void>
  passwortVergessen: (email: string) => Promise<void>
  /** after confirming the e-mail address: fetch a fresh token */
  erneutPruefen: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | undefined>(undefined)

const FIREBASE_FEHLER: Record<string, string> = {
  'auth/invalid-credential': 'E-Mail oder Passwort ist falsch.',
  'auth/wrong-password': 'E-Mail oder Passwort ist falsch.',
  'auth/user-not-found': 'E-Mail oder Passwort ist falsch.',
  'auth/too-many-requests': 'Zu viele Versuche. Bitte warten Sie einige Minuten.',
  'auth/popup-closed-by-user': 'Die Anmeldung wurde abgebrochen.',
  'auth/unauthorized-domain': 'Diese Adresse ist in Firebase nicht als Domain freigegeben.',
  'auth/operation-not-allowed': 'Diese Anmeldeart ist in Firebase nicht aktiviert.',
}

function text(e: unknown): string {
  const code = (e as { code?: string })?.code
  if (code && FIREBASE_FEHLER[code]) return FIREBASE_FEHLER[code]
  return e instanceof Error ? e.message : String(e)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<UserPublic | null>(null)
  const [loading, setLoading] = useState(true)
  const [anbieter, setAnbieter] = useState<string[]>([])
  const [hinweis, setHinweis] = useState<string | null>(null)
  const authRef = useRef<Auth | null>(null)

  useEffect(() => {
    let abbrechen = () => {}
    fetchAuthConfig()
      .then((cfg) => {
        setAnbieter(cfg.anbieter)
        if (!cfg.firebase) return altesLogin()
        const app: FirebaseApp = initializeApp(cfg.firebase)
        const auth = getAuth(app)
        auth.languageCode = 'de'
        authRef.current = auth
        // fires on sign-in, sign-out and every token refresh (about hourly)
        abbrechen = onIdTokenChanged(auth, async (fb) => {
          if (!fb) {
            setUser(null)
            setToken(null)
            setLoading(false)
            return
          }
          const t = await fb.getIdToken()
          setToken(t)
          try {
            setUser(await fetchMeStatus(t))
            setHinweis(null)
          } catch (e) {
            setUser(null)
            setHinweis(e instanceof ApiFehler ? e.message : 'Anmeldung derzeit nicht möglich.')
          } finally {
            setLoading(false)
          }
        })
      })
      .catch(() => {
        setHinweis('Die Anmeldung ist derzeit nicht erreichbar.')
        setLoading(false)
      })
    return () => abbrechen()
  }, [])

  /** Former password sign-in: token in localStorage. */
  const altesLogin = async () => {
    const t = localStorage.getItem(TOKEN_KEY)
    if (!t) return setLoading(false)
    try {
      setUser(await fetchMe(t))
      setToken(t)
    } catch {
      localStorage.removeItem(TOKEN_KEY)
    } finally {
      setLoading(false)
    }
  }

  const loginPasswort = async (email: string, password: string) => {
    setHinweis(null)
    const auth = authRef.current
    if (!auth) {
      const res = await loginRequest(email, password)
      localStorage.setItem(TOKEN_KEY, res.access_token)
      setToken(res.access_token)
      setUser(res.user)
      return
    }
    try {
      const cred = await signInWithEmailAndPassword(auth, email, password)
      if (!cred.user.emailVerified) {
        await sendEmailVerification(cred.user)
        setHinweis('Bitte bestätigen Sie zuerst Ihre E-Mail-Adresse. Wir haben Ihnen dafür eine E-Mail geschickt.')
      }
    } catch (e) {
      throw new Error(text(e))
    }
  }

  const popup = async (provider: GoogleAuthProvider | OAuthProvider) => {
    setHinweis(null)
    if (!authRef.current) return
    try {
      await signInWithPopup(authRef.current, provider)
    } catch (e) {
      throw new Error(text(e))
    }
  }

  const passwortVergessen = async (email: string) => {
    if (!authRef.current) return
    try {
      await sendPasswordResetEmail(authRef.current, email)
    } catch (e) {
      throw new Error(text(e))
    }
  }

  const erneutPruefen = async () => {
    const fb = authRef.current?.currentUser
    if (!fb) return
    await fb.reload()
    await fb.getIdToken(true) // triggers onIdTokenChanged with the confirmed address
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    setToken(null)
    setHinweis(null)
    if (authRef.current) void signOut(authRef.current)
  }

  return (
    <AuthContext.Provider
      value={{
        user, token, loading, anbieter, hinweis, loginPasswort,
        loginGoogle: () => popup(new GoogleAuthProvider()),
        loginMicrosoft: () => popup(new OAuthProvider('microsoft.com')),
        passwortVergessen, erneutPruefen, logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
