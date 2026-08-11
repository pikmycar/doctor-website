import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight, CheckCircle2, CheckSquare, Clock3, Download, FileText, LogOut, Mail, RotateCcw, Save, Search, ShieldCheck, Square, User, XCircle } from 'lucide-react'

type Appointment = {
  id: string
  name: string
  email: string
  message: string
  slot_start: string
  slot_end: string
  created_at: string
  status: 'requested' | 'confirmed' | 'cancelled'
  notes: string
}

type Stats = {
  total: number
  by_status: Record<string, number>
  last_alert: { status?: string; created_at?: string; webhook_url?: string | null } | null
}

const fmt = (iso: string) => {
  const d = new Date(iso)
  return d.toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

const statusMeta: Record<string, { label: string; className: string }> = {
  requested: { label: 'Requested', className: 'pill pill-amber' },
  confirmed: { label: 'Confirmed', className: 'pill pill-green' },
  cancelled: { label: 'Cancelled', className: 'pill pill-grey' },
}

function LoginPanel({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setSubmitting(true); setErr('')
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: 'Login failed.' }))
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Login failed.')
      }
      onLoggedIn()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Login failed.')
    } finally { setSubmitting(false) }
  }

  return (
    <div className="admin-login" data-testid="admin-login">
      <motion.div className="admin-login-card"
        initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5 }}>
        <div className="admin-login-brand"><span className="brand-mark">M</span>Meridian · admin</div>
        <h1>Welcome back.</h1>
        <p className="dialog-copy">Sign in to review incoming appointments.</p>
        <form onSubmit={submit}>
          <label>Email<input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="admin-email-input" placeholder="admin@meridianmedical.com" /></label>
          <label>Password<input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="admin-password-input" placeholder="••••••••" /></label>
          {err && <p className="dialog-error" role="alert" data-testid="admin-login-error">{err}</p>}
          <button className="button button-dark full" type="submit" disabled={submitting} data-testid="admin-login-button">
            {submitting ? 'Signing in…' : 'Sign in'} <ArrowUpRight size={17} />
          </button>
        </form>
        <a className="text-link admin-back-link" href="/" data-testid="admin-back-link">← Back to site</a>
      </motion.div>
    </div>
  )
}

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [filter, setFilter] = useState<'all' | 'requested' | 'confirmed' | 'cancelled'>('all')
  const [loading, setLoading] = useState(true)
  const today = useMemo(() => new Date().toISOString().slice(0, 10), [])
  const nextMonth = useMemo(() => {
    const d = new Date(); d.setMonth(d.getMonth() + 1); return d.toISOString().slice(0, 10)
  }, [])
  const [dateFrom, setDateFrom] = useState(today)
  const [dateTo, setDateTo] = useState(nextMonth)
  const [exporting, setExporting] = useState(false)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [bulkBusy, setBulkBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [aRes, sRes] = await Promise.all([
        fetch('/api/admin/appointments', { credentials: 'include' }),
        fetch('/api/admin/stats', { credentials: 'include' }),
      ])
      if (aRes.status === 401 || sRes.status === 401) { onLogout(); return }
      const a = await aRes.json(); const s = await sRes.json()
      setAppointments(a); setStats(s)
    } finally { setLoading(false) }
  }, [onLogout])

  useEffect(() => { load() }, [load])

  const updateStatus = async (id: string, status: Appointment['status']) => {
    const prev = appointments
    setAppointments((cur) => cur.map((x) => x.id === id ? { ...x, status } : x))
    try {
      const res = await fetch(`/api/admin/appointments/${id}`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      if (!res.ok) throw new Error('Update failed')
      load()
    } catch {
      setAppointments(prev)
    }
  }

  const saveNotes = async (id: string, notes: string) => {
    const prev = appointments
    setAppointments((cur) => cur.map((x) => x.id === id ? { ...x, notes } : x))
    try {
      const res = await fetch(`/api/admin/appointments/${id}`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes }),
      })
      if (!res.ok) throw new Error('Save failed')
    } catch {
      setAppointments(prev)
      throw new Error('Save failed')
    }
  }

  const exportCsv = async () => {
    setExporting(true)
    try {
      const params = new URLSearchParams()
      if (dateFrom) params.set('date_from', dateFrom)
      if (dateTo) params.set('date_to', dateTo)
      const res = await fetch(`/api/admin/appointments.csv?${params.toString()}`, { credentials: 'include' })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `meridian-appointments-${dateFrom}_to_${dateTo}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } finally { setExporting(false) }
  }

  const signOut = async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
    onLogout()
  }

  const filtered = useMemo(() => {
    const base = filter === 'all' ? appointments : appointments.filter((a) => a.status === filter)
    const q = query.trim().toLowerCase()
    if (!q) return base
    return base.filter((a) =>
      a.name.toLowerCase().includes(q)
      || a.email.toLowerCase().includes(q)
      || (a.notes || '').toLowerCase().includes(q)
      || (a.message || '').toLowerCase().includes(q)
    )
  }, [appointments, filter, query])

  const toggleSelected = (id: string) => setSelected((cur) => {
    const next = new Set(cur)
    if (next.has(id)) next.delete(id); else next.add(id)
    return next
  })
  const selectAllVisible = () => setSelected(new Set(filtered.map((a) => a.id)))
  const clearSelection = () => setSelected(new Set())
  const allVisibleSelected = filtered.length > 0 && filtered.every((a) => selected.has(a.id))

  const bulkUpdate = async (status: Appointment['status']) => {
    if (selected.size === 0 || bulkBusy) return
    setBulkBusy(true)
    const ids = Array.from(selected)
    const prev = appointments
    setAppointments((cur) => cur.map((x) => ids.includes(x.id) ? { ...x, status } : x))
    try {
      const res = await fetch('/api/admin/appointments/bulk', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids, status }),
      })
      if (!res.ok) throw new Error('Bulk failed')
      clearSelection()
      load()
    } catch {
      setAppointments(prev)
    } finally { setBulkBusy(false) }
  }

  return (
    <div className="admin-shell" data-testid="admin-dashboard">
      <header className="admin-header">
        <div className="admin-title">
          <span className="brand-mark">M</span>
          <div>
            <span className="eyebrow">Meridian · Studio admin</span>
            <h1>Appointments</h1>
          </div>
        </div>
        <div className="admin-actions">
          <a href="/" className="text-link" data-testid="admin-view-site-link">View site ↗</a>
          <button className="icon-button admin-signout" onClick={signOut} data-testid="admin-logout-button" title="Sign out"><LogOut size={16} /> Sign out</button>
        </div>
      </header>

      {stats && (
        <section className="admin-stats" data-testid="admin-stats">
          <StatCard label="Total requests" value={stats.total} icon={<Mail size={16} />} />
          <StatCard label="Awaiting" value={stats.by_status.requested || 0} icon={<Clock3 size={16} />} tone="amber" />
          <StatCard label="Confirmed" value={stats.by_status.confirmed || 0} icon={<CheckCircle2 size={16} />} tone="green" />
          <StatCard label="Cancelled" value={stats.by_status.cancelled || 0} icon={<XCircle size={16} />} tone="grey" />
        </section>
      )}

      <div className="admin-filter" role="tablist">
        {(['all', 'requested', 'confirmed', 'cancelled'] as const).map((f) => (
          <button key={f} type="button" role="tab" aria-selected={filter === f}
            className={`filter-tab ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)} data-testid={`admin-filter-${f}`}>
            {f === 'all' ? 'All' : statusMeta[f].label}
          </button>
        ))}
        <button className="filter-tab refresh" onClick={load} data-testid="admin-refresh-button" aria-label="Refresh"><RotateCcw size={13} /></button>
      </div>

      <div className="admin-search" data-testid="admin-search-bar">
        <Search size={14} strokeWidth={1.6} />
        <input
          type="search"
          placeholder="Search name, email, note or message…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          data-testid="admin-search-input"
          aria-label="Search appointments"
        />
        {query && (
          <button type="button" className="admin-search-clear" onClick={() => setQuery('')} data-testid="admin-search-clear" aria-label="Clear search">
            <XCircle size={14} />
          </button>
        )}
        {(query || filter !== 'all') && (
          <span className="admin-search-count" data-testid="admin-search-count">{filtered.length} of {appointments.length}</span>
        )}
      </div>

      {selected.size > 0 && (
        <motion.div className="bulk-bar" data-testid="admin-bulk-bar"
          initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
          <span className="bulk-count"><CheckSquare size={14} /> {selected.size} selected</span>
          <button className="bulk-link" onClick={selectAllVisible} data-testid="bulk-select-all">Select all visible</button>
          <button className="bulk-link" onClick={clearSelection} data-testid="bulk-clear">Clear</button>
          <div className="bulk-spacer" />
          <button className="button button-small ghost" onClick={() => bulkUpdate('confirmed')} disabled={bulkBusy} data-testid="bulk-confirm">
            <CheckCircle2 size={14} /> Confirm all
          </button>
          <button className="button button-small ghost danger" onClick={() => bulkUpdate('cancelled')} disabled={bulkBusy} data-testid="bulk-cancel">
            <XCircle size={14} /> Cancel all
          </button>
        </motion.div>
      )}

      <div className="admin-export" data-testid="admin-export-bar">
        <span className="admin-export-label"><FileText size={14} /> Export CSV</span>
        <label className="admin-export-date">From
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} data-testid="csv-date-from" />
        </label>
        <label className="admin-export-date">To
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} data-testid="csv-date-to" />
        </label>
        <button className="button button-small ghost" onClick={exportCsv} disabled={exporting} data-testid="csv-export-button">
          <Download size={14} /> {exporting ? 'Preparing…' : 'Download'}
        </button>
      </div>

      <div className="admin-list">
        {loading && appointments.length === 0 ? (
          <div className="admin-empty">Loading appointments…</div>
        ) : filtered.length === 0 ? (
          <div className="admin-empty" data-testid="admin-empty">{query ? `No matches for "${query}".` : 'No appointments in this view yet.'}</div>
        ) : filtered.map((a) => (
          <motion.article key={a.id} className={`admin-card ${selected.has(a.id) ? 'is-selected' : ''}`}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            data-testid={`admin-appointment-${a.id}`}>
            <div className="admin-card-head">
              <button
                type="button"
                className="admin-checkbox"
                onClick={() => toggleSelected(a.id)}
                aria-pressed={selected.has(a.id)}
                aria-label={selected.has(a.id) ? 'Deselect appointment' : 'Select appointment'}
                data-testid={`select-${a.id}`}
              >
                {selected.has(a.id) ? <CheckSquare size={18} strokeWidth={1.7} /> : <Square size={18} strokeWidth={1.5} />}
              </button>
              <div className="admin-card-left">
                <div className="admin-card-time">
                  <Clock3 size={14} /> {fmt(a.slot_start)}
                </div>
                <h3><User size={15} strokeWidth={1.5} /> {a.name}</h3>
                <a href={`mailto:${a.email}`} className="admin-email"><Mail size={13} /> {a.email}</a>
                {a.message && <p className="admin-msg">"{a.message}"</p>}
              </div>
              <div className="admin-card-right">
                <span className={statusMeta[a.status]?.className || 'pill'} data-testid={`status-badge-${a.id}`}>
                  {statusMeta[a.status]?.label || a.status}
                </span>
                <div className="admin-status-actions">
                  <button className="button button-small ghost" disabled={a.status === 'confirmed'}
                    onClick={() => updateStatus(a.id, 'confirmed')} data-testid={`confirm-${a.id}`}>
                    <CheckCircle2 size={14} /> Confirm
                  </button>
                  <button className="button button-small ghost danger" disabled={a.status === 'cancelled'}
                    onClick={() => updateStatus(a.id, 'cancelled')} data-testid={`cancel-${a.id}`}>
                    <XCircle size={14} /> Cancel
                  </button>
                </div>
              </div>
            </div>
            <NoteEditor appointmentId={a.id} initialNotes={a.notes || ''} onSave={saveNotes} />
          </motion.article>
        ))}
      </div>

      {stats?.last_alert && (
        <p className="admin-footer-note" data-testid="admin-alert-status">
          <ShieldCheck size={13} /> Last alert: {stats.last_alert.status} · {stats.last_alert.created_at ? fmt(stats.last_alert.created_at) : '—'}
          {!stats.last_alert.webhook_url && <span> (webhook URL not configured — DB-only)</span>}
        </p>
      )}
    </div>
  )
}

