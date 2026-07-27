// Shared Supabase client (Phase 12 WP2, revised). Every page that touches auth --
// login.html, index.html, editor.html -- creates its client through this ONE function,
// so "Remember me" and session storage behave identically regardless of which page
// created the session. Depends on the Supabase CDN script + supabase-config.js loading
// first (both provide globals this file reads).
//
// "Remember me": a flag in localStorage decides which Web Storage backend actually holds
// the session -- localStorage (survives closing the browser) when remembered, sessionStorage
// (cleared when the tab closes) when not. The flag itself always lives in localStorage --
// it has to be readable before we know which backend to use for the session itself.

const REMEMBER_ME_KEY = "diagram-builder-remember-me";

function setRememberMe(remember) {
  localStorage.setItem(REMEMBER_ME_KEY, remember ? "true" : "false");
}

function isRemembered() {
  return localStorage.getItem(REMEMBER_ME_KEY) !== "false"; // unset = remembered, the sane default
}

const _rememberAwareStorage = {
  getItem: (key) => (isRemembered() ? localStorage : sessionStorage).getItem(key),
  setItem: (key, value) => (isRemembered() ? localStorage : sessionStorage).setItem(key, value),
  removeItem: (key) => {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  },
};

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: { storage: _rememberAwareStorage, persistSession: true, autoRefreshToken: true },
});

// Shared circuit breaker for the login.html <-> index.html/editor.html redirect, used by
// both sides. Belt-and-suspenders on top of the actual fixes elsewhere (backend-verified
// session checks, a narrowly-scoped fetch 401 handler, an auth-state listener that only
// reacts to a real SIGNED_OUT event) -- if the two pages ever disagree again for a reason
// none of those anticipated, this stops an actual infinite loop rather than letting it run.
const REDIRECT_GUARD_KEY = "diagram-builder-auth-redirect-guard";

// A redirect to login.html is often caused by something the *user* should be told about
// (a rejected token, an ended session) -- but it's a full-page navigation, so the only way
// to carry that reason across is a handoff key login.html reads once on load, then clears.
const AUTH_MESSAGE_KEY = "diagram-builder-auth-message";

function guardedRedirect(targetUrl, message) {
  const now = Date.now();
  let guard = { count: 0, firstAt: now };
  try {
    const raw = sessionStorage.getItem(REDIRECT_GUARD_KEY);
    if (raw) guard = JSON.parse(raw);
  } catch {
    // malformed guard state -- treat as fresh
  }
  if (now - guard.firstAt > 4000) {
    guard = { count: 0, firstAt: now };
  }
  guard.count += 1;
  if (guard.count > 3) {
    sessionStorage.removeItem(REDIRECT_GUARD_KEY);
    document.body.innerHTML =
      '<div style="max-width:420px;margin:80px auto;text-align:center;font-family:sans-serif;">' +
      "<h2>Trouble verifying your session</h2>" +
      "<p>Something kept redirecting between sign-in and the app. Please try signing in again.</p>" +
      '<a href="login.html" style="color:#3c5fb0;">Go to sign in</a></div>';
    return;
  }
  sessionStorage.setItem(REDIRECT_GUARD_KEY, JSON.stringify(guard));
  if (message) sessionStorage.setItem(AUTH_MESSAGE_KEY, message);
  window.location.href = targetUrl;
}
