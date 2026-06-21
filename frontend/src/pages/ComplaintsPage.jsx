import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Filter, ArrowRight, Plus } from 'lucide-react';
import { complaintsAPI } from '../utils/api';
import { format } from 'date-fns';
import { useAuthStore } from '../store/authStore';

const CATEGORIES = [
  '', 'financial_fraud','phishing','identity_theft','cyberbullying',
  'ransomware','hacking','social_media_fraud','upi_fraud','otp_fraud','investment_fraud','other'
];
const STATUSES  = ['','submitted','under_review','investigating','linked','resolved','closed'];
const RISKS     = ['','critical','high','medium','low'];

function RiskBadge({ level }) {
  const cls = { critical:'badge-critical', high:'badge-high', medium:'badge-medium', low:'badge-low' };
  return <span className={cls[level] || 'badge capitalize'}>{level}</span>;
}
function StatusBadge({ status }) {
  const cls = `status-${status}`;
  return <span className={`${cls} capitalize`}>{status?.replace(/_/g,' ')}</span>;
}

export default function ComplaintsPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const filters = {
    page,
    page_size: 20,
    status:     params.get('status')     || undefined,
    category:   params.get('category')   || undefined,
    risk_level: params.get('risk_level') || undefined,
    search:     search || undefined,
    sort_by:    'risk_score',
    sort_order: 'desc',
  };

  const { data, isLoading } = useQuery({
    queryKey: ['complaints', filters],
    queryFn: () => complaintsAPI.list(filters).then(r => r.data),
    keepPreviousData: true,
  });

  const setFilter = (key, val) => {
    const p = new URLSearchParams(params);
    if (val) p.set(key, val); else p.delete(key);
    setParams(p);
    setPage(1);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Complaints</h1>
          <p className="page-subtitle">{data?.total || 0} total records</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/complaints/new')}>
          <Plus size={16} /> Submit Complaint
        </button>
      </div>

      {/* Filters */}
      <div className="ct-card p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-48">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="ct-input pl-8 text-sm" placeholder="Search complaints..."
              value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
          </div>
          <select className="ct-select w-36 text-sm" value={params.get('status') || ''}
            onChange={e => setFilter('status', e.target.value)}>
            {STATUSES.map(s => <option key={s} value={s}>{s ? s.replace(/_/g,' ') : 'All Status'}</option>)}
          </select>
          <select className="ct-select w-40 text-sm" value={params.get('risk_level') || ''}
            onChange={e => setFilter('risk_level', e.target.value)}>
            {RISKS.map(r => <option key={r} value={r}>{r ? r : 'All Risk Levels'}</option>)}
          </select>
          <select className="ct-select w-44 text-sm" value={params.get('category') || ''}
            onChange={e => setFilter('category', e.target.value)}>
            {CATEGORIES.map(c => <option key={c} value={c}>{c ? c.replace(/_/g,' ') : 'All Categories'}</option>)}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="ct-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full" />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="ct-table">
                <thead>
                  <tr>
                    <th>Complaint #</th>
                    <th>Title</th>
                    <th>Category</th>
                    <th>Risk</th>
                    <th>Status</th>
                    <th>Entities</th>
                    {user?.role !== 'citizen' && <th>Loss</th>}
                    <th>Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items?.map(c => (
                    <tr key={c.id} className="cursor-pointer" onClick={() => navigate(`/complaints/${c.id}`)}>
                      <td><span className="font-mono text-xs font-bold text-blue-700">{c.complaint_number}</span></td>
                      <td>
                        <div>
                          <p className="font-medium text-slate-800 text-sm">{c.title.slice(0,50)}{c.title.length>50?'...':''}</p>
                          {c.linked_case_ids?.length > 0 && (
                            <span className="text-xs text-orange-600 font-medium">
                              🔗 {c.linked_case_ids.length} linked case(s)
                            </span>
                          )}
                        </div>
                      </td>
                      <td><span className="text-xs capitalize text-slate-500">{c.category?.replace(/_/g,' ')}</span></td>
                      <td>
                        <div className="flex items-center gap-1.5">
                          <div className="risk-bar w-12">
                            <div className="risk-bar-fill" style={{
                              width:`${(c.risk_score||0)*100}%`,
                              background: c.risk_level==='critical'?'#DC2626':c.risk_level==='high'?'#EA580C':c.risk_level==='medium'?'#D97706':'#16A34A'
                            }}/>
                          </div>
                          <RiskBadge level={c.risk_level} />
                        </div>
                      </td>
                      <td><StatusBadge status={c.status} /></td>
                      <td><span className="text-xs font-medium text-slate-600">{c.entity_count || 0}</span></td>
                      {user?.role !== 'citizen' && (
                        <td><span className="text-xs text-slate-500">{c.financial_loss ? `₹${c.financial_loss.toLocaleString()}` : '—'}</span></td>
                      )}
                      <td><span className="text-xs text-slate-400">{format(new Date(c.created_at), 'dd MMM yy')}</span></td>
                      <td><ArrowRight size={14} className="text-slate-300" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data?.total_pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
                <p className="text-xs text-slate-500">
                  Showing {((page - 1) * 20) + 1}–{Math.min(page * 20, data.total)} of {data.total}
                </p>
                <div className="flex gap-2">
                  <button className="btn-secondary text-xs py-1" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
                  <button className="btn-secondary text-xs py-1" disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
