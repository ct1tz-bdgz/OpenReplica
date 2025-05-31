// API Types
export interface Session {
  session_id: string
  workspace_name: string
  agent_type: string
  llm_provider: string
  llm_model: string
  status: string
  created_at: string
  last_activity: string
  message_count: number
}

export interface Agent {
  agent_id: string
  agent_type: string
  state: string
  stats: Record<string, any>
}

export interface FileInfo {
  name: string
  path: string
  size: number
  modified: number
  is_directory: boolean
  mime_type?: string
}

export interface DirectoryListing {
  path: string
  files: FileInfo[]
  total_files: number
  total_size: number
}

export interface FileContent {
  path: string
  content: string
  encoding: string
  size: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  event_type?: string
}

// Event Types
export interface Event {
  id: string
  timestamp: string
  event_type: string
  source?: string
  session_id?: string
}

export interface Action extends Event {
  action_type: string
  thought?: string
}

export interface Observation extends Event {
  observation_type: string
  content: string
  success: boolean
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
  session_id?: string
}

export interface ConnectionStatus {
  connected: boolean
  session_id?: string
  error?: string
}

// UI Types
export interface PanelSizes {
  sidebar: number
  editor: number
  terminal: number
}

export interface TabItem {
  id: string
  title: string
  type: 'file' | 'terminal' | 'chat'
  path?: string
  content?: string
  modified?: boolean
  active?: boolean
}

export interface ContextMenuItem {
  id: string
  label: string
  icon?: string
  action: () => void
  disabled?: boolean
  separator?: boolean
}

// Agent Types
export type AgentType = 'codeact' | 'browsing' | 'dummy'

export type AgentState = 'idle' | 'thinking' | 'acting' | 'waiting' | 'finished' | 'error'

// LLM Types
export interface LLMProvider {
  id: string
  name: string
  models: string[]
  apiKeyRequired: boolean
}

export interface LLMSettings {
  provider: string
  model: string
  temperature: number
  maxTokens: number
}

// Terminal Types
export interface TerminalSession {
  id: string
  pid: number
  title: string
  cwd: string
  active: boolean
}

// Editor Types
export interface EditorTheme {
  name: string
  type: 'light' | 'dark'
}

export interface EditorSettings {
  theme: string
  fontSize: number
  tabSize: number
  wordWrap: boolean
  minimap: boolean
  lineNumbers: boolean
}

// File Explorer Types
export interface FileTreeNode {
  id: string
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileTreeNode[]
  expanded?: boolean
  selected?: boolean
  modified?: boolean
}

// Chat Types
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  status?: 'sending' | 'sent' | 'error'
}

export interface ChatSession {
  id: string
  messages: ChatMessage[]
  agent_type: string
  created_at: Date
  updated_at: Date
}

// API Request/Response Types
export interface CreateSessionRequest {
  workspace_name?: string
  agent_type: string
  llm_provider: string
  llm_model: string
}

export interface CreateAgentRequest {
  agent_type: string
  config: Record<string, any>
  session_id: string
}

export interface WriteFileRequest {
  path: string
  content: string
  encoding?: string
}

// Error Types
export interface APIError {
  message: string
  code?: string
  details?: any
}

export interface ValidationError {
  field: string
  message: string
}

// Utility Types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error'

export type Theme = 'light' | 'dark'

export type NotificationType = 'info' | 'success' | 'warning' | 'error'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  duration?: number
  persistent?: boolean
}

// Search Types
export interface SearchResult {
  file: string
  line: number
  column: number
  content: string
  match: string
}

export interface SearchOptions {
  query: string
  caseSensitive: boolean
  wholeWord: boolean
  regex: boolean
  includeFiles: string[]
  excludeFiles: string[]
}
