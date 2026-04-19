import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { clearData, createSession, deleteHistoryItem, deletePreference, deleteSession, getProfile, getSessionMessages, getSettings, listHistory, listPreferences, listSessions, patchProfile, patchSession, patchSettings } from './api'
import type { ChatMessage, HistoryItem, Mode, Preference, Session, Settings, ToolProgress, UserProfile } from './types'
import './App.css'

const MODES: Mode[] = ['general', 'shopping', 'diet', 'fitness', 'lifestyle']
const MODE_LABELS: Record<Mode, string> = {
  general: 'General',
  shopping: 'Shopping',
  diet: 'Diet',
  fitness: 'Fitness',
  lifestyle: 'Lifestyle',
}

// ── Settings page ────────────────────────────────────────────────────────────

const DECAY_LABELS: Record<string, string> = {
  goals: 'Goals (days)',
  fitness_level: 'Fitness level (days)',
  dietary_approach: 'Dietary approach (days)',
  body_metrics: 'Body metrics (days)',
  taste_lifestyle: 'Taste & lifestyle (days)',
}

const DECAY_DEFAULTS: Record<string, number> = {
  goals: 60,
  fitness_level: 90,
  dietary_approach: 90,
  body_metrics: 180,
  taste_lifestyle: 365,
}

const DEFAULT_SETTINGS: Settings = {
  follow_up_cadence: 'off',
  proactive_surfacing: 'false',
  max_tool_calls_per_turn: 6,
  decay_thresholds: {},
}

function SettingsPage({ onBack }: { onBack: () => void }) {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  const [confirmClear, setConfirmClear] = useState(false)
  const [decayDraft, setDecayDraft] = useState<Record<string, number>>(DECAY_DEFAULTS)
  const [settingsLoaded, setSettingsLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSettings().then(s => {
      setSettings(s)
      const fromServer = s.decay_thresholds ?? {}
      setDecayDraft({ ...DECAY_DEFAULTS, ...fromServer })
      setSettingsLoaded(true)
    }).catch(() => setError('Failed to load settings — try refreshing'))
  }, [])

  async function save(patch: Partial<Settings>) {
    const updated = await patchSettings(patch)
    setSettings(updated)
  }

  async function saveDecay() {
    const updated = await patchSettings({ decay_thresholds: decayDraft })
    setSettings(updated)
    const fromServer = updated.decay_thresholds ?? {}
    setDecayDraft({ ...DECAY_DEFAULTS, ...fromServer })
  }

  async function handleClearData() {
    await clearData()
    onBack()
  }

  if (error) return <div className="settings-page"><button className="back-btn" onClick={onBack}>← Back</button><p className="page-error">{error}</p></div>

  return (
    <div className="settings-page">
      <button className="back-btn" onClick={onBack}>← Back</button>
      <h1>Settings</h1>

      <section>
        <h2>Notifications</h2>
        <label>
          Follow-up cadence
          <select
            value={String(settings.follow_up_cadence ?? 'off')}
            onChange={e => save({ follow_up_cadence: e.target.value })}
          >
            <option value="off">Off</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
      </section>

      <section>
        <h2>Proactive surfacing</h2>
        <label>
          <input
            type="checkbox"
            checked={settings.proactive_surfacing === 'true'}
            onChange={e => save({ proactive_surfacing: (String(e.target.checked) as 'true' | 'false') })}
          />
          Suggest relevant information proactively
        </label>
      </section>

      <section>
        <h2>Profile decay thresholds</h2>
        {Object.keys(DECAY_LABELS).map(key => (
          <label key={key}>
            {DECAY_LABELS[key]}
            <input
              type="number"
              value={decayDraft[key] ?? DECAY_DEFAULTS[key]}
              onChange={e => setDecayDraft(prev => ({ ...prev, [key]: Number(e.target.value) }))}
            />
          </label>
        ))}
        <button onClick={saveDecay} disabled={!settingsLoaded}>Save</button>
      </section>

      <section>
        <h2>Data</h2>
        {confirmClear ? (
          <div className="confirm-modal">
            <p>This will permanently delete all sessions, history, profile, and preferences. Cannot be undone.</p>
            <button onClick={handleClearData}>Confirm</button>
            <button onClick={() => setConfirmClear(false)}>Cancel</button>
          </div>
        ) : (
          <button className="danger-btn" onClick={() => setConfirmClear(true)}>Clear all data</button>
        )}
      </section>
    </div>
  )
}

// ── Information page ──────────────────────────────────────────────────────

