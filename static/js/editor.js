const params = new URLSearchParams(window.location.search);
const projectId = params.get("project");

const CLASSIFICATIONS = [
  "AI Agent", "Workflow", "Database", "API", "UI", "Decision", "Configuration",
  "Storage", "Queue", "Security", "Validation", "Service", "Monitoring", "Infrastructure",
  "Engine", "Pipeline", "Module", "Strategy",
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
  Engine: "#0d9488",
  Pipeline: "#059669",
  Module: "#92400e",
  Strategy: "#c026d3",
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
  Engine: "ENG",
  Pipeline: "PIPE",
  Module: "MOD",
  Strategy: "STR",
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
  Engine: "🎛",
  Pipeline: "🔀",
  Module: "🧩",
  Strategy: "🎯",
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

// A subtle, cycling tint per hierarchy level (NOT per node type — that's what
// classification color is for) so the Explorer and canvas communicate depth by more than
// indentation and the L-badge alone. Muted on purpose: this is structural context, not a
// primary signal, so it must never compete with classification color when one is set.
const LEVEL_TINT_COLORS = ["#2563eb", "#0891b2", "#16a34a", "#ca8a04", "#dc2626", "#ea580c"];
function levelTintColor(level) {
  return LEVEL_TINT_COLORS[(Math.max(1, level) - 1) % LEVEL_TINT_COLORS.length];
}

// A small icon per hierarchy level in the Outline, cycling alongside the tint colors above —
// distinct from classification icons (node TYPE) and the L-badge (level NUMBER); this one
// just gives depth a recognizable shape at a glance while scanning the tree.
const LEVEL_ICONS = ["◆", "▲", "●", "■", "▶", "◈"];

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
const workspaceSwitcherBtn = document.getElementById("workspaceSwitcherBtn");
const workspaceSwitcherMenu = document.getElementById("workspaceSwitcherMenu");
const domainFilterBtn = document.getElementById("domainFilterBtn");
const domainFilterMenu = document.getElementById("domainFilterMenu");
const kanbanPane = document.getElementById("kanbanPane");
const kanbanBoard = document.getElementById("kanbanBoard");
const timelinePane = document.getElementById("timelinePane");
const timelineBoard = document.getElementById("timelineBoard");
const documentationPane = document.getElementById("documentationPane");
const documentationBoard = document.getElementById("documentationBoard");
const dependenciesPane = document.getElementById("dependenciesPane");
const dependenciesBoard = document.getElementById("dependenciesBoard");
const showDepsCheckbox = document.getElementById("showDepsCheckbox");
const showGridCheckbox = document.getElementById("showGridCheckbox");
const snapGridCheckbox = document.getElementById("snapGridCheckbox");
const animateFlowCheckbox = document.getElementById("animateFlowCheckbox");
const layoutMenuBtn = document.getElementById("layoutMenuBtn");
const layoutMenu = document.getElementById("layoutMenu");
const settingsMenuBtn = document.getElementById("settingsMenuBtn");
const settingsMenu = document.getElementById("settingsMenu");
const emptyCanvasPrompt = document.getElementById("emptyCanvasPrompt");
const emptyCanvasBtn = document.getElementById("emptyCanvasBtn");
const connectCoachMark = document.getElementById("connectCoachMark");
const connectCoachMarkDismiss = document.getElementById("connectCoachMarkDismiss");
const paneCoachMark = document.getElementById("paneCoachMark");
const paneCoachMarkDismiss = document.getElementById("paneCoachMarkDismiss");
const toolRail = document.getElementById("toolRail");
const toolSelectBtn = document.getElementById("toolSelectBtn");
const toolPanBtn = document.getElementById("toolPanBtn");
const shapesRailBtn = document.getElementById("shapesRailBtn");
const shapesFlyout = document.getElementById("shapesFlyout");
const railAutoArrangeBtn = document.getElementById("railAutoArrangeBtn");
const clusterZoomInBtn = document.getElementById("clusterZoomInBtn");
const clusterZoomOutBtn = document.getElementById("clusterZoomOutBtn");
const collapseAllBtn = document.getElementById("collapseAllBtn");
const expandBranchBtn = document.getElementById("expandBranchBtn");
const expandToLevelBtn = document.getElementById("expandToLevelBtn");
const undoBtn = document.getElementById("undoBtn");
const redoBtn = document.getElementById("redoBtn");
const refModeBanner = document.getElementById("refModeBanner");
const zoomLevelEl = document.getElementById("zoomLevel");
const cullIndicatorEl = document.getElementById("cullIndicator");
const fitSelectionBtn = document.getElementById("fitSelectionBtn");
const fitBranchBtn = document.getElementById("fitBranchBtn");
const fitAllBtn = document.getElementById("fitAllBtn");
const selectionToolbar = document.getElementById("selectionToolbar");
const selectionCountEl = document.getElementById("selectionCount");
const selCollapseBtn = document.getElementById("selCollapseBtn");
const selExpandBtn = document.getElementById("selExpandBtn");
const selColorBtn = document.getElementById("selColorBtn");
const selConnectBtn = document.getElementById("selConnectBtn");
const selStatusBtn = document.getElementById("selStatusBtn");
const selStatusMenu = document.getElementById("selStatusMenu");
const selGroupBtn = document.getElementById("selGroupBtn");
const selUngroupBtn = document.getElementById("selUngroupBtn");
const selDuplicateBtn = document.getElementById("selDuplicateBtn");
const selAlignBtn = document.getElementById("selAlignBtn");
const selAlignMenu = document.getElementById("selAlignMenu");
const selDistributeBtn = document.getElementById("selDistributeBtn");
const selDistributeMenu = document.getElementById("selDistributeMenu");
const selDeleteBtn = document.getElementById("selDeleteBtn");
const selClearBtn = document.getElementById("selClearBtn");
const selMoreBtn = document.getElementById("selMoreBtn");
const selMoreMenu = document.getElementById("selMoreMenu");
const focusModeBtn = document.getElementById("focusModeBtn");
const fullArchModeBtn = document.getElementById("fullArchModeBtn");
const minimapSvg = document.getElementById("minimapSvg");
const presentEnterBtn = document.getElementById("presentEnterBtn");
const presentationBar = document.getElementById("presentationBar");
const presentPrevLevelBtn = document.getElementById("presentPrevLevelBtn");
const presentPrevNodeBtn = document.getElementById("presentPrevNodeBtn");
const presentNextNodeBtn = document.getElementById("presentNextNodeBtn");
const presentNextLevelBtn = document.getElementById("presentNextLevelBtn");
const presentBranchBtn = document.getElementById("presentBranchBtn");
const presentZoomTopicBtn = document.getElementById("presentZoomTopicBtn");
const presentStoryBtn = document.getElementById("presentStoryBtn");
const presentExitBtn = document.getElementById("presentExitBtn");
const outlinePane = document.getElementById("outlinePane");
const outlineCollapseBtn = document.getElementById("outlineCollapseBtn");
const inspectorPane = document.getElementById("inspectorPane");
const inspectorCollapseBtn = document.getElementById("inspectorCollapseBtn");
const healthFooterEl = document.getElementById("healthFooter");
const healthFooterChip = document.getElementById("healthFooterChip");
const healthFooterDotEl = document.getElementById("healthFooterDot");
const healthFooterChipScoreEl = document.getElementById("healthFooterChipScore");
const healthFooterChevronEl = document.getElementById("healthFooterChevron");
const healthFooterGaugeEl = document.getElementById("healthFooterGauge");
const healthFooterSummaryEl = document.getElementById("healthFooterSummary");
const healthFooterRecentEl = document.getElementById("healthFooterRecent");
const healthPane = document.getElementById("healthPane");
const reasoningPane = document.getElementById("reasoningPane");
const reasoningBoard = document.getElementById("reasoningBoard");
const shortcutsBtn = document.getElementById("shortcutsBtn");
const shortcutsModal = document.getElementById("shortcutsModal");
const shortcutsCloseBtn = document.getElementById("shortcutsCloseBtn");
const shortcutsListEl = document.getElementById("shortcutsList");
const healthScoreEl = document.getElementById("healthScore");
const viewFullReportBtn = document.getElementById("viewFullReportBtn");
const validationSummaryEl = document.getElementById("validationSummary");
const runValidationBtn = document.getElementById("runValidationBtn");
const activityListEl = document.getElementById("activityList");
const importOutlineBtn = document.getElementById("importOutlineBtn");
const importModal = document.getElementById("importModal");
const importText = document.getElementById("importText");
const importCancelBtn = document.getElementById("importCancelBtn");
const clearCanvasBtn = document.getElementById("clearCanvasBtn");
const clearCanvasModal = document.getElementById("clearCanvasModal");
const clearCanvasSummary = document.getElementById("clearCanvasSummary");
const clearCanvasInput = document.getElementById("clearCanvasInput");
const clearCanvasXBtn = document.getElementById("clearCanvasXBtn");
const clearCanvasCancelBtn = document.getElementById("clearCanvasCancelBtn");
const clearCanvasConfirmBtn = document.getElementById("clearCanvasConfirmBtn");
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
// On by default, same reasoning as animateDataFlow — a connection you just drew should be
// visible immediately, not hidden behind a Settings toggle nobody knows to flip.
let showDependencies = true;
let expandedGroupOverflow = false; // "show all" for progressive disclosure of many ungrouped children
let lastValidationReport = null;
let viewMode = "focus"; // "focus" | "full"
let activeStatusFilters = new Set(PLANNING_STATUSES);
// Domain-scoping toggle within the Canvas family (Phase 9 section 2, WP11's Workspace
// Framework) -- unlike activeStatusFilters above, this one is deliberately persisted
// (workspace-state.js), matching the theme/pane-collapse precedent rather than the
// per-session status-filter one, since a domain lens is more like a standing preference.
let activeDomainFilter = getCurrentDomainFilter();
domainFilterBtn.textContent = `Domain: ${activeDomainFilter} ▾`;
domainFilterBtn.classList.toggle("active", activeDomainFilter !== "Hierarchy");
let nodeDragJustHappened = false; // suppresses the click-to-select that follows a drag's mouseup

// Nodes with no planning_status set are never filtered out — only nodes that HAVE an
// explicit status get faded when their status is unchecked, so freshly-added nodes never
// mysteriously vanish from view.
function nodeMatchesStatusFilter(node) {
  if (!node.planning_status) return true;
  return activeStatusFilters.has(node.planning_status);
}

// Same "unclassified is never hidden" policy as the status filter above -- a domain lens
// narrows focus, it never makes freshly-added or not-yet-classified nodes disappear.
function nodeMatchesDomainFilter(node) {
  if (activeDomainFilter === "Hierarchy") return true;
  if (!node.classification) return true;
  return node.classification === activeDomainFilter;
}

function nodeMatchesActiveFilters(node) {
  return nodeMatchesStatusFilter(node) && nodeMatchesDomainFilter(node);
}

// ---------- Multi-selection ----------
// Independent of focusedNodeId (which drives the Inspector/breadcrumb/camera): this is a
// lightweight set of node ids the user has multi-selected on the canvas, for bulk actions.
let selectedNodeIds = new Set();

function selectOnly(nodeId) {
  selectedNodeIds = new Set([nodeId]);
  updateSelectionToolbar();
  maybeShowConnectCoachMark();
}

// One-time coach mark pointing out the connection handles, shown the first time a node
// is selected on any project. Dismissed permanently once the user clicks "Got it".
const CONNECT_COACH_MARK_KEY = "skaido_seen_connect_coach_mark";

function maybeShowConnectCoachMark() {
  if (localStorage.getItem(CONNECT_COACH_MARK_KEY)) return;
  connectCoachMark.hidden = false;
}

connectCoachMarkDismiss.addEventListener("click", () => {
  localStorage.setItem(CONNECT_COACH_MARK_KEY, "1");
  connectCoachMark.hidden = true;
});

function toggleNodeSelection(nodeId) {
  if (selectedNodeIds.has(nodeId)) selectedNodeIds.delete(nodeId);
  else selectedNodeIds.add(nodeId);
  updateSelectionToolbar();
  renderCanvas();
}

function clearSelection() {
  selectedNodeIds = new Set();
  selectedConceptObjectIds = new Set();
  updateSelectionToolbar();
}

function updateSelectionToolbar() {
  const count = selectedNodeIds.size;
  selectionToolbar.hidden = count === 0;
  if (count > 0) {
    selectionCountEl.textContent = `${count} selected`;
  }
  // Genuinely hidden, not just disabled, when inapplicable -- Connect only makes sense for
  // exactly one selected node, it's not a "temporarily blocked" action for any other count.
  selConnectBtn.hidden = count !== 1;
  selConnectBtn.title = "Draw a relationship from this node to another — click the target node next";
  // Align/Distribute write canvas_x/canvas_y, which only Focus Mode reads — in Full
  // Architecture the layout is always recomputed live, so an edit there would have no
  // lasting visible effect.
  const canAlign = count >= 2 && viewMode !== "full";
  selAlignBtn.disabled = !canAlign;
  selDistributeBtn.disabled = !canAlign;
  selAlignBtn.title =
    viewMode === "full" ? "Switch to Focus Mode to align nodes" : canAlign ? "Align selected nodes" : "Select 2+ nodes to align";
  selDistributeBtn.title =
    viewMode === "full"
      ? "Switch to Focus Mode to distribute nodes"
      : canAlign
        ? "Distribute selected nodes evenly"
        : "Select 2+ nodes to distribute";
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
  if (res.status === 404) {
    projectNameEl.textContent = "Project not found";
    return;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    projectNameEl.textContent = "Couldn't load this project";
    alert(err.detail || "This project couldn't be loaded (a server error occurred). Your data has not been deleted.");
    return;
  }
  project = await res.json();
  rootId = Object.values(project.nodes).find((n) => n.parent_id === null).id;
  projectNameEl.textContent = project.name;
  if (!focusedNodeId) focusedNodeId = rootId;
  render();
}

// Double-click to rename in place, same as nodes and outline rows — no more prompt() dialog.
projectNameEl.addEventListener("dblclick", () => {
  if (!project) return;
  const input = document.createElement("input");
  input.type = "text";
  input.className = "project-name-input";
  input.value = project.name;
  projectNameEl.replaceWith(input);
  input.focus();
  input.select();

  const commit = async (save) => {
    input.removeEventListener("blur", onBlur);
    const trimmed = input.value.trim();
    input.replaceWith(projectNameEl); // always restore the real element first
    if (save && trimmed && trimmed !== project.name) {
      await fetch(`/api/projects/${projectId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmed }),
      });
      await loadProject(); // updates projectNameEl.textContent now that it's back in the DOM
    }
  };
  const onBlur = () => commit(true);
  input.addEventListener("blur", onBlur);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      input.blur();
    } else if (e.key === "Escape") {
      e.preventDefault();
      commit(false);
    }
  });
});
projectNameEl.style.cursor = "text";
projectNameEl.title = "Double-click to rename project";

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
  refreshHealthPanel();
  updateEmptyCanvasPrompt();
  if (!kanbanPane.hidden) renderKanbanBoard();
  if (!timelinePane.hidden) renderTimelineBoard();
  if (!documentationPane.hidden) renderDocumentationBoard();
  if (!dependenciesPane.hidden) renderDependenciesBoard();
}

// Shown only on a genuinely empty project (just the root, nothing placed yet) — the
// permanent Insert button stays the single source of truth; this just makes it impossible
// to miss the first time, then disappears the moment anything exists and never comes back.
function updateEmptyCanvasPrompt() {
  const isEmpty =
    project && rootId && project.nodes[rootId].children.length === 0 && project.concept_objects.length === 0;
  emptyCanvasPrompt.hidden = !isEmpty;
}

// Serialized: focusNode does a PUT (expandAncestors) then a GET (loadProject), and is called
// from many places (clicks, keyboard nav, search, Presentation Mode's auto-play timer). If a
// second call started before the first finished, two overlapping saves for the same project
// could race — the backend's save is now atomic so that can no longer corrupt the file, but
// the calls would still stomp on each other's in-progress state, so a second call while one is
// already in flight is simply ignored rather than queued (nav is idempotent — being a beat
// late to the next click/tick is harmless; overlapping is not).
let focusNodeInFlight = false;

async function focusNode(nodeId) {
  if (focusNodeInFlight) return;
  focusNodeInFlight = true;
  try {
    focusedNodeId = nodeId;
    panOffsetX = 0;
    panOffsetY = 0;
    expandedGroupOverflow = false;
    zoomScale = 1;
    zoomLevelEl.textContent = "100%";
    await expandAncestors(nodeId);
    await loadProject();
    fitToView();
  } finally {
    focusNodeInFlight = false;
  }
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

// Classic box-drawing tree prefix (│  , ├── , └── ) so the Explorer reads as a real ASCII
// tree instead of just indentation — real last-child bookkeeping per ancestor level, not
// the flat per-level color rails tried previously, since the user asked for exactly this
// structure with a reference screenshot. Root gets no prefix at all.
function buildTreePrefix(nodeId) {
  const chain = [];
  let cur = project.nodes[nodeId];
  while (cur.parent_id) {
    chain.unshift(cur);
    cur = project.nodes[cur.parent_id];
  }
  let prefix = "";
  for (let i = 0; i < chain.length - 1; i++) {
    const entry = chain[i];
    const parent = project.nodes[entry.parent_id];
    const isLast = parent.children[parent.children.length - 1] === entry.id;
    prefix += isLast ? "    " : "│   ";
  }
  if (chain.length > 0) {
    const node = chain[chain.length - 1];
    const parent = project.nodes[node.parent_id];
    const isLast = parent.children[parent.children.length - 1] === node.id;
    prefix += isLast ? "└── " : "├── ";
  }
  return prefix;
}

function renderNode(nodeId) {
  const node = project.nodes[nodeId];
  const wrapper = document.createElement("div");

  const row = document.createElement("div");
  row.className = "outline-row" + (nodeId === focusedNodeId ? " focused" : "");
  row.dataset.id = nodeId;

  const prefix = document.createElement("span");
  prefix.className = "tree-prefix";
  prefix.textContent = buildTreePrefix(nodeId);
  row.appendChild(prefix);

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

  const levelDot = document.createElement("span");
  levelDot.className = "level-dot";
  levelDot.textContent = LEVEL_ICONS[(node.level - 1) % LEVEL_ICONS.length];
  levelDot.style.color = levelTintColor(node.level);

  const label = document.createElement("span");
  label.className = "label";
  const typeIcon = !node.is_group && node.classification ? `${CLASSIFICATION_ICONS[node.classification]} ` : "";
  label.textContent = node.is_group ? `▤ ${node.label}` : `${typeIcon}${node.label}`;
  label.addEventListener("dblclick", (e) => {
    e.stopPropagation();
    startRename(nodeId, row, label);
  });

  const levelBadge = document.createElement("span");
  levelBadge.className = "level-badge";
  levelBadge.textContent = `L${node.level}`;

  const actions = document.createElement("span");
  actions.className = "row-actions";

  const delBtn = document.createElement("button");
  delBtn.className = "row-btn delete-node";
  delBtn.textContent = "×";
  delBtn.title = "Delete";
  delBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    deleteNodeFlow(nodeId);
  });

  if (node.parent_id !== null) actions.appendChild(delBtn);

  row.appendChild(toggle);
  row.appendChild(levelDot);
  row.appendChild(label);
  row.appendChild(levelBadge);
  row.appendChild(actions);
  row.addEventListener("click", () => {
    focusNode(nodeId);
  });
  row.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    if (selectedNodeIds.size > 1 && selectedNodeIds.has(nodeId)) {
      openMultiSelectContextMenu(e.clientX, e.clientY);
    } else {
      openContextMenu(nodeId, e.clientX, e.clientY);
    }
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
  pushUndoSnapshot("Add Component");
  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: parentId, label: "New Component" }),
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
  pushUndoSnapshot("Add Parallel Component");
  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: node.parent_id, label: "New Component", insert_after: nodeId }),
  });
  const newNode = await res.json();
  await loadProject();
  focusedNodeId = newNode.id;
  render();
  focusAndRenameRow(newNode.id);
}

async function addSiblingAbove(nodeId) {
  const node = project.nodes[nodeId];
  if (node.parent_id === null) {
    return addChild(nodeId);
  }
  pushUndoSnapshot("Add Parallel Component");
  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: node.parent_id, label: "New Component", insert_before: nodeId }),
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

  if (!typingGlobal && selectedConceptObjectId && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "c") {
    const obj = project.concept_objects.find((o) => o.id === selectedConceptObjectId);
    if (obj) conceptClipboard = { ...obj };
    return;
  }
  if (!typingGlobal && conceptClipboard && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "v") {
    const svgRect = canvasSvg.getBoundingClientRect();
    await pasteConceptObject(svgRect.left + svgRect.width / 2, svgRect.top + svgRect.height / 2);
    return;
  }
  if (!typingGlobal && e.key === "Delete" && selectedConceptObjectId) {
    const objId = selectedConceptObjectId;
    pushUndoSnapshot("Delete");
    const res = await fetch(`/api/projects/${projectId}/concept-objects/${objId}`, { method: "DELETE" });
    if (res.ok) {
      selectedConceptObjectId = null;
      await loadProject();
    } else {
      undoStack.pop();
      updateUndoRedoButtons();
    }
    return;
  }

  if (e.key === "Escape" && refMode) {
    exitRefMode();
    return;
  }
  if (e.key === "Escape" && selectedEdgeKey) {
    selectedEdgeKey = null;
    closeConnectorPanel();
    renderCanvas();
    return;
  }
  if (e.key === "Escape" && selectedNodeIds.size > 0) {
    selectedNodeIds = new Set();
    updateSelectionToolbar();
    renderCanvas();
    return;
  }
  if (e.key === "Escape" && !importModal.hidden) {
    closeImportModal();
    return;
  }
  if (e.key === "Escape" && !shortcutsModal.hidden) {
    shortcutsModal.hidden = true;
    return;
  }
  if (e.key === "Escape" && !exportMenu.hidden) {
    exportMenu.hidden = true;
    return;
  }
  if (!focusedNodeId || editingNodeId) return;
  const activeTag = document.activeElement.tagName;
  if (activeTag === "INPUT" || activeTag === "TEXTAREA") return;

  const noModifiers = !e.ctrlKey && !e.metaKey && !e.altKey;
  const key = e.key.toLowerCase();
  if (noModifiers && key === "n") {
    e.preventDefault();
    insertNewArchitectureNode();
    return;
  } else if (noModifiers && key === "s") {
    e.preventDefault();
    createConceptObject("sticky-note");
    return;
  } else if (noModifiers && key === "t") {
    e.preventDefault();
    createConceptObject("text");
    return;
  } else if (noModifiers && key === "r") {
    e.preventDefault();
    createConceptObject("rectangle");
    return;
  }

  if (e.key === "Tab") {
    e.preventDefault();
    const endpoint = e.shiftKey ? "outdent" : "indent";
    pushUndoSnapshot(e.shiftKey ? "Move Up One Level" : "Move Under Selected");
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

function straightPath(from, to) {
  return `M ${from.x} ${from.y} L ${to.x} ${to.y}`;
}

// Every node's position is now its own stored canvas_x/canvas_y — real and persistent, the
// same absolute space Full Architecture always used, so a node dragged anywhere stays there
// regardless of which node is later focused. Focus Mode's job is purely a *filter*: which
// ancestors/children/faded-context siblings are shown at all — "focusing" a node is a camera
// move (see fitToView/fitToBounds), never a position recompute. Auto Arrange is how you get
// back to the tidy deterministic layout on demand.
function nodePos(node) {
  return { x: node.canvas_x, y: node.canvas_y };
}

// Soft-caps context siblings so an ancestor with hundreds of children doesn't blow out the
// layout — this is context, not the thing being worked on. Returns the capped list actually
// placed, so callers can group edges to exactly these nodes.
function placeContextSiblings(siblings, positions, fadedIds) {
  const capped = siblings.length > MAX_UNGROUPED_VISIBLE ? siblings.slice(0, MAX_UNGROUPED_VISIBLE) : siblings;
  for (const sib of capped) {
    positions.set(sib.id, nodePos(sib));
    fadedIds.add(sib.id);
  }
  return capped;
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
  const contextGroups = []; // {fromId, siblings: Node[]} — drawn via the same trunk+bus connector, dimmed

  positions.set(focus.id, nodePos(focus));

  // Every ancestor sits on the direct path (full opacity); every OTHER child of that
  // ancestor (i.e. its siblings at that level) renders faded alongside it, never omitted.
  ancestorChain.forEach((ancestor, i) => {
    positions.set(ancestor.id, nodePos(ancestor));
    const childOnPath = i === 0 ? focus.id : ancestorChain[i - 1].id;
    const siblings = ancestor.children.filter((id) => id !== childOnPath).map((id) => project.nodes[id]);
    const placed = placeContextSiblings(siblings, positions, fadedIds);
    if (placed.length > 0) contextGroups.push({ fromId: ancestor.id, siblings: placed });
  });

  if (parent) {
    const focusSiblings = parent.children.filter((id) => id !== focus.id).map((id) => project.nodes[id]);
    const placed = placeContextSiblings(focusSiblings, positions, fadedIds);
    if (placed.length > 0) contextGroups.push({ fromId: parent.id, siblings: placed });
  }

  visibleChildren.forEach((child) => {
    positions.set(child.id, nodePos(child));
  });

  let minX = focus.canvas_x - NODE_W / 2;
  let maxX = focus.canvas_x + NODE_W / 2;
  let minY = focus.canvas_y - NODE_H / 2;
  let maxY = focus.canvas_y + NODE_H / 2;
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
    contextGroups,
    bounds: { minX, maxX, minY, maxY },
  };
}

function renderCanvas() {
  hideNodeHoverTooltip();
  canvasSvg.innerHTML = "";
  canvasSvg.classList.toggle("ref-mode-active", refMode);
  canvasSvg.appendChild(buildRefArrowDefs());
  updateEmptyCanvasPrompt();
  if (!project || !focusedNodeId) {
    return;
  }

  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;

  if (viewMode === "full") {
    renderFullArchitectureCanvas(viewW, viewH);
  } else {
    renderFocusCanvas(viewW, viewH);
  }

  canvasSvg.onclick = (e) => {
    if (e.target !== canvasSvg) return;
    let changed = false;
    if (selectedEdgeKey) {
      selectedEdgeKey = null;
      closeConnectorPanel();
      changed = true;
    }
    if (selectedConceptObjectId) {
      selectedConceptObjectId = null;
      changed = true;
    }
    if (selectedConceptObjectIds.size > 0) {
      selectedConceptObjectIds = new Set();
      changed = true;
    }
    if (selectedNodeIds.size > 0) {
      selectedNodeIds = new Set();
      updateSelectionToolbar();
      changed = true;
    }
    if (changed) renderCanvas();
  };

  smoothZoomNextRender = false;
}

function renderFocusCanvas(viewW, viewH) {
  const { focus, parent, ancestorChain, visibleChildren, hiddenCount, positions, fadedIds, contextGroups } =
    computeCanvasLayout(viewW, viewH);
  const visibleIds = new Set(positions.keys());

  const viewport = document.createElementNS(SVG_NS, "g");
  viewport.setAttribute("class", "viewport-group" + (smoothZoomNextRender ? " smooth" : ""));
  viewport.setAttribute(
    "transform",
    `translate(${viewW / 2 + panOffsetX} ${viewH / 2 + panOffsetY}) scale(${zoomScale}) translate(${-viewW / 2} ${-viewH / 2})`
  );
  const grid = buildGridBackground();
  if (grid) viewport.appendChild(grid);

  const edgesGroup = document.createElementNS(SVG_NS, "g");
  const refGroup = document.createElementNS(SVG_NS, "g");
  const nodesGroup = document.createElementNS(SVG_NS, "g");

  for (const group of contextGroups) {
    edgesGroup.appendChild(drawTreeBranches(positions.get(group.fromId), group.siblings, positions, true));
  }

  if (parent) {
    const parentPos = positions.get(parent.id);
    const focusPos = positions.get(focus.id);
    const parentEdgeGroup = document.createElementNS(SVG_NS, "g");
    parentEdgeGroup.setAttribute("class", "tree-edge-group");
    parentEdgeGroup.appendChild(drawTreeEdge(parentPos, focusPos, parent.id, focus.id));
    if (selectedEdgeKey === edgeKey("tree", focus.id)) {
      parentEdgeGroup.appendChild(drawTreeHandle(parentPos, focus.id, focusPos));
      parentEdgeGroup.appendChild(drawTreeHandle(focusPos, focus.id, parentPos));
    } else {
      parentEdgeGroup.appendChild(drawTreeHandle(focusPos, focus.id, parentPos, true));
    }
    edgesGroup.appendChild(parentEdgeGroup);
  }
  // Rest of the direct ancestor chain above the parent (grandparent, great-grandparent, ...)
  for (let i = 1; i < ancestorChain.length; i++) {
    const child = ancestorChain[i - 1];
    const ancestor = ancestorChain[i];
    const ancestorPos = positions.get(ancestor.id);
    const childPos = positions.get(child.id);
    const key = edgeKey("tree", child.id);
    const ancestorEdgeGroup = document.createElementNS(SVG_NS, "g");
    ancestorEdgeGroup.setAttribute("class", "tree-edge-group");
    ancestorEdgeGroup.appendChild(drawTreeEdge(ancestorPos, childPos, ancestor.id, child.id));
    if (selectedEdgeKey === key) {
      ancestorEdgeGroup.appendChild(drawTreeHandle(ancestorPos, child.id, childPos));
      ancestorEdgeGroup.appendChild(drawTreeHandle(childPos, child.id, ancestorPos));
    } else {
      ancestorEdgeGroup.appendChild(drawTreeHandle(childPos, child.id, ancestorPos, true));
    }
    edgesGroup.appendChild(ancestorEdgeGroup);
  }

  if (visibleChildren.length > 0) {
    edgesGroup.appendChild(drawTreeBranches(positions.get(focus.id), visibleChildren, positions));
  }

  if (showDependencies) {
    const tagCounters = new Map();
    // Free (concept) objects aren't scoped to Focus Mode's ancestor/children view — they
    // always render, so a reference touching one is always visible on that end.
    const endpointVisible = (id) => (project.nodes[id] ? visibleIds.has(id) : true);
    const endpointPos = (id) => (project.nodes[id] ? positions.get(id) : canvasObjectCenter(id));
    for (const ref of project.references) {
      if (ref.connector_hidden) continue;
      // Only draw references touching the focused node itself — otherwise a node with many
      // children each carrying their own unrelated reference links turns into a wall of lines.
      if (ref.from !== focus.id && ref.to !== focus.id) continue;
      const fromVisible = endpointVisible(ref.from);
      const toVisible = endpointVisible(ref.to);
      if (fromVisible && toVisible) {
        const fromPos = endpointPos(ref.from);
        const toPos = endpointPos(ref.to);
        if (!fromPos || !toPos) continue;
        refGroup.appendChild(drawRefEdge(fromPos, toPos, ref));
        if (selectedEdgeKey === edgeKey("ref", ref.id)) {
          refGroup.appendChild(drawRefHandle(fromPos, ref, "from"));
          refGroup.appendChild(drawRefHandle(toPos, ref, "to"));
        }
      } else if (fromVisible || toVisible) {
        const visibleId = fromVisible ? ref.from : ref.to;
        const otherId = fromVisible ? ref.to : ref.from;
        const otherPos = endpointPos(visibleId);
        if (!otherPos) continue;
        const index = tagCounters.get(visibleId) || 0;
        tagCounters.set(visibleId, index + 1);
        const arrow = fromVisible ? "→" : "←";
        refGroup.appendChild(
          drawRefTag(otherPos, `${arrow} ${canvasObjectLabel(otherId)}`, otherId, index, visibleId)
        );
      }
    }
  }

  for (const ancestor of ancestorChain) {
    nodesGroup.appendChild(drawNode(ancestor, positions.get(ancestor.id), !nodeMatchesActiveFilters(ancestor)));
  }
  for (const fadedId of fadedIds) {
    nodesGroup.appendChild(drawNode(project.nodes[fadedId], positions.get(fadedId), true));
  }
  nodesGroup.appendChild(drawNode(focus, positions.get(focus.id)));
  for (const child of visibleChildren) {
    nodesGroup.appendChild(drawNode(child, positions.get(child.id), !nodeMatchesActiveFilters(child)));
  }
  if (hiddenCount > 0) {
    const lastPos = positions.get(visibleChildren[visibleChildren.length - 1].id);
    nodesGroup.appendChild(drawShowMoreAffordance(lastPos.x + NODE_W + COL_GAP, lastPos.y, hiddenCount));
  }

  viewport.appendChild(edgesGroup);
  viewport.appendChild(refGroup);
  viewport.appendChild(nodesGroup);
  viewport.appendChild(buildFreeObjectsLayer());
  canvasSvg.appendChild(viewport);

  // Focus Mode is already inherently bounded (ancestor chain + immediate children +
  // context siblings, never the whole tree regardless of its size) -- viewport culling
  // (WP12) only ever applies in Full Architecture mode, so the indicator never applies here.
  updateCullIndicator(0);
  lastVisiblePositions = positions;
  lastViewW = viewW;
  lastViewH = viewH;
}

// Recursive subtree layout: every parent lays out its own children's subtrees packed
// tightly side by side, then centers itself over them. This is the core fix for "which
// child belongs to which parent" — a branch is always positioned within its actual parent's
// own span, never smeared across a shared row alongside unrelated nodes at the same depth,
// and the canvas only grows as wide as the real branching requires at each point, not as
// wide as the total node count anywhere in the whole tree (a flat one-row-per-level layout's
// failure mode: exponentially wide, and ownership only readable by cross-checking the
// Outline). Y still tracks depth (matching the L1/L2/L3 badges and breadcrumb everywhere
// else in the app) — only X packing changed, from "one shared row" to "recursive per-parent."
const SUBTREE_GAP = 40;

function computeSubtreeLayout(viewW) {
  const childrenByParent = new Map(); // parentId -> Node[] shown, drawn as one trunk+bus group
  const overflowByParent = new Map();
  const widths = new Map();
  const visited = new Set();

  function computeWidth(nodeId) {
    if (visited.has(nodeId)) return NODE_W;
    visited.add(nodeId);
    const node = project.nodes[nodeId];
    if (node.collapsed || node.children.length === 0) {
      widths.set(nodeId, NODE_W);
      return NODE_W;
    }
    const shown =
      node.children.length > MAX_UNGROUPED_VISIBLE ? node.children.slice(0, MAX_UNGROUPED_VISIBLE) : node.children;
    if (node.children.length > shown.length) overflowByParent.set(nodeId, node.children.length - shown.length);
    childrenByParent.set(nodeId, shown.map((id) => project.nodes[id]));
    let total = 0;
    for (const childId of shown) total += computeWidth(childId);
    total += Math.max(0, shown.length - 1) * SUBTREE_GAP;
    const width = Math.max(NODE_W, total);
    widths.set(nodeId, width);
    return width;
  }
  computeWidth(rootId);

  const positions = new Map();
  function assignPositions(nodeId, centerX, depth) {
    positions.set(nodeId, { x: centerX, y: 60 + depth * ROW_GAP });
    const children = childrenByParent.get(nodeId);
    if (!children) return;
    const totalWidth =
      children.reduce((sum, c) => sum + widths.get(c.id), 0) + Math.max(0, children.length - 1) * SUBTREE_GAP;
    let cursor = centerX - totalWidth / 2;
    for (const child of children) {
      const w = widths.get(child.id);
      assignPositions(child.id, cursor + w / 2, depth + 1);
      cursor += w + SUBTREE_GAP;
    }
  }
  assignPositions(rootId, viewW / 2, 0);

  return { positions, childrenByParent, overflowByParent };
}

// Full Architecture mode: every non-collapsed node in the project, recursively laid out by
// ownership (see computeSubtreeLayout above), nothing faded. This is the "show me everything
// at once" counterpart to Focus Mode's single-branch-plus-context view. Always recomputed
// live from the hierarchy — this view never reads or writes anyone's stored canvas position,
// so it can never drift into a scattered mess the way free-dragging can; Auto Arrange (below)
// persists this same layout to storage so Focus Mode, which DOES read stored position, shows
// a consistent picture once you step into any branch.
function computeFullArchitectureLayout(viewW, viewH) {
  const { positions, childrenByParent, overflowByParent } = computeSubtreeLayout(viewW);

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

  return { positions, childrenByParent, overflowByParent, bounds: { minX, maxX, minY, maxY } };
}

// Used only by Auto Arrange: persists computeSubtreeLayout's positions back to storage so
// Focus Mode (which reads stored canvas_x/canvas_y) shows the same tidy, ownership-clear
// arrangement Full Architecture always renders live.
function computeDeterministicFullLayout(viewW, viewH) {
  return computeSubtreeLayout(viewW).positions;
}

// Viewport culling (Phase 11 section 11, WP12) -- Full Architecture mode lays out every
// non-collapsed node in the project regardless of tree size (the mode's own long-standing
// design, unchanged here); on a genuinely large tree, creating a full drawNode() SVG
// element (box, text, icons, progress badge, hover handlers) for every one of them is what
// actually stops scaling gracefully past a few hundred nodes (Phase 1's finding), not the
// underlying layout computation itself (computeFullArchitectureLayout, untouched below --
// its positions/bounds still cover the whole tree, so Fit/Center and the minimap are
// unaffected). Trunk+bus branch lines and references stay unculled (cheap, and needed for
// visual continuity as the viewport pans); only the expensive per-node drawNode() call is
// skipped for positions that fall outside the current viewport.
function computeVisibleWorldBounds(viewW, viewH) {
  // Inverse of the exact transform string renderFullArchitectureCanvas applies below
  // (translate -> scale -> translate) -- screen point (sx, sy) maps back to world point:
  //   wx = (sx - viewW/2 - panOffsetX) / zoomScale + viewW/2
  // A margin of a full viewport's worth of world-space is deliberately generous: culling
  // should only ever skip things genuinely far outside view, never something borderline --
  // erring toward rendering slightly more than necessary is a far safer failure mode than
  // erring toward hiding something that should be visible, especially with no browser
  // available in this environment to visually confirm the transform math against.
  const toWorldX = (sx) => (sx - viewW / 2 - panOffsetX) / zoomScale + viewW / 2;
  const toWorldY = (sy) => (sy - viewH / 2 - panOffsetY) / zoomScale + viewH / 2;
  const marginX = viewW;
  const marginY = viewH;
  return {
    minX: toWorldX(0) - marginX,
    maxX: toWorldX(viewW) + marginX,
    minY: toWorldY(0) - marginY,
    maxY: toWorldY(viewH) + marginY,
  };
}

function isPositionWithinBounds(pos, bounds) {
  return (
    pos.x + NODE_W / 2 >= bounds.minX &&
    pos.x - NODE_W / 2 <= bounds.maxX &&
    pos.y + NODE_H / 2 >= bounds.minY &&
    pos.y - NODE_H / 2 <= bounds.maxY
  );
}

function updateCullIndicator(culledCount) {
  if (!cullIndicatorEl) return;
  cullIndicatorEl.hidden = culledCount === 0;
  if (culledCount > 0) {
    cullIndicatorEl.textContent = `⊙ ${culledCount} component${culledCount === 1 ? "" : "s"} off-screen`;
  }
}

function renderFullArchitectureCanvas(viewW, viewH) {
  const { positions, childrenByParent, overflowByParent, bounds } = computeFullArchitectureLayout(viewW, viewH);
  const visibleIds = new Set(positions.keys());

  const viewport = document.createElementNS(SVG_NS, "g");
  viewport.setAttribute("class", "viewport-group" + (smoothZoomNextRender ? " smooth" : ""));
  viewport.setAttribute(
    "transform",
    `translate(${viewW / 2 + panOffsetX} ${viewH / 2 + panOffsetY}) scale(${zoomScale}) translate(${-viewW / 2} ${-viewH / 2})`
  );
  const grid = buildGridBackground();
  if (grid) viewport.appendChild(grid);

  const edgesGroup = document.createElementNS(SVG_NS, "g");
  const refGroup = document.createElementNS(SVG_NS, "g");
  const nodesGroup = document.createElementNS(SVG_NS, "g");

  // Same trunk+bus distribution rail as Focus Mode, per parent — never a flat fan of
  // individual parent-child lines, at any level or node count.
  for (const [parentId, children] of childrenByParent.entries()) {
    const parentPos = positions.get(parentId);
    if (!parentPos) continue;
    edgesGroup.appendChild(drawTreeBranches(parentPos, children, positions));
  }

  if (showDependencies) {
    // Unlike Focus Mode, there's no single focused node to scope to — the whole tree is
    // already on screen, so every non-hidden reference draws (still tagged instead of drawn
    // full-length when one endpoint is inside a collapsed branch).
    const tagCounters = new Map();
    const endpointVisible = (id) => (project.nodes[id] ? visibleIds.has(id) : true);
    const endpointPos = (id) => (project.nodes[id] ? positions.get(id) : canvasObjectCenter(id));
    for (const ref of project.references) {
      if (ref.connector_hidden) continue;
      const fromVisible = endpointVisible(ref.from);
      const toVisible = endpointVisible(ref.to);
      if (fromVisible && toVisible) {
        const fromPos = endpointPos(ref.from);
        const toPos = endpointPos(ref.to);
        if (!fromPos || !toPos) continue;
        refGroup.appendChild(drawRefEdge(fromPos, toPos, ref));
        if (selectedEdgeKey === edgeKey("ref", ref.id)) {
          refGroup.appendChild(drawRefHandle(fromPos, ref, "from"));
          refGroup.appendChild(drawRefHandle(toPos, ref, "to"));
        }
      } else if (fromVisible || toVisible) {
        const visibleId = fromVisible ? ref.from : ref.to;
        const otherId = fromVisible ? ref.to : ref.from;
        const otherPos = endpointPos(visibleId);
        if (!otherPos) continue;
        const index = tagCounters.get(visibleId) || 0;
        tagCounters.set(visibleId, index + 1);
        const arrow = fromVisible ? "→" : "←";
        refGroup.appendChild(
          drawRefTag(otherPos, `${arrow} ${canvasObjectLabel(otherId)}`, otherId, index, visibleId)
        );
      }
    }
  }

  const cullBounds = computeVisibleWorldBounds(viewW, viewH);
  let culledCount = 0;
  for (const [nodeId, pos] of positions.entries()) {
    if (!isPositionWithinBounds(pos, cullBounds)) {
      culledCount++;
      continue;
    }
    const n = project.nodes[nodeId];
    nodesGroup.appendChild(drawNode(n, pos, !nodeMatchesActiveFilters(n)));
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
  viewport.appendChild(refGroup);
  viewport.appendChild(nodesGroup);
  viewport.appendChild(buildFreeObjectsLayer());
  canvasSvg.appendChild(viewport);

  updateCullIndicator(culledCount);
  lastVisiblePositions = positions;
  lastViewW = viewW;
  lastViewH = viewH;
}

// ---------- Free objects: sticky notes, shapes, etc. ----------
// One workspace: architecture nodes (structured, tree-connected) and free objects (sticky
// notes, shapes, etc. — not part of the hierarchy) render on the same canvas at all times.
// There is no mode toggle; "structured vs free" is a property of each object, not a
// workspace-wide switch.
let selectedConceptObjectId = null;
// Mirrors selectedNodeIds — Shift/Ctrl+click or lasso-select into this Set for bulk actions
// (group/ungroup/duplicate/delete/move-together) on free objects.
let selectedConceptObjectIds = new Set();
let conceptDragState = null;
let showConceptGrid = false;
let snapToConceptGrid = false;
const CONCEPT_GRID_SIZE = 20;

function toggleConceptObjectSelection(objId) {
  if (selectedConceptObjectIds.has(objId)) selectedConceptObjectIds.delete(objId);
  else selectedConceptObjectIds.add(objId);
  renderCanvas();
}

function snapConceptValue(v) {
  return snapToConceptGrid ? Math.round(v / CONCEPT_GRID_SIZE) * CONCEPT_GRID_SIZE : v;
}

const CONCEPT_DEFAULT_COLORS = {
  rectangle: "#475569",
  "rounded-rectangle": "#2563eb",
  circle: "#0891b2",
  diamond: "#f59e0b",
  hexagon: "#7c3aed",
  "sticky-note": "#fde68a",
  text: "#f1f5f9",
  arrow: "#64748b",
  divider: "#64748b",
  "section-header": "#f1f5f9",
  image: "#334155",
  icon: "#8b5cf6",
};

const INSERT_TYPES = [
  ["sticky-note", "🗒 Sticky Note"],
  ["rectangle", "▭ Rectangle"],
  ["rounded-rectangle", "▢ Rounded Rectangle"],
  ["circle", "◯ Circle"],
  ["diamond", "◇ Diamond"],
  ["hexagon", "⬡ Hexagon"],
  ["text", "A Text"],
  ["arrow", "➜ Arrow"],
  ["divider", "─ Divider"],
  ["section-header", "▬ Section Header"],
  ["image", "🖼 Image"],
  ["icon", "★ Icon"],
];

async function insertNewArchitectureNode() {
  const parentId = focusedNodeId || rootId;
  if (parentId) await addChild(parentId);
}

// The floating left tool rail (Mural-style icon rail) replaces the old text Insert dropdown.
// Node/Sticky Note/Text/Image are one-click rail buttons; Shapes is the one flyout, bundling
// the less-common object types (matches how Mural bundles its own shape picker behind one icon).
emptyCanvasBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  insertNewArchitectureNode();
});
toolRail.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-insert]");
  if (!btn) return;
  shapesFlyout.hidden = true;
  if (btn.dataset.insert === "node") {
    insertNewArchitectureNode();
  } else {
    createConceptObject(btn.dataset.insert);
  }
});
shapesRailBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  const wasHidden = shapesFlyout.hidden;
  exportMenu.hidden = true;
  layoutMenu.hidden = true;
  settingsMenu.hidden = true;
  shapesFlyout.hidden = !wasHidden;
});
document.addEventListener("click", (e) => {
  if (!shapesFlyout.hidden && !shapesRailBtn.contains(e.target) && !shapesFlyout.contains(e.target)) {
    shapesFlyout.hidden = true;
  }
});

async function createConceptObject(type) {
  pushUndoSnapshot("Add Content");
  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;
  const cx = snapConceptValue(viewW / 2 - panOffsetX / zoomScale);
  const cy = snapConceptValue(viewH / 2 - panOffsetY / zoomScale);
  const needsText = type === "text" || type === "sticky-note" || type === "icon" || type === "section-header";
  const res = await fetch(`/api/projects/${projectId}/concept-objects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      type,
      x: cx,
      y: cy,
      text: needsText ? (type === "icon" ? "★" : type === "section-header" ? "Section" : "Double-click to edit") : "",
    }),
  });
  const obj = await res.json();
  selectedConceptObjectId = obj.id;
  await loadProject();
}

async function pasteConceptObject(clientX, clientY) {
  if (!conceptClipboard) return;
  pushUndoSnapshot("Paste");
  const svgRect = canvasSvg.getBoundingClientRect();
  const viewW = svgRect.width || 800;
  const viewH = svgRect.height || 500;
  const cx = snapConceptValue(viewW / 2 + (clientX - svgRect.left - viewW / 2 - panOffsetX) / zoomScale);
  const cy = snapConceptValue(viewH / 2 + (clientY - svgRect.top - viewH / 2 - panOffsetY) / zoomScale);
  const res = await fetch(`/api/projects/${projectId}/concept-objects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      type: conceptClipboard.type,
      x: cx,
      y: cy,
      width: conceptClipboard.width,
      height: conceptClipboard.height,
      text: conceptClipboard.text,
      color: conceptClipboard.color,
    }),
  });
  const obj = await res.json();
  selectedConceptObjectId = obj.id;
  await loadProject();
}

// Shared by both Focus and Full Architecture rendering: the grid backdrop (opt-in, mainly
// useful while Unlock Layout / free objects are being positioned) and the free-objects layer
// itself, drawn above the node/edge layers so annotations sit on top of the architecture.
function buildGridBackground() {
  if (!showConceptGrid) return null;
  const g = document.createElementNS(SVG_NS, "g");
  const defs = document.createElementNS(SVG_NS, "defs");
  const pattern = document.createElementNS(SVG_NS, "pattern");
  pattern.setAttribute("id", "conceptGrid");
  pattern.setAttribute("width", CONCEPT_GRID_SIZE);
  pattern.setAttribute("height", CONCEPT_GRID_SIZE);
  pattern.setAttribute("patternUnits", "userSpaceOnUse");
  const dot = document.createElementNS(SVG_NS, "circle");
  dot.setAttribute("cx", 1);
  dot.setAttribute("cy", 1);
  dot.setAttribute("r", 1);
  dot.setAttribute("class", "concept-grid-dot");
  pattern.appendChild(dot);
  defs.appendChild(pattern);
  g.appendChild(defs);

  const bg = document.createElementNS(SVG_NS, "rect");
  bg.setAttribute("x", -5000);
  bg.setAttribute("y", -5000);
  bg.setAttribute("width", 10000);
  bg.setAttribute("height", 10000);
  bg.setAttribute("fill", "url(#conceptGrid)");
  bg.style.pointerEvents = "none";
  g.appendChild(bg);
  return g;
}

function buildFreeObjectsLayer() {
  const objectsGroup = document.createElementNS(SVG_NS, "g");
  objectsGroup.setAttribute("class", "free-objects-layer");
  const sorted = [...project.concept_objects].sort((a, b) => a.z_index - b.z_index);
  for (const obj of sorted) {
    objectsGroup.appendChild(drawConceptObject(obj));
  }
  return objectsGroup;
}

function drawConceptObject(obj) {
  const group = document.createElementNS(SVG_NS, "g");
  group.setAttribute(
    "class",
    "concept-object" +
      (selectedConceptObjectId === obj.id ? " selected" : "") +
      (selectedConceptObjectIds.has(obj.id) ? " multi-selected" : "") +
      (obj.locked ? " locked" : "")
  );
  group.dataset.id = obj.id;

  const color = obj.color || CONCEPT_DEFAULT_COLORS[obj.type] || "#64748b";
  let shape;

  if (obj.type === "circle") {
    shape = document.createElementNS(SVG_NS, "ellipse");
    shape.setAttribute("cx", obj.x + obj.width / 2);
    shape.setAttribute("cy", obj.y + obj.height / 2);
    shape.setAttribute("rx", obj.width / 2);
    shape.setAttribute("ry", obj.height / 2);
    shape.setAttribute("fill", "var(--surface)");
    shape.setAttribute("stroke", color);
  } else if (obj.type === "diamond") {
    const cx = obj.x + obj.width / 2;
    const cy = obj.y + obj.height / 2;
    shape = document.createElementNS(SVG_NS, "polygon");
    shape.setAttribute(
      "points",
      `${cx},${obj.y} ${obj.x + obj.width},${cy} ${cx},${obj.y + obj.height} ${obj.x},${cy}`
    );
    shape.setAttribute("fill", "var(--surface)");
    shape.setAttribute("stroke", color);
  } else if (obj.type === "hexagon") {
    const inset = obj.width * 0.25;
    shape = document.createElementNS(SVG_NS, "polygon");
    shape.setAttribute(
      "points",
      [
        `${obj.x + inset},${obj.y}`,
        `${obj.x + obj.width - inset},${obj.y}`,
        `${obj.x + obj.width},${obj.y + obj.height / 2}`,
        `${obj.x + obj.width - inset},${obj.y + obj.height}`,
        `${obj.x + inset},${obj.y + obj.height}`,
        `${obj.x},${obj.y + obj.height / 2}`,
      ].join(" ")
    );
    shape.setAttribute("fill", "var(--surface)");
    shape.setAttribute("stroke", color);
  } else if (obj.type === "divider") {
    shape = document.createElementNS(SVG_NS, "line");
    shape.setAttribute("x1", obj.x);
    shape.setAttribute("y1", obj.y);
    shape.setAttribute("x2", obj.x + obj.width);
    shape.setAttribute("y2", obj.y);
    shape.setAttribute("stroke", color);
  } else if (obj.type === "arrow") {
    shape = document.createElementNS(SVG_NS, "line");
    shape.setAttribute("x1", obj.x);
    shape.setAttribute("y1", obj.y);
    shape.setAttribute("x2", obj.x + obj.width);
    shape.setAttribute("y2", obj.y);
    shape.setAttribute("stroke", color);
    shape.setAttribute("marker-end", "url(#refArrow)");
  } else if (obj.type === "text" || obj.type === "icon" || obj.type === "section-header") {
    shape = document.createElementNS(SVG_NS, "rect");
    shape.setAttribute("x", obj.x);
    shape.setAttribute("y", obj.y);
    shape.setAttribute("width", obj.width);
    shape.setAttribute("height", obj.height);
    shape.setAttribute("fill", "transparent");
    shape.style.stroke = "none";
  } else if (obj.type === "image") {
    const isUrl = /^(https?:|data:)/.test(obj.text || "");
    if (isUrl) {
      shape = document.createElementNS(SVG_NS, "image");
      shape.setAttribute("x", obj.x);
      shape.setAttribute("y", obj.y);
      shape.setAttribute("width", obj.width);
      shape.setAttribute("height", obj.height);
      shape.setAttribute("preserveAspectRatio", "xMidYMid slice");
      shape.setAttributeNS("http://www.w3.org/1999/xlink", "href", obj.text);
    } else {
      shape = document.createElementNS(SVG_NS, "rect");
      shape.setAttribute("x", obj.x);
      shape.setAttribute("y", obj.y);
      shape.setAttribute("width", obj.width);
      shape.setAttribute("height", obj.height);
      shape.setAttribute("rx", 6);
      shape.setAttribute("fill", "var(--surface-2)");
      shape.setAttribute("stroke", color);
      shape.style.strokeDasharray = "5 4";
    }
  } else {
    shape = document.createElementNS(SVG_NS, "rect");
    shape.setAttribute("x", obj.x);
    shape.setAttribute("y", obj.y);
    shape.setAttribute("width", obj.width);
    shape.setAttribute("height", obj.height);
    shape.setAttribute("rx", obj.type === "rounded-rectangle" ? 14 : obj.type === "sticky-note" ? 4 : 0);
    shape.setAttribute("fill", obj.type === "sticky-note" ? color : "var(--surface)");
    shape.setAttribute("stroke", obj.type === "sticky-note" ? "transparent" : color);
  }
  shape.setAttribute("class", "concept-shape");
  if (obj.type !== "text" && obj.type !== "icon" && obj.type !== "image") {
    shape.style.strokeWidth = obj.border_style === "none" ? 0 : 2;
    if (obj.border_style === "dashed") shape.style.strokeDasharray = "6 4";
  }
  group.appendChild(shape);

  if (obj.text && obj.type !== "divider" && obj.type !== "arrow" && obj.type !== "image") {
    const textEl = document.createElementNS(SVG_NS, "text");
    textEl.setAttribute(
      "class",
      "concept-object-text" +
        (obj.type === "icon" ? " concept-icon-text" : "") +
        (obj.type === "section-header" ? " concept-section-header-text" : "")
    );
    textEl.setAttribute("x", obj.type === "section-header" ? obj.x + 6 : obj.x + obj.width / 2);
    textEl.setAttribute("y", obj.y + obj.height / 2);
    const displayText = obj.text.length > 60 ? obj.text.slice(0, 59) + "…" : obj.text;
    textEl.textContent = displayText;
    if (obj.type === "sticky-note") textEl.style.fill = "#1f2937";
    group.appendChild(textEl);
  } else if (obj.type === "image" && !/^(https?:|data:)/.test(obj.text || "")) {
    const placeholderText = document.createElementNS(SVG_NS, "text");
    placeholderText.setAttribute("class", "concept-object-text concept-icon-text");
    placeholderText.setAttribute("x", obj.x + obj.width / 2);
    placeholderText.setAttribute("y", obj.y + obj.height / 2);
    placeholderText.textContent = "🖼 Double-click to set image URL";
    group.appendChild(placeholderText);
  }

  if (selectedConceptObjectId === obj.id && !obj.locked) {
    const handle = document.createElementNS(SVG_NS, "rect");
    handle.setAttribute("class", "concept-resize-handle");
    handle.setAttribute("x", obj.x + obj.width - 6);
    handle.setAttribute("y", obj.y + obj.height - 6);
    handle.setAttribute("width", 12);
    handle.setAttribute("height", 12);
    handle.addEventListener("mousedown", (e) => {
      e.stopPropagation();
      startConceptDrag(e, obj.id, "resize");
    });
    group.appendChild(handle);
  }

  if (obj.locked) {
    const lockBadge = document.createElementNS(SVG_NS, "text");
    lockBadge.setAttribute("class", "concept-lock-badge");
    lockBadge.setAttribute("x", obj.x + obj.width - 10);
    lockBadge.setAttribute("y", obj.y + 10);
    lockBadge.textContent = "🔒";
    group.appendChild(lockBadge);
  }

  // Free objects get the same connection handles as architecture nodes — shapes, sticky
  // notes, images, etc. can all start a relationship, not just nodes. Revealed on hover or
  // selection (see CSS), not gated to selection-only, so hovering any object shows them.
  if (!obj.locked && obj.type !== "divider" && obj.type !== "arrow") {
    const cx = obj.x + obj.width / 2;
    const cy = obj.y + obj.height / 2;
    const handleSpecs = [
      { x: cx, y: obj.y },
      { x: cx, y: obj.y + obj.height },
      { x: obj.x, y: cy },
      { x: obj.x + obj.width, y: cy },
    ];
    for (const hp of handleSpecs) {
      const onHandleDown = (e) => {
        e.preventDefault();
        e.stopPropagation();
        startRelationshipDrag(e, obj.id, hp);
      };
      const hit = document.createElementNS(SVG_NS, "circle");
      hit.setAttribute("class", "node-connection-handle-hit");
      hit.setAttribute("cx", hp.x);
      hit.setAttribute("cy", hp.y);
      hit.setAttribute("r", 12);
      hit.addEventListener("mousedown", onHandleDown);
      group.appendChild(hit);

      const handle = document.createElementNS(SVG_NS, "circle");
      handle.setAttribute("class", "node-connection-handle");
      handle.setAttribute("cx", hp.x);
      handle.setAttribute("cy", hp.y);
      handle.setAttribute("r", 6);
      group.appendChild(handle);
    }
  }

  group.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    if (refMode) {
      e.preventDefault();
      handleRefModeClick(obj.id);
      return;
    }
    if (e.shiftKey || e.ctrlKey || e.metaKey) {
      toggleConceptObjectSelection(obj.id);
      return;
    }
    selectedConceptObjectId = obj.id;
    if (!selectedConceptObjectIds.has(obj.id)) selectedConceptObjectIds = new Set([obj.id]);
    startConceptDrag(e, obj.id, "move");
    renderCanvas();
  });
  group.addEventListener("dblclick", (e) => {
    e.stopPropagation();
    startConceptTextEdit(obj.id);
  });
  group.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (selectedConceptObjectIds.size > 1 && selectedConceptObjectIds.has(obj.id)) {
      openConceptMultiSelectContextMenu(e.clientX, e.clientY);
      return;
    }
    selectedConceptObjectId = obj.id;
    openConceptObjectContextMenu(obj.id, e.clientX, e.clientY);
  });

  return group;
}

function startConceptDrag(e, objId, mode) {
  const obj = project.concept_objects.find((o) => o.id === objId);
  if (!obj || obj.locked) return;
  // Move Together: dragging any selected object when 2+ are selected moves the whole group,
  // preserving their relative positions — same idea as startNodeFreeDrag. Resize always
  // stays single-object.
  const groupIds =
    mode === "move" && selectedConceptObjectIds.has(objId) && selectedConceptObjectIds.size > 1
      ? [...selectedConceptObjectIds]
      : [objId];
  pushUndoSnapshot(mode === "resize" ? "Resize" : groupIds.length > 1 ? "Move selection" : "Move");
  const startPositions = groupIds
    .map((id) => project.concept_objects.find((o) => o.id === id))
    .filter((o) => o && !o.locked)
    .map((o) => ({ id: o.id, obj: o, startX: o.x, startY: o.y }));
  conceptDragState = {
    id: objId,
    startClientX: e.clientX,
    startClientY: e.clientY,
    startX: obj.x,
    startY: obj.y,
    startW: obj.width,
    startH: obj.height,
  };

  const onMove = (moveEvent) => {
    if (!conceptDragState) return;
    const dx = (moveEvent.clientX - conceptDragState.startClientX) / zoomScale;
    const dy = (moveEvent.clientY - conceptDragState.startClientY) / zoomScale;
    if (mode === "move") {
      for (const p of startPositions) {
        p.obj.x = snapConceptValue(p.startX + dx);
        p.obj.y = snapConceptValue(p.startY + dy);
      }
    } else {
      const liveObj = project.concept_objects.find((o) => o.id === conceptDragState.id);
      if (!liveObj) return;
      liveObj.width = snapConceptValue(Math.max(30, conceptDragState.startW + dx));
      liveObj.height = snapConceptValue(Math.max(20, conceptDragState.startH + dy));
    }
    renderCanvas();
  };
  const onUp = async () => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    const dragState = conceptDragState;
    conceptDragState = null;
    if (!dragState) return;
    if (mode === "move") {
      const moved = startPositions.some((p) => p.obj.x !== p.startX || p.obj.y !== p.startY);
      if (!moved) {
        undoStack.pop();
        updateUndoRedoButtons();
        return;
      }
      for (const p of startPositions) {
        await fetch(`/api/projects/${projectId}/concept-objects/${p.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ x: p.obj.x, y: p.obj.y }),
        });
      }
      return;
    }
    const liveObj = project.concept_objects.find((o) => o.id === objId);
    if (!liveObj) return;
    const unchanged = liveObj.width === dragState.startW && liveObj.height === dragState.startH;
    if (unchanged) {
      undoStack.pop();
      updateUndoRedoButtons();
      return;
    }
    await fetch(`/api/projects/${projectId}/concept-objects/${objId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ width: liveObj.width, height: liveObj.height }),
    });
  };
  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

function startConceptTextEdit(objId) {
  const obj = project.concept_objects.find((o) => o.id === objId);
  if (!obj) return;
  const svgRect = canvasSvg.getBoundingClientRect();
  const localX = lastViewW / 2 + panOffsetX + zoomScale * (obj.x - lastViewW / 2);
  const localY = lastViewH / 2 + panOffsetY + zoomScale * (obj.y - lastViewH / 2);

  const textarea = document.createElement("textarea");
  textarea.className = "concept-text-edit-overlay";
  textarea.value = obj.text || "";
  textarea.style.left = `${svgRect.left + localX}px`;
  textarea.style.top = `${svgRect.top + localY}px`;
  textarea.style.width = `${Math.max(60, obj.width * zoomScale)}px`;
  textarea.style.height = `${Math.max(24, obj.height * zoomScale)}px`;
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();

  const commit = async () => {
    textarea.removeEventListener("blur", commit);
    if (textarea.parentNode) textarea.remove();
    if (textarea.value !== obj.text) {
      pushUndoSnapshot("Edit Text");
      await fetch(`/api/projects/${projectId}/concept-objects/${objId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: textarea.value }),
      });
      await loadProject();
    }
  };
  textarea.addEventListener("blur", commit);
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      textarea.removeEventListener("blur", commit);
      textarea.remove();
    } else if (e.key === "Enter" && !e.shiftKey && obj.type !== "sticky-note" && obj.type !== "text") {
      e.preventDefault();
      textarea.blur();
    }
  });
}

