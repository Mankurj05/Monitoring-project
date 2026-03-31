const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_KEY = import.meta.env.VITE_MONITORING_API_KEY || "dev-monitor-key";
const TENANT_ID = import.meta.env.VITE_TENANT_ID || "default";
const PROJECT_ID = import.meta.env.VITE_PROJECT_ID || "demo";

async function request(path) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": TENANT_ID,
      "x-project-id": PROJECT_ID,
    },
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getTraces: (limit = 20) => request(`/api/traces?limit=${limit}`),
  getTrace: (traceId) => request(`/api/traces/${traceId}`),
  getServiceMap: (minutes = 60) => request(`/api/service-map?minutes=${minutes}`),
  getLatency: (minutes = 60) => request(`/api/metrics/latency?minutes=${minutes}`),
  getErrors: (minutes = 60) => request(`/api/metrics/errors?minutes=${minutes}`),
  getServices: () => request(`/api/services`),
};
