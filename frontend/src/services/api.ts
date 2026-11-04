// Клиент REST API: токен доступа, обработка ошибок, вызовы ресурсов
import type {
  AuditEntry, DetectionResult, Heatmap, ImportBatch, ImportResult,
  NotificationItem, Overview, Period, Preview, Report, Risk, User,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";
const KEY = "auditxp.token";
let token: string | null =
  localStorage.getItem(KEY) ?? sessionStorage.getItem(KEY);

export function setToken(value: string | null, remember = false): void {
  token = value;
  localStorage.removeItem(KEY);
  sessionStorage.removeItem(KEY);
  if (value) (remember ? localStorage : sessionStorage).setItem(KEY, value);
}

export const hasToken = (): boolean => token !== null;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(BASE + path, { ...init, headers });
  if (response.status === 401 && token) {
    window.dispatchEvent(new Event("auditxp:logout"));
  }
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = typeof body.detail === "string"
        ? body.detail : body.detail?.[0]?.msg ?? message;
    } catch {
      /* тело ответа не JSON */
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  const type = response.headers.get("content-type") ?? "";
  return (type.includes("json") ? response.json() : response.blob()) as
    Promise<T>;
}

const post = (body?: unknown): RequestInit => ({
  method: "POST", body: body === undefined ? undefined : JSON.stringify(body),
});
const qs = (params: Record<string, string | number | undefined | null>) =>
  new URLSearchParams(Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => [k, String(v)])).toString();

export const api = {
  login: (login: string, password: string) =>
    request<{ access_token: string; user: User }>("/api/v1/auth/login",
      post({ login, password })),
  me: () => request<User>("/api/v1/auth/me"),
  recover: (email: string) =>
    request<{ detail: string }>("/api/v1/auth/password-recovery",
      post({ email })),
  reset: (resetToken: string, newPassword: string) =>
    request<{ detail: string }>("/api/v1/auth/password-reset",
      post({ token: resetToken, new_password: newPassword })),

  overview: (p?: Period) =>
    request<Overview>(`/api/v1/dashboard/overview?${qs({ ...p })}`),
  risks: (params: Record<string, string | number | undefined>) =>
    request<{ items: Risk[]; total: number }>(`/api/v1/risks?${qs(params)}`),
  risk: (id: number) => request<Risk>(`/api/v1/risks/${id}`),
  transition: (id: number, body: Record<string, unknown>) =>
    request<Risk>(`/api/v1/risks/${id}/transition`, post(body)),
  escalate: (id: number) =>
    request<Risk>(`/api/v1/risks/${id}/escalate`, post()),
  detect: (p: Period, strategy = "ml") =>
    request<DetectionResult>("/api/v1/risks/detect", post({ ...p, strategy })),
  heatmap: (p: Period) => request<Heatmap>(`/api/v1/heatmap?${qs({ ...p })}`),

  erpCheck: () => request<{ connected: boolean; source: string;
    base_url: string }>("/api/v1/etl/erp/check"),
  erpPreview: (p: Period) => request<Preview>("/api/v1/etl/erp/preview",
    post(p)),
  filePreview: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Preview>("/api/v1/etl/file/preview",
      { method: "POST", body: form });
  },
  runImport: (p: Period) => request<ImportResult>("/api/v1/etl/imports",
    post(p)),
  importFile: (file: File, mapping: Record<string, string>) => {
    const form = new FormData();
    form.append("file", file);
    form.append("mapping", JSON.stringify(mapping));
    return request<ImportResult>("/api/v1/etl/imports/file",
      { method: "POST", body: form });
  },
  journal: () => request<ImportBatch[]>("/api/v1/etl/imports"),
  quarantine: (id: number) => request<{ id: number;
    doc_number: string | null; reason: string }[]>(
    `/api/v1/etl/imports/${id}/quarantine`),

  reports: () => request<Report[]>("/api/v1/reports"),
  report: (id: number) => request<Report>(`/api/v1/reports/${id}`),
  createReport: (body: Period & { title: string }) =>
    request<Report>("/api/v1/reports", post(body)),
  submitReport: (id: number) =>
    request<Report>(`/api/v1/reports/${id}/submit`, post()),
  approveReport: (id: number) =>
    request<Report>(`/api/v1/reports/${id}/approve`, post()),
  returnReport: (id: number, comment: string) =>
    request<Report>(`/api/v1/reports/${id}/return`, post({ comment })),
  verifyReport: (id: number) =>
    request<{ valid: boolean }>(`/api/v1/reports/${id}/verify`),
  exportReport: (id: number, format: "pdf" | "xlsx") =>
    request<Blob>(`/api/v1/reports/${id}/export?format=${format}`),

  users: () => request<User[]>("/api/v1/users"),
  createUser: (body: Record<string, string>) =>
    request<User>("/api/v1/users", post(body)),
  updateUser: (id: number, body: Record<string, string>) =>
    request<User>(`/api/v1/users/${id}`,
      { method: "PUT", body: JSON.stringify(body) }),
  blockUser: (id: number, locked: boolean) =>
    request<User>(`/api/v1/users/${id}/${locked ? "block" : "unblock"}`,
      post()),
  deleteUser: (id: number) =>
    request<User>(`/api/v1/users/${id}`, { method: "DELETE" }),

  notifications: () => request<NotificationItem[]>("/api/v1/notifications"),
  readAll: () => request("/api/v1/notifications/read-all", post()),
  auditLog: (table?: string) =>
    request<AuditEntry[]>(`/api/v1/audit-log?${qs({ table_name: table,
      limit: 200 })}`),
};

export function download(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
