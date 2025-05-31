import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AppState {
  // Theme
  theme: 'dark' | 'light'
  setTheme: (theme: 'dark' | 'light') => void

  // Session management
  currentSessionId: string | null
  setCurrentSessionId: (sessionId: string | null) => void

  // UI state
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
  
  panelSizes: {
    sidebar: number
    editor: number
    terminal: number
  }
  setPanelSizes: (sizes: Partial<AppState['panelSizes']>) => void

  // LLM settings
  llmProvider: string
  llmModel: string
  setLLMSettings: (provider: string, model: string) => void

  // Agent settings
  selectedAgent: string
  setSelectedAgent: (agent: string) => void

  // Connection status
  connected: boolean
  setConnected: (connected: boolean) => void

  // Loading states
  isLoading: boolean
  setLoading: (loading: boolean) => void

  // Error handling
  error: string | null
  setError: (error: string | null) => void
  clearError: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Theme
      theme: 'dark',
      setTheme: (theme) => set({ theme }),

      // Session management
      currentSessionId: null,
      setCurrentSessionId: (sessionId) => set({ currentSessionId: sessionId }),

      // UI state
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      panelSizes: {
        sidebar: 20,
        editor: 50,
        terminal: 30,
      },
      setPanelSizes: (sizes) => set((state) => ({
        panelSizes: { ...state.panelSizes, ...sizes }
      })),

      // LLM settings
      llmProvider: 'openai',
      llmModel: 'gpt-4',
      setLLMSettings: (provider, model) => set({ 
        llmProvider: provider, 
        llmModel: model 
      }),

      // Agent settings
      selectedAgent: 'codeact',
      setSelectedAgent: (agent) => set({ selectedAgent: agent }),

      // Connection status
      connected: false,
      setConnected: (connected) => set({ connected }),

      // Loading states
      isLoading: false,
      setLoading: (loading) => set({ isLoading: loading }),

      // Error handling
      error: null,
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'openreplica-app-store',
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        panelSizes: state.panelSizes,
        llmProvider: state.llmProvider,
        llmModel: state.llmModel,
        selectedAgent: state.selectedAgent,
      }),
    }
  )
)

// Convenience hooks for common use cases
export const useTheme = () => useAppStore((state) => ({
  theme: state.theme,
  setTheme: state.setTheme,
}))

export const useSession = () => useAppStore((state) => ({
  currentSessionId: state.currentSessionId,
  setCurrentSessionId: state.setCurrentSessionId,
}))

export const useUI = () => useAppStore((state) => ({
  sidebarCollapsed: state.sidebarCollapsed,
  setSidebarCollapsed: state.setSidebarCollapsed,
  panelSizes: state.panelSizes,
  setPanelSizes: state.setPanelSizes,
}))

export const useConnection = () => useAppStore((state) => ({
  connected: state.connected,
  setConnected: state.setConnected,
}))

export const useError = () => useAppStore((state) => ({
  error: state.error,
  setError: state.setError,
  clearError: state.clearError,
}))

export const useLoading = () => useAppStore((state) => ({
  isLoading: state.isLoading,
  setLoading: state.setLoading,
}))
