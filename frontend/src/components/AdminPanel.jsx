import { useEffect, useState } from 'react'
import { adminAPI, channelsAPI, knowledgeAPI } from '../api/client'
import toast from 'react-hot-toast'

export default function AdminPanel() {
  const [users, setUsers] = useState([])
  const [channels, setChannels] = useState({})
  const [kb, setKb] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [usersRes, channelsRes, kbRes] = await Promise.all([
        adminAPI.users(),
        channelsAPI.status(),
        knowledgeAPI.list(),
      ])
      setUsers(usersRes.data)
      setChannels(channelsRes.data)
      setKb(kbRes.data)
    } catch {
      toast.error('Failed to load admin data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const approveKb = async (entry) => {
    try {
      const res = await knowledgeAPI.update(entry.id, { status: 'approved' })
      setKb(prev => prev.map(item => item.id === entry.id ? res.data : item))
      toast.success('Knowledge entry approved')
    } catch {
      toast.error('Approval failed')
    }
  }

  const toggleUser = async (user) => {
    try {
      const res = await adminAPI.updateUser(user.id, { is_active: !user.is_active })
      setUsers(prev => prev.map(item => item.id === user.id ? res.data : item))
    } catch {
      toast.error('User update failed')
    }
  }

  if (loading) return <div className="p-6 text-gray-500">Loading admin...</div>

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Admin</h1>
        <p className="text-sm text-gray-500">Manage users, channel status, and knowledge review.</p>
      </div>

      <section className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="font-semibold text-gray-800 mb-3">Users</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr><th className="py-2">Email</th><th>Role</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id} className="border-t">
                  <td className="py-2">{user.email}</td>
                  <td>{user.role}</td>
                  <td>{user.is_active ? 'Active' : 'Disabled'}</td>
                  <td className="text-right">
                    <button onClick={() => toggleUser(user)} className="text-indigo-600 hover:underline">
                      {user.is_active ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="font-semibold text-gray-800 mb-3">Channels</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(channels).map(([name, status]) => (
            <div key={name} className="border border-gray-200 rounded-lg p-3">
              <p className="font-medium capitalize">{name}</p>
              <p className={`text-sm ${status.enabled ? 'text-green-600' : 'text-gray-500'}`}>
                {status.enabled ? 'Enabled' : 'Disabled'} · {status.mode}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="font-semibold text-gray-800 mb-3">Knowledge Review</h2>
        {kb.length === 0 ? (
          <p className="text-sm text-gray-500">No knowledge entries yet.</p>
        ) : (
          <div className="space-y-3">
            {kb.map(entry => (
              <div key={entry.id} className="border border-gray-200 rounded-lg p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{entry.question}</p>
                    <p className="text-sm text-gray-600 mt-1">{entry.answer}</p>
                    <p className="text-xs text-gray-400 mt-2">{entry.status} · {entry.language || 'en'} · {entry.topic || 'support'}</p>
                  </div>
                  {entry.status !== 'approved' && (
                    <button onClick={() => approveKb(entry)} className="shrink-0 bg-indigo-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-indigo-700">
                      Approve
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
