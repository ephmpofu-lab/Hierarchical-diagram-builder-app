const params = new URLSearchParams(window.location.search);
const projectId = params.get("project");

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
const arrangeChildrenBtn = document.getElementById("arrangeChildrenBtn");
const groupChildrenBtn = document.getElementById("groupChildrenBtn");
const shapeBtn = document.getElementById("shapeBtn");
const shapePicker = document.getElementById("shapePicker");
const minimapSvg = document.getElementById("minimapSvg");
const healthToggleBtn = document.getElementById("healthToggleBtn");
const healthPanel = document.getElementById("healthPanel");
const healthCloseBtn = document.getElementById("healthCloseBtn");
const healthScoreEl = document.getElementById("healthScore");
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
let dragState = null;
let zoomScale = 1;
let refMode = false;
let pendingRefFrom = null;
let panCenterX = null;
let panCenterY = null;
let selectedEdgeKey = null; // "ref:<refId>" or "tree:<childId>"
let lastVisiblePositions = new Map();
let lastViewW = 800;
let lastViewH = 500;

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
  panCenterX = null;
  panCenterY = null;
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
  label.textContent = node.label;
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

function renderCanvas() {
  canvasSvg.innerHTML = "";
  canvasSvg.classList.toggle("ref-mode-active", refMode);
  canvasSvg.appendChild(buildRefArrowDefs());
  if (!project || !focusedNodeId) return;

  const focus = project.nodes[focusedNodeId];
  const parent = focus.parent_id ? project.nodes[focus.parent_id] : null;
  const children = focus.children.map((id) => project.nodes[id]);
  const visible = [focus, ...(parent ? [parent] : []), ...children];
  const visibleIds = new Set(visible.map((n) => n.id));

  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;
  const centerX = panCenterX !== null ? panCenterX : focus.canvas_x;
  const centerY = panCenterY !== null ? panCenterY : focus.canvas_y;

  const toScreen = (node) => ({
    x: viewW / 2 + (node.canvas_x - centerX),
    y: viewH / 2 + (node.canvas_y - centerY),
  });
  const positions = new Map(visible.map((n) => [n.id, toScreen(n)]));

  const viewport = document.createElementNS(SVG_NS, "g");
  viewport.setAttribute(
    "transform",
    `translate(${viewW / 2} ${viewH / 2}) scale(${zoomScale}) translate(${-viewW / 2} ${-viewH / 2})`
  );

  const edgesGroup = document.createElementNS(SVG_NS, "g");
  const refGroup = document.createElementNS(SVG_NS, "g");
  const nodesGroup = document.createElementNS(SVG_NS, "g");

  const groupedMode = focus.group_children && children.length > 0;
  groupChildrenBtn.classList.toggle("active", !!focus.group_children);

  if (parent) {
    const parentPos = positions.get(parent.id);
    const focusPos = positions.get(focus.id);
    edgesGroup.appendChild(drawTreeEdge(parentPos, focusPos, parent.id, focus.id));
    if (selectedEdgeKey === edgeKey("tree", focus.id)) {
      edgesGroup.appendChild(drawTreeHandle(parentPos, focus.id, focusPos));
      edgesGroup.appendChild(drawTreeHandle(focusPos, focus.id, parentPos));
    }
  }

  let groupBox = null;
  if (groupedMode) {
    groupBox = drawGroupedChildrenBox(focus, positions.get(focus.id), children);
    edgesGroup.appendChild(drawTreeEdge(positions.get(focus.id), groupBox.anchor, focus.id, null));
  } else {
    for (const child of children) {
      const focusPos = positions.get(focus.id);
      const childPos = positions.get(child.id);
      edgesGroup.appendChild(drawTreeEdge(focusPos, childPos, focus.id, child.id));
      if (selectedEdgeKey === edgeKey("tree", child.id)) {
        edgesGroup.appendChild(drawTreeHandle(focusPos, child.id, childPos));
        edgesGroup.appendChild(drawTreeHandle(childPos, child.id, focusPos));
      }
    }
  }

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

  if (parent) nodesGroup.appendChild(drawNode(parent, positions.get(parent.id)));
  nodesGroup.appendChild(drawNode(focus, positions.get(focus.id)));
  if (groupedMode) {
    nodesGroup.appendChild(groupBox.group);
  } else {
    for (const child of children) {
      nodesGroup.appendChild(drawNode(child, positions.get(child.id)));
    }
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
  canvasSvg.ondblclick = (e) => {
    if (e.target !== canvasSvg || refMode) return;
    handleCanvasDblClick(e, centerX, centerY, viewW, viewH);
  };
}

function edgeKey(kind, id) {
  return `${kind}:${id}`;
}

function drawTreeEdge(from, to, fromId, toId) {
  const group = document.createElementNS(SVG_NS, "g");
  const key = toId ? edgeKey("tree", toId) : null;

  const hit = document.createElementNS(SVG_NS, "path");
  hit.setAttribute("class", "edge-hit");
  hit.setAttribute("d", curvePath(from, to));

  const line = document.createElementNS(SVG_NS, "path");
  line.setAttribute("class", "edge" + (key && selectedEdgeKey === key ? " selected" : ""));
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

function drawShapeEl(node, pos) {
  const shape = node.shape || "rect";
  const w = NODE_W;
  const h = NODE_H;
  const cx = pos.x;
  const cy = pos.y;

  if (shape === "diamond") {
    const el = document.createElementNS(SVG_NS, "polygon");
    el.setAttribute(
      "points",
      `${cx},${cy - h / 2} ${cx + w / 2},${cy} ${cx},${cy + h / 2} ${cx - w / 2},${cy}`
    );
    return el;
  }
  if (shape === "hexagon") {
    const inset = w * 0.2;
    const el = document.createElementNS(SVG_NS, "polygon");
    el.setAttribute(
      "points",
      `${cx - w / 2 + inset},${cy - h / 2} ${cx + w / 2 - inset},${cy - h / 2} ${cx + w / 2},${cy} ` +
        `${cx + w / 2 - inset},${cy + h / 2} ${cx - w / 2 + inset},${cy + h / 2} ${cx - w / 2},${cy}`
    );
    return el;
  }
  if (shape === "ellipse") {
    const el = document.createElementNS(SVG_NS, "ellipse");
    el.setAttribute("cx", cx);
    el.setAttribute("cy", cy);
    el.setAttribute("rx", w / 2);
    el.setAttribute("ry", h / 2);
    return el;
  }
  const el = document.createElementNS(SVG_NS, "rect");
  el.setAttribute("x", cx - w / 2);
  el.setAttribute("y", cy - h / 2);
  el.setAttribute("width", w);
  el.setAttribute("height", h);
  el.setAttribute("rx", shape === "pill" ? h / 2 : Math.max(4, 16 - (node.level - 1) * 2));
  return el;
}

function drawGroupedChildrenBox(focus, focusPos, children) {
  const perRow = 3;
  const innerW = 120;
  const innerH = 34;
  const gapX = 10;
  const gapY = 8;
  const padding = 14;
  const headerH = 24;
  const cols = Math.min(perRow, children.length);
  const rows = Math.ceil(children.length / perRow);
  const boxW = cols * innerW + (cols - 1) * gapX + padding * 2;
  const boxH = headerH + rows * innerH + (rows - 1) * gapY + padding * 2;
  const boxX = focusPos.x - boxW / 2;
  const boxY = focusPos.y + 150;

  const group = document.createElementNS(SVG_NS, "g");
  group.setAttribute("class", "group-box");

  const rect = document.createElementNS(SVG_NS, "rect");
  rect.setAttribute("class", "group-box-rect");
  rect.setAttribute("x", boxX);
  rect.setAttribute("y", boxY);
  rect.setAttribute("width", boxW);
  rect.setAttribute("height", boxH);
  rect.setAttribute("rx", 10);
  group.appendChild(rect);

  const title = document.createElementNS(SVG_NS, "text");
  title.setAttribute("class", "group-box-title");
  title.setAttribute("x", boxX + padding);
  title.setAttribute("y", boxY + padding + 2);
  title.textContent = `${children.length} item${children.length === 1 ? "" : "s"}`;
  group.appendChild(title);

  children.forEach((child, i) => {
    const row = Math.floor(i / perRow);
    const col = i % perRow;
    const cx = boxX + padding + col * (innerW + gapX);
    const cy = boxY + headerH + padding + row * (innerH + gapY);

    const childGroup = document.createElementNS(SVG_NS, "g");
    childGroup.setAttribute("class", "group-box-item" + (child.id === focusedNodeId ? " focused" : ""));

    const childRect = document.createElementNS(SVG_NS, "rect");
    childRect.setAttribute("x", cx);
    childRect.setAttribute("y", cy);
    childRect.setAttribute("width", innerW);
    childRect.setAttribute("height", innerH);
    childRect.setAttribute("rx", 6);

    const childLabel = document.createElementNS(SVG_NS, "text");
    childLabel.setAttribute("x", cx + innerW / 2);
    childLabel.setAttribute("y", cy + innerH / 2);
    const maxChars = 16;
    childLabel.textContent = child.label.length > maxChars ? child.label.slice(0, maxChars - 1) + "…" : child.label;

    childGroup.appendChild(childRect);
    childGroup.appendChild(childLabel);
    childGroup.addEventListener("click", (e) => {
      e.stopPropagation();
      focusNode(child.id);
    });
    group.appendChild(childGroup);
  });

  return { group, anchor: { x: boxX + boxW / 2, y: boxY } };
}

function drawNode(node, pos) {
  const group = document.createElementNS(SVG_NS, "g");
  const classes = ["node-group"];
  if (node.id === focusedNodeId) classes.push("focused");
  if (node.id === pendingRefFrom) classes.push("ref-pending");
  group.setAttribute("class", classes.join(" "));
  group.dataset.id = node.id;

  const box = drawShapeEl(node, pos);
  box.setAttribute("class", "node-box");

  const label = document.createElementNS(SVG_NS, "text");
  label.setAttribute("class", "node-label");
  label.setAttribute("x", pos.x);
  label.setAttribute("y", pos.y);
  const maxChars = 20;
  label.textContent = node.label.length > maxChars ? node.label.slice(0, maxChars - 1) + "…" : node.label;

  group.appendChild(box);
  group.appendChild(label);

  if (computeWarnings(node).length > 0) {
    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("class", "warning-dot");
    dot.setAttribute("cx", pos.x + NODE_W / 2 - 6);
    dot.setAttribute("cy", pos.y - NODE_H / 2 + 6);
    dot.setAttribute("r", 4);
    group.appendChild(dot);
  }

  group.addEventListener("mousedown", (e) => {
    if (refMode) {
      e.preventDefault();
      e.stopPropagation();
      handleRefModeClick(node.id);
    } else {
      startDrag(e, node, group, pos);
    }
  });

  return group;
}

function startDrag(e, node, group, origPos) {
  e.preventDefault();
  const startX = e.clientX;
  const startY = e.clientY;

  const relatedEdges = Array.from(canvasSvg.querySelectorAll("[data-from-id], [data-to-id]")).filter(
    (el) => el.dataset.fromId === node.id || el.dataset.toId === node.id
  );
  const relatedTags = Array.from(canvasSvg.querySelectorAll(".ref-tag")).filter(
    (el) => el.dataset.anchorId === node.id
  );

  dragState = {
    nodeId: node.id,
    group,
    startX,
    startY,
    origX: node.canvas_x,
    origY: node.canvas_y,
    origScreenX: origPos.x,
    origScreenY: origPos.y,
    relatedEdges,
    relatedTags,
    moved: false,
  };

  const onMove = (moveEvent) => {
    if (!dragState) return;
    const rawDx = moveEvent.clientX - dragState.startX;
    const rawDy = moveEvent.clientY - dragState.startY;
    if (Math.abs(rawDx) > 3 || Math.abs(rawDy) > 3) dragState.moved = true;
    if (!dragState.moved) return;
    const dx = rawDx / zoomScale;
    const dy = rawDy / zoomScale;
    dragState.group.classList.add("dragging");
    dragState.group.setAttribute("transform", `translate(${dx} ${dy})`);

    const newCenterX = dragState.origScreenX + dx;
    const newCenterY = dragState.origScreenY + dy;
    for (const edge of dragState.relatedEdges) {
      const x1 = edge.dataset.fromId === node.id ? newCenterX : parseFloat(edge.dataset.x1);
      const y1 = edge.dataset.fromId === node.id ? newCenterY : parseFloat(edge.dataset.y1);
      const x2 = edge.dataset.toId === node.id ? newCenterX : parseFloat(edge.dataset.x2);
      const y2 = edge.dataset.toId === node.id ? newCenterY : parseFloat(edge.dataset.y2);
      const paths = edge.querySelectorAll("path");
      const d = curvePath({ x: x1, y: y1 }, { x: x2, y: y2 });
      for (const p of paths) p.setAttribute("d", d);
    }
    for (const tag of dragState.relatedTags) {
      tag.setAttribute("transform", `translate(${dx} ${dy})`);
    }
    dragState.finalDx = dx;
    dragState.finalDy = dy;
  };

  const onUp = async () => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    if (!dragState) return;
    const { nodeId, moved, origX, origY, finalDx, finalDy } = dragState;
    dragState = null;
    if (!moved) {
      await focusNode(nodeId);
      return;
    }
    const newX = origX + finalDx;
    const newY = origY + finalDy;
    await fetch(`/api/projects/${projectId}/nodes/${nodeId}/position`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canvas_x: newX, canvas_y: newY }),
    });
    await loadProject();
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

