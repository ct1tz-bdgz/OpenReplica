import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AppState {
  // Theme
  theme: 'light' | 'dark'
  toggleTheme: () => void
  
  // User preferences
  preferences: {
    defaultLLMProvider: string
    defaultLLMModel: string
    autoSave: boolean
    showLineNumbers: boolean
    fontSize: number
    tabSize: number
  }
  updatePreferences: (preferences: Partial<AppState['preferences']>) => void
  
  // UI state
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  
  // Connection status
  isConnected: boolean
  setConnectionStatus: (connected: boolean) => void
  
  // Initialization
  isInitialized: boolean
  initializeApp: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Theme
      theme: 'light',
      toggleTheme: () => set((state) => ({ 
        theme: state.theme === 'light' ? 'dark' : 'light' 
      })),
      
      // User preferences
      preferences: {
        defaultLLMProvider: 'openai',
        defaultLLMModel: 'gpt-4',
        autoSave: true,
        showLineNumbers: true,
        fontSize: 14,
        tabSize: 2,
      },
      updatePreferences: (newPreferences) => set((state) => ({
        preferences: { ...state.preferences, ...newPreferences }
      })),
      
      // UI state
      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      
      // Connection status
      isConnected: false,
      setConnectionStatus: (connected) => set({ isConnected: connected }),
      
      // Initialization
      isInitialized: false,
      initializeApp: () => {
        // Detect system theme preference
        if (!get().isInitialized) {
          const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
          set({ theme: systemTheme, isInitialized: true })
        }
      },
    }),
    {
      name: 'openreplica-app-store',
      partialize: (state) => ({
        theme: state.theme,
        preferences: state.preferences,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
)
