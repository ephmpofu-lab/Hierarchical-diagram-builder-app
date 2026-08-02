// Decompose (Engineering Decomposition & Solution Generation pipeline): the app's one real
// page for the whole primary loop (AMENDMENT 4 -- 2 screens + hidden Settings). Screens 1
// and 2 are this SAME page, distinguished only by state.view -- never a navigation/redirect
// between them. Full-repaint-per-state-change, same pattern discovery.html/js established.
//
// Item 2 (new-domain flow): "drafting" (calls POST .../draft) -> "reviewing_draft" (shows
// the proposed tree + any validation violations + an Approve action, all in place -- no
// separate Validation Results page) -> "canvas" once approved. Reuses the already-built
// draft/approve endpoints verbatim; nothing backend changes for this item.
//
// Item 3 (tree visualization): "canvas" now fetches and renders the real frozen tree --
// Layers as sections, each Sub-task's Atomic steps as a row of `.reasoning-node-card`s
// (this codebase's own established "one card per node" convention, reused verbatim).
//
// Item 4 (mode toggle + rendered output): Python | n8n is a toggle on this same canvas
// state, not a separate Output page. Each mode's render is fetched once per domain and
// cached client-side so re-toggling doesn't re-fetch. n8n's diagram reuses editor.js's own
// createElementNS(SVG_NS, ...) idiom -- this codebase's only other SVG-building code --
// rather than inventing a different pattern.
//
// Item 5 (node detail panel): clicking any atomic-step card opens a slide-in drawer
// (canvas stays visible behind it -- new CSS, this app's existing `.inspector-pane` is a
// permanently-docked column, not an overlay) showing variables/requires/produces, and,
// once a mode is picked, that node's exact snippet/mapping -- found client-side in the
// already-fetched whole-domain render, no new per-node endpoint.
//
// Item 6 (persistent Command/Refine Input): a small input, always present on the canvas
// state (Railway's embedded-Agent equivalent) for mutating an already-frozen tree in place
// -- "also add a rate-limiting step to Retrieval" -- via POST .../refine. Placed right
// after the topbar so it's visible without scrolling past a long tree.

const SVG_NS = "http://www.w3.org/2000/svg";
const decomposeBoard = document.getElementById("decomposeBoard");

// 10f -- static, real example prompts (the reference mockup's own 3); fill the intent
// input on click, never auto-submit.
const DECOMPOSE_EXAMPLE_PROMPTS = [
  "I want to develop a RAG",
  "I want to automate invoice processing",
  "I want to build a support ticket triage system",
];

function formatDate(iso) {
  // Same convention library.js's own recent-projects list already established --
  // absolute date, not a fuzzy "N hours ago" precision claim.
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

let state = {
  view: "home", // "home" | "drafting" | "reviewing_draft" | "canvas"
  knownDomains: [], // List[DomainSummary] (10f) -- {domain, last_touched, atomic_step_count}
  domain: null,
  lastIntentText: "",
  draft: null, // { domain, checklist, tree, validation } from POST .../draft
  tree: null, // the frozen DomainTaskTree, once loaded for the current canvas domain
  mode: null, // "python" | "n8n" | null, canvas-state only
  pythonRender: null, // cached List[RenderedCodeBlock] for the current domain
  n8nRender: null, // cached N8nWorkflow for the current domain
  pyBrowser: { level: 1, folderIdx: null, fileIdx: null, funcId: null, docId: null }, // Python
  // mode's folder/file/function browser position (Plan 10c) + docs/ artifact (Plan 12a) --
  // reset whenever domain changes
  selectedNodeId: null, // drives the slide-in detail panel, canvas-state only
  n8nNodeConfig: {}, // step_id -> {paramName: value}, client-side/session-scoped only
  // (10b-iii) -- confirmed configuration values, merged into effective parameters at
  // badge/download time, never persisted server-side; reset whenever domain changes
  draftRevealLines: [], // [{text, status: "done"|"pending"|"failed"}] (10d) -- drives the
  // build-status panel in the "drafting" view; real, computed-from-the-actual-tree lines,
  // never a fabricated live per-attempt progress feed (propose_tree's own retry loop runs
  // entirely inside the single synchronous /draft call -- see 10d's own plan file)
  treeRevealed: false, // (10d) -- whether reviewing_draft's Tree Diagram has already
  // played its streamed layer/sub-task/atomic-step reveal for the current draft
  refineBarExpanded: false, // (10e) -- collapsed-pill vs. expanded-fields state for the
  // persistent refine bar; reset whenever domain changes
  refining: false,
  submitting: false,
  error: null,
};

function renderBoard() {
  decomposeBoard.innerHTML = "";
  decomposeBoard.classList.toggle("discovery-board-wide", state.view === "canvas");
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

  // 10f -- example chips fill the input, they never auto-submit or skip a screen (that
  // was the reference mockup's own click-through demo shortcut, not real product behavior).
  const examples = document.createElement("div");
  examples.className = "examples";
  for (const text of DECOMPOSE_EXAMPLE_PROMPTS) {
    const chip = document.createElement("div");
    chip.className = "example-chip";
    chip.textContent = text;
    chip.addEventListener("click", () => {
      input.value = text;
      input.focus();
    });
    examples.appendChild(chip);
  }
  decomposeBoard.appendChild(examples);

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
    for (const summary of state.knownDomains) {
      const row = document.createElement("div");
      row.className = "launchpad-recent-row";
      const name = document.createElement("span");
      name.className = "launchpad-recent-name";
      name.textContent = summary.domain;
      name.addEventListener("click", () => selectDomain(summary.domain));
      row.appendChild(name);
      const meta = document.createElement("span");
      meta.className = "launchpad-recent-meta";
      const stepWord = summary.atomic_step_count === 1 ? "atomic step" : "atomic steps";
      meta.textContent = `${formatDate(summary.last_touched)} · ${summary.atomic_step_count} ${stepWord}`;
      row.appendChild(meta);
      historyList.appendChild(row);
    }
    decomposeBoard.appendChild(historyList);
  }
}

// ---- Refine bar collapse/expand + idle-retract (10e) ----
// Module-level timer, not a state field -- renderBoard() tears down and rebuilds the whole
// DOM on every state change, so a fired timeout re-queries the *current* DOM/state at fire
// time rather than trusting a captured element reference from whenever it was armed.
let refineIdleTimer = null;

function armRefineIdleRetract() {
  clearTimeout(refineIdleTimer);
  refineIdleTimer = setTimeout(() => {
    const input = document.querySelector(".decompose-refine-input");
    if (state.refineBarExpanded && (!input || input.value.trim() === "")) {
      collapseRefineBar();
    }
  }, 6000);
}

function collapseRefineBar() {
  clearTimeout(refineIdleTimer);
  state = { ...state, refineBarExpanded: false };
  renderBoard();
}

function expandRefineBar() {
  state = { ...state, refineBarExpanded: true };
  renderBoard();
  const input = document.querySelector(".decompose-refine-input");
  if (input) input.focus();
  armRefineIdleRetract();
}

function renderRefineBar() {
  const bar = document.createElement("div");
  bar.className = `decompose-refine-bar ${state.refineBarExpanded ? "expanded" : "collapsed"}`;

  if (!state.refineBarExpanded) {
    const pill = document.createElement("div");
    pill.className = "decompose-refine-pill";
    pill.textContent = "✦ Refine";
    pill.addEventListener("click", expandRefineBar);
    bar.appendChild(pill);
    return bar;
  }

  const input = document.createElement("input");
  input.type = "text";
  input.className = "decompose-refine-input";
  input.placeholder = 'Refine this tree… (e.g. "also add a rate-limiting step to Retrieval")';
  input.disabled = state.refining;
  const btn = document.createElement("button");
  btn.className = "btn btn-small";
  btn.textContent = state.refining ? "Refining…" : "Refine";
  btn.disabled = state.refining;
  btn.addEventListener("click", () => submitRefine(input.value));
  input.addEventListener("input", armRefineIdleRetract);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitRefine(input.value);
    }
  });
  input.addEventListener("blur", () => {
    if (input.value.trim() === "") setTimeout(collapseRefineBar, 200);
  });
  bar.appendChild(input);
  bar.appendChild(btn);
  return bar;
}

async function submitRefine(instruction) {
  const trimmed = instruction.trim();
  if (!trimmed || state.refining) return;
  state = { ...state, refining: true, error: null };
  renderBoard();
  try {
    const res = await fetch(`/api/decompose/domains/${encodeURIComponent(state.domain)}/refine`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ instruction: trimmed }),
    });
    if (!res.ok) {
      state = { ...state, refining: false, error: "Failed to refine this tree. Please try again." };
      return;
    }
    const result = await res.json();
    if (!result.validation.passed) {
      const messages = result.validation.violations.map((v) => v.message).join("; ");
      state = { ...state, refining: false, error: `Refinement produced an invalid tree, not applied: ${messages}` };
      return;
    }
    // Applied and re-frozen server-side -- sync local state to match, and drop any
    // render caches / open detail panel since the tree itself just changed underneath them.
    // Collapses the refine bar back to a pill on success only -- an error leaves it
    // expanded so the user can see the message and retry.
    clearTimeout(refineIdleTimer);
    state = {
      ...state, refining: false, tree: result.tree, refineBarExpanded: false,
      pythonRender: null, n8nRender: null, mode: null, selectedNodeId: null, n8nNodeConfig: {},
    };
  } finally {
    renderBoard();
  }
}

