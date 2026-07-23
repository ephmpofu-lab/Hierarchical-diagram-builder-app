const params = new URLSearchParams(window.location.search);
const projectId = params.get("project");

const CLASSIFICATIONS = [
  "AI Agent", "Workflow", "Database", "API", "UI", "Decision", "Configuration",
  "Storage", "Queue", "Security", "Validation", "Service", "Monitoring", "Infrastructure",
];
const CLASSIFICATION_COLORS = {
  "AI Agent": "#8b5cf6",
  Workflow: "#2563eb",
  Database: "#0891b2",
  API: "#4f46e5",
  UI: "#db2777",
  Decision: "#f59e0b",
  Configuration: "#64748b",
  Storage: "#c2410c",
  Queue: "#ca8a04",
  Security: "#dc2626",
  Validation: "#16a34a",
  Service: "#0ea5e9",
  Monitoring: "#ea580c",
  Infrastructure: "#475569",
};
const CLASSIFICATION_BADGES = {
  "AI Agent": "AI",
  Workflow: "WF",
  Database: "DB",
  API: "API",
  UI: "UI",
  Decision: "DEC",
  Configuration: "CFG",
  Storage: "STO",
  Queue: "Q",
  Security: "SEC",
  Validation: "VAL",
  Service: "SVC",
  Monitoring: "MON",
  Infrastructure: "INF",
};

const outlineTree = document.getElementById("outlineTree");
const projectNameEl = document.getElementById("projectName");
const breadcrumbEl = document.getElementById("breadcrumb");
const canvasSvg = document.getElementById("canvasSvg");
const inspectorContent = document.getElementById("inspectorContent");
const searchBox = document.getElementById("searchBox");
const searchWrap = document.querySelector(".search-wrap");
const searchResults = document.getElementById("searchResults");
const exportBtn = document.getElementById("exportBtn");
const exportMenu = document.getElementById("exportMenu");
const addRefModeBtn = document.getElementById("addRefModeBtn");
const refModeBanner = document.getElementById("refModeBanner");
const zoomInBtn = document.getElementById("zoomInBtn");
const zoomOutBtn = document.getElementById("zoomOutBtn");
const zoomLevelEl = document.getElementById("zoomLevel");
const fitViewBtn = document.getElementById("fitViewBtn");
const addGroupBtn = document.getElementById("addGroupBtn");
const showDepsBtn = document.getElementById("showDepsBtn");
const focusModeBtn = document.getElementById("focusModeBtn");
const fullArchModeBtn = document.getElementById("fullArchModeBtn");
const minimapSvg = document.getElementById("minimapSvg");
const healthToggleBtn = document.getElementById("healthToggleBtn");
const healthPanel = document.getElementById("healthPanel");
const healthCloseBtn = document.getElementById("healthCloseBtn");
const healthScoreEl = document.getElementById("healthScore");
const viewFullReportBtn = document.getElementById("viewFullReportBtn");
const validationSummaryEl = document.getElementById("validationSummary");
const runValidationBtn = document.getElementById("runValidationBtn");
const activityListEl = document.getElementById("activityList");
const importOutlineBtn = document.getElementById("importOutlineBtn");
const importModal = document.getElementById("importModal");
const importText = document.getElementById("importText");
const importCancelBtn = document.getElementById("importCancelBtn");
const importConfirmBtn = document.getElementById("importConfirmBtn");
const importXBtn = document.getElementById("importXBtn");

const SVG_NS = "http://www.w3.org/2000/svg";
const NODE_W = 150;
const NODE_H = 44;
const ZOOM_MIN = 0.4;
const ZOOM_MAX = 2.5;
const ZOOM_STEP = 0.15;

let project = null;
let rootId = null;
let focusedNodeId = null;
let editingNodeId = null;
let zoomScale = 1;
let refMode = false;
let pendingRefFrom = null;
let panOffsetX = 0;
let panOffsetY = 0;
let selectedEdgeKey = null; // "ref:<refId>" or "tree:<childId>"
let lastVisiblePositions = new Map();
let lastViewW = 800;
let lastViewH = 500;
let showDependencies = false;
let expandedGroupOverflow = false; // "show all" for progressive disclosure of many ungrouped children
let lastValidationReport = null;
let viewMode = "focus"; // "focus" | "full"

const ROW_GAP = 130;
const COL_GAP = 24;
const MAX_UNGROUPED_VISIBLE = 12;

if (!projectId) {
  projectNameEl.textContent = "No project specified";
} else {
  loadProject();
}

async function loadProject() {
  const res = await fetch(`/api/projects/${projectId}`);
  if (!res.ok) {
    projectNameEl.textContent = "Project not found";
    return;
  }
  project = await res.json();
  rootId = Object.values(project.nodes).find((n) => n.parent_id === null).id;
  projectNameEl.textContent = project.name;
  if (!focusedNodeId) focusedNodeId = rootId;
  render();
}

projectNameEl.addEventListener("click", async () => {
  if (!project) return;
  const name = prompt("Rename project:", project.name);
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed || trimmed === project.name) return;
  await fetch(`/api/projects/${projectId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: trimmed }),
  });
  loadProject();
});
projectNameEl.style.cursor = "pointer";
projectNameEl.title = "Click to rename project";

function render() {
  renderOutline();
  renderBreadcrumb();
  renderCanvas();
  renderMinimap();
  renderInspector();
  if (!healthPanel.hidden) refreshHealthPanel();
}

async function focusNode(nodeId) {
  focusedNodeId = nodeId;
  panOffsetX = 0;
  panOffsetY = 0;
  expandedGroupOverflow = false;
  zoomScale = 1;
  zoomLevelEl.textContent = "100%";
  await expandAncestors(nodeId);
  await loadProject();
  fitToView();
}

async function expandAncestors(nodeId) {
  if (!project || !project.nodes[nodeId]) return;
  let current = project.nodes[nodeId];
  const toExpand = [];
  while (current && current.parent_id) {
    const parent = project.nodes[current.parent_id];
    if (parent.collapsed) toExpand.push(parent.id);
    current = parent;
  }
  for (const id of toExpand) {
    await fetch(`/api/projects/${projectId}/nodes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collapsed: false }),
    });
  }
}

function renderOutline() {
  outlineTree.innerHTML = "";
  outlineTree.appendChild(renderNode(rootId));
}

function renderNode(nodeId) {
  const node = project.nodes[nodeId];
  const wrapper = document.createElement("div");

  const row = document.createElement("div");
  row.className = "outline-row" + (nodeId === focusedNodeId ? " focused" : "");
  row.dataset.id = nodeId;
  row.style.paddingLeft = `${8 + (node.level - 1) * 20}px`;

  const toggle = document.createElement("span");
  toggle.className = "toggle";
  if (node.children.length > 0) {
    toggle.textContent = node.collapsed ? "▸" : "▾";
  } else {
    toggle.textContent = "";
  }
  toggle.addEventListener("click", (e) => {
    e.stopPropagation();
    if (node.children.length > 0) toggleCollapse(nodeId, !node.collapsed);
  });

  const label = document.createElement("span");
  label.className = "label";
  label.textContent = node.is_group ? `▤ ${node.label}` : node.label;
  label.addEventListener("dblclick", (e) => {
    e.stopPropagation();
    startRename(nodeId, row, label);
  });

  const levelBadge = document.createElement("span");
  levelBadge.className = "level-badge";
  levelBadge.textContent = `L${node.level}`;

  const actions = document.createElement("span");
  actions.className = "row-actions";

  const addBtn = document.createElement("button");
  addBtn.className = "row-btn add-child";
  addBtn.textContent = "+";
  addBtn.title = "Add child";
  addBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    addChild(nodeId);
  });

  const delBtn = document.createElement("button");
  delBtn.className = "row-btn delete-node";
  delBtn.textContent = "×";
  delBtn.title = "Delete";
  delBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    deleteNodeFlow(nodeId);
  });

  actions.appendChild(addBtn);
  if (node.parent_id !== null) actions.appendChild(delBtn);

  row.appendChild(toggle);
  row.appendChild(label);
  row.appendChild(levelBadge);
  row.appendChild(actions);
  row.addEventListener("click", () => {
    focusNode(nodeId);
  });
  row.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    openContextMenu(nodeId, e.clientX, e.clientY);
  });

  wrapper.appendChild(row);

  if (node.children.length > 0 && !node.collapsed) {
    for (const childId of node.children) {
      wrapper.appendChild(renderNode(childId));
    }
  }

  return wrapper;
}

async function toggleCollapse(nodeId, collapsed) {
  await fetch(`/api/projects/${projectId}/nodes/${nodeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ collapsed }),
  });
  await loadProject();
}

function startRename(nodeId, row, labelSpan) {
  editingNodeId = nodeId;
  const node = project.nodes[nodeId];
  const input = document.createElement("input");
  input.className = "label-input";
  input.value = node.label;
  row.replaceChild(input, labelSpan);
  input.focus();
  input.select();

  const finish = async (commit) => {
    editingNodeId = null;
    if (commit) {
      const trimmed = input.value.trim();
      if (trimmed && trimmed !== node.label) {
        await fetch(`/api/projects/${projectId}/nodes/${nodeId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ label: trimmed }),
        });
      }
    }
    await loadProject();
  };

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      finish(true);
    } else if (e.key === "Escape") {
      e.preventDefault();
      finish(false);
    }
  });
  input.addEventListener("blur", () => finish(true));
}

async function addChild(parentId) {
  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: parentId, label: "New node" }),
  });
  const newNode = await res.json();
  if (project.nodes[parentId].collapsed) {
    await toggleCollapse(parentId, false);
  } else {
    await loadProject();
  }
  focusedNodeId = newNode.id;
  render();
  focusAndRenameRow(newNode.id);
}

async function addSiblingBelow(nodeId) {
  const node = project.nodes[nodeId];
  if (node.parent_id === null) {
    return addChild(nodeId);
  }
  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: node.parent_id, label: "New node", insert_after: nodeId }),
  });
  const newNode = await res.json();
  await loadProject();
  focusedNodeId = newNode.id;
  render();
  focusAndRenameRow(newNode.id);
}

function focusAndRenameRow(nodeId) {
  const row = outlineTree.querySelector(`.outline-row[data-id="${nodeId}"]`);
  if (!row) return;
  const labelSpan = row.querySelector(".label");
  startRename(nodeId, row, labelSpan);
}

async function deleteNodeFlow(nodeId) {
  const node = project.nodes[nodeId];
  if (node.parent_id === null) {
    alert("The root node cannot be deleted.");
    return;
  }
  if (node.children.length === 0) {
    const confirmed = confirm(`Delete "${node.label}"?`);
    if (!confirmed) return;
    await performDelete(nodeId, false);
    return;
  }

  const choice = await showChoiceModal(
    `"${node.label}" has ${node.children.length} direct child${node.children.length === 1 ? "" : "ren"}. What should happen to them?`,
    [
      { key: "promote", label: "Promote children up one level" },
      { key: "delete", label: "Delete children too", danger: true },
      { key: "cancel", label: "Cancel" },
    ]
  );
  if (choice === "promote") await performDelete(nodeId, true);
  if (choice === "delete") await performDelete(nodeId, false);
}

