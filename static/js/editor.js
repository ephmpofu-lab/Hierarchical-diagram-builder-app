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
const CLASSIFICATION_ICONS = {
  "AI Agent": "🤖",
  Workflow: "⚙",
  Database: "🗄",
  API: "🔌",
  UI: "🖥",
  Decision: "◆",
  Configuration: "🔧",
  Storage: "📦",
  Queue: "➜",
  Security: "🔒",
  Validation: "✓",
  Service: "⚡",
  Monitoring: "📊",
  Infrastructure: "🏗",
};

// Planning status is distinct from the freeform `status` field (Planned/In Development/
// Done/Blocked/Deprecated) — this is the fixed 5-state progress tracker that turns the
// architecture tree itself into a planning board (see PLANNING_ENHANCEMENTS notes).
const PLANNING_STATUSES = ["Not Started", "In Progress", "Completed", "Needs Review", "Blocked"];
const PLANNING_STATUS_ICONS = {
  "Not Started": "○",
  "In Progress": "◐",
  Completed: "✓",
  "Needs Review": "⚠",
  Blocked: "⛔",
};
const PLANNING_STATUS_COLORS = {
  "Not Started": "#64748b",
  "In Progress": "#2563eb",
  Completed: "#16a34a",
  "Needs Review": "#f59e0b",
  Blocked: "#dc2626",
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
const statusFilterBtn = document.getElementById("statusFilterBtn");
const statusFilterMenu = document.getElementById("statusFilterMenu");
const collapseExpandBtn = document.getElementById("collapseExpandBtn");
const collapseExpandMenu = document.getElementById("collapseExpandMenu");
const collapseAllBtn = document.getElementById("collapseAllBtn");
const expandBranchBtn = document.getElementById("expandBranchBtn");
const expandToLevelBtn = document.getElementById("expandToLevelBtn");
const undoBtn = document.getElementById("undoBtn");
const redoBtn = document.getElementById("redoBtn");
const addRefModeBtn = document.getElementById("addRefModeBtn");
const refModeBanner = document.getElementById("refModeBanner");
const zoomInBtn = document.getElementById("zoomInBtn");
const zoomOutBtn = document.getElementById("zoomOutBtn");
const zoomLevelEl = document.getElementById("zoomLevel");
const fitViewBtn = document.getElementById("fitViewBtn");
const fitAllBtn = document.getElementById("fitAllBtn");
const selectionToolbar = document.getElementById("selectionToolbar");
const selectionCountEl = document.getElementById("selectionCount");
const selCollapseBtn = document.getElementById("selCollapseBtn");
const selExpandBtn = document.getElementById("selExpandBtn");
const selColorBtn = document.getElementById("selColorBtn");
const selStatusBtn = document.getElementById("selStatusBtn");
const selStatusMenu = document.getElementById("selStatusMenu");
const selGroupBtn = document.getElementById("selGroupBtn");
const selClearBtn = document.getElementById("selClearBtn");
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
let activeStatusFilters = new Set(PLANNING_STATUSES);

// Nodes with no planning_status set are never filtered out — only nodes that HAVE an
// explicit status get faded when their status is unchecked, so freshly-added nodes never
// mysteriously vanish from view.
function nodeMatchesStatusFilter(node) {
  if (!node.planning_status) return true;
  return activeStatusFilters.has(node.planning_status);
}

// ---------- Multi-selection ----------
// Independent of focusedNodeId (which drives the Inspector/breadcrumb/camera): this is a
// lightweight set of node ids the user has multi-selected on the canvas, for bulk actions.
let selectedNodeIds = new Set();

function selectOnly(nodeId) {
  selectedNodeIds = new Set([nodeId]);
  updateSelectionToolbar();
}

function toggleNodeSelection(nodeId) {
  if (selectedNodeIds.has(nodeId)) selectedNodeIds.delete(nodeId);
  else selectedNodeIds.add(nodeId);
  updateSelectionToolbar();
  renderCanvas();
}

function clearSelection() {
  selectedNodeIds = new Set();
  updateSelectionToolbar();
}

function updateSelectionToolbar() {
  const count = selectedNodeIds.size;
  selectionToolbar.hidden = count === 0;
  if (count > 0) {
    selectionCountEl.textContent = `${count} selected`;
  }
}

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

let progressCache = new Map();

// One bottom-up pass over the whole tree, computing each node's rollup over its FULL
// subtree (not just direct children) so progress is meaningful at any level of nesting.
// is_group nodes are organizational (level-transparent) and don't count as work items
// themselves, but their own children still roll up through them into their parent.
function computeAllProgress() {
  const cache = new Map();
  function walk(id) {
    const n = project.nodes[id];
    const stats = { total: 0, completed: 0, inProgress: 0, needsReview: 0, blocked: 0, notStarted: 0 };
    for (const childId of n.children) {
      const child = project.nodes[childId];
      const childStats = walk(childId);
      if (!child.is_group) {
        stats.total++;
        if (child.planning_status === "Completed") stats.completed++;
        else if (child.planning_status === "In Progress") stats.inProgress++;
        else if (child.planning_status === "Needs Review") stats.needsReview++;
        else if (child.planning_status === "Blocked") stats.blocked++;
        else stats.notStarted++;
      }
      stats.total += childStats.total;
      stats.completed += childStats.completed;
      stats.inProgress += childStats.inProgress;
      stats.needsReview += childStats.needsReview;
      stats.blocked += childStats.blocked;
      stats.notStarted += childStats.notStarted;
    }
    stats.percent = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;
    cache.set(id, stats);
    return stats;
  }
  if (rootId && project.nodes[rootId]) walk(rootId);
  return cache;
}

function render() {
  if (project) progressCache = computeAllProgress();
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
        pushUndoSnapshot("Rename node");
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
  pushUndoSnapshot("Add child");
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
  pushUndoSnapshot("Add sibling");
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
  pushUndoSnapshot("Delete node");
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
  const activeTagGlobal = document.activeElement && document.activeElement.tagName;
  const typingGlobal = activeTagGlobal === "INPUT" || activeTagGlobal === "TEXTAREA";
  if (!typingGlobal && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !e.shiftKey) {
    e.preventDefault();
    await performUndo();
    return;
  }
  if (
    !typingGlobal &&
    (e.ctrlKey || e.metaKey) &&
    ((e.key.toLowerCase() === "z" && e.shiftKey) || e.key.toLowerCase() === "y")
  ) {
    e.preventDefault();
    await performRedo();
    return;
  }

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
    pushUndoSnapshot(e.shiftKey ? "Outdent" : "Indent");
    const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/${endpoint}`, {
      method: "POST",
    });
    if (res.ok) {
      await loadProject();
    } else {
      undoStack.pop();
      updateUndoRedoButtons();
    }
  } else if (e.key === "Enter") {
    e.preventDefault();
    await addSiblingBelow(focusedNodeId);
  } else if (e.key === "Delete") {
    e.preventDefault();
    await deleteNodeFlow(focusedNodeId);
  }
});

// ---------- Undo / Redo ----------
// Scoped to structural edits: create, delete, rename, reparent, indent/outdent, and
// move-sibling. Rather than hand-writing an inverse for every action (fragile, especially
// for delete which destroys data), each of those flows snapshots the whole project just
// before it runs; undo/redo replay a snapshot wholesale via PUT /restore. Cosmetic field
// edits (status, tags, notes, comments, etc.) are not part of this history.
const UNDO_LIMIT = 50;
let undoStack = [];
let redoStack = [];

function cloneProject() {
  return JSON.parse(JSON.stringify(project));
}

function pushUndoSnapshot(label) {
  if (!project) return;
  undoStack.push({ label, snapshot: cloneProject() });
  if (undoStack.length > UNDO_LIMIT) undoStack.shift();
  redoStack = [];
  updateUndoRedoButtons();
}

function updateUndoRedoButtons() {
  undoBtn.disabled = undoStack.length === 0;
  redoBtn.disabled = redoStack.length === 0;
  undoBtn.title = undoStack.length
    ? `Undo: ${undoStack[undoStack.length - 1].label} (Ctrl+Z)`
    : "Undo the last change (Ctrl+Z)";
  redoBtn.title = redoStack.length
    ? `Redo: ${redoStack[redoStack.length - 1].label} (Ctrl+Shift+Z / Ctrl+Y)`
    : "Redo the last undone change (Ctrl+Shift+Z / Ctrl+Y)";
}

async function restoreSnapshot(snapshotProject) {
  await fetch(`/api/projects/${projectId}/restore`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(snapshotProject),
  });
  await loadProject();
  if (!project.nodes[focusedNodeId]) {
    focusedNodeId = rootId;
    render();
  }
}

async function performUndo() {
  if (undoStack.length === 0 || !project) return;
  const entry = undoStack.pop();
  redoStack.push({ label: entry.label, snapshot: cloneProject() });
  await restoreSnapshot(entry.snapshot);
  updateUndoRedoButtons();
}

async function performRedo() {
  if (redoStack.length === 0 || !project) return;
  const entry = redoStack.pop();
  undoStack.push({ label: entry.label, snapshot: cloneProject() });
  await restoreSnapshot(entry.snapshot);
  updateUndoRedoButtons();
}

undoBtn.addEventListener("click", performUndo);
redoBtn.addEventListener("click", performRedo);
updateUndoRedoButtons();

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
  // Soft-cap even faded context rows so an ancestor with hundreds of siblings doesn't
  // blow out the layout — this is context, not the thing being worked on.
  const capped = siblings.length > MAX_UNGROUPED_VISIBLE ? siblings.slice(0, MAX_UNGROUPED_VISIBLE) : siblings;
  const activeX = positions.get(activeId).x;
  capped.forEach((sib, i) => {
    const side = i % 2 === 0 ? 1 : -1;
    const rank = Math.floor(i / 2) + 1;
    positions.set(sib.id, { x: activeX + side * rank * (NODE_W + COL_GAP), y });
    fadedIds.add(sib.id);
  });
}

function computeCanvasLayout(viewW, viewH) {
  const focus = project.nodes[focusedNodeId];
  const parent = focus.parent_id ? project.nodes[focus.parent_id] : null;

  // Full ancestor chain from the immediate parent up to the root: [parent, grandparent, ...,
  // root]. Answers "how did I get here / what's above me" at any depth, not just two levels
  // up — architectural context must never be lost, no matter how deeply nested the focus is.
  const ancestorChain = [];
  let cur = focus;
  while (cur.parent_id) {
    cur = project.nodes[cur.parent_id];
    ancestorChain.push(cur);
  }

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

  // Every ancestor sits on the direct path (full opacity); every OTHER child of that
  // ancestor (i.e. its siblings at that level) renders faded alongside it, never omitted.
  ancestorChain.forEach((ancestor, i) => {
    const y = viewH / 2 - (i + 1) * ROW_GAP;
    positions.set(ancestor.id, { x: viewW / 2, y });
    const childOnPath = i === 0 ? focus.id : ancestorChain[i - 1].id;
    const siblings = ancestor.children.filter((id) => id !== childOnPath).map((id) => project.nodes[id]);
    layoutSiblingRow(siblings, ancestor.id, y, positions, fadedIds);
    for (const sib of siblings) contextEdges.push({ fromId: ancestor.id, toId: sib.id });
  });

  if (parent) {
    const focusSiblings = parent.children.filter((id) => id !== focus.id).map((id) => project.nodes[id]);
    layoutSiblingRow(focusSiblings, focus.id, viewH / 2, positions, fadedIds);
    for (const sib of focusSiblings) contextEdges.push({ fromId: parent.id, toId: sib.id });
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
  let minY = (ancestorChain.length > 0 ? viewH / 2 - ancestorChain.length * ROW_GAP : viewH / 2) - NODE_H / 2;
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
    ancestorChain,
    visibleChildren,
    hiddenCount,
    positions,
    fadedIds,
    contextEdges,
    bounds: { minX, maxX, minY, maxY },
  };
}

function renderCanvas() {
  hideNodeHoverTooltip();
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
  smoothZoomNextRender = false;
}

function renderFocusCanvas(viewW, viewH) {
  const { focus, parent, ancestorChain, visibleChildren, hiddenCount, positions, fadedIds, contextEdges } =
    computeCanvasLayout(viewW, viewH);
  const visibleIds = new Set(positions.keys());

  const viewport = document.createElementNS(SVG_NS, "g");
  viewport.setAttribute("class", "viewport-group" + (smoothZoomNextRender ? " smooth" : ""));
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
  // Rest of the direct ancestor chain above the parent (grandparent, great-grandparent, ...)
  for (let i = 1; i < ancestorChain.length; i++) {
    const child = ancestorChain[i - 1];
    const ancestor = ancestorChain[i];
    edgesGroup.appendChild(drawTreeEdge(positions.get(ancestor.id), positions.get(child.id), ancestor.id, child.id));
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

  for (const ancestor of ancestorChain) {
    nodesGroup.appendChild(drawNode(ancestor, positions.get(ancestor.id), !nodeMatchesStatusFilter(ancestor)));
  }
  for (const fadedId of fadedIds) {
    nodesGroup.appendChild(drawNode(project.nodes[fadedId], positions.get(fadedId), true));
  }
  nodesGroup.appendChild(drawNode(focus, positions.get(focus.id)));
  for (const child of visibleChildren) {
    nodesGroup.appendChild(drawNode(child, positions.get(child.id), !nodeMatchesStatusFilter(child)));
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
  viewport.setAttribute("class", "viewport-group" + (smoothZoomNextRender ? " smooth" : ""));
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
    const n = project.nodes[nodeId];
    nodesGroup.appendChild(drawNode(n, pos, !nodeMatchesStatusFilter(n)));
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
      pushUndoSnapshot("Reparent node");
      const res = await fetch(`/api/projects/${projectId}/nodes/${childId}/reparent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_parent_id: targetId }),
      });
      if (!res.ok) {
        undoStack.pop();
        updateUndoRedoButtons();
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
    x: lastViewW / 2 + (clientX - rect.left - lastViewW / 2 - panOffsetX) / zoomScale,
    y: lastViewH / 2 + (clientY - rect.top - lastViewH / 2 - panOffsetY) / zoomScale,
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
  if (selectedNodeIds.has(node.id)) classes.push("multi-selected");
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

  if (!node.is_group && node.planning_status) {
    const planBadge = document.createElementNS(SVG_NS, "g");
    planBadge.setAttribute("class", "planning-badge");
    const planCircle = document.createElementNS(SVG_NS, "circle");
    planCircle.setAttribute("cx", pos.x - NODE_W / 2 + 9);
    planCircle.setAttribute("cy", pos.y + NODE_H / 2 - 8);
    planCircle.setAttribute("r", 7);
    planCircle.setAttribute("fill", PLANNING_STATUS_COLORS[node.planning_status] || "var(--text-muted)");
    const planIcon = document.createElementNS(SVG_NS, "text");
    planIcon.setAttribute("class", "planning-badge-text");
    planIcon.setAttribute("x", pos.x - NODE_W / 2 + 9);
    planIcon.setAttribute("y", pos.y + NODE_H / 2 - 8);
    planIcon.textContent = PLANNING_STATUS_ICONS[node.planning_status] || "";
    planBadge.appendChild(planCircle);
    planBadge.appendChild(planIcon);
    group.appendChild(planBadge);
  }

  const progress = progressCache.get(node.id);
  if (!node.is_group && progress && progress.total > 0) {
    const barY = pos.y + NODE_H / 2 + 4;
    const track = document.createElementNS(SVG_NS, "rect");
    track.setAttribute("class", "progress-track");
    track.setAttribute("x", pos.x - NODE_W / 2);
    track.setAttribute("y", barY);
    track.setAttribute("width", NODE_W);
    track.setAttribute("height", 3);
    track.setAttribute("rx", 1.5);
    const fill = document.createElementNS(SVG_NS, "rect");
    fill.setAttribute("class", "progress-fill");
    fill.setAttribute("x", pos.x - NODE_W / 2);
    fill.setAttribute("y", barY);
    fill.setAttribute("width", Math.max(2, (NODE_W * progress.percent) / 100));
    fill.setAttribute("height", 3);
    fill.setAttribute("rx", 1.5);
    group.appendChild(track);
    group.appendChild(fill);
  }

  group.addEventListener("click", (e) => {
    if (refMode) {
      e.preventDefault();
      e.stopPropagation();
      handleRefModeClick(node.id);
      return;
    }
    if (e.shiftKey || e.ctrlKey || e.metaKey) {
      e.stopPropagation();
      toggleNodeSelection(node.id);
      return;
    }
    selectOnly(node.id);
    focusNode(node.id);
  });

  group.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    e.stopPropagation();
    openContextMenu(node.id, e.clientX, e.clientY);
  });

  group.addEventListener("mouseenter", (e) => {
    if (refMode) return;
    showNodeHoverTooltip(node, e.clientX, e.clientY);
  });
  group.addEventListener("mousemove", (e) => {
    if (refMode) return;
    positionHoverTooltip(e.clientX, e.clientY);
  });
  group.addEventListener("mouseleave", hideNodeHoverTooltip);

  group.addEventListener("dblclick", (e) => {
    e.preventDefault();
    e.stopPropagation();
    zoomToNode(node.id);
  });

  return group;
}

