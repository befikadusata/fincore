'use client';

import { create } from 'zustand';
import { setTheme as applyTheme, getTheme } from '@/lib/theme';
import type { Theme } from '@/lib/theme';

interface UIState {
  sidebarOpen: boolean;
  theme: Theme;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTheme: (theme: Theme) => void;
}

export const useUIStore = create<UIState>()((set) => ({
  sidebarOpen: true,
  theme: 'light',
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
}));

/** Sync the store's theme field with the DOM-applied theme on mount. */
export function syncThemeStore() {
  useUIStore.setState({ theme: getTheme() });
}
