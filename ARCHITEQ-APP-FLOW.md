# App Flow: ARCHITEQ

Per `~/.claude/frameworks/universal-prd-framework.md` Section 2 and `rules/principles/
ui-design.md`. Companion to `ARCHITEQ-UI-and-Dev-Loop-Directive.md`, which mandates the
underlying "2 screens + 1 hidden Settings screen" constraint this document maps concretely
against the real, built `decompose.html`/`decompose.js` state machine.

---

## 1. Screens

| Screen | File | Reachable from nav? |
|---|---|---|
| Home / Canvas (merged) | `decompose.html` + `decompose.js` | Yes — the app's one real entry point |
| Settings | `settings.html` + `settings.js` | No — deliberately unlinked, per R16 |

Everything below "Home / Canvas" is a **state**, not a separate page: `state.view` takes
one of `"home" | "drafting" | "reviewing_draft" | "canvas"`, and `renderBoard()` repaints in
place on every transition. No URL/route change happens between these states.

## 2. Onboarding

There is no separate onboarding flow. `view: "home"` is both the landing state and the
new-intent state: an intent input box, front and center. If `taxonomy.list_domains()` is
non-empty, a "past decompositions" list renders below the same input — the input never
disappears once history exists (R17: submitting an intent never navigates to a different
page).

## 3. Primary User Journey — New Domain

```
view: "home"
    user types a free-text intent, submits
    -> POST /api/decompose/intent
    if intent resolves to a KNOWN domain (tree_available: true):
        -> view: "canvas" directly, tree already loaded (GET .../domains/{domain}/tree)
    if intent resolves to a domain with NO frozen tree yet:
        -> view: "drafting"
view: "drafting"
    -> POST /api/decompose/domains/{domain}/draft   (Stages 0-4, one-time authoring)
    on success -> view: "reviewing_draft"
    on failure -> view: "home", error message shown inline
view: "reviewing_draft"
    shows the proposed tree + any validator violations, inline, on the same state
    user clicks Approve -> POST /api/decompose/domains/{domain}/approve
    -> view: "canvas", tree now frozen and loaded
view: "canvas"
    Layer -> Sub-task -> Atomic step tree, rendered as a real branching SVG diagram
    (trunk+bus / straight-line connectors, distinct box size/color per level)
    Python | n8n mode toggle -- selecting a mode calls
        POST /api/decompose/render/python  or  POST /api/decompose/render/n8n
        (client-side cached per domain+mode, no re-fetch on re-toggle)
    persistent refine input, always visible in this state
        -> POST /api/decompose/domains/{domain}/refine
```

## 4. Primary User Journey — Returning to a Known Domain

```
view: "home" -> history list entry clicked, OR intent resolves to a known domain
    -> view: "canvas" directly (no drafting/reviewing_draft detour)
```

## 5. Screens/Panels Within `canvas`

- **Tree diagram** — the frozen tree, always visible.
- **Node detail drawer** — clicking any node (Layer, Sub-task, or Atomic step box) slides in
  a fixed-position panel (canvas stays visible behind it, not an overlay that hides it):
  variables, requires/produces, rules, pillar tags, and the mode-specific
  code snippet/node mapping for that node, all read from the already-fetched whole-domain
  render (no new per-node network call). Escape or backdrop click closes it.
- **Refine bar** — a small persistent input pinned to the canvas. Submitting an instruction
  re-validates and re-freezes the tree in place; the canvas re-renders with the updated
  tree, still in `view: "canvas"`.
- **Output section** — once a mode is picked, ordered Python code blocks or the n8n SVG
  diagram + a "Download workflow.json" link render below/alongside the tree.

## 6. Settings (hidden)

Reached only by direct URL (`settings.html`), gated by the same `requireSession()` every
other page uses. Three raw-JSON panels: Decomposition Principles, Reference Architectures,
Domain Checklists — `GET`/`PUT` against `backend/taxonomy/repository.py`'s file-based
storage. No nav link anywhere in `decompose.html`.

## 7. Button Actions Reference

| Action | Trigger | Result |
|---|---|---|
| Submit intent | Home input, Enter or button | `POST /decompose/intent`, transitions per Section 3 |
| Click history entry | Home, past-decompositions list | Loads that domain's frozen tree directly into `canvas` |
| Approve draft | `reviewing_draft` state | `POST .../approve`, freezes tree, transitions to `canvas` |
| Select Python/n8n | Canvas mode toggle | `POST .../render/{mode}`, renders output section |
| Click a tree node | Canvas, any Layer/Sub-task/Atomic-step box | Opens node detail drawer |
| Submit refine instruction | Canvas, persistent input | `POST .../refine`, re-renders tree in place |
| Download workflow.json | Canvas, n8n mode output | Client-side `Blob`/`URL.createObjectURL`, no new request |

## 8. Success / Error Paths

- **Intent doesn't resolve to any domain**: `view` stays `"home"`, an inline message states
  the intent wasn't recognized (per R1 — never silently invents a domain checklist).
- **Draft fails validation after `MAX_DECOMPOSITION_RETRIES`**: `view` returns to `"home"`
  with a specific, named-violation error message (per R9 — never a generic failure).
  Actually reached via `reviewing_draft` showing the last attempt's violations if the draft
  call itself succeeded but produced a tree that still needs visible correction context.
- **Refine instruction produces an invalid tree**: the refine call's own validation rejects
  it server-side; the canvas keeps the last-good frozen tree, an inline error names the
  violation, per the same "specific violation, not generic failure" standard as R9.
- **Render call fails** (e.g. transient AI error): the mode toggle's own section shows an
  inline retry affordance; the tree itself is unaffected since rendering never mutates the
  frozen tree.
