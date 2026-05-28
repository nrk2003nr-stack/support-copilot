/**
 * AgentDashboard.jsx
 * Real-time dashboard for agents and admins.
 * Features:
 *  - Live WebSocket connection to receive escalation alerts
 *  - Unassigned urgent ticket queue
 *  - Assign ticket to self with one click
 *  - Live customer message feed when handling an escalated chat
 *  - Quick reply to customer via WebSocket
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { ticketsAPI } from '../api/client'
import {
  Bell, BellRing, MessageCircle, CheckCircle,
  AlertTriangle, User, RefreshCw, Send
} from 'lucide-react'
import toast from 'react-hot-toast'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

// ── Escalation Alert Banner ───────────────────────────────────────────────
function EscalationAlert({ alert, onAccept, onDismiss }) {
  return (
    <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl p-4">
      <div className="mt-0.5 shrink-0 text-red-500">
        <BellRing size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-red-700">Customer needs help</p>
        <p className="text-xs text-red-500 mt-0.5 truncate">
          Session: {alert.session_id} · {alert.reason}
        </p>
        {alert.sentiment_score !== undefined && (
          <p className="text-xs text-red-400 mt-0.5">
            Sentiment score: {alert.sentiment_score?.toFixed(2)}
          </p>
        )}
      </div>
      <div className="flex gap-2 shrink-0">
        <button
          onClick={() => onDismiss(alert.session_id)}
          className="text-xs px-2.5 py-1.5 border border-red-200 text-red-600 rounded-lg hover:bg-red-100 transition"
        >
          Dismiss
        </button>
        <button
          onClick={() => onAccept(alert)}
          className="text-xs px-2.5 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
        >
          Accept
        </button>
      </div>
    </div>
  )
}

// ── Live Chat Panel (after agent accepts escalation) ──────────────────────
function LiveChatPanel({ customerSession, agentSession, ws, onClose, user }) {
  const [messages, setMessages] = useState([])
  const [input, setInput]       = useState('')
  const bottomRef               = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Listen for incoming customer messages directed to this agent
  useEffect(() => {
    if (!ws) return
    const handler = (event) => {
      const data = JSON.parse(event.data)
      if (
        data.type === 'customer_message' &&
        data.session_id === customerSession
      ) {
        setMessages(prev => [...prev, {
          role: 'customer',
          content: data.content,
          timestamp: data.timestamp,
        }])
      }
    }
    ws.addEventListener('message', handler)
    return () => ws.removeEventListener('message', handler)
  }, [ws, customerSession])

  const sendReply = () => {
    if (!input.trim() || !ws) return
    const msg = {
      type: 'agent_message',
      customer_session: customerSession,
      content: input.trim(),
      agent_name: user?.username || 'Agent',
    }
    ws.send(JSON.stringify(msg))
    setMessages(prev => [...prev, {
      role: 'agent',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }])
    setInput('')
  }

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden flex flex-col h-96">
      {/* Header */}
      <div className="bg-indigo-600 text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageCircle size={16} />
          <span className="text-sm font-medium">Live chat — customer {customerSession.slice(0, 8)}…</span>
        </div>
        <button
          onClick={onClose}
          className="text-indigo-200 hover:text-white text-xs"
        >
          Close
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {messages.length === 0 && (
          <p className="text-xs text-gray-400 text-center mt-8">
            Waiting for customer messages…
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'agent' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] text-xs px-3 py-2 rounded-xl ${
              m.role === 'agent'
                ? 'bg-indigo-600 text-white rounded-br-sm'
                : 'bg-gray-100 text-gray-800 rounded-bl-sm'
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-100 px-3 py-2 flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendReply()}
          placeholder="Type a reply…"
          className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <button
          onClick={sendReply}
          className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 transition"
        >
          <Send size={13} />
        </button>
      </div>
    </div>
  )
}