// ---------- Node hover tooltip ----------
// A rich hover popover so users can scan a node's key facts without clicking into the
// Inspector — distinct from the title= tooltips on toolbar chrome.
let hoverTooltipEl = null;

function ensureHoverTooltip() {
  if (!hoverTooltipEl) {
    hoverTooltipEl = document.createElement("div");
    hoverTooltipEl.className = "node-hover-tooltip";
    hoverTooltipEl.hidden = true;
    document.body.appendChild(hoverTooltipEl);
  }
  return hoverTooltipEl;
}

function hoverField(label, value) {
  const row = document.createElement("div");
  row.className = "hover-row";
  const l = document.createElement("span");
  l.textContent = label;
  const v = document.createElement("strong");
  v.textContent = value;
  row.appendChild(l);
  row.appendChild(v);
  return row;
}

function showNodeHoverTooltip(node, clientX, clientY) {
  const el = ensureHoverTooltip();
  el.innerHTML = "";

  const title = document.createElement("div");
  title.className = "hover-title";
  title.textContent = node.label;
  el.appendChild(title);

  if (node.notes.trim()) {
    const desc = document.createElement("div");
    desc.className = "hover-desc";
    desc.textContent = node.notes.length > 140 ? node.notes.slice(0, 139) + "…" : node.notes;
    el.appendChild(desc);
  }

  const fields = document.createElement("div");
  fields.className = "hover-fields";
  if (node.node_type) fields.appendChild(hoverField("Type", node.node_type));
  if (node.classification) {
    fields.appendChild(hoverField("Classification", `${CLASSIFICATION_ICONS[node.classification] || ""} ${node.classification}`));
  }
  if (node.status) fields.appendChild(hoverField("Status", node.status));
  if (node.planning_status) {
    fields.appendChild(hoverField("Planning", `${PLANNING_STATUS_ICONS[node.planning_status]} ${node.planning_status}`));
  }
  if (node.owner) fields.appendChild(hoverField("Owner", node.owner));
  if (node.priority) fields.appendChild(hoverField("Priority", node.priority));
  if (node.risk_level) fields.appendChild(hoverField("Risk", node.risk_level));
  const stats = progressCache.get(node.id);
  if (stats && stats.total > 0) {
    fields.appendChild(hoverField("Completion", `${stats.completed} / ${stats.total} (${stats.percent}%)`));
  }
  fields.appendChild(hoverField("Children", String(node.children.length)));
  const touchingRefs = project.references.filter((r) => r.from === node.id || r.to === node.id).length;
  if (touchingRefs > 0) fields.appendChild(hoverField("References", String(touchingRefs)));
  el.appendChild(fields);

  el.hidden = false;
  positionHoverTooltip(clientX, clientY);
}

