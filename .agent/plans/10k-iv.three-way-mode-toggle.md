# Plan 10k-iv: Three-Way `Python | n8n | Tree` Mode Toggle

**Complexity: Medium.** Restructures `renderCanvasView`'s existing branching; touches one
JS file, one CSS file (toggle already pill-styled from 10j, no new rule needed), and
`ARCHITEQ-APP-FLOW.md` per DP12. Third of 10k's four sub-plans.

## Requirement

`docs/ARCHITEQ-n8n-Canvas-Complete-Spec.md` 4.1 — corrected from
`ARCHITEQ-APP-FLOW.md:66`'s "Tree diagram — the frozen tree, always visible." The
Layer/Sub-task/Atomic-step tree stops being unconditionally stacked above whatever mode is
selected; it becomes a third, equal mode option. Directly resolves the layout confusion
flagged earlier this session (two diagrams stacked with no visual separation) by removing
the stacking, not adding a divider.

## Scope decisions

1. Mode toggle becomes `["python", "n8n", "tree"]`, same pill styling already in place
   (10j) — no new CSS needed beyond the button label.
2. Default mode on domain load changes from `null` to `"tree"` — preserves the prior
   "you see something immediately" experience without violating "not stacked": Tree is a
   real, single selected mode, not a permanent background layer. Also avoids an unnecessary
   `/api/decompose/render/{mode}` round-trip on every domain open (Tree needs no fetch;
   its data is already in `state.tree`). Applied everywhere `mode` currently resets to
   `null`: initial state, `selectDomain`, and the post-refine reset (a refined tree's
   structure changed, but Tree mode needs no re-fetch to reflect that, unlike Python/n8n's
   now-stale render caches, which still reset to `null`/re-fetch on next selection as
   today).
3. `selectMode("tree")` short-circuits before the existing fetch logic — no backend call,
   matching the Python/n8n branches' own real-work-only-when-real-work-needed pattern.
4. Selecting Tree mode shows the tree diagram alone, full-canvas width, not layered with
   the output section (removes the two-stacked-diagrams read entirely, not a smaller
   version of it).

## Build

- `static/js/decompose.js`, `renderCanvasView`: unconditional `renderTreeDiagram` call
  removed; mode toggle extended to three buttons; canvas body now branches on
  `state.mode`: `"tree"` renders the tree diagram alone, `"python"`/`"n8n"` render
  `renderOutputSection()` as today, no mode renders nothing (the pre-selection state,
  reachable only via the post-refine reset path if ever re-nulled elsewhere).
- `selectMode`: early return for `"tree"` after setting state, before the existing
  `cacheKey`/fetch logic (which stays python/n8n-only).
- Every `mode: null` reset site changed to `mode: "tree"`.
- `ARCHITEQ-APP-FLOW.md`: line 66 ("Tree diagram — the frozen tree, always visible")
  corrected to describe the three-way toggle, per DP12 (a spec-document change triggers a
  cross-reference check before it's complete — `docs/ARCHITEQ-n8n-Canvas-Complete-Spec.md`
  4.1 is the new source of truth this line must match).

## Test

Real Playwright screenshots + DOM queries, per DP14: domain loads directly into Tree mode
(no extra fetch fired — confirmed via network event count, not just "the render looks
right"), tree diagram renders alone (no output section present in the DOM alongside it),
switching to Python or n8n mode replaces it entirely (tree diagram absent from the DOM in
those modes, not just visually behind something). Mode toggle shows three real, correctly
highlighted options. Full pytest suite green.

## Commit

One commit, then a second flipping this file's own Committed checkbox.

## Status

- [x] Built — mode toggle extended to `["python", "n8n", "tree"]`; `renderCanvasView`'s
  unconditional `renderTreeDiagram` call replaced with a branch on `state.mode` (`"tree"` ->
  tree diagram alone, `"python"`/`"n8n"` -> `renderOutputSection()`, matching today);
  `selectMode("tree")` short-circuits before the fetch logic; every `mode: null` reset site
  (initial state, `selectDomain`, post-refine) changed to `mode: "tree"`.
  `ARCHITEQ-APP-FLOW.md` section 5 and its button-actions table corrected per DP12.
- [x] Tested — real DOM query + network monitoring against the served `rag` domain (not a
  visual glance): on domain load, the Tree button is the only active one, zero
  `/render/{mode}` requests fire, the tree diagram is present and the output section is
  absent; clicking n8n removes the tree diagram from the DOM entirely (not just visually
  behind it) and the output section appears, with exactly one real `/render/n8n` request
  firing. Screenshot confirms no layout confusion -- one diagram, not two stacked. Full
  pytest suite green (443 passed after this sub-plan's own commit -- one pre-existing
  self-referential test updated for Module 10's honest current state, same established
  pattern).
- [ ] Committed