async function handleCanvasDblClick(e, centerX, centerY, viewW, viewH) {
  const rect = canvasSvg.getBoundingClientRect();
  const screenX = e.clientX - rect.left;
  const screenY = e.clientY - rect.top;
  const canvasX = centerX + (screenX - viewW / 2) / zoomScale;
  const canvasY = centerY + (screenY - viewH / 2) / zoomScale;

  const focus = project.nodes[focusedNodeId];
  const parentId = focus.parent_id !== null ? focus.parent_id : focus.id;

  const res = await fetch(`/api/projects/${projectId}/nodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_id: parentId, label: "New node" }),
  });
  const newNode = await res.json();

  await fetch(`/api/projects/${projectId}/nodes/${newNode.id}/position`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ canvas_x: canvasX, canvas_y: canvasY }),
  });

  focusedNodeId = newNode.id;
  await loadProject();
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
    const focus = project.nodes[focusedNodeId];
    const baseX = panCenterX !== null ? panCenterX : focus.canvas_x;
    const baseY = panCenterY !== null ? panCenterY : focus.canvas_y;
    panCenterX = baseX + e.deltaX / zoomScale;
    panCenterY = baseY + e.deltaY / zoomScale;
    renderCanvas();
  },
  { passive: false }
);

function fitToView() {
  if (!project || !focusedNodeId) return;
  const focus = project.nodes[focusedNodeId];
  const parent = focus.parent_id ? project.nodes[focus.parent_id] : null;
  const children = focus.children.map((id) => project.nodes[id]);
  const visible = [focus, ...(parent ? [parent] : []), ...children];

  const xs = visible.map((n) => n.canvas_x);
  const ys = visible.map((n) => n.canvas_y);
  const minX = Math.min(...xs) - NODE_W / 2;
  const maxX = Math.max(...xs) + NODE_W / 2;
  const minY = Math.min(...ys) - NODE_H / 2;
  const maxY = Math.max(...ys) + NODE_H / 2;
  const boxW = Math.max(maxX - minX, 1);
  const boxH = Math.max(maxY - minY, 1);

  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;
  const padding = 70;

  const scale = Math.min((viewW - padding * 2) / boxW, (viewH - padding * 2) / boxH, ZOOM_MAX);
  zoomScale = Math.max(0.05, scale);
  panCenterX = (minX + maxX) / 2;
  panCenterY = (minY + maxY) / 2;
  zoomLevelEl.textContent = `${Math.round(zoomScale * 100)}%`;
  renderCanvas();
}

fitViewBtn.addEventListener("click", fitToView);

arrangeChildrenBtn.addEventListener("click", async () => {
  if (!focusedNodeId) return;
  await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}/arrange-children`, { method: "POST" });
  await loadProject();
  fitToView();
});

