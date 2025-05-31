import { useEffect, useRef, useCallback } from 'react'
import { useSessionStore } from '@/store/sessionStore'
import { useAppStore } from '@/store/appStore'
import toast from 'react-hot-toast'

export interface WebSocketMessage {
  type: string
  content?: string
  session_id?: string
  conversation_id?: string
  full_response?: string
  timestamp?: number
  [key: string]: any
}

export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5
  
  const {
    setWsConnection,
    setAgentStatus,
    addToCurrentResponse,
    setCurrentResponse,
    clearCurrentResponse,
    addMessage,
  } = useSessionStore()
  
  const { setConnectionStatus } = useAppStore()

  const connect = useCallback(() => {
    if (!sessionId) return

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`
      
      wsRef.current = new WebSocket(wsUrl)
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        setConnectionStatus(true)
        setWsConnection(wsRef.current)
        reconnectAttemptsRef.current = 0
        
        // Send ping to verify connection
        wsRef.current?.send(JSON.stringify({
          type: 'ping',
          timestamp: Date.now()
        }))
      }
      
      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setConnectionStatus(false)
        setWsConnection(null)
        setAgentStatus('idle')
        
        // Attempt to reconnect if not a normal closure
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++
            connect()
          }, delay)
        }
      }
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus(false)
      }
      
    } catch (error) {
      console.error('Error creating WebSocket connection:', error)
      setConnectionStatus(false)
    }
  }, [sessionId, setConnectionStatus, setWsConnection, setAgentStatus])

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'pong':
        // Connection verified
        break
        
      case 'agent_response_start':
        setAgentStatus('responding')
        clearCurrentResponse()
        break
        
      case 'agent_response_chunk':
        if (message.content) {
          addToCurrentResponse(message.content)
        }
        break
        
      case 'agent_response_end':
        setAgentStatus('idle')
        if (message.full_response) {
          // Add the complete message to conversation
          addMessage({
            id: crypto.randomUUID(),
            conversation_id: message.conversation_id || '',
            role: 'assistant',
            content: message.full_response,
            message_type: 'text',
            tokens_used: 0,
            metadata: {},
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          })
        }
        clearCurrentResponse()
        break
        
      case 'code_execution':
        setAgentStatus('executing')
        toast.loading('Executing code...', { id: 'code-execution' })
        break
        
      case 'code_result':
        setAgentStatus('idle')
        toast.dismiss('code-execution')
        if (message.success) {
          toast.success('Code executed successfully')
        } else {
          toast.error('Code execution failed')
        }
        break
        
      case 'file_change':
        toast.success(`File ${message.action}: ${message.filepath}`)
        break
        
      case 'agent_error':
        setAgentStatus('error')
        toast.error(`Agent error: ${message.error}`)
        break
        
      case 'error':
        toast.error(message.message || 'An error occurred')
        break
        
      default:
        console.log('Unknown message type:', message.type, message)
    }
  }, [setAgentStatus, addToCurrentResponse, clearCurrentResponse, addMessage])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
      return true
    } else {
      toast.error('Connection lost. Please refresh the page.')
      return false
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounting')
    }
    setConnectionStatus(false)
    setWsConnection(null)
  }, [setConnectionStatus, setWsConnection])

  useEffect(() => {
    if (sessionId) {
      connect()
    }
    
    return () => {
      disconnect()
    }
  }, [sessionId, connect, disconnect])

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    sendMessage,
    disconnect,
    reconnect: connect,
  }
}
