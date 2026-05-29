import { BrowserRouter, Routes, Route, Navigate, NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { LogOut, Menu, X } from 'lucide-react'
import { Toaster, toast } from 'react-hot-toast'
import { authAPI } from './api/client'
import Chat from './components/Chat'
import Analytics from './components/Analytics'
import TicketList from "./components/tickets/TicketList";
import AgentDashboard from './components/AgentDashboard'
import AdminPanel from './components/AdminPanel'

function Login({ onAuthed }) {
  const [form, setForm] = useState({ email: 'customer@example.com', password: 'password123', full_name: 'Customer' })
  const [isRegister, setIsRegister] = useState(false)
  const [saving, setSaving] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const res = isRegister
        ? await authAPI.register(form)
        : await authAPI.login(form.email, form.password)
      localStorage.setItem('access_token', res.data.access_token)
      if (res.data.refresh_token) localStorage.setItem('refresh_token', res.data.refresh_token)
      onAuthed(res.data.user)
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Authentication failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <form onSubmit={submit} className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Support Copilot</h1>
        <p className="text-gray-500 text-sm mb-6">{isRegister ? 'Create your account' : 'Sign in to continue'}</p>
        {isRegister && (
          <input value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })}
            placeholder="Full name" type="text"
            className="w-full border rounded-lg px-4 py-2.5 mb-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        )}
        <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
          placeholder="Email" type="email"
          className="w-full border rounded-lg px-4 py-2.5 mb-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        <input value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
          placeholder="Password" type="password"
          className="w-full border rounded-lg px-4 py-2.5 mb-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        <button disabled={saving} className="w-full bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50">
          {saving ? 'Working...' : isRegister ? 'Create Account' : 'Sign In'}
        </button>
        <button type="button" onClick={() => setIsRegister(!isRegister)} className="w-full text-center text-sm text-indigo-600 mt-4">
          {isRegister ? 'Already have an account? Sign in' : 'Need an account? Register'}
        </button>
      </form>
    </div>
  )
}

function Protected({ user, roles, children }) {
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/chat" replace />
  return children
}

function Layout({ user, onLogout, children }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const isAgent = user.role === 'agent' || user.role === 'admin'
  const links = [
    ['Chat', '/chat', true],
    ['Tickets', '/tickets', true],
    ['Agent', '/agent', isAgent],
    ['Analytics', '/analytics', isAgent],
    ['Admin', '/admin', user.role === 'admin'],
  ].filter(([, , show]) => show)

  const signOut = async () => {
    await onLogout()
    navigate('/login', { replace: true })
  }

  const nav = (
    <nav className="space-y-1">
      {links.map(([label, to]) => (
        <NavLink key={to} to={to} onClick={() => setOpen(false)}
          className={({ isActive }) => `block px-3 py-2 rounded-lg text-sm ${isActive ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-700 hover:bg-gray-100'}`}>
          {label}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-40 bg-white border-b border-gray-200">
        <div className="h-14 px-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setOpen(true)} className="md:hidden p-2 rounded-lg hover:bg-gray-100" aria-label="Open navigation">
              <Menu size={18} />
            </button>
            <span className="font-bold text-indigo-700">Support Copilot</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden sm:block text-xs text-gray-500">{user.email} · {user.role}</span>
            <button onClick={signOut} className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50" aria-label="Sign out">
              <LogOut size={16} />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>
      <div className="flex">
        <aside className="hidden md:block w-56 shrink-0 bg-white border-r border-gray-200 min-h-[calc(100vh-3.5rem)] px-4 py-6">
          {nav}
        </aside>
        {open && (
          <div className="fixed inset-0 z-50 md:hidden">
            <button className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} aria-label="Close navigation" />
            <aside className="relative w-72 h-full bg-white p-4 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <span className="font-bold text-indigo-700">Support Copilot</span>
                <button onClick={() => setOpen(false)} className="p-2 rounded-lg hover:bg-gray-100" aria-label="Close navigation"><X size={18} /></button>
              </div>
              {nav}
            </aside>
          </div>
        )}
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setLoading(false)
      return
    }
    authAPI.me()
      .then(r => setUser(r.data))
      .catch(() => {
        localStorage.removeItem('access_token')
        sessionStorage.clear()
      })
      .finally(() => setLoading(false))
  }, [])

  const logout = async () => {
    try {
      await authAPI.logout()
    } catch {
      // The local clear is authoritative for the browser.
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('session_id')
    localStorage.removeItem('conversation_id')
    sessionStorage.clear()
    setUser(null)
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading...</div>

  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/chat" replace /> : <Login onAuthed={setUser} />} />
        <Route path="/chat" element={<Protected user={user}><Layout user={user} onLogout={logout}><Chat /></Layout></Protected>} />
        <Route path="/tickets" element={<Protected user={user}><Layout user={user} onLogout={logout}><TicketList currentUser={user} /></Layout></Protected>} />
        <Route path="/agent" element={<Protected user={user} roles={['agent', 'admin']}><Layout user={user} onLogout={logout}><AgentDashboard currentUser={user} /></Layout></Protected>} />
        <Route path="/analytics" element={<Protected user={user} roles={['agent', 'admin']}><Layout user={user} onLogout={logout}><Analytics /></Layout></Protected>} />
        <Route path="/admin" element={<Protected user={user} roles={['admin']}><Layout user={user} onLogout={logout}><AdminPanel /></Layout></Protected>} />
        <Route path="*" element={<Navigate to={user ? '/chat' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}
