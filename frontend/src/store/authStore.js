import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('access_token'),

  login: (tokenData) => {
    const user = {
      id: tokenData.user_id,
      role: tokenData.role,
      full_name: tokenData.full_name,
    };
    localStorage.setItem('access_token', tokenData.access_token);
    localStorage.setItem('user', JSON.stringify(user));
    set({ user, token: tokenData.access_token });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    set({ user: null, token: null });
  },

  isInvestigator: () => {
    const { user } = useAuthStore.getState();
    return user && ['investigator', 'supervisor', 'admin'].includes(user.role);
  },
}));
