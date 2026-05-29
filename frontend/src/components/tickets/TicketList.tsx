/**
 * TicketList.jsx
 * Full ticket management screen.
 * - Customers see their own tickets + can create new ones
 * - Agents see all unassigned + their assigned tickets
 * - Agents can update status, priority, add resolution notes, mark for KB
 * - Both can submit CSAT feedback after resolution
 */

import { useState, useEffect, useCallback } from 'react'
import { ticketsAPI } from '../../api/client'
import FeedbackWidget from "../FeedbackWidget";
import {
  Plus, RefreshCw, ChevronDown, ChevronUp,
  Clock, CheckCircle, AlertCircle, User, Tag
} from 'lucide-react'
import toast from 'react-hot-toast'

// ── Priority / Status badge colours ──────────────────────────────────────
const PRIORITY_STYLES = {
  low:    'bg-gray-100 text-gray-600',
  medium: 'bg-blue-100 text-blue-700',
  high:   'bg-amber-100 text-amber-700',
  urgent: 'bg-red-100 text-red-700',
}

const STATUS_STYLES = {
  open:        'bg-indigo-100 text-indigo-700',
  in_progress: 'bg-amber-100 text-amber-700',
  resolved:    'bg-green-100 text-green-700',
  closed:      'bg-gray-100 text-gray-500',
}

const STATUS_ICONS = {
  open:        <Clock size={12} />,
  in_progress: <AlertCircle size={12} />,
  resolved:    <CheckCircle size={12} />,
  closed:      <CheckCircle size={12} />,
}

