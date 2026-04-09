// TODO: implement in Step 3
import { useEffect, useState } from 'react'
import { type AnalysisStatus } from '../api/motavi'

export function useAnalysis(jobId: string | undefined): AnalysisStatus {
  const [state, setState] = useState<AnalysisStatus>({ status: 'processing' })

  useEffect(() => {
    if (!jobId) return
    // TODO: poll GET /api/v1/analysis/{jobId} every 3 s, clear on done/error
  }, [jobId])

  return state
}