async function performDelete(nodeId, promoteChildren) {
  if (focusedNodeId === nodeId) focusedNodeId = project.nodes[nodeId].parent_id;
  await fetch(`/api/projects/${projectId}/nodes/${nodeId}?promote_children=${promoteChildren}`, {
    method: "DELETE",
  });
  await loadProject();
}

function showChoiceModal(message, choices) {
  return new Promise((resolve) => {
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";

    const modal = document.createElement("div");
    modal.className = "modal";

    const text = document.createElement("p");
    text.textContent = message;
    modal.appendChild(text);

    const actions = document.createElement("div");
    actions.className = "modal-actions";

    for (const choice of choices) {
      const btn = document.createElement("button");
      btn.className = "btn btn-small" + (choice.danger ? " btn-danger" : "");
      btn.textContent = choice.label;
      btn.addEventListener("click", () => {
        document.body.removeChild(backdrop);
        resolve(choice.key);
      });
      actions.appendChild(btn);
    }

    modal.appendChild(actions);
    backdrop.appendChild(modal);
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        document.body.removeChild(backdrop);
        resolve("cancel");
      }
    });
    document.body.appendChild(backdrop);
  });
}

document.addEventListener("keydown", async (e) => {
  if (e.key === "Escape" && refMode) {
    exitRefMode();
    return;
  }
  if (e.key === "Escape" && selectedEdgeKey) {
    selectedEdgeKey = null;
    renderCanvas();
    return;
  }
  if (e.key === "Escape" && !importModal.hidden) {
    closeImportModal();
    return;
  }
  if (e.key === "Escape" && !exportMenu.hidden) {
    exportMenu.hidden = true;
    return;
  }
  if (!focusedNodeId || editingNodeId) return;
  const activeTag = document.activeElement.tagName;
  if (activeTag === "INPUT" || activeTag === "TEXTAREA") return;

  if (e.key === "Tab") {
    e.preventDefault();
    const endpoint = e.shiftKey ? "outdent" : "indent";
    const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/${endpoint}`, {
      method: "POST",
    });
    if (res.ok) await loadProject();
  } else if (e.key === "Enter") {
    e.preventDefault();
    await addSiblingBelow(focusedNodeId);
  } else if (e.key === "Delete") {
    e.preventDefault();
    await deleteNodeFlow(focusedNodeId);
  }
});

// ---------- Breadcrumb ----------

function renderBreadcrumb() {
  breadcrumbEl.innerHTML = "";
  if (!project || !focusedNodeId) return;

  const chain = [];
  let current = project.nodes[focusedNodeId];
  while (current) {
    chain.unshift(current);
    current = current.parent_id ? project.nodes[current.parent_id] : null;
  }

  chain.forEach((node, i) => {
    if (i > 0) {
      const sep = document.createElement("span");
      sep.className = "sep";
      sep.textContent = ">";
      breadcrumbEl.appendChild(sep);
    }
    const crumb = document.createElement("span");
    const isCurrent = i === chain.length - 1;
    crumb.className = "crumb" + (isCurrent ? " current" : "");
    crumb.textContent = node.parent_id === null ? "Root" : node.label;
    if (!isCurrent) {
      crumb.addEventListener("click", () => {
        focusNode(node.id);
      });
    }
    breadcrumbEl.appendChild(crumb);
  });
}

// ---------- Canvas ----------

function curvePath(from, to) {
  const midY = (from.y + to.y) / 2;
  return `M ${from.x} ${from.y} C ${from.x} ${midY}, ${to.x} ${midY}, ${to.x} ${to.y}`;
}

// Places `siblings` in a row alongside the already-positioned `activeId` node (which stays
// put), fanning outward left/right of it, and marks each as faded context — visible, but
// dimmed, so ancestor context is never fully hidden even though it isn't the active branch.
function layoutSiblingRow(siblings, activeId, y, positions, fadedIds) {
  const activeX = positions.get(activeId).x;
  siblings.forEach((sib, i) => {
    const side = i % 2 === 0 ? 1 : -1;
    const rank = Math.floor(i / 2) + 1;
    positions.set(sib.id, { x: activeX + side * rank * (NODE_W + COL_GAP), y });
    fadedIds.add(sib.id);
  });
}

function computeCanvasLayout(viewW, viewH) {
  const focus = project.nodes[focusedNodeId];
  const parent = focus.parent_id ? project.nodes[focus.parent_id] : null;
  const grandparent = parent && parent.parent_id ? project.nodes[parent.parent_id] : null;
  const allChildren = focus.children.map((id) => project.nodes[id]);
  const visibleChildren =
    !expandedGroupOverflow && allChildren.length > MAX_UNGROUPED_VISIBLE
      ? allChildren.slice(0, MAX_UNGROUPED_VISIBLE)
      : allChildren;
  const hiddenCount = allChildren.length - visibleChildren.length;

  const positions = new Map();
  const fadedIds = new Set();
  const contextEdges = []; // {fromId, toId} for faded ancestor/sibling context, drawn dimmed

  positions.set(focus.id, { x: viewW / 2, y: viewH / 2 });
  if (parent) positions.set(parent.id, { x: viewW / 2, y: viewH / 2 - ROW_GAP });
  if (grandparent) positions.set(grandparent.id, { x: viewW / 2, y: viewH / 2 - 2 * ROW_GAP });

  // Never fully hide ancestor context: show the focused node's siblings, and the parent's
  // siblings, faded rather than omitted — only the direct root→focus path and focus's own
  // children render at full opacity.
  if (parent) {
    const focusSiblings = parent.children.filter((id) => id !== focus.id).map((id) => project.nodes[id]);
    layoutSiblingRow(focusSiblings, focus.id, viewH / 2, positions, fadedIds);
    for (const sib of focusSiblings) contextEdges.push({ fromId: parent.id, toId: sib.id });
  }
  if (grandparent) {
    const parentSiblings = grandparent.children.filter((id) => id !== parent.id).map((id) => project.nodes[id]);
    layoutSiblingRow(parentSiblings, parent.id, viewH / 2 - ROW_GAP, positions, fadedIds);
    for (const sib of parentSiblings) contextEdges.push({ fromId: grandparent.id, toId: sib.id });
  }

  const n = visibleChildren.length;
  const rowOffsetX = n > 0 ? -((n - 1) * (NODE_W + COL_GAP)) / 2 : 0;
  visibleChildren.forEach((child, i) => {
    positions.set(child.id, {
      x: viewW / 2 + rowOffsetX + i * (NODE_W + COL_GAP),
      y: viewH / 2 + ROW_GAP,
    });
  });

  let minX = viewW / 2 - NODE_W / 2;
  let maxX = viewW / 2 + NODE_W / 2;
  let minY = (grandparent ? viewH / 2 - 2 * ROW_GAP : parent ? viewH / 2 - ROW_GAP : viewH / 2) - NODE_H / 2;
  let maxY = viewH / 2 + NODE_H / 2;
  for (const pos of positions.values()) {
    minX = Math.min(minX, pos.x - NODE_W / 2);
    maxX = Math.max(maxX, pos.x + NODE_W / 2);
    minY = Math.min(minY, pos.y - NODE_H / 2);
    maxY = Math.max(maxY, pos.y + NODE_H / 2);
  }

  return {
    focus,
    parent,
    grandparent,
    visibleChildren,
    hiddenCount,
    positions,
    fadedIds,
    contextEdges,
    bounds: { minX, maxX, minY, maxY },
  };
}

function renderCanvas() {
  canvasSvg.innerHTML = "";
  canvasSvg.classList.toggle("ref-mode-active", refMode);
  canvasSvg.appendChild(buildRefArrowDefs());
  if (!project || !focusedNodeId) return;

  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;

  if (viewMode === "full") {
    renderFullArchitectureCanvas(viewW, viewH);
  } else {
    renderFocusCanvas(viewW, viewH);
  }
}

function renderFocusCanvas(viewW, viewH) {
  const { focus, parent, grandparent, visibleChildren, hiddenCount, positions, fadedIds, contextEdges } =
    computeCanvasLayout(viewW, viewH);
  const visibleIds = new Set(positions.keys());

  const viewport = document.createElementNS(SVG_NS, "g");
  viewport.setAttribute(
    "transform",
    `translate(${viewW / 2 + panOffsetX} ${viewH / 2 + panOffsetY}) scale(${zoomScale}) translate(${-viewW / 2} ${-viewH / 2})`
  );

  const edgesGroup = document.createElementNS(SVG_NS, "g");
  const refGroup = document.createElementNS(SVG_NS, "g");
  const nodesGroup = document.createElementNS(SVG_NS, "g");

  for (const contextEdge of contextEdges) {
    const fromPos = positions.get(contextEdge.fromId);
    const toPos = positions.get(contextEdge.toId);
    edgesGroup.appendChild(drawTreeEdge(fromPos, toPos, contextEdge.fromId, contextEdge.toId, true));
  }

  if (parent) {
    const parentPos = positions.get(parent.id);
    const focusPos = positions.get(focus.id);
    edgesGroup.appendChild(drawTreeEdge(parentPos, focusPos, parent.id, focus.id));
    if (selectedEdgeKey === edgeKey("tree", focus.id)) {
      edgesGroup.appendChild(drawTreeHandle(parentPos, focus.id, focusPos));
      edgesGroup.appendChild(drawTreeHandle(focusPos, focus.id, parentPos));
    }
  }
  if (grandparent && parent) {
    edgesGroup.appendChild(drawTreeEdge(positions.get(grandparent.id), positions.get(parent.id), grandparent.id, parent.id));
  }

  if (visibleChildren.length > 0) {
    edgesGroup.appendChild(drawTreeBranches(positions.get(focus.id), visibleChildren, positions));
  }

  if (showDependencies) {
    const tagCounters = new Map();
    for (const ref of project.references) {
      // Only draw references touching the focused node itself — otherwise a node with many
      // children each carrying their own unrelated reference links turns into a wall of lines.
      if (ref.from !== focus.id && ref.to !== focus.id) continue;
      const fromVisible = visibleIds.has(ref.from);
      const toVisible = visibleIds.has(ref.to);
      if (fromVisible && toVisible) {
        const fromPos = positions.get(ref.from);
        const toPos = positions.get(ref.to);
        refGroup.appendChild(drawRefEdge(fromPos, toPos, ref.from, ref.to, ref.id));
        if (selectedEdgeKey === edgeKey("ref", ref.id)) {
          refGroup.appendChild(drawRefHandle(fromPos, ref, "from"));
          refGroup.appendChild(drawRefHandle(toPos, ref, "to"));
        }
      } else if (fromVisible || toVisible) {
        const visibleId = fromVisible ? ref.from : ref.to;
        const otherId = fromVisible ? ref.to : ref.from;
        const otherNode = project.nodes[otherId];
        if (!otherNode) continue;
        const index = tagCounters.get(visibleId) || 0;
        tagCounters.set(visibleId, index + 1);
        const arrow = fromVisible ? "→" : "←";
        refGroup.appendChild(
          drawRefTag(positions.get(visibleId), `${arrow} ${otherNode.label}`, otherId, index, visibleId)
        );
      }
    }
  }

  if (grandparent) nodesGroup.appendChild(drawNode(grandparent, positions.get(grandparent.id)));
  for (const fadedId of fadedIds) {
    nodesGroup.appendChild(drawNode(project.nodes[fadedId], positions.get(fadedId), true));
  }
  if (parent) nodesGroup.appendChild(drawNode(parent, positions.get(parent.id)));
  nodesGroup.appendChild(drawNode(focus, positions.get(focus.id)));
  for (const child of visibleChildren) {
    nodesGroup.appendChild(drawNode(child, positions.get(child.id)));
  }
  if (hiddenCount > 0) {
    const lastPos = positions.get(visibleChildren[visibleChildren.length - 1].id);
    nodesGroup.appendChild(drawShowMoreAffordance(lastPos.x + NODE_W + COL_GAP, lastPos.y, hiddenCount));
  }

  viewport.appendChild(edgesGroup);
  viewport.appendChild(refGroup);
  viewport.appendChild(nodesGroup);
  canvasSvg.appendChild(viewport);

  lastVisiblePositions = positions;
  lastViewW = viewW;
  lastViewH = viewH;

  canvasSvg.onclick = (e) => {
    if (e.target === canvasSvg && selectedEdgeKey) {
      selectedEdgeKey = null;
      renderCanvas();
    }
  };
}

// Full Architecture mode: every non-collapsed node in the project, laid out one row per
// hierarchy level, nothing faded. This is the "show me everything at once" counterpart to
// Focus Mode's single-branch-plus-context view.
function computeFullArchitectureLayout(viewW, viewH) {
  const levelBuckets = new Map();
  const edges = [];
  const visited = new Set();
  const overflowByParent = new Map();

  function walk(nodeId) {
    if (visited.has(nodeId)) return;
    visited.add(nodeId);
    const node = project.nodes[nodeId];
    if (!levelBuckets.has(node.level)) levelBuckets.set(node.level, []);
    levelBuckets.get(node.level).push(node);
    if (node.collapsed) return;
    const children = node.children;
    const shown = children.length > MAX_UNGROUPED_VISIBLE ? children.slice(0, MAX_UNGROUPED_VISIBLE) : children;
    if (children.length > shown.length) overflowByParent.set(nodeId, children.length - shown.length);
    for (const childId of shown) {
      edges.push({ fromId: nodeId, toId: childId });
      walk(childId);
    }
  }
  walk(rootId);

  const positions = new Map();
  const levels = [...levelBuckets.keys()].sort((a, b) => a - b);
  levels.forEach((level, rowIndex) => {
    const nodesInRow = levelBuckets.get(level);
    const n = nodesInRow.length;
    const rowWidth = n * NODE_W + Math.max(0, n - 1) * COL_GAP;
    const startX = viewW / 2 - rowWidth / 2 + NODE_W / 2;
    nodesInRow.forEach((node, i) => {
      positions.set(node.id, { x: startX + i * (NODE_W + COL_GAP), y: 60 + rowIndex * ROW_GAP });
    });
  });

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const pos of positions.values()) {
    minX = Math.min(minX, pos.x - NODE_W / 2);
    maxX = Math.max(maxX, pos.x + NODE_W / 2);
    minY = Math.min(minY, pos.y - NODE_H / 2);
    maxY = Math.max(maxY, pos.y + NODE_H / 2);
  }
  if (!isFinite(minX)) {
    minX = 0;
    maxX = NODE_W;
    minY = 0;
    maxY = NODE_H;
  }

  return { positions, edges, overflowByParent, bounds: { minX, maxX, minY, maxY } };
}

function renderFullArchitectureCanvas(viewW, viewH) {
  const { positions, edges, overflowByParent, bounds } = computeFullArchitectureLayout(viewW, viewH);

  const viewport = document.createElementNS(SVG_NS, "g");
  viewport.setAttribute(
    "transform",
    `translate(${viewW / 2 + panOffsetX} ${viewH / 2 + panOffsetY}) scale(${zoomScale}) translate(${-viewW / 2} ${-viewH / 2})`
  );

  const edgesGroup = document.createElementNS(SVG_NS, "g");
  const nodesGroup = document.createElementNS(SVG_NS, "g");

  for (const edge of edges) {
    const fromPos = positions.get(edge.fromId);
    const toPos = positions.get(edge.toId);
    if (!fromPos || !toPos) continue;
    edgesGroup.appendChild(drawTreeEdge(fromPos, toPos, edge.fromId, edge.toId));
  }

  for (const [nodeId, pos] of positions.entries()) {
    nodesGroup.appendChild(drawNode(project.nodes[nodeId], pos));
    const overflow = overflowByParent.get(nodeId);
    if (overflow) {
      const label = document.createElementNS(SVG_NS, "text");
      label.setAttribute("class", "overflow-note");
      label.setAttribute("x", pos.x);
      label.setAttribute("y", pos.y + NODE_H / 2 + 14);
      label.textContent = `+${overflow} more not shown`;
      nodesGroup.appendChild(label);
    }
  }

  viewport.appendChild(edgesGroup);
  viewport.appendChild(nodesGroup);
  canvasSvg.appendChild(viewport);

  lastVisiblePositions = positions;
  lastViewW = viewW;
  lastViewH = viewH;

  canvasSvg.onclick = (e) => {
    if (e.target === canvasSvg && selectedEdgeKey) {
      selectedEdgeKey = null;
      renderCanvas();
    }
  };
}

function drawShowMoreAffordance(x, y, hiddenCount) {
  const group = document.createElementNS(SVG_NS, "g");
  group.setAttribute("class", "show-more-affordance");

  const box = document.createElementNS(SVG_NS, "rect");
  box.setAttribute("x", x - NODE_W / 2);
  box.setAttribute("y", y - NODE_H / 2);
  box.setAttribute("width", NODE_W);
  box.setAttribute("height", NODE_H);
  box.setAttribute("rx", 10);

  const label = document.createElementNS(SVG_NS, "text");
  label.setAttribute("x", x);
  label.setAttribute("y", y);
  label.textContent = `+${hiddenCount} more`;

  group.appendChild(box);
  group.appendChild(label);
  group.addEventListener("click", (e) => {
    e.stopPropagation();
    expandedGroupOverflow = true;
    renderCanvas();
    fitToView();
  });
  return group;
}

function edgeKey(kind, id) {
  return `${kind}:${id}`;
}

function drawTreeBranches(focusPos, children, positions) {
  const group = document.createElementNS(SVG_NS, "g");
  if (children.length === 0) return group;

  if (children.length === 1) {
    const childPos = positions.get(children[0].id);
    group.appendChild(drawTreeEdge(focusPos, childPos, null, children[0].id));
    const key = edgeKey("tree", children[0].id);
    if (selectedEdgeKey === key) {
      group.appendChild(drawTreeHandle(focusPos, children[0].id, childPos));
      group.appendChild(drawTreeHandle(childPos, children[0].id, focusPos));
    }
    return group;
  }

  // Classic org-chart connector: one trunk from the parent down to a shared horizontal
  // bus, then one short branch per child — much clearer than N lines fanning from a
  // single point once there are more than a couple of children. Children are always laid
  // out in a single deterministic row, so the bus always lines up cleanly.
  const childPositions = children.map((c) => positions.get(c.id));
  const busY = focusPos.y + (childPositions[0].y - focusPos.y) / 2;
  const xs = childPositions.map((p) => p.x);
  const minX = Math.min(...xs, focusPos.x);
  const maxX = Math.max(...xs, focusPos.x);

  const trunk = document.createElementNS(SVG_NS, "path");
  trunk.setAttribute("class", "edge");
  trunk.setAttribute("d", `M ${focusPos.x} ${focusPos.y} L ${focusPos.x} ${busY}`);
  group.appendChild(trunk);

  const bus = document.createElementNS(SVG_NS, "line");
  bus.setAttribute("class", "edge");
  bus.setAttribute("x1", minX);
  bus.setAttribute("y1", busY);
  bus.setAttribute("x2", maxX);
  bus.setAttribute("y2", busY);
  group.appendChild(bus);

  children.forEach((child, i) => {
    const childPos = childPositions[i];
    const key = edgeKey("tree", child.id);

    const branchGroup = document.createElementNS(SVG_NS, "g");
    const hit = document.createElementNS(SVG_NS, "path");
    hit.setAttribute("class", "edge-hit");
    hit.setAttribute("d", `M ${childPos.x} ${busY} L ${childPos.x} ${childPos.y}`);
    const branch = document.createElementNS(SVG_NS, "path");
    branch.setAttribute("class", "edge" + (selectedEdgeKey === key ? " selected" : ""));
    branch.setAttribute("d", `M ${childPos.x} ${busY} L ${childPos.x} ${childPos.y}`);
    branchGroup.dataset.toId = child.id;
    branchGroup.dataset.x1 = childPos.x;
    branchGroup.dataset.y1 = busY;
    branchGroup.dataset.x2 = childPos.x;
    branchGroup.dataset.y2 = childPos.y;
    branchGroup.appendChild(hit);
    branchGroup.appendChild(branch);
    branchGroup.addEventListener("click", (e) => {
      e.stopPropagation();
      selectedEdgeKey = selectedEdgeKey === key ? null : key;
      renderCanvas();
    });
    group.appendChild(branchGroup);

    if (selectedEdgeKey === key) {
      group.appendChild(drawTreeHandle(childPos, child.id, { x: childPos.x, y: busY }));
    }
  });

  return group;
}

function drawTreeEdge(from, to, fromId, toId, faded = false) {
  const group = document.createElementNS(SVG_NS, "g");
  const key = toId ? edgeKey("tree", toId) : null;

  const hit = document.createElementNS(SVG_NS, "path");
  hit.setAttribute("class", "edge-hit");
  hit.setAttribute("d", curvePath(from, to));

  const line = document.createElementNS(SVG_NS, "path");
  line.setAttribute(
    "class",
    "edge" + (faded ? " faded-edge" : "") + (key && selectedEdgeKey === key ? " selected" : "")
  );
  line.setAttribute("d", curvePath(from, to));
  if (fromId) group.dataset.fromId = fromId;
  if (toId) group.dataset.toId = toId;
  group.dataset.x1 = from.x;
  group.dataset.y1 = from.y;
  group.dataset.x2 = to.x;
  group.dataset.y2 = to.y;

  group.appendChild(hit);
  group.appendChild(line);
  if (key) {
    group.addEventListener("click", (e) => {
      e.stopPropagation();
      selectedEdgeKey = selectedEdgeKey === key ? null : key;
      renderCanvas();
    });
  }
  return group;
}

function drawTreeHandle(pos, childId, fixedPos) {
  const circle = document.createElementNS(SVG_NS, "circle");
  circle.setAttribute("class", "ref-handle");
  circle.setAttribute("cx", pos.x);
  circle.setAttribute("cy", pos.y);
  circle.setAttribute("r", 6);
  circle.addEventListener("mousedown", (e) => {
    startEdgeEndpointDrag(e, fixedPos, childId, async (targetId) => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${childId}/reparent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_parent_id: targetId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Couldn't move this node there.");
        renderCanvas();
        return;
      }
      selectedEdgeKey = null;
      await focusNode(childId);
    });
  });
  return circle;
}

function buildRefArrowDefs() {
  const defs = document.createElementNS(SVG_NS, "defs");
  const marker = document.createElementNS(SVG_NS, "marker");
  marker.setAttribute("id", "refArrow");
  marker.setAttribute("viewBox", "0 0 10 10");
  marker.setAttribute("refX", "8");
  marker.setAttribute("refY", "5");
  marker.setAttribute("markerWidth", "6");
  marker.setAttribute("markerHeight", "6");
  marker.setAttribute("orient", "auto-start-reverse");
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
  path.setAttribute("class", "ref-arrow-fill");
  marker.appendChild(path);
  defs.appendChild(marker);
  return defs;
}

function drawRefEdge(from, to, fromId, toId, refId) {
  const group = document.createElementNS(SVG_NS, "g");
  const key = edgeKey("ref", refId);

  const hitPath = document.createElementNS(SVG_NS, "path");
  hitPath.setAttribute("class", "edge-hit");
  hitPath.setAttribute("d", curvePath(from, to));

  const line = document.createElementNS(SVG_NS, "path");
  line.setAttribute("class", "ref-edge" + (selectedEdgeKey === key ? " selected" : ""));
  line.setAttribute("d", curvePath(from, to));
  line.setAttribute("marker-end", "url(#refArrow)");
  group.dataset.fromId = fromId;
  group.dataset.toId = toId;
  group.dataset.x1 = from.x;
  group.dataset.y1 = from.y;
  group.dataset.x2 = to.x;
  group.dataset.y2 = to.y;

  group.appendChild(hitPath);
  group.appendChild(line);
  group.addEventListener("click", (e) => {
    e.stopPropagation();
    selectedEdgeKey = selectedEdgeKey === key ? null : key;
    renderCanvas();
  });

  return group;
}

function drawRefHandle(pos, ref, endpoint) {
  const circle = document.createElementNS(SVG_NS, "circle");
  circle.setAttribute("class", "ref-handle");
  circle.setAttribute("cx", pos.x);
  circle.setAttribute("cy", pos.y);
  circle.setAttribute("r", 6);
  circle.addEventListener("mousedown", (e) => {
    const fixedEndId = endpoint === "from" ? ref.to : ref.from;
    const fixedPos = lastVisiblePositions.get(fixedEndId);
    if (!fixedPos) return;
    startEdgeEndpointDrag(e, fixedPos, fixedEndId, async (targetId) => {
      const payload = endpoint === "from" ? { from: targetId } : { to: targetId };
      await fetch(`/api/projects/${projectId}/references/${ref.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      selectedEdgeKey = edgeKey("ref", ref.id);
      await loadProject();
    });
  });
  return circle;
}

