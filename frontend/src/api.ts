import type { HistoryItem, Message, Mode, Preference, Session, Settings, UserProfile } from './types'

function checkOk(r: Response): Response {
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r
}

export async function createSession(): Promise<Session> {
  const r = await fetch('/sessions', { method: 'POST' })
  return checkOk(r).json()
}

export async function listSessions(search?: string): Promise<Session[]> {
  const url = search ? `/sessions?search=${encodeURIComponent(search)}` : '/sessions'
  const r = await fetch(url)
  return checkOk(r).json()
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`/sessions/${id}`, { method: 'DELETE' })
}

export async function patchSession(id: string, patch: { title?: string; mode?: Mode }): Promise<Session> {
  const r = await fetch(`/sessions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return checkOk(r).json()
}

export async function getSettings(): Promise<Settings> {
  const r = await fetch('/settings')
  return checkOk(r).json()
}

export async function patchSettings(patch: Partial<Settings>): Promise<Settings> {
  const r = await fetch('/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return checkOk(r).json()
}

export async function getProfile(): Promise<UserProfile> {
  const r = await fetch('/profile')
  return checkOk(r).json()
}

export async function patchProfile(patch: Record<string, unknown>): Promise<UserProfile> {
  const r = await fetch('/profile', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return checkOk(r).json()
}

export async function listPreferences(): Promise<Preference[]> {
  const r = await fetch('/preferences')
  return checkOk(r).json()
}

export async function deletePreference(id: string): Promise<void> {
  await fetch(`/preferences/${id}`, { method: 'DELETE' })
}

export async function clearData(): Promise<void> {
  const r = await fetch('/data', { method: 'DELETE' })
  if (!r.ok) throw new Error(`DELETE /data failed: ${r.status}`)
}

export interface HistoryPage {
  items: HistoryItem[]
  total: number
  limit: number
  offset: number
}

export async function listHistory(
  domain?: string,
  status?: string,
  limit = 50,
  offset = 0,
  search?: string,
  sort: 'newest' | 'oldest' = 'newest',
): Promise<HistoryPage> {
  const params = new URLSearchParams()
  if (domain) params.set('domain', domain)
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  params.set('sort', sort)
  params.set('limit', String(limit))
  params.set('offset', String(offset))
  const r = await fetch(`/history?${params.toString()}`)
  return checkOk(r).json()
}

export async function getSessionMessages(sessionId: string, limit = 100, beforeId?: string): Promise<Message[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (beforeId) params.set('before_id', beforeId)
  const r = await fetch(`/sessions/${sessionId}/messages?${params.toString()}`)
  return checkOk(r).json()
}

export async function deleteHistoryItem(id: string): Promise<void> {
  await fetch(`/history/${id}`, { method: 'DELETE' })
}

export type { HistoryItem, Message, Preference, Settings, UserProfile } from './types'