// ---------- Real tree diagram (AMENDMENT 5, Fix D) ----------
// Ports editor.js's own hierarchy-canvas idiom (computeSubtreeLayout's recursive subtree-
// width-then-position algorithm, drawTreeBranches/drawTreeEdge's trunk+bus/straight-line
// connector -- editor.js:1341/2384/2472) rather than importing editor.js itself: that file's
// canvas is tightly coupled to its own global Project/Node state (drag-to-reparent handles,
// click-to-select edges, flow-particle animation), none of which applies to this read-only
// frozen tree. Only the layout math and the box-and-connector visual language are reused.

const DECOMPOSE_LEVEL_GAP = 110; // vertical gap between C4 levels
const DECOMPOSE_SIBLING_GAP = 30; // horizontal gap between sibling subtrees
const DECOMPOSE_LAYER_GAP = 60; // extra horizontal gap between separate top-level Layer trees
const DECOMPOSE_BOX_SIZES = {
  "Layer": [220, 56],
  "Sub-task": [190, 46],
  "Atomic step": [170, 40],
};
const DECOMPOSE_LEVEL_DEPTH = { "Layer": 0, "Sub-task": 1, "Atomic step": 2 };

function decomposeBoxSize(level) {
  return DECOMPOSE_BOX_SIZES[level] || DECOMPOSE_BOX_SIZES["Atomic step"];
}

function computeTreeLayout(tree) {
  const widths = new Map();

  function computeWidth(nodeId) {
    const node = tree.nodes[nodeId];
    const children = (node.children || []).filter((id) => tree.nodes[id]);
    const [ownW] = decomposeBoxSize(node.level);
    if (children.length === 0) {
      widths.set(nodeId, ownW);
      return ownW;
    }
    let total = 0;
    for (const childId of children) total += computeWidth(childId);
    total += Math.max(0, children.length - 1) * DECOMPOSE_SIBLING_GAP;
    const width = Math.max(ownW, total);
    widths.set(nodeId, width);
    return width;
  }
  for (const layerId of tree.root_ids) if (tree.nodes[layerId]) computeWidth(layerId);

  const positions = new Map(); // id -> { x, y } (box center)

  function assignPositions(nodeId, centerX) {
    const node = tree.nodes[nodeId];
    const depth = DECOMPOSE_LEVEL_DEPTH[node.level] ?? 0;
    positions.set(nodeId, { x: centerX, y: 40 + depth * DECOMPOSE_LEVEL_GAP });
    const children = (node.children || []).filter((id) => tree.nodes[id]);
    if (children.length === 0) return;
    const totalWidth = children.reduce((sum, id) => sum + widths.get(id), 0)
      + Math.max(0, children.length - 1) * DECOMPOSE_SIBLING_GAP;
    let cursor = centerX - totalWidth / 2;
    for (const childId of children) {
      const w = widths.get(childId);
      assignPositions(childId, cursor + w / 2);
      cursor += w + DECOMPOSE_SIBLING_GAP;
    }
  }

  let cursorX = 0;
  for (const layerId of tree.root_ids) {
    if (!tree.nodes[layerId]) continue;
    const w = widths.get(layerId);
    assignPositions(layerId, cursorX + w / 2);
    cursorX += w + DECOMPOSE_LAYER_GAP;
  }

  // Normalize so no box's left edge falls below a small left margin.
  let minX = Infinity;
  let maxX = -Infinity;
  for (const [id, pos] of positions) {
    const [w] = decomposeBoxSize(tree.nodes[id].level);
    minX = Math.min(minX, pos.x - w / 2);
    maxX = Math.max(maxX, pos.x + w / 2);
  }
  const shift = Number.isFinite(minX) ? -minX + 20 : 0;
  for (const pos of positions.values()) pos.x += shift;

  return { positions, totalWidth: Number.isFinite(maxX) ? maxX - minX + 40 : 400 };
}

function drawTreeDiagramEdges(node, tree, positions) {
  const group = document.createElementNS(SVG_NS, "g");
  const children = (node.children || []).filter((id) => tree.nodes[id]);
  if (children.length === 0) return group;
  const parentPos = positions.get(node.id);
  const [, parentH] = decomposeBoxSize(node.level);
  const parentBottom = parentPos.y + parentH / 2;
  const childPositions = children.map((id) => ({ id, pos: positions.get(id) }));

  if (children.length === 1) {
    const only = childPositions[0];
    const [, childH] = decomposeBoxSize(tree.nodes[only.id].level);
    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", parentPos.x);
    line.setAttribute("y1", parentBottom);
    line.setAttribute("x2", only.pos.x);
    line.setAttribute("y2", only.pos.y - childH / 2);
    line.setAttribute("class", "decompose-tree-edge");
    group.appendChild(line);
    return group;
  }

  const firstChildTop = childPositions[0].pos.y - decomposeBoxSize(tree.nodes[childPositions[0].id].level)[1] / 2;
  const busY = parentBottom + (firstChildTop - parentBottom) / 2;

  const trunk = document.createElementNS(SVG_NS, "line");
  trunk.setAttribute("x1", parentPos.x);
  trunk.setAttribute("y1", parentBottom);
  trunk.setAttribute("x2", parentPos.x);
  trunk.setAttribute("y2", busY);
  trunk.setAttribute("class", "decompose-tree-edge");
  group.appendChild(trunk);

  const xs = childPositions.map((c) => c.pos.x);
  const bus = document.createElementNS(SVG_NS, "line");
  bus.setAttribute("x1", Math.min(...xs, parentPos.x));
  bus.setAttribute("y1", busY);
  bus.setAttribute("x2", Math.max(...xs, parentPos.x));
  bus.setAttribute("y2", busY);
  bus.setAttribute("class", "decompose-tree-edge");
  group.appendChild(bus);

  for (const { id, pos } of childPositions) {
    const [, childH] = decomposeBoxSize(tree.nodes[id].level);
    const branch = document.createElementNS(SVG_NS, "line");
    branch.setAttribute("x1", pos.x);
    branch.setAttribute("y1", busY);
    branch.setAttribute("x2", pos.x);
    branch.setAttribute("y2", pos.y - childH / 2);
    branch.setAttribute("class", "decompose-tree-edge");
    group.appendChild(branch);
  }
  return group;
}

function drawTreeDiagramNode(node, pos, onAtomicClick) {
  const [w, h] = decomposeBoxSize(node.level);
  const levelClass = node.level.replace(/\s+/g, "-").toLowerCase(); // "layer" | "sub-task" | "atomic-step"
  const g = document.createElementNS(SVG_NS, "g");
  g.setAttribute("class", `decompose-tree-node level-${levelClass}`);

  const rect = document.createElementNS(SVG_NS, "rect");
  rect.setAttribute("x", pos.x - w / 2);
  rect.setAttribute("y", pos.y - h / 2);
  rect.setAttribute("width", w);
  rect.setAttribute("height", h);
  rect.setAttribute("rx", 8);
  g.appendChild(rect);

  const text = document.createElementNS(SVG_NS, "text");
  text.setAttribute("x", pos.x);
  text.setAttribute("y", pos.y + 4);
  text.setAttribute("text-anchor", "middle");
  text.textContent = node.label.length > 26 ? `${node.label.slice(0, 24)}…` : node.label;
  g.appendChild(text);

  if (node.level === "Atomic step") {
    g.addEventListener("click", () => onAtomicClick(node.id));
  }
  return g;
}

function renderTreeDiagram(tree, onAtomicClick) {
  const { positions, totalWidth } = computeTreeLayout(tree);
  const maxDepth = Math.max(...Object.values(DECOMPOSE_LEVEL_DEPTH));
  const height = 40 + maxDepth * DECOMPOSE_LEVEL_GAP + decomposeBoxSize("Atomic step")[1] / 2 + 40;
  const width = Math.max(totalWidth, 400);

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.classList.add("decompose-tree-svg");

  const edgesGroup = document.createElementNS(SVG_NS, "g");
  const nodesGroup = document.createElementNS(SVG_NS, "g");
  for (const node of Object.values(tree.nodes)) {
    edgesGroup.appendChild(drawTreeDiagramEdges(node, tree, positions));
  }
  for (const node of Object.values(tree.nodes)) {
    const pos = positions.get(node.id);
    if (pos) nodesGroup.appendChild(drawTreeDiagramNode(node, pos, onAtomicClick));
  }
  svg.appendChild(edgesGroup);
  svg.appendChild(nodesGroup);

  const wrap = document.createElement("div");
  wrap.className = "decompose-tree-diagram-wrap";
  wrap.appendChild(svg);
  return wrap;
}

