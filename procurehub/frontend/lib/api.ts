const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:48000/api/v1";
let accessToken: string | null = null;

export type User = {
  id: string;
  email: string;
  full_name: string;
  company: { id: string; legal_name: string; company_type: string } | null;
  roles: string[];
};

export type Kpi = { value: number | string | null; n: number; unit: string; definition: string; rate?: number | null };

export type DashboardData = {
  scope: { company_id: string | null; global: boolean; supplier_view: boolean };
  counts: Record<string, Record<string, number>>;
  receivables: { open_balance: string; overdue_count: number };
  kpis: Record<string, Kpi> | null;
  pending_actions: Array<{ type: string; id: string; number: string; status: string; label: string; updated_at: string }>;
  recent_activity: Array<{ id: number; action: string; entity_type: string; entity_id: string; actor: User | null; payload: Record<string, unknown>; occurred_at: string }>;
  pending_count: number;
  generated_at: string;
};

export type PurchaseRequest = {
  id: string;
  number: string;
  status: string;
  purpose: string;
  needed_by: string;
  currency: string;
  estimated_budget: string | null;
  requester: { id: string; email: string; full_name: string };
  lines: Array<{ id: number; description: string; quantity: string; unit: string }>;
};

export type PurchaseRequestInput = {
  purpose: string;
  needed_by: string;
  currency: string;
  estimated_budget?: string | null;
  lines: Array<{ description: string; quantity: string; unit: string }>;
};

export type SupplierRelationship = {
  id: string;
  status: string;
  supplier_company: { id: string; legal_name: string; category: string; status: string };
  rating_average: string | null;
  rating_count: number;
};

export type ScoringWeights = { price: number; delivery: number; rating: number; payment_terms: number };

export type RFQCreateInput = {
  request_id: string;
  title: string;
  instructions?: string;
  deadline: string;
  supplier_company_ids: string[];
  scoring_weights?: ScoringWeights;
};

export type ApiList<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export type RFQLine = { id: number; description: string; quantity: string; unit: string };
export type RFQ = {
  id: string;
  number: string;
  title: string;
  status: string;
  deadline: string;
  instructions: string;
  scoring_weights: ScoringWeights;
  published_at: string | null;
  lines: RFQLine[];
  invitations: Array<{ id: string; supplier_company: string; supplier: { legal_name: string }; status: string; viewed_at: string | null; responded_at: string | null; decline_reason: string }>;
};
export type QuotationSignature = {
  state: "UNSIGNED" | "PENDING" | "VALID" | "INVALID" | "REJECTED" | "FAILED" | "UNVERIFIABLE";
  revision?: number;
  sign_url?: string;
  signer?: string;
  signer_tax_code?: string;
  certificate_serial?: string;
  issuer?: string;
  signed_at?: string;
  reason?: string;
};
export type Quotation = {
  id: string;
  status: string;
  revision: number;
  valid_until: string | null;
  delivery_days: number | null;
  payment_terms: string;
  payment_term_days: number | null;
  total: string;
  signature: QuotationSignature;
  supplier: { id: string; legal_name: string };
  lines: Array<{ id: number; rfq_line: RFQLine; offered_quantity: string; unit_price: string | null; line_total: string }>;
};
export type ScoreResult = {
  quotation_id: string;
  supplier: { id: string; legal_name: string };
  components: Record<keyof ScoringWeights, string>;
  rating_available: boolean;
  rating_average: string | null;
  rating_count: number;
  total_score: string;
  rank: number;
};
export type Scoring = { weights: ScoringWeights; formula: string; neutral_rating: string; results: ScoreResult[] };
export type Comparison = { rfq: RFQ; quotations: Quotation[]; scoring: Scoring };
export type SupplierSelection = {
  id: string;
  rfq: string;
  quotation: { id: string; supplier_company_id: string; total: string };
  status: string;
  rationale: string;
  score_snapshot: { selected?: ScoreResult } | Record<string, never>;
};
export type PurchaseOrder = {
  id: string;
  number: string;
  status: string;
  currency: string;
  total: string;
  delivery_days: number | null;
  payment_terms: string;
  payment_term_days: number;
  delivered_at: string | null;
  supplier: { id: string; legal_name: string };
  lines: Array<{ id: number; description: string; unit: string; quantity: string; unit_price: string; line_total: string; delivered_quantity: string }>;
  invoice: { id: string; number: string; status: string; balance: string; due_date: string; is_overdue: boolean } | null;
  evaluation: { quality_score: number; delivery_score: number; comment: string; created_at: string } | null;
};

export type Payment = {
  id: string;
  amount: string;
  status: "PENDING" | "SUCCEEDED" | "FAILED";
  provider: "MOCK" | "SANDBOX_GW" | string;
  external_ref: string;
  gateway_transaction_id: string;
  checkout_url: string;
  settled_at: string | null;
  failure_reason: string;
  created_at: string;
};

