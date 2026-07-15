import { apiFetch } from "./api.js";

export function signup({ name, email, password }) {
  return apiFetch("/api/auth/signup", {
    method: "POST",
    body: { name, email, password },
  });
}

export function login({ email, password }) {
  return apiFetch("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function fetchCurrentUser(token) {
  return apiFetch("/api/auth/me", { token });
}