function renderCanvasView() {
  const topRow = document.createElement("div");
  topRow.className = "decompose-canvas-topbar";
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = `Canvas — ${state.domain}`;
  const backBtn = document.createElement("button");
  backBtn.className = "btn btn-small";
  backBtn.textContent = "← Home";
  backBtn.addEventListener("click", () => {
    state = { ...state, view: "home", tree: null };
    renderBoard();
  });
  topRow.appendChild(heading);
  topRow.appendChild(backBtn);
  decomposeBoard.appendChild(topRow);

  if (state.tree) {
    decomposeBoard.appendChild(renderRefineBar());
  }

  if (state.error) {
    const errorBox = document.createElement("div");
    errorBox.className = "reasoning-empty-state";
    errorBox.textContent = state.error;
    decomposeBoard.appendChild(errorBox);
    if (!state.tree) return;
  }

  if (!state.tree) {
    const loading = document.createElement("div");
    loading.className = "reasoning-empty-state";
    loading.textContent = "Loading tree…";
    decomposeBoard.appendChild(loading);
    return;
  }

  const tree = state.tree;
  decomposeBoard.appendChild(renderTreeDiagram(tree, (nodeId) => {
    state = { ...state, selectedNodeId: nodeId };
    renderBoard();
  }));

  const modeToggle = document.createElement("div");
  modeToggle.className = "decompose-mode-toggle";
  for (const mode of ["python", "n8n"]) {
    const btn = document.createElement("button");
    btn.className = "btn btn-small" + (state.mode === mode ? " active" : "");
    btn.textContent = mode === "python" ? "Python" : "n8n";
    btn.addEventListener("click", () => selectMode(mode));
    modeToggle.appendChild(btn);
  }
  decomposeBoard.appendChild(modeToggle);

  if (state.mode) {
    decomposeBoard.appendChild(renderOutputSection());
  }

  if (state.selectedNodeId) {
    const panel = renderNodeDetailPanel();
    if (panel) decomposeBoard.appendChild(panel);
  }
}

function metaRow(label, value) {
  const row = document.createElement("div");
  row.className = "decompose-drawer-meta-row";
  const labelEl = document.createElement("span");
  labelEl.className = "decompose-drawer-meta-label";
  labelEl.textContent = label;
  const valueEl = document.createElement("span");
  valueEl.textContent = value;
  row.appendChild(labelEl);
  row.appendChild(valueEl);
  return row;
}

// ---- Detail panel idle-retract (10e) ----
let panelIdleTimer = null;

function armPanelIdleRetract() {
  clearTimeout(panelIdleTimer);
  panelIdleTimer = setTimeout(() => {
    if (state.selectedNodeId) closeNodeDetail();
  }, 7000);
}

function closeNodeDetail() {
  clearTimeout(panelIdleTimer);
  state = { ...state, selectedNodeId: null };
  renderBoard();
}

function renderNodeDetailPanel() {
  const node = state.tree.nodes[state.selectedNodeId];
  if (!node) return null;

  const wrap = document.createElement("div");

  const backdrop = document.createElement("div");
  backdrop.className = "decompose-drawer-backdrop";
  backdrop.addEventListener("click", closeNodeDetail);
  wrap.appendChild(backdrop);

  const drawer = document.createElement("div");
  drawer.className = "decompose-drawer";

  const closeBtn = document.createElement("button");
  closeBtn.className = "btn btn-small decompose-drawer-close";
  closeBtn.textContent = "✕";
  closeBtn.addEventListener("click", closeNodeDetail);
  drawer.appendChild(closeBtn);

  const title = document.createElement("div");
  title.className = "decompose-drawer-title";
  title.textContent = node.label;
  drawer.appendChild(title);

  const meta = document.createElement("div");
  meta.className = "decompose-drawer-meta";
  meta.appendChild(metaRow("Level", node.level));
  if (node.consumes) meta.appendChild(metaRow("Consumes", node.consumes));
  if (node.produces) meta.appendChild(metaRow("Produces", node.produces));
  if (node.requires && node.requires.length > 0) {
    const requiredLabels = node.requires.map((id) => (state.tree.nodes[id] || {}).label || id).join(", ");
    meta.appendChild(metaRow("Requires", requiredLabels));
  }
  if (node.terminal_output) meta.appendChild(metaRow("Terminal output", "yes"));
  if (node.pillar_tags && node.pillar_tags.length > 0) meta.appendChild(metaRow("Pillars", node.pillar_tags.join(", ")));
  drawer.appendChild(meta);

  if (node.variables && node.variables.length > 0) {
    const varsLabel = document.createElement("div");
    varsLabel.className = "reasoning-section-label";
    varsLabel.textContent = "Variables";
    drawer.appendChild(varsLabel);
    const varsList = document.createElement("ul");
    varsList.className = "decompose-drawer-variables";
    for (const v of node.variables) {
      const item = document.createElement("li");
      item.textContent = v.default != null ? `${v.name} = ${v.default}` : v.name;
      if (v.description) item.title = v.description;
      varsList.appendChild(item);
    }
    drawer.appendChild(varsList);
  }

  if (node.rules && node.rules.length > 0) {
    const rulesLabel = document.createElement("div");
    rulesLabel.className = "reasoning-section-label";
    rulesLabel.textContent = "Rules";
    drawer.appendChild(rulesLabel);
    const rulesList = document.createElement("ul");
    rulesList.className = "decompose-drawer-rules";
    for (const rule of node.rules) {
      const item = document.createElement("li");
      item.textContent = rule;
      rulesList.appendChild(item);
    }
    drawer.appendChild(rulesList);
  }

  if (node.notes) {
    const notesLabel = document.createElement("div");
    notesLabel.className = "reasoning-section-label";
    notesLabel.textContent = "Notes";
    drawer.appendChild(notesLabel);
    const notesText = document.createElement("div");
    notesText.className = "decompose-drawer-notes";
    notesText.textContent = node.notes;
    drawer.appendChild(notesText);
  }

  if (state.mode === "python" && state.pythonRender) {
    const block = state.pythonRender.find((b) => b.step_id === node.id);
    if (block) drawer.appendChild(renderDrawerSnippet("Python", block.code));
  } else if (state.mode === "n8n" && state.n8nRender) {
    const mapped = state.n8nRender.nodes.find((n) => n.step_id === node.id);
    if (mapped) {
      const snippet = JSON.stringify({ type: mapped.type, parameters: n8nEffectiveParameters(mapped) }, null, 2);
      drawer.appendChild(renderDrawerSnippet("n8n node", snippet));
      drawer.appendChild(renderN8nConfigureSection(mapped));
    }
  }

  for (const evt of ["mousemove", "keydown", "input", "click", "scroll"]) {
    drawer.addEventListener(evt, armPanelIdleRetract);
  }
  armPanelIdleRetract();

  wrap.appendChild(drawer);
  return wrap;
}

function renderDrawerSnippet(label, code) {
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = label;
  const pre = document.createElement("pre");
  pre.className = "decompose-code-block";
  const codeEl = document.createElement("code");
  codeEl.textContent = code;
  pre.appendChild(codeEl);
  const container = document.createElement("div");
  container.appendChild(heading);
  container.appendChild(pre);
  return container;
}

// ---- Configuration mechanism (10b-iii): chip selection -> confirm -> collapse ----

function renderN8nConfigureSection(mapped) {
  const container = document.createElement("div");
  const effective = n8nEffectiveParameters(mapped);
  const emptyKeys = Object.keys(mapped.parameters || {}).filter((key) => effective[key] === "");
  if (emptyKeys.length === 0) return container; // already fully configured -- nothing to show

  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = "Configure";
  container.appendChild(heading);

  const draft = {}; // local working copy for this open drawer, keyed by param name
  let saveBtn;

  function updateSaveState() {
    const allFilled = emptyKeys.every((key) => (draft[key] || "").trim().length > 0);
    saveBtn.disabled = !allFilled;
  }

  for (const key of emptyKeys) {
    draft[key] = "";
    const row = document.createElement("div");
    row.className = "decompose-n8n-config-row";

    const label = document.createElement("div");
    label.className = "decompose-n8n-config-label";
    label.textContent = key;
    row.appendChild(label);

    const options = (mapped.parameter_options || {})[key];
    if (options && options.length > 0) {
      const chipWrap = document.createElement("div");
      chipWrap.className = "decompose-n8n-config-chips";
      for (const opt of options) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "decompose-n8n-config-chip";
        chip.textContent = opt;
        chip.addEventListener("click", () => {
          draft[key] = opt;
          for (const c of chipWrap.children) c.classList.remove("selected");
          chip.classList.add("selected");
          updateSaveState();
        });
        chipWrap.appendChild(chip);
      }
      row.appendChild(chipWrap);
    } else {
      const input = document.createElement("input");
      input.type = "text";
      input.className = "decompose-n8n-config-input";
      input.placeholder = `Enter ${key}…`;
      input.addEventListener("input", () => {
        draft[key] = input.value;
        updateSaveState();
      });
      row.appendChild(input);
    }

    container.appendChild(row);
  }

  saveBtn = document.createElement("button");
  saveBtn.className = "btn btn-small decompose-n8n-config-save";
  saveBtn.textContent = "Save configuration";
  saveBtn.disabled = true;
  saveBtn.addEventListener("click", () => {
    state = {
      ...state,
      n8nNodeConfig: {
        ...state.n8nNodeConfig,
        [mapped.step_id]: { ...state.n8nNodeConfig[mapped.step_id], ...draft },
      },
    };
    renderBoard();
  });
  container.appendChild(saveBtn);

  return container;
}

