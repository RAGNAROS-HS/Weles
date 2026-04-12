import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { clearData, createSession, deleteHistoryItem, deleteSession, getSettings, listHistory, listSessions, patchSession, patchSettings } from './api'
import type { ChatMessage, HistoryItem, Mode, Session, ToolProgress } from './types'
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

function SettingsPage({ onBack }: { onBack: () => void }) {
  const [settings, setSettings] = useState<Record<string, unknown>>({})
  const [confirmClear, setConfirmClear] = useState(false)
  const [decayDraft, setDecayDraft] = useState<Record<string, number>>(DECAY_DEFAULTS)
  const [settingsLoaded, setSettingsLoaded] = useState(false)

  useEffect(() => {
    getSettings().then(s => {
      setSettings(s)
      const fromServer = (s.decay_thresholds as Record<string, number>) ?? {}
      setDecayDraft({ ...DECAY_DEFAULTS, ...fromServer })
      setSettingsLoaded(true)
    })
  }, [])

  async function save(patch: Record<string, unknown>) {
    const updated = await patchSettings(patch)
    setSettings(updated)
  }

  async function saveDecay() {
    const updated = await patchSettings({ decay_thresholds: decayDraft })
    setSettings(updated)
    const fromServer = (updated.decay_thresholds as Record<string, number>) ?? {}
    setDecayDraft({ ...DECAY_DEFAULTS, ...fromServer })
  }

  async function handleClearData() {
    await clearData()
    onBack()
  }

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
            checked={settings.proactive_surfacing === 'true' || settings.proactive_surfacing === true}
            onChange={e => save({ proactive_surfacing: String(e.target.checked) })}
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

// ── History page ─────────────────────────────────────────────────────────

const DOMAINS = ['', 'shopping', 'diet', 'fitness', 'lifestyle']
const STATUSES = ['', 'recommended', 'bought', 'tried', 'rated', 'skipped']

function HistoryPage({ onBack }: { onBack: () => void }) {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [domain, setDomain] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    listHistory(domain || undefined, status || undefined).then(setItems)
  }, [domain, status])

  async function handleDelete(id: string) {
    await deleteHistoryItem(id)
    setItems(prev => prev.filter(i => i.id !== id))
  }

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
    setMode('general')
    setPage('chat')
    return session.id
  }

  async function selectSession(id: string) {
    setActiveId(id)
    setPage('chat')
    const r = await fetch(`/sessions/${id}/messages`)
    const msgs = await r.json()
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
          const payload = JSON.parse(line.slice(5).trim())
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
