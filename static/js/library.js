const grid = document.getElementById("projectGrid");
const emptyState = document.getElementById("emptyState");
const newProjectBtn = document.getElementById("newProjectBtn");
const importOutlineBtn = document.getElementById("importOutlineBtn");
const importModal = document.getElementById("importModal");
const importText = document.getElementById("importText");
const importCancelBtn = document.getElementById("importCancelBtn");
const importConfirmBtn = document.getElementById("importConfirmBtn");

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function fetchProjects() {
  const res = await fetch("/api/projects");
  if (!res.ok) throw new Error("Failed to load projects");
  return res.json();
}

function renderProjects(projects) {
  grid.innerHTML = "";
  if (projects.length === 0) {
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  for (const project of projects) {
    const card = document.createElement("div");
    card.className = "project-card";

    const name = document.createElement("div");
    name.className = "name";
    name.textContent = project.name;
    name.title = "Open project";
    name.addEventListener("click", () => {
      window.location.href = `editor.html?project=${project.id}`;
    });

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${project.node_count} node${project.node_count === 1 ? "" : "s"} · updated ${formatDate(project.updated_at)}`;

    const actions = document.createElement("div");
    actions.className = "actions";

    const renameBtn = document.createElement("button");
    renameBtn.className = "btn btn-small";
    renameBtn.textContent = "Rename";
    renameBtn.addEventListener("click", () => renameProject(project));

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "btn btn-small btn-danger";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", () => deleteProject(project));

    actions.appendChild(renameBtn);
    actions.appendChild(deleteBtn);

    card.appendChild(name);
    card.appendChild(meta);
    card.appendChild(actions);
    grid.appendChild(card);
  }
}

async function loadAndRender() {
  const projects = await fetchProjects();
  renderProjects(projects);
}

async function createProject() {
  const name = prompt("Name for the new project:");
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) return;

  const res = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: trimmed }),
  });
  if (!res.ok) {
    alert("Failed to create project.");
    return;
  }
  const project = await res.json();
  window.location.href = `editor.html?project=${project.id}`;
}

async function renameProject(project) {
  const name = prompt("Rename project:", project.name);
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed || trimmed === project.name) return;

  const res = await fetch(`/api/projects/${project.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: trimmed }),
  });
  if (!res.ok) {
    alert("Failed to rename project.");
    return;
  }
  loadAndRender();
}

async function deleteProject(project) {
  const confirmed = confirm(`Delete "${project.name}"? This cannot be undone.`);
  if (!confirmed) return;

  const res = await fetch(`/api/projects/${project.id}`, { method: "DELETE" });
  if (!res.ok) {
    alert("Failed to delete project.");
    return;
  }
  loadAndRender();
}

async function createProjectFromOutline() {
  const text = importText.value.trim();
  if (!text) return;
  const res = await fetch("/api/projects/from-outline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "Import failed. Check the outline format.");
    return;
  }
  const project = await res.json();
  window.location.href = `editor.html?project=${project.id}`;
}

newProjectBtn.addEventListener("click", createProject);
importOutlineBtn.addEventListener("click", () => {
  importText.value = "";
  importModal.hidden = false;
  importText.focus();
});
importCancelBtn.addEventListener("click", () => {
  importModal.hidden = true;
});
importModal.addEventListener("click", (e) => {
  if (e.target === importModal) importModal.hidden = true;
});
importConfirmBtn.addEventListener("click", createProjectFromOutline);

loadAndRender();