function startEdgeEndpointDrag(e, fixedPos, excludeId, onDrop) {
  e.preventDefault();
  e.stopPropagation();
  const rect = canvasSvg.getBoundingClientRect();

  const tempLine = document.createElementNS(SVG_NS, "line");
  tempLine.setAttribute("class", "ref-edge");
  tempLine.setAttribute("x1", fixedPos.x);
  tempLine.setAttribute("y1", fixedPos.y);
  tempLine.setAttribute("x2", fixedPos.x);
  tempLine.setAttribute("y2", fixedPos.y);
  const viewportEl = canvasSvg.querySelector(":scope > g");
  if (viewportEl) viewportEl.appendChild(tempLine);

  const toPretransform = (clientX, clientY) => ({
    x: lastViewW / 2 + (clientX - rect.left - lastViewW / 2) / zoomScale,
    y: lastViewH / 2 + (clientY - rect.top - lastViewH / 2) / zoomScale,
  });

  const onMove = (moveEvent) => {
    const p = toPretransform(moveEvent.clientX, moveEvent.clientY);
    tempLine.setAttribute("x2", p.x);
    tempLine.setAttribute("y2", p.y);
  };

  const onUp = async (upEvent) => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    tempLine.remove();
    const p = toPretransform(upEvent.clientX, upEvent.clientY);
    let targetId = null;
    for (const [nodeId, nodePos] of lastVisiblePositions.entries()) {
      if (nodeId === excludeId) continue;
      if (Math.abs(p.x - nodePos.x) <= NODE_W / 2 && Math.abs(p.y - nodePos.y) <= NODE_H / 2) {
        targetId = nodeId;
        break;
      }
    }
    if (targetId) {
      await onDrop(targetId);
    } else {
      renderCanvas();
    }
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

function drawRefTag(nodePos, text, targetId, index, anchorId) {
  const group = document.createElementNS(SVG_NS, "g");
  group.setAttribute("class", "ref-tag");
  group.dataset.anchorId = anchorId;
  group.dataset.anchorX = nodePos.x;
  group.dataset.anchorY = nodePos.y;
  const tagW = Math.min(140, 16 + text.length * 6.2);
  const tagX = nodePos.x + NODE_W / 2 + 10;
  const tagY = nodePos.y - NODE_H / 2 + index * 24;

  const rect = document.createElementNS(SVG_NS, "rect");
  rect.setAttribute("x", tagX);
  rect.setAttribute("y", tagY);
  rect.setAttribute("width", tagW);
  rect.setAttribute("height", 20);
  rect.setAttribute("rx", 5);

  const label = document.createElementNS(SVG_NS, "text");
  label.setAttribute("x", tagX + tagW / 2);
  label.setAttribute("y", tagY + 10);
  const maxChars = 16;
  label.textContent = text.length > maxChars ? text.slice(0, maxChars - 1) + "…" : text;

  group.appendChild(rect);
  group.appendChild(label);
  group.addEventListener("click", (e) => {
    e.stopPropagation();
    focusNode(targetId);
  });

  return group;
}

function drawNode(node, pos, faded = false) {
  const group = document.createElementNS(SVG_NS, "g");
  const classes = ["node-group"];
  if (node.id === focusedNodeId) classes.push("focused");
  if (node.id === pendingRefFrom) classes.push("ref-pending");
  if (node.is_group) classes.push("is-group");
  if (faded) classes.push("faded-node");
  group.setAttribute("class", classes.join(" "));
  group.dataset.id = node.id;

  const box = document.createElementNS(SVG_NS, "rect");
  box.setAttribute("class", "node-box");
  box.setAttribute("x", pos.x - NODE_W / 2);
  box.setAttribute("y", pos.y - NODE_H / 2);
  box.setAttribute("width", NODE_W);
  box.setAttribute("height", NODE_H);
  box.setAttribute("rx", node.is_group ? 6 : 10);

  const accentColor = node.custom_color || CLASSIFICATION_COLORS[node.classification];
  if (!node.is_group && accentColor) {
    box.style.stroke = accentColor;
    box.style.strokeWidth = "2";
  }

  const label = document.createElementNS(SVG_NS, "text");
  label.setAttribute("class", "node-label");
  label.setAttribute("x", pos.x);
  label.setAttribute("y", pos.y);
  const maxChars = 20;
  const displayText = node.is_group ? `▤ ${node.label} (${node.children.length})` : node.label;
  label.textContent = displayText.length > maxChars ? displayText.slice(0, maxChars - 1) + "…" : displayText;

  group.appendChild(box);
  group.appendChild(label);

  if (!node.is_group && node.classification) {
    const badgeText = CLASSIFICATION_BADGES[node.classification] || node.classification.slice(0, 3).toUpperCase();
    const badgeW = 10 + badgeText.length * 6;
    const badge = document.createElementNS(SVG_NS, "g");
    const badgeRect = document.createElementNS(SVG_NS, "rect");
    badgeRect.setAttribute("x", pos.x - NODE_W / 2 + 4);
    badgeRect.setAttribute("y", pos.y - NODE_H / 2 + 4);
    badgeRect.setAttribute("width", badgeW);
    badgeRect.setAttribute("height", 14);
    badgeRect.setAttribute("rx", 3);
    badgeRect.setAttribute("fill", accentColor);
    const badgeLabel = document.createElementNS(SVG_NS, "text");
    badgeLabel.setAttribute("class", "node-badge-text");
    badgeLabel.setAttribute("x", pos.x - NODE_W / 2 + 4 + badgeW / 2);
    badgeLabel.setAttribute("y", pos.y - NODE_H / 2 + 11);
    badgeLabel.textContent = badgeText;
    badge.appendChild(badgeRect);
    badge.appendChild(badgeLabel);
    group.appendChild(badge);
  }

  if (!node.is_group && (node.priority === "High" || node.priority === "Critical")) {
    const priBadge = document.createElementNS(SVG_NS, "circle");
    priBadge.setAttribute("class", "priority-dot");
    priBadge.setAttribute("cx", pos.x + NODE_W / 2 - 6);
    priBadge.setAttribute("cy", pos.y + NODE_H / 2 - 6);
    priBadge.setAttribute("r", 4);
    group.appendChild(priBadge);
  }

  if (!node.is_group && computeWarnings(node).length > 0) {
    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("class", "warning-dot");
    dot.setAttribute("cx", pos.x + NODE_W / 2 - 6);
    dot.setAttribute("cy", pos.y - NODE_H / 2 + 6);
    dot.setAttribute("r", 4);
    group.appendChild(dot);
  }

  group.addEventListener("click", (e) => {
    if (refMode) {
      e.preventDefault();
      e.stopPropagation();
      handleRefModeClick(node.id);
    } else {
      focusNode(node.id);
    }
  });

  group.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    e.stopPropagation();
    openContextMenu(node.id, e.clientX, e.clientY);
  });

  return group;
}