function openConceptObjectContextMenu(objId, clientX, clientY) {
  closeContextMenu();
  const obj = project.concept_objects.find((o) => o.id === objId);
  if (!obj) return;

  const menu = document.createElement("div");
  menu.className = "context-menu";

  menu.appendChild(
    contextMenuItem("🎨 Change Color", () => {
      const colorInput = document.createElement("input");
      colorInput.type = "color";
      colorInput.value = obj.color || CONCEPT_DEFAULT_COLORS[obj.type] || "#64748b";
      colorInput.style.position = "fixed";
      colorInput.style.left = "-9999px";
      document.body.appendChild(colorInput);
      colorInput.addEventListener("change", async () => {
        pushUndoSnapshot("Change Color");
        await fetch(`/api/projects/${projectId}/concept-objects/${objId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ color: colorInput.value }),
        });
        colorInput.remove();
        await loadProject();
      });
      colorInput.click();
    })
  );
  menu.appendChild(
    contextMenuSubmenu("▭ Border Style", ["Solid", "Dashed", "None"], async (opt) => {
      pushUndoSnapshot("Change Border Style");
      await fetch(`/api/projects/${projectId}/concept-objects/${objId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ border_style: opt.toLowerCase() }),
      });
      await loadProject();
    })
  );
  menu.appendChild(
    contextMenuItem("✎ Edit Text", () => startConceptTextEdit(objId))
  );
  menu.appendChild(
    contextMenuItem("⇢ Connect", () => {
      refMode = true;
      pendingRefFrom = objId;
      refModeBanner.hidden = false;
      renderCanvas();
    })
  );
  menu.appendChild(
    contextMenuItem("⧉ Duplicate", async () => {
      pushUndoSnapshot("Duplicate");
      const res = await fetch(`/api/projects/${projectId}/concept-objects/${objId}/duplicate`, { method: "POST" });
      const newObj = await res.json();
      selectedConceptObjectId = newObj.id;
      await loadProject();
    })
  );
  menu.appendChild(
    contextMenuItem("⎘ Copy", () => {
      conceptClipboard = { ...obj };
    })
  );
  menu.appendChild(
    contextMenuItem(obj.locked ? "🔓 Unlock" : "🔒 Lock", async () => {
      pushUndoSnapshot(obj.locked ? "Unlock" : "Lock");
      await fetch(`/api/projects/${projectId}/concept-objects/${objId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ locked: !obj.locked }),
      });
      await loadProject();
    })
  );

  menu.appendChild(contextMenuSeparator());

  menu.appendChild(
    contextMenuSubmenu("▤ Organize", ["Bring to Front", "Send to Back"], async (opt) => {
      pushUndoSnapshot(opt);
      const endpoint = opt === "Bring to Front" ? "bring-to-front" : "send-to-back";
      await fetch(`/api/projects/${projectId}/concept-objects/${objId}/${endpoint}`, { method: "POST" });
      await loadProject();
    })
  );

  menu.appendChild(contextMenuSeparator());

  menu.appendChild(
    contextMenuItem("→ Convert to Architecture Component", async () => {
      pushUndoSnapshot("Convert to Architecture Component");
      const parentId = (project.nodes[focusedNodeId] && focusedNodeId) || rootId;
      const res = await fetch(`/api/projects/${projectId}/concept-objects/${objId}/convert-to-node`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parent_id: parentId }),
      });
      const node = await res.json();
      await loadProject();
      focusNode(node.id);
    })
  );

  menu.appendChild(
    contextMenuItem(
      "🗑 Delete",
      async () => {
        pushUndoSnapshot("Delete");
        const res = await fetch(`/api/projects/${projectId}/concept-objects/${objId}`, { method: "DELETE" });
        if (!res.ok) {
          undoStack.pop();
          updateUndoRedoButtons();
          const err = await res.json().catch(() => ({}));
          alert(err.detail || "Couldn't delete this object.");
          return;
        }
        if (selectedConceptObjectId === objId) selectedConceptObjectId = null;
        await loadProject();
      },
      { danger: true, disabled: obj.locked }
    )
  );

  menu.style.left = `${clientX}px`;
  menu.style.top = `${clientY}px`;
  document.body.appendChild(menu);
  openContextMenuEl = menu;

  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) menu.style.left = `${Math.max(4, window.innerWidth - rect.width - 4)}px`;
  if (rect.bottom > window.innerHeight) menu.style.top = `${Math.max(4, window.innerHeight - rect.height - 4)}px`;
}

// ---------- Free-object bulk selection actions ----------
// Mirrors the node multi-select actions (openMultiSelectContextMenu / groupSelectedNodes /
// etc.) but "group" here just tags a shared group_id rather than reparenting under a new
// node — free objects have no hierarchy to nest into.

async function groupSelectedConceptObjects() {
  const ids = [...selectedConceptObjectIds];
  if (ids.length < 2) {
    alert("Select at least two objects to group them.");
    return;
  }
  pushUndoSnapshot("Group objects");
  const groupId = ids[0]; // reuse the first selected object's own id as the shared group id
  for (const id of ids) {
    await fetch(`/api/projects/${projectId}/concept-objects/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ group_id: groupId }),
    });
  }
  await loadProject();
}

