import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, Eye, EyeOff } from 'lucide-react';
import { authAPI } from '../utils/api';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [form, setForm] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authAPI.login(form);
      login(data);
      toast.success(`Welcome back, ${data.full_name}`);
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Shield size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">CyberTrace AI</h1>
          <p className="text-blue-300 text-sm mt-1">Cyber Crime Investigation Platform</p>
        </div>

        {/* Form card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-xl font-bold text-slate-800 mb-6">Sign In</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="ct-label">Email Address</label>
              <input className="ct-input" type="email" placeholder="officer@cybercrime.gov.in"
                value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required />
            </div>
            <div>
              <label className="ct-label">Password</label>
              <div className="relative">
                <input className="ct-input pr-10" type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <button className="btn-primary w-full justify-center py-2.5 mt-2" type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          <p className="text-center text-sm text-slate-500 mt-6">
            No account?{' '}
            <Link to="/register" className="text-blue-600 font-medium hover:underline">Register here</Link>
          </p>
        </div>

        <p className="text-center text-xs text-blue-400 mt-6">
          Secure platform for authorized personnel only.
        </p>
      </div>
    </div>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', password: '',
    role: 'citizen', badge_number: '', department: '', preferred_language: 'en',
  });
  const [loading, setLoading] = useState(false);

  const isLEO = ['investigator', 'supervisor', 'admin'].includes(form.role);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authAPI.register(form);
      toast.success('Account created. Please sign in.');
      navigate('/login');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const f = (k) => ({ value: form[k], onChange: e => setForm({ ...form, [k]: e.target.value }) });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-6">
          <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-3">
            <Shield size={22} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">CyberTrace AI</h1>
          <p className="text-blue-300 text-sm">Create Account</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="ct-label">Full Name</label>
                <input className="ct-input" placeholder="Inspector Sharma" {...f('full_name')} required />
              </div>
              <div>
                <label className="ct-label">Email</label>
                <input className="ct-input" type="email" {...f('email')} required />
              </div>
              <div>
                <label className="ct-label">Phone</label>
                <input className="ct-input" type="tel" placeholder="+91 98765 43210" {...f('phone')} />
              </div>
              <div className="col-span-2">
                <label className="ct-label">Password</label>
                <input className="ct-input" type="password" placeholder="Min 8 chars, 1 uppercase, 1 digit" {...f('password')} required />
              </div>
              <div>
                <label className="ct-label">Account Type</label>
                <select className="ct-select" {...f('role')}>
                  <option value="citizen">Citizen</option>
                  <option value="investigator">Investigator</option>
                  <option value="supervisor">Supervisor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <label className="ct-label">Preferred Language</label>
                <select className="ct-select" {...f('preferred_language')}>
                  <option value="en">English</option>
                  <option value="hi">हिंदी (Hindi)</option>
                  <option value="mr">मराठी (Marathi)</option>
                  <option value="gu">ગુજરાતી (Gujarati)</option>
                </select>
              </div>
              {isLEO && (<>
                <div>
                  <label className="ct-label">Badge Number <span className="text-red-500">*</span></label>
                  <input className="ct-input" placeholder="CCB/2024/001" {...f('badge_number')} required={isLEO} />
                </div>
                <div>
                  <label className="ct-label">Department</label>
                  <input className="ct-input" placeholder="Cyber Crime Branch" {...f('department')} />
                </div>
              </>)}
            </div>
            <button className="btn-primary w-full justify-center py-2.5 mt-2" type="submit" disabled={loading}>
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>
          <p className="text-center text-sm text-slate-500 mt-4">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-600 font-medium hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