// ---------- Context menu ----------

let clipboardSubtree = null;
let openContextMenuEl = null;

function closeContextMenu() {
  if (openContextMenuEl) {
    openContextMenuEl.remove();
    openContextMenuEl = null;
  }
}

document.addEventListener("click", () => closeContextMenu());
document.addEventListener("contextmenu", (e) => {
  if (openContextMenuEl && !openContextMenuEl.contains(e.target)) closeContextMenu();
});
window.addEventListener("blur", () => closeContextMenu());
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeContextMenu();
});

async function patchNodeById(nodeId, payload) {
  await fetch(`/api/projects/${projectId}/nodes/${nodeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadProject();
}

function contextMenuItem(text, onClick, opts = {}) {
  const item = document.createElement("button");
  item.className = "context-menu-item" + (opts.danger ? " danger" : "");
  item.textContent = text;
  item.disabled = !!opts.disabled;
  item.addEventListener("click", (e) => {
    e.stopPropagation();
    closeContextMenu();
    onClick();
  });
  return item;
}

function contextMenuSeparator() {
  const sep = document.createElement("div");
  sep.className = "context-menu-separator";
  return sep;
}

function contextMenuSubmenu(text, options, onPick) {
  const wrap = document.createElement("div");
  wrap.className = "context-menu-item context-menu-has-submenu";
  const label = document.createElement("span");
  label.textContent = text;
  const arrow = document.createElement("span");
  arrow.className = "context-menu-arrow";
  arrow.textContent = "▸";
  wrap.appendChild(label);
  wrap.appendChild(arrow);

  const submenu = document.createElement("div");
  submenu.className = "context-menu context-submenu";
  for (const opt of options) {
    submenu.appendChild(
      contextMenuItem(opt, () => onPick(opt))
    );
  }
  wrap.appendChild(submenu);
  return wrap;
}

function openContextMenu(nodeId, clientX, clientY) {
  closeContextMenu();
  const node = project.nodes[nodeId];
  const isRoot = node.parent_id === null;
  const CLEAR = "— Clear —";

  const menu = document.createElement("div");
  menu.className = "context-menu";

  menu.appendChild(contextMenuItem("+ Add Child", () => addChild(nodeId)));
  menu.appendChild(contextMenuItem("+ Add Sibling", () => addSiblingBelow(nodeId), { disabled: isRoot }));
  menu.appendChild(
    contextMenuItem("↑ Add Parent Above", async () => {
      const label = prompt("New parent label:", "New parent");
      if (!label || !label.trim()) return;
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/add-parent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: label.trim() }),
      });
      const newNode = await res.json();
      await loadProject();
      focusNode(newNode.id);
    }, { disabled: isRoot })
  );
  menu.appendChild(
    contextMenuItem("⧉ Duplicate", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/duplicate`, { method: "POST" });
      const newNode = await res.json();
      await loadProject();
      focusNode(newNode.id);
    }, { disabled: isRoot })
  );
  menu.appendChild(
    contextMenuItem("✎ Rename", () => {
      const label = prompt("Rename node:", node.label);
      if (label && label.trim()) patchNodeById(nodeId, { label: label.trim() });
    })
  );

  menu.appendChild(contextMenuSeparator());

  menu.appendChild(
    contextMenuSubmenu("◆ Set Classification", [CLEAR, ...CLASSIFICATIONS], (opt) => {
      patchNodeById(nodeId, { classification: opt === CLEAR ? "" : opt });
    })
  );
  menu.appendChild(
    contextMenuItem("🎨 Change Color", () => {
      const colorInput = document.createElement("input");
      colorInput.type = "color";
      colorInput.value = node.custom_color || CLASSIFICATION_COLORS[node.classification] || "#64748b";
      colorInput.style.position = "fixed";
      colorInput.style.left = "-9999px";
      document.body.appendChild(colorInput);
      colorInput.addEventListener("change", () => {
        patchNodeById(nodeId, { custom_color: colorInput.value });
        colorInput.remove();
      });
      colorInput.click();
    })
  );
  menu.appendChild(
    contextMenuItem("Change Node Type", () => {
      const value = prompt("Node type:", node.node_type || "");
      if (value !== null) patchNodeById(nodeId, { node_type: value.trim() });
    })
  );
  menu.appendChild(
    contextMenuSubmenu("● Set Status", [CLEAR, "Planned", "In Development", "Done", "Blocked", "Deprecated"], (opt) => {
      patchNodeById(nodeId, { status: opt === CLEAR ? "" : opt });
    })
  );
  menu.appendChild(
    contextMenuSubmenu("● Set Priority", [CLEAR, "Low", "Medium", "High", "Critical"], (opt) => {
      patchNodeById(nodeId, { priority: opt === CLEAR ? "" : opt });
    })
  );
  menu.appendChild(
    contextMenuSubmenu("● Set Risk Level", [CLEAR, "Low", "Medium", "High", "Critical"], (opt) => {
      patchNodeById(nodeId, { risk_level: opt === CLEAR ? "" : opt });
    })
  );
  menu.appendChild(
    contextMenuItem("+ Add Tag", () => {
      const tag = prompt("Tag to add:");
      if (tag && tag.trim() && !node.tags.includes(tag.trim())) {
        patchNodeById(nodeId, { tags: [...node.tags, tag.trim()] });
      }
    })
  );
  menu.appendChild(
    contextMenuItem("Assign Owner", () => {
      const owner = prompt("Owner:", node.owner || "");
      if (owner !== null) patchNodeById(nodeId, { owner: owner.trim() });
    })
  );
  menu.appendChild(
    contextMenuItem("Add / Edit Notes", () => {
      focusedNodeId = nodeId;
      inspectorActiveTab = "inspector";
      render();
      const textarea = inspectorContent.querySelector("textarea");
      if (textarea) textarea.focus();
    })
  );

  menu.appendChild(contextMenuSeparator());

  menu.appendChild(
    contextMenuItem("⇢ Add Reference Link", () => {
      refMode = true;
      pendingRefFrom = nodeId;
      addRefModeBtn.classList.add("active");
      refModeBanner.hidden = false;
      renderCanvas();
    })
  );
  menu.appendChild(
    contextMenuItem(node.collapsed ? "▸ Expand Branch" : "▾ Collapse Branch", () => toggleCollapse(nodeId, !node.collapsed), {
      disabled: node.children.length === 0,
    })
  );
  menu.appendChild(
    contextMenuItem("Copy Subtree", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/subtree`);
      clipboardSubtree = await res.json();
    })
  );
  menu.appendChild(
    contextMenuItem("Paste Subtree Here", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/paste-subtree`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ root: clipboardSubtree }),
      });
      const newNode = await res.json();
      await loadProject();
      focusNode(newNode.id);
    }, { disabled: !clipboardSubtree })
  );
  menu.appendChild(
    contextMenuItem("⇩ Export Subtree", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/subtree`);
      const subtree = await res.json();
      downloadBlob(JSON.stringify(subtree, null, 2), `${safeFilename(node.label)}_subtree.json`, "application/json");
    })
  );

  menu.appendChild(contextMenuSeparator());

  menu.appendChild(
    contextMenuItem("🗑 Delete", () => deleteNodeFlow(nodeId), { disabled: isRoot, danger: true })
  );

  menu.style.left = `${clientX}px`;
  menu.style.top = `${clientY}px`;
  document.body.appendChild(menu);
  openContextMenuEl = menu;

  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) menu.style.left = `${Math.max(4, window.innerWidth - rect.width - 4)}px`;
  if (rect.bottom > window.innerHeight) menu.style.top = `${Math.max(4, window.innerHeight - rect.height - 4)}px`;
}

window.addEventListener("resize", () => {
  if (project) renderCanvas();
});

// ---------- Reference mode ----------

addRefModeBtn.addEventListener("click", () => {
  if (refMode) {
    exitRefMode();
  } else {
    refMode = true;
    pendingRefFrom = null;
    addRefModeBtn.classList.add("active");
    refModeBanner.hidden = false;
    renderCanvas();
  }
});

function exitRefMode() {
  refMode = false;
  pendingRefFrom = null;
  addRefModeBtn.classList.remove("active");
  refModeBanner.hidden = true;
  renderCanvas();
}

async function handleRefModeClick(nodeId) {
  if (!pendingRefFrom) {
    pendingRefFrom = nodeId;
    renderCanvas();
    return;
  }
  if (pendingRefFrom === nodeId) {
    exitRefMode();
    return;
  }
  const fromId = pendingRefFrom;
  const label = prompt("Optional label for this reference link:", "");
  if (label === null) {
    exitRefMode();
    return;
  }
  await fetch(`/api/projects/${projectId}/references`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from: fromId, to: nodeId, label: label.trim() || null }),
  });
  exitRefMode();
  await loadProject();
}

// ---------- Zoom ----------

function setZoom(scale) {
  zoomScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, scale));
  zoomLevelEl.textContent = `${Math.round(zoomScale * 100)}%`;
  renderCanvas();
}

zoomInBtn.addEventListener("click", () => setZoom(zoomScale + ZOOM_STEP));
zoomOutBtn.addEventListener("click", () => setZoom(zoomScale - ZOOM_STEP));

canvasSvg.addEventListener(
  "wheel",
  (e) => {
    if (!project || !focusedNodeId) return;
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) {
      setZoom(zoomScale + (e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP));
      return;
    }
    panOffsetX -= e.deltaX;
    panOffsetY -= e.deltaY;
    renderCanvas();
  },
  { passive: false }
);

function fitToView() {
  if (!project || !focusedNodeId) return;
  panOffsetX = 0;
  panOffsetY = 0;
  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;
  const { bounds } = viewMode === "full" ? computeFullArchitectureLayout(viewW, viewH) : computeCanvasLayout(viewW, viewH);
  const boxW = Math.max(bounds.maxX - bounds.minX, 1);
  const boxH = Math.max(bounds.maxY - bounds.minY, 1);
  const padding = 60;

  const scale = Math.min((viewW - padding * 2) / boxW, (viewH - padding * 2) / boxH, ZOOM_MAX);
  zoomScale = Math.max(0.1, scale);
  zoomLevelEl.textContent = `${Math.round(zoomScale * 100)}%`;
  renderCanvas();
}

fitViewBtn.addEventListener("click", fitToView);

function setViewMode(mode) {
  if (viewMode === mode) return;
  viewMode = mode;
  focusModeBtn.classList.toggle("active", mode === "focus");
  fullArchModeBtn.classList.toggle("active", mode === "full");
  fitToView();
}
focusModeBtn.addEventListener("click", () => setViewMode("focus"));
fullArchModeBtn.addEventListener("click", () => setViewMode("full"));

addGroupBtn.addEventListener("click", async () => {
  if (!focusedNodeId) return;
  const name = prompt("Name for this group (e.g. Configuration, Scanning, Validation):");
  if (!name || !name.trim()) return;
  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: focusedNodeId, label: name.trim(), is_group: true }),
  });
  const newNode = await res.json();
  await focusNode(newNode.id);
});

showDepsBtn.addEventListener("click", () => {
  showDependencies = !showDependencies;
  showDepsBtn.classList.toggle("active", showDependencies);
  renderCanvas();
});

// ---------- Minimap ----------

function renderMinimap() {
  minimapSvg.innerHTML = "";
  if (!project || !focusedNodeId) return;

  // Overview by hierarchy level — one horizontal band per level, real (non-group) nodes
  // only, since groups are a display-time organizational device rather than a real layer.
  const byLevel = new Map();
  for (const node of Object.values(project.nodes)) {
    if (node.is_group) continue;
    if (!byLevel.has(node.level)) byLevel.set(node.level, []);
    byLevel.get(node.level).push(node);
  }
  const levels = [...byLevel.keys()].sort((a, b) => a - b);
  if (levels.length === 0) return;

  const mapW = 160;
  const mapH = 100;
  const pad = 8;
  const rowH = (mapH - pad * 2) / levels.length;
  const focusLevel = project.nodes[focusedNodeId].level;

  levels.forEach((level, rowIdx) => {
    const nodesAtLevel = byLevel.get(level);
    const y = pad + rowIdx * rowH + rowH / 2;
    const colW = (mapW - pad * 2) / nodesAtLevel.length;
    nodesAtLevel.forEach((node, colIdx) => {
      const x = pad + colIdx * colW + colW / 2;
      const dot = document.createElementNS(SVG_NS, "circle");
      const classes = ["mini-node"];
      if (node.id === focusedNodeId) classes.push("focused");
      else if (level === focusLevel) classes.push("same-level");
      dot.setAttribute("class", classes.join(" "));
      dot.setAttribute("cx", x);
      dot.setAttribute("cy", y);
      dot.setAttribute("r", node.id === focusedNodeId ? 3 : 2);
      dot.addEventListener("click", (e) => {
        e.stopPropagation();
        focusNode(node.id);
      });
      minimapSvg.appendChild(dot);
    });
  });
}

// ---------- Health / validation / activity ----------

healthToggleBtn.addEventListener("click", () => {
  healthPanel.hidden = !healthPanel.hidden;
  if (!healthPanel.hidden) refreshHealthPanel();
});
healthCloseBtn.addEventListener("click", () => {
  healthPanel.hidden = true;
});
runValidationBtn.addEventListener("click", refreshHealthPanel);
viewFullReportBtn.addEventListener("click", async () => {
  if (!lastValidationReport) await refreshHealthPanel();
  const categoryLabels = [
    "Duplicate labels",
    "Circular references",
    "Large modules (>10 children)",
    "Single-child nodes",
    "Missing notes",
    "Missing owners",
    "Orphaned nodes",
    "Broken references",
  ];
  for (const label of categoryLabels) expandedValidationRows.add(label);
  renderValidationSummary(lastValidationReport);
});

async function refreshHealthPanel() {
  if (!project) return;
  const res = await fetch(`/api/projects/${projectId}/validation`);
  if (!res.ok) return;
  const report = await res.json();
  lastValidationReport = report;
  renderHealthScore(report);
  renderValidationSummary(report);
  renderActivityLog();
  if (inspectorActiveTab === "validation") renderInspector();
}

function renderHealthScore(report) {
  const ratingClass = "rating-" + report.rating.toLowerCase().replace(/\s+/g, "-");
  healthScoreEl.className = "health-score " + ratingClass;
  healthScoreEl.innerHTML = "";

  const size = 92;
  const stroke = 9;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - report.score / 100);

  const gaugeWrap = document.createElement("div");
  gaugeWrap.className = "health-gauge-wrap";

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("class", "health-gauge");

  const track = document.createElementNS(SVG_NS, "circle");
  track.setAttribute("cx", size / 2);
  track.setAttribute("cy", size / 2);
  track.setAttribute("r", radius);
  track.setAttribute("class", "gauge-track");
  track.setAttribute("stroke-width", stroke);

  const fill = document.createElementNS(SVG_NS, "circle");
  fill.setAttribute("cx", size / 2);
  fill.setAttribute("cy", size / 2);
  fill.setAttribute("r", radius);
  fill.setAttribute("class", "gauge-fill");
  fill.setAttribute("stroke-width", stroke);
  fill.setAttribute("stroke-dasharray", circumference);
  fill.setAttribute("stroke-dashoffset", offset);
  fill.setAttribute("transform", `rotate(-90 ${size / 2} ${size / 2})`);

  svg.appendChild(track);
  svg.appendChild(fill);

  const scoreText = document.createElement("div");
  scoreText.className = "score-number";
  scoreText.textContent = `${report.score}`;

  gaugeWrap.appendChild(svg);
  gaugeWrap.appendChild(scoreText);

  const ratingEl = document.createElement("div");
  ratingEl.className = "score-rating";
  ratingEl.textContent = report.rating;

  healthScoreEl.appendChild(gaugeWrap);
  healthScoreEl.appendChild(ratingEl);
}

let expandedValidationRows = new Set();

function validationIssueRow(label, issues) {
  const row = document.createElement("div");
  row.className = "validation-row" + (issues.length > 0 ? " flagged clickable" : "");
  const l = document.createElement("span");
  l.textContent = label;
  const v = document.createElement("strong");
  v.textContent = issues.length;
  row.appendChild(l);
  row.appendChild(v);
  if (issues.length > 0) {
    row.title = "Click to see and jump to affected nodes";
    row.addEventListener("click", () => {
      if (expandedValidationRows.has(label)) expandedValidationRows.delete(label);
      else expandedValidationRows.add(label);
      renderValidationSummary(lastValidationReport);
    });
  }
  validationSummaryEl.appendChild(row);

  if (issues.length > 0 && expandedValidationRows.has(label)) {
    const list = document.createElement("div");
    list.className = "validation-issue-list";
    for (const issue of issues) {
      const item = document.createElement("button");
      item.className = "validation-issue-item";
      item.textContent = issue.label || issue;
      item.addEventListener("click", (e) => {
        e.stopPropagation();
        if (issue.id) focusNode(issue.id);
      });
      list.appendChild(item);
    }
    validationSummaryEl.appendChild(list);
  }
}

function renderValidationSummary(report) {
  validationSummaryEl.innerHTML = "";

  validationIssueRow("Duplicate labels", report.duplicate_labels);
  validationIssueRow("Circular references", report.circular_references.map((chain) => ({ label: chain.join(" → ") })));
  validationIssueRow("Large modules (>10 children)", report.large_modules);
  validationIssueRow("Single-child nodes", report.single_child_nodes);
  validationIssueRow("Missing notes", report.missing_notes);
  validationIssueRow("Missing owners", report.missing_owners);
  validationIssueRow("Orphaned nodes", report.orphan_nodes);
  validationIssueRow("Broken references", report.broken_references.map((msg) => ({ label: msg })));

  validationSummaryEl.appendChild(document.createElement("hr")).className = "inspector-divider";

  const depthRow = document.createElement("div");
  depthRow.className = "validation-row";
  const dl = document.createElement("span");
  dl.textContent = "Avg / max depth";
  const dv = document.createElement("strong");
  dv.textContent = `${report.avg_depth} / ${report.max_depth}`;
  depthRow.appendChild(dl);
  depthRow.appendChild(dv);
  validationSummaryEl.appendChild(depthRow);

  const riskWrap = document.createElement("div");
  riskWrap.className = "risk-distribution";
  for (const [level, count] of Object.entries(report.risk_distribution)) {
    if (count === 0) continue;
    const pill = document.createElement("span");
    pill.className = `risk-pill risk-${level.toLowerCase()}`;
    pill.textContent = `${level}: ${count}`;
    riskWrap.appendChild(pill);
  }
  validationSummaryEl.appendChild(riskWrap);
}

function renderActivityLog() {
  activityListEl.innerHTML = "";
  const entries = [...project.activity_log].reverse().slice(0, 30);
  if (entries.length === 0) {
    const empty = document.createElement("div");
    empty.textContent = "No activity yet.";
    activityListEl.appendChild(empty);
    return;
  }
  for (const entry of entries) {
    const item = document.createElement("div");
    item.className = "activity-item";
    const time = document.createElement("div");
    time.className = "activity-time";
    time.textContent = formatDateTime(entry.timestamp);
    const msg = document.createElement("div");
    msg.textContent = entry.message;
    item.appendChild(time);
    item.appendChild(msg);
    activityListEl.appendChild(item);
  }
}

// ---------- Outline import ----------

function closeImportModal() {
  importModal.hidden = true;
}

importOutlineBtn.addEventListener("click", () => {
  if (!focusedNodeId) return;
  exportMenu.hidden = true;
  importText.value = "";
  importModal.hidden = false;
  importText.focus();
});
importCancelBtn.addEventListener("click", closeImportModal);
importXBtn.addEventListener("click", closeImportModal);
importModal.addEventListener("click", (e) => {
  if (e.target === importModal) closeImportModal();
});
importConfirmBtn.addEventListener("click", async () => {
  const text = importText.value.trim();
  if (!text) return;
  importConfirmBtn.disabled = true;
  try {
    const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/import-outline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Import failed. Check the outline format and try again.");
      return;
    }
    const newNode = await res.json();
    closeImportModal();
    focusedNodeId = newNode.id;
    await loadProject();
  } catch (err) {
    alert("Import failed: could not reach the server.");
  } finally {
    importConfirmBtn.disabled = false;
  }
});

// ---------- Search ----------

searchBox.addEventListener("input", () => {
  const q = searchBox.value.trim().toLowerCase();
  searchResults.innerHTML = "";
  if (!q || !project) {
    searchResults.hidden = true;
    return;
  }
  const matches = Object.values(project.nodes)
    .filter((n) => n.label.toLowerCase().includes(q))
    .slice(0, 20);
  if (matches.length === 0) {
    searchResults.hidden = true;
    return;
  }
  for (const match of matches) {
    const row = document.createElement("div");
    row.className = "result";
    const nameEl = document.createElement("div");
    nameEl.textContent = match.label;
    const pathEl = document.createElement("div");
    pathEl.className = "path";
    pathEl.textContent = buildPathString(match.id);
    row.appendChild(nameEl);
    row.appendChild(pathEl);
    row.addEventListener("click", async () => {
      searchBox.value = "";
      searchResults.hidden = true;
      searchResults.innerHTML = "";
      await focusNode(match.id);
    });
    searchResults.appendChild(row);
  }
  searchResults.hidden = false;
});

document.addEventListener("click", (e) => {
  if (searchWrap && !searchWrap.contains(e.target)) {
    searchResults.hidden = true;
  }
});

function buildPathString(nodeId) {
  const chain = [];
  let current = project.nodes[nodeId];
  while (current && current.parent_id) {
    current = project.nodes[current.parent_id];
    chain.unshift(current.parent_id === null ? "Root" : current.label);
  }
  return chain.length ? chain.join(" > ") : "Root";
}

// ---------- Export ----------

exportBtn.addEventListener("click", () => {
  if (exportMenu.hidden) closeImportModal();
  exportMenu.hidden = !exportMenu.hidden;
});

document.addEventListener("click", (e) => {
  if (!exportMenu.hidden && !exportMenu.contains(e.target) && e.target !== exportBtn) {
    exportMenu.hidden = true;
  }
});

exportMenu.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-export]");
  if (!btn || !project) return;
  exportMenu.hidden = true;
  const type = btn.dataset.export;
  if (type === "svg") exportCanvasSvg();
  else if (type === "md") exportMarkdown();
  else if (type === "json") await exportJson();
});

function safeFilename(name) {
  return name.replace(/[^a-z0-9]+/gi, "_").replace(/^_+|_+$/g, "") || "diagram";
}

function downloadBlob(content, filename, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportCanvasSvg() {
  const clone = canvasSvg.cloneNode(true);
  clone.setAttribute("xmlns", SVG_NS);
  const rect = canvasSvg.getBoundingClientRect();
  clone.setAttribute("width", rect.width);
  clone.setAttribute("height", rect.height);
  const svgStr = '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone);
  downloadBlob(svgStr, `${safeFilename(project.name)}_canvas.svg`, "image/svg+xml");
}

function exportMarkdown() {
  const lines = [];
  const walk = (nodeId, depth) => {
    const node = project.nodes[nodeId];
    lines.push("  ".repeat(depth) + "- " + node.label);
    for (const childId of node.children) walk(childId, depth + 1);
  };
  walk(rootId, 0);
  downloadBlob(lines.join("\n") + "\n", `${safeFilename(project.name)}.md`, "text/markdown");
}

async function exportJson() {
  const res = await fetch(`/api/projects/${projectId}/raw`);
  const raw = await res.json();
  downloadBlob(JSON.stringify(raw, null, 2), `${safeFilename(project.name)}.json`, "application/json");
}

// ---------- Inspector ----------

function subtreeDepthClient(nodeId) {
  const node = project.nodes[nodeId];
  let deepest = node.level;
  for (const childId of node.children) deepest = Math.max(deepest, subtreeDepthClient(childId));
  return deepest;
}

function collectSubtreeIds(nodeId) {
  const ids = [nodeId];
  for (const childId of project.nodes[nodeId].children) ids.push(...collectSubtreeIds(childId));
  return ids;
}

function computeWarnings(node) {
  const warnings = [];
  if (node.children.length === 1) {
    warnings.push("This node has exactly 1 child. Consider whether it needs its own level.");
  }
  if (node.children.length > 10) {
    warnings.push(`This node has ${node.children.length} direct children. Consider grouping into sub-levels.`);
  }
  if (node.parent_id && node.children.length > 0) {
    const parent = project.nodes[node.parent_id];
    const ownDepth = subtreeDepthClient(node.id);
    for (const sibId of parent.children) {
      if (sibId === node.id) continue;
      const sibDepth = subtreeDepthClient(sibId);
      if (sibDepth - ownDepth >= 3) {
        warnings.push(
          `This branch is ${sibDepth - ownDepth} levels shallower than sibling "${project.nodes[sibId].label}"'s deepest descendant. Worth checking the structure is consistent.`
        );
        break;
      }
    }
  }
  return warnings;
}

