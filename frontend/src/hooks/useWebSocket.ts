import { useEffect, useRef, useCallback, useState } from 'react'
import { WsEvent } from '../types'

// Same-origin: in dev the Vite proxy forwards /ws to the backend; in prod nginx
// forwards it to the backend Cloud Run service.
const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
const RECONNECT_DELAY_MS = 3000

interface UseWebSocketReturn {
  isConnected: boolean
  lastEvent: WsEvent | null
  sendMessage: (msg: string) => void
}

export function useWebSocket(
  onMessage: (event: WsEvent) => void
): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      console.log('[WS] Connected')
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const data: WsEvent = JSON.parse(event.data)
        setLastEvent(data)
        onMessage(data)
      } catch (err) {
        console.warn('[WS] Failed to parse message', err)
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      console.log('[WS] Disconnected — reconnecting in 3s...')
      setIsConnected(false)
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS)
    }

    ws.onerror = (err) => {
      console.error('[WS] Error', err)
      ws.close()
    }
  }, [onMessage])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((msg: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(msg)
    }
  }, [])

  return { isConnected, lastEvent, sendMessage }
}
