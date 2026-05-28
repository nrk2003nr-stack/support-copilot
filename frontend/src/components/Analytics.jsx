import { useEffect, useState } from 'react';
import { analyticsAPI } from '../api/client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444'];

export default function Analytics() {
  const [data, setData] = useState(null);
  const [byStatus, setByStatus] = useState([]);
  const [byPriority, setByPriority] = useState([]);
  const [channelMix, setChannelMix] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      analyticsAPI.overview(),
      analyticsAPI.byStatus(),
      analyticsAPI.byPriority(),
      analyticsAPI.channelMix(),
    ]).then(([overview, status, priority, channels]) => {
      setData(overview.data);
      setByStatus(status.data);
      setByPriority(priority.data);
      setChannelMix(channels.data);
    }).catch(() => setError('Failed to load analytics.'));
  }, []);

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!data) return <div className="p-8 text-gray-500">Loading analytics...</div>;

  const stats = [
    { label: 'Total Tickets', value: data.total_tickets },
    { label: 'Resolution Rate', value: `${data.resolution_rate}%` },
    { label: 'Avg CSAT', value: `${data.avg_csat_rating}/5` },
    { label: 'Escalation Rate', value: `${data.escalation_rate}%` },
    { label: 'Reopen Rate', value: `${data.reopen_rate || 0}%` },
    { label: 'SLA Breaches', value: data.sla_breaches || 0 },
  ];

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Analytics Dashboard</h2>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {stats.map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{s.label}</p>
            <p className="text-2xl font-bold text-indigo-600 mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border p-4 shadow-sm">
        <p className="text-sm font-semibold text-gray-700 mb-3">Channel Mix</p>
        <div className="flex flex-wrap gap-2">
          {channelMix.length === 0 ? <span className="text-sm text-gray-500">No channel data yet</span> : channelMix.map(item => (
            <span key={item.channel} className="text-xs rounded-full bg-gray-100 px-3 py-1 text-gray-700">
              {item.channel}: {item.count}
            </span>
          ))}
        </div>
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-4 shadow-sm">
          <p className="text-sm font-semibold text-gray-700 mb-4">Tickets by Status</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={byStatus}>
              <XAxis dataKey="status" tick={{ fontSize: 12 }} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#6366f1" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white rounded-xl border p-4 shadow-sm">
          <p className="text-sm font-semibold text-gray-700 mb-4">Tickets by Priority</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={byPriority} dataKey="count" nameKey="priority" cx="50%" cy="50%" outerRadius={80} label>
                {byPriority.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