function field(labelText) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  const label = document.createElement("label");
  label.textContent = labelText;
  wrap.appendChild(label);
  return wrap;
}

function infoRow(labelText, valueEl) {
  const row = document.createElement("div");
  row.className = "info-row";
  const l = document.createElement("span");
  l.className = "info-row-label";
  l.textContent = labelText;
  const v = document.createElement("div");
  v.className = "info-row-value";
  v.appendChild(valueEl);
  row.appendChild(l);
  row.appendChild(v);
  return row;
}

function infoStaticValue(text) {
  const span = document.createElement("span");
  span.textContent = text;
  return span;
}

function infoTextValue(value, placeholder, onCommit) {
  const input = document.createElement("input");
  input.className = "info-input";
  input.placeholder = placeholder || "";
  input.value = value || "";
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") input.blur();
  });
  input.addEventListener("blur", () => {
    if (input.value !== (value || "")) onCommit(input.value);
  });
  return input;
}

function formatDateTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function patchNode(payload) {
  await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadProject();
}

const META_DOT_CLASSES = {
  status: { Planned: "dot-info", "In Development": "dot-accent", Done: "dot-success", Blocked: "dot-danger", Deprecated: "dot-neutral" },
  priority: { Low: "dot-info", Medium: "dot-accent", High: "dot-warning", Critical: "dot-danger" },
  complexity: { Low: "dot-success", Medium: "dot-warning", High: "dot-danger" },
  risk_level: { Low: "dot-success", Medium: "dot-warning", High: "dot-danger", Critical: "dot-danger" },
};

