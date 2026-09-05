import { create } from 'zustand';

interface AppState {
  username: string | null;
  token: string | null;
  tokenType: string | null;
  email: string | null;
  alertCount: number;
  setAuth: (username: string, token: string, tokenType?: string, email?: string) => void;
  clearAuth: () => void;
  setAlertCount: (count: number) => void;
  isAuthenticated: () => boolean;
}

export const useAppStore = create<AppState>((set, get) => ({
  username: localStorage.getItem('username'),
  token: localStorage.getItem('token'),
  tokenType: localStorage.getItem('token_type'),
  email: localStorage.getItem('email'),
  alertCount: 0,
  setAuth: (username, token, tokenType = 'local', email = '') => {
    localStorage.setItem('username', username);
    localStorage.setItem('token', token);
    localStorage.setItem('token_type', tokenType);
    if (email) localStorage.setItem('email', email);
    set({ username, token, tokenType, email: email || null });
  },
  clearAuth: () => {
    localStorage.removeItem('username');
    localStorage.removeItem('token');
    localStorage.removeItem('token_type');
    localStorage.removeItem('email');
    set({ username: null, token: null, tokenType: null, email: null });
  },
  setAlertCount: (count) => set({ alertCount: count }),
  isAuthenticated: () => !!get().token,
}));
