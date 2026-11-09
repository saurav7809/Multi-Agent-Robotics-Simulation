import { useEffect, useState } from 'react'
import { request } from './api'
import type { Sample, Snapshot } from './types'

export function useRunHistory(frame: Snapshot) {
  const { session_id: session, run_id: run, status } = frame
  const [records, setRecords] = useState<{ session: string; run: number; samples: Sample[] } | null>(null)
  useEffect(() => {
    const abort = new AbortController()
    let after = -1, timer: number
    const accumulated: Sample[] = []
    async function sync() {
      try {
        const result = await request<{ session_id: string; run_id: number; samples: Sample[] }>(
          '/metrics/history?after=' + after, undefined, 'GET', abort.signal,
        )
        if (!abort.signal.aborted && result.session_id === session && result.run_id === run && result.samples.length) {
          accumulated.push(...result.samples)
          after = accumulated[accumulated.length - 1].time
          setRecords({ session, run, samples: [...accumulated] })
        }
      } catch {
        // The latest frame remains usable while the history request retries.
      }
      if (!abort.signal.aborted && status === 'running') timer = window.setTimeout(sync, 1500)
    }
    void sync()
    return () => { abort.abort(); clearTimeout(timer) }
  }, [run, session, status])

  const history = records?.session === session && records.run === run ? records.samples : []
  const tail = history.at(-1)
  const live: Sample = { time: frame.time, metrics: frame.metrics }
  const samples = tail && tail.time > frame.time ? history
    : [...(tail?.time === frame.time ? history.slice(0, -1) : history), live]
  const stride = Math.max(1, Math.ceil(samples.length / 360))
  return samples.filter((_, index) => index % stride === 0 || index === samples.length - 1)
}
