import { ref, readonly } from 'vue'

export interface WebSocketMessage {
  type: string
  data?: unknown
  [key: string]: unknown
}

class WebSocketService {
  private ws: WebSocket | null = null
  private messageHandlers: Map<string, Set<(data: unknown) => void>> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  
  public isConnected = ref(false)
  public connectionError = ref<string | null>(null)

  connect(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          this.isConnected.value = true
          this.connectionError.value = null
          this.reconnectAttempts = 0
          console.log('WebSocket connected')
          resolve()
        }

        this.ws.onclose = () => {
          this.isConnected.value = false
          console.log('WebSocket disconnected')
          this.attemptReconnect(url)
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.connectionError.value = '连接失败'
          reject(error)
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (e) {
            console.error('Failed to parse message:', e)
          }
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  private attemptReconnect(url: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      setTimeout(() => {
        this.connect(url).catch(() => {})
      }, this.reconnectDelay * this.reconnectAttempts)
    }
  }

  private handleMessage(message: WebSocketMessage) {
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => handler(message.data))
    }
  }

  on(type: string, handler: (data: unknown) => void) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set())
    }
    this.messageHandlers.get(type)!.add(handler)
  }

  off(type: string, handler: (data: unknown) => void) {
    this.messageHandlers.get(type)?.delete(handler)
  }

  send(type: string, data?: Record<string, unknown>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = data ? { type, ...data } : { type }
      this.ws.send(JSON.stringify(payload))
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

export const wsService = new WebSocketService()
export const isConnected = readonly(wsService.isConnected)
export const connectionError = readonly(wsService.connectionError)
