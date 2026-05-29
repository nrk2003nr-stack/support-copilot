import axios from "axios";

const API_ORIGIN = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const API_BASE_URL = API_ORIGIN
  ? (API_ORIGIN.endsWith("/api") ? API_ORIGIN : `${API_ORIGIN}/api`)
  : "/api";

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  // Accept either an object { email, password } or two args (email, password)
  login: (dataOrEmail: any, password?: string) => {
    const payload = typeof dataOrEmail === "object" ? dataOrEmail : { email: dataOrEmail, password };
    return api.post("/auth/login", payload);
  },
  register: async (data: any) => {
    const res = await api.post("/auth/register", data);
    // Some backend implementations return tokens on register, others only return the user.
    // If tokens aren't returned, automatically log the user in to obtain tokens.
    if (res.data && res.data.access_token) return res;
    return api.post("/auth/login", { email: data.email, password: data.password });
  },
  me: () => api.get("/auth/me"),
  logout: () => {
    // keep interface but also clear client-side tokens
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    return Promise.resolve();
  },
};

// backward-compatible alias (some files imported `authApi`)
export const authApi = authAPI;

export const ticketsAPI = {
  getAll: () => api.get("/tickets"),
  getById: (id: string) => api.get(`/tickets/${id}`),
  create: (data: any) => api.post("/tickets", data),
  update: (id: string, data: any) => api.patch(`/tickets/${id}`, data),
  delete: (id: string) => api.delete(`/tickets/${id}`),
  // Aliases / additional endpoints used across components
  list: (status?: string) => api.get("/tickets", { params: status ? { status } : {} }),
  assign: (id: string) => api.post(`/tickets/${id}/assign`),
  timeline: (id: string) => api.get(`/tickets/${id}/timeline`),
  comment: (id: string, body: any) => api.post(`/tickets/${id}/comments`, { body }),
  messageFeedback: (ticketId: string, messageId: string, payload: any) => api.post(`/tickets/${ticketId}/messages/${messageId}/feedback`, payload),
  submitFeedback: (ticketId: string, payload: any) => api.post(`/tickets/${ticketId}/csat`, {
    score: payload.score ?? payload.rating ?? (payload.thumbs_up ? 5 : 2),
    comment: payload.comment,
  }),
};

export const chatAPI = {
  sendMessage: (data: any) => api.post("/chat", data),
  getMessages: (ticketId: string) => api.get(`/chat/${ticketId}`),
  // compatibility aliases
  // Send a message to a ticket (used by chat widget)
  send: (ticket_id: string | number, message: string) => api.post(`/tickets/${ticket_id}/messages`, { content: message }),
  analyzeImage: (file: File, caption?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (caption) form.append('caption', caption);
    return api.post('/chat/analyze-image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  transcribe: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/voice/transcribe', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
};

export const adminAPI = {
  getUsers: () => api.get("/admin/users"),
  getDashboard: () => api.get("/admin/dashboard"),
};

export const channelsAPI = {
  getAll: () => api.get("/channels"),
  create: (data: any) => api.post("/channels", data),
};

export const knowledgeAPI = {
  getAll: () => api.get("/knowledge"),
  create: (data: any) => api.post("/knowledge", data),
};

export const analyticsAPI = {
  getDashboard: () => api.get("/analytics/dashboard"),
  overview: () => api.get("/analytics/overview"),
  byStatus: () => api.get("/analytics/tickets/by-status"),
  byPriority: () => api.get("/analytics/tickets/by-priority"),
  channelMix: () => api.get("/analytics/channels/mix"),
};

export default api;
