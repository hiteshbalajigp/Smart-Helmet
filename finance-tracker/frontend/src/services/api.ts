import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refreshToken = localStorage.getItem('refreshToken');
        const { data } = await axios.post(`${API_URL}/auth/refresh`, { refreshToken });
        localStorage.setItem('accessToken', data.data.accessToken);
        localStorage.setItem('refreshToken', data.data.refreshToken);
        original.headers.Authorization = `Bearer ${data.data.accessToken}`;
        return api(original);
      } catch {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth
export const authAPI = {
  register: (data: { name: string; email: string; password: string }) =>
    api.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
  googleLogin: (data: { googleId: string; email: string; name: string; avatar?: string }) =>
    api.post('/auth/google', data),
  logout: () => api.post('/auth/logout'),
  forgotPassword: (email: string) => api.post('/auth/forgot-password', { email }),
  resetPassword: (data: { token: string; password: string }) =>
    api.post('/auth/reset-password', data),
  getMe: () => api.get('/auth/me'),
  updateProfile: (data: Record<string, unknown>) => api.put('/auth/profile', data),
  deleteAccount: () => api.delete('/auth/account'),
};

// Dashboard
export const dashboardAPI = {
  getDashboard: () => api.get('/dashboard'),
  getAnalytics: (period?: string) => api.get('/analytics', { params: { period } }),
  getInsights: () => api.get('/insights'),
  getNotifications: () => api.get('/notifications'),
  markNotificationRead: (id: string) => api.put(`/notifications/${id}/read`),
  markAllRead: () => api.put('/notifications/read-all'),
};

// Transactions
export const transactionAPI = {
  search: (q: string, type?: string) => api.get('/search', { params: { q, type } }),
  // Income
  getIncome: (params?: Record<string, string>) => api.get('/income', { params }),
  createIncome: (data: Record<string, unknown>) => api.post('/income', data),
  updateIncome: (id: string, data: Record<string, unknown>) => api.put(`/income/${id}`, data),
  deleteIncome: (id: string) => api.delete(`/income/${id}`),
  // Expenses
  getExpenses: (params?: Record<string, string>) => api.get('/expenses', { params }),
  createExpense: (data: Record<string, unknown>) => api.post('/expenses', data),
  updateExpense: (id: string, data: Record<string, unknown>) => api.put(`/expenses/${id}`, data),
  deleteExpense: (id: string) => api.delete(`/expenses/${id}`),
  // Budgets
  getBudgets: () => api.get('/budgets'),
  createBudget: (data: Record<string, unknown>) => api.post('/budgets', data),
  updateBudget: (id: string, data: Record<string, unknown>) => api.put(`/budgets/${id}`, data),
  deleteBudget: (id: string) => api.delete(`/budgets/${id}`),
  // Goals
  getGoals: () => api.get('/goals'),
  createGoal: (data: Record<string, unknown>) => api.post('/goals', data),
  updateGoal: (id: string, data: Record<string, unknown>) => api.put(`/goals/${id}`, data),
  deleteGoal: (id: string) => api.delete(`/goals/${id}`),
  contributeGoal: (id: string, amount: number) => api.post(`/goals/${id}/contribute`, { amount }),
  // Investments
  getInvestments: () => api.get('/investments'),
  createInvestment: (data: Record<string, unknown>) => api.post('/investments', data),
  updateInvestment: (id: string, data: Record<string, unknown>) => api.put(`/investments/${id}`, data),
  deleteInvestment: (id: string) => api.delete(`/investments/${id}`),
};

// AI
export const aiAPI = {
  chat: (message: string, chatId?: string) => api.post('/ai/chat', { message, chatId }),
  getChats: () => api.get('/ai/chats'),
  getChat: (id: string) => api.get(`/ai/chats/${id}`),
  getMonthlyReport: () => api.get('/ai/monthly-report'),
  predictExpenses: () => api.get('/ai/predict-expenses'),
  whatIf: (data: { monthlySaving?: number; targetAmount: number; itemName?: string }) =>
    api.post('/ai/what-if', data),
  scanReceipt: (file: File) => {
    const formData = new FormData();
    formData.append('receipt', file);
    return api.post('/ai/scan-receipt', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Recurring
export const recurringAPI = {
  getAll: () => api.get('/recurring'),
  create: (data: Record<string, unknown>) => api.post('/recurring', data),
  update: (id: string, data: Record<string, unknown>) => api.put(`/recurring/${id}`, data),
  delete: (id: string) => api.delete(`/recurring/${id}`),
  generate: () => api.post('/recurring/generate'),
};

// Reports
export const reportAPI = {
  exportCSV: (params?: Record<string, string>) =>
    api.get('/reports/csv', { params, responseType: 'blob' }),
  getSummary: (period?: string) => api.get('/reports/summary', { params: { period } }),
};
