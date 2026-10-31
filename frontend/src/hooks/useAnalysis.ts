import { useEffect, useRef, useState } from 'react'
import { getAnalysisStatus, type AnalysisStatus } from '../api/motavi'
import { useAuth } from '../auth/AuthContext'

const POLL_MS = 3_000

export function useAnalysis(jobId: string | undefined): AnalysisStatus {
  const { token } = useAuth()
  const [state, setState] = useState<AnalysisStatus>({ status: 'processing' })
  const cancelledRef = useRef(false)

  useEffect(() => {
    if (!jobId || !token) return
    cancelledRef.current = false
    let timerId: ReturnType<typeof setTimeout> | null = null

    const poll = async () => {
      if (cancelledRef.current) return
      try {
        const data = await getAnalysisStatus(jobId, token)
        if (cancelledRef.current) return
        setState(data)
        if (data.status !== 'processing') return  // terminal state: stop polling
      } catch {
        if (cancelledRef.current) return
        setState({ status: 'error', error: 'Verbindungsfehler, wird erneut versucht …' })
      }
      if (!cancelledRef.current) timerId = setTimeout(poll, POLL_MS)
    }

    poll()
    return () => {
      cancelledRef.current = true
      if (timerId) clearTimeout(timerId)
    }
  }, [jobId, token])

  return state
}