async function downloadPythonPackage(domain) {
  const res = await fetch("/api/decompose/render/python/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain }),
  });
  if (!res.ok) return;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${domain}_python.zip`;
  a.click();
  URL.revokeObjectURL(url);
}

function renderOutputSection() {
  const section = document.createElement("div");
  section.className = "decompose-output-section";

  if (state.mode === "python") {
    section.appendChild(renderPythonBrowser());
    const downloadBtn = document.createElement("button");
    downloadBtn.className = "btn btn-small";
    downloadBtn.textContent = "Download Python package (.zip)";
    downloadBtn.addEventListener("click", () => downloadPythonPackage(state.domain));
    section.appendChild(downloadBtn);
    return section;
  }

  // n8n
  if (!state.n8nRender) {
    section.textContent = "Rendering…";
    return section;
  }
  const diagramWrap = document.createElement("div");
  diagramWrap.className = "decompose-n8n-diagram-wrap";
  diagramWrap.appendChild(renderN8nDiagram(state.n8nRender));
  section.appendChild(diagramWrap);
  const downloadBtn = document.createElement("button");
  downloadBtn.className = "btn btn-small";
  downloadBtn.textContent = "Download workflow.json";
  downloadBtn.addEventListener("click", () => downloadWorkflowJson(state.n8nRender, state.domain));
  section.appendChild(downloadBtn);
  return section;
}

// ---- Python folder/file/function browser (Plan 10c) ----
// No backend change needed: state.tree already carries every Atomic step's parent_id
// chain (Atomic step -> Sub-task -> Layer), and state.pythonRender already carries each
// step's real generated code, keyed by the same step id. Folder = Layer, file = Sub-task,
// grouped client-side by joining the two, preserving pythonRender's own topological order.

function pySlug(text) {
  return (text || "").toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "module";
}
function pyFileName(label) {
  return `${pySlug(label)}.py`;
}
function pyFolderName(label) {
  return `${pySlug(label)}/`;
}
function pyFunctionName(block) {
  const match = /^def\s+([a-zA-Z0-9_]+)\s*\(/.exec(block.code || "");
  return match ? match[1] : block.label;
}

function groupPythonRenderByFile(tree, pythonRender) {
  const packageName = `architeq_${pySlug(state.domain)}/`;
  const folders = [];
  const folderIndex = new Map(); // Layer node id -> folder entry
  const fileIndex = new Map(); // Sub-task node id -> file entry
  let rootFolder = null;
  let rootFile = null;

  for (const block of pythonRender) {
    const atomicNode = tree.nodes[block.step_id];
    const subTask = atomicNode && atomicNode.parent_id ? tree.nodes[atomicNode.parent_id] : null;
    const layer = subTask && subTask.parent_id ? tree.nodes[subTask.parent_id] : null;

    if (!subTask || !layer) {
      // Shouldn't happen given R2's C4 nesting, but never silently drop a block --
      // same "always account for it" posture as NT3's Code-node fallback.
      if (!rootFolder) { rootFolder = { label: "(root)", files: [] }; folders.push(rootFolder); }
      if (!rootFile) { rootFile = { label: "(unresolved)", blocks: [] }; rootFolder.files.push(rootFile); }
      rootFile.blocks.push(block);
      continue;
    }

    let folder = folderIndex.get(layer.id);
    if (!folder) {
      folder = { label: layer.label, files: [] };
      folderIndex.set(layer.id, folder);
      folders.push(folder);
    }
    let file = fileIndex.get(subTask.id);
    if (!file) {
      file = { label: subTask.label, blocks: [] };
      fileIndex.set(subTask.id, file);
      folder.files.push(file);
    }
    file.blocks.push(block);
  }

  return { packageName, folders };
}

function renderPythonBrowser() {
  const wrap = document.createElement("div");
  wrap.className = "decompose-py-browser";

  if (!state.tree || !state.pythonRender) {
    wrap.textContent = "Rendering…";
    return wrap;
  }

  const grouped = groupPythonRenderByFile(state.tree, state.pythonRender);
  const pb = state.pyBrowser || { level: 1, folderIdx: null, fileIdx: null, funcId: null };

  wrap.appendChild(renderPyCrumbs(grouped, pb));

  if (pb.docId != null) {
    wrap.appendChild(renderDocArtifact(grouped, pb.docId));
  } else if (pb.folderIdx == null || pb.fileIdx == null) {
    wrap.appendChild(renderPyLevel1(grouped));
  } else if (pb.funcId == null) {
    wrap.appendChild(renderPyLevel2(grouped, pb));
  } else {
    wrap.appendChild(renderPyLevel3(grouped, pb));
  }

  if (pb.fileIdx != null) {
    wrap.appendChild(renderPythonSidePanel(grouped, pb));
  }

  return wrap;
}

function pyCrumbSep() {
  const sep = document.createElement("span");
  sep.className = "decompose-py-crumb-sep";
  sep.textContent = "›";
  return sep;
}

function setPyBrowserState(next) {
  state = { ...state, pyBrowser: { level: 1, folderIdx: null, fileIdx: null, funcId: null, docId: null, ...next } };
  renderBoard();
}

// ---- docs/ folder: current domain's own planning artifacts (Plan 12a) ----
// Not ARCHITEQ's own self-documentation -- these are the RAG-project-equivalent's PRD,
// TDD, etc., sitting next to that domain's own architeq_{domain}/ code folder. Per the
// resolved scope, only the Engineering-Plan-equivalent has a real per-domain generator
// today (Modules 5-8, already rendered by the browser above); the other five show R40's
// honest "not generated yet" state until their own generators exist.
const DOC_ARTIFACTS = [
  { id: "prd", file: "PRD.md" },
  { id: "tdd", file: "TDD.md" },
  { id: "app_flow", file: "AppFlow.md" },
  { id: "design_brief", file: "DesignBrief.md" },
  { id: "backend_schema", file: "BackendSchema.md" },
  { id: "engineering_plan", file: "EngineeringPlan.md" },
];

function docArtifactStatus(artifactId) {
  if (artifactId === "engineering_plan") {
    return { status: "built" };
  }
  if (artifactId === "prd") {
    return {
      status: "missing",
      blockedReason: "Depends on Module 11's Stage -3 (Requirements Engineering), not yet built.",
    };
  }
  return {
    status: "missing",
    blockedReason: "No generator scoped for this artifact yet (see ARCHITEQ-PRD.md OQ6).",
  };
}

function renderHubAndSpoke(hub, spokes) {
  if (spokes.length > 6) {
    throw new Error(`renderHubAndSpoke supports at most 6 spokes; got ${spokes.length}`);
  }
  const container = document.createElement("div");
  container.className = "decompose-hub-diagram";

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "decompose-hub-connectors");
  container.appendChild(svg);

  const positions = ["pos-tl", "pos-tr", "pos-ml", "pos-mr", "pos-bl", "pos-br"];
  const spokeEls = [];
  spokes.forEach((spoke, i) => {
    const spokeEl = document.createElement("div");
    spokeEl.className = `decompose-spoke ${positions[i]}`;
    const titleEl = document.createElement("div");
    titleEl.className = "decompose-spoke-title";
    titleEl.textContent = spoke.title;
    spokeEl.appendChild(titleEl);
    (spoke.items || []).forEach((item) => {
      const itemEl = document.createElement("div");
      itemEl.className = "decompose-spoke-item";
      itemEl.textContent = item;
      spokeEl.appendChild(itemEl);
    });
    if (spoke.onClick) {
      spokeEl.classList.add("decompose-spoke-clickable");
      spokeEl.addEventListener("click", spoke.onClick);
    }
    container.appendChild(spokeEl);
    spokeEls.push(spokeEl);
  });

  const hubEl = document.createElement("div");
  hubEl.className = "decompose-hub";
  const hubTitle = document.createElement("div");
  hubTitle.className = "decompose-hub-title";
  hubTitle.textContent = hub.title;
  const hubSubtitle = document.createElement("div");
  hubSubtitle.className = "decompose-hub-subtitle";
  hubSubtitle.textContent = hub.subtitle;
  const hubDesc = document.createElement("div");
  hubDesc.className = "decompose-hub-desc";
  hubDesc.textContent = hub.desc;
  hubEl.appendChild(hubTitle);
  hubEl.appendChild(hubSubtitle);
  hubEl.appendChild(hubDesc);
  container.appendChild(hubEl);

  const drawConnectors = () => {
    const rect = container.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${rect.width} ${rect.height}`);
    svg.innerHTML = "";
    const hubRect = hubEl.getBoundingClientRect();
    const hubCenter = {
      x: hubRect.left - rect.left + hubRect.width / 2,
      y: hubRect.top - rect.top + hubRect.height / 2,
    };
    spokeEls.forEach((spokeEl) => {
      const sr = spokeEl.getBoundingClientRect();
      const onLeft = sr.left < hubRect.left;
      const sx = sr.left - rect.left + (onLeft ? sr.width : 0);
      const sy = sr.top - rect.top + sr.height / 2;
      const hx = hubCenter.x + (onLeft ? -hubRect.width / 2 : hubRect.width / 2);
      const midX = (sx + hx) / 2;
      const path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", `M${sx},${sy} C${midX},${sy} ${midX},${hubCenter.y} ${hx},${hubCenter.y}`);
      path.setAttribute("class", "decompose-hub-conn");
      svg.appendChild(path);
    });
  };
  setTimeout(drawConnectors, 30);
  window.addEventListener("resize", drawConnectors);

  return container;
}