type DecayThresholds = Record<string, number>

const FIELD_DECAY_CATEGORY: Record<string, keyof DecayThresholds> = {
  fitness_goal: 'goals', dietary_goal: 'goals', lifestyle_focus: 'goals',
  fitness_level: 'fitness_level',
  dietary_approach: 'dietary_approach',
  height_cm: 'body_metrics', weight_kg: 'body_metrics', build: 'body_metrics',
  aesthetic_style: 'taste_lifestyle', brand_rejections: 'taste_lifestyle',
  climate: 'taste_lifestyle', activity_level: 'taste_lifestyle',
  living_situation: 'taste_lifestyle', country: 'taste_lifestyle',
  budget_psychology: 'taste_lifestyle', injury_history: 'taste_lifestyle',
  dietary_restrictions: 'taste_lifestyle', dietary_preferences: 'taste_lifestyle',
}

const FIELD_ENUMS: Record<string, string[]> = {
  build: ['lean', 'athletic', 'average', 'heavy'],
  fitness_level: ['sedentary', 'beginner', 'intermediate', 'advanced'],
  dietary_approach: ['keto', 'vegan', 'omnivore', 'carnivore', 'flexible'],
  aesthetic_style: ['minimal', 'technical', 'classic', 'mixed'],
  budget_psychology: ['buy_once_buy_right', 'good_enough', 'context_dependent'],
  activity_level: ['low', 'moderate', 'high'],
  living_situation: ['urban', 'suburban', 'rural'],
}

const FIELD_LABELS: Record<string, string> = {
  height_cm: 'Height (cm)', weight_kg: 'Weight (kg)', build: 'Build',
  fitness_level: 'Fitness level', injury_history: 'Injury history',
  dietary_restrictions: 'Dietary restrictions', dietary_preferences: 'Dietary preferences',
  dietary_approach: 'Dietary approach', aesthetic_style: 'Aesthetic style',
  brand_rejections: 'Brand rejections', climate: 'Climate', country: 'Country',
  activity_level: 'Activity level', living_situation: 'Living situation',
  budget_psychology: 'Budget psychology', fitness_goal: 'Fitness goal',
  dietary_goal: 'Dietary goal', lifestyle_focus: 'Lifestyle focus',
}

const INFO_SECTIONS: { title: string; fields: string[] }[] = [
  { title: 'Identity & Body', fields: ['height_cm', 'weight_kg', 'build', 'fitness_level', 'injury_history'] },
  { title: 'Diet', fields: ['dietary_restrictions', 'dietary_preferences', 'dietary_approach'] },
  { title: 'Style & Taste', fields: ['aesthetic_style', 'brand_rejections'] },
  { title: 'Lifestyle', fields: ['climate', 'country', 'activity_level', 'living_situation'] },
  { title: 'Budget', fields: ['budget_psychology'] },
  { title: 'Goals', fields: ['fitness_goal', 'dietary_goal', 'lifestyle_focus'] },
]

function isStale(field: string, timestamps: Record<string, string>, thresholds: DecayThresholds): boolean {
  const ts = timestamps[field]
  if (!ts) return false
  const category = FIELD_DECAY_CATEGORY[field]
  if (!category) return false
  const days = thresholds[category]
  if (!days) return false
  return Date.now() - Date.parse(ts) > days * 86400000
}

function daysSince(iso: string): number {
  return Math.floor((Date.now() - Date.parse(iso)) / 86400000)
}

function ProfileField({
  field, value, timestamp, stale, onSave,
}: {
  field: string
  value: string | null
  timestamp: string | null
  stale: boolean
  onSave: (field: string, value: string) => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value ?? '')
  const enumOptions = FIELD_ENUMS[field]

  async function save() {
    if (draft.trim() === (value ?? '')) { setEditing(false); return }
    await onSave(field, draft.trim())
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="info-field editing">
        <span className="info-field-label">{FIELD_LABELS[field]}</span>
        {enumOptions ? (
          <select
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onBlur={save}
            autoFocus
          >
            <option value="">— not set —</option>
            {enumOptions.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : (
          <input
            type={field === 'height_cm' || field === 'weight_kg' ? 'number' : 'text'}
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onBlur={save}
            onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false) }}
            autoFocus
          />
        )}
      </div>
    )
  }

  return (
    <div className="info-field" onClick={() => { setDraft(value ?? ''); setEditing(true) }}>
      <span className="info-field-label">{FIELD_LABELS[field]}</span>
      <span className={`info-field-value${value ? '' : ' unset'}`}>{value ?? 'Not set'}</span>
      <span className="info-field-meta">
        {stale && <span className="stale-dot" title={`Last set ${daysSince(timestamp!)} days ago`}>●</span>}
        {timestamp && <span className="info-field-date">{timestamp.slice(0, 10)}</span>}
      </span>
    </div>
  )
}

