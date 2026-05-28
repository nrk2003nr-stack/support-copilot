/**
 * api/client.js
 * Central Axios instance + all API helper functions.
 * Auto-attaches JWT, auto-redirects on 401.
 */

import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({ baseURL: API_BASE })

// Attach JWT to every request
client.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
client.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default client

// ── Auth ──────────────────────────────────────────────────────────────────
export const authAPI = {
  login:    (email, password)   => client.post('/auth/login',    { email, password }),
  register: (data)              => client.post('/auth/register', data),
  me:       ()                  => client.get('/auth/me'),
  logout:   ()                  => client.post('/auth/logout'),
  refresh:  ()                  => client.post('/auth/refresh'),
}

// ── Chat ──────────────────────────────────────────────────────────────────
export const chatAPI = {
  send: (message, session_id, conversation_id) =>
    client.post('/chat', { message, session_id, conversation_id }),

  analyzeImage: (file, question) => {
    const form = new FormData()
    form.append('file', file)
    form.append('question', question)
    return client.post('/vision/analyze', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  transcribe: (file) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/voice/transcribe', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// ── Tickets ───────────────────────────────────────────────────────────────
export const ticketsAPI = {
  list:           (status)      => client.get('/tickets/',          { params: status ? { status } : {} }),
  get:            (id)          => client.get(`/tickets/${id}`),
  timeline:       (id)          => client.get(`/tickets/${id}/timeline`),
  create:         (data)        => client.post('/tickets/',          data),
  update:         (id, data)    => client.patch(`/tickets/${id}`,    data),
  assign:         (id)          => client.post(`/tickets/${id}/assign`),
  comment:        (id, body)    => client.post(`/tickets/${id}/comments`, { body }),
  submitFeedback: (id, data)    => client.post(`/tickets/${id}/feedback`, data),
}

// ── Analytics ─────────────────────────────────────────────────────────────
export const analyticsAPI = {
  overview:        () => client.get('/analytics/overview'),
  byPriority:      () => client.get('/analytics/tickets/by-priority'),
  byStatus:        () => client.get('/analytics/tickets/by-status'),
  feedbackSummary: () => client.get('/analytics/feedback/summary'),
  channelMix:      () => client.get('/analytics/channels/mix'),
}

// ── Handoff ───────────────────────────────────────────────────────────────
export const handoffAPI = {
  escalate: (conversationId) => client.post(`/handoff/escalate/${conversationId}`),
  takeover: (ticketId) => client.post(`/handoff/tickets/${ticketId}/takeover`),
  resumeBot: (ticketId) => client.post(`/handoff/tickets/${ticketId}/resume-bot`),
}

export const channelsAPI = {
  status: () => client.get('/channels/status'),
  send: (provider, data) => client.post(`/channels/${provider}/send`, data),
}

export const knowledgeAPI = {
  list: (status) => client.get('/knowledge/', { params: status ? { status } : {} }),
  create: (data) => client.post('/knowledge/', data),
  update: (id, data) => client.patch(`/knowledge/${id}`, data),
  remove: (id) => client.delete(`/knowledge/${id}`),
}

export const adminAPI = {
  users: () => client.get('/admin/users'),
  createUser: (data) => client.post('/admin/users', data),
  updateUser: (id, data) => client.patch(`/admin/users/${id}`, data),
  config: () => client.get('/admin/config'),
}
