import { apiFetch } from "./api.js";

export function fetchAnalyticsSummary(token, days = 14) {
  return apiFetch(`/api/analytics/summary?days=${days}`, { token });
}

export function fetchMyAnalytics(token, days = 14) {
  return apiFetch(`/api/analytics/me?days=${days}`, { token });
}