function InformationPage({ onBack, onGoHistory }: { onBack: () => void; onGoHistory: () => void }) {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [prefs, setPrefs] = useState<Preference[]>([])
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [thresholds, setThresholds] = useState<DecayThresholds>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getProfile(), listPreferences(), listHistory(), getSettings()]).then(
      ([p, pr, hPage, s]) => {
        setProfile(p)
        setPrefs(pr)
        setHistory(hPage.items)
        setThresholds(s.decay_thresholds ?? {})
      }
    ).catch(() => setError('Failed to load — try refreshing'))
  }, [])

  async function saveField(field: string, value: string) {
    const updated = await patchProfile({ [field]: value || null })
    setProfile(updated)
  }

  async function handleDeletePref(id: string) {
    await deletePreference(id)
    setPrefs(prev => prev.filter(p => p.id !== id))
  }

  const timestamps: Record<string, string> = profile?.field_timestamps
    ? JSON.parse(profile.field_timestamps)
    : {}

  // History summary: count per domain per status
  const historySummary: Record<string, Record<string, number>> = {}
  for (const item of history) {
    if (!historySummary[item.domain]) historySummary[item.domain] = {}
    historySummary[item.domain][item.status] = (historySummary[item.domain][item.status] ?? 0) + 1
  }

  if (error) return <div className="info-page"><button className="back-btn" onClick={onBack}>← Back</button><p className="page-error">{error}</p></div>
  if (!profile) return <div className="info-page"><button className="back-btn" onClick={onBack}>← Back</button><p>Loading…</p></div>

  return (
    <div className="info-page">
      <button className="back-btn" onClick={onBack}>← Back</button>
      <h1>Information</h1>

      {INFO_SECTIONS.map(section => (
        <section key={section.title} className="info-section">
          <h2>{section.title}</h2>
          {section.fields.map(field => (
            <ProfileField
              key={field}
              field={field}
              value={profile[field] as string | null}
              timestamp={timestamps[field] ?? null}
              stale={isStale(field, timestamps, thresholds)}
              onSave={saveField}
            />
          ))}
        </section>
      ))}

      <section className="info-section">
        <h2>Learned Preferences</h2>
        {prefs.length === 0
          ? <p className="info-empty">No learned preferences yet.</p>
          : prefs.map(pref => (
            <div key={pref.id} className="info-pref-row">
              <span className="info-pref-dim">{pref.dimension}</span>
              <span className="info-pref-value">{pref.value}</span>
              {pref.reason && <span className="info-pref-reason">{pref.reason}</span>}
              <span className={`info-pref-source source-${pref.source}`}>{pref.source}</span>
              <button className="del-btn" onClick={() => handleDeletePref(pref.id)}>×</button>
            </div>
          ))
        }
      </section>

      <section className="info-section">
        <h2>History Summary</h2>
        {Object.keys(historySummary).length === 0
          ? <p className="info-empty">No history yet.</p>
          : Object.entries(historySummary).map(([domain, counts]) => (
            <div key={domain} className="info-history-row">
              <span className="info-history-domain">{domain}</span>
              <span className="info-history-counts">
                {Object.entries(counts).map(([status, n]) => `${n} ${status}`).join(', ')}
              </span>
            </div>
          ))
        }
        {history.length > 0 && (
          <button className="info-history-link" onClick={onGoHistory}>View full history →</button>
        )}
      </section>
    </div>
  )
}

// ── History page ─────────────────────────────────────────────────────────

const DOMAINS = ['', 'shopping', 'diet', 'fitness', 'lifestyle']
const STATUSES = ['', 'recommended', 'bought', 'tried', 'rated', 'skipped']

