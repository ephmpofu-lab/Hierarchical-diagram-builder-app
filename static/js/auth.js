// Shared session guard + fetch-wrapping (Phase 12 WP2, revised). Loaded on every page
// except login.html. Depends on supabase-client.js (which depends on the Supabase CDN
// script + supabase-config.js) having already run and defined `supabaseClient`.
//
// Wrapping window.fetch once, globally, is deliberate: editor.js and library.js already
// have dozens of existing fetch("/api/...") call sites built up over many rounds of this
// project. One wrapper here gives every existing and future call site the Authorization
// header automatically, with zero changes to any of them.

let currentSession = null;

async function requireSession() {
  const { data } = await supabaseClient.auth.getSession();
  if (!data.session) {
    guardedRedirect("login.html");
    return null;
  }
  currentSession = data.session;
  return data.session;
}

// Root cause of the earlier signup redirect loop: onAuthStateChange's very first callback
// can fire with a transient null session before the persisted session finishes loading --
// reacting to ANY falsy session here raced against requireSession() above, which had
// already found and confirmed a real one, and the two disagreed. Only an explicit
// SIGNED_OUT event should ever send us back to the login page from this listener.
supabaseClient.auth.onAuthStateChange((event, session) => {
  currentSession = session;
  if (event === "SIGNED_OUT") {
    guardedRedirect("login.html", "Your session ended. Please sign in again.");
  }
});

// Scoped deliberately to our own /api/ calls only, for both the header injection AND the
// 401 redirect below. Supabase's JS client also calls the global fetch() internally (for
// its own token-refresh requests against supabase.co) -- an earlier version of this file
// redirected on ANY 401 from ANY fetch, which meant a failed Supabase-internal refresh
// call could trigger this same redirect, competing with Supabase's own auth-state handling
// and contributing to exactly the instability this fix addresses. Supabase's client already
// fires a real SIGNED_OUT event through onAuthStateChange above when a refresh genuinely
// fails -- that's the one path that should ever send us to login.html, not a raw 401 count.
const _nativeFetch = window.fetch.bind(window);
window.fetch = async (input, init = {}) => {
  const url = typeof input === "string" ? input : input.url;
  const isOwnApiCall = url.startsWith("/api/");
  if (isOwnApiCall) {
    const session = currentSession || (await supabaseClient.auth.getSession()).data.session;
    if (session) {
      init = {
        ...init,
        headers: { ...(init.headers || {}), Authorization: `Bearer ${session.access_token}` },
      };
    }
  }
  const response = await _nativeFetch(input, init);
  if (isOwnApiCall && response.status === 401) {
    // Surface *why* -- backend/auth.py's require_auth sends a specific detail message
    // (e.g. "Invalid or expired session: <reason>"); silently redirecting on the status
    // code alone and discarding the body is exactly the kind of "nothing happened" gap
    // that makes a real auth failure indistinguishable from a UI bug.
    let detail = "Your session could not be verified. Please sign in again.";
    try {
      const body = await response.clone().json();
      if (body && body.detail) detail = body.detail;
    } catch {
      // no JSON body -- fall back to the generic message
    }
    guardedRedirect("login.html", detail);
  }
  return response;
};

async function logout() {
  await supabaseClient.auth.signOut();
  guardedRedirect("login.html");
}

requireSession();
