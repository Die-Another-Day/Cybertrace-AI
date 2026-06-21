import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './store/authStore';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ComplaintsPage from './pages/ComplaintsPage';
import ComplaintDetailPage from './pages/ComplaintDetailPage';
import SubmitComplaintPage from './pages/SubmitComplaintPage';
import GraphPage from './pages/GraphPage';
import IntelligencePage from './pages/IntelligencePage';
import AuditPage from './pages/AuditPage';
import Layout from './components/shared/Layout';

import './styles/index.css';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30000 } },
});

function PrivateRoute({ children }) {
  const { token } = useAuthStore();
  return token ? children : <Navigate to="/login" replace />;
}

function InvestigatorRoute({ children }) {
  const { user } = useAuthStore();
  const allowed = ['investigator', 'supervisor', 'admin'];
  return user && allowed.includes(user.role)
    ? children
    : <Navigate to="/dashboard" replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
        <Routes>
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard"          element={<DashboardPage />} />
            <Route path="complaints"         element={<ComplaintsPage />} />
            <Route path="complaints/new"     element={<SubmitComplaintPage />} />
            <Route path="complaints/:id"     element={<ComplaintDetailPage />} />
            <Route path="graph"              element={<InvestigatorRoute><GraphPage /></InvestigatorRoute>} />
            <Route path="intelligence"       element={<InvestigatorRoute><IntelligencePage /></InvestigatorRoute>} />
            <Route path="audit"              element={<InvestigatorRoute><AuditPage /></InvestigatorRoute>} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