export type Invoice = {
  id: string;
  number: string;
  purchase_order: { id: string; number: string };
  buyer: { id: string; legal_name: string };
  supplier: { id: string; legal_name: string };
  status: string;
  currency: string;
  subtotal: string;
  vat_rate: string;
  vat_amount: string;
  total: string;
  paid_amount: string;
  balance: string;
  is_overdue: boolean;
  issued_at: string;
  due_date: string;
  payment_term_days: number;
  einvoice: {
    status: "NOT_SENT" | "PENDING_TAX_CODE" | "ISSUED" | "FAILED";
    symbol: string;
    number: number | null;
    lookup_code: string;
    tax_code: string;
    lookup_url: string;
    xml_url: string;
    error: string;
  };
  payments: Payment[];
};

export type AppNotification = {
  id: number;
  event_type: string;
  entity_type: string;
  entity_id: string;
  title: string;
  payload: { number?: string; status?: string; path?: string };
  read_at: string | null;
  created_at: string;
};

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function fetchWithAuth<T>(path: string, options: RequestInit, allowRefresh: boolean): Promise<T> {
  if (
    !accessToken &&
    allowRefresh &&
    !path.startsWith("/auth/") &&
    typeof window !== "undefined" &&
    getStoredUser() !== null
  ) {
    await refreshAccessToken();
  }

  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: "include" });
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401 && allowRefresh && !path.startsWith("/auth/") && typeof window !== "undefined") {
    if (await refreshAccessToken()) return fetchWithAuth<T>(path, options, false);
  }
  if (!response.ok) {
    throw new ApiError(response.status, payload.message ?? "Có lỗi xảy ra.", payload.code);
  }
  return payload as T;
}

let refreshInFlight: Promise<string | null> | null = null;

/**
 * Gọi /auth/refresh một lần cho mọi request đang chờ. Refresh token xoay vòng sau mỗi lần dùng,
 * nên nhiều lời gọi song song (ví dụ ngay sau F5) sẽ làm các lời gọi sau bị 401.
 */
function refreshAccessToken(): Promise<string | null> {
  refreshInFlight ??= fetch(`${API_URL}/auth/refresh`, { method: "POST", credentials: "include" })
    .then(async (refreshed) => {
      if (!refreshed.ok) {
        if (refreshed.status === 401 || refreshed.status === 403) {
          accessToken = null;
          if (typeof window !== "undefined") {
            window.localStorage.removeItem("procurehub_user");
          }
        }
        return null;
      }
      accessToken = ((await refreshed.json()) as { access: string }).access;
      return accessToken;
    })
    .catch(() => null)
    .finally(() => { refreshInFlight = null; });
  return refreshInFlight;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  return fetchWithAuth<T>(path, options, true);
}

/** Lấy access token trong bộ nhớ; nếu chưa có (vừa tải lại trang) thì khôi phục qua refresh cookie. */
export async function ensureAccessToken(force = false): Promise<string> {
  if (accessToken && !force) return accessToken;
  const token = await refreshAccessToken();
  if (!token) throw new ApiError(401, "Phiên đăng nhập đã hết hạn.", "authentication_required");
  return token;
}

/**
 * Đọc luồng SSE /notifications/stream bằng fetch (để gửi Bearer token qua header, không đưa token lên URL).
 * Server tự đóng kết nối sau ~25 giây; trả về id sự kiện cuối để gọi lại với `after`.
 */
export async function streamNotifications(after: number, onNotification: (item: AppNotification) => void, signal: AbortSignal): Promise<number> {
  const token = await ensureAccessToken();
  const response = await fetch(`${API_URL}/notifications/stream?after=${after}`, {
    headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
    credentials: "include",
    signal,
  });
  if (response.status === 401) {
    accessToken = null;
    throw new ApiError(401, "Phiên đăng nhập đã hết hạn.", "authentication_required");
  }
  if (!response.ok || !response.body) throw new ApiError(response.status, "Không mở được kênh thông báo.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let lastId = after;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      let eventName = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
        else if (line.startsWith("id:")) lastId = Number(line.slice(3).trim()) || lastId;
      }
      if (eventName === "notification" && data) onNotification(JSON.parse(data) as AppNotification);
      boundary = buffer.indexOf("\n\n");
    }
  }
  return lastId;
}

export function hasRole(user: User | null, ...roles: string[]): boolean {
  return user?.roles.some((role) => roles.includes(role)) ?? false;
}

export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return `${Number(value).toLocaleString("vi-VN")} ₫`;
}

export async function login(email: string, password: string) {
  const result = await apiFetch<{ access: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  accessToken = result.access;
  window.localStorage.removeItem("procurehub_access");
  window.localStorage.setItem("procurehub_user", JSON.stringify(result.user));
  return result;
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  window.localStorage.removeItem("procurehub_access");
  const raw = window.localStorage.getItem("procurehub_user");
  return raw ? (JSON.parse(raw) as User) : null;
}

export async function logout() {
  try {
    await fetch(`${API_URL}/auth/logout`, { method: "POST", credentials: "include" });
  } finally {
    accessToken = null;
    window.localStorage.removeItem("procurehub_access");
    window.localStorage.removeItem("procurehub_user");
  }
}