async function ungroupSelectedConceptObjects() {
  const ids = [...selectedConceptObjectIds].filter((id) => {
    const obj = project.concept_objects.find((o) => o.id === id);
    return obj && obj.group_id;
  });
  if (ids.length === 0) {
    alert("None of the selected objects are grouped.");
    return;
  }
  pushUndoSnapshot("Ungroup objects");
  for (const id of ids) {
    await fetch(`/api/projects/${projectId}/concept-objects/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ group_id: "" }),
    });
  }
  await loadProject();
}

async function duplicateSelectedConceptObjects() {
  const ids = [...selectedConceptObjectIds];
  pushUndoSnapshot("Duplicate selected");
  let lastObj = null;
  for (const id of ids) {
    const res = await fetch(`/api/projects/${projectId}/concept-objects/${id}/duplicate`, { method: "POST" });
    lastObj = await res.json();
  }
  clearSelection();
  await loadProject();
  if (lastObj) selectedConceptObjectId = lastObj.id;
}

async function deleteSelectedConceptObjects() {
  const ids = [...selectedConceptObjectIds].filter((id) => {
    const obj = project.concept_objects.find((o) => o.id === id);
    return obj && !obj.locked;
  });
  if (ids.length === 0) {
    alert("The selected objects are locked.");
    return;
  }
  const confirmed = confirm(`Delete ${ids.length} selected object${ids.length === 1 ? "" : "s"}?`);
  if (!confirmed) return;
  pushUndoSnapshot("Delete selected");
  for (const id of ids) {
    await fetch(`/api/projects/${projectId}/concept-objects/${id}`, { method: "DELETE" });
  }
  clearSelection();
  await loadProject();
}

function openConceptMultiSelectContextMenu(clientX, clientY) {
  closeContextMenu();
  const count = selectedConceptObjectIds.size;
  const menu = document.createElement("div");
  menu.className = "context-menu";

  menu.appendChild(contextMenuItem(`${count} selected`, () => {}, { disabled: true }));
  menu.appendChild(contextMenuSeparator());
  menu.appendChild(contextMenuItem("▤ Group", groupSelectedConceptObjects));
  menu.appendChild(contextMenuItem("Ungroup", ungroupSelectedConceptObjects));
  menu.appendChild(contextMenuItem("⧉ Duplicate", duplicateSelectedConceptObjects));
  menu.appendChild(contextMenuSeparator());
  menu.appendChild(contextMenuItem("🗑 Delete", deleteSelectedConceptObjects, { danger: true }));
  menu.appendChild(
    contextMenuItem("Clear Selection", () => {
      clearSelection();
      renderCanvas();
    })
  );

  menu.style.left = `${clientX}px`;
  menu.style.top = `${clientY}px`;
  document.body.appendChild(menu);
  openContextMenuEl = menu;

  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) menu.style.left = `${Math.max(4, window.innerWidth - rect.width - 4)}px`;
  if (rect.bottom > window.innerHeight) menu.style.top = `${Math.max(4, window.innerHeight - rect.height - 4)}px`;
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

// Connectors are not exclusive to architecture nodes — a reference's from/to id may belong
// to a node OR a free (concept) object. These two helpers resolve either kind uniformly so
// rendering/labeling code doesn't need to know which one it's looking at.
function canvasObjectLabel(id) {
  const node = project.nodes[id];
  if (node) return node.label;
  const obj = project.concept_objects.find((o) => o.id === id);
  if (obj) return obj.text || obj.type;
  return "?";
}

function canvasObjectCenter(id) {
  if (lastVisiblePositions.has(id)) return lastVisiblePositions.get(id);
  const obj = project.concept_objects.find((o) => o.id === id);
  if (obj) return { x: obj.x + obj.width / 2, y: obj.y + obj.height / 2 };
  return null;
}

function drawTreeBranches(focusPos, children, positions, faded = false) {
  const group = document.createElementNS(SVG_NS, "g");
  if (children.length === 0) return group;
  const edgeClass = "edge" + (faded ? " faded-edge" : "");

  if (children.length === 1) {
    group.setAttribute("class", "tree-edge-group");
    const childPos = positions.get(children[0].id);
    group.appendChild(drawTreeEdge(focusPos, childPos, null, children[0].id, faded));
    const key = edgeKey("tree", children[0].id);
    if (selectedEdgeKey === key) {
      group.appendChild(drawTreeHandle(focusPos, children[0].id, childPos));
      group.appendChild(drawTreeHandle(childPos, children[0].id, focusPos));
    } else if (!faded) {
      // Always-present but subtle (opacity 0 until hover) so dragging a connection to
      // reparent it is discoverable without needing to select the edge first.
      group.appendChild(drawTreeHandle(childPos, children[0].id, focusPos, true));
    }
    return group;
  }

  // Classic org-chart connector: one trunk from the parent down to a shared horizontal
  // bus, then one short branch per child — much clearer than N lines fanning from a
  // single point once there are more than a couple of children. Children are always laid
  // out in a single deterministic row, so the bus always lines up cleanly. This is the ONLY
  // hierarchy connector strategy used anywhere in the app — Full Architecture mode and faded
  // ancestor-context rows reuse this same function rather than falling back to one edge per
  // parent-child pair, so no level of the tree ever reverts to a fan of individual lines.
  const childPositions = children.map((c) => positions.get(c.id));
  const busY = focusPos.y + (childPositions[0].y - focusPos.y) / 2;
  const xs = childPositions.map((p) => p.x);
  const minX = Math.min(...xs, focusPos.x);
  const maxX = Math.max(...xs, focusPos.x);

  const trunk = document.createElementNS(SVG_NS, "path");
  trunk.setAttribute("class", edgeClass);
  const trunkD = `M ${focusPos.x} ${focusPos.y} L ${focusPos.x} ${busY}`;
  trunk.setAttribute("d", trunkD);
  group.appendChild(trunk);
  if (animateDataFlow && !faded) group.appendChild(drawFlowParticle(trunkD, "var(--accent)"));

  const bus = document.createElementNS(SVG_NS, "line");
  bus.setAttribute("class", edgeClass);
  bus.setAttribute("x1", minX);
  bus.setAttribute("y1", busY);
  bus.setAttribute("x2", maxX);
  bus.setAttribute("y2", busY);
  group.appendChild(bus);

  children.forEach((child, i) => {
    const childPos = childPositions[i];
    const key = edgeKey("tree", child.id);

    const branchGroup = document.createElementNS(SVG_NS, "g");
    branchGroup.setAttribute("class", "tree-edge-group");
    const hit = document.createElementNS(SVG_NS, "path");
    hit.setAttribute("class", "edge-hit");
    hit.setAttribute("d", `M ${childPos.x} ${busY} L ${childPos.x} ${childPos.y}`);
    const branch = document.createElementNS(SVG_NS, "path");
    const branchD = `M ${childPos.x} ${busY} L ${childPos.x} ${childPos.y}`;
    branch.setAttribute("class", edgeClass + (selectedEdgeKey === key ? " selected" : ""));
    branch.setAttribute("d", branchD);
    branchGroup.dataset.toId = child.id;
    branchGroup.dataset.x1 = childPos.x;
    branchGroup.dataset.y1 = busY;
    branchGroup.dataset.x2 = childPos.x;
    branchGroup.dataset.y2 = childPos.y;
    branchGroup.appendChild(hit);
    branchGroup.appendChild(branch);
    if (animateDataFlow && !faded) branchGroup.appendChild(drawFlowParticle(branchD, "var(--accent)"));
    if (!faded && selectedEdgeKey !== key) {
      branchGroup.appendChild(drawTreeHandle(childPos, child.id, { x: childPos.x, y: busY }, true));
    }
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

  // Hierarchy edges are always straight lines (never curved) — same "tree diagram" straight-
  // line convention as the multi-child trunk+bus connector, so Auto Arrange and free dragging
  // both produce a consistent look. Reference edges keep their own separate curve/straight
  // per-connector choice (drawRefEdge) — unrelated to this.
  const hit = document.createElementNS(SVG_NS, "path");
  hit.setAttribute("class", "edge-hit");
  hit.setAttribute("d", straightPath(from, to));

  const line = document.createElementNS(SVG_NS, "path");
  line.setAttribute(
    "class",
    "edge" + (faded ? " faded-edge" : "") + (key && selectedEdgeKey === key ? " selected" : "")
  );
  line.setAttribute("d", straightPath(from, to));
  if (fromId) group.dataset.fromId = fromId;
  if (toId) group.dataset.toId = toId;
  group.dataset.x1 = from.x;
  group.dataset.y1 = from.y;
  group.dataset.x2 = to.x;
  group.dataset.y2 = to.y;

  group.appendChild(hit);
  group.appendChild(line);
  if (animateDataFlow && !faded) {
    group.appendChild(drawFlowParticle(straightPath(from, to), "var(--accent)"));
  }
  if (key) {
    group.addEventListener("click", (e) => {
      e.stopPropagation();
      selectedEdgeKey = selectedEdgeKey === key ? null : key;
      renderCanvas();
    });
  }
  return group;
}

function drawFlowParticle(pathD, color, speedSeconds) {
  const particle = document.createElementNS(SVG_NS, "circle");
  particle.setAttribute("class", "flow-particle");
  particle.setAttribute("r", 2.5);
  particle.style.fill = color;
  const anim = document.createElementNS(SVG_NS, "animateMotion");
  anim.setAttribute("dur", `${speedSeconds || 2.4}s`);
  anim.setAttribute("repeatCount", "indefinite");
  anim.setAttribute("path", pathD);
  particle.appendChild(anim);
  return particle;
}

function drawTreeHandle(pos, childId, fixedPos, subtle = false) {
  const circle = document.createElementNS(SVG_NS, "circle");
  circle.setAttribute("class", "ref-handle" + (subtle ? " tree-detach-handle" : ""));
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
      closeConnectorPanel();
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

const REF_TYPE_CLASS = {
  Dependency: "type-dependency",
  Warning: "type-warning",
  Broken: "type-broken",
  "Data Flow": "type-data-flow",
  Optional: "type-optional",
};
const REF_THICKNESS_WIDTH = { Thin: 1, Normal: 1.5, Thick: 2.5 };
const REF_LINE_DASH = { dashed: "6 4", dotted: "2 3" };

function drawRefEdge(from, to, ref) {
  const group = document.createElementNS(SVG_NS, "g");
  const key = edgeKey("ref", ref.id);

  const hitPath = document.createElementNS(SVG_NS, "path");
  const pathFn = ref.curve_style === "straight" ? straightPath : curvePath;
  hitPath.setAttribute("class", "edge-hit");
  hitPath.setAttribute("d", pathFn(from, to));

  const typeClass = REF_TYPE_CLASS[ref.reference_type] || "";
  const line = document.createElementNS(SVG_NS, "path");
  line.setAttribute(
    "class",
    "ref-edge" + (typeClass ? ` ${typeClass}` : "") + (selectedEdgeKey === key ? " selected" : "")
  );
  line.setAttribute("d", pathFn(from, to));
  line.style.strokeWidth = REF_THICKNESS_WIDTH[ref.thickness] || REF_THICKNESS_WIDTH.Normal;
  if (ref.custom_color) line.style.stroke = ref.custom_color;
  if (REF_LINE_DASH[ref.line_style]) line.style.strokeDasharray = REF_LINE_DASH[ref.line_style];
  if (typeof ref.opacity === "number") line.style.strokeOpacity = ref.opacity;
  const direction = ref.direction || "Forward";
  // #refArrow uses orient="auto-start-reverse", so the same marker definition flips
  // correctly whether it's attached as marker-start or marker-end.
  if (ref.show_arrowhead !== false) {
    if (direction === "Forward" || direction === "Both") line.setAttribute("marker-end", "url(#refArrow)");
    if (direction === "Backward" || direction === "Both") line.setAttribute("marker-start", "url(#refArrow)");
  }
  group.dataset.fromId = ref.from;
  group.dataset.toId = ref.to;
  group.dataset.x1 = from.x;
  group.dataset.y1 = from.y;
  group.dataset.x2 = to.x;
  group.dataset.y2 = to.y;

  group.appendChild(hitPath);
  group.appendChild(line);

  if (animateDataFlow || ref.animated) {
    // Hierarchy blue, Reference purple, Dependency amber, Data Flow emerald, Error red —
    // the animation should read as data actually flowing through the architecture.
    const particleColor =
      ref.custom_color ||
      (ref.reference_type === "Dependency"
        ? "#d97706"
        : ref.reference_type === "Warning"
        ? "var(--warning-text)"
        : ref.reference_type === "Broken"
        ? "var(--danger-text)"
        : ref.reference_type === "Data Flow"
        ? "#10b981"
        : "#a855f7");
    group.appendChild(drawFlowParticle(pathFn(from, to), particleColor, ref.animation_speed));
  }

  group.addEventListener("click", (e) => {
    e.stopPropagation();
    if (selectedEdgeKey === key) {
      selectedEdgeKey = null;
      closeConnectorPanel();
    } else {
      selectedEdgeKey = key;
      showConnectorPropertiesPanel(ref.id, e.clientX, e.clientY);
    }
    renderCanvas();
  });
  group.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    e.stopPropagation();
    selectedEdgeKey = key;
    showConnectorPropertiesPanel(ref.id, e.clientX, e.clientY);
    renderCanvas();
  });

  return group;
}

// ---------- Connector properties panel ----------
// Selecting a reference edge opens a small floating panel so connectors stop being passive
// graphics: type, description, color, direction, thickness, per-connector animation, and
// visibility are all editable right from the canvas, not buried in a modal elsewhere.
let connectorPanelEl = null;
let connectorPanelPos = null;

function closeConnectorPanel() {
  if (connectorPanelEl) {
    connectorPanelEl.remove();
    connectorPanelEl = null;
  }
  connectorPanelPos = null;
}

async function updateConnector(refId, payload) {
  await fetch(`/api/projects/${projectId}/references/${refId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadProject();
  if (connectorPanelPos && selectedEdgeKey === edgeKey("ref", refId)) {
    showConnectorPropertiesPanel(refId, connectorPanelPos.x, connectorPanelPos.y);
  }
}

function connectorPanelField(labelText, inputEl) {
  const row = document.createElement("div");
  row.className = "connector-panel-row";
  const l = document.createElement("label");
  l.textContent = labelText;
  row.appendChild(l);
  row.appendChild(inputEl);
  return row;
}

function showConnectorPropertiesPanel(refId, clientX, clientY) {
  closeConnectorPanel();
  const ref = project.references.find((r) => r.id === refId);
  if (!ref) return;
  connectorPanelPos = { x: clientX, y: clientY };

  const panel = document.createElement("div");
  panel.className = "connector-panel";

  const title = document.createElement("div");
  title.className = "connector-panel-title";
  const fromLabel = canvasObjectLabel(ref.from);
  const toLabel = canvasObjectLabel(ref.to);
  title.textContent = `${fromLabel} → ${toLabel}`;
  panel.appendChild(title);

  panel.appendChild(connectorPanelField("Source", infoStaticValue(fromLabel)));
  panel.appendChild(connectorPanelField("Destination", infoStaticValue(toLabel)));

  const typeSelect = document.createElement("select");
  for (const opt of ["", "Dependency", "Warning", "Broken", "Data Flow", "Optional"]) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt || "Reference";
    if ((ref.reference_type || "") === opt) o.selected = true;
    typeSelect.appendChild(o);
  }
  typeSelect.addEventListener("change", () => updateConnector(refId, { reference_type: typeSelect.value }));
  panel.appendChild(connectorPanelField("Type", typeSelect));

  const descInput = document.createElement("input");
  descInput.type = "text";
  descInput.className = "connector-panel-input";
  descInput.value = ref.label || "";
  descInput.placeholder = "Description";
  descInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") descInput.blur();
  });
  descInput.addEventListener("blur", () => {
    if (descInput.value !== (ref.label || "")) updateConnector(refId, { label: descInput.value });
  });
  panel.appendChild(connectorPanelField("Description", descInput));

  const colorWrap = document.createElement("div");
  colorWrap.className = "connector-panel-color-wrap";
  const colorInput = document.createElement("input");
  colorInput.type = "color";
  colorInput.className = "color-swatch-input";
  colorInput.value = ref.custom_color || "#64748b";
  colorInput.addEventListener("change", () => updateConnector(refId, { custom_color: colorInput.value }));
  colorWrap.appendChild(colorInput);
  if (ref.custom_color) {
    const resetBtn = document.createElement("button");
    resetBtn.className = "btn btn-small";
    resetBtn.textContent = "Reset";
    resetBtn.title = "Remove the color override and fall back to the relationship type color";
    resetBtn.addEventListener("click", () => updateConnector(refId, { custom_color: "" }));
    colorWrap.appendChild(resetBtn);
  }
  panel.appendChild(connectorPanelField("Color", colorWrap));

  const directionSelect = document.createElement("select");
  for (const opt of ["Forward", "Backward", "Both"]) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    if ((ref.direction || "Forward") === opt) o.selected = true;
    directionSelect.appendChild(o);
  }
  directionSelect.addEventListener("change", () => updateConnector(refId, { direction: directionSelect.value }));
  panel.appendChild(connectorPanelField("Direction", directionSelect));

  const thicknessSelect = document.createElement("select");
  for (const opt of ["Thin", "Normal", "Thick"]) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    if ((ref.thickness || "Normal") === opt) o.selected = true;
    thicknessSelect.appendChild(o);
  }
  thicknessSelect.addEventListener("change", () => updateConnector(refId, { thickness: thicknessSelect.value }));
  panel.appendChild(connectorPanelField("Thickness", thicknessSelect));

  const lineStyleSelect = document.createElement("select");
  for (const opt of ["solid", "dashed", "dotted"]) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt[0].toUpperCase() + opt.slice(1);
    if ((ref.line_style || "solid") === opt) o.selected = true;
    lineStyleSelect.appendChild(o);
  }
  lineStyleSelect.addEventListener("change", () => updateConnector(refId, { line_style: lineStyleSelect.value }));
  panel.appendChild(connectorPanelField("Line Style", lineStyleSelect));

  const curveSelect = document.createElement("select");
  for (const opt of ["curved", "straight"]) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt[0].toUpperCase() + opt.slice(1);
    if ((ref.curve_style || "curved") === opt) o.selected = true;
    curveSelect.appendChild(o);
  }
  curveSelect.addEventListener("change", () => updateConnector(refId, { curve_style: curveSelect.value }));
  panel.appendChild(connectorPanelField("Shape", curveSelect));

  const opacityInput = document.createElement("input");
  opacityInput.type = "range";
  opacityInput.min = "0.15";
  opacityInput.max = "1";
  opacityInput.step = "0.05";
  opacityInput.value = typeof ref.opacity === "number" ? ref.opacity : 1;
  opacityInput.addEventListener("change", () =>
    updateConnector(refId, { opacity: parseFloat(opacityInput.value) })
  );
  panel.appendChild(connectorPanelField("Opacity", opacityInput));

  const arrowheadLabel = document.createElement("label");
  arrowheadLabel.className = "connector-panel-checkbox-row";
  const arrowheadCheckbox = document.createElement("input");
  arrowheadCheckbox.type = "checkbox";
  arrowheadCheckbox.checked = ref.show_arrowhead !== false;
  arrowheadCheckbox.addEventListener("change", () =>
    updateConnector(refId, { show_arrowhead: arrowheadCheckbox.checked })
  );
  arrowheadLabel.appendChild(arrowheadCheckbox);
  arrowheadLabel.appendChild(document.createTextNode(" Show arrowhead"));
  panel.appendChild(arrowheadLabel);

  const animatedLabel = document.createElement("label");
  animatedLabel.className = "connector-panel-checkbox-row";
  const animatedCheckbox = document.createElement("input");
  animatedCheckbox.type = "checkbox";
  animatedCheckbox.checked = !!ref.animated;
  animatedCheckbox.addEventListener("change", () => updateConnector(refId, { animated: animatedCheckbox.checked }));
  animatedLabel.appendChild(animatedCheckbox);
  animatedLabel.appendChild(document.createTextNode(" Animate this connector"));
  panel.appendChild(animatedLabel);

  const speedInput = document.createElement("input");
  speedInput.type = "range";
  speedInput.min = "0.6";
  speedInput.max = "6";
  speedInput.step = "0.2";
  speedInput.value = ref.animation_speed || 2.4;
  speedInput.title = "Faster on the left, slower on the right";
  speedInput.addEventListener("change", () =>
    updateConnector(refId, { animation_speed: parseFloat(speedInput.value) })
  );
  panel.appendChild(connectorPanelField("Animation Speed", speedInput));

  const visibleLabel = document.createElement("label");
  visibleLabel.className = "connector-panel-checkbox-row";
  const visibleCheckbox = document.createElement("input");
  visibleCheckbox.type = "checkbox";
  visibleCheckbox.checked = !ref.connector_hidden;
  visibleCheckbox.addEventListener("change", () =>
    updateConnector(refId, { connector_hidden: !visibleCheckbox.checked })
  );
  visibleLabel.appendChild(visibleCheckbox);
  visibleLabel.appendChild(document.createTextNode(" Visible"));
  panel.appendChild(visibleLabel);

  const actionRow = document.createElement("div");
  actionRow.className = "btn-row connector-panel-actions";

  const reverseBtn = document.createElement("button");
  reverseBtn.className = "btn btn-small";
  reverseBtn.textContent = "⇄ Reverse Direction";
  reverseBtn.title = "Swap this connector's from/to endpoints";
  reverseBtn.addEventListener("click", async () => {
    pushUndoSnapshot("Reverse connector");
    await fetch(`/api/projects/${projectId}/references/${refId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from: ref.to, to: ref.from }),
    });
    selectedEdgeKey = null;
    closeConnectorPanel();
    await loadProject();
  });
  actionRow.appendChild(reverseBtn);

  const deleteBtn = document.createElement("button");
  deleteBtn.className = "btn btn-small btn-danger";
  deleteBtn.textContent = "🗑 Delete Connection";
  deleteBtn.addEventListener("click", async () => {
    pushUndoSnapshot("Delete connector");
    await fetch(`/api/projects/${projectId}/references/${refId}`, { method: "DELETE" });
    selectedEdgeKey = null;
    closeConnectorPanel();
    await loadProject();
  });
  actionRow.appendChild(deleteBtn);
  panel.appendChild(actionRow);

  const closeBtn = document.createElement("button");
  closeBtn.className = "btn btn-small connector-panel-close";
  closeBtn.textContent = "Close";
  closeBtn.addEventListener("click", () => {
    selectedEdgeKey = null;
    closeConnectorPanel();
    renderCanvas();
  });
  panel.appendChild(closeBtn);

  panel.style.left = `${clientX}px`;
  panel.style.top = `${clientY}px`;
  document.body.appendChild(panel);
  connectorPanelEl = panel;

  const rect = panel.getBoundingClientRect();
  if (rect.right > window.innerWidth) panel.style.left = `${Math.max(4, window.innerWidth - rect.width - 4)}px`;
  if (rect.bottom > window.innerHeight) panel.style.top = `${Math.max(4, window.innerHeight - rect.height - 4)}px`;
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

// Dragging a node's body always just moves it (position is always absolute and
// persistent — see Phase 1 of the fix plan). Reparenting happens exclusively via the
// connection-handle drag → chooser → "Hierarchy".
function startNodeFreeDrag(e, nodeId) {
  e.preventDefault();
  e.stopPropagation();
  // Move Together: dragging any selected node when 2+ are selected moves the whole group,
  // preserving their relative positions.
  const groupIds = selectedNodeIds.has(nodeId) && selectedNodeIds.size > 1 ? [...selectedNodeIds] : [nodeId];
  const startPositions = groupIds.map((id) => ({
    id,
    node: project.nodes[id],
    startX: project.nodes[id].canvas_x,
    startY: project.nodes[id].canvas_y,
  }));
  pushUndoSnapshot(groupIds.length > 1 ? "Move selection" : "Move node");
  const startClientX = e.clientX;
  const startClientY = e.clientY;
  let moved = false;

  const onMove = (moveEvent) => {
    const dx = (moveEvent.clientX - startClientX) / zoomScale;
    const dy = (moveEvent.clientY - startClientY) / zoomScale;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) moved = true;
    for (const p of startPositions) {
      p.node.canvas_x = p.startX + dx;
      p.node.canvas_y = p.startY + dy;
    }
    renderCanvas();
  };
  const onUp = async () => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    nodeDragJustHappened = true;
    setTimeout(() => (nodeDragJustHappened = false), 0);
    if (!moved) {
      undoStack.pop();
      updateUndoRedoButtons();
      return;
    }
    for (const p of startPositions) {
      await fetch(`/api/projects/${projectId}/nodes/${p.id}/position`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ canvas_x: p.node.canvas_x, canvas_y: p.node.canvas_y }),
      });
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
    if (project.nodes[targetId]) {
      focusNode(targetId);
    } else {
      selectedConceptObjectId = targetId;
      renderCanvas();
    }
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
  } else if (!node.is_group) {
    // No classification set: fall back to a subtle per-level tint so depth still reads
    // visually on the canvas, not just via the level badge — thinner than a real
    // classification stroke so it never competes with an actual category color.
    box.style.stroke = levelTintColor(node.level);
    box.style.strokeWidth = "1.5";
    box.style.strokeOpacity = "0.45";
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

  if (!node.is_group && typeof node.level === "number") {
    const levelBadge = document.createElementNS(SVG_NS, "text");
    levelBadge.setAttribute("class", "node-level-badge");
    levelBadge.setAttribute("x", pos.x - NODE_W / 2);
    levelBadge.setAttribute("y", pos.y - NODE_H / 2 - 6);
    levelBadge.textContent = `L${node.level}`;
    group.appendChild(levelBadge);
  }

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

  if (!node.is_group && node.locked) {
    const lockBadge = document.createElementNS(SVG_NS, "text");
    lockBadge.setAttribute("class", "node-lock-badge");
    lockBadge.setAttribute("x", pos.x + NODE_W / 2 - 12);
    lockBadge.setAttribute("y", pos.y - NODE_H / 2 + 12);
    lockBadge.textContent = "🔒";
    group.appendChild(lockBadge);
  }

  if (!node.is_group && (node.priority === "High" || node.priority === "Critical")) {
    const priBadge = document.createElementNS(SVG_NS, "circle");
    priBadge.setAttribute("class", "priority-dot");
    priBadge.setAttribute("cx", pos.x + NODE_W / 2 - 6);
    priBadge.setAttribute("cy", pos.y + NODE_H / 2 - 6);
    priBadge.setAttribute("r", 4);
    group.appendChild(priBadge);
  }

  if (!node.is_group && node.planning_status === "Completed") {
    const tick = document.createElementNS(SVG_NS, "g");
    tick.setAttribute("class", "completion-tick");
    const tickCircle = document.createElementNS(SVG_NS, "circle");
    tickCircle.setAttribute("cx", pos.x + NODE_W / 2 - 7);
    tickCircle.setAttribute("cy", pos.y - NODE_H / 2 + 7);
    tickCircle.setAttribute("r", 7);
    const tickMark = document.createElementNS(SVG_NS, "text");
    tickMark.setAttribute("class", "completion-tick-mark");
    tickMark.setAttribute("x", pos.x + NODE_W / 2 - 7);
    tickMark.setAttribute("y", pos.y - NODE_H / 2 + 7);
    tickMark.textContent = "✓";
    tick.appendChild(tickCircle);
    tick.appendChild(tickMark);
    group.appendChild(tick);
  } else if (!node.is_group && computeWarnings(node).length > 0) {
    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("class", "warning-dot");
    dot.setAttribute("cx", pos.x + NODE_W / 2 - 6);
    dot.setAttribute("cy", pos.y - NODE_H / 2 + 6);
    dot.setAttribute("r", 4);
    group.appendChild(dot);
  }

  if (!node.is_group && node.planning_status && node.planning_status !== "Completed") {
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
    if (nodeDragJustHappened) return;
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
    if (selectedNodeIds.size > 1 && selectedNodeIds.has(node.id)) {
      openMultiSelectContextMenu(e.clientX, e.clientY);
    } else {
      openContextMenu(node.id, e.clientX, e.clientY);
    }
  });

  // Free dragging only means anything in Focus Mode, which reads each node's stored
  // canvas_x/canvas_y. Full Architecture always recomputes the recursive layout live and
  // never reads stored position, so a drag there would just snap back on the next render —
  // dragging is disabled in that view rather than shipping a control that silently does
  // nothing lasting.
  if (!node.is_group && !node.locked && viewMode !== "full") {
    group.addEventListener("mousedown", (e) => {
      if (e.button !== 0 || refMode) return;
      startNodeFreeDrag(e, node.id);
    });
    group.style.cursor = "move";
  }

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
    startNodeCanvasRename(node.id, pos);
  });

  // Connection handles: one per edge, on every draggable node (revealed on hover or when
  // the node is focused — see CSS). Dragging from a handle creates a live connector and, on
  // drop, a relationship-type chooser — this replaces needing a modifier-key shortcut to draw
  // a Reference/Dependency/Data Flow link. A larger invisible hit-ring sits under each visible
  // dot so the drag reliably starts even when the click doesn't land pixel-perfect on it.
  if (!node.is_group && !faded && !node.locked) {
    const handleSpecs = [
      { x: pos.x, y: pos.y - NODE_H / 2 },
      { x: pos.x, y: pos.y + NODE_H / 2 },
      { x: pos.x - NODE_W / 2, y: pos.y },
      { x: pos.x + NODE_W / 2, y: pos.y },
    ];
    for (const hp of handleSpecs) {
      const onHandleDown = (e) => {
        e.preventDefault();
        e.stopPropagation();
        startRelationshipDrag(e, node.id, hp);
      };
      const hit = document.createElementNS(SVG_NS, "circle");
      hit.setAttribute("class", "node-connection-handle-hit");
      hit.setAttribute("cx", hp.x);
      hit.setAttribute("cy", hp.y);
      hit.setAttribute("r", 12);
      hit.addEventListener("mousedown", onHandleDown);
      group.appendChild(hit);

      const handle = document.createElementNS(SVG_NS, "circle");
      handle.setAttribute("class", "node-connection-handle");
      handle.setAttribute("cx", hp.x);
      handle.setAttribute("cy", hp.y);
      handle.setAttribute("r", 6);
      group.appendChild(handle);
    }
  }

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
  if (node.status) fields.appendChild(hoverField("Lifecycle Stage", node.status));
  if (node.planning_status) {
    fields.appendChild(hoverField("Completion Status", `${PLANNING_STATUS_ICONS[node.planning_status]} ${node.planning_status}`));
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

function openQuickPicker(options, clientX, clientY, onPick) {
  closeContextMenu();
  const menu = document.createElement("div");
  menu.className = "context-menu";
  for (const opt of options) {
    menu.appendChild(contextMenuItem(opt, () => onPick(opt)));
  }
  menu.style.left = `${clientX}px`;
  menu.style.top = `${clientY}px`;
  document.body.appendChild(menu);
  openContextMenuEl = menu;
  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) menu.style.left = `${Math.max(4, window.innerWidth - rect.width - 4)}px`;
  if (rect.bottom > window.innerHeight) menu.style.top = `${Math.max(4, window.innerHeight - rect.height - 4)}px`;
}

// ---------- Relationship drag (connection handles) ----------
// Dragging from a selected node's connection handle draws a live connector, highlights the
// node currently under the cursor, and on drop opens a small chooser so the relationship
// type is always a deliberate choice — never inferred from a modifier key the user has to
// remember, and never triggered by accident.
const RELATIONSHIP_TYPES = ["Hierarchy", "Reference", "Dependency", "Data Flow", "Optional", "Cancel"];

function startRelationshipDrag(e, fromId, originPos) {
  const rect = canvasSvg.getBoundingClientRect();
  const viewportEl = canvasSvg.querySelector(":scope > g");
  const tempLine = document.createElementNS(SVG_NS, "line");
  tempLine.setAttribute("class", "ref-edge relationship-drag-line");
  tempLine.setAttribute("x1", originPos.x);
  tempLine.setAttribute("y1", originPos.y);
  tempLine.setAttribute("x2", originPos.x);
  tempLine.setAttribute("y2", originPos.y);
  if (viewportEl) viewportEl.appendChild(tempLine);

  let hoveredTargetId = null;
  const targetSelector = (id) =>
    project.nodes[id]
      ? `.node-group[data-id="${id}"] .node-box`
      : `.concept-object[data-id="${id}"] .concept-shape`;
  const clearHighlight = () => {
    if (!hoveredTargetId) return;
    const el = canvasSvg.querySelector(targetSelector(hoveredTargetId));
    if (el) el.classList.remove("relationship-drop-target");
    hoveredTargetId = null;
  };

  const toPretransform = (clientX, clientY) => ({
    x: lastViewW / 2 + (clientX - rect.left - lastViewW / 2 - panOffsetX) / zoomScale,
    y: lastViewH / 2 + (clientY - rect.top - lastViewH / 2 - panOffsetY) / zoomScale,
  });

  const onMove = (moveEvent) => {
    const p = toPretransform(moveEvent.clientX, moveEvent.clientY);
    tempLine.setAttribute("x2", p.x);
    tempLine.setAttribute("y2", p.y);

    let targetId = null;
    for (const [nodeId, nodePos] of lastVisiblePositions.entries()) {
      if (nodeId === fromId) continue;
      if (Math.abs(p.x - nodePos.x) <= NODE_W / 2 && Math.abs(p.y - nodePos.y) <= NODE_H / 2) {
        targetId = nodeId;
        break;
      }
    }
    if (!targetId) {
      for (const obj of project.concept_objects) {
        if (obj.id === fromId) continue;
        if (p.x >= obj.x && p.x <= obj.x + obj.width && p.y >= obj.y && p.y <= obj.y + obj.height) {
          targetId = obj.id;
          break;
        }
      }
    }
    if (targetId !== hoveredTargetId) {
      clearHighlight();
      if (targetId) {
        const el = canvasSvg.querySelector(targetSelector(targetId));
        if (el) el.classList.add("relationship-drop-target");
        hoveredTargetId = targetId;
      }
    }
  };

  const onUp = async (upEvent) => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    tempLine.remove();
    clearHighlight();
    if (!hoveredTargetId) return;
    const targetId = hoveredTargetId;
    // Hierarchy (reparenting) only makes sense between two architecture nodes — free objects
    // aren't part of the tree, so that option is left out when either end is a free object.
    const bothNodes = !!project.nodes[fromId] && !!project.nodes[targetId];
    const types = bothNodes ? RELATIONSHIP_TYPES : RELATIONSHIP_TYPES.filter((t) => t !== "Hierarchy");
    openRelationshipChooser(upEvent.clientX, upEvent.clientY, types, async (type) => {
      if (type === "Cancel") return;
      if (type === "Hierarchy") {
        pushUndoSnapshot("Become Child");
        const res = await fetch(`/api/projects/${projectId}/nodes/${fromId}/reparent`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ new_parent_id: targetId }),
        });
        if (!res.ok) {
          undoStack.pop();
          updateUndoRedoButtons();
          const err = await res.json().catch(() => ({}));
          alert(err.detail || "Couldn't create that relationship.");
          return;
        }
        await loadProject();
        focusNode(fromId);
        return;
      }
      pushUndoSnapshot(`Create ${type}`);
      await fetch(`/api/projects/${projectId}/references`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from: fromId, to: targetId, reference_type: type === "Reference" ? null : type }),
      });
      await loadProject();
    });
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

function openRelationshipChooser(clientX, clientY, types, onPick) {
  closeContextMenu();
  const menu = document.createElement("div");
  menu.className = "context-menu";
  for (const type of types) {
    if (type === "Cancel") menu.appendChild(contextMenuSeparator());
    menu.appendChild(contextMenuItem(type, () => onPick(type), { danger: type === "Cancel" }));
  }
  menu.style.left = `${clientX}px`;
  menu.style.top = `${clientY}px`;
  document.body.appendChild(menu);
  openContextMenuEl = menu;

  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) menu.style.left = `${Math.max(4, window.innerWidth - rect.width - 4)}px`;
  if (rect.bottom > window.innerHeight) menu.style.top = `${Math.max(4, window.innerHeight - rect.height - 4)}px`;
}

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

// Same submenu shell as contextMenuSubmenu, but for pre-built menu-item elements (including
// nested submenus) rather than a flat list of string options — used for "▸ More".
function contextMenuElementSubmenu(text, items) {
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
  for (const item of items) submenu.appendChild(item);
  wrap.appendChild(submenu);
  return wrap;
}

function openContextMenu(nodeId, clientX, clientY) {
  closeContextMenu();
  const node = project.nodes[nodeId];
  const isRoot = node.parent_id === null;
  const locked = !!node.locked;
  const CLEAR = "— Clear —";

  const menu = document.createElement("div");
  menu.className = "context-menu";

  // Primary, always-visible actions — everything else lives under "More" so the menu stays
  // scannable. Nothing here is removed, just reorganized: every item below still exists.
  menu.appendChild(contextMenuItem("+ Add Child", () => addChild(nodeId), { disabled: locked }));
  menu.appendChild(
    contextMenuItem(
      "⛓ Decompose",
      () => {
        focusedNodeId = nodeId;
        inspectorActiveTab = "decompose";
        render();
      },
      { disabled: locked }
    )
  );
  menu.appendChild(
    contextMenuItem(
      "🧭 Blueprint",
      () => {
        focusedNodeId = nodeId;
        inspectorActiveTab = "blueprint";
        render();
      },
      { disabled: locked }
    )
  );
  menu.appendChild(
    contextMenuItem("+ Add Parallel", () => addSiblingBelow(nodeId), { disabled: isRoot || locked })
  );
  menu.appendChild(
    contextMenuItem("⇢ Connect", () => {
      refMode = true;
      pendingRefFrom = nodeId;
      refModeBanner.hidden = false;
      renderCanvas();
    })
  );
  menu.appendChild(
    contextMenuItem("⧉ Duplicate", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/duplicate`, { method: "POST" });
      const newNode = await res.json();
      await loadProject();
      focusNode(newNode.id);
    }, { disabled: isRoot || locked })
  );
  menu.appendChild(
    contextMenuItem("💬 Comment", () => {
      focusedNodeId = nodeId;
      inspectorActiveTab = "comments";
      render();
    })
  );
  menu.appendChild(
    contextMenuItem("→ Convert to Planning Object", async () => {
      pushUndoSnapshot("Convert to Planning Object");
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/convert-to-object`, { method: "POST" });
      const obj = await res.json();
      await loadProject();
      selectedConceptObjectId = obj.id;
      renderCanvas();
    }, { disabled: locked })
  );
  menu.appendChild(
    contextMenuItem(locked ? "🔓 Unlock" : "🔒 Lock", () => patchNodeById(nodeId, { locked: !locked }))
  );

  menu.appendChild(contextMenuSeparator());

  const moreItems = [
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
    }, { disabled: isRoot || locked }),
    contextMenuItem("+ Insert Sibling Above", () => addSiblingAbove(nodeId), { disabled: isRoot || locked }),
    contextMenuItem(
      "⬆ Promote (Move Up a Level)",
      async () => {
        pushUndoSnapshot("Promote");
        const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/outdent`, { method: "POST" });
        if (res.ok) {
          await loadProject();
        } else {
          undoStack.pop();
          updateUndoRedoButtons();
        }
      },
      { disabled: isRoot || locked || project.nodes[node.parent_id].parent_id === null }
    ),
    contextMenuItem(
      "⬇ Demote (Move Under Previous Sibling)",
      async () => {
        pushUndoSnapshot("Demote");
        const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/indent`, { method: "POST" });
        if (res.ok) {
          await loadProject();
        } else {
          undoStack.pop();
          updateUndoRedoButtons();
        }
      },
      { disabled: isRoot || locked || project.nodes[node.parent_id].children.indexOf(nodeId) === 0 }
    ),
    contextMenuItem("▤ Add Group", () => addGroupUnder(nodeId), { disabled: locked }),
    contextMenuItem("✎ Rename", () => {
      const label = prompt("Rename node:", node.label);
      if (label && label.trim()) {
        pushUndoSnapshot("Rename node");
        patchNodeById(nodeId, { label: label.trim() });
      }
    }, { disabled: locked }),
    contextMenuSubmenu("◆ Set Classification", [CLEAR, ...CLASSIFICATIONS], (opt) => {
      patchNodeById(nodeId, { classification: opt === CLEAR ? "" : opt });
    }),
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
    }),
    contextMenuItem("Change Node Type", () => {
      const value = prompt("Node type:", node.node_type || "");
      if (value !== null) patchNodeById(nodeId, { node_type: value.trim() });
    }),
    contextMenuSubmenu("● Set Lifecycle Stage", [CLEAR, "Planned", "In Development", "Done", "Blocked", "Deprecated"], (opt) => {
      patchNodeById(nodeId, { status: opt === CLEAR ? "" : opt });
    }),
    contextMenuSubmenu("● Set Priority", [CLEAR, "Low", "Medium", "High", "Critical"], (opt) => {
      patchNodeById(nodeId, { priority: opt === CLEAR ? "" : opt });
    }),
    contextMenuSubmenu("● Set Risk Level", [CLEAR, "Low", "Medium", "High", "Critical"], (opt) => {
      patchNodeById(nodeId, { risk_level: opt === CLEAR ? "" : opt });
    }),
    contextMenuItem("+ Add Tag", () => {
      const tag = prompt("Tag to add:");
      if (tag && tag.trim() && !node.tags.includes(tag.trim())) {
        patchNodeById(nodeId, { tags: [...node.tags, tag.trim()] });
      }
    }),
    contextMenuItem("Assign Owner", () => {
      const owner = prompt("Owner:", node.owner || "");
      if (owner !== null) patchNodeById(nodeId, { owner: owner.trim() });
    }),
    contextMenuItem("Add / Edit Notes", () => {
      focusedNodeId = nodeId;
      inspectorActiveTab = "documentation";
      render();
      const textarea = inspectorContent.querySelector("textarea");
      if (textarea) textarea.focus();
    }),
    contextMenuItem(node.collapsed ? "▸ Expand Branch" : "▾ Collapse Branch", () => toggleCollapse(nodeId, !node.collapsed), {
      disabled: node.children.length === 0,
    }),
    contextMenuItem("Copy Subtree", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/subtree`);
      clipboardSubtree = await res.json();
    }),
    contextMenuItem("Paste Subtree Here", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/paste-subtree`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ root: clipboardSubtree }),
      });
      const newNode = await res.json();
      await loadProject();
      focusNode(newNode.id);
    }, { disabled: !clipboardSubtree || locked }),
    contextMenuItem("⇩ Export Subtree", async () => {
      const res = await fetch(`/api/projects/${projectId}/nodes/${nodeId}/subtree`);
      const subtree = await res.json();
      downloadBlob(JSON.stringify(subtree, null, 2), `${safeFilename(node.label)}_subtree.json`, "application/json");
    }),
  ];
  menu.appendChild(contextMenuElementSubmenu("▸ More", moreItems));

  menu.appendChild(contextMenuSeparator());

  menu.appendChild(
    contextMenuItem("🗑 Delete", () => deleteNodeFlow(nodeId), { disabled: isRoot || locked, danger: true })
  );

  menu.style.left = `${clientX}px`;
  menu.style.top = `${clientY}px`;
  document.body.appendChild(menu);
  openContextMenuEl = menu;

  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) menu.style.left = `${Math.max(4, window.innerWidth - rect.width - 4)}px`;
  if (rect.bottom > window.innerHeight) menu.style.top = `${Math.max(4, window.innerHeight - rect.height - 4)}px`;
}

// Right-clicking a node that's part of a larger multi-selection shows the bulk-action menu
// instead of that one node's own menu — matches Miro/Mural, where right-click respects
// whatever's currently selected rather than always acting on a single object.
function openMultiSelectContextMenu(clientX, clientY) {
  closeContextMenu();
  const count = selectedNodeIds.size;
  const menu = document.createElement("div");
  menu.className = "context-menu";

  menu.appendChild(contextMenuItem(`${count} selected`, () => {}, { disabled: true }));
  menu.appendChild(contextMenuSeparator());
  menu.appendChild(contextMenuItem("▤ Group", groupSelectedNodes));
  menu.appendChild(contextMenuItem("Ungroup", ungroupSelectedNodes));
  menu.appendChild(contextMenuItem("⧉ Duplicate", duplicateSelectedNodes));
  // Align/Distribute write canvas_x/canvas_y, only meaningful where that's actually read
  // back (Focus Mode) — Full Architecture always recomputes its layout live.
  if (viewMode !== "full") {
    menu.appendChild(
      contextMenuSubmenu(
        "Align",
        ["Left", "Center", "Right", "Top", "Middle", "Bottom"],
        (opt) =>
          alignSelectedNodes(
            { Left: "left", Center: "center-h", Right: "right", Top: "top", Middle: "center-v", Bottom: "bottom" }[opt]
          )
      )
    );
    if (count >= 3) {
      menu.appendChild(
        contextMenuSubmenu("Distribute", ["Horizontally", "Vertically"], (opt) =>
          distributeSelectedNodes(opt === "Horizontally")
        )
      );
    }
  }
  menu.appendChild(contextMenuSeparator());
  menu.appendChild(contextMenuItem("🗑 Delete", deleteSelectedNodes, { danger: true }));
  menu.appendChild(contextMenuItem("Clear Selection", () => {
    clearSelection();
    renderCanvas();
  }));

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
// Entered via a node's right-click "Add Reference Link" (context menu) or the References
// tab's own button — there is no standalone toolbar toggle; the ref-mode-banner is the
// only persistent indicator that it's active.

function exitRefMode() {
  refMode = false;
  pendingRefFrom = null;
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

clusterZoomInBtn.addEventListener("click", () => {
  const c = viewportCenterClient();
  zoomAtPoint(zoomScale + ZOOM_STEP, c.x, c.y, true);
});
clusterZoomOutBtn.addEventListener("click", () => {
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

// Pan tool (rail's hand icon): a capture-phase listener so it runs BEFORE any node/object's
// own mousedown handler and can stopPropagation to suspend them entirely — clicking anywhere,
// including on top of content, just pans while this tool is active, matching Mural's Hand tool.
let canvasTool = "select"; // "select" | "pan"

function setCanvasTool(tool) {
  canvasTool = tool;
  toolSelectBtn.classList.toggle("active", tool === "select");
  toolPanBtn.classList.toggle("active", tool === "pan");
  canvasSvg.classList.toggle("pan-tool-active", tool === "pan");
}
toolSelectBtn.addEventListener("click", () => setCanvasTool("select"));
toolPanBtn.addEventListener("click", () => setCanvasTool("pan"));

canvasSvg.addEventListener(
  "mousedown",
  (e) => {
    if (canvasTool !== "pan" || e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    isPanning = true;
    panDragStart = { clientX: e.clientX, clientY: e.clientY, startX: panOffsetX, startY: panOffsetY };
    canvasSvg.classList.add("panning");
  },
  true
);

window.addEventListener("mousemove", (e) => {
  if (!isPanning || !panDragStart) return;
  panOffsetX = panDragStart.startX + (e.clientX - panDragStart.clientX);
  panOffsetY = panDragStart.startY + (e.clientY - panDragStart.clientY);
  renderCanvas();
});
window.addEventListener("mouseup", () => {
  if (!isPanning) return;
  isPanning = false;
  panDragStart = null;
  canvasSvg.classList.remove("panning");
});
canvasSvg.addEventListener("auxclick", (e) => {
  if (e.button === 1) e.preventDefault();
});

// Double-clicking a node on the canvas renames it in place (Miro/Figma-style direct text
// editing) instead of zooming — zoom-to-node is still reachable via Presentation Mode's
// Zoom to Topic, this just frees up double-click for the more expected behavior.
function startNodeCanvasRename(nodeId, pos) {
  const node = project.nodes[nodeId];
  if (node.locked) return;
  const rect = canvasSvg.getBoundingClientRect();
  const localX = lastViewW / 2 + panOffsetX + zoomScale * (pos.x - lastViewW / 2);
  const localY = lastViewH / 2 + panOffsetY + zoomScale * (pos.y - lastViewH / 2);

  const input = document.createElement("input");
  input.type = "text";
  input.className = "node-rename-overlay";
  input.value = node.label;
  input.style.left = `${rect.left + localX - (NODE_W * zoomScale) / 2}px`;
  input.style.top = `${rect.top + localY - (NODE_H * zoomScale) / 2}px`;
  input.style.width = `${NODE_W * zoomScale}px`;
  input.style.height = `${NODE_H * zoomScale}px`;
  document.body.appendChild(input);
  input.focus();
  input.select();

  const commit = async () => {
    input.removeEventListener("blur", commit);
    if (input.parentNode) input.remove();
    const trimmed = input.value.trim();
    if (trimmed && trimmed !== node.label) {
      pushUndoSnapshot("Rename node");
      await patchNodeById(nodeId, { label: trimmed });
    }
  };
  input.addEventListener("blur", commit);
  input.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Escape") {
      input.removeEventListener("blur", commit);
      input.remove();
    } else if (e.key === "Enter") {
      e.preventDefault();
      input.blur();
    }
  });
}

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

// Centers the given content-space bounds in the viewport and scales to fit, correctly
// accounting for bounds that aren't already centered around (viewW/2, viewH/2) — needed
// for Fit Selection/Fit Branch, whose bounding boxes can sit anywhere in content space.
function fitToBounds(bounds, viewW, viewH, smooth = true) {
  const boxW = Math.max(bounds.maxX - bounds.minX, 1);
  const boxH = Math.max(bounds.maxY - bounds.minY, 1);
  const padding = 60;
  const scale = Math.min((viewW - padding * 2) / boxW, (viewH - padding * 2) / boxH, ZOOM_MAX);
  zoomScale = Math.max(0.1, scale);
  const cx = (bounds.minX + bounds.maxX) / 2;
  const cy = (bounds.minY + bounds.maxY) / 2;
  panOffsetX = -zoomScale * (cx - viewW / 2);
  panOffsetY = -zoomScale * (cy - viewH / 2);
  zoomLevelEl.textContent = `${Math.round(zoomScale * 100)}%`;
  smoothZoomNextRender = smooth;
  renderCanvas();
}

function fitToView(smooth = true) {
  if (!project || !focusedNodeId) return;
  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;
  const { bounds } = viewMode === "full" ? computeFullArchitectureLayout(viewW, viewH) : computeCanvasLayout(viewW, viewH);
  fitToBounds(bounds, viewW, viewH, smooth);
}

function boundsFromPositions(ids) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const id of ids) {
    const pos = lastVisiblePositions.get(id);
    if (!pos) continue;
    minX = Math.min(minX, pos.x - NODE_W / 2);
    maxX = Math.max(maxX, pos.x + NODE_W / 2);
    minY = Math.min(minY, pos.y - NODE_H / 2);
    maxY = Math.max(maxY, pos.y + NODE_H / 2);
  }
  return isFinite(minX) ? { minX, maxX, minY, maxY } : null;
}

// Fit Selection: frames the current multi-selection if there is one, otherwise falls back
// to the same "fit the current focus context" behavior as before.
function fitSelection() {
  if (!project) return;
  if (selectedNodeIds.size === 0) {
    fitToView();
    return;
  }
  const bounds = boundsFromPositions(selectedNodeIds);
  if (!bounds) {
    fitToView();
    return;
  }
  const rect = canvasSvg.getBoundingClientRect();
  fitToBounds(bounds, rect.width || 800, rect.height || 500);
}

// Fit Branch: switches to Full Architecture mode (so the whole subtree actually renders)
// and frames just the focused node's own descendants, not the whole tree.
function fitBranch() {
  if (!project || !focusedNodeId) return;
  viewMode = "full";
  focusModeBtn.classList.remove("active");
  fullArchModeBtn.classList.add("active");
  renderCanvas();
  const bounds = boundsFromPositions(collectSubtreeIds(focusedNodeId));
  if (!bounds) return;
  const rect = canvasSvg.getBoundingClientRect();
  fitToBounds(bounds, rect.width || 800, rect.height || 500);
}

function fitArchitecture() {
  viewMode = "full";
  focusModeBtn.classList.remove("active");
  fullArchModeBtn.classList.add("active");
  fitToView();
}

// ---------- Toolbar dropdowns: Layout and Settings ----------
// The permanent toolbar stays minimal (Search, Insert, Export, Undo, Redo, Present, Layout,
// Settings) — camera/arrangement controls live in Layout, display toggles live in Settings,
// closing whichever other dropdown/modal is open so only one is ever visible at a time.
function closeToolbarMenus() {
  exportMenu.hidden = true;
  layoutMenu.hidden = true;
  settingsMenu.hidden = true;
  shapesFlyout.hidden = true;
  selMoreMenu.hidden = true;
  workspaceSwitcherMenu.hidden = true;
  domainFilterMenu.hidden = true;
  closeImportModal();
}
layoutMenuBtn.addEventListener("click", () => {
  const wasHidden = layoutMenu.hidden;
  closeToolbarMenus();
  layoutMenu.hidden = !wasHidden;
});
settingsMenuBtn.addEventListener("click", () => {
  const wasHidden = settingsMenu.hidden;
  closeToolbarMenus();
  settingsMenu.hidden = !wasHidden;
});
workspaceSwitcherBtn.addEventListener("click", () => {
  const wasHidden = workspaceSwitcherMenu.hidden;
  closeToolbarMenus();
  workspaceSwitcherMenu.hidden = !wasHidden;
});
domainFilterBtn.addEventListener("click", () => {
  const wasHidden = domainFilterMenu.hidden;
  closeToolbarMenus();
  domainFilterMenu.hidden = !wasHidden;
});
// Only "canvas" (Hierarchy) has real content today (WP11 builds the Workspace Framework
// infrastructure only, per this project's one-capability-per-WP rule) -- every other entry
// is rendered disabled in the HTML, so this only ever needs to close the menu.
workspaceSwitcherMenu.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-workspace]");
  if (!btn || btn.disabled) return;
  switchToWorkspace(btn.dataset.workspace);
  workspaceSwitcherMenu.hidden = true;
});
domainFilterMenu.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-domain]");
  if (!btn) return;
  activeDomainFilter = btn.dataset.domain;
  setCurrentDomainFilter(activeDomainFilter);
  domainFilterBtn.textContent = `Domain: ${activeDomainFilter} ▾`;
  domainFilterBtn.classList.toggle("active", activeDomainFilter !== "Hierarchy");
  domainFilterMenu.hidden = true;
  renderCanvas();
});

// ---------- Workspace switching (Phase 9 section 2, WP11 Framework + WP11a Kanban) ----------
// Every workspace fills the same primary-content region below the topbar (Phase 9's own
// generic shell) -- switching means showing exactly one of .editor-panes / #kanbanPane and
// hiding the rest, never both. Only "canvas" and "kanban" have real content; switching to
// any other id is unreachable today since the switcher only ever enables real entries.
const KANBAN_STATUS_ORDER = ["Not Started", "In Progress", "Blocked", "Needs Review", "Completed"];
const KANBAN_STATUS_ICONS = {
  "Not Started": "○",
  "In Progress": "◐",
  Blocked: "⛔",
  "Needs Review": "⚠",
  Completed: "✓",
};

function switchToWorkspace(workspaceId) {
  setCurrentWorkspaceId(workspaceId);
  const entry = getWorkspaceRegistry().find((w) => w.id === workspaceId) || getWorkspaceRegistry()[0];
  workspaceSwitcherBtn.textContent = `🗂 ${entry.label} ▾`;
  for (const btn of workspaceSwitcherMenu.querySelectorAll("button[data-workspace]")) {
    btn.textContent = btn.textContent.replace(/^✓\s*/, "");
    if (btn.dataset.workspace === workspaceId) btn.textContent = `✓ ${btn.textContent}`;
  }
  editorPanesEl.hidden = workspaceId !== "canvas";
  kanbanPane.hidden = workspaceId !== "kanban";
  timelinePane.hidden = workspaceId !== "timeline";
  documentationPane.hidden = workspaceId !== "documentation";
  dependenciesPane.hidden = workspaceId !== "dependencies";
  healthPane.hidden = workspaceId !== "health";
  reasoningPane.hidden = workspaceId !== "reasoning";
  if (workspaceId === "kanban") renderKanbanBoard();
  if (workspaceId === "timeline") renderTimelineBoard();
  if (workspaceId === "documentation") renderDocumentationBoard();
  if (workspaceId === "dependencies") renderDependenciesBoard();
  if (workspaceId === "health" && !lastValidationReport) refreshHealthPanel();
  if (workspaceId === "reasoning") renderReasoningBoard();
  else stopReasoningPolling(); // leaving the workspace mid-run shouldn't keep polling in the background
}

// ---------- AI Reasoning workspace (first screen for the reasoning/governance backend --
// previously only reachable by calling the API directly). Three states, never blended:
// intake (describe an objective) -> running (a pipeline stepper, polling the Cycle the
// backend already tracks) -> reviewing (the proposal + governance verdict + one action).
// Async only (POST /api/intelligence/reason-async) -- the pipeline is up to 9 sequential
// AI calls; a blocking sync fetch would freeze the UI for up to a minute with no feedback. ----------

const REASONING_STAGES = [
  { key: "domain_selection", label: "Domains" },
  { key: "business_analysis", label: "Business" },
  { key: "capability_analysis", label: "Capability" },
  { key: "architecture_thinking", label: "Architecture" },
  { key: "dependency_reasoning", label: "Dependencies" },
  { key: "risk_reasoning", label: "Risk" },
  { key: "governance_reasoning", label: "Governance" },
  { key: "technology_reasoning", label: "Technology" },
  { key: "implementation_reasoning", label: "Implementation" },
];

const REASONING_VERDICT_LABELS = {
  approved: "Approved",
  rejected: "Rejected",
  held_pending_human_review: "Held for human review",
  held_pending_risk_acceptance: "Held for risk acceptance",
};

let reasoningScreenState = "intake"; // intake | running | reviewing
let reasoningCycleId = null;
let reasoningPollTimer = null;
let reasoningResult = null; // the ReasoningResult once available
let reasoningReview = null; // the GovernanceReview once available
let reasoningStageAgents = new Map(); // stage key -> agent name, for completed stages
let reasoningCommittedNodeIds = null; // set after a successful commit, switches to the success view
let reasoningCommittedRiskIds = null;

function reasoningRootNodeId() {
  return Object.values(project.nodes).find((n) => !n.parent_id).id;
}

function reasoningResetToIntake() {
  reasoningScreenState = "intake";
  reasoningResult = null;
  reasoningReview = null;
  reasoningStageAgents = new Map();
  reasoningCommittedNodeIds = null;
  reasoningCommittedRiskIds = null;
}

function stopReasoningPolling() {
  if (reasoningPollTimer) {
    clearTimeout(reasoningPollTimer);
    reasoningPollTimer = null;
  }
}

function renderReasoningBoard() {
  if (!reasoningBoard) return;
  if (!project) {
    reasoningBoard.innerHTML = "";
    return;
  }
  if (reasoningScreenState === "intake") renderReasoningIntake();
  else if (reasoningScreenState === "running") renderReasoningRunning();
  else renderReasoningReviewing();
}

function renderReasoningIntake() {
  reasoningBoard.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "reasoning-intake";

  const hint = document.createElement("div");
  hint.className = "reasoning-intake-hint";
  hint.textContent =
    "Describe a business objective. Architeq reasons across Business, Data, Application, and Technology, then governance decides what happens next.";
  wrap.appendChild(hint);

  if (focusedNodeId && project.nodes[focusedNodeId]) {
    const context = document.createElement("div");
    context.className = "reasoning-intake-context";
    context.textContent = `Attaching under: ${project.nodes[focusedNodeId].label}`;
    wrap.appendChild(context);
  }

  const textarea = document.createElement("textarea");
  textarea.className = "reasoning-objective-input";
  textarea.placeholder = "e.g. Enable single sign-on for enterprise customers";
  wrap.appendChild(textarea);

  const button = document.createElement("button");
  button.className = "btn btn-primary";
  button.textContent = "Reason";
  button.addEventListener("click", () => {
    const objective = textarea.value.trim();
    if (!objective) return;
    startReasoningRun(objective);
  });
  wrap.appendChild(button);

  reasoningBoard.appendChild(wrap);
}

async function startReasoningRun(objective) {
  reasoningResetToIntake();
  reasoningScreenState = "running";
  renderReasoningBoard();
  const response = await fetch("/api/intelligence/reason-async", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ objective }),
  });
  if (!response.ok) {
    reasoningResetToIntake();
    renderReasoningBoard();
    return;
  }
  const cycle = await response.json();
  reasoningCycleId = cycle.id;
  pollReasoningCycle();
}

function parseStageEventDetail(detail) {
  const match = /^([a-z_]+) \(([^)]*)\)/.exec(detail || "");
  return match ? { stage: match[1], agent: match[2] } : { stage: null, agent: null };
}

async function pollReasoningCycle() {
  if (!reasoningCycleId) return;
  const response = await fetch(`/api/cycles/${reasoningCycleId}`);
  if (!response.ok) return;
  const cycle = await response.json();
  for (const event of cycle.events) {
    if (event.event_type === "StageCompleted") {
      const parsed = parseStageEventDetail(event.detail);
      if (parsed.stage) reasoningStageAgents.set(parsed.stage, parsed.agent);
    }
  }
  if (cycle.status === "Completed") {
    reasoningResult = cycle.result && cycle.result.reasoning;
    reasoningReview = cycle.result && cycle.result.review;
    reasoningScreenState = "reviewing";
    renderReasoningBoard();
    return;
  }
  if (cycle.status === "Failed") {
    reasoningResetToIntake();
    renderReasoningBoard();
    return;
  }
  if (reasoningScreenState === "running") renderReasoningRunning();
  reasoningPollTimer = setTimeout(pollReasoningCycle, 1500);
}

function renderReasoningRunning() {
  reasoningBoard.innerHTML = "";
  const heading = document.createElement("div");
  heading.className = "reasoning-section-label";
  heading.textContent = "Reasoning in progress";
  reasoningBoard.appendChild(heading);

  const pipeline = document.createElement("div");
  pipeline.className = "reasoning-pipeline";
  let activeAssigned = false;
  for (const stage of REASONING_STAGES) {
    const completed = reasoningStageAgents.has(stage.key);
    const stageEl = document.createElement("div");
    stageEl.className = "reasoning-stage" + (completed ? " completed" : !activeAssigned ? " active" : "");
    if (!completed) activeAssigned = true;

    const dot = document.createElement("div");
    dot.className = "reasoning-stage-dot";
    dot.textContent = completed ? "✓" : "";
    stageEl.appendChild(dot);

    const label = document.createElement("div");
    label.className = "reasoning-stage-label";
    label.textContent = stage.label;
    stageEl.appendChild(label);

    if (completed) {
      const agent = document.createElement("div");
      agent.className = "reasoning-stage-agent";
      agent.textContent = reasoningStageAgents.get(stage.key) || "";
      stageEl.appendChild(agent);
    }
    pipeline.appendChild(stageEl);
  }
  reasoningBoard.appendChild(pipeline);
}

function reasoningVerdictBucket(confidenceTier) {
  return confidenceTier === "High" ? "high" : confidenceTier === "Medium" ? "medium" : "low";
}

function renderReasoningReviewing() {
  reasoningBoard.innerHTML = "";
  if (!reasoningResult) {
    const empty = document.createElement("div");
    empty.className = "reasoning-empty-state";
    empty.textContent = "Something went wrong reading the result.";
    reasoningBoard.appendChild(empty);
    const retryBtn = document.createElement("button");
    retryBtn.className = "btn btn-small";
    retryBtn.textContent = "Start over";
    retryBtn.addEventListener("click", () => {
      reasoningResetToIntake();
      renderReasoningBoard();
    });
    reasoningBoard.appendChild(retryBtn);
    return;
  }

  if (reasoningCommittedNodeIds) {
    renderReasoningCommittedSuccess();
    return;
  }

  const summaryRow = document.createElement("div");
  summaryRow.className = "reasoning-summary-row";
  const confidenceBadge = document.createElement("span");
  confidenceBadge.className = `reasoning-confidence-badge ${reasoningVerdictBucket(reasoningResult.confidence_tier)}`;
  confidenceBadge.textContent = `${reasoningResult.confidence_tier} confidence`;
  summaryRow.appendChild(confidenceBadge);
  for (const domain of reasoningResult.domains || []) {
    const pill = document.createElement("span");
    pill.className = "reasoning-domain-pill";
    pill.textContent = domain;
    summaryRow.appendChild(pill);
  }
  reasoningBoard.appendChild(summaryRow);

  const nodesLabel = document.createElement("div");
  nodesLabel.className = "reasoning-section-label";
  nodesLabel.textContent = `Proposed components (${reasoningResult.proposed_nodes.length})`;
  reasoningBoard.appendChild(nodesLabel);
  const nodeRow = document.createElement("div");
  nodeRow.className = "reasoning-node-row";
  for (const node of reasoningResult.proposed_nodes) {
    const card = document.createElement("div");
    card.className = "reasoning-node-card";
    const label = document.createElement("div");
    label.textContent = node.label;
    card.appendChild(label);
    if (node.node_type) {
      const type = document.createElement("div");
      type.className = "reasoning-node-card-type";
      type.textContent = node.node_type;
      card.appendChild(type);
    }
    nodeRow.appendChild(card);
  }
  reasoningBoard.appendChild(nodeRow);

  if (reasoningResult.proposed_relationships && reasoningResult.proposed_relationships.length) {
    const relLabel = document.createElement("div");
    relLabel.className = "reasoning-section-label";
    relLabel.textContent = `Proposed relationships (${reasoningResult.proposed_relationships.length})`;
    reasoningBoard.appendChild(relLabel);
    for (const rel of reasoningResult.proposed_relationships) {
      const row = document.createElement("div");
      row.className = "reasoning-relationship-row";
      const from = document.createElement("span");
      from.textContent = rel.from_label;
      row.appendChild(from);
      const arrow = document.createElement("span");
      arrow.textContent = "→";
      row.appendChild(arrow);
      const to = document.createElement("span");
      to.textContent = rel.to_label;
      row.appendChild(to);
      if (rel.label) {
        const relLabelTag = document.createElement("span");
        relLabelTag.className = "rel-label";
        relLabelTag.textContent = rel.label;
        row.appendChild(relLabelTag);
      }
      reasoningBoard.appendChild(row);
    }
  }

  if (reasoningResult.proposed_risks && reasoningResult.proposed_risks.length) {
    const details = document.createElement("details");
    details.className = "reasoning-disclosure";
    const summary = document.createElement("summary");
    summary.textContent = `${reasoningResult.proposed_risks.length} risk(s) identified`;
    details.appendChild(summary);
    for (const risk of reasoningResult.proposed_risks) {
      const card = document.createElement("div");
      card.className = "reasoning-risk-card";
      const desc = document.createElement("div");
      desc.textContent = risk.description;
      card.appendChild(desc);
      const severity = document.createElement("span");
      severity.className = `reasoning-risk-severity ${(risk.initial_level || "low").toLowerCase()}`;
      severity.textContent = risk.initial_level || "Unknown";
      card.appendChild(severity);
      details.appendChild(card);
    }
    reasoningBoard.appendChild(details);
  }

  const outcome = reasoningReview ? reasoningReview.outcome : "unknown";
  const banner = document.createElement("div");
  const bannerClass = outcome === "approved" ? "approved" : outcome === "rejected" ? "rejected" : "held";
  banner.className = `reasoning-verdict-banner ${bannerClass}`;
  const title = document.createElement("div");
  title.className = "reasoning-verdict-title";
  title.textContent = REASONING_VERDICT_LABELS[outcome] || outcome;
  banner.appendChild(title);
  if (reasoningReview) {
    for (const finding of reasoningReview.findings || []) {
      const line = document.createElement("div");
      line.className = "reasoning-finding-line";
      line.textContent = `${finding.severity}: ${finding.message}`;
      banner.appendChild(line);
    }
  }
  reasoningBoard.appendChild(banner);

  const actions = document.createElement("div");
  actions.className = "reasoning-actions";
  if (outcome !== "rejected") {
    const approveBtn = document.createElement("button");
    approveBtn.className = "btn btn-primary";
    approveBtn.textContent = "Approve";
    approveBtn.addEventListener("click", () => approveReasoningProposal());
    actions.appendChild(approveBtn);
  }
  const rejectBtn = document.createElement("button");
  rejectBtn.className = "btn btn-small";
  rejectBtn.textContent = "Reject";
  rejectBtn.addEventListener("click", () => rejectReasoningProposal());
  actions.appendChild(rejectBtn);
  reasoningBoard.appendChild(actions);
}

async function approveReasoningProposal() {
  const parentId = focusedNodeId && project.nodes[focusedNodeId] ? focusedNodeId : reasoningRootNodeId();
  const response = await fetch(`/api/projects/${projectId}/nodes/${parentId}/commit-reasoning`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reasoningResult),
  });
  if (!response.ok) return;
  const payload = await response.json();
  reasoningCommittedNodeIds = payload.committed_node_ids;
  reasoningCommittedRiskIds = payload.committed_risk_ids;
  await loadProject();
  // Same reasoning as Import Outline's own auto-arrange call: proposed nodes land at
  // per-parent grid-math defaults, not a tidy layout, so a commit looks jumbled in Focus
  // Mode until Auto Arrange runs. Never let a fresh commit start messy.
  await autoArrangeLayout();
  renderReasoningBoard();
}

async function rejectReasoningProposal() {
  await fetch(`/api/projects/${projectId}/governance-decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      actor: "",
      decision_type: "Reject",
      target_node_id: null,
      rationale: `Rejected reasoning proposal for objective '${reasoningResult.objective}'`,
    }),
  });
  reasoningResetToIntake();
  renderReasoningBoard();
}

