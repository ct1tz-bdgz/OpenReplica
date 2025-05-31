import axios from 'axios'

// Create axios instance with base configuration
export const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add any auth headers here if needed
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Handle unauthorized
      console.error('Unauthorized access')
    } else if (error.response?.status >= 500) {
      // Handle server errors
      console.error('Server error:', error.response.data)
    }
    return Promise.reject(error)
  }
)

// API endpoints
export const sessionAPI = {
  list: (params?: { user_id?: string; limit?: number }) =>
    api.get('/sessions', { params }),
  
  get: (sessionId: string) =>
    api.get(`/sessions/${sessionId}`),
  
  create: (data: {
    title: string
    description?: string
    llm_provider?: string
    llm_model?: string
    temperature?: string
    max_tokens?: number
    git_repo?: string
    branch?: string
    metadata?: Record<string, any>
  }) => api.post('/sessions', data),
  
  update: (sessionId: string, data: Partial<{
    title: string
    description: string
    status: string
    metadata: Record<string, any>
  }>) => api.patch(`/sessions/${sessionId}`, data),
  
  delete: (sessionId: string) =>
    api.delete(`/sessions/${sessionId}`),
}

export const conversationAPI = {
  list: (sessionId: string) =>
    api.get(`/conversations/${sessionId}`),
  
  get: (conversationId: string) =>
    api.get(`/conversations/detail/${conversationId}`),
  
  create: (sessionId: string, data: {
    title: string
    agent_type?: string
    agent_config?: Record<string, any>
    metadata?: Record<string, any>
  }) => api.post(`/conversations/${sessionId}`, data),
  
  addMessage: (conversationId: string, data: {
    role: string
    content: string
    message_type?: string
    metadata?: Record<string, any>
  }) => api.post(`/conversations/${conversationId}/messages`, data),
  
  getMessages: (conversationId: string, limit?: number) =>
    api.get(`/conversations/${conversationId}/messages`, { params: { limit } }),
}

export const agentAPI = {
  getTypes: () =>
    api.get('/agents/types'),
  
  getTypesDetailed: () =>
    api.get('/agents/types/detailed'),
  
  getStatus: (sessionId: string) =>
    api.get(`/agents/${sessionId}/status`),
}

export const runtimeAPI = {
  executeCode: (sessionId: string, data: {
    code: string
    language?: string
    timeout?: number
  }) => api.post(`/runtime/${sessionId}/execute`, data),
  
  writeFile: (sessionId: string, data: {
    filepath: string
    content: string
  }) => api.post(`/runtime/${sessionId}/files`, data),
  
  readFile: (sessionId: string, filepath: string) =>
    api.get(`/runtime/${sessionId}/files/${filepath}`),
  
  listFiles: (sessionId: string, directory?: string) =>
    api.get(`/runtime/${sessionId}/files`, { params: { directory } }),
  
  uploadFile: (sessionId: string, file: File, filepath: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('filepath', filepath)
    return api.post(`/runtime/${sessionId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  
  getWorkspaceInfo: (sessionId: string) =>
    api.get(`/runtime/${sessionId}/workspace`),
}

export default api
