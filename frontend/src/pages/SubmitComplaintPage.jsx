import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Shield, ArrowLeft, CheckCircle } from 'lucide-react';
import { complaintsAPI } from '../utils/api';
import toast from 'react-hot-toast';

const CATEGORIES = [
  { value:'financial_fraud',    label:'Financial Fraud' },
  { value:'phishing',           label:'Phishing / Fake Website' },
  { value:'identity_theft',     label:'Identity Theft' },
  { value:'cyberbullying',      label:'Cyberbullying / Harassment' },
  { value:'ransomware',         label:'Ransomware Attack' },
  { value:'hacking',            label:'Hacking / Unauthorized Access' },
  { value:'social_media_fraud', label:'Social Media Fraud' },
  { value:'upi_fraud',          label:'UPI / Payment Fraud' },
  { value:'otp_fraud',          label:'OTP Fraud' },
  { value:'investment_fraud',   label:'Investment / Trading Fraud' },
  { value:'other',              label:'Other Cybercrime' },
];

export default function SubmitComplaintPage() {
  const navigate = useNavigate();
  const [submitted, setSubmitted] = useState(null);
  const [form, setForm] = useState({
    title: '', description: '', category: 'upi_fraud',
    victim_name: '', victim_phone: '', victim_email: '',
    victim_address: '', financial_loss: '', incident_date: '',
    is_anonymous: false, language: 'en',
  });

  const f = k => ({ value: form[k], onChange: e => setForm({ ...form, [k]: e.target.value }) });

  const mutation = useMutation({
    mutationFn: () => complaintsAPI.create({
      ...form,
      financial_loss: form.financial_loss ? parseFloat(form.financial_loss) : null,
      incident_date: form.incident_date || null,
    }),
    onSuccess: r => setSubmitted(r.data),
    onError: err => toast.error(err.response?.data?.detail || 'Submission failed.'),
  });

  if (submitted) return (
    <div className="max-w-lg mx-auto text-center py-16">
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <CheckCircle size={32} className="text-green-600" />
      </div>
      <h2 className="text-2xl font-bold text-slate-800 mb-2">Complaint Submitted</h2>
      <p className="text-slate-500 mb-2">Your complaint has been registered successfully.</p>
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
        <p className="text-xs text-blue-500 mb-1">Complaint Reference Number</p>
        <p className="font-mono text-xl font-bold text-blue-800">{submitted.complaint_number}</p>
        <p className="text-xs text-blue-500 mt-1">Save this for future reference</p>
      </div>
      <p className="text-sm text-slate-500 mb-6">
        Our AI system is analyzing your complaint. An investigator will be assigned based on priority.
      </p>
      <div className="flex gap-3 justify-center">
        <button className="btn-secondary" onClick={() => navigate('/complaints')}>View My Complaints</button>
        <button className="btn-primary" onClick={() => navigate(`/complaints/${submitted.id}`)}>Track This Complaint</button>
      </div>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button className="btn-ghost p-2" onClick={() => navigate(-1)}><ArrowLeft size={18}/></button>
        <div>
          <h1 className="page-title">Submit Complaint</h1>
          <p className="page-subtitle">All information is kept confidential and securely encrypted</p>
        </div>
      </div>

      {/* Security notice */}
      <div className="flex gap-3 p-4 bg-blue-50 border border-blue-100 rounded-xl mb-6">
        <Shield size={18} className="text-blue-600 flex-shrink-0 mt-0.5"/>
        <p className="text-sm text-blue-700">
          Your complaint is encrypted with AES-256 and accessible only to authorized Cyber Crime Branch investigators.
        </p>
      </div>

      <div className="ct-card p-6 space-y-5">
        {/* Basic Info */}
        <div>
          <h3 className="font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Complaint Information</h3>
          <div className="space-y-4">
            <div>
              <label className="ct-label">Complaint Title <span className="text-red-500">*</span></label>
              <input className="ct-input" placeholder="Brief description of the cybercrime (e.g. Lost ₹50,000 via UPI fraud)" {...f('title')} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="ct-label">Crime Category <span className="text-red-500">*</span></label>
                <select className="ct-select" {...f('category')}>
                  {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="ct-label">Language</label>
                <select className="ct-select" {...f('language')}>
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                  <option value="mr">Marathi</option>
                  <option value="gu">Gujarati</option>
                </select>
              </div>
            </div>
            <div>
              <label className="ct-label">Detailed Description <span className="text-red-500">*</span></label>
              <textarea className="ct-input min-h-32 resize-none"
                placeholder="Describe exactly what happened. Include any phone numbers, UPI IDs, websites, names, account numbers, or other details related to the fraud. The more detail you provide, the better our AI can identify patterns and link to other cases."
                {...f('description')} required />
              <p className="text-xs text-slate-400 mt-1">Include all suspicious numbers, IDs, URLs, or account details mentioned by the fraudster.</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="ct-label">Date of Incident</label>
                <input className="ct-input" type="datetime-local" {...f('incident_date')} />
              </div>
              <div>
                <label className="ct-label">Financial Loss (₹)</label>
                <input className="ct-input" type="number" min="0" placeholder="0" {...f('financial_loss')} />
              </div>
            </div>
          </div>
        </div>

        {/* Victim Info */}
        <div>
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
            <h3 className="font-semibold text-slate-700">Victim Information</h3>
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" checked={form.is_anonymous}
                onChange={e => setForm({ ...form, is_anonymous: e.target.checked })} />
              Submit anonymously
            </label>
          </div>
          {!form.is_anonymous && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="ct-label">Full Name</label>
                <input className="ct-input" placeholder="Your full name" {...f('victim_name')} />
              </div>
              <div>
                <label className="ct-label">Phone Number</label>
                <input className="ct-input" type="tel" placeholder="+91 98765 43210" {...f('victim_phone')} />
              </div>
              <div>
                <label className="ct-label">Email Address</label>
                <input className="ct-input" type="email" placeholder="your@email.com" {...f('victim_email')} />
              </div>
              <div>
                <label className="ct-label">Address / City</label>
                <input className="ct-input" placeholder="City, State" {...f('victim_address')} />
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 pt-2 border-t border-slate-100">
          <button className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
          <button className="btn-primary px-8" disabled={mutation.isPending || !form.title || !form.description}
            onClick={() => mutation.mutate()}>
            {mutation.isPending ? 'Submitting...' : 'Submit Complaint'}
          </button>
        </div>
      </div>
    </div>
  );
}