function renderReasoningCommittedSuccess() {
  const heading = document.createElement("div");
  heading.className = "reasoning-verdict-banner approved";
  const title = document.createElement("div");
  title.className = "reasoning-verdict-title";
  title.textContent = `Committed ${reasoningCommittedNodeIds.length} component(s)`;
  heading.appendChild(title);
  reasoningBoard.appendChild(heading);

  const nodesLabel = document.createElement("div");
  nodesLabel.className = "reasoning-section-label";
  nodesLabel.textContent = "New components";
  reasoningBoard.appendChild(nodesLabel);
  const nodeRow = document.createElement("div");
  nodeRow.className = "reasoning-node-row";
  for (const nodeId of reasoningCommittedNodeIds) {
    const node = project.nodes[nodeId];
    if (!node) continue;
    const card = document.createElement("div");
    card.className = "reasoning-node-card";
    card.title = "Jump to this component in Hierarchy";
    card.textContent = node.label;
    card.addEventListener("click", async () => {
      switchToWorkspace("canvas");
      await focusNode(node.id);
    });
    nodeRow.appendChild(card);
  }
  reasoningBoard.appendChild(nodeRow);

  const pendingRisks = (reasoningCommittedRiskIds || [])
    .map((riskId) => project.risks.find((r) => r.id === riskId))
    .filter((risk) => risk && risk.status !== "Accepted");
  if (pendingRisks.length) {
    const riskLabel = document.createElement("div");
    riskLabel.className = "reasoning-section-label";
    riskLabel.textContent = "Risks needing acceptance";
    reasoningBoard.appendChild(riskLabel);
    for (const risk of pendingRisks) {
      const card = document.createElement("div");
      card.className = "reasoning-risk-card";
      const desc = document.createElement("div");
      desc.textContent = risk.description;
      card.appendChild(desc);
      const acceptBtn = document.createElement("button");
      acceptBtn.className = "btn btn-small";
      acceptBtn.textContent = "Accept";
      acceptBtn.addEventListener("click", async () => {
        await fetch(`/api/projects/${projectId}/risks/${risk.id}/accept`, { method: "POST" });
        await loadProject();
        renderReasoningBoard();
      });
      card.appendChild(acceptBtn);
      reasoningBoard.appendChild(card);
    }
  }

  const startOverBtn = document.createElement("button");
  startOverBtn.className = "btn btn-small";
  startOverBtn.textContent = "Reason about something else";
  startOverBtn.addEventListener("click", () => {
    reasoningResetToIntake();
    renderReasoningBoard();
  });
  reasoningBoard.appendChild(startOverBtn);
}