function HistoryPage({ onBack }: { onBack: () => void }) {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [domain, setDomain] = useState('')
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)
  const LIMIT = 50

  useEffect(() => {
    setItems([])
    setOffset(0)
    setTotal(0)
    listHistory(domain || undefined, status || undefined, LIMIT, 0)
      .then(page => { setItems(page.items); setTotal(page.total) })
      .catch(() => setError('Failed to load — try refreshing'))
  }, [domain, status])

  async function loadMore() {
    const nextOffset = offset + LIMIT
    const page = await listHistory(domain || undefined, status || undefined, LIMIT, nextOffset)
    setItems(prev => [...prev, ...page.items])
    setOffset(nextOffset)
    setTotal(page.total)
  }

  async function handleDelete(id: string) {
    await deleteHistoryItem(id)
    setItems(prev => prev.filter(i => i.id !== id))
    setTotal(prev => prev - 1)
  }

  if (error) return <div className="history-page"><button className="back-btn" onClick={onBack}>← Back</button><p className="page-error">{error}</p></div>

  return (
    <div className="history-page">
      <button className="back-btn" onClick={onBack}>← Back</button>
      <h1>History</h1>
      <div className="history-filters">
        <label>
          Domain
          <select value={domain} onChange={e => setDomain(e.target.value)}>
            {DOMAINS.map(d => <option key={d} value={d}>{d || 'All'}</option>)}
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={e => setStatus(e.target.value)}>
            {STATUSES.map(s => <option key={s} value={s}>{s || 'All'}</option>)}
          </select>
        </label>
      </div>
      {items.length === 0
        ? <p className="history-empty">No items found.</p>
        : (
          <table className="history-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Category</th>
                <th>Domain</th>
                <th>Status</th>
                <th>Rating</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.id}>
                  <td>{item.item_name}{item.notes ? <span className="history-notes" title={item.notes}> *</span> : null}</td>
                  <td>{item.category}</td>
                  <td>{item.domain}</td>
                  <td>{item.status}</td>
                  <td>{item.rating != null ? `${item.rating}/5` : '—'}</td>
                  <td>{item.created_at.slice(0, 10)}</td>
                  <td><button className="del-btn" onClick={() => handleDelete(item.id)}>×</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      }
      {total > offset + LIMIT && (
        <button className="load-more-btn" onClick={loadMore}>Load more</button>
      )}
    </div>
  )
}