function dotClassFor(fieldKey, value) {
  return (META_DOT_CLASSES[fieldKey] && META_DOT_CLASSES[fieldKey][value]) || "dot-neutral";
}

function infoSelectValue(fieldKey, options, node) {
  const wrap = document.createElement("div");
  wrap.className = "info-value-with-dot";
  const dot = document.createElement("span");
  dot.className = `dot ${dotClassFor(fieldKey, node[fieldKey])}`;
  const select = document.createElement("select");
  select.className = "info-select";
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "—";
  select.appendChild(noneOpt);
  for (const opt of options) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    if (node[fieldKey] === opt) o.selected = true;
    select.appendChild(o);
  }
  select.addEventListener("change", () => patchNode({ [fieldKey]: select.value }));
  wrap.appendChild(dot);
  wrap.appendChild(select);
  return wrap;
}

let inspectorActiveTab = "overview"; // overview | properties | references | documentation | history | comments | validation

function renderInspector() {
  inspectorContent.innerHTML = "";
  if (!project || !focusedNodeId) return;
  const node = project.nodes[focusedNodeId];

  // ---- Sticky header: title + level badge + tabs. Always visible while scrolling, so
  // Notes/Comments/etc never lose their "which node is this?" context. ----
  const header = document.createElement("div");
  header.className = "inspector-sticky-header";

  const titleRow = document.createElement("div");
  titleRow.className = "inspector-title-row";
  const titleIcon = document.createElement("span");
  titleIcon.className = "inspector-title-icon";
  titleIcon.textContent = "⚙";
  const labelInput = document.createElement("input");
  labelInput.className = "inspector-title-input";
  labelInput.value = node.label;
  labelInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") labelInput.blur();
  });
  labelInput.addEventListener("blur", async () => {
    const trimmed = labelInput.value.trim();
    if (trimmed && trimmed !== node.label) await patchNode({ label: trimmed });
  });
  const levelPill = document.createElement("span");
  levelPill.className = "level-pill";
  levelPill.textContent = `Level ${node.level}`;
  titleRow.appendChild(titleIcon);
  titleRow.appendChild(labelInput);
  titleRow.appendChild(levelPill);
  header.appendChild(titleRow);

  const tabBar = document.createElement("div");
  tabBar.className = "inspector-tabs";
  const touchingRefCount = project.references.filter((r) => r.from === node.id || r.to === node.id).length;
  const tabDefs = [
    ["overview", "Overview"],
    ["properties", "Properties"],
    ["references", `References${touchingRefCount ? ` (${touchingRefCount})` : ""}`],
    ["documentation", "Documentation"],
    ["history", "History"],
    ["comments", `Comments${node.comments.length ? ` (${node.comments.length})` : ""}`],
    ["validation", "Validation"],
  ];
  for (const [key, label] of tabDefs) {
    const tabBtn = document.createElement("button");
    tabBtn.className = "inspector-tab" + (inspectorActiveTab === key ? " active" : "");
    tabBtn.textContent = label;
    tabBtn.addEventListener("click", () => {
      inspectorActiveTab = key;
      renderInspector();
    });
    tabBar.appendChild(tabBtn);
  }
  header.appendChild(tabBar);
  inspectorContent.appendChild(header);

  const tabContent = document.createElement("div");
  tabContent.className = "inspector-tab-content";
  inspectorContent.appendChild(tabContent);

  if (inspectorActiveTab === "overview") renderOverviewTab(tabContent, node);
  else if (inspectorActiveTab === "properties") renderPropertiesTab(tabContent, node);
  else if (inspectorActiveTab === "references") renderReferencesTab(tabContent, node);
  else if (inspectorActiveTab === "documentation") renderDocumentationTab(tabContent, node);
  else if (inspectorActiveTab === "history") renderHistoryTab(tabContent, node);
  else if (inspectorActiveTab === "validation") renderValidationTab(tabContent, node);
  else renderCommentsTab(tabContent, node);
}

