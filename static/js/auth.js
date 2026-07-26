// Shared session guard + fetch-wrapping (Phase 12 WP2). Loaded on every page except
// login.html, which has its own separate sign-in/sign-up flow. Depends on the Supabase JS
// client (CDN) and supabase-config.js being loaded first.
//
// Wrapping window.fetch once, globally, is deliberate: editor.js and library.js already
// have dozens of existing fetch("/api/...") call sites built up over many rounds of this
// project. Rewriting each one individually to attach an Authorization header would touch
// far more of the codebase than this change needs to -- one wrapper here gives every
// existing and future call site the header automatically, with zero changes to any of them.

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);

let currentSession = null;

async function requireSession() {
  const { data } = await supabaseClient.auth.getSession();
  if (!data.session) {
    window.location.href = "login.html";
    return null;
  }
  currentSession = data.session;
  return data.session;
}

supabaseClient.auth.onAuthStateChange((_event, session) => {
  currentSession = session;
  if (!session) {
    window.location.href = "login.html";
  }
});

const _nativeFetch = window.fetch.bind(window);
window.fetch = async (input, init = {}) => {
  const url = typeof input === "string" ? input : input.url;
  if (url.startsWith("/api/")) {
    const session = currentSession || (await supabaseClient.auth.getSession()).data.session;
    if (session) {
      init = {
        ...init,
        headers: { ...(init.headers || {}), Authorization: `Bearer ${session.access_token}` },
      };
    }
  }
  const response = await _nativeFetch(input, init);
  if (response.status === 401) {
    window.location.href = "login.html";
  }
  return response;
};

async function logout() {
  await supabaseClient.auth.signOut();
  window.location.href = "login.html";
}

requireSession();
