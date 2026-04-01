import { create } from "zustand";
import { persist } from "zustand/middleware";
import { getCurrentUser, UserInfo, login, LoginRequest, register, RegisterRequest } from "@/lib/api/auth";

interface AuthStore {
  user: UserInfo | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;

  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,
      isAuthenticated: false,

      login: async (data: LoginRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await login(data);
          set({ token: response.access_token, isLoading: false });
          await get().fetchUser();
        } catch (error: any) {
          set({
            error: error.message || "登录失败",
            isLoading: false,
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        try {
          await register(data);
          // 注册成功后自动登录
          await get().login({ username: data.username, password: data.password });
        } catch (error: any) {
          set({
            error: error.message || "注册失败",
            isLoading: false,
          });
          throw error;
        }
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false, error: null });
      },

      fetchUser: async () => {
        const token = get().token;
        if (!token) {
          set({ isAuthenticated: false, user: null });
          return;
        }

        set({ isLoading: true });
        try {
          const user = await getCurrentUser();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
          set({ user: null, isAuthenticated: false, isLoading: false, token: null });
        }
      },

      checkAuth: async () => {
        const token = get().token;
        if (!token) {
          return false;
        }
        await get().fetchUser();
        return get().isAuthenticated;
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
);