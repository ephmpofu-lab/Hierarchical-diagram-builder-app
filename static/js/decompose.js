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

let state = {
  view: "home", // "home" | "drafting" | "reviewing_draft" | "canvas"
  knownDomains: [],
  domain: null,
  lastIntentText: "",
  draft: null, // { domain, checklist, tree, validation } from POST .../draft
  tree: null, // the frozen DomainTaskTree, once loaded for the current canvas domain
  mode: null, // "python" | "n8n" | null, canvas-state only
  pythonRender: null, // cached List[RenderedCodeBlock] for the current domain
  n8nRender: null, // cached N8nWorkflow for the current domain
  selectedNodeId: null, // drives the slide-in detail panel, canvas-state only
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

function renderRefineBar() {
  const bar = document.createElement("div");
  bar.className = "decompose-refine-bar";
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
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitRefine(input.value);
    }
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
    state = {
      ...state, refining: false, tree: result.tree,
      pythonRender: null, n8nRender: null, mode: null, selectedNodeId: null,
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

function closeNodeDetail() {
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
      const snippet = JSON.stringify({ type: mapped.type, parameters: mapped.parameters }, null, 2);
      drawer.appendChild(renderDrawerSnippet("n8n node", snippet));
    }
  }

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

function renderOutputSection() {
  const section = document.createElement("div");
  section.className = "decompose-output-section";

  if (state.mode === "python") {
    if (!state.pythonRender) {
      section.textContent = "Rendering…";
      return section;
    }
    for (const block of state.pythonRender) {
      const pre = document.createElement("pre");
      pre.className = "decompose-code-block";
      const code = document.createElement("code");
      code.textContent = block.code;
      pre.appendChild(code);
      section.appendChild(pre);
    }
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

function renderN8nDiagram(workflow) {
  const boxWidth = 180;
  const boxHeight = 50;
  const padding = 40;
  const maxX = workflow.nodes.reduce((max, n) => Math.max(max, n.position[0]), 0);

  const totalWidth = maxX + boxWidth + padding * 2;
  const totalHeight = boxHeight + padding * 2;
  const svg = document.createElementNS(SVG_NS, "svg");
  // Explicit pixel size, not width="100%" -- a wide tree (RAG's 32 atomic steps) must
  // scroll horizontally in its own container, never be squashed illegibly small to fit.
  svg.setAttribute("width", totalWidth);
  svg.setAttribute("height", totalHeight);
  svg.setAttribute("viewBox", `0 0 ${totalWidth} ${totalHeight}`);
  svg.classList.add("decompose-n8n-diagram");

  const nodeByName = {};
  for (const node of workflow.nodes) nodeByName[node.name] = node;

  // Connections drawn first so node boxes sit on top of the lines.
  for (const [sourceName, outputs] of Object.entries(workflow.connections)) {
    const source = nodeByName[sourceName];
    const targets = (outputs.main && outputs.main[0]) || [];
    for (const conn of targets) {
      const target = nodeByName[conn.node];
      if (!source || !target) continue;
      const line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("x1", source.position[0] + boxWidth + padding);
      line.setAttribute("y1", padding + boxHeight / 2);
      line.setAttribute("x2", target.position[0] + padding);
      line.setAttribute("y2", padding + boxHeight / 2);
      line.setAttribute("class", "decompose-n8n-connection");
      svg.appendChild(line);
    }
  }

  for (const node of workflow.nodes) {
    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", node.position[0] + padding);
    rect.setAttribute("y", padding);
    rect.setAttribute("width", boxWidth);
    rect.setAttribute("height", boxHeight);
    rect.setAttribute("rx", "8");
    rect.setAttribute("class", "decompose-n8n-node-rect");
    svg.appendChild(rect);

    const text = document.createElementNS(SVG_NS, "text");
    text.setAttribute("x", node.position[0] + padding + boxWidth / 2);
    text.setAttribute("y", padding + boxHeight / 2 + 4);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("class", "decompose-n8n-node-text");
    text.textContent = node.name.length > 22 ? `${node.name.slice(0, 20)}…` : node.name;
    svg.appendChild(text);
  }
  return svg;
}

function downloadWorkflowJson(workflow, domain) {
  const exportable = { name: workflow.name, nodes: workflow.nodes, connections: workflow.connections };
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
  state = {
    ...state, view: "canvas", domain, tree: null, error: null,
    mode: null, pythonRender: null, n8nRender: null, selectedNodeId: null,
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
