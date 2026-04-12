import type { Mode, Session } from './types'

export async function createSession(): Promise<Session> {
  const r = await fetch('/sessions', { method: 'POST' })
  return r.json()
}

export async function listSessions(): Promise<Session[]> {
  const r = await fetch('/sessions')
  return r.json()
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
  return r.json()
}

export async function getSettings(): Promise<Record<string, unknown>> {
  const r = await fetch('/settings')
  return r.json()
}

export async function patchSettings(patch: Record<string, unknown>): Promise<Record<string, unknown>> {
  const r = await fetch('/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return r.json()
}

export async function clearData(): Promise<void> {
  const r = await fetch('/data', { method: 'DELETE' })
  if (!r.ok) throw new Error(`DELETE /data failed: ${r.status}`)
}

export async function listHistory(domain?: string, status?: string): Promise<HistoryItem[]> {
  const params = new URLSearchParams()
  if (domain) params.set('domain', domain)
  if (status) params.set('status', status)
  const query = params.toString()
  const r = await fetch(`/history${query ? `?${query}` : ''}`)
  return r.json()
}

export async function deleteHistoryItem(id: string): Promise<void> {
  await fetch(`/history/${id}`, { method: 'DELETE' })
}

export type { HistoryItem } from './types'
