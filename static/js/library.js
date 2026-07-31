// The Launchpad (Home): one job only -- start engineering. No sidebar, no project
// templates grid, no filters/sort/star -- all of that either belongs to the Engineering
// Workspace (editor.html) or has been deliberately simplified away per the product's own
// "two completely separate experiences" philosophy. The primary input is the only way to
// begin; typing an idea and submitting carries it into the Discovery Session as the
// user's own first message (via sessionStorage handoff, same pattern login.html already
// uses for its own cross-page message handoff).

const LAUNCHPAD_IDEA_KEY = "architeq-launchpad-idea";

const userAvatarBtn = document.getElementById("userAvatarBtn");
const userMenu = document.getElementById("userMenu");
const userInitials = document.getElementById("userInitials");
const userMenuEmail = document.getElementById("userMenuEmail");
const launchpadInput = document.getElementById("launchpadInput");
const launchpadSubmitBtn = document.getElementById("launchpadSubmitBtn");
const launchpadExamples = document.getElementById("launchpadExamples");
const recentProjectsList = document.getElementById("recentProjectsList");
const emptyState = document.getElementById("emptyState");

function updateIdentity() {
  const email = currentSession && currentSession.user ? currentSession.user.email : "";
  userInitials.textContent = email ? email.slice(0, 2).toUpperCase() : "–";
  userMenuEmail.textContent = email || "";
}

userAvatarBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  userMenu.hidden = !userMenu.hidden;
});
document.addEventListener("click", (e) => {
  if (!userMenu.hidden && !userMenu.contains(e.target) && e.target !== userAvatarBtn) {
    userMenu.hidden = true;
  }
});

// currentSession (from auth.js) may not be populated yet on first paint -- poll briefly
// until requireSession()'s own async fetch resolves, rather than racing it.
(function waitForSession() {
  if (currentSession) {
    updateIdentity();
  } else {
    setTimeout(waitForSession, 100);
  }
})();

// ---------- Primary input: the only way to start engineering ----------

function startEngineering() {
  const idea = launchpadInput.value.trim();
  if (idea) sessionStorage.setItem(LAUNCHPAD_IDEA_KEY, idea);
  window.location.href = "decompose.html";
}

launchpadSubmitBtn.addEventListener("click", startEngineering);
launchpadInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    startEngineering();
  }
});
launchpadExamples.addEventListener("click", (e) => {
  const chip = e.target.closest(".example-chip");
  if (!chip) return;
  launchpadInput.value = chip.textContent;
  launchpadInput.focus();
});

// ---------- Recent projects: a simple list, not a dashboard ----------

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
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
  loadRecentProjects();
}

async function deleteProject(project) {
  const confirmed = confirm(`Delete "${project.name}"? This cannot be undone.`);
  if (!confirmed) return;
  const res = await fetch(`/api/projects/${project.id}`, { method: "DELETE" });
  if (!res.ok) {
    alert("Failed to delete project.");
    return;
  }
  loadRecentProjects();
}

function renderRecentProjects(projects) {
  recentProjectsList.innerHTML = "";
  if (projects.length === 0) {
    emptyState.hidden = false;
    return;
  }
  emptyState.hidden = true;

  for (const project of projects.slice(0, 8)) {
    const row = document.createElement("div");
    row.className = "launchpad-recent-row";

    const name = document.createElement("span");
    name.className = "launchpad-recent-name";
    name.textContent = project.name;
    name.addEventListener("click", () => {
      window.location.href = `editor.html?project=${project.id}`;
    });

    const meta = document.createElement("div");
    meta.className = "launchpad-recent-meta";

    const modified = document.createElement("span");
    modified.textContent = formatDate(project.updated_at);
    meta.appendChild(modified);

    const actionsWrap = document.createElement("div");
    actionsWrap.className = "row-actions-wrap";
    const menuBtn = document.createElement("button");
    menuBtn.className = "row-menu-btn";
    menuBtn.textContent = "⋯";
    menuBtn.title = "Rename or delete";
    const menu = document.createElement("div");
    menu.className = "dropdown-menu";
    menu.hidden = true;
    menu.style.right = "0";
    menu.style.left = "auto";
    const renameBtn = document.createElement("button");
    renameBtn.textContent = "Rename";
    renameBtn.addEventListener("click", () => {
      menu.hidden = true;
      renameProject(project);
    });
    const deleteBtn = document.createElement("button");
    deleteBtn.className = "danger";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", () => {
      menu.hidden = true;
      deleteProject(project);
    });
    menu.appendChild(renameBtn);
    menu.appendChild(deleteBtn);
    menuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.hidden = !menu.hidden;
    });
    actionsWrap.appendChild(menuBtn);
    actionsWrap.appendChild(menu);
    meta.appendChild(actionsWrap);

    row.appendChild(name);
    row.appendChild(meta);
    recentProjectsList.appendChild(row);
  }
}

document.addEventListener("click", (e) => {
  for (const menu of recentProjectsList.querySelectorAll(".dropdown-menu")) {
    if (!menu.hidden && !menu.contains(e.target)) menu.hidden = true;
  }
});

async function loadRecentProjects() {
  const res = await fetch("/api/projects");
  if (!res.ok) return;
  const projects = await res.json();
  projects.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
  renderRecentProjects(projects);
}

loadRecentProjects();
