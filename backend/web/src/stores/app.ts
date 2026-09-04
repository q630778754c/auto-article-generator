import { create } from 'zustand';

interface AppState {
  username: string | null;
  token: string | null;
  alertCount: number;
  setAuth: (username: string, token: string) => void;
  clearAuth: () => void;
  setAlertCount: (count: number) => void;
  isAuthenticated: () => boolean;
}

export const useAppStore = create<AppState>((set, get) => ({
  username: localStorage.getItem('username'),
  token: localStorage.getItem('token'),
  alertCount: 0,
  setAuth: (username, token) => {
    localStorage.setItem('username', username);
    localStorage.setItem('token', token);
    set({ username, token });
  },
  clearAuth: () => {
    localStorage.removeItem('username');
    localStorage.removeItem('token');
    set({ username: null, token: null });
  },
  setAlertCount: (count) => set({ alertCount: count }),
  isAuthenticated: () => !!get().token,
}));