function StatCard({ label, value, icon, tone }: { label: string; value: number; icon: React.ReactNode; tone?: string }) {
  return (
    <div className={`stat-card ${tone || ''}`}>
      <span className="stat-icon">{icon}</span>
      <div>
        <span className="stat-num">{value}</span>
        <span className="stat-label">{label}</span>
      </div>
    </div>
  )
}

function NoteEditor({ appointmentId, initialNotes, onSave }: { appointmentId: string; initialNotes: string; onSave: (id: string, notes: string) => Promise<void> }) {
  const [value, setValue] = useState(initialNotes)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<'idle' | 'saved' | 'error'>('idle')
  useEffect(() => { setValue(initialNotes) }, [initialNotes])
  const dirty = value !== initialNotes
  const save = async () => {
    if (!dirty || saving) return
    setSaving(true); setStatus('idle')
    try { await onSave(appointmentId, value); setStatus('saved'); setTimeout(() => setStatus('idle'), 1800) }
    catch { setStatus('error') }
    finally { setSaving(false) }
  }
  return (
    <div className="admin-notes" data-testid={`notes-editor-${appointmentId}`}>
      <label className="admin-notes-label">
        <FileText size={13} /> Private notes
      </label>
      <textarea
        className="admin-notes-input"
        rows={2}
        placeholder="Jot a private note — visible only in this dashboard."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        data-testid={`notes-input-${appointmentId}`}
      />
      <div className="admin-notes-footer">
        <span className="admin-notes-status" data-testid={`notes-status-${appointmentId}`}>
          {status === 'saved' && '✓ Saved'}
          {status === 'error' && 'Save failed — try again'}
          {status === 'idle' && dirty && 'Unsaved changes'}
        </span>
        <button
          className="button button-small ghost"
          onClick={save}
          disabled={!dirty || saving}
          data-testid={`notes-save-${appointmentId}`}
        >
          <Save size={13} /> {saving ? 'Saving…' : 'Save note'}
        </button>
      </div>
    </div>
  )
}

export default function Admin() {
  const [authState, setAuthState] = useState<'checking' | 'in' | 'out'>('checking')

  const check = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/me', { credentials: 'include' })
      setAuthState(res.ok ? 'in' : 'out')
    } catch { setAuthState('out') }
  }, [])

  useEffect(() => { check() }, [check])

  if (authState === 'checking') return <div className="admin-loading">Loading…</div>
  if (authState === 'out') return <LoginPanel onLoggedIn={() => setAuthState('in')} />
  return <Dashboard onLogout={() => setAuthState('out')} />
}
