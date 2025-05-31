import { io, Socket } from 'socket.io-client'
import type { WebSocketMessage, ConnectionStatus } from '@/types'

class WebSocketService {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private listeners: Map<string, Set<(data: any) => void>> = new Map()
  private connectionListeners: Set<(status: ConnectionStatus) => void> = new Set()

  connect(sessionId: string): void {
    if (this.socket?.connected) {
      this.disconnect()
    }

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/connect/${sessionId}`
    
    this.socket = io(wsUrl, {
      transports: ['websocket'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
    })

    this.setupEventHandlers(sessionId)
  }

  private setupEventHandlers(sessionId: string): void {
    if (!this.socket) return

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      this.notifyConnectionListeners({
        connected: true,
        session_id: sessionId,
      })
    })

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
      this.notifyConnectionListeners({
        connected: false,
        session_id: sessionId,
        error: reason,
      })
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.notifyConnectionListeners({
        connected: false,
        session_id: sessionId,
        error: error.message,
      })
    })

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('WebSocket reconnected after', attemptNumber, 'attempts')
      this.notifyConnectionListeners({
        connected: true,
        session_id: sessionId,
      })
    })

    this.socket.on('reconnect_error', (error) => {
      console.error('WebSocket reconnection error:', error)
      this.reconnectAttempts++
    })

    // Handle all message types
    this.socket.onAny((eventName: string, data: any) => {
      if (eventName.startsWith('socket.io')) return // Skip internal events
      
      const message: WebSocketMessage = {
        type: eventName,
        data,
        timestamp: new Date().toISOString(),
        session_id: sessionId,
      }

      this.notifyListeners(eventName, message)
    })
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  send(type: string, data: any): void {
    if (this.socket?.connected) {
      this.socket.emit(type, {
        type,
        data,
        timestamp: new Date().toISOString(),
      })
    } else {
      console.warn('WebSocket not connected, cannot send message:', type)
    }
  }

  // Convenience methods for common message types
  sendUserMessage(content: string): void {
    this.send('user_message', { content })
  }

  startAgent(agentType: string): void {
    this.send('start_agent', { agent_type: agentType })
  }

  stopAgent(): void {
    this.send('stop_agent', {})
  }

  sendFileOperation(operation: string, data: any): void {
    this.send('file_operation', { operation, ...data })
  }

  ping(): void {
    this.send('ping', { timestamp: Date.now() })
  }

  // Event listening
  on(eventType: string, callback: (data: any) => void): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    
    this.listeners.get(eventType)!.add(callback)
    
    // Return unsubscribe function
    return () => {
      const listeners = this.listeners.get(eventType)
      if (listeners) {
        listeners.delete(callback)
        if (listeners.size === 0) {
          this.listeners.delete(eventType)
        }
      }
    }
  }

  onConnection(callback: (status: ConnectionStatus) => void): () => void {
    this.connectionListeners.add(callback)
    
    return () => {
      this.connectionListeners.delete(callback)
    }
  }

  private notifyListeners(eventType: string, message: WebSocketMessage): void {
    const listeners = this.listeners.get(eventType)
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(message)
        } catch (error) {
          console.error('Error in WebSocket listener:', error)
        }
      })
    }

    // Also notify wildcard listeners
    const wildcardListeners = this.listeners.get('*')
    if (wildcardListeners) {
      wildcardListeners.forEach(callback => {
        try {
          callback(message)
        } catch (error) {
          console.error('Error in wildcard WebSocket listener:', error)
        }
      })
    }
  }

  private notifyConnectionListeners(status: ConnectionStatus): void {
    this.connectionListeners.forEach(callback => {
      try {
        callback(status)
      } catch (error) {
        console.error('Error in connection listener:', error)
      }
    })
  }

  get isConnected(): boolean {
    return this.socket?.connected ?? false
  }

  get connectionState(): string {
    if (!this.socket) return 'disconnected'
    return this.socket.connected ? 'connected' : 'disconnected'
  }
}

// Create singleton instance
export const websocketService = new WebSocketService()

// Hook for React components
import { useEffect, useState } from 'react'
import { useAppStore } from '@/stores/appStore'

export const useWebSocket = (sessionId: string | null) => {
  const { setConnected } = useAppStore()
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    connected: false,
  })

  useEffect(() => {
    if (!sessionId) return

    // Connect to WebSocket
    websocketService.connect(sessionId)

    // Listen for connection status changes
    const unsubscribe = websocketService.onConnection((status) => {
      setConnectionStatus(status)
      setConnected(status.connected)
    })

    return () => {
      unsubscribe()
      websocketService.disconnect()
    }
  }, [sessionId, setConnected])

  return {
    connectionStatus,
    isConnected: websocketService.isConnected,
    send: websocketService.send.bind(websocketService),
    sendUserMessage: websocketService.sendUserMessage.bind(websocketService),
    startAgent: websocketService.startAgent.bind(websocketService),
    stopAgent: websocketService.stopAgent.bind(websocketService),
    sendFileOperation: websocketService.sendFileOperation.bind(websocketService),
    on: websocketService.on.bind(websocketService),
  }
}

export default websocketService