// ── Create Ticket Modal ────────────────────────────────────────────────────
function CreateTicketModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium' })
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!form.title.trim() || !form.description.trim()) {
      toast.error('Title and description are required.')
      return
    }
    setSaving(true)
    try {
      const res = await ticketsAPI.create({
        title: form.title,
        initial_message: form.description,
        priority: form.priority,
      })
      toast.success('Ticket created successfully!')
      onCreated(res.data)
      onClose()
    } catch {
      toast.error('Failed to create ticket.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Open a new ticket</h2>

        <label className="block text-sm text-gray-600 mb-1">Title</label>
        <input
          value={form.title}
          onChange={e => setForm({ ...form, title: e.target.value })}
          placeholder="Brief description of the issue"
          className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />

        <label className="block text-sm text-gray-600 mb-1">Details</label>
        <textarea
          value={form.description}
          onChange={e => setForm({ ...form, description: e.target.value })}
          placeholder="Describe the problem in detail…"
          rows={4}
          className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
        />

        <label className="block text-sm text-gray-600 mb-1">Priority</label>
        <select
          value={form.priority}
          onChange={e => setForm({ ...form, priority: e.target.value })}
          className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm mb-5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-xl text-sm hover:bg-gray-50 transition"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={saving}
            className="flex-1 bg-indigo-600 text-white py-2.5 rounded-xl text-sm hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {saving ? 'Creating…' : 'Create ticket'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Agent Update Panel ────────────────────────────────────────────────────
function AgentUpdatePanel({ ticket, onUpdated }) {
  const [form, setForm] = useState({
    status: ticket.status,
    priority: ticket.priority,
    resolution_note: ticket.resolution_note || '',
    add_to_knowledge_base: ticket.add_to_knowledge_base || false,
  })
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    try {
      const res = await ticketsAPI.update(ticket.id, form)
      toast.success('Ticket updated!')
      onUpdated(res.data)
    } catch {
      toast.error('Update failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Agent controls</p>

      <div className="flex gap-3">
        <div className="flex-1">
          <label className="text-xs text-gray-500 mb-1 block">Status</label>
          <select
            value={form.status}
            onChange={e => setForm({ ...form, status: e.target.value })}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          >
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="text-xs text-gray-500 mb-1 block">Priority</label>
          <select
            value={form.priority}
            onChange={e => setForm({ ...form, priority: e.target.value })}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-500 mb-1 block">Resolution note</label>
        <textarea
          value={form.resolution_note}
          onChange={e => setForm({ ...form, resolution_note: e.target.value })}
          placeholder="Describe how this was resolved…"
          rows={3}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
        />
      </div>

      <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-600">
        <input
          type="checkbox"
          checked={form.add_to_knowledge_base}
          onChange={e => setForm({ ...form, add_to_knowledge_base: e.target.checked })}
          className="rounded"
        />
        Add resolution to knowledge base
      </label>

      <button
        onClick={save}
        disabled={saving}
        className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm hover:bg-indigo-700 transition disabled:opacity-50"
      >
        {saving ? 'Saving…' : 'Save changes'}
      </button>
    </div>
  )
}

// ── Single Ticket Row ─────────────────────────────────────────────────────
function TicketRow({ ticket: initialTicket, isAgent }) {
  const [ticket, setTicket] = useState(initialTicket)
  const [expanded, setExpanded] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)

  const isResolved = ticket.status === 'resolved' || ticket.status === 'closed'

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full px-5 py-4 flex items-start justify-between text-left hover:bg-gray-50 transition"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[ticket.status]}`}>
              {STATUS_ICONS[ticket.status]}
              {ticket.status.replace('_', ' ')}
            </span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${PRIORITY_STYLES[ticket.priority]}`}>
              {ticket.priority}
            </span>
            <span className="text-xs text-gray-400">#{ticket.id}</span>
          </div>
          <p className="text-sm font-medium text-gray-800 truncate">{ticket.title}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            {new Date(ticket.created_at).toLocaleDateString('en-IN', {
              day: 'numeric', month: 'short', year: 'numeric'
            })}
          </p>
        </div>
        <span className="ml-3 text-gray-400 mt-1 shrink-0">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="px-5 pb-5">
          <p className="text-sm text-gray-600 leading-relaxed mb-3">
            {ticket.description || `${ticket.message_count || 0} message${ticket.message_count === 1 ? '' : 's'} in this ticket.`}
          </p>

          {ticket.resolution_note && (
            <div className="bg-green-50 border border-green-100 rounded-xl p-3 mb-3">
              <p className="text-xs font-semibold text-green-700 mb-1">Resolution</p>
              <p className="text-sm text-green-800">{ticket.resolution_note}</p>
            </div>
          )}

          {/* Agent panel */}
          {isAgent && (
            <AgentUpdatePanel ticket={ticket} onUpdated={setTicket} />
          )}

          {/* Customer feedback (only on resolved tickets) */}
          {!isAgent && isResolved && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              {showFeedback ? (
                <FeedbackWidget
                  ticketId={ticket.id}
                  onSubmitted={() => setShowFeedback(false)}
                />
              ) : (
                <button
                  onClick={() => setShowFeedback(true)}
                  className="text-sm text-indigo-600 hover:underline"
                >
                  Rate this resolution
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main TicketList Component ─────────────────────────────────────────────
export default function TicketList({ currentUser }) {
  const isAgent = currentUser?.role === 'agent' || currentUser?.role === 'admin'
  const [tickets, setTickets]         = useState([])
  const [loading, setLoading]         = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreate, setShowCreate]   = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await ticketsAPI.list(statusFilter || undefined)
      setTickets(res.data)
    } catch {
      toast.error('Failed to load tickets.')
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => { load() }, [load])

  const handleCreated = (newTicket) => {
    setTickets(prev => [newTicket, ...prev])
  }

  const filterOptions = ['', 'open', 'in_progress', 'pending_agent', 'resolved', 'closed']

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-800">
            {isAgent ? 'All tickets' : 'My tickets'}
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {tickets.length} ticket{tickets.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="p-2 text-gray-400 hover:text-indigo-600 transition"
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
          {!isAgent && (
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-1.5 bg-indigo-600 text-white px-4 py-2 rounded-xl text-sm hover:bg-indigo-700 transition"
            >
              <Plus size={15} />
              New ticket
            </button>
          )}
        </div>
      </div>

      {/* Filter chips */}
      <div className="flex gap-2 flex-wrap mb-5">
        {filterOptions.map(opt => (
          <button
            key={opt || 'all'}
            onClick={() => setStatusFilter(opt)}
            className={`text-xs px-3 py-1.5 rounded-full border transition ${
              statusFilter === opt
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-gray-500 border-gray-200 hover:border-indigo-300'
            }`}
          >
            {opt ? opt.replace('_', ' ') : 'All'}
          </button>
        ))}
      </div>

      {/* Ticket list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-gray-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : tickets.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-lg font-medium">No tickets found</p>
          <p className="text-sm mt-1">
            {isAgent ? 'All clear — no tickets in this category.' : 'Open a ticket if you need help.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {tickets.map(t => (
            <TicketRow key={t.id} ticket={t} isAgent={isAgent} />
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <CreateTicketModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  )
}
