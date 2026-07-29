// Workspace Framework shared state (Phase 9 Workspace & UX Architecture, WP11).
//
// A plain global script, loaded before editor.js -- this codebase has no bundler/module
// system (editor.js itself is one big top-level scope), so shared state here means real
// globals other scripts read/write directly, same convention as everything else in
// static/js/. Persisted via localStorage under the existing "diagram-builder-" prefix
// (theme.js, pane-collapse), not a new persistence pattern.
//
// WP11 built the workspace INFRASTRUCTURE only -- the switcher shell, the domain filter,
// and this shared registry/state layer. Each concrete workspace is its own independently
// testable follow-up WP (a standing project rule, not an oversight): WP11a (Kanban) is
// the first to flip its `available` flag to true and register real content; Timeline,
// Documentation, Dependencies, and Architecture Health remain named placeholders below
// until their own WPs are built.

const WORKSPACE_STORAGE_KEY = "diagram-builder-workspace";
const DOMAIN_FILTER_STORAGE_KEY = "diagram-builder-domain-filter";

// The three families from Phase 9 section 2. Only "canvas" has real content today --
// every other entry is a named placeholder a later WP fills in by giving it real content
// and flipping `available` to true, not by changing this list's shape.
const WORKSPACE_REGISTRY = [
  { id: "canvas", label: "Hierarchy", family: "Canvas", available: true },
  { id: "kanban", label: "Kanban", family: "Execution", available: true },
  { id: "timeline", label: "Timeline", family: "Execution", available: true },
  { id: "documentation", label: "Documentation", family: "Supporting", available: true },
  { id: "dependencies", label: "Dependencies", family: "Supporting", available: true },
  { id: "health", label: "Architecture Health", family: "Supporting", available: true },
  // First screen for the reasoning/governance backend (WP1-WP16) -- previously only
  // reachable by calling the API directly. New "Intelligence" family, same registry shape.
  { id: "reasoning", label: "AI Reasoning", family: "Intelligence", available: true },
];

// Domain-scoping toggle within the Canvas family (section 2's Canvas family diagram) --
// "Hierarchy" means no domain filter, i.e. show everything; the other four filter to
// nodes whose `classification` matches (WP8 already writes this field for decomposed
// nodes; manually-classified nodes work identically).
const DOMAIN_FILTERS = ["Hierarchy", "Business", "Data", "Application", "Technology"];

function getWorkspaceRegistry() {
  return WORKSPACE_REGISTRY;
}

function getCurrentWorkspaceId() {
  return localStorage.getItem(WORKSPACE_STORAGE_KEY) || "canvas";
}

function setCurrentWorkspaceId(id) {
  localStorage.setItem(WORKSPACE_STORAGE_KEY, id);
}

function getCurrentDomainFilter() {
  const stored = localStorage.getItem(DOMAIN_FILTER_STORAGE_KEY);
  return DOMAIN_FILTERS.includes(stored) ? stored : "Hierarchy";
}

function setCurrentDomainFilter(domain) {
  if (!DOMAIN_FILTERS.includes(domain)) return;
  localStorage.setItem(DOMAIN_FILTER_STORAGE_KEY, domain);
}
