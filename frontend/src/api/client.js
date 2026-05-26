import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({ baseURL: API_BASE });

// Attach JWT token to every request
client.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-logout on 401
client.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default client;

// Auth API
export const authAPI = {
  login: (email, password) => client.post('/auth/login', { email, password }),
  register: (data) => client.post('/auth/register', data),
  me: () => client.get('/auth/me'),
};

// Chat API
export const chatAPI = {
  send: (message, session_id, conversation_id) =>
    client.post('/chat', { message, session_id, conversation_id }),
  analyzeImage: (file, question) => {
    const form = new FormData();
    form.append('file', file);
    form.append('question', question);
    return client.post('/vision/analyze', form);
  },
};

// Tickets API
export const ticketsAPI = {
  list: (status) => client.get('/tickets/', { params: { status } }),
  get: (id) => client.get(`/tickets/${id}`),
  create: (data) => client.post('/tickets/', data),
  update: (id, data) => client.patch(`/tickets/${id}`, data),
  submitFeedback: (id, data) => client.post(`/tickets/${id}/feedback`, data),
};

// Analytics API
export const analyticsAPI = {
  overview: () => client.get('/analytics/overview'),
  byPriority: () => client.get('/analytics/tickets/by-priority'),
  byStatus: () => client.get('/analytics/tickets/by-status'),
  feedbackSummary: () => client.get('/analytics/feedback/summary'),
};