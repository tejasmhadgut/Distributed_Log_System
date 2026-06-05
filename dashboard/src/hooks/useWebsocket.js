import { useState, useEffect, useRef, useCallback } from 'react'

export function useWebSocket(url) {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('connecting')
  const wsRef = useRef(null)
  const retryRef = useRef(null)
  const retryDelay = useRef(1000)

  const connect = useCallback(() => {
    if (!url) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      retryDelay.current = 1000
    }

    ws.onmessage = (event) => {
      try {
        setData(JSON.parse(event.data))
      } catch (e) {
        console.error('Failed to parse WS message', e)
      }
    }

    ws.onclose = () => {
      setStatus('disconnected')
      retryRef.current = setTimeout(() => {
        retryDelay.current = Math.min(retryDelay.current * 2, 30000)
        connect()
      }, retryDelay.current)
    }

    ws.onerror = () => ws.close()
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { data, status }
}