function renderDocArtifact(grouped, docId) {
  const el = document.createElement("div");
  el.className = "decompose-py-level decompose-py-level-3";
  const doc = DOC_ARTIFACTS.find((d) => d.id === docId);
  const status = docArtifactStatus(docId);

  if (status.status === "missing") {
    const banner = document.createElement("div");
    banner.className = "decompose-py-doc-missing";
    const icon = document.createElement("span");
    icon.className = "decompose-py-doc-missing-icon";
    icon.textContent = "⚠";
    const text = document.createElement("span");
    text.textContent = `${doc.file} has not been generated for this domain yet. ${status.blockedReason}`;
    banner.appendChild(icon);
    banner.appendChild(text);
    el.appendChild(banner);
    return el;
  }

  const hub = {
    title: "Engineering Plan",
    subtitle: doc.file,
    desc: `${state.domain} — ${grouped.folders.length} layer${grouped.folders.length === 1 ? "" : "s"}, derived from the frozen tree's topological build order (R10).`,
  };
  const spokes = grouped.folders.map((folder, folderIdx) => ({
    title: folder.label,
    items: folder.files.map((f) => pyFileName(f.label)),
    onClick: () => setPyBrowserState({ folderIdx, fileIdx: 0 }),
  }));
  el.appendChild(renderHubAndSpoke(hub, spokes));
  return el;
}

function renderPyCrumbs(grouped, pb) {
  const crumbs = document.createElement("div");
  crumbs.className = "decompose-py-crumbs";

  const pkgSpan = document.createElement("span");
  pkgSpan.textContent = grouped.packageName;
  pkgSpan.addEventListener("click", () => setPyBrowserState({}));
  crumbs.appendChild(pkgSpan);

  if (pb.docId != null) {
    const doc = DOC_ARTIFACTS.find((d) => d.id === pb.docId);
    crumbs.appendChild(pyCrumbSep());
    const docSpan = document.createElement("span");
    docSpan.className = "decompose-py-crumb-current";
    docSpan.textContent = doc ? doc.file : "";
    crumbs.appendChild(docSpan);
    return crumbs;
  }

  if (pb.folderIdx != null && pb.fileIdx != null) {
    const file = grouped.folders[pb.folderIdx].files[pb.fileIdx];
    crumbs.appendChild(pyCrumbSep());
    const fileSpan = document.createElement("span");
    fileSpan.textContent = pyFileName(file.label);
    fileSpan.addEventListener("click", () => setPyBrowserState({ folderIdx: pb.folderIdx, fileIdx: pb.fileIdx }));
    crumbs.appendChild(fileSpan);
  }
  if (pb.funcId != null) {
    const file = grouped.folders[pb.folderIdx].files[pb.fileIdx];
    const block = file.blocks.find((b) => b.step_id === pb.funcId);
    crumbs.appendChild(pyCrumbSep());
    const funcSpan = document.createElement("span");
    funcSpan.className = "decompose-py-crumb-current";
    funcSpan.textContent = block ? `${pyFunctionName(block)}()` : "";
    crumbs.appendChild(funcSpan);
  }
  return crumbs;
}

function renderPyLevel1(grouped) {
  const el = document.createElement("div");
  el.className = "decompose-py-level decompose-py-level-1";

  const docsFolderRow = document.createElement("div");
  docsFolderRow.className = "decompose-py-folder-row";
  docsFolderRow.textContent = "docs/";
  el.appendChild(docsFolderRow);

  const docsChildren = document.createElement("div");
  docsChildren.className = "decompose-py-children";
  DOC_ARTIFACTS.forEach((doc) => {
    const status = docArtifactStatus(doc.id);
    const row = document.createElement("div");
    row.className = "decompose-py-file-row";
    const nameSpan = document.createElement("span");
    nameSpan.textContent = doc.file;
    row.appendChild(nameSpan);
    if (status.status === "missing") {
      const badge = document.createElement("span");
      badge.className = "decompose-py-doc-badge";
      badge.textContent = "not generated yet";
      row.appendChild(badge);
    }
    const chev = document.createElement("span");
    chev.className = "decompose-py-chev";
    chev.textContent = "›";
    row.appendChild(chev);
    row.addEventListener("click", () => setPyBrowserState({ docId: doc.id }));
    docsChildren.appendChild(row);
  });
  el.appendChild(docsChildren);

  grouped.folders.forEach((folder, folderIdx) => {
    const folderRow = document.createElement("div");
    folderRow.className = "decompose-py-folder-row";
    folderRow.textContent = pyFolderName(folder.label);
    el.appendChild(folderRow);

    const children = document.createElement("div");
    children.className = "decompose-py-children";
    folder.files.forEach((file, fileIdx) => {
      const fileRow = document.createElement("div");
      fileRow.className = "decompose-py-file-row";
      const nameSpan = document.createElement("span");
      nameSpan.textContent = pyFileName(file.label);
      const countSpan = document.createElement("span");
      countSpan.className = "decompose-py-file-count";
      countSpan.textContent = `(${file.blocks.length} function${file.blocks.length === 1 ? "" : "s"})`;
      const chev = document.createElement("span");
      chev.className = "decompose-py-chev";
      chev.textContent = "›";
      fileRow.appendChild(nameSpan);
      fileRow.appendChild(countSpan);
      fileRow.appendChild(chev);
      fileRow.addEventListener("click", () => setPyBrowserState({ folderIdx, fileIdx }));
      children.appendChild(fileRow);
    });
    el.appendChild(children);
  });
  return el;
}

function renderPyLevel2(grouped, pb) {
  const el = document.createElement("div");
  el.className = "decompose-py-level decompose-py-level-2";
  const file = grouped.folders[pb.folderIdx].files[pb.fileIdx];

  const chain = document.createElement("div");
  chain.className = "decompose-py-func-chain";
  file.blocks.forEach((block, i) => {
    if (i > 0) {
      const prevNode = state.tree.nodes[file.blocks[i - 1].step_id];
      const connector = document.createElement("div");
      connector.className = "decompose-py-func-connector";
      if (prevNode && prevNode.produces) {
        const label = document.createElement("span");
        label.className = "decompose-py-func-portlabel";
        label.textContent = prevNode.produces;
        connector.appendChild(label);
      }
      chain.appendChild(connector);
    }
    const node = state.tree.nodes[block.step_id];
    const row = document.createElement("div");
    row.className = "decompose-py-func-row";
    const nameEl = document.createElement("div");
    nameEl.className = "decompose-py-func-name";
    nameEl.textContent = `${pyFunctionName(block)}()`;
    row.appendChild(nameEl);
    if (node && node.notes) {
      const descEl = document.createElement("div");
      descEl.className = "decompose-py-func-desc";
      descEl.textContent = node.notes;
      row.appendChild(descEl);
    }
    row.addEventListener("click", () => setPyBrowserState({ folderIdx: pb.folderIdx, fileIdx: pb.fileIdx, funcId: block.step_id }));
    chain.appendChild(row);
  });
  el.appendChild(chain);
  return el;
}

function renderPyCodeBlock(code) {
  const container = document.createElement("div");
  container.className = "decompose-py-code-block";
  const copyBtn = document.createElement("button");
  copyBtn.className = "decompose-py-copy-btn";
  copyBtn.textContent = "copy";
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(code).then(() => {
      copyBtn.textContent = "copied ✓";
      setTimeout(() => { copyBtn.textContent = "copy"; }, 1400);
    });
  });
  const pre = document.createElement("pre");
  pre.className = "decompose-code-block";
  const codeEl = document.createElement("code");
  codeEl.textContent = code;
  pre.appendChild(codeEl);
  container.appendChild(copyBtn);
  container.appendChild(pre);
  return container;
}

