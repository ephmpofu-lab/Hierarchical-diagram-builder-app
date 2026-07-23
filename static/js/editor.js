const params = new URLSearchParams(window.location.search);
const projectId = params.get("project");

const outlineTree = document.getElementById("outlineTree");
const projectNameEl = document.getElementById("projectName");

let project = null;
let rootId = null;
let focusedNodeId = null;
let editingNodeId = null;

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
    focusedNodeId = nodeId;
    render();
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
