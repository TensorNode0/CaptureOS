import { createClient } from "@supabase/supabase-js";

/* Supabase Auth client. Identity, passwords, email confirmation and password
   reset are owned by Supabase; the app reads the session token and sends it as
   a Bearer to our backend. Configure with REACT_APP_SUPABASE_URL and
   REACT_APP_SUPABASE_ANON_KEY (both are safe to expose to the browser). */
const url = process.env.REACT_APP_SUPABASE_URL || "";
const anon = process.env.REACT_APP_SUPABASE_ANON_KEY || "";

export const supabaseConfigured = Boolean(url && anon);

export const supabase = createClient(url || "http://localhost", anon || "public-anon-key", {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true, // handle email-confirmation / recovery links
  },
});

export async function accessToken() {
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token || "";
}
