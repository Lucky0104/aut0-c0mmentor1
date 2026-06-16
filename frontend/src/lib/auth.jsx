import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTenantId, setActiveTenantId] = useState(localStorage.getItem("dashai_tid"));

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setMe(data);
      if (!activeTenantId && data.tenants?.length) {
        const tid = data.active_tenant_id || data.tenants[0].id;
        localStorage.setItem("dashai_tid", tid);
        setActiveTenantId(tid);
      }
    } catch (e) {
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, [activeTenantId]);

  useEffect(() => {
    if (localStorage.getItem("dashai_token")) refresh();
    else setLoading(false);
  }, [refresh]);

  const logout = () => {
    localStorage.removeItem("dashai_token");
    localStorage.removeItem("dashai_tid");
    window.location.href = "/login";
  };

  const switchTenant = async (tid) => {
    const { data } = await api.post(`/auth/switch/${tid}`);
    localStorage.setItem("dashai_token", data.token);
    localStorage.setItem("dashai_tid", tid);
    setActiveTenantId(tid);
    await refresh();
  };

  const activeTenant = me?.tenants?.find((t) => t.id === activeTenantId);

  return (
    <AuthCtx.Provider value={{ me, loading, activeTenant, activeTenantId, refresh, logout, switchTenant }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
