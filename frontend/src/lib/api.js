import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true, // send httpOnly cookie
});

api.interceptors.request.use((config) => {
  const tid = localStorage.getItem("dashai_tid");
  if (tid) config.headers["X-Tenant-Id"] = tid;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401 && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const API_BASE = API;