function renderPyLevel3(grouped, pb) {
  const el = document.createElement("div");
  el.className = "decompose-py-level decompose-py-level-3";
  const file = grouped.folders[pb.folderIdx].files[pb.fileIdx];
  const block = file.blocks.find((b) => b.step_id === pb.funcId);
  if (!block) return el;
  const node = state.tree.nodes[block.step_id];

  el.appendChild(renderPyCodeBlock(block.code));

  if (node) {
    const meta = document.createElement("div");
    meta.className = "decompose-py-meta-line";
    const requiredLabels = (node.requires || []).map((id) => (state.tree.nodes[id] || {}).label || id);
    const parts = [
      `requires: ${requiredLabels.length ? requiredLabels.join(", ") : "—"}`,
      `produces: ${node.produces || "—"}`,
    ];
    if (node.rules && node.rules.length) parts.push(`rules: ${node.rules.join("; ")}`);
    meta.textContent = parts.join("  ·  ");
    el.appendChild(meta);
  }
  return el;
}

// Import lines are DERIVED from what the generated code actually uses, never asserted
// upfront -- so nothing appears here that isn't justified by code visible right below it.
// Today's render_python output is a "# TODO: implement" stub, so this rarely triggers yet;
// the mechanism is real and starts producing real import lines the moment generated code
// stops being a stub, not before.
const PY_IMPORT_TRIGGERS = [
  { pattern: /unicodedata\./, line: "import unicodedata" },
  { pattern: /requests\./, line: "import requests" },
  { pattern: /log\.(warning|error|info)/, line: "import logging\nlog = logging.getLogger(__name__)" },
  { pattern: /Path\(/, line: "from pathlib import Path" },
];
function pyDeriveImports(codeBlocks) {
  const found = [];
  for (const code of codeBlocks) {
    for (const trigger of PY_IMPORT_TRIGGERS) {
      if (trigger.pattern.test(code) && !found.includes(trigger.line)) found.push(trigger.line);
    }
  }
  return found;
}

function renderPythonSidePanel(grouped, pb) {
  const file = grouped.folders[pb.folderIdx].files[pb.fileIdx];
  const panel = document.createElement("div");
  panel.className = "decompose-py-side-panel";

  const header = document.createElement("div");
  header.className = "decompose-py-side-header";
  const titleWrap = document.createElement("div");
  const title = document.createElement("div");
  title.className = "decompose-py-side-title";
  title.textContent = file.label;
  const subtitle = document.createElement("div");
  subtitle.className = "decompose-py-side-subtitle";
  subtitle.textContent = pyFileName(file.label);
  const status = document.createElement("div");
  status.className = "decompose-py-side-status";
  status.textContent = `complete — ${file.blocks.length} function${file.blocks.length === 1 ? "" : "s"}`;
  titleWrap.appendChild(title);
  titleWrap.appendChild(subtitle);
  titleWrap.appendChild(status);
  const closeBtn = document.createElement("span");
  closeBtn.className = "decompose-drawer-close";
  closeBtn.textContent = "close ×";
  closeBtn.addEventListener("click", () => setPyBrowserState({ folderIdx: pb.folderIdx, fileIdx: pb.fileIdx }));
  header.appendChild(titleWrap);
  header.appendChild(closeBtn);
  panel.appendChild(header);

  const copyBtn = document.createElement("button");
  copyBtn.className = "decompose-py-copy-btn";
  copyBtn.textContent = "copy";
  const fullCode = file.blocks.map((b) => b.code).join("\n\n");
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(fullCode).then(() => {
      copyBtn.textContent = "copied ✓";
      setTimeout(() => { copyBtn.textContent = "copy"; }, 1400);
    });
  });

  const pre = document.createElement("pre");
  pre.className = "decompose-code-block";
  const codeEl = document.createElement("code");
  const imports = pyDeriveImports(file.blocks.map((b) => b.code));
  if (imports.length) {
    codeEl.appendChild(document.createTextNode(imports.join("\n") + "\n\n\n"));
  }
  file.blocks.forEach((b, i) => {
    const span = document.createElement("span");
    span.id = `decompose-py-side-fn-${b.step_id}`;
    span.className = "decompose-py-side-fn-code";
    span.textContent = b.code + (i < file.blocks.length - 1 ? "\n\n" : "");
    codeEl.appendChild(span);
  });
  pre.appendChild(codeEl);

  const codeContainer = document.createElement("div");
  codeContainer.className = "decompose-py-code-block";
  codeContainer.appendChild(copyBtn);
  codeContainer.appendChild(pre);
  panel.appendChild(codeContainer);

  if (pb.funcId) {
    setTimeout(() => {
      const target = document.getElementById(`decompose-py-side-fn-${pb.funcId}`);
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      target.classList.add("decompose-py-side-fn-highlight");
      setTimeout(() => target.classList.remove("decompose-py-side-fn-highlight"), 900);
    }, 30);
  }

  return panel;
}

// ---- SVG routing rewrite (10a-iii, CR2/CR5/CR6/CR7/CR16) ----
// roundedPolylinePath is the one shared geometry function every classification's waypoints
// run through -- CR18's own discipline (classify first, one function per class supplies
// waypoints only, geometry/rounding is never re-implemented per class).

function _n8nDistance(a, b) {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

function _n8nPointTowards(from, to, dist) {
  const total = _n8nDistance(from, to);
  if (total === 0) return { x: from.x, y: from.y };
  const t = Math.min(dist, total) / total;
  return { x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t };
}

function roundedPolylinePath(points, radius) {
  if (points.length < 2) return "";
  if (points.length === 2) {
    return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
  }
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const next = points[i + 1];
    const r = Math.min(radius, _n8nDistance(prev, curr) / 2, _n8nDistance(curr, next) / 2);
    const p1 = _n8nPointTowards(curr, prev, r);
    const p2 = _n8nPointTowards(curr, next, r);
    d += ` L ${p1.x} ${p1.y} Q ${curr.x} ${curr.y} ${p2.x} ${p2.y}`;
  }
  const last = points[points.length - 1];
  d += ` L ${last.x} ${last.y}`;
  return d;
}

const N8N_CORNER_RADIUS = 12;
const N8N_LANE_OFFSET = 30; // whitespace lane below a row, for local_branch routing (CR6)

function _n8nBuildWaypoints(classification, outPort, inPort) {
  switch (classification) {
    case "adjacent":
      return [outPort, inPort];
    case "local_branch": {
      const laneY = Math.max(outPort.y, inPort.y) + N8N_LANE_OFFSET;
      return [outPort, { x: outPort.x, y: laneY }, { x: inPort.x, y: laneY }, inPort];
    }
    default: {
      // row_transition | cross_row | cross_stage | long_distance -- a standard elbow;
      // the path's final waypoint is always inPort, so it always enters the target's
      // normal left port regardless of class (CR16).
      const midX = (outPort.x + inPort.x) / 2;
      return [outPort, { x: midX, y: outPort.y }, { x: midX, y: inPort.y }, inPort];
    }
  }
}

function n8nEffectiveParameters(node) {
  // 10b-iii -- merges any client-side/session-scoped confirmed config (state.n8nNodeConfig)
  // over the node's own real parameters. Never persisted server-side; lost on reload,
  // matching this app's standing "stateless per-request execution" scope decision.
  const confirmed = state.n8nNodeConfig[node.step_id];
  return confirmed ? { ...node.parameters, ...confirmed } : node.parameters;
}

function n8nNeedsConfiguration(node) {
  // A node needs configuration when one of its own real n8n parameters is still sitting at
  // the schema's own empty placeholder (_build_parameters, node_mapper.py, never overlaid a
  // real declared Variable.default onto it), and no confirmed config has filled it in yet.
  // Nested/non-string values (Set's assignments, If's conditions) are structural, not
  // "needs a value" in this same sense, and are left alone deliberately.
  return Object.values(n8nEffectiveParameters(node) || {}).some((v) => v === "");
}

