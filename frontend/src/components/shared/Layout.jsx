import React, { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import {
  Shield, LayoutDashboard, FileText, GitBranch,
  Brain, ClipboardList, LogOut, Menu, X, Bell, User, ChevronRight
} from 'lucide-react';

const NAV = [
  { to: '/dashboard',    icon: LayoutDashboard, label: 'Dashboard',        roles: ['all'] },
  { to: '/complaints',   icon: FileText,         label: 'Complaints',       roles: ['all'] },
  { to: '/graph',        icon: GitBranch,        label: 'Threat Graph',     roles: ['investigator','supervisor','admin'] },
  { to: '/intelligence', icon: Brain,            label: 'Intelligence',     roles: ['investigator','supervisor','admin'] },
  { to: '/audit',        icon: ClipboardList,    label: 'Audit Trail',      roles: ['investigator','supervisor','admin'] },
];

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => { logout(); navigate('/login'); };

  const visibleNav = NAV.filter(n =>
    n.roles.includes('all') || n.roles.includes(user?.role)
  );

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      {/* Sidebar */}
      <aside className={`flex-shrink-0 flex flex-col bg-white border-r border-slate-200 transition-all duration-200 ${sidebarOpen ? 'w-60' : 'w-16'}`}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-slate-100">
          <div className="w-8 h-8 bg-blue-700 rounded-lg flex items-center justify-center flex-shrink-0">
            <Shield size={16} className="text-white" />
          </div>
          {sidebarOpen && (
            <div>
              <p className="text-sm font-bold text-blue-800 leading-tight">CyberTrace AI</p>
              <p className="text-xs text-slate-400">Smart Policing</p>
            </div>
          )}
        </div>

        {/* Nav Items */}
        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {visibleNav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
            >
              <Icon size={18} className="flex-shrink-0" />
              {sidebarOpen && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User Info */}
        <div className="p-3 border-t border-slate-100">
          {sidebarOpen ? (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <User size={14} className="text-blue-700" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-700 truncate">{user?.full_name}</p>
                <p className="text-xs text-slate-400 capitalize">{user?.role}</p>
              </div>
              <button onClick={handleLogout} className="p-1 text-slate-400 hover:text-red-500 transition-colors" title="Logout">
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <button onClick={handleLogout} className="w-full flex justify-center p-1 text-slate-400 hover:text-red-500">
              <LogOut size={16} />
            </button>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex-shrink-0 bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100">
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <span className={`badge ${
              user?.role === 'admin' ? 'bg-red-100 text-red-700' :
              user?.role === 'supervisor' ? 'bg-purple-100 text-purple-700' :
              user?.role === 'investigator' ? 'bg-blue-100 text-blue-700' :
              'bg-green-100 text-green-700'
            } capitalize`}>
              {user?.role}
            </span>
            <button
              onClick={() => navigate('/complaints/new')}
              className="btn-primary text-xs py-1.5"
            >
              + New Complaint
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