// ── Ticket Card ───────────────────────────────────────────────────────────
function TicketCard({ ticket, onAssigned }) {
  const user = ticket.currentUser
  const [loading, setLoading] = useState(false)

  const assign = async () => {
    setLoading(true)
    try {
      await ticketsAPI.assign(ticket.id)
      toast.success('Ticket assigned to you!')
      onAssigned(ticket.id)
    } catch {
      toast.error('Could not assign ticket.')
    } finally {
      setLoading(false)
    }
  }

  const PRIORITY_DOT = {
    low: 'bg-gray-400',
    medium: 'bg-blue-400',
    high: 'bg-amber-400',
    urgent: 'bg-red-500',
  }

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2 h-2 rounded-full shrink-0 ${PRIORITY_DOT[ticket.priority]}`} />
            <span className="text-xs text-gray-500">#{ticket.id} · {ticket.priority}</span>
          </div>
          <p className="text-sm font-medium text-gray-800 truncate">{ticket.title}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            {new Date(ticket.created_at).toLocaleDateString()}
          </p>
        </div>
        {!ticket.assigned_agent_id && (
          <button
            onClick={assign}
            disabled={loading}
            className="shrink-0 text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1.5 rounded-lg hover:bg-indigo-100 transition disabled:opacity-50"
          >
            {loading ? '…' : 'Claim'}
          </button>
        )}
        {ticket.assigned_agent_id === user?.id && (
          <span className="text-xs text-green-600 flex items-center gap-1 shrink-0">
            <CheckCircle size={12} />
            Yours
          </span>
        )}
      </div>
      {ticket.description && (
        <p className="text-xs text-gray-500 mt-2 line-clamp-2">{ticket.description}</p>
      )}
    </div>
  )
}

// ── Main AgentDashboard ───────────────────────────────────────────────────
export default function AgentDashboard({ currentUser }) {
  const user = currentUser
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts]   = useState([])          // live escalation alerts
  const [activeChat, setActiveChat] = useState(null)  // { session_id }
  const wsRef                 = useRef(null)

  // ── WebSocket connection ───────────────────────────────────────────────
  useEffect(() => {
    if (!user) return
    const sessionId = `agent_${user.id}`
    const ws = new WebSocket(`${WS_BASE}/handoff/ws/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => {}

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'escalation_request') {
        setAlerts(prev => {
          // De-duplicate by session_id
          if (prev.some(a => a.session_id === data.session_id)) return prev
          return [data, ...prev]
        })
        toast.custom((t) => (
          <div className={`flex items-center gap-2 bg-white border border-red-200 shadow-lg rounded-xl px-4 py-3 ${t.visible ? 'animate-enter' : 'animate-leave'}`}>
            <AlertTriangle size={16} className="text-red-500" />
            <span className="text-sm text-gray-700">Customer needs a human agent!</span>
          </div>
        ), { duration: 5000 })
      }
    }

    ws.onclose = () => {}

    return () => ws.close()
  }, [user])

  // ── Load tickets ───────────────────────────────────────────────────────
  const loadTickets = useCallback(async () => {
    setLoading(true)
    try {
      const res = await ticketsAPI.list()
      setTickets(res.data)
    } catch {
      toast.error('Failed to load tickets.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadTickets() }, [loadTickets])

  const handleDismissAlert = (sessionId) => {
    setAlerts(prev => prev.filter(a => a.session_id !== sessionId))
  }

  const handleAcceptAlert = (alert) => {
    setActiveChat(alert)
    setAlerts(prev => prev.filter(a => a.session_id !== alert.session_id))
    toast.success('Chat session accepted!')
  }

  const handleAssigned = (ticketId) => {
    setTickets(prev => prev.map(t =>
      t.id === ticketId ? { ...t, assigned_agent_id: user?.id, status: 'in_progress' } : t
    ))
  }

  const urgentOpen   = tickets.filter(t => t.priority === 'urgent' && t.status === 'open')
  const myTickets    = tickets.filter(t => t.assigned_agent_id === user?.id)
  const unassigned   = tickets.filter(t => !t.assigned_agent_id && t.status === 'open')

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Page title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-800">Agent Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Welcome back, {user?.username}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {alerts.length > 0 && (
            <span className="flex items-center gap-1 text-xs bg-red-100 text-red-700 px-2.5 py-1 rounded-full font-medium">
              <BellRing size={12} />
              {alerts.length} alert{alerts.length > 1 ? 's' : ''}
            </span>
          )}
          <button
            onClick={loadTickets}
            className="p-2 text-gray-400 hover:text-indigo-600 transition"
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Live escalation alerts */}
      {alerts.length > 0 && (
        <section>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Live escalations
          </p>
          <div className="space-y-2">
            {alerts.map(alert => (
              <EscalationAlert
                key={alert.session_id}
                alert={alert}
                onAccept={handleAcceptAlert}
                onDismiss={handleDismissAlert}
              />
            ))}
          </div>
        </section>
      )}

      {/* Active live chat */}
      {activeChat && (
        <section>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Active live chat
          </p>
          <LiveChatPanel
            customerSession={activeChat.session_id}
            agentSession={`agent_${user?.id}`}
            ws={wsRef.current}
            user={user}
            onClose={() => setActiveChat(null)}
          />
        </section>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Unassigned', value: unassigned.length, color: 'text-amber-600' },
          { label: 'My open tickets', value: myTickets.filter(t => t.status !== 'resolved').length, color: 'text-indigo-600' },
          { label: 'Urgent', value: urgentOpen.length, color: 'text-red-600' },
        ].map(s => (
          <div key={s.label} className="bg-white border border-gray-100 rounded-xl p-4 text-center shadow-sm">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Urgent tickets */}
      {urgentOpen.length > 0 && (
        <section>
          <p className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-3 flex items-center gap-1">
            <AlertTriangle size={12} />
            Urgent &amp; unresolved
          </p>
          <div className="space-y-3">
            {urgentOpen.map(t => (
              <TicketCard key={t.id} ticket={{ ...t, currentUser: user }} onAssigned={handleAssigned} />
            ))}
          </div>
        </section>
      )}

      {/* Unassigned queue */}
      <section>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Unassigned queue ({unassigned.length})
        </p>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : unassigned.length === 0 ? (
          <div className="text-center py-10 text-gray-400">
            <CheckCircle size={32} className="mx-auto mb-2 text-green-400" />
            <p className="text-sm">Queue is clear!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {unassigned.slice(0, 10).map(t => (
              <TicketCard key={t.id} ticket={{ ...t, currentUser: user }} onAssigned={handleAssigned} />
            ))}
          </div>
        )}
      </section>

      {/* My tickets */}
      {myTickets.length > 0 && (
        <section>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            My tickets ({myTickets.length})
          </p>
          <div className="space-y-3">
            {myTickets.map(t => (
              <TicketCard key={t.id} ticket={{ ...t, currentUser: user }} onAssigned={handleAssigned} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
