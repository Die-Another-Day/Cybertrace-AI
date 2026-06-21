import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import {
  FileText, AlertTriangle, CheckCircle, TrendingUp,
  Database, Link2, Target, DollarSign, Clock, ArrowRight
} from 'lucide-react';
import { dashboardAPI } from '../utils/api';
import { useAuthStore } from '../store/authStore';
import { format } from 'date-fns';

const RISK_COLORS = { critical: '#DC2626', high: '#EA580C', medium: '#D97706', low: '#16A34A' };
const CATEGORY_COLORS = ['#2563EB','#7C3AED','#DB2777','#D97706','#059669','#DC2626','#0891B2'];

function StatCard({ icon: Icon, label, value, sub, color = 'blue', onClick }) {
  const colors = {
    blue:   { bg: 'bg-blue-50',   icon: 'bg-blue-100 text-blue-700', text: 'text-blue-800' },
    red:    { bg: 'bg-red-50',    icon: 'bg-red-100 text-red-700',   text: 'text-red-800' },
    orange: { bg: 'bg-orange-50', icon: 'bg-orange-100 text-orange-700', text: 'text-orange-800' },
    green:  { bg: 'bg-green-50',  icon: 'bg-green-100 text-green-700',  text: 'text-green-800' },
    purple: { bg: 'bg-purple-50', icon: 'bg-purple-100 text-purple-700', text: 'text-purple-800' },
  };
  const c = colors[color];

  return (
    <div className={`stat-card cursor-pointer hover:shadow-md transition-shadow ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}>
      <div className={`stat-icon ${c.icon}`}><Icon size={20} /></div>
      <div>
        <p className="text-xs text-slate-500 font-medium">{label}</p>
        <p className={`text-2xl font-bold ${c.text} mt-0.5`}>{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function RiskBadge({ level }) {
  const cls = {
    critical: 'badge-critical', high: 'badge-high',
    medium: 'badge-medium', low: 'badge-low'
  };
  return <span className={cls[level] || 'badge'}>{level}</span>;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const isLEO = ['investigator', 'supervisor', 'admin'].includes(user?.role);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardAPI.stats().then(r => r.data),
    enabled: isLEO,
    refetchInterval: 30000,
  });

  const { data: trends } = useQuery({
    queryKey: ['trends-30'],
    queryFn: () => dashboardAPI.trends(30).then(r => r.data),
    enabled: isLEO,
  });

  const { data: priority } = useQuery({
    queryKey: ['priority-queue'],
    queryFn: () => dashboardAPI.priority(8).then(r => r.data),
    enabled: isLEO,
  });

  const { data: recent } = useQuery({
    queryKey: ['recent-complaints'],
    queryFn: () => dashboardAPI.recent(5).then(r => r.data),
    enabled: !isLEO,
  });

  if (!isLEO) {
    // Citizen view
    return (
      <div>
        <div className="page-header">
          <div>
            <h1 className="page-title">Welcome, {user?.full_name}</h1>
            <p className="page-subtitle">Submit and track your cybercrime complaints</p>
          </div>
          <button className="btn-primary" onClick={() => navigate('/complaints/new')}>
            + Submit Complaint
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard icon={FileText} label="My Complaints" value={recent?.length || 0} color="blue" onClick={() => navigate('/complaints')} />
          <StatCard icon={Clock} label="Under Review" value={recent?.filter(c => c.status === 'under_review').length || 0} color="orange" />
          <StatCard icon={CheckCircle} label="Resolved" value={recent?.filter(c => c.status === 'resolved').length || 0} color="green" />
        </div>
        <div className="ct-card">
          <div className="ct-card-header">
            <h3 className="font-semibold text-slate-700">Recent Complaints</h3>
            <button className="btn-ghost text-xs" onClick={() => navigate('/complaints')}>View All <ArrowRight size={12} /></button>
          </div>
          <div className="p-4 space-y-3">
            {recent?.map(c => (
              <div key={c.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100"
                onClick={() => navigate(`/complaints/${c.id}`)}>
                <div>
                  <p className="text-sm font-medium text-slate-700">{c.complaint_number}</p>
                  <p className="text-xs text-slate-500">{c.title.slice(0, 60)}...</p>
                </div>
                <RiskBadge level={c.risk_level} />
              </div>
            ))}
            {!recent?.length && <p className="text-sm text-slate-400 text-center py-8">No complaints submitted yet.</p>}
          </div>
        </div>
      </div>
    );
  }

  if (statsLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full" />
    </div>
  );

  const pieData = [
    { name: 'Critical', value: stats?.critical_complaints || 0, color: '#DC2626' },
    { name: 'High',     value: stats?.high_risk_complaints || 0, color: '#EA580C' },
    { name: 'Others',   value: Math.max(0, (stats?.total_complaints || 0) - (stats?.critical_complaints || 0) - (stats?.high_risk_complaints || 0)), color: '#2563EB' },
  ].filter(d => d.value > 0);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Investigation Dashboard</h1>
          <p className="page-subtitle">Real-time cybercrime intelligence overview</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary text-xs" onClick={() => navigate('/graph')}>View Threat Graph</button>
          <button className="btn-primary" onClick={() => navigate('/complaints/new')}>+ New Complaint</button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard icon={FileText} label="Total Complaints" value={stats?.total_complaints || 0}
          sub={`${stats?.complaints_today || 0} today`} color="blue" onClick={() => navigate('/complaints')} />
        <StatCard icon={AlertTriangle} label="Critical / High" color="red"
          value={`${stats?.critical_complaints || 0} / ${stats?.high_risk_complaints || 0}`}
          sub="Require immediate action" onClick={() => navigate('/complaints?risk_level=critical')} />
        <StatCard icon={Link2} label="Linked Case Pairs" value={stats?.linked_case_pairs || 0}
          sub="Correlated via graph" color="purple" onClick={() => navigate('/graph')} />
        <StatCard icon={Target} label="Active Campaigns" value={stats?.active_campaigns || 0}
          sub="Scam campaign clusters" color="orange" onClick={() => navigate('/intelligence')} />
        <StatCard icon={Database} label="Entities Extracted" value={stats?.total_entities_extracted || 0}
          sub="Phone / UPI / IP / URL" color="blue" />
        <StatCard icon={CheckCircle} label="Resolved" value={stats?.resolved_complaints || 0}
          sub={`of ${stats?.total_complaints || 0} total`} color="green" />
        <StatCard icon={TrendingUp} label="Graph Nodes" value={stats?.graph_nodes || 0}
          sub={`${stats?.graph_edges || 0} relationships`} color="purple" />
        <StatCard icon={DollarSign} label="Total Financial Loss"
          value={`₹${((stats?.total_financial_loss || 0) / 100000).toFixed(1)}L`}
          sub="Reported by victims" color="red" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Trend area chart */}
        <div className="ct-card col-span-2">
          <div className="ct-card-header">
            <h3 className="font-semibold text-slate-700">Complaint Trend (30 days)</h3>
          </div>
          <div className="p-4">
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={trends || []}>
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" tick={{ fontSize: 10 }}
                  tickFormatter={v => format(new Date(v), 'dd MMM')} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip labelFormatter={v => format(new Date(v), 'dd MMM yyyy')} />
                <Area type="monotone" dataKey="count" name="Complaints"
                  stroke="#2563EB" fill="url(#areaGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk distribution pie */}
        <div className="ct-card">
          <div className="ct-card-header">
            <h3 className="font-semibold text-slate-700">Risk Distribution</h3>
          </div>
          <div className="p-4 flex flex-col items-center">
            <ResponsiveContainer width="100%" height={140}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={65}
                  dataKey="value" paddingAngle={3}>
                  {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-col gap-1 w-full mt-2">
              {pieData.map(d => (
                <div key={d.name} className="flex items-center gap-2 text-xs text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: d.color }} />
                  <span className="flex-1">{d.name}</span>
                  <span className="font-semibold">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Priority Queue */}
      <div className="ct-card">
        <div className="ct-card-header">
          <div>
            <h3 className="font-semibold text-slate-700">Priority Queue</h3>
            <p className="text-xs text-slate-400">Unassigned complaints ranked by AI risk score</p>
          </div>
          <button className="btn-ghost text-xs" onClick={() => navigate('/complaints')}>
            View All <ArrowRight size={12} />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="ct-table">
            <thead>
              <tr>
                <th>Complaint #</th>
                <th>Title</th>
                <th>Category</th>
                <th>Risk Score</th>
                <th>Risk Level</th>
                <th>Submitted</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {priority?.map(c => (
                <tr key={c.id} className="cursor-pointer" onClick={() => navigate(`/complaints/${c.id}`)}>
                  <td><span className="font-mono text-xs font-semibold text-blue-700">{c.complaint_number}</span></td>
                  <td><span className="font-medium">{c.title.slice(0, 45)}{c.title.length > 45 ? '...' : ''}</span></td>
                  <td><span className="text-xs text-slate-500 capitalize">{c.category?.replace(/_/g, ' ')}</span></td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="risk-bar w-16">
                        <div className="risk-bar-fill" style={{
                          width: `${(c.risk_score || 0) * 100}%`,
                          background: c.risk_level === 'critical' ? '#DC2626' : c.risk_level === 'high' ? '#EA580C' : c.risk_level === 'medium' ? '#D97706' : '#16A34A'
                        }} />
                      </div>
                      <span className="text-xs font-mono">{((c.risk_score || 0) * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td><RiskBadge level={c.risk_level} /></td>
                  <td><span className="text-xs text-slate-400">{format(new Date(c.created_at), 'dd MMM HH:mm')}</span></td>
                  <td><ArrowRight size={14} className="text-slate-400" /></td>
                </tr>
              ))}
              {!priority?.length && (
                <tr><td colSpan={7} className="text-center py-8 text-slate-400">No pending complaints in queue.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