function positionHoverTooltip(clientX, clientY) {
  if (!hoverTooltipEl || hoverTooltipEl.hidden) return;
  const offset = 16;
  const rect = hoverTooltipEl.getBoundingClientRect();
  let left = clientX + offset;
  let top = clientY + offset;
  if (left + rect.width > window.innerWidth) left = clientX - rect.width - offset;
  if (top + rect.height > window.innerHeight) top = clientY - rect.height - offset;
  hoverTooltipEl.style.left = `${Math.max(4, left)}px`;
  hoverTooltipEl.style.top = `${Math.max(4, top)}px`;
}

function hideNodeHoverTooltip() {
  if (hoverTooltipEl) hoverTooltipEl.hidden = true;
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
      if (label && label.trim()) {
        pushUndoSnapshot("Rename node");
        patchNodeById(nodeId, { label: label.trim() });
      }
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

// ---------- Zoom / pan navigation ----------
// Professional-editor feel (Figma/Mural/Miro/CAD): plain mouse wheel always zooms toward
// the cursor (not the viewport center), middle-mouse-button drag pans, double-click a node
// zooms in on it, and discrete zoom changes (buttons, fit, double-click) animate smoothly
// via a CSS transition toggled on the viewport <g> — continuous interactions (wheel ticks,
// live panning) stay instant so they don't feel laggy.
let smoothZoomNextRender = false;

function zoomAtPoint(newScaleRaw, clientX, clientY, smooth) {
  const newScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, newScaleRaw));
  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;
  const screenX = clientX - rect.left;
  const screenY = clientY - rect.top;
  const contentX = viewW / 2 + (screenX - viewW / 2 - panOffsetX) / zoomScale;
  const contentY = viewH / 2 + (screenY - viewH / 2 - panOffsetY) / zoomScale;
  panOffsetX = screenX - viewW / 2 - newScale * (contentX - viewW / 2);
  panOffsetY = screenY - viewH / 2 - newScale * (contentY - viewH / 2);
  zoomScale = newScale;
  zoomLevelEl.textContent = `${Math.round(zoomScale * 100)}%`;
  smoothZoomNextRender = !!smooth;
  renderCanvas();
}

