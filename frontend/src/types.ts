export type Mode = 'general' | 'shopping' | 'diet' | 'fitness' | 'lifestyle'

export interface Settings {
  follow_up_cadence: 'weekly' | 'monthly' | 'off'
  proactive_surfacing: 'true' | 'false'
  max_tool_calls_per_turn: number
  decay_thresholds: Record<string, number>
}

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

export interface UserProfile {
  [key: string]: unknown
  id: number | null
  height_cm: number | null
  weight_kg: number | null
  build: string | null
  fitness_level: string | null
  injury_history: string | null
  dietary_restrictions: string | null
  dietary_preferences: string | null
  dietary_approach: string | null
  aesthetic_style: string | null
  brand_rejections: string | null
  climate: string | null
  activity_level: string | null
  living_situation: string | null
  country: string | null
  budget_psychology: string | null
  fitness_goal: string | null
  dietary_goal: string | null
  lifestyle_focus: string | null
  first_session_at: string | null
  field_timestamps: string | null
}

export interface Preference {
  id: string
  dimension: string
  value: string
  reason: string | null
  source: string
  created_at: string | null
}

export interface HistoryItem {
  id: string
  item_name: string
  category: string
  domain: string
  status: string
  rating: number | null
  notes: string | null
  follow_up_due_at: string | null
  check_in_due_at: string | null
  created_at: string
}
