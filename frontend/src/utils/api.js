import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ───────────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  me:       ()     => api.get('/auth/me'),
};

// ── Complaints ─────────────────────────────────────────────────────────────
export const complaintsAPI = {
  list:       (params) => api.get('/complaints', { params }),
  get:        (id)     => api.get(`/complaints/${id}`),
  create:     (data)   => api.post('/complaints', data),
  update:     (id, d)  => api.patch(`/complaints/${id}`, d),
  process:    (id)     => api.post(`/complaints/${id}/process`),
  entities:   (id)     => api.get(`/complaints/${id}/entities`),
  related:    (id)     => api.get(`/complaints/${id}/related`),
  notes:      (id)     => api.get(`/complaints/${id}/notes`),
  addNote:    (id, d)  => api.post(`/complaints/${id}/notes`, d),
};

// ── Dashboard ──────────────────────────────────────────────────────────────
export const dashboardAPI = {
  stats:     ()        => api.get('/dashboard/stats'),
  recent:    (limit)   => api.get('/dashboard/recent-complaints', { params: { limit } }),
  priority:  (limit)   => api.get('/dashboard/priority-queue', { params: { limit } }),
  trends:    (days)    => api.get('/dashboard/trends', { params: { days } }),
};

// ── Graph ──────────────────────────────────────────────────────────────────
export const graphAPI = {
  full:       (limit)           => api.get('/graph/full', { params: { limit } }),
  network:    (id)              => api.get(`/graph/complaint/${id}/network`),
  entity:     (type, value)     => api.get(`/graph/entity/${type}/${encodeURIComponent(value)}/profile`),
  campaigns:  (min)             => api.get('/graph/campaigns', { params: { min_complaints: min } }),
  stats:      ()                => api.get('/graph/stats'),
};

// ── Intelligence ───────────────────────────────────────────────────────────
export const intelAPI = {
  searchEntity: (type, value) => api.get('/intelligence/search-entity', { params: { entity_type: type, value } }),
  extractText:  (text)        => api.post('/intelligence/extract-text', null, { params: { text } }),
  campaigns:    ()            => api.get('/intelligence/campaigns'),
};

// ── Evidence ───────────────────────────────────────────────────────────────
export const evidenceAPI = {
  upload: (complaintId, file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post(`/evidence/upload/${complaintId}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  list: (complaintId) => api.get(`/evidence/complaint/${complaintId}`),
};

// ── Audit ──────────────────────────────────────────────────────────────────
export const auditAPI = {
  logs: (params) => api.get('/audit/logs', { params }),
};
