import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// Attach bearer token from localStorage as fallback (for environments where cookies fail)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nalanda_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Globally swallow request-cancellation errors so unmounted-component aborts
// never bubble up as unhandled rejections (which trigger the red overlay).
// All real errors still propagate normally.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isCanceled =
      axios.isCancel?.(error) ||
      error?.code === "ERR_CANCELED" ||
      error?.name === "CanceledError" ||
      error?.name === "AbortError" ||
      error?.message === "canceled";
    if (isCanceled) {
      // Resolve with a sentinel so .then(({data})) won't throw; pages can ignore
      return new Promise(() => {}); // never settles → caller never sees rejection
    }
    return Promise.reject(error);
  }
);

// Belt-and-braces: swallow any leaked Axios cancellation at the window level.
if (typeof window !== "undefined") {
  window.addEventListener("unhandledrejection", (event) => {
    const r = event.reason;
    const isCanceled =
      axios.isCancel?.(r) ||
      r?.code === "ERR_CANCELED" ||
      r?.name === "CanceledError" ||
      r?.name === "AbortError" ||
      r?.message === "canceled";
    if (isCanceled) event.preventDefault();
  });
}

export function setToken(token) {
  if (token) localStorage.setItem("nalanda_token", token);
  else localStorage.removeItem("nalanda_token");
}

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const formatINR = (n) => {
  if (n === null || n === undefined || isNaN(n)) return "₹0";
  const num = Number(n);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  if (num >= 1000) return `₹${(num / 1000).toFixed(1)}K`;
  return `₹${num.toLocaleString("en-IN")}`;
};

export const formatINRFull = (n) => {
  if (n === null || n === undefined || isNaN(n)) return "₹0";
  return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
};