// ---------- Decompose tab (Journey 2: Architecture -> Recursive Decomposition) ----------
// Lives in the Inspector, not a separate workspace -- unlike objective-first Reasoning,
// this is an action on an already-selected node. State is keyed per node (not a single
// global like reasoning's) since the Inspector can point at a different node anytime
// while a prior node's held proposal is still unresolved. Reuses the .reasoning-* CSS
// classes and card/banner idioms verbatim -- confirmed unscoped to the reasoning pane. ----------

const DECOMPOSE_STRATEGIES = ["Business", "Data", "Application", "Technology", "Governance"];

const decomposeStateByNode = new Map(); // nodeId -> { status, result, strategyOverride, primaryDiscarded, parallelDiscarded }

function getDecomposeState(nodeId) {
  if (!decomposeStateByNode.has(nodeId)) {
    decomposeStateByNode.set(nodeId, {
      status: "idle", // idle | running | result
      result: null,
      strategyOverride: "",
      primaryDiscarded: false,
      parallelDiscarded: false,
    });
  }
  return decomposeStateByNode.get(nodeId);
}

function nodeHasActiveRisk(nodeId) {
  return project.risks.some(
    (r) => r.target_node_id === nodeId && r.status !== "Accepted" && r.status !== "Mitigated"
  );
}

