'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { setAuthCookie, clearAuthCookie } from '@/lib/auth-cookie';

export interface AuthUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  setAuth: (user: AuthUser, accessToken: string, refreshToken: string) => void;
  setAccessToken: (token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      setAuth: (user, accessToken, refreshToken) => {
        setAuthCookie(accessToken);
        set({ user, accessToken, refreshToken });
      },
      setAccessToken: (token) => {
        setAuthCookie(token);
        set({ accessToken: token });
      },
      clearAuth: () => {
        clearAuthCookie();
        set({ user: null, accessToken: null, refreshToken: null });
      },
    }),
    { name: 'fincore-auth' },
  ),
);
