import { create } from "zustand";
import { authAPI } from "../api/client";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "agent" | "user";
  preferred_language: string;
}

interface AuthStore {
  user: User | null;
  isLoading: boolean;
  setAuth: (user: User, accessToken: string, refreshToken?: string) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadMe: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isLoading: false,

  setAuth: (user, accessToken, refreshToken) => {
    localStorage.setItem("access_token", accessToken);
    if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
    set({ user, isLoading: false });
  },

  login: async (email, password) => {
    set({ isLoading: true });
    const { data } = await authAPI.login(email, password);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    const me = await authAPI.me();
    set({ user: me.data, isLoading: false });
  },

  logout: () => {
    localStorage.clear();
    set({ user: null });
  },

  loadMe: async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    set({ isLoading: true });
    try {
      const { data } = await authAPI.me();
      set({ user: data });
    } catch {
      localStorage.clear();
    } finally {
      set({ isLoading: false });
    }
  },
}));