async function runDecompose(node) {
  const state = getDecomposeState(node.id);
  state.status = "running";
  state.primaryDiscarded = false;
  state.parallelDiscarded = false;
  renderInspector();
  const body = state.strategyOverride ? { strategy_override: state.strategyOverride } : {};
  const response = await fetch(`/api/projects/${projectId}/nodes/${node.id}/decompose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    state.status = "idle";
    renderInspector();
    return;
  }
  const result = await response.json();
  state.status = "result";
  state.result = result;
  const committedTotal = (result.committed_node_ids || []).length + (result.parallel_committed_node_ids || []).length;
  if (committedTotal > 0) {
    await loadProject();
    await autoArrangeLayout(); // same reasoning as reasoning's own commit -- grid-math
    // defaults don't respect subtree ownership, don't let a fresh commit start jumbled
  }
  renderInspector();
}

async function approveDecomposeProposal(node, isParallel) {
  const state = getDecomposeState(node.id);
  const result = state.result;
  const proposedNodes = isParallel ? result.parallel_proposed_nodes : result.proposed_nodes;
  const strategy = isParallel ? result.parallel_strategy : result.strategy;
  const response = await fetch(`/api/projects/${projectId}/nodes/${node.id}/commit-decomposition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy, terminal: false, proposed_nodes: proposedNodes }),
  });
  if (!response.ok) return;
  const payload = await response.json();
  if (isParallel) {
    result.parallel_committed_node_ids = payload.committed_node_ids;
    result.parallel_review = { ...result.parallel_review, outcome: "approved" };
  } else {
    result.committed_node_ids = payload.committed_node_ids;
    result.review = { ...result.review, outcome: "approved" };
  }
  await loadProject();
  await autoArrangeLayout();
  renderInspector();
}

async function discardDecomposeProposal(node, isParallel) {
  const state = getDecomposeState(node.id);
  const result = state.result;
  const strategyLabel = isParallel ? result.parallel_strategy : result.strategy;
  await fetch(`/api/projects/${projectId}/governance-decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      actor: "",
      decision_type: "Reject",
      target_node_id: null,
      rationale: `Rejected ${strategyLabel} decomposition proposal for '${node.label}'`,
    }),
  });
  if (isParallel) state.parallelDiscarded = true;
  else state.primaryDiscarded = true;
  renderInspector();
}

function renderDecomposeResultBlock(container, node, state, result, isParallel) {
  const strategy = isParallel ? result.parallel_strategy : result.strategy;
  const review = isParallel ? result.parallel_review : result.review;
  const proposedNodes = isParallel ? result.parallel_proposed_nodes : result.proposed_nodes;
  const committedIds = isParallel ? result.parallel_committed_node_ids : result.committed_node_ids;

  if (!isParallel && result.terminal && (!proposedNodes || !proposedNodes.length)) {
    const empty = document.createElement("div");
    empty.className = "reasoning-empty-state";
    empty.textContent = `Terminal for the ${strategy} strategy — nothing further to decompose.`;
    container.appendChild(empty);
    return;
  }

  if (!review) return;

  const outcome = review.outcome;
  if (outcome === "approved") {
    const banner = document.createElement("div");
    banner.className = "reasoning-verdict-banner approved";
    const title = document.createElement("div");
    title.className = "reasoning-verdict-title";
    title.textContent = `Committed ${(committedIds || []).length} component(s)`;
    banner.appendChild(title);
    container.appendChild(banner);

    const nodeRow = document.createElement("div");
    nodeRow.className = "reasoning-node-row";
    for (const nodeId of committedIds || []) {
      const childNode = project.nodes[nodeId];
      if (!childNode) continue;
      const card = document.createElement("div");
      card.className = "reasoning-node-card";
      card.title = "Jump to this component in Hierarchy";
      card.textContent = childNode.label;
      card.addEventListener("click", async () => {
        switchToWorkspace("canvas");
        await focusNode(childNode.id);
      });
      nodeRow.appendChild(card);
    }
    container.appendChild(nodeRow);
    return;
  }

  const bannerClass = outcome === "rejected" ? "rejected" : "held";
  const banner = document.createElement("div");
  banner.className = `reasoning-verdict-banner ${bannerClass}`;
  const title = document.createElement("div");
  title.className = "reasoning-verdict-title";
  title.textContent = REASONING_VERDICT_LABELS[outcome] || outcome;
  banner.appendChild(title);
  if (review.rationale) {
    const rationale = document.createElement("div");
    rationale.className = "reasoning-finding-line";
    rationale.textContent = review.rationale;
    banner.appendChild(rationale);
  }
  for (const finding of review.findings || []) {
    const line = document.createElement("div");
    line.className = "reasoning-finding-line";
    line.textContent = `${finding.severity}: ${finding.message}`;
    banner.appendChild(line);
  }
  container.appendChild(banner);

  const nodeRow = document.createElement("div");
  nodeRow.className = "reasoning-node-row";
  for (const proposedNode of proposedNodes || []) {
    const card = document.createElement("div");
    card.className = "reasoning-node-card";
    const label = document.createElement("div");
    label.textContent = proposedNode.label;
    card.appendChild(label);
    if (proposedNode.node_type) {
      const type = document.createElement("div");
      type.className = "reasoning-node-card-type";
      type.textContent = proposedNode.node_type;
      card.appendChild(type);
    }
    nodeRow.appendChild(card);
  }
  container.appendChild(nodeRow);

  const actions = document.createElement("div");
  actions.className = "reasoning-actions";
  if (outcome === "held_pending_human_review") {
    const approveBtn = document.createElement("button");
    approveBtn.className = "btn btn-primary";
    approveBtn.textContent = "Approve";
    approveBtn.addEventListener("click", () => approveDecomposeProposal(node, isParallel));
    actions.appendChild(approveBtn);
  }
  const discardBtn = document.createElement("button");
  discardBtn.className = "btn btn-small";
  discardBtn.textContent = "Discard";
  discardBtn.addEventListener("click", () => discardDecomposeProposal(node, isParallel));
  actions.appendChild(discardBtn);
  container.appendChild(actions);
}

function renderDecomposeTab(container, node) {
  const state = getDecomposeState(node.id);

  const strategyRow = document.createElement("div");
  strategyRow.className = "reasoning-actions";
  const select = document.createElement("select");
  select.className = "decompose-strategy-select";
  select.disabled = state.status === "running";
  const autoOption = document.createElement("option");
  autoOption.value = "";
  autoOption.textContent = "Auto";
  select.appendChild(autoOption);
  for (const strategyName of DECOMPOSE_STRATEGIES) {
    const opt = document.createElement("option");
    opt.value = strategyName;
    opt.textContent = strategyName;
    select.appendChild(opt);
  }
  select.value = state.strategyOverride || "";
  select.addEventListener("change", () => {
    state.strategyOverride = select.value;
  });
  strategyRow.appendChild(select);

  const button = document.createElement("button");
  button.className = "btn btn-primary";
  button.textContent = state.status === "running" ? "Decomposing…" : "Decompose";
  button.disabled = state.status === "running" || !!node.locked;
  button.addEventListener("click", () => runDecompose(node));
  strategyRow.appendChild(button);
  container.appendChild(strategyRow);

  if (nodeHasActiveRisk(node.id)) {
    const note = document.createElement("div");
    note.className = "reasoning-intake-hint";
    note.textContent = "An active risk on this node will also trigger a parallel Governance pass.";
    container.appendChild(note);
  }

  if (state.status !== "result" || !state.result) return;

  const result = state.result;
  const primaryHasReview = !state.primaryDiscarded && !!result.review;
  const primaryHasContent = !state.primaryDiscarded && (result.terminal || result.review);
  if (primaryHasContent) {
    renderDecomposeResultBlock(container, node, state, result, false);
  }

  if (result.parallel_strategy && !state.parallelDiscarded) {
    const details = document.createElement("details");
    details.className = "reasoning-disclosure";
    details.open = !primaryHasReview;
    const summary = document.createElement("summary");
    summary.textContent = "Also triggered: Governance strategy (active risk)";
    details.appendChild(summary);
    renderDecomposeResultBlock(details, node, state, result, true);
    container.appendChild(details);
  }
}

// ---------- Blueprint tab (Journey 3: Decomposition -> Implementation Blueprint) ----------
// Lives in the Inspector, same node-scoped placement as Decompose (not a workspace) --
// Blueprint is always triggered against a specific, already-selected subtree root. State
// is per-node (blueprintStateByNode), same reason as Decompose's own per-node state.
// Reuses the .reasoning-* CSS classes and card/banner idioms verbatim. ----------

const blueprintStateByNode = new Map(); // nodeId -> { status: "idle"|"running"|"result", result }

function getBlueprintState(nodeId) {
  if (!blueprintStateByNode.has(nodeId)) {
    blueprintStateByNode.set(nodeId, { status: "idle", result: null });
  }
  return blueprintStateByNode.get(nodeId);
}

async function runBlueprint(node) {
  const state = getBlueprintState(node.id);
  state.status = "running";
  renderInspector();
  const response = await fetch(`/api/projects/${projectId}/nodes/${node.id}/blueprint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    state.status = "idle";
    renderInspector();
    return;
  }
  const result = await response.json();
  state.status = "result";
  state.result = result;
  if ((result.committed_work_package_node_ids || []).length > 0) {
    await loadProject();
    await autoArrangeLayout(); // same reasoning as Reasoning/Decompose's own commit --
    // grid-math defaults don't respect subtree ownership, don't let a fresh commit start jumbled
  }
  renderInspector();
}

async function approveBlueprintProposal(node) {
  const state = getBlueprintState(node.id);
  const result = state.result;
  const response = await fetch(`/api/projects/${projectId}/nodes/${node.id}/commit-blueprint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(result),
  });
  if (!response.ok) return;
  const payload = await response.json();
  result.committed_work_package_node_ids = payload.committed_work_package_node_ids;
  result.committed_dependency_ids = payload.committed_dependency_ids;
  result.review = { ...result.review, outcome: "approved" };
  await loadProject();
  await autoArrangeLayout();
  renderInspector();
}

async function discardBlueprintProposal(node) {
  const state = getBlueprintState(node.id);
  await fetch(`/api/projects/${projectId}/governance-decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      actor: "",
      decision_type: "Reject",
      target_node_id: null,
      rationale: `Rejected Implementation Blueprint proposal for '${node.label}'`,
    }),
  });
  state.status = "idle";
  state.result = null;
  renderInspector();
}

function renderBlueprintTab(container, node) {
  const state = getBlueprintState(node.id);

  const actionsRow = document.createElement("div");
  actionsRow.className = "reasoning-actions";
  const button = document.createElement("button");
  button.className = "btn btn-primary";
  button.textContent =
    state.status === "running" ? "Generating…" : state.status === "result" ? "Regenerate" : "Generate Blueprint";
  button.disabled = state.status === "running" || !!node.locked;
  button.addEventListener("click", () => runBlueprint(node));
  actionsRow.appendChild(button);
  container.appendChild(actionsRow);

  if (state.status !== "result" || !state.result) return;

  const result = state.result;

  if (result.ready === false && (result.non_terminal_leaf_labels || []).length) {
    const note = document.createElement("div");
    note.className = "reasoning-intake-hint";
    note.textContent = `Some leaves may still need further decomposition: ${result.non_terminal_leaf_labels.join(", ")}.`;
    container.appendChild(note);
  }

  const review = result.review;
  if (!review) return;
  const outcome = review.outcome;

  if (outcome === "approved") {
    const banner = document.createElement("div");
    banner.className = "reasoning-verdict-banner approved";
    const title = document.createElement("div");
    title.className = "reasoning-verdict-title";
    title.textContent = `Committed ${(result.committed_work_package_node_ids || []).length} work package(s)`;
    banner.appendChild(title);
    container.appendChild(banner);

    const nodeRow = document.createElement("div");
    nodeRow.className = "reasoning-node-row";
    for (const wpNodeId of result.committed_work_package_node_ids || []) {
      const wpNode = project.nodes[wpNodeId];
      if (!wpNode) continue;
      const card = document.createElement("div");
      card.className = "reasoning-node-card";
      card.title = "Jump to this task in Hierarchy";
      card.textContent = wpNode.milestone ? `${wpNode.label} (${wpNode.milestone})` : wpNode.label;
      card.addEventListener("click", async () => {
        switchToWorkspace("canvas");
        await focusNode(wpNode.id);
      });
      nodeRow.appendChild(card);
    }
    container.appendChild(nodeRow);
  } else {
    const bannerClass = outcome === "rejected" ? "rejected" : "held";
    const banner = document.createElement("div");
    banner.className = `reasoning-verdict-banner ${bannerClass}`;
    const title = document.createElement("div");
    title.className = "reasoning-verdict-title";
    title.textContent = REASONING_VERDICT_LABELS[outcome] || outcome;
    banner.appendChild(title);
    if (review.rationale) {
      const rationale = document.createElement("div");
      rationale.className = "reasoning-finding-line";
      rationale.textContent = review.rationale;
      banner.appendChild(rationale);
    }
    for (const finding of review.findings || []) {
      const line = document.createElement("div");
      line.className = "reasoning-finding-line";
      line.textContent = `${finding.severity}: ${finding.message}`;
      banner.appendChild(line);
    }
    container.appendChild(banner);

    const nodeRow = document.createElement("div");
    nodeRow.className = "reasoning-node-row";
    for (const wp of result.proposed_work_packages || []) {
      const wpNode = project.nodes[wp.node_id];
      const card = document.createElement("div");
      card.className = "reasoning-node-card";
      const label = document.createElement("div");
      label.textContent = wpNode ? wpNode.label : wp.node_id;
      card.appendChild(label);
      const meta = document.createElement("div");
      meta.className = "reasoning-node-card-type";
      const bits = [wp.milestone];
      if (wp.target_date) bits.push(wp.target_date);
      if (wp.duration_days != null) bits.push(`${wp.duration_days}d`);
      meta.textContent = bits.filter(Boolean).join(" · ");
      card.appendChild(meta);
      nodeRow.appendChild(card);
    }
    container.appendChild(nodeRow);

    if ((result.proposed_dependencies || []).length) {
      const depSection = document.createElement("div");
      depSection.className = "reasoning-section-label";
      depSection.textContent = "Build order";
      container.appendChild(depSection);
      for (const dep of result.proposed_dependencies) {
        const fromNode = project.nodes[dep.from_node_id];
        const toNode = project.nodes[dep.to_node_id];
        const row = document.createElement("div");
        row.className = "reasoning-relationship-row";
        row.textContent = `${fromNode ? fromNode.label : dep.from_node_id} → ${toNode ? toNode.label : dep.to_node_id}`;
        if (dep.label) {
          const relLabel = document.createElement("span");
          relLabel.className = "rel-label";
          relLabel.textContent = dep.label;
          row.appendChild(relLabel);
        }
        container.appendChild(row);
      }
    }

    const actions = document.createElement("div");
    actions.className = "reasoning-actions";
    if (outcome === "held_pending_human_review") {
      const approveBtn = document.createElement("button");
      approveBtn.className = "btn btn-primary";
      approveBtn.textContent = "Approve";
      approveBtn.addEventListener("click", () => approveBlueprintProposal(node));
      actions.appendChild(approveBtn);
    }
    const discardBtn = document.createElement("button");
    discardBtn.className = "btn btn-small";
    discardBtn.textContent = "Discard";
    discardBtn.addEventListener("click", () => discardBlueprintProposal(node));
    actions.appendChild(discardBtn);
    container.appendChild(actions);
  }

  if (result.testing_strategy || result.ci_cd_strategy) {
    const details = document.createElement("details");
    details.className = "reasoning-disclosure";
    const summary = document.createElement("summary");
    summary.textContent = "Testing & CI/CD guidance";
    details.appendChild(summary);
    if (result.testing_strategy) {
      const p = document.createElement("div");
      p.className = "reasoning-finding-line";
      p.textContent = `Testing: ${result.testing_strategy}`;
      details.appendChild(p);
    }
    if (result.ci_cd_strategy) {
      const p = document.createElement("div");
      p.className = "reasoning-finding-line";
      p.textContent = `CI/CD: ${result.ci_cd_strategy}`;
      details.appendChild(p);
    }
    container.appendChild(details);
  }
}

// Breadcrumb-style path for a card, reusing the same parent_id chain compute_level already
// walks server-side -- traceability (Phase 9 section 3) made visible on every card, not just
// a "jump" affordance.
function kanbanCardPath(node) {
  const labels = [];
  let current = node.parent_id ? project.nodes[node.parent_id] : null;
  while (current) {
    labels.unshift(current.label);
    current = current.parent_id ? project.nodes[current.parent_id] : null;
  }
  return labels.join(" / ");
}

