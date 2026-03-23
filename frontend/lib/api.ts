import axios from "axios";

// Empty string = use Next.js reverse proxy (/api/* → localhost:8000 via next.config.ts)
// Works for both local dev AND public ngrok/production URL without any changes
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Add auth token to admin requests
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("nutriveda_admin_token");
    if (token && config.url?.includes("/admin")) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const adminApi = {
  login: (username: string, password: string) =>
    api.post("/api/admin/login", { username, password }),

  getStats: () => api.get("/api/admin/stats"),

  getClients: () => api.get("/api/admin/clients"),

  getClientDetail: (id: number) => api.get(`/api/admin/clients/${id}`),

  getPlan: (planId: number) => api.get(`/api/admin/plans/${planId}`),

  updatePlan: (planId: number, data: { final_plan?: string; admin_notes?: string; status?: string }) =>
    api.patch(`/api/admin/plans/${planId}`, data),

  approvePlan: (planId: number) => api.post(`/api/admin/plans/${planId}/approve`),

  sendEmail: (planId: number) => api.post(`/api/admin/plans/${planId}/send-email`),

  regeneratePlan: (planId: number, extraInstructions?: string, chatMessages?: string[]) =>
    api.post(`/api/admin/plans/${planId}/regenerate`, {
      extra_instructions: extraInstructions || null,
      chat_messages: chatMessages || [],
    }),

  getPdfDownloadUrl: (planId: number) => `${API_BASE}/api/admin/plans/${planId}/pdf-download`,
  getWordDownloadUrl: (planId: number) => `${API_BASE}/api/admin/plans/${planId}/word-download`,
  getAdminDocUrl: (planId: number) => `${API_BASE}/api/admin/plans/${planId}/admin-doc-download`,

  chat: (message: string, planId: number | null, history: { role: string; content: string }[]) =>
    api.post("/api/admin/chat", { message, plan_id: planId, history }),

  getPriceConfig: (token: string) =>
    api.get("/api/admin/price-config", { headers: { Authorization: `Bearer ${token}` } }),

  updatePriceConfig: (token: string, price: number) =>
    api.put("/api/admin/price-config", { active_price_inr: price }, { headers: { Authorization: `Bearer ${token}` } }),
};

export const intakeApi = {
  submit: (formData: Record<string, unknown>) => api.post("/api/intake/submit", formData),
};

export const paymentApi = {
  getConfig: () => api.get("/api/payment/config"),
  createOrder: (submission_id: number, currency?: string) =>
    api.post("/api/payment/create-order", { submission_id, currency }),
  verify: (data: object) => api.post("/api/payment/verify", data),
};

export const adminPriceApi = {
  getConfig: (token: string) =>
    api.get("/api/admin/price-config", { headers: { Authorization: `Bearer ${token}` } }),
  updateConfig: (token: string, price: number) =>
    api.put("/api/admin/price-config", { active_price_inr: price }, { headers: { Authorization: `Bearer ${token}` } }),
};
