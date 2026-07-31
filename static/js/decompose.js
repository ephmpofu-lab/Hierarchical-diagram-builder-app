// Decompose (Engineering Decomposition & Solution Generation pipeline): the app's one real
// page for the whole primary loop (AMENDMENT 4 -- 2 screens + hidden Settings). Screens 1
// and 2 are this SAME page, distinguished only by state.view -- never a navigation/redirect
// between them. Full-repaint-per-state-change, same pattern discovery.html/js established.
//
// Item 1 (state machine shell): state.view = "home" | "drafting" | "reviewing_draft" |
// "canvas". Home shows the intent input plus a history list of known domains once any
// exist -- the input never disappears, so "start a new one" never requires leaving this
// state. "drafting"/"reviewing_draft" (new-domain flow) and real tree rendering inside
// "canvas" are later items -- this item only wires the shell + history + basic transitions.

const decomposeBoard = document.getElementById("decomposeBoard");

let state = {
  view: "home", // "home" | "drafting" | "reviewing_draft" | "canvas"
  knownDomains: [],
  domain: null,
  submitting: false,
  intentResult: null,
  error: null,
};

function renderBoard() {
  decomposeBoard.innerHTML = "";
  if (state.view === "canvas") {
    renderCanvasView();
  } else {
    renderHomeView();
  }
}

function renderHomeView() {
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = "What do you want to build?";
  decomposeBoard.appendChild(heading);

  const inputRow = document.createElement("div");
  inputRow.className = "discovery-input-row";
  const input = document.createElement("textarea");
  input.className = "discovery-message-input";
  input.placeholder = "e.g. I want to develop a RAG for our internal support docs…";
  input.rows = 3;
  input.id = "decomposeIntentInput";
  input.disabled = state.submitting;
  const submitBtn = document.createElement("button");
  submitBtn.className = "btn btn-primary";
  submitBtn.textContent = state.submitting ? "Parsing…" : "Decompose";
  submitBtn.disabled = state.submitting;
  submitBtn.addEventListener("click", () => submitIntent(input.value));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitIntent(input.value);
    }
  });
  inputRow.appendChild(input);
  inputRow.appendChild(submitBtn);
  decomposeBoard.appendChild(inputRow);
  input.focus();

  if (state.error) {
    const errorBox = document.createElement("div");
    errorBox.className = "reasoning-empty-state";
    errorBox.textContent = state.error;
    decomposeBoard.appendChild(errorBox);
  }

  if (state.intentResult) {
    const result = document.createElement("div");
    result.className = "discovery-turn architect";
    const label = document.createElement("div");
    label.className = "discovery-turn-label";
    label.textContent = "Detected domain";
    const message = document.createElement("div");
    message.className = "discovery-turn-message";
    const pct = Math.round(state.intentResult.confidence * 100);
    message.textContent = state.intentResult.tree_available
      ? `${state.intentResult.domain} (${pct}% confidence) — ready to decompose.`
      : `${state.intentResult.domain} (${pct}% confidence) — no frozen decomposition for this domain yet. New-domain drafting lands in the next increment.`;
    result.appendChild(label);
    result.appendChild(message);
    decomposeBoard.appendChild(result);
  }

  // History: the input above never disappears once entries exist -- no click-through
  // needed to reach "start a new one" (spec's own requirement).
  if (state.knownDomains.length > 0) {
    const historyLabel = document.createElement("div");
    historyLabel.className = "reasoning-section-label";
    historyLabel.textContent = "Past decompositions";
    decomposeBoard.appendChild(historyLabel);

    const historyList = document.createElement("div");
    historyList.className = "launchpad-recent-list";
    for (const domain of state.knownDomains) {
      const row = document.createElement("div");
      row.className = "launchpad-recent-row";
      const name = document.createElement("span");
      name.className = "launchpad-recent-name";
      name.textContent = domain;
      name.addEventListener("click", () => selectDomain(domain));
      row.appendChild(name);
      historyList.appendChild(row);
    }
    decomposeBoard.appendChild(historyList);
  }
}

function renderCanvasView() {
  // Placeholder for this item -- confirms the state transition works. Real tree
  // visualization, mode toggle, and node detail panel land in the next few items.
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = `Canvas — ${state.domain}`;
  decomposeBoard.appendChild(heading);

  const placeholder = document.createElement("div");
  placeholder.className = "reasoning-empty-state";
  placeholder.textContent = "Tree visualization lands in the next increment.";
  decomposeBoard.appendChild(placeholder);

  const backBtn = document.createElement("button");
  backBtn.className = "btn btn-small";
  backBtn.textContent = "← Home";
  backBtn.addEventListener("click", () => {
    state = { ...state, view: "home" };
    renderBoard();
  });
  decomposeBoard.appendChild(backBtn);
}

function selectDomain(domain) {
  state = { ...state, view: "canvas", domain };
  renderBoard();
}

async function submitIntent(text) {
  const trimmed = text.trim();
  if (!trimmed || state.submitting) return;
  state = { ...state, submitting: true, error: null };
  renderBoard();
  try {
    const res = await fetch("/api/decompose/intent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: trimmed }),
    });
    if (!res.ok) {
      state = { ...state, submitting: false, error: "Failed to parse your intent. Please try again." };
      renderBoard();
      return;
    }
    const intentResult = await res.json();
    state = { ...state, submitting: false, intentResult };
    if (intentResult.tree_available) {
      selectDomain(intentResult.domain);
      return;
    }
  } finally {
    renderBoard();
  }
}

async function loadKnownDomains() {
  const res = await fetch("/api/decompose/domains");
  if (!res.ok) return;
  state = { ...state, knownDomains: await res.json() };
  renderBoard();
}

// The Launchpad's primary input hands off here via sessionStorage (same cross-page handoff
// pattern login.html/discovery.js already use) -- read once, then clear immediately so a
// later refresh of this page doesn't resend it.
const LAUNCHPAD_IDEA_KEY = "architeq-launchpad-idea";

function init() {
  renderBoard();
  loadKnownDomains();
  const idea = sessionStorage.getItem(LAUNCHPAD_IDEA_KEY);
  if (idea) {
    sessionStorage.removeItem(LAUNCHPAD_IDEA_KEY);
    document.getElementById("decomposeIntentInput").value = idea;
    submitIntent(idea);
  }
}

init();
