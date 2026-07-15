import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { api, errMsg } from "../lib/api";
import { supabase } from "../lib/supabase";

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
    // Bootstrap: if supabase-js restored a session, hydrate the profile.
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      if (data?.session) {
        refreshUser();
      } else {
        setUser(false);
      }
    });
    // React to sign-in / sign-out / token-refresh / email-confirmation links.
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (!active) return;
      if (session) {
        refreshUser();
      } else if (event === "SIGNED_OUT") {
        authedRef.current = false;
        setUser(false);
        setActiveOrgId(null);
        localStorage.removeItem("activeOrgId");
      }
    });
    return () => { active = false; sub?.subscription?.unsubscribe(); };
  }, [refreshUser]);

  const switchOrg = (id) => {
    setActiveOrgId(id);
    localStorage.setItem("activeOrgId", id);
  };

  // Auth is owned by Supabase (GoTrue). We sign in/up with supabase-js, then
  // hydrate the app profile (orgs + roles) from our backend via /auth/me.
  const login = async (email, password) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error(error.message);
    return refreshUser();
  };

  const register = async (name, email, password) => {
    const { error } = await supabase.auth.signUp({
      email, password, options: { data: { full_name: name } },
    });
    if (error) throw new Error(error.message);
    // If the project requires email confirmation, there is no session yet;
    // /auth/me will 401 until the user confirms. Surface the profile if present.
    return refreshUser();
  };

  const logout = async () => {
    try { await supabase.auth.signOut(); } catch (e) { /* ignore */ }
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
