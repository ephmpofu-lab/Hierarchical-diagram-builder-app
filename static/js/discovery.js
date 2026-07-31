// Discovery Session (Journey 4/5, WP20/WP21): a standalone page (like login.html) where
// the Architect Agent conducts an adaptive interview. Per the definitive product flow --
// Landing Page -> Discovery -> Engineering Workspace, nothing else -- there is no separate
// report-review screen here. The Project Initiation Report is still generated and used for
// real, deterministic project creation, but it is never displayed: clicking "Begin
// Engineering" generates it, approves it, starts the background Engineering Cycle, and
// redirects straight into the Engineering Workspace in one action, with no intermediate
// screens. Follows editor.js's reasoning-workspace pattern (full repaint per state change).

const DISCOVERY_TOPICS = [
  "business_objectives",
  "desired_outcomes",
  "current_processes",
  "pain_points",
  "stakeholders",
  "existing_systems",
  "constraints",
  "regulations",
  "success_criteria",
  "available_documentation",
];

const discoveryBoard = document.getElementById("discoveryBoard");

let session = null;
let sending = false;
let beginningEngineering = false;

function humanizeTopic(topic) {
  return topic
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

function coverageClass(status) {
  if (status === "Covered") return "covered";
  if (status === "Partial") return "partial";
  return "unexplored";
}

function renderBoard() {
  discoveryBoard.innerHTML = "";
  renderConversation();
}

function renderConversation() {
  const coverageRow = document.createElement("div");
  coverageRow.className = "discovery-topic-row";
  for (const topic of DISCOVERY_TOPICS) {
    const status = (session.topic_coverage || {})[topic] || "Unexplored";
    const chip = document.createElement("span");
    chip.className = `discovery-topic-chip ${coverageClass(status)}`;
    chip.textContent = humanizeTopic(topic);
    chip.title = status;
    coverageRow.appendChild(chip);
  }
  discoveryBoard.appendChild(coverageRow);

  const thread = document.createElement("div");
  thread.className = "discovery-thread";
  for (const turn of session.turns) {
    const bubble = document.createElement("div");
    bubble.className = `discovery-turn ${turn.role}`;
    const label = document.createElement("div");
    label.className = "discovery-turn-label";
    label.textContent = turn.role === "architect" ? "Architect Agent" : "You";
    const message = document.createElement("div");
    message.className = "discovery-turn-message";
    message.textContent = turn.message;
    bubble.appendChild(label);
    bubble.appendChild(message);
    thread.appendChild(bubble);
  }
  discoveryBoard.appendChild(thread);

  const inputRow = document.createElement("div");
  inputRow.className = "discovery-input-row";
  const input = document.createElement("textarea");
  input.className = "discovery-message-input";
  input.placeholder = "Type your reply…";
  input.rows = 3;
  input.disabled = sending || beginningEngineering;
  const sendBtn = document.createElement("button");
  sendBtn.className = "btn btn-primary";
  sendBtn.textContent = sending ? "Sending…" : "Send";
  sendBtn.disabled = sending || beginningEngineering;
  sendBtn.addEventListener("click", () => sendTurn(input.value));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendTurn(input.value);
    }
  });
  inputRow.appendChild(input);
  inputRow.appendChild(sendBtn);
  discoveryBoard.appendChild(inputRow);
  if (!beginningEngineering) input.focus();

  const actions = document.createElement("div");
  actions.className = "reasoning-actions";
  const beginBtn = document.createElement("button");
  beginBtn.className = "btn btn-primary";
  beginBtn.textContent = beginningEngineering ? "Preparing your engineering workspace…" : "Begin Engineering";
  beginBtn.disabled = beginningEngineering;
  beginBtn.addEventListener("click", beginEngineering);
  actions.appendChild(beginBtn);
  discoveryBoard.appendChild(actions);

  if (!beginningEngineering && session.status !== "ReadyForReport" && session.status !== "ReportGenerated" && session.status !== "Approved") {
    const hint = document.createElement("div");
    hint.className = "reasoning-intake-hint";
    hint.textContent =
      "The Architect Agent is still exploring the problem — you can begin engineering " +
      "early, but a few more turns usually gives it a stronger starting point.";
    discoveryBoard.appendChild(hint);
  }
}

async function sendTurn(message) {
  const trimmed = message.trim();
  if (!trimmed || sending) return;
  sending = true;
  renderBoard();
  try {
    const res = await fetch(`/api/discovery-sessions/${session.id}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: trimmed }),
    });
    if (!res.ok) {
      alert("Failed to send your reply. Please try again.");
      return;
    }
    session = await res.json();
  } finally {
    sending = false;
    renderBoard();
  }
}

function rootNodeId(project) {
  return Object.values(project.nodes).find((n) => !n.parent_id).id;
}

// One action, no intermediate screens: generate the report -> approve it -> start the
// background Engineering Cycle -> land in the Engineering Workspace. The report itself is
// never shown -- it exists only to drive real, deterministic project creation.
async function beginEngineering() {
  if (beginningEngineering) return;
  beginningEngineering = true;
  renderBoard();
  try {
    const reportRes = await fetch(`/api/discovery-sessions/${session.id}/generate-report`, { method: "POST" });
    if (!reportRes.ok) {
      alert("Failed to prepare your engineering workspace. Please try again.");
      return;
    }
    const report = await reportRes.json();

    const approveRes = await fetch(`/api/discovery-sessions/${session.id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    });
    if (!approveRes.ok) {
      alert("Failed to create the project. Please try again.");
      return;
    }
    const project = await approveRes.json();

    const cycleRes = await fetch(`/api/projects/${project.id}/nodes/${rootNodeId(project)}/engineer-architecture`, {
      method: "POST",
    });
    if (!cycleRes.ok) {
      // The project exists even if kicking off engineering failed to start -- still land
      // in the workspace rather than stranding the user with no path forward.
      window.location.href = `editor.html?project=${project.id}&workspace=engineering`;
      return;
    }
    const cycle = await cycleRes.json();
    window.location.href = `editor.html?project=${project.id}&workspace=engineering&cycle=${cycle.id}`;
  } finally {
    beginningEngineering = false;
  }
}

// The Launchpad's primary input hands off here via sessionStorage (same cross-page
// handoff pattern login.html already uses) -- read once, then clear immediately so a
// later refresh of this page doesn't resend it.
const LAUNCHPAD_IDEA_KEY = "architeq-launchpad-idea";

async function startSession() {
  discoveryBoard.innerHTML = '<div class="reasoning-empty-state">Starting your Discovery Session…</div>';
  try {
    const res = await fetch("/api/discovery-sessions", { method: "POST" });
    if (!res.ok) {
      discoveryBoard.innerHTML = '<div class="reasoning-empty-state">Could not start a Discovery Session. Please refresh to try again.</div>';
      return;
    }
    session = await res.json();
    renderBoard();

    const idea = sessionStorage.getItem(LAUNCHPAD_IDEA_KEY);
    if (idea) {
      sessionStorage.removeItem(LAUNCHPAD_IDEA_KEY);
      await sendTurn(idea);
    }
  } catch {
    discoveryBoard.innerHTML = '<div class="reasoning-empty-state">Could not reach the server. Please refresh to try again.</div>';
  }
}

startSession();