function renderOverviewTab(container, node) {
  const parentNode = node.parent_id ? project.nodes[node.parent_id] : null;
  const infoTable = document.createElement("div");
  infoTable.className = "info-table";
  infoTable.appendChild(infoRow("Parent", infoStaticValue(parentNode ? parentNode.label : "— (root)")));
  infoTable.appendChild(infoRow("Children", infoStaticValue(String(node.children.length))));
  infoTable.appendChild(infoRow("Level", infoStaticValue(String(node.level))));
  container.appendChild(infoTable);

  const btnRow = document.createElement("div");
  btnRow.className = "btn-row";
  const mkBtn = (text, title, onClick) => {
    const b = document.createElement("button");
    b.className = "btn btn-small";
    b.textContent = text;
    b.title = title;
    b.addEventListener("click", onClick);
    return b;
  };
  btnRow.appendChild(
    mkBtn("⇥ Indent", "Make this a child of the node above", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/indent`, { method: "POST" });
      if (!res.ok) alert("Can't indent: no preceding sibling.");
      await loadProject();
    })
  );
  btnRow.appendChild(
    mkBtn("⇤ Outdent", "Move this up one level", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/outdent`, { method: "POST" });
      if (!res.ok) alert("Can't outdent past the root.");
      await loadProject();
    })
  );
  btnRow.appendChild(mkBtn("+ Child", "Add a child node", () => addChild(focusedNodeId)));
  btnRow.appendChild(mkBtn("+ Sibling", "Add a sibling node below", () => addSiblingBelow(focusedNodeId)));
  if (node.parent_id !== null) {
    btnRow.appendChild(
      mkBtn("↑ Move up", "Move earlier among its siblings", async () => {
        const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/move-sibling`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ direction: "up" }),
        });
        if (!res.ok) alert("Already first among its siblings.");
        await loadProject();
      })
    );
    btnRow.appendChild(
      mkBtn("↓ Move down", "Move later among its siblings", async () => {
        const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/move-sibling`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ direction: "down" }),
        });
        if (!res.ok) alert("Already last among its siblings.");
        await loadProject();
      })
    );
    btnRow.appendChild(
      mkBtn("⇧ Promote to root", "Make this node the new root of the whole tree", async () => {
        const confirmed = confirm(
          `Make "${node.label}" the new root? The current root and everything above this node will be reattached underneath it instead.`
        );
        if (!confirmed) return;
        await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/promote-to-root`, { method: "POST" });
        await focusNode(focusedNodeId);
      })
    );
    const delBtn = mkBtn("Delete", "Delete this node", () => deleteNodeFlow(focusedNodeId));
    delBtn.classList.add("btn-danger");
    btnRow.appendChild(delBtn);
  }
  container.appendChild(btnRow);
}

function infoClassificationValue(node) {
  const wrap = document.createElement("div");
  wrap.className = "info-value-with-dot";
  const activeColor = node.custom_color || CLASSIFICATION_COLORS[node.classification];
  const swatch = document.createElement("span");
  swatch.className = "classification-swatch";
  swatch.style.background = activeColor || "transparent";
  swatch.style.borderColor = activeColor || "var(--border)";
  const select = document.createElement("select");
  select.className = "info-select";
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "—";
  select.appendChild(noneOpt);
  for (const opt of CLASSIFICATIONS) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    if (node.classification === opt) o.selected = true;
    select.appendChild(o);
  }
  select.addEventListener("change", () => patchNode({ classification: select.value }));
  wrap.appendChild(swatch);
  wrap.appendChild(select);
  return wrap;
}

function infoColorOverrideValue(node) {
  const wrap = document.createElement("div");
  wrap.className = "info-value-with-dot";
  const colorInput = document.createElement("input");
  colorInput.type = "color";
  colorInput.className = "color-swatch-input";
  colorInput.value = node.custom_color || CLASSIFICATION_COLORS[node.classification] || "#64748b";
  colorInput.title = "Override the classification color for this node";
  colorInput.addEventListener("change", () => patchNode({ custom_color: colorInput.value }));
  wrap.appendChild(colorInput);
  if (node.custom_color) {
    const resetBtn = document.createElement("button");
    resetBtn.className = "btn btn-small";
    resetBtn.textContent = "Reset";
    resetBtn.title = "Remove the color override and fall back to the classification color";
    resetBtn.addEventListener("click", () => patchNode({ custom_color: "" }));
    wrap.appendChild(resetBtn);
  }
  return wrap;
}

function renderPropertiesTab(container, node) {
  const infoTable = document.createElement("div");
  infoTable.className = "info-table";
  infoTable.appendChild(infoRow("Classification", infoClassificationValue(node)));
  infoTable.appendChild(infoRow("Color Override", infoColorOverrideValue(node)));
  infoTable.appendChild(
    infoRow("Node Type", infoTextValue(node.node_type, "e.g. Decision Engine", (v) => patchNode({ node_type: v })))
  );
  infoTable.appendChild(
    infoRow("Status", infoSelectValue("status", ["Planned", "In Development", "Done", "Blocked", "Deprecated"], node))
  );
  infoTable.appendChild(infoRow("Owner", infoTextValue(node.owner, "e.g. your name or team", (v) => patchNode({ owner: v }))));
  infoTable.appendChild(infoRow("Priority", infoSelectValue("priority", ["Low", "Medium", "High", "Critical"], node)));
  infoTable.appendChild(infoRow("Complexity", infoSelectValue("complexity", ["Low", "Medium", "High"], node)));
  infoTable.appendChild(infoRow("Risk Level", infoSelectValue("risk_level", ["Low", "Medium", "High", "Critical"], node)));
  container.appendChild(infoTable);

  container.appendChild(document.createElement("hr")).className = "inspector-divider";

  const tagsField = field("Tags");
  const tagsWrap = document.createElement("div");
  tagsWrap.className = "tag-list";
  for (const tag of node.tags) {
    const pill = document.createElement("span");
    pill.className = "tag-pill";
    const text = document.createElement("span");
    text.textContent = tag;
    const remove = document.createElement("button");
    remove.textContent = "×";
    remove.addEventListener("click", async () => {
      await patchNode({ tags: node.tags.filter((t) => t !== tag) });
    });
    pill.appendChild(text);
    pill.appendChild(remove);
    tagsWrap.appendChild(pill);
  }
  const tagInput = document.createElement("input");
  tagInput.className = "label-input";
  tagInput.placeholder = "Add tag, press Enter";
  tagInput.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const value = tagInput.value.trim();
      if (value && !node.tags.includes(value)) {
        await patchNode({ tags: [...node.tags, value] });
      } else {
        tagInput.value = "";
      }
    }
  });
  tagsField.appendChild(tagsWrap);
  tagsField.appendChild(tagInput);
  container.appendChild(tagsField);
}

function renderReferencesTab(container, node) {
  const touchingRefs = project.references.filter((r) => r.from === node.id || r.to === node.id);
  const subtreeIds = new Set(collectSubtreeIds(node.id));
  const outsideCount = touchingRefs.filter((r) => {
    const other = r.from === node.id ? r.to : r.from;
    return !subtreeIds.has(other);
  }).length;

  const addRefBtn = document.createElement("button");
  addRefBtn.className = "btn btn-small";
  addRefBtn.textContent = "⇢ Add Reference Link";
  addRefBtn.title = "Click two nodes on the canvas in sequence to link them with a reference/dependency";
  addRefBtn.addEventListener("click", () => {
    refMode = true;
    pendingRefFrom = node.id;
    addRefModeBtn.classList.add("active");
    refModeBanner.hidden = false;
    renderCanvas();
  });
  container.appendChild(addRefBtn);

  if (outsideCount > 0) {
    const badge = document.createElement("div");
    badge.className = "ref-badge";
    badge.textContent = `${outsideCount} reference link${outsideCount === 1 ? "" : "s"} outside this subtree`;
    container.appendChild(badge);
  }

  if (touchingRefs.length > 0) {
    const refsField = field(`Reference Links (${touchingRefs.length})`);
    for (const ref of touchingRefs) {
      const otherId = ref.from === node.id ? ref.to : ref.from;
      const otherNode = project.nodes[otherId];
      const direction = ref.from === node.id ? "→" : "←";
      const item = document.createElement("div");
      item.className = "ref-list-item";
      const dot = document.createElement("span");
      dot.className = "dot dot-accent";
      const text = document.createElement("span");
      text.className = "ref-text";
      text.textContent = `${direction} ${otherNode ? otherNode.label : "(unknown)"}${ref.label ? " · " + ref.label : ""}`;
      const delBtn = document.createElement("button");
      delBtn.className = "row-btn delete-node";
      delBtn.textContent = "×";
      delBtn.title = "Remove reference";
      delBtn.addEventListener("click", async () => {
        await fetch(`/api/projects/${projectId}/references/${ref.id}`, { method: "DELETE" });
        await loadProject();
      });
      item.appendChild(dot);
      item.appendChild(text);
      item.appendChild(delBtn);
      refsField.appendChild(item);
    }
    container.appendChild(refsField);
  } else {
    const empty = document.createElement("p");
    empty.className = "inspector-empty-note";
    empty.textContent = "No reference links yet.";
    container.appendChild(empty);
  }
}

function renderDocumentationTab(container, node) {
  const notesField = document.createElement("div");
  notesField.className = "field";
  const notesLabel = document.createElement("label");
  notesLabel.textContent = "Description / Notes";
  notesField.appendChild(notesLabel);
  const textarea = document.createElement("textarea");
  textarea.rows = 6;
  textarea.placeholder = "Add notes…";
  textarea.value = node.notes;
  let notesTimer = null;
  textarea.addEventListener("input", () => {
    clearTimeout(notesTimer);
    notesTimer = setTimeout(async () => {
      await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: textarea.value }),
      });
      if (project.nodes[focusedNodeId]) project.nodes[focusedNodeId].notes = textarea.value;
    }, 500);
  });
  notesField.appendChild(textarea);
  container.appendChild(notesField);

  container.appendChild(document.createElement("hr")).className = "inspector-divider";

  const templateField = field("Templates");
  const saveTplBtn = document.createElement("button");
  saveTplBtn.className = "btn btn-small";
  saveTplBtn.textContent = "Save this subtree as template";
  saveTplBtn.addEventListener("click", async () => {
    const name = prompt("Template name:", node.label);
    if (!name || !name.trim()) return;
    await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/save-as-template`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    });
    renderInspector();
  });
  templateField.appendChild(saveTplBtn);

  const applyRow = document.createElement("div");
  applyRow.className = "btn-row";
  const select = document.createElement("select");
  select.className = "label-input";
  const applyBtn = document.createElement("button");
  applyBtn.className = "btn btn-small";
  applyBtn.textContent = "Apply under this node";
  applyBtn.addEventListener("click", async () => {
    if (!select.value) return;
    await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/apply-template/${select.value}`, {
      method: "POST",
    });
    await loadProject();
  });
  applyRow.appendChild(select);
  applyRow.appendChild(applyBtn);
  templateField.appendChild(applyRow);
  container.appendChild(templateField);

  fetch("/api/templates")
    .then((res) => (res.ok ? res.json() : []))
    .then((templates) => {
      select.innerHTML = "";
      if (templates.length === 0) {
        const opt = document.createElement("option");
        opt.textContent = "No templates saved yet";
        opt.value = "";
        select.appendChild(opt);
        applyBtn.disabled = true;
        return;
      }
      applyBtn.disabled = false;
      for (const t of templates) {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = `${t.name} (${t.node_count} nodes)`;
        select.appendChild(opt);
      }
    });
}

function renderCommentsTab(container, node) {
  for (const comment of node.comments) {
    const item = document.createElement("div");
    item.className = "comment-item";
    const meta = document.createElement("div");
    meta.className = "comment-meta";
    meta.textContent = formatDateTime(comment.created_at);
    const text = document.createElement("div");
    text.className = "comment-text";
    text.textContent = comment.text;
    const delBtn = document.createElement("button");
    delBtn.className = "row-btn delete-node comment-delete";
    delBtn.textContent = "×";
    delBtn.title = "Delete comment";
    delBtn.addEventListener("click", async () => {
      await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/comments/${comment.id}`, {
        method: "DELETE",
      });
      await loadProject();
    });
    const row = document.createElement("div");
    row.className = "comment-row";
    const commentBody = document.createElement("div");
    commentBody.appendChild(meta);
    commentBody.appendChild(text);
    row.appendChild(commentBody);
    row.appendChild(delBtn);
    item.appendChild(row);
    container.appendChild(item);
  }
  const commentInput = document.createElement("textarea");
  commentInput.rows = 2;
  commentInput.placeholder = "Add a comment…";
  commentInput.addEventListener("keydown", async (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const value = commentInput.value.trim();
      if (!value) return;
      await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value }),
      });
      await loadProject();
    }
  });
  container.appendChild(commentInput);
}

