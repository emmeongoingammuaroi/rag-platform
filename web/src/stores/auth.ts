import { create } from "zustand";
import { api, ApiError } from "../lib/api";
import type { User } from "../lib/types";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("token"),
  isLoading: true,
  isAuthenticated: !!localStorage.getItem("token"),

  login: async (email, password) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const res = await fetch(
      `${import.meta.env.VITE_API_URL || "http://localhost:8010"}/api/v1/auth/login`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      },
    );

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(
        res.status,
        body.detail || "login_failed",
        body.detail || "Invalid credentials",
      );
    }

    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    set({ token: data.access_token, isAuthenticated: true });
    await get().fetchUser();
  },

  register: async (email, password) => {
    await api.post("/api/v1/auth/register", { email, password });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ user: null, token: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    try {
      const user = await api.get<User>("/api/v1/users/me");
      set({ user, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
      localStorage.removeItem("token");
    }
  },

  initialize: async () => {
    const token = localStorage.getItem("token");
    if (token) {
      await get().fetchUser();
    }
    set({ isLoading: false });
  },
}));
