const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? ''

export interface UserPublic {
  email: string
  name?: string
  company?: string
  role: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserPublic
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') return data.detail
  } catch {
    /* ignore */
  }
  return `Anfrage fehlgeschlagen (${res.status}).`
}

export async function loginRequest(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function fetchMe(token: string): Promise<UserPublic> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}
