import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

export interface Session {
  id: string
  title: string
  description?: string
  status: 'active' | 'paused' | 'completed' | 'error'
  llm_provider: string
  llm_model: string
  temperature: string
  max_tokens: number
  workspace_path?: string
  git_repo?: string
  branch: string
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface Conversation {
  id: string
  session_id: string
  title: string
  status: 'active' | 'completed' | 'error'
  agent_type: string
  agent_config: Record<string, any>
  metadata: Record<string, any>
  messages: Message[]
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  message_type: 'text' | 'code' | 'image' | 'file'
  tokens_used: number
  execution_time?: string
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface SessionState {
  // Current session
  currentSession: Session | null
  setCurrentSession: (session: Session | null) => void
  
  // Sessions list
  sessions: Session[]
  setSessions: (sessions: Session[]) => void
  addSession: (session: Session) => void
  updateSession: (sessionId: string, updates: Partial<Session>) => void
  removeSession: (sessionId: string) => void
  
  // Current conversation
  currentConversation: Conversation | null
  setCurrentConversation: (conversation: Conversation | null) => void
  
  // Conversations
  conversations: Record<string, Conversation[]>
  setConversations: (sessionId: string, conversations: Conversation[]) => void
  addConversation: (conversation: Conversation) => void
  updateConversation: (conversationId: string, updates: Partial<Conversation>) => void
  
  // Messages
  addMessage: (message: Message) => void
  updateMessage: (messageId: string, updates: Partial<Message>) => void
  
  // Loading states
  isLoading: boolean
  setLoading: (loading: boolean) => void
  
  // WebSocket connection
  wsConnection: WebSocket | null
  setWsConnection: (ws: WebSocket | null) => void
  
  // Agent status
  agentStatus: 'idle' | 'thinking' | 'responding' | 'executing' | 'error'
  setAgentStatus: (status: SessionState['agentStatus']) => void
  
  // Current response being streamed
  currentResponse: string
  setCurrentResponse: (response: string) => void
  addToCurrentResponse: (chunk: string) => void
  clearCurrentResponse: () => void
}

export const useSessionStore = create<SessionState>()(
  subscribeWithSelector((set, get) => ({
    // Current session
    currentSession: null,
    setCurrentSession: (session) => set({ currentSession: session }),
    
    // Sessions list
    sessions: [],
    setSessions: (sessions) => set({ sessions }),
    addSession: (session) => set((state) => ({ 
      sessions: [session, ...state.sessions] 
    })),
    updateSession: (sessionId, updates) => set((state) => ({
      sessions: state.sessions.map(s => 
        s.id === sessionId ? { ...s, ...updates } : s
      ),
      currentSession: state.currentSession?.id === sessionId 
        ? { ...state.currentSession, ...updates }
        : state.currentSession
    })),
    removeSession: (sessionId) => set((state) => ({
      sessions: state.sessions.filter(s => s.id !== sessionId),
      currentSession: state.currentSession?.id === sessionId 
        ? null 
        : state.currentSession
    })),
    
    // Current conversation
    currentConversation: null,
    setCurrentConversation: (conversation) => set({ currentConversation: conversation }),
    
    // Conversations
    conversations: {},
    setConversations: (sessionId, conversations) => set((state) => ({
      conversations: { ...state.conversations, [sessionId]: conversations }
    })),
    addConversation: (conversation) => set((state) => ({
      conversations: {
        ...state.conversations,
        [conversation.session_id]: [
          conversation,
          ...(state.conversations[conversation.session_id] || [])
        ]
      }
    })),
    updateConversation: (conversationId, updates) => set((state) => {
      const newConversations = { ...state.conversations }
      for (const sessionId in newConversations) {
        newConversations[sessionId] = newConversations[sessionId].map(c =>
          c.id === conversationId ? { ...c, ...updates } : c
        )
      }
      return {
        conversations: newConversations,
        currentConversation: state.currentConversation?.id === conversationId
          ? { ...state.currentConversation, ...updates }
          : state.currentConversation
      }
    }),
    
    // Messages
    addMessage: (message) => set((state) => {
      const newConversations = { ...state.conversations }
      for (const sessionId in newConversations) {
        newConversations[sessionId] = newConversations[sessionId].map(c =>
          c.id === message.conversation_id
            ? { ...c, messages: [...c.messages, message] }
            : c
        )
      }
      return {
        conversations: newConversations,
        currentConversation: state.currentConversation?.id === message.conversation_id
          ? { ...state.currentConversation, messages: [...state.currentConversation.messages, message] }
          : state.currentConversation
      }
    }),
    updateMessage: (messageId, updates) => set((state) => {
      const newConversations = { ...state.conversations }
      for (const sessionId in newConversations) {
        newConversations[sessionId] = newConversations[sessionId].map(c => ({
          ...c,
          messages: c.messages.map(m =>
            m.id === messageId ? { ...m, ...updates } : m
          )
        }))
      }
      return {
        conversations: newConversations,
        currentConversation: state.currentConversation ? {
          ...state.currentConversation,
          messages: state.currentConversation.messages.map(m =>
            m.id === messageId ? { ...m, ...updates } : m
          )
        } : null
      }
    }),
    
    // Loading states
    isLoading: false,
    setLoading: (loading) => set({ isLoading: loading }),
    
    // WebSocket connection
    wsConnection: null,
    setWsConnection: (ws) => set({ wsConnection: ws }),
    
    // Agent status
    agentStatus: 'idle',
    setAgentStatus: (status) => set({ agentStatus: status }),
    
    // Current response being streamed
    currentResponse: '',
    setCurrentResponse: (response) => set({ currentResponse: response }),
    addToCurrentResponse: (chunk) => set((state) => ({ 
      currentResponse: state.currentResponse + chunk 
    })),
    clearCurrentResponse: () => set({ currentResponse: '' }),
  }))
)