async function setNodePlanningStatus(nodeId, status) {
  await fetch(`/api/projects/${projectId}/nodes/${nodeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ planning_status: status }),
  });
  await loadProject();
}

function renderKanbanBoard() {
  if (!kanbanBoard) return;
  kanbanBoard.innerHTML = "";
  if (!project) return;

  const cardsByStatus = new Map(KANBAN_STATUS_ORDER.map((s) => [s, []]));
  for (const node of Object.values(project.nodes)) {
    if (node.planning_status && cardsByStatus.has(node.planning_status)) {
      cardsByStatus.get(node.planning_status).push(node);
    }
  }

  for (const status of KANBAN_STATUS_ORDER) {
    const cards = cardsByStatus.get(status);
    const column = document.createElement("div");
    column.className = "kanban-column";

    const header = document.createElement("div");
    header.className = "kanban-column-header";
    header.innerHTML =
      `<span>${KANBAN_STATUS_ICONS[status]} ${status}</span>` + `<span class="kanban-column-count">${cards.length}</span>`;
    column.appendChild(header);

    const list = document.createElement("div");
    list.className = "kanban-cards";
    if (cards.length === 0) {
      const empty = document.createElement("div");
      empty.className = "kanban-empty-state";
      empty.textContent = "No items";
      list.appendChild(empty);
    }
    for (const node of cards) {
      list.appendChild(renderKanbanCard(node, status));
    }
    column.appendChild(list);
    kanbanBoard.appendChild(column);
  }
}

function renderKanbanCard(node, status) {
  const card = document.createElement("div");
  card.className = "kanban-card";

  const label = document.createElement("div");
  label.className = "kanban-card-label";
  label.textContent = node.label;
  label.title = "Jump to this component in Hierarchy";
  label.addEventListener("click", async () => {
    switchToWorkspace("canvas");
    await focusNode(node.id);
  });
  card.appendChild(label);

  const path = kanbanCardPath(node);
  if (path) {
    const pathEl = document.createElement("div");
    pathEl.className = "kanban-card-path";
    pathEl.textContent = path;
    pathEl.title = path;
    card.appendChild(pathEl);
  }

  const select = document.createElement("select");
  select.className = "kanban-card-status-select";
  for (const s of KANBAN_STATUS_ORDER) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = `${KANBAN_STATUS_ICONS[s]} ${s}`;
    if (s === status) opt.selected = true;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => setNodePlanningStatus(node.id, select.value));
  card.appendChild(select);

  return card;
}

// ---------- Timeline workspace (Phase 9 section 6, WP11b) ----------
// Resolves section 6's own flagged gap: target_date/duration_days now exist on Node
// (migration_wp11b_node_temporal.sql). A shared date axis across every scheduled node,
// not independent per-row scales -- otherwise the bars wouldn't actually convey relative
// timing, which is the entire point of a timeline over a plain list.

const MS_PER_DAY = 24 * 60 * 60 * 1000;

async function setNodeSchedule(nodeId, targetDate, durationDays) {
  await fetch(`/api/projects/${projectId}/nodes/${nodeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_date: targetDate, duration_days: durationDays }),
  });
  await loadProject();
}

function renderTimelineBoard() {
  if (!timelineBoard) return;
  timelineBoard.innerHTML = "";
  if (!project) return;

  const scheduled = Object.values(project.nodes)
    .filter((n) => n.target_date)
    .sort((a, b) => a.target_date.localeCompare(b.target_date));

  if (scheduled.length === 0) {
    const empty = document.createElement("div");
    empty.className = "timeline-empty-state";
    empty.textContent = "No scheduled items yet -- set a target date on any node to place it here.";
    timelineBoard.appendChild(empty);
    return;
  }

  const starts = scheduled.map((n) => new Date(n.target_date).getTime());
  const ends = scheduled.map(
    (n) => new Date(n.target_date).getTime() + (n.duration_days || 1) * MS_PER_DAY
  );
  const rangeStart = Math.min(...starts);
  const rangeEnd = Math.max(...ends);
  const rangeSpan = Math.max(rangeEnd - rangeStart, MS_PER_DAY);

  const axis = document.createElement("div");
  axis.className = "timeline-axis";
  axis.innerHTML = `<span>${new Date(rangeStart).toISOString().slice(0, 10)}</span><span>${new Date(rangeEnd)
    .toISOString()
    .slice(0, 10)}</span>`;
  timelineBoard.appendChild(axis);

  for (const node of scheduled) {
    timelineBoard.appendChild(renderTimelineRow(node, rangeStart, rangeSpan));
  }
}

function renderTimelineRow(node, rangeStart, rangeSpan) {
  const row = document.createElement("div");
  row.className = "timeline-row";

  const label = document.createElement("div");
  label.className = "timeline-row-label";
  label.textContent = node.label;
  label.title = "Jump to this component in Hierarchy";
  label.addEventListener("click", async () => {
    switchToWorkspace("canvas");
    await focusNode(node.id);
  });
  if (node.milestone) {
    const chip = document.createElement("span");
    chip.className = "timeline-milestone-chip";
    chip.textContent = node.milestone;
    label.appendChild(chip);
  }
  row.appendChild(label);

  const inputs = document.createElement("div");
  inputs.className = "timeline-row-inputs";

  const dateInput = document.createElement("input");
  dateInput.type = "date";
  dateInput.value = node.target_date || "";
  const durationInput = document.createElement("input");
  durationInput.type = "number";
  durationInput.min = "1";
  durationInput.title = "Duration (days)";
  durationInput.value = node.duration_days || 1;

  const commit = () => setNodeSchedule(node.id, dateInput.value, Number(durationInput.value) || 1);
  dateInput.addEventListener("change", commit);
  durationInput.addEventListener("change", commit);
  inputs.appendChild(dateInput);
  inputs.appendChild(durationInput);
  row.appendChild(inputs);

  const track = document.createElement("div");
  track.className = "timeline-row-track";
  const bar = document.createElement("div");
  bar.className = "timeline-bar";
  const startOffset = new Date(node.target_date).getTime() - rangeStart;
  const durationMs = (node.duration_days || 1) * MS_PER_DAY;
  bar.style.left = `${(startOffset / rangeSpan) * 100}%`;
  bar.style.width = `${Math.max((durationMs / rangeSpan) * 100, 1)}%`;
  bar.title = `${node.target_date} · ${node.duration_days || 1}d`;
  track.appendChild(bar);
  row.appendChild(track);

  return row;
}

// ---------- Documentation workspace (Phase 9 section 12, WP11c) ----------
// Reads: Architecture Landscape (node notes/comments) + Knowledge Domain -- both already
// existed with real endpoints (Phase 9's own claim, confirmed true), so this needs no new
// backend at all: the existing per-node Comment endpoint and WP3's /api/knowledge/concepts
// list. A consolidated, browsable view of documentation scattered one-node-at-a-time across
// the tree today, not a new content model.

function renderDocumentationBoard() {
  if (!documentationBoard) return;
  documentationBoard.innerHTML = "";
  if (!project) return;

  const notesColumn = document.createElement("div");
  notesColumn.className = "documentation-column";
  const notesHeader = document.createElement("div");
  notesHeader.className = "documentation-column-header";
  notesHeader.textContent = "Architecture Notes & Comments";
  notesColumn.appendChild(notesHeader);
  const notesList = document.createElement("div");
  notesList.className = "documentation-list";

  const documented = Object.values(project.nodes)
    .filter((n) => n.notes.trim() || n.comments.length > 0)
    .sort((a, b) => a.label.localeCompare(b.label));

  if (documented.length === 0) {
    const empty = document.createElement("div");
    empty.className = "kanban-empty-state";
    empty.textContent = "No notes or comments yet -- add notes to a node, or comment on one, to see it here.";
    notesList.appendChild(empty);
  } else {
    for (const node of documented) notesList.appendChild(renderDocumentationNoteCard(node));
  }
  notesColumn.appendChild(notesList);
  documentationBoard.appendChild(notesColumn);

  const kbColumn = document.createElement("div");
  kbColumn.className = "documentation-column";
  const kbHeader = document.createElement("div");
  kbHeader.className = "documentation-column-header";
  kbHeader.textContent = "Knowledge Base";
  kbColumn.appendChild(kbHeader);
  const kbList = document.createElement("div");
  kbList.className = "documentation-list";
  kbList.innerHTML = '<div class="kanban-empty-state">Loading…</div>';
  kbColumn.appendChild(kbList);
  documentationBoard.appendChild(kbColumn);
  loadKnowledgeConceptsInto(kbList);
}

function renderDocumentationNoteCard(node) {
  const card = document.createElement("div");
  card.className = "documentation-card";

  const title = document.createElement("div");
  title.className = "documentation-card-title";
  title.textContent = node.label;
  title.title = "Jump to this component in Hierarchy";
  title.addEventListener("click", async () => {
    switchToWorkspace("canvas");
    await focusNode(node.id);
  });
  card.appendChild(title);

  const path = kanbanCardPath(node);
  if (path) {
    const pathEl = document.createElement("div");
    pathEl.className = "documentation-card-path";
    pathEl.textContent = path;
    card.appendChild(pathEl);
  }

  if (node.notes.trim()) {
    const notesEl = document.createElement("div");
    notesEl.className = "documentation-card-notes";
    notesEl.textContent = node.notes;
    card.appendChild(notesEl);
  }

  for (const comment of node.comments) {
    const commentEl = document.createElement("div");
    commentEl.className = "documentation-comment";
    commentEl.textContent = comment.text;
    card.appendChild(commentEl);
  }

  const form = document.createElement("div");
  form.className = "documentation-comment-form";
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Add a comment…";
  const addBtn = document.createElement("button");
  addBtn.className = "btn btn-small";
  addBtn.textContent = "Add";
  addBtn.addEventListener("click", async () => {
    const text = input.value.trim();
    if (!text) return;
    await fetch(`/api/projects/${projectId}/nodes/${node.id}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    await loadProject();
  });
  form.appendChild(input);
  form.appendChild(addBtn);
  card.appendChild(form);

  return card;
}

async function loadKnowledgeConceptsInto(container) {
  let concepts = [];
  try {
    const res = await fetch("/api/knowledge/concepts");
    if (res.ok) concepts = await res.json();
  } catch {
    // Knowledge Base is a separate, project-independent domain (Phase 6) -- a failed fetch
    // here just means an empty section, never blocks the rest of the Documentation workspace.
  }
  // The workspace may have been switched away from before this resolved.
  if (documentationPane.hidden) return;
  container.innerHTML = "";
  if (concepts.length === 0) {
    container.innerHTML = '<div class="kanban-empty-state">No Knowledge Base concepts yet.</div>';
    return;
  }
  for (const concept of concepts) {
    const card = document.createElement("div");
    card.className = "documentation-card";

    const title = document.createElement("div");
    title.className = "documentation-card-title";
    title.textContent = concept.name;
    const statusBadge = document.createElement("span");
    statusBadge.className = "documentation-kb-status";
    statusBadge.textContent = concept.status;
    title.appendChild(statusBadge);
    card.appendChild(title);

    const path = document.createElement("div");
    path.className = "documentation-card-path";
    path.textContent = `${concept.category} · ${concept.concept_id}`;
    card.appendChild(path);

    const definition = document.createElement("div");
    definition.className = "documentation-card-notes";
    definition.textContent = concept.definition;
    card.appendChild(definition);

    container.appendChild(card);
  }
}

// ---------- Dependencies workspace (Phase 9 sections 5/12, WP11d) ----------
// A Matrix artifact, deliberately typed differently from Kanban/Timeline/Documentation's
// Catalog artifacts (Phase 9 section 2). Reads: Architecture Landscape (Relationships) --
// scoped to node-to-node references only, excluding any reference touching a free-form
// Concept Mode object, since those live outside the formal node tree. Writes: relationship
// edits via the existing PUT/DELETE reference endpoints -- no new backend needed.

const REFERENCE_TYPE_OPTIONS = ["", "Dependency", "Warning", "Broken", "Data Flow", "Optional"];
let selectedDependencyRefId = null;

function renderDependenciesBoard() {
  if (!dependenciesBoard) return;
  dependenciesBoard.innerHTML = "";
  if (!project) return;

  const nodeRefs = project.references.filter((r) => project.nodes[r.from] && project.nodes[r.to]);
  if (nodeRefs.length === 0) {
    const empty = document.createElement("div");
    empty.className = "dependencies-empty-state";
    empty.textContent = "No relationships between components yet -- draw a connection on the canvas to see it here.";
    dependenciesBoard.appendChild(empty);
    return;
  }

  const nodeIds = new Set();
  for (const r of nodeRefs) {
    nodeIds.add(r.from);
    nodeIds.add(r.to);
  }
  const orderedNodes = [...nodeIds].map((id) => project.nodes[id]).sort((a, b) => a.label.localeCompare(b.label));

  const wrap = document.createElement("div");
  wrap.className = "dependencies-matrix-wrap";
  const table = document.createElement("table");
  table.className = "dependencies-matrix";

  const headRow = document.createElement("tr");
  headRow.appendChild(document.createElement("th"));
  for (const node of orderedNodes) {
    headRow.appendChild(makeDependencyHeaderCell(node, "dep-col-header"));
  }
  table.appendChild(headRow);

  for (const rowNode of orderedNodes) {
    const row = document.createElement("tr");
    row.appendChild(makeDependencyHeaderCell(rowNode, "dep-row-header"));
    for (const colNode of orderedNodes) {
      row.appendChild(makeDependencyCell(rowNode, colNode, nodeRefs));
    }
    table.appendChild(row);
  }
  wrap.appendChild(table);
  dependenciesBoard.appendChild(wrap);

  const panelHost = document.createElement("div");
  dependenciesBoard.appendChild(panelHost);
  const selectedRef = nodeRefs.find((r) => r.id === selectedDependencyRefId);
  if (selectedRef) {
    panelHost.appendChild(renderDependencyEditPanel(selectedRef));
  } else {
    selectedDependencyRefId = null;
  }
}

function makeDependencyHeaderCell(node, className) {
  const th = document.createElement("th");
  th.className = className;
  th.textContent = node.label;
  th.title = "Jump to this component in Hierarchy";
  th.addEventListener("click", async () => {
    switchToWorkspace("canvas");
    await focusNode(node.id);
  });
  return th;
}

function makeDependencyCell(rowNode, colNode, nodeRefs) {
  const td = document.createElement("td");
  if (rowNode.id === colNode.id) {
    td.className = "dependencies-cell diagonal";
    return td;
  }
  const ref = nodeRefs.find(
    (r) => (r.from === rowNode.id && r.to === colNode.id) || (r.from === colNode.id && r.to === rowNode.id)
  );
  td.className = "dependencies-cell" + (ref ? " has-ref" : "");
  if (ref) {
    td.textContent = ref.from === rowNode.id ? "→" : "←";
    td.title = `${ref.reference_type || "Relationship"}${ref.label ? ": " + ref.label : ""}`;
    td.addEventListener("click", () => {
      selectedDependencyRefId = ref.id;
      renderDependenciesBoard();
    });
  }
  return td;
}

function renderDependencyEditPanel(ref) {
  const panel = document.createElement("div");
  panel.className = "dependencies-edit-panel";

  const title = document.createElement("div");
  title.style.fontWeight = "700";
  title.textContent = `${project.nodes[ref.from].label} → ${project.nodes[ref.to].label}`;
  panel.appendChild(title);

  const labelField = document.createElement("label");
  labelField.textContent = "Label";
  const labelInput = document.createElement("input");
  labelInput.type = "text";
  labelInput.value = ref.label || "";
  panel.appendChild(labelField);
  panel.appendChild(labelInput);

  const typeField = document.createElement("label");
  typeField.textContent = "Relationship Type";
  const typeSelect = document.createElement("select");
  for (const opt of REFERENCE_TYPE_OPTIONS) {
    const option = document.createElement("option");
    option.value = opt;
    option.textContent = opt || "(none)";
    if ((ref.reference_type || "") === opt) option.selected = true;
    typeSelect.appendChild(option);
  }
  panel.appendChild(typeField);
  panel.appendChild(typeSelect);

  const actions = document.createElement("div");
  actions.className = "dependencies-edit-actions";
  const saveBtn = document.createElement("button");
  saveBtn.className = "btn btn-small btn-primary";
  saveBtn.textContent = "Save";
  saveBtn.addEventListener("click", async () => {
    // Both label and reference_type must be sent as real strings, never null -- the
    // backend's "None means leave unchanged" convention (tree.update_reference) means an
    // empty string is how a field actually gets cleared, not null.
    await fetch(`/api/projects/${projectId}/references/${ref.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from: ref.from,
        to: ref.to,
        label: labelInput.value.trim(),
        reference_type: typeSelect.value,
      }),
    });
    await loadProject();
  });
  const closeBtn = document.createElement("button");
  closeBtn.className = "btn btn-small";
  closeBtn.textContent = "Close";
  closeBtn.addEventListener("click", () => {
    selectedDependencyRefId = null;
    renderDependenciesBoard();
  });
  actions.appendChild(saveBtn);
  actions.appendChild(closeBtn);
  panel.appendChild(actions);

  return panel;
}

selMoreBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  const wasHidden = selMoreMenu.hidden;
  closeToolbarMenus();
  selMoreMenu.hidden = !wasHidden;
});
document.addEventListener("click", (e) => {
  if (!layoutMenu.hidden && !layoutMenu.contains(e.target) && e.target !== layoutMenuBtn) {
    layoutMenu.hidden = true;
  }
  if (!settingsMenu.hidden && !settingsMenu.contains(e.target) && e.target !== settingsMenuBtn) {
    settingsMenu.hidden = true;
  }
  if (!selMoreMenu.hidden && !selMoreMenu.contains(e.target) && e.target !== selMoreBtn) {
    selMoreMenu.hidden = true;
  }
  if (
    !workspaceSwitcherMenu.hidden &&
    !workspaceSwitcherMenu.contains(e.target) &&
    e.target !== workspaceSwitcherBtn
  ) {
    workspaceSwitcherMenu.hidden = true;
  }
  if (!domainFilterMenu.hidden && !domainFilterMenu.contains(e.target) && e.target !== domainFilterBtn) {
    domainFilterMenu.hidden = true;
  }
});
fitSelectionBtn.addEventListener("click", () => {
  layoutMenu.hidden = true;
  fitSelection();
});
fitBranchBtn.addEventListener("click", () => {
  layoutMenu.hidden = true;
  fitBranch();
});
fitAllBtn.addEventListener("click", () => {
  layoutMenu.hidden = true;
  fitArchitecture();
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
  if (e.button !== 0 || refMode || e.target !== canvasSvg || canvasTool === "pan") return;
  selectionBoxStart = { x: e.clientX, y: e.clientY };
  selectionBoxEl = document.createElement("div");
  selectionBoxEl.className = "selection-box";
  document.body.appendChild(selectionBoxEl);
  updateSelectionBoxRect(e.clientX, e.clientY);
});

// Right-click on empty canvas background (not on a node — those have their own context
// menu with stopPropagation) gets a smaller, canvas-scoped menu.
canvasSvg.addEventListener("contextmenu", (e) => {
  if (e.target !== canvasSvg) return;
  e.preventDefault();
  openCanvasContextMenu(e.clientX, e.clientY);
});

let conceptClipboard = null;

