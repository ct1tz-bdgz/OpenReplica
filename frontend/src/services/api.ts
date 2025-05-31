import axios from 'axios'
import type {
  Session,
  Agent,
  DirectoryListing,
  FileContent,
  CreateSessionRequest,
  CreateAgentRequest,
  WriteFileRequest,
} from '@/types'

// Create axios instance
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if needed
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Session API
export const sessionAPI = {
  create: async (data: CreateSessionRequest): Promise<Session> => {
    const response = await api.post('/sessions/create', data)
    return response.data
  },

  get: async (sessionId: string): Promise<Session> => {
    const response = await api.get(`/sessions/${sessionId}`)
    return response.data
  },

  list: async (): Promise<Session[]> => {
    const response = await api.get('/sessions/')
    return response.data.sessions
  },

  delete: async (sessionId: string): Promise<void> => {
    await api.delete(`/sessions/${sessionId}`)
  },

  getMessages: async (sessionId: string) => {
    const response = await api.get(`/sessions/${sessionId}/messages`)
    return response.data.messages
  },

  addMessage: async (sessionId: string, content: string, role: string = 'user') => {
    const response = await api.post(`/sessions/${sessionId}/messages`, null, {
      params: { content, role }
    })
    return response.data
  },

  getEvents: async (sessionId: string) => {
    const response = await api.get(`/sessions/${sessionId}/events`)
    return response.data.events
  },
}

// Agent API
export const agentAPI = {
  getTypes: async (): Promise<string[]> => {
    const response = await api.get('/agents/types')
    return response.data.agent_types
  },

  create: async (data: CreateAgentRequest): Promise<Agent> => {
    const response = await api.post('/agents/create', data)
    return response.data
  },

  get: async (agentId: string): Promise<Agent> => {
    const response = await api.get(`/agents/${agentId}`)
    return response.data
  },

  list: async (): Promise<Agent[]> => {
    const response = await api.get('/agents/')
    return response.data.agents
  },

  delete: async (agentId: string): Promise<void> => {
    await api.delete(`/agents/${agentId}`)
  },

  reset: async (agentId: string): Promise<Agent> => {
    const response = await api.post(`/agents/${agentId}/reset`)
    return response.data
  },
}

// File API
export const fileAPI = {
  list: async (sessionId: string, path: string = ''): Promise<DirectoryListing> => {
    const response = await api.get(`/files/${sessionId}/list`, {
      params: { path }
    })
    return response.data
  },

  read: async (sessionId: string, path: string): Promise<FileContent> => {
    const response = await api.get(`/files/${sessionId}/read`, {
      params: { path }
    })
    return response.data
  },

  write: async (sessionId: string, data: WriteFileRequest): Promise<void> => {
    await api.post(`/files/${sessionId}/write`, data)
  },

  delete: async (sessionId: string, path: string): Promise<void> => {
    await api.delete(`/files/${sessionId}/delete`, {
      params: { path }
    })
  },

  upload: async (sessionId: string, file: File, path: string = ''): Promise<void> => {
    const formData = new FormData()
    formData.append('file', file)
    
    await api.post(`/files/${sessionId}/upload`, formData, {
      params: { path },
      headers: {
        'Content-Type': 'multipart/form-data',
      }
    })
  },

  createDirectory: async (sessionId: string, path: string): Promise<void> => {
    await api.post(`/files/${sessionId}/create-directory`, null, {
      params: { path }
    })
  },
}

// WebSocket status API
export const wsAPI = {
  getStatus: async () => {
    const response = await api.get('/ws/status')
    return response.data
  },
}

// Health check
export const healthAPI = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
}

export default api
