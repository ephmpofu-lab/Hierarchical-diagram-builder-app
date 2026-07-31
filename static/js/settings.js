// Settings (hidden Screen 3, AMENDMENT 4 item 7): view/edit rules/decomposition_principles
// .json, rules/reference_architectures/*.json, and rules/domain_checklists/*.json as raw
// JSON. Not part of the primary user loop -- not linked from any nav element, reached only
// by navigating here directly. Same full-repaint-per-state-change pattern as decompose.js.

const settingsBoard = document.getElementById("settingsBoard");

let state = {
  principlesText: "",
  principlesStatus: "",
  refArchNames: [],
  selectedRefArch: "",
  refArchText: "",
  refArchStatus: "",
  checklistDomains: [],
  selectedChecklist: "",
  checklistText: "",
  checklistStatus: "",
};

function jsonEditorSection({ title, text, status, onTextChange, onSave, picker }) {
  const section = document.createElement("div");
  section.className = "decompose-layer-section";

  const heading = document.createElement("div");
  heading.className = "decompose-layer-heading";
  heading.textContent = title;
  section.appendChild(heading);

  if (picker) section.appendChild(picker);

  const textarea = document.createElement("textarea");
  textarea.className = "settings-json-editor";
  textarea.value = text;
  textarea.spellcheck = false;
  textarea.addEventListener("input", () => onTextChange(textarea.value));
  section.appendChild(textarea);

  const actions = document.createElement("div");
  actions.className = "reasoning-actions";
  const saveBtn = document.createElement("button");
  saveBtn.className = "btn btn-small";
  saveBtn.textContent = "Save";
  saveBtn.addEventListener("click", onSave);
  actions.appendChild(saveBtn);
  if (status) {
    const statusEl = document.createElement("span");
    statusEl.className = "settings-status";
    statusEl.textContent = status;
    actions.appendChild(statusEl);
  }
  section.appendChild(actions);

  return section;
}

function makePicker(names, selected, onChange) {
  const select = document.createElement("select");
  select.className = "settings-picker";
  for (const name of names) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    option.selected = name === selected;
    select.appendChild(option);
  }
  select.addEventListener("change", () => onChange(select.value));
  return select;
}

function renderBoard() {
  settingsBoard.innerHTML = "";

  const intro = document.createElement("div");
  intro.className = "reasoning-empty-state";
  intro.textContent = "Raw JSON. Saved changes take effect immediately -- there is no undo besides re-editing.";
  settingsBoard.appendChild(intro);

  settingsBoard.appendChild(jsonEditorSection({
    title: "Decomposition Principles (P1–P8)",
    text: state.principlesText,
    status: state.principlesStatus,
    onTextChange: (value) => { state.principlesText = value; },
    onSave: savePrinciples,
  }));

  settingsBoard.appendChild(jsonEditorSection({
    title: "Reference Architectures",
    text: state.refArchText,
    status: state.refArchStatus,
    onTextChange: (value) => { state.refArchText = value; },
    onSave: saveRefArch,
    picker: makePicker(state.refArchNames, state.selectedRefArch, selectRefArch),
  }));

  settingsBoard.appendChild(jsonEditorSection({
    title: "Domain Checklists",
    text: state.checklistText,
    status: state.checklistStatus,
    onTextChange: (value) => { state.checklistText = value; },
    onSave: saveChecklist,
    picker: makePicker(state.checklistDomains, state.selectedChecklist, selectChecklist),
  }));
}

async function loadPrinciples() {
  const res = await fetch("/api/decompose/settings/principles");
  if (!res.ok) return;
  state.principlesText = JSON.stringify(await res.json(), null, 2);
  renderBoard();
}

async function savePrinciples() {
  try {
    const parsed = JSON.parse(state.principlesText);
    const res = await fetch("/api/decompose/settings/principles", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    });
    state.principlesStatus = res.ok ? "Saved." : "Failed to save.";
  } catch {
    state.principlesStatus = "Invalid JSON -- not saved.";
  }
  renderBoard();
}

async function loadRefArchNames() {
  const res = await fetch("/api/decompose/settings/reference-architectures");
  if (!res.ok) return;
  state.refArchNames = await res.json();
  if (state.refArchNames.length > 0) await selectRefArch(state.refArchNames[0]);
}

async function selectRefArch(name) {
  state.selectedRefArch = name;
  const res = await fetch(`/api/decompose/settings/reference-architectures/${encodeURIComponent(name)}`);
  state.refArchText = res.ok ? JSON.stringify(await res.json(), null, 2) : "";
  state.refArchStatus = "";
  renderBoard();
}

async function saveRefArch() {
  try {
    const parsed = JSON.parse(state.refArchText);
    const res = await fetch(`/api/decompose/settings/reference-architectures/${encodeURIComponent(state.selectedRefArch)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    });
    state.refArchStatus = res.ok ? "Saved." : "Failed to save.";
  } catch {
    state.refArchStatus = "Invalid JSON -- not saved.";
  }
  renderBoard();
}

async function loadChecklistDomains() {
  const res = await fetch("/api/decompose/settings/checklists");
  if (!res.ok) return;
  state.checklistDomains = await res.json();
  if (state.checklistDomains.length > 0) await selectChecklist(state.checklistDomains[0]);
}

async function selectChecklist(domain) {
  state.selectedChecklist = domain;
  const res = await fetch(`/api/decompose/settings/checklists/${encodeURIComponent(domain)}`);
  state.checklistText = res.ok ? JSON.stringify(await res.json(), null, 2) : "";
  state.checklistStatus = "";
  renderBoard();
}

async function saveChecklist() {
  try {
    const parsed = JSON.parse(state.checklistText);
    const res = await fetch(`/api/decompose/settings/checklists/${encodeURIComponent(state.selectedChecklist)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    });
    state.checklistStatus = res.ok ? "Saved." : "Failed to save.";
  } catch {
    state.checklistStatus = "Invalid JSON -- not saved.";
  }
  renderBoard();
}

function init() {
  renderBoard();
  loadPrinciples();
  loadRefArchNames();
  loadChecklistDomains();
}

init();