// One right-click menu for the whole canvas, regardless of what's under the cursor or which
// view is active — the same "+ Insert" picker as the toolbar Insert button, plus layout and
// presentation controls. Works even with nothing focused (previously silently did nothing).
function openCanvasContextMenu(clientX, clientY) {
  closeContextMenu();
  const menu = document.createElement("div");
  menu.className = "context-menu";
  const NEW_NODE_LABEL = "◆ New Architecture Node";

  menu.appendChild(
    contextMenuSubmenu("+ Insert", [NEW_NODE_LABEL, ...INSERT_TYPES.map(([, label]) => label)], (label) => {
      if (label === NEW_NODE_LABEL) {
        insertNewArchitectureNode();
        return;
      }
      const found = INSERT_TYPES.find(([, l]) => l === label);
      if (found) createConceptObject(found[0]);
    })
  );
  menu.appendChild(
    contextMenuElementSubmenu("📋 Paste", [
      contextMenuItem("Paste Object", () => pasteConceptObject(clientX, clientY), { disabled: !conceptClipboard }),
      contextMenuItem("Paste Subtree Here", async () => {
        const res = await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/paste-subtree`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ root: clipboardSubtree }),
        });
        const newNode = await res.json();
        await loadProject();
        focusNode(newNode.id);
      }, { disabled: !clipboardSubtree || !focusedNodeId }),
    ])
  );

  menu.appendChild(contextMenuSeparator());

  menu.appendChild(contextMenuItem("⤾ Auto Arrange", autoArrangeLayout));
  menu.appendChild(contextMenuItem("▶ Presentation Mode", enterPresentationMode));
  menu.appendChild(
    contextMenuElementSubmenu("⚙ Canvas Settings", [
      contextMenuItem(showConceptGrid ? "☑ Show Grid" : "☐ Show Grid", () => {
        showConceptGrid = !showConceptGrid;
        renderCanvas();
      }),
      contextMenuItem(snapToConceptGrid ? "☑ Snap to Grid" : "☐ Snap to Grid", () => {
        snapToConceptGrid = !snapToConceptGrid;
      }),
    ])
  );

  menu.style.left = `${clientX}px`;
  menu.style.top = `${clientY}px`;
  document.body.appendChild(menu);
  openContextMenuEl = menu;

  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) menu.style.left = `${Math.max(4, window.innerWidth - rect.width - 4)}px`;
  if (rect.bottom > window.innerHeight) menu.style.top = `${Math.max(4, window.innerHeight - rect.height - 4)}px`;
}

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
  const toScreen = (contentX, contentY) => ({
    x: svgRect.left + lastViewW / 2 + panOffsetX + zoomScale * (contentX - lastViewW / 2),
    y: svgRect.top + lastViewH / 2 + panOffsetY + zoomScale * (contentY - lastViewH / 2),
  });
  const inBox = (p) => p.x >= boxLeft && p.x <= boxRight && p.y >= boxTop && p.y <= boxBottom;

  const hits = [];
  for (const [nodeId, pos] of lastVisiblePositions.entries()) {
    if (inBox(toScreen(pos.x, pos.y))) hits.push(nodeId);
  }
  const objectHits = [];
  for (const obj of project.concept_objects) {
    if (inBox(toScreen(obj.x + obj.width / 2, obj.y + obj.height / 2))) objectHits.push(obj.id);
  }
  if (hits.length === 0 && objectHits.length === 0) return;
  if (!e.shiftKey) {
    selectedNodeIds = new Set();
    selectedConceptObjectIds = new Set();
  }
  for (const id of hits) selectedNodeIds.add(id);
  for (const id of objectHits) selectedConceptObjectIds.add(id);
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

selConnectBtn.addEventListener("click", () => {
  if (selectedNodeIds.size !== 1) return;
  const [nodeId] = selectedNodeIds;
  refMode = true;
  pendingRefFrom = nodeId;
  refModeBanner.hidden = false;
  renderCanvas();
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

// Selection bulk actions — shared functions so the selection toolbar AND the multi-select
// right-click menu (below) invoke exactly one implementation each, never two.
async function groupSelectedNodes() {
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
}

async function ungroupSelectedNodes() {
  const ids = [...selectedNodeIds].filter((id) => project.nodes[id].is_group);
  if (ids.length === 0) {
    alert("Select at least one group to ungroup.");
    return;
  }
  pushUndoSnapshot("Ungroup");
  for (const id of ids) {
    await fetch(`/api/projects/${projectId}/nodes/${id}?promote_children=true`, { method: "DELETE" });
  }
  clearSelection();
  await loadProject();
}

async function duplicateSelectedNodes() {
  const ids = [...selectedNodeIds];
  pushUndoSnapshot("Duplicate selected");
  let lastNode = null;
  for (const id of ids) {
    if (project.nodes[id].parent_id === null) continue; // root can't be duplicated
    const res = await fetch(`/api/projects/${projectId}/nodes/${id}/duplicate`, { method: "POST" });
    lastNode = await res.json();
  }
  clearSelection();
  await loadProject();
  if (lastNode) focusNode(lastNode.id);
}

async function deleteSelectedNodes() {
  const ids = [...selectedNodeIds].filter((id) => project.nodes[id].parent_id !== null);
  if (ids.length === 0) {
    alert("The root node cannot be deleted.");
    return;
  }
  const confirmed = confirm(`Delete ${ids.length} selected node${ids.length === 1 ? "" : "s"} and everything beneath them?`);
  if (!confirmed) return;
  pushUndoSnapshot("Delete selected");
  for (const id of ids) {
    if (!project.nodes[id]) continue; // already removed as a descendant of an earlier deletion this batch
    await fetch(`/api/projects/${projectId}/nodes/${id}?promote_children=false`, { method: "DELETE" });
  }
  clearSelection();
  await loadProject();
}

// Align / Distribute only make sense once positions are free (Unlock Layout, Full
// Architecture view) — updateSelectionToolbar() disables the toolbar buttons otherwise, and
// the multi-select context menu below hides them entirely rather than showing them disabled.
async function alignSelectedNodes(mode) {
  const nodes = [...selectedNodeIds].map((id) => project.nodes[id]);
  pushUndoSnapshot("Align selected");
  let target;
  if (mode === "left") target = Math.min(...nodes.map((n) => n.canvas_x - NODE_W / 2));
  else if (mode === "right") target = Math.max(...nodes.map((n) => n.canvas_x + NODE_W / 2));
  else if (mode === "center-h") target = nodes.reduce((s, n) => s + n.canvas_x, 0) / nodes.length;
  else if (mode === "top") target = Math.min(...nodes.map((n) => n.canvas_y - NODE_H / 2));
  else if (mode === "bottom") target = Math.max(...nodes.map((n) => n.canvas_y + NODE_H / 2));
  else target = nodes.reduce((s, n) => s + n.canvas_y, 0) / nodes.length; // center-v
  for (const node of nodes) {
    if (mode === "left") node.canvas_x = target + NODE_W / 2;
    else if (mode === "right") node.canvas_x = target - NODE_W / 2;
    else if (mode === "center-h") node.canvas_x = target;
    else if (mode === "top") node.canvas_y = target + NODE_H / 2;
    else if (mode === "bottom") node.canvas_y = target - NODE_H / 2;
    else node.canvas_y = target;
    await fetch(`/api/projects/${projectId}/nodes/${node.id}/position`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canvas_x: node.canvas_x, canvas_y: node.canvas_y }),
    });
  }
  renderCanvas();
}

async function distributeSelectedNodes(horizontal) {
  const nodes = [...selectedNodeIds].map((id) => project.nodes[id]);
  if (nodes.length < 3) {
    alert("Distribute needs at least 3 selected nodes.");
    return;
  }
  pushUndoSnapshot("Distribute selected");
  nodes.sort((a, b) => (horizontal ? a.canvas_x - b.canvas_x : a.canvas_y - b.canvas_y));
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  const span = horizontal ? last.canvas_x - first.canvas_x : last.canvas_y - first.canvas_y;
  const step = span / (nodes.length - 1);
  for (let i = 1; i < nodes.length - 1; i++) {
    const node = nodes[i];
    if (horizontal) node.canvas_x = first.canvas_x + step * i;
    else node.canvas_y = first.canvas_y + step * i;
    await fetch(`/api/projects/${projectId}/nodes/${node.id}/position`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canvas_x: node.canvas_x, canvas_y: node.canvas_y }),
    });
  }
  renderCanvas();
}

selGroupBtn.addEventListener("click", groupSelectedNodes);
selUngroupBtn.addEventListener("click", ungroupSelectedNodes);
selDuplicateBtn.addEventListener("click", duplicateSelectedNodes);
selDeleteBtn.addEventListener("click", deleteSelectedNodes);

selAlignBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  if (selAlignBtn.disabled) return;
  selAlignMenu.hidden = !selAlignMenu.hidden;
});
selAlignMenu.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-align]");
  if (!btn) return;
  selAlignMenu.hidden = true;
  alignSelectedNodes(btn.dataset.align);
});

selDistributeBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  if (selDistributeBtn.disabled) return;
  selDistributeMenu.hidden = !selDistributeMenu.hidden;
});
selDistributeMenu.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-distribute]");
  if (!btn) return;
  selDistributeMenu.hidden = true;
  distributeSelectedNodes(btn.dataset.distribute === "horizontal");
});
document.addEventListener("click", (e) => {
  if (!selAlignMenu.hidden && !selAlignMenu.contains(e.target) && e.target !== selAlignBtn) selAlignMenu.hidden = true;
  if (!selDistributeMenu.hidden && !selDistributeMenu.contains(e.target) && e.target !== selDistributeBtn) {
    selDistributeMenu.hidden = true;
  }
});

function setViewMode(mode) {
  if (viewMode === mode) return;
  viewMode = mode;
  focusModeBtn.classList.toggle("active", mode === "focus");
  fullArchModeBtn.classList.toggle("active", mode === "full");
  updateSelectionToolbar();
  fitToView();
}
focusModeBtn.addEventListener("click", () => setViewMode("focus"));
fullArchModeBtn.addEventListener("click", () => setViewMode("full"));

railAutoArrangeBtn.addEventListener("click", () => autoArrangeLayout());

// Full Architecture always shows the recursive layout live; this persists the same
// positions to storage so Focus Mode (which reads stored canvas_x/canvas_y, and is where
// free dragging actually means something) starts from a tidy arrangement instead of
// whatever scattered positions accumulated from past drags, imports, or stale data.
async function autoArrangeLayout() {
  pushUndoSnapshot("Auto Arrange");
  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;
  const positions = computeDeterministicFullLayout(viewW, viewH);
  for (const [nodeId, pos] of positions.entries()) {
    const node = project.nodes[nodeId];
    node.canvas_x = pos.x;
    node.canvas_y = pos.y;
    await fetch(`/api/projects/${projectId}/nodes/${nodeId}/position`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canvas_x: pos.x, canvas_y: pos.y }),
    });
  }
  await loadProject();
}

animateFlowCheckbox.addEventListener("change", () => {
  animateDataFlow = animateFlowCheckbox.checked;
  renderCanvas();
});
showGridCheckbox.addEventListener("change", () => {
  showConceptGrid = showGridCheckbox.checked;
  renderCanvas();
});
snapGridCheckbox.addEventListener("change", () => {
  snapToConceptGrid = snapGridCheckbox.checked;
});

async function addGroupUnder(parentId) {
  const name = prompt("Name for this group (e.g. Configuration, Scanning, Validation):");
  if (!name || !name.trim()) return;
  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: parentId, label: name.trim(), is_group: true }),
  });
  const newNode = await res.json();
  await focusNode(newNode.id);
}

showDepsCheckbox.addEventListener("change", () => {
  showDependencies = showDepsCheckbox.checked;
  renderCanvas();
});

// On by default per user preference: a visual board should read like electricity/data
// flowing through it out of the box, not require finding a settings toggle first.
let animateDataFlow = true;

// ---------- Visual status filters ----------

settingsMenu.addEventListener("change", (e) => {
  const checkbox = e.target.closest("input[data-filter]");
  if (!checkbox) return;
  if (checkbox.checked) activeStatusFilters.add(checkbox.dataset.filter);
  else activeStatusFilters.delete(checkbox.dataset.filter);
  const allChecked = activeStatusFilters.size === PLANNING_STATUSES.length;
  settingsMenuBtn.classList.toggle("active", !allChecked);
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

collapseAllBtn.addEventListener("click", async () => {
  layoutMenu.hidden = true;
  const allIds = Object.keys(project.nodes).filter((id) => id !== rootId);
  await setCollapsedForIds(allIds, true);
});

expandBranchBtn.addEventListener("click", async () => {
  layoutMenu.hidden = true;
  if (!focusedNodeId) return;
  await setCollapsedForIds(collectSubtreeIds(focusedNodeId), false);
});

expandToLevelBtn.addEventListener("click", async () => {
  layoutMenu.hidden = true;
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

// ---------- Right panel: collapsible side panels ----------

const editorPanesEl = document.querySelector(".editor-panes");

// Restores whichever workspace was last active (WP11 Framework), now that editorPanesEl
// exists -- switchToWorkspace/renderKanbanBoard are function declarations (hoisted), but
// editorPanesEl itself is a const that must actually execute first.
switchToWorkspace(getCurrentWorkspaceId());

const OUTLINE_COLLAPSED_KEY = "diagram-builder-outline-collapsed";
const INSPECTOR_COLLAPSED_KEY = "diagram-builder-inspector-collapsed";

// Applies whatever the anti-FOUC inline script in <head> already decided (from localStorage,
// defaulting to collapsed for a first-time session -- canvas dominates by default) as the
// real classes, then removes those data attributes: from this point on the classes below are
// the single source of truth, never the html[data-*] attributes again.
function applyInitialPaneCollapse() {
  const outlineCollapsed = document.documentElement.dataset.outlineCollapsed === "true";
  const inspectorCollapsed = document.documentElement.dataset.inspectorCollapsed === "true";
  outlinePane.classList.toggle("collapsed", outlineCollapsed);
  editorPanesEl.classList.toggle("outline-collapsed", outlineCollapsed);
  outlineCollapseBtn.textContent = outlineCollapsed ? "»" : "«";
  outlineCollapseBtn.title = outlineCollapsed ? "Expand Outline panel" : "Collapse this panel for a distraction-free canvas";
  inspectorPane.classList.toggle("collapsed", inspectorCollapsed);
  editorPanesEl.classList.toggle("inspector-collapsed", inspectorCollapsed);
  inspectorCollapseBtn.textContent = inspectorCollapsed ? "«" : "»";
  inspectorCollapseBtn.title = inspectorCollapsed ? "Expand Inspector panel" : "Collapse this panel for a distraction-free canvas";
  delete document.documentElement.dataset.outlineCollapsed;
  delete document.documentElement.dataset.inspectorCollapsed;
}
applyInitialPaneCollapse();

// One-time nudge toward the (now collapsed-by-default) Outline/Inspector edge strips, since
// a 36px chevron is easy for a first-time user to miss entirely.
const PANE_COACH_MARK_KEY = "skaido_seen_pane_coach_mark";
if (!localStorage.getItem(PANE_COACH_MARK_KEY)) paneCoachMark.hidden = false;
paneCoachMarkDismiss.addEventListener("click", () => {
  localStorage.setItem(PANE_COACH_MARK_KEY, "1");
  paneCoachMark.hidden = true;
});

outlineCollapseBtn.addEventListener("click", () => {
  const collapsed = outlinePane.classList.toggle("collapsed");
  editorPanesEl.classList.toggle("outline-collapsed", collapsed);
  outlineCollapseBtn.textContent = collapsed ? "»" : "«";
  outlineCollapseBtn.title = collapsed ? "Expand Outline panel" : "Collapse this panel for a distraction-free canvas";
  localStorage.setItem(OUTLINE_COLLAPSED_KEY, String(collapsed));
});
inspectorCollapseBtn.addEventListener("click", () => {
  const collapsed = inspectorPane.classList.toggle("collapsed");
  editorPanesEl.classList.toggle("inspector-collapsed", collapsed);
  inspectorCollapseBtn.textContent = collapsed ? "«" : "»";
  inspectorCollapseBtn.title = collapsed ? "Expand Inspector panel" : "Collapse this panel for a distraction-free canvas";
  localStorage.setItem(INSPECTOR_COLLAPSED_KEY, String(collapsed));
});

// ---------- Presentation Mode ----------
// Hides all interface chrome down to just the architecture canvas, breadcrumb, and a
// minimal control bar, so the tree can be walked through as a guided story rather than
// shown as a static diagram — reuses the same pane-collapse mechanism as the manual
// collapse buttons rather than a separate hide/show system.
let presentationMode = false;
let prePresentationState = null;

function storyOrder() {
  return collectSubtreeIds(rootId);
}

function presentNextNode() {
  const order = storyOrder();
  const idx = order.indexOf(focusedNodeId);
  if (idx === -1 || idx >= order.length - 1) return;
  focusNode(order[idx + 1]);
}

function presentPrevNode() {
  const order = storyOrder();
  const idx = order.indexOf(focusedNodeId);
  if (idx <= 0) return;
  focusNode(order[idx - 1]);
}

function presentNextLevel() {
  const node = project.nodes[focusedNodeId];
  if (node && node.children.length > 0) focusNode(node.children[0]);
}

function presentPrevLevel() {
  const node = project.nodes[focusedNodeId];
  if (node && node.parent_id) focusNode(node.parent_id);
}

function enterPresentationMode() {
  if (presentationMode || !project) return;
  presentationMode = true;
  prePresentationState = {
    outlineCollapsed: outlinePane.classList.contains("collapsed"),
    inspectorCollapsed: inspectorPane.classList.contains("collapsed"),
  };
  if (!prePresentationState.outlineCollapsed) {
    outlinePane.classList.add("collapsed");
    editorPanesEl.classList.add("outline-collapsed");
  }
  if (!prePresentationState.inspectorCollapsed) {
    inspectorPane.classList.add("collapsed");
    editorPanesEl.classList.add("inspector-collapsed");
  }
  if (viewMode !== "focus") setViewMode("focus");
  document.body.classList.add("presentation-active");
  presentationBar.hidden = false;
  // Collapsing the side panes just changed the canvas's actual pixel width via CSS grid --
  // setViewMode() above only re-renders when the view mode itself changes, which is a no-op
  // if already in Focus Mode (the common case). Without this, the last frame stays positioned
  // for the old, narrower viewport and is invisible in the new, wider one.
  fitToView(false);
}

let storyModeInterval = null;

function stopStoryMode() {
  if (storyModeInterval) {
    clearInterval(storyModeInterval);
    storyModeInterval = null;
  }
  presentStoryBtn.textContent = "▶ Auto-Play";
  presentStoryBtn.classList.remove("active");
}

function toggleStoryMode() {
  if (storyModeInterval) {
    stopStoryMode();
    return;
  }
  presentStoryBtn.textContent = "⏸ Auto-Play";
  presentStoryBtn.classList.add("active");
  storyModeInterval = setInterval(() => {
    const order = storyOrder();
    const idx = order.indexOf(focusedNodeId);
    if (idx === -1 || idx >= order.length - 1) {
      stopStoryMode();
      return;
    }
    focusNode(order[idx + 1]);
  }, 4000);
}

function exitPresentationMode() {
  if (!presentationMode) return;
  presentationMode = false;
  stopStoryMode();
  if (prePresentationState && !prePresentationState.outlineCollapsed) {
    outlinePane.classList.remove("collapsed");
    editorPanesEl.classList.remove("outline-collapsed");
  }
  if (prePresentationState && !prePresentationState.inspectorCollapsed) {
    inspectorPane.classList.remove("collapsed");
    editorPanesEl.classList.remove("inspector-collapsed");
  }
  prePresentationState = null;
  document.body.classList.remove("presentation-active");
  presentationBar.hidden = true;
  // Symmetric with enterPresentationMode() -- restoring the side panes changes the canvas's
  // pixel width back, so the view needs to be re-fit against the new (smaller) size too.
  fitToView(false);
}

presentEnterBtn.addEventListener("click", enterPresentationMode);
presentExitBtn.addEventListener("click", exitPresentationMode);
presentPrevNodeBtn.addEventListener("click", () => {
  stopStoryMode();
  presentPrevNode();
});
presentNextNodeBtn.addEventListener("click", () => {
  stopStoryMode();
  presentNextNode();
});
presentPrevLevelBtn.addEventListener("click", () => {
  stopStoryMode();
  presentPrevLevel();
});
presentNextLevelBtn.addEventListener("click", () => {
  stopStoryMode();
  presentNextLevel();
});
presentBranchBtn.addEventListener("click", fitBranch);
presentZoomTopicBtn.addEventListener("click", () => {
  if (focusedNodeId) zoomToNode(focusedNodeId);
});
presentStoryBtn.addEventListener("click", toggleStoryMode);

document.addEventListener("keydown", (e) => {
  if (!presentationMode) return;
  const activeTag = document.activeElement && document.activeElement.tagName;
  if (activeTag === "INPUT" || activeTag === "TEXTAREA") return;
  if (e.key === "Escape") {
    exitPresentationMode();
  } else if (e.key === "ArrowRight") {
    e.preventDefault();
    stopStoryMode();
    presentNextNode();
  } else if (e.key === "ArrowLeft") {
    e.preventDefault();
    stopStoryMode();
    presentPrevNode();
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    stopStoryMode();
    presentNextLevel();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    stopStoryMode();
    presentPrevLevel();
  } else if (e.key === " ") {
    e.preventDefault();
    toggleStoryMode();
  }
});

// ---------- Health / validation / activity ----------

runValidationBtn.addEventListener("click", refreshHealthPanel);
// Promoted to a full workspace (Phase 9 section 5, WP11e) -- this used to open a modal;
// same content, same renderValidationSummary/renderHealthScore/renderActivityLog calls,
// just a full pane instead of a popup now.
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
  switchToWorkspace("health");
});

// ---------- Keyboard shortcuts modal ----------
// A structured registry, not hardcoded modal HTML, so a future command palette (if ever
// built) can read the same list instead of drifting out of sync with it. `action` is a
// stable id for that future consumer -- nothing here invokes it yet.
const SHORTCUT_REGISTRY = [
  { group: "Navigation & Structure", label: "Promote / demote node", keys: ["Tab", "⇧ Tab"], action: "outdent-indent" },
  { group: "Navigation & Structure", label: "Add sibling below", keys: ["Enter"], action: "add-sibling" },
  { group: "Navigation & Structure", label: "Delete focused node / object", keys: ["Delete"], action: "delete" },
  { group: "Quick Insert", label: "New component", keys: ["N"], action: "insert-node" },
  { group: "Quick Insert", label: "New sticky note", keys: ["S"], action: "insert-sticky-note" },
  { group: "Quick Insert", label: "New text box", keys: ["T"], action: "insert-text" },
  { group: "Quick Insert", label: "New rectangle", keys: ["R"], action: "insert-rectangle" },
  { group: "Edit", label: "Undo", keys: ["Ctrl", "Z"], action: "undo" },
  { group: "Edit", label: "Redo", keys: ["Ctrl", "Shift", "Z"], action: "redo" },
  { group: "Edit", label: "Copy selected object", keys: ["Ctrl", "C"], action: "copy-object" },
  { group: "Edit", label: "Paste object", keys: ["Ctrl", "V"], action: "paste-object" },
  { group: "Selection", label: "Clear selection / close panel", keys: ["Esc"], action: "escape" },
];

function renderShortcutsModal() {
  shortcutsListEl.innerHTML = "";
  let lastGroup = null;
  for (const item of SHORTCUT_REGISTRY) {
    if (item.group !== lastGroup) {
      const groupLabel = document.createElement("div");
      groupLabel.className = "shortcuts-group-label";
      groupLabel.textContent = item.group;
      shortcutsListEl.appendChild(groupLabel);
      lastGroup = item.group;
    }
    const row = document.createElement("div");
    row.className = "shortcuts-row";
    const label = document.createElement("span");
    label.textContent = item.label;
    const keys = document.createElement("span");
    keys.className = "shortcut-keys";
    for (const key of item.keys) {
      const kbd = document.createElement("kbd");
      kbd.textContent = key;
      keys.appendChild(kbd);
    }
    row.appendChild(label);
    row.appendChild(keys);
    shortcutsListEl.appendChild(row);
  }
}
shortcutsBtn.addEventListener("click", () => {
  renderShortcutsModal();
  shortcutsModal.hidden = false;
});
shortcutsCloseBtn.addEventListener("click", () => {
  shortcutsModal.hidden = true;
});
shortcutsModal.addEventListener("click", (e) => {
  if (e.target === shortcutsModal) shortcutsModal.hidden = true;
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
  renderHealthFooter(report);
  if (inspectorActiveTab === "validation") renderInspector();
}

let healthFooterAutoExpandedOnce = false;

healthFooterChip.addEventListener("click", () => {
  const collapsed = healthFooterEl.classList.toggle("chip-collapsed");
  healthFooterChip.title = collapsed ? "Expand the health summary" : "Collapse the health summary";
  healthFooterChevronEl.textContent = collapsed ? "▾" : "▴";
});

// Compact, always-visible summary at the bottom of the Inspector — full detail (per-category
// breakdown, complete change history) only shows up in the modal opened by View Full Report,
// so the Inspector stays focused on the selected node instead of a wall of validation rows.
// The chip row (dot + score) stays visible when collapsed; the detail below it starts
// collapsed each session, EXCEPT it auto-expands once the first time a critical issue shows
// up, so real structural regressions surface instead of hiding quietly behind a closed chip.
function renderHealthFooter(report) {
  healthFooterGaugeEl.innerHTML = "";
  healthFooterGaugeEl.appendChild(buildHealthGauge(report, 48));

  const critical =
    report.duplicate_labels.length +
    report.circular_references.length +
    report.orphan_nodes.length +
    report.broken_references.length;
  const warnings = report.large_modules.length + report.missing_owners.length;
  const suggestions = report.single_child_nodes.length + report.missing_notes.length;

  const ratingClass = "rating-" + report.rating.toLowerCase().replace(/\s+/g, "-");
  healthFooterDotEl.className = "health-footer-dot " + ratingClass;
  healthFooterChipScoreEl.textContent = report.score;

  if (critical > 0 && !healthFooterAutoExpandedOnce) {
    healthFooterAutoExpandedOnce = true;
    healthFooterEl.classList.remove("chip-collapsed");
    healthFooterChip.title = "Collapse the health summary";
    healthFooterChevronEl.textContent = "▴";
  }

  healthFooterSummaryEl.innerHTML = "";
  const rows = [
    [critical === 0 ? "✓" : "⛔", `${critical} Critical Issue${critical === 1 ? "" : "s"}`, critical > 0],
    ["⚠", `${warnings} Warning${warnings === 1 ? "" : "s"}`, warnings > 0],
    ["💡", `${suggestions} Suggestion${suggestions === 1 ? "" : "s"}`, false],
  ];
  for (const [icon, text, flagged] of rows) {
    const row = document.createElement("div");
    row.className = "health-footer-row" + (flagged ? " flagged" : "");
    row.textContent = `${icon} ${text}`;
    healthFooterSummaryEl.appendChild(row);
  }

  healthFooterRecentEl.innerHTML = "";
  const recent = [...project.activity_log].reverse().slice(0, 5);
  if (recent.length > 0) {
    const label = document.createElement("div");
    label.className = "health-footer-recent-label";
    label.textContent = `Recent Changes (last ${recent.length})`;
    healthFooterRecentEl.appendChild(label);
    for (const entry of recent) {
      const item = document.createElement("div");
      item.className = "health-footer-recent-item";
      item.textContent = entry.message;
      healthFooterRecentEl.appendChild(item);
    }
  }
}

// Explains exactly what's driving the score, since a bare number invites "why is this what
// it is" with no way to check — hygiene issues (notes/owners/etc.) are weighted as a % of
// the tree (see build_validation_report in tree.py), so this mirrors that in plain language
// rather than just repeating the raw counts.
function healthScoreExplanation(report) {
  const lines = [
    "Score starts at 100 and subtracts weighted penalties.",
    "Documentation/ownership gaps count as a % of all nodes; structural defects count per instance (capped).",
    "",
    `Duplicate labels: ${report.duplicate_labels.length}`,
    `Circular references: ${report.circular_references.length}`,
    `Large modules (>10 children): ${report.large_modules.length}`,
    `Single-child nodes: ${report.single_child_nodes.length}`,
    `Missing notes: ${report.missing_notes.length}`,
    `Missing owners: ${report.missing_owners.length}`,
    `Orphan nodes: ${report.orphan_nodes.length}`,
    `Broken references: ${report.broken_references.length}`,
  ];
  return lines.join("\n");
}

// Shared by the full-report modal (92px) and the compact Inspector footer (48px) — same
// gauge, just a different size, so the two views never drift into inconsistent visuals.
function buildHealthGauge(report, size) {
  const ratingClass = "rating-" + report.rating.toLowerCase().replace(/\s+/g, "-");
  const stroke = size >= 80 ? 9 : 5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - report.score / 100);

  const gaugeWrap = document.createElement("div");
  gaugeWrap.className = "health-gauge-wrap " + ratingClass + (size < 80 ? " small" : "");
  gaugeWrap.style.width = `${size}px`;
  gaugeWrap.style.height = `${size}px`;
  gaugeWrap.title = healthScoreExplanation(report);

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
  return gaugeWrap;
}

function renderHealthScore(report) {
  const ratingClass = "rating-" + report.rating.toLowerCase().replace(/\s+/g, "-");
  healthScoreEl.className = "health-score " + ratingClass;
  healthScoreEl.innerHTML = "";
  healthScoreEl.appendChild(buildHealthGauge(report, 92));

  const ratingEl = document.createElement("div");
  ratingEl.className = "score-rating";
  ratingEl.textContent = report.rating;
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

// ---------- Clear Canvas ----------
// Resets the project back to just the root node. Destructive and only undoable within the
// current session (undo history isn't persisted across reloads), so it's gated behind a
// type-DELETE-to-confirm modal rather than a plain confirm() dialog.
function closeClearCanvasModal() {
  clearCanvasModal.hidden = true;
}

clearCanvasBtn.addEventListener("click", () => {
  if (!project) return;
  layoutMenu.hidden = true;
  const nodeCount = Object.keys(project.nodes).length - 1; // everything except root
  const refCount = project.references.length;
  const objectCount = project.concept_objects.length;
  clearCanvasSummary.textContent =
    `This will permanently delete ${nodeCount} component${nodeCount === 1 ? "" : "s"}, ` +
    `${refCount} connector${refCount === 1 ? "" : "s"}, and ${objectCount} free object${objectCount === 1 ? "" : "s"}, ` +
    `leaving only the root node.`;
  clearCanvasInput.value = "";
  clearCanvasConfirmBtn.disabled = true;
  clearCanvasModal.hidden = false;
  clearCanvasInput.focus();
});
clearCanvasXBtn.addEventListener("click", closeClearCanvasModal);
clearCanvasCancelBtn.addEventListener("click", closeClearCanvasModal);
clearCanvasInput.addEventListener("input", () => {
  clearCanvasConfirmBtn.disabled = clearCanvasInput.value.trim().toUpperCase() !== "DELETE";
});
clearCanvasInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !clearCanvasConfirmBtn.disabled) clearCanvasConfirmBtn.click();
});
clearCanvasConfirmBtn.addEventListener("click", async () => {
  if (clearCanvasConfirmBtn.disabled) return;
  await fetch(`/api/projects/${projectId}/clear`, { method: "POST" });
  closeClearCanvasModal();
  undoStack = [];
  redoStack = [];
  updateUndoRedoButtons();
  clearSelection();
  selectedConceptObjectId = null;
  focusedNodeId = null;
  await loadProject();
});

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
    // A bulk-imported subtree's default positions come from per-parent grid math applied
    // recursively — reasonable node-by-node, but nothing ties siblings across different
    // parents to a shared per-level row, so a big import reliably looks jumbled until
    // Auto Arrange runs. Run it automatically so the result is never a mess by default.
    await autoArrangeLayout();
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
  const wasHidden = exportMenu.hidden;
  if (wasHidden) closeImportModal();
  layoutMenu.hidden = true;
  settingsMenu.hidden = true;
  shapesFlyout.hidden = true;
  exportMenu.hidden = !wasHidden;
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

// Defuses the biggest discoverability risk of the collapsed-by-default Inspector: the first
// time the user focuses a real (non-root) node, open it for them. A plain in-memory flag, not
// persisted -- it resets every reload, so it fires again each session rather than overriding
// whatever collapse preference the user actually chose last time (see INSPECTOR_COLLAPSED_KEY).
let inspectorAutoExpandedThisSession = false;

function renderInspector() {
  inspectorContent.innerHTML = "";
  if (!project || !focusedNodeId) return;
  const node = project.nodes[focusedNodeId];

  if (focusedNodeId !== rootId && !inspectorAutoExpandedThisSession) {
    inspectorAutoExpandedThisSession = true;
    if (inspectorPane.classList.contains("collapsed")) {
      inspectorPane.classList.remove("collapsed");
      editorPanesEl.classList.remove("inspector-collapsed");
      inspectorCollapseBtn.textContent = "»";
      inspectorCollapseBtn.title = "Collapse this panel for a distraction-free canvas";
    }
  }

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
    ["decompose", "Decompose"],
    ["blueprint", "Blueprint"],
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
  else if (inspectorActiveTab === "decompose") renderDecomposeTab(tabContent, node);
  else if (inspectorActiveTab === "blueprint") renderBlueprintTab(tabContent, node);
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
  infoTable.appendChild(infoRow("Completion Status", infoPlanningStatusValue(node)));
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
    infoRow("Lifecycle Stage", infoSelectValue("status", ["Planned", "In Development", "Done", "Blocked", "Deprecated"], node))
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
      const direction = ref.from === node.id ? "→" : "←";
      const item = document.createElement("div");
      item.className = "ref-list-item";
      const dot = document.createElement("span");
      dot.className = "dot dot-accent";
      const text = document.createElement("span");
      text.className = "ref-text";
      text.textContent = `${direction} ${canvasObjectLabel(otherId)}${ref.label ? " · " + ref.label : ""}`;
      const typeSelect = document.createElement("select");
      typeSelect.className = "ref-type-select";
      typeSelect.title = "Relationship type — colors the connector on the canvas (Dependency=emerald, Warning=amber, Broken=red)";
      for (const opt of ["", "Dependency", "Warning", "Broken"]) {
        const o = document.createElement("option");
        o.value = opt;
        o.textContent = opt || "Reference";
        if ((ref.reference_type || "") === opt) o.selected = true;
        typeSelect.appendChild(o);
      }
      typeSelect.addEventListener("change", async () => {
        await fetch(`/api/projects/${projectId}/references/${ref.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reference_type: typeSelect.value || "" }),
        });
        await loadProject();
      });
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
      item.appendChild(typeSelect);
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