function viewportCenterClient() {
  const rect = canvasSvg.getBoundingClientRect();
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
}

zoomInBtn.addEventListener("click", () => {
  const c = viewportCenterClient();
  zoomAtPoint(zoomScale + ZOOM_STEP, c.x, c.y, true);
});
zoomOutBtn.addEventListener("click", () => {
  const c = viewportCenterClient();
  zoomAtPoint(zoomScale - ZOOM_STEP, c.x, c.y, true);
});

canvasSvg.addEventListener(
  "wheel",
  (e) => {
    if (!project || !focusedNodeId) return;
    e.preventDefault();
    zoomAtPoint(zoomScale + (e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP), e.clientX, e.clientY, false);
  },
  { passive: false }
);

let isPanning = false;
let panDragStart = null;

canvasSvg.addEventListener("mousedown", (e) => {
  if (e.button !== 1) return; // middle mouse button only
  e.preventDefault();
  isPanning = true;
  panDragStart = { clientX: e.clientX, clientY: e.clientY, startX: panOffsetX, startY: panOffsetY };
  canvasSvg.classList.add("panning");
});
window.addEventListener("mousemove", (e) => {
  if (!isPanning || !panDragStart) return;
  panOffsetX = panDragStart.startX + (e.clientX - panDragStart.clientX);
  panOffsetY = panDragStart.startY + (e.clientY - panDragStart.clientY);
  renderCanvas();
});
window.addEventListener("mouseup", (e) => {
  if (e.button !== 1 || !isPanning) return;
  isPanning = false;
  panDragStart = null;
  canvasSvg.classList.remove("panning");
});
canvasSvg.addEventListener("auxclick", (e) => {
  if (e.button === 1) e.preventDefault();
});

