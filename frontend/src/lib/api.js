import axios from "axios";
import { accessToken } from "./supabase";

// Empty REACT_APP_BACKEND_URL → same-origin "/api" (CRA dev proxy / reverse proxy)
const BASE = process.env.REACT_APP_BACKEND_URL || "";

export const api = axios.create({
  baseURL: `${BASE}/api`,
  withCredentials: true,
  timeout: 20000,
});

// Attach the Supabase access token as a Bearer on every request; supabase-js
// keeps it fresh (auto-refresh), so the backend always sees a valid session.
api.interceptors.request.use(async (config) => {
  const token = await accessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export function errMsg(e) {
  return formatApiError(e?.response?.data?.detail) || e?.message || "Request failed";
}
