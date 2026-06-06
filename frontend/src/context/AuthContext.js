import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { api, errMsg } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null=checking, false=anon, obj=auth
  const [activeOrgId, setActiveOrgId] = useState(
    () => localStorage.getItem("activeOrgId") || null
  );
  // true once the user is explicitly authenticated; prevents a late/stale
  // bootstrap /auth/me response from clobbering a successful login.
  const authedRef = useRef(false);

  const syncActiveOrg = useCallback((data) => {
    const ids = (data?.organizations || []).map((o) => o.id);
    setActiveOrgId((prev) => {
      if (prev && ids.includes(prev)) return prev;
      const next = ids[0] || null;
      if (next) localStorage.setItem("activeOrgId", next);
      else localStorage.removeItem("activeOrgId");
      return next;
    });
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      authedRef.current = true;
      setUser(data);
      syncActiveOrg(data);
      return data;
    } catch {
      if (!authedRef.current) setUser(false);
      return null;
    }
  }, [syncActiveOrg]);

  useEffect(() => {
    let active = true;
    api.get("/auth/me")
      .then(({ data }) => {
        if (active && !authedRef.current) {
          authedRef.current = true;
          setUser(data);
          syncActiveOrg(data);
        }
      })
      .catch(() => { if (active && !authedRef.current) setUser(false); });
    return () => { active = false; };
  }, [syncActiveOrg]);

  const switchOrg = (id) => {
    setActiveOrgId(id);
    localStorage.setItem("activeOrgId", id);
  };

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    authedRef.current = true;
    setUser(data);
    syncActiveOrg(data);
    return data;
  };

  const register = async (name, email, password) => {
    const { data } = await api.post("/auth/register", { name, email, password });
    authedRef.current = true;
    setUser(data);
    syncActiveOrg(data);
    return data;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch (e) { /* ignore */ }
    authedRef.current = false;
    setUser(false);
    setActiveOrgId(null);
    localStorage.removeItem("activeOrgId");
  };

  const activeOrg =
    user && user.organizations
      ? user.organizations.find((o) => o.id === activeOrgId)
      : null;

  const value = {
    user, setUser, refreshUser, login, register, logout, errMsg,
    activeOrgId, activeOrg, switchOrg,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