function renderHistoryTab(container, node) {
  const note = document.createElement("p");
  note.className = "inspector-empty-note";
  note.textContent = "Changes across the project that mention this node's label.";
  container.appendChild(note);

  const entries = (project.activity_log || [])
    .filter((entry) => entry.message.includes(node.label))
    .slice()
    .reverse();

  if (entries.length === 0) {
    const empty = document.createElement("p");
    empty.className = "inspector-empty-note";
    empty.textContent = "No recorded changes mention this node yet.";
    container.appendChild(empty);
    return;
  }

  for (const entry of entries) {
    const row = document.createElement("div");
    row.className = "history-row";
    const meta = document.createElement("div");
    meta.className = "comment-meta";
    meta.textContent = formatDateTime(entry.timestamp);
    const text = document.createElement("div");
    text.className = "comment-text";
    text.textContent = entry.message;
    row.appendChild(meta);
    row.appendChild(text);
    container.appendChild(row);
  }
}

function renderValidationTab(container, node) {
  const warnings = computeWarnings(node);
  if (warnings.length === 0) {
    const ok = document.createElement("p");
    ok.className = "inspector-empty-note";
    ok.textContent = "No structural warnings for this node.";
    container.appendChild(ok);
  } else {
    for (const warning of warnings) {
      const box = document.createElement("div");
      box.className = "warning-box";
      box.textContent = warning;
      container.appendChild(box);
    }
  }

  container.appendChild(document.createElement("hr")).className = "inspector-divider";

  if (!lastValidationReport) {
    const runBtn = document.createElement("button");
    runBtn.className = "btn btn-small";
    runBtn.textContent = "Run Validation";
    runBtn.title = "Scan the whole tree so project-wide issues can be cross-checked against this node";
    runBtn.addEventListener("click", async () => {
      await refreshHealthPanel();
      renderInspector();
    });
    container.appendChild(runBtn);
    return;
  }

  const report = lastValidationReport;
  const hasIssue = (issues) => issues.some((issue) => issue.id === node.id);
  const flags = [];
  if (hasIssue(report.duplicate_labels)) flags.push("Duplicate label — another node shares this exact label.");
  if (hasIssue(report.large_modules)) flags.push("Large module — more than 10 direct children.");
  if (hasIssue(report.single_child_nodes)) flags.push("Single-child node — consider whether it needs its own level.");
  if (hasIssue(report.orphan_nodes)) flags.push("Orphaned — unreachable from the root node.");
  if (hasIssue(report.missing_owners)) flags.push("No owner assigned.");
  if (report.circular_references.some((cycle) => cycle.includes(node.label))) {
    flags.push("Part of a circular reference chain.");
  }
  if (!node.notes.trim()) flags.push("Missing description/notes.");

  if (flags.length === 0) {
    const ok = document.createElement("p");
    ok.className = "inspector-empty-note";
    ok.textContent = "No project-wide validation issues involve this node.";
    container.appendChild(ok);
  } else {
    const field_ = field("Project-wide issues involving this node");
    for (const flag of flags) {
      const box = document.createElement("div");
      box.className = "warning-box";
      box.textContent = flag;
      field_.appendChild(box);
    }
    container.appendChild(field_);
  }
}
