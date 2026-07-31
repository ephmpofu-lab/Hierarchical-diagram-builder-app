# ARCHITEQ — UI Architecture & Dev Loop Directive

Addendum to `ARCHITEQ-Build-Directive.md` and `ARCHITEQ-Decomposition-Engine-Spec.md`. This file covers two things: (1) the UI/page structure, and (2) the development process to build the whole app under — both are binding.

---

## PART 1 — UI Architecture

### Principle: collapse stops, don't just declutter screens

Every additional page is a decision point and a context-switch cost. The reference model is Railway's actual dashboard behavior (not just its marketing site): the home screen doubles as the new-project screen — there is no separate "New Project" page, creating something is the primary action sitting on the same screen you land on. Deploy, monitor, and configure are all states on one canvas, not separate pages. Their embedded Agent is a persistent chat surface available on top of wherever you already are, not a page you navigate to.

Apply the same logic here. Do not build a wizard-style, multi-page flow. Collapse to the minimum number of real navigational stops.

### Final Screen Count: 2 user-facing screens + 1 hidden settings screen

**Screen 1 — Home / Canvas (merged, single landing surface)**
- Empty state (no history): intent input box front and center. "I want to develop a ___."
- Populated state (has history): past generated trees listed, but the same intent input box still sits on this same screen to start a new one. No click-through required to reach "new."
- Submitting an intent does NOT navigate to a different page. It populates this same screen with the generated tree in place.

**Screen 2 — Canvas, populated state (same screen as above, different state, not a different page)**
- Shows the frozen task tree visually: Layers → Sub-tasks → Atomic steps.
- Mode toggle control: `Python | n8n`. A UI element on this screen, not a separate page.
- Clicking any node opens a detail panel (slides in, canvas stays visible behind it): variables, `requires`/`produces`, and once mode is picked, the node's rendered code snippet or n8n node mapping.
- Rendered output (Python code blocks, or n8n SVG diagram + JSON download) is also a panel/state on this same canvas screen — not a separate "Output" page.

**Persistent element — Command/Refine Input**
- A lightweight input stays available on the canvas at all times, so refining an already-generated tree (e.g. "also add a rate-limiting step to Retrieval") is a message sent in place, not a re-navigation back to Screen 1.
- This is the direct equivalent of Railway's embedded Agent: available wherever the user already is.

**Screen 3 — Settings (hidden, admin-only)**
- Where `rules/domain_checklists/`, `rules/reference_architectures/`, and `rules/decomposition_principles.json` are viewed/edited.
- Not part of the primary user loop. Not in main navigation. Reached deliberately, not surfaced by default.

### Explicit instruction to Claude Code
Do not add a separate "New Project" page, a separate "Validation Results" page, a separate "History" page, or a separate "Output" page. If a workflow seems to need one, first check whether it can instead be a state, panel, or persistent input on Screen 1/2 before creating a new page.

---

## PART 2 — Development Process: The AI Dev Loop

The app itself must be built following this loop, and this loop should also be documented/available as the process Claude Code (and any future contributor) follows for every feature added to ARCHITEQ going forward — not just for the initial build.

### The Loop

```
              PRD
               │
   ┌───────────┼───────────┬────────────┬────────────┐
   ▼           ▼           ▼            ▼            ▼
 PLAN ◄──────────────────────────────────────── COMMIT
   │                                                ▲
   ▼                                                │
 BUILD ─────────────────────────────────────────► TEST
```

- **PRD** feeds directly into **PLAN**. Every plan traces back to a written requirement — nothing gets planned that isn't grounded in a PRD item. (For this app, the PRD is the three directive documents: Build Directive, Decomposition Engine Spec, and this file.)
- **PLAN → BUILD**: once a plan item is scoped, it gets built. No skipping straight from PRD to Build without a plan step — this mirrors P2 (No Skip) from the Decomposition Engine's own rules; the dev process should follow the same discipline it enforces in the product.
- **BUILD → TEST**: nothing built is considered done until tested.
- **TEST → COMMIT**: only passes tests, get committed.
- **COMMIT → PLAN**: closes the loop. A commit doesn't end the process — it feeds back into planning the next item. This is continuous, not a one-shot waterfall.

### How this applies to ARCHITEQ's build order specifically

Map the Build Priority Order already defined in `ARCHITEQ-Build-Directive.md` Section 6 onto this loop, one item at a time, not all at once:

```
PRD item (from directive docs)
   → PLAN: scope exactly what this item requires, confirm against P1–P8 and reference architecture rules where relevant
   → BUILD: implement just that item
   → TEST: verify it against the Validator/spec predicates before moving on
   → COMMIT: commit only once tested
   → back to PLAN: next item in the priority order
```

Example for item 1 (task tree schema): PLAN the schema fields against P4's `requires`/`produces` requirement → BUILD the JSON schema → TEST that a sample tree validates against it → COMMIT → PLAN item 2 (Decomposition Principles module).

### Explicit instruction to Claude Code
Do not batch multiple build-priority items into one untested commit. Each loop iteration is scoped to one item from the Section 6 priority list (or one sub-piece of an item, if the item is large). Do not proceed to the next PLAN step until the current item has passed TEST and been COMMITted. This applies for the entire lifetime of the project, not just the initial build — every future feature request follows the same PRD → Plan → Build → Test → Commit → Plan loop.