function renderN8nDiagram(workflow) {
  const boxWidth = 180;
  const boxHeight = 58;
  const padding = 40;
  const zones = workflow.stage_zones || [];

  const maxRight = zones.length
    ? Math.max(...zones.map((z) => z.x + z.width))
    : Math.max(boxWidth, ...workflow.nodes.map((n) => n.position[0] + boxWidth));
  const maxBottom = zones.length
    ? Math.max(...zones.map((z) => z.y + z.height))
    : Math.max(boxHeight, ...workflow.nodes.map((n) => n.position[1] + boxHeight));

  const totalWidth = maxRight + padding * 2;
  const totalHeight = maxBottom + padding * 2;
  // The viewport is capped, not the full content extent -- a wide/tall tree (RAG's 32
  // atomic steps) is explored by dragging and scrolling the wheel (10a-iv), not by a
  // native scrollbar sized to the whole tree.
  const viewportWidth = Math.min(totalWidth, 1100);
  const viewportHeight = Math.min(totalHeight, 640);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("width", viewportWidth);
  svg.setAttribute("height", viewportHeight);
  svg.setAttribute("viewBox", `0 0 ${viewportWidth} ${viewportHeight}`);
  svg.classList.add("decompose-n8n-diagram");

  const viewport = document.createElementNS(SVG_NS, "g");
  viewport.classList.add("decompose-n8n-viewport");

  // Stage-zone backgrounds drawn first, behind everything (CR2: visual group only, never
  // a connection anchor -- no connection below ever originates/terminates at a zone).
  for (const zone of zones) {
    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", zone.x + padding);
    rect.setAttribute("y", zone.y + padding);
    rect.setAttribute("width", zone.width);
    rect.setAttribute("height", zone.height);
    rect.setAttribute("rx", "6");
    rect.setAttribute("class", "decompose-n8n-stage-zone");
    viewport.appendChild(rect);

    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", zone.x + padding + 10);
    label.setAttribute("y", zone.y + padding + 18);
    label.setAttribute("class", "decompose-n8n-stage-zone-label");
    label.textContent = zone.label;
    viewport.appendChild(label);
  }

  const nodeByName = {};
  for (const node of workflow.nodes) nodeByName[node.name] = node;
  const classificationByPair = {};
  for (const c of workflow.connection_classifications || []) {
    classificationByPair[`${c.source_step_id} ${c.target_step_id}`] = c.classification;
  }

  function portOf(node, side) {
    const x = node.position[0] + padding + (side === "output" ? boxWidth : 0);
    const y = node.position[1] + padding + boxHeight / 2;
    return { x, y };
  }

  // Connections drawn first so node boxes sit on top of the lines.
  for (const [sourceName, outputs] of Object.entries(workflow.connections)) {
    const source = nodeByName[sourceName];
    const targets = (outputs.main && outputs.main[0]) || [];
    for (const conn of targets) {
      const target = nodeByName[conn.node];
      if (!source || !target) continue;
      const classification = classificationByPair[`${source.step_id} ${target.step_id}`] || "adjacent";
      const waypoints = _n8nBuildWaypoints(classification, portOf(source, "output"), portOf(target, "input"));
      const path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", roundedPolylinePath(waypoints, N8N_CORNER_RADIUS));
      path.setAttribute("class", "decompose-n8n-connection");
      path.setAttribute("data-classification", classification);
      viewport.appendChild(path);
    }
  }

  for (const node of workflow.nodes) {
    const group = document.createElementNS(SVG_NS, "g");
    group.addEventListener("mouseenter", (evt) => showN8nHoverPayload(evt, node));
    group.addEventListener("mousemove", (evt) => showN8nHoverPayload(evt, node));
    group.addEventListener("mouseleave", hideN8nHoverPayload);
    group.addEventListener("click", () => {
      state = { ...state, selectedNodeId: node.step_id };
      renderBoard();
    });
    group.classList.add("decompose-n8n-node-group");

    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", node.position[0] + padding);
    rect.setAttribute("y", node.position[1] + padding);
    rect.setAttribute("width", boxWidth);
    rect.setAttribute("height", boxHeight);
    rect.setAttribute("rx", "8");
    rect.setAttribute("class", "decompose-n8n-node-rect");
    group.appendChild(rect);

    // Two distinct labels (CR11): display name and real n8n type, never merged into one.
    const text = document.createElementNS(SVG_NS, "text");
    text.setAttribute("x", node.position[0] + padding + boxWidth / 2);
    text.setAttribute("y", node.position[1] + padding + 22);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("class", "decompose-n8n-node-text");
    text.setAttribute("pointer-events", "none"); // hover events land on the group, not this text
    text.textContent = node.name.length > 22 ? `${node.name.slice(0, 20)}…` : node.name;
    group.appendChild(text);

    const typeText = document.createElementNS(SVG_NS, "text");
    typeText.setAttribute("x", node.position[0] + padding + boxWidth / 2);
    typeText.setAttribute("y", node.position[1] + padding + 40);
    typeText.setAttribute("text-anchor", "middle");
    typeText.setAttribute("class", "decompose-n8n-node-type-text");
    typeText.setAttribute("pointer-events", "none");
    typeText.textContent = node.type;
    group.appendChild(typeText);

    // Visible input/output ports (CR7) -- every connection's endpoint coincides exactly
    // with one of these, never an approximate edge of the box's bounding rect.
    for (const side of ["input", "output"]) {
      const port = portOf(node, side);
      const circle = document.createElementNS(SVG_NS, "circle");
      circle.setAttribute("cx", port.x);
      circle.setAttribute("cy", port.y);
      circle.setAttribute("r", "4");
      circle.setAttribute("class", "decompose-n8n-port");
      circle.setAttribute("pointer-events", "none");
      group.appendChild(circle);
    }

    if (n8nNeedsConfiguration(node)) {
      const badge = document.createElementNS(SVG_NS, "circle");
      badge.setAttribute("cx", node.position[0] + padding + boxWidth - 10);
      badge.setAttribute("cy", node.position[1] + padding + 10);
      badge.setAttribute("r", "5");
      badge.setAttribute("class", "decompose-n8n-needs-config-badge");
      badge.setAttribute("pointer-events", "none");
      group.appendChild(badge);
    }

    viewport.appendChild(group);
  }

  svg.appendChild(viewport);
  attachN8nPanZoom(svg, viewport);
  return svg;
}

// ---- Pan (middle-mouse drag) + zoom (cursor-centered scroll-wheel), 10a-iv ----

const N8N_MIN_SCALE = 0.2;
const N8N_MAX_SCALE = 3;

function attachN8nPanZoom(svg, viewport) {
  let scale = 1;
  let tx = 0;
  let ty = 0;
  let dragging = false;
  let dragStart = null;

  function applyTransform() {
    viewport.setAttribute("transform", `translate(${tx} ${ty}) scale(${scale})`);
  }

  svg.addEventListener("mousedown", (evt) => {
    if (evt.button !== 1) return; // middle mouse only -- left click stays free for later
    evt.preventDefault(); // suppresses the browser's native middle-click autoscroll icon
    dragging = true;
    dragStart = { x: evt.clientX, y: evt.clientY, tx0: tx, ty0: ty };
  });

  svg.addEventListener("mousemove", (evt) => {
    if (!dragging || !dragStart) return;
    tx = dragStart.tx0 + (evt.clientX - dragStart.x);
    ty = dragStart.ty0 + (evt.clientY - dragStart.y);
    applyTransform();
  });

  function stopDrag() {
    dragging = false;
    dragStart = null;
  }
  svg.addEventListener("mouseup", stopDrag);
  svg.addEventListener("mouseleave", stopDrag);

  svg.addEventListener(
    "wheel",
    (evt) => {
      evt.preventDefault();
      const rect = svg.getBoundingClientRect();
      const mouseX = evt.clientX - rect.left;
      const mouseY = evt.clientY - rect.top;
      const zoomFactor = evt.deltaY < 0 ? 1.1 : 1 / 1.1;
      const newScale = Math.min(N8N_MAX_SCALE, Math.max(N8N_MIN_SCALE, scale * zoomFactor));
      // Zoom-to-point: convert the cursor to current world-space coordinates, then solve
      // for the translate that keeps that same world point stationary under the cursor
      // at the new scale -- never a "zoom to center" that would drift the diagram away
      // from where the user is actually looking.
      const worldX = (mouseX - tx) / scale;
      const worldY = (mouseY - ty) / scale;
      tx = mouseX - worldX * newScale;
      ty = mouseY - worldY * newScale;
      scale = newScale;
      applyTransform();
    },
    { passive: false }
  );
}

// ---- n8n hover-payload (R31, sub-plan 11g) ----
// Flagged for whoever builds 10a's canvas-foundation rebuild: this hover behavior must be
// carried forward into the new node-tile rendering, not dropped, when renderN8nDiagram's
// internals get replaced by stage-zone layout + rounded-orthogonal routing.

function getOrCreateN8nTooltip() {
  let tooltip = document.getElementById("decomposeN8nTooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.id = "decomposeN8nTooltip";
    tooltip.className = "decompose-n8n-tooltip";
    document.body.appendChild(tooltip);
  }
  return tooltip;
}