function zoomToNode(nodeId) {
  focusedNodeId = nodeId;
  renderOutline();
  renderBreadcrumb();
  renderInspector();
  renderMinimap();
  panOffsetX = 0;
  panOffsetY = 0;
  zoomScale = Math.min(ZOOM_MAX, 1.6);
  zoomLevelEl.textContent = `${Math.round(zoomScale * 100)}%`;
  smoothZoomNextRender = true;
  renderCanvas();
}

function fitToView(smooth = true) {
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
  smoothZoomNextRender = smooth;
  renderCanvas();
}

fitAllBtn.addEventListener("click", () => {
  viewMode = "full";
  focusModeBtn.classList.remove("active");
  fullArchModeBtn.classList.add("active");
  fitToView();
});

// ---------- Rubber-band box select ----------

let selectionBoxStart = null;
let selectionBoxEl = null;

function updateSelectionBoxRect(clientX, clientY) {
  if (!selectionBoxEl || !selectionBoxStart) return;
  const left = Math.min(selectionBoxStart.x, clientX);
  const top = Math.min(selectionBoxStart.y, clientY);
  selectionBoxEl.style.left = `${left}px`;
  selectionBoxEl.style.top = `${top}px`;
  selectionBoxEl.style.width = `${Math.abs(clientX - selectionBoxStart.x)}px`;
  selectionBoxEl.style.height = `${Math.abs(clientY - selectionBoxStart.y)}px`;
}

canvasSvg.addEventListener("mousedown", (e) => {
  if (e.button !== 0 || refMode || e.target !== canvasSvg) return;
  selectionBoxStart = { x: e.clientX, y: e.clientY };
  selectionBoxEl = document.createElement("div");
  selectionBoxEl.className = "selection-box";
  document.body.appendChild(selectionBoxEl);
  updateSelectionBoxRect(e.clientX, e.clientY);
});

window.addEventListener("mousemove", (e) => {
  if (!selectionBoxStart) return;
  updateSelectionBoxRect(e.clientX, e.clientY);
});

window.addEventListener("mouseup", (e) => {
  if (!selectionBoxStart) return;
  const boxLeft = Math.min(selectionBoxStart.x, e.clientX);
  const boxRight = Math.max(selectionBoxStart.x, e.clientX);
  const boxTop = Math.min(selectionBoxStart.y, e.clientY);
  const boxBottom = Math.max(selectionBoxStart.y, e.clientY);
  selectionBoxStart = null;
  if (selectionBoxEl) {
    selectionBoxEl.remove();
    selectionBoxEl = null;
  }

  const svgRect = canvasSvg.getBoundingClientRect();
  const hits = [];
  for (const [nodeId, pos] of lastVisiblePositions.entries()) {
    const localX = lastViewW / 2 + panOffsetX + zoomScale * (pos.x - lastViewW / 2);
    const localY = lastViewH / 2 + panOffsetY + zoomScale * (pos.y - lastViewH / 2);
    const screenX = svgRect.left + localX;
    const screenY = svgRect.top + localY;
    if (screenX >= boxLeft && screenX <= boxRight && screenY >= boxTop && screenY <= boxBottom) {
      hits.push(nodeId);
    }
  }
  if (hits.length === 0) return;
  if (!e.shiftKey) selectedNodeIds = new Set();
  for (const id of hits) selectedNodeIds.add(id);
  updateSelectionToolbar();
  renderCanvas();
});

