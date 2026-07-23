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
  renderInspector();
}

async function focusNode(nodeId) {
  focusedNodeId = nodeId;
  panCenterX = null;
  panCenterY = null;
  zoomScale = 1;
  zoomLevelEl.textContent = "100%";
  await expandAncestors(nodeId);
  await loadProject();
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

  if (parent) {
    edgesGroup.appendChild(drawEdge(positions.get(parent.id), positions.get(focus.id), parent.id, focus.id));
  }
  for (const child of children) {
    edgesGroup.appendChild(drawEdge(positions.get(focus.id), positions.get(child.id), focus.id, child.id));
  }

  const tagCounters = new Map();
  for (const ref of project.references) {
    const fromVisible = visibleIds.has(ref.from);
    const toVisible = visibleIds.has(ref.to);
    if (fromVisible && toVisible) {
      refGroup.appendChild(drawRefEdge(positions.get(ref.from), positions.get(ref.to), ref.from, ref.to));
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
  for (const child of children) {
    nodesGroup.appendChild(drawNode(child, positions.get(child.id)));
  }

  viewport.appendChild(edgesGroup);
  viewport.appendChild(refGroup);
  viewport.appendChild(nodesGroup);
  canvasSvg.appendChild(viewport);

  canvasSvg.ondblclick = (e) => {
    if (e.target !== canvasSvg || refMode) return;
    handleCanvasDblClick(e, centerX, centerY, viewW, viewH);
  };
}

function drawEdge(from, to, fromId, toId) {
  const line = document.createElementNS(SVG_NS, "line");
  line.setAttribute("class", "edge");
  line.setAttribute("x1", from.x);
  line.setAttribute("y1", from.y);
  line.setAttribute("x2", to.x);
  line.setAttribute("y2", to.y);
  line.dataset.fromId = fromId;
  line.dataset.toId = toId;
  return line;
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

function drawRefEdge(from, to, fromId, toId) {
  const line = document.createElementNS(SVG_NS, "line");
  line.setAttribute("class", "ref-edge");
  line.setAttribute("x1", from.x);
  line.setAttribute("y1", from.y);
  line.setAttribute("x2", to.x);
  line.setAttribute("y2", to.y);
  line.setAttribute("marker-end", "url(#refArrow)");
  line.dataset.fromId = fromId;
  line.dataset.toId = toId;
  return line;
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

function drawNode(node, pos) {
  const group = document.createElementNS(SVG_NS, "g");
  const classes = ["node-group"];
  if (node.id === focusedNodeId) classes.push("focused");
  if (node.id === pendingRefFrom) classes.push("ref-pending");
  group.setAttribute("class", classes.join(" "));
  group.dataset.id = node.id;

  const box = document.createElementNS(SVG_NS, "rect");
  box.setAttribute("class", "node-box");
  box.setAttribute("x", pos.x - NODE_W / 2);
  box.setAttribute("y", pos.y - NODE_H / 2);
  box.setAttribute("width", NODE_W);
  box.setAttribute("height", NODE_H);
  box.setAttribute("rx", Math.max(4, 16 - (node.level - 1) * 2));

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
      startDrag(e, node, group);
    }
  });

  return group;
}

function startDrag(e, node, group) {
  e.preventDefault();
  const startX = e.clientX;
  const startY = e.clientY;

  const relatedEdges = Array.from(canvasSvg.querySelectorAll(".edge, .ref-edge")).filter(
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
    origScreenX: parseFloat(group.querySelector(".node-box").getAttribute("x")) + NODE_W / 2,
    origScreenY: parseFloat(group.querySelector(".node-box").getAttribute("y")) + NODE_H / 2,
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
    const box = dragState.group.querySelector(".node-box");
    const label = dragState.group.querySelector(".node-label");
    const dot = dragState.group.querySelector(".warning-dot");
    const newCenterX = parseFloat(box.getAttribute("x")) + NODE_W / 2 + dx - (dragState.appliedDx || 0);
    const newCenterY = parseFloat(box.getAttribute("y")) + NODE_H / 2 + dy - (dragState.appliedDy || 0);
    box.setAttribute("x", newCenterX - NODE_W / 2);
    box.setAttribute("y", newCenterY - NODE_H / 2);
    label.setAttribute("x", newCenterX);
    label.setAttribute("y", newCenterY);
    if (dot) {
      dot.setAttribute("cx", newCenterX + NODE_W / 2 - 6);
      dot.setAttribute("cy", newCenterY - NODE_H / 2 + 6);
    }
    for (const edge of dragState.relatedEdges) {
      if (edge.dataset.fromId === node.id) {
        edge.setAttribute("x1", newCenterX);
        edge.setAttribute("y1", newCenterY);
      }
      if (edge.dataset.toId === node.id) {
        edge.setAttribute("x2", newCenterX);
        edge.setAttribute("y2", newCenterY);
      }
    }
    const totalDx = newCenterX - dragState.origScreenX;
    const totalDy = newCenterY - dragState.origScreenY;
    for (const tag of dragState.relatedTags) {
      tag.setAttribute("transform", `translate(${totalDx} ${totalDy})`);
    }
    dragState.appliedDx = dx;
    dragState.appliedDy = dy;
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
    if (!project) return;
    e.preventDefault();
    setZoom(zoomScale + (e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP));
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

function renderInspector() {
  inspectorContent.innerHTML = "";
  if (!project || !focusedNodeId) return;
  const node = project.nodes[focusedNodeId];

  // Label
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
  inspectorContent.appendChild(labelField);

  // Meta
  const parentNode = node.parent_id ? project.nodes[node.parent_id] : null;
  inspectorContent.appendChild(metaRow("Level", node.level));
  inspectorContent.appendChild(metaRow("Parent", parentNode ? parentNode.label : "— (root)"));
  inspectorContent.appendChild(metaRow("Children", node.children.length));

  // Quick structure actions
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
    const delBtn = mkBtn("Delete", "Delete this node", () => deleteNodeFlow(focusedNodeId));
    delBtn.classList.add("btn-danger");
    btnRow.appendChild(delBtn);
  }
  inspectorContent.appendChild(btnRow);
  inspectorContent.appendChild(document.createElement("hr")).className = "inspector-divider";

  // Notes
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

  // Warnings
  for (const warning of computeWarnings(node)) {
    const box = document.createElement("div");
    box.className = "warning-box";
    box.textContent = warning;
    inspectorContent.appendChild(box);
  }

  // References touching this node
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
    const refsField = field("References");
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
      refsField.appendChild(item);
    }
    inspectorContent.appendChild(refsField);
  }

  inspectorContent.appendChild(document.createElement("hr")).className = "inspector-divider";

  // Templates
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
  inspectorContent.appendChild(templateField);

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