groupChildrenBtn.addEventListener("click", async () => {
  if (!focusedNodeId || !project) return;
  const node = project.nodes[focusedNodeId];
  await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ group_children: !node.group_children }),
  });
  await loadProject();
  fitToView();
});

shapeBtn.addEventListener("click", () => {
  shapePicker.hidden = !shapePicker.hidden;
});
shapePicker.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-shape]");
  if (!btn || !focusedNodeId) return;
  shapePicker.hidden = true;
  await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shape: btn.dataset.shape }),
  });
  await loadProject();
});
document.addEventListener("click", (e) => {
  if (!shapePicker.hidden && !shapePicker.contains(e.target) && e.target !== shapeBtn) {
    shapePicker.hidden = true;
  }
});

// ---------- Minimap ----------

function renderMinimap() {
  minimapSvg.innerHTML = "";
  if (!project || !focusedNodeId) return;

  const allNodes = Object.values(project.nodes);
  const xs = allNodes.map((n) => n.canvas_x);
  const ys = allNodes.map((n) => n.canvas_y);
  const minX = Math.min(...xs) - NODE_W / 2;
  const maxX = Math.max(...xs) + NODE_W / 2;
  const minY = Math.min(...ys) - NODE_H / 2;
  const maxY = Math.max(...ys) + NODE_H / 2;
  const treeW = Math.max(maxX - minX, 1);
  const treeH = Math.max(maxY - minY, 1);

  const mapW = 160;
  const mapH = 100;
  const pad = 8;
  const scale = Math.min((mapW - pad * 2) / treeW, (mapH - pad * 2) / treeH);

  const toMini = (x, y) => ({
    x: pad + (x - minX) * scale,
    y: pad + (y - minY) * scale,
  });

  const focus = project.nodes[focusedNodeId];
  const rect = canvasSvg.getBoundingClientRect();
  const viewW = rect.width || 800;
  const viewH = rect.height || 500;
  const centerX = panCenterX !== null ? panCenterX : focus.canvas_x;
  const centerY = panCenterY !== null ? panCenterY : focus.canvas_y;
  const viewportWorldW = viewW / zoomScale;
  const viewportWorldH = viewH / zoomScale;
  const vpTopLeft = toMini(centerX - viewportWorldW / 2, centerY - viewportWorldH / 2);
  const vpBottomRight = toMini(centerX + viewportWorldW / 2, centerY + viewportWorldH / 2);

  const viewportRect = document.createElementNS(SVG_NS, "rect");
  viewportRect.setAttribute("class", "mini-viewport");
  viewportRect.setAttribute("x", vpTopLeft.x);
  viewportRect.setAttribute("y", vpTopLeft.y);
  viewportRect.setAttribute("width", Math.max(2, vpBottomRight.x - vpTopLeft.x));
  viewportRect.setAttribute("height", Math.max(2, vpBottomRight.y - vpTopLeft.y));
  viewportRect.addEventListener("click", (e) => {
    const svgRect = minimapSvg.getBoundingClientRect();
    const clickX = e.clientX - svgRect.left;
    const clickY = e.clientY - svgRect.top;
    const worldX = minX + (clickX - pad) / scale;
    const worldY = minY + (clickY - pad) / scale;
    panCenterX = worldX;
    panCenterY = worldY;
    renderCanvas();
    renderMinimap();
  });

  for (const node of allNodes) {
    const pos = toMini(node.canvas_x, node.canvas_y);
    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("class", "mini-node" + (node.id === focusedNodeId ? " focused" : ""));
    dot.setAttribute("cx", pos.x);
    dot.setAttribute("cy", pos.y);
    dot.setAttribute("r", node.id === focusedNodeId ? 3 : 2);
    minimapSvg.appendChild(dot);
  }

  minimapSvg.appendChild(viewportRect);
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

async function refreshHealthPanel() {
  if (!project) return;
  const res = await fetch(`/api/projects/${projectId}/validation`);
  if (!res.ok) return;
  const report = await res.json();
  renderHealthScore(report);
  renderValidationSummary(report);
  renderActivityLog();
}

function renderHealthScore(report) {
  const ratingClass = "rating-" + report.rating.toLowerCase().replace(/\s+/g, "-");
  healthScoreEl.className = "health-score " + ratingClass;
  healthScoreEl.innerHTML = "";
  const scoreEl = document.createElement("div");
  scoreEl.className = "score-number";
  scoreEl.textContent = `${report.score}%`;
  const ratingEl = document.createElement("div");
  ratingEl.className = "score-rating";
  ratingEl.textContent = report.rating;
  healthScoreEl.appendChild(scoreEl);
  healthScoreEl.appendChild(ratingEl);
}

function renderValidationSummary(report) {
  validationSummaryEl.innerHTML = "";
  const rows = [
    ["Duplicate labels", report.duplicate_labels.length],
    ["Circular references", report.circular_references.length],
    ["Large modules (>10 children)", report.large_modules.length],
    ["Single-child nodes", report.single_child_nodes.length],
    ["Missing notes", report.missing_notes_count],
  ];
  for (const [label, count] of rows) {
    const row = document.createElement("div");
    row.className = "validation-row" + (count > 0 ? " flagged" : "");
    const l = document.createElement("span");
    l.textContent = label;
    const v = document.createElement("strong");
    v.textContent = count;
    row.appendChild(l);
    row.appendChild(v);
    validationSummaryEl.appendChild(row);
  }
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

function metaRow(labelText, value) {
  const row = document.createElement("div");
  row.className = "meta-row";
  const l = document.createElement("span");
  l.textContent = labelText;
  const v = document.createElement("strong");
  v.textContent = value;
  row.appendChild(l);
  row.appendChild(v);
  return row;
}

const inspectorCollapseState = { metadata: true, comments: true, templates: true };

function collapsibleSection(key, title, buildFn) {
  const section = document.createElement("div");
  section.className = "insp-section";

  const collapsed = !!inspectorCollapseState[key];
  const header = document.createElement("div");
  header.className = "insp-section-header";
  const arrow = document.createElement("span");
  arrow.className = "insp-section-arrow";
  arrow.textContent = collapsed ? "▸" : "▾";
  const titleEl = document.createElement("span");
  titleEl.textContent = title;
  header.appendChild(arrow);
  header.appendChild(titleEl);
  header.addEventListener("click", () => {
    inspectorCollapseState[key] = !collapsed;
    renderInspector();
  });
  section.appendChild(header);

  if (!collapsed) {
    const body = document.createElement("div");
    body.className = "insp-section-body";
    buildFn(body);
    section.appendChild(body);
  }
  return section;
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

function metaSelectField(fieldKey, labelText, options, node) {
  const wrap = field(labelText);
  const row = document.createElement("div");
  row.className = "meta-select-row";
  const dot = document.createElement("span");
  dot.className = `dot ${dotClassFor(fieldKey, node[fieldKey])}`;
  const select = document.createElement("select");
  select.className = "label-input";
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
  row.appendChild(dot);
  row.appendChild(select);
  wrap.appendChild(row);
  return wrap;
}

function renderInspector() {
  inspectorContent.innerHTML = "";
  if (!project || !focusedNodeId) return;
  const node = project.nodes[focusedNodeId];

  // ---- Sticky header: always visible while scrolling, so Notes/Comments/etc never
  // lose their "which node is this?" context. ----
  const header = document.createElement("div");
  header.className = "inspector-sticky-header";

  const labelField = field("Label");
  const labelInput = document.createElement("input");
  labelInput.className = "label-input";
  labelInput.value = node.label;
  labelInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") labelInput.blur();
  });
  labelInput.addEventListener("blur", async () => {
    const trimmed = labelInput.value.trim();
    if (trimmed && trimmed !== node.label) {
      await fetch(`/api/projects/${projectId}/nodes/${focusedNodeId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: trimmed }),
      });
      await loadProject();
    }
  });
  labelField.appendChild(labelInput);
  header.appendChild(labelField);

  const parentNode = node.parent_id ? project.nodes[node.parent_id] : null;
  header.appendChild(metaRow("Level", node.level));
  header.appendChild(metaRow("Parent", parentNode ? parentNode.label : "— (root)"));
  header.appendChild(metaRow("Children", node.children.length));

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
  header.appendChild(btnRow);
  inspectorContent.appendChild(header);

  // ---- Notes (always visible — most-used field) ----
  const notesField = field("Notes");
  const textarea = document.createElement("textarea");
  textarea.rows = 4;
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
  inspectorContent.appendChild(notesField);

  // Warnings (always visible when present — they're alerts, not reference material)
  for (const warning of computeWarnings(node)) {
    const box = document.createElement("div");
    box.className = "warning-box";
    box.textContent = warning;
    inspectorContent.appendChild(box);
  }

  // ---- Metadata (collapsible) ----
  inspectorContent.appendChild(
    collapsibleSection("metadata", "Metadata", (body) => {
      const typeField = field("Node type");
      const typeInput = document.createElement("input");
      typeInput.className = "label-input";
      typeInput.placeholder = "e.g. Decision Engine";
      typeInput.value = node.node_type || "";
      typeInput.addEventListener("blur", async () => {
        if (typeInput.value !== (node.node_type || "")) {
          await patchNode({ node_type: typeInput.value });
        }
      });
      typeField.appendChild(typeInput);
      body.appendChild(typeField);

      body.appendChild(
        metaSelectField("status", "Status", ["Planned", "In Development", "Done", "Blocked", "Deprecated"], node)
      );
      body.appendChild(metaSelectField("priority", "Priority", ["Low", "Medium", "High", "Critical"], node));
      body.appendChild(metaSelectField("complexity", "Complexity", ["Low", "Medium", "High"], node));
      body.appendChild(metaSelectField("risk_level", "Risk level", ["Low", "Medium", "High", "Critical"], node));

      const ownerField = field("Owner");
      const ownerInput = document.createElement("input");
      ownerInput.className = "label-input";
      ownerInput.placeholder = "e.g. your name or team";
      ownerInput.value = node.owner || "";
      ownerInput.addEventListener("blur", async () => {
        if (ownerInput.value !== (node.owner || "")) {
          await patchNode({ owner: ownerInput.value });
        }
      });
      ownerField.appendChild(ownerInput);
      body.appendChild(ownerField);

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
      body.appendChild(tagsField);
    })
  );

  // ---- References (collapsible) ----
  const touchingRefs = project.references.filter((r) => r.from === node.id || r.to === node.id);
  const subtreeIds = new Set(collectSubtreeIds(node.id));
  const outsideCount = touchingRefs.filter((r) => {
    const other = r.from === node.id ? r.to : r.from;
    return !subtreeIds.has(other);
  }).length;

  if (outsideCount > 0) {
    const badge = document.createElement("div");
    badge.className = "ref-badge";
    badge.textContent = `${outsideCount} reference link${outsideCount === 1 ? "" : "s"} outside this subtree`;
    inspectorContent.appendChild(badge);
  }

  if (touchingRefs.length > 0) {
    inspectorContent.appendChild(
      collapsibleSection(`references-${node.id}`, `References (${touchingRefs.length})`, (body) => {
        for (const ref of touchingRefs) {
          const otherId = ref.from === node.id ? ref.to : ref.from;
          const otherNode = project.nodes[otherId];
          const direction = ref.from === node.id ? "→" : "←";
          const item = document.createElement("div");
          item.className = "ref-list-item";
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
          item.appendChild(text);
          item.appendChild(delBtn);
          body.appendChild(item);
        }
      })
    );
  }

  // ---- Comments (collapsible) ----
  inspectorContent.appendChild(
    collapsibleSection("comments", `Comments${node.comments.length ? ` (${node.comments.length})` : ""}`, (body) => {
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
        body.appendChild(item);
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
      body.appendChild(commentInput);
    })
  );

  // ---- Templates (collapsible) ----
  inspectorContent.appendChild(
    collapsibleSection("templates", "Templates", (body) => {
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
      body.appendChild(saveTplBtn);

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
      body.appendChild(applyRow);

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
    })
  );
}
