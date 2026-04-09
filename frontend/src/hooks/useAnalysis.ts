import { useEffect, useRef, useState } from 'react'
import { getAnalysisStatus, type AnalysisStatus } from '../api/motavi'

const POLL_MS = 3_000

export function useAnalysis(jobId: string | undefined): AnalysisStatus {
  const [state, setState] = useState<AnalysisStatus>({ status: 'processing' })
  const cancelledRef = useRef(false)

  useEffect(() => {
    if (!jobId) return
    cancelledRef.current = false
    let timerId: ReturnType<typeof setTimeout> | null = null

    const poll = async () => {
      if (cancelledRef.current) return
      try {
        const data = await getAnalysisStatus(jobId)
        if (cancelledRef.current) return
        setState(data)
        if (data.status !== 'processing') return  // terminal state — stop polling
      } catch {
        if (cancelledRef.current) return
        setState({ status: 'error', error: 'Verbindungsfehler — wird erneut versucht…' })
      }
      if (!cancelledRef.current) timerId = setTimeout(poll, POLL_MS)
    }

    poll()
    return () => {
      cancelledRef.current = true
      if (timerId) clearTimeout(timerId)
    }
  }, [jobId])

  return state
}
