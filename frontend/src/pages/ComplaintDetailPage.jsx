import React, { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  ArrowLeft, RefreshCw, Upload, MessageSquare, Link2,
  AlertTriangle, CheckCircle, Clock, FileText, Shield
} from 'lucide-react';
import { complaintsAPI, evidenceAPI } from '../utils/api';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

const ENTITY_LABELS = {
  phone_number:'Phone', upi_id:'UPI ID', email:'Email', url:'URL',
  ip_address:'IP', bank_account:'Bank Acct', social_handle:'Social', domain:'Domain',
  ifsc_code:'IFSC', keyword:'Keyword'
};

function RiskBadge({ level }) {
  const cls={critical:'badge-critical',high:'badge-high',medium:'badge-medium',low:'badge-low'};
  return <span className={cls[level]||'badge'}>{level?.toUpperCase()}</span>;
}
function StatusBadge({ s }) {
  return <span className={`status-${s} capitalize`}>{s?.replace(/_/g,' ')}</span>;
}

export default function ComplaintDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuthStore();
  const isLEO = ['investigator','supervisor','admin'].includes(user?.role);
  const fileRef = useRef();
  const [noteText, setNoteText] = useState('');
  const [tab, setTab] = useState('overview');

  const { data: complaint, isLoading } = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => complaintsAPI.get(id).then(r => r.data),
  });

  const { data: entities } = useQuery({
    queryKey: ['entities', id],
    queryFn: () => complaintsAPI.entities(id).then(r => r.data),
  });

  const { data: related } = useQuery({
    queryKey: ['related', id],
    queryFn: () => complaintsAPI.related(id).then(r => r.data),
    enabled: isLEO,
  });

  const { data: notes } = useQuery({
    queryKey: ['notes', id],
    queryFn: () => complaintsAPI.notes(id).then(r => r.data),
  });

  const processMut = useMutation({
    mutationFn: () => complaintsAPI.process(id),
    onSuccess: (r) => {
      toast.success(`Processing complete: ${r.data.entities_found} entities found`);
      qc.invalidateQueries(['complaint', id]);
      qc.invalidateQueries(['entities', id]);
    },
    onError: () => toast.error('Processing failed.'),
  });

  const noteMut = useMutation({
    mutationFn: () => complaintsAPI.addNote(id, { content: noteText, is_internal: true }),
    onSuccess: () => {
      toast.success('Note added.');
      setNoteText('');
      qc.invalidateQueries(['notes', id]);
    },
  });

  const uploadMut = useMutation({
    mutationFn: (file) => evidenceAPI.upload(id, file),
    onSuccess: () => { toast.success('Evidence uploaded and processed.'); },
    onError: () => toast.error('Upload failed.'),
  });

  const statusMut = useMutation({
    mutationFn: (status) => complaintsAPI.update(id, { status }),
    onSuccess: () => {
      toast.success('Status updated.');
      qc.invalidateQueries(['complaint', id]);
    },
  });

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full" />
    </div>
  );

  if (!complaint) return <p className="text-slate-500">Complaint not found.</p>;

  const TABS = ['overview', 'entities', ...(isLEO ? ['related','evidence','notes'] : ['notes'])];

  return (
    <div>
      {/* Header */}
      <div className="flex items-start gap-3 mb-6">
        <button className="btn-ghost p-2" onClick={() => navigate('/complaints')}><ArrowLeft size={18}/></button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="page-title">{complaint.complaint_number}</h1>
            <RiskBadge level={complaint.risk_level} />
            <StatusBadge s={complaint.status} />
          </div>
          <p className="page-subtitle mt-0.5">{complaint.title}</p>
        </div>
        {isLEO && (
          <div className="flex gap-2">
            <button className="btn-secondary text-xs" onClick={() => processMut.mutate()}
              disabled={processMut.isPending}>
              <RefreshCw size={13} className={processMut.isPending ? 'animate-spin' : ''} />
              {processMut.isPending ? 'Analyzing...' : 'Re-analyze'}
            </button>
            <select className="ct-select text-xs w-40"
              value={complaint.status}
              onChange={e => statusMut.mutate(e.target.value)}>
              {['submitted','under_review','investigating','linked','resolved','closed'].map(s => (
                <option key={s} value={s}>{s.replace(/_/g,' ')}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* AI Summary banner */}
      {complaint.ai_summary && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-xl flex gap-3">
          <Shield size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-blue-800 mb-0.5">AI Analysis Summary</p>
            <p className="text-sm text-blue-700">{complaint.ai_summary}</p>
          </div>
        </div>
      )}

      {/* Risk score bar */}
      <div className="ct-card p-4 mb-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex justify-between text-xs mb-1">
              <span className="font-medium text-slate-600">Risk Score</span>
              <span className="font-bold text-slate-800">{((complaint.risk_score || 0)*100).toFixed(1)}%</span>
            </div>
            <div className="risk-bar h-3">
              <div className="risk-bar-fill h-3" style={{
                width:`${(complaint.risk_score||0)*100}%`,
                background: complaint.risk_level==='critical'?'#DC2626':complaint.risk_level==='high'?'#EA580C':complaint.risk_level==='medium'?'#D97706':'#16A34A'
              }}/>
            </div>
          </div>
          <div className="flex gap-6 text-center text-xs">
            <div><p className="text-slate-400">Entities</p><p className="font-bold text-slate-700">{complaint.entity_count || 0}</p></div>
            <div><p className="text-slate-400">Linked Cases</p><p className="font-bold text-slate-700">{complaint.linked_case_ids?.length || 0}</p></div>
            {complaint.financial_loss && <div><p className="text-slate-400">Loss</p><p className="font-bold text-red-600">₹{complaint.financial_loss.toLocaleString()}</p></div>}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-white rounded-lg p-1 border border-slate-200 w-fit">
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${tab===t?'bg-blue-700 text-white':'text-slate-600 hover:bg-slate-100'}`}>
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="grid grid-cols-2 gap-4">
          <div className="ct-card p-5">
            <h3 className="font-semibold text-slate-700 mb-4">Complaint Details</h3>
            <dl className="space-y-3 text-sm">
              <div><dt className="text-slate-400 text-xs">Description</dt><dd className="text-slate-700 mt-1 leading-relaxed">{complaint.description}</dd></div>
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                <div><dt className="text-slate-400 text-xs">Category</dt><dd className="font-medium capitalize">{complaint.category?.replace(/_/g,' ')}</dd></div>
                <div><dt className="text-slate-400 text-xs">Language</dt><dd className="font-medium uppercase">{complaint.language}</dd></div>
                <div><dt className="text-slate-400 text-xs">Incident Date</dt><dd>{complaint.incident_date ? format(new Date(complaint.incident_date),'dd MMM yyyy') : '—'}</dd></div>
                <div><dt className="text-slate-400 text-xs">Submitted</dt><dd>{format(new Date(complaint.created_at),'dd MMM yyyy HH:mm')}</dd></div>
              </div>
            </dl>
          </div>
          <div className="ct-card p-5">
            <h3 className="font-semibold text-slate-700 mb-4">Victim Information</h3>
            <dl className="space-y-3 text-sm">
              {[
                ['Name', complaint.victim_name],
                ['Phone', complaint.victim_phone],
                ['Email', complaint.victim_email],
                ['Address', complaint.victim_address],
                ['Financial Loss', complaint.financial_loss ? `₹${complaint.financial_loss.toLocaleString()}` : null],
              ].map(([k, v]) => v ? (
                <div key={k}><dt className="text-slate-400 text-xs">{k}</dt><dd className="font-medium text-slate-700">{v}</dd></div>
              ) : null)}
            </dl>
          </div>
        </div>
      )}

      {tab === 'entities' && (
        <div className="ct-card">
          <div className="ct-card-header">
            <h3 className="font-semibold text-slate-700">Extracted Cyber Indicators</h3>
            <span className="badge bg-blue-100 text-blue-700">{entities?.length || 0} found</span>
          </div>
          <div className="p-4">
            {entities?.length ? (
              <div className="space-y-2">
                {entities.map(e => (
                  <div key={e.id} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                    <span className={`entity-${e.entity_type}`}>{ENTITY_LABELS[e.entity_type] || e.entity_type}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-sm font-semibold text-slate-800 break-all">{e.value}</p>
                      {e.normalized_value && e.normalized_value !== e.value && (
                        <p className="text-xs text-slate-400">Normalized: {e.normalized_value}</p>
                      )}
                      {e.context_snippet && <p className="text-xs text-slate-500 mt-1 italic truncate">{e.context_snippet}</p>}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-xs text-slate-400">Confidence</div>
                      <div className="font-mono text-sm font-bold text-slate-700">{(e.confidence*100).toFixed(0)}%</div>
                      <div className="text-xs text-slate-400">via {e.source}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-10 text-slate-400">
                <p>No entities extracted yet.</p>
                {isLEO && <button className="btn-primary mt-3 text-xs" onClick={() => processMut.mutate()}>Run AI Analysis</button>}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'related' && isLEO && (
        <div className="ct-card">
          <div className="ct-card-header">
            <h3 className="font-semibold text-slate-700">Linked Cases</h3>
            <span className="badge bg-orange-100 text-orange-700">{related?.length || 0} links</span>
          </div>
          <div className="p-4 space-y-3">
            {related?.map(link => (
              <div key={link.id} className="p-4 border border-orange-200 bg-orange-50 rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-sm font-bold text-blue-700">
                    {link.complaint_a_id === id ? link.complaint_b_id : link.complaint_a_id}
                  </span>
                  <div className="flex gap-2">
                    <span className="text-xs text-slate-500">Similarity: {(link.similarity_score*100).toFixed(0)}%</span>
                    <span className={`badge ${link.is_confirmed ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
                      {link.is_confirmed ? 'Confirmed' : 'Auto-detected'}
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {link.shared_entities?.map((e, i) => (
                    <span key={i} className={`entity-${e.type || 'keyword'} text-xs`}>
                      {e.value}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {!related?.length && <p className="text-center py-8 text-slate-400">No linked cases found yet.</p>}
          </div>
        </div>
      )}

      {tab === 'evidence' && (
        <div className="ct-card">
          <div className="ct-card-header">
            <h3 className="font-semibold text-slate-700">Evidence Files</h3>
            <button className="btn-secondary text-xs" onClick={() => fileRef.current?.click()}>
              <Upload size={13}/> Upload Evidence
            </button>
            <input ref={fileRef} type="file" className="hidden"
              onChange={e => e.target.files?.[0] && uploadMut.mutate(e.target.files[0])} />
          </div>
          <div className="p-4">
            {uploadMut.isPending && <p className="text-sm text-blue-600 mb-3">⏳ Processing evidence...</p>}
            <p className="text-sm text-slate-400 text-center py-8">Drag or click Upload to add screenshots, audio, or documents.</p>
          </div>
        </div>
      )}

      {tab === 'notes' && (
        <div className="ct-card">
          <div className="ct-card-header">
            <h3 className="font-semibold text-slate-700">Investigation Notes</h3>
          </div>
          <div className="p-4 space-y-3">
            {isLEO && (
              <div className="flex gap-2">
                <textarea className="ct-input flex-1 min-h-20 resize-none text-sm"
                  placeholder="Add investigation note..."
                  value={noteText} onChange={e => setNoteText(e.target.value)} />
                <button className="btn-primary self-end" disabled={!noteText.trim() || noteMut.isPending}
                  onClick={() => noteMut.mutate()}>Add</button>
              </div>
            )}
            {notes?.map(n => (
              <div key={n.id} className="p-3 bg-slate-50 rounded-lg border-l-4 border-blue-400">
                <p className="text-sm text-slate-700">{n.content}</p>
                <p className="text-xs text-slate-400 mt-1">{format(new Date(n.created_at),'dd MMM yyyy HH:mm')}</p>
              </div>
            ))}
            {!notes?.length && <p className="text-center text-slate-400 py-6">No notes yet.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
