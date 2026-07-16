// FILE LOCATION: frontend/src/api/client.js
//
// Thin fetch wrapper. Base URL comes from VITE_API_BASE_URL (set in
// docker-compose.yml / .env for the frontend service); falls back to
// same-origin /api which is what nginx proxies to the api service in prod.

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

class ApiError extends Error {
  constructor(code, message, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    const err = body?.error || {};
    throw new ApiError(err.code || "unknown_error", err.message || res.statusText, res.status);
  }
  return body;
}

function qs(params = {}) {
  const clean = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  const search = new URLSearchParams(clean);
  const str = search.toString();
  return str ? `?${str}` : "";
}

export const api = {
  // --- Alerts (Phase 4) ---
  listAlerts: (params) => request(`/v1/alerts${qs(params)}`),
  getAlert: (id) => request(`/v1/alerts/${id}`),
  updateAlertStatus: (id, payload) =>
    request(`/v1/alerts/${id}/status`, { method: "PATCH", body: JSON.stringify(payload) }),
  alertsStreamUrl: () => `${BASE_URL}/v1/alerts/stream`,

  // --- Events / log viewer (Phase 1 + 4) ---
  listEvents: (params) => request(`/v1/events${qs(params)}`),

  // --- Playbooks (Phase 3) ---
  listPlaybooks: () => request(`/v1/playbooks`),
  getPlaybook: (name) => request(`/v1/playbooks/${name}`),
  togglePlaybook: (name, enabled) =>
    request(`/v1/playbooks/${name}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),

  // --- Simulation (Phase 5) ---
  triggerSimulation: (payload) =>
    request(`/v1/simulate`, { method: "POST", body: JSON.stringify(payload) }),
  getSimulationStatus: (id) => request(`/v1/simulate/${id}/status`),
};

export { ApiError, BASE_URL };
