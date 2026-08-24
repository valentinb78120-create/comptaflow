import axios from "axios";
import type { Invoice, InvoicePatch } from "../types/invoice";

const BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

const client = axios.create({ baseURL: BASE });

const TOKEN_KEY = "comptaflow_token";

export const tokenStore = {
  get: (): string | null => localStorage.getItem(TOKEN_KEY),
  set: (token: string): void => localStorage.setItem(TOKEN_KEY, token),
  clear: (): void => localStorage.removeItem(TOKEN_KEY),
};

// Toutes les requêtes portent le token quand il existe
client.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export interface Cabinet {
  id: string;
  name: string;
  email: string;
  siret: string | null;
  subscription_active: boolean;
  trial_ends_at: string | null;
  is_admin: boolean;
  plan: string;
  created_at: string;
}

export const PLAN_LABELS: Record<string, string> = {
  decouverte: "Découverte",
  cabinet: "Cabinet",
  cabinet_plus: "Cabinet+",
  illimite: "Illimité",
};

export interface PlatformStats {
  cabinets_total: number;
  cabinets_subscribed: number;
  cabinets_in_trial: number;
  invoices_total: number;
  invoices_last_7d: number;
  invoices_by_status: Record<string, number>;
}

export interface AdminCabinetRow extends Cabinet {
  invoice_count: number;
}

/** URL directe du fichier original (aperçu PDF/image). */
export function invoiceFileUrl(id: string): string {
  return `${BASE}/invoices/${id}/file`;
}

/**
 * Déclenche le téléchargement d'un blob.
 * Lien attaché au DOM + révocation différée de l'URL, sinon Chrome
 * peut annuler le téléchargement (race condition).
 */
function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 1000);
}


export interface AuthResponse {
  token: string;
  cabinet: Cabinet;
}

export interface BillingStatus {
  cabinet_id: string;
  subscription_active: boolean;
  trial_active: boolean;
  trial_ends_at: string | null;
  has_access: boolean;
  stripe_configured: boolean;
  plan: string;
  plan_label: string;
  plan_price_eur: number | null;
  monthly_limit: number | null;
  monthly_used: number;
}

export interface PCGRule {
  keywords: string[];
  account: string;
  label: string;
}

export interface StandardPCGRule extends PCGRule {
  key: string;
}

export interface CustomPCGRule extends PCGRule {
  id: string;
}

export type ExportFormat = "ebp" | "sage50" | "fec";

export const api = {
  // --- Auth ---
  register: async (payload: { name: string; email: string; password: string; siret?: string }): Promise<AuthResponse> => {
    const { data } = await client.post<AuthResponse>("/auth/register", payload);
    return data;
  },

  login: async (payload: { email: string; password: string }): Promise<AuthResponse> => {
    const { data } = await client.post<AuthResponse>("/auth/login", payload);
    return data;
  },

  me: async (): Promise<Cabinet> => {
    const { data } = await client.get<Cabinet>("/auth/me");
    return data;
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await client.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },

  // --- Règles PCG personnalisées ---
  customRules: async (): Promise<CustomPCGRule[]> => {
    const { data } = await client.get<CustomPCGRule[]>("/pcg-rules/custom");
    return data;
  },

  createCustomRule: async (rule: PCGRule): Promise<CustomPCGRule> => {
    const { data } = await client.post<CustomPCGRule>("/pcg-rules/custom", rule);
    return data;
  },

  deleteCustomRule: async (id: string): Promise<void> => {
    await client.delete(`/pcg-rules/custom/${id}`);
  },

  // --- Billing & PCG ---
  billingStatus: async (cabinetId: string): Promise<BillingStatus> => {
    const { data } = await client.get<BillingStatus>("/billing/status", { params: { cabinet_id: cabinetId } });
    return data;
  },

  // --- Admin ---
  adminStats: async (): Promise<PlatformStats> => {
    const { data } = await client.get<PlatformStats>("/admin/stats");
    return data;
  },

  adminCabinets: async (): Promise<AdminCabinetRow[]> => {
    const { data } = await client.get<AdminCabinetRow[]>("/admin/cabinets");
    return data;
  },

  adminExtendTrial: async (cabinetId: string, days = 14): Promise<Cabinet> => {
    const { data } = await client.post<Cabinet>(`/admin/cabinets/${cabinetId}/extend-trial`, null, { params: { days } });
    return data;
  },

  adminToggleSubscription: async (cabinetId: string): Promise<Cabinet> => {
    const { data } = await client.post<Cabinet>(`/admin/cabinets/${cabinetId}/toggle-subscription`);
    return data;
  },

  adminSetPlan: async (cabinetId: string, plan: string): Promise<Cabinet> => {
    const { data } = await client.post<Cabinet>(`/admin/cabinets/${cabinetId}/set-plan`, null, { params: { plan } });
    return data;
  },

  pcgRules: async (): Promise<StandardPCGRule[]> => {
    const { data } = await client.get<StandardPCGRule[]>("/pcg-rules/");
    return data;
  },

  disabledRules: async (): Promise<string[]> => {
    const { data } = await client.get<string[]>("/pcg-rules/disabled");
    return data;
  },

  toggleStandardRule: async (key: string): Promise<{ key: string; disabled: boolean }> => {
    const { data } = await client.post<{ key: string; disabled: boolean }>("/pcg-rules/standard/toggle", { key });
    return data;
  },

  createCabinet: async (payload: { name: string; email: string; siret?: string }): Promise<Cabinet> => {
    const { data } = await client.post<Cabinet>("/cabinets/", payload);
    return data;
  },

  getCabinet: async (id: string): Promise<Cabinet> => {
    const { data } = await client.get<Cabinet>(`/cabinets/${id}`);
    return data;
  },

  uploadInvoice: async (file: File, cabinetId: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("cabinet_id", cabinetId);
    const { data } = await client.post<{ id: string; status: string; message: string }>(
      "/invoices/upload",
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },

  listInvoices: async (cabinetId: string, status?: string): Promise<Invoice[]> => {
    const params: Record<string, string> = { cabinet_id: cabinetId };
    if (status) params.status = status;
    const { data } = await client.get<Invoice[]>("/invoices/", { params });
    return data;
  },

  getInvoice: async (id: string): Promise<Invoice> => {
    const { data } = await client.get<Invoice>(`/invoices/${id}`);
    return data;
  },

  patchInvoice: async (id: string, patch: InvoicePatch): Promise<Invoice> => {
    const { data } = await client.patch<Invoice>(`/invoices/${id}`, patch);
    return data;
  },

  reprocessInvoice: async (id: string): Promise<void> => {
    await client.post(`/invoices/${id}/reprocess`);
  },

  exportInvoice: async (id: string, format: "ebp" | "sage50") => {
    const response = await client.post(`/invoices/${id}/export`, null, {
      params: { format },
      responseType: "blob",
    });
    triggerDownload(response.data, `export_${format}_${id.slice(0, 8)}.csv`);
  },

  exportBulk: async (cabinetId: string, format: ExportFormat) => {
    const response = await client.post("/invoices/export/bulk", null, {
      params: { cabinet_id: cabinetId, format },
      responseType: "blob",
    });
    const ext = format === "fec" ? "txt" : "csv";
    triggerDownload(response.data, `export_${format}_global.${ext}`);
  },
};
