// GraphPage.jsx
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { graphAPI } from '../utils/api';
import { GitBranch, Target, Activity } from 'lucide-react';

export function GraphPage() {
  const [view, setView] = useState('stats');

  const { data: stats } = useQuery({
    queryKey: ['graph-stats'],
    queryFn: () => graphAPI.stats().then(r => r.data),
  });

  const { data: campaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => graphAPI.campaigns(2).then(r => r.data),
  });

  const { data: graphData } = useQuery({
    queryKey: ['graph-full'],
    queryFn: () => graphAPI.full(100).then(r => r.data),
    enabled: view === 'graph',
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Threat Intelligence Graph</h1>
          <p className="page-subtitle">Neo4j-powered entity relationship network</p>
        </div>
        <div className="flex gap-1 bg-white border border-slate-200 rounded-lg p-1">
          {['stats','campaigns','graph'].map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`px-3 py-1.5 text-sm rounded-md font-medium capitalize transition-colors
                ${view===v ? 'bg-blue-700 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
              {v}
            </button>
          ))}
        </div>
      </div>

      {view === 'stats' && (
        <div className="grid grid-cols-2 gap-4">
          <div className="ct-card p-6 col-span-2">
            <h3 className="font-semibold text-slate-700 mb-4">Graph Overview</h3>
            <div className="grid grid-cols-4 gap-6">
              {[
                { label: 'Complaint Nodes', value: stats?.total_complaints || 0, color: 'text-blue-700' },
                { label: 'Entity Nodes',    value: stats?.total_entities || 0,   color: 'text-purple-700' },
                { label: 'Relationships',   value: stats?.total_links || 0,      color: 'text-orange-600' },
                { label: 'Recurring Entities', value: stats?.recurring_entities || 0, color: 'text-red-600' },
              ].map(s => (
                <div key={s.label} className="text-center p-4 bg-slate-50 rounded-xl">
                  <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
                  <p className="text-xs text-slate-500 mt-1">{s.label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="ct-card p-5">
            <h3 className="font-semibold text-slate-700 mb-3">What the Graph Tracks</h3>
            <div className="space-y-2 text-sm text-slate-600">
              {[
                ['📞', 'Phone Numbers', 'Links complaints with same suspect numbers'],
                ['💳', 'UPI IDs', 'Tracks fraudulent payment identifiers across cases'],
                ['🌐', 'IP Addresses', 'Maps attacker infrastructure'],
                ['🔗', 'URLs & Domains', 'Identifies phishing campaign networks'],
                ['🏦', 'Bank Accounts', 'Connects financial fraud chains'],
                ['✉️', 'Email Addresses', 'Links impersonation and phishing attempts'],
              ].map(([icon, type, desc]) => (
                <div key={type} className="flex gap-3 p-2 rounded-lg hover:bg-slate-50">
                  <span className="text-lg">{icon}</span>
                  <div>
                    <p className="font-medium">{type}</p>
                    <p className="text-xs text-slate-400">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="ct-card p-5">
            <h3 className="font-semibold text-slate-700 mb-3">How Correlation Works</h3>
            <div className="space-y-3 text-sm">
              {[
                ['1', 'Entity Extraction', 'NLP/OCR pulls cyber indicators from every complaint'],
                ['2', 'Graph Ingestion', 'Entities and complaints become nodes; connections become edges'],
                ['3', 'Pattern Detection', 'Cypher queries find complaints sharing common entities'],
                ['4', 'Campaign Clustering', 'Multiple complaints with shared high-risk entities → campaign alert'],
                ['5', 'Risk Amplification', 'Entities appearing in multiple complaints get higher risk scores'],
              ].map(([n, title, desc]) => (
                <div key={n} className="flex gap-3">
                  <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center flex-shrink-0">{n}</span>
                  <div>
                    <p className="font-medium text-slate-700">{title}</p>
                    <p className="text-xs text-slate-400">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {view === 'campaigns' && (
        <div className="space-y-3">
          <div className="ct-card p-4 bg-amber-50 border-amber-200">
            <p className="text-sm text-amber-800">
              <strong>Detected campaigns</strong> are clusters of complaints sharing multiple entities — indicating organized criminal activity targeting multiple victims.
            </p>
          </div>
          {campaigns?.map((c, i) => (
            <div key={i} className="ct-card p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-semibold text-slate-800 capitalize">
                    {c.pivot_entity_type?.replace(/_/g,' ')} Cluster
                  </p>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">{c.pivot_entity_value}</p>
                </div>
                <div className="text-right">
                  <span className={`badge ${c.complaint_count >= 5 ? 'badge-critical' : c.complaint_count >= 3 ? 'badge-high' : 'badge-medium'}`}>
                    {c.complaint_count} complaints
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs text-center">
                <div className="bg-slate-50 rounded-lg p-2">
                  <p className="text-slate-400">Pivot Risk</p>
                  <p className="font-bold text-red-600">{((c.pivot_risk || 0)*100).toFixed(0)}%</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-2">
                  <p className="text-slate-400">Linked Entities</p>
                  <p className="font-bold text-purple-600">{c.correlated_entity_count}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-2">
                  <p className="text-slate-400">Category</p>
                  <p className="font-bold text-slate-700 capitalize">{c.categories?.[0]?.replace(/_/g,' ') || '—'}</p>
                </div>
              </div>
            </div>
          ))}
          {!campaigns?.length && (
            <div className="ct-card p-12 text-center">
              <Activity size={32} className="text-slate-300 mx-auto mb-3"/>
              <p className="text-slate-400">No campaigns detected yet. Submit more complaints to enable pattern detection.</p>
            </div>
          )}
        </div>
      )}

      {view === 'graph' && (
        <div className="ct-card p-6">
          <h3 className="font-semibold text-slate-700 mb-4">Entity-Complaint Network</h3>
          <div className="bg-slate-900 rounded-xl p-4 min-h-96 flex items-center justify-center">
            <div className="text-center text-slate-400">
              <GitBranch size={48} className="mx-auto mb-3 opacity-30"/>
              <p className="text-sm">Interactive graph visualization</p>
              <p className="text-xs mt-1 opacity-60">
                {graphData?.nodes?.length || 0} nodes · {graphData?.edges?.length || 0} edges
              </p>
              <p className="text-xs mt-3 text-slate-500">
                Connect Neo4j Bloom to your Neo4j instance for full visual exploration.<br/>
                URI: configured in .env → NEO4J_URI
              </p>
            </div>
          </div>
          {graphData?.nodes?.length > 0 && (
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Complaint Nodes ({graphData.nodes.filter(n=>n.type==='complaint').length})</h4>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {graphData.nodes.filter(n=>n.type==='complaint').slice(0,10).map((n,i) => (
                    <div key={i} className="flex items-center gap-2 text-xs p-1.5 bg-blue-50 rounded">
                      <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0"/>
                      <span className="font-mono">{n.label}</span>
                      <span className="text-slate-400 ml-auto">risk: {((n.risk||0)*100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Top Entity Nodes ({graphData.nodes.filter(n=>n.type!=='complaint').length})</h4>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {graphData.nodes.filter(n=>n.type!=='complaint').slice(0,10).map((n,i) => (
                    <div key={i} className="flex items-center gap-2 text-xs p-1.5 bg-purple-50 rounded">
                      <span className="w-2 h-2 rounded-full bg-purple-500 flex-shrink-0"/>
                      <span className={`entity-${n.type} text-xs`}>{n.type}</span>
                      <span className="font-mono truncate">{n.label}</span>
                      <span className="text-slate-400 ml-auto">×{n.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// IntelligencePage.jsx
export function IntelligencePage() {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchType, setSearchType] = useState('phone_number');
  const [searchVal, setSearchVal] = useState('');
  const [searchResult, setSearchResult] = useState(null);
  const { intelAPI } = require('../utils/api');

  const handleExtract = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const { data } = await intelAPI.extractText(text);
      setResult(data);
    } catch(e) { } finally { setLoading(false); }
  };

  const handleSearch = async () => {
    if (!searchVal.trim()) return;
    setLoading(true);
    try {
      const { intelAPI: api } = await import('../utils/api');
      const { data } = await api.searchEntity(searchType, searchVal);
      setSearchResult(data);
    } catch(e) { } finally { setLoading(false); }
  };

  const ENTITY_TYPES = ['phone_number','upi_id','email','url','ip_address','bank_account','social_handle','domain'];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Threat Intelligence</h1>
          <p className="page-subtitle">Ad-hoc entity extraction and entity search across all cases</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Text Extractor */}
        <div className="ct-card p-5">
          <h3 className="font-semibold text-slate-700 mb-4">Entity Extractor</h3>
          <p className="text-xs text-slate-500 mb-3">Paste any text — complaint, email, SMS, chat — to extract cyber indicators.</p>
          <textarea className="ct-input min-h-32 resize-none text-sm mb-3" placeholder="Paste text here..."
            value={text} onChange={e => setText(e.target.value)} />
          <button className="btn-primary w-full" onClick={handleExtract} disabled={loading || !text.trim()}>
            {loading ? 'Extracting...' : 'Extract Entities'}
          </button>
          {result && (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-semibold text-slate-500">{result.entity_count} entities found</p>
              {result.entities?.map((e, i) => (
                <div key={i} className="flex items-center gap-2 p-2 bg-slate-50 rounded-lg">
                  <span className={`entity-${e.entity_type}`}>{e.entity_type?.replace(/_/g,' ')}</span>
                  <span className="font-mono text-xs font-semibold text-slate-700 flex-1 break-all">{e.value}</span>
                  <span className="text-xs text-slate-400">{(e.confidence*100).toFixed(0)}%</span>
                </div>
              ))}
              {result.keywords?.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <p className="text-xs font-semibold text-slate-500 mb-2">Suspicious Keywords</p>
                  <div className="flex flex-wrap gap-1">
                    {result.keywords.map((k, i) => (
                      <span key={i} className="entity-chip bg-red-50 text-red-700 text-xs">{k.keyword}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Entity Search */}
        <div className="ct-card p-5">
          <h3 className="font-semibold text-slate-700 mb-4">Cross-Case Entity Search</h3>
          <p className="text-xs text-slate-500 mb-3">Search for a phone number, UPI ID, or email across all complaints in the system.</p>
          <div className="flex gap-2 mb-3">
            <select className="ct-select w-44 text-sm" value={searchType} onChange={e => setSearchType(e.target.value)}>
              {ENTITY_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g,' ')}</option>)}
            </select>
          </div>
          <input className="ct-input mb-3 text-sm" placeholder="Enter value to search..."
            value={searchVal} onChange={e => setSearchVal(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()} />
          <button className="btn-primary w-full" onClick={handleSearch} disabled={loading || !searchVal.trim()}>
            {loading ? 'Searching...' : 'Search Across All Cases'}
          </button>

          {searchResult && (
            <div className="mt-4 space-y-3">
              <p className="text-xs font-semibold text-slate-500">{searchResult.total} match(es)</p>
              {searchResult.graph_profile && Object.keys(searchResult.graph_profile).length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl">
                  <p className="text-xs font-semibold text-red-700 mb-1">Graph Profile</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span className="text-slate-500">Appearances: </span><span className="font-bold">{searchResult.graph_profile.total_appearances}</span></div>
                    <div><span className="text-slate-500">Risk: </span><span className="font-bold text-red-600">{((searchResult.graph_profile.risk_score||0)*100).toFixed(0)}%</span></div>
                  </div>
                </div>
              )}
              {searchResult.matches?.slice(0,5).map((m, i) => (
                <div key={i} className="p-2 bg-slate-50 rounded-lg text-xs">
                  <p className="font-mono font-semibold">{m.value}</p>
                  <p className="text-slate-400">Complaint: {m.complaint_id?.slice(0,8)}... · Risk: {(m.risk_score*100).toFixed(0)}%</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// AuditPage.jsx
export function AuditPage() {
  const { auditAPI } = require('../utils/api');
  const { useQuery } = require('@tanstack/react-query');
  const { format } = require('date-fns');
  const { data } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => auditAPI.logs({ limit: 100 }).then(r => r.data),
    refetchInterval: 30000,
  });

  const ACTION_COLOR = {
    USER_LOGIN: 'bg-green-100 text-green-700',
    USER_REGISTERED: 'bg-blue-100 text-blue-700',
    COMPLAINT_SUBMITTED: 'bg-purple-100 text-purple-700',
    COMPLAINT_UPDATED: 'bg-orange-100 text-orange-700',
    EVIDENCE_UPLOADED: 'bg-cyan-100 text-cyan-700',
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit Trail</h1>
          <p className="page-subtitle">Immutable log of all platform actions for accountability</p>
        </div>
      </div>
      <div className="ct-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="ct-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>User</th>
                <th>Resource</th>
                <th>IP Address</th>
              </tr>
            </thead>
            <tbody>
              {data?.map(log => (
                <tr key={log.id}>
                  <td><span className="text-xs font-mono">{format(new Date(log.created_at),'dd MMM HH:mm:ss')}</span></td>
                  <td><span className={`badge text-xs ${ACTION_COLOR[log.action] || 'bg-slate-100 text-slate-600'}`}>{log.action}</span></td>
                  <td><span className="text-xs font-mono text-slate-500">{log.user_id?.slice(0,8) || '—'}</span></td>
                  <td>
                    {log.resource_type && (
                      <span className="text-xs text-slate-600 font-medium">
                        {log.resource_type}: <span className="font-mono">{log.resource_id?.slice(0,8)}...</span>
                      </span>
                    )}
                  </td>
                  <td><span className="text-xs font-mono text-slate-400">{log.ip_address || '—'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default GraphPage;
