// Decompose (Engineering Decomposition & Solution Generation pipeline): the app's one real
// page for the whole primary loop (AMENDMENT 4 -- 2 screens + hidden Settings). Screens 1
// and 2 are this SAME page, distinguished only by state.view -- never a navigation/redirect
// between them. Full-repaint-per-state-change, same pattern discovery.html/js established.
//
// Item 2 (new-domain flow): "drafting" (calls POST .../draft) -> "reviewing_draft" (shows
// the proposed tree + any validation violations + an Approve action, all in place -- no
// separate Validation Results page) -> "canvas" once approved. Reuses the already-built
// draft/approve endpoints verbatim; nothing backend changes for this item.

const decomposeBoard = document.getElementById("decomposeBoard");

let state = {
  view: "home", // "home" | "drafting" | "reviewing_draft" | "canvas"
  knownDomains: [],
  domain: null,
  lastIntentText: "",
  draft: null, // { domain, checklist, tree, validation } from POST .../draft
  submitting: false,
  error: null,
};

function renderBoard() {
  decomposeBoard.innerHTML = "";
  if (state.view === "drafting") {
    renderDraftingView();
  } else if (state.view === "reviewing_draft") {
    renderReviewingDraftView();
  } else if (state.view === "canvas") {
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
    state = { ...state, submitting: false, lastIntentText: trimmed };
    if (intentResult.tree_available) {
      selectDomain(intentResult.domain);
      return;
    }
    startDrafting(intentResult.domain);
    return;
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

async function startDrafting(domain) {
  state = { ...state, view: "drafting", domain, draft: null, error: null };
  renderBoard();
  try {
    const res = await fetch(`/api/decompose/domains/${encodeURIComponent(domain)}/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reasoning_context: state.lastIntentText }),
    });
    if (!res.ok) {
      state = { ...state, view: "home", error: `Failed to draft a decomposition for '${domain}'. Please try again.` };
      return;
    }
    const draft = await res.json();
    state = { ...state, view: "reviewing_draft", draft };
  } finally {
    renderBoard();
  }
}

function renderDraftingView() {
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = `Drafting a decomposition for '${state.domain}'…`;
  decomposeBoard.appendChild(heading);
  const note = document.createElement("div");
  note.className = "reasoning-empty-state";
  note.textContent = "Running the Decomposition Engine's full 4-stage build order for a brand-new domain -- this can take a little while.";
  decomposeBoard.appendChild(note);
}

function renderTreeOutline(tree) {
  // Lightweight nested list -- item 3 upgrades this into the real card-based canvas
  // visualization; this is enough to review a draft before approving it.
  const list = document.createElement("ul");
  list.className = "decompose-tree-outline";
  for (const layerId of tree.root_ids) {
    const layer = tree.nodes[layerId];
    if (!layer) continue;
    const layerItem = document.createElement("li");
    layerItem.textContent = layer.label;
    const subList = document.createElement("ul");
    for (const subId of layer.children) {
      const sub = tree.nodes[subId];
      if (!sub) continue;
      const subItem = document.createElement("li");
      subItem.textContent = sub.label;
      const atomicList = document.createElement("ul");
      for (const atomicId of sub.children) {
        const atomic = tree.nodes[atomicId];
        if (!atomic) continue;
        const atomicItem = document.createElement("li");
        atomicItem.textContent = atomic.label;
        atomicList.appendChild(atomicItem);
      }
      subItem.appendChild(atomicList);
      subList.appendChild(subItem);
    }
    layerItem.appendChild(subList);
    list.appendChild(layerItem);
  }
  return list;
}

function renderReviewingDraftView() {
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = `Review draft — ${state.domain}`;
  decomposeBoard.appendChild(heading);

  decomposeBoard.appendChild(renderTreeOutline(state.draft.tree));

  if (!state.draft.validation.passed) {
    const violationsLabel = document.createElement("div");
    violationsLabel.className = "reasoning-section-label";
    violationsLabel.textContent = "Validation violations";
    decomposeBoard.appendChild(violationsLabel);
    const list = document.createElement("ul");
    list.className = "decompose-violations-list";
    for (const v of state.draft.validation.violations) {
      const item = document.createElement("li");
      item.textContent = `[${v.principle_id}] ${v.message}`;
      list.appendChild(item);
    }
    decomposeBoard.appendChild(list);
  }

  if (state.error) {
    const errorBox = document.createElement("div");
    errorBox.className = "reasoning-empty-state";
    errorBox.textContent = state.error;
    decomposeBoard.appendChild(errorBox);
  }

  const actions = document.createElement("div");
  actions.className = "reasoning-actions";
  const approveBtn = document.createElement("button");
  approveBtn.className = "btn btn-primary";
  approveBtn.textContent = state.submitting ? "Approving…" : "Approve";
  approveBtn.disabled = state.submitting || !state.draft.validation.passed;
  approveBtn.title = state.draft.validation.passed ? "" : "This draft has unresolved validation violations and cannot be approved yet.";
  approveBtn.addEventListener("click", approveDraft);
  actions.appendChild(approveBtn);
  const backBtn = document.createElement("button");
  backBtn.className = "btn btn-small";
  backBtn.textContent = "← Home";
  backBtn.addEventListener("click", () => {
    state = { ...state, view: "home", draft: null, error: null };
    renderBoard();
  });
  actions.appendChild(backBtn);
  decomposeBoard.appendChild(actions);
}

async function approveDraft() {
  if (state.submitting) return;
  state = { ...state, submitting: true, error: null };
  renderBoard();
  try {
    const res = await fetch(`/api/decompose/domains/${encodeURIComponent(state.domain)}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checklist: state.draft.checklist, tree: state.draft.tree }),
    });
    if (!res.ok) {
      state = { ...state, submitting: false, error: "Failed to approve this draft. Please try again." };
      return;
    }
    const domain = state.domain;
    state = { ...state, submitting: false, draft: null };
    loadKnownDomains();
    selectDomain(domain);
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
  loadKnownDomains();
  const idea = sessionStorage.getItem(LAUNCHPAD_IDEA_KEY);
  if (idea) {
    sessionStorage.removeItem(LAUNCHPAD_IDEA_KEY);
    document.getElementById("decomposeIntentInput").value = idea;
    submitIntent(idea);
  }
}

init();
