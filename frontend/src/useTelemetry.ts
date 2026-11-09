import { useCallback, useEffect, useRef, useState } from 'react'
import { request } from './api'
import type { Snapshot } from './types'

export type Connection = 'connecting' | 'streaming' | 'polling' | 'offline'

export function useTelemetry() {
  const latest = useRef<Snapshot | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const [frame, setFrame] = useState<Snapshot | null>(null)
  const [connection, setConnection] = useState<Connection>('connecting')

  const ingest = useCallback((snapshot: Snapshot, urgent = false) => {
    const previous = latest.current
    const newSession = previous?.session_id !== snapshot.session_id
    if (previous && !newSession && previous.revision >= snapshot.revision) return
    latest.current = snapshot
    if (urgent || newSession || previous?.status !== snapshot.status || previous?.run_id !== snapshot.run_id) {
      clearTimeout(timer.current)
      timer.current = undefined
      setFrame(snapshot)
    } else if (timer.current === undefined) {
      timer.current = window.setTimeout(() => {
        timer.current = undefined
        setFrame(latest.current)
      }, 170)
    }
  }, [])

  useEffect(() => {
    const abort = new AbortController()
    let socket: WebSocket | undefined
    let pollTimer: number | undefined, retryTimer: number | undefined, deadline: number | undefined
    let live = false, failures = 0, polling = false

    async function poll() {
      if (live || polling || abort.signal.aborted) return
      polling = true
      try {
        const snapshot = await request<Snapshot>('/simulation/status', undefined, 'GET', abort.signal)
        if (!live && !abort.signal.aborted) {
          ingest(snapshot)
          if (failures) setConnection('polling')
        }
      } catch {
        if (!live && !abort.signal.aborted) setConnection('offline')
      } finally {
        polling = false
      }
      if (!live && !abort.signal.aborted) pollTimer = window.setTimeout(poll, 1000)
    }

    function connect() {
      if (abort.signal.aborted) return
      const url = new URL('/ws/simulation', window.location.href)
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      const current = new WebSocket(url)
      socket = current
      deadline = window.setTimeout(() => { if (!live) current.close() }, 4000)
      current.onmessage = (message) => {
        if (abort.signal.aborted) return
        try {
          const snapshot = JSON.parse(String(message.data)) as Snapshot
          if (typeof snapshot.session_id !== 'string' || !Array.isArray(snapshot.agents)) return
          if (!live) {
            live = true
            failures = 0
            clearTimeout(deadline)
            clearTimeout(pollTimer)
            setConnection('streaming')
          }
          ingest(snapshot)
        } catch {
          current.close()
        }
      }
      current.onerror = () => current.close()
      current.onclose = () => {
        clearTimeout(deadline)
        if (abort.signal.aborted) return
        live = false
        failures += 1
        setConnection(latest.current ? 'polling' : 'offline')
        clearTimeout(pollTimer)
        void poll()
        retryTimer = window.setTimeout(connect, Math.min(6000, 400 * 2 ** Math.min(failures, 4)))
      }
    }
    retryTimer = window.setTimeout(() => { connect(); void poll() }, 0)
    return () => {
      abort.abort()
      socket?.close()
      clearTimeout(deadline)
      clearTimeout(retryTimer)
      clearTimeout(pollTimer)
      clearTimeout(timer.current)
      timer.current = undefined
    }
  }, [ingest])

  return { latest, frame, connection, ingest }
}