function showN8nHoverPayload(evt, n8nNode) {
  const node = state.tree && state.tree.nodes[n8nNode.step_id];
  if (!node) return;
  const tooltip = getOrCreateN8nTooltip();

  const requiredLabels = (node.requires || []).map((id) => (state.tree.nodes[id] || {}).label || id);

  tooltip.innerHTML = "";
  const title = document.createElement("div");
  title.className = "decompose-n8n-tooltip-title";
  title.textContent = node.label;
  tooltip.appendChild(title);

  const rows = [
    ["consumes", node.consumes || "—"],
    ["produces", node.produces || "—"],
    ["requires", requiredLabels.length ? requiredLabels.join(", ") : "—"],
  ];
  for (const [label, value] of rows) {
    const row = document.createElement("div");
    row.className = "decompose-n8n-tooltip-row";
    const labelEl = document.createElement("span");
    labelEl.className = "decompose-n8n-tooltip-label";
    labelEl.textContent = label;
    const valueEl = document.createElement("span");
    valueEl.textContent = value;
    row.appendChild(labelEl);
    row.appendChild(valueEl);
    tooltip.appendChild(row);
  }

  if (node.rules && node.rules.length) {
    const rulesRow = document.createElement("div");
    rulesRow.className = "decompose-n8n-tooltip-row";
    const labelEl = document.createElement("span");
    labelEl.className = "decompose-n8n-tooltip-label";
    labelEl.textContent = "rules";
    const valueEl = document.createElement("span");
    valueEl.textContent = node.rules.join("; ");
    rulesRow.appendChild(labelEl);
    rulesRow.appendChild(valueEl);
    tooltip.appendChild(rulesRow);
  }

  if (node.variables && node.variables.length) {
    const varsLabel = document.createElement("div");
    varsLabel.className = "decompose-n8n-tooltip-label";
    varsLabel.textContent = "intermediate objects (variables)";
    tooltip.appendChild(varsLabel);
    for (const v of node.variables) {
      const varRow = document.createElement("div");
      varRow.className = "decompose-n8n-tooltip-row";
      varRow.textContent = v.default != null ? `${v.name} = ${v.default}` : v.name;
      tooltip.appendChild(varRow);
    }
  }

  tooltip.style.left = `${evt.clientX + 14}px`;
  tooltip.style.top = `${evt.clientY + 12}px`;
  tooltip.style.opacity = "1";
}

function hideN8nHoverPayload() {
  const tooltip = document.getElementById("decomposeN8nTooltip");
  if (tooltip) tooltip.style.opacity = "0";
}

function downloadWorkflowJson(workflow, domain) {
  // 10b-iii: any confirmed configuration is a real effect on the exported file, not
  // cosmetic -- merged in here, the one place the download actually gets built.
  const nodesWithConfig = workflow.nodes.map((n) => ({ ...n, parameters: n8nEffectiveParameters(n) }));
  const exportable = { name: workflow.name, nodes: nodesWithConfig, connections: workflow.connections };
  const blob = new Blob([JSON.stringify(exportable, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${domain}-workflow.json`;
  a.click();
  URL.revokeObjectURL(url);
}

async function selectMode(mode) {
  state = { ...state, mode };
  renderBoard();
  const cacheKey = mode === "python" ? "pythonRender" : "n8nRender";
  if (state[cacheKey]) return; // already fetched for this domain -- no re-fetch on re-toggle
  const res = await fetch(`/api/decompose/render/${mode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain: state.domain }),
  });
  if (!res.ok) {
    state = { ...state, error: `Failed to render ${mode} output.` };
    renderBoard();
    return;
  }
  state = { ...state, [cacheKey]: await res.json() };
  renderBoard();
}

async function selectDomain(domain) {
  clearTimeout(refineIdleTimer);
  state = {
    ...state, view: "canvas", domain, tree: null, error: null,
    mode: null, pythonRender: null, n8nRender: null, selectedNodeId: null, n8nNodeConfig: {},
    refineBarExpanded: false,
    pyBrowser: { level: 1, folderIdx: null, fileIdx: null, funcId: null, docId: null },
  };
  renderBoard();
  const res = await fetch(`/api/decompose/domains/${encodeURIComponent(domain)}/tree`);
  if (!res.ok) {
    state = { ...state, error: `Failed to load the tree for '${domain}'.` };
    renderBoard();
    return;
  }
  state = { ...state, tree: await res.json() };
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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function startDrafting(domain) {
  state = {
    ...state, view: "drafting", domain, draft: null, error: null, treeRevealed: false,
    draftRevealLines: [
      { text: `Domain resolved: ${domain}`, status: "done" },
      { text: "Decomposing into layers, sub-tasks, and atomic steps…", status: "pending" },
    ],
  };
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
    await revealDraftSummary(draft);
    state = { ...state, view: "reviewing_draft", draft };
  } finally {
    renderBoard();
  }
}

async function revealDraftSummary(draft) {
  // 10d -- real, computed-from-the-actual-tree lines only; never a fabricated live
  // per-attempt progress feed (see 10d's own plan file for why that would be dishonest
  // given how propose_tree's retry loop actually runs).
  const tree = draft.tree;
  const levelCount = (level) => Object.values(tree.nodes).filter((n) => n.level === level).length;
  const layerCount = tree.root_ids.length;
  const subTaskCount = levelCount("Sub-task");
  const atomicCount = levelCount("Atomic step");
  const violations = draft.validation.violations || [];

  function replaceLine(index, text, status) {
    const lines = [...state.draftRevealLines];
    lines[index] = { text, status };
    state = { ...state, draftRevealLines: lines };
    renderBoard();
  }
  function pushLine(text, status) {
    state = { ...state, draftRevealLines: [...state.draftRevealLines, { text, status }] };
    renderBoard();
  }

  replaceLine(1, "Layers, sub-tasks, and atomic steps decomposed", "done");
  await sleep(300);
  pushLine(`${layerCount} Layer${layerCount === 1 ? "" : "s"} instantiated`, "done");
  await sleep(300);
  pushLine(`${subTaskCount} Sub-task${subTaskCount === 1 ? "" : "s"} generated`, "done");
  await sleep(300);
  pushLine(`${atomicCount} Atomic step${atomicCount === 1 ? "" : "s"} generated`, "done");
  await sleep(300);
  pushLine("Grounding simulation complete", "done");
  await sleep(300);
  if (violations.length === 0) {
    pushLine("Atomicity validation passed", "done");
  } else {
    pushLine(`Atomicity validation: ${violations.length} issue${violations.length === 1 ? "" : "s"} found`, "failed");
  }
  await sleep(500);
}

function renderBuildStatusPanel(lines) {
  const panel = document.createElement("div");
  panel.className = "decompose-build-status";
  for (const line of lines) {
    const row = document.createElement("div");
    row.className = `decompose-bs-line ${line.status}`;
    const icon = document.createElement("span");
    icon.className = "decompose-bs-icon";
    icon.textContent = line.status === "done" ? "✓" : line.status === "failed" ? "✕" : "⏳";
    row.appendChild(icon);
    const text = document.createElement("span");
    text.textContent = line.text;
    row.appendChild(text);
    panel.appendChild(row);
  }
  return panel;
}

function renderDraftingView() {
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = `Drafting a decomposition for '${state.domain}'…`;
  decomposeBoard.appendChild(heading);
  decomposeBoard.appendChild(renderBuildStatusPanel(state.draftRevealLines));
  const note = document.createElement("div");
  note.className = "reasoning-empty-state";
  note.textContent = "Running the Decomposition Engine's full 4-stage build order for a brand-new domain -- this can take a little while.";
  decomposeBoard.appendChild(note);
}

async function streamRevealTreeNodes(diagramWrap) {
  // 10d -- Layer nodes fade in, then Sub-task nodes, then Atomic steps one at a time.
  // Purely a presentation choreography over the already-real, already-correct tree data --
  // not a claim about live backend progress (see 10d's own plan file).
  const svg = diagramWrap.querySelector("svg");
  if (!svg) return;
  const layerNodes = svg.querySelectorAll(".level-layer");
  const subNodes = svg.querySelectorAll(".level-sub-task");
  const atomicNodes = svg.querySelectorAll(".level-atomic-step");
  for (const n of [...layerNodes, ...subNodes, ...atomicNodes]) {
    n.style.transition = "opacity 0.25s";
    n.style.opacity = "0";
  }
  await sleep(50); // let the hidden state paint before animating
  for (const n of layerNodes) n.style.opacity = "1";
  await sleep(300);
  for (const n of subNodes) n.style.opacity = "1";
  await sleep(300);
  for (const n of atomicNodes) {
    n.style.opacity = "1";
    await sleep(90);
  }
}

function renderReviewingDraftView() {
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = `Review draft — ${state.domain}`;
  decomposeBoard.appendChild(heading);

  const diagramWrap = renderTreeDiagram(state.draft.tree, () => {});
  decomposeBoard.appendChild(diagramWrap);
  if (!state.treeRevealed) {
    // Direct mutation, deliberately not a `state = {...}` replace -- this is animation
    // bookkeeping only and must not trigger a renderBoard() that would wipe the DOM and
    // restart the reveal mid-flight.
    state.treeRevealed = true;
    streamRevealTreeNodes(diagramWrap);
  }

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
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && state.selectedNodeId) closeNodeDetail();
  });
  const idea = sessionStorage.getItem(LAUNCHPAD_IDEA_KEY);
  if (idea) {
    sessionStorage.removeItem(LAUNCHPAD_IDEA_KEY);
    document.getElementById("decomposeIntentInput").value = idea;
    submitIntent(idea);
  }
}

init();
