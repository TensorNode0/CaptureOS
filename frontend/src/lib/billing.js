import { useEffect, useState, useCallback, createContext, useContext, useRef } from "react";
import { api } from "./api";
import { useAuth } from "../context/AuthContext";

// Business-tier gating on the frontend. Source of truth is /api/payments/me;
// the hook caches it in React context so we don't refetch on every page nav.

const SubscriptionCtx = createContext(null);

const TIER_RANK = { free: 0, oi: 1, full: 2, enterprise: 3 };

export function SubscriptionProvider({ children }) {
  const { user } = useAuth();
  const [sub, setSub] = useState(null); // null=loading, {} once loaded
  const [loading, setLoading] = useState(true);
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const { data } = await api.get("/payments/me");
      setSub(data);
    } catch {
      // Anonymous or /auth/me not yet resolved — leave defaults.
      setSub({ tier: "free", status: "free", isPlatformOwner: false });
    } finally {
      setLoading(false);
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    if (user && user.id) refresh();
    else { setSub(null); setLoading(false); }
  }, [user, refresh]);

  return (
    <SubscriptionCtx.Provider value={{ sub, loading, refresh }}>
      {children}
    </SubscriptionCtx.Provider>
  );
}

export function useSubscription() {
  return useContext(SubscriptionCtx) || { sub: null, loading: false, refresh: () => {} };
}

export function hasTier(sub, minTier) {
  if (!sub) return false;
  return (TIER_RANK[sub.tier] || 0) >= (TIER_RANK[minTier] || 99);
}