// ---------- Bulk selection actions ----------

selClearBtn.addEventListener("click", () => {
  clearSelection();
  renderCanvas();
});

selCollapseBtn.addEventListener("click", async () => {
  for (const id of selectedNodeIds) {
    await fetch(`/api/projects/${projectId}/nodes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collapsed: true }),
    });
  }
  await loadProject();
});

selExpandBtn.addEventListener("click", async () => {
  for (const id of selectedNodeIds) {
    await fetch(`/api/projects/${projectId}/nodes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collapsed: false }),
    });
  }
  await loadProject();
});

selColorBtn.addEventListener("click", () => {
  const colorInput = document.createElement("input");
  colorInput.type = "color";
  colorInput.value = "#2563eb";
  colorInput.style.position = "fixed";
  colorInput.style.left = "-9999px";
  document.body.appendChild(colorInput);
  colorInput.addEventListener("change", async () => {
    for (const id of selectedNodeIds) {
      await fetch(`/api/projects/${projectId}/nodes/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ custom_color: colorInput.value }),
      });
    }
    colorInput.remove();
    await loadProject();
  });
  colorInput.click();
});

selStatusBtn.addEventListener("click", () => {
  selStatusMenu.hidden = !selStatusMenu.hidden;
});
document.addEventListener("click", (e) => {
  if (!selStatusMenu.hidden && !selStatusMenu.contains(e.target) && e.target !== selStatusBtn) {
    selStatusMenu.hidden = true;
  }
});
selStatusMenu.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-status]");
  if (!btn) return;
  selStatusMenu.hidden = true;
  for (const id of selectedNodeIds) {
    await fetch(`/api/projects/${projectId}/nodes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ planning_status: btn.dataset.status }),
    });
  }
  await loadProject();
});

selGroupBtn.addEventListener("click", async () => {
  const ids = [...selectedNodeIds];
  if (ids.length < 2) {
    alert("Select at least two nodes that share the same parent to group them.");
    return;
  }
  const nodes = ids.map((id) => project.nodes[id]);
  const parentId = nodes[0].parent_id;
  if (!parentId || nodes.some((n) => n.parent_id !== parentId)) {
    alert("Grouping requires all selected nodes to share the same parent.");
    return;
  }
  const name = prompt("Name for this group:");
  if (!name || !name.trim()) return;
  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: parentId, label: name.trim(), is_group: true }),
  });
  const groupNode = await res.json();
  for (const id of ids) {
    await fetch(`/api/projects/${projectId}/nodes/${id}/reparent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_parent_id: groupNode.id }),
    });
  }
  clearSelection();
  await loadProject();
  focusNode(groupNode.id);
});

fitViewBtn.addEventListener("click", () => fitToView());

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

// ---------- Visual status filters ----------

statusFilterBtn.addEventListener("click", () => {
  if (statusFilterMenu.hidden) {
    exportMenu.hidden = true;
    collapseExpandMenu.hidden = true;
    closeImportModal();
  }
  statusFilterMenu.hidden = !statusFilterMenu.hidden;
});
document.addEventListener("click", (e) => {
  if (!statusFilterMenu.hidden && !statusFilterMenu.contains(e.target) && e.target !== statusFilterBtn) {
    statusFilterMenu.hidden = true;
  }
});
statusFilterMenu.addEventListener("change", (e) => {
  const checkbox = e.target.closest("input[data-filter]");
  if (!checkbox) return;
  if (checkbox.checked) activeStatusFilters.add(checkbox.dataset.filter);
  else activeStatusFilters.delete(checkbox.dataset.filter);
  const allChecked = activeStatusFilters.size === PLANNING_STATUSES.length;
  statusFilterBtn.classList.toggle("active", !allChecked);
  renderCanvas();
});

// ---------- Bulk collapse / expand ----------

async function setCollapsedForIds(ids, collapsed) {
  for (const id of ids) {
    const node = project.nodes[id];
    if (!node || node.children.length === 0) continue;
    await fetch(`/api/projects/${projectId}/nodes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collapsed }),
    });
  }
  await loadProject();
}

collapseExpandBtn.addEventListener("click", () => {
  if (collapseExpandMenu.hidden) {
    exportMenu.hidden = true;
    statusFilterMenu.hidden = true;
    closeImportModal();
  }
  collapseExpandMenu.hidden = !collapseExpandMenu.hidden;
});
document.addEventListener("click", (e) => {
  if (!collapseExpandMenu.hidden && !collapseExpandMenu.contains(e.target) && e.target !== collapseExpandBtn) {
    collapseExpandMenu.hidden = true;
  }
});

collapseAllBtn.addEventListener("click", async () => {
  collapseExpandMenu.hidden = true;
  const allIds = Object.keys(project.nodes).filter((id) => id !== rootId);
  await setCollapsedForIds(allIds, true);
});

