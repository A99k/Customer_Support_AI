import { apiFetch } from "./api.js";

export function sendChatMessage(token, { sessionId, message }) {
  return apiFetch("/api/chat", {
    method: "POST",
    token,
    body: { session_id: sessionId, message },
  });
}
