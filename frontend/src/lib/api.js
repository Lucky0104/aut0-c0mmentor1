import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("dashai_token");
  const tid = localStorage.getItem("dashai_tid");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (tid) config.headers["X-Tenant-Id"] = tid;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem("dashai_token");
      if (window.location.pathname !== "/login") window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const API_BASE = API;