expandBranchBtn.addEventListener("click", async () => {
  collapseExpandMenu.hidden = true;
  if (!focusedNodeId) return;
  await setCollapsedForIds(collectSubtreeIds(focusedNodeId), false);
});

expandToLevelBtn.addEventListener("click", async () => {
  collapseExpandMenu.hidden = true;
  const raw = prompt("Show levels 1 through N (collapses everything deeper):", "3");
  const level = parseInt(raw, 10);
  if (!raw || isNaN(level) || level < 1) return;
  for (const node of Object.values(project.nodes)) {
    if (node.children.length === 0) continue;
    const shouldCollapse = node.level >= level;
    if (node.collapsed !== shouldCollapse) {
      await fetch(`/api/projects/${projectId}/nodes/${node.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ collapsed: shouldCollapse }),
      });
    }
  }
  await loadProject();
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

// Every validation rule explained in the same shape: what it is, why it matters, and how to
// fix it, plus which severity bucket it belongs in for the Critical/Warnings/Suggestions
// grouping below. Critical = actual structural breakage; Warnings = quality problems that
// aren't broken but make the tree harder to work with; Suggestions = soft style nits.
const VALIDATION_CATEGORY_INFO = {
  "Duplicate labels": {
    severity: "critical",
    tooltip:
      "Two or more nodes share the exact same label. Why it matters: duplicate names make it ambiguous which node is being referenced anywhere else in the app (search, references, exports). How to improve: rename one of them so every label is unique.",
  },
  "Circular references": {
    severity: "critical",
    tooltip:
      "A chain of reference links loops back on itself. Why it matters: circular dependencies usually signal a real design problem and make it unclear which component actually owns what. How to improve: break the cycle by removing or redirecting one of the reference links in the Inspector's References tab.",
  },
  "Orphaned nodes": {
    severity: "critical",
    tooltip:
      "This node is not reachable from the root by following parent/child links. Why it matters: this usually means data corruption from a bug or a manual JSON edit, not a normal design choice. How to improve: reparent it under the correct part of the tree via drag-to-reattach or the context menu.",
  },
  "Broken references": {
    severity: "critical",
    tooltip:
      "A reference link points to a node that no longer exists. Why it matters: stale references clutter the dependency graph with dead links that go nowhere. How to improve: delete the reference from the Inspector's References tab.",
  },
  "Large modules (>10 children)": {
    severity: "warning",
    tooltip:
      "This node has more than 10 direct children. Why it matters: modules this wide are hard to scan and usually mean several unrelated concerns got flattened into one place. How to improve: group related children into a named group (right-click a child > Add Group), or split into sub-levels.",
  },
  "Missing owners": {
    severity: "warning",
    tooltip:
      "This node has no owner assigned. Why it matters: without an owner it's unclear who is responsible for planning or maintaining this part of the system. How to improve: assign an owner in the Properties tab.",
  },
  "Single-child nodes": {
    severity: "suggestion",
    tooltip:
      "This node has exactly one child. Why it matters: a level that never branches often doesn't need to be its own level, adding depth without adding real structure. How to improve: consider merging it with its child, or add more children if more detail genuinely belongs here.",
  },
  "Missing notes": {
    severity: "suggestion",
    tooltip:
      "This node has no description or notes. Why it matters: undocumented nodes are the first thing to become confusing as the architecture grows. How to improve: add a short description in the Documentation tab.",
  },
};

function validationIssueRow(label, issues) {
  const row = document.createElement("div");
  row.className = "validation-row" + (issues.length > 0 ? " flagged clickable" : "");
  const info = VALIDATION_CATEGORY_INFO[label];
  const l = document.createElement("span");
  l.textContent = label;
  const v = document.createElement("strong");
  v.textContent = issues.length;
  row.appendChild(l);
  row.appendChild(v);
  const baseTooltip = info ? info.tooltip : "";
  row.title = issues.length > 0 ? `${baseTooltip} Click to expand and jump to affected nodes.` : baseTooltip;
  if (issues.length > 0) {
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

function renderSeverityGroup(title, entries) {
  const totalCount = entries.reduce((sum, [, issues]) => sum + issues.length, 0);
  const header = document.createElement("div");
  header.className = "severity-group-header severity-" + title.toLowerCase().replace(/\s+/g, "-");
  header.textContent = `${title} (${totalCount})`;
  validationSummaryEl.appendChild(header);
  for (const [label, issues] of entries) {
    validationIssueRow(label, issues);
  }
}

function renderValidationSummary(report) {
  validationSummaryEl.innerHTML = "";

  const categories = [
    ["Duplicate labels", report.duplicate_labels],
    ["Circular references", report.circular_references.map((chain) => ({ label: chain.join(" → ") }))],
    ["Orphaned nodes", report.orphan_nodes],
    ["Broken references", report.broken_references.map((msg) => ({ label: msg }))],
    ["Large modules (>10 children)", report.large_modules],
    ["Missing owners", report.missing_owners],
    ["Single-child nodes", report.single_child_nodes],
    ["Missing notes", report.missing_notes],
  ];

  const buckets = { critical: [], warning: [], suggestion: [] };
  for (const entry of categories) {
    buckets[VALIDATION_CATEGORY_INFO[entry[0]].severity].push(entry);
  }

  renderSeverityGroup("Critical Issues", buckets.critical);
  renderSeverityGroup("Warnings", buckets.warning);
  renderSeverityGroup("Suggestions", buckets.suggestion);

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
  statusFilterMenu.hidden = true;
  collapseExpandMenu.hidden = true;
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
    if (trimmed && trimmed !== node.label) {
      pushUndoSnapshot("Rename node");
      await patchNode({ label: trimmed });
    }
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

function infoPlanningStatusValue(node) {
  const wrap = document.createElement("div");
  wrap.className = "info-value-with-dot";
  const swatch = document.createElement("span");
  swatch.className = "classification-swatch";
  const activeColor = PLANNING_STATUS_COLORS[node.planning_status];
  swatch.style.background = activeColor || "transparent";
  swatch.style.borderColor = activeColor || "var(--border)";
  swatch.textContent = PLANNING_STATUS_ICONS[node.planning_status] || "";
  const select = document.createElement("select");
  select.className = "info-select";
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "—";
  select.appendChild(noneOpt);
  for (const opt of PLANNING_STATUSES) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = `${PLANNING_STATUS_ICONS[opt]} ${opt}`;
    if (node.planning_status === opt) o.selected = true;
    select.appendChild(o);
  }
  select.addEventListener("change", () => patchNode({ planning_status: select.value }));
  wrap.appendChild(swatch);
  wrap.appendChild(select);
  return wrap;
}

function renderProgressSummary(nodeId) {
  const stats = progressCache.get(nodeId);
  const wrap = document.createElement("div");
  wrap.className = "progress-summary";
  if (!stats || stats.total === 0) {
    wrap.textContent = "No trackable children yet.";
    wrap.classList.add("inspector-empty-note");
    return wrap;
  }
  const line = document.createElement("div");
  line.className = "progress-summary-line";
  line.textContent = `${stats.completed} / ${stats.total} Complete — ${stats.percent}%`;
  const bar = document.createElement("div");
  bar.className = "progress-summary-bar";
  const fill = document.createElement("div");
  fill.className = "progress-summary-fill";
  fill.style.width = `${stats.percent}%`;
  bar.appendChild(fill);
  const breakdown = document.createElement("div");
  breakdown.className = "progress-summary-breakdown";
  const parts = [
    ["Completed", stats.completed],
    ["In Progress", stats.inProgress],
    ["Needs Review", stats.needsReview],
    ["Blocked", stats.blocked],
    ["Not Started", stats.notStarted],
  ];
  for (const [label, count] of parts) {
    if (count === 0) continue;
    const part = document.createElement("span");
    part.textContent = `${PLANNING_STATUS_ICONS[label]} ${label}: ${count}`;
    breakdown.appendChild(part);
  }
  wrap.appendChild(line);
  wrap.appendChild(bar);
  wrap.appendChild(breakdown);
  return wrap;
}

function renderOverviewTab(container, node) {
  const parentNode = node.parent_id ? project.nodes[node.parent_id] : null;
  const infoTable = document.createElement("div");
  infoTable.className = "info-table";
  infoTable.appendChild(infoRow("Parent", infoStaticValue(parentNode ? parentNode.label : "— (root)")));
  infoTable.appendChild(infoRow("Children", infoStaticValue(String(node.children.length))));
  infoTable.appendChild(infoRow("Level", infoStaticValue(String(node.level))));
  infoTable.appendChild(infoRow("Planning Status", infoPlanningStatusValue(node)));
  container.appendChild(infoTable);

  const progressField = field("Progress");
  progressField.appendChild(renderProgressSummary(node.id));
  container.appendChild(progressField);
  container.appendChild(document.createElement("hr")).className = "inspector-divider";

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
      pushUndoSnapshot("Indent");
      const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/indent`, { method: "POST" });
      if (!res.ok) {
        undoStack.pop();
        updateUndoRedoButtons();
        alert("Can't indent: no preceding sibling.");
      }
      await loadProject();
    })
  );
  btnRow.appendChild(
    mkBtn("⇤ Outdent", "Move this up one level", async () => {
      pushUndoSnapshot("Outdent");
      const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/outdent`, { method: "POST" });
      if (!res.ok) {
        undoStack.pop();
        updateUndoRedoButtons();
        alert("Can't outdent past the root.");
      }
      await loadProject();
    })
  );
  btnRow.appendChild(mkBtn("+ Child", "Add a child node", () => addChild(focusedNodeId)));
  btnRow.appendChild(mkBtn("+ Sibling", "Add a sibling node below", () => addSiblingBelow(focusedNodeId)));
  if (node.parent_id !== null) {
    btnRow.appendChild(
      mkBtn("↑ Move up", "Move earlier among its siblings", async () => {
        pushUndoSnapshot("Move sibling up");
        const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/move-sibling`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ direction: "up" }),
        });
        if (!res.ok) {
          undoStack.pop();
          updateUndoRedoButtons();
          alert("Already first among its siblings.");
        }
        await loadProject();
      })
    );
    btnRow.appendChild(
      mkBtn("↓ Move down", "Move later among its siblings", async () => {
        pushUndoSnapshot("Move sibling down");
        const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/move-sibling`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ direction: "down" }),
        });
        if (!res.ok) {
          undoStack.pop();
          updateUndoRedoButtons();
          alert("Already last among its siblings.");
        }
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
  swatch.textContent = CLASSIFICATION_ICONS[node.classification] || "";
  const select = document.createElement("select");
  select.className = "info-select";
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "—";
  select.appendChild(noneOpt);
  for (const opt of CLASSIFICATIONS) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = `${CLASSIFICATION_ICONS[opt]} ${opt}`;
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
