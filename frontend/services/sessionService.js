import { apiFetch } from "./api.js";

export function createSession(token) {
  return apiFetch("/api/session", { method: "POST", token });
}

export function listSessions(token) {
  return apiFetch("/api/sessions", { token });
}

export function getHistory(token, sessionId) {
  return apiFetch(`/api/history/${sessionId}`, { token });
}