// ── Chat page ────────────────────────────────────────────────────────────────

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [toolProgress, setToolProgress] = useState<ToolProgress[]>([])
  const [toolsExpanded, setToolsExpanded] = useState(false)
  const [page, setPage] = useState<'chat' | 'settings' | 'info' | 'history'>('chat')
  const [mode, setMode] = useState<Mode>('general')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    listSessions().then(setSessions)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function newChat(): Promise<string> {
    const session = await createSession()
    setSessions(prev => [session, ...prev])
    setActiveId(session.id)
    setMessages(
      session.session_start_prompt
        ? [{ id: 'init', role: 'assistant', content: session.session_start_prompt }]
        : []
    )
    setToolProgress([])
    // Preserve current mode; patch the session if it differs from the default 'general'
    if (mode !== 'general') {
      await patchSession(session.id, { mode })
    }
    setPage('chat')
    return session.id
  }

  async function selectSession(id: string) {
    setActiveId(id)
    setPage('chat')
    const msgs = await getSessionMessages(id)
    setMessages(
      msgs
        .filter((m: { role: string }) => m.role === 'user' || m.role === 'assistant')
        .map((m: { id: string; role: string; content: string }) => ({
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
        }))
    )
    const sess = sessions.find(s => s.id === id)
    if (sess) setMode(sess.mode as Mode)
    setToolProgress([])
  }

  async function loadOlderMessages(sessionId: string) {
    if (messages.length === 0) return
    const oldest = messages[0]
    const older = await getSessionMessages(sessionId, 100, oldest.id)
    const mapped = older
      .filter((m: { role: string }) => m.role === 'user' || m.role === 'assistant')
      .map((m: { id: string; role: string; content: string }) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
      }))
    setMessages(prev => [...mapped, ...prev])
  }

  async function removeSession(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    await deleteSession(id)
    setSessions(prev => prev.filter(s => s.id !== id))
    if (activeId === id) {
      setActiveId(null)
      setMessages([])
    }
  }

  async function changeMode(newMode: Mode) {
    setMode(newMode)
    if (activeId) {
      await patchSession(activeId, { mode: newMode })
      setSessions(prev => prev.map(s => s.id === activeId ? { ...s, mode: newMode } : s))
    }
  }

  async function sendMessage() {
    if (!input.trim() || streaming) return
    const sessionId = activeId ?? await newChat()

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setStreaming(true)
    setToolProgress([])

    const assistantId = `a-${Date.now()}`
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', streaming: true }])

    const resp = await fetch(`/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: userMsg.content }),
    })

    if (!resp.body) {
      setMessages(prev => prev.filter(m => m.id !== assistantId))
      setMessages(prev => [
        ...prev,
        { id: assistantId, role: 'assistant', content: 'Connection failed — try again.' },
      ])
      setStreaming(false)
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          let payload: Record<string, unknown>
          try {
            payload = JSON.parse(line.slice(5).trim()) as Record<string, unknown>
          } catch (e) {
            if (e instanceof SyntaxError) { console.warn('SSE parse error', line); continue }
            throw e
          }
          if (currentEvent === 'text_delta') {
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId ? { ...m, content: m.content + payload.delta } : m
              )
            )
          } else if (currentEvent === 'tool_start') {
            setToolProgress(prev => [...prev, { tool: payload.tool, status: 'running', description: payload.description }])
          } else if (currentEvent === 'tool_end') {
            setToolProgress(prev =>
              prev.map(t => t.tool === payload.tool ? { ...t, status: 'done', summary: payload.result_summary } : t)
            )
          } else if (currentEvent === 'tool_error') {
            setToolProgress(prev =>
              prev.map(t => t.tool === payload.tool ? { ...t, status: 'error', error: payload.error } : t)
            )
          } else if (currentEvent === 'done') {
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, streaming: false } : m))
            setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title: payload.title } : s))
          } else if (currentEvent === 'error') {
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: 'Could not reach Claude. Check your API key.', streaming: false }
                  : m
              )
            )
          }
        }
      }
    }

    setStreaming(false)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    } else if (e.key === 'Escape') {
      setInput('')
    }
  }

  if (page === 'settings') {
    return <SettingsPage onBack={() => setPage('chat')} />
  }

  if (page === 'info') {
    return <InformationPage onBack={() => setPage('chat')} onGoHistory={() => setPage('history')} />
  }

  if (page === 'history') {
    return <HistoryPage onBack={() => setPage('chat')} />
  }

  return (
    <div className="layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <button className="new-chat-btn" onClick={newChat}>+ New chat</button>
        <nav className="session-list">
          {sessions.map(s => (
            <div
              key={s.id}
              className={`session-item${s.id === activeId ? ' active' : ''}`}
              onClick={() => selectSession(s.id)}
            >
              <span className="session-title">{s.title ?? s.preview ?? 'New chat'}</span>
              <button className="del-btn" onClick={e => removeSession(s.id, e)}>×</button>
            </div>
          ))}
        </nav>
        <div className="sidebar-links">
          <button onClick={() => setPage('info')}>Information</button>
          <button onClick={() => setPage('history')}>History</button>
          <button onClick={() => setPage('settings')}>Settings</button>
        </div>
      </aside>

      {/* Main */}
      <main className="chat-area">
        {/* Mode selector */}
        <header className="mode-bar">
          {MODES.map(m => (
            <button
              key={m}
              className={`mode-pill${mode === m ? ' active' : ''}`}
              onClick={() => changeMode(m)}
            >
              {MODE_LABELS[m]}
            </button>
          ))}
        </header>

        {/* Messages */}
        <div className="messages">
          {activeId && messages.length > 0 && (
            <button className="load-older-btn" onClick={() => loadOlderMessages(activeId)}>
              Load older messages
            </button>
          )}
          {messages.map(msg => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <div className="bubble">
                {msg.role === 'assistant'
                  ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || (msg.streaming ? '…' : '')}</ReactMarkdown>
                  : msg.content}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Tool progress strip */}
        {toolProgress.length > 0 && (
          <div className={`tool-strip${toolsExpanded ? ' expanded' : ''}`} onClick={() => setToolsExpanded(p => !p)}>
            {toolsExpanded
              ? toolProgress.map((t, i) => (
                  <div key={i} className={`tool-line status-${t.status}`}>
                    {t.status === 'error'
                      ? `⚠ ${t.tool} failed — ${t.error}`
                      : t.status === 'done'
                      ? `✓ ${t.tool}: ${t.summary}`
                      : `⋯ ${t.description ?? t.tool}`}
                  </div>
                ))
              : <span className="tool-summary">{toolProgress.length} tool{toolProgress.length > 1 ? 's' : ''} used — click to expand</span>
            }
          </div>
        )}

        {/* Input */}
        <div className="input-bar">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message Weles… (Enter to send, Shift+Enter for newline)"
            rows={1}
            disabled={streaming}
          />
          <button onClick={sendMessage} disabled={streaming || !input.trim()}>Send</button>
        </div>
      </main>
    </div>
  )
}
