// All backend calls go through here so the token handling lives in one place.

const TOKEN_KEY = "finshield_token";
const USER_KEY = "finshield_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function storeSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(path, { ...options, headers });

  if (response.status === 401) {
    clearSession();
    window.location.href = "/login";
    throw new Error("Your session has expired. Sign in again.");
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = data && data.detail;
    throw new Error(
      typeof detail === "string" ? detail : "The request could not be completed."
    );
  }
  return data;
}

export const api = {
  login(username, password) {
    // FastAPI's login endpoint expects form encoded fields.
    const form = new URLSearchParams({ username, password });
    return request("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
  },
  register(payload) {
    return request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  me: () => request("/api/auth/me"),

  summary: () => request("/api/analytics/summary"),

  transactions: (query = "") => request(`/api/transactions${query}`),
  transaction: (id) => request(`/api/transactions/${id}`),
  explanation: (id) => request(`/api/transactions/${id}/explanation`),
  submitTransaction: (payload) =>
    request("/api/transactions", { method: "POST", body: JSON.stringify(payload) }),
  reanalyse: (id) =>
    request(`/api/transactions/${id}/reanalyse`, { method: "POST" }),

  alerts: (query = "") => request(`/api/alerts${query}`),
  updateAlertStatus: (id, status) =>
    request(`/api/alerts/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  cases: (query = "") => request(`/api/cases${query}`),
  caseDetail: (id) => request(`/api/cases/${id}`),
  createCase: (payload) =>
    request("/api/cases", { method: "POST", body: JSON.stringify(payload) }),
  updateCase: (id, payload) =>
    request(`/api/cases/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  addCaseNote: (id, note) =>
    request(`/api/cases/${id}/notes`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  
  runAmlTests: () =>
    request("/api/admin/aml-testing/run", {
      method: "POST",
    }),

  users: () => request("/api/admin/users"),
  changeRole: (id, role) =>
    request(`/api/admin/users/${id}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),
  auditLogs: (query = "") => request(`/api/admin/audit-logs${query}`),
  amlRules: () => request("/api/admin/aml-rules"),
  mlModels: () => request("/api/admin/ml-models"),
};
