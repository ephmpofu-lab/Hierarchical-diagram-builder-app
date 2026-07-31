// Decompose (Engineering Decomposition & Solution Generation pipeline): a standalone page,
// following discovery.html's exact pattern (full-repaint-per-state-change, own script tags).
// Stage (a) only: page shell + free-text intent input -> /api/decompose/intent. Domain
// confirmation, the frozen tree, and rendering come in later, reviewed increments.

const decomposeBoard = document.getElementById("decomposeBoard");

let state = {
  submitting: false,
  intentResult: null, // { domain, confidence, extracted_constraints, tree_available }
  error: null,
};

function renderBoard() {
  decomposeBoard.innerHTML = "";

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
      : `${state.intentResult.domain} (${pct}% confidence) — no frozen decomposition for this domain yet.`;
    result.appendChild(label);
    result.appendChild(message);
    decomposeBoard.appendChild(result);
  }
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
  } finally {
    renderBoard();
  }
}

// The Launchpad's primary input hands off here via sessionStorage (same cross-page handoff
// pattern login.html/discovery.js already use) -- read once, then clear immediately so a
// later refresh of this page doesn't resend it.
const LAUNCHPAD_IDEA_KEY = "architeq-launchpad-idea";

function init() {
  renderBoard();
  const idea = sessionStorage.getItem(LAUNCHPAD_IDEA_KEY);
  if (idea) {
    sessionStorage.removeItem(LAUNCHPAD_IDEA_KEY);
    document.getElementById("decomposeIntentInput").value = idea;
    submitIntent(idea);
  }
}

init();
