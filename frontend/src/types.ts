export type Mode = 'general' | 'shopping' | 'diet' | 'fitness' | 'lifestyle'

export interface Session {
  id: string
  title: string | null
  mode: Mode
  created_at: string
  preview: string | null
  session_start_prompt?: string | null
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ToolProgress {
  tool: string
  status: 'running' | 'done' | 'error'
  description?: string
  summary?: string
  error?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}
