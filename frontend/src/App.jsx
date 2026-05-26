import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { authAPI } from './api/client';
import Chat from './components/Chat';
import Analytics from './components/Analytics';
import TicketList from './components/TicketList';

function Login() {
  const [form, setForm] = useState({ email: '', password: '' });
  const [isRegister, setIsRegister] = useState(false);

  const submit = async () => {
    try {
      const res = isRegister
        ? await authAPI.register({ ...form, username: form.email.split('@')[0] })
        : await authAPI.login(form.email, form.password);
      localStorage.setItem('access_token', res.data.access_token);
      window.location.href = '/chat';
    } catch (e) {
      alert(e.response?.data?.detail || 'Error');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Support Copilot</h1>
        <p className="text-gray-500 text-sm mb-6">{isRegister ? 'Create your account' : 'Sign in to continue'}</p>
        <input value={form.email} onChange={e => setForm({...form, email: e.target.value})}
          placeholder="Email" type="email"
          className="w-full border rounded-xl px-4 py-2.5 mb-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        <input value={form.password} onChange={e => setForm({...form, password: e.target.value})}
          placeholder="Password" type="password"
          className="w-full border rounded-xl px-4 py-2.5 mb-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        <button onClick={submit}
          className="w-full bg-indigo-600 text-white py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition">
          {isRegister ? 'Create Account' : 'Sign In'}
        </button>
        <p className="text-center text-sm text-gray-500 mt-4">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}
          <button onClick={() => setIsRegister(!isRegister)} className="text-indigo-600 ml-1 font-medium">
            {isRegister ? 'Sign in' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  );
}

function Layout({ children, role }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-56 bg-white border-r border-gray-100 px-4 py-6">
        <p className="text-lg font-bold text-indigo-600 mb-8">Support Copilot</p>
        <nav className="space-y-1">
          <Link to="/chat" className="block px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-600">Chat</Link>
          <Link to="/tickets" className="block px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-600">Tickets</Link>
          {(role === 'agent' || role === 'admin') && (
            <Link to="/analytics" className="block px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-600">Analytics</Link>
          )}
        </nav>
        <div className="absolute bottom-6 left-4 right-4">
          <button onClick={() => { localStorage.removeItem('access_token'); window.location.href='/login'; }}
            className="w-full text-xs text-gray-400 hover:text-red-500">Sign out</button>
        </div>
      </aside>
      <main className="flex-1">{children}</main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      authAPI.me().then(r => setUser(r.data)).catch(() => {}).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>;

  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/chat" element={user ? <Layout role={user.role}><Chat /></Layout> : <Navigate to="/login" />} />
        <Route path="/tickets" element={user ? <Layout role={user.role}><TicketList /></Layout> : <Navigate to="/login" />} />
        <Route path="/analytics" element={user ? <Layout role={user.role}><Analytics /></Layout> : <Navigate to="/login" />} />
        <Route path="*" element={<Navigate to={user ? '/chat' : '/login'} />} />
      </Routes>
    </BrowserRouter>
  );
}